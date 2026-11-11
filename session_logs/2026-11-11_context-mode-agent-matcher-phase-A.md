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
- Review round 1 (six profiles): gate PASS, no CRITICAL or MAJOR, two MINORs, both fixed. (1) `docs/runtime-checks.md`: the pin-bump procedure did not say to recheck the Claude matcher against the new version's routed tools, and the recorded fixtures cover a fixed tool set, so a newly routed tool would be skipped silently; added step 3 (compare `CLAUDE_CONTEXT_MODE_MATCHER` with `routePreToolUse` and extend the test). (2) `tests/test_lifecycle_hooks.py`: the helper comment claimed a full copy of the legacy-name table and the `TaskStop` row was never asserted; the coder reworded the comment (only the rows for Agent, TaskOutput, TaskStop; session aliases not modelled) and added `TaskStop` to the must-not-fire tuple. Reviewer notes also acted on: re-wrapped the orphan line in `docs/architecture.md`, and both `docs/architecture.md` and `docs/runtime-checks.md` now say the filter already drops the Agent rewrite, so leaving Agent out is a second safeguard.
- After the fixes: regenerated, refreshed the self-install, and re-ran `verify.py phase`.

## [LEARN] Entries

- [LEARN:tooling] Claude Code 2.1.226 reads a hook matcher as exact names only when it holds just letters, digits, `_`, `|`, comma, space, or `-` (a listed legacy name such as `Task` still counts for `Agent`); anything else is an unanchored JavaScript regex that is also tried on a tool's legacy names (`Task` for `Agent`, `BashOutput` for `TaskOutput`, `KillBash` for `TaskStop`). Anchor regex matchers: `Bash|Read|mcp__.*` also fires for `TaskOutput` and `ReadMcpResourceTool`. In auto mode a PreToolUse hook that returns `updatedInput` makes the call fail ("a hook changed this call's input after auto mode reviewed it"). Found by running the matcher function extracted from the installed binary under Node.
- [LEARN:workflow] Check a forwarded consumer report against the kit version the consumer runs. The 2026-11-11 report blamed the `*` Context Mode matcher for failing Agent calls in auto mode, but the kit has dropped hook input rewrites since `de5a2f8` (2026-10-17); an Agent call that fails while `curl` is still redirected points to an unfiltered hook (an old install or the user-level `context-mode@context-mode` plugin).

## Stale-claims surfaces checked

- `CLAUDE.md`, `AGENTS.md`: clean (no Context Mode matcher claim).
- `README.md`: clean; its Context Mode sections cover the pin, the cache, and the MCP filter, with no matcher or every-tool claim.
- `docs/architecture.md`: fixed; "Target-native PreToolUse routing" gives the per-target matcher, why it is anchored, why Agent is left out, and that the filter already drops the rewrite.
- `docs/smoke-tests.md`: fixed (the Claude and Codex group list, and the observability bullet now covers both targets).
- `docs/runtime-checks.md`: fixed (the three-group line, one passage in the Context Mode bullet, and a new pin-bump step 3 to recheck the matcher against `routePreToolUse`). Its Codex line ("wildcard-observability matcher groups", line 934) is still accurate.
- `docs/target-mapping.md`, `docs/native-client-acceptance.md`, `docs/plan-deterministic-commit-gate.md`, `docs/sidecar-provider-contract.md`: clean.
- The `*` statements about `.agents/hooks.json` in `docs/runtime-checks.md` and `docs/smoke-tests.md`: still accurate; that is the Antigravity safety bridge, not a Context Mode hook.
- `shared/policies/`: clean; `tool-routing.instructions.md` and `workspace.instructions.md` make no matcher claim.
- `shared/skills/`, `shared/agents/`, `shared/templates/`, `shared/review-profiles/`, and state READMEs under `shared/`: clean. The agent prompts already carry static Context Mode guidance (the four guarded tools).
- Installed `.claude/` overlay: refreshed by the self-install; `.claude/settings.json` carries the anchored matcher.
- `.claude/MEMORY.md`: no entry recommended `*` for Context Mode; the gate-repair entry on upstream hook output is still accurate. Two new entries added (above).
- `openwiki/architecture/hooks-and-guardrails.md:88` ("`*` runs only the optional `context-mode-dispatch.sh`"): stale, left for the next knowledge-refresh phase; OpenWiki pages change only through OpenWiki's tools, and a one-phase plan gets no refresh phase. `docs/architecture.md` links to that page for the matcher groups, so the two disagree until then.
- Dated records (`docs/2026-*`, archived plans, closed session logs): left unchanged.

## Verification

```text
# verify closeout --format text summary lines
```

## Open Questions / Next Steps

- User follow-up: find out which unfiltered hook the consumer runs, then refresh it.
