---
name: 2026-08-09_phase-C-cancelled-status-contract
type: small-plan
parent_plan: state-sync-recovery-and-plan-cancellation
phase_index: 3
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-09_phase-C-cancelled-status-contract

## Scope

Give the lifecycle a way to say "this phase will never run". Add a `cancelled`
status for small plans and big plans to `scripts/validate_plan_frontmatter.py`,
together with the three fields that make cancellation auditable rather than a
silent bypass: `cancelled_at`, `cancelled_reason`, and `cancelled_evidence`. The
evidence path must resolve to a file that exists and contains
`**Status:** CANCELLED`, mirroring the existing `closeout_session_log` contract.
The validator, the plan templates, the session-log template, the plans README,
and the workflow policy all change together in one phase, because the previous
validator rejects the new contract and a split would leave a boundary where
templates document a status the validator refuses.

## Ownership

- `coder`: `scripts/validate_plan_frontmatter.py`,
  `shared/templates/plan-small.md`, `shared/templates/plan-big.md`,
  `shared/templates/session-log.md`, `shared/plans/README.md`,
  `shared/policies/workflow.instructions.md`,
  `tests/test_validate_plan_frontmatter.py`.
- `verifier`: full verification plus target generation and determinism.
- `reviewer`: the profiles listed below.
- `documenter`: policy and template prose is part of this phase's diff; README
  and `docs/` land in Phase E.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` in `full` mode.
- `.claude/skills/code-style/SKILL.md` and
  `.claude/skills/testing-patterns/SKILL.md`.
- `.claude/skills/run-tests/SKILL.md` for the verifier.
- `.claude/skills/documentation/SKILL.md` for the policy and template prose.
- `.claude/skills/learn/SKILL.md` and `.claude/skills/commit/SKILL.md` at
  closeout.

## Review Profiles

- `.claude/review-profiles/code.md`
- `.claude/review-profiles/architecture.md`
- `.claude/review-profiles/security.md`
- `.claude/review-profiles/tests.md`
- `.claude/review-profiles/ponytail.md`
- `.claude/review-profiles/documentation.md`

Review is mandatory here because this phase changes control-plane/high-risk
lifecycle code. This use of the Ponytail profile follows the current calibrated
review policy; it is not a return to universal Ponytail review for every diff.

## Steps

- [ ] `scripts/validate_plan_frontmatter.py` (modify): lift the two status
      allow-lists into module-level constants and add
      `CANCELLED_FIELDS = ("cancelled_at", "cancelled_reason",
      "cancelled_evidence")`. Big-plan statuses become
      `{planning, in-progress, complete, cancelled}`; small-plan statuses become
      `{in-progress, complete, cancelled}`.
- [ ] Keep `started_at` required only for `in-progress` and `complete`, and
      `current_phase` required only for `in-progress`. A `cancelled` big plan
      requires neither: a plan can be called off before its branch exists.
- [ ] Add
      `validate_cancellation(path: Path, data: dict[str, Any], errors: list[str]) -> None`
      (create). It requires all three `CANCELLED_FIELDS` present and non-empty;
      requires `cancelled_at` to match `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`;
      resolves `cancelled_evidence` against `REPO_ROOT` when it is not absolute;
      requires that file to exist and to contain a line matching
      `^\*\*Status:\*\*\s+CANCELLED\b`. Call it from both
      `validate_big_plan` and `validate_small_plan` when status is `cancelled`.
- [ ] Guard the evidence-file read so a missing or unreadable file becomes a
      clean accumulated failure, not an uncaught exception. This is a recorded
      lesson about unconditional `read()` on a required-but-maybe-missing file.
- [ ] A `cancelled` small plan must not require `closeout_session_log`. A
      cancelled phase has no closeout.
- [ ] `shared/templates/plan-small.md` (modify): document the status vocabulary
      as a `#` comment line inside the frontmatter and add the commented
      cancellation field block. The frontmatter parser skips lines whose first
      non-space character is `#`, so comments are safe there.
