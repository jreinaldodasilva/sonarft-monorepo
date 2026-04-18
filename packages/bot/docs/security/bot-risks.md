# SonarFT Bot — Security & Trading Risk Review

**Prompt:** 08-BOT-SECURITY  
**Reviewer:** Senior Security Auditor / Trading Risk Analyst  
**Date:** July 2025  
**Codebase:** `packages/bot` — full security and operational risk assessment  
**Severity:** ⭐ CRITICAL — Security audit

---

## 1. Secret & Credential Handling

### 1.1 API Key Lifecycle

```
Environment Variables → _load_api_keys() → setAPIKeys() → exchange.apiKey/secret/password (in memory)
```

| Stage | Assessment |
|---|---|
| **Storage** | ✅ Environment variables only — not in config files or source code |
| **Loading** | ✅ `os.environ.get()` — standard pattern |
| **In memory** | ✅ Stored on ccxt exchange instance objects — not persisted |
| **Logging** | ✅ Only exchange ID logged (`"API keys loaded for exchange: okx"`), never key values |
| **Config files** | ✅ No secrets in any JSON config file |
| **`.gitignore`** | ✅ `.env` is gitignored |
| **Error messages** | ✅ Warning mentions env var names (`OKX_API_KEY`), not values |

### 1.2 Secret Exposure Scan

| Pattern | Files Scanned | Secrets Found? |
|---|---|---|
| `api_key` in log statements | All `sonarft_*.py` | ❌ None — only exchange ID logged |
| `secret` in log statements | All `sonarft_*.py` | ❌ None |
| `password` in log statements | All `sonarft_*.py` | ❌ None |
| Hardcoded keys/tokens | All `sonarft_*.py` | ❌ None |
| Keys in config JSON | All `sonarftdata/*.json` | ❌ None |

✅ **Clean:** No secret exposure found in source code, config files, or log statements.

### 1.3 Remaining Risks

| Risk | Assessment | Severity |
|---|---|---|
| Keys in process environment (visible via `/proc/PID/environ`) | ⚠️ Standard risk for env-var-based secrets | **Low** |
| Keys in Docker inspect output | ⚠️ If passed via `docker run -e` | **Low** |
| No key rotation mechanism | ⚠️ Requires bot restart to rotate keys | **Low** |
| Keys persist in ccxt exchange objects | ⚠️ In-memory only — cleared on process exit | **Info** |

---

## 2. Input Validation & Injection Risks

### 2.1 Input Sources

| Input | Source | Validation | Risk |
|---|---|---|---|
| `config_setup` | CLI `-c` flag | ❌ No validation — used as JSON key | **Low** (local only) |
| `library` | CLI `-l` flag | ❌ No validation — used in `if/elif` | **Low** (local only) |
| `client_id` | API layer (external) | ❌ **No sanitization** — used in file paths | **Medium** |
| `botid` | Internal (`random.randint`) | ✅ Numeric only | **None** |
| Config file contents | Local JSON files | ❌ Minimal validation | **Low** (local files) |
| Exchange API responses | External (exchange) | ⚠️ Trusted — no validation of response structure | **Low** |
| WebSocket messages | API layer (external) | ⚠️ Handled by API package, not bot | **N/A** |

### 2.2 Injection Analysis

**File Path Injection (confirmed):**

```python
# sonarftdata/config/{client_id}_parameters.json
file_name = os.path.join('sonarftdata', 'config', f"{client_id}_parameters.json")
```

If `client_id = "../../etc/cron.d/malicious"`, the path becomes:
`sonarftdata/config/../../etc/cron.d/malicious_parameters.json`

**Evidence:** `[object Object]_parameters.json` exists in `sonarftdata/config/` — confirms unsanitized input reaches the filesystem.

**Command Injection:** ❌ Not possible — no `os.system()`, `subprocess`, or `eval()` calls found.

**SQL Injection:** ❌ Not possible — SQLite uses parameterized queries:
```python
conn.execute(
    f"INSERT INTO {table} (botid, timestamp, data) VALUES (?, ?, ?)",
    (str(botid), timestamp, json.dumps(data))
)
```

⚠️ However, the `table` parameter is interpolated via f-string, not parameterized. If `table` were user-controlled, this would be SQL injection. Currently `table` is hardcoded to `'orders'` or `'trades'` — safe. Severity: **Info**.

**JSON Injection:** ❌ Not possible — `json.load()` and `json.dumps()` handle escaping.

### 2.3 Exchange API Response Trust

