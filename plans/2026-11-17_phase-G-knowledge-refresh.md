---
name: 2026-11-17_phase-G-knowledge-refresh
type: small-plan
parent_plan: copilot-harness-migration
phase_index: 7
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: planned
closeout_session_log:
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---

# Small Plan: 2026-11-17_phase-G-knowledge-refresh

## Scope

This is the plan's final phase. It refreshes the OpenWiki pages (the
generated repository wiki) for the changes of Phases A to F. It inspects the
generated diff. It runs the standing documentation, memory, and LEARN audit
from `.claude/instructions/closeout.instructions.md`, and records it under
`## Stale-claims surfaces checked` in this phase's closeout session log.

The pages most affected are `openwiki/architecture/hooks-and-guardrails.md`
(Copilot answers, the stand-down rule, the tool names, `SubagentStart`),
`openwiki/architecture/agents-and-skills.md` (sub-agent context), and
`openwiki/operations/install-ownership-and-runtime-checks.md` (the probe).

## Steps

- [ ] **1. Refresh the wiki.**
  Owner: orchestrator, with the coder for page writing.
  Required Skills: `.claude/skills/knowledge-refresh/SKILL.md`,
  `.claude/skills/openwiki/SKILL.md`.
  - Follow the skill exactly: begin, plan, each page job, finish.
  - Take each claim's line range from a search run in the same step as
    `openwiki_submit_page`.
  - Use links relative to the page's folder.
  - Never hand-edit a generated page outside the job, and never commit
    OpenWiki's own root snippet.

- [ ] **2. Inspect the generated diff.**
  Owner: orchestrator.
  - Read each changed page's prose against the code it cites.
  - Fix mismatches through a second scoped update run, not by hand.

- [ ] **3. Run the final audit.**
  Owner: coder.
  Required Skills: `.claude/skills/documentation/SKILL.md`,
  `.claude/skills/learn/SKILL.md`.
  Sweep `README.md`, `docs/`, `.claude/instructions/`, active plans,
  `.claude/MEMORY.md`, and `openwiki/` for claims this plan invalidated.
  In particular:
  - Correct, in place, the `[LEARN:tooling]` entry about the 2026-11-17
    spike in `.claude/MEMORY.md`. Its "every hook runs twice",
    `apply_patch` crash, and "sub-agents get no repository instructions"
    statements are fixed on the Copilot harness by this plan; the Local
    `chat.useClaudeHooks` double run remains.
  - Add LEARN entries for:
    - the shell-helper finding (P3);
    - the `COPILOT_CLI` inheritance finding (P1);
    - the Local-settings reason against a Local stand-down (A2).
  - Leave dated records unchanged.
  - Record every surface and its outcome under
    `## Stale-claims surfaces checked`.

- [ ] **4. Review.**
  Owner: reviewer.
  Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`,
  `documentation`.
  Focus:
  - the wiki pages match the code;
  - `MEMORY.md` has no stale advice;
  - the audit list is complete.

## Verification

<!-- Every non-comment line in a `bash`/`sh` block below is a required item:
     a shell command `verify closeout` runs itself, from the repository
     root, and that must exit 0. Never list `verify.py closeout` itself.
     Anything a script cannot run — an interactive probe, a host session, a
     manual inspection — belongs under `## Optional Verification` instead.
     See the Verification Evidence Contract in
     `.claude/instructions/workflow.instructions.md`. -->

```bash
uv run python scripts/generate_targets.py --all
test ! -e openwiki/.run.json
test "$(grep -c -F '<!-- OPENWIKI:START -->' AGENTS.md)" = "0"
test "$(grep -c -F '<!-- OPENWIKI:START -->' CLAUDE.md)" = "0"
grep -q -F 'SubagentStart' openwiki/architecture/hooks-and-guardrails.md
grep -q -F 'Copilot harness' openwiki/architecture/hooks-and-guardrails.md
grep -q -F 'check_copilot_runtime.py' openwiki/operations/install-ownership-and-runtime-checks.md
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

<!-- The only place a check may be conditional or non-executable. One `- `
     bullet per item, numbered in the order it appears. -->

- Read each refreshed page's prose against the code it cites, not only its flagged claims, and record any mismatch.

## Closeout Checklist

Run the numbered CLOSEOUT sequence in `.claude/instructions/closeout.instructions.md` in order. Tick both boxes at its step 2. Later steps bind this file's bytes, so do not edit this file after step 2.

- [ ] Step 1: documentation updated, or skipped as pure-internal with a reason
- [ ] Step 2: this plan set to `status: complete` with `closeout_session_log`, every step ticked, and LEARN entries or the no-lessons marker recorded

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record the three pause fields, and create a session log
with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it
does not require final findings, LEARN, DOCUMENT, or a completed closeout.
After the checkpoint commit, it may be pushed as a durable remote backup when
paused-publication invariants pass. It remains unfinished and blocks PR creation
and final closeout.
Keep the big plan `in-progress` with the same `current_phase`. On resume, read
the pause log and Git state, restore this plan to `in-progress`, and continue
this same phase without creating another small plan.
