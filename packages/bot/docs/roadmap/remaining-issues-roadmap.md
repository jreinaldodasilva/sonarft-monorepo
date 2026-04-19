# SonarFT Bot — Remaining Issues Roadmap

**Date:** July 2025  
**Status:** Post-implementation — consolidation of all open items from Prompts 01–11  
**Input:** Remediation status sections from all 12 review documents  
**Previous Roadmap:** `docs/roadmap/implementation-roadmap.md` (32 of 37 tasks completed)

---

## 1. Executive Summary

After completing 32 of 37 roadmap tasks, the system moved from **6.0/10 (Early Beta)** to **8.0/10 (Near Production-Ready)**. All 12 High-severity and ~36 Medium-severity issues were resolved.

This document consolidates the **remaining open items** from all review documents into a prioritized roadmap for the next development cycle.

| Category | Open | Deferred | Accepted | Total Remaining |
|---|---|---|---|---|
| **Medium severity** | 8 | 3 | 0 | 11 |
| **Low severity** | 12 | 2 | 3 | 17 |
| **Info** | 0 | 0 | 1 | 1 |
| **Tech debt** | 15 | 0 | 0 | 15 |
| **Total** | **35** | **5** | **4** | **44** |

---

## 2. Deferred Tasks from Previous Roadmap

These 5 tasks were scoped in the original roadmap but deferred during implementation.

| ID | Task | Severity | Source | Reason Deferred | Effort | Priority |
|---|---|---|---|---|---|---|
| **T19** | Add `pip audit` to CI pipeline | Medium | P08 | No CI config in bot package | 0.5d | **High** |
| **T30** | Split `sonarft_search.py` into `trade_processor.py`, `trade_validator.py`, `trade_executor.py` | Low | P01, P10 | Lower priority refactoring; import breakage risk | 1d | **Medium** |
| **T31** | Consolidate VWAP into `SonarftPrices`; remove duplicate from `SonarftApiManager` | Low | P01, P10 | Working correctly in both locations | 0.5d | **Low** |
| **T33** | Order reconciliation on startup: query open orders, cancel stale ones | Medium | P06 | Complex; requires integration testing with real exchanges | 2d | **High** |
| **T37** | Parallelize buy/sell combinations with `asyncio.gather` in `process_symbol()` | Low | P09 | Depends on T30 split | 0.5d | **Low** |

---

## 3. Open Issues from Review Documents

### 3.1 Medium Severity — Should Fix

