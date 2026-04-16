# sonarftweb — Trading Interface UX/UI & Interaction Design

**Prompt:** 07-trading-interface-ux  
**Category:** User Experience  
**Date:** July 2025  
**Depends on:** [docs/architecture/structure.md](../architecture/structure.md), [docs/components/design-patterns.md](../components/design-patterns.md)

---

## Executive Summary

sonarftweb's trading interface is functional but provides a minimal user experience. The core trading workflow (sign in → configure → create bot → monitor) is achievable, but every step lacks feedback: there are no success confirmations, no error messages, no loading states on configuration forms, no connection status indicator, and no confirmation dialogs before destructive actions. The 13-column order/trade history tables overflow on any screen smaller than a wide desktop. Accessibility is poor — no ARIA labels, no semantic landmark roles, incorrect heading hierarchy, and the global `font-size: small` override makes all text smaller than browser defaults. There is no data visualization, no performance analytics, and no onboarding guidance. The design system (CSS variables, responsive breakpoints) is a solid foundation, but the trading-specific UX layer built on top of it is incomplete.

---

## 1. Navigation & Information Architecture

### Current Structure

```
/ (Home)          — Public — Welcome hero text only
/crypto           — Auth-gated — Main trading interface
/cryptochatgpt    — Public — Single coin price display
/doggy            — Public — Empty section
```

`App_Trading.js` defines an alternate structure (Forex, DEX, Token) that is not active. Those routes render `<Building />` placeholders.

### Issues

- **No active page indicator.** The NavBar has no visual cue showing which page the user is on. All nav links look identical whether active or not.
- **No breadcrumbs.** Not needed at this depth, but the `/crypto` page has no page title or heading that confirms where the user is.
- **Navigation links use `<h1>` tags.** Every nav link is wrapped in an `<h1>`:
  ```jsx
  <Link to="/crypto"><h1>Crypt<span>o</span></h1></Link>
  ```
  This is semantically incorrect — `<h1>` is a document heading, not a navigation label. Screen readers announce these as top-level headings, not links.
- **No mobile hamburger menu.** On small screens, all nav links are displayed inline. At 360px width with 3 links plus a logo and a button, the navbar becomes cramped.
- **`/doggy` and `/cryptochatgpt` routes** have no clear purpose from a trading application perspective — they appear to be experimental pages left in the navigation.

---

## 2. Trading Workflows

### Workflow 1: First-Time Setup

| Step | UI Element | Clarity | Issues |
|---|---|---|---|
| 1. Sign in | NavBar "Sign In" button → Netlify modal | Clear | No explanation of why sign-in is needed |
| 2. Navigate to Crypto | NavBar link | Clear | No redirect after login — user must manually navigate |
| 3. Configure exchanges/symbols | Parameters checkboxes | Moderate | No explanation of what these settings do |
| 4. Configure indicators | Indicators checkboxes | Moderate | No explanation of what each indicator does |
| 5. Click "Set bot parameters" | Button | Unclear | No success/failure feedback after click |
| 6. Click "Set bot indicators" | Button | Unclear | No success/failure feedback after click |

After login, the user is left on whatever page they were on — there is no redirect to `/crypto`. A new user who signs in from the Home page must know to click "Crypto" in the nav.

### Workflow 2: Creating and Running a Bot

| Step | UI Element | Clarity | Issues |
|---|---|---|---|
| 1. Click "Create New Bot" | Button in Bots panel | Clear | Button disabled state logic is inverted (see below) |
| 2. Wait for bot creation | Log console | Moderate | No spinner; user watches raw log text |
| 3. Bot auto-runs | Automatic | Unclear | No visual confirmation that bot is running |
| 4. Monitor activity | Log console | Poor | Raw log text with no formatting, filtering, or highlighting |
| 5. View order/trade history | Tables below console | Moderate | Tables appear only after first order/trade |

**Button disabled logic issue:**

```jsx
<button
    onClick={handleCreateButtonClick}
    disabled={botState !== BotState.REMOVED}  // disabled when NOT removed
>
    Create New Bot
</button>
```

`BotState.REMOVED = 1` is the initial state. `botState !== BotState.REMOVED` is `false` initially, so the button starts **enabled** — correct. But `BotState.CREATED = 0`, and the button is never set to `CREATED` after bot creation — `setBotState` is only called on `BOT_REMOVED_MESSAGE`. This means the "Create New Bot" button remains enabled even while a bot is running, allowing duplicate bot creation.

