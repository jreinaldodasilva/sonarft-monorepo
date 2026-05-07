# Error Handling, Logging & Observability Review

**Prompt ID:** 06-API-ERRORS  
**Package:** `packages/api` + `packages/bot`  
**Reviewer:** Amazon Q (Senior Python / FastAPI / Observability)  
**Date:** July 2025  
**Status:** Complete  
**Implementation Status:** ✅ All findings resolved — see [roadmap](../roadmap/12-implementation-roadmap.md)

> **Post-implementation note (July 2025):** All error handling findings addressed. `BotService`/`ConfigService` no longer raise `HTTPException` directly — domain exceptions `BotCreationFailedError`, `ConfigNotFoundError`, `ConfigWriteError` added with registered handlers (M6). HTTP access log middleware added (`AccessLogMiddleware` → `sonarft.access` logger) (M5). `request_id` included in all error response bodies (M7). `BotRunError` dead code marked deprecated (M14). Bot modules use `logger.exception()` instead of `logger.error(str(e))` (M19). `503 + Retry-After: 30` returned when services are unavailable (L11). Optional structured JSON logging via `JSON_LOG_FILE` env var (L12).

---

## Executive Summary

The SonarFT API has a well-structured error handling foundation: custom domain exceptions are cleanly separated from HTTP translation, the generic 500 handler logs full tracebacks server-side while returning only `"Internal server error"` to clients, and request-ID correlation is injected into every log line via a `ContextVar`. The bot engine has a mature observability layer — a dedicated `sonarft_metrics.py` module emits structured JSON events for signals, orders, trades, risk events, and API calls to a separate rotating log file. The main gaps are: the three-format error response inconsistency (identified in Prompt 02) is confirmed here; there is no structured logging on the API side (only the bot side has JSON metrics); the `BotService` raises `HTTPException` directly from the service layer; and there is no runtime log-level change mechanism. The bot-side error handling is notably thorough — `_cancel_order_with_retry` with exponential backoff, circuit breaker in `run_bot`, flash crash detection, and unhedged position alerts all demonstrate production-grade defensive programming.

---

## 1. Exception Hierarchy

### 1.1 API Custom Exceptions — `core/errors.py`

```
Exception
├── BotNotFoundError          # Bot ID not found in registry
└── BotLimitExceededError     # Client has reached MAX_BOTS_PER_CLIENT
```

Both exceptions are minimal and focused. They carry domain-specific context (`botid` and `limit` respectively) and produce clear string representations via `__init__` messages.

```python
class BotNotFoundError(Exception):
    def __init__(self, botid: str):
        self.botid = botid
        super().__init__(f"Bot not found: {botid}")

class BotLimitExceededError(Exception):
    def __init__(self, limit: int):
        self.limit = limit
        super().__init__(f"Bot limit reached: {limit}")
```

### 1.2 Bot Custom Exceptions — `sonarft_bot.py`, `sonarft_manager.py`

```
Exception
├── BotCreationError          # sonarft_bot.py — raised during create_bot()
└── BotRunError               # sonarft_manager.py — raised during run_bot()
```

`BotCreationError` is raised for config file errors, invalid parameters, and live-mode guard violations. It is caught by `BotManager.create_bot()` and converted to a `None` return value — the API then raises `HTTPException(500)` from `BotService.create_bot()`.

`BotRunError` is defined in `sonarft_manager.py:175` but is **never raised** — `run_bot()` catches `BotRunError` at line 155 but the only code that could raise it is the `except BotRunError` clause itself. It is dead code.

### 1.3 Missing Exception Types

| Missing Exception | Where Needed | Current Behaviour |
|---|---|---|
| `BotCreationFailedError` (API-side) | `bot_service.py:40` | `HTTPException(500)` raised directly from service layer |
| `ConfigNotFoundError` | `config_service.py` | `HTTPException(404)` raised directly from service layer |
| `ConfigWriteError` | `config_service.py` | `HTTPException(500)` raised directly from service layer |

The service layer raises `HTTPException` directly rather than domain exceptions, violating the separation between business logic and HTTP translation.

---

## 2. Error Handlers

### 2.1 Registered Handlers — `main.py:178–183`

