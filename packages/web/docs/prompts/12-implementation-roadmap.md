# Prompt 12 — Implementation Roadmap & Action Plan

**Focus:** Prioritized action items, implementation plan, effort estimation  
**Category:** Post-Review Planning  
**Output File:** `docs/code-quality/roadmap.md`  
**Run After:** [11-final-consolidation.md](./11-final-consolidation.md)  
**Time Estimate:** 20-30 minutes  
**Prerequisites:** Have completed final consolidation

---

## When to Use This Prompt

Use this prompt to convert findings from the consolidation into an actionable implementation roadmap with timelines and effort estimates.

**Best for:**
- Creating sprint plans
- Allocating work to team members
- Estimating project timeline
- Justifying engineering time to management
- Tracking progress on improvements

---

## The Prompt

Copy and paste this into your AI chat:

```text
Based on the consolidation findings, create a detailed implementation roadmap for fixing identified issues and improving sonarftweb.

### 1. Quick Wins (1-2 days effort)

List issues that can be fixed quickly:
- Issue description
- Why it's important
- Effort estimate
- Team member recommendation
- Expected completion: This week

Examples:
- Remove unused dependencies
- Fix ESLint/Prettier violations
- Add missing JSDoc comments
- Update outdated package versions
- Fix obvious code smells

### 2. Short Term (1-2 weeks)

List issues for the first sprint:

For each issue:
- **Title:** Clear, actionable title
- **Description:** What needs to be done
- **Why:** Business/technical justification
- **Effort:** Estimate in hours/days
- **Acceptance criteria:** How to know it's done
- **Risk:** Any risks involved
- **Dependencies:** Any dependencies on other work
- **Owner:** Recommended team member
- **Priority:** Critical, High, Medium, Low

Format as a table:

| Issue | Effort | Owner | Priority | Deadline |
|-------|--------|-------|----------|----------|
| | | | | |

### 3. Medium Term (1-3 months)

Larger improvements requiring more coordination:
- Architecture refactoring
- Major performance optimization
- Testing improvements
- Security hardening
- Code quality overhaul

For each:
- Break into sub-tasks
- Estimate total effort
- Identify dependencies
- Recommend sequencing

### 4. Long Term (3-6 months)

Strategic improvements:
- Major refactoring
- Technology upgrades
- Infrastructure improvements
- Process improvements
- Team skill development

### 5. Effort Estimation & Timeline

Create a Gantt-like timeline:

```
Sprint 1 (1-2 weeks): Quick Wins + High Priority
  - Task 1 (2 days)
  - Task 2 (3 days)
  - Task 3 (2 days)

Sprint 2 (2 weeks): Security & Performance
  - Security fixes (5 days)
  - Performance optimization (5 days)

Sprint 3 (2 weeks): Testing & Architecture
  - Add tests (5 days)
  - Refactor components (5 days)

Month 2: Larger improvements
Month 3: Polish and stabilization
```

### 6. Security Issues Action Plan

Priority fixes for security:

For each security issue:
- **Issue:** Clear description
- **Risk:** What could go wrong
- **Fix:** How to fix it
- **Effort:** Time to fix
- **Verification:** How to test the fix
- **Timeline:** When it should be fixed (ASAP for Critical)

### 7. Performance Improvements Plan

For each performance issue:
- **Issue:** What's slow
- **Current:** Current performance metric
- **Target:** Target performance
- **Approach:** How to improve
- **Effort:** Estimated effort
- **Measurement:** How to measure improvement

### 8. Testing Roadmap

Plan to improve test coverage:
- **Current coverage:** Current percentage
- **Target coverage:** Target percentage
- **Coverage gaps:** Where are the gaps
- **Priority areas:** What to test first
- **Effort:** To reach target coverage
- **Timeline:** When to complete

Break into phases:
- Phase 1: Critical paths (1-2 weeks)
- Phase 2: Component tests (1-2 weeks)
- Phase 3: Integration tests (2 weeks)
- Phase 4: Reach target coverage (ongoing)

### 9. Code Quality Improvements

Plan to improve code quality:
- **Linting:** Enforce ESLint rules
- **Formatting:** Enforce Prettier
- **Type safety:** Add TypeScript or PropTypes
- **Documentation:** Add JSDoc
- **Refactoring:** Code cleanup

### 10. Dependencies & Tooling Updates

- **Update critical dependencies:** Timeline
- **Update nice-to-have dependencies:** When
- **Audit for vulnerabilities:** Frequency
- **Tool upgrades:** When and why

### 11. Team Allocation & Capacity

For each phase:
- How many people needed
- What skills required
- Estimated capacity
- Risks to capacity

Example:
```
Sprint 1: 2 people, 80 hours total
- Developer 1: 40 hours (full time)
- Developer 2: 40 hours (full time)
```

### 12. Risk & Mitigation

For each major item:
- What could go wrong?
- How to mitigate?
- Contingency plan?
- Who is responsible?

### 13. Success Criteria

Define how to know the roadmap succeeded:

- Code quality improved from X to Y
- Test coverage improved from X to Y
- Performance improved (specify metrics)
- Security issues fixed: All critical/high
- No regression in functionality
- Team velocity improved

### 14. Communication Plan

How to keep stakeholders informed:
- Weekly status updates
- Monthly progress reports
- Roadmap adjustments
- Risk communication
- Success celebration

### 15. Post-Implementation Review

After each phase:
- Measure against success criteria
- Document lessons learned
- Identify what worked/didn't
- Adjust plan for next phase
- Team retrospective

### 16. Detailed Sprint Plans

Create detailed sprint plans for first 2-3 sprints:

**Sprint 1 Week 1:**
- Monday: Tasks for the week
- Tuesday: Progress check
- Wednesday: Midweek review
- Thursday: Testing/QA
- Friday: Sprint review & retro

For each task:
- Time estimate
- Acceptance criteria
- Dependency chain
- Testing plan

### 17. Contingency & Flex Time

- Buffer time for unknowns (20%)
- How to handle blockers
- Escalation process
- Plan adjustments process
```

---

## After Running This Prompt

The AI should produce a document containing:
- **Quick wins** (1-2 days work)
- **Short-term plan** (1-2 weeks)
- **Medium-term plan** (1-3 months)
- **Long-term plan** (3-6 months)
- **Effort estimation and timeline**
- **Security fixes plan**
- **Performance improvements plan**
- **Testing roadmap**
- **Code quality improvements**
- **Detailed sprint plans**
- **Team capacity and allocation**
- **Risk mitigation**
- **Success criteria**
- **Communication plan**

**Save to:** `docs/code-quality/roadmap.md`

---

## Using the Roadmap

This roadmap serves as:
- **Sprint planning input** for the team
- **Timeline** for stakeholders
- **Work allocation** guide
- **Progress tracking** document
- **Budget/resource** estimation
- **Risk management** tool

---

## Typical Roadmap Phases

**Phase 1: Quick Wins (Week 1-2)**
- 40 hours: Fix critical issues, low-hanging fruit

**Phase 2: Security & Performance (Week 3-6)**
- 80 hours: Address security/performance issues

**Phase 3: Testing & Code Quality (Week 7-10)**
- 80 hours: Improve tests and code

**Phase 4: Architecture (Week 11-16)**
- 120 hours: Major refactoring if needed

**Phase 5: Polish (Week 17+)**
- Ongoing improvements and maintenance
