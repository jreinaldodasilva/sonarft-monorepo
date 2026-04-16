# Prompt 3 — State Management & Data Flow

**Focus:** State management patterns, data flow, context usage, Redux design  
**Category:** State & Data Management  
**Output File:** `docs/state-management/data-flow.md`  
**Run After:** [01-architecture-structure.md](./01-architecture-structure.md)  
**Time Estimate:** 20-30 minutes  
**Prerequisites:** Understand app architecture from Prompt 1

---

## When to Use This Prompt

Use this prompt to analyze how the app manages state, passes data between components, and maintains data consistency. Review Context API usage, Redux patterns, and data flow.

**Best for:**
- Understanding data flow through components
- Identifying state management issues
- Reviewing component coupling via props
- Planning state refactoring
- Reducing prop drilling

---

## The Prompt

Copy and paste this into your AI chat:

```text
Analyze the sonarftweb state management architecture and how data flows through the application.

Cover the following areas:

### 1. State Management Overview

Identify all state management approaches used:
- **React Local State:** Which components use useState?
- **Context API:** What contexts exist and what do they manage?
- **Redux/Zustand/Recoil:** Is a state library used? How is it configured?
- **URL State:** Is state stored in URL (query params, route params)?
- **Browser Storage:** Is localStorage or sessionStorage used? What's stored?
- **Server Cache:** Is there a caching layer for API responses?
- **Global vs Local:** What is global state vs component-local state?

### 2. Global State Inventory

If using global state (Redux, Context, etc.), document:
- **Redux Store Structure:** If Redux is used, map the store shape
- **Contexts:** For each Context, what data does it provide?
- **Providers:** How are providers organized and nested?
- **Selectors:** Are selectors used to access state?
- **Actions/Reducers:** How are state updates handled?

Create a table for each global state:

| State Name | Type | Purpose | Data | Updated From |
|------------|------|---------|------|--------------|
| | | | | |

### 3. Data Flow Analysis

Trace data flow for key features:
- **Bot Management:** How does bot data flow from API to UI?
- **Indicators:** How are indicator configurations stored and updated?
- **Trading Parameters:** How are parameters configured and persisted?
- **Real-time Prices:** How are WebSocket prices integrated into state?
- **User Settings:** How are user preferences stored?

For each flow:
- Where does data originate?
- How does it get to components that need it?
- How is it updated?
- How is it persisted?

### 4. Component Props Analysis

Examine prop drilling:
- **Props patterns:** How are props passed through component trees?
- **Prop drilling:** How deep does prop passing go (max levels)?
- **Unnecessary props:** Are components receiving unused props?
- **Alternative approaches:** Could Context or a state library reduce drilling?
- **Prop interface design:** Are props well-defined and documented?

### 5. Context Usage

If using React Context, analyze:
- **Context creation:** How are contexts created?
- **Provider placement:** Where are providers in the component tree?
- **Consumer usage:** How many components consume each context?
- **Context splitting:** Are contexts split appropriately?
- **Unnecessary re-renders:** Does context cause unnecessary re-renders?
- **Composition:** Are context values well-composed?

### 6. Reducer Patterns

If using useReducer or Redux, examine:
- **Action types:** Are action types well-organized?
- **Reducer logic:** Is logic pure and testable?
- **Action creators:** Are action creators used (vs inline objects)?
- **Middleware:** Is middleware used (for side effects, logging, etc.)?
- **Thunks:** Are async actions handled (thunks, sagas, etc.)?
- **Dev tools:** Is Redux DevTools or equivalent available?

### 7. API Data Management

Review how API responses are stored:
- **Normalization:** Is API data normalized or kept flat?
- **Denormalization:** How is denormalized data for UI handled?
- **Cache invalidation:** How is cached data invalidated?
- **Optimistic updates:** Are optimistic updates used?
- **Conflict resolution:** How are conflicts between local and server state resolved?
- **Loading/error states:** How are async states (loading, error) managed?

### 8. Local Storage & Persistence

Analyze persistence:
- **What's stored:** What data is saved to localStorage/sessionStorage?
- **Hydration:** How is state restored from storage on page load?
- **Sync:** How is in-memory state kept in sync with storage?
- **Encryption:** Is sensitive data encrypted?
- **Expiration:** Do stored values expire?

### 9. Real-time Data Integration

Review WebSocket data integration:
- **WebSocket events:** What WebSocket events update state?
- **Event handling:** How are events mapped to state updates?
- **Merging:** How is real-time data merged with existing state?
- **Consistency:** How is consistency maintained with API data?
- **Duplicate handling:** How are duplicate events prevented?

### 10. Performance & Re-renders

Analyze rendering performance:
- **Memoization:** Is useMemo/useCallback used appropriately?
- **Component boundaries:** Are components small enough to not re-render unnecessarily?
- **Selector functions:** Are selectors used to prevent prop changes?
- **Re-render triggers:** What causes re-renders? Are they necessary?
- **Profiling:** Have re-renders been profiled?

### 11. Developer Experience

Review state management usability:
- **Debugging:** How easy is it to debug state?
- **Time-travel debugging:** Is this possible (Redux DevTools)?
- **Logging:** Is state logging available?
- **Testing:** How easy is it to test components with state?
- **Documentation:** Is the state structure documented?

### 12. State Flow Diagram

Create a Mermaid diagram showing:
- Components that manage/consume state
- Data sources (API, localStorage, WebSocket)
- How data flows between them
- Global state containers
- External integrations

### 13. Issue Analysis

Identify potential issues:
- **Prop drilling:** Is it excessive?
- **State duplication:** Is the same data stored in multiple places?
- **Stale state:** Can state become out of sync?
- **Memory leaks:** Are event listeners cleaned up?
- **Untracked mutations:** Is state mutated directly?
```

---

## After Running This Prompt

The AI should produce a document covering:
- **State management architecture**
- **Global state inventory**
- **Data flow diagrams**
- **Props analysis**
- **Context usage patterns**
- **API data management**
- **Real-time data integration**
- **Performance and re-render analysis**
- **Recommendations for improvement**

**Save to:** `docs/state-management/data-flow.md`

**Related Prompts:**
- [02-api-integration.md](./02-api-integration.md) — How API data flows in
- [05-real-time-updates.md](./05-real-time-updates.md) — Real-time data handling
- [08-performance-optimization.md](./08-performance-optimization.md) — Re-render optimization

---

## Key Areas to Focus On

1. **Prop Drilling:** Excessive props passing between components
2. **State Duplication:** Same data stored in multiple places
3. **Context Performance:** Unnecessary re-renders from context changes
4. **Data Consistency:** Real-time vs API data sync issues
5. **Testability:** How easy is testing with current state setup?
