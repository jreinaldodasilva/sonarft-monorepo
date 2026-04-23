# SonarFT Bot — Final Consolidated Audit Report

**Prompt:** 11-BOT-FINAL  
**Reviewer role:** Senior technical auditor — synthesis of all 10 review domains  
**Date:** July 2025  
**Status:** Complete  
**Source documents:** Prompts 01–10 (all completed)

---

## 1. Executive Summary

### System overview

SonarFT is an async-first, multi-exchange cryptocurrency arbitrage and market-making bot built in Python 3.11. It is architecturally sound, well-structured, and demonstrates strong engineering discipline in its financial calculation layer. The codebase is the product of sustained development with clear design intent.

### Overall readiness judgment

**Recommendation: BETA — Safe for simulation and paper trading. Not ready for live trading.**

The system is production-ready for simulation mode. For live trading, three blocking issues must be resolved before any real funds are placed at risk.

### Top 3 critical findings

**1. No startup live mode guard (T-14 / S-13 / C-07)**  
A deployment with `is_simulating_trade: 0` in config and exchange API keys in environment variables will place real orders immediately on startup without any confirmation. This is the single most dangerous defect in the codebase.

**2. No persistent position tracker (E-24)**  
The bot has no mechanism to record or recover open positions across restarts. If the bot restarts after a partial fill (buy filled, sell not placed), the open position is invisible to the new instance. In live trading, this creates unmanaged financial exposure.

**3. Unbounded `trade_tasks` list (S-09)**  
Under high trade frequency, the `trade_tasks` list grows without bound. With 3 exchanges, 3 symbols, and 300-second order monitoring timeouts, up to 1,500 concurrent tasks can accumulate — leading to memory exhaustion and OOM kill, which abandons all in-flight trades.

### Financial risk assessment

| Risk | Likelihood | Impact | Status |
|---|---|---|---|
| Accidental live trading on startup | Medium | Critical | ❌ Unmitigated |
| Unhedged position after failed sell leg | Low-Medium | High | ⚠️ Alert only, no auto-close |
| Stale fee rates causing unprofitable trades | Medium | Medium | ❌ Unmitigated |
| Daily loss limit bypass by in-flight trades | Low | Medium | ⚠️ Partial mitigation |
| Slippage eroding marginal profits | Medium | Low-Medium | ❌ No slippage buffer |

### Security risk assessment

| Risk | Likelihood | Impact | Status |
|---|---|---|---|
| API key exposure | Low | Critical | ✅ Keys in env vars only |
| SQL injection via table name | Low | High | ❌ No allowlist validation |
| Credential logging | Low | Medium | ✅ Keys never logged |
| Dependency CVE | Medium | Medium | ❌ No CI scanning |

---

## 2. Findings Synthesis

### Cross-cutting architectural problems

**A. Missing startup safety gate** — The `SONARFT_ALLOW_LIVE` environment variable guard exists for hot-reload but is absent at initial startup. This same gap appears in Prompts 03 (T-14), 07 (C-07), and 08 (S-13). It is the highest-priority fix in the entire codebase.

**B. No persistent position tracking** — Identified in Prompts 06 (E-24) and 08. The bot has no `positions` table in SQLite, no position reconciliation on restart beyond cancelling open orders, and no emergency close mechanism. This is a fundamental gap for live trading.

**C. Unbounded resource growth** — The `trade_tasks` list (S-09, P-10) and the order book/ticker caches (S-10, P-11) grow without bound. Both are straightforward to fix with a maximum concurrent task limit and LRU eviction.

**D. Static fee rates** — Identified in Prompts 03 (T-11) and 08. Fee rates are loaded from a static JSON file. Exchange fee changes cause the bot to execute unprofitable trades silently.

**E. No WebSocket → REST failover** — Identified in Prompts 02 (B-25) and 06 (E-06). A persistent WebSocket failure degrades silently until the circuit breaker trips after 5 cycles.

### Systematic issues repeated across modules

