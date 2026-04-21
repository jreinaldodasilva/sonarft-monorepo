# Prompt 11 — Final Consolidation & Executive Summary

**Package:** `packages/web`  
**Prompt ID:** 11-WEB-FINAL  
**Output File:** `docs/code-quality/consolidation.md`  
**Reviewed:** July 2025  
**Based on:** Prompts 01–10 (Architecture, API, State, Components, Real-time, Security, UX, Performance, Testing, Code Quality)

---

## 1. Overall System Health Assessment

### Health Rating: 🟡 Yellow — Needs Attention Before Production

sonarftweb is a well-structured, cleanly written React application with a sound architecture. The codebase is small, readable, and follows modern conventions throughout. For a development-stage trading tool it is functional and coherent.

However, it is **not production-ready** in its current state. There are three categories of blocking issues:

1. **A broken production configuration** — `.env.production` uses `REACT_APP_*` variable names that Vite ignores, meaning a production build silently connects to `http://localhost:8000`. Every API call and WebSocket connection would fail.
2. **A broken core feature** — the simulation/live trading mode toggle sends an invalid WebSocket command that the server rejects silently. Users cannot switch trading modes.
3. **A broken test suite** — 31 of 82 tests fail on a clean run, and no CI pipeline runs tests. The codebase has been shipping with undetected regressions.

### Key Strengths

- Clean, consistent TypeScript throughout — zero `any` types, strict mode enabled
- Well-designed hook architecture — logic correctly separated from UI
- Solid WebSocket reconnection with exponential backoff, fully tested
- Three-tier config fallback (API → localStorage → bundled defaults) is robust
- Auth tokens never written to `localStorage` by application code
- Content Security Policy present in both HTML files
- No circular dependencies, no `var`, no `console.log` in production code
- All components under 200 lines; no monolithic files

### Key Weaknesses

- Production environment misconfiguration (`.env.production` broken)
- Core feature broken (`set_simulation` WS command missing `botid`)
- 31/82 tests failing; `useBots` — the most critical hook — has zero tests
- Bundle size 229KB gzip (target: 100KB) due to unused Redux stack + `netlify-identity-widget` loading on all pages
- JWT passed in WebSocket URL query string — exposed in server logs
- Multiple WCAG accessibility violations (contrast failures, invalid HTML landmarks, missing `aria-live`)
- nginx serves static files with no security headers and no gzip compression
- ESLint configuration broken (incompatible with ESLint v9)

### Technical Debt Level: Medium

The debt is concentrated in three areas: security/configuration (high-impact, low-effort to fix), testing gaps (medium-effort), and UX/accessibility (medium-effort). The core architecture is sound and does not require significant rework.

---

## 2. Risk Assessment by Severity

### 🔴 Critical — Must Fix Before Any Production Deployment

| # | Issue | Source | Why Critical | Effort |
|---|---|---|---|---|
| C1 | `.env.production` uses `REACT_APP_*` prefix — Vite ignores these; production build connects to `http://localhost:8000` | Prompt 06 | Every API call and WS connection fails in production; all traffic unencrypted | 5 min |
| C2 | `form-data` critical vulnerability (GHSA-fjxv-7rqg-78g4) via `axios` | Prompt 06 | Critical CVE in production bundle | 30 min (remove axios) |
| C3 | `set_simulation` WS command missing `botid` — server rejects silently | Prompts 02, 05, 07 | Core feature broken; users cannot switch trading modes | 15 min |
| C4 | 31/82 tests failing; no CI runs tests | Prompt 09 | Regressions ship undetected; test suite provides false confidence | 2-4 hrs |

### 🟠 High — Fix Before Live Trading Is Enabled

