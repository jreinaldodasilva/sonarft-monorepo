# sonarftweb — Authentication, Security & Data Protection

**Prompt:** 06-authentication-security  
**Category:** Security  
**Date:** July 2025  
**Depends on:** [docs/api-integration/sonarft-integration.md](../api-integration/sonarft-integration.md)

---

## Executive Summary

sonarftweb has significant security gaps that must be addressed before production deployment. The most critical issues are: the sonarft backend receives no authentication credentials (any caller knowing a `clientId` can control bots and read trade history), all backend communication uses plain HTTP, the `axios` dependency has 7 known CVEs including CSRF and SSRF, `react-router-dom` has an XSS via open redirect, and the Netlify Identity widget is loaded from an external CDN without subresource integrity. The app has no Content Security Policy, no input validation, and no CSRF protection. The dependency audit reports 63 vulnerabilities (3 critical, 29 high). The authentication layer itself (Netlify Identity) is correctly implemented as a frontend gate, but it provides zero protection for the sonarft backend.

---

## 1. Authentication & Token Management

| Aspect | Implementation | Assessment |
|---|---|---|
| Auth provider | Netlify Identity (`netlify-identity-widget` v1.9.2) | Third-party hosted identity service |
| Token type | JWT issued by Netlify Identity | Standard JWT |
| Token storage | Managed by `netlify-identity-widget` internally in `localStorage` | Vulnerable to XSS token theft |
| Token passed to sonarft | **Never** | Critical gap — backend is unprotected |
| Token lifetime | Controlled by Netlify Identity service | Not configurable in app code |
| Refresh mechanism | Handled internally by widget | Not visible in app code |
| Expiration handling | Widget handles silently | No app-level expiry UI |
| Revocation | Via Netlify Identity dashboard only | No in-app revocation |
| Secure transmission | HTTP only (localhost) | Plaintext in any non-local deployment |

### The Core Authentication Gap

The Netlify Identity JWT is available via `netlifyIdentity.currentUser().token.access_token` but is **never retrieved or sent** to the sonarft backend. Every REST call and WebSocket connection is unauthenticated:

```js
// utils/api.js — every fetch call looks like this
const response = await fetch(HTTP + `/botids/${clientId}`, {
    method: "GET",
    headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        // No Authorization header
    },
});
```

The `clientId` (Netlify user UUID) is passed as a URL path parameter. UUIDs are not secret — they appear in browser history, server access logs, and the network tab. Anyone who observes or guesses a `clientId` can:
- List and control all bots for that client
- Read full order and trade history
- Change trading parameters and indicators
- Create and remove bots

**Fix:**
```js
// Get token from Netlify Identity
const getAuthHeader = () => {
    const user = netlifyIdentity.currentUser();
    const token = user?.token?.access_token;
    return token ? { Authorization: `Bearer ${token}` } : {};
};

// Apply to every fetch
const response = await fetch(HTTP + `/botids/${clientId}`, {
    headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...getAuthHeader(),
    },
});
```

The sonarft backend would also need to validate the JWT on every request.

---

## 2. Login / Logout Flow

| Step | Implementation | Assessment |
|---|---|---|
| Login trigger | `netlifyIdentity.open()` → modal widget | Correct |
| Credential handling | Handled entirely by Netlify Identity service | Credentials never touch app code ✓ |
| Post-login state | `netlifyIdentity.on("login", user => setUser(user))` | Correct ✓ |
| Session persistence | `netlifyIdentity.currentUser()` checked on mount | Correct ✓ |
| Logout | `netlifyIdentity.logout()` → `setUser(null)` | Correct ✓ |
| Token deletion on logout | Handled by widget (clears localStorage) | Correct ✓ |
| Protected routes | `PrivateRoute` checks `user !== null` → redirect to `/` | Correct pattern, but duplicated 4× |
| Post-logout redirect | Redirect to `/` via `<Navigate>` | Correct ✓ |

The login/logout flow itself is well-implemented. The gap is entirely in the backend communication layer.

---

## 3. Authorization & Access Control

| Aspect | Status |
|---|---|
| Role-based access | Not implemented — single user role only |
| Protected pages | `Crypto`, `Dex`, `Forex`, `Token` require auth via `PrivateRoute` |
| Unprotected pages | `Home`, `CryptoChatGPT`, `Doggy` are public |
| Client-side enforcement | `PrivateRoute` redirects unauthenticated users |
| Server-side enforcement | **None** — sonarft backend has no auth validation |
| Scope/permissions | Not implemented |

