"""
Additional tests for Phase 4 features:
- SonarftHelpers SQLite persistence
- SonarftBot parameter hot-reload
- Emergency stop endpoint
"""
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# SonarftHelpers — SQLite persistence
# ---------------------------------------------------------------------------

class TestSonarftHelpersSQLite:

    def _make_helpers(self, tmp_path):
        from sonarft_helpers import SonarftHelpers, Trade
        # Point DB to a temp file so tests don't pollute sonarftdata/
        SonarftHelpers._DB_PATH = str(tmp_path / "test.db")
        helpers = SonarftHelpers(is_simulation_mode=True)
        return helpers, Trade

    @pytest.mark.asyncio
    async def test_save_and_retrieve_order(self, tmp_path):
        helpers, Trade = self._make_helpers(tmp_path)
        trade = Trade(
            position='', base='BTC', quote='USDT',
            buy_exchange='binance', sell_exchange='okx',
            buy_price=60000.0, sell_price=60200.0,
            buy_trade_amount=1.0, sell_trade_amount=1.0,
            executed_amount=1.0, buy_value=60000.0, sell_value=60200.0,
            buy_fee_rate=0.001, sell_fee_rate=0.001,
            buy_fee_base=0.0, buy_fee_quote=60.0, sell_fee_quote=60.2,
            profit=79.8, profit_percentage=0.00133,
        )
        await helpers.save_order_history(botid=12345, trade=trade, trade_position='LONG')
        orders = await helpers.get_orders(12345)
        assert len(orders) == 1
        assert orders[0]['base'] == 'BTC'
        assert orders[0]['position'] == 'LONG'

    @pytest.mark.asyncio
    async def test_save_and_retrieve_trade(self, tmp_path):
        helpers, Trade = self._make_helpers(tmp_path)
        trade = Trade(
            position='', base='ETH', quote='USDT',
            buy_exchange='binance', sell_exchange='okx',
            buy_price=3000.0, sell_price=3020.0,
            buy_trade_amount=1.0, sell_trade_amount=1.0,
            executed_amount=1.0, buy_value=3000.0, sell_value=3020.0,
            buy_fee_rate=0.001, sell_fee_rate=0.001,
            buy_fee_base=0.0, buy_fee_quote=3.0, sell_fee_quote=3.02,
            profit=13.98, profit_percentage=0.00466,
        )
        await helpers.save_trade_history(
            botid=12345, trade=trade,
            buy_order_id='buy_001', sell_order_id='sell_001',
            trade_position='LONG',
            order_buy_success=True, order_sell_success=True, trade_success=True
        )
        trades = await helpers.get_trades(12345)
        assert len(trades) == 1
        assert trades[0]['base'] == 'ETH'
        assert trades[0]['trade_success'] is True

    @pytest.mark.asyncio
    async def test_multiple_bots_isolated(self, tmp_path):
        helpers, Trade = self._make_helpers(tmp_path)
        trade = Trade(
            position='', base='BTC', quote='USDT',
            buy_exchange='binance', sell_exchange='okx',
            buy_price=60000.0, sell_price=60200.0,
            buy_trade_amount=1.0, sell_trade_amount=1.0,
            executed_amount=1.0, buy_value=60000.0, sell_value=60200.0,
            buy_fee_rate=0.001, sell_fee_rate=0.001,
            buy_fee_base=0.0, buy_fee_quote=60.0, sell_fee_quote=60.2,
            profit=79.8, profit_percentage=0.00133,
        )
        await helpers.save_order_history(botid=111, trade=trade, trade_position='LONG')
        await helpers.save_order_history(botid=222, trade=trade, trade_position='SHORT')

        orders_111 = await helpers.get_orders(111)
        orders_222 = await helpers.get_orders(222)
        assert len(orders_111) == 1
        assert len(orders_222) == 1
        assert orders_111[0]['position'] == 'LONG'
        assert orders_222[0]['position'] == 'SHORT'

    @pytest.mark.asyncio
    async def test_empty_botid_returns_empty_list(self, tmp_path):
        helpers, _ = self._make_helpers(tmp_path)
        orders = await helpers.get_orders(99999)
        assert orders == []


# ---------------------------------------------------------------------------
# SonarftBot — parameter hot-reload
# ---------------------------------------------------------------------------

