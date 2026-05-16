# Getting Started

This guide walks through setting up the SonarFT monorepo from scratch, running all three services locally, and verifying the stack is working.

---

## Prerequisites

| Tool | Minimum Version | Purpose |
|---|---|---|
| Python | 3.11 | Bot engine and API server |
| Node.js | 20 LTS | Web frontend build and dev server |
| npm | 9+ | Web package management (bundled with Node 20) |
| Docker | 24+ | Containerised deployment (optional for dev) |
| Docker Compose | 2.x | Multi-service orchestration (optional for dev) |
| Git | 2.x | Source control |

Verify your versions:

```bash
python3 --version    # Python 3.11.x
node --version       # v20.x.x
npm --version        # 9.x or 10.x
docker --version     # Docker version 24.x
```

---

## Repository Layout

```
sonarft-monorepo/
├── packages/
│   ├── bot/        # Python trading engine
│   ├── api/        # FastAPI backend
│   └── web/        # React frontend
├── shared/types/   # Shared TypeScript API contract
├── infra/          # Docker Compose files
├── docs/           # This documentation
└── Makefile        # Top-level dev commands
```

---

## Option 1 — Manual Setup (Recommended for Development)

### Step 1: Clone and bootstrap

```bash
git clone <repo-url> sonarft-monorepo
cd sonarft-monorepo

# Creates .venv, installs bot package (editable), API deps, and web deps
make setup
```

`make setup` runs the following in sequence:

1. `python3 -m venv .venv` — creates a shared virtual environment at the repo root
2. `pip install -e packages/bot` — installs the bot as an editable package (`sonarft-bot`)
3. `pip install -r packages/api/requirements.txt` — installs API dependencies into the same venv
4. `cd packages/web && npm ci` — installs web dependencies from the lockfile

The bot is installed as an editable package so the API can import it directly (`from sonarft_bot import SonarftBot`) without a separate deployment step.

### Step 2: Configure the API

```bash
cp packages/api/.env.example packages/api/.env
```

For local development, the defaults work without modification. The file looks like:

```env
# Leave both empty to disable auth in dev mode
NETLIFY_SITE_URL=
SONARFT_API_TOKEN=

CORS_ORIGINS=http://localhost:3000,http://localhost:5173
MAX_BOTS_PER_CLIENT=5
DATA_DIR=../bot/sonarftdata
LOG_LEVEL=INFO
LOG_FILE=logs/sonarft.log
```

> **Warning:** When both `NETLIFY_SITE_URL` and `SONARFT_API_TOKEN` are empty, all API endpoints are publicly accessible. This is intentional for local development. Never deploy to production with auth disabled.

### Step 3: Start the API server

```bash
source .venv/bin/activate
make dev-api
```

This runs:
```bash
cd packages/api && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify the API is running:
```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok","version":"1.0.0"}
```

Interactive API docs are available at: http://localhost:8000/api/v1/docs

### Step 4: Start the web dev server

In a second terminal:

```bash
make dev-web
```

This runs:
```bash
cd packages/web && npm run dev
```

The web app is available at: http://localhost:5173

The `VITE_DEV_AUTH_BYPASS=true` setting in `packages/web/.env.development` auto-injects a dev user, so you can use the full trading interface without configuring Netlify Identity.

---

## Option 2 — Docker Compose

Docker Compose runs all three services (bot, api, web) in containers with hot reload enabled via the dev override file.

```bash
# Copy environment files
cp packages/api/.env.example packages/api/.env
cp packages/web/.env.development.example packages/web/.env.development

# Start all services with hot reload
make dev
```

This runs:
```bash
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up
```

Services:
- Web: http://localhost:5173
- API: http://localhost:8000
- API docs: http://localhost:8000/api/v1/docs

The dev override mounts source directories as volumes so code changes trigger hot reload without rebuilding images.

---

## Environment Variables Reference

### `packages/api/.env`

| Variable | Default | Required | Description |
|---|---|---|---|
| `NETLIFY_SITE_URL` | — | No | Netlify site URL for JWT validation (e.g. `https://your-site.netlify.app`) |
| `SONARFT_API_TOKEN` | — | No | Static token for non-Netlify auth |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | No | Comma-separated allowed CORS origins |
| `MAX_BOTS_PER_CLIENT` | `5` | No | Maximum concurrent bots per client |
| `DATA_DIR` | `sonarftdata` | No | Path to bot data directory (relative to `packages/api/`) |
| `LOG_LEVEL` | `INFO` | No | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | `logs/sonarft.log` | No | Log file path (relative to `packages/api/`); empty to disable |
| `JSON_LOG_FILE` | — | No | Structured JSON log file path; empty to disable |

### `packages/web/.env.development`

