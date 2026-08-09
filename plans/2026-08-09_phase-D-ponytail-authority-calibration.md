---
name: 2026-08-09_phase-D-ponytail-authority-calibration
type: small-plan
parent_plan: guidance-and-review-calibration
phase_index: 4
status: in-progress
closeout_session_log: .claude/session_logs/2026-08-09_guidance-and-review-calibration-phase-D.md
---

# Small Plan: 2026-08-09_phase-D-ponytail-authority-calibration

## Scope

Remove Ponytail as a standalone lifecycle phase and special findings gate while retaining it once as a coder implementation discipline and conditionally as a review profile for control-plane/high-risk or complexity-expanding changes under the ordinary severity model.

## Ownership

- `coder`: workflow/review/Ponytail policy, agent prompts, hooks/report readers, diff classification, generators, validators, and tests.
- `verifier`: focused hook/report compatibility tests, full tests, typing, linting, formatting, generation, target validation, self-refresh, runtime checks, and root hashes.
- `reviewer`: `code`, `architecture`, `security`, `tests`, `documentation`, and `ponytail` profiles under the current pre-change policy.
- `documenter`: README, architecture, workflow, quality gate, and compatibility documentation.

## Required Skills

- `ponytail` in `full` mode for this implementation under the currently active policy.
- `code-style` and `testing-patterns` where applicable.

## Steps

- [ ] Remove standalone `PONYTAIL` from canonical lifecycle policies, generated roots, README, and lifecycle validators.
- [ ] Keep the main Ponytail skill once per coding task as reuse/native/minimum-correct implementation discipline; remove the second mandatory Ponytail-review/refactor ceremony while retaining a lightweight changed-scope simplification self-check and re-verification.
- [ ] Define minimality by necessary concepts, dependencies, abstractions, layers, configuration, execution paths, and behavior; clarity and maintainability outrank line-count reduction.
- [ ] Require/select Ponytail review for control-plane/high-risk and complexity-expanding changes; make it optional for ordinary low-complexity work and unnecessary for documentation-only diffs.
- [ ] Remove the special zero-Ponytail-findings commit/push gate; apply ordinary severity gates so Ponytail CRITICAL blocks commit, MAJOR blocks push, and MINOR is advisory.
- [ ] Make Ponytail report metadata optional where the profile did not run while preserving compatible existing reports/readers.
- [ ] Update hooks, report recording, diff classification, generated targets, policies, prompts, validators, and representative required/optional/exempt tests.
- [ ] Update README and architecture/workflow documentation consistently.

## Verification

```bash
uv run pytest tests/test_validate_targets.py tests/test_quality_score.py -q --tb=short
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/install_bootstrap.py . --allow-self --local-only
uv run python scripts/check_runtime.py
```

## Acceptance Criteria

- [ ] Canonical lifecycle has no standalone Ponytail phase.
- [ ] Coder uses Ponytail once as implementation discipline without an automatic second review/refactor invocation.
- [ ] Ponytail review is discoverable and required only for documented high-risk/complexity triggers.
- [ ] Ponytail MINOR is advisory, CRITICAL blocks commit, and MAJOR blocks push through ordinary severity gates.
- [ ] Documentation-only and non-applicable diffs do not require Ponytail metadata.
- [ ] Existing compatible findings reports remain consumable.
- [ ] Policies state that clarity and maintainability outrank line-count reduction and define conceptual minimality.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
