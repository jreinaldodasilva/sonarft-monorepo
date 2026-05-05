# API Architecture & Project Structure Review

**Prompt ID:** 01-API-ARCH  
**Package:** `packages/api`  
**Reviewer:** Amazon Q (Senior Python / FastAPI / Async Systems)  
**Date:** July 2025  
**Status:** Complete

---

## Executive Summary

The SonarFT API is a well-structured FastAPI service that cleanly separates transport, service, and infrastructure concerns across five distinct layers. The application factory pattern (`create_app()` in `src/main.py`) is correctly implemented with lifespan-managed service initialisation, layered middleware, and typed dependency injection throughout. Bot-engine integration is achieved via direct in-process import of the `sonarft-bot` package (installed as an editable local dependency), which is a pragmatic and low-latency choice but creates a tight runtime coupling that limits independent deployment. The dual-route strategy (canonical `/clients/{id}/bots` + deprecated `/bots?client_id=`) is clearly signposted in OpenAPI but introduces meaningful code duplication across `clients.py` and `bots.py`. Overall the architecture is production-ready for a single-process deployment; the main structural risks are the in-process bot coupling, the absence of a persistence abstraction layer, and the single-instance WebSocket ticket store.

---

## 1. Architecture Diagram

```mermaid
graph TD
    subgraph Frontend["sonarftweb (React / TypeScript)"]
        FE[Browser Client]
    end

    subgraph API["packages/api — FastAPI / Uvicorn"]
        MW["Middleware Stack\n(CORS → RequestId → SecurityHeaders → SlowAPI)"]
        R_H[health.py]
        R_C[clients.py — canonical]
        R_B[bots.py — legacy/deprecated]
        R_CFG[config.py — legacy/deprecated]
        R_WS_T[ws_ticket.py]
        WS_EP[WebSocket endpoint\n/api/v1/ws/{client_id}]

        subgraph Core["src/core/"]
            CFG[config.py\nSettings / pydantic-settings]
            SEC[security.py\nJWT / static token / ticket sentinel]
            ERR[errors.py\nBotNotFoundError / BotLimitExceededError]
            CTX[context.py\nrequest_id ContextVar]
            LIM[limiter.py\nslowapi Limiter]
        end

        subgraph Services["src/services/"]
            BS[bot_service.py\nBotService]
            CS[config_service.py\nConfigService]
        end

        subgraph WS["src/websocket/"]
            WM[manager.py\nWebSocketManager + WsLogHandler]
            TK[tickets.py\nTicketStore]
        end

        subgraph Models["src/models/"]
            SCH[schemas.py\nPydantic v2 models]
        end
    end

    subgraph Bot["packages/bot — sonarft-bot (editable install)"]
        BM[sonarft_manager.py\nBotManager]
        SB[sonarft_bot.py\nSonarftBot]
        SH[sonarft_helpers.py\nSonarftHelpers + SQLite]
        SS[sonarft_search.py\nSonarftSearch]
        SI[sonarft_indicators.py]
        SP[sonarft_prices.py]
        SE[sonarft_execution.py]
    end

    subgraph Exchanges["External"]
        EX[CCXT / CCXTpro\nExchange APIs]
    end

    FE -->|HTTP REST + JWT| MW
    FE -->|WS ?ticket=| WS_EP
    MW --> R_H & R_C & R_B & R_CFG & R_WS_T
    R_C & R_B --> BS
    R_CFG & R_C --> CS
    R_WS_T --> TK
    WS_EP --> WM
    WM --> BM
    BS --> BM
    BM --> SB --> SS --> SI & SP & SE
    SH -->|SQLite WAL| DB[(sonarft.db)]
    SE --> EX
    CS -->|JSON files| FS[(sonarftdata/config/)]
```

---

## 2. Module Organisation Table

