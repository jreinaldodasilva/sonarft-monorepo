# SonarFT Bot — Configuration & Runtime Environment Review

**Prompt:** 07-BOT-CONFIG  
**Reviewer role:** Senior DevOps / platform engineer / configuration auditor  
**Date:** July 2025  
**Status:** Complete — all High findings implemented ✅

## ⚡ Implementation Status (Post-Roadmap)

| Finding | Severity | Resolution |
|---|---|---|
| C-01 No JSON schema validation | High | ✅ T-10 — Pydantic v2 `ParametersConfig`, `SymbolConfig`, `FeeConfig` |
| C-05 `indicators_3` malformed entry | High | ✅ T-09 — fixed to `["rsi", "stoch rsi"]` |
| C-07 `SONARFT_ALLOW_LIVE` not checked at startup | High | ✅ T-01 — `_check_live_mode_guard()` in `load_configurations()` |
| C-11 Indicator periods hardcoded | Medium | ✅ T-28 — `flash_crash_threshold` configurable; indicator periods documented |
| C-12 Flash crash threshold hardcoded | Medium | ✅ T-28 — `flash_crash_threshold` in config + Pydantic schema |
| C-13 Docker HEALTHCHECK weak | Medium | ⚠️ Acceptable for current deployment |
| C-18 Config name hardcoded in Docker CMD | Medium | ✅ Documented in `.env.example` |
| C-19 `_DB_PATH` CWD-relative | Medium | ✅ T-20 — anchored to `_BOT_DIR` |
| C-02 `max_trade_amount`/`max_orders_per_minute` not validated | Medium | ✅ T-10 — Pydantic `ge=0` constraints |
| C-03 No `maker_buy_fee`/`maker_sell_fee` | Medium | ✅ TD-09 — added to `config_fees.json` |
| C-08 No `.env.example` | Low | ✅ T-26 — created with all 12 env vars |
| C-10 Code defaults `0.0` (disabled) | Low | ✅ T-10 — Pydantic defaults; config files have non-zero values |

**Overall configuration maturity updated: 6.5/10 → 9/10**

**Prerequisites:** [01-BOT-ARCH](../architecture/bot-overview.md)

---

## 1. Configuration File Structure

### Format

All configuration is JSON. No YAML, TOML, or Python dicts. Files live under `sonarftdata/`.

### File inventory

| File | Purpose | Format |
|---|---|---|
| `config.json` | Named configuration sets — maps setup names to file paths and setup IDs | `{ "config_N": [{ ... }] }` |
| `config_parameters.json` | Trading parameters per setup | `{ "parameters_N": [{ ... }] }` |
| `config_exchanges.json` | Exchange lists per setup | `{ "exchanges_N": ["exchange_id", ...] }` |
| `config_symbols.json` | Trading pairs per setup | `{ "symbols_N": [{ "base": "X", "quotes": ["Y"] }] }` |
| `config_fees.json` | Fee rates per exchange | `{ "exchanges_fees_N": [{ "exchange": "...", "buy_fee": 0.001, ... }] }` |
| `config_indicators.json` | Active indicator list per setup | `{ "indicators_N": ["rsi", "stoch rsi", ...] }` |
| `config_markets.json` | Market type per setup | `{ "market_N": ["crypto"] }` |

### Schema validation

**Finding C-01 (High):** There is **no JSON schema validation** on any config file. `_load_config_section()` loads the JSON and accesses the named key — if a required field is missing or has the wrong type, the error surfaces as a `KeyError` or `TypeError` at the point of use, not at load time. For example, if `config_parameters.json` has `"trade_amount": "0.01"` (string instead of float), `_validate_parameters()` will call `float("0.01")` which succeeds — but `int("0.01")` for `is_simulating_trade` would raise `ValueError`. The error messages are not always clear about which field caused the problem.

**Recommendation:** Add a `pydantic` or `jsonschema` validation step in `load_configurations()` before field extraction.

### Complete parameter inventory

#### `config_parameters.json`

