# Performance Optimization & Scalability Review

**Prompt ID:** 08-API-PERF  
**Package:** `packages/api` + `packages/bot`  
**Output:** `docs/performance/08-performance-optimization.md`  
**Reviewed:** July 2025  
**Status:** Complete

---

## Executive Summary

The SonarFT API is well-positioned for its target workload: a small number of concurrent clients (≤ 5 bots per client, ≤ ~20 concurrent WebSocket connections) running a latency-tolerant trading loop with 6–18 second cycle intervals. The async model is correctly implemented throughout — all blocking I/O is offloaded via `asyncio.to_thread()`, `orjson` is used for fast serialisation, GZip compression is enabled, and `uvloop`/`httptools` are configured in the Dockerfile for maximum uvicorn throughput. The most impactful performance concern is the **bot engine integration model**: `BotManager.create_bot()` and `run_bot()` are awaited directly on the event loop. `create_bot()` performs network I/O (loading exchange markets via ccxt) that can take 1–10 seconds per exchange — this blocks the event loop for the duration of the call, stalling all other requests. The second concern is the **O(N) log handler overhead** identified in Prompt 05: with N concurrent WebSocket clients, every bot log record triggers N handler invocations including N format calls. At the current scale this is negligible; it becomes measurable above ~20 concurrent clients on a high-frequency bot.

---

## Performance Baseline Assessment

No load test results or APM metrics are available in the codebase. The following estimates are derived from code analysis and the actual log file.

| Operation | Estimated Latency | Bottleneck |
|---|---|---|
| `GET /health` | < 1ms | None — pure in-memory |
| `GET /clients/{id}/bots` | < 5ms | Dict lookup in `BotManager._clients` |
| `POST /clients/{id}/bots` (create) | **1–15 seconds** | ccxt `load_markets()` network I/O on event loop |
| `POST /clients/{id}/bots/{id}/run` | < 10ms | Async task dispatch |
| `POST /clients/{id}/bots/{id}/stop` | < 50ms | `asyncio.Event` set + task cancel |
| `GET /clients/{id}/bots/{id}/orders` (100 records) | 5–20ms | `asyncio.to_thread` + SQLite indexed SELECT |
| `GET /clients/{id}/bots/{id}/orders` (1000 records) | 20–80ms | SQLite + JSON deserialisation of 1000 blobs |
| `GET /clients/{id}/parameters` (cached) | < 1ms | mtime check + dict lookup |
| `GET /clients/{id}/parameters` (uncached) | 3–8ms | `asyncio.to_thread` + file read |
| `PUT /clients/{id}/parameters` | 5–15ms | `asyncio.to_thread` + atomic file write |
| WS connect + `connected` event | < 5ms | Queue creation + log handler attach |
| WS `create` command → bot running | **1–15 seconds** | Same as POST create |

---

## Bottleneck Analysis

```mermaid
graph LR
    subgraph "Request Path"
        REQ[HTTP Request] --> MW[Middleware Stack\n~0.1ms]
        MW --> EP[Endpoint Handler\n~0.1ms]
        EP --> SVC[Service Layer\n~0.1ms]
    end

    subgraph "Bottlenecks"
        SVC -->|create_bot| BOT_CREATE[BotManager.create_bot\nccxt load_markets\n⚠️ 1-15s on event loop]
        SVC -->|get_orders/trades| DB[SQLite via to_thread\n5-80ms]
        SVC -->|get/put config| FS[File I/O via to_thread\n3-15ms]
    end

    subgraph "WebSocket Path"
        WS[WS Message] --> RL[_receive_loop\n~0.1ms]
        RL -->|create task| TASK[asyncio.Task\n~0.1ms dispatch]
        TASK -->|create_bot| BOT_CREATE
        LOG[Bot log record] -->|N handlers| LH[WsLogHandler × N\n⚠️ O(N) format calls]
        LH --> Q[asyncio.Queue\nput_nowait ~0.01ms]
    end
```

### Bottleneck 1 — `create_bot()` blocks the event loop (High impact)

