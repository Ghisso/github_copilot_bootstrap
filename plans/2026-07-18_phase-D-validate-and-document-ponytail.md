---
name: 2026-07-18_phase-D-validate-and-document-ponytail
type: small-plan
parent_plan: ponytail-integration
phase_index: 4
status: complete
closeout_session_log: plans/2026-07-18_ponytail-integration-closeout.md
---

# Small Plan: 2026-07-18_phase-D-validate-and-document-ponytail

## Scope

Prove that Ponytail survives generation, fresh installation, repeat updates,
and all three target adapters, then document the downstream contract and
upstream upgrade process. This phase closes the gap between local source
integration and actual consumer availability.

## Steps

- [ ] Extend `scripts/validate_targets.py` end-to-end consumer fixtures.
  - Generate a clean `dist/multi-agent/`.
  - Install into a throwaway consumer.
  - Assert both skills, provenance, and license are present.
  - Assert Copilot, Claude, and Codex root adapters point to the same canonical
    Ponytail skill.
  - Produce a non-documentation diff and demonstrate commit rejection without
    Ponytail review evidence.
  - Record a fresh zero-finding Ponytail review and demonstrate the Ponytail
    portion of the gate passes.
  - Change the diff and demonstrate the report becomes stale.
- [ ] Exercise `scripts/update_consumers.py` against a fixture that predates
  Ponytail.
  - The update adds Ponytail without deleting mutable plans, memory, session
    logs, quality reports, or project-local instructions.
  - A repeat update is idempotent.
  - No network access or global plugin install occurs in the consumer.
- [ ] Update `scripts/check_runtime.py`.
  - Require the downstream Ponytail skills, license, and provenance files.
  - Do not require Node.js solely for this instruction-and-review integration.
  - If a future phase adds upstream lifecycle hooks, Node remains a
    warning/fallback dependency unless all target environments guarantee it.
- [ ] Update `README.md`.
  - Explain that Ponytail is built into downstream projects and defaults to
    `full` for coding.
  - Document the pre-write activation and post-write fresh-review gate.
  - Explain that it complements rather than replaces security/correctness
    review.
  - Document how a user explicitly overrides it and how that interacts with
    the existing bypass ledger.
- [ ] Update `docs/architecture.md`, `docs/target-mapping.md`,
  `docs/runtime-checks.md`, and `docs/smoke-tests.md` with canonical paths,
  report fields, gate behavior, consumer update behavior, and troubleshooting.
- [ ] Add an upstream upgrade section to
  `shared/third_party/ponytail/UPSTREAM.md`.
  - Review the new release notes and diff from the pinned tag.
  - Refresh only allowlisted portable files.
  - Preserve the license.
  - Regenerate and run the full target validator.
  - Record the new tag, commit, hashes, and any local metadata-only
    transformations.
- [ ] Run a manual three-target smoke review using a small intentionally
  over-engineered fixture and confirm every target identifies the same
  deletion opportunity while preserving a required safety check.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
