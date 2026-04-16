# Quick Start Guide — sonarftweb Code Review Prompts

**When to Use:** First time using this prompt suite?  
**Time to Read:** 5-10 minutes  
**Prerequisites:** Read [Master Instruction](./00-master-instruction.md) first  
**Next Step:** Pick your review path below

---

## What Is This?

This is a suite of **AI-powered code review prompts** designed specifically for the **sonarftweb** cryptocurrency trading client application. Each prompt generates professional documentation covering a specific domain (architecture, API integration, state management, security, performance, etc.).

Unlike sonarft (the backend server), sonarftweb focuses on:
- **React component design** and reusability
- **Client-server communication** (REST API + WebSocket)
- **User interface** and experience
- **Client-side state** management
- **Real-time updates** handling
- **Client-side security** (auth tokens, XSS prevention)
- **Frontend performance** optimization

---

## Three Ways to Use This Suite

### 🚀 Option 1: Quick Audit (30 minutes)
**Best for:** Quick health check or getting started

1. Read: [Master Instruction](./00-master-instruction.md) (5 min)
2. Run: [10-code-quality-javascript.md](./10-code-quality-javascript.md) (15 min)
3. Get quick assessment of code quality and maintainability

**Output:** `docs/code-quality/code-quality.md`

**Why This First:**
- Quick snapshot of overall code health
- Identifies obvious problems
- Takes minimal time
- No prerequisites

---

### 🔍 Option 2: Complete System Audit (2-3 hours)
**Best for:** Comprehensive understanding of the system

**Read Foundation First:**
1. [Master Instruction](./00-master-instruction.md) (5 min)

**Run All Prompts in Order:**
1. [01-architecture-structure.md](./01-architecture-structure.md) — Component structure and organization
2. [02-api-integration.md](./02-api-integration.md) — sonarft server integration
3. [03-state-management.md](./03-state-management.md) — Data flow and state patterns
4. [04-ui-component-design.md](./04-ui-component-design.md) — Component reusability and design
5. [05-real-time-updates.md](./05-real-time-updates.md) — WebSocket integration
6. [06-authentication-security.md](./06-authentication-security.md) — Security audit (CRITICAL)
7. [07-trading-interface-ux.md](./07-trading-interface-ux.md) — UI/UX and user experience
8. [08-performance-optimization.md](./08-performance-optimization.md) — Performance review
9. [09-testing-quality.md](./09-testing-quality.md) — Testing strategy assessment
10. [10-code-quality-javascript.md](./10-code-quality-javascript.md) — Code quality assessment

**Consolidate Results:**
11. [11-final-consolidation.md](./11-final-consolidation.md) — Executive summary

**Outputs:** Complete documentation in `docs/` folder, organized by category

---

### 📋 Option 3: Production Readiness (4-5 hours)
**Best for:** Before deploying to production

Follow **Option 2** (Complete System Audit), then add:

12. [12-implementation-roadmap.md](./12-implementation-roadmap.md) — Action plan for fixes
13. [99-best-practices.md](./99-best-practices.md) — Best practices checklist

**Deliverables:**
- Complete audit documentation
- Prioritized fix roadmap
- Best practices compliance checklist
- Deployment readiness assessment

---

## Choosing Your Path

| Your Goal | Time | Recommended Path | When to Use |
|-----------|------|------------------|------------|
| Quick health check | 30 min | Option 1 | First review, tight timeline |
| Comprehensive review | 2-3 hours | Option 2 | Quarterly reviews, before releases |
| Production deployment | 4-5 hours | Option 3 | Before major production deploys |
| Specific area review | 30-60 min | Pick individual prompts | Focused debugging or feature review |
| Performance issues | 60-90 min | #8 + #10 + #12 | Performance optimization focus |
| Security audit | 60-90 min | #6 + #12 + #99 | Security-focused review |
| New team onboarding | 2+ hours | #1 + #3 + #4 | Help team understand codebase |

---

## How Each Prompt Works

### Step-by-Step Process

1. **Copy the prompt text** from the file you want (e.g., 01-architecture-structure.md)
2. **Paste into your AI chat** (Claude, ChatGPT, etc.)
3. **Upload the sonarftweb codebase** to the AI
4. **Run the prompt** — AI generates documentation
5. **Save output** to the location specified in the prompt

### Key Tips

- **Always start with Master Instruction:** Every prompt assumes you've run the Master Instruction first
- **Use same conversation:** Keep the AI in the same chat session across prompts for consistency
- **Upload once:** Upload the sonarftweb source code once, reuse in multiple prompts
- **Save outputs:** Each prompt generates a file — save it to the location specified
- **Review findings:** Don't just run prompts — read the output and prioritize fixes

---

## Understanding Dependencies

Some prompts should run in a specific order:

