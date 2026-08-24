---
name: 2026-08-24_phase-A-paused-phase-checkpoint-lifecycle
type: small-plan
parent_plan: paused-phase-checkpoint-lifecycle
phase_index: 0
status: in-progress
closeout_session_log:
---

# Phase A: Paused phase checkpoint lifecycle

## Scope

Implement the complete paused-phase checkpoint feature in one control-plane phase.

A user must be able to stop a long-running current phase at a deliberate safe boundary, preserve real tracked work in an outer-repository checkpoint commit, record a PAUSED session log, and resume the same phase later.

The checkpoint must not claim that verification, review, score, LEARN, documentation, or phase closeout are complete.

This phase changes all layers that define that contract together:

- small-plan frontmatter validation;
- pause evidence;
- commit-gate branching;
- post-commit phase advancement;
- session-log/template guidance;
- orchestrator pause/resume behavior;
- generated-target integration tests;
- repository documentation.

Do not split this work into additional small plans unless current `dev` exposes a concrete blocker that makes one atomic change unsafe.

## Pre-flight

Before editing:

1. update/rebase from current `dev`;
2. run baseline generation, plan validation, hook tests, and target validation;
3. inspect the current implementations of:
   - `scripts/validate_plan_frontmatter.py`;
   - `shared/hooks/scripts/_lib-frontmatter.sh`;
   - `shared/hooks/scripts/enforce-commit-gate.sh`;
   - `shared/hooks/scripts/record-commit-closeout.sh`;
   - the push/PR invariant implementation;
   - `shared/templates/plan-small.md`;
   - `shared/templates/session-log.md`;
   - `shared/plans/README.md`;
   - `shared/policies/workflow.instructions.md`;
   - `shared/agents/orchestrator/prompt.md`;
   - `scripts/validate_targets.py`;
   - `tests/test_validate_plan_frontmatter.py`;
   - `tests/test_hook_gates.py`;
4. confirm the already-landed `cancelled` behavior and preserve it;
5. use current function/file names when they differ from older plans.

Do not apply this plan against a pre-cancellation snapshot.

## Approved execution note

This plan is intentionally one phase.

Do not delegate a planner merely to subdivide it. If PLAN delegation is mechanically required, use a confirmation-only pass.

A redesign is justified only if live `dev` proves a material assumption wrong.

## Ownership

### Coder

Own:

- small-plan `paused` status validation;
- pause evidence helper(s);
- checkpoint branch in commit invariants;
- post-commit no-advance behavior for paused phases;
- orchestrator/workflow contract changes;
- focused deterministic tests.

### Verifier

Own:

- focused status-validator tests;
- direct hook invariant tests;
- generated-consumer gate tests;
- cancellation/completion regression checks;
- push/PR regression checks;
- generation and determinism;
- full repository verification.

### Reviewer

Run one consolidated reviewer delegation with:

- `code`;
- `architecture`;
- `security`;
- `tests`;
- `ponytail`;
- `documentation`.

This is control-plane/high-risk work. Review the gate relaxation as a security boundary, even though it is user-authorized workflow behavior.

### Documenter

After review converges:

- update `README.md` and the detailed commit-gate documentation where needed;
- use `humanize` in targeted `edit` mode for changed human-facing prose;
- preserve code, commands, paths, identifiers, status literals, field names, and test names exactly;
- do not add sales language or claim formal ASD-STE100 compliance.

## Required Skills

For implementation/review as applicable:

- `.claude/skills/create-feature/SKILL.md`;
- `.claude/skills/ponytail/SKILL.md` in `full` mode;
- `.claude/skills/code-style/SKILL.md`;
- `.claude/skills/testing-patterns/SKILL.md`;
- `.claude/skills/run-tests/SKILL.md`;
- `.claude/skills/documentation/SKILL.md`;
- `.claude/skills/humanize/SKILL.md` for the documenter;
- `.claude/skills/learn/SKILL.md`;
- `.claude/skills/commit/SKILL.md`.

## Review focus

The reviewer must specifically test these claims:

