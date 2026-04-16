# sonarftweb — Implementation Schedule

**Started:** July 2025  
**Status legend:** ⬜ Pending | 🔄 In Progress | ✅ Done

---

## Quick Wins (Day 1–2)

| # | Task | Status | Notes |
|---|---|---|---|
| Q1 | Add `npm test` step to `cloudbuild.yaml` | ✅ | Added `npm ci`, `npm audit --audit-level=high`, and `CI=true npm test` steps before Docker build |
| Q2 | Fix `App.test.js` smoke test | ✅ | Replaced broken CRA scaffold with 4 smoke tests: renders, logo, sign-in button, nav link |
| Q3 | Mock `netlify-identity-widget` in `setupTests.js` | ✅ | Added global mock in `setupTests.js`; all 6 widget methods mocked |
| Q4 | Upgrade `axios` to latest | ✅ | v1.4.0 → v1.15.0 (fixes 7 CVEs: CSRF, SSRF, DoS, prototype pollution) |
| Q5 | Upgrade `react-router-dom` to latest | ✅ | v6.15.0 → v6.30.3 latest v6.x (fixes XSS via open redirect CVE; stayed on v6 to avoid v7 breaking changes) |
| Q6 | Upgrade Node.js in `Dockerfile` from 14 to 20 | ✅ | `node:14` → `node:20-alpine`; also switched `npm install` → `npm ci` for reproducible builds |
| Q7 | Remove `socket.io-client` from `package.json` | ✅ | Removed `socket.io-client` and `uuid` (only used in orphaned `Config.js`) |
| Q8 | Remove CDN `<script>` from `public/index.html` | ✅ | Removed render-blocking Netlify Identity CDN script; npm package already bundled |
| Q9 | Set `GENERATE_SOURCEMAP=false` in build script | ✅ | Added to `build` script in `package.json`; source code no longer exposed in production |
| Q10 | Move URLs to environment variables | ✅ | `constants.js` now reads `REACT_APP_API_URL` / `REACT_APP_WS_URL` with localhost fallbacks; `.env.development.example` and `.env.production.example` committed as templates; actual `.env.*` files gitignored |
| Q11 | Delete 13 dead files/symbols | ✅ | Removed `App_Trading.js`, `NavBar_Trading.js`, entire `Config/` dir (17 files), `ParametersProvider.js`, `WebSocketContext.js`, `sonarft_bg.jpg`, `public/sonarftlogo.png`, `public/defaultParameters.json`, `public/defaultIndicators.json`; removed `getBotId` from `api.js` |
| Q12 | Remove all 38 `console.log` statements | ✅ | Removed from `api.js`, `useWebSocket.jsx` (+ dropped debug readyState `useEffect`), `Parameters.js`, `Indicators.js`, `CryptoTicker.js`, `CChatGPT.js`; 0 `console.*` calls remain in `src/` |
| Q13 | Fix `key={index}` → stable keys in `Bots.js` | ✅ | Bot selector uses `key={botId}`; order/trade rows use `key={timestamp-exchange-index}`; removed commented-out debug log |
| Q14 | Fix `Terciary` typo in CSS | ✅ | Renamed `--textTerciary` → `--textTertiary` and `--backgroundTerciary` → `--backgroundTertiary` across 5 CSS files; also removed 5 dead `:root_`/`:root__` theme variant blocks from `variables.css` |

---

## Sprint 1 — Security Track

| # | Task | Status | Notes |
|---|---|---|---|
| S1 | Add `Authorization: Bearer` header to all sonarft API calls | ✅ | Added `getAuthToken()` and `getAuthHeaders()` helpers to `api.js`; all 9 fetch calls now include `Authorization: Bearer {jwt}`; `baseHeaders` constant eliminates header duplication |
| S2 | Pass auth token on WebSocket connect URL | ✅ | `Bots.js` appends `?token={jwt}` to WS URL when token is available; falls back to unauthenticated URL gracefully |
| S3 | Add Content Security Policy meta tag | ✅ | Added CSP to `public/index.html`: `default-src 'self'`, `script-src 'self'`, `connect-src` allows localhost + CoinGecko + Netlify, `frame-ancestors 'none'`, `base-uri 'self'`, `form-action 'self'` |
| S4 | Add `.env.production` with HTTPS/WSS URLs | ✅ | Already completed as part of Q10; `.env.production.example` updated with CSP note |

