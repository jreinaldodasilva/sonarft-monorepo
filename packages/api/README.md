# sonarft-api

**SonarFT REST API and WebSocket backend** — bot lifecycle management, real-time log streaming, and configuration for the SonarFT trading platform.

`sonarft-api` is the HTTP/WebSocket layer of the SonarFT monorepo. It wraps the `sonarft-bot` trading engine behind a FastAPI service with JWT authentication, rate limiting, and structured observability.

---

## Status

| Metric | Value |
|---|---|
| Python | 3.11+ |
| Tests | 239 passing |
| Coverage threshold | ≥ 75% (CI enforced) |
| Lint | ruff — 0 errors |
| Type check | mypy — 0 errors |
| Security audit | pip-audit — 0 High/Critical |

---

## Architecture

```
create_app() — main.py
  │
  ├── Middleware (outermost → innermost)
  │     GZipMiddleware → SlowAPIMiddleware → SecurityHeadersMiddleware
  │     → AccessLogMiddleware → RequestIdMiddleware → CORSMiddleware
  │
  ├── Routers
  │     /api/v1/health          ← liveness + readiness probes
  │     /api/v1/clients/        ← canonical bot + config endpoints
  │     /api/v1/bots/           ← legacy (deprecated, sunset 2026-01-01)
  │     /api/v1/parameters/     ← legacy (deprecated, sunset 2026-01-01)
  │     /api/v1/ws/ticket       ← JWT → single-use WS ticket
  │     /api/v1/ws/{client_id}  ← WebSocket stream
  │
  ├── Services (on app.state)
  │     BotService      ← wraps BotManager from packages/bot
  │     ConfigService   ← reads/writes sonarftdata/config/*.json
  │     WebSocketManager ← per-client queues + WsFanOutHandler
  │
  └── Exception handlers
        BotNotFoundError → 404 + code: BOT_NOT_FOUND
        BotLimitExceededError → 429 + code: BOT_LIMIT_EXCEEDED
        ConfigNotFoundError → 404 + code: CONFIG_NOT_FOUND
        HTTPException → status + code
        Exception → 500 + code: INTERNAL_ERROR
```

### Module index

| Module | Responsibility |
|---|---|
| `src/main.py` | App factory, middleware stack, lifespan handler |
| `src/core/config.py` | `Settings` (pydantic-settings), `ID_PATTERN`, `get_settings()` |
| `src/core/errors.py` | Domain exceptions, async handlers, machine-readable error codes |
| `src/core/security.py` | JWT (Netlify JWKS, auto-refresh), static token, `require_auth`, `get_client_id` |
| `src/core/limiter.py` | slowapi `Limiter` singleton (200 req/min default) |
| `src/core/context.py` | `request_id_var` ContextVar |
| `src/api/v1/_bot_handlers.py` | Shared bot lifecycle handler functions (used by both canonical and legacy routers) |
| `src/api/v1/_legacy.py` | `LEGACY_SUNSET_DATE`, `add_deprecation_headers()` |
| `src/api/v1/endpoints/clients.py` | Canonical `/clients/{id}/bots` routes |
| `src/api/v1/endpoints/bots.py` | Legacy `/bots?client_id=` routes (deprecated) |
| `src/api/v1/endpoints/config.py` | Legacy `/parameters`, `/indicators` routes (deprecated) |
| `src/api/v1/endpoints/health.py` | `GET /health`, `GET /health/ready` |
| `src/api/v1/endpoints/websocket.py` | WebSocket endpoint |
| `src/api/v1/endpoints/ws_ticket.py` | `POST /ws/ticket` |
| `src/services/bot_service.py` | `BotService` — bot lifecycle, ownership checks, status |
| `src/services/config_service.py` | `ConfigService` — atomic JSON read/write, mtime cache |
| `src/models/schemas.py` | All Pydantic v2 request/response models |
| `src/websocket/manager.py` | `WebSocketManager`, `WsFanOutHandler`, `WsLogHandler` |
| `src/websocket/tickets.py` | `TicketStore` — single-use WS auth tickets |

---

## Quick Start

### Prerequisites

