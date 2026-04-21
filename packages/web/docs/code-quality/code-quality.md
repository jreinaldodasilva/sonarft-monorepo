# Prompt 10 — Code Quality & JavaScript Best Practices

**Package:** `packages/web`  
**Prompt ID:** 10-WEB-QUALITY  
**Output File:** `docs/code-quality/code-quality.md`  
**Reviewed:** July 2025

---

## Executive Summary

The codebase is in good shape for its size. The code is clean, consistently styled, and follows modern React and TypeScript conventions throughout. There are no `var` declarations, no `console.log` calls in production code, no `dangerouslySetInnerHTML`, no hardcoded secrets, and no circular dependencies. TypeScript strict mode is enabled and respected.

The main quality concerns are: the ESLint configuration is outdated (uses `react-app` preset which is CRA-specific and incompatible with ESLint v9); Prettier has no configuration file (relies on defaults, which may diverge from the code style); `useConfigCheckboxes` has a suppressed `react-hooks/exhaustive-deps` warning and contains complex type assertion chains that reduce readability; and the `ParametersConfig` interface has an index signature that conflicts with its named properties, creating a type safety gap.

The codebase is small (1,765 source lines across all non-test files) and well-organised. No file exceeds 200 lines.

---

## 1. Code Style & Consistency

### ESLint Configuration

ESLint is configured in `package.json`:

```json
"eslintConfig": {
    "extends": ["react-app", "react-app/jest"],
    "rules": {
        "no-console": "warn",
        "no-unused-vars": "warn",
        "react/prop-types": "warn"
    }
}
```

**Issues:**

- **`react-app` preset is CRA-specific** — it depends on `eslint-config-react-app` which is a Create React App package. This project uses Vite. The preset may not be installed or may be a stale dependency. Running `npm run lint` (which calls `eslint src/ --ext .js,.jsx,.ts,.tsx --max-warnings=0`) would fail if `eslint-config-react-app` is not present.

- **ESLint v9 incompatibility** — the project uses the legacy `.eslintrc` format (via `package.json` `eslintConfig` key). ESLint v9 (released 2024) requires `eslint.config.js` flat config format. Running `npx eslint` with the latest version fails with "couldn't find an eslint.config.js file". The project needs to either pin ESLint to v8 or migrate to flat config.

- **`react/prop-types: warn`** — redundant with TypeScript strict mode. PropTypes are not used anywhere in the codebase (correctly, since TypeScript handles type checking). This rule should be disabled.

- **`no-unused-vars: warn`** — TypeScript's own `noUnusedLocals` / `noUnusedParameters` (not enabled in `tsconfig.json`) would be more precise. The ESLint rule may produce false positives with TypeScript.

- **Missing rules** — no `react-hooks/rules-of-hooks` or `react-hooks/exhaustive-deps` rules are explicitly configured. These are critical for React hook correctness. The `react-app` preset includes them, but given the preset compatibility issues, their enforcement is uncertain.

### Prettier

Prettier is listed as a dev dependency (`^3.0.3`) but **no Prettier configuration file exists** — no `.prettierrc`, no `prettier.config.js`, no `prettier` key in `package.json`. Prettier runs with all defaults. The `npm run format` script (`prettier --write "**/*.{js,jsx,ts,tsx}"`) will apply default Prettier formatting, which may not match the existing code style (e.g., default Prettier uses 80-char line width and double quotes — the code already uses double quotes consistently, so this is likely fine).

**Risk:** Without a committed Prettier config, different team members running `npm run format` with different Prettier versions may produce different output.

### Indentation & Style

- **4-space indentation** throughout all TypeScript/TSX files — consistent ✅
- **Double quotes** for all string literals — consistent ✅
- **Semicolons** present on all statements — consistent ✅
- **Trailing commas** in multi-line structures — consistent ✅
- **Arrow functions** used for all callbacks and component definitions — consistent ✅

