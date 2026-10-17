---
name: gate-repair
type: big-plan
status: in-progress
originating_branch: dev
implementation_branch: gate-repair_implementation
started_at: 2026-10-17T04:58:19Z
phases:
  - 2026-10-17_phase-A-review-gate-integrity
  - 2026-10-17_phase-B-context-mode-hook-sanitizer
  - 2026-10-17_phase-C-mcp-surface-parity
  - 2026-10-17_phase-D-guard-coverage
  - 2026-10-17_phase-E-gate-repair-knowledge-refresh
current_phase: 2026-10-17_phase-B-context-mode-hook-sanitizer
---

# Big Plan: Gate Repair

## Context

A read-only audit of `dev` at `050a1de` on 2026-10-17
(`.claude/explorations/2026-10-17_bootstrap-backlog-audit.md`) checked an
outside improvement backlog against the code. Its main finding: several
gates and guards do not do what the policy says they do. A PASS can
therefore rest on evidence that was never checked. That is the problem
this plan fixes. It adds no new evaluation system, agent, or provider.

An independent devil's advocate review (Opus, extra-high effort, read-only,
2026-10-17) re-checked this plan against the code. Its confirmed findings
are folded in below; see "Devil's advocate".

Confirmed defects (audit §5 IDs, corrected by the review):

- **D1** — Context Mode is unguarded in this repository. Root `.mcp.json`
  (Claude) and `.vscode/mcp.json` (Copilot) start `context-mode` directly,
  so all 11 tools are exposed. The hook dispatcher `exec`s upstream
  `context-mode hook` and forwards its output unchanged. At the pinned
  `1.0.169` that output names blocked tools, **denies WebFetch and plain
  `curl`** in favour of blocked tools, and can return `allow` with a
  rewritten tool input (`updatedInput`, for example a changed subagent
  prompt). `docs/smoke-tests.md` says this lane "makes no safety decision or
  mutation".
- **D2** — A `WARN` review with open requests passes the commit gate as
  clean. `record_findings.py` records no gate result, and `verify.py` never
  checks one.
- **D3** — Hook- and server-launching configs are not all protected.
  `protect-files.py` covers `.claude/settings.json`, `.codex/config.toml`,
  `.codex/hooks.json`, and the hook directories, but not
  `.claude/settings.local.json`, `.agents/hooks.json`, `.mcp.json`,
  `.vscode/mcp.json`, or `.agents/mcp_config.json`. Also, the nested ai-state
  repository here still tracks `settings.local.json`, despite its
  `.gitignore`, so state sync can deliver it.
- **D4** — Corrected: the Ponytail blocking path *is* tested through the
  installed commit-msg and pre-push hooks (`scripts/validate_targets.py:6098-6112`,
  `:6580-6600`). Missing: a unit test in `tests/test_verify.py`, and hook
  cases for the new GR-001 and GR-002 rules.
- **D5** — `tracked_state_hash` is written but never compared. At commit,
  `tree_sha` from `git write-tree` binds every staged change. The real gap is
  tests or evaluators weakened before the receipt, with no gate requiring
  the `tests` review profile.
- **D6** — Claude subagents get no Context7 grant. Copilot agents do, and
  Antigravity agents declare `inheritMcp: true`.
- **D7** — `run-tests` and `add-dependency` ship a deprecation-check
  command that prints "Clean" when pytest fails.
- **D8** — Plan checks L1–L4 are documented as running at plan approval
  (`shared/policies/workflow.instructions.md:395-398`) but run only at
  commit.
- **D9** — `shared/schemas/agent.schema.json` is stale and nothing reads it.

## Goals

- Make every PASS depend on evidence a gate checks: the reviewer's own gate
  result, the review profiles the changed surfaces require, and the existing
  Ponytail requirement.
- Make the documented four-tool Context Mode surface true for every client
  configuration this repository ships or uses. Make its hook lane advisory
  only: no decision, no input rewrite, no blocked-tool advice.
- Protect each client's in-repository hook- and server-launching
  configuration the same way.
- Give the four clients the same capability wherever their native
  interfaces allow it. Work and verify in this order: Claude Code, Codex,
  GitHub Copilot, Antigravity. Record each remaining gap with its reason
  instead of claiming parity.

## Non-Goals and Constraints

- No model call in tests, hooks, or `verify.py`. No new agent role, provider,
  telemetry, or evaluation runner.