- Python 3.11+
- `packages/bot` installed as an editable package

### Install

```bash
# From the monorepo root (recommended)
make setup

# Or manually
pip install -e packages/bot
pip install -r packages/api/requirements.txt
```

### Configure

```bash
cp packages/api/.env.example packages/api/.env
# Edit .env — key settings:
#   DATA_DIR=../bot/sonarftdata   ← must point to bot's sonarftdata
#   NETLIFY_SITE_URL=             ← or SONARFT_API_TOKEN= for static token auth
#   CORS_ORIGINS=http://localhost:5173
```

### Run

```bash
# Development (hot reload)
cd packages/api
uvicorn src.main:app --reload

# Or via Makefile
make dev-api
```

Services:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

---

## API Reference

### Canonical endpoints (use these)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/health` | None | Liveness probe |
| GET | `/api/v1/health/ready` | None | Readiness probe — 503 if services not initialised |
| GET | `/api/v1/clients/{id}/bots` | ✅ | List bot IDs for a client |
| POST | `/api/v1/clients/{id}/bots` | ✅ | Create a new bot (returns `Location` header) |
| POST | `/api/v1/clients/{id}/bots/{botid}/run` | ✅ | Start a bot |
| POST | `/api/v1/clients/{id}/bots/{botid}/stop` | ✅ | Pause a bot |
| DELETE | `/api/v1/clients/{id}/bots/{botid}` | ✅ | Remove a bot (204 No Content) |
| GET | `/api/v1/clients/{id}/bots/{botid}/status` | ✅ | Bot runtime status (running/halted) |
| GET | `/api/v1/clients/{id}/bots/{botid}/orders` | ✅ | Order history (paginated) |
| GET | `/api/v1/clients/{id}/bots/{botid}/trades` | ✅ | Trade history (paginated) |
| GET | `/api/v1/clients/{id}/parameters` | ✅ | Client trading parameters |
| PUT | `/api/v1/clients/{id}/parameters` | ✅ | Update trading parameters |
| GET | `/api/v1/clients/{id}/parameters/defaults` | ✅ | Default trading parameters |
| GET | `/api/v1/clients/{id}/indicators` | ✅ | Client indicator settings |
| PUT | `/api/v1/clients/{id}/indicators` | ✅ | Update indicator settings |
| GET | `/api/v1/clients/{id}/indicators/defaults` | ✅ | Default indicator settings |
| POST | `/api/v1/ws/ticket` | ✅ | Exchange JWT for a 30s single-use WS ticket |
| WS | `/api/v1/ws/{client_id}?ticket=` | Ticket | Real-time event stream |

### History query parameters

All `/orders` and `/trades` endpoints accept:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | int | 100 | Max records (1–1000) |
| `offset` | int | 0 | Records to skip |
| `from_ts` | str | — | ISO 8601 start timestamp (e.g. `2025-01-01T00:00:00`) |
| `to_ts` | str | — | ISO 8601 end timestamp |

### Error response format

All errors include a machine-readable `code` field:

```json
{
  "detail": "Bot not found: bot-abc",
  "code": "BOT_NOT_FOUND",
  "request_id": "3f2a1b4c-..."
}
```

| Code | HTTP | Meaning |
|---|---|---|
| `BOT_NOT_FOUND` | 404 | Bot does not exist or belongs to another client |
| `BOT_LIMIT_EXCEEDED` | 429 | Client has reached `MAX_BOTS_PER_CLIENT` |
| `BOT_CREATION_FAILED` | 500 | Bot engine returned no botid |
| `CONFIG_NOT_FOUND` | 404 | Config file does not exist |
| `CONFIG_WRITE_ERROR` | 500 | Config file could not be written |
| `UNAUTHORIZED` | 401 | Missing or invalid token |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Unhandled exception |

---

## WebSocket Protocol

### Authentication

```
1. POST /api/v1/ws/ticket  (Authorization: Bearer <jwt>)
   → {"ticket": "...", "ttl_seconds": 30}

2. WS /api/v1/ws/{client_id}?ticket=<ticket>
   → {"type": "connected", "client_id": "...", "ts": ...}
```

