# Bot Package — Security & Trading Risk Review

**Prompt ID:** 08-BOT-SECURITY  
**Generated:** July 2025  
**Source:** `packages/bot/` — full static analysis  
**Output File:** `docs/security/bot-risks.md`  
**Depends On:** Prompts 01, 03, 04, 06, 07

---

## 1. Secret & Credential Handling

### API key storage and loading

Exchange API keys are loaded exclusively from environment variables in `_load_api_keys`:

```python
api_key  = os.environ.get(f"{prefix}_API_KEY")
secret   = os.environ.get(f"{prefix}_SECRET")
password = os.environ.get(f"{prefix}_PASSWORD", "")
```

Keys are never read from config files, never written to disk, and never appear in any log statement. ✅

The only log message related to keys is:
```
"API keys loaded for exchange: {exchange_id}"   ← exchange name only, no key value
```

### In-memory key exposure

Once loaded, keys are stored on ccxt exchange instances (`exchange.apiKey`, `exchange.secret`, `exchange.password`). These are plain Python string attributes — accessible to any code with a reference to the exchange instance. In the current architecture, only `SonarftApiManager` holds exchange instances, and it is not exposed to external callers directly.

**Finding — ccxt exchange instances are accessible via `api_manager.exchanges_instances` (public list):** Any code that receives an `api_manager` reference can iterate `exchanges_instances` and read `exchange.apiKey`. The list is not protected. In the current codebase this is not exploited, but it is a defence-in-depth gap. Should be `_exchanges_instances` (private) with no public accessor.

**Finding — REST fallback copies credentials to a new instance:** In `call_api_method`, the REST fallback reads credentials from the ccxtpro instance:

```python
"apiKey":   getattr(ws_exchange, "apiKey", ""),
"secret":   getattr(ws_exchange, "secret", ""),
"password": getattr(ws_exchange, "password", ""),
```

These are passed to a new ccxt instance. The new instance is never explicitly closed (see Prompt 06). If the instance is garbage-collected with an open connection, the credentials remain in memory until GC runs. Low risk in practice but worth noting.

### Secrets in config files

No secrets in any JSON config file. `config_fees.json`, `config_exchanges.json`, etc. contain only non-sensitive trading parameters. ✅

### `.gitignore` compliance

The `.gitignore` correctly excludes:
- `.env` and `.envrc` ✅
- `sonarftdata/history/` (SQLite DB with trade data) ✅
- `sonarftdata/bots/` (bot registry) ✅
- `sonarftdata/config/` (per-client config) ✅

**Finding — `sonarftdata/config_fees.json` and other root-level config files are NOT in `.gitignore`:** The per-client config directory (`sonarftdata/config/`) is excluded, but the root-level config files (`sonarftdata/config_parameters.json`, `sonarftdata/config_fees.json`, etc.) are tracked by git. These files contain trading parameters and fee rates — not secrets, but potentially sensitive operational data. If a developer commits a config with `is_simulating_trade=0`, it could be accidentally deployed in live mode.

**Finding — `sonarftdata/` root-level JSON files are committed to the repository:** The `sonarftdata/` directory contains live config files that are version-controlled. This means config changes require a git commit, which is good for auditability but means the repository contains operational configuration that may differ between environments.

### Webhook URL security

`SONARFT_ALERT_WEBHOOK` is read from environment and used in `_send_alert`. The URL is logged on successful send:

```python
self.logger.info(f"Alert sent to webhook: {message}")
```

The URL itself is not logged — only the message content. ✅ However, if the webhook URL contains a secret token in the path (common for Slack/Discord webhooks), it would be exposed if the URL were ever logged. Currently it is not. ✅

---

## 2. Input Validation & Injection Risks

### Input sources

The bot package has no HTTP server — it receives input only from:
1. JSON config files (operator-controlled)
2. Environment variables (operator-controlled)
3. Exchange API responses (ccxt-mediated)
4. `BotManager` method calls (from the API layer)
5. `apply_parameters` dict (from the API layer via hot-reload)

