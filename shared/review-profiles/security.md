# Security Review Profile

Use for secrets, injection risk, unsafe operations, and input validation.

## Checklist

- No hardcoded API keys, passwords, tokens, or credentials.
- Secrets are not emitted in logs, configs, errors, or reports.
- User inputs are validated before use.
- SQL uses parameterized queries.
- No unsafe deserialization of untrusted data.
- No `eval()` or `exec()` on untrusted input.
- Shell commands avoid `shell=True` with user-controlled values.
- File paths are sanitized to avoid traversal.
- CORS and auth defaults are appropriate for the deployment context.

## Severity

- Critical: Hardcoded secrets, injection vulnerabilities, unsafe deserialization, or path traversal.
- Major: Missing validation, insecure defaults, overly permissive CORS, or leaked internals.
- Minor: Missing rate limits, overly verbose messages, or defense-in-depth gaps.

