---
name: 2026-08-09_phase-E-docs-and-graphify-remediation
type: small-plan
parent_plan: state-sync-recovery-and-plan-cancellation
phase_index: 5
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-09_phase-E-docs-and-graphify-remediation

## Scope

Document both repairs and use the new vocabulary to correct the records that
motivated it. The Graphify big plan currently claims `status: complete` while
its own body admits the status is inaccurate and explains that the validator
left no alternative. Phase 0 measured too little value to justify bootstrap
integration and returned NO-GO. With `cancelled` available, that plan and its
six never-authorized phases get accurate statuses backed by the evidence
artifact that already exists.

This is record remediation only. Do not add Graphify dependencies, routing,
runtime support, persistence, another benchmark, or a follow-up adoption plan.
Historical evidence stays intact. Active documentation must not imply that a
Graphify retry is scheduled or expected.

This phase also writes the single dated record of the state-sync incident, so
the volatile detail lives in one place and every other file points at it.

## Ownership

- `documenter`: `README.md`, `docs/plan-deterministic-commit-gate.md`,
  `docs/2026-08-09-state-sync-rebase-recovery.md`.
- `coder`: the Graphify plan records under `.claude/plans/`, the evidence
  artifact marker, and `.claude/MEMORY.md`.
- `verifier`: full verification, target generation, determinism, plan-frontmatter
  validation across all plans, and the `state-sync.sh status` health probe.
- `reviewer`: the profiles listed below.

## Required Skills

- `.claude/skills/documentation/SKILL.md` for the documentation edits.
- `.claude/skills/ponytail/SKILL.md` in `full` mode for any code touched.
- `.claude/skills/run-tests/SKILL.md` for the verifier.
- `.claude/skills/learn/SKILL.md` and `.claude/skills/commit/SKILL.md` at
  closeout.
- Human-facing documentation follows the already-shipped
  `shared/policies/agent-reporting.instructions.md` clarity rules. Do not add a
  second writing policy or claim formal ASD-STE100 compliance.

## Review Profiles

- `.claude/review-profiles/code.md`
- `.claude/review-profiles/architecture.md`
- `.claude/review-profiles/security.md`
- `.claude/review-profiles/tests.md`
- `.claude/review-profiles/ponytail.md`
- `.claude/review-profiles/documentation.md`

This phase is multi-file control-plane/state remediation, so the full review
set remains justified under the current calibrated routing. The Ponytail
profile is not being reinstated as a universal documentation gate.

## Sequencing Constraint

`.claude/` is ignored by the outer repository, so every edit under `.claude/` in
this phase produces no tracked diff. `README.md` and `docs/` supply the tracked
content that the score report's `content_hash` and `changed_files` bind to.
Stage every file destined for the commit before running `quality_score.py` and
`record_findings.py`, or the recomputed hash will not match and the gate will
reject the report as dirty. This is a recorded lesson.

## Steps

- [ ] `README.md` (modify): update the commit-invariant and push-invariant
      bullets (around lines 589 and 590) to describe cancelled-phase handling,
      the completed-phase commit count, and the last-completed-phase findings
      binding.
- [ ] `docs/plan-deterministic-commit-gate.md` (modify): update the
      blocked-state bullet (around line 97) to include the cancelled-phase
      cases, including the stale-pointer commit refusal.
- [ ] `docs/2026-08-09-state-sync-rebase-recovery.md` (create): the single dated
      record of the incident. Include the measured evidence counts from
      `.claude/session_logs/hooks-errors.log` (1 `Created autostash`, 9
      `already a rebase-merge`, 5 unreproduced
      `Cannot rebase onto multiple branches`), the causal chain, why `--abort`
      alone cannot clear a half-initialized rebase, why `--quit` can, why
      `--autostash` was removed, and an explicit assumption marker on the
      refspec defence. Other files point here instead of restating it; a wrong
      mechanism claim propagates across files otherwise.
- [ ] `.claude/plans/graphify-structural-code-intelligence.md` (modify): set
      `status: cancelled`; add `cancelled_at`, `cancelled_reason` recording that
      the Phase 0 gate returned NO-GO, and `cancelled_evidence` pointing at the
      evidence artifact. In the body,
      delete the sentence stating that `complete` is the only terminal status
      the validator accepts, which this plan makes false, and replace the
      "complete in lifecycle terms only" paragraph with a plain statement that
      the plan was cancelled at the Phase 0 gate because measured value did not
      justify bootstrap integration. Remove or neutralize active wording that
      presents another Graphify trial as the expected next step. Do not rewrite
      historical gate criteria or measured evidence. Quote the removed
      lifecycle-vocabulary sentence in the new `docs/` record so the reason it
      existed is preserved.
- [ ] The six Graphify phase files
      `2026-08-09_phase-A-graphify-managed-dependency-and-thin-adapter.md`
      through `2026-08-09_phase-F-graphify-optional-persistence-gate.md`
      (modify): set `status: cancelled` and add the three cancellation fields.
      Leave `parent_plan`, `phase_index`, and the bodies unchanged. Leave
      `closeout_session_log` empty; a cancelled phase has no closeout.
