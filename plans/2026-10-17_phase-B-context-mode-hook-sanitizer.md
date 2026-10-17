---
name: 2026-10-17_phase-B-context-mode-hook-sanitizer
type: small-plan
parent_plan: gate-repair
phase_index: 2
status: planned
closeout_session_log:
---

# Small Plan: Context Mode Hook Sanitizer

## Scope

Stop the Context Mode hook lane from advising or forcing tools that the
repository's own MCP filter blocks (GR-007). Today the dispatcher forwards
upstream `context-mode hook` output unchanged. At the pinned `1.0.169` that
output names blocked tools, and it denies WebFetch and plain `curl` in favour
of blocked tools. The lane is documented as one that "makes no safety
decision". This phase first records what upstream actually emits for each
wired client, then filters the output in the dispatcher. Clients in priority
order: Claude Code (`claude-code`), Codex (`codex`), GitHub Copilot
(`vscode-copilot`). Antigravity has no Context Mode hooks wired, so it has
nothing to sanitize; that gap is recorded, not changed.

## Steps

- [ ] **1. Capture upstream hook output (evidence only, no production code).**
  **Owner:** orchestrator.
  **Files:** add `tests/fixtures/context_mode_hook/1.0.169/<target>/<event>.json`
  (recorded outputs) and a short capture note in the phase session log.
  **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`,
  `shared/skills/ponytail/SKILL.md` (full).
  For each target `claude-code`, `codex`, `vscode-copilot`, pipe fixed
  synthetic payloads through
  `.claude/hooks/scripts/run-hook.sh context-mode-dispatch.sh <client-id> <event>`
  with one throwaway session id: `sessionstart` (startup), `pretooluse`
  (Bash `ls`, Bash `curl -s https://example.com`, Read, Grep, the client's
  web-fetch tool), `posttooluse` (one Bash call), `precompact`, then
  `sessionstart` with source `compact` for the same session id. Replace
  absolute user paths with a placeholder before saving. Record a table: per
  target and event, the output fields, any decision, the tool names
  mentioned, and whether restore content is present and separable (by which
  block or field).
  **Question:** can continuity content be kept while every blocked-tool
  mention and every upstream decision is removed?
  **Stop rule:** if, for any target, restore content cannot be separated from
  blocked-tool advice, stop before step 2 and ask the user to choose: drop
  that target's session-start output (lose restore) or keep it with the
  advice.
  **Limits:** one pinned version, synthetic payloads, no native client run.

- [ ] **2. Sanitize hook output in the dispatcher (GR-007).**
  **Owner:** coder.
  **Files:** modify `shared/hooks/scripts/context-mode-dispatch.sh` (hook
  modes stop `exec`-ing upstream; they run it and pass its stdout through
  the sanitizer) and `shared/hooks/scripts/context-mode-mcp-filter.mjs` (add
  a hook-output mode that reuses its existing four-tool allowlist constant).
  Do not write a second hand-maintained tool list.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`,
  `shared/skills/integration-gate-spike/SKILL.md`.
  Rules, applied to the JSON upstream prints:
  1. Remove any upstream `deny` or `ask` decision and its reason, in each
     client's captured shape. This lane makes no safety decision; the
     bootstrap's own guards do.
  2. Remove the advice blocks step 1 identified, by their observed block or
     field boundaries.
  3. Safety net: after steps 1–2, drop any remaining string field that still
     contains `mcp__plugin_context-mode_` or a `ctx_` tool name outside the
     allowlist.
  4. Empty or unparseable output: emit nothing, exit 0, and write one
     warning through the dispatcher's existing `warn` path.
  Upstream still runs, so its own side effects (event capture, compaction
  snapshot) are unchanged. Hook modes keep exit status 0 and the existing
  missing-binary and timeout behavior. Server mode is unchanged.
  **Tests:** in `tests/test_context_mode_dispatch.py`, feed every recorded
  fixture through the sanitizer and assert: no blocked or plugin-prefixed
  name, no `deny` or `ask`, separable restore content kept byte for byte,
  allowlisted `ctx_search` advice with the correct prefix kept, malformed
  output yields nothing. Add one real-binary test selected by
  `-k real_upstream`. With `CONTEXT_MODE_REAL=1` it requires the pinned
  binary (it fails, not skips, when the binary is absent). It runs WebFetch,
  `curl`, and session-start payloads for `claude-code` through the real
  dispatcher and asserts the same rules. Without the variable it skips.

- [ ] **3. Document the lane and its version tie.**
  **Owner:** documenter after review.
  **Files:** modify `docs/smoke-tests.md` (the "makes no safety decision"
  statement is now enforced, and how), `docs/runtime-checks.md` (bumping
  `PINNED_CONTEXT_MODE_VERSION` requires re-capturing the fixtures),
  `docs/target-mapping.md` (start the per-client parity table: this row, plus
  the Antigravity "no Context Mode hooks, no continuity" gap). Change
  `shared/policies/tool-routing.instructions.md` only when its text
  conflicts with the result.
  **Required Skills:** `shared/skills/documentation/SKILL.md`.

- [ ] **4. Regenerate, refresh the installed runtime, review, close out.**
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

- Claude Code: in a new session in this repository, call WebFetch on a
  public page and record that no Context Mode deny appears. The user-level
  `context-mode@context-mode` plugin, if still enabled, has its own hooks;
  record its effect separately.
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

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
