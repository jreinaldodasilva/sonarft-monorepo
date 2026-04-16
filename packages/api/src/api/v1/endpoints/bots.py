"""
Bot lifecycle endpoints.
"""
from __future__ import annotations
import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from ....core.security import require_auth
from ....core.errors import BotNotFoundError, BotLimitExceededError
from ....models.schemas import BotListResponse, BotCreateResponse, MessageResponse
from ....services.bot_service import BotService, get_bot_service

router = APIRouter(prefix="/bots", tags=["Bots"])
Auth = Annotated[None, Depends(require_auth)]


@router.get("", response_model=BotListResponse)
async def list_bots(
    client_id: str,
    _: Auth,
    service: BotService = Depends(get_bot_service),
) -> BotListResponse:
    """List all bot IDs for a client."""
    return BotListResponse(botids=service.get_botids(client_id))


@router.post("", response_model=BotCreateResponse, status_code=201)
async def create_bot(
    client_id: str,
    _: Auth,
    service: BotService = Depends(get_bot_service),
) -> BotCreateResponse:
    """Create a new bot for a client."""
    try:
        botid = await service.create_bot(client_id)
        return BotCreateResponse(botid=botid)
    except BotLimitExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc


@router.post("/{botid}/run", response_model=MessageResponse)
async def run_bot(
    botid: Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{1,64}$")],
    _: Auth,
    service: BotService = Depends(get_bot_service),
) -> MessageResponse:
    """Start a bot."""
    try:
        await service.run_bot(botid)
        return MessageResponse(message=f"Bot {botid} started.")
    except BotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{botid}/stop", response_model=MessageResponse)
async def stop_bot(
    botid: Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{1,64}$")],
    _: Auth,
    service: BotService = Depends(get_bot_service),
) -> MessageResponse:
    """Stop a running bot."""
    try:
        await service.stop_bot(botid)
        return MessageResponse(message=f"Bot {botid} stopped.")
    except BotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{botid}", response_model=MessageResponse)
async def remove_bot(
    botid: Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{1,64}$")],
    _: Auth,
    service: BotService = Depends(get_bot_service),
) -> MessageResponse:
    """Remove a bot."""
    try:
        await service.remove_bot(botid)
        return MessageResponse(message=f"Bot {botid} removed.")
    except BotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{botid}/orders")
async def get_orders(
    botid: Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{1,64}$")],
    _: Auth,
    service: BotService = Depends(get_bot_service),
) -> list:
    """Get order history for a bot."""
    return await service.get_orders(botid)


@router.get("/{botid}/trades")
async def get_trades(
    botid: Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{1,64}$")],
    _: Auth,
    service: BotService = Depends(get_bot_service),
) -> list:
    """Get trade history for a bot."""
    return await service.get_trades(botid)
