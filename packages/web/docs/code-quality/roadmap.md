# sonarftweb — Implementation Roadmap & Action Plan

**Prompt:** 12-implementation-roadmap  
**Category:** Post-Review Planning  
**Date:** July 2025  
**Based on:** [docs/code-quality/consolidation.md](./consolidation.md)

---

## 1. Quick Wins (1–2 days total)

These require no architectural changes — pure configuration, cleanup, and dependency updates.

| # | Task | Why | Effort | File(s) |
|---|---|---|---|---|
| Q1 | Add `npm test` step to `cloudbuild.yaml` | Broken code currently ships undetected | 30 min | `cloudbuild.yaml` | **Completed** — Added `npm ci`, `npm audit --audit-level=high`, and `CI=true npm test -- --watchAll=false` steps before Docker build. Audit step fails on high/critical CVEs. |
| Q2 | Fix `App.test.js` smoke test | `npm test` fails immediately | 30 min | `src/App.test.js` | **Completed** — Replaced broken CRA scaffold test with 4 smoke tests: renders without crash, logo present, Sign In button visible, Crypto nav link present. |
| Q3 | Mock `netlify-identity-widget` in `setupTests.js` | Required for any test rendering `App` | 30 min | `src/setupTests.js` | **Completed** — Added `jest.mock('netlify-identity-widget', ...)` with all 6 widget methods mocked globally. |
| Q4 | Upgrade `axios` to latest | 7 CVEs including CSRF and SSRF | 30 min | `package.json` | **Completed** — v1.4.0 → v1.15.0. Fixes CSRF (GHSA-wf5p-g6vw-rhxx), SSRF (GHSA-8hc4-vh64-cxmj), credential leakage, DoS, and prototype pollution CVEs. |
| Q5 | Upgrade `react-router-dom` to latest | XSS via open redirect CVE | 30 min | `package.json` | **Completed** — v6.15.0 → v6.30.3 (latest v6.x). Stayed on v6 to avoid v7 breaking changes. Fixes XSS via open redirect (GHSA-2w69-qvjg-hvjx). |
| Q6 | Upgrade Node.js in `Dockerfile` from 14 to 20 | EOL since April 2023 — no security patches | 15 min | `Dockerfile` | **Completed** — `node:14` → `node:20-alpine`. Also switched `npm install` → `npm ci` for reproducible CI builds. |
| Q7 | Remove `socket.io-client` from `package.json` | Unused; ~14 KB + its own CVEs | 15 min | `package.json` | **Completed** — Removed `socket.io-client` and `uuid` (only used in orphaned `Config.js`). Both removed from `package.json` and `package-lock.json`. |
| Q8 | Remove CDN `<script>` from `public/index.html` | Widget loaded twice; CDN script has no SRI | 15 min | `public/index.html` | **Completed** — Removed render-blocking Netlify Identity CDN script. Widget is already bundled via npm package. |
| Q9 | Set `GENERATE_SOURCEMAP=false` in build script | Source code exposed in production DevTools | 5 min | `package.json` | **Completed** — `build` script now runs `GENERATE_SOURCEMAP=false react-scripts build`. |
| Q10 | Move URLs to env vars | Hardcoded `localhost` breaks any deployment | 1 hour | `constants.js`, `.env` | **Completed** — `constants.js` reads `REACT_APP_API_URL` / `REACT_APP_WS_URL` with localhost fallbacks. `.env.development.example` and `.env.production.example` committed as templates. Actual `.env.*` files added to `.gitignore`. |
| Q11 | Delete 13 dead files/symbols | Reduces confusion; removes dead CVE surface | 30 min | See list below | **Completed** — Deleted 25 files: `App_Trading.js`, `NavBar_Trading.js`, entire `src/components/Config/` directory (17 files including all sub-components), `ParametersProvider.js`, `WebSocketContext.js`, `sonarft_bg.jpg`, `public/sonarftlogo.png`, `public/defaultParameters.json`, `public/defaultIndicators.json`. Removed `getBotId` (singular) function from `api.js`. |
| Q12 | Remove all 38 `console.log` statements | Sensitive data in production logs | 1 hour | `api.js`, hooks, components | **Completed** — Removed all `console.log`/`console.error` from `api.js`, `useWebSocket.jsx`, `Parameters.js`, `Indicators.js`, `CryptoTicker.js`, `CChatGPT.js`. Also dropped the debug-only readyState `useEffect` from `useWebSocket.jsx`. Zero `console.*` calls remain in `src/`. |
| Q13 | Fix `key={index}` → stable keys in `Bots.js` | Incorrect reconciliation on list updates | 30 min | `Bots.js` | **Completed** — Bot selector `<option>` uses `key={botId}`; order rows use `key={timestamp-exchange-index}`; trade rows same pattern. Removed commented-out debug log. |
| Q14 | Fix `Terciary` typo in CSS | Footer background falls back to browser default | 10 min | `variables.css`, `footer.css` | **Completed** — Renamed `--textTerciary` → `--textTertiary` and `--backgroundTerciary` → `--backgroundTertiary` across `variables.css`, `footer.css`, `welcome.css`, `navbar.css`, `building.css`. Also removed 5 dead `:root_`/`:root__` inactive theme blocks from `variables.css`. |

