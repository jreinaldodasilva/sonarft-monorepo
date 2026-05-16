# Developer Guide

This guide defines the coding standards, patterns, and conventions used throughout the SonarFT codebase. All contributions must follow these conventions to maintain consistency.

---

## Python Coding Standards

### Module Header Convention

Every Python file starts with a module-level docstring describing its role:

```python
"""
SonarFT Execution Module
Order execution (real and simulated), price monitoring, balance checking.
"""
```

This is not optional. It serves as the first thing a reader sees and must accurately describe the file's responsibility.

### Class Structure Convention

Classes follow a consistent layout:

1. Class docstring
2. `__init__` with injected dependencies
3. Grouped methods separated by `# ### Section Name ***` comment banners
4. Private/support methods at the bottom

```python
# ### SonarftBot Class - ##########################################
class SonarftBot:
    """ """

    def __init__(self, library: str, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self.library = library
        # ... other attributes

    # ### loaders *****************************************************
    def load_configurations(self, config_setup: str) -> None:
        ...

    # ### Initialize all modules ***************************************
    async def initialize_modules(self) -> None:
        ...

    # ### private helpers **********************************************
    def _load_config_section(self, pathname: str, key: str):
        ...
```

### Logger Injection Pattern

Every class accepts an optional logger and falls back to the module-level logger:

```python
self.logger = logger or logging.getLogger(__name__)
```

**Never use `print()` for operational messages.** Use `self.logger.info/warning/error/exception`. The `print()` function bypasses the logging infrastructure, loses request IDs, and cannot be redirected to files or structured log sinks.

Use `self.logger.exception(...)` (not `self.logger.error(...)`) for unexpected exceptions — it automatically includes the full traceback:

```python
except Exception:
    self.logger.exception("Error executing trade")
    return {"success": False, "profit": 0.0}
```

### Type Annotations

All public methods use full type annotations:

```python
from typing import Dict, List, Tuple, Optional, Union

async def execute_trade(self, botid: str, trade: dict) -> dict:
    ...

async def get_weighted_prices(self, depth: int, order_book: Dict) -> Tuple[float, float]:
    ...
```

### Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Classes | `PascalCase` | `SonarftBot`, `BotManager`, `TradeProcessor` |
| Methods | `snake_case` | `create_bot`, `load_configurations` |
| Private methods | `_snake_case` | `_execute_single_trade`, `_load_config_section` |
| Variables | `snake_case` | `buy_exchange`, `profit_percentage` |
| Constants | `UPPER_SNAKE_CASE` | `RSI_OVERBOUGHT`, `EXCHANGE_RULES` |
| Module-level private | `_snake_case` | `_BOT_DIR`, `_settings` |

**Market direction strings:** always lowercase `'bull'`, `'bear'`, `'neutral'`.
**Trade position strings:** always uppercase `'LONG'`, `'SHORT'`.
**Symbol format:** always `f"{base}/{quote}"` — never hardcoded as a full string.

### Financial Precision

Every file that performs financial calculations must set decimal precision at the top:

```python
from decimal import getcontext
getcontext().prec = 28
```

`prec=28` matches IEEE 754 decimal128. This matters because floating-point arithmetic accumulates rounding errors that compound over thousands of trades. A 0.0001% rounding error on a $10,000 trade is $0.01 — small per trade, but significant at scale. Using `Decimal` with `prec=28` ensures calculations are reproducible and auditable.

---

## Async Patterns

### All I/O is async

Every exchange API call, order book fetch, indicator calculation, and order execution must be `async/await`. Blocking I/O on the event loop stalls all concurrent bot cycles.

```python
async def get_rsi(self, exchange: str, base: str, quote: str, period: int = 14) -> float | None:
    ohlcv = await self.api_manager.get_history(exchange, base, quote, '1m', period + 2)
    if not ohlcv:
        return None
    close_prices = pd.Series([x[4] for x in ohlcv])
    rsi = pta.rsi(close_prices, length=period)
    return float(rsi.iloc[-1])
```

### Concurrent Execution with asyncio.gather

Use `asyncio.gather` for parallel operations. This is the primary mechanism for processing multiple symbols concurrently within a single bot cycle:

```python
futures = [
    self.trade_processor.process_symbol(botid, symbol, trade_amount, threshold)
    for symbol in self.symbols
]
results = await asyncio.gather(*futures, return_exceptions=True)

for result in results:
    if isinstance(result, Exception):
        self.logger.error(f"Symbol processing error: {result}")
```

`return_exceptions=True` is critical — without it, a single symbol failure cancels all other concurrent tasks.

### Stop Event Pattern

Long-running loops use `asyncio.Event` for graceful shutdown. The `asyncio.shield` + `asyncio.wait_for` pattern creates an interruptible sleep that responds to the stop event without being cancelled by the timeout:

```python
self._stop_event = asyncio.Event()

# In run loop:
try:
    await asyncio.wait_for(
        asyncio.shield(self._stop_event.wait()),
        timeout=sleep_seconds
    )
except asyncio.TimeoutError:
    pass  # normal — timeout elapsed, continue loop
# If stop_event was set, the wait returns without raising
if self._stop_event.is_set():
    break
```

Why `asyncio.shield`? Without it, when `asyncio.wait_for` times out, it cancels the inner coroutine — which would cancel the `_stop_event.wait()` itself, making it impossible to detect the stop signal on the next iteration.

### asyncio.Lock for Shared State

Per-exchange locks prevent concurrent balance race conditions when multiple symbols are processed in parallel:

```python
if exchange_id not in self._exchange_locks:
    self._exchange_locks[exchange_id] = asyncio.Lock()

async with self._exchange_locks[exchange_id]:
    balance = await self.api_manager.get_balance(exchange_id)
    # balance check and order placement are atomic per exchange
```

The `BotManager` bot registry is also protected by `asyncio.Lock`:

```python
async with self._lock:
    self._bots[botid] = bot
    self._clients.setdefault(client_id, []).append(botid)
```

`stop_bot()` is called **outside** the lock to avoid blocking other operations during network I/O (order cancellation, exchange connection close).

### try/finally for Resource Cleanup

Order monitoring always cancels the order on any exit path — timeout, `CancelledError`, or unexpected exception:

```python
try:
    while asyncio.get_running_loop().time() < deadline:
        status = await self.api_manager.fetch_order(exchange_id, order_id, base, quote)
        if status and status.get('status') == 'closed':
            return True
        await asyncio.sleep(3)
finally:
    # Always attempt cancellation — even if the monitoring loop was cancelled
    await self._cancel_order_with_retry(exchange_id, order_id, base, quote)
```

### Exponential Backoff Retry

Critical operations use exponential backoff:

```python
async def _cancel_order_with_retry(self, exchange_id, order_id, base, quote, max_retries=3):
    for attempt in range(1, max_retries + 1):
        result = await self.api_manager.cancel_order(exchange_id, order_id, base, quote)
        if result is not None:
            return True
        if attempt < max_retries:
            backoff = 2 ** (attempt - 1)  # 1s, 2s
            await asyncio.sleep(backoff)
    return False
```

---

## Error Handling Patterns

### Return None/False on Failure

Methods return `None`, `False`, or a typed failure dict rather than raising, allowing callers to check:

```python
async def get_order_book(self, exchange_id: str, base: str, quote: str) -> dict | None:
    try:
        return await self.call_api_method(exchange_id, 'fetch_order_book', 'watch_order_book', ...)
    except Exception as e:
        self.logger.error(f"Error fetching order book: {e}")
        return None

# Caller:
order_book = await self.api_manager.get_order_book(exchange_id, base, quote)
if order_book is None:
    return  # skip this symbol
```

### Custom Exception Classes

Domain-specific errors use custom exception classes with default messages:

```python
class BotCreationError(Exception):
    """Raised when there's an issue during the bot creation process."""
    def __init__(self, message="Failed to create the bot."):
        self.message = message
        super().__init__(self.message)
```

### FastAPI Error Handlers

The API uses dedicated exception handler functions registered at app creation, not inline try/except in routes:

```python
# In create_app():
app.add_exception_handler(BotNotFoundError, bot_not_found_handler)
app.add_exception_handler(BotCreationFailedError, bot_creation_failed_handler)
app.add_exception_handler(Exception, generic_error_handler)
```

This keeps route handlers clean and ensures consistent error response format across all endpoints.

---

## Dependency Injection Pattern

Modules never instantiate their own dependencies. All dependencies are passed via constructor:

```python
class SonarftPrices:
    def __init__(
        self,
        api_manager: SonarftApiManager,
        sonarft_indicators: SonarftIndicators,
        logger=None
    ):
        self.api_manager = api_manager
        self.sonarft_indicators = sonarft_indicators
        self.logger = logger or logging.getLogger(__name__)
```

`SonarftBot.initialize_modules()` is the single wiring point for the entire dependency graph. This makes the dependency structure explicit, testable (dependencies can be mocked), and prevents hidden coupling between modules.

---

## Configuration Loading Pattern

All config is loaded from JSON files via named setups:

```python
def _load_config_section(self, pathname: str, key: str):
    """Generic JSON config loader: opens pathname and returns data[key]."""
    with open(pathname) as f:
        data = json.load(f)
    return data[key]

# Usage:
parameters_raw = self._load_config_section(
    "sonarftdata/config_parameters.json",
    f"parameters_{config['parameters_setup']}"
)[0]
```

After loading, raw dicts are validated through Pydantic schemas before being applied:

```python
try:
    parameters = ParametersConfig(**parameters_raw)
except Exception as e:
    raise BotCreationError(f"Invalid trading parameters: {e}") from e
```

Never hardcode trading parameters. All values must come from config files.

### Hot-Reload with Rollback

`apply_parameters()` saves old values before applying and restores them if validation fails:

```python
old_values = {}
old_values["trade_amount"] = self.trade_amount
self.trade_amount = float(parameters["trade_amount"])

try:
    self._validate_parameters()
except ValueError:
    for key, val in old_values.items():
        setattr(self, key, val)
    raise
```

---

## FastAPI Standards

### Application Factory

The app is created via `create_app()` factory function, not at module level. This enables testing (create a fresh app per test) and avoids import-time side effects:

```python
def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.api_title, lifespan=_lifespan, ...)
    # register middleware, error handlers, routers
    return app

app = create_app()
```

### Lifespan for Startup/Shutdown

Services are initialised in the `@asynccontextmanager` lifespan and stored on `app.state`:

```python
@asynccontextmanager
async def _lifespan(app: FastAPI):
    app.state.bot_service = BotService()
    app.state.config_service = ConfigService()
    yield
    # shutdown cleanup here
```

This ensures:
- The bot package import happens before the server accepts requests
- Import errors surface immediately with a clear message
- Services are accessible to route handlers via `request.app.state`

### WebSocket Ticket Auth

The WebSocket ticket pattern prevents the JWT from appearing in server access logs and browser history:

```python
# 1. Client exchanges JWT for a short-lived ticket
@router.post("/ws/ticket")
async def get_ws_ticket(identity: str = Depends(get_client_id)) -> WsTicketResponse:
    store = get_ticket_store()
    ticket = store.issue(identity)
    return WsTicketResponse(ticket=ticket, ttl_seconds=30)

# 2. Client connects with the ticket in the query string
@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, ticket: str = Query(...)):
    store = get_ticket_store()
    identity = store.redeem(ticket)  # single-use, 30s TTL
    if not identity:
        await websocket.close(code=4001)
        return
```

The `TicketStore` is an in-memory singleton. Tickets are 32-byte URL-safe random strings, expire after 30 seconds, and can only be redeemed once.

### Request ID Propagation

`RequestIdMiddleware` generates or propagates `X-Request-ID` and sets a `ContextVar` so all log lines within a request include the ID:

```python
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = _request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            _request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response
```

The `ContextVar` is reset in `finally` to prevent leaking the request ID into subsequent requests on the same thread.

---

## React / TypeScript Standards

### Hooks Organization

Custom hooks live in `packages/web/src/hooks/`. Each hook has a single responsibility:

| Hook | Responsibility |
|---|---|
| `useWebSocket` | WebSocket connection lifecycle, reconnect with exponential backoff, ping watchdog |
| `useBots` | Bot state machine, WebSocket message handling, REST API calls, RAF log batching |
| `useConfigCheckboxes` | Checkbox state for parameters and indicators configuration panels |
| `useIdleTimeout` | Session idle timeout detection |
| `AuthProvider` | Netlify Identity auth context, dev bypass |

### Bot State Machine

Bot lifecycle is managed with `useReducer` with explicit transitions. This prevents impossible states (e.g. "removing" a bot that was never created):