| Variable | Default | Description |
|---|---|---|
| `VITE_DEV_AUTH_BYPASS` | `true` | Skip Netlify Identity — auto-injects a dev user |
| `VITE_API_URL` | `http://localhost:8000/api/v1` | API base URL |
| `VITE_WS_URL` | `ws://localhost:8000/api/v1/ws` | WebSocket base URL |
| `VITE_IDLE_TIMEOUT_MS` | `1800000` | Session idle timeout in milliseconds (30 minutes) |
| `VITE_VITALS_URL` | — | Web Vitals reporting endpoint (optional) |

### Bot environment variables (set in shell or `.env` before running)

| Variable | Default | Description |
|---|---|---|
| `SONARFT_ALLOW_LIVE` | — | Must be `true` to enable live trading; prevents accidental real-money trades |
| `SONARFT_ALERT_WEBHOOK` | — | Slack/Discord/Teams webhook URL for circuit breaker alerts |
| `SONARFT_MAX_FAILURES` | `5` | Consecutive failures before circuit breaker trips |
| `SONARFT_BACKOFF_BASE` | `30` | Base backoff in seconds for failure retry |
| `SONARFT_CYCLE_SLEEP_MIN` | `6` | Minimum sleep between trade search cycles (seconds) |
| `SONARFT_CYCLE_SLEEP_MAX` | `18` | Maximum sleep between trade search cycles (seconds) |
| `SONARFT_FEE_REFRESH_INTERVAL` | `86400` | Fee refresh interval in seconds (24 hours) |
| `SONARFT_BACKUP_INTERVAL` | `86400` | Database backup interval in seconds; `0` to disable |
| `SONARFT_BACKUP_DIR` | `sonarftdata/backups` | Directory for SQLite database backups |
| `{EXCHANGE}_API_KEY` | — | Exchange API key (e.g. `BINANCE_API_KEY`) |
| `{EXCHANGE}_SECRET` | — | Exchange secret key (e.g. `BINANCE_SECRET`) |
| `{EXCHANGE}_PASSWORD` | — | Exchange passphrase if required (e.g. `OKX_PASSWORD`) |

---

## Running the Bot Engine Directly

The bot engine can be run standalone for testing without the API layer:

```bash
source .venv/bin/activate
make dev-bot
```

This runs `python -m sonarft_bot` from `packages/bot/`. The bot reads its configuration from `packages/bot/sonarftdata/config.json` and defaults to `config_1`.

---

## Verifying the Full Stack

After starting both the API and web dev server:

1. Open http://localhost:5173
2. The dev auth bypass auto-logs you in as a dev user
3. The trading interface loads with bot controls and configuration panels
4. Click **Create Bot** — the API creates a bot instance and streams logs over WebSocket
5. The log panel shows real-time output from the bot engine

---

## Troubleshooting

### `make setup` fails with "python3 not found"

Ensure Python 3.11 is installed and on your PATH:
```bash
which python3
python3 --version
```

On macOS with Homebrew: `brew install python@3.11`
On Ubuntu/Debian: `sudo apt install python3.11 python3.11-venv`

### `make setup` fails installing `ccxt` or `pandas-ta`

These packages require a C compiler for native extensions. Install build tools:
```bash
# Ubuntu/Debian
sudo apt install build-essential python3.11-dev

# macOS
xcode-select --install
```

### API starts but returns 500 on bot creation

Check that the bot package is installed in the venv:
```bash
source .venv/bin/activate
python -c "import sonarft_bot; print('OK')"
```

If this fails, re-run `make install-bot`.

### Web dev server starts but shows "Cannot connect to server"

Verify the API is running on port 8000:
```bash
curl http://localhost:8000/api/v1/health
```

Check `packages/web/.env.development` has `VITE_API_URL=http://localhost:8000/api/v1`.

### WebSocket connection fails

The WebSocket URL is derived from `VITE_WS_URL`. In dev mode, the frontend fetches a single-use ticket from `POST /api/v1/ws/ticket` before connecting. If auth is disabled (dev mode), the ticket endpoint still works and returns a valid ticket.

Check the browser console for the exact WebSocket URL being used.

### `npm ci` fails with peer dependency errors

Ensure you are using Node.js 20 LTS:
```bash
node --version  # must be v20.x.x
```

Use `nvm` to switch versions: `nvm use 20`

### Port conflicts

If ports 8000 or 5173 are in use:
```bash
# Find what is using port 8000
lsof -i :8000

# Change the API port
cd packages/api && uvicorn src.main:app --port 8001 --reload
# Then update VITE_API_URL in packages/web/.env.development
```

### Docker Compose: containers exit immediately

Check logs for the failing service:
```bash
make logs
# or
docker-compose -f infra/docker-compose.yml logs api
```

Common causes: missing `.env` file, port already in use, or insufficient Docker memory allocation.
