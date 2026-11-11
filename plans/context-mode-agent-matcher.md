---
name: context-mode-agent-matcher
type: big-plan
status: complete
originating_branch: dev
implementation_branch: context-mode-agent-matcher_implementation
started_at: 2026-11-11T12:55:24Z
phases:
  - 2026-11-11_phase-A-context-mode-agent-matcher
current_phase: 
---

# Big Plan: Context Mode PreToolUse Matcher Skips Agent

## Context

On 2026-11-11 a consumer agent (in `translation-workflow`) reported that every subagent launch fails in Claude Code auto mode with "The server-side auto mode classifier gave no verdict for Agent: a hook changed this call's input after auto mode reviewed it". Its analysis: generated Claude Code settings run `context-mode-dispatch.sh claude-code pretooluse` under `"matcher": "*"`, and Context Mode 1.0.169 (`hooks/core/routing.mjs` lines 894-916) answers every Agent call with `modify` and an `updatedInput` that appends a `<context_window_protection>` block to the subagent prompt.

Checked on 2026-11-11 against this repository:

- The generator writes that group in `render_claude_settings` (`scripts/generate_targets.py`, about line 1127) and, for Codex, in `render_codex_hooks` (about line 1233). `pretool_routing_errors` (`scripts/validate_targets.py`, about line 1502) requires `*` for both.
- Since commit `de5a2f8` (2026-10-17, gate-repair Phase B), the dispatcher passes upstream hook output through `context-mode-mcp-filter.mjs --hook-output`, which forwards only `hookEventName` and filtered `additionalContext`. The Agent `updatedInput` and the `curl` deny are both dropped. Every recorded Claude PreToolUse fixture under `tests/fixtures/context_mode_hook/1.0.169/claude-code/` forwards nothing through the filter, and `CONTEXT_MODE_REAL=1 uv run pytest tests/test_context_mode_dispatch.py -q -k real_upstream` passes against the real pinned binary.
- Live probe in this repository, in auto mode, with today's `*` matcher and filtered dispatcher: a subagent started on the first try, and the upstream hook ran for that Agent call (its `/tmp/context-mode-latency-<session>-Agent.txt` marker appeared at launch time).
- So the reported failure needs an unfiltered Context Mode hook: a consumer install older than `de5a2f8`, or the user-level plugin `context-mode@context-mode` (enabled in `~/.claude/settings.json` on this machine, though not installed here), which `docs/runtime-checks.md` already lists as outside this repository's control. A sidecar install ships no hooks and no `.claude/settings.json` (README, "What neither profile installs").
- Claude Code 2.1.226's own matcher function (`WoS` and the `rns` legacy-name table, extracted from `~/.local/share/claude/versions/2.1.226` and run under Node) reads `*` or an empty matcher as every tool; a matcher made only of letters, digits, `_`, `|`, `,`, space, and `-` as exact names; and anything else as an unanchored JavaScript regex, also tried on the tool's legacy names (`Task` for `Agent`, `BashOutput` for `TaskOutput`, `KillBash` for `TaskStop`). The reported pattern `Bash|Read|Grep|WebFetch|mcp__.*` skips Agent and Task but also fires for `TaskOutput`, `TaskStop`, and `ReadMcpResourceTool`. The anchored `^(Bash|Read|Grep|WebFetch|mcp__.*)$` fires for exactly Bash, Read, Grep, WebFetch, and MCP tools.

The narrower matcher is still worth having: Agent calls never reach Context Mode's only Agent action (a prompt rewrite), even if the filter regresses, and Claude Code stops starting the dispatcher for tools Context Mode does not route.

## Goals

- Generated Claude Code settings run the Context Mode PreToolUse hook only for `^(Bash|Read|Grep|WebFetch|mcp__.*)$`, never for `Agent` or `Task`.
- The validator requires that exact matcher for Claude Code and keeps `*` for Codex.
- A test fails if the Claude Code matcher is `*` or fires for `Agent` or `Task` under Claude Code's matcher rules, and checks that the routed tools still fire.
- Docs describe the new Claude matcher; `.claude/MEMORY.md` records the matcher rules and the auto-mode failure.

## Non-Goals and Constraints

