"""
SonarFT Search Module
Orchestrates trade search, validation, and execution dispatch across symbols.
"""
import asyncio
import logging
import os
import sqlite3
import time as _time

from sonarft_execution import SonarftExecution
from sonarft_math import SonarftMath
from sonarft_prices import SonarftPrices
from sonarft_validators import SonarftValidators
from trade_processor import TradeProcessor

# Split modules — re-exported for backward compatibility

# Resolve the bot package directory so data paths work regardless of CWD.
_BOT_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.join(_BOT_DIR, 'sonarftdata', 'history', 'sonarft.db')


def _load_daily_loss_sync(botid: str, date: str) -> float:
    """Synchronous SQLite read — run via asyncio.to_thread, never on the event loop directly."""
    try:
        with sqlite3.connect(_DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_loss (
                    botid TEXT NOT NULL,
                    date  TEXT NOT NULL,
                    loss  REAL NOT NULL DEFAULT 0.0,
                    PRIMARY KEY (botid, date)
                )
            """)
            row = conn.execute(
                "SELECT loss FROM daily_loss WHERE botid = ? AND date = ?",
                (str(botid), date)
            ).fetchone()
        return float(row[0]) if row else 0.0
    except Exception:
        return 0.0


def _save_daily_loss_sync(botid: str, date: str, loss: float) -> None:
    """Synchronous SQLite upsert — run via asyncio.to_thread, never on the event loop directly."""
    try:
        with sqlite3.connect(_DB_PATH) as conn:
            conn.execute("""
                INSERT INTO daily_loss (botid, date, loss)
                VALUES (?, ?, ?)
                ON CONFLICT(botid, date) DO UPDATE SET loss = excluded.loss
            """, (str(botid), date, loss))
            conn.commit()
    except Exception:
        pass  # non-critical — loss tracking degrades gracefully


async def _load_daily_loss(botid: str, date: str) -> float:
    """Load persisted daily loss for botid/date from SQLite (async-safe)."""
    return await asyncio.to_thread(_load_daily_loss_sync, botid, date)


async def _save_daily_loss(botid: str, date: str, loss: float) -> None:
    """Upsert daily loss for botid/date into SQLite (async-safe)."""
    await asyncio.to_thread(_save_daily_loss_sync, botid, date, loss)


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
        self._loss_reset_date = _time.strftime('%Y-%m-%d', _time.localtime())
        # Load persisted daily loss so restarts don't reset the counter mid-day
        self._botid: str | None = None  # set after bot creation via set_botid()
        self.daily_loss_accumulated = 0.0
        self._paused = False

        self.latest_executed_buy_price_order = []

    async def set_botid(self, botid: str) -> None:
        """Set the botid and load any persisted daily loss for today."""
        self._botid = botid
        self.daily_loss_accumulated = await _load_daily_loss(botid, self._loss_reset_date)

    async def start(self):
        """Start background tasks. Must be called once from an async context after construction."""
        await self.trade_processor.start()
        # Wire the daily loss callback so TradeExecutor can notify us of trade results
        self.trade_processor.trade_executor._search_ref = self

    async def record_trade_result(self, profit: float) -> None:
        """Accumulate profit/loss. Call after each completed trade."""
        await self._check_daily_reset()
        if profit < 0:
            self.daily_loss_accumulated += abs(profit)
            botid = getattr(self, '_botid', None)
            if botid:
                await _save_daily_loss(botid, self._loss_reset_date, self.daily_loss_accumulated)

    async def _check_daily_reset(self) -> None:
        """Reset daily loss accumulator if the date has changed."""
        today = _time.strftime('%Y-%m-%d', _time.localtime())
        if today != self._loss_reset_date:
            self.logger.info(
                f"Daily loss reset: {self._loss_reset_date} -> {today} "
                f"(accumulated: {self.daily_loss_accumulated})"
            )
            self.daily_loss_accumulated = 0.0
            self._loss_reset_date = today
            botid = getattr(self, '_botid', None)
            if botid:
                await _save_daily_loss(botid, today, 0.0)

    async def is_halted(self) -> bool:
        """Returns True if the daily loss limit has been reached."""
        await self._check_daily_reset()
        if self.max_daily_loss > 0 and self.daily_loss_accumulated >= self.max_daily_loss:
            self.logger.warning(
                f"Daily loss limit reached: {self.daily_loss_accumulated} >= {self.max_daily_loss}. Halting trades."
            )
            return True
        return False

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
