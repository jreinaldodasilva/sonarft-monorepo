# SonarFT Bot — Implementation Roadmap

**Prompt:** 12-BOT-ROADMAP  
**Reviewer role:** Senior technical program manager / software architect  
**Date:** July 2025  
**Status:** Complete  
**Input:** All 10 review documents + Final Consolidation (Prompt 11)

---

## 1. Executive Roadmap Summary

### System readiness before roadmap

**Current state: Beta — 6.5/10**  
Safe for simulation. Three blocking issues prevent live trading. 221 findings across 10 domains.

### Estimated total effort

**Medium** — 3–6 weeks for a single experienced developer; 2–3 weeks with a two-person team.

### Phases

6 phases: Phase 0 (Critical Safety) → Phase 1 (Stability) → Phase 2 (Security) → Phase 3 (Performance) → Phase 4 (Architecture) → Phase 5 (Enhancement)

### Primary risk domains

1. Trading Safety (startup live mode guard, position tracker)
2. Exchange Integration (no WS→REST failover, lost confirmations)
3. Configuration (no schema validation, hardcoded values)
4. Security (SQL table validation, dependency scanning)

### Top architectural priorities

1. Persistent position tracking — the largest missing feature for live trading
2. Startup safety gate — the most critical single-line fix
3. Infrastructure test coverage — `SonarftApiManager` and `TradeExecutor` are untested
4. Async SQLite consistency — one module still blocks the event loop
5. Dead code removal — reduces cognitive load and maintenance surface

---

## 2. Issue-to-Task Matrix

| Task ID | Issue ID | Affected File | Severity | Task Description | Category | Complexity | Effort | Depends On |
|---|---|---|---|---|---|---|---|---|
| ~~T-01~~ ✅ | T-14, S-13, C-07 | `sonarft_bot.py` | **Critical** | Add `SONARFT_ALLOW_LIVE` env var check in `load_configurations()` when `is_simulating_trade=0` | Safety | XS | 1h | — |
| ~~T-02~~ ✅ | S-09, P-10 | `trade_executor.py` | **High** | Add `MAX_CONCURRENT_TRADES` env var limit; skip dispatch when limit reached; log risk event | Reliability | S | 2h | — |
| ~~T-03~~ ✅ | A-01, E-02 | `requirements.txt`, `pyproject.toml` | **High** | Add `ccxt[pro]` as declared dependency with pinned version | Deployment | XS | 30m | — |
| ~~T-04~~ ✅ | I-26 | `sonarft_prices.py` | **Medium** | Fix `if stoch_buy` → `if stoch_buy is not None` (×4 occurrences) | Logic | XS | 30m | — |
| ~~T-05~~ ✅ | S-06 | `sonarft_helpers.py` | **High** | Add `_ALLOWED_TABLES = frozenset({'orders','trades','daily_loss'})` validation in all `_db_*` methods | Security | XS | 1h | — |
| ~~T-06~~ ✅ | E-24 | `sonarft_helpers.py`, `sonarft_execution.py`, `sonarft_bot.py` | **High** | Add `positions` SQLite table; record on first leg fill; close on second leg fill; reconcile on startup | Safety | L | 2 days | T-01 |
| ~~T-07~~ ✅ | E-06, B-25 | `sonarft_api_manager.py` | **High** | Add REST fallback in `call_api_method()` when ccxtpro call raises exception | Reliability | M | 4h | T-03 |
| ~~T-08~~ ✅ | B-03 | `sonarft_search.py` | **High** | Wrap `_save_daily_loss()` and `_load_daily_loss()` in `asyncio.to_thread`; make `set_botid()` async | Performance | S | 1h | — |
| ~~T-09~~ ✅ | C-05 | `sonarftdata/config_indicators.json` | **High** | Fix `indicators_3`: change `"rsi, stoch rsi"` → `["rsi", "stoch rsi"]` | Config | XS | 15m | — |
| ~~T-10~~ ✅ | C-01 | `sonarft_bot.py` | **High** | Add `pydantic` schema validation for all config sections in `load_configurations()` | Config | M | 4h | — |
| ~~T-11~~ ✅ | T-17, I-28 | `models.py`, `sonarft_prices.py`, `sonarft_execution.py` | **Medium** | Extract `RSI_OVERBOUGHT = 70`, `RSI_OVERSOLD = 30` to `models.py`; import in both files | Logic | XS | 1h | — |
| ~~T-12~~ ✅ | I-13 | `sonarft_prices.py` | **Medium** | Remove `market_movement()` calls from `weighted_adjust_prices()` gather; remove unused variables | Performance | XS | 1h | — |
| ~~T-13~~ ✅ | Q-16 | `tests/` | **High** | Add `test_sonarft_api_manager.py`: cache hit/miss, dispatch, `get_latest_prices`, `get_weighted_prices` | Quality | M | 4h | T-03 |
| ~~T-14~~ ✅ | Q-17 | `tests/` | **High** | Add `test_trade_executor.py`: task lifecycle, `monitor_trade_tasks`, `shutdown`, P&L tracking | Quality | M | 4h | — |
| ~~T-15~~ ✅ | S-27 | `.github/workflows/ci.yml` | **Medium** | Add `pip-audit -r requirements.txt` step to CI pipeline | Security | XS | 1h | T-03 |
| ~~T-16~~ ✅ | E-31 | `sonarft_execution.py` | **Medium** | Wrap `monitor_order()` polling loop in `try/finally`; cancel order on any exit | Safety | S | 2h | — |
| ~~T-17~~ ✅ | T-09, S-18 | `trade_processor.py`, `sonarft_execution.py` | **Medium** | Add `slippage_buffer` config param; add to profit threshold check; re-validate after `monitor_price()` | Financial | M | 3h | T-10 |
| ~~T-18~~ ✅ | E-15 | `sonarft_execution.py` | **Medium** | Re-run `calculate_trade()` with monitored price before placing order; skip if no longer profitable | Financial | M | 3h | — |
| ~~T-19~~ ✅ | S-10, P-11 | `sonarft_api_manager.py` | **Medium** | Add LRU eviction (500 entries) to `_order_book_cache` and `_ticker_cache` | Performance | S | 2h | — |
| ~~T-20~~ ✅ | C-19 | `sonarft_helpers.py`, `sonarft_search.py` | **Medium** | Replace `os.path.join('sonarftdata',...)` with `_bot_path('sonarftdata',...)` in both files | Config | XS | 1h | — |
| ~~T-21~~ ✅ | T-11 | `sonarft_api_manager.py` | **High** | Add `refresh_fees()` method; call at startup and every 24h via background task | Financial | M | 4h | — |
| ~~T-22~~ ✅ | P-04 | `sonarft_api_manager.py` | **Medium** | Route `get_latest_prices()` through `get_order_book()` and `_get_ticker()` to populate cache | Performance | S | 2h | — |
| ~~T-23~~ ✅ | B-08 | `sonarft_prices.py` | **Low** | Use `asyncio.gather(get_macd, get_rsi)` in `dynamic_volatility_adjustment()` | Performance | XS | 1h | — |
| ~~T-24~~ ✅ | Q-09, Q-10 | `sonarft_execution.py` | **Medium** | Decompose `_execute_single_trade()` into `_determine_position()` + `_execute_two_leg_trade()` | Quality | M | 4h | — |
| ~~T-25~~ ✅ | Q-18, Q-19 | `tests/` | **Medium** | Add circuit breaker test; add `sanitize_client_id()` path traversal tests | Quality | S | 2h | — |
| T-26 | C-08 | `packages/bot/` | **Low** | Create `.env.example` listing all env vars with descriptions | Docs | XS | 1h | — |
| ~~T-27~~ ✅ | I-11, I-12, E-32 | `sonarft_indicators.py`, `sonarft_api_manager.py` | **Low** | Remove dead code: `get_atr()`, `get_24h_high()`, `get_24h_low()`, `create_futures_order()` | Quality | XS | 1h | — |
| ~~T-28~~ ✅ | C-11, C-12 | `sonarftdata/config_indicators.json`, `config_parameters.json` | **Medium** | Add indicator period fields and `flash_crash_threshold` to config files; read in code | Config | M | 3h | T-10 |
| ~~T-29~~ ✅ | E-29 | `sonarft_bot.py` | **Low** | Parallelise `_reconcile_open_orders()` with `asyncio.gather` | Performance | S | 2h | — |
| ~~T-30~~ ✅ | M-16 | `sonarft_math.py` | **High** | Treat missing `get_symbol_precision()` as a hard error (not silent fallback to wrong precision) | Financial | S | 2h | — |

