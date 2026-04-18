# Testing, Quality Assurance & Test Coverage Review Prompt

**Prompt:** 09-testing-quality  
**Time:** 45-60 minutes  
**Output:** Markdown document in `docs/testing/`  
**Prerequisites:** [Master Instruction](./00-master-instruction.md)

---

## What This Prompt Does

Analyzes test coverage, testing strategy, test quality, and QA practices. You'll get:

- Test coverage assessment
- Testing strategy review
- Unit, integration, and end-to-end test analysis
- Test code quality evaluation
- Missing test identification
- Testing best practices recommendations

---

## Copy & Paste Into Your AI Chat

```text
# PROMPT 09: Testing, Quality Assurance & Test Coverage Review

Please review the testing infrastructure and test coverage for the sonarft API.

## 1. Test Structure & Organization
Analyze test organization:
- How are tests organized? (tests/ directory structure)
- Are there separate directories for unit, integration, e2e tests?
- What testing framework is used? (pytest, unittest, etc.)
- Is test configuration documented? (pytest.ini, conftest.py)
- Are there test fixtures and factories?

## 2. Unit Test Coverage
Review unit tests:
- What percentage of code has unit test coverage?
- Which modules are covered? (services, models, utils)
- Which modules are missing tests?
- Are critical functions tested?
- Are edge cases tested? (None, empty lists, negative values)
- Are exceptions tested?

## 3. Integration Tests
Analyze integration testing:
- Are there integration tests?
- Do they test endpoint-to-service integration?
- Do they test database integration?
- Do they test WebSocket integration?
- Are they isolated or using real databases?

## 4. Endpoint Tests
Review API endpoint testing:
- Are all endpoints tested?
- Are different HTTP methods tested?
- Are request validation errors tested?
- Are different response codes tested?
- Are request/response formats tested?

## 5. Authentication & Security Testing
Check security tests:
- Are authenticated endpoints tested with/without tokens?
- Are authorization checks tested?
- Is token expiration tested?
- Are invalid tokens tested?
- Are attack scenarios tested? (SQL injection, etc.)

## 6. Error Handling Testing
Review error scenario testing:
- Are error responses tested?
- Are exception handlers tested?
- Are timeout scenarios tested?
- Are connection failures tested?
- Are invalid inputs tested?

## 7. WebSocket Testing
If WebSocket exists:
- Are WebSocket connections tested?
- Are message formats validated?
- Are connection drop scenarios tested?
- Are multiple clients tested?
- Is message ordering verified?

## 8. Database Testing
Review database test strategy:
- Are database operations tested?
- Is a test database used?
- Is data seeding implemented?
- Are transactions tested?
- Is data cleanup working?

## 9. External Dependency Mocking
Analyze mocking strategy:
- Are external dependencies mocked? (bot engine, exchanges)
- Are mocks realistic?
- Is there test data for mocking?
- Could mocking be improved?

## 10. Test Code Quality
Review test code itself:
- Are tests readable and maintainable?
- Do tests follow DRY principle?
- Are test names descriptive?
- Is there test duplication?
- Could test helpers reduce boilerplate?

## 11. Test Maintainability
Check for test issues:
- Are there flaky tests?
- Are there hardcoded values that might break?
- Is test setup/teardown correct?
- Are tests isolated from each other?
- Could test data be parameterized?

## 12. Performance Testing
Review performance tests:
- Are load tests performed?
- Are concurrency scenarios tested?
- Is memory usage tested?
- Are slow operations identified?

## 13. Continuous Integration
Check CI/CD integration:
- Are tests run in CI/CD? (GitHub Actions, etc.)
- Is coverage reported?
- Do tests block deployment?
- Is there a coverage threshold?

## 14. Test Fixtures & Factories
Review test data management:
- Are there test fixtures?
- Are factories used for complex objects?
- Is test data reusable?
- Is test data realistic?

## 15. Concerns & Recommendations
- Identify untested code areas
- Suggest additional test scenarios
- Recommend testing improvements
- Rate severity: Low/Medium/High
- Provide test code examples

## Output Format

Generate a Markdown document including:
- Executive Summary
- Test Coverage Assessment (by module/percentage)
- Testing Strategy Review
- Coverage Analysis with Mermaid diagram
- Unit Test Review
- Integration Test Review
- Security Test Review
- Issues Found (with severity)
- Missing Test Scenarios (prioritized)
- Recommendations (with code examples)
- Testing Best Practices Guide
- CI/CD Integration Checklist

Be specific about test file names, test functions, and coverage metrics.
```

---

## Expected Output

A comprehensive testing review that includes:

- Test coverage analysis
- Testing strategy assessment
- Identified gaps in test coverage
- Test code quality evaluation
- Recommendations for improving tests

---

## How to Use the Output

1. Save the generated document to `docs/testing/09-testing-quality.md`
2. Implement missing unit tests
3. Add integration tests for critical paths
4. Improve test coverage for security-critical code
5. Establish automated testing in CI/CD
6. Set coverage thresholds and monitor

---

## Related Prompts

After this prompt, consider:

- [Prompt 10: Code Quality Python](./10-code-quality-python.md) — Code organization and quality
- [Prompt 4: Authentication & Security](./04-authentication-security.md) — Security testing
- [Prompt 8: Performance Optimization](./08-performance-optimization.md) — Performance testing

---

_Part of the sonarft API Code Review Prompt Suite_
