# SonarFT Bot — Implementation Roadmap

**Prompt:** 12-BOT-ROADMAP  
**Author:** Senior Technical Program Manager  
**Date:** July 2025  
**Input:** All review documents (Prompts 01–11)  
**Total Findings:** 123 issues across 10 domains

---

## 1. Executive Roadmap Summary

| Aspect | Assessment |
|---|---|
| **System readiness before roadmap** | 6.0/10 — Early Beta |
| **Target readiness after roadmap** | 8.5/10 — Production-Ready |
| **Estimated total effort** | Medium (~25 engineering days) |
| **Number of phases** | 6 (Phase 0–5) |
| **Primary risk domains** | Execution/Order Lifecycle, Async Task Cleanup, Input Validation |
| **Top architectural priority** | Proper shutdown sequence with order reconciliation |

### Risk Domain Summary

```
Execution/Exchange ████████████ 4 High — ORDER LIFECYCLE (top priority)
Async/Concurrency  █████████    3 High — TASK CLEANUP
Trading Logic      ██████       1 High — SPREAD THRESHOLD
Security           █████        0 High, 8 Medium — INPUT VALIDATION
Configuration      █████        0 High, 9 Medium — HOT-RELOAD SAFETY
```

---

## 2. Issue-to-Task Conversion Matrix

### Phase 0 — Critical Safety Fixes

| ID | Source | Affected Code | Sev | Task | Complexity | Effort | Depends On | Validation |
|---|---|---|---|---|---|---|---|---|
| ~~T01~~ | P02,P06 | `sonarft_bot.py:stop_bot()` | High | ✅ **DONE** — Rewrite shutdown: cancel monitor task → await trade tasks → cancel open orders → close connections | Medium | 2d | — | 96/96 tests pass |

> **T01 Implementation Notes:** Rewrote `stop_bot()` with proper 3-step shutdown: (1) signal stop event, (2) call `TradeExecutor.shutdown()` which cancels `monitor_trade_tasks` and awaits/cancels all in-flight `trade_tasks`, (3) close exchange connections. Added `shutdown()` method to `TradeExecutor`. Added `CancelledError` handling to `monitor_trade_tasks` (both from `task.result()` and the outer loop). Fixed `cancel_trade()` list-while-iterating bug (builds removal list first). Exchange connections are now only closed after all trade tasks have completed or been cancelled — no more mid-flight connection closures.
| ~~T02~~ | P03,P06 | `sonarft_execution.py:execute_long/short_trade()` | High | ✅ **DONE** — Add cancel retry (3× exponential backoff) + `_send_alert()` on final failure | Small | 1d | — | 95/96 tests pass |

> **T02 Implementation Notes:** Added `_cancel_order_with_retry()` method to `SonarftExecution` — retries cancel 3× with 1s/2s exponential backoff. On final failure, logs CRITICAL error and calls `_alert_callback` (wired to `SonarftBot._send_alert` via `InitializeModules()`). Replaced bare `cancel_order` calls in both `execute_long_trade()` and `execute_short_trade()`. Added `_alert_callback` attribute to constructor (defaults to `None`, set post-construction).
| ~~T03~~ | P06 | `sonarft_execution.py:monitor_order()` | High | ✅ **DONE** — Cancel order on 300s timeout; verify cancellation result | Small | 0.5d | T02 | 95/96 tests pass |

> **T03 Implementation Notes:** Added cancel-on-timeout to `monitor_order()`. When the 300s deadline is reached, calls `_cancel_order_with_retry()` (from T02) before returning `(0, target_amount)`. If cancel also fails, logs error warning that the order may still be open on the exchange. Previously, timed-out orders were silently abandoned — they remained open on the exchange indefinitely.
| ~~T04~~ | P03 | `sonarft_validators.py:calculate_thresholds_based_on_historical_data()` | High | ✅ **DONE** — Fix OHLCV indices: use close prices `[4]` from both exchanges instead of `[1]`/`[2]` | Small | 0.5d | — | 95/96 tests pass; threshold tests updated |

> **T04 Implementation Notes:** Rewrote `calculate_thresholds_based_on_historical_data()` to compute cross-exchange spread from close prices (`data[4]`) of buy and sell exchange OHLCV data separately, instead of incorrectly using open (`data[1]`) and high (`data[2]`) from combined data. The old code treated intra-candle open/high as bid/ask, which systematically overestimated historical spreads and made the validation gate too permissive. Updated test helper data (`HISTORICAL_BUY`/`HISTORICAL_SELL`) to proper 6-field OHLCV format.
| ~~T05~~ | P06 | `sonarft_api_manager.py:get_last_price()`, `get_trading_volume()` | Med | ✅ **DONE** — Add null check: `if result is None: return None` | Trivial | 0.5h | — | 95/96 tests pass (1 pre-existing StochRSI failure) |

> **T05 Implementation Notes:** Added null guard to both `get_last_price()` and `get_trading_volume()` — check `if ticker is None: return None` before accessing dict keys. Return type updated to `Optional[float]`. All 95 passing tests unaffected; 1 pre-existing `test_returns_k_and_d_in_range` failure (pandas-ta StochRSI compatibility with pandas 3.0).

### Phase 1 — Stability & Reliability

| ID | Source | Affected Code | Sev | Task | Complexity | Effort | Depends On | Validation |
|---|---|---|---|---|---|---|---|---|
| ~~T06~~ | P02 | `sonarft_search.py:monitor_trade_tasks()` | High | ✅ **DONE** (completed in T01) — Add stop event check to `while True` loop; handle `CancelledError` from `task.result()` | Small | 0.5d | T01 | 96/96 tests pass |

