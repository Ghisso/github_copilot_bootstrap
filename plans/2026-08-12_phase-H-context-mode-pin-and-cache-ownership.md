---
name: 2026-08-12_phase-H-context-mode-pin-and-cache-ownership
type: small-plan
parent_plan: state-sync-recovery-and-plan-cancellation
phase_index: 8
status: complete
closeout_session_log: .claude/session_logs/2026-08-12_context-mode-pin-and-cache-ownership-phase-H.md
---

# Small Plan: 2026-08-12_phase-H-context-mode-pin-and-cache-ownership

## Why This Phase Exists

Two merge-blocking Context Mode defects were reported by the user after the big
plan had already been closed out. Phases A-G are committed and their reviews are
finished, so these findings were **not** part of any previous completed review
and must not be backdated into one. This phase exists solely to carry the two
corrections honestly, with its own verification, findings, and score.

Scope is deliberately narrow. It does not reopen the Phase F architecture.

## Findings Corrected

1. **The 1.0.169 pin was enforced on MCP mode only.** The MCP filter proves the
   pin over stdio via `serverInfo.version`, but hook mode preferred any
   `context-mode` on `PATH` and executed it unverified, and `--self-check`
   printed `required-version` as a PASS without ever observing the binary's
   actual version. That contradicted the Phase F contract that the audited
   version is pinned across install, fallback, runtime, and capability checks.
2. **An arbitrary external `CONTEXT_MODE_DIR` could be adopted and renamed.**
   `storage_override_is_allowed` accepted any absolute path outside the
   repository, and `configure_storage` quarantines an unaudited cache by
   *renaming the directory*. The bootstrap could therefore reorganize
   user-owned state outside the repository, which contradicts the conservative
   ownership model used everywhere else in the project.

## Scope

- Verify a direct `context-mode` executable is exactly `1.0.169` before running
  it in hook mode; never execute a wrong or undeterminable version; keep the
  pinned `npx` fallback; preserve hook fail-open. Report the observed version
  and a contract result from `--self-check`.
- Restrict bootstrap cache ownership to the project-local
  `.claude/.cache/context-mode` subtree. Refuse any other `CONTEXT_MODE_DIR`
  with a clear warning and fall back, never creating, stamping, renaming, or
  otherwise mutating the refused path.
- Update the tests and docs that stated external absolute overrides are
  supported.

Explicitly out of scope and unchanged: the four-tool allowlist, the filtered
tool set, method-based fail-closed MCP filtering, the initialization/version
gate, bounded request tracking, guarded regular-file/content `ctx_index`,
deferred directory indexing, read-deny defense in depth, the shared
project-local `CONTEXT_MODE_DIR` for MCP and hooks, direct reads/`rg`/Semble as
normal routes, hook routing advertising only exposed tools, the MCP parity-loop
fix, and Graphify as a closed NO-GO. No Serena, `ast-grep`, capability
registry, telemetry, MCP gateway, or generic MCP security framework was added.

The known stale root-`CLAUDE.md` Ponytail lifecycle wording and stale README
planner-interview wording are pre-existing guidance debt being handled
separately, and were deliberately not touched here.

## Implementation Notes

Context Mode 1.0.169 has no working version flag: `--version`, `-v`, and
`version` all exit 0 printing nothing. `doctor` does report a version but is
slow, ANSI-decorated, and performs a network npm check, so it is unusable as a
per-hook-event gate. The executable is an npm bin symlink into the installed
package directory, so `direct_context_mode_version` resolves it and reads the
owning `package.json`, matching on `name` as well as `version` so a nested
dependency manifest can never be mistaken for Context Mode's own. This is
offline, fast, deterministic, and independent of the minified bundle's
internals.

## Steps

- [x] Add `direct_context_mode_version` and gate the direct binary in
      `resolve_context_mode`, keeping the pinned `npx` fallback.
- [x] Report `required-version`, `resolved-path`, `observed-version`, and
      `version-contract` from `--self-check`.
- [x] Narrow `storage_override_is_allowed` to the project-local cache subtree
      and warn clearly on any other override.
- [x] Model a real npm install layout in the dispatcher test fixture so version
      cases can be exercised.
- [x] Add regressions for both findings and prove each fails when reverted.
- [x] Update README, architecture, runtime-checks, and smoke-tests docs.

## Verification

```bash
uv run pytest tests/test_context_mode_dispatch.py tests/test_context_mode_mcp_filter.py tests/test_state_sync.py tests/test_install_bootstrap.py -q --tb=short
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
bash -n shared/hooks/scripts/context-mode-dispatch.sh
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/check_runtime.py
bash .claude/hooks/scripts/context-mode-dispatch.sh --self-check
```

## Review Profiles

- `.claude/review-profiles/code.md`
- `.claude/review-profiles/security.md`
- `.claude/review-profiles/tests.md`
- `.claude/review-profiles/ponytail.md`
- `.claude/review-profiles/documentation.md`

## Results

- Focused Context Mode/state-sync/installer tests — 118 passed.
- Full suite — 812 passed.
- mypy — no issues in 22 source files. Ruff check and `format --check` — clean.
- `bash -n` — OK. Generation, target validation, plan frontmatter, runtime
  checks — pass, zero runtime failures.
- Two independent generations byte-identical via `diff -qr`.
- No cache or provenance artifact in `dist/`, the outer Git index, or the
  nested `ai-state` index.
- Live MCP probe against real 1.0.169: exactly four tools advertised, all seven
  blocked tools plus an unknown tool rejected locally, exact version validated.
- MCP filter unchanged and still holding: notification/batch bypass and
  cross-method id leak probes both fail to breach.
- Load-bearing proof: reverting the version gate fails 7 tests; reverting the
  ownership narrowing fails 3 tests.
- Score 100/100 (EXCELLENCE); findings 0 critical, 0 major, 0 minor.

## Done Criteria

- [x] Hook mode executes only a provably pinned direct binary.
- [x] `--self-check` proves the version contract rather than restating the pin.
- [x] No external `CONTEXT_MODE_DIR` is ever created, stamped, renamed, or
      mutated.
- [x] Phase F security architecture unchanged.
- [x] Regressions exist that fail if either fix is reverted.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