```python
app.add_exception_handler(BotNotFoundError, bot_not_found_handler)      # → 404
app.add_exception_handler(BotLimitExceededError, bot_limit_handler)     # → 429
app.add_exception_handler(Exception, generic_error_handler)             # → 500
```

### 2.2 Handler Implementations

```python
# errors.py:16–19
async def bot_not_found_handler(_request, exc: BotNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})

async def bot_limit_handler(_request, exc: BotLimitExceededError) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": str(exc)})

async def generic_error_handler(request, exc: Exception) -> JSONResponse:
    _logger.exception("Unhandled exception [%s %s] request_id=%s: %s", ...)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

All three handlers return `{"detail": "..."}` — consistent with FastAPI's default format. ✅

### 2.3 Three-Format Error Inconsistency (confirmed from Prompt 02)

| Source | Format | Example |
|---|---|---|
| Custom handlers | `{"detail": "Bot not found: abc"}` | 404, 429, 500 |
| FastAPI/Pydantic 422 | `{"detail": [{"loc": [...], "msg": "..."}]}` | Validation errors |
| slowapi rate limit | `{"error": "Rate limit exceeded: ..."}` | 429 from IP throttle |

The `slowapi` handler uses `"error"` instead of `"detail"`. This is the only format inconsistency and is fixable with a one-line custom handler (see Recommendations).

### 2.4 Exception Chaining

FastAPI endpoint handlers use `raise ... from exc` consistently:

```python
# clients.py:52
except BotLimitExceededError as exc:
    raise HTTPException(status_code=429, detail=str(exc)) from exc