**Dead files to delete (Q11):**
- `src/App_Trading.js`
- `src/components/NavBar/NavBar_Trading.js`
- `src/components/Config/Config.js` (and its sub-component dirs if empty)
- `src/components/Parameters/ParametersProvider.js`
- `src/components/Config/IndicatorsProvider.js`
- `src/components/Config/ValidatorsProvider.js`
- `src/hooks/WebSocketContext.js`
- `src/assets/img/sonarft_bg.jpg`
- `public/sonarftlogo.png`
- `public/defaultParameters.json`
- `public/defaultIndicators.json`
- `getBotId` function in `src/utils/api.js`

**Total Quick Wins effort: ~6 hours**

---

## 2. Short-term Plan (Sprint 1 — 2 weeks)

### Security Track

| Task | Description | Effort | Priority | Acceptance Criteria |
|---|---|---|---|---|
| S1 — Backend auth | Retrieve Netlify JWT via `netlifyIdentity.currentUser().token.access_token`; add `Authorization: Bearer` header to all `fetch` calls in `api.js`; pass token as query param on WebSocket URL | 1 day | Critical | All sonarft API calls include auth header; WS URL includes token; sonarft backend validates JWT | **Completed** — Added `getAuthToken()` (exported for WS use) and `getAuthHeaders()` helpers. All 9 fetch calls use `{ ...baseHeaders, ...getAuthHeaders() }`. `baseHeaders` constant eliminates per-call header duplication. |
| S2 — WS auth | Pass token as `?token=` query param on WebSocket connect URL | 2 hours | High | `useWebSocket` accepts optional token param; URL constructed with token | **Completed** — `Bots.js` calls `getAuthToken()` and appends `?token={encodeURIComponent(token)}` to the WS URL. Falls back to unauthenticated URL if no token (e.g. during testing). |
| S3 — CSP header | Add `<meta http-equiv="Content-Security-Policy">` to `public/index.html` | 2 hours | High | CSP blocks inline scripts; allows sonarft API and CoinGecko origins | **Completed** — Added CSP meta tag: `default-src 'self'`, `script-src 'self'`, `style-src 'self' 'unsafe-inline'`, `connect-src` allows localhost + CoinGecko + Netlify, `frame-ancestors 'none'`, `base-uri 'self'`, `form-action 'self'`. Update `connect-src` in production to replace localhost with actual API domain. |
| S4 — HTTPS env | Ensure `REACT_APP_API_URL` uses `https://` and `REACT_APP_WS_URL` uses `wss://` in production `.env` | 1 hour | High | Production build connects over TLS | **Completed** — Completed as part of Q10. `.env.production.example` updated with reminder to also update CSP `connect-src` for production URLs. |

### WebSocket Track

| Task | Description | Effort | Priority | Acceptance Criteria |
|---|---|---|---|---|
| W1 — Fix memory leak | Add `shouldReconnect` ref to `useWebSocket.jsx`; set `false` in cleanup; guard `connect()` call | 2 hours | High | Unmounting `Bots` does not create orphaned socket; verified by test | **Completed** — `shouldReconnect` ref set to `false` in cleanup; `connect()` returns early if `!shouldReconnect.current`; `attemptRef` tracks backoff count and resets on open. |
| W2 — Add `onerror` handler | Add `ws.onerror` in `useWebSocket.jsx`; expose `wsError` state | 1 hour | High | WS errors logged and surfaced to consumer | **Completed** — `ws.onerror` sets `wsError` state; hook returns `{ socket, wsOpen, wsError }`; `Bots.js` renders error banner when `wsError` is set. |
| W3 — Connection status UI | Use `wsOpen` state in `Bots.js` to show "Connected / Disconnected" badge | 2 hours | High | User sees connection status at all times | **Completed** — `● Connected` / `○ Disconnected` badge rendered next to Bots heading; green/amber CSS classes in `bots.css`. Also added `overflow-x: auto` to `.tables-container` (U3). |
| W4 — Backoff reconnect | Replace immediate reconnect with `setTimeout(connect, delay)` using exponential backoff (1s, 2s, 4s, 8s, 30s cap) | 2 hours | Medium | Reconnect attempts are spaced; server not hammered on restart | **Completed** — Backoff: 1s, 2s, 4s, 8s, 16s, 30s cap. Attempt counter resets to 0 on successful open. |

