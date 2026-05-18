# Bot Package — Performance & Scalability Review

**Prompt ID:** 09-BOT-PERFORMANCE  
**Generated:** July 2025  
**Source:** `packages/bot/` — full static analysis  
**Output File:** `docs/operations/bot-performance.md`  
**Depends On:** `docs/architecture/bot-overview.md` (01), `docs/async/bot-concurrency.md` (02)

---

## 1. API Call Frequency Audit

### Per-cycle API call budget

With default config: 2 exchanges (`okx`, `binance`), 1 symbol (`ETH/USDT`), 1 quote, cycle sleep 6–18s.

Per `process_symbol` call, for each exchange pair (2 pairs: okx→binance, binance→okx):

**`weighted_adjust_prices` — 14 concurrent fetches per pair:**

| Fetch | Method | Cache TTL | Net calls/pair |
|---|---|---|---|
| `get_market_direction` × 2 | `fetch_ohlcv` (1m, 16 candles) | 60s | 0–2 (cache hit after first cycle) |
| `get_rsi` × 2 | `fetch_ohlcv` (1m, 16 candles) | 60s | 0 (same OHLCV key as direction) |
| `get_stoch_rsi` × 2 | `fetch_ohlcv` (1m, 32 candles) | 60s | 0–2 (different limit, may miss) |
| `get_short_term_market_trend` × 2 | `fetch_ohlcv` (1m, 6 candles) | 60s | 0 (subset of cached 32-candle response) |
| `get_volatility` × 2 | `get_order_book` | 2s | 0–2 (2s TTL, likely hit within cycle) |
| `get_order_book` × 2 | `get_order_book` | 2s | 0 (same key as volatility) |
| `get_support_price` × 1 | `fetch_ohlcv` (1h, 24 candles) | 3600s | 0–1 (1h TTL, hit after first cycle) |
| `get_resistance_price` × 1 | `fetch_ohlcv` (1h, 24 candles) | 3600s | 0 (same key as support) |
| `dynamic_volatility_adjustment` × 2 | `get_rsi` + `get_macd` | 60s | 0 (RSI cached; MACD not in default config) |

**`get_latest_prices` — per symbol:**

| Fetch | Method | Cache TTL | Net calls |
|---|---|---|---|
| `get_order_book` × 2 exchanges | `watch_order_book` | 2s | 0–2 |
| `_get_ticker` × 2 exchanges | `watch_ticker` | 2s | 0–2 |

**Total net API calls per cycle (warm, all caches populated):**

| Scenario | Net calls | Notes |
|---|---|---|
| First cycle (cold cache) | ~12–16 | All OHLCV and order book fetches miss |
| Subsequent cycles (< 2s elapsed) | 0–4 | Order book/ticker may expire (2s TTL) |
| Subsequent cycles (2–60s elapsed) | 2–6 | Order book/ticker refresh; OHLCV cached |
| After 60s (OHLCV cache expires) | 6–12 | OHLCV refetched for all indicators |

**Finding — OHLCV cache key ignores `limit`:** As noted in Prompt 06, a 16-candle request and a 32-candle request for the same exchange/symbol/timeframe share the same cache key. If the 32-candle StochRSI request is made first, the 16-candle RSI request hits the cache. If RSI is requested first (16 candles cached), the StochRSI request (32 candles needed) misses and triggers a fresh fetch. Call order within `asyncio.gather` is non-deterministic in terms of which completes first, but the gather starts all coroutines simultaneously — the first to complete sets the cache. This is generally fine but means cache hit rate for OHLCV is order-dependent.

### API call table

