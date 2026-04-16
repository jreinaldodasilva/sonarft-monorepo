"""
SonarFT Bot Service
Business logic layer between API endpoints and the bot engine.
"""
from __future__ import annotations
import asyncio
import logging
from functools import lru_cache
from typing import Optional

from ..core.config import get_settings
from ..core.errors import BotNotFoundError, BotLimitExceededError

_logger = logging.getLogger(__name__)


class BotService:
    """
    Wraps the sonarft-bot BotManager.
    Imported lazily so the API can start even if the bot package
    is not yet installed (useful during development).
    """

    def __init__(self) -> None:
        from sonarft_manager import BotManager  # type: ignore[import]
        from sonarft_helpers import SonarftHelpers  # type: ignore[import]
        self._manager = BotManager()
        self._helpers = SonarftHelpers
        self._settings = get_settings()

    def get_botids(self, client_id: str) -> list[str]:
        return self._manager.get_botids(client_id)

    async def create_bot(self, client_id: str) -> str:
        current = len(self.get_botids(client_id))
        if current >= self._settings.max_bots_per_client:
            raise BotLimitExceededError(self._settings.max_bots_per_client)
        await self._manager.create_bot(client_id)
        ids = self.get_botids(client_id)
        return ids[-1] if ids else client_id

    async def run_bot(self, botid: str) -> None:
        await self._manager.run_bot(botid)

    async def stop_bot(self, botid: str) -> None:
        if not self._bot_exists(botid):
            raise BotNotFoundError(botid)
        await self._manager.remove_bot(botid)

    async def remove_bot(self, botid: str) -> None:
        if not self._bot_exists(botid):
            raise BotNotFoundError(botid)
        await self._manager.remove_bot(botid)

    async def set_simulation_mode(self, botid: str, value: bool) -> None:
        await self._manager.set_simulation_mode(botid, value)

    async def get_orders(self, botid: str) -> list:
        return await self._helpers._async_query("orders", botid)

    async def get_trades(self, botid: str) -> list:
        return await self._helpers._async_query("trades", botid)

    def _bot_exists(self, botid: str) -> bool:
        for ids in self._manager._clients.values():
            if botid in ids:
                return True
        return False


@lru_cache
def get_bot_service() -> BotService:
    return BotService()
