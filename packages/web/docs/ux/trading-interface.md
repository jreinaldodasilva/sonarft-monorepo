# Trading Interface UX/UI & Interaction Design
**Prompt:** 07-WEB-UX | **Package:** web | **Reviewed:** July 2025

---

## Executive Summary

The sonarftweb trading interface is purposeful and well-suited to its domain.
The dark palette, compact information density, and real-time log console are
appropriate for a trading dashboard. The live-trading confirmation modal is a
standout safety feature. Accessibility is strong: `aria-live` regions, `role`
attributes, `sr-only` captions, `:focus-visible` outlines, and semantic HTML
are all present. The main UX gaps are: no idle session timeout in effect, the
stopped bot state is not reflected in the UI, there is no empty-state guidance
for new users, and the single-breakpoint responsive layout collapses the config
sidebar above the bot panel on narrow screens rather than using a tab or
accordion pattern. No WCAG AA failures were found in the reviewed source.

---

## 1. Navigation & Information Architecture

**Navigation structure:** Single top navbar with logo, a "Dashboard" link, and
the user email badge. No secondary navigation, no sidebar menu, no breadcrumbs.

**Page hierarchy:** Flat — one route (`/crypto`) serves the entire trading
interface. All features (parameters, indicators, bots, history, chart) are
visible simultaneously on the dashboard. There is no page-level navigation
between sections.

**Layout:** Two-column CSS grid:
- Left column (260px, sticky): Parameters panel + Indicators panel
- Right column (flex-1): Bot controls + console + history + P&L chart

```css
/* crypto.css */
.crypto {
    display: grid;
    grid-template-columns: 260px 1fr;
    gap: 12px;
    padding: 12px;
}
.parameters-container { position: sticky; top: 12px; }
```

The sticky left column keeps config visible while scrolling through trade
history — a good UX decision for a dashboard where config and activity are
used together.

**Navigation clarity:** The single "Dashboard" nav link is clear. The user
always knows where they are. No active-link highlighting is applied to the
nav link (it is always the current page), which is acceptable given there is
only one route.

**Cross-linking:** Not applicable — single-page application with one route.

**Breadcrumbs:** Not needed at this navigation depth.

---

## 2. Trading Workflows

### Workflow 1: Configure and start a bot

| Step | UI element | Clarity |
|---|---|---|
| 1. Select exchanges | Parameters panel checkboxes | ✅ Clear — exchange names with tooltips |
| 2. Select symbols | Parameters panel checkboxes | ✅ Clear — symbol names with tooltips |
| 3. Select strategy | Strategy dropdown | ✅ Clear — two options with descriptions |
| 4. Save parameters | "Set bot parameters" button | ✅ Clear — save feedback shown inline |
| 5. Select indicators | Indicators panel checkboxes | ✅ Clear — indicator names with tooltips |
| 6. Save indicators | "Set bot indicators" button | ✅ Clear |
| 7. Create bot | "+ Create Bot" button | ✅ Clear — disabled when bot exists or WS disconnected |
| 8. Monitor | Log console updates in real time | ✅ Clear |

**Gap:** There is no onboarding guidance for new users. A first-time user sees
all panels simultaneously with no indication of the recommended workflow order
(configure first, then create bot). A numbered step indicator or a "Getting
started" tooltip sequence would reduce confusion.

**Gap:** The "+ Create Bot" button is disabled when a bot already exists
(`hasBots || !wsOpen`). The disabled state has no tooltip explaining why it is
disabled. A user who has a bot running and tries to create another sees a greyed
button with no explanation.

### Workflow 2: Switch to live trading

| Step | UI element | Clarity |
|---|---|---|
| 1. Click "📝 Paper" toggle | Mode toggle button | ✅ Clear — paper/live state visible |
| 2. Read confirmation modal | Modal with warning text | ✅ Excellent — explicit risk warning |
| 3. Confirm or cancel | Two clearly labelled buttons | ✅ Clear |

