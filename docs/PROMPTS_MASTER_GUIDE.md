# SonarFT Monorepo Code Review Prompts — Master Guide

**Purpose:** Navigate and use code review prompts across all three packages (Bot, API, Web)  
**Audience:** Developers, reviewers, technical leads  
**Time:** Read in 10 minutes

---

## The SonarFT System

SonarFT is a cryptocurrency trading system with three main components working together:

```
┌─────────────────────────────────────────────────────────┐
│                  SonarFT Trading System                  │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────┐  ┌──────────────────┐              │
│  │   sonarftweb     │  │   sonarft bot    │              │
│  │   (Frontend)     │  │   (Engine)       │              │
│  │   React/TS       │  │   Python         │              │
│  └────────┬─────────┘  └────────┬─────────┘              │
│           │                      │                       │
│           │   HTTP/WS            │                       │
│           │   (REST+WebSocket)   │                       │
│           └──────────┬───────────┘                       │
│                      │                                   │
│              ┌───────▼────────┐                          │
│              │   sonarft api  │                          │
│              │   (FastAPI)    │                          │
│              │   Python       │                          │
│              └────────────────┘                          │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Navigation

### I Want to Review...

| What                        | Go to                                            | Time             |
| --------------------------- | ------------------------------------------------ | ---------------- |
| **Just the bot**            | [Bot Prompts](./packages/bot/docs/prompts/)      | 30 min - 5 hours |
| **Just the API**            | [API Prompts](./packages/api/docs/prompts/)      | 30 min - 5 hours |
| **Just the frontend**       | [Web Prompts](./packages/web/docs/prompts/)      | 30 min - 5 hours |
| **Everything (full-stack)** | [Full-Stack Workflow](#full-stack-system-review) | 8-12 hours       |
| **Integration points only** | [Integration Review](#integration-point-review)  | 4-6 hours        |

---

## Code Review Prompt Suites

### 1. Bot Package Prompts (Core Engine)

**Location:** `packages/bot/docs/prompts/`  
**Focus:** Trading logic, strategy execution, indicators, financial math  
**Use When:** Reviewing trading engine, strategy logic, market data handling

**Key Prompts:**

- Architecture & Project Structure
- Async Design & Concurrency
- Trading Engine & Strategy Logic
- Financial Math & Precision (critical for safety!)
- Indicator Pipeline
- Execution & Exchange Integration

[👉 Start with Bot Prompts](./packages/bot/docs/prompts/README.md)

---

### 2. API Package Prompts (Backend Service)

**Location:** `packages/api/docs/prompts/`  
**Focus:** RESTful endpoints, WebSocket, bot control, real-time data  
**Use When:** Reviewing API design, endpoint security, bot management

**Key Prompts:**

- API Architecture & Structure
- API Endpoints Design
- Data Models & Validation
- Authentication & Security (critical for safety!)
- WebSocket Real-Time Streaming
- Error Handling & Logging

[👉 Start with API Prompts](./packages/api/docs/prompts/README.md)

---

### 3. Web Package Prompts (Frontend)

**Location:** `packages/web/docs/prompts/`  
**Focus:** React components, state management, API integration  
**Use When:** Reviewing UI, client-side logic, component design

**Key Prompts:**

- Architecture & Structure (React)
- API Integration
- State Management
- UI Component Design
- Real-Time Updates
- Testing & Quality

[👉 Start with Web Prompts](./packages/web/docs/prompts/README.md)

---

## Review Workflows

### Single-Package Reviews

#### Review Just the Bot

```
1. Read: Bot Master Instruction
2. Run: Bot Prompt 1 (Architecture)
3. Run: Bot Prompts 2-10 (Details)
4. Run: Bot Final Consolidation
5. Generate: Implementation Roadmap
```

⏱️ **Time:** 4-5 hours  
✓ **Best For:** Engine-focused reviews

#### Review Just the API

```
1. Read: API Master Instruction
2. Run: API Prompt 1 (Architecture)
3. Run: API Prompts 2-10 (Details)
4. Run: API Final Consolidation
5. Generate: Implementation Roadmap
```

⏱️ **Time:** 4-5 hours  
✓ **Best For:** Backend-focused reviews

#### Review Just the Web

```
1. Read: Web Master Instruction
2. Run: Web Prompt 1 (Architecture)
3. Run: Web Prompts 2-10 (Details)
4. Run: Web Final Consolidation
5. Generate: Implementation Roadmap
```

⏱️ **Time:** 4-5 hours  
✓ **Best For:** Frontend-focused reviews

---

### Full-Stack System Review

Perfect for comprehensive production readiness assessment:

```
PHASE 1: ENGINE LAYER (Bot)
├─ Read: Bot Master Instruction
├─ Run: Bot Prompts 1-10
└─ Run: Bot Final Consolidation
   └─ Generate: Bot Implementation Roadmap

