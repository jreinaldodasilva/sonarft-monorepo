# SonarFT Monorepo

**System Oscillator for Navigation and Ranging in Financial Trade**

A three-layer monorepo separating the trading engine, API backend, and React frontend into independent, deployable packages.

---

## Architecture

```
sonarft-monorepo/
├── packages/
│   ├── bot/        # Python — core trading engine (indicators, execution, CCXT)
│   ├── api/        # Python — FastAPI REST + WebSocket backend
│   └── web/        # TypeScript — React 18 + Vite frontend
├── shared/
│   └── types/      # api.ts — single source of truth for API contract
├── infra/
│   ├── docker-compose.yml      # Production orchestration
│   └── docker-compose.dev.yml  # Development overrides (hot reload)
├── .github/
│   └── workflows/ci.yml        # CI: web tests + npm audit on push/PR
├── Makefile                    # Top-level dev commands
└── docs/                       # Developer guide, backtesting guide
```

### Layer responsibilities

| Package | Language | Role |
|---|---|---|
| `packages/bot` | Python 3.11 | Pure trading engine — no HTTP, no auth. Importable as `sonarft-bot`. |
| `packages/api` | Python 3.11 | FastAPI service — REST endpoints, WebSocket, JWT auth, CORS, rate limiting. |
| `packages/web` | TypeScript | React 18 + Vite frontend. Talks only to `packages/api`. |
| `shared/types` | TypeScript | API contract types shared between `api` (Pydantic) and `web` (TypeScript). |

### Technology stack

| Layer | Key technologies |
|---|---|
| Bot engine | Python 3.11, pandas 3.0, pandas-ta 0.4, ccxt 4.5, asyncio |
| API server | FastAPI 0.135, uvicorn 0.44, Pydantic v2, PyJWT, slowapi |
| Web frontend | React 18, TypeScript 5, Vite 8, Recharts, Netlify Identity |
| Testing | pytest (bot + api), Vitest + RTL + MSW v2 (web) |
| CI | GitHub Actions — web tests + `npm audit --audit-level=high` |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20 LTS
- Docker + Docker Compose (for containerised deployment)

### Option 1 — Manual (recommended for development)

```bash
# 1. First-time setup (creates .venv, installs all deps)
make setup

# 2. Copy and configure environment files
cp packages/api/.env.example packages/api/.env
# Edit packages/api/.env — leave NETLIFY_SITE_URL and SONARFT_API_TOKEN empty for dev

# 3. Terminal 1: start the API server
source .venv/bin/activate
make dev-api

# 4. Terminal 2: start the web dev server
make dev-web
```

Services:
- Web: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/api/v1/docs

> **Dev auth bypass:** `packages/web/.env.development` has `VITE_DEV_AUTH_BYPASS=true`
> pre-configured — the web app auto-injects a dev user so you can use the trading
> interface without setting up Netlify Identity.

### Option 2 — Docker Compose

```bash
# Copy environment files
cp packages/api/.env.example packages/api/.env
cp packages/web/.env.development.example packages/web/.env.development

# Start all services with hot reload
make dev
```

---

## Development Commands

```bash
make help          # Show all commands
make setup         # First-time setup: create venv, install all deps
make install       # Re-install all dependencies (after pulling changes)
make dev-api       # Start API server with hot reload on :8000
make dev-web       # Start web dev server with HMR on :5173
make dev           # Start all services via Docker Compose
make test          # Run all tests (bot + api + web)
make test-bot      # Run bot tests only (pytest)
make test-api      # Run API tests only (pytest)
make test-web      # Run web tests only (Vitest — 110/110 passing)
make lint          # Lint all packages
make build         # Build all Docker images
make build-web     # Build web production bundle
make clean         # Remove build artifacts and caches
make logs          # Tail Docker Compose logs
```

---

## API Reference

Base URL: `http://localhost:8000/api/v1`  
Interactive docs: `http://localhost:8000/api/v1/docs`

### Endpoints

#### Canonical paths (preferred for new integrations)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health check |
| `GET` | `/clients/{client_id}/bots` | List bot IDs |
| `POST` | `/clients/{client_id}/bots` | Create new bot |
| `POST` | `/clients/{client_id}/bots/{botid}/run` | Start bot |
| `POST` | `/clients/{client_id}/bots/{botid}/stop` | Stop bot |
| `DELETE` | `/clients/{client_id}/bots/{botid}` | Remove bot |
| `GET` | `/clients/{client_id}/bots/{botid}/orders` | Order history |
| `GET` | `/clients/{client_id}/bots/{botid}/trades` | Trade history |
| `GET` | `/clients/{client_id}/parameters` | Get parameters |
| `PUT` | `/clients/{client_id}/parameters` | Update parameters |
| `GET` | `/clients/{client_id}/indicators` | Get indicators |
| `PUT` | `/clients/{client_id}/indicators` | Update indicators |
| `POST` | `/ws/ticket` | Get single-use WebSocket ticket |
| `WS` | `/ws/{clientId}?ticket=` | Real-time stream |

