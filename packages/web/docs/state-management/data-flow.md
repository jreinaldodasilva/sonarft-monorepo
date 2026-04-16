# sonarftweb — State Management & Data Flow

**Prompt:** 03-state-management  
**Category:** State & Data Management  
**Date:** July 2025  
**Depends on:** [docs/architecture/structure.md](../architecture/structure.md), [docs/api-integration/sonarft-integration.md](../api-integration/sonarft-integration.md)

---

## Executive Summary

sonarftweb uses a minimal, fragmented state management approach: React Context API for authentication, component-local state for all trading data, and `localStorage` as a persistence layer for parameters and indicators. There is no shared trading state — each component independently fetches, owns, and manages its own slice of data. Three Context providers (`ParametersProvider`, `IndicatorsProvider`, `ValidatorsProvider`) were created but never mounted, leaving the app without the shared state infrastructure it was apparently designed to use. The result is state duplication between `localStorage`, component state, and the server, with no clear source of truth. The most critical issue is that `Bots.js` accumulates all trading state (bot IDs, logs, orders, trades, WebSocket connection) in a single component with no mechanism to share it with other parts of the app.

---

## 1. State Management Overview

| Approach | Used? | Where |
|---|---|---|
| `useState` (local) | Yes | `Bots.js`, `CryptoTicker.js`, `CChatGPT.js`, `NavBar.js` (via context) |
| Class `this.state` | Yes | `Parameters.js`, `Indicators.js`, `Config.js` |
| React Context API | Partially | `AuthContext` (active), `ParametersContext`, `IndicatorsContext`, `ValidatorsContext` (created but unused) |
| Redux / Zustand / Recoil | No | Not present |
| URL state (query params) | No | Not used |
| `localStorage` | Yes | `Parameters.js` (key: `parametersState`), `Indicators.js` (key: `indicatorsState`) |
| `sessionStorage` | No | Not used |
| Server cache / React Query | No | Not present |

### Global vs Local State

| State | Scope | Location |
|---|---|---|
| Authenticated user | Global | `AuthContext` via `AuthProvider` |
| Bot IDs | Local | `Bots.js` `useState` |
| Bot state (CREATED/REMOVED) | Local | `Bots.js` `useState` |
| Log stream | Local | `Bots.js` `useState` |
| Selected bot ID | Local | `Bots.js` `useState` |
| Order history | Local | `Bots.js` `useState` |
| Trade history | Local | `Bots.js` `useState` |
| Loading flag | Local | `Bots.js` `useState` |
| Exchange/symbol parameters | Local + localStorage | `Parameters.js` `this.state` |
| Indicator settings | Local + localStorage | `Indicators.js` `this.state` |
| Crypto ticker prices | Local | `CryptoTicker.js` `useState` |
| CChatGPT price | Local | `CChatGPT.js` `useState` |

---

## 2. Global State Inventory

### Active Contexts

#### AuthContext (`hooks/AuthProvider.js`)

| State Name | Type | Purpose | Data | Updated From |
|---|---|---|---|---|
| `user` | `object \| null` | Netlify Identity user object | `{ id, email, ... }` | `netlifyIdentity` login/logout events |

Provided values: `{ user, handleLogin, handleLogout }`  
Consumers: `NavBar.js`, `Crypto.js`, `Dex.js`, `Forex.js`, `Token.js`

#### ParametersContext (`components/Parameters/ParametersProvider.js`)

| State Name | Type | Purpose | Data | Updated From |
|---|---|---|---|---|
| `parameters` | `object` | Trading parameters | `{}` (empty default) | `setParameters` setter |

**Status: Created but never mounted in `App.js` or `App_Trading.js`. No component consumes it.**

#### IndicatorsContext (`components/Config/IndicatorsProvider.js`)

| State Name | Type | Purpose | Data | Updated From |
|---|---|---|---|---|
| `indicators` | `array` | Indicator list | `[]` (empty default) | `setIndicators` setter |

