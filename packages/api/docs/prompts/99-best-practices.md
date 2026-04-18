---
Prompt ID: 99-API-BEST
Package: api
Category: Reference
Difficulty: Beginner
Time Estimate: As needed
Run After: None
Can Run In Parallel With: All
Output Location: N/A (reference document)
Last Updated: July 2025
Status: Complete
---

# Python & FastAPI Best Practices Reference Guide

**Reference:** 99-best-practices  
**Purpose:** Guidelines for all reviews  
**Read:** As needed for implementation

---

## FastAPI Best Practices

### API Design

- Use semantic HTTP methods (GET, POST, PUT, DELETE, PATCH)
- Design resources around nouns, not verbs
- Use HTTP status codes correctly
- Implement proper error responses
- Use OpenAPI documentation effectively
- Version your API (/api/v1)
- Use pagination for list endpoints
- Implement proper CORS configuration

### Endpoints & Routing

- Organize routers by resource/feature
- Use path parameters for resource IDs
- Use query parameters for filtering/sorting
- Validate all inputs (Pydantic models)
- Return consistent response formats
- Document endpoint behavior clearly
- Use type hints for request/response models

### Authentication & Security

- Implement JWT authentication properly
- Use short-lived tokens
- Implement token refresh mechanisms
- Never expose secrets in code/logs
- Use HTTPS/TLS in production
- Implement rate limiting
- Validate all user input
- Use CORS carefully
- Add security headers

### Error Handling

- Catch specific exceptions, not generic Exception
- Return meaningful error messages
- Log errors with context
- Don't expose internal details in error responses
- Use custom exception classes
- Implement proper HTTP status codes for errors
- Provide error codes for client-side handling

### Async & Concurrency

- Use async/await for I/O operations
- Never block the event loop
- Use asyncio.gather for parallel operations
- Handle timeouts properly
- Use connection pools for database/HTTP
- Manage resource cleanup with context managers
- Avoid synchronous operations in async handlers

### Data Validation

- Use Pydantic models for request/response
- Validate at the earliest point
- Use field validators for complex rules
- Provide clear validation error messages
- Use type hints throughout
- Leverage Pydantic's field constraints
- Validate external data thoroughly

### Performance

- Implement caching where appropriate
- Use query optimization and indexes
- Implement pagination for large datasets
- Compress responses (gzip)
- Monitor and optimize slow endpoints
- Use connection pooling
- Consider async operations for I/O

### Testing

- Write unit tests for business logic
- Write integration tests for endpoints
- Test error scenarios
- Test authentication/authorization
- Use fixtures and factories
- Mock external dependencies
- Achieve >80% code coverage

### Documentation

- Use OpenAPI/Swagger for auto-documentation
- Include detailed docstrings
- Document authentication requirements
- Provide example requests/responses
- Document error responses
- Keep documentation in sync with code
- Include usage examples

---

## Python Best Practices

### Code Organization

- Follow PEP 8 style guide
- Organize imports (stdlib, third-party, local)
- Use meaningful variable/function names
- Keep functions focused (single responsibility)
- Extract repeated code into helper functions
- Use type hints throughout
- Document complex logic

### Type Hints

- Always provide function parameter types
- Always provide return types
- Use Optional for nullable values
- Use Union for multiple possible types
- Use Generic types appropriately
- Consider using dataclasses for simple objects
- Use mypy or pyright for type checking

### Async Programming

- Use async/await for I/O operations
- Never block the event loop
- Use asyncio primitives correctly
- Handle timeouts and cancellation
- Use context managers for resources
- Document async behavior
- Test async code thoroughly

### Error Handling

- Catch specific exceptions
- Use try/except/finally appropriately
- Don't catch Exception silently
- Log exceptions with context
- Chain exceptions (from e) to preserve context
- Create custom exceptions for specific errors
- Provide meaningful error messages

### Imports

- Use absolute imports
- Avoid circular imports
- Avoid star imports (from x import \*)
- Group imports logically
- Remove unused imports
- Use lazy imports for expensive operations

### Constants & Configuration

- Use UPPER_CASE for constants
- Extract magic numbers to constants
- Externalize configuration (env variables)
- Use configuration classes for validation
- Document configuration options
- Validate configuration at startup

### Documentation

- Use docstrings for modules, classes, functions
- Use consistent docstring format
- Document parameters and return values
- Include examples for complex functions
- Document exceptions that can be raised
- Keep documentation in sync with code

---

## Pydantic Best Practices

### Model Design

- Create separate models for request/response
- Use field validators for business rules
- Use Field() for documentation and constraints
- Avoid deeply nested models
- Extract shared models
- Use enums for restricted values
- Make use of Pydantic v2 features

### Validation

- Validate early and thoroughly
- Use field_validator for complex rules
- Provide clear validation error messages
- Consider validation order (field → model)
- Document validation rules
- Test validation thoroughly