| Module | File(s) | Responsibility | Lines (approx.) |
|---|---|---|---|
| Application factory | `src/main.py` | `create_app()`, middleware stack, lifespan, WebSocket endpoint, logging setup | ~230 |
| Settings | `src/core/config.py` | `Settings` (pydantic-settings), `get_settings()` lru_cache | ~45 |
| Security | `src/core/security.py` | JWT (Netlify JWKS), static token, `require_auth`, `get_client_id` deps | ~120 |
| Error handling | `src/core/errors.py` | `BotNotFoundError`, `BotLimitExceededError`, async exception handlers | ~35 |
| Request context | `src/core/context.py` | `request_id_var` ContextVar — avoids circular import with `main.py` | ~12 |
| Rate limiter | `src/core/limiter.py` | `slowapi.Limiter` singleton (200 req/min default) | ~8 |
| Canonical endpoints | `src/api/v1/endpoints/clients.py` | `/clients/{id}/bots`, `/clients/{id}/parameters`, `/clients/{id}/indicators` | ~175 |
| Legacy bot endpoints | `src/api/v1/endpoints/bots.py` | `/bots?client_id=` (deprecated) | ~100 |
| Legacy config endpoints | `src/api/v1/endpoints/config.py` | `/parameters`, `/indicators` (deprecated) | ~90 |
| Health | `src/api/v1/endpoints/health.py` | `GET /health` | ~10 |
| WS ticket | `src/api/v1/endpoints/ws_ticket.py` | `POST /ws/ticket` — issues single-use ticket | ~35 |
| Bot service | `src/services/bot_service.py` | Wraps `BotManager`; tenant isolation, bot limit enforcement | ~80 |
| Config service | `src/services/config_service.py` | Atomic JSON read/write for parameters & indicators; path traversal guard | ~120 |
| Pydantic schemas | `src/models/schemas.py` | All request/response models; config key validation regex | ~130 |
| WebSocket manager | `src/websocket/manager.py` | Per-client connection, `WsLogHandler`, send/receive loops, keepalive | ~290 |
| Ticket store | `src/websocket/tickets.py` | In-memory single-use ticket store with TTL and eviction | ~60 |

---

## 3. Integration Points

### 3.1 API → Bot Engine (in-process)

The API integrates with the bot engine via **direct Python import**, not subprocess or IPC. The bot package is installed as an editable local dependency (`pip install -e ../bot`, declared in `requirements.txt`).

| API file | Bot file imported | Symbol used |
|---|---|---|
| `src/services/bot_service.py:26` | `sonarft_manager.py` | `BotManager` |
| `src/services/bot_service.py:25` | `sonarft_helpers.py` | `SonarftHelpers` (classmethod `_async_query`) |
| `src/websocket/manager.py` | _(indirect via BotManager)_ | `BotManager.create_bot`, `run_bot`, `pause_bot`, `remove_bot`, `set_simulation_mode` |

The import is **lazy** (deferred to `BotService.__init__` inside the lifespan handler) so the API process can start even if the bot package is missing, surfacing the error as a logged warning rather than a startup crash.

### 3.2 API → Frontend

- REST: standard HTTP/JSON over CORS-controlled origins (`http://localhost:3000`, `http://localhost:5173` by default).
- WebSocket: `ws://host/api/v1/ws/{client_id}?ticket=<token>` — ticket issued by `POST /ws/ticket`.
- Auth: Netlify Identity JWT (RS256) or static `SONARFT_API_TOKEN`; dev mode disables auth when neither is set.

### 3.3 Bot Engine → Exchanges

`SonarftApiManager` (in `packages/bot/sonarft_api_manager.py`) dispatches to ccxtpro (WebSocket) or ccxt (REST) depending on the `-l` flag. The API layer has no direct exchange dependency.

### 3.4 Persistence

| Store | Location | Used by |
|---|---|---|
| Trade/order history | `sonarftdata/history/sonarft.db` (SQLite WAL) | `SonarftHelpers` in bot package; queried by `BotService._helpers._async_query` |
| Per-client config | `sonarftdata/config/{client_id}_parameters.json` / `_indicators.json` | `ConfigService` |
| Bot registry | `sonarftdata/bots/{botid}.json` | `SonarftHelpers.save_botid` |

---

## 4. Application Factory Pattern

`create_app()` in `src/main.py` follows the standard FastAPI factory pattern correctly:

1. **Settings** — `get_settings()` (lru_cache) called first; drives all configuration.
2. **FastAPI instance** — title, version, docs/redoc/openapi URLs, and `_lifespan` context manager registered.
3. **Lifespan** — `_lifespan` initialises `BotService` and `ConfigService` on `app.state` before the server accepts requests. Failures are logged but do not crash the process (graceful degradation).
4. **Middleware** (outermost → innermost, i.e. last-added wraps first):
   - `SlowAPIMiddleware` (rate limiting)
   - `SecurityHeadersMiddleware` (X-Frame-Options, HSTS, CSP-adjacent headers)
   - `RequestIdMiddleware` (X-Request-ID propagation + ContextVar)
   - `CORSMiddleware`
5. **Exception handlers** — `BotNotFoundError` → 404, `BotLimitExceededError` → 429, `Exception` → 500.
6. **Routers** — all five routers included under `settings.api_prefix` (`/api/v1`).
7. **WebSocket endpoint** — defined inline in `create_app()` rather than in a router; this is the only structural inconsistency (see Concerns §6.2).

---

## 5. Cross-Package Dependencies

```
packages/api
  └── requires (editable install): packages/bot
        ├── sonarft_manager.BotManager          ← bot_service.py
        ├── sonarft_helpers.SonarftHelpers      ← bot_service.py
        └── (transitive) sonarft_bot, sonarft_search, sonarft_indicators,
            sonarft_prices, sonarft_execution, sonarft_validators,
            sonarft_api_manager, sonarft_math, models.Trade
```

There are **no circular dependencies** — the bot package has no knowledge of the API package. The dependency graph is strictly one-directional: `api → bot`.

The bot package's own dependencies (ccxt, ccxtpro, pandas, pandas-ta) are pulled in transitively when the API process starts. This means the API process carries the full weight of the trading engine's dependency tree.

---

## 6. Architectural Strengths

1. **Clean layered separation** — endpoints delegate entirely to services; services delegate to the bot engine or file system; no business logic leaks into routers. The `core/` modules (config, security, errors, context, limiter) are each single-responsibility and free of cross-dependencies.

2. **Security-first middleware stack** — HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, and Permissions-Policy are applied globally via `SecurityHeadersMiddleware`. The WebSocket ticket pattern keeps JWTs out of server logs and browser history. Static token comparison uses `hmac.compare_digest` to prevent timing attacks (`security.py:72`).

3. **Async-correct I/O** — all blocking file operations in `ConfigService` are wrapped in `asyncio.to_thread` (`config_service.py:72,82,95`). The SQLite layer in `SonarftHelpers` uses WAL mode for concurrent read/write and is accessed exclusively via `asyncio.to_thread`. The WebSocket manager uses `asyncio.Queue` with `put_nowait` to avoid blocking the event loop from log handlers.

---

## 7. Architectural Concerns