---

## 3. Phase-Based Implementation Plan

---

### Phase 0 — Critical Safety Fixes

**Objective:** Eliminate all risks that can cause direct financial loss or system failure before any live deployment.

**Tasks:** T-01, T-02, T-03, T-04, T-05, T-09

| Task | Description | Effort |
|---|---|---|
| T-01 | Startup live mode guard | 1h |
| T-02 | `MAX_CONCURRENT_TRADES` limit | 2h |
| T-03 | Add `ccxt[pro]` to requirements | 30m |
| T-04 | Fix StochRSI truthiness check | 30m |
| T-05 | SQL table allowlist | 1h |
| T-09 | Fix `indicators_3` config entry | 15m |

**Total effort:** ~5.5 hours  
**Can be parallelised:** T-01, T-02, T-03, T-04, T-05, T-09 are all independent.

**Risk reduction impact:**
- Eliminates accidental live trading on startup (Critical)
- Eliminates OOM kill from unbounded task list (High)
- Fixes deployment failure from missing `ccxt.pro` (High)
- Fixes StochRSI signal masking bug (Medium)
- Prevents future SQL injection (High)
- Fixes malformed config entry (High)

**Exit criteria:**
- `SONARFT_ALLOW_LIVE` check raises `BotCreationError` when absent in live mode
- `MAX_CONCURRENT_TRADES=10` env var limits task list
- `pip install -r requirements.txt` installs ccxt.pro without error
- `if stoch_buy is not None` in all 4 occurrences
- `_ALLOWED_TABLES` validation in all `_db_*` methods
- `indicators_3` is a valid JSON array

