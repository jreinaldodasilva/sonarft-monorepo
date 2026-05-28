"""
Client-scoped endpoints — canonical path-segment form.
All client-scoped resources live under /clients/{client_id}/.

These are the preferred routes. The legacy query-param routes
(GET /bots?client_id=, GET /parameters?client_id=, etc.) remain
functional but are marked deprecated in OpenAPI.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response

from ....core.config import ID_PATTERN
from ....core.limiter import limiter
from ....core.security import require_auth
from ....models.schemas import (
    BotCreateResponse,
    BotListResponse,
    BotStatusResponse,
    ClientParametersConfig,
    IndicatorsConfig,
    MessageResponse,
    TradeRecord,
)
from ....services.bot_service import BotService, get_bot_service_from_state
from ....services.config_service import ConfigService, get_config_service_from_state
from .._bot_handlers import (
    handle_create_bot,
    handle_get_orders,
    handle_get_trades,
    handle_list_bots,
    handle_remove_bot,
    handle_run_bot,
    handle_stop_bot,
)

router = APIRouter(prefix="/clients", tags=["Clients"])

Auth = Annotated[None, Depends(require_auth)]
ClientId = Annotated[str, Path(pattern=ID_PATTERN, description="Client identifier")]
BotId = Annotated[str, Path(pattern=ID_PATTERN, description="Bot identifier")]
BotSvc = Annotated[BotService, Depends(get_bot_service_from_state)]
CfgSvc = Annotated[ConfigService, Depends(get_config_service_from_state)]


# ---------------------------------------------------------------------------
# Bots
# ---------------------------------------------------------------------------

@router.get("/{client_id}/bots", response_model=BotListResponse)
@limiter.limit("60/minute")
async def list_bots(
    request: Request,
    client_id: ClientId,
    _: Auth,
    service: BotSvc,
) -> BotListResponse:
    """List all bot IDs for a client."""
    return await handle_list_bots(client_id, service)


@router.post("/{client_id}/bots", response_model=BotCreateResponse, status_code=201)
@limiter.limit("10/minute")
async def create_bot(
    request: Request,
    client_id: ClientId,
    _: Auth,
    service: BotSvc,
    response: Response,
) -> BotCreateResponse:
    """Create a new bot for a client."""
    result = await handle_create_bot(client_id, service)
    response.headers["Location"] = (
        f"{request.base_url}api/v1/clients/{client_id}/bots/{result.botid}"
    )
    return result


@router.post("/{client_id}/bots/{botid}/run", response_model=MessageResponse)
@limiter.limit("20/minute")
async def run_bot(
    request: Request,
    client_id: ClientId,
    botid: BotId,
    _: Auth,
    service: BotSvc,
) -> MessageResponse:
    """Start a bot."""
    return await handle_run_bot(botid, client_id, service)


@router.post("/{client_id}/bots/{botid}/stop", response_model=MessageResponse)
@limiter.limit("20/minute")
async def stop_bot(
    request: Request,
    client_id: ClientId,
    botid: BotId,
    _: Auth,
    service: BotSvc,
) -> MessageResponse:
    """Pause a running bot (keeps it registered; resume via run)."""
    return await handle_stop_bot(botid, client_id, service)


@router.delete("/{client_id}/bots/{botid}", status_code=204)
@limiter.limit("20/minute")
async def remove_bot(
    request: Request,
    client_id: ClientId,
    botid: BotId,
    _: Auth,
    service: BotSvc,
) -> None:
    """Remove a bot."""
    await handle_remove_bot(botid, client_id, service)


@router.get("/{client_id}/bots/{botid}/status", response_model=BotStatusResponse)
@limiter.limit("60/minute")
async def get_bot_status(
    request: Request,
    client_id: ClientId,
    botid: BotId,
    _: Auth,
    service: BotSvc,
) -> BotStatusResponse:
    """Get runtime status for a bot (running, halted by circuit breaker, etc.)."""
    from ....core.errors import BotNotFoundError
    from fastapi import HTTPException
    try:
        status = await service.get_bot_status(botid, client_id)
        return BotStatusResponse(**status)
    except BotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{client_id}/bots/{botid}/orders", response_model=list[TradeRecord])
@limiter.limit("60/minute")
async def get_orders(
    request: Request,
    client_id: ClientId,
    botid: BotId,
    _: Auth,
    service: BotSvc,
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Records to skip"),
    from_ts: str | None = Query(default=None, description="ISO 8601 start timestamp (inclusive)"),
    to_ts: str | None = Query(default=None, description="ISO 8601 end timestamp (inclusive)"),
) -> list[TradeRecord]:
    """Get order history for a bot."""
    return await handle_get_orders(botid, client_id, service, limit, offset, from_ts, to_ts)


@router.get("/{client_id}/bots/{botid}/trades", response_model=list[TradeRecord])
@limiter.limit("60/minute")
async def get_trades(
    request: Request,
    client_id: ClientId,
    botid: BotId,
    _: Auth,
    service: BotSvc,
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Records to skip"),
    from_ts: str | None = Query(default=None, description="ISO 8601 start timestamp (inclusive)"),
    to_ts: str | None = Query(default=None, description="ISO 8601 end timestamp (inclusive)"),
) -> list[TradeRecord]:
    """Get trade history for a bot."""
    return await handle_get_trades(botid, client_id, service, limit, offset, from_ts, to_ts)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@router.get("/{client_id}/parameters/defaults", response_model=ClientParametersConfig)
@limiter.limit("60/minute")
async def get_default_parameters(
    request: Request,
    client_id: ClientId,
    _: Auth,
    service: CfgSvc,
) -> ClientParametersConfig:
    """Get default trading parameters."""
    return await service.get_default_parameters()


@router.get("/{client_id}/indicators/defaults", response_model=IndicatorsConfig)
@limiter.limit("60/minute")
async def get_default_indicators(
    request: Request,
    client_id: ClientId,
    _: Auth,
    service: CfgSvc,
) -> IndicatorsConfig:
    """Get default indicator settings."""
    return await service.get_default_indicators()


@router.get("/{client_id}/parameters", response_model=ClientParametersConfig)
@limiter.limit("60/minute")
async def get_parameters(
    request: Request,
    client_id: ClientId,
    _: Auth,
    service: CfgSvc,
) -> ClientParametersConfig:
    """Get per-client trading parameters."""
    return await service.get_parameters(client_id)


@router.put("/{client_id}/parameters", response_model=MessageResponse)
@limiter.limit("30/minute")
async def update_parameters(
    request: Request,
    client_id: ClientId,
    body: ClientParametersConfig,
    _: Auth,
    service: CfgSvc,
) -> MessageResponse:
    """Update per-client trading parameters."""
    await service.update_parameters(client_id, body)
    return MessageResponse(message=f"Parameters for {client_id} updated.")


@router.get("/{client_id}/indicators", response_model=IndicatorsConfig)
@limiter.limit("60/minute")
async def get_indicators(
    request: Request,
    client_id: ClientId,
    _: Auth,
    service: CfgSvc,
) -> IndicatorsConfig:
    """Get per-client indicator settings."""
    return await service.get_indicators(client_id)


@router.put("/{client_id}/indicators", response_model=MessageResponse)
@limiter.limit("30/minute")
async def update_indicators(
    request: Request,
    client_id: ClientId,
    body: IndicatorsConfig,
    _: Auth,
    service: CfgSvc,
) -> MessageResponse:
    """Update per-client indicator settings."""
    await service.update_indicators(client_id, body)
    return MessageResponse(message=f"Indicators for {client_id} updated.")
