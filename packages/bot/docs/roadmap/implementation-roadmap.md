# SonarFT Bot Package — Implementation Roadmap

**Prompt ID:** 12-BOT-ROADMAP  
**Generated:** July 2025  
**Input:** All review documents (Prompts 01–11)  
**Output File:** `docs/roadmap/implementation-roadmap.md`

---

## 1. Executive Roadmap Summary

| Attribute | Value |
|---|---|
| Current readiness | 6.5 / 10 — Simulation-Ready, Not Live-Ready |
| Total effort estimate | **Medium** (~50–60 engineering hours) |
| Phases | 6 (Phase 0 → Phase 5) |
| Estimated duration (1 developer) | 3–4 weeks |
| Estimated duration (2 developers) | 2 weeks |
| Primary risk domains | Trading Safety, Async/Concurrency, Exchange Integration |
| Blocking live trading | 5 defects (all in Phase 0) |

### Top architectural priorities

1. Fix four live-trading blocking defects (Phase 0)
2. Resolve three async race conditions (Phase 1)
3. Harden Docker deployment (Phase 0)
4. Expand test coverage for execution paths (Phase 1)
5. Refactor `SonarftBot` God Object (Phase 4)

---

## 2. Issue-to-Task Conversion Matrix

| ID | Source | Affected File | Severity | Task | Category | Complexity | Effort | Depends On |
|---|---|---|---|---|---|---|---|---|
| T01 | P01, P06, P08, P10 | `sonarft_execution.py:310` | High | ~~Fix `open_position` botid — pass actual bot UUID~~ ✅ DONE | Trading Safety | Low | 1h | — |
| T02 | P03, P06, P08 | `sonarft_execution.py` | High | ~~Implement `_current_exposure` increment/decrement with `asyncio.Lock`~~ ✅ DONE | Trading Safety | Medium | 3h | — |
| T03 | P06, P08 | `sonarft_api_manager.py` | High | ~~Add post-timeout order status check in `create_order`~~ ✅ DONE | Exchange Integration | Medium | 4h | — |
| T04 | P03, P04, P07, P08 | `sonarftdata/config_fees.json`, `config_schemas.py` | High | ~~Remove `exchanges_fees_2`; add Pydantic zero-fee validator~~ ✅ DONE | Financial Math | Low | 1h | — |
| T05 | P07, P08 | `Dockerfile`, `.dockerignore` | High | ~~Add volume mount for `sonarftdata/`; update `.dockerignore`~~ ✅ DONE | Configuration | Low | 2h | — |
| T06 | P02, P10 | `trade_executor.py` | High | Fix `trade_tasks` list race — protect with `asyncio.Lock` | Async | Medium | 3h | — |
| T07 | P02, P09 | `sonarft_api_manager.py`, `sonarft_indicators.py` | Medium | Replace 4 LRU cache dicts with `cachetools.TTLCache` | Async | Medium | 3h | — |
| T08 | P02 | `sonarft_execution.py` | Medium | Protect `_order_timestamps` rate limit check with `asyncio.Lock` | Async | Low | 1h | — |
| T09 | P02, P08 | `sonarft_bot.py` | Medium | Add inner `except Exception` handler to `_periodic_fee_refresh` and `_periodic_db_backup` | Async | Low | 1h | — |
| T10 | P08 | `sonarft_search.py` | Medium | Add webhook alert when `is_halted()` returns `True` | Trading Safety | Low | 1h | T01 |
| T11 | P04, P08 | `sonarft_math.py` | Medium | Fix OKX hardcoded `prices_precision=1` — wrong for low-price assets | Financial Math | Low | 2h | — |
| T12 | P06, P08 | `sonarft_api_manager.py` | Medium | Close REST fallback exchange instance in `finally` block | Exchange Integration | Low | 1h | — |
| T13 | P02 | `sonarft_manager.py` | Low | Replace `os.remove` with `asyncio.to_thread(os.remove, ...)` | Async | Low | 0.5h | — |
| T14 | P02 | `sonarft_bot.py` | Low | Wrap `load_configurations` file I/O in `asyncio.to_thread` | Async | Low | 1h | — |
| T15 | P02 | `sonarft_helpers.py` | Low | Move `_init_db` to async classmethod called from `initialize_modules` | Async | Low | 1h | — |
| T16 | P06, P10 | `sonarft_execution.py` | High | Add unit tests for `_execute_two_leg_trade` (partial fill, second-leg failure, botid) | Testing | Medium | 1 day | T01, T02 |
| T17 | P10 | `tests/` | Medium | Add dedicated test file for `sonarft_helpers.py` | Testing | Medium | 0.5 day | — |
| T18 | P10 | `tests/` | Medium | Add `monitor_order` timeout and cancellation path tests | Testing | Medium | 0.5 day | — |
| T19 | P07, P10 | `sonarft_bot.py`, `sonarft_helpers.py`, `sonarft_search.py` | Medium | Centralise `_BOT_DIR` / `_DB_PATH` into `paths.py` | Architecture | Low | 2h | — |
| T20 | P07 | `sonarft_search.py`, `sonarft_helpers.py` | Medium | Consolidate `daily_loss` SQLite helpers into `SonarftHelpers` | Architecture | Low | 2h | T19 |
| T21 | P10 | `sonarft_math.py`, `models.py` | Medium | Add type annotations to `calculate_trade`; fix `Trade` optional fields | Code Quality | Low | 2h | — |
| T22 | P07, P10 | `sonarft_bot.py` | Medium | Add hot-reload support for `slippage_buffer`, `flash_crash_threshold`, `max_daily_trades`, `max_total_exposure` | Configuration | Low | 2h | T02 |
| T23 | P07, P10 | `sonarft_bot.py`, `config_schemas.py` | Medium | Unify hot-reload validation to use Pydantic | Configuration | Medium | 3h | T22 |
| T24 | P07 | `sonarft_bot.py` | Medium | Add exchange name and indicator name validation at config load | Configuration | Low | 2h | — |
| T25 | P05, P10 | `sonarft_indicators.py` | Medium | Fix StochRSI K/D — use named column access instead of `iloc[0]`/`iloc[1]` | Indicators | Low | 1h | — |
| T26 | P08 | CI pipeline | Medium | Add `pip audit` to CI; pin `pydantic` to exact version | Security | Low | 1h | — |
| T27 | P07, P10 | `sonarft_helpers.py` | Low | Migrate `errors_history.json` / `balance_history.json` to SQLite | Configuration | Medium | 3h | T19 |
| T28 | P09 | `sonarft_api_manager.py` | Medium | Batch OHLCV fetch — one call per exchange/symbol/timeframe per cycle | Performance | Medium | 4h | — |
| T29 | P09 | `sonarft_execution.py` | Medium | Restructure `monitor_order` to await WebSocket order updates instead of 1s polling | Performance | High | 1 day | — |
| T30 | P01, P10 | `sonarft_bot.py` | Medium | Extract `BotConfig` dataclass from `SonarftBot` | Architecture | High | 2 days | T19, T20, T22, T23 |
| T31 | P09 | `sonarft_api_manager.py` | Low | Implement shared process-level cache for multi-bot deployments | Performance | High | 2 days | T07 |
| T32 | P05, P10 | `sonarft_indicators.py` | Low | Add 60s TTL cache to 4 uncached indicator functions | Performance | Low | 1h | T07 |
| T33 | P10 | `sonarft_prices.py` | Low | Add module docstring; add docstring to `weighted_adjust_prices` | Code Quality | Low | 0.5h | — |
| T34 | P10 | `sonarft_bot.py` | Low | Add class docstring to `SonarftBot` | Code Quality | Low | 0.5h | — |
| T35 | P10 | `trade_processor.py` | Low | Rename `weight=12` parameter to `vwap_depth=12` | Code Quality | Low | 0.5h | — |
| T36 | P08 | `sonarft_helpers.py` | Low | Add `'positions'` to `_ALLOWED_TABLES` | Security | Low | 0.5h | — |
| T37 | P07 | `sonarft_bot.py` | Low | Validate and parse all env vars at `create_bot` time, not lazily | Configuration | Low | 1h | — |
| T38 | P07 | `sonarft_bot.py` | Low | Add DB backup file rotation (keep last N days) | Configuration | Low | 1h | — |
| T39 | P06, P10 | `sonarft_validators.py` | Low | Parallelise liquidity + spread checks in `TradeValidator` | Performance | Low | 1h | — |
| T40 | P10 | `sonarft_execution.py` | Low | Fix `monitor_order` `finally` — only cancel if order not confirmed filled | Trading Safety | Low | 1h | — |