### UX Track

| Task | Description | Effort | Priority | Acceptance Criteria |
|---|---|---|---|---|
| U1 — Action feedback | Add `saveStatus` state to `Parameters` and `Indicators`; show "Saved ✓" or "Error — try again" after POST | 2 hours | High | User sees result of every "Set" button click | **Completed** — `saveStatus` state (`null`/`saving`/`saved`/`error`) added to both components. Button disabled during save. `✓ Saved` (green) / `✗ Error — try again` (red) badge auto-clears after 3s. `.save-row` and `.save-status--*` CSS added. |
| U2 — Bot removal confirm | Add `window.confirm()` or a simple modal before `handleRemoveButtonClick` fires | 1 hour | High | User must confirm before bot is removed | **Completed** — `window.confirm()` added to `handleRemoveButtonClick`; returns early if user cancels. |
| U3 — Table overflow fix | Add `overflow-x: auto` to `.tables-container` in `bots.css` | 15 min | High | Tables scroll horizontally on mobile/tablet | **Completed** — Added as part of W3. |
| U4 — Error states | Add `error` state to `Bots.js` `fetchBotIds`; render error message if fetch fails | 1 hour | High | User sees "Could not load bots" instead of empty UI | **Completed** — `fetchError` state added; catch block sets message; error banner rendered using existing `.bots-ws-error` CSS class. |
| U5 — Add try/catch | Add try/catch to `getBotIds`, `getOrders`, `getTrades` in `api.js` | 1 hour | High | No unhandled promise rejections | **Completed** — `getBotIds` wrapped in try/catch and re-throws (caller handles UI); `getOrders`/`getTrades` return `null` on network failure (consistent with existing `!response.ok` behaviour). |

### Testing Track — Phase 1 (Critical paths)

| Task | Description | Effort | Priority |
|---|---|---|---|
| T1 — `utils/api.js` tests | Test all 10 functions: success, HTTP error, network error, fallback chain | 1 day | High | **Completed** — 26 test cases across 9 describe blocks. Covers: success paths, HTTP errors, network failures, fallback to local JSON, Authorization header injection, POST body format. |
| T2 — `utils/helpers.js` tests | Test `fetchAllOrders` and `fetchAllTrades` aggregation | 2 hours | Medium | **Completed** — 7 test cases. Covers: multi-bot aggregation, null response skipping, empty botIds array. |
| T3 — `useWebSocket` tests | Test connect, wsOpen state, cleanup (memory leak regression), onerror | 1 day | High | **Completed** — 11 test cases across 4 describe blocks. Covers: connection, wsOpen/wsError state, memory leak regression (W1 — no reconnect after unmount), socket close on unmount, exponential backoff timing. |
| T4 — Create `src/mocks/fixtures.js` | Shared test data: `mockUser`, `mockBotIds`, `mockOrder`, `mockParameters`, `mockIndicators` | 2 hours | Medium | **Completed** — `mockUser`, `mockBotIds`, `mockOrder`, `mockTrade`, `mockParameters`, `mockIndicators`, `mockResponse` helper. |

**Sprint 1 total effort: ~10 days**

---

## 3. Medium-term Plan (Month 2 — Architecture & Quality)

### Component Refactoring

**M1 — Extract `PrivateRoute` (0.5 day)** — **Completed**

`src/components/PrivateRoute/PrivateRoute.js` created as a 5-line functional component. Removed 4 identical inline `function PrivateRoute` definitions from `Crypto.js`, `Dex.js`, `Forex.js`, `Token.js`. All `Navigate` imports removed from page files. Added `PrivateRoute.test.js` with 3 test cases (truthy value renders children, null redirects, undefined redirects).
```
src/components/PrivateRoute/PrivateRoute.js
```
Remove 4 identical inline definitions. Single import everywhere.

**M2 — Refactor `Parameters` + `Indicators` to functional (3 days)** — **Completed**

Created `src/hooks/useConfigCheckboxes.js` (105 lines) encapsulating all shared logic:
- Synchronous localStorage hydration in `useState` initialiser
- 3-tier async load in `useEffect`: server → localStorage → bundled defaults
- `handleCheckboxChange` with `useCallback` — updates state + localStorage atomically
- `handleSave` with `useCallback` — manages `saveStatus` lifecycle