### Import Organisation

Imports follow a consistent pattern: external libraries first, then internal modules, then CSS:

```ts
// utils/api.ts
import netlifyIdentity from "netlify-identity-widget";  // external
import { HTTP } from "./constants.js";                   // internal
import parameterOptions from "./parameterOptions.json";  // local JSON
```

No import sorting tool (e.g., `eslint-plugin-import`) is configured. Imports are manually ordered but consistently so.

**Minor issue:** `import { HTTP } from "./constants.js"` uses a `.js` extension in a TypeScript file. This works with Vite's module resolution but is unconventional — TypeScript files should import without extension or with `.ts`.

---

## 2. JavaScript Best Practices

### `var` / `let` / `const`

**Zero `var` declarations found.** All variables use `const` or `let` appropriately:
- `const` for values that don't change ✅
- `let` only where reassignment is needed ✅

### Modern JavaScript Features

| Feature | Used? | Assessment |
|---|---|---|
| Arrow functions | ✅ Everywhere | Consistent |
| Template literals | ✅ Used | e.g., `` `${WS}/${clientId}?token=...` `` |
| Destructuring | ✅ Used | e.g., `const { socket, wsOpen, wsError } = useWebSocket(...)` |
| Spread operator | ✅ Used | e.g., `{ ...baseHeaders, ...getAuthHeaders() }` |
| Optional chaining (`?.`) | ✅ Used | e.g., `socket?.send(...)`, `user?.token?.access_token` |
| Nullish coalescing (`??`) | ✅ Used | e.g., `stored ?? "null"`, `msg.message ?? ""` |
| `async`/`await` | ✅ Everywhere | No raw Promise chains |
| `Promise.all` | ✅ Used | Parallel fetch in `helpers.ts` |
| `Object.freeze` | ✅ Used | `BotState`, `BotStatus` constants |
| `as const` | ✅ Used | `ACTIVITY_EVENTS as const` |

All modern JavaScript features are used correctly and consistently. ✅

### Async/Await Error Handling

All async functions use `try/catch`. No unhandled promise rejections found. ✅

---

## 3. React Best Practices

### Functional Components

100% functional components except `ErrorBoundary` (class component required for `componentDidCatch`). ✅

### Hooks Usage

All hooks follow the Rules of Hooks:
- No conditional hook calls ✅
- No hook calls inside loops ✅
- All custom hooks start with `use` ✅

### Key Props in Lists

All list renders use keys:

```tsx
// TradeHistoryTable.tsx
{rows.map((row, index) => (
    <tr key={`${row.timestamp}-${row.buy_exchange}-${index}`}>
```

```tsx
// BotControls.tsx
{botIds.map((botId) => (
    <option key={botId} value={botId}>{botId}</option>
))}
```

```tsx
// Indicators.tsx / Parameters.tsx
{Object.keys(options).map((item) => (
    <li key={item}>
```

**Minor issue — `TradeHistoryTable` key includes `index`:** The key `${row.timestamp}-${row.buy_exchange}-${index}` uses `index` as a tiebreaker. If two rows have the same timestamp and exchange (possible for rapid trades), the index prevents key collisions. However, using index in keys can cause issues with reordering. A stable unique key (e.g., a trade ID from the server) would be preferable. The API's `TradeRecord` schema does not include an `id` field — this is a server-side gap.

### Dependency Arrays

`useEffect` dependency arrays are generally correct. The one suppressed warning:

```ts
// useConfigCheckboxes.ts
}, [clientId]); // eslint-disable-line react-hooks/exhaustive-deps
```

`fetchFn`, `defaultFn`, `updateFn`, and `stateKeys` are missing from the dependency array. This is a known issue documented in Prompts 03 and 05. The suppression is a code smell — it hides a real correctness risk.

### Fragment Shorthand

`<></>` shorthand is used where fragments are needed (e.g., `Crypto.tsx`). ✅

