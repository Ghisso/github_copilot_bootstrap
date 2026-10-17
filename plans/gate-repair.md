---
name: gate-repair
type: big-plan
status: planning
originating_branch: dev
implementation_branch: gate-repair_implementation
started_at:
phases:
  - 2026-10-17_phase-A-review-gate-integrity
  - 2026-10-17_phase-B-context-mode-hook-sanitizer
  - 2026-10-17_phase-C-mcp-surface-parity
  - 2026-10-17_phase-D-guard-coverage
  - 2026-10-17_phase-E-gate-repair-knowledge-refresh
current_phase:
---

# Big Plan: Gate Repair

## Context

A read-only audit of `dev` at `050a1de` on 2026-10-17
(`.claude/explorations/2026-10-17_bootstrap-backlog-audit.md`) checked an
outside improvement backlog against the code. Its main finding: several
gates and guards do not do what the policy says they do. A PASS can
therefore rest on evidence that was never checked. That is the problem
this plan fixes. It adds no new evaluation system, agent, or provider.

Confirmed defects (audit §5 IDs):

- **D1** — Context Mode is unguarded in this repository. Root `.mcp.json`
  (Claude) and `.vscode/mcp.json` (Copilot) start `context-mode` directly,
  so all 11 tools are exposed. Also, the hook dispatcher forwards upstream
  `context-mode hook` output unchanged. A live run at the pinned `1.0.169`
  showed that this output names blocked tools at session start and before
  tool use. It also **denies WebFetch and plain `curl`** and points to the
  blocked `ctx_fetch_and_index` and `ctx_execute` instead, so agents here
  cannot fetch web pages. `docs/smoke-tests.md` says this lane "makes no
  safety decision".
- **D2** — A `WARN` review with open requests passes the commit gate as
  clean. `record_findings.py` records no gate result, and `verify.py` never
  checks one.
- **D3** — `.claude/settings.local.json` (Claude) and `.agents/hooks.json`
  (Antigravity) can disable or replace hooks, but `protect-files.py` does
  not protect them.
- **D4** — No test exercises the blocking path of the required Ponytail
  review.
- **D5** — `tracked_state_hash` is written but never compared. At commit,
  `tree_sha` already binds every tracked change. The real gap is tests or
  evaluators weakened before the receipt, with no gate requiring the
  `tests` review profile.
- **D6** — Claude subagents get no Context7 grant. Copilot agents do, and
  Antigravity agents inherit MCP servers.
- **D7** — `run-tests` and `add-dependency` ship a deprecation-check
  command that prints "Clean" when pytest fails.
- **D8** — Plan checks L1–L4 are documented as running at plan approval,
  but run only at commit.
- **D9** — `shared/schemas/agent.schema.json` is stale and nothing reads it.

## Goals

- Make every PASS depend on evidence a gate checks: the reviewer's own gate
  result, the review profiles the changed surfaces require, and a tested
  Ponytail requirement.
- Make the documented four-tool Context Mode surface true for every client
  configuration this repository ships or uses. Make sure its hooks never
  advise or force blocked tools.
- Protect each client's in-repository hook-bearing configuration the same
  way.
- Give the four clients the same capability wherever their native
  interfaces allow it. Work and verify in this order: Claude Code, Codex,
  GitHub Copilot, Antigravity. Record each remaining gap with its reason
  instead of claiming parity.

## Non-Goals and Constraints

- No model call in tests, hooks, or `verify.py`. No new agent role, provider,
  telemetry, or evaluation runner.
- No Context Mode, OpenWiki, or Ponytail version upgrade. Context Mode stays
  pinned at `1.0.169`.
- Context7 is not added to this repository's own root adapters. It is a
  generated-target capability for consumer projects; this authoring repo has
  no fast-moving third-party library code.
- The user-level Claude Code plugin `context-mode@context-mode` (enabled in
  `~/.claude/settings.json`) is outside repository control. The plan
  documents its effect and changes no user-level file.
- Historical findings reports and receipts are never re-judged. New rules
  apply to the current phase only.
- The fail-closed `protect-files` handling of interpreter commands, the
  `MEMORY.md` split, the `caveman-compress` backup defect, Ponytail 5, and
  stale statuses of earlier plans are out of scope.
- Native client runs are optional host evidence, run by the user in priority
  order. Offline tests are the required evidence.
- `settings.local.json` stays out of the runtime fingerprint. Claude Code
  itself writes permission approvals there, so fingerprinting it would make
  receipts stale on every approval. Path protection closes the agent-write
  route instead.

