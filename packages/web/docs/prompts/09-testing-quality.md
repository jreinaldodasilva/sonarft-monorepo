# Prompt 9 — Testing & Quality Assurance

**Focus:** Unit tests, integration tests, test coverage, testing strategy  
**Category:** Testing & Quality  
**Output File:** `docs/testing/test-strategy.md`  
**Run After:** [04-ui-component-design.md](./04-ui-component-design.md), [02-api-integration.md](./02-api-integration.md)  
**Time Estimate:** 25-35 minutes  
**Prerequisites:** Understand components and API integration

---

## When to Use This Prompt

Use this prompt to analyze testing coverage, strategy, and quality practices. Review unit tests, integration tests, and test organization.

**Best for:**
- Improving test coverage
- Establishing testing strategy
- Reviewing test quality
- Planning test improvements
- Understanding test organization

---

## The Prompt

Copy and paste this into your AI chat:

```text
Analyze the testing and quality assurance approach for sonarftweb.

Cover the following areas:

### 1. Testing Framework & Setup

Examine the testing infrastructure:
- **Test runner:** What test runner is used (Jest, Vitest, etc.)?
- **Testing library:** What testing library is used (React Testing Library, Enzyme, etc.)?
- **Configuration:** How is testing configured?
- **Test environment:** What environment do tests run in (jsdom, etc.)?
- **Setup/teardown:** Are there global setup/teardown hooks?
- **CI/CD integration:** Are tests run in CI/CD?

### 2. Unit Test Coverage

Document unit test coverage:
- **Coverage percentage:** What's the overall test coverage?
- **Coverage by component:** Which components have tests? Which don't?
- **Coverage by file:** What files have high/low coverage?
- **Coverage report:** How is coverage measured/reported?
- **Coverage requirements:** Are there minimum coverage requirements?

Create a table:

| File/Component | Lines | Branches | Functions | Statements |
|---|---|---|---|---|
| | | | | |

### 3. Component Tests

Examine component testing:
- **Component test count:** How many components have tests?
- **Test types:** What types of tests (snapshot, behavioral, etc.)?
- **Test quality:** Are tests testing behavior or implementation?
- **Mock dependencies:** How are dependencies mocked?
- **Props testing:** Do tests cover different prop combinations?
- **Edge cases:** Are edge cases tested?

### 4. Integration Tests

Review integration testing:
- **Integration test coverage:** What workflows have integration tests?
- **Test scope:** What do integration tests test?
- **API mocking:** How are API calls mocked?
- **WebSocket testing:** Are WebSocket interactions tested?
- **User flow testing:** Are user workflows tested end-to-end?

Example test scenarios:
- Login flow
- Create bot flow
- Configure indicator flow
- Execute trade flow
- Real-time data updates

### 5. API/Service Tests

Examine API testing:
- **Service layer tests:** Are API calls tested?
- **Mock API:** What's used to mock the API (MSW, etc.)?
- **Request testing:** Are request format and content tested?
- **Response testing:** Are responses validated?
- **Error testing:** Are API errors tested?
- **Authentication testing:** Is auth flow tested?

### 6. Hook Tests

Review custom hook testing:
- **Hook coverage:** How many custom hooks have tests?
- **Hook test quality:** Are hooks tested in isolation?
- **Effect testing:** Are useEffect behaviors tested?
- **Cleanup testing:** Are cleanup functions tested?
- **State testing:** Are state changes tested?

### 7. Snapshot Testing

Examine snapshot usage:
- **Snapshot count:** How many snapshot tests exist?
- **Snapshot purpose:** What do snapshots test?
- **Snapshot maintenance:** How often are snapshots updated?
- **Snapshot risk:** Are snapshot tests valuable or brittle?
- **Snapshot relevance:** Are snapshot tests testing behavior?

### 8. Test Data & Fixtures

Review test data:
- **Mock data:** Is there mock data for testing?
- **Fixtures:** Are test fixtures provided?
- **Factory functions:** Are factory functions used?
- **Realistic data:** Is test data realistic?
- **Data variety:** Do tests cover different data scenarios?

### 9. Test Organization

Examine test structure:
- **File organization:** How are tests organized?
- **Test naming:** Are test names descriptive?
- **Test grouping:** Are tests grouped logically?
- **Test structure:** Do tests follow AAA (Arrange, Act, Assert)?
- **Duplication:** Is there duplicated test code?

### 10. Error & Edge Case Testing

Review edge case coverage:
- **Error scenarios:** Are error cases tested?
- **Boundary conditions:** Are boundary values tested?
- **Empty states:** Are empty/null values tested?
- **Network errors:** Are network failures tested?
- **Race conditions:** Are async race conditions tested?

### 11. Accessibility Testing

Examine a11y testing:
- **a11y tests:** Are accessibility tests automated?
- **a11y library:** What library is used (jest-axe, etc.)?
- **Manual testing:** Is accessibility manually tested?
- **WCAG coverage:** What WCAG level is covered?
- **Common issues:** Are common a11y issues tested for?

### 12. Visual Regression Testing

Review visual testing:
- **Screenshot tests:** Are visual regression tests used?
- **Visual tool:** What tool is used (Percy, Chromatic, etc.)?
- **Coverage:** What components are visually tested?
- **Maintenance:** How are visual diffs reviewed?

### 13. Performance Testing

Examine performance testing:
- **Bundle size tests:** Are bundle sizes tested/benchmarked?
- **Runtime performance:** Are performance benchmarks tested?
- **Memory tests:** Are memory leaks tested?
- **Render performance:** Are render times tested?

### 14. Test Execution & CI/CD

Review testing in CI/CD:
- **CI integration:** Are tests run in CI?
- **Test timeout:** What's the test timeout?
- **Parallel execution:** Are tests run in parallel?
- **Execution time:** How long do tests take to run?
- **Coverage reporting:** Is coverage reported in CI?
- **Test reporting:** Are test results reported?

### 15. Testing Issues Summary

Document identified issues:

| Issue | Severity | Description | Impact |
|-------|----------|-------------|--------|
| | | | |

### 16. Testing Recommendations

Provide recommendations for:
- Test coverage improvement
- Test quality improvement
- Testing strategy
- Test organization
- CI/CD improvements
```

---

## After Running This Prompt

The AI should produce a document covering:
- **Testing framework and setup**
- **Test coverage analysis**
- **Component testing strategy**
- **Integration testing coverage**
- **API testing approach**
- **Hook testing**
- **Test data and fixtures**
- **Test organization**
- **Edge case coverage**
- **Accessibility testing**
- **CI/CD testing integration**
- **Recommendations for improvement**

**Save to:** `docs/testing/test-strategy.md`

**Related Prompts:**
- [04-ui-component-design.md](./04-ui-component-design.md) — Component design/testability
- [02-api-integration.md](./02-api-integration.md) — API testing
- [10-code-quality-javascript.md](./10-code-quality-javascript.md) — Code quality

---

## Critical Testing Areas

1. **Coverage:** Aim for 80%+ coverage
2. **Component Tests:** Test behavior, not implementation
3. **API Mocking:** Use proper mocking (MSW, jest.mock)
4. **Integration Tests:** Test user workflows
5. **CI/CD:** Tests must run in CI/CD pipeline