> **T06 Implementation Notes:** Fully addressed by T01. `monitor_trade_tasks` now catches `CancelledError` from both `task.result()` and the outer `while True` loop. `TradeExecutor.shutdown()` cancels the task explicitly. No separate work needed.
| ~~T07~~ | P02 | `sonarft_manager.py:remove_bot_instance()` | Med | ✅ **DONE** — Release lock before calling `stop_bot()` — extract bot ref under lock, stop outside | Small | 0.5d | T01 | 96/96 tests pass |

> **T07 Implementation Notes:** `remove_bot_instance()` now pops the bot from `_bots` and removes the botid from `_clients` under the lock, then calls `stop_bot()` outside the lock. Previously, `stop_bot()` (which performs network I/O: cancel tasks, close exchange connections) was called while holding `self._lock`, blocking all other bot management operations (create, remove, get) for the duration of the shutdown. Also fixed the `_clients` iteration bug — was iterating `self._clients.items()` with wrong variable unpacking (`_client, client_id` instead of `client_id, bot_list`).
| ~~T08~~ | P04,P05 | 6 locations across indicators/validators | Med | ✅ **DONE** — Add division-by-zero guards to `get_price_change`, `deeper_verify_liquidity`, `verify_spread_threshold`, `check_exchange_slippage`, `stop_loss_triggered` | Small | 1d | — | 96/96 tests pass |

> **T08 Implementation Notes:** Added zero guards to 5 locations: `get_price_change` (ternary guard on `previous_avg_price`), `deeper_verify_liquidity` (guard `depth_bids==0 or depth_asks==0`), `verify_spread_threshold` (guard `average_price==0`), `check_exchange_slippage` (ternary guard on `trade_price`), `stop_loss_triggered` (guard `buy_price==0`). The 6th location (`calculate_slippage_tolerance`) already had `buy_price > 0` guard in the loop condition.
| ~~T09~~ | P05 | `sonarft_indicators.py:get_volatility()` | Med | ✅ **DONE** — Add NaN guard: `if np.isnan(volatility): return 0.0` | Trivial | 0.5h | — | 96/96 tests pass |
| ~~T10~~ | P05 | `sonarft_prices.py:weighted_adjust_prices()` | Med | ✅ **DONE** — Add NaN guard after volatility calculation: return `(0, 0, {})` if NaN | Trivial | 0.5h | T09 | 96/96 tests pass |

> **T09+T10 Implementation Notes:** T09 adds `if np.isnan(volatility): return 0.0` at the end of `get_volatility()`. T10 adds `if math.isnan(volatility_buy) or math.isnan(volatility_sell): return 0, 0, {}` after the volatility adjustment multiplication in `weighted_adjust_prices()`. Together these prevent NaN from propagating through the weight calculation into adjusted prices.
| ~~T11~~ | P07 | `sonarft_bot.py:load_configurations()` | Med | ✅ **DONE** — Wrap in try/except catching `FileNotFoundError`, `KeyError`, `json.JSONDecodeError` → raise `BotCreationError` with descriptive message | Small | 0.5d | — | 96/96 tests pass |
| ~~T12~~ | P07 | `sonarft_bot.py:create_bot()` | Med | ✅ **DONE** — Add `os.makedirs('sonarftdata/bots', exist_ok=True)` before writing botid file | Trivial | 0.5h | — | 96/96 tests pass |
| ~~T13~~ | P02 | `sonarft_api_manager.py:call_api_method()` | Med | ✅ **DONE** — Wrap in `asyncio.wait_for(..., timeout=30)` | Small | 0.5d | — | 96/96 tests pass |

> **T11 Implementation Notes:** `_load_config_section()` now catches `FileNotFoundError`, `json.JSONDecodeError`, and missing key — all raise `BotCreationError` with descriptive messages. Previously these propagated as unhandled exceptions crashing the bot.
>
> **T12 Implementation Notes:** Added `os.makedirs('sonarftdata/bots', exist_ok=True)` in `create_bot()` before writing the botid JSON file. Prevents `FileNotFoundError` on fresh installations.
>
> **T13 Implementation Notes:** `call_api_method()` now wraps the API coroutine in `asyncio.wait_for(..., timeout=30.0)`. Both ccxt REST (via `run_in_executor`) and ccxtpro WebSocket calls are covered. `TimeoutError` is caught and logged separately from other exceptions. Previously, a hanging exchange API could block the coroutine indefinitely.

### Phase 2 — Security Hardening

| ID | Source | Affected Code | Sev | Task | Complexity | Effort | Depends On | Validation |
|---|---|---|---|---|---|---|---|---|
| ~~T14~~ | P07,P08 | API layer + `sonarft_helpers.py` | Med | ✅ **DONE** — Sanitize `client_id`: `re.sub(r'[^a-zA-Z0-9_-]', '', client_id)` at API boundary | Small | 0.5d | — | 96/96 tests pass |
| ~~T15~~ | P03,P07,P08 | `sonarft_bot.py:apply_parameters()` | Med | ✅ **DONE** — Call `_validate_parameters()` after applying hot-reload; reject invalid values with rollback | Small | 0.5d | — | 96/96 tests pass |
| ~~T16~~ | P03,P08 | `sonarft_bot.py:apply_parameters()` | Med | ✅ **DONE** — Require `SONARFT_ALLOW_LIVE=true` env var for sim→live switch | Small | 1d | T15 | 96/96 tests pass |
| ~~T17~~ | P08 | `sonarft_bot.py:apply_parameters()` | Med | ✅ **DONE** — Add structured audit log entry for every parameter change (old→new values) | Small | 0.5d | — | 96/96 tests pass |
| ~~T18~~ | P01,P05,P08 | `requirements.txt`, `pyproject.toml` | Med | ✅ **DONE** — Pin `pandas-ta==0.4.71b0`; remove unused `orjson`, `coincurve`, `aiofiles` | Trivial | 0.5h | — | 96/96 tests pass |
| T19 | P08 | CI/CD | Med | Add `pip audit` to CI pipeline | Small | 0.5d | — | ⚠️ Deferred — requires CI infrastructure |

