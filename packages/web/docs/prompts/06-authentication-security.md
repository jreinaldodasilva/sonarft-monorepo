# Prompt 6 — Authentication, Security & Data Protection

**Focus:** Auth tokens, sensitive data handling, XSS prevention, client-side security  
**Category:** Security  
**Output File:** `docs/security/auth-and-security.md`  
**Run After:** [02-api-integration.md](./02-api-integration.md), [01-architecture-structure.md](./01-architecture-structure.md)  
**Time Estimate:** 25-35 minutes  
**Prerequisites:** Understand API and app structure

---

## When to Use This Prompt

Use this prompt to conduct a security audit of the sonarftweb client. Review authentication, data storage, and protection against client-side vulnerabilities.

**Best for:**
- Security audit before production
- Reviewing sensitive data handling
- Checking OWASP vulnerabilities
- Improving authentication flow
- Understanding compliance requirements

---

## The Prompt

Copy and paste this into your AI chat:

```text
Conduct a security audit of sonarftweb focusing on client-side security, authentication, and data protection.

Cover the following areas:

### 1. Authentication & Token Management

Examine auth implementation:
- **Token type:** Is it JWT? Session token? Custom?
- **Token storage:** Where is the token stored (localStorage, sessionStorage, memory, cookie)?
- **Storage security:** Is localStorage vulnerable to XSS?
- **Token lifetime:** How long is the token valid?
- **Refresh mechanism:** How is the token refreshed?
- **Expiration handling:** How is expired token handled?
- **Revocation:** Can tokens be revoked?
- **Secure transmission:** Is the token sent securely (HTTPS, secure cookies)?

### 2. Login/Logout Flow

Review the authentication flow:
- **Login:** How does the user log in? What credentials are sent?
- **Password handling:** Is the password transmitted securely?
- **Token storage:** Where is token stored after login?
- **Session persistence:** How is auth persisted on page reload?
- **Logout:** What happens to the token on logout?
- **Token deletion:** Is the token deleted from storage on logout?
- **Protected endpoints:** Are authenticated endpoints protected?

### 3. Authorization & Access Control

Examine access control:
- **Role-based access:** Are there user roles? How are they enforced?
- **Protected pages:** Which routes/pages require authentication?
- **Unprotected endpoints:** Are any sensitive endpoints unprotected?
- **Client-side checks:** Are there client-side role checks?
- **Server validation:** Does the server validate authorization?
- **Scope/permissions:** What specific permissions are checked?

### 4. HTTPS/TLS

Review secure transport:
- **HTTPS enforcement:** Is HTTPS required?
- **Mixed content:** Are there any HTTP calls from HTTPS pages?
- **Certificate validation:** Is certificate validation done?
- **HSTS:** Is HSTS header set?
- **Secure cookies:** Are auth cookies marked Secure?
- **SameSite cookies:** Is SameSite attribute set correctly?

### 5. XSS (Cross-Site Scripting) Prevention

Analyze XSS vulnerabilities:
- **User input rendering:** How is user input displayed?
- **Sanitization:** Is user input sanitized before rendering?
- **React escaping:** Does React escape user content by default?
- **HTML injection:** Can users inject HTML/JavaScript?
- **DOM manipulation:** Is innerHTML used? Is it safe?
- **Third-party scripts:** Are third-party scripts loaded safely?
- **Content Security Policy:** Is CSP implemented?

Identify potential XSS vulnerabilities:
- Components that render user input
- Use of dangerouslySetInnerHTML
- Unsafe DOM manipulations
- External script loading

### 6. CSRF (Cross-Site Request Forgery) Prevention

Examine CSRF protection:
- **CSRF tokens:** Are CSRF tokens used?
- **Token validation:** How are tokens validated?
- **SameSite cookies:** Is SameSite set to Strict/Lax?
- **Origin checking:** Is Origin header validated?
- **Double-submit cookies:** Is this pattern used?
- **Form submissions:** How are form submissions protected?

### 7. Sensitive Data Handling

Review how sensitive data is handled:
- **API keys:** Are any API keys stored/exposed?
- **Passwords:** Are passwords ever stored in code or logs?
- **Tokens:** Are auth tokens exposed in logs or errors?
- **User data:** What PII is collected and stored?
- **Storage location:** Where is sensitive data stored?
- **Encryption:** Is sensitive data encrypted?
- **Logging:** Are sensitive values logged?
- **Error messages:** Do error messages expose sensitive info?

### 8. Data Privacy

Examine privacy:
- **Data collection:** What user data is collected?
- **Data retention:** How long is data kept?
- **Deletion:** Can users delete their data?
- **Analytics:** What analytics data is tracked?
- **Third-party tracking:** Are there third-party trackers?
- **Privacy policy:** Is there a privacy policy?

### 9. Input Validation & Sanitization

Review input handling:
- **Form validation:** Are form inputs validated?
- **Type checking:** Are input types checked?
- **Range checking:** Are numeric ranges validated?
- **Length validation:** Are string lengths limited?
- **Format validation:** Are formats checked (email, URL, etc.)?
- **Whitelist validation:** Is input validated against whitelist?

### 10. API Communication Security

Examine API security:
- **HTTPS:** Are API calls made over HTTPS?
- **Authentication header:** How is the token sent?
- **Request validation:** Are requests validated on server?
- **Response validation:** Are responses validated on client?
- **Error handling:** Do errors expose sensitive info?
- **Rate limiting:** Is rate limiting implemented?

### 11. Dependency Security

Review dependencies:
- **Vulnerable packages:** Are there known vulnerabilities in dependencies?
- **Package audits:** Is `npm audit` run regularly?
- **Supply chain:** Are package sources trusted?
- **Updates:** Are packages kept up-to-date?
- **License compliance:** Are licenses compatible?

Identify potential issues:
- Outdated packages with known CVEs
- Packages not maintained
- Suspicious packages

### 12. Session Management

Examine session handling:
- **Session storage:** How is session state stored?
- **Session timeout:** Is there a timeout for inactive sessions?
- **Concurrent sessions:** Can users have multiple sessions?
- **Session fixation:** Can sessions be fixed/hijacked?
- **Session revocation:** Can sessions be revoked?

### 13. Compliance & Standards

Review compliance:
- **OWASP Top 10:** Are OWASP vulnerabilities addressed?
- **GDPR:** Is there GDPR compliance (if applicable)?
- **PCI DSS:** Is PCI compliance needed (if handling payments)?
- **SOC 2:** Are there SOC 2 requirements?
- **Data residency:** Are data residency requirements met?

### 14. Security Testing

Examine security testing:
- **Penetration testing:** Has the app been pen-tested?
- **Security tests:** Are there automated security tests?
- **Dependency scanning:** Are dependencies scanned for CVEs?
- **SAST:** Is static analysis security testing used?

### 15. Security Issues Summary

Create a table of identified issues:

| Issue | Severity | Description | Remediation |
|-------|----------|-------------|-------------|
| | | | |

Rank by: Critical, High, Medium, Low
```

---

## After Running This Prompt

The AI should produce a document covering:
- **Authentication and token management**
- **Authorization and access control**
- **HTTPS and transport security**
- **XSS vulnerability analysis**
- **CSRF prevention**
- **Sensitive data handling**
- **Input validation**
- **Dependency security**
- **Compliance assessment**
- **Prioritized security issues and fixes**

**Save to:** `docs/security/auth-and-security.md`

**Related Prompts:**
- [02-api-integration.md](./02-api-integration.md) — API security
- [12-implementation-roadmap.md](./12-implementation-roadmap.md) — Security fixes

---

## Critical Security Areas

1. **Token Storage:** Should auth tokens be in memory, cookies, or localStorage?
2. **XSS Prevention:** All user input must be escaped
3. **HTTPS:** All communication must be encrypted
4. **CSRF Protection:** Forms must be CSRF-protected
5. **Dependency Vulnerabilities:** Keep packages updated
