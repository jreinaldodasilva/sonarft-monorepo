# Prompt 10 — Code Quality & Python Best Practices Review

**Generated:** July 2025  
**Reviewer:** Amazon Q (Senior Python / Code Quality / PEP 8)  
**Source files inspected:** All `packages/api/src/` and `packages/bot/` Python source files  
**Output location:** `docs/code-quality/10-code-quality-python.md`

---

## Executive Summary

Both packages demonstrate solid Python craftsmanship: consistent module docstrings, dependency injection throughout, `async/await` used correctly, `Decimal` arithmetic for financial calculations, and meaningful naming. The API package is notably clean — short focused modules, consistent `Annotated` dependency aliases, and Pydantic v2 used correctly. The bot package is larger and shows more variation: some modules are exemplary (`sonarft_math.py`, `trade_executor.py`) while others have quality gaps (`sonarft_execution.py` at ~350 lines with deeply nested conditionals, `sonarft_validators.py` with an unreachable `self.volatility` reference). The most impactful cross-cutting issues are: no linting or formatting tooling configured in either package; inconsistent type hint coverage (complete in API, partial in bot); f-string log calls that defeat lazy evaluation; and several TODO comments marking unfinished implementations that could affect production behaviour.

---

## Code Quality Scorecard

| Dimension | API Package | Bot Package | Notes |
|---|---|---|---|
| PEP 8 compliance | ✅ Good | ⚠️ Mostly good | Bot has some long lines, inconsistent blank lines |
| Naming conventions | ✅ Consistent | ✅ Consistent | One legacy `InitializeModules` → `initialize_modules` |
| Type hints | ✅ Complete | ⚠️ Partial | Bot public methods mostly typed; internals often not |
| Docstrings | ⚠️ Minimal | ✅ Good | API docstrings are one-liners; bot has parameter docs |
| Import organisation | ✅ Clean | ✅ Clean | Both follow stdlib → third-party → local order |
| Code complexity | ✅ Low | ⚠️ Medium | `sonarft_execution.py` has high cyclomatic complexity |
| Code duplication | ⚠️ Some | ⚠️ Some | `get_order_book` wrapper repeated in 3 bot modules |
| Constants / magic numbers | ⚠️ Some | ⚠️ Some | Hardcoded timeouts, depths, thresholds in bot |
| Error handling specificity | ⚠️ Broad | ✅ Good | API `generic_error_handler` too broad; bot is specific |
| Async correctness | ✅ Correct | ✅ Correct | No blocking calls in async context |
| Resource management | ✅ Good | ✅ Good | `with` statements used for all file/DB access |
| Linting tooling | ❌ None | ❌ None | No ruff/flake8/pylint configured in either package |
| Formatting tooling | ❌ None | ❌ None | No black/autopep8 configured |
| Type checking tooling | ❌ None | ❌ None | No mypy configured |

---

## 1. Linting & Formatting Tooling — Missing in Both Packages

Neither package has a linting or formatting configuration. The bot's `pyproject.toml` has no `[tool.ruff]`, `[tool.black]`, or `[tool.mypy]` section. The API has no `pyproject.toml` at all.

**Recommended minimum `pyproject.toml` additions (bot) / new file (API):**

```toml
[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I", "UP", "B", "SIM"]
ignore = ["E501"]  # handled by formatter

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.11"
strict = false
ignore_missing_imports = true
warn_return_any = true
warn_unused_ignores = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

---

## 2. Type Hint Coverage

### API Package — Complete

All public methods in the API package have full type annotations including return types. The `Annotated` alias pattern is used consistently:

```python
# bots.py — clean, reusable alias
Auth = Annotated[None, Depends(require_auth)]

@router.get("", response_model=BotListResponse)
async def list_bots(
    client_id: str,
    _: Auth,
    service: BotService = Depends(get_bot_service),
) -> BotListResponse:
```

### Bot Package — Partial

Public methods in `sonarft_indicators.py`, `sonarft_prices.py`, and `sonarft_validators.py` have type annotations. Internal helpers and some older methods do not:

```python
# sonarft_manager.py — missing return types and parameter types
async def add_bot_instance(self, client_id, botid, bot):       # no types
async def remove_bot_instance(self, botid):                     # no types
def get_botids(self, client_id):                                # no return type
async def create_bot(self, client_id):                          # no return type