**Status: Created but never mounted. No component consumes it.**

#### ValidatorsContext (`components/Config/ValidatorsProvider.js`)

| State Name | Type | Purpose | Data | Updated From |
|---|---|---|---|---|
| `validators` | `array` | Validator list | `[]` (empty default) | `setValidators` setter |

**Status: Created but never mounted. No component consumes it.**

#### WebSocketContext (`hooks/WebSocketContext.js`)

| State Name | Type | Purpose | Data | Updated From |
|---|---|---|---|---|
| `ws` | `WebSocket \| null` | Shared WS instance | Native WebSocket | `useEffect` on mount |
| `wsOpen` | `ref (bool)` | Connection status | `true/false` | `ws.onopen` / `ws.onclose` |
| `listeners` | `ref (object)` | Message listener registry | `{ id: fn }` | `addListener` / `removeListener` |

**Status: Provider defined but never mounted. `useWebSocket` export from this file is never used — `Bots.js` uses the separate `useWebSocket.jsx` hook instead.**

---

## 3. Data Flow Analysis

### Bot Management Flow

```
Mount
  └── getBotIds(clientId) → REST GET /botids/{clientId}
        └── setBotIds([...])  →  <select> dropdown

User: "Create New Bot"
  └── socket.send({ key: "create" })
        └── WS message: "Bot CREATED!"
              ├── getBotIds(clientId) → setBotIds([...])
              ├── setSelectedBotId(ids[last])
              └── socket.send({ key: "run", botid })

WS message: "Order: Success"
  └── fetchAllOrders(botIds) → sequential REST per botId
        └── setOrders([...])

WS message: "Trade: Success"
  └── fetchAllTrades(botIds) → sequential REST per botId
        └── setTrades([...])

User: "Remove Bot"
  └── socket.send({ key: "remove", botid })
        └── WS message: "Bot REMOVED!"
              └── setBotState(REMOVED)
```

All state lives in `Bots.js`. Nothing is shared upward or sideways.

### Parameters Configuration Flow

```
Mount (componentDidMount)
  ├── 1. getParameters(clientId) → REST → setState({ exchanges, symbols })
  ├── 2. [fallback] localStorage.getItem("parametersState") → setState(...)
  └── 3. [fallback] getDefaultParameters() → local JSON → setState(...)

User: checkbox change
  └── setState({ [category]: { [item]: checked } })
        └── localStorage.setItem("parametersState", JSON.stringify(state))

User: "Set bot parameters"
  └── updateParameters(clientId, state) → REST POST /bot/set_parameters/{clientId}
```

**Source of truth ambiguity:** After mount, state lives in three places simultaneously — server, `localStorage`, and component state. They can diverge at any time.

### Indicators Configuration Flow

Identical pattern to Parameters. Same three-tier fallback, same localStorage mirror, same explicit POST on button click.

### Real-time Log Flow

```
WebSocket message received
  └── setLogs(prev => prev + "\n" + event.data)
        └── <pre> renders full log string
              └── consoleEndRef.scrollIntoView() auto-scrolls
```

Logs are append-only strings. There is no log rotation, size limit, or structured log parsing.

### Crypto Ticker Flow

```
Mount + setInterval(180s)
  └── axios.get(CoinGecko /coins/markets) → coinIds
        └── axios.get(CoinGecko /simple/price?ids=...) → setCryptoData([...])
              └── renders scrolling banner
```

Entirely self-contained. No shared state.

---

## 4. Component Props Analysis

### Prop Passing Depth

```
App.js
  └── Crypto.js                    (no props)
        ├── Parameters              clientId={user.id}       [1 level]
        ├── Indicators              clientId={user.id}       [1 level]
        └── Bots                    user={user}              [1 level]
```

Prop drilling depth is only 1 level — shallow. However, `Bots` receives the entire `user` object when it only needs `user.id`. `Parameters` and `Indicators` receive `clientId` directly, which is correct.