```typescript
type BotLifecycle = "idle" | "creating" | "running" | "stopping" | "stopped" | "removing" | "error";

function botMachineReducer(state: BotMachineState, action: BotMachineAction): BotMachineState {
    switch (action.type) {
        case "CREATE_REQUESTED": return { lifecycle: "creating", canRemove: false };
        case "BOT_CREATED":      return { lifecycle: "running",  canRemove: true  };
        case "STOP_REQUESTED":   return { ...state, lifecycle: "stopping" };
        case "BOT_STOPPED":      return { lifecycle: "stopped",  canRemove: true  };
        case "REMOVE_REQUESTED": return { ...state, lifecycle: "removing" };
        case "BOT_REMOVED":      return { lifecycle: "idle",     canRemove: false };
        case "ERROR":            return { ...state, lifecycle: "error" };
        default:                 return state;
    }
}
```

### RAF Log Batching

WebSocket log messages accumulate in a ref buffer and flush to React state at most 60 times/second via `requestAnimationFrame`. This prevents GC pressure and excessive re-renders at high message frequency:

```typescript
// Accumulate in ref — no re-render
logBufferRef.current.push(msg.message ?? "");

// Flush on animation frame — at most 60fps
const flush = () => {
    if (logBufferRef.current.length > 0) {
        const incoming = logBufferRef.current.splice(0);
        setLogs(prev => {
            const next = [...prev, ...incoming];
            return next.length > MAX_LOG_LINES ? next.slice(-MAX_LOG_LINES) : next;
        });
    }
    rafRef.current = requestAnimationFrame(flush);
};
rafRef.current = requestAnimationFrame(flush);
```

### WebSocket Reconnect

`useWebSocket` implements exponential backoff reconnection:

```typescript
const delay = Math.min(
    BACKOFF_BASE_MS * Math.pow(2, attemptRef.current),  // 1s, 2s, 4s, 8s...
    BACKOFF_MAX_MS  // capped at 30s
);
attemptRef.current += 1;
setTimeout(connect, delay);
```

A ping watchdog closes silently dropped connections so the reconnect loop can re-establish them:

```typescript
const watchdog = setInterval(() => {
    const ws = socketRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
        if (Date.now() - lastMessageRef.current > PING_TIMEOUT_MS) {
            ws.close();  // triggers onclose → reconnect
        }
    }
}, PING_CHECK_INTERVAL_MS);
```

### Shared API Contract

The frontend imports types directly from `shared/types/api.ts`. Never define API types inline in component files:

```typescript
import type { TradeRecord, WsEvent, WsCommand } from "../../shared/types/api";
```

All WebSocket messages sent to the server must conform to `WsCommand`. All messages received from the server must be typed as `WsEvent`.

---

## Git Workflow

### Branch Naming

```
main          — production-ready code
develop       — integration branch
feature/...   — new features (e.g. feature/add-macd-indicator)
fix/...       — bug fixes (e.g. fix/ws-reconnect-loop)
chore/...     — maintenance (e.g. chore/update-dependencies)
```

### Commit Conventions

Use conventional commits:

```
feat: add StochRSI crossover signal to price adjustment
fix: prevent double-cancel on order timeout
chore: update ccxt to 4.5.48
docs: add WebSocket ticket auth flow to architecture.md
test: add hypothesis tests for SonarftMath.calculate_trade
```

### PR Requirements

Before merging a PR:

1. `make lint` passes with 0 errors and 0 warnings
2. `make test` passes — all packages
3. No new `npm audit` Critical or High vulnerabilities
4. No new `pip-audit` High or Critical vulnerabilities
5. `shared/types/api.ts` and `packages/api/src/models/schemas.py` are in sync if either was modified
6. New public methods have type annotations
7. New Python files have module-level docstrings
8. Financial calculation changes include a test in `test_sonarft_math.py` or `test_hypothesis_math.py`

### CI Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on push and PR to `main` and `develop`:

- **Web job:** `npm ci` → lint → test → coverage → prettier check → `npm audit --audit-level=critical`
- **Bot job:** `pip install` → pytest → `pip-audit --severity high`
- **API job:** `pip install` → ruff lint → pytest with coverage (≥75%) → mypy → `pip-audit --severity high`
