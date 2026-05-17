# SonarFT - Product Overview

## Purpose
SonarFT (System Oscillator for Navigation and Ranging in Financial Trade) is an automated cryptocurrency trading bot that monitors market oscillations and trends to identify and execute profitable trading opportunities across single or multiple exchanges.

## Key Features
- Multi-exchange and cross-exchange trading support
- Real-time market analysis using technical indicators (RSI, MACD, StochRSI, VWAP, SMA/EMA)
- Dual API support: WebSocket (ccxtpro, default) and REST (ccxt, fallback)
- Multi-bot concurrency: multiple independent bot instances per server, isolated by `botid` and `client_id`
- Configurable trading strategies via JSON config files
- Simulation/paper trading mode (`is_simulating_trade`)
- WebSocket-based real-time communication between API server and web frontend
- Per-client logging streamed live over WebSocket
- REST + WebSocket API for bot management, parameter/indicator configuration, and trade history
- API JWT authentication via Netlify Identity or static token fallback; WebSocket ticket auth (JWT never in URL)
- Docker + Traefik deployment with TLS support
- React 18 web frontend with live P&L chart, bot lifecycle controls, and configuration panels

## Architecture — Three-Layer Monorepo
| Package | Language | Role |
|---|---|---|
| `packages/bot` | Python 3.11 | Pure trading engine — indicators, execution, CCXT. No HTTP, no auth. |
| `packages/api` | Python 3.11 | FastAPI service — REST endpoints, WebSocket, JWT auth, CORS, rate limiting. |
| `packages/web` | TypeScript | React 18 + Vite frontend. Talks only to `packages/api`. |
| `shared/types` | TypeScript | API contract types shared between api (Pydantic) and web (TypeScript). |

## Core Trading Mechanism
1. Establish initial bid/ask prices using VWAP from order book depth
2. Adjust prices based on market dynamics: volatility, RSI, StochRSI, MACD, SMA/EMA trend, support/resistance
3. Validate price spread covers trading fees before executing orders
4. Execute buy/sell limit orders (real or simulated) and persist trade/order history

## Target Users
- Algorithmic traders seeking automated crypto market-making
- Developers building or extending trading bot infrastructure
- Operators running multi-bot, multi-exchange trading systems

## Configuration
Bots are configured via JSON files in `sonarftdata/`:
- `config.json` — named configuration sets (config_1, config_2, ...)
- `config_parameters.json` — trading parameters (profit threshold, trade amount, simulation mode)
- `config_exchanges.json` — exchange list
- `config_symbols.json` — trading pairs
- `config_fees.json` — per-exchange fee structures
- `config_indicators.json` — technical indicator settings
- `config_markets.json` — market type (e.g. crypto)

## Project Status
- Test suite: 110/110 web tests passing; pytest suites for bot and api
- npm audit Critical/High: 0
- ESLint: 0 errors, 0 warnings
- WebSocket auth: ticket-based (JWT not in URL)
- Production-ready: Yes