---

## 3. Phase-Based Implementation Plan

---

### Phase 0 — Critical Safety Fixes

**Objective:** Unblock live trading. Fix all defects that cause incorrect behaviour, data loss, or financial risk in live mode.

**Tasks:** T01, T02, T03, T04, T05

**Detailed task breakdown:**

#### T01 — Fix `open_position` botid (1h) ✅ DONE
```python
# sonarft_execution.py — _execute_two_leg_trade signature already receives botid
# Change:
await self.sonarft_helpers.open_position(botid=first_exchange_id, ...)
# To:
await self.sonarft_helpers.open_position(botid=str(botid), ...)
```
Validation: `test_open_position_called_with_bot_uuid_not_exchange_id` ✅

**Implementation notes:** `botid` was not a parameter of `_execute_two_leg_trade`. Threaded it through `execute_long_trade` and `execute_short_trade` as the first positional argument. Fixed both `open_position` and `close_position` calls. Added two validation tests (`test_open_position_called_with_bot_uuid_not_exchange_id`, `test_close_position_called_with_bot_uuid_not_exchange_id`). All 76 affected tests pass.

#### T02 — Implement exposure tracking (3h) ✅ DONE
Add `_exposure_lock = asyncio.Lock()` to `SonarftExecution.__init__`. In `execute_trade`, acquire lock, increment `_current_exposure` before first leg, decrement after second leg completes or fails.
Validation: `TestExposureTracking` (6 tests) ✅

