---
name: paused-phase-checkpoint-lifecycle
type: big-plan
status: planning
originating_branch: dev
implementation_branch: paused-phase-checkpoint-lifecycle_implementation
started_at:
phases:
  - 2026-08-24_phase-A-paused-phase-checkpoint-lifecycle
current_phase:
---

# Big Plan: Paused phase checkpoint lifecycle

## Context

The bootstrap currently treats an outer-repository commit as proof that the current small plan is complete.

That is correct for normal phase closeout, but it leaves no valid path for a deliberate checkpoint during long-running work.

The concrete failure mode is a phase that runs the same expensive local evaluation suite across several LLMs. One model can finish after substantial local runtime while the remaining models still need to run. If the user asks the orchestrator to stop after that safe boundary and resume later, the current lifecycle forces one of two bad choices:

- keep running until the whole phase is complete;
- stop without a normal outer-repository commit.

Neither choice means the phase failed or was cancelled. The phase is still active and is expected to resume.

The bootstrap already distinguishes terminal cancellation from successful completion. `cancelled` must stay terminal and must not certify a commit. This plan adds a separate non-terminal `paused` state for a current small plan and a narrowly scoped checkpoint-commit path.

## Pre-flight authority

Before implementation, re-read current `dev`.

The live checkout is authoritative for:

- `scripts/validate_plan_frontmatter.py`;
- `shared/hooks/scripts/_lib-frontmatter.sh`;
- `shared/hooks/scripts/enforce-commit-gate.sh`;
- `shared/hooks/scripts/record-commit-closeout.sh`;
- the current push/PR gate;
- plan/session-log templates;
- workflow/orchestrator guidance;
- current generated-target validation and hook tests.

Do not restore older pre-cancellation versions of these files.

Preserve the existing `cancelled` behavior and the current quality/findings/LEARN/closeout requirements for a completed phase.

## Goal

Allow the user to deliberately pause the current small plan at a safe boundary, record enough state to resume it, create a checkpoint commit for tracked outer-repository work, and continue the same phase later without falsely marking it complete.

## Non-goals

- No relaxation of final completion requirements.
- No use of `paused` as a response to failed verification, review, or score unless the user explicitly asks to stop.
- No automatic pause chosen by an agent merely to bypass a gate.
- No `paused` status for big plans.
- No new terminal state.
- No replacement or weakening of `cancelled`.
- No checkpoint commit for a cancelled phase.
- No automatic `--allow-empty` commit when the outer repository has no tracked changes.
- No new quality-score mode for partial work.
- No partial findings report requirement.
- No LEARN requirement at pause time.
- No DOCUMENT requirement at pause time.
- No push/PR relaxation in v1. A branch with a paused phase remains not ready for push/PR closeout under the existing completion policy.
- No generic workflow/state-machine framework.
- No broad refactor of the frontmatter parser or hook library.

## Design decisions

### 1. `paused` belongs to small plans only

Small-plan status vocabulary becomes:

```text
in-progress
paused
complete
cancelled
```

Big-plan status vocabulary does not gain `paused`.

When the current small plan is paused:

- the big plan remains `in-progress`;
- `current_phase` remains the paused phase;
- the phase is not advanced;
- the phase is expected to resume.

This keeps the existing branch and big-plan lifecycle intact.

### 2. `paused` is non-terminal

State transitions:

```text
in-progress -> paused -> in-progress
in-progress -> complete
in-progress -> cancelled
paused      -> cancelled
```

A normal successful phase still ends only at `complete`.

Do not support `paused -> complete` as a shortcut. Resume the phase to `in-progress`, finish the normal lifecycle, then mark it `complete`.

### 3. Pause requires explicit user intent

The orchestrator may enter `paused` only after an explicit user request to stop, checkpoint, pause, or resume later.

Examples:

- "stop after this test finishes";
- "checkpoint here and continue tomorrow";
- "pause this phase after model 1 completes".

A failed test, review finding, low score, timeout, or agent fatigue is not by itself authority to mark the phase paused.

This is an audited policy boundary, not a claim that repository files can cryptographically prove who requested the pause.

### 4. Pause evidence is explicit and small

A paused small plan requires:

```yaml
status: paused
paused_at: 2026-08-24T12:34:56Z
paused_reason: user requested an overnight checkpoint after model 1 completed
pause_session_log: .claude/session_logs/2026-08-24_<description>.md
```

`paused_at` uses the same UTC timestamp shape as other lifecycle evidence.

`paused_reason` is non-empty single-line prose.

`pause_session_log` must resolve to an existing file that contains:

```text
**Status:** PAUSED
```

The session log must also record, in normal prose:

- what completed;
- what remains;
- verification already run and its result;
- known failures or incomplete checks;
- exact next step for resume;
- useful resume command/config/model identifier when applicable.

Do not make those free-text sections brittle machine-parsed fields.

### 5. A checkpoint commit is not a completion commit

The commit gate gets two explicit paths.

Completion path:

```text
status == complete
-> existing closeout_session_log requirement
-> existing verification/score/findings requirements
-> existing LEARN requirement
-> existing documentation/closeout requirements
-> commit
```

Checkpoint path:

```text
status == paused
-> validate pause evidence
-> preserve all common branch/current-phase safety checks
-> do not require final score/findings/LEARN/DOCUMENT/COMPLETED closeout
-> allow checkpoint commit
```

`in-progress` still cannot commit.

`cancelled` still cannot certify a commit.

Do not route `paused` through the existing bypass-subject mechanism. A pause checkpoint is an explicit lifecycle path, not a bypass.

Do not require a special commit-subject prefix. The commit skill may use a clear conventional subject such as `chore(checkpoint): ...`, but status/evidence is the authority.

### 6. Checkpoint commit must not advance the phase machine

The post-commit closeout hook must distinguish the current plan status.

For `complete`:

- keep existing phase-advance behavior.

For `paused`:

- keep `current_phase` unchanged;
- keep the big plan `in-progress`;
- do not set the phase complete;
- do not advance to the next phase;
- allow the normal durable AI-state checkpoint/publish path to record the pause metadata and session log.

For `cancelled`:

- preserve existing cancellation behavior.

### 7. Resume reopens the same phase

At the start of a later session, if `current_phase` points to a small plan with `status: paused`:

1. read the paused small plan;
2. read `pause_session_log`;
3. inspect `git log --oneline -10`, `git status`, and the current diff;
4. state the recorded resume point;
5. change the small plan back to `status: in-progress`;
6. preserve the last pause metadata for audit;
7. continue the same phase.

Do not create another small plan merely because execution crossed a session boundary.

A later pause may replace the `paused_at`, `paused_reason`, and `pause_session_log` frontmatter with the newest pause record. Older pause logs remain in AI-state history.

### 8. No empty outer checkpoint commits

If no tracked outer-repository changes exist at the requested pause point:

- write the paused plan state and PAUSED session log;
- publish/checkpoint AI state through the normal state-sync path;
- do not create an empty outer commit solely for ceremony.

The checkpoint-commit path exists to preserve real outer-repository work.

### 9. Push/PR closeout stays strict

Do not make a paused branch merge-ready.

A paused phase remains unfinished, so the existing push/PR closeout gate must continue to reject it.

The implementation must add regression coverage proving that `paused` does not accidentally become equivalent to `complete` or `cancelled` in the push/PR path.

If the current push gate already accepts extra commits as long as every required completed phase has its completion evidence, preserve that behavior. Do not add commit-history parsing unless the live code proves it is necessary.

## One small phase, intentionally

This feature is implemented in one small plan:

```text
2026-08-24_phase-A-paused-phase-checkpoint-lifecycle.md
```

Do not split schema/templates, commit gating, post-commit behavior, and workflow documentation into separate phases.

They define one lifecycle contract. Landing them separately would create an intermediate bootstrap where one layer accepts `paused` while another rejects or mishandles it.

One control-plane phase also avoids extra review/score/commit ceremony for changes that must be verified together.

## Expected source surfaces

Expected changes include:

```text
scripts/validate_plan_frontmatter.py

shared/hooks/scripts/_lib-frontmatter.sh
shared/hooks/scripts/enforce-commit-gate.sh          # only if live dispatch/messages require it
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

Use the live `dev` layout as authority.

Do not modify:

```text
shared/templates/plan-big.md
shared/hooks/scripts/enforce-branch-state.sh
shared/hooks/scripts/enforce-pr-gate.sh
scripts/generate_targets.py
```

unless a focused failing test proves the current implementation requires a narrow change.

Never hand-edit generated `dist/`.

## Phase

### Phase A — Paused phase checkpoint lifecycle

Implement and verify the complete contract:

- small-plan `paused` status;
- pause evidence validation;
- PAUSED session-log contract;
- checkpoint commit path;
- no phase advancement after a checkpoint commit;
- resume guidance;
- strict completion behavior preserved;
- strict cancellation behavior preserved;
- paused phase still blocked from push/PR closeout;
- generated-target parity;
- documentation;
- full control-plane review and final repository verification.

## Repository-wide acceptance

Before parent completion:

- the single small plan is complete;
- `paused` is valid only for small plans;
- a valid paused phase can checkpoint-commit tracked work without final quality artifacts;
- invalid or unaudited pause state cannot commit;
- `in-progress` still cannot commit;
- `cancelled` still cannot commit;
- `complete` still requires every existing final gate;
- a paused checkpoint commit does not advance `current_phase`;
- resume continues the same phase;
- paused phases remain non-pushable/non-PR-ready;
- generated targets carry the same behavior;
- full tests/type/lint/format/generation/runtime checks pass;
- generated output is deterministic;
- documentation describes checkpoint commits as incomplete work, never as certified completion;
- final findings satisfy the normal repository gates;
- quality score is >= 90 for this implementation phase;
- final AI-state closeout is published through the normal durable state-sync path.

## References

Bootstrap:

- https://github.com/Ghisso/github_copilot_bootstrap/tree/dev
- `shared/policies/workflow.instructions.md`
- `shared/agents/orchestrator/prompt.md`
- `scripts/validate_plan_frontmatter.py`
- `shared/hooks/scripts/_lib-frontmatter.sh`
- `shared/hooks/scripts/record-commit-closeout.sh`
- `docs/plan-deterministic-commit-gate.md`
