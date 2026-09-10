---
name: 2026-09-10_phase-A-commit-closeout-reliability
type: small-plan
parent_plan: consumer-lifecycle-friction-hardening
phase_index: 1
status: complete
closeout_session_log: .claude/session_logs/2026-09-10_consumer-lifecycle-friction-hardening.md
---

# Small Plan: Phase A — Commit and Closeout Reliability

## Scope

Make commit-driven phase advancement depend on the commit Git actually created,
not on parsing the shell command that requested it. Reproduce the reported
terminal receipt failure through a generated consumer before changing
provenance behavior, retain the existing narrow terminal transition allowance,
and replace misleading recovery advice with state-specific commands. Finally,
make one closeout order authoritative and test it end to end.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` in `full` mode
- `.claude/skills/code-style/SKILL.md`
- `.claude/skills/testing-patterns/SKILL.md`

## Review Profiles

- `code`
- `architecture`
- `security`
- `tests`
- `ponytail`
- `documentation`

## Steps

1. **Add the exact consumer lifecycle reproduction before changing behavior.**
   Owner: `coder`.
   Modify `scripts/validate_targets.py` and the smallest relevant focused test
   modules under `tests/`. Build a generated consumer fixture that finalizes a
   small plan, explicitly stages intended outer files, persists findings,
   phase, and closeout evidence, commits with `git commit -F <file>`, lets the
   native post-commit path checkpoint nested state, and performs a real push to
   a local bare remote. Cover both immediate dirty nested state and the clean
   checkpointed terminal state already modeled by `verify.py`. Record whether
   current source passes or fails before changing receipt logic.

2. **Move phase advancement to the native post-commit boundary.**
   Owner: `coder`.
   Modify `shared/hooks/git-hooks/post-commit` so it invokes the existing
   `shared/hooks/scripts/record-commit-closeout.sh` before `state-sync.sh push`.
   Simplify `record-commit-closeout.sh` to read the current branch and the
   created `HEAD` subject from Git, require the current small plan to be
   `complete`, preserve bypass and cancelled-phase behavior, and advance at
   most once. Remove its Bash PostToolUse registration from
   `shared/hooks/hooks.json` and the Claude/Codex generator paths in
   `scripts/generate_targets.py`. Update structural assertions and lifecycle
   tests accordingly. A failed commit, non-implementation branch, merge,
   paused phase, incomplete phase, or repeated invocation must not advance the
   plan. A `-m`, `-F <file>`, `-F -`, heredoc, GUI, or editor-produced commit
   must behave identically after Git creates it.

3. **Keep terminal receipt provenance narrow and prove the full composition.**
   Owner: `coder`.
   Modify `shared/scripts/verify.py` only if Step 1 reproduces a failure in the
   current terminal matcher. Reuse `terminal_control_plane_provenance_matches`
   and the last-completed-phase gate path; do not add a second freshness model
   or exclude general plan fields. The only post-receipt allowance remains the
   exact automatic final big-plan transition, with both unstaged and clean
   nested-checkpoint forms. Add negatives for unrelated plan text, small-plan,
   runtime, adapter, receipt, index-only, and later-phase mutations. Do not
   bump receipt schema v4 unless the existing metadata cannot express the
   tested correct state.

4. **Make inactive-plan diagnostics state-specific.**
   Owner: `coder`.
   Update `unresolved_phase_reason` in `shared/scripts/verify.py` and its tests.
   If the big plan is complete and `current_phase` is empty, identify the last
   completed non-cancelled phase and print the exact optional receipt-refresh
   form using `--phase <slug>`; do not advise opening another small plan. If a
   plan is still `planning`, advise starting its first phase. Preserve distinct
   diagnostics for missing, unreadable, malformed, or unsafe plan metadata.
   Normal terminal push must not require manual receipt refresh.

5. **Define the canonical closeout order once and enforce its claims.**
   Owner: `coder`, followed by `documenter` after review converges.
   Update `shared/policies/workflow.instructions.md`,
   `shared/policies/quality-and-testing.instructions.md`,
   `shared/agents/orchestrator/prompt.md`,
   `shared/skills/commit/SKILL.md`, the small-plan template, and related live
   documentation. The successful path is: focused/fast checks; review;
   documentation and final plan/log/LEARN state; explicit staging of intended
   outer files; `record_findings.py`; `verify.py phase --persist`; `verify.py
   closeout --persist`; commit. State that `dirty` means unstaged tracked
   changes and that untracked target files are not represented by `git diff`.
   If a later fix changes code, restart verification and review. Remove or
   redirect competing order descriptions rather than maintaining duplicates.

6. **Warn when findings omit untracked target content.**
   Owner: `coder`.
   Extend `shared/scripts/record_findings.py` using Git's standard porcelain
   output to detect untracked files contained by the requested target. Emit a
   concise stderr warning that names the paths and tells the caller to stage
   intended files before recording again. Do not mark unrelated repository
   files, ignored files, or output artifacts outside the target as findings
   dirtiness. Keep existing report JSON stable and add focused positive and
   negative tests.

7. **Regenerate and verify all provider surfaces.**
   Owner: `coder`.
   Regenerate `dist/multi-agent/` from `shared/`, confirm no source mirror was
   hand-edited, and exercise GitHub Copilot, Claude Code, and Codex hook
   registrations. The end-to-end consumer must commit and push with no manual
   `current_phase` edit and no stale-provenance repair.

## Acceptance Criteria

- [x] `-m`, `-F <file>`, `-F -`, heredoc, GUI/editor, and equivalent successful commits advance the same completed phase exactly once.
- [x] Failed, paused, incomplete, bypass, merge, repeated, and non-implementation commit paths do not advance normal phase state.
- [x] Phase advancement runs before post-commit state synchronization.
- [x] A generated consumer completes the terminal commit and real local push without manual plan or receipt repair.
- [x] Only the exact automatic terminal big-plan transition receives the existing provenance exception.
- [x] A complete plan's no-active-phase message names `--phase <last completed slug>` instead of advising another phase.
- [x] One canonical closeout sequence matches the gate's real staged-tree and dirty semantics.
- [x] `record_findings.py` warns about untracked files inside its target without changing report schema.
- [x] No automatic broad staging or post-commit verification command is introduced.

## Verification

```bash
uv run pytest tests/test_verify.py tests/test_hook_gates.py tests/test_lifecycle_hooks.py tests/test_validate_targets.py -q
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run ruff check shared/scripts/verify.py shared/scripts/record_findings.py tests scripts/validate_targets.py
uv run mypy shared/scripts/verify.py shared/scripts/record_findings.py tests scripts/validate_targets.py --ignore-missing-imports --explicit-package-bases
uv run python .claude/scripts/verify.py phase --format json --persist
```

## Closeout Checklist

- [x] Verification passed (`verify phase` PASS)
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record `paused_at`, `paused_reason`, and
`pause_session_log`, and keep the big plan `in-progress` with this same
`current_phase`. Resume this file rather than creating a replacement phase.
