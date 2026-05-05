"""
SonarFT Trade Processor Module
Per-symbol price fetching, adjustment, profit check, and execution trigger.
"""
import asyncio
import logging
import time as _time

from sonarft_execution import SonarftExecution
from sonarft_math import SonarftMath
from sonarft_metrics import log_cycle, log_signal
from sonarft_prices import SonarftPrices
from sonarft_validators import SonarftValidators
from trade_executor import TradeExecutor
from trade_validator import TradeValidator

_BOT_VERSION = "v1009"


class TradeProcessor:
    """Processes symbols and trade combinations, dispatching profitable trades."""

    def __init__(
        self,
        sonarft_validators: SonarftValidators,
        sonarft_execution: SonarftExecution,
        sonarft_math: SonarftMath,
        sonarft_prices: SonarftPrices,
        logger=None,
        slippage_buffer: float = 0.0,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.sonarft_math = sonarft_math
        self.sonarft_prices = sonarft_prices
        self.slippage_buffer = slippage_buffer
        self.trade_validator = TradeValidator(sonarft_validators, logger)
        self.trade_executor = TradeExecutor(sonarft_execution, logger)

    async def start(self):
        """Start background tasks. Must be called from an async context."""
        await self.trade_executor.start()

    async def process_symbol(self, botid, symbol, trade_amount, percentage_threshold):
        if trade_amount <= 0:
            self.logger.warning(f"Bot {botid}: trade_amount {trade_amount} is invalid, skipping symbol")
            return

        self.logger.debug(f"({_BOT_VERSION}) - Bot {botid}: NEW TRADE SEARCHING...")
        self.logger.debug(
            "-----------------------------------------------------------\n"
        )

        t0 = _time.monotonic()
        trades_found = 0
        trades_skipped = 0

        base = symbol["base"]
        quotes = symbol["quotes"]
        for _quote_index, quote in enumerate(quotes):
            (
                buy_prices_list,
                sell_prices_list,
            ) = await self.sonarft_prices.get_the_latest_prices(
                base, quote, trade_amount, weight=12
            )
            if not buy_prices_list or not sell_prices_list:
                return

            futures = []
            for buy_price_list in buy_prices_list:
                for sell_price_list in sell_prices_list:
                    if buy_price_list[0] == sell_price_list[0]:
                        continue  # skip same-exchange combinations
                    natural_buy  = buy_price_list[1]
                    natural_sell = sell_price_list[2]
                    if natural_sell <= natural_buy:
                        trades_skipped += 1
                        continue
                    futures.append(self.process_trade_combination(
                        botid,
                        base,
                        quote,
                        trade_amount,
                        buy_price_list,
                        sell_price_list,
                        percentage_threshold,
                    ))
            if futures:
                results = await asyncio.gather(*futures, return_exceptions=True)
                trades_found = sum(1 for r in results if r is True)

        cycle_ms = (_time.monotonic() - t0) * 1000
        log_cycle(str(botid), cycle_ms, trades_found, trades_skipped)

    async def process_trade_combination(
        self,
        botid,
        base: str,
        quote: str,
        trade_amount: float,
        buy_price_list: list,
        sell_price_list: list,
        percentage_threshold,
    ):
        """Process a trade combination."""
        buy_exchange, buy_price, buy_ask, latest_buy_price, _ = buy_price_list
        sell_exchange, sell_bid, sell_price, latest_sell_price, _ = sell_price_list

        (
            adjusted_buy_price,
            adjusted_sell_price,
            indicators,
        ) = await self.sonarft_prices.weighted_adjust_prices(
            botid,
            buy_exchange,
            sell_exchange,
            base,
            quote,
            buy_price,
            sell_price,
            latest_buy_price,
            latest_sell_price,
        )

        if adjusted_buy_price == 0 or adjusted_sell_price == 0:
            self.logger.warning(f"{base}/{quote}: Price adjustment returned zero — skipping combination")
            return

        # Update the buy and sell lists with the adjusted prices
        buy_price_list = (buy_exchange, adjusted_buy_price, *buy_price_list[2:])
        sell_price_list = (
            sell_exchange,
            sell_bid,
            adjusted_sell_price,
            *sell_price_list[3:],
        )

        profit, profit_percentage, trade_data = self.sonarft_math.calculate_trade(
            adjusted_buy_price,
            adjusted_sell_price,
            buy_price_list,
            sell_price_list,
            trade_amount,
            base,
            quote,
        )

        if trade_data is not None:
            trade_data.update(indicators)
        else:
            self.logger.warning(f"{base}/{quote}: calculate_trade returned no data — skipping")
            return

        self.logger.debug(f"{base}/{quote}: Trade Amount {trade_amount}")
        self.logger.debug(
            f"{base}/{quote}: Latest Buy: {latest_buy_price} - Latest Sell: {latest_sell_price}"
        )
        self.logger.debug(
            f"{base}/{quote}: Target Buy: {trade_data['buy_price']} - Target Sell: {trade_data['sell_price']}"
        )
        self.logger.debug(
            f"{base}/{quote}: Profit {profit} - Percentage: {profit_percentage}"
        )
        self.logger.debug(
            "-----------------------------------------------------------\n"
        )

        # Verify if profit is above the profit percentage threshold plus slippage buffer.
        # The buffer accounts for price movement during monitor_price() (up to 120s).
        effective_threshold = percentage_threshold + self.slippage_buffer
        if profit_percentage >= effective_threshold:
            has_requirements = (
                await self.trade_validator.has_requirements_for_success_carrying_out(
                    buy_exchange,
                    sell_exchange,
                    base,
                    quote,
                    adjusted_buy_price,
                    adjusted_sell_price,
                    trade_amount,
                )
            )

            if has_requirements:
                log_signal(
                    botid=str(botid),
                    symbol=f"{base}/{quote}",
                    buy_exchange=buy_exchange,
                    sell_exchange=sell_exchange,
                    signal_type="entry",
                    decision_reason="profit_threshold_met",
                    profit=profit,
                    profit_pct=profit_percentage,
                    rsi_buy=indicators.get("market_rsi_buy", 0.0) or 0.0,
                    rsi_sell=indicators.get("market_rsi_sell", 0.0) or 0.0,
                    direction_buy=indicators.get("market_direction_buy", "") or "",
                    direction_sell=indicators.get("market_direction_sell", "") or "",
                    weight=0.0,
                    volatility=0.0,
                )
                self.logger.info(
                    f"\n({_BOT_VERSION}) - Bot {botid}: A NEW TRADE HAS BEEN FOUND!"
                )
                self.logger.info(
                    "------------------------------------------------------------------------------------\n"
                )
                self.trade_executor.execute_trade(botid, trade_data)
                return True
        else:
            log_signal(
                botid=str(botid),
                symbol=f"{base}/{quote}",
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                signal_type="skipped",
                decision_reason="below_profit_threshold",
                profit=profit,
                profit_pct=profit_percentage,
                rsi_buy=indicators.get("market_rsi_buy", 0.0) or 0.0,
                rsi_sell=indicators.get("market_rsi_sell", 0.0) or 0.0,
                direction_buy=indicators.get("market_direction_buy", "") or "",
                direction_sell=indicators.get("market_direction_sell", "") or "",
                weight=0.0,
                volatility=0.0,
            )
        return False