- [ ] Add the `**Status:** CANCELLED` marker and the list of cancelled phases to
      the evidence artifact at
      `.claude/explorations/2026-08-09_graphify-compatibility-value-gate/evidence.md`.
      If that file is not the right home, create a dated session log under
      `.claude/session_logs/` and point `cancelled_evidence` there instead.
      The marker/reason must state that the compatibility/value gate returned
      NO-GO because measured value did not justify integration. Perform the edit
      before writing any statement that it was done; never order the claim
      ahead of the action.
- [ ] `2026-08-09_phase-0-graphify-compatibility-and-value-gate.md`: leave
      unchanged at `status: complete`. Phase 0 genuinely ran, shipped, and
      produced the gate result.
- [ ] Search active bootstrap source/configuration for Graphify references.
      `shared/`, generated MCP configuration, the devcontainer, and runtime
      routing must contain no active Graphify dependency or integration path.
      Historical plans/evidence may retain Graphify references. Correct only
      stale documentation or log wording that incorrectly presents adoption as
      pending.
- [ ] `.claude/MEMORY.md` (modify): record the `[LEARN]` entries listed below.
- [ ] Regenerate targets and run the full verification set.

## LEARN Entries To Record

- A recovery that swallows its own failure converts a transient fault into a
  permanent one. `git rebase --abort 2>/dev/null || true` cannot clear a
  half-initialized rebase; `--quit` can, because it clears state without moving
  `HEAD`.
- `--autostash` is not free insurance. It writes the autostash commit and the
  rebase directory before it discovers the tree is dirty again, so on a
  self-writing repository it manufactures the latched state it was meant to
  avoid.
- A warn-never-fail subsystem needs a health surface. Nine hours and eleven
  unpublished commits passed unnoticed because nothing reported the latched
  state; `status` now does.
- A lifecycle vocabulary gap forces falsification. With no `cancelled` status,
  the only ways to clear the gate were to fabricate six closeouts or to write an
  inaccurate `complete`; the second actually happened and documented itself.
- Relaxing a gate is safe only when paired with a new requirement. Cancellation
  buys exemption from commit, score, findings, and closeout by paying an
  artifact-backed reason.
- A NO-GO gate is a valid final result. Low measured value is a reason to stop,
  not a reason to add more integration machinery or schedule another trial.

## Test Scenarios

- [ ] `uv run python scripts/validate_plan_frontmatter.py` with no arguments
      passes over every file in `.claude/plans/`, including the seven remediated
      Graphify files.
- [ ] The Graphify shape is covered as a fixture scenario in
      `scripts/validate_targets.py` (added in Phase D): seven phases, one
      complete, six cancelled with evidence, one commit, and a findings report
      bound to the completed phase. That scenario is the pushability proof. Do
      not push the real branch: push is the user's decision and is out of scope
      here.
- [ ] `bash .claude/hooks/scripts/state-sync.sh status` reports `rebase: none`.
- [ ] Active bootstrap configuration contains no Graphify executable,
      dependency, MCP server, routing rule, or persistence path. Historical
      plan/evidence references remain allowed.

## Verification

```bash
uv sync
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/check_runtime.py
bash .claude/hooks/scripts/state-sync.sh status
uv run python .claude/scripts/quality_score.py scripts/ --phase 2026-08-09_phase-E-docs-and-graphify-remediation --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

Generator determinism, after all edits settle:

```bash
uv run python scripts/generate_targets.py --all
cp -a dist /tmp/dist-gen-a
uv run python scripts/generate_targets.py --all
diff -r /tmp/dist-gen-a dist
rm -rf /tmp/dist-gen-a
```

## Risks

- Editing another plan's records can look like tampering. The edit replaces an
  admittedly inaccurate status with an accurate one and adds evidence; the
  removed sentence is quoted in the new `docs/` record, so the history of why it
  existed survives the correction.
- The evidence artifact must exist before `cancelled_evidence` points at it, or
  the validator fails. Write the marker first, then the frontmatter.
- Documentation drift across `README.md`, `docs/`, and the workflow policy from
  Phase C. Mitigation: the incident detail lives only in the new dated record,
  and every other file links to it.
- An outer-repo diff limited to `.claude/` would leave the score report unable to
  bind. `README.md` and `docs/` changes are in the same commit for exactly this
  reason.

## Acceptance Criteria

- [ ] `README.md` and `docs/plan-deterministic-commit-gate.md` describe the
      cancelled-phase gate behavior accurately.
- [ ] `docs/2026-08-09-state-sync-rebase-recovery.md` records the measured
      evidence, the causal chain, and the unverified-cause assumption.
- [ ] The Graphify big plan reads `status: cancelled` with a reason, timestamp,
      and evidence pointer, and no longer contains the false sentence about
      `complete` being the only terminal status.
- [ ] Graphify phases A through F read `status: cancelled` with full evidence;
      Phase 0 is untouched at `complete`.
- [ ] The Graphify plan/evidence state records the low-value NO-GO accurately
      and does not schedule or imply a renewed integration attempt.
- [ ] Active bootstrap source/configuration contains no Graphify integration;
      only historical planning/evidence references remain.
- [ ] No fabricated closeout log, findings report, or score exists for any
      cancelled phase.
- [ ] `validate_plan_frontmatter.py` passes over every plan file.
- [ ] The Graphify-shaped fixture scenario proves the branch is pushable under
      the new gates without falsification.
- [ ] `[LEARN]` entries are recorded in `.claude/MEMORY.md`.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
