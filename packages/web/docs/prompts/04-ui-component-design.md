# Prompt 4 — UI Component Design & Reusability

**Focus:** Component architecture, reusability, props design, composition patterns  
**Category:** Components & UI  
**Output File:** `docs/components/design-patterns.md`  
**Run After:** [01-architecture-structure.md](./01-architecture-structure.md)  
**Time Estimate:** 25-35 minutes  
**Prerequisites:** Understand app structure from Prompt 1

---

## When to Use This Prompt

Use this prompt to analyze component design, reusability, and composition patterns. Review how well components are designed for reuse and how well responsibilities are separated.

**Best for:**
- Improving component reusability
- Identifying monolithic components
- Reviewing component prop interfaces
- Planning component library organization
- Understanding composition patterns

---

## The Prompt

Copy and paste this into your AI chat:

```text
Analyze the React component architecture in sonarftweb and how components are designed for reusability.

Cover the following areas:

### 1. Component Inventory

Create a comprehensive list of components:
- **Component name** and file location
- **Type:** Presentational, Container, Hook, etc.
- **Purpose:** What does it do in one sentence
- **Reusability:** Is it reused? How many places?
- **Size:** Approximate lines of code
- **Complexity:** Simple, Medium, Complex

Format as a table:

| Component | Location | Purpose | Reused? | Size | Complexity |
|-----------|----------|---------|---------|------|------------|
| | | | | | |

Focus on major/important components first.

### 2. Presentational vs Container Pattern

Analyze component structure:
- **Container components:** Which components handle logic and API calls?
- **Presentational components:** Which components only receive props and render?
- **Smart/Dumb pattern:** Is this pattern used?
- **Mixed concerns:** Which components mix presentation and logic?
- **Separation quality:** How well are these separated?

### 3. Component Responsibility Analysis

For significant components, document:
- **Single Responsibility Principle:** Does each component have one main job?
- **Mixed concerns:** Does the component handle logic, styling, and rendering?
- **Size:** Is the component too large? Could it be split?
- **Dependencies:** What does it depend on?
- **Reusability:** Could this component be used elsewhere?

Identify components that violate single responsibility:
- Components handling both presentation and business logic
- Components doing API calls and rendering
- Components mixing formatting/layout with logic

### 4. Props Design & Interface

Examine how props are designed:
- **Props definition:** Are PropTypes or TypeScript used?
- **Required vs optional:** Which props are required?
- **Prop drilling:** Are unnecessary props passed through?
- **Props validation:** Is data validated before use?
- **Default props:** Are sensible defaults provided?
- **Props documentation:** Are props documented?
- **Props naming:** Are props named clearly?

Create a table for key components' props:

| Component | Props | Required? | Type | Purpose |
|-----------|-------|-----------|------|---------|
| | | | | |

### 5. Composition Patterns

Analyze how components are composed:
- **Higher-Order Components:** Are HOCs used? Are they necessary?
- **Render Props:** Is this pattern used?
- **Hooks composition:** Are custom hooks used for logic composition?
- **Slot/Children pattern:** Is the children prop used creatively?
- **Compound components:** Are compound component patterns used?
- **Composition vs inheritance:** Is composition preferred?

### 6. Custom Hooks

Document all custom hooks:
- **Hook name** and file location
- **Purpose:** What does it do?
- **Used by:** Which components use it?
- **Dependencies:** What does it depend on?
- **Side effects:** Does it have side effects (API calls, localStorage, etc.)?
- **Cleanup:** Are resources cleaned up properly?
- **Testing:** How easily can it be tested?

Create a table:

| Hook Name | Purpose | Used By | Dependencies | Side Effects |
|-----------|---------|---------|--------------|--------------|
| | | | | |

### 7. Styling Approach

Examine styling:
- **CSS approach:** CSS files, CSS-in-JS, styled-components, Tailwind, etc.?
- **Style organization:** How are styles organized?
- **Component-scoped styles:** Are styles scoped to components?
- **Theme support:** Is there a theme/design token system?
- **Responsive design:** How is mobile responsiveness handled?
- **Style duplication:** Are styles duplicated across components?
- **Dark mode:** Is dark mode supported?

### 8. Reusable Component Library

Identify if there's a component library:
- **Base components:** Are there basic components (Button, Input, etc.)?
- **Compound components:** Are complex components built from simple ones?
- **Component consistency:** Are all components consistent in design?
- **Storybook:** Is Storybook or similar used for documentation?
- **Export organization:** Are components exported clearly?

Document base components:

| Component | Purpose | Props | Customization |
|-----------|---------|-------|----------------|
| | | | |

### 9. Component Lifecycle & Hooks

Analyze lifecycle usage:
- **useEffect:** How is it used? Are dependencies correct?
- **useCallback/useMemo:** When are these used? Are they overused?
- **useRef:** What is stored in refs? Is it necessary?
- **Custom hooks:** What hooks abstract common patterns?
- **Cleanup:** Are effects cleaned up? Are event listeners removed?
- **Dependencies:** Are all dependencies included?

### 10. Form Components

If forms are used, examine:
- **Form handling:** How are forms handled (HTML form, controlled inputs)?
- **Validation:** How is validation done (client-side, server-side)?
- **Error display:** How are validation errors shown?
- **Submit handling:** How are form submissions handled?
- **Input components:** Are there reusable input components?
- **Form state:** How is form state managed?

### 11. Testing & Documentation

Review component testing:
- **Unit tests:** Do components have unit tests?
- **Snapshot testing:** Are snapshots used?
- **Mock data:** Is there mock data for components?
- **Documentation:** Are components documented?
- **Examples:** Are there usage examples?
- **Prop documentation:** Are props documented?

### 12. Code Quality Issues

Identify quality problems:
- **Monolithic components:** Components > 300 lines
- **Prop drilling:** More than 3 levels of prop passing
- **Mixed concerns:** Business logic + rendering mixed
- **Magic strings:** Hard-coded values instead of constants
- **Type safety:** Are types checked (PropTypes/TypeScript)?
- **Naming:** Are component/prop names clear?
- **Comments:** Are complex sections documented?

### 13. Component Architecture Diagram

Create a Mermaid diagram showing:
- Major components and their relationships
- Container vs presentational components
- Custom hooks and what components use them
- Data flow through components
```

---

## After Running This Prompt

The AI should produce a document covering:
- **Component inventory and analysis**
- **Separation of concerns assessment**
- **Props design review**
- **Composition patterns**
- **Custom hooks documentation**
- **Styling approach analysis**
- **Reusability assessment**
- **Testing and quality issues**
- **Recommendations for improvement**

**Save to:** `docs/components/design-patterns.md`

**Related Prompts:**
- [01-architecture-structure.md](./01-architecture-structure.md) — Overall structure
- [08-performance-optimization.md](./08-performance-optimization.md) — Component optimization
- [09-testing-quality.md](./09-testing-quality.md) — Component testing

---

## Key Areas to Focus On

1. **Component Size:** Too-large components that should be split
2. **Reusability:** Components that could be made reusable
3. **Props Design:** Unclear or excessive props
4. **Prop Drilling:** Excessive prop passing through levels
5. **Mixed Concerns:** Logic and presentation in same component