Exchange responses are used without structural validation:

```python
last_price = await self.call_api_method(...)
return last_price['last']  # assumes 'last' key exists
```

If an exchange returns malformed data (missing keys, wrong types), the bot crashes with `TypeError` or `KeyError`. This is a reliability issue, not a security issue — exchanges are trusted data sources. Severity: **Low**.

---

## 3. File Path Safety

### 3.1 Path Traversal Risks

| Path | User-Controlled Component | Traversal Possible? | Severity |
|---|---|---|---|
| `sonarftdata/config/{client_id}_parameters.json` | `client_id` | ✅ **Yes** | **Medium** |
| `sonarftdata/config/{client_id}_indicators.json` | `client_id` | ✅ **Yes** | **Medium** |
| `sonarftdata/bots/{botid}.json` | `botid` (numeric) | ❌ No | **None** |
| `sonarftdata/history/sonarft.db` | None | ❌ No | **None** |
| Config file paths in `config.json` | `*_pathname` values | ⚠️ Theoretically yes (local file) | **Low** |

### 3.2 Mitigation Recommendations

```python
import re

def sanitize_client_id(client_id: str) -> str:
    """Allow only alphanumeric, hyphens, and underscores."""
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', str(client_id))
    if not sanitized:
        raise ValueError(f"Invalid client_id: {client_id}")
    return sanitized
```

Apply at the API layer boundary before any file path construction.

---

## 4. WebSocket Security

The bot package itself does not expose WebSocket endpoints — the WebSocket server is in `packages/api`. However, the bot's `SonarftApiManager` connects to exchange WebSockets via ccxtpro.

### 4.1 Exchange WebSocket Connections

| Aspect | Assessment |
|---|---|
| Authentication | ✅ Handled by ccxt — API keys used for authenticated channels |
| TLS | ✅ ccxt uses `wss://` (TLS) for all exchange connections |
| Reconnection | ✅ ccxtpro handles reconnection internally |
| Message validation | ⚠️ Delegated to ccxt — bot trusts ccxt's parsing |

### 4.2 Internal WebSocket (API Layer)

⚠️ Not in scope for this review — see API Prompt 04 for WebSocket security assessment.

---

## 5. API Exposure Risks

The bot package does not expose HTTP endpoints directly. The API layer (`packages/api`) wraps bot functionality. However, the bot exposes methods that the API layer calls:

### 5.1 Bot Methods Callable from API

| Method | Parameters | Validation | Risk |
|---|---|---|---|
| `BotManager.create_bot(client_id)` | `client_id` (string) | ❌ No sanitization | **Medium** (path traversal) |
| `BotManager.run_bot(botid)` | `botid` (int) | ✅ Looked up in dict | **None** |
| `BotManager.remove_bot(botid)` | `botid` (int) | ✅ Looked up in dict | **None** |
| `BotManager.reload_parameters(client_id, params)` | `client_id`, `params` dict | ❌ No validation on params | **Medium** |
| `SonarftHelpers.get_orders(botid)` | `botid` (string) | ✅ Parameterized SQL query | **None** |
| `SonarftHelpers.get_trades(botid)` | `botid` (string) | ✅ Parameterized SQL query | **None** |

### 5.2 Information Leakage

| Source | What's Exposed | Risk |
|---|---|---|
| Error messages | Stack traces with file paths and line numbers | **Low** |
| Trade history | Full trade details (prices, amounts, exchanges) | ⚠️ Sensitive financial data |
| Order history | Full order details | ⚠️ Sensitive financial data |
| Log messages | Trading parameters, exchange names, prices | **Low** |
| Config parameters | Profit thresholds, trade amounts | **Low** |

Trade and order history access is gated by `botid` — but there's no authorization check that the requesting client owns that bot. The API layer should enforce this. Severity: **Medium** (API layer responsibility).


---

## 6. Denial of Service (DoS) Risks

### 6.1 Resource Exhaustion Vectors

