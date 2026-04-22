# Prompt 07 — Trading Interface UX/UI & Interaction Design

**Package:** `packages/web`  
**Prompt ID:** 07-WEB-UX  
**Output File:** `docs/ux/trading-interface.md`  
**Reviewed:** July 2025 | **Updated:** July 2025 (post-implementation)

---

## Implementation Status

| Finding | Severity | Status |
|---|---|---|
| Simulation toggle broken | **Critical** | ✅ **Resolved** — `botid` added to WS command |
| No confirmation before live trading | **Critical** | ✅ **Resolved** — confirmation modal with risk warning |
| Bot auto-starts without confirmation | **High** | ⚠️ **Deferred** — auto-start is intentional UX; live modal covers the risk |
| 5 of 11 error scenarios silent | **High** | ✅ **Resolved** — `WsErrorEvent` handled; `handleCreate` disconnection error |
| Bot status badge too small | **High** | ⚠️ **Partial** — `role="status" aria-live="polite"` added; visual size unchanged |
| No loading state for bot creation | **Medium** | ⚠️ **Deferred** |
| All NavBar links use `<h1>` | **Medium** | ✅ **Resolved** — replaced with `<span class="nav-title">` |
| Missing `aria-live` for dynamic content | **Medium** | ✅ **Resolved** — bot status, save feedback, table container |
| Bot status "Idle" contrast failure | **Medium** | ✅ **Resolved** — `#7a9ab0` → `#a8c4d8` (~5.8:1) |
| Save status "Saved" contrast failure | **Medium** | ✅ **Resolved** — `#4a8a4a` → `#88dd88` (~5.5:1) |
| No `:focus-visible` styles | **Medium** | ✅ **Resolved** — global `:focus-visible` added to `styles.css` |
| Trade history table unreadable on mobile | **Medium** | ⚠️ **Deferred** — `overflow-x: auto` present; card layout deferred |
| Profit values not formatted | **Medium** | ✅ **Resolved** — `Intl.NumberFormat` |
| Empty bot selector has no guidance | **Medium** | ⚠️ **Deferred** |
| `window.confirm` for bot removal | **Low** | ⚠️ **Deferred** — TODO comment added |
| No table captions | **Low** | ✅ **Resolved** — `<caption class="sr-only">` added |
| Tooltip `title` not accessible on touch | **Low** | ⚠️ **Deferred** |
| Timestamp formatting is ISO string | **Low** | ✅ **Resolved** — `Intl.DateTimeFormat` |
| No active nav link indicator | **Low** | ⚠️ **Deferred** |
| No onboarding for new users | **Low** | ⚠️ **Deferred** |

---

## 1. Accessibility Improvements Implemented

### Heading Hierarchy (fixed)
```tsx
// Before: <h1>Crypt<span>o</span></h1> in nav links
// After:
<span className="nav-title">Crypt<span className="nav-accent">o</span></span>
```
Page now has a correct single `<h1>` (Welcome hero text).

### aria-live Regions (new)
```tsx
// Bot status badge
<span role="status" aria-live="polite" className={`bot-status ${statusLabel.cls}`}>
    {statusLabel.text}
</span>

// Save feedback
<span role="status" aria-live="polite" className={`save-status save-status--${saveStatus}`}>
    {SAVE_MESSAGES[saveStatus]}
</span>

// Table container
<div className="tables-container" aria-live="polite" aria-relevant="additions">
    <table>
        <caption className="sr-only">{caption}</caption>
```

### Color Contrast (fixed)
| Element | Before | After | Ratio |
|---|---|---|---|
| Bot status "Idle" | `#7a9ab0` on `#1a2a3a` | `#a8c4d8` on `#1a2a3a` | ~5.8:1 ✅ |
| Save status "Saved" | `#4a8a4a` on `#1a3a1a` | `#88dd88` on `#1a3a1a` | ~5.5:1 ✅ |

### Focus Visible (new)
```css
:focus-visible {
    outline: 2px solid var(--borderPrimary);
    outline-offset: 2px;
    border-radius: 3px;
}
:focus:not(:focus-visible) { outline: none; }
```

---

## 2. Live Trading Confirmation Modal (new)

```
User clicks "📝 Paper" toggle
  → showLiveConfirm = true
  → Modal appears with:
      "⚠ Enable Live Trading?"
      "Real orders will be placed on exchanges using real funds."
      [Cancel] [⚡ Confirm Live Trading]
  → Only on Confirm: handleToggleSimulation() called
  → Live → Paper: immediate (no confirmation needed)
```

---

## 3. Data Formatting (new)

```tsx
// TradeHistoryTable
const formatDate    = (ts) => new Intl.DateTimeFormat(undefined, { month:"numeric", day:"numeric", hour:"2-digit", minute:"2-digit" }).format(new Date(ts));
const formatCurrency = (v) => new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 }).format(v);
const formatPercent  = (v) => new Intl.NumberFormat(undefined, { style:"percent", minimumFractionDigits: 3 }).format(v);
```

Profit percentage now displays as `0.116%` instead of `0.00116`.

---

## 4. HTML Validity Fixes

| Component | Before | After |
|---|---|---|
| `BotConsole` | `<ul><pre><div>` | `<pre><span>` |
| `BotControls` | `<ul><button>` | `<div class="bot-controls"><button>` |
| `Home` | `<main><main>` | `<div><section>` |
| `Welcome` | `<main>` | `<section>` |
| Config forms | `<form>` (no onSubmit) | `<div>` |

---

## Remaining Open Items

| Item | Priority | Notes |
|---|---|---|
| Bot status badge visual prominence | Medium | Functional (aria-live); visual size deferred |
| Loading state for bot creation | Medium | Deferred |
| Empty bot selector guidance | Medium | Deferred |
| Mobile table layout | Medium | `overflow-x: auto` present; card layout deferred |
| `window.confirm` → styled modal | Low | TODO comment in `useBots.ts` |
| Active nav link indicator | Low | Deferred |
| Onboarding flow | Low | Deferred |
