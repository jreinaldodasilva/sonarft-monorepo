# sonarftweb — Code Quality & JavaScript Best Practices

**Prompt:** 10-code-quality-javascript  
**Category:** Code Quality  
**Date:** July 2025  
**Depends on:** All previous prompts

---

## Executive Summary

The codebase is clean at the syntax level — no `var`, no `eval`, no `dangerouslySetInnerHTML`, consistent `const`/`let` usage, and `async/await` throughout. The main quality issues are structural: mixed class and functional components, zero type safety (no PropTypes, no TypeScript), `index` used as React list keys in 11 places, inline styles scattered across components, 38 `console.log` statements in production code, significant code duplication between `Parameters.js` and `Indicators.js`, and dead code (`App_Trading.js`, `Config.js`, `NavBar_Trading.js`, unused providers) that adds confusion without value. The ESLint config is minimal (CRA defaults only) and Prettier is installed but not enforced in CI.

---

## 1. Code Style & Consistency

| Aspect | Status |
|---|---|
| Linter | ESLint via CRA (`react-app` + `react-app/jest` presets) — minimal rules |
| Formatter | Prettier v3.0.3 installed; `format` script in `package.json` |
| Formatter enforced in CI | No — `cloudbuild.yaml` has no format/lint step |
| Indentation | 4 spaces consistently throughout ✓ |
| Quote style | Double quotes in JSX, double quotes in JS — consistent ✓ |
| Semicolons | Present consistently ✓ |
| `var` usage | None — all `const`/`let` ✓ |
| File naming | PascalCase for components, camelCase for hooks/utils ✓ |

The `.hintrc` file configures `webhint` (a browser compatibility linter) with the `development` preset — this is separate from ESLint and only checks HTML compatibility, not JS quality.

---

## 2. JavaScript Best Practices

### Strengths

- `const`/`let` used exclusively — no `var` anywhere ✓
- `async/await` used consistently for all async operations (18 async arrow functions) ✓
- Template literals used for string interpolation ✓
- Spread operator used correctly in state updates ✓
- Arrow functions used for callbacks and class methods ✓

### Gaps

**Optional chaining used in only one place:**
```js
// Bots.js — only usage of optional chaining
consoleEndRef.current?.scrollIntoView({ behavior: "smooth" });
```

Several other places would benefit from it:
```js
// api.js — could use optional chaining
const data = await response.json();
return data.botid;  // throws if data is null/undefined

// Bots.js — could use optional chaining
socket.send(JSON.stringify({ ... }));  // guarded by if(socket) — ok, but ?.send() is cleaner
```

**Nullish coalescing (`??`) not used:**
```js
// Parameters.js — uses || which coerces falsy values
checked={options[item] || false}
// Better:
checked={options[item] ?? false}
```

**Destructuring underused in some places:**
```js
// Bots.js — could destructure
const clientId = user.id;  // fine, but could be in props destructuring
const Bots = ({ user }) => { ... }
// Better:
const Bots = ({ user: { id: clientId } }) => { ... }
```

---

## 3. React Best Practices

### Class vs Functional Components

| Component | Type | Should Be |
|---|---|---|
| `Parameters.js` | Class | Functional + hooks |
| `Indicators.js` | Class | Functional + hooks |
| `Config.js` | Class | Functional + hooks (or removed) |

Three class components remain. They cannot use hooks, `React.memo`, or `useCallback`. CRA supports functional components fully — there is no reason to keep class components in new code.

### `key={index}` Anti-pattern — 11 Occurrences

Using array index as React key causes incorrect reconciliation when list items are reordered or removed:

```jsx
// Bots.js — index as key (problematic for dynamic lists)
{botIds.map((botId, index) => (
    <option key={index} value={botId}>{botId}</option>
))}

{orders.map((order, index) => (
    <tr key={index}>...</tr>
))}

{trades.map((trade, index) => (
    <tr key={index}>...</tr>
))}
```

For the bot selector `<option>`, `botId` itself is a unique string — use it directly:
```jsx
<option key={botId} value={botId}>{botId}</option>
```

