"""
Unit tests for SonarftBot parameter validation and simulation mode safety gate.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from sonarft_bot import BotCreationError, SonarftBot
from sonarft_execution import SonarftExecution
from sonarft_helpers import Trade

# ---------------------------------------------------------------------------
# _validate_parameters
# ---------------------------------------------------------------------------

class TestValidateParameters:

    def _bot_with(self, **kwargs):
        bot = SonarftBot.__new__(SonarftBot)
        bot.logger = MagicMock()
        bot.strategy                   = kwargs.get('strategy', 'market_making')
        bot.profit_percentage_threshold = kwargs.get('profit_percentage_threshold', 0.003)
        bot.trade_amount               = kwargs.get('trade_amount', 1.0)
        bot.is_simulating_trade        = kwargs.get('is_simulating_trade', 1)
        bot.max_daily_loss             = kwargs.get('max_daily_loss', 100.0)
        bot.spread_increase_factor     = kwargs.get('spread_increase_factor', 1.00072)
        bot.spread_decrease_factor     = kwargs.get('spread_decrease_factor', 0.99936)
        return bot

    def test_valid_parameters_do_not_raise(self):
        bot = self._bot_with()
        bot._validate_parameters()  # should not raise

    def test_zero_profit_threshold_raises(self):
        bot = self._bot_with(profit_percentage_threshold=0.0)
        with pytest.raises(ValueError, match="profit_percentage_threshold"):
            bot._validate_parameters()

    def test_profit_threshold_above_one_raises(self):
        bot = self._bot_with(profit_percentage_threshold=1.5)
        with pytest.raises(ValueError, match="profit_percentage_threshold"):
            bot._validate_parameters()

    def test_zero_trade_amount_raises(self):
        bot = self._bot_with(trade_amount=0.0)
        with pytest.raises(ValueError, match="trade_amount"):
            bot._validate_parameters()

    def test_negative_trade_amount_raises(self):
        bot = self._bot_with(trade_amount=-1.0)
        with pytest.raises(ValueError, match="trade_amount"):
            bot._validate_parameters()

    def test_invalid_simulation_flag_raises(self):
        bot = self._bot_with(is_simulating_trade=2)
        with pytest.raises(ValueError, match="is_simulating_trade"):
            bot._validate_parameters()

    def test_negative_max_daily_loss_raises(self):
        bot = self._bot_with(max_daily_loss=-10.0)
        with pytest.raises(ValueError, match="max_daily_loss"):
            bot._validate_parameters()

    def test_zero_max_daily_loss_is_valid(self):
        """Zero means disabled — should be allowed."""
        bot = self._bot_with(max_daily_loss=0.0)
        bot._validate_parameters()  # should not raise


# ---------------------------------------------------------------------------
# _check_live_mode_guard  (T-01)
# ---------------------------------------------------------------------------

class TestLiveModeGuard:

    def _bot_with_sim(self, is_simulating_trade: int):
        bot = SonarftBot.__new__(SonarftBot)
        bot.logger = MagicMock()
        bot.strategy                    = 'arbitrage'
        bot.profit_percentage_threshold = 0.003
        bot.trade_amount                = 1.0
        bot.is_simulating_trade         = is_simulating_trade
        bot.max_daily_loss              = 100.0
        bot.spread_increase_factor      = 1.00072
        bot.spread_decrease_factor      = 0.99936
        return bot

    def test_simulation_mode_never_raises(self):
        bot = self._bot_with_sim(1)
        bot._check_live_mode_guard()  # must not raise

    def test_live_mode_without_env_var_raises(self):
        import os
        os.environ.pop('SONARFT_ALLOW_LIVE', None)
        bot = self._bot_with_sim(0)
        with pytest.raises(BotCreationError, match='SONARFT_ALLOW_LIVE'):
            bot._check_live_mode_guard()

    def test_live_mode_with_env_var_logs_warning(self):
        import os
        os.environ['SONARFT_ALLOW_LIVE'] = 'true'
        try:
            bot = self._bot_with_sim(0)
            bot._check_live_mode_guard()  # must not raise
            bot.logger.warning.assert_called_once()
            assert 'LIVE TRADING' in bot.logger.warning.call_args[0][0]
        finally:
            os.environ.pop('SONARFT_ALLOW_LIVE', None)


# ---------------------------------------------------------------------------
# _validate_parameters (continued)
# ---------------------------------------------------------------------------

class TestValidateParametersSpread:

    def _bot_with(self, **kwargs):
        bot = SonarftBot.__new__(SonarftBot)
        bot.logger = MagicMock()
        bot.strategy                    = kwargs.get('strategy', 'market_making')
        bot.profit_percentage_threshold = kwargs.get('profit_percentage_threshold', 0.003)
        bot.trade_amount                = kwargs.get('trade_amount', 1.0)
        bot.is_simulating_trade         = kwargs.get('is_simulating_trade', 1)
        bot.max_daily_loss              = kwargs.get('max_daily_loss', 100.0)
        bot.spread_increase_factor      = kwargs.get('spread_increase_factor', 1.00072)
        bot.spread_decrease_factor      = kwargs.get('spread_decrease_factor', 0.99936)
        return bot

    def test_spread_increase_factor_out_of_range_raises(self):
        bot = self._bot_with(spread_increase_factor=1.02)
        with pytest.raises(ValueError, match="spread_increase_factor"):
            bot._validate_parameters()

    def test_spread_decrease_factor_out_of_range_raises(self):
        bot = self._bot_with(spread_decrease_factor=0.98)
        with pytest.raises(ValueError, match="spread_decrease_factor"):
            bot._validate_parameters()


# ---------------------------------------------------------------------------
# Simulation mode gate
# ---------------------------------------------------------------------------

class TestSimulationModeGate:

    def _make_execution(self, is_simulation):
        api = MagicMock()
        api.create_order = AsyncMock(return_value={'id': 'real_order_001'})
        api.get_balance = AsyncMock(return_value={'free': {'BTC': 10.0, 'USDT': 1_000_000.0}})
        api.watch_orders = AsyncMock(return_value=[])
        api.get_last_price = AsyncMock(return_value=60000.0)
        helpers = MagicMock()
        helpers.save_order_history = MagicMock()
        helpers.save_trade_history = MagicMock()
        helpers.open_position = AsyncMock()
        helpers.close_position = AsyncMock()
        indicators = MagicMock()
        indicators.get_market_direction = AsyncMock(return_value='bull')
        indicators.get_rsi = AsyncMock(return_value=50.0)
        indicators.get_stoch_rsi = AsyncMock(return_value=(50.0, 50.0))
        return SonarftExecution(api, helpers, is_simulation_mode=is_simulation)

    def _make_trade(self, **kwargs):
        defaults = dict(
            position='', base='BTC', quote='USDT',
            buy_exchange='binance', sell_exchange='okx',
            buy_price=60000.0, sell_price=60200.0,
            buy_trade_amount=1.0, sell_trade_amount=1.0,
            executed_amount=1.0, buy_value=60000.0, sell_value=60200.0,
            buy_fee_rate=0.001, sell_fee_rate=0.001,
            buy_fee_base=0.0, buy_fee_quote=60.0, sell_fee_quote=60.2,
            profit=79.8, profit_percentage=0.00133,
            market_direction_buy='bull', market_direction_sell='bull',
            market_rsi_buy=50.0, market_rsi_sell=50.0,
            market_stoch_rsi_buy_k=50.0, market_stoch_rsi_buy_d=45.0,
            market_stoch_rsi_sell_k=50.0, market_stoch_rsi_sell_d=45.0,
        )
        defaults.update(kwargs)
        return Trade(**defaults)

    @pytest.mark.asyncio
    async def test_simulation_mode_never_calls_create_order(self):
        execution = self._make_execution(is_simulation=True)
        trade = self._make_trade()
        await execution._execute_single_trade(botid=1, trade=trade)
        execution.api_manager.create_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_simulation_mode_returns_synthetic_order_id(self):
        execution = self._make_execution(is_simulation=True)
        result = await execution.execute_order(
            'binance', 'BTC', 'USDT', 'buy', 1.0, 60000.0, monitor_order=False
        )
        order_id, executed, remaining = result
        assert 'buy_' in order_id
        assert executed == 1.0
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_simulation_mode_balance_check_always_passes(self):
        execution = self._make_execution(is_simulation=True)
        result = await execution.check_balance('binance', 'BTC', 'USDT', 'buy', 1.0, 60000.0)
        assert result is True
        execution.api_manager.get_balance.assert_not_called()

    @pytest.mark.asyncio
    async def test_live_mode_calls_create_order(self):
        execution = self._make_execution(is_simulation=False)
        # Patch monitor_price to return immediately
        execution.api_manager.get_last_price = AsyncMock(return_value=59999.0)
        await execution.execute_order(
            'binance', 'BTC', 'USDT', 'buy', 1.0, 60000.0, monitor_order=False
        )
        execution.api_manager.create_order.assert_called_once()


# ---------------------------------------------------------------------------
# SonarftSearch — daily loss limit
# ---------------------------------------------------------------------------

class TestDailyLossLimit:

    def _make_search(self, max_daily_loss=100.0, max_daily_trades=0):
        import time as _time

        from sonarft_search import SonarftSearch
        search = SonarftSearch.__new__(SonarftSearch)
        search.logger = MagicMock()
        search.max_daily_loss = max_daily_loss
        search.max_daily_trades = max_daily_trades
        search._daily_trades_count = 0
        search.daily_loss_accumulated = 0.0
        search._loss_reset_date = _time.strftime('%Y-%m-%d', _time.localtime())
        search._halt_alerted = False
        search._alert_callback = None
        search._botid = "test-bot-uuid"
        return search

    @pytest.mark.asyncio
    async def test_not_halted_initially(self):
        search = self._make_search(max_daily_loss=100.0)
        assert await search.is_halted() is False

    @pytest.mark.asyncio
    async def test_halted_after_loss_exceeds_limit(self):
        search = self._make_search(max_daily_loss=100.0)
        await search.record_trade_result(-150.0)
        assert await search.is_halted() is True

    @pytest.mark.asyncio
    async def test_not_halted_when_limit_is_zero(self):
        """Zero means disabled."""
        search = self._make_search(max_daily_loss=0.0)
        await search.record_trade_result(-999999.0)
        assert await search.is_halted() is False

    @pytest.mark.asyncio
    async def test_positive_profit_does_not_accumulate_loss(self):
        search = self._make_search(max_daily_loss=100.0)
        await search.record_trade_result(50.0)
        assert search.daily_loss_accumulated == 0.0
        assert await search.is_halted() is False

    @pytest.mark.asyncio
    async def test_accumulates_multiple_losses(self):
        search = self._make_search(max_daily_loss=100.0)
        await search.record_trade_result(-40.0)
        await search.record_trade_result(-40.0)
        assert search.daily_loss_accumulated == 80.0
        assert await search.is_halted() is False
        await search.record_trade_result(-30.0)
        assert await search.is_halted() is True

    # T10: alert sent on halt

    @pytest.mark.asyncio
    async def test_halt_sends_alert_once_on_loss_limit(self):
        """T10: alert callback must be called exactly once when loss limit is hit."""
        search = self._make_search(max_daily_loss=100.0)
        alert_messages = []
        async def capture_alert(msg):
            alert_messages.append(msg)
        search._alert_callback = capture_alert

        await search.record_trade_result(-150.0)
        # First call — should send alert
        assert await search.is_halted() is True
        assert len(alert_messages) == 1
        assert "daily loss limit" in alert_messages[0].lower()

        # Second call — must NOT send another alert
        assert await search.is_halted() is True
        assert len(alert_messages) == 1  # still only one

    @pytest.mark.asyncio
    async def test_halt_sends_alert_once_on_trade_limit(self):
        """T10: alert callback must be called exactly once when trade limit is hit."""
        search = self._make_search(max_daily_loss=0.0, max_daily_trades=2)
        alert_messages = []
        async def capture_alert(msg):
            alert_messages.append(msg)
        search._alert_callback = capture_alert

        search._daily_trades_count = 2  # at limit
        assert await search.is_halted() is True
        assert len(alert_messages) == 1
        assert "daily trade limit" in alert_messages[0].lower()

        # Second call — no duplicate alert
        assert await search.is_halted() is True
        assert len(alert_messages) == 1

    @pytest.mark.asyncio
    async def test_no_alert_when_callback_not_set(self):
        """T10: is_halted must not raise when _alert_callback is None."""
        search = self._make_search(max_daily_loss=100.0)
        search._alert_callback = None
        await search.record_trade_result(-150.0)
        # Must not raise
        assert await search.is_halted() is True

    @pytest.mark.asyncio
    async def test_halt_alert_reset_on_daily_rollover(self):
        """T10: _halt_alerted is cleared on daily reset so next day sends a fresh alert."""
        import time as _t
        search = self._make_search(max_daily_loss=100.0)
        search._halt_alerted = True  # simulate already alerted today

        # Simulate date rollover
        search._loss_reset_date = "2000-01-01"  # yesterday
        await search._check_daily_reset()

        assert search._halt_alerted is False  # reset by daily rollover


# ---------------------------------------------------------------------------
# T-10: Pydantic config schema validation
# ---------------------------------------------------------------------------

class TestParametersConfig:
    """Tests for the ParametersConfig Pydantic model."""

    def _valid(self, **overrides):
        from config_schemas import ParametersConfig
        defaults = dict(
            strategy="arbitrage",
            profit_percentage_threshold=0.001,
            trade_amount=1.0,
            is_simulating_trade=1,
        )
        defaults.update(overrides)
        return ParametersConfig(**defaults)

    def test_valid_arbitrage_config_accepted(self):
        cfg = self._valid()
        assert cfg.strategy == "arbitrage"
        assert cfg.is_simulating_trade == 1

    def test_invalid_strategy_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="strategy"):
            self._valid(strategy="scalping")

    def test_zero_profit_threshold_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="profit_percentage_threshold"):
            self._valid(profit_percentage_threshold=0.0)

    def test_negative_trade_amount_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="trade_amount"):
            self._valid(trade_amount=-1.0)

    def test_invalid_simulation_flag_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self._valid(is_simulating_trade=2)

    def test_negative_max_daily_loss_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="max_daily_loss"):
            self._valid(max_daily_loss=-10.0)

    def test_market_making_spread_factor_out_of_range_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="spread_increase_factor"):
            self._valid(
                strategy="market_making",
                spread_increase_factor=1.02,
                spread_decrease_factor=0.999,
            )

    def test_market_making_valid_spread_factors_accepted(self):
        cfg = self._valid(
            strategy="market_making",
            spread_increase_factor=1.00072,
            spread_decrease_factor=0.99936,
        )
        assert cfg.strategy == "market_making"

    def test_defaults_applied_for_optional_fields(self):
        cfg = self._valid()
        assert cfg.max_daily_loss == 0.0
        assert cfg.max_trade_amount == 0.0
        assert cfg.max_orders_per_minute == 0


class TestSymbolConfig:

    def test_valid_symbol_accepted(self):
        from config_schemas import SymbolConfig
        s = SymbolConfig(base="BTC", quotes=["USDT"])
        assert s.base == "BTC"
        assert s.quotes == ["USDT"]

    def test_empty_quotes_raises(self):
        from config_schemas import SymbolConfig
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SymbolConfig(base="BTC", quotes=[])

    def test_empty_quote_string_raises(self):
        from config_schemas import SymbolConfig
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="empty string"):
            SymbolConfig(base="BTC", quotes=[""])


class TestFeeConfig:

    def test_valid_fee_accepted(self):
        from config_schemas import FeeConfig
        f = FeeConfig(exchange="binance", buy_fee=0.001, sell_fee=0.001)
        assert f.exchange == "binance"

    def test_negative_fee_raises(self):
        from config_schemas import FeeConfig
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="buy_fee"):
            FeeConfig(exchange="binance", buy_fee=-0.001, sell_fee=0.001)

    def test_zero_buy_and_sell_fee_raises(self):
        """T04: both fees zero must be rejected — live trading trap."""
        from config_schemas import FeeConfig
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="Zero fees"):
            FeeConfig(exchange="binance", buy_fee=0.0, sell_fee=0.0)

    def test_zero_buy_fee_only_is_accepted(self):
        """A zero buy_fee with non-zero sell_fee is valid (e.g. maker rebate)."""
        from config_schemas import FeeConfig
        f = FeeConfig(exchange="binance", buy_fee=0.0, sell_fee=0.001)
        assert f.buy_fee == 0.0

    def test_zero_sell_fee_only_is_accepted(self):
        """A zero sell_fee with non-zero buy_fee is valid."""
        from config_schemas import FeeConfig
        f = FeeConfig(exchange="binance", buy_fee=0.001, sell_fee=0.0)
        assert f.sell_fee == 0.0

    def test_maker_fees_optional(self):
        """maker_buy_fee and maker_sell_fee are optional."""
        from config_schemas import FeeConfig
        f = FeeConfig(exchange="okx", buy_fee=0.001, sell_fee=0.001,
                      maker_buy_fee=0.0008, maker_sell_fee=0.0008)
        assert f.maker_buy_fee == 0.0008


# ---------------------------------------------------------------------------
# T-25: Circuit breaker in run_bot()
# ---------------------------------------------------------------------------

class TestCircuitBreaker:

    @pytest.mark.asyncio
    async def test_circuit_breaker_trips_after_max_failures(self):
        """After SONARFT_MAX_FAILURES consecutive search failures, _stop_event is set."""
        import os
        os.environ['SONARFT_MAX_FAILURES'] = '3'
        os.environ['SONARFT_BACKOFF_BASE'] = '0'
        try:
            bot = SonarftBot.__new__(SonarftBot)
            bot.logger = MagicMock()
            bot.botid = 'test-bot'
            bot._stop_event = asyncio.Event()
            bot._send_alert = AsyncMock()

            call_count = 0

            async def failing_search(_botid):
                nonlocal call_count
                call_count += 1
                raise RuntimeError("simulated exchange failure")

            mock_search = MagicMock()
            mock_search.search_trades = failing_search
            bot.sonarft_search = mock_search

            await bot.run_bot()

            assert bot._stop_event.is_set()
            assert call_count == 3  # exactly max_failures calls
            bot._send_alert.assert_called_once()
        finally:
            os.environ.pop('SONARFT_MAX_FAILURES', None)
            os.environ.pop('SONARFT_BACKOFF_BASE', None)

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(self):
        """A successful cycle resets the consecutive failure counter."""
        import os
        os.environ['SONARFT_MAX_FAILURES'] = '3'
        os.environ['SONARFT_BACKOFF_BASE'] = '0'
        os.environ['SONARFT_CYCLE_SLEEP_MIN'] = '0'
        os.environ['SONARFT_CYCLE_SLEEP_MAX'] = '0'
        try:
            bot = SonarftBot.__new__(SonarftBot)
            bot.logger = MagicMock()
            bot.botid = 'test-bot'
            bot._stop_event = asyncio.Event()
            bot._send_alert = AsyncMock()

            call_count = 0

            async def mixed_search(_botid):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise RuntimeError("failure")
                # Second call succeeds, then we stop
                bot._stop_event.set()

            mock_search = MagicMock()
            mock_search.search_trades = mixed_search
            bot.sonarft_search = mock_search

            await bot.run_bot()

            # Circuit breaker should NOT have tripped (only 1 failure before success)
            bot._send_alert.assert_not_called()
        finally:
            for k in ('SONARFT_MAX_FAILURES', 'SONARFT_BACKOFF_BASE',
                      'SONARFT_CYCLE_SLEEP_MIN', 'SONARFT_CYCLE_SLEEP_MAX'):
                os.environ.pop(k, None)


# ---------------------------------------------------------------------------
# T-25: sanitize_client_id() path traversal prevention
# ---------------------------------------------------------------------------

class TestSanitizeClientId:

    def test_normal_id_unchanged(self):
        from sonarft_helpers import sanitize_client_id
        assert sanitize_client_id("client-123") == "client-123"

    def test_alphanumeric_unchanged(self):
        from sonarft_helpers import sanitize_client_id
        assert sanitize_client_id("ClientABC") == "ClientABC"

    def test_underscores_and_hyphens_kept(self):
        from sonarft_helpers import sanitize_client_id
        assert sanitize_client_id("client_id-001") == "client_id-001"

    def test_spaces_stripped(self):
        from sonarft_helpers import sanitize_client_id
        assert sanitize_client_id("client id") == "clientid"

    def test_special_chars_stripped(self):
        from sonarft_helpers import sanitize_client_id
        assert sanitize_client_id("client!@#$%") == "client"

    def test_path_traversal_stripped(self):
        from sonarft_helpers import sanitize_client_id
        result = sanitize_client_id("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_null_bytes_stripped(self):
        from sonarft_helpers import sanitize_client_id
        result = sanitize_client_id("client\x00id")
        assert "\x00" not in result

    def test_empty_after_sanitize_raises(self):
        from sonarft_helpers import sanitize_client_id
        with pytest.raises(ValueError, match="Invalid client_id"):
            sanitize_client_id("!!!")

    def test_empty_string_raises(self):
        from sonarft_helpers import sanitize_client_id
        with pytest.raises(ValueError):
            sanitize_client_id("")


# ---------------------------------------------------------------------------
# T09: periodic tasks survive unexpected exceptions
# ---------------------------------------------------------------------------

class TestPeriodicTaskResilience:
    """T09: _periodic_fee_refresh and _periodic_db_backup must continue running
    after an unexpected exception in the loop body, not silently die."""

    def _make_bot(self):
        """Build a minimal SonarftBot with mocked dependencies."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock
        from sonarft_bot import SonarftBot
        bot = SonarftBot.__new__(SonarftBot)
        bot.logger = MagicMock()
        bot._stop_event = asyncio.Event()
        bot.api_manager = MagicMock()
        bot.sonarft_helpers = MagicMock()
        bot.sonarft_helpers.async_backup_db = AsyncMock()
        return bot

    @pytest.mark.asyncio
    async def test_fee_refresh_continues_after_exception(self):
        """An exception in refresh_fees must be logged and the task must
        continue running — not die silently."""
        import asyncio
        import os
        bot = self._make_bot()

        call_count = {"n": 0}

        async def failing_then_ok():
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("network error")
            # Second call succeeds — stop the loop
            bot._stop_event.set()

        bot.api_manager.refresh_fees = failing_then_ok

        # Use a very short interval so the test completes quickly
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("SONARFT_FEE_REFRESH_INTERVAL", "0")
            task = asyncio.create_task(bot._periodic_fee_refresh())
            await asyncio.wait_for(task, timeout=2.0)

        # Task completed normally (not killed by the exception)
        assert task.done()
        assert not task.cancelled()
        # Exception was logged
        bot.logger.exception.assert_called_once()
        # refresh_fees was called twice (first failed, second succeeded)
        assert call_count["n"] == 2

    @pytest.mark.asyncio
    async def test_db_backup_continues_after_exception(self):
        """An exception in async_backup_db must be logged and the task must
        continue running — not die silently."""
        import asyncio
        from unittest.mock import patch
        bot = self._make_bot()

        call_count = {"n": 0}

        async def failing_then_ok(path):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise OSError("disk full")
            bot._stop_event.set()

        bot.sonarft_helpers.async_backup_db = failing_then_ok

        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("SONARFT_BACKUP_INTERVAL", "1")  # non-zero so task runs
            mp.setenv("SONARFT_BACKUP_DIR", "/tmp/sonarft_test_backups")
            # Patch os.makedirs so no real filesystem access is needed
            with patch("sonarft_bot.os.makedirs"):
                task = asyncio.create_task(bot._periodic_db_backup())
                await asyncio.wait_for(task, timeout=3.0)

        assert task.done()
        assert not task.cancelled()
        bot.logger.exception.assert_called_once()
        assert call_count["n"] == 2