---

## Sprint 1 — WebSocket Track

| # | Task | Status | Notes |
|---|---|---|---|
| W1 | Fix WebSocket memory leak (`shouldReconnect` ref) | ✅ | `shouldReconnect` ref set to `false` in cleanup; `connect()` guards on `shouldReconnect.current`; `attemptRef` tracks backoff attempt count |
| W2 | Add `onerror` handler + expose `wsError` state | ✅ | `ws.onerror` sets `wsError` state; returned from hook; `Bots.js` shows error banner when `wsError` is set |
| W3 | Add connection status badge to `Bots.js` | ✅ | `● Connected` / `○ Disconnected` badge next to Bots heading; styled with green/amber CSS classes; also added `overflow-x: auto` to tables container (U3) |
| W4 | Exponential backoff reconnect | ✅ | Backoff: 1s, 2s, 4s, 8s, 16s, 30s cap; attempt counter resets on successful open |

---

## Sprint 1 — UX Track

| # | Task | Status | Notes |
|---|---|---|---|
| U1 | Action feedback on Parameters + Indicators save | ✅ | `saveStatus` state: `null`/`saving`/`saved`/`error`; button disabled during save; `✓ Saved` / `✗ Error` badge auto-clears after 3s |
| U2 | Confirmation dialog before bot removal | ✅ | `window.confirm()` before `handleRemoveButtonClick` fires WS command |
| U3 | Fix table overflow (`overflow-x: auto`) | ✅ | Completed as part of W3 |
| U4 | Error state in `Bots.js` fetch | ✅ | `fetchError` state; catch block sets message; error banner rendered below loading indicator |
| U5 | Add try/catch to `getBotIds`, `getOrders`, `getTrades` | ✅ | `getBotIds` throws on error (caller handles); `getOrders`/`getTrades` return `null` on network failure |

---

## Sprint 1 — Testing Track

| # | Task | Status | Notes |
|---|---|---|---|
| T1 | Tests for `utils/api.js` | ✅ | 26 test cases across 9 describe blocks; covers success, HTTP error, network failure, fallback chain, auth header, POST body |
| T2 | Tests for `utils/helpers.js` | ✅ | 7 test cases; covers aggregation, null skipping, empty input |
| T3 | Tests for `useWebSocket.jsx` | ✅ | 11 test cases across 4 describe blocks; covers connect, wsOpen, wsError, memory leak regression (W1), backoff timing |
| T4 | Create `src/mocks/fixtures.js` | ✅ | `mockUser`, `mockBotIds`, `mockOrder`, `mockTrade`, `mockParameters`, `mockIndicators`, `mockResponse` helper |

---

## Month 2 — Architecture & Quality

| # | Task | Status | Notes |
|---|---|---|---|
| M1 | Extract shared `PrivateRoute` component | ✅ | `src/components/PrivateRoute/PrivateRoute.js` created; 4 inline definitions removed from `Crypto.js`, `Dex.js`, `Forex.js`, `Token.js`; 3 test cases added |
| M2 | Refactor `Parameters` + `Indicators` to functional + shared hook | ✅ | `useConfigCheckboxes` hook created (105 lines); both components refactored to functional (~74/76 lines each); 8 test cases added; no class components remain except `ErrorBoundary` |
| M3 | Split `Bots.js` into hook + sub-components | ✅ | `useBots.js` hook (126 lines); `BotControls.js` (59); `BotConsole.js` (25); `TradeHistoryTable.js` (69, reusable for orders+trades); `Bots.js` orchestrator (71); 5 tests added |
| M4 | Add `ErrorBoundary` around `<Crypto>` page | ✅ | `ErrorBoundary.js` class component with `getDerivedStateFromError`; fallback shows error message + "Try again" button; error detail shown in dev mode only; 4 test cases added |
| M5 | Code splitting with `React.lazy` + `Suspense` | ✅ | All 4 page routes lazy-loaded in `App.js`; `PageLoader` fallback component; `App.test.js` updated to use `waitFor` for async Suspense resolution |
| M6 | Cap log array at 500 entries | ✅ | `logs` state changed from unbounded string to array; capped at `MAX_LOG_LINES = 500` via `slice(-500)`; rendered with `logs.join("\\n")` |
| M7 | Replace sequential fetches with `Promise.all` | ✅ | `helpers.js` rewritten: `for await` loops replaced with `Promise.all` + `filter(Boolean).flat()`; 2 parallel-execution tests added |
| M8 | Memoize `AuthContext` value | ✅ | `handleLogin`, `handleLogout`, `handleLoginSuccess`, `handleLogoutSuccess` wrapped in `useCallback`; context value wrapped in `useMemo([user, handleLogin, handleLogout])`; `useEffect` deps array now correct |
| M9 | Tests for `Parameters` + `Indicators` | ⬜ | |
| M10 | Tests for `Bots.js` | ⬜ | |
| M11 | Tests for `Crypto.js` | ⬜ | |
| M12 | Install `jest-axe` + accessibility tests | ⬜ | |
| M13 | Add PropTypes to all components | ✅ | Added to `Bots`, `Parameters`, `Indicators`, `PrivateRoute`, `ErrorBoundary`; `prop-types` v15.8.1 added to `package.json` |
| M14 | Remove inline styles | ✅ | `NavBar.js`: 4× `style={{ textDecoration: "none" }}` → `.nav-link` CSS class; `Bots.js`: 2× opacity inline → `.btn-disabled` CSS class; `App.js`: `PageLoader` inline → `.page-loader` CSS class; zero inline styles remain in `src/` |
| M15 | Add ESLint `no-console` rule + enforce in CI | ✅ | Added `no-console: warn`, `no-unused-vars: warn`, `react/prop-types: warn` to `eslintConfig`; added `lint` script with `--max-warnings=0`; lint step added to `cloudbuild.yaml` before audit and tests |

