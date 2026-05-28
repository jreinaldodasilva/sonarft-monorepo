# Code Quality & Python Best Practices Review

**Prompt ID:** 10-API-QUALITY  
**Package:** `packages/api` + `packages/bot`  
**Output:** `docs/code-quality/10-code-quality-python.md`  
**Reviewed:** July 2025  
**Status:** Complete

---

## Executive Summary

The SonarFT API codebase is clean, idiomatic Python 3.11 with consistent style throughout. Ruff is configured at the monorepo root (`pyproject.toml`) and enforces `E`, `F`, `W`, `I`, `UP`, `B` rules across both packages — CI blocks on any lint error. Type hints are present on all public functions and most private helpers. The code is self-documenting with minimal comments, and the few docstrings that exist are accurate. The most significant quality concern is **code duplication between `bots.py` and `clients.py`**: 14 endpoint handlers are implemented twice with near-identical bodies, doubling the maintenance surface. A secondary concern is **inconsistent exception handling specificity** — several `except Exception` catch-alls in service and WebSocket code swallow unexpected errors silently. The bot package has one notable quality issue: `sonarft_manager.py` references `BotRunError` in a `try/except` block but the exception is defined *after* the method that catches it, and the docstring notes it is "never raised" — the `except` clause is dead code that should be removed.

---

## Code Quality Scorecard

| Dimension | Score | Notes |
|---|---|---|
| Style & formatting | ✅ Excellent | Ruff enforced in CI; consistent double-quote strings, 4-space indent |
| Naming conventions | ✅ Excellent | PascalCase classes, snake_case functions, `_private` prefix used correctly |
| Type hints | ✅ Good | All public APIs typed; a few private helpers missing return types |
| Docstrings | ⚠️ Partial | Module-level docstrings present; most functions rely on self-documenting names |
| Import organisation | ✅ Excellent | `isort` via ruff `I` rules; stdlib → third-party → local ordering consistent |
| Code complexity | ✅ Good | Most functions are short; `_receive_loop` and `main.py` are the longest |
| Code duplication | ⚠️ Medium | `bots.py` / `clients.py` duplication; test helper duplication |
| Design patterns | ✅ Good | Service layer, DI via `Depends`, lifespan pattern all correctly applied |
| Constants | ✅ Good | Magic numbers extracted to named constants; a few inline literals remain |
| Error handling | ⚠️ Partial | Some `except Exception` catch-alls; dead `except BotRunError` in bot |
| Async correctness | ✅ Good | All blocking I/O offloaded except `create_bot()` (Prompt 08 H1) |
| Resource management | ✅ Excellent | Context managers used throughout; cleanup in `finally` blocks |
| Testability | ✅ Good | DI via `app.state`; `lru_cache` fallbacks for test compatibility |

---

## 1. Code Style & Formatting