# ---------------------------------------------------------------------------
# T24: exchange name and indicator name validation at config load
# ---------------------------------------------------------------------------

class TestConfigValidation:
    """T24: unknown exchange names and indicator names must raise BotCreationError
    at load_configurations time with a clear message."""

    def _make_bot(self):
        from sonarft_bot import SonarftBot
        from unittest.mock import MagicMock
        bot = SonarftBot.__new__(SonarftBot)
        bot.logger = MagicMock()
        return bot

    def _patch_load(self, bot, config_data: dict):
        """Patch bot_config._load_config_section to return controlled data."""
        from unittest.mock import patch

        def fake_load(pathname, key):
            return config_data[key]

        return patch("bot_config._load_config_section", side_effect=fake_load)

    def _base_config(self):
        """Minimal valid config data for load_configurations."""
        return {
            "config_1": [{"markets_pathname": "x", "markets_setup": 1,
                           "exchanges_pathname": "x", "exchanges_setup": 1,
                           "symbols_pathname": "x", "symbols_setup": 1,
                           "indicators_pathname": "x", "indicators_setup": 1,
                           "parameters_pathname": "x", "parameters_setup": 1,
                           "fees_pathname": "x", "fees_setup": 1}],
            "market_1": ["crypto"],
            "parameters_1": [{"strategy": "arbitrage",
                               "profit_percentage_threshold": 0.001,
                               "trade_amount": 0.01,
                               "is_simulating_trade": 1}],
            "symbols_1": [{"base": "BTC", "quotes": ["USDT"]}],
            "exchanges_fees_1": [{"exchange": "binance", "buy_fee": 0.001, "sell_fee": 0.001}],
            "indicators_1": ["rsi", "stoch rsi"],
        }

    def test_unknown_exchange_raises_bot_creation_error(self):
        """A typo in exchange name must raise BotCreationError at config load."""
        from sonarft_bot import BotCreationError
        bot = self._make_bot()
        data = self._base_config()
        data["exchanges_1"] = ["binnance"]  # typo

        with self._patch_load(bot, data):
            with pytest.raises(BotCreationError, match="Unknown exchange"):
                bot.load_configurations("config_1")

    def test_valid_exchange_accepted(self):
        """A valid ccxt exchange name must not raise."""
        from sonarft_bot import BotCreationError
        from unittest.mock import patch, MagicMock
        bot = self._make_bot()
        data = self._base_config()
        data["exchanges_1"] = ["binance"]

        with self._patch_load(bot, data):
            # Patch _check_live_mode_guard to avoid env var check
            with patch.object(bot, "_check_live_mode_guard"):
                # Should not raise
                try:
                    bot.load_configurations("config_1")
                except BotCreationError as e:
                    # Only fail if it's an exchange validation error
                    assert "Unknown exchange" not in str(e)

    def test_unknown_indicator_raises_bot_creation_error(self):
        """An unrecognised indicator name must raise BotCreationError."""
        from sonarft_bot import BotCreationError
        from unittest.mock import patch
        bot = self._make_bot()
        data = self._base_config()
        data["exchanges_1"] = ["binance"]
        data["indicators_1"] = ["rsi", "unknown_indicator_xyz"]

        with self._patch_load(bot, data):
            with patch.object(bot, "_check_live_mode_guard"):
                with pytest.raises(BotCreationError, match="Unknown indicator"):
                    bot.load_configurations("config_1")

    def test_valid_indicators_accepted(self):
        """All known indicator names must be accepted without error."""
        from sonarft_bot import BotCreationError
        from unittest.mock import patch
        bot = self._make_bot()
        data = self._base_config()
        data["exchanges_1"] = ["binance"]
        data["indicators_1"] = ["rsi", "stoch rsi", "macd", "sma", "ema"]

        with self._patch_load(bot, data):
            with patch.object(bot, "_check_live_mode_guard"):
                try:
                    bot.load_configurations("config_1")
                except BotCreationError as e:
                    assert "Unknown indicator" not in str(e)

    def test_empty_indicators_list_accepted(self):
        """An empty indicators list disables all indicator gates — must not raise."""
        from sonarft_bot import BotCreationError
        from unittest.mock import patch
        bot = self._make_bot()
        data = self._base_config()
        data["exchanges_1"] = ["binance"]
        data["indicators_1"] = []

        with self._patch_load(bot, data):
            with patch.object(bot, "_check_live_mode_guard"):
                try:
                    bot.load_configurations("config_1")
                except BotCreationError as e:
                    assert "Unknown indicator" not in str(e)


