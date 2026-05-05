# Authentication, Security & Authorization Review

**Prompt ID:** 04-API-SECURITY  
**Package:** `packages/api`  
**Reviewer:** Amazon Q (Senior Python / FastAPI / Security Auditor)  
**Date:** July 2025  
**Status:** Complete

---

## Executive Summary

The SonarFT API has a solid security foundation: JWT validation uses RS256 with live JWKS key fetching (no hardcoded secrets), static token comparison uses `hmac.compare_digest` to prevent timing attacks, the WebSocket ticket pattern keeps JWTs out of server logs, and the middleware stack applies HSTS, X-Frame-Options, and other security headers globally. The most significant finding is that `packages/api/.gitignore` does not exclude `.env`, meaning the `.env` file — which contains `SONARFT_API_TOKEN` and `NETLIFY_SITE_URL` — is tracked by git. In the current state the `.env` values are empty, but this is one accidental `git commit` away from a credential leak. A second structural concern is that auth is completely disabled when neither `NETLIFY_SITE_URL` nor `SONARFT_API_TOKEN` is set — this is documented as dev-mode behaviour but there is no runtime warning and no enforcement that production deployments have auth configured. No critical vulnerabilities were found in the authentication logic itself; the implementation correctly validates JWTs, enforces expiry, and isolates tenants.

---

## Security Score Card

| Area | Status | Notes |
|---|---|---|
| JWT algorithm | ✅ RS256 | Asymmetric — private key never touches the API |
| JWT expiry enforcement | ✅ `verify_exp: True` | Enforced in `_decode_jwt` |
| Timing-safe token comparison | ✅ `hmac.compare_digest` | `security.py:72` |
| WebSocket JWT exposure | ✅ Ticket-based | JWT never in WS URL or server logs |
| Tenant isolation | ✅ Enforced | Bot ownership checked before every mutation |
| CORS configuration | ✅ Restrictive | Explicit origin allowlist, no wildcard |
| Security headers | ✅ All major headers | HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy |
| Input validation | ✅ Regex + Pydantic | Path params, config keys, botid all validated |
| SQL injection | ✅ Parameterised queries | SQLite uses `?` placeholders throughout |
| Path traversal | ✅ Guarded | `_client_path` resolves and checks prefix |
| Rate limiting | ✅ Per-endpoint tiers | slowapi, IP-based |
| Secret storage | ⚠️ `.env` in git | `packages/api/.gitignore` missing `.env` entry |
| Auth disabled in dev | ⚠️ Silent | No warning logged when auth is off |
| Token revocation | ❌ Not implemented | No JWT blocklist or session invalidation |
| RBAC | ❌ Not implemented | Single-role model (authenticated = full access) |
| TLS enforcement | ⚠️ Not enforced by API | Delegated to reverse proxy — not documented |

---

## 1. Authentication Mechanism

### 1.1 JWT Validation — `core/security.py`

The API supports two authentication modes, selected by environment variable:

**Mode A — Netlify Identity JWT (RS256)**

```python
# security.py:27–35
def _get_jwks_client() -> PyJWKClient | None:
    if settings.netlify_site_url:
        url = f"{settings.netlify_site_url.rstrip('/')}/.netlify/identity/keys"
        _jwks_client_holder[0] = PyJWKClient(url)
```

- Algorithm: RS256 (asymmetric — API only holds the public key via JWKS)
- Key source: Netlify Identity JWKS endpoint, fetched at first use
- Expiry: enforced via `options={"verify_exp": True}` (`security.py:46`)
- Audience: `"netlify"` (`security.py:45`)
- Claims used: `sub` (preferred) or `email` as tenant identity (`security.py:100`)

**Mode B — Static Token**

```python
# security.py:70–75
if settings.sonarft_api_token:
    if not hmac.compare_digest(
        token.encode("utf-8"),
        settings.sonarft_api_token.encode("utf-8"),
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")
```

- Timing-safe comparison via `hmac.compare_digest` ✅
- No expiry — static tokens are valid indefinitely ⚠️
- No per-user identity — all static token users share the same `client_id` (from query param)

**Mode C — Dev mode (no auth)**

```python
# security.py:62–63
if not settings.netlify_site_url and not settings.sonarft_api_token:
    return  # dev mode — no auth configured
```