**Implementation notes:** `trade_value` computed once before the lock and reused for both the cap check and the decrement. The `finally` block uses `max(0.0, ...)` to guard against floating-point underflow. The concurrent test uses an `asyncio.Event` gate to hold the first trade open while the second checks exposure — necessary because asyncio is cooperative. Also fixed pre-existing `test_execute_long_trade_opens_and_closes_position` broken by T01's `botid` parameter addition. 251 tests pass.

#### T03 — Post-timeout order status check (4h) ✅ DONE
After `asyncio.TimeoutError` on `create_order`, call `fetch_open_orders(symbol)` and search for a recently placed order. If found, return its ID for monitoring rather than treating as failed.
Validation: `TestCreateOrderRecovery` (6 tests) ✅

**Implementation notes:** Recovery check lives in `SonarftApiManager.create_order` — when the primary `call_api_method` returns `None`, `fetch_open_orders` is queried and the result is scanned for an order matching side, amount (within 0.1%), and price (within 0.1%) placed in the last 60 seconds. The recovery check itself is wrapped in `try/except` so a secondary failure degrades gracefully to `None`. 257 tests pass.

#### T04 — Remove zero-fee config trap (1h) ✅ DONE
Delete `exchanges_fees_2` from `config_fees.json`. Add `@model_validator` to `FeeConfig` rejecting `buy_fee == 0 and sell_fee == 0`.
Validation: `TestFeeConfig` (4 new tests) ✅

**Implementation notes:** The validator message includes "Zero fees" to make the `pytest.raises(match=...)` assertion readable. Zero on one side only (e.g. maker rebate) is explicitly allowed — only the combination of both zero is rejected. 261 tests pass.

#### T05 — Docker volume + `.dockerignore` (2h) ✅ DONE
Add `VOLUME` declaration to `Dockerfile`. Update `.dockerignore` to exclude `sonarftdata/history/`, `sonarftdata/bots/`, `sonarftdata/backups/`. Update `docker-compose.yml` with named volume mounts.
Validation: Deploy, create bot, replace container, verify history persists.

**Implementation notes:** Split the single `bot-data:/app/sonarftdata` volume into three granular volumes (`bot-history`, `bot-bots`, `bot-backups`) so config JSON files remain in the image (part of the application) while only runtime-generated data is persisted. Added `mkdir -p` in Dockerfile to ensure directories exist even without a volume mount (e.g. local dev). `.dockerignore` now excludes all four runtime data subdirectories. The API service in `docker-compose.yml` shares `bot-history` and `bot-bots` volumes (it reads trade history). 261 tests pass.

**Exit criteria for Phase 0:**
- All 5 tasks complete and tested
- `test_open_position_called_with_bot_uuid_not_exchange_id` passes
- `test_zero_fee_config_raises_validation_error` passes
- Docker container replacement preserves trade history
- Live trading mode can be enabled safely

**Risk reduction:** Eliminates all 4 live trading blockers + data loss risk.

---

### Phase 1 — Stability & Reliability

**Objective:** Fix async race conditions, improve error recovery, strengthen data validation, expand test coverage for critical paths.

**Tasks:** T06, T07, T08, T09, T10, T11, T12, T16, T17, T18, T24, T25

**Detailed task breakdown:**

#### T06 — Fix `trade_tasks` list race (3h)
Add `_tasks_lock = asyncio.Lock()` to `TradeExecutor`. Acquire lock in both `execute_trade` (append) and `monitor_trade_tasks` (read + replace). Alternatively replace list with `asyncio.Queue`.  
Validation: `test_concurrent_task_dispatch_no_task_loss`

#### T07 — Replace LRU cache dicts with `cachetools.TTLCache` (3h)
Add `cachetools` to `requirements.txt`. Replace `_ohlcv_cache`, `_order_book_cache`, `_ticker_cache` in `SonarftApiManager` and `_indicator_cache` in `SonarftIndicators` with `cachetools.TTLCache(maxsize=500, ttl=N)`. Remove manual eviction code.  
Validation: Existing cache tests pass; no `KeyError` under concurrent access.

#### T08 — Protect rate limit check (1h)
Add `_rate_limit_lock = asyncio.Lock()` to `SonarftExecution`. Acquire in the `_order_timestamps` check-and-append block.  
Validation: `test_rate_limit_not_exceeded_under_concurrent_tasks`

#### T09 — Periodic task exception handlers (1h)
Wrap the loop body of `_periodic_fee_refresh` and `_periodic_db_backup` in `try/except Exception as e: self.logger.error(...)` so unexpected errors log and continue rather than killing the task.  
Validation: `test_fee_refresh_continues_after_exception`