### Ruff configuration (root `pyproject.toml`)

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B"]
ignore = [
    "E501",   # line too long — handled by formatter
    "B008",   # do not perform function calls in default arguments (FastAPI Depends)
    "UP007",  # use X | Y for union types — keep Optional for clarity
]
```

- `E`/`W` — pycodestyle errors and warnings
- `F` — pyflakes (unused imports, undefined names)
- `I` — isort (import ordering)
- `UP` — pyupgrade (modern Python syntax)
- `B` — flake8-bugbear (common bugs and design issues)

`E501` (line length) is ignored — the formatter handles wrapping. `B008` is correctly ignored for FastAPI's `Depends()` pattern. `UP007` is ignored to allow `Optional[X]` — though the codebase actually uses `X | None` syntax consistently (Python 3.10+ union syntax), making this ignore redundant.

**No style violations were found** in the reviewed source files. The codebase is clean against the configured ruleset.

### Formatting consistency

- Double-quoted strings throughout (enforced by `ruff.format.quote-style = "double"`)
- 4-space indentation
- Blank lines between top-level definitions
- `from __future__ import annotations` used in files that need forward references

---

## 2. Naming Conventions

All naming conventions are followed correctly:

| Convention | Examples | Assessment |
|---|---|---|
| PascalCase classes | `BotService`, `ConfigService`, `WebSocketManager`, `TicketStore` | ✅ |
| snake_case functions | `get_bot_service_from_state`, `_validate_client_id`, `_write_json` | ✅ |
| `_private` prefix | `_logger`, `_bearer`, `_jwks_client_holder`, `_ws_manager` | ✅ |
| UPPER_CASE constants | `ID_PATTERN`, `_TICKET_TTL_SECONDS`, `_MAX_TICKETS`, `_WS_QUEUE_MAX_SIZE` | ✅ |
| Descriptive names | `get_bot_service_from_state` vs `get_service` | ✅ |

One minor inconsistency: `_SUNSET_DATE` in `bots.py` and `config.py` is a module-level constant but uses a `_` prefix suggesting it is private to the module — which is correct, but the value is duplicated (noted in Prompt 02 M6).

The `_TICKET_VERIFIED_SENTINEL` constant in `security.py` is well-named — the name makes its purpose clear without needing a comment.

---

## 3. Type Hints & Type Safety

### API package (`src/`)

Type hint coverage is high. All public endpoint functions, service methods, and core utilities are fully typed. Return types are specified on all public functions.

| File | Coverage | Notes |
|---|---|---|
| `core/config.py` | ✅ 100% | `Settings`, `get_settings()`, `ID_PATTERN` all typed |
| `core/errors.py` | ✅ 100% | All handlers typed `async def ... -> JSONResponse` |
| `core/security.py` | ✅ 95% | `_client_ip` return type `str` correct; `_decode_jwt` returns `dict` (could be `dict[str, Any]`) |
| `core/context.py` | ✅ 100% | `ContextVar[str]` typed |
| `services/bot_service.py` | ✅ 90% | `get_orders`/`get_trades` return `list` (unparameterised) |
| `services/config_service.py` | ✅ 95% | `_cache` typed as `dict[str, tuple[float, dict]]` |
| `models/schemas.py` | ✅ 100% | All Pydantic models fully typed |
| `websocket/manager.py` | ✅ 85% | `_tasks` typed `dict[str, list[asyncio.Task]]`; `push_event` `event: dict` unparameterised |
| `websocket/tickets.py` | ✅ 100% | `_tickets: dict[str, tuple[str, float]]` typed |
| `main.py` | ✅ 80% | Middleware `dispatch` methods use `call_next` without annotation |

### Unparameterised `list` and `dict` return types

Several methods return bare `list` or `dict` without type parameters:

```python
# bot_service.py:72 — should be list[dict[str, Any]]
async def get_orders(self, ...) -> list:

# websocket/manager.py:97 — should be dict[str, Any]
async def push_event(self, client_id: str, event: dict) -> None:
```

These are minor — mypy with `--strict` would flag them, but the current `mypy` config uses `warn_return_any = false`.

### `TYPE_CHECKING` guard

`websocket/manager.py` correctly uses `TYPE_CHECKING` to avoid a circular import:

```python
if TYPE_CHECKING:
    from sonarft_manager import BotManager
