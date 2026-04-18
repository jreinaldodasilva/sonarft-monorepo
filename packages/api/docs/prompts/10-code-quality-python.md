---
Prompt ID: 10-API-QUALITY
Package: api
Category: Quality
Difficulty: Medium
Time Estimate: 45-60 minutes
Run After: 01-API-ARCH
Can Run In Parallel With: 09-API-TESTING
Output Location: docs/code-quality/code-quality-python.md
Last Updated: April 2026
Status: Complete
---

# Prompt 10 — Code Quality & Python Best Practices Review

**Focus:** Python code quality, style consistency, and maintainability  
**Category:** Code Quality & Best Practices  
**Deliverables:** 10 sections / 12 analysis areas  
**Output File:** `docs/code-quality/code-quality-python.md`  
**Prerequisites:** Master Instruction + Prompt 01 + codebase uploaded

---

## What This Prompt Does

Comprehensive Python code quality analysis with best practices and maintainability evaluation. Provides:

✅ **Code Style & Formatting** — PEP 8 compliance and consistent formatting  
✅ **Naming Conventions** — Clear and consistent naming across functions, classes, variables  
✅ **Type Hints & Type Safety** — Type annotation completeness and mypy compatibility  
✅ **Docstrings & Documentation** — Comprehensive documentation and docstring quality  
✅ **Import Organization** — Proper import ordering and circular import prevention  
✅ **Code Complexity** — Function length and cyclomatic complexity assessment  
✅ **Code Duplication** — Duplicate code identification and utility extraction opportunities  
✅ **Design Patterns & Best Practices** — SOLID principles and appropriate pattern usage  
✅ **Constants & Magic Numbers** — Hard-coded value elimination and constant organization  
✅ **Error Handling** — Exception handling specificity and logging appropriateness  
✅ **Async/Await Best Practices** — Async code correctness and blocking operation prevention  
✅ **Context Managers & Resource Management** — Proper resource cleanup and leak prevention  
✅ **Testing & Testability** — Code structure for easy testing and dependency injection  
✅ **Comments & Clarity** — Comment necessity and code self-documentation  
✅ **Dependencies & Imports** — Dependency minimization and security vulnerability assessment  
✅ **Concerns & Recommendations** — Code smells, anti-patterns, and refactoring suggestions

---

## Related Prompts

Same Package:

- [Prompt 01](./01-architecture-structure.md) — Overall architecture quality
- [Prompt 09](./09-testing-quality.md) — Testing that validates code quality
- [Prompt 03](./03-data-models-validation.md) — Model quality and validation

Cross-Package:

- [Bot Prompt 10](../../bot/docs/prompts/10-code-quality-testing.md) — Bot code quality and testing
- [Web Prompt 10](../../web/docs/prompts/10-code-quality-maintenance.md) — Web code quality and maintenance

---

## Copy & Paste Into Your AI Chat