`Parameters.js` refactored from 140-line class to 74-line functional component.
`Indicators.js` refactored from 140-line class to 76-line functional component.
Both now use `useConfigCheckboxes` with their specific API functions and state keys.

No class components remain in the codebase except `ErrorBoundary` (required by React).

Added `useConfigCheckboxes.test.js` with 8 test cases covering all 3 fallback tiers, checkbox interaction, localStorage sync, save success, and save error.

Extract shared hook:
```
src/hooks/useConfigCheckboxes.js
  - accepts: { fetchFn, updateFn, storageKey, defaultFn }
  - returns: { state, handleCheckboxChange, handleSetClick, isLoading, error, saveStatus }
```
Replace both class components with functional wrappers using this hook.

**M3 — Split `Bots.js` (3 days)** — **Completed**

Original 290-line monolithic `Bots.js` split into 5 focused files:

- `src/hooks/useBots.js` (126 lines) — all state, WebSocket, and data fetching. Exports `BotState` enum. Handlers wrapped in `useCallback`.
- `src/components/Bots/BotControls.js` (59 lines) — create/select/remove buttons. `aria-label` added to bot selector. `wsOpen` gates remove button.
- `src/components/Bots/BotConsole.js` (25 lines) — log `<pre>` with auto-scroll ref.
- `src/components/Bots/TradeHistoryTable.js` (69 lines) — reusable table used for both orders and trades (eliminates the duplicate table). Full PropTypes with shape.
- `src/components/Bots/Bots.js` (71 lines) — thin orchestrator composing the above.

Added `TradeHistoryTable.test.js` with 5 test cases.
```
src/hooks/useBots.js              — WS + state machine + fetches
src/components/Bots/BotControls.js — create/select/remove buttons
src/components/Bots/BotConsole.js  — log <pre> display
src/components/Bots/TradeHistoryTable.js — reusable for orders + trades
src/components/Bots/Bots.js        — orchestrator only
```

**M4 — Add `ErrorBoundary` (0.5 day)** — **Completed**

`src/components/ErrorBoundary/ErrorBoundary.js` created as a class component using `getDerivedStateFromError`. Fallback UI shows "Something went wrong" heading, description, and "Try again" button that resets error state. Error message detail shown only in `development` mode. Wrapped the trading content inside `<Crypto>` (inside `<PrivateRoute>`). Added `ErrorBoundary.test.js` with 4 test cases: normal render, fallback on throw, children hidden in error state, reset on Try again click.
```
src/components/ErrorBoundary/ErrorBoundary.js
```
Wrap `<Crypto>` page. Show "Something went wrong — reload" fallback.

### Performance

**M5 — Code splitting (0.5 day)** — **Completed**

All 4 page routes (`Home`, `Crypto`, `CryptoChatGPT`, `Doggy`) converted to `React.lazy` dynamic imports in `App.js`. Layout components (`Header`, `Footer`, `CryptoTicker`) remain static imports as they render on every page. `<Suspense fallback={<PageLoader />}>` wraps the `<Routes>` block. `App.test.js` updated to use `waitFor` to handle async Suspense resolution. Estimated ~60 KB reduction in initial bundle (trading components deferred until `/crypto` is visited).
Add `React.lazy` + `Suspense` to all routes in `App.js`. Estimated ~60 KB reduction in initial bundle.

**M6 — Cap log array (0.5 day)** — **Completed**

`logs` state in `Bots.js` changed from an unbounded string to an array. Each message appended via `setLogs(prev => { const next = [...prev, event.data]; return next.length > MAX_LOG_LINES ? next.slice(-MAX_LOG_LINES) : next; })`. Rendered with `logs.join("\n")`. `MAX_LOG_LINES = 500` constant defined at module level. Eliminates the memory leak and increasingly expensive re-renders for long-running sessions.
Replace `logs` string with capped array (500 entries max) in `Bots.js`.

**M7 — Parallel fetches (0.5 day)** — **Completed**

`helpers.js` rewritten: both `fetchAllOrders` and `fetchAllTrades` now use `Promise.all(botIds.map(...))` + `filter(Boolean).flat()`. Reduces N sequential HTTP requests to a single parallel batch. With 5 bots and 200ms average response time, table refresh time drops from ~1s to ~200ms. `helpers.test.js` updated with 2 additional parallel-execution tests.
Replace `for await` loop in `helpers.js` with `Promise.all`.

**M8 — Memoize `AuthContext` (0.5 day)** — **Completed**

