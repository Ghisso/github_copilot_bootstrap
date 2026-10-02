# Session: Sidecar native write evidence (Phase A)

**Date:** 2026-10-02
**Plan:** .claude/plans/2026-10-02_phase-A-sidecar-write-evidence.md
**Status:** IN-PROGRESS

## Goal

Prove, with real Claude Code sessions and ordinary permissions, that the
proposed sidecar state root `.ai-bootstrap/` accepts the direct and delegated
writes the workflow profile needs, before Phase B changes production code.

## Work Log

- **06:40** - Created `sidecar-workflow-repair_implementation` from clean
  `dev`. The branch-state hook did not fire because the create command was
  chained after `cd`; ran `record-branch-state.sh` by hand with the same
  payload, which activated Phase A and filled the big-plan branch fields.
- **06:45** - Built the fixture in the session scratchpad
  (`fixture-write-gate`): staged team `.claude/settings.json`,
  `.claude/rules/team.md`, and `src/hello.py` (no commit; the commit gate
  blocks fixture commits). Installed the real current sidecar workflow
  profile (`installed 72`). In the fixture only, copied the seeded state to
  `.ai-bootstrap/`, rewrote `.claude/ai-bootstrap` to `.ai-bootstrap` in the
  12 installed files that referenced it, and added `/.ai-bootstrap` to the
  fixture's `info/exclude`. The old root stays as a write control.
  Snapshotted index hash, team-file hashes, and status.
- **06:50** - Starting a nested `claude -p` session from this agent session
  was denied by the auto-mode safety classifier. Not worked around. The user
  chose to run the probe script (`run-write-gate-probe.sh`, scratchpad) in
  their own shell, matching the provider contract's existing rule that
  fixture runs happen in the operator's shell.
- **06:50** - New defect found while preparing step 3 (not among the seven
  review findings): the sidecar `planner` and `reviewer` prompts tell them to
  save their plan/report under the state root, but their rendered tool lists
  come from the shared `agent.yaml` capabilities (planner: no Write/Edit;
  reviewer: Read/Grep/Glob only). The user chose "caller saves": planner and
  reviewer return text and the requesting agent saves it, matching the full
  install's read-only reviewer. This is a Phase B scope addition.

## [LEARN] Entries

Pending.

## Verification

Pending.
