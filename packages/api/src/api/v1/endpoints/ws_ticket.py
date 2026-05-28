"""
WebSocket ticket endpoint.
POST /ws/ticket — exchange a valid Bearer token for a short-lived single-use
WebSocket ticket. The ticket is passed as ?ticket= on the WS URL, keeping
the JWT out of server logs and browser history.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ....core.limiter import limiter
from ....core.security import get_client_id
from ....models.schemas import WsTicketResponse
from ....websocket.tickets import TICKET_TTL_SECONDS, get_ticket_store

router = APIRouter(tags=["WebSocket"])

ClientId = Annotated[str, Depends(get_client_id)]


@router.post("/ws/ticket", response_model=WsTicketResponse)
@limiter.limit("30/minute")
async def issue_ws_ticket(
    request: Request,
    client_id: ClientId,
) -> WsTicketResponse:
    """
    Exchange a valid Bearer token for a short-lived WebSocket ticket.

    The returned ticket should be passed as `?ticket=<value>` when opening
    the WebSocket connection. It expires in 30 seconds and can only be used once.
    """
    store = get_ticket_store()
    ticket = store.issue(client_id)
    return WsTicketResponse(ticket=ticket, ttl_seconds=TICKET_TTL_SECONDS)
