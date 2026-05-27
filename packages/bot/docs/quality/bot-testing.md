# Bot Package — Code Quality, Testing & Refactoring Review

**Prompt ID:** 10-BOT-QUALITY  
**Generated:** July 2025  
**Source:** `packages/bot/` — full static analysis  
**Output File:** `docs/quality/bot-testing.md`  
**Depends On:** All previous prompts (01–09)

---

## 1. Naming Consistency Audit

### Variable names

Overall naming is descriptive and consistent. Key observations:

| Pattern | Assessment | Examples |
|---|---|---|
| Snake_case throughout | ✅ Consistent | `buy_price`, `trade_amount`, `profit_percentage` |
| Boolean flags as `is_*` | ✅ | `is_simulating_trade`, `is_simulation_mode`, `is_halted` |
| Private helpers as `_*` | ✅ | `_bot_path`, `_load_config_section`, `_execute_two_leg_trade` |
| Async helpers as `_*_sync` | ✅ | `_load_daily_loss_sync`, `_save_daily_loss_sync` |
| Cache keys as f-strings | ✅ | `f"rsi:{exchange}:{base}/{quote}:{period}:{timeframe}"` |

**Finding — `weight` used for two different concepts:** In `trade_processor.py`, `weight=12` is passed as the VWAP order book depth (an integer). In `sonarft_prices.py`, `weight` is a float 0–1 blend factor computed from volatility. The same name in adjacent code paths with different semantics is confusing. Should be `vwap_depth=12` and `blend_weight` respectively.

**Finding — `sonarft` prefix on all class names is redundant within the package:** `SonarftMath`, `SonarftPrices`, `SonarftIndicators` etc. are all in the `sonarft_bot` package — the prefix adds no disambiguation value internally. Externally (when imported by the API layer), the prefix is useful. This is a style choice, not a bug.

**Finding — `botid` vs `bot_id` inconsistency:** The codebase uses `botid` (no underscore) throughout, which is consistent internally but deviates from Python naming conventions (`bot_id` would be more idiomatic). Since it is consistent, this is Low priority.

### Constant naming

| Constant | Convention | Assessment |
|---|---|---|
| `RSI_OVERBOUGHT`, `RSI_OVERSOLD` | UPPER_CASE ✅ | Correct |
| `OHLCV_TIMESTAMP`, `OHLCV_HIGH` etc. | UPPER_CASE ✅ | Correct |
| `_TIMEFRAME_SECONDS`, `_INDICATOR_CACHE_TTL` | `_UPPER_CASE` ✅ | Module-private constants |
| `_MAX_CONCURRENT_TRADES` | `_UPPER_CASE` ✅ | Correct |
| `_ALLOWED_TABLES` | `_UPPER_CASE` ✅ | Correct |
| `_BOT_VERSION = "v1009"` | Mixed — string value | Low concern |

### Function names

All function names are clear and action-oriented. `get_*` for reads, `set_*` for writes, `create_*` for construction, `execute_*` for side effects. ✅

**Finding — `has_requirements_for_success_carrying_out` is verbose:** This function name is 44 characters. `validate_trade_requirements` or `check_trade_prerequisites` would be clearer and shorter.

---

## 2. Module Documentation

### Module-level docstrings

| Module | Docstring | Quality |
|---|---|---|
| `models.py` | ✅ | Clear — "Domain data classes shared across modules" |
| `config_schemas.py` | ✅ | Clear — explains purpose and when validation runs |
| `sonarft_math.py` | ✅ | Clear |
| `sonarft_api_manager.py` | ✅ | Clear |
| `sonarft_bot.py` | ✅ | Clear |
| `sonarft_manager.py` | ✅ | Clear |
| `sonarft_search.py` | ✅ | Clear |
| `sonarft_execution.py` | ✅ | Clear |
| `sonarft_prices.py` | ❌ | Missing module docstring |
| `sonarft_indicators.py` | ✅ | Clear |
| `sonarft_helpers.py` | ✅ | Clear — explains SQLite strategy |
| `sonarft_validators.py` | ✅ | Clear |
| `sonarft_metrics.py` | ✅ | Clear |
| `trade_processor.py` | ✅ | Clear |
| `trade_executor.py` | ✅ | Clear |
| `trade_validator.py` | ✅ | Clear |

### Class docstrings

Most classes have docstrings. Quality varies:

| Class | Docstring | Quality |
|---|---|---|
| `SonarftBot` | `""" """` | ⚠️ Empty — placeholder only |
| `BotManager` | ✅ | Adequate |
| `SonarftApiManager` | ✅ | Adequate |
| `SonarftExecution` | ✅ | Adequate |
| `SonarftSearch` | ✅ | Good — explains "healthy trade" concept |
| `SonarftMath` | ✅ | One-liner, adequate |
| `SonarftValidators` | ✅ | Good — explains subclassing intent |
| `TradeProcessor` | ✅ | One-liner, adequate |
| `TradeExecutor` | ✅ | One-liner, adequate |

**Finding — `SonarftBot` class docstring is empty (`""" """`):** The most complex class in the codebase has no documentation. Given its 782 lines and 8+ responsibilities, a docstring explaining its role, lifecycle, and key methods is essential.

### Function docstrings

Coverage is high (~85% of public methods). Most docstrings describe parameters and purpose. Key gaps:

- `SonarftBot.run_bot` — no docstring
- `SonarftBot.initialize_modules` — no docstring
- `SonarftPrices.weighted_adjust_prices` — no docstring (most complex pricing function)
- `SonarftPrices._adjust_market_making` — has docstring ✅
- `SonarftExecution._determine_position` — has docstring ✅

---

## 3. Type Annotations

### Coverage assessment

| Module | Parameter hints | Return hints | Coverage |
|---|---|---|---|
| `models.py` | ✅ Full | ✅ Full | ~95% |
| `config_schemas.py` | ✅ Full (Pydantic) | ✅ Full | ~100% |
| `sonarft_math.py` | Partial | Partial | ~60% |
| `sonarft_api_manager.py` | ✅ Good | ✅ Good | ~80% |
| `sonarft_bot.py` | Partial | Partial | ~50% |
| `sonarft_manager.py` | Partial | Partial | ~55% |
| `sonarft_execution.py` | ✅ Good | ✅ Good | ~75% |
| `sonarft_search.py` | ✅ Good | ✅ Good | ~80% |
| `sonarft_prices.py` | ✅ Good | ✅ Good | ~75% |
| `sonarft_indicators.py` | Partial | Partial | ~60% |
| `sonarft_helpers.py` | ✅ Good | Partial | ~70% |
| `sonarft_validators.py` | ✅ Good | ✅ Good | ~80% |
| `sonarft_metrics.py` | ✅ Full | ✅ Full | ~95% |
| `trade_processor.py` | Partial | Partial | ~55% |
| `trade_executor.py` | Partial | Partial | ~50% |
| `trade_validator.py` | ✅ Full | ✅ Full | ~90% |

**Overall type annotation coverage: ~70%**

**Finding — `sonarft_math.calculate_trade` has no type annotations:** The most financially critical function in the codebase has no parameter or return type hints. Its signature is:

```python
def calculate_trade(self, buy_price, sell_price, buy_price_list, sell_price_list, target_amount, base, quote):
```

Should be:
```python
def calculate_trade(
    self,
    buy_price: float,
    sell_price: float,
    buy_price_list: tuple,
    sell_price_list: tuple,
    target_amount: float,
    base: str,
    quote: str,
) -> tuple[float, float, dict | None]:
```

**Finding — `logger` parameter typed as `= None` without `Optional[logging.Logger]`:** Many constructors accept `logger=None` but type it as just `None` default without `logging.Logger | None`. mypy would flag these.

**Finding — `Trade` dataclass optional fields typed as `float = None`:** Fields like `market_rsi_buy: float = None` should be `market_rsi_buy: float | None = None` for correct type safety.

---

## 4. Code Size & Complexity

### Large files

| File | Lines | Assessment |
|---|---|---|
| `sonarft_execution.py` | 824 | ⚠️ Too large — mixes risk checks, two-leg execution, price monitoring, order monitoring |
| `sonarft_bot.py` | 782 | ⚠️ Too large — God Object (see Prompt 01) |
| `sonarft_api_manager.py` | 597 | ⚠️ Borderline — could split caching from API dispatch |
| `sonarft_helpers.py` | 464 | Acceptable — cohesive SQLite persistence layer |
| `sonarft_indicators.py` | 443 | Acceptable — each method is independent |

### Large functions (> 50 lines)

