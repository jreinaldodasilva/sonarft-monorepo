# Authentication, Security & Authorization Review

**Prompt ID:** 04-API-SECURITY  
**Package:** `packages/api`  
**Output:** `docs/security/04-authentication-security.md`  
**Reviewed:** July 2025  
**Status:** Complete

---

## Executive Summary

The SonarFT API has a solid security foundation: timing-safe token comparison, ticket-based WebSocket auth that keeps JWTs out of server logs, comprehensive security headers, path-traversal prevention on config file paths, and a table-allowlist guard on all SQLite queries. The most significant finding is a **data isolation vulnerability** (carried forward from Prompt 01/02): `BotService.get_orders()` and `get_trades()` accept a `client_id` parameter but never verify that the requested `botid` belongs to that client before querying the database. Any authenticated user who knows or guesses a `botid` can read another client's full trade history. A secondary concern is the **open-by-default auth mode**: when neither `NETLIFY_SITE_URL` nor `SONARFT_API_TOKEN` is set, all endpoints are publicly accessible with no authentication whatsoever — this is intentional for development but the only safeguard is a startup log warning, which is easy to miss in a containerised deployment. No SQL injection vulnerabilities were found — all SQLite queries use parameterised statements and a table-name allowlist.

---

## Security Score Card

| Area | Status | Notes |
|---|---|---|
| JWT validation | ✅ Secure | RS256, `verify_exp=True`, JWKS rotation supported |
| Static token comparison | ✅ Secure | `hmac.compare_digest()` — timing-safe |
| WebSocket auth | ✅ Secure | Single-use tickets, 30s TTL, JWT kept out of URL |
| Security headers | ✅ Secure | HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy |
| CORS configuration | ✅ Secure | Explicit origin allowlist, no wildcard |
| SQL injection | ✅ Secure | Parameterised queries + table-name allowlist |
| Path traversal | ✅ Secure | `ID_PATTERN` regex + `Path.resolve()` containment check |
| Input validation | ✅ Secure | `ID_PATTERN` on all IDs; config key regex |
| Secret storage | ✅ Secure | Environment variables only; `.env` in `.gitignore` |
| Exchange key handling | ✅ Secure | Keys never touch the API layer |
| Error information disclosure | ✅ Secure | Generic 500 message; no stack traces to clients |
| Client ID logging | ✅ Secure | `[redacted]` in `BotService` log lines |
| Data isolation (orders/trades) | ❌ **Vulnerable** | `get_orders`/`get_trades` missing ownership check |
| Auth open-by-default | ⚠️ Risk | Dev mode disables all auth; only a log warning guards it |
| Token revocation | ⚠️ Not implemented | No JWT blocklist; compromised tokens valid until expiry |
| Per-client rate limiting | ⚠️ Not implemented | IP-based only; shared proxy collapses all clients |

---

## 1. Authentication Mechanism

### Netlify JWT mode (`security.py:31-47`)

- Algorithm: `RS256` (asymmetric — private key never touches the API)
- Key source: `{NETLIFY_SITE_URL}/.netlify/identity/keys` (JWKS endpoint)
- `PyJWKClient` is initialised once at import time and cached in `_jwks_client_holder`
- `verify_exp=True` — token expiry is enforced
- Audience: `"netlify"` — prevents tokens issued for other services being accepted
- `InvalidTokenError` is caught and re-raised as `HTTPException(401)` — no internal detail leaks

**JWKS key rotation:** `PyJWKClient` fetches the JWKS URL on first use and caches the signing key. It does not automatically refresh when Netlify rotates keys. If Netlify rotates its signing key, all subsequent JWT validations will fail until the API process is restarted. `PyJWT >= 2.4` supports `PyJWKClient(url, cache_jwk_set=True, lifespan=300)` for automatic refresh.

### Static token mode (`security.py:75-82`)

