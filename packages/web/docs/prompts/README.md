# sonarftweb Code Review & Development Prompt Suite

A comprehensive framework for conducting structured AI-assisted code reviews and development guidance for the sonarftweb cryptocurrency trading client application.

**sonarftweb** is a React-based web client that provides a user interface for the sonarft trading server. It enables traders to:
- Configure and manage multiple trading bots
- Monitor trading activity in real-time
- Set up technical indicators and trading parameters
- Execute and simulate trades
- Analyze trading performance and metrics

---

## Quick Navigation

### 🚀 Getting Started
- **New to this suite?** Start with [Quick Start Guide](./00-quick-start-guide.md)
- **Want context?** Read [Master Instruction](./00-master-instruction.md) first

### 📋 Choose Your Review Path

| Your Goal | Time | Path |
|-----------|------|------|
| Quick health check | 30 min | Quick Audit |
| Comprehensive review | 2-3 hours | Complete Audit |
| Production deployment | 4-5 hours | Production Ready |
| Specific area review | 30-60 min | Pick individual prompts |

### 🔍 Individual Prompts by Category

**Foundation (Read First)**
- [Master Instruction](./00-master-instruction.md) — Shared context
- [Quick Start Guide](./00-quick-start-guide.md) — How to use this suite

**UI & Component Architecture**
- [01-architecture-structure.md](./01-architecture-structure.md) — React app structure, components, and modules
- [04-ui-component-design.md](./04-ui-component-design.md) — Component design patterns and reusability

**Client-Server Integration**
- [02-api-integration.md](./02-api-integration.md) — sonarft API communication and HTTP integration
- [05-real-time-updates.md](./05-real-time-updates.md) — WebSocket integration and real-time data

**State & Data Management**
- [03-state-management.md](./03-state-management.md) — State management, data flow, and context providers

**Security & Configuration**
- [06-authentication-security.md](./06-authentication-security.md) — Client-side security, auth tokens, and data protection
- [07-trading-interface-ux.md](./07-trading-interface-ux.md) — Trading UI patterns, user experience, and interaction design

**Performance & Quality**
- [08-performance-optimization.md](./08-performance-optimization.md) — React optimization, bundle size, and performance metrics
- [09-testing-quality.md](./09-testing-quality.md) — Testing strategy, unit/integration tests, and test coverage
- [10-code-quality-javascript.md](./10-code-quality-javascript.md) — JavaScript best practices, code organization, and maintainability

**Post-Review Documents**
- [11-final-consolidation.md](./11-final-consolidation.md) — Executive summary of all findings
- [12-implementation-roadmap.md](./12-implementation-roadmap.md) — Prioritized action items and improvement plan
- [99-best-practices.md](./99-best-practices.md) — React and JavaScript best practices reference

---

## How to Use This Suite

### Step 1: Prepare Your AI Chat
1. Start a new conversation with your AI (Claude, ChatGPT, etc.)
2. Paste the [Master Instruction](./00-master-instruction.md)
3. Wait for AI to acknowledge

### Step 2: Upload the Codebase
Upload sonarftweb source files:
- All React components (src/components/)
- Utility files (src/utils/)
- Hook files (src/hooks/)
- Page files (src/pages/)
- Configuration files (package.json, etc.)
- CSS/styling files

### Step 3: Run a Specific Prompt
1. Go to the prompt file you want (e.g., 01-architecture-structure.md)
2. Copy the prompt text
3. Paste into your AI chat
4. AI generates documentation

### Step 4: Save Output
Each prompt specifies output location. Organize in `docs/` folder:
```
docs/
├── architecture/
├── components/
├── api-integration/
├── state-management/
├── security/
├── performance/
└── testing/
```

---

## Recommended Review Paths

### 🚀 Quick Audit (30 minutes)
**Best for:** Quick assessment or getting started

1. Read: [Master Instruction](./00-master-instruction.md) (5 min)
2. Run: [10-code-quality-javascript.md](./10-code-quality-javascript.md) (15 min)
3. Review: Code quality findings

**Output:** `docs/code-quality/code-quality.md`

---

### 🔍 Complete System Audit (2-3 hours)
**Best for:** Comprehensive understanding of the system

**Foundation:**
1. [Master Instruction](./00-master-instruction.md) (5 min)

**Run All Prompts in Order:**
1. [01-architecture-structure.md](./01-architecture-structure.md) — Understand component structure
2. [02-api-integration.md](./02-api-integration.md) — Check sonarft API integration
3. [03-state-management.md](./03-state-management.md) — Review state management approach
4. [04-ui-component-design.md](./04-ui-component-design.md) — Assess component patterns
5. [05-real-time-updates.md](./05-real-time-updates.md) — Verify WebSocket integration
6. [06-authentication-security.md](./06-authentication-security.md) — Security audit
7. [07-trading-interface-ux.md](./07-trading-interface-ux.md) — UX/UI review
8. [08-performance-optimization.md](./08-performance-optimization.md) — Performance analysis
9. [09-testing-quality.md](./09-testing-quality.md) — Testing assessment
10. [10-code-quality-javascript.md](./10-code-quality-javascript.md) — Code quality review

**Consolidate:**
11. [11-final-consolidation.md](./11-final-consolidation.md) — Executive summary

---

### 📋 Production Readiness (4-5 hours)
**Best for:** Before deploying to production

Follow **Complete System Audit** (Option 2), then:

12. [12-implementation-roadmap.md](./12-implementation-roadmap.md) — Create action plan
13. [99-best-practices.md](./99-best-practices.md) — Verify best practices compliance

**Deliverables:**
- Complete audit documentation
- Prioritized fix roadmap
- Best practices checklist

---

## Understanding the AI's Role

The AI acts as a **senior frontend engineer, React architect, and code quality reviewer** analyzing for:

| Focus Area | What AI Looks For |
|-----------|------------------|
| **Component Design** | Reusability, prop design, composition patterns |
| **State Management** | Data flow, context usage, Redux/Zustand patterns |
| **API Integration** | sonarft API calls, error handling, retry logic |
| **Real-time Comms** | WebSocket reliability, event handling, reconnection |
| **User Experience** | Accessibility, responsiveness, error feedback |
| **Security** | Auth token handling, XSS prevention, data validation |
| **Performance** | Re-render optimization, code splitting, bundle size |
| **Testing** | Unit tests, integration tests, coverage, mocking |
| **Code Quality** | Readability, naming, documentation, best practices |
| **Accessibility** | WCAG compliance, keyboard navigation, screen readers |

---

## Important Notes

1. **Context Matters:** Always read [Master Instruction](./00-master-instruction.md) before running other prompts
2. **Dependencies:** Some prompts should run in order (see individual files)
3. **Consistency:** When running multiple prompts, maintain terminology and findings consistency
4. **Output Organization:** Save outputs in topic-specific subfolders under `docs/`
5. **Team Usage:** Assign different prompts to team members for parallel reviews

---

## File Structure

```
sonarftweb/docs/prompts/
├── README.md (this file)
├── 00-quick-start-guide.md
├── 00-master-instruction.md
├── 01-architecture-structure.md
├── 02-api-integration.md
├── 03-state-management.md
├── 04-ui-component-design.md
├── 05-real-time-updates.md
├── 06-authentication-security.md
├── 07-trading-interface-ux.md
├── 08-performance-optimization.md
├── 09-testing-quality.md
├── 10-code-quality-javascript.md
├── 11-final-consolidation.md
├── 12-implementation-roadmap.md
└── 99-best-practices.md
```

---

## Version History

- **v1.0** - April 2026 - Initial prompt suite creation for sonarftweb