| Function | Lines (approx) | Issue |
|---|---|---|
| `SonarftBot.apply_parameters` | ~80 | 9 sequential if-blocks + rollback + propagation |
| `SonarftBot.load_configurations` | ~70 | Sequential config loading — acceptable |
| `SonarftBot.initialize_modules` | ~60 | Sequential module construction — acceptable |
| `SonarftBot.create_bot` | ~55 | Startup sequence — acceptable |
| `SonarftExecution._execute_two_leg_trade` | ~90 | Complex two-leg logic with partial fill handling |
| `SonarftExecution.create_order` | ~70 | Pre-flight checks + monitoring + placement |
| `SonarftPrices.weighted_adjust_prices` | ~80 | 14 concurrent fetches + strategy dispatch |
| `SonarftApiManager.call_api_method` | ~60 | Primary + fallback dispatch |
| `SonarftApiManager.refresh_fees` | ~55 | Per-exchange fee update loop |

**Finding — `apply_parameters` has 9 sequential `if key in parameters` blocks:** Each block saves old value, applies new value, and later propagates to child modules. This pattern is repetitive and error-prone — adding a new hot-reloadable parameter requires changes in 3 places (save, apply, propagate). A data-driven approach (dict of `{param: (getter, setter, validator)}`) would be more maintainable.

### Cyclomatic complexity hotspots

| Function | Estimated complexity | Branches |
|---|---|---|
| `SonarftExecution._execute_two_leg_trade` | ~12 | Balance check, first leg, partial fill, second leg, imbalance, cancel |
| `SonarftExecution._determine_position` | ~10 | bull+bull, bear+bear, mixed, missing indicators, flash crash |
| `SonarftBot.apply_parameters` | ~15 | 9 parameter checks + validation + rollback + propagation |
| `SonarftPrices._adjust_market_making` | ~8 | 2 direction checks × 3 RSI/StochRSI branches each |
| `SonarftApiManager.call_api_method` | ~8 | ccxt/ccxtpro dispatch, timeout, fallback |

### Parameter count

| Function | Parameters | Assessment |
|---|---|---|
| `SonarftExecution.__init__` | 9 | ⚠️ High — consider a config dataclass |
| `SonarftSearch.__init__` | 11 | ⚠️ High — consider a config dataclass |
| `SonarftExecution._execute_two_leg_trade` | 11 | ⚠️ High — consider a `TradeLeg` dataclass |
| `SonarftHelpers.save_trade_history` | 9 | Acceptable — all required |
| `SonarftValidators.get_trade_dynamic_spread_threshold_avg` | 6 | Acceptable |


---

## 5. Duplication Audit

### Confirmed duplications

| Pattern | Locations | Lines duplicated | Priority |
|---|---|---|---|
| `_BOT_DIR` + `_bot_path` definition | `sonarft_bot.py`, `sonarft_helpers.py`, `sonarft_search.py` | ~6 lines × 3 | Medium |
| `_DB_PATH` definition | `sonarft_helpers.py` (class attr), `sonarft_search.py` (module var) | ~1 line × 2 | Medium |
| SQLite `daily_loss` table schema | `sonarft_helpers._init_db`, `sonarft_search._load_daily_loss_sync` | ~8 lines | Medium |
| `asyncio.wait_for(_stop_event.wait(), timeout=N)` pattern | `run_bot`, `_periodic_fee_refresh`, `_periodic_db_backup` | ~5 lines × 3 | Low |
| `except asyncio.CancelledError: pass` | `_periodic_fee_refresh`, `_periodic_db_backup`, `stop_bot` | ~3 lines × 3 | Low |
| `make_math()` helper | `test_sonarft_math.py`, `test_hypothesis_math.py` | ~8 lines × 2 | Low (test code) |
| `price_list()` / `_price_list()` helper | `test_sonarft_math.py`, `test_hypothesis_math.py` | ~2 lines × 2 | Low (test code) |

### Similar logic patterns

**Finding — `execute_long_trade` and `execute_short_trade` are near-identical:** Both delegate to `_execute_two_leg_trade` with swapped arguments. The only difference is which exchange is "first" and which side is "first". This is already well-refactored — the duplication is minimal. ✅

**Finding — LRU eviction pattern repeated in 4 caches:** The same 4-line eviction pattern appears in `_ohlcv_cache`, `_order_book_cache`, `_ticker_cache`, and `_indicator_cache`:

```python
if len(self._cache) >= 500:
    oldest_key = next(iter(self._cache))
    del self._cache[oldest_key]
self._cache[key] = (expires_at, value)
```

This should be extracted into a `_cache_set(cache, key, value, ttl)` helper or replaced with `cachetools.TTLCache`.

