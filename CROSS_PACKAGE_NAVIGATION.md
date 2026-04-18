# 📊 Prompt Suite Cross-Package Navigation Guide

**Purpose:** Help you understand how all 49 prompt files across bot, API, and web packages work together  
**Updated:** Current session  
**For:** Code reviewers using AI assistants for comprehensive analysis

---

## Package Overview

| Package | Focus                                     | Files    | Time    | Best For                                        |
| ------- | ----------------------------------------- | -------- | ------- | ----------------------------------------------- |
| **Bot** | Trading logic, indicators, execution      | 17 files | 4-6 hrs | Understanding trading bot architecture & safety |
| **API** | Backend, endpoints, data models, security | 15 files | 2-3 hrs | Reviewing FastAPI service layer                 |
| **Web** | Frontend, UI components, user experience  | 15 files | 2-3 hrs | Reviewing React/TypeScript UI                   |

---

## Execution Paths by Goal

### Goal: Fast Security Audit (45 minutes)

**Start:** Any package

1. Read Master Instruction (5 min)
2. Run Prompt 04 — Security/Auth (25 min)
3. Read findings and remediate

**Files:**

- API: `04-authentication-security.md`
- Bot: `08-security-risk.md`
- Web: `04-security-privacy.md`

---

### Goal: Review Full Trading Stack (6-8 hours)

**Best order: Bot → API → Web**

#### Phase 1: Bot Core (2-3 hours)

Review trading logic and safety-critical components:

1. [Bot 01](../../bot/docs/prompts/01-architecture-structure.md) — Bot architecture
2. [Bot 03](../../bot/docs/prompts/03-trading-engine-logic.md) **CRITICAL** — Trading logic
3. [Bot 04](../../bot/docs/prompts/04-financial-math.md) **CRITICAL** — Math accuracy
4. [Bot 05](../../bot/docs/prompts/05-indicator-pipeline.md) — Indicators

**Why this order:** Understand bot → verify correctness → validate calculations

#### Phase 2: API Integration (1-2 hours)

Review how bot communicates with backend:

1. [API 01](../../api/docs/prompts/01-architecture-structure.md) — API design
2. [API 02](../../api/docs/prompts/02-api-endpoints-design.md) — Endpoints for bot control
3. [API 05](../../api/docs/prompts/05-websocket-realtime.md) — Bot → API real-time updates

**Why this order:** Understand API → how bot integrates → real-time communication

#### Phase 3: Web Integration (1-2 hours)

Review how web frontend consumes API:

1. [Web 01](../../web/docs/prompts/01-architecture-structure.md) — Web architecture
2. [Web 05](../../web/docs/prompts/05-real-time-updates.md) — WebSocket client integration
3. [Web 02](../../web/docs/prompts/02-component-structure.md) — Bot status components

**Why this order:** Understand web → real-time display → control UI

---

### Goal: Prepare for Production (8-10 hours)

**Best approach: Complete audits in parallel**

**Run in parallel:**

- [Bot Complete Audit](../../bot/docs/prompts/00-quick-start-guide.md) (follow their recommended path)
- [API Complete Audit](../../api/docs/prompts/00-quick-start-guide.md) (follow their recommended path)
- [Web Complete Audit](../../web/docs/prompts/00-quick-start-guide.md) (follow their recommended path)

**Then:**

1. Consolidate findings from all 3 packages
2. Map cross-package issues (e.g., API security → Web validation)
3. Prioritize fixes by severity and impact
4. Create unified action plan

---

## Related Prompts by Domain

### Security & Authentication

- [API 04](../../api/docs/prompts/04-authentication-security.md) — API auth & JWT
- [Bot 08](../../bot/docs/prompts/08-security-risk.md) — Bot security
- [Web 04](../../web/docs/prompts/04-security-privacy.md) — Web security
- **Connection:** API auth tokens used by web & bot clients

### Real-Time Data Flow

- [Bot 06](../../bot/docs/prompts/06-execution-exchange.md) — Bot trades generated
- [API 05](../../api/docs/prompts/05-websocket-realtime.md) — WebSocket streaming
- [Web 05](../../web/docs/prompts/05-real-time-updates.md) — Real-time UI updates
- **Connection:** Trade → Stream to API → Display on Web

### Data Models & Validation

- [Bot 01](../../bot/docs/prompts/01-architecture-structure.md) — Bot data structures
- [API 03](../../api/docs/prompts/03-data-models-validation.md) — Pydantic models
- [Web 02](../../web/docs/prompts/02-component-structure.md) — Web components
- **Connection:** Bot types → API validation → Web display

### Performance & Scalability

- [Bot 09](../../bot/docs/prompts/09-performance-scalability.md) — Trading throughput
- [API 08](../../api/docs/prompts/08-performance-optimization.md) — API performance
- [Web 08](../../web/docs/prompts/08-performance-optimization.md) — Web performance
- **Connection:** Fast bot → fast API → responsive UI

---

## Prompt ID Mapping

### By Topic

