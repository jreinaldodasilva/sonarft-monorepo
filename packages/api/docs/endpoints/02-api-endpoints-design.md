# API Endpoints Design & REST Contract Review

**Prompt ID:** 02-API-ENDPOINTS  
**Package:** `packages/api`  
**Reviewer:** Amazon Q (Senior Python / FastAPI / REST Design)  
**Date:** July 2025  
**Status:** Complete

---

## Executive Summary

The SonarFT API exposes 22 endpoints across five routers, split between a canonical resource-path design (`/clients/{client_id}/...`) and a deprecated query-parameter design (`/bots?client_id=`, `/parameters?client_id=`). HTTP method usage is correct throughout — no state-mutating GETs, idempotent PUTs used for config updates, and DELETE used for bot removal. The canonical routes follow REST conventions cleanly; the legacy routes have minor inconsistencies (POST used for run/stop instead of a more RESTful sub-resource pattern). Pagination is implemented on history endpoints with `limit`/`offset` but is absent from the bot list endpoint. Rate limiting is applied per-endpoint with appropriate tiers. The main design concerns are: the WebSocket endpoint is invisible to OpenAPI, the legacy routes duplicate all canonical logic, `stop` uses POST rather than a dedicated state sub-resource, and there is no standardised error envelope beyond `{"detail": "..."}`.

---

## 1. Complete Endpoint Reference Table

### 1.1 Canonical Routes — `/clients/{client_id}/...` (`clients.py`)

| Method | Path | Handler | Auth | Rate Limit | Status Codes | Description |
|---|---|---|---|---|---|---|
| `GET` | `/api/v1/clients/{client_id}/bots` | `list_bots` | ✅ required | 60/min | 200, 401, 429 | List all bot IDs for a client |
| `POST` | `/api/v1/clients/{client_id}/bots` | `create_bot` | ✅ required | 10/min | 201, 401, 429 | Create a new bot |
| `POST` | `/api/v1/clients/{client_id}/bots/{botid}/run` | `run_bot` | ✅ required | 20/min | 200, 401, 404, 429 | Start a bot |
| `POST` | `/api/v1/clients/{client_id}/bots/{botid}/stop` | `stop_bot` | ✅ required | 20/min | 200, 401, 404, 429 | Pause a running bot |
| `DELETE` | `/api/v1/clients/{client_id}/bots/{botid}` | `remove_bot` | ✅ required | 20/min | 200, 401, 404, 429 | Remove a bot |
| `GET` | `/api/v1/clients/{client_id}/bots/{botid}/orders` | `get_orders` | ✅ required | 60/min | 200, 401, 429 | Get order history |
| `GET` | `/api/v1/clients/{client_id}/bots/{botid}/trades` | `get_trades` | ✅ required | 60/min | 200, 401, 429 | Get trade history |
| `GET` | `/api/v1/clients/{client_id}/parameters` | `get_parameters` | ✅ required | 60/min | 200, 401, 404, 429 | Get trading parameters |
| `PUT` | `/api/v1/clients/{client_id}/parameters` | `update_parameters` | ✅ required | 30/min | 200, 401, 422, 429 | Update trading parameters |
| `GET` | `/api/v1/clients/{client_id}/indicators` | `get_indicators` | ✅ required | 60/min | 200, 401, 404, 429 | Get indicator settings |
| `PUT` | `/api/v1/clients/{client_id}/indicators` | `update_indicators` | ✅ required | 30/min | 200, 401, 422, 429 | Update indicator settings |

### 1.2 Legacy Routes — deprecated (`bots.py`, `config.py`)

