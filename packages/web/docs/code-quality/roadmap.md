# Implementation Roadmap & Action Plan
**Prompt:** 12-WEB-ROADMAP | **Package:** web | **Reviewed:** July 2025  
**Based on:** Prompts 01–11 consolidation findings

---

## Overview

Total estimated effort to clear all identified issues: **~40 hours** across
4 sprints. No architectural rewrites required. All items are incremental
improvements to a production-quality codebase.

```
Sprint 1 (Week 1)   — Safety & Tooling fixes        ~4h   ← Before next deploy
Sprint 2 (Week 2)   — Testing critical gaps          ~12h
Sprint 3 (Weeks 3-4)— Code quality & API hardening   ~10h
Sprint 4 (Month 2)  — Polish & long-term items       ~14h
```

---

## 1. Quick Wins (Sprint 1 — complete before next production deploy)

These 7 items take under 4 hours combined and address the highest-risk gaps.

| # | Issue | Why | Effort | Acceptance Criteria |
|---|---|---|---|---|
| QW1 | Handle `bot_stopped` WS event | Users cannot confirm bot stopped in live trading — safety risk | 1–2h | `bot_stopped` dispatches `BOT_STOPPED` action; status badge shows "● Stopped"; test added |
| QW2 | Wire `useIdleTimeout` into `AuthProvider` | Unattended live trading session never expires | 1h | `handleLogout` called after `VITE_IDLE_TIMEOUT_MS` ms of inactivity; existing `useIdleTimeout` tests still pass |
| QW3 | Clear token on logout | JWT persists in `sessionStorage` after logout until tab close | 15min | `handleLogout` calls `sessionStorage.removeItem("sonarft_token")`; `AuthProvider` test updated |
| QW4 | Add ESLint to CI | 3 `no-undef` errors not caught in CI | 15min | `npm run lint` step added to `.github/workflows/ci.yml`; CI passes after fixing globals |
| QW5 | Fix ESLint `no-undef` errors | `HTMLPreElement`, `HTMLSelectElement`, `sessionStorage` missing from globals | 15min | `npm run lint` exits 0; 0 errors |
| QW6 | Resize `logo192.png` | 869 KB for a 192×192 icon — ~850 KB wasted on every home-screen add | 15min | `logo192.png` < 20 KB; visual check passes |
| QW7 | Run `npm audit fix` | 3 HIGH transitive CVEs in build tooling | 30min | `npm audit --audit-level=high` exits 0 |

### QW1 — Handle `bot_stopped` in detail

**Files to change:**
- `src/hooks/useBots.ts` — add `BOT_STOPPED` action to reducer and `onmessage` switch
- `src/components/Bots/Bots.tsx` — add `"stopped"` entry to `STATUS_LABELS`

```typescript
// useBots.ts — reducer addition
case "BOT_STOPPED":
    return { lifecycle: "stopped", canRemove: true };

// useBots.ts — onmessage addition
case "bot_stopped":
    dispatch({ type: "BOT_STOPPED" });
    break;

// Bots.tsx — STATUS_LABELS addition
stopped: { text: "● Stopped", cls: "bot-status--stopped" },
```

```css
/* bots.css */
.bot-status--stopped { background: var(--amber-bg); color: var(--amber); border: 1px solid #78350f; }
```

### QW2 — Wire `useIdleTimeout` in detail

**File to change:** `src/hooks/AuthProvider.tsx`

```typescript
import useIdleTimeout from "./useIdleTimeout";

const IDLE_MS = parseInt(import.meta.env.VITE_IDLE_TIMEOUT_MS as string ?? "1800000", 10);

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
    const [user, setUser] = useState<AppUser | null>(DEFAULT_USER);
    const handleLogout = useCallback(() => {
        setUser(null);
        sessionStorage.removeItem("sonarft_token");  // QW3 combined here
    }, []);
    const handleLogin = useCallback(() => setUser(DEFAULT_USER), []);

    useIdleTimeout(handleLogout, IDLE_MS, !!user);
    // ...
};
```

### QW4 + QW5 — ESLint CI and globals fix in detail

**`.github/workflows/ci.yml`** — add after `npm test`:
```yaml
- name: Lint
  run: npm run lint
  working-directory: packages/web
```

