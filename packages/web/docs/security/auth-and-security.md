# Authentication, Security & Data Protection
**Prompt:** 06-WEB-SECURITY | **Package:** web | **Reviewed:** July 2025

---

## Executive Summary

The sonarftweb security posture is solid for a trading dashboard SPA. The
WebSocket ticket pattern is a genuine security improvement over JWT-in-URL.
The nginx CSP is well-configured with `frame-ancestors 'none'`, HSTS, and
`X-Frame-Options: DENY`. The API enforces rate limiting, input key validation,
and timing-safe token comparison. React's default JSX escaping eliminates the
primary XSS surface. The main gaps are: the auth token is not cleared from
`sessionStorage` on logout, `PrivateRoute` is defined but not wired into
routing (leaving the `Crypto` page guarded only by a `return null` check), and
three transitive `HIGH` severity npm packages (`braces`, `lodash`, `picomatch`)
are present in the dependency tree — all in dev/build tooling, not in the
production bundle. No critical vulnerabilities were found.

---

## 1. Authentication & Token Management

**Token type:** Netlify Identity JWT (RS256, `audience: "netlify"`). Fallback:
static opaque token (`SONARFT_API_TOKEN`) for non-Netlify deployments. Dev
mode: no auth when neither is configured.

**Token storage:** `sessionStorage` under key `"sonarft_token"`.

```typescript
// utils/api.ts
export const getAuthToken = (): string | null =>
    sessionStorage.getItem("sonarft_token");
```

`sessionStorage` is scoped to the browser tab and cleared when the tab is
closed. It is not accessible to other tabs or windows. It is accessible to
JavaScript running in the same origin — meaning an XSS attack could read it.
This is the standard trade-off for SPA JWT storage: `sessionStorage` is
preferable to `localStorage` (persists across sessions) but less secure than
an `HttpOnly` cookie (not accessible to JS at all).

**Token lifetime:** Netlify Identity JWTs have a configurable TTL (typically
1 hour). The frontend does not inspect the token's `exp` claim — it relies on
the server to reject expired tokens with a 401.

**Refresh mechanism:** None implemented in the frontend. Netlify Identity's
client-side widget handles token refresh transparently when used. In the current
`AuthProvider` implementation (which uses a hardcoded `DEFAULT_USER` rather than
the Netlify Identity widget), there is no refresh path.

**Expiration handling:** If the JWT expires mid-session, the next API call
returns 401. The frontend catches this as a generic error and sets `fetchError`
or `saveStatus === "error"`. There is no automatic re-authentication or redirect
to login.

**Revocation:** JWTs are stateless — the server cannot revoke an individual
token before its expiry. The static token (`SONARFT_API_TOKEN`) can be revoked
by changing the environment variable and restarting the server.

**Secure transmission:** Tokens are sent as `Authorization: Bearer <token>`
headers over HTTPS in production (`.env.production` uses `https://`). The
WebSocket ticket pattern keeps the JWT out of the WS URL and server access logs.

**WebSocket ticket security:**
- Issued by `POST /ws/ticket` (requires valid Bearer token)
- `secrets.token_urlsafe(32)` — 256 bits of entropy, URL-safe
- 30-second TTL, single-use (consumed on first `redeem()`)
- In-memory store, capped at 10,000 tickets
- Expired tickets evicted on each `issue()` call

---

## 2. Login / Logout Flow

**Current auth implementation:** `AuthProvider` initializes `user` from
`DEFAULT_USER` (env vars `VITE_DEFAULT_USER_ID` / `VITE_DEFAULT_USER_EMAIL`,
falling back to `"dev_user"` / `"user@sonarft.local"`). This is the dev-bypass
mode controlled by `VITE_DEV_AUTH_BYPASS=true`.

In production, the expectation is that Netlify Identity sets the JWT in
`sessionStorage("sonarft_token")` before the React app initializes. The
`AuthProvider` reads the token via `getAuthToken()` for API calls but does not
read it to populate `user` — `user` is always `DEFAULT_USER` in the current
implementation.

**Login:** `handleLogin` sets `user` to `DEFAULT_USER`. No credential
transmission — identity comes from the Netlify Identity widget externally.

**Logout:** `handleLogout` sets `user` to `null`.