For order/trade rows, use a stable identifier from the data (e.g., `order.timestamp + order.buy_exchange`), or add an `id` field to the server response.

### Inline Styles — 11 Occurrences

```jsx
// NavBar.js — repeated on every Link (5 times)
<Link style={{ textDecoration: "none" }} to="/crypto">

// Bots.js — conditional opacity via inline style
<button style={{ opacity: botState === BotState.REMOVED ? 1 : 0.5 }}>
```

`textDecoration: "none"` on every `<Link>` should be a CSS class. The opacity pattern in `Bots.js` should use a CSS class toggled by state:

```css
/* bots.css */
.btn-disabled { opacity: 0.5; }
```
```jsx
<button className={isDisabled ? 'btn-disabled' : ''}>
```

### useEffect Dependency Arrays

```js
// Bots.js — large dependency array, re-registers onmessage frequently
useEffect(() => {
    if (wsOpen) {
        socket.onmessage = async (event) => { ... };
    }
}, [clientId, wsOpen, socket, botIds, selectedBotId]);
```

All dependencies are legitimate — the handler needs fresh `botIds` to avoid stale closure. However, the pattern of assigning `socket.onmessage` directly (rather than using `addEventListener`) means only one handler can exist at a time. This is fine for the current single-consumer model but would break if multiple effects tried to handle messages.

### No Error Boundaries

No `ErrorBoundary` component exists. A runtime error in `Bots.js` (e.g., `user.id` is undefined, or a malformed API response causes a render crash) would unmount the entire `<Crypto>` page with a blank screen and no recovery path.

---

## 4. Error Handling

### try/catch Coverage

| File | Functions | Has try/catch | Missing |
|---|---|---|---|
| `utils/api.js` | 10 | 8 | `getBotIds`, `getOrders`, `getTrades` |
| `Parameters.js` | `componentDidMount`, `handleSetClick` | Yes | — |
| `Indicators.js` | `componentDidMount`, `handleSetClick` | Yes | — |
| `Bots.js` | `fetchBotIds` (useEffect) | Yes (finally only) | No catch block |
| `CryptoTicker.js` | `fetchData` | Yes | — |
| `CChatGPT.js` | `fetchData` | Yes | — |

`Bots.js` `fetchBotIds` has a `finally` but no `catch`:
```js
const fetchBotIds = async () => {
    try {
        setIsLoading(true);
        const ids = await getBotIds(clientId);
        setBotIds(ids);
    } finally {
        setIsLoading(false);  // no catch — error is silently swallowed
    }
};
```

### Inconsistent Error Handling Pattern

Three different patterns are used across the codebase:

```js
// Pattern 1 — try/catch + re-throw (api.js getBotId)
catch (e) { console.log(...); throw e; }

// Pattern 2 — try/catch + swallow (Parameters.js componentDidMount)
catch (e) { console.log(...); }  // continues to next fallback

// Pattern 3 — no try/catch (getBotIds, getOrders, getTrades)
// unhandled rejection
```

A consistent pattern should be established and applied uniformly.

---

## 5. Code Organization

### File Size

| File | Lines | Status |
|---|---|---|
| `Bots.js` | 257 | ⚠️ Over 200 — should be split |
| `utils/api.js` | 204 | ⚠️ Large but well-structured |
| `Indicators.js` | 147 | Acceptable |
| `Parameters.js` | 139 | Acceptable |
| All others | < 100 | ✓ |

### Import Organization

Imports are not consistently ordered. The CRA ESLint config does not enforce import ordering. A consistent order would be:

```js
// 1. React
import React, { useState, useEffect } from 'react';
// 2. Third-party
import { Link } from 'react-router-dom';
// 3. Internal — hooks/context
import { AuthContext } from '../../hooks/AuthProvider';
// 4. Internal — components
import Bots from '../../components/Bots/Bots';
// 5. Internal — utils
import { getBotIds } from '../../utils/api';
// 6. Assets and styles
import './crypto.css';
```

### No Index Files

