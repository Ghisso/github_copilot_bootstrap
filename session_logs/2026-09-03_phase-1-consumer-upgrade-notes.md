# Session: Consumer Upgrade Notes

**Date:** 2026-09-03
**Plan:** `.claude/plans/2026-09-03_phase-1-consumer-upgrade-notes.md`
**Status:** COMPLETED

## Goal

Document every gate that newly blocks a consumer refreshed onto the runtime
produced by `verification-gate-semantic-hardening`, with a verified recovery
command for each.

## Work Log

- **07:20** - The user asked whether their usual refresh command
  (`update_consumers.py <three consumer paths>`) was still safe after PR #29.
  Checked the CLI: unchanged, multiple positional targets, no new required
  flags. Then checked the three real projects, which is where the answer
  actually lay.
- **07:25** - Two of three would have been blocked immediately.
  `industrial-inspection` was mid-plan with a small plan at
  `status: planned` — never a valid value, but only gate-blocking once Phase 2
  shipped `validate_plan_frontmatter.py` to consumers. All three had
  unformatted tracked files (2, 1, 6), newly gate-blocking after Phase 6
  folded `ruff format --check` into `VFY-RUFF-001`. All three had zero
  existing receipts, so the v3→v4 migration was a non-issue for them.
- **07:30** - The user fixed their side. Two RAG files failed with
  `Permission denied` because they were `root:root`. I initially reported that
  as two files; a proper sweep found **156** root-owned Python files in that
  project, none in the other two. Corrected the report rather than leaving the
  understated number standing.
- **07:34** - The user then asked for this to be documented. Tracked,
  multi-file, needs a commit, so it took a plan and branch rather than a
  direct edit.
- **07:50** - Implementation returned, having corrected an error in my own
  plan. Verified its corrections independently.

## Design decisions

- **Extended two existing sections rather than adding a document.** An
  operator reads the README's refresh path and
  `docs/runtime-checks.md`'s mid-plan upgrade section; a third document would
  be a place to miss. The README carries a pointer plus the two likeliest
  surprises, the docs file carries the full table.
- **Operator-facing only: effect and recovery.** The design rationale already
  lives in the plans and session logs of the preceding seven phases, and
  restating it here would be a second copy to drift.
- **Every documented command was executed, not asserted.** That was an
  explicit acceptance criterion, because a recovery instruction that does not
  run is worse than none.

## A correction to the plan of record

My phase plan's gate table claimed `check_runtime.py` promotes plan-frontmatter
from WARN to FAIL for consumers. That is wrong, and the implementation caught
it rather than copying it. Verified independently:

- `dist/multi-agent/.claude/scripts/` contains only `record_findings.py`,
  `runtime_ownership.py`, `validate_plan_frontmatter.py`, and `verify.py`;
  `grep -c check_runtime scripts/generate_targets.py` returns 0. So
  `check_runtime.py` never reaches a consumer at all.
- The real consumer-facing enforcement is `assert_plan_frontmatter` in
  `shared/hooks/scripts/_lib-frontmatter.sh:1184`, which resolves
  `$repo_root/.claude/scripts/validate_plan_frontmatter.py` and fails the
  commit. There is no prior WARN state for a consumer to be promoted from,
  because the validator did not exist for them before Phase 2.

The documented mechanism is the one that actually fires. The WARN→FAIL framing
applies only to this authoring repository.

## Verified facts behind the documentation

- Status vocabularies read from `scripts/validate_plan_frontmatter.py`:
  `BIG_PLAN_STATUSES = {"planning", "in-progress", "complete", "cancelled"}`
  and `SMALL_PLAN_STATUSES = {"in-progress", "paused", "complete",
  "cancelled"}`. Worth stating both: the valid initial big-plan value is
  `planning`, one letter from the `planned` that caused the blockage.
- The four bootstrap-owned state READMEs named in the table match
  `STATE_DIR_OWNED_README_PATHS` in `scripts/runtime_ownership.py:64` exactly,
  and match the live refresh output, which logs `refresh bootstrap-owned state
  directory README` for `plans`, `explorations`, `session_logs`, and
  `quality_reports`.
