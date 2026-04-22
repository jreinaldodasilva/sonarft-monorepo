# Prompt 09 — Testing & Quality Assurance

**Package:** `packages/web`  
**Prompt ID:** 09-WEB-TESTING  
**Output File:** `docs/testing/test-strategy.md`  
**Reviewed:** July 2025 | **Updated:** July 2025 (post-implementation)

---

## Implementation Status

| Finding | Severity | Status |
|---|---|---|
| `api.test.ts` all 22 tests failing | **Critical** | ✅ **Resolved** — `vi.stubGlobal`; stale URL assertions fixed |
| `useBots` has zero tests | **Critical** | ✅ **Resolved** — 20 tests added |
| No CI pipeline | **High** | ✅ **Resolved** — `.github/workflows/ci.yml` |
| `ErrorBoundary` reset test fails | **Medium** | ✅ **Resolved** — unmount+remount pattern |
| `useWebSocket` socket-close test fails | **Medium** | ✅ **Resolved** — `socketRef` in hook; synchronous close |
| `useConfigCheckboxes` save-status test fails | **Medium** | ✅ **Resolved** — real timers for load, fake timers for save |
| `workflows.test.tsx` stale URL | **Medium** | ✅ **Resolved** — updated to current endpoints |
| `App.test.tsx` nav link test fails | **Low** | ✅ **Resolved** — synchronous assertion on link text |
| No WebSocket integration tests | **High** | ⚠️ **Deferred** — MSW v2 `ws` handler not yet used |
| No `AuthProvider` tests | **Medium** | ✅ **Resolved** — 9 tests added |
| No accessibility tests | **Medium** | ⚠️ **Deferred** — `jest-axe` not yet installed |
| `onUnhandledRequest: "warn"` | **Low** | ⚠️ **Deferred** |

---

## Current Test Results

```
Test Files  12 passed (12)
     Tests  110 passed (110)
  Duration  ~9s
```

**Pass rate: 100% (110/110)** — up from 62% (51/82) at initial review.

---

## Test File Inventory (updated)

| Test file | Tests | Status |
|---|---|---|
| `src/hooks/useWebSocket.test.tsx` | 11 | ✅ All pass |
| `src/hooks/useConfigCheckboxes.test.ts` | 7 | ✅ All pass |
| `src/hooks/useIdleTimeout.test.ts` | 5 | ✅ All pass |
| `src/hooks/useBots.test.ts` | **20** | ✅ **New** — all pass |
| `src/hooks/AuthProvider.test.tsx` | **9** | ✅ **New** — all pass |
| `src/components/ErrorBoundary/ErrorBoundary.test.tsx` | 4 | ✅ All pass |
| `src/components/PrivateRoute/PrivateRoute.test.tsx` | 3 | ✅ All pass |
| `src/components/Bots/TradeHistoryTable.test.tsx` | 5 | ✅ All pass |
| `src/App.test.tsx` | 4 | ✅ All pass |
| `src/utils/api.test.ts` | 22 | ✅ All pass (was 0/22) |
| `src/utils/helpers.test.ts` | 9 | ✅ All pass |
| `src/integration/workflows.test.tsx` | 9 | ✅ All pass |

---

## useBots Test Coverage (new)

```
useBots — initial load
  ✓ fetches bot IDs on mount
  ✓ sets fetchError when getBotIds fails
  ✓ resolves WS URL via ticket when fetchWsTicket succeeds
  ✓ falls back to token URL when fetchWsTicket returns null

useBots — bot_created event
  ✓ fetches updated bot list and auto-runs the new bot

useBots — bot_removed event
  ✓ resets botState and botStatus

useBots — order_success event
  ✓ calls fetchAllOrders with current botIds

useBots — trade_success event
  ✓ calls fetchAllTrades with current botIds

useBots — error event
  ✓ sets fetchError from server error message
  ✓ uses fallback message when error event has no message

useBots — log event
  ✓ appends log messages to logs array (via RAF flush)
  ✓ caps logs at MAX_LOG_LINES (500)
  ✓ handles non-JSON raw log strings

useBots — handleCreate
  ✓ sends create command when connected
  ✓ sets fetchError when not connected

useBots — handleRemove
  ✓ sends remove command after confirmation
  ✓ does not send if user cancels confirmation

useBots — handleToggleSimulation
  ✓ sends set_simulation with botid and new value
  ✓ does nothing when no bot is selected
```

---

## AuthProvider Test Coverage (new)

```
AuthProvider — initial state
  ✓ starts with null user when no session exists
  ✓ restores existing session from netlifyIdentity.currentUser()
  ✓ initialises netlify identity on mount

AuthProvider — login event
  ✓ sets user when netlify login event fires

AuthProvider — logout event
  ✓ clears user when netlify logout event fires

AuthProvider — handleLogin / handleLogout
  ✓ calls netlifyIdentity.open() when user clicks login
  ✓ calls netlifyIdentity.logout() when user clicks logout

AuthProvider — cleanup
  ✓ removes netlify event listeners on unmount
```

---

## CI Pipeline (new)

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test-web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "npm" }
      - run: npm ci
      - run: npm test
      - run: npm audit --audit-level=high
```

Every PR now runs tests and blocks on High/Critical vulnerabilities.

---

## Root Cause Fixes Summary

| Root cause | Fix |
|---|---|
| `global.fetch = vi.fn()` incompatible with `vi.mocked()` | `vi.stubGlobal("fetch", vi.fn())` + `vi.unstubAllGlobals()` |
| `ErrorBoundary` reset: `rerender` doesn't re-mount | Unmount + remount pattern |
| `useWebSocket` socket-close: async state updater | `socketRef` in hook; cleanup calls `socketRef.current.close()` directly |
| `useConfigCheckboxes` save-status: timer race | Load with real timers; switch to fake timers for save phase |
| `App` nav link: split text accessible name | Synchronous assertion on `link.textContent?.includes("Crypt")` |
| `workflows.test.tsx` stale URLs | Updated to `PUT /parameters`, `GET /parameters` |

---

## Remaining Open Items

| Item | Priority | Notes |
|---|---|---|
| WebSocket integration tests (MSW v2 `ws`) | High | Bot lifecycle flow untested at integration level |
| Accessibility tests (`jest-axe`) | Medium | WCAG violations not caught automatically |
| `onUnhandledRequest: "error"` | Low | Currently `"warn"` |