class TestHotReload:

    def _make_bot(self):
        from sonarft_bot import SonarftBot
        bot = SonarftBot.__new__(SonarftBot)
        bot.logger = MagicMock()
        bot.botid = 1
        bot.strategy = 'market_making'
        bot.profit_percentage_threshold = 0.003
        bot.trade_amount = 1.0
        bot.is_simulating_trade = 1
        bot.max_daily_loss = 100.0
        bot.max_trade_amount = 0.0
        bot.max_orders_per_minute = 0
        bot.spread_increase_factor = 1.00072
        bot.spread_decrease_factor = 0.99936
        bot.sonarft_search = None
        bot.sonarft_execution = None
        bot.sonarft_prices = None
        return bot

    def test_apply_parameters_updates_threshold(self):
        bot = self._make_bot()
        bot.apply_parameters({'profit_percentage_threshold': 0.005})
        assert bot.profit_percentage_threshold == 0.005

    def test_apply_parameters_updates_trade_amount(self):
        bot = self._make_bot()
        bot.apply_parameters({'trade_amount': 2.0})
        assert bot.trade_amount == 2.0

    def test_apply_parameters_updates_simulation_mode(self):
        bot = self._make_bot()
        os.environ['SONARFT_ALLOW_LIVE'] = 'true'
        try:
            bot.apply_parameters({'is_simulating_trade': 0})
            assert bot.is_simulating_trade == 0
        finally:
            os.environ.pop('SONARFT_ALLOW_LIVE', None)

    def test_apply_parameters_updates_max_daily_loss(self):
        bot = self._make_bot()
        bot.apply_parameters({'max_daily_loss': 500.0})
        assert bot.max_daily_loss == 500.0

    def test_apply_parameters_propagates_to_search(self):
        bot = self._make_bot()
        search = MagicMock()
        search.trade_amount = 1.0
        search.profit_percentage_threshold = 0.003
        search.max_daily_loss = 100.0
        bot.sonarft_search = search
        bot.apply_parameters({'trade_amount': 3.0, 'profit_percentage_threshold': 0.01})
        assert search.trade_amount == 3.0
        assert search.profit_percentage_threshold == 0.01

    def test_apply_parameters_propagates_to_execution(self):
        bot = self._make_bot()
        execution = MagicMock()
        execution.is_simulation_mode = True
        execution.max_trade_amount = 0.0
        execution.max_orders_per_minute = 0
        bot.sonarft_execution = execution
        os.environ['SONARFT_ALLOW_LIVE'] = 'true'
        try:
            bot.apply_parameters({'is_simulating_trade': 0, 'max_trade_amount': 5.0})
            assert execution.is_simulation_mode is False
            assert execution.max_trade_amount == 5.0
        finally:
            os.environ.pop('SONARFT_ALLOW_LIVE', None)

    def test_apply_parameters_ignores_unknown_keys(self):
        bot = self._make_bot()
        # Should not raise
        bot.apply_parameters({'unknown_key': 'value', 'profit_percentage_threshold': 0.004})
        assert bot.profit_percentage_threshold == 0.004


# ---------------------------------------------------------------------------
# SonarftSearch — same-exchange guard
# ---------------------------------------------------------------------------

class TestSameExchangeGuard:

    @pytest.mark.asyncio
    async def test_same_exchange_combination_skipped(self):
        """process_symbol must skip buy==sell exchange combinations."""
        from unittest.mock import MagicMock

        from sonarft_search import TradeProcessor

        processor = TradeProcessor.__new__(TradeProcessor)
        processor.logger = MagicMock()
        processor.sonarft_math = MagicMock()
        processor.sonarft_prices = MagicMock()
        processor.sonarft_prices.get_the_latest_prices = AsyncMock(return_value=(
            [('binance', 60000.0, 60010.0, 60005.0, 'BTC/USDT')],
            [('binance', 59990.0, 60200.0, 60100.0, 'BTC/USDT')],  # same exchange
        ))
        processor.trade_validator = MagicMock()
        processor.trade_executor = MagicMock()
        processor.process_trade_combination = AsyncMock()

        symbol = {'base': 'BTC', 'quotes': ['USDT']}
        await processor.process_symbol(botid=1, symbol=symbol, trade_amount=1.0, percentage_threshold=0.003)

        # process_trade_combination should NOT be called for same-exchange pair
        processor.process_trade_combination.assert_not_called()


# ---------------------------------------------------------------------------
# T-04: StochRSI (0.0, 0.0) must not be treated as None
# ---------------------------------------------------------------------------

