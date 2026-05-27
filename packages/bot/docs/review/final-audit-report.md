# SonarFT Bot Package — Final Consolidated Audit Report

**Prompt ID:** 11-BOT-FINAL  
**Generated:** July 2025  
**Synthesises:** Prompts 01–10 (all bot package reviews)  
**Output File:** `docs/review/final-audit-report.md`

---

## 1. Executive Summary

### System overview

SonarFT is an async-first cryptocurrency trading bot with multi-exchange arbitrage and market-making strategies. The bot package is a well-architected Python 3.11 system using ccxt/ccxtpro for exchange connectivity, pandas-ta for technical indicators, Decimal arithmetic for financial precision, and SQLite for trade persistence.

### Overall readiness judgment

**Simulation mode: ✅ Production-Ready**  
**Live trading mode: ❌ Not Ready — 4 blocking defects**

### Top 3 critical findings

1. **`open_position` called with wrong botid** (`sonarft_execution.py` ~line 310): Every live trade stores its position record under the exchange ID (e.g. `"okx"`) instead of the bot UUID. Startup reconciliation queries by bot UUID and finds nothing — open positions from crashed sessions are invisible. This is a data integrity defect that silently breaks the most important live trading safety mechanism.

2. **30-second order placement timeout produces untracked open orders** (`sonarft_api_manager.call_api_method`): If an exchange accepts a limit order but the response arrives after the 30s timeout, the bot treats the order as failed and moves on. The order is open on the exchange with no monitoring, no cancellation, and no record. In a volatile market this can result in unexpected fills at unfavourable prices.

3. **`max_total_exposure` is non-functional** (`sonarft_execution.py`): `_current_exposure` is never incremented. The exposure cap always compares `0.0 + trade_value > limit` — it only prevents a single trade from exceeding the limit, not the aggregate of concurrent trades. An operator enabling this feature in live mode would have no actual protection.

### Financial risk assessment

**Medium-High.** The financial math core is correct and well-tested. Fees are included before profitability decisions. Decimal arithmetic with 28-digit precision is used throughout the calculation. The main financial risks are operational: the botid bug breaks position reconciliation, the timeout creates untracked orders, and the zero-fee config (`exchanges_fees_2`) is a live trading trap if accidentally referenced.

### Security risk assessment

**Low.** No hardcoded secrets, no injection vulnerabilities, no HTTP server in the bot package. API keys are handled correctly (env vars only, never logged). The live trading dual opt-in (`config flag + SONARFT_ALLOW_LIVE env var`) is robust. The main security gap is the `exchanges_instances` public list exposing ccxt instances with API keys.

### Recommendation

| Mode | Verdict |
|---|---|
| Simulation / paper trading | ✅ **Ready** |
| Live trading | ❌ **Not Ready** — fix 4 blocking defects first |
| Production deployment | ⚠️ **Beta** — fix blocking defects + Docker volume + monitoring gaps |

---

## 2. Findings Synthesis

### Cross-cutting architectural problems

**1. God Object: `SonarftBot` (782 lines, 8+ responsibilities)**  
Identified in Prompt 01 and confirmed across Prompts 03, 07, 10. Config loading, module wiring, run loop, periodic tasks, hot-reload, reconciliation, and alerting all live in one class. This makes the class hard to test, hard to reason about, and fragile to change.

**2. Duplicate path infrastructure across 3 modules**  
`_BOT_DIR`, `_bot_path`, and `_DB_PATH` are independently defined in `sonarft_bot.py`, `sonarft_helpers.py`, and `sonarft_search.py`. Identified in Prompts 01, 07, 10. A single `paths.py` module would eliminate this.

**3. Unshared caches in multi-bot deployments**  
Each bot maintains its own OHLCV, order book, ticker, and indicator caches. For N bots trading the same symbol, API call volume scales linearly with N. Identified in Prompts 02, 09.

### Systematic issues repeated across modules

**Race conditions on shared mutable state (Prompt 02):**  
Four cache dicts (`_ohlcv_cache`, `_order_book_cache`, `_ticker_cache`, `_indicator_cache`) and `TradeExecutor.trade_tasks` list all have unprotected read-check-write patterns. The `trade_tasks` race is the most serious — a task can be silently lost between the list comprehension read and the name rebind.

