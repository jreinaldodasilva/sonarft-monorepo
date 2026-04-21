# Prompt 06 — Authentication, Security & Data Protection

**Package:** `packages/web`  
**Prompt ID:** 06-WEB-SECURITY  
**Output File:** `docs/security/auth-and-security.md`  
**Reviewed:** July 2025  
**API Sources:** `packages/api` included — server-side auth contracts verified

---

## Executive Summary

The application has a reasonable security baseline for a development-stage trading tool. React's default JSX escaping prevents XSS from rendered data, a Content Security Policy is present in both HTML files, security headers are set server-side by the API, and auth tokens are never written to `localStorage` by the frontend code.

However, there are several issues that must be resolved before production deployment:

- **Critical:** `form-data` dependency has a critical vulnerability (unsafe random boundary — GHSA-fjxv-7rqg-78g4)
- **High:** React Router has an XSS-via-open-redirect vulnerability (GHSA-2w69-qvjg-hvjx, GHSA-9jcx-v3wj-wh4m) — all fixes are available
- **High:** JWT passed as WebSocket query parameter — exposed in server logs and browser history
- **High:** CSP in `index.html` (Vite entry point) includes `http://localhost:8000` and `ws://localhost:8000` — these development origins must not reach production
- **Medium:** `.env.production` uses stale `REACT_APP_*` variable names — the production build will silently use localhost fallbacks
- **Medium:** `nginx.conf` sets no security headers — the API's security headers do not apply to the static frontend served by nginx

---

## 1. Authentication & Token Management

### Token Type

