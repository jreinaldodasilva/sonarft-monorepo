# sonarftweb — Testing & Quality Assurance

**Prompt:** 09-testing-quality  
**Category:** Testing & Quality  
**Date:** July 2025  
**Depends on:** [docs/components/design-patterns.md](../components/design-patterns.md), [docs/api-integration/sonarft-integration.md](../api-integration/sonarft-integration.md)

---

## Executive Summary

sonarftweb has effectively zero test coverage. There is one test file (`App.test.js`) containing one test that is broken — it searches for the text "learn react" which does not exist in the app, so `npm test` fails immediately. No component, hook, utility function, API call, or WebSocket interaction has any test. The CI/CD pipeline (`cloudbuild.yaml`) skips tests entirely — it builds a Docker image and deploys directly without running `npm test`. The testing infrastructure (Jest + React Testing Library) is correctly installed and configured, but has never been used beyond the default CRA scaffold. For a financial trading application that executes real orders, this is the highest-risk gap in the entire codebase.

---

## 1. Testing Framework & Setup

| Aspect | Status |
|---|---|
| Test runner | Jest (via `react-scripts test`) |
| Testing library | `@testing-library/react` v13.4.0 ✓ |
| User event library | `@testing-library/user-event` v13.5.0 ✓ |
| DOM matchers | `@testing-library/jest-dom` v5.16.5 ✓ |
| Test environment | jsdom (CRA default) |
| Setup file | `src/setupTests.js` — imports `@testing-library/jest-dom` ✓ |
| Jest config | Embedded in CRA (`react-scripts`) — no custom `jest.config.js` |
| Coverage reporting | Available via `react-scripts test --coverage` — never run |
| CI/CD test execution | **Not run** — `cloudbuild.yaml` has no test step |

### CI/CD Pipeline — Tests Skipped

```yaml
# cloudbuild.yaml — current
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', 'gcr.io/sonarft/my-app', '.']
- name: 'gcr.io/cloud-builders/gcloud'
  args: ['run', 'deploy', 'my-app', ...]
```

The pipeline goes directly from Docker build to Cloud Run deployment. There is no `npm test`, no `npm audit`, and no coverage check. Code is deployed to production without any automated quality gate.

### The Only Existing Test — Broken

```js
// src/App.test.js
test('renders learn react link', () => {
    render(<App />);
    const linkElement = screen.getByText(/learn react/i);  // ← fails: text doesn't exist
    expect(linkElement).toBeInTheDocument();
});
```

This is the unmodified CRA scaffold test. The app renders "SonarFT", not "learn react". Running `npm test` fails immediately with:

```
Unable to find an element with the text: /learn react/i
```

Additionally, `App.js` uses `AuthProvider` which initializes `netlify-identity-widget` — this would require mocking in a test environment.

---

## 2. Test Coverage

| File | Lines | Tests | Coverage |
|---|---|---|---|
| `src/App.js` | 35 | 1 (broken) | ~0% |
| `src/App_Trading.js` | 38 | 0 | 0% |
| `src/utils/api.js` | 204 | 0 | 0% |
| `src/utils/helpers.js` | 18 | 0 | 0% |
| `src/utils/constants.js` | 14 | 0 | 0% |
| `src/hooks/AuthProvider.js` | 51 | 0 | 0% |
| `src/hooks/useWebSocket.jsx` | 62 | 0 | 0% |
| `src/hooks/WebSocketContext.js` | 49 | 0 | 0% |
| `src/components/Bots/Bots.js` | 257 | 0 | 0% |
| `src/components/Parameters/Parameters.js` | 139 | 0 | 0% |
| `src/components/Indicators/Indicators.js` | 147 | 0 | 0% |
| `src/components/CryptoTicker/CryptoTicker.js` | 69 | 0 | 0% |
| `src/pages/Crypto/Crypto.js` | 33 | 0 | 0% |
| **Total** | **~1,812** | **1 (broken)** | **~0%** |

**Estimated actual coverage: 0%**

---

## 3. Component Tests

No component has a test. The components most in need of testing, ranked by risk:

| Component | Risk | Why Critical to Test |
|---|---|---|
| `Bots.js` | Critical | Bot lifecycle, WebSocket message handling, state machine, order/trade display |
| `Parameters.js` | High | 3-tier data loading, localStorage sync, server POST |
| `Indicators.js` | High | Same as Parameters — near-duplicate logic |
| `AuthProvider.js` | High | Auth state, login/logout, session persistence |
| `useWebSocket.jsx` | High | Connection lifecycle, reconnect, cleanup/memory leak |
| `Crypto.js` | Medium | Auth gate (PrivateRoute), component composition |
| `CryptoTicker.js` | Medium | CoinGecko polling, interval cleanup |
| `utils/api.js` | High | All sonarft REST calls, error handling, fallback logic |
| `utils/helpers.js` | Medium | Order/trade aggregation |

### What Good Component Tests Would Cover

**Bots.js example:**
```js
describe('Bots', () => {
    it('fetches bot IDs on mount', async () => {
        mockGetBotIds.mockResolvedValue(['bot_1', 'bot_2']);
        render(<Bots user={{ id: 'client_123' }} />);
        await waitFor(() => expect(mockGetBotIds).toHaveBeenCalledWith('client_123'));
    });

    it('shows loading state while fetching', () => {
        mockGetBotIds.mockReturnValue(new Promise(() => {})); // never resolves
        render(<Bots user={{ id: 'client_123' }} />);
        expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('sends create command over WebSocket', async () => {
        const mockSend = jest.fn();
        mockUseWebSocket.mockReturnValue({ socket: { send: mockSend }, wsOpen: true });
        render(<Bots user={{ id: 'client_123' }} />);
        await userEvent.click(screen.getByText('Create New Bot'));
        expect(mockSend).toHaveBeenCalledWith(
            JSON.stringify({ type: 'keypress', key: 'create' })
        );
    });

    it('refreshes bot IDs when BOT_CREATED message received', async () => {
        // simulate WebSocket message
    });
});
```

---

## 4. Integration Tests

No integration tests exist. The following user workflows have no automated coverage:

| Workflow | Risk | Test Scenario |
|---|---|---|
| Sign in → navigate to /crypto | High | Auth gate redirects unauthenticated users; authenticated users see trading UI |
| Create bot → bot runs | Critical | WS command sent; bot IDs refresh; run command auto-sent |
| Remove bot → confirmation | High | Removal command sent; state updates |
| Set parameters → server updated | High | POST fires with correct payload; success/error feedback |
| Set indicators → server updated | High | POST fires with correct payload |
| Order fill → table updates | High | WS message triggers REST fetch; table renders new row |
| Server unreachable → fallback | Medium | Parameters/Indicators fall back to localStorage then defaults |
| WebSocket disconnect → reconnect | High | Connection drops; reconnect fires; user notified |

---

## 5. API / Service Tests

`utils/api.js` has 204 lines and 10 exported functions — none are tested. This is the highest-value test target in the codebase because it is pure async logic with no React dependencies, making it straightforward to test with Jest alone.

### Example Tests for api.js

```js
// utils/api.test.js
import { getBotIds, getDefaultParameters, updateParameters } from './api';
import { HTTP } from './constants';

global.fetch = jest.fn();

describe('getBotIds', () => {
    it('returns bot IDs on success', async () => {
        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ botids: ['bot_1', 'bot_2'] }),
        });
        const result = await getBotIds('client_123');
        expect(result).toEqual(['bot_1', 'bot_2']);
        expect(fetch).toHaveBeenCalledWith(
            HTTP + '/botids/client_123',
            expect.objectContaining({ method: 'GET' })
        );
    });

    it('throws on HTTP error', async () => {
        fetch.mockResolvedValueOnce({ ok: false, status: 500 });
        await expect(getBotIds('client_123')).rejects.toThrow();
    });
});

describe('getDefaultParameters', () => {
    it('falls back to local JSON when server unreachable', async () => {
        fetch.mockRejectedValueOnce(new Error('Network error'));
        const result = await getDefaultParameters();
        expect(result).toHaveProperty('exchanges');
        expect(result).toHaveProperty('symbols');
    });
});
```

### Mock Service Worker (MSW) — Recommended

For integration-level API testing, MSW provides a more realistic mock than `jest.fn()`:

```js
// src/mocks/handlers.js
import { rest } from 'msw';
import { HTTP } from '../utils/constants';

export const handlers = [
    rest.get(HTTP + '/botids/:clientId', (req, res, ctx) =>
        res(ctx.json({ botids: ['bot_abc', 'bot_def'] }))
    ),
    rest.post(HTTP + '/bot/set_parameters/:clientId', (req, res, ctx) =>
        res(ctx.json({ status: 'ok' }))
    ),
];
```

---

## 6. Hook Tests

Neither `useWebSocket.jsx` nor `AuthProvider.js` has any tests. These are the two most critical hooks in the app.

### useWebSocket.jsx — Key Test Scenarios

```js
import { renderHook, act } from '@testing-library/react';
import useWebSocket from './useWebSocket';

describe('useWebSocket', () => {
    let mockWs;

    beforeEach(() => {
        mockWs = {
            close: jest.fn(),
            onopen: null, onclose: null, onerror: null,
        };
        global.WebSocket = jest.fn(() => mockWs);
    });

    it('connects on mount', () => {
        renderHook(() => useWebSocket('ws://localhost:5000/ws/test'));
        expect(WebSocket).toHaveBeenCalledWith('ws://localhost:5000/ws/test');
    });

    it('sets wsOpen true on connection open', () => {
        const { result } = renderHook(() => useWebSocket('ws://test'));
        act(() => { mockWs.onopen(); });
        expect(result.current.wsOpen).toBe(true);
    });

    it('does NOT reconnect after unmount', () => {
        const { unmount } = renderHook(() => useWebSocket('ws://test', true));
        act(() => { mockWs.onopen(); });
        unmount();
        // onclose should NOT trigger a new WebSocket call
        act(() => { mockWs.onclose(); });
        expect(WebSocket).toHaveBeenCalledTimes(1); // only the initial connection
    });

    it('closes socket on unmount', () => {
        const { unmount } = renderHook(() => useWebSocket('ws://test'));
        act(() => { mockWs.onopen(); });
        unmount();
        expect(mockWs.close).toHaveBeenCalled();
    });
});
```

The third test (`does NOT reconnect after unmount`) would currently **fail** — confirming the memory leak documented in the WebSocket review.

---

## 7. Snapshot Testing

No snapshot tests exist. Given the current state of the codebase (no PropTypes, no stable component interfaces), snapshot tests would be brittle and low-value. Behavioral tests with React Testing Library are preferred.

---

## 8. Test Data & Fixtures

No test fixtures, factory functions, or mock data files exist for testing purposes. The following fixtures would be needed to bootstrap a test suite:

```js
// src/mocks/fixtures.js
export const mockUser = { id: 'user_abc123', email: 'test@example.com' };

export const mockBotIds = ['bot_001', 'bot_002'];

export const mockOrder = {
    timestamp: '2025-01-01T00:00:00Z',
    position: 'LONG',
    base: 'BTC', quote: 'USDT',
    buy_trade_amount: 1,
    buy_exchange: 'binance', buy_price: 43000, buy_value: 43000,
    sell_exchange: 'okx', sell_price: 43050, sell_value: 43050,
    profit: 50, profit_percentage: 0.00116,
};

export const mockParameters = {
    exchanges: { Binance: true, Okx: false, Kraken: false },
    symbols: { 'BTC/USDT': true, 'ETH/USDT': false },
};

export const mockIndicators = {
    periods: { '5min': true, '15min': false },
    oscillators: { 'Relative Strength Index (14)': true },
    movingaverages: { 'Exponential Moving Average (10)': true },
};
```

---

## 9. Test Organization

### Recommended Structure

```
src/
├── components/
│   ├── Bots/
│   │   ├── Bots.js
│   │   └── Bots.test.js          ← co-located with component
│   ├── Parameters/
│   │   ├── Parameters.js
│   │   └── Parameters.test.js
│   └── Indicators/
│       ├── Indicators.js
│       └── Indicators.test.js
├── hooks/
│   ├── useWebSocket.jsx
│   ├── useWebSocket.test.js
│   ├── AuthProvider.js
│   └── AuthProvider.test.js
├── utils/
│   ├── api.js
│   ├── api.test.js
│   ├── helpers.js
│   └── helpers.test.js
└── mocks/
    ├── fixtures.js               ← shared test data
    ├── handlers.js               ← MSW request handlers
    └── server.js                 ← MSW server setup
```