## Design Overview

### Parity matrix (target state)

| Fix | Claude Code | Codex | GitHub Copilot | Antigravity |
| --- | --- | --- | --- | --- |
| Review result and profile gate (A) | shared `verify.py` gate via `pretool-bash-guard.sh` | same | same, `enforce-commit-gate.sh` listed directly | same, via `antigravity-pretool.py` bridge; native deny unobserved |
| Context Mode hook output sanitized (B) | `claude-code` target | `codex` target | `vscode-copilot` target | no Context Mode hooks are wired; nothing to sanitize; no continuity (recorded gap) |
| Guarded Context Mode server (C) | root `.mcp.json` fixed; generated already guarded | root and generated already guarded | root `.vscode/mcp.json` fixed; generated already guarded | installed and generated guarded; MCP calls are denied by the bridge today (gap, see C) |
| Context7 for subagents (C) | add `mcp__context7` grant | inherit session servers (docs evidence in C) | `context7/*` already | `inheritMcp: true` already; bridge gap as above |
| Hook-config protection (D) | add `.claude/settings.local.json` | `.codex/*` already | `.github/hooks/*` already; workspace settings per docs evidence | add `.agents/hooks.json` |
| Plan checks at branch creation (D) | shared `enforce-branch-state.sh` | same | same | same via bridge |
| Shipped commands cannot hide failures (D) | shared skills | same | same | same |

The sidecar profiles ship no hooks or receipts. They receive only the
shared skill and guidance text changes.

### Priority rule

Each phase implements and tests the shared path first, then checks client
surfaces in this order: Claude Code, Codex, GitHub Copilot, Antigravity.
When a lower-priority client cannot get the same capability, the phase
records the gap in `docs/target-mapping.md` with its evidence. The phase
does not block on that client.

### Decisive assumptions

| Assumption | Status | Evidence or remaining limit |
| --- | --- | --- |
| A server-level `mcp__<server>` entry in a Claude subagent `tools:` list exposes that project server's tools | Settled | 2026-10-17 probe: the `reviewer` subagent (`tools: Read, Grep, Glob, mcp__semble, mcp__context-mode`) listed every `mcp__semble__*` and `mcp__context-mode__*` tool. Model-reported tool list; the server was configured at session start. |
| Upstream `context-mode hook` at `1.0.169` emits blocked-tool advice and denies WebFetch and plain `curl` for target `claude-code` | Settled | Live dispatcher runs on 2026-10-17 (audit §5 D1). |
| The same holds for targets `codex` and `vscode-copilot`, and session-start output after compaction carries restore content that can be separated from routing advice | Unobserved | Phase B step 1 captures it before any code. Stop rule in Phase B. |
| Codex custom agents inherit the session's `mcp_servers` | Unobserved | Phase C checks Codex documentation and source; no native run needed to plan. |
| Antigravity loads `.agents/mcp_config.json` and names MCP tool calls in a documented way | Unobserved, contrary evidence | `docs/runtime-checks.md:326-330`: `agy mcp list` reported no MCP servers. The bridge denies unknown tools. Phase C changes the bridge only if documentation gives the tool-name shape. Otherwise it records the gap. |
| A VS Code workspace setting can disable or relocate Copilot agent hooks | Unknown | Phase D checks VS Code documentation. It protects such a file only when a documented setting exists. |
| Claude Code's own permission approvals reach `settings.local.json` without a PreToolUse tool call | Expected, unobserved here | Same model as `settings.json`, which is already protected. For Claude, protect-files answers "ask", not "deny" (`docs/smoke-tests.md`). Phase D optional host check. |

## Requirement Map

IDs are prose references for this plan only.

