"""
Unit tests for BotManager — bot lifecycle, client isolation, asyncio.Lock safety,
and parameter hot-reload.
"""
from __future__ import annotations
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sonarft_manager import BotManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager() -> BotManager:
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return BotManager(logger=logger)


def _make_bot(botid: str = "bot-001") -> MagicMock:
    bot = MagicMock()
    bot.botid = botid
    bot.stop_bot = AsyncMock(return_value=None)
    bot.run_bot = AsyncMock(return_value=None)
    bot.apply_parameters = MagicMock()
    return bot


# ---------------------------------------------------------------------------
# 1. Initialisation
# ---------------------------------------------------------------------------

class TestBotManagerInit:

    def test_starts_empty(self):
        mgr = _make_manager()
        assert mgr._bots == {}
        assert mgr._clients == {}

    def test_accepts_logger(self):
        logger = MagicMock()
        mgr = BotManager(logger=logger)
        assert mgr.logger is logger

    def test_no_logger_defaults_to_none(self):
        mgr = BotManager()
        assert mgr.logger is None


# ---------------------------------------------------------------------------
# 2. add_bot_instance / remove_bot_instance
# ---------------------------------------------------------------------------

class TestAddRemoveBotInstance:

    @pytest.mark.asyncio
    async def test_add_stores_bot_and_client_mapping(self):
        mgr = _make_manager()
        bot = _make_bot("bot-001")
        await mgr.add_bot_instance("client-a", "bot-001", bot)
        assert "bot-001" in mgr._bots
        assert "bot-001" in mgr._clients["client-a"]

    @pytest.mark.asyncio
    async def test_add_sanitizes_client_id(self):
        mgr = _make_manager()
        bot = _make_bot("bot-001")
        await mgr.add_bot_instance("client a!", "bot-001", bot)
        # sanitize_client_id strips non-alphanumeric except _ and -
        assert "clienta" in mgr._clients

    @pytest.mark.asyncio
    async def test_add_multiple_bots_same_client(self):
        mgr = _make_manager()
        for i in range(3):
            bot = _make_bot(f"bot-00{i}")
            await mgr.add_bot_instance("client-a", f"bot-00{i}", bot)
        assert len(mgr._clients["client-a"]) == 3

    @pytest.mark.asyncio
    async def test_remove_cleans_up_bots_and_clients(self):
        mgr = _make_manager()
        bot = _make_bot("bot-001")
        await mgr.add_bot_instance("client-a", "bot-001", bot)
        await mgr.remove_bot_instance("bot-001")
        assert "bot-001" not in mgr._bots
        assert "bot-001" not in mgr._clients.get("client-a", [])

    @pytest.mark.asyncio
    async def test_remove_calls_stop_bot(self):
        mgr = _make_manager()
        bot = _make_bot("bot-001")
        await mgr.add_bot_instance("client-a", "bot-001", bot)
        await mgr.remove_bot_instance("bot-001")
        bot.stop_bot.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_nonexistent_bot_is_safe(self):
        mgr = _make_manager()
        await mgr.remove_bot_instance("nonexistent")  # must not raise


# ---------------------------------------------------------------------------
# 3. get_botids
# ---------------------------------------------------------------------------

class TestGetBotids:

    @pytest.mark.asyncio
    async def test_returns_ids_for_client(self):
        mgr = _make_manager()
        bot = _make_bot("bot-001")
        await mgr.add_bot_instance("client-a", "bot-001", bot)
        assert mgr.get_botids("client-a") == ["bot-001"]

    def test_returns_empty_for_unknown_client(self):
        mgr = _make_manager()
        assert mgr.get_botids("unknown") == []

    @pytest.mark.asyncio
    async def test_client_isolation(self):
        mgr = _make_manager()
        await mgr.add_bot_instance("client-a", "bot-a1", _make_bot("bot-a1"))
        await mgr.add_bot_instance("client-b", "bot-b1", _make_bot("bot-b1"))
        assert mgr.get_botids("client-a") == ["bot-a1"]
        assert mgr.get_botids("client-b") == ["bot-b1"]


# ---------------------------------------------------------------------------
# 4. get_bot_instance
# ---------------------------------------------------------------------------