No `index.js` barrel files exist in any directory. Imports use full paths:
```js
import Bots from "../../components/Bots/Bots";
// vs with barrel:
import { Bots } from "../../components";
```

For the current small codebase this is fine, but barrel files would simplify imports as the codebase grows.

---

## 6. Naming Conventions

### Strengths

- Components: PascalCase throughout ✓
- Functions/variables: camelCase throughout ✓
- CSS classes: kebab-case throughout ✓
- Constants in `constants.js`: UPPER_SNAKE_CASE ✓

### Issues

| Issue | Location | Example |
|---|---|---|
| Boolean state not prefixed with `is`/`has` | `Bots.js` | `wsOpen` → `isWsOpen`; `botState` is an enum not a boolean |
| Abbreviated names | `Bots.js` | `ws`, `WS` — acceptable in context but `wsOpen` vs `isWsOpen` inconsistent |
| `textTerciary` typo | `variables.css`, `footer.css` | Should be `textTertiary` |
| `backgroundTerciary` typo | `footer.css` | Should be `backgroundTertiary` |
| `BotState.CREATED = 0` / `REMOVED = 1` | `Bots.js` | Values are counterintuitive — `CREATED` should be truthy |

### Magic Strings in JSX

```jsx
// Bots.js — hardcoded label
<h2>Bots <span>(paper trading)</span></h2>
```

"paper trading" is hardcoded and does not reflect the actual `is_simulating_trade` config value. This should be dynamic.

---

## 7. Documentation & Comments

| Aspect | Status |
|---|---|
| Project README | Present — comprehensive ✓ |
| JSDoc on functions | None |
| Inline comments | Sparse — a few in `Bots.js` and `Parameters.js` |
| TODO/FIXME comments | None found |
| Commented-out code | Present in several files |

### Commented-Out Code

```js
// constants.js — 4 commented-out URL alternatives
//const HTTPURL = "https://100.66.35.193:5000";
//const WSURL = "wss://100.66.35.193:5000/ws";
//const HTTPURL = "https://81f5-179-108-19-66.ngrok-free.app";
//const WSURL = "wss://81f5-179-108-19-66.ngrok-free.app/ws";

// Bots.js — commented-out debug log
//console.log("Rendering with:", { orders, trades, botIds });

// Home.js — commented-out second welcome section
{/*
<div className="welcome2-container">
    <Welcome/>
</div>
*/}
```

Commented-out code should be removed — version control (git) preserves history.

---

## 8. Performance Anti-patterns

| Anti-pattern | Location | Occurrences |
|---|---|---|
| `key={index}` in lists | `Bots.js`, `CryptoTicker.js`, `CChatGPT.js`, Config components | 11 |
| Inline style objects (recreated each render) | `NavBar.js`, `NavBar_Trading.js`, `Bots.js` | 11 |
| Inline functions in JSX props | `Parameters.js`, `Indicators.js` `onChange` | Multiple |
| No `React.memo` on any component | All components | — |
| Unbounded state growth (`logs` string) | `Bots.js` | 1 |
| Sequential awaits where parallel possible | `helpers.js` | 2 functions |

### Inline Functions in JSX

```jsx
// Parameters.js — new function created on every render
onChange={(e) => this.handleCheckboxChange(e, category)}
```

In class components this cannot be fixed with `useCallback`, but extracting to a bound method avoids the inline arrow function:
```jsx
// Bind in constructor or use class field
handleExchangeChange = (e) => this.handleCheckboxChange(e, 'exchanges');
// Then:
onChange={this.handleExchangeChange}
```

---

## 9. Security Anti-patterns

| Issue | Location | Severity |
|---|---|---|
| Hardcoded localhost URLs | `constants.js`, `WebSocketContext.js` | High |
| Sensitive data in `console.log` | `api.js` (trade/order data) | Medium |
| No input validation | All forms | Medium |
| CDN script without SRI | `public/index.html` | High |
| No `dangerouslySetInnerHTML` | — | ✓ Safe |
| No `eval` | — | ✓ Safe |

