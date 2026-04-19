"""
SonarFT Search Module
Orchestrates trade search, validation, and execution dispatch across symbols.
"""
import logging
import asyncio
import time as _time
from typing import Optional, Dict, List

from sonarft_math import SonarftMath
from sonarft_prices import SonarftPrices
from sonarft_validators import SonarftValidators
from sonarft_execution import SonarftExecution

# Split modules — re-exported for backward compatibility
from trade_validator import TradeValidator
from trade_executor import TradeExecutor
from trade_processor import TradeProcessor


class SonarftSearch:
    """
    SonarftSearch class is responsible for finding healthy trades and executing them.
    A healthy trade is a profitable trade with the lowest risk and the highest probability of successful execution.
    """

    def __init__(
        self,
        sonarft_math: SonarftMath,
        sonarft_prices: SonarftPrices,
        sonarft_validators: SonarftValidators,
        sonarft_execution: SonarftExecution,
        trade_amount: float,
        symbols: List,
        profit_percentage_threshold: float,
        is_simulating_trade: bool,
        logger=None,
        max_daily_loss: float = 0.0,
    ):
        self.logger = logger or logging.getLogger(__name__)

        self.trade_processor = TradeProcessor(
            sonarft_validators, sonarft_execution, sonarft_math, sonarft_prices, logger
        )

        self.trade_amount = trade_amount
        self.symbols = symbols
        self.profit_percentage_threshold = profit_percentage_threshold
        self.is_simulating_trade = is_simulating_trade
        self.max_daily_loss = max_daily_loss
        self.daily_loss_accumulated = 0.0
        self._loss_reset_date = _time.strftime('%Y-%m-%d', _time.localtime())

        self.latest_executed_buy_price_order = []

    async def start(self):
        """Start background tasks. Must be called once from an async context after construction."""
        await self.trade_processor.start()
        # Wire the daily loss callback so TradeExecutor can notify us of trade results
        self.trade_processor.trade_executor._search_ref = self

    def record_trade_result(self, profit: float):
        """Accumulate profit/loss. Call after each completed trade."""
        self._check_daily_reset()
        if profit < 0:
            self.daily_loss_accumulated += abs(profit)

    def _check_daily_reset(self):
        """Reset daily loss accumulator if the date has changed."""
        today = _time.strftime('%Y-%m-%d', _time.localtime())
        if today != self._loss_reset_date:
            self.logger.info(
                f"Daily loss reset: {self._loss_reset_date} -> {today} "
                f"(accumulated: {self.daily_loss_accumulated})"
            )
            self.daily_loss_accumulated = 0.0
            self._loss_reset_date = today

    def is_halted(self) -> bool:
        """Returns True if the daily loss limit has been reached."""
        self._check_daily_reset()
        if self.max_daily_loss > 0 and self.daily_loss_accumulated >= self.max_daily_loss:
            self.logger.warning(
                f"Daily loss limit reached: {self.daily_loss_accumulated} >= {self.max_daily_loss}. Halting trades."
            )
            return True
        return False

    async def search_trades(self, botid) -> None:
        """Search for the best trades for the given symbols and trade amounts."""
        if self.is_halted():
            return

        futures = [
            self.trade_processor.process_symbol(
                botid, symbol, self.trade_amount, self.profit_percentage_threshold
            )
            for symbol in self.symbols
        ]
        results = await asyncio.gather(*futures, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Error while searching for trades: {result}\n")