#### Legacy paths (deprecated, still functional)

| Method | Path | Description |
|---|---|---|
| `GET` | `/bots?client_id=` | List bot IDs |
| `POST` | `/bots?client_id=` | Create new bot |
| `GET` | `/parameters/defaults` | Default parameters |
| `GET` | `/parameters?client_id=` | Client parameters |
| `PUT` | `/parameters?client_id=` | Update parameters |
| `GET` | `/indicators/defaults` | Default indicators |
| `GET` | `/indicators?client_id=` | Client indicators |
| `PUT` | `/indicators?client_id=` | Update indicators |

### Authentication

Set `NETLIFY_SITE_URL` for Netlify Identity JWT validation, or `SONARFT_API_TOKEN`
for static token auth. If neither is set, auth is disabled (development only).

**WebSocket authentication** uses a single-use ticket to keep the JWT out of
server logs:

```bash
# 1. Get a ticket (30-second TTL)
curl -X POST -H "Authorization: Bearer <jwt>" \
     http://localhost:8000/api/v1/ws/ticket
# → {"ticket":"<opaque>","ttl_seconds":30}

# 2. Connect with the ticket
ws://localhost:8000/api/v1/ws/{clientId}?ticket=<ticket>
```

### WebSocket events

**Client → Server:**
```json
{ "type": "keypress", "key": "create" }
{ "type": "keypress", "key": "run",    "botid": "bot_abc" }
{ "type": "keypress", "key": "remove", "botid": "bot_abc" }
{ "type": "keypress", "key": "set_simulation", "botid": "bot_abc", "value": false }
```

**Server → Client:**
```json
{ "type": "connected",     "client_id": "...", "ts": 0 }
{ "type": "log",           "level": "INFO", "message": "...", "ts": 0 }
{ "type": "bot_created",   "botid": "bot_abc", "ts": 0 }
{ "type": "bot_removed",   "botid": "bot_abc", "ts": 0 }
{ "type": "order_success",                      "ts": 0 }
{ "type": "trade_success",                      "ts": 0 }
{ "type": "error",         "message": "...",    "ts": 0 }
{ "type": "ping",                               "ts": 0 }
```

All event and command types are defined in `shared/types/api.ts`.

---

## Environment Variables

### `packages/api/.env`

| Variable | Default | Description |
|---|---|---|
| `NETLIFY_SITE_URL` | — | Netlify site URL for JWT validation |
| `SONARFT_API_TOKEN` | — | Static token fallback |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Allowed CORS origins |
| `MAX_BOTS_PER_CLIENT` | `5` | Max concurrent bots per client |
| `DATA_DIR` | `sonarftdata` | Path to bot data directory |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

### `packages/web/.env.development`

| Variable | Default | Description |
|---|---|---|
| `VITE_DEV_AUTH_BYPASS` | `true` | Skip Netlify Identity — auto-injects dev user |
| `VITE_API_URL` | `http://localhost:8000/api/v1` | API base URL |
| `VITE_WS_URL` | `ws://localhost:8000/api/v1/ws` | WebSocket base URL |
| `VITE_VITALS_URL` | — | Web Vitals reporting endpoint (optional) |
| `VITE_IDLE_TIMEOUT_MS` | `1800000` | Session idle timeout (ms) |

---

## Web Frontend

The React frontend (`packages/web`) is built with:

- **React 18** — functional components, hooks throughout
- **TypeScript 5** — strict mode, `noUnusedLocals`, `noUnusedParameters`
- **Vite 8** — fast builds with vendor chunk splitting
- **Recharts** — P&L chart visualization
- **Netlify Identity** — JWT authentication
- **ESLint v9** flat config with `react-hooks`, `jsx-a11y`, `@typescript-eslint`

### Key architectural decisions

**WebSocket ticket auth** — the frontend exchanges its JWT for a short-lived
opaque ticket before opening the WebSocket connection, keeping the JWT out of
server access logs and browser history.

**Bot state machine** — bot lifecycle is managed with `useReducer` with explicit
transitions: `idle → creating → running → removing → idle`.