| Topic        | Bot | API | Web |
| ------------ | --- | --- | --- |
| Architecture | 01  | 01  | 01  |
| Data/Models  | 01  | 03  | 02  |
| Security     | 08  | 04  | 04  |
| Real-Time    | 06  | 05  | 05  |
| Performance  | 09  | 08  | 08  |
| Quality      | 10  | 10  | 10  |

### Quick ID Reference

```
Bot:  00-master, 01-arch, 02-async, 03-trading, 04-math, 05-indicators
      06-execution, 07-config, 08-security, 09-perf, 10-quality, 11-consolidate, 12-roadmap, 99-best-practices

API:  00-master, 01-arch, 02-endpoints, 03-models, 04-security, 05-websocket
      06-errors, 07-database, 08-perf, 09-testing, 10-quality, 11-consolidate, 12-roadmap, 99-best-practices

Web:  00-master, 01-arch, 02-components, 03-hooks, 04-security, 05-realtime
      06-styling, 07-testing, 08-perf, 09-integration, 10-quality, 11-consolidate, 12-roadmap, 99-best-practices
```

---

## How to Structure Your Review Session

### For Individual Contributors

1. **Pick a package** based on what you're reviewing
2. **Read the quick-start guide** in that package's `docs/prompts/00-quick-start-guide.md`
3. **Run the recommended path** for your time/goals
4. **Review findings** and create issues/PRs

### For Code Review Teams

1. **Assign packages** (Bot → Team A, API → Team B, Web → Team C)
2. **Each team runs their package's Complete Audit** (parallel)
3. **Meet to consolidate** findings across packages
4. **Prioritize cross-package issues** (e.g., API changes → Web impact)
5. **Create unified action plan**

### For Pre-Deployment Checklist

1. **Run security audits** on all 3 packages (30 min each in parallel = 30 min total)
2. **Run performance reviews** on all 3 packages (1 hr each in parallel = 1 hr total)
3. **Run integration tests** between packages using provided integration prompts
4. **Get sign-off** from security, performance, and product teams
5. **Deploy with confidence**

---

## Interdependencies Summary

### Prompt Execution Dependencies

```
00-master (read once)
    ↓
01-architecture (always first in each package)
    ├→ 02-domain-specific (async/endpoints/components)
    ├→ 03-data-models
    ├→ 04-security ⚠️ CRITICAL
    ├→ 05-integration (websocket/indicators/realtime)
    ├→ 06-execution/styling
    ├→ 07-configuration/testing
    ├→ 08-security/perf/optimization
    ├→ 09-performance/integration
    └→ 10-quality (can run anytime)
    ↓
11-consolidation (after 01-10)
    ↓
12-roadmap (after 11)
```

### Cross-Package Execution Order

```
Bot 01 → Bot 03-04 → API 01 → API 02-05 → Web 01-02 → Web 05
(Bot logic verified) → (API integration) → (Web integration)
```

---

## File Navigation

**All prompts located in:**

- `/packages/bot/docs/prompts/` (17 files)
- `/packages/api/docs/prompts/` (15 files)
- `/packages/web/docs/prompts/` (15 files)

**Master guides:**

- `/docs/PROMPTS_MASTER_GUIDE.md` — Comprehensive overview
- `/docs/PROMPTS_INDEX.md` — Quick reference index
- `/IMPLEMENTATION_GUIDE.md` — Bulk improvement specifications

---

## Key Stats

| Metric                           | Count                               |
| -------------------------------- | ----------------------------------- |
| Total Prompt Files               | 49                                  |
| Core Prompts (01-10)             | 30                                  |
| Summary Prompts (11-12)          | 9                                   |
| Reference (99)                   | 3                                   |
| Master/Quick-Start Files         | 6                                   |
| **Total Review Hours**           | **12-18 (complete) or 4-6 (quick)** |
| **Typical Team Size**            | 3 people (1 per package)            |
| **Recommended Review Frequency** | Before each release, or quarterly   |

---

## Common Questions

**Q: Do I need to run all 49 prompts?**  
A: No. Each package has Quick (30 min), Complete (2-3 hrs), and Full (4-5 hrs) paths. Start with Quick Audit.

**Q: What if I only care about API?**  
A: Run API package prompts only. Start with [API Quick Start](../../packages/api/docs/prompts/00-quick-start-guide.md).

**Q: Which prompts are most critical?**  
A: All Prompt 04 files (Security) are CRITICAL. Run those first.

**Q: Can I run prompts in parallel?**  
A: Yes! All "01" prompts can run in parallel. Check each prompt file for "Can Run In Parallel With" guidance.

**Q: How long does a full code review take?**  
A: 12-18 hours for complete system review with 3 people (Bot/API/Web in parallel), or 6-8 hours alone sequentially.

**Q: Where do AI-generated outputs go?**  
A: Each prompt specifies its output location (usually `docs/[category]/filename.md`). Outputs are meant to be checked into git.

---

**Last Updated:** [Date]  
**Maintained by:** Dev Team  
**Questions?** See the relevant package's README.md
