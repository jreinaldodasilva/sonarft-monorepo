# Prompt 09 — Testing & Quality Assurance

**Package:** `packages/web`  
**Prompt ID:** 09-WEB-TESTING  
**Output File:** `docs/testing/test-strategy.md`  
**Reviewed:** July 2025  
**API Sources:** `packages/api` included — mock fidelity verified against real schemas

---

## Executive Summary

The test suite has a solid structural foundation — the right tools are in place (Vitest, React Testing Library, MSW v2), the mock layer is well-organised, and the hook tests for `useWebSocket`, `useConfigCheckboxes`, and `useIdleTimeout` are genuinely good. However, the suite is currently **broken**: 31 of 82 tests fail on a clean run, and the failures are caused by three distinct root-cause bugs in the tests themselves, not in the application code.

The most critical gap is coverage: `useBots` — the most complex and highest-risk hook in the codebase — has zero tests. The entire WebSocket message handling path, bot lifecycle state machine, and trade history fetch logic are untested. Combined with the broken `api.test.ts` (which covers all REST functions), the two most important test files in the project are either absent or non-functional.

**Current test results: 51 passed / 31 failed / 82 total across 10 test files.**

---

## 1. Testing Framework & Setup

### Test Runner

**Vitest 3.0** — configured in `vite.config.js`:

```js
test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
    css: false,
}
```

`globals: true` makes `describe`, `it`, `expect`, `vi` available without imports — consistent with the test files. `css: false` skips CSS processing in tests — correct, CSS is not needed for behaviour tests.

### Testing Library

**@testing-library/react 13.4** with **@testing-library/jest-dom 5.16** for DOM matchers. `@testing-library/user-event 13.5` is installed but not used in any test file — all interaction tests use `fireEvent` instead.

### Setup File (`setupTests.ts`)

