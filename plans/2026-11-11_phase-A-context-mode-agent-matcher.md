---
name: 2026-11-11_phase-A-context-mode-agent-matcher
type: small-plan
parent_plan: context-mode-agent-matcher
phase_index: 1
status: in-progress
closeout_session_log:
---

# Small Plan: Context Mode PreToolUse Matcher Skips Agent

## Scope

Generated Claude Code settings run `context-mode-dispatch.sh claude-code pretooluse` for every tool (`"matcher": "*"`), including `Agent`. This phase narrows that one group to `^(Bash|Read|Grep|WebFetch|mcp__.*)$`, makes the validator require it, adds a test that copies Claude Code's matcher rules, and updates the docs. Codex, Copilot, Antigravity, the dispatcher, and the filter stay as they are. See the big plan `context-mode-agent-matcher` for the evidence and the reasons.

## Steps

- [ ] **1. Write the tests first.**
  - Owner: `coder`. Files: `tests/test_lifecycle_hooks.py`, `tests/test_validate_targets.py` (modify).
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - In `tests/test_lifecycle_hooks.py`, add `test_rendered_claude_context_mode_pretool_matcher_skips_agent`. Render with `render_claude_settings(tmp_path / "settings.json")`. Select the PreToolUse groups whose handler commands contain `context-mode-dispatch.sh` and assert there is exactly one. Check its matcher with a small module helper, `_claude_matcher_fires(matcher: str, tool: str) -> bool`, that copies Claude Code 2.1.226's PreToolUse rules:
    - `""` or `"*"` fires for every tool;
    - a matcher made only of letters, digits, `_`, `|`, `,`, space, and `-` is a list of exact names, split on `|` or `,` and stripped;
    - anything else is `re.search(matcher, name)` over the tool name and its legacy names: `Agent`: `Task`; `TaskOutput`: `AgentOutputTool`, `BashOutputTool`, `AgentOutput`, `BashOutput`; `TaskStop`: `KillShell`, `KillBash`.
    - One short comment names the source: the hook matcher function and legacy-name table in Claude Code 2.1.226.
  - Assert: the matcher is not `""` or `"*"`; it does not fire for `Agent` or `Task`; it does not fire for `TaskOutput` (the legacy-name trap of an unanchored pattern); it fires for `Bash`, `Read`, `Grep`, `WebFetch`, `mcp__context-mode__ctx_search`, and `mcp__semble__search`. The expected names come from Context Mode's routing branches (big plan), so do not import the generator constant into this test.
  - In `tests/test_validate_targets.py`, add `test_pretool_routing_requires_target_specific_context_mode_matcher`, built from the four-group hooks object of `test_pretool_routing_rejects_wildcard_safety_and_lifecycle_drift`, with the Context Mode group's matcher set per case and the anchored string written literally: `claude-code` with `*` returns an error naming the anchored matcher; `claude-code` with `^(Bash|Read|Grep|WebFetch|mcp__.*)$` returns `[]`; `openai-codex` with the anchored matcher returns an error. (`openai-codex` with `*` is already covered by the existing test.)
  - Negative control, before Step 2: `uv run pytest tests/test_lifecycle_hooks.py tests/test_validate_targets.py -q --tb=line -k "context_mode_pretool or context_mode_matcher"`. Record in the session log which cases fail on today's code and why. Expected: the lifecycle test fails because the matcher is `*`; the `claude-code` with `*` case fails because today's validator accepts it; the `claude-code` with the anchored matcher case fails because today's validator requires `*`; the `openai-codex` with the anchored matcher case already passes.

- [ ] **2. Narrow the matcher and the validator.**
  - Owner: `coder`. Files: `scripts/generate_targets.py`, `scripts/validate_targets.py`, `tests/test_validate_targets.py` (modify).
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - `scripts/generate_targets.py`: add `CLAUDE_CONTEXT_MODE_MATCHER = "^(Bash|Read|Grep|WebFetch|mcp__.*)$"` right after `OPENWIKI_BEGIN_MATCHER`, with a comment of at most five lines in the style of the comment above `OPENWIKI_BEGIN_MATCHER`: Claude Code reads it as an unanchored regex that it also tries on legacy tool names, hence the anchors; it lists what Context Mode 1.0.169 routes except Agent, whose only action rewrites the subagent prompt, a change auto mode refuses. Use the constant as the matcher of the Context Mode PreToolUse group in `render_claude_settings`. `render_codex_hooks` keeps `"*"`.
  - `scripts/validate_targets.py`: import the constant next to `OPENWIKI_BEGIN_MATCHER`. In `pretool_routing_errors`, set the observer matcher to the constant for `claude-code` and `"*"` for any other target; use it in `expected`; apply the observability-only check to the group with that matcher, and say "context-mode" instead of "wildcard" in that one message. Update the existing test's `"wildcard"` assertion to the new wording.
  - Must not: change the dispatcher, the filter, the Codex output, the Copilot `shared/hooks/hooks.json`, the Antigravity output, group order, timeouts, or any other validator message.
  - Run Step 1's command again (every case passes), then `uv run python .claude/scripts/verify.py fast --format text`.