- No Context Mode, OpenWiki, or Ponytail version upgrade. Context Mode stays
  pinned at `1.0.169`.
- Context7 is not added to the tracked root adapters (`.mcp.json`,
  `.vscode/mcp.json`, `.codex/config.toml`). The installed, untracked
  `.agents/mcp_config.json` already carries it from the generated target.
  This authoring repo has no fast-moving third-party library code.
- The user-level Claude Code plugin `context-mode@context-mode` is the
  user's to manage (decision recorded below). The plan changes no
  user-level file. While that plugin is on, its own hooks can still deny
  WebFetch and `curl` in Claude sessions; documentation lookups use the
  fallback in Phases C and D.
- Historical findings reports and receipts are never re-judged (see the
  push-gate rule in GR-001).
- Agent definition files (`.claude/agents/`, `.codex/agents/*.toml`,
  `.github/agents/`, `.agents/agents/`) stay unprotected in all four
  clients. Protecting them, including Codex `sandbox_mode` in agent TOML,
  is a follow-up recorded in Phase E.
- The fail-closed `protect-files` handling of interpreter commands, the
  `MEMORY.md` split, the `caveman-compress` backup defect, Ponytail 5,
  wiring upstream's `antigravity-cli` hooks, and stale statuses of earlier
  plans are out of scope.
- Native client runs are optional host evidence, run by the user in priority
  order. Offline tests are the required evidence.
- `settings.local.json` stays out of the runtime fingerprint. Claude Code
  itself writes permission approvals there, so fingerprinting it would make
  receipts stale on every approval. Path protection and untracking close the
  agent-write and sync routes instead.

## Design Overview

### Parity matrix (target state)

| Fix | Claude Code | Codex | GitHub Copilot | Antigravity |
| --- | --- | --- | --- | --- |
| Review result and profile gate (A) | shared `verify.py` gate via `pretool-bash-guard.sh` and installed Git hooks | same | same; `enforce-commit-gate.sh` listed directly | same via `antigravity-pretool.py`; native deny unobserved |
| Hook lane advisory only (B) | `claude-code` client id | `openai-codex` | `github-copilot` | upstream ships `antigravity-cli` hooks, but the bootstrap does not wire them: nothing to sanitize, no continuity (recorded gap) |
| Guarded Context Mode server (C) | root `.mcp.json` fixed; generated already guarded | root and generated already guarded | root `.vscode/mcp.json` fixed; generated already guarded | installed and generated guarded; the bridge denies MCP calls today (gap, see C) |
| Context7 for subagents (C) | add `mcp__context7` grant | inherit session servers (evidence in C) | `context7/*` already | `inheritMcp: true`; bridge gap as above |
| Hook- and server-config protection (D) | add `settings.local.json`, `.mcp.json` (ask) | `config.toml`, `hooks.json`, `hooks/` already (deny) | add `.vscode/mcp.json` (ask); workspace settings per docs evidence | add `.agents/hooks.json`, `.agents/mcp_config.json` (deny, decided in `protect-files.py` itself) |
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

### Documentation lookups

Phases C and D read official client documentation. Use WebFetch or
Context7 first. When a hook denies them (for example the user-level plugin),
use `gh api` on the official documentation repositories (`openai/codex`,
`microsoft/vscode-docs`) or WebSearch. When none of these reach an answer,
record the question as unverified, change no code for it, and continue.

### Decisive assumptions

| Assumption | Status | Evidence or remaining limit |
| --- | --- | --- |
| A server-level `mcp__<server>` entry in a Claude subagent `tools:` list exposes that project server's tools | Settled | 2026-10-17 probe: the `reviewer` subagent listed every `mcp__semble__*` and `mcp__context-mode__*` tool. Model-reported tool list; the server was configured at session start. |
| Upstream `context-mode hook` at `1.0.169` emits blocked-tool advice, denies WebFetch and `curl`, and can return `allow` with `updatedInput` | Settled | Live dispatcher runs on 2026-10-17; upstream `hooks/core/formatters.mjs:23-77`. |
| The same shapes hold for Codex and Copilot, and session-start restore content can be separated from routing advice | Unobserved | Phase B step 1 captures it before any code, with a stop rule. |
| Push gates re-check the last completed phase's findings with the strict completion rule | Settled | `_lib-frontmatter.sh:1541` (`ancestor`), `:1756` (`certified`). Drives the schema-version rule in GR-001. |
| Codex custom agents inherit the session's `mcp_servers` | Unobserved | Phase C step 3, from documentation. |
| Antigravity loads `.agents/mcp_config.json` and names MCP tool calls in a documented way | Unobserved, contrary evidence | `docs/runtime-checks.md:326-330`: `agy mcp list` reported none. Phase C step 4 changes code only with documentation. |
| VS Code reads agent hooks from other files (for example `.claude/settings*.json`), or a workspace setting can relocate or turn them off | Unknown | Phase D step 2, from documentation. |
| Claude Code's own permission approvals reach `settings.local.json` without a PreToolUse tool call | Expected, unobserved here | For Claude, protect-files answers "ask", not "deny". Phase D optional host check. |