```ts
import "@testing-library/jest-dom";
import { vi } from "vitest";

vi.mock("netlify-identity-widget", () => ({
    default: {
        init: vi.fn(), on: vi.fn(), off: vi.fn(),
        open: vi.fn(), logout: vi.fn(),
        currentUser: vi.fn(() => null),
    },
}));

import { server } from "./mocks/server";
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

**Strengths:**
- `netlify-identity-widget` is globally mocked — prevents real auth calls in all tests ✅
- MSW server is started/reset/stopped correctly around all tests ✅
- `onUnhandledRequest: "warn"` surfaces unexpected fetch calls without failing tests ✅

**Issue:** `onUnhandledRequest: "warn"` should be `"error"` in a mature test suite. Unhandled requests indicate missing mocks — warning silently allows tests to pass with incomplete mock coverage.

### CI/CD Integration

No CI configuration file was found (`cloudbuild.yaml` exists in the web package but contains only a Docker build step — no test execution). Tests are not run in CI. This means the 31 failing tests have gone undetected.

---

## 2. Unit Test Coverage

### Test File Inventory

| Test file | Tests | Passing | Failing | Status |
|---|---|---|---|---|
| `src/hooks/useWebSocket.test.tsx` | 11 | 10 | 1 | ⚠️ 1 failure |
| `src/hooks/useConfigCheckboxes.test.ts` | 7 | 6 | 1 | ⚠️ 1 failure |
| `src/hooks/useIdleTimeout.test.ts` | 5 | 5 | 0 | ✅ All pass |
| `src/components/ErrorBoundary/ErrorBoundary.test.tsx` | 4 | 3 | 1 | ⚠️ 1 failure |
| `src/components/PrivateRoute/PrivateRoute.test.tsx` | 3 | 3 | 0 | ✅ All pass |
| `src/components/Bots/TradeHistoryTable.test.tsx` | 5 | 5 | 0 | ✅ All pass |
| `src/App.test.tsx` | 4 | 3 | 1 | ⚠️ 1 failure |
| `src/utils/api.test.ts` | 22 | 0 | 22 | ❌ All fail |
| `src/integration/workflows.test.tsx` | 9 | 8 | 1 | ⚠️ 1 failure |
| `src/utils/helpers.test.ts` | — | — | — | ⚠️ Not found in run |
| **Total** | **82** | **51** | **31** | **62% pass rate** |

### Coverage by Source File

| Source file | Has tests | Test quality | Gap |
|---|---|---|---|
| `hooks/useWebSocket.tsx` | ✅ Yes | High | 1 failing test |
| `hooks/useConfigCheckboxes.ts` | ✅ Yes | High | 1 failing test |
| `hooks/useIdleTimeout.ts` | ✅ Yes | High | None |
| `hooks/AuthProvider.tsx` | ❌ No | — | Entire file untested |
| `hooks/useBots.ts` | ❌ No | — | **Entire file untested** |
| `utils/api.ts` | ✅ Yes | High (design) | **All 22 tests failing** |
| `utils/helpers.ts` | ✅ Yes | Unknown | Not confirmed running |
| `utils/constants.ts` | ❌ No | — | Trivial, low priority |
| `utils/vitals.ts` | ❌ No | — | Low priority |
| `components/ErrorBoundary` | ✅ Yes | High | 1 failing test |
| `components/PrivateRoute` | ✅ Yes | High | None |
| `components/Bots/TradeHistoryTable` | ✅ Yes | High | None |
| `components/Bots/Bots` | ❌ No | — | Untested |
| `components/Bots/BotControls` | ❌ No | — | Untested |
| `components/Bots/BotConsole` | ❌ No | — | Untested |
| `components/Charts/ProfitChart` | ❌ No | — | Untested |
| `components/Indicators/Indicators` | ⚠️ Integration only | Medium | No unit test |
| `components/Parameters/Parameters` | ⚠️ Integration only | Medium | No unit test |
| `components/NavBar/NavBar` | ❌ No | — | Untested |
| `components/CryptoTicker/CryptoTicker` | ❌ No | — | Untested |
| `pages/Crypto/Crypto` | ❌ No | — | Untested |

**Estimated line coverage: ~35-45%** (based on tested vs untested files). The two most critical untested areas are `useBots` and `utils/api.ts` (all tests broken).

---

## 3. The Three Root-Cause Test Failures

All 31 test failures trace back to three distinct bugs. None are caused by application code regressions.

### Root Cause 1 — `api.test.ts`: `global.fetch` mock incompatible with Vitest globals (22 failures)

```ts
// api.test.ts line 7
global.fetch = vi.fn() as unknown as typeof fetch;

// line 23
vi.mocked(fetch).mockClear();  // ← TypeError: vi.mocked(...).mockClear is not a function
```

`global.fetch = vi.fn()` assigns a new `vi.fn()` to `global.fetch`, but `vi.mocked(fetch)` looks up the mock by the `fetch` identifier in the current module scope — which is the original `fetch`, not the reassigned global. The mock is not registered with Vitest's mock registry, so `vi.mocked()` returns the original function which has no `.mockClear()`.

**Fix:** Use `vi.stubGlobal` instead:
```ts
beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
});
afterEach(() => {
    vi.unstubAllGlobals();
});
```

### Root Cause 2 — `ErrorBoundary.test.tsx`: Reset test assumes `handleReload` re-mounts children (1 failure)

```ts
// ErrorBoundary.test.tsx
fireEvent.click(screen.getByRole("button", { name: /try again/i }));
rerender(<ErrorBoundary><ThrowingComponent shouldThrow={false} /></ErrorBoundary>);
expect(screen.getByText("Normal content")).toBeInTheDocument();  // ← fails
```

`handleReload` calls `setState({ hasError: false, error: null })`. In the test environment (Vitest + jsdom), the error boundary's `getDerivedStateFromError` is triggered during the initial render and the error state persists. After clicking "Try again", the state resets but the `ThrowingComponent` with `shouldThrow={false}` is not re-mounted — the `rerender` call updates props but the component tree is already in an error state from the previous render cycle.

**Fix:** Unmount and remount the component after clicking "Try again":
```ts
const { unmount } = render(<ErrorBoundary>...</ErrorBoundary>);
fireEvent.click(screen.getByRole("button", { name: /try again/i }));
unmount();
render(<ErrorBoundary><ThrowingComponent shouldThrow={false} /></ErrorBoundary>);
expect(screen.getByText("Normal content")).toBeInTheDocument();
```

### Root Cause 3 — `useWebSocket.test.tsx`: Socket close assertion timing (1 failure)

```ts
// useWebSocket.test.tsx
it("closes the socket on unmount", () => {
    const { unmount } = renderHook(() => useWebSocket("ws://test"));
    act(() => { mockWsInstance.onopen?.(); });
    unmount();
    expect(mockWsInstance.close).toHaveBeenCalled();  // ← fails
});
```

The `useWebSocket` cleanup uses a functional `setSocket` updater to close the socket:
```ts
setSocket((currentSocket) => {
    if (currentSocket) currentSocket.close();
    return null;
});
```

The functional updater is called asynchronously by React's state batching. By the time `expect` runs, the updater may not have executed yet. The test needs to wrap the unmount in `act` to flush pending state updates:
```ts
act(() => { unmount(); });
expect(mockWsInstance.close).toHaveBeenCalled();
```

### Root Cause 4 — `useConfigCheckboxes.test.ts`: Save status timer not flushed (1 failure)

```ts
it("sets saveStatus to saved on successful update", async () => {
    await act(async () => { await result.current.handleSave(); });
    expect(result.current.saveStatus).toBe("saved");  // ← fails
});
```

`handleSave` sets `saveStatus = "saved"` then schedules `setTimeout(() => setSaveStatus(null), 3000)`. The test uses real timers — after `handleSave` resolves, the `setTimeout` fires immediately in the test environment and clears `saveStatus` back to `null` before the assertion runs.

**Fix:** Use fake timers:
```ts
beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); });