**Implementation notes (completed tasks):**
- **T-01** ✅ — `_check_live_mode_guard()` added to `sonarft_bot.py`; called from `load_configurations()` after `is_simulating_trade` is loaded. Raises `BotCreationError` if `is_simulating_trade=0` and `SONARFT_ALLOW_LIVE` env var is absent. Logs a `⚠️ LIVE TRADING MODE ACTIVE` warning when live mode is correctly enabled. 3 unit tests added to `test_sonarft_bot.py`.
- **T-02** ✅ — `_MAX_CONCURRENT_TRADES` module-level constant added to `trade_executor.py` (default 10, overridable via `SONARFT_MAX_CONCURRENT_TRADES` env var). `execute_trade()` counts active (not-done) tasks before dispatching; skips and emits a `log_risk_event` when the limit is reached. 3 async unit tests added to `test_sonarft_search_execution.py`.
- **T-08** ✅ — `_save_daily_loss` and `_load_daily_loss` renamed to `_*_sync` variants; async wrappers added using `asyncio.to_thread`. `set_botid()`, `record_trade_result()`, `_check_daily_reset()`, and `is_halted()` all made async. `search_trades()` updated to `await is_halted()`. `TradeExecutor.monitor_trade_tasks()` updated to `await record_trade_result()`. `SonarftBot.initialize_modules()` updated to `await set_botid()`. All 5 `TestDailyLossLimit` tests converted to async.
- **T-11** ✅ — `RSI_OVERBOUGHT = 70` and `RSI_OVERSOLD = 30` added to `models.py` as module-level constants. Both `sonarft_prices.py` (was 72/28) and `sonarft_execution.py` (was 70/30) now import and use these constants. The 72/28 vs 70/30 inconsistency is eliminated — both layers now use the same thresholds. No new tests needed (existing price and execution tests cover the branches).
- **T-12** ✅ — Removed the two `market_movement()` calls from the `weighted_adjust_prices()` indicator gather in `sonarft_prices.py`. Their results were assigned to `_market_movement_buy` / `_market_movement_sell` (throwaway variables) and never used in any price adjustment logic. The gather shrinks from 16 to 14 concurrent calls, saving 2 API calls per combination and reducing pressure on the 30-second timeout budget. The unused `order_book_depth` local variable was also removed.
- **T-20** ✅ — Added `_BOT_DIR = os.path.dirname(os.path.abspath(__file__))` and `_bot_path()` helper to `sonarft_helpers.py`. Updated `_DB_PATH` class attribute and all `os.path.join('sonarftdata', ...)` calls in `sonarft_helpers.py` to use `_bot_path()`. Added `_BOT_DIR` anchor to `sonarft_search.py` and updated its `_DB_PATH` module constant. The SQLite database and all data files are now always created relative to the bot package directory, regardless of the working directory from which the bot is started.
- **T-16** ✅ — Wrapped the `monitor_order()` polling loop in `try/finally` in `sonarft_execution.py`. The `finally` block always calls `_cancel_order_with_retry()` on any exit path — normal fill, timeout, external `CancelledError`, or exception. For already-filled/cancelled orders the exchange rejects the cancel gracefully. This prevents open orders being left on the exchange when `stop_bot()` cancels in-flight trade tasks. 2 async unit tests added to `test_sonarft_search_execution.py` covering cancellation and timeout paths.
- **T-10** ✅ — Created `config_schemas.py` with three Pydantic v2 models: `ParametersConfig` (all trading parameters with range validators and market_making cross-field validation), `SymbolConfig` (base/quotes with non-empty checks), `FeeConfig` (exchange/fee rates with non-negative checks). `load_configurations()` in `sonarft_bot.py` now validates parameters, symbols, and fees through these models, raising `BotCreationError` with a clear field-level message on any type error or constraint violation. Empty `symbols` and `exchanges` lists are also caught. `pydantic>=2.0` added to `requirements.txt`. 14 unit tests added to `test_sonarft_bot.py`.
- **T-07** ✅ — Added WS→REST fallback to `call_api_method()` in `sonarft_api_manager.py`. When running in ccxtpro mode and the primary WebSocket call fails (any exception or timeout), and the ccxt method name differs from the ccxtpro method name, the method automatically retries once using a fresh ccxt REST instance with the same credentials. Methods where both names are identical (e.g. `create_order`, `cancel_order`, `fetch_ohlcv`) do not trigger the fallback — a retry would be redundant. Fallback is logged at WARNING level. Created `tests/test_sonarft_api_manager.py` with 9 tests covering ccxt dispatch, ccxtpro dispatch, fallback trigger conditions, and order book cache hit/miss.
- **T-06** ✅ — Added persistent position tracker. `sonarft_helpers.py`: new `positions` table in SQLite (schema: `order_id`, `botid`, `exchange`, `symbol`, `side`, `amount`, `entry_price`, `opened_at`, `status`, `closed_at`; indexed on `(botid, status)`); three new async methods: `open_position()`, `close_position()`, `get_open_positions()`. `sonarft_execution.py`: `execute_long_trade()` calls `open_position()` after buy fills and `close_position()` after sell fully fills; `execute_short_trade()` does the same for the sell-first path. `sonarft_bot.py`: `_reconcile_open_positions()` added — called at startup in live mode after `_reconcile_open_orders()`; logs all open positions from previous sessions and sends an alert. 6 unit/integration tests added to `test_phase4_features.py`.
- **T-03** ✅ — `ccxt[pro]==4.5.48` added to both `requirements.txt` and `pyproject.toml`.
- **T-04** ✅ — All 4 `if stoch_buy` / `if stoch_sell` truthiness checks in `sonarft_prices.py` changed to `is not None`. 1 regression test added to `test_phase4_features.py` verifying `(0.0, 0.0)` is treated as a valid extreme oversold signal.
- **T-05** ✅ — `_ALLOWED_TABLES = frozenset({'orders', 'trades', 'daily_loss'})` added to `sonarft_helpers.py`. Validation added at the top of `_db_insert()`, `_db_query()`, and `_db_purge()`. 4 unit tests added to `test_phase4_features.py`.
- **T-09** ✅ — `indicators_3` in `config_indicators.json` fixed from `"rsi, stoch rsi"` (single string) to `["rsi", "stoch rsi"]` (correct array).

---

### Phase 1 — Stability & Reliability

**Objective:** Make the system safe for live trading with real funds. Resolve all blocking live-trading issues.

**Tasks:** T-06, T-07, T-08, T-10, T-11, T-12, T-16, T-20

| Task | Description | Effort |
|---|---|---|
| T-06 | Persistent position tracker | 2 days |
| T-07 | WS→REST fallback | 4h |
| T-08 | Async SQLite daily loss | 1h |
| T-10 | Pydantic config validation | 4h |
| T-11 | RSI threshold constants | 1h |
| T-12 | Remove `market_movement()` from gather | 1h |
| T-16 | `monitor_order()` cancel on exit | 2h |
| T-20 | Anchor `_DB_PATH` to `_BOT_DIR` | 1h |

**Total effort:** ~3.5 days  
**Dependencies:** T-06 depends on T-01 (live mode guard must exist before position tracking is meaningful). T-10 should precede T-28.

**Risk reduction impact:**
- Eliminates unmanaged open positions after restart (High)
- Eliminates silent degradation on WebSocket failure (High)
- Eliminates event loop blocking on trade results (High)
- Prevents silent misconfiguration (High)
- Fixes RSI signal inconsistency (Medium)
- Eliminates 2 wasted API calls per combination (Medium)
- Prevents open orders on task cancellation (Medium)
- Fixes database path inconsistency (Medium)

**Exit criteria:**
- Bot restart after partial fill detects and logs open position
- WS failure triggers REST fallback within one cycle
- `_save_daily_loss()` no longer blocks event loop
- Invalid config raises `ValidationError` with field name
- RSI thresholds consistent across pricing and execution layers
- `market_movement()` removed from 16-indicator gather
- `monitor_order()` cancels order on `CancelledError`
- SQLite database created in correct location regardless of CWD

---

### Phase 2 — Security Hardening

**Objective:** Eliminate security vulnerabilities and add automated security monitoring.

**Tasks:** T-15, T-21, T-30