### Prop Interface Issues

| Component | Prop | Issue |
|---|---|---|
| `Bots` | `user` | Receives full user object; only uses `user.id`. Should receive `clientId` directly for consistency with `Parameters`/`Indicators` |
| `Parameters` | `clientId` | Undocumented; no PropTypes |
| `Indicators` | `clientId` | Undocumented; no PropTypes |
| `Config` | `user` | Orphaned component; prop never validated |

No PropTypes or TypeScript interfaces are defined anywhere. Prop contracts are implicit.

---

## 5. Context Usage

### AuthContext — Well Implemented

- Created with `createContext()`, provided at root level in `App.js`
- Consumed via `useContext(AuthContext)` in `NavBar`, `Crypto`, `Dex`, `Forex`, `Token`
- Context value is `{ user, handleLogin, handleLogout }` — stable object shape
- **Re-render concern:** The context value object `{ user, handleLogin, handleLogout }` is recreated on every render of `AuthProvider` because `handleLogin` and `handleLogout` are defined as inline functions. This causes all consumers to re-render whenever `AuthProvider` re-renders, even if `user` hasn't changed.

```js
// Current — handleLogin/handleLogout recreated every render
const handleLogin = () => { netlifyIdentity.open(); };
const handleLogout = () => { netlifyIdentity.logout(); };

// Fix — wrap in useCallback
const handleLogin = useCallback(() => { netlifyIdentity.open(); }, []);
const handleLogout = useCallback(() => { netlifyIdentity.logout(); }, []);
```

### Unused Contexts — Architectural Debt

Three contexts (`ParametersContext`, `IndicatorsContext`, `ValidatorsContext`) and one WebSocket context (`WebSocketContext`) were built but never integrated. This suggests a planned refactoring toward shared state that was never completed. The current `Parameters.js` and `Indicators.js` class components manage their own state independently, bypassing the context system entirely.

### Provider Nesting (Current)

```
<AuthProvider>          ← only active provider
  <Router>
    <App layout>
      <Routes>
        <Crypto>
          <Parameters>  ← manages own state (class)
          <Indicators>  ← manages own state (class)
          <Bots>        ← manages own state (functional)
```

### Provider Nesting (Intended, based on existing providers)

```
<AuthProvider>
  <ParametersProvider>
    <IndicatorsProvider>
      <ValidatorsProvider>
        <WebSocketProvider>
          <Router> ...
```

This intended structure was never wired up.

---

## 6. Reducer Patterns

No `useReducer` or Redux is used anywhere. `Bots.js` has the most complex state transitions but manages them with multiple `useState` calls and inline logic rather than a reducer. The `BotState` enum (`CREATED: 0, REMOVED: 1`) is the closest thing to a state machine, but it's only used to control button disabled states.

The bot lifecycle would benefit from `useReducer`:

```js
// Suggested reducer for Bots.js
const initialState = {
    botIds: [], selectedBotId: null, botStatus: 'idle',
    logs: '', orders: [], trades: [], isLoading: false, error: null
};

function botsReducer(state, action) {
    switch (action.type) {
        case 'FETCH_BOTS_START': return { ...state, isLoading: true, error: null };
        case 'FETCH_BOTS_SUCCESS': return { ...state, isLoading: false, botIds: action.payload };
        case 'FETCH_BOTS_ERROR': return { ...state, isLoading: false, error: action.payload };
        case 'BOT_CREATED': return { ...state, botIds: action.payload, selectedBotId: action.payload.at(-1) };
        case 'BOT_REMOVED': return { ...state, botStatus: 'idle' };
        case 'LOG_APPEND': return { ...state, logs: state.logs + '\n' + action.payload };
        case 'ORDERS_UPDATED': return { ...state, orders: action.payload };
        case 'TRADES_UPDATED': return { ...state, trades: action.payload };
        default: return state;
    }
}
```

