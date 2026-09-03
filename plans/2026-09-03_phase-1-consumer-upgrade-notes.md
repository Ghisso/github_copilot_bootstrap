---
name: 2026-09-03_phase-1-consumer-upgrade-notes
type: small-plan
parent_plan: consumer-upgrade-notes
phase_index: 1
status: in-progress
---

# Phase 1 — Consumer Upgrade Notes

**Parent:** `consumer-upgrade-notes`
**Phase:** 1 of 1
**Primary objective:** document every gate that newly blocks a refreshed
consumer, with a verified recovery command for each.

## 1. The gates to document

Each of these blocks a consumer that refreshes onto the post-PR-#29 runtime.
The measured evidence is in the big plan's §2.

| Change | Consumer-visible effect | Recovery |
|---|---|---|
| `validate_plan_frontmatter.py` shipped and gated at commit (Phase 2) | A plan with invalid frontmatter blocks the next commit. `check_runtime.py` also promotes this from WARN to FAIL | Fix the frontmatter. Valid small-plan statuses are exactly `in-progress`, `paused`, `complete`, `cancelled` |
| `ruff format --check` folded into `VFY-RUFF-001` (Phase 6) | Any unformatted tracked file now fails verification | `uv run ruff format .` |
| Receipt schema v4, v3 rejected unconditionally (Phase 1) | A stale v3 receipt fails closed | Re-run `verify.py phase --persist` then `closeout --persist` |
| `MEMORY.md` mtime no longer LEARN evidence (Phase 3) | A closeout log relying on it no longer satisfies the gate | Add a `## [LEARN] Entries` section with real entries or the exact no-lessons marker |
| Final-phase audit gate (Phase 7) | A big plan's last phase needs a recorded surface list | Add `## Stale-claims surfaces checked` to that phase's closeout log |
| MAJOR blocks the phase-completion commit; surviving MINOR needs disposition and reason (Phase 2) | A findings report with an open MAJOR, or a MINOR lacking disposition, blocks completion | Resolve the MAJOR; give each surviving MINOR an explicit `disposition` and non-empty `reason` |
| Typo-bypass path restriction (Phase 3) | `docs(typo):` / `chore(typo):` no longer bypass for runtime paths | Use the normal lifecycle for anything outside documentation content |
| State-directory READMEs now bootstrap-owned (Phase 7) | A refresh overwrites `.claude/{plans,explorations,session_logs,quality_reports}/README.md` | None needed; disclose it so a hand-edited README is not a surprise |

## 2. Where it goes

Extend the existing mid-plan upgrade guidance rather than adding a parallel
document, so an operator reads one place before refreshing:

- `README.md` — the consumer refresh/upgrade path, since that is where an
  operator looks first.
- `docs/runtime-checks.md` — it already carries the mid-plan consumer upgrade
  section from Phase 6's work; this belongs beside it.

Keep it operator-facing: what breaks, and the command that fixes it. Do not
restate the design rationale, which already lives in the plans and session
logs.

## 3. Non-goals

- Do not change any gate, check, threshold, or scope. Documentation only.
- Do not create a new top-level document if the existing sections can carry
  it.
- Do not patch consumer repositories.
- Do not restate phase-by-phase history; an operator needs the effect and the
  fix, not the narrative.

## 4. Verification

Every documented command must be run and confirmed, not asserted. In
particular confirm the valid small-plan status set against
`scripts/validate_plan_frontmatter.py` rather than from memory.

```
uv run python scripts/generate_targets.py --all
uv run python scripts/update_consumers.py --allow-self --local-only .
uv run pytest tests/ -q --tb=short
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
uv run ruff format --check shared scripts tests
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## 5. Acceptance criteria

- [ ] every gate in §1 is documented with its effect and recovery.
- [ ] each documented command was run and works.
- [ ] the valid small-plan status vocabulary is stated explicitly.
- [ ] the state-README overwrite is disclosed.
- [ ] the guidance is reachable from the README's refresh path.
- [ ] no gate behavior changed.
- [ ] no new stale claim introduced; docs and runtime agree.
- [ ] full tests and validation pass with no regeneration drift.

## 6. Completion evidence

Updated plan status, deterministic verification PASS, a findings report with
zero surviving findings or explicit dispositions, the closeout session log
including `## Stale-claims surfaces checked` since this is the final phase,
and generated-target parity.