| API Call | Purpose | Frequency | Cache | Optimization Potential |
|---|---|---|---|---|
| `fetch_ohlcv` (1m, 16–45 candles) | RSI, SMA, MACD, StochRSI | Every 60s per exchange/symbol | 60s TTL ✅ | Batch all indicators from one fetch |
| `fetch_ohlcv` (1h, 24 candles) | Support/resistance | Every 3600s per exchange/symbol | 3600s TTL ✅ | None needed |
| `watch_order_book` / `fetch_order_book` | VWAP, volatility, liquidity | Every 2s per exchange/symbol | 2s TTL ✅ | None needed |
| `watch_ticker` / `fetch_ticker` | Last price, volume | Every 2s per exchange/symbol | 2s TTL ✅ | None needed |
| `fetch_balance` | Balance check before orders | Per trade leg (live only) | None | Acceptable — safety critical |
| `create_order` | Order placement | Per trade (live only) | N/A | None |
| `cancel_order` | Order cancellation | Per failed/partial trade | N/A | None |
| `watch_orders` / `fetch_orders` | Order status monitoring | Every 1s during monitor_order | None | Reduce polling interval |
| `fetch_open_orders` | Startup reconciliation | Once at startup | N/A | None |
| `fetch_trading_fees` | Fee refresh | Every 24h | N/A | None |
| `load_markets` | Market data | Once at startup | N/A | None |

**Finding — `watch_orders` polled every 1s for up to 300s per order:** In `monitor_order`, `api_manager.watch_orders` is called every 1 second for up to 300 seconds. In ccxtpro mode, `watch_orders` is a WebSocket subscription that returns on the next update — it does not poll. In ccxt REST mode, `fetch_orders` is called every 1 second, generating up to 300 REST calls per order. For a bot with `max_orders_per_minute=10` and 2 concurrent orders, this is 20 REST calls/second during active monitoring — potentially hitting exchange rate limits.

---

## 2. Order Book Fetching Analysis

### Fetch frequency

Order book is fetched via `get_order_book` with a 2s TTL cache. In a single cycle:
- `get_latest_prices` fetches order book for each exchange (2 fetches)
- `weighted_adjust_prices` fetches order book for each exchange again (2 fetches via `get_order_book` in the gather)
- `get_volatility` fetches order book for each exchange (2 fetches via `get_order_book`)
- `deeper_verify_liquidity` fetches order book for each exchange (2 fetches)

All 8 fetches share the same 2s TTL cache key (`{exchange_id}:{symbol}`). Within a single cycle (which completes in < 2s), all fetches after the first hit the cache. ✅

**Finding — order book fetched in `get_latest_prices` AND `weighted_adjust_prices` for the same exchange/symbol:** `get_latest_prices` calls `api_manager.get_order_book` directly. `weighted_adjust_prices` calls `sonarft_indicators.get_order_book` which also calls `api_manager.get_order_book`. Both use the same cache key — the second call hits the cache. No redundant API call, but the code structure implies a double-fetch that is only efficient because of the cache.

### Data staleness

With a 2s TTL, order book data can be up to 2 seconds old when used for price decisions. For a bot with a 6–18s cycle sleep, the order book is refreshed at most once per cycle. In a fast-moving market, 2s-old order book data may not reflect the current best bid/ask. This is a design trade-off between API cost and data freshness.

---

## 3. Data Processing Performance

### DataFrame operations

All indicator computations create a `pd.Series` from a list comprehension over 14–45 OHLCV candles:

```python
close_prices = pd.Series([x[4] for x in ohlcv])
```

For 45 elements, this is ~1–5 microseconds. pandas-ta then computes the indicator on this Series. Total per-indicator computation: ~0.1–1ms. ✅

### Repeated calculations

Within a single `weighted_adjust_prices` call:
- RSI is computed twice (once in the main gather, once in `dynamic_volatility_adjustment`) — but the second call hits the 60s cache. ✅
- OHLCV data is fetched once per exchange/symbol/timeframe and cached — all indicators for the same exchange share the cached data. ✅

