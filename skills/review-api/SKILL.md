---
name: review-api
visibility: public
description: |
  Thin API-review alias. Use when asked to review an API or endpoint; routes
  to the unified `reviewer` agent with `api`, `security`, and `tests` profiles.
argument-hint: "[endpoint or service file]"
---

# Review API

Run:

```text
reviewer: Review [endpoint or service file] with profiles api, security, tests.
```

The authoritative API checklist lives in `.claude/review-profiles/api.md`.
Security and test coverage concerns come from `.claude/review-profiles/security.md` and `.claude/review-profiles/tests.md`.