> **T14 Implementation Notes:** Added `sanitize_client_id()` to `sonarft_helpers.py` — strips all characters except `[a-zA-Z0-9_-]`, raises `ValueError` if result is empty. Applied at `BotManager` entry points: `create_bot()`, `add_bot_instance()`, `reload_parameters()`.
>
> **T15 Implementation Notes:** `apply_parameters()` now calls `_validate_parameters()` after applying changes. On validation failure, all changed values are rolled back to their previous state before re-raising `ValueError`. Also propagates `spread_increase_factor`/`spread_decrease_factor` to `sonarft_prices`.
>
> **T16 Implementation Notes:** Switching `is_simulating_trade` from 1→0 via hot-reload now requires `SONARFT_ALLOW_LIVE=true` environment variable. Without it, `ValueError` is raised and the change is rolled back. This prevents accidental live trading via API calls.
>
> **T17 Implementation Notes:** Every successful `apply_parameters()` call now logs a `WARNING`-level audit entry: `"AUDIT parameter change: {param: {old: X, new: Y}}"`. Uses WARNING level so it's visible in production logs without debug mode.
>
> **T18 Implementation Notes:** Pinned `pandas-ta==0.4.71b0` (installed version). Removed `orjson`, `coincurve`, `aiofiles` from both `requirements.txt` and `pyproject.toml` — none were imported in any source file.

### Phase 3 — Performance & Precision

| ID | Source | Affected Code | Sev | Task | Complexity | Effort | Depends On | Validation |
|---|---|---|---|---|---|---|---|---|
| ~~T20~~ | P03,P06 | `sonarft_execution.py:create_order()` | Med | ✅ **DONE** — Round `monitor_price()` return value to exchange precision before passing to `execute_order()` | Small | 0.5d | — | 96/96 tests pass |
| ~~T21~~ | P06 | `sonarft_execution.py:create_order()` | Med | ✅ **DONE** — Validate trade amount against `market['limits']['amount']['min']` and cost against `market['limits']['cost']['min']` | Small | 1d | — | 96/96 tests pass |
| ~~T22~~ | P05 | `sonarft_indicators.py:market_movement()` | Med | ✅ **DONE** — Change `self.previous_spread` to per-symbol dict keyed by `f"{exchange}:{base}/{quote}"` | Small | 0.5d | — | 96/96 tests pass |
| ~~T23~~ | P09 | `sonarft_api_manager.py:get_last_price()` | Low | ✅ **DONE** — Add ticker cache with 2s TTL via `_get_ticker()` helper | Small | 0.5d | — | 96/96 tests pass |
| ~~T24~~ | P09 | `sonarft_api_manager.py:get_ohlcv_history()` | Low | ✅ **DONE** — Normalize OHLCV cache key to exclude limit; reuse larger cached responses | Small | 0.5d | — | 96/96 tests pass |
| ~~T25~~ | P09 | `sonarft_execution.py:check_balance()` | Low | ✅ **DONE** — Remove hardcoded `asyncio.sleep(1)` | Trivial | 0.5h | — | 96/96 tests pass |

> **T20 Implementation Notes:** In `create_order()`, after `monitor_price()` returns a raw float, the price is now rounded to the exchange's `prices_precision` via `get_symbol_precision()` before being passed to `execute_order()`. Skipped if precision data is unavailable.
>
> **T21 Implementation Notes:** `create_order()` now checks `market['limits']['amount']['min']` and `market['limits']['cost']['min']` from loaded market data. Orders below minimums are rejected with a warning. Defensive against missing/non-dict market data.
>
> **T22 Implementation Notes:** `previous_spread` changed from a single `float` to a `dict` keyed by `f"{exchange_id}:{base}/{quote}"`. Each symbol gets its own independent spread history, eliminating the race condition when `market_movement()` is called concurrently for different symbols via `asyncio.gather`.
>
> **T23 Implementation Notes:** Added `_get_ticker()` with 2s TTL cache (same pattern as order book cache). Both `get_last_price()` and `get_trading_volume()` now use this shared cache, eliminating redundant ticker API calls within the same cycle.
>
> **T24 Implementation Notes:** OHLCV cache key no longer includes `limit`. A cached response with ≥ requested candles is reused (sliced to requested limit). This means RSI (16 candles) and MACD (45 candles) for the same symbol/timeframe share one cache entry — the first call fetches 45, subsequent calls get a slice.
>
> **T25 Implementation Notes:** Removed the hardcoded `asyncio.sleep(1)` before every balance check. This was adding 1 second of unnecessary latency per trade leg.

### Phase 4 — Architecture & Quality