**`eslint.config.js`** — add to the `globals` block:
```javascript
globals: {
    // existing...
    HTMLPreElement: "readonly",
    HTMLSelectElement: "readonly",
    sessionStorage: "readonly",
},
```

---

## 2. Short Term — Sprint 2 (Week 2, ~12 hours)

Focus: close the critical testing gaps.

| # | Issue | Effort | Priority | Acceptance Criteria |
|---|---|---|---|---|
| ST1 | Add `Bots` component tests | 4–6h | High | ≥ 7 tests covering: live modal, remove modal, status badges, error banner, disabled Create button, WS disconnect state |
| ST2 | Add bot workflow integration tests | 3–4h | High | ≥ 3 tests in `workflows.test.tsx`: create flow, remove flow, live trading toggle |
| ST3 | Add `jest-axe` accessibility tests | 2h | Medium | `jest-axe` installed; axe checks on `TradeHistoryTable`, `Parameters`, `Indicators`, `ErrorBoundary`; 0 violations |
| ST4 | Configure coverage reporting | 1h | Medium | `vite.config.js` has `coverage: { provider: "v8", thresholds: { lines: 70 } }`; `npm test -- --coverage` passes |

### ST1 — `Bots` test plan

```typescript
// src/components/Bots/Bots.test.tsx
describe("Bots — live trading modal", () => {
    it("shows live confirm modal when switching paper → live")
    it("calls handleToggleSimulation after confirming live mode")
    it("does not toggle when user cancels live confirm")
})
describe("Bots — remove modal", () => {
    it("shows remove confirm modal when clicking Remove")
    it("calls handleRemove after confirming removal")
    it("does not remove when user cancels")
})
describe("Bots — status and connection", () => {
    it("shows error banner when fetchError is set")
    it("shows WS error banner when wsError is set")
    it("disables Create Bot button when bot exists")
    it("disables Create Bot button when WS disconnected")
    it("shows Running status badge when lifecycle is running")
    it("shows Stopped status badge when lifecycle is stopped")
})
```

### ST2 — Bot workflow integration test plan

```typescript
// src/integration/workflows.test.tsx additions
describe("Bot creation workflow", () => {
    it("create → bot_created WS event → Running status → bot ID in selector")
})
describe("Bot removal workflow", () => {
    it("remove → confirmation → bot_removed WS event → Idle status")
})
describe("Live trading toggle", () => {
    it("paper → modal shown → confirm → live mode active")
    it("paper → modal shown → cancel → remains paper mode")
})
```

### ST3 — Accessibility test setup

```bash
npm install --save-dev jest-axe @types/jest-axe
```

```typescript
// src/components/Bots/TradeHistoryTable.test.tsx addition
import { axe, toHaveNoViolations } from "jest-axe";
expect.extend(toHaveNoViolations);

it("has no accessibility violations", async () => {
    const { container } = render(
        <TradeHistoryTable rows={[mockOrder]} caption="Order History" />
    );
    expect(await axe(container)).toHaveNoViolations();
});
```

### ST4 — Coverage configuration

```javascript
// vite.config.js — add to test block
coverage: {
    provider: "v8",
    reporter: ["text", "lcov"],
    thresholds: { lines: 70, functions: 70, branches: 60 },
    exclude: [
        "src/mocks/**",
        "src/setupTests.ts",
        "src/utils/vitals.ts",
        "src/vite-env.d.ts",
    ],
},
```

Add to CI:
```yaml
- name: Test with coverage
  run: npm test -- --coverage
  working-directory: packages/web
```

---

## 3. Medium Term — Sprint 3 (Weeks 3–4, ~10 hours)

Focus: API hardening, code quality, and type safety.