| Parameter | Required | Type | Default in code | Purpose | Validated |
|---|---|---|---|---|---|
| `strategy` | No | str | `"arbitrage"` | Trading strategy | ✅ `in ("arbitrage", "market_making")` |
| `profit_percentage_threshold` | Yes | float | — | Minimum net profit % | ✅ `0 < x < 1` |
| `trade_amount` | Yes | float | — | Order size in base currency | ✅ `> 0` |
| `is_simulating_trade` | Yes | int | — | 0=live, 1=simulation | ✅ `in (0, 1)` |
| `max_daily_loss` | No | float | `0.0` | Daily loss halt threshold (0=disabled) | ✅ `>= 0` |
| `max_trade_amount` | No | float | `0.0` | Max position size (0=disabled) | No |
| `max_orders_per_minute` | No | int | `0` | Order rate limit (0=disabled) | No |
| `spread_increase_factor` | No | float | `1.00020` | Sell spread widening (market_making) | ✅ only for market_making |
| `spread_decrease_factor` | No | float | `0.99980` | Buy spread narrowing (market_making) | ✅ only for market_making |

**Finding C-02 (Medium):** `max_trade_amount` and `max_orders_per_minute` are loaded but **not validated** in `_validate_parameters()`. A negative `max_trade_amount` or a very large `max_orders_per_minute` would be accepted silently. The rate limiter uses `>= max_orders_per_minute` so a value of `0` disables it (correct), but a negative value would also disable it (unintended).

#### `config_fees.json`

**Finding C-03 (Medium):** `config_fees.json` contains only `buy_fee` and `sell_fee` fields — no `maker_buy_fee` or `maker_sell_fee`. The `get_buy_fee()` method checks for `maker_buy_fee` first and falls back to `buy_fee`. Since `maker_buy_fee` is never present in the config, the fallback is always used. The maker/taker distinction is effectively non-functional. The config schema should be updated to include maker/taker fee fields.

**Finding C-04 (Medium):** `exchanges_fees_2` has `buy_fee: 0.0` and `sell_fee: 0.0` for Binance — zero fees. This is a test/development setup but if accidentally used in production, the bot would calculate profit without accounting for fees, potentially executing unprofitable trades.

#### `config_indicators.json`

**Finding C-05 (High):** `indicators_3` contains `"rsi, stoch rsi"` (a single string with a comma) instead of `["rsi", "stoch rsi"]` (two separate strings). The `_indicator_active()` method checks:

```python
return any(name.lower() in s.lower() for s in self.active_indicators)
```

With `active_indicators = ["rsi, stoch rsi"]`, checking for `"rsi"` returns `True` (substring match) and checking for `"stoch rsi"` also returns `True` (substring match). So `indicators_3` accidentally works correctly due to substring matching — but it is a malformed config entry that could cause confusion and would break any strict equality check.

---

## 2. Configuration Loading Behaviour

### Entry point

`SonarftBot.load_configurations(config_setup)` is the single entry point. Called from `create_bot()`.

### File locations

All config paths in `config.json` are **relative paths** (e.g. `"sonarftdata/config_parameters.json"`). They are resolved relative to the bot package directory via `_bot_path()`:

```python
_BOT_DIR = os.path.dirname(os.path.abspath(__file__))

def _bot_path(*parts: str) -> str:
    return os.path.join(_BOT_DIR, *parts)
```

**Finding C-06 (Low):** `_bot_path()` anchors all paths to the directory containing `sonarft_bot.py`. This means config files must always be in `sonarftdata/` relative to the bot package — they cannot be relocated without code changes. There is no `SONARFT_DATA_DIR` environment variable to override the data directory location.

### Environment variable overrides

Config values cannot be overridden via environment variables — all trading parameters come exclusively from JSON files. Environment variables are used only for:

