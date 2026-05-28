"""
Bot lifecycle endpoints — legacy query-param form.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from ....core.config import ID_PATTERN
from ....core.limiter import limiter
from ....core.security import get_client_id, require_auth
from ....models.schemas import (
    BotCreateResponse,
    BotListResponse,
    MessageResponse,
    TradeRecord,
)
from ....services.bot_service import BotService, get_bot_service_from_state
from .._bot_handlers import (
    handle_create_bot,
    handle_get_orders,
    handle_get_trades,
    handle_list_bots,
    handle_remove_bot,
    handle_run_bot,
    handle_stop_bot,
)
from .._legacy import add_deprecation_headers as _deprecation_headers

router = APIRouter(
    prefix="/bots",
    tags=["Bots (Legacy — use /clients/{client_id}/bots]"],
    deprecated=True,
    dependencies=[Depends(_deprecation_headers)],
)
Auth = Annotated[None, Depends(require_auth)]
ClientId = Annotated[str, Depends(get_client_id)]
BotId = Annotated[str, Path(pattern=ID_PATTERN)]
BotSvc = Annotated[BotService, Depends(get_bot_service_from_state)]


@router.get("", response_model=BotListResponse)
@limiter.limit("60/minute")
async def list_bots(
    request: Request,
    client_id: ClientId,
    service: BotSvc,
) -> BotListResponse:
    """List all bot IDs for a client."""
    return await handle_list_bots(client_id, service)


@router.post("", response_model=BotCreateResponse, status_code=201)
@limiter.limit("10/minute")
async def create_bot(
    request: Request,
    client_id: ClientId,
    service: BotSvc,
) -> BotCreateResponse:
    """Create a new bot for a client."""
    return await handle_create_bot(client_id, service)


@router.post("/{botid}/run", response_model=MessageResponse)
@limiter.limit("20/minute")
async def run_bot(
    request: Request,
    botid: BotId,
    client_id: ClientId,
    service: BotSvc,
) -> MessageResponse:
    """Start a bot."""
    return await handle_run_bot(botid, client_id, service)


@router.post("/{botid}/stop", response_model=MessageResponse)
@limiter.limit("20/minute")
async def stop_bot(
    request: Request,
    botid: BotId,
    client_id: ClientId,
    service: BotSvc,
) -> MessageResponse:
    """Stop a running bot."""
    return await handle_stop_bot(botid, client_id, service)


@router.delete("/{botid}", response_model=MessageResponse)
@limiter.limit("20/minute")
async def remove_bot(
    request: Request,
    botid: BotId,
    client_id: ClientId,
    service: BotSvc,
) -> MessageResponse:
    """Remove a bot."""
    await handle_remove_bot(botid, client_id, service)
    return MessageResponse(message=f"Bot {botid} removed.")


@router.get("/{botid}/orders", response_model=list[TradeRecord])
@limiter.limit("60/minute")
async def get_orders(
    request: Request,
    botid: BotId,
    client_id: ClientId,
    service: BotSvc,
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Records to skip"),
    from_ts: str | None = Query(default=None, description="ISO 8601 start timestamp (inclusive)"),
    to_ts: str | None = Query(default=None, description="ISO 8601 end timestamp (inclusive)"),
) -> list[TradeRecord]:
    """Get order history for a bot."""
    return await handle_get_orders(botid, client_id, service, limit, offset, from_ts, to_ts)


@router.get("/{botid}/trades", response_model=list[TradeRecord])
@limiter.limit("60/minute")
async def get_trades(
    request: Request,
    botid: BotId,
    client_id: ClientId,
    service: BotSvc,
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Records to skip"),
    from_ts: str | None = Query(default=None, description="ISO 8601 start timestamp (inclusive)"),
    to_ts: str | None = Query(default=None, description="ISO 8601 end timestamp (inclusive)"),
) -> list[TradeRecord]:
    """Get trade history for a bot."""
    return await handle_get_trades(botid, client_id, service, limit, offset, from_ts, to_ts)