**Finding — each indicator creates a new `pd.Series` from the same OHLCV data:** `get_rsi`, `get_stoch_rsi`, `get_market_direction`, and `get_macd` all independently create `pd.Series([x[4] for x in ohlcv])` from the same cached OHLCV list. For 45 candles, this is 4 × 45 list comprehensions + 4 Series constructions. Total overhead: ~20 microseconds. Negligible for current scale, but could be eliminated by caching the Series alongside the OHLCV data.

### Unnecessary copies

No unnecessary DataFrame copies detected. `pd.Series` is created once per indicator call and not copied. ✅

### Pandas vectorization

All pandas-ta functions are vectorized internally. The custom `get_short_term_market_trend` and `get_price_change` use pure Python list comprehensions over 3–10 elements — vectorization would add overhead for such small datasets. ✅

### Inefficient loops

**Finding — `get_trade_dynamic_spread_threshold_avg` has two separate loops over the same order book data:**

```python
trade_spread_sum = sum(
    (ask_price - bid_price) * min(ask_volume, bid_volume)
    for (bid_price, bid_volume) in buy_order_book['bids'][:10]
    for (ask_price, ask_volume) in sell_order_book['asks'][:10]
)
```

This is an O(n²) cross-product (10 × 10 = 100 iterations). The comment in the code notes this was previously worse and was partially optimised. The `avg_bid` and `avg_ask` computation is a separate O(n) loop over the same data. Both loops could be combined into one pass. For 10 entries each, this is 110 iterations total — negligible in absolute terms but algorithmically suboptimal.

---

## 4. Indicator Calculation Performance

### Computational cost per indicator

| Indicator | Input size | pandas-ta cost | Total per call |
|---|---|---|---|
| RSI(14) | 16 candles | ~0.1ms | ~0.2ms (incl. Series creation) |
| StochRSI(14,14,3,3) | 32 candles | ~0.3ms | ~0.5ms |
| SMA(14) direction | 16 candles | ~0.05ms | ~0.1ms |
| MACD(12,26,9) | 45 candles | ~0.5ms | ~0.8ms |
| Short-term trend | 6 candles | ~0.01ms (pure Python) | ~0.02ms |
| Volatility | Order book (~20 entries) | ~0.05ms (numpy std) | ~0.1ms |
| Support/resistance | 24 candles | ~0.01ms (min/max) | ~0.02ms |

**Total indicator pipeline per trade combination: ~2–5ms** (excluding network I/O, which is cached).

### Recalculation frequency

With 60s indicator cache TTL and 6–18s cycle sleep:
- Indicators are recomputed at most once per 60s per exchange/symbol.
- Within a 60s window, all cycles use cached values.
- At scale (10 bots × 5 symbols × 3 exchanges), the cache holds 150 indicator entries — well within the 500-entry cap. ✅

### Caching gaps

Four indicator functions lack result caches (identified in Prompt 05):
- `get_short_term_market_trend` — 6-candle computation, ~0.02ms, OHLCV cached
- `get_volatility` — numpy std on order book, ~0.1ms, order book cached
- `get_support_price` — min over 24 candles, ~0.02ms, OHLCV cached
- `get_resistance_price` — max over 24 candles, ~0.02ms, OHLCV cached

Total uncached computation per cycle: ~0.16ms. Negligible for current scale. At 100 bots × 10 symbols, this becomes ~160ms of CPU per cycle — still acceptable but worth caching for consistency.


---

## 5. Memory Usage Analysis

### Per-bot memory footprint (estimated)

