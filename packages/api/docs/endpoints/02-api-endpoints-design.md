# API Endpoints Design & REST Contract Review

**Prompt ID:** 02-API-ENDPOINTS  
**Package:** `packages/api`  
**Output:** `docs/endpoints/02-api-endpoints-design.md`  
**Reviewed:** July 2025  
**Status:** Complete

---

## Executive Summary

The SonarFT API exposes 22 endpoints across six routers. The canonical `/clients/{client_id}/...` routes are well-designed REST resources with correct HTTP methods, path-segment identity, and consistent response schemas. The legacy `/bots` and `/parameters` routes duplicate this surface area entirely and are correctly marked deprecated with `Deprecation` and `Sunset` headers. Pagination on history endpoints is solid (limit/offset with validated bounds and ISO 8601 date-range filtering) but lacks total-count metadata, making cursor-based navigation impossible for clients. The most significant design gap is the absence of a `PATCH /bots/{botid}/run` or equivalent state-transition endpoint — bot lifecycle actions (`run`, `stop`) are modelled as sub-resource `POST` actions, which is acceptable but inconsistent with the `DELETE` used for removal. Rate-limit headers are not returned to clients, making it impossible for callers to implement proactive backoff.

---

## Complete Endpoint Reference

### Canonical Routes — `/api/v1/clients/` (`clients.py`)

| Method | Path | Handler | Auth | Rate Limit | Status Code(s) |
|---|---|---|---|---|---|
| GET | `/api/v1/clients/{client_id}/bots` | `list_bots` | ✅ Required | 60/min | 200, 401, 422 |
| POST | `/api/v1/clients/{client_id}/bots` | `create_bot` | ✅ Required | 10/min | 201, 401, 422, 429 |
| POST | `/api/v1/clients/{client_id}/bots/{botid}/run` | `run_bot` | ✅ Required | 20/min | 200, 401, 404, 422 |
| POST | `/api/v1/clients/{client_id}/bots/{botid}/stop` | `stop_bot` | ✅ Required | 20/min | 200, 401, 404, 422 |
| DELETE | `/api/v1/clients/{client_id}/bots/{botid}` | `remove_bot` | ✅ Required | 20/min | 200, 401, 404, 422 |
| GET | `/api/v1/clients/{client_id}/bots/{botid}/orders` | `get_orders` | ✅ Required | 60/min | 200, 401, 404, 422 |
| GET | `/api/v1/clients/{client_id}/bots/{botid}/trades` | `get_trades` | ✅ Required | 60/min | 200, 401, 404, 422 |
| GET | `/api/v1/clients/{client_id}/parameters` | `get_parameters` | ✅ Required | 60/min | 200, 401, 404, 422 |
| PUT | `/api/v1/clients/{client_id}/parameters` | `update_parameters` | ✅ Required | 30/min | 200, 401, 422 |
| GET | `/api/v1/clients/{client_id}/indicators` | `get_indicators` | ✅ Required | 60/min | 200, 401, 404, 422 |
| PUT | `/api/v1/clients/{client_id}/indicators` | `update_indicators` | ✅ Required | 30/min | 200, 401, 422 |

### Legacy Routes — `/api/v1/bots/` (`bots.py`) ⚠️ Deprecated

| Method | Path | Handler | Auth | Rate Limit | Status Code(s) |
|---|---|---|---|---|---|
| GET | `/api/v1/bots` | `list_bots` | ✅ Required | 60/min | 200, 400, 401, 422 |
| POST | `/api/v1/bots` | `create_bot` | ✅ Required | 10/min | 201, 400, 401, 429 |
| POST | `/api/v1/bots/{botid}/run` | `run_bot` | ✅ Required | 20/min | 200, 400, 401, 404 |
| POST | `/api/v1/bots/{botid}/stop` | `stop_bot` | ✅ Required | 20/min | 200, 400, 401, 404 |
| DELETE | `/api/v1/bots/{botid}` | `remove_bot` | ✅ Required | 20/min | 200, 400, 401, 404 |
| GET | `/api/v1/bots/{botid}/orders` | `get_orders` | ✅ Required | 60/min | 200, 400, 401, 404 |
| GET | `/api/v1/bots/{botid}/trades` | `get_trades` | ✅ Required | 60/min | 200, 400, 401, 404 |

### Legacy Routes — `/api/v1/` (`config.py`) ⚠️ Deprecated

