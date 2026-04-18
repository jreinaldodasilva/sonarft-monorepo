# Authentication, Security & Authorization Review Prompt

**Prompt:** 04-authentication-security  
**Time:** 45-60 minutes  
**Output:** Markdown document in `docs/security/`  
**Prerequisites:** [Master Instruction](./00-master-instruction.md)

---

## What This Prompt Does

Analyzes authentication mechanisms, authorization controls, security vulnerabilities, and secret management. You'll get:

- JWT implementation review
- Authorization strategy assessment
- Security vulnerability identification
- Secret/credential management review
- CORS and access control analysis
- Security best practices evaluation

---

## Copy & Paste Into Your AI Chat

```text
# PROMPT 04: Authentication, Security & Authorization Review

Please conduct a comprehensive security review of the sonarft API focusing on authentication, authorization, and access control.

## 1. Authentication Mechanism
Analyze JWT token authentication (core/security.py):
- How are tokens generated? (algorithm, expiration)
- How are tokens validated?
- What claims are included in tokens?
- Is token refresh implemented?
- Are token expirations enforced?
- How are invalid tokens handled?

## 2. Secret Management
Review credential and secret handling:
- Where are secrets stored? (environment variables, .env, hardcoded?)
- Are secrets properly isolated from code?
- How are API keys and passwords managed?
- Is there a secrets rotation mechanism?
- Are database credentials secure?
- Are exchange API keys protected?

## 3. Authorization & Access Control
Analyze endpoint-level access control:
- How are endpoints protected? (require_token, etc.)
- Is role-based access control (RBAC) implemented?
- Can users only access their own data?
- Are there privilege escalation vulnerabilities?
- Is authorization checked consistently across all endpoints?

Example questions:
- Can bot A access bot B's data?
- Can a user modify another user's configuration?
- Are admin-only endpoints properly protected?
- Are there missing authorization checks?

## 4. HTTP Security Headers
Check for security headers:
- CORS configuration (allowed origins, methods, headers)
- Are CORS settings too permissive?
- Are other security headers set? (HSTS, CSP, X-Frame-Options)
- Are headers configured in middleware?

## 5. Input Validation & Injection Prevention
- Are all inputs validated?
- Are there SQL injection vulnerabilities? (if database is used)
- Are there command injection risks? (subprocess calls to bot)
- Are string inputs sanitized?
- Is there rate limiting on authentication endpoints?

## 6. Error Information Disclosure
Check for information leakage in errors:
- Do error responses expose internal details?
- Are stack traces visible to users?
- Do error messages reveal system structure?
- Are authentication failures logged properly without exposing details?

## 7. Password & Token Security
Review password/token handling:
- Are passwords hashed? (if used)
- Is a secure hashing algorithm used? (bcrypt, argon2)
- Are tokens short-lived?
- Are refresh tokens properly managed?
- Is token revocation supported?

## 8. API Key Management (if used)
- How are API keys generated and issued?
- Are API keys rotated?
- Can users regenerate API keys?
- Are rate limits per API key?
- How are old keys invalidated?

## 9. Dependencies & Known Vulnerabilities
- Are there known security vulnerabilities in dependencies?
- Check: cryptography, PyJWT, uvicorn, fastapi
- When were dependencies last updated?
- Are security patches applied?

## 10. Compliance & Standards
- Does the implementation follow JWT best practices?
- Is HTTPS/TLS enforced? (or indicated in documentation)
- Are there GDPR/privacy considerations?
- Does the API meet security compliance requirements?

## 11. Specific Vulnerabilities
Check for common vulnerabilities:
- Authentication bypass: Can endpoints be accessed without tokens?
- Authorization bypass: Can users access unauthorized resources?
- Session fixation: Is session management secure?
- Token tampering: Can tokens be modified?
- Brute force: Is there protection against credential guessing?

## 12. Logging & Monitoring
- Are authentication attempts logged?
- Are authorization failures logged?
- Can suspicious activity be detected?
- Is sensitive data logged? (should not log passwords/tokens)

## 13. Concerns & Recommendations
- List identified vulnerabilities (severity: Low/Medium/High/Critical)
- Provide specific remediation steps
- Suggest security hardening measures
- Rate overall security posture

## Output Format

Generate a Markdown document including:
- Executive Summary
- Security Score Card (what's secure vs. not)
- JWT Implementation Review
- Authorization Matrix (which users can do what)
- Vulnerabilities Found (ranked by severity)
- Recommendations (with code examples)
- Security Hardening Checklist
- Compliance Assessment

Be very specific about vulnerabilities, line numbers, and remediation steps. If you find a critical vulnerability, flag it prominently.
```

---

## Expected Output

A comprehensive security audit that includes:

- Authentication mechanism analysis
- Authorization completeness assessment
- Identified vulnerabilities with severity ratings
- Secret management recommendations
- Security hardening action plan

---

## How to Use the Output

1. Save the generated document to `docs/security/04-authentication-security.md`
2. **CRITICAL:** Address any Critical/High severity findings immediately
3. Plan remediation for identified vulnerabilities
4. Implement additional security controls
5. Establish security testing procedures
6. Share findings with security team

---

## Related Prompts

After this prompt, consider:

- [Prompt 6: Error Handling & Logging](./06-error-handling-logging.md) — Logging for security
- [Prompt 1: Architecture Structure](./01-architecture-structure.md) — Security architecture
- [Prompt 9: Testing & Quality](./09-testing-quality.md) — Security testing

---

_Part of the sonarft API Code Review Prompt Suite_
