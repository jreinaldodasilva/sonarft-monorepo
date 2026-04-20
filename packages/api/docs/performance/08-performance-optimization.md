# Prompt 08 — Performance Optimization & Scalability Review

**Generated:** July 2025  
**Reviewer:** Amazon Q (Senior Python / Async Performance / FastAPI)  
**Source files inspected:**
- `packages/api/src/` (all modules)
- `packages/bot/sonarft_indicators.py`
- `packages/bot/sonarft_prices.py`
- `packages/bot/sonarft_validators.py`
- `packages/bot/sonarft_execution.py`
- `packages/bot/sonarft_search.py`
- `packages/bot/sonarft_helpers.py`
- `packages/bot/sonarft_api_manager.py`
- `packages/api/requirements.txt`

**Output location:** `docs/performance/08-performance-optimization.md`

---

## Executive Summary

The SonarFT system has a strong async foundation — `asyncio.gather` for parallel indicator fetches, TTL caches on OHLCV/order book/indicator data, and `asyncio.to_thread` for all blocking I/O. The bot's per-cycle latency is dominated by the 16-coroutine `weighted_adjust_prices` gather (up to 30s timeout), which is correctly parallelised. However, six performance issues stand out: the `get_trade_dynamic_spread_threshold_avg` validator computes an O(n²) nested loop over order book entries (100×100 = 10,000 iterations per call); `get_24h_high` and `get_24h_low` fetch 1,440 OHLCV candles per call with no caching; the SQLite write lock serialises all bot history writes; `BotService` and `ConfigService` are `lru_cache` singletons that cannot be replaced or reset without a process restart; there is no response compression on the API; and the entire system is single-process with in-memory state, making horizontal scaling impossible without architectural changes.

---

## Performance Bottleneck Map

```mermaid
graph TD
    subgraph API["API Layer (FastAPI / uvicorn)"]
        EP[HTTP Endpoints\n~1ms overhead]
        WS[WebSocket Manager\nasyncio.Queue drain]
        CS[ConfigService\nasyncio.to_thread JSON read/write]
        BS[BotService\ndelegates to BotManager]
    end

    subgraph Bot["Bot Engine (same process)"]
        BM[BotManager\nasyncio.Lock on _bots]
        SB[SonarftBot\nrun loop 6-18s cycle]
        SS[SonarftSearch\nasyncio.gather per symbol]
        SP[SonarftPrices\nweighted_adjust_prices\n16 parallel fetches, 30s timeout]
        SI[SonarftIndicators\nRSI/MACD/StochRSI\npandas-ta computation]
        SV[SonarftValidators\nO(n²) spread calc\n100 OHLCV fetch]
        SE[SonarftExecution\nmonitor_price 120s\nmonitor_order 300s]
    end

    subgraph Storage["Storage"]
        DB[(SQLite\nsingle write lock)]
        CACHE[In-memory caches\nOHLCV 60s TTL\nOrder book 2s TTL\nIndicator 60s TTL]
        EX[Exchange APIs\nccxt/ccxtpro\n30s timeout]
    end

    EP --> BS --> BM
    WS --> BM
    BS --> DB
    CS --> FS[(JSON files)]
    SB --> SS --> SP --> SI
    SP --> CACHE
    SI --> CACHE
    SS --> SV
    SV --> EX
    SE --> EX
    SE --> DB

    style SP fill:#ff9999
    style SV fill:#ff9999
    style DB fill:#ffcc99
    style SE fill:#ffcc99
```

**Red = highest latency / bottleneck risk**

---

## 1. Async / Concurrency Model

### API Layer

| Component | Async? | Assessment |
|---|---|---|
| All HTTP endpoint handlers | ✅ `async def` | Correct |
| `ConfigService` file I/O | ✅ `asyncio.to_thread` | Correct — blocking I/O offloaded |
| `BotService` bot operations | ✅ `await` | Correct |
| `BotService.get_botids` | ⚠️ Sync dict lookup | Acceptable — O(1), no I/O |
| `BotService._bot_exists` | ⚠️ Sync loop over `_clients` | Acceptable — bounded by `max_bots_per_client` |
| `lru_cache` singleton init | ⚠️ Sync `__init__` with import | Risk: import of bot package blocks event loop at first request |
| WebSocket send/receive loops | ✅ `asyncio.gather` | Correct |

