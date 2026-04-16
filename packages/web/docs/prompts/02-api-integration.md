# Prompt 2 — API Integration & sonarft Communication

**Focus:** REST API usage, HTTP client setup, backend communication patterns  
**Category:** Client-Server Integration  
**Output File:** `docs/api-integration/sonarft-integration.md`  
**Run After:** [01-architecture-structure.md](./01-architecture-structure.md)  
**Time Estimate:** 20-30 minutes  
**Prerequisites:** Understand app architecture from Prompt 1

---

## When to Use This Prompt

Use this prompt to understand how sonarftweb communicates with the sonarft backend server. Review REST API calls, error handling, authentication, and request patterns.

**Best for:**
- Understanding API communication patterns
- Identifying integration issues
- Reviewing error handling
- Checking authentication implementation
- Planning API-related refactoring

---

## The Prompt

Copy and paste this into your AI chat:

```text
Analyze how sonarftweb communicates with the sonarft backend server via REST API and HTTP.

Cover the following areas:

### 1. API Client Setup

Examine the API communication layer:
- **HTTP client:** What library is used (fetch, axios, etc.)?
- **Configuration:** How is the base URL, headers, etc. configured?
- **Interceptors:** Are there request/response interceptors?
- **Default headers:** What headers are set by default?
- **Error handling:** How are HTTP errors caught?
- **Timeout:** Is there a timeout configuration?
- **Retry logic:** Is there automatic retry on failure?

### 2. Authentication & Authorization

Identify auth implementation:
- **Token storage:** Where is the auth token stored (localStorage, sessionStorage, memory, cookies)?
- **Token passing:** How is the token sent with requests (Authorization header, query param, etc.)?
- **Token refresh:** Is there a token refresh mechanism?
- **Session persistence:** How does the app handle auth on page reload?
- **Logout:** How is the token cleared on logout?
- **Protected routes:** How are unauthorized users handled?

### 3. API Endpoint Usage

For each major API endpoint called, document:
- **Endpoint URL/path**
- **HTTP method** (GET, POST, PUT, DELETE, etc.)
- **Which component(s) call it**
- **Request parameters and body** (if applicable)
- **Expected response structure**
- **Error handling**
- **When it's called** (on mount, on user action, etc.)
- **Loading/error state handling**

Create a table:

| Endpoint | Method | Called From | Purpose | Error Handling |
|----------|--------|------------|---------|----------------|
| | | | | |

### 4. Error Handling Patterns

Examine how API errors are handled:
- **HTTP errors:** How are 4xx/5xx errors handled?
- **Network errors:** How are connection failures handled?
- **Validation errors:** How are server validation errors displayed?
- **Error messages:** Are errors shown to the user? How?
- **Retry logic:** Are failed requests retried?
- **Error logging:** Are errors logged or reported?
- **Error boundaries:** Are error boundaries used?

### 5. Request Patterns & Best Practices

Analyze request patterns:
- **Batch requests:** Are multiple requests batched?
- **Request deduplication:** Are duplicate requests prevented?
- **Caching:** Is there any request caching?
- **Request timing:** Are requests throttled or debounced?
- **Cancellation:** Can in-flight requests be cancelled?
- **Race conditions:** Are race conditions possible?

### 6. Response Handling

Examine how responses are processed:
- **Data transformation:** Is response data transformed/normalized?
- **Validation:** Is response data validated?
- **Type checking:** Is response structure verified?
- **Error responses:** How are error responses handled?
- **Pagination:** If data is paginated, how is it handled?
- **Data consistency:** How is consistency maintained across requests?

### 7. Loading & Skeleton States

Review loading state handling:
- **Loading indicators:** Are loading states shown to the user?
- **Skeleton screens:** Are skeleton screens used?
- **Disabled buttons:** Are form buttons disabled during requests?
- **Timeout messages:** How long before a "timed out" message shows?
- **Partial data:** Is partial data shown while loading?

### 8. API Documentation & Constants

Examine how API information is organized:
- **Base URL:** Is it configurable per environment?
- **API constants:** Are endpoints defined as constants?
- **Version handling:** How is the API version handled?
- **Documentation:** Are endpoints documented in code?
- **Mock data:** Is there mock data for testing?

### 9. sonarft-Specific Integration

Review how sonarftweb integrates with sonarft:
- **Bot management endpoints:** How are bots CRUD'd?
- **Indicator configuration:** How are indicators configured?
- **Trading parameters:** How are trading parameters set?
- **Execution endpoints:** How are trades executed?
- **Strategy/search:** How is strategy search configured?
- **Real-time data:** How is real-time market data integrated?

### 10. Security Concerns

Identify potential security issues:
- **Token exposure:** Is the token exposed in logs or errors?
- **Credentials:** Are any credentials passed in URL or logs?
- **CORS:** How is CORS configured?
- **SSL/TLS:** Is HTTPS enforced?
- **Input validation:** Are request parameters validated?
- **Output encoding:** Is response data sanitized?

### 11. Performance Considerations

Review API performance:
- **Request frequency:** Are there unnecessary requests?
- **Bundle size:** How large is the HTTP client library?
- **Compression:** Is gzip compression used?
- **Caching headers:** Are cache headers respected?
- **Waterfall requests:** Are there dependency chains of requests?

### 12. API Integration Diagram

Create a Mermaid diagram showing:
- sonarftweb client as one box
- sonarft backend as another
- Major API endpoints between them
- Direction of data flow
- Where WebSocket fits in
```

---

## After Running This Prompt

The AI should produce a document covering:
- **API client implementation**
- **Authentication approach**
- **Endpoint catalog**
- **Error handling patterns**
- **Request/response patterns**
- **Integration strengths and weaknesses**
- **Security assessment**
- **Performance recommendations**

**Save to:** `docs/api-integration/sonarft-integration.md`

**Related Prompts:**
- [05-real-time-updates.md](./05-real-time-updates.md) — WebSocket integration
- [06-authentication-security.md](./06-authentication-security.md) — Auth security details
- [03-state-management.md](./03-state-management.md) — How API data is managed

---

## Key Areas to Focus On

1. **Authentication:** Ensure auth tokens are handled securely
2. **Error handling:** Verify all error cases are handled
3. **Loading states:** Check that loading/error states are shown to users
4. **Performance:** Look for unnecessary or redundant requests
5. **Type safety:** Ensure response data is validated