```

This is the correct pattern for type-only imports.

---

## 4. Docstrings & Documentation

### Module-level docstrings

All API source files have module-level docstrings:

```python
"""
SonarFT API — FastAPI application factory.
"""
```

These are brief but accurate. They describe the module's purpose without over-explaining.

### Class and function docstrings

| Component | Docstring quality | Notes |
|---|---|---|
| `BotService` | ✅ Good | Explains lazy import rationale |
| `ConfigService` | ❌ Missing | No class-level docstring |
| `WebSocketManager` | ✅ Good | Explains decoupling from bot manager |
| `WsLogHandler` | ✅ Good | Explains `put_nowait` choice |
| `TicketStore` | ✅ Good | Documents thread-safety model |
| `RequestIdMiddleware` | ✅ Good | Explains ContextVar usage |
| `SecurityHeadersMiddleware` | ✅ Good | |
| `_lifespan` | ✅ Good | Explains why services are on `app.state` |
| Endpoint functions | ⚠️ Minimal | One-line docstrings only; no parameter docs |
| `_validate_client_id` | ✅ Good | |
| `_client_path` | ✅ Good | Documents path traversal defence |

The WebSocket endpoint (`websocket.py`) has an unusually detailed docstring listing all events and commands — this is the most complete documentation in the codebase and is valuable, though it is not rendered in Swagger UI (noted in Prompt 02 L3).

### Docstring format

No consistent format (Google, NumPy, reStructuredText) is enforced. Most docstrings are plain prose. This is acceptable for a codebase of this size but would benefit from a consistent format if the team grows.

---

## 5. Import Organisation

Imports are consistently organised in the correct order (stdlib → third-party → local) across all files, enforced by ruff's `I` rules. No star imports (`from x import *`) are present. No unused imports were found.

One pattern worth noting: `main.py` uses deferred imports inside `_lifespan` to avoid circular imports:

```python
# main.py:_lifespan
from .services.bot_service import BotService
from .services.config_service import ConfigService
```

This is correct — importing at module level would cause circular import issues since `main.py` is the application root.

---

## 6. Code Complexity

### Longest functions

| Function | File | Lines | Assessment |
|---|---|---|---|
| `_receive_loop` | `websocket/manager.py` | ~80 | ⚠️ Long but linear — each branch handles one command |
| `create_app` | `main.py` | ~60 | ✅ Acceptable — factory function with sequential setup |
| `_lifespan` | `main.py` | ~30 | ✅ |
| `get_client_id` | `core/security.py` | ~35 | ✅ Two clear branches (Netlify vs static) |
| `load_bot_config` | `bot_config.py` | ~70 | ⚠️ Long but each section loads one config file |
| `handle_connection` | `websocket/manager.py` | ~35 | ✅ |

`_receive_loop` is the most complex function in the API package. It handles 5 command types with identical validation patterns for each. The repetition is the main complexity driver — extracting a `_validate_botid(event, client_id)` helper would reduce it significantly.

### Cyclomatic complexity

No function has deeply nested conditionals (> 3 levels). The `_receive_loop` has 5 `elif` branches but each is flat. `get_client_id` has 2 branches with 2 sub-branches each — acceptable.

---

## 7. Code Duplication

### `bots.py` vs `clients.py` — 14 duplicate endpoint handlers

This is the most significant duplication in the codebase. Every bot lifecycle endpoint is implemented twice:

| Endpoint | `bots.py` | `clients.py` | Difference |
|---|---|---|---|
| List bots | `list_bots` | `list_bots` | `client_id` source (query vs path) |
| Create bot | `create_bot` | `create_bot` | Same + deprecation headers |
| Run bot | `run_bot` | `run_bot` | Same |
| Stop bot | `stop_bot` | `stop_bot` | Same |
| Remove bot | `remove_bot` | `remove_bot` | Same |
| Get orders | `get_orders` | `get_orders` | Same |
| Get trades | `get_trades` | `get_trades` | Same |

The handler bodies are identical — the only difference is how `client_id` is extracted (query param via `get_client_id` dependency vs path segment via `Path(pattern=ID_PATTERN)`).

### `config.py` vs `clients.py` — 4 duplicate config handlers

`GET/PUT /parameters` and `GET/PUT /indicators` are implemented in both `config.py` (legacy) and `clients.py` (canonical).

### `_deprecation_headers` defined twice

```python
# bots.py:21-24
def _deprecation_headers(response: Response) -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = _SUNSET_DATE

# config.py:17-20 — identical
def _deprecation_headers(response: Response) -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = _SUNSET_DATE
```

### `_SUNSET_DATE` defined twice

```python
# bots.py:21
_SUNSET_DATE = "Sun, 01 Jan 2026 00:00:00 GMT"

# config.py:14 — identical
_SUNSET_DATE = "Sun, 01 Jan 2026 00:00:00 GMT"
```

### Test helper duplication

`_trade_record()`, `_params_config()`, `_indicators_config()` defined in both `test_endpoints.py` and `test_clients.py` (noted in Prompt 09 M1).

---

## 8. Design Patterns & Best Practices

### SOLID assessment

| Principle | Status | Notes |
|---|---|---|
| Single Responsibility | ✅ Good | Each module has one clear purpose; `main.py` is the only multi-concern file (factory + logging setup) |
| Open/Closed | ✅ Good | New endpoints added by creating new router files; exception handlers registered without modifying existing handlers |
| Liskov Substitution | ✅ N/A | No inheritance hierarchies in the API package |
| Interface Segregation | ✅ Good | `BotService` and `ConfigService` expose only what endpoints need |
| Dependency Inversion | ✅ Good | Endpoints depend on `BotService`/`ConfigService` abstractions via `Depends()`; not on `BotManager` directly |

### Dependency injection

FastAPI's `Depends()` is used correctly throughout. The `Annotated` type alias pattern (`Auth = Annotated[None, Depends(require_auth)]`) reduces boilerplate and makes dependencies explicit in function signatures.

### `lru_cache` singleton pattern

`get_bot_service()` and `get_config_service()` use `@lru_cache` as fallback singletons for test compatibility. This is a pragmatic pattern but has the side effect that tests must call `cache_clear()` to reset state between test runs — documented in `conftest.py`.

---

## 9. Constants & Magic Numbers

### Well-extracted constants

```python
# core/config.py
ID_PATTERN: str = r"^[a-zA-Z0-9_-]{1,64}$"