Client-side route protection is correct but insufficient on its own. A user who bypasses the React router (e.g., direct API call via curl) has full access to all sonarft endpoints.

---

## 4. HTTPS / TLS

| Aspect | Status | Severity |
|---|---|---|
| Backend URL | `http://localhost:5000` — plaintext HTTP | High |
| WebSocket URL | `ws://localhost:5000/ws` — unencrypted | High |
| CoinGecko API | `https://` — correct ✓ | — |
| Netlify Identity widget | Loaded from `https://identity.netlify.com` — correct ✓ | — |
| Docker deployment | No TLS configured in `docker-compose.yml` | High |
| HSTS | Not set (no server config in frontend) | Medium |
| Mixed content | If deployed to HTTPS, HTTP backend calls will be blocked by browsers | High |

The `docker-compose.yml` exposes port 3000 (frontend) and 5000 (backend) with no TLS termination. The sonarft `docker-compose.yml` uses Traefik with ACME TLS, but the sonarftweb compose file has no equivalent.

**Fix:** Use environment variables for URLs and enforce HTTPS in production:
```
REACT_APP_API_URL=https://api.sonarft.com
REACT_APP_WS_URL=wss://api.sonarft.com/ws
```

---

## 5. XSS (Cross-Site Scripting) Prevention

### React's Default Escaping

React escapes all string content rendered via JSX by default. The log display in `Bots.js` is safe as written:

```jsx
<pre className="console">
    {logs}  {/* React escapes this — safe */}
    <div ref={consoleEndRef} />
</pre>
```

No `dangerouslySetInnerHTML` is used anywhere in the codebase. ✓

### External Script — Netlify Identity Widget

```html
<!-- public/index.html -->
<script type="text/javascript"
    src="https://identity.netlify.com/v1/netlify-identity-widget.js">
</script>
```

This loads a third-party script from an external CDN **without Subresource Integrity (SRI)**. If the CDN is compromised or the URL is hijacked, malicious JavaScript executes in the app's origin with full access to `localStorage` (including the Netlify JWT).

**Fix:**
```html
<script src="https://identity.netlify.com/v1/netlify-identity-widget.js"
    integrity="sha384-[hash]"
    crossorigin="anonymous">
</script>
```

Or better — import the widget as an npm package (already in `package.json`) and remove the CDN script entirely.

### Content Security Policy

No CSP header or `<meta http-equiv="Content-Security-Policy">` is set anywhere. Without CSP:
- Injected scripts can execute freely
- Inline event handlers are unrestricted
- External resources can be loaded from any origin

**Minimum recommended CSP for production:**
```html
<meta http-equiv="Content-Security-Policy"
    content="default-src 'self';
             script-src 'self' https://identity.netlify.com;
             connect-src 'self' https://api.sonarft.com wss://api.sonarft.com https://api.coingecko.com;
             img-src 'self' data:;
             style-src 'self' 'unsafe-inline';">
```

### XSS via react-router-dom (CVE)

`npm audit` reports `@remix-run/router` (used by `react-router-dom` v6.15.0) is vulnerable to XSS via open redirects (`GHSA-2w69-qvjg-hvjx`). A crafted URL could redirect users to a malicious site. Fix: upgrade `react-router-dom`.

---

## 6. CSRF Prevention

| Aspect | Status |
|---|---|
| CSRF tokens | Not implemented |
| SameSite cookies | Not applicable — no cookies used for auth |
| Origin header validation | Not implemented (server-side gap) |
| Fetch requests | Use `Content-Type: application/json` — provides some CSRF protection for simple requests |

The app uses `fetch` with `Content-Type: application/json` for all POST requests. Browsers enforce CORS preflight for non-simple requests with JSON bodies, which provides implicit CSRF protection **if** the sonarft backend correctly validates the `Origin` header in CORS configuration.

However, `axios` v1.4.0 has a known CSRF vulnerability (`GHSA-wf5p-g6vw-rhxx`). While `axios` is only used for CoinGecko calls (GET requests, no auth), the vulnerability exists in the installed version.

---

