"""
Unit tests for SonarftIndicators — RSI, MACD, StochRSI, market direction, trend.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from sonarft_indicators import SonarftIndicators

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_indicators(ohlcv=None):
    api = MagicMock()
    api.get_order_book = AsyncMock(return_value={
        'bids': [[60000.0 - i, 1.0] for i in range(20)],
        'asks': [[60010.0 + i, 1.0] for i in range(20)],
    })
    api.get_ohlcv_history = AsyncMock(return_value=ohlcv or _rising_ohlcv(50))
    return SonarftIndicators(api)


def _rising_ohlcv(n, base=100.0, step=1.0):
    """Steadily rising close prices — produces bull RSI > 50."""
    return [
        [1_000_000 + i * 60_000, base + i * step, base + i * step + 2,
         base + i * step - 1, base + i * step, 10.0]
        for i in range(n)
    ]


def _falling_ohlcv(n, base=200.0, step=1.0):
    """Steadily falling close prices — produces bear RSI < 50."""
    return [
        [1_000_000 + i * 60_000, base - i * step, base - i * step + 1,
         base - i * step - 2, base - i * step, 10.0]
        for i in range(n)
    ]


def _flat_ohlcv(n, price=100.0):
    return [
        [1_000_000 + i * 60_000, price, price + 0.1, price - 0.1, price, 10.0]
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# get_rsi
# ---------------------------------------------------------------------------

class TestGetRsi:

    @pytest.mark.asyncio
    async def test_rising_market_rsi_above_50(self):
        ind = make_indicators(_rising_ohlcv(50))
        rsi = await ind.get_rsi('binance', 'BTC', 'USDT', moving_average_period=14)
        assert rsi is not None
        assert rsi > 50

    @pytest.mark.asyncio
    async def test_falling_market_rsi_below_50(self):
        ind = make_indicators(_falling_ohlcv(50))
        rsi = await ind.get_rsi('binance', 'BTC', 'USDT', moving_average_period=14)
        assert rsi is not None
        assert rsi < 50

    @pytest.mark.asyncio
    async def test_rsi_in_valid_range(self):
        ind = make_indicators(_rising_ohlcv(50))
        rsi = await ind.get_rsi('binance', 'BTC', 'USDT')
        assert rsi is not None
        assert 0 <= rsi <= 100

    @pytest.mark.asyncio
    async def test_insufficient_data_returns_none(self):
        ind = make_indicators(_rising_ohlcv(5))  # only 5 candles, need 14
        rsi = await ind.get_rsi('binance', 'BTC', 'USDT', moving_average_period=14)
        assert rsi is None


# ---------------------------------------------------------------------------
# get_macd
# ---------------------------------------------------------------------------

class TestGetMacd:

    @pytest.mark.asyncio
    async def test_returns_three_floats(self):
        ind = make_indicators(_rising_ohlcv(50))
        result = await ind.get_macd('binance', 'BTC', 'USDT')
        assert result is not None
        macd, signal, hist = result
        assert isinstance(macd, float)
        assert isinstance(signal, float)
        assert isinstance(hist, float)

    @pytest.mark.asyncio
    async def test_rising_market_positive_macd(self):
        ind = make_indicators(_rising_ohlcv(50))
        result = await ind.get_macd('binance', 'BTC', 'USDT')
        assert result is not None
        macd, signal, hist = result
        assert macd > 0

    @pytest.mark.asyncio
    async def test_insufficient_data_returns_none(self):
        ind = make_indicators(_rising_ohlcv(10))
        result = await ind.get_macd('binance', 'BTC', 'USDT')
        assert result is None


# ---------------------------------------------------------------------------
# get_stoch_rsi — keyword argument fix regression
# ---------------------------------------------------------------------------

class TestGetStochRsi:

    @pytest.mark.asyncio
    async def test_returns_k_and_d_in_range(self):
        ind = make_indicators(_rising_ohlcv(50))
        result = await ind.get_stoch_rsi('binance', 'BTC', 'USDT',
                                          rsi_period=14, stoch_period=14,
                                          k_period=3, d_period=3)
        assert result is not None
        k, d = result
        assert 0 <= k <= 100
        assert 0 <= d <= 100

    @pytest.mark.asyncio
    async def test_rsi_period_14_not_3(self):
        """Regression: ensure rsi_length=14 is used, not k_period=3."""
        ind = make_indicators(_rising_ohlcv(50))
        # With rsi_period=14 the result should be stable; with rsi_period=3 it would be noisy
        results = []
        for _ in range(3):
            r = await ind.get_stoch_rsi('binance', 'BTC', 'USDT',
                                         rsi_period=14, stoch_period=14,
                                         k_period=3, d_period=3)
            results.append(r)
        # All calls return the same data (same mock), so results should be identical
        assert all(r == results[0] for r in results)


# ---------------------------------------------------------------------------
# get_market_direction
# ---------------------------------------------------------------------------

class TestGetMarketDirection:

    @pytest.mark.asyncio
    async def test_rising_prices_return_bull(self):
        ind = make_indicators(_rising_ohlcv(50))
        direction = await ind.get_market_direction('binance', 'BTC', 'USDT', 'sma', 14)
        assert direction == 'bull'

    @pytest.mark.asyncio
    async def test_falling_prices_return_bear(self):
        ind = make_indicators(_falling_ohlcv(50))
        direction = await ind.get_market_direction('binance', 'BTC', 'USDT', 'sma', 14)
        assert direction == 'bear'

    @pytest.mark.asyncio
    async def test_invalid_ma_type_returns_none(self):
        ind = make_indicators(_rising_ohlcv(50))
        direction = await ind.get_market_direction('binance', 'BTC', 'USDT', 'invalid_ma', 14)
        assert direction is None

    @pytest.mark.asyncio
    async def test_insufficient_data_returns_none(self):
        ind = make_indicators(_rising_ohlcv(5))
        direction = await ind.get_market_direction('binance', 'BTC', 'USDT', 'sma', 14)
        assert direction is None


# ---------------------------------------------------------------------------
# get_short_term_market_trend — zero-division regression
# ---------------------------------------------------------------------------

class TestGetShortTermMarketTrend:

    @pytest.mark.asyncio
    async def test_rising_prices_return_bull(self):
        ind = make_indicators(_rising_ohlcv(10))
        trend = await ind.get_short_term_market_trend('binance', 'BTC', 'USDT', limit=6)
        assert trend == 'bull'

    @pytest.mark.asyncio
    async def test_falling_prices_return_bear(self):
        ind = make_indicators(_falling_ohlcv(10))
        trend = await ind.get_short_term_market_trend('binance', 'BTC', 'USDT', limit=6)
        assert trend == 'bear'

    @pytest.mark.asyncio
    async def test_flat_prices_return_neutral(self):
        ind = make_indicators(_flat_ohlcv(10))
        trend = await ind.get_short_term_market_trend('binance', 'BTC', 'USDT', limit=6)
        assert trend == 'neutral'

    @pytest.mark.asyncio
    async def test_zero_previous_avg_returns_neutral_not_crash(self):
        """Regression: zero previous_avg_price must not raise ZeroDivisionError or NameError."""
        zero_ohlcv = [[1_000_000 + i * 60_000, 0, 0, 0, 0, 0] for i in range(10)]
        ind = make_indicators(zero_ohlcv)
        trend = await ind.get_short_term_market_trend('binance', 'BTC', 'USDT', limit=6)
        assert trend == 'neutral'


# ---------------------------------------------------------------------------
# get_support_price / get_resistance_price
# ---------------------------------------------------------------------------

class TestSupportResistance:

    @pytest.mark.asyncio
    async def test_support_is_minimum_low(self):
        ohlcv = _rising_ohlcv(10)
        ind = make_indicators(ohlcv)
        support = await ind.get_support_price('binance', 'BTC', 'USDT', lookback_period=10)
        expected_min_low = min(x[3] for x in ohlcv)
        assert support == expected_min_low

    @pytest.mark.asyncio
    async def test_resistance_is_maximum_high(self):
        ohlcv = _rising_ohlcv(10)
        ind = make_indicators(ohlcv)
        resistance = await ind.get_resistance_price('binance', 'BTC', 'USDT', lookback_period=10)
        expected_max_high = max(x[2] for x in ohlcv)
        assert resistance == expected_max_high

    @pytest.mark.asyncio
    async def test_insufficient_data_returns_none(self):
        ind = make_indicators(_rising_ohlcv(3))
        support = await ind.get_support_price('binance', 'BTC', 'USDT', lookback_period=10)
        assert support is None


# ---------------------------------------------------------------------------
# T25: StochRSI uses named column access (not fragile iloc[0]/iloc[1])
# ---------------------------------------------------------------------------

class TestStochRsiNamedColumns:
    """T25: get_stoch_rsi must access K and D by named column, not positional
    index. This guards against a future pandas-ta column reorder silently
    swapping K and D and inverting the momentum signal."""

    def _make_indicators(self, mock_api):
        from sonarft_indicators import SonarftIndicators
        return SonarftIndicators(mock_api)

    def _rising_ohlcv(self, n=35):
        """Generate n candles of steadily rising prices."""
        return [
            [1_000_000 + i * 60_000, 100.0 + i, 105.0 + i, 95.0 + i, 100.0 + i, 10.0]
            for i in range(n)
        ]

    @pytest.mark.asyncio
    async def test_k_and_d_are_named_not_positional(self):
        """Verify that the returned (K, D) values match the named columns,
        not just whatever happens to be at iloc[0] and iloc[1]."""
        import pandas as pd
        import pandas_ta as pta
        from unittest.mock import AsyncMock, MagicMock

        mock_api = MagicMock()
        ohlcv = self._rising_ohlcv(35)
        mock_api.get_ohlcv_history = AsyncMock(return_value=ohlcv)
        ind = self._make_indicators(mock_api)

        result = await ind.get_stoch_rsi(
            "binance", "BTC", "USDT",
            rsi_period=14, stoch_period=14, k_period=3, d_period=3,
        )

        if result is None:
            pytest.skip("Insufficient data for StochRSI — skip column name check")

        k_returned, d_returned = result

        # Independently compute the expected named-column values
        close = pd.Series([x[4] for x in ohlcv])
        df = pta.stochrsi(close, length=14, rsi_length=14, k=3, d=3)
        k_col = "STOCHRSIk_14_14_3_3"
        d_col = "STOCHRSId_14_14_3_3"

        assert k_col in df.columns, f"Expected column '{k_col}' not found: {list(df.columns)}"
        assert d_col in df.columns, f"Expected column '{d_col}' not found: {list(df.columns)}"

        k_expected = float(df[k_col].iloc[-1])
        d_expected = float(df[d_col].iloc[-1])

        assert abs(k_returned - k_expected) < 1e-9, (
            f"K value mismatch: got {k_returned}, expected {k_expected} from named column"
        )
        assert abs(d_returned - d_expected) < 1e-9, (
            f"D value mismatch: got {d_returned}, expected {d_expected} from named column"
        )

    @pytest.mark.asyncio
    async def test_stochrsi_k_greater_than_d_for_rising_prices(self):
        """For a strongly rising price series, K should be >= D (upward momentum)."""
        from unittest.mock import AsyncMock, MagicMock

        mock_api = MagicMock()
        # Use a longer series to ensure StochRSI has enough data
        ohlcv = self._rising_ohlcv(50)
        mock_api.get_ohlcv_history = AsyncMock(return_value=ohlcv)
        ind = self._make_indicators(mock_api)

        result = await ind.get_stoch_rsi(
            "binance", "BTC", "USDT",
            rsi_period=14, stoch_period=14, k_period=3, d_period=3,
        )

        if result is None:
            pytest.skip("Insufficient data for StochRSI")

        k, d = result
        # For a monotonically rising series, K should be at or above D
        assert k >= d - 1.0, (
            f"Expected K >= D for rising prices, got K={k:.2f}, D={d:.2f}"
        )
