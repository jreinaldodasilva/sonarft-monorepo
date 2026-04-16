# SonarFT Monorepo — Developer Guide

**Version:** 1.0.0  
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
│   │   ├── sonarft_*.py        # Trading modules (indicators, execution, etc.)
│   │   ├── sonarftdata/        # Configuration files
│   │   ├── tests/              # Bot unit tests
│   │   ├── pyproject.toml      # Package definition (pip-installable)
│   │   ├── requirements.txt    # Runtime dependencies
│   │   └── Dockerfile
│   │
│   ├── api/                    # Python — FastAPI REST + WebSocket backend
│   │   ├── src/
│   │   │   ├── api/v1/
│   │   │   │   └── endpoints/  # health.py, bots.py, config.py
│   │   │   ├── core/           # config.py, security.py, errors.py
│   │   │   ├── models/         # schemas.py (Pydantic models)
│   │   │   ├── services/       # bot_service.py, config_service.py
│   │   │   ├── websocket/      # manager.py
│   │   │   └── main.py         # FastAPI app factory
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   ├── .env.example        # Environment template
│   │   └── Dockerfile
│   │
│   └── web/                    # TypeScript — React 18 + Vite frontend
│       ├── src/
│       │   ├── components/     # UI components
│       │   ├── hooks/          # Custom React hooks
│       │   ├── pages/          # Route-level pages
│       │   ├── utils/          # api.ts, constants.ts, helpers.ts
│       │   └── mocks/          # MSW test handlers
│       ├── package.json
│       ├── vite.config.js
│       ├── tsconfig.json
│       ├── .env.development    # Local dev URLs (gitignored)
│       ├── .env.development.example
│       └── Dockerfile
│
├── shared/
│   └── types/
│       └── api.ts              # Single source of truth for API contract
│
├── infra/
│   ├── docker-compose.yml      # Production orchestration
│   └── docker-compose.dev.yml  # Development overrides (hot reload)
│
├── .github/
│   └── workflows/
│       └── ci.yml              # Per-package CI jobs
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
> library imported by `packages/api`. The old `sonarft_server.py` and `sonarft.py`
> entry points have been removed — all HTTP/WebSocket concerns live in `packages/api`.

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
python --version                  # Python 3.12.x
pip show sonarft-bot              # confirms bot is installed as editable
pip show fastapi                  # confirms API deps are installed

# Confirm the API app loads without errors
cd packages/api
python -c "from src.main import app; print('Routes:', len(app.routes))"
# → Routes: 19
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
automatically sets the Python interpreter to `.venv/bin/python`. No manual
interpreter selection is needed.

Recommended extensions (prompted automatically by VS Code):
- `ms-python.python` — Python language support
- `ms-python.black-formatter` — Python formatting
- `esbenp.prettier-vscode` — TypeScript/JSX formatting
- `dbaeumer.vscode-eslint` — ESLint integration

### 3.6 Updating dependencies

After pulling changes that modify `requirements.txt` or `package.json`:

```bash
# Update Python dependencies
make install-bot    # re-installs bot (picks up pyproject.toml changes)
make install-api    # re-installs API deps

# Update Node dependencies
make install-web    # runs npm ci
```

---

## 4. Environment Variables

### 4.1 packages/api — `.env`

Create `packages/api/.env` by copying the example:

```bash
cp packages/api/.env.example packages/api/.env
```

| Variable | Default | Required | Description |
|---|---|---|---|
| `NETLIFY_SITE_URL` | `""` | No* | Netlify site URL for JWT validation (e.g. `https://sonarft.netlify.app`) |
| `SONARFT_API_TOKEN` | `""` | No* | Static Bearer token fallback for non-Netlify deployments |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Yes | Comma-separated list of allowed frontend origins |
| `MAX_BOTS_PER_CLIENT` | `5` | No | Maximum concurrent bots per authenticated client |
| `DATA_DIR` | `sonarftdata` | Yes | Path to the bot data directory (relative to `packages/api/`) |
| `LOG_LEVEL` | `INFO` | No | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

> \* If neither `NETLIFY_SITE_URL` nor `SONARFT_API_TOKEN` is set, authentication
> is **disabled**. This is acceptable for local development but must not be used
> in production. The API will log a warning on startup.

**Authentication modes:**

```bash
# Option A — Netlify Identity (production, recommended)
NETLIFY_SITE_URL=https://your-site.netlify.app

# Option B — Static token (simpler, non-Netlify deployments)
SONARFT_API_TOKEN=your-secret-token-here

# Option C — No auth (development only — leave both empty)
NETLIFY_SITE_URL=
SONARFT_API_TOKEN=
```

**Development `.env` (minimum working config):**

```bash
# packages/api/.env
NETLIFY_SITE_URL=
SONARFT_API_TOKEN=
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
MAX_BOTS_PER_CLIENT=5
DATA_DIR=../bot/sonarftdata
LOG_LEVEL=INFO
```

### 4.2 packages/web — `.env.development`

The web package already has `.env.development` pre-configured in the monorepo.
To customise, copy the example:

```bash
cp packages/web/.env.development.example packages/web/.env.development
```

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000/api/v1` | API base URL used by the frontend |
| `VITE_WS_URL` | `ws://localhost:8000/api/v1/ws` | WebSocket base URL |
| `VITE_VITALS_URL` | `""` | Optional Web Vitals reporting endpoint |
| `VITE_IDLE_TIMEOUT_MS` | `1800000` | Session idle timeout in milliseconds (30 min) |

