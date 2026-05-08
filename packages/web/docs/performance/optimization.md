# Performance Optimization & Bundle Size
**Prompt:** 08-WEB-PERF | **Package:** web | **Reviewed:** July 2025

---

## Executive Summary

sonarftweb's performance profile is strong for a trading dashboard SPA. The
vendor chunk splitting strategy is well-designed, the app code is tiny, and
the RAF log-batching pattern is the right solution for high-frequency WebSocket
updates. The one significant finding is the Recharts vendor chunk at 96.69 KB
gzip — above the 100 KB warning threshold and the largest single asset. This
is inherent to Recharts' bundle size and is acceptable given the chart is the
primary data visualization. The `logo192.png` at 869 KB uncompressed is the
largest asset and should be optimized. No memory leaks were identified. The
`useCallback`/`useMemo`/`React.memo` usage is well-calibrated — no over- or
under-memoization found.

---

## 1. Bundle Size Analysis

All figures from a production build (`npm run build`, Vite 8.0.8, July 2025).

### Chunk inventory

| Chunk | Raw size | Gzip size | Type |
|---|---|---|---|
| `vendor-recharts-*.js` | 330.24 KB | **96.69 KB** | Vendor — Recharts + victory-vendor |
| `vendor-react-*.js` | 161.64 KB | **53.15 KB** | Vendor — React 18 + React-DOM + React-Router |
| `Crypto-*.js` | 24.58 KB | **7.67 KB** | App — Crypto page + all components + hooks |
| `index-*.js` | 4.03 KB | **1.70 KB** | App — App shell, AuthProvider, NavBar, Footer |
| `AuthProvider-*.js` | 0.50 KB | **0.32 KB** | App — AuthProvider chunk |
| `rolldown-runtime-*.js` | 0.68 KB | **0.41 KB** | Runtime |
| `Crypto-*.css` | 10.42 KB | **2.28 KB** | CSS — all component styles |
| `index-*.css` | 4.20 KB | **1.50 KB** | CSS — global styles |
| `index.html` | 1.01 KB | **0.49 KB** | HTML shell |

**Total JS (gzip):** ~160 KB
**Total CSS (gzip):** ~3.78 KB
**Total transfer (gzip, excluding logo):** ~164 KB

### Key observations

**App code is tiny:** The entire application logic — all components, hooks,
utilities, and page code — compresses to under 10 KB gzip. This is excellent.
The `Crypto` chunk at 7.67 KB gzip contains `Bots`, `BotControls`, `BotConsole`,
`TradeHistoryTable`, `ProfitChart`, `Parameters`, `Indicators`,
`ConfigCheckboxPanel`, `useBots`, `useWebSocket`, `useConfigCheckboxes`,
`useIdleTimeout`, `api.ts`, `helpers.ts`, `constants.ts`, and all CSS.

**Recharts dominates:** At 96.69 KB gzip, Recharts is 60% of the total JS
transfer. This is the inherent cost of the library. The single `ProfitChart`
component uses `AreaChart`, `Area`, `XAxis`, `YAxis`, `CartesianGrid`,
`Tooltip`, `ReferenceLine`, and `ResponsiveContainer` — a significant portion
of Recharts' API surface.

**React vendor chunk:** 53.15 KB gzip for React 18 + React-DOM + React-Router.
This is the expected size for the React ecosystem.

**No `vendor-netlify` chunk:** The Netlify Identity widget is not in the
production bundle — it is not imported in the reviewed source. The
`manualChunks` config references it but it is not a dependency. This is
correct for the current dev-bypass auth implementation.

**Source maps:** `sourcemap: false` in `vite.config.js` — source maps are not
included in the production build. ✅

**Compression:** nginx `gzip on` with `gzip_comp_level 6` serves all JS/CSS
assets compressed. ✅

### Unoptimized asset

`logo192.png` at **869.86 KB** uncompressed is the largest asset by far. It
is referenced in `index.html` as an Apple touch icon (`<link rel="apple-touch-icon">`)
and in `manifest.json`. It is not rendered in the app UI (the navbar uses
`sonarftlogo.png` from `src/assets/img/`). A 192×192 PNG should be well under
50 KB — 869 KB suggests it is either a much larger image scaled down or
unoptimized.