### Workflow 3: Removing a Bot

| Step | UI Element | Clarity | Issues |
|---|---|---|---|
| 1. Select bot from dropdown | `<select>` | Clear | |
| 2. Click "Remove Bot {id}" | Button | Clear | **No confirmation dialog** — removal is immediate and irreversible |
| 3. Bot removed | Log console | Poor | Only visible in raw log text |

Removing a running bot with no confirmation dialog is a significant UX risk in a trading application. A misclick stops a live trading bot with no undo.

### Workflow 4: Viewing Trade History

| Step | UI Element | Clarity | Issues |
|---|---|---|---|
| 1. Navigate to Crypto | NavBar | Clear | |
| 2. Scroll down past console | Page scroll | Poor | Tables are below the log console — not visible without scrolling |
| 3. View order/trade tables | HTML tables | Moderate | 13 columns overflow on non-wide screens; no sorting, filtering, or pagination |

---

## 3. Form Design & Input Validation

### Parameters Form

```jsx
<form>
    <div className="checkbox-group label">
        <h3>Exchanges</h3>
        <ul>{this.renderCheckboxes("exchanges")}</ul>
        <h3>Symbols</h3>
        <ul>{this.renderCheckboxes("symbols")}</ul>
        <button type="button" onClick={this.handleSetClick}>
            Set bot parameters
        </button>
    </div>
</form>
```

| Aspect | Status |
|---|---|
| Labels | Each checkbox has a `<label>` wrapping the input ✓ |
| Required fields | None marked — all checkboxes are optional |
| Validation | None — user can click "Set" with nothing selected |
| Error messages | None |
| Success feedback | None — button click fires silently |
| Default values | Loaded from server/localStorage/JSON ✓ |
| Disabled during submit | No — button remains clickable during async POST |

The same gaps apply identically to the Indicators form.

### Missing Feedback Pattern

Every action in the app fires silently. The user has no way to know if "Set bot parameters" succeeded or failed:

```js
// Parameters.js handleSetClick — current
handleSetClick = async () => {
    try {
        await updateParameters(clientId, this.state);
        console.log("Successfully updated parameters on the server.");  // invisible to user
    } catch (e) {
        console.log("Failed to update parameters on the server: " + e.message);  // invisible to user
    }
};
```

Minimum fix — add visual feedback:
```js
this.setState({ saveStatus: 'saving' });
try {
    await updateParameters(clientId, this.state);
    this.setState({ saveStatus: 'saved' });
    setTimeout(() => this.setState({ saveStatus: null }), 3000);
} catch (e) {
    this.setState({ saveStatus: 'error', saveError: e.message });
}
```

---

## 4. Error Handling & User Feedback

### Current State — Complete Absence of User Feedback

| Event | Current User Experience | Expected |
|---|---|---|
| Server unreachable on load | Checkboxes appear empty, no message | "Could not load settings — using defaults" |
| "Set parameters" POST fails | Nothing visible | Error banner: "Failed to save — try again" |
| "Set indicators" POST fails | Nothing visible | Error banner: "Failed to save — try again" |
| Bot creation fails | Nothing visible (log may show error) | Error message in UI |
| WebSocket disconnects | Nothing visible | "Disconnected — reconnecting..." banner |
| Order fetch fails | Table stays empty | "Could not load order history" |
| Trade fetch fails | Table stays empty | "Could not load trade history" |
| CoinGecko API fails | Ticker banner is empty | Ticker shows "Price data unavailable" |

The only user-visible loading state in the entire app is `<div>Loading...</div>` in `Bots.js` during the initial bot ID fetch. Everything else fails silently.

### No Toast / Notification System

There is no notification infrastructure. No toast library, no alert component, no status banner. Every action result is invisible to the user unless they open browser DevTools.

### No Confirmation Dialogs

Destructive actions have no confirmation:
- "Remove Bot" — immediately stops and removes a running trading bot
- "Set bot parameters" — immediately changes live trading configuration

---

## 5. Responsiveness & Mobile Design

### Viewport Configuration

```html
<meta name="viewport" content="width=device-width, initial-scale=1" />
```
Correct. ✓

### Responsive Breakpoints

`styles.css` and `navbar.css` implement breakpoints for mobile (360px+), tablet (768px+), and desktop (1366px+). Typography scales correctly across breakpoints.

### Critical Responsive Failures

**13-column trading tables — no responsive handling:**

