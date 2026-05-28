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
from typing import TYPE_CHECKING

import orjson
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from ..core.config import ID_PATTERN, get_settings
from ..core.security import verify_token
from ..models.schemas import (
    WsBotCreatedEvent,
    WsBotRemovedEvent,
    WsBotStoppedEvent,
    WsConnectedEvent,
    WsErrorEvent,
    WsLogEvent,
    WsPingEvent,
)

if TYPE_CHECKING:
    from sonarft_manager import BotManager

_logger = logging.getLogger(__name__)

_BOTID_RE = re.compile(ID_PATTERN)
_WS_QUEUE_MAX_SIZE = 1000
_WS_KEEPALIVE_INTERVAL = 30.0

# Filter function: pass only log records from the bot package loggers
# (sonarft_manager, sonarft_bot, sonarft_search, sonarft_execution, etc.)
# The handler is attached to the root logger so all bot modules are captured
# regardless of their exact logger name.
_BOT_LOG_PREFIX = "sonarft"


def _is_bot_record(record: logging.LogRecord) -> bool:
    """Return True for log records originating from the bot package."""
    return record.name.startswith(_BOT_LOG_PREFIX)


class WsFanOutHandler(logging.Handler):
    """
    A single root-level logging handler that fans out bot log records to all
    active WebSocket client queues. Replaces the per-client WsLogHandler pattern
    so record formatting happens once (O(1)) rather than N times (O(N)).
    Attached to logging.root once at startup via _lifespan.
    """

    def __init__(self, manager: "WebSocketManager") -> None:
        super().__init__()
        self._manager = manager

    def emit(self, record: logging.LogRecord) -> None:
        if not _is_bot_record(record):
            return
        try:
            msg = self.format(record)
            event = WsLogEvent(
                ts=int(record.created),
                level=record.levelname,  # type: ignore[arg-type]
                message=msg,
            ).model_dump()
            # Detect trade lifecycle events
            if record.levelno >= logging.INFO:
                raw_msg = record.getMessage()
                if "Order: Success" in raw_msg:
                    order_event = {"type": "order_success", "ts": int(record.created)}
                elif "Trade: Success" in raw_msg:
                    order_event = {"type": "trade_success", "ts": int(record.created)}
                else:
                    order_event = None
            else:
                order_event = None
            for queue in list(self._manager.queues.values()):
                try:
                    queue.put_nowait(event)
                    if order_event:
                        queue.put_nowait(order_event)
                except asyncio.QueueFull:
                    pass
        except Exception:
            self.handleError(record)


class WsLogHandler(logging.Handler):
    """
    Legacy per-client handler — kept for backward compatibility with tests
    that attach it directly. In production the WsFanOutHandler is used instead.
    """

    def __init__(self, queue: asyncio.Queue) -> None:
        super().__init__()
        self._queue = queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            # Use WsLogEvent model to ensure the payload matches the typed contract.
            event = WsLogEvent(
                ts=int(record.created),
                level=record.levelname,  # type: ignore[arg-type]
                message=msg,
            ).model_dump()
            self._queue.put_nowait(event)
            # Detect trade lifecycle log lines and emit structured events
            # so the web client can refresh order/trade history tables.
            if record.levelno >= logging.INFO:
                if "Order: Success" in record.getMessage():
                    self._queue.put_nowait({"type": "order_success", "ts": int(record.created)})
                elif "Trade: Success" in record.getMessage():
                    self._queue.put_nowait({"type": "trade_success", "ts": int(record.created)})
        except asyncio.QueueFull:
            pass
        except Exception:
            self.handleError(record)