| # | Issue | Source | Why High | Effort |
|---|---|---|---|---|
| H1 | JWT passed as WebSocket query parameter (`?token=<JWT>`) | Prompts 02, 05, 06 | Token exposed in server logs and browser history | 1-2 hrs |
| H2 | React Router XSS via open redirect (GHSA-2w69-qvjg-hvjx) | Prompt 06 | Direct XSS vulnerability in production bundle | 15 min (`npm update`) |
| H3 | nginx has no security headers and no gzip compression | Prompts 06, 08 | No `X-Frame-Options`, no HSTS, no CSP header; 3.3× larger downloads | 30 min |
| H4 | CSP `frame-ancestors 'none'` via `<meta>` tag — silently ignored | Prompt 06 | Clickjacking protection is ineffective | 30 min |
| H5 | No confirmation before switching to live trading mode | Prompt 07 | Real orders placed with no warning | 1-2 hrs |
| H6 | `WsErrorEvent` not handled — all server-side failures silent | Prompts 02, 05, 07 | Users get no feedback when bot commands fail | 1-2 hrs |
| H7 | `useBots` has zero unit tests | Prompts 03, 05, 09 | Highest-risk code path entirely untested | 4-6 hrs |
| H8 | Redux stack bundled but never used (~25-35KB gzip) | Prompts 01, 08 | Unnecessary bundle weight + parse time | 15 min (`npm uninstall`) |
| H9 | favicon.ico is 870KB | Prompt 08 | Downloaded on every page load | 15 min |
| H10 | ESLint configuration broken (incompatible with ESLint v9) | Prompt 10 | Linting has been non-functional; code quality checks bypassed | 1-2 hrs |

### 🟡 Medium — Plan to Fix

| # | Issue | Source |
|---|---|---|
| M1 | `handleCreate` does not check `wsOpen` — silent failure when disconnected | Prompt 05 |
| M2 | Stale `botIds` closure in `onmessage` handler | Prompts 03, 05 |
| M3 | `useConfigCheckboxes` suppresses `react-hooks/exhaustive-deps` | Prompts 03, 10 |
| M4 | `TradeRecord` frontend interface missing 7 fields from API schema | Prompts 02, 09 |
| M5 | No request timeouts on any `fetch` call | Prompt 02 |
| M6 | Stale token race: `getAuthToken()` called at render time for WS URL | Prompts 02, 05 |
| M7 | `botState` + `botStatus` are two variables for one state machine | Prompts 03, 05 |
| M8 | Three `<main>` landmarks on Home page — WCAG violation | Prompts 04, 07 |
| M9 | All NavBar links use `<h1>` — heading hierarchy violation | Prompts 04, 07 |
| M10 | Missing `aria-live` for bot status, WS status, save feedback | Prompt 07 |
| M11 | Bot status "Idle" contrast ratio ~3.8:1 (fails WCAG AA 4.5:1) | Prompt 07 |
| M12 | Save status "Saved" contrast ratio ~2.1:1 (fails WCAG AA) | Prompt 07 |
| M13 | No `:focus-visible` styles — keyboard users cannot track focus | Prompt 07 |
| M14 | `BotControls`, `TradeHistoryTable`, `ProfitChart` not `React.memo`-wrapped | Prompts 03, 08 |
| M15 | Log array spread on every WS message — GC pressure at high frequency | Prompts 03, 08 |
| M16 | `ParametersConfig` index signature defeats TypeScript type safety | Prompt 10 |
| M17 | `api.test.ts` stale URL assertions pass against wrong endpoints | Prompts 02, 09 |
| M18 | `AuthProvider` has zero tests | Prompt 09 |
| M19 | No WebSocket integration tests | Prompts 05, 09 |
| M20 | `onmessage` handler has no outer `try/catch` | Prompt 10 |

### 🔵 Low — Nice to Fix

