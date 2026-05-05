# Code Quality & Python Best Practices Review

**Prompt ID:** 10-API-QUALITY  
**Package:** `packages/api` + `packages/bot`  
**Reviewer:** Amazon Q (Senior Python / Code Quality / Best Practices)  
**Date:** July 2025  
**Status:** Complete

---

## Executive Summary

Both packages demonstrate strong Python code quality. The API package is clean, consistently typed, and well-organised — `ruff` is configured with a sensible ruleset and `mypy` is present in the bot's dev dependencies. The bot package is more complex but follows consistent patterns: dependency injection throughout, `asyncio.to_thread` for all blocking I/O, and a dedicated metrics module for structured observability. The main quality concerns are: the `Makefile` uses `pylint` for linting while both `pyproject.toml` files configure `ruff` — the tooling is inconsistent; the bot package has several long methods that violate the Single Responsibility Principle (`SonarftBot.create_bot` at ~100 lines, `SonarftExecution.execute_long_trade` at ~80 lines); magic numbers appear in several places; and the API's `main.py` mixes application factory, middleware, logging setup, and the WebSocket endpoint in a single 230-line file. Overall the codebase scores approximately **8.2/10** for code quality — production-ready with targeted improvements needed.

---

## Code Quality Scorecard

| Dimension | API Package | Bot Package | Notes |
|---|---|---|---|
| PEP 8 / Style | ✅ 9/10 | ✅ 8/10 | Both use ruff; bot has some long lines |
| Naming conventions | ✅ 9/10 | ✅ 8/10 | Consistent; one PascalCase method in bot |
| Type hints | ✅ 9/10 | ⚠️ 7/10 | API fully typed; bot has gaps |
| Docstrings | ⚠️ 7/10 | ⚠️ 7/10 | Module/class docs present; method docs inconsistent |
| Import organisation | ✅ 9/10 | ✅ 8/10 | Clean; no circular imports |
| Code complexity | ⚠️ 7/10 | ⚠️ 6/10 | Some long methods in bot |
| Code duplication | ⚠️ 7/10 | ✅ 8/10 | API has canonical/legacy duplication |
| Design patterns | ✅ 9/10 | ✅ 9/10 | DI, service layer, async patterns all correct |
| Constants / magic numbers | ⚠️ 7/10 | ⚠️ 7/10 | Some hardcoded values in both packages |
| Error handling | ✅ 8/10 | ✅ 8/10 | Consistent fail-safe pattern |
| Async correctness | ✅ 10/10 | ✅ 9/10 | No blocking calls in async context |
| Resource management | ✅ 9/10 | ✅ 9/10 | Context managers used correctly |
| **Overall** | **8.5/10** | **7.9/10** | Production-ready |

---

## 1. Code Style & Formatting

### 1.1 Linting Configuration

Both packages configure `ruff` in their `pyproject.toml` with identical rulesets:

```toml
# Both packages/api/pyproject.toml and packages/bot/pyproject.toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B"]
ignore = [
    "E501",   # line too long
    "B008",   # function calls in default arguments (FastAPI Depends)
    "UP007",  # X | Y union syntax
    "B904",   # raise-without-from
]
```

The `B904` ignore is notable — it suppresses the "raise without from" warning, which means exception chaining issues (identified in Prompt 06) are not caught by the linter. ⚠️

### 1.2 Linting Tooling Inconsistency

The `Makefile` uses `pylint` for linting:

```makefile
lint-bot: ## Lint bot package
    cd packages/bot && python -m pylint sonarft_*.py || true

lint-api: ## Lint API package
    cd packages/api && python -m pylint src/ || true
```

But `pylint` is not in either `requirements.txt` or `pyproject.toml` dependencies. The `|| true` means lint failures are silently ignored. Both packages configure `ruff` — the `Makefile` should use `ruff check` instead.

### 1.3 No Root-Level Shared Config

There is no root-level `pyproject.toml` or `.ruff.toml` shared across packages. Each package has its own identical `ruff` config — duplication that could drift over time.

### 1.4 `from __future__ import annotations`

Used consistently in the API package (`main.py`, `security.py`, `clients.py`, `bots.py`, etc.) for deferred annotation evaluation. Not used in the bot package. This is a minor inconsistency — the bot targets Python 3.10+ where `from __future__ import annotations` is optional but still useful for forward references.

---

## 2. Naming Conventions

### 2.1 API Package

