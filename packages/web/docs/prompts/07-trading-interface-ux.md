# Prompt 7 — Trading Interface UX/UI & Interaction Design

**Focus:** User experience, trading interface design, accessibility, error handling  
**Category:** User Experience  
**Output File:** `docs/ux/trading-interface.md`  
**Run After:** [01-architecture-structure.md](./01-architecture-structure.md), [04-ui-component-design.md](./04-ui-component-design.md)  
**Time Estimate:** 25-35 minutes  
**Prerequisites:** Understand app structure and components

---

## When to Use This Prompt

Use this prompt to assess the user experience and interface design of sonarftweb. Review accessibility, responsiveness, error handling, and trading-specific UX patterns.

**Best for:**
- UX/UI review
- Improving accessibility
- Enhancing user feedback
- Reviewing error messages
- Optimizing trading workflows

---

## The Prompt

Copy and paste this into your AI chat:

```text
Analyze the user experience and interface design of sonarftweb, focusing on trading workflows and usability.

Cover the following areas:

### 1. Navigation & Information Architecture

Examine how users navigate the app:
- **Navigation structure:** How is the main navigation organized?
- **Page hierarchy:** How are pages organized (home, bots, indicators, etc.)?
- **Breadcrumbs:** Are breadcrumbs provided for context?
- **Menu organization:** Are menus logically organized?
- **Navigation clarity:** Is it clear where users are?
- **Cross-linking:** Can users easily navigate between related pages?

### 2. Trading Workflows

For each major trading workflow, document:
- **Workflow name:** What is the workflow called?
- **Steps:** What are the main steps in the workflow?
- **Entry point:** Where does the user start?
- **Completion:** How does the workflow end?
- **Clarity:** Is it clear what to do at each step?
- **Guidance:** Is there help or guidance?
- **Error recovery:** If something goes wrong, can the user recover?

Example workflows:
- Creating a new bot
- Configuring indicators
- Setting trading parameters
- Starting/stopping a bot
- Viewing trading history
- Analyzing performance

### 3. Form Design & Input Validation

Examine forms:
- **Form labels:** Are all inputs clearly labeled?
- **Required fields:** Are required fields marked?
- **Input types:** Are appropriate input types used (number, select, etc.)?
- **Validation:** When is validation done (real-time vs submit)?
- **Error messages:** Are validation errors clear and helpful?
- **Autocomplete:** Is autocomplete/suggestions provided?
- **Default values:** Are sensible defaults provided?
- **Form state:** Are users prevented from submitting invalid forms?

### 4. Error Handling & User Feedback

Review error communication:
- **Error visibility:** Are errors shown prominently?
- **Error clarity:** Are error messages understandable?
- **Error context:** Do errors explain what went wrong?
- **Error recovery:** Do errors suggest how to fix the issue?
- **Toast/notifications:** Are there notifications for actions?
- **Loading states:** Are loading states shown clearly?
- **Success feedback:** Is there feedback on successful actions?
- **Timeout messages:** Are timeouts communicated clearly?

Examples:
- API errors (401, 404, 500, etc.)
- Validation errors
- Network errors
- Timeout errors
- Business logic errors (e.g., "insufficient balance")

### 5. Responsiveness & Mobile Design

Examine responsiveness:
- **Desktop layout:** How does the app look on desktop?
- **Tablet layout:** Is the app usable on tablets?
- **Mobile layout:** Is the app mobile-friendly?
- **Responsive components:** Do components adapt to screen size?
- **Touch interactions:** Are mobile touch patterns supported?
- **Viewport meta tag:** Is viewport configured for mobile?
- **Mobile navigation:** How is navigation organized on mobile?

### 6. Accessibility (WCAG Compliance)

Review accessibility:
- **Color contrast:** Is there sufficient color contrast?
- **Font size:** Is text readable (default font size)?
- **Keyboard navigation:** Can the app be used with keyboard only?
- **Focus indicators:** Are focused elements visible?
- **Screen readers:** Are screen readers supported?
- **ARIA labels:** Are ARIA labels used appropriately?
- **Semantic HTML:** Is semantic HTML used?
- **Alt text:** Are images properly described?
- **Heading hierarchy:** Are headings structured correctly?

Identify accessibility issues:
- Links/buttons without clear labels
- Missing focus indicators
- Images without alt text
- Poor color contrast

### 7. Trading-Specific UX Patterns

Examine trading patterns:
- **Price display:** How are prices displayed (real-time updates)?
- **Order confirmation:** How are orders confirmed before execution?
- **Risk warnings:** Are there warnings for risky actions?
- **Account balance:** Is account balance prominently shown?
- **Execution status:** Is execution status clearly shown?
- **Charts/indicators:** How are trading indicators visualized?
- **Performance metrics:** How are trading results shown?

### 8. Data Visualization

Review charts and visualizations:
- **Charts used:** What chart types are used (line, bar, candlestick, etc.)?
- **Readability:** Are charts easy to read and understand?
- **Legends:** Are chart legends clear?
- **Real-time updates:** Do charts update in real-time?
- **Interactivity:** Can users interact with charts (zoom, pan, etc.)?
- **Performance:** Do charts perform well with large datasets?
- **Mobile rendering:** Do charts render properly on mobile?

### 9. Loading & Empty States

Examine loading and empty states:
- **Skeleton screens:** Are skeleton screens used during loading?
- **Loading indicators:** Are loading spinners/progress shown?
- **Empty states:** How are empty result sets shown?
- **Helpful messaging:** Do empty states explain why it's empty?
- **Call-to-action:** Do empty states suggest what to do next?

### 10. Help & Documentation

Review user guidance:
- **Help text:** Is inline help provided?
- **Tooltips:** Are tooltips used for additional context?
- **User guide:** Is there a user guide or documentation?
- **FAQ:** Are FAQs available?
- **Error guidance:** Do errors suggest solutions?
- **Onboarding:** Is there an onboarding flow for new users?

### 11. Performance Perceived by User

Examine user-perceived performance:
- **Page load time:** How long does the app take to load?
- **Interaction responsiveness:** Do clicks feel responsive?
- **Animation smoothness:** Are animations smooth?
- **Perceived performance:** Are there optimistic updates?
- **Progress indication:** Is progress shown for long operations?

### 12. Consistency & Design System

Review design consistency:
- **Design system:** Is there a design system/style guide?
- **Component consistency:** Are components consistent in design?
- **Color scheme:** Is there a consistent color scheme?
- **Typography:** Is typography consistent?
- **Spacing:** Is whitespace/spacing consistent?
- **Interaction patterns:** Are similar actions consistent?

### 13. Internationalization (i18n)

Examine multi-language support:
- **Translation:** Are all strings translatable?
- **Languages supported:** What languages are supported?
- **RTL support:** Is right-to-left text supported?
- **Number formatting:** Are numbers formatted per locale?
- **Currency formatting:** Are currencies formatted correctly?
- **Date formatting:** Are dates formatted per locale?

### 14. Specific Trading UI Elements

For trading-specific elements, assess:
- **Bot management:** How are bots created/edited/deleted?
- **Indicator configuration:** How are indicators configured?
- **Parameter settings:** How are trading parameters set?
- **Strategy selection:** How are strategies chosen?
- **Paper vs live:** How does the user switch between modes?
- **Stop-loss/take-profit:** How are these set?

### 15. Usability Issues Summary

Document identified UX issues:

| Issue | Severity | Description | Impact | Fix |
|-------|----------|-------------|--------|-----|
| | | | | |
```

---

## After Running This Prompt

The AI should produce a document covering:
- **Navigation and information architecture**
- **Trading workflow analysis**
- **Form design and validation**
- **Error handling and user feedback**
- **Accessibility assessment (WCAG)**
- **Responsiveness and mobile**
- **Trading-specific UX patterns**
- **Data visualization**
- **Design consistency**
- **Usability issues and recommendations**

**Save to:** `docs/ux/trading-interface.md`

**Related Prompts:**
- [04-ui-component-design.md](./04-ui-component-design.md) — Component design
- [08-performance-optimization.md](./08-performance-optimization.md) — Performance/perceived speed
- [09-testing-quality.md](./09-testing-quality.md) — User flow testing

---

## Critical UX Areas

1. **Error Messages:** Clear, actionable error feedback
2. **Accessibility:** WCAG AA compliance minimum
3. **Mobile Responsiveness:** Should work on mobile
4. **Loading States:** Should show loading/progress
5. **Trading Safety:** Confirmations for risky actions