- Invalid HTML nesting (`BotConsole`, `BotControls`, `Home`) — Prompts 04, 07
- `Parameters`/`Indicators` duplication (~120 lines) — Prompts 04, 10
- CSS class name collisions across component stylesheets — Prompt 04
- Dead code (8 unused page/component files, CRA template styles) — Prompts 04, 10
- `Header.tsx` one-line wrapper — Prompts 04, 10
- No `useAuth` convenience hook — Prompt 04
- Profit values not formatted with `Intl.NumberFormat` — Prompt 07
- Timestamps displayed as ISO strings — Prompt 07
- No table `<caption>` elements — Prompt 07
- `window.confirm` in `handleRemove` hook — Prompts 02, 04
- No Prettier config file — Prompt 10
- Both `package-lock.json` and `yarn.lock` committed — Prompt 10
- `VITE_DEV_AUTH_BYPASS` not asserted false in production builds — Prompt 06

---

## 3. Key Metrics Summary

| Metric | Score | Notes |
|---|---|---|
| **Architecture** | 8/10 | Clean layering, good hook design, minor issues (unused Redux, dead pages) |
| **API Integration** | 6/10 | REST layer solid; WS auth insecure; `set_simulation` broken; no timeouts |
| **State Management** | 7/10 | Appropriate choices; stale closure bug; missing `useBots` tests |
| **Component Design** | 7/10 | Well-sized, typed; HTML validity issues; duplication; no base components |
| **Real-time / WebSocket** | 6/10 | Connection layer excellent; message handling has 3 high-severity bugs |
| **Security** | 4/10 | Auth token handling good; JWT in WS URL; broken prod config; 11 CVEs |
| **UX / Accessibility** | 4/10 | Functional UI; broken toggle; silent errors; multiple WCAG failures |
| **Performance** | 5/10 | 229KB gzip (target 100KB); no nginx gzip; unused deps; good rendering |
| **Testing** | 3/10 | 62% pass rate; `useBots` untested; no CI; 31 failing tests |
| **Code Quality** | 7/10 | Clean code; broken ESLint; 2 suppressions; duplication; no TODOs |
| **Overall** | **5.7/10** | Solid foundation; not production-ready without addressing critical issues |

---

## 4. Top 10 Priority Issues

| Priority | Issue | Category | Severity | Impact | Effort | Timeline |
|---|---|---|---|---|---|---|
| 1 | Fix `.env.production` — rename `REACT_APP_*` to `VITE_*` | Security/Config | Critical | Production build broken | 5 min | Immediate |
| 2 | Fix `set_simulation` — add `botid` to WS message | Real-time | Critical | Core feature broken | 15 min | Immediate |
| 3 | Fix `api.test.ts` — replace `global.fetch` with `vi.stubGlobal` | Testing | Critical | 22 tests failing; REST layer untested | 30 min | Immediate |
| 4 | Remove `axios` — migrate `CryptoTicker` to `fetch` | Security/Perf | Critical/High | Critical CVE; 11KB gzip saving | 30 min | Immediate |
| 5 | Implement WS ticket auth — use `POST /ws/ticket` | Security | High | JWT exposed in server logs | 1-2 hrs | Sprint 1 |
| 6 | Handle `WsErrorEvent` — display server errors in UI | Real-time/UX | High | All server failures silent | 1-2 hrs | Sprint 1 |
| 7 | Add nginx security headers + gzip compression | Security/Perf | High | No security headers; 3.3× download penalty | 30 min | Sprint 1 |
| 8 | Write `useBots` unit tests | Testing | High | Highest-risk hook entirely untested | 4-6 hrs | Sprint 1 |
| 9 | Remove unused Redux stack | Performance | High | ~25-35KB gzip; parse overhead | 15 min | Sprint 1 |
| 10 | Add live trading confirmation modal | UX/Safety | High | Real orders placed without warning | 1-2 hrs | Sprint 1 |

---

## 5. Risk Categories Summary