`AuthProvider.js` updated: `handleLogin`, `handleLogout`, `handleLoginSuccess`, `handleLogoutSuccess` all wrapped in `useCallback` with stable empty dependency arrays. Context value wrapped in `useMemo([user, handleLogin, handleLogout])` — only creates a new object when `user` changes. `useEffect` dependency array now correctly lists `handleLoginSuccess` and `handleLogoutSuccess` (previously missing, causing a lint warning). All 5 context consumers (`NavBar`, `Crypto`, `Dex`, `Forex`, `Token`) no longer re-render on unrelated `AuthProvider` renders.
Wrap `handleLogin`/`handleLogout` in `useCallback`; memoize context value with `useMemo`.

### Testing — Phase 2 (Component tests)

**M9 — `Parameters` + `Indicators` tests (2 days)**
Test 3-tier fallback chain, localStorage sync, POST on button click, error state.

**M10 — `Bots.js` tests (3 days)**
Mock WebSocket + API. Test bot creation flow, message handling, order/trade refresh, empty states.

**M11 — `Crypto.js` tests (1 day)**
Test PrivateRoute redirects unauthenticated users; renders trading components for authenticated users.

**M12 — Install `jest-axe` + a11y tests (1 day)**
Add accessibility assertions to all component tests. Will catch heading hierarchy and missing label issues.

### Code Quality

**M13 — Add PropTypes to all components (1 day)** — **Completed**

Added `prop-types` v15.8.1 to `package.json`. PropTypes added to all 5 components that receive external props:
- `Bots`: `user: shape({ id: string.isRequired, email: string }).isRequired`
- `Parameters`: `clientId: string.isRequired`
- `Indicators`: `clientId: string.isRequired`
- `PrivateRoute`: `children: node.isRequired`, `value: any` (default `null`)
- `ErrorBoundary`: `children: node.isRequired`

Components that only consume context (`NavBar`, `Crypto`, `Dex`, `Forex`, `Token`) have no external props and do not need PropTypes.
Start with `Bots`, `Parameters`, `Indicators`, `NavBar`, `Crypto`.

**M14 — Remove inline styles (0.5 day)** — **Completed**

All inline `style={{}}` props removed from source files. Zero inline styles remain in `src/`:
- `NavBar.js`: 4× `style={{ textDecoration: "none" }}` → `.nav-link` class in `navbar.css`
- `Bots.js`: 2× opacity inline styles → `.btn-disabled` class in `bots.css`
- `App.js`: `PageLoader` inline styles → `.page-loader` class in `App.css` (also added `App.css` import)
Move `style={{ textDecoration: "none" }}` to CSS class; move opacity logic to CSS class toggle.

**M15 — Add ESLint rules to CI (0.5 day)** — **Completed**

Added three ESLint rules to `eslintConfig` in `package.json`:
- `no-console: warn` — flags any `console.*` call (all removed in Q12, so zero warnings)
- `no-unused-vars: warn` — flags unused imports and variables
- `react/prop-types: warn` — flags missing PropTypes (all added in M13)

Added `lint` script: `eslint src/ --ext .js,.jsx --max-warnings=0` — any warning fails CI.

Added lint step to `cloudbuild.yaml` between `npm ci` and `npm audit`. CI pipeline order: install → lint → audit → test → build → deploy.
Add `npm run eslint` step to `cloudbuild.yaml`. Add `no-console` rule to ESLint config.

**Month 2 total effort: ~20 days**

---

## 4. Long-term Plan (Month 3–6)