### Component Naming

All components use PascalCase. All hooks use camelCase with `use` prefix. ✅

---

## 4. Error Handling

### `try/catch` Coverage

All async functions in `utils/api.ts` and all hooks use `try/catch`. ✅

### Error Boundary

`ErrorBoundary` is correctly placed in `Crypto.tsx` to catch render errors in the trading interface. ✅

### Promise Rejection

No unhandled promise rejections. All `async` functions either catch errors internally or propagate them to callers that catch them. ✅

### Silent Failures

As documented in Prompts 02 and 07, several error paths are caught but produce no user feedback:

```ts
// useBots.ts — order_success handler
case "order_success":
    setOrders(await fetchAllOrders(botIds));  // if fetchAllOrders throws, error is swallowed
    break;
```

The `onmessage` handler has no outer `try/catch`. If `fetchAllOrders` throws (e.g., network error), the error propagates to the `async` handler and becomes an unhandled promise rejection in the `onmessage` callback context.

**Fix:**
```ts
socket.onmessage = async (event: MessageEvent<string>) => {
    try {
        const msg = parseMessage(event.data);
        // ... switch statement
    } catch (e) {
        setFetchError("Unexpected error processing server message");
    }
};
```

### `void` Operator Usage

```ts
// ErrorBoundary.tsx
componentDidCatch(error: Error, info: ErrorInfo): void {
    void error; void info;
}
```

Using `void` to suppress unused variable warnings is unconventional. The correct approach is to either use the variables (log them) or use `_error` / `_info` naming convention to signal intentional non-use.

---

## 5. Code Organisation

### File Size

| File | Lines | Assessment |
|---|---|---|
| `utils/api.ts` | 184 | ✅ Acceptable |
| `hooks/useBots.ts` | 152 | ✅ Acceptable |
| `hooks/useConfigCheckboxes.ts` | 104 | ✅ Acceptable |
| `components/Indicators/Indicators.tsx` | 100 | ✅ Acceptable |
| `components/Charts/ProfitChart.tsx` | 100 | ✅ Acceptable |
| `hooks/AuthProvider.tsx` | 85 | ✅ Acceptable |
| `components/Parameters/Parameters.tsx` | 85 | ✅ Acceptable |

No file exceeds 200 lines. The codebase is well-sized throughout. ✅

**Total source lines: 1,765** across all non-test TypeScript/TSX files.

### Function Size

No function exceeds 50 lines. The largest functions are:
- `useBots` hook body (~100 lines including state declarations and effects)
- `useConfigCheckboxes` `load` async function (~30 lines)
- `ProfitChart` render function (~40 lines)

All within acceptable bounds. ✅

### Cyclomatic Complexity

The most complex function is the `onmessage` handler in `useBots`:

```ts
socket.onmessage = async (event) => {
    const msg = parseMessage(event.data);
    if (msg.type === "log") { ... return; }
    switch (msg.type) {
        case "bot_created": { ... break; }
        case "bot_removed": { ... break; }
        case "order_success": { ... break; }
        case "trade_success": { ... break; }
        default: break;
    }
};
```

Cyclomatic complexity: ~6 (one path per switch case + the log early return). Acceptable. ✅

### Import Organisation

Imports are consistently ordered: external → internal → CSS. No circular dependencies detected. ✅

### Index Files

No `index.ts` barrel files are used. Components are imported directly by path. This is fine for the current codebase size — barrel files add complexity without benefit at this scale.

---

## 6. Naming Conventions

### Variables & Functions

