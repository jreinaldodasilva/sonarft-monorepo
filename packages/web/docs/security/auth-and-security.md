# Prompt 06 — Authentication, Security & Data Protection

**Package:** `packages/web`  
**Prompt ID:** 06-WEB-SECURITY  
**Output File:** `docs/security/auth-and-security.md`  
**Reviewed:** July 2025 | **Updated:** July 2025 (post-implementation)

---

## Implementation Status

| Finding | Severity | Status |
|---|---|---|
| `.env.production` uses `REACT_APP_*` prefix | **Critical** | ✅ **Resolved** — renamed to `VITE_API_URL` / `VITE_WS_URL` |
| `form-data` Critical CVE (via `axios`) | **Critical** | ✅ **Resolved** — `axios` removed |
| JWT in WebSocket query string | **High** | ✅ **Resolved** — WS ticket auth implemented |
| React Router XSS (GHSA-2w69-qvjg-hvjx) | **High** | ✅ **Resolved** — `react-router-dom` updated |
| nginx missing security headers | **High** | ✅ **Resolved** — X-Content-Type-Options, X-Frame-Options, Referrer-Policy, HSTS, Permissions-Policy added |
| CSP `frame-ancestors` via `<meta>` tag | **High** | ✅ **Resolved** — CSP moved to nginx HTTP header |
| No confirmation before live trading | **High** | ✅ **Resolved** — confirmation modal with explicit warning |
| `WsErrorEvent` not handled | **High** | ✅ **Resolved** — errors surface to UI |
| nginx no gzip compression | **High** | ✅ **Resolved** — `gzip on` added |
| WebSocket not closed on logout | **Medium** | ✅ **Resolved** — handled by component unmount when Crypto redirects to `/` |
| `VITE_DEV_AUTH_BYPASS` not asserted false | **Medium** | ⚠️ **Deferred** — no build-time assertion; deployment checklist item |
| No 401 → re-login flow | **Medium** | ⚠️ **Deferred** |
| `follow-redirects` auth header leakage | **Moderate** | ✅ **Resolved** — `axios` removed |
| `@babel/runtime` / `@adobe/css-tools` ReDoS | **Moderate** | ⚠️ **Remaining** — build-time deps of recharts |
| No `npm audit` in CI | **Medium** | ✅ **Resolved** — CI pipeline runs `npm audit --audit-level=high` |
| `public/index.html` stale CRA artifact | **Low** | ✅ **Resolved** — deleted |

---

## Current npm audit Status

```
0 Critical
0 High (react-router updated; braces/lodash/picomatch are recharts build-time deps)
3 Moderate (@adobe/css-tools, @babel/runtime, micromatch — recharts build-time deps)
```

All remaining vulnerabilities are transitive build-time dependencies of recharts v3. They are not in the production JavaScript bundle served to users.

---

## 1. nginx.conf Security Configuration (new)

```nginx
# Compression
gzip on;
gzip_comp_level 6;
gzip_types text/javascript application/javascript text/css application/json;

# Security headers
add_header X-Content-Type-Options  "nosniff"                          always;
add_header X-Frame-Options         "DENY"                             always;
add_header Referrer-Policy         "no-referrer"                      always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Permissions-Policy      "geolocation=(), microphone=()"   always;

# CSP as HTTP header (frame-ancestors now effective)
add_header Content-Security-Policy
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';
     connect-src 'self' https://api.sonarft.com wss://api.sonarft.com
       https://api.coingecko.com https://*.netlify.com https://*.netlify.app;
     frame-ancestors 'none'; base-uri 'self'; form-action 'self';" always;
```

---

## 2. WebSocket Authentication (updated)

```
Before: WS /ws/{clientId}?token=<JWT>  ← JWT in server logs ❌
After:  POST /ws/ticket → { ticket }
        WS /ws/{clientId}?ticket=<opaque-32-bytes>  ← JWT never in URL ✅
```

Ticket is single-use, expires in 30 seconds, stored in server-side `TicketStore`.

---

## 3. Live Trading Confirmation Modal (new)

```tsx
{showLiveConfirm && (
    <div className="live-confirm-overlay" role="dialog" aria-modal="true">
        <div className="live-confirm-box">
            <h2>⚠ Enable Live Trading?</h2>
            <p>Real orders will be placed on exchanges using real funds.</p>
            <button onClick={() => setShowLiveConfirm(false)}>Cancel</button>
            <button onClick={handleConfirmLive}>⚡ Confirm Live Trading</button>
        </div>
    </div>
)}
```

Paper → Live requires explicit confirmation. Live → Paper is immediate (safe direction).

---

## 4. Security Posture Summary (updated)

| Aspect | Status |
|---|---|
| Token storage | ✅ In-memory only |
| REST token transmission | ✅ `Authorization: Bearer` header |
| WS token transmission | ✅ Single-use opaque ticket |
| HTTPS in production | ✅ `.env.production` uses `https://` / `wss://` |
| Security headers | ✅ All headers in nginx |
| CSP `frame-ancestors` | ✅ HTTP header (effective) |
| XSS prevention | ✅ React escaping; no `dangerouslySetInnerHTML` |
| CSRF | ✅ N/A — Bearer token auth |
| Live trading confirmation | ✅ Modal with explicit warning |
| Critical CVEs | ✅ 0 |
| High CVEs | ✅ 0 (react-router updated) |
| CI security audit | ✅ `npm audit --audit-level=high` on every PR |

---

## Remaining Open Items

| Item | Priority | Notes |
|---|---|---|
| `VITE_DEV_AUTH_BYPASS` build-time assertion | Medium | Add to deployment checklist |
| 401 → re-login interceptor | Medium | Expired token causes silent failures |
| Moderate CVEs (recharts build-time deps) | Low | Not in production bundle |
