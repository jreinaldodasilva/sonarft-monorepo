# API Architecture & Project Structure Review

**Prompt ID:** 01-API-ARCH  
**Package:** `packages/api`  
**Output:** `docs/architecture/01-api-architecture.md`  
**Reviewed:** July 2025 | **Updated:** July 2025 (post-implementation)  
**Status:** Complete — all findings resolved

---

## Executive Summary

The SonarFT API is a well-structured FastAPI application with clear separation of concerns across five layers: endpoints, services, models, websocket, and core. All architectural issues identified in the original review have been resolved. The `WebSocketManager` is now managed through `app.state` via the lifespan pattern. Endpoint duplication between `bots.py` and `clients.py` has been eliminated by extracting shared handler functions into `_bot_handlers.py`. The `WsFanOutHandler` replaces the per-client `WsLogHandler` pattern, reducing log record formatting from O(N) to O(1). The data isolation vulnerability (`get_orders`/`get_trades` missing ownership checks) has been fixed.

---

## Architecture Diagram

```mermaid
graph TD
    subgraph "packages/web (React + TypeScript)"
        FE[Frontend Client]
    end

    subgraph "packages/api (FastAPI)"
        subgraph "Middleware Stack"
            GZ[GZipMiddleware]
            RL[SlowAPIMiddleware]
            SH[SecurityHeadersMiddleware]
            AL[AccessLogMiddleware]
            RI[RequestIdMiddleware]
            CO[CORSMiddleware]
        end

        subgraph "Endpoints — api/v1/endpoints/"
            HE[health.py\nGET /health\nGET /health/ready]
            CL[clients.py\nCanonical /clients/{id}/bots]
            BO[bots.py\nLegacy /bots — DEPRECATED]
            CF[config.py\nLegacy /parameters — DEPRECATED]
            WS[websocket.py\nWS /ws/{client_id}]
            TK[ws_ticket.py\nPOST /ws/ticket]
        end

        subgraph "Shared Helpers — api/v1/"
            BH[_bot_handlers.py\nShared endpoint logic]
            LG[_legacy.py\nSunset date + headers]
        end

        subgraph "Core — core/"
            SEC[security.py\nJWT + static token]
            CFG[config.py\nSettings + ID_PATTERN]
            ERR[errors.py\nExceptions + handlers\n+ error codes]
            LIM[limiter.py\nslowapi Limiter]
            CTX[context.py\nrequest_id ContextVar]
        end

        subgraph "Services — services/"
            BS[BotService\nbot_service.py]
            CS[ConfigService\nconfig_service.py]
        end

        subgraph "Models — models/"
            SCH[schemas.py\nPydantic v2 models\n+ BotStatusResponse]
        end

        subgraph "WebSocket — websocket/"
            WM[WebSocketManager\nmanager.py\n+ WsFanOutHandler]
            TS[TicketStore\ntickets.py]
        end
    end

    subgraph "packages/bot (Python)"
        BM[BotManager\nsonarft_manager.py]
        SB[SonarftBot\nsonarft_bot.py]
        SH2[SonarftHelpers\nsonarft_helpers.py]
    end

    FE -->|HTTP REST| CO
    FE -->|WebSocket| CO
    CO --> RI --> AL --> SH --> RL --> GZ
    GZ --> CL & BO & CF & HE & WS & TK
    CL & BO --> BH --> BS
    CF --> CS
    WS --> WM
    TK --> TS
    BS --> BM --> SB
    BS --> SH2
    WM -->|WsFanOutHandler| BM
```

---

## Module Organization Table