```jsx
<table className="tradehistory-table">
    <thead>
        <tr>
            <th>Index</th><th>Time</th><th>Position</th><th>Symbol</th>
            <th>Amount</th><th>Buy Exchange</th><th>Price</th><th>Value</th>
            <th>Sell Exchange</th><th>Price</th><th>Value</th>
            <th>Profit</th><th>Profit Perc</th>
        </tr>
    </thead>
```

`bots.css` sets `.tables-container { max-height: 200px; overflow-y: auto; }` but no `overflow-x: auto`. On screens narrower than ~1200px, the table overflows the viewport with no horizontal scroll, breaking the page layout.

**Fix:**
```css
.tables-container {
    width: 100%;
    max-height: 200px;
    overflow-y: auto;
    overflow-x: auto;  /* add this */
}
```

**Crypto page layout — no column stacking on mobile:**

```css
/* crypto.css */
.crypto {
    display: flex;
    width: 100%;
    padding: 10px;
    /* no flex-direction: column for mobile */
}
```

`styles.css` has a media query `@media (min-width: 360px) and (max-width: 639px) { .crypto { flex-direction: column; } }` but this only applies within that specific range. The Parameters and Bots panels sit side-by-side on all other screen sizes, including tablets where they may be too narrow.

**Log console — fixed height:**

```css
.console {
    height: 300px;
    overflow-y: auto;
}
```

Fixed pixel height works on desktop but wastes screen space on mobile where 300px is a large portion of the viewport.

---

## 6. Accessibility (WCAG)

### Heading Hierarchy — Broken

The heading structure is semantically incorrect throughout:

```
<h1> SonarFT (NavBar logo link)
<h1> Crypto (NavBar link)
<h1> CryptoChatGPT (NavBar link)
<h1> Doggy (NavBar link)
  <h2> Bots (paper trading)
  <h2> Order History
  <h2> Trade History
  <h2> Parameters
  <h2> Indicators
```

Multiple `<h1>` elements on a single page confuse screen readers. Navigation links should use `<span>` or `<a>` with appropriate styling, not heading tags. The page should have exactly one `<h1>` identifying the page content.

### Missing ARIA Labels

| Element | Issue |
|---|---|
| NavBar logo `<img>` | Has `alt="SonarFT"` ✓ |
| "Create New Bot" button | No `aria-label`; button text is clear ✓ |
| "Remove Bot" button | Text includes bot ID — acceptable ✓ |
| Bot selector `<select>` | No `<label>` associated — screen readers cannot identify it |
| Log `<pre>` console | No `aria-label` or `role` — screen readers read entire log content |
| History tables | No `<caption>` elements |
| Checkbox groups | `<h3>` used as group label but not associated via `aria-labelledby` |

### Color Contrast

The design uses `--textSecondary: #142850` (dark blue) on `--backgroundTertiary: #e0e0e0` (light grey) for the main content area. Contrast ratio ≈ 8.5:1 — passes WCAG AA ✓.

NavBar uses `--textPrimary: #dae1e7` on `--backgroundPrimary: #000814`. Contrast ratio ≈ 14:1 — passes WCAG AAA ✓.

Button: `--buttonText: #000814` on `--buttonBackground: #75a0fc`. Contrast ratio ≈ 4.8:1 — passes WCAG AA ✓.

### Font Size

```css
/* styles.css */
* {
    font-size: small;  /* overrides browser default of 16px */
}
```

Setting `font-size: small` globally reduces all text to approximately 13px. WCAG 1.4.4 requires text to be resizable up to 200% without loss of content. The `small` keyword is relative to the parent, creating unpredictable cascading. This should be replaced with a base `rem` size:

```css
html { font-size: 16px; }
body { font-size: 1rem; }
```

### Keyboard Navigation

- All interactive elements (buttons, checkboxes, links, select) are natively keyboard-accessible ✓
- No custom focus styles defined — browser defaults apply (visible in most browsers)
- No skip-to-content link for keyboard users to bypass the navbar
- Tab order follows DOM order — acceptable

### Semantic HTML Issues

| Element | Used As | Should Be |
|---|---|---|
| `<h1>` in NavBar links | Navigation labels | `<span>` or styled `<a>` |
| `<ul>` in Bots `<h2>` | Button container | `<div>` or `<nav>` |
| `<ul>` wrapping `<pre>` | Log container | `<div>` |
| `<main>` nested inside `<main>` | Layout | Only one `<main>` per page |