PHASE 2: API LAYER (Backend)
├─ Read: API Master Instruction
├─ Run: API Prompts 1-10
└─ Run: API Final Consolidation
   └─ Generate: API Implementation Roadmap

PHASE 3: CLIENT LAYER (Frontend)
├─ Read: Web Master Instruction
├─ Run: Web Prompts 1-10
└─ Run: Web Final Consolidation
   └─ Generate: Web Implementation Roadmap

PHASE 4: SYSTEM CONSOLIDATION
├─ Review: All three implementation roadmaps
├─ Identify: Cross-package dependencies
├─ Prioritize: Fixes across all layers
└─ Create: Integrated project roadmap
```

⏱️ **Total Time:** 12-16 hours  
✓ **Best For:** Production deployment, major releases

---

### Integration Point Review

Focus on how components interact:

```
STAGE 1: INTEGRATION POINTS
├─ Bot → API Communication
│  └─ How does API invoke bot? (subprocess, IPC)
│  └─ How does API receive bot status/data?
│
├─ API → Web Communication
│  └─ How does Web authenticate with API?
│  └─ How are bot commands sent to API?
│  └─ How are real-time updates received?
│
└─ Bot ← Exchange Communication
   └─ How does bot connect to exchanges?
   └─ How are market data and orders handled?

STAGE 2: DATA FLOW
├─ Request flow: Web → API → Bot → Exchange
├─ Response flow: Exchange → Bot → API → Web
└─ Real-time flow: Bot/Exchange → API (WebSocket) → Web

STAGE 3: SECURITY ACROSS LAYERS
├─ Authentication: Web → API (JWT)
├─ Authorization: API → Bot control
└─ Secrets: How API keys/tokens are managed
```

⏱️ **Time:** 4-6 hours  
✓ **Best For:** Integration testing, system architecture review

---

### Security-First Review

Prioritize security across all components:

```
Priority 1: Critical Security Issues
├─ Bot: Prompt 8 (Security & Trading Risk)
├─ API: Prompt 4 (Authentication & Security)
└─ Web: Prompt 6 (Authentication & Security)

Priority 2: Data Protection
├─ Bot: Financial data handling
├─ API: Secrets management, token handling
└─ Web: Client-side security, XSS prevention

Priority 3: Integration Security
├─ API-Bot: IPC security
├─ Web-API: CORS and request validation
└─ Bot-Exchange: Exchange API key protection
```

⏱️ **Time:** 4-5 hours  
✓ **Best For:** Security audit, compliance review

---

### Performance Review

Focus on speed and scalability:

```
Bot Performance
├─ Async efficiency
├─ Indicator calculation speed
└─ Exchange API latency

API Performance
├─ Endpoint response times
├─ WebSocket throughput
├─ Database query optimization
└─ Concurrent connection limits