#### T10 — Alert on daily loss halt (1h)
In `SonarftSearch.is_halted`, call `self._alert_callback` (if set) when returning `True` for the first time in a day.  
Validation: `test_daily_loss_halt_sends_alert`

#### T11 — Fix OKX precision fallback (2h)
Change `EXCHANGE_RULES['okx']['prices_precision']` from `1` to `8` (safe default). Add a note that live precision from `get_symbol_precision` is always preferred. Add a test with a low-price asset (e.g. SHIB at 0.000012 USDT).  
Validation: `test_okx_low_price_asset_precision_not_zero`

#### T12 — Close REST fallback instance (1h)
In `call_api_method` REST fallback block, add `finally: await asyncio.to_thread(rest_instance.close)`.  
Validation: `test_rest_fallback_instance_closed_after_use`

#### T16 — `_execute_two_leg_trade` unit tests (1 day)
Write tests covering: first leg `None` → second leg not placed; partial first leg → `actual_second_amount` = filled amount; second leg `None` → first leg cancel called; second leg partial → alert sent; `open_position` called with correct botid.

#### T17 — `sonarft_helpers.py` test file (0.5 day)
Write tests for: save/retrieve order, save/retrieve trade, open/close position, `get_open_positions` excludes closed, `purge_history` keeps last N, `backup_db` creates readable file.

#### T18 — `monitor_order` path tests (0.5 day)
Write tests for: timeout path cancels order, `CancelledError` propagates through `finally`, filled order returns correct amounts.

#### T24 — Exchange and indicator name validation (2h)
In `load_configurations`, validate exchange names against `ccxt.exchanges` list. Validate indicator names against `{'rsi', 'stoch rsi', 'macd', 'sma', 'ema'}`. Raise `BotCreationError` on unknown values.

#### T25 — StochRSI named column access (1h)
Replace `last_row.iloc[0]` / `last_row.iloc[1]` with:
```python
k_col = f'STOCHRSIk_{stoch_period}_{rsi_period}_{k_period}_{d_period}'
d_col = f'STOCHRSId_{stoch_period}_{rsi_period}_{k_period}_{d_period}'
k_val = stoch_rsi[k_col].iloc[-1]
d_val = stoch_rsi[d_col].iloc[-1]
```
Validation: `test_stochrsi_k_greater_than_d_for_rising_prices`

**Exit criteria for Phase 1:**
- All race conditions resolved
- `_execute_two_leg_trade` has ≥ 5 unit tests
- `sonarft_helpers.py` has dedicated test file
- `monitor_order` timeout path tested
- No `KeyError` from cache eviction under concurrent load
- Fee refresh task survives unexpected exceptions

**Risk reduction:** Eliminates 3 async race conditions; closes test coverage gap on most critical execution path.


---

### Phase 2 — Security Hardening

**Objective:** Close remaining security gaps, harden configuration, protect against operational risks.

**Tasks:** T13, T14, T15, T19, T20, T26, T36, T37

**Detailed task breakdown:**

#### T13 — Async `os.remove` in `BotManager` (0.5h)
```python
# sonarft_manager.py remove_bot_instance
await asyncio.to_thread(os.remove, registry_file)
```

#### T14 — Async config file loading (1h)
Wrap `_load_config_section` calls in `asyncio.to_thread` or move `load_configurations` to be called before `asyncio.run` in `__main__.py`.

#### T15 — Async `_init_db` (1h)
Move `self._init_db()` from `SonarftHelpers.__init__` to an `async_init` classmethod. Call from `SonarftBot.initialize_modules` via `await asyncio.to_thread(SonarftHelpers._init_db)`.

#### T19 — Centralise paths into `paths.py` (2h)
Create `packages/bot/paths.py`:
```python
import os
BOT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BOT_DIR, 'sonarftdata', 'history', 'sonarft.db')
def bot_path(*parts): return os.path.join(BOT_DIR, *parts)
```
Update all three modules to import from `paths.py`.

#### T20 — Consolidate `daily_loss` SQLite helpers (2h)
Move `_load_daily_loss_sync`, `_save_daily_loss_sync` and the `daily_loss` table schema from `sonarft_search.py` into `SonarftHelpers`. Remove duplicate schema creation from `sonarft_search.py`.

#### T26 — CI dependency scanning (1h)
Add `pip audit` step to GitHub Actions workflow. Pin `pydantic` to exact version in `requirements.txt`. Add `hypothesis`, `pytest`, `pytest-asyncio` to pinned dev dependencies.

#### T36 — Add `positions` to `_ALLOWED_TABLES` (0.5h)
```python
_ALLOWED_TABLES = frozenset({'orders', 'trades', 'daily_loss', 'positions'})
```

#### T37 — Validate env vars at startup (1h)
Parse and validate all `SONARFT_*` env vars in `create_bot` before the run loop starts. Raise `BotCreationError` on invalid values (e.g. non-integer `SONARFT_MAX_FAILURES`).

