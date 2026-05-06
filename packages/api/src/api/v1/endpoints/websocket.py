"""
WebSocket endpoint — real-time event streaming.

Preferred auth: ?ticket=<single-use ticket from POST /ws/ticket>
Legacy auth:    ?token=<JWT> (kept for backward compatibility)

The ticket pattern keeps the JWT out of server logs and browser history.
See POST /ws/ticket to exchange a Bearer token for a short-lived ticket.
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket

from ....core.security import _TICKET_VERIFIED_SENTINEL
from ....websocket.manager import WebSocketManager
from ....websocket.tickets import get_ticket_store

router = APIRouter(tags=["WebSocket"])

# Module-level manager — shared across all connections for the lifetime
# of the process. Instantiated once here so the router is self-contained.
_ws_manager = WebSocketManager()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    ticket: str | None = None,
    token: str | None = None,
) -> None:
    """
    Real-time WebSocket stream for a client.

    **Authentication (choose one):**
    - `?ticket=<value>` — preferred; exchange your JWT for a ticket via
      `POST /ws/ticket` first. The ticket expires in 30 seconds and can
      only be used once, keeping the JWT out of server logs.
    - `?token=<jwt>` — legacy; the JWT appears in server access logs.

    **Events sent by the server:**
    - `connected` — session established
    - `log` — bot engine log line
    - `bot_created` / `bot_removed` / `bot_stopped` — lifecycle events
    - `order_success` / `trade_success` — trade lifecycle events
    - `error` — command validation failure or handler exception
    - `ping` — keepalive (every 30 seconds)

    **Commands sent by the client:**
    - `{"key": "create"}` — create and auto-run a new bot
    - `{"key": "run", "botid": "..."}` — start a paused bot
    - `{"key": "stop", "botid": "..."}` — pause a running bot
    - `{"key": "remove", "botid": "..."}` — remove a bot
    - `{"key": "set_simulation", "botid": "...", "value": bool}` — toggle sim mode
    """
    # Retrieve BotService from app state (set by lifespan handler)
    bot_service = websocket.app.state.bot_service
    if bot_service is None:
        await websocket.close(code=1011)  # internal error — service unavailable
        return

    # Resolve identity from ticket (preferred) or token (legacy)
    resolved_token: str | None = None
    if ticket:
        store = get_ticket_store()
        identity = store.redeem(ticket)
        if identity is None:
            await websocket.close(code=1008)  # invalid/expired ticket
            return
        resolved_token = _TICKET_VERIFIED_SENTINEL
    else:
        resolved_token = token

    await _ws_manager.handle_connection(
        websocket, client_id, resolved_token, bot_service._manager
    )
