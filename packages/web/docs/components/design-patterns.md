# Prompt 04 — UI Component Design & Reusability

**Package:** `packages/web`  
**Prompt ID:** 04-WEB-UI  
**Output File:** `docs/components/design-patterns.md`  
**Reviewed:** July 2025 | **Updated:** July 2025 (post-implementation)

---

## Implementation Status

| Finding | Severity | Status |
|---|---|---|
| `BotConsole` `<ul><pre>` invalid HTML | Medium | ✅ **Resolved** — `<pre>` is now root element |
| `BotControls` buttons in `<ul>` | Medium | ✅ **Resolved** — replaced with `<div class="bot-controls">` |
| Three `<main>` on Home page | Medium | ✅ **Resolved** — `<div>` + `<section>` used |
| `Parameters` and `Indicators` ~120 lines duplicate | Medium | ✅ **Resolved** — `ConfigCheckboxPanel` generic component extracted |
| CSS class name collisions | Medium | ⚠️ **Partial** — `save-row`/`save-status` now only in `ConfigCheckboxPanel`; `.bots-container` still in two files |
| `useConfigCheckboxes` missing AbortController | Medium | ✅ **Resolved** — `cancelled` flag |
| `Header.tsx` one-line wrapper | Low | ✅ **Resolved** — inlined into `App.tsx` |
| `<form>` wrapper with no `onSubmit` | Low | ✅ **Resolved** — replaced with `<div>` |
| Overlapping CSS breakpoints | Low | ⚠️ **Deferred** |
| `reset.css` + `styles.css` duplicate reset | Low | ⚠️ **Deferred** |
| `App.css` unused CRA styles | Low | ⚠️ **Deferred** |
| Dead component/page files | Low | ✅ **Resolved** — Building, CChatGPT, DoggyWelcome, Dex, Forex, Token removed |
| No `useAuth` convenience hook | Low | ✅ **Resolved** — `useAuth()` exported from `AuthProvider` |
| `BotControls`/`BotConsole`/`TradeHistoryTable` not memoized | Low | ✅ **Resolved** — `React.memo` added |

---

## 1. Component Inventory (updated)

| Component | Location | Purpose | Reused? | ~Lines | Complexity |
|---|---|---|---|---|---|
| `App` | `src/App.tsx` | Root layout, router, lazy routes (Header inlined) | No | 40 | Simple |
| `NavBar` | `components/NavBar/NavBar.tsx` | Navigation links (span not h1) + auth | No | 30 | Simple |
| `Footer` | `components/Footer/Footer.tsx` | Static copyright | No | 7 | Simple |
| `CryptoTicker` | `components/CryptoTicker/CryptoTicker.tsx` | Live price banner (native fetch) | No | 55 | Simple |
| `ErrorBoundary` | `components/ErrorBoundary/ErrorBoundary.tsx` | Render error boundary | Yes | 45 | Simple |
| `PrivateRoute` | `components/PrivateRoute/PrivateRoute.tsx` | Auth guard | Yes | 10 | Simple |
| `ConfigCheckboxPanel` | `components/ConfigCheckboxPanel/ConfigCheckboxPanel.tsx` | **NEW** — generic config form | Yes (×2) | 103 | Medium |
| `Bots` | `components/Bots/Bots.tsx` | Bot management container + live confirm modal | No | 132 | Medium |
| `BotControls` | `components/Bots/BotControls.tsx` | Create/select/remove buttons (`React.memo`) | No | 45 | Simple |
| `BotConsole` | `components/Bots/BotConsole.tsx` | Scrolling log output (`React.memo`) | No | 20 | Simple |
| `TradeHistoryTable` | `components/Bots/TradeHistoryTable.tsx` | History table with locale formatting (`React.memo`) | No | 58 | Simple |
| `ProfitChart` | `components/Charts/ProfitChart.tsx` | P&L chart (`React.memo`, `Intl.DateTimeFormat`) | No | 102 | Medium |
| `Parameters` | `components/Parameters/Parameters.tsx` | Config wrapper (49 lines) | No | 49 | Simple |
| `Indicators` | `components/Indicators/Indicators.tsx` | Config wrapper (66 lines) | No | 66 | Simple |

**Removed:** `Header`, `Building`, `CChatGPT`, `DoggyWelcome`

---

## 2. ConfigCheckboxPanel — New Generic Component

```tsx
function ConfigCheckboxPanel<T extends ConfigState>({
    title, clientId, storageKey, defaultState,
    sections, fetchFn, defaultFn, updateFn,
    saveLabel, className,
}: ConfigCheckboxPanelProps<T>): React.ReactElement
```

`sections` is an array of `{ key, label, tooltips? }` objects. The component handles all state, loading, saving, and feedback internally via `useConfigCheckboxes`. `Parameters` and `Indicators` are now ~40-50 line configuration wrappers.

---

## 3. HTML Validity Fixes

| Component | Before | After |
|---|---|---|
| `BotConsole` | `<ul><pre><div>` | `<pre><span>` |
| `BotControls` | `<ul><button><select>` | `<div class="bot-controls"><button><select>` |
| `Home` | `<main><main>` | `<div><section>` |
| `Welcome` | `<main>` | `<section>` |
| `NavBar` links | `<h1>` | `<span class="nav-title">` |
| Config forms | `<form>` (no onSubmit) | `<div>` |

---

## 4. Accessibility Improvements

- `role="status" aria-live="polite"` on save feedback spans
- `role="status" aria-live="polite"` on bot status badge
- `aria-label` on WS status badge
- `<caption class="sr-only">` on both `TradeHistoryTable` instances
- `aria-live="polite"` on table container
- `.sr-only` utility class added to `index.css`
- `:focus-visible` global styles added to `styles.css`

---

## 5. Custom Hooks (updated)

| Hook | Purpose | Key Changes |
|---|---|---|
| `useWebSocket` | WS connection + backoff | `socketRef` for direct cleanup (no async state updater) |
| `useBots` | Bot lifecycle + WS messages | `useReducer` state machine; `botIdsRef`; RAF log batching; ticket auth |
| `useConfigCheckboxes` | Config form state | `cancelled` flag; all deps explicit; no eslint-disable |
| `useIdleTimeout` | Session idle detection | Unchanged |
| `AuthProvider` / `useAuth` | Auth context | `useAuth()` convenience hook added |

---

## Remaining Open Items

| Item | Priority | Notes |
|---|---|---|
| CSS class name collisions (`.bots-container`) | Low | Still in `bots.css` and `crypto.css` |
| Overlapping mobile CSS breakpoints | Low | Deferred |
| `reset.css` duplicate reset | Low | Deferred |
| `App.css` unused CRA styles | Low | Deferred |