- [ ] `shared/templates/plan-big.md` (modify): same treatment.
- [ ] `shared/templates/session-log.md` (modify): add the `**Status:** CANCELLED`
      variant beside `**Status:** COMPLETED`, with one line each saying when to
      use which.
- [ ] `shared/plans/README.md` (modify): document both status vocabularies, the
      three cancellation fields, and the rule that a cancelled phase needs no
      commit, findings report, score, or closeout log but does need the
      evidence artifact.
- [ ] `shared/policies/workflow.instructions.md` (modify): add a "Cancelling a
      plan or phase" subsection under Branch Lifecycle. State what cancellation
      means, the three required fields and the evidence marker, that a cancelled
      phase requires no commit or closeout artifacts, that `cancelled` on a big
      plan is terminal and cannot start a branch, and the three conditions under
      which a branch carrying cancelled phases becomes pushable. Amend the
      existing bullet "Open a PR to `dev` only after every small plan in the big
      plan is complete" to read "complete or cancelled".
- [ ] `tests/test_validate_plan_frontmatter.py` (create): the accept/reject
      matrix below. There is no test module for this validator today.
- [ ] Regenerate targets.

## Test Scenarios

- [ ] Accepts a small plan with `status: cancelled`, all three fields, and an
      evidence file containing `**Status:** CANCELLED`.
- [ ] Rejects `cancelled` with each of the three fields missing in turn
      (parameterized over `CANCELLED_FIELDS`).
- [ ] Rejects a malformed `cancelled_at` (missing `Z`, date only, free text).
- [ ] Rejects `cancelled_evidence` pointing at a path that does not exist.
- [ ] Rejects `cancelled_evidence` pointing at an existing file that lacks the
      `**Status:** CANCELLED` line.
- [ ] Accepts a big plan with `status: cancelled` and no `started_at` and no
      `current_phase`.
- [ ] Rejects the near-miss spellings `canceled` and `abandoned` as invalid
      statuses, proving the single-literal rule fails loudly.
- [ ] Regression: existing `planning`, `in-progress`, and `complete` behavior is
      unchanged, including that a `complete` small plan still requires
      `closeout_session_log`.
- [ ] Regression: `uv run python scripts/validate_plan_frontmatter.py` with no
      arguments still passes over every current file in `.claude/plans/`.

## Verification

```bash
uv sync
uv run pytest tests/test_validate_plan_frontmatter.py -q --tb=short
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/quality_score.py scripts/ --phase 2026-08-09_phase-C-cancelled-status-contract --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
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

- The frontmatter parser is hand-rolled. It splits on the first `:` and strips
  surrounding quotes, so a `cancelled_reason` containing a colon parses
  correctly but one starting with a quote character loses it. The templates and
  policy must say reasons are plain single-line prose without leading quotes.
- Requiring an evidence artifact could read as ceremony. It is the anti-abuse
  property and it costs exactly what a closeout log already costs; the
  alternative is a status any agent can set with one word and no trace.
- This phase alone makes the validator more permissive while the push gate stays
  strict, so a plan can be marked `cancelled` and still be refused at push until
  Phase D lands. That direction errs strict and is the reason for this ordering.
- Adding a new status is a control-plane vocabulary change that every consumer
  inherits on refresh. Regeneration and `validate_targets.py` must both pass
  before the phase closes.

## Acceptance Criteria

- [ ] `cancelled` is a valid status for both plan types.
- [ ] A `cancelled` plan without all three fields fails validation.
- [ ] A `cancelled` plan whose evidence file is missing or lacks
      `**Status:** CANCELLED` fails validation.
- [ ] A `cancelled` big plan needs no `started_at` and no `current_phase`.
- [ ] A `cancelled` small plan needs no `closeout_session_log`.
- [ ] `canceled` and `abandoned` are rejected as invalid statuses.
- [ ] Templates, session-log template, plans README, and the workflow policy all
      describe the same contract.
- [ ] Every existing plan file still validates unchanged.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
