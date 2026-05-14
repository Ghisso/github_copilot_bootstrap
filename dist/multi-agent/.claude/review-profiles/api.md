# API Review Profile

Use for BentoML services, HTTP endpoints, request/response schemas, and production readiness.

## Checklist

- Inputs and outputs use Pydantic models with constraints.
- Validation errors are meaningful and do not leak internals.
- Exceptions are caught, logged with context, and returned as structured errors.
- HTTP methods and paths are consistent.
- Public APIs are versioned when needed.
- Health checks exist.
- CORS, timeouts, and concurrency limits are configured deliberately.
- Expensive resources initialize once in startup lifecycle hooks.
- Shutdown cleanup exists where resources need it.
- Environment-driven settings do not expose secrets.

## Severity

- Critical: No input validation, missing error handling, secrets in responses, or per-request model loading.
- Major: Missing health checks, incorrect status codes, missing timeouts, or lifecycle gaps.
- Minor: Naming inconsistencies, missing request logging, or documentation gaps.