| Convention | Compliance | Examples |
|---|---|---|
| Classes: `PascalCase` | ✅ | `BotService`, `WebSocketManager`, `RequestIdMiddleware` |
| Functions/methods: `snake_case` | ✅ | `create_bot`, `verify_token`, `handle_connection` |
| Constants: `UPPER_SNAKE_CASE` | ✅ | `_WS_QUEUE_MAX_SIZE`, `_WS_KEEPALIVE_INTERVAL`, `_BOT_LOGGER_NAME` |
| Private: leading underscore | ✅ | `_decode_jwt`, `_client_ip`, `_cleanup` |
| Module-level private vars | ✅ | `_logger`, `_bearer`, `_settings` |

### 2.2 Bot Package

| Convention | Compliance | Examples |
|---|---|---|
| Classes: `PascalCase` | ✅ | `SonarftBot`, `BotManager`, `SonarftExecution` |
| Methods: `snake_case` | ✅ | `create_bot`, `run_bot`, `execute_trade` |
| Exception: `initialize_modules` | ⚠️ | Should be `initialize_modules` — already snake_case ✅ |
| Exception: `InitializeModules` | ⚠️ | Legacy name in older docs — actual code uses `initialize_modules` ✅ |
| Constants: `UPPER_SNAKE_CASE` | ✅ | `RSI_OVERBOUGHT`, `RSI_OVERSOLD`, `OHLCV_CLOSE` |
| Private: leading underscore | ✅ | `_execute_single_trade`, `_determine_position` |

### 2.3 Ambiguous Names

| Name | Location | Issue |
|---|---|---|
| `weight` | `sonarft_prices.py` | Used for both VWAP weight and market strength weight — context-dependent |
| `result_01`, `result_02` | `sonarft_search.py` (older pattern) | Positional names — `buy_result`, `sell_result` would be clearer |
| `t0` | `sonarft_execution.py` | Timing variable — `start_time` or `order_start` would be clearer |

---

## 3. Type Hints & Type Safety

### 3.1 API Package — Type Coverage

All public methods in the API package have complete type annotations:

```python
# security.py — fully typed
def verify_token(token: str | None) -> None: ...
def require_auth(request: Request, credentials: HTTPAuthorizationCredentials = ...) -> None: ...
def get_client_id(request: Request, credentials: ..., client_id: str | None = ...) -> str: ...

# manager.py — fully typed
async def handle_connection(self, websocket: WebSocket, client_id: str, token: str | None, bot_manager) -> None: ...
```

One gap: `bot_manager` parameter in `handle_connection` and `_receive_loop` is typed as bare `bot_manager` (no type annotation) — it should be `BotManager` from the bot package:

```python
# manager.py:96 — current
async def handle_connection(self, websocket: WebSocket, client_id: str, token: str | None, bot_manager) -> None:

# Should be:
from sonarft_manager import BotManager  # type: ignore[import]
async def handle_connection(self, websocket: WebSocket, client_id: str, token: str | None, bot_manager: BotManager) -> None:
```

### 3.2 Bot Package — Type Coverage

The bot package has partial type coverage. Public methods in newer modules (`sonarft_execution.py`, `sonarft_search.py`) are well-typed. Older modules (`sonarft_indicators.py`, `sonarft_prices.py`) have gaps:

```python
# sonarft_indicators.py — missing return types on several methods
async def get_rsi(self, exchange, base, quote, moving_average_period=14, timeframe='1m'):
    # No type annotations on parameters or return type

# Should be:
async def get_rsi(self, exchange: str, base: str, quote: str,
                  moving_average_period: int = 14, timeframe: str = '1m') -> float | None:
```

### 3.3 `mypy` Configuration

Both packages have `mypy` configured in `pyproject.toml` with `ignore_missing_imports = true`. The API's `mypy` targets Python 3.11; the bot targets 3.10. Neither runs `mypy` in CI. Running `mypy src/` on the API would likely pass cleanly given the type coverage.

---

## 4. Docstrings & Documentation

### 4.1 Module-Level Docstrings

| Module | Has Docstring? | Quality |
|---|---|---|
| `src/main.py` | ✅ | One-liner: `"SonarFT API — FastAPI application factory."` |
| `src/core/config.py` | ✅ | Describes purpose |
| `src/core/security.py` | ✅ | Describes auth modes |
| `src/services/bot_service.py` | ✅ | Describes role |
| `src/websocket/manager.py` | ✅ | Describes role |
| `sonarft_bot.py` | ✅ | `"SonarFT Bot Control"` |
| `sonarft_execution.py` | ✅ | `"SonarFT Execution Module"` |
| `sonarft_helpers.py` | ✅ | Detailed description with SQLite note |