**1. Blocking SQLite calls on event loop** — `_save_daily_loss()` and `_load_daily_loss()` in `sonarft_search.py` call `sqlite3.connect()` synchronously on the event loop (B-03). All other SQLite operations correctly use `asyncio.to_thread`. This is an isolated inconsistency.

**2. RSI threshold inconsistency** — RSI overbought/oversold thresholds are 72/28 in `sonarft_prices.py` and 70/30 in `sonarft_execution.py` (T-17, I-28). The same signal is interpreted differently at the pricing and execution layers.

**3. Hardcoded values that should be configurable** — Indicator periods (RSI 14, StochRSI 14/14/3/3), flash crash threshold (2%), VWAP depths (12, 3), and monitor timeouts (120s, 300s) are all hardcoded in source (C-11, C-12). These should be configurable via environment variables or config files.

**4. Dead code** — `get_atr()`, `get_24h_high()`, `get_24h_low()` in `SonarftIndicators` and `create_futures_order()` in `SonarftApiManager` are defined but never called (I-11, I-12, E-32). `market_movement()` is called but its results are discarded (I-13).

**5. Missing test coverage for infrastructure** — `SonarftApiManager` and `TradeExecutor` have zero test coverage (Q-16, Q-17). These are critical infrastructure components.

### Patterns of quality

**Strengths:**
- Consistent dependency injection throughout — every class is independently testable
- Comprehensive financial calculation testing — `calculate_trade()` and `vwap()` are thoroughly covered
- Correct async patterns — all I/O is async, `asyncio.gather` used consistently, `CancelledError` handled correctly
- Defence-in-depth trading safety — 14-gate validation chain before order placement
- Structured observability — `sonarft_metrics.py` emits JSON events for all critical operations
- SQLite WAL mode with indexed queries — correct concurrent-safe persistence

**Concerns:**
- Broad `except Exception` throughout — no differentiation between transient and permanent errors
- O(exchanges²) combination explosion — practical limit of 3 exchanges before rate limit issues
- Single 30-second timeout for 16 concurrent indicator fetches — one slow exchange cancels all

---

## 3. Risk Ranking — Top 20 Issues

| Rank | Issue | Category | Severity | Financial Impact | Source |
|---|---|---|---|---|---|
| 1 | No `SONARFT_ALLOW_LIVE` check at startup — live orders placed on misconfigured deployment | Safety | **Critical** | Unlimited loss | T-14, S-13, C-07 |
| 2 | No persistent position tracker — open positions invisible after restart | Safety | **High** | Unmanaged exposure | E-24 |
| 3 | Unbounded `trade_tasks` list — OOM kill abandons in-flight trades | Reliability | **High** | Open positions | S-09, P-10 |
| 4 | No WebSocket → REST failover — silent degradation on WS failure | Reliability | **High** | Missed opportunities | E-06, B-25 |
| 5 | Static fee rates — stale fees cause unprofitable trades | Financial | **High** | Cumulative loss | T-11 |
| 6 | Lost order confirmation — order placed but untracked on network error | Reliability | **High** | Untracked open order | E-28 |
| 7 | `ccxt.pro` not in `requirements.txt` — `ImportError` on startup | Deployment | **High** | Bot fails to start | A-01, E-02 |
| 8 | SQL table name not validated — future injection risk | Security | **High** | Data corruption | S-06 |
| 9 | Blocking SQLite calls on event loop — latency spikes on every trade | Performance | **High** | Degraded throughput | B-03 |
| 10 | `monitor_order()` cancellation doesn't trigger order cancel — open order on shutdown | Safety | **Medium** | Untracked open order | E-31 |
| 11 | No slippage buffer in profit threshold — marginal trades execute at a loss | Financial | **Medium** | Per-trade loss | T-09 |
| 12 | Profitability not re-validated after `monitor_price()` | Financial | **Medium** | Trade at a loss | E-15, S-18 |
| 13 | RSI thresholds inconsistent (72/28 vs 70/30) | Logic | **Medium** | Wrong position direction | T-17, I-28 |
| 14 | StochRSI `(0.0, 0.0)` treated as `None` — extreme signal masked | Logic | **Medium** | Missed signal | I-26 |
| 15 | `market_movement()` called but results discarded — wasted API calls | Performance | **Medium** | Rate limit pressure | I-13 |
| 16 | No JSON schema validation on config files | Config | **High** | Silent misconfiguration | C-01 |
| 17 | `indicators_3` malformed entry in config | Config | **High** | Works by accident | C-05 |
| 18 | `SonarftApiManager` zero test coverage | Quality | **High** | Undetected regressions | Q-16 |
| 19 | `TradeExecutor` zero test coverage | Quality | **High** | Undetected regressions | Q-17 |
| 20 | Risk limits default to `0.0` (disabled) in code fallbacks | Safety | **Medium** | No risk controls on stripped config | C-10 |