1. `paused` cannot silently become a general quality-gate bypass.
2. Only a current small plan can use the checkpoint path.
3. A paused checkpoint does not mutate big-plan completion state.
4. `cancelled` stays terminal and non-committing.
5. `complete` keeps every current final gate.
6. The pause evidence path cannot crash on a missing/unreadable file.
7. Generated consumers receive the same hook behavior as the source bootstrap.
8. Bash changes remain compatible with the repository's supported macOS `/bin/bash` constraints.
9. Pause/resume instructions do not cause a second small plan to be created for the same work.
10. Push/PR closeout still rejects unfinished paused work.

## Design contract

### Small-plan status

Extend only the small-plan vocabulary:

```text
in-progress
paused
complete
cancelled
```

Do not add `paused` to big plans.

### Required pause frontmatter

A small plan with `status: paused` requires:

```yaml
paused_at: 2026-08-24T12:34:56Z
paused_reason: user requested an overnight checkpoint after model 1 completed
pause_session_log: .claude/session_logs/2026-08-24_<description>.md
```

Rules:

- `paused_at` must match the repository's UTC timestamp convention;
- `paused_reason` must be non-empty single-line prose;
- `pause_session_log` may be repository-relative;
- the resolved log must exist;
- the log must contain a line matching the repository's status-marker style for `**Status:** PAUSED`;
- a paused small plan does not require `closeout_session_log`.

Do not require new frontmatter fields on `in-progress`, `complete`, or `cancelled`.

Pause metadata may remain after resume/completion as historical evidence. It is required and validated only when current status is `paused`, unless the live validator already has a consistent stronger pattern that can be reused without breaking existing plans.

### PAUSED session log

Extend the session-log template with a PAUSED variant.

At minimum a pause log records:

```text
**Status:** PAUSED
**Plan:** .claude/plans/<current-small-plan>.md
```

The prose/template must also request:

```text
Pause reason
Completed work
Verification already run
Known failures or incomplete checks
Remaining work
Resume next
Useful resume command/config/model identifier when applicable
```

Only the stable status/evidence marker needs machine validation.

Do not add a fragile parser for the free-text resume sections.

### Commit-gate dispatch

Refactor only as much as needed to make the status branches explicit.

Conceptually:

```text
common branch/current-phase invariants

status == complete
    -> existing completion invariants unchanged

status == paused
    -> pause evidence invariants
    -> allow checkpoint commit

status == cancelled
    -> reject commit

status == in-progress
    -> reject commit

anything else
    -> reject commit
```

The paused path must not require:

- final `closeout_session_log`;
- score >= 90;
- persisted final findings;
- `counts.critical == 0`;
- `[LEARN]`;
- DOCUMENT completion.

Those are completion claims and remain mandatory when the phase later becomes `complete`.

Do not remove common invariants that establish:

- correct implementation branch;
- valid current big plan;
- valid `current_phase`;
- current small-plan identity;
- other existing basic safety preconditions that are independent of final quality certification.

Do not use the bypass-prefix mechanism for pause commits.

### Explicit-user policy

Update workflow/orchestrator guidance:

- `paused` is allowed only after explicit user intent to pause/checkpoint/stop and resume later;
- if the user names a safe boundary such as "after the current model finishes", reach that boundary before pausing when execution can safely do so;
- verification failure alone does not authorize pause;
- an agent must not mark `paused` simply to get a commit through the gate.

The repository cannot prove conversational authority cryptographically. The pause reason and PAUSED session log make the decision visible and reviewable.

### Post-commit behavior

Update `record-commit-closeout.sh` or the current equivalent.

When the current phase is `paused` after a successful checkpoint commit:

- do not advance `current_phase`;
- do not mark the small plan complete;
- do not mark the big plan complete;
- do not select the next phase;
- keep the big plan `in-progress`;
- allow normal post-commit AI-state checkpoint/publish behavior to run.

When the current phase is `complete`:

- preserve existing phase advancement, including current cancellation-aware skip behavior.

Do not change cancellation semantics.

### Resume behavior

Update workflow/orchestrator guidance for session start when current phase is paused:

1. read the paused small plan;
2. read `pause_session_log`;
3. inspect recent Git history and working-tree state;
4. report the recorded resume point;
5. change `status: paused` to `status: in-progress`;
6. preserve the latest pause metadata;
7. continue the same small plan.

Do not create a replacement small plan.

Do not rerun already-completed expensive work automatically when the pause log/config/results prove it remains valid. Re-run only when inputs/config/code changed or verification requires it.

### No empty checkpoint commit

If there are no tracked outer-repository changes:

- do not use `git commit --allow-empty`;
- persist the PAUSED plan state and session log in AI state;
- use the existing state-sync checkpoint/publish path;
- stop with the phase still paused.

### Push/PR behavior

A paused phase is unfinished.

Do not make it eligible for push/PR closeout.

Add a regression scenario that proves the push/PR invariant rejects a big plan while any required current phase is `paused`.

Do not change the push/PR implementation unless a focused test proves that an earlier checkpoint commit breaks later completed-plan closeout.

If current commit-count logic already means "at least one commit per completed phase", preserve it.

## Expected source changes

Expected:

```text
scripts/validate_plan_frontmatter.py

shared/hooks/scripts/_lib-frontmatter.sh
shared/hooks/scripts/record-commit-closeout.sh

shared/templates/plan-small.md
shared/templates/session-log.md
shared/plans/README.md
shared/policies/workflow.instructions.md
shared/agents/orchestrator/prompt.md

scripts/validate_targets.py
tests/test_validate_plan_frontmatter.py
tests/test_hook_gates.py
tests/test_validate_targets.py

README.md
docs/plan-deterministic-commit-gate.md
```

Conditional only if the live implementation requires it:

```text
shared/hooks/scripts/enforce-commit-gate.sh
shared/hooks/scripts/enforce-pr-gate.sh
scripts/generate_targets.py
```

Do not modify `shared/templates/plan-big.md` unless a focused test proves a comment/reference must change. The big-plan status vocabulary does not change.

Never hand-edit generated `dist/`.

## Steps

- [ ] **1. Reconfirm the live status/gate implementation**
  - Run baseline tests.
  - Confirm current `complete` and `cancelled` paths.
  - Identify the exact function that owns commit invariants.
  - Identify the exact post-commit function that advances `current_phase`.
  - Confirm whether push/PR commit counting is lower-bound or exact.
  - Record any difference from this plan before editing.

- [ ] **2. Add `paused` to small-plan validation**
  - Add `paused` only to the small-plan allow-list.
  - Add `PAUSED_FIELDS` or the current codebase's equivalent:
    - `paused_at`;
    - `paused_reason`;
    - `pause_session_log`.
  - Add a focused pause validator using the existing cancellation-validation style where appropriate.
  - Validate timestamp, non-empty reason, evidence-file existence/readability, and `**Status:** PAUSED`.
  - Convert missing/unreadable evidence into accumulated validation errors, not uncaught exceptions.
  - Preserve existing `complete` and `cancelled` validation.

- [ ] **3. Update the plan and session-log contracts**
  - Update `shared/templates/plan-small.md`.
  - Update `shared/templates/session-log.md`.
  - Update `shared/plans/README.md`.
  - Document `paused` as non-terminal.
  - Document the three required fields.
  - Document that a paused phase has no `closeout_session_log`.
  - Document resume behavior and latest-pause metadata behavior.

- [ ] **4. Add the checkpoint branch to commit invariants**
  - Keep common branch/current-phase checks shared.
  - Preserve the current completion path byte-for-byte where practical.
  - Add a `paused` branch that validates pause evidence and permits the checkpoint without final quality artifacts.
  - Keep `in-progress` blocked.
  - Keep `cancelled` blocked.
  - Produce distinct actionable messages for invalid pause evidence.
  - Do not use or extend the existing bypass-prefix list.

- [ ] **5. Prevent checkpoint commits from advancing phase state**
  - Teach `record-commit-closeout.sh` or the live equivalent to detect `paused`.
  - On paused checkpoint commit, leave `current_phase` and big-plan status unchanged.
  - Preserve existing complete/cancelled advancement logic.
  - Keep existing warn-on-miss behavior and Bash compatibility.

