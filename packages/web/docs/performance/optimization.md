# sonarftweb — Performance Optimization & Bundle Size

**Prompt:** 08-performance-optimization  
**Category:** Performance  
**Date:** July 2025  
**Depends on:** [docs/components/design-patterns.md](../components/design-patterns.md), [docs/state-management/data-flow.md](../state-management/data-flow.md)

---

## Executive Summary

sonarftweb's performance profile is acceptable for a low-traffic internal tool but has several structural issues that will degrade under real usage. The most impactful problems are: zero code splitting (the entire app loads as a single bundle), no memoization of any kind (`React.memo`, `useMemo`, `useCallback` are absent throughout), an unbounded log string that grows indefinitely causing increasingly expensive re-renders on every WebSocket message, two CoinGecko components making identical duplicate API calls, and 38 `console.log` statements left in production code. The app is small enough (~1800 lines of source JS) that these issues are not yet critical, but the WebSocket log growth and lack of code splitting will become noticeable as usage scales.

---

## 1. Bundle Size Analysis

`node_modules` is not installed in this environment so a live build could not be run. The following estimates are based on known gzipped sizes for the installed package versions.

### Runtime Dependencies (shipped to browser)

| Package | Version | Est. Gzipped | Est. Uncompressed | Used For |
|---|---|---|---|---|
| `react` | 18.2.0 | ~2.5 KB | ~7 KB | Core framework |
| `react-dom` | 18.2.0 | ~42 KB | ~130 KB | DOM rendering |
| `react-router-dom` | 6.15.0 | ~13 KB | ~40 KB | Routing |
| `axios` | 1.4.0 | ~14 KB | ~45 KB | CoinGecko calls only |
| `socket.io-client` | 4.7.1 | ~14 KB | ~45 KB | ⚠️ Not used in active code |
| `netlify-identity-widget` | 1.9.2 | ~50 KB | ~180 KB | Auth (also loaded via CDN) |
| `uuid` | 9.0.0 | ~1 KB | ~3 KB | Config.js (orphaned) |
| `web-vitals` | 2.1.4 | ~2 KB | ~6 KB | reportWebVitals (unused) |
| **App source** | — | ~5 KB | ~18 KB | All application code |
| **CSS** | — | ~3 KB | ~15 KB | All stylesheets |
| **Estimated total** | — | **~147 KB** | **~489 KB** | — |

### Key Observations

**`socket.io-client` (~14 KB gzipped) is installed but never used.** The app uses the native `WebSocket` API directly. `socket.io-client` is a dead dependency adding ~14 KB to the bundle.

**`netlify-identity-widget` is loaded twice.** It is both in `package.json` (bundled) and loaded via CDN script in `public/index.html`. This means the widget code is downloaded twice — once as part of the bundle and once as an external script. One of these should be removed.

**`uuid` is only used in `Config.js`** which is an orphaned component not reachable from any route. It adds ~1 KB for zero benefit.

**`axios` is used only for CoinGecko GET requests.** The native `fetch` API handles all sonarft communication. `axios` (~14 KB gzipped) could be replaced with `fetch` to eliminate the dependency entirely.

**`web-vitals` is installed but `reportWebVitals()` is called with no callback** in `index.js`:
```js
reportWebVitals(); // no argument — metrics are collected but never reported anywhere
```
This adds ~2 KB for zero benefit unless a reporting endpoint is configured.

---

## 2. Code Splitting Strategy

**No code splitting exists.** The entire application — all routes, all components, all dependencies — is bundled into a single JavaScript file.

```js
// App.js — all imports are static, nothing is lazy-loaded
import Home from "./pages/Home/Home";
import Crypto from "./pages/Crypto/Crypto";
import CryptoChatGPT from "./pages/CryptoChatGPT/CryptoChatGPT";
import Doggy from "./pages/Doggy/Doggy";
```

A user visiting only the Home page (`/`) downloads the full bundle including `Bots.js`, `Parameters.js`, `Indicators.js`, the WebSocket hook, and all trading logic — none of which is needed until the user navigates to `/crypto`.

### Recommended Route-Based Splitting

