# Session: Sidecar workflow repair (Phase B)

**Date:** 2026-10-02
**Plan:** .claude/plans/2026-10-02_phase-B-sidecar-workflow-repair.md
**Status:** IN-PROGRESS

## Goal

Fix findings 1-7 of `.claude/explorations/2026-10-02_sidecar-workflow-profile-hands-on-review.md`
plus finding 8 from Phase A (planner and reviewer prompts ask for saves their
tools cannot make), relocate sidecar state to `.ai-bootstrap/`, and migrate
owned legacy state safely.

## Work Log

- **07:25** - Phase A committed (`e8297f8`) and pushed; Phase B activated.
  Material-impact check: Phase A added finding 8 and the user-run native
  rerun constraint. One planner revised Phase B only (+24 lines: step 5 now
  covers findings 5-8 with the caller-saves decision; step 6 native rerun is
  prepared and verified by the orchestrator and run by the user, fresh
  install only). Big plan goal, phase line, and done criteria now say
  findings 1-8.
- **07:50** - Step 1 (finding 2) by coder. `_full_install_evidence` adds a
  legacy signal only when no modern marker fired: a real, untracked
  `.claude/` (same tracked-path guard) plus either (a) tracked
  `.devcontainer/hf-ai-sync.py` or `.devcontainer/state-sync.sh`, or (b) a
  local `.claude/scripts/verify.py`, each corroborated by at least 2 of the
  bootstrap hook scripts `run-hook.sh`, `protect-files.sh`, `session-log.sh`,
  `context-mode-dispatch.sh`, `git-protection.sh`. Evidence: read-only
  inspection of `img-classification` (has six such hook scripts, tracked
  `hf-ai-sync.py`, no `verify.py`) and this repository's history
  (`dd1ee06` retired `hf-ai-sync.py`; `3de8385` added `state-sync.sh`).
  Rejected: an arbitrary hooks folder, a single hook name, a tracked team
  `.claude/` with the same names. Mixed evidence now advises backup and
  inspected cleanup; the ambiguous plain refusal stops steering toward
  sidecar when a per-clone `.claude/` exists. Focused tests: 228 passed;
  ruff, format, and mypy clean on touched files.
- **08:15** - Step 2 (finding 4) by coder. `backup_sidecar_state` now runs
  the shared target preflight, takes `_acquire_run_lock` only for a real
  backup with state present, and copies through the new
  `_copy_state_into_preserved(source, preserved_root)` helper: copy into a
  `mkdtemp` sibling, then `os.rename` to the collision-free name; on
  `OSError` it removes only its own staging copy (or names it as incomplete)
  and prints the existing `ABORT: filesystem error at <path>: <reason>`.
  Behavior change to document: a symlinked state root or preserved folder
  now refuses instead of being skipped. `_run_backup_state` lost its dead
  `CalledProcessError` wrapper. Full suite: 2289 passed.
- **09:30** - Step 3 (finding 1) by coder. `SIDECAR_STATE_ROOT =
  ".ai-bootstrap"`, new `SIDECAR_LEGACY_STATE_ROOT = ".claude/ai-bootstrap"`;
  `_ALL_STATE_ROOTS` is the union, which extends validation, exclude
  parsing, tracked/symlink protections, backup, and uninstall to both roots.
  `_legacy_state_migration_outcome` (none / migrate / both_exist / unowned;
  ownership = legacy line in the managed exclude block) runs before
  classification; `_perform_legacy_state_migration` adds and proves the new
  exclude line (restoring `info/exclude` bytes on early failure), backs up
  via `_copy_state_into_preserved` (`symlinks=True`), refuses a
  cross-filesystem move, rechecks the destination, renames, then falls into
  normal reconciliation, which drops the obsolete legacy line. New fault
  points `after_legacy_state_backup` and `after_legacy_state_rename`.
  Generator path table and all workflow sources render `.ai-bootstrap/`;
  `validate_targets.py` forbids the legacy path in generated workflow
  content. Bug fixed: two state roots needing preserved copies in one pass
  got the same `state--<timestamp>` name; `state_backup_slug` now takes a
  `reserved` set via shared `preserved_destinations_for`. To document: the
  both-roots refusal applies to install/update only; uninstall/purge keep
  both roots independently. Full suite: 2308 passed.
- **10:40** - Steps 4-5 by coder. Step 4: `_print_report(dry_run=True)`
  skips past-tense per-action lines; preserve/purge remedy texts get "would"
  wording through `plan_sidecar_reconciliation(dry_run=...)`. Step 5:
  Copilot instructions write plans and self-review; shared rules and role
  prompts delegate only to agents this session can start, otherwise the
  current agent does the step (self-review labeled); planner and reviewer
  return text and the caller saves it. Full suite: 2313 passed.
- **10:50** - Orchestrator corrected the orchestrator prompt's Coder
  bullet: the coder's text said a team agent in any client's folder still
  counts as having a coder, which is false in Claude Code for a team's
  `.github/agents/coder.agent.md`. Now: when this session cannot start an
  agent named `coder`, implement the change yourself.
- **10:55** - Step 6 checks: generate exit 0; validate PASS; 7 focused files
  752 passed; zero `.claude/ai-bootstrap` hits in `dist/sidecar/workflow`;
  `check_runtime.py` exit 1 only for the stale self-install copy of
  `.claude/scripts/runtime_ownership.py` (expected). The self-install refresh
  (`install_bootstrap.py . --allow-self --local-only`) was denied by the
  auto-mode classifier; handed to the user. Built
  `fixture-repair-rerun` from the new generated install (72 installed,
  state seeded at `.ai-bootstrap/`, no legacy refs) and
  `run-repair-rerun-probe.sh` (runs as the installed `orchestrator` agent,
  no hint about who saves). Reviewer started on the Phase B diff.