All modules have docstrings. ✅

### 4.2 Method-Level Docstrings

| Package | Coverage | Notes |
|---|---|---|
| API — endpoint handlers | ⚠️ One-liners only | `"List all bot IDs for a client."` — sufficient for OpenAPI |
| API — service methods | ⚠️ Sparse | `BotService.run_bot` has no docstring |
| API — `WebSocketManager` methods | ⚠️ Sparse | `_receive_loop`, `_send_loop` have no docstrings |
| Bot — `SonarftBot` methods | ✅ Good | `create_bot`, `run_bot`, `stop_bot` all documented |
| Bot — `SonarftExecution` methods | ✅ Good | `execute_trade`, `monitor_order` well documented |
| Bot — `SonarftHelpers` methods | ✅ Good | All public methods documented |

### 4.3 Docstring Format

No consistent docstring format (Google, NumPy, reStructuredText) is enforced. Most docstrings are plain prose without parameter/return documentation. For a public API, Google-style docstrings would improve IDE tooling and documentation generation.

---

## 5. Import Organisation

### 5.1 API Package

Imports follow the standard order (stdlib → third-party → local) with `from __future__ import annotations` at the top. `ruff`'s `I` ruleset enforces import sorting. ✅

One pattern worth noting — `main.py` defers bot package imports to the lifespan handler to avoid circular imports and allow graceful startup failure:

```python
# main.py:_lifespan — lazy import
from .services.bot_service import BotService
```

This is correct but means the import is not visible at the top of the file, which can confuse static analysis tools. ✅ (intentional trade-off)

### 5.2 Bot Package

Bot modules import from each other at the top level (no lazy imports). Since the bot package is a flat module structure (no sub-packages), circular imports are not a risk. ✅

### 5.3 No Star Imports

No `from module import *` found in either package. ✅

### 5.4 Unused Imports

`aiofiles` is in `packages/api/requirements.txt` but not imported anywhere in the API source. It may be a leftover from an earlier implementation.

---

## 6. Code Complexity

### 6.1 Long Methods — API Package

| Method | File | Lines | Issue |
|---|---|---|---|
| `create_app()` | `main.py` | ~80 | Mixes factory, middleware, logging setup, WS endpoint |
| `_lifespan()` | `main.py` | ~25 | Acceptable |
| `_receive_loop()` | `manager.py` | ~70 | Long but each branch is simple |
| `handle_connection()` | `manager.py` | ~30 | Acceptable |

`create_app()` is the most complex function in the API package. It handles:
1. FastAPI instance creation
2. Rate limiting setup
3. Middleware registration (4 middlewares)
4. Exception handler registration (3 handlers)
5. Router registration (5 routers)
6. WebSocket endpoint definition (inline)

The WebSocket endpoint definition inside `create_app()` is the main complexity driver — moving it to a router would reduce `create_app()` to a clean factory function.

### 6.2 Long Methods — Bot Package

| Method | File | Lines | Issue |
|---|---|---|---|
| `create_bot()` | `sonarft_bot.py` | ~100 | Config loading + module init + exchange setup |
| `execute_long_trade()` | `sonarft_execution.py` | ~80 | Two-leg execution with partial fill handling |
| `execute_short_trade()` | `sonarft_execution.py` | ~75 | Mirror of `execute_long_trade` |
| `load_configurations()` | `sonarft_bot.py` | ~60 | Loads 6 config sections |
| `apply_parameters()` | `sonarft_bot.py` | ~55 | Hot-reload with rollback |
| `monitor_order()` | `sonarft_execution.py` | ~50 | Order monitoring loop |

`execute_long_trade` and `execute_short_trade` are near-mirrors of each other (~80 lines each). The shared logic (balance check → first leg → partial fill handling → second leg → position tracking) could be extracted into a shared `_execute_two_leg_trade(buy_first: bool, ...)` method.

### 6.3 Cyclomatic Complexity Hotspots

| Method | Estimated Complexity | Notes |
|---|---|---|
| `_determine_position()` | ~8 | Multiple direction/RSI/StochRSI branches |
| `_receive_loop()` | ~10 | 5 command branches + validation |
| `weighted_adjust_prices()` | ~12 | Market direction × trend × RSI × StochRSI |
| `execute_long_trade()` | ~8 | Partial fill + cancel + imbalance branches |

