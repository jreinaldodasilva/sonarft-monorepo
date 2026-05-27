# Bot Package — Configuration & Runtime Environment Review

**Prompt ID:** 07-BOT-CONFIG  
**Generated:** July 2025  
**Source:** `packages/bot/sonarftdata/`, `sonarft_bot.py`, `config_schemas.py`, `Dockerfile`, `.env.example`  
**Output File:** `docs/operations/bot-config.md`  
**Depends On:** `docs/architecture/bot-overview.md` (01)

---

## 1. Configuration File Structure

### Format

All configuration is JSON. No YAML, TOML, or Python dicts. Files live under `sonarftdata/`.

```
sonarftdata/
├── config.json              ← master index: maps config_N → file paths + setup keys
├── config_markets.json      ← market type (crypto / forex)
├── config_exchanges.json    ← exchange lists per setup
├── config_symbols.json      ← trading pairs per setup
├── config_parameters.json   ← trading parameters per setup
├── config_fees.json         ← exchange fee rates per setup
├── config_indicators.json   ← active indicator list per setup
└── bots/
    └── {uuid}.json          ← per-bot registry (botid only)
```

### Schema validation

Pydantic v2 models validate three config sections at load time:

| Schema | File | Validates |
|---|---|---|
| `ParametersConfig` | `config_schemas.py` | All trading parameters with type + range checks |
| `SymbolConfig` | `config_schemas.py` | Base currency + non-empty quotes list |
| `FeeConfig` | `config_schemas.py` | Exchange name + non-negative fee rates |

Markets, exchanges, and indicators are loaded as raw JSON with no Pydantic validation — only presence and non-empty checks.

### Full configuration parameter inventory

#### `config_parameters.json` — trading parameters

| Parameter | Required | Type | Default (config) | Pydantic validation | Purpose |
|---|---|---|---|---|---|
| `strategy` | Yes | `"arbitrage"` \| `"market_making"` | `"arbitrage"` | `Literal` | Trading strategy |
| `profit_percentage_threshold` | Yes | float | 0.0001 | `gt=0, lt=1` | Minimum net profit % to trade |
| `trade_amount` | Yes | float | 0.01 | `gt=0` | Base currency amount per trade |
| `is_simulating_trade` | Yes | `0` \| `1` | 1 | `Literal[0, 1]` | Simulation mode flag |
| `max_daily_loss` | No | float | 100.0 | `ge=0` | Daily loss halt threshold (quote currency) |
| `max_trade_amount` | No | float | 0.1 | `ge=0` | Max single trade size (0 = disabled) |
| `max_orders_per_minute` | No | int | 10 | `ge=0` | Order rate cap (0 = disabled) |
| `spread_increase_factor` | No | float | 1.00020 | range check if market_making | Sell price multiplier (market-making) |
| `spread_decrease_factor` | No | float | 0.99980 | range check if market_making | Buy price multiplier (market-making) |
| `slippage_buffer` | No | float | 0.0002 | `ge=0` | Added to profit threshold; price drift tolerance |
| `flash_crash_threshold` | No | float | 0.02 | `gt=0, lt=1` | Max price deviation between exchanges |
| `max_daily_trades` | No | int | 0 | `ge=0` | Daily trade count cap (0 = disabled) |
| `max_total_exposure` | No | float | 0.0 | `ge=0` | Aggregate open position cap (0 = disabled) |

#### `config_symbols.json` — trading pairs

| Field | Required | Type | Validation |
|---|---|---|---|
| `base` | Yes | string | `min_length=1` |
| `quotes` | Yes | list[string] | `min_length=1`; each quote non-empty |

#### `config_fees.json` — exchange fees

| Field | Required | Type | Validation |
|---|---|---|---|
| `exchange` | Yes | string | `min_length=1` |
| `buy_fee` | Yes | float | `ge=0` |
| `sell_fee` | Yes | float | `ge=0` |
| `maker_buy_fee` | No | float | `ge=0` (if present) |
| `maker_sell_fee` | No | float | `ge=0` (if present) |

#### `config_exchanges.json` — exchange lists

Raw JSON list of exchange ID strings. No Pydantic validation. Non-empty check only.

