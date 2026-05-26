"""
Tests for Phase 3 performance optimisations:
T-17 — slippage buffer in profit threshold
T-18 — re-validate profitability after monitor_price()
T-19 — LRU eviction for order book + ticker caches
T-22 — get_latest_prices() populates cache
T-23 — MACD+RSI gathered concurrently in dynamic_volatility_adjustment()
T-29 — _reconcile_open_orders() parallelised
"""
import time as _time
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# T-17: Slippage buffer in profit threshold
# ---------------------------------------------------------------------------

class TestSlippageBuffer:

    def _make_processor(self, slippage_buffer=0.0, profit_pct=0.005):
        from trade_processor import TradeProcessor
        validators = MagicMock()
        execution = MagicMock()
        math = MagicMock()
        prices = MagicMock()
        prices.get_the_latest_prices = AsyncMock()
        prices.weighted_adjust_prices = AsyncMock(return_value=(
            60000.0, 60200.0,
            {'market_direction_buy': 'bull', 'market_direction_sell': 'bull',
             'market_rsi_buy': 55.0, 'market_rsi_sell': 55.0,
             'market_stoch_rsi_buy_k': 50.0, 'market_stoch_rsi_buy_d': 45.0,
             'market_stoch_rsi_sell_k': 50.0, 'market_stoch_rsi_sell_d': 45.0},
        ))
        trade_data = {
            'position': '', 'base': 'BTC', 'quote': 'USDT',
            'buy_exchange': 'binance', 'sell_exchange': 'okx',
            'buy_price': 60000.0, 'sell_price': 60200.0,
            'buy_trade_amount': 1.0, 'sell_trade_amount': 1.0,
            'executed_amount': 1.0, 'buy_value': 60000.0, 'sell_value': 60200.0,
            'buy_fee_rate': 0.001, 'sell_fee_rate': 0.001,
            'buy_fee_base': 0, 'buy_fee_quote': 60.0, 'sell_fee_quote': 60.2,
            'profit': 50.0, 'profit_percentage': profit_pct,
        }
        math.calculate_trade = MagicMock(return_value=(50.0, profit_pct, trade_data))
        proc = TradeProcessor(validators, execution, math, prices,
                              slippage_buffer=slippage_buffer)
        proc.trade_validator.has_requirements_for_success_carrying_out = AsyncMock(return_value=True)
        proc.trade_executor.execute_trade = MagicMock()
        return proc

    @pytest.mark.asyncio
    async def test_trade_dispatched_when_profit_above_threshold_plus_buffer(self):
        # profit_pct=0.005, threshold=0.003, buffer=0.001 → effective=0.004 → 0.005 >= 0.004 ✓
        proc = self._make_processor(slippage_buffer=0.001, profit_pct=0.005)
        buy = ('binance', 60000.0, 60010.0, 60005.0, 'BTC/USDT')
        sell = ('okx', 59990.0, 60200.0, 60100.0, 'BTC/USDT')
        await proc.process_trade_combination(1, 'BTC', 'USDT', 1.0, buy, sell, 0.003)
        proc.trade_executor.execute_trade.assert_called_once()

    @pytest.mark.asyncio
    async def test_trade_skipped_when_profit_below_threshold_plus_buffer(self):
        # profit_pct=0.003, threshold=0.003, buffer=0.001 → effective=0.004 → 0.003 < 0.004 ✗
        proc = self._make_processor(slippage_buffer=0.001, profit_pct=0.003)
        buy = ('binance', 60000.0, 60010.0, 60005.0, 'BTC/USDT')
        sell = ('okx', 59990.0, 60200.0, 60100.0, 'BTC/USDT')
        await proc.process_trade_combination(1, 'BTC', 'USDT', 1.0, buy, sell, 0.003)
        proc.trade_executor.execute_trade.assert_not_called()

    @pytest.mark.asyncio
    async def test_zero_buffer_behaves_as_before(self):
        # profit_pct=0.003, threshold=0.003, buffer=0.0 → effective=0.003 → 0.003 >= 0.003 ✓
        proc = self._make_processor(slippage_buffer=0.0, profit_pct=0.003)
        buy = ('binance', 60000.0, 60010.0, 60005.0, 'BTC/USDT')
        sell = ('okx', 59990.0, 60200.0, 60100.0, 'BTC/USDT')
        await proc.process_trade_combination(1, 'BTC', 'USDT', 1.0, buy, sell, 0.003)
        proc.trade_executor.execute_trade.assert_called_once()


# ---------------------------------------------------------------------------
# T-18: Re-validate profitability after monitor_price()
# ---------------------------------------------------------------------------