---

## Month 3–6 — Long-term

| # | Task | Status | Notes |
|---|---|---|---|
| L1 | Structured JSON WebSocket protocol | ✅ | Backend: `send_logs()` wraps all messages in JSON; emits `bot_created`, `bot_removed`, `order_success`, `trade_success` events. Frontend: `parseMessage()` in `useBots.js` dispatches via `switch(msg.type)`; plain-text fallback for legacy compatibility |
| L2 | Data visualization with Recharts | ✅ | `recharts` v3.8.1 added; `ProfitChart` component: cumulative P&L area chart with custom tooltip, reference line at zero, gradient fill; shown above trade history table |
| L3 | Bot status indicator (running/stopped/error) | ✅ | `BotStatus` enum (idle/running/error) in `useBots`; badge shown next to Bots heading; green/blue/red CSS classes |
| L4 | Paper vs live trading mode toggle | ✅ | `isSimulating` state + `handleToggleSimulation` in `useBots`; toggle button in `Bots.js`; sends `set_simulation` WS command; backend wired |
| L5 | MSW integration tests | ✅ | `msw` v2.13.3 added; `src/mocks/handlers.js` covers all 9 sonarft endpoints; `src/mocks/server.js` for Jest; MSW lifecycle in `setupTests.js`; 8 integration tests in `src/integration/workflows.test.js` |
| L6 | TypeScript migration (start with `utils/`) | ✅ | `tsconfig.json` added; `@types/react`, `@types/react-dom`, `@types/node` added; `api.ts` with full type interfaces (`TradeRecord`, `ParametersConfig`, `IndicatorsConfig`); `helpers.ts` with typed filter predicate; incremental — JS files coexist |
| L7 | Vite migration from CRA | ✅ | `react-scripts` replaced with `vite` v8 + `@vitejs/plugin-react`; `vitest` replaces Jest; `vite.config.js` with `REACT_APP_` env prefix for CRA compat; root `index.html` created; `cloudbuild.yaml` test command updated |
| L8 | Performance monitoring (`reportWebVitals`) | ✅ | `src/utils/vitals.js` created; dev: logs to console; prod: `sendBeacon` to `REACT_APP_VITALS_URL` (no-op if unset); `index.js` wired; env examples updated |
| L9 | Idle session timeout | ✅ | `useIdleTimeout` hook (resets on mousemove/keydown/mousedown/touchstart/scroll); wired into `AuthProvider` with `!!user` guard; default 30 min via `REACT_APP_IDLE_TIMEOUT_MS`; 5 test cases |
| L10 | Tooltips on indicators/parameters | ✅ | `TOOLTIPS` maps added to both components; `title` attribute on every `<label>`; covers all 5 periods, 6 oscillators, 5 moving averages, 3 exchanges, 2 symbols |
