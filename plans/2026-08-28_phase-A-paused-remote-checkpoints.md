---
name: 2026-08-28_phase-A-paused-remote-checkpoints
type: small-plan
parent_plan: paused-push-copilot-vscode-parity
phase_index: 1
# status must occur exactly once: in-progress | paused | complete | cancelled
status: complete
closeout_session_log: .claude/session_logs/2026-08-29_paused-remote-checkpoints.md
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---
# Small Plan: 2026-08-28_phase-A-paused-remote-checkpoints

## Scope

Allow a valid paused implementation-phase checkpoint to be pushed to a remote without making the branch PR-ready. Reuse the existing pause evidence and pushed-SHA inputs. Preserve the current strict final push/PR closeout path for completed/cancelled plans.

This phase changes control-plane shell logic, executable regression fixtures, and lifecycle documentation. Use `ponytail/SKILL.md` in `full` mode for implementation and run review profiles `code`, `architecture`, `security`, `tests`, and `ponytail`.

### Required Skills

- `.claude/skills/ponytail/SKILL.md` — `full`
- `.claude/skills/ponytail-review/SKILL.md`
- `.claude/skills/commit/SKILL.md` when closing the phase

### Primary Files

Modify:

- `shared/hooks/scripts/_lib-frontmatter.sh`
- `shared/hooks/scripts/enforce-pr-gate.sh`
- `scripts/validate_targets.py`
- `shared/policies/workflow.instructions.md`
- `shared/skills/commit/SKILL.md`
- `shared/agents/orchestrator/prompt.md`
- `shared/templates/plan-small.md`
- `README.md`

Regenerate; do not hand-edit:

- `dist/multi-agent/**`

Default to **no change** in `shared/hooks/git-hooks/pre-push`. It already calls `assert_push_invariants "$REPO_ROOT" "$branch" "$local_sha"` with the actual ref being pushed. Change it only if implementation proves that its current caller contract cannot support the split.

## Steps

- [ ] **1. Split paused publication from strict closeout in `shared/hooks/scripts/_lib-frontmatter.sh`.**
  - Owner: `coder`
  - Required Skills: `ponytail/SKILL.md` (`full`)
  - Keep the current strict terminal behavior as one helper, preferably `assert_closeout_invariants(repo_root, branch, local_sha)` or an equivalently clear name.
  - Preserve the existing strict helper body as much as possible:
    - every listed phase must be `complete` or evidenced `cancelled`;
    - at least one phase must be complete;
    - `dev..local_sha` commit count must cover completed phases;
    - bypass acknowledgment remains required where it is required today;
    - final findings freshness, `counts.major == 0`, and required Ponytail review remain required.
  - Keep `assert_push_invariants(repo_root, branch, local_sha)` as the public push entry point used by the native pre-push hook.
  - Make `assert_push_invariants` choose the paused-publication path only when the big plan's current phase is validly `paused`; otherwise delegate to the strict closeout helper.
  - The paused-publication path must:
    1. require the big-plan file for the implementation branch;
    2. require exactly one big-plan status and `status: in-progress`;
    3. require a non-empty safe `current_phase`;
    4. require `current_phase` to appear in the big plan `phases` list;
    5. require the current small-plan file;
    6. require `type: small-plan` and `parent_plan` matching the big-plan slug, using existing frontmatter helpers/contracts rather than a new parser;
    7. require exactly one current small-plan status and `status: paused`;
    8. call the existing `assert_pause_evidence` for `paused_at`, `paused_reason`, and `pause_session_log`;
    9. validate every phase *before* `current_phase`:
       - `complete` increments the prior completed count;
       - `cancelled` must pass existing cancellation evidence;
       - any other or missing/duplicate status blocks the push;
    10. ignore the status of phases *after* `current_phase` for checkpoint publication; future pre-created phases must not block backup;
    11. require `git rev-list --count "dev..$local_sha"` to be at least `prior_completed_count + 1`.
  - The `+1` is the paused checkpoint commit. This intentionally supports a first-phase pause with zero completed phases.
  - Do **not** add:
    - `pause_checkpoint_sha`;
    - new pause metadata;
    - a WIP branch;
    - a new plan status;
    - final score/findings/LEARN/DOCUMENT requirements to paused publication.
  - Do not weaken the existing paused **commit** gate. It remains the mechanism that creates the checkpoint commit.
  - Keep Bash 3.2 compatibility. Do not introduce `mapfile`, `readarray`, associative arrays, or newer Bash-only syntax.
  - Verification for this step:
    ```bash
    bash -n shared/hooks/scripts/_lib-frontmatter.sh
    uv run python scripts/generate_targets.py --all
    uv run python scripts/validate_targets.py
    ```