Co-locating test files with their source files (CRA convention) makes it easy to find tests and keeps coverage visible.

---

## 10. Error & Edge Case Testing

The following error and edge cases have no test coverage and represent real failure modes observed in the code:

| Scenario | Component | Current Behavior | Should Test |
|---|---|---|---|
| Server unreachable on mount | `Parameters`, `Indicators` | Falls back to localStorage | Verify fallback chain fires in order |
| All fallbacks fail | `Parameters`, `Indicators` | Empty checkboxes, no error shown | Verify graceful empty state |
| `getBotIds` returns empty array | `Bots` | Empty select, no message | Verify empty state renders |
| WebSocket message with no matching sentinel | `Bots` | Appended to log only | Verify no state mutation |
| Rapid duplicate WS events | `Bots` | Multiple concurrent fetches | Verify deduplication (or document lack thereof) |
| `updateParameters` POST fails | `Parameters` | Silent failure | Verify error state shown |
| Bot removal while bot is running | `Bots` | Immediate removal, no confirm | Verify command sent correctly |
| `user` prop is null | `Bots` | `user.id` throws TypeError | Verify null guard |
| `botIds` is empty when ORDER_SUCCESS fires | `Bots` | `fetchAllOrders([])` — no-op | Verify no unnecessary fetch |

---

## 11. Accessibility Testing

No automated accessibility tests exist. `jest-axe` is not installed.

### Recommended Setup

```bash
npm install --save-dev jest-axe
```

```js
// Example a11y test
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

it('Bots component has no accessibility violations', async () => {
    const { container } = render(<Bots user={mockUser} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
});
```

Based on the UX review findings, the following violations would be caught:
- Multiple `<h1>` elements on the page
- `<select>` without associated `<label>`
- Nested `<main>` elements
- `<ul>` used as button container

---

## 12. Visual Regression Testing

No visual regression testing exists. No Storybook, Percy, or Chromatic integration. Given the current state of the codebase, establishing component tests and unit tests is a higher priority than visual regression.

---

## 13. Performance Testing

No performance tests exist. No bundle size budgets, no render time benchmarks, no memory leak detection in tests.

A simple bundle size check can be added to CI:

```yaml
# cloudbuild.yaml addition
- name: 'node:20'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      npm ci
      npm run build
      # Fail if main bundle exceeds 200KB gzipped
      BUNDLE_SIZE=$(gzip -c build/static/js/main.*.js | wc -c)
      echo "Bundle size: $BUNDLE_SIZE bytes"
      [ $BUNDLE_SIZE -lt 204800 ] || (echo "Bundle too large!" && exit 1)
```

---

## 14. CI/CD Integration

### Current Pipeline

```yaml
# cloudbuild.yaml
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', 'gcr.io/sonarft/my-app', '.']
- name: 'gcr.io/cloud-builders/gcloud'
  args: ['run', 'deploy', 'my-app', '--image', 'gcr.io/sonarft/my-app',
         '--region', 'us-central1', '--platform', 'managed', '--allow-unauthenticated']
```

No test step. No audit step. No coverage check. Code deploys directly from commit to Cloud Run.

### Recommended Pipeline

```yaml
steps:
# 1. Install dependencies
- name: 'node:20'
  entrypoint: npm
  args: ['ci']

# 2. Security audit
- name: 'node:20'
  entrypoint: bash
  args: ['-c', 'npm audit --audit-level=high || true']

# 3. Lint
- name: 'node:20'
  entrypoint: npm
  args: ['run', 'eslint']

# 4. Test with coverage
- name: 'node:20'
  entrypoint: bash
  args: ['-c', 'CI=true npm test -- --coverage --watchAll=false']

# 5. Build
- name: 'node:20'
  entrypoint: npm
  args: ['run', 'build']

# 6. Docker build and deploy (only on main branch)
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', 'gcr.io/sonarft/my-app', '.']
- name: 'gcr.io/cloud-builders/gcloud'
  args: ['run', 'deploy', 'my-app', '--image', 'gcr.io/sonarft/my-app',
         '--region', 'us-central1', '--platform', 'managed', '--allow-unauthenticated']
```

