# Final Consolidation & Executive Summary
**Prompt:** 11-WEB-FINAL | **Package:** web | **Reviewed:** July 2025  
**Based on:** Prompts 01–10 (Architecture, API, State, Components, Real-time, Security, UX, Performance, Testing, Code Quality)

---

## 1. Overall System Health Assessment

**Overall health:** 🟡 Yellow — Good with targeted gaps  
**Production readiness:** Conditionally ready — safe to deploy with the three medium-priority items addressed first

sonarftweb is a well-engineered, focused SPA. The codebase is small (~1,100
source lines), TypeScript-strict, and architecturally clean. The WebSocket
ticket auth, RAF log batching, bot state machine, and `ConfigCheckboxPanel`
abstraction are all genuinely good engineering decisions. The test suite is
behaviorally focused and covers the critical hook layer thoroughly.

The gaps that prevent a clean "Green" rating are not architectural — they are
a cluster of medium-priority items that are individually small but collectively
represent meaningful risk for a live trading application: the `bot_stopped`
event is silently ignored (users cannot tell if a bot is actively trading after
clicking Stop), there is no idle session timeout in effect despite the hook
being implemented, and the auth token is not cleared on logout.

**Key strengths:**
- Minimal, purposeful architecture — no unnecessary abstractions or dependencies
- TypeScript strict mode throughout — zero `any` in production code
- WebSocket ticket auth correctly implemented end-to-end
- RAF log batching — correct solution to high-frequency re-render problem
- `ConfigCheckboxPanel` generic abstraction — clean dependency injection pattern
- `React.memo` + `useCallback` correctly applied — no unnecessary re-renders
- MSW v2 test strategy — tests exercise real `fetch` code paths
- nginx security headers — CSP, HSTS, `X-Frame-Options`, `frame-ancestors`

**Key weaknesses:**
- `bot_stopped` event ignored — UI shows wrong state after Stop
- No idle session timeout wired — security gap for live trading
- Token not cleared on logout — session persists until tab close
- No tests for `Bots` component — most complex component has zero coverage
- `Parameters` duplicates `ConfigCheckboxPanel` pattern — DRY violation
- ESLint not run in CI — 3 errors would not block a PR

**Technical debt level:** Low. The debt is concentrated in a small number of
well-understood items, all with clear remediation paths.

---

## 2. Risk Assessment by Severity

### Critical — None

No critical issues were identified across all 10 review areas.

### High

| # | Issue | Area | Why High | Effort |
|---|---|---|---|---|
| H1 | `bot_stopped` event silently ignored | Real-time / UX | Users cannot tell if a bot is actively trading after clicking Stop — safety risk in live trading | Small (1–2h) |
| H2 | No tests for `Bots` component | Testing | Most complex, safety-critical component (live trading modal, bot lifecycle) has zero test coverage | Medium (4–6h) |
| H3 | No idle session timeout wired | Security / UX | `useIdleTimeout` hook exists and is tested but is not connected — unattended live trading session never expires | Small (1h) |

### Medium

| # | Issue | Area | Why Medium | Effort |
|---|---|---|---|---|
| M1 | Token not cleared on logout | Security | JWT persists in `sessionStorage` until tab close after `handleLogout` | Trivial (15min) |
| M2 | No integration tests for bot workflow | Testing | Bot creation, removal, and live trading toggle have no integration test coverage | Medium (3–4h) |
| M3 | No accessibility tests | Testing | No `jest-axe` — a11y regressions not caught automatically | Small (2h) |
| M4 | No request timeout on `fetch` calls | API / Performance | Hung server shows "Saving..." indefinitely — no `AbortController` | Small (1–2h) |
| M5 | `set_simulation` has no server confirmation | Real-time | `isSimulating` can drift from server state — no rollback on error | Medium (2–3h, requires server change) |
| M6 | ESLint not run in CI | Code Quality | 3 `no-undef` errors would not block a PR | Trivial (15min) |
| M7 | No coverage reporting configured | Testing | Coverage not measured or enforced — unknown gaps | Small (1h) |
| M8 | 3 HIGH transitive npm CVEs | Security | `braces`, `lodash`, `picomatch` — all in build tooling, not prod bundle | Small (30min — `npm audit fix`) |

### Low