(Full security analysis in [docs/security/auth-and-security.md](../security/auth-and-security.md))

---

## 10. Maintainability Issues

### Dead Code Inventory

| File/Symbol | Status | Action |
|---|---|---|
| `App_Trading.js` | Not imported anywhere | Remove or merge into `App.js` |
| `NavBar_Trading.js` | Not imported anywhere | Remove or wire into `App_Trading.js` |
| `Config.js` | Not routed; imports missing files | Remove or complete |
| `ParametersProvider.js` | Created, never mounted | Remove or integrate |
| `IndicatorsProvider.js` | Created, never mounted | Remove or integrate |
| `ValidatorsProvider.js` | Created, never mounted | Remove or integrate |
| `WebSocketContext.js` | Created, never mounted | Remove or integrate |
| `getBotId` (singular) in `api.js` | Defined but never called | Remove |
| `sonarft_bg.jpg` | In assets, never imported | Remove |
| `public/sonarftlogo.png` | Duplicate of `src/assets` version | Remove |
| `public/defaultParameters.json` | Wrong shape; never used by app | Remove |
| `public/defaultIndicators.json` | Wrong shape; never used by app | Remove |
| `public/stats.json` | Not referenced anywhere | Remove or document |

### Code Duplication

The most significant duplication is between `Parameters.js` and `Indicators.js`. A diff of the two files shows ~80% identical code — only the state keys, API function names, and localStorage key differ.

```
Parameters.js                    Indicators.js
─────────────────────────────    ─────────────────────────────
constructor() { localStorage }   constructor() { localStorage }
componentDidMount() { 3-tier }   componentDidMount() { 3-tier }
handleCheckboxChange()           handleCheckboxChange()
handleSetClick()                 handleSetClick()
renderCheckboxes()               renderCheckboxes()
render() { form + button }       render() { form + button }
```

---

## 11. Code Smells

| Smell | Location | Description |
|---|---|---|
| **Large component** | `Bots.js` (257 lines) | 5 responsibilities in one file |
| **Duplicate class** | `Parameters.js` / `Indicators.js` | ~80% identical code |
| **Dead code** | 13 files/symbols | Unused components, providers, assets |
| **Commented-out code** | `constants.js`, `Bots.js`, `Home.js` | Should be deleted |
| **Magic string** | `Bots.js` `"(paper trading)"` | Hardcoded, not dynamic |
| **Inconsistent boolean naming** | `wsOpen` | Should be `isWsOpen` |
| **Index as key** | 11 locations | Incorrect reconciliation on reorder |
| **Inline styles** | 11 locations | Recreated on every render |
| **Typo in variable names** | `variables.css` | `Terciary` → `Tertiary` (2 occurrences) |
| **Parallel entry points** | `App.js` / `App_Trading.js` | Two root components, one unused |
| **`PrivateRoute` defined 4×** | Page files | Identical inline function |

---

## 12. Type Safety

No TypeScript. No PropTypes. The codebase has zero type safety.

| Risk | Example |
|---|---|
| `user` prop could be null | `Bots.js`: `user.id` throws if `user` is null |
| API response shape assumed | `data.botids` — no check if `botids` key exists |
| `botIds` assumed to be array | `fetchAllOrders(botIds)` — no guard if `botIds` is undefined |
| `options[item]` assumed to be boolean | `checked={options[item] || false}` — works but undocumented |

**Minimum fix — add PropTypes:**
```js
import PropTypes from 'prop-types';

Bots.propTypes = {
    user: PropTypes.shape({
        id: PropTypes.string.isRequired,
    }).isRequired,
};
```

---

## 13. Build & Tooling

| Aspect | Status |
|---|---|
| Build tool | CRA (`react-scripts`) — zero config ✓ |
| Dev server | `react-scripts start` ✓ |
| ESLint in CI | Not enforced |
| Prettier in CI | Not enforced |
| Tests in CI | Not run |
| Environment variables | Not used — URLs hardcoded |
| Source maps in production | CRA default: enabled (leaks source) |
| `GENERATE_SOURCEMAP=false` | Not set |

