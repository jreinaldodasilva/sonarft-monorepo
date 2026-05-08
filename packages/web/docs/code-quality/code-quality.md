# Code Quality & JavaScript Best Practices
**Prompt:** 10-WEB-QUALITY | **Package:** web | **Reviewed:** July 2025

---

## Executive Summary

sonarftweb's code quality is high. TypeScript strict mode is enabled throughout,
`const`/`let` are used exclusively, async/await is consistent, and React best
practices (functional components, correct hook dependencies, `React.memo` on
pure components) are followed without exception. The ESLint configuration is
comprehensive with `react-hooks/exhaustive-deps` enforced. The three ESLint
errors found are `no-undef` for browser globals (`HTMLPreElement`,
`HTMLSelectElement`, `sessionStorage`) that are missing from the ESLint globals
config — a tooling gap, not a code quality issue. The main quality observations
are: `useBots.ts` at 263 lines is the largest source file and concentrates
multiple concerns; `Parameters.tsx` at 163 lines duplicates the
`ConfigCheckboxPanel` pattern; and there are no JSDoc comments on any exported
function. No `var`, no `any` in production code, no `dangerouslySetInnerHTML`,
no hardcoded secrets.

---

## 1. Code Style & Consistency

**ESLint:** Configured via `eslint.config.js` (ESLint v9 flat config). Rules:
- `no-console: warn` — discourages console logging in production
- `@typescript-eslint/no-unused-vars: warn` (args with `^_` ignored)
- `@typescript-eslint/no-explicit-any: warn`
- `react/jsx-key: error`
- `react-hooks/rules-of-hooks: error`
- `react-hooks/exhaustive-deps: warn`
- `jsx-a11y/alt-text`, `aria-props`, `aria-role`, `no-noninteractive-element-interactions: warn`

**Live ESLint result (July 2025):** 3 errors, 0 warnings.

The 3 errors are all `no-undef` for browser globals not listed in the ESLint
globals config:
- `HTMLPreElement` in `BotConsole.tsx` (used in `useRef<HTMLPreElement>`)
- `HTMLSelectElement` in `Parameters.tsx` (used in event handler type)
- `sessionStorage` in `api.ts`

These are valid browser globals available at runtime. The fix is to add them
to the `globals` block in `eslint.config.js`, not to change the code.

**Prettier:** Configured via `.prettierrc`:
```json
{
  "semi": true,
  "singleQuote": false,
  "tabWidth": 4,
  "trailingComma": "es5",
  "printWidth": 100,
  "bracketSpacing": true,
  "arrowParens": "always"
}
```

Double quotes, 4-space indentation, semicolons, trailing commas in ES5
positions. Applied consistently across all source files. ✅

**Indentation:** 4 spaces throughout. Consistent. ✅

**Quote style:** Double quotes for JSX attributes and string literals.
Consistent. ✅

**Semicolons:** Present on all statements. Consistent. ✅

**Line length:** `printWidth: 100`. A few lines in `vite.config.js` and
`eslint.config.js` exceed 100 chars but these are excluded from linting. ✅

**File organization:** Each component in its own directory with co-located
CSS and test files. Hooks in `hooks/`, utilities in `utils/`, pages in
`pages/`. Consistent. ✅

---

## 2. JavaScript Best Practices

**`var` usage:** None. All variables use `const` or `let`. ✅

**`const` vs `let`:** `const` used for all values that are not reassigned.
`let` used only where reassignment is needed (e.g. `let cumulative = 0` in
`ProfitChart`). ✅

**Arrow functions:** Used consistently for callbacks, event handlers, and
inline functions. Named function declarations used for component definitions
(`const Bots: React.FC = ...`). ✅

**Template literals:** Used for string interpolation throughout:
```typescript
setWsUrl(`${WS}/${clientId}?ticket=${encodeURIComponent(ticket)}`);
throw new Error(`HTTP error! status: ${response.status}`);
```
✅

**Destructuring:** Used consistently for props, hook returns, and object
access:
```typescript
const { socket, wsOpen, wsError } = useWebSocket(wsUrl ?? "", !!wsUrl);
const { name, checked } = e.target;
const [config, setConfig] = useState<T>(...);
```
✅