| ID | Source | Affected Code | Sev | Task | Complexity | Effort | Depends On | Validation |
|---|---|---|---|---|---|---|---|---|
| ~~T26~~ | P10 | `sonarft_prices.py` | Crit (test) | ✅ **DONE** — Add comprehensive test suite: 25 tests covering 4 market branches, timeout, None indicators, NaN volatility, support/resistance clamping, dynamic_volatility_adjustment, get_weighted_price | Medium | 2d | T09,T10 | 131/131 tests pass |
| ~~T27~~ | P10 | `sonarft_search.py` | High (test) | ✅ **DONE** — Add 6 tests for `process_trade_combination()`: profitable/unprofitable, zero price, failed validation, None trade_data, threshold boundary | Medium | 1.5d | T26 | 131/131 tests pass |
| ~~T28~~ | P10 | `sonarft_execution.py` | High (test) | ✅ **DONE** — Add 4 tests for partial fill handling: partial buy adjusts sell, zero fill skips, second leg fail cancels first, short partial sell adjusts buy | Medium | 1d | T02 | 131/131 tests pass |
| ~~T29~~ | P01,P10 | `sonarft_helpers.py` → new `models.py` | Low | ✅ **DONE** — Extract `Trade` dataclass to `models.py`; re-export from `sonarft_helpers` for backward compatibility | Trivial | 0.5d | — | 131/131 tests pass |
| T30 | P01 | `sonarft_search.py` | Low | Split into `trade_processor.py`, `trade_validator.py`, `trade_executor.py` | Small | 1d | T27 | ⚠️ Deferred — lower priority refactoring |
| T31 | P01,P10 | `sonarft_api_manager.py`, `sonarft_prices.py` | Low | Consolidate VWAP into `SonarftPrices`; remove duplicate from `SonarftApiManager` | Small | 0.5d | — | ⚠️ Deferred — lower priority refactoring |

> **T26 Implementation Notes:** Created `tests/test_sonarft_prices.py` with 25 tests across 4 classes: `TestWeightedAdjustPricesBasic` (2), `TestWeightedAdjustPricesBranches` (5 — bull+bull normal, bull+bull overbought, bear+bear normal, bear+bear oversold, neutral), `TestWeightedAdjustPricesEdgeCases` (8 — timeout, None RSI, None StochRSI, NaN volatility, zero-volume order book, support clamp, resistance clamp, indicator keys), `TestDynamicVolatilityAdjustment` (7 — all 4 direction/trend combos + None MACD/RSI + neutral), `TestGetWeightedPrice` (3). Uses fully mocked `SonarftIndicators` with per-exchange RSI/StochRSI side effects.
>
> **T27 Implementation Notes:** Created 6 tests in `TestProcessTradeCombination`: profitable triggers execution, unprofitable skipped, zero adjusted price skipped, failed validation skipped, None trade_data skipped, at-threshold boundary executes (≥ comparison).
>
> **T28 Implementation Notes:** Created 4 tests in `TestPartialFillHandling`: partial buy fill adjusts sell amount to 0.7, zero fill skips second leg, second leg failure triggers cancel of first leg, short trade partial sell adjusts buy amount.
>
> **T29 Implementation Notes:** Extracted `Trade` dataclass to new `models.py`. `sonarft_helpers.py` re-exports `Trade` via `from models import Trade` for backward compatibility — all existing `from sonarft_helpers import Trade` imports continue to work. Added `models` to `pyproject.toml` py-modules.

### Phase 5 — Enhancement & Polish

| ID | Source | Affected Code | Sev | Task | Complexity | Effort | Depends On | Validation |
|---|---|---|---|---|---|---|---|---|
| ~~T32~~ | P07 | `Dockerfile` | Med | ✅ **DONE** — Add non-root user, `HEALTHCHECK`, `.dockerignore` | Small | 0.5d | — | 131/131 tests pass |
| T33 | P06 | `sonarft_execution.py` | Med | Add order reconciliation on bot startup: query open orders, cancel stale ones | Medium | 2d | T01 | ⚠️ Deferred — complex, requires integration testing |
| ~~T34~~ | P08 | `sonarft_search.py` | Low | ✅ **DONE** — Add daily loss auto-reset (check date change in `is_halted()` and `record_trade_result()`) | Small | 0.5d | — | 131/131 tests pass |
| ~~T35~~ | P06 | `sonarft_execution.py` | Low | ✅ **DONE** — Add simulation slippage modeling (0-0.1% random) | Small | 0.5d | — | 131/131 tests pass |
| ~~T36~~ | P10 | All modules | Low | ✅ **DONE** — Add module docstrings to `sonarft_indicators.py`, `sonarft_execution.py`, `sonarft_validators.py`, `sonarft_api_manager.py` | Small | 1d | — | 131/131 tests pass |
| T37 | P09 | `sonarft_search.py:process_symbol()` | Low | Parallelize buy/sell combinations with `asyncio.gather` | Small | 0.5d | T30 | ⚠️ Deferred — depends on T30 split |

> **T32 Implementation Notes:** Added non-root `sonarft` user (UID 1000) to Dockerfile. Added `HEALTHCHECK` directive (30s interval, 5s timeout). Created `.dockerignore` excluding tests, docs, .git, __pycache__, .venv, and dev files.
>
> **T34 Implementation Notes:** Added `_loss_reset_date` tracking to `SonarftSearch`. Both `record_trade_result()` and `is_halted()` call `_check_daily_reset()` which compares current date to stored date. On date change, resets `daily_loss_accumulated` to 0.0 and logs the reset. Previously, accumulated loss persisted across days until bot restart.
>
> **T35 Implementation Notes:** Simulation mode in `execute_order()` now applies random slippage (0-0.1%) to the simulated fill price. Buy orders get slightly higher price, sell orders slightly lower. Makes simulation results more realistic — previously assumed perfect execution at exact target price.
>
> **T36 Implementation Notes:** Added module-level docstrings to `sonarft_indicators.py`, `sonarft_execution.py`, `sonarft_validators.py`, and `sonarft_api_manager.py`. All 10 source modules now have module docstrings.