`weighted_adjust_prices` in `sonarft_prices.py` is the most complex method in the codebase — it combines 6 market signals into a price adjustment. This is inherently complex domain logic, not a code quality issue.

---

## 7. Code Duplication

### 7.1 API Package — Canonical vs Legacy Duplication

The most significant duplication is the parallel endpoint implementations in `clients.py` and `bots.py`/`config.py` (identified in Prompts 01 and 02). Each bot operation is implemented twice with identical service calls:

```python
# clients.py:run_bot (canonical)
async def run_bot(request, client_id, botid, _, service) -> MessageResponse:
    try:
        await service.run_bot(botid, client_id)
        return MessageResponse(message=f"Bot {botid} started.")
    except BotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

# bots.py:run_bot (legacy) — identical body
async def run_bot(request, botid, client_id, service) -> MessageResponse:
    try:
        await service.run_bot(botid, client_id)
        return MessageResponse(message=f"Bot {botid} started.")
    except BotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
```

The only difference is parameter order and the `_: Auth` dependency. This duplication is intentional (migration strategy) but should be tracked for removal.

### 7.2 Bot Package — `execute_long_trade` / `execute_short_trade`

These two methods share ~70% of their logic. The structural difference is which leg executes first (buy vs sell). A shared helper would eliminate ~60 lines:

```python
# Current: two ~80-line methods
async def execute_long_trade(self, ...): ...   # buy first
async def execute_short_trade(self, ...): ...  # sell first

# Refactored: one shared method
async def _execute_two_leg_trade(
    self, first_exchange, second_exchange, base, quote,
    first_amount, second_amount, first_price, second_price,
    first_side: str, second_side: str
) -> tuple[...]: ...
```

### 7.3 `_BOTID_RE` Pattern Duplicated

The botid validation regex `^[a-zA-Z0-9_-]{1,64}$` appears in three places:
- `clients.py:33` — `Path(pattern=...)`
- `bots.py:22` — `Path(pattern=...)`
- `manager.py:18` — `re.compile(...)`

A single constant in `core/config.py` or `models/schemas.py` would be the single source of truth (identified in Prompt 02 R3).

### 7.4 `_client_id` Regex Duplicated

The client_id validation regex `^[a-zA-Z0-9_-]{1,64}$` appears in:
- `clients.py:32`
- `bots.py:22`
- `config_service.py:20`

Same fix as above.

---

## 8. Design Patterns & Best Practices

### 8.1 SOLID Assessment

| Principle | API | Bot | Notes |
|---|---|---|---|
| **S** — Single Responsibility | ⚠️ | ⚠️ | `main.py` and `create_bot()` do too much |
| **O** — Open/Closed | ✅ | ✅ | New endpoints/modules added without modifying existing |
| **L** — Liskov Substitution | ✅ | ✅ | No inheritance hierarchies to violate |
| **I** — Interface Segregation | ✅ | ✅ | Services expose only what endpoints need |
| **D** — Dependency Inversion | ✅ | ✅ | DI via constructor and FastAPI `Depends` throughout |

### 8.2 Dependency Injection

Both packages use constructor injection consistently. The API uses FastAPI's `Depends` system for endpoint-level DI. The bot uses constructor injection for all module wiring in `SonarftBot.initialize_modules()`. ✅

### 8.3 Service Layer Pattern

The API correctly separates concerns:
- Endpoints: HTTP translation only
- Services: business logic
- Bot engine: domain logic

The one violation is `BotService` and `ConfigService` raising `HTTPException` directly (identified in Prompt 06 E1/E2). ⚠️

### 8.4 Factory Pattern

`create_app()` in `main.py` is a clean application factory. The lifespan handler correctly initialises services before the server accepts requests. ✅

### 8.5 Strategy Pattern

`SonarftBot.strategy` (`"arbitrage"` or `"market_making"`) controls price adjustment behaviour in `SonarftPrices`. This is an implicit strategy pattern — the strategy string is checked in multiple places rather than using a proper Strategy class. For two strategies this is acceptable; for more it would warrant a formal Strategy pattern.

---

## 9. Constants & Magic Numbers

### 9.1 API Package