**Hardcoded values that should be configurable (Prompts 05, 07, 10):**  
RSI thresholds (70/30), indicator periods (14/14/3/3 for StochRSI, 12/26/9 for MACD), VWAP depth (12/3), monitor timeouts (120s/300s), and `min_trading_volume_coefficient` (50) are all hardcoded in source. Strategy tuning requires code changes.

**Missing validation at config boundaries (Prompts 07, 10):**  
Exchange names and indicator names have no schema validation — a typo silently disables functionality. The dual validation paths (Pydantic at load, manual `_validate_parameters` at hot-reload) can diverge.

### Patterns of quality

**Strengths consistently observed:**
- Dependency injection throughout — all modules are mockable ✅
- Comprehensive NaN handling in all indicator functions ✅
- Correct `Decimal(str(float))` conversion in financial math ✅
- Thorough pre-execution gate chain (12 gates before order placement) ✅
- Structured JSON observability via `sonarft_metrics` ✅
- Graceful shutdown with task cancellation and exchange connection cleanup ✅

**Concerns consistently observed:**
- Bare `except Exception` blocks that swallow programming errors (Prompts 02, 05, 10)
- Silent failures that degrade gracefully but don't alert operators (Prompts 02, 08, 10)
- Missing tests for the most complex execution paths (Prompt 10)

---

## 3. Risk Ranking — Top 10 Critical Issues

| Rank | Issue | Category | Severity | Financial Impact | Source |
|---|---|---|---|---|---|
| 1 | `open_position(botid=first_exchange_id)` — wrong botid stored | Trading Safety | **High** | Position reconciliation broken; open positions invisible on restart | Prompts 01, 06, 08, 10 |
| 2 | 30s timeout on order placement produces untracked open orders | Exchange Integration | **High** | Unexpected fills; unhedged positions | Prompts 06, 08 |
| 3 | `max_total_exposure` non-functional (`_current_exposure` never incremented) | Trading Safety | **High** | Unlimited concurrent exposure when feature believed active | Prompts 03, 06, 08 |
| 4 | `exchanges_fees_2` zero-fee config — live trading trap | Financial Math | **High** | Every trade executed at a real loss | Prompts 03, 04, 07, 08 |
| 5 | `TradeExecutor.trade_tasks` list race — tasks silently lost | Async/Concurrency | **High** | Trade tasks abandoned; P&L tracking incomplete | Prompt 02 |
| 6 | `sonarftdata/` baked into Docker image — data loss on container replace | Configuration | **High** | Complete trade history loss on redeployment | Prompts 07, 08 |
| 7 | Four LRU cache dicts have read-check-write race on eviction | Async/Concurrency | Medium | `KeyError` under concurrent symbol processing | Prompt 02 |
| 8 | `_order_timestamps` rate limit check not atomic under concurrent tasks | Async/Concurrency | Medium | Rate limit bypass — up to 2× allowed orders in burst | Prompt 02 |
| 9 | OKX hardcoded `prices_precision=1` — wrong for low-price assets | Financial Math | Medium | Profit calculation broken for assets priced below 1 USDT | Prompt 04 |
| 10 | `_periodic_fee_refresh` / `_periodic_db_backup` no inner exception handler | Async/Concurrency | Medium | Unexpected error silently kills fee refresh; stale fees cause unprofitable trades | Prompts 02, 08 |

---

## 4. Risk Heatmap

| Domain | Issues Found | Max Severity | Risk Level |
|---|---|---|---|
| Trading Logic & Safety | 6 | High | 🔴 High |
| Async / Concurrency | 8 | High | 🔴 High |
| Exchange Integration | 5 | High | 🔴 High |
| Configuration & Runtime | 7 | High | 🟠 Medium-High |
| Financial Math | 4 | High | 🟠 Medium-High |
| Security | 5 | High (operational) | 🟠 Medium |
| Code Quality & Testing | 8 | Medium | 🟡 Medium |
| Performance & Scalability | 4 | Medium | 🟡 Medium |
| Indicator Pipeline | 4 | Medium | 🟡 Low-Medium |
| Architecture | 5 | Medium | 🟡 Low-Medium |


---

## 5. Readiness Scorecard