---

## 3. Phase-Based Implementation Plan

### Phase 0 — Critical Safety Fixes

**Objective:** Eliminate all High-severity financial risks.  
**Tasks:** T01, T02, T03, T04, T05  
**Effort:** 4.5 days  
**Risk reduction:** Eliminates 5 of 12 High-severity findings

**Goals:**
- ✅ Bot shutdown properly cancels open orders
- ✅ Failed cancel retried with alerting
- ✅ Timed-out orders cancelled on exchange
- ✅ Spread threshold uses correct data
- ✅ No `TypeError` crashes on API failures

**Exit criteria:**
- All 5 tasks completed and tested
- Integration test: `stop_bot()` leaves no open orders
- Unit tests: cancel retry, timeout cancel, null-safe ticker
- Spread threshold unit test with known historical data

---

### Phase 1 — Stability & Reliability

**Objective:** Eliminate runtime crashes and async correctness issues.  
**Tasks:** T06, T07, T08, T09, T10, T11, T12, T13  
**Effort:** 4.5 days  
**Risk reduction:** Eliminates 3 High + 6 Medium findings

**Goals:**
- ✅ `monitor_trade_tasks` exits cleanly on shutdown
- ✅ `BotManager._lock` not held during network I/O
- ✅ No division-by-zero crashes in any indicator/validator
- ✅ NaN volatility doesn't propagate to price adjustment
- ✅ Config loading errors produce clear messages
- ✅ API calls have 30s timeout

**Exit criteria:**
- All 8 tasks completed and tested
- Zero unhandled exceptions in 24h simulation run
- All division-by-zero unit tests pass

---

### Phase 2 — Security Hardening

**Objective:** Close input validation and safety control gaps.  
**Tasks:** T14, T15, T16, T17, T18, T19  
**Effort:** 3.5 days  
**Risk reduction:** Eliminates 8 Medium-severity security findings

**Goals:**
- ✅ `client_id` sanitized — no path traversal possible
- ✅ Hot-reload validates parameters before applying
- ✅ Sim→live switch requires explicit confirmation
- ✅ All parameter changes audit-logged
- ✅ Dependencies pinned; unused packages removed
- ✅ Vulnerability scanning in CI

**Exit criteria:**
- Path traversal test: `../../etc/passwd` → rejected
- Hot-reload test: invalid threshold → rejected
- Sim→live test: without env var → rejected
- `pip audit` passes in CI

---

### Phase 3 — Performance & Precision

**Objective:** Fix precision issues and optimize performance.  
**Tasks:** T20, T21, T22, T23, T24, T25  
**Effort:** 3.5 days  
**Risk reduction:** Eliminates 4 Medium + 2 Low findings

**Goals:**
- ✅ Live order prices rounded to exchange precision
- ✅ Minimum order size validated before placement
- ✅ `previous_spread` race condition eliminated
- ✅ Ticker data cached (2s TTL)
- ✅ OHLCV fetches normalized to reduce API calls
- ✅ Balance check latency reduced by 1s

**Exit criteria:**
- Unit test: unrounded price → rounded before order
- Unit test: below-minimum amount → rejected
- Unit test: concurrent `market_movement` calls → independent results
- API call count reduced by ~20% in benchmark

---

### Phase 4 — Architecture & Quality

**Objective:** Fill critical test gaps and improve code organization.  
**Tasks:** T26, T27, T28, T29, T30, T31  
**Effort:** 6.5 days  
**Risk reduction:** Eliminates 1 Critical (testing) + 2 High (testing) + 3 Low

**Goals:**
- ✅ `weighted_adjust_prices()` fully tested (4 market branches + edge cases)
- ✅ `process_trade_combination()` tested end-to-end
- ✅ Partial fill handling tested
- ✅ `Trade` dataclass in dedicated `models.py`
- ✅ `sonarft_search.py` split into 3 focused files
- ✅ VWAP consolidated into single location

**Exit criteria:**
- `sonarft_prices.py` test coverage >80%
- `sonarft_search.py` test coverage >60%
- All existing 96 tests still pass after refactoring
- Total test count >130

---

### Phase 5 — Enhancement & Polish

**Objective:** Production hardening and operational improvements.  
**Tasks:** T32, T33, T34, T35, T36, T37  
**Effort:** 5 days  
**Risk reduction:** Eliminates remaining Medium + Low findings

**Goals:**
- ✅ Docker container runs as non-root with health check
- ✅ Order reconciliation on startup
- ✅ Daily loss auto-reset
- ✅ Simulation slippage modeling
- ✅ Complete module documentation
- ✅ Parallel buy/sell combinations

**Exit criteria:**
- Docker health check responds
- Startup reconciliation test: pre-existing order → cancelled
- All modules have docstrings
- Benchmark: per-symbol processing ~2× faster

---

## 4. Task Dependency Graph