| Magic Value | Location | Should Be |
|---|---|---|
| `"__ticket_verified__"` | `main.py:207`, `security.py:58` | Named constant `_TICKET_VERIFIED_SENTINEL` |
| `30` (ticket TTL) | `ws_ticket.py:30`, `tickets.py:8` | `_TICKET_TTL_SECONDS = 30` (already defined in `tickets.py`) — `ws_ticket.py` hardcodes it again |
| `1000` (queue max size) | `manager.py:17` | `_WS_QUEUE_MAX_SIZE = 1000` ✅ already a constant |
| `30.0` (keepalive interval) | `manager.py:18` | `_WS_KEEPALIVE_INTERVAL = 30.0` ✅ already a constant |
| `10 * 1024 * 1024` (log file size) | `main.py:63` | `_LOG_MAX_BYTES = 10 * 1024 * 1024` |
| `7` (log backup count) | `main.py:65` | `_LOG_BACKUP_COUNT = 7` |
| `10_000` (ticket store cap) | `tickets.py:9` | `_MAX_TICKETS = 10_000` ✅ already a constant |

### 9.2 Bot Package

| Magic Value | Location | Should Be |
|---|---|---|
| `300` (order monitor timeout) | `sonarft_execution.py:monitor_order` | `_ORDER_MONITOR_TIMEOUT_SECONDS = 300` |
| `120` (price monitor timeout) | `sonarft_execution.py:monitor_price` | `_PRICE_MONITOR_TIMEOUT_SECONDS = 120` |
| `3` (cancel retry count) | `sonarft_execution.py:_cancel_order_with_retry` | `_CANCEL_MAX_RETRIES = 3` |
| `10_000` (history retention) | `sonarft_helpers.py:purge_history` | `_HISTORY_KEEP_LAST = 10_000` |
| `50 * 1024 * 1024` (metrics log size) | `main.py:82` | `_METRICS_MAX_BYTES = 50 * 1024 * 1024` |

Most critical constants are already named (e.g. `RSI_OVERBOUGHT = 70`, `_WS_QUEUE_MAX_SIZE = 1000`). The remaining magic numbers are low-risk but should be named for clarity.

---

## 10. Error Handling Patterns

### 10.1 API Package — Consistency

The API uses a consistent fail-safe pattern in endpoint handlers:

```python
try:
    await service.run_bot(botid, client_id)
    return MessageResponse(message=f"Bot {botid} started.")
except BotNotFoundError as exc:
    raise HTTPException(status_code=404, detail=str(exc)) from exc
```

Exception types are specific (`BotNotFoundError`, `BotLimitExceededError`). The generic `Exception` handler is the last resort. ✅

### 10.2 Bot Package — Broad `except Exception`

The bot uses broad `except Exception` throughout as a fail-safe pattern:

```python
try:
    ...
except Exception as e:
    self.logger.error(f"Error get_rsi: {str(e)}")
    return None
```

This is intentional — the bot must not crash on any single indicator failure. However, using `logger.error` instead of `logger.exception` loses the stack trace (identified in Prompt 06 E5). The fix is minimal:

```python
except Exception:
    self.logger.exception("Error get_rsi")
    return None
```

### 10.3 `B904` Ruff Ignore

Both `pyproject.toml` files ignore `B904` (raise-without-from). This suppresses warnings about missing exception chaining. The `BotService` issue (`raise HTTPException(...)` without `from exc`) would be caught by `B904` if it were enabled. Removing this ignore would surface real issues.

---

## 11. Async / Await Best Practices

### 11.1 No Blocking Calls in Async Context

A full audit of all `async def` methods confirms no blocking calls:

| Blocking Operation | Async Wrapper Used |
|---|---|
| File read/write | `asyncio.to_thread(_read_json, ...)` ✅ |
| SQLite queries | `asyncio.to_thread(_db_query, ...)` ✅ |
| Webhook HTTP call | `asyncio.to_thread(urllib.request.urlopen, ...)` ✅ |
| Exchange API calls | `await api_manager.call_api_method(...)` ✅ |
| pandas-ta calculations | Called inside `asyncio.to_thread` via OHLCV fetch ✅ |

### 11.2 `asyncio.gather` Usage

`asyncio.gather` is used correctly for parallel operations:
- `SonarftSearch.search_trades` — parallel symbol processing ✅
- `TradeValidator` — parallel buy/sell liquidity checks ✅
- `WebSocketManager.handle_connection` — concurrent send/receive loops ✅
- `SonarftBot._reconcile_open_orders` — parallel exchange/symbol queries ✅

### 11.3 `asyncio.create_task` Tracking

Background tasks created by `asyncio.create_task` are tracked in lists and cancelled on cleanup:
- `WebSocketManager._tasks` — per-client task list, cancelled in `_cleanup` ✅
- `SonarftBot._fee_refresh_task`, `_db_backup_task` — cancelled in `stop_bot` ✅
- `TradeExecutor` tasks — managed with `monitor_task` and shutdown ✅