| # | Issue | Effort | Priority | Acceptance Criteria |
|---|---|---|---|---|
| MT1 | Add `AbortController` timeout to all `fetch` calls | 1–2h | Medium | All `fetch` calls in `api.ts` abort after 15s; "Request timed out" error shown to user |
| MT2 | Add Prettier check to CI | 15min | Low | `npx prettier --check "src/**/*.{ts,tsx}"` step in CI; passes on clean code |
| MT3 | Add `version?: number` to `ParametersConfig`/`IndicatorsConfig` | 15min | Low | Types updated; no `as` cast needed for `version` field |
| MT4 | Declare `ImportMetaEnv` in `vite-env.d.ts` | 30min | Low | All `import.meta.env.VITE_*` accesses typed without `as string` casts |
| MT5 | Refactor `Parameters` to use `ConfigCheckboxPanel` | 2–3h | Low | `Parameters.tsx` reduced to ~30 lines; `ConfigCheckboxPanel` accepts optional `headerSlot` prop; existing integration tests pass |
| MT6 | Extract shared CSS from `parameters.css`/`indicators.css` | 1h | Low | Shared rules in `configpanel.css`; both files import it; no visual regression |
| MT7 | Fix `TradeHistoryTable` test — add `caption` prop | 15min | Low | All `TradeHistoryTable` test calls include `caption="..."` |
| MT8 | Add `fetchWsTicket` direct tests | 1h | Low | `fetchWsTicket` tested: success, 401, network failure, null return |
| MT9 | Add `handleStop` test to `useBots.test.ts` | 30min | Low | Test verifies `socket.send` called with `{ type: "keypress", key: "stop", botid }` |
| MT10 | Suppress React Router future flag warnings in tests | 15min | Info | `MemoryRouter` in tests uses `future={{ v7_startTransition: true, v7_relativeSplatPath: true }}`; no warnings in test output |

### MT1 — `AbortController` timeout in detail

```typescript
// utils/api.ts — add helper
const fetchWithTimeout = (url: string, options: RequestInit, ms = 15000): Promise<Response> => {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), ms);
    return fetch(url, { ...options, signal: controller.signal })
        .finally(() => clearTimeout(id));
};
```

Replace all `fetch(...)` calls in `api.ts` with `fetchWithTimeout(...)`.
Catch `AbortError` separately to show "Request timed out — check server status".

### MT5 — `Parameters` refactor in detail

Add `headerSlot?: React.ReactNode` to `ConfigCheckboxPanelProps`:

```typescript
interface ConfigCheckboxPanelProps<T extends ConfigState> {
    // existing props...
    headerSlot?: React.ReactNode;
}

// In render, before sections:
{headerSlot && <div className="panel-header-slot">{headerSlot}</div>}
```

`Parameters.tsx` becomes:

```typescript
const Parameters: React.FC<ParametersProps> = ({ clientId }) => (
    <ConfigCheckboxPanel
        title="Parameters"
        clientId={clientId}
        storageKey="parametersState"
        defaultState={DEFAULT_STATE}
        sections={SECTIONS}
        fetchFn={getParameters}
        defaultFn={getDefaultParameters}
        updateFn={updateParameters}
        saveLabel="Set bot parameters"
        className="setAndDisplayParameters"
        headerSlot={<StrategyRow clientId={clientId} />}
    />
);
```

---

## 4. Long Term — Sprint 4 (Month 2, ~14 hours)

Focus: API migration, UX improvements, and monitoring.

| # | Issue | Effort | Priority | Acceptance Criteria |
|---|---|---|---|---|
| LT1 | Migrate API calls to canonical paths | 1–2h | Low (deadline: Jan 2026) | `api.ts` uses `/clients/{clientId}/bots`, `/clients/{clientId}/parameters`, `/clients/{clientId}/indicators`; legacy paths no longer called |
| LT2 | Add 401 detection in `api.ts` | 1h | Low | `response.status === 401` triggers `handleLogout` or shows "Session expired — please log in again" |
| LT3 | Wire `PrivateRoute` into routing or remove | 30min | Low | Either `App.tsx` uses `<PrivateRoute value={user}>` or `PrivateRoute.tsx` and its test are deleted |
| LT4 | Fix modal focus trap | 2h | Low | On modal open: focus moves to first button; Tab cycles within modal; Escape closes; focus restores on close |
| LT5 | Fix `<h1>` in Footer → `<p>`; add sr-only `<h1>` to Crypto | 30min | Low | `Footer` uses `<p>`; `Crypto` has `<h1 className="sr-only">SonarFT Trading Dashboard</h1>` |
| LT6 | Add `set_simulation` server confirmation event | 2–3h | Low (requires server change) | Server sends `bot_simulation_changed` event; frontend handles it to set `isSimulating` from confirmed value; rollback on `error` event |
| LT7 | Add client-side ping timeout | 1–2h | Low | If no WS message received in 60s, close socket to trigger reconnect; handles silently dropped connections |
| LT8 | Add empty state messages to history tables | 1h | Low | `TradeHistoryTable` shows "No records yet" row when `rows` is empty |
| LT9 | Remove dead code | 1h | Info | `App.css` legacy styles removed; `.card` class used or removed; `@testing-library/user-event` removed or used |
| LT10 | Enable Web Vitals reporting | 30min | Info | `VITE_VITALS_URL` set in `.env.production`; vitals reported to endpoint |
| LT11 | Remove `coingecko.com` from CSP `connect-src` | 15min | Info | `nginx.conf` CSP updated; no CoinGecko entry until integration is implemented |
| LT12 | Add JSDoc to `api.ts` exported functions | 1–2h | Info | All exported functions have `/** ... */` doc comments with `@param`, `@returns`, `@throws` |