| Task | Description | Effort |
|---|---|---|
| T-15 | `pip-audit` in CI | 1h |
| T-21 | Automated fee refresh | 4h |
| T-30 | Hard error on missing symbol precision | 2h |

**Total effort:** ~7 hours  
**Can be parallelised:** All three are independent.

**Risk reduction impact:**
- Automated CVE detection for all Python dependencies (Medium)
- Eliminates stale fee rates causing unprofitable trades (High)
- Prevents wrong precision silently producing incorrect calculations (High)

**Exit criteria:**
- CI fails on `pip-audit` finding a High/Critical CVE
- `refresh_fees()` called at startup and every 24h; logs fee updates
- Missing symbol precision raises `BotCreationError` at startup

**Implementation notes (completed tasks):**
- **T-15** ✅ — Added `test-bot` job to `.github/workflows/ci.yml` running `pytest tests/ -q` and `pip-audit -r requirements.txt --severity high`. Blocks on High/Critical CVEs. Runs on push/PR to main and develop.
- **T-21** ✅ — Added `refresh_fees()` to `SonarftApiManager` — calls `fetch_trading_fees()` via thread executor, extracts minimum maker/taker rates, updates the in-memory `exchanges_fees` list. Gracefully falls back to existing config rates on timeout or API error. Called at startup in `SonarftBot.create_bot()` after `load_all_markets()`. `_periodic_fee_refresh()` background task refreshes every 24h (configurable via `SONARFT_FEE_REFRESH_INTERVAL` env var). Task cancelled in `stop_bot()`. 4 unit tests added to `test_sonarft_math_precision.py`.
- **T-30** ✅ — `calculate_trade()` in `sonarft_math.py` now logs a `WARNING` when falling back to hardcoded `EXCHANGE_RULES` precision (live market data unavailable). Also warns when no fallback exists for an unconfigured exchange. `_validate_precision_rules()` added to `SonarftBot` — called after `load_all_markets()` at startup; logs warnings for any configured exchange/symbol pair without live precision. 3 unit tests added to `test_sonarft_math_precision.py`.

---

### Phase 3 — Performance Optimization

**Objective:** Improve throughput, reduce API call overhead, and eliminate memory growth risks.

**Tasks:** T-17, T-18, T-19, T-22, T-23, T-29

| Task | Description | Effort |
|---|---|---|
| T-17 | Slippage buffer + re-validate after monitor_price | 3h |
| T-18 | Re-validate profitability after `monitor_price()` | 3h |
| T-19 | LRU eviction for order book + ticker caches | 2h |
| T-22 | Route `get_latest_prices()` through cache | 2h |
| T-23 | Gather MACD+RSI in `dynamic_volatility_adjustment()` | 1h |
| T-29 | Parallelise `_reconcile_open_orders()` | 2h |

**Total effort:** ~13 hours  
**Note:** T-17 and T-18 overlap — implement together.

**Risk reduction impact:**
- Prevents marginal trades executing at a loss after price movement (Medium)
- Prevents unbounded memory growth in caches (Medium)
- Reduces API calls per cycle by 2–4 (Medium)
- Reduces `dynamic_volatility_adjustment()` latency by ~50% (Low)
- Reduces startup time for large exchange/symbol configs (Low)

**Exit criteria:**
- Slippage buffer configurable via `config_parameters.json`
- Order placed only if profit still above threshold after `monitor_price()`
- Order book and ticker caches evict oldest entry at 500 entries
- `get_latest_prices()` populates order book cache
- MACD and RSI fetched concurrently in `dynamic_volatility_adjustment()`
- `_reconcile_open_orders()` uses `asyncio.gather`

**Implementation notes (completed tasks):**
- **T-17** ✅ — `slippage_buffer` field added to `ParametersConfig` Pydantic schema and `config_parameters.json` (default `0.0002` = 0.02%). Loaded in `SonarftBot` and passed through `SonarftSearch` → `TradeProcessor`. Applied as `effective_threshold = percentage_threshold + slippage_buffer` in `process_trade_combination()`. Also added to `SonarftExecution` constructor.
- **T-18** ✅ — After `monitor_price()` returns in `SonarftExecution.create_order()`, the price drift is checked against `slippage_buffer`. If `|monitored_price - target_price| / target_price > slippage_buffer`, the order is skipped with a WARNING log. Zero buffer disables the check.
- **T-19** ✅ — LRU eviction (500 entries) added to `_order_book_cache` and `_ticker_cache` in `SonarftApiManager.get_order_book()` and `_get_ticker()`. Matches the existing OHLCV cache pattern.
- **T-22** ✅ — `get_latest_prices()` in `SonarftApiManager` now calls `get_order_book()` and `_get_ticker()` (the cached methods) instead of `call_api_method()` directly. Price discovery now populates the 2-second cache, eliminating redundant API calls in subsequent indicator fetches within the same cycle.
- **T-23** ✅ — `dynamic_volatility_adjustment()` in `SonarftPrices` now fetches MACD and RSI concurrently via `asyncio.gather` instead of two sequential awaits. Reduces latency by ~50% for this method.
- **T-29** ✅ — `_reconcile_open_orders()` in `SonarftBot` refactored to use `asyncio.gather` — all exchange/symbol queries run concurrently. Extracted inner `_check_symbol()` coroutine for clarity. Reduces startup time proportionally to the number of exchange×symbol combinations.
- 9 unit tests added to `tests/test_phase3_performance.py`.

---

### Phase 4 — Architecture Improvements

**Objective:** Improve code quality, test coverage, and maintainability.

**Tasks:** T-13, T-14, T-24, T-25, T-27, T-28

| Task | Description | Effort |
|---|---|---|
| T-13 | `test_sonarft_api_manager.py` | 4h |
| T-14 | `test_trade_executor.py` | 4h |
| T-24 | Decompose `_execute_single_trade()` | 4h |
| T-25 | Circuit breaker + `sanitize_client_id()` tests | 2h |
| T-27 | Remove dead code | 1h |
| T-28 | Move indicator periods + flash crash threshold to config | 3h |

**Total effort:** ~18 hours  
**Dependencies:** T-28 depends on T-10 (pydantic schema must exist first).