| Vector | Location | Assessment | Severity |
|---|---|---|---|
| **Unbounded bot creation** | `BotManager.create_bot()` | ⚠️ No limit on bots per client (enforced in API layer via `MAX_BOTS_PER_CLIENT`) | **Low** (API layer mitigates) |
| **Unbounded trade tasks** | `TradeExecutor.trade_tasks` list | ⚠️ Tasks accumulate if trades are found faster than executed | **Low** |
| **`monitor_trade_tasks` infinite loop** | `sonarft_search.py:81` | ⚠️ Runs forever — CPU usage minimal (1s sleep) | **Low** |
| **Exchange API flooding** | `asyncio.gather(16+ calls)` | ✅ Mitigated by `enableRateLimit: True` | **None** |
| **SQLite write contention** | `SonarftHelpers._db_lock` | ✅ Serialized via asyncio.Lock | **None** |
| **Indicator cache unbounded** | `_indicator_cache` max 500 entries | ✅ Bounded with LRU eviction | **None** |
| **OHLCV cache unbounded** | `_ohlcv_cache` max 500 entries | ✅ Bounded with LRU eviction | **None** |
| **Order book cache unbounded** | `_order_book_cache` | ⚠️ No size limit — grows with exchange×symbol combinations | **Low** |
| **Log queue accumulation** | Per-client log queue (API layer) | ⚠️ Not in bot scope — API layer responsibility | **N/A** |
| **Large config files** | `json.load()` reads entire file | ⚠️ Config files are small (~1KB) — not a practical risk | **Info** |

### 6.2 Memory Usage Assessment

| Component | Memory Pattern | Bounded? |
|---|---|---|
| Exchange instances | 2 per bot (default config) | ✅ Fixed at startup |
| Indicator cache | Up to 500 entries × ~1KB | ✅ ~500KB max |
| OHLCV cache | Up to 500 entries × ~10KB | ✅ ~5MB max |
| Order book cache | Unbounded (exchange × symbol) | ⚠️ ~2 entries × 2 exchanges × 2 symbols = ~4 entries typical |
| Trade tasks | Unbounded list | ⚠️ Grows if trades accumulate — cleaned by monitor |
| SQLite DB | Grows with trade history | ⚠️ Unbounded but on disk |

**Overall:** Memory usage is well-bounded for typical configurations. No practical DoS risk from memory exhaustion.

---

## 7. Trading Safety Controls

### 7.1 Control Inventory

| Control | Location | Default | Enforced? | Bypassable? |
|---|---|---|---|---|
| **Simulation mode** | `SonarftExecution.execute_order()` | ON (`1`) | ✅ At order placement | ⚠️ Via hot-reload API |
| **Profit threshold** | `TradeProcessor.process_trade_combination()` | 0.3% | ✅ Before execution | ⚠️ Via hot-reload API |
| **Daily loss limit** | `SonarftSearch.is_halted()` | $100 | ✅ At cycle start | ⚠️ Via hot-reload API |
| **Max trade amount** | `SonarftExecution.execute_trade()` | Disabled (0) | ✅ Before execution | ⚠️ Via hot-reload API |
| **Order rate limit** | `SonarftExecution.execute_trade()` | Disabled (0) | ✅ Before execution | ⚠️ Via hot-reload API |
| **Circuit breaker** | `SonarftBot.run_bot()` | 5 failures | ✅ In run loop | ❌ Not bypassable |
| **Balance check** | `SonarftExecution.check_balance()` | Always | ✅ Before each order | ❌ Not bypassable (except sim mode) |
| **Liquidity check** | `TradeValidator` | Always | ✅ Before execution | ❌ Not bypassable |
| **Spread threshold** | `TradeValidator` | Dynamic | ✅ Before execution | ❌ Not bypassable |
| **Parameter validation** | `_validate_parameters()` | At load time | ✅ At config load | ⚠️ Skipped on hot-reload |

### 7.2 Safety Control Assessment

| Aspect | Assessment | Severity |
|---|---|---|
| All safety controls bypassable via hot-reload | ⚠️ No auth required beyond API access | **Medium** |
| No confirmation for sim→live switch | ⚠️ Single API call can enable live trading | **Medium** |
| Parameter validation skipped on hot-reload | ⚠️ Invalid values can be injected | **Medium** |
| Circuit breaker not configurable | ⚠️ Hardcoded to 5 failures — can't adjust | **Low** |
| No "kill switch" for all bots | ⚠️ Must stop each bot individually | **Low** |
| No audit log for parameter changes | ⚠️ Hot-reload changes not recorded | **Medium** |

---

## 8. Financial Risk Management

### 8.1 Risk Controls

