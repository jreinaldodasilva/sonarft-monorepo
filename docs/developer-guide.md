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
