# Prompt 02 — API Endpoints Design & REST Contract Review

**Generated:** July 2025 | **Updated:** July 2025 (post-implementation)
**Reviewer:** Amazon Q (Senior Python / FastAPI / REST Design)
**Status:** ✅ All high/medium findings resolved

---

## Executive Summary

The SonarFT API now exposes 20 endpoints across five routers plus one WebSocket route. The canonical path-segment routes (`/clients/{client_id}/bots`) replace the legacy query-parameter pattern. All originally identified issues have been resolved: `TradeRecord` is wired as `response_model` on orders/trades endpoints; pagination (`limit`/`offset`) is implemented; `stop` and `remove` are semantically distinct; `slowapi` rate limiting is active on all endpoints; and `client_id` is validated by path regex in the canonical router.

---

## Complete Endpoint Reference (Current)

### Canonical Routes (preferred)

| Method | Path | Auth | Response | Rate Limit |
|---|---|---|---|---|
| GET | `/api/v1/clients/{client_id}/bots` | ✅ Bearer | `BotListResponse` | 60/min |
| POST | `/api/v1/clients/{client_id}/bots` | ✅ Bearer | `BotCreateResponse` 201 | 10/min |
| POST | `/api/v1/clients/{client_id}/bots/{botid}/run` | ✅ Bearer | `MessageResponse` | 20/min |
| POST | `/api/v1/clients/{client_id}/bots/{botid}/stop` | ✅ Bearer | `MessageResponse` | 20/min |
| DELETE | `/api/v1/clients/{client_id}/bots/{botid}` | ✅ Bearer | `MessageResponse` | 20/min |
| GET | `/api/v1/clients/{client_id}/bots/{botid}/orders` | ✅ Bearer | `list[TradeRecord]` | 60/min |
| GET | `/api/v1/clients/{client_id}/bots/{botid}/trades` | ✅ Bearer | `list[TradeRecord]` | 60/min |
| GET | `/api/v1/clients/{client_id}/parameters` | ✅ Bearer | `ParametersConfig` | 60/min |
| PUT | `/api/v1/clients/{client_id}/parameters` | ✅ Bearer | `MessageResponse` | 30/min |
| GET | `/api/v1/clients/{client_id}/indicators` | ✅ Bearer | `IndicatorsConfig` | 60/min |
| PUT | `/api/v1/clients/{client_id}/indicators` | ✅ Bearer | `MessageResponse` | 30/min |

### Global / Auth Routes

| Method | Path | Auth | Response | Rate Limit |
|---|---|---|---|---|
| GET | `/api/v1/health` | ❌ None | `HealthResponse` | — |
| GET | `/api/v1/parameters/defaults` | ✅ Bearer | `ParametersConfig` | 60/min |
| GET | `/api/v1/indicators/defaults` | ✅ Bearer | `IndicatorsConfig` | 60/min |
| POST | `/api/v1/ws/ticket` | ✅ Bearer | `WsTicketResponse` | 30/min |
| WS | `/api/v1/ws/{client_id}?ticket=` | ✅ Ticket | JSON event stream | — |

### Legacy Routes (deprecated — still functional)

| Method | Path | Notes |
|---|---|---|
| GET/POST | `/api/v1/bots?client_id=` | Marked `deprecated=True` in OpenAPI |
| POST | `/api/v1/bots/{botid}/run\|stop` | Marked deprecated |
| DELETE | `/api/v1/bots/{botid}` | Marked deprecated |
| GET | `/api/v1/bots/{botid}/orders\|trades` | Marked deprecated |
| GET/PUT | `/api/v1/parameters?client_id=` | Marked deprecated |
| GET/PUT | `/api/v1/indicators?client_id=` | Marked deprecated |

---

## Resolved Issues

| # | Original Issue | Resolution |
|---|---|---|
| 1 | Orders/trades return untyped `list` | ✅ `response_model=list[TradeRecord]` on both endpoints |
| 2 | No pagination on orders/trades | ✅ `limit` (1–1000, default 100) + `offset` query params; `ORDER BY id DESC` |
| 3 | `stop_bot` ≡ `remove_bot` | ✅ `stop` → `pause_bot()` (keeps registered); `DELETE` → full removal |
| 4 | `client_id` as query param | ✅ Canonical `/clients/{client_id}/bots` with `Path(pattern=...)` validation |
| 5 | No HTTP rate limiting | ✅ `slowapi` — 10/min create, 20/min actions, 30/min PUT, 60/min GET, 200/min global |
| 6 | `client_id` not validated | ✅ `Path(pattern=r"^[a-zA-Z0-9_-]{1,64}$")` in canonical router |
| 7 | `HealthResponse.version` hardcoded | ℹ️ Remains `"1.0.0"` — minor, acceptable |

---

## Pagination

```
GET /api/v1/clients/{client_id}/bots/{botid}/orders?limit=100&offset=0
GET /api/v1/clients/{client_id}/bots/{botid}/trades?limit=50&offset=100
```

- `limit`: 1–1000, default 100 (validated with `ge=1, le=1000`)
- `offset`: ≥0, default 0
- Results ordered by `id DESC` (most recent first)
- `_db_query` in `sonarft_helpers.py` uses `LIMIT ? OFFSET ?`

---

## Rate Limiting

| Endpoint group | Limit | Rationale |
|---|---|---|
| `POST /clients/{id}/bots` | 10/min | Bot creation is expensive |
| `POST .../run`, `.../stop`, `DELETE` | 20/min | Prevent rapid cycling |
| `PUT .../parameters`, `.../indicators` | 30/min | Config flooding prevention |
| All GET endpoints | 60/min | Read-heavy, less critical |
| `POST /ws/ticket` | 30/min | Ticket issuance |
| Global default | 200/min per IP | DDoS baseline |

---

## WebSocket Authentication Flow

```
1. Client: POST /api/v1/ws/ticket  (Authorization: Bearer <jwt>)
   Server: {"ticket": "HutIc__IWEbLV0O9...", "ttl_seconds": 30}

2. Client: WS /api/v1/ws/{clientId}?ticket=HutIc__IWEbLV0O9...
   Server: {"type": "connected", "client_id": "...", "ts": ...}
```

JWT never appears in a URL. Ticket is single-use, 30s TTL, `secrets.token_urlsafe(32)`.

---

_Part of the SonarFT API Code Review Prompt Suite — Prompt 02_
_Previous: [Prompt 01 — Architecture](../architecture/01-api-architecture.md)_
_Next: [Prompt 03 — Data Models](../models/03-data-models-validation.md)_