```

This preserves the original exception as `__cause__` for debugging. ✅

However, `BotService` raises `HTTPException` directly without chaining:

```python
# bot_service.py:40
raise HTTPException(status_code=500, detail="Bot creation failed")
# Missing: from exc — original BotCreationError is lost
```

---

## 3. Logging Coverage

### 3.1 API Layer Coverage Matrix

| Operation | Logged? | Level | Location |
|---|---|---|---|
| Service startup (BotService init) | ✅ | INFO | `main.py:_lifespan` |
| Service startup failure | ✅ | ERROR | `main.py:_lifespan` |
| Bot created | ✅ | INFO | `bot_service.py:43` |
| Bot creation failed (None return) | ✅ | ERROR | `bot_service.py:41` |
| Bot paused | ✅ | INFO | `bot_service.py:55` |
| Bot removed | ✅ | INFO | `bot_service.py:58` |
| Auth failure (JWT) | ✅ | WARNING | `security.py:49` |
| Auth failure (missing token) | ✅ | WARNING | `security.py:84` |
| Auth failure (invalid static token) | ✅ | WARNING | `security.py:92` |
| WS client connected | ✅ | INFO | `manager.py:120` |
| WS client disconnected | ✅ | INFO | `manager.py:293` |
| WS auth failure | ✅ | WARNING | `manager.py:107` |
| WS command handler failure | ✅ | ERROR | `manager.py:238,248,258,268,278` |
| WS queue full | ✅ | WARNING | `manager.py:88` |
| Config read/write | ❌ | — | `config_service.py` — only on exception |
| HTTP request/response | ❌ | — | No request logging middleware |
| Rate limit exceeded | ✅ | Via slowapi | slowapi middleware |
| Unhandled exception | ✅ | ERROR + traceback | `errors.py:32` |

### 3.2 Bot Engine Coverage Matrix

| Operation | Logged? | Level | Location |
|---|---|---|---|
| Bot created | ✅ | INFO | `sonarft_manager.py` |
| Bot run loop started | ✅ | INFO | `sonarft_bot.py:84` |
| Search cycle error | ✅ | ERROR | `sonarft_bot.py:100` |
| Circuit breaker tripped | ✅ | ERROR | `sonarft_bot.py:109` |
| Order created | ✅ | INFO | `sonarft_execution.py` |
| Order partial fill | ✅ | WARNING | `sonarft_execution.py` |
| Order failed | ✅ | WARNING | `sonarft_execution.py` |
| Unhedged position | ✅ | WARNING + alert | `sonarft_execution.py` |
| Cancel retry failure | ✅ | ERROR + alert | `sonarft_execution.py:_cancel_order_with_retry` |
| Flash crash detected | ✅ | WARNING | `sonarft_execution.py:_determine_position` |
| Daily loss limit | ✅ | WARNING | `sonarft_search.py` (via `log_risk_event`) |
| Fee refresh | ✅ | INFO | `sonarft_bot.py` |
| API call latency | ✅ | DEBUG/WARNING | `sonarft_metrics.log_api_call` |
| Trade signal | ✅ | INFO | `sonarft_metrics.log_signal` |
| Trade result | ✅ | INFO/WARNING | `sonarft_metrics.log_trade_result` |

### 3.3 Missing: HTTP Request Logging

No middleware logs incoming HTTP requests (method, path, status code, duration). This makes it impossible to reconstruct the request history from logs alone. A standard access log would be:

```
INFO [req-id] GET /api/v1/clients/dev_user/bots → 200 (12ms)
```

---

## 4. Structured Logging

### 4.1 API Side — Plain Text

The API uses Python's standard `logging` with a plain text formatter:

```python
# main.py:52
_log_fmt = "%(asctime)s %(levelname)s [%(request_id)s] %(name)s — %(message)s"
```

Example output:
```
2025-07-01 12:00:00,123 INFO [a1b2c3d4] src.services.bot_service — Bot created: abc-123 for client: [redacted]
```

This is human-readable but not machine-parseable. Log aggregation tools (Datadog, CloudWatch, Loki) work better with JSON.

### 4.2 Bot Side — Structured JSON Metrics

`sonarft_metrics.py` emits fully structured JSON to a dedicated `sonarft_metrics.jsonl` file:

```json
{
  "timestamp": "2025-07-01T12:00:00",
  "component": "bot.execution",
  "event_type": "order_execution",
  "severity": "INFO",
  "botid": "abc-123",
  "order_id": "buy_456789",
  "symbol": "BTC/USDT",
  "exchange": "binance",
  "side": "buy",
  "requested_price": 65000.0,
  "executed_price": 65001.3,
  "amount": 1.0,
  "slippage_pct": 0.002,
  "fill_status": "full",
  "simulated": true
}
```

This is production-grade observability. The metrics logger has `propagate = False` to prevent duplication into the human-readable log. ✅

### 4.3 Request ID Correlation

`RequestIdMiddleware` (`main.py:95–105`) generates or propagates an `X-Request-ID` header and sets a `ContextVar`:

```python
request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
token = _request_id_var.set(request_id)
```

`RequestIdFilter` injects `request_id` into every log record (`main.py:38–42`). This means every log line within a request is tagged with the same ID, enabling full request tracing in log files. ✅

The `X-Request-ID` is also returned in the response header, allowing clients to correlate their requests with server logs. ✅

---

## 5. Sensitive Information in Logs

### 5.1 Audit Results

| Data Type | Logged? | Location | Assessment |
|---|---|---|---|
| JWT tokens | ❌ Never | — | ✅ |
| Static API token | ❌ Never | — | ✅ |
| Exchange API keys | ❌ Never | `sonarft_bot._load_api_keys` logs only exchange name | ✅ |
| Exchange secrets | ❌ Never | — | ✅ |
| `client_id` (may be email) | ✅ Redacted | `bot_service.py:43,55,58` — `[redacted]` | ✅ |
| `botid` | ✅ Logged | Multiple locations | ✅ Acceptable — not sensitive |
| Trade amounts/prices | ✅ Logged | `sonarft_execution.py` | ✅ Operational data |
| Balance amounts | ✅ Logged on failure | `sonarft_execution.py:check_balance` | ⚠️ Balance values in WARNING logs |
| Order IDs | ✅ Logged | `sonarft_execution.py` | ✅ Acceptable |
| IP addresses | ✅ Logged | `security.py:_client_ip` | ✅ Standard practice |
| Request bodies | ❌ Never | — | ✅ |

### 5.2 Balance Values in Logs

```python
# sonarft_execution.py:check_balance
self.logger.warning(
    f"Not enough buy balance: {balance['free'][quote]} < {amount}"
)
```

The actual balance value is logged at WARNING level. In a multi-tenant deployment where logs are shared, this could expose financial information. For a single-operator deployment this is acceptable operational data. ⚠️ Low severity.

### 5.3 No Credentials in Source Code

A full scan of all Python files found no hardcoded credentials, API keys, tokens, or passwords. ✅

---

## 6. Error Response Format

### 6.1 Current Formats

**Format A — Domain exceptions and generic 500 (consistent):**
```json
{ "detail": "Bot not found: abc-123" }
{ "detail": "Bot limit reached: 5" }
{ "detail": "Internal server error" }
```

**Format B — Pydantic 422 validation (FastAPI default):**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "exchanges", "../../etc/passwd"],
      "msg": "Value error, Invalid key in 'exchanges': '../../etc/passwd'",
      "input": "../../etc/passwd"
    }
  ]
}
```