- **11:30** - The user ran the self-install refresh (nested commit
  `47deb93 bootstrap: update`); `check_runtime.py` now exit 0. The user ran
  `run-repair-rerun-probe.sh` (exit 0). Claude Code 2.1.226, `--agent
  orchestrator`, `acceptEdits`, tools Read/Write/Edit/Grep/Glob/Agent.
  Events: planner, coder, reviewer invoked through `Agent`; the planner and
  reviewer returned text and the orchestrator saved
  `.ai-bootstrap/plans/2026-10-02_phase-1-hello-docstring-and-greeting.md`
  (76 lines) and `.ai-bootstrap/quality_reports/2026-10-02_hello-docstring-and-greeting-review.md`
  (30 lines) with its own Write, unprompted; the coder edited
  `src/hello.py`; the orchestrator wrote the session log (50 lines) and
  added a `[LEARN:python]` line to `.ai-bootstrap/MEMORY.md`.
  `permission_denials` empty; no `.claude/ai-bootstrap/` created; team-file
  and index hashes unchanged; status differs only by `AM src/hello.py`.

- **11:45** - Review 1 (code, architecture, security, tests, ponytail,
  documentation; two passes) on the full code diff: PASS. Ruled out with
  code and test evidence: symlinked legacy root, destination race before
  `os.rename`, claiming an unowned or tracked legacy folder, `symlinks=True`
  escape, duplicate migration on rerun, legacy-signal false positives,
  leftover old paths. One MINOR: the planner prompt claimed "you have no
  tool to save a file" though the planner keeps `Bash`. Fixed in the planner
  and reviewer prompts ("do not write it to a file yourself") and the
  `tests/test_validate_targets.py` assertions.
- **12:00** - Documenter updated `README.md`, `docs/target-mapping.md`, and
  `docs/sidecar-provider-contract.md` (new subsections "Legacy full-install
  evidence, 2026-10-02" and "Rerun on the repaired install, 2026-10-02";
  dated history untouched). Full verification after all edits: generate
  exit 0, `validate_targets.py` PASS, `check_runtime.py` exit 0, full pytest
  2313 passed, ruff, format, and mypy (42 files) clean.
- **12:10** - Review 2 (same six profiles) on the docs and post-review
  prompt edits: PASS. One MINOR: the rerun record dropped the `[LEARN:python]`
  category. Fixed.

## Findings to evidence

| Finding | Fix | Evidence |
| --- | --- | --- |
| 1. Writes refused under `.claude/ai-bootstrap/` | State at `.ai-bootstrap/`; owned legacy state migrated | Phase A write gate and the 11:30 native rerun; migration, refusal, fault-point rerun, dry-run, profile-switch, uninstall, purge, and backup tests in `tests/test_sidecar_workflow_scenario.py`; batch migration in `tests/test_sidecar_update.py`; generated-tree scan in `tests/test_validate_targets.py` |
| 2. Older full installs not detected | Legacy evidence in `_full_install_evidence`; mixed-evidence advice | HF-era, pre-manifest, negative, mixed, and CLI refusal tests in `tests/test_install_bootstrap.py`; uninstall refusal in `tests/test_sidecar_uninstall.py`; batch routing in `tests/test_sidecar_update.py` |
| 3. Dry run printed past tense | `_print_report(dry_run=...)`; "would" remedy texts | Dry-run tests in `tests/test_sidecar_install.py`, `tests/test_sidecar_uninstall.py`, `tests/test_sidecar_workflow_scenario.py` |
| 4. Backup without lock or error handling | Lock, temp copy then rename, `ABORT: filesystem error` | Lock contention, same-second, copy, rename, and cleanup failure, symlink, no-state, and CLI dry-run snapshot tests in `tests/test_sidecar_workflow_scenario.py` |
| 5. Copilot told to ask missing agents | Copilot writes plans and self-reviews | Rendered-content tests in `tests/test_validate_targets.py` |
| 6. Team agent removes the Claude agent | Delegate only to agents the session can start; else do it yourself | `.github/agents/coder.agent.md` fallback test in `tests/test_sidecar_workflow_scenario.py`; native rerun |
| 7. No precedence test for profiles and templates | Tests added | Tracked, foreign-untracked, and deleted-tracked collision tests in `tests/test_sidecar_workflow_scenario.py` |
| 8. Planner and reviewer told to save without a write tool | Return text; the caller saves | `tests/test_validate_targets.py` rendered-prompt tests; native rerun (orchestrator saved both, unprompted) |

## [LEARN] Entries

- [LEARN:workflow] In auto mode the safety classifier also denies the
  self-install refresh `install_bootstrap.py . --allow-self --local-only`,
  not only nested `claude -p`; hand both to the user up front.
- [LEARN:review] Before a prompt states what a role can or cannot do, check
  its rendered `tools:` line; the sidecar planner keeps `Bash` through the
  `execute` capability.

## Verification

- optional 1: PASS — native rerun on the actual generated workflow install,
  run by the user on 2026-10-02 (Claude Code 2.1.226, `--agent
  orchestrator`, `acceptEdits`); caller-saved plan and review, coder edit,
  session log, and memory edit at `.ai-bootstrap/`; no permission denials.
- optional 2: NOT RUN — no disposable clone of the reported legacy
  consumer was made; its layout was inspected read-only and reproduced as
  real-Git test fixtures instead, and the plan forbids touching the real
  consumer.