`BotManager.create_bot()` calls `SonarftBot.create_bot()` which calls `SonarftApiManager` to load exchange markets via ccxt. From the actual log:

```
2026-04-23 13:03:38,421 INFO — Initializing API Manager module...
2026-04-23 13:03:39,399 INFO — Initializing API Manager module OK   ← ~1 second
2026-04-23 13:03:39,404 INFO — Loading markets...
2026-04-23 13:03:40,775 INFO — Markets loaded for okx: 2938 symbols  ← ~1.4 seconds
2026-04-23 13:03:41,860 INFO — Markets loaded for binance: 4321 symbols ← ~1 second
```

Total: ~3.4 seconds for 2 exchanges. This entire duration is spent on the asyncio event loop because `create_bot()` is `await`ed directly. During this time, no other HTTP requests or WebSocket messages can be processed.

The first session in the log shows a worse case — exchange API calls failing after a 10-second timeout:
```
2026-04-23 12:55:20,698 INFO — Initializing API Manager module...
2026-04-23 12:55:31,951 ERROR — Error calling method load_markets: binance GET ...
```
That is an **11-second block** on the event loop.

### Bottleneck 2 — O(N) log handler overhead (Medium impact at scale)

Identified in Prompt 05. With N concurrent WebSocket clients, every `sonarft.*` log record triggers N `WsLogHandler.emit()` calls, each including a `self.format(record)` call. At 20 concurrent clients and 10 log records/second, this is 200 format calls/second on the event loop thread.

### Bottleneck 3 — History query JSON deserialisation (Low-Medium impact)

`_db_query` returns `[json.loads(row[0]) for row in rows]`. For 1000 records, this is 1000 `json.loads()` calls in a thread pool worker. At ~0.01ms per call, 1000 records takes ~10ms of CPU in the thread. This is acceptable but grows linearly with `limit`.

---

## 1. Async/Concurrency Model

| Operation | Async? | Blocking? | Assessment |
|---|---|---|---|
| `BotManager.create_bot()` | ✅ `async def` | ⚠️ **Yes — network I/O on event loop** | Critical fix needed |
| `BotManager.run_bot()` | ✅ `async def` | ✅ No — dispatches task | Correct |
| `BotManager.pause_bot()` | ✅ `async def` | ✅ No — sets asyncio.Event | Correct |
| `SonarftHelpers._async_query()` | ✅ `asyncio.to_thread` | ✅ No | Correct |
| `ConfigService.get_parameters()` | ✅ `asyncio.to_thread` | ✅ No | Correct |
| `ConfigService.update_parameters()` | ✅ `asyncio.to_thread` | ✅ No | Correct |
| `WsLogHandler.emit()` | ❌ Sync | ✅ No — `put_nowait` | Correct (handlers must be sync) |
| `_send_loop` queue drain | ✅ `await queue.get()` | ✅ No | Correct |
| `_receive_loop` command dispatch | ✅ `create_task` | ✅ No | Correct |

The only blocking operation on the event loop is `BotManager.create_bot()`. All other I/O is correctly offloaded.

---

## 2. Caching Strategy

### Existing caches

| Cache | Location | TTL | Invalidation | Scope |
|---|---|---|---|---|
| `ConfigService._cache` | `config_service.py` | mtime-based | On write (`_invalidate_cache`) | Per-process |
| `SharedMarketCache.ohlcv` | `shared_cache.py` | 60s (TTLCache) | Automatic TTL expiry | Per-process |
| `SharedMarketCache.order_book` | `shared_cache.py` | 2s (TTLCache) | Automatic TTL expiry | Per-process |
| `SharedMarketCache.ticker` | `shared_cache.py` | 2s (TTLCache) | Automatic TTL expiry | Per-process |
| `get_settings()` | `core/config.py` | `lru_cache` | `cache_clear()` | Per-process |
| `get_bot_service()` | `bot_service.py` | `lru_cache` | `cache_clear()` | Per-process (test fallback) |

### Missing caches

