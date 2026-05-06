"""
SonarFT Indicators Module
Technical indicators: RSI, MACD, StochRSI, SMA, volatility, order book analysis.
"""
import logging
import time as _time

import numpy as np
import pandas as pd
import pandas_ta as pta
from models import percentage_difference as _percentage_difference
from sonarft_api_manager import SonarftApiManager

# Indicator cache TTL in seconds (matches 1m OHLCV candle duration)
_INDICATOR_CACHE_TTL = 60


class SonarftIndicators:
    def __init__(self, api_manager: SonarftApiManager, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.api_manager = api_manager

        self.spread_rate_threshold = 0.01
        self.price_rate_threshold = 0.01
        self.previous_spread: dict = {}  # per-symbol: {"exchange:base/quote": spread}
        self._indicator_cache: dict = {}  # key -> (expires_at, value)

    def _cached(self, key: str, ttl: float = _INDICATOR_CACHE_TTL):
        """Return cached value if still valid, else None."""
        entry = self._indicator_cache.get(key)
        if entry and _time.monotonic() < entry[0]:
            return entry[1], True
        return None, False

    def _cache_set(self, key: str, value, ttl: float = _INDICATOR_CACHE_TTL):
        """Store value in indicator cache."""
        if len(self._indicator_cache) >= 500:
            oldest = next(iter(self._indicator_cache))
            del self._indicator_cache[oldest]
        self._indicator_cache[key] = (_time.monotonic() + ttl, value)

    def get_profit_factor(self, volatility: float, min_spread: float = 0.99912, max_spread: float = 0.99972) -> float:
        """
        Calculate a dynamic spread factor based on market volatility.
        """
        try:
            normalized_volatility = min(max(volatility, 0), 1)

            # Calculate the spread factor as a linear interpolation between the minimum and maximum spread
            spread_factor = min_spread + \
                (max_spread - min_spread) * normalized_volatility

            return spread_factor
        except Exception:
            self.logger.exception("Error calculating profit factor")
            return None

    async def get_support_price(self, exchange_id, base, quote, lookback_period=24, timeframe='1h'):
        """
        Calculate support level based on historical data over the lookback_period.
        """
        try:
            history_data = await self.get_history(exchange_id, base, quote, timeframe, lookback_period)

            # Ensure there are enough periods to calculate
            if history_data is None or len(history_data) < lookback_period:
                return None

            # 'Low' price is at index 3 in OHLCV data
            low_prices = [x[3] for x in history_data]
            return min(low_prices)
        except Exception:
            self.logger.exception("Error get_support_price")
            return None

    async def get_resistance_price(self, exchange_id, base, quote, lookback_period=24, timeframe='1h'):
        """
        Calculate resistance level based on historical data over the lookback_period.
        """
        try:
            history_data = await self.get_history(exchange_id, base, quote, timeframe, lookback_period)

            # Ensure there are enough periods to calculate
            if history_data is None or len(history_data) < lookback_period:
                return None

            # 'High' price is at index 2 in OHLCV data
            high_prices = [x[2] for x in history_data]
            return max(high_prices)
        except Exception:
            self.logger.exception("Error get_resistance_price")
            return None

    async def get_rsi(self, exchange, base, quote, moving_average_period=14, timeframe='1m'):
        """Calculate the Relative Strength Index (RSI)."""
        cache_key = f"rsi:{exchange}:{base}/{quote}:{moving_average_period}:{timeframe}"
        cached, hit = self._cached(cache_key)
        if hit:
            return cached
        try:
            ohlcv = await self.get_history(exchange, base, quote, timeframe, moving_average_period+2)
            if not ohlcv or len(ohlcv) < moving_average_period:
                raise ValueError(f"Not enough data for RSI: need {moving_average_period}, have {len(ohlcv) if ohlcv else 0}")
            close_prices = pd.Series([x[4] for x in ohlcv])
            rsi = pta.rsi(close_prices, length=moving_average_period)
            value = rsi.iloc[-1]
            if pd.isna(value):
                self.logger.warning(f"RSI returned NaN for {exchange} {base}/{quote}")
                return None
            result = float(value)
            self._cache_set(cache_key, result)
            return result
        except Exception:
            self.logger.exception("Error get_rsi")
            return None


    async def get_stoch_rsi(self, exchange, base, quote, rsi_period=14, stoch_period=14, k_period=3, d_period=3, timeframe='1m'):
        """Calculate the Stochastic RSI."""
        cache_key = f"stochrsi:{exchange}:{base}/{quote}:{rsi_period}:{stoch_period}:{k_period}:{d_period}:{timeframe}"
        cached, hit = self._cached(cache_key)
        if hit:
            return cached
        try:
            ohlcv = await self.get_history(exchange, base, quote, timeframe, rsi_period + stoch_period + d_period + 1)
            if not ohlcv or len(ohlcv) < rsi_period + stoch_period:
                raise ValueError(f"Not enough data for StochRSI: need {rsi_period + stoch_period}, have {len(ohlcv) if ohlcv else 0}")
            close_prices = pd.Series([x[4] for x in ohlcv])
            # Use keyword arguments to avoid positional parameter mismatch.
            # pandas-ta stochrsi signature: (close, length, rsi_length, k, d)
            stoch_rsi = pta.stochrsi(close_prices, length=stoch_period, rsi_length=rsi_period, k=k_period, d=d_period)
            last_row = stoch_rsi.iloc[-1]
            k_val = last_row.iloc[0]
            d_val = last_row.iloc[1]
            if pd.isna(k_val) or pd.isna(d_val):
                self.logger.warning(f"StochRSI returned NaN for {exchange} {base}/{quote}")
                return None
            result = float(k_val), float(d_val)
            self._cache_set(cache_key, result)
            return result
        except Exception:
            self.logger.exception("Error get_stoch_rsi")
            return None


    async def get_market_direction(self, exchange_id, base, quote, ma_type='sma', moving_average_period=14, timeframe='1m'):
        """Get market direction via SMA or EMA."""
        cache_key = f"direction:{exchange_id}:{base}/{quote}:{ma_type}:{moving_average_period}:{timeframe}"
        cached, hit = self._cached(cache_key)
        if hit:
            return cached
        try:
            history_data = await self.get_history(exchange_id, base, quote, timeframe, moving_average_period+2)
            if not history_data or len(history_data) < moving_average_period:
                raise ValueError(f"Insufficient data for market direction: {exchange_id} {base}/{quote}")
            close_prices = pd.Series([x[4] for x in history_data])
            if ma_type == 'sma':
                moving_average = pta.sma(close_prices, length=moving_average_period)
            elif ma_type == 'ema':
                moving_average = pta.ema(close_prices, length=moving_average_period)
            else:
                raise ValueError(f"Invalid ma_type: {ma_type}")
            current_price = close_prices.iloc[-1]
            ma_value = moving_average.iloc[-1]
            if pd.isna(ma_value) or pd.isna(current_price):
                self.logger.warning(f"Market direction MA returned NaN for {exchange_id} {base}/{quote}")
                return 'neutral'
            if current_price > ma_value:
                result = 'bull'
            elif current_price < ma_value:
                result = 'bear'
            else:
                result = 'neutral'
            self._cache_set(cache_key, result)
            return result
        except Exception:
            self.logger.exception("Error get_market_direction")
            return None

    async def get_short_term_market_trend(self, exchange, base, quote, timeframe='1m', limit=6, threshold=0.001):
        """
        Calculate the percent price change between the most recent N OHLCV candles and the N candles
        before those, and determine if this change indicates a bull or bear market.
        """
        try:
            N = limit // 2  # we'll consider the last N periods and the N periods before those

            # Fetch OHLCV data
            ohlcv = await self.get_history(exchange, base, quote, timeframe, limit)

            # Ensure there are enough periods to calculate a change
            if len(ohlcv) < 2*N:
                raise ValueError(
                    f"Not enough data to calculate market trend. Need {2*N} periods, have {len(ohlcv)}.")

            # Get the close prices of the most recent N periods and the N periods before those
            current_prices = [period[4] for period in ohlcv[-N:]]
            previous_prices = [period[4] for period in ohlcv[-2*N:-N]]

            # Calculate the average price for each period
            current_avg_price = sum(current_prices) / N
            previous_avg_price = sum(previous_prices) / N

            # Guard against zero division before computing percent change
            if previous_avg_price == 0:
                return 'neutral'

            # Calculate the percent change
            price_change = 100 * (current_avg_price - previous_avg_price) / previous_avg_price

            # price_change is already in percent (multiplied by 100 above).
            # threshold is treated as a percent value (e.g. 0.1 = 0.1%).
            if price_change > threshold * 100:
                return 'bull'
            elif price_change < -(threshold * 100):
                return 'bear'
            else:
                return 'neutral'
        except Exception:
            self.logger.exception("Error get_short_term_market_trend")
            return None


    async def get_macd(self, exchange, base, quote, short_period=12, long_period=26, signal_period=9, warmup=10):
        """Calculate MACD."""
        cache_key = f"macd:{exchange}:{base}/{quote}:{short_period}:{long_period}:{signal_period}"
        cached, hit = self._cached(cache_key)
        if hit:
            return cached
        try:
            timeframe = '1m'
            ohlcv = await self.get_history(exchange, base, quote, timeframe, long_period + signal_period + warmup)
            if not ohlcv or len(ohlcv) < long_period + signal_period + warmup:
                raise ValueError(f"Not enough data for MACD: need {long_period + signal_period + warmup}, have {len(ohlcv) if ohlcv else 0}")
            close_prices = pd.Series([x[4] for x in ohlcv])
            macd = pta.macd(close_prices, short_period, long_period, signal_period)
            macd_col = f'MACD_{short_period}_{long_period}_{signal_period}'
            signal_col = f'MACDs_{short_period}_{long_period}_{signal_period}'
            hist_col = f'MACDh_{short_period}_{long_period}_{signal_period}'
            if macd_col not in macd.columns:
                raise KeyError(f"Expected MACD column '{macd_col}' not found. Available: {list(macd.columns)}")
            m, s, h = macd[macd_col].iloc[-1], macd[signal_col].iloc[-1], macd[hist_col].iloc[-1]
            if pd.isna(m) or pd.isna(s) or pd.isna(h):
                self.logger.warning(f"MACD returned NaN for {exchange} {base}/{quote}")
                return None
            result = float(m), float(s), float(h)
            self._cache_set(cache_key, result)
            return result
        except Exception:
            self.logger.exception("Error get_macd")
            return None


    async def get_price_change(self, exchange, base, quote, timeframe='1m', limit=20):
        """
        Calculate the percent price change between the most recent N OHLCV candles and the N candles before those.
        """
        N = limit // 2  # we'll consider the last N periods and the N periods before those

        # Fetch OHLCV data
        ohlcv = await self.get_history(exchange, base, quote, timeframe, limit)

        # Ensure there are enough periods to calculate a change
        if len(ohlcv) < 2*N:
            return None

        # Get the close prices of the most recent N periods and the N periods before those
        current_prices = [period[4] for period in ohlcv[-N:]]
        previous_prices = [period[4] for period in ohlcv[-2*N:-N]]

        # Calculate the average price for each period
        current_avg_price = sum(current_prices) / N
        previous_avg_price = sum(previous_prices) / N

        # Calculate the percent change
        price_change = 100 * (current_avg_price -
                              previous_avg_price) / previous_avg_price if previous_avg_price != 0 else 0

        return price_change

    async def market_movement(self, exchange_id: str, base: str, quote: str, order_book_depth) -> tuple[bool, str]:
        """
        Check if the market is experiencing a fast movement and determine the movement direction (bull or bear).
        Uses a per-call previous_spread local to avoid race conditions under concurrent symbol processing.
        """

        order_book = await self.get_order_book(exchange_id, base, quote)

        depth_bids = sum([float(bid[0])
                         for bid in order_book['bids'][:order_book_depth]])
        depth_asks = sum([float(ask[0])
                         for ask in order_book['asks'][:order_book_depth]])

        # Calculate the spread
        spread = depth_asks - depth_bids

        # Per-symbol previous_spread to avoid race conditions under concurrent processing
        spread_key = f"{exchange_id}:{base}/{quote}"
        previous = self.previous_spread.get(spread_key, spread)
        self.previous_spread[spread_key] = spread
        spread_rate = (spread - previous) / previous if previous != 0 else 0

        direction = "bull" if depth_bids > depth_asks else "bear"

        if abs(spread_rate) > self.spread_rate_threshold:
            return "fast", direction

        return "slow", direction

    async def get_historical_volume(self, exchange_id: str, base: str, quote: str, timeframe, limit) -> float:
        """
        Returns the most recent candle's volume for the given exchange and symbol.
        The limit parameter controls how many candles are fetched; only the last candle's volume is returned.
        """
        ohlcv = await self.get_history(exchange_id, base, quote, timeframe, limit)
        if not ohlcv:
            return 0.0
        # OHLCV format: [timestamp, open, high, low, close, volume] — index -1 is most recent
        return ohlcv[-1][5]

    async def get_current_volume(self, exchange_id: str, base: str, quote: str, depth: int = 10) -> tuple[float, float]:
        """
        Calculate the total volume of the bid and ask orders up to a certain depth in the order book.
        """
        order_book = await self.get_order_book(exchange_id, base, quote)

        bid_volume = sum(volume for price,
                         volume in order_book['bids'][:depth])
        ask_volume = sum(volume for price,
                         volume in order_book['asks'][:depth])

        return bid_volume, ask_volume

    async def get_liquidity(self, exchange_id: str, base: str, quote: str) -> float:
        """
        Calculate a normalised liquidity score for the given exchange and market pair.
        Computed as total order book volume divided by the mid-price, then clamped to [0, 1]
        relative to a reference volume of 100 units.
        """
        order_book = await self.get_order_book(exchange_id, base, quote)
        if not order_book:
            return 0.0
        bids = order_book['bids']
        asks = order_book['asks']
        if not bids or not asks:
            return 0.0

        mid_price = (bids[0][0] + asks[0][0]) / 2
        if mid_price == 0:
            return 0.0

        bid_volume_sum = sum(volume for _, volume in bids)
        ask_volume_sum = sum(volume for _, volume in asks)
        total_volume = bid_volume_sum + ask_volume_sum

        # Normalise: 100 units of base currency at mid-price = liquidity score of 1.0
        reference_volume = 100.0
        normalized_liquidity = min(total_volume / reference_volume, 1.0)
        return normalized_liquidity

    async def get_volatility(self, exchange_id: str, base: str, quote: str) -> float:
        """
        Calculate volatility as the normalised standard deviation of order book
        price deviations from the mid-price, expressed as a fraction of mid-price.

        Returns a dimensionless value (e.g. 0.001 = 0.1% spread dispersion)
        that is scale-independent across all asset price ranges.
        """
        order_book = await self.get_order_book(exchange_id, base, quote)
        if order_book is None:
            return 0.0

        bids = order_book['bids']
        asks = order_book['asks']

        bid_prices = [price for price, _ in bids]
        ask_prices = [price for price, _ in asks]

        if not bid_prices or not ask_prices:
            return 0.0

        mid_price = (max(bid_prices) + min(ask_prices)) / 2
        if mid_price == 0:
            return 0.0

        price_changes = [abs(price - mid_price) for price in bid_prices + ask_prices]

        # Normalise by mid_price so the result is scale-independent
        # (e.g. BTC at $60,000 and SHIB at $0.00001 produce comparable values)
        volatility = np.std(price_changes) / mid_price

        if np.isnan(volatility):
            return 0.0

        return volatility

    async def get_past_performance(self, exchange: str, base: str, quote: str, lookback_period: int = 24) -> float:
        """
        Calculate the past performance for the given exchange and market pair.
        Compares the most recent close price to the oldest close price in the lookback window.
        """
        timeframe = "1m"
        historical_data = await self.get_history(exchange, base, quote, timeframe, lookback_period)
        if not historical_data or len(historical_data) < 2:
            return 0.5  # neutral

        # OHLCV: index -1 = most recent, index 0 = oldest
        current_price = historical_data[-1][4]
        past_price = historical_data[0][4]

        if past_price == 0:
            return 0.5

        performance = (current_price - past_price) / past_price
        normalized_performance = (performance + 1) / 2
        return normalized_performance

    # @lru_cache(maxsize=None)
    async def get_order_book(self, exchange_id: str, base: str, quote: str) -> dict:
        order_book = await self.api_manager.get_order_book(
            exchange_id, base, quote)
        return order_book

    # @lru_cache(maxsize=None)
    async def get_trading_volume(self, exchange_id: str, base: str, quote: str) -> dict:
        trading_volume = await self.api_manager.get_trading_volume(
            exchange_id, base, quote)
        return trading_volume

    # @lru_cache(maxsize=None)
    async def get_history(self, exchange_id: str, base: str, quote: str, timeframe, limit) -> dict:
        history_data = await self.api_manager.get_ohlcv_history(
            exchange_id, base, quote, timeframe, None, limit)
        return history_data

    # @lru_cache(maxsize=None)
    async def get_trade_history(self, exchange_id: str, base: str, quote: str) -> dict:
        history_trade_data = await self.api_manager.get_trades_history(
            exchange_id, base, quote)
        return history_trade_data

    def percentage_difference(self, value1, value2):
        return _percentage_difference(value1, value2)