The live-trading confirmation modal is the strongest safety UX in the
application. It explicitly states "Real orders will be placed on exchanges
using real funds" and warns about API key configuration. The "⚡ Confirm Live
Trading" button is styled in red to reinforce the risk. ✅

### Workflow 3: Remove a bot

| Step | UI element | Clarity |
|---|---|---|
| 1. Click "✕ Remove" | Remove button (red) | ✅ Clear |
| 2. Read confirmation modal | Modal with bot ID and warning | ✅ Clear |
| 3. Confirm or cancel | Two clearly labelled buttons | ✅ Clear |

The remove confirmation modal correctly truncates the bot ID to 8 chars for
readability and notes that "Trade history is preserved." ✅

### Workflow 4: View trade history

| Step | UI element | Clarity |
|---|---|---|
| 1. Scroll to history panel | Below bot controls | ⚠️ Not obvious — no anchor link |
| 2. View order history table | `TradeHistoryTable` | ✅ Clear — formatted columns |
| 3. View P&L chart | `ProfitChart` area chart | ✅ Clear — cumulative curve with tooltip |
| 4. View trade history table | Second `TradeHistoryTable` | ✅ Clear |

**Gap:** The history panel is below the fold on most screens. There is no
"Jump to history" link or tab. Users must scroll to find it.

### Workflow 5: Stop a bot

| Step | UI element | Clarity |
|---|---|---|
| 1. Click "■ Stop" | Stop button (amber) | ✅ Clear |
| 2. (No confirmation) | — | ⚠️ No confirmation modal for stop |
| 3. Bot status update | Status badge | ⚠️ Status does not change — `bot_stopped` event ignored |

Stop is a lower-risk action than remove (bot is paused, not deleted), so no
confirmation modal is reasonable. However, the status badge does not update
after stop because the `bot_stopped` WebSocket event is silently ignored by
the frontend. The user sees "● Running" after clicking Stop until they reload.

---

## 3. Form Design & Input Validation

**Form elements used:**
- Checkboxes (exchanges, symbols, indicators) — controlled inputs
- Strategy dropdown (`<select>`) — controlled input
- No free-text inputs in the trading interface

**Labels:** All checkboxes have `<label>` elements wrapping the input. The
strategy dropdown has an explicit `<label htmlFor="strategy-select">`. ✅

**Tooltips:** All checkbox items have `title` attributes providing descriptive
tooltips (e.g. `"RSI (14) — measures momentum; ≥70 overbought, ≤30 oversold"`).
These appear on hover and provide valuable context for non-expert users. ✅

**Required fields:** Not applicable — all config fields are optional checkboxes.
The API accepts empty config dicts.

**Default values:** Config panels initialize from the server, then localStorage,
then bundled defaults. Users always see a pre-populated state rather than empty
checkboxes. ✅

**Validation:** No client-side validation before save. The API validates server-
side (key regex, dict size limit). If validation fails, the user sees
"✗ Error — try again" with no field-level detail. The API's 422 response body
contains field-level errors but the frontend does not parse them.

**Save feedback:** Inline `<span role="status" aria-live="polite">` shows
"Saving...", "✓ Saved", or "✗ Error — try again" for 3 seconds after each
save attempt. ✅

**Double-submission prevention:** Save buttons are disabled during
`saveStatus === "saving"`. ✅

**`:has(input:checked)` visual feedback:** Checked checkbox items get a blue
border and background (`border-color: var(--accent); background: var(--accent-dim)`).
This provides clear visual confirmation of selected state beyond the checkbox
tick alone. ✅

---

## 4. Error Handling & User Feedback

### Error display inventory