```python
if not hmac.compare_digest(
    token.encode("utf-8"),
    settings.sonarft_api_token.encode("utf-8"),
):
    raise HTTPException(status_code=401, detail="Unauthorized")
```

`hmac.compare_digest()` is used correctly — constant-time comparison prevents timing attacks. The token is read from `SONARFT_API_TOKEN` environment variable.

**No token rotation mechanism exists.** A compromised static token requires a manual environment variable change and process restart.

### Dev mode (`security.py:68-70`)

```python
if not settings.netlify_site_url and not settings.sonarft_api_token:
    return  # dev mode — no auth configured
```

When neither auth variable is set, `verify_token()` returns immediately for any input including `None`. This is intentional for local development but creates a silent open deployment risk. The only safeguard is a `WARNING` log at startup (`main.py:_lifespan`). A misconfigured production deployment with empty env vars would be fully open with no runtime indication beyond the log line.

### Token refresh

No token refresh is implemented. JWT expiry is enforced but there is no refresh endpoint. Clients must re-authenticate via Netlify Identity when their token expires.

---

## 2. WebSocket Authentication (`websocket/tickets.py`, `websocket.py`)

The ticket-based auth pattern is correctly implemented:

1. Client authenticates via `POST /ws/ticket` with a valid Bearer token → receives a 32-byte `secrets.token_urlsafe()` ticket
2. Client opens `WS /ws/{client_id}?ticket=<ticket>` — ticket is redeemed once and deleted
3. If the ticket is invalid or expired, the WebSocket is closed with code `1008` (Policy Violation)
4. The `_TICKET_VERIFIED_SENTINEL` constant (`"__ticket_verified__"`) is passed as the token to `verify_token()`, which returns immediately — the sentinel is not a valid JWT or hex string and cannot be forged by a client

**Ticket security properties:**
- `secrets.token_urlsafe(32)` — 256 bits of entropy, cryptographically random
- 30-second TTL enforced via `time.monotonic()`
- Single-use: `_tickets.pop(ticket, None)` atomically removes on redeem
- Capacity cap: `_MAX_TICKETS = 10_000` prevents memory exhaustion
- Expired ticket eviction on every `issue()` call

**One gap:** The ticket store is a module-level singleton (`_store = TicketStore()` in `tickets.py:57`). In a multi-worker deployment (multiple uvicorn workers or processes), each worker has its own in-memory store. A ticket issued by worker A cannot be redeemed by worker B. This is not a security vulnerability but a correctness issue under horizontal scaling.

---

## 3. Authorization & Access Control

### Authorization matrix

| Operation | Auth Required | Ownership Check | Notes |
|---|---|---|---|
| List bots | ✅ | ✅ `get_botids(client_id)` | Returns only client's bots |
| Create bot | ✅ | ✅ Limit check per client | |
| Run bot | ✅ | ✅ `_bot_owned_by()` | |
| Stop bot | ✅ | ✅ `_bot_owned_by()` | |
| Remove bot | ✅ | ✅ `_bot_owned_by()` | |
| Get orders | ✅ | ❌ **Missing** | Any client can read any bot's orders |
| Get trades | ✅ | ❌ **Missing** | Any client can read any bot's trades |
| Get parameters | ✅ | ✅ Path-scoped to `client_id` | File path includes `client_id` |
| Update parameters | ✅ | ✅ Path-scoped to `client_id` | |
| Get indicators | ✅ | ✅ Path-scoped to `client_id` | |
| Update indicators | ✅ | ✅ Path-scoped to `client_id` | |
| WS commands (run/stop/remove) | ✅ | ⚠️ Partial | `_BOTID_RE` validates format but no ownership check in `_receive_loop` |

### Data isolation vulnerability (`bot_service.py:72-85`)

`get_orders()` and `get_trades()` both accept `client_id` but pass only `botid` to `SonarftHelpers._async_query()`:

```python
# bot_service.py:72-85 — client_id is accepted but never used
async def get_orders(self, botid: str, client_id: str, ...) -> list:
    return await self._helpers._async_query("orders", botid, limit, offset, from_ts, to_ts)
```

The SQLite query in `sonarft_helpers.py:_db_query()` filters only by `botid`:

```sql
SELECT data FROM orders WHERE botid = ? ORDER BY id DESC LIMIT ? OFFSET ?
```

An authenticated client who knows or guesses a `botid` belonging to another client can retrieve that client's complete order and trade history, including exchange names, prices, amounts, and profit figures.

### WebSocket command ownership

In `WebSocketManager._receive_loop()` (`manager.py:148-215`), the `run`, `stop`, and `remove` commands validate `botid` format via `_BOTID_RE` but do not verify that the `botid` belongs to the authenticated `client_id`. A client can issue `{"key": "stop", "botid": "<other_client_botid>"}` and stop another client's bot if they know its ID.

---

## 4. HTTP Security Headers (`main.py:SecurityHeadersMiddleware`)

All headers are applied to every response via `SecurityHeadersMiddleware`:

| Header | Value | Assessment |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | ✅ |
| `X-Frame-Options` | `DENY` | ✅ |
| `Referrer-Policy` | `no-referrer` | ✅ |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | ✅ |
| `Permissions-Policy` | `geolocation=(), microphone=()` | ✅ |
| `Cache-Control` | `no-store, no-cache, must-revalidate` | ✅ |
| `Pragma` | `no-cache` | ✅ |
| `Content-Security-Policy` | `default-src 'none'` | ✅ Appropriate for a pure JSON API |

**HSTS note:** `Strict-Transport-Security` is set unconditionally, including on HTTP responses in development. Browsers that receive HSTS over HTTP will ignore it (per spec), so this is harmless but slightly misleading in dev.

### CORS (`main.py:create_app`)

```python
CORSMiddleware(
    allow_origins=settings.allowed_origins,  # from CORS_ORIGINS env var
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

- No wildcard origins — `allowed_origins` is parsed from `CORS_ORIGINS` env var
- Default in `config.py`: `"http://localhost:3000,http://localhost:5173"` — development only
- `allow_credentials=True` is correct since the frontend sends `Authorization` headers
- Methods are explicitly enumerated — `PATCH` and `OPTIONS` are not allowed (OPTIONS is handled automatically by the middleware)

---

## 5. Input Validation & Injection Prevention

### Path parameter validation

All `botid` and `client_id` path parameters are validated against `ID_PATTERN`:

```python
ID_PATTERN = r"^[a-zA-Z0-9_-]{1,64}$"
```

This blocks path traversal (`../`), shell metacharacters (`;`, `|`, `&`), and null bytes. Validated at the FastAPI routing layer before any handler code runs.

### Config file path traversal prevention (`config_service.py:36-46`)

```python
base = Path(data_dir).resolve() / "config"
target = (base / f"{client_id}_{suffix}.json").resolve()
if not str(target).startswith(str(base)):
    raise HTTPException(status_code=400, detail="Invalid client_id")