| Method | Path | Handler | Auth | Rate Limit | Status Codes | Description |
|---|---|---|---|---|---|---|
| `GET` | `/api/v1/bots` | `list_bots` | ✅ required | 60/min | 200, 401, 429 | List bots (`?client_id=`) |
| `POST` | `/api/v1/bots` | `create_bot` | ✅ required | 10/min | 201, 401, 429 | Create bot (`?client_id=`) |
| `POST` | `/api/v1/bots/{botid}/run` | `run_bot` | ✅ required | 20/min | 200, 401, 404, 429 | Start bot |
| `POST` | `/api/v1/bots/{botid}/stop` | `stop_bot` | ✅ required | 20/min | 200, 401, 404, 429 | Stop bot |
| `DELETE` | `/api/v1/bots/{botid}` | `remove_bot` | ✅ required | 20/min | 200, 401, 404, 429 | Remove bot |
| `GET` | `/api/v1/bots/{botid}/orders` | `get_orders` | ✅ required | 60/min | 200, 401, 429 | Order history |
| `GET` | `/api/v1/bots/{botid}/trades` | `get_trades` | ✅ required | 60/min | 200, 401, 429 | Trade history |
| `GET` | `/api/v1/parameters/defaults` | `get_default_parameters` | ✅ required | 60/min | 200, 401, 404, 429 | Default parameters |
| `GET` | `/api/v1/parameters` | `get_parameters` | ✅ required | 60/min | 200, 401, 404, 429 | Client parameters |
| `PUT` | `/api/v1/parameters` | `update_parameters` | ✅ required | 30/min | 200, 401, 422, 429 | Update parameters |
| `GET` | `/api/v1/indicators/defaults` | `get_default_indicators` | ✅ required | 60/min | 200, 401, 404, 429 | Default indicators |
| `GET` | `/api/v1/indicators` | `get_indicators` | ✅ required | 60/min | 200, 401, 404, 429 | Client indicators |
| `PUT` | `/api/v1/indicators` | `update_indicators` | ✅ required | 30/min | 200, 401, 422, 429 | Update indicators |

### 1.3 Infrastructure Routes

| Method | Path | Handler | Auth | Rate Limit | Status Codes | Description |
|---|---|---|---|---|---|---|
| `GET` | `/api/v1/health` | `health` | ❌ none | 200/min (global) | 200 | Service health check |
| `POST` | `/api/v1/ws/ticket` | `issue_ws_ticket` | ✅ required | 30/min | 200, 401, 429 | Issue single-use WS ticket |
| `WS` | `/api/v1/ws/{client_id}` | `websocket_endpoint` | ✅ ticket/token | — | 1000, 1001, 1008, 1011 | Real-time event stream |

---

## 2. HTTP Method Review

### 2.1 Assessment

| Endpoint | Method | Verdict | Notes |
|---|---|---|---|
| `GET /clients/{id}/bots` | GET | ✅ Correct | Read-only, no side effects |
| `POST /clients/{id}/bots` | POST | ✅ Correct | Creates a new resource, non-idempotent |
| `POST /clients/{id}/bots/{botid}/run` | POST | ⚠️ Acceptable | Action sub-resource; `PATCH /bots/{id}` with `{"status":"running"}` is more RESTful but POST on a verb sub-resource is a widely accepted pattern |
| `POST /clients/{id}/bots/{botid}/stop` | POST | ⚠️ Acceptable | Same as above — `{"status":"paused"}` via PATCH would be more idiomatic |
| `DELETE /clients/{id}/bots/{botid}` | DELETE | ✅ Correct | Removes the resource |
| `GET /clients/{id}/bots/{botid}/orders` | GET | ✅ Correct | Read-only history |
| `GET /clients/{id}/bots/{botid}/trades` | GET | ✅ Correct | Read-only history |
| `GET /clients/{id}/parameters` | GET | ✅ Correct | Read-only |
| `PUT /clients/{id}/parameters` | PUT | ✅ Correct | Full replacement of config resource, idempotent |
| `PUT /clients/{id}/indicators` | PUT | ✅ Correct | Full replacement, idempotent |
| `POST /ws/ticket` | POST | ✅ Correct | Creates a new ticket resource |
| `GET /health` | GET | ✅ Correct | Read-only, no side effects |

**No state-mutating GETs found.** All GET endpoints are strictly read-only. PUT is used correctly for full config replacement (not partial update — no PATCH needed given the config objects are small and always fully replaced).

### 2.2 The run/stop POST pattern

`POST /bots/{botid}/run` and `POST /bots/{botid}/stop` follow the "action sub-resource" pattern, which is pragmatic and widely used. The alternative — `PATCH /bots/{botid}` with a `status` field — would require a `BotStatusRequest` body and a status state machine on the API side. The current approach is simpler and unambiguous. No change is required, but the docstring on `stop_bot` in `clients.py:82` correctly notes it "pauses" rather than fully stops, which is a semantic mismatch with the endpoint name (see Concerns §7.3).

---

## 3. URI Path Design

### 3.1 Path Structure Assessment