```js
import { lazy, Suspense } from 'react';

const Home = lazy(() => import('./pages/Home/Home'));
const Crypto = lazy(() => import('./pages/Crypto/Crypto'));
const CryptoChatGPT = lazy(() => import('./pages/CryptoChatGPT/CryptoChatGPT'));
const Doggy = lazy(() => import('./pages/Doggy/Doggy'));

// In router:
<Suspense fallback={<div>Loading...</div>}>
    <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/crypto" element={<Crypto />} />
        ...
    </Routes>
</Suspense>
```

This would split the `netlify-identity-widget` and trading components into a separate chunk loaded only when `/crypto` is visited, reducing the initial bundle by an estimated ~60–70 KB gzipped.

---

## 3. React Rendering Performance

### Memoization — Completely Absent

```
React.memo    — 0 usages
useMemo       — 0 usages
useCallback   — 0 usages
```

No component or value is memoized anywhere in the codebase. For the current app size this is not a critical problem, but specific patterns cause unnecessary re-renders:

### AuthContext Re-render Cascade

```js
// AuthProvider.js — context value recreated on every render
return (
    <AuthContext.Provider value={{ user, handleLogin, handleLogout }}>
```

`handleLogin` and `handleLogout` are plain functions defined in the component body — they are recreated on every `AuthProvider` render. The context value object `{ user, handleLogin, handleLogout }` is also a new object reference on every render. This causes every context consumer (`NavBar`, `Crypto`, `Dex`, `Forex`, `Token`) to re-render whenever `AuthProvider` re-renders, even if `user` hasn't changed.

**Fix:**
```js
const handleLogin = useCallback(() => netlifyIdentity.open(), []);
const handleLogout = useCallback(() => netlifyIdentity.logout(), []);
const value = useMemo(() => ({ user, handleLogin, handleLogout }), [user, handleLogin, handleLogout]);
return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
```

### Bots.js — Re-render on Every WebSocket Message

Every inbound WebSocket message triggers:
```js
setLogs((logs) => logs + "\n" + event.data);
```

This causes `Bots.js` to re-render, which re-renders the entire `<pre>` element with the full (and growing) log string, plus both history tables. As the log grows, each re-render becomes more expensive because React must diff an increasingly large string.

The `consoleEndRef.scrollIntoView()` in the logs `useEffect` also fires on every message, triggering a layout recalculation.

### onmessage Re-registration

```js
useEffect(() => {
    if (wsOpen) {
        socket.onmessage = async (event) => { ... };
    }
}, [clientId, wsOpen, socket, botIds, selectedBotId]);
```

This effect re-runs whenever `botIds` or `selectedBotId` changes, re-assigning `socket.onmessage`. During bot creation, `botIds` changes → effect re-runs → brief window where `onmessage` is unset → any messages arriving during re-registration are missed.

### Class Components Cannot Use Hooks

`Parameters.js` and `Indicators.js` are class components. They cannot use `React.memo`, `useMemo`, or `useCallback`. Every parent re-render causes them to re-render with no optimization possible without refactoring to functional components.

---

## 4. State Management Performance

### Context Re-renders

Only `AuthContext` is active. Its re-render impact is low — `user` state only changes on login/logout, which is infrequent. The main issue is the unmemoized context value described in §3.

### Log String Growth — Memory and Render Cost

```js
const [logs, setLogs] = useState("");
// Every message: logs = logs + "\n" + event.data
```

For a bot running at 1 message/second:

| Runtime | Log size | Re-render cost |
|---|---|---|
| 1 minute | ~6 KB | Negligible |
| 1 hour | ~360 KB | Noticeable |
| 8 hours | ~2.9 MB | Significant |
| 24 hours | ~8.6 MB | Severe |

React must hold the full string in memory and diff it on every update. The `<pre>` DOM node grows proportionally. There is no garbage collection of old log entries.

### Sequential vs Parallel Fetches

```js
// helpers.js — sequential (O(n) requests)
for (const id of botIds) {
    const orderData = await getOrders(id);  // waits for each
    if (orderData) allOrders.push(...orderData);
}
```

With N bots, one `"Order: Success"` event triggers N sequential HTTP requests. Each request must complete before the next starts. With 5 bots and 200ms average response time, the table update takes ~1 second after the WebSocket notification.