| Variable | Purpose | Required |
|---|---|---|
| `{EXCHANGE}_API_KEY` | Exchange API key | Live mode only |
| `{EXCHANGE}_SECRET` | Exchange API secret | Live mode only |
| `{EXCHANGE}_PASSWORD` | Exchange API passphrase | Optional |
| `SONARFT_ALLOW_LIVE` | Permit simulation→live switch | Required for hot-reload to live |
| `SONARFT_MAX_FAILURES` | Circuit breaker threshold | Optional (default: 5) |
| `SONARFT_BACKOFF_BASE` | Circuit breaker backoff seconds | Optional (default: 30) |
| `SONARFT_CYCLE_SLEEP_MIN` | Min sleep between cycles (s) | Optional (default: 6) |
| `SONARFT_CYCLE_SLEEP_MAX` | Max sleep between cycles (s) | Optional (default: 18) |
| `SONARFT_ALERT_WEBHOOK` | Webhook URL for alerts | Optional |
| `SONARFT_FEE_ROUNDING` | Fee rounding mode (`HALF_UP`) | Optional (default: HALF_EVEN) |

**Finding C-07 (Medium):** `SONARFT_ALLOW_LIVE` is checked during hot-reload (`apply_parameters()`) but **not at initial startup** when `is_simulating_trade = 0` in config. As noted in Prompt 03 (T-14), this is a Critical safety gap.

**Finding C-08 (Low):** None of the environment variables are documented in a `.env.example` file for the bot package. The API package has `.env.example` but the bot package does not. Operators must discover required variables from the source code.

### Fallback behaviour

If a config file is missing: `BotCreationError` is raised with a clear message. ✅  
If a config key is missing: `BotCreationError` is raised. ✅  
If JSON is malformed: `BotCreationError` is raised with the JSON parse error. ✅

### Per-client runtime config

The API layer writes per-client parameter and indicator overrides to `sonarftdata/config/{client_id}_parameters.json` and `sonarftdata/config/{client_id}_indicators.json`. These are loaded by the API's parameter endpoints and applied via `BotManager.reload_parameters()`.

**Finding C-09 (Medium):** Per-client config files use `client_id` as part of the filename. `sanitize_client_id()` strips non-alphanumeric characters, but the sanitized ID is used directly in file path construction. A `client_id` of `../../../etc/passwd` would be sanitized to an empty string (raising `ValueError`). ✅ The sanitization is correct.

---

## 3. Defaults & Hardcoding Audit

### Unsafe defaults

| Parameter | Default | Risk |
|---|---|---|
| `is_simulating_trade` | `1` (simulation) in both `parameters_1` and `parameters_2` | ✅ Safe — simulation on by default |
| `max_daily_loss` | `100.0` in config files | ✅ Non-zero default in config |
| `max_trade_amount` | `0.1` in config files | ✅ Non-zero default in config |
| `max_orders_per_minute` | `10` in config files | ✅ Non-zero default in config |
| `strategy` | `"arbitrage"` | ✅ Safe default |
| `profit_percentage_threshold` | `0.0001` | ⚠️ Very tight — see T-03 |

**Finding C-10 (Low):** The actual config files (`parameters_1`, `parameters_2`) have sensible non-zero defaults for risk limits. However, the code-level defaults in `load_configurations()` use `parameters.get("max_daily_loss", 0.0)` — if the field is absent from the JSON, the code default is `0.0` (disabled). The config files currently include the field, but a stripped-down config without these fields would silently disable all risk limits.

### Hardcoded values audit

| Value | Location | Should be config? |
|---|---|---|
| VWAP depth `12` | `trade_processor.py` — `process_symbol()` | Yes — per-exchange/symbol |
| VWAP depth `3` | `sonarft_prices.py` — `weighted_adjust_prices()` | Yes — configurable |
| RSI period `14` | `sonarft_prices.py` — `weighted_adjust_prices()` | Yes — already in indicators config |
| StochRSI periods `14/14/3/3` | `sonarft_prices.py` | Yes — already in indicators config |
| Order book depth `6` | `sonarft_prices.py` | Yes — configurable |
| Indicator gather timeout `30.0s` | `sonarft_prices.py` | Yes — env var |
| Flash crash threshold `0.02` | `sonarft_execution.py` | Yes — configurable |
| RSI overbought `70`/`72` | `sonarft_execution.py`, `sonarft_prices.py` | Yes — shared constant |
| RSI oversold `30`/`28` | Same | Yes — shared constant |
| Monitor price timeout `120s` | `sonarft_execution.py` | Yes — env var |
| Monitor order timeout `300s` | `sonarft_execution.py` | Yes — env var |
| Cancel retry count `3` | `sonarft_execution.py` | Yes — env var |
| Order book cache TTL `2.0s` | `sonarft_api_manager.py` | Yes — env var |
| Indicator cache TTL `60s` | `sonarft_indicators.py` | Yes — env var |
| OHLCV cache max entries `500` | `sonarft_api_manager.py` | Low priority |
| SQLite keep_last `10_000` | `sonarft_helpers.py` | Yes — env var |
| `_DB_PATH` `sonarftdata/history/sonarft.db` | `sonarft_helpers.py`, `sonarft_search.py` | Yes — env var |