| # | Concern | Severity | Location |
|---|---|---|---|
| 7.1 | **In-process bot coupling** — API and bot run in the same process. A bot crash, memory leak, or blocking call in the trading engine can take down the API. Independent scaling and deployment are not possible. | High | `bot_service.py:25-27` |
| 7.2 | **WebSocket endpoint defined inline in `create_app()`** — the WS endpoint is not a router; it is a bare `@app.websocket` decorator inside the factory function. This makes it invisible to OpenAPI docs, untestable via `APIRouter`, and harder to discover. | Medium | `main.py:185-215` |
| 7.3 | **Duplicate endpoint logic** — `clients.py` and `bots.py` implement identical bot CRUD operations (list, create, run, stop, remove, orders, trades). `clients.py` and `config.py` duplicate parameters/indicators CRUD. Any change to business logic must be applied in two places. | Medium | `clients.py`, `bots.py`, `config.py` |
| 7.4 | **Single-instance TicketStore** — `tickets.py` uses a module-level singleton (`_store`). In a multi-worker deployment (e.g. `uvicorn --workers 4`), each worker has its own store; a ticket issued by worker A cannot be redeemed by worker B. | Medium | `websocket/tickets.py:68` |
| 7.5 | **No persistence abstraction layer** — `ConfigService` reads/writes JSON files directly; `BotService` calls `SonarftHelpers._async_query` directly against SQLite. There is no repository or DAO interface, making it difficult to swap storage backends or add caching. | Low | `config_service.py`, `bot_service.py:68-71` |
| 7.6 | **`BotRunError` defined in `sonarft_manager.py` but never imported by the API** — `sonarft_manager.py:155` references `BotRunError` in `run_bot()` but the exception class is defined at the bottom of the same file and is not re-exported. If `run_bot` raises it, the API's generic 500 handler catches it with no specific message. | Low | `sonarft_manager.py:155,175` |
| 7.7 | **`_BOT_LOGGER_NAME` hardcoded to `"src.services.bot_service"`** — the WsLogHandler attaches to this logger name. If the API package is ever renamed or restructured, log streaming silently breaks with no error. | Low | `websocket/manager.py:30` |
| 7.8 | **`HealthResponse.version` is hardcoded `"1.0.0"`** — not derived from `Settings.api_version`, so the health endpoint can report a stale version after a version bump. | Low | `models/schemas.py:130`, `core/config.py:9` |

---

## 8. Recommendations (Prioritised)

### P1 — High impact, low effort

**8.1 Fix `HealthResponse.version` to use `Settings.api_version`**

```python
# schemas.py
class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = Field(default_factory=lambda: get_settings().api_version)
```

**8.2 Move the WebSocket endpoint into a dedicated router**

Create `src/api/v1/endpoints/websocket.py` with an `APIRouter` and register it in `create_app()`. This makes the endpoint discoverable, testable, and consistent with the rest of the routing layer.

**8.3 Derive `_BOT_LOGGER_NAME` from the module path rather than hardcoding it**

```python
# websocket/manager.py
import src.services.bot_service as _bs_module
_BOT_LOGGER_NAME = _bs_module.__name__
```

### P2 — Medium impact, moderate effort

**8.4 Eliminate the legacy/canonical duplication**

The deprecated `bots.py` and `config.py` routers share all logic with `clients.py`. Extract the shared handler functions into the service layer (already partially done) and have both routers call the same service methods — which they already do. The remaining duplication is the endpoint function bodies themselves. Consider a thin adapter pattern:

```python
# bots.py — legacy shim
@router.get("")
async def list_bots(client_id: ClientId, service: BotSvc) -> BotListResponse:
    return BotListResponse(botids=service.get_botids(client_id))
```
This is already the case — the real fix is to document a deprecation timeline and remove the legacy routers in a future major version.

**8.5 Add a `TicketStore` interface backed by Redis for multi-worker deployments**

For single-worker deployments the current in-memory store is correct. Add a `RedisTicketStore` implementation behind an abstract `AbstractTicketStore` protocol, selectable via a `TICKET_STORE_BACKEND` env var. This unblocks horizontal scaling without changing the endpoint contract.

### P3 — Low impact / long-term

**8.6 Introduce a persistence abstraction layer**

Define `AbstractConfigRepository` and `AbstractHistoryRepository` protocols. `ConfigService` and `BotService` depend on the protocol, not the concrete file/SQLite implementation. This enables unit testing without touching the filesystem and makes future storage migrations straightforward.

**8.7 Consider process isolation for the bot engine**

For production deployments handling real money, running the bot engine in a separate process (via `asyncio.subprocess` or a message queue) would isolate API availability from bot crashes. This is a significant architectural change but directly addresses concern 7.1.

---

## Related Prompts

- [Prompt 02: API Endpoints Design](../endpoints/02-api-endpoints-design.md) — Detailed endpoint review
- [Prompt 03: Data Models & Validation](../models/03-data-models-validation.md) — Schema design
- [Prompt 04: Authentication & Security](../security/04-authentication-security.md) — Security deep-dive
- [Prompt 05: WebSocket & Real-time](../websocket/05-websocket-realtime.md) — WS lifecycle

---

_Part of the SonarFT API Code Review Prompt Suite — Prompt 01_
