"""
SonarFT Trade Executor Module
Async task management for trade execution dispatch and monitoring.
"""
import logging
import asyncio
from typing import Dict

from sonarft_execution import SonarftExecution


class TradeExecutor:
    """Dispatches trade execution as async tasks and monitors completion."""

    def __init__(self, sonarft_execution: SonarftExecution, logger=None):
        self.sonarft_execution = sonarft_execution
        self.logger = logger or logging.getLogger(__name__)
        self.trade_tasks = []
        self.monitor_task = None
        self._search_ref = None  # set by SonarftSearch after construction

    async def start(self):
        """Start the background monitor task. Must be called from an async context."""
        self.monitor_task = asyncio.create_task(self.monitor_trade_tasks())

    def execute_trade(self, botid, trade_data: Dict) -> None:
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
                        # Notify search of trade outcome for daily loss tracking
                        if self._search_ref is not None and isinstance(result, dict) and 'profit' in result:
                            self._search_ref.record_trade_result(result['profit'])
                    except asyncio.CancelledError:
                        self.logger.info("Trade task was cancelled")
                    except Exception as e:
                        self.logger.error(f"Trade task raised an exception: {e}")
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
            self.logger.info(f"Cancelling {len(self.trade_tasks)} in-flight trade tasks...")
            for task in self.trade_tasks:
                task.cancel()
            await asyncio.gather(*self.trade_tasks, return_exceptions=True)
            self.trade_tasks.clear()
            self.logger.info("All trade tasks cancelled")

    def cancel_trade(self, botid):
        # Cancel the task for the given botid
        tasks_to_remove = [t for t in self.trade_tasks if t.botid == botid]
        for task in tasks_to_remove:
            task.cancel()
            self.trade_tasks.remove(task)