**`BotService` lazy import risk:**

```python
# bot_service.py:22-24
def __init__(self) -> None:
    from sonarft_manager import BotManager   # ← sync import at first request
    from sonarft_helpers import SonarftHelpers
    self._manager = BotManager()
```

`BotService.__init__` is called the first time `get_bot_service()` is invoked (first HTTP request). The `BotManager()` constructor is synchronous and triggers the import of the entire bot package. If the bot package takes >100ms to import (e.g. pandas, pandas-ta, ccxt), the first request to any bot endpoint will block the event loop for that duration.

**Fix:** Move `BotService` initialisation to a FastAPI `lifespan` startup handler so it runs before the server accepts requests.

### Bot Layer

| Component | Async? | Assessment |
|---|---|---|
| `weighted_adjust_prices` — 16 indicators | ✅ `asyncio.gather` with 30s timeout | ✅ Fully parallelised |
| `search_trades` — per-symbol | ✅ `asyncio.gather(return_exceptions=True)` | ✅ Correct |
| `deeper_verify_liquidity` — dual exchange | ✅ `asyncio.gather` | ✅ Correct |
| `dynamic_volatility_adjustment` — MACD + RSI | ⚠️ Sequential `await` calls | Two sequential fetches that could be gathered |
| `execute_long_trade` / `execute_short_trade` | ⚠️ Sequential buy then sell | By design — sell depends on buy fill amount |
| SQLite writes | ✅ `asyncio.to_thread` | Correct |
| Exchange API calls | ✅ `asyncio.wait_for(30s)` | Correct |

---

## 2. Caching Strategy

### Existing Caches

| Cache | Location | TTL | Max Size | Eviction |
|---|---|---|---|---|
| OHLCV history | `SonarftApiManager._ohlcv_cache` | Per-timeframe (60s for 1m) | 500 entries | LRU (manual) |
| Order book | `SonarftApiManager._order_book_cache` | 2 seconds | Unbounded | None |
| Ticker | `SonarftApiManager._ticker_cache` | 2 seconds | Unbounded | None |
| Indicator results (RSI, MACD, StochRSI, direction) | `SonarftIndicators._indicator_cache` | 60 seconds | 500 entries | LRU (manual) |
| Exchange markets | `SonarftApiManager.markets` | Permanent (loaded once) | Unbounded | None |
| FastAPI settings | `core/config.py` `lru_cache` | Permanent | 1 entry | None |
| Bot/Config services | `bot_service.py`, `config_service.py` `lru_cache` | Permanent | 1 entry | None |

### Cache Gaps

| Data | Currently Cached? | Recommendation |
|---|---|---|
| `get_24h_high` / `get_24h_low` (1440 candles) | ❌ No | Cache with 5-minute TTL — value changes slowly |
| `get_support_price` / `get_resistance_price` | ❌ No | Cache with 5-minute TTL |
| `get_short_term_market_trend` | ❌ No | Cache with 60s TTL (same as indicators) |
| `get_atr` | ❌ No | Cache with 60s TTL |
| Config file reads (`ConfigService`) | ❌ No | Cache with short TTL or invalidate on write |
| Default parameters/indicators | ❌ No | Cache permanently — files never change at runtime |

`get_24h_high` and `get_24h_low` each fetch 1,440 OHLCV candles per call. If called once per trade cycle per symbol per exchange, this is a significant unnecessary load on the exchange API. The OHLCV cache in `SonarftApiManager` would serve these if the cache key matched, but the 24h methods call `get_history` with `limit=1440` while the cache stores the last fetched limit — a mismatch will cause a cache miss and a full 1440-candle fetch.

---

## 3. Critical Bottleneck: O(n²) Spread Calculation

```python
# sonarft_validators.py:get_trade_dynamic_spread_threshold_avg
buy_bids = buy_order_book['bids'][:100]
sell_asks = sell_order_book['asks'][:100]
actual_count = len(buy_bids) * len(sell_asks)   # up to 10,000

trade_spread_sum = sum(
    (ask_price - bid_price) * min(ask_volume, bid_volume)
    for (bid_price, bid_volume) in buy_order_book['bids'][:10]
    for (ask_price, ask_volume) in sell_order_book['asks'][:10]
)
trade_price_sum = sum(
    (ask_price + bid_price) / 2
    for bid_price, _ in buy_bids          # 100 entries
    for ask_price, _ in sell_asks         # 100 entries → 10,000 iterations
)
```