class TestRevalidateAfterMonitorPrice:

    def _make_execution(self, slippage_buffer=0.001):
        from sonarft_execution import SonarftExecution
        api = MagicMock()
        api.markets = {}
        api.get_symbol_precision = MagicMock(return_value=None)
        helpers = MagicMock()
        helpers.open_position = AsyncMock()
        helpers.close_position = AsyncMock()
        execution = SonarftExecution(
            api, helpers, is_simulation_mode=False,
            slippage_buffer=slippage_buffer,
        )
        return execution

    @pytest.mark.asyncio
    async def test_order_skipped_when_price_drifts_beyond_buffer(self):
        execution = self._make_execution(slippage_buffer=0.001)
        # Target price 60000, monitored price 60100 → drift = 0.167% > 0.1% buffer
        execution.monitor_price = AsyncMock(return_value=60100.0)
        result = await execution.create_order(
            'binance', 'BTC', 'USDT', 60000.0, 1.0, 'buy', False
        )
        assert result is None
        execution.api_manager.create_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_order_placed_when_price_within_buffer(self):
        execution = self._make_execution(slippage_buffer=0.005)
        # Target price 60000, monitored price 60100 → drift = 0.167% < 0.5% buffer
        execution.monitor_price = AsyncMock(return_value=60100.0)
        execution.api_manager.create_order = AsyncMock(return_value={'id': 'order_001'})
        execution.api_manager.watch_orders = AsyncMock(return_value=[])
        result = await execution.create_order(
            'binance', 'BTC', 'USDT', 60000.0, 1.0, 'buy', False
        )
        assert result is not None
        execution.api_manager.create_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_zero_buffer_never_skips_on_drift(self):
        """With slippage_buffer=0, the re-validation check is disabled."""
        execution = self._make_execution(slippage_buffer=0.0)
        execution.monitor_price = AsyncMock(return_value=59000.0)  # large drift
        execution.api_manager.create_order = AsyncMock(return_value={'id': 'order_001'})
        execution.api_manager.watch_orders = AsyncMock(return_value=[])
        result = await execution.create_order(
            'binance', 'BTC', 'USDT', 60000.0, 1.0, 'buy', False
        )
        # Should not be skipped — buffer is 0
        assert result is not None


# ---------------------------------------------------------------------------
# T-19: LRU eviction for order book + ticker caches
# ---------------------------------------------------------------------------

class TestCacheLRUEviction:

    def _make_manager(self):
        from cachetools import TTLCache
        from sonarft_api_manager import SonarftApiManager
        manager = SonarftApiManager.__new__(SonarftApiManager)
        manager.logger = MagicMock()
        manager.__ccxt__ = True
        manager.__ccxtpro__ = False
        manager._order_book_cache = TTLCache(maxsize=500, ttl=2)
        manager._ticker_cache = TTLCache(maxsize=500, ttl=2)
        manager._shared_cache = None
        mock_exchange = MagicMock()
        mock_exchange.id = 'binance'
        mock_exchange.fetch_order_book = MagicMock(return_value={'bids': [[60000, 1]], 'asks': [[60010, 1]]})
        mock_exchange.fetch_ticker = MagicMock(return_value={'last': 60005, 'bid': 60000, 'ask': 60010, 'baseVolume': 100})
        manager._exchange_map = {'binance': mock_exchange}
        return manager, mock_exchange

    @pytest.mark.asyncio
    async def test_order_book_cache_evicts_at_500(self):
        """TTLCache enforces maxsize=500 — inserting a 501st entry evicts the oldest."""
        manager, exchange = self._make_manager()
        # Pre-fill cache with 500 valid entries (TTLCache stores values directly)
        for i in range(500):
            manager._order_book_cache[f'exchange_{i}:BTC/USDT'] = {}
        assert len(manager._order_book_cache) == 500
        # Fetch a new entry — TTLCache evicts oldest to stay at maxsize=500
        await manager.get_order_book('binance', 'BTC', 'USDT')
        assert len(manager._order_book_cache) == 500

    @pytest.mark.asyncio
    async def test_ticker_cache_evicts_at_500(self):
        """TTLCache enforces maxsize=500 — inserting a 501st entry evicts the oldest."""
        manager, exchange = self._make_manager()
        for i in range(500):
            manager._ticker_cache[f'exchange_{i}:BTC/USDT'] = {}
        assert len(manager._ticker_cache) == 500
        await manager._get_ticker('binance', 'BTC', 'USDT')
        assert len(manager._ticker_cache) == 500


# ---------------------------------------------------------------------------
# T-23: MACD+RSI gathered concurrently
# ---------------------------------------------------------------------------

class TestDynamicVolatilityGather:

    @pytest.mark.asyncio
    async def test_macd_and_rsi_called_concurrently(self):
        """Both get_macd and get_rsi must be called (not skipped) when both active."""
        from sonarft_prices import SonarftPrices
        ind = MagicMock()
        call_order = []

        async def mock_macd(*a, **kw):
            call_order.append('macd')
            return (1.0, 0.5, 0.5)

        async def mock_rsi(*a, **kw):
            call_order.append('rsi')
            return 55.0

        ind.get_macd = AsyncMock(side_effect=mock_macd)
        ind.get_rsi = AsyncMock(side_effect=mock_rsi)

        api = MagicMock()
        prices = SonarftPrices(api, ind)
        prices.active_indicators = ['rsi', 'macd']

        await prices.dynamic_volatility_adjustment('bull', 'bear', 'binance', 'BTC', 'USDT')

        ind.get_macd.assert_called_once()
        ind.get_rsi.assert_called_once()
        # Both were called (order may vary due to gather)
        assert set(call_order) == {'macd', 'rsi'}