**Fix — parallel:**
```js
const results = await Promise.all(botIds.map(id => getOrders(id)));
return results.filter(Boolean).flat();
```

---

## 5. Network Performance

### API Calls on Page Load (Crypto page)

| Call | Endpoint | Parallel? |
|---|---|---|
| 1 | `GET /botids/{clientId}` | — |
| 2 | `GET /bot/get_parameters/{clientId}` | No — sequential in componentDidMount |
| 3 | `GET /bot/get_indicators/{clientId}` | No — sequential in componentDidMount |

`Parameters` and `Indicators` each make their own fetch in `componentDidMount`. These are independent and could be parallel, but since they are in separate class components they fire independently — effectively parallel by accident. However, if they were in the same component they would need explicit `Promise.all`.

### CoinGecko — Duplicate Requests

`CryptoTicker.js` and `CChatGPT.js` both call CoinGecko independently:

```js
// CryptoTicker.js — fetches top 20 coins every 3 minutes
// CChatGPT.js — fetches top 1 coin every 3 minutes
```

Both components are mounted simultaneously when the user is on `/cryptochatgpt`. They make separate HTTP requests to the same CoinGecko endpoint with no shared cache. If both are mounted on the same page, CoinGecko is called twice per poll cycle.

### No HTTP Caching

All `fetch` calls use default browser cache behavior (no explicit `Cache-Control` headers set). The sonarft backend would need to set appropriate cache headers for GET endpoints like `/default_parameters` and `/default_indicators` which rarely change.

### No Request Cancellation

No `AbortController` is used anywhere. If a component unmounts while a fetch is in flight (e.g., user navigates away from `/crypto` during the initial load), the response still arrives and attempts to call `setState` on the unmounted component. React 18 suppresses the warning but the network request completes unnecessarily.

---

## 6. Image & Asset Optimization

| Asset | Format | Size | Optimization |
|---|---|---|---|
| `sonarftlogo.png` (src/assets) | PNG | Unknown | No WebP alternative |
| `sonarft_bg.jpg` (src/assets) | JPG | Unknown | Not used in any component |
| `sonarftlogo.png` (public/) | PNG | Unknown | Duplicate of src/assets version |
| `logo192.png`, `logo512.png` | PNG | Standard CRA sizes | PWA icons — fine |
| `favicon.ico` | ICO | Standard | Fine |

`sonarft_bg.jpg` is in `src/assets/img/` but is not imported by any component — dead asset.

The logo is duplicated: once in `src/assets/img/sonarftlogo.png` (imported by NavBar) and once in `public/sonarftlogo.png`. Only the `src/assets` version is used in code.

No lazy loading (`loading="lazy"`) is applied to images. The logo in the NavBar is always visible above the fold, so lazy loading is not needed there, but any future below-fold images should use it.

---

## 7. CSS Performance

### Total CSS: ~1,480 lines across 15+ files

CRA concatenates and minifies all CSS into a single bundle at build time. The total uncompressed CSS is approximately 15 KB, which gzips to ~3 KB — negligible.

### CSS Animation Performance

```css
/* cryptoticker.css */
@keyframes scrolling {
    0%  { transform: translateX(100%); }
    100% { transform: translateX(-100%); }
}
.crypto-banner .inner {
    animation: scrolling 270s linear infinite;
}
```

`transform: translateX()` is GPU-accelerated — this animation is correctly implemented for performance. ✓

### Unused CSS

Several CSS files contain styles for components that are orphaned or unused:
- `building.css` — used only by placeholder pages
- `cryptochatgpt.css`, `doggy.css` — minimal pages
- `addvalidators.css`, `addindicators.css` — Config sub-components not reachable from routing

The `.outer-container` class is defined identically in both `welcome.css` and `building.css` — pure duplication.

### Global `font-size: small` Override

```css
/* styles.css */
* { font-size: small; }
```

Applying `font-size` to the `*` selector overrides every element including headings, buttons, and inputs. This forces the browser to recalculate font sizes for every element on every render. Using `html { font-size: 16px }` and `rem`-based sizing is both more performant and more maintainable.

---

## 8. JavaScript Execution