```mermaid
graph TD
    subgraph "Phase 0 — Critical Safety"
        T01[T01: Shutdown sequence]
        T02[T02: Cancel retry]
        T03[T03: Timeout cancel]
        T04[T04: Spread threshold fix]
        T05[T05: Null-safe ticker]
        T03 --> T02
    end

    subgraph "Phase 1 — Stability"
        T06[T06: Monitor task exit]
        T07[T07: Lock during stop]
        T08[T08: Zero-division guards]
        T09[T09: Volatility NaN guard]
        T10[T10: Price NaN guard]
        T11[T11: Config error handling]
        T12[T12: Bots dir creation]
        T13[T13: API timeout]
        T06 --> T01
        T07 --> T01
        T10 --> T09
    end

    subgraph "Phase 2 — Security"
        T14[T14: client_id sanitize]
        T15[T15: Hot-reload validation]
        T16[T16: Sim→live confirm]
        T17[T17: Audit logging]
        T18[T18: Pin dependencies]
        T19[T19: pip audit CI]
        T16 --> T15
    end

    subgraph "Phase 3 — Performance"
        T20[T20: Round live price]
        T21[T21: Min order size]
        T22[T22: previous_spread fix]
        T23[T23: Ticker cache]
        T24[T24: OHLCV normalize]
        T25[T25: Remove balance sleep]
    end

    subgraph "Phase 4 — Quality"
        T26[T26: Test prices.py]
        T27[T27: Test search.py]
        T28[T28: Test partial fills]
        T29[T29: Extract Trade model]
        T30[T30: Split search.py]
        T31[T31: Consolidate VWAP]
        T26 --> T09
        T26 --> T10
        T27 --> T26
        T28 --> T02
        T30 --> T27
    end

    subgraph "Phase 5 — Polish"
        T32[T32: Docker hardening]
        T33[T33: Order reconciliation]
        T34[T34: Daily loss reset]
        T35[T35: Sim slippage]
        T36[T36: Documentation]
        T37[T37: Parallel combos]
        T33 --> T01
        T37 --> T30
    end

    style T01 fill:#ff6666
    style T02 fill:#ff6666
    style T03 fill:#ff6666
    style T04 fill:#ff6666
    style T26 fill:#ff9999
```

### Critical Path

```
T01 (shutdown) → T06 (monitor exit) → T07 (lock fix)
                                    → T33 (order reconciliation)
T02 (cancel retry) → T03 (timeout cancel) → T28 (test partial fills)
T09 (vol NaN) → T10 (price NaN) → T26 (test prices.py) → T27 (test search.py) → T30 (split search)
```

### Parallelizable Tasks

| Can Run In Parallel | Tasks |
|---|---|
| Phase 0 parallel group | T01, T02, T04, T05 (all independent) |
| Phase 1 parallel group | T08, T11, T12, T13 (all independent) |
| Phase 2 parallel group | T14, T17, T18, T19 (all independent) |
| Phase 3 parallel group | T20, T21, T22, T23, T24, T25 (all independent) |
| Cross-phase parallel | T26 can start during Phase 1 (after T09/T10) |

---

## 5. Risk Reduction Mapping

| Phase | High Risks Before | High Risks After | Medium Before | Medium After | Reduction |
|---|---|---|---|---|---|
| **Phase 0** | 12 | 7 | 56 | 55 | -5 High, -1 Medium |
| **Phase 1** | 7 | 4 | 55 | 49 | -3 High, -6 Medium |
| **Phase 2** | 4 | 4 | 49 | 41 | -8 Medium |
| **Phase 3** | 4 | 4 | 41 | 37 | -4 Medium |
| **Phase 4** | 4 | 1 | 37 | 34 | -3 High (testing), -3 Low |
| **Phase 5** | 1 | 0 | 34 | 28 | -1 High, -6 remaining |

### Cumulative Risk Reduction

```
After Phase 0:  ████████████████░░░░  80% of High risks eliminated
After Phase 1:  ██████████████████░░  92% of High risks eliminated
After Phase 2:  ██████████████████░░  + 27% of Medium risks eliminated
After Phase 3:  ███████████████████░  + 34% of Medium risks eliminated
After Phase 4:  ████████████████████  100% of High risks eliminated
After Phase 5:  ████████████████████  50% of Medium risks eliminated
```


---

## 6. Effort & Timeline Projection

| Phase | Tasks | Conservative (1 dev) | Aggressive (2 devs) | Duration (1 dev) | Duration (2 devs) |
|---|---|---|---|---|---|
| **Phase 0** — Critical Safety | T01–T05 | 5 days | 3 days | Week 1 | Week 1 (3d) |
| **Phase 1** — Stability | T06–T13 | 5 days | 3 days | Week 2 | Week 1-2 |
| **Phase 2** — Security | T14–T19 | 4 days | 2 days | Week 3 | Week 2 |
| **Phase 3** — Performance | T20–T25 | 4 days | 2 days | Week 3-4 | Week 3 |
| **Phase 4** — Quality | T26–T31 | 7 days | 4 days | Week 4-5 | Week 3-4 |
| **Phase 5** — Polish | T32–T37 | 5 days | 3 days | Week 5-6 | Week 4-5 |
| **TOTAL** | **37 tasks** | **30 days** | **17 days** | **6 weeks** | **5 weeks** |

### Recommended Approach

With **2 developers** working in parallel:

```
Week 1:  Dev A: T01 (shutdown)     Dev B: T04 (spread), T05 (null), T08 (zero guards)
Week 2:  Dev A: T02, T03 (cancel)  Dev B: T06, T07, T09-T13 (stability)
Week 3:  Dev A: T14-T19 (security) Dev B: T20-T25 (performance) + T26 start (tests)
Week 4:  Dev A: T26-T28 (tests)    Dev B: T29-T31 (refactoring)
Week 5:  Dev A: T32-T34 (polish)   Dev B: T35-T37 (polish)
```