```

Double defence: `ID_PATTERN` regex on `client_id` + `Path.resolve()` containment check. Even if a symlink or encoded sequence bypassed the regex, the resolved path check would catch it.

### SQL injection prevention (`sonarft_helpers.py`)

All SQLite queries use parameterised statements (`?` placeholders). The table name is validated against `_ALLOWED_TABLES = frozenset({'orders', 'trades', 'daily_loss', 'positions', 'errors', 'balances'})` before use in any f-string interpolation. This is the correct defence — table names cannot be parameterised in SQLite, so the allowlist is the right approach.

The `from_ts` and `to_ts` timestamp parameters are passed as bound parameters (`params.append(from_ts)`), not interpolated — no SQL injection risk even though they are not format-validated at the API layer (noted in Prompt 02 as H1).

### Config key validation (`schemas.py:50`)

```python
_CONFIG_KEY_RE = re.compile(r'^[\w\s/(). %,:-]{1,128}$')
```

Applied to all keys in `exchanges`, `symbols`, `periods`, `oscillators`, and `movingaverages` dicts. Blocks `<script>`, null bytes, and shell metacharacters.

---

## 6. Error Information Disclosure

| Error type | Response body | Stack trace exposed? | Assessment |
|---|---|---|---|
| `BotNotFoundError` | `{"detail": "Bot not found: {botid}", "request_id": "..."}` | ❌ No | ✅ |
| `BotLimitExceededError` | `{"detail": "Bot limit reached: {limit}", "request_id": "..."}` | ❌ No | ✅ |
| `ConfigNotFoundError` | `{"detail": "{message}", "request_id": "..."}` | ❌ No | ✅ |
| `HTTPException` | `{"detail": "{exc.detail}", "request_id": "..."}` | ❌ No | ✅ |
| Unhandled `Exception` | `{"detail": "Internal server error", "request_id": "..."}` | ❌ No | ✅ |
| Auth failure | `{"detail": "Unauthorized"}` | ❌ No | ✅ |

The generic handler (`errors.py:generic_error_handler`) logs the full exception with `_logger.exception()` (server-side only) and returns only `"Internal server error"` to the client. No stack traces, file paths, or internal state are exposed.

Auth failure log lines include the client IP but not the token value:
```python
_logger.warning("Auth failure from %s — missing or invalid token", _client_ip(request))
```

`BotService` log lines redact `client_id`:
```python
_logger.info("Bot created: %s for client: [redacted]", botid)
```

---

## 7. Secret Management

### API secrets

| Secret | Storage | Rotation | Assessment |
|---|---|---|---|
| `SONARFT_API_TOKEN` | Environment variable | Manual restart | ✅ Not hardcoded |
| `NETLIFY_SITE_URL` | Environment variable | N/A (URL, not secret) | ✅ |
| Exchange API keys | Bot `.env` only | Manual | ✅ Never touch API layer |

Exchange API keys (`BINANCE_API_KEY`, `OKX_SECRET`, etc.) are loaded exclusively by `packages/bot/sonarft_api_manager.py` from environment variables. They are never passed to or stored by the API layer. The API has no knowledge of exchange credentials.

The `.env` file is listed in `.gitignore` in both packages. The `.env.example` files contain only placeholder comments — no real credentials.

### Sensitive data in logs

- Client IDs are redacted in `BotService` log lines (`[redacted]`)
- Tokens are never logged (auth failure logs record IP only)
- Exchange API keys are never logged by the bot (confirmed by inspection of `sonarft_api_manager.py` — keys are passed directly to ccxt constructors, not logged)

---

## 8. Dependencies

| Package | Version in `requirements.txt` | Known CVEs | Notes |
|---|---|---|---|
| `fastapi` | `0.135.3` | None known | Current as of July 2025 |
| `uvicorn[standard]` | `0.44.0` | None known | Current |
| `PyJWT[crypto]` | `>=2.7.0` | None known | `[crypto]` pulls `cryptography` for RS256 |
| `pydantic` | `>=2.0.0` | None known | v2 — no v1 compat issues |
| `slowapi` | `>=0.1.9` | None known | |
| `orjson` | unpinned | None known | ⚠️ No version pin |

`orjson` has no version pin in `requirements.txt`. A breaking change or security patch in `orjson` would not be automatically applied or blocked. All other packages are pinned or have lower-bound constraints.

---

## Concerns & Recommendations

### Critical

None found.

### High

| # | Concern | Location | Detail |
|---|---|---|---|
| H1 | **Data isolation: `get_orders`/`get_trades` missing ownership check** | `bot_service.py:72-85` | Any authenticated client who knows a `botid` can read another client's complete trade history. Fix: add `_bot_owned_by()` check before querying. |
| H2 | **WebSocket commands lack ownership verification** | `websocket/manager.py:_receive_loop` | `run`, `stop`, and `remove` commands validate `botid` format but not ownership. A client can stop or remove another client's bot. Fix: verify `botid in bot_manager.get_botids(client_id)` before dispatching each command. |

### Medium

| # | Concern | Location | Detail |
|---|---|---|---|
| M1 | **Open-by-default auth with only a log warning as safeguard** | `core/security.py:68-70`, `main.py:_lifespan` | A misconfigured production deployment (empty env vars) is fully open. Consider failing hard at startup rather than warning. |
| M2 | **JWKS client does not auto-refresh on key rotation** | `core/security.py:31-35` | `PyJWKClient` is initialised once. Netlify key rotation requires a process restart. Use `PyJWKClient(url, cache_jwk_set=True, lifespan=300)`. |
| M3 | **No token revocation for static tokens** | `core/security.py` | A compromised `SONARFT_API_TOKEN` is valid until the env var is changed and the process restarted. No blocklist or invalidation mechanism exists. |
| M4 | **Ticket store is in-memory only** | `websocket/tickets.py:57` | In a multi-worker deployment, tickets issued by one worker cannot be redeemed by another. Not a security issue in single-worker mode but a correctness risk if scaled. |

### Low

| # | Concern | Location | Detail |
|---|---|---|---|
| L1 | **`orjson` has no version pin** | `requirements.txt:8` | Add `orjson>=3.9,<4` to prevent unexpected breaking changes. |
| L2 | **HSTS header sent over HTTP in development** | `main.py:SecurityHeadersMiddleware` | Harmless (browsers ignore HSTS over HTTP) but misleading. Consider gating on `settings.api_debug`. |
| L3 | **No brute-force protection on static token endpoint** | `core/security.py` | The 20/min rate limit on bot endpoints applies, but there is no specific limit on auth attempts. The global 200/min limit provides some protection. |
| L4 | **`_TICKET_VERIFIED_SENTINEL` is a module-level string constant** | `core/security.py:24` | If the sentinel value were ever logged or exposed in an error message, it could theoretically be used to bypass ticket validation. The value is not a valid JWT or hex string, making accidental exposure low-risk, but a non-string sentinel (e.g. a dedicated object) would be more robust. |

---

## Recommendations

### Priority 1 — Fix before production

**R1 (H1): Add ownership check to `get_orders` and `get_trades`**

```python
# bot_service.py
async def get_orders(self, botid: str, client_id: str, ...) -> list:
    if not self._bot_owned_by(botid, client_id):
        raise BotNotFoundError(botid)
    return await self._helpers._async_query("orders", botid, limit, offset, from_ts, to_ts)