> **Vite vs CRA env vars:** Vite exposes variables prefixed with `VITE_` via
> `import.meta.env.VITE_*`. The old `REACT_APP_*` prefix is no longer used.

**Production `.env.production`:**

```bash
# packages/web/.env.production
VITE_API_URL=https://api.your-domain.com/api/v1
VITE_WS_URL=wss://api.your-domain.com/api/v1/ws
VITE_IDLE_TIMEOUT_MS=1800000
```

> **Important:** After changing `VITE_API_URL` or `VITE_WS_URL` for production,
> also update the `connect-src` directive in `packages/web/public/index.html`
> to include the new API domain in the Content Security Policy.

### 4.3 Docker Compose environment

When running via Docker Compose, variables are passed through a root-level `.env` file:

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

Docker Compose reads this file automatically when run from the monorepo root.

---

## 5. Running the Application

### 5.1 Manual start (recommended for development)

Open three terminal windows from the monorepo root:

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

The API server starts with `--reload` — it automatically restarts when any
file in `packages/api/src/` changes.

**Terminal 2 — Web dev server**

```bash
make dev-web
```

Output:
```
  VITE v8.x.x  ready in 312 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

**Terminal 3 — (optional) watch API logs**

```bash
# The API terminal already shows logs.
# For structured log tailing with filtering:
source .venv/bin/activate
cd packages/api
../../.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

### 5.2 Service URLs

| Service | URL | Notes |
|---|---|---|
| Web frontend | http://localhost:5173 | Vite dev server with HMR |
| API server | http://localhost:8000 | FastAPI with auto-reload |
| API docs (Swagger) | http://localhost:8000/api/v1/docs | Interactive API explorer |
| API docs (ReDoc) | http://localhost:8000/api/v1/redoc | Alternative API docs |
| OpenAPI schema | http://localhost:8000/api/v1/openapi.json | Raw JSON schema |
| Health check | http://localhost:8000/api/v1/health | Returns `{"status":"ok"}` |

### 5.3 Verify everything is working

```bash
# 1. Health check
curl http://localhost:8000/api/v1/health
# → {"status":"ok","version":"1.0.0"}

# 2. List bots (no auth in dev mode)
curl "http://localhost:8000/api/v1/bots?client_id=test_user"
# → {"botids":[]}

# 3. Open the web app
open http://localhost:5173   # macOS
xdg-open http://localhost:5173  # Linux
```

### 5.4 Docker Compose start (all services)

```bash
# Production mode
make dev

# This runs:
# docker-compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up
```

Services started:
- `bot` — trading engine (internal, not exposed)
- `api` — FastAPI on port 8000
- `web` — React frontend on port 3000 (nginx in prod, Vite in dev)

### 5.5 Stopping services

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
Changes to any `sonarft_*.py` file take effect immediately — no reinstall needed.

```bash
# Edit a bot module
vim packages/bot/sonarft_indicators.py

# The API server (if running with --reload) will pick up the change
# automatically on the next request that imports the modified module.
# For deeper changes, restart the API server (Ctrl+C, then make dev-api).
```

### 6.2 Making changes to packages/api

The API server runs with `--reload` in development. Any change to a file in
`packages/api/src/` triggers an automatic restart within ~1 second.

```bash
# Edit an endpoint
vim packages/api/src/api/v1/endpoints/bots.py
# → API restarts automatically
```

### 6.3 Making changes to packages/web

The Vite dev server provides Hot Module Replacement (HMR). Changes to
TypeScript/TSX/CSS files appear in the browser instantly without a full reload.

```bash
# Edit a component
vim packages/web/src/components/Bots/Bots.tsx
# → Browser updates in < 100ms
```

### 6.4 Adding a new API endpoint

1. Create the endpoint in `packages/api/src/api/v1/endpoints/`
2. Add Pydantic request/response models to `packages/api/src/models/schemas.py`
3. Register the router in `packages/api/src/main.py`
4. Add the corresponding TypeScript types to `shared/types/api.ts`
5. Update `packages/web/src/utils/api.ts` to call the new endpoint

### 6.5 Adding a new bot module

1. Create `packages/bot/sonarft_newmodule.py`
2. Add it to `[tool.setuptools.packages.find]` in `packages/bot/pyproject.toml` if needed
3. Import it in `packages/api/src/services/bot_service.py`
4. No reinstall needed — editable install picks it up immediately

### 6.6 Updating shared types

`shared/types/api.ts` is the contract between the API and the web frontend.
When you change it:

1. Update `shared/types/api.ts` with the new TypeScript types
2. Update the corresponding Pydantic models in `packages/api/src/models/schemas.py`
3. Update `packages/web/src/utils/api.ts` to use the new types
4. Run both test suites to confirm nothing is broken

### 6.7 Makefile quick reference

```bash
make help          # List all available commands with descriptions
make setup         # First-time setup: create venv, install all deps
make install       # Re-install all dependencies (after pulling changes)
make dev-api       # Start API server with hot reload on :8000
make dev-web       # Start web dev server with HMR on :5173
make dev           # Start all services via Docker Compose
make test          # Run all tests (bot + api + web)
make test-bot      # Run bot tests only
make test-api      # Run API tests only
make test-web      # Run web tests only
make lint          # Lint all packages
make lint-web      # Lint web package (ESLint + TypeScript)
make build         # Build all Docker images
make build-web     # Build web production bundle
make clean         # Remove build artifacts and caches
make logs          # Tail Docker Compose logs
```