- The README's anchor link resolves to `#### Other gates that newly block a
  refresh` at `docs/runtime-checks.md:373`.
- `uv run ruff format --check shared scripts tests` runs clean, so the
  documented recovery command is real.
- The MAJOR row was tightened during review from "always blocks completion" to
  "blocks the phase-completion commit, not intermediate ones". The preceding
  plan spent five CRITICAL findings on documents getting this exact
  distinction backwards, so leaving an ambiguous "always" in the row most
  likely to be misread was not worth the brevity.

## [LEARN] Entries

- [LEARN:workflow] Answer "is it still safe to run this?" by inspecting the
  actual targets, not the tool. The CLI was unchanged and the honest answer
  was still "no, two of your three projects will be blocked" — which only the
  target state could reveal.
- [LEARN:review] A plausible-looking enum value is a latent outage. `planned`
  was never valid, sat harmlessly in a consumer for weeks, and became
  commit-blocking the moment validation shipped. When shipping a validator to
  existing installs, check what those installs already contain before
  refreshing them.
- [LEARN:diagnostics] Report the scale of a problem, not the first instance.
  Two root-owned files were visible because those two needed reformatting; 156
  existed. A count derived from the symptom rather than the cause will
  understate it.
- [LEARN:documentation] A recovery instruction that has not been run is a
  guess. Every command here was executed before being documented, which is
  what caught that the authoring repo's WARN→FAIL framing does not apply to a
  consumer at all.

## Stale-claims surfaces checked

This is the big plan's final phase, so the standing audit applies. This phase
changed no behavior — it documents behavior the preceding plan introduced — so
the sweep was scoped to whether the new prose contradicts the runtime, and to
the surfaces describing consumer refresh.

| Surface | Outcome |
|---|---|
| `README.md` | Corrected — added the refresh-gate guidance; verified the anchor resolves |
| `docs/runtime-checks.md` | Corrected — added the gate table and practical notes; MAJOR row wording tightened |
| `scripts/validate_plan_frontmatter.py` | Checked as source of truth for both status vocabularies; docs match |
| `scripts/runtime_ownership.py` | Checked as source of truth for the owned README set; docs match, confirmed against live refresh output |
| `shared/hooks/scripts/_lib-frontmatter.sh` | Checked as the real consumer enforcement path; docs corrected to match it |
| `scripts/generate_targets.py`, `dist/multi-agent/.claude/scripts/` | Checked to confirm `check_runtime.py` is not shipped; my plan's claim was wrong and was not carried into the docs |
| `.claude/MEMORY.md` | Checked — no claim about consumer refresh gates to update |
| Other `docs/*.md`, `shared/policies/`, `shared/skills/`, `shared/templates/` | Checked — none describe consumer refresh gates; nothing to update |

## Verification Results

```bash
uv run pytest tests/ -q --tb=short
# 1242 passed

uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
# Success: no issues found in 25 source files

uv run ruff check shared scripts tests
# All checks passed!

uv run ruff format --check shared scripts tests
# 25 files already formatted

uv run python scripts/validate_targets.py
# PASS generated target is structurally valid

uv run python scripts/validate_plan_frontmatter.py
# (clean)

uv run python .claude/scripts/verify.py phase --format text
# phase: PASS
```

Diff is 2 files, additive prose and one table only — no code, config, check
id, or threshold touched.

## Open Questions / Next Steps

- The user's three consumer projects: `industrial-inspection` is clean;
  `schema-bootstrap-llm-wiki` and `RAG` each have only the obsolete
  `.devcontainer/hf-ai-sync.py` outstanding, which the refresh deletes. RAG
  still has ~154 root-owned Python files that are currently formatted and so
  not blocking, but will fail the moment any needs rewriting.
- No compatibility allowance exists in this plan, so none carries a removal
  condition.
- The user owns the merge decision; no PR was opened.
