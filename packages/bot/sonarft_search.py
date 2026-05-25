"""
SonarFT Search Module
Orchestrates trade search, validation, and execution dispatch across symbols.
"""
import asyncio
import logging
import os
import time as _time

from sonarft_execution import SonarftExecution
from sonarft_math import SonarftMath
from sonarft_prices import SonarftPrices
from sonarft_validators import SonarftValidators
from trade_processor import TradeProcessor

# Split modules — re-exported for backward compatibility

# Daily loss helpers delegate to SonarftHelpers (single source of truth).
from sonarft_helpers import SonarftHelpers as _SonarftHelpers



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
        symbols: list,
        profit_percentage_threshold: float,
        is_simulating_trade: bool,
        logger=None,
        max_daily_loss: float = 0.0,
        slippage_buffer: float = 0.0,
        max_daily_trades: int = 0,
    ):
        self.logger = logger or logging.getLogger(__name__)

        self.trade_processor = TradeProcessor(
            sonarft_validators, sonarft_execution, sonarft_math, sonarft_prices, logger,
            slippage_buffer=slippage_buffer,
        )

        self.trade_amount = trade_amount
        self.symbols = symbols
        self.profit_percentage_threshold = profit_percentage_threshold
        self.is_simulating_trade = is_simulating_trade
        self.max_daily_loss = max_daily_loss
        self.max_daily_trades = max_daily_trades
        self._daily_trades_count = 0
        self._loss_reset_date = _time.strftime('%Y-%m-%d', _time.localtime())
        # Load persisted daily loss so restarts don't reset the counter mid-day
        self._botid: str | None = None  # set after bot creation via set_botid()
        self.daily_loss_accumulated = 0.0
        self._paused = False
        # Alert callback — set by SonarftBot after construction (same pattern
        # as SonarftExecution._alert_callback). Fires once per halt event.
        self._alert_callback = None
        self._halt_alerted: bool = False  # prevents repeated alerts per halt period

        self.latest_executed_buy_price_order = []

    async def set_botid(self, botid: str) -> None:
        """Set the botid and load any persisted daily loss for today."""
        self._botid = botid
        self.daily_loss_accumulated = await _SonarftHelpers.load_daily_loss(botid, self._loss_reset_date)

    async def start(self):
        """Start background tasks. Must be called once from an async context after construction."""
        await self.trade_processor.start()
        # Wire the daily loss callback so TradeExecutor can notify us of trade results
        self.trade_processor.trade_executor._search_ref = self

    async def record_trade_result(self, profit: float) -> None:
        """Accumulate profit/loss and trade count. Call after each completed trade."""
        await self._check_daily_reset()
        # Count every completed trade (win or loss)
        self._daily_trades_count += 1
        if profit < 0:
            self.daily_loss_accumulated += abs(profit)
            botid = getattr(self, '_botid', None)
            if botid:
                await _SonarftHelpers.save_daily_loss(botid, self._loss_reset_date, self.daily_loss_accumulated)

    async def _check_daily_reset(self) -> None:
        """Reset daily loss accumulator and trade count if the date has changed."""
        today = _time.strftime('%Y-%m-%d', _time.localtime())
        if today != self._loss_reset_date:
            self.logger.info(
                f"Daily reset: {self._loss_reset_date} -> {today} "
                f"(loss: {self.daily_loss_accumulated}, trades: {self._daily_trades_count})"
            )
            self.daily_loss_accumulated = 0.0
            self._daily_trades_count = 0
            self._loss_reset_date = today
            self._halt_alerted = False  # new day — re-enable halt alert
            botid = getattr(self, '_botid', None)
            if botid:
                await _SonarftHelpers.save_daily_loss(botid, today, 0.0)

    async def is_halted(self) -> bool:
        """Returns True if the daily loss limit or daily trade limit has been reached.
        Sends a webhook alert once per halt period (reset on daily rollover).
        """
        await self._check_daily_reset()
        if self.max_daily_loss > 0 and self.daily_loss_accumulated >= self.max_daily_loss:
            self.logger.warning(
                f"Daily loss limit reached: {self.daily_loss_accumulated} >= {self.max_daily_loss}. Halting trades."
            )
            await self._maybe_send_halt_alert(
                f"SonarFT Bot {self._botid}: daily loss limit reached "
                f"({self.daily_loss_accumulated:.4f} >= {self.max_daily_loss}). Trading halted."
            )
            return True
        if self.max_daily_trades > 0 and self._daily_trades_count >= self.max_daily_trades:
            self.logger.warning(
                f"Daily trade limit reached: {self._daily_trades_count} >= {self.max_daily_trades}. Halting trades."
            )
            await self._maybe_send_halt_alert(
                f"SonarFT Bot {self._botid}: daily trade limit reached "
                f"({self._daily_trades_count} >= {self.max_daily_trades}). Trading halted."
            )
            return True
        return False

    async def _maybe_send_halt_alert(self, message: str) -> None:
        """Send a halt alert once per halt period. Suppresses repeated alerts
        on subsequent cycles until the daily reset clears _halt_alerted."""
        if self._halt_alerted:
            return
        self._halt_alerted = True
        if self._alert_callback:
            try:
                await self._alert_callback(message)
            except Exception:
                self.logger.exception("Failed to send halt alert")

    def pause(self):
        """Pause trading without stopping the bot. Search cycles will be skipped."""
        self._paused = True
        self.logger.warning("Trading PAUSED")

    def resume(self):
        """Resume trading after a pause."""
        self._paused = False
        self.logger.info("Trading RESUMED")

    @property
    def is_paused(self) -> bool:
        return self._paused

    async def search_trades(self, botid) -> None:
        """Search for the best trades for the given symbols and trade amounts."""
        if self._paused:
            return
        if await self.is_halted():
            return

        # Warm-up logging: on the first cycle, note that indicators need time to stabilise.
        # MACD requires ~45 candles (45 minutes at 1m timeframe) before producing valid signals.
        if not getattr(self, '_warmup_logged', False):
            self.logger.info(
                "Bot warming up — indicators need ~45 candles (45 min at 1m) before first valid signal. "
                "Trades will be skipped until RSI, MACD, and StochRSI are ready."
            )
            self._warmup_logged = True

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