### LT6 — Server-side change required

This item requires a change to `packages/api/src/websocket/manager.py`:

```python
# In _handle_set_simulation, after success:
await self._push_model(client_id, WsBotSimulationChangedEvent(
    botid=botid, value=value, ts=int(time.time())
))
```

And a new Pydantic model in `schemas.py`:
```python
class WsBotSimulationChangedEvent(WsBaseEvent):
    type: Literal["bot_simulation_changed"] = "bot_simulation_changed"
    botid: str
    value: bool
```

Frontend handler in `useBots.ts`:
```typescript
case "bot_simulation_changed":
    setIsSimulating(msg.value ?? isSimulating);
    break;
```

---

## 5. Effort Estimation & Timeline

```
Week 1 — Sprint 1: Safety & Tooling (Quick Wins)
  QW1  Handle bot_stopped event                    1.5h
  QW2  Wire useIdleTimeout                         1.0h
  QW3  Clear token on logout (combined with QW2)   0.0h
  QW4  Add ESLint to CI                            0.25h
  QW5  Fix ESLint no-undef errors                  0.25h
  QW6  Resize logo192.png                          0.25h
  QW7  npm audit fix                               0.5h
  ─────────────────────────────────────────────────────
  Sprint 1 total:                                  ~4h

Week 2 — Sprint 2: Testing Critical Gaps
  ST1  Bots component tests (≥7 tests)             5h
  ST2  Bot workflow integration tests (≥3 tests)   3.5h
  ST3  jest-axe accessibility tests                2h
  ST4  Configure coverage reporting                1h
  ─────────────────────────────────────────────────────
  Sprint 2 total:                                  ~12h

Weeks 3–4 — Sprint 3: Code Quality & API Hardening
  MT1  AbortController timeout on fetch            1.5h
  MT2  Prettier check in CI                        0.25h
  MT3  Add version field to types                  0.25h
  MT4  ImportMetaEnv declarations                  0.5h
  MT5  Refactor Parameters → ConfigCheckboxPanel   2.5h
  MT6  Extract shared CSS                          1h
  MT7  Fix TradeHistoryTable test caption          0.25h
  MT8  fetchWsTicket direct tests                  1h
  MT9  handleStop test                             0.5h
  MT10 Suppress Router warnings in tests           0.25h
  ─────────────────────────────────────────────────────
  Sprint 3 total:                                  ~8h

Month 2 — Sprint 4: Polish & Long-term
  LT1  Migrate to canonical API paths              1.5h
  LT2  401 detection in api.ts                     1h
  LT3  Wire/remove PrivateRoute                    0.5h
  LT4  Modal focus trap                            2h
  LT5  Fix heading hierarchy                       0.5h
  LT6  set_simulation confirmation (+ server)      3h
  LT7  Client-side ping timeout                    1.5h
  LT8  Empty state messages in tables              1h
  LT9  Remove dead code                            1h
  LT10 Enable Web Vitals                           0.5h
  LT11 Remove coingecko from CSP                   0.25h
  LT12 JSDoc on api.ts                             1.5h
  ─────────────────────────────────────────────────────
  Sprint 4 total:                                  ~14h

─────────────────────────────────────────────────────
TOTAL:                                             ~38h
```

---

## 6. Security Issues Action Plan