| Risk | Control | Assessment |
|---|---|---|
| **Excessive position size** | `max_trade_amount` (disabled by default) | ⚠️ No limit unless configured |
| **Runaway trading** | `max_orders_per_minute` (disabled by default) | ⚠️ No limit unless configured |
| **Daily loss** | `max_daily_loss` ($100 default) | ✅ Halts trading when reached |
| **Insufficient balance** | `check_balance()` before each order | ✅ Skips trade if insufficient |
| **Unhedged position** | Cancel first leg on second-leg failure | ⚠️ Cancel may fail (no retry) |
| **Stale prices** | `monitor_price()` waits for favorable price | ✅ But 120s timeout |
| **Slippage** | ❌ Not Found in Source Code | **Medium** |
| **Margin requirements** | ❌ Not Found in Source Code (spot trading only) | **Info** |
| **Orphaned orders** | ❌ No cleanup mechanism | **High** |
| **Flash crash protection** | ❌ Not Found in Source Code | **Medium** |

### 8.2 Worst-Case Financial Scenarios

| Scenario | Impact | Current Mitigation | Gap |
|---|---|---|---|
| Bot switched to live mode accidentally | Real money trades at $30K/trade (default) | Sim mode default ON | No confirmation for switch |
| All safety controls disabled via hot-reload | Unlimited trading with no limits | Parameter validation at load time | Validation skipped on hot-reload |
| Exchange flash crash during open position | Unhedged loss on one leg | Cancel first leg on failure | Cancel may fail; no stop-loss |
| Bot crashes with open orders | Orders fill at unexpected prices | None | No order cleanup on crash |
| Network partition during two-leg trade | First leg fills, second leg fails | Cancel first leg | Cancel may fail over network |

---

## 9. Logging & Monitoring

### 9.1 What's Logged

| Category | Examples | Sensitive? |
|---|---|---|
| Bot lifecycle | "Bot 12345 has been created!", "Bot REMOVED!" | ❌ No |
| Trading parameters | "profit_threshold=0.003, trade_amount=1" | ⚠️ Mildly sensitive |
| Prices and indicators | "RSI buy=65.23 sell=58.91", "Target Buy: 30000.1" | ⚠️ Mildly sensitive |
| Trade execution | "Creating buy order on okx for 1.0 BTC at 30000" | ⚠️ Financial data |
| Errors | "Error get_rsi: Not enough data" | ❌ No |
| Exchange IDs | "API keys loaded for exchange: okx" | ❌ No |
| **API keys/secrets** | **Never logged** | ✅ |

### 9.2 Logging Security Assessment

| Aspect | Assessment | Severity |
|---|---|---|
| Secrets in logs | ✅ None found | — |
| Financial data in logs | ⚠️ Prices, amounts, exchange names logged | **Low** |
| Log storage | Per-client via WebSocket + Python logging | ✅ |
| Log rotation | ❌ Not configured — depends on deployment | **Low** |
| Error alerting | ✅ Webhook alerts for circuit breaker trips | — |
| **Audit trail for parameter changes** | ❌ Hot-reload changes logged but not in a structured audit format | **Medium** |

### 9.3 Alert Mechanism

```python
async def _send_alert(self, message: str) -> None:
    webhook_url = os.environ.get("SONARFT_ALERT_WEBHOOK")
    if not webhook_url:
        self.logger.error(f"ALERT (no webhook configured): {message}")
        return
    # POST to webhook URL
```

| Aspect | Assessment |
|---|---|
| Webhook-based alerting | ✅ Supports Slack/Discord/Teams |
| Fallback to logger | ✅ If no webhook configured |
| Alert on circuit breaker | ✅ Sends alert after 5 consecutive failures |
| Alert on fatal error | ✅ Sends alert on `run_bot` fatal exception |
| **Alert on failed order cancel** | ❌ Not implemented | 
| **Alert on unhedged position** | ❌ Not implemented |
| **Alert on sim→live switch** | ❌ Not implemented |

---

## 10. Dependency Security

### 10.1 Dependency Inventory

| Package | Version | Pinned? | Known Vulnerabilities | Risk |
|---|---|---|---|---|
| `fastapi` | 0.135.3 | ✅ | None known | **None** |
| `uvicorn[standard]` | 0.44.0 | ✅ | None known | **None** |
| `pandas` | 3.0.2 | ✅ | None known | **None** |
| `pandas-ta` | unpinned | ❌ **No** | Beta library (0.3.14b0) | **Medium** |
| `simple-websocket` | 1.1.0 | ✅ | None known | **None** |
| `ccxt` | 4.5.48 | ✅ | None known | **None** |
| `pytest` | unpinned | ❌ | Dev dependency only | **None** |
| `pytest-asyncio` | unpinned | ❌ | Dev dependency only | **None** |
| `orjson` | unpinned | ❌ | Not used in code | **Low** |
| `coincurve` | unpinned | ❌ | Not used in code | **Low** |
| `aiofiles` | unpinned | ❌ | Not used in code | **Low** |
| `PyJWT[crypto]` | ≥2.7.0 | ⚠️ Minimum only | None known | **Low** |

