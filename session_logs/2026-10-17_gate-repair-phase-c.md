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
- [x] IMPLEMENT/VERIFY/REVIEW — two review rounds; final Gate Result `PASS`
  with no findings.
- [x] CLOSEOUT: final AI state, checkpoint, staged index, findings, phase
  receipt, closeout dry run, checkpoint, closeout receipt.
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

- **09:50** - Coder finished steps 1–2: root `.mcp.json` and
  `.vscode/mcp.json` use the guarded route; `root_mcp_adapter_errors` checks
  all three root adapters with their own keys; `mcp__context7` added to the
  Claude `search` map and grant check. Negative controls failed as expected.
  Generator comment corrected (Antigravity `inheritMcp` is undocumented).
  Self-install repopulated `.claude/bootstrap-root/` (clears the
  `verify.py fast` provenance mismatch the coder reported) and the installed
  agents (clears `check_runtime.py`). `fast` PASS, `validate_targets.py`
  PASS, `verify.py phase` PASS (pytest 2468 passed, 1 skipped). The
  installer's printed `git rm --cached ...` line is consumer advice only;
  every root adapter stayed tracked here.
- **09:55** - Documenter: parity rows, recorded follow-ups, and runtime-check
  bullets. Two live overclaims in `docs/smoke-tests.md` (lines 117, 119) sent
  back for fixing. For Phase E: `docs/sidecar-provider-contract.md:672-676`
  quotes older Codex docs on agent-file keys; decide there whether it is a
  dated record (errata) or live advice.

- **10:20** - Review round 1: Gate Result `PASS`, no CRITICAL or MAJOR, five
  MINOR (wiring test ignores helper arguments; GR-005 check covers only the
  `context-mode` entry while docs said "any direct start"; duplicate test
  helper; Codex "(confirmed)" without basis and "fixed" wording; duplicated
  runtime-checks bullet). Reviewer re-checked the Codex source at HEAD via
  Semble (no sandbox, approval, or MCP override field). All five sent back
  for fixing. Plan GR-005 wording corrected to the real check; Phase E
  follow-up now records that Codex ignores per-agent `sandbox_mode`.

- **10:45** - All five fixes landed (coder: wiring test records arguments,
  negative control with `TARGET_ROOT` failed; duplicate helper removed.
  Documenter: GR-005 scope wording, Codex evidence basis, "guarded" wording,
  duplicate bullet removed). Regenerate, self-install, `check_runtime.py`
  PASS, `verify.py fast` PASS, `validate_targets.py` PASS, `verify.py phase`
  PASS (pytest 2468 passed, 1 skipped). Review round 2 (same reviewer):
  Gate Result `PASS`, findings `[]`.

### Phase-boundary summary

- **Objective and change:** this repository's root `.mcp.json` (Claude) and
  `.vscode/mcp.json` (Copilot) start Context Mode through the guarded
  dispatcher, like root `.codex/config.toml`, and the validator checks all
  three; generated Claude agents with `search` get `mcp__context7`.
- **Deviations from the plan:** GR-005's wording was narrowed to match the
  approved step: the validator checks each root adapter's `context-mode`
  entry and does not detect a direct start under another server name
  (Phase D protects these files). This narrows a user-approved requirement
  and is reported to the user. No Codex or Antigravity code change: Codex
  agents already inherit MCP servers; Antigravity facts are undocumented.
- **Checks:** see `## Verification` below.
- **Open findings:** none. Recorded follow-ups (in `docs/target-mapping.md`
  and Phase E): Codex ignores per-agent `sandbox_mode`, so read-only Codex
  roles run with the parent session's sandbox; Antigravity MCP tool naming
  and subagent MCP access need a logged native run.
- **Next operation:** Phase D, guard coverage.

### Requirement mapping

- GR-005: `test_root_mcp_adapters_reject_a_direct_context_mode_start` (3
  root files), `test_root_mcp_adapters_read_each_file_with_its_own_key`,
  `test_validate_mcp_and_hooks_runs_the_root_adapter_check` (asserts
  `REPO_ROOT` and the shared route); real `validate_targets.py` run.
- GR-006: `test_claude_agents_list_context7_exactly_when_they_have_search`,
  `test_claude_agent_grant_check_requires_context7`,
  `test_render_claude_tools_skips_todo_and_maps_delegate_to_agent`; Codex and
  Antigravity evidence in this log and `docs/target-mapping.md`.
- GR-013: no model call; no version change; no network in required checks.

## [LEARN] Entries

- [LEARN:tooling] Codex custom agent files cannot override `sandbox_mode`,
  approval policy, or `mcp_servers`; the bootstrap's per-agent read-only
  sandbox is ignored.
- [LEARN:tooling] Antigravity `inheritMcp` is undocumented and MCP tool names
  in hook payloads are undocumented; claim no Antigravity subagent MCP
  access without a logged native run.
- [LEARN:workflow] After editing a tracked root adapter, refresh
  `.claude/bootstrap-root/` with the self-install before `verify.py`.

## Verification

- optional 1: NOT RUN — a new native Claude Code session and a reviewer-subagent tool probe in a disposable generated install are user-run host checks; the validator checks the root route offline, and the 2026-10-17 probe in this session already showed server-level MCP grants reach Claude subagents.
- optional 2: NOT RUN — a native Codex tool-list check is a user-run host check; the root Codex config was already guarded and validator-checked before this phase.
- optional 3: NOT RUN — a VS Code Copilot tool-list check is a user-run host check; the root `.vscode/mcp.json` route is validator-checked offline.
- optional 4: NOT RUN — an Antigravity `agy mcp list` run and an MCP call through the bridge are user-run host checks; the bridge still denies MCP calls by design, recorded as a gap.

## Open Questions / Next Steps

- Next: Phase D, `2026-10-17_phase-D-guard-coverage`.