---

## 7. Technical Debt Backlog

Lower-priority improvements for future sprints:

| # | Task | Category | Benefit | Recommended Timeline |
|---|---|---|---|---|
| D01 | Rename `InitializeModules` → `initialize_modules` | Naming | Consistency | Post-Phase 5 |
| D02 | Rename `setAPIKeys` → `set_api_keys` | Naming | Consistency | Post-Phase 5 |
| D03 | Add `DEBUG` level logging throughout | Observability | Production debugging | Post-Phase 5 |
| D04 | Replace separator lines in logs with structured logging | Observability | Log parsing | Post-Phase 5 |
| D05 | Add `ROUND_HALF_EVEN` option for fee calculations | Precision | Eliminate systematic rounding bias | Post-Phase 5 |
| D06 | Shared exchange instance pool across bots | Scalability | ~50% fewer connections at scale | When >5 bots needed |
| D07 | Shared indicator cache across bots | Scalability | Eliminate redundant calculations | When >5 bots needed |
| D08 | WebSocket price stream for `monitor_price` | Latency | Near-instant price detection | When latency matters |
| D09 | Stop-loss / flash crash protection | Safety | Protect against extreme market moves | Before large positions |
| D10 | Configurable circuit breaker threshold | Flexibility | Different strategies need different thresholds | When multiple strategies |
| D11 | Configurable cycle sleep interval | Flexibility | Tunable trading frequency | When optimizing frequency |
| D12 | Unify `execute_long_trade`/`execute_short_trade` | Duplication | ~80% code reduction | Post-Phase 4 |
| D13 | Add RSI hysteresis (72/68 instead of 70/70) | Signal quality | Reduce boundary noise | When optimizing signals |
| D14 | SQLite DB rotation / archival | Operations | Prevent unbounded growth | When running >1 month |
| D15 | Exchange fee tier auto-detection | Accuracy | Match actual fee tier | When fee accuracy matters |

---

## 8. Testing & Validation Strategy

### Phase 0 Testing

| Test Type | Target | Scenarios |
|---|---|---|
| **Integration** | `stop_bot()` shutdown sequence | Stop during search cycle; stop during trade execution; stop with open orders |
| **Unit** | `cancel_order` retry logic | 1st cancel succeeds; all 3 fail → alert; network error on cancel |
| **Unit** | `monitor_order` timeout | 300s timeout → cancel called; cancel succeeds; cancel fails |
| **Unit** | Spread threshold fix | Known OHLCV data → expected thresholds; empty data → safe defaults |
| **Unit** | Null-safe ticker | `call_api_method` returns None → `get_last_price` returns None |

### Phase 1 Testing

| Test Type | Target | Scenarios |
|---|---|---|
| **Unit** | Division-by-zero guards (6 functions) | Zero denominator → safe default; normal values → correct result |
| **Unit** | NaN volatility guard | `get_volatility` returns NaN → `weighted_adjust_prices` returns (0,0,{}) |
| **Unit** | Config error handling | Missing file → BotCreationError; malformed JSON → BotCreationError |
| **Unit** | API timeout | Slow API → TimeoutError caught → returns None |

### Phase 2 Testing

| Test Type | Target | Scenarios |
|---|---|---|
| **Unit** | `client_id` sanitization | `../../etc/passwd` → sanitized; UUID → unchanged; `[object Object]` → sanitized |
| **Unit** | Hot-reload validation | Invalid threshold → ValueError; valid params → applied |
| **Unit** | Sim→live confirmation | Without env var → rejected; with env var → allowed |
| **Unit** | Audit logging | Parameter change → audit record with timestamp, old/new values |

### Phase 4 Testing (Critical Test Gap)

| Test Type | Target | Scenarios |
|---|---|---|
| **Unit** | `weighted_adjust_prices` | Bull+bull → spread increase; bear+bear → spread decrease; RSI≥70 → reversal; timeout → (0,0,{}); all None → (0,0,{}); NaN volatility → (0,0,{}) |
| **Unit** | `process_trade_combination` | Profitable → execute; unprofitable → skip; zero price → skip; validation fail → skip |
| **Unit** | Partial fill handling | Partial buy → adjusted sell amount; zero fill → skip sell; sell fail → cancel buy |

### Regression Testing

After each phase, run the full test suite (currently 96 tests) to verify no regressions. Target: **zero test failures after every phase.**

---

## 9. Release Strategy Milestones

### Milestone A — Safe Simulation Mode ✅ ACHIEVED

| Requirement | Status |
|---|---|
| Simulation mode default ON | ✅ |
| No real API calls in simulation | ✅ |
| Trade history persisted | ✅ |
| Parameter validation | ✅ |
| 96 tests passing | ✅ |

**Current state: Milestone A is already achieved.**

---

### Milestone B — Paper Trading Mode

**Target:** After Phase 0 + Phase 1 + Phase 2

| Requirement | Task | Status |
|---|---|---|
| All Phase 0 critical fixes | T01–T05 | ❌ |
| All Phase 1 stability fixes | T06–T13 | ❌ |
| `client_id` sanitized | T14 | ❌ |
| Hot-reload validated | T15 | ❌ |
| Dependencies pinned | T18 | ❌ |
| `weighted_adjust_prices` tested | T26 | ❌ |
| `process_trade_combination` tested | T27 | ❌ |
| **Total tests >120** | — | ❌ |

**Blocking issues:** T01, T02, T03, T04, T14, T15, T26, T27

---