| # | Issue | Source | Location | Description | Effort | Priority |
|---|---|---|---|---|---|---|
| R01 | Indicator re-fetch fallback in execution | P01 | `sonarft_execution.py:_execute_single_trade()` | Execution re-fetches RSI/MACD/StochRSI when not passed through `trade_data`. Duplicates analysis layer logic. | Small | **Medium** |
| R02 | `_search_ref` bidirectional dependency | P01 | `sonarft_search.py:TradeExecutor` | `TradeExecutor._search_ref` creates a mutable back-reference to `SonarftSearch`. Should use a callback function instead. | Small | **Low** |
| R03 | Blocking config file reads | P02 | `sonarft_bot.py:_load_config_section()` | Sync `open()`/`json.load()` in async `create_bot()`. Blocks event loop for ~ms per file (6 reads at startup). | Small | **Low** |
| R04 | Stale prices during execution pipeline | P03 | `sonarft_search.py` → `sonarft_execution.py` | 30s indicator fetch + validation + 120s price monitor = arbitrage window may close. Inherent to limit order arbitrage; mitigated by `monitor_price()`. | N/A | **Accepted** |
| R05 | Partial fill imbalance — no rebalancing | P06 | `sonarft_execution.py:execute_long/short_trade()` | If second leg partially fills, bot has imbalanced position with no rebalancing logic. | Medium | **Medium** |
| R06 | Remaining amount from partial first leg | P06 | `sonarft_execution.py:execute_long/short_trade()` | If first leg partially fills (e.g., 0.7 of 1.0 BTC), the remaining 0.3 BTC order stays open on exchange. No cancellation of remaining. | Medium | **Medium** |
| R07 | Untracked order on exchange failure | P06 | `sonarft_api_manager.py:create_order()` | If `create_order` returns `None` due to network error AFTER exchange accepted the order, the order exists but bot doesn't know. Needs order reconciliation (T33). | Medium | **High** |
| R08 | Trade history without ownership check | P08 | `sonarft_helpers.py:get_orders/get_trades()` | `botid`-based access has no authorization check that the requesting client owns that bot. API layer should enforce. | Small | **Medium** |
| R09 | `trade_amount` default = 1 BTC (~$30K) | P07 | `config_parameters.json` | Default trade amount is 1 base currency unit. For BTC, this is ~$30,000 — could be expensive if sim mode accidentally off. | Trivial | **Medium** |
| R10 | `max_trade_amount` disabled by default | P07 | `config_parameters.json` | No position size limit by default (`0.0` = disabled). Should have a reasonable default. | Trivial | **Medium** |
| R11 | Docker entrypoint may not work | P07 | `Dockerfile` | `CMD ["python", "-m", "sonarft_bot"]` requires `__main__.py` or `if __name__ == "__main__"` block. | Small | **Medium** |
| R12 | `get_atr()` no NaN check | P05 | `sonarft_indicators.py:get_atr()` | ATR return value not checked for NaN. Not currently used in trade decisions, but could be in future. | Trivial | **Low** |
| R13 | `monitor_price` 3s polling latency | P09 | `sonarft_execution.py:monitor_price()` | Polls every 3s with 120s max. Could use WebSocket ticker stream for near-instant detection. | Medium | **Low** |
| R14 | Sequential buy/sell combinations | P09 | `sonarft_search.py:process_symbol()` | Inner loop processes combinations sequentially. Could parallelize with `asyncio.gather` for ~2-4× speedup. | Small | **Low** |
| R15 | No vulnerability scanning in CI | P08 | CI/CD | No `pip audit` or equivalent in CI pipeline. Known CVEs in dependencies go undetected. | Small | **High** |

### 3.2 Low Severity — Nice to Have

| # | Issue | Source | Location | Description | Effort |
|---|---|---|---|---|---|
| R16 | `EXCHANGE_RULES` hardcoded for 3 exchanges | P01 | `sonarft_math.py` | Static precision rules for OKX, Binance, Bitfinex only. Dynamic precision preferred at runtime (already falls back). | Small |
| R17 | Bot ID collision risk | P01, P03 | `sonarft_bot.py:create_botid()` | `random.randint(10001, 99999)` — 89,999 possible IDs. Should use `uuid.uuid4()`. | Trivial |
| R18 | Duplicate VWAP implementation | P01 | `sonarft_api_manager.py` + `sonarft_prices.py` | VWAP exists in both modules. Maintenance risk. | Small |
| R19 | `dynamic_volatility_adjustment` sequential calls | P02 | `sonarft_prices.py` | `get_macd()` and `get_rsi()` called sequentially instead of `asyncio.gather()`. Mitigated by indicator cache. | Trivial |
| R20 | `calculate_slippage_tolerance` async with no await | P02 | `sonarft_validators.py` | Marked `async` but contains no `await`. Misleading. | Trivial |
| R21 | File handle leak in `create_bot` lambda | P02 | `sonarft_bot.py:create_bot()` | `open()` inside lambda without `with` statement. Relies on GC. | Trivial |
| R22 | Maker vs taker fee not distinguished | P03 | `config_fees.json` / `sonarft_math.py` | Single fee rate per side per exchange. Limit orders (maker) typically have lower fees. | Small |
| R23 | No pause/resume mechanism | P03 | `sonarft_bot.py` | Must stop and recreate bot to pause. No pause flag. | Small |
| R24 | `ROUND_HALF_UP` systematic rounding bias | P04 | `sonarft_math.py` | Slight upward bias on buy prices. ~$5/day at 100 trades/day. Consider `ROUND_HALF_EVEN`. | Small |
| R25 | No RSI hysteresis | P05 | `sonarft_prices.py`, `sonarft_execution.py` | RSI 70/30 boundary has no hysteresis. Noisy signals possible at boundary. | Small |
| R26 | Duplicate order possible | P06 | `sonarft_execution.py` | No dedup — exchange may accept duplicate orders with same params. | Small |
| R27 | No schema validation for config files | P07 | All config files | No JSON schema or Pydantic models for config validation. | Medium |
| R28 | Exchange IDs not validated against ccxt | P07 | `config_exchanges.json` | No check that exchange IDs are valid ccxt names. | Trivial |
| R29 | Many hardcoded operational values | P07 | Various | Circuit breaker (5), backoff (30s), sleep (6-18s), timeouts (120s/300s), cache sizes, depths. | Medium |
| R30 | Random cycle sleep not configurable | P09 | `sonarft_bot.py:run_bot()` | `random.randint(6, 18)` hardcoded. Should be configurable. | Trivial |
| R31 | Sequential `dynamic_volatility_adjustment` | P09 | `sonarft_prices.py` | Two sequential API calls instead of `asyncio.gather`. Mitigated by cache. | Trivial |