Netlify Identity JWT (RS256, signed by Netlify's JWKS endpoint). The token contains standard JWT claims including `sub` (user ID), `email`, and `exp` (expiration).

### Token Storage

**In-memory only** — the JWT is never written to `localStorage` or `sessionStorage` by the frontend code. It lives exclusively in the `netlify-identity-widget`'s internal state. This is the most secure storage option for a browser application — tokens in memory are not accessible to other origins or persistent across sessions unless Netlify Identity itself persists them.

Netlify Identity does persist its session internally (likely via `localStorage` under its own key namespace), but this is managed by the widget, not by application code. The application never reads or writes auth tokens directly to browser storage.

### Token Retrieval

```ts
export const getAuthToken = (): string | null => {
    const user = netlifyIdentity.currentUser() as { token?: { access_token?: string } } | null;
    return user?.token?.access_token ?? null;
};
```

Called on demand before each API request and once at `useBots` render time for the WebSocket URL. The on-demand pattern for REST calls is correct — it always retrieves the current token. The render-time call for the WebSocket URL is the stale-token risk documented in Prompts 02 and 05.

### Token Lifetime & Refresh

Netlify Identity JWTs expire after 1 hour by default. The widget handles refresh internally. The frontend has no explicit refresh logic — if the token expires mid-session, the next API call will receive a 401, which is thrown as an error but not caught to trigger re-authentication. The user would need to manually log out and back in.

### Token Transmission

- **REST API:** `Authorization: Bearer <token>` header — correct, not in URL
- **WebSocket:** `?token=<JWT>` query parameter — **insecure**, documented as High severity

### Token Revocation

No client-side revocation mechanism. Netlify Identity tokens are stateless JWTs — they cannot be revoked server-side before expiry. The idle timeout (`useIdleTimeout`) provides a compensating control by logging the user out after 30 minutes of inactivity.

---

## 2. Login / Logout Flow

### Login

```
User clicks "Sign In" (NavBar)
  → handleLogin() → netlifyIdentity.open()
  → Netlify Identity modal opens
  → User enters credentials (handled entirely by Netlify Identity widget)
  → netlifyIdentity.on("login") fires → setUser(user)
  → AuthContext updates → NavBar shows "Sign Out"
  → Crypto page re-renders with user.id
```

Credentials are submitted directly to Netlify's servers by the widget — the application never sees the password. This is correct.

### Session Persistence on Reload

```ts
const currentUser = netlifyIdentity.currentUser() as NetlifyUser | null;
if (currentUser) setUser(currentUser);
```

On mount, `AuthProvider` checks for an existing Netlify Identity session. If one exists (widget has a stored session), the user is restored without re-authentication. This is the expected behaviour.

### Logout

```ts
const handleLogout = useCallback(() => {
    if (DEV_AUTH_BYPASS) return;
    netlifyIdentity.logout();
}, []);
```

`netlifyIdentity.logout()` clears the Netlify Identity session and fires the `logout` event, which sets `user` to `null` in `AuthContext`. The WebSocket connection is not explicitly closed on logout — it will remain open until the next reconnect attempt fails auth, or until the component unmounts.

**Gap:** On logout, the WebSocket connection should be explicitly closed. Currently, the bot continues running and streaming logs to the disconnected-but-still-open WebSocket until the component unmounts or the connection drops naturally.

### Dev Auth Bypass

```ts
const DEV_AUTH_BYPASS = import.meta.env.VITE_DEV_AUTH_BYPASS === "true";
const DEV_USER: NetlifyUser = {
    id: "dev_user",
    email: "dev@localhost",
    token: { access_token: "dev-token" },
};
```

When `VITE_DEV_AUTH_BYPASS=true` (set in `.env.development`), a hardcoded dev user is injected and all auth operations are no-ops. This is a clean pattern for development. The `"dev-token"` value is sent as a Bearer token to the API, which passes it through in dev mode (no auth configured).

**Risk:** If `VITE_DEV_AUTH_BYPASS=true` were accidentally set in a production build, authentication would be completely bypassed. The Dockerfile does not pass this variable as a build arg, so it would only be active if explicitly set — but there is no build-time assertion that it is `false` in production.

---

## 3. Authorization & Access Control

### Protected Routes

Only the `/crypto` route requires authentication. The guard is implemented in `Crypto.tsx`:

```tsx
const Crypto: React.FC = () => {
    const { user } = useContext(AuthContext);
    if (!user) return <PrivateRoute value={null}><></></PrivateRoute>;
    // ...
};
```

This redirects unauthenticated users to `/`. The `PrivateRoute` component is also used here, but redundantly — `Crypto` already handles the `!user` case before `PrivateRoute` is reached. See Prompt 01 Finding #12.

### Role-Based Access Control

**No RBAC.** All authenticated users have identical permissions. There is no concept of admin vs regular user, read-only vs read-write, or per-bot ownership beyond the `client_id` scoping.

### Server-Side Authorization

The API enforces authorization correctly:
- In Netlify JWT mode: `client_id` is derived from the JWT `sub` claim — users cannot impersonate other clients
- In static token mode: `client_id` is a query parameter — any caller with the token can use any `client_id`
- Bot operations validate that the `botid` belongs to the requesting `client_id` (via `BotService`)

### Client-Side Authorization Checks

The only client-side check is the `!user` guard in `Crypto.tsx`. There are no client-side role checks — correct, since client-side checks are not a security boundary.

---

## 4. HTTPS / TLS

### Production Configuration

`.env.production` specifies:
```
REACT_APP_API_URL=https://api.sonarft.com
REACT_APP_WS_URL=wss://api.sonarft.com/ws
```

**Critical issue:** These use `REACT_APP_*` prefixes (Create React App convention). The current build tool is Vite, which requires `VITE_*` prefixes. These variables will be silently ignored by Vite. The production build will fall back to the hardcoded defaults in `constants.ts`:
```ts
export const HTTP: string = (import.meta.env.VITE_API_URL as string) ?? "http://localhost:8000/api/v1";
export const WS: string = (import.meta.env.VITE_WS_URL as string) ?? "ws://localhost:8000/api/v1/ws";
```

**A production build will connect to `http://localhost:8000` over plain HTTP.** This is a critical misconfiguration that would expose all API traffic unencrypted and fail to connect in any real deployment.

### HSTS

The API sets `Strict-Transport-Security: max-age=31536000; includeSubDomains` via `SecurityHeadersMiddleware`. This applies to API responses only. The nginx server serving the frontend does not set HSTS — see Section 10.

### Mixed Content

If the frontend is served over HTTPS but the API URL falls back to `http://localhost:8000` (due to the `.env.production` misconfiguration), all API calls will be blocked by the browser as mixed content.

### WebSocket Security

`wss://` (WebSocket Secure) is specified in `.env.production` but will not be used due to the `REACT_APP_*` prefix issue. The fallback is `ws://` (unencrypted).

---

## 5. XSS (Cross-Site Scripting) Prevention

### React's Default Escaping

React escapes all JSX expressions by default. String values rendered in JSX are HTML-entity-encoded before insertion into the DOM. This prevents the vast majority of XSS vectors from API responses or WebSocket messages.

### `dangerouslySetInnerHTML`

**Not used anywhere in the codebase.** No components bypass React's escaping.

### User Input Rendering

The only user-controlled data rendered in the UI comes from:

1. **WebSocket log messages** — rendered in `BotConsole`:
   ```tsx
   <pre className="console">{logs.join("\n")}</pre>
   ```
   Log content is rendered as text inside `<pre>` — React escapes it. No XSS risk.

2. **Trade history data** — rendered in `TradeHistoryTable`:
   ```tsx
   <td>{row.timestamp}</td>
   <td>{row.position}</td>
   ```
   All fields are rendered as text children — React escapes them. No XSS risk.

3. **Bot IDs** — rendered in `BotControls` select options:
   ```tsx
   <option key={botId} value={botId}>{botId}</option>
   ```
   React escapes option text. No XSS risk.

4. **Error messages** — `fetchError` and `wsError` are set from hardcoded strings in the frontend code, not from server responses. No XSS risk.

5. **`ErrorBoundary` error detail** — in dev mode only:
   ```tsx
   {import.meta.env.DEV && (
       <pre className="error-boundary__detail">
           {this.state.error?.message}
       </pre>
   )}
   ```
   Rendered as text inside `<pre>` — React escapes it. Only shown in dev mode. No XSS risk.

### React Router XSS Vulnerability (GHSA-2w69-qvjg-hvjx)

`react-router-dom` ^6.30.3 is vulnerable to XSS via open redirects. An attacker can craft a URL that causes React Router to redirect to an external site, potentially enabling phishing or token theft. **Fix is available** — update to the patched version.

### Content Security Policy

A CSP is defined in both `public/index.html` (CRA legacy) and `index.html` (Vite entry point):

```html
<meta http-equiv="Content-Security-Policy" content="
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data:;
  font-src 'self';
  connect-src 'self'
    http://localhost:8000
    ws://localhost:8000
    https://api.coingecko.com
    https://*.netlify.com
    https://*.netlify.app;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
" />
```

**Strengths:**
- `default-src 'self'` — blocks all external resources by default
- `script-src 'self'` — no inline scripts, no `unsafe-eval`
- `frame-ancestors 'none'` — prevents clickjacking
- `base-uri 'self'` — prevents base tag injection
- `form-action 'self'` — prevents form hijacking

**Issues:**
- `style-src 'unsafe-inline'` — allows inline styles, which could be exploited for CSS injection attacks. Required for the current plain CSS approach but worth noting.
- `http://localhost:8000` and `ws://localhost:8000` are in `connect-src` — these development origins must be removed for production. If the CSP is served as-is in production, it allows connections to localhost (harmless but sloppy) and does not include the actual production API URL (which would block all API calls).
- The CSP is delivered via `<meta>` tag, not an HTTP header. `<meta>` CSP does not support `frame-ancestors` — that directive is silently ignored when delivered via meta tag. It must be set as an HTTP response header to be effective.
- `public/index.html` uses `%PUBLIC_URL%` template syntax (CRA) — this file is not used by Vite and should be removed to avoid confusion.

---

## 6. CSRF (Cross-Site Request Forgery) Prevention

### Token-Based Auth (CSRF-Resistant by Design)

The application uses `Authorization: Bearer <token>` headers for all REST API calls. Bearer token authentication is inherently CSRF-resistant because:
- Browsers do not automatically attach `Authorization` headers to cross-origin requests
- A malicious site cannot read the token from memory (same-origin policy)
- No cookies are used for authentication

### WebSocket CSRF

WebSocket connections are not subject to the same CSRF risks as form submissions. The `Origin` header is sent by the browser on WebSocket upgrade requests and can be validated server-side. The API's CORS configuration (`allow_origins`) provides this protection.

### Form Submissions

The config forms (`Parameters`, `Indicators`) submit data via `fetch` with `Authorization` headers — not via HTML form submission. No CSRF tokens are needed.

**Assessment:** CSRF is not a practical concern for this application given the Bearer token auth model.

---

## 7. Sensitive Data Handling

### Auth Tokens

- Never written to `localStorage` or `sessionStorage` by application code ✅
- Never logged to the console ✅
- Passed in `Authorization: Bearer` header for REST calls ✅
- **Passed as `?token=<JWT>` in WebSocket URL** — exposed in server logs ❌

### API Keys / Credentials

No API keys, exchange credentials, or secrets are present in the frontend source code. The trading bot's exchange API keys are managed server-side only.

### PII

The only PII handled by the frontend is the user's email address (from `NetlifyUser.email`), which is:
- Stored in `AuthContext` in-memory state
- Never written to `localStorage` by application code
- Never sent to any endpoint other than Netlify Identity (handled by the widget)
- Not logged or displayed in error messages

### Error Messages

API error response bodies (`detail` field) are never read or displayed — the frontend only shows the HTTP status code. This prevents server-side error details from leaking to the UI. However, it also means users see unhelpful generic errors (see Prompt 02).

### `ErrorBoundary` Error Detail

```tsx
{import.meta.env.DEV && (
    <pre className="error-boundary__detail">
        {this.state.error?.message}
    </pre>
)}
```

Error details are only shown in development mode (`import.meta.env.DEV`). In production builds, Vite sets `DEV` to `false`, so this block is excluded from the production bundle entirely (dead code elimination). ✅

### Web Vitals Reporting

`sendVitals` sends performance metrics (CLS, FID, FCP, LCP, TTFB) to `VITE_VITALS_URL` if configured. The payload includes `window.location.href` — this could expose URL parameters (e.g., if a token were ever placed in the URL). Currently no tokens appear in URLs except the WebSocket `?token=` parameter, which is not a page URL. Low risk, but worth noting.

### `localStorage` Contents

Only config data is stored in `localStorage`:
- `"parametersState"` — exchange names and symbol pairs (e.g., `{"exchanges":{"Binance":true}}`)
- `"indicatorsState"` — indicator names and periods

No tokens, no PII, no financial data. ✅

---

## 8. Data Privacy

### Data Collected

| Data | Where stored | Retention |
|---|---|---|
| User email + Netlify user ID | Netlify Identity (external) | Per Netlify's policy |
| Auth JWT | In-memory (Netlify widget) | Session duration |
| Config preferences | `localStorage` | Indefinite (no expiry) |
| Trade/order history | Server-side JSON files | Indefinite |
| Web Vitals metrics | External endpoint (if configured) | Per endpoint policy |

### Third-Party Data Sharing

- **Netlify Identity** — handles authentication; receives user credentials
- **CoinGecko API** — receives the user's IP address on every price fetch (unauthenticated public API)
- **Web Vitals endpoint** — receives performance metrics including `window.location.href` (if `VITE_VITALS_URL` is configured)

### Analytics / Tracking

No analytics library (Google Analytics, Mixpanel, etc.) is present. No tracking pixels or third-party scripts beyond Netlify Identity.

### Privacy Policy

No privacy policy is present in the application. For a production deployment handling user accounts and financial data, a privacy policy is required in most jurisdictions.

---

## 9. Input Validation & Sanitization

### Config Forms (Parameters / Indicators)

The config forms use checkboxes only — boolean values. There is no free-text user input in these forms. The checkbox keys come from the server's own response data, not from user-typed input. No client-side validation is needed or missing here.

### Bot ID Selection

Bot IDs are selected from a dropdown populated by the server's `getBotIds` response. Users cannot type arbitrary bot IDs. The server validates bot IDs with a regex (`^[a-zA-Z0-9_-]{1,64}$`) before processing commands.

### WebSocket Commands

Client-to-server WebSocket messages are constructed from controlled values (hardcoded keys, server-provided bot IDs). No user-typed text is included in WS commands.

### URL Parameters

`clientId` and `botId` values are passed through `encodeURIComponent` before insertion into query strings — correct.

**Assessment:** The application has minimal user text input, which significantly reduces the input validation surface. The existing validation is appropriate.

---

## 10. API Communication Security

### REST API

- All calls use `fetch` with `Authorization: Bearer` header ✅
- `Content-Type: application/json` set on all requests ✅
- No credentials in URL parameters (except `client_id`, which is not a secret) ✅
- Response data is cast with TypeScript assertions — no runtime validation ⚠️

### WebSocket

- JWT in query parameter — High severity ❌
- No message signing or integrity verification ⚠️

### Rate Limiting

The API implements rate limiting via `slowapi`:
- `GET /bots`: 60/minute
- `POST /bots`: 10/minute
- `PUT /parameters`, `PUT /indicators`: 30/minute

The frontend has no client-side rate limiting or debouncing on API calls. Rapid user interactions (e.g., clicking Save repeatedly) can generate bursts of requests up to the server's rate limit.

### nginx Security Headers

The `nginx.conf` serving the production frontend sets only caching headers — **no security headers**:

```nginx
server {
    listen 80;
    # ... only cache headers, no security headers
}
```

Missing headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Strict-Transport-Security`
- `Content-Security-Policy` (as HTTP header, not meta tag)
- `Permissions-Policy`

The API sets these headers via `SecurityHeadersMiddleware`, but they apply only to API responses — not to the static HTML/JS/CSS served by nginx.

---

## 11. Dependency Security

### npm audit Results

| Package | Severity | Vulnerability | Fix Available |
|---|---|---|---|
| `form-data` | **Critical** | Unsafe random boundary generation (GHSA-fjxv-7rqg-78g4) | ✅ Yes |
| `@remix-run/router` | **High** | XSS via open redirects (GHSA-2w69-qvjg-hvjx) | ✅ Yes |
| `react-router` | **High** | Unexpected external redirect (GHSA-9jcx-v3wj-wh4m) | ✅ Yes |
| `braces` | **High** | Uncontrolled resource consumption (GHSA-grv7-fg5c-xmjg) | ✅ Yes |
| `lodash` | **High** | Prototype pollution in `_.unset`/`_.omit` (×3 advisories) | ✅ Yes |
| `picomatch` | **High** | Method injection + ReDoS (×2 advisories) | ✅ Yes |
| `@adobe/css-tools` | Moderate | ReDoS while parsing CSS (×2 advisories) | ✅ Yes |
| `@babel/runtime` | Moderate | Inefficient RegExp in named capturing groups | ✅ Yes |
| `follow-redirects` | Moderate | Auth header leakage + URL parsing (×3 advisories) | ✅ Yes |
| `micromatch` | Moderate | ReDoS (GHSA-952p-6rrq-rcjv) | ✅ Yes |

**Total: 1 Critical, 6 High, 4 Moderate — all fixes available.**

### Risk Assessment

- `form-data` (Critical) and `follow-redirects` (Moderate) are transitive dependencies of `axios`. Since `axios` is only used in `CryptoTicker` for unauthenticated CoinGecko calls, the practical risk is low — but the vulnerabilities are real and the fix is to remove `axios` entirely.
- `react-router` / `@remix-run/router` (High) are direct dependencies. The XSS-via-open-redirect vulnerability is directly relevant to this application. **Update immediately.**
- `lodash` (High) and `braces`/`picomatch`/`micromatch` are transitive build-tool dependencies — not in the production bundle. Risk is limited to the build environment.
- `@adobe/css-tools` and `@babel/runtime` are test/build dependencies — not in the production bundle.

### Recommended Actions

```bash
# Update react-router-dom (fixes react-router + @remix-run/router)
npm update react-router-dom

# Remove axios (fixes form-data + follow-redirects)
npm uninstall axios
# Replace CryptoTicker axios calls with fetch

# Update remaining build/test deps
npm audit fix
```

---

## 12. Session Management

### Session Timeout

`useIdleTimeout` triggers `handleLogout` after 30 minutes of inactivity (configurable via `VITE_IDLE_TIMEOUT_MS`). Activity events monitored: `mousemove`, `keydown`, `mousedown`, `touchstart`, `scroll`.

This is a well-implemented compensating control for the lack of server-side session revocation. The implementation is correct and fully tested.

### Concurrent Sessions

Netlify Identity allows multiple concurrent sessions (e.g., two browser tabs). Each tab maintains its own `AuthContext` state. The WebSocket server closes the previous connection when a new one arrives for the same `client_id` — so two tabs cannot both have an active WebSocket connection simultaneously.

### Session Fixation

Not applicable — Netlify Identity manages session tokens. The application does not create or manipulate session identifiers.

### WebSocket Session on Logout

As noted in Section 2, the WebSocket connection is not explicitly closed on logout. The connection remains open until:
- The component unmounts (navigating away from `/crypto`)
- The server detects the token is invalid on the next keepalive or command
- The connection drops naturally

This means a logged-out user's bot continues running and streaming logs until one of the above occurs. For a trading application this is a meaningful gap — logout should immediately stop all bot activity or at minimum close the WebSocket.

---

## 13. Compliance & Standards

### OWASP Top 10 Assessment

| OWASP Category | Status | Notes |
|---|---|---|
| A01 Broken Access Control | ⚠️ Partial | Server enforces `client_id` isolation; no RBAC; WS not closed on logout |
| A02 Cryptographic Failures | ❌ Issue | JWT in WS query string; `.env.production` misconfiguration risks plain HTTP |
| A03 Injection | ✅ Low risk | React escaping; no free-text user input; server validates bot IDs |
| A04 Insecure Design | ⚠️ Partial | No timeout on bot commands; no WS close on logout |
| A05 Security Misconfiguration | ❌ Issue | nginx missing security headers; CSP `frame-ancestors` via meta tag ineffective; dev origins in production CSP |
| A06 Vulnerable Components | ❌ Issue | 1 Critical + 6 High vulnerabilities in dependencies |
| A07 Auth Failures | ⚠️ Partial | No 401 → re-login flow; no token refresh handling; WS not closed on logout |
| A08 Software Integrity | ✅ OK | `npm ci` used in Dockerfile; no integrity issues found |
| A09 Logging Failures | ⚠️ Partial | No client-side error reporting; WS errors not logged |
| A10 SSRF | ✅ N/A | Frontend does not make server-side requests |

### GDPR

The application collects user email via Netlify Identity. No explicit consent mechanism, privacy policy, or data deletion capability is present in the frontend. For EU users, GDPR compliance requires at minimum a privacy policy and a mechanism to request data deletion.

### PCI DSS

Not applicable — the application does not handle payment card data.

---

## 14. Security Testing

### Current Coverage

- No automated security tests (SAST, DAST)
- No penetration testing evidence
- `npm audit` identifies dependency vulnerabilities but is not run in CI (no CI configuration found)
- No secrets scanning (e.g., `git-secrets`, `truffleHog`)

### Recommendations

- Add `npm audit --audit-level=high` to CI pipeline to block builds with High/Critical vulnerabilities
- Add a secrets scanner to pre-commit hooks
- Consider SAST tooling (e.g., CodeQL, Semgrep) for the TypeScript source

---

## 15. Security Issues Summary

| # | Issue | Severity | Description | Remediation |
|---|---|---|---|---|
| 1 | `form-data` critical vulnerability | **Critical** | Unsafe random boundary in `form-data` (GHSA-fjxv-7rqg-78g4) — transitive dep of `axios` | Remove `axios`; migrate `CryptoTicker` to `fetch` |
| 2 | `.env.production` uses `REACT_APP_*` prefix | **Critical** | Vite ignores these vars; production build connects to `http://localhost:8000` over plain HTTP | Rename to `VITE_API_URL` and `VITE_WS_URL` |
| 3 | JWT in WebSocket query string | **High** | Token exposed in server access logs and browser history | Implement `POST /ws/ticket` flow before opening WS |
| 4 | React Router XSS via open redirect | **High** | `react-router-dom` ^6.30.3 vulnerable (GHSA-2w69-qvjg-hvjx, GHSA-9jcx-v3wj-wh4m) | `npm update react-router-dom` |
| 5 | `lodash` prototype pollution | **High** | Three prototype pollution advisories in `lodash` (build/test dep) | `npm audit fix` |
| 6 | `braces` / `picomatch` ReDoS | **High** | Uncontrolled resource consumption in build-time deps | `npm audit fix` |
| 7 | CSP `frame-ancestors` via `<meta>` tag | **High** | `frame-ancestors` is ignored when delivered via meta tag — clickjacking protection is ineffective | Move CSP to nginx HTTP response header |
| 8 | nginx missing security headers | **High** | No `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `HSTS`, or `Permissions-Policy` on static frontend | Add security headers to `nginx.conf` |
| 9 | CSP includes `http://localhost:8000` in production | **Medium** | Development origins in production CSP; production API URL not included (blocks all API calls) | Parameterise CSP with production URLs; remove localhost origins |
| 10 | WebSocket not closed on logout | **Medium** | Bot continues running after user logs out until component unmounts | Close WebSocket in `handleLogout` |
| 11 | `VITE_DEV_AUTH_BYPASS` not asserted false in production | **Medium** | If accidentally set, bypasses all authentication | Add build-time assertion; document in deployment checklist |
| 12 | No 401 → re-login flow | **Medium** | Expired token causes silent API failures; user must manually log out and back in | Intercept 401 responses and trigger `handleLogin()` |
| 13 | `follow-redirects` auth header leakage | **Moderate** | Transitive dep of `axios` leaks auth headers on cross-domain redirects | Remove `axios` |
| 14 | `@babel/runtime` / `@adobe/css-tools` ReDoS | **Moderate** | Build/test dependencies with ReDoS vulnerabilities | `npm audit fix` |
| 15 | No `npm audit` in CI | **Medium** | Vulnerable dependencies not caught automatically | Add `npm audit --audit-level=high` to CI |
| 16 | `public/index.html` is stale CRA artifact | **Low** | Contains `%PUBLIC_URL%` template syntax; not used by Vite; may cause confusion | Remove `public/index.html` |
| 17 | No privacy policy | **Low** | Required for GDPR compliance if serving EU users | Add privacy policy page |
| 18 | Web Vitals sends `window.location.href` | **Low** | Could expose URL parameters to analytics endpoint | Strip query params before sending |

---

## Recommendations

**Priority 1 — Fix before any production deployment**

1. **Fix `.env.production`** — rename `REACT_APP_API_URL` → `VITE_API_URL` and `REACT_APP_WS_URL` → `VITE_WS_URL`. This is the single most impactful fix — without it, the production build is broken.

2. **Update `react-router-dom`** — resolves the High XSS vulnerability:
   ```bash
   npm update react-router-dom
   ```

3. **Remove `axios`** — resolves the Critical `form-data` vulnerability and the Moderate `follow-redirects` vulnerabilities. Migrate `CryptoTicker` to native `fetch`.

4. **Move CSP to nginx HTTP header** and remove `http://localhost:8000` / `ws://localhost:8000` from `connect-src`. Add the production API URL:
   ```nginx
   add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' https://api.sonarft.com wss://api.sonarft.com https://api.coingecko.com https://*.netlify.com https://*.netlify.app; frame-ancestors 'none'; base-uri 'self'; form-action 'self';";
   ```

5. **Add security headers to `nginx.conf`**:
   ```nginx
   add_header X-Content-Type-Options "nosniff";
   add_header X-Frame-Options "DENY";
   add_header Referrer-Policy "no-referrer";
   add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
   add_header Permissions-Policy "geolocation=(), microphone=()";
   ```

**Priority 2 — Fix before production**

6. **Implement WS ticket auth** — `POST /ws/ticket` → `?ticket=<value>` (resolves JWT-in-URL).

7. **Close WebSocket on logout** — call `socket?.close()` in `handleLogout`.

8. **Add `npm audit --audit-level=high` to CI** to prevent future vulnerable dependencies from reaching production.

**Priority 3 — Quality improvements**

9. **Add 401 → re-login interceptor** — catch 401 responses in `utils/api.ts` and call `handleLogin()`.

10. **Add build-time assertion** that `VITE_DEV_AUTH_BYPASS` is not `"true"` in production builds.

11. **Run `npm audit fix`** to resolve remaining Moderate/High build-time dependency vulnerabilities.