- [ ] **6. Teach the orchestrator the pause/resume branch**
  - Update `shared/policies/workflow.instructions.md`.
  - Update `shared/agents/orchestrator/prompt.md`.
  - Keep the canonical completion loop unchanged.
  - Add a conditional pause branch, not a mandatory new lifecycle step.
  - Require explicit user intent.
  - Require PAUSED session log before checkpoint commit.
  - On resume, reopen the same phase and set it back to `in-progress`.
  - State that final verification/review/document/score/LEARN/COMPLETED closeout still run once at real phase completion.
  - State that no empty checkpoint commit is created.

- [ ] **7. Add focused validator tests**
  - Extend `tests/test_validate_plan_frontmatter.py`.
  - Prefer parameterized missing-field cases.
  - Do not use whole-file snapshots.

- [ ] **8. Add direct hook tests**
  - Extend `tests/test_hook_gates.py` using the current Bash-source/test harness.
  - Cover both checkpoint acceptance and forbidden bypass cases.
  - Cover post-commit non-advancement.

- [ ] **9. Add generated-target integration scenarios**
  - Extend `scripts/validate_targets.py` and `tests/test_validate_targets.py` using current helpers.
  - Exercise the generated hook/runtime surface, not only source helper functions.
  - Verify source/generated parity.

- [ ] **10. Update repository-facing documentation**
  - Update `README.md` only where the main lifecycle/commit description would otherwise be false.
  - Update `docs/plan-deterministic-commit-gate.md` with the two commit paths.
  - Keep wording explicit:
    - checkpoint commit = durable incomplete work;
    - completion commit = certified completed small plan.
  - Document that paused branches remain blocked from push/PR closeout in v1.
  - Document that no final quality claim is made by a checkpoint.

- [ ] **11. Generate and inspect**
  - Run target generation.
  - Inspect generated hook/templates/policy/orchestrator diffs.
  - Verify no unrelated target drift.
  - Do not hand-edit generated output.

- [ ] **12. Run one consolidated control-plane review**
  - Use all required profiles in one reviewer invocation.
  - Resolve surviving blocking findings.
  - Repeat implementation/verification/review only when a fix changes code.

- [ ] **13. Run final full verification once**
  - Run focused tests first.
  - Run complete tests/type/lint/format.
  - Run generation, target validation, plan validation, runtime check, and determinism.
  - Run a disposable-consumer checkpoint/resume smoke test if the current test harness does not already exercise the actual installed hook path.

- [ ] **14. Score, learn, close out, and commit once**
  - Persist final findings for this implementation phase.
  - Run the normal quality score; require >= 90.
  - Run LEARN.
  - Run DOCUMENT before final persisted score/findings if documentation changed, per current lifecycle.
  - Record `**Status:** COMPLETED` for this implementation phase.
  - Mark this small plan complete.
  - Create one normal completion commit for the bootstrap feature implementation.

## Test scenarios

### Plan validator

- [ ] Accept a small plan with:
  - `status: paused`;
  - valid `paused_at`;
  - non-empty `paused_reason`;
  - `pause_session_log` pointing to an existing log with `**Status:** PAUSED`.
- [ ] Reject `paused` with each required pause field missing in turn.
- [ ] Reject malformed `paused_at`.
- [ ] Reject missing pause-session-log file.
- [ ] Reject unreadable pause-session-log file as a clean validation failure where practical.
- [ ] Reject a pause log that lacks `**Status:** PAUSED`.
- [ ] Reject `paused` as a big-plan status.
- [ ] Reject near-miss statuses such as `pause`.
- [ ] Regression: `complete` still requires `closeout_session_log`.
- [ ] Regression: existing `cancelled` evidence contract is unchanged.
- [ ] Regression: all current plan files validate unchanged.

### Commit invariants

- [ ] Valid paused current phase permits a checkpoint commit without:
  - score report;
  - findings report;
  - LEARN marker;
  - completed closeout log.
