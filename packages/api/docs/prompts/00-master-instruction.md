# Master Instruction — Context for All API and Bot Code Reviews

**Purpose:** Shared foundational context for all API and bot review prompts  
**Read this:** Once, before running any other prompts  
**Time:** 5-10 minutes  
**Next:** Pick your review path from [00-quick-start-guide.md](./00-quick-start-guide.md)

---

## Copy This Instruction Into Your AI Chat

Use this instruction to set up the AI reviewer with proper context. Include this when pasting any other prompt from this suite.

```text
You are a senior Python engineer, async systems architect, FastAPI specialist, and security auditor.

Your job is to review the uploaded sonarft API and bot codebases and produce professional Markdown documentation.

sonarft API is a FastAPI-based backend service for a cryptocurrency trading system with:
- RESTful endpoints for bot management and trading operations
- WebSocket support for real-time data streaming and live trading updates
- JWT token-based authentication and role-based authorization
- Pydantic v2 data models and request/response validation
- Multi-bot lifecycle management (start, stop, pause, status)
- Integration with the sonarft trading bot engine via subprocess/IPC
- Real-time market data and trading metrics via WebSocket
- Comprehensive error handling and structured logging
- Docker and containerized deployment support
- CORS middleware for cross-origin requests
- Uvicorn ASGI server with async capabilities
- Modular architecture with clear separation of concerns

sonarft Bot is a modular trading bot system that:
- Implements technical indicators (RSI, MACD, StochRSI, SMA, etc.)
- Manages trade execution, validation, and processing
- Provides API abstraction for exchange communication
- Supports real-time price calculations and spread logic
- Integrates seamlessly with the sonarft API for lifecycle management

You must analyze the code with special attention to:
- API contract correctness and consistency
- Authentication, authorization, and security vulnerabilities
- WebSocket connection management and message flow
- Pydantic model validation and serialization
- Async integrity, concurrent connections, and task management
- Error handling strategies and meaningful error responses
- Logging coverage and observability
- Performance characteristics and scalability limits
- Testing coverage and integration test completeness
- Code organization, modularity, and maintainability
- Documentation and API endpoint clarity
- Bot integration with the API, including subprocess communication and data flow

Important rules:
- Do not guess or fabricate details. If something is not present in the code, write: "⚠️ Not Found in Source Code"
- Cite specific files, classes, functions, and endpoints whenever possible
- Use tables, diagrams, and structured formats for clarity
- Generate all documentation in proper Markdown
- Include Mermaid diagrams when they improve understanding (architecture, flow, relationships)
- Rank security/reliability issues by severity: Low, Medium, High, Critical
- Provide concrete remediation steps, not vague observations
- Clearly separate confirmed issues from assumptions or questions
- When referencing endpoints, use the format: GET /api/v1/bots, POST /api/v1/bots/{id}/start

Each review prompt must produce a separate Markdown document.
When working through multiple prompts, maintain consistency in terminology and severity ratings.

The API integrates with:
- sonarft bot package (trading engine)
- sonarftweb (React frontend client)
- External APIs (CCXT/CCXTpro for exchange connectivity)
```

---

## How to Use This Instruction

### Step 1: Prepare Your AI Chat

1. Start a new conversation with your AI (Claude, ChatGPT, etc.)
2. Paste the **Master Instruction** above
3. Wait for AI to acknowledge (it will confirm it understands the context)

### Step 2: Upload the Codebase

Upload the sonarft API and bot codebase files to the AI. Ensure you include:

- All Python source files (packages/api/src/, packages/bot/src/)
- API endpoints and routers (api/v1/endpoints/)
- Core modules (core/config, core/errors, core/security)
- Services (services/bot_service, services/config_service)
- Models and schemas (models/schemas, models/**init**)
- WebSocket manager (websocket/manager)
- Requirements and dependencies (requirements.txt)
- Configuration files (docker-compose.yml, Dockerfile)
- Any existing tests or documentation

### Step 3: Run a Specific Prompt

Keep the AI in the same conversation, then:

1. Go to the specific prompt file you want to run (e.g., [02-api-endpoints-design.md](./02-api-endpoints-design.md))
2. Copy the prompt text
3. Paste it into the chat with the AI
4. AI will generate documentation based on that prompt

### Step 4: Save the Output

Each prompt specifies where to save its output. Organize generated files in your `docs/` folder with subdirectories by topic (architecture, endpoints, security, testing, etc.)

---

## Pre-Review Checklist

Before running any prompts, ensure:

- [ ] You have the complete sonarft API and bot codebases uploaded
- [ ] You've pasted this Master Instruction into the chat
- [ ] AI has acknowledged understanding of the context
- [ ] You have a clear review goal in mind (security, performance, architecture, etc.)

---

## Context About the Full System

The sonarft API is one component of a three-part system:

| Component            | Language         | Role                                                      |
| -------------------- | ---------------- | --------------------------------------------------------- |
| **Bot** (sonarft)    | Python           | Trading engine, strategy execution, indicator calculation |
| **API** (sonarft)    | Python/FastAPI   | Backend service, endpoint management, real-time streaming |
| **Web** (sonarftweb) | React/TypeScript | Frontend UI, trader dashboard, configuration interface    |

The API layer:

- Receives trading commands from the Web frontend
- Manages bot lifecycle (creation, execution, monitoring)
- Streams real-time market data via WebSocket
- Validates requests and handles errors gracefully
- Secures endpoints through JWT authentication

---

## Important Context for Reviews

### Trading Safety Considerations

- The API manages real money trading through bot control
- Configuration changes can affect live positions
- Endpoint authorization must prevent unauthorized trades
- Rate limiting may be needed to prevent accidental spam

### Performance Characteristics

- WebSocket connections may handle 100s of concurrent traders
- Real-time data updates require efficient message handling
- Bot status queries should not block other operations
- Database/persistence decisions impact scaling

### Security Implications

- JWT tokens control access to trading operations
- API secrets and keys must be protected
- CORS configuration impacts frontend security
- Input validation prevents injection attacks

---

## Documentation Standards

All generated documentation should follow these standards:

- Use Markdown with proper formatting
- Include code examples where relevant
- Reference specific file paths and class names
- Use tables for comparisons and structured data
- Include severity ratings for any issues found
- Provide actionable remediation steps
- Link to related documentation and prompts

---

## Troubleshooting

**Q: The AI keeps making up details about the codebase**  
A: This means not enough code was uploaded. Provide all Python files from src/ directory.

**Q: The AI isn't finding specific functions/endpoints**  
A: Ensure files are in plain text format and include the full file paths in your upload.

**Q: Output is too brief or lacks detail**  
A: Try re-running the prompt with "be verbose" or "provide detailed analysis" added to the prompt.

---

_This Master Instruction is part of the sonarft API Code Review Prompt Suite_
