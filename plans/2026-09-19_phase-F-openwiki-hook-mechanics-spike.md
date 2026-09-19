---
name: 2026-09-19_phase-F-openwiki-hook-mechanics-spike
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 6
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-09-19_phase-F-openwiki-hook-mechanics-spike

## Scope

The guard planned for Phase G rests on host hook behavior for MCP tool calls that is documented
(code.claude.com/docs/en/hooks; learn.chatgpt.com/docs/hooks) but has not been observed. This
phase observes it, on Claude Code and on Codex, using a throwaway MCP server and a hook logger in
a scratch repository. It follows `.claude/skills/integration-gate-spike/SKILL.md`: evidence
only. It writes no adapter code, no hook script for this repository, and no generator wiring.
It does not require OpenWiki to be installed or enabled and does not touch this repository's
control plane.

Status is `in-progress` because this phase becomes the big plan's `current_phase` when the
cancelled Phase D is replaced; that mirrors what the branch hooks would otherwise do.

Unknowns that change the guard (verify only these):

| ID | Unknown |
| --- | --- |
| U1 | `PreToolUse` fires on an MCP tool call |
| U2 | payload `tool_name` is `mcp__<server>__<tool>` and an exact-name matcher fires |
| U3 | a deny is honored: the tool does not execute |
| U4 | `PostToolUse` fires after a successful call and carries `tool_input` |
| U5 | `tool_response` is present in the `PostToolUse` payload |
| U6 | what fires when the tool returns `isError: true` |
| U7 | hook `cwd` and project-directory environment variable |

## Steps

### Step F1 — Build the scratch repository and throwaway tooling (outside this repository)

- [ ] **Owner:** `coder`
- **Target files (all in a scratch directory, for example `/tmp/openwiki-hook-spike`; nothing
  in this repository):** `spike_mcp_server.py`, `spike_hook.py`, `.mcp.json`,
  `.claude/settings.json`, `.codex/config.toml`, `.codex/hooks.json`
- **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`
- **Setup:** `git init` the scratch directory and make one empty commit (hosts and OpenWiki
  alike treat a Git top-level as the project). Use absolute paths in the Codex config.
- **`spike_mcp_server.py` (stdlib only; verified in the planning session against a JSON-RPC
  client):** newline-delimited JSON-RPC over stdio; answers `initialize` (echo the client's
  `protocolVersion`, `capabilities: {tools: {}}`, `serverInfo: {name: "spike", version:
  "0.0.1"}`), ignores `notifications/initialized`, answers `ping`, lists one tool
  `write_marker` with `inputSchema {mode: enum[init, update, fail]}`; on `tools/call` appends
  `{"at", "mode"}` to `server-calls.log`, then for `fail` returns `isError: true`, otherwise
  writes `marker-<mode>.txt` and returns text; any other request with an id gets error
  `-32601`.
- **`spike_hook.py <pre|post|post-failure>`:** reads the payload from stdin and appends one
  JSON line to `hook-log.jsonl` with `stage`, `cwd`, every environment variable ending in
  `PROJECT_DIR` (name and value), the names of `CLAUDE_*`/`CODEX_*` variables, sorted payload
  keys, `hook_event_name`, `tool_name`, `tool_input`, whether `tool_response` is present and a
  300-character preview of it. On `pre` with `tool_input.mode == "init"` it prints
  `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"spike: mode init is denied by the PreToolUse hook"}}`
  and exits 0; otherwise prints nothing and exits 0.
- **Claude Code wiring:** `.mcp.json` → `{"mcpServers":{"spike":{"command":"python3","args":["<ABS>/spike_mcp_server.py"]}}}`;
  `.claude/settings.json` → `hooks.PreToolUse`, `hooks.PostToolUse`, and
  `hooks.PostToolUseFailure`, each one entry with `matcher: "mcp__spike__write_marker"` and
  command `python3 "$CLAUDE_PROJECT_DIR/spike_hook.py" <pre|post|post-failure>`, timeout 10.
- **Codex wiring:** `.codex/config.toml` → `[mcp_servers.spike]` with the same command/args;
  `.codex/hooks.json` → root-level `PreToolUse` and `PostToolUse` arrays (the shape this
  repository's generated `.codex/hooks.json` already uses), each with
  `matcher: "mcp__spike__write_marker"` and command `python3 <ABS>/spike_hook.py <pre|post>`.
- **Acceptance criteria:** `python3 -m py_compile` passes for both scripts; a scripted
  `initialize` → `tools/list` → `tools/call` round trip against the server succeeds; this
  repository's `git status` is unchanged.

### Step F2 — Observe Claude Code

- [ ] **Owner:** `coder` (the user launches the session and approves the project MCP server)
- **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`
- **Procedure:** launch Claude Code with the scratch directory as the working directory;
  approve the `spike` project MCP server when prompted; run `/hooks` and record that the three
  matchers are registered; record `claude --version`. Then issue exactly three prompts:
  (1) "Call the spike tool `write_marker` with mode `init`." (2) "… with mode `update`."
  (3) "… with mode `fail`." Do not let the model retry or vary the arguments; if it does,
  record that as an observation.