## Requirement Map

IDs are prose references for this plan only.

| Requirement | Acceptance and existing contract | Owning phase | Evidence |
| --- | --- | --- | --- |
| GR-001 | `record_findings.py` writes `schema_version: 2`, the reviewer's `gate_result`, and `open_requests`. The commit gate (`exact` relation, phase completion) blocks unless `gate_result == "PASS"` and no request is open; a report without the field is rejected there. Push gates (`ancestor`, `certified`) apply the same rule only to reports with `schema_version >= 2`, so reports written before the upgrade stay valid. The reviewer prompt maps results: `FAIL` when a CRITICAL or MAJOR survives, `WARN` when a request is open, otherwise `PASS` (surviving MINORs with dispositions allow `PASS`). Contract: `report_errors` (`shared/scripts/verify.py:2227`). | `2026-10-17_phase-A-review-gate-integrity` | `tests/test_verify.py`, `tests/test_commit_closeout.py`, `scripts/validate_targets.py` smoke |
| GR-002 | Gates require the profiles the branch's changed paths call for, computed from the receipt's `changed_paths` in `gate_receipt_errors`. Test surfaces (checked first: `tests/` prefix, `test_*.py`, `*_test.py`, `conftest.py`) require `tests`. `control-plane` and `generator` paths and dependency files (`DEPENDENCY_FILES`, `pyproject.toml`, `requirements*.txt`, `requirements*.in`) require `code`, `architecture`, `security`, `tests`, `ponytail`. `.vscode/mcp.json` joins `CONTROL_PLANE_FILES`. The diff is cumulative from the merge-base, so later phases of a branch keep the earlier phases' requirements. The multi-file Ponytail rule stays. Same schema-version rule as GR-001: always at the commit gate, at push gates only for `schema_version >= 2` reports. | `2026-10-17_phase-A-review-gate-integrity` | `tests/test_verify.py`; `scripts/validate_targets.py` smoke |
| GR-003 | A `tests/test_verify.py` unit test covers the required-Ponytail error. The installed-hook smoke in `scripts/validate_targets.py` adds a `WARN` report denied by the commit-msg hook and a test-file diff missing `tests` denied. | `2026-10-17_phase-A-review-gate-integrity` | same |
| GR-004 | A staged documentation change after closeout blocks the commit with "closeout receipt final tracked state is stale". `tracked_state_hash` is documented as informational. | `2026-10-17_phase-A-review-gate-integrity` | `tests/test_verify.py` |
| GR-005 | Every tracked root MCP adapter (Claude `.mcp.json`, Copilot `.vscode/mcp.json`, Codex `.codex/config.toml`) starts Context Mode through `context-mode-dispatch.sh server`. The validator fails on any direct start. | `2026-10-17_phase-C-mcp-surface-parity` | `tests/test_validate_targets.py` |
| GR-006 | Generated Claude agents with the `search` capability list `mcp__context7`. Codex and Antigravity MCP reachability is documented with evidence. Each gap is recorded. | `2026-10-17_phase-C-mcp-surface-parity` | `tests/test_validate_targets.py`; `docs/target-mapping.md` |
| GR-007 | For client ids `claude-code`, `openai-codex`, `github-copilot`, hook modes forward only an allowlist of output fields: the event name and the advice text field(s) step B1 identifies, each text-filtered. Everything else is dropped: any decision value, `updatedInput`, `tool_input`, `continue`, `stopReason`, `systemMessage`. No forwarded text names a Context Mode tool outside the four-tool allowlist or a `mcp__plugin_context-mode_` name. Hook modes always exit 0. | `2026-10-17_phase-B-context-mode-hook-sanitizer` | `tests/test_context_mode_dispatch.py` with recorded fixtures; real-binary check |
| GR-008 | Agent writes to `.claude/settings.local.json`, `.agents/hooks.json`, `.mcp.json`, `.vscode/mcp.json`, and `.agents/mcp_config.json` get the hook-config decision (Claude and Copilot ask; Codex and Antigravity deny). The nested ai-state repository never tracks `settings.local.json`. | `2026-10-17_phase-D-guard-coverage` | `tests/test_hook_gates.py`, `tests/test_protect_files_scoping.py`, state-sync test |
| GR-009 | Creating an implementation branch runs the plan-frontmatter validator on the big plan and its listed phase files, and denies on any error, L1–L4 included. | `2026-10-17_phase-D-guard-coverage` | `tests/test_branch_state.py` or `tests/test_hook_gates.py` |
| GR-010 | The deprecation steps in `run-tests` and `add-dependency` keep pytest's exit status. The validator rejects shipped fenced shell lines that run `pytest`, `mypy`, `ruff`, or `verify.py` and end in `\|\| true`, `\|\| :`, or `\|\| echo`. | `2026-10-17_phase-D-guard-coverage` | `tests/test_validate_targets.py` |
| GR-011 | `shared/schemas/agent.schema.json` is removed. | `2026-10-17_phase-D-guard-coverage` | `validate_targets.py`; `rg` |
| GR-012 | Knowledge refresh and final stale-claims audit, including the parity table, the Ponytail "mandatory versus optional" wording, the MEMORY entry on subagent MCP grants, and the recorded follow-ups. | `2026-10-17_phase-E-gate-repair-knowledge-refresh` | OpenWiki completion; `## Stale-claims surfaces checked` |
| GR-013 | Boundaries hold: no model call in tests, hooks, or `verify.py`; no version upgrade; historical reports never re-judged; no network download in required checks. | all phases | Review and existing tests |