### 11.4 `asyncio.shield` Usage

`asyncio.shield` is used correctly in `run_bot` to prevent the stop event wait from being cancelled:

```python
await asyncio.wait_for(
    asyncio.shield(self._stop_event.wait()), timeout=backoff
)
```

This allows the backoff sleep to be interrupted by the stop event without cancelling the outer task. ✅

---

## 12. Context Managers & Resource Management

### 12.1 SQLite Connections

All SQLite connections use `with sqlite3.connect(...) as conn:` — the context manager commits on success and rolls back on exception. ✅

### 12.2 File Operations

`ConfigService._write_json` uses `tempfile.NamedTemporaryFile` as a context manager for atomic writes. ✅

`SonarftBot._write_botid_file` uses `with open(path, "w") as f:` — correct. ✅

### 12.3 Exchange Connections

ccxt/ccxtpro exchange instances are closed in `SonarftBot.stop_bot()`:

```python
for exchange in self.api_manager.exchanges_instances:
    try:
        await self.api_manager.close_exchange(exchange.id)
    except Exception as e:
        self.logger.warning(f"Error closing exchange {exchange.id}: {e}")
```

The `try/except` prevents a failed close from blocking the shutdown sequence. ✅

### 12.4 `asyncio.Lock` as Context Manager

All `asyncio.Lock` usage correctly uses `async with self._lock:` — never manually acquired/released. ✅

---

## 13. Testing & Testability

### 13.1 Dependency Injection Enables Testing

Both packages use constructor injection, making unit testing straightforward — all dependencies can be replaced with mocks at construction time. The API's `get_bot_service_from_state` / `get_config_service_from_state` pattern allows `app.state` injection in tests without modifying production code. ✅

### 13.2 Hard-Coded Dependencies

| Hard-Coded Dependency | Location | Testability Impact |
|---|---|---|
| `_BOT_LOGGER_NAME = "src.services.bot_service"` | `manager.py:30` | Low — can be patched |
| `_DB_PATH` in `SonarftHelpers` | `sonarft_helpers.py:47` | Medium — class-level, requires monkeypatching |
| `_bot_path(...)` in `sonarft_search.py` | `sonarft_search.py:14` | Medium — filesystem path |

`SonarftHelpers._DB_PATH` is a class-level attribute — it can be overridden in tests via `SonarftHelpers._DB_PATH = str(tmp_path / "test.db")`. This is workable but fragile. A constructor parameter would be cleaner.

### 13.3 Pure Functions

`SonarftMath.calculate_trade` and `models.percentage_difference` are pure functions with no side effects — trivially testable. ✅

---

## 14. Comments & Clarity

### 14.1 Comment Quality

Comments in both packages are generally high quality — they explain *why*, not *what*:

```python
# sonarft_manager.py — explains the design decision
# stop_bot() performs network I/O (cancel tasks, close connections)
# — called outside the lock so other operations are not blocked

# sonarft_execution.py — explains the invariant
# Per-exchange asyncio.Lock to prevent concurrent balance race conditions.
# Two concurrent tasks checking balance for the same exchange could both
# pass the check but only one can actually fill.

# main.py — explains the sentinel pattern
# Ticket is valid — identity already verified; pass None so
# verify_token in handle_connection runs in dev-mode pass-through
```

### 14.2 TODO / FIXME Comments

No `TODO` or `FIXME` comments found in either package. ✅

### 14.3 Commented-Out Code

No commented-out code blocks found. ✅

### 14.4 Inline Comments on Complex Logic

`sonarft_execution.py` uses inline comments to label partial fill scenarios:

```python
# Cancel remaining buy amount if partially filled (B2)
# Second leg partially filled — imbalanced position (B1)
```

The `(B1)`, `(B2)` labels reference internal design documents — useful for maintainers but opaque to new contributors. Expanding these to full descriptions would improve clarity.

---

## 15. Dependencies & Imports

### 15.1 API Package Dependencies

```
fastapi==0.135.3          ✅ Current
uvicorn[standard]==0.44.0 ✅ Current
pydantic>=2.0.0           ⚠️ Unpinned
pydantic-settings>=2.0.0  ⚠️ Unpinned
PyJWT[crypto]>=2.7.0      ⚠️ Unpinned
python-dotenv>=1.2.2      ⚠️ Unpinned
orjson                    ⚠️ Unpinned + unused
aiofiles                  ⚠️ Unpinned + unused
slowapi>=0.1.9            ⚠️ Unpinned
```

