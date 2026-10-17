# Session: Gate repair — Phase C, MCP surface parity

**Date:** 2026-10-17
**Plan:** .claude/plans/2026-10-17_phase-C-mcp-surface-parity.md
**Parent plan:** .claude/plans/gate-repair.md
**Status:** IN-PROGRESS

## Goal

Make every tracked root MCP adapter start Context Mode through the guarded
dispatcher (GR-005); give Claude subagents Context7; settle Codex and
Antigravity MCP reachability from documentation (GR-006).

## Task Tracking

- [x] PRE-FLIGHT: Phase B committed (`de5a2f8`) and pushed; post-commit hook
  activated Phase C. No material impact on this phase from A or B (GR-002
  already treats `.mcp.json` and `.vscode/mcp.json` as control-plane).
- [x] PLAN WHEN NEEDED: approved plan is implementation-ready; no planner.
- [ ] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT — repeat until verification and review pass.
- [ ] COMMIT
- [ ] PUSH

## Work Log

- **09:05** - Steps 1–2 delegated to a coder; steps 3–4 documentation
  research delegated in parallel to a read-only research agent (code
  changes from its answers, if any, go to the coder afterwards).

- **09:25** - Steps 3–4 research (read-only agent; WebFetch worked for every
  official page; `gh api` needed login). Results, all looked up 2026-10-17:
  - Codex MCP (step 3): confirmed by the official subagents page
    (`https://learn.chatgpt.com/docs/agent-configuration/subagents`, the
    redirect target of `developers.openai.com/codex/subagents`) and source
    (`openai/codex` `codex-rs/core/src/agent/role.rs`, commit
    `7ac954ea24116700632906d89715f7755cd3523e`): custom agents inherit the
    parent's MCP servers; no per-agent MCP field. No code change needed.
  - Codex follow-up: a custom agent file cannot override `sandbox_mode` or
    approval policy (same sources; `AgentRoleOverrides` copies only
    instructions, model, effort, summary, verbosity, personality, service
    tier). The bootstrap emits `sandbox_mode = "read-only"` for read-only
    roles, which Codex ignores; only `features.*` can be disabled per
    agent. Recorded as a follow-up, not fixed here (agent definitions are
    a big-plan non-goal).
  - Antigravity MCP config (step 4): `.agents/mcp_config.json` with one
    `mcpServers` object is the documented workspace location
    (`https://antigravity.google/docs/mcp`). Why `agy mcp list` reported
    none in 2026-08 is undocumented.
  - Antigravity hook payload: `toolCall.{name,args}` documented
    (`https://antigravity.google/docs/hooks`); the MCP tool-name format in
    `toolCall.name` is undocumented. No bridge change (plan rule).
  - Antigravity `inheritMcp`: not in the official frontmatter table
    (`https://antigravity.google/docs/subagents`); the documented field is
    `mcpServers: object[]` with no entry shape shown, and MCP is not in
    the documented inherited scopes. Subagent MCP access is unverified; no
    code change without documented shape. Parity matrix row for Context7
    on Antigravity is downgraded to "unverified".

## [LEARN] Entries

## Verification

## Open Questions / Next Steps

- Await coder and research results.