When neither env var is set, all endpoints are publicly accessible. This is intentional for local development but has no runtime warning.

### 1.2 Token Lifecycle

| Property | Netlify JWT | Static Token |
|---|---|---|
| Generation | Netlify Identity (external) | Manual / env var |
| Expiry | Enforced (JWT `exp` claim) | Never expires |
| Refresh | Handled by Netlify Identity | N/A |
| Revocation | Not supported by API | Not supported |
| Rotation | Via Netlify Identity | Manual env var change + restart |

### 1.3 WebSocket Ticket Auth — `websocket/tickets.py`

The ticket system is a well-designed security control:

1. Client exchanges JWT for a 30-second single-use opaque ticket via `POST /ws/ticket`
2. Ticket is passed as `?ticket=` on the WebSocket URL
3. `TicketStore.redeem()` atomically pops the ticket — it cannot be reused
4. Expired tickets (checked via `time.monotonic()`) return `None`
5. The sentinel `"__ticket_verified__"` is passed to `verify_token` to bypass re-validation

The sentinel pattern (`security.py:58`) is clean but relies on the string `"__ticket_verified__"` never appearing as a real token. This is safe in practice (it is not a valid JWT or hex string) but is an implicit contract rather than a typed invariant.

---

## 2. Secret Management

### 2.1 Secret Storage

| Secret | Storage Location | Status |
|---|---|---|
| `NETLIFY_SITE_URL` | `.env` file | ⚠️ `.env` tracked by git (see §2.2) |
| `SONARFT_API_TOKEN` | `.env` file | ⚠️ Same |
| Exchange API keys (`BINANCE_API_KEY`, etc.) | Bot `.env` file | ✅ Bot `.gitignore` excludes `.env` |
| JWT signing key | Netlify Identity (external) | ✅ Never touches the API |
| SQLite database | `sonarftdata/history/sonarft.db` | ✅ Bot `.gitignore` excludes `sonarftdata/history/` |

### 2.2 Critical: `.env` Not in `packages/api/.gitignore`

```
# packages/api/.gitignore — current content:
logs/
```

The bot's `.gitignore` correctly excludes `.env` (`packages/bot/.gitignore` line: `.env`). The API's `.gitignore` does **not**. The committed `packages/api/.env` currently contains empty values:

```
NETLIFY_SITE_URL=
SONARFT_API_TOKEN=
```

This is safe today, but the file is tracked. Any developer who fills in real values and runs `git add .` will commit credentials. This is a **High** severity finding.

### 2.3 No Secrets in Source Code

No hardcoded credentials, API keys, or tokens were found in any Python source file. The `Settings` model reads all secrets from environment variables via `pydantic-settings`. ✅

### 2.4 Exchange API Key Handling — Bot Side

Exchange API keys are loaded from environment variables in `sonarft_bot._load_api_keys()` (`sonarft_bot.py:220–248`). Keys are passed to `SonarftApiManager.set_api_keys()` and stored in the ccxt exchange instance. They are never logged (the method logs `"API keys loaded for exchange: {exchange_id}"` without the key value). ✅

Keys are never transmitted to the API layer — the API has no knowledge of exchange credentials. ✅

---

## 3. Authorization & Access Control

### 3.1 Tenant Isolation

Every bot mutation checks ownership before acting:

```python
# bot_service.py:33–35
def _bot_owned_by(self, botid: str, client_id: str) -> bool:
    return botid in self._manager.get_botids(client_id)
```

This is called in `run_bot`, `stop_bot`, and `remove_bot` before delegating to `BotManager`. If the bot does not belong to the requesting client, `BotNotFoundError` is raised (404) — deliberately not 403, to avoid confirming resource existence. ✅

### 3.2 Authorization Matrix

| Operation | Netlify JWT | Static Token | Dev (no auth) |
|---|---|---|---|
| List own bots | ✅ | ✅ | ✅ |
| Create bot | ✅ | ✅ | ✅ |
| Run/stop/remove own bot | ✅ | ✅ | ✅ |
| Access another client's bot | ❌ 404 | ❌ 404 | ❌ 404 |
| Read own config | ✅ | ✅ | ✅ |
| Write own config | ✅ | ✅ | ✅ |
| Read another client's config | ❌ 404 | ❌ 404 | ❌ 404 |
| Access health endpoint | ✅ (no auth) | ✅ (no auth) | ✅ (no auth) |
| Issue WS ticket | ✅ | ✅ | ✅ |