The `trade_price_sum` loop iterates over all combinations of 100 bid prices × 100 ask prices = 10,000 iterations per call. This runs synchronously inside `asyncio.to_thread` is not used here — it runs on the event loop directly. For 3 symbols × 2 exchanges, this is 60,000 iterations per trade cycle.

**Fix:** The average of all cross-combinations of bid and ask prices equals the average of bids plus the average of asks divided by 2 — no nested loop needed:

```python
# O(n) replacement
avg_bid = sum(p for p, _ in buy_bids) / len(buy_bids) if buy_bids else 0
avg_ask = sum(p for p, _ in sell_asks) / len(sell_asks) if sell_asks else 0
trade_price_avg = (avg_bid + avg_ask) / 2
```

---

## 4. Database Performance

Carried forward from Prompt 07 with performance framing:

| Issue | Performance Impact | Fix |
|---|---|---|
| `fetchall()` with no LIMIT | High — full table scan per request | Add `LIMIT`/`OFFSET` |
| Single `asyncio.Lock` for reads + writes | Medium — API history requests block bot writes | Enable WAL mode, lock writes only |
| New `sqlite3.connect()` per query | Low-Medium — connection overhead per call | Connection pool or persistent connection |
| No `timestamp` index | Medium — date range queries full-scan | Add composite index `(botid, timestamp)` |

### SQLite WAL Mode Impact

Without WAL: a `GET /bots/{botid}/trades` request acquires `_db_lock`, blocking all concurrent bot trade writes for the duration of the query. With WAL mode enabled, reads and writes can proceed concurrently — the lock on reads can be removed entirely.

---

## 5. WebSocket Performance

| Aspect | Current | Assessment |
|---|---|---|
| Queue size | 1000 events per client | ✅ Sufficient for normal load |
| Send loop timeout | 30s → keepalive ping | ✅ Prevents idle blocking |
| Message serialisation | `json.dumps` (stdlib) | ⚠️ `orjson` is in requirements but not used in `manager.py` |
| Concurrent connections | Unbounded | ⚠️ No limit — memory grows linearly |
| Event fan-out | Per-client queues | ✅ No broadcast overhead |
| Task tracking | None | ❌ Orphaned tasks accumulate (Prompt 05) |

`orjson` is listed in `requirements.txt` and FastAPI uses it automatically for HTTP responses, but `WebSocketManager._send_loop` uses `json.dumps` directly:

```python
# manager.py:109 — uses stdlib json
await websocket.send_text(json.dumps(event))

# Fix — use orjson for ~3x faster serialisation
import orjson
await websocket.send_text(orjson.dumps(event).decode())
```

---

## 6. Bot Engine Integration Performance

The bot runs in the same process as the API (direct Python import, no subprocess). This has two performance implications:

**Positive:** Zero IPC overhead — bot operations are direct Python function calls with no serialisation, socket, or process boundary.

**Negative:** CPU-intensive bot operations (pandas-ta indicator computation, numpy spread calculations) compete with the FastAPI event loop for CPU time. Python's GIL means that while a bot is computing RSI via pandas-ta (which releases the GIL for numpy operations), the event loop can run. However, pure-Python loops (like the O(n²) spread calculation) hold the GIL and block the event loop.

**Indicator computation latency estimate per cycle (2 exchanges, 1 symbol):**

| Operation | Estimated latency | Parallelised? |
|---|---|---|
| 16 indicator fetches (gather) | ~200-500ms (exchange RTT) | ✅ Yes |
| pandas-ta RSI computation | ~1-5ms | N/A (CPU) |
| pandas-ta StochRSI computation | ~2-8ms | N/A (CPU) |
| pandas-ta MACD computation | ~2-8ms | N/A (CPU) |
| O(n²) spread calculation | ~1-3ms (10,000 iterations) | ❌ No |
| SQLite write (order + trade) | ~5-20ms | ✅ to_thread |
| **Total per cycle** | **~210-540ms** | — |

With a 6-18s sleep between cycles, the bot is idle >95% of the time. Performance is not a bottleneck at current scale.

