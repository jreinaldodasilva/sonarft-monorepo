"""
Bot lifecycle endpoints.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response

from ....core.config import ID_PATTERN
from ....core.errors import BotLimitExceededError, BotNotFoundError
from ....core.limiter import limiter
from ....core.security import get_client_id, require_auth
from ....models.schemas import (
    BotCreateResponse,
    BotListResponse,
    MessageResponse,
    TradeRecord,
)
from ....services.bot_service import BotService, get_bot_service_from_state

# Sunset date for legacy routes — update when a removal date is decided.
_SUNSET_DATE = "Sun, 01 Jan 2026 00:00:00 GMT"


def _deprecation_headers(response: Response) -> None:
    """Inject Deprecation and Sunset headers on every legacy response."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = _SUNSET_DATE


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
    return BotListResponse(botids=service.get_botids(client_id))


@router.post("", response_model=BotCreateResponse, status_code=201)
@limiter.limit("10/minute")
async def create_bot(
    request: Request,
    client_id: ClientId,
    service: BotSvc,
) -> BotCreateResponse:
    """Create a new bot for a client."""
    try:
        botid = await service.create_bot(client_id)
        return BotCreateResponse(botid=botid)
    except BotLimitExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc


@router.post("/{botid}/run", response_model=MessageResponse)
@limiter.limit("20/minute")
async def run_bot(
    request: Request,
    botid: BotId,
    client_id: ClientId,
    service: BotSvc,
) -> MessageResponse:
    """Start a bot."""
    try:
        await service.run_bot(botid, client_id)
        return MessageResponse(message=f"Bot {botid} started.")
    except BotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{botid}/stop", response_model=MessageResponse)
@limiter.limit("20/minute")
async def stop_bot(
    request: Request,
    botid: BotId,
    client_id: ClientId,
    service: BotSvc,
) -> MessageResponse:
    """Stop a running bot."""
    try:
        await service.stop_bot(botid, client_id)
        return MessageResponse(message=f"Bot {botid} stopped.")
    except BotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{botid}", response_model=MessageResponse)
@limiter.limit("20/minute")
async def remove_bot(
    request: Request,
    botid: BotId,
    client_id: ClientId,
    service: BotSvc,
) -> MessageResponse:
    """Remove a bot."""
    try:
        await service.remove_bot(botid, client_id)
        return MessageResponse(message=f"Bot {botid} removed.")
    except BotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{botid}/orders", response_model=list[TradeRecord])
@limiter.limit("60/minute")
async def get_orders(
    request: Request,
    botid: BotId,
    client_id: ClientId,
    service: BotSvc,
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Records to skip"),
) -> list[TradeRecord]:
    """Get order history for a bot."""
    return await service.get_orders(botid, client_id, limit, offset)


@router.get("/{botid}/trades", response_model=list[TradeRecord])
@limiter.limit("60/minute")
async def get_trades(
    request: Request,
    botid: BotId,
    client_id: ClientId,
    service: BotSvc,
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Records to skip"),
) -> list[TradeRecord]:
    """Get trade history for a bot."""
    return await service.get_trades(botid, client_id, limit, offset)