### 3.3 No RBAC

There is a single role: authenticated user. There are no admin-only endpoints, no read-only roles, and no per-bot permission scopes. For the current single-tenant-per-JWT model this is appropriate. If multi-user organisations are added in future, RBAC will be needed.

### 3.4 `client_id` Derivation in Netlify Mode

In Netlify JWT mode, `client_id` is derived from the JWT `sub` claim (`security.py:100`). The query parameter `client_id` is **ignored** — the identity comes from the verified token. This correctly prevents a user from impersonating another client by passing a different `client_id` query param. ✅

In static token / dev mode, `client_id` comes from the query parameter and is trusted. This is documented behaviour but means any caller who knows the static token can act as any `client_id`. ⚠️

---

## 4. HTTP Security Headers

### 4.1 `SecurityHeadersMiddleware` — `main.py:107–118`

Applied to every HTTP response via `BaseHTTPMiddleware`:

| Header | Value | Assessment |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | ✅ Prevents MIME sniffing |
| `X-Frame-Options` | `DENY` | ✅ Clickjacking protection |
| `Referrer-Policy` | `no-referrer` | ✅ No referrer leakage |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | ✅ 1-year HSTS |
| `Permissions-Policy` | `geolocation=(), microphone=()` | ✅ Feature restriction |
| `Content-Security-Policy` | ❌ Not set | ⚠️ Missing — API responses are JSON so CSP is less critical, but adding `default-src 'none'` would be defence-in-depth |
| `Cache-Control` | ❌ Not set | ⚠️ Sensitive API responses (trade history) could be cached by intermediaries |

### 4.2 CORS Configuration — `main.py:170–177`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,   # from CORS_ORIGINS env var
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

- Origins: explicit allowlist from `CORS_ORIGINS` env var (default: `localhost:3000,localhost:5173`) ✅
- No wildcard `*` ✅
- `allow_credentials=True` is correct — the frontend sends `Authorization` headers ✅
- Methods restricted to the four used by the API ✅
- Headers restricted to `Authorization` and `Content-Type` ✅

The `allowed_origins` property (`core/config.py:28`) splits on commas and strips whitespace — correctly handles multi-origin configuration. ✅

### 4.3 Security Headers Not Applied to WebSocket

`SecurityHeadersMiddleware` uses `BaseHTTPMiddleware` which only intercepts HTTP responses. WebSocket upgrade responses do not pass through this middleware. HSTS and other headers are not sent on the `101 Switching Protocols` response. This is a minor gap — browsers enforce HSTS from prior HTTP responses, so in practice this is not exploitable, but it is worth noting.

---

## 5. Input Validation & Injection Prevention

### 5.1 Path Parameter Validation

All path parameters carrying resource identifiers are validated by regex before reaching service code:

| Parameter | Regex | Location |
|---|---|---|
| `client_id` (canonical) | `^[a-zA-Z0-9_-]{1,64}$` | `clients.py:32` |
| `botid` (canonical) | `^[a-zA-Z0-9_-]{1,64}$` | `clients.py:33` |
| `botid` (legacy) | `^[a-zA-Z0-9_-]{1,64}$` | `bots.py:22` |
| `botid` (WebSocket) | `^[a-zA-Z0-9_-]{1,64}$` | `manager.py:18` |

FastAPI enforces these at the routing layer — invalid values return 422 before any handler code runs. ✅

### 5.2 Config Key Validation

`ParametersConfig` and `IndicatorsConfig` validate all dict keys against `_CONFIG_KEY_RE = re.compile(r'^[\w\s/(). %,:-]{1,128}$')` (`schemas.py:56`). This allowlist blocks path traversal sequences (`../`), shell metacharacters (`;`, `|`, `$`), and null bytes. ✅

`ConfigService._client_path` additionally resolves the final path and checks it stays within `data_dir/config/` (`config_service.py:37–42`):

```python
target = (base / f"{client_id}_{suffix}.json").resolve()
if not str(target).startswith(str(base)):
    raise HTTPException(status_code=400, detail="Invalid client_id")
```

This is a defence-in-depth path traversal guard — even if the regex were bypassed, the resolved path check would catch symlink attacks. ✅

### 5.3 SQL Injection

