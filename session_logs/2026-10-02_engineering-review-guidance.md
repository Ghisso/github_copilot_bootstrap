# Session: Engineering workflow Phase A — review and original-symptom guidance

**Date:** 2026-10-02
**Plan:** `.claude/plans/2026-10-02_phase-A-engineering-review-guidance.md`
**Status:** IN-PROGRESS

## Goal

Align the reviewer's inputs and review steps with the orchestrator's existing
"plan requirements and non-goals" delegation rule, name approved scope changes
as requirement authority, and require rerunning the original bug
reproduction after a fix. Adapt the same advice to the relaxed workflow
sidecar and add focused deterministic text checks. Covers REQ-004, REQ-005,
and the review part of REQ-009 from
`.claude/plans/engineering-workflow-improvements.md`.

## Work Log

- **Approval** - User approved Plan 1 after review of the exploration at
  `.claude/explorations/2026-10-02_bootstrap-engineering-workflow/`. The
  original four-phase evaluator-first draft was replaced by a two-plan split;
  Phase A was later split so review alignment lands first. Plans validated
  with `scripts/validate_plan_frontmatter.py` (exit 0) and were moved to
  `.claude/plans/`; nested state checkpoint `5eceb16`.
- **Branch** - Created `engineering-workflow-improvements_implementation`
  from clean `dev` at `1626364`; the branch hook set the big plan
  `in-progress` and Phase A `in-progress`.
- **Verified facts carried into the coder packet** -
  `shared/agents/orchestrator/prompt.md:126` already requires "plan
  requirements and non-goals" for every delegation; line 128 (reviewer packet)
  and `shared/agents/reviewer/prompt.md:5-10` (Inputs: scope/diff, profiles,
  gate) do not mention requirements or approved scope changes.
  `shared/skills/debug-investigator/SKILL.md` Phase 6 and its Resolution
  output block have no step that reruns the original reproduction.
- **IMPLEMENT** - Delegated steps 1-2 and the test part of step 3 to one
  `coder` (sequential, since the tests depend on the wording). Test pattern
  given: `_collapsed(...)` key-phrase assertions with `render_sidecar(tmp_path,
  "workflow")` and `target_generator.render_claude_agents/render_codex/
  render_github`, as in `tests/test_validate_targets.py` (~1423, ~1685,
  ~3141). The orchestrator keeps generation-after-settle, the self-overlay
  refresh, and the documentation step.
- **IMPLEMENT result** - Coder changed 12 `shared/` files and
  `tests/test_validate_targets.py` (5 new section-scoped key-phrase test
  cases; negative control: reverse-applying the `shared/` diff fails all 5).
  Deviation: re-captured `SIDECAR_SKILLS_PROFILE_SNAPSHOT_SHA256` because the
  edited `debug-investigator` skill ships in the skills-only sidecar; sent to
  review for judgment.
- **VERIFY** - Orchestrator ran the plan's Verification block: generation,
  both pytest groups (1230 and 223 passed), `validate_targets.py`,
  `validate_plan_frontmatter.py`, and `verify.py fast` all exit 0.
  `check_runtime.py` exit 1 with 26 failures, all "stale runtime path" for
  the self-installed copies of the changed files; cleared by the closeout
  self-overlay refresh.
- **REVIEW** - Fresh `reviewer` with `code`, `architecture`, `security`,
  `tests`, `ponytail`, `documentation`; packet carried the approved plan,
  requirements, non-goals, and the scoped diff.
- **REVIEW round 1** - Gate PASS: 0 CRITICAL, 0 MAJOR, 6 MINOR. Hash
  re-capture judged acceptable (only the two `debug-investigator` copies in
  `dist/sidecar/skills/` change). Decisions: fix #1 (reviewer cannot pause to
  ask: add an optional `### Open Requests` section and answer `WARN` while a
  request is open; the orchestrator packet carries verification results
  already obtained; sidecar hand-back list names the negative control), #2
  (sidecar simple-work clause), #3 (real moved-out-of-section test case), #5
  (role-neutral, plain-words negative-control bullet), #6 (wrong "rule above"
  pointer; separate lead-in for the test checks). Accept #4 (three
  asset-to-text maps): shared-source and generated paths have different
  shapes, so a helper would still need one path table per root and save
  little. Fixes sent back to the same coder (same role and phase).

## [LEARN] Entries

- Pending closeout.

## Verification

```text
# verify closeout --format text summary lines
# verify.py phase/closeout receipt path
```

## Open Questions / Next Steps

- Implement Phase A steps 1-3, then VERIFY, REVIEW, CLOSEOUT.