| Component | Memory | Notes |
|---|---|---|
| Python interpreter + asyncio event loop | ~30–50 MB | Base overhead |
| ccxtpro exchange instances (2 exchanges) | ~5–10 MB | WebSocket connection state, market data |
| OHLCV cache (500 entries × 45 candles × 6 floats) | ~1 MB | `_ohlcv_cache` |
| Order book cache (500 entries × ~40 levels × 2 floats) | ~0.3 MB | `_order_book_cache` |
| Ticker cache (500 entries) | ~0.1 MB | `_ticker_cache` |
| Indicator cache (500 entries) | ~0.05 MB | `_indicator_cache` |
| SQLite connection (WAL mode) | ~1–2 MB | Per connection, shared across threads |
| pandas + numpy (loaded) | ~50–80 MB | Library overhead, loaded once |
| pandas-ta (loaded) | ~20–30 MB | Library overhead |
| Trade tasks (up to 10 active) | ~0.1 MB | Coroutine stack frames |
| **Total estimated per bot** | **~110–175 MB** | Dominated by pandas/numpy library load |

**Finding — pandas and numpy are loaded once per process, not per bot:** The ~50–80 MB pandas + ~20–30 MB numpy overhead is a one-time process cost. For a process running 10 bots, the per-bot marginal cost is much lower (~10–20 MB). The library overhead is amortised across all bots in the same process. ✅

### Memory growth over time

| Source | Growth rate | Bound |
|---|---|---|
| OHLCV cache | Grows to 500 entries, then LRU eviction | Bounded ✅ |
| Order book cache | Same | Bounded ✅ |
| Indicator cache | Same | Bounded ✅ |
| `trade_tasks` list | Grows between monitor cycles (1s) | Bounded by `_MAX_CONCURRENT_TRADES` ✅ |
| `errors_history.json` | Unbounded file growth | Unbounded ⚠️ |
| `balance_history.json` | Unbounded file growth | Unbounded ⚠️ |
| SQLite DB | Bounded by `purge_history(keep_last=10,000)` | Bounded ✅ |
| DB backup files | One file per day, never deleted | Unbounded ⚠️ |
| `previous_spread` dict in `SonarftIndicators` | One entry per exchange/symbol | Bounded by config ✅ |

**Finding — `_append_json` reads entire file into memory on every write:** `errors_history.json` and `balance_history.json` are read fully into memory, appended, and rewritten on every call. For a 10 MB file, this is a 10 MB memory spike per write. Under sustained error conditions (e.g. exchange API down), `save_error` is called frequently, causing repeated large memory allocations.

### DataFrame memory

Each indicator call creates a `pd.Series` of 14–45 floats (~0.4–1.4 KB). These are local variables and are garbage-collected after the function returns. No persistent DataFrame state. ✅

---

## 6. Bottleneck Identification

### Critical path per cycle

```
search_trades()                                    [~0ms — gate checks]
  └─ process_symbol()                              [~0ms — price fetch dispatch]
        └─ get_latest_prices()                     [~50–200ms — network I/O, cached after first]
        └─ process_trade_combination() × N pairs   [parallel via gather]
              └─ weighted_adjust_prices()          [~50–200ms — 14 indicator fetches, 30s timeout]
              └─ calculate_trade()                 [~0.1ms — Decimal arithmetic]
              └─ has_requirements_for_success()    [~50–200ms — liquidity + spread checks]
              └─ execute_trade() [fire-and-forget] [~0ms — task dispatch]
```

**Dominant cost: network I/O** — all significant latency comes from exchange API calls. On cache hit, the cycle completes in < 10ms. On cache miss, it depends on exchange response time (typically 50–500ms per call).

### Bottleneck table