| Convention | Applied? | Examples |
|---|---|---|
| `camelCase` for variables | ✅ | `botIds`, `wsOpen`, `fetchError` |
| `camelCase` for functions | ✅ | `handleCreate`, `getBotIds`, `parseMessage` |
| `PascalCase` for components | ✅ | `BotControls`, `TradeHistoryTable` |
| `PascalCase` for interfaces | ✅ | `BotsProps`, `UseBotsReturn`, `TradeRecord` |
| `UPPER_SNAKE_CASE` for constants | ✅ | `MAX_LOG_LINES`, `BACKOFF_BASE_MS`, `BACKOFF_MAX_MS` |
| `use` prefix for hooks | ✅ | `useBots`, `useWebSocket`, `useConfigCheckboxes` |
| `on` prefix for event handlers | ✅ | `onCreate`, `onRemove`, `onSelectBot` |
| `handle` prefix for internal handlers | ✅ | `handleCreate`, `handleRemove`, `handleLogin` |

### Boolean Naming

Boolean state variables and props use descriptive names but not consistently prefixed with `is`/`has`:

| Variable | Has `is`/`has` prefix? |
|---|---|
| `wsOpen` | ❌ (should be `isWsOpen`) |
| `isLoading` | ✅ |
| `isSimulating` | ✅ |
| `autoReconnect` | ❌ (should be `autoReconnect` is fine as an adjective) |
| `enabled` (useIdleTimeout) | ❌ (should be `isEnabled`) |

Minor inconsistency — not a significant issue.

### Magic Values

Named constants are used for all significant magic values:

```ts
const MAX_LOG_LINES = 500;          // useBots.ts
const BACKOFF_BASE_MS = 1000;       // useWebSocket.tsx
const BACKOFF_MAX_MS = 30000;       // useWebSocket.tsx
const SAVE_FEEDBACK_MS = 3000;      // useConfigCheckboxes.ts
const IDLE_TIMEOUT_MS = parseInt(import.meta.env.VITE_IDLE_TIMEOUT_MS ?? "1800000", 10);
```

**Remaining magic values not extracted:**
- `180000` (CoinGecko poll interval in `CryptoTicker.tsx`) — should be `const COINGECKO_POLL_MS = 180_000`
- `270s` (ticker animation duration in `cryptoticker.css`) — should be a CSS variable
- `300px` (console height in `bots.css`) — should be a CSS variable
- `200px` (table max-height in `bots.css`) — should be a CSS variable

---

## 7. Documentation & Comments

### README

A comprehensive `README.md` exists at the package level. ✅

### Code Comments

Comments are minimal and purposeful — the code is largely self-documenting. Section banners (`// ### Types ###`, `// ### Auth helpers ###`, `// ### Bot endpoints ###`) in `api.ts` improve navigation. ✅

### JSDoc

No JSDoc comments on any function. For a small codebase with TypeScript interfaces, this is acceptable — the TypeScript types serve as documentation. The one area that would benefit from a comment is the `useConfigCheckboxes` three-tier loading logic, which is non-obvious.

### `eslint-disable` Comments

Two suppressed warnings:

```ts
// vitals.ts — intentional console.log in dev mode
// eslint-disable-next-line no-console
console.log(`[Web Vitals] ${metric.name}: ...`);
```
✅ Justified — this is a deliberate dev-mode log.

```ts
// useConfigCheckboxes.ts — missing deps
}, [clientId]); // eslint-disable-line react-hooks/exhaustive-deps
```
⚠️ Not justified — this suppresses a real correctness warning. Should be fixed, not suppressed.

### TODO / FIXME Comments

**Zero TODO/FIXME comments found.** The codebase has no tracked technical debt markers. This is either very clean code or untracked debt — given the findings across all prompts, it is likely the latter. Key known issues (broken simulation toggle, missing `botid` in WS command, stale test URLs) are not marked with TODOs.

---

## 8. Performance Anti-patterns

### Inline Functions in JSX Props

Three instances of inline arrow functions in JSX props:

```tsx
// BotControls.tsx
onChange={(e) => onSelectBot(e.target.value)}

// Parameters.tsx / Indicators.tsx
onChange={(e) => handleCheckboxChange(e, category)}
```