**Format C — slowapi rate limit (inconsistent):**
```json
{ "error": "Rate limit exceeded: 60 per 1 minute" }
```

### 6.2 Missing Machine-Readable Error Codes

None of the error responses include a machine-readable `code` field. Clients must string-match `detail` to distinguish error types programmatically. A standardised envelope would be:

```json
{
  "code": "BOT_NOT_FOUND",
  "detail": "Bot not found: abc-123",
  "request_id": "a1b2c3d4"
}
```

Including `request_id` in error responses would allow clients to correlate errors with server logs without needing to inspect response headers.

### 6.3 Validation Error Detail Level

Pydantic 422 responses expose field names and rejected values. For the config key validator, this means a rejected key value appears in the error response:

```json
{ "loc": ["body", "exchanges", "../../etc/passwd"], "input": "../../etc/passwd" }
```

The rejected value is echoed back. For path traversal attempts this is not a security issue (the value came from the client), but it confirms the validation rule to an attacker. This is acceptable — the alternative (opaque errors) makes debugging harder for legitimate clients.

---

## 7. Logging Configuration

### 7.1 Startup Configuration — `main.py:48–88`

Logging is configured at module import time (before `create_app()` is called):

1. `logging.basicConfig(level=_log_level, format=_log_fmt)` — root logger
2. `logging.getLogger("ccxt").setLevel(logging.WARNING)` — suppress ccxt verbose output
3. Optional rotating file handler (`RotatingFileHandler`, 10 MB, 7 backups)
4. Optional structured metrics handler (`RotatingFileHandler`, 50 MB, 14 backups)
5. `RequestIdFilter` attached to all root handlers

### 7.2 Log Rotation

| Log | Max Size | Backups | Total Max |
|---|---|---|---|
| `logs/sonarft.log` | 10 MB | 7 | 80 MB |
| `logs/sonarft_metrics.jsonl` | 50 MB | 14 | 750 MB |

Rotation is handled by `logging.handlers.RotatingFileHandler`. The metrics log is significantly larger — 750 MB total — which is appropriate for a high-frequency trading system but should be monitored in constrained environments. ✅

### 7.3 Log Level Configuration

Log level is set from `Settings.log_level` (env var `LOG_LEVEL`, default `"INFO"`). It is applied once at startup — there is no runtime log-level change mechanism (e.g. via a `PUT /admin/log-level` endpoint or signal handler). Changing the log level requires a restart.

### 7.4 ccxt Suppression

```python
logging.getLogger("ccxt").setLevel(logging.WARNING)
```

ccxt logs full HTTP response bodies at DEBUG level. Suppressing it to WARNING prevents log flooding during normal operation. ✅

---

## 8. Exception Context

### 8.1 Stack Trace Preservation

`generic_error_handler` uses `_logger.exception(...)` which automatically includes the full stack trace in the log output. ✅

```python
# errors.py:32
_logger.exception(
    "Unhandled exception [%s %s] request_id=%s: %s",
    request.method, request.url.path, request_id_var.get("-"), exc,
)
```

### 8.2 Exception Chaining in Endpoints

Endpoint handlers chain exceptions correctly:
```python
raise HTTPException(status_code=404, detail=str(exc)) from exc  # ✅
```

Service layer does not chain:
```python
# bot_service.py:40
raise HTTPException(status_code=500, detail="Bot creation failed")
# Missing: from exc — BotCreationError.__cause__ is lost
```

### 8.3 Bot-Side Exception Context

The bot engine uses a consistent pattern across all modules:

```python
try:
    ...
except Exception as e:
    self.logger.error(f"Error get_rsi: {str(e)}")
    return None
```

