---
name: 2026-11-17_phase-F-copilot-docs
type: small-plan
parent_plan: copilot-harness-migration
phase_index: 6
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

# Small Plan: 2026-11-17_phase-F-copilot-docs

## Scope

This phase rewrites the Copilot claims so they match what the plan built
and what was run (REQ-008). It adds a short manual checklist for a
signed-in VS Code window. It records a check of the personal sidecar
overlay on the Copilot harness. The sidecar needs no code change: it ships
no hooks and no Copilot agent files.

Every claim names the runtime version it was seen on: the version the
Phase E probe printed, `1.0.108-0` at planning time. Every claim also says
that VS Code hooks are "in preview". Plain language throughout: "harness"
is explained at first use, and no internal label stands alone.

## Steps

- [ ] **1. Record the sidecar check.**
  Owner: coder. No code change.
  Required Skills: `.claude/skills/documentation/SKILL.md`,
  `.claude/skills/ponytail/SKILL.md` (full).
  - Install the `skills` profile and the `workflow` profile of the sidecar
    overlay into two new temporary Git repositories. Use the install
    command in `README.md`'s sidecar section.
  - Run `uv run python scripts/check_copilot_runtime.py --discover <dir>`
    on each.
  - Record in `docs/sidecar-provider-contract.md`, as a new dated row
    (2026-11-17 or the run date, runtime version):
    - which instruction files load (`.github/instructions/` and
      `.claude/rules/`);
    - whether the sidecar `.claude/agents/*.md` appear as Copilot agents;
    - which skill copy wins.
  - Keep the 2026-09-25 rows as dated records.
  - Any defect becomes a recorded follow-up, not a code change here.

- [ ] **2. Rewrite the Copilot claims.**
  Owner: coder, as the documenter role.
  Files and content:
  - `README.md`: Quick Install note, conditional policy applicability,
    Agent System, Hooks. Explain the two harnesses; what the bootstrap
    supports on each until February 2027; the `chat.useClaudeHooks`
    advice.
  - `docs/target-mapping.md`: Native Adapters; the GitHub Copilot column of
    both parity tables, split into Local harness and Copilot harness;
    Recorded follow-ups (the list in the big plan).
  - `docs/runtime-checks.md`: rewrite "VS Code Copilot evidence boundary":
    - what the probe proves, and on which version;
    - what only a signed-in window shows;
    - replace the "native-harness support" sentence with the exact claim:
      Copilot harness inside VS Code yes, Copilot CLI and cloud agents no.
  - `docs/smoke-tests.md`: a new "VS Code Copilot harness (manual)"
    checklist. Before starting, check the precondition: `/run/user/<uid>`
    must be in place. Recognize the fault by repeated
    `listen EACCES: permission denied /run/user/<uid>/vscode-ipc-<id>.sock`
    lines in `agenthost.log` under `~/.vscode-server/data/logs/<session>/`
    (A1). Then the items:
    - the denied `git reset --hard HEAD`;
    - one approval question for a protected edit, and what "Allow all" and
      Autopilot do;
    - the tool names in the hook log;
    - each MCP server listed once;
    - the five custom agents listed, and whether
      `github.copilot.chat.cli.customAgents.enabled` matters;
    - the sub-agent context;
    - when `sessionEnd` fires;
    - a Local-harness deny still works.
  - `docs/architecture.md`: the Copilot adapter description.

  Required Skills: `.claude/skills/documentation/SKILL.md`,
  `.claude/skills/humanize/SKILL.md`.
  Must not:
  - claim a result that was not run;
  - claim Copilot CLI or cloud-agent support;
  - edit dated records.

- [ ] **3. Review.**
  Owner: reviewer.
  Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`,
  `documentation`. Paths accumulate from the merge-base.
  Focus:
  - every claim has a run, source, or docs basis with a version;
  - plain language;
  - no stale claim left in the six files.

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
uv run python scripts/check_copilot_runtime.py --require --format text
uv run python -I -c 'import pathlib, sys; text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"); hits = [s for s in sys.argv[2:] if s in text]; sys.exit("stale text: " + "; ".join(hits) if hits else 0)' docs/target-mapping.md 'is not established from official sources'
uv run python -I -c 'import pathlib, sys; text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"); hits = [s for s in sys.argv[2:] if s in text]; sys.exit("stale text: " + "; ".join(hits) if hits else 0)' docs/runtime-checks.md 'or native-harness support'
grep -q -F '1.0.108-0' docs/runtime-checks.md
grep -q -F 'in preview' docs/runtime-checks.md
grep -q -F 'EACCES' docs/smoke-tests.md
grep -q -F 'chat.useClaudeHooks' docs/smoke-tests.md
grep -q -F 'SubagentStart' docs/target-mapping.md
grep -q -F 'Copilot harness' README.md
grep -q -F 'Copilot harness' docs/sidecar-provider-contract.md
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

<!-- The only place a check may be conditional or non-executable. One `- `
     bullet per item, numbered in the order it appears. -->

- The user runs the new manual checklist in a signed-in VS Code window and the results are recorded in the closeout session log; items not run are recorded as not run.
- If the final probe prints a runtime version other than `1.0.108-0`, the docs name the printed version instead, and the `1.0.108-0` check line above is updated before closeout.

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
