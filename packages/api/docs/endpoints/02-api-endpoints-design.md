# Prompt 02 — API Endpoints Design & REST Contract Review

**Generated:** July 2025  
**Reviewer:** Amazon Q (Senior Python / FastAPI / REST Design)  
**Source files inspected:** `packages/api/src/api/v1/endpoints/`, `packages/api/src/services/`, `packages/api/src/models/schemas.py`, `packages/bot/sonarft_manager.py`  
**Output location:** `docs/endpoints/02-api-endpoints-design.md`

---

## Executive Summary

The SonarFT API exposes 14 endpoints across three routers (health, bots, config) plus one WebSocket route, all correctly versioned under `/api/v1`. HTTP method usage is largely appropriate and path naming is consistent. Four design issues stand out: `GET /bots` and `GET /parameters` / `GET /indicators` accept `client_id` as a query parameter rather than a path segment, which is unconventional for resource-scoped collections; `GET /{botid}/orders` and `GET /{botid}/trades` return untyped `list` responses with no Pydantic schema; there is no pagination, filtering, or sorting on any list endpoint; and there is no rate limiting beyond the bot-count cap. The bot lifecycle flow (create → run → stop → delete) maps cleanly onto the underlying `BotManager` in `sonarft_manager.py`, but the `stop` and `delete` operations are functionally identical at the service layer, which is a contract ambiguity surfaced to API consumers.

---

## Complete Endpoint Reference

| # | Method | Path | Handler | File | Auth | Request | Response Schema | Status Codes |
|---|---|---|---|---|---|---|---|---|
| 1 | GET | `/api/v1/health` | `health` | `health.py:7` | ❌ None | — | `HealthResponse` | 200 |
| 2 | GET | `/api/v1/bots` | `list_bots` | `bots.py:18` | ✅ Bearer | `?client_id=` (query) | `BotListResponse` | 200, 401 |
| 3 | POST | `/api/v1/bots` | `create_bot` | `bots.py:26` | ✅ Bearer | `?client_id=` (query) | `BotCreateResponse` | 201, 401, 429 |
| 4 | POST | `/api/v1/bots/{botid}/run` | `run_bot` | `bots.py:35` | ✅ Bearer | `{botid}` (path) | `MessageResponse` | 200, 401, 404 |
| 5 | POST | `/api/v1/bots/{botid}/stop` | `stop_bot` | `bots.py:47` | ✅ Bearer | `{botid}` (path) | `MessageResponse` | 200, 401, 404 |
| 6 | DELETE | `/api/v1/bots/{botid}` | `remove_bot` | `bots.py:59` | ✅ Bearer | `{botid}` (path) | `MessageResponse` | 200, 401, 404 |
| 7 | GET | `/api/v1/bots/{botid}/orders` | `get_orders` | `bots.py:71` | ✅ Bearer | `{botid}` (path) | `list` (untyped) | 200, 401 |
| 8 | GET | `/api/v1/bots/{botid}/trades` | `get_trades` | `bots.py:80` | ✅ Bearer | `{botid}` (path) | `list` (untyped) | 200, 401 |
| 9 | GET | `/api/v1/parameters/defaults` | `get_default_parameters` | `config.py:18` | ✅ Bearer | — | `ParametersConfig` | 200, 401 |
| 10 | GET | `/api/v1/parameters` | `get_parameters` | `config.py:26` | ✅ Bearer | `?client_id=` (query) | `ParametersConfig` | 200, 401 |
| 11 | PUT | `/api/v1/parameters` | `update_parameters` | `config.py:35` | ✅ Bearer | `?client_id=` + body `ParametersConfig` | `MessageResponse` | 200, 401 |
| 12 | GET | `/api/v1/indicators/defaults` | `get_default_indicators` | `config.py:45` | ✅ Bearer | — | `IndicatorsConfig` | 200, 401 |
| 13 | GET | `/api/v1/indicators` | `get_indicators` | `config.py:53` | ✅ Bearer | `?client_id=` (query) | `IndicatorsConfig` | 200, 401 |
| 14 | PUT | `/api/v1/indicators` | `update_indicators` | `config.py:62` | ✅ Bearer | `?client_id=` + body `IndicatorsConfig` | `MessageResponse` | 200, 401 |
| 15 | WS | `/api/v1/ws/{client_id}` | `websocket_endpoint` | `main.py:57` | ✅ `?token=` | JSON frames | JSON event stream | 1000, 1008 |