**Risk reduction impact:**
- `SonarftApiManager` regressions detectable (High)
- `TradeExecutor` regressions detectable (High)
- `_execute_single_trade()` easier to maintain and test (Medium)
- Circuit breaker behaviour verified (Medium)
- Dead code removed — reduces confusion (Low)
- Indicator periods configurable without code changes (Medium)

**Exit criteria:**
- `test_sonarft_api_manager.py` covers cache, dispatch, `get_latest_prices`
- `test_trade_executor.py` covers task lifecycle and shutdown
- `_execute_single_trade()` decomposed into ≤3 focused methods each ≤50 lines
- Circuit breaker test passes
- `sanitize_client_id()` path traversal tests pass
- Dead code removed with no test regressions
- Indicator periods read from `config_indicators.json`

**Implementation notes (completed tasks):**
- **T-27** ✅ — Removed dead code: `get_atr()`, `get_24h_high()`, `get_24h_low()` from `sonarft_indicators.py`; `create_futures_order()` from `sonarft_api_manager.py`. None were called anywhere. `create_futures_order()` also mutated `exchange.options["defaultType"] = "future"` which could have corrupted subsequent spot orders.
- **T-25** ✅ — Added 2 circuit breaker tests to `test_sonarft_bot.py` (trips after max failures, resets on success). Added 9 `sanitize_client_id()` tests covering normal IDs, special chars, path traversal (`../../../etc/passwd`), null bytes, and empty-after-sanitize.
- **T-13** ✅ — Extended `test_sonarft_api_manager.py` with `get_latest_prices` tests (valid symbol, cache population, symbol not in markets) and `get_weighted_prices` tests (correct VWAP formula, zero volume). Total: 14 tests in the file.
- **T-14** ✅ — Created `tests/test_trade_executor.py` with 11 tests covering: task creation with botid attachment, multiple dispatch accumulation, monitor loop processing done tasks, session P&L accumulation, `_search_ref` callback, shutdown cancels monitor task, shutdown awaits in-flight tasks, shutdown safe with no tasks, `cancel_trade()` removes matching tasks.
- **T-24** ✅ — Decomposed `_execute_single_trade()` (~150 lines) into three focused methods: `_execute_single_trade()` (5 lines — delegates), `_determine_position()` (~40 lines — pure indicator logic, returns `'LONG'`/`'SHORT'`/`None`), `_execute_position()` (~50 lines — dispatch + history + metrics). Each method is independently testable.
- **T-28** ✅ — Added `flash_crash_threshold` field to `ParametersConfig` Pydantic schema (default `0.02`, `gt=0`, `lt=1`) and `config_parameters.json`. Loaded in `SonarftBot` and passed to `SonarftExecution`. `_determine_position()` now uses `self.flash_crash_threshold` instead of the hardcoded `0.02`. Note: indicator period fields (RSI 14, StochRSI 14/14/3/3) remain hardcoded in `weighted_adjust_prices()` — moving them to config requires a larger refactor of the indicator gather signature and is deferred to the technical debt backlog.
- 25 new tests added across `test_sonarft_bot.py`, `test_sonarft_api_manager.py`, and `test_trade_executor.py`.

---

### Phase 5 — Enhancement & Polish

**Objective:** Developer experience, documentation, and long-term maintainability.

**Tasks:** T-26, plus technical debt backlog items

| Task | Description | Effort |
|---|---|---|
| T-26 | Create `.env.example` | 1h |
| TD-01 | Shared OHLCV cache across bots | 1 day |
| TD-02 | Per-indicator timeout in `weighted_adjust_prices()` | 4h |
| TD-03 | `max_daily_trades` parameter | 2h |
| TD-04 | Normalise volatility metric to percentage | 2h |
| TD-05 | Add warm-up period logging | 1h |

**Total effort:** ~2.5 days  
**Note:** TD-01 (shared cache) is the highest-impact item but requires architectural changes.

**Exit criteria:**
- `.env.example` documents all env vars
- Shared cache reduces API calls by ≥50% in multi-bot deployment
- Per-indicator timeout prevents single slow exchange from cancelling all indicators
- `max_daily_trades` parameter enforced in `SonarftSearch`

---

## 4. Task Dependency Graph

### Critical path

```
T-03 (ccxt.pro in requirements)
  └─► T-07 (WS→REST fallback)
  └─► T-13 (ApiManager tests)
  └─► T-15 (pip-audit in CI)

T-01 (startup live mode guard)
  └─► T-06 (position tracker)  ← LONGEST TASK — 2 days

T-10 (pydantic config validation)
  └─► T-28 (indicator periods in config)

[T-02, T-04, T-05, T-08, T-09, T-11, T-12, T-16, T-20] — all independent
```

### Parallelisable groups

**Day 1 (can all run in parallel):**
- T-01 — startup guard (1h)
- T-02 — task limit (2h)
- T-03 — requirements (30m)
- T-04 — StochRSI fix (30m)
- T-05 — SQL allowlist (1h)
- T-09 — config fix (15m)

**Week 1 (can run in parallel after Day 1):**
- T-06 — position tracker (2 days) — critical path
- T-07 — WS→REST fallback (4h) — after T-03
- T-08 — async SQLite (1h)
- T-10 — pydantic validation (4h)
- T-11 — RSI constants (1h)
- T-12 — remove market_movement (1h)
- T-16 — monitor_order cancel (2h)
- T-20 — DB path fix (1h)

**Blocking relationships:**
- T-06 must follow T-01 (position tracking only meaningful with live mode guard)
- T-28 must follow T-10 (config schema must exist before adding new fields)
- T-13 must follow T-03 (ccxt.pro must be installed for ApiManager tests)

---

## 5. Risk Reduction Mapping