# ---------------------------------------------------------------------------
# T36: _ALLOWED_TABLES includes 'positions'
# ---------------------------------------------------------------------------

class TestAllowedTables:
    """T36: _ALLOWED_TABLES must include 'positions' so the whitelist is complete."""

    def test_positions_in_allowed_tables(self):
        from sonarft_helpers import _ALLOWED_TABLES
        assert "positions" in _ALLOWED_TABLES

    def test_all_expected_tables_present(self):
        from sonarft_helpers import _ALLOWED_TABLES
        expected = {"orders", "trades", "daily_loss", "positions"}
        assert expected.issubset(_ALLOWED_TABLES)


# ---------------------------------------------------------------------------
# T37: _validate_env_vars raises BotCreationError on invalid values
# ---------------------------------------------------------------------------

class TestValidateEnvVars:
    """T37: all SONARFT_* env vars must be validated at create_bot time."""

    def _make_bot(self):
        from sonarft_bot import SonarftBot
        from unittest.mock import MagicMock
        bot = SonarftBot.__new__(SonarftBot)
        bot.logger = MagicMock()
        return bot

    def test_valid_defaults_do_not_raise(self):
        """Default env var values must all pass validation."""
        from sonarft_bot import BotCreationError
        bot = self._make_bot()
        # Should not raise with no env vars set (all defaults are valid)
        with pytest.MonkeyPatch().context() as mp:
            for var in ["SONARFT_MAX_FAILURES", "SONARFT_BACKOFF_BASE",
                        "SONARFT_CYCLE_SLEEP_MIN", "SONARFT_CYCLE_SLEEP_MAX",
                        "SONARFT_MAX_CONCURRENT_TRADES", "SONARFT_FEE_REFRESH_INTERVAL",
                        "SONARFT_BACKUP_INTERVAL", "SONARFT_FEE_ROUNDING"]:
                mp.delenv(var, raising=False)
            bot._validate_env_vars()  # must not raise

    def test_non_integer_max_failures_raises(self):
        """Non-integer SONARFT_MAX_FAILURES must raise BotCreationError."""
        from sonarft_bot import BotCreationError
        bot = self._make_bot()
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("SONARFT_MAX_FAILURES", "abc")
            with pytest.raises(BotCreationError, match="SONARFT_MAX_FAILURES"):
                bot._validate_env_vars()

    def test_out_of_range_cycle_sleep_raises(self):
        """SONARFT_CYCLE_SLEEP_MIN=0 is below the minimum of 1."""
        from sonarft_bot import BotCreationError
        bot = self._make_bot()
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("SONARFT_CYCLE_SLEEP_MIN", "0")
            with pytest.raises(BotCreationError, match="SONARFT_CYCLE_SLEEP_MIN"):
                bot._validate_env_vars()

    def test_invalid_fee_rounding_raises(self):
        """Unknown SONARFT_FEE_ROUNDING value must raise BotCreationError."""
        from sonarft_bot import BotCreationError
        bot = self._make_bot()
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("SONARFT_FEE_ROUNDING", "ROUND_DOWN")
            with pytest.raises(BotCreationError, match="SONARFT_FEE_ROUNDING"):
                bot._validate_env_vars()

    def test_valid_fee_rounding_half_up_accepted(self):
        """SONARFT_FEE_ROUNDING=HALF_UP must be accepted."""
        bot = self._make_bot()
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("SONARFT_FEE_ROUNDING", "HALF_UP")
            bot._validate_env_vars()  # must not raise