All SQLite queries use parameterised statements with `?` placeholders (`sonarft_helpers.py:108–116`):

```python
rows = conn.execute(
    f"SELECT data FROM {table} WHERE botid = ?"
    f" ORDER BY id DESC LIMIT ? OFFSET ?",
    (str(botid), limit, offset)
).fetchall()
```

The `table` name is validated against `_ALLOWED_TABLES = frozenset({'orders', 'trades', 'daily_loss'})` before use in the f-string (`sonarft_helpers.py:22`). This prevents table name injection via the one dynamic SQL component. ✅

### 5.4 WebSocket Command Injection

WebSocket commands are parsed as JSON and dispatched by `key` value (`manager.py:155–220`). The `key` field is matched against known string literals (`"create"`, `"run"`, `"remove"`, `"stop"`, `"set_simulation"`). Unknown keys return a `WsErrorEvent` — no command execution occurs. ✅

`botid` values from WebSocket commands are validated against `_BOTID_RE` before use (`manager.py:18`, checked at `manager.py:168,178,188,198,208`). ✅

### 5.5 No Subprocess Calls

The API does not use `subprocess`, `os.system`, or `eval` anywhere. Bot control is via direct Python method calls on `BotManager`. There is no shell injection surface. ✅

### 5.6 Rate Limiting on Auth Endpoints

`POST /ws/ticket` is rate-limited at 30/min (`ws_ticket.py:30`). This limits ticket-farming attacks. The `require_auth` dependency on all protected endpoints means an attacker must first obtain a valid token — brute-forcing the static token is constrained by the 200/min global rate limit and `hmac.compare_digest` (constant-time comparison). ✅

---

## 6. Error Information Disclosure

### 6.1 Error Response Content

| Error Type | Response Body | Internal Details Exposed? |
|---|---|---|
| 401 Unauthorized | `{"detail": "Unauthorized"}` | ❌ No |
| 404 Bot not found | `{"detail": "Bot not found: {botid}"}` | ⚠️ botid echoed back |
| 429 Rate limit | `{"error": "Rate limit exceeded: ..."}` | ⚠️ Limit value exposed |
| 422 Validation | `{"detail": [{"loc":...,"msg":...}]}` | ⚠️ Field names and values exposed |
| 500 Internal error | `{"detail": "Internal server error"}` | ✅ Generic message only |

The 500 handler (`errors.py:32–39`) logs the full exception with stack trace server-side but returns only `"Internal server error"` to the client. ✅

The 404 message echoes the `botid` back to the caller. Since `botid` is a UUID supplied by the caller, this is not an information leak — the caller already knows the value. ✅

### 6.2 Stack Trace Exposure

`generic_error_handler` uses `_logger.exception(...)` which logs the full traceback server-side. The client receives only `{"detail": "Internal server error"}`. No stack traces are returned to clients. ✅

### 6.3 JWT Validation Failure Logging

```python
# security.py:49–51
except InvalidTokenError as exc:
    _logger.warning("JWT validation failed: %s", exc)
    raise HTTPException(status_code=401, detail="Unauthorized") from exc
```

The JWT error detail (e.g. `"Signature has expired"`) is logged server-side but not returned to the client. The client always receives `"Unauthorized"`. ✅

Auth failures from IP are logged with the client IP:

```python
# security.py:84–87
_logger.warning(
    "Auth failure from %s — missing or invalid token",
    _client_ip(request),
)
```

This enables detection of brute-force attempts in log analysis. ✅

### 6.4 `client_id` Redaction in Logs

`bot_service.py` redacts `client_id` in log messages:

```python
_logger.info("Bot created: %s for client: [redacted]", botid)   # line 43
_logger.info("Bot paused: %s for client: [redacted]", botid)    # line 55
```

This is good practice — client identities (which may be email addresses in Netlify JWT mode) are not written to log files. ✅

---

## 7. Token Security

### 7.1 JWT Properties

| Property | Value | Assessment |
|---|---|---|
| Algorithm | RS256 | ✅ Asymmetric — no shared secret |
| Key source | Netlify JWKS (live fetch) | ✅ Automatic key rotation support |
| Expiry | Enforced (`verify_exp: True`) | ✅ |
| Audience | `"netlify"` | ✅ Prevents token reuse across services |
| `none` algorithm | Not accepted | ✅ PyJWT rejects `alg: none` by default |
| Algorithm confusion | Not possible | ✅ `algorithms=["RS256"]` is an explicit allowlist |