**Spread operator:** Used for object merging in state updates and header
construction:
```typescript
const next = { ...prev, [section]: { ...prev[section], [name]: checked } };
headers: { ...baseHeaders, ...getAuthHeaders() }
```
✅

**Optional chaining (`?.`):** Used appropriately:
```typescript
user?.email
mockSocket.onmessage?.(event)
this.state.error?.message
payload[0].payload
```
✅

**Nullish coalescing (`??`):** Used for fallbacks:
```typescript
(import.meta.env.VITE_API_URL as string) ?? "http://localhost:8000/api/v1"
msg.message ?? ""
trades.map((t) => { cumulative += t.profit ?? 0; })
```
✅

**Async/await:** Used consistently for all async operations. No raw `.then()`
chains in production code. ✅

**`Promise.all`:** Used correctly for parallel fetches:
```typescript
const [existingOrders, existingTrades] = await Promise.all([
    fetchAllOrders(ids, clientId),
    fetchAllTrades(ids, clientId),
]);
```
✅

**`encodeURIComponent`:** Used on all URL parameters:
```typescript
HTTP + `/bots?client_id=${encodeURIComponent(clientId)}`
`${WS}/${clientId}?ticket=${encodeURIComponent(ticket)}`
```
✅

---

## 3. React Best Practices

