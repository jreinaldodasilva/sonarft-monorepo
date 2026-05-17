# Testing Guide

SonarFT uses a multi-layer test strategy: pytest for the Python packages, Vitest + RTL + MSW for the frontend, and Hypothesis for property-based testing of financial calculations.

---

## Running Tests

```bash
make test          # all packages
make test-bot      # packages/bot only
make test-api      # packages/api only
make test-web      # packages/web only
```

---

## Bot Package Tests (`packages/bot/tests/`)

### Framework

- **pytest** — test runner
- **pytest-asyncio** — async test support
- **Hypothesis** — property-based testing for financial math

### Configuration

`packages/bot/pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

`asyncio_mode = auto` means all `async def test_*` functions are automatically treated as async tests without needing `@pytest.mark.asyncio`.

### Test Files

| File | Coverage |
|---|---|
| `test_sonarft_bot.py` | Bot creation, config loading, lifecycle, live mode guard |
| `test_sonarft_manager.py` | BotManager create/run/remove, concurrent access |
| `test_sonarft_search_execution.py` | Search orchestration, daily loss, halt conditions |
| `test_sonarft_math.py` | Profit calculation, fee calculation, precision |
| `test_hypothesis_math.py` | Property-based tests for SonarftMath |
| `test_sonarft_math_precision.py` | Decimal precision edge cases |
| `test_sonarft_prices.py` | VWAP calculation, price adjustment |
| `test_sonarft_indicators.py` | RSI, MACD, StochRSI, SMA |
| `test_sonarft_validators.py` | Liquidity depth, spread threshold |
| `test_sonarft_api_manager.py` | Exchange API abstraction, ccxt mocking |
| `test_simulation_integration.py` | Full simulation mode integration |
| `test_trade_executor.py` | Async task management, shutdown |
| `test_phase3_performance.py` | Performance benchmarks |
| `test_phase4_features.py` | Feature integration tests |

### Mocking Exchange APIs

Exchange API calls are mocked using `unittest.mock.AsyncMock`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_api_manager():
    manager = MagicMock()
    manager.get_order_book = AsyncMock(return_value={
        "bids": [[2450.0, 1.5], [2449.5, 2.0]],
        "asks": [[2451.0, 1.0], [2451.5, 3.0]],
    })
    manager.get_history = AsyncMock(return_value=[
        [1705312200000, 2448.0, 2452.0, 2447.0, 2450.0, 100.0],
        # ... more OHLCV candles
    ])
    return manager
```

### Testing Async Systems

All async tests use `asyncio_mode = auto`. For tests that need to control the event loop or test concurrent behavior:

```python
import asyncio
import pytest

async def test_concurrent_symbol_processing(mock_api_manager):
    search = SonarftSearch(
        sonarft_math=mock_math,
        sonarft_prices=mock_prices,
        # ...
    )
    # Verify asyncio.gather processes all symbols
    await search.search_trades("test-bot-id")
    assert mock_prices.get_weighted_prices.call_count == len(symbols)
```

### Property-Based Testing with Hypothesis

`test_hypothesis_math.py` uses Hypothesis to test `SonarftMath.calculate_trade` with a wide range of inputs:

```python
from hypothesis import given, strategies as st

@given(
    buy_price=st.floats(min_value=0.01, max_value=100000.0, allow_nan=False),
    sell_price=st.floats(min_value=0.01, max_value=100000.0, allow_nan=False),
    trade_amount=st.floats(min_value=0.001, max_value=10.0, allow_nan=False),
    buy_fee_rate=st.floats(min_value=0.0, max_value=0.01, allow_nan=False),
    sell_fee_rate=st.floats(min_value=0.0, max_value=0.01, allow_nan=False),
)
def test_calculate_trade_profit_sign(buy_price, sell_price, trade_amount, buy_fee_rate, sell_fee_rate):
    """Profit should be positive iff sell_value > buy_value after fees."""
    result = sonarft_math.calculate_trade(...)
    if sell_price > buy_price:
        # Not guaranteed to be profitable due to fees, but profit sign should be consistent
        assert result["profit"] == pytest.approx(result["sell_value"] - result["buy_value"])
```