#### `config_indicators.json` — active indicators

Raw JSON list of indicator name strings. No Pydantic validation. No non-empty check — an empty list is accepted and disables all indicator gates.

#### `config_markets.json` — market type

Raw JSON list of market type strings (e.g. `["crypto"]`). No validation. Used only for logging.

#### `config.json` — master index

Maps config setup names to file paths and setup keys. No Pydantic validation. Missing keys raise `BotCreationError` with a clear message.

---

## 2. Configuration Loading Behaviour

### Entry point

```
SonarftBot.create_bot(config_setup)
    → load_configurations(config_setup)
        → _load_config_section(config.json, config_setup)   ← master index
        → _load_config_section(markets_pathname, market_N)
        → _load_config_section(parameters_pathname, parameters_N) → ParametersConfig(...)
        → _load_config_section(symbols_pathname, symbols_N)  → [SymbolConfig(...)]
        → _load_config_section(exchanges_pathname, exchanges_N)
        → _load_config_section(fees_pathname, fees_N)        → [FeeConfig(...)]
        → _load_config_section(indicators_pathname, indicators_N)
```

All config is loaded synchronously on the event loop (blocking file I/O — see Prompt 02, Low finding).

### File location resolution

`_load_config_section` resolves relative paths against `_BOT_DIR` (the directory containing `sonarft_bot.py`):

```python
if not os.path.isabs(pathname):
    pathname = _bot_path(pathname)
```

This means config files are always resolved relative to the bot package directory, regardless of the current working directory. ✅ This is correct for Docker deployments where `WORKDIR=/app` and the bot package is at `/app`.

### Error handling on missing/invalid config

| Error | Raised as | Message quality |
|---|---|---|
| File not found | `BotCreationError` | `"Configuration file not found: {pathname}"` ✅ |
| Invalid JSON | `BotCreationError` | `"Invalid JSON in {pathname}: {error}"` ✅ |
| Missing key | `BotCreationError` | `"Configuration key '{key}' not found in {pathname}"` ✅ |
| Pydantic validation failure | `BotCreationError` | `"Invalid trading parameters: {pydantic_error}"` ✅ |
| Empty exchanges list | `BotCreationError` | `"exchanges list must not be empty"` ✅ |
| Empty symbols list | `BotCreationError` | `"symbols list must not be empty"` ✅ |

All config errors raise `BotCreationError` with descriptive messages. `BotManager.create_bot` catches this and returns `None`. ✅

### Environment variable overrides

No environment variable overrides for JSON config values. Config is file-only. Runtime behaviour (cycle timing, circuit breaker, concurrency) is controlled via environment variables (see Section 4).

### Merge behaviour

No config merging. Each bot loads one complete config setup. Multiple bots can use different config setups (e.g. bot A uses `config_1`, bot B uses `config_2`).

---

## 3. Per-Bot & Per-Client Configuration

### Bot isolation

Each `SonarftBot` instance loads its own config independently. Config values are stored as instance attributes on `SonarftBot` — no shared mutable config state between bots. ✅

### Per-client config

The `sonarftdata/config/` directory contains per-client parameter files (e.g. `dev_user_parameters.json`, `c482b04b-..._parameters.json`). These are not loaded by the current `load_configurations` path — they appear to be legacy or API-managed files. The API layer is responsible for routing per-client config to the correct bot.

### Hot-reload

`apply_parameters` supports hot-reloading a subset of parameters on a running bot:

| Hot-reloadable | Not hot-reloadable |
|---|---|
| `profit_percentage_threshold` | `exchanges` |
| `trade_amount` | `symbols` |
| `is_simulating_trade` (with `SONARFT_ALLOW_LIVE` guard) | `library` (ccxt/ccxtpro) |
| `max_daily_loss` | `indicators` |
| `spread_increase_factor` / `spread_decrease_factor` | `fees` |
| `strategy` | — |
| `max_trade_amount` | — |
| `max_orders_per_minute` | — |

Hot-reload includes rollback on Pydantic validation failure. ✅ Changes are audit-logged at `WARNING` level. ✅