### 7.2 Algorithm Confusion Attack

The `jwt.decode` call specifies `algorithms=["RS256"]` explicitly (`security.py:44`). This prevents the classic algorithm confusion attack where an attacker changes the header to `HS256` and signs with the public key. ✅

### 7.3 Token Revocation

There is no JWT blocklist or session invalidation mechanism. A stolen JWT remains valid until its `exp` claim. For Netlify Identity tokens, the TTL is controlled by Netlify (typically 1 hour). For static tokens, there is no expiry — revocation requires changing `SONARFT_API_TOKEN` and restarting the API.

This is a known limitation of stateless JWT authentication. For a trading application handling real money, a short JWT TTL (≤15 minutes) with refresh tokens is recommended.

### 7.4 WebSocket Ticket Security

| Property | Value |
|---|---|
| Ticket format | `secrets.token_urlsafe(32)` — 256 bits of entropy |
| TTL | 30 seconds (`tickets.py:8`) |
| Single-use | ✅ `pop()` on redeem |
| Expiry check | `time.monotonic()` — not wall clock, immune to system time changes |
| Capacity cap | 10,000 tickets (`tickets.py:9`) — prevents memory exhaustion |
| Eviction | Expired tickets purged on each `issue()` call |

The ticket store is well-implemented. The only limitation is that it is in-memory and single-process (see Prompt 01 concern 7.4).

---

## 8. API Key Management

### 8.1 `SONARFT_API_TOKEN` Lifecycle

| Stage | Implementation |
|---|---|
| Generation | Manual — operator sets value in `.env` |
| Storage | Environment variable / `.env` file |
| Validation | `hmac.compare_digest` — timing-safe |
| Rotation | Manual — change env var + restart |
| Revocation | Manual — remove env var + restart |
| Per-key rate limiting | ❌ Not implemented — rate limiting is IP-based |

There is no API endpoint to rotate or regenerate the static token. Rotation requires direct server access.

### 8.2 Exchange API Keys — Bot Side

Exchange keys are loaded from environment variables at bot creation time (`sonarft_bot._load_api_keys()`). They are:
- Never logged ✅
- Never transmitted to the API layer ✅
- Never stored in the SQLite database ✅
- Held only in the ccxt exchange instance in memory

The bot `.env.example` correctly documents the key naming convention (`{EXCHANGE_UPPER}_API_KEY`, `{EXCHANGE_UPPER}_SECRET`) and notes they are only required for live trading. ✅

---

## 9. Dependencies & Known Vulnerabilities

### 9.1 Security-Relevant Dependencies

| Package | Version in `requirements.txt` | Notes |
|---|---|---|
| `fastapi` | `0.135.3` | Current stable release ✅ |
| `uvicorn[standard]` | `0.44.0` | Current stable release ✅ |
| `pydantic` | `>=2.0.0` | Unpinned — any Pydantic v2 ⚠️ |
| `pydantic-settings` | `>=2.0.0` | Unpinned ⚠️ |
| `PyJWT[crypto]` | `>=2.7.0` | Unpinned — `[crypto]` pulls `cryptography` ✅ |
| `slowapi` | `>=0.1.9` | Unpinned ⚠️ |
| `python-dotenv` | `>=1.2.2` | Unpinned ⚠️ |
| `orjson` | unpinned | Unpinned ⚠️ |
| `aiofiles` | unpinned | Unpinned ⚠️ |

### 9.2 Unpinned Dependencies

Most dependencies use `>=` lower bounds with no upper bound. This means `pip install` will always fetch the latest compatible version, which is good for security patches but risks breaking changes. For a production trading system, pinning to exact versions (or using a lockfile) is recommended.

### 9.3 `cryptography` Transitive Dependency

`PyJWT[crypto]` pulls in the `cryptography` package for RS256 support. The `cryptography` library has had several CVEs in past versions (e.g. CVE-2023-49083). Since the version is unpinned, the latest patched version will be installed — this is actually the correct behaviour for security patches, but should be verified in CI with `pip audit` or `safety check`.

### 9.4 No `pip audit` in CI

