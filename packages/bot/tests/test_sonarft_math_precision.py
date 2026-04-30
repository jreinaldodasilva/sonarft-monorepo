"""
Tests for T-30 (precision fallback warning) and T-21 (fee refresh).
"""
import pytest
from unittest.mock import MagicMock, AsyncMock


# ---------------------------------------------------------------------------
# T-30: Precision fallback warning in calculate_trade()
# ---------------------------------------------------------------------------

class TestPrecisionFallbackWarning:

    def _make_math(self, live_precision=None):
        from sonarft_math import SonarftMath
        api = MagicMock()
        api.get_buy_fee.return_value = 0.001
        api.get_sell_fee.return_value = 0.001
        api.get_symbol_precision.return_value = live_precision
        return SonarftMath(api)

    def _price_list(self, exchange):
        return (exchange, 60000.0, 60010.0, 60005.0, 'BTC/USDT')

    def test_no_warning_when_live_precision_available(self):
        live = {
            'prices_precision': 2, 'buy_amount_precision': 5,
            'sell_amount_precision': 5, 'cost_precision': 7, 'fee_precision': 8,
        }
        math = self._make_math(live_precision=live)
        math.logger = MagicMock()
        math.calculate_trade(
            60000.0, 60200.0,
            self._price_list('binance'), self._price_list('okx'),
            1.0, 'BTC', 'USDT',
        )
        # No fallback warning should be logged
        warning_calls = [str(c) for c in math.logger.warning.call_args_list]
        assert not any('hardcoded precision fallback' in w for w in warning_calls)

    def test_warning_logged_when_falling_back_to_exchange_rules(self):
        math = self._make_math(live_precision=None)  # no live precision
        math.logger = MagicMock()
        math.calculate_trade(
            60000.0, 60200.0,
            self._price_list('binance'), self._price_list('okx'),
            1.0, 'BTC', 'USDT',
        )
        warning_calls = [str(c) for c in math.logger.warning.call_args_list]
        assert any('hardcoded precision fallback' in w for w in warning_calls)

    def test_returns_none_when_no_live_and_no_fallback(self):
        """Exchange not in EXCHANGE_RULES and no live precision → skip trade."""
        math = self._make_math(live_precision=None)
        math.logger = MagicMock()
        profit, pct, data = math.calculate_trade(
            60000.0, 60200.0,
            ('unknown_exchange', 60000.0, 60010.0, 60005.0, 'BTC/USDT'),
            ('okx', 59990.0, 60200.0, 60100.0, 'BTC/USDT'),
            1.0, 'BTC', 'USDT',
        )
        assert data is None


# ---------------------------------------------------------------------------
# T-21: Fee refresh
# ---------------------------------------------------------------------------

class TestFeeRefresh:

    def _make_manager(self):
        from sonarft_api_manager import SonarftApiManager
        manager = SonarftApiManager.__new__(SonarftApiManager)
        manager.logger = MagicMock()
        manager.__ccxt__ = True
        manager.__ccxtpro__ = False
        manager.exchanges_fees = [
            {'exchange': 'binance', 'buy_fee': 0.001, 'sell_fee': 0.001},
        ]
        mock_exchange = MagicMock()
        mock_exchange.id = 'binance'
        manager.exchanges_instances = [mock_exchange]
        manager._exchange_map = {'binance': mock_exchange}
        return manager, mock_exchange

    @pytest.mark.asyncio
    async def test_refresh_updates_fee_rates(self):
        manager, exchange = self._make_manager()
        # fetch_trading_fees returns maker=0.0008, taker=0.001
        exchange.fetch_trading_fees = MagicMock(return_value={
            'BTC/USDT': {'maker': 0.0008, 'taker': 0.001},
            'ETH/USDT': {'maker': 0.0008, 'taker': 0.001},
        })
        await manager.refresh_fees()
        fee_entry = manager.exchanges_fees[0]
        assert fee_entry['maker_buy_fee'] == 0.0008
        assert fee_entry['buy_fee'] == 0.001  # taker rate

    @pytest.mark.asyncio
    async def test_refresh_keeps_existing_on_failure(self):
        manager, exchange = self._make_manager()
        exchange.fetch_trading_fees = MagicMock(side_effect=RuntimeError("API error"))
        await manager.refresh_fees()
        # Original rates must be unchanged
        assert manager.exchanges_fees[0]['buy_fee'] == 0.001
        manager.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_refresh_keeps_existing_on_empty_response(self):
        manager, exchange = self._make_manager()
        exchange.fetch_trading_fees = MagicMock(return_value={})
        await manager.refresh_fees()
        assert manager.exchanges_fees[0]['buy_fee'] == 0.001
        manager.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_refresh_skips_unknown_exchange(self):
        """If exchange not in exchanges_fees config, log warning and skip."""
        manager, exchange = self._make_manager()
        exchange.id = 'unknown_exchange'
        manager._exchange_map = {'unknown_exchange': exchange}
        exchange.fetch_trading_fees = MagicMock(return_value={
            'BTC/USDT': {'maker': 0.0005, 'taker': 0.001},
        })
        await manager.refresh_fees()
        # exchanges_fees unchanged (binance entry still there)
        assert manager.exchanges_fees[0]['buy_fee'] == 0.001
        manager.logger.warning.assert_called()