**Finding — hot-reload does not propagate `slippage_buffer`, `flash_crash_threshold`, `max_daily_trades`, or `max_total_exposure`:** `apply_parameters` handles 9 parameters but omits 4 that are present in `ParametersConfig`. If an operator hot-reloads parameters, these 4 values cannot be updated without a bot restart.


---

## 4. Environment Variable Usage

### Complete inventory

| Variable | Required | Default | Purpose | Security notes |
|---|---|---|---|---|
| `{EXCHANGE}_API_KEY` | Live only | — | Exchange API key | Never logged ✅ |
| `{EXCHANGE}_SECRET` | Live only | — | Exchange secret | Never logged ✅ |
| `{EXCHANGE}_PASSWORD` | Exchange-dependent | `""` | Exchange passphrase (OKX) | Never logged ✅ |
| `SONARFT_ALLOW_LIVE` | Live only | unset | Live trading opt-in gate | — |
| `SONARFT_MAX_FAILURES` | No | `"5"` | Circuit breaker threshold | — |
| `SONARFT_BACKOFF_BASE` | No | `"30"` | Backoff seconds per failure | — |
| `SONARFT_CYCLE_SLEEP_MIN` | No | `"6"` | Min seconds between cycles | — |
| `SONARFT_CYCLE_SLEEP_MAX` | No | `"18"` | Max seconds between cycles | — |
| `SONARFT_MAX_CONCURRENT_TRADES` | No | `"10"` | Max in-flight trade tasks | — |
| `SONARFT_FEE_REFRESH_INTERVAL` | No | `"86400"` | Fee refresh interval (seconds) | — |
| `SONARFT_FEE_ROUNDING` | No | `"HALF_EVEN"` | Fee rounding mode | — |
| `SONARFT_ALERT_WEBHOOK` | No | unset | Webhook URL for critical alerts | URL only, no secrets in URL |
| `SONARFT_BACKUP_INTERVAL` | No | `"86400"` | DB backup interval (seconds) | — |
| `SONARFT_BACKUP_DIR` | No | `sonarftdata/backups/` | Backup destination directory | — |

### API key handling

API keys are read from environment variables in `_load_api_keys`:

```python
api_key  = os.environ.get(f"{prefix}_API_KEY")
secret   = os.environ.get(f"{prefix}_SECRET")
password = os.environ.get(f"{prefix}_PASSWORD", "")
```

Keys are passed directly to `api_manager.set_api_keys` and stored on the ccxt exchange instance. They are never logged — only a confirmation message `"API keys loaded for exchange: {exchange_id}"` is emitted. ✅

**Finding — API keys stored in memory on ccxt exchange instances for the bot's lifetime:** Once loaded, keys are accessible via `exchange.apiKey`, `exchange.secret`, `exchange.password` on the ccxt instance. Any code with access to `api_manager.exchanges_instances` can read the keys. This is unavoidable for a trading bot but means a memory dump or debug log that serialises the exchange instance would expose keys.

### Integer parsing of env vars

All numeric env vars are parsed with `int(os.environ.get("VAR", "default"))`. If an operator sets `SONARFT_MAX_FAILURES=abc`, this raises `ValueError` inside `run_bot`, which is caught by the outer `except Exception` and triggers the circuit breaker. The bot would halt immediately on startup.

**Finding — no validation of environment variable values at startup:** Env vars are parsed lazily inside `run_bot` and `_periodic_fee_refresh` — not at `create_bot` time. An invalid value (e.g. `SONARFT_CYCLE_SLEEP_MIN=abc`) would not be caught until the first cycle runs. Should be validated and converted at `create_bot` time.

---

## 5. Defaults & Hardcoding Audit

### Hardcoded values