The GitHub Actions CI workflow runs `npm audit --audit-level=high` for the web package but there is no equivalent Python dependency audit (`pip audit` or `safety`) for the API or bot packages. This is a gap — Python CVEs in transitive dependencies would not be caught automatically.

---

## 10. Compliance & Standards

### 10.1 JWT Best Practices (RFC 7519)

| Best Practice | Status |
|---|---|
| Use asymmetric algorithm (RS256/ES256) | ✅ RS256 |
| Validate `exp` claim | ✅ |
| Validate `aud` claim | ✅ `"netlify"` |
| Explicit algorithm allowlist | ✅ `["RS256"]` |
| Short token lifetime | ✅ Controlled by Netlify Identity |
| No sensitive data in payload | ✅ Only `sub`/`email` used |
| HTTPS transport | ⚠️ Not enforced by API — delegated to reverse proxy |

### 10.2 TLS / HTTPS

The API itself does not enforce HTTPS. TLS termination is expected to be handled by a reverse proxy (nginx, Traefik, or a cloud load balancer). The HSTS header (`max-age=31536000; includeSubDomains`) is set by `SecurityHeadersMiddleware`, which instructs browsers to only connect over HTTPS for future requests — but this only takes effect after the first HTTPS response. If the API is accidentally exposed on HTTP, the HSTS header provides no protection for the first connection.

The `Dockerfile` exposes port 8000 with no TLS. The `infra/docker-compose.yml` should be verified to confirm TLS termination is configured at the proxy layer.

### 10.3 GDPR / Privacy

In Netlify JWT mode, the JWT `sub` or `email` claim is used as `client_id`. If `email` is used, it is a personal identifier. It appears in:
- Log messages (currently redacted as `[redacted]` in `bot_service.py`) ✅
- File paths: `sonarftdata/config/{client_id}_parameters.json` ⚠️ — if `client_id` is an email address, it appears in filesystem paths

The `get_client_id` dependency prefers `sub` over `email` (`security.py:100`): `identity = payload.get("sub") or payload.get("email")`. Using `sub` (an opaque UUID) is strongly preferred over `email` for privacy. This should be documented as a deployment requirement.

---

## 11. Specific Vulnerabilities

### 11.1 Authentication Bypass

**Can endpoints be accessed without tokens?**

- In dev mode (no env vars set): yes, by design. ✅ (documented)
- In production (env vars set): no — `require_auth` and `get_client_id` raise 401. ✅
- Health endpoint: always public — intentional. ✅

**Bypass via `__ticket_verified__` sentinel:**

The sentinel `"__ticket_verified__"` in `verify_token` (`security.py:58`) bypasses all validation. It is only set by the WebSocket endpoint after a ticket is successfully redeemed (`main.py:207`). An attacker who passes the literal string `"__ticket_verified__"` as a Bearer token would bypass auth. However:
- The WebSocket endpoint sets this sentinel only after `store.redeem(ticket)` succeeds
- HTTP endpoints use `require_auth` which calls `verify_token` with the actual Bearer token from the `Authorization` header
- An attacker would need to pass `Authorization: Bearer __ticket_verified__` to an HTTP endpoint

**This is a real bypass vector for HTTP endpoints in dev mode** (where `verify_token` returns early for any token when auth is disabled). In production mode with `SONARFT_API_TOKEN` set, `hmac.compare_digest("__ticket_verified__", settings.sonarft_api_token)` would fail unless the token is literally set to that string. In Netlify JWT mode, `_decode_jwt("__ticket_verified__")` would fail JWT parsing. The risk is **Low** in production but the sentinel should be made unexploitable by design (see Recommendations §13.2 R3).

### 11.2 Authorization Bypass

**Can a user access another user's bots?**

No. `_bot_owned_by` checks `botid in self._manager.get_botids(client_id)` before every mutation. In Netlify JWT mode, `client_id` is derived from the verified JWT `sub` — it cannot be spoofed. ✅

**Can a user read another user's config files?**

No. `_client_path` constructs the path as `{data_dir}/config/{client_id}_{suffix}.json` where `client_id` is validated by regex and the resolved path is checked to stay within `data_dir/config/`. ✅

### 11.3 Brute Force

Static token brute force is constrained by:
- 200 req/min global rate limit (IP-based)
- `hmac.compare_digest` — constant time, no timing oracle