## Phases

- [x] `2026-10-17_phase-A-review-gate-integrity` — complete: gate result with schema version, required profiles, unit and installed-hook tests, post-closeout drift test. See `.claude/session_logs/2026-10-17_gate-repair-phase-a.md`.
- [ ] `2026-10-17_phase-B-context-mode-hook-sanitizer` — capture upstream hook output in isolation, then forward only allowlisted advice fields
- [ ] `2026-10-17_phase-C-mcp-surface-parity` — guarded root MCP adapters, validator rule, Context7 grant, Codex and Antigravity MCP evidence
- [ ] `2026-10-17_phase-D-guard-coverage` — hook- and server-config protection, untracked local settings, branch-time plan checks, failure-hiding commands, stale schema
- [ ] `2026-10-17_phase-E-gate-repair-knowledge-refresh` — OpenWiki refresh and final audit

Phase A comes first, so every later phase is reviewed under the repaired
gate. B comes next because the unsanitized hook denies WebFetch and plain
`curl` here, and Phases C and D need documentation lookups. C changes the
root MCP adapters before D protects them.

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

- **Critical cases:** a `WARN`, `FAIL`, or open-request report blocks the
  commit gate; a missing required profile blocks; any upstream decision,
  input rewrite, or blocked-tool name never leaves the dispatcher; agent
  writes to each newly protected config are protected for every client id;
  a plan without a Verification block cannot start a branch.
- **Negative controls:** a `PASS` report with no open request passes; a
  schema-1 report from before the upgrade still passes the push gates; a
  documentation-only first phase needs no extra profile; reads of protected
  configs stay allowed; allowlisted `ctx_search` advice with the correct
  prefix passes; a valid plan starts a branch while an unrelated draft plan
  elsewhere does not block it; the existing gates keep passing on this
  plan's own phases.
- **Real integration:** the Context Mode dispatcher runs against the real
  pinned binary in Phase B (machine-run, isolated `HOME`, no npx fallback).
  The installed Git hooks run in the `validate_targets.py` smoke. Native
  client sessions are optional host checks, in priority order.
- **Mocked boundaries:** Git repositories in temporary directories, existing
  hook-test harnesses, recorded upstream hook fixtures.
- **Independent expected values:** expected decisions come from the policy
  tables (Task Lanes, `docs/smoke-tests.md`, `tool-routing.instructions.md`)
  and the profile table in GR-002, not from the implementation.
- **No available verification:** native Antigravity PreToolUse enforcement
  and MCP tool naming; Copilot hook behavior inside VS Code. Docs must say so.

## Risks and Dependencies

