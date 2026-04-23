"""
SonarFT Prices Module
VWAP calculation, weighted price adjustment, spread logic, and support/resistance.
"""
import asyncio
import logging
import math

from models import vwap
from sonarft_api_manager import SonarftApiManager
from sonarft_indicators import SonarftIndicators


class SonarftPrices:

    def __init__(self, api_manager: SonarftApiManager, sonarft_indicators: SonarftIndicators, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.api_manager = api_manager
        self.sonarft_indicators = sonarft_indicators
        self.strategy: str = 'arbitrage'  # set by SonarftBot from config
        self.active_indicators: list = ['rsi', 'stoch rsi', 'macd']  # default: all on

    def _indicator_active(self, name: str) -> bool:
        """Return True if the named indicator is in the active set (case-insensitive)."""
        return any(name.lower() in s.lower() for s in self.active_indicators)

    async def weighted_adjust_prices(
        self, botid, buy_exchange: str, sell_exchange, base: str, quote: str,
        target_buy_price, target_sell_price,
        last_buy_price, last_sell_price,
        volatility_risk_factor=0.001,
    ):
        """Fetch indicators then dispatch to the configured strategy."""
        period = 14
        rsi_period = 14
        stoch_period = 14
        k_period = 3
        d_period = 3
        order_book_depth = 6

        use_stoch = self._indicator_active('stoch rsi')
        try:
            (
                market_movement_buy,
                market_movement_sell,
                market_direction_buy,
                market_direction_sell,
                market_rsi_buy,
                market_rsi_sell,
                stoch_buy,
                stoch_sell,
                market_trend_buy,
                market_trend_sell,
                volatility_buy_raw,
                volatility_sell_raw,
                order_book_buy,
                order_book_sell,
                support_price,
                resistance_price,
            ) = await asyncio.wait_for(
                asyncio.gather(
                    self.sonarft_indicators.market_movement(buy_exchange, base, quote, order_book_depth),
                    self.sonarft_indicators.market_movement(sell_exchange, base, quote, order_book_depth),
                    self.sonarft_indicators.get_market_direction(buy_exchange, base, quote, 'sma', period),
                    self.sonarft_indicators.get_market_direction(sell_exchange, base, quote, 'sma', period),
                    self.sonarft_indicators.get_rsi(buy_exchange, base, quote, rsi_period),
                    self.sonarft_indicators.get_rsi(sell_exchange, base, quote, rsi_period),
                    self.sonarft_indicators.get_stoch_rsi(buy_exchange, base, quote, rsi_period, stoch_period, k_period, d_period) if use_stoch else asyncio.sleep(0, result=None),
                    self.sonarft_indicators.get_stoch_rsi(sell_exchange, base, quote, rsi_period, stoch_period, k_period, d_period) if use_stoch else asyncio.sleep(0, result=None),
                    self.sonarft_indicators.get_short_term_market_trend(buy_exchange, base, quote, '1m', 6, 0.001),
                    self.sonarft_indicators.get_short_term_market_trend(sell_exchange, base, quote, '1m', 6, 0.001),
                    self.sonarft_indicators.get_volatility(buy_exchange, base, quote),
                    self.sonarft_indicators.get_volatility(sell_exchange, base, quote),
                    self.sonarft_indicators.get_order_book(buy_exchange, base, quote),
                    self.sonarft_indicators.get_order_book(sell_exchange, base, quote),
                    self.sonarft_indicators.get_support_price(buy_exchange, base, quote, 24),
                    self.sonarft_indicators.get_resistance_price(sell_exchange, base, quote, 24),
                ),
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            self.logger.warning(f"weighted_adjust_prices timed out after 30s for {base}/{quote} — skipping adjustment")
            return 0, 0, {}

        if self._indicator_active('stoch rsi') and (stoch_buy is None or stoch_sell is None):
            self.logger.warning(f"StochRSI unavailable for {base}/{quote}, skipping adjustment")
            return 0, 0, {}
        market_stoch_rsi_buy_k  = stoch_buy[0]  if stoch_buy  else 50.0
        market_stoch_rsi_buy_d  = stoch_buy[1]  if stoch_buy  else 50.0
        market_stoch_rsi_sell_k = stoch_sell[0] if stoch_sell else 50.0
        market_stoch_rsi_sell_d = stoch_sell[1] if stoch_sell else 50.0

        if self._indicator_active('rsi') and (market_rsi_buy is None or market_rsi_sell is None):
            self.logger.warning(f"RSI unavailable for {base}/{quote}, skipping adjustment")
            return 0, 0, {}
        market_rsi_buy  = market_rsi_buy  if market_rsi_buy  is not None else 50.0
        market_rsi_sell = market_rsi_sell if market_rsi_sell is not None else 50.0
        market_strength = (market_rsi_buy + market_rsi_sell) / 2

        vol_adj_buy, vol_adj_sell = await asyncio.gather(
            self.dynamic_volatility_adjustment(market_direction_buy, market_trend_buy, buy_exchange, base, quote),
            self.dynamic_volatility_adjustment(market_direction_sell, market_trend_sell, sell_exchange, base, quote),
        )
        volatility_buy = volatility_buy_raw * vol_adj_buy
        volatility_sell = volatility_sell_raw * vol_adj_sell

        if math.isnan(volatility_buy) or math.isnan(volatility_sell):
            self.logger.warning(f"NaN volatility for {base}/{quote}, skipping adjustment")
            return 0, 0, {}

        volatility = volatility_risk_factor * (volatility_buy + volatility_sell) / 2
        volatility_factor = volatility_risk_factor * market_strength
        weight = max(0.0, min(1.0, 1 - (volatility * volatility_factor)))

        depth = 3
        buy_weighted_price = self.get_weighted_price(order_book_buy['bids'], depth)
        sell_weighted_price = self.get_weighted_price(order_book_sell['asks'], depth)

        if buy_weighted_price == 0.0 or sell_weighted_price == 0.0:
            self.logger.warning(f"Zero-volume order book for {base}/{quote}, skipping adjustment")
            return 0, 0, {}

        # shared base blend — both strategies start from the same weighted price
        adjusted_buy_price = weight * target_buy_price + (1 - weight) * buy_weighted_price
        adjusted_sell_price = weight * target_sell_price + (1 - weight) * sell_weighted_price

        # dispatch to strategy-specific adjustment
        if self.strategy == 'market_making':
            adjusted_buy_price, adjusted_sell_price = self._adjust_market_making(
                adjusted_buy_price, adjusted_sell_price,
                market_direction_buy, market_direction_sell,
                market_trend_buy, market_trend_sell,
                market_rsi_buy, market_rsi_sell,
                market_stoch_rsi_buy_k, market_stoch_rsi_buy_d,
                market_stoch_rsi_sell_k, market_stoch_rsi_sell_d,
                volatility,
            )
        # arbitrage: no further adjustment — weight blend is sufficient

        if support_price is not None and adjusted_buy_price < support_price:
            adjusted_buy_price = support_price
        if resistance_price is not None and adjusted_sell_price > resistance_price:
            adjusted_sell_price = resistance_price

        self.logger.debug(f"BOT: {botid} | strategy={self.strategy} | BUY: {buy_exchange} -> SELL: {sell_exchange}")
        self.logger.debug(f"RSI buy={market_rsi_buy:.2f} sell={market_rsi_sell:.2f} | strength={market_strength:.2f}")
        self.logger.debug(f"Direction buy={market_direction_buy} sell={market_direction_sell} | trend buy={market_trend_buy} sell={market_trend_sell}")
        self.logger.debug(f"StochRSI buy_k={market_stoch_rsi_buy_k:.2f} sell_k={market_stoch_rsi_sell_k:.2f}")
        self.logger.debug(f"Support={support_price} resistance={resistance_price}")
        self.logger.debug(f"weight={weight:.6f} vol={volatility:.6f}")

        indicators = {
            'market_direction_buy': market_direction_buy,
            'market_direction_sell': market_direction_sell,
            'market_rsi_buy': market_rsi_buy,
            'market_rsi_sell': market_rsi_sell,
            'market_stoch_rsi_buy_k': market_stoch_rsi_buy_k,
            'market_stoch_rsi_buy_d': market_stoch_rsi_buy_d,
            'market_stoch_rsi_sell_k': market_stoch_rsi_sell_k,
            'market_stoch_rsi_sell_d': market_stoch_rsi_sell_d,
        }
        return adjusted_buy_price, adjusted_sell_price, indicators

    def _adjust_market_making(
        self,
        adjusted_buy_price: float, adjusted_sell_price: float,
        market_direction_buy: str, market_direction_sell: str,
        market_trend_buy: str, market_trend_sell: str,
        market_rsi_buy: float, market_rsi_sell: float,
        market_stoch_rsi_buy_k: float, market_stoch_rsi_buy_d: float,
        market_stoch_rsi_sell_k: float, market_stoch_rsi_sell_d: float,
        volatility: float,
    ) -> tuple[float, float]:
        """Apply directional spread adjustment for market-making strategy."""
        spread_increase_factor = getattr(self, 'spread_increase_factor', 1.00072)
        spread_decrease_factor = getattr(self, 'spread_decrease_factor', 0.99936)

        rsi_overbought = 72
        rsi_oversold = 28

        # bull+bull: widen spread — buy lower, sell higher
        if market_direction_buy == 'bull' and market_trend_buy == 'bull':
            if market_rsi_buy >= rsi_overbought and market_stoch_rsi_buy_k > market_stoch_rsi_buy_d:
                adjusted_buy_price *= spread_decrease_factor
            else:
                adjusted_buy_price *= spread_increase_factor
        if market_direction_sell == 'bull' and market_trend_sell == 'bull':
            if market_rsi_sell >= rsi_overbought and market_stoch_rsi_sell_k > market_stoch_rsi_sell_d:
                adjusted_sell_price *= spread_decrease_factor
            else:
                adjusted_sell_price *= spread_increase_factor

        # bear+bear: widen spread in the other direction
        if market_direction_buy == 'bear' and market_trend_buy == 'bear':
            if market_rsi_buy <= rsi_oversold and market_stoch_rsi_buy_k < market_stoch_rsi_buy_d:
                adjusted_buy_price *= spread_increase_factor
            else:
                adjusted_buy_price *= spread_decrease_factor
        if market_direction_sell == 'bear' and market_trend_sell == 'bear':
            if market_rsi_sell <= rsi_oversold and market_stoch_rsi_sell_k < market_stoch_rsi_sell_d:
                adjusted_sell_price *= spread_increase_factor
            else:
                adjusted_sell_price *= spread_decrease_factor

        return adjusted_buy_price, adjusted_sell_price

    def get_weighted_price(self, price_list: list, depth: int) -> float:
        """Returns the volume-weighted average price. Delegates to shared vwap()."""
        return vwap(price_list, depth)

    async def dynamic_volatility_adjustment(self, market_direction: str, market_trend: str, exchange: str, base: str, quote: str) -> float:
        adjustment_factor = 1.0
        if not self._indicator_active('macd') and not self._indicator_active('rsi'):
            return adjustment_factor
        macd_result = await self.sonarft_indicators.get_macd(exchange, base, quote) if self._indicator_active('macd') else None
        rsi = await self.sonarft_indicators.get_rsi(exchange, base, quote) if self._indicator_active('rsi') else None
        if macd_result is None and rsi is None:
            return adjustment_factor
        macd = macd_result[0] if macd_result else None
        if market_direction == 'bear' and market_trend == 'bull':
            adjustment_factor = 0.75 if (macd is not None and macd < 0) else 1.0
        elif market_direction == 'bull' and market_trend == 'bear':
            adjustment_factor = 0.5 if (rsi is not None and rsi > 70) else 1.0
        elif market_direction == 'bull' and market_trend == 'bull':
            adjustment_factor = 0.25 if (macd is not None and macd > 0 and rsi is not None and rsi < 30) else 1.0
        elif market_direction == 'bear' and market_trend == 'bear':
            adjustment_factor = 1.75 if (macd is not None and macd < 0 and rsi is not None and rsi > 70) else 1.0
        return adjustment_factor


    async def get_the_latest_prices(self, base: str, quote: str, trade_amount: float, weight) -> tuple[list, list] | None:
        latest_prices = await self.get_latest_prices(base, quote, weight)
        if not latest_prices:
            self.logger.error(
                f"Could not find latest prices for {base}/{quote}")

        target_buy_prices, target_sell_prices = self.get_target_buy_and_sell_prices(
            latest_prices)

        if target_buy_prices is None or target_sell_prices is None:
            self.logger.error(
                f"Could not find best buy and sell prices for {base}/{quote}")

        return target_buy_prices, target_sell_prices

    async def get_latest_prices(self, base: str, quote: str, weight) -> list:
        """
        Get the latest prices for a symbol combination
        """
        latest_prices = await self.api_manager.get_latest_prices(
            base, quote, weight)
        return latest_prices

    def get_target_buy_and_sell_prices(self, filtered_latest_prices: list) -> tuple[list, list]:
        """
        Get the buy and sell prices.
        """
        target_buy_prices = sorted(filtered_latest_prices, key=lambda x: x[1])
        target_sell_prices = sorted(
            filtered_latest_prices, key=lambda x: x[2], reverse=True)

        return target_buy_prices, target_sell_prices
