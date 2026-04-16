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
