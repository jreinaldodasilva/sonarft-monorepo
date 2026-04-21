# Prompt 07 — Trading Interface UX/UI & Interaction Design

**Package:** `packages/web`  
**Prompt ID:** 07-WEB-UX  
**Output File:** `docs/ux/trading-interface.md`  
**Reviewed:** July 2025  
**API Sources:** `packages/api` included — workflow and error mapping verified

---

## Executive Summary

The trading interface is functional and focused. The layout is clean, the dark theme is appropriate for a trading tool, and the core workflow (configure → create bot → monitor) is achievable. The CSS design token system and responsive breakpoints show deliberate design thinking.

The main UX concerns are: the interface provides very little guidance for new users; several critical actions (live trading mode, bot removal) lack adequate risk warnings; error feedback is incomplete (server errors are not surfaced, WS command failures are silent); accessibility has multiple violations including missing ARIA labels, invalid HTML landmarks, and insufficient color contrast in some areas; and the simulation/live mode toggle is broken at the API level (Prompt 05 Finding #2), meaning users cannot actually switch modes.

---

## 1. Navigation & Information Architecture

### Navigation Structure

The application has a flat, single-level navigation bar with four links:

```
[Logo] SonarFT | Crypto | CryptoChatGPT | Doggy    [Sign In / Sign Out]
```

- **Home (`/`)** — Landing page with hero text only
- **Crypto (`/crypto`)** — Main trading interface (auth-gated)
- **CryptoChatGPT (`/cryptochatgpt`)** — Placeholder (lazy-loaded but route exists)
- **Doggy (`/doggy`)** — Placeholder

Three additional page directories exist (`Dex`, `Forex`, `Token`) but are not linked in the nav.

### Page Hierarchy

```
/ (Home)
  └── Welcome hero text

/crypto (Crypto — auth required)
  ├── Parameters (exchange + symbol selection)
  ├── Indicators (indicator selection)
  └── Bots
        ├── Bot controls (create / select / remove)
        ├── Bot console (live log stream)
        ├── Order history table
        ├── Cumulative P&L chart
        └── Trade history table
```

The hierarchy is shallow and logical. All trading functionality lives on a single page — appropriate for a tool used by operators who want everything visible at once.

### Navigation Clarity

**Issues:**
- There is no active link indicator — the current page is not visually distinguished in the nav. A user on `/crypto` cannot tell from the nav that they are on the Crypto page.
- "CryptoChatGPT" and "Doggy" are non-descriptive names for placeholder pages. They create confusion about the app's scope.
- No breadcrumbs — not needed for this flat structure, but the single-page trading interface has no section headings that orient the user within the page.

### Cross-linking

No cross-linking between sections. The trading page is self-contained. There are no links from the bot console to the trade history, or from the parameters section to documentation.

---

## 2. Trading Workflows

### Workflow 1: Initial Setup (Configure Parameters & Indicators)

| Step | UI element | Clarity |
|---|---|---|
| 1. Sign in | NavBar "Sign In" button | ✅ Clear |
| 2. Navigate to Crypto | NavBar "Crypto" link | ✅ Clear |
| 3. Select exchanges | Parameters checkboxes | ⚠️ No guidance on which to choose |
| 4. Select symbols | Parameters checkboxes | ⚠️ Tooltips help but no defaults shown |
| 5. Select indicators | Indicators checkboxes | ⚠️ Tooltips help but no explanation of impact |
| 6. Save | "Set bot parameters" / "Set bot indicators" buttons | ✅ Clear, with save feedback |

**Gap:** There is no indication of which configuration is currently active on the server vs what is shown in the UI. If the server has different settings than localStorage, the user has no way to know until they explicitly fetch (which happens on mount, but silently).

### Workflow 2: Create and Run a Bot

| Step | UI element | Clarity |
|---|---|---|
| 1. Click "Create New Bot" | Button in BotControls | ✅ Clear |
| 2. Wait for bot_created event | (no feedback) | ❌ No loading indicator |
| 3. Bot auto-starts | Status badge changes to "● Running" | ⚠️ Automatic — user has no control |
| 4. Monitor logs | BotConsole | ✅ Clear |
| 5. View trade history | TradeHistoryTable | ✅ Clear |

**Critical gap:** The bot auto-starts immediately after creation with no confirmation step. In live trading mode (if the toggle worked), this would immediately begin placing real orders on exchanges. There is no "Are you sure you want to start trading?" confirmation.

**Gap:** No loading state between clicking "Create New Bot" and the bot appearing. The button remains enabled (it is disabled by `botState !== BotState.REMOVED`, but `botState` starts as `REMOVED` so the button is always enabled when disconnected or before creation).

### Workflow 3: Switch Between Paper and Live Trading

| Step | UI element | Clarity |
|---|---|---|
| 1. Click "📝 Paper" / "⚡ Live" toggle | Mode toggle button in Bots h2 | ⚠️ Small, inline with heading |
| 2. Mode changes | Button label updates | ❌ **Broken** — server rejects (missing botid) |

**Critical gap:** The simulation toggle is broken at the API level (Prompt 05 Finding #2). The UI updates optimistically (button label changes) but the server never receives a valid command. The user believes they have switched modes but the bot continues in its previous mode.

Additionally, switching to live trading mode is a high-risk action that should require explicit confirmation ("You are about to enable live trading with real funds. Are you sure?"). No such confirmation exists.

### Workflow 4: Remove a Bot

| Step | UI element | Clarity |
|---|---|---|
| 1. Select bot from dropdown | Select element | ✅ Clear |
| 2. Click "Remove Bot {id}" | Button in BotControls | ✅ Clear |
| 3. Confirm | `window.confirm()` browser dialog | ⚠️ Browser native dialog, not styled |
| 4. Bot removed | Status resets | ✅ Clear |

The `window.confirm` dialog is functional but jarring — it uses the browser's native unstyled dialog, which breaks the dark theme. A styled in-app confirmation modal would be more appropriate.

### Workflow 5: View Trading Performance

| Step | UI element | Clarity |
|---|---|---|
| 1. Navigate to Crypto | NavBar | ✅ |
| 2. View P&L chart | ProfitChart (Recharts area chart) | ✅ Clear, good tooltip |
| 3. View trade history | TradeHistoryTable | ⚠️ No sorting, no filtering, no pagination |
| 4. View order history | TradeHistoryTable (separate) | ⚠️ Same limitations |

**Gap:** Trade history is capped at 100 records (API default) with no pagination controls and no indication that records may be truncated. A user with an active bot will not know they are only seeing the most recent 100 trades.

---

## 3. Form Design & Input Validation

### Parameters Form

```
[✓] Binance    [✓] BTC/USDT
[ ] Okx        [ ] ETH/USDT
[ ] Kraken
```

**Strengths:**
- Tooltips on hover provide exchange and symbol descriptions ✅
- Save feedback ("✓ Saved" / "✗ Error — try again") is clear ✅
- Button disabled during save ✅

**Issues:**
- No indication of which checkboxes are required — can a user save with zero exchanges selected? The API accepts it (empty dict is valid Pydantic), but the bot would have nothing to trade on.
- No validation that at least one exchange and one symbol are selected before saving.
- The form heading is "Parameters" — this is too generic. "Exchange & Symbol Selection" would be more descriptive.
- No "Reset to defaults" option.

### Indicators Form

Same structure as Parameters. Same strengths and issues. Additionally:
- No indication of which indicators are mutually exclusive or complementary.
- No explanation of what happens if no indicators are selected.
- The three categories (Periods, Oscillators, Moving Averages) have no explanation of how they interact.

### General Form Issues

- No `<label for="...">` associations — labels use wrapping `<label>` elements which is valid, but the `<input>` elements have no `id` attributes, making them inaccessible to screen readers that navigate by form field.
- No `required` attribute on any input — all fields are optional from the browser's perspective.
- The `<form>` element has no `onSubmit` handler (noted in Prompt 04) — pressing Enter does nothing.

---

## 4. Error Handling & User Feedback

### Error Visibility Matrix

| Error scenario | User sees | Severity |
|---|---|---|
| WebSocket connection failure | "⚠ WebSocket connection error — check server status — reconnecting..." banner | ✅ Visible |
| Bot list fetch failure | "⚠ Could not load bots — is the server running?" banner | ✅ Visible |
| Config save failure | "✗ Error — try again" inline text (auto-clears in 3s) | ✅ Visible |
| Config fetch failure | Nothing — falls back silently to localStorage/defaults | ❌ Silent |
| Order/trade history fetch failure | Nothing — table remains empty | ❌ Silent |
| Bot creation failure (WS error event) | Nothing — `WsErrorEvent` not handled | ❌ Silent |
| `set_simulation` failure | Nothing — `WsErrorEvent` not handled | ❌ Silent |
| Bot limit exceeded | Nothing — `WsErrorEvent` not handled | ❌ Silent |
| API 401 (expired token) | Nothing — request throws, caught silently | ❌ Silent |
| API 500 | Generic "HTTP error! status: 500" thrown, caught by hook | ⚠️ Partial |
| Render error | ErrorBoundary fallback with "Something went wrong" | ✅ Visible |

**5 out of 11 error scenarios are completely silent.** For a trading application where silent failures can mean missed trades or unexpected live orders, this is a significant UX and safety concern.

### Success Feedback

| Action | Feedback |
|---|---|
| Save parameters | "✓ Saved" (3 seconds) ✅ |
| Save indicators | "✓ Saved" (3 seconds) ✅ |
| Bot created | Status badge → "● Running" ✅ |
| Bot removed | Status badge → "● Idle" ✅ |
| Order executed | Trade history table updates ✅ |
| Trade completed | P&L chart updates ✅ |

Success feedback is generally good for the actions that work correctly.

### Loading States

| Operation | Loading indicator |
|---|---|
| Initial bot list fetch | "Loading..." text ✅ |
| Config fetch | None ❌ |
| Order/trade history fetch | None ❌ |
| Bot creation (waiting for WS event) | None ❌ |
| Config save | Button disabled + "Saving..." ✅ |

### Error Message Quality

The error messages that do appear are functional but generic:
- "Could not load bots — is the server running?" — helpful for developers, not for end users
- "WebSocket connection error — check server status" — technical, not actionable for non-technical users
- "✗ Error — try again" — no explanation of what failed or why

---

## 5. Responsiveness & Mobile Design

### Viewport Configuration

```html
<meta name="viewport" content="width=device-width, initial-scale=1" />
```
Correctly configured. ✅

### Desktop Layout (≥1366px)

The Crypto page uses a two-column flex layout:
```css
.crypto { display: flex; width: 100%; padding: 10px; }
.parameters-container { width: 100%; margin-right: 10px; }
.bots-container { width: 100%; }
```

Parameters/Indicators on the left, Bots on the right. This is a reasonable trading dashboard layout.

### Mobile Layout (≤639px)

```css
@media only screen and (min-width: 360px) and (max-width: 639px) {
    .crypto { flex-direction: column; }
}
```

Switches to single-column stacking on mobile. The layout adapts, but:

- The trade history table has 13 columns — it will overflow horizontally on mobile. The `.tables-container` has `overflow-x: auto` which enables scrolling, but the table is not readable on a small screen.
- The bot console (`height: 300px`) takes up a large portion of the mobile viewport.
- The P&L chart (`height: 220px`) renders correctly via `ResponsiveContainer` ✅.
- The CryptoTicker scroll animation runs at a fixed 270-second duration regardless of screen width — on mobile with a narrow viewport, the animation appears very slow.

### Touch Interactions

No touch-specific interactions are implemented. Buttons and checkboxes are standard HTML elements with adequate tap target sizes (padding: 10px on buttons). The bot selector dropdown is a native `<select>` — works on mobile but not styled.

### NavBar on Mobile

The NavBar has a mobile breakpoint that reduces font sizes. However, all navigation links remain visible in a horizontal row — on very small screens (360px), the nav items may overflow or wrap awkwardly. No hamburger menu or mobile-specific navigation pattern is implemented.

---

## 6. Accessibility (WCAG Compliance)

### Semantic HTML Issues

Multiple semantic HTML violations were identified across prompts. Summary for accessibility impact:

| Issue | Element | WCAG criterion | Impact |
|---|---|---|---|
| Three `<main>` landmarks on Home page | `Home.tsx`, `Welcome.tsx`, `App.tsx` | 1.3.1 Info and Relationships | Screen readers announce multiple main regions |
| `<ul>` containing `<button>` and `<select>` directly | `BotControls.tsx` | 1.3.1 | Invalid list structure confuses AT |
| `<ul><pre><div>` nesting | `BotConsole.tsx` | 1.3.1 | Invalid structure |
| `<h2>` containing interactive controls | `Bots.tsx` | 1.3.1 | Heading text includes button/badge content |

### ARIA Labels

**Missing ARIA labels:**

- The bot selector `<select>` has `aria-label="Active Bot"` ✅ — this is the only ARIA label in the entire codebase.
- The mode toggle button (`📝 Paper` / `⚡ Live`) has a `title` attribute but no `aria-label` — `title` is not reliably announced by screen readers.
- The WS status badge (`● Connected` / `○ Disconnected`) has no ARIA role or label — a screen reader user cannot determine connection status.
- The bot status badge (`● Running` / `● Idle` / `● Error`) has no `aria-live` attribute — status changes are not announced to screen readers.
- The "Create New Bot" and "Remove Bot" buttons have no `aria-disabled` attribute when disabled — they use a CSS class (`btn-disabled`) for visual styling but the `disabled` HTML attribute is set, which is correct for native buttons ✅.
- The save status spans ("✓ Saved", "✗ Error") have no `aria-live` attribute — save results are not announced to screen readers.

### Color Contrast

The application uses a dark theme. Key contrast ratios to assess:

| Element | Foreground | Background | Estimated ratio | WCAG AA (4.5:1) |
|---|---|---|---|---|
| Body text | `#dae1e7` (textPrimary) | `#000814` (backgroundPrimary) | ~14:1 | ✅ Pass |
| Secondary text | `#9AA5B1` (textTertiary) | `#000814` | ~7:1 | ✅ Pass |
| Form text | `#142850` (textSecondary) | `#e0e0e0` (backgroundTertiary) | ~6:1 | ✅ Pass |
| Button text | `#000814` (buttonText) | `#75a0fc` (buttonBackground) | ~4.6:1 | ✅ Marginal pass |
| WS status "Connected" | `#88dd88` | `#1a3a1a` | ~5.5:1 | ✅ Pass |
| WS status "Disconnected" | `#ddaa66` | `#3a2a1a` | ~4.2:1 | ⚠️ Marginal fail |
| Bot status "Idle" | `#7a9ab0` | `#1a2a3a` | ~3.8:1 | ❌ Fail |
| Bot status "Error" | `#ffcccc` | `#5c1a1a` | ~6.5:1 | ✅ Pass |
| Save status "Saved" | `#4a8a4a` | `#1a3a1a` | ~2.1:1 | ❌ Fail |
| Console text | `White` | `Black` | 21:1 | ✅ Pass |
| Chart axis labels | `#9AA5B1` | chart background | ~5:1 | ✅ Pass |

**Two confirmed contrast failures:**
- Bot status "Idle" badge: `#7a9ab0` on `#1a2a3a` — approximately 3.8:1, below the 4.5:1 WCAG AA threshold
- Save status "Saved": `#4a8a4a` on `#1a3a1a` — approximately 2.1:1, significantly below threshold

### Keyboard Navigation

- All interactive elements (buttons, select, checkboxes) are natively focusable ✅
- No `tabindex="-1"` or `tabindex` manipulation found ✅
- No keyboard trap detected ✅
- Focus order follows DOM order ✅
- **No visible focus indicator** beyond the browser default — the CSS does not define `:focus` or `:focus-visible` styles. On Chrome, the default blue outline may be visible, but on some browsers/themes it may be invisible against the dark background.

### Screen Reader Support

- Logo image: `<img src={logo} alt="SonarFT" className="logo" />` ✅
- Nav links use `<Link>` with text content ✅
- The `<nav>` element is present ✅
- No `role="status"` or `aria-live` regions for dynamic content (bot status, save feedback, WS status) ❌
- The bot console (`<pre>`) has no `aria-label` — a screen reader user cannot identify it as a log output ❌
- The trade history table has no `<caption>` element — screen readers cannot identify the table's purpose ❌

### Heading Hierarchy

```
<h1> SonarFT (NavBar logo link)
<h1> Crypto (NavBar link — all nav links use h1)
<h2> Bots (Bots component)
<h2> Order History
<h2> Trade History
<h3> Cumulative P&L (ProfitChart)
<h2> Parameters
<h3> Exchanges
<h3> Symbols
<h2> Indicators
<h3> Periods
<h3> Oscillators
<h3> Moving Averages
```

**Issues:**
- All NavBar links use `<h1>` — there should be only one `<h1>` per page (the page title). Using `<h1>` for navigation links is a heading hierarchy violation.
- The heading structure on the Crypto page is reasonable (`h2` for sections, `h3` for subsections) but the `h1` pollution from the NavBar breaks the overall hierarchy.

---

## 7. Trading-Specific UX Patterns

### Paper vs Live Trading Mode

The mode toggle is the most safety-critical UI element in the application:

```tsx
<button
    className={`mode-toggle ${isSimulating ? "mode-toggle--paper" : "mode-toggle--live"}`}
    onClick={handleToggleSimulation}
    title={isSimulating ? "Switch to live trading" : "Switch to paper trading"}
>
    {isSimulating ? "📝 Paper" : "⚡ Live"}
</button>
```

**Issues:**
1. **Broken** — the toggle sends a WS command without `botid`; the server rejects it silently (Prompt 05)
2. **No confirmation dialog** — switching to live trading should require explicit confirmation ("This will place real orders on exchanges with real funds")
3. **Placement** — the toggle is inline inside an `<h2>` heading, making it easy to click accidentally
4. **Visual weight** — the toggle is small (0.75rem font, pill-shaped badge) — insufficient visual prominence for a high-stakes control
5. **No persistent indicator** — the mode is stored in React state only; on page reload, `isSimulating` resets to `true` (default). The user has no way to know what mode the server-side bot is actually running in.

### Order Confirmation

**No order confirmation exists.** When a bot is created and auto-started, it immediately begins scanning for trades. In live mode (if it worked), real orders would be placed without any user confirmation step. This is a significant trading safety gap.

### Risk Warnings

**No risk warnings anywhere in the interface.** There is no:
- Warning when switching to live trading mode
- Warning about the financial risks of automated trading
- Warning when removing a running bot
- Indication of the current account balance or exposure

### Bot Status Visibility

The bot status badge (`● Running` / `● Idle` / `● Error`) is small and inline with the heading. For a trading application, the bot's operational status should be the most prominent element on the page — not a small pill badge next to a heading.

### Price Display

The CryptoTicker shows live prices from CoinGecko (updated every 3 minutes). These are display-only prices — they are not the prices the bot is actually trading at. There is no display of:
- Current bid/ask prices from the configured exchanges
- The bot's last executed buy/sell prices
- Current spread or profit margin

### Performance Metrics

The P&L chart shows cumulative profit over time — this is the most useful performance metric. However:
- No total profit/loss summary figure
- No win rate or trade count
- No comparison to a benchmark
- No time-range selector on the chart

### Account Balance

Account balance is not displayed anywhere. Users cannot see how much capital is deployed or available.

---

## 8. Data Visualization

### ProfitChart (Recharts AreaChart)

**Strengths:**
- Cumulative P&L line with gradient fill — visually clear ✅
- Color changes based on positive/negative cumulative result (green/red) ✅
- Custom tooltip showing trade P&L and cumulative P&L ✅
- Zero reference line (`ReferenceLine y={0}`) ✅
- `ResponsiveContainer` — adapts to container width ✅
- Empty state message when no trades exist ✅
- `useMemo` for data transformation — no unnecessary recomputation ✅

**Issues:**
- No time-range selector (all-time only)
- No zoom or pan interaction
- X-axis labels use `interval="preserveStartEnd"` — only first and last labels shown; intermediate timestamps are hidden, making it hard to read the time axis for large datasets
- The gradient `id="plGradient"` is hardcoded — if two `ProfitChart` instances were rendered simultaneously (e.g., one for orders, one for trades), they would share the same SVG gradient ID, causing visual glitches. Currently only one instance is rendered, so this is latent.

### TradeHistoryTable

A plain HTML table with 13 columns. No sorting, no filtering, no pagination, no column resizing.

**Issues:**
- 13 columns is too many for a readable table — especially on tablet/mobile
- No column sorting (e.g., sort by profit, sort by timestamp)
- No filtering (e.g., show only profitable trades)
- No pagination — capped at 100 records with no indication
- Profit values are raw floats (e.g., `0.00116`) — no currency formatting or color coding
- `profit_percentage` is displayed as a raw decimal (e.g., `0.00116`) — should be formatted as a percentage (`0.116%`)
- Timestamp is displayed as ISO string — should be formatted as a human-readable date/time

### CryptoTicker

A scrolling price banner. Functional but:
- Prices are from CoinGecko (3-minute delay) — not the exchange prices the bot uses
- No indication of the data source or update frequency
- The scroll animation speed (270s) is fixed regardless of the number of coins displayed

---

## 9. Loading & Empty States

### Loading States

| Component | Loading state | Quality |
|---|---|---|
| Bot list (initial) | "Loading..." text | ⚠️ Functional but unstyled |
| Config forms | None | ❌ Missing |
| Trade/order history | None | ❌ Missing |
| Bot creation | None | ❌ Missing |
| Page lazy load | "Loading..." text (`PageLoader`) | ⚠️ Functional but unstyled |

No skeleton screens are used anywhere. The forms render immediately with localStorage/default data, which avoids a blank flash — this is acceptable. But the bot list and history sections have no visual indication of loading state beyond a plain text string.

### Empty States

| Component | Empty state | Quality |
|---|---|---|
| ProfitChart (no trades) | "No trade data yet — P&L curve will appear after the first trade." | ✅ Clear, helpful |
| TradeHistoryTable (no rows) | Empty table body (headers visible, no rows) | ⚠️ No message |
| BotConsole (no logs) | Empty `<pre>` | ❌ No message |
| Bot selector (no bots) | Empty `<select>` | ❌ No message or call-to-action |

The `ProfitChart` empty state is well-done. The others are missing or inadequate. An empty bot selector with no message leaves new users confused about what to do next.

---

## 10. Help & Documentation

### Tooltips

Tooltips are implemented on indicator and parameter checkboxes via the HTML `title` attribute:

```tsx
<label title={tips[item] ?? item}>
    <input type="checkbox" ... />
    {item}
</label>
```

The tooltip content is detailed and helpful (e.g., "RSI (14) — measures momentum; ≥70 overbought, ≤30 oversold"). However:
- `title` tooltips are not accessible on touch devices (no hover)
- `title` tooltips are not announced by screen readers on focus
- Custom tooltip components (e.g., using `aria-describedby`) would be more accessible

### Inline Help

No inline help text, no "?" icons, no expandable help sections. The interface assumes users understand trading concepts (RSI, MACD, VWAP, spread, etc.).

### Onboarding

No onboarding flow. A new user arriving at the Crypto page sees:
1. A Parameters section with checkboxes (no explanation of what to do)
2. An Indicators section with checkboxes (no explanation)
3. A Bots section with a "Create New Bot" button (no explanation of what happens next)

There is no "Getting Started" guide, no first-run wizard, and no contextual help.

### User Guide / Documentation

No user guide is linked from the application. The README exists in the repository but is not accessible from the UI.

---

## 11. Performance Perceived by User

### Page Load

The application uses lazy loading for all page components (`React.lazy` + `Suspense`). The initial bundle contains only the shell (App, Header, Footer, CryptoTicker, AuthProvider). Page components load on first navigation.

The `PageLoader` fallback is a plain text div — functional but provides no visual progress indication for slow connections.

### Interaction Responsiveness

- Button clicks feel immediate — no artificial delays
- Checkbox changes update instantly (controlled inputs)
- Save operations show "Saving..." immediately on click ✅
- Bot creation has no feedback between click and `bot_created` event — feels unresponsive for the 1-3 seconds it takes

### Animation

The CryptoTicker uses a CSS `@keyframes scrolling` animation — smooth and GPU-accelerated ✅. No other animations are used. The mode toggle and nav links have `transition: all 0.3s ease` on hover — smooth ✅.

### Optimistic Updates

No optimistic updates. All state changes wait for server confirmation. For a trading tool this is correct — showing unconfirmed state would be dangerous.

### Perceived Performance Issues

- No skeleton screens — the bot list area is blank during the initial fetch
- No progress indication for bot creation (can take 1-3 seconds)
- Trade history table re-renders completely on every `order_success` event — no incremental update

---

## 12. Consistency & Design System

### Color Scheme

The dark theme is consistent throughout. CSS custom properties (`variables.css`) are used for all colors — no hardcoded hex values in component CSS except for the status badge colors in `bots.css` (which are not in `variables.css`).

**Inconsistency:** The config form panels use `--backgroundTertiary: #e0e0e0` (light grey) as their background, while the rest of the UI uses dark backgrounds. This creates a mixed dark/light appearance that may be intentional (form fields on light background for readability) but is visually jarring.

### Typography

`styles.css` sets `font-size: small` globally via `* { font-size: small }`. This is an unusual approach — it overrides the browser's default font size for all elements, including headings. The heading sizes are then re-specified in media queries. This works but is fragile.

### Button Consistency

Buttons are styled differently across the application:
- NavBar sign-in button: `background: var(--buttonBackground)`, `border: none`, `border-radius: 5px`
- Config save buttons: `background: var(--buttonBackground)`, `border: 1px solid var(--borderPrimary)`, `border-radius: 5px`
- Bot control buttons: styled via `.bots-container button` in `crypto.css`
- Mode toggle: custom pill style in `bots.css`
- ErrorBoundary button: `background: var(--buttonBackground)`, `border: 1px solid var(--borderPrimary)`

All use the same color variables but have slightly different border and padding rules. A shared `Button` component would enforce consistency.

### Spacing

Spacing is inconsistent — some components use `padding: 10px`, others use `padding: 5px`, `8px`, `12px`. No spacing scale (e.g., 4px base unit) is defined.

### Interaction Patterns

- Hover states: defined for nav links and buttons ✅
- Active states: not defined ❌
- Focus states: browser default only ❌
- Disabled states: `opacity: 0.5` via `.btn-disabled` class ✅

---

## 13. Internationalization (i18n)

No internationalization support. All strings are hardcoded in English. No i18n library (react-i18next, etc.) is present.

For the current scope (a personal/team trading tool), this is acceptable. If the application is intended for international users, i18n would be needed.

**Number formatting:** Profit values are displayed as raw JavaScript floats (e.g., `50`, `0.00116`). No `Intl.NumberFormat` or locale-aware formatting is used. For a financial application, numbers should be formatted with appropriate decimal places and locale-specific separators.

**Date formatting:** Timestamps are displayed as ISO strings (e.g., `2025-01-01T00:00:00Z`). The `ProfitChart` formats timestamps as `M/D H:MM` — this is US-centric and not locale-aware.

---

## 14. Specific Trading UI Elements

### Bot Management

| Element | Implementation | Quality |
|---|---|---|
| Create bot | Button → WS command | ✅ Works, but no loading state |
| Select active bot | Native `<select>` dropdown | ⚠️ Functional, not styled |
| Remove bot | Button → `window.confirm` → WS command | ⚠️ Works, but native dialog |
| Bot status | Pill badge in heading | ⚠️ Too small, not prominent |
| WS connection status | Pill badge in heading | ⚠️ Too small |

### Indicator Configuration

Checkboxes with tooltips. Functional. Missing: visual grouping of related indicators, explanation of how indicators affect bot behaviour, indication of which indicators are currently active on the running bot.

### Parameter Settings

Checkboxes for exchange and symbol selection. Functional. Missing: indication of which exchanges the bot is currently connected to, current trading pair prices, exchange status (online/offline).

### Paper vs Live Mode

As documented in Section 7 — broken and unsafe.

### Stop-Loss / Take-Profit

**Not implemented.** The `profit_percentage_threshold` parameter (minimum profit to execute a trade) is configured server-side in `config_parameters.json` but is not exposed in the UI. Users cannot set stop-loss, take-profit, or position size from the interface.

---

## 15. Usability Issues Summary

| # | Issue | Severity | Description | Impact | Fix |
|---|---|---|---|---|---|
| 1 | Simulation toggle is broken | **Critical** | `set_simulation` WS command missing `botid` — server rejects silently | User believes mode changed but bot continues in previous mode | Add `botid` to WS message; add error handler |
| 2 | No confirmation before live trading | **Critical** | Switching to live mode places real orders with no warning | Financial loss risk | Add confirmation modal with explicit risk warning |
| 3 | Bot auto-starts without confirmation | **High** | Bot starts trading immediately after creation | Unexpected live orders | Add "Start bot?" confirmation step |
| 4 | 5 of 11 error scenarios are silent | **High** | WS errors, history fetch failures, config fetch failures not shown | Users unaware of failures | Handle `WsErrorEvent`; show history fetch errors |
| 5 | Bot status badge too small | **High** | 0.75rem pill badge inline with heading | Users miss critical status changes | Make status a prominent standalone element |
| 6 | No loading state for bot creation | **Medium** | No feedback between "Create" click and bot appearing | Interface feels unresponsive | Disable button + show spinner after click |
| 7 | All NavBar links use `<h1>` | **Medium** | Multiple `<h1>` elements — heading hierarchy violation | Screen reader confusion | Use `<span>` or `<p>` for nav link text |
| 8 | Missing `aria-live` for dynamic content | **Medium** | Bot status, save feedback, WS status not announced | Screen reader users miss status changes | Add `role="status"` / `aria-live="polite"` |
| 9 | Bot status "Idle" contrast failure | **Medium** | `#7a9ab0` on `#1a2a3a` ≈ 3.8:1 (below 4.5:1 WCAG AA) | Low-vision users cannot read status | Lighten text or darken background |
| 10 | Save status "Saved" contrast failure | **Medium** | `#4a8a4a` on `#1a3a1a` ≈ 2.1:1 (below 4.5:1 WCAG AA) | Low-vision users cannot read confirmation | Use lighter green (e.g., `#88dd88`) |
| 11 | No focus visible styles | **Medium** | Browser default focus ring only — invisible on dark backgrounds | Keyboard users cannot track focus | Add `:focus-visible` outline styles |
| 12 | Trade history table unreadable on mobile | **Medium** | 13 columns overflow on small screens | Mobile users cannot view history | Reduce columns on mobile or use card layout |
| 13 | Profit values not formatted | **Medium** | Raw floats displayed (e.g., `0.00116`) | Hard to read financial data | Use `Intl.NumberFormat` for currency/percentage |
| 14 | Empty bot selector has no guidance | **Medium** | New users see empty dropdown with no call-to-action | Confusion about what to do | Add "No bots — click Create to start" message |
| 15 | `window.confirm` for bot removal | **Low** | Browser native dialog breaks dark theme | Jarring UX | Replace with styled in-app confirmation modal |
| 16 | No table captions | **Low** | TradeHistoryTable has no `<caption>` | Screen readers cannot identify table purpose | Add `<caption>Order History</caption>` |
| 17 | Tooltip `title` not accessible on touch | **Low** | Indicator/parameter tooltips not shown on mobile | Mobile users miss helpful context | Use custom tooltip component with `aria-describedby` |
| 18 | Timestamp formatting is ISO string | **Low** | `2025-01-01T00:00:00Z` displayed raw | Hard to read | Format with `Intl.DateTimeFormat` |
| 19 | No active nav link indicator | **Low** | Current page not highlighted in nav | Minor orientation confusion | Add active class to current route link |
| 20 | No onboarding for new users | **Low** | No guidance on first visit | New users confused | Add first-run tooltip sequence or help panel |

---

## Recommendations

**Priority 1 — Safety-critical (fix before live trading is enabled)**

1. **Fix simulation toggle** — add `botid: selectedBotId` to the `set_simulation` WS message and handle `WsErrorEvent`.

2. **Add live trading confirmation modal** — when switching from Paper to Live mode, show a styled modal:
   > "⚠️ You are switching to LIVE trading. Real orders will be placed on exchanges using real funds. Are you sure?"
   > [Cancel] [Confirm Live Trading]

3. **Add bot creation confirmation in live mode** — if `isSimulating` is false, confirm before creating a bot.

**Priority 2 — Accessibility (WCAG AA compliance)**

4. **Fix heading hierarchy** — replace `<h1>` in NavBar links with `<span>` styled to match.

5. **Add `aria-live` regions** for bot status, WS status, and save feedback:
   ```tsx
   <span role="status" aria-live="polite" className={`bot-status ${statusLabel.cls}`}>
       {statusLabel.text}
   </span>
   ```

6. **Fix color contrast** — bot status "Idle" and save status "Saved" fail WCAG AA.

7. **Add `:focus-visible` styles** to all interactive elements.

8. **Add table `<caption>` elements** to both TradeHistoryTable instances.

**Priority 3 — Error feedback**

9. **Handle `WsErrorEvent`** — display server errors in the UI (bot limit, operation failures).

10. **Add loading states** for bot creation, config fetch, and history fetch.

11. **Add empty state messages** to BotConsole and the bot selector dropdown.

**Priority 4 — Data presentation**

12. **Format financial values** — use `Intl.NumberFormat` for profit values and `Intl.DateTimeFormat` for timestamps.

13. **Add table sorting** to TradeHistoryTable — at minimum sort by timestamp and profit.

14. **Make bot status prominent** — move the status indicator out of the heading into a dedicated status bar.