**Finding — `_with_timeout` helper defined inline in `weighted_adjust_prices`:** This 5-line helper is defined as a nested function inside `weighted_adjust_prices`. It could be a module-level utility used across the indicator pipeline.

---

## 6. Error Handling Consistency

### Exception handling patterns

| Pattern | Usage | Assessment |
|---|---|---|
| `except Exception: self.logger.exception(...)` | Indicators, execution | ✅ Logs full traceback |
| `except Exception as e: self.logger.error(...)` | API manager, helpers | ✅ Logs message |
| `except asyncio.CancelledError: pass` | Periodic tasks | ✅ Correct — lets cancellation propagate |
| `except asyncio.TimeoutError: self.logger.error(...)` | API calls | ✅ Specific timeout handling |
| `except BotCreationError: self.logger.exception(...)` | Bot creation | ✅ Typed exception |
| `except FileNotFoundError: pass` | Registry file removal | ✅ Expected case |
| Bare `except Exception` swallowing all errors | `_with_timeout` in prices | ⚠️ Hides programming errors |

**Finding — `_with_timeout` catches all exceptions including programming errors:**

```python
async def _with_timeout(coro, default=None):
    try:
        return await asyncio.wait_for(coro, timeout=_IND_TIMEOUT)
    except (asyncio.TimeoutError, Exception):
        return default
```

An `AttributeError` or `TypeError` inside an indicator is silently swallowed and treated as a missing indicator. Should be:

```python
except asyncio.TimeoutError:
    return default
except Exception:
    self.logger.exception("Indicator fetch failed")
    return default
```

**Finding — `sonarft_search._load_daily_loss_sync` silently returns 0.0 on any exception:**

```python
except Exception:
    return 0.0
```

A database corruption or permission error would silently reset the daily loss counter to zero, allowing trading to continue past the daily loss limit. Should log the exception.

**Finding — inconsistent exception types for config errors:** Config loading raises `BotCreationError` for all errors (file not found, invalid JSON, missing key, Pydantic failure). This is consistent but means callers cannot distinguish a missing file from an invalid parameter without parsing the message string.

### Error recovery

| Scenario | Recovery | Assessment |
|---|---|---|
| Config load failure | `BotCreationError` → `create_bot` returns `None` | ✅ Clean |
| API call failure | Returns `None` → caller skips trade | ✅ Graceful |
| Order placement failure | Returns `None` → trade abandoned | ✅ Safe |
| Cancel failure | 3 retries → alert sent | ✅ Robust |
| Circuit breaker trip | Bot halts → alert sent | ✅ Correct |
| Hot-reload validation failure | Rollback applied | ✅ Safe |
| SQLite write failure | Silently ignored (non-critical) | ⚠️ Loss of trade history |

---

## 7. Testing Gaps Analysis

### Test file inventory

| Test file | Tests | Primary coverage |
|---|---|---|
| `test_sonarft_bot.py` | 47 | Config validation, live mode guard, simulation mode, daily loss, parameter validation |
| `test_sonarft_prices.py` | 25 | Price adjustment, VWAP blend, strategy dispatch, support/resistance clamping |
| `test_sonarft_manager.py` | 25 | BotManager lifecycle, add/remove/pause/resume, hot-reload |
| `test_phase4_features.py` | 23 | Circuit breaker, flash crash, rate limiting, exposure checks, slippage |
| `test_sonarft_math.py` | 22 | `calculate_trade` profitability, fees, edge cases, precision, VWAP |
| `test_sonarft_indicators.py` | 20 | RSI, StochRSI, SMA, MACD, volatility, support/resistance |
| `test_sonarft_search_execution.py` | 15 | Search loop, trade dispatch, daily halt, pause/resume |
| `test_sonarft_api_manager.py` | 14 | API dispatch, caching, fee lookup, order book, VWAP |
| `test_simulation_integration.py` | 12 | End-to-end simulation flow |
| `test_sonarft_validators.py` | 11 | Liquidity checks, spread threshold, slippage |
| `test_trade_executor.py` | 9 | Task dispatch, concurrent limit, monitor, shutdown |
| `test_phase3_performance.py` | 9 | Cache TTL, concurrent indicator fetch, cycle timing |
| `test_sonarft_math_precision.py` | 7 | Decimal precision, rounding, fee rounding modes |
| `test_hypothesis_math.py` | 4 | Property-based: profit sign, NaN/Inf, zero amount, fee monotonicity |
| **Total** | **243** | — |