### Server → client events

| Type | Fields | Trigger |
|---|---|---|
| `connected` | `client_id`, `ts` | On connection |
| `log` | `level`, `message`, `ts` | Bot engine log record |
| `bot_created` | `botid`, `ts` | After `create` command succeeds |
| `bot_removed` | `botid`, `ts` | After `remove` command succeeds |
| `bot_stopped` | `botid`, `ts` | After `stop` command succeeds |
| `order_success` | `ts` | Order filled |
| `trade_success` | `ts` | Trade completed |
| `error` | `message`, `ts` | Command validation failure |
| `ping` | `ts` | Keepalive (every 30s) |

### Client → server commands

```json
{"key": "create"}
{"key": "run",            "botid": "..."}
{"key": "stop",           "botid": "..."}
{"key": "remove",         "botid": "..."}
{"key": "set_simulation", "botid": "...", "value": true}
```

---

## Authentication

Two modes — configure one:

### Netlify Identity JWT (production)

```bash
NETLIFY_SITE_URL=https://your-site.netlify.app
```

- RS256 JWT validated against Netlify JWKS endpoint
- JWKS keys auto-refreshed every 5 minutes
- `client_id` extracted from JWT `sub` claim

### Static token (simple deployments)

```bash
SONARFT_API_TOKEN=your-secret-token
```

- Timing-safe comparison via `hmac.compare_digest()`
- `client_id` must be supplied as a query parameter

### Development mode

Leave both variables empty. All endpoints are publicly accessible. A `WARNING` is logged at startup. Setting `SONARFT_ENV=production` with no auth configured raises `RuntimeError` at startup.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `NETLIFY_SITE_URL` | `""` | Netlify Identity URL for JWT auth |
| `SONARFT_API_TOKEN` | `""` | Static bearer token |
| `SONARFT_ENV` | `development` | Set to `production` to enforce auth at startup |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated allowed origins |
| `MAX_BOTS_PER_CLIENT` | `5` | Max concurrent bots per client |
| `DATA_DIR` | `sonarftdata` | **Must be `../bot/sonarftdata`** to share config with the bot engine |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `LOG_FILE` | `logs/sonarft.log` | Rotating log file (empty = disabled) |
| `METRICS_LOG_FILE` | `logs/sonarft_metrics.jsonl` | Structured JSON metrics (empty = disabled) |
| `JSON_LOG_FILE` | `""` | Optional structured JSON log for aggregation tools |

---

## Rate Limits

All limits are per source IP via slowapi.

| Endpoint group | Limit |
|---|---|
| GET list/history/status | 60/min |
| POST create bot | 10/min |
| POST run/stop/remove | 20/min |
| PUT config update | 30/min |
| POST ws/ticket | 30/min |
| Global default | 200/min |

---

## Testing

```bash
# Run all tests
pytest tests/ -q

# Run with coverage
pytest tests/ -q --cov=src --cov-report=term-missing --cov-fail-under=75

# Run load tests (requires locust)
pip install locust
locust -f tests/load/locustfile.py --host http://localhost:8000
```

### Test structure

```
tests/
├── conftest.py                    # Shared fixtures and data factories
├── unit/
│   ├── test_smoke.py              # App startup, health, auth warning
│   ├── test_endpoints.py          # Legacy REST endpoints
│   ├── test_clients.py            # Canonical /clients/ endpoints
│   ├── test_security.py           # Auth modes, input validation
│   ├── test_tickets.py            # TicketStore unit tests
│   └── test_websocket.py          # WS lifecycle, commands, log streaming
├── integration/
│   ├── test_config_service.py     # ConfigService against real filesystem
│   ├── test_log_streaming.py      # WsLogHandler E2E log delivery
│   └── test_bot_service_integration.py  # Logger name + DATA_DIR contracts
└── load/
    └── locustfile.py              # Locust load test suite
```

---

## Security

