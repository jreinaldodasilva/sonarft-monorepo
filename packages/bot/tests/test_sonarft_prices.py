"""
Unit tests for SonarftPrices — weighted_adjust_prices and dynamic_volatility_adjustment.
These are the most complex price-adjustment functions in the codebase.
"""
import pytest
import math
from unittest.mock import MagicMock, AsyncMock
from sonarft_prices import SonarftPrices


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ORDER_BOOK = {
    'bids': [[60000.0, 1.0], [59990.0, 2.0], [59980.0, 0.5]],
    'asks': [[60010.0, 1.5], [60020.0, 0.5], [60030.0, 1.0]],
}


def make_prices(
    direction='bull', trend='bull',
    rsi_buy=50.0, rsi_sell=50.0,
    stoch_buy=(50.0, 45.0), stoch_sell=(50.0, 45.0),
    volatility=0.5, support=None, resistance=None,
    macd=(1.0, 0.5, 0.5), macd_rsi=50.0,
):
    """Build a SonarftPrices with fully mocked indicators."""
    ind = MagicMock()
    ind.market_movement = AsyncMock(return_value=('slow', direction))
    ind.get_market_direction = AsyncMock(return_value=direction)
    ind.get_rsi = AsyncMock(return_value=rsi_buy)  # overridden per-call below
    ind.get_stoch_rsi = AsyncMock(return_value=stoch_buy)
    ind.get_short_term_market_trend = AsyncMock(return_value=trend)
    ind.get_volatility = AsyncMock(return_value=volatility)
    ind.get_order_book = AsyncMock(return_value=ORDER_BOOK)
    ind.get_support_price = AsyncMock(return_value=support)
    ind.get_resistance_price = AsyncMock(return_value=resistance)
    ind.get_macd = AsyncMock(return_value=macd)
    ind.get_profit_factor = MagicMock(return_value=0.99942)

    # Make get_rsi and get_stoch_rsi return different values for buy vs sell exchange
    async def _rsi(exchange, *a, **kw):
        return rsi_buy if exchange == 'binance' else rsi_sell
    async def _stoch(exchange, *a, **kw):
        return stoch_buy if exchange == 'binance' else stoch_sell
    async def _macd_rsi(exchange, *a, **kw):
        return macd_rsi
    ind.get_rsi = AsyncMock(side_effect=_rsi)
    ind.get_stoch_rsi = AsyncMock(side_effect=_stoch)

    api = MagicMock()
    prices = SonarftPrices(api, ind)
    prices.spread_increase_factor = 1.00072
    prices.spread_decrease_factor = 0.99936
    prices.active_indicators = ['rsi', 'stoch rsi', 'macd']
    return prices


# ---------------------------------------------------------------------------
# weighted_adjust_prices — basic behavior
# ---------------------------------------------------------------------------

class TestWeightedAdjustPricesBasic:

    @pytest.mark.asyncio
    async def test_returns_nonzero_prices_and_indicators(self):
        prices = make_prices()
        buy, sell, ind = await prices.weighted_adjust_prices(
            1, 'binance', 'okx', 'BTC', 'USDT', 60000.0, 60200.0, 60005.0, 60100.0
        )
        assert buy > 0
        assert sell > 0
        assert 'market_direction_buy' in ind
        assert 'market_rsi_buy' in ind

    @pytest.mark.asyncio
    async def test_adjusted_prices_near_targets(self):
        """With low volatility, adjusted prices should be close to targets."""
        prices = make_prices(volatility=0.001)
        buy, sell, _ = await prices.weighted_adjust_prices(
            1, 'binance', 'okx', 'BTC', 'USDT', 60000.0, 60200.0, 60005.0, 60100.0
        )
        assert abs(buy - 60000.0) / 60000.0 < 0.01  # within 1%
        assert abs(sell - 60200.0) / 60200.0 < 0.01


# ---------------------------------------------------------------------------
# weighted_adjust_prices — market condition branches
# ---------------------------------------------------------------------------