# sonarft_execution.py — mixed
async def execute_trade(self, botid, trade: dict) -> bool:      # botid untyped
async def _execute_single_trade(self, botid, trade: Trade) -> Tuple[bool, bool, bool]:  # botid untyped
```

`botid` is used as both `int` and `str` across the codebase (created as `str(uuid.uuid4())` in `sonarft_bot.py` but typed as `int` in some test fixtures). A `BotId = str` type alias would clarify this.

---

## 3. Naming Conventions

### Consistent Strengths

- Classes: `PascalCase` throughout (`SonarftBot`, `BotManager`, `TradeProcessor`)
- Methods: `snake_case` throughout
- Constants: `UPPER_SNAKE_CASE` (`LOW_VOLATILITY_THRESHOLD`, `EXCHANGE_RULES`, `_TIMEFRAME_SECONDS`)
- Private methods: leading underscore (`_execute_single_trade`, `_get_bot_unsafe`, `_safe_path`)

### Issues

| Issue | Location | Severity |
|---|---|---|
| `InitializeModules` uses PascalCase — should be `initialize_modules` | `sonarft_bot.py` (now renamed to `initialize_modules` — ✅ fixed) | Low |
| `set_api_keys` duplicated on both `SonarftBot` and `SonarftApiManager` — same name, different signatures | `sonarft_bot.py:set_api_keys`, `sonarft_api_manager.py:set_api_keys` | Low |
| `has_requirements_for_success_carrying_out` — overly verbose method name | `trade_validator.py` | Low |
| `v1009` version string hardcoded in log messages | `trade_processor.py:42,55` | Low |

---

## 4. Code Complexity Analysis

### High-Complexity Functions

| Function | File | Lines | Cyclomatic Complexity | Issue |
|---|---|---|---|---|
| `_execute_single_trade` | `sonarft_execution.py` | ~100 | High (~12) | Deeply nested if/elif for market direction × RSI × StochRSI |
| `weighted_adjust_prices` | `sonarft_prices.py` | ~120 | High (~10) | 16-coroutine gather + 6 conditional spread branches |
| `execute_long_trade` | `sonarft_execution.py` | ~50 | Medium (~6) | Sequential order placement with partial fill handling |
| `load_configurations` | `sonarft_bot.py` | ~50 | Medium (~5) | Multiple config file loads with error handling |
| `get_trade_dynamic_spread_threshold_avg` | `sonarft_validators.py` | ~50 | Medium (~5) | O(n²) loop + threshold calculation |

### `_execute_single_trade` — Refactoring Opportunity

```python
# sonarft_execution.py — current: deeply nested
if market_direction_buy == 'bull' and market_direction_sell == 'bull':
    if market_rsi_buy >= 70 and market_rsi_sell >= 70 and ...:
        trade_position = 'SHORT'
        result_buy_order, result_sell_order = await self.execute_short_trade(...)
        ...
    else:
        trade_position = 'LONG'
        result_buy_order, result_sell_order = await self.execute_long_trade(...)
        ...
elif market_direction_buy == 'bear' and market_direction_sell == 'bear':
    if market_rsi_buy <= 30 and ...:
        ...
```

This can be extracted into a `_determine_trade_position` method that returns `('LONG'|'SHORT'|None)`, separating the decision logic from the execution:

```python
def _determine_trade_position(self, trade: Trade) -> Optional[str]:
    """Determine trade position from market indicators. Returns 'LONG', 'SHORT', or None."""
    bull_bull = trade.market_direction_buy == 'bull' and trade.market_direction_sell == 'bull'
    bear_bear = trade.market_direction_buy == 'bear' and trade.market_direction_sell == 'bear'
    overbought = (trade.market_rsi_buy >= 70 and trade.market_rsi_sell >= 70
                  and trade.market_stoch_rsi_buy_k > trade.market_stoch_rsi_buy_d
                  and trade.market_stoch_rsi_sell_k > trade.market_stoch_rsi_sell_d)
    oversold = (trade.market_rsi_buy <= 30 and trade.market_rsi_sell <= 30
                and trade.market_stoch_rsi_buy_k < trade.market_stoch_rsi_buy_d
                and trade.market_stoch_rsi_sell_k < trade.market_stoch_rsi_sell_d)

    if bull_bull:
        return 'SHORT' if overbought else 'LONG'
    if bear_bear:
        return 'LONG' if oversold else 'SHORT'
    return None
```

---

## 5. Code Duplication

### `get_order_book` Wrapper — 3 Copies

The same thin wrapper method appears in three bot modules:

```python
# sonarft_indicators.py:get_order_book
async def get_order_book(self, exchange_id: str, base: str, quote: str) -> dict:
    return await self.api_manager.get_order_book(exchange_id, base, quote)