### SQL injection

All SQLite queries use parameterised statements (`?` placeholders). ✅

```python
conn.execute(
    "INSERT INTO orders (botid, timestamp, data) VALUES (?, ?, ?)",
    (str(botid), timestamp, json.dumps(data))
)
```

Table names are validated against `_ALLOWED_TABLES = frozenset({'orders', 'trades', 'daily_loss'})` before use in f-string SQL. ✅ This prevents SQL injection via table name even though table names cannot be parameterised in SQLite.

**Finding — `positions` table is missing from `_ALLOWED_TABLES`:** The `_ALLOWED_TABLES` whitelist contains `{'orders', 'trades', 'daily_loss'}` but not `'positions'`. The position tracker methods (`_position_open_sync`, `_position_close_sync`, `_positions_open_sync`) use hardcoded `"positions"` table name directly in SQL strings — they do not go through the `_db_insert`/`_db_query` helpers that check `_ALLOWED_TABLES`. This is safe (the table name is hardcoded, not user-supplied) but the whitelist is incomplete and misleading.

### Command injection

No `subprocess`, `os.system`, `eval`, or `exec` calls anywhere in the bot package. ✅

### JSON injection

Exchange API responses are parsed by ccxt — the bot never calls `json.loads` on raw exchange data directly. Config files are parsed with `json.load(f)` — standard library, no injection risk. ✅

### `apply_parameters` input validation

Hot-reload parameters arrive as a dict from the API layer. `apply_parameters` validates each value:

```python
self.profit_percentage_threshold = float(parameters["profit_percentage_threshold"])
```

`float()` conversion raises `ValueError` on non-numeric input, which propagates to the API layer. The subsequent `_validate_parameters()` call enforces range constraints. ✅

**Finding — `apply_parameters` does not validate `strategy` against an allowlist before assignment:** The strategy is assigned before validation:

```python
old_values["strategy"] = self.strategy
self.strategy = parameters["strategy"]   # assigned first
# ...
self._validate_parameters()              # validated after
```

If `_validate_parameters` raises, the rollback restores the old value. However, between assignment and validation, `self.strategy` holds an unvalidated string. If any code reads `self.strategy` in a concurrent coroutine during this window, it could see an invalid value. The window is extremely small (microseconds) and `apply_parameters` is synchronous, but it is a TOCTOU pattern.

### `sanitize_client_id`

```python
def sanitize_client_id(client_id: str) -> str:
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', str(client_id))
    if not sanitized:
        raise ValueError(f"Invalid client_id after sanitization: {client_id!r}")
    return sanitized
```

Client IDs are sanitised before use as dict keys and in file paths. ✅ The regex allows only alphanumeric, hyphen, and underscore — no path traversal characters.

---

## 3. File Path Safety

### Path construction

All paths are constructed via `_bot_path(*parts)` using `os.path.join`, anchored to `_BOT_DIR`. `os.path.join` does not prevent path traversal if a component starts with `/` or contains `..` — it would use the absolute path or traverse upward.

**Finding — config pathnames from `config.json` are not sanitised for path traversal:** `_load_config_section` resolves relative paths via `_bot_path(pathname)`. A config value of `"../../etc/passwd"` would resolve to a path outside the bot directory. Since config files are operator-controlled (not user HTTP input), this is Low risk. However, if the API layer ever allows users to specify config paths, this becomes Critical.

**Finding — `SONARFT_BACKUP_DIR` env var used directly in `os.path.join` without validation:** An operator setting `SONARFT_BACKUP_DIR=/etc` would write backup files to `/etc/sonarft_backup_YYYYMMDD.db`. Low risk (operator-controlled) but should be validated.

### Botid in file paths

Bot registry files: `sonarftdata/bots/{botid}.json`. `botid` is a UUID4 — contains only hex digits and hyphens. No path traversal possible. ✅

### File permissions

The Dockerfile creates a non-root user (`sonarft`, uid 1000) and `chown -R sonarft:sonarft /app`. All files are owned by the bot user. No world-writable files. ✅