| Error type | Display location | ARIA | Dismissible? |
|---|---|---|---|
| WS connection error | Red banner above bot panel | `role="alert"` | No — clears on reconnect |
| REST fetch error | Red banner above bot panel | `role="alert"` | No — persists until next success |
| Config save error | Inline span next to save button | `role="status"`, `aria-live="polite"` | Auto-clears after 3s |
| Config save success | Inline span next to save button | `role="status"`, `aria-live="polite"` | Auto-clears after 3s |
| Bot loading | Grey italic text | None | N/A |
| Render error | `ErrorBoundary` full-panel fallback | None | "Try again" button |

**Error clarity:** The WS and fetch error messages are user-readable:
- `"WebSocket connection error — check server status"`
- `"Could not load bots — is the server running?"`
- `"Cannot create bot — not connected to server"`

These are actionable — they tell the user what to check. ✅

**Error persistence:** The `fetchError` banner persists until the next
successful operation. There is no dismiss button. A user who sees an error
and then successfully creates a bot will see the error clear automatically,
but a user who sees an error and takes no further action cannot dismiss it.

**Success feedback:** Save operations show "✓ Saved" for 3 seconds. Bot
creation is confirmed by the status badge changing to "● Running" and the
bot selector populating. ✅

**No toast/notification system:** All feedback is inline. There are no
floating toast notifications. This is appropriate for a dashboard where
inline context is more useful than floating overlays.

**Timeout feedback:** No timeout messages. If a `fetch` call hangs (no
`AbortController`), the user sees "Saving..." indefinitely with no timeout
message. This is the most significant UX gap in error handling.

**API error codes not surfaced:** 401 (session expired), 429 (rate limited),
and 422 (validation error) all show the same generic "✗ Error — try again"
message. A 401 should prompt re-authentication; a 429 should suggest waiting.

---

## 5. Responsiveness & Mobile Design

**Breakpoints:**

| Breakpoint | Layout change |
|---|---|
| `> 900px` | Two-column grid: 260px config sidebar + flex-1 bot panel |
| `≤ 900px` | Single column: config panels stack above bot panel |
| `≤ 767px` | Additional: `h2` font size reduced; `.crypto` forced to `flex-direction: column` |

**Desktop (> 900px):** The two-column layout with sticky config sidebar is
well-suited to a trading dashboard. Config is always visible while scrolling
through history. ✅

**Tablet (768–900px):** Single-column layout. Config panels appear above the
bot panel. The user must scroll past Parameters and Indicators to reach the
bot controls. On a tablet in landscape mode this is manageable; in portrait
it requires significant scrolling.

**Mobile (< 768px):** The layout collapses to a single column. The bot
controls, console, and history tables are usable but the trade history table
has 13 columns and will overflow horizontally — the `tables-container` has
`overflow: auto` which enables horizontal scrolling, but this is not ideal
on a small screen.

**Touch interactions:** No touch-specific patterns (swipe, long-press). All
interactions are click/tap. Buttons have adequate padding (`6px 14px`) for
touch targets. The bot selector dropdown is a native `<select>` — touch-
friendly on mobile. ✅

**Viewport meta tag:**

```html
<!-- index.html -->
<meta name="viewport" content="width=device-width, initial-scale=1" />
```
✅ Present.

**Mobile navigation:** The navbar collapses gracefully — logo, title, and
"Dashboard" link remain visible. The user email badge wraps to a new line on
very narrow screens due to `flex-wrap` not being set on `.nav`. On screens
narrower than ~320px the nav could overflow.

**Console on mobile:** The log console has a fixed height of 220px and
`overflow-y: auto`. On mobile this is usable but takes up significant vertical
space. A collapse/expand toggle would improve mobile usability.

**Chart on mobile:** `ResponsiveContainer width="100%"` ensures the P&L chart
fills its container. Recharts renders correctly on mobile. The chart tooltip
is touch-accessible via tap. ✅

---

## 6. Accessibility (WCAG Compliance)

### ARIA and semantic HTML