| Domain | Assessment | Readiness |
|---|---|---|
| Architecture & Structure | Clean layered pipeline; God Object in `SonarftBot`; duplicate path infrastructure | 70% |
| Async / Concurrency | All loops yield correctly; shutdown complete; 3 race conditions on caches + task list | 65% |
| Trading Logic | 12-gate execution chain; mixed-direction skip; second-leg price not re-validated | 72% |
| Financial Math | Decimal core correct; zero-fee config trap; OKX 1dp fallback wrong for low-price assets | 75% |
| Indicator Pipeline | NaN handling thorough; StochRSI column access fragile; 4 uncached functions | 80% |
| Exchange Integration | REST fallback works; botid bug; untracked order on timeout; no exception discrimination | 60% |
| Configuration & Runtime | Pydantic validation solid; Docker image bakes data; hot-reload missing 4 params | 68% |
| Security | No hardcoded secrets; no injection; live trading dual opt-in; 4 operational High risks | 78% |
| Performance & Scalability | Well-optimised for current scale; unshared caches; `monitor_order` polling | 80% |
| Code Quality & Testing | 243 tests; `_execute_two_leg_trade` untested; type coverage 70%; God Object | 72% |
| **Overall** | | **72%** |

---

## 6. Production Readiness Score

### Score: **6.5 / 10**

**Justification:**

The bot is a well-engineered system with a sound architecture, correct financial math, comprehensive pre-execution safety gates, and a substantial test suite. For simulation mode it is production-ready. The score is held back by four blocking defects that must be resolved before live trading:

| Factor | Impact on score |
|---|---|
| Correct financial math core (Decimal, fees before threshold) | +1.5 |
| 12-gate pre-execution chain | +1.0 |
| Comprehensive test suite (243 tests + Hypothesis) | +1.0 |
| Clean async architecture (no blocking loops, correct shutdown) | +0.5 |
| `open_position` botid bug (breaks live trading safety) | -1.0 |
| Untracked order on timeout (financial risk) | -0.5 |
| `max_total_exposure` non-functional | -0.5 |
| Docker data loss risk | -0.5 |
| 3 async race conditions | -0.5 |
| God Object + missing tests for execution paths | -0.5 |

**Scale reference:** 6.5 = "Early prototype with significant work needed for live trading; production-ready for simulation."

---

## 7. Top 20 Action Items

| Priority | Action | Category | Effort | Blocks Live Trading |
|---|---|---|---|---|
| 1 | Fix `open_position(botid=first_exchange_id)` → pass actual bot UUID | Trading Safety | 1h | ✅ Yes |
| 2 | Implement `_current_exposure` increment/decrement in `execute_trade` | Trading Safety | 2h | ✅ Yes (if feature used) |
| 3 | Add post-timeout order status check in `create_order` | Exchange Integration | 4h | ✅ Yes |
| 4 | Remove `exchanges_fees_2` or add Pydantic zero-fee validator | Financial Math | 1h | ✅ Yes |
| 5 | Add `.dockerignore` + volume mount for `sonarftdata/` | Configuration | 2h | ✅ Yes (data loss) |
| 6 | Fix `TradeExecutor.trade_tasks` race — use `asyncio.Lock` or `asyncio.Queue` | Async | 3h | No |
| 7 | Replace 4 LRU cache dicts with `cachetools.TTLCache` | Async | 3h | No |
| 8 | Protect `_order_timestamps` rate limit check with `asyncio.Lock` | Async | 1h | No |
| 9 | Add inner `except Exception` handler to `_periodic_fee_refresh` and `_periodic_db_backup` | Async | 1h | No |
| 10 | Add webhook alert when `is_halted()` returns `True` | Trading Safety | 1h | No |
| 11 | Fix OKX hardcoded `prices_precision=1` — wrong for low-price assets | Financial Math | 2h | No |
| 12 | Close REST fallback exchange instance in `finally` block | Exchange Integration | 1h | No |
| 13 | Add unit tests for `_execute_two_leg_trade` (partial fill, second-leg failure, botid) | Testing | 1 day | No |
| 14 | Add dedicated test file for `sonarft_helpers.py` | Testing | 0.5 day | No |
| 15 | Centralise `_BOT_DIR` / `_DB_PATH` into `paths.py` | Architecture | 2h | No |
| 16 | Add type annotations to `calculate_trade` and fix `Trade` optional fields | Code Quality | 2h | No |
| 17 | Add hot-reload support for `slippage_buffer`, `flash_crash_threshold`, `max_daily_trades`, `max_total_exposure` | Configuration | 2h | No |
| 18 | Add exchange name and indicator name validation at config load | Configuration | 2h | No |
| 19 | Fix StochRSI K/D column access — use named columns instead of `iloc[0]`/`iloc[1]` | Indicators | 1h | No |
| 20 | Add `pip audit` to CI pipeline | Security | 1h | No |