```text
# PROMPT 10: Code Quality & Python Best Practices Review

Please conduct a comprehensive code quality review of the sonarft API focusing on Python best practices.

## 1. Code Style & Formatting
Review code style consistency:
- Is PEP 8 followed? (line length, indentation, spacing)
- Is there a consistent style across all modules?
- Are there linting tools configured? (flake8, pylint, ruff)
- Is code formatting consistent? (Black, autopep8)
- Are style violations present?

## 2. Naming Conventions
Check naming consistency:
- Are functions, classes, variables named clearly?
- Are constants in UPPER_CASE?
- Are class names in PascalCase?
- Are function/method names in snake_case?
- Are private methods prefixed with underscore?
- Are there any ambiguous names?

## 3. Type Hints & Type Safety
Review type hints:
- Are type hints present?
- Are all function parameters typed?
- Are return types specified?
- Is type hint coverage high?
- Could mypy be used for type checking?
- Are Any types minimized?

## 4. Docstrings & Documentation
Analyze documentation:
- Are docstrings present for modules, classes, functions?
- Are docstring format consistent? (Google, NumPy, etc.)
- Are parameters documented?
- Are return values documented?
- Are examples provided for complex functions?
- Are edge cases documented?

## 5. Import Organization
Review imports:
- Are imports organized correctly? (stdlib, third-party, local)
- Are unused imports removed?
- Are imports at top of file?
- Are circular imports avoided?
- Are star imports avoided?
- Could imports be organized better?

## 6. Code Complexity
Analyze code complexity:
- Are functions too long?
- Are functions doing too much? (Single Responsibility Principle)
- Are there deeply nested conditionals?
- Could complexity be reduced?
- Are there functions over 50 lines? (Consider splitting)

## 7. Code Duplication
Identify duplicated code:
- Is there repeated code across endpoints?
- Could utilities reduce duplication?
- Are there duplicate patterns in error handling?
- Could helper functions be extracted?

## 8. Design Patterns & Best Practices
Check design pattern usage:
- Are appropriate design patterns used?
- Is dependency injection used?
- Are there proper abstractions?
- Is inheritance/composition used appropriately?
- Are there SOLID principle violations?

Example questions:
- Single Responsibility: Does each function do one thing?
- Open/Closed: Can code be extended without modification?
- Liskov Substitution: Are subclasses compatible?
- Interface Segregation: Are interfaces too broad?
- Dependency Inversion: Do high-level modules depend on abstractions?

## 9. Constants & Magic Numbers
Review hard-coded values:
- Are magic numbers defined as constants?
- Are configuration values configurable?
- Are strings duplicated?
- Could constants be organized better?

## 10. Error Handling
Check error handling patterns:
- Are exceptions caught too broadly?
- Are exceptions handled or logged?
- Are there catch-all exception handlers?
- Could error handling be more specific?

## 11. Async/Await Best Practices
Review async code:
- Are async/await used correctly?
- Are there any blocking operations in async code?
- Are there any forgotten await keywords?
- Could more operations be async?
- Are context managers used with async resources?

## 12. Context Managers & Resource Management
Check resource handling:
- Are files/connections closed properly?
- Are context managers used? (with statements)
- Could cleanup be improved?
- Are there resource leaks?

## 13. Testing & Testability
Review code testability:
- Is code easy to test?
- Are dependencies injectable?
- Are there hard-coded dependencies?
- Could code structure improve testability?

## 14. Comments & Clarity
Analyze comments:
- Are there unnecessary comments?
- Are complex algorithms explained?
- Do comments stay in sync with code?
- Could code be clearer to avoid comments?
- Are there TODO/FIXME comments that need resolution?

## 15. Dependencies & Imports
Review external dependencies:
- Are dependencies minimal?
- Are outdated dependencies used?
- Could any dependencies be removed?
- Are there security vulnerabilities?

## 16. Concerns & Recommendations
- Identify code smell and anti-patterns
- Suggest refactoring opportunities
- Recommend style improvements
- Rate severity: Low/Medium/High
- Provide code examples

## Output Format

Generate a Markdown document including:
- Executive Summary
- Code Quality Scorecard
- PEP 8 Compliance Assessment
- Type Hint Coverage Analysis
- Documentation Audit
- Complexity Analysis (function count by complexity)
- Code Duplication Report
- Design Pattern Assessment
- Issues Found (with severity and examples)
- Refactoring Recommendations (with before/after code)
- Python Best Practices Checklist
- Tooling Recommendations (linters, formatters, type checkers)

Be specific about file paths, line numbers, and provide code examples.
```

---

## Expected Output

A comprehensive code quality review that includes:

- Code style and formatting assessment
- Type hint completeness analysis
- Complexity and duplication detection
- Design pattern evaluation
- Specific refactoring recommendations with code examples

---

## How to Use the Output

1. Save the generated document to `docs/code-quality/10-code-quality.md`
2. Set up linting and formatting tools (black, flake8, mypy)
3. Refactor high-complexity functions
4. Add missing type hints
5. Improve documentation and docstrings
6. Extract and reuse duplicated code
7. Establish code quality standards

---

## Related Prompts

After this prompt, consider:

- [Prompt 11: Final Consolidation](./11-final-consolidation.md) — Summary of all reviews
- [Prompt 9: Testing & Quality](./09-testing-quality.md) — Testing coverage
- [Prompt 1: Architecture Structure](./01-architecture-structure.md) — Architecture design

---

_Part of the sonarft API Code Review Prompt Suite_