However, the rate limit is IP-based and in-memory. An attacker with multiple IPs or in a multi-worker deployment could exceed the effective limit. No account lockout or progressive delay exists.

### 11.4 Replay Attack on WS Tickets

Tickets are single-use (`pop()` on redeem) and expire in 30 seconds. A captured ticket cannot be replayed. ✅

### 11.5 CORS Bypass

`allow_origins` is an explicit list — no wildcard. `allow_credentials=True` with a wildcard origin would be a critical misconfiguration, but that combination is not present. ✅

---

## 12. Logging & Monitoring

### 12.1 Security Event Logging

| Event | Logged? | Level | Location |
|---|---|---|---|
| JWT validation failure | ✅ | WARNING | `security.py:49` |
| Auth failure (missing token) | ✅ | WARNING | `security.py:84` |
| Auth failure (invalid JWT) | ✅ | WARNING | `security.py:88` |
| Auth failure (invalid static token) | ✅ | WARNING | `security.py:92` |
| WS auth failure | ✅ | WARNING | `manager.py:107` |
| Invalid ticket | ✅ | Implicit (WS close 1008) | `main.py:202` |
| Rate limit exceeded | ✅ | Via slowapi | slowapi middleware |
| Bot creation | ✅ | INFO | `bot_service.py:43` |
| Bot removal | ✅ | INFO | `bot_service.py:58` |
| Unhandled exception | ✅ | ERROR + traceback | `errors.py:32` |

### 12.2 Sensitive Data in Logs

- `client_id` is redacted as `[redacted]` in `bot_service.py` ✅
- JWT tokens are never logged ✅
- Exchange API keys are never logged ✅
- Request bodies are not logged ✅
- The `request_id` ContextVar is injected into every log line, enabling request correlation ✅

### 12.3 Log File Security

The rotating log file is written to `logs/sonarft.log` (relative to `packages/api/`). The `logs/` directory is in `packages/api/.gitignore` ✅. Log files contain IP addresses and auth failure messages — they should be protected with appropriate filesystem permissions (`chmod 640`) in production.

### 12.4 Metrics Log

A separate structured JSON metrics log is written to `logs/sonarft_metrics.jsonl` when `METRICS_LOG_FILE` is set. This file is also excluded by `.gitignore`. The metrics logger has `propagate = False` to prevent duplication into the main log. ✅

---

## 13. Concerns & Recommendations

### 13.1 Vulnerability Summary

| # | Vulnerability | Severity | Location |
|---|---|---|---|
| V1 | **`.env` not in `packages/api/.gitignore`** — credentials will be committed if a developer fills in values | High | `packages/api/.gitignore` |
| V2 | **Auth silently disabled in dev mode** — no warning logged or raised when neither auth env var is set | Medium | `security.py:62–63` |
| V3 | **`__ticket_verified__` sentinel is a string constant** — exploitable as an auth bypass if passed as a Bearer token to HTTP endpoints in dev mode | Low | `security.py:58`, `main.py:207` |
| V4 | **Static token never expires** — a leaked `SONARFT_API_TOKEN` is valid indefinitely until manually rotated | Medium | `security.py:68–75` |
| V5 | **Rate limiting is IP-based only** — multi-IP attackers or multi-worker deployments bypass effective limits | Low | `core/limiter.py` |
| V6 | **No `pip audit` in CI** — Python CVEs in transitive dependencies not caught automatically | Medium | `.github/workflows/ci.yml` |
| V7 | **No `Cache-Control` header on API responses** — trade history could be cached by intermediaries | Low | `main.py` — `SecurityHeadersMiddleware` |
| V8 | **`client_id` may be an email address in filesystem paths** — GDPR concern if Netlify JWT uses `email` as identity | Low | `security.py:100`, `config_service.py:35` |
| V9 | **No token revocation** — stolen JWT valid until expiry; stolen static token valid indefinitely | Medium | `security.py` |
| V10 | **Unpinned Python dependencies** — `pydantic>=2.0.0` etc. could pull breaking changes | Low | `requirements.txt` |

---

### 13.2 Recommendations (Prioritised)

#### P1 — Fix immediately

**R1: Add `.env` to `packages/api/.gitignore`**

```
# packages/api/.gitignore
.env
logs/
```

Also verify the root `.gitignore` covers both packages. Run `git rm --cached packages/api/.env` if the file is already tracked.