| Bottleneck | Location | Frequency | Impact | Potential Improvement |
|---|---|---|---|---|
| `monitor_order` polling (1s × 300s) | `sonarft_execution.py` | Per live trade | Holds task for up to 300s; 300 API calls | Use WebSocket order updates instead of polling |
| `monitor_price` polling (3s × 120s) | `sonarft_execution.py` | Per live trade | Holds task for up to 120s; 40 API calls | Reduce polling interval or use WebSocket ticker |
| `watch_orders` REST polling in ccxt mode | `sonarft_api_manager.py` | Every 1s during monitor_order | Up to 300 REST calls per order | Use ccxtpro WebSocket mode |
| OHLCV cache miss (60s expiry) | `sonarft_api_manager.py` | Every 60s | 4–8 API calls per miss | Batch all indicator OHLCV into one fetch |
| `load_configurations` blocking file I/O | `sonarft_bot.py` | Once at startup | Blocks event loop briefly | Wrap in `asyncio.to_thread` |
| `_init_db` blocking SQLite in constructor | `sonarft_helpers.py` | Once at startup | Blocks event loop briefly | Move to async init |
| `_append_json` read-modify-write | `sonarft_helpers.py` | Per error/balance save | Memory spike for large files | Migrate to SQLite |
| pandas-ta on event loop | `sonarft_indicators.py` | Every 60s per indicator | ~2–5ms CPU per cycle | Wrap in `asyncio.to_thread` at scale |

### Sequential work that could parallelise

**Finding — `get_latest_prices` and `weighted_adjust_prices` are sequential per pair:** In `process_trade_combination`, `get_latest_prices` is called first (in `process_symbol`), then `weighted_adjust_prices` is called for each pair. The price fetch and indicator fetch are sequential. They could be parallelised — start fetching indicators while the price list is being sorted.

**Finding — liquidity validation is sequential after profit check:** `has_requirements_for_success_carrying_out` runs after the profit threshold check. The two liquidity checks inside it run concurrently (`asyncio.gather`), but the spread threshold check runs after both liquidity checks complete. All three could run concurrently since they are independent.

---

## 7. Concurrency & Scaling

### Multi-bot concurrency

Multiple `SonarftBot` instances can run concurrently in the same process under `BotManager`. Each bot has its own:
- `SonarftApiManager` instance (separate exchange connections)
- `SonarftSearch`, `TradeProcessor`, `TradeExecutor` instances
- `SonarftHelpers` instance (but shared SQLite DB file)
- Indicator and API caches (not shared between bots)

**Finding — caches are not shared between bots:** Each bot maintains its own `_ohlcv_cache`, `_order_book_cache`, `_ticker_cache`, and `_indicator_cache`. Two bots trading the same symbol on the same exchange will each fetch OHLCV data independently (after cache expiry). For N bots trading the same symbol, API call volume scales linearly with N. A shared process-level cache would reduce this to O(1) regardless of bot count.

**Finding — SQLite DB is shared between all bots:** All bots write to the same `sonarft.db`. WAL mode allows concurrent reads and serialises writes. Under high trade frequency with many bots, SQLite write contention could become a bottleneck. For > 10 bots with high trade frequency, consider per-bot database files or a proper database server.

### Multi-symbol scaling

Within a single bot, symbols are processed concurrently via `asyncio.gather` in `search_trades`. Adding more symbols increases the number of concurrent indicator fetches but all share the same caches. Linear scaling up to the cache cap (500 entries). ✅

### CPU vs I/O bound

The bot is **I/O bound** — the dominant cost is exchange API latency (50–500ms per call). CPU usage (pandas-ta, Decimal arithmetic) is < 10ms per cycle. Adding more CPU cores provides no benefit for a single bot. Multiple bots benefit from multiple cores only if pandas-ta computations become significant (> 10 bots × 10 symbols).

### Scalability limits

| Dimension | Current limit | Bottleneck |
|---|---|---|
| Bots per process | ~10–20 (practical) | Shared event loop; pandas memory overhead |
| Symbols per bot | ~10–20 (practical) | 14 concurrent indicator fetches × symbols |
| Exchanges per bot | ~5 (practical) | Exchange connection overhead; rate limits |
| Concurrent trades | 10 (configurable) | `_MAX_CONCURRENT_TRADES` |
| API calls/second | Exchange-dependent | ccxt rate limiter |

**Finding — all bots share a single asyncio event loop:** Python's asyncio is single-threaded. All bots in the same process share one event loop. Under high load (many bots, many symbols), long-running coroutines (monitor_order: 300s, monitor_price: 120s) can delay other coroutines. For > 5 bots, consider running each bot in a separate process with `multiprocessing`.

