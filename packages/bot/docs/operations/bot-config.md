# SonarFT Bot — Configuration & Runtime Environment Review

**Prompt:** 07-BOT-CONFIG  
**Reviewer:** Senior DevOps / Configuration Safety Auditor  
**Date:** July 2025  
**Codebase:** `packages/bot` — configuration system and runtime environment

---

## 1. Configuration File Structure

### 1.1 Format and Layout

All configuration is JSON, stored under `sonarftdata/`:

| File | Purpose | Schema Validation? |
|---|---|---|
| `config.json` | Named config sets mapping to other files | ❌ No |
| `config_parameters.json` | Trading parameters per setup | ✅ Partial (`_validate_parameters()`) |
| `config_exchanges.json` | Exchange list per setup | ❌ No |
| `config_symbols.json` | Trading pairs per setup | ❌ No |
| `config_fees.json` | Fee rates per exchange | ❌ No |
| `config_indicators.json` | Active indicator list per setup | ❌ No |
| `config_markets.json` | Market type (crypto, forex) | ❌ No |

### 1.2 Configuration Parameter Inventory

| Parameter | File | Required | Type | Default | Validation | Purpose |
|---|---|---|---|---|---|---|
| `profit_percentage_threshold` | `config_parameters.json` | ✅ | float | 0.003 | `(0, 1)` range check | Minimum profit % to execute |
| `trade_amount` | `config_parameters.json` | ✅ | float | 1 | `> 0` check | Base currency units per trade |
| `is_simulating_trade` | `config_parameters.json` | ✅ | int | 1 | `in (0, 1)` check | Simulation mode flag |
| `max_daily_loss` | `config_parameters.json` | ❌ | float | 100.0 | `>= 0` check | Daily loss halt threshold |
| `max_trade_amount` | `config_parameters.json` | ❌ | float | 0.0 | None (0=disabled) | Max single trade size |
| `max_orders_per_minute` | `config_parameters.json` | ❌ | int | 0 | None (0=disabled) | Order rate limit |
| `spread_increase_factor` | `config_parameters.json` | ❌ | float | 1.00072 | `(1.0, 1.01)` range | Spread widening multiplier |
| `spread_decrease_factor` | `config_parameters.json` | ❌ | float | 0.99936 | `(0.99, 1.0)` range | Spread narrowing multiplier |
| `exchanges` | `config_exchanges.json` | ✅ | list[str] | `["okx","binance"]` | ❌ None | Exchange IDs |
| `symbols` | `config_symbols.json` | ✅ | list[dict] | BTC/USDT, ETH/USDT | ❌ None | Trading pairs |
| `buy_fee` / `sell_fee` | `config_fees.json` | ✅ | float | Per exchange | ❌ None | Fee rates |
| `indicators` | `config_indicators.json` | ✅ | list[str] | `["rsi"]` | ❌ None | Active indicators |
| `market` | `config_markets.json` | ✅ | list[str] | `["crypto"]` | ❌ None | Market type |

### 1.3 Config Set Structure

`config.json` maps named sets to file paths and setup indices:

```json
{
    "config_1": [{
        "markets_pathname": "sonarftdata/config_markets.json",
        "markets_setup": 1,
        "exchanges_pathname": "sonarftdata/config_exchanges.json",
        "exchanges_setup": 1,
        ...
    }]
}
```

Each config set references specific setups within each file (e.g., `parameters_1`, `exchanges_1`). This allows multiple configurations to coexist.

---

## 2. Configuration Loading Behavior

### 2.1 Loading Entry Point

`SonarftBot.load_configurations(config_setup="config_1")`:

```python
def load_configurations(self, config_setup="config_1"):
    config = self._load_config_section("sonarftdata/config.json", config_setup)[0]
    self.market = self._load_config_section(config["markets_pathname"], f"market_{config['markets_setup']}")
    parameters = self._load_config_section(config["parameters_pathname"], f"parameters_{config['parameters_setup']}")[0]
    self.symbols = self._load_config_section(config["symbols_pathname"], f"symbols_{config['symbols_setup']}")
    self.exchanges = self._load_config_section(config["exchanges_pathname"], f"exchanges_{config['exchanges_setup']}")
    self.exchanges_fees = self._load_config_section(config["fees_pathname"], f"exchanges_fees_{config['fees_setup']}")
    self.active_indicators = self._load_config_section(config["indicators_pathname"], f"indicators_{config['indicators_setup']}")
```

### 2.2 Loading Assessment

| Aspect | Assessment | Severity |
|---|---|---|
| File paths from config | ⚠️ `config.json` specifies file paths — user-controlled path traversal possible | **Medium** |
| Missing file | ❌ `FileNotFoundError` — unhandled, crashes bot | **Medium** |
| Missing key | ❌ `KeyError` — unhandled, crashes bot | **Medium** |
| Malformed JSON | ❌ `json.JSONDecodeError` — unhandled, crashes bot | **Medium** |
| Config setup selection | ✅ Via CLI `-c config_1` or default | — |
| Environment variable overrides | ❌ Not supported — all config from JSON files | **Low** |
| Merge behavior | ❌ No merging — each config set is independent | — |
| Blocking I/O | ⚠️ Sync `open()`/`json.load()` in async context (confirmed Prompt 02) | **Medium** |

### 2.3 Fallback Behavior

There are no fallbacks. If any config file is missing or malformed, the bot crashes with an unhandled exception during `create_bot()`. The `BotCreationError` catch in `create_bot()` only catches that specific exception type — `FileNotFoundError`, `KeyError`, and `json.JSONDecodeError` propagate uncaught.

---

## 3. Per-Bot & Per-Client Configuration

### 3.1 Per-Client Runtime Config

The API layer (outside the bot package) stores per-client overrides in `sonarftdata/config/`:

```
sonarftdata/config/
├── {client_id}_parameters.json
├── {client_id}_indicators.json
├── parameters.json          (default)
└── indicators.json           (default)
```

### 3.2 Hot-Reload Mechanism

`BotManager.reload_parameters()` → `SonarftBot.apply_parameters()`:

```python
def apply_parameters(self, parameters: dict) -> None:
    if 'profit_percentage_threshold' in parameters:
        self.profit_percentage_threshold = float(parameters['profit_percentage_threshold'])
    if 'trade_amount' in parameters:
        self.trade_amount = float(parameters['trade_amount'])
    if 'is_simulating_trade' in parameters:
        self.is_simulating_trade = int(parameters['is_simulating_trade'])
    # ... propagates to live modules
```

### 3.3 Isolation Assessment

| Aspect | Assessment | Severity |
|---|---|---|
| Each bot has its own `SonarftBot` instance | ✅ Full isolation | — |
| Each bot has its own module instances | ✅ Wired in `InitializeModules()` | — |
| Bots share `SonarftApiManager` exchange instances | ⚠️ No — each bot creates its own. Multiple bots = multiple exchange connections. | **Low** |
| Per-client config stored separately | ✅ `{client_id}_parameters.json` | — |
| Hot-reload applies to all bots of a client | ✅ `reload_parameters()` iterates `get_botids(client_id)` | — |
| **Hot-reload has no validation** | ⚠️ `apply_parameters()` does not call `_validate_parameters()` | **Medium** |
| **Hot-reload can switch sim→live** | ⚠️ `is_simulating_trade` can be changed at runtime (confirmed Prompt 03, F4) | **Medium** |

---

## 4. Environment Variable Usage

### 4.1 Environment Variables

| Variable | Required | Purpose | Default | Security |
|---|---|---|---|---|
| `{EXCHANGE}_API_KEY` | ⚠️ For live trading | Exchange API key | None (warning logged) | ✅ Not logged |
| `{EXCHANGE}_SECRET` | ⚠️ For live trading | Exchange secret key | None (warning logged) | ✅ Not logged |
| `{EXCHANGE}_PASSWORD` | ❌ | Exchange password (some exchanges) | `""` | ✅ Not logged |
| `SONARFT_ALERT_WEBHOOK` | ❌ | Webhook URL for alerts | None (falls back to logger) | ✅ Not logged |