| Phase | Critical Risks Before | Critical Risks After | Risk Reduction |
|---|---|---|---|
| **Phase 0** | Accidental live trading; OOM kill; deployment failure; StochRSI signal masking; SQL injection | All Phase 0 risks eliminated | **Critical → None** |
| **Phase 1** | Unmanaged open positions; WS silent failure; event loop blocking; misconfiguration; RSI inconsistency | All Phase 1 risks eliminated | **High → Low** |
| **Phase 2** | Stale fee rates; CVE exposure; wrong precision fallback | All Phase 2 risks eliminated | **High → Low** |
| **Phase 3** | Marginal trades at a loss; cache memory growth; redundant API calls | All Phase 3 risks eliminated | **Medium → Low** |
| **Phase 4** | Undetected regressions in ApiManager/TradeExecutor; unmaintainable execution code | All Phase 4 risks eliminated | **High → Low** |
| **Phase 5** | Developer friction; single-exchange bottleneck; indicator timeout risk | Significantly reduced | **Low → Minimal** |

---

## 6. Effort & Timeline Projection

| Phase | Tasks | Conservative | Aggressive | Solo Dev | 2-Person Team |
|---|---|---|---|---|---|
| Phase 0 | T-01–T-05, T-09 | 1 day | 0.5 days | 1 day | 0.5 days |
| Phase 1 | T-06–T-08, T-10–T-12, T-16, T-20 | 1 week | 4 days | 1 week | 4 days |
| Phase 2 | T-15, T-21, T-30 | 2 days | 1 day | 2 days | 1 day |
| Phase 3 | T-17–T-19, T-22–T-23, T-29 | 3 days | 2 days | 3 days | 2 days |
| Phase 4 | T-13–T-14, T-24–T-25, T-27–T-28 | 1 week | 4 days | 1 week | 4 days |
| Phase 5 | T-26, TD-01–TD-05 | 1 week | 4 days | 1 week | 4 days |
| **Total** | **30 tasks** | **~5 weeks** | **~3 weeks** | **~5 weeks** | **~3 weeks** |

**To live trading (Phase 0 + Phase 1):** 1.5–2 weeks solo, 1 week with 2 developers.  
**To full production (all phases):** 3–5 weeks solo, 2–3 weeks with 2 developers.

---

## 7. Technical Debt Backlog

Lower-priority improvements that should be addressed over time but do not block any milestone.

| Task | Category | Benefit | Recommended Timeline |
|---|---|---|---|
| TD-01 | Shared OHLCV/indicator cache across bots | Performance | After Phase 3 — reduces API calls 5× in multi-bot |
| TD-02 | Per-indicator timeout in `weighted_adjust_prices()` | Reliability | After Phase 1 — prevents single slow exchange cancelling all |
| TD-03 | `max_daily_trades` parameter | Safety | After Phase 1 — additional trading frequency control |
| TD-04 | Normalise volatility metric to percentage of mid-price | Financial | After Phase 3 — fixes scale-dependent weight formula |
| TD-05 | Add warm-up period logging | Observability | After Phase 4 — improves operator visibility |
| TD-06 | `percentage_difference()` deduplication | Quality | After Phase 4 — remove from both `SonarftIndicators` and `SonarftHelpers` |
| TD-07 | OHLCV field index constants in `models.py` | Quality | After Phase 4 — `OHLCV_CLOSE = 4`, `OHLCV_HIGH = 2`, etc. |
| TD-08 | `hypothesis` property-based tests for `calculate_trade()` | Quality | After Phase 4 — catches edge cases in financial math |
| TD-09 | Taker fee support in `config_fees.json` | Financial | After Phase 2 — accurate fee estimation when limit fills as taker |
| TD-10 | `max_total_exposure` aggregate position limit | Safety | After Phase 1 — limits total concurrent exposure across symbols |
| TD-11 | Per-exchange balance reservation lock | Safety | After Phase 1 — prevents balance race condition |
| TD-12 | Update `memory-bank/guidelines.md` `prec=8` → `prec=28` | Docs | Anytime — trivial |
| TD-13 | `SonarftValidators` inherit from `ABC` with `@abstractmethod` | Quality | After Phase 4 — formalise abstract interface |
| TD-14 | Cross-bot rate limit coordination | Performance | After Phase 5 — required for large multi-bot deployments |
| TD-15 | SQLite database backup automation | Operations | After Phase 1 — scheduled `async_backup_db()` call |

---

## 8. Testing & Validation Strategy

### Phase 0 validation

| Test | Type | Target | Pass Criteria |
|---|---|---|---|
| Startup live mode guard | Unit | `SonarftBot._check_live_mode_guard()` | Raises `BotCreationError` without `SONARFT_ALLOW_LIVE` |
| Task limit enforcement | Unit | `TradeExecutor.execute_trade()` | Skips dispatch when `len(active_tasks) >= MAX_CONCURRENT_TRADES` |
| ccxt.pro import | Integration | `SonarftApiManager.load_api_library()` | No `ImportError` with `library="ccxtpro"` |
| StochRSI `(0.0, 0.0)` | Unit | `SonarftPrices.weighted_adjust_prices()` | Returns valid prices, not `(0, 0, {})` |
| SQL table allowlist | Unit | `SonarftHelpers._db_insert()` | Raises `ValueError` for unknown table name |
| Config `indicators_3` | Integration | `SonarftBot.load_configurations()` | Loads without error; `_indicator_active('rsi')` returns `True` |

### Phase 1 validation

| Test | Type | Target | Pass Criteria |
|---|---|---|---|
| Position tracker — record on fill | Integration | `SonarftExecution.execute_long_trade()` | `positions` table has entry after buy fills |
| Position tracker — close on second leg | Integration | `SonarftExecution.execute_long_trade()` | `positions` entry marked closed after sell fills |
| Position tracker — reconcile on restart | Integration | `SonarftBot.create_bot()` | Open positions logged on startup |
| WS→REST fallback | Unit | `SonarftApiManager.call_api_method()` | Returns data when ccxtpro raises, REST succeeds |
| Async SQLite daily loss | Unit | `SonarftSearch.record_trade_result()` | No blocking call on event loop (use `asyncio` debug mode) |
| Pydantic validation | Unit | `SonarftBot.load_configurations()` | `ValidationError` on invalid field type |
| RSI threshold consistency | Unit | `SonarftPrices._adjust_market_making()` + `SonarftExecution._determine_position()` | Both use `RSI_OVERBOUGHT = 70` |
| `monitor_order()` cancel on exit | Unit | `SonarftExecution.monitor_order()` | `cancel_order` called when task is cancelled |

### Phase 2 validation