# websocket/manager.py
_WS_QUEUE_MAX_SIZE = 1000
_WS_KEEPALIVE_INTERVAL = 30.0
_BOT_LOG_PREFIX = "sonarft"

# websocket/tickets.py
_TICKET_TTL_SECONDS = 30
_MAX_TICKETS = 10_000

# models/schemas.py
_MAX_CONFIG_DICT_SIZE = 50
```

### Remaining inline literals

| Value | Location | Recommendation |
|---|---|---|
| `"Sun, 01 Jan 2026 00:00:00 GMT"` | `bots.py:21`, `config.py:14` | Extract to `core/config.py` as `Settings.legacy_sunset_date` |
| `5` (max bots default) | `core/config.py:Settings.max_bots_per_client` | ✅ Already in Settings |
| `30` (ticket TTL) | `schemas.py:153`, `ws_ticket.py:30` | Consolidate to `tickets.py:TICKET_TTL_SECONDS` (Prompt 03 M4) |
| `1001` (WS close code) | `manager.py:122` | Extract as `_WS_CLOSE_REPLACED = 1001` |
| `1008` (WS policy violation) | `websocket.py:47`, `manager.py:113` | Extract as `_WS_CLOSE_POLICY = 1008` |
| `1011` (WS internal error) | `websocket.py:52` | Extract as `_WS_CLOSE_INTERNAL = 1011` |

---

## 10. Error Handling Specificity

### Broad `except Exception` catch-alls

Several locations catch `Exception` broadly:

```python
# main.py:_lifespan:196 — intentional: catches import errors
try:
    app.state.bot_service = BotService()
except Exception as exc:
    _logger.error("Failed to initialise BotService: %s", exc)
    app.state.bot_service = None
```
This is intentional and correct — startup failures should not crash the process.

```python
# websocket/manager.py:_handle_create:248
except Exception as exc:
    _logger.error("WS create_bot failed for client %s: %s", client_id, exc)
    await self._push_model(client_id, WsErrorEvent(...))
```
This is acceptable for WebSocket command handlers — any exception should be caught and reported to the client rather than crashing the connection. However, it swallows unexpected errors silently from the operator's perspective (only logged at ERROR, not re-raised).

```python
# bot_service.py:get_bot_service_from_state:103
except Exception:
    raise HTTPException(status_code=503, ...) from None
```
This is intentional — any failure to get the service should return 503.

```python
# config_service.py:_read_json_cached:79
except OSError:
    raise FileNotFoundError(path) from None
```
✅ Specific exception type — correct.

### Dead `except BotRunError` in bot package

```python
# sonarft_manager.py:run_bot:155
except BotRunError as error:  # noqa: F821 — kept for backward compat, never raised
    self.logger.exception(f"Bot run error: {error}")
    if botid:
        await self.remove_bot(botid)
```

`BotRunError` is defined at the bottom of the file and its docstring states it is "never raised internally". The `# noqa: F821` suppresses the "undefined name" warning. This is dead code that adds confusion. The `noqa` comment is a code smell — it suppresses a legitimate warning about a real problem.

---

## 11. Async/Await Best Practices

All async patterns are correct with one exception (Prompt 08 H1 — `create_bot()` blocking the event loop).

### Correct patterns observed

- `asyncio.to_thread()` used for all SQLite and file I/O
- `asyncio.gather()` for concurrent send/receive loops
- `asyncio.create_task()` for fire-and-forget WS command handlers
- `asyncio.wait_for()` with timeout for queue drain
- `asyncio.Lock()` for write serialisation
- `asyncio.Queue` with `put_nowait()` in sync logging handler (correct — `put_nowait` is the only safe call from a sync context)

### One missing `await` risk

`BotManager.run_bot()` in `sonarft_manager.py` references `BotRunError` which is never raised, but the `except` clause calls `await self.remove_bot(botid)` — this is correct async usage. No missing `await` keywords were found.

---

## 12. Context Managers & Resource Management

All resources are correctly managed:

- SQLite connections: `with sqlite3.connect(...) as conn:` — auto-commits and closes
- Temp files: `with tempfile.NamedTemporaryFile(...) as tmp:` — auto-deletes on exception
- WebSocket cleanup: `finally: self._cleanup(client_id)` in `handle_connection`
- Log handler cleanup: `_detach_log_handler()` called in `_cleanup()`
- Task cancellation: `task.cancel()` called in `_cleanup()` for all pending tasks
- ContextVar reset: `_request_id_var.reset(token)` in `finally` block of `RequestIdMiddleware`

No resource leaks were found.

---

## 13. Comments & Clarity

The codebase follows a "code as documentation" philosophy — functions and variables are named to be self-explanatory, with comments reserved for non-obvious decisions.

### Good comment examples

```python
# Suppress ccxt's verbose HTTP debug output — it logs full response bodies at DEBUG
logging.getLogger("ccxt").setLevel(logging.WARNING)

# minimum_size=1000 skips compression for tiny responses (health, bot list)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# stop_bot() performs network I/O (cancel tasks, close connections)
# — called outside the lock so other operations are not blocked
if bot:
    await bot.stop_bot()
```

These comments explain *why*, not *what* — the correct use of comments.

### TODO/FIXME comments

No `TODO` or `FIXME` comments were found in the API package source files. The bot package has one:

```python
# sonarft_manager.py:155
except BotRunError as error:  # noqa: F821 — kept for backward compat, never raised
```

This `noqa` comment is effectively a deferred TODO — the dead code should be removed.

---

## Concerns & Recommendations

### Medium

| # | Concern | Location | Detail |
|---|---|---|---|
| M1 | **`bots.py`/`clients.py` endpoint duplication** | Both files | 14 handlers implemented twice. Maintenance burden doubles for every bug fix or feature addition to bot lifecycle endpoints. |
| M2 | **`_deprecation_headers` and `_SUNSET_DATE` defined twice** | `bots.py:21`, `config.py:14` | Identical function and constant in two files. |
| M3 | **Dead `except BotRunError` with `noqa` suppression** | `sonarft_manager.py:155` | Dead code suppressed with `noqa: F821`. Should be removed. |
| M4 | **Unparameterised `list` and `dict` return types** | `bot_service.py:72,82`, `manager.py:97` | `-> list` and `event: dict` should be `-> list[dict[str, Any]]` and `event: dict[str, Any]`. |

### Low

| # | Concern | Location | Detail |
|---|---|---|---|
| L1 | **WS close codes as inline integers** | `websocket.py`, `manager.py` | `1001`, `1008`, `1011` should be named constants. |
| L2 | **`ConfigService` missing class-level docstring** | `config_service.py` | All other service classes have docstrings. |
| L3 | **`UP007` ruff ignore is redundant** | Root `pyproject.toml` | The codebase uses `X | None` syntax (not `Optional[X]`), making the `UP007` ignore unnecessary. |
| L4 | **`_decode_jwt` return type is `dict` not `dict[str, Any]`** | `core/security.py:37` | Minor — mypy would flag with `--strict`. |
| L5 | **`main.py` logging setup is 140 lines** | `main.py:55-140` | The logging configuration block could be extracted to a `_configure_logging(settings)` function to reduce `main.py` length. |

---

## Recommendations

### Priority 1

**R1 (M1/M2): Extract shared legacy infrastructure to a common module**

Create `src/api/v1/_legacy.py`:

```python
# src/api/v1/_legacy.py
from fastapi.responses import Response
from ...core.config import get_settings

SUNSET_DATE: str = get_settings().legacy_sunset_date  # or hardcoded once

def add_deprecation_headers(response: Response) -> None:
    """Inject Deprecation and Sunset headers on legacy responses."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = SUNSET_DATE
```

Import in both `bots.py` and `config.py`:
```python
from .._legacy import add_deprecation_headers, SUNSET_DATE
```

**R2 (M1): Extract shared bot lifecycle handler logic**

Create `src/api/v1/_bot_handlers.py` with the shared handler implementations, parameterised by `client_id` source:

```python
# src/api/v1/_bot_handlers.py
async def handle_list_bots(client_id: str, service: BotService) -> BotListResponse:
    return BotListResponse(botids=service.get_botids(client_id))

async def handle_create_bot(client_id: str, service: BotService) -> BotCreateResponse:
    botid = await service.create_bot(client_id)
    return BotCreateResponse(botid=botid)
# ... etc
```