- [ ] **2. Route PR creation to strict closeout and push to publication in `shared/hooks/scripts/enforce-pr-gate.sh`.**
  - Owner: `coder`
  - Required Skills: `ponytail/SKILL.md` (`full`)
  - Preserve:
    - payload fail-closed behavior;
    - Bash-tool filtering;
    - nested `.claude` state-sync push exemption;
    - implementation-branch requirement;
    - `gh pr create --base dev` requirement.
  - Change only the final invariant selection:
    - `gh pr create` must call the strict closeout helper directly;
    - `git push` must call `assert_push_invariants`.
  - This must make a paused branch pushable but keep the same paused branch blocked from PR creation.
  - Do not add command parsing logic beyond what is needed to select the already-detected operation.
  - Leave native `pre-push` on `assert_push_invariants`; it has no PR concept.
  - Verification:
    ```bash
    bash -n shared/hooks/scripts/enforce-pr-gate.sh
    uv run python scripts/generate_targets.py --all
    uv run python scripts/validate_targets.py
    ```

- [ ] **3. Replace the old paused-push expectation with focused lifecycle regressions in `scripts/validate_targets.py`.**
  - Owner: `coder`
  - Required Skills: `ponytail/SKILL.md` (`full`)
  - Reuse the existing paused-phase and pre-push fixture helpers. Do not create a second test framework.
  - Update the current fixture that expects `assert_push_invariants` to reject a paused phase.
  - Add the smallest set of cases that protects the new contract:
    1. **first phase paused:** valid pause evidence + one checkpoint commit -> push invariant passes;
    2. **missing checkpoint commit:** otherwise valid first-phase pause with `dev..local_sha == 0` -> push invariant fails;
    3. **mid-plan paused:** prior completed phase(s) + current valid paused phase + checkpoint commit -> passes;
    4. **prior cancelled phase:** valid cancellation evidence before current paused phase -> does not block; malformed cancellation evidence -> blocks;
    5. **prior non-terminal phase:** a phase before `current_phase` that is `in-progress`/`paused`/invalid -> blocks;
    6. **future phase:** a listed phase after `current_phase` left `in-progress` -> does not block paused backup;
    7. **current ordinary in-progress:** remains blocked from push;
    8. **malformed pause evidence:** paused publication reuses `assert_pause_evidence` and blocks;
    9. **PR separation:** the PreToolUse `gh pr create --base dev` path remains blocked for the same paused plan even though `git push` is allowed;
    10. **terminal regression:** existing fully completed/cancelled push/PR behavior, MAJOR finding gate, bypass acknowledgment, branch/ref scoping, and pushed-SHA behavior remain unchanged.
  - Extend the existing real native pre-push fixture if it can express the paused case with a small addition:
    - push a valid paused implementation ref to the fixture bare remote;
    - confirm the actual native pre-push hook accepts it;
    - keep the existing `local_sha`/non-HEAD ref coverage.
  - Do not duplicate every malformed pause-evidence case at the push layer. The existing exhaustive pause validator already covers field/path/UTF-8/marker errors; add only enough push-layer coverage to prove the existing validator is actually called.
  - Verification:
    ```bash
    uv run python scripts/generate_targets.py --all
    uv run python scripts/validate_targets.py
    ```