---

## 7. API Data Management

| Aspect | Status | Detail |
|---|---|---|
| Normalization | None | API responses used directly as-is |
| Cache invalidation | None | `localStorage` is never invalidated; stale data persists across sessions |
| Optimistic updates | None | UI only updates after server confirms |
| Conflict resolution | None | If server state differs from localStorage on mount, server wins (correct), but no notification to user |
| Loading states | Partial | Only `Bots.js` has `isLoading`; `Parameters` and `Indicators` show nothing during fetch |
| Error states | None | No error state in any component |

### localStorage Staleness Problem

`Parameters.js` and `Indicators.js` write to `localStorage` on every checkbox change. On next mount, the fallback chain is:

1. Try server (correct)
2. Try localStorage (potentially stale from previous session)
3. Try bundled JSON defaults

If the server is unreachable on mount, the user gets their last local state — which may be days old and out of sync with what the server actually has. There is no timestamp, version, or TTL on the stored data.

```js
// Current localStorage write — no metadata
localStorage.setItem("parametersState", JSON.stringify(this.state));

// Recommended — add timestamp for staleness detection
localStorage.setItem("parametersState", JSON.stringify({
    data: this.state,
    savedAt: Date.now(),
    version: 1
}));
```

---

## 8. Local Storage & Persistence

| Key | Component | Data Stored | Encrypted | Expires | Sensitive? |
|---|---|---|---|---|---|
| `parametersState` | `Parameters.js` | `{ exchanges: {}, symbols: {} }` | No | Never | Low |
| `indicatorsState` | `Indicators.js` | `{ periods: {}, oscillators: {}, movingaverages: {} }` | No | Never | Low |

Netlify Identity also writes to `localStorage` internally (token, user data) — this is managed by the widget, not the app code.

### Hydration Pattern

Both `Parameters` and `Indicators` hydrate from `localStorage` in the constructor:

```js
constructor() {
    super();
    const localStorageState = localStorage.getItem("parametersState");
    this.state = localStorageState
        ? JSON.parse(localStorageState)
        : { exchanges: {}, symbols: {} };
}
```

This is synchronous and happens before `componentDidMount`. The server fetch in `componentDidMount` then overwrites this if successful — meaning the user briefly sees stale localStorage data before the server response arrives. No loading indicator covers this flash.

### Sync Between Memory and Storage

State → localStorage sync is one-directional and manual: checkbox changes write to localStorage immediately. The server is only updated on explicit button click. This creates a three-way divergence risk:

```
localStorage  ←→  component state  ←→  server
     ↑                                    ↑
  (on change)                      (on button click)
```

---

## 9. Real-time Data Integration

### WebSocket → State Mapping

| WS Message Content | State Update | Method |
|---|---|---|
| Any message | `logs` appended | `setLogs(prev => prev + "\n" + event.data)` |
| Contains `"Bot CREATED!"` | `botIds`, `selectedBotId` refreshed | REST fetch → `setBotIds`, `setSelectedBotId` |
| Contains `"Bot REMOVED!"` | `botState` → `REMOVED` | `setBotState(BotState.REMOVED)` |
| Contains `"Order: Success"` | `orders` refreshed | REST fetch → `setOrders` |
| Contains `"Trade: Success"` | `trades` refreshed | REST fetch → `setTrades` |

### Issues

**String-based event detection is fragile.** The entire real-time update system depends on `event.data.includes("Bot CREATED!")`. If the sonarft server changes its log format (e.g., `"Bot bot_123 CREATED successfully"`), the client silently stops responding to bot creation events.

**No deduplication.** If the server sends two `"Order: Success"` messages in rapid succession (e.g., two orders filled simultaneously), `fetchAllOrders` is called twice concurrently. Both calls update `orders` state, but the second may overwrite the first with identical data — harmless but wasteful.