### Source Maps in Production

CRA generates source maps by default. This means the original source code is accessible to anyone who opens DevTools on the production site. For a trading application, this exposes all business logic.

**Fix:**
```json
"build": "GENERATE_SOURCEMAP=false react-scripts build"
```

---

## 14. Code Quality Metrics

| Metric | Value |
|---|---|
| Total source JS lines | ~1,812 |
| Total source CSS lines | ~1,480 |
| Number of components | 18 |
| Class components | 3 (Parameters, Indicators, Config) |
| Functional components | 15 |
| Custom hooks | 2 active (useWebSocket, AuthProvider) + 2 unused |
| Test coverage | ~0% |
| `console.log` in production | 38 |
| `key={index}` occurrences | 11 |
| Inline style occurrences | 11 |
| Dead files | ~13 |
| npm dependencies (runtime) | 8 |
| npm vulnerabilities | 63 (3 critical, 29 high) |
| Duplicated component pairs | 1 major (Parameters/Indicators) |

---

## 15. Issues Summary

| # | Issue | Type | Severity | Occurrences | Remediation |
|---|---|---|---|---|---|
| 1 | No PropTypes or TypeScript | Type Safety | High | All components | Add PropTypes to all components with props |
| 2 | `key={index}` in lists | React | High | 11 | Use stable unique IDs as keys |
| 3 | 38 `console.log` in production | Quality | High | 38 | Remove or replace with conditional logging |
| 4 | Dead code (unused files/providers) | Maintainability | Medium | ~13 files | Remove all dead code |
| 5 | `Parameters.js`/`Indicators.js` duplication | Maintainability | High | 2 files | Extract shared `useConfigCheckboxes` hook |
| 6 | `PrivateRoute` defined 4 times | Maintainability | Medium | 4 files | Extract to shared component |
| 7 | Inline styles | Performance | Medium | 11 | Move to CSS classes |
| 8 | No error boundaries | React | Medium | 0 | Add `ErrorBoundary` around `<Crypto>` |
| 9 | Commented-out code | Quality | Low | 3 files | Delete — use git history |
| 10 | Source maps in production build | Security | Medium | Build config | Set `GENERATE_SOURCEMAP=false` |
| 11 | ESLint/Prettier not enforced in CI | Tooling | Medium | CI config | Add lint/format check to `cloudbuild.yaml` |
| 12 | `getBotId` (singular) never called | Dead code | Low | `api.js` | Remove |
| 13 | `textTerciary`/`backgroundTerciary` typos | Quality | Low | 2 | Fix spelling |
| 14 | `"(paper trading)"` hardcoded | Quality | Low | `Bots.js` | Make dynamic from config |
| 15 | Optional chaining used in 1 of many places | Quality | Low | Many | Apply consistently |

---

## 16. Recommendations

**Immediate (< 1 day):**
- Remove all 38 `console.log` statements or gate behind `process.env.NODE_ENV === 'development'`
- Set `GENERATE_SOURCEMAP=false` in build script
- Fix `key={index}` in `Bots.js` order/trade tables and bot selector
- Delete all dead files (13 identified above)
- Fix `Terciary` typo in `variables.css` and `footer.css`

**Short-term (1 week):**
- Add PropTypes to all components with props
- Extract `PrivateRoute` to a shared component
- Extract `TradeHistoryTable` from `Bots.js`
- Add `ErrorBoundary` around `<Crypto>` page
- Add ESLint and Prettier checks to `cloudbuild.yaml`
- Move `style={{ textDecoration: "none" }}` to a CSS class

**Medium-term (2–4 weeks):**
- Refactor `Parameters.js` and `Indicators.js` to functional components with a shared `useConfigCheckboxes` hook
- Split `Bots.js` into `useBots` hook + sub-components
- Add environment variable support for all URLs
- Consider TypeScript migration starting with `utils/api.js`

---

**Save location:** `docs/code-quality/code-quality.md`  
**Next prompt:** `11-final-consolidation.md`
