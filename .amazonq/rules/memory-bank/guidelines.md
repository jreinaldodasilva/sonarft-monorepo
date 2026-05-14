# SonarFT - Development Guidelines

## Code Quality Standards

### Module Header Convention
Every Python file starts with a module-level docstring describing its role:
```python
"""
SonarFT Execution Module
Order execution (real and simulated), price monitoring, balance checking.
"""
```

### Class Structure Convention
Classes follow a consistent layout:
1. Class docstring
2. `__init__` with injected dependencies (api_manager, logger, peer modules)
3. Grouped methods separated by `# ### Section Name ***` comment banners
4. Private/support methods at the bottom

```python
# ### SonarftBot Class - ##########################################
class SonarftBot:
    """ """
    def __init__(self, library: str, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        ...

    # ### loaders *****************************************************
    def load_configurations(self, ...):
        ...

    # ### Initialize all modules ***************************************
    async def initialize_modules(self):
        ...
```

### Logger Injection Pattern
Every class accepts an optional logger and falls back to module-level logger:
```python
self.logger = logger or logging.getLogger(__name__)
```
Never use `print()` for operational messages — use `self.logger.info/warning/error/exception`.

### Decimal Precision
Set at the top of every file that performs financial calculations:
```python
from decimal import getcontext
getcontext().prec = 28
```
`prec=28` matches IEEE 754 decimal128 and is the correct value for financial calculations.

### Type Annotations
All public methods use full type annotations with `typing` imports:
```python
from typing import Dict, List, Tuple, Optional, Union
async def execute_trade(self, botid, trade: dict) -> dict:
async def _execute_two_leg_trade(self, ...) -> tuple[bool, bool, bool]:
```

---

## Async Patterns

### All I/O is async
Every exchange API call, order book fetch, indicator calculation, and order execution is `async/await`:
```python
async def monitor_price(self, exchange_id: str, base: str, quote: str, side, price_to_check, max_wait_seconds: int = 120):
    deadline = asyncio.get_running_loop().time() + max_wait_seconds
    while asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(3)
        price = await self.api_manager.get_last_price(exchange_id, base, quote)
```

### Concurrent execution with asyncio.gather
Use `asyncio.gather` for parallel operations (symbol processing, dual-exchange calls, startup reconciliation):
```python
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Stop event pattern
Long-running loops use `asyncio.Event` for graceful shutdown, with `asyncio.wait_for` + `asyncio.shield` for interruptible sleeps:
```python
self._stop_event = asyncio.Event()

# In run loop:
try:
    await asyncio.wait_for(asyncio.shield(self._stop_event.wait()), timeout=timesleep_size)
except asyncio.TimeoutError:
    pass
```

### asyncio.Lock for shared state
Per-exchange locks prevent concurrent balance race conditions:
```python
if exchange_id not in self._exchange_locks:
    self._exchange_locks[exchange_id] = asyncio.Lock()
async with self._exchange_locks[exchange_id]:
    balance = await self.api_manager.get_balance(exchange_id)
```

### try/finally for resource cleanup
Order monitoring always cancels the order on any exit path (timeout, CancelledError, exception):
```python
try:
    while asyncio.get_running_loop().time() < deadline:
        ...
finally:
    cancelled = await self._cancel_order_with_retry(exchange_id, order_id, base, quote)
```

---

## Error Handling Patterns

### logger.exception for unexpected errors
Use `self.logger.exception(...)` (not `logger.error`) for unexpected exceptions — it includes the full traceback:
```python
except Exception:
    self.logger.exception("Error executing trade")
    return {"success": False, "profit": 0.0}
```

### Return None/False/dict on failure
Methods return `None`, `False`, or a typed failure dict rather than raising, allowing callers to check:
```python
if result_buy_order is None or result_sell_order is None:
    return buy_order_id, sell_order_id, False, False, False