`Crypto.js` renders `<section><main>`, and `Home.js` renders `<main><main>` — nested `<main>` elements are invalid HTML.

---

## 7. Trading-Specific UX Patterns

### Price Display

- **CoinGecko ticker:** Scrolling banner shows top-20 coin prices, updated every 3 minutes. No indication of data age or last-updated timestamp.
- **Live exchange prices:** ⚠️ Not Found in Source Code — no real-time price feed from the trading exchanges. The bot operates on exchange prices internally, but the UI shows no current bid/ask prices.

### Order Confirmation

⚠️ Not Found in Source Code. The bot executes trades automatically — there is no manual order entry UI. However, bot creation and removal have no confirmation dialogs (see §2).

### Risk Warnings

⚠️ Not Found in Source Code. No warnings for:
- Switching from paper trading to live trading
- Removing a running bot
- Changing parameters on a running bot
- Low balance conditions

The Bots panel heading includes `<span>(paper trading)</span>` — this is the only indication of trading mode, and it is hardcoded text, not a dynamic indicator.

### Bot Status Indicator

⚠️ Not Found in Source Code. There is no visual indicator showing whether a bot is currently running, stopped, or in an error state. The user must read the raw log console to infer bot status.

### Performance Metrics

⚠️ Not Found in Source Code. No P&L summary, win rate, average profit per trade, or any aggregate performance metric is displayed. The order/trade history tables show raw data but no computed analytics.

### Paper vs Live Trading Mode

The mode is controlled by `is_simulating_trade` in the server-side config. The UI has no toggle for this — it is hardcoded as `(paper trading)` in the Bots heading. Users cannot switch modes from the UI.

---

## 8. Data Visualization

⚠️ Not Found in Source Code. No charts, graphs, or visualizations of any kind exist in the codebase. No charting library is installed (`package.json` has no Chart.js, Recharts, D3, TradingView, etc.).

The trading history is presented as raw HTML tables only. For a trading application, the absence of any price charts, P&L curves, or indicator visualizations is a significant UX gap.

---

## 9. Loading & Empty States

| Component | Loading State | Empty State | Error State |
|---|---|---|---|
| `Bots.js` — bot IDs | `<div>Loading...</div>` ✓ | Bot selector renders empty with no message | None |
| `Bots.js` — log console | None | Empty `<pre>` with no message | None |
| `Bots.js` — order table | None | Empty `<tbody>` with no message | None |
| `Bots.js` — trade table | None | Empty `<tbody>` with no message | None |
| `Parameters.js` | None | Checkboxes render empty | None |
| `Indicators.js` | None | Checkboxes render empty | None |
| `CryptoTicker.js` | None | Empty banner | None |

Empty tables with no message leave users wondering if data hasn't loaded yet or if there genuinely are no records. A simple empty state message ("No orders yet — create a bot to start trading") would significantly improve clarity.

---

## 10. Help & Documentation

⚠️ Not Found in Source Code. There is no:
- Inline help text or tooltips on any UI element
- Explanation of what each indicator does
- Explanation of what each trading parameter controls
- Onboarding flow for new users
- Link to documentation
- FAQ or help section

A new user arriving at the Crypto page sees three panels of unlabeled checkboxes and a bot console with no guidance on what to do or what the settings mean.

---

## 11. Perceived Performance

| Aspect | Status | Notes |
|---|---|---|
| Initial page load | Fast — static React bundle | CRA build is well-optimized |
| Parameters/Indicators load | Slight flash | localStorage hydration shows stale data briefly before server response |
| Bot creation feedback | Delayed | User watches log text; no progress indicator |
| Order/trade table refresh | Noticeable delay | Sequential REST fetches after WS event |
| CryptoTicker animation | Smooth | CSS animation at 270s duration — very slow scroll |
| Log console scroll | Smooth | `scrollIntoView` works correctly |
| No optimistic updates | — | All UI updates wait for server confirmation |

The CryptoTicker scroll animation duration of 270 seconds (4.5 minutes) for a full cycle means prices scroll very slowly. With 20 coins × 2 (original + clone), the inner div is wide but moves imperceptibly.

---

## 12. Consistency & Design System

### Strengths

- CSS custom properties in `variables.css` provide a consistent color palette ✓
- Button hover transitions (`transition: all 0.3s ease`) are consistent across components ✓
- Dark theme is applied consistently across all pages ✓
- Border radius and border color are consistent ✓

