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

- **07:05** - The user ran `run-write-gate-probe.sh` (both sessions exit 0).
  Parsed the `stream-json` events outside the model. Direct run: all four
  `.ai-bootstrap/` folder markers written then edited, `MEMORY.md` edited;
  control A (`.claude/ai-bootstrap/plans/`) refused as "a sensitive file"
  and listed in `permission_denials`; control B (root file) written, then
  removed. Delegated run: planner, coder, reviewer, and documenter each
  invoked through `Agent` tool events; coder Edit and documenter Write
  succeeded natively at their targets; plan and review saved by the main
  session; `permission_denials` empty. On disk: every marker matches, the old
  root holds only its five seeded files, team-file and index hashes match
  the snapshot, status differs only by the intended `src/hello.py` edit.
- **07:10** - Documenter appended `## Workflow state write gate, 2026-10-02`
  to `docs/sidecar-provider-contract.md` (append-only; earlier evidence
  untouched). Reviewer (code, architecture, security, tests, ponytail,
  documentation; two passes) returned PASS with one MINOR: the recipe did
  not say the fixture must be `fixture-write-gate/` beside the probe
  script. Fixed in the document; recorded as `fixed`.
- **07:15** - Decision gate: PASS for Claude Code. Phase B may relocate
  sidecar state to `.ai-bootstrap/`. Phase B scope addition (user
  decision): planner and reviewer return text; the requesting agent saves.

## [LEARN] Entries

- [LEARN:verification] A native evidence gate must exercise every capability
  the feature relies on, not only discovery; the earlier gate proved loading
  but never writing, and Claude Code protects every path under `.claude/`.
- [LEARN:workflow] An agent session cannot start a nested `claude -p` probe
  (auto-mode classifier denial); the user runs the prepared script and the
  agent verifies the events and files.
- [LEARN:workflow] Run the implementation-branch create as a bare Bash
  command; a `cd ... &&` prefix makes the branch-state hook record nothing.

## Verification

- optional 1: PASS — host-session evidence from steps 2 and 3, Claude Code
  2.1.226 print mode, `acceptEdits`, run by the user on 2026-10-02; checked
  from `stream-json` events and on-disk contents as logged above.
- optional 2: NOT RUN — no other client session was already available, and
  the plan does not require one.