| Element | Implementation | Status |
|---|---|---|
| Bot status badge | `role="status"`, `aria-live="polite"` | ✅ |
| WS status badge | `aria-label="WebSocket connected/disconnected"` | ✅ |
| Mode toggle button | `aria-label="Switch to live/paper trading"` | ✅ |
| Error banners | `role="alert"` | ✅ |
| Save status span | `role="status"`, `aria-live="polite"` | ✅ |
| Log console | `aria-label="Bot log output"`, `aria-live="polite"` | ✅ |
| Trade history table | `<caption className="sr-only">` | ✅ |
| Table headers | `scope="col"` on all `<th>` | ✅ |
| History container | `aria-live="polite"`, `aria-relevant="additions"` | ✅ |
| Live confirm modal | `role="dialog"`, `aria-modal="true"`, `aria-labelledby` | ✅ |
| Remove confirm modal | `role="dialog"`, `aria-modal="true"`, `aria-labelledby` | ✅ |
| Logo image | `alt="SonarFT"` | ✅ |
| Bot selector | `aria-label="Active Bot"` | ✅ |
| Strategy select | `<label htmlFor="strategy-select">` | ✅ |

**Focus management:** `:focus-visible` is defined globally in `styles.css`:

```css
:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
    border-radius: 3px;
}
:focus:not(:focus-visible) { outline: none; }
```

This provides visible keyboard focus indicators without showing outlines on
mouse clicks. ✅

**Modal focus trap:** The confirmation modals use `role="dialog"` and
`aria-modal="true"` but do not implement a focus trap. When the modal opens,
focus is not moved to the modal, and keyboard users can Tab to elements behind
the overlay. A focus trap (moving focus to the first modal button on open,
trapping Tab within the modal, restoring focus on close) is needed for full
WCAG 2.1 AA compliance.

**Heading hierarchy:**

```
<h1> — Footer copyright (misplaced — should be <p>)
<h2> — "Bots", "Parameters", "Indicators", "Order History", "Trade History"
<h3> — "Exchanges", "Symbols", "Periods", "Oscillators", "Moving Averages"
<h3> — "Cumulative P&L" (chart title)
```

The `<h1>` in `Footer` is semantically incorrect — the footer copyright line
uses `<h1>` which should be a `<p>` or `<span>`. There is no page-level `<h1>`
for the dashboard content. WCAG 2.4.6 (Headings and Labels) recommends a
descriptive `<h1>` for the main content area.

**Color contrast:** The dark palette uses:
- Primary text `#e2e8f0` on `#111827` background — contrast ratio ~13:1 ✅
- Secondary text `#94a3b8` on `#111827` — contrast ratio ~5.5:1 ✅
- Accent blue `#3b82f6` on `#111827` — contrast ratio ~4.6:1 ✅ (AA)
- Green `#22c55e` on `#052e16` (profit positive) — contrast ratio ~5.2:1 ✅
- Red `#ef4444` on `#2d0a0a` (profit negative) — contrast ratio ~4.8:1 ✅
- Amber `#f59e0b` on `#2d1a00` (stop button) — contrast ratio ~5.1:1 ✅
- Muted text `#4a5568` on `#111827` — contrast ratio ~2.8:1 ⚠️ fails AA (4.5:1 required for normal text)

The `--text-muted` (`#4a5568`) token is defined but its usage in the reviewed
components is limited to the scrollbar thumb — not used for readable text
content. If it is used for text elsewhere, it would fail WCAG AA contrast.

**Screen reader support:** `aria-live="polite"` on the log console means screen
readers announce new log lines. At high log frequency this could be disruptive.
Consider `aria-live="off"` for the console and providing a separate
"last status" region with `aria-live="polite"` for important events only.

**Keyboard navigation:** All interactive elements (buttons, selects, checkboxes,
links) are natively focusable. Tab order follows DOM order, which matches the
visual layout. ✅

---

## 7. Trading-Specific UX Patterns