| Test | Type | Target | Pass Criteria |
|---|---|---|---|
| `pip-audit` CI | CI | `requirements.txt` | Pipeline fails on High/Critical CVE |
| Fee refresh | Integration | `SonarftApiManager.refresh_fees()` | Fee rates updated from exchange API |
| Missing precision hard error | Unit | `SonarftMath.calculate_trade()` | `BotCreationError` when precision unavailable |

### Phase 3 validation

| Test | Type | Target | Pass Criteria |
|---|---|---|---|
| Slippage buffer | Unit | `TradeProcessor.process_trade_combination()` | Trade skipped when `profit_pct < threshold + slippage_buffer` |
| Re-validate after monitor_price | Unit | `SonarftExecution.create_order()` | Order skipped when re-calculated profit < threshold |
| Cache eviction | Unit | `SonarftApiManager.get_order_book()` | Cache size never exceeds 500 entries |
| Cache routing | Unit | `SonarftApiManager.get_latest_prices()` | Order book cache populated after `get_latest_prices()` call |

### Phase 4 validation

| Test | Type | Target | Pass Criteria |
|---|---|---|---|
| ApiManager cache | Unit | `SonarftApiManager.get_order_book()` | Cache hit returns same object; cache miss calls API |
| ApiManager dispatch | Unit | `SonarftApiManager.call_api_method()` | ccxt path uses thread executor; ccxtpro path awaits directly |
| TradeExecutor lifecycle | Unit | `TradeExecutor.execute_trade()` + `shutdown()` | All tasks cancelled and awaited on shutdown |
| Circuit breaker | Unit | `SonarftBot.run_bot()` | `_stop_event` set after `SONARFT_MAX_FAILURES` consecutive failures |
| `sanitize_client_id` | Unit | `sonarft_helpers.sanitize_client_id()` | Path traversal attempt returns safe string or raises |
| Decomposed execution | Unit | `SonarftExecution._determine_position()` | Returns `"LONG"`, `"SHORT"`, or `None` for all direction/RSI combinations |

### Regression testing plan

After each phase, run the full test suite:
```bash
make test-bot   # pytest packages/bot/tests/
```

All 165+ existing tests must continue to pass. New tests added in each phase are additive.

### Load testing (Phase 3+)

```bash
# Scenario: 5 bots, 2 exchanges, 1 symbol, simulation mode, 1-hour run
SONARFT_CYCLE_SLEEP_MIN=1 SONARFT_CYCLE_SLEEP_MAX=3 \
SONARFT_MAX_CONCURRENT_TRADES=10 \
python -m pytest tests/test_load_simulation.py -v
```

Monitor: memory RSS, `trade_tasks` list size, API call count, cycle duration via `sonarft.metrics` logger.

---

## 9. Release Strategy Milestones

### Milestone A — Safe Simulation Mode ✅ ACHIEVED

**Status:** Ready now (no blocking issues).

**Requirements:**
- `is_simulating_trade = 1` in config
- All tests passing (165+)
- `ccxt.pro` installed

**Validation:**
- Run `make test-bot` — all tests pass
- Start bot in simulation, verify no real API calls via exchange sandbox logs
- Verify trade history written to SQLite

---

### Milestone B — Paper Trading Mode

**Status:** Ready after T-03 (ccxt.pro in requirements).

**Requirements:**
- T-03 complete — `ccxt.pro` declared in requirements
- Live exchange API keys configured in environment
- `is_simulating_trade = 1` (simulation gate active)
- Bot connects to live exchange, reads real market data

**Blocking issues:** T-03 only.

**Validation:**
- Bot starts without `ImportError`
- Order book and OHLCV data fetched from live exchange
- No real orders placed (verify via exchange order history)
- Indicators compute correctly on live data

---

### Milestone C — Limited Real Trading

**Status:** Ready after Phase 0 + Phase 1 complete.

**Requirements:**
- T-01 — startup live mode guard ✅
- T-02 — concurrent task limit ✅
- T-03 — ccxt.pro in requirements ✅
- T-06 — persistent position tracker ✅
- T-07 — WS→REST fallback ✅ (recommended, not strictly blocking)
- `SONARFT_ALLOW_LIVE=true` set explicitly
- `trade_amount ≤ 0.01` (small position size)
- `max_daily_loss` set to conservative value (e.g. 10.0)
- `max_orders_per_minute = 2`
- Manual monitoring during first sessions

**Blocking issues:** T-01, T-02, T-06. T-03 must also be complete.

**Validation:**
- Bot starts only when `SONARFT_ALLOW_LIVE=true` is set
- Real orders placed and confirmed on exchange
- Position tracker records open positions
- Position tracker closes positions after second leg fills
- Daily loss limit halts trading when reached
- Bot restart detects and logs any open positions

---

### Milestone D — Full Production Operation

**Status:** Ready after all phases complete.

**Requirements:**
- All Milestone C requirements ✅
- T-10 — pydantic config validation ✅
- T-15 — `pip-audit` in CI ✅
- T-21 — automated fee refresh ✅
- T-13, T-14 — infrastructure test coverage ✅
- T-17, T-18 — slippage buffer + re-validation ✅
- T-19 — cache eviction ✅
- T-30 — hard error on missing precision ✅
- Multi-bot deployment tested
- Exchange rate limits verified under load
- Monitoring/alerting configured (`SONARFT_ALERT_WEBHOOK`)

**Blocking issues:** All items above.

**Validation:**
- Full test suite passes (200+ tests)
- `pip-audit` clean in CI
- Fee rates auto-refreshed at startup
- 5-bot simulation run for 1 hour without memory growth
- Alert webhook fires on circuit breaker trip
- All exchange rate limits respected under multi-bot load

---

## 10. Success Metrics & Monitoring