| Category | Status | Key Risks | Priority |
|---|---|---|---|
| Architecture | 🟢 Good | Unused Redux in bundle; dead page files | Low |
| API Integration | 🟡 Needs attention | `set_simulation` broken; JWT in WS URL; no timeouts; stale token | High |
| State Management | 🟡 Needs attention | Stale `botIds` closure; suppressed deps warning; no `useBots` tests | Medium |
| Components | 🟡 Needs attention | HTML validity; duplication; no base components; no `React.memo` | Medium |
| Real-time / WebSocket | 🟠 Issues | `set_simulation` broken; `WsErrorEvent` unhandled; no WS tests | High |
| Security | 🔴 Critical | Broken prod config; JWT in URL; 11 CVEs; no nginx headers; broken CSP | Critical |
| UX / Accessibility | 🟠 Issues | Silent errors; broken toggle; WCAG failures; no live trading warning | High |
| Performance | 🟡 Needs attention | 229KB gzip; no nginx gzip; unused deps; favicon 870KB | Medium |
| Testing | 🔴 Critical | 31/82 failing; `useBots` untested; no CI; no a11y tests | Critical |
| Code Quality | 🟡 Needs attention | Broken ESLint; suppressed warning; duplication; no Prettier config | Medium |

---

## 6. Dependency & Tooling Status

### Runtime Dependencies (20 total)

| Status | Packages | Action |
|---|---|---|
| ✅ Actively used | `react`, `react-dom`, `react-router-dom`, `netlify-identity-widget`, `recharts`, `react-redux` (wait — unused), `prop-types` (wait — unused) | Keep used ones |
| ❌ Unused — remove | `@reduxjs/toolkit`, `react-redux`, `reselect`, `use-sync-external-store`, `immer`, `eventemitter3`, `es-toolkit`, `clsx`, `decimal.js-light`, `tiny-invariant`, `victory-vendor`, `prop-types` | `npm uninstall` |
| ❌ Replace | `axios` | Replace with `fetch` in `CryptoTicker` |

Removing unused dependencies reduces runtime deps from 20 to ~7 and saves ~41-56KB gzip.

### Vulnerability Status

| Severity | Count | Packages | Fix |
|---|---|---|---|
| Critical | 1 | `form-data` (via `axios`) | Remove `axios` |
| High | 6 | `react-router`, `@remix-run/router`, `braces`, `lodash`, `picomatch` (×2) | `npm update react-router-dom` + `npm audit fix` |
| Moderate | 4 | `@adobe/css-tools`, `@babel/runtime`, `follow-redirects`, `micromatch` | `npm audit fix` |

All 11 vulnerabilities have fixes available. Most resolve automatically after removing `axios` and updating `react-router-dom`.

### Build Tooling

| Tool | Status | Notes |
|---|---|---|
| Vite 8.0.8 | ✅ Current | Good choice; fast builds |
| TypeScript 5.x | ✅ Current | Strict mode enabled |
| Vitest 3.0 | ✅ Current | Good test runner |
| ESLint | ❌ Broken | `react-app` preset incompatible with ESLint v9; needs flat config migration |
| Prettier | ⚠️ No config | Installed but no `.prettierrc`; uses defaults |
| MSW 2.x | ✅ Current | Good mock library; WS support available but unused |

---

## 7. Security Posture

### Authentication & Authorization

| Aspect | Status | Notes |
|---|---|---|
| Token storage | ✅ Secure | In-memory only; never written to `localStorage` by app code |
| Token transmission (REST) | ✅ Secure | `Authorization: Bearer` header |
| Token transmission (WebSocket) | ❌ Insecure | `?token=<JWT>` in URL — exposed in logs |
| Session timeout | ✅ Implemented | 30-minute idle timeout via `useIdleTimeout` |
| Logout | ⚠️ Incomplete | WebSocket not closed on logout |
| Dev auth bypass | ⚠️ Risk | `VITE_DEV_AUTH_BYPASS` not asserted false in production |

### Transport Security

| Aspect | Status | Notes |
|---|---|---|
| HTTPS in production | ❌ Broken | `.env.production` misconfiguration causes HTTP fallback |
| WSS in production | ❌ Broken | Same misconfiguration |
| HSTS | ⚠️ API only | Set by API middleware; not set by nginx for frontend |
| nginx security headers | ❌ Missing | No `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` |

### XSS / CSRF

