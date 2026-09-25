# Session: Sidecar Phase A — provider contract

**Date:** 2026-09-25
**Plan:** `.claude/plans/2026-09-24_phase-A-sidecar-provider-contract.md`
**Status:** IN-PROGRESS

## Goal

Record documented and native discovery evidence for each client (Claude
Code, OpenAI Codex, GitHub Copilot in VS Code, Google Antigravity), then
freeze the read list, write list, and bridge paths in
`docs/sidecar-provider-contract.md`. No installer, generator, validator, or
test code changes in this phase.

## Work Log

- Pre-flight on `dev` at `1a06f1e`: clean outer and nested trees;
  `scripts/check_runtime.py` passes; `verify.py fast` is NOT_APPLICABLE (no
  changed Python). Branch `consumer-sidecar-bootstrap-overlay_implementation`
  created; the branch hook set the big plan `in-progress` and activated
  Phase A.
- Host clients checked 2026-09-25: Claude Code 2.1.226, codex-cli 0.147.0,
  VS Code 1.139.0 (WSL remote server), Git 2.43.0. The Antigravity CLI
  `agy` is not installed on this host.
- User decisions for step 3 (native runs), 2026-09-25:
  - Claude Code and Codex: the orchestrator runs `claude -p` and
    `codex exec` non-interactively in the fixture after the user runs the
    fixture recipe in their own shell (the agent-session commit gate blocks
    `git commit` even in other repositories). No trust or user-setting
    change; only marker-phrase yes/no results and structured skill lists are
    recorded, never raw transcripts.
  - Copilot in VS Code: the user runs the Local agent and Agent Host
    sessions and reports results.
  - Google Antigravity: recorded as `unavailable`. Its rules-file bridge
    therefore does not ship in v1 (Decision 14); `.agents/skills/` can still
    ship on Codex evidence.
- Steps 1-2 (documentation re-check and fixture recipe) delegated to
  `coder`.

## [LEARN] Entries

Pending.

## Verification

Pending.

## Open Questions / Next Steps

- Step 3: user runs the fixture recipe; orchestrator runs Claude Code and
  Codex probes; user runs Copilot sessions.
- Step 4: freeze the matrix. Step 5: apply the decision gate.