### Coverage by module

| Module | Test file | Coverage assessment |
|---|---|---|
| `sonarft_math.py` | `test_sonarft_math.py` + `test_hypothesis_math.py` + `test_sonarft_math_precision.py` | ✅ Excellent — 33 tests + 4 property tests |
| `sonarft_bot.py` | `test_sonarft_bot.py` | ✅ Good — 47 tests covering key paths |
| `sonarft_manager.py` | `test_sonarft_manager.py` | ✅ Good — 25 tests |
| `sonarft_prices.py` | `test_sonarft_prices.py` | ✅ Good — 25 tests |
| `sonarft_indicators.py` | `test_sonarft_indicators.py` | ✅ Good — 20 tests |
| `sonarft_api_manager.py` | `test_sonarft_api_manager.py` | ✅ Adequate — 14 tests |
| `sonarft_execution.py` | `test_sonarft_search_execution.py` + `test_phase4_features.py` | ⚠️ Partial — execution path tested but not `_execute_two_leg_trade` directly |
| `sonarft_validators.py` | `test_sonarft_validators.py` | ⚠️ Partial — 11 tests, spread threshold not fully covered |
| `sonarft_search.py` | `test_sonarft_search_execution.py` | ⚠️ Partial — daily halt tested, full search loop not |
| `trade_executor.py` | `test_trade_executor.py` | ⚠️ Partial — 9 tests, shutdown path not fully covered |
| `trade_processor.py` | `test_simulation_integration.py` | ⚠️ Partial — integration only, no unit tests |
| `trade_validator.py` | Indirect via `test_sonarft_search_execution.py` | ⚠️ No dedicated unit tests |
| `sonarft_helpers.py` | Indirect via other tests | ⚠️ No dedicated unit tests |
| `sonarft_metrics.py` | None | ❌ No tests |
| `models.py` | Indirect via math tests | ⚠️ `vwap` and `percentage_difference` tested indirectly |
| `config_schemas.py` | `test_sonarft_bot.py` (Pydantic validation) | ✅ Adequate |

### Critical untested areas

**Finding — `_execute_two_leg_trade` has no direct unit tests:** The most complex execution function (90 lines, 12 cyclomatic complexity) is only tested indirectly through integration tests. The partial fill handling, second-leg failure path, and cancel-on-failure logic are not unit-tested. This is the highest-risk untested code in the codebase.

**Finding — `open_position` / `close_position` botid bug is not caught by tests:** The bug where `botid=first_exchange_id` is passed to `open_position` (identified in Prompt 01) is not caught by any test. A test asserting that the stored position's botid matches the bot UUID would have caught this.

**Finding — `monitor_order` timeout and cancellation paths not tested:** The `finally` block in `monitor_order` (which always cancels the order) is not tested. The timeout path (300s elapsed) is not tested. These are critical for live trading safety.

**Finding — `sonarft_helpers.py` has no dedicated test file:** The SQLite persistence layer (orders, trades, positions, daily_loss, backup) has no unit tests. It is exercised indirectly through integration tests but the WAL mode, concurrent write behaviour, and `purge_history` are not tested.

**Finding — `sonarft_metrics.py` has no tests:** The structured JSON emission functions are untested. While they are simple, a test verifying the JSON structure and required fields would catch regressions.

**Finding — REST fallback in `call_api_method` is not tested:** The ccxtpro → ccxt REST fallback path is not covered by any test.

---

## 8. Test-Friendly Code Assessment

### Dependency injection

All modules receive dependencies via constructor injection. ✅ This makes mocking straightforward — replace `api_manager`, `sonarft_helpers`, etc. with `MagicMock` / `AsyncMock`.

The shared `conftest.py` provides a well-designed `mock_api_manager` fixture covering all commonly used methods. ✅

### Global state

No module-level mutable global state except:
- `_metrics_logger` in `sonarft_metrics.py` — a module-level logger (acceptable, standard Python pattern)
- `_BOT_DIR`, `_DB_PATH` — module-level constants (immutable, safe)

No global singletons that would make tests interfere with each other. ✅

### External dependencies mockable

| Dependency | Mockable? | How |
|---|---|---|
| ccxt/ccxtpro exchange | ✅ | `MagicMock` on `SonarftApiManager` |
| SQLite | ✅ | In-memory DB or temp file in tests |
| pandas-ta | ✅ | Mock `get_history` to return controlled OHLCV |
| Environment variables | ✅ | `monkeypatch.setenv` in pytest |
| File system | ✅ | `tmp_path` fixture |
| Webhook HTTP | ✅ | Mock `urllib.request.urlopen` |