This logs the error message but not the stack trace (`logger.error` vs `logger.exception`). For debugging production issues, `logger.exception` would preserve the traceback. The trade-off is log verbosity — the bot's fail-safe pattern prioritises continued operation over diagnostic detail.

---

## 9. Timeout & Retry Handling

### 9.1 Bot-Side Retry — `_cancel_order_with_retry`

The most critical retry path is order cancellation (`sonarft_execution.py:_cancel_order_with_retry`):

```python
async def _cancel_order_with_retry(self, exchange_id, order_id, base, quote, max_retries=3):
    for attempt in range(1, max_retries + 1):
        result = await self.api_manager.cancel_order(...)
        if result is not None:
            return True
        if attempt < max_retries:
            backoff = 2 ** (attempt - 1)  # 1s, 2s
            await asyncio.sleep(backoff)
    # Final failure → alert
    await self._alert_callback(f"CRITICAL: Failed to cancel order {order_id}...")
    return False
```

- 3 attempts with exponential backoff (1s, 2s) ✅
- Alert on final failure ✅
- Logs each retry attempt ✅

### 9.2 Bot-Side Circuit Breaker — `sonarft_bot.run_bot`

```python
consecutive_failures = 0
max_failures = int(os.environ.get("SONARFT_MAX_FAILURES", "5"))
base_backoff = int(os.environ.get("SONARFT_BACKOFF_BASE", "30"))

while not self._stop_event.is_set():
    try:
        await self.sonarft_search.search_trades(self.botid)
        consecutive_failures = 0
    except Exception as e:
        consecutive_failures += 1
        backoff = base_backoff * consecutive_failures
        if consecutive_failures >= max_failures:
            self._stop_event.set()  # circuit breaker trips
            await self._send_alert(...)
            break
        await asyncio.wait_for(asyncio.shield(self._stop_event.wait()), timeout=backoff)
```

- Configurable failure threshold and backoff via env vars ✅
- Alert sent when circuit breaker trips ✅
- Bot stops cleanly rather than spinning ✅

### 9.3 Order Monitoring Timeout — `monitor_order`

```python
max_wait_seconds: int = 300  # 5-minute timeout
deadline = asyncio.get_running_loop().time() + max_wait_seconds
try:
    while asyncio.get_running_loop().time() < deadline:
        ...
finally:
    await self._cancel_order_with_retry(...)  # always cancel on exit
```

The `finally` block ensures the order is always cancelled on timeout, `CancelledError`, or exception — preventing open orders from being left on the exchange. ✅

### 9.4 Price Monitoring Timeout — `monitor_price`

```python
max_wait_seconds: int = 120  # 2-minute timeout
```

Returns `None` on timeout, which causes `create_order` to skip the order. ✅

### 9.5 API-Side Timeouts

The API layer has no explicit timeouts on bot operations. `BotService.run_bot()` calls `BotManager.run_bot()` which calls `SonarftBot.run_bot()` — a long-running coroutine. If the bot hangs, the HTTP request that triggered it will also hang until the client times out. However, `run_bot` is called without `await` in the WebSocket path (via `asyncio.create_task`) and the REST endpoint returns immediately after calling `await self._manager.run_bot(botid)` which only starts the loop — it does not wait for it to complete. ✅

---

## 10. Graceful Degradation

### 10.1 BotService Unavailable

If `BotService.__init__` fails (e.g. bot package not installed), `app.state.bot_service` is set to `None` in the lifespan handler:

```python
# main.py:_lifespan
try:
    app.state.bot_service = BotService()
except Exception as exc:
    _logger.error("Failed to initialise BotService: %s", exc)
    app.state.bot_service = None
```

- WebSocket endpoint: closes with 1011 (`main.py:196`) ✅
- HTTP endpoints: `get_bot_service_from_state` falls back to `get_bot_service()` lru_cache singleton, which will also fail and raise an unhandled exception → 500 ⚠️

A 503 with `Retry-After` would be more informative than a 500 when the service is unavailable.

### 10.2 ConfigService Unavailable

Same pattern — `app.state.config_service = None` on failure. Config endpoints will 500 rather than 503.

### 10.3 Bot Engine Partial Failure

The bot's circuit breaker (`run_bot`) stops a failing bot without affecting other bots or the API. Each bot is isolated — one bot's circuit breaker does not affect others. ✅