# sonarft_validators.py:get_order_book  — identical
async def get_order_book(self, exchange_id: str, base: str, quote: str) -> dict:
    return await self.api_manager.get_order_book(exchange_id, base, quote)

# sonarft_prices.py — calls through sonarft_indicators.get_order_book
```

These wrappers exist to allow mocking in tests (mock `self.api_manager` rather than the method directly). This is acceptable but the pattern is repeated for `get_trading_volume`, `get_history`, and `get_trade_history` as well — 4 wrapper methods × 2 classes = 8 identical one-liners. A mixin or base class could consolidate these.

### `_make_trade` / `_make_execution` Test Fixtures — Duplicated

The `_make_trade` and `_make_execution` helper functions are defined independently in `test_sonarft_bot.py`, `test_simulation_integration.py`, and `test_sonarft_search_execution.py` with near-identical implementations. These should be moved to `conftest.py`.

### Error Handler Pattern — Duplicated in Endpoints

```python
# bots.py — repeated in run_bot, stop_bot, remove_bot
try:
    await service.run_bot(botid)
    return MessageResponse(message=f"Bot {botid} started.")
except BotNotFoundError as exc:
    raise HTTPException(status_code=404, detail=str(exc)) from exc
```

This try/except pattern is repeated three times. A decorator or context manager could consolidate it, though the current repetition is readable and the duplication is minor.

---

## 6. Magic Numbers & Hardcoded Values

| Value | Location | Recommendation |
|---|---|---|
| `30.0` (API call timeout) | `sonarft_api_manager.py:call_api_method` | `_API_TIMEOUT_SECONDS = 30.0` |
| `30.0` (indicator gather timeout) | `sonarft_prices.py:weighted_adjust_prices` | `_INDICATOR_GATHER_TIMEOUT = 30.0` |
| `120` (monitor_price max wait) | `sonarft_execution.py:monitor_price` | `_PRICE_MONITOR_TIMEOUT = 120` |
| `300` (monitor_order max wait) | `sonarft_execution.py:monitor_order` | `_ORDER_MONITOR_TIMEOUT = 300` |
| `3` (cancel retry count) | `sonarft_execution.py:_cancel_order_with_retry` | `_CANCEL_MAX_RETRIES = 3` |
| `0.02` (flash crash threshold) | `sonarft_execution.py:_execute_single_trade` | `_FLASH_CRASH_THRESHOLD = 0.02` |
| `72` / `28` (RSI hysteresis) | `sonarft_prices.py` | `_RSI_OVERBOUGHT = 72`, `_RSI_OVERSOLD = 28` |
| `1000` (WS queue size) | `websocket/manager.py` | `_WS_QUEUE_MAX_SIZE = 1000` |
| `30.0` (WS send timeout) | `websocket/manager.py` | `_WS_KEEPALIVE_INTERVAL = 30.0` |
| `64` (botid max length) | `bots.py` Path pattern | `_BOTID_MAX_LEN = 64` |

The bot already defines some constants correctly (`LOW_VOLATILITY_THRESHOLD`, `MEDIUM_VOLATILITY_THRESHOLD`, `_TIMEFRAME_SECONDS`, `_INDICATOR_CACHE_TTL`). The remaining magic numbers should follow the same pattern.

---

## 7. F-String Logging — Defeats Lazy Evaluation

Throughout the bot package, f-strings are used directly in log calls:

```python
# sonarft_manager.py — f-string evaluated even if log level filters it out
self.logger.info(f"Bot: {botid} successfully stored for client: {client_id}.")
self.logger.error(f"Bot creation error: {error}")

# Correct pattern — lazy evaluation, no string construction if filtered
self.logger.info("Bot %s successfully stored for client: %s", botid, client_id)
self.logger.error("Bot creation error: %s", error)
```

F-string log calls construct the string unconditionally, even when the log level would filter the message. For high-frequency paths (indicator logging in `sonarft_prices.py` logs 5 lines per trade cycle), this is a measurable overhead. The `%s` format pattern defers string construction until the handler confirms the message will be emitted.

The API package uses `%s` format correctly in `security.py` and `manager.py`. The bot package uses f-strings almost exclusively.

---

## 8. Unreachable Code — `self.volatility` in `SonarftValidators`

```python
# sonarft_validators.py:check_exchange_slippage
async def check_exchange_slippage(self, exchange: str, action: str, trade: Trade) -> bool:
    ...
    if self.volatility == 'Low' and slippage_tolerance == 0:   # ← AttributeError at runtime
        slippage_tolerance = 0.00001
