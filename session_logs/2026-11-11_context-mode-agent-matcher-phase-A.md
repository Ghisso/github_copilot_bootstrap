# Session: Context Mode PreToolUse matcher skips Agent

**Date:** 2026-11-11
**Plan:** `.claude/plans/2026-11-11_phase-A-context-mode-agent-matcher.md`
**Status:** IN-PROGRESS

## Goal

Generated Claude Code settings run the Context Mode PreToolUse hook only for `^(Bash|Read|Grep|WebFetch|mcp__.*)$`, never for `Agent` or `Task`; the validator, a test, and the docs enforce and describe it. Codex, Copilot, and Antigravity outputs stay unchanged.

## Work Log

- Trigger: the user pasted a consumer agent's report (`translation-workflow`, seen 2026-11-09 and 2026-11-11): every subagent launch fails in auto mode with "The server-side auto mode classifier gave no verdict for Agent: a hook changed this call's input after auto mode reviewed it", blamed on the `*` Context Mode PreToolUse matcher and Context Mode 1.0.169's Agent prompt rewrite (`routing.mjs` 894-916).
- Checked the claims. Generator: `render_claude_settings` and `render_codex_hooks` both write `*`; `pretool_routing_errors` requires it. Since `de5a2f8` (2026-10-17) the dispatcher's `--hook-output` filter forwards only `hookEventName` and filtered `additionalContext`: all seven recorded Claude PreToolUse fixtures (agent, bash-curl, bash-ls, ctx-execute, grep, read, webfetch) forward nothing, and `CONTEXT_MODE_REAL=1 uv run pytest tests/test_context_mode_dispatch.py -q -k real_upstream` passed (1 passed) against the real pinned binary. So the Agent rewrite and the `curl` deny never reach Claude Code from the current kit.
- Live probe, this session (auto mode, this repository's `.claude/settings.json` with `*`, dispatcher and filter identical in content to `shared/`): an Explore subagent started on the first try and finished; `/tmp/context-mode-latency-<this session>-Agent.txt` appeared at launch time, so the upstream hook ran for that Agent call.
- Conclusion for the report: the failure needs an unfiltered Context Mode hook, either a consumer install older than `de5a2f8` or the user-level plugin `context-mode@context-mode` (enabled in `~/.claude/settings.json`; not installed on this machine). A sidecar install ships no hooks and no `.claude/settings.json`. The report's "curl is still redirected" check cannot pass on a current install, because the filter drops that deny on purpose. `translation-workflow` is not on this machine and `gh` is not authenticated, so its installed version was not checked.
- Matcher semantics: extracted Claude Code 2.1.226's hook matcher function and legacy-name table from `~/.local/share/claude/versions/2.1.226` and ran them under Node (scratchpad `matcher-probe/claude_matcher.mjs`). `*` fires for all 14 probe names. The reported `Bash|Read|Grep|WebFetch|mcp__.*` skips Agent and Task but also fires for TaskOutput, TaskStop (legacy BashOutput, KillBash), and ReadMcpResourceTool. `^(Bash|Read|Grep|WebFetch|mcp__.*)$` fires for exactly Bash, Read, Grep, WebFetch, and the two MCP names.
- Agent definitions already carry static Context Mode guidance (the four guarded tools) in the coder, planner, reviewer, documenter, and orchestrator prompts, so no agent text changes.
- Plan written by the orchestrator from the user's explicit request (one phase, no new module or architecture decision, so no planner or devil's-advocate round). Plan files validated. Pre-flight: `dev` clean and level with `origin/dev` at `d650999`. Created `context-mode-agent-matcher_implementation`; the branch hook set the big plan `in-progress` (`started_at: 2026-11-11T12:55:24Z`) and activated this phase.
- Coder (Steps 1-2), tests first. Negative control on the unchanged generator and validator (`-k "context_mode_pretool or context_mode_matcher"`): 3 failed, 1 passed, as planned. `test_rendered_claude_context_mode_pretool_matcher_skips_agent` failed with `assert '*' not in ('', '*')`; `[claude-wildcard]` failed because the old validator accepted `*` for `claude-code`; `[claude-anchored]` failed because the old validator required `*`; `[codex-anchored]` already passed. After the change: 4 passed. Code: `CLAUDE_CONTEXT_MODE_MATCHER` plus a four-line comment in `scripts/generate_targets.py`, used by `render_claude_settings`; `pretool_routing_errors` picks the observer matcher by target and its one message now says "context-mode" instead of "wildcard". Codex output untouched. ruff, ruff format, and mypy clean; `verify.py fast` PASS.
- Orchestrator review of the coder diff: the test helper's plain-list branch ignored legacy names (Claude Code maps a listed `Task` to `Agent`), so it was not the faithful copy its comment claimed. Coder fixed it (one `names` tuple used by both branches); a throwaway check confirmed `Bash|Task` now fires for `Agent`.
- Documenter (Step 4 and the docs half of Step 5): `docs/architecture.md`, `docs/smoke-tests.md` (two lines), `docs/runtime-checks.md` (three-group line and one passage in the Context Mode bullet). I re-wrapped one long line in `docs/runtime-checks.md`. Audit outcomes are under `## Stale-claims surfaces checked`.
- Step 3: `generate_targets.py --all`, then `install_bootstrap.py . --allow-self --local-only`. `dist/multi-agent/.claude/settings.json` and `.claude/settings.json` now carry `^(Bash|Read|Grep|WebFetch|mcp__.*)$`; `dist/multi-agent/.codex/hooks.json` keeps `*`.
- Checks on that tree: the plan's pytest set 403 passed, 1 skipped (the opt-in real-binary test); `validate_targets.py` PASS; `check_runtime.py` PASS; `validate_plan_frontmatter.py` exit 0. Optional: Claude Code 2.1.226's own matcher code on the generated value fires for Bash, Read, Grep, WebFetch, and three MCP names, and not for Agent, Task, TaskOutput, TaskStop, ReadMcpResourceTool, Edit, Write, Glob, NotebookEdit, WebSearch, or Skill; `CONTEXT_MODE_REAL=1 ... -k real_upstream` 1 passed.
- `verify.py phase --format text` on that tree: PASS (ruff 0, mypy 0, pytest 5014 passed, 1 skipped; VFY-GEN-001 PASS).
- Review round 1 started: `reviewer` with `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`; the diff packet is the outer-repo `git diff`.

## [LEARN] Entries

- (filled at closeout)

## Verification

```text
# verify closeout --format text summary lines
```

## Open Questions / Next Steps

- User follow-up: find out which unfiltered hook the consumer runs, then refresh it.
