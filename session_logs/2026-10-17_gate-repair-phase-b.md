# Session: Gate repair — Phase B, Context Mode hook sanitizer

**Date:** 2026-10-17
**Plan:** .claude/plans/2026-10-17_phase-B-context-mode-hook-sanitizer.md
**Parent plan:** .claude/plans/gate-repair.md
**Status:** COMPLETED

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
- [x] IMPLEMENT/VERIFY/REVIEW — three review rounds (same reviewer for
  confirmations); final Gate Result `PASS` with no findings.
- [x] CLOSEOUT: final AI state, checkpoint, staged index, findings, phase
  receipt, closeout dry run, checkpoint, closeout receipt.
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

- **08:00** - Review round 1: Gate Result `PASS`, no CRITICAL or MAJOR, five
  MINOR (real-binary test could pass vacuously; unclosed/nested/cased tag
  limit undocumented and one smoke-tests sentence inaccurate; re-capture
  rule had no committed procedure or pin tie; `hookEventName` unchecked; no
  test for advice forwarded after a nonzero exit). Reviewer probed leak
  shapes (arrays, `__proto__`, non-string fields, BOM, split names) and found
  none; fixtures hold no private data (about 56 KB of content). All five
  sent back for fixing: coder (tests, capture script committed as
  `tests/fixtures/context_mode_hook/capture.py`, pin-tie test, event-name
  check), documenter (limits, wording, procedure pointer).

- **08:30** - All five MINOR fixes landed. The capture script is committed
  as `tests/fixtures/context_mode_hook/capture.py`; it now records raw
  upstream output directly (the dispatcher filters), with a private
  `TMPDIR` (upstream's once-per-session tip files in the shared temporary
  directory had suppressed tips on a re-run). A scratch re-run reproduced
  all 32 fixtures byte for byte. Orchestrator caught one doc inaccuracy
  (step 1 said the script runs through the dispatcher); documenter fixed it.
  Self-install, `check_runtime.py` PASS, `validate_targets.py` PASS,
  `verify.py phase` PASS (pytest 2460 passed, 1 skipped), real test PASS.
  Signal forwarding on timeout stays out of scope (documented limit).
  Same reviewer asked to confirm, with the full fix evidence.

- **08:45** - Review round 2: all five fixes confirmed; one new MINOR from my
  own corrective wording (the capture script reads the pin from `shared/`,
  not from the temporary copy). Applied the reviewer's exact sentence.
  Round 3 (same reviewer, scoped to that sentence): Gate Result `PASS`,
  findings `[]`.

### Phase-boundary summary

- **Objective and change:** the Context Mode hook lane now forwards only
  filtered advice text for `claude-code`, `openai-codex`, `github-copilot`;
  upstream decisions and input rewrites never reach the client. In this
  repository the installed hook no longer denies WebFetch or `curl`.
- **Deviations from the plan:** the capture script is committed as
  `tests/fixtures/context_mode_hook/capture.py` and records raw upstream
  output directly (review finding); `hookEventName` must be a plain word;
  `<context_guidance>` added to the stripped advice blocks.
- **Checks:** see `## Verification` below.
- **Open findings:** none. Accepted, documented limits: fail-closed drop of
  a restored block naming a non-allowlisted `ctx_` tool; unclosed, nested,
  or cased advice tags rely on the name safety net; no signal forwarding on
  client timeout; Codex and Copilot restore shapes unobserved.
- **Next operation:** Phase C, MCP surface parity.

### Requirement mapping

- GR-007: `test_recorded_upstream_output_is_reduced_to_advice_only` (32
  recorded fixtures through the real dispatcher),
  `test_decisions_and_rewrites_are_dropped_but_advice_text_survives`,
  `test_nonzero_upstream_exit_is_logged_once_and_the_hook_exits_zero`,
  `test_nonzero_upstream_exit_still_forwards_the_filtered_advice`,
  `test_the_client_hook_payload_reaches_upstream_on_stdin`,
  `test_fixture_directory_is_named_after_the_pinned_version`, the
  `--hook-output` unit tests in `tests/test_context_mode_mcp_filter.py`
  (including the plain-word event name), and the opt-in
  `test_real_upstream_hook_output_is_advisory_only`.
- GR-013: no model call; no version change; the real-binary check refuses
  an `npx` download.

## [LEARN] Entries

- [LEARN:security] Upstream `context-mode hook` output is not advisory: at
  1.0.169 it denies fetches and returns `allow` with `updatedInput` that
  rewrites commands and subagent prompts. Forwarding must allowlist fields,
  not strip known decisions.
- [LEARN:tooling] Upstream Context Mode tip throttling uses files in the OS
  temporary directory; captures and tests that reuse a session id need a
  private `TMPDIR`.

## Verification

- PASS        0.3s  uv run python scripts/generate_targets.py --all
- PASS       44.5s  uv run python scripts/validate_targets.py
- PASS        8.5s  uv run pytest tests/test_context_mode_dispatch.py tests/test_context_mode_mcp_filter.py tests/test_lifecycle_hooks.py -q
- PASS        0.8s  CONTEXT_MODE_REAL=1 uv run pytest tests/test_context_mode_dispatch.py -q -k real_upstream
- PASS        0.8s  uv run python scripts/check_runtime.py
- PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
- PASS        0.2s  uv run python .claude/scripts/verify.py fast --format json

Phase receipt: `verify.py phase --format json --persist` PASS. Findings
report: `.claude/quality_reports/findings-2026-10-17_phase-B-context-mode-hook-sanitizer.json`
(0 findings, `gate_result: PASS`, six profiles).

- optional 1: NOT RUN — a new native Claude Code session with the user-level `context-mode@context-mode` plugin turned off is a user-run host check; instead the installed hook in this repository was run directly with `claude-code` WebFetch and Bash `curl` PreToolUse payloads and produced no output with exit 0 (before the change: deny).
- optional 2: NOT RUN — a native Codex fetch is a user-run host check; the `openai-codex` recorded fixtures cover the hook output offline.
- optional 3: NOT RUN — a native GitHub Copilot fetch in VS Code is a user-run host check; the `github-copilot` recorded fixtures cover the hook output offline.

## Open Questions / Next Steps

- Next: Phase C, `2026-10-17_phase-C-mcp-surface-parity`.