**Log growth is unbounded.** `logs` is a string that only grows. A long-running bot session will accumulate megabytes of log text in memory with no rotation or truncation.

**`botIds` closure stale in `onmessage`.** The `socket.onmessage` handler in `Bots.js` captures `botIds` from the closure at the time the effect runs. If `botIds` changes (new bot added), the handler still references the old array until the effect re-runs. This is partially mitigated by the `botIds` dependency in the `useEffect` array, but creates a brief window of stale data.

```js
// The effect re-registers onmessage whenever botIds changes — correct but subtle
useEffect(() => {
    if (wsOpen) {
        socket.onmessage = async (event) => {
            // botIds captured here — stale if effect hasn't re-run yet
            const allOrders = await fetchAllOrders(botIds);
        };
    }
}, [clientId, wsOpen, socket, botIds, selectedBotId]);
```

---

## 10. Performance & Re-renders

| Issue | Component | Severity | Detail |
|---|---|---|---|
| `AuthContext` value recreated every render | `AuthProvider` | Low | `handleLogin`/`handleLogout` not memoized; all consumers re-render on any `AuthProvider` state change |
| `Bots.js` re-registers `onmessage` on every `botIds` change | `Bots.js` | Low | Necessary for closure freshness, but causes brief gaps in message handling |
| Log string grows unbounded | `Bots.js` | Medium | Large `logs` string causes increasingly expensive re-renders on every message |
| No `useMemo`/`useCallback` anywhere | All functional components | Low | Not critical at current scale, but will matter as components grow |
| Class components can't use hooks | `Parameters.js`, `Indicators.js` | Low | Cannot use `useMemo`, `useCallback`, or custom hooks without refactoring to functional |
| `CryptoTicker` renders items twice (original + clone for CSS scroll) | `CryptoTicker.js` | Low | Intentional CSS animation technique; not a bug but doubles DOM nodes |

### Log Performance Fix

```js
// Replace unbounded string with a capped array
const [logs, setLogs] = useState([]);
const MAX_LOGS = 500;

// In onmessage:
setLogs(prev => [...prev.slice(-MAX_LOGS + 1), event.data]);

// In render:
<pre className="console">
    {logs.join('\n')}
    <div ref={consoleEndRef} />
</pre>
```

---

## 11. Developer Experience

| Aspect | Status | Notes |
|---|---|---|
| State debugging | Poor | No Redux DevTools; no state logging; must use React DevTools manually |
| Time-travel debugging | Not available | No Redux or equivalent |
| State documentation | None | No comments or docs on state shape in any component |
| Testing state | Difficult | Class components with `componentDidMount` API calls require complex mocking; no test utilities set up |
| State traceability | Poor | State updates scattered across multiple `useEffect` hooks and class methods with no central log |

---

## 12. State Flow Diagram

```mermaid
graph TD
    subgraph External Sources
        SonarftAPI[sonarft REST API]
        SonarftWS[sonarft WebSocket]
        CoinGeckoAPI[CoinGecko API]
        NetlifyID[Netlify Identity]
        LS[(localStorage)]
    end

    subgraph Global State
        AuthCtx[AuthContext\nuser, handleLogin, handleLogout]
    end

    subgraph Bots.js Local State
        BotIds[botIds: string array]
        BotState2[botState: CREATED/REMOVED]
        SelectedBot[selectedBotId: string]
        Logs[logs: string - append only]
        Orders[orders: array]
        Trades[trades: array]
        Loading[isLoading: bool]
        WSConn[socket: WebSocket]
    end

    subgraph Parameters.js Local State
        ParamState[exchanges: object\nsymbols: object]
    end

    subgraph Indicators.js Local State
        IndState[periods: object\noscillators: object\nmovingaverages: object]
    end

    subgraph Unused Contexts
        ParamCtx[ParametersContext - UNUSED]
        IndCtx[IndicatorsContext - UNUSED]
        ValCtx[ValidatorsContext - UNUSED]
        WSCtx[WebSocketContext - UNUSED]
    end

    NetlifyID -->|login event| AuthCtx
    AuthCtx -->|user.id as clientId| Bots.js Local State
    AuthCtx -->|user.id as clientId| Parameters.js Local State
    AuthCtx -->|user.id as clientId| Indicators.js Local State

    SonarftAPI -->|GET /botids| BotIds
    SonarftAPI -->|GET /orders| Orders
    SonarftAPI -->|GET /trades| Trades
    SonarftAPI -->|GET /parameters| ParamState
    SonarftAPI -->|GET /indicators| IndState

    SonarftWS -->|text messages| Logs
    SonarftWS -->|BOT_CREATED| BotIds
    SonarftWS -->|BOT_REMOVED| BotState2
    SonarftWS -->|ORDER_SUCCESS| Orders
    SonarftWS -->|TRADE_SUCCESS| Trades

    ParamState <-->|read/write| LS
    IndState <-->|read/write| LS

    CoinGeckoAPI -->|prices| CryptoTicker.js
```

