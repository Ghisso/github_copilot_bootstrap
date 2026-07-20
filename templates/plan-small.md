---
name: <YYYY-MM-DD_phase-X-slug>
type: small-plan
parent_plan: <big-plan-slug>
phase_index: 1
status: in-progress
closeout_session_log:
---

# Small Plan: <YYYY-MM-DD_phase-X-slug>

## Scope

[What this phase changes]

## Steps

- [ ] [Step]

## Verification

```bash
uv run pytest tests/ -q --tb=short
uv run mypy src/ --ignore-missing-imports --explicit-package-bases
uv run ruff check src/ tests/
uv run python .claude/scripts/quality_score.py src/ --phase <current_phase> --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