---

## 7. HTTP / API Efficiency

| Aspect | Status | Notes |
|---|---|---|
| Response compression (gzip) | ❌ Not configured | `GZipMiddleware` not added |
| `orjson` for HTTP responses | ✅ Auto-used by FastAPI | `orjson` in requirements — FastAPI detects it |
| `Cache-Control` headers | ❌ Not set | GET endpoints return no caching headers |
| Pagination | ❌ Not implemented | Orders/trades return full history |
| HTTP/2 | ⚠️ Depends on uvicorn config | `uvicorn[standard]` supports HTTP/2 with `--http h2` |
| Response payload size | ⚠️ Unbounded for history | No pagination = potentially large responses |

**Add GZip middleware:**

```python
# main.py
from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**Add `Cache-Control` for read-only endpoints:**

```python
# health.py
from fastapi import Response

@router.get("/health", response_model=HealthResponse)
async def health(response: Response) -> HealthResponse:
    response.headers["Cache-Control"] = "public, max-age=10"
    return HealthResponse()
```

---

## 8. `dynamic_volatility_adjustment` — Sequential Fetches

```python
# sonarft_prices.py:dynamic_volatility_adjustment
async def dynamic_volatility_adjustment(self, market_direction, market_trend, exchange, base, quote):
    macd_result = await self.sonarft_indicators.get_macd(exchange, base, quote)   # fetch 1
    rsi = await self.sonarft_indicators.get_rsi(exchange, base, quote)             # fetch 2 (sequential)