| Data | Current | Opportunity |
|---|---|---|
| Bot list per client | `BotManager._clients` dict lookup — already O(1) | None needed |
| Trade/order history | No cache — SQLite query per request | Cache last N records per bot in memory; invalidate on new trade |
| Health response | Recomputed per request | Static response — could be cached for 5s |

The `ConfigService` mtime cache is well-designed for the access pattern (frequent reads, infrequent writes). No additional caching is needed for config.

---

## 3. HTTP/API Efficiency

### Compression

`GZipMiddleware(minimum_size=1000)` is registered in `create_app()`. Responses smaller than 1000 bytes (health, bot list) are not compressed. History responses (100+ `TradeRecord` objects) will be compressed — typical compression ratio for JSON trade records is 3–5×.

### Serialisation

`ORJSONResponse` is set as the default response class. `orjson` is 2–10× faster than the standard `json` module for serialisation. `orjson.dumps()` is also used in `_send_loop` for WebSocket messages.

### Cache-Control headers

`SecurityHeadersMiddleware` sets `Cache-Control: no-store, no-cache, must-revalidate` on **all** responses, including the health endpoint. This is correct for financial data but prevents browser/proxy caching of the health check, which is safe to cache briefly.

### HTTP/2

The Dockerfile uses `uvicorn` with `--http httptools` (HTTP/1.1). HTTP/2 would allow request multiplexing, reducing connection overhead for clients making multiple concurrent requests. This requires TLS termination at the reverse proxy (nginx/Caddy) level — not a uvicorn concern.

---

## 4. Serialisation Performance

| Format | Used | Notes |
|---|---|---|
| `orjson` | REST responses, WS send | ✅ Fastest Python JSON library |
| `json` (stdlib) | WS receive parsing, config files, SQLite data column | ✅ Acceptable for these paths |
| Pydantic `model_dump()` | Config serialisation to disk | ✅ Correct |

The `TradeRecord` model has `ConfigDict(extra="ignore")` — Pydantic v2 validation on response serialisation adds ~0.1ms per record. For 100 records this is ~10ms. This is acceptable but could be eliminated by returning raw dicts from `_async_query` and bypassing Pydantic for the response path (using `ORJSONResponse` directly with the raw list).

---

## 5. Bot Engine Integration Performance

### Current model: direct in-process async calls

The bot engine is imported as a Python library and called directly:

```python
# bot_service.py
await self._manager.create_bot(client_id)  # blocks event loop during market load
await self._manager.run_bot(botid)          # dispatches asyncio.Task — non-blocking
await self._manager.pause_bot(botid)        # sets asyncio.Event — non-blocking
```

**Advantage:** Zero IPC overhead, shared memory, no serialisation cost.  
**Disadvantage:** `create_bot()` performs network I/O synchronously on the event loop.

### Fix: wrap `create_bot()` in `asyncio.to_thread()`

The market loading in `SonarftApiManager` uses ccxt's synchronous REST API (`ccxt.exchange.load_markets()`). Wrapping the entire `create_bot()` call in `asyncio.to_thread()` would move the blocking network I/O off the event loop:

```python
# bot_service.py
async def create_bot(self, client_id: str) -> str:
    current = len(self.get_botids(client_id))
    if current >= self._settings.max_bots_per_client:
        raise BotLimitExceededError(self._settings.max_bots_per_client)
    # Offload the blocking market-load to a thread pool worker
    botid = await asyncio.to_thread(
        asyncio.run,
        self._manager.create_bot(client_id)
    )
    ...
```

Note: `asyncio.to_thread` with an async function requires care — the correct pattern is to run the async `create_bot` in a new event loop in the thread, or to refactor `SonarftApiManager.load_markets()` to use `asyncio.to_thread` internally.

The cleaner fix is to make `SonarftApiManager.load_markets()` use `asyncio.to_thread` for the ccxt REST calls, keeping the outer `create_bot()` coroutine non-blocking.

---

## 6. WebSocket Scalability