class TestStochRSITruthinessfix:

    @pytest.mark.asyncio
    async def test_stoch_zero_zero_not_treated_as_none(self):
        """(0.0, 0.0) is a valid extreme oversold signal — must not fall back to 50.0."""
        from unittest.mock import MagicMock

        from sonarft_prices import SonarftPrices

        ORDER_BOOK = {
            'bids': [[60000.0, 1.0], [59990.0, 2.0], [59980.0, 0.5]],
            'asks': [[60010.0, 1.5], [60020.0, 0.5], [60030.0, 1.0]],
        }
        ind = MagicMock()
        ind.market_movement = AsyncMock(return_value=('slow', 'bear'))
        ind.get_market_direction = AsyncMock(return_value='bear')
        ind.get_rsi = AsyncMock(return_value=25.0)
        ind.get_stoch_rsi = AsyncMock(return_value=(0.0, 0.0))  # extreme oversold
        ind.get_short_term_market_trend = AsyncMock(return_value='bear')
        ind.get_volatility = AsyncMock(return_value=0.5)
        ind.get_order_book = AsyncMock(return_value=ORDER_BOOK)
        ind.get_support_price = AsyncMock(return_value=None)
        ind.get_resistance_price = AsyncMock(return_value=None)
        ind.get_macd = AsyncMock(return_value=(1.0, 0.5, 0.5))

        api = MagicMock()
        prices = SonarftPrices(api, ind)
        prices.active_indicators = ['rsi', 'stoch rsi', 'macd']

        buy, sell, indicators = await prices.weighted_adjust_prices(
            1, 'binance', 'okx', 'BTC', 'USDT', 60000.0, 60200.0, 60005.0, 60100.0
        )
        # With stoch_rsi active and returning (0.0, 0.0), prices should be valid
        assert buy > 0
        assert sell > 0
        # The actual k/d values in indicators must be 0.0, not the 50.0 fallback
        assert indicators['market_stoch_rsi_buy_k'] == 0.0
        assert indicators['market_stoch_rsi_buy_d'] == 0.0


# ---------------------------------------------------------------------------
# T-05: SQL table allowlist
# ---------------------------------------------------------------------------

class TestSQLTableAllowlist:

    def _make_helpers(self, tmp_path):
        from sonarft_helpers import SonarftHelpers
        SonarftHelpers._DB_PATH = str(tmp_path / "test.db")
        return SonarftHelpers(is_simulation_mode=True)

    @pytest.mark.asyncio
    async def test_valid_table_names_accepted(self, tmp_path):
        helpers = self._make_helpers(tmp_path)
        # These should not raise
        for table in ('orders', 'trades'):
            helpers._db_insert(table, 'bot1', '2025-01-01', {'test': True})

    @pytest.mark.asyncio
    async def test_invalid_table_name_raises(self, tmp_path):
        helpers = self._make_helpers(tmp_path)
        with pytest.raises(ValueError, match="Invalid table name"):
            helpers._db_insert('malicious; DROP TABLE orders; --', 'bot1', '', {})

    @pytest.mark.asyncio
    async def test_invalid_table_query_raises(self, tmp_path):
        helpers = self._make_helpers(tmp_path)
        with pytest.raises(ValueError, match="Invalid table name"):
            helpers._db_query('unknown_table', 'bot1')

    @pytest.mark.asyncio
    async def test_invalid_table_purge_raises(self, tmp_path):
        helpers = self._make_helpers(tmp_path)
        with pytest.raises(ValueError, match="Invalid table name"):
            helpers._db_purge('unknown_table', 'bot1')


# ---------------------------------------------------------------------------
# T-06: Persistent position tracker
# ---------------------------------------------------------------------------

