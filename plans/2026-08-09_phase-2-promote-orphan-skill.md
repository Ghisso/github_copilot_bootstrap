---
name: 2026-08-09_phase-2-promote-orphan-skill
type: small-plan
parent_plan: installer-self-target-refresh
phase_index: 2
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-09_phase-2-promote-orphan-skill

## Scope

`safe-consumer-bootstrap-refresh` is an authored skill that exists only in this
repository's `.claude/skills/` overlay, not in `shared/skills/`. It is therefore
an obsolete owned file: the next self-refresh deletes it, and it is the sole
remaining `check_runtime.py` drift failure.

Promote it into `shared/skills/` so it is generated into every target and
survives refreshes.

## Ownership

- `coder`: move the skill into `shared/`, add required metadata.
- `verifier`: generation, validator, full suite, runtime drift check.
- `reviewer`: `code`, `architecture`, `tests`, `documentation`, `ponytail`.

## Steps

- [ ] Add `visibility` to the skill's frontmatter; `shared/skills/*/SKILL.md`
  requires `public|background` and the orphan copy has neither.
- [ ] Create `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md` with the
  existing body unchanged.
- [ ] Regenerate; confirm the skill appears in the generated target and in the
  Codex `[[skills.config]]` set, which must equal the `shared/skills` set
  exactly.
- [ ] Refresh this repository's overlay with `--allow-self` so the installed
  copy matches generated output.
- [ ] Confirm `check_runtime.py` reports zero drift failures.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run python scripts/check_runtime.py
```

## Acceptance Criteria

- The skill lives in `shared/` and regenerates into the target.
- `check_runtime.py` reports zero drift failures.
- A subsequent self-refresh no longer removes the skill.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