`orjson` and `aiofiles` are declared but unused in the API source. They should either be used (see Prompt 08 R3/R4) or removed.

### 15.2 Bot Package Dependencies

```
pandas==3.0.2             ✅ Pinned
pandas-ta==0.4.71b0       ✅ Pinned
simple-websocket==1.1.0   ✅ Pinned
ccxt==4.5.48              ✅ Pinned
ccxt[pro]==4.5.48         ✅ Pinned
```

The bot package pins all dependencies exactly — good for reproducibility. ✅

### 15.3 Dependency Minimisation

The API's `aiofiles` dependency is unused — it can be removed. `orjson` is declared but unused — it should be used (Prompt 08 R3) or removed.

---

## 16. Concerns & Recommendations

### 16.1 Concerns

| # | Concern | Severity | Location |
|---|---|---|---|
| Q1 | **`Makefile` uses `pylint` but packages configure `ruff`** — linting tooling inconsistency | Medium | `Makefile:lint-bot`, `lint-api` |
| Q2 | **`B904` ruff ignore suppresses exception chaining warnings** — real issues not caught by linter | Medium | Both `pyproject.toml` files |
| Q3 | **`execute_long_trade` / `execute_short_trade` are near-mirrors** — ~60 lines of duplicated logic | Medium | `sonarft_execution.py` |
| Q4 | **`create_app()` violates SRP** — factory + middleware + logging + WS endpoint in one function | Low | `main.py` |
| Q5 | **`bot_manager` parameter untyped in `WebSocketManager`** — breaks static analysis | Low | `manager.py:96` |
| Q6 | **`"__ticket_verified__"` string sentinel not a named constant** | Low | `main.py:207`, `security.py:58` |
| Q7 | **`ws_ticket.py` hardcodes TTL `30` instead of using `_TICKET_TTL_SECONDS`** | Low | `ws_ticket.py:30` |
| Q8 | **`aiofiles` declared but unused** | Low | `requirements.txt` |
| Q9 | **No shared root-level linting config** — identical `ruff` config duplicated in both packages | Low | Both `pyproject.toml` files |
| Q10 | **Bot methods use `logger.error(str(e))` instead of `logger.exception()`** — stack traces lost | Low | Multiple bot modules |

---

### 16.2 Recommendations (Prioritised)

#### P1 — Quick wins

**R1: Fix `Makefile` to use `ruff` instead of `pylint`**

```makefile
lint-bot: ## Lint bot package
    cd packages/bot && ruff check .

lint-api: ## Lint API package
    cd packages/api && ruff check src/ tests/
```

**R2: Remove `B904` from ruff ignore list and fix the violations**

```toml
# Both pyproject.toml files — remove from ignore:
# "B904",   # raise-without-from
```

Then fix the two known violations:
```python
# bot_service.py:40
raise HTTPException(status_code=500, detail="Bot creation failed") from exc
```

**R3: Extract `_BOTID_PATTERN` and `_CLIENT_ID_PATTERN` constants**

```python
# src/core/config.py — add
BOTID_PATTERN = r"^[a-zA-Z0-9_-]{1,64}$"
CLIENT_ID_PATTERN = r"^[a-zA-Z0-9_-]{1,64}$"

# clients.py, bots.py — use
from ..core.config import BOTID_PATTERN, CLIENT_ID_PATTERN
BotId = Annotated[str, Path(pattern=BOTID_PATTERN)]
ClientId = Annotated[str, Path(pattern=CLIENT_ID_PATTERN)]

# config_service.py — use
_SAFE_CLIENT_ID = re.compile(CLIENT_ID_PATTERN)
```

**R4: Name the ticket sentinel constant**

```python
# src/core/security.py — add at module level
_TICKET_VERIFIED_SENTINEL = "__ticket_verified__"

# Replace all occurrences:
if token == _TICKET_VERIFIED_SENTINEL:
    return
```

**R5: Remove unused `aiofiles` from `requirements.txt`**

```
# packages/api/requirements.txt — remove:
# aiofiles
```

Either use it (for async file operations in `ConfigService`) or remove it.

**R6: Use `logger.exception()` in bot error handlers**

```python
# sonarft_execution.py and other bot modules — replace
self.logger.error(f"Error executing trade: {e}")
# with
self.logger.exception("Error executing trade")
```

---

#### P2 — Medium effort

**R7: Extract shared `_execute_two_leg_trade` in `SonarftExecution`**