| # | Issue | Area |
|---|---|---|
| L1 | `Parameters` duplicates `ConfigCheckboxPanel` pattern | Components / Code Quality |
| L2 | CSS duplication between `parameters.css` and `indicators.css` | Components / Code Quality |
| L3 | `PrivateRoute` defined but unused | Architecture / Code Quality |
| L4 | `logo192.png` at 869 KB — severely oversized | Performance |
| L5 | Legacy API paths in use (`/bots?client_id=`) — sunset Jan 2026 | API |
| L6 | `ParametersConfig`/`IndicatorsConfig` missing `version` field | API / Type Safety |
| L7 | No 401 detection in API client | API / UX |
| L8 | History fetch not paginated (default limit=100) | API |
| L9 | Modal focus not trapped | UX / Accessibility |
| L10 | `<h1>` misused in Footer; no page-level `<h1>` | UX / Accessibility |
| L11 | `bot_stopped` not reflected in status badge | UX (duplicate of H1 — UX aspect) |
| L12 | No onboarding for new users | UX |
| L13 | Empty history tables have no message | UX |
| L14 | `saveTimer` not cleared on unmount | Code Quality |
| L15 | Dead code: `useIdleTimeout` unwired, legacy `App.css` styles, `.card` class | Code Quality |
| L16 | Prettier not enforced in CI | Code Quality |
| L17 | `vite-env.d.ts` missing `ImportMetaEnv` declarations | Type Safety |
| L18 | No Web Vitals reporting active in production | Performance |
| L19 | `coingecko.com` in CSP `connect-src` but unused | Security |

---

## 3. Key Metrics Summary

| Dimension | Score | Basis |
|---|---|---|
| **Architecture** | 9/10 | Clean layered design, no circular deps, appropriate abstractions, minor: `Parameters` DRY violation |
| **API Integration** | 7/10 | Centralized, auth-correct, ticket pattern; gaps: no timeout, legacy paths, no 401 handling |
| **State Management** | 9/10 | Minimal, well-distributed, correct patterns; minor: `isSimulating` drift |
| **Component Design** | 8/10 | Clean SRP, good memoization, `ConfigCheckboxPanel` excellent; gap: `Parameters` duplication |
| **Real-time / WebSocket** | 8/10 | Ticket auth, backoff, RAF batching all correct; gaps: `bot_stopped` ignored, no ping timeout |
| **Security** | 8/10 | Strong CSP, HSTS, no XSS surface, ticket auth; gaps: token not cleared on logout, no idle timeout |
| **UX / Accessibility** | 7/10 | Strong ARIA, live trading modal, tooltips; gaps: `bot_stopped` UI, modal focus trap, no onboarding |
| **Performance** | 8/10 | Tiny app bundle (7.67 KB gzip), vendor splitting, RAF batching; gap: `logo192.png` 869 KB |
| **Testing** | 7/10 | Thorough hook tests, MSW v2, 105/105 passing; gaps: no `Bots` tests, no a11y tests, no coverage config |
| **Code Quality** | 8/10 | Strict TS, zero `any`, correct patterns; gaps: ESLint not in CI, 3 `no-undef` errors |
| **Overall** | **7.9/10** | Production-quality codebase with a focused set of addressable gaps |

---

## 4. Top 10 Priority Issues

| Priority | Issue | Category | Severity | Impact | Effort | Timeline |
|---|---|---|---|---|---|---|
| 1 | Handle `bot_stopped` WS event — add `BOT_STOPPED` reducer action, update status badge | Real-time / UX | High | Users cannot confirm bot is stopped in live trading | Small (1–2h) | Immediate |
| 2 | Wire `useIdleTimeout` into `AuthProvider` using `VITE_IDLE_TIMEOUT_MS` | Security | High | Unattended live trading session never expires | Small (1h) | Immediate |
| 3 | Add `sessionStorage.removeItem("sonarft_token")` to `handleLogout` | Security | Medium | JWT persists after logout until tab close | Trivial (15min) | Immediate |
| 4 | Add ESLint to CI (`npm run lint` step) | Code Quality | Medium | 3 `no-undef` errors not caught in CI | Trivial (15min) | Immediate |
| 5 | Add `Bots` component tests (modal logic, status badges, disabled states) | Testing | High | Most complex component has zero coverage | Medium (4–6h) | Next sprint |
| 6 | Add bot workflow integration tests (create, remove, live toggle) | Testing | Medium | Core trading workflow has no automated coverage | Medium (3–4h) | Next sprint |
| 7 | Add `AbortController` timeout to all `fetch` calls in `api.ts` | API | Medium | Hung server shows "Saving..." indefinitely | Small (1–2h) | Next sprint |
| 8 | Run `npm audit fix` — resolve transitive HIGH CVEs | Security | Medium | `braces`, `lodash`, `picomatch` in build tooling | Small (30min) | Next sprint |
| 9 | Refactor `Parameters` to use `ConfigCheckboxPanel` + `useConfigCheckboxes` | Components | Low | ~40 lines of duplicate load/save logic | Medium (2–3h) | Next month |
| 10 | Migrate API calls to canonical paths before Jan 2026 sunset | API | Low | Legacy `/bots?client_id=` paths deprecated | Small (1–2h) | Before Jan 2026 |