---

## 13. Issue Analysis

### Prop Drilling
**Severity: Low.** Only 1 level deep. Not a current problem, but `Bots` receiving `user` instead of `clientId` is inconsistent.

### State Duplication
**Severity: High.** Parameters and indicators exist in three places simultaneously: server, `localStorage`, and component state. There is no single source of truth. After a user edits checkboxes but doesn't click "Set", the three sources diverge permanently until the next page load.

### Stale State
**Severity: Medium.** The `onmessage` closure in `Bots.js` captures `botIds` at effect registration time. Between effect re-runs, `botIds` in the handler may be stale. Also, `localStorage` data never expires and can be arbitrarily old.

### Memory Leaks
**Severity: Medium.** Two issues:
1. `useWebSocket.jsx` calls `connect()` recursively on close for auto-reconnect, but the cleanup function only closes the current socket — if reconnection fires before cleanup, a second socket may be created.
2. `logs` string grows without bound for the lifetime of the component.

### Untracked Mutations
**Severity: Low.** No direct state mutations detected. Class components use `setState` correctly. Functional components use setter functions. The `listeners` ref in `WebSocketContext.js` is mutated directly (`listeners.current[id] = func`) but this is intentional for a ref.

### Unused Infrastructure
**Severity: Medium.** Four context providers were built but never integrated. This represents dead code that creates confusion about the intended architecture. Either complete the migration to shared context state or remove the unused providers.

---

## Summary of Recommendations by Priority

| Priority | Issue | Recommendation |
|---|---|---|
| High | Three-way state duplication (server / localStorage / component) | Establish server as single source of truth; use localStorage only as offline cache with TTL |
| High | Unused context providers create architectural confusion | Either wire `ParametersContext` + `IndicatorsContext` into the app, or remove them |
| Medium | `Bots.js` manages too much state | Extract bot state into a `useBots` custom hook; extract order/trade tables into sub-components |
| Medium | Log string grows unbounded | Cap logs array at N entries; use array instead of string |
| Medium | `onmessage` string-matching is fragile | Coordinate with sonarft backend to send structured JSON events |
| Medium | No error state in any component | Add `error` state alongside `isLoading` in all data-fetching components |
| Low | `AuthContext` value not memoized | Wrap `handleLogin`/`handleLogout` in `useCallback`; memoize context value with `useMemo` |
| Low | Class components block hook adoption | Refactor `Parameters.js` and `Indicators.js` to functional components |
| Low | No PropTypes or TypeScript | Add PropTypes at minimum; consider TypeScript migration |
| Low | No state documentation | Document state shape with JSDoc comments in each component |

---

**Save location:** `docs/state-management/data-flow.md`  
**Next prompts:** `04-ui-component-design.md`, `05-real-time-updates.md`, `08-performance-optimization.md`