| Metric | Current | Limit | Notes |
|---|---|---|---|
| Connections per client | 1 (enforced) | 1 | New connection replaces old |
| Total concurrent connections | Unlimited | ~50 practical | O(N) log handler overhead |
| Queue size per client | 1000 events | Fixed | Silent drop on overflow |
| Keepalive interval | 30s | — | Client watchdog at 60s |
| Message serialisation | `orjson.dumps()` | — | Fast |
| Memory per connection | ~1 queue (1000 × ~200 bytes) + 1 handler | ~200KB | Acceptable |

The practical limit of ~50 concurrent connections is driven by the O(N) log handler overhead. At 50 clients with a bot emitting 20 log records/second, the event loop processes 1000 handler invocations/second. Each invocation includes a `logging.Formatter.format()` call (~0.05ms), totalling ~50ms/second of event loop time — 5% overhead. This is acceptable but should be monitored.

---

## 7. Resource Utilisation

### Memory footprint

| Component | Memory estimate | Notes |
|---|---|---|
| FastAPI + uvicorn | ~50MB base | Python process overhead |
| Bot engine (per bot) | ~100–200MB | pandas DataFrames for OHLCV history, ccxt exchange objects |
| `SharedMarketCache` | ~10MB max | 1000 entries × ~10KB per OHLCV dataset |
| WS queue (per client) | ~200KB max | 1000 events × ~200 bytes |
| SQLite WAL | ~1–5MB | WAL file grows during write bursts |
| Config cache | < 1MB | Small JSON files |

With 5 bots running, total memory is approximately 550–1050MB. This is within the range of a standard 2GB container.

### CPU utilisation

The bot's trading loop is the dominant CPU consumer:
- Indicator calculation (RSI, StochRSI, MACD) via `pandas-ta` — ~5–20ms per cycle per symbol
- OHLCV data processing via pandas — ~1–5ms per fetch
- Profit calculation via `Decimal` arithmetic — < 1ms

The API layer itself is CPU-light — request handling is dominated by I/O wait, not computation.

### Resource leaks

| Risk | Assessment |
|---|---|
| WS log handlers not detached | ✅ Detached in `_cleanup()` `finally` block |
| Background tasks not cancelled | ✅ Cancelled in `_cleanup()` |
| SQLite connections not closed | ✅ `with sqlite3.connect()` context manager |
| Completed tasks accumulating in `_tasks` | ⚠️ Not pruned until disconnect (Prompt 05 M2) |
| `lru_cache` singletons in tests | ⚠️ Must call `cache_clear()` between tests |

---

## 8. Infrastructure Scaling

### Current deployment model

Single uvicorn process, single worker. The Dockerfile uses:
```
uvicorn src.main:app --host 0.0.0.0 --port 8000 --loop uvloop --http httptools
```

`uvloop` replaces the default asyncio event loop with a libuv-based implementation — typically 2–4× faster for I/O-bound workloads.

### Horizontal scaling constraints

| Component | Stateful? | Scalable? | Blocker |
|---|---|---|---|
| HTTP endpoints (read) | ❌ Stateless | ✅ Yes | None |
| HTTP endpoints (write config) | ⚠️ File-based | ⚠️ Partial | Shared filesystem needed |
| Bot lifecycle (create/run/stop) | ✅ Stateful | ❌ No | `BotManager` is in-memory per process |
| WebSocket connections | ✅ Stateful | ❌ No | `WebSocketManager` is in-memory per process |
| WS auth tickets | ✅ Stateful | ❌ No | `TicketStore` is in-memory per process |
| Rate limiting | ⚠️ In-process | ❌ No | `slowapi` counters are per-process |
| Config cache | ⚠️ In-process | ⚠️ Partial | Cache invalidation not cross-process |

The API **cannot be horizontally scaled** in its current form. Bot state, WebSocket connections, and auth tickets are all in-memory and process-local. A load balancer would route requests to different workers, each with a different view of bot state.

For horizontal scaling, the following would be required:
1. Move bot state to a shared store (Redis)
2. Move WS ticket store to Redis
3. Move rate limiting counters to Redis
4. Use sticky sessions for WebSocket connections (or a pub/sub fan-out)

---

## 9. Load Testing Recommendations

No load tests exist in the codebase. The following scenarios should be tested:

| Scenario | Tool | Target | Pass Criteria |
|---|---|---|---|
| Baseline REST throughput | `locust` or `k6` | 50 concurrent users, GET /health | p99 < 10ms |
| Bot creation under load | `locust` | 10 concurrent POST /clients/{id}/bots | p99 < 20s (network-dependent) |
| History query pagination | `locust` | 20 concurrent GET .../orders?limit=1000 | p99 < 500ms |
| WebSocket concurrent connections | Custom asyncio client | 50 concurrent WS connections | No dropped events, p99 ping < 35s |
| Config read/write contention | `locust` | 20 concurrent PUT /parameters | No 500 errors, p99 < 100ms |

---

## Concerns & Recommendations

### High

| # | Concern | Location | Impact | Detail |
|---|---|---|---|---|
| H1 | **`create_bot()` blocks the event loop during market load** | `bot_service.py:42`, `sonarft_manager.py:create_bot` | 1–15 second event loop stall per bot creation | ccxt `load_markets()` is synchronous network I/O awaited directly on the event loop |

### Medium

| # | Concern | Location | Impact | Detail |
|---|---|---|---|---|
| M1 | **O(N) log handler overhead** | `manager.py:_attach_log_handler` | ~5% event loop overhead at 50 clients | N format calls per log record; grows linearly with concurrent WS clients |
| M2 | **No load tests** | — | Unknown | No performance baseline; regressions are undetectable |
| M3 | **History response deserialises all records in thread** | `sonarft_helpers.py:_db_query` | ~10ms per 1000 records | 1000 `json.loads()` calls per query; grows linearly with `limit` |
| M4 | **API cannot scale horizontally** | Architecture | Operational | All state is in-memory per process; multi-worker deployment is not supported |

### Low

| # | Concern | Location | Impact | Detail |
|---|---|---|---|---|
| L1 | **`Cache-Control: no-store` on health endpoint** | `main.py:SecurityHeadersMiddleware` | Negligible | Health check cannot be cached by load balancers; adds unnecessary round-trips |
| L2 | **Pydantic validation on response serialisation** | `schemas.py:TradeRecord` | ~10ms per 100 records | `response_model` validation adds overhead; raw dict return would be faster |
| L3 | **No connection pool for SQLite** | `sonarft_helpers.py` | Negligible at current scale | Each query opens a new connection; connection pooling would reduce overhead at high query rates |
| L4 | **`_db_purge` O(N) subquery** | `sonarft_helpers.py:_db_purge` | Negligible at current scale | Identified in Prompt 07 M5 |

---

## Recommendations

### Priority 1 — Fix before production load

**R1 (H1): Move blocking market load off the event loop**

The cleanest fix is to make `SonarftApiManager`'s synchronous ccxt calls use `asyncio.to_thread` internally. As a simpler interim fix, wrap the entire `create_bot` call:

```python
# bot_service.py
import asyncio

async def create_bot(self, client_id: str) -> str:
    current = len(self.get_botids(client_id))
    if current >= self._settings.max_bots_per_client:
        raise BotLimitExceededError(self._settings.max_bots_per_client)

    # Run the blocking market-load in a thread pool worker
    # so the event loop remains responsive during exchange API calls
    loop = asyncio.get_event_loop()
    botid = await loop.run_in_executor(
        None,
        lambda: asyncio.run(self._manager.create_bot(client_id))
    )
    if not botid:
        raise BotCreationFailedError("BotManager.create_bot returned None")
    return botid
```

A better long-term fix is to refactor `SonarftApiManager.load_markets()` to use `asyncio.to_thread` for the ccxt REST calls, keeping the outer coroutine non-blocking without needing `run_in_executor`.

---

### Priority 2

**R2 (M1): Replace per-client log handlers with a single fan-out handler**