- [ ] **3. Regenerate and refresh the self-install.**
  - Owner: orchestrator.
  - `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`. Confirm that `dist/multi-agent/.claude/settings.json` and `.claude/settings.json` carry the new matcher and that `dist/multi-agent/.codex/hooks.json` keeps `*`. Never hand-copy.

- [ ] **4. Update the documentation.**
  - Owner: `documenter` (CLOSEOUT step 1; runs in parallel with Steps 1-2 because the files do not overlap). Required Skills: `.claude/skills/documentation/SKILL.md`.
  - `docs/architecture.md`, "Target-native PreToolUse routing" (about lines 293-296): Claude's Context Mode group matches only `^(Bash|Read|Grep|WebFetch|mcp__.*)$`; Codex keeps the wildcard; one sentence on why (Context Mode's Agent action rewrites the subagent prompt, and Claude Code auto mode refuses a call whose input a hook changed).
  - `docs/smoke-tests.md` (about lines 209 and 220): the same correction; keep the dispatcher-filter sentence.
  - `docs/runtime-checks.md` (about line 248): the same correction. In the Context Mode bullet (about lines 94-110), add one short line: on Claude Code the PreToolUse hook runs only for that anchored matcher, because Claude Code reads such a matcher as an unanchored regex that it also tries on legacy tool names (for example `Task` for `Agent`), and Agent is left out. Leave the Codex line (about line 931) as it is.
  - Check `docs/target-mapping.md` and `README.md` for a claim that Claude's Context Mode PreToolUse hook runs for every tool; fix any you find.
  - Use plain words and short sentences.

- [ ] **5. Audit live advice for stale claims and record lessons.**
  - Owner: `documenter` for `README.md`, `docs/`, and `shared/` text; orchestrator for `.claude/MEMORY.md` and the session log.
  - Required Skills: `.claude/skills/documentation/SKILL.md`.
  - This phase is the big plan's last entry, so it runs the standing final-phase documentation, memory, and LEARN audit. Surfaces: root guidance (`CLAUDE.md`, `AGENTS.md`), `README.md`, `docs/`, `shared/policies/`, `shared/skills/`, `shared/agents/`, `shared/templates/`, `shared/review-profiles/`, state READMEs, the installed `.claude/` overlay after the self-install, and `.claude/MEMORY.md`.
  - Known items to record with their outcome:
    - `openwiki/architecture/hooks-and-guardrails.md` line 88 ("`*` runs only the optional `context-mode-dispatch.sh`"): stale, left for the next knowledge-refresh phase. No hand edits.
    - `.claude/MEMORY.md`: no entry recommends `*` for Context Mode; record that.
  - Leave dated records unchanged: archived plans, closed session logs, and dated `docs/` narratives.
  - Record each surface and its outcome under the exact heading `## Stale-claims surfaces checked` in this phase's closeout session log.
  - Add these `[LEARN]` entries to `.claude/MEMORY.md` and the session log:
    - `[LEARN:tooling] Claude Code 2.1.226 reads a hook matcher as exact names only when it holds just letters, digits, _, |, comma, space, or -; anything else is an unanchored JavaScript regex that is also tried on a tool's legacy names (Task for Agent, BashOutput for TaskOutput, KillBash for TaskStop). Anchor regex matchers: Bash|Read|mcp__.* also fires for TaskOutput and ReadMcpResourceTool. In auto mode a PreToolUse hook that returns updatedInput makes the call fail ("a hook changed this call's input after auto mode reviewed it").`
    - `[LEARN:workflow] Check a forwarded consumer report against the kit version the consumer runs. The 2026-11-11 report blamed the "*" Context Mode matcher for failing Agent calls in auto mode, but the kit has dropped hook input rewrites since de5a2f8 (2026-10-17); an Agent call that fails while curl is still redirected points to an unfiltered hook (an old install or the user-level context-mode plugin).`

- [ ] **6. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.
  - Focus: the matcher cannot fire for Agent or Task under Claude Code's rules and still fires for every tool Context Mode routes; the test's copy of the matcher rules matches the evidence; the Codex, Copilot, and Antigravity outputs are unchanged; the validator still rejects safety-lane drift; the docs state exactly what changed.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_lifecycle_hooks.py tests/test_validate_targets.py tests/test_openwiki_guard.py tests/test_context_mode_dispatch.py -q --tb=short
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- Run Claude Code 2.1.226's own hook matcher function, extracted from `~/.local/share/claude/versions/2.1.226` into the session scratchpad, against the generated matcher: it fires for exactly Bash, Read, Grep, WebFetch, and MCP tool names, and not for Agent, Task, TaskOutput, TaskStop, ReadMcpResourceTool, Edit, Write, or Glob. The binary is machine-specific, so this is not a required item.
- `CONTEXT_MODE_REAL=1 uv run pytest tests/test_context_mode_dispatch.py -q -k real_upstream`: the real pinned binary's Agent rewrite and `curl` deny still reach nothing.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)

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