---

## 2. Code Splitting Strategy

**Route-based splitting:** The `Crypto` page is lazy-loaded via `React.lazy`:

```typescript
// App.tsx
const Crypto = lazy(() => import("./pages/Crypto/Crypto"));
```

This means the `Crypto-*.js` chunk (7.67 KB gzip) is not loaded until the
user navigates to `/crypto`. Since `/crypto` is the only route and the app
redirects there immediately, this split provides minimal practical benefit
today — but it is the correct pattern for future route additions. ✅

**Vendor chunk splitting:** Three manual chunks defined in `vite.config.js`:

```javascript
manualChunks(id) {
    if (id.includes("netlify-identity-widget")) return "vendor-netlify";
    if (id.includes("recharts") || id.includes("victory-vendor")) return "vendor-recharts";
    if (id.includes("node_modules/react/") || id.includes("node_modules/react-dom/")
        || id.includes("node_modules/react-router")) return "vendor-react";
}
```

This is a well-designed splitting strategy:
- `vendor-react`: changes rarely → long cache TTL ✅
- `vendor-recharts`: changes rarely → long cache TTL ✅
- `Crypto-*.js`: app code changes frequently → short cache TTL ✅

When app code changes, only the `Crypto-*.js` chunk is invalidated. Users
who have visited before will serve React and Recharts from cache.

**nginx cache headers:**
```nginx
location ~* \.(js|css|png|jpg|ico|svg|woff2?)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```
Content-hashed filenames + 1-year immutable cache = optimal caching. ✅

**Component-level splitting:** Not used. All components are in the `Crypto`
chunk. Given the chunk is only 7.67 KB gzip, further splitting would add
HTTP request overhead without meaningful size benefit.

**`chunkSizeWarningLimit: 100`:** Set to 100 KB in `vite.config.js`. The
`vendor-recharts` chunk (96.69 KB) is just under this limit. The build
currently warns about chunks larger than 100 KB — the Recharts chunk is
flagged. This is expected and acceptable.

---

## 3. React Rendering Performance

### Memoization inventory and assessment

