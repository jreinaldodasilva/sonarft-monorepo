# Prompt 8 — Performance Optimization & Bundle Size

**Focus:** React performance, bundle size, rendering optimization, network efficiency  
**Category:** Performance  
**Output File:** `docs/performance/optimization.md`  
**Run After:** [04-ui-component-design.md](./04-ui-component-design.md), [08-performance-optimization.md](./08-performance-optimization.md)  
**Time Estimate:** 25-35 minutes  
**Prerequisites:** Understand component and state architecture

---

## When to Use This Prompt

Use this prompt to analyze React performance, bundle size, and optimization opportunities. Review rendering bottlenecks and network efficiency.

**Best for:**
- Optimizing app performance
- Reducing bundle size
- Improving load times
- Analyzing rendering performance
- Planning performance improvements

---

## The Prompt

Copy and paste this into your AI chat:

```text
Analyze the performance characteristics of sonarftweb including bundle size, rendering, and network efficiency.

Cover the following areas:

### 1. Bundle Size Analysis

Examine the build output:
- **Total bundle size:** What is the main bundle size?
- **Code splitting:** Are routes/features split into chunks?
- **Vendor bundle:** How large is the vendor code?
- **App code:** How much is application code vs dependencies?
- **CSS size:** How large are CSS bundles?
- **Source maps:** Are source maps included in production?
- **Compression:** Is gzip compression configured?

For major dependencies, document:
- React, React-DOM
- State management (Redux, Context, etc.)
- HTTP client (axios, fetch)
- UI components/libraries
- Other significant packages

Create a table:

| Package | Size (gzipped) | Size (uncompressed) | Importance |
|---------|---|---|---|
| | | | |

### 2. Code Splitting Strategy

Analyze code splitting:
- **Route-based splitting:** Are routes lazy-loaded?
- **Component splitting:** Are large components split?
- **Feature splitting:** Are features split into chunks?
- **Bundle analyzer:** Is webpack-bundle-analyzer used?
- **Dynamic imports:** How are dynamic imports configured?
- **Load performance:** What's the load time impact of splitting?

### 3. React Rendering Performance

Examine rendering:
- **useCallback usage:** Where is useCallback used? Is it necessary?
- **useMemo usage:** Where is useMemo used? Is it necessary?
- **Memo HOC:** Are components wrapped with React.memo?
- **Component memoization:** Which components are memoized?
- **Re-render causes:** What causes unnecessary re-renders?
- **DevTools profiling:** Have re-renders been profiled?

Identify rendering issues:
- Over-memoization
- Ineffective memoization
- Unnecessary re-renders

### 4. State Management Performance

Review state performance:
- **Store structure:** Is the state tree optimally structured?
- **Selector memoization:** Are selectors memoized (reselect)?
- **Context performance:** Does context cause unnecessary re-renders?
- **Subscription patterns:** How are components subscribed to state?
- **Update batching:** Are updates batched?
- **State normalization:** Is state normalized to prevent duplication?

### 5. Network Performance

Analyze network efficiency:
- **API calls:** How many API calls are made on page load?
- **Request size:** How large are request/response payloads?
- **Request waterfall:** Are requests chained (dependent)?
- **Parallel requests:** Are independent requests parallel?
- **Caching:** Is HTTP caching used?
- **Compression:** Are responses gzip compressed?
- **Response time:** What's the average API response time?

### 6. Image & Asset Optimization

Examine images:
- **Image formats:** Are modern formats used (WebP)?
- **Image sizes:** Are images scaled to needed sizes?
- **Lazy loading:** Are images lazy-loaded?
- **SVG vs PNG:** Are SVGs used where appropriate?
- **Asset size:** How large are static assets?
- **Responsive images:** Are multiple sizes provided?

### 7. CSS Performance

Review CSS:
- **CSS size:** How large is the CSS?
- **CSS-in-JS overhead:** What's the runtime cost of styled-components/CSS-in-JS?
- **Unused CSS:** Is there unused CSS?
- **Critical CSS:** Is critical path CSS optimized?
- **Animations:** Are animations GPU-accelerated?
- **Media queries:** Are breakpoints optimized?

### 8. JavaScript Execution

Analyze JavaScript performance:
- **Parsing time:** How long does JS parsing take?
- **Compilation time:** How long does compilation take?
- **Execution time:** How long does execution take?
- **Long tasks:** Are there tasks blocking the main thread > 50ms?
- **Bottlenecks:** Where are the performance bottlenecks?

### 9. Web Vitals

Examine Core Web Vitals:
- **LCP (Largest Contentful Paint):** How long until main content paints?
- **FID (First Input Delay):** How responsive is the app?
- **CLS (Cumulative Layout Shift):** Are there unexpected layout shifts?
- **FCP (First Contentful Paint):** How long until anything paints?
- **TTI (Time to Interactive):** How long until the app is interactive?
- **TTFB (Time to First Byte):** Server response time?

### 10. Real-time Update Performance

Review WebSocket performance:
- **Message handling:** How long to process WebSocket messages?
- **Re-render frequency:** How often do WebSocket updates cause re-renders?
- **Update debouncing:** Are rapid updates debounced?
- **Memory growth:** Does memory grow with WebSocket updates?
- **Disconnection impact:** How does disconnection affect performance?

### 11. Browser DevTools Profiling

Analyze profiling data:
- **Rendering profile:** Are renders slow?
- **JavaScript profile:** Is there slow JS execution?
- **Network profile:** Are there slow network requests?
- **Memory profile:** Is there memory leaks or bloat?
- **CPU usage:** How much CPU is used?

### 12. Third-party Scripts

Examine third-party code:
- **Analytics:** What analytics scripts are loaded?
- **Tracking:** What tracking/monitoring scripts are loaded?
- **Ad networks:** Are ad networks loaded?
- **Third-party impact:** What's the performance impact?
- **Async loading:** Are third-party scripts async loaded?

### 13. Mobile Performance

Review mobile-specific performance:
- **Mobile load time:** How long to load on mobile?
- **Mobile rendering:** Is rendering slow on mobile?
- **Mobile CPU:** Is CPU usage high on mobile?
- **Battery impact:** What's the battery impact?
- **Network impact:** Performance on 4G vs WiFi?

### 14. Performance Monitoring

Examine monitoring:
- **Analytics:** Are performance metrics tracked?
- **Real User Monitoring (RUM):** Is RUM in place?
- **Error tracking:** Are performance errors tracked?
- **Benchmarking:** Are benchmarks established?
- **Alerts:** Are performance regressions alerted?

### 15. Performance Issues Summary

Document identified issues:

| Issue | Category | Severity | Impact | Fix Difficulty |
|-------|----------|----------|--------|----------------|
| | | | | |

Rank by: Critical, High, Medium, Low
```

---

## After Running This Prompt

The AI should produce a document covering:
- **Bundle size analysis**
- **Code splitting strategy**
- **React rendering performance**
- **State management performance**
- **Network efficiency**
- **Web Vitals assessment**
- **Performance bottlenecks**
- **Optimization recommendations**
- **Performance monitoring setup**

**Save to:** `docs/performance/optimization.md`

**Related Prompts:**
- [04-ui-component-design.md](./04-ui-component-design.md) — Component optimization
- [03-state-management.md](./03-state-management.md) — State performance
- [02-api-integration.md](./02-api-integration.md) — API efficiency

---

## Key Performance Areas

1. **Bundle Size:** Keep under 100KB gzipped for main bundle
2. **First Load:** Should be < 3 seconds on 4G
3. **Interaction:** Should be < 100ms for user interactions
4. **Web Vitals:** Should meet Google Core Web Vitals
5. **Memory:** Should not grow significantly over time