- [ ] `status: paused` with missing evidence blocks commit.
- [ ] `status: paused` with wrong log marker blocks commit.
- [ ] `status: in-progress` still blocks commit.
- [ ] `status: cancelled` still blocks commit.
- [ ] `status: complete` with missing score/findings/LEARN/closeout still blocks commit exactly as before.
- [ ] Existing completion success fixture still passes unchanged.
- [ ] Existing bypass-subject behavior is unchanged and is not required for pause.

### Post-commit phase state

- [ ] A successful paused checkpoint leaves `current_phase` on the same phase.
- [ ] A successful paused checkpoint leaves the big plan `in-progress`.
- [ ] A paused checkpoint does not write `status: complete`.
- [ ] A normal completion commit still advances to the next eligible phase.
- [ ] Existing cancellation-aware phase skipping remains unchanged.
- [ ] Final completion after an earlier checkpoint still closes normally.

### Resume

- [ ] A paused phase can be changed back to `in-progress`.
- [ ] The same `current_phase` is reused.
- [ ] Previous pause metadata may remain without invalidating the in-progress plan.
- [ ] A resumed `in-progress` phase cannot commit again until it is either paused with fresh evidence or fully complete.
- [ ] A second pause can replace the latest pause metadata and point to a new PAUSED session log.

### Push/PR regression

- [ ] A big plan with a paused phase is rejected by push/PR closeout.
- [ ] A paused checkpoint does not cause `paused` to be counted as a completed phase.
- [ ] After the phase later completes, the existence of an earlier checkpoint commit does not by itself break push/PR closeout under the current commit-count contract.
- [ ] Existing complete/cancelled mixed-plan scenarios remain valid.

### Generated target

- [ ] Generated plan template documents `paused`.
- [ ] Generated session-log template documents PAUSED.
- [ ] Generated workflow/orchestrator guidance contains the same pause/resume contract.
- [ ] Generated commit gate accepts the valid pause fixture.
- [ ] Generated post-commit hook does not advance the paused phase.
- [ ] Existing Claude/Codex/Copilot/other supported target behavior remains valid.

## Verification

Run focused checks first:

```bash
uv sync
uv run pytest tests/test_validate_plan_frontmatter.py tests/test_hook_gates.py tests/test_validate_targets.py -q --tb=short
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

Then run the full repository checks:

```bash
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/check_runtime.py
```

Run the repository's current self-install/runtime smoke path if it is part of the live control-plane verification contract and can be run without overwriting authoring files.

Generator determinism after edits settle:

```bash
uv run python scripts/generate_targets.py --all
cp -a dist /tmp/dist-paused-a
uv run python scripts/generate_targets.py --all
diff -r /tmp/dist-paused-a dist
rm -rf /tmp/dist-paused-a
```

Persist final quality evidence using the current canonical commands. Expected score invocation shape:

```bash
uv run python .claude/scripts/quality_score.py scripts/ shared/ tests/ \
  --phase 2026-08-24_phase-A-paused-phase-checkpoint-lifecycle \
  --base-ref dev \
  --json \
  --out .claude/quality_reports/score-<timestamp>.json
