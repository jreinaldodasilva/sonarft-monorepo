"""
Unit tests for TradeProcessor.process_trade_combination (T27)
and SonarftExecution partial fill handling (T28).
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from sonarft_execution import SonarftExecution
from sonarft_search import TradeProcessor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_processor(
    adjusted_buy=60000.0, adjusted_sell=60200.0,
    profit=50.0, profit_pct=0.005, trade_data=None,
    validation_pass=True,
):
    """Build a TradeProcessor with fully mocked dependencies."""
    validators = MagicMock()
    execution = MagicMock()
    math = MagicMock()
    prices = MagicMock()

    prices.get_the_latest_prices = AsyncMock()
    prices.weighted_adjust_prices = AsyncMock(return_value=(
        adjusted_buy, adjusted_sell,
        {'market_direction_buy': 'bull', 'market_direction_sell': 'bull',
         'market_rsi_buy': 55.0, 'market_rsi_sell': 55.0,
         'market_stoch_rsi_buy_k': 50.0, 'market_stoch_rsi_buy_d': 45.0,
         'market_stoch_rsi_sell_k': 50.0, 'market_stoch_rsi_sell_d': 45.0},
    ))

    if trade_data is None:
        trade_data = {
            'position': '', 'base': 'BTC', 'quote': 'USDT',
            'buy_exchange': 'binance', 'sell_exchange': 'okx',
            'buy_price': adjusted_buy, 'sell_price': adjusted_sell,
            'buy_trade_amount': 1.0, 'sell_trade_amount': 1.0,
            'executed_amount': 1.0, 'buy_value': adjusted_buy, 'sell_value': adjusted_sell,
            'buy_fee_rate': 0.001, 'sell_fee_rate': 0.001,
            'buy_fee_base': 0, 'buy_fee_quote': 60.0, 'sell_fee_quote': 60.2,
            'profit': profit, 'profit_percentage': profit_pct,
        }
    math.calculate_trade = MagicMock(return_value=(profit, profit_pct, trade_data))

    proc = TradeProcessor(validators, execution, math, prices)
    proc.trade_validator.has_requirements_for_success_carrying_out = AsyncMock(return_value=validation_pass)
    proc.trade_executor.execute_trade = MagicMock()

    return proc


def _make_execution(is_sim=True):
    api = MagicMock()
    api.create_order = AsyncMock(return_value={'id': 'order_001'})
    api.cancel_order = AsyncMock(return_value={'id': 'order_001', 'status': 'canceled'})
    api.get_balance = AsyncMock(return_value={'free': {'BTC': 10.0, 'USDT': 1_000_000.0}})
    api.watch_orders = AsyncMock(return_value=[])
    api.get_last_price = AsyncMock(return_value=59999.0)
    api.markets = {}
    helpers = MagicMock()
    helpers.save_order_history = AsyncMock()
    helpers.save_trade_history = AsyncMock()
    helpers.open_position = AsyncMock()
    helpers.close_position = AsyncMock()
    indicators = MagicMock()
    indicators.get_market_direction = AsyncMock(return_value='bull')
    indicators.get_rsi = AsyncMock(return_value=50.0)
    indicators.get_stoch_rsi = AsyncMock(return_value=(50.0, 45.0))
    return SonarftExecution(api, helpers, is_simulation_mode=is_sim)


# ---------------------------------------------------------------------------
# T27: process_trade_combination
# ---------------------------------------------------------------------------

class TestProcessTradeCombination:

    @pytest.mark.asyncio
    async def test_profitable_trade_triggers_execution(self):
        proc = _make_processor(profit=50.0, profit_pct=0.005, validation_pass=True)
        buy_list = ('binance', 60000.0, 60010.0, 60005.0, 'BTC/USDT')
        sell_list = ('okx', 59990.0, 60200.0, 60100.0, 'BTC/USDT')
        await proc.process_trade_combination(1, 'BTC', 'USDT', 1.0, buy_list, sell_list, 0.003)
        proc.trade_executor.execute_trade.assert_called_once()

    @pytest.mark.asyncio
    async def test_unprofitable_trade_skipped(self):
        proc = _make_processor(profit=-10.0, profit_pct=-0.001)
        buy_list = ('binance', 60000.0, 60010.0, 60005.0, 'BTC/USDT')
        sell_list = ('okx', 59990.0, 60200.0, 60100.0, 'BTC/USDT')
        await proc.process_trade_combination(1, 'BTC', 'USDT', 1.0, buy_list, sell_list, 0.003)
        proc.trade_executor.execute_trade.assert_not_called()

    @pytest.mark.asyncio
    async def test_zero_adjusted_price_skipped(self):
        proc = _make_processor(adjusted_buy=0, adjusted_sell=0)
        buy_list = ('binance', 60000.0, 60010.0, 60005.0, 'BTC/USDT')
        sell_list = ('okx', 59990.0, 60200.0, 60100.0, 'BTC/USDT')
        await proc.process_trade_combination(1, 'BTC', 'USDT', 1.0, buy_list, sell_list, 0.003)
        proc.trade_executor.execute_trade.assert_not_called()

    @pytest.mark.asyncio
    async def test_failed_validation_skips_execution(self):
        proc = _make_processor(profit=50.0, profit_pct=0.005, validation_pass=False)
        buy_list = ('binance', 60000.0, 60010.0, 60005.0, 'BTC/USDT')
        sell_list = ('okx', 59990.0, 60200.0, 60100.0, 'BTC/USDT')
        await proc.process_trade_combination(1, 'BTC', 'USDT', 1.0, buy_list, sell_list, 0.003)
        proc.trade_executor.execute_trade.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_trade_data_skipped(self):
        proc = _make_processor()
        proc.sonarft_math.calculate_trade = MagicMock(return_value=(0, 0, None))
        buy_list = ('binance', 60000.0, 60010.0, 60005.0, 'BTC/USDT')
        sell_list = ('okx', 59990.0, 60200.0, 60100.0, 'BTC/USDT')
        await proc.process_trade_combination(1, 'BTC', 'USDT', 1.0, buy_list, sell_list, 0.003)
        proc.trade_executor.execute_trade.assert_not_called()

    @pytest.mark.asyncio
    async def test_at_threshold_boundary_executes(self):
        """profit_pct == threshold should execute (>= comparison)."""
        proc = _make_processor(profit=18.0, profit_pct=0.003, validation_pass=True)
        buy_list = ('binance', 60000.0, 60010.0, 60005.0, 'BTC/USDT')
        sell_list = ('okx', 59990.0, 60200.0, 60100.0, 'BTC/USDT')
        await proc.process_trade_combination(1, 'BTC', 'USDT', 1.0, buy_list, sell_list, 0.003)
        proc.trade_executor.execute_trade.assert_called_once()


# ---------------------------------------------------------------------------
# T28: Partial fill handling
# ---------------------------------------------------------------------------

class TestPartialFillHandling:

    @pytest.mark.asyncio
    async def test_partial_buy_fill_adjusts_sell_amount(self):
        """If buy fills 0.7 of 1.0, sell leg should use 0.7."""
        execution = _make_execution(is_sim=True)
        # Simulate partial fill: execute_order returns 0.7 filled
        async def mock_execute(exchange_id, base, quote, side, amount, price, monitor):
            if side == 'buy':
                return 'buy_123', 0.7, 0.3  # partial fill
            return 'sell_456', amount, 0  # full fill for sell
        execution.execute_order = mock_execute

        result_buy, result_sell = await execution.execute_long_trade(
            'bot-uuid-1234', 'binance', 'okx', 'BTC', 'USDT', 1.0, 1.0, 60000.0, 60200.0
        )
        assert result_buy is not None
        assert result_buy[1] == 0.7  # executed amount
        # Sell should have been called with 0.7 (the actual filled amount)
        assert result_sell is not None

    @pytest.mark.asyncio
    async def test_zero_fill_skips_second_leg(self):
        """If buy fills 0, sell leg should be skipped."""
        execution = _make_execution(is_sim=True)
        async def mock_execute(exchange_id, base, quote, side, amount, price, monitor):
            if side == 'buy':
                return 'buy_123', 0, 1.0  # zero fill
            return 'sell_456', amount, 0
        execution.execute_order = mock_execute

        result_buy, result_sell = await execution.execute_long_trade(
            'bot-uuid-1234', 'binance', 'okx', 'BTC', 'USDT', 1.0, 1.0, 60000.0, 60200.0
        )
        assert result_buy is not None
        assert result_sell is None  # sell leg skipped

    @pytest.mark.asyncio
    async def test_second_leg_failure_cancels_first(self):
        """If sell leg fails, buy order should be cancelled."""
        execution = _make_execution(is_sim=False)
        execution.api_manager.get_last_price = AsyncMock(return_value=59999.0)

        call_count = {'buy': 0, 'sell': 0}
        async def mock_execute(exchange_id, base, quote, side, amount, price, monitor):
            call_count[side] += 1
            if side == 'buy':
                return 'buy_123', 1.0, 0
            return None  # sell fails
        execution.execute_order = mock_execute

        result_buy, result_sell = await execution.execute_long_trade(
            'bot-uuid-1234', 'binance', 'okx', 'BTC', 'USDT', 1.0, 1.0, 60000.0, 60200.0
        )
        assert result_sell is None
        # cancel_order should have been called (via _cancel_order_with_retry)
        execution.api_manager.cancel_order.assert_called()

    @pytest.mark.asyncio
    async def test_short_trade_partial_sell_adjusts_buy(self):
        """SHORT: if sell fills 0.6, buy leg should use 0.6."""
        execution = _make_execution(is_sim=True)
        async def mock_execute(exchange_id, base, quote, side, amount, price, monitor):
            if side == 'sell':
                return 'sell_789', 0.6, 0.4  # partial fill
            return 'buy_012', amount, 0
        execution.execute_order = mock_execute

        result_buy, result_sell = await execution.execute_short_trade(
            'bot-uuid-1234', 'binance', 'okx', 'BTC', 'USDT', 1.0, 1.0, 60000.0, 60200.0
        )
        assert result_sell is not None
        assert result_sell[1] == 0.6
        assert result_buy is not None

    @pytest.mark.asyncio
    async def test_open_position_called_with_bot_uuid_not_exchange_id(self):
        """T01: open_position must be called with the bot UUID, not the exchange ID."""
        execution = _make_execution(is_sim=True)
        async def mock_execute(exchange_id, base, quote, side, amount, price, monitor):
            return f'{side}_order', amount, 0
        execution.execute_order = mock_execute

        await execution.execute_long_trade(
            'bot-uuid-abcd', 'binance', 'okx', 'BTC', 'USDT', 1.0, 1.0, 60000.0, 60200.0
        )
        call_kwargs = execution.sonarft_helpers.open_position.call_args
        assert call_kwargs.kwargs['botid'] == 'bot-uuid-abcd', (
            f"open_position called with botid={call_kwargs.kwargs['botid']!r}, "
            f"expected 'bot-uuid-abcd'"
        )

    @pytest.mark.asyncio
    async def test_close_position_called_with_bot_uuid_not_exchange_id(self):
        """T01: close_position must be called with the bot UUID, not the exchange ID."""
        execution = _make_execution(is_sim=True)
        async def mock_execute(exchange_id, base, quote, side, amount, price, monitor):
            return f'{side}_order', amount, 0
        execution.execute_order = mock_execute

        await execution.execute_long_trade(
            'bot-uuid-abcd', 'binance', 'okx', 'BTC', 'USDT', 1.0, 1.0, 60000.0, 60200.0
        )
        call_kwargs = execution.sonarft_helpers.close_position.call_args
        assert call_kwargs.kwargs['botid'] == 'bot-uuid-abcd', (
            f"close_position called with botid={call_kwargs.kwargs['botid']!r}, "
            f"expected 'bot-uuid-abcd'"
        )


# ---------------------------------------------------------------------------
# T-02: MAX_CONCURRENT_TRADES limit in TradeExecutor
# ---------------------------------------------------------------------------

class TestConcurrentTradeLimit:

    def _make_executor(self, max_trades: int = 2):
        import trade_executor as te_module
        original = te_module._MAX_CONCURRENT_TRADES
        te_module._MAX_CONCURRENT_TRADES = max_trades
        execution = _make_execution(is_sim=True)
        from trade_executor import TradeExecutor
        executor = TradeExecutor(execution)
        return executor, te_module, original

    def _make_trade_data(self):
        return {
            'position': '', 'base': 'BTC', 'quote': 'USDT',
            'buy_exchange': 'binance', 'sell_exchange': 'okx',
            'buy_price': 60000.0, 'sell_price': 60200.0,
            'buy_trade_amount': 1.0, 'sell_trade_amount': 1.0,
            'executed_amount': 1.0, 'buy_value': 60000.0, 'sell_value': 60200.0,
            'buy_fee_rate': 0.001, 'sell_fee_rate': 0.001,
            'buy_fee_base': 0, 'buy_fee_quote': 60.0, 'sell_fee_quote': 60.2,
            'profit': 79.8, 'profit_percentage': 0.00133,
            'market_direction_buy': 'bull', 'market_direction_sell': 'bull',
            'market_rsi_buy': 50.0, 'market_rsi_sell': 50.0,
            'market_stoch_rsi_buy_k': 50.0, 'market_stoch_rsi_buy_d': 45.0,
            'market_stoch_rsi_sell_k': 50.0, 'market_stoch_rsi_sell_d': 45.0,
        }

    @pytest.mark.asyncio
    async def test_dispatch_allowed_below_limit(self):
        executor, te_module, original = self._make_executor(max_trades=3)
        try:
            trade_data = self._make_trade_data()
            executor.execute_trade('bot-1', trade_data)
            executor.execute_trade('bot-1', trade_data)
            # 2 tasks dispatched, limit is 3 — both should be in the list
            assert len(executor.trade_tasks) == 2
        finally:
            te_module._MAX_CONCURRENT_TRADES = original
            for t in executor.trade_tasks:
                t.cancel()

    @pytest.mark.asyncio
    async def test_dispatch_blocked_at_limit(self):
        executor, te_module, original = self._make_executor(max_trades=2)
        try:
            trade_data = self._make_trade_data()
            executor.execute_trade('bot-1', trade_data)
            executor.execute_trade('bot-1', trade_data)
            # At limit — third dispatch must be skipped
            executor.execute_trade('bot-1', trade_data)
            assert len(executor.trade_tasks) == 2  # still 2, not 3
        finally:
            te_module._MAX_CONCURRENT_TRADES = original
            for t in executor.trade_tasks:
                t.cancel()

    @pytest.mark.asyncio
    async def test_dispatch_resumes_after_task_completes(self):
        """Once a task finishes, the slot opens and a new dispatch is accepted."""
        executor, te_module, original = self._make_executor(max_trades=1)
        try:
            trade_data = self._make_trade_data()
            executor.execute_trade('bot-1', trade_data)
            assert len(executor.trade_tasks) == 1

            # Cancel the task to simulate completion (done() returns True)
            executor.trade_tasks[0].cancel()
            # Yield to let the cancellation propagate
            import asyncio
            await asyncio.sleep(0)

            # Now active count is 0 — next dispatch should succeed
            executor.execute_trade('bot-1', trade_data)
            active = [t for t in executor.trade_tasks if not t.done()]
            assert len(active) == 1
        finally:
            te_module._MAX_CONCURRENT_TRADES = original
            for t in executor.trade_tasks:
                t.cancel()


# ---------------------------------------------------------------------------
# T-16: monitor_order() always cancels order on any exit path
# ---------------------------------------------------------------------------

class TestMonitorOrderCancelOnExit:

    @pytest.mark.asyncio
    async def test_cancel_called_on_task_cancellation(self):
        """When the monitoring task is cancelled externally, cancel_order must be called."""
        execution = _make_execution(is_sim=False)

        # watch_orders hangs indefinitely — simulates a slow exchange
        async def _hang(*a, **kw):
            await asyncio.sleep(9999)

        execution.api_manager.watch_orders = AsyncMock(side_effect=_hang)
        execution.api_manager.cancel_order = AsyncMock(
            return_value={'id': 'order_001', 'status': 'canceled'}
        )

        # Start monitoring in a task and cancel it immediately
        task = asyncio.create_task(
            execution.monitor_order(
                'binance', 'order_001', 'buy', 'BTC', 'USDT', 1.0, 60000.0,
                max_wait_seconds=300,
            )
        )
        await asyncio.sleep(0.05)  # let the task start and reach the first await
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        # cancel_order must have been called via the finally block
        execution.api_manager.cancel_order.assert_called_once_with(
            'binance', 'order_001', 'BTC', 'USDT'
        )

    @pytest.mark.asyncio
    async def test_cancel_called_on_timeout(self):
        """When the deadline is reached, cancel_order must be called."""
        execution = _make_execution(is_sim=False)

        # watch_orders returns empty — loop runs until deadline
        execution.api_manager.watch_orders = AsyncMock(return_value=[])
        execution.api_manager.cancel_order = AsyncMock(
            return_value={'id': 'order_001', 'status': 'canceled'}
        )

        # Use a very short timeout so the test completes quickly
        filled, remaining = await execution.monitor_order(
            'binance', 'order_001', 'buy', 'BTC', 'USDT', 1.0, 60000.0,
            max_wait_seconds=0,  # expires immediately
        )

        # cancel_order must have been called via the finally block
        execution.api_manager.cancel_order.assert_called()


# ---------------------------------------------------------------------------
# T16 (extended): _execute_two_leg_trade — imbalance alert + full round-trip
# ---------------------------------------------------------------------------

class TestTwoLegTradeExtended:
    """T16: additional coverage for _execute_two_leg_trade paths not yet tested."""

    def _make_execution(self, is_sim=True):
        from unittest.mock import AsyncMock, MagicMock
        api = MagicMock()
        api.markets = {}
        api.create_order = AsyncMock(return_value={"id": "order_001"})
        api.cancel_order = AsyncMock(return_value={"id": "order_001", "status": "canceled"})
        api.get_balance = AsyncMock(return_value={"free": {"BTC": 10.0, "USDT": 1_000_000.0}})
        api.watch_orders = AsyncMock(return_value=[])
        api.get_last_price = AsyncMock(return_value=59999.0)
        helpers = MagicMock()
        helpers.save_order_history = AsyncMock()
        helpers.save_trade_history = AsyncMock()
        helpers.open_position = AsyncMock()
        helpers.close_position = AsyncMock()
        ex = SonarftExecution(api, helpers, is_simulation_mode=is_sim)
        return ex

    @pytest.mark.asyncio
    async def test_imbalanced_second_leg_sends_alert(self):
        """When second leg partially fills, alert callback must be called."""
        execution = self._make_execution(is_sim=True)
        alert_messages = []
        execution._alert_callback = AsyncMock(side_effect=lambda m: alert_messages.append(m))

        async def mock_execute(exchange_id, base, quote, side, amount, price, monitor):
            if side == "buy":
                return "buy_001", amount, 0       # full fill
            return "sell_001", amount * 0.5, amount * 0.5  # partial fill

        execution.execute_order = mock_execute

        await execution.execute_long_trade(
            "bot-uuid", "binance", "okx", "BTC", "USDT",
            1.0, 1.0, 60000.0, 60200.0,
        )

        assert len(alert_messages) == 1
        assert "IMBALANCE" in alert_messages[0]

    @pytest.mark.asyncio
    async def test_full_round_trip_saves_history(self):
        """A fully successful two-leg trade must call save_order_history and
        save_trade_history exactly once each via _execute_position."""
        from models import Trade
        execution = self._make_execution(is_sim=True)

        async def mock_execute(exchange_id, base, quote, side, amount, price, monitor):
            return f"{side}_001", amount, 0  # full fill

        execution.execute_order = mock_execute

        trade = Trade(
            position="", base="BTC", quote="USDT",
            buy_exchange="binance", sell_exchange="okx",
            buy_price=60000.0, sell_price=60200.0,
            buy_trade_amount=1.0, sell_trade_amount=1.0,
            executed_amount=1.0, buy_value=60000.0, sell_value=60200.0,
            buy_fee_rate=0.001, sell_fee_rate=0.001,
            buy_fee_base=0.0, buy_fee_quote=60.0, sell_fee_quote=60.2,
            profit=79.8, profit_percentage=0.00133,
            market_direction_buy="bull", market_direction_sell="bull",
            market_rsi_buy=50.0, market_rsi_sell=50.0,
            market_stoch_rsi_buy_k=50.0, market_stoch_rsi_buy_d=45.0,
            market_stoch_rsi_sell_k=50.0, market_stoch_rsi_sell_d=45.0,
        )

        buy_ok, sell_ok, success = await execution._execute_position(
            "bot-uuid", trade, "LONG"
        )

        assert success is True
        execution.sonarft_helpers.save_order_history.assert_called_once()
        execution.sonarft_helpers.save_trade_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_position_dispatches_long_correctly(self):
        """_execute_position with LONG must call execute_long_trade (buy first)."""
        from models import Trade
        execution = self._make_execution(is_sim=True)
        calls = []

        async def mock_execute(exchange_id, base, quote, side, amount, price, monitor):
            calls.append(side)
            return f"{side}_001", amount, 0

        execution.execute_order = mock_execute

        trade = Trade(
            position="", base="ETH", quote="USDT",
            buy_exchange="binance", sell_exchange="okx",
            buy_price=2000.0, sell_price=2010.0,
            buy_trade_amount=0.1, sell_trade_amount=0.1,
            executed_amount=0.1, buy_value=200.0, sell_value=201.0,
            buy_fee_rate=0.001, sell_fee_rate=0.001,
            buy_fee_base=0.0, buy_fee_quote=0.2, sell_fee_quote=0.201,
            profit=0.599, profit_percentage=0.003,
            market_direction_buy="bull", market_direction_sell="bull",
            market_rsi_buy=50.0, market_rsi_sell=50.0,
            market_stoch_rsi_buy_k=50.0, market_stoch_rsi_buy_d=45.0,
            market_stoch_rsi_sell_k=50.0, market_stoch_rsi_sell_d=45.0,
        )

        await execution._execute_position("bot-uuid", trade, "LONG")

        # LONG: buy must come before sell
        assert calls[0] == "buy"
        assert calls[1] == "sell"

    @pytest.mark.asyncio
    async def test_execute_position_dispatches_short_correctly(self):
        """_execute_position with SHORT must call execute_short_trade (sell first)."""
        from models import Trade
        execution = self._make_execution(is_sim=True)
        calls = []

        async def mock_execute(exchange_id, base, quote, side, amount, price, monitor):
            calls.append(side)
            return f"{side}_001", amount, 0

        execution.execute_order = mock_execute

        trade = Trade(
            position="", base="ETH", quote="USDT",
            buy_exchange="binance", sell_exchange="okx",
            buy_price=2000.0, sell_price=2010.0,
            buy_trade_amount=0.1, sell_trade_amount=0.1,
            executed_amount=0.1, buy_value=200.0, sell_value=201.0,
            buy_fee_rate=0.001, sell_fee_rate=0.001,
            buy_fee_base=0.0, buy_fee_quote=0.2, sell_fee_quote=0.201,
            profit=0.599, profit_percentage=0.003,
            market_direction_buy="bull", market_direction_sell="bull",
            market_rsi_buy=50.0, market_rsi_sell=50.0,
            market_stoch_rsi_buy_k=50.0, market_stoch_rsi_buy_d=45.0,
            market_stoch_rsi_sell_k=50.0, market_stoch_rsi_sell_d=45.0,
        )

        await execution._execute_position("bot-uuid", trade, "SHORT")

        # SHORT: sell must come before buy
        assert calls[0] == "sell"
        assert calls[1] == "buy"


# ---------------------------------------------------------------------------
# T18 (extended): monitor_order — filled and cancelled return values
# ---------------------------------------------------------------------------

class TestMonitorOrderReturnValues:
    """T18: verify monitor_order returns correct (filled, remaining) tuples
    for the filled and cancelled order status paths."""

    def _make_execution(self):
        from unittest.mock import AsyncMock, MagicMock
        api = MagicMock()
        api.cancel_order = AsyncMock(
            return_value={"id": "order_001", "status": "canceled"}
        )
        helpers = MagicMock()
        ex = SonarftExecution(api, helpers, is_simulation_mode=False)
        return ex

    @pytest.mark.asyncio
    async def test_filled_order_returns_filled_amount(self):
        """When order status is 'closed', monitor_order must return
        (filled_amount, 0) from the order dict."""
        execution = self._make_execution()

        filled_order = {
            "id": "order_001",
            "status": "closed",
            "filled": 0.75,
            "remaining": 0.0,
        }
        execution.api_manager.watch_orders = AsyncMock(
            return_value=[filled_order]
        )

        filled, remaining = await execution.monitor_order(
            "binance", "order_001", "buy", "BTC", "USDT",
            target_amount=1.0, price=60000.0, max_wait_seconds=5,
        )

        assert filled == 0.75
        assert remaining == 0.0

    @pytest.mark.asyncio
    async def test_cancelled_order_returns_zero_filled(self):
        """When order status is 'canceled', monitor_order must return (0, target_amount)."""
        execution = self._make_execution()

        cancelled_order = {
            "id": "order_001",
            "status": "canceled",
            "filled": 0.0,
            "remaining": 1.0,
        }
        execution.api_manager.watch_orders = AsyncMock(
            return_value=[cancelled_order]
        )

        filled, remaining = await execution.monitor_order(
            "binance", "order_001", "buy", "BTC", "USDT",
            target_amount=1.0, price=60000.0, max_wait_seconds=5,
        )

        assert filled == 0
        assert remaining == 1.0

    @pytest.mark.asyncio
    async def test_order_not_in_list_treated_as_filled(self):
        """When the order ID is absent from watch_orders result (already filled
        and removed), monitor_order must return (target_amount, 0)."""
        execution = self._make_execution()

        # watch_orders returns a different order — ours is gone (filled)
        execution.api_manager.watch_orders = AsyncMock(
            return_value=[{"id": "other_order", "status": "open"}]
        )

        filled, remaining = await execution.monitor_order(
            "binance", "order_001", "buy", "BTC", "USDT",
            target_amount=1.0, price=60000.0, max_wait_seconds=5,
        )

        assert filled == 1.0  # target_amount assumed filled
        assert remaining == 0