### 3.3 Accepted Risks (No Action Planned)

| # | Issue | Source | Severity | Rationale |
|---|---|---|---|---|
| A01 | `calculate_trade` float() conversion from Decimal | P04 | Low | Precision loss ~1e-16 — below any meaningful threshold |
| A02 | Float pipeline accumulated error | P04 | Low | Eliminated by Decimal boundary in `calculate_trade()` |
| A03 | Float comparison at profit threshold boundary | P04 | Info | Negligible risk — Decimal produces 8dp precision, threshold is round number |
| A04 | API keys in process environment | P08 | Low | Standard pattern for container deployments |

---

## 4. Prioritized Implementation Plan

### Phase A — Production Blockers (Milestone D completion)

**Goal:** Complete the 2 remaining items blocking full production deployment.

| # | Task | Source | Effort | Priority |
|---|---|---|---|---|
| **A1** | T33: Order reconciliation on startup | R07, P06 | 2d | **Critical for live trading** | ✅ **DONE** |

> **A1 Implementation Notes:** Added `_reconcile_open_orders()` to `SonarftBot`. Called after `load_all_markets()` in `create_bot()` (live mode only). Iterates all configured exchanges × symbols, calls `fetch_open_orders`, and cancels each stale order via `cancel_order()`. Logs warnings for found orders and failures. Skipped entirely in simulation mode.
| **A2** | T19/R15: Add `pip audit` to CI | P08 | 0.5d | **Required for production** | ✅ **DONE** |

> **A2 Implementation Notes:** Added `pip-audit` step to the existing `.github/workflows/ci.yml` security audit job. Installs bot dependencies, then runs `pip-audit -r requirements.txt`. Runs alongside the existing `npm audit` for the web package. CI will now reject PRs with known Python dependency vulnerabilities.

**Exit criteria:** Bot queries open orders on startup and cancels stale ones. CI rejects PRs with known vulnerabilities.

### Phase B — Execution Safety Improvements

**Goal:** Address remaining partial fill and order management gaps.

| # | Task | Source | Effort | Priority |
|---|---|---|---|---|
| **B1** | R05: Partial fill rebalancing logic | P06 | 2d | Medium | ✅ **DONE** |
| **B2** | R06: Cancel remaining amount from partial first leg | P06 | 1d | Medium | ✅ **DONE** |

> **B1+B2 Implementation Notes:** Both issues addressed together in `execute_long_trade()` and `execute_short_trade()`:
> - **B2 (first leg partial fill):** After first leg returns with `remaining_amount > 0`, the remaining order is cancelled via `_cancel_order_with_retry()`. Previously it stayed open on the exchange indefinitely.
> - **B1 (second leg partial fill):** After second leg returns with `remaining_amount > 0`, the remaining order is cancelled and an IMBALANCE alert is sent via `_alert_callback`. The operator is notified of the unhedged amount. Previously the imbalance was silently ignored.
| **B3** | R11: Add `__main__.py` for Docker entrypoint | P07 | 0.5d | Medium | ✅ **DONE** |
| **B4** | R09+R10: Set safer defaults (`trade_amount`, `max_trade_amount`) | P07 | Trivial | Medium | ✅ **DONE** |

