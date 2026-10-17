# Session: Gate repair — Phase B, Context Mode hook sanitizer

**Date:** 2026-10-17
**Plan:** .claude/plans/2026-10-17_phase-B-context-mode-hook-sanitizer.md
**Parent plan:** .claude/plans/gate-repair.md
**Status:** IN-PROGRESS

## Goal

Make the Context Mode hook lane advisory only (GR-007): forward only
allowlisted advice text, never an upstream decision, input rewrite, or
blocked-tool name, for client ids `claude-code`, `openai-codex`,
`github-copilot`.

## Task Tracking

- [x] PRE-FLIGHT: Phase A committed (`5eaa18e`) and pushed; post-commit hook
  activated Phase B. No material impact from Phase A on this phase.
- [x] PLAN WHEN NEEDED: approved plan is implementation-ready; no planner.
- [x] Step 1 capture (orchestrator): done; stop rule not triggered.
- [ ] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT — repeat until verification and review pass.
- [ ] COMMIT
- [ ] PUSH

## Work Log

- **06:55** - Step 1 capture. Script:
  scratchpad `capture_cm_hooks.py` (not committed). It copied
  `context-mode-dispatch.sh` and `context-mode-mcp-filter.mjs` into a
  throwaway Git repository, set a throwaway `HOME`, `CLAUDE_CONFIG_DIR`, and
  `CODEX_HOME`, and confirmed `--self-check` reported
  `launcher=context-mode` and `version-contract=pinned-direct-binary` (no
  `npx`). Fixtures written to
  `tests/fixtures/context_mode_hook/1.0.169/<client-id>/<event>-<case>.json`
  with temporary paths replaced by `<TMP>`. Every run exited 0 with empty
  stderr.

### Capture table (pinned 1.0.169)

| Client id | Event / case | Output fields | Decision or rewrite | Tool names in output |
| --- | --- | --- | --- | --- |
| claude-code | sessionstart startup | `hookSpecificOutput.{hookEventName, additionalContext}` (4.6 KB, one `<context_window_protection>` block) | none | plugin-prefixed `ctx_batch_execute`, `ctx_execute`, `ctx_execute_file`, `ctx_fetch_and_index`, `ctx_search` |
| claude-code | pretooluse Bash `ls`, posttooluse | empty | none | none |
| claude-code | pretooluse Bash `curl` | `permissionDecision: deny` + reason | **deny** | plugin-prefixed blocked tools |
| claude-code | pretooluse Read, Grep | `additionalContext` tip | none | plugin-prefixed `ctx_execute_file` / `ctx_execute` |
| claude-code | pretooluse WebFetch | `permissionDecision: deny` + reason | **deny** | plugin-prefixed blocked tools |
| claude-code | pretooluse Agent | `updatedInput` (4.8 KB) | **rewrites the subagent prompt** with routing advice | plugin-prefixed blocked tools |
| claude-code | pretooluse `mcp__context-mode__ctx_execute` | `updatedInput` | **rewrites the tool input** | none |
| claude-code | precompact | `{}` | none | none |
| claude-code | sessionstart compact | `<context_window_protection>` + `<session_knowledge>` | none | `<session_knowledge>` holds `<session_guide>` (restored data) and `<session_search>` (advice naming plugin-prefixed `ctx_search`) |
| openai-codex | sessionstart startup and compact | one `<context_window_protection>` block (4.1 KB; no restore block in this run) | none | unprefixed blocked tools |
| openai-codex | pretooluse Bash `ls`, `ctx_execute` | `hookSpecificOutput.hookEventName` only | none | none |
| openai-codex | pretooluse Bash `curl` | `permissionDecision: allow` + `updatedInput` | **allow + rewrites the command** | blocked tools |
| openai-codex | pretooluse `read` | `additionalContext` tip | none | `ctx_execute_file` |
| openai-codex | pretooluse `web_fetch` | `permissionDecision: deny` + reason | **deny** | blocked tools |
| openai-codex | posttooluse | `additionalContext: ""` | none | none |
| github-copilot | sessionstart startup and compact | one `<context_window_protection>` block (4.2 KB; no restore block in this run) | none | unprefixed blocked tools |
| github-copilot | pretooluse `run_in_terminal ls`, `runSubagent`, MCP `ctx_execute`, posttooluse, precompact | empty | none | none |
| github-copilot | pretooluse `run_in_terminal curl` | `permissionDecision: allow` + reason + `updatedInput` | **allow + rewrites the command** | blocked tools |
| github-copilot | pretooluse `read_file`, `grep_search` | `additionalContext` tip | none | `ctx_execute_file` / `ctx_execute` |
| github-copilot | pretooluse `fetch` | top-level `permissionDecision: deny` + reason (not under `hookSpecificOutput`) | **deny** | blocked tools |
| github-copilot | pretooluse `agent` | `permissionDecision: allow` + `updatedInput` | **allow + rewrites the subagent prompt** | blocked tools |

**Answer to the step 1 question:** yes. Restore content is separable by
block: `<context_window_protection>` and `<session_search>` are advice;
`<session_guide>` inside `<session_knowledge>` is restored data. Stop rule
not triggered. Limits: only `claude-code` produced restore content in this
synthetic run; Codex and Copilot compact output equalled startup output, so
their restore shape is unobserved. One pinned version, synthetic payloads,
no native client.

- **07:05** - Delegated step 2 to a fresh coder. Added `<context_guidance>`
  (the observed pretooluse tip wrapper) to the advice blocks to strip, next
  to `<context_window_protection>` and `<session_search>`; the safety net
  still drops any field left with a blocked or plugin-prefixed name.

- **07:40** - Coder finished step 2: `run_upstream_hook` in the dispatcher,
  `--hook-output` mode in the filter, 32-fixture dispatcher test, filter unit
  tests, opt-in real-binary test. Negative controls failed as expected for
  every rule. Accepted limits (documented): fail-closed drop of a restored
  block that mentions a non-allowlisted `ctx_` name; unclosed advice tags
  rely on the safety net; no `exec`, so a timed-out dispatcher can leave the
  upstream child running.
- **07:45** - Self-install; `check_runtime.py` PASS. Live check: the
  installed hook now forwards nothing for WebFetch and Bash curl (before:
  deny). `verify.py phase` PASS (pytest 2452 passed, 1 skipped);
  `CONTEXT_MODE_REAL=1 ... -k real_upstream` 1 passed.
- **07:50** - Documenter: `docs/smoke-tests.md`, `docs/runtime-checks.md`,
  `docs/target-mapping.md` (new parity section). `validate_targets.py` PASS.
  `shared/policies/tool-routing.instructions.md:28` is silent about the
  filter (not contradicted); deferred to Phase E's stale-claims audit.
  Fresh reviewer started with the full evidence packet, including negative
  controls (lesson from Phase A round 2).

## [LEARN] Entries

## Verification

## Open Questions / Next Steps

- Delegate step 2 (filter) to the coder with this table.