| Issue | Risk | Fix | Effort | Verification | Timeline |
|---|---|---|---|---|---|
| No idle timeout wired | Unattended live trading session stays active indefinitely | Wire `useIdleTimeout` in `AuthProvider` (QW2) | 1h | `useIdleTimeout` test passes; manual test: leave app idle for timeout period | Sprint 1 |
| Token not cleared on logout | JWT accessible in `sessionStorage` after logout until tab close | Add `sessionStorage.removeItem` to `handleLogout` (QW3) | 15min | `AuthProvider` test: after logout, `getAuthToken()` returns null | Sprint 1 |
| 3 HIGH transitive CVEs | `braces`, `lodash`, `picomatch` in build tooling — not in prod bundle | `npm audit fix` (QW7) | 30min | `npm audit --audit-level=high` exits 0 | Sprint 1 |
| `PrivateRoute` unused | Unauthenticated users see blank page instead of redirect | Wire into routing or remove (LT3) | 30min | Unauthenticated navigation to `/crypto` redirects to `/` | Sprint 4 |
| No 401 handling | Expired JWT shows generic error — no re-auth prompt | Detect 401 in `api.ts`, trigger logout (LT2) | 1h | After token expiry, user sees "Session expired" and is logged out | Sprint 4 |
| `coingecko.com` in CSP | Unnecessary `connect-src` entry widens allowed connections | Remove from `nginx.conf` (LT11) | 15min | CSP header no longer includes `api.coingecko.com` | Sprint 4 |

---

## 7. Performance Improvements Plan

| Issue | Current | Target | Approach | Effort | Measurement |
|---|---|---|---|---|---|
| `logo192.png` oversized | 869 KB | < 20 KB | Export at 192×192 from source; use WebP with PNG fallback | 15min | `ls -lh public/logo192.png` |
| `logo512.png` likely oversized | Unknown | < 50 KB | Same as above at 512×512 | 15min | `ls -lh public/logo512.png` |
| `Bots` re-renders at 60fps | Up to 60 re-renders/s during log flush | Isolated to `BotConsole` subtree | Extract log state into `BotConsoleContainer` component | 2h | React DevTools Profiler — verify `Bots` shows 0 renders during log flush |
| No `fetch` timeout | Hung server: "Saving..." forever | 15s timeout with user message | `AbortController` in `fetchWithTimeout` helper (MT1) | 1.5h | Manual test: block API, verify timeout message after 15s |
| History re-fetch not debounced | Concurrent REST calls on rapid events | Single call per 200ms window | `useRef` debounce on `fetchAllOrders`/`fetchAllTrades` trigger | 1h | Network tab: verify single request per event burst |
| No Web Vitals reporting | No real-user data | LCP, FID, CLS reported | Set `VITE_VITALS_URL` in `.env.production` (LT10) | 30min | Verify beacon sent in production |

---

## 8. Testing Roadmap

**Current state:** 105/105 passing, no coverage config, `Bots` component untested.

**Target:** ≥ 70% line coverage, `Bots` tested, bot workflow integration tested, a11y tested.

### Phase 1 — Critical paths (Sprint 2, Week 2)

| Task | Tests to add | Effort |
|---|---|---|
| `Bots` component | ≥ 7 tests (modals, status, disabled states) | 5h |
| Bot workflow integration | ≥ 3 tests (create, remove, live toggle) | 3.5h |
| `jest-axe` setup + 4 component checks | 4 axe assertions | 2h |
| Coverage config | Threshold: 70% lines | 1h |

### Phase 2 — Fill remaining gaps (Sprint 3, Weeks 3–4)

| Task | Tests to add | Effort |
|---|---|---|
| `fetchWsTicket` direct tests | 3 tests | 1h |
| `handleStop` in `useBots` | 1 test | 30min |
| Auth header tests for all API functions | 5 tests | 1h |
| `TradeHistoryTable` formatting tests (negative profit, legacy date) | 2 tests | 30min |

### Phase 3 — Ongoing (Sprint 4+)

- Add tests for any new components before merging
- Enforce coverage threshold in CI — fail if lines drop below 70%
- Add `userEvent` interactions to replace `fireEvent` for more realistic tests