---

## 5. Risk Categories Summary

| Category | Status | Key Risks | Priority |
|---|---|---|---|
| Architecture | 🟢 Green | No circular deps, clean layering, appropriate abstractions. `Parameters` DRY violation is the only structural issue. | Low |
| API Integration | 🟡 Yellow | No request timeout, legacy paths in use (sunset Jan 2026), no 401 handling, `version` field missing from types. | Medium |
| State Management | 🟢 Green | Minimal, correct patterns. `isSimulating` optimistic drift is the only state consistency risk. | Low |
| Components | 🟡 Yellow | `Parameters` duplicates `ConfigCheckboxPanel`. CSS duplication. `PrivateRoute` unused. Otherwise clean. | Low–Medium |
| Real-time | 🟡 Yellow | `bot_stopped` ignored (High). `set_simulation` no confirmation. No ping timeout for dropped connections. | High |
| Security | 🟡 Yellow | Token not cleared on logout (Medium). No idle timeout wired (High). 3 HIGH transitive CVEs in build tooling. Strong CSP, HSTS, ticket auth. | Medium |
| UX / Accessibility | 🟡 Yellow | `bot_stopped` UI gap (High). Modal focus trap missing. No onboarding. Empty table states. Strong ARIA otherwise. | Medium |
| Performance | 🟢 Green | Tiny app bundle. Vendor splitting. RAF batching. `logo192.png` 869 KB is the only significant asset issue. | Low |
| Testing | 🟡 Yellow | `Bots` component untested (High). No bot workflow integration tests. No a11y tests. No coverage config. Hook layer is thorough. | Medium–High |
| Code Quality | 🟡 Yellow | ESLint not in CI. 3 `no-undef` errors. `Parameters` duplication. Dead code. Otherwise strict TS, zero `any`, correct patterns. | Low–Medium |

---

## 6. Dependency & Tooling Status

### Production dependencies (6)

| Package | Version | Status |
|---|---|---|
| `react` | ^18.2.0 | ✅ Current stable |
| `react-dom` | ^18.2.0 | ✅ Current stable |
| `react-is` | ^19.2.5 | ⚠️ Version mismatch — `react-is` 19.x with React 18.x (peer dep of Recharts) |
| `react-router-dom` | ^6.30.3 | ✅ Current v6 |
| `recharts` | ^3.8.1 | ✅ Current |
| `web-vitals` | ^2.1.4 | ⚠️ v2 — v4 is current; v2 still functional |

### Dev dependency highlights

| Package | Status |
|---|---|
| `vite` | ^8.0.8 — ✅ Current |
| `typescript` | ^5.0.0 — ✅ Current |
| `vitest` | ^3.0.0 — ✅ Current |
| `msw` | ^2.13.4 — ✅ Current v2 |
| `eslint` | ^9.39.4 — ✅ Current v9 flat config |
| `@testing-library/user-event` | ^13.5.0 — ⚠️ Installed but unused |

### Vulnerability status

| Severity | Count | Location | Risk |
|---|---|---|---|
| Critical | 0 | — | None |
| High | 3 | Build tooling only (`braces`, `lodash`, `picomatch`) | Low — not in prod bundle |
| Moderate | 3 | Build/test tooling | Low — not in prod bundle |

**Build tooling:** Vite 8 (rolldown bundler), TypeScript 5, ESLint v9 flat
config, Prettier 3. All current. ✅

**Testing tools:** Vitest 3, RTL 13, MSW v2. All current and appropriate. ✅

**Linting/formatting:** ESLint configured with `react-hooks`, `jsx-a11y`,
`@typescript-eslint`. Prettier configured. Neither enforced in CI. ⚠️

---

## 7. Security Posture

**Overall security rating:** 🟡 Good with two addressable gaps

