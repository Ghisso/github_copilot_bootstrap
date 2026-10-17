---
name: 2026-10-17_phase-C-mcp-surface-parity
type: small-plan
parent_plan: gate-repair
phase_index: 3
status: planned
closeout_session_log:
---

# Small Plan: MCP Surface Parity

## Scope

Make the documented four-tool Context Mode server true for every client
configuration in this repository (GR-005). Give Claude Code subagents the
same Context7 access the other clients already have (GR-006). Record, with
evidence, how Codex and Antigravity agents reach MCP servers. Work in
priority order: Claude Code, Codex, GitHub Copilot, Antigravity. Today the
tracked root `.mcp.json` (Claude) and `.vscode/mcp.json` (Copilot) start
`context-mode` directly. The root `.codex/config.toml`, the installed
`.agents/mcp_config.json`, and every generated target already use the
guarded dispatcher. Context7 stays a generated-target capability; it is not
added to this repository's root adapters (big-plan non-goal).

## Steps

- [ ] **1. Guard the root Claude and Copilot MCP adapters (GR-005).**
  **Owner:** coder.
  **Files:** modify root `.mcp.json` and root `.vscode/mcp.json`;
  modify `scripts/validate_targets.py` (the authoring-config check near the
  root Codex rule, about lines 3007–3024); modify
  `tests/test_validate_targets.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Set each root adapter's `context-mode` entry to exactly the guarded route
  in `shared/mcp/servers.json`. Keep the other root entries (`semble`, and
  `openwiki` in `.mcp.json`) unchanged. Extend the validator so that every
  tracked root MCP adapter (Claude `mcpServers`, Copilot `servers`, Codex
  `mcp_servers`) must carry the shared guarded `context-mode` route. Read
  each file with its own key; do not duplicate the route literal.
  `.claude/bootstrap-root/` mirrors root adapters; refresh it only through
  the supported install or state-sync path, never by hand.
  **Tests:** for each of the three root files, a direct `context-mode`
  command fails validation and the guarded route passes.

- [ ] **2. Grant Context7 to Claude subagents (GR-006, Claude).**
  **Owner:** coder.
  **Files:** modify `scripts/generate_targets.py` (`CLAUDE_TOOL_MAP`
  `search`, about line 104, and its comment), `scripts/validate_targets.py`
  (the Claude agent grant check, about line 2471), and
  `tests/test_validate_targets.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Add `mcp__context7` to the `search` capability. The 2026-10-17 probe
  settled that a server-level grant exposes a project server's tools.
  Context7 is read-only documentation lookup.
  **Tests:** every generated Claude agent with `search` lists
  `mcp__context7`; agents without `search` do not.

- [ ] **3. Settle Codex MCP inheritance from documentation (GR-006, Codex).**
  **Owner:** coder.
  **Files:** modify `docs/target-mapping.md`; modify the Codex agent
  renderer in `scripts/generate_targets.py` and its tests only for a
  documented gap.
  **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`,
  `shared/skills/ponytail/SKILL.md` (full).
  Use Context7 or WebFetch (working after Phase B) on the official Codex
  documentation and source for custom agents in `.codex/agents/*.toml`.
  Question: do spawned agents get the session's `mcp_servers`? Record the
  answer with links. When the documentation shows a per-agent setting is
  required, render it for agents with the `search` capability and test it.
  Otherwise record "inherits session MCP servers" in the parity table.

- [ ] **4. Settle Antigravity MCP reachability from documentation (GR-006, Antigravity).**
  **Owner:** coder.
  **Files:** modify `docs/target-mapping.md` and `docs/runtime-checks.md`;
  modify `shared/hooks/scripts/antigravity-pretool.py`, the Antigravity MCP
  config rendering in `scripts/generate_targets.py`, and
  `tests/test_hook_gates.py` only for documented behavior.
  **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`,
  `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/testing-patterns/SKILL.md`.
  Two questions from the official Antigravity documentation: where `agy`
  reads workspace MCP servers (a 2026-08 run reported `No MCP servers
  configured` for `.agents/mcp_config.json`), and what `toolCall.name` an MCP
  call carries in a PreToolUse payload. The bridge denies unknown tools today,
  so MCP calls are blocked. Only with documented answers: fix the config
  location, and let the bridge allow exactly the read-only MCP tools (Semble
  `search` and `find_related`, the four allowlisted Context Mode tools, the
  Context7 lookup tools) by their documented names. Everything else stays
  denied. Without documented answers, change no code and record the gap and
  its evidence.

- [ ] **5. Regenerate, refresh, document, review, close out.**
  **Owner:** orchestrator; fresh reviewer; documenter after review.
  Run `uv run python scripts/generate_targets.py --all` and
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  before verification. Update the parity rows in `docs/target-mapping.md`
  and the Context Mode lines in `docs/runtime-checks.md`. State that the
  user-level `context-mode@context-mode` plugin, when enabled, adds an
  unfiltered server and hooks the repository cannot govern.
  **Required Skills:** `shared/skills/documentation/SKILL.md`,
  `shared/skills/code-review/SKILL.md`.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/test_validate_targets.py tests/test_context_mode_mcp_filter.py tests/test_hook_gates.py -q
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Claude Code: start a new session in this repository (a running session
  does not reload `.mcp.json`) and record that the project `context-mode`
  server lists only `ctx_index`, `ctx_search`, `ctx_stats`, `ctx_doctor`.
  Then spawn the `reviewer` subagent in a disposable generated install and
  record whether it lists `mcp__context7__*` tools.
- Codex: in a new session, record the Context Mode tool list.
- GitHub Copilot: in VS Code, record the Context Mode tools shown for the
  root `.vscode/mcp.json` server.
- Antigravity: in a disposable install, record `agy mcp list` and one
  allowed MCP call through the bridge.

## Review Profiles

Use `.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Give the reviewer the
documentation evidence for steps 3 and 4, GR-005 and GR-006, and the final
diff.

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
