---
name: 2026-11-17_phase-F-copilot-docs
type: small-plan
parent_plan: copilot-harness-migration
phase_index: 6
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: in-progress
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
that VS Code hooks are "in preview", and that VS Code can give a model a
different tool set than the runtime's own list (A4). Plain language
throughout: "harness" is explained at first use, and no internal label
stands alone.

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
  - In `docs/sidecar-provider-contract.md`, add a section headed
    `### Copilot harness discovery check (2026-11-17 or the run date)`.
    Record the runtime version, the command used, which instruction files
    load (`.github/instructions/` and `.claude/rules/`), whether the
    sidecar `.claude/agents/*.md` appear as Copilot agents, and which skill
    copy wins.
  - Keep the 2026-09-25 rows as dated records.
  - Any defect becomes a recorded follow-up, not a code change here.

- [ ] **2. Rewrite the Copilot claims.**
  Owner: coder, as the documenter role.
  Files and content:
  - `README.md`: Quick Install note, conditional policy applicability,
    Agent System, Hooks. Explain the two harnesses, with the sentence
    "VS Code removes the Local harness in February 2027." Say what the
    bootstrap supports on each until then, and repeat the
    `chat.useClaudeHooks` advice.
  - `docs/target-mapping.md`: Native Adapters; the GitHub Copilot column of
    both parity tables, split into Local harness and Copilot harness;
    Recorded follow-ups (the big plan's list, including the policies
    offered twice and the per-hook `disableKey`).
  - `docs/runtime-checks.md`: rewrite "VS Code Copilot evidence boundary":
    - what the probe proves, and on which version;
    - what only a signed-in window shows;
    - replace the "native-harness support" sentence with: "This bootstrap
      supports the Copilot harness inside VS Code. It does not claim
      Copilot CLI or Copilot cloud agents."
  - `docs/smoke-tests.md`: a new `## VS Code Copilot harness (manual)`
    section.
    - Precondition: the folder `/run/user/<uid>` owned by the user. Without
      it, `agenthost.log` (under `~/.vscode-server/data/logs/<session>/`)
      repeats
      `listen EACCES: permission denied /run/user/<uid>/vscode-ipc-<id>.sock`.
      Fix it with
      `sudo install -d -m 700 -o "$(id -u)" -g "$(id -g)" /run/user/$(id -u)`,
      repeated after every WSL restart (A1).
    - Items:
      - the denied `git reset --hard HEAD`;
      - the approval questions for a protected edit (two under option B),
        and what "Allow all" and Autopilot do;
      - a file edit with a model that uses `apply_patch`;
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

  Scope-change record (approved by the orchestrator on 2026-11-18; each
  item serves this phase's stated intent, and no code changes):
  - The manual checklist has 11 items, not 9. It takes in the checks that
    Phases B to E left for a signed-in window: the patch tool, the
    Local-harness deny with the new answer, one session-log entry for each
    chat, the sub-agent guidance, and the session-start reminder.
  - The checklist item on the approval questions follows the Phase D
    correction: the runtime raises two hook questions for one protected
    edit, and in the one real VS Code run VS Code answered the second one
    itself. The item asks how many dialogs appear.
  - Step 1: the heading `### Copilot harness discovery check (2026-11-18)`
    sits under a new parent heading `## Copilot harness check, 2026-11-18`,
    so that it does not fall under a dated section of 2026-10-02.
  - In the six files, bare labels of the evidence report (such as "A6" or
    "F13") get a plain description of what was seen, where, and when. Each
    document says once where the report is.
  - Stale or unsupported sentences corrected inside the six files, beyond
    the plan's list: that Copilot gets no sidecar agents (the discovery
    check lists the five sidecar agent files); that
    `check_native_clients.py` covers Copilot; that no earlier decision was
    loosened (the rows L1 to L3 did loosen decisions); row L1's "every
    sub-agent read asked"; row T2's one-off run, which had no saved
    record and now cites a saved probe run.
  - Not added to the docs: the follow-up on inline Python without `-I`
    and on the temp-file leak of `protect-files.sh`. The user decides how
    to handle both.
  - After review rounds 1 to 3 (26 MINOR findings and one MAJOR, all
    fixed):
    - `docs/runtime-checks.md` gives the run dates by evidence file
      (2026-11-17 and 2026-11-18); it had said all runs were made on
      2026-11-17.
    - The statement on the Local harness changed after a new reading of
      VS Code's `extension.js` on 2026-11-18: it takes the decision from
      the nested copy, and it drops a whole result whose top-level
      `hookEventName` names another event. The three documents that
      state it use the same words.
    - The checklist opens with a safety paragraph: run it only in a test
      folder with no work to keep. Each item starts with a mark that says
      whether it was ever run, names its Session Target, and gives the
      answer for a dialog. Result words are defined once, with one for an
      item that only records what is seen.
    - This plan's text calls the folder `/run/user/<uid>` a precondition.
      The checklist says it is needed only when a chat freezes and
      `agenthost.log` shows the `listen EACCES` lines, because one check
      on 2026-11-17 showed sessions whose agent host used a socket under
      `/tmp`.
    - The hook and sub-agent detail of `docs/target-mapping.md` moved to
      the two README sections; that document keeps one short paragraph
      with links. The Local-harness source reading is stated once, in the
      README.
    - One paragraph below the hook-config table of
      `docs/target-mapping.md` names the files the Copilot harness loads
      and cites one direct run of the guard on 2026-11-18.
    - A recorded follow-up and `docs/architecture.md` say that
      `.github/copilot-instructions.md` is also read by the sub-agent
      hook, so it must stay when the Local harness is removed.
    - The February 2027 date names its sources at its first mention in
      each document.
    - The sidecar note says GitHub Copilot chat has two harnesses and
      names the dated "Agent Host, Claude harness" row as a third,
      unverified session type.

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
uv run python -I -c 'import pathlib, sys; text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"); hits = [s for s in sys.argv[2:] if s in text]; sys.exit("stale text: " + "; ".join(hits) if hits else 0)' docs/target-mapping.md 'is not established from official sources'
uv run python -I -c 'import pathlib, sys; text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"); hits = [s for s in sys.argv[2:] if s in text]; sys.exit("stale text: " + "; ".join(hits) if hits else 0)' docs/runtime-checks.md 'or native-harness support'
grep -q -F 'It does not claim Copilot CLI or Copilot cloud agents.' docs/runtime-checks.md
grep -q -F '## VS Code Copilot harness (manual)' docs/smoke-tests.md
grep -q -F 'sudo install -d -m 700' docs/smoke-tests.md
grep -q -F 'VS Code removes the Local harness in February 2027.' README.md
grep -q -F '### Copilot harness discovery check' docs/sidecar-provider-contract.md
grep -q -F 'check_copilot_runtime.py --discover' docs/sidecar-provider-contract.md
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

<!-- The only place a check may be conditional or non-executable. One `- `
     bullet per item, numbered in the order it appears. -->

- Run `uv run python scripts/check_copilot_runtime.py --require` and record the printed runtime version; the docs name that version.
- The user runs the new manual checklist in a signed-in VS Code window and the results are recorded in the closeout session log; items not run are recorded as not run.

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