async def get_trades(self, botid: str, client_id: str, ...) -> list:
    if not self._bot_owned_by(botid, client_id):
        raise BotNotFoundError(botid)
    return await self._helpers._async_query("trades", botid, limit, offset, from_ts, to_ts)
```

**R2 (H2): Add ownership check to WebSocket command handlers**

```python
# websocket/manager.py — _receive_loop, for run/stop/remove commands
elif key in ("run", "stop", "remove"):
    if not botid or not _BOTID_RE.match(str(botid)):
        await self._push_model(client_id, WsErrorEvent(...))
    elif botid not in bot_manager.get_botids(client_id):
        await self._push_model(client_id, WsErrorEvent(
            message="Bot not found", ts=int(time.time()),
        ))
    else:
        task = asyncio.create_task(self._handle_run/stop/remove(...))
```

---

### Priority 2

**R3 (M1): Fail hard at startup when auth is not configured in production**

Add a `SONARFT_ENV` or `SONARFT_REQUIRE_AUTH` env var and fail at startup if auth is disabled in non-dev mode:

```python
# main.py:_lifespan
if not settings.netlify_site_url and not settings.sonarft_api_token:
    if os.environ.get("SONARFT_ENV", "development") != "development":
        raise RuntimeError(
            "AUTH DISABLED in non-development environment. "
            "Set NETLIFY_SITE_URL or SONARFT_API_TOKEN."
        )
    _logger.warning("⚠️  AUTH DISABLED ...")