### 10.2 Supply Chain Risks

| Risk | Assessment | Severity |
|---|---|---|
| `pandas-ta` unpinned + beta | ⚠️ Could break indicator calculations silently | **Medium** |
| Unused dependencies (`orjson`, `coincurve`, `aiofiles`) | ⚠️ Unnecessary attack surface | **Low** |
| `ccxt` is a large package with many transitive deps | ⚠️ Standard risk for exchange libraries | **Low** |
| No `pip audit` or vulnerability scanning in CI | ⚠️ No automated vulnerability detection | **Medium** |
| No lockfile (`requirements.txt` without hashes) | ⚠️ Reproducibility risk | **Low** |


---

## 11. Security Risk Table

| # | Risk Category | Specific Risk | Location | Severity | Likelihood | Mitigation |
|---|---|---|---|---|---|---|
| **S1** | Path Traversal | `client_id` used unsanitized in file paths | `sonarft_helpers.py`, API layer | **Medium** | Medium | Sanitize `client_id` with allowlist regex |
| **S2** | Trading Safety | Hot-reload can switch sim→live without confirmation | `sonarft_bot.py:apply_parameters()` | **Medium** | Medium | Require separate auth for sim→live |
| **S3** | Trading Safety | Hot-reload skips parameter validation | `sonarft_bot.py:apply_parameters()` | **Medium** | Medium | Call `_validate_parameters()` after apply |
| **S4** | Trading Safety | No audit log for parameter changes | `sonarft_bot.py:apply_parameters()` | **Medium** | High | Log changes to structured audit trail |
| **S5** | Container Security | Docker runs as root | `Dockerfile` | **Medium** | High | Add `USER nonroot` |
| **S6** | Dependency | `pandas-ta` unpinned beta library | `requirements.txt` | **Medium** | Medium | Pin to `0.3.14b0` |
| **S7** | Dependency | No vulnerability scanning | CI/CD | **Medium** | Medium | Add `pip audit` to CI |
| **S8** | Information Leak | Trade history accessible without ownership check | `SonarftHelpers.get_orders/trades()` | **Medium** | Low | API layer should enforce ownership |
| **S9** | SQL Injection | `table` parameter in f-string SQL | `sonarft_helpers.py:_db_insert/_db_query` | **Info** | None (hardcoded) | Use allowlist validation |
| **S10** | Secrets | API keys in process environment | Standard pattern | **Low** | Low | Consider secrets manager for production |
| **S11** | Dependency | Unused packages increase attack surface | `requirements.txt` | **Low** | Low | Remove `orjson`, `coincurve`, `aiofiles` |

---

## 12. Operational Risk Table

| # | Risk | Scenario | Impact | Preventing Control | Gap |
|---|---|---|---|---|---|
| **O1** | Accidental live trading | Operator or API call sets `is_simulating_trade=0` | Real money trades at default $30K/trade | Sim mode default ON | No confirmation required |
| **O2** | Orphaned orders on crash | Bot process killed with open orders | Orders fill at unexpected prices/times | None | No order cleanup on shutdown |
| **O3** | Unhedged position | Second leg fails, cancel of first leg also fails | Open exposure to market risk | Cancel first leg | No retry, no alert |
| **O4** | Flash crash | Market drops 10%+ during open position | Loss on one or both legs | None | No stop-loss, no circuit breaker for price |
| **O5** | Exchange maintenance | Exchange goes offline during trade | One leg fills, other fails | Cancel first leg | Cancel may fail |
| **O6** | Config corruption | `config.json` manually edited with errors | Bot crashes on startup | `_validate_parameters()` | Only validates 6 of 8 params; no schema validation |
| **O7** | Daily loss not reset | Bot runs past midnight | Stays halted from previous day's losses | `max_daily_loss` | No automatic daily reset |
| **O8** | Multiple bots same exchange | Two bots trade same symbol on same exchange | Conflicting orders, doubled position | None | No cross-bot coordination |
| **O9** | API key expiration | Exchange rotates API keys | All orders fail with auth error | Circuit breaker (5 failures) | No specific auth error handling |
| **O10** | Disk full | SQLite DB or JSON files fill disk | Write failures, potential data loss | None | No disk space monitoring |