### Determinism

**Finding — `random.randint` in `execute_order` (simulation) and `run_bot` (cycle sleep) makes tests non-deterministic:** Simulation order IDs use `random.randint(100000, 999999)` and cycle sleep uses `random.randint(min, max)`. Tests that check order IDs or timing must account for this. The existing tests mock these away correctly. ✅

**Finding — `time.strftime` in `save_order_history` and `save_trade_history` makes timestamps non-deterministic:** Tests that check stored trade data must either mock `time.localtime` or ignore the timestamp field. The existing tests handle this correctly. ✅

---

## 9. Logging Consistency

### Log level usage

| Level | Used for | Appropriate? |
|---|---|---|
| `DEBUG` | Trade search details, price adjustments, indicator values | ✅ Correct — verbose operational data |
| `INFO` | Bot lifecycle, module init, order placement, API key loading | ✅ Correct |
| `WARNING` | Missing indicators, partial fills, stale precision, balance issues | ✅ Correct |
| `ERROR` | API failures, order placement failures, circuit breaker | ✅ Correct |
| `EXCEPTION` | Unexpected exceptions with stack traces | ✅ Correct |
| `WARNING` for audit log | Parameter changes logged at WARNING | ⚠️ Should be INFO with structured data |

**Finding — parameter change audit log uses `WARNING` level:** `apply_parameters` logs parameter changes at `WARNING`:

```python
self.logger.warning(f"Bot {self.botid}: AUDIT parameter change: {changes}")
```

Audit events are not warnings — they are expected operational events. Should use `INFO` with a structured JSON format (via `sonarft_metrics`) for consistency with the rest of the observability layer.

**Finding — `logger.info(f"Bot {botid} start running")` and similar lifecycle messages are inconsistently formatted:** Some messages use f-strings, others use `%s` formatting. Python's logging documentation recommends `%s` formatting (lazy evaluation) for performance, but f-strings are used throughout. This is a style inconsistency, not a bug.

**Finding — no structured logging for position open/close events:** `open_position` and `close_position` log plain text messages. These are financially significant events that should be emitted via `sonarft_metrics` as structured JSON for auditability.

### Log verbosity

- `DEBUG` level is used appropriately for per-cycle trade details — not emitted in production unless debug logging is enabled. ✅
- `INFO` level messages are concise and actionable. ✅
- No sensitive data (API keys, balances) in any log message. ✅


---

## 10. Code Quality Scorecard

| Aspect | Score (1–10) | Assessment |
|---|---|---|
| **Readability** | 7 | Clear naming, good structure; `sonarft_bot.py` and `sonarft_execution.py` are too large |
| **Documentation** | 7 | ~85% docstring coverage; `SonarftBot` class docstring empty; `weighted_adjust_prices` undocumented |
| **Type safety** | 6 | ~70% annotation coverage; `calculate_trade` unannotated; `Trade` optional fields incorrectly typed |
| **Error handling** | 7 | Consistent patterns; `_with_timeout` swallows all exceptions; `_load_daily_loss_sync` silent on DB error |
| **Testability** | 8 | Excellent DI throughout; good mock fixtures; no global state; some non-determinism from `random` |
| **Test coverage** | 7 | 243 tests + 4 property tests; `_execute_two_leg_trade`, `sonarft_helpers`, `monitor_order` paths untested |
| **Performance awareness** | 8 | Good caching strategy; async parallelism used correctly; 4 uncached indicator functions |
| **Security awareness** | 8 | No hardcoded secrets; SQL injection prevented; live trading dual opt-in; `_with_timeout` exception gap |
| **Standards adherence** | 7 | Consistent snake_case; `weight` naming collision; `botid` vs `bot_id`; `sonarft` prefix redundancy |
| **Overall** | **7.2 / 10** | Solid codebase with clear architecture; main gaps are size/complexity of two files and testing of execution paths |

---

## 11. Refactoring Roadmap