| Requirement | Acceptance and existing contract | Owning phase | Evidence |
| --- | --- | --- | --- |
| GR-001 | `record_findings.py` records the reviewer's gate result and open requests. At phase completion the commit and push gates block unless the result is `PASS` and no request is open. Existing contract: `report_errors` (`shared/scripts/verify.py:2227`); reviewer `### Gate Result`. | `2026-10-17_phase-A-review-gate-integrity` | `tests/test_verify.py`, `tests/test_commit_closeout.py` |
| GR-002 | Gates require the review profiles the changed paths call for: a test surface requires `tests`; a `control-plane` or `generator` path, or a dependency file, requires `code`, `architecture`, `security`, `tests`, `ponytail`. The existing multi-file Ponytail rule stays. Uses `classify_path`. | `2026-10-17_phase-A-review-gate-integrity` | `tests/test_verify.py` |
| GR-003 | Tests prove the required-Ponytail path blocks a commit, in the verifier and through the installed commit hook. | `2026-10-17_phase-A-review-gate-integrity` | `tests/test_verify.py`, `tests/test_hook_gates.py` |
| GR-004 | A tracked change after closeout, documentation included, blocks the commit through `tree_sha`. `tracked_state_hash` is documented as informational. | `2026-10-17_phase-A-review-gate-integrity` | `tests/test_verify.py` |
| GR-005 | Every tracked root MCP adapter (Claude `.mcp.json`, Copilot `.vscode/mcp.json`, Codex `.codex/config.toml`) starts Context Mode through `context-mode-dispatch.sh server`. The validator fails on any direct start. | `2026-10-17_phase-C-mcp-surface-parity` | `tests/test_validate_targets.py` |
| GR-006 | Generated Claude agents with the `search` capability list `mcp__context7`. Codex and Antigravity MCP inheritance is documented with evidence. Each gap is recorded. | `2026-10-17_phase-C-mcp-surface-parity` | `tests/test_validate_targets.py`; `docs/target-mapping.md` |
| GR-007 | For targets `claude-code`, `codex`, `vscode-copilot`, the dispatcher never emits text naming a Context Mode tool outside the four-tool allowlist, never emits a `mcp__plugin_context-mode_` name, and never forwards an upstream `deny` or `ask` decision. Separable continuity content passes unchanged. | `2026-10-17_phase-B-context-mode-hook-sanitizer` | `tests/test_context_mode_dispatch.py` with recorded fixtures; real-binary check |
| GR-008 | Agent writes to `.claude/settings.local.json` and `.agents/hooks.json` get the same protect-files decision as other hook configs, for every client target id. | `2026-10-17_phase-D-guard-coverage` | `tests/test_hook_gates.py`, `tests/test_protect_files_scoping.py` |
| GR-009 | Creating an implementation branch runs the plan-frontmatter validator and denies on any error, L1–L4 included. | `2026-10-17_phase-D-guard-coverage` | `tests/test_branch_state.py` or `tests/test_hook_gates.py` |
| GR-010 | The deprecation steps in `run-tests` and `add-dependency` keep pytest's exit status. The validator rejects shipped fenced shell lines that run `pytest`, `mypy`, `ruff`, or `verify.py` and end in `\|\| true`, `\|\| :`, or `\|\| echo`, or pipe into another command without `pipefail`. | `2026-10-17_phase-D-guard-coverage` | `tests/test_validate_targets.py` |
| GR-011 | `shared/schemas/agent.schema.json` is removed. | `2026-10-17_phase-D-guard-coverage` | `validate_targets.py`; `rg` |
| GR-012 | Knowledge refresh and final stale-claims audit, including the parity table, the Ponytail "mandatory versus optional" wording, and the MEMORY entry on subagent MCP grants. | `2026-10-17_phase-E-gate-repair-knowledge-refresh` | OpenWiki completion; `## Stale-claims surfaces checked` |
| GR-013 | Boundaries hold: no model call in tests, hooks, or `verify.py`; no version upgrade; historical reports never re-judged. | all phases | Review and existing tests |

## Phases

- [ ] `2026-10-17_phase-A-review-gate-integrity` — gate result, required profiles, Ponytail blocking test, post-closeout drift test
- [ ] `2026-10-17_phase-B-context-mode-hook-sanitizer` — capture upstream hook output, then sanitize it for three targets
- [ ] `2026-10-17_phase-C-mcp-surface-parity` — guarded root MCP adapters, validator rule, Context7 grant, Codex and Antigravity MCP evidence
- [ ] `2026-10-17_phase-D-guard-coverage` — hook-config protection, branch-time plan checks, failure-hiding commands, stale schema
- [ ] `2026-10-17_phase-E-gate-repair-knowledge-refresh` — OpenWiki refresh and final audit

Phase A comes first, so every later phase is reviewed under the repaired
gate. B comes next because the unsanitized hook denies WebFetch and plain
`curl` here, and Phases C and D need documentation lookups. C then guards
the root servers against the same four-tool allowlist B enforces.

## Ownership and Required Skills

