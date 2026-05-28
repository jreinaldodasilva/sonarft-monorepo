"""
Shared bot lifecycle handler functions.
Called by both the canonical /clients/{client_id}/bots routes and the
legacy /bots?client_id= routes, differing only in how client_id is sourced.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException

from ...core.errors import BotLimitExceededError, BotNotFoundError
from ...models.schemas import (
    BotCreateResponse,
    BotListResponse,
    MessageResponse,
    TradeRecord,
)
from ...services.bot_service import BotService


def _parse_ts(value: str | None, param_name: str) -> str | None:
    """Validate an optional ISO 8601 timestamp query parameter."""
    if value is None:
        return None
    try:
        datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid {param_name}: must be ISO 8601 (e.g. 2025-01-01T00:00:00)",
        )
    return value


async def handle_list_bots(client_id: str, service: BotService) -> BotListResponse:
    return BotListResponse(botids=service.get_botids(client_id))


async def handle_create_bot(client_id: str, service: BotService) -> BotCreateResponse:
    try:
        botid = await service.create_bot(client_id)
        return BotCreateResponse(botid=botid)
    except BotLimitExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc


async def handle_run_bot(botid: str, client_id: str, service: BotService) -> MessageResponse:
    try:
        await service.run_bot(botid, client_id)
        return MessageResponse(message=f"Bot {botid} started.")
    except BotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


async def handle_stop_bot(botid: str, client_id: str, service: BotService) -> MessageResponse:
    try:
        await service.stop_bot(botid, client_id)
        return MessageResponse(message=f"Bot {botid} stopped.")
    except BotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


async def handle_remove_bot(botid: str, client_id: str, service: BotService) -> None:
    try:
        await service.remove_bot(botid, client_id)
    except BotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


async def handle_get_orders(
    botid: str,
    client_id: str,
    service: BotService,
    limit: int,
    offset: int,
    from_ts: str | None,
    to_ts: str | None,
) -> list[TradeRecord]:
    return await service.get_orders(
        botid, client_id, limit, offset,
        _parse_ts(from_ts, "from_ts"), _parse_ts(to_ts, "to_ts"),
    )


async def handle_get_trades(
    botid: str,
    client_id: str,
    service: BotService,
    limit: int,
    offset: int,
    from_ts: str | None,
    to_ts: str | None,
) -> list[TradeRecord]:
    return await service.get_trades(
        botid, client_id, limit, offset,
        _parse_ts(from_ts, "from_ts"), _parse_ts(to_ts, "to_ts"),
    )