```

`SonarftValidators` has no `self.volatility` attribute — it is never set in `__init__`. This line will raise `AttributeError` at runtime whenever `check_exchange_slippage` is called with `Low` volatility and zero slippage tolerance. The `volatility` value is computed locally in `get_trade_dynamic_spread_threshold_avg` but never stored on `self`. This is dead/broken code.

---

## 9. TODO Comments Marking Unfinished Implementations

```python
# sonarft_api_manager.py:get_balance
# TODO: Finish implementation
async def get_balance(self, exchange_id: str) -> Dict[str, Union[str, float]]:

# sonarft_api_manager.py:get_trades_history
# TODO: Finish the Implementation - use the since and limit
async def get_trades_history(self, exchange_id: str, base: str, quote: str) -> List[...]:
```

`get_balance` is called in live mode by `SonarftExecution.check_balance` — if the implementation is incomplete, live trading balance checks may silently fail. `get_trades_history` is called by `SonarftValidators.check_slippage` — if it returns incomplete data, slippage calculations will be wrong.

These TODOs should be tracked as issues, not left as comments.

---

## 10. Docstring Quality

### API Package

Docstrings are present but minimal — single-line descriptions only:

```python
# health.py
async def health() -> HealthResponse:
    """Service health check."""

# bot_service.py
class BotService:
    """
    Wraps the sonarft-bot BotManager.
    Imported lazily so the API can start even if the bot package
    is not yet installed (useful during development).
    """
```

No parameter or return value documentation. For a public API, the OpenAPI docs are auto-generated from these docstrings — richer docstrings improve the interactive docs.

### Bot Package

Bot docstrings are more complete, with parameter documentation on most public methods:

```python
# sonarft_manager.py
async def add_bot_instance(self, client_id, botid, bot):
    """
    Adds a new bot instance to the _bots dictionary and stores the bot id.

    Parameters:
    client_id (str): The client id to associate the new bot with.
    botid (str): The unique identifier for the bot.
    bot (SonarftBot): An instance of the SonarftBot class.
    """
```

The format is informal (not Google/NumPy style) but consistent and readable.

---

## 11. Import Organisation

Both packages follow the correct import order (stdlib → third-party → local) consistently. No star imports, no circular imports detected. The API uses `from __future__ import annotations` correctly in files that need forward references.

One minor issue in the bot: `import time as _time` uses a private-style alias for a stdlib module. This is intentional (to avoid shadowing the `time` module name in local scope) but unusual — a comment explaining the alias would help.

---

## 12. Context Managers & Resource Management

All file I/O uses `with` statements correctly in both packages. SQLite connections use `with sqlite3.connect(...) as conn:` which auto-commits on success and rolls back on exception. No resource leaks detected.

One gap: `SonarftApiManager.load_exchanges_instances` creates exchange instances but `close_exchange` must be called explicitly. The `SonarftBot.stop_bot` method does call `close_exchange` for all instances — this is correct but relies on `stop_bot` always being called, which is not guaranteed if the process is killed with SIGKILL.

---

## 13. Cross-Package Consistency

| Aspect | API | Bot | Consistent? |
|---|---|---|---|
| Logger injection pattern | `logger or logging.getLogger(__name__)` | `logger or logging.getLogger(__name__)` | ✅ Yes |
| Dependency injection | `Depends()` (FastAPI) | Constructor injection | ✅ Yes (different mechanisms, same principle) |
| Async I/O offload | `asyncio.to_thread` | `asyncio.to_thread` | ✅ Yes |
| Error return pattern | `HTTPException` | `return None/False` | ✅ Yes (appropriate to layer) |
| Log format | `%s` style | f-string style | ❌ Inconsistent |
| Type hints | Complete | Partial | ❌ Inconsistent |
| Docstring format | One-liner | Informal multi-line | ❌ Inconsistent |
| Constants | Inline | Module-level | ⚠️ Partially consistent |

---

## Issues Summary

| # | Issue | Severity | Location |
|---|---|---|---|
| 1 | `self.volatility` referenced in `check_exchange_slippage` but never set — `AttributeError` at runtime | **High** | `sonarft_validators.py:check_exchange_slippage` |
| 2 | No linting/formatting tooling in either package — style drift inevitable | **Medium** | Both packages |
| 3 | F-string log calls throughout bot package — defeats lazy evaluation on hot paths | **Medium** | `sonarft_manager.py`, `sonarft_prices.py`, `sonarft_execution.py`, others |
| 4 | `get_balance` and `get_trades_history` marked TODO — may be incomplete in production | **Medium** | `sonarft_api_manager.py` |
| 5 | `_execute_single_trade` has high cyclomatic complexity (~12) — hard to test and maintain | **Medium** | `sonarft_execution.py` |
| 6 | `botid` typed inconsistently — `int` in some places, `str` in others | **Medium** | `sonarft_bot.py`, `sonarft_execution.py`, tests |
| 7 | Magic numbers for timeouts, thresholds, depths scattered across bot modules | **Low** | Multiple bot files |
| 8 | `get_order_book`/`get_history`/`get_trading_volume` wrapper methods duplicated across 2 classes | **Low** | `sonarft_indicators.py`, `sonarft_validators.py` |
| 9 | `_make_trade`/`_make_execution` test helpers duplicated across 3 test files | **Low** | Bot test files |
| 10 | `v1009` version string hardcoded in log messages | **Low** | `trade_processor.py:42,55` |
| 11 | No `mypy` configuration — type errors go undetected | **Low** | Both packages |
| 12 | API docstrings are one-liners — OpenAPI docs lack parameter descriptions | **Low** | `packages/api/src/` |

---

## Recommendations

### Priority 1 — Fix broken code

**1. Fix `self.volatility` AttributeError**

```python
# sonarft_validators.py:check_exchange_slippage — fix
async def check_exchange_slippage(self, exchange: str, action: str, trade: Trade) -> bool:
    history = await self.get_trade_history(exchange, trade.base, trade.quote)
    preprocessed_data = self.preprocess_trade_data(history)
    slippage_tolerance = self.calculate_slippage_tolerance(exchange, preprocessed_data, 1)
    if slippage_tolerance is None:
        self.logger.warning(f"Slippage tolerance not found for {exchange}")
        return False

    order_book = await self.get_order_book(exchange, trade.base, trade.quote)
    top_price = order_book['asks'][0][0] if action == 'Buy' else order_book['bids'][0][0]
    trade_price = trade.buy_price if action == 'Buy' else trade.sell_price
    slippage = ((top_price) - trade_price) / trade_price if trade_price != 0 else 0

    # Fix: volatility is not stored on self — use a local default
    if slippage_tolerance == 0:
        slippage_tolerance = 0.00001

    return slippage <= slippage_tolerance
