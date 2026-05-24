"""
Unit tests for SonarftHelpers — SQLite persistence, position tracker,
purge, and backup. Covers T17 from the implementation roadmap.

Each test uses a tmp_path-scoped database so tests are fully isolated.
"""
import asyncio
import json
import os

import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_helpers(tmp_path):
    """Build a SonarftHelpers instance backed by a temp SQLite database."""
    from sonarft_helpers import SonarftHelpers
    SonarftHelpers._DB_PATH = str(tmp_path / "test.db")
    helpers = SonarftHelpers(is_simulation_mode=True)
    return helpers


def _trade_info(botid="bot-1", profit=5.0):
    return {
        "timestamp": "2025-01-01T00:00:00",
        "position": "LONG",
        "base": "BTC", "quote": "USDT",
        "buy_exchange": "binance", "sell_exchange": "okx",
        "buy_price": 60000.0, "sell_price": 60200.0,
        "buy_trade_amount": 0.01, "sell_trade_amount": 0.01,
        "executed_amount": 0.01,
        "buy_value": 600.0, "sell_value": 602.0,
        "buy_fee_rate": 0.001, "sell_fee_rate": 0.001,
        "buy_fee_base": 0.0, "buy_fee_quote": 0.6, "sell_fee_quote": 0.602,
        "profit": profit, "profit_percentage": 0.00133,
        "order_buy_success": True, "order_sell_success": True, "trade_success": True,
    }


# ---------------------------------------------------------------------------
# T17-A: Order and trade CRUD
# ---------------------------------------------------------------------------

class TestOrderTradeCRUD:

    @pytest.mark.asyncio
    async def test_save_and_retrieve_order(self, tmp_path):
        """Saved order must be retrievable by botid."""
        helpers = _make_helpers(tmp_path)
        info = _trade_info()
        await helpers.save_order_data("bot-1", info)

        orders = await helpers.get_orders("bot-1")
        assert len(orders) == 1
        assert orders[0]["profit"] == 5.0

    @pytest.mark.asyncio
    async def test_save_and_retrieve_trade(self, tmp_path):
        """Saved trade must be retrievable by botid."""
        helpers = _make_helpers(tmp_path)
        info = _trade_info()
        await helpers.save_trade_data("bot-1", info)

        trades = await helpers.get_trades("bot-1")
        assert len(trades) == 1
        assert trades[0]["buy_exchange"] == "binance"

    @pytest.mark.asyncio
    async def test_multiple_bots_isolated(self, tmp_path):
        """Records for bot-1 must not appear in bot-2 queries."""
        helpers = _make_helpers(tmp_path)
        await helpers.save_order_data("bot-1", _trade_info("bot-1"))
        await helpers.save_order_data("bot-2", _trade_info("bot-2", profit=99.0))

        bot1_orders = await helpers.get_orders("bot-1")
        bot2_orders = await helpers.get_orders("bot-2")

        assert len(bot1_orders) == 1
        assert len(bot2_orders) == 1
        assert bot1_orders[0]["profit"] == 5.0
        assert bot2_orders[0]["profit"] == 99.0

    @pytest.mark.asyncio
    async def test_empty_botid_returns_empty_list(self, tmp_path):
        """Querying a botid with no records must return an empty list."""
        helpers = _make_helpers(tmp_path)
        orders = await helpers.get_orders("nonexistent-bot")
        assert orders == []

    @pytest.mark.asyncio
    async def test_multiple_records_returned_most_recent_first(self, tmp_path):
        """get_orders returns records in descending insertion order."""
        helpers = _make_helpers(tmp_path)
        for i in range(3):
            info = _trade_info(profit=float(i))
            await helpers.save_order_data("bot-1", info)

        orders = await helpers.get_orders("bot-1")
        assert len(orders) == 3
        # Most recent first (profit=2 was inserted last)
        assert orders[0]["profit"] == 2.0


# ---------------------------------------------------------------------------
# T17-B: Purge history
# ---------------------------------------------------------------------------

class TestPurgeHistory:

    @pytest.mark.asyncio
    async def test_purge_keeps_last_n_records(self, tmp_path):
        """After purge(keep_last=3), only 3 most recent records remain."""
        helpers = _make_helpers(tmp_path)
        for i in range(5):
            await helpers.save_order_data("bot-1", _trade_info(profit=float(i)))

        await helpers.purge_history("bot-1", keep_last=3)

        orders = await helpers.get_orders("bot-1")
        assert len(orders) == 3

    @pytest.mark.asyncio
    async def test_purge_does_not_affect_other_bots(self, tmp_path):
        """Purging bot-1 must not remove bot-2 records."""
        helpers = _make_helpers(tmp_path)
        for i in range(5):
            await helpers.save_order_data("bot-1", _trade_info(profit=float(i)))
        await helpers.save_order_data("bot-2", _trade_info("bot-2", profit=99.0))

        await helpers.purge_history("bot-1", keep_last=2)

        bot2_orders = await helpers.get_orders("bot-2")
        assert len(bot2_orders) == 1