**Token deletion on logout — gap:**

```typescript
// AuthProvider.tsx — current
const handleLogout = useCallback(() => setUser(null), []);

// Missing:
// sessionStorage.removeItem("sonarft_token");
```

`handleLogout` does not clear `sessionStorage`. After logout, the JWT remains
in storage until the tab is closed. Any subsequent API call (e.g. from a
background effect that hasn't been cleaned up) would still send the token.

**Session persistence:** `sessionStorage` persists across page reloads within
the same tab. On reload, `AuthProvider` re-initializes `user` from
`DEFAULT_USER` (always logged in in dev mode). The token in `sessionStorage`
is available for API calls immediately.

**Protected endpoints:** The API validates the Bearer token on every request
via `require_auth` / `get_client_id` FastAPI dependencies. Server-side
protection is independent of client-side auth state. ✅

---

## 3. Authorization & Access Control

**Role-based access:** None. The app has a single user role — authenticated
user. There are no admin/viewer/trader role distinctions.

**Protected pages:** The `Crypto` page guards itself:

```typescript
// pages/Crypto/Crypto.tsx
const Crypto: React.FC = () => {
    const { user } = useContext(AuthContext);
    if (!user) return null;
    // ...
};
```

This prevents rendering when `user` is `null` but does not redirect to a login
page. The user sees a blank page rather than a login prompt.

**`PrivateRoute` — defined but unused:**

```typescript
// components/PrivateRoute/PrivateRoute.tsx
const PrivateRoute: React.FC<PrivateRouteProps> = ({ children, value }) =>
    value ? <>{children}</> : <Navigate to="/" />;
```

`PrivateRoute` exists and is tested but is not used in `App.tsx`. The routing
is:

```typescript
<Route path="/crypto" element={<Crypto />} />
```

Rather than:

```typescript
<Route path="/crypto" element={
    <PrivateRoute value={user}><Crypto /></PrivateRoute>
} />
```

The practical difference: with `PrivateRoute`, an unauthenticated user is
redirected to `/`. Without it, they see a blank page at `/crypto`. Both prevent
access to the trading interface, but `PrivateRoute` provides a better UX and
a more explicit access control pattern.

**Client-side vs server-side:** Client-side auth checks are UX guards only.
All sensitive operations (bot management, config updates, history reads) are
protected server-side by `require_auth` / `get_client_id` dependencies. A
client bypassing the frontend auth would still receive 401 from the API. ✅

**Tenant isolation:** The API's `get_client_id` dependency enforces tenant
isolation. In Netlify JWT mode, `client_id` is derived from the JWT `sub`
claim — the client cannot supply a different `client_id`. In static token /
dev mode, `client_id` comes from the query parameter (trusted caller). The
frontend always passes `user.id` as `client_id`, which in dev mode is
`"dev_user"` or the `VITE_DEFAULT_USER_ID` env var.

---

## 4. HTTPS / TLS

**HTTPS enforcement:** `.env.production` uses `https://api.sonarft.com` and
`wss://api.sonarft.com`. No HTTP URLs in production config. ✅

**Mixed content:** Not possible — all API calls use the base URL from
`VITE_API_URL`, which is `https://` in production. ✅

**HSTS:** Set in both nginx (`Strict-Transport-Security: max-age=31536000;
includeSubDomains`) and the API's `SecurityHeadersMiddleware`. ✅

**Secure cookies:** The app does not use cookies for auth — tokens are in
`sessionStorage`. No `Set-Cookie` headers are involved in the auth flow.

**Certificate validation:** Native `fetch` and `WebSocket` use the browser's
built-in TLS stack, which validates certificates by default. No custom
certificate handling. ✅

**nginx CSP `connect-src`:**

```nginx
connect-src 'self'
  https://api.sonarft.com
  wss://api.sonarft.com
  https://api.coingecko.com
  https://*.netlify.com
  https://*.netlify.app;
```

The `https://api.coingecko.com` entry is present in the CSP but no CoinGecko
API calls are visible in the reviewed frontend source. This may be a planned
integration or a leftover from a previous version. If unused, it should be
removed to tighten the CSP.

---

## 5. XSS (Cross-Site Scripting) Prevention

**React JSX escaping:** React escapes all string values rendered in JSX by
default. Text content, attribute values, and event handler strings are all
escaped. This eliminates the primary XSS surface for data-driven rendering. ✅

**`dangerouslySetInnerHTML`:** Not used anywhere in the codebase. ✅

**User input rendering:** The only user-controlled data rendered in the UI is:
- Bot IDs (truncated to 8 chars + `…` in `BotControls`)
- Trade records from the API (`TradeRecord` fields rendered in `TradeHistoryTable`)
- Log messages from the server (rendered as text in `BotConsole`)
- Config keys from the API (exchange names, symbol names, indicator names)

All of these are rendered as React text nodes (not `innerHTML`), so they are
automatically escaped. ✅

**Log message rendering:**

```typescript
// BotConsole.tsx
<span key={i} className={getLogClass(line)}>{line}{"\n"}</span>
```

Log lines from the server are rendered as JSX text children — React escapes
any HTML entities. A malicious server sending `<script>alert(1)</script>` in
a log message would render it as literal text, not execute it. ✅

**`getLogClass` regex on log content:**

```typescript
const getLogClass = (line: string): string => {
    if (/WARNING|WARN/i.test(line))   return "log-line log-line--warning";
    if (/ERROR|CRITICAL/i.test(line)) return "log-line log-line--error";
    if (/DEBUG/i.test(line))          return "log-line log-line--debug";
    return "log-line log-line--info";
};
```

This regex runs on every log line. The patterns are simple and non-backtracking
— no ReDoS risk. The result is a CSS class name string, not rendered HTML. ✅

**DOM manipulation:** No direct `document.getElementById`, `innerHTML`, or
`document.write` usage. All DOM interaction goes through React. ✅

**Third-party scripts:** None loaded at runtime. All dependencies are bundled
at build time. The CSP `script-src 'self'` blocks any injected external scripts. ✅

**Content Security Policy (nginx):**

```
default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline';
img-src 'self' data:;
font-src 'self';
connect-src 'self' https://api.sonarft.com wss://api.sonarft.com ...;
frame-ancestors 'none';
base-uri 'self';
form-action 'self';
```

`style-src 'unsafe-inline'` is required for Recharts and inline styles. This
is a known trade-off — removing it would break chart rendering. The risk is
low given `script-src 'self'` blocks script injection. ✅

`frame-ancestors 'none'` is set as an HTTP header (not a `<meta>` tag), which
is the only effective placement for this directive. ✅

---

## 6. CSRF (Cross-Site Request Forgery) Prevention

**CSRF tokens:** Not used. The app relies on the `Authorization: Bearer`
header for CSRF protection.

**Why Bearer tokens prevent CSRF:** CSRF attacks exploit the browser's
automatic cookie attachment. Since this app uses `sessionStorage` (not cookies)
for the auth token, and the `Authorization` header must be explicitly set by
JavaScript, a cross-origin request from a malicious site cannot include the
token — the browser's same-origin policy prevents cross-origin JavaScript from
reading `sessionStorage` or setting custom headers on cross-origin requests. ✅

**CORS configuration (API):**

```python
CORSMiddleware(
    allow_origins=settings.allowed_origins,  # from CORS_ORIGINS env var
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

`allow_credentials=True` is set. This is required for the `Authorization`
header to be sent on cross-origin requests. The `allow_origins` list must not
include `*` when `allow_credentials=True` — the API correctly uses an explicit
list from `CORS_ORIGINS`. ✅

**SameSite cookies:** Not applicable — no cookies are used.

**WebSocket CSRF:** WebSocket connections do not send cookies automatically,
and the browser does not enforce CORS for WebSocket upgrades. The ticket-based
auth (or `?token=` fallback) ensures only authenticated clients can open a
WebSocket connection. ✅

---

## 7. Sensitive Data Handling

**Auth token:** Stored in `sessionStorage("sonarft_token")`. Not logged, not
included in error messages, not passed as a URL parameter for REST calls. The
WS ticket pattern keeps it out of server access logs. ✅

**Token in WS URL fallback:** The legacy `?token=<jwt>` fallback is used only
when the ticket endpoint is unavailable (dev mode). In production, the ticket
path is always attempted first. The fallback is a known risk, documented in the
codebase. Acceptable for dev; should not reach production.

**API keys / exchange credentials:** Not handled by the frontend at all. Exchange
API keys are managed server-side by the bot engine. The frontend has no input
fields for API keys and no storage of them. ✅

**PII:** The only PII is the user's email address, displayed in `NavBar`:

```typescript
{user?.email && (
    <section className="sectionUser">
        <span className="nav-user">{user.email}</span>
    </section>
)}
```

The email is rendered as a React text node (escaped) and is not stored beyond
the `AuthProvider` state (in-memory, cleared on logout). ✅

**Trade data:** `TradeRecord` fields (prices, amounts, profits) are rendered in
`TradeHistoryTable` and `ProfitChart`. This data comes from the server and is
not stored client-side beyond React state (no `localStorage` persistence of
trade history). ✅

**Error messages:** API error responses include `{ "detail": "...", "request_id": "..." }`.
The frontend displays `detail` strings in alert banners. The `generic_error_handler`
returns `"Internal server error"` for unhandled exceptions — no stack traces
or internal details are exposed to the client. ✅

**Logging:** `no-console: warn` ESLint rule discourages `console.log` in
production code. `vitals.ts` uses `console.log` in dev mode only (guarded by
`isDev`). No sensitive values are logged. ✅

**`localStorage` contents:** Only config state (`parametersState`,
`indicatorsState`) — exchange names, symbol names, indicator selections. No
tokens, no PII, no financial data. ✅

---

## 8. Data Privacy

**Data collected:** User email (from Netlify Identity JWT), user ID (JWT `sub`
claim), trading configuration (exchanges, symbols, indicators), trade/order
history (server-side only, not persisted client-side beyond session).

**Data retention:** Config state in `localStorage` has no TTL — it persists
until the user clears browser storage. No other client-side data retention.

**Analytics:** `web-vitals` reports Core Web Vitals to `VITE_VITALS_URL` if
configured. The payload includes `url`, `metric name`, `value`, `rating`, and
`id` — no PII. In production, `VITE_VITALS_URL` is not set in `.env.production`
(commented out), so no vitals are reported by default. ✅

**Third-party tracking:** None. No Google Analytics, no tracking pixels, no
third-party scripts loaded at runtime. ✅

**CoinGecko in CSP:** `https://api.coingecko.com` is listed in the nginx CSP
`connect-src` but no CoinGecko calls are present in the reviewed source. If
this is a planned integration, ensure any price data fetched does not include
user-identifying parameters.

---

## 9. Input Validation & Sanitization

**Client-side validation:** Minimal. The config panels use checkboxes and a
strategy dropdown — there are no free-text inputs in the trading interface.
The only user-typed input would be through Netlify Identity's login form
(handled externally by the Netlify widget).

**Server-side validation (API):** Comprehensive:
- Config keys validated against `_CONFIG_KEY_RE`:
  `^[\w\s/(). %,:-]{1,128}$` — blocks path traversal, shell injection,
  prototype pollution
- Config dict size capped at 50 entries per section
- Bot/client IDs validated against `ID_PATTERN`:
  `^[a-zA-Z0-9_-]{1,64}$`
- `strategy` field validated as `Literal["arbitrage", "market_making"]`
- Pydantic v2 validates all request bodies with strict type checking

Since the frontend sends only checkbox-derived boolean maps and a strategy
enum value, the attack surface for injection via user input is effectively zero.
The server-side validation is a defence-in-depth measure. ✅

**Bot ID truncation in UI:** Bot IDs are displayed as `botId.slice(0, 8) + "…"`
in `BotControls` and the remove modal. This is a display concern, not a
security concern — the full ID is used in API calls. ✅

---

## 10. API Communication Security

**HTTPS:** All production API calls use `https://api.sonarft.com` (from
`.env.production`). Dev uses `http://localhost:8000` — acceptable for local
development. ✅

**Authentication header:** `Authorization: Bearer <token>` on every request
via `getAuthHeaders()`. Never in URL query parameters for REST calls. ✅

**Request validation:** Pydantic v2 on the server validates all request bodies.
Path parameters validated by regex patterns. Rate limiting enforced by slowapi.

**Response validation:** None client-side beyond TypeScript type assertions.
No runtime schema validation (e.g. Zod). If the server returns an unexpected
shape, the app may silently render incorrect data.

**Error handling:** API error responses do not expose stack traces or internal
details. The `generic_error_handler` returns `"Internal server error"` for
unhandled exceptions. `request_id` is included in error responses for
correlation with server logs — this is not sensitive information. ✅

**Rate limiting:**

| Endpoint category | Limit |
|---|---|
| Global default | 200/minute per IP |
| Read endpoints (GET) | 60/minute |
| Write endpoints (PUT) | 30/minute |
| Bot creation | 10/minute |
| WS ticket | 30/minute |

The frontend does not handle 429 responses specially — they appear as generic
errors. No client-side backoff on rate limit hits.

---

## 11. Dependency Security

### npm audit results (July 2025)

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 3 |
| Moderate | 3 |
| Low | 0 |
| Total | 6 |

### High severity findings

| Package | CVE / Issue | Direct? | In prod bundle? |
|---|---|---|---|
| `braces` | Uncontrolled resource consumption (ReDoS) | No (transitive) | No — build tooling only |
| `lodash` | Prototype pollution in `_.unset`/`_.omit`; code injection via `_.template` | No (transitive) | No — build tooling only |
| `picomatch` | Method injection in POSIX character classes; ReDoS via extglob quantifiers | No (transitive) | No — build tooling only |

### Moderate severity findings

| Package | CVE / Issue | Direct? | In prod bundle? |
|---|---|---|---|
| `@adobe/css-tools` | ReDoS while parsing CSS | No (transitive) | No — test tooling |
| `@babel/runtime` | Inefficient RegExp in named capturing group transpilation | No (transitive) | Potentially (Babel runtime) |
| `micromatch` | ReDoS | No (transitive) | No — build tooling only |

**Assessment:** All six vulnerabilities are in transitive dependencies used by
build tools (Vite, Vitest, Babel) or test infrastructure. None are in the
production JavaScript bundle served to users. The CI pipeline runs
`npm audit --audit-level=high` — the current 3 high findings would fail this
check if they were not already present before the CI rule was added, or if the
audit level was set to `moderate`.

**Recommended action:** Run `npm audit fix` to resolve auto-fixable issues.
For non-auto-fixable transitive vulnerabilities, check if the parent packages
have released updates that pull in patched versions.

---

## 12. Session Management

**Session storage:** `sessionStorage` — tab-scoped, cleared on tab close.

**Session timeout:** `useIdleTimeout` hook exists and is implemented correctly
but is **not wired into any component**. `VITE_IDLE_TIMEOUT_MS=1800000` (30
minutes) is documented in `.env.development` but has no effect. There is
currently no idle session timeout in the running application.

**Concurrent sessions:** Multiple tabs can each have their own `sessionStorage`
with separate tokens. The server's `WebSocketManager` closes the previous
connection when a new one arrives for the same `client_id`, so only one active
WebSocket per client is maintained. REST calls from multiple tabs would all
succeed independently.

**Session fixation:** Not applicable — the app does not use session cookies.
The JWT is issued by Netlify Identity and cannot be fixed by an attacker.

**Session revocation:** JWTs cannot be revoked before expiry (stateless).
Closing the tab clears `sessionStorage` and effectively ends the session.

---

## 13. Compliance & Standards

**OWASP Top 10 (2021) assessment:**

| OWASP Category | Status | Notes |
|---|---|---|
| A01 Broken Access Control | ✅ Low risk | Server enforces auth on all endpoints; tenant isolation via JWT `sub` |
| A02 Cryptographic Failures | ✅ Low risk | HTTPS in production; `sessionStorage` (not `localStorage`); no sensitive data in logs |
| A03 Injection | ✅ Low risk | React JSX escaping; no `innerHTML`; server validates all inputs with regex + Pydantic |
| A04 Insecure Design | ⚠️ Note | `isSimulating` optimistic toggle without server confirmation; `bot_stopped` ignored |
| A05 Security Misconfiguration | ✅ Low risk | CSP, HSTS, `X-Frame-Options`, `X-Content-Type-Options` all set |
| A06 Vulnerable Components | ⚠️ Medium | 3 HIGH transitive deps in build tooling (not in prod bundle) |
| A07 Auth Failures | ⚠️ Note | Token not cleared on logout; no idle timeout wired; no token refresh |
| A08 Software Integrity | ✅ Low risk | No CDN scripts; all deps bundled; `npm audit` in CI |
| A09 Logging Failures | ✅ Low risk | Server logs all requests with request IDs; no sensitive data in logs |
| A10 SSRF | ✅ N/A | Frontend-only; no server-side URL fetching |

**PCI DSS:** Not applicable — the frontend does not handle payment card data.
Exchange API keys are managed server-side only.

**GDPR:** Minimal PII (email address in memory only). No analytics by default.
No third-party trackers. Low GDPR surface area.

---

## 14. Security Testing

**Automated:** `npm audit --audit-level=high` runs in CI on every push/PR
(`.github/workflows/ci.yml`). Currently passing at `high` level (0 critical,
0 high in prod bundle).

**Static analysis:** ESLint with `@typescript-eslint` catches type safety
issues. No dedicated SAST tool (e.g. Semgrep, CodeQL) is configured.

**Penetration testing:** No evidence of formal pen testing in the reviewed
source.

**Dependency scanning:** `npm audit` in CI. No Dependabot or Snyk configuration
found.

**Security-focused tests:** The test suite covers auth flows (`AuthProvider.test.tsx`,
`PrivateRoute.test.tsx`) and API error handling (`api.test.ts`). No dedicated
security regression tests (e.g. XSS payload rendering, CSRF simulation).

---

## 15. Security Issues Summary

| Severity | Issue | Description | Remediation |
|---|---|---|---|
| Medium | Token not cleared on logout | `handleLogout` sets `user = null` but does not call `sessionStorage.removeItem("sonarft_token")`. JWT persists until tab close. | Add `sessionStorage.removeItem("sonarft_token")` to `handleLogout` in `AuthProvider`. |
| Medium | Idle session timeout not wired | `useIdleTimeout` hook exists but is not connected to any component. `VITE_IDLE_TIMEOUT_MS` has no effect. | Wire `useIdleTimeout` into `AuthProvider` or `App`, calling `handleLogout` on idle. |
| Medium | 3 HIGH transitive npm vulnerabilities | `braces`, `lodash`, `picomatch` have HIGH severity CVEs. All are in build/test tooling, not the prod bundle. | Run `npm audit fix`; update parent packages that pull in these transitive deps. |
| Low | `PrivateRoute` unused — weaker route guard | `Crypto` page uses `if (!user) return null` instead of `PrivateRoute`, showing a blank page rather than redirecting unauthenticated users. | Wire `PrivateRoute` into `App.tsx` route definitions. |
| Low | No token refresh mechanism | Expired JWT causes silent API failures (generic error banner) with no re-authentication prompt. | Detect 401 responses in `api.ts` and trigger `handleLogout` (or a re-auth flow) to give the user a clear signal. |
| Low | `isSimulating` optimistic with no rollback | If `set_simulation` fails server-side, `isSimulating` shows the wrong state with no correction. | Add rollback logic: on `error` event following a `set_simulation` command, revert `isSimulating`. |
| Low | `https://api.coingecko.com` in CSP but unused | The nginx CSP `connect-src` includes CoinGecko but no CoinGecko calls exist in the source. Unnecessary CSP entries widen the allowed connection surface. | Remove `https://api.coingecko.com` from `connect-src` until the integration is implemented. |
| Low | No 401 detection in API client | `api.ts` treats 401 the same as any other HTTP error. Users see a generic error banner rather than a session-expired message. | Check `response.status === 401` in `api.ts` and dispatch a logout or show a "Session expired — please log in again" message. |
| Info | `style-src 'unsafe-inline'` in CSP | Required for Recharts inline styles. Weakens style injection protection. | Acceptable trade-off. Consider a nonce-based approach if Recharts adds nonce support. |
| Info | No SAST tool configured | ESLint catches type issues but no dedicated security static analysis (Semgrep, CodeQL) is configured. | Add a CodeQL or Semgrep GitHub Actions workflow for automated security scanning on PRs. |
| Info | `npm audit` CI level is `high` not `moderate` | 3 moderate vulnerabilities pass CI. | Consider lowering to `--audit-level=moderate` and resolving or suppressing the known moderate findings. |