---

## 4. Risk Heatmap

| Domain | Issue Count | Critical | High | Medium | Low | Risk Level |
|---|---|---|---|---|---|---|
| Architecture | 11 | 0 | 1 | 5 | 5 | 🟡 Medium |
| Async/Concurrency | 20 | 0 | 1 | 9 | 10 | 🟡 Medium |
| Trading Logic | 23 | 1 | 3 | 11 | 8 | 🔴 High |
| Financial Math | 15 | 0 | 1 | 5 | 9 | 🟡 Medium |
| Indicators | 22 | 0 | 0 | 10 | 12 | 🟡 Medium |
| Exchange Integration | 30 | 0 | 4 | 14 | 12 | 🔴 High |
| Configuration | 24 | 0 | 4 | 10 | 10 | 🔴 High |
| Security | 27 | 1 | 2 | 12 | 12 | 🔴 High |
| Performance | 22 | 0 | 5 | 12 | 5 | 🟡 Medium |
| Code Quality | 27 | 0 | 2 | 8 | 17 | 🟡 Medium |
| **Total** | **221** | **2** | **23** | **96** | **100** | |

**Highest-risk domains:** Trading Logic, Exchange Integration, Configuration, Security

---

## 5. Readiness Scorecard

| Domain | Score | Assessment | Readiness |
|---|---|---|---|
| Architecture | 8/10 | Clean DAG, consistent DI, good layering. Minor coupling issues. | 80% |
| Async/Concurrency | 7.5/10 | Correct patterns throughout. Blocking SQLite calls and unbounded task list are gaps. | 75% |
| Trading Logic | 7/10 | Sound core logic. Missing startup safety gate is Critical. Slippage buffer absent. | 65% |
| Financial Math | 8/10 | Excellent Decimal usage. Hardcoded exchange precision fallback is the main risk. | 80% |
| Indicators | 7/10 | Correct formulas, good caching. StochRSI truthiness bug and dead code reduce score. | 70% |
| Exchange Integration | 6.5/10 | Solid foundations. No WS→REST failover, no position tracker, lost confirmation risk. | 55% |
| Configuration | 6.5/10 | Functional but no schema validation. Startup live mode gap. Hardcoded values. | 60% |
| Security | 6/10 | Good credential handling. Missing startup guard, SQL table validation, no CI scanning. | 55% |
| Performance | 7/10 | Effective caching after warm-up. O(n²) scaling and unbounded task list are risks. | 65% |
| Code Quality | 7.2/10 | Strong financial testing. Infrastructure layer (ApiManager, TradeExecutor) untested. | 70% |
| **Overall** | **7.1/10** | | **68%** |

---

## 6. Production Readiness Score

### Score: **6.5 / 10 — Beta**

**Justification:**

The system scores 6.5 because it is genuinely well-engineered in its core trading logic, financial calculations, and async architecture — but has a cluster of blocking issues that prevent safe live deployment.

**Factors pushing the score up:**
- Financial calculation layer is correct and thoroughly tested
- 14-gate validation chain before order placement
- Consistent async patterns with no blocking I/O (except the SQLite gap)
- Comprehensive simulation mode that correctly gates all real exchange calls
- Structured observability with JSON metrics
- Non-root Docker deployment with correct secret handling