| Task | Description | Effort |
|---|---|---|
| L1 — Structured WS protocol | Coordinate with sonarft backend to send JSON events instead of log strings | 3 days (both sides) | **Completed** — Backend: `send_logs()` wraps every log in `{"type":"log","level","message","ts"}` and emits `bot_created`, `bot_removed`, `order_success`, `trade_success` structured events. Frontend: `parseMessage()` in `useBots.js` parses JSON and dispatches via `switch(msg.type)`; plain-text fallback for legacy compatibility. String-matching (`includes()`) fully retired from `useBots.js`. |
| L2 — Data visualization | Add Recharts for P&L curve, trade frequency chart | 5 days | **Completed** — `recharts` v3.8.1 added. `ProfitChart` component: cumulative P&L area chart, custom tooltip, reference line at zero, gradient fill (green/red). Shown above trade history table in `Bots.js`. |
| L3 — Bot status indicator | Show running/stopped/error badge per bot using WS events | 2 days | **Completed** — `BotStatus` enum (IDLE/RUNNING/ERROR) in `useBots.js`. Set RUNNING on `bot_created`, IDLE on `bot_removed`. Colored badge in `Bots.js` heading. |
| L4 — Paper vs live toggle | UI control for `is_simulating_trade` config | 2 days | **Completed** — `isSimulating` state + `handleToggleSimulation` in `useBots.js`. Toggle button replaces hardcoded label. Sends `set_simulation` WS command. Backend wired in `sonarft_server.py`. |
| L5 — MSW integration tests | Install MSW; write full user workflow tests | 5 days | **Completed** — `msw` v2.13.3 added. `handlers.js` covers all 9 endpoints. `server.js` for Jest/Vitest. MSW lifecycle in `setupTests.js`. 8 integration tests in `src/integration/workflows.test.js`. |
| L6 — TypeScript migration | Start with `utils/api.js` and `utils/helpers.js`; expand incrementally | 10 days | **Completed (Phase 1)** — `tsconfig.json` added. `api.ts` with `TradeRecord`, `ParametersConfig`, `IndicatorsConfig` interfaces. `helpers.ts` with typed filter predicate. Incremental — JS files coexist. |
| L7 — Vite migration | Replace CRA with Vite for faster builds, better tree-shaking | 3 days | **Completed** — `react-scripts` replaced with `vite` v8 + `@vitejs/plugin-react`. `vitest` replaces Jest. `vite.config.js` with `REACT_APP_` env prefix. Root `index.html` created. CI updated. |
| L8 — Performance monitoring | Configure `reportWebVitals` with reporting endpoint | 1 day | **Completed** — Created `src/utils/vitals.js` with `sendVitals` function. Dev: logs `[Web Vitals] LCP: 1200ms (good)` to console. Prod: sends JSON beacon via `navigator.sendBeacon` (non-blocking, survives page unload) to `REACT_APP_VITALS_URL`; falls back to `fetch` with `keepalive: true`; silently no-ops if URL not configured. `index.js` updated to pass `sendVitals` to `reportWebVitals`. Env example files updated with `REACT_APP_VITALS_URL` documentation. |
| L9 — Idle session timeout | Auto-logout after N minutes of inactivity | 1 day | **Completed** — Created `src/hooks/useIdleTimeout.js`: resets on `mousemove`, `keydown`, `mousedown`, `touchstart`, `scroll`; uses `useRef` for timer and stable `onIdle` reference; cleans up on unmount and when disabled. Wired into `AuthProvider.js` with `!!user` guard (only active when logged in). Default 30 minutes; configurable via `REACT_APP_IDLE_TIMEOUT_MS`. Added `useIdleTimeout.test.js` with 5 test cases. |
| L10 — Tooltips on indicators | Add `title` attributes or tooltip component to all indicator/parameter labels | 2 days | **Completed** — Added `TOOLTIPS` constant maps to `Parameters.js` and `Indicators.js`. Every `<label>` now has `title={categoryTooltips[item] ?? item}`. Covers: 5 periods (5min–1h), 6 oscillators (RSI, Stochastic, MACD, StochRSI, Momentum, Awesome Oscillator), 5 moving averages (EMA/SMA 10/30, Ichimoku), 3 exchanges (Binance, OKX, Kraken), 2 symbols (BTC/USDT, ETH/USDT). Fallback to item name if no tooltip defined. |

---

## 5. Timeline

```
Week 1–2   QUICK WINS + SPRINT 1
  ├── Day 1:   Q1–Q9 (CI, test fix, dependency upgrades, env vars)
  ├── Day 2:   Q10–Q14 (dead files, console.log, keys, typo)
  ├── Day 3–4: S1–S4 (backend auth, CSP, HTTPS)
  ├── Day 5–6: W1–W4 (WS memory leak, onerror, status UI, backoff)
  ├── Day 7–8: U1–U5 (action feedback, confirm dialog, table fix, error states)
  └── Day 9–10: T1–T4 (api.js tests, helpers tests, WS hook tests, fixtures)

Month 2    ARCHITECTURE & QUALITY
  ├── Week 3:  M1–M4 (PrivateRoute, Parameters/Indicators refactor, ErrorBoundary)
  ├── Week 4:  M5–M8 (code splitting, log cap, parallel fetches, AuthContext memo)
  ├── Week 5:  M9–M12 (component tests, Bots tests, a11y tests)
  └── Week 6:  M13–M15 (PropTypes, inline styles, ESLint CI)

Month 3–6  LONG-TERM
  ├── Month 3: L1–L4 (structured WS, data viz, bot status, paper/live toggle)
  ├── Month 4: L5–L6 (MSW tests, TypeScript start)
  └── Month 5–6: L7–L10 (Vite, monitoring, session timeout, tooltips)
```