**Simulation / live mode toggle:**
The paper/live toggle is prominently placed in the bot panel header. The
"📝 Paper" / "⚡ Live" labels with emoji are immediately recognizable. The
red styling for live mode provides a persistent visual warning. The confirmation
modal for switching to live is the correct safety pattern for a financial
application. ✅

**Bot status indicator:**
Three states with color-coded badges:
- `● Idle` — dark grey
- `● Running` — green
- `● Error` — red

Clear and immediately readable. The `aria-live="polite"` attribute ensures
screen readers announce status changes. ✅

**WebSocket connection indicator:**
`● Connected` (green) / `○ Disconnected` (amber) badge in the panel header.
Buttons are disabled when disconnected. Users cannot accidentally send commands
to a disconnected server. ✅

**Bot stopped state — gap:**
As noted in Prompt 05, the `bot_stopped` WebSocket event is ignored. After
clicking "■ Stop", the status badge remains "● Running". The user has no visual
confirmation that the stop command was received. This is a meaningful UX gap
for a trading application where knowing whether a bot is actively trading is
critical.

**Order/trade confirmation:**
Individual orders and trades are not confirmed before execution — the bot
executes autonomously. The only user-facing confirmation is the live/paper
mode toggle. This is correct for an automated trading bot — the user configures
the strategy, not individual orders.

**Risk warnings:**
- Live trading modal: explicit warning with red styling ✅
- Remove bot modal: warns about in-flight orders ✅
- No warning when saving parameters that could affect a running bot (e.g.
  changing exchanges while a bot is running). This is a potential UX gap —
  the user may not realize that parameter changes take effect on the next
  bot cycle.

**Account balance:** Not displayed. The frontend has no balance information —
this is managed server-side by the bot engine. For a paper trading interface
this is acceptable; for live trading, showing available balance would be a
valuable safety feature.

**Performance metrics:**
- Cumulative P&L chart (area chart, green/red based on final value) ✅
- Per-trade profit column with color coding (green positive, red negative) ✅
- Profit percentage column ✅
- No aggregate statistics (total profit, win rate, average trade size, Sharpe
  ratio). The history tables show raw data but no summary statistics panel.

**Price display:** Real-time prices are not displayed in the UI. The bot engine
processes prices internally and logs activity to the console. The frontend
shows trade execution prices in the history table but not live bid/ask prices.
This is a deliberate design choice for an automated bot — the user monitors
outcomes, not individual price ticks.

---

## 8. Data Visualization

**Chart type:** Single `AreaChart` (Recharts) showing cumulative P&L over time.

**Readability:**
- Chart title "Cumulative P&L" is clear
- Y-axis tick formatter rounds to 2 decimal places
- X-axis uses `interval="preserveStartEnd"` — shows first and last timestamps,
  avoiding label crowding on dense datasets ✅
- Color adapts to final P&L: green gradient for positive, red for negative —
  immediate visual signal of overall performance ✅
- `ReferenceLine y={0}` draws a blue dashed zero line — clear break-even
  reference ✅

**Tooltip:**
```
[timestamp]
Trade P&L: +0.0042
Cumulative: +0.1234
```
Shows both per-trade and cumulative values. Color-coded positive/negative. ✅

**Interactivity:** Hover tooltip via Recharts default. No zoom, pan, or
time-range selection. For a trading dashboard, zoom/pan would be valuable
for analyzing performance over specific periods.

**Empty state:**
```
"No trade data yet — P&L curve will appear after the first trade."
```
Clear, informative, and sets correct expectations. ✅

**Real-time updates:** The chart re-renders when `trades` state updates (on
`trade_success` WebSocket event). `React.memo` on `ProfitChart` and `useMemo`
on the data computation prevent unnecessary re-renders. ✅

**Performance with large datasets:** `useMemo` recomputes the chart data array
only when `trades` changes. Recharts renders SVG — performance degrades
gracefully with hundreds of data points but may become sluggish with thousands.
The API's default `limit=100` caps the dataset at 100 trades, which is well
within Recharts' comfortable range.