```python
async def _execute_two_leg_trade(
    self, botid,
    first_exchange: str, second_exchange: str,
    base: str, quote: str,
    first_amount: float, second_amount: float,
    first_price: float, second_price: float,
    first_side: str, second_side: str,
) -> tuple[Any, Any]:
    """Execute a two-leg trade. first_side executes first."""
    # Shared logic for both LONG and SHORT
    ...

async def execute_long_trade(self, ...):
    return await self._execute_two_leg_trade(..., first_side="buy", second_side="sell")

async def execute_short_trade(self, ...):
    return await self._execute_two_leg_trade(..., first_side="sell", second_side="buy")
```

**R8: Extract WebSocket endpoint from `create_app()`**

```python
# src/api/v1/endpoints/websocket.py
from fastapi import APIRouter, WebSocket

router = APIRouter()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, ...):
    ...

# main.py — register like other routers
app.include_router(ws_router, prefix=prefix)
```

**R9: Add type annotation to `bot_manager` parameter**

```python
# manager.py — add import
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sonarft_manager import BotManager  # type: ignore[import]

async def handle_connection(
    self, websocket: WebSocket, client_id: str,
    token: str | None, bot_manager: "BotManager"
) -> None:
```

---

#### P3 — Longer term

**R10: Create a shared root-level `ruff` config**

```toml
# sonarft-monorepo/pyproject.toml (new root-level file)
[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B"]
ignore = ["E501", "B008", "UP007"]
# Remove B904 — enforce exception chaining

[tool.ruff.format]
quote-style = "double"
```

Both packages inherit from this, eliminating duplication.

**R11: Run `mypy` in CI for the API package**

```yaml
# .github/workflows/ci.yml — add to test-api job
- name: Type check
  run: mypy src/ --ignore-missing-imports
```

The API package is well-typed enough that `mypy` should pass with minimal fixes.

---

## Python Best Practices Checklist

### API Package
- [x] PEP 8 compliance via `ruff`
- [x] Type hints on all public methods
- [x] `from __future__ import annotations` for deferred evaluation
- [x] No blocking calls in async handlers
- [x] `asyncio.to_thread` for all I/O
- [x] Context managers for all resources
- [x] Dependency injection throughout
- [ ] Fix `Makefile` to use `ruff` instead of `pylint`
- [ ] Remove `B904` from ruff ignore
- [ ] Extract `BOTID_PATTERN` / `CLIENT_ID_PATTERN` constants
- [ ] Name `__ticket_verified__` sentinel
- [ ] Remove unused `aiofiles` dependency
- [ ] Add `bot_manager` type annotation in `WebSocketManager`
- [ ] Extract WS endpoint from `create_app()`

### Bot Package
- [x] Consistent `snake_case` naming
- [x] Named constants for RSI thresholds, OHLCV indices
- [x] `asyncio.to_thread` for all blocking I/O
- [x] `asyncio.Lock` for shared state
- [x] `asyncio.shield` for interruptible waits
- [x] Exponential backoff retry on order cancellation
- [x] Circuit breaker in `run_bot`
- [ ] Use `logger.exception()` instead of `logger.error(str(e))`
- [ ] Extract `_execute_two_leg_trade` shared method
- [ ] Add type hints to `sonarft_indicators.py` methods
- [ ] Name magic numbers (`300`, `120`, `3`) as constants

---

## Tooling Recommendations

| Tool | Purpose | Status | Recommendation |
|---|---|---|---|
| `ruff` | Linting + formatting | ✅ Configured | Fix `Makefile` to use it |
| `mypy` | Static type checking | ⚠️ Configured, not in CI | Add to CI for API package |
| `pytest-cov` | Coverage measurement | ⚠️ Installed, not invoked | Add `--cov` to pytest invocation |
| `pip-audit` | Dependency CVE scanning | ✅ In bot CI | Add to API CI |
| `black` | Code formatting | ❌ Not used | `ruff format` covers this |
| `pre-commit` | Git hook enforcement | ❌ Not configured | Consider adding `ruff check` + `ruff format` hooks |

---

## Related Prompts

- [Prompt 01: Architecture Structure](../architecture/01-api-architecture.md) — Architecture quality
- [Prompt 09: Testing & Quality](../testing/09-testing-quality.md) — Test coverage
- [Prompt 11: Final Consolidation](../consolidation/11-executive-summary.md) — Overall summary

---

_Part of the SonarFT API Code Review Prompt Suite — Prompt 10_