```

### Custom exception classes with default messages
Domain-specific errors use custom exception classes:
```python
class BotCreationError(Exception):
    """Raised when there's an issue during the bot creation process."""
    def __init__(self, message="Failed to create the bot."):
        self.message = message
        super().__init__(self.message)
```

### FastAPI error handlers
The API uses dedicated exception handler functions registered at app creation, not inline try/except in routes:
```python
app.add_exception_handler(BotNotFoundError, bot_not_found_handler)
app.add_exception_handler(BotCreationFailedError, bot_creation_failed_handler)
app.add_exception_handler(Exception, generic_error_handler)
```

### Exponential backoff retry
Order cancellation and other critical operations use exponential backoff:
```python
async def _cancel_order_with_retry(self, exchange_id, order_id, base, quote, max_retries=3):
    for attempt in range(1, max_retries + 1):
        result = await self.api_manager.cancel_order(exchange_id, order_id, base, quote)
        if result is not None:
            return True
        if attempt < max_retries:
            backoff = 2 ** (attempt - 1)  # 1s, 2s
            await asyncio.sleep(backoff)
```

### Circuit breaker pattern
The bot run loop tracks consecutive failures and stops after a configurable threshold:
```python
consecutive_failures += 1
if consecutive_failures >= max_failures:
    self._stop_event.set()
    await self._send_alert(...)
    break
```

---

## Naming Conventions

### Python (snake_case throughout)
- Classes: `PascalCase` — `SonarftBot`, `BotManager`, `TradeProcessor`, `RequestIdMiddleware`
- Methods: `snake_case` — `create_bot`, `load_configurations`, `execute_trade`
- Private methods: leading underscore — `_execute_single_trade`, `_cancel_order_with_retry`, `_load_config_section`
- Variables: `snake_case` — `buy_exchange`, `profit_percentage`, `trade_amount`
- Constants: `UPPER_SNAKE_CASE` — `RSI_OVERBOUGHT`, `RSI_OVERSOLD`, `MAX_USER_INST`
- Module-level private: leading underscore — `_BOT_DIR`, `_settings`, `_log_fmt`

### Market direction strings
Use lowercase string literals `'bull'`, `'bear'`, `'neutral'` consistently across all modules.

### Exchange/symbol format
Symbols always constructed as `f"{base}/{quote}"` — never hardcoded as a full string.

### Trade position strings
Use uppercase string literals `'LONG'`, `'SHORT'` for trade positions.

---

## Dependency Injection Pattern
Modules never instantiate their own dependencies. All dependencies are passed via constructor:
```python
class SonarftExecution:
    def __init__(self, api_manager: SonarftApiManager, sonarft_helpers: SonarftHelpers,
                 is_simulation_mode: bool, logger=None, max_trade_amount: float = 0.0, ...):
        self.api_manager = api_manager
        self.sonarft_helpers = sonarft_helpers
```
`SonarftBot.initialize_modules` is the single wiring point for the entire dependency graph.

---

## Configuration Pattern
All config is loaded from JSON files via named setups (e.g. `parameters_1`, `exchanges_1`):
```python
def _load_config_section(self, pathname: str, key: str):
    with open(pathname) as f:
        data = json.load(f)
    return data[key]
```
Config values are validated through Pydantic schemas (`ParametersConfig`, `SymbolConfig`, `FeeConfig`) on load.
Never hardcode trading parameters — always read from config files.

### Live mode guard
Switching from simulation to live trading requires an explicit environment variable:
```python
if self.is_simulating_trade == 0:
    if not os.environ.get("SONARFT_ALLOW_LIVE"):
        raise BotCreationError("Live trading requires SONARFT_ALLOW_LIVE=true ...")
```

### Hot-reload with rollback
`apply_parameters` saves old values before applying and restores them if validation fails:
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

## Simulation Mode Pattern
The `is_simulation_mode` boolean gates all real order placement:
```python
if not self.is_simulation_mode:
    order_placed = await self.api_manager.create_order(...)