```
/api/v1/                                    ← versioned prefix ✅
  health                                    ← singleton resource ✅
  clients/{client_id}/                      ← tenant scope in path ✅
    bots                                    ← collection ✅
    bots/{botid}                            ← item ✅
    bots/{botid}/run                        ← action sub-resource ⚠️ (verb)
    bots/{botid}/stop                       ← action sub-resource ⚠️ (verb)
    bots/{botid}/orders                     ← sub-collection ✅
    bots/{botid}/trades                     ← sub-collection ✅
    parameters                              ← singleton config resource ✅
    indicators                              ← singleton config resource ✅
  ws/ticket                                 ← action resource ✅
  ws/{client_id}                            ← WebSocket ✅
```

### 3.2 Naming Consistency

| Check | Result |
|---|---|
| Collections use plural nouns (`bots`, `orders`, `trades`) | ✅ |
| Singleton resources use singular (`parameters`, `indicators`) | ✅ |
| All paths lowercase, hyphen-free | ✅ |
| API prefix `/api/v1` applied consistently via `settings.api_prefix` | ✅ |
| Path parameters use `{client_id}` and `{botid}` consistently | ✅ |
| `botid` is not `bot_id` — minor inconsistency with Python snake_case convention | ⚠️ Low |

### 3.3 Path vs Query Parameter Usage

| Parameter | Location | Verdict |
|---|---|---|
| `client_id` (canonical routes) | Path segment | ✅ Correct — identifies the tenant resource |
| `client_id` (legacy routes) | Query string | ⚠️ Deprecated — query params for resource identity are non-RESTful |
| `botid` | Path segment | ✅ Correct |
| `limit`, `offset` | Query string | ✅ Correct — pagination is a query concern |
| `ticket` (WebSocket) | Query string | ✅ Correct — auth token in WS URL is the standard pattern |

### 3.4 Path Validation

Both `client_id` and `botid` are validated by regex `^[a-zA-Z0-9_-]{1,64}$` at the path level (`clients.py:32-33`). This prevents path traversal and injection before the request reaches the service layer. The same regex is independently applied in `config_service.py:20` (`_SAFE_CLIENT_ID`) — consistent but duplicated (see Concerns §7.5).

---

## 4. Request & Response Contracts

### 4.1 Request Bodies

| Endpoint | Body Schema | Validation |
|---|---|---|
| `POST /clients/{id}/bots` | None (no body) | — |
| `POST /clients/{id}/bots/{botid}/run` | None | — |
| `POST /clients/{id}/bots/{botid}/stop` | None | — |
| `DELETE /clients/{id}/bots/{botid}` | None | — |
| `PUT /clients/{id}/parameters` | `ParametersConfig` | ✅ Pydantic v2 + key regex |
| `PUT /clients/{id}/indicators` | `IndicatorsConfig` | ✅ Pydantic v2 + key regex |
| `POST /ws/ticket` | None | — |

`ParametersConfig` and `IndicatorsConfig` (`schemas.py:62–100`) use `@field_validator` to enforce a key allowlist regex `^[\w\s/(). %,:-]{1,128}$` on all dict keys, blocking path traversal and injection attempts before data reaches the filesystem.

### 4.2 Response Schemas

| Endpoint | Success Schema | Example |
|---|---|---|
| `GET /clients/{id}/bots` | `BotListResponse` | `{"botids": ["abc-123"]}` |
| `POST /clients/{id}/bots` | `BotCreateResponse` | `{"botid": "abc-123"}` |
| `POST .../run`, `.../stop` | `MessageResponse` | `{"message": "Bot abc-123 started."}` |
| `DELETE .../bots/{botid}` | `MessageResponse` | `{"message": "Bot abc-123 removed."}` |
| `GET .../orders` | `list[TradeRecord]` | Array of 20-field trade objects |
| `GET .../trades` | `list[TradeRecord]` | Array of 20-field trade objects |
| `GET .../parameters` | `ParametersConfig` | `{"exchanges": {...}, "symbols": {...}, "strategy": "arbitrage"}` |
| `PUT .../parameters` | `MessageResponse` | `{"message": "Parameters for dev_user updated."}` |
| `GET .../indicators` | `IndicatorsConfig` | `{"periods": {...}, "oscillators": {...}, "movingaverages": {...}}` |
| `PUT .../indicators` | `MessageResponse` | `{"message": "Indicators for dev_user updated."}` |
| `GET /health` | `HealthResponse` | `{"status": "ok", "version": "1.0.0"}` |
| `POST /ws/ticket` | `TicketResponse` | `{"ticket": "<opaque>", "ttl_seconds": 30}` |

### 4.3 Error Response Format

All error responses use FastAPI's default `{"detail": "..."}` envelope:

```json
{ "detail": "Bot not found: abc-123" }          // 404
{ "detail": "Bot limit reached: 5" }             // 429
{ "detail": "Internal server error" }            // 500
{ "detail": [{"loc": [...], "msg": "..."}] }     // 422 (Pydantic validation)
```

There is no standardised error envelope with a machine-readable `code` field. The 422 response from Pydantic uses a different structure than the 404/429/500 responses (see Concerns §7.1).

### 4.4 TradeRecord Schema

`TradeRecord` (`schemas.py:30–52`) maps directly to the dict written by `SonarftHelpers.save_order_history` (`sonarft_helpers.py:155–178`). It uses `ConfigDict(extra="ignore")` to silently drop fields present in the DB but not in the schema (e.g. `buy_order_id`, `sell_order_id`, `order_buy_success` from `save_trade_history`). This is intentional — the orders and trades endpoints return the same schema — but means some execution metadata is not surfaced via the API.

### 4.5 Optional / Nullable Fields

| Field | Schema | Nullable | Notes |
|---|---|---|---|
| `BotCreateResponse.botid` | `str` | ❌ | Always present |
| `WsBotCreatedEvent.botid` | `str \| None` | ✅ | Can be None if creation fails mid-flight |
| `WsBotRemovedEvent.botid` | `str \| None` | ✅ | Same |
| `ParametersConfig.strategy` | `Literal["arbitrage","market_making"]` | ❌ | Defaults to `"arbitrage"` |
| `TicketResponse.ttl_seconds` | `int` | ❌ | Always 30 |

`WsBotCreatedEvent.botid` being nullable (`schemas.py:103`) is a latent issue — if the frontend receives `{"type":"bot_created","botid":null}` it must handle null gracefully. The web client does handle this, but the schema should reflect the invariant that a successfully created bot always has a botid (see Concerns §7.4).

---

## 5. Status Code Usage

### 5.1 2xx Success

| Code | Used For | Verdict |
|---|---|---|
| `200 OK` | All GETs, run/stop/remove actions | ✅ Correct |
| `201 Created` | `POST /clients/{id}/bots` | ✅ Correct — new resource created |
| `204 No Content` | Not used | ⚠️ DELETE and action endpoints return `200 + MessageResponse` instead of `204`. Both are valid; `204` is more idiomatic for DELETE but `200 + body` is acceptable and more informative for clients. |

### 5.2 4xx Client Errors

| Code | Used For | Verdict |
|---|---|---|
| `400 Bad Request` | Invalid `client_id` in `ConfigService._validate_client_id` | ✅ Correct |
| `401 Unauthorized` | Missing/invalid token | ✅ Correct |
| `403 Forbidden` | Not used | ⚠️ No 403 — tenant isolation is enforced by returning 404 when a bot doesn't belong to the requesting client (`bot_service.py:35`). This is a deliberate security choice (avoids confirming resource existence) but is worth documenting. |
| `404 Not Found` | Bot not found, config file not found | ✅ Correct |
| `422 Unprocessable Entity` | Pydantic validation failure | ✅ Correct — FastAPI default |
| `429 Too Many Requests` | Rate limit exceeded, bot limit exceeded | ✅ Correct for rate limiting. ⚠️ Using 429 for bot limit (`BotLimitExceededError`) is debatable — `507 Insufficient Storage` or `403 Forbidden` could be argued, but 429 is widely understood and acceptable. |

### 5.3 5xx Server Errors

| Code | Used For | Verdict |
|---|---|---|
| `500 Internal Server Error` | Unhandled exceptions via `generic_error_handler` | ✅ Correct |
| `503 Service Unavailable` | Not used | ⚠️ When `app.state.bot_service is None` (failed lifespan init), the WebSocket endpoint closes with code 1011 (`main.py:196`), but HTTP endpoints will raise an unhandled `AttributeError` that falls through to the 500 handler. A 503 with `Retry-After` would be more informative. |

### 5.4 WebSocket Close Codes

| Code | Used For | Verdict |
|---|---|---|
| `1000` | Normal closure | ✅ |
| `1001` | Existing connection displaced by new connection | ✅ Correct |
| `1008` | Policy violation (invalid ticket/token) | ✅ Correct |
| `1011` | Internal server error (BotService unavailable) | ✅ Correct |

---

## 6. API Consistency

### 6.1 Naming Patterns