| Area | Status | Detail |
|---|---|---|
| Authentication | 🟡 Partial | Ticket-based WS auth ✅; token not cleared on logout ⚠️; no token refresh ⚠️ |
| Authorization | 🟡 Partial | Server enforces auth on all endpoints ✅; `PrivateRoute` unused ⚠️; `Crypto` guards with `return null` only |
| Transport security | 🟢 Secure | HTTPS in production, WSS, HSTS in nginx and API middleware ✅ |
| XSS prevention | 🟢 Secure | React JSX escaping, no `dangerouslySetInnerHTML`, no `innerHTML`, `script-src 'self'` CSP ✅ |
| CSRF prevention | 🟢 Secure | Bearer token in header (not cookie) — inherent CSRF protection ✅ |
| Content Security Policy | 🟢 Strong | `frame-ancestors 'none'` as HTTP header, `script-src 'self'`, `base-uri 'self'` ✅ |
| Sensitive data | 🟢 Secure | No secrets in source, token in `sessionStorage`, no PII beyond email in memory ✅ |
| Session management | 🟡 Partial | `sessionStorage` (tab-scoped) ✅; no idle timeout wired ⚠️; token not cleared on logout ⚠️ |
| Dependency security | 🟡 Partial | 0 critical/high in prod bundle ✅; 3 HIGH in build tooling ⚠️ |
| Input validation | 🟢 Secure | No free-text inputs; server validates all config keys ✅ |

**Two items to fix before production:**
1. Wire `useIdleTimeout` — unattended live trading session never expires
2. Clear token on logout — `sessionStorage.removeItem("sonarft_token")`

---

## 8. Performance Profile

**Overall performance rating:** 🟢 Good

| Metric | Value | Assessment |
|---|---|---|
| Total JS transfer (gzip) | ~160 KB | ✅ Good |
| App code (gzip) | ~10 KB | ✅ Excellent |
| Recharts vendor chunk | 96.69 KB gzip | ⚠️ Largest asset — inherent library cost |
| React vendor chunk | 53.15 KB gzip | ✅ Expected |
| Total CSS (gzip) | 3.78 KB | ✅ Negligible |
| `logo192.png` | 869 KB uncompressed | ⚠️ Severely oversized — easy fix |
| Estimated FCP | < 1s (desktop broadband) | ✅ |
| Estimated LCP | < 2s (desktop broadband) | ✅ |
| Estimated TTI | 1.5–3s (desktop) | ✅ |
| Log re-renders | ≤ 60/s (RAF-batched) | ✅ Correct pattern |
| Memory growth | Stable (logs capped at 500) | ✅ |

**One item to fix:** Resize `logo192.png` from 869 KB to < 20 KB. This is
the single highest-impact performance fix and takes minutes.

**Vendor chunk splitting** is well-designed — React and Recharts are cached
independently from app code. When app code changes, only the 7.67 KB `Crypto`
chunk is invalidated.

---

## 9. Testing & Quality

**Overall testing rating:** 🟡 Good hook coverage, component gaps

| Metric | Value |
|---|---|
| Test files | 12 |
| Tests passing | 105/105 (100%) |
| Test execution time | 20.55s |
| Hook coverage | High — all 5 hooks thoroughly tested |
| API utility coverage | High — all functions, success + error paths |
| Component coverage | Partial — `ErrorBoundary`, `PrivateRoute`, `TradeHistoryTable` tested; `Bots`, `Parameters`, `ConfigCheckboxPanel`, `ProfitChart` not |
| Integration coverage | Partial — config panels covered; bot workflow not covered |
| Accessibility tests | None |
| Coverage reporting | Not configured |
| Mock strategy | MSW v2 (network-level) — robust |

**Biggest gap:** The `Bots` component — the most complex and safety-critical
part of the UI — has zero test coverage. The live trading confirmation modal,
bot lifecycle status badges, and WebSocket command dispatch are all untested.

**Biggest strength:** The hook test suite is genuinely thorough. `useBots`
has 27 tests covering every WebSocket event, every handler, error paths, the
log cap, and non-JSON message fallback. `useWebSocket` tests verify exact
backoff timing. `useConfigCheckboxes` tests all three load tiers.

---

## 10. Architectural Observations

**Overall design:** Sound. The layered architecture (transport → orchestration
→ strategy → analysis → infrastructure) maps cleanly to the frontend's
(shell → page → hooks → components → utils). No architectural anti-patterns.

**Separation of concerns:** Good. All API calls in `utils/api.ts`. All WS
lifecycle in `useWebSocket`. All bot orchestration in `useBots`. Config logic
in `useConfigCheckboxes`. The one exception is `Parameters`, which duplicates
the config pattern inline.