it("sets saveStatus to saved on successful update", async () => {
    await act(async () => { await result.current.handleSave(); });
    expect(result.current.saveStatus).toBe("saved");
    act(() => { vi.advanceTimersByTime(3000); });
    expect(result.current.saveStatus).toBeNull();
});
```

### Root Cause 5 — `App.test.tsx`: Lazy-loaded route not rendered (1 failure)

```ts
it("renders the Crypto navigation link", async () => {
    render(<App />);
    await waitFor(() =>
        expect(screen.getByRole("link", { name: /crypto/i })).toBeInTheDocument()
    );
});
```

The NavBar renders a `<Link>` to `/crypto` with `<h1>Crypt<span>o</span></h1>` as its content. The accessible name computed by the browser is "Crypto" but the text is split across elements. `getByRole("link", { name: /crypto/i })` may fail because the accessible name computation in jsdom differs from the browser. The test should use `getByText` or a more specific selector.

### Root Cause 6 — `workflows.test.tsx`: Stale MSW handler URL (1 failure)

```ts
server.use(
    http.post("http://localhost:5000/bot/set_parameters/:clientId", () =>
        HttpResponse.json({ error: "Server error" }, { status: 500 })
    )
);
```

The actual endpoint is `PUT http://localhost:8000/api/v1/parameters?client_id=`. The test uses the old URL (`localhost:5000`, old path, wrong method). The override handler never matches, so the default handler returns 200, and the "error feedback" test never sees an error.

---

## 4. Integration Tests

### Coverage

`workflows.test.tsx` covers:

| Workflow | Covered | Quality |
|---|---|---|
| Parameters load from server | ✅ | Good |
| Parameters save success | ✅ | Good |
| Parameters save error | ⚠️ | Broken (stale URL) |
| Parameters server 500 fallback | ✅ | Good |
| Indicators load from server | ✅ | Good |
| Indicators save success | ✅ | Good |
| PrivateRoute auth gate (authenticated) | ✅ | Good |
| PrivateRoute auth gate (unauthenticated) | ✅ | Good |
| Bot creation flow | ❌ | Missing |
| WebSocket event handling | ❌ | Missing |
| Trade history display | ❌ | Missing |
| Login/logout flow | ❌ | Missing |

### API Mock Fidelity

MSW handlers in `mocks/handlers.ts` match the current API endpoints correctly:

| Handler | Endpoint | Method | Matches API? |
|---|---|---|---|
| `GET /bots` | `/bots` | GET | ✅ |
| `GET /bots/:botId/orders` | `/bots/{botId}/orders` | GET | ✅ |
| `GET /bots/:botId/trades` | `/bots/{botId}/trades` | GET | ✅ |
| `GET /parameters/defaults` | `/parameters/defaults` | GET | ✅ |
| `GET /parameters` | `/parameters` | GET | ✅ |
| `PUT /parameters` | `/parameters` | PUT | ✅ |
| `GET /indicators/defaults` | `/indicators/defaults` | GET | ✅ |
| `GET /indicators` | `/indicators` | GET | ✅ |
| `PUT /indicators` | `/indicators` | PUT | ✅ |

All MSW handlers correctly reflect the current API. The stale URLs are only in the test assertions and override handlers, not in the base handlers. ✅

### WebSocket Integration Testing

No WebSocket integration tests exist. MSW v2 supports WebSocket mocking via `ws` from `msw` — this is not used. The entire bot lifecycle flow (create → run → log stream → trade → history) is untested at the integration level.

---

## 5. API / Service Tests (`utils/api.test.ts`)

All 22 tests in `api.test.ts` fail due to Root Cause 1 (`global.fetch` mock incompatibility). The test design is otherwise good:

**What the tests cover (when fixed):**
- `getAuthToken` — null when no user logged in
- `getBotIds` — success, auth header injection, HTTP error, network failure
- `getOrders` / `getTrades` — success, non-ok response, network failure
- `getDefaultParameters` / `getDefaultIndicators` — success, HTTP error fallback, network failure fallback
- `getParameters` / `getIndicators` — success, HTTP error, network failure
- `updateParameters` / `updateIndicators` — success with body, HTTP error

**Stale URL assertions** (noted in Prompt 02) — these tests assert against old endpoint paths:
```ts
expect.stringContaining("/botids/client_123")           // actual: /bots?client_id=client_123
expect.stringContaining("/bot/set_parameters/client_123") // actual: /parameters?client_id=client_123
expect.stringContaining("/bot/set_indicators/client_123") // actual: /indicators?client_id=client_123
```
These assertions would pass even after fixing the `vi.stubGlobal` issue because `stringContaining` only checks for substring presence — and the mock `fetch` resolves regardless of URL. The URL assertions are wrong but non-blocking.

---

## 6. Hook Tests

### `useWebSocket` — 10/11 passing

Well-structured tests covering all major scenarios. The one failure (socket close on unmount) is a timing issue fixable with `act(() => { unmount(); })`.

**Missing coverage:**
- URL change causes reconnection (effect re-runs with new URL)
- `wsError` persists correctly after `onerror` + `onclose` sequence
- Backoff cap at 30 seconds

### `useConfigCheckboxes` — 6/7 passing

Good coverage of the three-tier loading fallback, checkbox interaction, and save flow. The one failure (save status timer) is fixable with fake timers.

**Missing coverage:**
- `clientId` change triggers re-fetch
- Concurrent save requests (double-click)
- `stateKeys` filtering (only specified keys are copied from server response)

### `useIdleTimeout` — 5/5 passing ✅

Complete coverage. All scenarios tested correctly with fake timers.

### `useBots` — 0 tests ❌

The highest-priority testing gap. The hook manages:
- WebSocket message dispatch (5 event types)
- Bot lifecycle state machine
- REST fetch triggers
- Simulation mode toggle
- Log accumulation and capping

None of this is tested. A `useBots` test suite should mock `useWebSocket` and `utils/api` and simulate each WS event type.

### `AuthProvider` — 0 tests ❌

No tests for the auth context, Netlify Identity event handling, or idle timeout integration.

---

## 7. Snapshot Testing

No snapshot tests are used anywhere in the codebase. This is the correct decision — snapshot tests are brittle, require frequent updates, and provide low signal for behaviour regressions. The test suite correctly focuses on behaviour-based assertions. ✅

---

## 8. Test Data & Fixtures

### `mocks/fixtures.ts`

Well-structured typed fixture data:

```ts
export const mockUser: MockUser = { id: "user_abc123", email: "test@example.com", token: { access_token: "mock-jwt-token" } };
export const mockBotIds: string[] = ["bot_001", "bot_002"];
export const mockOrder: TradeRecord = { timestamp: "2025-01-01T00:00:00Z", position: "LONG", ... };
export const mockTrade: TradeRecord = { ... };
export const mockParameters: ParametersConfig = { exchanges: { Binance: true, Okx: false, Kraken: false }, symbols: { "BTC/USDT": true, "ETH/USDT": false } };
export const mockIndicators: IndicatorsConfig = { periods: { "5min": true, "15min": false }, oscillators: { ... }, movingaverages: { ... } };
export const mockResponse = (body, ok = true, status = 200) => ({ ok, status, json: async () => body });
```

**Strengths:**
- All fixtures are TypeScript-typed against the actual interfaces ✅
- `mockResponse` helper reduces boilerplate in `api.test.ts` ✅
- Fixture data is realistic (real exchange names, real symbol pairs, real indicator names) ✅

**Gaps:**
- `mockOrder` and `mockTrade` use the frontend `TradeRecord` interface which is missing 7 fields from the API schema (fee data, executed amount) — noted in Prompt 02. Fixtures should be updated when the interface is fixed.
- No fixture for WebSocket events (`WsBotCreatedEvent`, `WsLogEvent`, etc.)
- No fixture for error responses (e.g., `{ detail: "Bot not found" }`)
- No factory functions — fixtures are single static objects. Tests that need variations must spread and override manually.

### Mock Fidelity vs API Schema

| Fixture | Matches API schema? | Notes |
|---|---|---|
| `mockOrder` / `mockTrade` | ⚠️ Partial | Missing 7 fee/execution fields |
| `mockParameters` | ✅ Exact | Matches `ParametersConfig` Pydantic model |
| `mockIndicators` | ✅ Exact | Matches `IndicatorsConfig` Pydantic model |
| `mockBotIds` | ✅ Exact | Matches `BotListResponse.botids` |
| WS event fixtures | ❌ Missing | No fixtures for any WS event type |

---

## 9. Test Organisation

### File Co-location

Tests are co-located with their source files:
- `components/Bots/TradeHistoryTable.test.tsx` next to `TradeHistoryTable.tsx` ✅
- `hooks/useWebSocket.test.tsx` next to `useWebSocket.tsx` ✅
- `utils/api.test.ts` next to `api.ts` ✅

Integration tests are in a dedicated `src/integration/` directory. ✅

### Test Naming

Test names follow a consistent `describe > it` pattern with descriptive names:
```ts
describe("useWebSocket — connection", () => {
    it("opens a WebSocket connection on mount", () => { ... });
    it("sets wsOpen to true when connection opens", () => { ... });
});
```

Names describe behaviour, not implementation. ✅

### AAA Pattern

Tests generally follow Arrange-Act-Assert:
```ts
// Arrange
mockFetchFn.mockResolvedValueOnce(mockParameters);
const { result } = renderHook(() => useConfigCheckboxes(defaultConfig));

// Act
await waitFor(() => expect(result.current.config.exchanges).toBeDefined());
act(() => { result.current.handleCheckboxChange(...); });

// Assert
expect(result.current.config.exchanges.Okx).toBe(true);
```

✅ Consistent throughout.

### Test Duplication

Minor duplication in `TradeHistoryTable.test.tsx`:
```ts
it("renders empty tbody when rows is empty", () => { ... });
it("renders empty tbody when rows defaults", () => { ... });
```
Both tests render `<TradeHistoryTable rows={[]} />` and assert the same thing. One should be removed.

---

## 10. Error & Edge Case Testing

### Covered Error Scenarios