- **Self-reported gate result.** `--gate-result` records what the
  orchestrator transcribes from the review. MEMORY `[LEARN:verification]`
  says a gate that reads a claim confirms only that the claim was written.
  Mitigation: the flag is required, and the recorder refuses `PASS` together
  with an open request. This turns a silent drop into an explicit, audited
  statement; it does not prove the statement.
- **Continuity loss.** Forwarding only advice fields could drop Context
  Mode's restored session content. Phase B captures the real output first,
  with a stop rule.
- **Upstream drift.** A later Context Mode version can change the output
  shape. The fixtures are tied to `1.0.169`; any version bump must refresh
  them (stated in docs).
- **Network in required checks.** The dispatcher falls back to `npx` when the
  pinned binary is missing. The real-binary check first asserts the direct
  pinned binary, so it fails instead of downloading.
- **Private data in fixtures.** Upstream session start reads user-level
  files such as `~/.claude/CLAUDE.md`. Capture and tests use a temporary
  `HOME`, `CLAUDE_CONFIG_DIR`, and `CODEX_HOME`.
- **Friction.** Path-based profile requirements make every control-plane
  change carry five profiles, and the cumulative diff keeps them for later
  phases of the same branch. In this repository that is already normal
  practice.
- **Consumers mid-plan.** A findings report written before the upgrade has
  no `gate_result`. For the current phase it must be re-recorded before
  closeout. Completed phases stay valid at push through the schema-version
  rule.
- **Installed runtime lag.** `.claude/` here is an installed copy. Each
  phase that changes `shared/` regenerates and refreshes it with
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  before its own verification.
- **Session boundary.** A running Claude session does not reload
  `.mcp.json`. Phase C's native check needs a new session.

### Devil's advocate

Independent review on 2026-10-17 (separate read-only subagent, Opus,
extra-high effort, devils-advocate skill). Outcome:

| Concern | Risk | Recommendation | Applied |
| --- | --- | --- | --- |
| Sanitizer stripped only deny/ask; upstream also returns `allow` + `updatedInput` | HIGH | CHANGE | GR-007 is now a field allowlist |
| Push gates re-judge completed phases; old reports lack `gate_result` | HIGH | CHANGE | GR-001 schema-version rule (option b) |
| Phase A omitted `scripts/validate_targets.py`, which runs the recorder | MED | CHANGE | Added to Phase A |
| Ponytail blocking path already tested via installed hooks | MED | CHANGE | D4 and GR-003 corrected |
| GR-002 classification gaps (`tests/fixtures/*.json`, `requirements.md`, `pyproject.toml`, `.vscode/mcp.json`) | MED | CHANGE | GR-002 rules |
| Profile paths should come from the receipt, not new discovery | MED | CHANGE | GR-002 uses `changed_paths` |
| No PASS/WARN/FAIL mapping for surviving MINORs | MED | CHANGE | GR-001 mapping in the reviewer prompt |
| Capture could leak private files and download via npx | MED | CHANGE | Phase B isolation and launcher assertion |
| Capture missed `updatedInput` payloads, exit codes, stderr | MED | CHANGE | Phase B step 1 |
| Documentation lookups may still be blocked by the user-level plugin | MED | CHANGE | Lookup fallback above |
| MCP configs launch commands but are unprotected | MED | CHANGE | GR-008 |
| Nested ai-state tracks `settings.local.json` | MED | CHANGE | GR-008 |
| Branch-time validation of every plan file blocks on unrelated drafts | LOW-MED | CHANGE | GR-009 explicit paths |
| Pipefail lint is more than needed | LOW | CHANGE | GR-010 narrowed |
| Antigravity row read as a native limit | LOW | CHANGE | Parity matrix says "not wired" |
| GR-002 enforces part of Task Lanes only (multi-file) | LOW | ACCEPT | Known limit; user decision stands |
| Transcribed gate result can be wrong | MED | ACCEPT | Risk stated above |

### Decisions recorded

- GR-002 profile strictness (user, 2026-10-17): the recommended rule.
  The narrower option (`tests` for tests, `security` for hooks only) was
  declined.
- The user-level `context-mode@context-mode` plugin (user, 2026-10-17): the
  user handles it.
- Push-gate treatment of findings reports written before the upgrade
  (user, 2026-10-17): option (b), schema-marked reports. Option (a), the
  commit gate only, would lose the check on completion commits made with
  `--no-verify`. Option (c), "push before upgrading", would strand
  consumers mid-plan.
- Plan approved by the user on 2026-10-17 with these decisions.

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