**R2: Log a startup warning when auth is disabled**

```python
# core/security.py or main.py lifespan
settings = get_settings()
if not settings.netlify_site_url and not settings.sonarft_api_token:
    logging.getLogger(__name__).warning(
        "⚠️  AUTH DISABLED — no NETLIFY_SITE_URL or SONARFT_API_TOKEN configured. "
        "All endpoints are publicly accessible. Do not use in production."
    )
```

**R3: Replace the `__ticket_verified__` string sentinel with a typed object**

```python
# websocket/tickets.py
class _TicketVerified:
    """Sentinel type — cannot be constructed from a string token."""
    pass

TICKET_VERIFIED = _TicketVerified()

# security.py
def verify_token(token: str | _TicketVerified | None) -> None:
    if isinstance(token, _TicketVerified):
        return  # pre-verified via single-use ticket
    ...
```

A typed sentinel cannot be passed as a Bearer token string — the bypass vector is eliminated by the type system.

---

#### P2 — Address before production

**R4: Add `pip audit` to CI**

```yaml
# .github/workflows/ci.yml
- name: Python dependency audit
  run: |
    pip install pip-audit
    pip-audit -r packages/api/requirements.txt
    pip-audit -r packages/bot/requirements.txt
```

**R5: Add `Cache-Control` header to API responses**

```python
# main.py — SecurityHeadersMiddleware
response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
response.headers["Pragma"] = "no-cache"
```

This prevents trade history and configuration data from being cached by browsers or intermediary proxies.

**R6: Add `Content-Security-Policy` header**

For a pure JSON API, a restrictive CSP provides defence-in-depth:

```python
response.headers["Content-Security-Policy"] = "default-src 'none'"
```

**R7: Enforce `sub` over `email` for `client_id` in Netlify mode**

```python
# security.py:100 — change preference order
identity = payload.get("sub")   # always prefer opaque UUID
if not identity:
    raise HTTPException(status_code=401, detail="Token missing sub claim")
```

Document this as a deployment requirement: Netlify Identity must be configured to include `sub` in the JWT payload (it does by default).

---

#### P3 — Longer term

**R8: Add static token expiry via a signed token with TTL**

Replace the bare static token with a HMAC-signed token that includes an expiry timestamp:

```python
# core/security.py
import hmac, hashlib, time, base64

def issue_api_token(secret: str, ttl_seconds: int = 86400) -> str:
    exp = int(time.time()) + ttl_seconds
    payload = f"{exp}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}.{sig}".encode()).decode()
```

**R9: Pin Python dependencies with a lockfile**

Use `pip-compile` (pip-tools) or `uv lock` to generate a pinned `requirements.lock` for production deployments. Use `requirements.txt` with `>=` bounds for development flexibility.

**R10: Add `X-RateLimit-*` response headers for per-user limits**

Implement per-`client_id` rate limiting alongside IP-based limiting (see Prompt 02 R10) and expose `X-RateLimit-Remaining` headers so clients can self-throttle.

---

## Security Hardening Checklist

- [ ] Add `.env` to `packages/api/.gitignore` and run `git rm --cached`
- [ ] Log startup warning when auth is disabled
- [ ] Replace `__ticket_verified__` string sentinel with typed object
- [ ] Add `pip audit` to CI pipeline
- [ ] Add `Cache-Control: no-store` to `SecurityHeadersMiddleware`
- [ ] Add `Content-Security-Policy: default-src 'none'`
- [ ] Enforce `sub` claim (not `email`) as `client_id` in Netlify mode
- [ ] Verify TLS termination is configured at the reverse proxy layer
- [ ] Set filesystem permissions `640` on log files in production
- [ ] Document static token rotation procedure in ops runbook
- [ ] Consider short-TTL static tokens for production deployments
- [ ] Pin Python dependencies with a lockfile for production

---

## Related Prompts

- [Prompt 01: Architecture Structure](../architecture/01-api-architecture.md) — Security architecture
- [Prompt 03: Data Models & Validation](../models/03-data-models-validation.md) — Input validation
- [Prompt 06: Error Handling & Logging](../error-handling/06-error-handling-logging.md) — Log security
- [Prompt 05: WebSocket & Real-time](../websocket/05-websocket-realtime.md) — WS auth

---

_Part of the SonarFT API Code Review Prompt Suite — Prompt 04_