### 4.2 API Key Loading

```python
def _load_api_keys(self):
    for exchange_id in self.exchanges:
        prefix = exchange_id.upper()
        api_key = os.environ.get(f"{prefix}_API_KEY")
        secret = os.environ.get(f"{prefix}_SECRET")
        password = os.environ.get(f"{prefix}_PASSWORD", "")
        if api_key and secret:
            self.api_manager.setAPIKeys(exchange_id, api_key, secret, password)
```

### 4.3 Security Assessment

| Aspect | Assessment | Severity |
|---|---|---|
| Keys from environment variables | ✅ Not in config files or code | — |
| Keys not logged | ✅ Only exchange ID logged, not key values | — |
| Missing keys warning | ✅ Warns if no keys found + sim mode off | — |
| Keys in `.env` file | ✅ `.env` is in `.gitignore` | — |
| **Keys passed to ccxt in memory** | ✅ `exchange.apiKey = api_key` — not persisted | — |
| **No key rotation mechanism** | ⚠️ Keys are loaded once at startup — requires bot restart to rotate | **Low** |


---

## 5. Defaults & Hardcoding Audit

### 5.1 Hardcoded Values

| Value | Location | Should Be Config? | Severity |
|---|---|---|---|
| Circuit breaker: 5 failures | `sonarft_bot.py:98` | ⚠️ Yes — different strategies may need different thresholds | **Low** |
| Backoff base: 30 seconds | `sonarft_bot.py:99` | ⚠️ Yes | **Low** |
| Sleep between cycles: 6-18s random | `sonarft_bot.py:127` | ⚠️ Yes — affects trading frequency | **Low** |
| `monitor_price` timeout: 120s | `sonarft_execution.py:291` | ⚠️ Yes | **Low** |
| `monitor_order` timeout: 300s | `sonarft_execution.py:343` | ⚠️ Yes | **Low** |
| `monitor_price` poll interval: 3s | `sonarft_execution.py:303` | ⚠️ Yes | **Low** |
| `monitor_order` poll interval: 1s | `sonarft_execution.py:360` | ⚠️ Yes | **Low** |
| `check_balance` sleep: 1s | `sonarft_execution.py:393` | ⚠️ Yes (or remove) | **Low** |
| Indicator cache TTL: 60s | `sonarft_indicators.py:9` | ⚠️ Yes | **Low** |
| Order book cache TTL: 2s | `sonarft_api_manager.py:213` | ⚠️ Yes | **Low** |
| OHLCV cache max: 500 entries | `sonarft_api_manager.py:244` | ⚠️ Yes | **Low** |
| Indicator cache max: 500 entries | `sonarft_indicators.py:33` | ⚠️ Yes | **Low** |
| RSI period: 14 | `sonarft_prices.py:38` | ✅ Standard default | — |
| MACD periods: 12/26/9 | `sonarft_indicators.py:219` | ✅ Standard default | — |
| Order book depth: 6 / 3 | `sonarft_prices.py:42` / `sonarft_prices.py:115` | ⚠️ Yes | **Low** |
| VWAP depth: 12 | `sonarft_search.py:140` (`weight=12`) | ⚠️ Yes | **Low** |
| `EXCHANGE_RULES` dict | `sonarft_math.py:19-42` | ⚠️ Partially — dynamic precision preferred | **Low** |
| Liquidity depth: 50 | `sonarft_search.py:39` | ⚠️ Yes | **Low** |
| Support/resistance lookback: 3h | `sonarft_prices.py:79-80` | ⚠️ Yes | **Low** |
| Bot ID range: 10001-99999 | `sonarft_bot.py:248` | Should use UUID | **Low** |