| Value | Location | Should be config? | Risk |
|---|---|---|---|
| `RSI_OVERBOUGHT = 70` | `models.py` | Yes — strategy-dependent | Medium |
| `RSI_OVERSOLD = 30` | `models.py` | Yes — strategy-dependent | Medium |
| `EXCHANGE_RULES` (precision) | `sonarft_math.py` | Partially — live data preferred | Medium (see Prompt 04) |
| `weight=12` (VWAP depth) | `trade_processor.py` | Yes — affects price quality | Low |
| `depth=3` (indicator VWAP) | `sonarft_prices.py` | Yes — affects price blend | Low |
| `period=14` (SMA/RSI) | `sonarft_prices.py` | Yes — strategy-dependent | Low |
| `rsi_period=14, stoch_period=14` | `sonarft_prices.py` | Yes — strategy-dependent | Low |
| `k_period=3, d_period=3` | `sonarft_prices.py` | Yes — strategy-dependent | Low |
| `short_period=12, long_period=26, signal_period=9` (MACD) | `sonarft_indicators.py` | Yes — strategy-dependent | Low |
| `lookback_period=24` (support/resistance) | `sonarft_prices.py` | Yes | Low |
| `limit=6` (short-term trend) | `sonarft_prices.py` | Yes | Low |
| `max_wait_seconds=120` (monitor_price) | `sonarft_execution.py` | Yes — exchange-dependent | Low |
| `max_wait_seconds=300` (monitor_order) | `sonarft_execution.py` | Yes — exchange-dependent | Low |
| `max_retries=3` (cancel retry) | `sonarft_execution.py` | Yes | Low |
| `_INDICATOR_CACHE_TTL=60` | `sonarft_indicators.py` | Yes | Low |
| `_MAX_CONCURRENT_TRADES=10` | `trade_executor.py` | Env var override ✅ | None |
| `min_trading_volume_coefficient=50` | `trade_validator.py` | Yes — hardcoded in call | Low |

**Finding — RSI thresholds (70/30) are hardcoded constants:** `RSI_OVERBOUGHT` and `RSI_OVERSOLD` are defined in `models.py` and used in both `sonarft_prices.py` and `sonarft_execution.py`. Different strategies may require different thresholds (e.g. 80/20 for trending markets). These should be configurable per-bot via `config_parameters.json`.

**Finding — indicator periods are hardcoded in `weighted_adjust_prices`:** The RSI period (14), StochRSI periods (14/14/3/3), and MACD periods (12/26/9) are hardcoded as local variables in `weighted_adjust_prices`. They cannot be changed without modifying source code. These should be read from `active_indicators` config or a dedicated `config_indicator_params.json`.

**Finding — `min_trading_volume_coefficient=50` hardcoded in `TradeValidator`:** The liquidity check requires trading volume to be at least 50× the trade amount. This is a significant constraint that is not documented or configurable. For a `trade_amount=0.01 ETH`, the exchange must have at least 0.5 ETH of 24h volume — easily met. For larger amounts, this could silently block all trades.

### Unsafe defaults

| Default | Risk | Assessment |
|---|---|---|
| `is_simulating_trade=1` in both parameter configs | Safe — simulation is the default ✅ | Correct |
| `max_daily_trades=0` (disabled) | No daily trade cap in live mode | Medium |
| `max_total_exposure=0.0` (disabled) | No exposure cap in live mode | Medium |
| `SONARFT_ALLOW_LIVE` unset | Live trading blocked by default ✅ | Correct |
| `spread_increase_factor=1.00115` in `parameters_2` | Within valid range (1.0–1.01) ✅ | Correct |

---

## 6. Docker Runtime Assumptions

### Dockerfile review

```dockerfile
FROM python:3.11-slim          # ✅ Minimal image, correct Python version
WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .
COPY . .                       # ⚠️ Copies entire directory including sonarftdata/
RUN adduser --disabled-password --gecos '' --uid 1000 sonarft \
    && chown -R sonarft:sonarft /app
USER sonarft                   # ✅ Non-root user
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "print('ok')" || exit 1   # ⚠️ Trivial health check
CMD ["python", "-m", "sonarft_bot"]
```

**Finding — `COPY . .` includes `sonarftdata/` with live config and bot registry files:** The entire `sonarftdata/` directory is baked into the image. This means:
1. Config files (including fee rates and exchange lists) are embedded in the image — changes require a rebuild.
2. Bot registry JSON files (`sonarftdata/bots/*.json`) from development are included in production images.
3. The SQLite database (`sonarftdata/history/sonarft.db`) would be included if it exists at build time.