The main-thread orchestrator owns activation, the Phase B capture, the
self-install refresh, closeout, commits, and pushes. A coder owns code and
tests. A fresh reviewer reviews each phase. A documenter updates live docs
after review. Every coding step uses `shared/skills/ponytail/SKILL.md`
(full), `shared/skills/code-style/SKILL.md`, and
`shared/skills/testing-patterns/SKILL.md`. Steps that wrap or describe an
unobserved third-party behavior add `shared/skills/integration-gate-spike/SKILL.md`.
Every phase uses the `code`, `architecture`, `security`, `tests`, and
`ponytail` review profiles, plus `documentation` where docs change.

## Test Strategy

- **Critical cases:** a `WARN` or open-request review blocks; a missing
  required profile blocks; a missing required Ponytail review blocks through
  the installed hook; a blocked-tool name or upstream deny never leaves the
  dispatcher; agent writes to the two hook configs are protected for every
  target id; a plan without a Verification block cannot start a branch.
- **Negative controls:** a `PASS` review with no open request passes; a
  documentation-only diff needs no extra profile; reads of protected configs
  stay allowed; allowlisted `ctx_search` advice with the correct prefix
  passes; a valid plan starts a branch; the existing gates keep passing on
  this plan's own phases.
- **Real integration:** the Context Mode dispatcher runs against the real
  pinned binary in Phase B (machine-run). Native client sessions are optional
  host checks, in priority order.
- **Mocked boundaries:** git repositories in `tmp_path`, existing hook-test
  harnesses, recorded upstream hook fixtures.
- **Independent expected values:** expected decisions come from the policy
  tables (Task Lanes, `docs/smoke-tests.md`, `tool-routing.instructions.md`),
  not from the implementation.
- **No available verification:** native Antigravity PreToolUse enforcement
  and MCP tool naming; Copilot hook behavior inside VS Code. Docs must say so.

## Risks and Dependencies

- **Self-reported gate result.** `--gate-result` records what the
  orchestrator transcribes from the review. MEMORY `[LEARN:verification]`
  says a gate that reads a claim confirms only that the claim was written.
  Mitigation: the flag is required, and the recorder refuses `PASS` together
  with an open request. Still, this turns a silent drop into an explicit,
  audited statement; it does not prove the statement.
- **Continuity loss.** Sanitizing session-start output could remove
  Context Mode's restored session content. Phase B captures the real output
  first. It strips only separable advice blocks, and drops a whole field
  only as the last safety net, recording that as a limit.
- **Upstream drift.** A later Context Mode version can change the output
  shape. The fixtures are tied to `1.0.169`, and any version bump must
  refresh them (stated in docs).
- **Friction.** Path-based profile requirements make every control-plane
  change carry five profiles. In this repository that is already normal
  practice. In consumers, control-plane changes are rare. See the decision
  below.
- **Mid-phase consumer upgrades.** A findings report written before the
  upgrade has no gate result. It must be re-recorded for the current phase;
  docs state this.
- **Installed runtime lag.** `.claude/` here is an installed copy. Each
  phase that changes `shared/` regenerates and refreshes it with
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  before its own verification.
- **Session boundary.** A running Claude session does not reload
  `.mcp.json`. Phase C's native check needs a new session.

### Devil's advocate

| Concern | Risk | Alternative | Recommendation |
| --- | --- | --- | --- |
| Transcribed gate result can be wrong | MED | Parse the saved reviewer report for `### Gate Result` | ACCEPT: parsing model-written Markdown is brittle; record the limit |
| Sanitizer drops continuity | MED | Stop forwarding all upstream output | INVESTIGATE in Phase B step 1, with a stop rule |
| Path-based profiles add review cost | LOW | Require only `tests` and `security` | Decided by the user: recommended rule (see below) |
| Protecting `settings.local.json` blocks agent edits a user wants | LOW | Key-level protection | ACCEPT: matches `settings.json`; Claude asks rather than denies |
| Antigravity parity claims overreach | MED | Leave Antigravity untouched | CHANGE applied: change Antigravity only with documentation evidence, otherwise record the gap |

### Decisions recorded

- GR-002 profile strictness (user, 2026-10-17): the recommended rule.
  Control-plane and generator paths, and dependency files, require the five
  Task Lanes profiles. Test surfaces require `tests`. The narrower option
  (`tests` for tests, `security` for hooks only) was declined.
- The user-level `context-mode@context-mode` plugin (user, 2026-10-17): the
  user handles it. The plan changes no user-level file.

## Verification

```bash
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Completion Evidence

Phase A–D closeout logs map their GR IDs to tests. Phase E's log maps
GR-001 to GR-013 and records the audit under `## Stale-claims surfaces
checked`. Each completed phase gets one commit and one normal push attempt.
PR creation and merge stay the user's decision.