Hypothesis generates hundreds of test cases automatically, including edge cases like very small prices, equal buy/sell prices, and maximum fee rates.

### conftest.py

`packages/bot/tests/conftest.py` provides shared fixtures:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_api_manager():
    ...

@pytest.fixture
def mock_logger():
    return MagicMock()

@pytest.fixture
def sample_ohlcv():
    """50 candles of synthetic OHLCV data — enough for MACD warmup."""
    ...
```

---

## API Package Tests (`packages/api/tests/`)

### Framework

- **pytest** — test runner
- **pytest-asyncio** — async test support
- **httpx** — async HTTP client for FastAPI testing
- **pytest-cov** — coverage reporting (minimum 75%)

### Configuration

`packages/api/pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

### Test Structure

```
packages/api/tests/
├── unit/
│   ├── test_security.py       # JWT validation, static token, tenant isolation
│   ├── test_tickets.py        # TicketStore: issue, redeem, expiry, capacity
│   ├── test_schemas.py        # Pydantic model validation
│   └── test_config_service.py # Config read/write, validation
└── integration/
    ├── test_bots.py           # Bot CRUD endpoints
    ├── test_parameters.py     # Parameters GET/PUT
    ├── test_indicators.py     # Indicators GET/PUT
    ├── test_websocket.py      # WebSocket connection, ticket auth, events
    └── test_health.py         # Health endpoint
```

### FastAPI Test Client

Integration tests use `httpx.AsyncClient` with the FastAPI app:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import create_app

@pytest.fixture
async def client():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

