---
name: 2026-10-03_phase-C-behavioral-pilot-comparison
type: small-plan
parent_plan: behavioral-evaluation-pilot
phase_index: 3
status: planned
closeout_session_log:
---

# Small Plan: Behavioral Pilot Comparison

## Scope

Run the bounded before/after comparison with Phase B's frozen runner and
scorer, and publish a dated result. Covers BEP-005 and BEP-007. Runner and
scorer code are not changed in this phase except through the repair rule in
step 4. If Phase A stopped, this phase is cancelled with evidence instead.
Its native budget (at most 12 user-run Claude Code sessions) was approved
on 2026-10-03; see the big plan's approved decisions.

## Steps

- [ ] **1. Prepare both consumers.**
  **Owner:** orchestrator.
  **Files:** scratch only: exported trees and two dedicated workspaces such
  as `/tmp/native-client-probe-pilot-before` and
  `/tmp/native-client-probe-pilot-after`.
  **Required Skills:** `.claude/skills/integration-gate-spike/SKILL.md`.
  Export the "before" revision `1626364` and the "after" revision (the
  `dev` merge commit of `engineering-workflow-improvements`, recorded by
  SHA) with `git archive`. Prepare each workspace with
  `--prepare-only --source-root <exported tree>`. Record both SHAs and the
  runner revision.
  **Acceptance:** both consumers come from the same runner revision; only
  the source root differs.

- [ ] **2. User runs the comparison; orchestrator saves the evidence.**
  **Owner:** user runs the prepared commands in their own shell;
  orchestrator checks and copies results.
  **Files:** copy saved evidence to `docs/evidence/behavioral-pilot/phase-c/`.
  Per revision: the defective variant 3 times and each of the three
  controls once, so 6 runs per revision and 12 in total, each limited to
  420 seconds. The prepared schedule script runs them in the frozen
  alternating order: for each variant and repetition, "before" then
  "after" (defective 1, 2, 3, then repaired, valid-alternative, and
  approved-change). Same client, model, effort, and permission mode for
  both revisions. No retries; an unavailable run stays unavailable and its
  slot is recorded in the schedule.
  **Acceptance:** 12 attempts are accounted for in schedule order, each
  saved or explicitly unavailable.

- [ ] **3. Score and write the dated report.**
  **Owner:** orchestrator scores; documenter writes the report.
  **Files:** create `docs/2026-10-03-behavioral-pilot-results.md` (use the
  actual date of the run).
  **Required Skills:** `.claude/skills/documentation/SKILL.md`,
  `.claude/skills/humanize/SKILL.md`.
  Judge every saved `run-NN.txt` output by hand against the frozen
  `rubric.md` before reading any `run-NN.meta.json` file or the schedule,
  and record one judgment per output with a quoted sentence as its reason in
  `judgments.json`. This blinding is partial: an output's own content (for
  example an `### Open Requests` section) can still hint at its revision,
  and the report says so. The reviewer
  re-checks every judgment in step 5. Then run `--score` over both evidence
  sets. Report per-variant counts with denominators for each revision,
  control false positives, unavailable and invalid runs, duration and usage,
  both SHAs, client version, reported model, the role-loading level from
  Phase A, and confounders: what `git diff --stat 1626364 <after>` shows
  (expected: the plan's prompts, profiles, policies, skills, templates, and
  docs, but no hook or script), one model, and few runs. Use exactly the
  conclusion wording the frozen rules produce, and describe it as an
  observed difference between two bootstrap revisions, not an effect of the
  reviewer instruction alone. Never claim a generalization beyond this case,
  client, and model.
  **Acceptance:** every number and the conclusion wording in the report come
  from the scorer output over the recorded judgments.

- [ ] **4. Lock the report's numbers with a replay test.**
  **Owner:** coder.
  **Files:** modify `tests/test_check_native_clients.py`.
  **Required Skills:** `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/testing-patterns/SKILL.md`.
  Add one test that replays `docs/evidence/behavioral-pilot/phase-c/`
  through the scorer and asserts the counts the report states. If a scorer
  defect is found, stop: fix it with its own review, rescore both saved
  sets with the fixed scorer, keep the earlier results, and say so in the
  report. Never adjust scoring for one revision only.
  **Acceptance:** the replay test fails if the saved evidence or the report
  counts drift apart.

- [ ] **5. Review and close out.**
  **Owner:** reviewer, then orchestrator.
  **Required Skills:** `.claude/skills/code-review/SKILL.md`.
  Re-check every rubric judgment against its saved output. Check the report
  against the scorer output, the schedule order, the privacy of saved
  evidence, the confounders, and that no conclusion overreaches.

## Verification

```bash
uv run pytest tests/test_check_native_clients.py -q
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- The user-run comparison from step 2: 12 Claude Code sessions across two
  prepared workspaces, with client version and any unavailable run
  recorded. Host-only evidence; never a deterministic gate.

## Review Profiles

Use `.claude/review-profiles/code.md`,
`.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
