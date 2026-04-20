"""
SonarFT WebSocket Manager
Handles per-client WebSocket connections and structured event streaming.
"""
from __future__ import annotations
import asyncio
import json
import logging
import re
import time
from typing import Dict, List, Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from ..core.security import verify_token
from ..core.config import get_settings

_logger = logging.getLogger(__name__)

_BOTID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
_WS_QUEUE_MAX_SIZE = 1000
_WS_KEEPALIVE_INTERVAL = 30.0


class WebSocketManager:
    """
    Manages per-client WebSocket connections.
    Decoupled from the bot manager — receives events via an asyncio.Queue.
    """

    def __init__(self) -> None:
        self.connections: Dict[str, WebSocket] = {}
        self.queues: Dict[str, asyncio.Queue] = {}
        # Per-client list of tracked background tasks
        self._tasks: Dict[str, List[asyncio.Task]] = {}

    def get_or_create_queue(self, client_id: str) -> asyncio.Queue:
        if client_id not in self.queues:
            self.queues[client_id] = asyncio.Queue(maxsize=_WS_QUEUE_MAX_SIZE)
        return self.queues[client_id]

    async def push_event(self, client_id: str, event: dict) -> None:
        """Push a structured event to a client's queue."""
        q = self.queues.get(client_id)
        if q:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                _logger.warning("WS queue full for client %s — event dropped: %s", client_id, event.get("type"))

    def _track_task(self, client_id: str, task: asyncio.Task) -> None:
        self._tasks.setdefault(client_id, []).append(task)

    async def handle_connection(
        self,
        websocket: WebSocket,
        client_id: str,
        token: Optional[str],
        bot_manager,
    ) -> None:
        """Main WebSocket connection handler."""
        try:
            verify_token(token)
        except Exception:
            _logger.warning("WS auth failure for client %s — closing with 1008", client_id)
            await websocket.close(code=1008)
            return

        # Close any existing connection for this client_id before accepting the new one
        existing = self.connections.get(client_id)
        if existing:
            try:
                await existing.close(code=1001)
            except Exception:
                pass

        await websocket.accept()
        self.connections[client_id] = websocket
        queue = self.get_or_create_queue(client_id)

        _logger.info("Client %s connected", client_id)

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
            except Exception:
                break

            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                await self.push_event(client_id, {
                    "type": "error",
                    "message": "Invalid JSON",
                    "ts": int(time.time()),
                })
                continue

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
                    task = asyncio.create_task(
                        self._handle_create(client_id, bot_manager)
                    )
                    self._track_task(client_id, task)

            elif key == "run":
                if not botid or not _BOTID_RE.match(str(botid)):
                    await self.push_event(client_id, {
                        "type": "error", "message": "Invalid or missing botid", "ts": int(time.time()),
                    })
                else:
                    task = asyncio.create_task(
                        self._handle_run(client_id, botid, bot_manager)
                    )
                    self._track_task(client_id, task)

            elif key == "remove":
                if not botid or not _BOTID_RE.match(str(botid)):
                    await self.push_event(client_id, {
                        "type": "error", "message": "Invalid or missing botid", "ts": int(time.time()),
                    })
                else:
                    task = asyncio.create_task(
                        self._handle_remove(client_id, botid, bot_manager)
                    )
                    self._track_task(client_id, task)

            elif key == "set_simulation":
                if not botid or not _BOTID_RE.match(str(botid)):
                    await self.push_event(client_id, {
                        "type": "error", "message": "Invalid or missing botid", "ts": int(time.time()),
                    })
                else:
                    value = bool(event.get("value", True))
                    task = asyncio.create_task(
                        self._handle_set_simulation(client_id, botid, value, bot_manager)
                    )
                    self._track_task(client_id, task)

            else:
                await self.push_event(client_id, {
                    "type": "error",
                    "message": f"Unknown command: {key!r}",
                    "ts": int(time.time()),
                })

    # ### Command handlers — awaited wrappers that push lifecycle events ###

    async def _handle_create(self, client_id: str, bot_manager) -> None:
        try:
            botid = await bot_manager.create_bot(client_id)
            await self.push_event(client_id, {
                "type": "bot_created",
                "botid": botid,
                "ts": int(time.time()),
            })
            _logger.info("WS bot_created: %s for client %s", botid, client_id)
        except Exception as exc:
            _logger.error("WS create_bot failed for client %s: %s", client_id, exc)
            await self.push_event(client_id, {
                "type": "error",
                "message": f"Bot creation failed: {exc}",
                "ts": int(time.time()),
            })

    async def _handle_run(self, client_id: str, botid: str, bot_manager) -> None:
        try:
            await bot_manager.run_bot(botid)
        except Exception as exc:
            _logger.error("WS run_bot failed for %s: %s", botid, exc)
            await self.push_event(client_id, {
                "type": "error",
                "message": f"Bot run failed: {exc}",
                "ts": int(time.time()),
            })

    async def _handle_remove(self, client_id: str, botid: str, bot_manager) -> None:
        try:
            await bot_manager.remove_bot(botid)
            await self.push_event(client_id, {
                "type": "bot_removed",
                "botid": botid,
                "ts": int(time.time()),
            })
            _logger.info("WS bot_removed: %s for client %s", botid, client_id)
        except Exception as exc:
            _logger.error("WS remove_bot failed for %s: %s", botid, exc)
            await self.push_event(client_id, {
                "type": "error",
                "message": f"Bot removal failed: {exc}",
                "ts": int(time.time()),
            })

    async def _handle_set_simulation(
        self, client_id: str, botid: str, value: bool, bot_manager
    ) -> None:
        try:
            await bot_manager.set_simulation_mode(botid, value)
        except Exception as exc:
            _logger.error("WS set_simulation failed for %s: %s", botid, exc)
            await self.push_event(client_id, {
                "type": "error",
                "message": f"Set simulation failed: {exc}",
                "ts": int(time.time()),
            })

    async def _send_loop(
        self,
        websocket: WebSocket,
        client_id: str,
        queue: asyncio.Queue,
    ) -> None:
        """Drain the event queue and send to client."""
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=_WS_KEEPALIVE_INTERVAL)
                await websocket.send_text(json.dumps(event))
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping", "ts": int(time.time())}))
            except Exception:
                break

    def _cleanup(self, client_id: str) -> None:
        self.connections.pop(client_id, None)
        self.queues.pop(client_id, None)
        # Cancel any in-flight background tasks for this client
        for task in self._tasks.pop(client_id, []):
            if not task.done():
                task.cancel()
        _logger.info("Client %s disconnected", client_id)