```

### Priority 2 — Tooling setup

**2. Add `ruff` and `mypy` to both packages**

```toml
# packages/bot/pyproject.toml — add
[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I", "UP"]

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
warn_return_any = true
```

**3. Switch bot logging to `%s` format on hot paths**

```python
# Before (f-string — always evaluated)
self.logger.info(f"RSI buy={market_rsi_buy:.2f} sell={market_rsi_sell:.2f}")

# After (lazy — only evaluated if INFO level is active)
self.logger.info("RSI buy=%.2f sell=%.2f", market_rsi_buy, market_rsi_sell)
```

### Priority 3 — Refactoring

**4. Extract `_determine_trade_position` from `_execute_single_trade`** (see Section 4)

**5. Define module-level constants for magic numbers**

```python
# sonarft_execution.py — add at module level
_FLASH_CRASH_THRESHOLD = 0.02
_PRICE_MONITOR_TIMEOUT = 120
_ORDER_MONITOR_TIMEOUT = 300
_CANCEL_MAX_RETRIES = 3
```

**6. Add `BotId` type alias**

```python
# models.py — add
from typing import TypeAlias
BotId: TypeAlias = str
```

---

## Python Best Practices Checklist

| Practice | API | Bot |
|---|---|---|
| PEP 8 compliance | ✅ | ⚠️ |
| Type hints on all public methods | ✅ | ⚠️ |
| No star imports | ✅ | ✅ |
| No circular imports | ✅ | ✅ |
| `with` for all file/DB access | ✅ | ✅ |
| `asyncio.to_thread` for blocking I/O | ✅ | ✅ |
| `%s` format in log calls | ✅ | ❌ |
| Constants for magic numbers | ⚠️ | ⚠️ |
| No `self.volatility` style bugs | ✅ | ❌ |
| No TODO in production paths | ✅ | ❌ |
| Ruff / flake8 configured | ❌ | ❌ |
| mypy configured | ❌ | ❌ |
| Black / formatter configured | ❌ | ❌ |

---

_Part of the SonarFT API Code Review Prompt Suite — Prompt 10_  
_Previous: [Prompt 09 — Testing & Quality](../testing/09-testing-quality.md)_  
_Next: [Prompt 11 — Final Consolidation](../prompts/11-final-consolidation.md)_