| Location | Technique | Deps | Justified? |
|---|---|---|---|
| `AuthProvider` | `useMemo` on context value | `[user, handleLogin, handleLogout]` | ✅ Prevents context consumers re-rendering on unrelated provider renders |
| `AuthProvider` | `useCallback` on `handleLogin` | `[]` | ✅ Stable reference for context value |
| `AuthProvider` | `useCallback` on `handleLogout` | `[]` | ✅ Stable reference for context value |
| `useBots` | `useCallback` on `handleCreate` | `[socket, wsOpen]` | ✅ Passed to `BotControls` (memo'd) |
| `useBots` | `useCallback` on `handleStop` | `[socket, selectedBotId]` | ✅ Passed to `BotControls` (memo'd) |
| `useBots` | `useCallback` on `handleRemove` | `[socket, selectedBotId]` | ✅ Passed to `BotControls` (memo'd) |
| `useBots` | `useCallback` on `handleToggleSimulation` | `[socket, selectedBotId]` | ✅ Passed to `Bots` handler |
| `Parameters` | `useCallback` on `handleCheckboxChange` | `[]` | ✅ Stable for checkbox renders |
| `Parameters` | `useCallback` on `handleStrategyChange` | `[]` | ✅ Stable for select render |
| `Parameters` | `useCallback` on `handleSave` | `[clientId, config, scheduleStatus]` | ✅ Prevents re-creation on every render |
| `Parameters` | `useCallback` on `scheduleStatus` | `[]` | ✅ Stable for `handleSave` dep |
| `Parameters` | `useMemo` on `exchangeEntries` | `[config.exchanges]` | ✅ Avoids `Object.entries` on every render |
| `Parameters` | `useMemo` on `symbolEntries` | `[config.symbols]` | ✅ Avoids `Object.entries` on every render |
| `useConfigCheckboxes` | `useCallback` on `handleCheckboxChange` | `[storageKey]` | ✅ Stable for checkbox renders |
| `useConfigCheckboxes` | `useCallback` on `handleSave` | `[clientId, config, updateFn]` | ✅ Prevents re-creation |
| `ConfigCheckboxPanel` | `useMemo` on `stateKeys` | `[sections]` | ✅ Prevents `useConfigCheckboxes` effect re-run |
| `ConfigCheckboxPanel` | `useCallback` on `renderCheckboxes` | `[config, handleCheckboxChange]` | ✅ Stable render function |
| `ProfitChart` | `useMemo` on `data` | `[trades]` | ✅ Avoids cumulative P&L recomputation |
| `BotControls` | `React.memo` | — | ✅ Pure display, stable props from `useCallback` |
| `BotConsole` | `React.memo` | — | ✅ Pure display, `logs` only changes on RAF flush |
| `TradeHistoryTable` | `React.memo` | — | ✅ Pure display, `rows` only changes on trade events |
| `ProfitChart` | `React.memo` | — | ✅ Pure display, `trades` only changes on trade events |

**Assessment:** Memoization is well-calibrated. No over-memoization (no
`useCallback` on trivial inline functions, no `useMemo` on primitive values).
No under-memoization (all callbacks passed to `React.memo` children are
stabilized). ✅

### Re-render frequency analysis

| Trigger | Components re-rendered | Frequency |
|---|---|---|
| RAF log flush | `Bots`, `BotConsole` | Up to 60/s during active trading |
| `order_success` / `trade_success` | `Bots`, `TradeHistoryTable`, `ProfitChart` | Per trade (seconds to minutes) |
| `bot_created` / `bot_removed` | `Bots`, `BotControls` | Rare |
| `fetchError` / `wsError` change | `Bots` | Rare |
| Config checkbox change | `Parameters` or `ConfigCheckboxPanel` | Per user interaction |
| Auth context change | `NavBar`, `Crypto` | Login/logout only |

**Hottest re-render path:** `Bots` re-renders up to 60 times/second during
log flushes. `BotControls`, `TradeHistoryTable`, and `ProfitChart` are
protected by `React.memo` and skip these re-renders. `BotConsole` re-renders
on every flush (its `logs` prop changes). This is the intended behavior —
the console must update to show new log lines.

**`Bots` re-render scope:** `Bots` re-renders on every log flush because
`logs` state lives in `useBots` alongside `botIds`, `orders`, etc. The modal
JSX (`showLiveConfirm`, `showRemoveConfirm`) is re-evaluated on every flush.
This is cheap (no DOM mutations when modal is closed) but represents wasted
work. Extracting log state into a dedicated `BotConsoleContainer` component
would isolate log re-renders to that subtree.

---

## 4. State Management Performance

**State tree structure:** Flat and minimal. No deeply nested state objects.
`useBots` has 9 `useState` calls + 1 `useReducer` — all at the same level.
No normalization needed at this data volume.

**Context performance:** `AuthContext` value is memoized with `useMemo`.
Context consumers (`NavBar`, `Crypto`) only re-render when `user` changes
(login/logout). During normal operation (user logged in, no auth changes),
zero context-driven re-renders occur. ✅

**Update batching:** React 18 automatic batching applies — multiple `setState`
calls within the same event handler or async callback are batched into a single
re-render. The `bot_created` handler calls `setSelectedBotId`, `setBotIds`,
and `dispatch` — these are batched. ✅

**Selector memoization:** No Redux/Recoil selectors needed. Derived values
(`botState`, `botStatus`) are computed inline from `machine.lifecycle` — cheap
string comparisons, no memoization needed.

**`botIdsRef` pattern:** The ref keeps a stable reference to `botIds` for use
in the `onmessage` closure without triggering re-renders on update. This is
the correct pattern for values needed in event handlers that should not cause
re-renders. ✅

---

## 5. Network Performance

### Requests on page load (cold start)

```
1. GET /ws/ticket          (POST, ~50 bytes request, ~100 bytes response)
2. GET /bots?client_id=    (~200 bytes response)
3. GET /parameters?client_id=  (~500 bytes response)
4. GET /indicators?client_id=  (~800 bytes response)
5. WS CONNECT /ws/{clientId}?ticket=...
```

Requests 1–4 fire in parallel (two independent `useEffect` chains). The WS
connection (5) waits for the ticket response (1). This is a two-level waterfall:
ticket → WS connect. The ticket fetch adds ~1 RTT to WS connection time.

If bots exist on load, two additional parallel requests fire:
```
6. GET /bots/{id}/orders?client_id=   (per bot)
7. GET /bots/{id}/trades?client_id=   (per bot)
```

**Total cold-start requests:** 5–7 (depending on existing bots).

**Parallel execution:** Requests 3 and 4 (parameters + indicators) fire
concurrently. Requests 6 and 7 (orders + trades) use `Promise.all`. ✅

**Payload sizes:** All config and history responses are JSON. The API applies
`GZipMiddleware` with `minimum_size=1000` — responses under 1 KB are not
compressed. Config responses (~500–800 bytes) may fall below the threshold.
History responses with 100 records will be well above 1 KB and will be
compressed.

**Caching:** The API sets `Cache-Control: no-store` on all responses. No
HTTP caching. The frontend's `localStorage` config cache provides a client-
side equivalent for config data.

**Request frequency during operation:**
- Log messages: 0 REST requests (WebSocket only)
- `order_success` / `trade_success`: 2 REST requests per event (orders + trades)
- `bot_created`: 1 REST request (bot IDs)

At high trading frequency, `order_success` events could trigger many REST
requests. The API's 60/min read rate limit provides a natural cap.

---

## 6. Image & Asset Optimization

### Asset inventory

| Asset | Size | Used in | Issue |
|---|---|---|---|
| `logo192.png` | **869.86 KB** | `index.html` (apple-touch-icon), `manifest.json` | ⚠️ Severely oversized for a 192×192 icon |
| `logo512.png` | Not measured | `manifest.json` | Likely also oversized |
| `sonarftlogo.png` | Not measured | `NavBar` | Unknown size |
| `favicon.ico` | 0.22 KB | `index.html` | ✅ Appropriately small |

**`logo192.png` at 869 KB** is the most significant performance issue in the
asset layer. A 192×192 PNG should be 10–50 KB. At 869 KB it is likely a
high-resolution source image that was not resized before being placed in
`public/`. This adds ~870 KB to the initial page load for iOS users who
trigger the apple-touch-icon fetch.

**Image formats:** PNG used throughout. WebP would reduce sizes by ~30%.
For the logo assets, SVG would be ideal (vector, infinitely scalable, tiny
file size).

**Lazy loading:** Not applicable — the only in-page image is the navbar logo
(`sonarftlogo.png`), which is above the fold and should load eagerly. ✅

**Responsive images:** Not implemented. Single `<img src={logo}>` in `NavBar`
with no `srcset`. For the 32×32 navbar logo this is fine.

**nginx static asset caching:**
```nginx
location ~* \.(js|css|png|jpg|ico|svg|woff2?)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```
All static assets are cached for 1 year with `immutable`. After the first
load, logo assets are served from browser cache. ✅

---

## 7. CSS Performance

### CSS size

| File | Raw | Gzip |
|---|---|---|
| `Crypto-*.css` (all component styles) | 10.42 KB | 2.28 KB |
| `index-*.css` (global styles) | 4.20 KB | 1.50 KB |
| **Total** | **14.62 KB** | **3.78 KB** |

CSS is negligible in the overall transfer budget. ✅

**CSS-in-JS overhead:** None — plain CSS files, zero runtime cost. ✅

**Unused CSS:** Some unused rules exist:
- `App.css`: `.App-logo`, `.App-header`, `.App-link`, `App-logo-spin` keyframe
  — legacy CRA styles not referenced by any component
- `index.css`: `body` font-family stack is overridden by `styles.css` — the
  `index.css` body rule is redundant
- `styles.css`: `.card` utility class defined but not used by any component

These are minor — the total unused CSS is under 1 KB.

**Critical CSS:** Not extracted. The entire CSS bundle loads as a single
stylesheet. Given the total CSS is only 3.78 KB gzip, inline critical CSS
would add complexity without meaningful benefit.

**Animations:** CSS `transition` properties use `background 0.2s` and
`border-color 0.15s` — these animate `background-color` and `border-color`,
which trigger paint but not layout. Not GPU-accelerated (no `transform` or
`opacity`). For button hover effects this is acceptable — the transitions are
short and infrequent. ✅

**`:has()` selector:** Used in `parameters.css` and `indicators.css` for
checked checkbox styling. Modern CSS, no performance concern. ✅

**CSS duplication:** ~60 lines duplicated between `parameters.css` and
`indicators.css` (`.checkbox-group`, `.save-row`, `.save-status`). No
performance impact — the duplication is in the source, not the output (both
files are bundled into `Crypto-*.css`).

---

## 8. JavaScript Execution

**Parsing budget:** Total JS is ~160 KB gzip (~500 KB uncompressed). On a
mid-range mobile device (4× CPU throttle), parsing ~500 KB of JS takes
approximately 200–400ms. This is within acceptable bounds for a trading
dashboard (not a consumer app requiring sub-100ms TTI).

**Main thread blocking:** No long synchronous tasks identified in the source:
- `botMachineReducer`: pure function, O(1)
- `parseMessage`: JSON.parse + string check, O(n) on message length
- `getLogClass`: three regex tests, O(1)
- `formatDate` / `formatCurrency`: `Intl` API calls, O(1)
- `ProfitChart` data computation: O(n) on trades array, memoized

The most expensive synchronous operation is the `useMemo` in `ProfitChart`
computing cumulative P&L — O(n) on the trades array. With 100 trades this
is negligible.

**RAF loop:** The log flush RAF loop runs continuously while `useBots` is
mounted. Each frame: check `logBufferRef.current.length`, conditionally call
`setLogs`. When no logs are buffered, the frame callback is a near-zero-cost
no-op. ✅

**`localStorage` writes:** Synchronous `localStorage.setItem` on every
checkbox change. For config objects of ~500 bytes, this is fast (< 1ms) but
blocks the main thread. At human interaction speed (one checkbox click at a
time) this is imperceptible.

---

## 9. Web Vitals

Web Vitals cannot be measured without a running browser session. The following
is an assessment based on the build output and code analysis.

**LCP (Largest Contentful Paint):**
The largest above-the-fold element is likely the navbar logo (`sonarftlogo.png`)
or the first rendered panel heading. The `Crypto` page is lazy-loaded but the
chunk is only 7.67 KB — the dynamic import resolves in < 50ms on a fast
connection. Estimated LCP: **< 2s** on desktop broadband. The `logo192.png`
at 869 KB could delay LCP on mobile if it is the LCP element (unlikely — it
is an apple-touch-icon, not rendered in the page).

**FID / INP (Interaction to Next Paint):**
All event handlers are lightweight (dispatch, setState, socket.send). No
synchronous blocking on user interaction. Estimated INP: **< 50ms**. ✅

**CLS (Cumulative Layout Shift):**
No dynamic content insertion above existing content. The log console has a
fixed height (220px). History tables grow downward. The P&L chart has a fixed
height (220px). Estimated CLS: **< 0.1** (Good). ✅

**FCP (First Contentful Paint):**
The HTML shell is 0.49 KB gzip. The `index-*.css` (1.50 KB) and `index-*.js`
(1.70 KB) are tiny — the app shell renders almost immediately. Estimated FCP:
**< 1s** on desktop broadband. ✅

**TTI (Time to Interactive):**
The main JS chunks total ~160 KB gzip. After parsing and executing React +
the app shell, the app is interactive. The `Crypto` chunk loads lazily but
resolves quickly. Estimated TTI: **1.5–3s** on desktop broadband,
**3–5s** on 4G mobile (accounting for Recharts parse time).

**TTFB:** Depends on server deployment. Not assessable from source alone.

**Web Vitals reporting:** `vitals.ts` is implemented and ready to report to
`VITE_VITALS_URL`. In production, `VITE_VITALS_URL` is not set in
`.env.production` — no vitals are reported by default. Setting this up would
provide real-user performance data.

---

## 10. Real-time Update Performance

**Message handling latency:** Each WebSocket message is processed in the
`onmessage` handler synchronously. For `log` events: push to `logBufferRef`
(array push, O(1)). For lifecycle events: async REST fetch triggered. The
handler itself is near-zero-cost for log messages.

**Re-render frequency from WebSocket:**
- Log messages: batched by RAF → max 60 re-renders/second of `Bots` +
  `BotConsole`
- Trade events: 1 re-render per event (seconds to minutes apart)
- Lifecycle events: 1–2 re-renders per event (rare)

**Memory growth:**
- `logs` array: capped at `MAX_LOG_LINES = 500`. Each log line is a string
  (~50–200 bytes). Maximum memory for logs: ~100 KB. ✅
- `orders` / `trades` arrays: replaced on each event (no accumulation).
  Bounded by API `limit=100`. ✅
- `logBufferRef`: drained on every RAF frame. No accumulation between frames
  under normal conditions. ✅
- WebSocket: one socket object per session. No accumulation. ✅

**Memory leak risk assessment:**
- RAF loop: cancelled on unmount via `cancelAnimationFrame`. ✅
- WebSocket: closed on unmount via `socketRef.current.close()`. ✅
- `onmessage` handler: replaced on each `wsOpen` change, not accumulated. ✅
- `setTimeout` for save feedback: not cancelled on unmount in `Parameters`
  and `useConfigCheckboxes` — minor leak (callback calls `setSaveStatus(null)`
  on unmounted component, silently ignored by React 18). ⚠️

**Disconnection impact:** On disconnect, `wsOpen` becomes `false`. The RAF
loop continues running (it is independent of WebSocket state). Log buffer
stops receiving new messages. No performance impact from disconnection. ✅

---

## 11. Browser DevTools Profiling

No profiling data is available from the source review. The following
observations are based on code analysis:

**Expected rendering profile:**
- During active trading: `Bots` + `BotConsole` re-render at ~60fps (RAF flush)
- During idle: zero re-renders (no state changes)
- On trade event: 1 re-render cycle for `Bots` + `TradeHistoryTable` + `ProfitChart`

**Expected JavaScript profile:**
- Hottest function: `setLogs` state updater (called up to 60/s)
- Second hottest: `logBufferRef.current.splice(0)` (array splice, O(n) on buffer size)
- All other functions: called at human interaction speed

**Memory profile:** Expected to be stable. No unbounded growth identified.
The `logs` cap at 500 lines and the full-replacement strategy for `orders`/
`trades` prevent accumulation.

**Recommended profiling steps:**
1. Open React DevTools Profiler during active bot trading
2. Record 5 seconds of log streaming
3. Verify `BotControls`, `TradeHistoryTable`, `ProfitChart` show 0 renders
   during log flush (confirming `React.memo` effectiveness)
4. Check `Bots` render duration — should be < 2ms per frame

---

## 12. Third-party Scripts

**None loaded at runtime.** All dependencies are bundled at build time. No
CDN scripts, no analytics tags, no tracking pixels, no ad networks. ✅

The CSP `script-src 'self'` blocks any injected external scripts. ✅

**Web Vitals reporting** (`vitals.ts`) uses `navigator.sendBeacon` or `fetch`
to POST metrics to `VITE_VITALS_URL` — this is a first-party endpoint, not
a third-party service. No performance impact unless `VITE_VITALS_URL` is set
to a slow endpoint.

---

## 13. Mobile Performance

**Bundle transfer on 4G (~10 Mbps):**
- Total JS: ~160 KB gzip → ~130ms transfer
- Total CSS: ~3.78 KB gzip → ~3ms transfer
- `logo192.png`: 869 KB → ~700ms transfer (if fetched)

The logo PNG is the dominant mobile load concern. On a 4G connection it adds
~700ms to the load. Since it is an apple-touch-icon (not rendered in the page),
it is only fetched when a user adds the app to their home screen — not on
every page load.

**CPU on mobile:** Recharts SVG rendering is the most CPU-intensive operation.
With 100 data points, the initial chart render takes ~50–100ms on a mid-range
device. Subsequent renders (on `trade_success`) are incremental.

**RAF loop on mobile:** `requestAnimationFrame` on mobile runs at the device's
refresh rate (typically 60fps, sometimes 120fps on newer devices). The loop
is lightweight when the buffer is empty. Battery impact is minimal — the RAF
callback does near-zero work when no logs are buffered.

**Touch targets:** All buttons have adequate padding for touch. The bot
selector is a native `<select>` — touch-friendly. ✅

---

## 14. Performance Monitoring

**Web Vitals:** `vitals.ts` is implemented and ready. Not active in production
(no `VITE_VITALS_URL` set). Enabling this would provide real-user LCP, FID,
CLS, FCP, and TTFB data.

**Error tracking:** No Sentry or equivalent. Errors surface to the user via
alert banners but are not reported to an external service.

**Server-side metrics:** The API writes structured JSON metrics to
`logs/sonarft_metrics.jsonl` via a dedicated rotating file handler. This
covers server-side performance but not client-side.

**Benchmarks:** No established performance budgets beyond the Vite
`chunkSizeWarningLimit: 100` (KB). No Lighthouse CI or performance regression
testing in the CI pipeline.

**Alerts:** No performance regression alerts configured.

---

## 15. Performance Issues Summary

| Issue | Category | Severity | Impact | Fix Difficulty |
|---|---|---|---|---|
| `logo192.png` at 869 KB | Asset | High | +700ms on 4G for home-screen users; wasted bandwidth | Easy — resize to 192×192 and re-export; target < 20 KB |
| Recharts chunk at 96.69 KB gzip | Bundle | Medium | Largest single JS asset; 60% of total JS transfer | Hard — inherent to Recharts; consider lighter alternative (uPlot, Chart.js) only if bundle size becomes a constraint |
| `Bots` re-renders at 60fps during log flush | Rendering | Medium | Modal JSX re-evaluated 60×/s; wasted work when modals are closed | Medium — extract log state into `BotConsoleContainer` to isolate re-renders |
| No request timeout on `fetch` calls | Network | Medium | Hung server holds connections indefinitely; "Saving..." shown forever | Easy — add `AbortController` with 15s timeout to all `fetch` calls in `api.ts` |
| History re-fetch not debounced | Network | Low | Rapid `order_success` events trigger concurrent REST calls | Easy — debounce history re-fetch trigger by 200ms |
| `logo512.png` likely oversized | Asset | Low | Similar to `logo192.png` — manifest icon | Easy — resize and re-export |
| `saveTimer` not cleared on unmount | Memory | Low | Minor: `setTimeout` callback fires on unmounted component (React 18 silently ignores) | Easy — add `useEffect` cleanup in `Parameters` and `useConfigCheckboxes` |
| Unused CSS rules in `App.css` / `index.css` | CSS | Low | ~1 KB of unused CSS in bundle | Easy — remove legacy CRA styles from `App.css`; remove redundant `body` rule from `index.css` |
| No Web Vitals reporting in production | Monitoring | Low | No real-user performance data | Easy — set `VITE_VITALS_URL` in `.env.production` |
| No Lighthouse CI in pipeline | Monitoring | Low | Performance regressions not caught automatically | Medium — add `lhci autorun` step to GitHub Actions workflow |
| `logo192.png` not WebP | Asset | Info | PNG ~30% larger than WebP equivalent | Easy — convert to WebP; keep PNG as fallback |
| `sonarftlogo.png` size unknown | Asset | Info | Navbar logo size not measured | Easy — verify size; convert to SVG if possible |
| No `srcset` on navbar logo | Asset | Info | Single resolution served to all devices | Low priority — logo is 32×32 display size |