---

## 8. Cache & Optimization Opportunities

### High-impact opportunities

**Opportunity 1 — Batch OHLCV fetch for all indicators:**

Currently, each indicator independently calls `get_history` with its required limit. The OHLCV cache deduplicates by key, but different limits for the same exchange/symbol/timeframe can cause cache misses. A single fetch of `max(all_required_limits)` candles at the start of each cycle would guarantee all indicators use the same cached data:

```python
await api_manager.get_ohlcv_history(exchange, base, quote, '1m', None, 45)
```

This would reduce OHLCV fetches from potentially 4 per exchange/symbol to 1.

**Opportunity 2 — Shared process-level cache for multi-bot deployments:**

Replace per-bot `SonarftApiManager` caches with a shared `asyncio`-safe cache (e.g. `cachetools.TTLCache` with a lock). All bots trading the same symbol share one OHLCV fetch per TTL window instead of N fetches.

**Opportunity 3 — Replace `monitor_order` polling with WebSocket order updates:**

In ccxtpro mode, `watch_orders` returns on the next WebSocket order update rather than polling. The current implementation calls `watch_orders` every 1 second regardless. Restructuring to await a single `watch_orders` call (which blocks until an update arrives) would eliminate the polling loop entirely and reduce API calls from 300 to ~1–5 per order.

### Medium-impact opportunities

**Opportunity 4 — Cache `pd.Series` alongside OHLCV data:**

Store the close price Series in the OHLCV cache alongside the raw data. All indicators for the same exchange/symbol/timeframe reuse the same Series object instead of creating 4 independent copies.

**Opportunity 5 — Add 60s TTL cache to the 4 uncached indicator functions:**

`get_short_term_market_trend`, `get_volatility`, `get_support_price`, `get_resistance_price` — consistent with the rest of the indicator pipeline.

**Opportunity 6 — Parallelise liquidity + spread checks:**

```python
result_01, result_02, spread_ok = await asyncio.gather(
    sonarft_validators.deeper_verify_liquidity(buy_exchange, ...),
    sonarft_validators.deeper_verify_liquidity(sell_exchange, ...),
    sonarft_validators.verify_spread_threshold(...),
)
```

Currently spread check runs after both liquidity checks. All three are independent and can run concurrently.

---

## 9. Latency Analysis

### Per-operation latency

| Operation | Typical latency | Acceptable? | Notes |
|---|---|---|---|
| OHLCV fetch (cache hit) | < 1ms | ✅ | Dict lookup |
| OHLCV fetch (cache miss) | 50–500ms | ✅ | Exchange-dependent |
| Order book fetch (cache hit) | < 1ms | ✅ | Dict lookup |
| Order book fetch (cache miss) | 20–200ms | ✅ | WebSocket update |
| RSI computation | ~0.2ms | ✅ | pandas-ta on 16 candles |
| StochRSI computation | ~0.5ms | ✅ | pandas-ta on 32 candles |
| MACD computation | ~0.8ms | ✅ | pandas-ta on 45 candles |
| `calculate_trade` (Decimal) | ~0.1ms | ✅ | 28-digit arithmetic |
| Full indicator pipeline (warm cache) | ~5–10ms | ✅ | 14 concurrent fetches |
| Full cycle (warm cache, no trade) | ~10–50ms | ✅ | Well within 6–18s sleep |
| `monitor_price` (live mode) | 0–120s | ⚠️ | Waits for favourable price |
| `monitor_order` (live mode) | 0–300s | ⚠️ | Waits for fill |
| SQLite write (order history) | ~1–5ms | ✅ | Via `asyncio.to_thread` |
| SQLite write (daily loss) | ~1–5ms | ✅ | Via `asyncio.to_thread` |

