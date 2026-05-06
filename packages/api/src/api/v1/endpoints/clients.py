"""
Client-scoped endpoints — canonical path-segment form.
All client-scoped resources live under /clients/{client_id}/.

These are the preferred routes. The legacy query-param routes
(GET /bots?client_id=, GET /parameters?client_id=, etc.) remain
functional but are marked deprecated in OpenAPI.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from ....core.config import ID_PATTERN
from ....core.errors import BotLimitExceededError, BotNotFoundError
from ....core.limiter import limiter
from ....core.security import require_auth
from ....models.schemas import (
    BotCreateResponse,
    BotListResponse,
    IndicatorsConfig,
    MessageResponse,
    ParametersConfig,
    TradeRecord,
)
from ....services.bot_service import BotService, get_bot_service_from_state
from ....services.config_service import ConfigService, get_config_service_from_state

router = APIRouter(prefix="/clients", tags=["Clients"])

Auth = Annotated[None, Depends(require_auth)]
# client_id comes from the path — validated by regex, no JWT extraction needed here
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
    return BotListResponse(botids=service.get_botids(client_id))


@router.post("/{client_id}/bots", response_model=BotCreateResponse, status_code=201)
@limiter.limit("10/minute")
async def create_bot(
    request: Request,
    client_id: ClientId,
    _: Auth,
    service: BotSvc,
) -> BotCreateResponse:
    """Create a new bot for a client."""
    try:
        botid = await service.create_bot(client_id)
        return BotCreateResponse(botid=botid)
    except BotLimitExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc


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
    try:
        await service.run_bot(botid, client_id)
        return MessageResponse(message=f"Bot {botid} started.")
    except BotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
    try:
        await service.stop_bot(botid, client_id)
        return MessageResponse(message=f"Bot {botid} stopped.")
    except BotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{client_id}/bots/{botid}", response_model=MessageResponse)
@limiter.limit("20/minute")
async def remove_bot(
    request: Request,
    client_id: ClientId,
    botid: BotId,
    _: Auth,
    service: BotSvc,
) -> MessageResponse:
    """Remove a bot."""
    try:
        await service.remove_bot(botid, client_id)
        return MessageResponse(message=f"Bot {botid} removed.")
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
) -> list[TradeRecord]:
    """Get order history for a bot."""
    return await service.get_orders(botid, client_id, limit, offset)


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
) -> list[TradeRecord]:
    """Get trade history for a bot."""
    return await service.get_trades(botid, client_id, limit, offset)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@router.get("/{client_id}/parameters", response_model=ParametersConfig)
@limiter.limit("60/minute")
async def get_parameters(
    request: Request,
    client_id: ClientId,
    _: Auth,
    service: CfgSvc,
) -> ParametersConfig:
    """Get per-client trading parameters."""
    return await service.get_parameters(client_id)


@router.put("/{client_id}/parameters", response_model=MessageResponse)
@limiter.limit("30/minute")
async def update_parameters(
    request: Request,
    client_id: ClientId,
    body: ParametersConfig,
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