| Aspect | Status | Notes |
|---|---|---|
| React JSX escaping | ✅ | All user data rendered as text; no `dangerouslySetInnerHTML` |
| CSP (script-src) | ✅ | `'self'` only; no `unsafe-eval` |
| CSP (frame-ancestors) | ❌ Ineffective | Delivered via `<meta>` tag — ignored by browsers |
| CSP (production URLs) | ❌ Missing | `connect-src` includes `localhost` but not production API URL |
| CSRF | ✅ N/A | Bearer token auth is CSRF-resistant by design |

### Overall Security Score: 4/10

The auth token handling and XSS prevention are well-implemented. The security posture is undermined by the broken production configuration, JWT in WebSocket URL, missing nginx headers, and 11 dependency vulnerabilities.

---

## 8. Performance Profile

### Bundle Size

| Metric | Current | Target | Gap |
|---|---|---|---|
| Total JS (gzip) | ~229KB | 100KB | 129KB over |
| `AuthProvider` chunk | 119KB gzip | — | `netlify-identity-widget` loads on all pages |
| `Crypto` chunk | 99KB gzip | — | Redux stack (~30KB) + Recharts (~60KB) |
| `axios` chunk | 11KB gzip | 0KB | Replace with `fetch` |
| favicon.ico | 870KB raw | <5KB | Regenerate |

**After removing unused deps + adding nginx gzip:** estimated total gzipped JS ~173-188KB, effective download ~173KB (vs current 766KB uncompressed due to missing nginx gzip).

### Rendering Performance

| Metric | Status | Notes |
|---|---|---|
| Route-based code splitting | ✅ | Lazy-loaded pages |
| `React.memo` on hot components | ❌ Missing | `BotControls`, `TradeHistoryTable`, `ProfitChart` re-render on every log message |
| Log update batching | ❌ Missing | Array spread on every WS message; GC pressure at high frequency |
| `useMemo` / `useCallback` | ✅ Correct | Applied where needed; no over-memoization |

### Web Vitals (estimated)

| Metric | Estimate | Target |
|---|---|---|
| LCP | 1.5-3s | <2.5s |
| FID/INP | <50ms | <200ms ✅ |
| CLS | Low-moderate | <0.1 |
| FCP | 1-2s | <1.8s |

### Overall Performance Score: 5/10

Good rendering architecture; bundle size and delivery are the main problems, both fixable with low effort.

---

## 9. Testing & Quality

### Test Suite Health

| Metric | Value | Target |
|---|---|---|
| Total tests | 82 | — |
| Passing | 51 (62%) | 100% |
| Failing | 31 (38%) | 0% |
| Estimated line coverage | ~35-45% | 80%+ |
| CI pipeline | ❌ None | Required |

### Coverage Gaps by Risk

| Area | Coverage | Risk |
|---|---|---|
| `useBots` | 0% | 🔴 Critical |
| `utils/api.ts` | 0% (all tests broken) | 🔴 Critical |
| `AuthProvider` | 0% | 🟠 High |
| WebSocket integration flows | 0% | 🟠 High |
| `useWebSocket` | ~90% | 🟢 Good |
| `useConfigCheckboxes` | ~85% | 🟢 Good |
| `useIdleTimeout` | 100% | 🟢 Good |
| `ErrorBoundary` | 75% | 🟡 OK |
| `TradeHistoryTable` | ~90% | 🟢 Good |
| `PrivateRoute` | 100% | 🟢 Good |

### Test Quality

Where tests exist, they are well-written: behaviour-based (not implementation), descriptive names, AAA pattern, realistic fixtures. The test infrastructure (Vitest + RTL + MSW) is appropriate and modern. The problems are broken tests and coverage gaps, not test quality.

### Overall Testing Score: 3/10

The score reflects the current broken state. After fixing the 5 root-cause bugs (Prompt 09), the score rises to ~6/10. Reaching 8/10 requires writing `useBots` and `AuthProvider` tests and adding CI.

