# SonarFT - Project Structure

## Directory Layout
```
sonarft-monorepo/
├── packages/
│   ├── bot/                    # Python trading engine (importable as sonarft-bot)
│   │   ├── sonarft_bot.py      # SonarftBot: config loading, module wiring, run loop
│   │   ├── sonarft_manager.py  # BotManager: lifecycle management, async lock
│   │   ├── sonarft_search.py   # Trade search orchestration (SonarftSearch)
│   │   ├── trade_processor.py  # Per-symbol price fetch, adjustment, profit check
│   │   ├── trade_validator.py  # Liquidity and spread validation
│   │   ├── trade_executor.py   # Async task management for trade execution
│   │   ├── sonarft_prices.py   # VWAP, weighted price adjustment, spread logic
│   │   ├── sonarft_indicators.py # RSI, MACD, StochRSI, SMA, volatility
│   │   ├── sonarft_math.py     # Profit/fee calculations, exchange precision rules
│   │   ├── sonarft_execution.py # Order placement (real and simulated)
│   │   ├── sonarft_validators.py # Liquidity depth and spread threshold checks
│   │   ├── sonarft_api_manager.py # Exchange API abstraction (ccxtpro/ccxt)
│   │   ├── sonarft_helpers.py  # File I/O, formatting, trade history persistence
│   │   ├── sonarft_metrics.py  # Metrics collection and reporting
│   │   ├── models.py           # Shared data models / dataclasses
│   │   ├── config_schemas.py   # Pydantic/dataclass schemas for config files
│   │   ├── sonarftdata/        # JSON config files and runtime data
│   │   │   ├── config.json
│   │   │   ├── config_parameters.json
│   │   │   ├── config_exchanges.json
│   │   │   ├── config_symbols.json
│   │   │   ├── config_fees.json
│   │   │   ├── config_indicators.json
│   │   │   ├── config_markets.json
│   │   │   ├── config/         # Per-client runtime config
│   │   │   ├── bots/           # Per-bot registry JSON
│   │   │   └── history/        # Per-bot trade and order history JSON
│   │   ├── models/             # C++ genetic algorithm, Java test generator
│   │   └── tests/              # pytest test suite
│   ├── api/                    # FastAPI REST + WebSocket backend
│   │   └── src/
│   │       ├── main.py         # FastAPI app entry point
│   │       ├── api/            # Route handlers (bots, parameters, indicators, ws)
│   │       ├── core/           # Auth, config, middleware, rate limiting
│   │       ├── models/         # Pydantic schemas (synced with shared/types/api.ts)
│   │       ├── services/       # Business logic, bot service layer
│   │       └── websocket/      # WebSocket handler, ticket auth, event dispatch
│   └── web/                    # React 18 + Vite frontend
│       └── src/
│           ├── components/     # UI components (ConfigCheckboxPanel, etc.)
│           ├── hooks/          # Custom React hooks (useWebSocket, useBot, etc.)
│           ├── pages/          # Page-level components (Crypto trading page)
│           ├── integration/    # API client functions
│           ├── utils/          # Utility functions
│           └── mocks/          # MSW v2 mock handlers for tests
├── shared/
│   └── types/
│       └── api.ts              # Single source of truth for API contract types
├── infra/
│   ├── docker-compose.yml      # Production orchestration
│   └── docker-compose.dev.yml  # Development overrides (hot reload)
├── docs/
│   ├── developer-guide.md
│   └── backtesting-guide.md
├── .github/workflows/ci.yml    # CI: web tests + npm audit on push/PR
└── Makefile                    # Top-level dev commands
```

## Class Responsibilities (bot package)

| Class | File | Role |
|---|---|---|
| BotManager | sonarft_manager.py | Create/run/remove bot instances, client-to-bot mapping, asyncio.Lock |
| SonarftBot | sonarft_bot.py | Config loading, module initialization, main run loop |
| SonarftSearch | sonarft_search.py | Orchestrates trade search across symbols concurrently |
| TradeProcessor | trade_processor.py | Per-symbol price fetching, adjustment, profit check, execution trigger |
| TradeValidator | trade_validator.py | Liquidity and spread validation before execution |
| TradeExecutor | trade_executor.py | Async task management for trade execution |
| SonarftPrices | sonarft_prices.py | VWAP, weighted price adjustment, dynamic volatility, support/resistance |
| SonarftIndicators | sonarft_indicators.py | RSI, MACD, StochRSI, SMA, market direction/trend/movement |
| SonarftMath | sonarft_math.py | Profit/fee calculation, trade data packaging, exchange precision rules |
| SonarftExecution | sonarft_execution.py | Buy/sell order placement (real or simulated) |
| SonarftValidators | sonarft_validators.py | Order book liquidity depth checks, spread threshold |
| SonarftApiManager | sonarft_api_manager.py | Exchange API calls (WebSocket default, ccxt fallback) |
| SonarftHelpers | sonarft_helpers.py | Formatting, file I/O, trade/order history persistence |

## Architectural Patterns

- **Monorepo with independent packages**: bot, api, and web are independently deployable; shared types enforce contract
- **Modular OOP (bot)**: each responsibility is a dedicated class in its own file
- **Dependency injection**: modules receive api_manager, logger, and peer modules via constructor — never self-instantiate
- **Async-first**: all I/O-bound operations use `async/await`; concurrent symbol processing via `asyncio.gather`
- **Layered architecture**:
  - Transport: FastAPI/WebSocket (api package)
  - Orchestration: BotManager → SonarftBot
  - Strategy: SonarftSearch → TradeProcessor → TradeValidator/TradeExecutor
  - Analysis: SonarftPrices + SonarftIndicators + SonarftMath
  - Infrastructure: SonarftApiManager + SonarftValidators + SonarftHelpers + SonarftExecution
- **Configuration-driven**: all trading parameters, exchanges, symbols, and fees are JSON-file driven
- **Multi-tenancy**: multiple bots per server, each isolated by `botid` and `client_id`
- **Simulation mode**: `is_simulating_trade` flag gates real order execution throughout the stack
- **Bot state machine (web)**: `useReducer` with explicit transitions: `idle → creating → running → removing → idle`
- **RAF log batching (web)**: WebSocket log messages flush to React state at most 60×/sec via `requestAnimationFrame`
- **Shared types**: `shared/types/api.ts` is the single source of truth; must stay in sync with `packages/api/src/models/schemas.py`