- Codex keeps `*`. The filter forwards no input rewrite to any client, so Codex does not have this failure. GitHub Copilot hooks have no matcher field. Antigravity wires no Context Mode hook. None of their outputs change.
- The advisory-only filter (`de5a2f8`) stays. It drops upstream's `curl` deny on purpose, because that deny points the agent to `ctx_execute` and `ctx_fetch_and_index`, which the kit's MCP filter blocks. So after a refresh the kit does not redirect `curl`; the report's "curl is still redirected" check can only pass on an unfiltered install.
- Agent definitions already carry static Context Mode guidance: the coder, planner, reviewer, documenter, and orchestrator prompts name the four guarded tools. No agent text changes. Upstream's injected block names blocked and plugin-prefixed tools, so it must not be copied.
- No edits to consumer repositories. Refreshing `translation-workflow` is the user's follow-up.
- No edits under `openwiki/`. The stale-claims audit records `openwiki/architecture/hooks-and-guardrails.md` line 88 for the next knowledge refresh.
- `dist/` and the `.claude/` self-install are regenerated (`generate_targets.py --all`, then `install_bootstrap.py . --allow-self --local-only`), never hand-copied.
- Control-plane/high-risk work: every coding step applies `.claude/skills/ponytail/SKILL.md` in `full` mode. Review uses `code`, `architecture`, `security`, `tests`, `ponytail`, and `documentation`.

## Design Overview

One constant in `scripts/generate_targets.py`, next to `OPENWIKI_BEGIN_MATCHER`:

`CLAUDE_CONTEXT_MODE_MATCHER = "^(Bash|Read|Grep|WebFetch|mcp__.*)$"`, with a short comment: Claude Code reads such a matcher as an unanchored regex that it also tries on legacy tool names, hence the anchors; it lists the tools Context Mode 1.0.169 routes except Agent, whose only action rewrites the subagent prompt, a change auto mode refuses.

`render_claude_settings` uses it for the Context Mode PreToolUse group. `pretool_routing_errors` expects it for `claude-code` and `*` for every other target, and applies its observability-only rule to that group.

### Decisive assumptions and evidence

| Assumption | Evidence | Remaining limit |
| --- | --- | --- |
| Claude Code reads the anchored matcher as a regex that never fires for Agent or Task | `WoS`, `rW`, `Flo`, `Ulo`, `Ucr`, and `rns` extracted from the installed 2.1.226 binary and run under Node: `*` fires for all 14 probe names; the anchored form fires only for Bash, Read, Grep, WebFetch, and two MCP names | Other Claude Code versions were not inspected; an anchored regex is the safe form for any version that reads non-plain matchers as regex |
| Context Mode 1.0.169 routes only Bash, Read, Grep, WebFetch, Agent, and MCP tools | `routePreToolUse` in `context-mode/hooks/core/routing.mjs`: the `canonical ===` branches at lines 704, 848, 870, 875, 894; ctx_* and external MCP at 925-1012; everything else returns `null` | A pin bump must recheck this list (the docs' re-capture procedure) |
| Leaving out Agent loses nothing | The filter already drops the Agent rewrite (`pretooluse-agent.json` forwards nothing); the kit's PostToolUse Context Mode hook runs only for Bash | None |

### Contracts touched

| Contract (source) | Behavior to keep | Planned change | Evidence |
| --- | --- | --- | --- |
| `render_claude_settings`, `scripts/generate_targets.py` | Group order, scripts, timeouts | Context Mode PreToolUse matcher | New test; `test_rendered_claude_lifecycle_uses_serialized_durability_boundaries` |
| `render_codex_hooks` | Everything | None | `tests/test_openwiki_guard.py` closes-the-loop test |
| `pretool_routing_errors`, `scripts/validate_targets.py` | Four groups; safety scripts scoped; observer group observability-only | Target-specific observer matcher | `tests/test_validate_targets.py`, `tests/test_openwiki_guard.py` |
| Dispatcher and filter, `shared/hooks/scripts/` | Advisory-only hook lane | None | `tests/test_context_mode_dispatch.py` |

## Phases

- [x] `2026-11-11_phase-A-context-mode-agent-matcher` — anchored Claude matcher, validator, tests, docs, and the stale-claims audit.

## Verification

```bash
uv run python scripts/validate_plan_frontmatter.py .claude/plans/context-mode-agent-matcher.md .claude/plans/2026-11-11_phase-A-context-mode-agent-matcher.md
```

## Completion Evidence

The only phase, `2026-11-11_phase-A-context-mode-agent-matcher`, is also the last one. It runs the documentation, memory, and LEARN audit across all live-advice surfaces and records each audited surface and its outcome under `## Stale-claims surfaces checked` in its closeout session log. A one-phase plan gets no knowledge-refresh phase; the audit lists the stale OpenWiki statement for the next one. The phase has its own verification, review, findings, session log, commit, and normal push evidence.