**Modularity:** High. `ConfigCheckboxPanel` is a genuinely reusable generic
component. `useWebSocket` is a standalone hook with no domain coupling.
`useConfigCheckboxes` is domain-agnostic.

**Scalability:** The current architecture scales well to 2–3x the current
feature set without structural changes. Beyond that, `useBots` would benefit
from being split into `useWsTicket`, `useBotHistory`, and `useBotMachine`.

**Extensibility:** Easy to add new config panels (just pass different
`sections`, `fetchFn`, `updateFn` to `ConfigCheckboxPanel`). Easy to add new
WS event handlers (add a `case` to the `onmessage` switch). Easy to add new
API functions (add to `api.ts` following the existing pattern).

**The one structural gap:** `Parameters` should use `ConfigCheckboxPanel`
as `Indicators` does. This is the only place where the architecture is not
followed consistently.

---

## 11. Technical Debt Assessment

**Estimated debt level:** Low

| Debt category | Share | Items |
|---|---|---|
| Testing gaps | 40% | No `Bots` tests, no bot workflow integration tests, no a11y tests, no coverage config |
| Code duplication | 25% | `Parameters` duplicates `ConfigCheckboxPanel`, CSS duplication |
| Tooling gaps | 20% | ESLint/Prettier not in CI, `vite-env.d.ts` incomplete, `logo192.png` oversized |
| Dead code | 10% | `PrivateRoute` unused, `useIdleTimeout` unwired, legacy `App.css` styles |
| Type gaps | 5% | `version` field missing, `ImportMetaEnv` not declared |

**Impact of debt:** Low. The debt does not block feature development or cause
runtime errors. The testing gap is the highest-risk item — a regression in
`Bots` would not be caught automatically.

**Debt paydown plan:** The entire debt backlog can be cleared in 2–3 focused
sprints. The testing gaps are the highest priority; the duplication and tooling
items are straightforward cleanup.

---

## 12. Recommendations by Timeline

### Immediate (this week — before next production deploy)

These are small, high-impact items that take minutes to hours:

1. **Wire `useIdleTimeout`** — connect to `AuthProvider`, call `handleLogout`
   on idle using `VITE_IDLE_TIMEOUT_MS` (1h)
2. **Clear token on logout** — add `sessionStorage.removeItem("sonarft_token")`
   to `handleLogout` (15min)
3. **Handle `bot_stopped` event** — add `BOT_STOPPED` reducer action, handle
   in `onmessage`, show "● Stopped" badge (1–2h)
4. **Add ESLint to CI** — one line in `.github/workflows/ci.yml` (15min)
5. **Fix ESLint `no-undef` errors** — add 3 browser globals to `eslint.config.js` (15min)
6. **Resize `logo192.png`** — export at 192×192, target < 20 KB (15min)
7. **Run `npm audit fix`** — resolve transitive HIGH CVEs (30min)

### Short term (next 1–2 sprints)

8. **Add `Bots` component tests** — modal logic, status badges, disabled
   states, error banners (4–6h)
9. **Add bot workflow integration tests** — create, remove, live toggle (3–4h)
10. **Add `AbortController` timeout to `fetch` calls** — 15s timeout in
    `api.ts` (1–2h)
11. **Add `jest-axe` accessibility tests** — `TradeHistoryTable`, `Parameters`,
    `Indicators`, `ErrorBoundary` (2h)
12. **Configure coverage reporting** — add `v8` provider to `vite.config.js`,
    set 70% threshold (1h)
13. **Add Prettier check to CI** (15min)
14. **Add `version?: number` to `ParametersConfig`/`IndicatorsConfig`** (15min)
15. **Declare `ImportMetaEnv` in `vite-env.d.ts`** (30min)

### Medium term (next 1–2 months)

16. **Refactor `Parameters` to use `ConfigCheckboxPanel`** — add optional
    `headerSlot` prop (2–3h)
17. **Extract shared CSS** from `parameters.css`/`indicators.css` (1h)
18. **Migrate API calls to canonical paths** — before Jan 2026 sunset (1–2h)
19. **Add 401 detection** in `api.ts` — trigger logout or show session-expired
    message (1h)
20. **Wire `PrivateRoute` into routing** or remove it (30min)
21. **Add `set_simulation` server confirmation event** — requires server change
    + frontend handler (2–3h)
22. **Fix modal focus trap** — move focus to first button on open, trap Tab,
    restore on close (2h)