---

## 10. Architectural Observations

### Overall Design

The architecture is sound. The layering is clear and consistently applied:

```
Route Layer (App.tsx)
  → Page Layer (Crypto, Home)
    → Component Layer (Bots, Parameters, Indicators)
      → Hook Layer (useBots, useConfigCheckboxes, useWebSocket)
        → API/Utils Layer (utils/api.ts, utils/constants.ts)
```

No layer violations detected. Components do not call `fetch` directly (except `CryptoTicker`). Hooks do not render JSX. The API layer is a single module. ✅

### Separation of Concerns

Good overall. The one area where concerns are mixed is `useBots`, which handles WebSocket message dispatch, REST fetching, bot lifecycle state, and simulation mode in a single hook. This is manageable at current size but would benefit from splitting as the feature grows.

### Modularity

High. Each component, hook, and utility is in its own file with a clear single responsibility. Dependencies are injected (hooks receive `clientId`, components receive callbacks). No tight coupling between unrelated modules.

### Scalability

The current architecture scales well to the stated use case (≤5 bots per client, single-page trading interface). Potential scaling concerns:
- Trade history is fetched in full on every event (no pagination in use)
- Log array spread creates GC pressure at high message frequency
- No server-side pagination support in the frontend

### Extensibility

Adding new WS event types requires only a new `case` in `useBots`. Adding new config categories requires only new `stateKeys` in `useConfigCheckboxes`. Adding new pages requires only a new lazy import and route in `App.tsx`. The architecture is easy to extend. ✅

---

## 11. Technical Debt Assessment

### Estimated Debt Level: Medium

| Debt Category | % of Total Debt | Description |
|---|---|---|
| Security & Configuration | 30% | Broken prod config, JWT in URL, missing nginx headers, 11 CVEs |
| Testing Gaps | 25% | `useBots` untested, 31 failing tests, no CI |
| UX & Accessibility | 20% | Silent errors, broken toggle, WCAG violations |
| Performance | 15% | Unused deps in bundle, no nginx gzip, no `React.memo` |
| Code Quality | 10% | Broken ESLint, duplication, suppressed warning |

### Impact of Current Debt

- **Development velocity:** Low impact — the codebase is clean and easy to work in
- **Production readiness:** High impact — the broken prod config and broken feature are blockers
- **Reliability:** Medium impact — silent error handling and untested `useBots` create hidden failure modes
- **Security:** High impact — JWT exposure and CVEs are real risks in production

### Debt Paydown Plan

The debt is concentrated and addressable. The critical and high items can be resolved in 2-3 focused sprints:

- **Sprint 1 (1 week):** All Critical items + security headers + WS ticket auth + `useBots` tests
- **Sprint 2 (1 week):** Medium items — accessibility fixes, error handling, `React.memo`, test fixes
- **Sprint 3 (1 week):** Low items — duplication, dead code, tooling, documentation

---

## 12. Recommendations by Timeline

### IMMEDIATE — Fix Before Any Deployment (Days 1-3)

These are blockers. Nothing should be deployed until these are resolved.

1. **Fix `.env.production`** — rename `REACT_APP_API_URL` → `VITE_API_URL`, `REACT_APP_WS_URL` → `VITE_WS_URL`. 5 minutes.

2. **Fix `set_simulation` WS command** — add `botid: selectedBotId` to the message in `useBots.handleToggleSimulation`. 15 minutes.

3. **Fix `api.test.ts`** — replace `global.fetch = vi.fn()` with `vi.stubGlobal("fetch", vi.fn())`. Fix the 4 other root-cause test bugs (Prompt 09). 1-2 hours.

4. **Remove `axios`** — migrate `CryptoTicker` to native `fetch`, then `npm uninstall axios`. Resolves Critical CVE. 30 minutes.

5. **Remove unused Redux stack** — `npm uninstall @reduxjs/toolkit react-redux reselect use-sync-external-store immer eventemitter3 es-toolkit clsx decimal.js-light tiny-invariant victory-vendor prop-types`. 15 minutes.