Both `bots.py` and `clients.py` call these shared handlers, differing only in how `client_id` is extracted.

---

### Priority 2

**R3 (M3): Remove dead `except BotRunError` from `sonarft_manager.py`**

```python
# Before
async def run_bot(self, botid):
    try:
        sonarft = await self.get_bot_instance(botid)
        if not sonarft:
            return
        await sonarft.run_bot()
        sonarft.stop_bot_flag = False
    except BotRunError as error:  # noqa: F821 — kept for backward compat, never raised
        self.logger.exception(f"Bot run error: {error}")
        if botid:
            await self.remove_bot(botid)

# After
async def run_bot(self, botid):
    sonarft = await self.get_bot_instance(botid)
    if not sonarft:
        return
    await sonarft.run_bot()
    sonarft.stop_bot_flag = False
```

**R4 (M4): Parameterise `list` and `dict` return types**

```python
# bot_service.py
from typing import Any

async def get_orders(self, botid: str, client_id: str, ...) -> list[dict[str, Any]]:
    ...

# websocket/manager.py
async def push_event(self, client_id: str, event: dict[str, Any]) -> None:
    ...
```

---

### Priority 3

**R5 (L1): Extract WS close codes as named constants**

```python
# websocket/manager.py — add at module level
_WS_CLOSE_GOING_AWAY = 1001
_WS_CLOSE_POLICY_VIOLATION = 1008
_WS_CLOSE_INTERNAL_ERROR = 1011
```

**R6 (L5): Extract logging setup from `main.py`**

```python
# src/core/logging_setup.py
def configure_logging(settings: Settings) -> None:
    """Configure all log handlers from settings."""
    ...

# main.py — replace 140-line block with:
from .core.logging_setup import configure_logging
configure_logging(_settings)
```

---

## Python Best Practices Checklist

| Practice | Status |
|---|---|
| PEP 8 compliance | ✅ Enforced by ruff |
| Type hints on public APIs | ✅ |
| `from __future__ import annotations` where needed | ✅ |
| No star imports | ✅ |
| No unused imports | ✅ |
| Context managers for resources | ✅ |
| `asyncio.to_thread` for blocking I/O | ✅ (except `create_bot`) |
| No mutable default arguments | ✅ |
| `Annotated` type aliases for DI | ✅ |
| `lru_cache` for expensive singletons | ✅ |
| `dataclass` / Pydantic for data containers | ✅ |
| `secrets.token_urlsafe` for tokens | ✅ |
| `hmac.compare_digest` for token comparison | ✅ |
| No `print()` statements | ✅ |
| No hardcoded credentials | ✅ |
| Parameterised SQL queries | ✅ |
| Dead code removed | ❌ `except BotRunError` in `sonarft_manager.py` |
| Endpoint duplication eliminated | ❌ `bots.py` / `clients.py` |
| Consistent docstring format | ❌ No enforced format |

---

_Generated by Amazon Q Developer — SonarFT API Code Review Prompt Suite, Prompt 10_


---

## Post-Implementation Update (July 2025)

### Resolved findings

| ID | Finding | Resolution |
|---|---|---|
| M1 | `bots.py`/`clients.py` endpoint duplication | `_bot_handlers.py` — 14 duplicate handlers → 7 shared functions |
| M2 | `_deprecation_headers`/`_SUNSET_DATE` defined twice | `_legacy.py` — single `LEGACY_SUNSET_DATE` constant and `add_deprecation_headers()` |
| M3 | Dead `except BotRunError` with `noqa` suppression | Removed from `sonarft_manager.py`; `BotRunError` class also removed |
| M4 | Unparameterised `list`/`dict` return types | `TradeRecord` bounds added; `WsLogEvent` model used in `emit()` |

### New shared modules

```
src/api/v1/
├── _bot_handlers.py   ← shared bot lifecycle handler functions
└── _legacy.py         ← LEGACY_SUNSET_DATE + add_deprecation_headers()
```

### Updated Python best practices checklist

| Practice | Status |
|---|---|
| Dead code removed | ✅ `except BotRunError` and `BotRunError` class removed |
| Endpoint duplication eliminated | ✅ `_bot_handlers.py` |
| Shared constants | ✅ `LEGACY_SUNSET_DATE`, `TICKET_TTL_SECONDS` |
| `WsLogEvent` model used in emit | ✅ |
| `TradeRecord` field bounds | ✅ |