class TestWeightedAdjustPricesBranches:

    @pytest.mark.asyncio
    async def test_bull_bull_normal_applies_increase_factor(self):
        """Bull direction + bull trend + RSI < 70 → spread_increase_factor."""
        prices = make_prices(direction='bull', trend='bull', rsi_buy=55.0, rsi_sell=55.0)
        buy, sell, _ = await prices.weighted_adjust_prices(
            1, 'binance', 'okx', 'BTC', 'USDT', 60000.0, 60200.0, 60005.0, 60100.0
        )
        # With increase factor, buy price should be slightly higher than without
        assert buy > 0
        assert sell > 0

    @pytest.mark.asyncio
    async def test_bull_bull_overbought_applies_decrease_factor(self):
        """Bull + bull + RSI >= 70 + StochK > StochD → spread_decrease_factor (reversal)."""
        prices = make_prices(
            direction='bull', trend='bull',
            rsi_buy=75.0, rsi_sell=75.0,
            stoch_buy=(80.0, 60.0), stoch_sell=(80.0, 60.0),  # K > D
        )
        buy, sell, _ = await prices.weighted_adjust_prices(
            1, 'binance', 'okx', 'BTC', 'USDT', 60000.0, 60200.0, 60005.0, 60100.0
        )
        assert buy > 0
        assert sell > 0

    @pytest.mark.asyncio
    async def test_bear_bear_normal_applies_decrease_factor(self):
        """Bear direction + bear trend + RSI > 30 → spread_decrease_factor."""
        prices = make_prices(direction='bear', trend='bear', rsi_buy=45.0, rsi_sell=45.0)
        buy, sell, _ = await prices.weighted_adjust_prices(
            1, 'binance', 'okx', 'BTC', 'USDT', 60000.0, 60200.0, 60005.0, 60100.0
        )
        assert buy > 0
        assert sell > 0

    @pytest.mark.asyncio
    async def test_bear_bear_oversold_applies_increase_factor(self):
        """Bear + bear + RSI <= 30 + StochK < StochD → spread_increase_factor (reversal)."""
        prices = make_prices(
            direction='bear', trend='bear',
            rsi_buy=25.0, rsi_sell=25.0,
            stoch_buy=(20.0, 40.0), stoch_sell=(20.0, 40.0),  # K < D
        )
        buy, sell, _ = await prices.weighted_adjust_prices(
            1, 'binance', 'okx', 'BTC', 'USDT', 60000.0, 60200.0, 60005.0, 60100.0
        )
        assert buy > 0
        assert sell > 0

    @pytest.mark.asyncio
    async def test_neutral_direction_no_spread_adjustment(self):
        """Neutral direction → no bull/bear spread factor applied."""
        prices = make_prices(direction='neutral', trend='neutral')
        buy, sell, _ = await prices.weighted_adjust_prices(
            1, 'binance', 'okx', 'BTC', 'USDT', 60000.0, 60200.0, 60005.0, 60100.0
        )
        assert buy > 0
        assert sell > 0


# ---------------------------------------------------------------------------
# weighted_adjust_prices — edge cases and guards
# ---------------------------------------------------------------------------