**Exit criteria for Phase 2:**
- No blocking I/O in async functions
- Single `paths.py` source of truth
- `pip audit` passing in CI with 0 High/Critical CVEs
- All env vars validated at startup

**Risk reduction:** Eliminates path duplication hazard; closes async blocking I/O gaps; adds dependency vulnerability detection.

---

### Phase 3 — Performance Optimization

**Objective:** Improve API efficiency, reduce redundant computation, prepare for multi-bot scale.

**Tasks:** T28, T29, T32, T38, T39

**Detailed task breakdown:**

#### T28 — Batch OHLCV fetch (4h)
At the start of each `process_symbol` cycle, pre-fetch `max(all_required_limits)` candles for each exchange/symbol/timeframe combination. Store in a cycle-scoped dict passed to all indicator functions. Eliminates per-indicator OHLCV fetches within a cycle.

#### T29 — WebSocket-based `monitor_order` (1 day)
In ccxtpro mode, replace the 1s polling loop with a single `await exchange.watch_orders(symbol)` call that returns on the next order update. Reduces per-order API calls from ~300 to ~1–5.

```python
# Current: polls every 1s for up to 300s
while loop.time() < deadline:
    await asyncio.sleep(1)
    orders = await self.api_manager.watch_orders(...)

# Target: await next WebSocket update
order_update = await asyncio.wait_for(
    exchange.watch_orders(symbol), timeout=300.0
)
```

#### T32 — Cache 4 uncached indicator functions (1h)
Add `_cached` / `_cache_set` calls to `get_short_term_market_trend`, `get_volatility`, `get_support_price`, `get_resistance_price` using the existing 60s TTL pattern.

#### T38 — DB backup rotation (1h)
In `_periodic_db_backup`, after creating the new backup, delete backups older than `SONARFT_BACKUP_KEEP_DAYS` (default 7).

#### T39 — Parallelise validation checks (1h)
In `TradeValidator.has_requirements_for_success_carrying_out`, run both liquidity checks and the spread threshold check concurrently:
```python
result_01, result_02, spread_ok = await asyncio.gather(
    validators.deeper_verify_liquidity(buy_exchange, ...),
    validators.deeper_verify_liquidity(sell_exchange, ...),
    validators.verify_spread_threshold(...),
)
```

**Exit criteria for Phase 3:**
- `monitor_order` API calls reduced by ≥ 90% in ccxtpro mode
- OHLCV fetches per cycle reduced to 1 per exchange/symbol/timeframe
- Backup directory bounded to last 7 days

**Risk reduction:** Eliminates `monitor_order` REST polling bottleneck; reduces exchange rate limit exposure.

---

### Phase 4 — Architecture Improvements

**Objective:** Reduce complexity, improve modularity, eliminate technical debt, complete test coverage.

**Tasks:** T21, T22, T23, T27, T30, T31, T33, T34, T35, T40

**Detailed task breakdown:**

#### T21 — Type annotations (2h)
Add full type annotations to `calculate_trade`, `SonarftMath`, `Trade` dataclass optional fields, and all `logger=None` parameters.

#### T22 + T23 — Hot-reload completeness + Pydantic unification (5h)
Add `slippage_buffer`, `flash_crash_threshold`, `max_daily_trades`, `max_total_exposure` to `apply_parameters`. Replace `_validate_parameters()` with a Pydantic `ParametersConfig(**current_values)` validation call.

#### T27 — Migrate JSON history files to SQLite (3h)
Replace `errors_history.json` and `balance_history.json` with SQLite tables in `sonarft.db`. Apply the same `purge_history` retention policy (keep last 10,000 records).

#### T30 — Extract `BotConfig` from `SonarftBot` (2 days)
Create a `BotConfig` dataclass holding all config-loaded values. Extract `load_configurations` into a standalone `load_bot_config(config_setup)` function returning `BotConfig`. `SonarftBot` receives `BotConfig` at construction. This reduces `SonarftBot` from ~782 lines to ~400 lines and makes config loading independently testable.

#### T31 — Shared process-level cache (2 days)
Create a `SharedMarketCache` class using `cachetools.TTLCache` with `asyncio.Lock`. Pass a single instance to all `SonarftApiManager` instances in the same process. All bots trading the same symbol share one OHLCV/order book fetch per TTL window.

#### T40 — Fix `monitor_order` always-cancel in `finally` (1h)
Add a `_filled` flag. Set it `True` when the order status is `"closed"`. In `finally`, only call `_cancel_order_with_retry` if `not _filled`.

**Exit criteria for Phase 4:**
- `SonarftBot` < 450 lines
- `BotConfig` independently testable
- Type annotation coverage ≥ 85%
- Hot-reload covers all 13 parameters
- `errors_history.json` / `balance_history.json` removed

**Risk reduction:** Reduces God Object complexity; eliminates unbounded file growth; improves maintainability.

---

### Phase 5 — Enhancement & Polish

**Objective:** Strategy improvements, documentation, developer experience, advanced features.

**Tasks:** T33, T34, T35, and new enhancement tasks