class TestPositionTracker:

    def _make_helpers(self, tmp_path):
        from sonarft_helpers import SonarftHelpers
        SonarftHelpers._DB_PATH = str(tmp_path / "test.db")
        return SonarftHelpers(is_simulation_mode=True)

    @pytest.mark.asyncio
    async def test_open_position_recorded(self, tmp_path):
        helpers = self._make_helpers(tmp_path)
        await helpers.open_position(
            botid='bot-1', order_id='order-001',
            exchange='binance', symbol='BTC/USDT',
            side='long', amount=0.01, entry_price=60000.0,
        )
        positions = await helpers.get_open_positions('bot-1')
        assert len(positions) == 1
        assert positions[0]['order_id'] == 'order-001'
        assert positions[0]['side'] == 'long'
        assert positions[0]['status'] == 'open'

    @pytest.mark.asyncio
    async def test_close_position_marks_closed(self, tmp_path):
        helpers = self._make_helpers(tmp_path)
        await helpers.open_position(
            botid='bot-1', order_id='order-001',
            exchange='binance', symbol='BTC/USDT',
            side='long', amount=0.01, entry_price=60000.0,
        )
        await helpers.close_position(botid='bot-1', order_id='order-001')
        positions = await helpers.get_open_positions('bot-1')
        assert len(positions) == 0  # no open positions remain

    @pytest.mark.asyncio
    async def test_multiple_bots_isolated(self, tmp_path):
        helpers = self._make_helpers(tmp_path)
        await helpers.open_position(
            botid='bot-1', order_id='order-A',
            exchange='binance', symbol='BTC/USDT',
            side='long', amount=0.01, entry_price=60000.0,
        )
        await helpers.open_position(
            botid='bot-2', order_id='order-B',
            exchange='okx', symbol='ETH/USDT',
            side='short', amount=0.1, entry_price=3000.0,
        )
        pos_1 = await helpers.get_open_positions('bot-1')
        pos_2 = await helpers.get_open_positions('bot-2')
        assert len(pos_1) == 1 and pos_1[0]['order_id'] == 'order-A'
        assert len(pos_2) == 1 and pos_2[0]['order_id'] == 'order-B'

    @pytest.mark.asyncio
    async def test_no_open_positions_returns_empty(self, tmp_path):
        helpers = self._make_helpers(tmp_path)
        positions = await helpers.get_open_positions('bot-unknown')
        assert positions == []

    @pytest.mark.asyncio
    async def test_duplicate_open_ignored(self, tmp_path):
        """INSERT OR IGNORE prevents duplicate position records."""
        helpers = self._make_helpers(tmp_path)
        await helpers.open_position(
            botid='bot-1', order_id='order-001',
            exchange='binance', symbol='BTC/USDT',
            side='long', amount=0.01, entry_price=60000.0,
        )
        # Second call with same order_id must not raise or duplicate
        await helpers.open_position(
            botid='bot-1', order_id='order-001',
            exchange='binance', symbol='BTC/USDT',
            side='long', amount=0.01, entry_price=60000.0,
        )
        positions = await helpers.get_open_positions('bot-1')
        assert len(positions) == 1

    @pytest.mark.asyncio
    async def test_execute_long_trade_opens_and_closes_position(self, tmp_path):
        """Integration: execute_long_trade() opens position on buy fill, closes on sell fill."""
        from unittest.mock import MagicMock

        from sonarft_execution import SonarftExecution
        from sonarft_helpers import SonarftHelpers

        SonarftHelpers._DB_PATH = str(tmp_path / "test.db")
        helpers = SonarftHelpers(is_simulation_mode=True)

        api = MagicMock()
        api.markets = {}
        api.get_symbol_precision = MagicMock(return_value=None)
        execution = SonarftExecution(api, helpers, is_simulation_mode=True)

        # Simulate full fills on both legs
        async def mock_execute(exchange_id, base, quote, side, amount, price, monitor):
            return f'{side}_001', amount, 0  # full fill, no remaining

        execution.execute_order = mock_execute

        result_buy, result_sell = await execution.execute_long_trade(
            'bot-test-uuid', 'binance', 'okx', 'BTC', 'USDT', 0.01, 0.01, 60000.0, 60200.0
        )

        # Both legs should have results
        assert result_buy is not None
        assert result_sell is not None

        # Position should be closed (opened then closed)
        positions = await helpers.get_open_positions('binance')
        assert len(positions) == 0  # closed after second leg


# ---------------------------------------------------------------------------
# T02: max_total_exposure tracking
# ---------------------------------------------------------------------------