**Estimated coverage after Phase 1:** ~75% lines (from ~55% estimated current)  
**Estimated coverage after Phase 2:** ~82% lines

---

## 9. Code Quality Improvements

| Item | Action | Sprint | Effort |
|---|---|---|---|
| ESLint in CI | Add `npm run lint` to CI workflow | 1 | 15min |
| ESLint `no-undef` | Add 3 browser globals to config | 1 | 15min |
| Prettier in CI | Add `prettier --check` to CI workflow | 3 | 15min |
| `Parameters` duplication | Refactor to use `ConfigCheckboxPanel` | 3 | 2.5h |
| CSS duplication | Extract shared `configpanel.css` | 3 | 1h |
| Dead code | Remove legacy `App.css` styles, `.card`, unused deps | 4 | 1h |
| `vite-env.d.ts` | Add `ImportMetaEnv` interface | 3 | 30min |
| Type gaps | Add `version?: number` to config types | 3 | 15min |
| JSDoc | Add to all `api.ts` exports | 4 | 1.5h |
| `void error` pattern | Rename to `_error`, `_info` in `ErrorBoundary` | 4 | 5min |

---

## 10. Dependencies & Tooling Updates

| Action | Timeline | Notes |
|---|---|---|
| `npm audit fix` | Sprint 1 | Resolves transitive HIGH CVEs in build tooling |
| Upgrade `web-vitals` v2 → v4 | Sprint 4 | v2 still functional; v4 adds INP metric |
| Investigate `react-is` v19 with React 18 | Sprint 3 | Peer dep of Recharts — verify no runtime issues |
| Remove `@testing-library/user-event` or migrate to it | Sprint 3 | Currently installed but unused |
| Add Dependabot | Sprint 4 | Automated dependency update PRs |
| `npm audit` frequency | Weekly in CI | Already configured at `--audit-level=high`; consider `--audit-level=moderate` |

---

## 11. Team Allocation & Capacity

The entire roadmap is sized for a single developer working part-time on
improvements alongside feature development.

```
Sprint 1 (Week 1):    ~4h   — 1 developer, half-day
Sprint 2 (Week 2):    ~12h  — 1 developer, 1.5 days
Sprint 3 (Weeks 3-4): ~8h   — 1 developer, 1 day
Sprint 4 (Month 2):   ~14h  — 1 developer, 2 days
─────────────────────────────────────────────────
Total:                ~38h  — ~5 developer-days
```

If two developers are available, Sprints 2 and 3 can be parallelized:
- Developer 1: `Bots` tests + bot workflow integration tests
- Developer 2: `jest-axe` setup + coverage config + code quality items

---

## 12. Risk & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `set_simulation` server change blocked | Medium | Low | Frontend can implement rollback on `error` event without server change as interim fix |
| `Parameters` refactor breaks existing behavior | Low | Medium | Integration tests cover load + save; add tests before refactoring |
| Coverage threshold fails CI after enabling | Medium | Low | Start at 60% threshold, raise to 70% after filling gaps |
| `npm audit fix` breaks build tooling | Low | Medium | Run in a branch; verify `npm run build` and `npm test` pass before merging |
| Modal focus trap breaks existing keyboard flow | Low | Low | Test with keyboard-only navigation before merging |

---

## 13. Success Criteria

The roadmap is complete when all of the following are true:

| Criterion | Target | How to verify |
|---|---|---|
| ESLint errors | 0 | `npm run lint` exits 0 |
| ESLint in CI | Yes | CI workflow includes lint step |
| Test pass rate | 100% | `npm test` exits 0 |
| Test coverage (lines) | ≥ 70% | `npm test -- --coverage` |
| `Bots` component tests | ≥ 7 | Test file exists with ≥ 7 passing tests |
| Bot workflow integration tests | ≥ 3 | `workflows.test.tsx` has ≥ 3 bot tests |
| Accessibility violations | 0 | `jest-axe` assertions pass |
| npm audit Critical/High (all) | 0 | `npm audit --audit-level=high` exits 0 |
| `logo192.png` size | < 20 KB | `ls -lh public/logo192.png` |
| Token cleared on logout | Yes | `AuthProvider` test verifies `sessionStorage` cleared |
| Idle timeout wired | Yes | `useIdleTimeout` connected in `AuthProvider` |
| `bot_stopped` handled | Yes | Status badge shows "● Stopped" after stop command |
| `Parameters` uses `ConfigCheckboxPanel` | Yes | `Parameters.tsx` < 40 lines |
| Legacy API paths migrated | Yes | No `/bots?client_id=` calls in `api.ts` |