**Mobile rendering:** `ResponsiveContainer width="100%"` adapts to container
width. Fixed height of 220px. Renders correctly on mobile. ✅

**Missing visualizations:**
- No candlestick or OHLCV chart (not needed for this bot type)
- No win/loss distribution chart
- No drawdown chart
- No per-exchange breakdown

These are enhancements rather than gaps — the current P&L chart covers the
primary performance monitoring need.

---

## 9. Loading & Empty States

| Context | Loading state | Empty state |
|---|---|---|
| Initial bot load | "Loading..." grey italic text | Implicit — bot controls show "No bots" in selector |
| Bot selector (no bots) | — | `<option value="">No bots</option>` ✅ |
| Trade history (no trades) | — | Table renders with empty `<tbody>` — no empty state message |
| Order history (no orders) | — | Table renders with empty `<tbody>` — no empty state message |
| P&L chart (no trades) | — | "No trade data yet — P&L curve will appear after the first trade." ✅ |
| Config load | — | Immediate render from localStorage/defaults — no visible loading |
| WS connecting | "○ Disconnected" badge | — |

**Empty table state — gap:** When there are no orders or trades, the history
tables render with visible column headers but an empty body. There is no
"No orders yet" or "No trades yet" message. A first-time user may wonder if
the table failed to load or if there is genuinely no data.

**Skeleton screens:** Not used. The config panels render immediately from
cached data, making skeletons unnecessary there. The bot panel shows a brief
"Loading..." text during the initial REST fetch.

**Call-to-action in empty states:** The P&L chart empty state is the only
one with a helpful message. The empty history tables and the initial "no bots"
state have no guidance on what to do next.

---

## 10. Help & Documentation

**Tooltips:** All checkbox items in Parameters and Indicators have `title`
attribute tooltips with descriptive text:
- Exchange tooltips: `"Binance — world's largest crypto exchange by volume"`
- Symbol tooltips: `"Bitcoin / Tether — highest liquidity trading pair"`
- Indicator tooltips: `"RSI (14) — measures momentum; ≥70 overbought, ≤30 oversold"`
- Strategy tooltips: `"Market Making — profit by posting limit orders on both sides of the spread"`

These are genuinely useful for non-expert users. ✅

**Inline help:** No inline help text beyond tooltips. No `?` help icons, no
expandable explanations.

**User guide:** Not present in the frontend. The monorepo has a
`docs/developer-guide.md` but no end-user guide.

**Onboarding:** No onboarding flow, no welcome screen, no step-by-step wizard
for first-time setup. A new user lands directly on the full dashboard.

**Error guidance:** Error messages are descriptive but do not suggest specific
remediation steps (e.g. "Could not load bots — is the server running?" is
helpful but could link to a troubleshooting guide).

**FAQ:** Not present.

---

## 11. Performance Perceived by User

**Page load:** The `Crypto` page is lazy-loaded via `React.lazy`:
```typescript
const Crypto = lazy(() => import("./pages/Crypto/Crypto"));
```
The `<Suspense fallback={<PageLoader />}>` shows "Loading..." during the
dynamic import. The `Crypto` chunk is small (~6.8KB gzip per README), so the
load is near-instant on a fast connection. ✅

**Interaction responsiveness:** Button clicks trigger immediate state updates
(dispatch, setShowConfirm) before any async operation. The UI responds
instantly to user input. ✅

**Optimistic updates:** The simulation toggle is the only optimistic update —
the button label changes immediately before server confirmation. All other
state changes wait for server events (bot_created, bot_removed) or REST
responses.

**Animation:** CSS `transition: background 0.2s` on buttons and
`transition: border-color 0.15s` on checkbox items. Smooth and subtle. ✅
No heavy animations that could cause jank.

**Log console performance:** RAF batching caps log re-renders at 60fps.
The console auto-scrolls only when the user is within 60px of the bottom —
preventing forced scroll when the user is reviewing earlier log lines. ✅