```

Use the live command/path contract if current `dev` differs.

## Risks

### 1. `paused` becomes a generic bypass

Risk:

An agent could mark work paused to avoid quality gates.

Mitigation:

- policy requires explicit user intent;
- frontmatter requires timestamp/reason/evidence;
- PAUSED session log records incomplete work and resume point;
- checkpoint does not advance phase state;
- paused branch remains blocked from push/PR closeout;
- final completion still requires every normal quality gate.

### 2. Post-commit hook accidentally closes the phase

Risk:

The existing post-commit hook may assume every permitted commit is a completion commit.

Mitigation:

Add an explicit `paused` no-advance branch and direct regression tests before changing documentation.

### 3. Pause logic weakens `cancelled`

Risk:

A shared status refactor could make cancellation commit-capable or resumable.

Mitigation:

Do not generalize the state machine. Preserve the existing cancellation helper/semantics and add explicit cancellation regression tests.

### 4. Python and Bash evidence contracts drift

Risk:

The frontmatter validator and commit hook may validate pause evidence differently.

Mitigation:

Use the same three field names and the same `**Status:** PAUSED` marker in both layers. Keep the rules simple and cover them in both test suites.

### 5. Checkpoint commits confuse commit-count logic

Risk:

One phase can now have a checkpoint commit plus its final completion commit.

Mitigation:

Confirm the live push/PR gate's current commit-count semantics. Preserve the existing lower-bound completed-phase rule when already present. Do not add commit-subject parsing or history classification unless a focused test proves the gate rejects the valid checkpoint-then-complete history.

### 6. Pause state is written but outer work has nothing to commit

Risk:

The orchestrator may create meaningless empty commits.

Mitigation:

Explicitly forbid `--allow-empty` checkpoint commits. Persist only AI state when no outer tracked changes exist.

### 7. Resume repeats expensive work

Risk:

The next session ignores the pause record and restarts long evaluation from the beginning.

Mitigation:

Require the PAUSED session log to record completed work, verification, remaining work, and exact resume point. Orchestrator resume guidance reads it before delegating.

### 8. Over-engineering the lifecycle

Risk:

A narrow checkpoint feature turns into a generic workflow engine or new quality-report model.

Mitigation:

One new small-plan status, three evidence fields, one commit branch, one post-commit branch, direct tests, and documentation. No new subsystem.

## Must not change

- Final score threshold.
- Final findings severity rules.
- LEARN requirement for completed phases.
- COMPLETED closeout requirement for completed phases.
- `cancelled` semantics.
- Existing bypass prefixes.
- Big-plan status vocabulary.
- Branch naming.
- One-big-plan-to-one-implementation-branch rule.
- User-controlled PR creation.
- Protected-file and dangerous-Git policies.
- AI-state storage model.
- Generated output by direct editing.

## Acceptance criteria

- [ ] `paused` is valid for small plans only.
- [ ] A paused small plan requires `paused_at`, `paused_reason`, and `pause_session_log`.
- [ ] Missing/invalid pause evidence fails cleanly.
- [ ] PAUSED session log records enough state for deterministic resume.
- [ ] A valid paused current phase can checkpoint-commit real tracked outer work.
- [ ] The checkpoint path does not require final score/findings/LEARN/DOCUMENT/COMPLETED closeout.
- [ ] `in-progress` still cannot commit.
- [ ] `cancelled` still cannot commit.
- [ ] `complete` still requires every existing final gate.
- [ ] A checkpoint commit does not advance `current_phase`.
- [ ] A checkpoint commit does not complete the big plan.
- [ ] Resume changes the same small plan back to `in-progress`.
- [ ] No replacement small plan is created on resume.
- [ ] No empty outer checkpoint commit is created when only AI state changed.
- [ ] A paused phase remains blocked from push/PR closeout.
- [ ] An earlier checkpoint commit does not prevent later normal completion.
- [ ] Existing cancellation tests pass unchanged.
- [ ] Existing normal completion tests pass unchanged.
- [ ] Generated targets carry the same behavior.
- [ ] Documentation distinguishes checkpoint durability from completion certification.
- [ ] Full repository verification passes.
- [ ] Generated output is deterministic.
- [ ] One implementation phase closes with one normal completion commit.

## Closeout checklist

- [ ] Coder reports final changed-file set and any evidence-backed deviation from expected paths.
- [ ] Verifier reports focused pause tests and full verification.
- [ ] Reviewer resolves or explicitly accepts findings according to repository gates.
- [ ] DOCUMENT is completed before final persisted score/findings when documentation changed.
- [ ] Documenter applies targeted `humanize edit` to changed human-facing prose.
- [ ] Quality score >= 90 is persisted.
- [ ] Final findings satisfy normal completion gates.
- [ ] LEARN is completed.
- [ ] Closeout session log records `**Status:** COMPLETED`.
- [ ] Small plan status is `complete`.
- [ ] One normal implementation completion commit is created.