---

## Endpoint Hierarchy

```
/api/v1
├── GET  /health                          (no auth)
│
├── GET  /bots?client_id=                 (list bots for client)
├── POST /bots?client_id=                 (create bot for client)
├── POST /bots/{botid}/run                (start bot)
├── POST /bots/{botid}/stop               (stop bot)
├── DELETE /bots/{botid}                  (remove bot)
├── GET  /bots/{botid}/orders             (order history)
├── GET  /bots/{botid}/trades             (trade history)
│
├── GET  /parameters/defaults             (global defaults)
├── GET  /parameters?client_id=           (client parameters)
├── PUT  /parameters?client_id=           (update client parameters)
│
├── GET  /indicators/defaults             (global defaults)
├── GET  /indicators?client_id=           (client indicators)
├── PUT  /indicators?client_id=           (update client indicators)
│
└── WS   /ws/{client_id}?token=           (real-time event stream)
```

---

## 1. HTTP Method Review

| Endpoint | Method | Assessment |
|---|---|---|
| `GET /health` | GET | ✅ Correct — read-only, safe, idempotent |
| `GET /bots` | GET | ✅ Correct — read-only collection |
| `POST /bots` | POST | ✅ Correct — non-idempotent resource creation |
| `POST /bots/{botid}/run` | POST | ✅ Acceptable — action/command on a resource sub-resource |
| `POST /bots/{botid}/stop` | POST | ✅ Acceptable — action/command pattern |
| `DELETE /bots/{botid}` | DELETE | ✅ Correct — resource removal |
| `GET /bots/{botid}/orders` | GET | ✅ Correct — read-only sub-collection |
| `GET /bots/{botid}/trades` | GET | ✅ Correct — read-only sub-collection |
| `GET /parameters/defaults` | GET | ✅ Correct |
| `GET /parameters` | GET | ✅ Correct |
| `PUT /parameters` | PUT | ⚠️ Partial — PUT implies full replacement; if only some fields are sent, the rest are silently defaulted by Pydantic. `PATCH` would be more semantically accurate for partial updates |
| `GET /indicators/defaults` | GET | ✅ Correct |
| `GET /indicators` | GET | ✅ Correct |
| `PUT /indicators` | PUT | ⚠️ Same as above — `PATCH` more appropriate for partial config updates |

---

## 2. URI Path Design

### Strengths
- All paths are correctly prefixed with `/api/v1` via `settings.api_prefix`
- Bot sub-resources (`/orders`, `/trades`, `/run`, `/stop`) follow the nested resource pattern correctly
- `/parameters/defaults` and `/indicators/defaults` are clean sub-paths for global defaults

### Issues

**`client_id` as query parameter instead of path segment** (Medium)

Endpoints `GET /bots`, `POST /bots`, `GET /parameters`, `PUT /parameters`, `GET /indicators`, `PUT /indicators` all accept `client_id` as a query parameter. Since `client_id` scopes the resource (it is the owner/tenant), it should be a path segment:

```
# Current (query param — unconventional)
GET /api/v1/bots?client_id=abc123

# Recommended (path segment — RESTful)
GET /api/v1/clients/{client_id}/bots
POST /api/v1/clients/{client_id}/bots
GET /api/v1/clients/{client_id}/parameters
PUT /api/v1/clients/{client_id}/parameters
GET /api/v1/clients/{client_id}/indicators
PUT /api/v1/clients/{client_id}/indicators
```

This also enables consistent path validation (regex pattern) on `client_id`, matching what is already done for `botid`.

**`/parameters` and `/indicators` lack a router prefix** (Low)

`config.py` defines `router = APIRouter(tags=["Configuration"])` with no `prefix`. The paths `/parameters` and `/indicators` are flat — they do not share a common resource prefix. A prefix of `/config` or grouping under `/clients/{client_id}` would improve discoverability.

**`stop` vs `delete` ambiguity** (Medium)

`POST /bots/{botid}/stop` and `DELETE /bots/{botid}` both ultimately call `_manager.remove_bot` in `sonarft_manager.py`. From a REST consumer's perspective, `stop` implies a reversible pause (the bot remains registered), while `delete` implies permanent removal. The current implementation makes them identical, which is misleading.

