"""
Sonarft Bot Control
"""

import asyncio
import json
import logging
import os
import random

# Resolve the bot package directory so config paths work regardless of CWD
_BOT_DIR = os.path.dirname(os.path.abspath(__file__))


def _bot_path(*parts: str) -> str:
    """Return an absolute path anchored to the bot package directory."""
    return os.path.join(_BOT_DIR, *parts)


from config_schemas import FeeConfig, ParametersConfig, SymbolConfig  # noqa: E402
from sonarft_api_manager import SonarftApiManager  # noqa: E402
from sonarft_execution import SonarftExecution  # noqa: E402
from sonarft_helpers import SonarftHelpers  # noqa: E402
from sonarft_indicators import SonarftIndicators  # noqa: E402
from sonarft_math import SonarftMath  # noqa: E402
from sonarft_prices import SonarftPrices  # noqa: E402
from sonarft_search import SonarftSearch  # noqa: E402
from sonarft_validators import SonarftValidators  # noqa: E402


# ### SonarftBot Class - ##########################################
class SonarftBot:
    """ """

    def __init__(self, library: str, logger: logging.Logger = None):
        """
        Initializes the SonarftBot with a unique bot id and a logger.

        Parameters:
        library (str): The name of the library to use for trading.
        logger (logging.Logger): An optional logger object to log messages.
        """

        self.logger = logger or logging.getLogger(__name__)
        self.library = library
        self.api_manager = None
        self.stop_bot_flag = False  # kept for BotManager.run_bot reset
        self._stop_event = asyncio.Event()
        self.botid = 0

    async def create_bot(self, config_setup: str):
        """
        Creates a new bot, loads the configurations, and initializes the API manager and all bot modules.
        Does not start the run loop — call run_bot() separately after creation.

        Parameters:
        config_setup (str): The name of the configuration setup to load.
        """

        try:
            self.stop_bot_flag = False

            self.botid = self.create_botid()
            os.makedirs(_bot_path("sonarftdata", "bots"), exist_ok=True)
            botid_path = _bot_path("sonarftdata", "bots", f"{self.botid}.json")
            await asyncio.to_thread(lambda: self._write_botid_file(botid_path))

            self.load_configurations(config_setup)

            self.logger.info("Initializing API Manager module...")
            self.api_manager = SonarftApiManager(
                self.library, self.exchanges, self.exchanges_fees, self.logger
            )

            self.logger.info("Initializing API Manager module OK")

            self._load_api_keys()

            self.logger.info("Initializing Bot modules...")
            await self.initialize_modules()

            self.logger.info("Loading markets...")
            await self.api_manager.load_all_markets()
            self._validate_precision_rules()

            # Refresh fee rates from exchange API (replaces stale config values)
            await self.api_manager.refresh_fees()
            # Schedule periodic fee refresh every 24 hours
            self._fee_refresh_task = asyncio.create_task(self._periodic_fee_refresh())
            # Schedule periodic SQLite backup every 24 hours
            self._db_backup_task = asyncio.create_task(self._periodic_db_backup())

            # Reconcile: cancel any stale open orders from previous runs
            if not self.is_simulating_trade:
                await self._reconcile_open_orders()
                await self._reconcile_open_positions()

            self.logger.info("Bot %s has been created!", self.botid)
        except BotCreationError as error:
            self.logger.error("Bot creation error: %s", error)
            return

        return self.botid

    async def run_bot(self):
        self.logger.info(f"Bot {self.botid} start running")
        consecutive_failures = 0
        max_failures = int(os.environ.get("SONARFT_MAX_FAILURES", "5"))
        base_backoff = int(os.environ.get("SONARFT_BACKOFF_BASE", "30"))
        try:
            while not self._stop_event.is_set():
                try:
                    await self.sonarft_search.search_trades(self.botid)
                    consecutive_failures = 0
                except Exception as e:
                    consecutive_failures += 1
                    backoff = base_backoff * consecutive_failures
                    self.logger.error(
                        f"Bot {self.botid}: search error ({consecutive_failures}/{max_failures}): {e}. "
                        f"Backing off {backoff}s."
                    )
                    if consecutive_failures >= max_failures:
                        self.logger.error(
                            f"Bot {self.botid}: circuit breaker tripped after {max_failures} consecutive failures. Stopping."
                        )
                        await self._send_alert(
                            f"SonarFT Bot {self.botid}: circuit breaker tripped after "
                            f"{max_failures} consecutive failures. Last error: {e}"
                        )
                        self._stop_event.set()
                        break
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(self._stop_event.wait()), timeout=backoff
                        )
                    except asyncio.TimeoutError:
                        pass
                    continue

                if self._stop_event.is_set():
                    break

                timesleep_size = random.randint(
                    int(os.environ.get("SONARFT_CYCLE_SLEEP_MIN", "6")),
                    int(os.environ.get("SONARFT_CYCLE_SLEEP_MAX", "18")),
                )
                self.logger.info(
                    f"Next trade for bot {self.botid} in {timesleep_size} secs..."
                )
                try:
                    await asyncio.wait_for(
                        asyncio.shield(self._stop_event.wait()), timeout=timesleep_size
                    )
                except asyncio.TimeoutError:
                    pass
        except Exception:
            self.logger.exception("Fatal error in run_bot")
            await self._send_alert(
                f"SonarFT Bot {self.botid}: fatal error in run_bot"
            )

    async def _send_alert(self, message: str) -> None:
        """
        Send an alert notification.
        Reads SONARFT_ALERT_WEBHOOK from environment — if set, POSTs the message
        as JSON to that URL (e.g. a Slack/Discord/Teams incoming webhook).
        Falls back to a logger.error if no webhook is configured.
        """
        webhook_url = os.environ.get("SONARFT_ALERT_WEBHOOK")
        if not webhook_url:
            self.logger.error(f"ALERT (no webhook configured): {message}")
            return
        try:
            import urllib.request

            payload = json.dumps({"text": message}).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            await asyncio.to_thread(urllib.request.urlopen, req)
            self.logger.info(f"Alert sent to webhook: {message}")
        except Exception as e:
            self.logger.error(
                f"Failed to send alert: {e} | Original message: {message}"
            )

    def apply_parameters(self, parameters: dict) -> None:
        """
        Hot-reload trading parameters into the running bot.
        Only numeric/flag parameters are updated; exchange/symbol config is unchanged.
        Saves old values before applying so they can be restored if validation fails.
        """
        # Save old values before applying — restored in the except block if validation fails
        old_values = {}
        if "profit_percentage_threshold" in parameters:
            old_values["profit_percentage_threshold"] = self.profit_percentage_threshold
            self.profit_percentage_threshold = float(
                parameters["profit_percentage_threshold"]
            )
        if "trade_amount" in parameters:
            old_values["trade_amount"] = self.trade_amount
            self.trade_amount = float(parameters["trade_amount"])
        if "is_simulating_trade" in parameters:
            new_sim = int(parameters["is_simulating_trade"])
            if self.is_simulating_trade == 1 and new_sim == 0:
                if not os.environ.get("SONARFT_ALLOW_LIVE"):
                    raise ValueError(
                        "Switching from simulation to live mode requires "
                        "SONARFT_ALLOW_LIVE=true environment variable"
                    )
            old_values["is_simulating_trade"] = self.is_simulating_trade
            self.is_simulating_trade = new_sim
        if "max_daily_loss" in parameters:
            old_values["max_daily_loss"] = self.max_daily_loss
            self.max_daily_loss = float(parameters.get("max_daily_loss", 0.0))
        if "spread_increase_factor" in parameters:
            old_values["spread_increase_factor"] = self.spread_increase_factor
            self.spread_increase_factor = float(parameters["spread_increase_factor"])
        if "spread_decrease_factor" in parameters:
            old_values["spread_decrease_factor"] = self.spread_decrease_factor
            self.spread_decrease_factor = float(parameters["spread_decrease_factor"])
        if "strategy" in parameters:
            old_values["strategy"] = self.strategy
            self.strategy = parameters["strategy"]
        if "max_trade_amount" in parameters:
            self.max_trade_amount = float(parameters.get("max_trade_amount", 0.0))
        if "max_orders_per_minute" in parameters:
            self.max_orders_per_minute = int(parameters.get("max_orders_per_minute", 0))

        # Validate — rollback on failure
        try:
            self._validate_parameters()
        except ValueError:
            for key, val in old_values.items():
                setattr(self, key, val)
            raise

        # Audit log: record what changed
        if old_values:
            changes = {
                k: {"old": old_values[k], "new": getattr(self, k)} for k in old_values
            }
            self.logger.warning(f"Bot {self.botid}: AUDIT parameter change: {changes}")

        # Propagate to live modules
        if hasattr(self, "sonarft_search") and self.sonarft_search:
            self.sonarft_search.trade_amount = self.trade_amount
            self.sonarft_search.profit_percentage_threshold = (
                self.profit_percentage_threshold
            )
            self.sonarft_search.max_daily_loss = self.max_daily_loss
        if hasattr(self, "sonarft_execution") and self.sonarft_execution:
            self.sonarft_execution.is_simulation_mode = bool(self.is_simulating_trade)
            self.sonarft_execution.max_trade_amount = self.max_trade_amount
            self.sonarft_execution.max_orders_per_minute = self.max_orders_per_minute
        if hasattr(self, "sonarft_prices") and self.sonarft_prices:
            self.sonarft_prices.strategy = self.strategy
            self.sonarft_prices.spread_increase_factor = self.spread_increase_factor
            self.sonarft_prices.spread_decrease_factor = self.spread_decrease_factor
        self.logger.info(
            f"Bot {self.botid}: parameters hot-reloaded — "
            f"strategy={self.strategy}, "
            f"profit_threshold={self.profit_percentage_threshold}, "
            f"trade_amount={self.trade_amount}, "
            f"sim_mode={self.is_simulating_trade}"
        )

    def _load_api_keys(self):
        """
        Load exchange API keys from environment variables.

        For each configured exchange, reads:
          {EXCHANGE_ID_UPPER}_API_KEY
          {EXCHANGE_ID_UPPER}_SECRET
          {EXCHANGE_ID_UPPER}_PASSWORD  (optional, defaults to empty string)

        If no keys are found for any exchange, logs a warning.
        In simulation mode this is non-blocking — keys are not required.
        In live mode (is_simulating_trade=0) missing keys will cause order
        placement to fail with an authentication error from the exchange.
        """
        keys_loaded = 0
        for exchange_id in self.exchanges:
            prefix = exchange_id.upper()
            api_key = os.environ.get(f"{prefix}_API_KEY")
            secret = os.environ.get(f"{prefix}_SECRET")
            password = os.environ.get(f"{prefix}_PASSWORD", "")
            if api_key and secret:
                self.api_manager.set_api_keys(exchange_id, api_key, secret, password)
                self.logger.info(f"API keys loaded for exchange: {exchange_id}")
                keys_loaded += 1
            else:
                self.logger.warning(
                    f"No API keys found for exchange '{exchange_id}'. "
                    f"Set {prefix}_API_KEY and {prefix}_SECRET environment variables "
                    f"to enable live trading on this exchange."
                )
        self.logger.info(
            f"API keys loading complete: {keys_loaded}/{len(self.exchanges)} exchange(s) configured"
        )
        if keys_loaded == 0 and not self.is_simulating_trade:
            self.logger.warning(
                "No API keys loaded for any exchange and simulation mode is OFF. "
                "Live order placement will fail with authentication errors."
            )

    def set_api_keys(self, exchange: str, api_key: str, secret_key: str, password: str):
        """
        Sets the API keys for a given exchange.
        Args:
            exchange (str): The name of the exchange.
            api_key (str): The API key.
            secret_key (str): The secret key.
            password (str): The password.
        """
        self.api_manager.set_api_keys(exchange, api_key, secret_key, password)

    def create_botid(self) -> str:
        import uuid

        self.logger.info("Creating Bot ID...")
        return str(uuid.uuid4())

    def _write_botid_file(self, path: str):
        """Write botid JSON file with proper file handle management."""
        with open(path, "w") as f:
            json.dump({"botid": self.botid}, f)

    async def stop_bot(self):
        """
        Graceful shutdown sequence:
        1. Signal the run loop to stop
        2. Cancel monitor task and await in-flight trade tasks
        3. Close all exchange connections
        """
        self._stop_event.set()
        self.stop_bot_flag = True
        self.logger.info(f"Bot {self.botid} stop signal sent.")

        # Cancel periodic fee refresh task
        if hasattr(self, '_fee_refresh_task') and self._fee_refresh_task:
            self._fee_refresh_task.cancel()
            try:
                await self._fee_refresh_task
            except asyncio.CancelledError:
                pass

        # Cancel periodic DB backup task
        if hasattr(self, '_db_backup_task') and self._db_backup_task:
            self._db_backup_task.cancel()
            try:
                await self._db_backup_task
            except asyncio.CancelledError:
                pass

        # 1. Shut down trade executor (cancel monitor + await trade tasks)
        if hasattr(self, "sonarft_search") and self.sonarft_search:
            executor = self.sonarft_search.trade_processor.trade_executor
            await executor.shutdown()

        # 2. Close exchange connections (safe now — no in-flight trades)
        if self.api_manager:
            for exchange in self.api_manager.exchanges_instances:
                try:
                    await self.api_manager.close_exchange(exchange.id)
                except Exception as e:
                    self.logger.warning(f"Error closing exchange {exchange.id}: {e}")

        self.logger.info(f"Bot {self.botid} shutdown complete.")

    async def pause_bot(self) -> None:
        """
        Pause the bot's trading loop without deregistering or closing exchange connections.
        The bot remains in BotManager._bots and can be resumed via resume_bot().
        In-flight trade tasks are awaited before returning.
        """
        self._stop_event.set()
        self.stop_bot_flag = True
        self.logger.info("Bot %s paused.", self.botid)

        # Await in-flight trade tasks so no open orders are left unmonitored
        if hasattr(self, "sonarft_search") and self.sonarft_search:
            executor = self.sonarft_search.trade_processor.trade_executor
            # Cancel the monitor task but let trade tasks finish
            if executor.monitor_task and not executor.monitor_task.done():
                executor.monitor_task.cancel()
                try:
                    await executor.monitor_task
                except asyncio.CancelledError:
                    pass

    def resume_bot(self) -> None:
        """
        Reset the stop event so run_bot() can be called again.
        Does not restart the run loop — caller must call run_bot() after this.
        """
        self._stop_event.clear()
        self.stop_bot_flag = False
        self.logger.info("Bot %s resumed.", self.botid)

    async def _periodic_fee_refresh(self) -> None:
        """Background task: refresh exchange fee rates every 24 hours."""
        _24H = int(os.environ.get("SONARFT_FEE_REFRESH_INTERVAL", str(24 * 3600)))
        try:
            while not self._stop_event.is_set():
                try:
                    await asyncio.wait_for(
                        asyncio.shield(self._stop_event.wait()), timeout=_24H
                    )
                except asyncio.TimeoutError:
                    pass
                if self._stop_event.is_set():
                    break
                self.logger.info("Scheduled fee refresh starting...")
                await self.api_manager.refresh_fees()
        except asyncio.CancelledError:
            pass

    async def _periodic_db_backup(self) -> None:
        """Background task: back up the SQLite database every 24 hours.

        Backup path: sonarftdata/history/sonarft_backup_YYYYMMDD.db
        Override interval via SONARFT_BACKUP_INTERVAL env var (seconds).
        Set SONARFT_BACKUP_INTERVAL=0 to disable.
        """
        interval = int(os.environ.get("SONARFT_BACKUP_INTERVAL", str(24 * 3600)))
        if interval == 0:
            return
        try:
            while not self._stop_event.is_set():
                try:
                    await asyncio.wait_for(
                        asyncio.shield(self._stop_event.wait()), timeout=interval
                    )
                except asyncio.TimeoutError:
                    pass
                if self._stop_event.is_set():
                    break
                import time as _t
                date_str = _t.strftime("%Y%m%d", _t.localtime())
                backup_path = _bot_path(
                    "sonarftdata", "history", f"sonarft_backup_{date_str}.db"
                )
                if hasattr(self, 'sonarft_helpers') and self.sonarft_helpers:
                    await self.sonarft_helpers.async_backup_db(backup_path)
        except asyncio.CancelledError:
            pass

    def _validate_precision_rules(self) -> None:
        """
        Warn if any configured exchange has no live symbol precision for any
        configured trading pair. Live precision is preferred over the hardcoded
        EXCHANGE_RULES fallback, which uses exchange-wide defaults that may be
        wrong for non-standard pairs (e.g. SHIB/USDT on Binance).

        This is a warning, not a hard error — the hardcoded fallback is still
        used so trading continues. Operators should investigate if this fires.
        """
        # SonarftMath is not yet initialised at this point; access EXCHANGE_RULES directly
        exchange_rules = {
            'okx', 'bitfinex', 'binance'
        }
        for exchange_id in self.exchanges:
            for symbol_config in self.symbols:
                base = symbol_config['base']
                for quote in symbol_config['quotes']:
                    precision = self.api_manager.get_symbol_precision(exchange_id, base, quote)
                    if precision is None:
                        if exchange_id in exchange_rules:
                            self.logger.warning(
                                f"No live precision for {exchange_id} {base}/{quote} — "
                                f"using hardcoded fallback. Verify precision is correct for this pair."
                            )
                        else:
                            self.logger.warning(
                                f"No live precision for {exchange_id} {base}/{quote} and no "
                                f"hardcoded fallback exists. Trades on this pair will be skipped."
                            )

    async def _reconcile_open_orders(self):
        """
        Query all configured exchanges for open orders on configured symbols
        and cancel any stale orders from previous bot runs.
        Called once at startup (live mode only). Runs all exchange/symbol
        queries concurrently via asyncio.gather for faster startup.
        """
        self.logger.info("Reconciling open orders from previous runs...")
        cancelled_count = 0

        async def _check_symbol(exchange_id: str, base: str, quote: str) -> int:
            """Fetch and cancel open orders for one exchange/symbol. Returns cancel count."""
            symbol = f"{base}/{quote}"
            count = 0
            try:
                orders = await self.api_manager.call_api_method(
                    exchange_id, "fetch_open_orders", "fetch_open_orders", symbol,
                )
                if not orders:
                    return 0
                self.logger.warning(
                    f"Found {len(orders)} open order(s) on {exchange_id} {symbol} — cancelling"
                )
                for order in orders:
                    result = await self.api_manager.cancel_order(
                        exchange_id, order["id"], base, quote
                    )
                    if result:
                        count += 1
                        self.logger.info(f"Cancelled stale order {order['id']} on {exchange_id}")
                    else:
                        self.logger.warning(
                            f"Failed to cancel stale order {order['id']} on {exchange_id}"
                        )
            except Exception as e:
                self.logger.warning(f"Error reconciling orders on {exchange_id} {symbol}: {e}")
            return count

        tasks = [
            _check_symbol(exchange_id, symbol_config["base"], quote)
            for exchange_id in self.exchanges
            for symbol_config in self.symbols
            for quote in symbol_config["quotes"]
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, int):
                cancelled_count += r

        if cancelled_count > 0:
            self.logger.warning(
                f"Reconciliation complete: cancelled {cancelled_count} stale order(s)"
            )
        else:
            self.logger.info("Reconciliation complete: no stale orders found")

    async def _reconcile_open_positions(self) -> None:
        """
        Log any open positions that survived a restart.
        Called once at startup in live mode after _reconcile_open_orders().

        Open positions indicate that a first leg filled but the second leg
        did not complete before the bot stopped. These require manual review
        and intervention on the exchange.
        """
        if not hasattr(self, 'sonarft_helpers') or not self.sonarft_helpers:
            return
        open_positions = await self.sonarft_helpers.get_open_positions(self.botid)
        if not open_positions:
            self.logger.info("Position reconciliation: no open positions found")
            return
        self.logger.warning(
            f"Position reconciliation: found {len(open_positions)} open position(s) "
            f"from a previous session — manual review required:"
        )
        for pos in open_positions:
            self.logger.warning(
                f"  OPEN POSITION: {pos['side'].upper()} {pos['amount']} {pos['symbol']} "
                f"@ {pos['entry_price']} on {pos['exchange']} "
                f"(order {pos['order_id']}, opened {pos['opened_at']})"
            )
        if self._alert_callback:
            await self._send_alert(
                f"SonarFT Bot {self.botid}: {len(open_positions)} open position(s) "
                f"detected on startup — manual review required. "
                f"Symbols: {', '.join(p['symbol'] for p in open_positions)}"
            )

    # ### loaders *****************************************************
    def _load_config_section(self, pathname: str, key: str):
        """Generic JSON config loader: opens pathname and returns data[key]."""
        if not os.path.isabs(pathname):
            pathname = _bot_path(pathname)
        try:
            with open(pathname) as f:
                data = json.load(f)
        except FileNotFoundError:
            raise BotCreationError(f"Configuration file not found: {pathname}") from None
        except json.JSONDecodeError as e:
            raise BotCreationError(f"Invalid JSON in {pathname}: {e}") from e
        if key not in data:
            raise BotCreationError(f"Configuration key '{key}' not found in {pathname}")
        return data[key]

    def load_configurations(self, config_setup: str = "config_1"):
        config = self._load_config_section(
            _bot_path("sonarftdata", "config.json"), config_setup
        )[0]

        self.market = self._load_config_section(
            config["markets_pathname"], f"market_{config['markets_setup']}"
        )
        self.logger.info(f"Market loaded: {self.market}")

        parameters_raw = self._load_config_section(
            config["parameters_pathname"], f"parameters_{config['parameters_setup']}"
        )[0]
        self.logger.info(
            f"Parameters loaded: {', '.join(f'{k}: {v}' for k, v in parameters_raw.items())}"
        )
        try:
            parameters = ParametersConfig(**parameters_raw)
        except Exception as e:
            raise BotCreationError(f"Invalid trading parameters: {e}") from e

        self.profit_percentage_threshold = parameters.profit_percentage_threshold
        self.trade_amount               = parameters.trade_amount
        self.is_simulating_trade        = parameters.is_simulating_trade
        self.max_daily_loss             = parameters.max_daily_loss
        self.spread_increase_factor     = parameters.spread_increase_factor
        self.spread_decrease_factor     = parameters.spread_decrease_factor
        self.strategy                   = parameters.strategy
        self.max_trade_amount           = parameters.max_trade_amount
        self.max_orders_per_minute      = parameters.max_orders_per_minute
        self.slippage_buffer            = parameters.slippage_buffer
        self.flash_crash_threshold      = parameters.flash_crash_threshold
        self.max_daily_trades           = parameters.max_daily_trades
        self.max_total_exposure         = parameters.max_total_exposure
        # _validate_parameters() is now superseded by Pydantic — kept for
        # hot-reload path (apply_parameters) which does not go through Pydantic.
        self._check_live_mode_guard()

        symbols_raw = self._load_config_section(
            config["symbols_pathname"], f"symbols_{config['symbols_setup']}"
        )
        try:
            self.symbols = [SymbolConfig(**s).model_dump() for s in symbols_raw]
        except Exception as e:
            raise BotCreationError(f"Invalid symbols configuration: {e}") from e
        if not self.symbols:
            raise BotCreationError("symbols list must not be empty")
        self.logger.info(f"Symbols loaded: {self.symbols}")

        exchanges_raw = self._load_config_section(
            config["exchanges_pathname"], f"exchanges_{config['exchanges_setup']}"
        )
        if not exchanges_raw:
            raise BotCreationError("exchanges list must not be empty")
        self.exchanges = exchanges_raw
        self.logger.info(f"Exchanges loaded: {self.exchanges}")

        fees_raw = self._load_config_section(
            config["fees_pathname"], f"exchanges_fees_{config['fees_setup']}"
        )
        try:
            self.exchanges_fees = [FeeConfig(**f).model_dump(exclude_none=True) for f in fees_raw]
        except Exception as e:
            raise BotCreationError(f"Invalid fees configuration: {e}") from e

        self.active_indicators = self._load_config_section(
            config["indicators_pathname"], f"indicators_{config['indicators_setup']}"
        )
        self.logger.info(f"Indicators loaded: {self.active_indicators}")

    def _check_live_mode_guard(self) -> None:
        """Raise BotCreationError if live mode is requested without explicit opt-in.

        Live trading requires SONARFT_ALLOW_LIVE=true to be set in the environment.
        This prevents accidental real-money trading from a misconfigured config file.
        """
        if self.is_simulating_trade == 0:
            if not os.environ.get("SONARFT_ALLOW_LIVE"):
                raise BotCreationError(
                    "Live trading requires SONARFT_ALLOW_LIVE=true environment variable. "
                    "Set is_simulating_trade=1 for simulation mode."
                )
            self.logger.warning(
                "⚠️  LIVE TRADING MODE ACTIVE — real orders will be placed on exchanges"
            )

    def _validate_parameters(self):
        """Raise ValueError early if any trading parameter is out of safe range."""
        if self.strategy not in ("arbitrage", "market_making"):
            raise ValueError(
                f"strategy must be 'arbitrage' or 'market_making', got '{self.strategy}'"
            )
        if not (0 < self.profit_percentage_threshold < 1):
            raise ValueError(
                f"profit_percentage_threshold must be between 0 and 1, got {self.profit_percentage_threshold}"
            )
        if self.trade_amount <= 0:
            raise ValueError(f"trade_amount must be positive, got {self.trade_amount}")
        if self.is_simulating_trade not in (0, 1):
            raise ValueError(
                f"is_simulating_trade must be 0 or 1, got {self.is_simulating_trade}"
            )
        if self.max_daily_loss < 0:
            raise ValueError(f"max_daily_loss must be >= 0, got {self.max_daily_loss}")
        if self.strategy == "market_making":
            if not (1.0 < self.spread_increase_factor < 1.01):
                raise ValueError(
                    f"spread_increase_factor must be between 1.0 and 1.01, got {self.spread_increase_factor}"
                )
            if not (0.99 < self.spread_decrease_factor < 1.0):
                raise ValueError(
                    f"spread_decrease_factor must be between 0.99 and 1.0, got {self.spread_decrease_factor}"
                )

    # ### Initialize all modules ***************************************
    async def initialize_modules(self):
        """
        Initializes all modules required for the bot's operation.
        """
        self.logger.info("Initializing Helpers module...")
        self.sonarft_helpers = SonarftHelpers(self.is_simulating_trade, self.logger)
        self.logger.info("Initializing Helpers module OK")

        self.logger.info("Initializing Validators module...")
        self.sonarft_validators = SonarftValidators(self.api_manager, self.logger)
        self.logger.info("Initializing Validators module OK")

        self.logger.info("Initializing Indicators module...")
        self.sonarft_indicators = SonarftIndicators(self.api_manager, self.logger)
        self.logger.info("Initializing Indicators module OK")

        self.logger.info("Initializing Math module...")
        self.sonarft_math = SonarftMath(self.api_manager)
        self.logger.info("Initializing Math module OK")

        self.logger.info("Initializing Prices module...")
        self.sonarft_prices = SonarftPrices(
            self.api_manager, self.sonarft_indicators, self.logger
        )
        self.sonarft_prices.strategy = self.strategy
        self.sonarft_prices.spread_increase_factor = self.spread_increase_factor
        self.sonarft_prices.spread_decrease_factor = self.spread_decrease_factor
        self.sonarft_prices.active_indicators = self.active_indicators
        self.logger.info("Initializing Prices module OK")

        self.logger.info("Initializing Execution module...")
        self.sonarft_execution = SonarftExecution(
            self.api_manager,
            self.sonarft_helpers,
            self.is_simulating_trade,
            self.logger,
            max_trade_amount=getattr(self, "max_trade_amount", 0.0),
            max_orders_per_minute=getattr(self, "max_orders_per_minute", 0),
            slippage_buffer=getattr(self, "slippage_buffer", 0.0),
            flash_crash_threshold=getattr(self, "flash_crash_threshold", 0.02),
            max_total_exposure=getattr(self, "max_total_exposure", 0.0),
        )
        self.sonarft_execution._alert_callback = self._send_alert
        self.logger.info("Initializing Execution module OK")

        self.logger.info("Initializing Search module...")
        self.sonarft_search = SonarftSearch(
            self.sonarft_math,
            self.sonarft_prices,
            self.sonarft_validators,
            self.sonarft_execution,
            self.trade_amount,
            self.symbols,
            self.profit_percentage_threshold,
            self.is_simulating_trade,
            self.logger,
            max_daily_loss=self.max_daily_loss,
            slippage_buffer=getattr(self, 'slippage_buffer', 0.0),
            max_daily_trades=getattr(self, 'max_daily_trades', 0),
        )
        await self.sonarft_search.start()
        await self.sonarft_search.set_botid(self.botid)
        self.logger.info("Initializing Search module OK")


class BotCreationError(Exception):
    """Raised when there's an issue during the bot creation process."""

    def __init__(self, message="Failed to create the bot."):
        self.message = message
        super().__init__(self.message)