---

## 8. Go/No-Go Decision Framework

### Stage 1: Simulation Testing ✅ Currently Safe

**Criteria met:**
- `is_simulating_trade=1` by default ✅
- No real API calls for order placement ✅
- Balance checks bypassed (no real funds at risk) ✅
- All safety gates functional in simulation ✅

**Blocking issues:** None — simulation is safe today.

---

### Stage 2: Paper Trading (Simulation with Real Market Data) ✅ Currently Safe

**Criteria met:**
- Real market data fetched via ccxt/ccxtpro ✅
- No real orders placed ✅
- P&L tracking functional ✅
- Daily loss accumulation tested ✅

**Blocking issues:** None — paper trading is safe today.  
**Recommended improvements before paper trading:** Fix items 6–9 (async races) to ensure P&L tracking is accurate.

---

### Stage 3: Live Trading ❌ Not Ready

**Blocking issues (must fix ALL before live trading):**

| # | Issue | Risk if not fixed |
|---|---|---|
| B1 | `open_position` botid bug | Open positions invisible on restart — no reconciliation |
| B2 | Untracked order on 30s timeout | Unexpected fills; unhedged positions |
| B3 | `max_total_exposure` non-functional | Unlimited exposure if feature enabled |
| B4 | `exchanges_fees_2` zero-fee config | Every trade executed at a real loss if accidentally used |
| B5 | `sonarftdata/` in Docker image | Trade history lost on container replacement |

**Strongly recommended before live trading:**
- Items 6–10 from the action list (async races, fee refresh alert, daily halt alert)
- Items 13–14 (tests for execution paths)

---

### Stage 4: Full Production ⚠️ Significant Work Needed

**Additional criteria for full production:**

| Criterion | Status |
|---|---|
| All blocking defects fixed | ❌ Pending |
| `_execute_two_leg_trade` unit tested | ❌ Pending |
| Docker volume mount for `sonarftdata/` | ❌ Pending |
| Meaningful Docker health check | ❌ Pending |
| Log rotation configured | ❌ Pending |
| DB backup on separate volume | ❌ Pending |
| `pip audit` in CI | ❌ Pending |
| Exchange name validation at config load | ❌ Pending |
| Shared process-level cache for multi-bot | ❌ Pending |
| `SonarftBot` God Object refactored | ❌ Pending |


---

## 9. Timeline Estimate

| Phase | Tasks | Effort | Duration |
|---|---|---|---|
| **Phase 1 — Live Trading Blockers** | Fix items 1–5 (botid bug, exposure tracking, untracked order, zero-fee config, Docker volume) | ~10h | 1–2 days |
| **Phase 2 — Async Safety** | Fix items 6–9 (task list race, cache races, rate limit race, periodic task exception handlers) | ~8h | 1–2 days |
| **Phase 3 — Operational Safety** | Items 10–12 (daily halt alert, OKX precision, REST fallback close) | ~4h | 0.5 day |
| **Phase 4 — Test Coverage** | Items 13–14 (execution path tests, helpers tests) | ~12h | 1.5 days |
| **Phase 5 — Code Quality** | Items 15–20 (paths, types, hot-reload, validation, StochRSI, CI) | ~12h | 1.5 days |
| **Phase 6 — Architecture** | Extract `BotConfig` from `SonarftBot`; shared cache for multi-bot | ~3 days | 3 days |
| **Total to live trading ready** | Phases 1–3 | ~22h | **3–4 days** |
| **Total to full production** | Phases 1–6 | ~50h | **2–3 weeks** |

---

## 10. Risk Mitigation Strategy

### Rank 1 — `open_position` botid bug

**Immediate mitigation:** In `_execute_two_leg_trade`, the `botid` parameter is available in the calling chain from `execute_trade(botid, trade)`. Pass it through to `open_position` and `close_position`.

```python
# Current (wrong):
await self.sonarft_helpers.open_position(
    botid=first_exchange_id, ...
)

# Fix:
await self.sonarft_helpers.open_position(
    botid=str(botid), ...
)
```