| Pattern | Canonical Routes | Legacy Routes | Verdict |
|---|---|---|---|
| Resource identity in path | ✅ `/clients/{client_id}/bots` | ❌ `/bots?client_id=` | Inconsistent — by design (migration) |
| Response envelope for mutations | `MessageResponse {"message": "..."}` | `MessageResponse {"message": "..."}` | ✅ Consistent |
| Response envelope for collections | `BotListResponse {"botids": [...]}` | `BotListResponse {"botids": [...]}` | ✅ Consistent |
| Error envelope | `{"detail": "..."}` | `{"detail": "..."}` | ✅ Consistent |
| Timestamp format in `TradeRecord` | ISO 8601 string (`"2025-07-01T12:00:00"`) | — | ✅ Consistent |
| Timestamp in WS events | Unix epoch integer (`ts: int`) | — | ⚠️ Mixed formats — REST uses ISO strings, WS uses epoch integers |

### 6.2 Documentation Consistency

All canonical endpoints have one-line docstrings used by FastAPI for OpenAPI descriptions. The legacy endpoints are marked `deprecated=True` at the router level (`bots.py:20`, `config.py:17`), which correctly renders them as deprecated in the Swagger UI.

The WebSocket endpoint (`main.py:185`) has a docstring but is **not visible in OpenAPI** because it is registered with `@app.websocket` rather than via an `APIRouter`. Developers must consult the README or source code to discover the WS contract.

### 6.3 Timestamp Format Inconsistency

REST history endpoints return `TradeRecord.timestamp` as an ISO 8601 string (e.g. `"2025-07-01T12:00:00"`) written by `sonarft_helpers.py:155`. WebSocket events use Unix epoch integers (`ts: int`) in all event models (`schemas.py:107–130`). This is a minor but real inconsistency that frontend consumers must handle with two different date parsing paths.

### 6.4 Auth Dependency Consistency

| Router | Auth dependency | `client_id` source |
|---|---|---|
| `clients.py` | `require_auth` (explicit `_: Auth`) | Path parameter |
| `bots.py` | `get_client_id` (implicit, derives identity) | JWT sub / query param |
| `config.py` | Mixed — `require_auth` on defaults, `get_client_id` on client routes | JWT sub / query param |
| `ws_ticket.py` | `get_client_id` | JWT sub / query param |

The canonical `clients.py` router uses `require_auth` + path `client_id`, while the legacy routers use `get_client_id` which both validates the token and derives the identity. This is architecturally correct but means the two router families have different dependency signatures, which can confuse contributors adding new endpoints.

In `config.py`, `get_default_parameters` and `get_default_indicators` use `require_auth` (no client identity needed), while the per-client endpoints use `get_client_id`. This is correct but the inconsistency within the same file is worth noting.

---

## 7. Pagination, Filtering & Sorting

### 7.1 History Endpoints

`GET /clients/{id}/bots/{botid}/orders` and `GET /clients/{id}/bots/{botid}/trades` both support `limit`/`offset` pagination:

```
GET /api/v1/clients/{id}/bots/{botid}/orders?limit=100&offset=0
```

| Parameter | Type | Default | Constraints | Location |
|---|---|---|---|---|
| `limit` | `int` | `100` | `ge=1, le=1000` | `clients.py:107`, `bots.py:87` |
| `offset` | `int` | `0` | `ge=0` | `clients.py:108`, `bots.py:88` |

The constraints are validated by FastAPI/Pydantic at the query-parameter level. The underlying `SonarftHelpers._db_query` passes `LIMIT ? OFFSET ?` directly to SQLite (`sonarft_helpers.py:113`), so the database never returns unbounded result sets.

### 7.2 Missing Pagination on Bot List

`GET /clients/{id}/bots` returns `BotListResponse {"botids": [...]}` with no pagination. This is acceptable given the hard cap of `MAX_BOTS_PER_CLIENT` (default 5), which bounds the list size. No change needed.

### 7.3 Filtering & Sorting

No filtering or sorting parameters exist on any endpoint. For the history endpoints this is a gap — clients cannot filter by date range, position type, or exchange without fetching all records and filtering client-side. Given the `keep_last=10_000` retention policy in `SonarftHelpers.purge_history`, this could return up to 1,000 records per request (the `limit` cap), which is manageable but not ideal for long-running bots.

**Missing:** `from_ts`, `to_ts` date range filters and `sort` direction on history endpoints.

---

## 8. Rate Limiting & Throttling

### 8.1 Implementation

Rate limiting is implemented via `slowapi` (`core/limiter.py`) with `get_remote_address` as the key function (IP-based). The `SlowAPIMiddleware` is registered in `create_app()` (`main.py:163`).