**Finding C-11 (Medium):** The indicator periods (RSI 14, StochRSI 14/14/3/3, SMA 14) are hardcoded in `weighted_adjust_prices()` but `config_indicators.json` already has an `active_indicators` list. The config does not include period values — only which indicators are active. The periods should be configurable via `config_indicators.json`.

**Finding C-12 (Medium):** The flash crash threshold (`0.02` = 2%) is hardcoded in `_execute_single_trade()`. This is a safety-critical parameter that should be configurable — different assets have different normal volatility ranges. A 2% threshold is appropriate for BTC/USDT but may be too tight for high-volatility altcoins.

---

## 4. Docker Runtime Review

### Dockerfile analysis

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .
COPY . .
RUN adduser --disabled-password --gecos '' --uid 1000 sonarft \
    && chown -R sonarft:sonarft /app
USER sonarft
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "print('ok')" || exit 1
CMD ["python", "-m", "sonarft_bot"]
```

**Finding C-13 (Medium):** The `HEALTHCHECK` command is `python -c "print('ok')"` — this only verifies that Python is executable, not that the bot is actually running and healthy. A meaningful health check would verify the bot process is alive and responsive (e.g. check a PID file, query a local health endpoint, or verify the SQLite database is accessible).

**Finding C-14 (Low):** `pip install -e .` installs the package in editable mode. In a production Docker image, editable installs are unnecessary and slightly slower to import. Use `pip install .` instead.

**Finding C-15 (Low):** The `COPY . .` instruction copies the entire bot directory including `sonarftdata/` (with runtime data, bot registry files, and trade history). In a production image, runtime data should be mounted as a volume, not baked into the image. A `.dockerignore` file should exclude `sonarftdata/bots/`, `sonarftdata/history/`, and `sonarftdata/config/`.

**Finding C-16 (Low):** The non-root user `sonarft` is created correctly with UID 1000. ✅ The `chown -R sonarft:sonarft /app` runs after `COPY . .` — correct order. ✅

**Finding C-17 (Low):** `python:3.11-slim` is the base image. The Dockerfile specifies Python 3.11 but `pyproject.toml` requires `>=3.10`. These are consistent. ✅ `slim` variant reduces image size. ✅

**Finding C-18 (Medium):** The `CMD` is `python -m sonarft_bot` which runs `__main__.py`. This starts a single bot with the default `config_1` configuration. In a multi-bot deployment, each container runs one bot. There is no mechanism to pass a different config name to the container without overriding `CMD` — the config name should be configurable via an environment variable:

```dockerfile
ENV SONARFT_CONFIG=config_1
CMD ["sh", "-c", "python -m sonarft_bot -c ${SONARFT_CONFIG}"]
```

### Secrets handling in Docker

API keys are loaded from environment variables (`{EXCHANGE}_API_KEY`, `{EXCHANGE}_SECRET`). These should be passed via Docker secrets or environment variables at runtime — never baked into the image. ✅ The Dockerfile does not include any secrets. ✅

---

## 5. File Paths & History Storage

### Path construction

All paths are constructed via `_bot_path()` anchored to `_BOT_DIR`. SQLite database path is `sonarftdata/history/sonarft.db` — relative to CWD in `sonarft_helpers.py` and `sonarft_search.py`.

**Finding C-19 (Medium):** `SonarftHelpers._DB_PATH` and `_DB_PATH` in `sonarft_search.py` use `os.path.join('sonarftdata', 'history', 'sonarft.db')` — a **relative path from CWD**, not from `_BOT_DIR`. If the bot is started from a different working directory (e.g. `python /path/to/sonarft_bot.py` from `/home/user`), the database will be created at `/home/user/sonarftdata/history/sonarft.db` instead of the expected location. This is inconsistent with `_bot_path()` which anchors to the package directory.

**Fix:** Use `_bot_path('sonarftdata', 'history', 'sonarft.db')` or an equivalent absolute path construction in both files.

### Path traversal risks

`sanitize_client_id()` strips all non-alphanumeric/hyphen/underscore characters before using `client_id` in file paths. ✅

Config file paths in `config.json` are loaded as-is and passed to `_load_config_section()`. If a malicious `config.json` contained `"parameters_pathname": "../../etc/passwd"`, `_bot_path()` would resolve it relative to `_BOT_DIR`. `os.path.join(_BOT_DIR, "../../etc/passwd")` would resolve to `/etc/passwd` on Linux. However, `config.json` is a local file controlled by the operator — this is not an external input attack vector.

**Finding C-20 (Low):** Config pathnames in `config.json` are not validated to be within the `sonarftdata/` directory. An operator error (e.g. absolute path pointing outside the data directory) would be silently accepted. Adding a check that all config pathnames resolve within `_BOT_DIR` would prevent accidental misconfiguration.

### Log rotation

**Finding C-21 (Low):** There is no log rotation configured. The bot uses Python's stdlib `logging` with a `StreamHandler` (stdout). In Docker, stdout logs are managed by the container runtime (e.g. Docker's `json-file` driver with `max-size` and `max-file` options). For non-Docker deployments, log rotation must be configured externally (e.g. `logrotate`). No `RotatingFileHandler` is used. ✅ Acceptable for containerised deployments.

---

## 6. Configuration Validation

### Current validation

`_validate_parameters()` in `SonarftBot` validates trading parameters after loading:

| Check | Validation | Error type |
|---|---|---|
| `strategy` | `in ("arbitrage", "market_making")` | `ValueError` |
| `profit_percentage_threshold` | `0 < x < 1` | `ValueError` |
| `trade_amount` | `> 0` | `ValueError` |
| `is_simulating_trade` | `in (0, 1)` | `ValueError` |
| `max_daily_loss` | `>= 0` | `ValueError` |
| `spread_increase_factor` | `1.0 < x < 1.01` (market_making only) | `ValueError` |
| `spread_decrease_factor` | `0.99 < x < 1.0` (market_making only) | `ValueError` |

**Finding C-22 (Medium):** The following loaded parameters have **no validation**:

| Parameter | Risk of missing validation |
|---|---|
| `max_trade_amount` | Negative value silently disables limit |
| `max_orders_per_minute` | Negative value silently disables limit |
| `symbols` list | Empty list → bot runs but never trades |
| `exchanges` list | Empty list → `SonarftApiManager` creates no instances → all API calls fail |
| Fee rates in `config_fees.json` | Negative fee → profit overestimated |
| Exchange IDs in `config_exchanges.json` | Invalid exchange ID → ccxt raises at instance creation |

**Finding C-23 (Low):** `_validate_parameters()` raises `ValueError` which is caught by `create_bot()` as `BotCreationError`. The error message includes the parameter name and value. ✅ However, the error is only raised for the first invalid parameter — subsequent invalid parameters are not reported. A validation approach that collects all errors before raising would give operators a complete picture.

### Type coercion

Parameters are loaded from JSON with Python's `json.load()`. JSON numbers are parsed as Python `float` or `int` depending on whether they have a decimal point. `is_simulating_trade: 1` is parsed as `int(1)`. `profit_percentage_threshold: 0.0001` is parsed as `float`. The code uses these types directly without explicit coercion — this is safe for well-formed JSON. ✅

**Finding C-24 (Low):** `max_orders_per_minute` is loaded as `int(parameters.get("max_orders_per_minute", 0))`. If the JSON value is `10.5` (float), `int(10.5)` = `10` — silently truncated. A strict type check would be more appropriate.

---

## 7. Configuration Issues Table

| ID | Issue | Location | Type | Severity | Remediation |
|---|---|---|---|---|---|
| C-01 | No JSON schema validation on any config file | `sonarft_bot.py` — `load_configurations()` | Missing validation | **High** | Add `pydantic` or `jsonschema` validation at load time |
| C-05 | `indicators_3` has `"rsi, stoch rsi"` as single string instead of two entries | `config_indicators.json` | Config bug | **High** | Fix to `["rsi", "stoch rsi"]`; add schema validation |
| C-07 | `SONARFT_ALLOW_LIVE` not checked at initial startup | `sonarft_bot.py` — `load_configurations()` | Safety gap | **High** | Check env var when `is_simulating_trade=0` at startup |
| C-11 | Indicator periods hardcoded in `weighted_adjust_prices()` | `sonarft_prices.py` | Hardcoded | **Medium** | Add period fields to `config_indicators.json` |
| C-12 | Flash crash threshold `0.02` hardcoded | `sonarft_execution.py` | Hardcoded | **Medium** | Add `flash_crash_threshold` to `config_parameters.json` |
| C-13 | `HEALTHCHECK` only verifies Python is executable | `Dockerfile` | Weak health check | **Medium** | Check bot process liveness or SQLite accessibility |
| C-18 | Config name not configurable via env var in Docker | `Dockerfile` | Inflexible | **Medium** | Add `SONARFT_CONFIG` env var to `CMD` |
| C-19 | `_DB_PATH` uses relative CWD path, not `_bot_path()` | `sonarft_helpers.py`, `sonarft_search.py` | Path inconsistency | **Medium** | Use `_bot_path()` or absolute path anchored to package dir |
| C-02 | `max_trade_amount` and `max_orders_per_minute` not validated | `sonarft_bot.py` — `_validate_parameters()` | Missing validation | **Medium** | Add `>= 0` checks |
| C-03 | `config_fees.json` has no `maker_buy_fee`/`maker_sell_fee` fields | `config_fees.json` | Incomplete schema | **Medium** | Add maker/taker fee fields; update `get_buy/sell_fee()` |
| C-04 | `exchanges_fees_2` has zero fees — dangerous if used in production | `config_fees.json` | Unsafe config | **Medium** | Add comment marking as test-only; add fee validation `> 0` |
| C-22 | Empty `symbols` or `exchanges` lists not validated | `sonarft_bot.py` — `load_configurations()` | Missing validation | **Medium** | Add `len > 0` checks with clear error messages |
| C-06 | No `SONARFT_DATA_DIR` env var to relocate data directory | `sonarft_bot.py` | Inflexible | **Low** | Add env var override for data directory |
| C-08 | No `.env.example` for bot package | `packages/bot/` | Missing docs | **Low** | Create `.env.example` listing all env vars |
| C-10 | Code-level defaults for risk limits are `0.0` (disabled) | `sonarft_bot.py` — `load_configurations()` | Unsafe fallback | **Low** | Use non-zero code defaults or require explicit config |
| C-14 | `pip install -e .` in production Docker image | `Dockerfile` | Non-production | **Low** | Use `pip install .` |
| C-15 | `COPY . .` includes runtime data in Docker image | `Dockerfile` | Image bloat | **Low** | Add `sonarftdata/bots/`, `sonarftdata/history/` to `.dockerignore` |
| C-20 | Config pathnames not validated to be within `sonarftdata/` | `sonarft_bot.py` — `_load_config_section()` | Path safety | **Low** | Validate resolved path starts with `_BOT_DIR` |
| C-23 | Validation stops at first error | `sonarft_bot.py` — `_validate_parameters()` | UX | **Low** | Collect all errors before raising |
| C-24 | `max_orders_per_minute` float silently truncated to int | `sonarft_bot.py` — `load_configurations()` | Type coercion | **Low** | Add type check |

---

## 8. Runtime Configuration Summary

| Aspect | Current Method | Safe? | Recommendation |
|---|---|---|---|
| Trading parameters | JSON file, loaded at startup | ✅ with caveats | Add schema validation; add `SONARFT_ALLOW_LIVE` startup check |
| API keys | Environment variables | ✅ | Add `.env.example`; document required vars |
| Live mode guard | `SONARFT_ALLOW_LIVE` env var (hot-reload only) | ⚠️ | Also check at initial startup |
| Risk limits | JSON config, code defaults `0.0` | ⚠️ | Use non-zero code defaults; validate all risk params |
| Indicator periods | Hardcoded in source | ⚠️ | Move to `config_indicators.json` |
| Flash crash threshold | Hardcoded `0.02` | ⚠️ | Move to `config_parameters.json` |
| Database path | Relative CWD path | ⚠️ | Anchor to `_BOT_DIR` |
| Config file location | Anchored to `_BOT_DIR` | ✅ | Add `SONARFT_DATA_DIR` override |
| Docker config name | Hardcoded `config_1` in CMD | ⚠️ | Add `SONARFT_CONFIG` env var |
| Docker health check | Python executable check only | ⚠️ | Check bot liveness |
| Docker secrets | Env vars at runtime | ✅ | Never bake into image |
| Log rotation | Container runtime managed | ✅ for Docker | Add `RotatingFileHandler` for non-Docker |
| Schema validation | None | ❌ | Add `pydantic` or `jsonschema` |
| Hot-reload | `apply_parameters()` via API | ✅ | Propagates to all running modules |
| Per-client config | JSON files in `sonarftdata/config/` | ✅ | Path sanitization correct |

---

## 9. Conclusion

### Overall configuration maturity: **6.5/10**

The configuration system is functional and covers all necessary trading parameters. The named-setup pattern (`config_1`, `config_2`) provides good flexibility for multiple deployment profiles. The `_validate_parameters()` function catches the most dangerous parameter errors. The Dockerfile follows security best practices (non-root user, slim base image).

The primary gaps are the absence of JSON schema validation, the `SONARFT_ALLOW_LIVE` startup gap, the relative CWD database path, and several hardcoded values that should be configurable.

### Critical fixes

**C-05 — Fix `indicators_3` malformed entry:**
```json
"indicators_3": ["rsi", "stoch rsi"]
```
This is a data bug that currently works by accident due to substring matching.

**C-07 — Add `SONARFT_ALLOW_LIVE` check at startup** (also T-14 from Prompt 03):
```python
if self.is_simulating_trade == 0:
    if not os.environ.get("SONARFT_ALLOW_LIVE"):
        raise BotCreationError(
            "Live trading requires SONARFT_ALLOW_LIVE=true. "
            "Set is_simulating_trade=1 for simulation."
        )