- **JWT auth** — RS256 via Netlify JWKS with 5-minute auto-refresh
- **Static token** — `hmac.compare_digest()` timing-safe comparison
- **WS auth** — single-use tickets (32-byte random, 30s TTL) keep JWT out of server logs
- **Ownership isolation** — all bot operations verify `botid` belongs to the requesting `client_id`
- **Security headers** — HSTS, CSP (`default-src 'none'`), X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- **Input validation** — `ID_PATTERN` regex on all IDs; config key regex; ISO 8601 validation on timestamp params
- **SQL injection** — parameterised queries throughout; table-name allowlist
- **Path traversal** — `ID_PATTERN` regex + `Path.resolve()` containment check on config paths

---

## Logging & Observability

### Log files

| File | Format | Contents |
|---|---|---|
| `logs/sonarft.log` | Plain text | All application logs with `[request_id]` |
| `logs/sonarft_metrics.jsonl` | JSON lines | Structured trading metrics (signals, orders, trades, risk events) |
| `logs/sonarft.jsonl` | JSON lines | Optional — set `JSON_LOG_FILE=logs/sonarft.jsonl` |

### Request correlation

Every HTTP request gets an `X-Request-ID` header (generated or propagated). The ID appears in all log lines for that request and in all error response bodies, enabling log correlation without inspecting response headers.

### Bot status endpoint

```
GET /api/v1/clients/{id}/bots/{botid}/status
→ {"botid": "...", "registered": true, "running": true, "halted": false}
```

`halted: true` means the circuit breaker has tripped after consecutive failures. Resume by calling `POST .../run`.

---

## Docker

```bash
# Build
docker build -t sonarft-api packages/api

# Run (with bot package)
docker run -p 8000:8000 \
  -e DATA_DIR=/app/sonarftdata \
  -e SONARFT_API_TOKEN=your-token \
  -e SONARFT_ENV=production \
  -v $(pwd)/packages/bot/sonarftdata:/app/sonarftdata \
  sonarft-api
```

See `infra/docker-compose.yml` for the full three-service deployment (bot + api + web).

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/architecture/01-api-architecture.md`](docs/architecture/01-api-architecture.md) | Module structure, integration points, resolved findings |
| [`docs/endpoints/02-api-endpoints-design.md`](docs/endpoints/02-api-endpoints-design.md) | Full endpoint reference, REST design assessment |
| [`docs/models/03-data-models-validation.md`](docs/models/03-data-models-validation.md) | Pydantic model inventory, cross-package alignment |
| [`docs/security/04-authentication-security.md`](docs/security/04-authentication-security.md) | Auth mechanisms, vulnerability assessment |
| [`docs/websocket/05-websocket-realtime.md`](docs/websocket/05-websocket-realtime.md) | WS protocol, connection lifecycle, log streaming |
| [`docs/error-handling/06-error-handling-logging.md`](docs/error-handling/06-error-handling-logging.md) | Exception hierarchy, logging strategy, error codes |
| [`docs/database/07-database-persistence.md`](docs/database/07-database-persistence.md) | SQLite schema, migrations, backup strategy |
| [`docs/performance/08-performance-optimization.md`](docs/performance/08-performance-optimization.md) | Bottleneck analysis, async model, scaling limits |
| [`docs/testing/09-testing-quality.md`](docs/testing/09-testing-quality.md) | Test coverage, strategy, CI pipeline |
| [`docs/code-quality/10-code-quality-python.md`](docs/code-quality/10-code-quality-python.md) | Style, naming, complexity, duplication |
| [`docs/consolidation/11-api-gaps.md`](docs/consolidation/11-api-gaps.md) | Executive summary, risk scores, go/no-go assessment |
| [`docs/roadmap/12-api-implementation.md`](docs/roadmap/12-api-implementation.md) | 40-item implementation roadmap with completion status |

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.135.3 | Web framework |
| `uvicorn[standard]` | 0.44.0 | ASGI server (uvloop + httptools) |
| `pydantic` | ≥2.0.0 | Data validation |
| `pydantic-settings` | ≥2.0.0 | Settings from environment |
| `PyJWT[crypto]` | ≥2.7.0 | JWT validation (RS256) |
| `orjson` | latest | Fast JSON serialisation |
| `slowapi` | ≥0.1.9 | Rate limiting |
| `sonarft-bot` | local editable | Trading engine |