### 10.4 Exchange API Unavailability

`SonarftApiManager` catches all exchange exceptions and returns `None`. Callers check for `None` and skip the operation. The bot continues its cycle — a failed exchange call results in a skipped trade, not a crash. ✅

---

## 11. Debugging Support

### 11.1 Request Traceability

Every log line includes `[request_id]` from the `ContextVar`. Given a `request_id` from a client error report or response header, an operator can `grep` the log file to reconstruct the full request lifecycle:

```bash
grep "a1b2c3d4" logs/sonarft.log
```

This is effective for single-instance deployments. For distributed deployments, a centralised log aggregator (Loki, CloudWatch, Datadog) would be needed. ✅

### 11.2 Bot Operation Traceability

The metrics log (`sonarft_metrics.jsonl`) provides a complete audit trail of every signal, order, trade, and risk event with `botid` as the correlation key:

```bash
jq 'select(.botid == "abc-123")' logs/sonarft_metrics.jsonl
```

This enables post-trade analysis and debugging of specific bot behaviour. ✅

### 11.3 Missing: HTTP Access Log

Without request logging middleware, there is no record of which endpoints were called, with what parameters, and what status codes were returned. An operator investigating a reported error has no way to confirm the request was received or what path it took.

### 11.4 Missing: Slow Request Detection

There is no timing instrumentation on HTTP requests. Slow bot operations (e.g. a `run_bot` call that takes 30 seconds) are not surfaced in logs.

---

## 12. Performance Impact of Logging

### 12.1 Synchronous Logging

Python's `logging` module is synchronous — `logger.info(...)` blocks the calling coroutine until the log record is written to the handler. For the rotating file handler, this involves a file write on every log call.

In the bot's high-frequency trading loop, log calls occur on every cycle (every 6–18 seconds) and on every order placement. The volume is low enough that synchronous logging is not a bottleneck. ✅

### 12.2 `WsLogHandler` — Non-Blocking

`WsLogHandler.emit()` uses `queue.put_nowait()` — it never blocks the event loop. ✅

### 12.3 Metrics Logger — Separate Handler

The metrics logger writes to a separate file with `propagate = False`. High-frequency metrics events (DEBUG-level `log_cycle`, `log_liquidity_check`) do not appear in the main log. ✅

### 12.4 Disk Usage

At maximum trading frequency with DEBUG metrics enabled, the metrics log could grow at ~1 KB/cycle × 10 cycles/minute × 60 minutes = ~600 KB/hour per bot. With 5 bots and 14 backup files at 50 MB each, disk usage is bounded at 750 MB. Acceptable for a dedicated server. ✅

---

## 13. Compliance & Standards

### 13.1 Audit Trail

The combination of:
- `sonarft_metrics.jsonl` — every trade signal, order, and result
- `sonarft.log` — every bot lifecycle event with request IDs
- SQLite `sonarft.db` — persistent order and trade history

...provides a complete audit trail for regulatory compliance in jurisdictions that require trade record-keeping. ✅

### 13.2 Log Retention

Log rotation is configured (7 backups for main log, 14 for metrics). There is no automated archival to cold storage. For compliance purposes, logs may need to be retained for longer periods (e.g. 5–7 years in some jurisdictions). This is an operational concern, not a code concern.

### 13.3 GDPR

`client_id` is redacted in `bot_service.py` logs. If `client_id` is an email address (Netlify JWT `email` claim), it should also be redacted in `security.py` auth failure logs:

```python
# security.py:84 — current
_logger.warning("Auth failure from %s — missing or invalid token", _client_ip(request))
```

The IP address is logged but not the `client_id` — this is correct. ✅

---

## 14. Concerns & Recommendations

### 14.1 Concerns