Web Performance
├─ Bundle size
├─ Component render performance
├─ API call optimization
└─ Real-time update handling
```

⏱️ **Time:** 4-6 hours  
✓ **Best For:** Performance optimization, scalability planning

---

## Getting Started

### Step 1: Choose Your Review Path

- Single package? Pick [Bot](#review-just-the-bot), [API](#review-just-the-api), or [Web](#review-just-the-web)
- Everything? Pick [Full-Stack Review](#full-stack-system-review)
- Integration focus? Pick [Integration Review](#integration-point-review)
- Security focus? Pick [Security Review](#security-first-review)

### Step 2: Access the Prompts

Navigate to the chosen package's prompt directory:

- Bot: `packages/bot/docs/prompts/README.md`
- API: `packages/api/docs/prompts/README.md`
- Web: `packages/web/docs/prompts/README.md`

### Step 3: Start with Master Instruction

Each package's master instruction provides essential context:

- Bot: `packages/bot/docs/prompts/00-master-instruction.md`
- API: `packages/api/docs/prompts/00-master-instruction.md`
- Web: `packages/web/docs/prompts/00-quick-start-guide.md` or master instruction

### Step 4: Upload Code & Run Prompts

1. Open a new conversation with your AI
2. Paste the master instruction
3. Upload the relevant source code
4. Run prompts in sequence
5. Save outputs to organized folder

### Step 5: Consolidate Findings

Run the "Final Consolidation" prompt for each package, then review across all:

- Are there consistent patterns?
- Are integration points secure?
- What is the overall readiness level?

---

## Prompt Structure (All Packages)

Each package follows the same 13-document structure:

| #     | Type         | Purpose                        | Time           |
| ----- | ------------ | ------------------------------ | -------------- |
| 00    | Foundation   | Master context                 | 5-10 min       |
| 00    | Foundation   | Quick start guide              | 5 min          |
| 01-10 | Core Reviews | Detailed analysis (10 prompts) | 30-60 min each |
| 11    | Summary      | Consolidation & findings       | 30 min         |
| 12    | Actionable   | Implementation roadmap         | 30-45 min      |
| 99    | Reference    | Best practices guide           | As needed      |

---

## Document Organization by Package

```
packages/bot/docs/prompts/
├── README.md (this guide)
├── 00-master-instruction.md
├── 00-quick-start-guide.md
├── 01-architecture-structure.md
├── 02-async-concurrency.md
├── 03-trading-engine-logic.md
├── 04-financial-math.md
├── 05-indicator-pipeline.md
├── 06-execution-exchange.md
├── 07-configuration-runtime.md
├── 08-security-risk.md
├── 09-performance-scalability.md
├── 10-code-quality-testing.md
├── 11-final-consolidation.md
├── 12-implementation-roadmap.md
├── 13-setup-operations-guide.md
└── 99-best-practices.md

packages/api/docs/prompts/
├── README.md
├── 00-master-instruction.md
├── 00-quick-start-guide.md
├── 01-architecture-structure.md
├── ...similar structure...
└── 99-best-practices.md