---

## 6. Security Action Plan

| Issue | Risk | Fix | Effort | Verify |
|---|---|---|---|---|
| No backend auth | Full API access without credentials | Add `Authorization: Bearer {jwt}` to all fetch calls | 1 day | Confirm sonarft returns 401 without token |
| HTTP backend | Plaintext traffic in production | Set `REACT_APP_API_URL=https://...` in production env | 1 hour | Check Network tab shows HTTPS |
| WS unauthenticated | Bot commands sent without identity | Pass token as `?token=` on WS URL | 2 hours | Confirm sonarft validates WS token |
| No CSP | Script injection unrestricted | Add CSP meta tag to `index.html` | 2 hours | Use browser CSP evaluator tool |
| CDN script no SRI | Compromised CDN = XSS | Remove CDN script (use npm package only) | 15 min | Verify widget still works |
| 63 npm CVEs | Runtime and build vulnerabilities | `npm audit fix`; manual upgrades for breaking changes | 2 hours | `npm audit` shows 0 critical/high |
| Source maps in prod | Source code exposed | `GENERATE_SOURCEMAP=false` | 5 min | Verify no `.map` files in build output |

---

## 7. Performance Improvements Plan

| Issue | Current | Target | Approach | Effort | Measure |
|---|---|---|---|---|---|
| No code splitting | ~147 KB single bundle | <100 KB initial | `React.lazy` on all routes | 0.5 day | Bundle analyzer output |
| Unused `socket.io-client` | ~14 KB in bundle | 0 KB | Remove from `package.json` | 15 min | Bundle size diff |
| Double Netlify widget | ~50 KB loaded twice | ~50 KB once | Remove CDN script | 15 min | Network tab |
| Log string unbounded | Grows indefinitely | Max 500 lines | Array with `slice(-500)` | 0.5 day | Memory profiler |
| Sequential fetches | O(n) requests | O(1) parallel | `Promise.all` in helpers.js | 0.5 day | Network waterfall |
| No memoization | Re-renders on every context change | Stable references | `useCallback`/`useMemo` in AuthProvider | 0.5 day | React DevTools profiler |

---

## 8. Testing Roadmap

**Current coverage: ~0%  |  Target: ≥70%**

### Phase 1 — Critical paths (Sprint 1, Week 2)
- `utils/api.js` — 10 functions, all error paths and fallback logic (~40 test cases)
- `utils/helpers.js` — 2 functions (~6 test cases)
- `useWebSocket.jsx` — connect, reconnect guard, cleanup, onerror (~10 test cases)

**Estimated coverage after Phase 1: ~25%**

### Phase 2 — Component tests (Month 2, Week 5)
- `Parameters.js` — 3-tier fallback, localStorage, POST, error state (~15 test cases)
- `Indicators.js` — same pattern (~15 test cases)
- `Bots.js` — bot creation flow, WS messages, order/trade refresh (~25 test cases)
- `Crypto.js` — PrivateRoute auth gate (~5 test cases)
- `AuthProvider.js` — login, logout, session restore (~8 test cases)

**Estimated coverage after Phase 2: ~60%**

### Phase 3 — Integration tests (Month 3)
- Install MSW; create handlers for all sonarft endpoints
- Full bot creation workflow test
- Parameters save workflow test
- WebSocket disconnect + reconnect test

**Estimated coverage after Phase 3: ≥70%**

### Coverage threshold (add to `package.json` after Phase 2):
```json
"jest": {
  "coverageThreshold": {
    "global": { "lines": 60, "functions": 60, "branches": 50 }
  }
}
```

---

## 9. Code Quality Improvements

| Task | Approach | Effort | When |
|---|---|---|---|
| Remove `console.log` | Replace with `if (process.env.NODE_ENV !== 'production') console.log(...)` or remove | 1 hour | Quick wins |
| Add `no-console` ESLint rule | Add to `eslintConfig` in `package.json` | 15 min | Quick wins |
| PropTypes | Add to all components with props; start with `Bots`, `Parameters`, `Indicators` | 1 day | Month 2 |
| Fix `key={index}` | Use `botId`, `order.timestamp + order.buy_exchange`, coin name as keys | 30 min | Quick wins |
| Extract `PrivateRoute` | Single shared component | 30 min | Month 2 |
| Enforce Prettier in CI | Add `npx prettier --check "src/**/*.js"` to `cloudbuild.yaml` | 15 min | Month 2 |
| JSDoc on `api.js` | Document all 10 exported functions | 1 hour | Month 2 |

---

## 10. Dependency & Tooling Updates

