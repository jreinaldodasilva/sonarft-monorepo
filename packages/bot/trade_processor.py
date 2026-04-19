"""
SonarFT Trade Processor Module
Per-symbol price fetching, adjustment, profit check, and execution trigger.
"""
import logging
import asyncio
from typing import List

from sonarft_math import SonarftMath
from sonarft_prices import SonarftPrices
from sonarft_validators import SonarftValidators
from sonarft_execution import SonarftExecution
from trade_validator import TradeValidator
from trade_executor import TradeExecutor


class TradeProcessor:
    """Processes symbols and trade combinations, dispatching profitable trades."""

    def __init__(
        self,
        sonarft_validators: SonarftValidators,
        sonarft_execution: SonarftExecution,
        sonarft_math: SonarftMath,
        sonarft_prices: SonarftPrices,
        logger=None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.sonarft_math = sonarft_math
        self.sonarft_prices = sonarft_prices
        self.trade_validator = TradeValidator(sonarft_validators, logger)
        self.trade_executor = TradeExecutor(sonarft_execution, logger)

    async def start(self):
        """Start background tasks. Must be called from an async context."""
        await self.trade_executor.start()

    async def process_symbol(self, botid, symbol, trade_amount, percentage_threshold):
        if trade_amount <= 0:
            self.logger.warning(f"Bot {botid}: trade_amount {trade_amount} is invalid, skipping symbol")
            return

        self.logger.info(f"(v1009) - Bot {botid}: NEW TRADE SEARCHING...")
        self.logger.info(
            "-----------------------------------------------------------\n"
        )

        base = symbol["base"]
        quotes = symbol["quotes"]
        for quote_index, quote in enumerate(quotes):
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
                        continue  # skip same-exchange combinations — no arbitrage possible
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
                await asyncio.gather(*futures, return_exceptions=True)

    async def process_trade_combination(
        self,
        botid,
        base: str,
        quote: str,
        trade_amount: float,
        buy_price_list: List,
        sell_price_list: List,
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

        self.logger.info(f"{base}/{quote}: Trade Amount {trade_amount}")
        self.logger.info(
            f"{base}/{quote}: Latest Buy: {latest_buy_price} - Latest Sell: {latest_sell_price}"
        )
        self.logger.info(
            f"{base}/{quote}: Target Buy: {trade_data['buy_price']} - Target Sell: {trade_data['sell_price']}"
        )
        self.logger.info(
            f"{base}/{quote}: Profit {profit} - Percentage: {profit_percentage}"
        )
        self.logger.info(
            "-----------------------------------------------------------\n"
        )

        # Verify if profit is above the profit percentage threshold
        if profit_percentage >= percentage_threshold:
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
                self.logger.info(
                    f"\n(v1009) - Bot {botid}: A NEW TRADE HAS BEEN FOUND!"
                )
                self.logger.info(
                    "------------------------------------------------------------------------------------\n"
                )
                self.trade_executor.execute_trade(botid, trade_data)