---

## 3. Request & Response Contracts

### Request Bodies

| Endpoint | Body Schema | Validation |
|---|---|---|
| `POST /bots` | None (client_id via query) | ✅ No body needed |
| `PUT /parameters` | `ParametersConfig` | ✅ Pydantic v2 validated |
| `PUT /indicators` | `IndicatorsConfig` | ✅ Pydantic v2 validated |
| All others | None | ✅ N/A |

### Response Schemas

| Endpoint | Response Schema | Issue |
|---|---|---|
| `GET /health` | `HealthResponse` | ⚠️ `version` hardcoded as `"1.0.0"` — not from `Settings` |
| `GET /bots` | `BotListResponse` | ✅ Typed |
| `POST /bots` | `BotCreateResponse` | ✅ Typed |
| `POST /bots/{botid}/run` | `MessageResponse` | ⚠️ Plain string message — no structured data (e.g. bot status) |
| `POST /bots/{botid}/stop` | `MessageResponse` | ⚠️ Same as above |
| `DELETE /bots/{botid}` | `MessageResponse` | ⚠️ 200 + body on DELETE — convention is 204 No Content |
| `GET /bots/{botid}/orders` | `list` (untyped) | ❌ No Pydantic schema — OpenAPI shows `array` with no item type |
| `GET /bots/{botid}/trades` | `list` (untyped) | ❌ No Pydantic schema — `TradeRecord` exists in `schemas.py` but is unused here |
| `GET /parameters/defaults` | `ParametersConfig` | ✅ Typed |
| `GET /parameters` | `ParametersConfig` | ✅ Typed |
| `PUT /parameters` | `MessageResponse` | ✅ Acceptable |
| `GET /indicators/defaults` | `IndicatorsConfig` | ✅ Typed |
| `GET /indicators` | `IndicatorsConfig` | ✅ Typed |
| `PUT /indicators` | `MessageResponse` | ✅ Acceptable |

### `TradeRecord` is defined but never used

`schemas.py` defines `TradeRecord` with all trade fields (`timestamp`, `position`, `base`, `quote`, `buy_price`, `sell_price`, `profit`, etc.) but `get_orders` and `get_trades` in `bots.py` return `list` with no `response_model`. This means the OpenAPI spec documents these endpoints as returning an untyped array, and no serialization validation occurs.

---

## 4. Status Code Usage

| Scenario | Current Code | Assessment |
|---|---|---|
| Successful GET | 200 | ✅ Correct |
| Successful POST (create bot) | 201 | ✅ Correct — `status_code=201` set explicitly |
| Successful POST (run/stop) | 200 | ✅ Acceptable for action endpoints |
| Successful DELETE | 200 + body | ⚠️ Convention is `204 No Content` with no body |
| Bot not found | 404 | ✅ Correct |
| Bot limit exceeded | 429 | ✅ Correct — semantically appropriate (Too Many Requests) |
| Unauthorized | 401 | ✅ Correct |
| Validation error (Pydantic) | 422 | ✅ FastAPI default — correct |
| Unhandled exception | 500 | ✅ Correct — via `generic_error_handler` |
| WebSocket auth failure | 1008 (Policy Violation) | ✅ Correct WebSocket close code |

**Missing status codes:**
- `400 Bad Request` — no explicit validation errors beyond Pydantic 422 (e.g. empty `client_id` query param is not validated)
- `403 Forbidden` — no role-based access control; auth is binary (valid token / no token)
- `503 Service Unavailable` — no health degradation signaling if bot engine fails to import

---

## 5. API Consistency

### Naming Consistency

| Aspect | Assessment |
|---|---|
| Resource names (plural) | ✅ `/bots`, `/orders`, `/trades` — all plural collections |
| Action sub-resources | ✅ `/run`, `/stop` — consistent verb-as-sub-resource pattern |
| Query parameter names | ✅ `client_id` used consistently across all scoped endpoints |
| Response field names | ✅ `snake_case` throughout |
| Error response format | ⚠️ Inconsistent — domain errors return `{"detail": "..."}` (FastAPI default), but `MessageResponse` returns `{"message": "..."}`. Two different shapes for "something happened" responses |

### Error Response Format Inconsistency