class TestGetBotInstance:

    @pytest.mark.asyncio
    async def test_returns_bot_by_id(self):
        mgr = _make_manager()
        bot = _make_bot("bot-001")
        await mgr.add_bot_instance("client-a", "bot-001", bot)
        result = await mgr.get_bot_instance("bot-001")
        assert result is bot

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_id(self):
        mgr = _make_manager()
        result = await mgr.get_bot_instance("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# 5. create_bot
# ---------------------------------------------------------------------------

class TestCreateBot:

    @pytest.mark.asyncio
    async def test_create_bot_stores_instance(self):
        mgr = _make_manager()
        mock_bot = _make_bot("uuid-001")
        mock_bot.create_bot = AsyncMock(return_value="uuid-001")

        with patch("sonarft_manager.SonarftBot", return_value=mock_bot), \
             patch("sonarft_manager.BotManager.parse_args") as mock_args:
            mock_args.return_value = MagicMock(library="ccxtpro", config="config_1")
            botid = await mgr.create_bot("client-a")

        assert botid == "uuid-001"
        assert "uuid-001" in mgr._bots
        assert "uuid-001" in mgr.get_botids("client-a")

    @pytest.mark.asyncio
    async def test_create_bot_handles_creation_error(self):
        from sonarft_bot import BotCreationError
        mgr = _make_manager()
        mock_bot = MagicMock()
        mock_bot.create_bot = AsyncMock(side_effect=BotCreationError("failed"))

        with patch("sonarft_manager.SonarftBot", return_value=mock_bot), \
             patch("sonarft_manager.BotManager.parse_args") as mock_args:
            mock_args.return_value = MagicMock(library="ccxtpro", config="config_1")
            result = await mgr.create_bot("client-a")

        assert result is None
        assert mgr._bots == {}


# ---------------------------------------------------------------------------
# 6. remove_bot
# ---------------------------------------------------------------------------

class TestRemoveBot:

    @pytest.mark.asyncio
    async def test_remove_bot_cleans_up(self):
        mgr = _make_manager()
        bot = _make_bot("bot-001")
        await mgr.add_bot_instance("client-a", "bot-001", bot)
        await mgr.remove_bot("bot-001")
        assert "bot-001" not in mgr._bots

    @pytest.mark.asyncio
    async def test_remove_nonexistent_bot_is_safe(self):
        mgr = _make_manager()
        await mgr.remove_bot("nonexistent")  # must not raise


# ---------------------------------------------------------------------------
# 7. reload_parameters
# ---------------------------------------------------------------------------

class TestReloadParameters:

    @pytest.mark.asyncio
    async def test_reload_propagates_to_all_client_bots(self):
        mgr = _make_manager()
        bot1 = _make_bot("bot-001")
        bot2 = _make_bot("bot-002")
        await mgr.add_bot_instance("client-a", "bot-001", bot1)
        await mgr.add_bot_instance("client-a", "bot-002", bot2)

        params = {"profit_percentage_threshold": 0.005, "trade_amount": 2.0}
        await mgr.reload_parameters("client-a", params)

        bot1.apply_parameters.assert_called_once_with(params)
        bot2.apply_parameters.assert_called_once_with(params)

    @pytest.mark.asyncio
    async def test_reload_does_not_affect_other_clients(self):
        mgr = _make_manager()
        bot_a = _make_bot("bot-a")
        bot_b = _make_bot("bot-b")
        await mgr.add_bot_instance("client-a", "bot-a", bot_a)
        await mgr.add_bot_instance("client-b", "bot-b", bot_b)

        await mgr.reload_parameters("client-a", {"trade_amount": 3.0})

        bot_a.apply_parameters.assert_called_once()
        bot_b.apply_parameters.assert_not_called()

    @pytest.mark.asyncio
    async def test_reload_unknown_client_is_safe(self):
        mgr = _make_manager()
        await mgr.reload_parameters("unknown-client", {"trade_amount": 1.0})


# ---------------------------------------------------------------------------
# 8. Concurrency — asyncio.Lock
# ---------------------------------------------------------------------------

class TestConcurrency:

    @pytest.mark.asyncio
    async def test_concurrent_add_does_not_corrupt_state(self):
        """Multiple concurrent add_bot_instance calls must not lose entries."""
        mgr = _make_manager()
        bots = [_make_bot(f"bot-{i:03d}") for i in range(10)]

        await asyncio.gather(*[
            mgr.add_bot_instance("client-a", f"bot-{i:03d}", bots[i])
            for i in range(10)
        ])

        assert len(mgr._bots) == 10
        assert len(mgr._clients["client-a"]) == 10

    @pytest.mark.asyncio
    async def test_concurrent_remove_does_not_raise(self):
        """Concurrent removes of the same bot must not raise."""
        mgr = _make_manager()
        bot = _make_bot("bot-001")
        await mgr.add_bot_instance("client-a", "bot-001", bot)

        # Both removes run concurrently — only one should actually remove
        await asyncio.gather(
            mgr.remove_bot_instance("bot-001"),
            mgr.remove_bot_instance("bot-001"),
            return_exceptions=True,
        )
        assert "bot-001" not in mgr._bots