6. **Update `react-router-dom`** — `npm update react-router-dom`. Resolves High XSS vulnerability. 15 minutes.

### SHORT TERM — Sprint 1 (Week 1-2)

7. **Implement WS ticket auth** — call `POST /ws/ticket` before opening WebSocket; use `?ticket=<value>` instead of `?token=<JWT>`.

8. **Handle `WsErrorEvent`** — add `case "error"` to `useBots` message handler; display server errors in UI.

9. **Add nginx security headers + gzip** — update `nginx.conf` with `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Strict-Transport-Security`, `Permissions-Policy`, and `gzip on`.

10. **Move CSP to nginx HTTP header** — remove from `<meta>` tag; add production API URL to `connect-src`; remove `localhost` origins.

11. **Add live trading confirmation modal** — require explicit confirmation before switching from paper to live mode.

12. **Write `useBots` unit tests** — mock `useWebSocket` and `utils/api`; test all 5 WS event handlers.

13. **Add CI pipeline** — add `npm test` step to `cloudbuild.yaml` or create GitHub Actions workflow.

14. **Fix favicon** — regenerate `favicon.ico` at 16×16 and 32×32. Target: <5KB.

### SHORT TERM — Sprint 2 (Week 3-4)

15. **Fix accessibility violations** — heading hierarchy (`<h1>` in nav), `aria-live` regions, contrast failures, `:focus-visible` styles, table `<caption>` elements.

16. **Fix HTML validity** — `BotConsole` (`<ul><pre>`), `BotControls` (buttons in `<ul>`), `Home` (nested `<main>`).

17. **Add `React.memo`** to `BotControls`, `BotConsole`, `TradeHistoryTable`, `ProfitChart`.

18. **Fix `useConfigCheckboxes` exhaustive-deps** — remove `eslint-disable` comment; wrap `fetchFn`/`defaultFn`/`updateFn` in `useCallback` at call sites.

19. **Fix stale `botIds` closure** — use a ref in `useBots` `onmessage` handler.

20. **Write `AuthProvider` tests** — test login/logout/idle timeout state transitions.

21. **Migrate ESLint to flat config** — create `eslint.config.js` with `react-hooks/exhaustive-deps: error`.

### MEDIUM TERM — Month 2-3

22. **Extract `ConfigCheckboxPanel`** — eliminate `Parameters`/`Indicators` duplication.

23. **Batch log updates** — use `requestAnimationFrame` to cap log state updates at 60fps.

24. **Add `AbortController`** to all `fetch` calls in `utils/api.ts`.

25. **Add accessibility tests** — install `jest-axe`; add a11y assertions to component tests.

26. **Add WebSocket integration tests** — use MSW v2 `ws` handler for bot lifecycle flow.

27. **Format financial values** — use `Intl.NumberFormat` for profit values and `Intl.DateTimeFormat` for timestamps.

28. **Add Prettier config file** — commit `.prettierrc` with explicit settings.

### LONG TERM — Month 3-6

29. **Unify bot state machine** — replace `botState` + `botStatus` with `useReducer` and explicit transitions.

30. **Split `useBots`** — separate `useBotLifecycle` and `useTradeHistory` hooks.

31. **Add table sorting and pagination** to `TradeHistoryTable`.

32. **Add `manualChunks` to Vite config** — split Recharts and Netlify Identity into separate vendor chunks.

33. **Remove dead code** — unused pages, components, CSS classes.

34. **Add `noUnusedLocals`/`noUnusedParameters`** to `tsconfig.json`.

---

## 13. Team Recommendations

### Process Improvements

- **Add CI before merging any PR** — the 31 failing tests went undetected because no pipeline runs tests. This is the single highest-leverage process improvement.
- **Add `npm audit --audit-level=high` to CI** — prevents vulnerable dependencies from reaching production.
- **Add TODO comments for known issues** — the codebase has zero TODO/FIXME markers despite multiple known bugs. Track debt in code, not just in documents.
- **Establish a pre-deployment checklist** — at minimum: `npm test` passes, `npm audit` clean, `.env.production` verified, build tested against staging.

