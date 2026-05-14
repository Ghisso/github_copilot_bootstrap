---
name: review-api
description: |
  API-specific review combining api-reviewer, security-reviewer, and test-reviewer.
  Checks endpoints, validation, error handling, and generates test cases.
  Use when asked to review the API or review an endpoint.
argument-hint: "[endpoint or service file]"
---

# review-api — API Endpoint Review

## Review Checklist

### Endpoints
- [ ] RESTful naming conventions
- [ ] Correct HTTP methods
- [ ] Consistent URL patterns
- [ ] Versioned if public-facing

### Validation
- [ ] Pydantic models for all inputs
- [ ] Field constraints (min/max, patterns, enums)
- [ ] Custom validators for complex rules
- [ ] Meaningful validation error messages

### Error Handling
- [ ] Structured error responses (consistent format)
- [ ] Correct HTTP status codes
- [ ] No internal details in error responses
- [ ] All exceptions caught and logged

### Security
- [ ] Input sanitization
- [ ] No injection vulnerabilities
- [ ] Auth/authz if needed
- [ ] No secrets in responses

### Testing
- [ ] Each endpoint has tests
- [ ] Valid and invalid inputs tested
- [ ] Error responses verified
- [ ] Edge cases covered

## Generated Test Cases

For each endpoint, generate:
1. Happy path (valid input → expected response)
2. Invalid input test (validation error response)
3. Missing required field (422 response)
4. Boundary value test

## Output

```
API Review: [service]

Endpoints: N reviewed
Issues: N critical, N major, N minor

[Detailed findings per endpoint]

Generated Test Cases:
  [test code for each endpoint]
```
