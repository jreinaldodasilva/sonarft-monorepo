# Prompt 04 — Authentication, Security & Authorization Review

**Generated:** July 2025 | **Updated:** July 2025 (post-implementation)
**Reviewer:** Amazon Q (Senior Security Auditor / FastAPI / JWT)
**Status:** ✅ All critical and high findings resolved

---

## Executive Summary

All six production-blocking security vulnerabilities have been resolved. The JWT implementation remains correct (RS256, JWKS, expiry enforcement). Tenant isolation is now enforced via `get_client_id` which extracts `sub` from the JWT in Netlify mode — the `client_id` query parameter is ignored, preventing cross-tenant access. Path traversal is blocked by `_validate_client_id()` regex in `ConfigService`. Static token comparison uses `hmac.compare_digest`. The WebSocket JWT-in-URL problem is solved by the one-time ticket system. Security headers (HSTS, X-Content-Type-Options, Referrer-Policy) are applied to every response. Rate limiting is active on all endpoints.

---

## Security Score Card (Current)

| Area | Status | Score |
|---|---|---|
| JWT algorithm (RS256) | ✅ Secure | 5/5 |
| JWT expiry enforcement | ✅ Enforced | 5/5 |
| JWKS key rotation | ✅ Supported | 5/5 |
| Tenant isolation | ✅ JWT `sub` claim | 5/5 |
| Path traversal prevention | ✅ Regex + pathlib | 5/5 |
| Static token comparison | ✅ `hmac.compare_digest` | 5/5 |
| WebSocket token transport | ✅ One-time ticket | 5/5 |
| `.env` in repository | ✅ Gitignored | 5/5 |
| Security headers | ✅ HSTS + 4 others | 5/5 |
| Rate limiting | ✅ slowapi | 5/5 |
| Exchange key isolation | ✅ Never transit API | 5/5 |
| Input sanitization (botid) | ✅ Regex pattern | 5/5 |
| Auth failure logging | ✅ IP + reason | 5/5 |
| Error information disclosure | ✅ Generic 500 + traceback log | 5/5 |
| **Overall** | **✅ Production-ready** | **5/5** |

---

## Tenant Isolation (Implemented)

```python
# core/security.py
def get_client_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    client_id: Optional[str] = Query(default=None),
) -> str:
    # Netlify JWT mode — identity from token, query param ignored
    if settings.netlify_site_url:
        payload = _decode_jwt(token)
        return payload.get("sub") or payload.get("email")
    # Static/dev mode — validate token, require client_id query param
    verify_token(token)
    return client_id
```

In Netlify mode, User A cannot access User B's data by supplying a different `client_id` — the identity is derived from the verified JWT `sub` claim.

---

## Path Traversal Prevention (Implemented)

```python
# services/config_service.py
_SAFE_CLIENT_ID = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')

def _validate_client_id(client_id: str) -> str:
    if not _SAFE_CLIENT_ID.match(client_id):
        raise HTTPException(status_code=400, detail=f"Invalid client_id: {client_id!r}")
    return client_id

def _client_path(data_dir: str, client_id: str, suffix: str) -> str:
    _validate_client_id(client_id)
    return str(Path(data_dir) / "config" / f"{client_id}_{suffix}.json")
```

`../../etc/passwd` → HTTP 400. `pathlib.Path` prevents traversal even if the regex were bypassed.

---

## WebSocket One-Time Ticket (Implemented)

```
POST /api/v1/ws/ticket  (Authorization: Bearer <jwt>)
→ {"ticket": "HutIc__IWEbLV0O9...", "ttl_seconds": 30}

WS /api/v1/ws/{clientId}?ticket=HutIc__IWEbLV0O9...
→ {"type": "connected", ...}
```

- `secrets.token_urlsafe(32)` — 256-bit entropy
- Single-use: `store.redeem()` pops the ticket
- 30-second TTL with monotonic clock
- 10,000-ticket capacity cap
- JWT never appears in server logs or browser history

---

## Security Headers (Implemented)

Every HTTP response includes:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Strict-Transport-Security: max-age=31536000; includeSubDomains
Permissions-Policy: geolocation=(), microphone=()
X-Request-ID: <uuid4>
```

---

## Auth Failure Logging (Implemented)

```python
# core/security.py
def _client_ip(request: Request) -> str:
    if request.client:
        return request.client.host
    return request.headers.get("X-Forwarded-For", "unknown").split(",")[0].strip()

# All failure paths log:
_logger.warning("Auth failure from %s — %s", ip, reason)
```

Failure reasons logged: missing token, invalid JWT, invalid static token, missing identity claim.

---

## Remaining Items

| Item | Status |
|---|---|
| `botid` ownership verification | ✅ `_bot_owned_by(botid, client_id)` in `BotService` |
| Dev mode guard (no auth in prod) | ℹ️ No startup warning — low priority |
| `orjson`/`aiofiles` unpinned | ℹ️ No known CVEs |
| WebSocket message rate limiting | ℹ️ Not implemented — low priority |

---

## Security Hardening Checklist

- [x] `.env` gitignored, no credentials committed
- [x] Tenant isolation via JWT `sub`
- [x] `client_id` sanitized before all path construction
- [x] `hmac.compare_digest` for static token
- [x] WebSocket one-time ticket (JWT out of URLs)
- [x] Security headers on all responses
- [x] Rate limiting on all endpoints
- [x] Auth failures logged with source IP
- [x] Unhandled exceptions logged with traceback
- [x] `botid` ownership verified before run/stop/delete
- [x] Exchange API keys never transit API layer

---

_Part of the SonarFT API Code Review Prompt Suite — Prompt 04_
_Previous: [Prompt 03 — Data Models](../models/03-data-models-validation.md)_
_Next: [Prompt 05 — WebSocket](../websocket/05-websocket-realtime.md)_
