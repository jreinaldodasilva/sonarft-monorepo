---
Prompt ID: 01-WEB-ARCH
Package: web
Category: Architecture
Difficulty: Beginner
Time Estimate: 20-30 minutes
Run After: 00-WEB-MASTER
Can Run In Parallel With: 02-WEB-API
Output Location: docs/architecture/structure.md
Last Updated: July 2025
Status: Complete
---

# Prompt 01 — Architecture & Project Structure

**Focus:** React app organization, component hierarchy, and module design  
**Category:** Architecture & Design  
**Deliverables:** 8 sections / 10 analysis areas  
**Output File:** `docs/architecture/structure.md`  
**Prerequisites:** Master Instruction + codebase uploaded

---

## What This Prompt Does

Detailed analysis of the React application organization, component hierarchy, and technology stack. Provides:

✅ **Technology Stack Inventory** — Complete dependency analysis (React, Vite, TypeScript)  
✅ **Directory Structure & Module Organization** — How src/, components/, hooks/, pages/ are organized  
✅ **Component Architecture** — Functional vs class, hooks usage, naming conventions  
✅ **Layering & Separation of Concerns** — UI, logic, API, state, and route layers  
✅ **Module Dependency Analysis** — Import graph and circular dependency detection  
✅ **Data Flow Architecture** — How data moves from API/WebSocket through components  
✅ **API Integration Points** — REST and WebSocket communication mapping  
✅ **Architecture Diagram** — Mermaid diagram of component relationships

---

## Related Prompts

Same Package:

- [Prompt 02](./02-api-integration.md) — API integration and server communication
- [Prompt 03](./03-state-management.md) — State management and data flow
- [Prompt 04](./04-ui-component-design.md) — Component design patterns

Cross-Package:

- [API Prompt 01](../../api/docs/prompts/01-architecture-structure.md) — API backend architecture
- [Bot Prompt 01](../../bot/docs/prompts/01-architecture-structure.md) — Trading engine architecture

---

## When to Use This Prompt

Use this prompt to understand the overall React application organization, how components are structured, and the technology stack. **Run this first** as it gives context for all other prompts.

**Best for:**

- Understanding component hierarchy
- Identifying code organization patterns
- Planning refactoring or restructuring
- Onboarding new team members
- Understanding module dependencies

---

## The Prompt

Copy and paste this into your AI chat:

```text
Analyze the sonarftweb React application architecture and explain how the frontend is organized.

Cover the following areas:

### 1. Technology Stack Inventory

List all major dependencies and technologies:
- React version and features used (hooks, context, etc.)
- JavaScript/ES6 version and compatibility
- State management (Redux, Zustand, Context API, etc.)
- HTTP client library (fetch, axios, etc.)
- UI component libraries (if any)
- Styling approach (CSS modules, styled-components, Tailwind, etc.)
- WebSocket library or approach
- Testing framework (Jest, Vitest, etc.)
- Build tool (Create React App, Vite, Webpack, etc.)
- Development server configuration
- Package manager (npm, yarn, pnpm)
- Linting and formatting tools (ESLint, Prettier, etc.)

### 2. Directory Structure & Module Organization

Map the project structure:
- Root-level files and configuration
- src/ directory organization
- components/ structure (how components are grouped)
- pages/ structure (page-level components)
- hooks/ organization (custom React hooks)
- utils/ organization (utilities and helpers)
- styles/ organization (CSS/styling approach)
- constants or config files
- API or service layer organization

For each major directory, describe:
- **Purpose** and what it contains
- **Naming conventions** used
- **Organization principle** (by feature, by type, by domain, etc.)
- **File organization** (component structure within directories)

### 3. Component Architecture

Analyze the component structure:
- **Component types:** Functional vs class components, hooks usage
- **Component organization:** Flat or hierarchical
- **Naming conventions:** Component naming patterns
- **Reusable component library:** Is there a set of reusable UI components?
- **Container vs presentational pattern:** Is this pattern used?
- **Custom hooks:** What custom hooks exist and what do they do?
- **Props design:** How are props defined (PropTypes, TypeScript, etc.)?

Create a table:

| Component | Type | Purpose | Key Props | Reusable? |
|-----------|------|---------|-----------|-----------|
| | | | | |

### 4. Layering & Separation of Concerns

Examine how concerns are separated:
- **UI Layer:** How are presentational components organized?
- **Logic Layer:** Where does business logic live (custom hooks, utils, etc.)?
- **API/Data Layer:** How is sonarft backend communication handled?
- **State Layer:** Where is state managed (local, context, Redux, etc.)?
- **Route Layer:** How is routing/navigation handled?

Is there clear separation or are concerns mixed?

### 5. Module Dependency Analysis

Create a dependency graph:
- What does each major module import?
- Are there circular dependencies?
- What are the key integration points?
- How does the app communicate with sonarft backend?
- Are dependencies injected or hardcoded?

### 6. Data Flow Architecture

Describe how data flows:
- **Initial load:** How does the app initialize and load data?
- **User interactions:** How do user actions trigger API calls?
- **Real-time updates:** How does WebSocket data get integrated?
- **State updates:** How does the app update state?
- **Props drilling:** Is there excessive prop drilling?

Create a diagram showing:
- Major data sources (sonarft backend, local storage, etc.)
- How data flows through components
- Where state lives
- Key integration points

### 7. API Integration Points

Identify all places where the app talks to sonarft:
- **REST endpoints:** What endpoints are called and where?
- **WebSocket events:** What events are listened to?
- **Error handling:** How are API errors handled?
- **Loading states:** How are loading states managed?
- **Authentication:** Where is auth token passed?
- **Data transformation:** Is there any response transformation?

### 8. Code Complexity Hotspots

Identify files with:
- **Highest line count:** List largest component files
- **Most complexity:** Files with complex logic or nesting
- **Most dependencies:** Files that import the most modules
- **Most state management:** Components managing complex state

### 9. Configuration & Constants

Describe:
- **Environment variables:** How are environment-specific settings handled?
- **Constants file:** Is there a centralized constants/config?
- **Feature flags:** Any conditional feature rendering?
- **Theme/styling variables:** How are design tokens managed?

### 10. Architecture Diagram

Create a Mermaid diagram showing:
- Major component groups as boxes
- Data flow between groups
- sonarft backend as external system
- WebSocket vs REST boundaries
- State management layer
```

---

## After Running This Prompt

The AI should produce a document covering:

- **Technology stack summary**
- **Directory structure map**
- **Component organization analysis**
- **Separation of concerns assessment**
- **Dependency analysis**
- **Data flow diagram**
- **Architecture recommendations**

**Save to:** `docs/architecture/structure.md`

**Next Prompts to Run:**

- [02-api-integration.md](./02-api-integration.md) — Understand API communication
- [03-state-management.md](./03-state-management.md) — Understand state design
- [04-ui-component-design.md](./04-ui-component-design.md) — Component patterns