**Factors holding the score down:**
- Missing startup live mode guard (Critical — direct financial loss risk)
- No persistent position tracker (High — unmanaged exposure on restart)
- Unbounded trade task list (High — OOM kill risk)
- No WS→REST failover (High — silent degradation)
- Static fee rates (High — cumulative loss risk)
- `ccxt.pro` not declared in requirements (High — deployment failure)
- Zero test coverage for `SonarftApiManager` and `TradeExecutor` (High)

**Score by deployment mode:**

| Mode | Score | Verdict |
|---|---|---|
| Simulation mode | 8.5/10 | ✅ Ready |
| Paper trading (live API, no real funds) | 7/10 | ✅ Ready with monitoring |
| Live trading (real funds) | 4/10 | ❌ Not ready — 3 blocking issues |
| Production (multi-bot, multi-exchange) | 3.5/10 | ❌ Not ready — additional scaling issues |

---

## 7. Top 20 Action Items

| Priority | Action | Category | Effort | Blocking Live? | Source |
|---|---|---|---|---|---|
| **P0-1** | Add `SONARFT_ALLOW_LIVE` check in `load_configurations()` when `is_simulating_trade=0` | Safety | 1h | ✅ Yes | T-14, S-13 |
| **P0-2** | Add `MAX_CONCURRENT_TRADES` limit in `TradeExecutor.execute_trade()` | Reliability | 2h | ✅ Yes | S-09 |
| **P0-3** | Add `ccxt[pro]` to `requirements.txt` and `pyproject.toml` | Deployment | 30m | ✅ Yes | A-01 |
| **P0-4** | Fix `if stoch_buy is not None` (not truthiness check) | Logic | 30m | No | I-26 |
| **P0-5** | Add `_ALLOWED_TABLES` frozenset validation in `SonarftHelpers` | Security | 1h | No | S-06 |
| **P1-1** | Implement persistent position tracker (SQLite `positions` table) | Safety | 1–2 days | ✅ Yes | E-24 |
| **P1-2** | Add WS→REST fallback in `call_api_method()` | Reliability | 4h | No | E-06 |
| **P1-3** | Wrap `_save_daily_loss()` / `_load_daily_loss()` in `asyncio.to_thread` | Performance | 1h | No | B-03 |
| **P1-4** | Add `pip-audit` to CI pipeline | Security | 1h | No | S-27 |
| **P1-5** | Fix `indicators_3` malformed config entry | Config | 15m | No | C-05 |
| **P1-6** | Add JSON schema validation (`pydantic`) for config loading | Config | 4h | No | C-01 |
| **P1-7** | Extract RSI thresholds to `models.py` constants | Logic | 1h | No | T-17, I-28 |
| **P1-8** | Remove `market_movement()` from indicator gather | Performance | 1h | No | I-13 |
| **P1-9** | Add `test_sonarft_api_manager.py` — cache, dispatch, `get_latest_prices` | Quality | 4h | No | Q-16 |
| **P1-10** | Add `test_trade_executor.py` — task lifecycle, shutdown, P&L | Quality | 4h | No | Q-17 |
| **P2-1** | Add `try/finally` to `monitor_order()` to cancel order on `CancelledError` | Safety | 2h | No | E-31 |
| **P2-2** | Add slippage buffer parameter to profit threshold check | Financial | 2h | No | T-09 |
| **P2-3** | Re-validate profitability after `monitor_price()` returns | Financial | 2h | No | E-15 |
| **P2-4** | Add order book + ticker cache LRU eviction | Performance | 2h | No | S-10 |
| **P2-5** | Anchor `_DB_PATH` to `_BOT_DIR` in `sonarft_helpers.py` and `sonarft_search.py` | Config | 1h | No | C-19 |

---

## 8. Go/No-Go Decision Framework

### Stage 1 — Simulation Testing ✅ READY NOW

**Criteria:** All trading logic runs with synthetic orders. No real funds at risk.

| Criterion | Status |
|---|---|
| `is_simulating_trade = 1` in config | ✅ Default |
| Simulation gate enforced in `execute_order()` | ✅ |
| Balance checks bypassed in simulation | ✅ |
| Trade history recorded | ✅ |
| Daily loss limit functional | ✅ |