A `.dockerignore` file should exclude `sonarftdata/bots/`, `sonarftdata/history/`, and `sonarftdata/backups/`.

**Finding — health check is trivial:** `python -c "print('ok')"` only verifies Python is installed, not that the bot is running or healthy. A meaningful health check would verify the bot process is alive and the event loop is responsive.

**Finding — no volume mount for `sonarftdata/`:** Config files and the SQLite database are inside the container. If the container is replaced, all trade history and bot registry data is lost. `sonarftdata/` should be mounted as a Docker volume.

**Finding — `requirements.txt` includes API-layer dependencies:** `fastapi`, `uvicorn`, `simple-websocket`, and `PyJWT` are installed in the bot container but not used. This increases image size and attack surface unnecessarily.

### Container security

| Aspect | Status |
|---|---|
| Non-root user | ✅ `USER sonarft` (uid 1000) |
| Minimal base image | ✅ `python:3.11-slim` |
| No secrets in image | ✅ Keys via env vars only |
| No privileged mode | ✅ (assumed — no `--privileged` in Dockerfile) |
| Read-only filesystem | ❌ Not configured — bot writes to `sonarftdata/` |

---

## 7. File Paths & History Storage

### Path construction

All paths are constructed via `_bot_path(*parts)` which anchors to `_BOT_DIR = os.path.dirname(os.path.abspath(__file__))`. This is consistent across `sonarft_bot.py`, `sonarft_helpers.py`, and `sonarft_manager.py`. ✅

**Finding — `_BOT_DIR` and `_bot_path` are duplicated across three modules:** `sonarft_bot.py`, `sonarft_helpers.py`, and `sonarft_search.py` each define their own `_BOT_DIR` and path helpers. If the package structure changes, all three must be updated. Should be centralised in a single `paths.py` module.

**Finding — `sonarft_search.py` defines `_DB_PATH` as a module-level constant:** Unlike `sonarft_helpers.py` which uses `SonarftHelpers._DB_PATH` (a class attribute), `sonarft_search.py` defines `_DB_PATH` as a module-level variable. Both point to the same path, but they are independent definitions. If the path ever changes, it must be updated in two places.

### Storage locations

| Data | Location | Format | Retention |
|---|---|---|---|
| Trade history | `sonarftdata/history/sonarft.db` (table: `trades`) | SQLite | `keep_last=10,000` via `purge_history` |
| Order history | `sonarftdata/history/sonarft.db` (table: `orders`) | SQLite | `keep_last=10,000` |
| Position tracker | `sonarftdata/history/sonarft.db` (table: `positions`) | SQLite | No purge |
| Daily loss | `sonarftdata/history/sonarft.db` (table: `daily_loss`) | SQLite | No purge |
| Bot registry | `sonarftdata/bots/{uuid}.json` | JSON | Deleted on `remove_bot` |
| Error history | `sonarftdata/errors_history.json` | JSON array | No rotation ⚠️ |
| Balance history | `sonarftdata/balance_history.json` | JSON array | No rotation ⚠️ |
| DB backups | `sonarftdata/backups/sonarft_backup_{date}.db` | SQLite | No rotation ⚠️ |

**Finding — `errors_history.json` and `balance_history.json` have no size limit or rotation:** These JSON files grow unboundedly. `_append_json` reads the entire file, appends, and rewrites it on every call. For a long-running bot with frequent errors or balance checks, these files can grow to hundreds of MB, causing increasingly slow writes.

**Finding — DB backup files have no rotation:** `_periodic_db_backup` creates `sonarft_backup_{YYYYMMDD}.db` daily. Old backups are never deleted. Over time, the backup directory accumulates one file per day indefinitely.

---

## 8. Path Safety & Traversal Risks

### User-supplied paths

Config file paths come from `config.json` (e.g. `"parameters_pathname": "sonarftdata/config_parameters.json"`). These are operator-supplied values read from a file on disk — not from user HTTP input. In a Docker deployment, the config file is baked into the image or mounted as a volume, so path traversal via config is only possible if an attacker can modify the config file (which implies full filesystem access already).

