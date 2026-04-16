# Prompt 10 — Code Quality & JavaScript Best Practices

**Focus:** Code style, best practices, maintainability, code organization  
**Category:** Code Quality  
**Output File:** `docs/code-quality/code-quality.md`  
**Run After:** [Master Instruction](./00-master-instruction.md)  
**Time Estimate:** 20-30 minutes  
**Prerequisites:** Have sonarftweb codebase uploaded

---

## When to Use This Prompt

Use this prompt to assess overall code quality, style, and JavaScript/React best practices. Review maintainability, naming, and documentation.

**Best for:**
- Overall code quality assessment
- Identifying code smell
- Establishing coding standards
- Quick health check
- Code maintainability review

---

## The Prompt

Copy and paste this into your AI chat:

```text
Analyze the code quality of sonarftweb and identify JavaScript/React best practices and code smell.

Cover the following areas:

### 1. Code Style & Consistency

Examine code style:
- **Linter:** Is ESLint configured? What rules?
- **Formatter:** Is Prettier configured?
- **Indentation:** Is indentation consistent?
- **Naming conventions:** Are naming conventions followed?
- **Quote style:** Is quote style consistent?
- **Semicolons:** Is semicolon usage consistent?
- **Line length:** What's the max line length?
- **File organization:** Are files organized consistently?

### 2. JavaScript Best Practices

Review JavaScript usage:
- **var vs let/const:** Is var avoided?
- **Arrow functions:** Are arrow functions used appropriately?
- **Template literals:** Are template literals used for strings?
- **Destructuring:** Is destructuring used where appropriate?
- **Spread operator:** Is spread operator used?
- **Optional chaining:** Is optional chaining (?.) used?
- **Nullish coalescing:** Is nullish coalescing (??) used?
- **Async/await:** Are async/await used (vs callbacks/promises)?

### 3. React Best Practices

Examine React patterns:
- **Functional components:** Are class components used?
- **Hooks:** Are hooks used appropriately?
- **Key prop:** Are keys used in lists?
- **Dependency arrays:** Are dependencies correct in useEffect?
- **Prop types:** Are prop types checked (PropTypes/TypeScript)?
- **Component naming:** Are components named correctly (PascalCase)?
- **Children prop:** Is the children prop used correctly?
- **Fragment shorthand:** Is <></> used instead of <Fragment>?

### 4. Error Handling

Review error handling:
- **Try/catch:** Are try/catch blocks used where appropriate?
- **Error boundaries:** Are error boundaries used?
- **Promise rejection:** Are promise rejections handled?
- **Async errors:** Are async function errors handled?
- **Error logging:** Are errors logged appropriately?
- **User feedback:** Are errors communicated to users?
- **Fallback UI:** Is there fallback UI for errors?

### 5. Code Organization

Examine code organization:
- **File size:** Are files too large (>300 lines)?
- **Function size:** Are functions too large (>50 lines)?
- **Cyclomatic complexity:** Are functions overly complex?
- **Nesting depth:** Is nesting too deep?
- **Import organization:** Are imports organized?
- **Exports:** Are exports organized?
- **Index files:** Are index files used appropriately?

### 6. Naming Conventions

Review naming:
- **Variable names:** Are variables named clearly?
- **Function names:** Do function names describe what they do?
- **Component names:** Are components named correctly?
- **Boolean naming:** Do booleans have is/has prefix?
- **Constant naming:** Are constants in UPPER_CASE?
- **Private methods:** Are private methods prefixed with _?
- **Abbreviations:** Are abbreviations avoided?
- **Magic strings/numbers:** Are magic values extracted to constants?

### 7. Documentation & Comments

Examine documentation:
- **README:** Is there a project README?
- **Code comments:** Are complex sections commented?
- **JSDoc:** Are functions documented with JSDoc?
- **Type documentation:** Are types documented?
- **Inline comments:** Are inline comments helpful (not obvious)?
- **TODO comments:** Are there TODOs? Are they tracked?
- **Documentation freshness:** Is documentation up-to-date?

### 8. Performance Anti-patterns

Identify performance issues:
- **Unnecessary renders:** Are components re-rendering unnecessarily?
- **Missing keys:** Are keys missing in lists?
- **Large bundles:** Are large libraries imported unnecessarily?
- **Inline functions:** Are inline functions used in props?
- **Inline objects:** Are inline objects used in props?
- **Inline styles:** Are inline styles used?
- **Large payloads:** Are API responses large?
- **Polling:** Is polling used when WebSocket would be better?

### 9. Security Anti-patterns

Identify security issues:
- **Hardcoded secrets:** Are secrets hardcoded?
- **Credential exposure:** Are credentials exposed?
- **XSS vulnerabilities:** Are there XSS risks?
- **eval/Function:** Is eval/Function used?
- **Dangerous HTML:** Is dangerouslySetInnerHTML used?
- **Input validation:** Is user input validated?
- **Dependencies:** Are dependencies up-to-date?

### 10. Maintainability Issues

Review maintainability:
- **Dead code:** Is there unused code?
- **Duplication:** Is code duplicated?
- **Tight coupling:** Are modules tightly coupled?
- **Circular dependencies:** Are there circular imports?
- **Mixed concerns:** Are concerns properly separated?
- **Type safety:** Is TypeScript used? How well?
- **Tested:** What code lacks tests?

### 11. Specific Code Smells

Identify code smell:
- **Long functions:** Functions > 50 lines
- **Large files:** Files > 300 lines
- **Long parameter lists:** Functions with > 4 parameters
- **Excessive nesting:** Nesting > 3 levels
- **Boolean blindness:** Using boolean parameters
- **Magic numbers:** Hard-coded numbers without explanation
- **Inconsistent naming:** Variable names don't match purpose
- **Obsolete comments:** Comments that are out of date

### 12. Type Safety (if using TypeScript)

If using TypeScript, examine:
- **Type coverage:** What percentage of code is typed?
- **Any type usage:** Is 'any' overused?
- **Strict mode:** Is strict mode enabled?
- **Type definitions:** Are third-party types available?
- **Type inference:** Are types inferred or explicit?
- **Type errors:** Are there unresolved type errors?

### 13. Build & Tooling

Review tooling:
- **Build configuration:** Is build configured well?
- **Development server:** Is dev server configured?
- **Linting:** Is linting enforced in CI?
- **Testing:** Are tests run automatically?
- **Formatting:** Is formatting automated?
- **Bundling:** Is bundling optimized?
- **Environment variables:** Are env vars handled correctly?

### 14. Code Quality Metrics

Provide metrics where available:
- **Cyclomatic complexity:** Average per function
- **Lines of code:** Total and per file
- **Test coverage:** Overall percentage
- **Dependency count:** Number of dependencies
- **Bundle size:** Gzipped and uncompressed
- **Duplication:** Percentage of duplicated code

### 15. Code Quality Issues Summary

Create a prioritized list:

| Issue | Type | Severity | Occurrences | Remediation |
|-------|------|----------|------------|-------------|
| | | | | |

Rank by: Critical, High, Medium, Low

### 16. Recommendations

Provide actionable recommendations for:
- Code style improvements
- Best practices adoption
- Code organization refactoring
- Documentation improvements
- Testing improvements
- Dependency cleanup
- Security improvements
```

---

## After Running This Prompt

The AI should produce a document covering:
- **Code style and consistency**
- **JavaScript best practices**
- **React best practices**
- **Error handling**
- **Code organization**
- **Naming conventions**
- **Documentation**
- **Performance anti-patterns**
- **Security anti-patterns**
- **Maintainability issues**
- **Code smell identification**
- **Type safety (if TypeScript)**
- **Build and tooling**
- **Metrics and recommendations**

**Save to:** `docs/code-quality/code-quality.md`

**Related Prompts:**
- [09-testing-quality.md](./09-testing-quality.md) — Testing quality
- [01-architecture-structure.md](./01-architecture-structure.md) — Architecture review
- [12-implementation-roadmap.md](./12-implementation-roadmap.md) — Fix roadmap

---

## Critical Quality Areas

1. **No var:** Should use const/let
2. **No console.log:** Should use logger
3. **Error handling:** All async errors must be handled
4. **Type safety:** Use TypeScript or PropTypes
5. **Testing:** Critical code must have tests