**Blocking issues:** None. Simulation mode is production-ready.

---

### Stage 2 — Paper Trading (live API, no real funds) ✅ READY with monitoring

**Criteria:** Bot connects to live exchange APIs, reads real market data, but places no real orders (`is_simulating_trade = 1`).

| Criterion | Status |
|---|---|
| Live API connectivity | ✅ ccxt/ccxtpro |
| Real market data for indicators | ✅ |
| No real orders placed | ✅ Simulation gate |
| `ccxt.pro` installed | ⚠️ Must be added to requirements |
| Monitoring/alerting configured | ⚠️ Webhook optional |

**Blocking issues:** P0-3 (`ccxt.pro` in requirements). All others are monitoring improvements.

---

### Stage 3 — Live Trading (real funds, single bot, small amounts) ❌ NOT READY

**Criteria:** Bot places real limit orders with a small `trade_amount` on a single exchange pair.

| Criterion | Status |
|---|---|
| Startup live mode guard | ❌ P0-1 — must fix |
| Persistent position tracker | ❌ P1-1 — must fix |
| Concurrent task limit | ❌ P0-2 — must fix |
| Fee rates current | ❌ Static config — acceptable for initial live with manual monitoring |
| WS→REST failover | ⚠️ P1-2 — recommended |
| `monitor_order()` cancel on shutdown | ⚠️ P2-1 — recommended |
| Slippage buffer | ⚠️ P2-2 — recommended |

**Blocking issues:** P0-1, P0-2, P1-1. All three must be resolved before any real funds.

---

### Stage 4 — Full Production (multi-bot, multi-exchange) ❌ NOT READY

**Criteria:** Multiple bots, multiple exchanges, automated fee refresh, full monitoring.

| Criterion | Status |
|---|---|
| All Stage 3 criteria | ❌ |
| Automated fee refresh | ❌ T-11 |
| Cross-bot rate limit coordination | ❌ P-03 |
| Shared cache across bots | ❌ P-18 |
| JSON schema validation | ❌ C-01 |
| Full test coverage (ApiManager, TradeExecutor) | ❌ Q-16, Q-17 |
| `pip-audit` in CI | ❌ S-27 |

**Blocking issues:** All Stage 3 blockers plus automated fee refresh and cross-bot rate limiting.

---

## 9. Timeline Estimate

| Phase | Tasks | Effort | Duration |
|---|---|---|---|
| **Sprint 1 — Critical Safety** | P0-1 (startup guard), P0-2 (task limit), P0-3 (requirements), P0-4 (StochRSI fix), P0-5 (SQL allowlist) | ~6h | 1 day |
| **Sprint 2 — Live Trading Blockers** | P1-1 (position tracker), P1-2 (WS→REST fallback), P1-3 (async SQLite), P1-5 (config fix) | ~3 days | 1 week |
| **Sprint 3 — Quality & Config** | P1-4 (CI audit), P1-6 (schema validation), P1-7 (RSI constants), P1-8 (remove market_movement), P1-9/10 (tests) | ~2 days | 1 week |
| **Sprint 4 — Financial Safety** | P2-1 (monitor_order cancel), P2-2 (slippage buffer), P2-3 (re-validate after monitor_price), P2-4 (cache eviction), P2-5 (DB path) | ~2 days | 1 week |
| **Sprint 5 — Production Hardening** | Automated fee refresh, cross-bot rate limiting, shared cache, full config schema, performance optimisations | ~1 week | 2 weeks |
| **Total to live trading** | Sprints 1–2 | ~4 days | **~2 weeks** |
| **Total to full production** | Sprints 1–5 | ~3 weeks | **~6 weeks** |

---

## 10. Risk Mitigation Strategy

### Critical — Startup live mode guard (T-14, S-13, C-07)

**Immediate mitigation:** Manually verify `is_simulating_trade = 1` in all config files before any deployment. Document this as a required pre-deployment checklist item.