---

## 14. Communication Plan

**Sprint 1 (safety items):** Complete before next production deploy. No
stakeholder communication needed — these are internal quality fixes.

**Sprint 2 (testing):** Report coverage baseline after configuring reporting.
Share coverage report with team.

**Sprint 3 (code quality):** No user-visible changes. Internal quality
improvement.

**Sprint 4 (UX + API):** The `bot_stopped` fix (Sprint 1) and modal focus
trap (Sprint 4) are user-visible. Include in release notes.

**Progress tracking:** Use the success criteria table above as a checklist.
Check off items as they are completed and merged.

---

## 15. Post-Implementation Review

After each sprint, verify:

1. All acceptance criteria met (run the verification commands)
2. No regressions — `npm test` passes, `npm run build` succeeds
3. No new ESLint errors introduced
4. Coverage did not decrease

After Sprint 4 (full roadmap complete):

1. Re-run the full 10-prompt review suite to measure improvement
2. Update the consolidation document (Prompt 11) with new scores
3. Archive this roadmap as complete
4. Establish a quarterly review cadence for ongoing quality maintenance

---

## 16. Detailed Sprint Plans

### Sprint 1 — Day by day

**Day 1 (morning, ~2h):**
- QW5: Fix ESLint globals (15min)
- QW4: Add ESLint to CI (15min)
- QW1: Handle `bot_stopped` event — reducer + `onmessage` + CSS (1.5h)

**Day 1 (afternoon, ~2h):**
- QW2+QW3: Wire `useIdleTimeout` + clear token on logout (1h)
- QW6: Resize `logo192.png` (15min)
- QW7: `npm audit fix` + verify build (30min)
- Verify: `npm run lint` exits 0, `npm test` passes, `npm run build` succeeds

### Sprint 2 — Day by day

**Day 1 (5h):**
- ST1: `Bots` component tests — modal logic (3h)
- ST1: `Bots` component tests — status badges + disabled states (2h)

**Day 2 (4h):**
- ST2: Bot workflow integration tests (3.5h)
- ST3: Install `jest-axe`, add to `TradeHistoryTable` test (30min)

**Day 3 (3h):**
- ST3: Add axe checks to `Parameters`, `Indicators`, `ErrorBoundary` (1.5h)
- ST4: Configure coverage reporting + CI step (1h)
- Verify: all tests pass, coverage ≥ 70%, no a11y violations

### Sprint 3 — Week 1

- MT1: `fetchWithTimeout` helper + update all `fetch` calls (1.5h)
- MT5: `Parameters` refactor — add `headerSlot` to `ConfigCheckboxPanel` (2.5h)
- MT6: Extract shared CSS (1h)
- MT3+MT4: Type fixes (`version` field, `ImportMetaEnv`) (45min)

### Sprint 3 — Week 2

- MT2: Prettier CI check (15min)
- MT7–MT10: Test fixes and additions (2.5h)
- Verify: `npm run lint`, `npm test -- --coverage`, `npx prettier --check` all pass

---

## 17. Contingency & Flex Time

**20% buffer built into estimates.** Actual estimates above include buffer.

**If Sprint 2 runs long:** Defer ST3 (`jest-axe`) to Sprint 3. The `Bots`
tests (ST1) and bot workflow tests (ST2) are the higher priority.

**If `Parameters` refactor (MT5) is blocked:** The `headerSlot` prop approach
may need design review. Defer to Sprint 4 and keep `Parameters` as-is. The
duplication is Low severity and does not block any other work.

**If `set_simulation` server change (LT6) is not feasible:** Implement
frontend-only rollback: on `error` event following a `set_simulation` command,
revert `isSimulating` to its previous value. This is a partial fix but
eliminates the drift risk without requiring a server change.

**Escalation:** If any Sprint 1 item is blocked (e.g. CI access), escalate
immediately — these items address live trading safety risks and should not
slip past the next production deploy.
