# Testing & Quality Assurance
**Prompt:** 09-WEB-TESTING | **Package:** web | **Reviewed:** July 2025

---

## Executive Summary

The sonarftweb test suite is well-structured, behaviorally focused, and
comprehensive for the hooks and utility layer. All 105 tests pass in 20.55s.
The MSW v2 mock strategy is robust — tests exercise real `fetch` code paths
rather than mocking module imports. Hook tests are thorough, covering happy
paths, error paths, edge cases, cleanup, and reconnection backoff. The main
gaps are: no direct component tests for `Bots`, `Parameters`, `ConfigCheckboxPanel`,
and `ProfitChart`; no accessibility tests (`jest-axe` or equivalent); no
coverage reporting configured; and the `TradeHistoryTable` test is missing a
`caption` prop (the component requires it). The README claims 110/110 passing
but the live run shows 105/105 — a minor discrepancy worth investigating.

---

## 1. Testing Framework & Setup

**Test runner:** Vitest 3.x — configured in `vite.config.js`:

```javascript
test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
    css: false,
}
```

**Testing library:** React Testing Library (`@testing-library/react` 13.x) +
`@testing-library/jest-dom` 5.x for custom matchers.

**User event:** `@testing-library/user-event` 13.x is listed as a dependency
but is not used in any test file — all interactions use `fireEvent` directly.

