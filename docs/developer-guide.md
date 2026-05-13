# SonarFT Monorepo — Developer Guide

**Version:** 1.2.0  
**Last Updated:** July 2025  
**Repository:** `sonarft-monorepo/`

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Repository Structure](#2-repository-structure)
3. [Environment Setup](#3-environment-setup)
4. [Environment Variables](#4-environment-variables)
5. [Running the Application](#5-running-the-application)
6. [Development Workflow](#6-development-workflow)
7. [Testing](#7-testing)
8. [Building for Production](#8-building-for-production)
9. [Docker Deployment](#9-docker-deployment)
10. [CI/CD Pipeline](#10-cicd-pipeline)
11. [API Reference](#11-api-reference)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Prerequisites

### Required Software

| Tool | Minimum Version | Purpose | Install |
|---|---|---|---|
| Python | 3.11+ | Bot engine + API server | [python.org](https://python.org) |
| Node.js | 20 LTS | Web frontend | [nodejs.org](https://nodejs.org) |
| npm | 10+ | Node package manager | Bundled with Node.js |
| Git | 2.x | Version control | [git-scm.com](https://git-scm.com) |
| Docker | 24+ | Containerised deployment | [docker.com](https://docker.com) |
| Docker Compose | 2.x | Multi-service orchestration | Bundled with Docker Desktop |

### Optional but Recommended

| Tool | Purpose |
|---|---|
| VS Code | IDE with workspace file pre-configured |
| `make` | Run monorepo commands (`make setup`, `make dev-api`, etc.) |
| `curl` | Test API endpoints from the terminal |

### Verify your environment

```bash
python3 --version    # Python 3.11.x or 3.12.x
node --version       # v20.x.x
npm --version        # 10.x.x
docker --version     # Docker version 24.x.x
docker compose version  # Docker Compose version v2.x.x
make --version       # GNU Make 4.x
```

> **Ubuntu / Debian note:** `pip` is not installed as a system command on Ubuntu 24.04.
> The setup process creates a virtual environment and uses `.venv/bin/pip` directly.
> Never run `sudo pip install` — always use the venv.

---

## 2. Repository Structure

```
sonarft-monorepo/
│
├── packages/
│   ├── bot/                    # Python — core trading engine
│   │   ├── sonarft_*.py        # Core modules (indicators, prices, math, etc.)
│   │   ├── trade_processor.py  # Per-symbol price fetch, adjust, profit check
│   │   ├── trade_validator.py  # Liquidity + spread validation
│   │   ├── trade_executor.py   # Async task management for trade execution
│   │   ├── sonarft_metrics.py  # Structured JSON observability (signals, orders, risk)
│   │   ├── config_schemas.py   # Pydantic config schemas
│   │   ├── models.py           # Shared data models (Trade dataclass, etc.)
│   │   ├── sonarftdata/        # Configuration files (JSON)
│   │   ├── tests/              # Bot unit tests
│   │   ├── pyproject.toml      # Package definition (pip-installable as sonarft-bot)
│   │   ├── requirements.txt    # Runtime dependencies
│   │   └── Dockerfile
│   │
│   ├── api/                    # Python — FastAPI REST + WebSocket backend
│   │   ├── src/
│   │   │   ├── api/v1/
│   │   │   │   └── endpoints/  # health.py, bots.py, clients.py, config.py, ws_ticket.py, websocket.py
│   │   │   ├── core/           # config.py, security.py, errors.py, limiter.py, context.py
│   │   │   ├── models/         # schemas.py (Pydantic models)
│   │   │   ├── services/       # bot_service.py, config_service.py
│   │   │   ├── websocket/      # manager.py, tickets.py
│   │   │   └── main.py         # FastAPI app factory
│   │   ├── tests/
│   │   │   ├── integration/
│   │   │   └── unit/
│   │   ├── logs/               # Rotating log files (gitignored)
│   │   ├── requirements.txt
│   │   ├── requirements-test.txt
│   │   ├── pyproject.toml
│   │   ├── .env.example
│   │   └── Dockerfile
│   │
│   └── web/                    # TypeScript — React 18 + Vite frontend
│       ├── src/
│       │   ├── components/     # UI components (Bots, Charts, ConfigCheckboxPanel, …)
│       │   ├── hooks/          # Custom React hooks (useBots, useWebSocket, …)
│       │   ├── pages/          # Route-level pages (Crypto, Home, …)
│       │   ├── utils/          # api.ts, constants.ts, helpers.ts
│       │   └── mocks/          # MSW test handlers and fixtures
│       ├── eslint.config.js    # ESLint v9 flat config
│       ├── nginx.conf          # Production nginx (security headers + gzip + CSP)
│       ├── package.json
│       ├── vite.config.js      # Vite build with vendor chunk splitting
│       ├── tsconfig.json
│       ├── .env.development    # Local dev URLs (gitignored)
│       ├── .env.development.example
│       └── Dockerfile
│
├── shared/
│   └── types/
│       └── api.ts              # Single source of truth for the API contract
│                               # (TypeScript types + WebSocket event/command shapes)
│
├── infra/
│   ├── docker-compose.yml      # Production orchestration
│   └── docker-compose.dev.yml  # Development overrides (hot reload)
│
├── .github/
│   └── workflows/
│       └── ci.yml              # CI: web tests + npm audit on push/PR
│
├── .venv/                      # Python virtual environment (gitignored)
├── Makefile                    # Top-level dev commands
├── sonarft.code-workspace      # VS Code multi-root workspace
└── README.md
```

### Layer responsibilities

```
┌─────────────────────────────────────────────────────┐
│  packages/web  (React + Vite, port 5173 / 3000)     │
│  User interface — talks only to packages/api         │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP REST + WebSocket
                       │ http://localhost:8000/api/v1
┌──────────────────────▼──────────────────────────────┐
│  packages/api  (FastAPI, port 8000)                  │
│  Auth, validation, CORS, rate limiting               │
│  Imports sonarft-bot as a Python library             │
└──────────────────────┬──────────────────────────────┘
                       │ Python import (in-process)
                       │ from sonarft_manager import BotManager
┌──────────────────────▼──────────────────────────────┐
│  packages/bot  (pure Python, no HTTP)                │
│  Trading engine — indicators, execution, CCXT        │
└─────────────────────────────────────────────────────┘
```

> **Key design decision:** `packages/bot` has no HTTP server. It is a pure Python
> library imported by `packages/api`. All HTTP/WebSocket concerns live in `packages/api`.

### shared/types/api.ts — the contract

`shared/types/api.ts` is the single source of truth for the API contract between
`packages/api` (Pydantic schemas) and `packages/web` (TypeScript types). It defines:

- `TradeRecord` — full trade/order record including fee fields
- `ParametersConfig`, `IndicatorsConfig` — config shapes
- `BotListResponse`, `BotCreateResponse`, `MessageResponse`, `HealthResponse`
- `WsTicketResponse` — WebSocket ticket exchange response
- All WebSocket event types (`WsLogEvent`, `WsBotCreatedEvent`, `WsErrorEvent`, …)
- All WebSocket command types (`WsCreateCommand`, `WsRunCommand`, `WsSetSimulationCommand`, …)

Any change to the API contract must be reflected in both this file and
`packages/api/src/models/schemas.py`.

---

## 3. Environment Setup

### 3.1 Clone the repository

```bash
git clone <repository-url> sonarft-monorepo
cd sonarft-monorepo
```

### 3.2 First-time setup (one command)

```bash
make setup
```

This single command:
1. Creates `.venv/` — a Python virtual environment at the monorepo root
2. Upgrades `pip`, `setuptools`, and `wheel` inside the venv
3. Installs `packages/bot` as an editable package (`pip install -e packages/bot`)
4. Installs `packages/api` dependencies (`pip install -r packages/api/requirements.txt`)
5. Installs `packages/web` Node dependencies (`npm ci`)

Expected output:
```
✓ Environment ready. Activate with: source .venv/bin/activate
```

### 3.3 Activate the Python virtual environment

```bash
source .venv/bin/activate
```

Your prompt will change to show `(.venv)`. To deactivate:

```bash
deactivate
```

> **Why one venv for both bot and api?**
> `packages/api` imports `packages/bot` as a Python library at runtime.
> A shared venv means both packages see the same installed dependencies
> with no version conflicts and no need to manage two separate environments.

### 3.4 Verify the installation

```bash
# Python environment
source .venv/bin/activate
python --version                  # Python 3.11.x or later
pip show sonarft-bot              # confirms bot is installed as editable
pip show fastapi                  # confirms API deps are installed

# Confirm the API app loads without errors
cd packages/api
python -c "from src.main import app; print('Routes:', len(app.routes))"
# → Routes: 31
cd ../..

# Node environment
cd packages/web
node --version                    # v20.x.x
ls node_modules/.bin/vite         # confirms Vite is installed
cd ../..
```

### 3.5 VS Code setup

Open the pre-configured workspace file:

```bash
code sonarft.code-workspace
```

This opens all four folders (root, bot, api, web) in the VS Code sidebar and
automatically sets the Python interpreter to `.venv/bin/python`.

Recommended extensions (prompted automatically by VS Code):
- `ms-python.python` — Python language support
- `ms-python.black-formatter` — Python formatting
- `esbenp.prettier-vscode` — TypeScript/JSX formatting (uses `.prettierrc`)
- `dbaeumer.vscode-eslint` — ESLint integration (uses `eslint.config.js`)

### 3.6 Updating dependencies

After pulling changes that modify `requirements.txt` or `package.json`:

```bash
make install-bot    # re-installs bot (picks up pyproject.toml changes)
make install-api    # re-installs API deps
make install-web    # runs npm ci
```

---

## 4. Environment Variables

### 4.1 packages/api — `.env`

```bash
cp packages/api/.env.example packages/api/.env
```

| Variable | Default | Required | Description |
|---|---|---|---|
| `NETLIFY_SITE_URL` | `""` | No* | Netlify site URL for JWT validation |
| `SONARFT_API_TOKEN` | `""` | No* | Static Bearer token fallback |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Yes | Comma-separated allowed frontend origins |
| `MAX_BOTS_PER_CLIENT` | `5` | No | Maximum concurrent bots per client |
| `DATA_DIR` | `sonarftdata` | Yes | Path to bot data directory (relative to `packages/api/`) |
| `LOG_LEVEL` | `INFO` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | `logs/sonarft.log` | No | Rotating plain-text log path (relative to `packages/api/`); set empty to disable |
| `METRICS_LOG_FILE` | `logs/sonarft_metrics.jsonl` | No | Structured JSON metrics log path; set empty to disable |
| `JSON_LOG_FILE` | `""` | No | Optional structured JSON log alongside the plain-text log |

> \* If neither is set, authentication is **disabled** — development only.

**Authentication modes:**

```bash
# Option A — Netlify Identity (production, recommended)
NETLIFY_SITE_URL=https://your-site.netlify.app

# Option B — Static token (non-Netlify deployments)
SONARFT_API_TOKEN=your-secret-token-here

# Option C — No auth (development only)
NETLIFY_SITE_URL=
SONARFT_API_TOKEN=
```

**Minimum development `.env`:**

```bash
NETLIFY_SITE_URL=
SONARFT_API_TOKEN=
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
MAX_BOTS_PER_CLIENT=5
DATA_DIR=../bot/sonarftdata
LOG_LEVEL=INFO
```

### 4.2 packages/web — `.env.development`

```bash
cp packages/web/.env.development.example packages/web/.env.development
```

| Variable | Default | Description |
|---|---|---|
| `VITE_DEV_AUTH_BYPASS` | `"true"` | Skip Netlify Identity — injects a dev user automatically |
| `VITE_API_URL` | `http://localhost:8000/api/v1` | API base URL |
| `VITE_WS_URL` | `ws://localhost:8000/api/v1/ws` | WebSocket base URL |
| `VITE_VITALS_URL` | `""` | Optional Web Vitals reporting endpoint |
| `VITE_IDLE_TIMEOUT_MS` | `1800000` | Session idle timeout in milliseconds (30 min) |

> **Vite env vars:** All variables must be prefixed `VITE_` and accessed via
> `import.meta.env.VITE_*`. The old `REACT_APP_*` prefix is not used.

**Production `.env.production`:**

```bash
VITE_API_URL=https://api.your-domain.com/api/v1
VITE_WS_URL=wss://api.your-domain.com/api/v1/ws
VITE_IDLE_TIMEOUT_MS=1800000
# VITE_DEV_AUTH_BYPASS must NOT be set in production
```

> **Important:** `VITE_*` variables are embedded into the JavaScript bundle at
> build time — they are not runtime environment variables. Rebuild the image
> if the API URL changes.

### 4.3 Docker Compose environment

```bash
# sonarft-monorepo/.env  (create at monorepo root for Docker)
NETLIFY_SITE_URL=https://your-site.netlify.app
SONARFT_API_TOKEN=
CORS_ORIGINS=https://your-frontend.com
MAX_BOTS_PER_CLIENT=5
LOG_LEVEL=INFO
VITE_API_URL=https://api.your-domain.com/api/v1
VITE_WS_URL=wss://api.your-domain.com/api/v1/ws
```

---

## 5. Running the Application

### 5.1 Manual start (recommended for development)

Open two terminal windows from the monorepo root:

**Terminal 1 — API server**

```bash
source .venv/bin/activate
make dev-api
```

Output:
```
INFO:     Started server process [12345]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

The API server starts with `--reload` — it restarts automatically when any
file in `packages/api/src/` changes.

**Terminal 2 — Web dev server**

```bash
make dev-web
```

Output:
```
  VITE v8.x.x  ready in 312 ms

  ➜  Local:   http://localhost:3000/
```

### 5.2 Service URLs

| Service | URL | Notes |
|---|---|---|
| Web frontend | http://localhost:3000 | Vite dev server with HMR |
| API server | http://localhost:8000 | FastAPI with auto-reload |
| API docs (Swagger) | http://localhost:8000/api/v1/docs | Interactive API explorer |
| API docs (ReDoc) | http://localhost:8000/api/v1/redoc | Alternative API docs |
| OpenAPI schema | http://localhost:8000/api/v1/openapi.json | Raw JSON schema |
| Health check | http://localhost:8000/api/v1/health | Returns `{"status":"ok"}` |

### 5.3 Verify everything is working

```bash
# Health check
curl http://localhost:8000/api/v1/health
# → {"status":"ok","version":"1.0.0"}

# List bots (no auth in dev mode)
curl "http://localhost:8000/api/v1/bots?client_id=test_user"
# → {"botids":[]}

# Open the web app
xdg-open http://localhost:3000   # Linux
open http://localhost:3000       # macOS
```

### 5.4 Creating and running a bot (REST)

```bash
# 1. Create a bot
curl -X POST "http://localhost:8000/api/v1/bots?client_id=test_user"
# → {"botid":"bot_abc123"}

# 2. Start the bot
curl -X POST http://localhost:8000/api/v1/bots/bot_abc123/run
# → {"message":"Bot bot_abc123 started."}

# 3. Check history while running
curl http://localhost:8000/api/v1/bots/bot_abc123/trades
curl http://localhost:8000/api/v1/bots/bot_abc123/orders

# 4. Stop the bot
curl -X POST http://localhost:8000/api/v1/bots/bot_abc123/stop

# 5. Remove the bot
curl -X DELETE http://localhost:8000/api/v1/bots/bot_abc123
```

### 5.5 Creating and running a bot (WebSocket)

The web frontend uses WebSocket for bot lifecycle management. To test manually,
connect to `ws://localhost:8000/api/v1/ws/test_user` and send JSON commands:

```json
{ "type": "keypress", "key": "create" }
{ "type": "keypress", "key": "run",    "botid": "bot_abc123" }
{ "type": "keypress", "key": "remove", "botid": "bot_abc123" }
{ "type": "keypress", "key": "set_simulation", "botid": "bot_abc123", "value": false }
```

> **Note:** Bots start in simulation mode by default (`is_simulating_trade = 1`).
> No real orders are placed until simulation is explicitly disabled.

### 5.6 Docker Compose start (all services)

```bash
# Development mode (hot reload)
make dev

# Equivalent to:
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up
```

### 5.7 Stopping services

```bash
# Manual processes — Ctrl+C in each terminal

# Docker Compose
docker-compose -f infra/docker-compose.yml down

# Docker Compose including volumes (resets bot data)
docker-compose -f infra/docker-compose.yml down --volumes
```

---

## 6. Development Workflow

### 6.1 Making changes to packages/bot

The bot package is installed as an **editable package** (`pip install -e`).
Changes to any `sonarft_*.py` or `trade_*.py` file take effect immediately —
no reinstall needed.

```bash
vim packages/bot/sonarft_indicators.py
# The API server (running with --reload) picks up the change automatically.
# For deeper changes (new files, pyproject.toml), restart the API server.
```

### 6.2 Making changes to packages/api

The API server runs with `--reload`. Any change to a file in
`packages/api/src/` triggers an automatic restart within ~1 second.

```bash
vim packages/api/src/api/v1/endpoints/bots.py
# → API restarts automatically
```

### 6.3 Making changes to packages/web

The Vite dev server provides Hot Module Replacement (HMR). Changes to
TypeScript/TSX/CSS files appear in the browser instantly.

```bash
vim packages/web/src/components/Bots/Bots.tsx
# → Browser updates in < 100ms
```

### 6.4 Adding a new API endpoint

1. Create the endpoint in `packages/api/src/api/v1/endpoints/`
2. Add Pydantic request/response models to `packages/api/src/models/schemas.py`
3. Register the router in `packages/api/src/main.py`
4. Update `shared/types/api.ts` with the corresponding TypeScript types
5. Update `packages/web/src/utils/api.ts` to call the new endpoint

**Canonical vs legacy paths:**

The API has two sets of routes:

| Style | Example | Status |
|---|---|---|
| Canonical (path segment) | `GET /clients/{client_id}/bots` | Preferred for new code |
| Legacy (query param) | `GET /bots?client_id=` | Deprecated but functional |

The web frontend currently uses the legacy query-param routes. New integrations
should use the canonical `/clients/{client_id}/…` paths.

### 6.5 Adding a new bot module

1. Create `packages/bot/sonarft_newmodule.py`
2. Add the module name to `[tool.setuptools.py-modules]` in `packages/bot/pyproject.toml`
3. Import it where needed in `packages/api/src/services/bot_service.py`
4. No reinstall needed — editable install picks it up immediately

### 6.6 Updating shared types

When changing the API contract:

1. Update `shared/types/api.ts` with the new TypeScript types
2. Update the corresponding Pydantic models in `packages/api/src/models/schemas.py`
3. Update `packages/web/src/utils/api.ts` to use the new types
4. Run both test suites to confirm nothing is broken

> **Known gap:** There is no automated check that `shared/types/api.ts` stays
> in sync with `packages/api/src/models/schemas.py`. Rely on the test suites
> and manual review during PRs that touch either side of the contract.

### 6.7 WebSocket authentication flow

The web frontend uses a single-use ticket for WebSocket authentication,
keeping the JWT out of server logs and browser history:

```
1. Frontend calls POST /api/v1/ws/ticket (Bearer JWT in header)
2. API returns { ticket: "<32-byte opaque>", ttl_seconds: 30 }
3. Frontend opens WS: ws://localhost:8000/api/v1/ws/{clientId}?ticket=<ticket>
4. Ticket is consumed on first use — cannot be replayed
5. Fallback: if ticket endpoint unavailable (dev mode), uses ?token= directly
```

### 6.8 Makefile quick reference

```bash
make help          # List all available commands with descriptions
make setup         # First-time setup: create venv, install all deps
make install       # Re-install all dependencies (after pulling changes)
make dev-api       # Start API server with hot reload on :8000
make dev-web       # Start web dev server with HMR on :3000
make dev-bot       # Run bot engine directly (for testing)
make dev           # Start all services via Docker Compose
make test          # Run all tests (bot + api + web)
make test-bot      # Run bot tests only
make test-api      # Run API tests only
make test-web      # Run web tests only
make lint          # Lint all packages
make lint-bot      # Lint bot package (ruff)
make lint-api      # Lint API package (ruff)
make lint-web      # Lint web package (ESLint v9 flat config)
make build         # Build all Docker images
make build-web     # Build web production bundle
make clean         # Remove build artifacts and caches
make logs          # Tail Docker Compose logs
```

---

## 7. Testing

### 7.1 Run all tests

```bash
make test
```

Runs `test-bot`, `test-api`, and `test-web` in sequence.

### 7.2 Bot tests (pytest)

```bash
make test-bot

# Or directly:
cd packages/bot
../../.venv/bin/pytest

# Verbose output:
../../.venv/bin/pytest -v

# Specific test file:
../../.venv/bin/pytest tests/test_sonarft_indicators.py

# Specific test:
../../.venv/bin/pytest tests/test_sonarft_math.py::test_calculate_trade
```

Test files are in `packages/bot/tests/`. `pytest.ini` sets `asyncio_mode = auto`
so async tests work without extra decorators.

**Bot package versions:**

| Package | Version | Purpose |
|---|---|---|
| `pandas` | 3.0.2 | Time-series data for indicators |
| `pandas-ta` | 0.4.71b0 | Technical analysis (RSI, MACD, StochRSI, SMA) |
| `ccxt` | 4.5.48 | Multi-exchange REST API |
| `ccxt[pro]` | 4.5.48 | WebSocket exchange connections (ccxtpro) |
| `simple-websocket` | 1.1.0 | WebSocket client fallback |

### 7.3 API tests (pytest)

```bash
make test-api

# Or directly:
cd packages/api
../../.venv/bin/pytest -v

# With coverage (CI threshold: 75%)
../../.venv/bin/pytest --cov=src --cov-report=term-missing --cov-fail-under=75
```

Test files are in `packages/api/tests/` (split into `unit/` and `integration/`).
The API tests use `httpx` and FastAPI's `TestClient`. Test dependencies are in
`requirements-test.txt` — install with `pip install -r packages/api/requirements-test.txt`.

**API package versions:**

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.135.3 | HTTP REST API and WebSocket server |
| `uvicorn[standard]` | 0.44.0 | ASGI server |
| `pydantic` | ≥2.0.0 | Request/response validation |
| `pydantic-settings` | ≥2.0.0 | Environment variable management |
| `PyJWT[crypto]` | ≥2.7.0 | JWT validation (Netlify Identity) |
| `slowapi` | ≥0.1.9 | Rate limiting |
| `orjson` | latest | Fast JSON serialisation (default response class) |
| `aiofiles` | latest | Async file I/O for config and history reads |

### 7.4 Web tests (Vitest)

```bash
make test-web

# Or directly:
cd packages/web
npm test              # run once (CI mode)
npm run test:watch    # watch mode (re-runs on file change)
```

**Current status: 110/110 tests passing.**

The web test suite uses **Vitest** and **React Testing Library**. MSW v2
intercepts all fetch calls so tests never hit a real server.

**Test file inventory:**

| File | What it tests |
|---|---|
| `src/utils/api.test.ts` | All API functions — success, errors, fallbacks, auth headers |
| `src/utils/helpers.test.ts` | `fetchAllOrders`, `fetchAllTrades` |
| `src/hooks/useWebSocket.test.tsx` | WS connection, reconnect backoff, cleanup (socketRef) |
| `src/hooks/useIdleTimeout.test.ts` | Idle timer, activity reset, cleanup |
| `src/hooks/useConfigCheckboxes.test.ts` | 3-tier fallback, cancelled flag, save lifecycle |
| `src/hooks/useBots.test.ts` | All WS events, bot lifecycle, ticket auth, error handling |
| `src/hooks/AuthProvider.test.tsx` | Login/logout events, session restore, cleanup |
| `src/components/PrivateRoute/PrivateRoute.test.tsx` | Auth gate |
| `src/components/ErrorBoundary/ErrorBoundary.test.tsx` | Error fallback, reset |
| `src/components/Bots/TradeHistoryTable.test.tsx` | Table rendering, locale formatting |
| `src/integration/workflows.test.tsx` | Parameters/Indicators full workflows via MSW |
| `src/App.test.tsx` | App smoke tests |

### 7.5 Coverage reports

```bash
# Web coverage
cd packages/web
npm test -- --coverage

# Bot coverage
cd packages/bot
../../.venv/bin/pytest --cov=. --cov-report=html
# → opens htmlcov/index.html
```

### 7.6 MSW (Mock Service Worker) in web tests

The web tests use MSW v2 to intercept all HTTP requests:

```
src/mocks/
├── fixtures.ts    # Typed test data (mockUser, mockOrder, mockTrade, etc.)
├── handlers.ts    # MSW request handlers for all API endpoints
└── server.ts      # MSW server setup for Vitest (Node environment)
```

Server lifecycle in `src/setupTests.ts`:
```typescript
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

Override a handler for a specific test:
```typescript
import { http, HttpResponse } from "msw";
import { server } from "../mocks/server";

it("handles server error", async () => {
    server.use(
        http.put("http://localhost:8000/api/v1/parameters", () =>
            HttpResponse.json({ detail: "Server error" }, { status: 500 })
        )
    );
    // ... test code
});
```

### 7.7 ESLint and formatting

```bash
# Lint web package (ESLint v9 flat config — 0 errors, 0 warnings)
cd packages/web
npx eslint src/

# Format all TypeScript/TSX files
npm run format

# Lint Python (ruff)
cd packages/bot
ruff check .

cd packages/api
ruff check src/
```

The web ESLint config (`eslint.config.js`) enforces:
- `react-hooks/rules-of-hooks: error` — hooks called unconditionally
- `react-hooks/exhaustive-deps: warn` — all effect dependencies declared
- `jsx-a11y` rules — accessibility linting
- `@typescript-eslint/no-unused-vars: warn` — no dead variables

---

## 8. Building for Production

### 8.1 Web production bundle

```bash
make build-web

# Or directly:
cd packages/web
npm run build
```

Output is written to `packages/web/build/`. Vite produces content-hashed
chunks split by vendor and route:

```
build/assets/vendor-react-*.js      161KB │ gzip:  53KB  (React + Router — stable)
build/assets/vendor-netlify-*.js    236KB │ gzip:  73KB  (Netlify Identity — stable)
build/assets/vendor-recharts-*.js   330KB │ gzip:  97KB  (Recharts + deps — stable)
build/assets/Crypto-*.js             20KB │ gzip:   7KB  (trading page — changes often)
build/assets/AuthProvider-*.js        1KB │ gzip: 0.6KB  (auth hook — changes often)
build/assets/index-*.js               6KB │ gzip: 2.4KB  (app shell)
```

Vendor chunks are cached independently of app code — a deployment that only
changes application code does not invalidate the large vendor chunks.

### 8.2 Preview the production build locally

```bash
cd packages/web
npm run preview
# → http://localhost:4173
```

### 8.3 Build all Docker images

```bash
make build

# Or:
docker-compose -f infra/docker-compose.yml build
```

### 8.4 Build arguments for the web image

The web Dockerfile accepts build arguments that bake the API URLs into the
static bundle at build time:

```bash
docker build \
  --build-arg VITE_API_URL=https://api.your-domain.com/api/v1 \
  --build-arg VITE_WS_URL=wss://api.your-domain.com/api/v1/ws \
  -t sonarft-web:latest \
  packages/web/
```

> **Important:** `VITE_*` variables are embedded at build time. Rebuild the
> image if the API URL changes.

### 8.5 Production checklist

Before deploying to production, verify:

- [ ] `NETLIFY_SITE_URL` or `SONARFT_API_TOKEN` is set (auth enabled)
- [ ] `CORS_ORIGINS` lists only your actual frontend domain(s)
- [ ] `VITE_API_URL` uses `https://` and `VITE_WS_URL` uses `wss://`
- [ ] `VITE_DEV_AUTH_BYPASS` is **not** set in production
- [ ] `LOG_LEVEL=INFO` (not `DEBUG`) in production
- [ ] Docker images built with production `VITE_*` build args
- [ ] `bot-data` volume is backed up or persisted externally
- [ ] Health check responds: `GET /api/v1/health` → `{"status":"ok"}`
- [ ] `npm audit --audit-level=high` shows 0 Critical/High CVEs

---

## 9. Docker Deployment

### 9.1 Architecture overview

```
Internet
    │
    ▼
┌─────────────────────────────────────────┐
│  nginx (packages/web, port 3000/80)     │
│  Serves static React bundle             │
│  Security headers + gzip + CSP          │
│  SPA fallback: all routes → index.html  │
└──────────────────┬──────────────────────┘
                   │ API calls (REST + WebSocket)
                   ▼
┌─────────────────────────────────────────┐
│  FastAPI (packages/api, port 8000)      │
│  REST + WebSocket                       │
│  Auth, CORS, rate limiting              │
└──────────────────┬──────────────────────┘
                   │ Python import
                   ▼
┌─────────────────────────────────────────┐
│  sonarft-bot (packages/bot)             │
│  Internal — no exposed port             │
│  Shared volume: bot-data                │
└─────────────────────────────────────────┘
```

### 9.2 nginx security configuration

The production nginx (`packages/web/nginx.conf`) includes:

```nginx
# Compression
gzip on;
gzip_comp_level 6;
gzip_types text/javascript application/javascript text/css application/json;

# Security headers
add_header X-Content-Type-Options  "nosniff"                          always;
add_header X-Frame-Options         "DENY"                             always;
add_header Referrer-Policy         "no-referrer"                      always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Permissions-Policy      "geolocation=(), microphone=()"   always;

# Content Security Policy (as HTTP header — frame-ancestors is effective here)
add_header Content-Security-Policy
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';
     connect-src 'self' https://api.sonarft.com wss://api.sonarft.com
       https://api.coingecko.com https://*.netlify.com https://*.netlify.app;
     frame-ancestors 'none'; base-uri 'self'; form-action 'self';" always;
```

> **Update `connect-src`** when deploying to a different API domain.

### 9.3 Production deployment

**Step 1 — Create the root `.env` file**

```bash
# sonarft-monorepo/.env
NETLIFY_SITE_URL=https://your-site.netlify.app
SONARFT_API_TOKEN=
CORS_ORIGINS=https://your-frontend.com
MAX_BOTS_PER_CLIENT=5
LOG_LEVEL=INFO
VITE_API_URL=https://api.your-domain.com/api/v1
VITE_WS_URL=wss://api.your-domain.com/api/v1/ws
```

**Step 2 — Build and start all services**

```bash
docker-compose -f infra/docker-compose.yml up -d
```

**Step 3 — Verify services are healthy**

```bash
docker-compose -f infra/docker-compose.yml ps
curl http://localhost:8000/api/v1/health
# → {"status":"ok","version":"1.0.0"}
```

### 9.4 Development with Docker Compose

```bash
make dev
# Equivalent to:
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up
```

The dev override mounts source directories as volumes:

| Service | Mount | Effect |
|---|---|---|
| `api` | `packages/api/src` → `/app/src` | uvicorn `--reload` picks up changes |
| `api` | `packages/bot` → `/app/bot` | Bot module changes visible immediately |
| `web` | `packages/web/src` → `/app/src` | Vite HMR serves updated files |

### 9.5 Shared data volume

`packages/bot` and `packages/api` share a Docker volume named `bot-data`
mounted at `/app/sonarftdata` in both containers:

```
sonarftdata/
├── config/                     # Per-client parameters and indicators
│   ├── {client_id}_parameters.json
│   └── {client_id}_indicators.json
├── history/                    # Per-bot trade and order history
│   ├── {botid}_orders.json
│   └── {botid}_trades.json
├── config.json                 # Named configuration sets
├── config_parameters.json      # Default parameter options
├── config_indicators.json      # Default indicator options
├── config_exchanges.json       # Exchange list
├── config_symbols.json         # Trading pairs
└── config_fees.json            # Fee structures
```

> **Persistence:** The `bot-data` volume persists across container restarts.
> To reset: `docker-compose -f infra/docker-compose.yml down --volumes`

### 9.6 Useful Docker commands

```bash
# View running containers
docker-compose -f infra/docker-compose.yml ps

# Tail logs from all services
make logs

# Tail logs from a specific service
docker-compose -f infra/docker-compose.yml logs -f api

# Restart a single service
docker-compose -f infra/docker-compose.yml restart api

# Open a shell in the API container
docker-compose -f infra/docker-compose.yml exec api bash

# Full reset (containers + volumes)
docker-compose -f infra/docker-compose.yml down --volumes --remove-orphans
```

---

## 10. CI/CD Pipeline

### 10.1 Overview

The pipeline is defined in `.github/workflows/ci.yml` and runs on every push
to `main` and `develop`, and on every pull request targeting those branches.

```
Push / PR to main or develop
    │
    ├── test-web
    │     ├── npm ci
    │     ├── npm run lint       (ESLint)
    │     ├── npm test           (Vitest — 110 tests + coverage)
    │     ├── prettier --check   (format check)
    │     └── npm audit --audit-level=critical
    │
    ├── test-bot
    │     ├── pip install -r requirements.txt && pip install -e .
    │     ├── pytest tests/ -q
    │     └── pip-audit --severity high
    │
    └── test-api
          ├── pip install -e ../bot
          ├── pip install -r requirements.txt -r requirements-test.txt
          ├── ruff check src/ tests/
          ├── pytest --cov=src --cov-fail-under=75
          ├── mypy src/
          └── pip-audit --severity high
```

### 10.2 Web CI job details

```yaml
test-web:
  runs-on: ubuntu-latest
  defaults:
    run:
      working-directory: packages/web
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with: { node-version: "20", cache: "npm" }
    - run: npm ci
    - run: npm run lint
    - run: npm test
    - run: npm test -- --coverage
    - run: npx prettier --check "src/**/*.{ts,tsx}"
    - run: npm audit --audit-level=critical
```

The audit step blocks the pipeline only on Critical CVEs. High CVEs in build
tooling (not the production bundle) are permitted — use `npm audit --audit-level=high`
locally to review them.

### 10.3 Adding CI secrets

For production deployments triggered from CI, add these secrets in
`Settings → Secrets and variables → Actions`:

| Secret | Description |
|---|---|
| `NETLIFY_SITE_URL` | Netlify site URL for JWT validation |
| `SONARFT_API_TOKEN` | Static API token (if not using Netlify) |
| `DOCKER_USERNAME` | Docker Hub username for image push |
| `DOCKER_PASSWORD` | Docker Hub password / access token |

### 10.4 Extending the pipeline

**Add a deployment step:**

```yaml
deploy:
  name: Deploy — api
  runs-on: ubuntu-latest
  needs: [test-bot, test-api, test-web]
  if: github.ref == 'refs/heads/main'
  steps:
    - uses: actions/checkout@v4
    - name: Build and push Docker image
      run: |
        docker build -t ${{ secrets.DOCKER_USERNAME }}/sonarft-api:latest packages/api/
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
        docker push ${{ secrets.DOCKER_USERNAME }}/sonarft-api:latest
```

---

## 11. API Reference

### 11.1 Base URL

```
Development:  http://localhost:8000/api/v1
Production:   https://api.your-domain.com/api/v1
```

Interactive documentation: `/api/v1/docs` (Swagger UI) and `/api/v1/redoc`.

### 11.2 Authentication

All endpoints except `/health` require a Bearer token when auth is enabled.

```bash
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/v1/bots?client_id=user_123"
```

In development with no auth configured, the header can be omitted.

### 11.3 Endpoint reference

#### Health

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Service health check |

```bash
curl http://localhost:8000/api/v1/health
# → {"status":"ok","version":"1.0.0"}
```

#### Bots — canonical paths (preferred)

| Method | Path | Description |
|---|---|---|
| `GET` | `/clients/{client_id}/bots` | List bot IDs |
| `POST` | `/clients/{client_id}/bots` | Create a new bot |
| `POST` | `/clients/{client_id}/bots/{botid}/run` | Start a bot |
| `POST` | `/clients/{client_id}/bots/{botid}/stop` | Stop a bot |
| `DELETE` | `/clients/{client_id}/bots/{botid}` | Remove a bot |
| `GET` | `/clients/{client_id}/bots/{botid}/orders` | Order history (`?limit=&offset=&from_ts=&to_ts=`) |
| `GET` | `/clients/{client_id}/bots/{botid}/trades` | Trade history (`?limit=&offset=&from_ts=&to_ts=`) |

#### Bots — legacy paths (deprecated, still functional)

| Method | Path | Description |
|---|---|---|
| `GET` | `/bots?client_id=` | List bot IDs |
| `POST` | `/bots?client_id=` | Create a new bot |
| `POST` | `/bots/{botid}/run` | Start a bot |
| `POST` | `/bots/{botid}/stop` | Stop a bot |
| `DELETE` | `/bots/{botid}` | Remove a bot |
| `GET` | `/bots/{botid}/orders` | Order history |
| `GET` | `/bots/{botid}/trades` | Trade history |

#### Configuration — canonical paths (preferred)

| Method | Path | Description |
|---|---|---|
| `GET` | `/clients/{client_id}/parameters` | Get per-client parameters |
| `PUT` | `/clients/{client_id}/parameters` | Update per-client parameters |
| `GET` | `/clients/{client_id}/indicators` | Get per-client indicators |
| `PUT` | `/clients/{client_id}/indicators` | Update per-client indicators |

#### Configuration — legacy paths (deprecated, still functional)

| Method | Path | Description |
|---|---|---|
| `GET` | `/parameters/defaults` | Default trading parameters |
| `GET` | `/parameters?client_id=` | Per-client parameters |
| `PUT` | `/parameters?client_id=` | Update per-client parameters |
| `GET` | `/indicators/defaults` | Default indicator settings |
| `GET` | `/indicators?client_id=` | Per-client indicators |
| `PUT` | `/indicators?client_id=` | Update per-client indicators |

#### WebSocket ticket

| Method | Path | Description |
|---|---|---|
| `POST` | `/ws/ticket` | Exchange Bearer JWT for a 30-second single-use WS ticket |

```bash
curl -X POST -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/ws/ticket
# → {"ticket":"<opaque-32-bytes>","ttl_seconds":30}
```

### 11.4 Request / response examples

```bash
# Create a bot (canonical)
curl -X POST -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/clients/user_123/bots
# → {"botid":"bot_abc123"}

# Update parameters (canonical)
curl -X PUT -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"exchanges":{"Binance":true,"Okx":false},"symbols":{"BTC/USDT":true}}' \
     http://localhost:8000/api/v1/clients/user_123/parameters
# → {"message":"Parameters for user_123 updated."}

# Update indicators (canonical)
curl -X PUT -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"periods":{"5min":true},"oscillators":{"Relative Strength Index (14)":true},"movingaverages":{"Exponential Moving Average (10)":true}}' \
     http://localhost:8000/api/v1/clients/user_123/indicators
# → {"message":"Indicators for user_123 updated."}

# Get trade history with pagination and time filter
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/v1/clients/user_123/bots/bot_abc123/trades?limit=50&offset=0&from_ts=2025-01-01T00:00:00&to_ts=2025-12-31T23:59:59"
# → [{"timestamp":"...","profit":50.0,...}]
```

### 11.5 WebSocket protocol

**Connection:**
```
ws://localhost:8000/api/v1/ws/{client_id}?ticket=<ticket>
```

**Client → Server commands:**

```json
{ "type": "keypress", "key": "create" }
{ "type": "keypress", "key": "run",    "botid": "bot_abc123" }
{ "type": "keypress", "key": "remove", "botid": "bot_abc123" }
{ "type": "keypress", "key": "set_simulation", "botid": "bot_abc123", "value": false }
```

**Server → Client events:**

```json
{ "type": "connected",     "client_id": "user_123",  "ts": 1720000000 }
{ "type": "log",           "level": "INFO", "message": "...", "ts": 1720000001 }
{ "type": "bot_created",   "botid": "bot_abc123",    "ts": 1720000002 }
{ "type": "bot_removed",   "botid": "bot_abc123",    "ts": 1720000003 }
{ "type": "order_success",                            "ts": 1720000004 }
{ "type": "trade_success",                            "ts": 1720000005 }
{ "type": "error",         "message": "Bot limit reached (5)", "ts": 1720000006 }
{ "type": "ping",                                     "ts": 1720000030 }
```

The server sends a `ping` every 30 seconds of inactivity. The client does not
need to respond. All event and command types are defined in `shared/types/api.ts`.

### 11.6 Error responses

```json
{ "detail": "Human-readable error message" }
```

| Status | Meaning |
|---|---|
| `400` | Invalid request (bad `botid` format, missing field) |
| `401` | Unauthorized — missing or invalid Bearer token |
| `404` | Bot not found |
| `429` | Bot limit exceeded or rate limit hit |
| `500` | Internal server error |

### 11.7 Rate limits

| Endpoint group | Limit |
|---|---|
| `GET /bots`, `GET /clients/*/bots` | 60 requests/minute |
| `POST /bots`, `POST /clients/*/bots` | 10 requests/minute |
| `POST /bots/*/run`, `POST /bots/*/stop` | 20 requests/minute |
| `GET /parameters`, `GET /indicators` | 60 requests/minute |
| `PUT /parameters`, `PUT /indicators` | 30 requests/minute |
| `POST /ws/ticket` | 30 requests/minute |

---

## 12. Troubleshooting

### 12.1 Python / venv issues

---

**`pip: command not found`**

Ubuntu 24.04 does not install pip as a system command. Use the venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install ...
```

---

**`ModuleNotFoundError: No module named 'sonarft_manager'`**

The bot package is not installed in the active venv:

```bash
source .venv/bin/activate
pip install -e packages/bot
```

---

**`ModuleNotFoundError: No module named 'src'`**

The API must be run from `packages/api/`, not from the monorepo root:

```bash
cd packages/api
../../.venv/bin/uvicorn src.main:app --reload
# Or: make dev-api
```

---

**`ValidationError: debug — Input should be a valid boolean`**

A system environment variable (e.g. `DEBUG=release`) conflicts with a
pydantic-settings field. Unset it:

```bash
unset DEBUG
```

---

**Changes to `packages/bot/*.py` not reflected in the API**

The bot is installed as an editable package — Python module changes are
picked up immediately. If you added a new file or changed `pyproject.toml`,
reinstall:

```bash
source .venv/bin/activate
pip install -e packages/bot
# Then restart the API server
```

---

### 12.2 API server issues

---

**API starts but returns `500 Internal Server Error`**

Check the API terminal for the traceback. Common causes:

1. **Missing `.env` file:**
   ```bash
   cp packages/api/.env.example packages/api/.env
   ```

2. **`DATA_DIR` path is wrong** — for development, set:
   ```bash
   DATA_DIR=../bot/sonarftdata
   ```

3. **Bot package not installed** — see §12.1.

---

**`401 Unauthorized` on all requests**

Disable auth in development by leaving both variables empty in `.env`:
```bash
NETLIFY_SITE_URL=
SONARFT_API_TOKEN=
```

---

**`CORS error` in the browser**

Add the frontend origin to `CORS_ORIGINS` in `packages/api/.env`:
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```
Restart the API server after changing `.env`.

---

**Port 8000 already in use**

```bash
lsof -ti:8000 | xargs kill -9
```

---

### 12.3 Web frontend issues

---

**`npm ci` fails with `ENOENT: package-lock.json`**

```bash
cd packages/web
npm install   # generates package-lock.json
npm ci        # now works
```

---

**Vite build fails: `Cannot resolve import "clsx" from recharts`**

Recharts' transitive dependencies are not installed. Run a clean install:

```bash
cd packages/web
rm -rf node_modules
npm install
```

---

**`VITE_API_URL` is undefined at runtime**

Verify `.env.development` exists and contains the variable:
```bash
cat packages/web/.env.development
# Should show: VITE_API_URL=http://localhost:8000/api/v1
```

Access via `import.meta.env.VITE_API_URL` — not `process.env`.

---

**Web tests fail: `Cannot find module 'netlify-identity-widget'`**

The mock is defined in `src/setupTests.ts`. Ensure Vitest is configured to
use it in `vite.config.js`:
```js
test: { setupFiles: "./src/setupTests.ts" }
```

---

**`npm test` passes locally but fails in CI**

CI runs `vitest run` (single pass, no watch). Ensure tests do not depend on
execution order and all async operations are properly awaited. Use `waitFor`
for components with async data loading.

---

### 12.4 Docker issues

---

**`docker-compose up` fails: `service 'api' failed to build`**

Always build from the monorepo root using the Makefile:
```bash
make build   # correct — runs from monorepo root
```

---

**Container starts but API health check fails**

```bash
docker-compose -f infra/docker-compose.yml logs api
docker-compose -f infra/docker-compose.yml exec api \
  curl http://localhost:8000/api/v1/health
```

---

**`bot-data` volume is empty after first run**

Seed the volume from the host:
```bash
docker cp packages/bot/sonarftdata/. \
  $(docker-compose -f infra/docker-compose.yml ps -q bot):/app/sonarftdata/
```

---

### 12.5 Quick diagnostics checklist

```bash
# 1. Is the venv active?
which python   # should show .venv/bin/python

# 2. Is the bot installed?
pip show sonarft-bot

# 3. Does the API import cleanly?
cd packages/api
python -c "from src.main import app; print(len(app.routes), 'routes')"

# 4. Is the API running?
curl http://localhost:8000/api/v1/health

# 5. Is the web dev server running?
curl http://localhost:3000

# 6. Are env vars loaded?
cd packages/api
python -c "from src.core.config import get_settings; s=get_settings(); print('data_dir:', s.data_dir)"

# 7. Are Node modules installed?
ls packages/web/node_modules/.bin/vite

# 8. Do all tests pass?
make test
```

---

*End of Developer Guide — v1.1.0*
