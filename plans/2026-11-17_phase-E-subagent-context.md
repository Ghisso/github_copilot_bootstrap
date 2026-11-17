---
name: 2026-11-17_phase-E-subagent-context
type: small-plan
parent_plan: copilot-harness-migration
phase_index: 5
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

# Small Plan: 2026-11-17_phase-E-subagent-context

## Scope

On the Copilot harness, a custom sub-agent (`coder`, `reviewer`, and the
others) gets only its three-line agent file. It gets no repository
instructions and no skill list (F9). This phase adds a `SubagentStart` hook
that gives each sub-agent the text of `.github/copilot-instructions.md`, the
Copilot root guidance, plus one fixed line about where agent files and
skills live (REQ-006). P2 observed that top-level `additionalContext` from
this event reaches the sub-agent's first message, under both event casings.
The PascalCase name is observed, not documented, for this event.

The phase also gives Copilot sessions the plain-language reporting reminder
at session start, the documented route (F13). The agent-file fields stay:
the Local harness uses `agents:`, `user-invocable`, and
`disable-model-invocation`, and the Copilot harness ignores `agents:` (F9).
The Local harness runs these hooks too and reads the nested copy, so its
sub-agents may receive the guidance twice; the docs say so.

## Steps

- [ ] **1. Write the failing tests first.**
  Owner: coder. Files: `tests/test_hook_gates.py`,
  `tests/test_validate_targets.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/testing-patterns/SKILL.md`.
  Cases:
  - `subagent-context.sh github-copilot` with a P2-shaped input prints one
    valid JSON object. Its top-level `additionalContext` equals the nested
    one, contains the file's full text (newlines kept), and ends with the
    fixed line. It exits 0.
  - With a missing file, a linked file, or a file over 2048 bytes: only the
    fixed line, exit 0.
  - With malformed input: no output, exit 0. This is a context hook, not a
    guard.
  - `reporting-reminder.sh session github-copilot` prints the reminder in
    the combined `SessionStart` shape. The `claude-code` and `openai-codex`
    modes keep their bytes.
  - The validator expects `SubagentStart` in the Copilot hook file and the
    reminder under `SessionStart`. It fails when the generated
    `.github/copilot-instructions.md` exceeds 2048 bytes.
  Acceptance: the new cases fail before steps 2 to 4.

- [ ] **2. Add the sub-agent context hook.**
  Owner: coder. Files: create `shared/hooks/scripts/subagent-context.sh`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full).
  - Read `$REPO_ROOT/.github/copilot-instructions.md` only when it is a
    regular file, not a link, and at most 2048 bytes.
  - Build the output with `python3` and `json.dumps`, with the nested
    `hookEventName` `SubagentStart`.
  - The fixed line names `.claude/agents/<id>.md` and
    `.claude/skills/<name>/SKILL.md`, and says to read a skill file with
    the read tool when the agent file lists it.
  - Any error: warn on stderr, exit 0.

- [ ] **3. Add the session-start reminder for Copilot.**
  Owner: coder. Files: `shared/hooks/scripts/reporting-reminder.sh`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full).
  - New mode `session`, accepted only with the provider `github-copilot`.
    It prints the existing reminder through `additional_context`
    (`TARGET_ID` is the provider since Phase C).
  - The reminder text constant and its 200-byte ceiling are unchanged.

- [ ] **4. Wire both hooks and the budget.**
  Owner: coder.
  Files:
  - `shared/hooks/hooks.json`: a `SubagentStart` entry running
    `run-hook.sh subagent-context.sh github-copilot`, and a fourth
    `SessionStart` entry running
    `run-hook.sh reporting-reminder.sh session github-copilot`, timeout 10.
  - `scripts/validate_targets.py`: add `SubagentStart` to
    `COPILOT_EXPECTED_EVENTS`; check both handlers. Add a separate
    2048-byte check for the generated `.github/copilot-instructions.md`,
    not an entry in `ROOT_GUIDANCE_BUDGETS`: that table also applies the
    root-guidance header and lifecycle rules, which this file does not
    follow.

  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/code-style/SKILL.md`.
  Must not change `render_github_agent_adapter`.

- [ ] **5. Add the probe checks.**
  Owner: coder. Files: `scripts/check_copilot_runtime.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/integration-gate-spike/SKILL.md`.
  - Session `main` adds a `task` call for `coder` and one for `reviewer`.
  - `subagent-context`: each child's first user message contains
    `GitHub Copilot Workspace Adapter` (the first heading of the generated
    file) and the fixed line.
  - `session-reminder`: the main session's first user message contains
    the reminder text.

- [ ] **6. Update the docs.**
  Owner: coder. Files: `README.md` (Agent System), `docs/target-mapping.md`
  (Native Adapters, GitHub Copilot).
  Required Skills: `.claude/skills/documentation/SKILL.md`.
  Content:
  - what sub-agents receive and from where;
  - "observed on runtime `1.0.108-0`", not "documented", for the PascalCase
    event;
  - why the agent-file fields stay;
  - that the Local harness may show the guidance twice;
  - the 2048-byte budget.

- [ ] **7. Regenerate and refresh this repository's own install.**
  Owner: coder.
  Commands:
  - `uv run python scripts/generate_targets.py --all`;
  - `uv run python scripts/install_bootstrap.py . --allow-self --local-only`;
  - `uv run python scripts/validate_targets.py`;
  - `uv run python scripts/check_runtime.py`.

- [ ] **8. Review.**
  Owner: reviewer.
  Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`,
  `documentation`.
  Focus:
  - valid JSON for any file text;
  - the context hook never denies;
  - no budget loosened;
  - Local behavior described honestly.

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
uv run pytest tests/test_hook_gates.py tests/test_validate_targets.py tests/test_check_copilot_runtime.py -q --tb=short
uv run python scripts/check_copilot_runtime.py --require
grep -q -F 'subagent-context.sh github-copilot' dist/multi-agent/.github/hooks/hooks.json
grep -q -F 'reporting-reminder.sh session github-copilot' dist/multi-agent/.github/hooks/hooks.json
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

<!-- The only place a check may be conditional or non-executable. One `- `
     bullet per item, numbered in the order it appears. -->

- In a Copilot-harness chat in VS Code, start the `coder` sub-agent, ask it to quote the first heading of its repository guidance, and record the answer.

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