**Detailed task breakdown:**

- Add module docstring to `sonarft_prices.py` (T33)
- Add class docstring to `SonarftBot` (T34)
- Rename `weight=12` to `vwap_depth=12` (T35)
- Move RSI thresholds (70/30) to `config_parameters.json`
- Move indicator periods (14/14/3/3, 12/26/9) to `config_indicators.json`
- Add `min_trading_volume_coefficient` to config
- Add `monitor_price` and `monitor_order` timeout durations to config
- Improve Docker health check to verify bot process liveness
- Add `pytest-cov` to CI with 80% minimum coverage gate for financial modules

**Exit criteria for Phase 5:**
- All hardcoded strategy parameters configurable
- Documentation coverage ≥ 95%
- CI coverage gate enforced

---

## 4. Task Dependency Graph

```
Phase 0 (no dependencies — start immediately):
  T01 ──────────────────────────────────────────► T10, T16
  T02 ──────────────────────────────────────────► T16, T22
  T03 (independent)
  T04 (independent)
  T05 (independent)

Phase 1 (can start after Phase 0 or in parallel):
  T06 (independent)
  T07 ──────────────────────────────────────────► T31 (Phase 4)
  T08 (independent)
  T09 (independent)
  T11 (independent)
  T12 (independent)
  T16 ◄── T01, T02
  T17 (independent)
  T18 (independent)
  T24 (independent)
  T25 (independent)

Phase 2 (can start after Phase 1 or in parallel):
  T19 ──────────────────────────────────────────► T20, T27 (Phase 4)
  T20 ◄── T19
  T13, T14, T15, T26, T36, T37 (independent)

Phase 3 (can start after Phase 1):
  T28 (independent)
  T29 (independent — requires ccxtpro)
  T32 ◄── T07
  T38, T39, T40 (independent)

Phase 4 (depends on Phase 2 + Phase 3):
  T22 ◄── T02
  T23 ◄── T22
  T30 ◄── T19, T20, T22, T23
  T31 ◄── T07
  T27 ◄── T19
  T21, T33, T34, T35, T40 (independent)

Critical path: T01 → T16 → (Phase 4 architecture work)
Parallelisable: T03, T04, T05 can all run simultaneously in Phase 0
```

---

## 5. Risk Reduction Mapping

| Phase | Critical Risks Before | Critical Risks After | Reduction |
|---|---|---|---|
| Phase 0 | Position reconciliation broken; untracked orders; unlimited exposure; zero-fee trap; data loss | All 5 live trading blockers resolved | **High** |
| Phase 1 | Task loss race; cache eviction race; rate limit bypass; fee refresh silent death; execution paths untested | All async races fixed; critical paths tested | **High** |
| Phase 2 | Blocking I/O in async; path duplication; no CVE scanning; env var validation deferred | All async blocking eliminated; security hardened | **Medium** |
| Phase 3 | 300 REST calls per order; unshared caches at scale | API load reduced 90%; multi-bot efficient | **Medium** |
| Phase 4 | God Object hard to test; hot-reload incomplete; unbounded files | Modular, fully testable; all params hot-reloadable | **Low-Medium** |
| Phase 5 | Hardcoded strategy params; documentation gaps | Fully configurable; documented | **Low** |

---

## 6. Effort & Timeline Projection

| Phase | Tasks | Conservative | Aggressive | 1 Developer | 2 Developers |
|---|---|---|---|---|---|
| Phase 0 | T01–T05 | 12h | 8h | 1.5 days | 1 day |
| Phase 1 | T06–T12, T16–T18, T24–T25 | 24h | 16h | 3 days | 1.5 days |
| Phase 2 | T13–T15, T19–T20, T26, T36–T37 | 12h | 8h | 1.5 days | 1 day |
| Phase 3 | T28–T29, T32, T38–T39, T40 | 16h | 10h | 2 days | 1 day |
| Phase 4 | T21–T23, T27, T30–T31, T33–T35 | 32h | 20h | 4 days | 2 days |
| Phase 5 | Enhancements + docs | 16h | 10h | 2 days | 1 day |
| **Total** | **40 tasks** | **~112h** | **~72h** | **~14 days** | **~7.5 days** |

**Live trading ready after Phase 0:** 1–1.5 days  
**Production beta after Phases 0–2:** 4–6 days  
**Full production after all phases:** 2–3 weeks


---

## 7. Technical Debt Backlog

Lower-priority improvements that can be addressed opportunistically:

| Task | Category | Benefit | Recommended Timeline |
|---|---|---|---|
| Replace `__ccxt__`/`__ccxtpro__` boolean flags with `_mode` enum | Architecture | Cleaner dispatch logic | Phase 4 |
| Add `Optional[logging.Logger]` type to all `logger=None` params | Code Quality | mypy compliance | Phase 4 |
| Remove dead `BotRunError` exception class | Code Quality | Reduces noise | Phase 2 |
| Remove dead `wait_for_rate_limit` method | Code Quality | Reduces noise | Phase 2 |
| Remove dead `get_profit_factor` in `SonarftIndicators` | Code Quality | Reduces noise | Phase 2 |
| Remove dead `market_movement` method (wrong formula) | Code Quality | Prevents accidental use | Phase 2 |
| Remove unused `BotManager` instantiation in `__main__.py` | Code Quality | Removes misleading code | Phase 2 |
| Add `clientOrderId` tagging for bot-placed orders | Exchange Integration | Distinguishes bot orders from manual orders at reconciliation | Phase 3 |
| Add per-exchange daily loss limit | Trading Safety | Finer-grained risk control | Phase 5 |
| Add Kelly criterion or volatility-based position sizing | Trading Logic | Replaces fixed `trade_amount` | Phase 5 |
| Add MACD to `_determine_position` entry logic | Trading Logic | Richer signal confirmation | Phase 5 |
| Add `pytest-cov` with 80% minimum for financial modules | Testing | Enforces coverage regression | Phase 1 |
| Add `pytest-timeout` to prevent hanging async tests | Testing | CI reliability | Phase 1 |
| Improve Docker health check to verify bot liveness | Configuration | Faster failure detection | Phase 3 |
| Add `SONARFT_BACKUP_KEEP_DAYS` env var | Configuration | Bounded backup storage | Phase 3 |

---

## 8. Testing & Validation Strategy

### Phase 0 validation

| Test | Type | Validates |
|---|---|---|
| `test_open_position_called_with_bot_uuid` | Unit | T01 fix |
| `test_exposure_cap_blocks_concurrent_trades` | Unit | T02 fix |
| `test_timeout_triggers_order_recovery` | Unit | T03 fix |
| `test_zero_fee_config_raises` | Unit | T04 fix |
| Docker volume persistence test | Integration | T05 fix |

### Phase 1 validation

| Test | Type | Validates |
|---|---|---|
| `test_concurrent_task_dispatch_no_loss` | Unit | T06 fix |
| `test_cache_no_keyerror_under_concurrent_access` | Unit | T07 fix |
| `test_rate_limit_not_exceeded_concurrently` | Unit | T08 fix |
| `test_fee_refresh_survives_exception` | Unit | T09 fix |
| `test_daily_halt_sends_alert` | Unit | T10 fix |
| `test_execute_two_leg_trade_*` (5 tests) | Unit | T16 |
| `test_helpers_*` (7 tests) | Unit | T17 |
| `test_monitor_order_timeout_cancels` | Unit | T18 |

### Phase 2 validation

| Test | Type | Validates |
|---|---|---|
| `test_no_blocking_io_in_async_functions` | Static analysis | T13–T15 |
| `test_paths_module_single_source` | Unit | T19 |
| `pip audit` in CI | Automated | T26 |
| `test_invalid_env_var_raises_at_startup` | Unit | T37 |

### Phase 3 validation

| Test | Type | Validates |
|---|---|---|
| `test_monitor_order_ws_fewer_api_calls` | Integration | T29 |
| `test_ohlcv_fetched_once_per_cycle` | Unit | T28 |
| `test_backup_rotation_keeps_last_n` | Unit | T38 |

### Regression testing plan

After each phase:
1. Run full test suite: `make test-bot`
2. Run simulation integration test: `pytest tests/test_simulation_integration.py -v`
3. Run Hypothesis property tests: `pytest tests/test_hypothesis_math.py -v`
4. Manual smoke test: start bot in simulation mode, verify 3 complete cycles

### Load testing (Phase 3+)

- 5 bots × 3 symbols × 2 exchanges: verify no event loop lag > 50ms
- 10 concurrent trade tasks: verify all tasks complete and are recorded
- 24h simulation run: verify no memory growth, no file size growth

---

## 9. Release Strategy Milestones

### Milestone A — Safe Simulation Mode ✅ Already Met

**Requirements:**
- `is_simulating_trade=1` default ✅
- No real API calls for orders ✅
- P&L tracking functional ✅

**Validation:** `make test-bot` passes; simulation integration test passes.

---

### Milestone B — Paper Trading Mode ✅ Already Met

**Requirements:**
- Real market data via ccxt/ccxtpro ✅
- No real orders placed ✅
- Daily loss tracking persisted across restarts ✅

**Recommended additions before paper trading:** Complete Phase 1 (async races fixed, execution paths tested).

---

### Milestone C — Limited Real Trading 🔴 Blocked

**Requirements (all must be met):**
- [ ] T01: `open_position` botid fix
- [ ] T02: `max_total_exposure` functional
- [ ] T03: Post-timeout order recovery
- [ ] T04: Zero-fee config removed
- [ ] T05: Docker volume mount
- [ ] T16: `_execute_two_leg_trade` unit tests passing
- [ ] Conservative live parameters: `max_trade_amount ≤ 0.01`, `max_daily_loss ≤ 50`, `max_orders_per_minute ≤ 3`
- [ ] `SONARFT_ALERT_WEBHOOK` configured
- [ ] Manual monitoring for first 48 hours