# ---------------------------------------------------------------------------
# T30: BotConfig dataclass and load_bot_config are independently testable
# ---------------------------------------------------------------------------

class TestBotConfig:
    """T30: BotConfig is a plain dataclass that can be constructed and
    inspected without instantiating a full SonarftBot."""

    def test_botconfig_is_a_dataclass(self):
        """BotConfig must be a plain dataclass with no async dependencies."""
        from bot_config import BotConfig
        import dataclasses
        assert dataclasses.is_dataclass(BotConfig)

    def test_botconfig_can_be_constructed_directly(self):
        """BotConfig must be constructable with explicit field values."""
        from bot_config import BotConfig
        cfg = BotConfig(
            market=["crypto"],
            strategy="arbitrage",
            profit_percentage_threshold=0.001,
            trade_amount=0.01,
            is_simulating_trade=1,
            max_daily_loss=100.0,
            max_trade_amount=0.1,
            max_orders_per_minute=10,
            spread_increase_factor=1.0002,
            spread_decrease_factor=0.9998,
            slippage_buffer=0.0002,
            flash_crash_threshold=0.02,
            max_daily_trades=0,
            max_total_exposure=0.0,
            symbols=[{"base": "BTC", "quotes": ["USDT"]}],
            exchanges=["binance"],
            exchanges_fees=[{"exchange": "binance", "buy_fee": 0.001, "sell_fee": 0.001}],
            active_indicators=["rsi", "stoch rsi"],
        )
        assert cfg.strategy == "arbitrage"
        assert cfg.trade_amount == 0.01
        assert cfg.exchanges == ["binance"]

    def test_load_bot_config_raises_on_missing_file(self):
        """load_bot_config must raise BotCreationError when config.json is absent."""
        from bot_config import BotCreationError, load_bot_config
        from unittest.mock import patch
        with patch("bot_config._load_config_section", side_effect=BotCreationError("not found")):
            with pytest.raises(BotCreationError):
                load_bot_config("config_1")

    def test_load_bot_config_raises_on_zero_fees(self):
        """load_bot_config must raise BotCreationError when fees are all zero."""
        from bot_config import BotCreationError, load_bot_config
        from unittest.mock import patch

        config_data = {
            "config_1": [{"markets_pathname": "x", "markets_setup": 1,
                           "exchanges_pathname": "x", "exchanges_setup": 1,
                           "symbols_pathname": "x", "symbols_setup": 1,
                           "indicators_pathname": "x", "indicators_setup": 1,
                           "parameters_pathname": "x", "parameters_setup": 1,
                           "fees_pathname": "x", "fees_setup": 1}],
            "market_1": ["crypto"],
            "parameters_1": [{"strategy": "arbitrage",
                               "profit_percentage_threshold": 0.001,
                               "trade_amount": 0.01,
                               "is_simulating_trade": 1}],
            "symbols_1": [{"base": "BTC", "quotes": ["USDT"]}],
            "exchanges_1": ["binance"],
            "exchanges_fees_1": [{"exchange": "binance", "buy_fee": 0.0, "sell_fee": 0.0}],
            "indicators_1": ["rsi"],
        }

        def fake_load(pathname, key):
            return config_data[key]

        with patch("bot_config._load_config_section", side_effect=fake_load):
            with pytest.raises(BotCreationError, match="Zero fees"):
                load_bot_config("config_1")