The `BotControls` instance creates a new function on every render. Since `BotControls` is not wrapped in `React.memo`, this is harmless — the component re-renders anyway. If `React.memo` is added (recommended in Prompt 08), this inline function would defeat the memoization for the `onChange` prop. It should be extracted to a `useCallback`.

The `Parameters`/`Indicators` instances are inside `renderCheckboxes` which is called per category. The `category` value is a string constant — the inline function is stable in practice but not in reference. Same recommendation applies.

### Inline Objects in Props

No inline object literals passed as props were found. ✅

### Inline Styles

No inline `style={{}}` props found. All styling uses CSS classes. ✅

### Missing Keys

All list renders have keys. ✅ (See Section 3 for the `index`-in-key minor issue.)

### Large Library Imports

As documented in Prompt 08, the Redux stack and `axios` are bundled despite being unused. These are the primary performance anti-patterns in the codebase.

### Polling vs WebSocket

`CryptoTicker` uses polling (every 3 minutes) for CoinGecko prices — appropriate since CoinGecko does not offer a WebSocket API for free-tier users. The sonarft backend uses WebSocket for real-time events — correct. No inappropriate polling detected. ✅

---

## 9. Security Anti-patterns

### Hardcoded Secrets

**None found.** No API keys, tokens, or credentials are hardcoded in source files. ✅

### `eval` / `Function` Constructor

**Not used anywhere.** ✅

### `dangerouslySetInnerHTML`

**Not used anywhere.** ✅

### Credential Exposure

The `DEV_USER` object in `AuthProvider.tsx` contains a hardcoded `access_token: "dev-token"`. This is a development-only value gated by `VITE_DEV_AUTH_BYPASS === "true"` — it is not a real credential and poses no security risk. ✅

### Input Validation

As documented in Prompt 06, the application has minimal user text input. All config values come from checkboxes (boolean), bot IDs come from the server, and URL parameters are `encodeURIComponent`-encoded. ✅

### Dependencies

As documented in Prompt 06: 1 Critical, 6 High, 4 Moderate vulnerabilities — all fixable. The most impactful fix is removing `axios`.

---

## 10. Maintainability Issues

### Dead Code

Dead code identified across prompts:

| Dead code | Location | Action |
|---|---|---|
| `pages/Dex/`, `pages/Forex/`, `pages/Token/` | `src/pages/` | Remove or add routes |
| `components/Building/`, `components/CChatGPT/`, `components/DoggyWelcome/` | `src/components/` | Remove |
| `App.css` CRA template styles | `src/App.css` | Remove |
| `public/index.html` CRA template | `public/` | Remove |
| `.env.production.example` with `REACT_APP_*` | root | Fix or remove |
| `welcome2-container` CSS class | `home.css` | Remove |
| `.indicatorsList`, `.parametersList` CSS classes | component CSS | Remove |

### Code Duplication

`Parameters.tsx` and `Indicators.tsx` are ~85% identical. As documented in Prompt 04, a single `ConfigCheckboxPanel` component would eliminate ~120 lines of duplication.

The `SAVE_MESSAGES` constant is defined identically in both files:
```ts
const SAVE_MESSAGES: Record<string, string> = {
    saving: "Saving...", saved: "✓ Saved", error: "✗ Error — try again",
};
```
This should be a shared constant in `utils/constants.ts`.

### Tight Coupling

`useBots` is tightly coupled to the WebSocket message format. If the server adds a new event type, `useBots` must be updated. This is unavoidable given the architecture, but the switch statement is the correct pattern for this coupling — it makes the coupling explicit and easy to extend.

### Circular Dependencies

None detected. ✅

### Mixed Concerns

`useBots` mixes WebSocket message handling, REST fetching, bot lifecycle state, and simulation mode in a single hook. As documented in Prompt 03, splitting into `useBotLifecycle` and `useTradeHistory` would improve separation of concerns.

---

## 11. Specific Code Smells

### `useConfigCheckboxes` — Complex Type Assertion Chain