### 38 console.log Statements in Production

```
src/utils/api.js          — 13 console.log calls
src/hooks/useWebSocket.jsx — 7 console.log calls
src/components/Parameters  — 5 console.log calls
src/components/Indicators  — 5 console.log calls
src/hooks/WebSocketContext — 2 console.log calls
... (others)
```

`console.log` calls in production code have a measurable performance cost — each call serializes its arguments and writes to the DevTools buffer. With 7 WebSocket state logs firing on every connection event and 13 API logs firing on every request, this adds up during active trading sessions.

CRA's production build does **not** strip `console.log` by default. These statements ship to production as-is.

**Fix — add to `package.json` build script or use a custom babel plugin:**
```json
"build": "GENERATE_SOURCEMAP=false react-scripts build"
```
Or use `babel-plugin-transform-remove-console` to strip all console calls in production builds.

### Long Tasks Risk

The `onmessage` handler in `Bots.js` is `async` and performs multiple state updates plus conditional REST fetches synchronously on the main thread:

```js
socket.onmessage = async (event) => {
    setLogs(logs => logs + "\n" + event.data);          // state update
    if (event.data.includes(BOT_CREATED_MESSAGE)) {
        const ids = await getBotIds(clientId);           // network request
        setSelectedBotId(ids[ids.length - 1]);           // state update
        setBotIds(ids);                                  // state update
        socket.send(JSON.stringify({ ... }));            // WS send
    }
    if (event.data.includes(ORDER_SUCCESS)) {
        const allOrders = await fetchAllOrders(botIds);  // N network requests
        setOrders(allOrders);                            // state update
    }
    // ...
};
```

During high-frequency message bursts, multiple async handlers run concurrently, each triggering state updates and re-renders. React 18's automatic batching helps here, but the sequential REST fetches in `fetchAllOrders` still block the handler.

---

## 9. Web Vitals

`reportWebVitals` is called in `index.js` with no callback — metrics are measured but never reported. The infrastructure exists but is unused.

### Estimated Web Vitals (no live measurement available)

| Metric | Estimate | Notes |
|---|---|---|
| FCP (First Contentful Paint) | ~0.8–1.2s | Small bundle, static HTML shell |
| LCP (Largest Contentful Paint) | ~1.0–1.5s | Logo image or hero text |
| CLS (Cumulative Layout Shift) | Low | No dynamic content above fold on load |
| FID / INP | Low | Minimal JS on initial load |
| TTI (Time to Interactive) | ~1.5–2.5s | Depends on bundle parse time |

The main LCP risk is the `netlify-identity-widget` CDN script in `<head>` — it is render-blocking if the CDN is slow.

### reportWebVitals Fix

```js
// index.js — current (metrics collected, never reported)
reportWebVitals();

// Fix — log to console in development, send to analytics in production
reportWebVitals(process.env.NODE_ENV === 'development' ? console.log : sendToAnalytics);
```

---

## 10. Real-time Update Performance

### Message Processing Cost Per Message

Each WebSocket message triggers:
1. `setLogs` state update → React schedules re-render
2. String concatenation: `logs + "\n" + event.data` — O(n) where n = log length
3. Re-render of `Bots.js` — diffs full component tree including two tables
4. `consoleEndRef.scrollIntoView()` — layout recalculation

At 1 msg/sec with a 1-hour session (3,600 messages, ~360 KB log string), each re-render processes a 360 KB string. At 5 msg/sec (active trading), this becomes 1.8 MB after 1 hour.

### Memory Growth Profile

| Component | Memory Growth | Bounded? |
|---|---|---|
| `logs` string | Linear with messages | No — unbounded |
| `orders` array | Grows with trades | No — full history loaded each time |
| `trades` array | Grows with trades | No — full history loaded each time |
| WebSocket socket object | Constant | Yes ✓ |
| CryptoTicker data | Constant (20 items) | Yes ✓ |

### Debouncing WebSocket-Triggered Fetches

Multiple rapid `"Order: Success"` messages trigger multiple concurrent `fetchAllOrders` calls. A simple debounce prevents redundant fetches:

```js
const debouncedRefreshOrders = useCallback(
    debounce(async () => {
        const allOrders = await fetchAllOrders(botIds);
        setOrders(allOrders);
    }, 500),
    [botIds]
);
```

---

## 11. Third-party Scripts

| Script | Load Method | Async? | Performance Impact |
|---|---|---|---|
| `netlify-identity-widget.js` (CDN) | `<script>` in `<head>` | No | Render-blocking — delays FCP |
| `netlify-identity-widget` (npm bundle) | Bundled | N/A | Adds ~50 KB to bundle |

The CDN script in `public/index.html` is synchronous and in `<head>`, making it render-blocking. It should be either:
1. Moved to end of `<body>` with `defer` attribute, or
2. Removed entirely (use only the npm package)

```html
<!-- Fix option 1 — defer the CDN script -->
<script defer src="https://identity.netlify.com/v1/netlify-identity-widget.js"></script>

<!-- Fix option 2 — remove CDN script, use npm package only (already in package.json) -->
```

---

## 12. Mobile Performance

The app has no service worker, no offline support, and no PWA caching strategy despite having `manifest.json` and PWA icons. The CRA default service worker is not registered.

On mobile networks (4G ~20 Mbps), the estimated ~147 KB gzipped bundle loads in ~60ms — acceptable. The main mobile performance concern is the 13-column trading tables causing horizontal overflow and the fixed-height log console consuming a large portion of the viewport.

The CryptoTicker CSS animation (`transform: translateX`) is GPU-accelerated and performs well on mobile. ✓

---

## 13. Performance Monitoring

`reportWebVitals` is installed but not configured. No error tracking (Sentry, etc.), no RUM (Real User Monitoring), no performance budgets, and no CI performance regression checks exist.

---

## 14. Performance Issues Summary

| # | Issue | Category | Severity | Impact | Fix Difficulty |
|---|---|---|---|---|---|
| 1 | No code splitting — single bundle | Bundle | High | All users download full app on first visit | Low — add `React.lazy` to routes |
| 2 | `socket.io-client` unused (~14 KB) | Bundle | High | Dead weight in bundle | Low — remove from `package.json` |
| 3 | `netlify-identity-widget` loaded twice | Bundle | High | ~50 KB downloaded twice | Low — remove CDN script from `index.html` |
| 4 | Log string grows unbounded | Memory/Render | High | Increasing re-render cost over time | Low — cap with array slice |
| 5 | No memoization anywhere | Rendering | Medium | Unnecessary re-renders on context changes | Medium — add `useCallback`/`useMemo` to AuthProvider |
| 6 | Sequential order/trade fetches | Network | Medium | O(n) requests per WS event | Low — replace with `Promise.all` |
| 7 | 38 `console.log` in production | Execution | Medium | Serialization cost on every API call and WS event | Low — strip with babel plugin or remove manually |
| 8 | `axios` used only for GET requests | Bundle | Medium | ~14 KB for functionality native `fetch` covers | Low — replace with `fetch` |
| 9 | CDN script is render-blocking | Load | Medium | Delays FCP | Low — add `defer` attribute |
| 10 | No request cancellation (AbortController) | Network | Medium | Stale responses update state after unmount | Medium — add AbortController to all fetches |
| 11 | No debounce on WS-triggered fetches | Network | Medium | Duplicate concurrent requests on rapid events | Low — add debounce |
| 12 | `uuid` used only in orphaned Config.js | Bundle | Low | ~1 KB dead weight | Low — remove with Config.js |
| 13 | `web-vitals` collected but not reported | Monitoring | Low | Metrics measured but lost | Low — add reporting callback |
| 14 | `sonarft_bg.jpg` unused asset | Assets | Low | Dead file in repo | Low — delete |
| 15 | Logo duplicated in src/ and public/ | Assets | Low | Confusion, potential double-serving | Low — remove public/ copy |
| 16 | `reportWebVitals()` called with no callback | Monitoring | Low | No performance visibility | Low — add console.log in dev |
| 17 | Class components block hook optimization | Rendering | Low | Cannot use `React.memo` or hooks | Medium — refactor to functional |

---

**Save location:** `docs/performance/optimization.md`  
**Next prompts:** `09-testing-quality.md`, `10-code-quality-javascript.md`