- **Record for U1–U7:** `hook-log.jsonl` lines (stage, `tool_name`, payload keys, `tool_input`,
  `tool_response` presence, `cwd`, project-dir variable); presence or absence of
  `marker-init.txt`, `marker-update.txt`, `marker-fail.txt`; `server-calls.log` contents; what
  the model reported after the denied call.
- **Acceptance criteria:** every U row has an observed value or an explicit "not observable
  because …"; no value is copied from documentation.

### Step F3 — Observe Codex

- [ ] **Owner:** `coder` (the user launches the session and grants project trust)
- **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`
- **Procedure:** delete the marker files, `server-calls.log`, and `hook-log.jsonl`; launch
  Codex in the scratch directory; grant project trust so `.codex/config.toml` and
  `.codex/hooks.json` load; record `codex --version`; repeat the three prompts; record the
  same artifacts. If Codex is unavailable on this host, record that fact and the reason; the
  decision then applies O4 to Codex provisionally and Phase I re-probes it.
- **Acceptance criteria:** as F2.

### Step F4 — Decide and record

- [ ] **Owner:** `coder` for the tables, `documenter` for prose
- **Target files:**
  - create `docs/2026-09-19-openwiki-hook-mechanics-spike.md` (dated narrative; the single
    evidence document; use the skill's "Integration Spike" table with one row per U per host,
    the outcome mapping, the decision, and both scripts inline so the spike is reproducible)
  - create `.claude/explorations/2026-09-19_openwiki-hook-mechanics-spike/` holding the raw
    `hook-log.jsonl` and `server-calls.log` from each host (redact nothing but tokens; there
    should be none)
- **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`,
  `shared/skills/documentation/SKILL.md`, `shared/skills/humanize/SKILL.md`
- **Outcome mapping (per host):** O1 GO when U1–U4 hold; O2 when `PostToolUse` does not fire
  after success or nothing fires on `isError`; O3 when the deny is not honored (marker or server
  log shows `init` executed); O4 when `PreToolUse` does not fire or no stable name is
  observable; O5 when the name differs from `mcp__<server>__<tool>` but is stable.
- **Decision text must state one of:** "GO: build Phase G as written"; "GO with adaptations:
  build Phase G applying <O2/O3/O5 per host>"; or "RE-PLAN: exit condition met — Phase G must
  be re-planned before implementation". The exit condition is met when O3 or O4 applies to
  Claude Code, or when `PreToolUse` fires on neither host.
- **Acceptance criteria:** the decision is derivable from the tables alone; the document
  contains no adapter design beyond the outcome mapping already in this plan.

### Step F5 — Review the evidence

- [ ] **Owner:** `reviewer`
- **Target files:** the docs narrative and raw logs
- **Review Profiles:** `architecture`, `security`, `tests`, `documentation`
- **Review focus:** every observation is observed, not inferred; the deny proof rests on the
  two absences (marker, server log), not on the model's words; the decision follows the
  mapping; no code entered `shared/`, `scripts/`, or `tests/`.
- **Acceptance criteria:** CRITICAL/MAJOR resolved; the decision line is unambiguous.

## Verification

```bash
git status --short                                                       # this repository: only docs/ and .claude/ changes
uv run python scripts/validate_targets.py                                # docs link integrity
uv run python .claude/scripts/verify.py fast --format json               # during IMPLEMENT
uv run python .claude/scripts/verify.py phase --format json --persist    # before REVIEW
```

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [ ] Documentation updated (`docs/2026-09-19-openwiki-hook-mechanics-spike.md` is the deliverable)
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED` and repeats the decision line
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged (the docs narrative only) and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
- [ ] No hook script, adapter code, or generator wiring was written in this repository
- [ ] If the decision is RE-PLAN, Phase G is marked for re-planning in the session log and not started

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
