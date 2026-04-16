"""
SonarFT WebSocket Manager
Handles per-client WebSocket connections and structured event streaming.
"""
from __future__ import annotations
import asyncio
import json
import logging
import time
from collections import deque
from typing import Dict, Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from ..core.security import verify_token
from ..core.config import get_settings

_logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages per-client WebSocket connections.
    Decoupled from the bot manager — receives events via an asyncio.Queue.
    """

    def __init__(self) -> None:
        self.connections: Dict[str, WebSocket] = {}
        # Per-client event queues — bot manager pushes structured events here
        self.queues: Dict[str, asyncio.Queue] = {}

    def get_or_create_queue(self, client_id: str) -> asyncio.Queue:
        if client_id not in self.queues:
            self.queues[client_id] = asyncio.Queue(maxsize=1000)
        return self.queues[client_id]

    async def push_event(self, client_id: str, event: dict) -> None:
        """Push a structured event to a client's queue (called by bot manager)."""
        q = self.queues.get(client_id)
        if q:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # drop if queue full

    async def handle_connection(
        self,
        websocket: WebSocket,
        client_id: str,
        token: Optional[str],
        bot_manager,
    ) -> None:
        """Main WebSocket connection handler."""
        # Auth check
        try:
            verify_token(token)
        except Exception:
            await websocket.close(code=1008)
            return

        await websocket.accept()
        self.connections[client_id] = websocket
        queue = self.get_or_create_queue(client_id)

        _logger.info("Client %s connected", client_id)

        # Push connected event
        await queue.put_nowait({
            "type": "connected",
            "client_id": client_id,
            "ts": int(time.time()),
        })

        try:
            await asyncio.gather(
                self._receive_loop(websocket, client_id, bot_manager),
                self._send_loop(websocket, client_id, queue),
            )
        except WebSocketDisconnect:
            pass
        finally:
            self._cleanup(client_id)

    async def _receive_loop(
        self,
        websocket: WebSocket,
        client_id: str,
        bot_manager,
    ) -> None:
        """Receive commands from the client."""
        settings = get_settings()
        while True:
            try:
                raw = await websocket.receive_text()
                event = json.loads(raw)
            except (json.JSONDecodeError, Exception):
                break

            key = event.get("key")
            botid = event.get("botid")

            if key == "create":
                current = len(bot_manager.get_botids(client_id))
                if current >= settings.max_bots_per_client:
                    await self.push_event(client_id, {
                        "type": "error",
                        "message": f"Bot limit reached ({settings.max_bots_per_client})",
                        "ts": int(time.time()),
                    })
                else:
                    asyncio.create_task(bot_manager.create_bot(client_id))

            elif key == "run" and botid:
                asyncio.create_task(bot_manager.run_bot(botid))

            elif key == "remove" and botid:
                asyncio.create_task(bot_manager.remove_bot(botid))

            elif key == "set_simulation" and botid:
                value = event.get("value", True)
                asyncio.create_task(
                    bot_manager.set_simulation_mode(botid, value)
                )

    async def _send_loop(
        self,
        websocket: WebSocket,
        client_id: str,
        queue: asyncio.Queue,
    ) -> None:
        """Drain the event queue and send to client."""
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_text(json.dumps(event))
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_text(json.dumps({"type": "ping", "ts": int(time.time())}))
            except Exception:
                break

    def _cleanup(self, client_id: str) -> None:
        self.connections.pop(client_id, None)
        self.queues.pop(client_id, None)
        _logger.info("Client %s disconnected", client_id)