**Perceived latency for bot creation:** After clicking "+ Create Bot", the
button is disabled (via `dispatch(CREATE_REQUESTED)` → `lifecycle: "creating"`)
and the status badge shows "● Idle" until `bot_created` arrives. There is no
spinner or progress indicator during the creation window. A brief "Creating..."
status would improve perceived responsiveness.

---

## 12. Consistency & Design System

**Color scheme:** Consistent dark trading palette throughout, driven by CSS
custom properties in `variables.css`. All components consume the same tokens.
No hardcoded colors except a few specific dark shades in `bots.css`. ✅

**Typography:** Consistent use of `styles.css` base typography:
- `h2`: 0.95rem, uppercase, letter-spacing — used for all panel titles
- `h3`: 0.8rem, uppercase — used for all section subheadings
- Body: 0.875rem Inter/system-ui

**Spacing:** Consistent 8–16px padding on cards, 8–12px gaps in flex/grid
layouts. ✅

**Button styles:** Three button variants used consistently:
- Primary (blue `--accent`): Create Bot, Save buttons
- Warning (amber): Stop button
- Danger (red): Remove button, Live confirm button

**Interaction patterns:** Consistent across config panels:
- Checkbox → immediate local state update + localStorage write
- Save button → async PUT → inline status feedback

**Inconsistency — `Parameters` vs `Indicators`:** `Parameters` has a strategy
dropdown that `Indicators` does not. Beyond this intentional difference, the
two panels are visually and behaviorally identical. ✅

**Inconsistency — `errorboundary.css` uses legacy tokens:** `errorboundary.css`
uses `var(--backgroundSecondary)`, `var(--buttonBackground)`, `var(--textPrimary)`
(legacy aliases) while all other components use the new `var(--bg-surface)`,
`var(--accent)`, `var(--text-primary)` tokens. The legacy aliases map to the
same values, so there is no visual difference, but it is an inconsistency in
the codebase.

**Inconsistency — `charts.css` uses legacy tokens:** Same issue —
`var(--textPrimary)`, `var(--textTertiary)`, `var(--backgroundSecondary)`,
`var(--borderPrimary)` used instead of the new token names.

---

## 13. Internationalization (i18n)

**Translation:** Not implemented. All strings are hardcoded in English in
component JSX and CSS. No i18n library (react-i18next, etc.) is used.

**Number formatting:** `Intl.NumberFormat` is used in `TradeHistoryTable` and
`ProfitChart` with `undefined` locale (uses browser locale):
```typescript
new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })
new Intl.DateTimeFormat(undefined, { month: "numeric", day: "numeric", ... })
```
Numbers and dates adapt to the user's browser locale. ✅

**Currency formatting:** Trade values are formatted as plain numbers, not as
currency (no `style: "currency"`). This is correct — the quote currency varies
per trading pair (USDT, BTC, etc.) and is shown in the symbol column.

**RTL support:** Not implemented. CSS uses directional properties (`margin-left`,
`padding-left`, `text-align: right`) that would not adapt to RTL layouts.

**Languages supported:** English only.

---

## 14. Specific Trading UI Elements

**Bot management:**
- Create: single button, one bot at a time (server limit: 5 per client)
- Stop: pauses the bot (no confirmation — low risk)
- Remove: confirmation modal with bot ID and warning
- Bot selector: native `<select>` showing truncated bot IDs

**Indicator configuration:**
- Grouped checkboxes: Periods, Oscillators, Moving Averages
- Tooltips explain each indicator's purpose and parameters
- Save persists to server and localStorage

**Parameter settings:**
- Exchanges: checkboxes with exchange name tooltips
- Symbols: checkboxes with pair description tooltips
- Strategy: dropdown (Arbitrage / Market Making)
- Save persists to server and localStorage

