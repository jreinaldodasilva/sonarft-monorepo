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
| **A2** | T19/R15: Add `pip audit` to CI | P08 | 0.5d | **Required for production** |

**Exit criteria:** Bot queries open orders on startup and cancels stale ones. CI rejects PRs with known vulnerabilities.

### Phase B — Execution Safety Improvements

**Goal:** Address remaining partial fill and order management gaps.

| # | Task | Source | Effort | Priority |
|---|---|---|---|---|
| **B1** | R05: Partial fill rebalancing logic | P06 | 2d | Medium |
| **B2** | R06: Cancel remaining amount from partial first leg | P06 | 1d | Medium |
| **B3** | R11: Add `__main__.py` for Docker entrypoint | P07 | 0.5d | Medium |
| **B4** | R09+R10: Set safer defaults (`trade_amount`, `max_trade_amount`) | P07 | Trivial | Medium |

**Exit criteria:** Partial fills handled end-to-end. Docker entrypoint works. Safer defaults documented.

### Phase C — Code Quality & Refactoring

**Goal:** Clean up architecture and improve maintainability.

| # | Task | Source | Effort | Priority |
|---|---|---|---|---|
| **C1** | T30: Split `sonarft_search.py` into 3 files | P01, P10 | 1d | Medium |
| **C2** | R01: Remove indicator re-fetch fallback in execution | P01 | 0.5d | Medium |
| **C3** | T31: Consolidate VWAP into `SonarftPrices` | P01, P10 | 0.5d | Low |
| **C4** | R17: Use `uuid.uuid4()` for bot IDs | P01, P03 | Trivial | Low |
| **C5** | R20: Make `calculate_slippage_tolerance` sync | P02 | Trivial | Low |
| **C6** | R21: Fix file handle leak in `create_bot` lambda | P02 | Trivial | Low |

**Exit criteria:** `sonarft_search.py` split. No duplicate indicator fetching. VWAP in single location.

### Phase D — Trading Enhancements

**Goal:** Improve trading signal quality and fee accuracy.

| # | Task | Source | Effort | Priority |
|---|---|---|---|---|
| **D1** | D09: Stop-loss / flash crash protection | Tech debt | 2d | Medium |
| **D2** | R25/D13: RSI hysteresis (72/68 vs 70/70) | P05 | 0.5d | Low |
| **D3** | R22/D15: Maker/taker fee distinction | P03 | 1d | Low |
| **D4** | R24/D05: `ROUND_HALF_EVEN` option for fees | P04 | 0.5d | Low |
| **D5** | R12: NaN check for `get_atr()` | P05 | Trivial | Low |

### Phase E — Performance & Scalability

**Goal:** Optimize for higher throughput and lower latency.

| # | Task | Source | Effort | Priority |
|---|---|---|---|---|
| **E1** | R13/D08: WebSocket price stream for `monitor_price` | P09 | 2d | Medium |
| **E2** | T37/R14: Parallelize buy/sell combinations | P09 | 0.5d | Low |
| **E3** | D06: Shared exchange instance pool across bots | Tech debt | 2d | When >5 bots |
| **E4** | D07: Shared indicator cache across bots | Tech debt | 2d | When >5 bots |
| **E5** | R19/R31: Parallelize `dynamic_volatility_adjustment` | P02, P09 | Trivial | Low |

### Phase F — Operations & Observability

**Goal:** Improve operational tooling and monitoring.

| # | Task | Source | Effort | Priority |
|---|---|---|---|---|
| **F1** | D03: Add `DEBUG` level logging | Tech debt | 1d | Low |
| **F2** | D04: Structured logging (replace separator lines) | Tech debt | 1d | Low |
| **F3** | R27: JSON schema validation for config files | P07 | 2d | Low |
| **F4** | R29/D10/D11: Extract hardcoded values to config | P07, P09 | 1d | Low |
| **F5** | D14: SQLite DB rotation / archival | Tech debt | 1d | When running >1 month |
| **F6** | R23: Add pause/resume mechanism | P03 | 0.5d | Low |
| **F7** | R08: Trade history ownership check | P08 | 0.5d | Medium (API layer) |

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