- [ ] **4. Update canonical lifecycle wording to distinguish checkpoint push from PR/final closeout.**
  - Owner: `coder`
  - Required Skills: `ponytail/SKILL.md` (`full`), `humanize/SKILL.md` (`edit`, docs profile)
  - Update only statements made false by this feature in:
    - `shared/policies/workflow.instructions.md`;
    - `shared/skills/commit/SKILL.md`;
    - `shared/agents/orchestrator/prompt.md`;
    - `shared/templates/plan-small.md`;
    - `README.md`.
  - Use one consistent distinction:
    - **paused checkpoint push / remote checkpoint:** durable backup of unfinished work;
    - **PR/final closeout:** terminal, reviewed, merge-readiness boundary.
  - Required policy points:
    - a paused checkpoint remains unfinished;
    - it does not advance `current_phase`;
    - the big plan remains `in-progress`;
    - it may be pushed only after the valid paused checkpoint commit and paused publication invariants pass;
    - it still blocks PR creation/final closeout;
    - final completion requirements are not waived.
  - Remove or update validator-required documentation fragments that still assert all paused phases block every push.
  - Do not rewrite unrelated workflow prose.
  - Verification:
    ```bash
    uv run python scripts/generate_targets.py --all
    uv run python scripts/validate_targets.py
    uv run python scripts/check_runtime.py
    ```

- [ ] **5. Review the phase as a control-plane change and shrink the diff before closeout.**
  - Owner: `reviewer`
  - Review Profiles:
    - `code`
    - `architecture`
    - `security`
    - `tests`
    - `ponytail`
  - Specific adversarial checks:
    - paused backup cannot accidentally satisfy PR closeout;
    - future phases do not block a legitimate paused backup;
    - prior unfinished phases cannot be skipped by moving `current_phase`;
    - first-phase pause does not hit the old “no completed work” rejection;
    - native pre-push still evaluates the actual pushed ref/SHA;
    - strict completed-flow findings/bypass gates are not weakened;
    - no new metadata/state source was added without need.
  - Run Ponytail review last on the stabilized diff. Prefer deletion/shrinking if the same contract can be expressed by reusing the existing strict helper and pause validator.

## Verification

Mandatory repository verification:

```bash
bash -n shared/hooks/scripts/_lib-frontmatter.sh
bash -n shared/hooks/scripts/enforce-pr-gate.sh
bash -n shared/hooks/git-hooks/pre-push
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

Persist the normal quality report for the phase after the final diff is staged/ready for closeout:

```bash
uv run python .claude/scripts/quality_score.py scripts/validate_targets.py \
  --phase 2026-08-28_phase-A-paused-remote-checkpoints \
  --base-ref dev \
  --json \
  --out .claude/quality_reports/score-<timestamp>.json
```

Record review findings with the actual profiles that ran, including `ponytail`, using the repository's existing `record_findings.py` workflow. Do not use a synthetic “no findings” file without running the required profiles.

## Acceptance Cases

| Case | `git push` | `gh pr create --base dev` |
|---|---:|---:|
| Phase 1 validly paused, checkpoint commit exists | Allow | Block |
| Mid-plan current phase validly paused, all prior phases terminal | Allow | Block |
| Paused but missing/malformed pause evidence | Block | Block |
| Paused but no checkpoint commit beyond prior completed phases | Block | Block |
| A phase before current phase is non-terminal | Block | Block |
| A future phase after current is pre-created `in-progress` | Allow paused checkpoint | Block |
| Current phase ordinary `in-progress` | Block | Block |
| All phases terminal and existing final gates pass | Allow | Allow |
| Terminal but existing final findings/bypass gate fails | Block | Block |

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.

Set `status: paused`, record the three pause fields, and create a session log with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it does not require final score, findings, LEARN, DOCUMENT, or a completed closeout.

After this phase's implementation lands, that valid checkpoint commit may also be pushed to the implementation branch remote under the new paused-publication invariant. This still does not complete the phase or make it PR-ready.

Keep the big plan `in-progress` with the same `current_phase`. On resume, read the pause log and Git state, restore this plan to `in-progress`, and continue this same phase without creating another small plan.