## 7. Sensitive Data Handling

| Data | Where Stored | Encrypted | Exposed in Logs | Risk |
|---|---|---|---|---|
| Netlify JWT | `localStorage` (by widget) | No | No | Medium — XSS can steal it |
| `clientId` (user UUID) | URL path params, component state | No | Yes (`console.log`) | Medium |
| Trading parameters | `localStorage` key `parametersState` | No | No | Low |
| Indicator settings | `localStorage` key `indicatorsState` | No | No | Low |
| API error messages | `console.log` only | — | Yes | Low |
| Exchange API keys | Not stored in frontend | — | — | N/A |
| Bot order/trade history | Component state (memory only) | — | No | Low |

### clientId Logged to Console

```js
// utils/api.js
const data = await response.json();
console.log("Botids:", data);  // logs clientId-associated data
```

```js
// utils/api.js
console.log("Order data:", orderdata);
console.log("Trade data:", tradedata);
```

Trade and order data (including prices, amounts, exchanges) is logged to the browser console. In a shared or public computer, this data persists in DevTools history.

### localStorage Token Exposure

The Netlify Identity JWT stored in `localStorage` is accessible to any JavaScript running on the same origin. If an XSS vulnerability is ever introduced (e.g., via a dependency), the token can be exfiltrated. The industry recommendation for high-security apps is to store tokens in `httpOnly` cookies, but this requires server-side session management that Netlify Identity does not provide out of the box.

---

## 8. Input Validation & Sanitization

| Input Point | Validation | Sanitization |
|---|---|---|
| Checkbox selections (Parameters) | None — truthy/falsy only | N/A |
| Checkbox selections (Indicators) | None — truthy/falsy only | N/A |
| Bot ID from server response | None | N/A |
| WebSocket `event.data` | None | N/A (rendered as text, React escapes) |
| URL parameters | None | N/A |

The app has minimal user text input — most interactions are checkbox selections and button clicks. The primary validation gap is on the server response side: API responses are used directly without schema validation. A compromised or misbehaving server could return unexpected data shapes that cause runtime errors or unexpected rendering.

---

## 9. Dependency Security — npm audit Results

**Total vulnerabilities: 63** (3 Critical, 29 High, 17 Moderate, 14 Low)

### Critical

| Package | CVE / Advisory | Issue | Fix |
|---|---|---|---|
| `@babel/traverse` | GHSA-67hx-6x53-jw92 | Arbitrary code execution when compiling malicious code | Update babel |
| `axios` v1.4.0 | GHSA-wf5p-g6vw-rhxx + 6 more | CSRF, SSRF, credential leakage, DoS, prototype pollution | Upgrade to latest axios |
| `form-data` | GHSA (2×) | Unsafe random boundary generation | Update via dependency chain |

### High (selected — directly relevant)

| Package | Issue | Fix Available |
|---|---|---|
| `react-router-dom` v6.15.0 | XSS via open redirect | Yes — upgrade |
| `@remix-run/router` | XSS via open redirect | Yes — upgrade |
| `serialize-javascript` | XSS, RCE via RegExp | Yes |
| `rollup` | DOM Clobbering → XSS, path traversal | Yes |
| `node-forge` | 6 CVEs: ASN.1 recursion, signature forgery, RSA bypass | Yes |
| `lodash` | Prototype pollution, code injection via template | Yes |
| `socket.io-parser` | DoS via unbounded binary attachments | Yes |
| `express` | XSS via response.redirect(), open redirect | Yes |
| `ws` | DoS via many HTTP headers | Yes |
| `webpack-dev-middleware` | Path traversal | Yes |

### Assessment

Most high/critical vulnerabilities are in the **build toolchain** (`react-scripts`, `webpack`, `babel`, `rollup`) rather than runtime dependencies. They affect the development environment and build process, not the deployed application directly. However:

- `axios` vulnerabilities **are runtime** — the CSRF and SSRF CVEs affect the deployed app
- `react-router-dom` XSS **is runtime** — affects the deployed app
- `socket.io-parser` DoS **is runtime** — affects the deployed app

### Dockerfile — Node 14 (EOL)

```dockerfile
FROM node:14
```

Node.js 14 reached End of Life in April 2023. It no longer receives security patches. The Docker image should use Node 18 LTS or Node 20 LTS.

---