**Long-term remediation:**
```python
# sonarft_bot.py — load_configurations()
if self.is_simulating_trade == 0:
    if not os.environ.get("SONARFT_ALLOW_LIVE"):
        raise BotCreationError(
            "Live trading requires SONARFT_ALLOW_LIVE=true. "
            "Set is_simulating_trade=1 for simulation."
        )
    self.logger.warning("⚠️  LIVE TRADING MODE ACTIVE")
```

**Validation test:**
```python
def test_live_mode_without_env_var_raises():
    bot = SonarftBot.__new__(SonarftBot)
    bot.is_simulating_trade = 0
    with pytest.raises(BotCreationError, match="SONARFT_ALLOW_LIVE"):
        bot._check_live_mode_guard()
```

---

### High — No persistent position tracker (E-24)

**Immediate mitigation:** In live mode, manually monitor exchange open positions after each bot restart. Keep `trade_amount` small (< 0.01 BTC equivalent) to limit exposure.

**Long-term remediation:** Add `positions` table to SQLite:
```sql
CREATE TABLE IF NOT EXISTS positions (
    botid TEXT NOT NULL,
    exchange TEXT NOT NULL,
    base TEXT NOT NULL,
    quote TEXT NOT NULL,
    side TEXT NOT NULL,
    amount REAL NOT NULL,
    price REAL NOT NULL,
    order_id TEXT,
    opened_at TEXT NOT NULL,
    status TEXT DEFAULT 'open',
    PRIMARY KEY (botid, order_id)
)
```
Record on first leg fill; close on second leg fill; reconcile on startup.

---

### High — Unbounded `trade_tasks` list (S-09)

**Immediate mitigation:** Set `max_orders_per_minute = 2` and `trade_amount` small to limit concurrent task accumulation.

**Long-term remediation:**
```python
# trade_executor.py
MAX_CONCURRENT_TRADES = int(os.environ.get("SONARFT_MAX_CONCURRENT_TRADES", "10"))

def execute_trade(self, botid, trade_data: dict) -> None:
    active = [t for t in self.trade_tasks if not t.done()]
    if len(active) >= MAX_CONCURRENT_TRADES:
        self.logger.warning(f"Max concurrent trades ({MAX_CONCURRENT_TRADES}) reached — skipping")
        log_risk_event(str(botid), "concurrent_limit", f"active={len(active)}")
        return
    ...
```

---

### High — Static fee rates (T-11)

**Immediate mitigation:** Manually verify fee rates in `config_fees.json` match current exchange fee schedules before each live session.

**Long-term remediation:** Add `refresh_fees()` to `SonarftApiManager`:
```python
async def refresh_fees(self) -> None:
    for exchange in self.exchanges_instances:
        try:
            fees = await asyncio.wait_for(exchange.fetch_trading_fees(), timeout=30.0)
            # Update self.exchanges_fees for this exchange
        except Exception as e:
            self.logger.warning(f"Fee refresh failed for {exchange.id}: {e}")
```
Call at startup and every 24 hours via a background task.

---

## 11. Recommended Next Steps

In strict priority order:

1. **Fix startup live mode guard** (P0-1, 1 hour) — Add `SONARFT_ALLOW_LIVE` check in `load_configurations()`. This is the single most important fix. Do this before anything else.

2. **Add `ccxt[pro]` to requirements** (P0-3, 30 minutes) — The default transport library is not declared. This causes deployment failures.

3. **Add `MAX_CONCURRENT_TRADES` limit** (P0-2, 2 hours) — Prevents memory exhaustion under high trade frequency.

4. **Fix StochRSI truthiness check** (P0-4, 30 minutes) — `if stoch_buy is not None` instead of `if stoch_buy`. One-line fix that corrects a signal masking bug.

5. **Add SQL table allowlist** (P0-5, 1 hour) — Add `_ALLOWED_TABLES` frozenset to `SonarftHelpers`. Prevents future SQL injection.

6. **Implement persistent position tracker** (P1-1, 1–2 days) — Add `positions` table to SQLite. Record on first leg fill, close on second leg fill, reconcile on startup. This is the largest single piece of work but is required for live trading.

7. **Fix `indicators_3` config entry** (P1-5, 15 minutes) — Change `"rsi, stoch rsi"` to `["rsi", "stoch rsi"]`. Trivial fix.