| Scenario | Tested | File |
|---|---|---|
| `getOrders` returns null on 404 | ✅ | `api.test.ts` (broken) |
| `getOrders` returns null on network failure | ✅ | `api.test.ts` (broken) |
| `getBotIds` throws on 500 | ✅ | `api.test.ts` (broken) |
| `getBotIds` throws on network failure | ✅ | `api.test.ts` (broken) |
| Config fetch falls back to localStorage | ✅ | `useConfigCheckboxes.test.ts` |
| Config fetch falls back to defaults | ✅ | `useConfigCheckboxes.test.ts` |
| Save fails → `saveStatus = "error"` | ✅ | `useConfigCheckboxes.test.ts` |
| WS connection error sets `wsError` | ✅ | `useWebSocket.test.tsx` |
| WS does not reconnect after unmount | ✅ | `useWebSocket.test.tsx` |
| ErrorBoundary catches render errors | ✅ | `ErrorBoundary.test.tsx` |
| PrivateRoute redirects unauthenticated | ✅ | `PrivateRoute.test.tsx` |

### Missing Error Scenarios

| Scenario | Priority |
|---|---|
| `useBots`: `bot_created` WS event → state transitions | **High** |
| `useBots`: `bot_removed` WS event → state reset | **High** |
| `useBots`: `order_success` → `fetchAllOrders` called | **High** |
| `useBots`: `error` WS event (currently unhandled) | **High** |
| `useBots`: `getBotIds` fails after `bot_created` | **High** |
| `useBots`: `set_simulation` missing `botid` | **High** |
| `AuthProvider`: login event sets user | Medium |
| `AuthProvider`: logout event clears user | Medium |
| `AuthProvider`: idle timeout triggers logout | Medium |
| `CryptoTicker`: CoinGecko fetch failure | Low |
| `ProfitChart`: empty trades array | ✅ Covered by component render |
| `TradeHistoryTable`: very large dataset | Low |

### Boundary Conditions

- Log cap at 500 lines — not tested
- Bot limit (5 per client) — not tested
- Empty `botIds` array — not tested
- `selectedBotId = null` when no bots exist — not tested

---

## 11. Accessibility Testing

No automated accessibility tests exist. No `jest-axe` or `@axe-core/react` is installed or used.

The accessibility violations identified in Prompt 07 (multiple `<main>` elements, missing `aria-live`, contrast failures, invalid HTML nesting) would all be catchable with automated a11y testing.

**Recommended addition:**
```bash
npm install --save-dev @axe-core/react
# or for unit tests:
npm install --save-dev jest-axe
```

Example usage with Testing Library:
```ts
import { axe, toHaveNoViolations } from "jest-axe";
expect.extend(toHaveNoViolations);

it("has no accessibility violations", async () => {
    const { container } = render(<TradeHistoryTable rows={[mockOrder]} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
});
```

---

## 12. Visual Regression Testing

No visual regression testing is configured. No Storybook, Percy, Chromatic, or Playwright visual comparison.

For a trading interface where visual clarity is important (status badges, P&L chart colours, error states), visual regression testing would catch unintended style changes. This is a low-priority addition for the current stage.

---

## 13. Performance Testing

No performance tests, bundle size assertions, or render timing benchmarks exist.

**Recommended addition to `vite.config.js`:**
```js
build: {
    chunkSizeWarningLimit: 100, // warn if chunk > 100KB
}
```

This would have flagged the 379KB and 339KB chunks during development.

---

## 14. Test Execution & CI/CD

### Current State

- Tests run locally with `npm test` (alias for `vitest run`)
- Watch mode available with `npm run test:watch`
- No CI pipeline runs tests
- No coverage thresholds configured
- No test timeout configured (Vitest default: 5000ms per test)
- Total test suite duration: **19.72 seconds** (including 13.33s setup time)

### Setup Time Analysis

The 13.33s setup time is dominated by MSW server initialisation and the jsdom environment setup. This is high for 82 tests. Potential causes:
- `netlify-identity-widget` mock setup
- jsdom environment initialisation per test file
- MSW server start/stop overhead

### CI Recommendation

Add to `cloudbuild.yaml` or a new `.github/workflows/test.yml`:
```yaml
- name: Run tests
  run: npm ci && npm test
  
- name: Check for test failures
  run: npm test -- --reporter=junit --outputFile=test-results.xml
```

---

## 15. Testing Issues Summary