| # | Concern | Severity | Location |
|---|---|---|---|
| E1 | **`BotService` raises `HTTPException` directly** — service layer should raise domain exceptions; HTTP translation belongs in endpoints | Medium | `bot_service.py:40` |
| E2 | **`ConfigService` raises `HTTPException` directly** — same violation across all config methods | Medium | `config_service.py:72,82,95,105,115,125` |
| E3 | **No HTTP access log** — no record of requests, status codes, or response times | Medium | `main.py` — no request logging middleware |
| E4 | **`BotRunError` is dead code** — defined and caught but never raised | Low | `sonarft_manager.py:155,175` |
| E5 | **Bot-side `logger.error` instead of `logger.exception`** — stack traces not preserved in error logs | Low | Multiple bot modules |
| E6 | **No runtime log-level change** — requires restart to change verbosity | Low | `main.py:48` |
| E7 | **API-side logging is plain text only** — no structured JSON for log aggregation tools | Low | `main.py:52` |
| E8 | **Balance values logged on failure** — financial data in WARNING logs | Low | `sonarft_execution.py:check_balance` |
| E9 | **503 not used for unavailable services** — `BotService=None` results in 500 instead of 503 | Low | `main.py:_lifespan`, `bot_service.py` |
| E10 | **`BotService` exception chaining missing** — `raise HTTPException(...) from exc` not used | Low | `bot_service.py:40` |

---

### 14.2 Recommendations (Prioritised)

#### P1 — Quick wins

**R1: Fix slowapi 429 format to use `"detail"` (confirmed from Prompt 02)**

```python
# main.py — replace
from starlette.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

async def _rate_limit_handler(request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": str(exc)})

app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
```

**R2: Add exception chaining in `BotService`**

```python
# bot_service.py:40
raise HTTPException(status_code=500, detail="Bot creation failed") from exc
```

**R3: Remove dead `BotRunError`**

```python
# sonarft_manager.py — delete lines 155 (except BotRunError) and 175–179 (class BotRunError)
```

---

#### P2 — Medium effort

**R4: Add HTTP access logging middleware**

```python
# main.py — add after RequestIdMiddleware
import time

class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        t0 = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - t0) * 1000
        _logger.info(
            "%s %s → %d (%.1fms)",
            request.method, request.url.path,
            response.status_code, duration_ms,
        )
        return response
```

**R5: Move `HTTPException` out of service layer**

```python
# core/errors.py — add domain exceptions
class BotCreationFailedError(Exception):
    pass

class ConfigNotFoundError(Exception):
    def __init__(self, resource: str):
        super().__init__(f"{resource} not found")

# bot_service.py — raise domain exception
raise BotCreationFailedError("BotManager.create_bot returned None")

# clients.py — translate at endpoint
except BotCreationFailedError as exc:
    raise HTTPException(status_code=500, detail="Bot creation failed") from exc
```

**R6: Add `request_id` to error response bodies**

```python
# errors.py
async def bot_not_found_handler(request: Request, exc: BotNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "detail": str(exc),
            "request_id": request_id_var.get("-"),
        }
    )
```

**R7: Use `logger.exception` in bot error handlers for stack traces**

```python
# sonarft_execution.py and other bot modules — replace
self.logger.error(f"Error executing trade: {e}")
# with
self.logger.exception("Error executing trade")
```

---

#### P3 — Longer term

**R8: Add structured JSON logging to the API layer**

```python
# main.py — replace plain text formatter with JSON
import json

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "request_id": getattr(record, "request_id", "-"),
            "logger": record.name,
            "message": record.getMessage(),
        })
```

**R9: Add 503 response when services are unavailable**

```python
# get_bot_service_from_state
def get_bot_service_from_state(request: Request) -> BotService:
    service = getattr(request.app.state, "bot_service", None)
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Bot service unavailable — check server logs",
            headers={"Retry-After": "30"},
        )
    return service
```

**R10: Add runtime log-level endpoint (admin-only)**

```python
# api/v1/endpoints/admin.py
@router.put("/admin/log-level", dependencies=[Depends(require_auth)])
async def set_log_level(level: Literal["DEBUG","INFO","WARNING","ERROR"]) -> MessageResponse:
    logging.root.setLevel(getattr(logging, level))
    return MessageResponse(message=f"Log level set to {level}")
```

---

## Related Prompts

- [Prompt 01: Architecture Structure](../architecture/01-api-architecture.md) — Error handling architecture
- [Prompt 04: Authentication & Security](../security/04-authentication-security.md) — Security logging
- [Prompt 05: WebSocket & Real-time](../websocket/05-websocket-realtime.md) — WS error handling
- [Prompt 08: Performance Optimization](../performance/08-performance-optimization.md) — Logging performance

---

_Part of the SonarFT API Code Review Prompt Suite — Prompt 06_