### Serialization

- Control JSON serialization with model_config
- Exclude sensitive fields from responses
- Use aliases for API compatibility
- Implement custom serializers if needed
- Handle datetime formatting consistently
- Test serialization behavior

---

## WebSocket Best Practices

### Connection Management

- Validate authentication on connect
- Track connections efficiently
- Handle disconnections gracefully
- Implement heartbeat/ping-pong
- Clean up stale connections
- Limit concurrent connections
- Log connection events

### Message Handling

- Define clear message protocol
- Validate message format
- Handle message ordering
- Implement backpressure
- Handle slow clients
- Log message events for debugging
- Version protocol for evolution

### Broadcasting

- Broadcast to relevant clients only
- Avoid unnecessary data serialization
- Handle broadcast failures gracefully
- Monitor broadcast performance
- Test with multiple concurrent clients

---

## Testing Best Practices

### Unit Tests

- Test one thing per test
- Use descriptive test names
- Use fixtures for setup/teardown
- Test normal cases, edge cases, errors
- Mock external dependencies
- Aim for >90% coverage of critical code

### Integration Tests

- Test realistic scenarios
- Use test database
- Clean up after tests
- Test error conditions
- Test async behavior
- Document test data setup

### Endpoint Tests

- Test all HTTP methods
- Test valid and invalid inputs
- Test authentication
- Test authorization
- Verify response formats
- Verify status codes
- Test error responses

---

## Security Best Practices

### Authentication

- Use established algorithms (JWT with strong algorithms)
- Keep tokens short-lived
- Implement refresh tokens
- Securely transmit tokens (HTTPS only)
- Never log tokens or passwords
- Use secure hash functions (bcrypt, argon2)

### Secrets Management

- Never hardcode secrets
- Use environment variables
- Use secrets manager in production
- Rotate secrets regularly
- Limit who has access to secrets
- Audit secret usage

### Input Validation

- Validate all inputs
- Use type hints for validation
- Sanitize string inputs
- Check array/object sizes
- Validate numeric ranges
- Prevent injection attacks

### Authorization

- Check permissions before allowing action
- Implement principle of least privilege
- Verify user owns requested resource
- Log authorization failures
- Test authorization thoroughly

---

## Deployment & Operations

### Configuration

- Externalize all configuration
- Use environment-based config
- Validate config at startup
- Document all settings
- Provide sensible defaults
- Don't commit secrets to version control

### Logging

- Log important events (start, stop, errors)
- Include context (request ID, user, etc.)
- Use structured logging format
- Use appropriate log levels
- Don't log sensitive data
- Implement log rotation

### Monitoring

- Monitor key metrics (response time, error rate)
- Set up alerting for errors
- Track database performance
- Monitor resource usage
- Implement health checks
- Use APM tools for production

### Deployment

- Use CI/CD for automated deployment
- Run tests before deployment
- Implement database migrations
- Plan for rollback
- Monitor after deployment
- Document deployment procedures

---

## Common Anti-Patterns to Avoid

### Code Anti-Patterns

- ❌ Large functions (>50 lines)
- ❌ Deeply nested conditionals (>3 levels)
- ❌ Catch Exception without handling
- ❌ Hardcoded values and magic numbers
- ❌ Circular imports
- ❌ Long parameter lists
- ❌ Comments explaining bad code (fix the code instead)

### FastAPI Anti-Patterns

- ❌ Global state in endpoints
- ❌ Blocking operations in async handlers
- ❌ Missing input validation
- ❌ Exposing internal errors to clients
- ❌ Returning HTML from API endpoints
- ❌ Missing authentication on sensitive endpoints
- ❌ No rate limiting on expensive operations

### Security Anti-Patterns

- ❌ Hardcoded passwords/keys
- ❌ No input validation
- ❌ Overly permissive CORS
- ❌ Exposing stack traces
- ❌ Storing passwords in plaintext
- ❌ No authentication/authorization
- ❌ Logging sensitive data

---

## Resources

### Official Documentation

- [FastAPI Official Docs](https://fastapi.tiangolo.com/)
- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [Python Type Hints PEP 484](https://www.python.org/dev/peps/pep-0484/)
- [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)

### Tools & Libraries

- **Linting:** flake8, pylint, ruff
- **Formatting:** black, autopep8
- **Type Checking:** mypy, pyright
- **Testing:** pytest, pytest-asyncio, httpx
- **Security:** bandit, safety
- **Async:** asyncio, aiohttp, httpx
- **API:** FastAPI, Uvicorn, Pydantic

### Security Resources

- OWASP Top 10
- OWASP API Security Top 10
- FastAPI Security Documentation
- JWT.io Best Practices

---

## Version History

- **v1.0** (July 2025) — Initial best practices guide for sonarft API

---

_Part of the sonarft API Code Review Prompt Suite_