| # | Issue | Severity | Description | Impact |
|---|---|---|---|---|
| 1 | `api.test.ts` — all 22 tests fail | **Critical** | `global.fetch = vi.fn()` incompatible with `vi.mocked()` | Entire REST API layer untested |
| 2 | `useBots` has zero tests | **Critical** | Most complex hook — WS handling, bot lifecycle, history fetch all untested | Highest-risk code path has no safety net |
| 3 | No CI pipeline runs tests | **High** | 31 failing tests undetected in repository | Regressions ship undetected |
| 4 | `ErrorBoundary` reset test fails | **Medium** | `rerender` after reset doesn't re-mount children in jsdom | Reset behaviour untested |
| 5 | `useWebSocket` socket-close test fails | **Medium** | `unmount()` not wrapped in `act()` | Cleanup behaviour partially untested |
| 6 | `useConfigCheckboxes` save-status test fails | **Medium** | Real timers race with `setTimeout` in `handleSave` | Save feedback timing untested |
| 7 | `workflows.test.tsx` error test uses stale URL | **Medium** | `localhost:5000/bot/set_parameters/` — wrong host, path, method | Error feedback path untested |
| 8 | `App.test.tsx` nav link test fails | **Low** | `getByRole("link", { name: /crypto/i })` fails on split text | Minor — nav link presence untested |
| 9 | No WebSocket integration tests | **High** | Bot lifecycle flow entirely untested at integration level | Core feature has no integration coverage |
| 10 | No `AuthProvider` tests | **Medium** | Login/logout/idle timeout untested | Auth flow has no safety net |
| 11 | No accessibility tests | **Medium** | Known WCAG violations not caught automatically | A11y regressions undetected |
| 12 | `onUnhandledRequest: "warn"` instead of `"error"` | **Low** | Missing mocks silently pass | Incomplete mock coverage undetected |
| 13 | `@testing-library/user-event` installed but unused | **Low** | `fireEvent` used instead of `userEvent` | Less realistic interaction simulation |
| 14 | WS event fixtures missing | **Low** | No typed fixtures for `WsBotCreatedEvent`, `WsLogEvent`, etc. | WS tests harder to write |
| 15 | Duplicate test in `TradeHistoryTable.test.tsx` | **Low** | Two identical empty-rows tests | Minor noise |

---

## 16. Testing Recommendations

**Priority 1 — Fix broken tests immediately**

1. **Fix `api.test.ts`** — replace `global.fetch = vi.fn()` with `vi.stubGlobal`:
   ```ts
   beforeEach(() => { vi.stubGlobal("fetch", vi.fn()); });
   afterEach(() => { vi.unstubAllGlobals(); });
   ```
   Also update the three stale URL assertions to match current endpoints.

2. **Fix `useWebSocket` socket-close test** — wrap unmount in `act`:
   ```ts
   act(() => { unmount(); });
   expect(mockWsInstance.close).toHaveBeenCalled();
   ```

3. **Fix `useConfigCheckboxes` save-status test** — add `vi.useFakeTimers()`.

4. **Fix `ErrorBoundary` reset test** — unmount and remount after clicking "Try again".

5. **Fix `workflows.test.tsx` error test** — update MSW override to use current URL and method.

**Priority 2 — Write missing critical tests**

6. **Write `useBots` unit tests** — mock `useWebSocket` and `utils/api`, simulate each WS event:
   ```ts
   vi.mock("./useWebSocket", () => ({
       default: vi.fn(() => ({ socket: mockSocket, wsOpen: true, wsError: null }))
   }));
   vi.mock("../utils/api", () => ({ getBotIds: vi.fn(), ... }));
   ```

7. **Write `AuthProvider` tests** — mock `netlify-identity-widget` events, test user state transitions.

8. **Add WebSocket integration tests** — use MSW v2 `ws` handler to simulate the bot creation flow.

**Priority 3 — Infrastructure**

9. **Add tests to CI** — add `npm test` step to `cloudbuild.yaml` or create a GitHub Actions workflow.

10. **Add accessibility tests** — install `jest-axe` and add a11y assertions to component tests.

11. **Change `onUnhandledRequest: "warn"` to `"error"`** in `setupTests.ts`.

12. **Add WS event fixtures** to `mocks/fixtures.ts` for use in future `useBots` tests.