### 5.2 Unsafe Defaults Assessment

| Default | Value | Risk | Assessment |
|---|---|---|---|
| `is_simulating_trade` | `1` (ON) | ✅ Safe — simulation by default | — |
| `profit_percentage_threshold` | `0.003` (0.3%) | ✅ Conservative — requires meaningful profit | — |
| `trade_amount` | `1` | ⚠️ 1 BTC = ~$30,000 — could be expensive if sim mode accidentally off | **Medium** |
| `max_daily_loss` | `100.0` | ✅ Reasonable default | — |
| `max_trade_amount` | `0.0` (disabled) | ⚠️ No position size limit by default | **Medium** |
| `max_orders_per_minute` | `0` (disabled) | ⚠️ No rate limit by default | **Low** |

---

## 6. Docker Runtime Assumptions

### 6.1 Dockerfile Review

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .
COPY . .
CMD ["python", "-m", "sonarft_bot"]
```

| Aspect | Assessment | Severity |
|---|---|---|
| Base image | ✅ `python:3.11-slim` — minimal, official | — |
| Working directory | ✅ `/app` — standard | — |
| Dependency install | ✅ Separate layer for caching | — |
| `pip install -e .` | ✅ Editable install from `pyproject.toml` | — |
| **Runs as root** | ⚠️ No `USER` directive — container runs as root | **Medium** |
| **No health check** | ⚠️ No `HEALTHCHECK` directive | **Low** |
| **No `.dockerignore`** | ⚠️ Copies everything including `.git`, `tests/`, `docs/` | **Low** |
| **`sonarftdata/` copied into image** | ⚠️ Config files baked into image — should be mounted as volume | **Medium** |
| **No multi-stage build** | ⚠️ Build tools remain in final image | **Low** |
| Entrypoint | `python -m sonarft_bot` — ⚠️ This runs `sonarft_bot.py` as `__main__`, but there's no `if __name__ == "__main__"` block in `sonarft_bot.py` | **Medium** |

### 6.2 Docker Compose

⚠️ Not Found in `packages/bot/` — the `docker-compose.yml` is at the monorepo root (`infra/docker-compose.yml`). The bot README references a `docker-compose.yml` with Traefik, but this appears to be for the legacy standalone deployment.

### 6.3 Docker Recommendations

1. Add `USER nonroot` after creating a non-root user
2. Add `.dockerignore` to exclude `tests/`, `docs/`, `.git/`, `*.md`
3. Mount `sonarftdata/` as a volume instead of baking into image
4. Add `HEALTHCHECK` directive
5. Add `__main__.py` or `if __name__ == "__main__"` block for the entrypoint

---

## 7. File Paths & History Storage

### 7.1 Path Inventory

| Path | Purpose | Relative To | Created By |
|---|---|---|---|
| `sonarftdata/config.json` | Main config | CWD | Manual |
| `sonarftdata/config_*.json` | Sub-configs | CWD | Manual |
| `sonarftdata/config/{client_id}_parameters.json` | Per-client params | CWD | API layer |
| `sonarftdata/config/{client_id}_indicators.json` | Per-client indicators | CWD | API layer |
| `sonarftdata/bots/{botid}.json` | Bot registry | CWD | `create_bot()` |
| `sonarftdata/history/sonarft.db` | SQLite trade/order history | CWD | `SonarftHelpers._init_db()` |
| `sonarftdata/errors_history.json` | Error log | CWD | `save_error()` |
| `sonarftdata/balance_history.json` | Balance log | CWD | `save_balance_data()` |

### 7.2 Path Safety Assessment

| Aspect | Assessment | Severity |
|---|---|---|
| All paths relative to CWD | ⚠️ Depends on working directory being correct | **Low** |
| `os.path.join` used for construction | ✅ Safe path joining | — |
| `os.makedirs(exist_ok=True)` for DB dir | ✅ Creates directory if missing | — |
| **`sonarftdata/bots/` directory assumed to exist** | ⚠️ `create_bot()` writes to `sonarftdata/bots/{botid}.json` without ensuring directory exists | **Medium** |
| SQLite DB path | ✅ `_init_db()` creates directory and tables | — |
| JSON history files | ✅ `_append_json()` creates file if missing | — |

### 7.3 Storage Concerns

| Concern | Assessment | Severity |
|---|---|---|
| SQLite for trade history | ✅ Good — O(1) writes, indexed queries | — |
| No log rotation | ⚠️ `errors_history.json` and `balance_history.json` grow unbounded | **Low** |
| No DB size limit | ⚠️ SQLite DB grows unbounded with trade history | **Low** |
| No backup mechanism | ⚠️ No automated backup of trade history | **Low** |

---

## 8. Path Safety & Traversal Risks

### 8.1 User-Controlled Paths

| Path Source | User-Controlled? | Traversal Risk |
|---|---|---|
| Config file paths in `config.json` | ✅ Yes — `markets_pathname`, `parameters_pathname`, etc. | ⚠️ **Medium** |
| `client_id` in per-client config | ✅ Yes — from API request | ⚠️ **Medium** |
| `botid` in bot registry | ❌ No — generated by `random.randint` | **None** |
| `exchange_id` in API keys | ✅ Yes — from config file | **Low** |

### 8.2 Path Traversal Analysis

**Config file paths:**
```json
{
    "parameters_pathname": "sonarftdata/config_parameters.json"
}
```

If an attacker modifies `config.json` to set `parameters_pathname: "../../../etc/passwd"`, the bot would attempt to read that file. However:
1. `config.json` is a local file — requires filesystem access to modify
2. The file is parsed as JSON — `/etc/passwd` is not valid JSON → `json.JSONDecodeError`
3. Even if valid JSON, the key lookup (`parameters_1`) would fail → `KeyError`

**Risk:** Low — requires local filesystem access, and the JSON parsing provides implicit protection.

**Client ID paths:**
```python
file_name = os.path.join('sonarftdata', 'config', f"{client_id}_parameters.json")
```

If `client_id` contains `../`, the path could escape the `sonarftdata/config/` directory. For example:
- `client_id = "../../etc/passwd"` → `sonarftdata/config/../../etc/passwd_parameters.json`

**Evidence:** The file `[object Object]_parameters.json` in `sonarftdata/config/` confirms that unsanitized input reaches the filesystem — a JavaScript object was stringified as `[object Object]` and used as a filename.

**Risk:** **Medium** — `client_id` comes from the API layer and is not sanitized before use in file paths.

### 8.3 Recommendations

1. **Sanitize `client_id`** before using in file paths:
   ```python
   import re
   safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', client_id)
   ```

2. **Validate config file paths** are within `sonarftdata/`:
   ```python
   resolved = os.path.realpath(pathname)
   if not resolved.startswith(os.path.realpath('sonarftdata')):
       raise ValueError(f"Config path escapes sonarftdata: {pathname}")
   ```


---

## 9. Configuration Validation

### 9.1 Validation Coverage

| Config Area | Validated? | Method | Assessment |
|---|---|---|---|
| Trading parameters | ✅ Partial | `_validate_parameters()` | 6 of 8 params validated |
| Exchange list | ❌ No | — | No check that exchanges are valid ccxt IDs |
| Symbol list | ❌ No | — | No check that symbols exist on configured exchanges |
| Fee rates | ❌ No | — | No check that fees are non-negative |
| Indicator list | ❌ No | — | No check that indicator names are valid |
| Market type | ❌ No | — | No check that market type is supported |
| Config file paths | ❌ No | — | No check that paths exist before loading |
| Config set name | ❌ No | — | `KeyError` if set doesn't exist |

### 9.2 `_validate_parameters()` Coverage

```python
def _validate_parameters(self):
    if not (0 < self.profit_percentage_threshold < 1):
        raise ValueError(...)
    if self.trade_amount <= 0:
        raise ValueError(...)
    if self.is_simulating_trade not in (0, 1):
        raise ValueError(...)
    if self.max_daily_loss < 0:
        raise ValueError(...)
    if not (1.0 < self.spread_increase_factor < 1.01):
        raise ValueError(...)
    if not (0.99 < self.spread_decrease_factor < 1.0):
        raise ValueError(...)
