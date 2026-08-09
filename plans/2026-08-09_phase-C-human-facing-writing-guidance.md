---
name: 2026-08-09_phase-C-human-facing-writing-guidance
type: small-plan
parent_plan: guidance-and-review-calibration
phase_index: 3
status: in-progress
closeout_session_log: .claude/session_logs/2026-08-09_guidance-and-review-calibration-phase-C.md
---

# Small Plan: 2026-08-09_phase-C-human-facing-writing-guidance

## Scope

Define one canonical audience-aware reporting policy: clear, precise, direct, natural human-facing technical prose inspired by ASD-STE100 principles, with compact Caveman retained only for internal agent handoffs and exact technical content protected from lossy rewriting.

## Ownership

- `coder`: canonical reporting policy, agent prompt pointers, generator/validator assertions, and tests.
- `verifier`: generation, full tests, typing, linting, formatting, target validation, self-refresh, runtime checks, and root hashes.
- `reviewer`: `code`, `architecture`, `security`, `tests`, `documentation`, and `ponytail` profiles.
- `documenter`: README and architecture/workflow/user-facing examples.

## Required Skills

- `ponytail` in `full` mode for code changes.
- `code-style` and `testing-patterns` where applicable.

## Steps

- [ ] Split the central reporting policy into explicit human-facing and agent-to-agent modes.
- [ ] State that the human-facing rules are inspired by ASD-STE100 principles but do not claim formal compliance.
- [ ] Require precise, clear, direct, natural prose with observable terminology, sentence, abbreviation, jargon, and active-voice rules; technical precision outranks simpler vocabulary.
- [ ] Apply the standard strongly to user answers, plans, explanations, reviews, reports, summaries, and documentation; lightly to commit messages.
- [ ] Protect identifiers, API names, commands, paths, logs, errors, structured findings, quotations, source code, and other exact material from lossy rewriting.
- [ ] Retain Caveman compression for compact internal agent status/handoffs, not default user communication.
- [ ] Point canonical agent prompts to the single policy without duplicating it; preserve the documenter's normal-prose requirement.
- [ ] Update generation, validators, tests, README, and examples for the audience distinction and jargon-to-clear-prose boundary.

## Verification

```bash
uv run pytest tests/test_validate_targets.py -q --tb=short
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

- [ ] The policy is explicitly ASD-STE100-inspired and explicitly disclaims formal compliance.
- [ ] Human-facing communication uses the defined precise, clear, direct, natural prose rules.
- [ ] Caveman remains available internally but is not the user-facing default.
- [ ] Technical precision takes priority over simpler vocabulary.
- [ ] Exact technical material is protected from lossy rewriting.
- [ ] No duplicate communication policy or mandatory rewrite stage exists.
- [ ] Canonical sources, generated targets, prompts, validators, tests, and docs agree.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
