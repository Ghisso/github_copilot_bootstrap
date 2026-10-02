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

## [LEARN] Entries

- Pending closeout.

## Verification

```text
# verify closeout --format text summary lines
# verify.py phase/closeout receipt path
```

## Open Questions / Next Steps

- Implement Phase A steps 1-3, then VERIFY, REVIEW, CLOSEOUT.