class WebSocketManager:
    """
    Manages per-client WebSocket connections.
    Decoupled from the bot manager — receives events via an asyncio.Queue.
    """

    def __init__(self) -> None:
        self.connections: dict[str, WebSocket] = {}
        self.queues: dict[str, asyncio.Queue] = {}
        # Per-client list of tracked background tasks
        self._tasks: dict[str, list[asyncio.Task]] = {}
        # Per-client log handlers attached to the bot logger
        self._log_handlers: dict[str, WsLogHandler] = {}

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

    async def _push_model(self, client_id: str, model) -> None:
        """Serialise a Pydantic event model and push to the client queue."""
        await self.push_event(client_id, model.model_dump())

    def _track_task(self, client_id: str, task: asyncio.Task) -> None:
        self._tasks.setdefault(client_id, []).append(task)

    async def handle_connection(
        self,
        websocket: WebSocket,
        client_id: str,
        token: str | None,
        bot_manager: BotManager,
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
            except Exception as exc:  # noqa: BLE001
                _logger.debug("Error closing existing WS for client %s: %s", client_id, exc)

        await websocket.accept()
        self.connections[client_id] = websocket
        queue = self.get_or_create_queue(client_id)

        _logger.info("Client %s connected", client_id)

        queue.put_nowait(
            WsConnectedEvent(client_id=client_id, ts=int(time.time())).model_dump()
        )

        # Attach log handler so bot log lines stream to this client
        self._attach_log_handler(client_id, queue)

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
        bot_manager: BotManager,
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
                await self._push_model(client_id, WsErrorEvent(
                    message="Invalid JSON", ts=int(time.time()),
                ))
                continue

            key = event.get("key")
            botid = event.get("botid")

            if key == "create":
                current = len(bot_manager.get_botids(client_id))
                if current >= settings.max_bots_per_client:
                    await self._push_model(client_id, WsErrorEvent(
                        message=f"Bot limit reached ({settings.max_bots_per_client})",
                        ts=int(time.time()),
                    ))
                else:
                    task = asyncio.create_task(
                        self._handle_create(client_id, bot_manager)
                    )
                    self._track_task(client_id, task)

            elif key == "run":
                if not botid or not _BOTID_RE.match(str(botid)):
                    await self._push_model(client_id, WsErrorEvent(
                        message="Invalid or missing botid", ts=int(time.time()),
                    ))
                elif botid not in bot_manager.get_botids(client_id):
                    await self._push_model(client_id, WsErrorEvent(
                        message="Bot not found", ts=int(time.time()),
                    ))
                else:
                    task = asyncio.create_task(
                        self._handle_run(client_id, botid, bot_manager)
                    )
                    self._track_task(client_id, task)

            elif key == "remove":
                if not botid or not _BOTID_RE.match(str(botid)):
                    await self._push_model(client_id, WsErrorEvent(
                        message="Invalid or missing botid", ts=int(time.time()),
                    ))
                elif botid not in bot_manager.get_botids(client_id):
                    await self._push_model(client_id, WsErrorEvent(
                        message="Bot not found", ts=int(time.time()),
                    ))
                else:
                    task = asyncio.create_task(
                        self._handle_remove(client_id, botid, bot_manager)
                    )
                    self._track_task(client_id, task)

            elif key == "stop":
                if not botid or not _BOTID_RE.match(str(botid)):
                    await self._push_model(client_id, WsErrorEvent(
                        message="Invalid or missing botid", ts=int(time.time()),
                    ))
                elif botid not in bot_manager.get_botids(client_id):
                    await self._push_model(client_id, WsErrorEvent(
                        message="Bot not found", ts=int(time.time()),
                    ))
                else:
                    task = asyncio.create_task(
                        self._handle_stop(client_id, botid, bot_manager)
                    )
                    self._track_task(client_id, task)

            elif key == "set_simulation":
                if not botid or not _BOTID_RE.match(str(botid)):
                    await self._push_model(client_id, WsErrorEvent(
                        message="Invalid or missing botid", ts=int(time.time()),
                    ))
                else:
                    value = bool(event.get("value", True))
                    task = asyncio.create_task(
                        self._handle_set_simulation(client_id, botid, value, bot_manager)
                    )
                    self._track_task(client_id, task)

            else:
                await self._push_model(client_id, WsErrorEvent(
                    message="Unknown command", ts=int(time.time()),
                ))

    def _attach_log_handler(self, client_id: str, queue: asyncio.Queue) -> None:
        """Attach a WsLogHandler to the root logger for this client.

        A filter restricts delivery to records from bot-package loggers
        (names starting with 'sonarft'), so API-internal log lines are
        not streamed to the WebSocket client.
        """
        handler = WsLogHandler(queue)
        handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
        handler.setLevel(logging.DEBUG)
        handler.addFilter(_is_bot_record)
        logging.root.addHandler(handler)
        self._log_handlers[client_id] = handler
        _logger.debug("WsLogHandler attached for client %s", client_id)

    def _detach_log_handler(self, client_id: str) -> None:
        """Remove the WsLogHandler from the root logger for this client."""
        handler = self._log_handlers.pop(client_id, None)
        if handler:
            logging.root.removeHandler(handler)
            _logger.debug("WsLogHandler detached for client %s", client_id)

    # ### Command handlers — awaited wrappers that push lifecycle events ###

    async def _handle_create(self, client_id: str, bot_manager: BotManager) -> None:
        try:
            botid = await bot_manager.create_bot(client_id)
            await self._push_model(client_id, WsBotCreatedEvent(botid=botid, ts=int(time.time())))
            _logger.info("WS bot_created: %s for client %s", botid, client_id)
            # Auto-run immediately — don’t wait for the client to send a run keypress
            # which can be lost if the WS reconnects during the creation window
            await bot_manager.run_bot(botid)
        except Exception as exc:
            _logger.error("WS create_bot failed for client %s: %s", client_id, exc)
            await self._push_model(client_id, WsErrorEvent(
                message="Bot creation failed", ts=int(time.time()),
            ))

    async def _handle_run(self, client_id: str, botid: str, bot_manager: BotManager) -> None:
        try:
            await bot_manager.run_bot(botid)
        except Exception as exc:
            _logger.error("WS run_bot failed for %s: %s", botid, exc)
            await self._push_model(client_id, WsErrorEvent(
                message="Bot run failed", ts=int(time.time()),
            ))

    async def _handle_remove(self, client_id: str, botid: str, bot_manager: BotManager) -> None:
        try:
            await bot_manager.remove_bot(botid)
            await self._push_model(client_id, WsBotRemovedEvent(botid=botid, ts=int(time.time())))
            _logger.info("WS bot_removed: %s for client %s", botid, client_id)
        except Exception as exc:
            _logger.error("WS remove_bot failed for %s: %s", botid, exc)
            await self._push_model(client_id, WsErrorEvent(
                message="Bot removal failed", ts=int(time.time()),
            ))

    async def _handle_stop(self, client_id: str, botid: str, bot_manager: BotManager) -> None:
        try:
            await bot_manager.pause_bot(botid)
            await self._push_model(client_id, WsBotStoppedEvent(botid=botid, ts=int(time.time())))
            _logger.info("WS bot_stopped: %s for client %s", botid, client_id)
        except Exception as exc:
            _logger.error("WS stop_bot failed for %s: %s", botid, exc)
            await self._push_model(client_id, WsErrorEvent(
                message="Bot stop failed", ts=int(time.time()),
            ))

    async def _handle_set_simulation(
        self, client_id: str, botid: str, value: bool, bot_manager: BotManager
    ) -> None:
        try:
            await bot_manager.set_simulation_mode(botid, value)
        except Exception as exc:
            _logger.error("WS set_simulation failed for %s: %s", botid, exc)
            await self._push_model(client_id, WsErrorEvent(
                message="Set simulation failed", ts=int(time.time()),
            ))

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
                await websocket.send_text(orjson.dumps(event).decode())
            except TimeoutError:
                await websocket.send_text(
                    orjson.dumps(WsPingEvent(ts=int(time.time())).model_dump()).decode()
                )
            except Exception:
                break

    def _cleanup(self, client_id: str) -> None:
        self.connections.pop(client_id, None)
        self.queues.pop(client_id, None)
        # Detach log handler before cancelling tasks
        self._detach_log_handler(client_id)
        # Cancel any in-flight background tasks for this client
        for task in self._tasks.pop(client_id, []):
            if not task.done():
                task.cancel()
        _logger.info("Client %s disconnected", client_id)