---

## 15. Testing Issues Summary

| # | Issue | Severity | Description | Impact |
|---|---|---|---|---|
| 1 | Only test file is broken | Critical | `App.test.js` fails on `npm test` — searches for non-existent text | `npm test` fails; CI would block if tests were run |
| 2 | CI/CD has no test step | Critical | `cloudbuild.yaml` deploys without running tests | Broken code ships to production undetected |
| 3 | 0% test coverage on all trading logic | Critical | `Bots.js`, `api.js`, `useWebSocket.jsx` have no tests | Regressions in bot lifecycle, API calls, WS handling go undetected |
| 4 | No API function tests | High | `utils/api.js` — 10 functions, 0 tests | Fallback logic, error handling, request format untested |
| 5 | No hook tests | High | `useWebSocket.jsx` memory leak undetected by tests | Known bug (reconnect after unmount) has no regression test |
| 6 | No integration tests | High | No user workflow is tested end-to-end | Bot creation, parameter setting, trade history flows untested |
| 7 | No error scenario tests | High | No test for server unreachable, WS disconnect, POST failure | Silent failure modes have no coverage |
| 8 | No test fixtures or mock data | Medium | No shared fixtures for components or API responses | Each test would need to define its own data from scratch |
| 9 | No WebSocket mock infrastructure | Medium | No mock for `WebSocket` constructor | Cannot test `Bots.js` or `useWebSocket.jsx` without setup |
| 10 | No accessibility tests | Medium | No `jest-axe` or equivalent | Known a11y violations (heading hierarchy, missing labels) undetected |
| 11 | No MSW or API mock layer | Medium | No request interception for integration tests | Cannot test component + API interaction realistically |
| 12 | `netlify-identity-widget` not mocked | Medium | `AuthProvider` initializes widget on import | All tests rendering `App` or `AuthProvider` will fail without mock |

---

## 16. Testing Recommendations

### Phase 1 — Foundation (1–2 days)

1. **Fix `App.test.js`** — replace with a smoke test that actually passes:
   ```js
   test('renders without crashing', () => {
       render(<App />);
       expect(document.body).toBeTruthy();
   });
   ```

2. **Mock `netlify-identity-widget`** in `src/setupTests.js`:
   ```js
   jest.mock('netlify-identity-widget', () => ({
       init: jest.fn(), on: jest.fn(), off: jest.fn(),
       open: jest.fn(), logout: jest.fn(), currentUser: jest.fn(() => null),
   }));
   ```

3. **Add test step to `cloudbuild.yaml`** before Docker build.

4. **Create `src/mocks/fixtures.js`** with shared test data.

### Phase 2 — Core Coverage (1 week)

5. **Test `utils/api.js`** — mock `fetch`, test all 10 functions including error paths and fallback logic. Highest ROI test target.

6. **Test `utils/helpers.js`** — pure functions, trivial to test.

7. **Test `useWebSocket.jsx`** — mock `WebSocket` constructor, test connection, reconnect guard, and cleanup. This will expose the memory leak as a failing test.

8. **Test `Parameters.js` and `Indicators.js`** — mock API calls, test 3-tier fallback chain, localStorage sync, and POST on button click.

### Phase 3 — Integration Coverage (1–2 weeks)

9. **Install MSW** and create request handlers for all sonarft endpoints.

10. **Test `Bots.js`** — mock WebSocket and API, test bot creation flow, message handling, order/trade refresh.

11. **Test `Crypto.js`** — test PrivateRoute redirects unauthenticated users, renders trading components for authenticated users.

12. **Install `jest-axe`** and add accessibility assertions to all component tests.

### Phase 4 — Quality Gates

13. **Set coverage threshold** in `package.json`:
    ```json
    "jest": {
        "coverageThreshold": {
            "global": { "lines": 70, "functions": 70, "branches": 60 }
        }
    }
    ```

14. **Add `npm audit --audit-level=high`** to CI — fail build on high/critical CVEs.

---

**Save location:** `docs/testing/test-strategy.md`  
**Next prompts:** `10-code-quality-javascript.md`, `11-final-consolidation.md`