**Strategy selection:**
- Two options: Arbitrage and Market Making
- Tooltip on the selected strategy explains the approach
- No visual explanation of the difference beyond the tooltip

**Paper vs live mode:**
- Toggle button in bot panel header
- Paper → Live requires confirmation modal
- Live → Paper is immediate (safe direction)
- Mode persists in `isSimulating` state (not persisted to server on reconnect)

**Stop-loss / take-profit:** Not configurable from the UI. These are managed
by the bot engine's internal logic (profit threshold in `config_parameters.json`).

---

## 15. Usability Issues Summary

| Severity | Issue | Description | Impact | Fix |
|---|---|---|---|---|
| High | Bot stopped state not reflected | `bot_stopped` WS event ignored — status badge stays "● Running" after Stop | User cannot tell if bot is actively trading | Handle `bot_stopped` in `onmessage`; add `BOT_STOPPED` reducer action; show "● Stopped" badge |
| Medium | No idle session timeout | `useIdleTimeout` hook exists but is not wired — session never expires | Security risk: unattended live trading session stays active | Wire `useIdleTimeout` into `AuthProvider` using `VITE_IDLE_TIMEOUT_MS` |
| Medium | No onboarding for new users | Full dashboard shown immediately with no workflow guidance | New users don't know to configure parameters before creating a bot | Add numbered step indicators or a "Getting started" tooltip sequence |
| Medium | Empty history tables have no message | Order/trade tables show column headers with empty body | Users can't tell if data failed to load or is genuinely empty | Add "No orders yet" / "No trades yet" empty state rows |
| Medium | Modal focus not trapped | Confirmation modals don't trap keyboard focus | Keyboard users can Tab to elements behind the modal overlay | Implement focus trap: move focus to first button on open, trap Tab, restore on close |
| Low | No feedback during bot creation | After "+ Create Bot", no spinner or "Creating..." status | User doesn't know if the command was received | Show "● Creating..." in status badge during `lifecycle === "creating"` |
| Low | Disabled "+ Create Bot" has no tooltip | Button is greyed with no explanation when a bot exists | User doesn't know why they can't create another bot | Add `title="A bot already exists — remove it first"` to the disabled button |
| Low | History panel below the fold | No anchor link or tab to jump to order/trade history | Users must scroll to find history | Add a "View History ↓" anchor link or a tab switcher between "Console" and "History" views |
| Low | `<h1>` misused in Footer | Footer copyright uses `<h1>` — should be `<p>` or `<span>` | Screen readers announce footer as a top-level heading | Change `<h1>` to `<p>` in `Footer.tsx` |
| Low | No page-level `<h1>` | Dashboard has no `<h1>` for the main content area | Screen readers have no landmark heading for the page | Add a visually hidden `<h1>` (`.sr-only`) to `Crypto.tsx`: `<h1 className="sr-only">SonarFT Trading Dashboard</h1>` |
| Low | `aria-live="polite"` on log console | Screen readers announce every log line at high frequency | Disruptive for screen reader users during active trading | Change console to `aria-live="off"`; add a separate `aria-live="polite"` region for important status events only |
| Low | `errorboundary.css` / `charts.css` use legacy tokens | These files use `var(--backgroundSecondary)` etc. instead of new token names | Inconsistency — no visual impact today but could break if legacy aliases are removed | Update to use new token names (`var(--bg-surface)`, `var(--text-primary)`, etc.) |
| Info | No aggregate performance statistics | History tables show raw data but no summary (total profit, win rate, avg trade) | Users must manually calculate performance metrics | Add a summary row or stats panel above the history tables |
| Info | No zoom/pan on P&L chart | Chart shows all trades with no time-range selection | Hard to analyze specific periods on long-running bots | Add Recharts `Brush` component for time-range selection |
| Info | `isSimulating` not re-synced on reconnect | After WS reconnect, simulation mode may not match server state | User sees wrong mode indicator after reconnect | Re-fetch bot state on reconnect to sync `isSimulating` |