**Finding — `monitor_price` + `monitor_order` chain (up to 420s) is the dominant latency source in live mode:** A single trade task can hold an async task for up to 7 minutes. With `_MAX_CONCURRENT_TRADES=10`, up to 70 minutes of cumulative task time can be in-flight simultaneously. This is by design but means the event loop must remain responsive for other coroutines during this period. Since all waits use `asyncio.sleep`, the event loop is not blocked. ✅

### Cycle latency budget

```
Cycle sleep:          6–18s
Indicator pipeline:   ~10–50ms (warm cache)
Price fetch:          ~20–200ms (warm cache)
Liquidity checks:     ~20–200ms (order book cached)
Spread check:         ~50–500ms (OHLCV + order book)
Total active work:    ~100–950ms per cycle
Remaining budget:     ~5–17s (well within sleep window)
```

The bot has ample latency budget for current configuration. ✅


---

## 10. Resource Usage Summary

### Single bot, default config (2 exchanges, 1 symbol, simulation mode)

| Resource | Idle | Active cycle | Peak (cold cache) | Limit | Headroom |
|---|---|---|---|---|---|
| CPU % | < 1% | 1–3% | 5–10% | 100% (1 core) | High ✅ |
| Memory (RSS) | ~120–150 MB | ~130–160 MB | ~160–180 MB | OS-dependent | High ✅ |
| Disk writes/hour | ~0 | ~1–5 MB/h (SQLite WAL) | ~10 MB/h | Disk capacity | High ✅ |
| API calls/minute | 0 | 2–8 (warm cache) | 20–40 (cold cache) | Exchange rate limit | High ✅ |
| Open file handles | ~5 | ~5–10 | ~15 | OS ulimit (~1024) | High ✅ |
| SQLite connections | 1 | 1–3 (to_thread) | 5 | SQLite WAL limit | High ✅ |

### Multi-bot scaling (N bots, same symbol)

| N bots | Memory | API calls/min | CPU % | Notes |
|---|---|---|---|---|
| 1 | ~150 MB | 2–8 | 1–3% | Baseline |
| 5 | ~350 MB | 10–40 | 5–15% | Caches not shared |
| 10 | ~600 MB | 20–80 | 10–30% | Approaching practical limit |
| 20 | ~1.1 GB | 40–160 | 20–60% | Likely needs multi-process |

**Finding — memory scales linearly with bot count due to unshared caches:** Each bot loads its own pandas/numpy (amortised after first bot) and maintains its own caches. The marginal cost per additional bot is ~30–50 MB (caches + exchange instances). For 20 bots, total memory approaches 1 GB — manageable on a modern server but worth monitoring.

---

## 11. Load Testing Recommendations

### Test scenarios

| Scenario | Purpose | Key metrics |
|---|---|---|
| Single bot, 1 symbol, warm cache | Baseline cycle latency | Cycle time, CPU %, memory |
| Single bot, 10 symbols, warm cache | Symbol scaling | Cycle time vs symbol count |
| 10 bots, 1 symbol each | Multi-bot concurrency | Memory, API calls/min, event loop lag |
| Single bot, cold cache (first cycle) | Startup performance | Time to first trade signal |
| Single bot, 10 concurrent trades (live sim) | Execution concurrency | Task queue depth, event loop lag |
| Single bot, 300s monitor_order × 10 | Max concurrent task load | Memory, event loop responsiveness |
| Error injection (exchange timeout) | Circuit breaker | Time to halt, alert delivery |
| Hot-reload under load | Parameter update safety | No trade interruption, rollback correctness |

### Metrics to measure

- **Cycle time** (ms): time from `search_trades` entry to exit
- **Event loop lag** (ms): time between `asyncio.sleep(0)` yield and resume
- **Memory RSS** (MB): resident set size over time
- **API calls/minute**: per exchange, per method
- **Cache hit rate** (%) per cache type
- **Task queue depth**: active trade tasks at any point
- **SQLite write latency** (ms): `asyncio.to_thread` overhead

