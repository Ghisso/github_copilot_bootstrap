# Exploration — Consumer CI Enforcement

**Date:** 2026-09-08
**Status:** OPEN — design direction identified; implementation not yet planned
**Trigger:** review of `.github/workflows/validate.yml` found that the bootstrap
repository does not run its full pytest, Ruff, and Mypy suite in GitHub Actions.
The higher-priority question is whether consumer repositories receive effective
continuous integration (CI), because they are the product surface of this
bootstrap.

## Finding

The bootstrap repository's `.github/workflows/validate.yml` checks target
generation and validation on Ubuntu and macOS, plus standalone Python 3.9 hook
compatibility. It does not run the complete pytest suite, coverage, Ruff, Mypy,
`check_runtime.py`, or the generated verifier stages.

That omission is not the main consumer-CI gap. The generated bootstrap installs
`.claude/scripts/verify.py`, hooks, policies, and agent guidance, but it does not
install a GitHub Actions workflow into consumer repositories. Consumer checks
are therefore enforced through the local plan, commit, and push lifecycle unless
the consumer defines its own CI workflow.

The generated verifier already adapts its measurements to a consumer:

- Ruff checks the consumer tree while excluding `.claude`.
- Mypy uses the consumer's configured source scope.
- Pytest uses native test discovery.
- Missing tools and abnormal execution report `UNVERIFIED` instead of a false
  pass.

## Recommended direction

Keep the bootstrap repository's workflow focused on cross-platform generation,
target validation, and hook compatibility. Running the bootstrap's own complete
pytest suite is still useful maintenance work, but it does not solve consumer CI.

Add an opt-in consumer-facing GitHub Actions template. Do not overwrite or
silently merge an existing consumer workflow. The template should install the
consumer project's own dependencies and invoke a stateless verifier command,
for example:

```bash
uv run python .claude/scripts/verify.py ci --format json
```

A new `ci` mode should reuse the adaptive Ruff, Ruff-format, Mypy, and pytest
measurements used by `verify.py phase`, while remaining safe for an unattended
CI runner:

- Do not require an active implementation plan.
- Do not create or update phase receipts.
- Do not mutate `.claude` state.
- Return a failing exit status for both `FAIL` and `UNVERIFIED` results so a
  missing tool cannot produce a successful check.
- Preserve machine-readable JSON output for GitHub Actions diagnostics and
  future integrations.

## Product boundary

This work concerns the existing generated bundle for GitHub Copilot, Claude
Code, OpenAI Codex, and Google Antigravity. It does not add another agent target
or change target-specific hook semantics.

The consumer workflow is an integration aid, not a replacement for a
repository's own CI policy. Consumers may need additional jobs, service
containers, platform matrices, deployment checks, or project-specific commands.
The bootstrap should provide a safe default and a documented opt-in path without
taking ownership of unrelated consumer workflows.

## Questions to resolve before implementation

1. Should the workflow be copied only through an explicit installer option, or
   shipped as a template that the consumer enables manually?
2. What path and filename avoid collisions with consumer-owned workflows?
3. Should the bootstrap offer a reusable workflow, a copied workflow template,
   or both?
4. How should projects that do not use `uv` opt out or substitute their setup
   while retaining the verifier contract?
5. Which generated-target, installer-ownership, and runtime checks prove that
   existing consumer workflows are never overwritten?

## Implementation-plan boundary

Any implementation changes generators, installer ownership behavior, generated
verification code, and validation tests. It is control-plane work and requires a
full implementation plan, cross-platform verification, and the required code,
architecture, security, tests, and Ponytail review profiles.