### Tool Improvements

- **Fix ESLint** — the linter has been non-functional. Migrating to flat config restores `react-hooks/exhaustive-deps` enforcement, which would have caught the `useConfigCheckboxes` suppression and the `useBots` stale closure.
- **Add `@axe-core/react`** in development — surfaces accessibility violations in the browser console during development, catching issues before they reach review.
- **Add `chunkSizeWarningLimit: 100`** to `vite.config.js` — would have flagged the 379KB and 339KB chunks during development.

### Code Review Focus Areas

- **WebSocket message handlers** — any change to `useBots` should be reviewed for stale closures and missing error handling
- **Environment variable names** — all new env vars must use `VITE_*` prefix
- **WS command messages** — verify all required fields (`botid`, `key`, `type`) are present before sending

### Documentation Needs

- Add inline comments to `useBots` explaining the WS message flow
- Document the three-tier config fallback in `useConfigCheckboxes`
- Add a deployment checklist to the README
- Document the WS ticket auth flow once implemented

---

## 14. Success Metrics

Define these as acceptance criteria for the improvement sprints:

| Metric | Current | Target | How to Measure |
|---|---|---|---|
| Test pass rate | 62% (51/82) | 100% | `npm test` |
| Estimated line coverage | ~35-45% | 80%+ | `vitest --coverage` |
| npm audit vulnerabilities | 1C + 6H + 4M | 0 High/Critical | `npm audit --audit-level=high` |
| Bundle size (gzip) | ~229KB | <150KB | Vite build output |
| Largest chunk (gzip) | 119KB | <100KB | Vite build output |
| nginx gzip enabled | No | Yes | `curl -H "Accept-Encoding: gzip" -I <url>` |
| WCAG AA contrast failures | 2 confirmed | 0 | `jest-axe` + manual check |
| `aria-live` regions | 0 | ≥3 (status, WS, save) | Code review |
| CI pipeline | None | Tests + audit on every PR | CI config |
| ESLint errors | N/A (broken) | 0 errors, 0 warnings | `npm run lint` |
| `useBots` test coverage | 0% | ≥80% | `vitest --coverage` |

---

## 15. Conclusion

### Is sonarftweb production-ready?

**No — not in its current state.** Three issues are hard blockers:

1. The production environment configuration is broken — a production build connects to `http://localhost:8000` over plain HTTP due to the `REACT_APP_*` variable name mismatch. This is a 5-minute fix that must happen before any deployment.

2. The simulation/live trading mode toggle is broken — the server silently rejects the command. Users cannot switch trading modes, and they receive no feedback that the switch failed.

3. The test suite has 31 failing tests and no CI pipeline — the codebase has been shipping with undetected regressions.

### What are the biggest risks?

In order of severity:
1. **Deploying with the broken `.env.production`** — would result in a completely non-functional production deployment
2. **Enabling live trading** before the confirmation modal and broken toggle are fixed — real orders could be placed unexpectedly
3. **JWT exposure in WebSocket URL** — token appears in server access logs in production
4. **`useBots` being entirely untested** — the most complex and highest-risk code path has no safety net

### What should be prioritised?

The immediate fixes (C1-C4) take less than 3 hours combined and unblock everything else. They should be done before any other work. The Sprint 1 items (security headers, WS ticket auth, `useBots` tests, CI) take approximately one week and bring the application to a defensible production baseline.

### Recommended next step

Run the immediate fixes today. Then proceed to Prompt 12 (Implementation Roadmap) to create a structured sprint plan from these findings.

The foundation is solid. The architecture is clean, the code is readable, and the team has clearly applied good engineering practices. The issues identified are concentrated and fixable — this is not a rewrite situation. With 2-3 focused sprints, sonarftweb can reach a strong production baseline.