**Functional components:** All components are functional except `ErrorBoundary`
(class component required by React's error boundary API). ✅

**Hooks:** Used correctly throughout. No hooks called conditionally. No hooks
called inside loops. `react-hooks/rules-of-hooks: error` enforces this. ✅

**Key props:** `react/jsx-key: error` enforces key props on all list renders.
Keys are meaningful (not just array index where possible):
```typescript
// TradeHistoryTable — composite key
key={`${row.timestamp}-${row.buy_exchange}-${index}`}

// BotConsole — index used (acceptable for log lines with no stable ID)
key={i}

// Config checkboxes — item name (stable)
key={name}
```
The `key={i}` in `BotConsole` is acceptable — log lines have no stable
identity and are append-only (never reordered). ✅

**`useEffect` dependency arrays:** All dependency arrays are explicit and
complete. `react-hooks/exhaustive-deps: warn` enforces this. The
`useConfigCheckboxes` effect comment explicitly notes:
```typescript
}, [clientId, storageKey, fetchFn, defaultFn, stateKeys]); // all deps explicit — no suppression
```
✅

**No `eslint-disable` suppression of hook deps:** No `// eslint-disable-next-line
react-hooks/exhaustive-deps` comments anywhere in the codebase. ✅

**Component naming:** All components use PascalCase. All hooks use `use`
prefix. ✅

**Fragment shorthand:** `<React.Fragment key={...}>` used where a key is
needed (in `ConfigCheckboxPanel`). `<>...</>` shorthand used elsewhere. ✅

**`React.memo`:** Applied to all pure display components (`BotControls`,
`BotConsole`, `TradeHistoryTable`, `ProfitChart`). Not applied to container
components (correct — memoizing containers with complex state provides no
benefit). ✅

**`React.StrictMode`:** Enabled in `index.tsx`. This causes effects to run
twice in development, which helps catch cleanup issues. ✅

**No `dangerouslySetInnerHTML`:** Not used anywhere. ✅

**No class components beyond `ErrorBoundary`:** ✅

---

## 4. Error Handling

**`try/catch` coverage:** All async operations are wrapped in `try/catch`:
- All `fetch` calls in `api.ts` ✅
- `useBots` load effect ✅
- `useBots` `onmessage` handler ✅
- `useConfigCheckboxes` load chain ✅
- `Parameters` load chain ✅
- `handleSave` in `useConfigCheckboxes` and `Parameters` ✅

**Promise rejection:** No unhandled promise rejections. All `async` functions
either `await` with `try/catch` or return `null`/`false` on failure. ✅

**Error boundaries:** One `ErrorBoundary` wraps the entire `Crypto` page
content. Catches render-time errors. Shows "Something went wrong" with a
"Try again" button. Dev-only error detail via `import.meta.env.DEV`. ✅

**User feedback:** All errors surface to the user:
- REST errors → `fetchError` state → `role="alert"` banner
- WS errors → `wsError` state → `role="alert"` banner
- Save errors → `saveStatus === "error"` → inline `role="status"` span
- Render errors → `ErrorBoundary` fallback UI

✅

**Error logging:** No `console.error` in production paths. Errors are surfaced
to the user but not sent to an external service. The `ErrorBoundary`
`componentDidCatch` has a comment noting it "could send to error reporting
service here" but does not. ✅ (acceptable — no Sentry configured)

**Specific error type handling:** HTTP status codes are not differentiated
beyond `response.ok`. A 401 (expired token), 429 (rate limited), and 500
(server error) all produce the same generic error message. This is the main
error handling gap — identified in Prompt 06 and Prompt 02.

---

## 5. Code Organization

### File size inventory

| File | Lines | Assessment |
|---|---|---|
| `hooks/useBots.test.ts` | 308 | Test file — acceptable |
| `hooks/useBots.ts` | 263 | ⚠️ Largest source file — multiple concerns |
| `utils/api.test.ts` | 227 | Test file — acceptable |
| `utils/api.ts` | 193 | Acceptable — single responsibility (API layer) |
| `components/Parameters/Parameters.tsx` | 163 | ⚠️ Could be reduced by using `ConfigCheckboxPanel` |
| `components/Bots/Bots.tsx` | 141 | Acceptable — orchestration component |
| `hooks/useWebSocket.test.tsx` | 139 | Test file — acceptable |
| `hooks/useConfigCheckboxes.ts` | 119 | Acceptable |
| `hooks/useConfigCheckboxes.test.ts` | 119 | Test file — acceptable |
| `components/Charts/ProfitChart.tsx` | 107 | Acceptable |
| `components/ConfigCheckboxPanel/ConfigCheckboxPanel.tsx` | 103 | Acceptable |

No file exceeds 300 lines. The 300-line threshold is not breached by any
source file. ✅

**`useBots.ts` at 263 lines** is the largest source file. It contains:
- Bot state machine types and reducer (~30 lines)
- Legacy exports (~5 lines)
- WS message type and parser (~15 lines)
- Return type interface (~25 lines)
- Hook body with 5 effects, 4 handlers, derived values (~190 lines)

This is a deliberate design — one orchestration hook for the bot domain.
Acceptable at current scale.

### Function size

No function exceeds 50 lines. The largest functions are:
- `useBots` hook body (~190 lines, but this is a hook, not a function)
- `botMachineReducer` (~20 lines)
- `handleConnection` in `manager.py` (~40 lines, server-side)

All component render functions are under 80 lines. ✅

### Import organization

Imports follow a consistent pattern across files:
1. React imports
2. Third-party imports
3. Local hook/context imports
4. Local component imports
5. Local utility imports
6. CSS imports

No import sorting tool (e.g. `eslint-plugin-import`) is configured, but the
manual ordering is consistent. ✅

### Circular dependencies

None detected (confirmed in Prompt 01 architecture review). The dependency
graph is a strict DAG. ✅

---

## 6. Naming Conventions

**Components:** PascalCase throughout (`Bots`, `BotControls`, `BotConsole`,
`ConfigCheckboxPanel`, `ErrorBoundary`). ✅

**Hooks:** `use` prefix throughout (`useBots`, `useWebSocket`,
`useConfigCheckboxes`, `useIdleTimeout`, `useAuth`). ✅

**Variables and functions:** camelCase throughout. ✅

**Constants:** Module-level constants use UPPER_SNAKE_CASE:
```typescript
const MAX_LOG_LINES = 500;
const BACKOFF_BASE_MS = 1000;
const BACKOFF_MAX_MS = 30000;
const SAVE_FEEDBACK_MS = 3000;
const ACTIVITY_EVENTS = [...] as const;
```
✅

**Boolean naming:** Mixed — some use `is`/`has` prefix, some do not:
- `isLoading`, `isSimulating`, `wsOpen` ✅
- `hasBots`, `canAct` ✅
- `autoReconnect`, `shouldReconnect` — no prefix but clear ✅
- `cancelled` — no prefix but clear ✅

**Object constants:** UPPER_SNAKE_CASE for frozen objects:
```typescript
export const BotState = Object.freeze({ CREATED: 0, REMOVED: 1 });
export const BotStatus = Object.freeze({ IDLE: "idle", RUNNING: "running", ERROR: "error" });
```
✅

**CSS class names:** BEM-inspired kebab-case (`bots-panel`, `bots-panel-header`,
`bot-status--running`, `live-confirm-overlay`). Consistent. ✅

**Magic strings:** Mostly avoided. WS event type strings (`"bot_created"`,
`"order_success"`) are inline in the `switch` statement rather than extracted
as constants. This is a minor issue — the strings are used in only one place
and match the server's schema directly. Extracting them to a shared
`shared/types/api.ts` (which already exists in the monorepo) would be the
ideal solution.

**Magic numbers:** None. All numeric constants are named:
`MAX_LOG_LINES`, `BACKOFF_BASE_MS`, `BACKOFF_MAX_MS`, `SAVE_FEEDBACK_MS`,
`_WS_KEEPALIVE_INTERVAL` (server-side). ✅

---

## 7. Documentation & Comments

**README:** Comprehensive `packages/web/README.md` covering overview,
structure, usage, and mechanisms. The monorepo `README.md` covers the full
stack with API reference, environment variables, and architecture. ✅

**Inline comments:** Used sparingly and purposefully — only where the
rationale is non-obvious:
```typescript
// Keep botIdsRef in sync so the onmessage closure always has the current list
// Flush log buffer to state on animation frame — caps re-renders at 60fps
// Falls back to ?token= for dev mode where the ticket endpoint is unavailable
// all deps explicit — no suppression
// Handle legacy MM-DD-YYYY HH:MM:SS format stored before ISO 8601 fix
```
These are high-quality comments that explain *why*, not *what*. ✅

**JSDoc:** None on any exported function or hook. The TypeScript interfaces
serve as inline documentation for return types and parameters, but there are
no `/** ... */` doc comments. For a small codebase this is acceptable, but
adding JSDoc to the public API surface of `api.ts` and the custom hooks would
improve IDE discoverability.

**TODO comments:** None found in the source. ✅

**Type documentation:** TypeScript interfaces are self-documenting through
their field names. Complex types like `BotMachineAction` and `UseBotsReturn`
are clear without additional comments. ✅

**Documentation freshness:** The README test count (110/110) is out of date
(live run: 105/105). The `VITE_IDLE_TIMEOUT_MS` env var is documented but
not wired. Minor staleness in two places.

---

## 8. Performance Anti-patterns

**Unnecessary re-renders:** The one identified case is `Bots` re-rendering
at 60fps during log flushes (covered in Prompt 08). `React.memo` on children
prevents cascade. No other unnecessary re-renders identified. ✅

**Missing keys:** `react/jsx-key: error` enforces keys. No missing keys. ✅

**Inline functions in props:** Avoided for props passed to `React.memo`
children. All handlers are `useCallback`-stabilized before being passed to
`BotControls`. ✅

One instance of an inline arrow function in `Bots.tsx`:
```typescript
onClick={() => { setShowRemoveConfirm(false); handleRemove(); }}
```
This is in the remove confirmation modal button — not passed to a memoized
child, so it does not cause unnecessary re-renders. Acceptable. ✅

**Inline objects in props:** None passed to memoized children. ✅

**Inline styles:** One instance in `Bots.tsx`:
```typescript
<h2 style={{ marginTop: 12 }}>Trade History</h2>
```
This creates a new object on every render. Minor — not passed to a memoized
child. Could be moved to CSS. ⚠️ (Info level)

**Large library imports:** Recharts is imported with named exports:
```typescript
import {
    ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
    CartesianGrid, Tooltip, ReferenceLine,
} from "recharts";
```
Named imports allow tree-shaking. Vite bundles only the used Recharts
components. ✅

**Polling:** Not used. WebSocket push replaces polling for real-time data. ✅

---

## 9. Security Anti-patterns

**Hardcoded secrets:** None. All sensitive configuration (API URLs, tokens)
comes from environment variables. ✅

**Credential exposure:** No credentials in source code. The `mockUser` fixture
has `token: { access_token: "mock-jwt-token" }` — this is test-only and not
a real credential. ✅

**XSS vulnerabilities:** None. React JSX escaping, no `dangerouslySetInnerHTML`,
no `innerHTML`. ✅

**`eval` / `Function` constructor:** Not used. ✅

**`console.log` in production:** `no-console: warn` ESLint rule. One
intentional `console.log` in `vitals.ts` guarded by `isDev`:
```typescript
// eslint-disable-next-line no-console
console.log(`[Web Vitals] ${metric.name}: ...`);
```
The `eslint-disable` comment is appropriate here — this is a deliberate dev-
only log. ✅

**Input validation:** No free-text user inputs in the trading interface.
All config inputs are checkboxes and a dropdown. Server-side validation
handles all config key validation. ✅

---

## 10. Maintainability Issues

**Dead code:**
- `PrivateRoute` component — defined, tested, not used in routing
- `BotState` / `BotStatus` legacy exports in `useBots.ts` — kept for
  `BotControls` backward compatibility but could be removed after refactoring
  `BotControls` to use `BotLifecycle`
- `App.css` legacy CRA styles (`.App-logo`, `.App-header`, keyframe)
- `styles.css` `.card` class — defined but not used by components
- `VITE_IDLE_TIMEOUT_MS` env var — documented but not wired
- `useIdleTimeout` hook — implemented, tested, not connected to any component
- `@testing-library/user-event` — installed but not used in any test

**Code duplication:**
- `Parameters.tsx` duplicates the `useConfigCheckboxes` load chain (~40 lines)
- `parameters.css` / `indicators.css` share ~60 lines of identical rules

**Tight coupling:** None. All dependencies are injected via props or hooks.
`ConfigCheckboxPanel` is fully decoupled from specific API functions. ✅

**Circular dependencies:** None. ✅

**Mixed concerns:** `useBots` combines WS lifecycle, state machine, REST
polling, and RAF batching. Deliberate design — acceptable at current scale.

**Type safety:** TypeScript strict mode. No `any` in production code. All
public APIs are fully typed. ✅

---

## 11. Specific Code Smells

**Long functions:** None exceeding 50 lines (excluding hook bodies, which
are not functions in the traditional sense). ✅

**Large files:** No source file exceeds 300 lines. ✅

**Long parameter lists:** `ConfigCheckboxPanel` has 9 props — the most of
any component. This is justified by its generic design (each prop is a
distinct concern). No function has more than 4 parameters. ✅

**Excessive nesting:** Maximum nesting depth is 3 levels (e.g. the three-tier
load chain in `useConfigCheckboxes`). No excessive nesting. ✅

**Boolean blindness:** Not present. Boolean parameters are named clearly
(`autoReconnect`, `enabled`, `wsOpen`). ✅

**Magic numbers:** None — all numeric constants are named. ✅

**Inconsistent naming:** One inconsistency: `InitializeModules` in the bot
package uses PascalCase (noted in the bot guidelines as legacy). The web
package has no such inconsistency. ✅

**Obsolete comments:** The `// Could send to error reporting service here`
comment in `ErrorBoundary.componentDidCatch` is a TODO-style comment without
a tracking issue. Minor. ✅

**`void` operator usage:**
```typescript
// ErrorBoundary.tsx
void error; void info;
```
Used to suppress TypeScript "unused variable" warnings for `error` and `info`
parameters in `componentDidCatch`. This is a valid pattern but slightly
unusual — the parameters could instead be prefixed with `_` to follow the
ESLint `argsIgnorePattern: "^_"` convention. ⚠️ (Info level)

---

## 12. Type Safety

**TypeScript version:** 5.x with strict mode enabled:
```json
{
  "strict": true,
  "noUnusedLocals": true,
  "noUnusedParameters": true,
  "noFallthroughCasesInSwitch": true
}
```

**`any` usage:** Zero `any` in production source files. The ESLint rule
`@typescript-eslint/no-explicit-any: warn` enforces this. Test files have
`"@typescript-eslint/no-explicit-any": "off"` — appropriate for test mocking
flexibility. ✅

**Type coverage:** 100% of exported functions and components have explicit
TypeScript types. All props interfaces are defined. All hook return types are
defined. ✅

**Type assertions (`as`):** Used in `api.ts` for API response casting:
```typescript
return await response.json() as TradeRecord[];
return await response.json() as ParametersConfig;
```
These are safe given the server's Pydantic validation, but they bypass runtime
type checking. No `zod` or `io-ts` validation layer. Acceptable for this
application's risk profile.

**Generic types:** `ConfigCheckboxPanel<T extends ConfigState>` and
`useConfigCheckboxes<T extends ConfigState>` use generics correctly. The
constraint `T extends ConfigState` (where `ConfigState = Record<string,
Record<string, boolean>>`) is appropriately tight. ✅

**`noUnusedLocals` / `noUnusedParameters`:** Enabled. The `void error; void info`
pattern in `ErrorBoundary` is a workaround for this — the parameters are
required by the React API but not used. ✅

**Missing type — `version` field:** `ParametersConfig` and `IndicatorsConfig`
in `api.ts` do not declare the `version: number` field present in the API's
Pydantic schemas. This is a type gap identified in Prompt 02. ✅ (tracked)

**`import.meta.env` typing:** `import.meta.env.VITE_*` values are cast with
`as string` throughout. The `vite-env.d.ts` file exists but does not declare
custom env var types. Adding typed declarations would eliminate the casts:
```typescript
// vite-env.d.ts
interface ImportMetaEnv {
    readonly VITE_API_URL: string;
    readonly VITE_WS_URL: string;
    readonly VITE_DEV_AUTH_BYPASS: string;
    readonly VITE_DEFAULT_USER_ID: string;
    readonly VITE_DEFAULT_USER_EMAIL: string;
    readonly VITE_VITALS_URL: string | undefined;
    readonly VITE_IDLE_TIMEOUT_MS: string | undefined;
}
```

---

## 13. Build & Tooling

**Build configuration:** Vite 8 with `@vitejs/plugin-react`. Vendor chunk
splitting for React, Recharts, and Netlify Identity. `sourcemap: false` in
production. `chunkSizeWarningLimit: 100`. ✅

**Development server:** Port 3000, `open: false`. ✅

**Linting in CI:** `npm run lint` is available but not confirmed in the CI
workflow (`.github/workflows/ci.yml` runs `npm test` and `npm audit`). ESLint
is not run in CI — the 3 `no-undef` errors would not block a PR. ⚠️

**Testing in CI:** `npm test` (Vitest) runs in CI. ✅

**Formatting:** Prettier configured. `npm run format` available. Not enforced
in CI (no `prettier --check` step). ⚠️

**Bundling:** Vite with rolldown (Vite 8 uses rolldown as the bundler). Vendor
chunk splitting. Content-hashed filenames. ✅

**Environment variables:** `VITE_` prefix, read via `import.meta.env`. Separate
`.env.development` and `.env.production` files. `.env.*.example` files
provided for onboarding. ✅

**`vite-env.d.ts`:** Present but minimal (only `/// <reference types="vite/client" />`).
Custom env var types not declared (see §12). ⚠️ (Info level)

---

## 14. Code Quality Metrics

| Metric | Value | Assessment |
|---|---|---|
| Total source lines (TS/TSX, excl. tests) | ~1,100 | Small, focused codebase |
| Total lines including tests | ~3,138 | ~65% test code — healthy ratio |
| Largest source file | `useBots.ts` — 263 lines | Under 300-line threshold |
| ESLint errors | 3 (all `no-undef` for browser globals) | Tooling gap, not code issues |
| ESLint warnings | 0 | ✅ |
| TypeScript `any` in production | 0 | ✅ |
| `dangerouslySetInnerHTML` | 0 | ✅ |
| Circular dependencies | 0 | ✅ |
| Direct dependencies | 6 (React, React-DOM, React-is, React-Router, Recharts, web-vitals) | Minimal |
| Dev dependencies | 20 | Appropriate for the toolchain |
| Bundle size (total JS gzip) | ~160 KB | Good |
| App code (gzip) | ~10 KB | Excellent |
| Test pass rate | 105/105 (100%) | ✅ |
| CSS duplication | ~60 lines (parameters.css / indicators.css) | Low |
| Dead code | ~5 items | Low |

---

## 15. Code Quality Issues Summary

| Issue | Type | Severity | Occurrences | Remediation |
|---|---|---|---|---|
| ESLint `no-undef` for browser globals | Tooling | Medium | 3 | Add `HTMLPreElement`, `HTMLSelectElement`, `sessionStorage` to ESLint globals config |
| ESLint not run in CI | Tooling | Medium | 1 | Add `npm run lint` step to `.github/workflows/ci.yml` |
| Prettier not enforced in CI | Tooling | Low | 1 | Add `npx prettier --check "src/**/*.{ts,tsx}"` to CI |
| `Parameters` duplicates `useConfigCheckboxes` | Duplication | Low | 1 | Refactor to use `ConfigCheckboxPanel` + `useConfigCheckboxes` |
| CSS duplication (`parameters.css` / `indicators.css`) | Duplication | Low | ~60 lines | Extract shared rules to `configpanel.css` |
| `PrivateRoute` unused | Dead code | Low | 1 | Wire into routing or remove |
| `useIdleTimeout` not wired | Dead code | Low | 1 | Wire into `AuthProvider` or remove |
| `@testing-library/user-event` unused | Dead code | Low | 1 | Remove from `devDependencies` or migrate `fireEvent` to `userEvent` |
| Legacy CRA styles in `App.css` | Dead code | Low | ~20 lines | Remove `.App-logo`, `.App-header`, keyframe |
| `.card` class unused | Dead code | Info | 1 | Use in components or remove |
| `vite-env.d.ts` missing custom env var types | Type safety | Info | 1 | Add `ImportMetaEnv` interface with all `VITE_*` vars |
| `ParametersConfig` / `IndicatorsConfig` missing `version` | Type safety | Info | 2 | Add `version?: number` to both interfaces |
| No JSDoc on exported functions | Documentation | Info | All exports | Add JSDoc to `api.ts` functions and custom hooks |
| `void error; void info` in `ErrorBoundary` | Style | Info | 1 | Rename to `_error`, `_info` to follow `argsIgnorePattern: "^_"` |
| Inline `style={{ marginTop: 12 }}` in `Bots.tsx` | Style | Info | 1 | Move to CSS |
| WS event type strings not extracted as constants | Maintainability | Info | 1 | Import from `shared/types/api.ts` |

---

## 16. Recommendations

### Immediate (tooling fixes — no code changes)

1. **Fix ESLint `no-undef` errors** — add the three missing browser globals
   to `eslint.config.js`:
   ```javascript
   globals: {
       // existing globals...
       HTMLPreElement: "readonly",
       HTMLSelectElement: "readonly",
       sessionStorage: "readonly",
   }
   ```

2. **Add ESLint to CI** — add to `.github/workflows/ci.yml`:
   ```yaml
   - run: npm run lint
   ```

3. **Add Prettier check to CI**:
   ```yaml
   - run: npx prettier --check "src/**/*.{ts,tsx}"
   ```

### Short-term (code quality)

4. **Refactor `Parameters` to use `ConfigCheckboxPanel`** — eliminates ~40
   lines of duplicate load/save logic. The strategy dropdown can be passed
   as a `headerSlot?: React.ReactNode` prop.

5. **Extract shared CSS** — move the ~60 duplicated lines from
   `parameters.css` and `indicators.css` into a shared `configpanel.css`.

6. **Wire `useIdleTimeout`** — connect to `AuthProvider` using
   `VITE_IDLE_TIMEOUT_MS`, calling `handleLogout` on idle.

7. **Add `version?: number` to `ParametersConfig` and `IndicatorsConfig`**
   in `api.ts` to align with the API schema.

8. **Declare `ImportMetaEnv` in `vite-env.d.ts`** — eliminates `as string`
   casts on `import.meta.env.VITE_*` accesses.

### Long-term (maintainability)

9. **Add JSDoc to `api.ts` exports** — document expected response shapes and
   error behavior for each function.

10. **Extract WS event type strings to `shared/types/api.ts`** — the monorepo
    already has this file; importing event type constants from it would make
    the frontend's `onmessage` switch type-safe against schema changes.

11. **Remove dead code** — `PrivateRoute` (wire or remove), legacy `App.css`
    styles, `.card` class, `@testing-library/user-event` dependency.

12. **Rename `void error; void info`** to `_error`, `_info` in
    `ErrorBoundary.componentDidCatch` to follow the established
    `argsIgnorePattern` convention.