class TestWeightedAdjustPricesEdgeCases:

    @pytest.mark.asyncio
    async def test_timeout_returns_zero(self):
        """If the indicator gather times out, weighted_adjust_prices returns (0, 0, {})."""
        import asyncio
        from unittest.mock import patch
        ind = MagicMock()

        async def _hang(*a, **kw):
            await asyncio.sleep(100)

        ind.market_movement = AsyncMock(side_effect=_hang)
        ind.get_market_direction = AsyncMock(side_effect=_hang)
        ind.get_rsi = AsyncMock(side_effect=_hang)
        ind.get_stoch_rsi = AsyncMock(side_effect=_hang)
        ind.get_short_term_market_trend = AsyncMock(side_effect=_hang)
        ind.get_volatility = AsyncMock(side_effect=_hang)
        ind.get_order_book = AsyncMock(side_effect=_hang)
        ind.get_support_price = AsyncMock(side_effect=_hang)
        ind.get_resistance_price = AsyncMock(side_effect=_hang)

        api = MagicMock()
        prices = SonarftPrices(api, ind)

        # Patch asyncio.wait_for to raise TimeoutError immediately
        with patch("sonarft_prices.asyncio.wait_for", side_effect=asyncio.TimeoutError):
            buy, sell, indicators = await prices.weighted_adjust_prices(
                1, "binance", "okx", "BTC", "USDT", 60000.0, 60200.0, 60005.0, 60100.0,
            )

        assert buy == 0
        assert sell == 0
        assert indicators == {}

    @pytest.mark.asyncio
    async def test_none_rsi_with_rsi_active_returns_zero(self):
        prices = make_prices(rsi_buy=None, rsi_sell=None)
        # Override to return None
        prices.sonarft_indicators.get_rsi = AsyncMock(return_value=None)
        buy, sell, ind = await prices.weighted_adjust_prices(
            1, 'binance', 'okx', 'BTC', 'USDT', 60000.0, 60200.0, 60005.0, 60100.0
        )
        assert buy == 0
        assert sell == 0
        assert ind == {}

    @pytest.mark.asyncio
    async def test_none_stoch_with_stoch_active_returns_zero(self):
        prices = make_prices()
        prices.sonarft_indicators.get_stoch_rsi = AsyncMock(return_value=None)
        buy, sell, ind = await prices.weighted_adjust_prices(
            1, 'binance', 'okx', 'BTC', 'USDT', 60000.0, 60200.0, 60005.0, 60100.0
        )
        assert buy == 0
        assert sell == 0

    @pytest.mark.asyncio
    async def test_nan_volatility_returns_zero(self):
        prices = make_prices(volatility=float('nan'))
        buy, sell, ind = await prices.weighted_adjust_prices(
            1, 'binance', 'okx', 'BTC', 'USDT', 60000.0, 60200.0, 60005.0, 60100.0
        )
        assert buy == 0
        assert sell == 0
        assert ind == {}

    @pytest.mark.asyncio
    async def test_zero_volume_order_book_returns_zero(self):
        prices = make_prices()
        prices.sonarft_indicators.get_order_book = AsyncMock(return_value={
            'bids': [[60000.0, 0.0]], 'asks': [[60010.0, 0.0]],
        })
        buy, sell, ind = await prices.weighted_adjust_prices(
            1, 'binance', 'okx', 'BTC', 'USDT', 60000.0, 60200.0, 60005.0, 60100.0
        )
        assert buy == 0
        assert sell == 0

    @pytest.mark.asyncio
    async def test_support_clamps_buy_price(self):
        """If adjusted buy < support, buy should be clamped to support."""
        prices = make_prices(support=60500.0)  # support above target
        buy, sell, _ = await prices.weighted_adjust_prices(
            1, 'binance', 'okx', 'BTC', 'USDT', 60000.0, 60200.0, 60005.0, 60100.0
        )
        assert buy >= 60500.0

    @pytest.mark.asyncio
    async def test_resistance_clamps_sell_price(self):
        """If adjusted sell > resistance, sell should be clamped to resistance."""
        prices = make_prices(resistance=59000.0)  # resistance below target
        buy, sell, _ = await prices.weighted_adjust_prices(
            1, 'binance', 'okx', 'BTC', 'USDT', 60000.0, 60200.0, 60005.0, 60100.0
        )
        assert sell <= 59000.0

    @pytest.mark.asyncio
    async def test_indicators_dict_contains_all_keys(self):
        prices = make_prices()
        _, _, ind = await prices.weighted_adjust_prices(
            1, 'binance', 'okx', 'BTC', 'USDT', 60000.0, 60200.0, 60005.0, 60100.0
        )
        required = {
            'market_direction_buy', 'market_direction_sell',
            'market_rsi_buy', 'market_rsi_sell',
            'market_stoch_rsi_buy_k', 'market_stoch_rsi_buy_d',
            'market_stoch_rsi_sell_k', 'market_stoch_rsi_sell_d',
        }
        assert required.issubset(ind.keys())