8. **Wrap SQLite daily loss calls in `asyncio.to_thread`** (P1-3, 1 hour) — Eliminates the only remaining blocking call on the event loop.

9. **Add `pip-audit` to CI** (P1-4, 1 hour) — Automated dependency vulnerability scanning.

10. **Add `test_sonarft_api_manager.py`** (P1-9, 4 hours) — The exchange integration layer has zero test coverage. This is the highest-value testing investment.

11. **Add `test_trade_executor.py`** (P1-10, 4 hours) — Task lifecycle and shutdown testing.

12. **Extract RSI thresholds to `models.py`** (P1-7, 1 hour) — Fixes the 72/28 vs 70/30 inconsistency.

13. **Remove `market_movement()` from indicator gather** (P1-8, 1 hour) — Eliminates 2 wasted API calls per combination.

14. **Add WS→REST fallback** (P1-2, 4 hours) — Improves resilience against WebSocket failures.

15. **Add JSON schema validation** (P1-6, 4 hours) — Prevents silent misconfiguration.

16. **Add `try/finally` to `monitor_order()`** (P2-1, 2 hours) — Ensures order is cancelled on task cancellation.

17. **Add slippage buffer parameter** (P2-2, 2 hours) — Protects marginal trades from price movement during monitoring.

18. **Re-validate profitability after `monitor_price()`** (P2-3, 2 hours) — Prevents executing trades that are no longer profitable.

19. **Add cache LRU eviction for order book and ticker** (P2-4, 2 hours) — Prevents unbounded memory growth.

20. **Anchor `_DB_PATH` to `_BOT_DIR`** (P2-5, 1 hour) — Fixes database path inconsistency.

---

## 12. Conclusion

### System maturity

SonarFT is a well-engineered trading bot that demonstrates clear architectural thinking, consistent coding standards, and strong financial calculation correctness. The codebase is the result of sustained, disciplined development — not a prototype. The async architecture is sound, the dependency injection is consistent, and the financial math is correct.

The system is **mature for simulation mode** and **approaching readiness for live trading**. The gap between current state and live-trading readiness is not architectural — it is a focused set of safety and reliability features that are well-understood and straightforward to implement.

### Path to production

**Week 1 (Sprint 1 + Sprint 2):** Resolve all 3 live trading blockers (startup guard, position tracker, task limit) plus the deployment fix (`ccxt.pro`). After this sprint, the system is safe for live trading with small amounts on a single exchange pair.

**Weeks 2–3 (Sprints 3–4):** Add test coverage for infrastructure, fix configuration issues, add financial safety improvements (slippage buffer, profitability re-validation). After this sprint, the system is suitable for regular live trading.

**Weeks 4–6 (Sprint 5):** Add automated fee refresh, cross-bot rate limiting, shared cache, and full production hardening. After this sprint, the system is ready for multi-bot, multi-exchange production deployment.

### Key success factors

1. **The startup live mode guard must be the first commit** — no other work matters if real funds can be placed accidentally.
2. **The position tracker is the most complex feature** — allocate adequate time and test it thoroughly before going live.
3. **Start live trading with the smallest possible `trade_amount`** — even after all fixes, live trading carries inherent market risk.
4. **Monitor the first live sessions manually** — watch logs, check exchange positions, verify P&L matches expectations.

### Timeline realism

The 2-week estimate to live trading readiness is achievable for an experienced Python developer familiar with the codebase. The 6-week estimate to full production is realistic assuming no major scope changes. The estimates assume the developer has access to exchange sandbox/testnet environments for integration testing.

### Final verdict

**SonarFT is a Beta-quality system.** It is production-ready for simulation, approaching readiness for live trading, and has a clear, achievable path to full production. The identified issues are well-understood, the fixes are concrete, and the codebase quality is high enough to support rapid iteration.

---

*This report synthesizes findings from 10 review prompts covering 221 individual findings across architecture, async/concurrency, trading logic, financial math, indicators, exchange integration, configuration, security, performance, and code quality.*