# ---------------------------------------------------------------------------
# T17-C: Position tracker
# ---------------------------------------------------------------------------

class TestPositionTracker:

    @pytest.mark.asyncio
    async def test_open_position_recorded(self, tmp_path):
        """open_position must create a record with status='open'."""
        helpers = _make_helpers(tmp_path)
        await helpers.open_position(
            botid="bot-1", order_id="order-001",
            exchange="binance", symbol="BTC/USDT",
            side="long", amount=0.01, entry_price=60000.0,
        )

        positions = await helpers.get_open_positions("bot-1")
        assert len(positions) == 1
        assert positions[0]["order_id"] == "order-001"
        assert positions[0]["status"] == "open"

    @pytest.mark.asyncio
    async def test_close_position_marks_closed(self, tmp_path):
        """close_position must update status to 'closed'."""
        helpers = _make_helpers(tmp_path)
        await helpers.open_position(
            botid="bot-1", order_id="order-001",
            exchange="binance", symbol="BTC/USDT",
            side="long", amount=0.01, entry_price=60000.0,
        )
        await helpers.close_position(botid="bot-1", order_id="order-001")

        open_positions = await helpers.get_open_positions("bot-1")
        assert len(open_positions) == 0

    @pytest.mark.asyncio
    async def test_get_open_positions_excludes_closed(self, tmp_path):
        """get_open_positions must not return closed positions."""
        helpers = _make_helpers(tmp_path)
        await helpers.open_position(
            botid="bot-1", order_id="order-open",
            exchange="binance", symbol="BTC/USDT",
            side="long", amount=0.01, entry_price=60000.0,
        )
        await helpers.open_position(
            botid="bot-1", order_id="order-closed",
            exchange="okx", symbol="ETH/USDT",
            side="short", amount=0.1, entry_price=2000.0,
        )
        await helpers.close_position(botid="bot-1", order_id="order-closed")

        open_positions = await helpers.get_open_positions("bot-1")
        assert len(open_positions) == 1
        assert open_positions[0]["order_id"] == "order-open"

    @pytest.mark.asyncio
    async def test_duplicate_open_ignored(self, tmp_path):
        """Opening the same order_id twice must not create a duplicate record."""
        helpers = _make_helpers(tmp_path)
        await helpers.open_position(
            botid="bot-1", order_id="order-001",
            exchange="binance", symbol="BTC/USDT",
            side="long", amount=0.01, entry_price=60000.0,
        )
        # Second open with same order_id — INSERT OR IGNORE
        await helpers.open_position(
            botid="bot-1", order_id="order-001",
            exchange="binance", symbol="BTC/USDT",
            side="long", amount=0.02, entry_price=61000.0,
        )

        positions = await helpers.get_open_positions("bot-1")
        assert len(positions) == 1
        assert positions[0]["amount"] == 0.01  # original amount preserved

    @pytest.mark.asyncio
    async def test_no_open_positions_returns_empty(self, tmp_path):
        """get_open_positions for a bot with no positions returns []."""
        helpers = _make_helpers(tmp_path)
        positions = await helpers.get_open_positions("bot-1")
        assert positions == []


# ---------------------------------------------------------------------------
# T17-D: Database backup
# ---------------------------------------------------------------------------

class TestDatabaseBackup:

    @pytest.mark.asyncio
    async def test_backup_creates_readable_file(self, tmp_path):
        """backup_db must create a valid SQLite file at dst_path."""
        import sqlite3
        helpers = _make_helpers(tmp_path)
        # Write some data so the DB is non-trivial
        await helpers.save_order_data("bot-1", _trade_info())

        backup_path = str(tmp_path / "backup.db")
        await helpers.async_backup_db(backup_path)

        assert os.path.exists(backup_path)
        # Verify the backup is a readable SQLite database
        with sqlite3.connect(backup_path) as conn:
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "orders" in tables
        assert "trades" in tables
        assert "positions" in tables

    @pytest.mark.asyncio
    async def test_backup_contains_saved_data(self, tmp_path):
        """Backup must contain the same records as the source database."""
        import sqlite3
        helpers = _make_helpers(tmp_path)
        await helpers.save_order_data("bot-1", _trade_info(profit=42.0))

        backup_path = str(tmp_path / "backup.db")
        await helpers.async_backup_db(backup_path)

        with sqlite3.connect(backup_path) as conn:
            rows = conn.execute(
                "SELECT data FROM orders WHERE botid = 'bot-1'"
            ).fetchall()
        assert len(rows) == 1
        data = json.loads(rows[0][0])
        assert data["profit"] == 42.0
