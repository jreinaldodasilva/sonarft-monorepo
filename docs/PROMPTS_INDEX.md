# SonarFT Code Review Prompts — Quick Reference Index

**Purpose:** Find the right prompt for your review task  
**Updated:** July 2025  
**Total Documents:** 49 across all packages

---

## 📍 Where Are The Prompts?

| Package | Location                     | Documents | Focus                                        |
| ------- | ---------------------------- | --------- | -------------------------------------------- |
| **Bot** | `packages/bot/docs/prompts/` | 19        | Trading engine, strategy, indicators         |
| **API** | `packages/api/docs/prompts/` | 16        | Backend service, endpoints, WebSocket        |
| **Web** | `packages/web/docs/prompts/` | 16        | Frontend, React components, state management |

---

## 🎯 Find Your Review Type

### By Review Goal

#### "Is it production-ready?"

- Start: [PROMPTS_MASTER_GUIDE.md](./PROMPTS_MASTER_GUIDE.md#full-stack-system-review)
- Bot: All prompts 1-10 → Consolidation → Roadmap
- API: All prompts 1-10 → Consolidation → Roadmap
- Web: All prompts 1-10 → Consolidation → Roadmap
- 📊 **Time:** 12-16 hours

#### "Find all security issues"

- Bot: [Prompt 8: Security & Trading Risk](../packages/bot/docs/prompts/08-security-risk.md)
- API: [Prompt 4: Authentication & Security](../packages/api/docs/prompts/04-authentication-security.md)
- Web: [Prompt 6: Authentication & Security](../packages/web/docs/prompts/06-authentication-security.md)
- 📊 **Time:** 4-5 hours

#### "Can it scale to thousands of users?"

- Bot: [Prompt 9: Performance & Scalability](../packages/bot/docs/prompts/09-performance-scalability.md)
- API: [Prompt 8: Performance Optimization](../packages/api/docs/prompts/08-performance-optimization.md)
- Web: [Prompt 8: Performance Optimization](../packages/web/docs/prompts/08-performance-optimization.md)
- 📊 **Time:** 4-6 hours

#### "How do the three parts work together?"

- Start: [PROMPTS_MASTER_GUIDE.md](./PROMPTS_MASTER_GUIDE.md#integration-point-review)
- Bot: [Prompt 1: Architecture](../packages/bot/docs/prompts/01-architecture-structure.md) + [Prompt 6: Execution & Exchange](../packages/bot/docs/prompts/06-execution-exchange.md)
- API: [Prompt 1: Architecture](../packages/api/docs/prompts/01-architecture-structure.md) + [Prompt 2: Endpoints](../packages/api/docs/prompts/02-api-endpoints-design.md) + [Prompt 5: WebSocket](../packages/api/docs/prompts/05-websocket-realtime.md)
- Web: [Prompt 2: API Integration](../packages/web/docs/prompts/02-api-integration.md)
- 📊 **Time:** 4-6 hours

#### "Quick 30-minute health check"

- Bot: [Prompt 10: Code Quality & Testing](../packages/bot/docs/prompts/10-code-quality-testing.md)
- API: [Prompt 10: Code Quality Python](../packages/api/docs/prompts/10-code-quality-python.md)
- Web: [Prompt 10: Code Quality JavaScript](../packages/web/docs/prompts/10-code-quality-javascript.md)
- 📊 **Time:** 30 minutes total

---

## 🏗️ By Component/Technology

### Bot (Python Trading Engine)

| Aspect                   | Prompts                                                                                                                                                                                        | Time    |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| **Overall Structure**    | [Arch](../packages/bot/docs/prompts/01-architecture-structure.md)                                                                                                                               | 45 min  |
| **Trading Logic**        | [Engine](../packages/bot/docs/prompts/03-trading-engine-logic.md), [Math](../packages/bot/docs/prompts/04-financial-math.md), [Indicators](../packages/bot/docs/prompts/05-indicator-pipeline.md) | 2 hours |
| **Exchange Integration** | [Execution](../packages/bot/docs/prompts/06-execution-exchange.md)                                                                                                                              | 45 min  |
| **Async & Concurrency**  | [Async](../packages/bot/docs/prompts/02-async-concurrency.md)                                                                                                                                   | 45 min  |
| **Configuration**        | [Config](../packages/bot/docs/prompts/07-configuration-runtime.md)                                                                                                                              | 30 min  |
| **Security**             | [Security](../packages/bot/docs/prompts/08-security-risk.md)                                                                                                                                    | 60 min  |
| **Performance**          | [Performance](../packages/bot/docs/prompts/09-performance-scalability.md)                                                                                                                       | 60 min  |
| **Code Quality**         | [Quality](../packages/bot/docs/prompts/10-code-quality-testing.md)                                                                                                                              | 60 min  |

### API (FastAPI Backend)

| Aspect                 | Prompts                                                                                                                                 | Time      |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| **Overall Structure**  | [Arch](../packages/api/docs/prompts/01-architecture-structure.md)                                                                        | 45 min    |
| **Endpoint Design**    | [Endpoints](../packages/api/docs/prompts/02-api-endpoints-design.md), [Models](../packages/api/docs/prompts/03-data-models-validation.md) | 1.5 hours |
| **Real-Time Data**     | [WebSocket](../packages/api/docs/prompts/05-websocket-realtime.md)                                                                       | 45 min    |
| **Security & Auth**    | [Security](../packages/api/docs/prompts/04-authentication-security.md)                                                                   | 60 min    |
| **Data & Persistence** | [Database](../packages/api/docs/prompts/07-database-persistence.md)                                                                      | 45 min    |
| **Error & Logging**    | [Error Handling](../packages/api/docs/prompts/06-error-handling-logging.md)                                                              | 45 min    |
| **Performance**        | [Performance](../packages/api/docs/prompts/08-performance-optimization.md)                                                               | 60 min    |
| **Testing**            | [Testing](../packages/api/docs/prompts/09-testing-quality.md)                                                                            | 60 min    |
| **Code Quality**       | [Quality](../packages/api/docs/prompts/10-code-quality-python.md)                                                                        | 60 min    |

### Web (React Frontend)

| Aspect                | Prompts                                                                                                                           | Time      |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------- | --------- |
| **Overall Structure** | [Arch](../packages/web/docs/prompts/01-architecture-structure.md)                                                                  | 45 min    |
| **API Integration**   | [API Integration](../packages/web/docs/prompts/02-api-integration.md)                                                              | 60 min    |
| **State Management**  | [State](../packages/web/docs/prompts/03-state-management.md)                                                                       | 45 min    |
| **Components & UI**   | [Components](../packages/web/docs/prompts/04-ui-component-design.md), [UX](../packages/web/docs/prompts/07-trading-interface-ux.md) | 1.5 hours |
| **Real-Time Updates** | [Real-Time](../packages/web/docs/prompts/05-real-time-updates.md)                                                                  | 45 min    |
| **Security**          | [Security](../packages/web/docs/prompts/06-authentication-security.md)                                                             | 60 min    |
| **Performance**       | [Performance](../packages/web/docs/prompts/08-performance-optimization.md)                                                         | 60 min    |
| **Testing**           | [Testing](../packages/web/docs/prompts/09-testing-quality.md)                                                                      | 60 min    |
| **Code Quality**      | [Quality](../packages/web/docs/prompts/10-code-quality-javascript.md)                                                              | 60 min    |

---

## 🎓 By Experience Level

### For New Team Members

1. Read: [PROMPTS_MASTER_GUIDE.md](./PROMPTS_MASTER_GUIDE.md) (10 min)
2. Pick one package:
   - Bot: [Master Instruction](../packages/bot/docs/prompts/00-master-instruction.md) → [Quick Start](../packages/bot/docs/prompts/00-quick-start-guide.md) → [Prompt 1](../packages/bot/docs/prompts/01-architecture-structure.md)
   - API: [Master Instruction](../packages/api/docs/prompts/00-master-instruction.md) → [Quick Start](../packages/api/docs/prompts/00-quick-start-guide.md) → [Prompt 1](../packages/api/docs/prompts/01-architecture-structure.md)
   - Web: [Master Instruction](../packages/web/docs/prompts/00-master-instruction.md) → [Quick Start](../packages/web/docs/prompts/00-quick-start-guide.md) → [Prompt 1](../packages/web/docs/prompts/01-architecture-structure.md)

### For Experienced Developers

1. [PROMPTS_MASTER_GUIDE.md](./PROMPTS_MASTER_GUIDE.md#review-workflows) (5 min)
2. Choose workflow (Single package / Full-stack / Security / Performance)
3. Jump to relevant prompts

### For Technical Leads/Architects

1. [PROMPTS_MASTER_GUIDE.md](./PROMPTS_MASTER_GUIDE.md#full-stack-system-review)
2. Run all 3 packages simultaneously
3. Use [Final Consolidation](../packages/bot/docs/prompts/11-final-consolidation.md) from each
4. Create integrated roadmap

### For Security/Compliance

1. [Security-First Review](./PROMPTS_MASTER_GUIDE.md#security-first-review)
2. Focus on:
   - Bot: [Prompt 8](../packages/bot/docs/prompts/08-security-risk.md)
   - API: [Prompt 4](../packages/api/docs/prompts/04-authentication-security.md)
   - Web: [Prompt 6](../packages/web/docs/prompts/06-authentication-security.md)

---

## 📚 Complete Prompt Index

### Foundation Documents (Read Once)

**Bot Package**

- [Master Instruction](../packages/bot/docs/prompts/00-master-instruction.md)
- [Quick Start Guide](../packages/bot/docs/prompts/00-quick-start-guide.md)

**API Package**

- [Master Instruction](../packages/api/docs/prompts/00-master-instruction.md)
- [Quick Start Guide](../packages/api/docs/prompts/00-quick-start-guide.md)

**Web Package**

- [Master Instruction](../packages/web/docs/prompts/00-master-instruction.md)
- [Quick Start Guide](../packages/web/docs/prompts/00-quick-start-guide.md)

**Monorepo**

- [Master Guide (This Index)](./PROMPTS_MASTER_GUIDE.md)
- [Quick Reference (This File)](./PROMPTS_INDEX.md)

---

### Bot Core Review Prompts (01-10)

1. [Architecture & Project Structure](../packages/bot/docs/prompts/01-architecture-structure.md)
2. [Async Design & Concurrency](../packages/bot/docs/prompts/02-async-concurrency.md)
3. [Trading Engine & Strategy Logic](../packages/bot/docs/prompts/03-trading-engine-logic.md)
4. [Financial Math & Precision](../packages/bot/docs/prompts/04-financial-math.md)
5. [Indicator Pipeline](../packages/bot/docs/prompts/05-indicator-pipeline.md)
6. [Execution & Exchange Integration](../packages/bot/docs/prompts/06-execution-exchange.md)
7. [Configuration & Runtime Environment](../packages/bot/docs/prompts/07-configuration-runtime.md)
8. [Security & Trading Risk](../packages/bot/docs/prompts/08-security-risk.md)
9. [Performance & Scalability](../packages/bot/docs/prompts/09-performance-scalability.md)
10. [Code Quality, Testing & Refactoring](../packages/bot/docs/prompts/10-code-quality-testing.md)

---

### API Core Review Prompts (01-10)

1. [API Architecture & Project Structure](../packages/api/docs/prompts/01-architecture-structure.md)
2. [API Endpoints Design & REST Contract](../packages/api/docs/prompts/02-api-endpoints-design.md)
3. [Data Models & Validation](../packages/api/docs/prompts/03-data-models-validation.md)
4. [Authentication, Security & Authorization](../packages/api/docs/prompts/04-authentication-security.md)
5. [WebSocket Real-Time Data Streaming](../packages/api/docs/prompts/05-websocket-realtime.md)
6. [Error Handling, Logging & Observability](../packages/api/docs/prompts/06-error-handling-logging.md)
7. [Database, Persistence & Data Storage](../packages/api/docs/prompts/07-database-persistence.md)
8. [Performance Optimization & Scalability](../packages/api/docs/prompts/08-performance-optimization.md)
9. [Testing, Quality Assurance & Test Coverage](../packages/api/docs/prompts/09-testing-quality.md)
10. [Code Quality & Python Best Practices](../packages/api/docs/prompts/10-code-quality-python.md)

---

### Web Core Review Prompts (01-10)

1. [Architecture & Structure](../packages/web/docs/prompts/01-architecture-structure.md)
2. [API Integration](../packages/web/docs/prompts/02-api-integration.md)
3. [State Management](../packages/web/docs/prompts/03-state-management.md)
4. [UI Component Design](../packages/web/docs/prompts/04-ui-component-design.md)
5. [Real-Time Updates](../packages/web/docs/prompts/05-real-time-updates.md)
6. [Authentication & Security](../packages/web/docs/prompts/06-authentication-security.md)
7. [Trading Interface & UX](../packages/web/docs/prompts/07-trading-interface-ux.md)
8. [Performance Optimization](../packages/web/docs/prompts/08-performance-optimization.md)
9. [Testing & Quality](../packages/web/docs/prompts/09-testing-quality.md)
10. [Code Quality JavaScript](../packages/web/docs/prompts/10-code-quality-javascript.md)

---

### Summary & Roadmap Documents

**Bot**

- [Final Consolidation](../packages/bot/docs/prompts/11-final-consolidation.md)
- [Implementation Roadmap](../packages/bot/docs/prompts/12-implementation-roadmap.md)
- [Setup & Operations Guide](../packages/bot/docs/prompts/13-setup-operations-guide.md)

**API**

- [Final Consolidation](../packages/api/docs/prompts/11-final-consolidation.md)
- [Implementation Roadmap](../packages/api/docs/prompts/12-implementation-roadmap.md)

**Web**

- [Final Consolidation](../packages/web/docs/prompts/11-final-consolidation.md)
- [Implementation Roadmap](../packages/web/docs/prompts/12-implementation-roadmap.md)

---

### Best Practices References

- [Bot Best Practices](../packages/bot/docs/prompts/99-best-practices.md)
- [API Best Practices](../packages/api/docs/prompts/99-best-practices.md)
- [Web Best Practices](../packages/web/docs/prompts/99-best-practices.md)

---

## ⚡ Quick Links

### Starting Points

- **[Master Guide (Full Overview)](./PROMPTS_MASTER_GUIDE.md)** — Best starting point
- **[This Index](./PROMPTS_INDEX.md)** — Quick reference

### By Package

- **[Bot Prompts Hub](../packages/bot/docs/prompts/README.md)**
- **[API Prompts Hub](../packages/api/docs/prompts/README.md)**
- **[Web Prompts Hub](../packages/web/docs/prompts/README.md)**

### By Review Type

- **[Full-Stack Review](./PROMPTS_MASTER_GUIDE.md#full-stack-system-review)** — Complete system assessment
- **[Security-First Review](./PROMPTS_MASTER_GUIDE.md#security-first-review)** — Security focused
- **[Performance Review](./PROMPTS_MASTER_GUIDE.md#performance-review)** — Scalability focused
- **[Integration Review](./PROMPTS_MASTER_GUIDE.md#integration-point-review)** — Component interaction

---

## 📊 Document Statistics

| Metric                     | Count         |
| -------------------------- | ------------- |
| **Total Prompt Documents** | 49            |
| Bot Prompts                | 19            |
| API Prompts                | 16            |
| Web Prompts                | 16            |
| **Monorepo Guides**        | 2             |
| Master Guide               | 1             |
| Quick Index                | 1 (this file) |
| **Review Paths**           | 5+            |
| Single Package Reviews     | 3             |
| Full-Stack Review          | 1             |
| Integration Review         | 1             |
| Security-First             | 1             |
| Performance-Focused        | 1             |

---

## 🚀 Getting Started in 60 Seconds

**Step 1:** Read [PROMPTS_MASTER_GUIDE.md](./PROMPTS_MASTER_GUIDE.md) (2 min)

**Step 2:** Choose your path:

- Single package? → Go to that package's README
- Everything? → Follow Full-Stack Review section
- Security? → Follow Security-First Review section
- Performance? → Follow Performance Review section

**Step 3:** Start with Master Instruction for your chosen package

**Step 4:** Run prompts in order

**Step 5:** Save outputs and consolidate

---

## 💡 Tips

- ✅ All files are **independent** — pick what you need
- ✅ Each prompt **stands alone** — you don't need all of them
- ✅ Results are **cumulative** — later prompts build on earlier ones
- ✅ **Consolidation** brings everything together
- ✅ **Roadmap** helps prioritize fixes

---

## 📝 Document Structure Reference

Every prompt follows this structure:

```
# Title
- What this prompt does
- Prerequisites
- Prompt text (copy & paste into AI)
- Expected output format
- How to use the output
- Related prompts
```

Every package's README includes:

```
- Quick navigation
- Prompt index by category
- Recommended review paths
- Document organization
- Key features
- How to use each prompt
- Cross-package references
```

---

**Last Updated:** July 2025  
**Version:** 1.0  
**Status:** ✅ Complete

For the comprehensive guide, see [PROMPTS_MASTER_GUIDE.md](./PROMPTS_MASTER_GUIDE.md)