class TestExposureTracking:
    """T02: _current_exposure is incremented before execution and decremented
    after, making max_total_exposure actually enforce a cap across concurrent
    trades."""

    def _make_execution(self, max_exposure: float) -> "SonarftExecution":
        from sonarft_execution import SonarftExecution
        from unittest.mock import AsyncMock, MagicMock
        api = MagicMock()
        api.markets = {}
        api.create_order = AsyncMock(return_value={"id": "order_001"})
        api.cancel_order = AsyncMock(return_value={"id": "order_001", "status": "canceled"})
        api.get_balance = AsyncMock(return_value={"free": {"BTC": 10.0, "USDT": 1_000_000.0}})
        api.watch_orders = AsyncMock(return_value=[])
        helpers = MagicMock()
        helpers.save_order_history = AsyncMock()
        helpers.save_trade_history = AsyncMock()
        helpers.open_position = AsyncMock()
        helpers.close_position = AsyncMock()
        return SonarftExecution(
            api, helpers, is_simulation_mode=True,
            max_total_exposure=max_exposure,
        )

    def _trade(self, amount: float = 1.0, price: float = 100.0) -> dict:
        return {
            "position": "", "base": "BTC", "quote": "USDT",
            "buy_exchange": "binance", "sell_exchange": "okx",
            "buy_price": price, "sell_price": price * 1.005,
            "buy_trade_amount": amount, "sell_trade_amount": amount,
            "executed_amount": amount,
            "buy_value": amount * price, "sell_value": amount * price * 1.005,
            "buy_fee_rate": 0.001, "sell_fee_rate": 0.001,
            "buy_fee_base": 0, "buy_fee_quote": amount * price * 0.001,
            "sell_fee_quote": amount * price * 1.005 * 0.001,
            "profit": amount * price * 0.003, "profit_percentage": 0.003,
            "market_direction_buy": "bull", "market_direction_sell": "bull",
            "market_rsi_buy": 50.0, "market_rsi_sell": 50.0,
            "market_stoch_rsi_buy_k": 50.0, "market_stoch_rsi_buy_d": 45.0,
            "market_stoch_rsi_sell_k": 50.0, "market_stoch_rsi_sell_d": 45.0,
        }

    @pytest.mark.asyncio
    async def test_exposure_disabled_when_zero(self):
        """max_total_exposure=0 disables the cap — all trades pass."""
        ex = self._make_execution(max_exposure=0.0)
        result = await ex.execute_trade("bot-1", self._trade(amount=1000.0, price=1000.0))
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_first_trade_within_cap_passes(self):
        """A single trade whose value is below the cap must be allowed."""
        ex = self._make_execution(max_exposure=200.0)
        # trade_value = 1.0 * 100.0 = 100 < 200
        result = await ex.execute_trade("bot-1", self._trade(amount=1.0, price=100.0))
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_trade_exceeding_cap_blocked(self):
        """A single trade whose value exceeds the cap must be blocked."""
        ex = self._make_execution(max_exposure=50.0)
        # trade_value = 1.0 * 100.0 = 100 > 50
        result = await ex.execute_trade("bot-1", self._trade(amount=1.0, price=100.0))
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_exposure_accumulates_across_concurrent_trades(self):
        """Two concurrent trades whose combined value exceeds the cap:
        the second must be blocked once the first has incremented exposure."""
        import asyncio
        ex = self._make_execution(max_exposure=150.0)
        # Each trade_value = 1.0 * 100.0 = 100; combined = 200 > 150

        # Gate that holds the first trade's _execute_single_trade open
        # until the second trade has had a chance to check exposure.
        first_started = asyncio.Event()
        release_first = asyncio.Event()

        original_execute = ex._execute_single_trade

        call_count = {"n": 0}

        async def gated_execute(botid, trade):
            call_count["n"] += 1
            if call_count["n"] == 1:
                first_started.set()          # signal: first trade is inside execution
                await release_first.wait()   # hold until we release it
            return await original_execute(botid, trade)

        ex._execute_single_trade = gated_execute

        async def run_first():
            return await ex.execute_trade("bot-1", self._trade(amount=1.0, price=100.0))

        async def run_second():
            await first_started.wait()   # wait until first trade has incremented exposure
            result = await ex.execute_trade("bot-1", self._trade(amount=1.0, price=100.0))
            release_first.set()          # let the first trade finish
            return result

        result_first, result_second = await asyncio.gather(run_first(), run_second())

        # First trade succeeds; second is blocked by the cap
        assert result_first["success"] is True
        assert result_second["success"] is False

    @pytest.mark.asyncio
    async def test_exposure_decremented_after_trade_completes(self):
        """After a trade finishes, _current_exposure must return to 0."""
        ex = self._make_execution(max_exposure=200.0)
        await ex.execute_trade("bot-1", self._trade(amount=1.0, price=100.0))
        assert ex._current_exposure == 0.0

    @pytest.mark.asyncio
    async def test_exposure_decremented_after_trade_fails(self):
        """Even if execution raises, _current_exposure must be decremented."""
        from unittest.mock import AsyncMock
        ex = self._make_execution(max_exposure=200.0)
        # Force _execute_single_trade to raise
        ex._execute_single_trade = AsyncMock(side_effect=RuntimeError("boom"))
        result = await ex.execute_trade("bot-1", self._trade(amount=1.0, price=100.0))
        assert result["success"] is False
        assert ex._current_exposure == 0.0