### Tools

- `asyncio` debug mode (`PYTHONASYNCIODEBUG=1`) — logs slow callbacks (> 100ms)
- `tracemalloc` — memory allocation tracing
- `cProfile` / `py-spy` — CPU profiling
- `sqlite3` `EXPLAIN QUERY PLAN` — query performance
- Exchange sandbox/testnet — live mode load testing without real funds

### Acceptable thresholds

| Metric | Acceptable | Warning | Critical |
|---|---|---|---|
| Cycle time (warm cache) | < 500ms | 500ms–2s | > 2s |
| Event loop lag | < 50ms | 50–200ms | > 200ms |
| Memory per bot | < 200 MB | 200–400 MB | > 400 MB |
| API calls/min (per exchange) | < 20 | 20–50 | > 50 |
| Cache hit rate (OHLCV) | > 80% | 60–80% | < 60% |

---

## 12. Performance Optimization Roadmap

| Optimization | Effort | Impact | Priority |
|---|---|---|---|
| Replace `monitor_order` polling with WebSocket order updates | High | High — eliminates 300 REST calls per order | High |
| Shared process-level OHLCV/order book cache for multi-bot | Medium | High — eliminates N× duplicate fetches | High |
| Batch OHLCV fetch (one fetch per exchange/symbol/timeframe per cycle) | Low | Medium — reduces cache misses | Medium |
| Add 60s TTL cache to 4 uncached indicator functions | Low | Low — ~0.16ms saved per cycle | Low |
| Parallelise liquidity + spread checks in `TradeValidator` | Low | Low — saves ~50–500ms per trade signal | Low |
| Cache `pd.Series` alongside OHLCV data | Low | Low — saves ~20μs per indicator call | Low |
| Migrate `errors_history.json` to SQLite | Low | Medium — eliminates memory spikes on error | Medium |
| Run bots in separate processes for > 10 bots | High | High — eliminates event loop contention | High (at scale) |
| Wrap pandas-ta in `asyncio.to_thread` | Medium | Low (current scale) / High (> 10 bots × 10 symbols) | Low now, Medium at scale |
| Reduce `monitor_order` polling interval from 1s to 2s | Low | Low — halves REST calls during monitoring | Low |

---

## 13. Conclusion

### Performance assessment

The bot is **well-optimised for its current scale** (1–5 bots, 1–3 symbols, 2–3 exchanges). The caching strategy is sound — OHLCV (60s TTL), order book (2s TTL), and indicator (60s TTL) caches eliminate the vast majority of redundant API calls. The async architecture correctly parallelises all independent fetches. The cycle latency budget (100–950ms active work vs 6–18s sleep) provides ample headroom.

### Critical bottlenecks

1. **`monitor_order` REST polling (300 calls/order):** In ccxt REST mode, this is the dominant API cost during live trading. Switching to ccxtpro WebSocket mode eliminates this entirely.

2. **Unshared caches in multi-bot deployments:** API call volume scales linearly with bot count. A shared process-level cache would make multi-bot deployments O(1) in API calls for the same symbol.

3. **Single asyncio event loop for all bots:** At > 10 bots, the shared event loop becomes a contention point. Multi-process deployment is the correct solution at that scale.

### Optimization recommendations (priority order)

1. **High:** Use ccxtpro WebSocket mode (already the default) and restructure `monitor_order` to await WebSocket updates rather than polling every 1s.
2. **High:** Implement shared process-level cache before scaling beyond 5 bots on the same symbol.
3. **Medium:** Batch OHLCV fetch to one call per exchange/symbol/timeframe per cycle.
4. **Medium:** Migrate `errors_history.json` to SQLite to eliminate memory spikes.
5. **Low:** Add result caches to the 4 uncached indicator functions for consistency.
6. **Low (future):** Multi-process bot deployment for > 10 bots.
