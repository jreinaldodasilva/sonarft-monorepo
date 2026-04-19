"""
Unit tests for TradeProcessor.process_trade_combination (T27)
and SonarftExecution partial fill handling (T28).
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from sonarft_search import TradeProcessor
from sonarft_execution import SonarftExecution
from sonarft_helpers import Trade


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
        original_execute = execution.execute_order
        async def mock_execute(exchange_id, base, quote, side, amount, price, monitor):
            if side == 'buy':
                return f'buy_123', 0.7, 0.3  # partial fill
            return f'sell_456', amount, 0  # full fill for sell
        execution.execute_order = mock_execute

        result_buy, result_sell = await execution.execute_long_trade(
            'binance', 'okx', 'BTC', 'USDT', 1.0, 1.0, 60000.0, 60200.0
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
            'binance', 'okx', 'BTC', 'USDT', 1.0, 1.0, 60000.0, 60200.0
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
            'binance', 'okx', 'BTC', 'USDT', 1.0, 1.0, 60000.0, 60200.0
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
            return f'buy_012', amount, 0
        execution.execute_order = mock_execute

        result_buy, result_sell = await execution.execute_short_trade(
            'binance', 'okx', 'BTC', 'USDT', 1.0, 1.0, 60000.0, 60200.0
        )
        assert result_sell is not None
        assert result_sell[1] == 0.6
        assert result_buy is not None