**Vendor chunk splitting** — Recharts, Netlify Identity, and React are split into
separate cached chunks. App code chunks are tiny (AuthProvider: 0.6KB gzip,
Crypto page: 6.8KB gzip).

**RAF log batching** — WebSocket log messages accumulate in a ref buffer and
flush to React state at most 60 times/second via `requestAnimationFrame`,
preventing GC pressure at high message frequency.

### Production security

The nginx configuration (`packages/web/nginx.conf`) includes:
- `gzip` compression (3× smaller downloads)
- `X-Frame-Options: DENY` (clickjacking protection)
- `Strict-Transport-Security` (HSTS)
- `Content-Security-Policy` as an HTTP header (`frame-ancestors 'none'` is
  effective only as a header, not a `<meta>` tag)
- `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`

---

## Shared Types

`shared/types/api.ts` is the single source of truth for the API contract.
It must stay in sync with `packages/api/src/models/schemas.py`.

```typescript
// Key types defined in shared/types/api.ts:
TradeRecord          // Full trade record including fee fields
ParametersConfig     // Exchange + symbol selections
IndicatorsConfig     // Period + oscillator + moving average selections
WsTicketResponse     // { ticket, ttl_seconds }
WsEvent              // Union of all server→client event types
WsCommand            // Union of all client→server command types
```

---

## 📚 Code Review Documentation

Comprehensive AI-assisted code review documents for the web package, produced
after a full 10-prompt review cycle:

| Document | Contents |
|---|---|
| [`docs/architecture/structure.md`](packages/web/docs/architecture/structure.md) | Component hierarchy, data flow, module dependencies |
| [`docs/api-integration/sonarft-integration.md`](packages/web/docs/api-integration/sonarft-integration.md) | REST + WebSocket integration patterns |
| [`docs/state-management/data-flow.md`](packages/web/docs/state-management/data-flow.md) | State architecture, useReducer machine, RAF batching |
| [`docs/components/design-patterns.md`](packages/web/docs/components/design-patterns.md) | Component design, ConfigCheckboxPanel, React.memo |
| [`docs/real-time/websocket-integration.md`](packages/web/docs/real-time/websocket-integration.md) | WebSocket lifecycle, ticket auth, event handling |
| [`docs/security/auth-and-security.md`](packages/web/docs/security/auth-and-security.md) | Security posture, CVE status, nginx config |
| [`docs/ux/trading-interface.md`](packages/web/docs/ux/trading-interface.md) | UX/accessibility findings and fixes |
| [`docs/performance/optimization.md`](packages/web/docs/performance/optimization.md) | Bundle sizes, vendor splitting, rendering performance |
| [`docs/testing/test-strategy.md`](packages/web/docs/testing/test-strategy.md) | Test suite, coverage, CI pipeline |
| [`docs/code-quality/code-quality.md`](packages/web/docs/code-quality/code-quality.md) | ESLint, TypeScript strictness, metrics |
| [`docs/code-quality/consolidation.md`](packages/web/docs/code-quality/consolidation.md) | Executive summary — overall 8.5/10, production-ready |
| [`docs/code-quality/roadmap.md`](packages/web/docs/code-quality/roadmap.md) | Implementation roadmap — all sprints complete ✅ |

### AI-assisted review prompt suites

Each package has a full set of review prompts for ongoing AI-assisted audits:

| Package | Prompts | Focus |
|---|---|---|
| [`packages/bot/docs/prompts/`](packages/bot/docs/prompts/) | 17 prompts | Trading logic, indicators, execution, security |
| [`packages/api/docs/prompts/`](packages/api/docs/prompts/) | 15 prompts | Architecture, endpoints, WebSocket, performance |
| [`packages/web/docs/prompts/`](packages/web/docs/prompts/) | 15 prompts | Components, hooks, styling, integration |

---

## Project Status

### Web package — post-implementation

| Metric | Status |
|---|---|
| Test suite | ✅ 110/110 passing |
| npm audit Critical/High | ✅ 0 |
| ESLint | ✅ 0 errors, 0 warnings |
| WebSocket auth | ✅ Ticket-based (JWT not in URL) |
| Live trading confirmation | ✅ Modal with explicit warning |
| Accessibility (WCAG AA) | ✅ Contrast, aria-live, focus-visible, HTML validity |
| CI pipeline | ✅ GitHub Actions on push/PR |
| Production-ready | ✅ Yes |

### Developer guide

Full setup, workflow, testing, deployment, and API reference:
→ [`docs/developer-guide.md`](docs/developer-guide.md)