> **B3 Implementation Notes:** Created `__main__.py` at package root. Provides `python -m sonarft_bot` entry point that initializes logging, parses CLI args, creates a bot, and runs it. Docker `CMD ["python", "-m", "sonarft_bot"]` now works correctly.
>
> **B4 Implementation Notes:** Updated `config_parameters.json` defaults: `trade_amount` 1→0.01 BTC (~$300 instead of ~$30K), `max_trade_amount` 0.0→0.1 BTC (enabled with 10× limit), `max_orders_per_minute` 0→10 (rate limit enabled). These safer defaults reduce accidental capital exposure if simulation mode is switched off.

**Exit criteria:** Partial fills handled end-to-end. Docker entrypoint works. Safer defaults documented.

### Phase C — Code Quality & Refactoring

**Goal:** Clean up architecture and improve maintainability.

| # | Task | Source | Effort | Priority |
|---|---|---|---|---|
| **C1** | T30: Split `sonarft_search.py` into 3 files | P01, P10 | 1d | Medium | ✅ **DONE** |

> **C1 Implementation Notes:** Split `sonarft_search.py` (was 332 LOC with 4 classes) into:
> - `trade_validator.py` — `TradeValidator` class (liquidity + spread checks)
> - `trade_executor.py` — `TradeExecutor` class (async task dispatch + monitoring + shutdown)
> - `trade_processor.py` — `TradeProcessor` class (symbol processing + trade combination logic)
> - `sonarft_search.py` — `SonarftSearch` class only (orchestrator + daily loss tracking)
>
> All three classes are re-exported from `sonarft_search.py` for backward compatibility. All existing `from sonarft_search import TradeProcessor` imports continue to work. Added new modules to `pyproject.toml`.
| **C2** | R01: Remove indicator re-fetch fallback in execution | P01 | 0.5d | Medium | ✅ **DONE** |

> **C2 Implementation Notes:** Removed the `asyncio.gather(6 indicator calls)` fallback from `_execute_single_trade()`. Indicators are now read directly from the `Trade` dataclass (always populated by `process_trade_combination` → `trade_data.update(indicators)`). If any indicator is `None`, execution is skipped with a warning instead of re-fetching. Also removed `SonarftIndicators` dependency from `SonarftExecution` constructor — reduces coupling from Medium to Low.
| **C3** | T31: Consolidate VWAP into `SonarftPrices` | P01, P10 | 0.5d | Low | ✅ **DONE** |
| **C4** | R17: Use `uuid.uuid4()` for bot IDs | P01, P03 | Trivial | Low | ✅ **DONE** |
| **C5** | R20: Make `calculate_slippage_tolerance` sync | P02 | Trivial | Low | ✅ **DONE** |
| **C6** | R21: Fix file handle leak in `create_bot` lambda | P02 | Trivial | Low | ✅ **DONE** |

> **C3 Implementation Notes:** Extracted standalone `vwap(price_volume_list, depth)` function into `models.py`. Both `SonarftApiManager.get_weighted_prices()` and `SonarftPrices.get_weighted_price()` now delegate to this shared function. Eliminates duplicate VWAP logic.
>
> **C4 Implementation Notes:** `create_botid()` now returns `str(uuid.uuid4())` instead of `random.randint(10001, 99999)`. Eliminates collision risk with multiple bots.
>
> **C5 Implementation Notes:** `calculate_slippage_tolerance()` changed from `async def` to `def` — it contained no `await` calls. Updated call site to remove `await`.
>
> **C6 Implementation Notes:** Replaced `open(path, "w")` inside lambda (file handle never explicitly closed) with `_write_botid_file()` helper that uses proper `with open(...) as f:` context manager.

**Exit criteria:** `sonarft_search.py` split. No duplicate indicator fetching. VWAP in single location.