```python
# Domain errors (BotNotFoundError, BotLimitExceededError) → FastAPI HTTPException shape
{"detail": "Bot not found: abc123"}

# Success action responses (run, stop, remove) → MessageResponse shape  
{"message": "Bot abc123 started."}

# Generic 500 → generic_error_handler shape
{"detail": "Internal server error"}
```

Three different shapes. A consumer must handle `detail` for errors and `message` for successes. Standardizing on `{"detail": "..."}` for all error responses (FastAPI convention) and `{"message": "..."}` for all success responses is the minimum fix.

---

## 6. Pagination, Filtering, Sorting

| Feature | Status | Impact |
|---|---|---|
| Pagination on `GET /bots/{botid}/orders` | ❌ Not implemented | High — unbounded SQLite query; large history will return all records |
| Pagination on `GET /bots/{botid}/trades` | ❌ Not implemented | High — same issue |
| Filtering by date range | ❌ Not implemented | Medium — no way to query recent trades only |
| Sorting | ❌ Not implemented | Low — SQLite query in `_db_query` uses `ORDER BY id` (insertion order) |
| Pagination on `GET /bots` | ❌ Not implemented | Low — bot count is bounded by `max_bots_per_client` |

The `_db_query` classmethod in `sonarft_helpers.py` fetches all rows for a `botid` with no `LIMIT`/`OFFSET`. For a long-running bot with thousands of trades, `GET /bots/{botid}/trades` will return the entire history in one response.

---

## 7. Rate Limiting & Throttling

| Mechanism | Status |
|---|---|
| Per-client bot count cap | ✅ Enforced in `BotService.create_bot` and `WebSocketManager._receive_loop` |
| HTTP request rate limiting | ❌ Not implemented |
| WebSocket message rate limiting | ❌ Not implemented |
| Rate limit response headers (`X-RateLimit-*`) | ❌ Not present |

There is no HTTP-level rate limiting middleware. A client can call `POST /bots/{botid}/run` or `PUT /parameters` in a tight loop without restriction. For a trading system controlling real money, this is a meaningful gap.

---

## 8. API Versioning

| Aspect | Status |
|---|---|
| Version prefix `/api/v1` | ✅ Applied via `settings.api_prefix` to all routers |
| Version in `HealthResponse` | ⚠️ Hardcoded `"1.0.0"` — not from `Settings.api_version` |
| Deprecation headers | ❌ Not implemented |
| v2 migration path | ❌ Not planned — no versioning strategy documented |

The versioning is structurally correct. Adding a v2 would require duplicating the router registration in `create_app()` and creating a new `api/v2/` directory — the current structure supports this without changes.

---

## 9. OpenAPI Documentation

FastAPI auto-generates OpenAPI from type annotations and docstrings. Current state:

| Endpoint | Docstring | Response Example | Request Example |
|---|---|---|---|
| `GET /health` | ✅ "Service health check." | ✅ (from schema default) | N/A |
| `GET /bots` | ✅ "List all bot IDs for a client." | ✅ | N/A |
| `POST /bots` | ✅ "Create a new bot for a client." | ✅ | N/A |
| `POST /bots/{botid}/run` | ✅ "Start a bot." | ✅ | N/A |
| `POST /bots/{botid}/stop` | ✅ "Stop a running bot." | ✅ | N/A |
| `DELETE /bots/{botid}` | ✅ "Remove a bot." | ✅ | N/A |
| `GET /bots/{botid}/orders` | ✅ "Get order history for a bot." | ❌ Untyped `array` | N/A |
| `GET /bots/{botid}/trades` | ✅ "Get trade history for a bot." | ❌ Untyped `array` | N/A |
| `PUT /parameters` | ✅ | ✅ | ⚠️ No field descriptions in `ParametersConfig` |
| `PUT /indicators` | ✅ | ✅ | ⚠️ No field descriptions in `IndicatorsConfig` |

The biggest OpenAPI gap is the untyped `list` return on orders/trades — the interactive docs at `/api/v1/docs` will show no schema for these responses, making them opaque to frontend developers.

---

## Issues Summary

