# SonarFT - Technology Stack

## Languages & Runtimes
| Layer | Language | Version |
|---|---|---|
| Bot engine | Python | 3.11 |
| API server | Python | 3.11 |
| Web frontend | TypeScript | 5.x |
| Models | C++ / Java | — |

## Bot Package Dependencies (`packages/bot/requirements.txt`)
| Package | Version | Purpose |
|---|---|---|
| fastapi | 0.135.3 | HTTP REST API and WebSocket server |
| uvicorn[standard] | 0.44.0 | ASGI server |
| pandas | 3.0.2 | Time-series data manipulation for indicators |
| pandas-ta | 0.4.71b0 | Technical analysis indicators (RSI, MACD, StochRSI, SMA, etc.) |
| ccxt / ccxt[pro] | 4.5.48 | Multi-exchange trading library (REST + WebSocket) |
| pydantic | >=2.0 | Data validation |
| PyJWT[crypto] | >=2.7.0 | JWT handling |
| simple-websocket | 1.1.0 | WebSocket client |
| hypothesis | latest | Property-based testing |
| pytest / pytest-asyncio | latest | Test framework |

## API Package Dependencies (`packages/api/requirements.txt`)
| Package | Version | Purpose |
|---|---|---|
| fastapi | 0.135.3 | HTTP REST API and WebSocket server |
| uvicorn[standard] | 0.44.0 | ASGI server |
| pydantic / pydantic-settings | >=2.0 | Data validation and settings management |
| PyJWT[crypto] | >=2.7.0 | JWT validation (Netlify Identity) |
| python-dotenv | >=1.2.2 | `.env` file loading |
| orjson | latest | Fast JSON serialization |
| aiofiles | latest | Async file I/O |
| slowapi | >=0.1.9 | Rate limiting for FastAPI |
| sonarft-bot | local editable | Bot engine (`pip install -e ../bot`) |

## Web Package Dependencies (`packages/web/package.json`)
| Package | Version | Purpose |
|---|---|---|
| react / react-dom | ^18.2.0 | UI framework |
| react-router-dom | ^6.30.3 | Client-side routing |
| react-redux | ^9.2.0 | State management |
| @reduxjs/toolkit | ^2.11.2 | Redux utilities |
| recharts | ^3.8.1 | P&L chart visualization |
| immer | ^11.1.8 | Immutable state updates |
| reselect | ^5.1.1 | Memoized selectors |
| decimal.js-light | ^2.5.1 | Decimal precision in frontend |
| clsx | ^2.1.1 | Conditional class names |
| es-toolkit | ^1.46.1 | Utility functions |
| eventemitter3 | ^5.0.4 | Event emitter |
| web-vitals | ^2.1.4 | Performance metrics |

## Web Dev Dependencies
| Package | Version | Purpose |
|---|---|---|
| vite | ^8.0.8 | Build tool with HMR |
| @vitejs/plugin-react | ^6.0.1 | React plugin for Vite |
| vitest | ^3.0.0 | Unit test runner |
| @testing-library/react | ^13.4.0 | React component testing |
| msw | ^2.13.4 | Mock Service Worker v2 for API mocking |
| jest-axe | ^10.0.0 | Accessibility testing |
| typescript | ^5.0.0 | TypeScript compiler |
| eslint | ^9.39.4 | Linting (flat config) |
| eslint-plugin-react-hooks | ^7.1.1 | React hooks lint rules |
| eslint-plugin-jsx-a11y | ^6.10.2 | Accessibility lint rules |
| @typescript-eslint/* | ^8.59.0 | TypeScript lint rules |
| prettier | ^3.0.3 | Code formatting |

## Async Framework (Python)
- `asyncio` — all bot operations, trade search, API calls, and WebSocket handling
- `asyncio.gather` — concurrent symbol processing per bot cycle
- `asyncio.Lock` — thread-safe bot registry in BotManager
- `asyncio.Queue` — async log streaming to WebSocket clients

## Decimal Precision (Python)
- `decimal.getcontext().prec = 28` — set in files performing financial calculations (matches IEEE 754 decimal128)

## Infrastructure
- Docker: `python:3.11` base image for bot and api; nginx for web
- Docker Compose: production (`infra/docker-compose.yml`) and dev with hot reload (`infra/docker-compose.dev.yml`)
- CI: GitHub Actions (`.github/workflows/ci.yml`) — web tests + `npm audit --audit-level=high` on push/PR
- Linting: `ruff` for Python, ESLint v9 flat config for TypeScript

## Development Commands
```bash
make setup         # Create .venv, install all deps (run once)
make install       # Re-install all dependencies
make dev-api       # Start API server with hot reload on :8000
make dev-web       # Start web dev server with HMR on :5173
make dev           # Start all services via Docker Compose
make test          # Run all tests (bot + api + web)
make test-bot      # pytest for bot package
make test-api      # pytest for api package
make test-web      # Vitest for web package
make lint          # ruff + eslint across all packages
make build         # Build all Docker images
make build-web     # Build web production bundle
make clean         # Remove build artifacts and caches
make logs          # Tail Docker Compose logs
```

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
| `VITE_DEV_AUTH_BYPASS` | `true` | Present for documentation purposes; app always uses DEFAULT_USER |
| `VITE_API_URL` | `http://localhost:8000/api/v1` | API base URL |
| `VITE_WS_URL` | `ws://localhost:8000/api/v1/ws` | WebSocket base URL |
| `VITE_IDLE_TIMEOUT_MS` | `1800000` | Session idle timeout (ms) |
