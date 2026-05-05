"""
SonarFT Trade Executor Module
Async task management for trade execution dispatch and monitoring.
"""

import asyncio
import logging
import os

from sonarft_execution import SonarftExecution
from sonarft_metrics import log_risk_event, log_session_pnl

# Maximum number of concurrently in-flight trade tasks per executor instance.
# Prevents unbounded memory growth under high trade frequency.
# Override via SONARFT_MAX_CONCURRENT_TRADES environment variable.
_MAX_CONCURRENT_TRADES = int(os.environ.get("SONARFT_MAX_CONCURRENT_TRADES", "10"))


class TradeExecutor:
    """Dispatches trade execution as async tasks and monitors completion."""

    def __init__(self, sonarft_execution: SonarftExecution, logger=None):
        self.sonarft_execution = sonarft_execution
        self.logger = logger or logging.getLogger(__name__)
        self.trade_tasks = []
        self.monitor_task = None
        self._search_ref = None  # set by SonarftSearch after construction
        self._session_trades = 0
        self._session_profit = 0.0

    async def start(self):
        """Start the background monitor task. Must be called from an async context."""
        self.monitor_task = asyncio.create_task(self.monitor_trade_tasks())

    def execute_trade(self, botid, trade_data: dict) -> None:
        """Dispatch a trade as an async task, subject to the concurrent task limit.

        Skips dispatch and logs a risk event if the number of active (not-done)
        tasks has reached SONARFT_MAX_CONCURRENT_TRADES (default: 10).
        """
        active_count = sum(1 for t in self.trade_tasks if not t.done())
        if active_count >= _MAX_CONCURRENT_TRADES:
            self.logger.warning(
                f"Bot {botid}: concurrent trade limit ({_MAX_CONCURRENT_TRADES}) reached "
                f"({active_count} active) — skipping dispatch"
            )
            log_risk_event(
                str(botid),
                "concurrent_limit",
                f"active={active_count} >= limit={_MAX_CONCURRENT_TRADES}",
            )
            return
        trade_task = asyncio.create_task(
            self.sonarft_execution.execute_trade(botid, trade_data)
        )
        trade_task.botid = botid  # Attach the botid to the task
        self.trade_tasks.append(trade_task)

    async def monitor_trade_tasks(self):
        try:
            while True:
                done_tasks = [t for t in self.trade_tasks if t.done()]
                self.trade_tasks = [t for t in self.trade_tasks if not t.done()]
                for task in done_tasks:
                    try:
                        result = task.result()
                        self.logger.info(f"Trade task result: {result}")
                        # result is now a dict: {"success": bool, "profit": float}
                        if isinstance(result, dict):
                            profit = result.get("profit", 0.0)
                            self._session_trades += 1
                            self._session_profit += profit
                            if self._search_ref is not None:
                                await self._search_ref.record_trade_result(profit)
                            botid = getattr(task, "botid", "")
                            log_session_pnl(
                                botid=str(botid),
                                session_trades=self._session_trades,
                                session_profit=self._session_profit,
                                daily_loss=getattr(
                                    self._search_ref, "daily_loss_accumulated", 0.0
                                ),
                            )
                    except asyncio.CancelledError:
                        self.logger.info("Trade task was cancelled")
                    except Exception:
                        self.logger.exception("Trade task raised an exception")
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.logger.info("monitor_trade_tasks cancelled — exiting")

    async def shutdown(self):
        """Cancel monitor task and await all in-flight trade tasks. Called by stop_bot()."""
        # 1. Cancel the background monitor
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.logger.info("monitor_trade_tasks stopped")

        # 2. Cancel and await in-flight trade tasks
        if self.trade_tasks:
            self.logger.info(
                f"Cancelling {len(self.trade_tasks)} in-flight trade tasks..."
            )
            for task in self.trade_tasks:
                task.cancel()
            await asyncio.gather(*self.trade_tasks, return_exceptions=True)
            self.trade_tasks.clear()
            self.logger.info("All trade tasks cancelled")

    def cancel_trade(self, botid):
        # Cancel the task for the given botid
        tasks_to_remove = [t for t in self.trade_tasks if t.botid == botid]
        if tasks_to_remove:
            self.logger.info(
                f"Cancelling {len(tasks_to_remove)} trade task(s) for bot {botid}"
            )
            for task in tasks_to_remove:
                task.cancel()
                self.trade_tasks.remove(task)
        else:
            self.logger.debug(f"No active trade tasks found for bot {botid}")