| # | Issue | Severity | Location |
|---|---|---|---|
| 1 | `GET /bots/{botid}/orders` and `/trades` return untyped `list` — `TradeRecord` schema exists but is unused | **High** | `bots.py:71,80` |
| 2 | No pagination on orders/trades — unbounded SQLite query for all history | **High** | `bots.py:71,80`, `sonarft_helpers.py:_db_query` |
| 3 | `stop_bot` and `remove_bot` are functionally identical at the service layer — misleading API contract | **Medium** | `bot_service.py:44-51`, `sonarft_manager.py` |
| 4 | `client_id` passed as query parameter instead of path segment — unconventional for resource scoping | **Medium** | `bots.py:19,28`, `config.py:27,36,54,63` |
| 5 | No HTTP rate limiting middleware — trading endpoints callable in tight loops | **Medium** | `main.py` (missing) |
| 6 | `DELETE /bots/{botid}` returns 200 + body — convention is 204 No Content | **Low** | `bots.py:59` |
| 7 | `PUT /parameters` and `PUT /indicators` use PUT semantics but behave as PATCH (partial update) | **Low** | `config.py:35,62` |
| 8 | Error response shape inconsistency — `{"detail": ...}` vs `{"message": ...}` | **Low** | `errors.py`, `schemas.py` |
| 9 | `client_id` query parameter not validated (no regex pattern, no length limit) | **Low** | `bots.py:19,28`, `config.py:27,36,54,63` |
| 10 | `HealthResponse.version` hardcoded — not sourced from `Settings.api_version` | **Low** | `schemas.py:80`, `health.py` |

---

## Recommendations

### Priority 1 — High impact

**1. Apply `response_model` to orders and trades endpoints**

```python
# bots.py — before
@router.get("/{botid}/orders")
async def get_orders(...) -> list:

# after
@router.get("/{botid}/orders", response_model=list[TradeRecord])
async def get_orders(...) -> list[TradeRecord]:
```

`TradeRecord` is already defined in `schemas.py` — it just needs to be imported and wired in.

**2. Add pagination to orders and trades**

```python
@router.get("/{botid}/orders", response_model=list[TradeRecord])
async def get_orders(
    botid: Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{1,64}$")],
    _: Auth,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: BotService = Depends(get_bot_service),
) -> list[TradeRecord]:
```

This requires adding `LIMIT`/`OFFSET` support to `SonarftHelpers._db_query`.

### Priority 2 — Medium impact

**3. Differentiate `stop` from `remove`**

`stop_bot` in `BotService` should set `bot.stop_bot_flag = True` (halt the run loop) without removing the bot from the registry. `remove_bot` should stop and deregister. This matches the semantic contract the API exposes.

**4. Add `client_id` path validation**

```python
# Apply the same pattern used for botid
ClientId = Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{1,64}$")]
```

Or, if moving to path segments, validate at the router level.

**5. Add rate limiting middleware**

```python
# requirements.txt — add:
slowapi

# main.py
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# bots.py
@router.post("/{botid}/run")
@limiter.limit("10/minute")
async def run_bot(...):
```

### Priority 3 — Low impact

**6. Return 204 on DELETE**

```python
@router.delete("/{botid}", status_code=204)
async def remove_bot(...) -> None:
    await service.remove_bot(botid)
    # no return body
```

**7. Standardize error response shape**

Use FastAPI's `HTTPException` with `detail` consistently for all error cases. Remove `MessageResponse` from error paths and reserve it for success action responses only.

---

## Before / After: Orders Endpoint

```python
# BEFORE — bots.py:71
@router.get("/{botid}/orders")
async def get_orders(
    botid: Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{1,64}$")],
    _: Auth,
    service: BotService = Depends(get_bot_service),
) -> list:
    return await service.get_orders(botid)


# AFTER — typed, paginated, documented
@router.get("/{botid}/orders", response_model=list[TradeRecord])
async def get_orders(
    botid: Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{1,64}$")],
    _: Auth,
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Records to skip"),
    service: BotService = Depends(get_bot_service),
) -> list[TradeRecord]:
    """Get order history for a bot."""
    return await service.get_orders(botid, limit=limit, offset=offset)
```

---

_Part of the SonarFT API Code Review Prompt Suite — Prompt 02_  
_Previous: [Prompt 01 — Architecture Structure](../architecture/01-api-architecture.md)_  
_Next: [Prompt 03 — Data Models & Validation](../prompts/03-data-models-validation.md)_