| Method | Path | Handler | Auth | Rate Limit | Status Code(s) |
|---|---|---|---|---|---|
| GET | `/api/v1/parameters/defaults` | `get_default_parameters` | ✅ Required | 60/min | 200, 401, 404 |
| GET | `/api/v1/parameters` | `get_parameters` | ✅ Required | 60/min | 200, 400, 401, 404 |
| PUT | `/api/v1/parameters` | `update_parameters` | ✅ Required | 30/min | 200, 400, 401, 422 |
| GET | `/api/v1/indicators/defaults` | `get_default_indicators` | ✅ Required | 60/min | 200, 401, 404 |
| GET | `/api/v1/indicators` | `get_indicators` | ✅ Required | 60/min | 200, 400, 401, 404 |
| PUT | `/api/v1/indicators` | `update_indicators` | ✅ Required | 30/min | 200, 400, 401, 422 |

### Infrastructure Routes

| Method | Path | Handler | Auth | Rate Limit | Status Code(s) |
|---|---|---|---|---|---|
| GET | `/api/v1/health` | `health` | ❌ None | Global 200/min | 200 |
| POST | `/api/v1/ws/ticket` | `issue_ws_ticket` | ✅ Required | 30/min | 200, 401 |
| WS | `/api/v1/ws/{client_id}` | `websocket_endpoint` | Ticket or token | — | 1000, 1008, 1011 |

---

## Endpoint Hierarchy

```
/api/v1/
├── health                                    GET
├── ws/
│   ├── ticket                                POST
│   └── {client_id}                           WS
├── clients/
│   └── {client_id}/
│       ├── bots                              GET, POST
│       ├── bots/{botid}/
│       │   ├── run                           POST
│       │   ├── stop                          POST
│       │   ├── orders                        GET
│       │   └── trades                        GET
│       ├── parameters                        GET, PUT
│       └── indicators                        GET, PUT
├── bots/                                     [DEPRECATED]
│   ├──                                       GET, POST
│   └── {botid}/
│       ├── run                               POST
│       ├── stop                              POST
│       ├── orders                            GET
│       └── trades                            GET
├── parameters/                               [DEPRECATED]
│   ├── defaults                              GET
│   └──                                       GET, PUT
└── indicators/                               [DEPRECATED]
    ├── defaults                              GET
    └──                                       GET, PUT
```

---

## 1. HTTP Method Review

| Endpoint | Method | Assessment |
|---|---|---|
| List bots | GET | ✅ Correct — read-only, safe, idempotent |
| Create bot | POST | ✅ Correct — non-idempotent resource creation |
| Run bot | POST | ⚠️ Acceptable but debatable — state transition; `PATCH` with `{"status": "running"}` would be more RESTful |
| Stop bot | POST | ⚠️ Same as above — `PATCH` with `{"status": "stopped"}` would be more RESTful |
| Remove bot | DELETE | ✅ Correct — idempotent resource deletion |
| Get orders/trades | GET | ✅ Correct — read-only, safe |
| Get parameters | GET | ✅ Correct |
| Update parameters | PUT | ✅ Correct for full replacement; `PATCH` would be more appropriate if partial updates are ever needed |
| Update indicators | PUT | ✅ Same as above |
| Issue WS ticket | POST | ✅ Correct — creates a new resource (ticket) |
| Health check | GET | ✅ Correct |

The `run` and `stop` sub-resource `POST` pattern is a common and pragmatic REST convention for state transitions (used by GitHub, Stripe, AWS). It is not incorrect, but it is inconsistent with the `DELETE` used for removal — which is a true REST verb — and means the bot lifecycle cannot be managed with a single `PATCH /bots/{botid}` call.

---

## 2. URI Path Design

### Canonical routes (`clients.py`)

Path design is clean and consistent:

- Collections use plural nouns: `/bots`, `/orders`, `/trades`
- Items use path segments: `/bots/{botid}`
- Sub-resources are nested one level: `/bots/{botid}/orders`
- Config resources are flat under the client: `/parameters`, `/indicators`
- All IDs are validated by `ID_PATTERN` (`^[a-zA-Z0-9_-]{1,64}$`) at the path level

One structural question: `parameters` and `indicators` are config resources for the client, not sub-resources of a bot. Their placement at `/clients/{client_id}/parameters` is correct. However, there is no `/clients/{client_id}/bots/{botid}/parameters` path — bot-level config is not exposed via REST (only via WebSocket `set_simulation` command and hot-reload). This is a deliberate design choice but worth documenting.