else:
    slippage = random.uniform(0, 0.001)
    executed_amount = trade_amount
    remaining_amount = 0
    order_placed_id = f"{side}_{random.randint(100000, 999999)}"
```
Balance checks also short-circuit in simulation mode: `if self.is_simulation_mode: return True`.

---

## API Layer Patterns (FastAPI)

### Application factory
The app is created via `create_app()` factory function, not at module level:
```python
def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=..., lifespan=_lifespan, default_response_class=ORJSONResponse)
    ...
    return app

app = create_app()
```

### Lifespan for startup/shutdown
Services are initialised in the `@asynccontextmanager` lifespan and stored on `app.state`:
```python
@asynccontextmanager
async def _lifespan(app: FastAPI):
    app.state.bot_service = BotService()
    app.state.config_service = ConfigService()
    yield
```

### Middleware stack (outermost to innermost)
```
GZipMiddleware → SlowAPIMiddleware (rate limit) → SecurityHeadersMiddleware
→ AccessLogMiddleware → RequestIdMiddleware → CORSMiddleware
```

### Request ID propagation
`RequestIdMiddleware` generates/propagates `X-Request-ID` and sets a `ContextVar` so all log lines within a request include the ID:
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

### Security headers
`SecurityHeadersMiddleware` adds `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `HSTS`, `Permissions-Policy`, `Cache-Control`, and `Content-Security-Policy` to every response.

### Logging
- Log format: `"%(asctime)s %(levelname)s [%(request_id)s] %(name)s — %(message)s"`
- Rotating file handler: 10 MB per file, 7 backups
- Separate metrics logger (`sonarft.metrics`) writes raw JSON lines to a dedicated file
- Optional structured JSON log enabled via `JSON_LOG_FILE` env var
- ccxt verbose output suppressed: `logging.getLogger("ccxt").setLevel(logging.WARNING)`

---

## Financial Calculation Patterns

### VWAP calculation
Standard pattern used in both `SonarftApiManager` and `SonarftPrices`:
```python
total_bid_volume = sum(volume for _, volume in bids)
bid_vwap = sum(price * volume for price, volume in bids) / total_bid_volume
```

### Price rounding by exchange rules
Each exchange has an `EXCHANGE_RULES` dict in `SonarftMath` defining precision per field:
```python
buy_price = round(buy_price, buy_rules['prices_precision'])
buy_fee_quote = round(buy_price * target_amount_buy * buy_fee_rate, buy_rules['fee_precision'])
```

### Indicator data format
OHLCV data is always indexed positionally: `[timestamp, open, high, low, close, volume]`
- Close price: `x[4]`
- High price: `x[2]`
- Low price: `x[3]`
- Volume: `x[5]`

### pandas-ta usage
Always convert OHLCV close prices to `pd.Series` before passing to pandas-ta:
```python
close_prices = pd.Series([x[4] for x in ohlcv])
rsi = pta.rsi(close_prices, length=moving_average_period)
return rsi.iloc[-1]
```

---

## C++ Model Conventions (models/)
- Use `constexpr` for compile-time constants: `constexpr int MAX_N = 100000;`
- Use `std::vector` with `.reserve()` for performance-critical collections
- Use `std::stable_sort` when sort stability matters
- Use `std::chrono::high_resolution_clock` for benchmarking
- Use `std::mt19937` with `std::random_device` for random number generation
- Input validation checks all constraints before processing and returns `false`/`1` on violation
- Genetic algorithm parameters (population size, generations, tournament size) are hardcoded constants

## Java Model Conventions (models/)
- `private final` for all constraint constants
- `Random` seeded for reproducibility; seed=1 produces the sample/reference case
- Gaussian distribution (`random.nextGaussian()`) for realistic test data generation
- `Math.max`/`Math.min` to clamp generated values within valid ranges