| Module | Path | Responsibility | Status |
|---|---|---|---|
| `main.py` | `src/main.py` | App factory, middleware, lifespan, logging, recovery | ✅ Updated |
| `health.py` | `src/api/v1/endpoints/health.py` | `GET /health`, `GET /health/ready` | ✅ Updated |
| `clients.py` | `src/api/v1/endpoints/clients.py` | Canonical client-scoped endpoints | ✅ Refactored |
| `bots.py` | `src/api/v1/endpoints/bots.py` | Legacy bot endpoints (deprecated) | ✅ Refactored |
| `config.py` | `src/api/v1/endpoints/config.py` | Legacy config endpoints (deprecated) | ✅ Refactored |
| `websocket.py` | `src/api/v1/endpoints/websocket.py` | WebSocket entry point | ✅ Fixed (no singleton) |
| `ws_ticket.py` | `src/api/v1/endpoints/ws_ticket.py` | `POST /ws/ticket` | ✅ Updated |
| `_bot_handlers.py` | `src/api/v1/_bot_handlers.py` | **New** — shared bot lifecycle handlers | ✅ New |
| `_legacy.py` | `src/api/v1/_legacy.py` | **New** — shared sunset date + deprecation headers | ✅ New |
| `config.py` | `src/core/config.py` | Settings, `ID_PATTERN` | ✅ Unchanged |
| `errors.py` | `src/core/errors.py` | Domain exceptions + handlers + **error codes** | ✅ Updated |
| `security.py` | `src/core/security.py` | JWT (JWKS auto-refresh), static token | ✅ Updated |
| `limiter.py` | `src/core/limiter.py` | slowapi Limiter | ✅ Unchanged |
| `context.py` | `src/core/context.py` | `request_id_var` ContextVar | ✅ Unchanged |
| `bot_service.py` | `src/services/bot_service.py` | Bot lifecycle + ownership checks + status | ✅ Updated |
| `config_service.py` | `src/services/config_service.py` | JSON config read/write/cache | ✅ Unchanged |
| `schemas.py` | `src/models/schemas.py` | Pydantic v2 models + `BotStatusResponse` | ✅ Updated |
| `manager.py` | `src/websocket/manager.py` | `WebSocketManager` + `WsFanOutHandler` | ✅ Updated |
| `tickets.py` | `src/websocket/tickets.py` | `TicketStore` + `TICKET_TTL_SECONDS` | ✅ Updated |

---

## Resolved Findings

| ID | Finding | Resolution |
|---|---|---|
| H1 | `get_orders`/`get_trades` missing ownership check | `_bot_owned_by()` guard added to both methods in `bot_service.py` |
| H2 | WS `run`/`stop`/`remove` missing ownership check | `botid not in bot_manager.get_botids(client_id)` guard added to `_receive_loop` |
| H3 | Logger injection breaks WS log streaming | `BotManager` now receives `logging.getLogger("sonarft.api_bridge")` |
| H4 | `create_bot()` blocks event loop | `run_in_executor` offloads ccxt market load to thread pool |
| H5 | `WebSocketManager` module-level singleton | Moved to `app.state.ws_manager` via `_lifespan` |
| H6 | `DATA_DIR` default creates split config directory | Startup warning added; `.env.example` updated |
| M1 | `bots.py`/`clients.py` endpoint duplication | `_bot_handlers.py` extracted — 14 duplicate handlers → 7 shared functions |
| M2 | `_deprecation_headers` defined twice | `_legacy.py` created as single source of truth |
| M3 | Dead `except BotRunError` | Removed from `sonarft_manager.py` |
| M4 | O(N) log handler overhead | `WsFanOutHandler` replaces per-client handlers — O(1) formatting |
| M5 | No machine-readable error codes | `code` field added to all error responses |
| M6 | No readiness probe | `GET /health/ready` added |
| M7 | JWKS no auto-refresh | `PyJWKClient(cache_jwk_set=True, lifespan=300)` |
| M8 | Open-by-default auth in production | `RuntimeError` raised when `SONARFT_ENV != development` and no auth configured |

---

## Current Architecture Strengths

1. **Clean service abstraction** — `BotService` fully encapsulates `BotManager`. Endpoints never import from `packages/bot` directly. The `sonarft.api_bridge` logger ensures WS log streaming works correctly.

2. **Comprehensive middleware stack** — GZip, rate limiting, security headers (HSTS, CSP, X-Frame-Options), access logging, request ID propagation, and CORS all correctly ordered.

3. **Zero-coupling log streaming** — `WsFanOutHandler` attached once at startup fans out bot log records to all active WebSocket client queues with O(1) formatting overhead.

4. **Shared handler pattern** — `_bot_handlers.py` provides a single implementation of all bot lifecycle operations, consumed by both canonical and legacy routers.

---

## Remaining Open Items

| ID | Item | Phase |
|---|---|---|
| API-002 | Rate-limit response headers (`X-RateLimit-*`) | Deferred — requires `response: Response` param on all endpoints |
| API-003 | Paginated response envelope with `total` count | Phase 4 backlog |
| ARCH-005 | Redis for multi-worker scaling | Spike required |
| DB-005 | PostgreSQL evaluation | Spike required |

---

_Generated by Amazon Q Developer — SonarFT API Code Review Prompt Suite, Prompt 01_  
_Updated post-implementation: Phases 1–4 complete_
