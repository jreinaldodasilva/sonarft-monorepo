"""
SonarFT Bot Service
Business logic layer between API endpoints and the bot engine.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import Request

from ..core.config import get_settings
from ..core.errors import (
    BotCreationFailedError,
    BotLimitExceededError,
    BotNotFoundError,
)

_logger = logging.getLogger(__name__)


class BotService:
    """
    Wraps the sonarft-bot BotManager.
    Imported lazily so the API can start even if the bot package
    is not yet installed (useful during development).
    """

    def __init__(self) -> None:
        from sonarft_helpers import SonarftHelpers
        from sonarft_manager import BotManager
        # Use a sonarft-namespaced logger so WsLogHandler._is_bot_record()
        # passes its records through to WebSocket clients.
        _bot_logger = logging.getLogger("sonarft.api_bridge")
        self._manager = BotManager(logger=_bot_logger)
        self._helpers = SonarftHelpers
        self._settings = get_settings()

    def get_botids(self, client_id: str) -> list[str]:
        return self._manager.get_botids(client_id)

    def _bot_owned_by(self, botid: str, client_id: str) -> bool:
        """Return True only if botid belongs to client_id."""
        return botid in self._manager.get_botids(client_id)

    async def create_bot(self, client_id: str) -> str:
        current = len(self.get_botids(client_id))
        if current >= self._settings.max_bots_per_client:
            raise BotLimitExceededError(self._settings.max_bots_per_client)
        # BotManager.create_bot() calls ccxt load_markets() via synchronous
        # REST — run it in a thread pool worker so the event loop stays
        # responsive during the 1-15 second market-load window.
        import asyncio as _asyncio
        loop = _asyncio.get_event_loop()
        botid = await loop.run_in_executor(
            None,
            lambda: _asyncio.run(self._manager.create_bot(client_id)),
        )
        if not botid:
            _logger.error("BotManager.create_bot returned None for client [redacted]")
            raise BotCreationFailedError("BotManager.create_bot returned None")
        _logger.info("Bot created: %s for client: [redacted]", botid)
        return botid

    async def run_bot(self, botid: str, client_id: str) -> None:
        if not self._bot_owned_by(botid, client_id):
            raise BotNotFoundError(botid)
        await self._manager.run_bot(botid)

    async def stop_bot(self, botid: str, client_id: str) -> None:
        """Pause the bot's run loop without deregistering it.
        The bot remains in the registry and can be restarted via run_bot.
        """
        if not self._bot_owned_by(botid, client_id):
            raise BotNotFoundError(botid)
        await self._manager.pause_bot(botid)
        _logger.info("Bot paused: %s for client: [redacted]", botid)

    async def remove_bot(self, botid: str, client_id: str) -> None:
        """Fully stop and deregister the bot."""
        if not self._bot_owned_by(botid, client_id):
            raise BotNotFoundError(botid)
        await self._manager.remove_bot(botid)
        _logger.info("Bot removed: %s for client: [redacted]", botid)

    async def set_simulation_mode(self, botid: str, value: bool) -> None:
        await self._manager.set_simulation_mode(botid, value)

    async def get_bot_status(self, botid: str, client_id: str) -> dict:
        """Return running/halted status for a bot owned by client_id."""
        if not self._bot_owned_by(botid, client_id):
            raise BotNotFoundError(botid)
        return await self._manager.get_bot_status(botid)

    async def get_orders(
        self,
        botid: str,
        client_id: str,
        limit: int = 100,
        offset: int = 0,
        from_ts: str | None = None,
        to_ts: str | None = None,
    ) -> list:
        if not self._bot_owned_by(botid, client_id):
            raise BotNotFoundError(botid)
        return await self._helpers._async_query("orders", botid, limit, offset, from_ts, to_ts)

    async def get_trades(
        self,
        botid: str,
        client_id: str,
        limit: int = 100,
        offset: int = 0,
        from_ts: str | None = None,
        to_ts: str | None = None,
    ) -> list:
        if not self._bot_owned_by(botid, client_id):
            raise BotNotFoundError(botid)
        return await self._helpers._async_query("trades", botid, limit, offset, from_ts, to_ts)


@lru_cache
def get_bot_service() -> BotService:
    """Fallback singleton — used by tests and when app.state is unavailable."""
    return BotService()


def get_bot_service_from_state(request: Request) -> BotService:
    """
    FastAPI dependency — reads BotService from app.state (set by lifespan).
    Returns 503 Service Unavailable if the service failed to initialise.
    Falls back to the lru_cache singleton if app.state is not populated
    (e.g. during testing with TestClient without lifespan).
    """
    from fastapi import HTTPException
    service = getattr(request.app.state, "bot_service", None)
    if service is None:
        # Check if we're in a test context (no lifespan) — fall back to singleton
        try:
            return get_bot_service()
        except Exception:
            raise HTTPException(
                status_code=503,
                detail="Bot service unavailable — check server logs",
                headers={"Retry-After": "30"},
            ) from None
    return service