---

## 13. Severity Assessment

### 13.1 Critical Findings

**No Critical (show-stopper) security vulnerabilities found.** The system does not expose secrets, does not have remote code execution vectors, and has reasonable default safety controls.

### 13.2 High-Severity Findings

| Finding | Scenario | Financial Impact | Remediation |
|---|---|---|---|
| Orphaned orders on shutdown/crash (from Prompt 06) | Bot stops with open orders | Orders fill at unexpected prices — potential significant loss | Cancel all open orders on shutdown; implement order reconciliation on startup |
| Failed cancel leaves unhedged position (from Prompt 06) | Network error during cancel | Open market exposure — loss proportional to market movement | Retry cancel 3×; alert operator; consider market order to close |

### 13.3 Medium-Severity Findings (Security-Specific)

| # | Finding | Attack/Failure Scenario | Remediation |
|---|---|---|---|
| S1 | Path traversal via `client_id` | Malicious client_id writes files outside `sonarftdata/` | Sanitize with `re.sub(r'[^a-zA-Z0-9_-]', '', client_id)` |
| S2 | Sim→live switch via hot-reload | Accidental or malicious API call enables live trading | Require separate auth token or confirmation |
| S3 | Validation bypass via hot-reload | Invalid parameters injected at runtime | Call `_validate_parameters()` in `apply_parameters()` |
| S4 | No audit trail | Parameter changes not recorded — no forensics | Log all changes to structured audit table |
| S5 | Root container | Container compromise = host compromise | Add non-root user to Dockerfile |
| S6 | Unpinned pandas-ta | Silent calculation changes on update | Pin version |
| S7 | No vulnerability scanning | Known CVEs in dependencies go undetected | Add `pip audit` to CI |

---

## 14. Conclusion

### Security Posture: **Adequate for Development, Needs Hardening for Production**

The bot package has a clean secret handling pattern and no critical security vulnerabilities. The main risks are operational (orphaned orders, unhedged positions) and configuration-related (path traversal, hot-reload safety).

### Risk Distribution

| Severity | Count | Category |
|---|---|---|
| **Critical** | 0 | — |
| **High** | 2 | Orphaned orders, failed cancel (from Prompt 06 — operational, not security) |
| **Medium** | 8 | Path traversal, hot-reload safety (3), Docker root, dependency (2), info leak |
| **Low** | 4 | Secrets in env, unused deps, financial data in logs, no lockfile |
| **Info** | 2 | SQL table f-string, keys in memory |

### What's Secure

- ✅ **Secrets:** API keys in environment variables, never logged, never in config files
- ✅ **No RCE vectors:** No `eval()`, `exec()`, `os.system()`, or `subprocess` calls
- ✅ **SQL injection safe:** Parameterized queries for all user data
- ✅ **Simulation default ON:** Prevents accidental live trading on first run
- ✅ **Circuit breaker:** Stops bot after 5 consecutive failures with webhook alert
- ✅ **Balance checks:** Before every order in live mode
- ✅ **`.gitignore`:** Secrets and runtime data excluded from version control

### What Needs Hardening

1. **Sanitize `client_id`** — prevent path traversal (Priority: High)
2. **Add validation to hot-reload** — prevent invalid parameter injection (Priority: High)
3. **Require confirmation for sim→live** — prevent accidental live trading (Priority: High)
4. **Add audit logging** — record all parameter changes (Priority: Medium)
5. **Docker non-root user** — reduce container compromise impact (Priority: Medium)
6. **Pin `pandas-ta`** — prevent silent calculation changes (Priority: Medium)
7. **Add `pip audit` to CI** — detect known vulnerabilities (Priority: Medium)
8. **Remove unused dependencies** — reduce attack surface (Priority: Low)

### Production Readiness

| Aspect | Ready? | Blocker? |
|---|---|---|
| Secret handling | ✅ Yes | — |
| Input validation | ⚠️ Needs `client_id` sanitization | Yes |
| Trading safety | ⚠️ Needs hot-reload validation | Yes |
| Container security | ⚠️ Needs non-root user | Recommended |
| Dependency management | ⚠️ Needs pinning + scanning | Recommended |
| Order lifecycle | ❌ Needs shutdown cleanup | Yes (from Prompt 06) |

---

*Generated by Prompt 08-BOT-SECURITY. Next: [09-performance-scalability.md](../prompts/09-performance-scalability.md)*