```

| Parameter | Validated | Range | Assessment |
|---|---|---|---|
| `profit_percentage_threshold` | ✅ | `(0, 1)` | ✅ Correct |
| `trade_amount` | ✅ | `> 0` | ✅ Correct |
| `is_simulating_trade` | ✅ | `in (0, 1)` | ✅ Correct |
| `max_daily_loss` | ✅ | `>= 0` | ✅ Correct |
| `spread_increase_factor` | ✅ | `(1.0, 1.01)` | ✅ Correct |
| `spread_decrease_factor` | ✅ | `(0.99, 1.0)` | ✅ Correct |
| `max_trade_amount` | ❌ | — | ⚠️ Not validated — negative value accepted |
| `max_orders_per_minute` | ❌ | — | ⚠️ Not validated — negative value accepted |

### 9.3 Hot-Reload Validation Gap

`apply_parameters()` does NOT call `_validate_parameters()`. A hot-reload could set:
- `profit_percentage_threshold = -1` (negative threshold → all trades execute)
- `trade_amount = -5` (negative amount → exchange rejects, but confusing)
- `is_simulating_trade = 2` (invalid value → treated as truthy in Python)

Severity: **Medium**.

### 9.4 Error Messages

`_validate_parameters()` raises `ValueError` with descriptive messages:
```
ValueError: profit_percentage_threshold must be between 0 and 1, got -0.5
```

✅ Clear and actionable error messages.

---

## 10. Configuration Issues Table

| # | Issue | Location | Type | Severity | Remediation |
|---|---|---|---|---|---|
| **C1** | `client_id` not sanitized in file paths | `sonarft_helpers.py`, API layer | Security | **Medium** | Sanitize: `re.sub(r'[^a-zA-Z0-9_-]', '', client_id)` |
| **C2** | Hot-reload skips parameter validation | `sonarft_bot.py:apply_parameters()` | Safety | **Medium** | Call `_validate_parameters()` after applying |
| **C3** | `trade_amount` default = 1 BTC (~$30K) | `config_parameters.json` | Safety | **Medium** | Document prominently; consider lower default |
| **C4** | `max_trade_amount` disabled by default | `config_parameters.json` | Safety | **Medium** | Enable with reasonable default (e.g., 10× trade_amount) |
| **C5** | Docker runs as root | `Dockerfile` | Security | **Medium** | Add `USER nonroot` |
| **C6** | `sonarftdata/` baked into Docker image | `Dockerfile` | Operations | **Medium** | Mount as volume |
| **C7** | Entrypoint `python -m sonarft_bot` may not work | `Dockerfile` | Operations | **Medium** | Add `__main__.py` or use `python sonarft_bot.py` |
| **C8** | Config file errors crash bot (unhandled) | `sonarft_bot.py:load_configurations()` | Reliability | **Medium** | Wrap in try/except with clear error messages |
| **C9** | `sonarftdata/bots/` directory not auto-created | `sonarft_bot.py:create_bot()` | Reliability | **Medium** | Add `os.makedirs(..., exist_ok=True)` |
| **C10** | No schema validation for config files | All config files | Reliability | **Low** | Add JSON schema or Pydantic models |
| **C11** | Exchange IDs not validated against ccxt | `config_exchanges.json` | Reliability | **Low** | Check `hasattr(apilib, exchange_id)` |
| **C12** | Many hardcoded operational values | Various | Maintainability | **Low** | Extract to config or constants file |
| **C13** | No `.dockerignore` | `Dockerfile` | Operations | **Low** | Add to exclude tests, docs, .git |
| **C14** | `[object Object]_parameters.json` exists | `sonarftdata/config/` | Bug evidence | **Info** | Confirms unsanitized client_id from JS frontend |

---

## 11. Runtime Configuration Summary

| Aspect | Current Method | Safe? | Recommendation |
|---|---|---|---|
| Trading parameters | JSON file + hot-reload | ⚠️ Hot-reload lacks validation | Add validation to `apply_parameters()` |
| Exchange selection | JSON file | ✅ | — |
| API keys | Environment variables | ✅ | — |
| Fee rates | JSON file (static) | ⚠️ May not match actual tier | Consider querying exchange API |
| Indicator selection | JSON file | ✅ | — |
| Simulation mode | JSON file + hot-reload | ⚠️ Can be switched at runtime | Require confirmation for sim→live |
| Bot lifecycle | API calls (create/run/stop) | ✅ | — |
| Trade history | SQLite (auto-created) | ✅ | — |
| Logging | Per-client via WebSocket | ✅ | — |
| Alerting | Webhook (env var) | ✅ | — |

---

## 12. Docker Configuration Review

| Aspect | Assessment | Production Ready? |
|---|---|---|
| Base image | `python:3.11-slim` — good | ✅ |
| Dependency caching | Separate `COPY` for requirements | ✅ |
| Non-root user | ❌ Missing | ❌ |
| Health check | ❌ Missing | ❌ |
| `.dockerignore` | ❌ Missing | ❌ |
| Config as volume | ❌ Baked into image | ❌ |
| Secrets handling | ✅ Via environment variables | ✅ |
| Multi-stage build | ❌ Not used | ⚠️ Nice to have |
| Image size | ~200MB (slim base + pandas + ccxt) | ✅ Acceptable |
| Entrypoint | ⚠️ May not work without `__main__.py` | ❌ |

---

## 13. Conclusion

### Configuration System Maturity: **Functional but Needs Hardening**

The configuration system works for development and testing. The JSON-based approach is simple and readable. However, several gaps need addressing before production deployment.

### Risk Distribution

| Severity | Count | Category |
|---|---|---|
| **High** | 0 | — |
| **Medium** | 9 | Path traversal (C1), hot-reload validation (C2), unsafe defaults (C3-C4), Docker security (C5-C7), error handling (C8-C9) |
| **Low** | 4 | No schema validation, exchange ID validation, hardcoded values, no .dockerignore |
| **Info** | 1 | `[object Object]` filename evidence |

### Key Strengths

- ✅ API keys stored in environment variables, not config files
- ✅ `.env` and runtime data directories in `.gitignore`
- ✅ Parameter validation with clear error messages (6 of 8 params)
- ✅ Named config sets allow multiple configurations
- ✅ Hot-reload mechanism for runtime parameter changes
- ✅ SQLite for trade history with auto-schema creation
- ✅ Simulation mode ON by default

### Key Weaknesses

- ⚠️ `client_id` used unsanitized in file paths (confirmed by `[object Object]` file)
- ⚠️ Hot-reload bypasses parameter validation
- ⚠️ Config file errors crash the bot with unhandled exceptions
- ⚠️ Docker container runs as root
- ⚠️ `sonarftdata/` baked into Docker image instead of mounted as volume
- ⚠️ Many operational values hardcoded instead of configurable

### Top Recommendations

1. **Sanitize `client_id`** before use in file paths — prevents path traversal
2. **Add validation to `apply_parameters()`** — prevents invalid hot-reload
3. **Wrap config loading in try/except** — graceful error messages instead of crashes
4. **Add `os.makedirs` for `sonarftdata/bots/`** — prevent `FileNotFoundError`
5. **Docker: add non-root user, health check, `.dockerignore`** — production hardening
6. **Mount `sonarftdata/` as volume** — separate config from image

---

*Generated by Prompt 07-BOT-CONFIG. Next: [08-security-risk.md](../prompts/08-security-risk.md)*