The most complex code in the codebase:

```ts
const next = {} as T;
stateKeys.forEach((k) => {
    (next as ConfigState)[k as string] = (data as ConfigState)[k as string];
});
```

This pattern appears three times in the `load` function. The `as T`, `as ConfigState`, `as string` chain is a sign that the generic type `T extends ConfigState` is fighting TypeScript's type system. The root cause is that TypeScript cannot narrow `T` to `ConfigState` even though the constraint `T extends ConfigState` is declared.

A cleaner approach using `Object.fromEntries`:
```ts
const next = Object.fromEntries(
    stateKeys.map(k => [k, (data as ConfigState)[k as string]])
) as T;
```

Or restructure the generic to avoid the need for casting entirely by using `Pick<T, keyof T>`.

### `ParametersConfig` Index Signature Conflict

```ts
export interface ParametersConfig {
    [key: string]: Record<string, boolean>;  // ← index signature
    exchanges: Record<string, boolean>;
    symbols: Record<string, boolean>;
}
```

The index signature `[key: string]: Record<string, boolean>` means any string key is valid on `ParametersConfig`. This defeats TypeScript's ability to catch typos like `config.exchnages` — it would return `undefined` (typed as `Record<string, boolean>`) rather than a type error. The index signature should be removed; the named properties are sufficient.

### `BotState` Enum-like Object

```ts
export const BotState = Object.freeze({ CREATED: 0, REMOVED: 1 });
```

`CREATED: 0` is never used — only `REMOVED: 1` is checked. The `CREATED` value was likely intended for a "bot is being created" state but was never implemented. This is dead code within the constant.

### `Crypto.tsx` — Redundant Auth Guard

```tsx
if (!user) return <PrivateRoute value={null}><></></PrivateRoute>;
```

This renders `PrivateRoute` with `value={null}` and an empty fragment as children, which immediately redirects to `/`. The `PrivateRoute` wrapper is unnecessary — a direct `return <Navigate to="/" />` would be clearer and more honest about intent.

### `Header.tsx` — One-line Wrapper

```tsx
const Header: React.FC = () => (
    <div className="header"><NavBar /></div>
);
```

This component exists solely to add a `<div className="header">` wrapper. The wrapper could be moved into `NavBar.tsx` or `App.tsx`, eliminating an unnecessary file and import.

---

## 12. Type Safety (TypeScript)

### TypeScript Configuration

```json
{
    "compilerOptions": {
        "strict": true,
        "target": "es6",
        "noEmit": true,
        "jsx": "react-jsx"
    }
}
```

`strict: true` enables: `strictNullChecks`, `strictFunctionTypes`, `strictBindCallApply`, `strictPropertyInitialization`, `noImplicitAny`, `noImplicitThis`, `alwaysStrict`. ✅

**Missing strict options:**
- `noUnusedLocals: true` — would catch unused variables at compile time
- `noUnusedParameters: true` — would catch unused function parameters
- `exactOptionalPropertyTypes: true` — stricter optional property handling

### `any` Type Usage

**Zero `any` type annotations found in production source code.** ✅

All type assertions use specific types (`as string[]`, `as TradeRecord[]`, `as ParametersConfig`). The only `as` casts are for:
1. API response deserialization (unavoidable without runtime validation)
2. Netlify Identity widget types (third-party library with incomplete types)
3. The `useConfigCheckboxes` generic type assertions (code smell, documented above)

### Type Coverage

Estimated type coverage: **~95%+** — all function signatures, props, state, and return types are explicitly typed. The only untyped areas are the `as` cast assertions which bypass the type system at specific points.

### Third-party Type Definitions

- `@types/react`, `@types/react-dom`, `@types/node` — installed ✅
- `netlify-identity-widget` — no `@types` package; types are cast manually in `AuthProvider.tsx` and `api.ts` ⚠️
- `recharts` — ships its own types ✅