### 8.2 Per-Endpoint Limits

| Tier | Limit | Endpoints |
|---|---|---|
| Global default | 200/min | All endpoints not explicitly decorated |
| Read-heavy | 60/min | `list_bots`, `get_orders`, `get_trades`, `get_parameters`, `get_indicators`, `get_default_*` |
| Write/action | 20–30/min | `run_bot`, `stop_bot`, `remove_bot`, `update_parameters`, `update_indicators` |
| Create | 10/min | `create_bot` |
| Ticket | 30/min | `issue_ws_ticket` |

The tiered approach is well-designed — the most dangerous endpoint (`create_bot`) has the tightest limit.

### 8.3 Rate Limit Headers

`slowapi` automatically adds `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers to responses when a limit is applied. When the limit is exceeded, `_rate_limit_exceeded_handler` returns HTTP 429 with `{"error": "Rate limit exceeded: ..."}` — note this uses `"error"` not `"detail"`, which is inconsistent with the rest of the API's error format (see Concerns §7.2).

### 8.4 Limitations

- **IP-based only** — in a reverse-proxy deployment (nginx, Traefik), all requests may appear to come from the proxy IP unless `X-Forwarded-For` is trusted. `slowapi` uses `get_remote_address` which reads `request.client.host`, not the forwarded header. This could allow a single user behind a proxy to consume the entire rate limit budget.
- **No per-user limits** — limits are per-IP, not per `client_id`. A single IP running multiple clients is not throttled per client.
- **In-memory store** — `slowapi`'s default backend is in-memory. In a multi-worker deployment, each worker has its own counter, effectively multiplying the limit by the number of workers.

---

## 9. API Versioning

### 9.1 Current Strategy

The API uses URL path versioning (`/api/v1/`) configured via `settings.api_prefix` (`core/config.py:8`). The prefix is applied uniformly to all routers in `create_app()` (`main.py:175–180`).

### 9.2 Backward Compatibility

The dual-route strategy (canonical + legacy) is the current backward-compatibility mechanism. Legacy routes are marked `deprecated=True` at the router level, which:
- Renders them with a strikethrough in Swagger UI
- Sets `"deprecated": true` in the OpenAPI schema
- Does **not** enforce any sunset date or return `Deprecation` / `Sunset` headers

There is no programmatic enforcement of the deprecation timeline. Clients using legacy routes receive no runtime warning.

### 9.3 Version Upgrade Path

No `/api/v2/` routes exist. When a v2 is needed, the `api_prefix` setting and router registration pattern in `create_app()` make it straightforward to add a parallel router set without breaking v1 consumers.

### 9.4 OpenAPI Metadata

```python
# main.py:152–159
app = FastAPI(
    title=settings.api_title,          # "SonarFT API"
    version=settings.api_version,      # "1.0.0"
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json",
)
```

Interactive docs are available at `/api/v1/docs` (Swagger UI) and `/api/v1/redoc`. The OpenAPI schema is at `/api/v1/openapi.json`.

---

## 10. Documentation Assessment

### 10.1 OpenAPI Coverage

| Endpoint group | Docstring | Tags | Deprecated flag | Response model | Notes |
|---|---|---|---|---|---|
| Canonical (`clients.py`) | ✅ All | `Clients` | N/A | ✅ All | Well documented |
| Legacy bots (`bots.py`) | ✅ All | `Bots (Legacy...)` | ✅ Router-level | ✅ All | Tag name is verbose but clear |
| Legacy config (`config.py`) | ✅ All | `Configuration (Legacy...)` | ✅ Router-level | ✅ All | Good |
| Health (`health.py`) | ✅ | `Health` | N/A | ✅ | Minimal but sufficient |
| WS ticket (`ws_ticket.py`) | ✅ | `WebSocket` | N/A | ✅ | Includes usage instructions in docstring |
| WebSocket endpoint | ✅ Docstring in source | ❌ Not in OpenAPI | N/A | ❌ Not in OpenAPI | Invisible to Swagger UI |

### 10.2 WebSocket Documentation Gap

The WebSocket endpoint at `/api/v1/ws/{client_id}` is the primary real-time interface but is completely absent from the generated OpenAPI schema. Developers must read `main.py:185–215` and the README to understand:
- Authentication (ticket vs token)
- Supported commands (`create`, `run`, `remove`, `stop`, `set_simulation`)
- Event types (`connected`, `log`, `bot_created`, `bot_removed`, `order_success`, `trade_success`, `error`, `ping`)

The `shared/types/api.ts` file documents the WS contract for the frontend, but there is no equivalent machine-readable spec for backend consumers.

### 10.3 Missing Response Examples

No `openapi_extra` or `responses` parameter examples are provided on any endpoint. FastAPI generates schema shapes from Pydantic models but does not auto-generate example values. Adding `model_config = ConfigDict(json_schema_extra={"example": {...}})` to key schemas would improve the Swagger UI experience.

### 10.4 Bot Lifecycle Call Flow (for documentation)

The full call chain for `POST /clients/{id}/bots/{botid}/run`:

```
clients.py:run_bot()
  → BotService.run_bot(botid, client_id)          [bot_service.py:44]
    → BotService._bot_owned_by(botid, client_id)  [bot_service.py:33]
    → BotManager.run_bot(botid)                   [sonarft_manager.py:118]
      → BotManager.get_bot_instance(botid)        [sonarft_manager.py:57]
      → SonarftBot.run_bot()                      [sonarft_bot.py:84]
        → SonarftSearch.search_trades(botid)      [sonarft_search.py — loop]