| Refactoring | Complexity | Impact | Priority |
|---|---|---|---|
| Fix `open_position(botid=first_exchange_id)` bug | Low | Critical — fixes live trading data integrity | **Immediate** |
| Extract `BotConfig` dataclass from `SonarftBot` | Medium | High — reduces God Object, improves testability | High |
| Centralise `_BOT_DIR` / `_DB_PATH` into `paths.py` | Low | Medium — eliminates duplication across 3 modules | Medium |
| Replace 4 LRU cache dicts with `cachetools.TTLCache` | Low | Medium — fixes race condition, reduces boilerplate | Medium |
| Add type annotations to `calculate_trade` and `Trade` | Low | Medium — enables mypy, improves IDE support | Medium |
| Extract `_execute_two_leg_trade` into `TwoLegTrade` class | High | Medium — improves testability of execution paths | Medium |
| Replace `apply_parameters` if-blocks with data-driven approach | Medium | Medium — reduces maintenance burden for new params | Medium |
| Unify hot-reload validation to use Pydantic | Low | Medium — single source of truth for parameter validation | Medium |
| Add `sonarft_metrics` events for position open/close | Low | Low — improves auditability | Low |
| Change parameter audit log from WARNING to INFO | Low | Low — correct log level semantics | Low |
| Add `Optional[logging.Logger]` type to all `logger=None` params | Low | Low — type correctness | Low |
| Rename `weight` parameter to `vwap_depth` in `process_symbol` | Low | Low — naming clarity | Low |
| Add module docstring to `sonarft_prices.py` | Low | Low — documentation completeness | Low |
| Add class docstring to `SonarftBot` | Low | Low — documentation completeness | Low |
| Migrate `errors_history.json` to SQLite | Medium | Medium — eliminates unbounded file growth | Medium |

---

## 12. Testing Strategy Recommendations

### Unit test targets (highest priority)

**`_execute_two_leg_trade` — direct unit tests needed:**

```python
async def test_first_leg_failure_skips_second_leg():
    """If first leg returns None, second leg must not be placed."""

async def test_partial_first_leg_uses_filled_amount_for_second():
    """actual_second_amount must equal first_executed_amount, not first_amount."""

async def test_second_leg_failure_cancels_first_leg():
    """If second leg returns None, cancel_order must be called for first leg."""

async def test_second_leg_partial_fill_sends_alert():
    """Imbalanced second leg must trigger alert callback."""

async def test_open_position_called_with_correct_botid():
    """open_position must be called with bot UUID, not exchange ID."""
```

**`monitor_order` — timeout and cancellation paths:**

```python
async def test_monitor_order_timeout_cancels_order():
    """After max_wait_seconds, order must be cancelled via _cancel_order_with_retry."""

async def test_monitor_order_finally_always_cancels():
    """Even on successful fill, finally block calls cancel (exchange rejects gracefully)."""

async def test_monitor_order_cancelled_error_propagates():
    """CancelledError must not be swallowed — finally runs then error propagates."""
```

**`sonarft_helpers.py` — dedicated test file:**

```python
async def test_save_and_retrieve_order():
    """Saved order must be retrievable by botid."""

async def test_purge_history_keeps_last_n():
    """After purge, only keep_last records remain."""

async def test_open_and_close_position():
    """Position opened then closed must have status='closed'."""

async def test_get_open_positions_excludes_closed():
    """Closed positions must not appear in get_open_positions."""

def test_backup_db_creates_file():
    """backup_db must create a readable SQLite file at dst_path."""
```

### Property-based tests (Hypothesis)

Extend `test_hypothesis_math.py` with:

```python
@given(amount=st.floats(min_value=0.001, max_value=100.0), ...)
def test_buy_sell_amounts_always_equal(amount, ...):
    """buy_trade_amount must always equal sell_trade_amount in trade_data."""

@given(fee=st.floats(min_value=0.0, max_value=0.01), ...)
def test_fee_always_non_negative(fee, ...):
    """buy_fee_quote and sell_fee_quote must always be >= 0."""
```

### Integration test scenarios

| Scenario | Test file | Status |
|---|---|---|
| Full simulation cycle (signal → execution → history) | `test_simulation_integration.py` | ✅ Exists |
| Hot-reload with rollback on invalid params | `test_sonarft_bot.py` | ✅ Exists |
| Circuit breaker trip after N failures | `test_phase4_features.py` | ✅ Exists |
| Daily loss halt and reset | `test_sonarft_bot.py` | ✅ Exists |
| Multi-bot concurrent execution | `test_sonarft_manager.py` | ✅ Exists |
| Partial fill handling end-to-end | ❌ Missing | Add to `test_sonarft_search_execution.py` |
| Startup reconciliation (stale orders cancelled) | ❌ Missing | Add to `test_sonarft_bot.py` |
| REST fallback on WebSocket failure | ❌ Missing | Add to `test_sonarft_api_manager.py` |