**Always First:**
- Read [Master Instruction](./00-master-instruction.md) once

**Architecture Before Details:**
- Run [01-architecture-structure.md](./01-architecture-structure.md) before other prompts
- It gives context for understanding component relationships

**Foundation Prompts (Run These First):**
1. [01-architecture-structure.md](./01-architecture-structure.md) — Overall structure
2. [02-api-integration.md](./02-api-integration.md) — How app talks to backend
3. [03-state-management.md](./03-state-management.md) — How data flows

**Detail Prompts (Can Run After Foundation):**
- [04-ui-component-design.md](./04-ui-component-design.md)
- [05-real-time-updates.md](./05-real-time-updates.md)
- [06-authentication-security.md](./06-authentication-security.md)
- [07-trading-interface-ux.md](./07-trading-interface-ux.md)
- [08-performance-optimization.md](./08-performance-optimization.md)
- [09-testing-quality.md](./09-testing-quality.md)
- [10-code-quality-javascript.md](./10-code-quality-javascript.md)

**Consolidation (Run Last):**
- [11-final-consolidation.md](./11-final-consolidation.md) — After all detail prompts
- [12-implementation-roadmap.md](./12-implementation-roadmap.md) — Action plan
- [99-best-practices.md](./99-best-practices.md) — Reference

---

## Key Differences from sonarft Prompts

sonarftweb is **not** a backend server — it's a **frontend client**. Key differences:

| Aspect | sonarft (Backend) | sonarftweb (Frontend) |
|--------|------------------|----------------------|
| **Language** | Python | JavaScript/React |
| **Focus** | Trading logic, math, exchanges | User interface, UX, components |
| **Concurrency** | Async/await, task management | Event loop, useEffect cleanup |
| **Communication** | FastAPI server, WebSocket | REST + WebSocket client |
| **State** | Database, in-memory state | React Context, hooks, local storage |
| **Testing** | Unit tests, pytest | Jest, React Testing Library |
| **Performance** | CPU, async bottlenecks | Re-renders, bundle size |
| **Security** | API security, secret management | Token storage, XSS prevention |
| **Real-time** | Broadcasts updates | Listens to WebSocket events |

---

## Common Questions

**Q: Do I need to read all prompts?**  
A: No. Option 1 (Quick Audit) is 30 minutes. Option 2 is 2-3 hours. Choose based on your goal.

**Q: Can I run prompts out of order?**  
A: Not recommended. Always run [01-architecture-structure.md](./01-architecture-structure.md) first, as it gives context. Foundation prompts (1-3) should run before details.

**Q: How long does each prompt take to run?**  
A: 15-30 minutes per prompt. Total time depends on codebase size and AI response time.

**Q: What if I don't have all source files?**  
A: Upload what you have. AI will note missing files and work with what's available.

**Q: Can multiple people run prompts?**  
A: Yes! Assign different prompts to different team members and combine results.

**Q: Do I need the sonarft code?**  
A: No. This suite focuses on sonarftweb only. Understanding sonarft helps context, but isn't required.

---

## What Happens Next?

After running prompts:

1. **Review Findings** — Read AI outputs carefully
2. **Prioritize Issues** — Focus on High/Critical severity first
3. **Create Action Items** — Use [12-implementation-roadmap.md](./12-implementation-roadmap.md) for this
4. **Assign Fixes** — Distribute work to team members
5. **Track Progress** — Monitor implementation of recommendations
6. **Re-audit** — Run prompts again after major changes

---

## File Organization

As you run prompts, organize outputs:

```
docs/
├── architecture/
│   └── structure.md (from Prompt 1)
├── api-integration/
│   └── sonarft-integration.md (from Prompt 2)
├── state-management/
│   └── data-flow.md (from Prompt 3)
├── components/
│   └── design-patterns.md (from Prompt 4)
├── real-time/
│   └── websocket-integration.md (from Prompt 5)
├── security/
│   └── auth-and-security.md (from Prompt 6)
├── ux/
│   └── trading-interface.md (from Prompt 7)
├── performance/
│   └── optimization.md (from Prompt 8)
├── testing/
│   └── test-strategy.md (from Prompt 9)
├── code-quality/
│   ├── code-quality.md (from Prompt 10)
│   ├── consolidation.md (from Prompt 11)
│   └── roadmap.md (from Prompt 12)
└── reference/
    └── best-practices.md (from Prompt 99)
```

---

## Next Steps

1. ✅ Read this Quick Start Guide (you're doing it!)
2. 📖 Read [Master Instruction](./00-master-instruction.md)
3. 🚀 Choose your path (Option 1, 2, or 3)
4. 💬 Open your AI chat
5. 📋 Copy the Master Instruction and upload sonarftweb code
6. 📝 Run your chosen prompts

**Ready to start?** Pick your path above and begin!