```

The full call chain for `POST /clients/{id}/bots/{botid}/stop`:

```
clients.py:stop_bot()
  → BotService.stop_bot(botid, client_id)         [bot_service.py:49]
    → BotManager.pause_bot(botid)                 [sonarft_manager.py:133]
      → SonarftBot.pause_bot()                    [sonarft_bot.py:290]
        → _stop_event.set()                       [stops run loop]
        → executor.monitor_task.cancel()          [cancels trade monitor]
```

---

## 11. Concerns & Recommendations

### 11.1 Concerns

| # | Concern | Severity | Location |
|---|---|---|---|
| 7.1 | **No standardised error envelope** — 404/429/500 use `{"detail": "..."}` but 422 (Pydantic) uses `{"detail": [{"loc":...,"msg":...}]}` and 429 from slowapi uses `{"error": "..."}`. Three different error shapes for clients to handle. | Medium | `errors.py`, `slowapi` default handler |
| 7.2 | **slowapi 429 uses `"error"` key, not `"detail"`** — inconsistent with all other error responses. The `_rate_limit_exceeded_handler` from slowapi is registered directly without a custom wrapper. | Medium | `main.py:161` |
| 7.3 | **`stop` semantics mismatch** — `POST /bots/{botid}/stop` pauses the bot (keeps it registered, resumable via `run`), but the endpoint name implies full termination. The docstring in `clients.py:82` says "Pause a running bot" but `bots.py:57` says "Stop a running bot". | Medium | `clients.py:82`, `bots.py:57` |
| 7.4 | **`WsBotCreatedEvent.botid` is nullable** — `schemas.py:103` declares `botid: str \| None`. A successfully created bot always has a botid; the nullable type is a defensive artefact that weakens the contract. | Low | `schemas.py:103` |
| 7.5 | **`client_id` regex duplicated** — the pattern `^[a-zA-Z0-9_-]{1,64}$` is defined in three places: `clients.py:32`, `bots.py:22`, and `config_service.py:20`. A single constant in `core/config.py` or `models/schemas.py` would be the single source of truth. | Low | `clients.py:32`, `bots.py:22`, `config_service.py:20` |
| 7.6 | **No `Deprecation` / `Sunset` headers on legacy routes** — clients using deprecated routes receive no runtime signal that the routes will be removed. RFC 8594 defines `Sunset` header for this purpose. | Low | `bots.py`, `config.py` |
| 7.7 | **History endpoints have no date-range filtering** — `GET .../orders` and `GET .../trades` only support `limit`/`offset`. Long-running bots accumulate up to 10,000 records; clients cannot efficiently query "trades from the last 24 hours". | Low | `clients.py:107–120`, `bots.py:87–100` |
| 7.8 | **`BotService` raises `HTTPException` directly** — `bot_service.py:40` raises `HTTPException(status_code=500)` inside the service layer. Services should raise domain exceptions; HTTP translation belongs in the endpoint layer. | Low | `bot_service.py:40` |
| 7.9 | **`HealthResponse.version` hardcoded** — `schemas.py:130` hardcodes `version: str = "1.0.0"` instead of reading from `Settings.api_version`. After a version bump the health endpoint reports a stale version. | Low | `schemas.py:130` |

---

### 11.2 Recommendations (Prioritised)

#### P1 — Quick wins

**R1: Wrap the slowapi 429 handler to use `{"detail": "..."}` consistently**

```python
# main.py — replace the default handler registration
from starlette.requests import Request
from starlette.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": str(exc)})