### Inconsistencies

| Element | Inconsistency |
|---|---|
| Button styling | Defined separately in `crypto.css`, `parameters.css`, `indicators.css`, `navbar.css` — minor variations |
| `<h2>` usage | Used as section headers in Bots, as form group labels in Parameters/Indicators |
| Loading text | Only `Bots.js` has loading state; no consistent loading component |
| Error handling | No consistent pattern — each component handles (or ignores) errors differently |
| `PrivateRoute` | Defined 4 times with identical code |
| `.outer-container` | Defined in both `welcome.css` and `building.css` with identical styles — CSS duplication |

---

## 13. Internationalization (i18n)

⚠️ Not Found in Source Code. No i18n library (react-i18next, react-intl, etc.) is installed. All strings are hardcoded in English. Numbers and currencies are not locale-formatted — prices from CoinGecko are displayed as raw JavaScript numbers (e.g., `$43521.23456789`).

---

## 14. Specific Trading UI Elements

| Element | Status | Quality |
|---|---|---|
| Bot creation | Button → WebSocket command | Minimal — no config options at creation time |
| Bot removal | Button → WebSocket command | No confirmation dialog |
| Bot selector | `<select>` dropdown | Functional but no bot status shown |
| Indicator configuration | Checkbox list | No descriptions, no visual grouping by type |
| Parameter configuration | Checkbox list | No descriptions, no validation |
| Paper vs live mode | Hardcoded label only | Cannot be changed from UI |
| Stop-loss / take-profit | ⚠️ Not Found | Not implemented in UI |
| Strategy selection | ⚠️ Not Found | Not implemented in UI |
| Account balance | ⚠️ Not Found | Not displayed |
| Execution status | Log text only | No structured status display |

---

## 15. Usability Issues Summary

| # | Issue | Severity | Description | Fix |
|---|---|---|---|---|
| 1 | No feedback on any user action | High | "Set parameters", "Set indicators", bot create/remove all fire silently | Add success/error state + visual feedback to every action |
| 2 | No confirmation on bot removal | High | Misclick stops a running trading bot with no undo | Add confirmation dialog before remove |
| 3 | 13-column tables overflow on mobile/tablet | High | No `overflow-x: auto` on table container | Add horizontal scroll wrapper |
| 4 | No WebSocket connection status indicator | High | User cannot tell if bot communication is live | Show connection badge using `wsOpen` state |
| 5 | No error messages anywhere | High | All failures are invisible to the user | Add error state + UI feedback in all components |
| 6 | `<h1>` used for nav links | Medium | Breaks heading hierarchy; confuses screen readers | Replace with styled `<span>` or `<a>` |
| 7 | `font-size: small` global override | Medium | Reduces all text below browser default; accessibility concern | Use `rem`-based sizing from `html { font-size: 16px }` |
| 8 | No active nav link indicator | Medium | User cannot tell which page they are on | Add `aria-current="page"` and active CSS class |
| 9 | No redirect to /crypto after login | Medium | New users must manually navigate after signing in | Redirect to `/crypto` on successful login |
| 10 | Bot status not shown in UI | Medium | No visual indicator of running/stopped/error state | Add status badge to bot selector |
| 11 | Empty tables show nothing | Medium | User cannot distinguish "no data" from "loading" | Add empty state messages to all tables |
| 12 | No data visualization | Medium | No charts, P&L curves, or indicator graphs | Add charting library (Recharts recommended) |
| 13 | Bot selector `<select>` has no label | Medium | Screen readers cannot identify the control | Add `<label htmlFor="bot-select">Active Bot</label>` |
| 14 | Nested `<main>` elements | Low | Invalid HTML — `Crypto.js` and `Home.js` nest `<main>` | Replace inner `<main>` with `<div>` or `<section>` |
| 15 | No tooltips on indicators/parameters | Low | Users don't know what RSI, MACD, StochRSI mean | Add `title` attributes or tooltip components |
| 16 | CryptoTicker scroll too slow (270s) | Low | Prices barely move | Reduce to 60–90s for visible scrolling |
| 17 | `DoggyWelcome` renders empty section | Low | Empty `<section>` with no content | Add content or remove the route |
| 18 | No onboarding for new users | Low | No guidance on first use | Add a simple welcome/setup guide |

---

**Save location:** `docs/ux/trading-interface.md`  
**Next prompts:** `08-performance-optimization.md`, `09-testing-quality.md`