**Estimated readiness:** After Phase 0 + T16 (Phase 1) = ~2 days

---

### Milestone D — Full Production Operation 🔴 Blocked

**Requirements (all must be met):**
- [ ] All Milestone C requirements
- [ ] All Phase 1 tasks complete (async races, full test coverage)
- [ ] All Phase 2 tasks complete (security hardening)
- [ ] `pip audit` passing with 0 High/Critical CVEs
- [ ] DB backup on separate volume (`SONARFT_BACKUP_DIR` configured)
- [ ] Log rotation configured in deployment environment
- [ ] Meaningful Docker health check
- [ ] Load test: 5 bots × 3 symbols with no event loop lag > 50ms
- [ ] 7-day paper trading run with P&L within expected range

**Estimated readiness:** After Phases 0–2 = ~6 days

---

## 10. Success Metrics & Monitoring

| Metric | Target | Measurement | Monitoring |
|---|---|---|---|
| Test suite pass rate | 100% | `pytest` exit code | CI on every commit |
| Financial module coverage | ≥ 80% | `pytest-cov` | CI gate |
| `pip audit` High/Critical CVEs | 0 | `pip audit` | CI on every commit |
| Cycle time (warm cache) | < 500ms | `log_cycle` `cycle_duration_ms` | `sonarft.metrics` logger |
| Event loop lag | < 50ms | `asyncio` debug mode | Deployment monitoring |
| Daily loss accuracy | ± 0.01 USDT | Compare SQLite vs manual calculation | Post-trade audit |
| Position reconciliation accuracy | 100% | All open positions found on restart | Startup log |
| Order tracking accuracy | 100% | No untracked orders after timeout | Exchange order history audit |
| API call rate | < 20/min per exchange | `log_api_call` metrics | `sonarft.metrics` logger |
| Memory per bot | < 200 MB | `tracemalloc` / container metrics | Deployment monitoring |
| Webhook alert delivery | < 30s | Alert timestamp vs event timestamp | Manual spot check |

---

## 11. Developer Onboarding Plan

### For a developer picking up this roadmap

**Day 1 — Context (2h):**
1. Read `docs/review/final-audit-report.md` — understand the 4 blocking defects
2. Read `docs/architecture/bot-overview.md` — understand module structure
3. Read `docs/trading/execution-review.md` — understand the execution path
4. Run `make test-bot` — verify all tests pass before making changes

**Day 1 — Phase 0 start (6h):**
5. Fix T01 (`open_position` botid) — 1h
6. Write `test_open_position_called_with_bot_uuid` — 1h
7. Fix T04 (zero-fee config) — 1h
8. Fix T05 (Docker volume) — 2h
9. Start T02 (exposure tracking) — 1h

**Day 2 — Phase 0 complete + Phase 1 start:**
10. Complete T02 + T03 — 5h
11. Start T06 (task list race) — 3h

**Week 1 — Phase 0 + Phase 1:**
- Complete all Phase 0 and Phase 1 tasks
- Run full test suite after each task
- Commit each task as a separate PR for review

**Week 2 — Phase 2 + Phase 3:**
- Complete security hardening and performance optimisation
- Run load test after T29 (WebSocket monitor_order)

**Weeks 3–4 — Phase 4 + Phase 5:**
- Architecture refactor (T30 is the largest task — plan 2 full days)
- Documentation and polish

### Key files to understand first

| File | Why |
|---|---|
| `sonarft_execution.py` | Contains T01, T02, T08, T40 — most Phase 0 work |
| `sonarft_api_manager.py` | Contains T03, T07, T12 |
| `trade_executor.py` | Contains T06 |
| `sonarft_bot.py` | Contains T09, T14, T22, T23, T30 |
| `tests/conftest.py` | Shared fixtures — understand before writing tests |

---

## 12. Final Roadmap Priorities

The five must-do items for production readiness, in strict order:

1. **T01 — Fix `open_position` botid** (1h): The single most dangerous defect. Breaks position reconciliation in live mode. Fix is a one-line change. Do this first.

2. **T05 — Docker volume mount** (2h): Without this, every container replacement destroys all trade history and bot registry data. Must be in place before any live deployment.

3. **T03 — Post-timeout order recovery** (4h): Prevents untracked open orders from accumulating on the exchange after network timeouts. Critical for live trading safety.

4. **T16 — `_execute_two_leg_trade` unit tests** (1 day): The most complex execution path has no direct tests. Writing these tests will validate T01 and T02 fixes and prevent regressions.

5. **T06 — Fix `trade_tasks` list race** (3h): Prevents trade tasks from being silently lost between the monitor cycle's list comprehension and rebind. Ensures P&L tracking is complete and accurate.

---

*Complete Phase 0 (T01–T05) and the system is safe for live trading. Complete Phases 0–2 and the system is production-ready. The rest is optimisation and polish.*