async def test_health(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

### Mocking BotService

Bot service calls are mocked to avoid requiring a real bot engine in API tests:

```python
@pytest.fixture
def mock_bot_service(monkeypatch):
    service = MagicMock()
    service.create_bot = AsyncMock(return_value="test-bot-id")
    service.get_bot_ids = MagicMock(return_value=["test-bot-id"])
    monkeypatch.setattr("src.services.bot_service.BotService", lambda: service)
    return service
```

### WebSocket Testing

```python
async def test_websocket_requires_ticket(client):
    # Connect without a ticket — should be rejected
    with pytest.raises(Exception):
        async with client.websocket_connect("/api/v1/ws/test-client"):
            pass

async def test_websocket_with_valid_ticket(client):
    # Get a ticket first
    ticket_response = await client.post("/api/v1/ws/ticket")
    ticket = ticket_response.json()["ticket"]

    # Connect with the ticket
    async with client.websocket_connect(f"/api/v1/ws/test-client?ticket={ticket}") as ws:
        data = await ws.receive_json()
        assert data["type"] == "connected"
```

### Coverage

The CI pipeline requires ≥75% coverage:

```bash
cd packages/api && pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=75
```

---

## Web Package Tests (`packages/web/src/`)

### Framework

- **Vitest** — test runner (Vite-native, fast)
- **@testing-library/react** — component testing utilities
- **MSW v2** — Mock Service Worker for HTTP and WebSocket mocking
- **jest-axe** — accessibility testing
- **jsdom** — DOM environment

### Configuration

`packages/web/vite.config.js` includes Vitest configuration:

```javascript
test: {
    environment: "jsdom",
    setupFiles: ["./src/setupTests.ts"],
    globals: true,
}
```

`src/setupTests.ts` initialises MSW and jest-axe matchers.

### Running Tests

```bash
cd packages/web

npm test              # run once (CI mode)
npm run test:watch    # watch mode (development)
npm test -- --coverage  # with coverage report
```

### Test Files

| File | Coverage |
|---|---|
| `App.test.tsx` | Root component rendering, routing |
| `hooks/useWebSocket.test.tsx` | Connection lifecycle, reconnect, ping watchdog |
| `hooks/useBots.test.ts` | State machine, WebSocket messages, REST calls |
| `hooks/useConfigCheckboxes.test.ts` | Checkbox state management |
| `hooks/useIdleTimeout.test.ts` | Idle detection, timer reset |
| `hooks/AuthProvider.test.tsx` | Auth context, dev bypass |

### MSW Setup

MSW handlers are defined in `src/mocks/` and started in `setupTests.ts`:

```typescript
// src/setupTests.ts
import { server } from "./mocks/server";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

`onUnhandledRequest: "error"` ensures tests fail if they make unexpected network requests — preventing tests from accidentally hitting real APIs.

### Component Testing Pattern

```typescript
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { server } from "../mocks/server";
import { http, HttpResponse } from "msw";

test("creates a bot when Create button is clicked", async () => {
    server.use(
        http.post("/api/v1/clients/test-client/bots", () =>
            HttpResponse.json({ botid: "new-bot-id" })
        )
    );

    render(<CryptoPage clientId="test-client" />);

    fireEvent.click(screen.getByRole("button", { name: /create bot/i }));

    await waitFor(() => {
        expect(screen.getByText("new-bot-id")).toBeInTheDocument();
    });
});
```

### Accessibility Testing

```typescript
import { axe, toHaveNoViolations } from "jest-axe";
expect.extend(toHaveNoViolations);

test("trading interface has no accessibility violations", async () => {
    const { container } = render(<CryptoPage clientId="test-client" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
});
```

### Testing the Bot State Machine

```typescript
import { renderHook, act } from "@testing-library/react";
import useBots from "../hooks/useBots";

test("lifecycle transitions from idle to running after bot creation", async () => {
    const { result } = renderHook(() => useBots("test-client"));

    expect(result.current.lifecycle).toBe("idle");

    act(() => result.current.handleCreate());
    expect(result.current.lifecycle).toBe("creating");

    // Simulate bot_created WebSocket message
    act(() => {
        // trigger the WebSocket message handler
    });

    await waitFor(() => {
        expect(result.current.lifecycle).toBe("running");
    });
});
```

---

## CI Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on push and PR to `main` and `develop`.

### Web Job

```yaml
- npm ci
- npm run lint          # ESLint — 0 errors required
- npm test              # Vitest — all tests must pass
- npm test -- --coverage
- npx prettier --check  # format check
- npm audit --audit-level=critical  # block on Critical CVEs only
```

### Bot Job

```yaml
- pip install -r requirements.txt && pip install -e .
- pytest tests/ -q
- pip-audit -r requirements.txt --severity high  # block on High/Critical
```

### API Job

```yaml
- pip install -e ../bot
- pip install -r requirements.txt -r requirements-test.txt
- ruff check src/ tests/
- pytest tests/ --cov=src --cov-fail-under=75
- mypy src/ --ignore-missing-imports
- pip-audit -r requirements.txt --severity high
```

---

## Writing New Tests

### For a new bot module

1. Create `packages/bot/tests/test_{module_name}.py`
2. Add a module-level docstring
3. Use `@pytest.fixture` for shared setup
4. Mock `SonarftApiManager` with `AsyncMock` — never make real exchange calls in tests
5. For financial calculations, add a Hypothesis test in `test_hypothesis_math.py`

### For a new API endpoint

1. Add unit tests in `packages/api/tests/unit/`
2. Add integration tests in `packages/api/tests/integration/`
3. Mock `BotService` and `ConfigService` — never create real bots in API tests
4. Test both success and error paths (404, 422, 401)

### For a new React component or hook

1. Create `{ComponentName}.test.tsx` or `{hookName}.test.ts` alongside the source file
2. Add MSW handlers for any new API endpoints the component calls
3. Test accessibility with `jest-axe` for any new UI components
4. Test all state machine transitions if the component uses `useReducer`