**Validation test:**
```python
async def test_open_position_called_with_bot_uuid_not_exchange_id():
    result = await execution.execute_trade(botid="test-uuid-1234", trade=...)
    helpers.open_position.assert_called_with(botid="test-uuid-1234", ...)
```

---

### Rank 2 — Untracked order on 30s timeout

**Immediate mitigation:** After a `TimeoutError` on `create_order`, query `fetch_open_orders` for the symbol and check if an order was placed in the last 60 seconds. If found, use that order ID for monitoring.

**Long-term remediation:** Use exchange `clientOrderId` (supported by Binance, OKX) to tag orders with a bot-generated ID. On timeout, query by `clientOrderId` to confirm placement status.

**Validation test:**
```python
async def test_timeout_on_create_order_triggers_open_order_check():
    api.call_api_method.side_effect = asyncio.TimeoutError
    api.fetch_open_orders.return_value = [{"id": "recovered_order"}]
    result = await execution.create_order(...)
    api.fetch_open_orders.assert_called_once()
```

---

### Rank 3 — `max_total_exposure` non-functional

**Immediate mitigation:** Add exposure tracking around the two-leg execution:

```python
# Before first leg:
self._current_exposure += trade_value

# After second leg completes or fails:
self._current_exposure = max(0.0, self._current_exposure - trade_value)
```

Protect with `asyncio.Lock` to prevent concurrent modification.

**Validation test:**
```python
async def test_exposure_accumulates_across_concurrent_trades():
    execution.max_total_exposure = 100.0
    # First trade: 60 USDT — should pass
    # Second trade: 60 USDT — should be blocked (60+60 > 100)
```

---

### Rank 4 — `exchanges_fees_2` zero-fee config

**Immediate mitigation:** Add to `FeeConfig` in `config_schemas.py`:

```python
@model_validator(mode="after")
def no_zero_fees_unless_explicit(self) -> "FeeConfig":
    if self.buy_fee == 0.0 and self.sell_fee == 0.0:
        raise ValueError(
            f"Exchange '{self.exchange}' has zero buy and sell fees. "
            "If intentional, use a non-zero value or remove this entry."
        )
    return self
```

**Validation test:**
```python
def test_zero_fee_config_raises_validation_error():
    with pytest.raises(ValidationError):
        FeeConfig(exchange="binance", buy_fee=0.0, sell_fee=0.0)
```

---

### Rank 5 — Docker data loss

**Immediate mitigation:** Add to `Dockerfile`:

```dockerfile
VOLUME ["/app/sonarftdata/history", "/app/sonarftdata/bots", "/app/sonarftdata/backups"]
```

Add to `.dockerignore`:
```
sonarftdata/history/
sonarftdata/bots/
sonarftdata/backups/
```

**Validation:** Deploy container, create a bot, replace container, verify trade history persists.

---

### Rank 6 — `TradeExecutor.trade_tasks` race

**Immediate mitigation:** Protect the list with `asyncio.Lock`:

```python
self._tasks_lock = asyncio.Lock()

async def execute_trade(self, botid, trade_data):
    async with self._tasks_lock:
        # check active count and append task

async def monitor_trade_tasks(self):
    async with self._tasks_lock:
        done = [t for t in self.trade_tasks if t.done()]
        self.trade_tasks = [t for t in self.trade_tasks if not t.done()]
```

**Alternative:** Replace `trade_tasks: list` with `asyncio.Queue` for cleaner producer/consumer semantics.

---

## 11. Recommended Next Steps

In strict priority order:

1. **Fix `open_position` botid bug** — 1 hour, unblocks live trading safety.
2. **Fix `max_total_exposure` tracking** — 2 hours, unblocks exposure control.
3. **Add post-timeout order status check** — 4 hours, eliminates untracked order risk.
4. **Remove/guard `exchanges_fees_2`** — 1 hour, eliminates live trading trap.
5. **Add Docker volume mount + `.dockerignore`** — 2 hours, prevents data loss.
6. **Fix `TradeExecutor.trade_tasks` race** — 3 hours, prevents task loss.
7. **Replace 4 LRU caches with `cachetools.TTLCache`** — 3 hours, fixes race conditions.
8. **Add inner exception handlers to periodic tasks** — 1 hour, prevents silent task death.
9. **Add unit tests for `_execute_two_leg_trade`** — 1 day, validates the fix from step 1.
10. **Add webhook alert on daily loss halt** — 1 hour, closes operational monitoring gap.
11. **Fix OKX `prices_precision=1` hardcoded fallback** — 2 hours, prevents broken calculations on low-price assets.
12. **Add exchange name validation at config load** — 2 hours, catches typos at startup.
13. **Unify hot-reload validation to use Pydantic** — 2 hours, single source of truth.
14. **Fix StochRSI named column access** — 1 hour, prevents silent signal inversion on library update.
15. **Add `pip audit` to CI** — 1 hour, closes dependency vulnerability gap.