```

Both `get_macd` and `get_rsi` are independent — they can be gathered. Both have 60s TTL caches so in practice they will usually be cache hits, but on a cold start or after cache expiry they are sequential exchange API calls:

```python
# Fix
macd_result, rsi = await asyncio.gather(
    self.sonarft_indicators.get_macd(exchange, base, quote),
    self.sonarft_indicators.get_rsi(exchange, base, quote),
)
```

This is called twice per `weighted_adjust_prices` cycle (once for buy exchange, once for sell exchange), both already inside the outer `asyncio.gather`. The sequential calls add latency only on cache misses.

---

## 9. Resource Utilisation

### Memory Footprint per Bot

| Component | Memory estimate |
|---|---|
| `SonarftBot` instance + modules | ~5-10 MB (pandas, numpy loaded once) |
| OHLCV cache (500 entries × ~50 candles × 6 floats) | ~1.2 MB |
| Order book cache (unbounded) | ~100 KB per symbol |
| Indicator cache (500 entries) | ~50 KB |
| WebSocket queue (1000 events × ~200 bytes) | ~200 KB |
| **Per bot estimate** | **~7-12 MB** |

With `max_bots_per_client=5` and 10 clients: ~50 bots × 10 MB = ~500 MB. This is within typical server limits but should be monitored.

### Memory Leak Risks

| Risk | Location | Severity |
|---|---|---|
| Order book cache unbounded | `SonarftApiManager._order_book_cache` | Medium — grows with unique exchange/symbol pairs |
| Ticker cache unbounded | `SonarftApiManager._ticker_cache` | Medium — same |
| `previous_spread` dict unbounded | `SonarftIndicators.previous_spread` | Low — bounded by symbol count |
| Orphaned `asyncio.Task` objects | `WebSocketManager._receive_loop` | Medium — accumulates until GC |
| `_file_locks` dict in `SonarftHelpers` | `sonarft_helpers.py` | Low — bounded by file count |

---

## 10. Scalability Assessment

| Dimension | Current Limit | Bottleneck | Path to Scale |
|---|---|---|---|
| Bots per process | ~50 (5 per client × 10 clients) | Memory, GIL | Increase `max_bots_per_client`, monitor memory |
| Concurrent HTTP requests | ~100-500 rps | uvicorn workers (1 by default) | `--workers N` (but breaks in-memory state) |
| Concurrent WebSocket clients | Unbounded (memory limit) | Queue memory | Add `MAX_WS_CONNECTIONS` guard |
| Multi-process / multi-host | ❌ Not supported | In-memory `BotManager._bots` | Requires external state store (Redis) |
| Database write throughput | ~100 writes/sec (SQLite) | Single file + lock | PostgreSQL for multi-process |
| Exchange API rate limits | Per-exchange (ccxt `enableRateLimit=True`) | Exchange-imposed | Already handled |

**Horizontal scaling is not possible** without replacing `BotManager._bots` (in-memory dict) with an external state store. This is a fundamental architectural constraint, not a bug.

---

## 11. Quick Wins vs Long-Term

### Quick Wins (< 1 day each)

| # | Optimisation | Impact | Effort |
|---|---|---|---|
| 1 | Fix O(n²) spread loop → O(n) | Medium | 5 min |
| 2 | Add `GZipMiddleware` | Low-Medium | 5 min |
| 3 | Use `orjson` in WebSocket send loop | Low | 5 min |
| 4 | Gather `get_macd` + `get_rsi` in `dynamic_volatility_adjustment` | Low | 10 min |
| 5 | Enable SQLite WAL mode | Medium | 10 min |
| 6 | Add `LIMIT`/`OFFSET` to `_db_query` | High | 30 min |
| 7 | Add TTL cache to `get_24h_high`/`get_24h_low` | Medium | 30 min |
| 8 | Add max size to order book + ticker caches | Low | 15 min |

### Medium-Term (1-5 days each)

| # | Optimisation | Impact | Effort |
|---|---|---|---|
| 9 | Move `BotService` init to FastAPI `lifespan` | Medium | 2 hours |
| 10 | Cache `ConfigService` default reads | Low | 1 hour |
| 11 | Add `Cache-Control` headers to read-only endpoints | Low | 1 hour |
| 12 | Add `timestamp` composite index to SQLite | Medium | 30 min |

### Long-Term (architectural)

| # | Optimisation | Impact | Effort |
|---|---|---|---|
| 13 | Replace SQLite with PostgreSQL for multi-process | High | 3-5 days |
| 14 | Replace in-memory `BotManager` state with Redis | High | 5-10 days |
| 15 | Move bot engine to separate process with IPC | Medium | 5-10 days |

---

## Issues Summary

| # | Issue | Severity | Location |
|---|---|---|---|
| 1 | O(n²) nested loop in `get_trade_dynamic_spread_threshold_avg` (10,000 iterations/call) | **High** | `sonarft_validators.py:get_trade_dynamic_spread_threshold_avg` |
| 2 | `get_24h_high`/`get_24h_low` fetch 1,440 candles with no caching | **High** | `sonarft_indicators.py:get_24h_high,get_24h_low` |
| 3 | SQLite write lock blocks API history reads | **Medium** | `sonarft_helpers.py:_db_lock` |
| 4 | `BotService` lazy import blocks event loop on first request | **Medium** | `bot_service.py:22-24` |
| 5 | `fetchall()` with no LIMIT — unbounded response size | **Medium** | `sonarft_helpers.py:_db_query` |
| 6 | Order book and ticker caches are unbounded | **Medium** | `sonarft_api_manager.py` |
| 7 | `dynamic_volatility_adjustment` makes sequential MACD + RSI fetches | **Low** | `sonarft_prices.py:dynamic_volatility_adjustment` |
| 8 | WebSocket `_send_loop` uses stdlib `json.dumps` instead of `orjson` | **Low** | `websocket/manager.py:109` |
| 9 | No response compression (GZip) | **Low** | `main.py` |
| 10 | No `Cache-Control` headers on read-only endpoints | **Low** | `api/v1/endpoints/health.py`, `config.py` |

---

## Performance Monitoring Checklist

- [ ] Add `prometheus-fastapi-instrumentator` or equivalent for request latency metrics
- [ ] Track `weighted_adjust_prices` duration per cycle (currently logged implicitly via bot logs)
- [ ] Monitor SQLite database file size and query latency
- [ ] Monitor WebSocket queue depth per client
- [ ] Set up alerts for circuit breaker trips (`sonarft_bot.py:run_bot`)
- [ ] Track memory usage per bot instance
- [ ] Monitor exchange API timeout rate (`sonarft_api_manager.py:call_api_method`)
- [ ] Benchmark O(n²) fix before/after with `timeit`

---

_Part of the SonarFT API Code Review Prompt Suite — Prompt 08_  
_Previous: [Prompt 07 — Database & Persistence](../database/07-database-persistence.md)_  
_Next: [Prompt 09 — Testing & Quality](../prompts/09-testing-quality.md)_