packages/web/docs/prompts/
├── README.md
├── 00-master-instruction.md
├── 00-quick-start-guide.md
├── 01-architecture-structure.md
├── ...similar structure...
└── 99-best-practices.md
```

---

## Key Concepts

### Master Instructions

Each package provides a master instruction that sets up your AI with proper context:

- **Bot:** Understands trading logic, async systems, exchanges, financial math
- **API:** Understands FastAPI, WebSocket, authentication, endpoint design
- **Web:** Understands React, state management, API integration

**Usage:** Paste once per conversation; include when running any prompt from that package

### Review Prompts (1-10)

Each prompt focuses on one area and generates a detailed analysis document:

- Independent: Can run individually
- Consistent: All follow same quality standards
- Actionable: Provide specific recommendations

### Consolidation (11) & Roadmap (12)

Summary and action documents:

- **Consolidation:** Executive overview of all findings
- **Roadmap:** Prioritized action items with estimates

### Best Practices (99)

Reference guide for that technology:

- **Bot:** Python/async best practices
- **API:** FastAPI/Pydantic best practices
- **Web:** React/TypeScript best practices

---

## Tips & Tricks

### ✅ DO's

- ✅ Keep conversations open across multiple prompts
- ✅ Upload complete source code for accurate analysis
- ✅ Run master instruction first, then prompts
- ✅ Tailor review path to your needs
- ✅ Save outputs to organized folders
- ✅ Run Final Consolidation to summarize
- ✅ Use Implementation Roadmap for planning

### ❌ DON'Ts

- ❌ Don't run prompts in multiple separate conversations
- ❌ Don't skip master instructions
- ❌ Don't upload incomplete code
- ❌ Don't ignore Critical/High severity findings
- ❌ Don't skip Final Consolidation for full reviews
- ❌ Don't try all packages simultaneously (too much)

---

## Common Use Cases

### "Is this production-ready?"

→ Run [Full-Stack Review](#full-stack-system-review)  
→ Focus on: Security, Testing, Error Handling

### "Find all security issues"

→ Run [Security-First Review](#security-first-review)  
→ Focus on: Prompts 4, 8, and 6 across all packages

### "Can this handle 1000s of users?"

→ Run [Performance Review](#performance-review)  
→ Focus on: Scalability, concurrency, database queries

### "What's the code quality?"

→ Run Prompt 10 from each package  
→ Focus on: Code Quality, Testing, Best Practices

### "Is the API design good?"

→ Run API Prompts 1-5  
→ Focus on: Architecture, Endpoints, Models, Security

### "How do the three parts work together?"

→ Run [Integration Point Review](#integration-point-review)  
→ Focus on: Bot-API communication, API-Web integration

---

## Output Organization

After running reviews, organize outputs like this:

```
docs/
├── bot-reviews/
│   ├── architecture.md
│   ├── trading-logic.md
│   ├── indicators.md
│   ├── security.md
│   ├── performance.md
│   ├── testing.md
│   ├── consolidation.md
│   └── roadmap.md
├── api-reviews/
│   ├── architecture.md
│   ├── endpoints.md
│   ├── models.md
│   ├── security.md
│   ├── websocket.md
│   ├── error-handling.md
│   ├── testing.md
│   ├── consolidation.md
│   └── roadmap.md
├── web-reviews/
│   ├── architecture.md
│   ├── api-integration.md
│   ├── state-management.md
│   ├── components.md
│   ├── security.md
│   ├── testing.md
│   ├── consolidation.md
│   └── roadmap.md
└── system/
    ├── integration-analysis.md
    ├── full-stack-consolidation.md
    └── master-roadmap.md
```

---

## Support & Customization

### Customizing Reviews

- Start with master instruction
- Skip irrelevant prompts
- Combine related prompts
- Add custom questions for your context

### Getting Better Results

- Upload **all** source code, not just summaries
- Provide **full context** in master instruction
- Use **recent** versions of this prompt suite
- **Run in same conversation** to maintain context

### Extending the Prompts

- Create package-specific variations
- Add compliance-focused prompts
- Add exchange-specific reviews
- Create custom consolidation templates

---

## Version & Updates

**Master Guide Version:** 1.0 (April 2026)

- ✅ Bot Prompts: Complete (19 documents)
- ✅ API Prompts: Complete (16 documents)
- ✅ Web Prompts: Complete (16 documents)
- ✅ Master Guide: Complete (this document)

---

## Quick Links

### Start Here

- [Bot Prompts](./packages/bot/docs/prompts/README.md) — Start with bot review
- [API Prompts](./packages/api/docs/prompts/README.md) — Start with API review
- [Web Prompts](./packages/web/docs/prompts/README.md) — Start with web review

### Workflows

- [Full-Stack Review](#full-stack-system-review) — Review everything
- [Integration Review](#integration-point-review) — Review how components connect
- [Security Review](#security-first-review) — Focus on security

### More Info

- [Review Workflows](#review-workflows) — Different review approaches
- [Getting Started](#getting-started) — Step-by-step guide
- [Prompt Structure](#prompt-structure-all-packages) — What each document contains

---

_For detailed information about any package's prompts, visit that package's README._

**Let's build secure, reliable, production-ready crypto trading software! 🚀**