### Test infrastructure improvements

1. **Add `pytest-cov` to CI:** Measure and enforce minimum coverage (suggest 80% for financial modules).
2. **Add `pytest-timeout`:** Prevent tests from hanging on async operations.
3. **Add exchange sandbox tests:** Use ccxt testnet/sandbox for live-mode integration tests without real funds.
4. **Separate fast and slow tests:** Mark property-based tests with `@pytest.mark.slow` to allow quick CI runs.

---

## 13. Conclusion

### Code quality assessment

The codebase is **well-structured and professionally written** for a trading system of this complexity. The architecture is clean, dependency injection is used consistently, and the test suite is substantial (243 tests + 4 property tests). The financial math core (`sonarft_math.py`) is the best-tested and most carefully implemented module — appropriate for the most critical component.

### Top refactoring priorities

1. **Immediate:** Fix `open_position(botid=first_exchange_id)` — data integrity bug.
2. **High:** Extract `BotConfig` from `SonarftBot` — reduces the God Object and improves testability.
3. **Medium:** Replace 4 LRU cache dicts with `cachetools.TTLCache` — fixes race condition and reduces boilerplate.
4. **Medium:** Add type annotations to `calculate_trade` and fix `Trade` optional field types.
5. **Medium:** Centralise `_BOT_DIR` / `_DB_PATH` into `paths.py`.

### Testing gaps and recommendations

The most critical testing gaps are:
1. `_execute_two_leg_trade` — no direct unit tests for the most complex execution path.
2. `sonarft_helpers.py` — no dedicated test file for the persistence layer.
3. `monitor_order` timeout and cancellation paths — untested live trading safety code.
4. The `open_position` botid bug — would have been caught by a simple assertion test.

### Effort estimate for improvements

| Category | Effort | Value |
|---|---|---|
| Fix High bugs (botid, exposure tracking) | 1–2 days | Critical |
| Add missing unit tests (execution, helpers) | 3–5 days | High |
| Type annotation completion | 1–2 days | Medium |
| Refactor `SonarftBot` God Object | 3–5 days | Medium |
| Replace LRU caches with `cachetools` | 0.5 days | Medium |
| Centralise paths | 0.5 days | Low |
| Documentation gaps | 0.5 days | Low |

---

## Implementation Status — July 2025

> All critical and high findings from this review have been resolved.

### Resolved findings

| Finding | Severity | Resolution | Task |
|---|---|---|---|
| `_execute_two_leg_trade` no direct unit tests | Critical | Fixed: `TestTwoLegTradeExtended` (4 tests) + existing partial fill and botid tests | T16 |
| `open_position` botid bug not caught by tests | High | Fixed: `test_open_position_called_with_bot_uuid_not_exchange_id` added | T01/T16 |
| `sonarft_helpers.py` no dedicated test file | Medium | Fixed: `tests/test_sonarft_helpers.py` created (16 tests) | T17 |
| `monitor_order` timeout/cancellation paths untested | Medium | Fixed: `TestMonitorOrderReturnValues` (3 tests) + existing timeout/cancel tests | T18 |
| `calculate_trade` no type annotations | Medium | Fixed: full type annotations added | T21 |
| `Trade` optional fields typed as `float = None` | Medium | Fixed: `float \| None = None` | T21 |
| `apply_parameters` 9 sequential if-blocks | Medium | Fixed: data-driven loop; Pydantic validation | T22+T23 |
| 4 LRU cache dicts repeat eviction pattern | Medium | Fixed: replaced with `cachetools.TTLCache` | T07 |
| `SonarftBot` class docstring empty | Low | Fixed: full docstring documents responsibilities and lifecycle | T34 |
| `weighted_adjust_prices` undocumented | Low | Fixed: full docstring added | T33 |
| `weight=12` naming collision | Low | Fixed: renamed to `vwap_depth=12` | T35 |
| `_with_timeout` swallows all exceptions | Low | Noted in technical debt backlog | — |

### Test count progression

| Phase | Tests Added | Total |
|---|---|---|
| Before implementation | — | 243 |
| Phase 0 | +18 | 261 |
| Phase 1 | +45 | 306 |
| Phase 2 | +7 | 313 |
| Phase 3 | 0 (behavioural) | 313 |
| Phase 4 | +4 | 317 |
| Phase 5 | 0 (behavioural) | **317** |
