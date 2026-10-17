---
name: 2026-10-17_phase-B-context-mode-hook-sanitizer
type: small-plan
parent_plan: gate-repair
phase_index: 2
status: complete
closeout_session_log: .claude/session_logs/2026-10-17_gate-repair-phase-b.md
---

# Small Plan: Context Mode Hook Sanitizer

## Scope

Make the Context Mode hook lane advisory only, as `docs/smoke-tests.md`
already says it is: "no safety decision or mutation" (GR-007). Today the
dispatcher `exec`s upstream `context-mode hook`, so upstream output and exit
status reach the client unchanged. At the pinned `1.0.169` that output names
blocked tools, denies WebFetch and plain `curl`, and can return `allow` with
a rewritten tool input (`updatedInput`). This phase first records what
upstream emits for each wired client, in isolation, then forwards only an
allowlist of advice fields. Clients in priority order: Claude Code
(`claude-code`), Codex (`openai-codex`), GitHub Copilot (`github-copilot`);
the dispatcher maps these client ids to upstream targets. Upstream also
ships `antigravity-cli` hooks, but the bootstrap does not wire Context Mode
hooks for Antigravity; that gap is recorded, not changed.

## Steps

- [x] **1. Capture upstream hook output in isolation (evidence only, no production code).**
  **Owner:** orchestrator.
  **Files:** add `tests/fixtures/context_mode_hook/1.0.169/<client-id>/<event>-<case>.json`
  (recorded stdout, exit code, and stderr summary) and a capture table in
  the phase session log.
  **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`,
  `shared/skills/ponytail/SKILL.md` (full).
  Copy the dispatcher into a temporary Git repository (the existing
  `installed_dispatcher` test pattern) and run it with a temporary `HOME`,
  `CLAUDE_CONFIG_DIR`, and `CODEX_HOME`, so no user-level file (for example
  `~/.claude/CLAUDE.md`) reaches the session store or a fixture. First
  confirm `--self-check` reports the direct pinned binary (no `npx`). For
  each client id `claude-code`, `openai-codex`, `github-copilot`, use one
  throwaway session id and these payloads: `sessionstart` (startup);
  `pretooluse` for Bash `ls`, Bash `curl -s https://example.com`, Read,
  Grep, the client's web-fetch tool, the client's subagent tool (Claude
  `Agent`, Copilot subagent), and a `ctx_execute` shell call; `posttooluse`
  (one Bash call); `precompact`; then `sessionstart` with source `compact`
  for the same session id. Record per case: exit code, stderr summary, every
  top-level and `hookSpecificOutput` field, any decision or input rewrite,
  the tool names mentioned, and whether restore content is present and in
  which field.
  **Question:** can continuity content be forwarded while every decision,
  every input rewrite, and every blocked-tool mention is dropped?
  **Stop rule:** if, for any client, restore content and blocked-tool advice
  share one field and cannot be separated by its observed structure, stop
  before step 2 and ask the user to choose: drop that client's session-start
  output (lose restore) or keep it with the advice.
  **Limits:** one pinned version, synthetic payloads, no native client run.

- [x] **2. Forward only allowlisted advice fields (GR-007).**
  **Owner:** coder.
  **Files:** modify `shared/hooks/scripts/context-mode-dispatch.sh` (hook
  modes run upstream instead of `exec`-ing it, capture its stdout and exit
  status, and pass stdout through the filter) and
  `shared/hooks/scripts/context-mode-mcp-filter.mjs` (add a hook-output mode
  that reuses its existing four-tool allowlist constant). Do not write a
  second hand-maintained tool list.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`,
  `shared/skills/integration-gate-spike/SKILL.md`.
  Rules:
  1. Build a new output object containing only the event name and the
     advice text field(s) step 1 identified for that client and event.
     Drop every other field, including any decision value,
     `permissionDecisionReason`, `updatedInput`, `tool_input`, `decision`,
     `continue`, `stopReason`, and `systemMessage`.
  2. Inside each kept text field, remove the advice blocks step 1
     identified. Then drop the field entirely if it still contains
     `mcp__plugin_context-mode_` or a `ctx_` tool name outside the
     allowlist.
  3. Emit nothing when no field survives, or when upstream output is empty
     or unparseable.
  4. Hook modes always exit 0. A nonzero upstream exit is logged once
     through the dispatcher's existing `warn` path.
  Upstream still runs, so its own side effects (event capture, compaction
  snapshot) are unchanged. The dispatcher adds no timeout of its own; the
  client hook timeout still applies. Server mode is unchanged.
  **Tests:** in `tests/test_context_mode_dispatch.py`, feed every recorded
  fixture through the filter and assert: no decision, no input rewrite, no
  blocked or plugin-prefixed name; a Copilot or Codex `allow` plus
  `updatedInput` fixture comes out with at most the advice field; separable
  restore content kept byte for byte; allowlisted `ctx_search` advice with
  the correct prefix kept; malformed output yields nothing; a nonzero
  upstream exit yields exit 0. Add one real-binary test selected by
  `-k real_upstream`. With `CONTEXT_MODE_REAL=1` it first asserts that
  `context-mode-dispatch.sh --self-check` reports `launcher=context-mode`
  and `version-contract=pinned-direct-binary`, failing otherwise (no `npx`
  download). It then runs WebFetch, `curl`, Agent, and session-start
  payloads for `claude-code` through the real dispatcher in an isolated
  temporary `HOME` and repository, and asserts the same rules. Without the
  variable it skips.

- [x] **3. Document the lane and its version tie.**
  **Owner:** documenter after review.
  **Files:** modify `docs/smoke-tests.md` (the "no safety decision or
  mutation" statement is now enforced, and how), `docs/runtime-checks.md`
  (bumping `PINNED_CONTEXT_MODE_VERSION` requires re-capturing the
  fixtures), `docs/target-mapping.md` (start the per-client parity table:
  this row, plus the Antigravity "Context Mode hooks not wired, no
  continuity" gap). Change `shared/policies/tool-routing.instructions.md`
  only when its text conflicts with the result.
  **Required Skills:** `shared/skills/documentation/SKILL.md`.

- [x] **4. Regenerate, refresh the installed runtime, review, close out.**
  **Owner:** orchestrator; fresh reviewer.
  Run `uv run python scripts/generate_targets.py --all` and
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  before verification. Map GR-007 to tests and fixtures in the closeout log.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/test_context_mode_dispatch.py tests/test_context_mode_mcp_filter.py tests/test_lifecycle_hooks.py -q
CONTEXT_MODE_REAL=1 uv run pytest tests/test_context_mode_dispatch.py -q -k real_upstream
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Claude Code: with the user-level `context-mode@context-mode` plugin off,
  start a new session in this repository, call WebFetch on a public page,
  and record that no Context Mode deny appears.
- Codex: in a new session, fetch a public page with the native web tool and
  record the result.
- GitHub Copilot: in VS Code agent mode, fetch a public page and record the
  result.

## Review Profiles

Use `.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Give the reviewer the step 1
capture table, the fixtures, GR-007, and the final diff.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