### Legacy routes (`bots.py`, `config.py`)

The legacy routes use `client_id` as a query parameter (`?client_id=`). This is the primary reason they are deprecated — query parameters are not appropriate for identity/ownership scoping of resources. The canonical path-segment form is correct.

The legacy `config.py` router has no prefix, so `/parameters` and `/indicators` sit at the top level of `/api/v1/`. This creates a flat namespace that would conflict with any future top-level resource named `parameters`.

### Versioning

All routes are correctly prefixed with `/api/v1` via `settings.api_prefix`. The prefix is applied in `create_app()` (`main.py:261`) and is not hardcoded in any router file.

---

## 3. Request & Response Contracts

### Bot endpoints

| Endpoint | Request Body | Response Schema | Notes |
|---|---|---|---|
| GET `.../bots` | None | `BotListResponse` `{botids: list[str]}` | |
| POST `.../bots` | None | `BotCreateResponse` `{botid: str}` | 201 on success |
| POST `.../bots/{botid}/run` | None | `MessageResponse` `{message: str}` | |
| POST `.../bots/{botid}/stop` | None | `MessageResponse` `{message: str}` | |
| DELETE `.../bots/{botid}` | None | `MessageResponse` `{message: str}` | Returns 200, not 204 |
| GET `.../orders` | Query params | `list[TradeRecord]` | Paginated |
| GET `.../trades` | Query params | `list[TradeRecord]` | Paginated |

### Config endpoints

| Endpoint | Request Body | Response Schema | Notes |
|---|---|---|---|
| GET `.../parameters` | None | `ClientParametersConfig` | |
| PUT `.../parameters` | `ClientParametersConfig` | `MessageResponse` | Full replacement |
| GET `.../indicators` | None | `IndicatorsConfig` | |
| PUT `.../indicators` | `IndicatorsConfig` | `MessageResponse` | Full replacement |
| GET `.../parameters/defaults` | None | `ClientParametersConfig` | Legacy only |
| GET `.../indicators/defaults` | None | `IndicatorsConfig` | Legacy only |

### Pagination parameters (orders/trades)

| Parameter | Type | Default | Constraints | Validated |
|---|---|---|---|---|
| `limit` | int | 100 | ge=1, le=1000 | ✅ FastAPI/Pydantic |
| `offset` | int | 0 | ge=0 | ✅ FastAPI/Pydantic |
| `from_ts` | str \| None | None | ISO 8601 (not validated) | ⚠️ Passed through as-is |
| `to_ts` | str \| None | None | ISO 8601 (not validated) | ⚠️ Passed through as-is |

### Error response schema

All error responses include `request_id` for log correlation:

```json
{
  "detail": "Bot not found: bot-999",
  "request_id": "3f2a1b4c-..."
}
```

This is consistent across all registered exception handlers (`errors.py`) and the generic 500 handler.

---

## 4. Status Code Usage

| Code | Used For | Assessment |
|---|---|---|
| 200 | All successful GET, POST (run/stop), PUT, DELETE | ⚠️ DELETE returning 200 with body is acceptable but 204 (No Content) is more conventional |
| 201 | POST `.../bots` (create) | ✅ Correct |
| 400 | Missing `client_id` query param (legacy routes) | ✅ Correct |
| 401 | Missing or invalid auth token | ✅ Correct |
| 404 | Bot not found, config file not found | ✅ Correct |
| 422 | Pydantic validation failure (path params, body) | ✅ Correct — FastAPI default for validation errors |
| 429 | Bot limit exceeded, rate limit exceeded | ✅ Correct — used for both business-rule limits and rate limiting |
| 500 | Unhandled exceptions, bot creation failure, config write failure | ✅ Correct |
| 503 | BotService or ConfigService failed to initialise | ✅ Correct — includes `Retry-After: 30` header |

One inconsistency: `BotLimitExceededError` (a business rule — "you have too many bots") and `RateLimitExceeded` (a rate limiter — "you are sending too many requests") both return 429. These are semantically different: the former is a permanent condition until a bot is removed; the latter is transient. Using 429 for both is technically valid but makes it harder for clients to distinguish them without parsing the `detail` string.

---

## 5. API Consistency

### Naming conventions