app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
```

**R2: Fix `HealthResponse.version` to read from settings**

```python
# schemas.py
from .core.config import get_settings  # or pass via Field default_factory

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = Field(default_factory=lambda: get_settings().api_version)
```

**R3: Extract the `client_id` regex to a single constant**

```python
# core/config.py or models/schemas.py
CLIENT_ID_PATTERN = r"^[a-zA-Z0-9_-]{1,64}$"

# clients.py
ClientId = Annotated[str, Path(pattern=CLIENT_ID_PATTERN)]

# config_service.py
_SAFE_CLIENT_ID = re.compile(CLIENT_ID_PATTERN)
```

**R4: Make `WsBotCreatedEvent.botid` non-nullable**

```python
# schemas.py
class WsBotCreatedEvent(BaseModel):
    type: Literal["bot_created"] = "bot_created"
    botid: str          # always present on success
    ts: int
```

Handle the error case by emitting `WsErrorEvent` instead of `WsBotCreatedEvent` with a null botid.

---

#### P2 — Medium effort

**R5: Standardise the error envelope with a machine-readable `code` field**

```python
# core/errors.py
class ErrorResponse(BaseModel):
    code: str       # e.g. "BOT_NOT_FOUND", "RATE_LIMIT_EXCEEDED"
    detail: str     # human-readable message

# All exception handlers return ErrorResponse
async def bot_not_found_handler(...) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(code="BOT_NOT_FOUND", detail=str(exc)).model_dump()
    )
```

**R6: Rename `stop` to `pause` in the canonical router, or align docstrings**

Option A — rename the endpoint path (breaking change, requires v2):
```
POST /api/v1/clients/{id}/bots/{botid}/pause
```

Option B — align docstrings immediately (non-breaking):
```python
# bots.py:57 — change "Stop a running bot." to "Pause a running bot."
```

Option B is the immediate fix; Option A is the correct long-term solution.

**R7: Add `Sunset` header to legacy route responses**

```python
# bots.py and config.py — add middleware or response header
response.headers["Sunset"] = "Sat, 01 Jan 2026 00:00:00 GMT"
response.headers["Deprecation"] = "true"
```

**R8: Add date-range filtering to history endpoints**

```python
@router.get("/{client_id}/bots/{botid}/orders")
async def get_orders(
    ...
    from_ts: str | None = Query(default=None, description="ISO 8601 start timestamp"),
    to_ts: str | None = Query(default=None, description="ISO 8601 end timestamp"),
) -> list[TradeRecord]:
```

Requires a corresponding `_db_query_range` method in `SonarftHelpers` using `WHERE timestamp BETWEEN ? AND ?`.

---

#### P3 — Longer term

**R9: Move the WebSocket endpoint into an `APIRouter` with AsyncAPI documentation**

Register the WS endpoint via a dedicated router so it appears in OpenAPI. Supplement with an AsyncAPI 2.x spec (`asyncapi.yaml`) documenting the full message schema — this is the WebSocket equivalent of OpenAPI.

**R10: Add per-user rate limiting alongside IP-based limiting**

```python
# core/limiter.py
from slowapi.util import get_remote_address

def get_rate_limit_key(request: Request) -> str:
    # Use client_id from path if available, fall back to IP
    client_id = request.path_params.get("client_id")
    return client_id or get_remote_address(request)

limiter = Limiter(key_func=get_rate_limit_key)
```

**R11: Move `HTTPException` out of `BotService`**

```python
# bot_service.py:40 — replace
raise HTTPException(status_code=500, detail="Bot creation failed")
# with a domain exception
raise BotCreationFailedError("BotManager.create_bot returned None")

# Then handle in the endpoint layer
except BotCreationFailedError as exc:
    raise HTTPException(status_code=500, detail=str(exc)) from exc
```

---

## Related Prompts

- [Prompt 01: Architecture Structure](../architecture/01-api-architecture.md) — Module organisation
- [Prompt 03: Data Models & Validation](../models/03-data-models-validation.md) — Schema deep-dive
- [Prompt 04: Authentication & Security](../security/04-authentication-security.md) — Auth patterns
- [Prompt 05: WebSocket & Real-time](../websocket/05-websocket-realtime.md) — WS lifecycle

---

_Part of the SonarFT API Code Review Prompt Suite — Prompt 02_