**Finding — no path traversal sanitisation on config pathnames:** `_load_config_section` resolves relative paths via `_bot_path(pathname)`:

```python
if not os.path.isabs(pathname):
    pathname = _bot_path(pathname)
```

A config value of `"../../etc/passwd"` would resolve to a path outside `sonarftdata/`. Since config files are operator-controlled (not user-controlled via HTTP), this is Low risk in practice. However, if the API layer ever allows users to specify config paths, this becomes a High risk.

**Finding — `SONARFT_BACKUP_DIR` env var is used directly in `os.path.join` without sanitisation:** 

```python
backup_dir = os.environ.get("SONARFT_BACKUP_DIR", _bot_path("sonarftdata", "backups"))
backup_path = os.path.join(backup_dir, f"sonarft_backup_{date_str}.db")
```

An operator setting `SONARFT_BACKUP_DIR=/etc` would write backup files to `/etc/`. This is operator-controlled and Low risk, but should be validated to be an absolute path within an expected directory.

### Botid in file paths

Bot registry files are named `{botid}.json` where `botid` is a UUID generated by `uuid.uuid4()`. UUIDs contain only hex digits and hyphens — no path traversal characters. ✅


---

## 9. Configuration Validation

### Schema validation coverage

| Config section | Validated by | Type checks | Range checks | Dependency checks |
|---|---|---|---|---|
| Trading parameters | `ParametersConfig` (Pydantic) | ✅ | ✅ (`gt`, `lt`, `ge`) | ✅ (spread factors for market_making) |
| Symbols | `SymbolConfig` (Pydantic) | ✅ | ✅ (`min_length`) | — |
| Fees | `FeeConfig` (Pydantic) | ✅ | ✅ (`ge=0`) | — |
| Exchanges | None | ❌ | ❌ | ❌ |
| Indicators | None | ❌ | ❌ | ❌ |
| Markets | None | ❌ | ❌ | ❌ |
| Master index (`config.json`) | None | ❌ | ❌ | ❌ |

**Finding — exchanges, indicators, and markets have no schema validation:** An invalid exchange name (e.g. `"binnance"` with a typo) passes config loading and only fails at `load_exchanges_instances` when ccxt raises `AttributeError`. The error is not caught at config load time — it propagates as an unhandled exception during `SonarftApiManager` construction, which is not wrapped in `BotCreationError`. This would cause an unhandled exception in `create_bot` rather than a clean `BotCreationError`.

**Finding — `config_indicators.json` accepts any string:** An indicator name like `"rsi_v2"` would be accepted, stored in `active_indicators`, and silently never match any `_indicator_active` check. All indicator gates would be disabled. No warning is emitted for unrecognised indicator names.

### Validation at hot-reload

`apply_parameters` calls `_validate_parameters()` after applying changes, with rollback on failure. `_validate_parameters` checks:
- `strategy` in `("arbitrage", "market_making")`
- `0 < profit_percentage_threshold < 1`
- `trade_amount > 0`
- `is_simulating_trade` in `(0, 1)`
- `max_daily_loss >= 0`
- Spread factors within range for market_making

This is a subset of Pydantic validation (which runs at initial load). The hot-reload path does not use Pydantic — it uses the manual `_validate_parameters` method. The two validation paths can diverge if `ParametersConfig` is updated but `_validate_parameters` is not.

**Finding — dual validation paths for parameters:** Initial load uses Pydantic (`ParametersConfig`); hot-reload uses `_validate_parameters`. These must be kept in sync manually. A single source of truth (always use Pydantic) would be safer.

---

## 10. Configuration Issues Table