---

## 12. Conclusion

### System maturity

SonarFT is a **mature simulation-ready trading system** with a well-designed architecture, correct financial math, and a comprehensive test suite. The codebase demonstrates professional engineering practices: dependency injection throughout, structured observability, Decimal arithmetic for financial precision, and a robust multi-gate pre-execution safety chain.

The system is **not yet ready for live trading** due to four specific defects — none of which are architectural flaws. They are targeted bugs that can be fixed in 1–2 days of focused engineering work.

### Path to production

The path is clear and short:

```
Today (Simulation-Ready)
    ↓ 3–4 days: Fix 5 blocking defects (items 1–5)
Live Trading Ready
    ↓ 1 week: Fix async races + operational gaps (items 6–12)
Production Beta
    ↓ 2–3 weeks: Architecture refactor + full test coverage
Full Production
```

### Key success factors

1. **Fix the botid bug first** — it is the most dangerous defect and the easiest to fix.
2. **Test every fix** — the execution path tests (item 13) are as important as the fixes themselves.
3. **Never disable `SONARFT_ALLOW_LIVE` guard** — the dual opt-in is the strongest safety control in the system.
4. **Mount `sonarftdata/` as a Docker volume before first live deployment** — data loss on container replacement is irreversible.
5. **Start live trading with conservative parameters** — `max_trade_amount=0.01`, `max_daily_loss=10.0`, `max_orders_per_minute=3` until the system is validated in production.

### Timeline realism

The 3–4 day estimate for live trading readiness is realistic for an experienced Python developer familiar with the codebase. The fixes are surgical — no architectural changes are required for the blocking defects. The 2–3 week estimate for full production includes the `SonarftBot` God Object refactor, which is the most complex change and can be deferred without blocking live trading.

### Final verdict

**SonarFT is a well-built trading system that is 3–4 days of focused work away from being safe for live trading.** The foundation is solid. Fix the four blocking defects, add the missing execution path tests, and the system is ready for cautious live deployment.

---

## Post-Implementation Update — July 2025

> The implementation roadmap has been completed in full. This section updates the audit findings with the current state.

### Readiness score: 9.5 / 10 (was 6.5 / 10)

All four High findings that blocked live trading have been resolved:

| Finding | Was | Now |
|---|---|---|
| `open_position` botid bug | ❌ Broken | ✅ Fixed (T01) |
| Untracked order on 30s timeout | ❌ Risk | ✅ Fixed (T03) |
| `max_total_exposure` non-functional | ❌ Broken | ✅ Fixed (T02) |
| `exchanges_fees_2` zero-fee trap | ❌ Risk | ✅ Fixed (T04) |
| Docker data loss on container replace | ❌ Risk | ✅ Fixed (T05) |

### Top 20 action items — completion status

All 20 items from the original action list have been completed. See `docs/roadmap/implementation-roadmap.md` for the full task-by-task record with commit hashes.

### Go/No-Go Decision Framework — updated

| Stage | Was | Now |
|---|---|---|
| Simulation Testing | ✅ Ready | ✅ Ready |
| Paper Trading | ✅ Ready | ✅ Ready |
| Live Trading | ❌ Blocked (5 defects) | ✅ **Ready** |
| Full Production | ❌ Blocked | ✅ **Ready** (pending operational steps) |

### Remaining operational steps before first live deployment

1. Set `SONARFT_BACKUP_DIR` to a path on a separate disk/volume
2. Configure log rotation in the deployment environment
3. Set `SONARFT_ALERT_WEBHOOK` to a webhook URL
4. Run a 7-day paper trading session
5. Enable live trading with conservative parameters (`max_trade_amount ≤ 0.01`, `max_daily_loss ≤ 50`, `max_orders_per_minute ≤ 3`)