### Type Errors

No TypeScript compilation errors (Vite build succeeds). ✅

---

## 13. Build & Tooling

### Build Configuration

`vite.config.js` is minimal and correct:
```js
export default defineConfig({
    plugins: [react()],
    envPrefix: "VITE_",
    server: { port: 3000, open: false },
    build: { outDir: "build", sourcemap: false },
    test: { globals: true, environment: "jsdom", setupFiles: "./src/setupTests.ts", css: false },
});
```

**Missing:**
- `build.chunkSizeWarningLimit` — default is 500KB; the 379KB and 339KB chunks do not trigger warnings
- `build.rollupOptions.output.manualChunks` — no vendor chunk splitting

### Development Server

Port 3000 configured. `open: false` — does not auto-open browser. Reasonable defaults. ✅

### Environment Variables

`envPrefix: "VITE_"` correctly restricts which env vars are exposed to the client bundle. ✅

The `.env.production` file uses `REACT_APP_*` prefixes — a critical misconfiguration documented in Prompt 06.

### Linting in CI

No CI pipeline. `npm run lint` uses `--max-warnings=0` which would fail on any warning — but the ESLint config is incompatible with ESLint v9, so the lint script itself fails before checking any code.

### Formatting

`npm run format` runs Prettier with no config file — uses defaults. No pre-commit hook enforces formatting.

### Package Manager Inconsistency

Both `package-lock.json` (npm) and `yarn.lock` (yarn) are committed. The Dockerfile uses `npm ci`. The project should commit to one package manager and remove the other lock file.

---

## 14. Code Quality Metrics

| Metric | Value | Assessment |
|---|---|---|
| Total source lines (non-test) | 1,765 | Small, well-sized |
| Largest file | `utils/api.ts` (184 lines) | ✅ Under 200 |
| `var` declarations | 0 | ✅ |
| `console.log` in production code | 0 | ✅ |
| `any` type annotations | 0 | ✅ |
| `dangerouslySetInnerHTML` | 0 | ✅ |
| `eslint-disable` suppressions | 2 | ⚠️ 1 unjustified |
| TODO/FIXME comments | 0 | ⚠️ Untracked debt |
| Circular dependencies | 0 | ✅ |
| Runtime dependencies | 20 | ⚠️ ~8 unused |
| Dev dependencies | 13 | ✅ |
| Test pass rate | 51/82 (62%) | ❌ 31 failing |
| Estimated line coverage | ~35-45% | ❌ Below 80% target |
| Bundle size (gzip) | ~229KB JS | ⚠️ Above 100KB target |
| npm audit vulnerabilities | 1 Critical, 6 High, 4 Moderate | ❌ Needs fixing |

---

## 15. Code Quality Issues Summary