| Package | Action | When | Breaking? |
|---|---|---|---|
| `axios` | Upgrade to latest | Quick wins | Unlikely |
| `react-router-dom` | Upgrade to latest v6.x | Quick wins | Unlikely |
| `socket.io-client` | Remove entirely | Quick wins | No — unused |
| `uuid` | Remove (only used in orphaned Config.js) | Quick wins | No |
| `web-vitals` | Keep; add reporting callback | Month 2 | No |
| `react-scripts` | Consider Vite migration | Month 5–6 | Yes — major |
| Node.js (Docker) | 14 → 20 LTS | Quick wins | No |
| Add `jest-axe` | `npm install --save-dev jest-axe` | Month 2 | No |
| Add `msw` | `npm install --save-dev msw` | Month 3 | No |
| Run `npm audit` in CI | Add to `cloudbuild.yaml` | Quick wins | No |

---

## 11. Risk & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| sonarft backend doesn't validate JWT | Medium | Auth fix is incomplete | Coordinate backend JWT validation in parallel with frontend work |
| Dependency upgrades break functionality | Low | Regression in routing or API calls | Run full manual smoke test after each upgrade; add tests first |
| Refactoring `Parameters`/`Indicators` introduces bugs | Medium | Config saving breaks | Write tests before refactoring (test-first) |
| WS structured protocol requires sonarft changes | High | L1 blocked on backend work | Keep string-matching as fallback during transition |
| TypeScript migration scope creep | High | Delays other work | Migrate one file at a time; don't block other work |

---

## 12. Success Criteria

| Metric | Current | Sprint 1 Target | Month 2 Target | Month 6 Target |
|---|---|---|---|---|
| `npm test` passes | ❌ Fails | ✅ Passes | ✅ Passes | ✅ Passes |
| CI runs tests | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| Test coverage | ~0% | ~25% | ~60% | ≥70% |
| Critical/High CVEs | 32 | 0 | 0 | 0 |
| Backend auth implemented | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| Bundle size (gzipped) | ~147 KB | ~120 KB | <100 KB | <80 KB |
| `console.log` in production | 38 | 0 | 0 | 0 |
| Dead files | ~13 | 0 | 0 | 0 |
| Components with PropTypes | 0% | 0% | 100% | 100% |
| User feedback on actions | None | Parameters/Indicators | All components | All components |
| Accessibility violations | Multiple | Table overflow fixed | WCAG AA | WCAG AA |

---

## 13. Detailed Sprint 1 Plan

### Week 1 — Security & Stability

| Day | Tasks | Owner | Hours |
|---|---|---|---|
| Mon | Q1–Q9: CI test step, fix App.test.js, mock netlify widget, upgrade axios + react-router-dom, Node 20, remove socket.io-client, remove CDN script, GENERATE_SOURCEMAP=false | Dev | 4h |
| Tue | Q10–Q14: env vars for URLs, delete dead files, remove console.log, fix key={index}, fix typo | Dev | 4h |
| Wed | S1: Backend auth — fetch JWT, add Authorization header to all api.js calls | Dev | 6h |
| Thu | S2–S4: WS auth token, CSP meta tag, verify HTTPS env config | Dev | 4h |
| Fri | W1–W2: Fix WS memory leak (shouldReconnect ref), add onerror handler | Dev | 4h |

### Week 2 — UX & Testing

| Day | Tasks | Owner | Hours |
|---|---|---|---|
| Mon | W3–W4: Connection status badge in Bots.js, exponential backoff reconnect | Dev | 4h |
| Tue | U1–U3: Action feedback on Parameters/Indicators, bot removal confirm dialog, table overflow fix | Dev | 6h |
| Wed | U4–U5: Error states in Bots.js, add try/catch to getBotIds/getOrders/getTrades | Dev | 4h |
| Thu | T1: Write tests for utils/api.js (all 10 functions, error paths, fallback chain) | Dev | 6h |
| Fri | T2–T4: helpers.js tests, useWebSocket tests, create fixtures.js | Dev | 6h |

**Sprint 1 total: ~48 hours (2 developers × 1 week, or 1 developer × 2 weeks)**

---

## 14. Communication Plan

| Cadence | Audience | Content |
|---|---|---|
| End of Sprint 1 | Team | Demo: auth working, tests passing, CI green |
| End of Month 2 | Stakeholders | Coverage report, security scan results, refactoring complete |
| Monthly | All | Metrics dashboard: coverage %, CVE count, bundle size |
| On completion of L1 | Team | Structured WS protocol live — retire string matching |

---

**Save location:** `docs/code-quality/roadmap.md`