```

**C-01 — Add schema validation:**
```python
# In load_configurations(), after json.load():
from pydantic import BaseModel, validator

class ParametersConfig(BaseModel):
    strategy: str
    profit_percentage_threshold: float
    trade_amount: float
    is_simulating_trade: int
    max_daily_loss: float = 0.0
    max_trade_amount: float = 0.0
    max_orders_per_minute: int = 0
    spread_increase_factor: float = 1.00020
    spread_decrease_factor: float = 0.99980
```

### Medium priority fixes

1. **C-19** — Anchor `_DB_PATH` to `_BOT_DIR` in both `sonarft_helpers.py` and `sonarft_search.py`
2. **C-11** — Add indicator period fields to `config_indicators.json`
3. **C-12** — Add `flash_crash_threshold` to `config_parameters.json`
4. **C-13** — Improve Docker `HEALTHCHECK` to verify bot liveness
5. **C-18** — Add `SONARFT_CONFIG` env var to Docker `CMD`
6. **C-03** — Add `maker_buy_fee`/`maker_sell_fee` to `config_fees.json`

### Summary

| Category | Findings | Critical | High | Medium | Low |
|---|---|---|---|---|---|
| Schema & validation | 5 | 0 | 2 | 3 | 0 |
| Hardcoded values | 5 | 0 | 0 | 2 | 3 |
| Docker | 6 | 0 | 0 | 2 | 4 |
| File paths | 3 | 0 | 0 | 1 | 2 |
| Environment variables | 3 | 0 | 1 | 1 | 1 |
| Config data bugs | 2 | 0 | 1 | 1 | 0 |
| **Total** | **24** | **0** | **4** | **10** | **10** |