| # | Issue | Type | Severity | Occurrences | Remediation |
|---|---|---|---|---|---|
| 1 | ESLint config uses `react-app` preset (CRA-specific, incompatible with ESLint v9) | Tooling | **High** | 1 | Migrate to ESLint flat config with `@eslint/js` + `eslint-plugin-react` + `eslint-plugin-react-hooks` |
| 2 | `eslint-disable-line react-hooks/exhaustive-deps` in `useConfigCheckboxes` | Code smell | **Medium** | 1 | Fix missing deps; wrap `fetchFn`/`defaultFn`/`updateFn` in `useCallback` at call sites |
| 3 | `ParametersConfig` index signature defeats type safety | TypeScript | **Medium** | 1 | Remove `[key: string]: Record<string, boolean>` index signature |
| 4 | `useConfigCheckboxes` complex `as T` / `as ConfigState` / `as string` chain | Code smell | **Medium** | 3 | Refactor using `Object.fromEntries` or restructure generic |
| 5 | `Parameters` and `Indicators` are ~85% duplicate code | Duplication | **Medium** | 2 files | Extract `ConfigCheckboxPanel` component |
| 6 | `SAVE_MESSAGES` constant duplicated in `Parameters` and `Indicators` | Duplication | **Low** | 2 | Move to `utils/constants.ts` |
| 7 | `onmessage` handler has no outer `try/catch` — async errors become unhandled rejections | Error handling | **Medium** | 1 | Wrap handler body in `try/catch` |
| 8 | `void error; void info` in `ErrorBoundary.componentDidCatch` | Code smell | **Low** | 1 | Use `_error`/`_info` naming or log the error |
| 9 | `Crypto.tsx` redundant `PrivateRoute` usage | Code smell | **Low** | 1 | Replace with `<Navigate to="/" />` |
| 10 | `Header.tsx` one-line wrapper component | Code smell | **Low** | 1 | Inline into `App.tsx` or `NavBar.tsx` |
| 11 | `BotState.CREATED` value is never used | Dead code | **Low** | 1 | Remove or implement the CREATING state |
| 12 | No Prettier config file | Tooling | **Low** | 1 | Add `.prettierrc` with explicit settings |
| 13 | Both `package-lock.json` and `yarn.lock` committed | Tooling | **Low** | 1 | Pick one package manager, remove the other lock file |
| 14 | `import { HTTP } from "./constants.js"` — `.js` extension in TS file | Style | **Low** | 1 | Remove extension or use `.ts` |
| 15 | `noUnusedLocals`/`noUnusedParameters` not enabled in `tsconfig.json` | TypeScript | **Low** | 1 | Add to `tsconfig.json` |
| 16 | Zero TODO/FIXME comments despite known issues | Documentation | **Low** | — | Add TODO comments for known issues (broken simulation toggle, stale test URLs, etc.) |

---

## 16. Recommendations

**Priority 1 — Fix tooling**

1. **Migrate ESLint to flat config** — create `eslint.config.js`:
   ```js
   import js from "@eslint/js";
   import reactPlugin from "eslint-plugin-react";
   import reactHooksPlugin from "eslint-plugin-react-hooks";
   import tsPlugin from "@typescript-eslint/eslint-plugin";
   import tsParser from "@typescript-eslint/parser";

   export default [
       js.configs.recommended,
       {
           plugins: { react: reactPlugin, "react-hooks": reactHooksPlugin, "@typescript-eslint": tsPlugin },
           rules: {
               "no-console": "warn",
               "react-hooks/rules-of-hooks": "error",
               "react-hooks/exhaustive-deps": "warn",
               "react/prop-types": "off",  // TypeScript handles this
           }
       }
   ];
   ```

2. **Add `.prettierrc`** with explicit settings to prevent formatting drift:
   ```json
   { "semi": true, "singleQuote": false, "tabWidth": 4, "trailingComma": "es5", "printWidth": 100 }
   ```

3. **Remove `yarn.lock`** — the Dockerfile uses `npm ci`; commit to npm.

**Priority 2 — Fix code quality**

4. **Fix `useConfigCheckboxes` exhaustive-deps** — remove the `eslint-disable` comment and fix the missing dependencies.

5. **Remove `ParametersConfig` index signature** — replace with explicit named properties only.

6. **Extract `ConfigCheckboxPanel`** — eliminate the `Parameters`/`Indicators` duplication.

7. **Add outer `try/catch` to `useBots` `onmessage` handler**.

**Priority 3 — TypeScript strictness**

8. **Add to `tsconfig.json`:**
   ```json
   "noUnusedLocals": true,
   "noUnusedParameters": true
   ```

9. **Add `build.chunkSizeWarningLimit: 100`** to `vite.config.js`.

**Priority 4 — Housekeeping**

10. **Add TODO comments** for all known issues so they are tracked in the codebase.

11. **Remove dead code** — unused pages, components, CSS classes, and the `BotState.CREATED` value.

12. **Inline `Header.tsx`** into `App.tsx` — remove the one-line wrapper.