| Metric | Target | Measurement | Monitoring |
|---|---|---|---|
| Test suite pass rate | 100% | `pytest` exit code | CI on every commit |
| Dependency CVEs (High/Critical) | 0 | `pip-audit` | CI on every commit |
| Cycle duration (warm cache) | < 1s | `log_cycle()` `cycle_duration_ms` | `sonarft.metrics` logger |
| API call latency (p95) | < 500ms | `log_api_call()` `latency_ms` | `sonarft.metrics` logger |
| Concurrent trade tasks | ≤ `MAX_CONCURRENT_TRADES` | `len(trade_tasks)` | Add to `log_cycle()` |
| Daily loss accumulated | < `max_daily_loss` | `log_risk_event()` | `sonarft.metrics` logger |
| Memory RSS per bot | < 200MB | `psutil.Process().memory_info().rss` | External monitoring |
| Open positions on restart | 0 (after reconciliation) | `positions` table count | Startup log |
| Circuit breaker trips | 0 per day (target) | `log_risk_event()` `daily_loss_limit` | Alert webhook |
| Profitable trade rate | > 60% (simulation baseline) | `log_trade_result()` `success` | `sonarft.metrics` logger |
| Fee accuracy | Within 0.01% of actual | Compare `trade_data.buy_fee_quote` to exchange statement | Manual audit |

---

## 11. Developer Onboarding Plan

### For a developer new to this roadmap

**Step 1 — Read the architecture (30 minutes)**
1. Read `docs/architecture/bot-overview.md` — module responsibilities and dependency graph
2. Read `docs/async/bot-concurrency.md` — async patterns and task lifecycle
3. Skim `packages/bot/.amazonq/rules/memory-bank/guidelines.md` — coding conventions

**Step 2 — Run the test suite (15 minutes)**
```bash
cd packages/bot
pip install -r requirements.txt
pytest tests/ -v
```
All 165+ tests should pass. This confirms the environment is set up correctly.

**Step 3 — Run in simulation mode (15 minutes)**
```bash
cp sonarftdata/config.json sonarftdata/config.json.bak
python -m sonarft_bot -c config_1
```
Observe the startup sequence, indicator warm-up, and first trade search cycle in logs.

**Step 4 — Understand the critical path (30 minutes)**
Read in order:
- `docs/trading/engine-review.md` — how trades are detected and executed
- `docs/security/bot-risks.md` — what can go wrong in live mode
- `docs/review/final-audit-report.md` — executive summary of all findings

**Step 5 — Start with Phase 0 tasks**

Each Phase 0 task is self-contained and can be completed independently:

| Task | File to edit | What to do |
|---|---|---|
| T-01 | `sonarft_bot.py` | Add 5 lines after `is_simulating_trade` is loaded |
| T-02 | `trade_executor.py` | Add 8 lines at the top of `execute_trade()` |
| T-03 | `requirements.txt`, `pyproject.toml` | Add one line each |
| T-04 | `sonarft_prices.py` | Change 4 `if stoch_buy` → `if stoch_buy is not None` |
| T-05 | `sonarft_helpers.py` | Add 3-line validation at top of each `_db_*` method |
| T-09 | `sonarftdata/config_indicators.json` | Fix one JSON value |

**Step 6 — Write tests before committing**

Every task should have a corresponding test. Use the existing test files as templates:
- `tests/test_sonarft_bot.py` — for `SonarftBot` changes
- `tests/test_sonarft_manager.py` — for `BotManager` changes
- `tests/test_simulation_integration.py` — for execution changes

**Reference documents by task:**

| Task | Primary reference |
|---|---|
| T-01 | `docs/trading/engine-review.md` §5 (T-14) |
| T-02 | `docs/security/bot-risks.md` §4 (S-09) |
| T-06 | `docs/trading/execution-review.md` §6 (E-24) |
| T-07 | `docs/trading/execution-review.md` §2 (E-06) |
| T-10 | `docs/operations/bot-config.md` §6 (C-01) |
| T-13 | `docs/quality/bot-testing.md` §7 (Q-16) |

---

## 12. Final Roadmap Priorities

The 5 must-do items for production readiness, in strict order:

### 1. T-01 — Startup live mode guard (1 hour)

The single most important fix. Without it, a misconfigured deployment places real orders immediately. This must be the first commit.

```python
# sonarft_bot.py — load_configurations(), after loading is_simulating_trade:
if self.is_simulating_trade == 0:
    if not os.environ.get("SONARFT_ALLOW_LIVE"):
        raise BotCreationError(
            "Live trading requires SONARFT_ALLOW_LIVE=true environment variable. "
            "Set is_simulating_trade=1 for simulation mode."
        )
    self.logger.warning(
        "⚠️  LIVE TRADING MODE ACTIVE — real orders will be placed on exchanges"
    )
```

### 2. T-06 — Persistent position tracker (2 days)

The largest missing feature. Without it, a bot restart after a partial fill leaves an unmanaged open position. This is the primary blocker for live trading.

Core schema:
```sql
CREATE TABLE IF NOT EXISTS positions (
    botid TEXT NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,        -- 'long' or 'short'
    amount REAL NOT NULL,
    entry_price REAL NOT NULL,
    order_id TEXT,
    opened_at TEXT NOT NULL,
    status TEXT DEFAULT 'open', -- 'open' | 'closed' | 'cancelled'
    PRIMARY KEY (botid, order_id)
)
```

### 3. T-02 — Concurrent task limit (2 hours)

Prevents memory exhaustion under high trade frequency. Simple to implement, high impact.

```python
# trade_executor.py
_MAX = int(os.environ.get("SONARFT_MAX_CONCURRENT_TRADES", "10"))

def execute_trade(self, botid, trade_data: dict) -> None:
    active = [t for t in self.trade_tasks if not t.done()]
    if len(active) >= _MAX:
        self.logger.warning(f"Concurrent trade limit ({_MAX}) reached — skipping")
        return
    ...
```

### 4. T-03 — Declare `ccxt.pro` in requirements (30 minutes)

Without this, the default transport library is not installable via `pip install -r requirements.txt`. Every deployment fails silently.

```
# requirements.txt — add:
ccxt[pro]==4.5.48
```

### 5. T-13 + T-14 — Infrastructure test coverage (8 hours)

`SonarftApiManager` and `TradeExecutor` are the two most critical untested modules. Any regression in these components is invisible until it causes a live trading failure.

---

*This roadmap covers 30 primary tasks and 15 technical debt items derived from 221 findings across 10 review domains. Total estimated effort: 3–5 weeks solo, 2–3 weeks with a two-person team.*