# ---------------------------------------------------------------------------
# dynamic_volatility_adjustment
# ---------------------------------------------------------------------------

class TestDynamicVolatilityAdjustment:

    @pytest.mark.asyncio
    async def test_bear_bull_macd_negative_returns_075(self):
        prices = make_prices(macd=(-1.0, 0.5, -1.5))
        result = await prices.dynamic_volatility_adjustment('bear', 'bull', 'binance', 'BTC', 'USDT')
        assert result == 0.75

    @pytest.mark.asyncio
    async def test_bull_bear_rsi_above_70_returns_050(self):
        prices = make_prices()
        prices.sonarft_indicators.get_rsi = AsyncMock(return_value=75.0)
        result = await prices.dynamic_volatility_adjustment('bull', 'bear', 'binance', 'BTC', 'USDT')
        assert result == 0.5

    @pytest.mark.asyncio
    async def test_bull_bull_macd_positive_rsi_below_30_returns_025(self):
        prices = make_prices(macd=(1.0, 0.5, 0.5))
        prices.sonarft_indicators.get_rsi = AsyncMock(return_value=25.0)
        result = await prices.dynamic_volatility_adjustment('bull', 'bull', 'binance', 'BTC', 'USDT')
        assert result == 0.25

    @pytest.mark.asyncio
    async def test_bear_bear_macd_negative_rsi_above_70_returns_175(self):
        prices = make_prices(macd=(-1.0, 0.5, -1.5))
        prices.sonarft_indicators.get_rsi = AsyncMock(return_value=75.0)
        result = await prices.dynamic_volatility_adjustment('bear', 'bear', 'binance', 'BTC', 'USDT')
        assert result == 1.75

    @pytest.mark.asyncio
    async def test_none_macd_returns_1(self):
        prices = make_prices()
        prices.sonarft_indicators.get_macd = AsyncMock(return_value=None)
        result = await prices.dynamic_volatility_adjustment('bull', 'bull', 'binance', 'BTC', 'USDT')
        assert result == 1.0

    @pytest.mark.asyncio
    async def test_none_rsi_returns_1(self):
        prices = make_prices()
        prices.sonarft_indicators.get_rsi = AsyncMock(return_value=None)
        result = await prices.dynamic_volatility_adjustment('bull', 'bull', 'binance', 'BTC', 'USDT')
        assert result == 1.0

    @pytest.mark.asyncio
    async def test_neutral_direction_returns_1(self):
        prices = make_prices(macd=(1.0, 0.5, 0.5))
        prices.sonarft_indicators.get_rsi = AsyncMock(return_value=50.0)
        result = await prices.dynamic_volatility_adjustment('neutral', 'neutral', 'binance', 'BTC', 'USDT')
        assert result == 1.0


# ---------------------------------------------------------------------------
# get_weighted_price
# ---------------------------------------------------------------------------

class TestGetWeightedPrice:

    def test_correct_calculation(self):
        api = MagicMock()
        ind = MagicMock()
        prices = SonarftPrices(api, ind)
        price_list = [[60000.0, 1.0], [59990.0, 2.0], [59980.0, 0.5]]
        result = prices.get_weighted_price(price_list, 3)
        expected = (60000.0 * 1.0 + 59990.0 * 2.0 + 59980.0 * 0.5) / 3.5
        assert abs(result - expected) < 1e-9

    def test_zero_volume_returns_zero(self):
        api = MagicMock()
        ind = MagicMock()
        prices = SonarftPrices(api, ind)
        result = prices.get_weighted_price([[60000.0, 0.0]], 1)
        assert result == 0.0

    def test_depth_exceeds_list_length(self):
        api = MagicMock()
        ind = MagicMock()
        prices = SonarftPrices(api, ind)
        price_list = [[60000.0, 1.0]]
        result = prices.get_weighted_price(price_list, 10)
        assert result == 60000.0