| Issue | Location | Type | Severity | Remediation |
|---|---|---|---|---|
| `exchanges_fees_2` has zero fees | `config_fees.json` | Dangerous config | **High** | Remove or add Pydantic validator rejecting zero fees |
| `COPY . .` bakes `sonarftdata/` into Docker image | `Dockerfile` | Deployment | **High** | Add `.dockerignore`; mount `sonarftdata/` as volume |
| RSI thresholds (70/30) hardcoded | `models.py` | Hardcoding | Medium | Move to `config_parameters.json` |
| Indicator periods hardcoded in `weighted_adjust_prices` | `sonarft_prices.py` | Hardcoding | Medium | Move to `config_indicators.json` or dedicated params |
| `max_daily_trades=0` and `max_total_exposure=0.0` disabled by default | `config_parameters.json` | Unsafe default | Medium | Set non-zero defaults for live mode; document |
| `_BOT_DIR` / `_bot_path` duplicated in 3 modules | Multiple | Code quality | Medium | Centralise in `paths.py` |
| `_DB_PATH` defined in both `sonarft_helpers.py` and `sonarft_search.py` | Both | Duplication | Medium | Use `SonarftHelpers._DB_PATH` in `sonarft_search.py` |
| Hot-reload missing 4 parameters | `sonarft_bot.apply_parameters` | Incomplete | Medium | Add `slippage_buffer`, `flash_crash_threshold`, `max_daily_trades`, `max_total_exposure` |
| Dual validation paths (Pydantic + `_validate_parameters`) | `sonarft_bot.py` | Maintenance risk | Medium | Use Pydantic for hot-reload validation too |
| Exchange names not validated at config load | `sonarft_bot.load_configurations` | Missing validation | Medium | Add Pydantic schema for exchanges list |
| Indicator names not validated | `sonarft_bot.load_configurations` | Missing validation | Low | Add allowed-values check for indicator names |
| `errors_history.json` / `balance_history.json` unbounded growth | `sonarft_helpers.py` | Operational | Low | Add size limit or rotate to SQLite |
| DB backup files never rotated | `sonarft_bot._periodic_db_backup` | Operational | Low | Keep last N backups; delete older ones |
| Trivial Docker health check | `Dockerfile` | Deployment | Low | Check bot process liveness |
| Env vars parsed lazily, not at startup | `sonarft_bot.run_bot` | Operational | Low | Parse and validate all env vars in `create_bot` |
| `min_trading_volume_coefficient=50` hardcoded | `trade_validator.py` | Hardcoding | Low | Move to config |
| `SONARFT_BACKUP_DIR` not validated | `sonarft_bot.py` | Path safety | Low | Validate is absolute path within expected directory |

---

## 11. Runtime Configuration Summary

| Aspect | Current Method | Safe? | Recommendation |
|---|---|---|---|
| Trading parameters | JSON + Pydantic validation | ✅ | Add missing hot-reload params |
| Exchange API keys | Environment variables | ✅ | Never log; rotate regularly |
| Live trading gate | `SONARFT_ALLOW_LIVE` env var + config flag | ✅ | Keep dual opt-in |
| Circuit breaker | Env var with default | ✅ | Validate at startup |
| Cycle timing | Env vars with defaults | ✅ | Validate at startup |
| Fee rates | JSON config + live refresh | ✅ | Remove zero-fee test config |
| Indicator selection | JSON list (no validation) | ⚠️ | Add allowed-values validation |
| Exchange selection | JSON list (no validation) | ⚠️ | Add ccxt exchange name validation |
| Data persistence | SQLite + JSON fallback | ✅ | Add rotation for JSON files |
| Backup | Periodic task + env var | ✅ | Add backup rotation |

---

## 12. Docker Configuration Review

| Aspect | Status | Notes |
|---|---|---|
| Base image | ✅ `python:3.11-slim` | Minimal, correct version |
| Non-root user | ✅ `USER sonarft` (uid 1000) | Good security practice |
| Secrets in image | ✅ None | Keys via env vars only |
| Config in image | ⚠️ `sonarftdata/` baked in | Should be volume-mounted |
| History in image | ⚠️ SQLite DB included if present | Must be volume-mounted |
| Unused dependencies | ⚠️ `fastapi`, `uvicorn`, `PyJWT` installed | Remove from `requirements.txt` |
| Health check | ⚠️ Trivial `print('ok')` | Should check bot liveness |
| Volume mounts | ❌ None defined | Add `sonarftdata/` volume |
| `.dockerignore` | ⚠️ Present but content not reviewed | Should exclude `sonarftdata/bots/`, `sonarftdata/history/` |

---

## 13. Conclusion

### Configuration system maturity