23. **Add `<h1>` to `Crypto` page** (sr-only) and fix Footer `<h1>` → `<p>` (30min)
24. **Enable Web Vitals reporting** — set `VITE_VITALS_URL` in production (30min)

### Long term (3–6 months)

25. **Add history pagination** — `limit`/`offset` support in `getOrders`/`getTrades`
26. **Add client-side ping timeout** — detect silently dropped WS connections
27. **Add aggregate performance statistics** — total profit, win rate, drawdown
28. **Add Recharts `Brush`** for time-range selection on P&L chart
29. **Consider splitting `useBots`** if bot features grow significantly

---

## 13. Team Recommendations

**Skills gaps:** None identified. The codebase demonstrates strong TypeScript,
React hooks, WebSocket, and async patterns. The team clearly understands the
domain.

**Process improvements:**
- Add ESLint and Prettier to CI — currently neither is enforced automatically
- Add coverage reporting — currently no visibility into coverage gaps
- Update README test count when tests change — currently 5 tests out of sync

**Tool improvements:**
- `jest-axe` for automated accessibility testing
- `bundlesize` or similar for CI bundle size regression detection
- Dependabot or Renovate for automated dependency updates

**Testing practices:**
- Prioritize `Bots` component tests — the most critical gap
- Use `userEvent` from `@testing-library/user-event` instead of `fireEvent`
  for more realistic user interaction simulation
- Add `axe` checks to all component tests

**Code review focus areas:**
- Verify `useEffect` dependency arrays are complete (ESLint enforces this, but
  reviewers should understand the implications)
- Check that new WS event types are handled in `onmessage` (not silently ignored)
- Ensure new config panels use `ConfigCheckboxPanel` rather than reimplementing
  the load/save pattern

**Documentation:**
- Add JSDoc to `api.ts` exported functions
- Add `ImportMetaEnv` declarations to `vite-env.d.ts`
- Keep README test count in sync with actual test count

---

## 14. Success Metrics

| Metric | Current | Target | How to measure |
|---|---|---|---|
| ESLint errors | 3 | 0 | `npm run lint` |
| Test pass rate | 105/105 (100%) | 100% | `npm test` |
| Test coverage (lines) | Unknown | ≥ 70% | `npm test -- --coverage` |
| `Bots` component tests | 0 | ≥ 7 | Test file count |
| Bot workflow integration tests | 0 | ≥ 3 | Test file count |
| Accessibility violations | Unknown | 0 | `jest-axe` in test suite |
| npm audit Critical/High (prod bundle) | 0 | 0 | `npm audit --audit-level=high` |
| npm audit High (all) | 3 | 0 | `npm audit` |
| `logo192.png` size | 869 KB | < 20 KB | `ls -lh public/logo192.png` |
| Bundle JS total (gzip) | ~160 KB | < 200 KB | Vite build output |
| App chunk (gzip) | 7.67 KB | < 15 KB | Vite build output |
| Token cleared on logout | No | Yes | Code review + test |
| Idle timeout wired | No | Yes | Code review + test |
| `bot_stopped` handled | No | Yes | Code review + test |

---

## 15. Conclusion

**Is sonarftweb production-ready?**

Yes, with three items addressed first:
1. Wire `useIdleTimeout` (1h)
2. Clear token on logout (15min)
3. Handle `bot_stopped` event (1–2h)

These three items together take under 3 hours and address the most meaningful
risks for a live trading application: an unattended session that never expires,
a token that persists after logout, and a UI that cannot confirm whether a bot
is actively trading after the user clicks Stop.

**What are the biggest risks?**

The `bot_stopped` UI gap is the highest-risk item in production: a user in
live trading mode clicks Stop, the UI shows "● Running", and they cannot tell
whether the bot is still placing orders. This is a safety issue, not just a
UX issue.

The absence of `Bots` component tests means that regressions in the live
trading confirmation modal, bot lifecycle transitions, and WebSocket command
dispatch would not be caught automatically.

**What should be prioritized?**

The immediate list (7 items, ~4 hours total) should be completed before the
next production deploy. The short-term list (items 8–15, ~15 hours) should
be completed in the next two sprints. Everything else is planned improvement
rather than risk mitigation.

**Overall assessment:** sonarftweb is a well-engineered trading dashboard with
a clean architecture, strong TypeScript discipline, and a solid hook test
suite. The gaps are well-understood, small in scope, and have clear remediation
paths. The codebase scores **7.9/10** across all review dimensions — above the
threshold for production deployment once the three immediate items are resolved.
The technical debt is low and payable in 2–3 focused sprints.