## 10. API Communication Security

| Aspect | Status |
|---|---|
| HTTPS for sonarft API | No — `http://localhost:5000` |
| HTTPS for CoinGecko | Yes ✓ |
| Auth header on sonarft calls | None |
| Response validation | None |
| Error messages expose server info | Partially — `HTTP error! status: ${response.status}` |
| Rate limiting (client-side) | None |
| CORS | Configured server-side (not visible in frontend code) |

---

## 11. Session Management

| Aspect | Status |
|---|---|
| Session storage mechanism | Netlify Identity `localStorage` |
| Session timeout | Controlled by Netlify Identity (not configurable in app) |
| Concurrent sessions | Allowed — multiple tabs/devices |
| Session fixation | Not applicable (no server-side session) |
| Session revocation | Via Netlify dashboard only |
| Inactive session timeout | Not implemented in app |

---

## 12. OWASP Top 10 Assessment

| OWASP Category | Status | Severity |
|---|---|---|
| A01 Broken Access Control | Backend has no auth validation | Critical |
| A02 Cryptographic Failures | HTTP used for backend; JWT in localStorage | High |
| A03 Injection | No user text input; React escapes output | Low |
| A04 Insecure Design | No threat model; no security requirements documented | Medium |
| A05 Security Misconfiguration | No CSP; Node 14 EOL in Docker; no HSTS | High |
| A06 Vulnerable Components | 63 npm vulnerabilities (3 critical, 29 high) | Critical |
| A07 Auth & Identity Failures | JWT never sent to backend | Critical |
| A08 Software & Data Integrity | No SRI on Netlify Identity CDN script | High |
| A09 Logging & Monitoring Failures | Sensitive data in console.log; no server-side audit log | Medium |
| A10 SSRF | axios SSRF CVE in installed version | High |

---

## 13. Consolidated Security Issues

| # | Issue | Severity | File | Remediation |
|---|---|---|---|---|
| 1 | No auth token sent to sonarft backend | Critical | `utils/api.js`, `useWebSocket.jsx` | Pass Netlify JWT as `Authorization: Bearer` header on all requests |
| 2 | `axios` has 7 CVEs including CSRF and SSRF | Critical | `package.json` | Upgrade `axios` to latest version |
| 3 | `@babel/traverse` arbitrary code execution | Critical | `package.json` | Update babel dependencies |
| 4 | `react-router-dom` XSS via open redirect | High | `package.json` | Upgrade `react-router-dom` |
| 5 | All backend communication over HTTP | High | `utils/constants.js` | Use HTTPS in production via env vars |
| 6 | WebSocket connection unauthenticated | High | `useWebSocket.jsx` | Pass auth token as query param or first message |
| 7 | Netlify Identity CDN script has no SRI | High | `public/index.html` | Add `integrity` attribute or use npm package only |
| 8 | No Content Security Policy | High | `public/index.html` | Add CSP meta tag or HTTP header |
| 9 | Node.js 14 EOL in Dockerfile | High | `Dockerfile` | Upgrade to `node:20-alpine` |
| 10 | `serialize-javascript` XSS / RCE CVE | High | `package.json` | Update via `react-scripts` upgrade |
| 11 | `socket.io-parser` DoS CVE | High | `package.json` | Upgrade `socket.io-client` |
| 12 | JWT stored in `localStorage` (XSS-stealable) | Medium | Netlify Identity | Accept as limitation of Netlify Identity; mitigate with CSP |
| 13 | `clientId` and trade data logged to console | Medium | `utils/api.js` | Remove all `console.log` with sensitive data |
| 14 | `PrivateRoute` is client-side only | Medium | All page files | Ensure server validates auth on every request |
| 15 | No session timeout for inactive users | Medium | `AuthProvider.js` | Implement idle timeout with `netlifyIdentity.logout()` |
| 16 | No input validation on API responses | Low | All components | Add response schema validation |
| 17 | Dual lock files (`npm` + `yarn`) | Low | Root | Pick one package manager; remove the other lock file |
| 18 | No security tests or SAST | Low | — | Add `npm audit` to CI; consider SAST tooling |

---

**Save location:** `docs/security/auth-and-security.md`  
**Next prompts:** `07-trading-interface-ux.md`, `08-performance-optimization.md`, `12-implementation-roadmap.md`