| Aspect | Canonical routes | Legacy routes | Consistent? |
|---|---|---|---|
| Resource names | Plural nouns (`bots`, `orders`) | Plural nouns | ✅ |
| Action sub-resources | Verb (`/run`, `/stop`) | Verb | ✅ |
| Response field names | `snake_case` | `snake_case` | ✅ |
| Error field names | `detail`, `request_id` | `detail`, `request_id` | ✅ |
| Message responses | `{"message": "Bot X started."}` | `{"message": "Bot X started."}` | ✅ |

### Timestamp format inconsistency

The `TradeRecord.timestamp` field is a plain `str` with no format enforcement. The test fixtures use two different formats:

- `test_endpoints.py`: `"07-20-2025 12:00:00"` (MM-DD-YYYY HH:MM:SS)
- `test_clients.py`: `"2025-07-01T12:00:00"` (ISO 8601)

The field accepts any string. Clients cannot rely on a consistent timestamp format when parsing history responses.

### `DELETE` returns 200 with body vs 204

`remove_bot` returns `200 MessageResponse` rather than `204 No Content`. This is internally consistent (all mutation endpoints return `MessageResponse`) but deviates from the REST convention where `DELETE` returns 204. The choice is defensible — the message body confirms which bot was removed — but should be documented.

### No `defaults` endpoint on canonical routes

The legacy `config.py` exposes `GET /parameters/defaults` and `GET /indicators/defaults`. The canonical `clients.py` does not expose equivalent endpoints. Clients migrating from legacy to canonical routes lose access to default config values.

---

## 6. Pagination, Filtering, Sorting

### Pagination

Both `/orders` and `/trades` endpoints use limit/offset pagination:

```
GET /api/v1/clients/{id}/bots/{botid}/orders?limit=100&offset=0
```

- `limit`: 1–1000, default 100 — validated by FastAPI
- `offset`: ≥0, default 0 — validated by FastAPI
- Parameters are forwarded directly to `SonarftHelpers._async_query()` in `packages/bot/sonarft_helpers.py`

**Missing:** No `total` count is returned in the response. The response is a bare `list[TradeRecord]` with no envelope. Clients cannot determine whether more pages exist without fetching the next page and checking if it is empty.

### Date-range filtering

```
GET .../orders?from_ts=2025-01-01T00:00:00&to_ts=2025-06-30T23:59:59
```

- Both parameters are optional `str | None`
- Forwarded as-is to `_async_query()` — no format validation at the API layer
- No enforcement that `from_ts < to_ts`

### Sorting

No sorting parameters exist on any list endpoint. Records are returned in the order provided by `SonarftHelpers._async_query()` (SQLite insertion order, descending by default based on the `LIMIT/OFFSET` query). Clients cannot request ascending order or sort by profit/timestamp.

---

## 7. Rate Limiting

Rate limits are applied per-IP via `slowapi` (`limiter.py`). Per-endpoint limits:

| Endpoint group | Limit |
|---|---|
| GET list/history | 60/min |
| POST create bot | 10/min |
| POST run/stop/remove | 20/min |
| PUT config update | 30/min |
| POST ws/ticket | 30/min |
| Global default | 200/min |