### Symlink handling

No explicit symlink handling. `os.path.join` and `open()` follow symlinks by default. If `sonarftdata/` contains a symlink pointing outside the directory, the bot would follow it. In a Docker container with a mounted volume, this is unlikely but not impossible.

---

## 4. WebSocket Security

The bot package has **no WebSocket server**. It is a pure client — it connects to exchange WebSocket endpoints via ccxtpro. WebSocket security in the bot context means:

### ccxtpro connection security

- All exchange WebSocket connections use TLS (wss://) — enforced by ccxtpro. ✅
- Authentication is handled by ccxtpro using the configured API keys. ✅
- No custom WebSocket server is exposed by the bot package. ✅

### WebSocket to API layer

The bot package does not directly communicate with the API layer via WebSocket. The API layer (`packages/api`) imports the bot package as a Python library and calls `BotManager` methods directly. There is no inter-process WebSocket communication between bot and API. ✅

---

## 5. API Exposure Risks

The bot package exposes **no HTTP endpoints**. It is a pure library imported by `packages/api`. All external API exposure is handled by the API layer.

The bot's public interface is `BotManager`:
- `create_bot(client_id, library, config)` — creates a bot
- `run_bot(botid)` — starts the run loop
- `pause_bot(botid)` / `resume_bot(botid)` — pause/resume
- `remove_bot(botid)` — stops and removes
- `reload_parameters(client_id, new_parameters)` — hot-reload
- `set_update(botid, update_data)` / `get_update(botid)` — state updates

**Finding — `BotManager` methods accept `client_id` and `botid` without type validation:** `create_bot` accepts any string as `client_id`. `sanitize_client_id` is called, which strips non-alphanumeric characters. However, `run_bot`, `pause_bot`, `resume_bot`, and `remove_bot` accept `botid` without any sanitisation — they look up the botid in `_bots` dict, so an invalid botid simply returns `None`/no-op. No injection risk, but no input validation either.

**Finding — `reload_parameters` accepts an arbitrary dict from the API layer:** The dict is validated by `apply_parameters` (type conversion + `_validate_parameters`). However, unknown keys are silently ignored — an API caller sending `{"unknown_param": "value"}` gets no error. This is safe but could mask typos in parameter names.


---

## 6. Denial of Service (DoS) Risks

### Unbounded loops

| Loop | Bound | DoS risk |
|---|---|---|
| `run_bot` main loop | `_stop_event` + circuit breaker | None — yields every 6–18s |
| `monitor_price` | 120s timeout | None — yields every 3s |
| `monitor_order` | 300s timeout | None — yields every 1s |
| `monitor_trade_tasks` | `_stop_event` | None — yields every 1s |
| `_periodic_fee_refresh` | `_stop_event` | None — yields every 24h |
| `_periodic_db_backup` | `_stop_event` | None — yields every 24h |

All loops are bounded and yield control. No unbounded busy loops. ✅

### Memory allocation risks

**Finding — `trade_tasks` list grows unboundedly between monitor cycles:** `TradeExecutor.trade_tasks` accumulates tasks between 1s monitor cycles. Under very high trade frequency (many symbols, many exchange pairs, all profitable), tasks could accumulate faster than they are pruned. The `_MAX_CONCURRENT_TRADES=10` cap limits active tasks, but done tasks are not pruned until the next monitor cycle. In practice, with 6–18s cycle sleep, this is not a concern.

**Finding — indicator and API caches are capped at 500 entries each:** Four caches (`_ohlcv_cache`, `_order_book_cache`, `_ticker_cache`, `_indicator_cache`) each cap at 500 entries with LRU eviction. For a bot trading 10 symbols across 5 exchanges with 3 timeframes, the maximum cache size is 10 × 5 × 3 = 150 entries — well within the 500 cap. No memory exhaustion risk for typical configurations. ✅

**Finding — `errors_history.json` and `balance_history.json` grow unboundedly:** As noted in Prompt 07, these JSON files have no size limit. Under error conditions (e.g. repeated API failures), `save_error` is called frequently, growing the file indefinitely. The `_append_json` method reads the entire file on every write — for a large file, this becomes a memory spike. A 100MB JSON file would require 100MB of memory per write operation.

### Computation DoS

pandas-ta computations on 14–45 candles are fast (sub-millisecond). No expensive computation that could block the event loop for a meaningful duration. ✅

### Connection limits

ccxtpro manages WebSocket connections internally. The bot creates one exchange instance per configured exchange — typically 2–3 connections. No connection exhaustion risk for typical configurations. ✅

### Queue accumulation

No explicit queues. `trade_tasks` list is the closest equivalent — capped by `_MAX_CONCURRENT_TRADES`. ✅

---

## 7. Trading Safety Controls

### Simulation mode gate

**Two independent opt-ins required for live trading:**

1. `is_simulating_trade=0` in `config_parameters.json`
2. `SONARFT_ALLOW_LIVE=true` environment variable

Both are checked at `create_bot` time (`_check_live_mode_guard`) and at hot-reload time (`apply_parameters`). ✅

In simulation mode:
- `execute_order` generates synthetic order IDs — no real API calls ✅
- `check_balance` returns `True` without checking real balance ✅
- `monitor_price` is bypassed — target price used directly ✅

### Maximum position size

`max_trade_amount` (default 0.1 base currency) caps individual trade size. Checked in `execute_trade` before order placement. ✅

### Maximum loss limit

`max_daily_loss` (default 100.0 quote currency) halts trading when accumulated daily loss reaches the threshold. Persisted to SQLite across restarts. ✅

### Order rate limiting

`max_orders_per_minute` (default 10) caps order placement rate. Checked in `execute_trade`. ✅

### Circuit breaker

After `SONARFT_MAX_FAILURES` (default 5) consecutive search errors, the bot halts and sends a webhook alert. ✅

### Manual stop

`BotManager.remove_bot` → `SonarftBot.stop_bot` → `_stop_event.set()` stops the run loop. `pause_bot`/`resume_bot` provide temporary pause without deregistration. ✅

### Gaps in trading safety controls

**Finding — `max_total_exposure` is non-functional** (carried from Prompt 03/06): `_current_exposure` is never incremented. The cap is always 0 vs the configured limit — it never triggers. ✅ (documented as known issue)

**Finding — no per-exchange position limit:** The bot can place unlimited orders on a single exchange as long as `max_trade_amount` and `max_orders_per_minute` are not exceeded. There is no per-exchange daily loss limit or per-exchange position cap.

**Finding — circuit breaker only triggers on search errors, not on execution errors:** Consecutive failures in `sonarft_search.search_trades` trigger the circuit breaker. Failures in `execute_trade` (order placement failures, balance check failures) are logged but do not increment the circuit breaker counter. A bot that consistently fails to place orders (e.g. due to insufficient balance) will continue cycling indefinitely without triggering the circuit breaker.

---

## 8. Financial Risk Management

### Balance checks

`check_balance` verifies available balance before each order leg:
- Buy: `balance['free'][quote] >= trade_amount × price`
- Sell: `balance['free'][base] >= trade_amount`

Protected by per-exchange `asyncio.Lock` to prevent concurrent balance race conditions. ✅

In simulation mode, balance checks are bypassed — the bot can simulate trades with zero balance. This is correct for paper trading but means simulation P&L is not capital-constrained. ✅

### Slippage protection

`slippage_buffer` (default 0.0002 = 0.02%) is added to the profit threshold. In live mode, `create_order` re-checks that the monitored price has not drifted beyond `slippage_buffer` from the target price before placing the order. ✅

### Flash crash protection

`flash_crash_threshold` (default 0.02 = 2%) prevents execution when the price deviation between buy and sell exchanges exceeds 2%. ✅

### Runaway trading prevention

Multiple controls prevent runaway trading:
- `max_orders_per_minute` rate cap ✅
- `max_daily_trades` count cap (disabled by default) ⚠️
- `max_daily_loss` halt ✅
- Circuit breaker on consecutive failures ✅
- `_MAX_CONCURRENT_TRADES` task cap ✅

**Finding — `max_daily_trades=0` (disabled) by default:** With no daily trade count cap, a bot in a highly liquid market with tight spreads could execute hundreds of trades per day. The only binding constraint is `max_orders_per_minute` (10/min = 600/hour = 14,400/day theoretical maximum). For live trading, a non-zero `max_daily_trades` should be set.

### Liquidity risk

`deeper_verify_liquidity` checks order book depth and trading volume before execution. The `min_trading_volume_coefficient=50` requires 50× the trade amount in 24h volume. ✅

### Margin requirements

The bot operates in spot mode only (`exchange.options["defaultType"] = "spot"`). No margin or futures trading. No margin requirement checks needed. ✅

---

## 9. Logging & Monitoring

### What is logged

| Category | Logger | Level | Contains sensitive data? |
|---|---|---|---|
| Bot lifecycle | `sonarft` | INFO | Exchange names, botid — no secrets ✅ |
| API key loading | `sonarft` | INFO | Exchange name only — no key values ✅ |
| Trade signals | `sonarft.metrics` | INFO (JSON) | Prices, profit, exchange names — no secrets ✅ |
| Order execution | `sonarft.metrics` | INFO (JSON) | Order IDs, prices, amounts — no secrets ✅ |
| Risk events | `sonarft.metrics` | WARNING (JSON) | Risk type, amounts — no secrets ✅ |
| API calls | `sonarft.metrics` | DEBUG/WARNING (JSON) | Exchange, method, latency — no secrets ✅ |
| Errors | `sonarft` | ERROR/EXCEPTION | Stack traces — may contain exchange response data |
| Parameter changes | `sonarft` | WARNING | Old and new parameter values — no secrets ✅ |
| Live trading warning | `sonarft` | WARNING | `"⚠️ LIVE TRADING MODE ACTIVE"` ✅ |

**Finding — exception stack traces may contain exchange API response data:** `self.logger.exception(...)` logs full stack traces. If a ccxt exception includes the raw exchange response (which sometimes contains order details, balance information, or error codes with account context), this data appears in logs. This is not a secret exposure risk but could leak account state information if logs are accessible to unauthorised parties.

**Finding — no log rotation configured in the bot package:** The bot uses Python's `logging` module with no `RotatingFileHandler` or `TimedRotatingFileHandler`. Log rotation is the responsibility of the deployment environment (Docker logging driver, systemd journal, etc.). If logs are written to a file without rotation, they grow unboundedly.

### Structured metrics

`sonarft_metrics.py` emits structured JSON to the `sonarft.metrics` logger. This is well-designed for ingestion by log aggregation systems (ELK, Datadog, CloudWatch). ✅

### Alerting

Webhook alerts are sent for:
- Circuit breaker trip ✅
- Fatal error in `run_bot` ✅
- Unhedged position (second leg failure) ✅
- Cancel order failure after retries ✅
- Open positions detected on startup ✅

**Finding — no alert on daily loss limit reached:** When `is_halted()` returns `True` due to `max_daily_loss`, trading halts silently with a `logger.warning`. No webhook alert is sent. An operator relying on alerts would not be notified that the bot has stopped trading due to losses.

**Finding — no alert on circuit breaker reset:** The circuit breaker trips and sends an alert, but there is no mechanism to automatically reset it or alert when it would be safe to restart. The operator must manually restart the bot.

---

## 10. Dependency Security

### Pinned versions

All dependencies in `requirements.txt` and `pyproject.toml` are pinned to exact versions:

```
pandas==3.0.2
pandas-ta==0.4.71b0
ccxt==4.5.48
ccxt[pro]==4.5.48
pydantic>=2.0        ← not pinned ⚠️
hypothesis           ← not pinned ⚠️
pytest               ← not pinned ⚠️
pytest-asyncio       ← not pinned ⚠️
```

**Finding — `pydantic`, `hypothesis`, `pytest`, and `pytest-asyncio` are not pinned:** `pydantic>=2.0` allows any Pydantic v2 version. A breaking change in a minor Pydantic release could affect config validation. For production, all dependencies should be pinned. `hypothesis`, `pytest`, and `pytest-asyncio` are dev dependencies — less critical but should still be pinned for reproducible test environments.

### Known vulnerabilities

| Package | Version | Known CVEs | Notes |
|---|---|---|---|
| `pandas` | 3.0.2 | ⚠️ Not Found in Source Code — requires `pip audit` | Recent release, likely clean |
| `pandas-ta` | 0.4.71b0 | ⚠️ Not Found in Source Code | Beta version — stability risk |
| `ccxt` | 4.5.48 | ⚠️ Not Found in Source Code | Actively maintained |
| `pydantic` | ≥2.0 | ⚠️ Not Found in Source Code | Pydantic v2 is stable |
| `numpy` | transitive | ⚠️ Not Found in Source Code | Requires `pip audit` |

**Finding — `pandas-ta==0.4.71b0` is a beta version:** The `b0` suffix indicates a beta release. Beta packages may have undocumented breaking changes or bugs. For a production trading system, a stable release should be used. If no stable release is available, the specific beta version should be pinned and tested thoroughly.

**Finding — no automated dependency vulnerability scanning in CI:** ⚠️ Not Found in Source Code — no `pip audit`, `safety`, or `dependabot` configuration is visible in the bot package. The monorepo CI (GitHub Actions) may handle this at the root level, but it is not confirmed from the bot package alone.

### Supply chain risk

All dependencies are from PyPI. ccxt and ccxtpro are widely used, actively maintained packages with a large user base. pandas and numpy are industry-standard. The main supply chain risk is `pandas-ta` (smaller community, beta version).


---

## 11. Security Risk Table

| Risk Category | Specific Risk | Location | Severity | Likelihood | Mitigation |
|---|---|---|---|---|---|
| Secrets exposure | `exchanges_instances` public list exposes ccxt instances with API keys | `sonarft_api_manager.py` | Medium | Low (internal only) | Make `_exchanges_instances` private |
| Secrets exposure | REST fallback copies credentials to unclosed instance | `sonarft_api_manager.py` | Low | Low | Close fallback instance in `finally` |
| Secrets exposure | Root-level `sonarftdata/*.json` tracked in git | `.gitignore` | Low | Low | Add to `.gitignore` or document as intentional |
| Injection | Config pathnames not sanitised for path traversal | `sonarft_bot._load_config_section` | Low | Very Low (operator-controlled) | Validate paths stay within `sonarftdata/` |
| Injection | `SONARFT_BACKUP_DIR` used without path validation | `sonarft_bot._periodic_db_backup` | Low | Very Low | Validate is absolute path within expected dir |
| Injection | `positions` table missing from `_ALLOWED_TABLES` | `sonarft_helpers.py` | Low | None (hardcoded table name) | Add `'positions'` to `_ALLOWED_TABLES` |
| Injection | `apply_parameters` assigns strategy before validation | `sonarft_bot.py` | Low | Very Low (microsecond window) | Validate before assignment |
| DoS | `errors_history.json` unbounded growth | `sonarft_helpers.py` | Medium | Medium (error conditions) | Add size limit or migrate to SQLite |
| DoS | `balance_history.json` unbounded growth | `sonarft_helpers.py` | Low | Low | Same as above |
| Trading safety | `max_total_exposure` non-functional | `sonarft_execution.py` | High | Certain (if feature enabled) | Implement exposure tracking |
| Trading safety | Circuit breaker only on search errors, not execution errors | `sonarft_bot.run_bot` | Medium | Medium | Count execution failures too |
| Trading safety | `max_daily_trades=0` disabled by default | `config_parameters.json` | Medium | Medium (live mode) | Set non-zero default for live |
| Trading safety | No alert on daily loss limit reached | `sonarft_search.is_halted` | Medium | Medium | Add webhook alert on halt |
| Financial risk | `exchanges_fees_2` zero fees | `config_fees.json` | High | Low (accidental use) | Remove or add Pydantic guard |
| Financial risk | Untracked order on 30s placement timeout | `sonarft_api_manager.call_api_method` | High | Low-Medium | Post-placement order status check |
| Financial risk | `open_position` called with wrong botid | `sonarft_execution.py` | High | Certain (live mode) | Fix to pass actual botid |
| Dependency | `pandas-ta==0.4.71b0` beta version | `requirements.txt` | Medium | Low | Pin to stable release when available |
| Dependency | `pydantic>=2.0` not pinned | `requirements.txt` | Low | Low | Pin to exact version |
| Dependency | No automated vulnerability scanning | CI | Medium | Medium | Add `pip audit` to CI pipeline |

---

## 12. Operational Risk Table

| Risk | Scenario | Impact | Preventing Control |
|---|---|---|---|
| Unhedged position | First leg fills, second leg API fails, cancel also fails | Open position with no hedge — financial loss | `_cancel_order_with_retry` + alert ✅ |
| Stale fee rates | `refresh_fees` task dies silently | Bot uses outdated fees — may execute unprofitable trades | Periodic refresh + fallback to config rates ✅ |
| Position reconciliation failure | `open_position` stores wrong botid — restart finds no open positions | Open positions from previous session not detected | **Fix botid bug** |
| Config deployed with `is_simulating_trade=0` | Developer commits live-mode config | Accidental live trading on next deployment | `SONARFT_ALLOW_LIVE` env var gate ✅ |
| Exchange maintenance | All API calls timeout for extended period | Circuit breaker trips; bot halts | Circuit breaker + alert ✅ |
| Database corruption | SQLite DB corrupted (disk full, crash) | Trade history lost; daily loss counter reset | WAL mode reduces risk; backup task ✅ |
| Backup on same disk as DB | Disk failure destroys both DB and backups | Complete data loss | `SONARFT_BACKUP_DIR` to separate volume ⚠️ |
| Memory leak from REST fallback | Sustained WebSocket failures create unclosed sessions | Resource exhaustion over hours/days | Close fallback instances ⚠️ |
| Log file exhaustion | No log rotation; high-frequency error logging | Disk full → process crash | Configure log rotation in deployment ⚠️ |
| `errors_history.json` exhaustion | Repeated API errors fill disk | Disk full → process crash | Add size limit ⚠️ |
| Indicator warm-up period | Bot starts trading before StochRSI is valid | Trades on incomplete signals | NaN guard skips trades ✅ (implicit) |
| Rate limit exceeded | Too many API calls in short window | Exchange bans IP temporarily | `enableRateLimit=True` in ccxt ✅ |
| Partial fill imbalance | Second leg partially fills | Unhedged position until manual resolution | Alert sent; cancel attempted ✅ |
| Hot-reload with invalid params | API sends malformed parameter update | `ValueError` raised; rollback applied | Rollback mechanism ✅ |

---

## 13. Severity Assessment

### Critical findings

None — no finding rises to Critical (system compromise, guaranteed financial loss, or complete safety gate bypass).

### High findings

#### H1 — `open_position` called with wrong botid (Financial Risk)

**Location:** `sonarft_execution.py`, `_execute_two_leg_trade`, line ~310  
**Scenario:** In live mode, every trade that opens a position stores it under the exchange ID (e.g. `"okx"`) instead of the bot UUID. On restart, `_reconcile_open_positions` queries by `self.botid` — it finds nothing. Open positions from crashed sessions are invisible to the reconciliation system.  
**Financial impact:** Operator is not alerted to open positions on restart. Manual review required to discover them.  
**Fix:** Pass `botid` (the actual bot UUID) as the first argument to `open_position`.

#### H2 — Untracked order on 30s placement timeout (Financial Risk)

**Location:** `sonarft_api_manager.call_api_method`  
**Scenario:** Exchange accepts a limit order. Before the response arrives, the 30s timeout fires. `call_api_method` returns `None`. The bot treats the order as failed and moves on. The order is open on the exchange with no monitoring or cancellation.  
**Financial impact:** Open order may fill at an unfavourable price with no corresponding hedge leg.  
**Fix:** After a timeout on `create_order`, query `fetch_open_orders` to check if the order was accepted before treating it as failed.

#### H3 — `max_total_exposure` non-functional (Trading Safety)

**Location:** `sonarft_execution.py`, `execute_trade`  
**Scenario:** Operator enables `max_total_exposure=1000.0` expecting to cap concurrent open position value. `_current_exposure` is always 0.0 — the cap never triggers. Ten concurrent trades of 200 USDT each (2000 USDT total) all pass the check.  
**Financial impact:** Unlimited concurrent exposure in live mode when the feature is believed to be active.  
**Fix:** Increment `_current_exposure` before first leg, decrement after second leg completes or fails.

#### H4 — `exchanges_fees_2` zero fees (Financial Risk)

**Location:** `sonarftdata/config_fees.json`  
**Scenario:** Config accidentally references `fees_setup: 2`. All trades appear profitable (no fees deducted). Bot executes trades that lose money on every fill.  
**Financial impact:** Every executed trade results in a real loss equal to the round-trip fee cost.  
**Fix:** Remove `exchanges_fees_2` or add Pydantic validator: `if buy_fee == 0 and sell_fee == 0: raise ValueError`.

### Medium findings

| Finding | Scenario | Financial impact |
|---|---|---|
| Circuit breaker misses execution failures | Bot repeatedly fails to place orders but keeps cycling | Wasted API calls; no financial loss |
| No alert on daily loss halt | Bot stops trading; operator not notified | Missed opportunity to investigate |
| `pandas-ta` beta version | Indicator bug in beta release | Incorrect signals → wrong trades |
| `errors_history.json` unbounded | Disk full under error conditions | Process crash → unmonitored open positions |
| No vulnerability scanning in CI | Known CVE in dependency undetected | Depends on vulnerability |

---

## 14. Conclusion

### Critical security findings

None. The bot package has no critical security vulnerabilities. API keys are handled correctly (env vars only, never logged). SQL injection is prevented by parameterised queries and table whitelisting. No command injection surface exists. The live trading dual opt-in is robust.

### Critical trading safety findings

Four High findings affect live trading safety:
1. **`open_position` botid bug** — position reconciliation is broken in live mode.
2. **Untracked order on timeout** — open orders can be left unmonitored on the exchange.
3. **`max_total_exposure` non-functional** — exposure cap does not work.
4. **Zero-fee config** — accidental use causes real financial losses.

All four must be fixed before live trading.

### Hardening recommendations (priority order)

1. **High:** Fix `open_position(botid=first_exchange_id)` → pass actual bot UUID.
2. **High:** Add post-timeout order status check in `create_order`.
3. **High:** Implement `_current_exposure` tracking in `execute_trade`.
4. **High:** Remove `exchanges_fees_2` or add Pydantic zero-fee guard.
5. **Medium:** Add webhook alert when `is_halted()` returns `True`.
6. **Medium:** Count execution failures in circuit breaker, not just search failures.
7. **Medium:** Add `pip audit` to CI pipeline.
8. **Medium:** Pin `pydantic` to exact version; replace `pandas-ta` beta with stable.
9. **Medium:** Migrate `errors_history.json` to SQLite with retention policy.
10. **Low:** Make `exchanges_instances` private (`_exchanges_instances`).
11. **Low:** Add `'positions'` to `_ALLOWED_TABLES`.
12. **Low:** Close REST fallback instances in `finally` block.

### Production readiness assessment

The bot package is **not production-ready for live trading** due to the four High findings. For simulation mode, it is production-ready from a security perspective — no real funds are at risk and the safety controls function correctly.

The security posture is **good for a trading bot of this complexity**: no hardcoded secrets, no injection vulnerabilities, strong live trading gates, comprehensive alerting for critical events, and well-structured observability. The remaining issues are operational and financial risk gaps rather than security vulnerabilities.
