"""
Unit tests for TradeExecutor — task lifecycle, monitor loop, shutdown, P&L tracking.
Covers T-14 (TradeExecutor test coverage).
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_executor(max_trades=10):
    import trade_executor as te_module
    from trade_executor import TradeExecutor
    original = te_module._MAX_CONCURRENT_TRADES
    te_module._MAX_CONCURRENT_TRADES = max_trades

    execution = MagicMock()
    execution.execute_trade = AsyncMock(return_value={"success": True, "profit": 5.0})
    executor = TradeExecutor(execution)
    return executor, te_module, original


def _make_trade_data():
    return {
        'position': '', 'base': 'BTC', 'quote': 'USDT',
        'buy_exchange': 'binance', 'sell_exchange': 'okx',
        'buy_price': 60000.0, 'sell_price': 60200.0,
        'buy_trade_amount': 1.0, 'sell_trade_amount': 1.0,
        'executed_amount': 1.0, 'buy_value': 60000.0, 'sell_value': 60200.0,
        'buy_fee_rate': 0.001, 'sell_fee_rate': 0.001,
        'buy_fee_base': 0, 'buy_fee_quote': 60.0, 'sell_fee_quote': 60.2,
        'profit': 5.0, 'profit_percentage': 0.00083,
        'market_direction_buy': 'bull', 'market_direction_sell': 'bull',
        'market_rsi_buy': 50.0, 'market_rsi_sell': 50.0,
        'market_stoch_rsi_buy_k': 50.0, 'market_stoch_rsi_buy_d': 45.0,
        'market_stoch_rsi_sell_k': 50.0, 'market_stoch_rsi_sell_d': 45.0,
    }


# ---------------------------------------------------------------------------
# Task creation and botid attachment
# ---------------------------------------------------------------------------

class TestTaskCreation:

    @pytest.mark.asyncio
    async def test_execute_trade_creates_task_with_botid(self):
        executor, te_module, original = _make_executor()
        try:
            executor.execute_trade('bot-1', _make_trade_data())
            assert len(executor.trade_tasks) == 1
            assert executor.trade_tasks[0].botid == 'bot-1'
        finally:
            te_module._MAX_CONCURRENT_TRADES = original
            for t in executor.trade_tasks:
                t.cancel()

    @pytest.mark.asyncio
    async def test_multiple_dispatches_accumulate_tasks(self):
        executor, te_module, original = _make_executor(max_trades=5)
        try:
            for _ in range(3):
                executor.execute_trade('bot-1', _make_trade_data())
            assert len(executor.trade_tasks) == 3
        finally:
            te_module._MAX_CONCURRENT_TRADES = original
            for t in executor.trade_tasks:
                t.cancel()


# ---------------------------------------------------------------------------
# monitor_trade_tasks — result processing and P&L
# ---------------------------------------------------------------------------

class TestMonitorTradeTasks:

    @pytest.mark.asyncio
    async def test_monitor_processes_done_tasks(self):
        executor, te_module, original = _make_executor()
        try:
            executor.execute_trade('bot-1', _make_trade_data())
            # Let the task complete
            await asyncio.sleep(0.05)
            # Start monitor briefly
            monitor = asyncio.create_task(executor.monitor_trade_tasks())
            await asyncio.sleep(0.1)
            monitor.cancel()
            try:
                await monitor
            except asyncio.CancelledError:
                pass
            # Done tasks should be cleared from the list
            active = [t for t in executor.trade_tasks if not t.done()]
            assert len(active) == 0
        finally:
            te_module._MAX_CONCURRENT_TRADES = original

    @pytest.mark.asyncio
    async def test_session_pnl_accumulates(self):
        executor, te_module, original = _make_executor()
        try:
            # Dispatch two trades
            executor.execute_trade('bot-1', _make_trade_data())
            executor.execute_trade('bot-1', _make_trade_data())
            await asyncio.sleep(0.05)

            monitor = asyncio.create_task(executor.monitor_trade_tasks())
            await asyncio.sleep(0.15)
            monitor.cancel()
            try:
                await monitor
            except asyncio.CancelledError:
                pass

            assert executor._session_trades == 2
            assert abs(executor._session_profit - 10.0) < 0.01  # 2 × 5.0
        finally:
            te_module._MAX_CONCURRENT_TRADES = original

    @pytest.mark.asyncio
    async def test_search_ref_callback_called(self):
        executor, te_module, original = _make_executor()
        try:
            search_ref = MagicMock()
            search_ref.record_trade_result = AsyncMock()
            search_ref.daily_loss_accumulated = 0.0
            executor._search_ref = search_ref

            executor.execute_trade('bot-1', _make_trade_data())
            await asyncio.sleep(0.05)

            monitor = asyncio.create_task(executor.monitor_trade_tasks())
            await asyncio.sleep(0.15)
            monitor.cancel()
            try:
                await monitor
            except asyncio.CancelledError:
                pass

            search_ref.record_trade_result.assert_called_once_with(5.0)
        finally:
            te_module._MAX_CONCURRENT_TRADES = original


# ---------------------------------------------------------------------------
# shutdown — cancel monitor + await trade tasks
# ---------------------------------------------------------------------------

class TestShutdown:

    @pytest.mark.asyncio
    async def test_shutdown_cancels_monitor_task(self):
        executor, te_module, original = _make_executor()
        try:
            await executor.start()
            assert executor.monitor_task is not None
            assert not executor.monitor_task.done()

            await executor.shutdown()

            assert executor.monitor_task.done()
        finally:
            te_module._MAX_CONCURRENT_TRADES = original

    @pytest.mark.asyncio
    async def test_shutdown_awaits_in_flight_tasks(self):
        """All trade tasks must be cancelled and awaited during shutdown."""
        executor, te_module, original = _make_executor()
        try:
            # Dispatch a slow trade
            async def slow_trade(*a, **kw):
                await asyncio.sleep(9999)
                return {"success": True, "profit": 0.0}

            executor.sonarft_execution.execute_trade = slow_trade
            executor.execute_trade('bot-1', _make_trade_data())
            assert len(executor.trade_tasks) == 1

            await executor.shutdown()

            # After shutdown, trade_tasks must be empty
            assert len(executor.trade_tasks) == 0
        finally:
            te_module._MAX_CONCURRENT_TRADES = original

    @pytest.mark.asyncio
    async def test_shutdown_safe_when_no_tasks(self):
        executor, te_module, original = _make_executor()
        try:
            await executor.start()
            await executor.shutdown()  # must not raise
        finally:
            te_module._MAX_CONCURRENT_TRADES = original


# ---------------------------------------------------------------------------
# cancel_trade — cancel tasks for specific botid
# ---------------------------------------------------------------------------

class TestCancelTrade:

    @pytest.mark.asyncio
    async def test_cancel_trade_removes_matching_tasks(self):
        executor, te_module, original = _make_executor(max_trades=5)
        try:
            executor.execute_trade('bot-1', _make_trade_data())
            executor.execute_trade('bot-2', _make_trade_data())
            assert len(executor.trade_tasks) == 2

            executor.cancel_trade('bot-1')

            remaining_botids = [t.botid for t in executor.trade_tasks]
            assert 'bot-1' not in remaining_botids
            assert 'bot-2' in remaining_botids
        finally:
            te_module._MAX_CONCURRENT_TRADES = original
            for t in executor.trade_tasks:
                t.cancel()


# ---------------------------------------------------------------------------
# T06: deque race fix — task appended during monitor drain must not be lost
# ---------------------------------------------------------------------------

class TestDequeRaceFix:
    """T06: replacing list with deque eliminates the race between execute_trade
    (append) and monitor_trade_tasks (drain). A task appended while the monitor
    is processing done tasks must appear in the deque on the next iteration."""

    @pytest.mark.asyncio
    async def test_all_dispatched_tasks_are_processed(self):
        """Dispatch multiple tasks rapidly; all must be processed by the monitor.
        With the old list-rebind approach, tasks appended between the comprehension
        read and the rebind would be silently lost. With deque they cannot be."""
        executor, te_module, original = _make_executor(max_trades=10)
        try:
            # Dispatch 5 tasks in quick succession
            for _ in range(5):
                executor.execute_trade('bot-1', _make_trade_data())

            # Let all tasks complete
            await asyncio.sleep(0.1)

            monitor = asyncio.create_task(executor.monitor_trade_tasks())
            await asyncio.sleep(0.2)
            monitor.cancel()
            try:
                await monitor
            except asyncio.CancelledError:
                pass

            # All 5 tasks must have been processed — none silently dropped
            assert executor._session_trades == 5
            assert abs(executor._session_profit - 25.0) < 0.01  # 5 × 5.0
        finally:
            te_module._MAX_CONCURRENT_TRADES = original
            for t in list(executor.trade_tasks):
                t.cancel()

    @pytest.mark.asyncio
    async def test_trade_tasks_is_deque(self):
        """trade_tasks must be a deque, not a list."""
        from collections import deque
        executor, te_module, original = _make_executor()
        try:
            assert isinstance(executor.trade_tasks, deque), (
                f"trade_tasks should be deque, got {type(executor.trade_tasks)}"
            )
        finally:
            te_module._MAX_CONCURRENT_TRADES = original