**Missing: Rate-limit response headers.** `slowapi` can emit `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers, but these are not configured. Clients receive a 429 with no indication of when they can retry (beyond the generic `Retry-After` header that `slowapi` adds on the 429 response itself).

**Missing: Per-client rate limiting.** Limits are enforced per source IP. In a multi-tenant deployment behind a reverse proxy, all clients share the same IP-based counter. A single high-frequency client can exhaust the limit for all clients on the same IP.

---

## 8. API Versioning

- All routes are prefixed with `/api/v1` via `settings.api_prefix` (configurable via `API_PREFIX` env var)
- The prefix is applied once in `create_app()` — no hardcoded `/api/v1` strings in router files
- Deprecated routes carry `Deprecation: true` and `Sunset: Sun, 01 Jan 2026 00:00:00 GMT` headers
- The `Sunset` date is hardcoded as a module-level constant (`_SUNSET_DATE`) in both `bots.py` and `config.py` — it is not driven by configuration

No `/api/v2` routes exist. The migration path from legacy to canonical is clear: replace query-param `client_id` with path-segment `client_id`.

---

## 9. OpenAPI Documentation

FastAPI auto-generates OpenAPI docs at `/api/v1/docs` (Swagger UI) and `/api/v1/redoc`.

**Present:**
- All endpoints appear in the schema with correct methods, paths, and response models
- Deprecated routers are tagged with `deprecated: true` in the OpenAPI spec
- Tags group endpoints logically: `Clients`, `Bots (Legacy)`, `Configuration (Legacy)`, `Health`, `WebSocket`
- Query parameter descriptions are present on pagination params (`"Max records to return"`, `"ISO 8601 start timestamp (inclusive)"`)

**Missing:**
- No `summary` or `description` on most endpoint functions beyond the one-line docstring
- No request body examples (`openapi_extra` or `Body(example=...)`)
- No response examples for `TradeRecord` — the schema is correct but no sample data is shown
- The WebSocket endpoint (`/ws/{client_id}`) has a detailed docstring listing all events and commands, but WebSocket endpoints are not rendered in Swagger UI — this documentation is invisible to API consumers browsing the docs

---

## Concerns & Recommendations

### High

| # | Concern | Location | Detail |
|---|---|---|---|
| H1 | **`from_ts`/`to_ts` are not validated at the API layer** | `clients.py:107,120`, `bots.py:75,100` | Both timestamp parameters are `str \| None` with no format check. An invalid value like `"yesterday"` or `"'; DROP TABLE orders;--"` is passed directly to `SonarftHelpers._async_query()`. If the helper passes these to a SQLite `WHERE timestamp >= ?` clause without parameterisation, this is a SQL injection vector. Requires inspection of `sonarft_helpers.py` to confirm parameterisation. |

### Medium

| # | Concern | Location | Detail |
|---|---|---|---|
| M1 | **No total count in paginated responses** | `clients.py`, `bots.py` | `list[TradeRecord]` is returned with no envelope. Clients cannot implement "load more" or page indicators without an extra request. |
| M2 | **No rate-limit headers returned to clients** | `core/limiter.py` | `slowapi` supports `X-RateLimit-*` headers but they are not enabled. Clients cannot implement proactive backoff. |
| M3 | **`DELETE /bots/{botid}` returns 200 with body** | `clients.py:97`, `bots.py:82` | Convention is 204 No Content. The current behaviour is internally consistent but deviates from REST norms and may surprise API consumers. |
| M4 | **No `/defaults` endpoints on canonical routes** | `clients.py` | `GET /clients/{id}/parameters/defaults` and `GET /clients/{id}/indicators/defaults` do not exist. Clients migrating from legacy routes lose access to default config. |
| M5 | **`BotLimitExceededError` and rate-limit 429 are indistinguishable by status code** | `errors.py`, `limiter.py` | Both return 429. Clients must parse `detail` to distinguish a permanent business-rule limit from a transient rate limit. Consider 409 Conflict for the business-rule case. |
| M6 | **`Sunset` date is hardcoded** | `bots.py:21`, `config.py:14` | `_SUNSET_DATE = "Sun, 01 Jan 2026 00:00:00 GMT"` is a string literal in two files. If the date changes, it must be updated in both places. |

### Low

| # | Concern | Location | Detail |
|---|---|---|---|
| L1 | **No sorting parameters on history endpoints** | `clients.py`, `bots.py` | Records are returned in SQLite insertion order. Clients cannot request ascending order or sort by profit. |
| L2 | **`TradeRecord.timestamp` has no format constraint** | `models/schemas.py:22` | The field is `str` with no regex or datetime validation. Test fixtures use two different formats. |
| L3 | **WebSocket command documentation is invisible in Swagger UI** | `websocket.py:30-55` | The detailed docstring listing all WS events and commands is not rendered by Swagger UI. Consider a separate `docs/websocket-protocol.md` or OpenAPI extension. |
| L4 | **`run` and `stop` use POST on sub-resources** | `clients.py:65,78` | Pragmatic but inconsistent with `DELETE` for removal. A `PATCH /bots/{botid}` with `{"status": "running"\|"stopped"\|"removed"}` would unify the lifecycle API. |
| L5 | **No `Content-Location` header on 201 responses** | `clients.py:52` | `POST /clients/{id}/bots` returns 201 with `{"botid": "..."}` but no `Location` or `Content-Location` header pointing to the created resource. REST convention is to include `Location: /api/v1/clients/{id}/bots/{botid}`. |

---

## Recommendations

### Priority 1

**R1 (H1): Validate `from_ts`/`to_ts` format at the API layer**

Add a regex or `datetime` parse check before forwarding to the service:

```python
from datetime import datetime