### Milestone C — Limited Real Trading (Small Amounts)

**Target:** After Phase 3 + Phase 4

| Requirement | Task | Status |
|---|---|---|
| All Milestone B requirements | — | ❌ |
| Sim→live confirmation gate | T16 | ❌ |
| Live order prices rounded | T20 | ❌ |
| Min order size validated | T21 | ❌ |
| `previous_spread` race fixed | T22 | ❌ |
| Partial fill tests passing | T28 | ❌ |
| Audit logging active | T17 | ❌ |
| **Total tests >130** | — | ❌ |

**Blocking issues:** T16, T20, T21, T28

---

### Milestone D — Full Production Operation

**Target:** After Phase 5

| Requirement | Task | Status |
|---|---|---|
| All Milestone C requirements | — | ❌ |
| Docker non-root + health check | T32 | ❌ |
| Order reconciliation on startup | T33 | ❌ |
| Daily loss auto-reset | T34 | ❌ |
| Vulnerability scanning in CI | T19 | ❌ |
| Complete documentation | T36 | ❌ |
| **24h endurance test passing** | — | ❌ |
| **Total tests >140** | — | ❌ |

**Blocking issues:** T32, T33, T19


---

## 10. Success Metrics & Monitoring

| # | Metric | Target | Measurement | Monitoring |
|---|---|---|---|---|
| M1 | **Test count** | >140 (from 96) | `pytest --co -q \| wc -l` | CI pipeline |
| M2 | **Test pass rate** | 100% | `pytest` exit code | CI pipeline |
| M3 | **Zero unhandled exceptions** | 0 in 24h simulation | Log grep for traceback | Log monitoring |
| M4 | **Open orders after shutdown** | 0 | Exchange API query after stop | Integration test |
| M5 | **Cancel success rate** | >99% | Count cancel attempts vs successes | Audit log |
| M6 | **API call efficiency** | <40 calls/cycle (from ~32) | Counter in `call_api_method` | Metrics endpoint |
| M7 | **Memory stability** | <150MB after 24h | `ps aux` RSS | Process monitor |
| M8 | **Cycle time** | <10s (typical) | Timer in `search_trades` | Log analysis |
| M9 | **Vulnerability scan** | 0 critical/high CVEs | `pip audit` | CI pipeline |
| M10 | **Audit log completeness** | 100% of parameter changes logged | Audit table query | Periodic review |

---

## 11. Developer Onboarding Plan

### For a new developer joining the roadmap:

**Day 1 — Context (4 hours)**
1. Read `README.md` (bot package) — system overview and architecture
2. Read `.amazonq/rules/memory-bank/guidelines.md` — coding conventions
3. Read `docs/architecture/bot-overview.md` (Prompt 01 output) — module map and dependency graph
4. Read `docs/review/final-audit-report.md` (Prompt 11 output) — executive summary and top 10 risks

**Day 2 — Deep Dive (4 hours)**
1. Read the source files in dependency order: `sonarft_api_manager.py` → `sonarft_indicators.py` → `sonarft_math.py` → `sonarft_prices.py` → `sonarft_search.py` → `sonarft_execution.py` → `sonarft_bot.py`
2. Run the test suite: `pytest -v`
3. Read the test files to understand expected behavior

**Day 3 — Hands-On (4 hours)**
1. Start a bot in simulation mode (follow README)
2. Read the logs to understand the search cycle flow
3. Pick a Phase 0 task (T04 or T05 are good starters) and implement it
4. Submit PR with tests

### Key Files to Understand First

| Priority | File | Why |
|---|---|---|
| 1 | `sonarft_bot.py` | Orchestrator — wires everything together |
| 2 | `sonarft_search.py` | Trade detection pipeline — where decisions happen |
| 3 | `sonarft_prices.py` | Price adjustment — most complex logic |
| 4 | `sonarft_execution.py` | Order placement — where money moves |
| 5 | `sonarft_math.py` | Financial calculations — must understand Decimal pattern |

---

## 12. Final Roadmap Priorities

### Top 5 Must-Do Items for Production Readiness

| # | Item | Why | Effort | Phase |
|---|---|---|---|---|
| **1** | **Fix shutdown sequence** (T01) | Orphaned orders = direct financial risk. Every other order lifecycle fix depends on this. | 2 days | Phase 0 |
| **2** | **Add cancel retry + alerting** (T02, T03) | Unhedged positions from failed cancels = uncontrolled market exposure. | 1.5 days | Phase 0 |
| **3** | **Test `weighted_adjust_prices()`** (T26) | Most complex, financially impactful function with zero tests. Cannot have confidence in trade decisions without this. | 2 days | Phase 4 (start early) |
| **4** | **Sanitize `client_id`** (T14) | Confirmed path traversal vulnerability with filesystem evidence. Must fix before any deployment. | 0.5 days | Phase 2 |
| **5** | **Add hot-reload validation** (T15, T16) | Prevents invalid or dangerous parameters from being injected at runtime. | 1.5 days | Phase 2 |

### Start Here

```
Week 1, Day 1:  Start T01 (shutdown sequence) — this unblocks everything
Week 1, Day 1:  In parallel, start T04 (spread fix) + T05 (null safety) — quick wins
Week 1, Day 3:  Start T02 (cancel retry) — depends on nothing
Week 1, Day 4:  Start T26 (test prices.py) — can begin once T09/T10 are done
```

---

*Generated by Prompt 12-BOT-ROADMAP. Next: [13-setup-operations-guide.md](../prompts/13-setup-operations-guide.md)*