```

**R4 (M2): Enable JWKS auto-refresh**

```python
# core/security.py
_jwks_client_holder[0] = PyJWKClient(
    url,
    cache_jwk_set=True,
    lifespan=300,  # refresh every 5 minutes
)
```

---

### Priority 3

**R5 (L1): Pin `orjson` version**

```
orjson>=3.9,<4
```

**R6 (L4): Replace string sentinel with a dedicated object**

```python
# core/security.py
class _TicketVerifiedSentinel:
    """Opaque sentinel — cannot be forged from a string token."""
    __slots__ = ()

_TICKET_VERIFIED = _TicketVerifiedSentinel()

# verify_token signature change:
def verify_token(token: str | _TicketVerifiedSentinel | None) -> None:
    if isinstance(token, _TicketVerifiedSentinel):
        return
    ...
```

---

## Security Hardening Checklist

- [x] RS256 JWT validation with JWKS
- [x] Timing-safe static token comparison
- [x] Single-use WebSocket tickets (JWT out of URL/logs)
- [x] Security headers (HSTS, CSP, X-Frame-Options, etc.)
- [x] Explicit CORS origin allowlist
- [x] Parameterised SQL queries
- [x] Table-name allowlist for dynamic SQL
- [x] Path traversal prevention (regex + `Path.resolve()`)
- [x] Config key injection prevention (regex allowlist)
- [x] No stack traces in error responses
- [x] Client ID redacted in log lines
- [x] Exchange keys isolated to bot package
- [ ] **Ownership check on `get_orders`/`get_trades`** ← H1
- [ ] **Ownership check on WebSocket commands** ← H2
- [ ] JWKS auto-refresh on key rotation ← M2
- [ ] Hard startup failure when auth disabled in production ← M1
- [ ] `orjson` version pin ← L1

---

_Generated by Amazon Q Developer — SonarFT API Code Review Prompt Suite, Prompt 04_


---

## Post-Implementation Update (July 2025)

### Resolved findings

| ID | Finding | Resolution |
|---|---|---|
| H1 | `get_orders`/`get_trades` missing ownership check | `_bot_owned_by()` guard added — foreign `botid` returns 404 |
| H2 | WS commands lack ownership verification | `botid not in bot_manager.get_botids(client_id)` guard in `_receive_loop` for `run`/`stop`/`remove` |
| M1 | Open-by-default auth with only a log warning | `RuntimeError` raised at startup when `SONARFT_ENV != development` and no auth configured |
| M2 | JWKS client does not auto-refresh | `PyJWKClient(cache_jwk_set=True, lifespan=300)` — refreshes every 5 minutes |

### Updated security scorecard

| Area | Status |
|---|---|
| JWT validation | ✅ RS256, `verify_exp=True`, JWKS auto-refresh every 5 min |
| Static token comparison | ✅ `hmac.compare_digest()` |
| WebSocket auth | ✅ Single-use tickets, 30s TTL |
| Security headers | ✅ Full stack |
| CORS | ✅ Explicit allowlist |
| SQL injection | ✅ Parameterised queries + table allowlist |
| Path traversal | ✅ Regex + `Path.resolve()` containment |
| Data isolation (orders/trades) | ✅ **Fixed** — `_bot_owned_by()` guard |
| WS command ownership | ✅ **Fixed** — ownership check in `_receive_loop` |
| Auth open-by-default | ✅ **Fixed** — `RuntimeError` in non-development environments |
| Token revocation | ⚠️ Not implemented — static token requires env var change + restart |
| Per-client rate limiting | ⚠️ IP-based only |