**Test environment:** `jsdom` (via Vitest's built-in jsdom integration). CSS
is disabled (`css: false`) — styles are not applied in tests, which is correct
for behavioral testing.

**Global setup (`setupTests.ts`):**

```typescript
import "@testing-library/jest-dom";
import { server } from "./mocks/server";
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

MSW server starts before all tests, resets handlers after each test (preventing
handler leakage between tests), and closes after all tests. ✅

**CI/CD integration:** Tests run in GitHub Actions on every push/PR
(`.github/workflows/ci.yml`). The CI pipeline runs `npm test` and
`npm audit --audit-level=high`. ✅

**Test execution time:** 20.55s total (2.64s test execution, 14.47s setup,
24.56s environment). The setup time is dominated by jsdom initialization —
normal for a Vitest + jsdom configuration.

---

## 2. Unit Test Coverage

No coverage report is configured (`coverage` is not set in `vite.config.js`).
The following is a file-by-file assessment based on test file inventory.

### Coverage by file

| File | Test file | Estimated coverage | Notes |
|---|---|---|---|
| `hooks/useBots.ts` | `useBots.test.ts` | High | All WS events, all handlers, load, error paths |
| `hooks/useWebSocket.tsx` | `useWebSocket.test.tsx` | High | Connect, error, cleanup, backoff |
| `hooks/AuthProvider.tsx` | `AuthProvider.test.tsx` | High | Initial state, login, logout |
| `hooks/useConfigCheckboxes.ts` | `useConfigCheckboxes.test.ts` | High | Load chain, checkbox, save, error |
| `hooks/useIdleTimeout.ts` | `useIdleTimeout.test.ts` | High | Timer, activity, disable, cleanup |
| `utils/api.ts` | `api.test.ts` | High | All functions, success + error paths |
| `utils/helpers.ts` | `helpers.test.ts` | High | Parallel fetch, null filtering, empty |
| `components/ErrorBoundary/ErrorBoundary.tsx` | `ErrorBoundary.test.tsx` | High | Render, catch, reset |
| `components/PrivateRoute/PrivateRoute.tsx` | `PrivateRoute.test.tsx` | High | Auth guard, redirect |
| `components/Bots/TradeHistoryTable.tsx` | `TradeHistoryTable.test.tsx` | Medium | Headers, rows, empty — no formatting tests |
| `App.tsx` | `App.test.tsx` | Low | Smoke test only |
| `components/Bots/Bots.tsx` | None | ❌ None | Modal logic, status badges untested |
| `components/Bots/BotControls.tsx` | None | ❌ None | Button states, disabled logic untested |
| `components/Bots/BotConsole.tsx` | None | ❌ None | Log rendering, scroll untested |
| `components/Parameters/Parameters.tsx` | Via integration | Partial | Load + save covered; checkbox interaction not |
| `components/Indicators/Indicators.tsx` | Via integration | Partial | Load + save covered |
| `components/ConfigCheckboxPanel/ConfigCheckboxPanel.tsx` | None | ❌ None | Generic panel rendering untested |
| `components/Charts/ProfitChart.tsx` | None | ❌ None | Chart rendering, empty state untested |
| `components/NavBar/NavBar.tsx` | Via App.test | Minimal | Logo alt text only |
| `components/Footer/Footer.tsx` | None | ❌ None | |
| `utils/vitals.ts` | None | ❌ None | |
| `utils/constants.ts` | None | ❌ None | Trivial — env var reads |

**Coverage requirement:** None configured. No minimum threshold enforced.

**Test count discrepancy:** The README states "110/110 passing" but the live
run shows **105/105 passing** across 12 test files. The 5-test difference
suggests either tests were removed after the README was last updated, or the
README count was written before some tests were removed. This should be
reconciled.

---

## 3. Component Tests

### Components with dedicated tests

**`ErrorBoundary`** (4 tests) — behavioral, not snapshot:
- Renders children normally ✅
- Shows fallback UI on error ✅
- Hides children in error state ✅
- Resets on "Try again" click ✅

**`PrivateRoute`** (3 tests):
- Renders children when value is truthy ✅
- Redirects when value is null ✅
- Redirects when value is undefined ✅

**`TradeHistoryTable`** (5 tests):
- Renders headers ✅
- Renders rows ✅
- Empty tbody on empty rows ✅
- Symbol formatted as `base/quote` ✅
- Missing: `caption` prop not passed in tests — the component signature
  requires `caption: string` but the test calls `<TradeHistoryTable rows={[]} />`
  without it. TypeScript would catch this at compile time but the test passes
  at runtime because the prop is only used in a `<caption>` element. ⚠️

**`App`** (3 tests — smoke):
- Renders without crashing ✅
- Logo alt text ✅
- Dashboard nav link ✅

### Components without dedicated tests

`Bots`, `BotControls`, `BotConsole`, `ConfigCheckboxPanel`, `ProfitChart`,
`NavBar`, `Footer` have no dedicated test files. `Parameters` and `Indicators`
are covered by integration tests but not unit tests.

**Mock strategy for component tests:** `vi.mock` for module-level dependencies
(`useWebSocket`, `api`, `helpers`). `vi.stubGlobal("WebSocket", ...)` for the
native WebSocket API. MSW v2 for network-level mocking in integration tests.

---

## 4. Integration Tests

**File:** `src/integration/workflows.test.tsx`

**Scope:** Renders real components against MSW-mocked API endpoints. Tests
user-visible behavior (text on screen, button clicks, feedback messages).

### Test scenarios covered

| Scenario | Tests | Coverage |
|---|---|---|
| Parameters load from server | ✅ | Exchange names visible after mount |
| Parameters save success | ✅ | "✓ Saved" shown after button click |
| Parameters save failure (500) | ✅ | "✗ Error — try again" shown |
| Parameters server 500 on load | ✅ | Graceful fallback — panel still renders |
| Indicators load from server | ✅ | Period names visible after mount |
| Indicators save success | ✅ | "✓ Saved" shown |
| PrivateRoute auth gate | ✅ | Children shown/hidden based on value |

### Test scenarios not covered

| Missing scenario | Impact |
|---|---|
| Bot creation workflow (create → bot_created event → status change) | High — core user workflow |
| Bot removal workflow (remove → confirmation → bot_removed event) | High |
| Live trading mode toggle (paper → confirmation modal → live) | High — safety-critical flow |
| WebSocket reconnection in integration context | Medium |
| Config checkbox interaction → save → server update | Medium |
| Trade history display after `trade_success` event | Medium |
| Error banner display on WS disconnect | Low |

The integration tests cover the config panels well but do not test the bot
management workflow at all. The `Bots` component — the most complex and
safety-critical part of the UI — has no integration test coverage.

---

## 5. API / Service Tests

**File:** `src/utils/api.test.ts`

**Mock strategy:** `vi.stubGlobal("fetch", vi.fn())` — stubs the global `fetch`
function directly. Uses `mockResponse` fixture helper to construct mock
`Response`-like objects.

### Coverage

| Function | Success | HTTP error | Network error | Auth header |
|---|---|---|---|---|
| `getAuthToken` | ✅ | N/A | N/A | N/A |
| `getBotIds` | ✅ | ✅ (500) | ✅ | ✅ |
| `getOrders` | ✅ | ✅ (404) | ✅ | — |
| `getTrades` | ✅ | ✅ (404) | ✅ | — |
| `getDefaultParameters` | ✅ | ✅ (fallback) | ✅ (fallback) | — |
| `getParameters` | ✅ | ✅ (404) | ✅ | — |
| `updateParameters` | ✅ | ✅ (500) | — | — |
| `getDefaultIndicators` | ✅ | ✅ (fallback) | ✅ (fallback) | — |
| `getIndicators` | ✅ | ✅ (404) | — | — |
| `updateIndicators` | ✅ | ✅ (500) | — | — |
| `fetchWsTicket` | — | — | — | — |

**`fetchWsTicket` not tested** — the WS ticket fetch function has no test
coverage. It is mocked in `useBots.test.ts` but never tested directly.

**Request body validation:** `updateParameters` and `updateIndicators` tests
verify the request body is `JSON.stringify(mockParameters/mockIndicators)`. ✅

**Auth header test:** Only `getBotIds` tests the `Authorization` header
injection. Other functions that also inject auth headers (`getOrders`,
`getTrades`, `updateParameters`, etc.) do not have auth header tests.

---

## 6. Hook Tests

### useBots (27 tests)

The most comprehensive test file. Covers:

| Category | Tests |
|---|---|
| Initial load | Fetch on mount, error handling, WS ticket URL resolution, fallback URL |
| `bot_created` event | Bot list re-fetch, `selectedBotId` update, status transition |
| `bot_removed` event | State reset, `botState`/`botStatus` values |
| `order_success` event | `fetchAllOrders` called with correct bot IDs |
| `trade_success` event | `fetchAllTrades` called with correct bot IDs |
| `error` event | `fetchError` set from message, fallback message |
| `log` event | Log appended, 500-line cap, non-JSON fallback |
| `handleCreate` | WS send payload, error when disconnected |
| `handleRemove` | WS send payload, no-op when no bot selected |
| `handleToggleSimulation` | WS send payload with value, no-op when no bot |

**Notable test:** The log cap test sends 510 messages and verifies
`logs.length <= 500`. The RAF flush is simulated with `setTimeout(r, 50)` —
a pragmatic workaround for jsdom not running `requestAnimationFrame`. ✅

**Missing:** `handleStop` is not tested (no test for the stop command payload).

### useWebSocket (11 tests)

Covers connection, error handling, cleanup (memory leak prevention), and
exponential backoff. The backoff test verifies the exact timing (1000ms first
delay, 2000ms second delay). ✅

**`vi.useFakeTimers()`** used throughout — correct for testing time-dependent
reconnection logic. ✅

### AuthProvider (5 tests)

Covers initial state, logout, and login-after-logout. Uses a `TestConsumer`
component to observe context values — the correct RTL pattern. ✅

### useConfigCheckboxes (8 tests)

Covers all three load tiers (server, localStorage, defaults), synchronous
localStorage hydration, checkbox change + localStorage write, save success,
and save error. ✅

**`vi.useFakeTimers()`** used for save feedback timeout test. ✅

### useIdleTimeout (5 tests)

Covers timer fire, disabled state, activity reset, mid-session disable, and
cleanup (event listener removal + timer cancellation). ✅

---

## 7. Snapshot Testing

**Snapshot tests:** None. The test suite uses behavioral assertions
(`getByRole`, `getByText`, `toBeInTheDocument`) rather than snapshots.

**Assessment:** This is the correct approach. Snapshot tests are brittle —
they break on any markup change, including cosmetic ones, and provide little
signal about behavioral regressions. The behavioral tests in this suite are
more valuable and more maintainable than snapshots would be. ✅

---

## 8. Test Data & Fixtures

**File:** `src/mocks/fixtures.ts`

### Fixture inventory

| Fixture | Type | Realistic? |
|---|---|---|
| `mockUser` | `MockUser` | ✅ — valid id, email, token structure |
| `mockBotIds` | `string[]` | ✅ — `["bot_001", "bot_002"]` |
| `mockOrder` | `TradeRecord` | ✅ — complete record with all fields, ISO timestamp |
| `mockTrade` | `TradeRecord` | ✅ — different exchange pair (ETH/USDT) |
| `mockParameters` | `ParametersConfig` | ✅ — realistic exchange/symbol/strategy values |
| `mockIndicators` | `IndicatorsConfig` | ✅ — realistic period/oscillator/MA values |
| `mockResponse` | Helper function | ✅ — constructs mock `Response`-like objects |

**Type safety:** All fixtures are typed against the actual application types
(`TradeRecord`, `ParametersConfig`, `IndicatorsConfig`). TypeScript will catch
fixture drift if the types change. ✅

**Data variety:** Limited. There is one `mockOrder` and one `mockTrade`. Tests
that need multiple records spread the single fixture (e.g.
`{ ...mockOrder, buy_exchange: "okx" }`). Edge cases like negative profit,
zero profit, or legacy date formats are not represented in fixtures.

**Missing fixtures:**
- Negative profit `TradeRecord` (for profit coloring tests)
- Legacy date format `TradeRecord` (`MM-DD-YYYY` — the `formatDate` function
  handles this but it is not tested)
- Empty `ParametersConfig` / `IndicatorsConfig` (for empty state tests)
- Error response bodies (for API error message tests)

**Factory functions:** Not used. Fixtures are static objects. A factory
function (e.g. `makeTradeRecord(overrides)`) would make it easier to create
variants without spreading. Acceptable at the current fixture count.

---

## 9. Test Organization

**File organization:** Co-located with source files — `useBots.test.ts` next
to `useBots.ts`, `ErrorBoundary.test.tsx` next to `ErrorBoundary.tsx`. The
exception is `integration/workflows.test.tsx` in its own directory. ✅

**Test naming:** Descriptive `describe` + `it` blocks following the pattern
`"ComponentName — scenario" > "specific behavior"`. Examples:
- `"useBots — bot_created event" > "fetches updated bot list on bot_created"`
- `"useWebSocket — reconnect backoff" > "uses exponential backoff on repeated failures"`

Names clearly describe what is being tested and what the expected behavior is. ✅

**Test grouping:** Tests are grouped by feature/scenario within each file
using `describe` blocks. Each `describe` block covers one aspect of the
component/hook behavior. ✅

**AAA pattern:** Tests follow Arrange-Act-Assert:
- Arrange: `vi.mocked(...).mockResolvedValueOnce(...)`, `renderHook(...)`
- Act: `act(() => { ... })`, `waitFor(() => ...)`
- Assert: `expect(...).toBe(...)`, `expect(...).toHaveBeenCalledWith(...)`

**Duplication:** Minimal. The `setupWebSocketMock` helper in `useBots.test.ts`
is reused across test groups. `beforeEach` clears mocks and sets up defaults.
The `renderWithRouter` helper in `PrivateRoute.test.tsx` wraps the router
boilerplate. ✅

---

## 10. Error & Edge Case Testing

### Covered edge cases

| Edge case | Test location |
|---|---|
| Network failure on `getBotIds` | `useBots.test.ts` |
| WS ticket fetch returns null (fallback URL) | `useBots.test.ts` |
| Non-JSON WebSocket message | `useBots.test.ts` |
| Log buffer cap at 500 lines | `useBots.test.ts` |
| `handleCreate` when WS disconnected | `useBots.test.ts` |
| `handleRemove` when no bot selected | `useBots.test.ts` |
| `handleToggleSimulation` when no bot selected | `useBots.test.ts` |
| WS error event with no message field | `useBots.test.ts` |
| `useWebSocket` unmount during reconnect | `useWebSocket.test.tsx` |
| `useConfigCheckboxes` all three load tiers | `useConfigCheckboxes.test.ts` |
| `useConfigCheckboxes` save error | `useConfigCheckboxes.test.ts` |
| `useIdleTimeout` disabled mid-session | `useIdleTimeout.test.ts` |
| `fetchAllOrders` all nulls | `helpers.test.ts` |
| `fetchAllOrders` empty bot IDs | `helpers.test.ts` |
| `getOrders` network failure | `api.test.ts` |
| `ErrorBoundary` reset after error | `ErrorBoundary.test.tsx` |
| `PrivateRoute` with `undefined` value | `PrivateRoute.test.tsx` |

### Missing edge cases

| Missing edge case | Impact |
|---|---|
| `bot_stopped` event handling | Medium — currently ignored; no test documents this |
| `set_simulation` error response (rollback) | Medium — `isSimulating` drift |
| `TradeHistoryTable` with negative profit | Low — profit coloring untested |
| `TradeHistoryTable` with legacy date format | Low — `formatDate` normalization untested |
| `Parameters` server 500 on load (fallback chain) | Low — covered for Indicators but not Parameters directly |
| `fetchWsTicket` success path | Low — mocked in `useBots` but not tested directly |
| `useConfigCheckboxes` cancelled effect (clientId change) | Low — `cancelled` flag not tested |
| `useWebSocket` URL change (reconnect to new URL) | Low |

---

## 11. Accessibility Testing

**Automated a11y tests:** None. No `jest-axe`, `@axe-core/react`, or equivalent
library is used. Accessibility is verified manually and through code review
(ARIA attributes, semantic HTML, contrast ratios).

**Manual testing:** The ARIA implementation reviewed in Prompt 07 is thorough
— `role="alert"`, `role="dialog"`, `aria-modal`, `aria-labelledby`,
`aria-live`, `aria-label`, `scope="col"`, `.sr-only` captions are all present.
However, without automated tests, regressions are not caught automatically.

**WCAG coverage:** No automated WCAG coverage. The code review found one
potential WCAG issue (modal focus trap) and one heading hierarchy issue
(`<h1>` in Footer).

**Recommendation:** Add `jest-axe` to the test suite and run `axe` checks on
key components:

```typescript
import { axe, toHaveNoViolations } from "jest-axe";
expect.extend(toHaveNoViolations);

it("has no accessibility violations", async () => {
    const { container } = render(<TradeHistoryTable rows={[mockOrder]} caption="Test" />);
    expect(await axe(container)).toHaveNoViolations();
});
```

---

## 12. Visual Regression Testing

**Visual regression tests:** None. No Percy, Chromatic, Playwright screenshots,
or similar tooling is configured.

**Assessment:** For a trading dashboard with a dark theme and data-driven
tables, visual regression testing would catch unintended layout changes. Not
critical at the current scale but worth adding if the UI grows.

---

## 13. Performance Testing

**Bundle size tests:** Not automated. The Vite `chunkSizeWarningLimit: 100`
provides a build-time warning but does not fail the build.

**Runtime performance tests:** None. No render time benchmarks, no memory
leak tests.

**Recommendation:** Add a bundle size check to CI using `bundlesize` or a
custom script that reads the Vite build output and fails if any chunk exceeds
a threshold:

```bash
# In CI, after npm run build:
node -e "
const fs = require('fs');
const stats = fs.readdirSync('build/assets')
    .filter(f => f.endsWith('.js'))
    .map(f => ({ name: f, size: fs.statSync('build/assets/' + f).size }));
stats.forEach(s => { if (s.size > 400000) process.exit(1); });
"
```

---

## 14. Test Execution & CI/CD

**CI integration:** GitHub Actions (`.github/workflows/ci.yml`). Runs on
push and PR. Steps include `npm test` and `npm audit --audit-level=high`. ✅

**Test timeout:** Vitest default (5000ms per test). No custom timeout
configured. The longest test (`useIdleTimeout — fires onIdle`) takes 30ms —
well within the default. ✅

**Parallel execution:** Vitest runs test files in parallel by default. The
12 test files run concurrently. ✅

**Execution time:** 20.55s total. The 14.47s setup time is dominated by jsdom
environment initialization — this is a known Vitest characteristic. Actual
test execution is 2.64s. ✅

**Coverage reporting:** Not configured. No `--coverage` flag, no coverage
thresholds, no coverage reports in CI.

**Test reporting:** Vitest default reporter in CI. No JUnit XML output for
CI test result visualization.

**React Router future flag warnings:** Two `⚠️ React Router Future Flag Warning`
messages appear in test output (for `v7_startTransition` and
`v7_relativeSplatPath`). These are warnings, not failures, but they add noise
to the test output. They can be suppressed by adding future flags to
`MemoryRouter` in tests:

```typescript
<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
```

---

## 15. Testing Issues Summary

| Severity | Issue | Description | Impact |
|---|---|---|---|
| High | No tests for `Bots` component | The most complex and safety-critical component (live trading modal, bot lifecycle) has no tests | Regressions in bot creation, removal, and mode toggle go undetected |
| Medium | No integration tests for bot workflow | `workflows.test.tsx` covers config panels but not bot creation, removal, or mode toggle | Core trading workflow has no automated coverage |
| Medium | No accessibility tests | No `jest-axe` or equivalent — a11y regressions not caught automatically | WCAG violations could be introduced silently |
| Medium | No coverage reporting | Coverage not measured or enforced — unknown coverage gaps | Cannot identify untested code paths |
| Low | `TradeHistoryTable` test missing `caption` prop | `<TradeHistoryTable rows={[]} />` called without required `caption` prop | TypeScript catches this at compile time but test is technically incorrect |
| Low | `fetchWsTicket` not tested directly | The WS ticket function is mocked in `useBots` tests but never tested in isolation | Ticket fetch error paths and response parsing untested |
| Low | `handleStop` not tested | No test for the stop command payload in `useBots` | Stop command regression not caught |
| Low | Auth header not tested for all API functions | Only `getBotIds` tests the `Authorization` header — other functions not verified | Auth header injection could regress silently for other endpoints |
| Low | Test count discrepancy | README says 110/110, live run shows 105/105 | README is out of date — minor but misleading |
| Low | React Router future flag warnings in test output | Two warnings per test that uses `MemoryRouter` | Noisy test output |
| Info | No factory functions for fixtures | Static fixtures require spreading for variants | Minor — acceptable at current fixture count |
| Info | `@testing-library/user-event` installed but unused | Listed in `devDependencies` but no test uses it | Dead dependency |
| Info | No visual regression tests | No screenshot comparison tooling | Layout regressions not caught automatically |
| Info | No bundle size CI check | Vite warns but does not fail on large chunks | Bundle size regressions not caught in CI |

---

## 16. Testing Recommendations

### Priority 1 — Add `Bots` component tests

The bot management workflow is the most critical user flow and has zero test
coverage. Minimum tests needed:

```typescript
// Bots.test.tsx
it("shows live confirm modal when switching from paper to live")
it("calls handleToggleSimulation after confirming live mode")
it("shows remove confirm modal when clicking Remove")
it("calls handleRemove after confirming removal")
it("shows error banner when fetchError is set")
it("shows disconnected status when wsOpen is false")
it("disables Create Bot button when bot exists")
```

### Priority 2 — Add bot workflow integration tests

```typescript
// workflows.test.tsx additions
it("bot creation workflow: create → bot_created event → Running status")
it("bot removal workflow: remove → confirmation → bot_removed → Idle status")
it("live trading toggle: paper → modal → confirm → live mode")
```

### Priority 3 — Add accessibility tests

```bash
npm install --save-dev jest-axe
```

Add axe checks to `TradeHistoryTable`, `Parameters`, `Indicators`, and
`ErrorBoundary` tests. Run as part of the existing test suite.

### Priority 4 — Configure coverage reporting

Add to `vite.config.js`:

```javascript
test: {
    coverage: {
        provider: "v8",
        reporter: ["text", "lcov"],
        thresholds: { lines: 70, functions: 70 },
        exclude: ["src/mocks/**", "src/setupTests.ts", "src/utils/vitals.ts"],
    }
}
```

Add `--coverage` to the CI test command.

### Priority 5 — Fix minor test issues

- Add `caption="Order History"` to `TradeHistoryTable` test calls
- Add `fetchWsTicket` direct tests (success, 401, network failure)
- Add `handleStop` test to `useBots.test.ts`
- Suppress React Router future flag warnings in `MemoryRouter` test wrappers
- Update README test count from 110 to 105 (or investigate the discrepancy)
- Remove unused `@testing-library/user-event` or migrate `fireEvent` calls to it