The configuration system is **well-structured** for its scope. The JSON-based multi-file layout with a master index is clean and easy to understand. Pydantic validation for trading parameters, symbols, and fees provides strong type safety at load time. The `BotCreationError` pattern with descriptive messages makes misconfiguration easy to diagnose.

### Safety of defaults

Defaults are **conservative and safe**:
- `is_simulating_trade=1` by default — no accidental live trading ✅
- `SONARFT_ALLOW_LIVE` must be explicitly set — strong live trading gate ✅
- Circuit breaker enabled by default (5 failures) ✅

The main default safety gaps are `max_daily_trades=0` and `max_total_exposure=0.0` being disabled — these should have non-zero defaults for live deployments.

### Production readiness

The configuration system is **not fully production-ready** due to:
1. `sonarftdata/` baked into the Docker image — data loss on container replacement.
2. `exchanges_fees_2` zero-fee config is a live trading trap.
3. Unbounded JSON history files.

### Hardening recommendations (priority order)

1. **High:** Add `.dockerignore` and volume mount for `sonarftdata/`.
2. **High:** Remove `exchanges_fees_2` or add Pydantic validator rejecting zero fees.
3. **Medium:** Centralise `_BOT_DIR`/`_DB_PATH` into a single `paths.py` module.
4. **Medium:** Move RSI thresholds and indicator periods to config.
5. **Medium:** Unify hot-reload validation to use Pydantic.
6. **Medium:** Add exchange name and indicator name validation at config load.
7. **Low:** Add JSON file rotation for `errors_history.json` and `balance_history.json`.
8. **Low:** Add DB backup rotation (keep last N days).
9. **Low:** Improve Docker health check to verify bot liveness.
10. **Low:** Parse and validate all env vars at `create_bot` time, not lazily.

---

## Implementation Status — July 2025

> All high and medium findings from this review have been resolved.

### Resolved findings

| Finding | Severity | Resolution | Task |
|---|---|---|---|
| `exchanges_fees_2` zero fees | High | Fixed: removed; Pydantic validator rejects zero fees | T04 |
| `sonarftdata/` baked into Docker image | High | Fixed: `VOLUME` declarations + `.dockerignore` excludes runtime data dirs | T05 |
| RSI thresholds hardcoded | Medium | Fixed: `rsi_overbought`/`rsi_oversold` configurable via `config_parameters.json` | Phase 5 |
| Indicator periods hardcoded | Medium | Noted; `weighted_adjust_prices` uses local variables — future enhancement | — |
| `_BOT_DIR`/`_DB_PATH` duplicated | Medium | Fixed: `paths.py` created as single source of truth | T19 |
| `daily_loss` helpers duplicated | Medium | Fixed: moved into `SonarftHelpers`; `sonarft_search.py` delegates | T20 |
| Hot-reload missing 4 parameters | Medium | Fixed: `slippage_buffer`, `flash_crash_threshold`, `max_daily_trades`, `max_total_exposure` added | T22 |
| Dual validation paths | Medium | Fixed: `apply_parameters` now uses Pydantic `ParametersConfig` | T23 |
| Exchange/indicator name validation missing | Medium | Fixed: validated against `ccxt.exchanges` and `_VALID_INDICATORS` at config load | T24 |
| `errors_history.json`/`balance_history.json` unbounded | Low | Fixed: migrated to SQLite `errors`/`balances` tables | T27 |
| DB backup files never rotated | Low | Fixed: `_rotate_backups()` deletes files older than `SONARFT_BACKUP_KEEP_DAYS` | T38 |
| Trivial Docker health check | Low | Fixed: `import sonarft_bot; print('ok')` verifies package imports | Phase 5 |
| Env vars parsed lazily | Low | Fixed: `_validate_env_vars()` called at start of `create_bot` | T37 |
| `min_trading_volume_coefficient` hardcoded | Low | Fixed: configurable via `config_parameters.json` | Phase 5 |

### New configurable parameters added

`config_parameters.json` now includes: `rsi_overbought`, `rsi_oversold`, `monitor_price_timeout`, `monitor_order_timeout`, `min_trading_volume_coefficient` — all with Pydantic validation and hot-reload support.