```python
# websocket/manager.py
class WsFanOutHandler(logging.Handler):
    """Single root handler that fans out to all active client queues."""

    def __init__(self, manager: "WebSocketManager") -> None:
        super().__init__()
        self._manager = manager

    def emit(self, record: logging.LogRecord) -> None:
        if not _is_bot_record(record):
            return
        msg = self.format(record)  # format ONCE, not N times
        event = {
            "type": "log",
            "level": record.levelname,
            "message": msg,
            "ts": int(record.created),
        }
        for queue in list(self._manager.queues.values()):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass
```

Attach one instance of `WsFanOutHandler` to `logging.root` at startup (in `_lifespan`) rather than one `WsLogHandler` per client connection. This reduces format calls from O(N) to O(1) per log record.

**R3 (M2): Add a minimal load test suite**

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class ApiUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(10)
    def health(self):
        self.client.get("/api/v1/health")

    @task(3)
    def list_bots(self):
        self.client.get(
            "/api/v1/clients/test-client/bots",
            headers={"Authorization": "Bearer test-token"},
        )

    @task(1)
    def get_orders(self):
        self.client.get(
            "/api/v1/clients/test-client/bots/test-bot/orders?limit=100",
            headers={"Authorization": "Bearer test-token"},
        )
```

---

### Priority 3

**R4 (L1): Exempt health endpoint from `Cache-Control: no-store`**

```python
# main.py:SecurityHeadersMiddleware
async def dispatch(self, request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    # ... other headers ...
    # Allow health endpoint to be cached briefly by load balancers
    if request.url.path.endswith("/health"):
        response.headers["Cache-Control"] = "public, max-age=5"
    else:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response
```

**R5 (L2): Bypass Pydantic validation for history responses**

```python
# clients.py / bots.py — get_orders / get_trades
@router.get("/{client_id}/bots/{botid}/orders")
async def get_orders(...) -> ORJSONResponse:
    records = await service.get_orders(botid, client_id, limit, offset, from_ts, to_ts)
    return ORJSONResponse(content=records)  # skip response_model validation
```

This trades type safety for ~10ms per 100 records. Only worthwhile if history endpoints become a measured bottleneck.

---

## Performance Monitoring Checklist

- [ ] **Event loop lag monitoring** — measure time between `asyncio.sleep(0)` calls; alert if > 100ms (indicates blocking operations)
- [ ] **Bot creation latency** — log duration of `create_bot()` including market load time
- [ ] **History query latency** — log `asyncio.to_thread` duration for `_async_query`
- [ ] **WS queue depth** — expose queue size per client as a metric; alert if > 500
- [ ] **Log handler count** — monitor `len(logging.root.handlers)` to detect handler leaks
- [ ] **Memory per bot** — log RSS before/after bot creation
- [ ] **SQLite WAL file size** — alert if WAL file exceeds 100MB (indicates write stall)
- [ ] **Rate limit hit rate** — log 429 responses from slowapi
- [ ] **Load test baseline** — establish p50/p95/p99 for all endpoints before production

---

_Generated by Amazon Q Developer — SonarFT API Code Review Prompt Suite, Prompt 08_


---

## Post-Implementation Update (July 2025)

### Resolved findings

| ID | Finding | Resolution |
|---|---|---|
| H1 | `create_bot()` blocks event loop during market load | `run_in_executor(None, lambda: asyncio.run(manager.create_bot(...)))` offloads to thread pool |
| M1 | O(N) log handler overhead | `WsFanOutHandler` — single handler, O(1) formatting per record |
| M5 | `_db_purge` O(N) subquery | `OFFSET`-based index scan — O(log N) |

### `create_bot()` threading model

```python
# bot_service.py
loop = asyncio.get_event_loop()
botid = await loop.run_in_executor(
    None,
    lambda: asyncio.run(self._manager.create_bot(client_id)),
)
```

The blocking ccxt `load_markets()` REST calls now run in a thread pool worker. The event loop remains responsive during the 1–15 second market-load window. Other requests and WebSocket messages are processed normally during bot creation.

### Remaining performance items

| Item | Status |
|---|---|
| API-002 Rate-limit headers | Deferred — requires `response: Response` on all endpoints |
| API-003 Paginated response envelope | Phase 4 backlog |
| ARCH-005 Redis for multi-worker | Spike required |