def _parse_ts(value: str | None, param_name: str) -> str | None:
    if value is None:
        return None
    try:
        datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid {param_name}: must be ISO 8601")
    return value
```

Apply in both `get_orders` and `get_trades` in `clients.py` and `bots.py`.

---

### Priority 2

**R2 (M1): Wrap paginated responses in an envelope with total count**

```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
```

This requires `SonarftHelpers._async_query()` to also return a count, or a separate `_async_count()` call.

**R3 (M2): Enable `slowapi` rate-limit headers**

```python
# core/limiter.py
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
    headers_enabled=True,  # emits X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
)
```

**R4 (M4): Add `/defaults` endpoints to canonical routes**

```python
@router.get("/{client_id}/parameters/defaults", response_model=ClientParametersConfig)
async def get_default_parameters(
    request: Request, client_id: ClientId, _: Auth, service: CfgSvc,
) -> ClientParametersConfig:
    return await service.get_default_parameters()
```

**R5 (L5): Add `Location` header on bot creation**

```python
@router.post("/{client_id}/bots", response_model=BotCreateResponse, status_code=201)
async def create_bot(..., response: Response) -> BotCreateResponse:
    botid = await service.create_bot(client_id)
    response.headers["Location"] = f"/api/v1/clients/{client_id}/bots/{botid}"
    return BotCreateResponse(botid=botid)
```

---

### Priority 3

**R6 (M3): Change `DELETE` to return 204**

```python
@router.delete("/{client_id}/bots/{botid}", status_code=204)
async def remove_bot(...) -> None:
    await service.remove_bot(botid, client_id)
```

**R7 (M6): Drive `Sunset` date from settings**

```python
# core/config.py
class Settings(BaseSettings):
    legacy_sunset_date: str = "Sun, 01 Jan 2026 00:00:00 GMT"
```

**R8 (L2): Add ISO 8601 format validation to `TradeRecord.timestamp`**

```python
from pydantic import field_validator

class TradeRecord(BaseModel):
    timestamp: str

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        from datetime import datetime
        try:
            datetime.fromisoformat(v)
        except ValueError:
            pass  # accept legacy formats gracefully
        return v
```

Or change the field type to `datetime` and let Pydantic handle parsing.

---

_Generated by Amazon Q Developer — SonarFT API Code Review Prompt Suite, Prompt 02_


---

## Post-Implementation Update (July 2025)

### Resolved findings

| ID | Finding | Resolution |
|---|---|---|
| H1 | `from_ts`/`to_ts` not validated at API layer | `_parse_ts()` helper added to `_bot_handlers.py` — raises 422 on non-ISO 8601 input |
| M1 | No total count in paginated responses | Deferred to Phase 4 backlog |
| M2 | No rate-limit headers | Deferred — `headers_enabled=True` in slowapi requires `response: Response` on all endpoints |
| M3 | `DELETE` returns 200 with body | `DELETE /clients/{id}/bots/{botid}` now returns **204 No Content** |
| M4 | No `/defaults` endpoints on canonical routes | `GET /clients/{id}/parameters/defaults` and `GET /clients/{id}/indicators/defaults` added |
| M5 | `BotLimitExceededError` and rate-limit 429 indistinguishable | All error responses now include a `code` field (`BOT_LIMIT_EXCEEDED`, `RATE_LIMITED`, etc.) |
| M6 | `Sunset` date hardcoded in two files | `_legacy.py` created — `LEGACY_SUNSET_DATE` is a single constant |
| L5 | No `Location` header on 201 responses | `POST /clients/{id}/bots` now returns `Location: /api/v1/clients/{id}/bots/{botid}` |

### New endpoints added

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health/ready` | Readiness probe — 503 if any service failed to initialise |
| GET | `/api/v1/clients/{id}/bots/{botid}/status` | Bot runtime status: `registered`, `running`, `halted` |
| GET | `/api/v1/clients/{id}/parameters/defaults` | Default trading parameters |
| GET | `/api/v1/clients/{id}/indicators/defaults` | Default indicator settings |

### Shared handler extraction

`src/api/v1/_bot_handlers.py` now contains all bot lifecycle logic. Both `clients.py` (canonical) and `bots.py` (legacy) delegate to these shared functions. The `_parse_ts()` helper lives here and is applied to all four history endpoints.

### TypeScript contract update

`WsStopCommand` added to `shared/types/api.ts` — the `stop` WebSocket command is now part of the typed `WsCommand` union.