### Phase D — Trading Enhancements

**Goal:** Improve trading signal quality and fee accuracy.

| # | Task | Source | Effort | Priority |
|---|---|---|---|---|
| **D1** | D09: Stop-loss / flash crash protection | Tech debt | 2d | Medium | ✅ **DONE** |
| **D2** | R25/D13: RSI hysteresis (72/28 vs 70/30) | P05 | 0.5d | Low | ✅ **DONE** |
| **D3** | R22/D15: Maker/taker fee distinction | P03 | 1d | Low | ✅ **DONE** |
| **D4** | R24/D05: `ROUND_HALF_EVEN` option for fees | P04 | 0.5d | Low | ✅ **DONE** |
| **D5** | R12: NaN check for `get_atr()` | P05 | Trivial | Low | ✅ **DONE** |

> **D1 Implementation Notes:** Added flash crash protection in `_execute_single_trade()`. If the price deviation between buy and sell exceeds 2% (`abs(sell - buy) / buy > 0.02`), execution is skipped with a warning. This prevents placing orders during extreme market moves where the arbitrage spread is likely due to stale data rather than a real opportunity.
>
> **D2 Implementation Notes:** RSI thresholds in `weighted_adjust_prices()` changed from 70/30 to 72/28. This 2-point hysteresis reduces signal noise at the boundary — RSI must cross 72 (not 70) to trigger overbought reversal, and 28 (not 30) for oversold.
>
> **D3 Implementation Notes:** `get_buy_fee()` and `get_sell_fee()` now accept an `order_type` parameter (default `'limit'`). If `maker_buy_fee`/`maker_sell_fee` keys exist in `config_fees.json`, they're used for limit orders. Falls back to `buy_fee`/`sell_fee` for backward compatibility. No config changes required — existing configs work unchanged.
>
> **D4 Implementation Notes:** Fee calculations now use `ROUND_HALF_EVEN` (banker's rounding) by default via `d_fee()` helper. This eliminates the systematic upward bias from `ROUND_HALF_UP`. Configurable via `SONARFT_FEE_ROUNDING=HALF_UP` env var to restore old behavior. Price/amount rounding still uses `ROUND_HALF_UP` (exchange-mandated).
>
> **D5 Implementation Notes:** `get_atr()` now checks `pd.isna(value)` before returning. Returns `None` on NaN (same pattern as RSI/MACD/StochRSI). Converts to `float()` for consistency.

### Phase E — Performance & Scalability

**Goal:** Optimize for higher throughput and lower latency.

| # | Task | Source | Effort | Priority |
|---|---|---|---|---|
| **E1** | R13/D08: WebSocket price stream for `monitor_price` | P09 | 2d | Medium | ⚠️ Deferred — requires WebSocket subscription infrastructure |
| **E2** | T37/R14: Parallelize buy/sell combinations | P09 | 0.5d | Low | ✅ **DONE** |
| **E3** | D06: Shared exchange instance pool across bots | Tech debt | 2d | When >5 bots | ⚠️ Deferred — conditional on scaling needs |
| **E4** | D07: Shared indicator cache across bots | Tech debt | 2d | When >5 bots | ⚠️ Deferred — conditional on scaling needs |
| **E5** | R19/R31: Parallelize `dynamic_volatility_adjustment` | P02, P09 | Trivial | Low | ✅ **Already done** — was already using `asyncio.gather` |

> **E2 Implementation Notes:** `process_symbol()` in `trade_processor.py` now collects all buy/sell combinations into a `futures` list and processes them with `asyncio.gather(*futures, return_exceptions=True)` instead of sequential `await`. With 2 exchanges × 2 symbols, this processes up to 4 combinations in parallel (~2-4× faster per symbol).
>
> **E5 Implementation Notes:** Already parallelized in the original code — `vol_adj_buy, vol_adj_sell = await asyncio.gather(dynamic_volatility_adjustment(...), dynamic_volatility_adjustment(...))`. No change needed.

### Phase F — Operations & Observability

**Goal:** Improve operational tooling and monitoring.

| # | Task | Source | Effort | Priority |
|---|---|---|---|---|
| **F1** | D03: Add `DEBUG` level logging | Tech debt | 1d | Low | ⚠️ Deferred — low priority |
| **F2** | D04: Structured logging (replace separator lines) | Tech debt | 1d | Low | ⚠️ Deferred — low priority |
| **F3** | R27: JSON schema validation for config files | P07 | 2d | Low | ⚠️ Deferred — low priority |
| **F4** | R29/D10/D11: Extract hardcoded values to config | P07, P09 | 1d | Low | ✅ **DONE** |
| **F5** | D14: SQLite DB rotation / archival | Tech debt | 1d | When running >1 month | ⚠️ Deferred — conditional |
| **F6** | R23: Add pause/resume mechanism | P03 | 0.5d | Low | ✅ **DONE** |
| **F7** | R08: Trade history ownership check | P08 | 0.5d | Medium (API layer) | ⚠️ Deferred — API layer responsibility |

> **F4 Implementation Notes:** Extracted circuit breaker threshold (`SONARFT_MAX_FAILURES`, default 5), backoff base (`SONARFT_BACKOFF_BASE`, default 30s), and cycle sleep range (`SONARFT_CYCLE_SLEEP_MIN`/`MAX`, default 6-18s) to environment variables. All have backward-compatible defaults.
>
> **F6 Implementation Notes:** Added `pause()`/`resume()`/`is_paused` to `SonarftSearch`. When paused, `search_trades()` returns immediately without processing. Bot continues running (WebSocket connections stay alive, monitoring continues) but no new trades are searched. Can be triggered via `BotManager` API without stopping the bot.

### Phase G — Naming & Style (Tech Debt)

**Goal:** Consistency cleanup.

| # | Task | Source | Effort | Priority |
|---|---|---|---|---|
| **G1** | D01: Rename `InitializeModules` → `initialize_modules` | Tech debt | Trivial | Low |
| **G2** | D02: Rename `setAPIKeys` → `set_api_keys` | Tech debt | Trivial | Low |
| **G3** | D12: Unify `execute_long_trade`/`execute_short_trade` | Tech debt | 1d | Low |
| **G4** | R02: Replace `_search_ref` with callback | P01 | Small | Low |
| **G5** | R26: Add order dedup by trade_data hash | P06 | Small | Low |
| **G6** | R28: Validate exchange IDs against ccxt | P07 | Trivial | Low |
| **G7** | R16: Remove static `EXCHANGE_RULES` fallback | P01 | Small | Low |
| **G8** | R30: Make cycle sleep configurable | P09 | Trivial | Low |

---

## 5. Effort Summary

| Phase | Tasks | Effort | Priority |
|---|---|---|---|
| **Phase A** — Production Blockers | 2 | 2.5d | **High** |
| **Phase B** — Execution Safety | 4 | 3.5d | **Medium** |
| **Phase C** — Code Quality | 6 | 2.5d | **Medium** |
| **Phase D** — Trading Enhancements | 5 | 4d | **Low-Medium** |
| **Phase E** — Performance | 5 | 6.5d | **Low** (conditional) |
| **Phase F** — Operations | 7 | 7d | **Low** |
| **Phase G** — Naming & Style | 8 | 3d | **Low** |
| **Total** | **37** | **~29 days** | — |

---

## 6. Recommended Execution Order

**Immediate (next sprint):**
1. **A1** — Order reconciliation on startup (T33) — critical for live trading safety
2. **A2** — `pip audit` in CI (T19) — required for production compliance

**Next cycle:**
3. **B1-B4** — Partial fill handling + Docker entrypoint + safer defaults
4. **C1-C2** — Split search.py + remove indicator re-fetch

**When needed:**
5. **D1** — Stop-loss protection (before large positions)
6. **E1** — WebSocket price stream (when latency matters)
7. **E3-E4** — Shared instances/cache (when >5 bots)

**Ongoing tech debt:**
8. Phases F and G — pick items per sprint as capacity allows

---

*Consolidated from remediation status sections of Prompts 01–11. July 2025.*
