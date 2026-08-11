# Session: Context Mode pin and cache ownership — Phase H

**Date:** 2026-08-12
**Plan:** [2026-08-12_phase-H-context-mode-pin-and-cache-ownership](../plans/2026-08-12_phase-H-context-mode-pin-and-cache-ownership.md)
**Status:** COMPLETED

## Goal

Fix two merge-blocking Context Mode defects reported after the big plan was
closed: the 1.0.169 pin was enforced only on MCP mode, and an arbitrary external
`CONTEXT_MODE_DIR` could be adopted and renamed by the quarantine path.

## Why A New Phase

Phases A-G are committed and reviewed. Backdating these findings into a
completed review would falsify plan state, and the commit gate correctly refuses
any commit outside a phase, so the smallest honest vehicle was a new corrective
phase recording why it exists.

## Work Log

- Confirmed both findings in code before changing anything. `resolve_context_mode`
  returned `context-mode` from `PATH` with no version check and line 272 exec'd
  it directly; `--self-check` printed `required-version` as an unconditional PASS.
  `storage_override_is_allowed` returned success for arbitrary external absolute
  paths, and `configure_storage` quarantines by renaming the directory.
- Established how to read the version. Context Mode 1.0.169 has no working
  version flag — `--version`, `-v`, and `version` all exit 0 printing nothing.
  `doctor` reports a version but is slow, ANSI-decorated, and performs a network
  npm check, so it cannot gate every hook event. The executable is an npm bin
  symlink into the package directory, so the owning `package.json` is the right
  source: offline, fast, deterministic, independent of the minified bundle.
- Added `direct_context_mode_version`, which resolves the executable and reads
  the owning manifest, matching on `name` as well as `version` so a nested
  dependency manifest can never be mistaken for Context Mode's own.
- Gated the direct binary in `resolve_context_mode`. A wrong or undeterminable
  version is never executed; the pinned `npx context-mode@1.0.169` fallback is
  used when available, and hooks otherwise warn and fail open.
- Rewrote `--self-check` to report `required-version`, `resolved-path`,
  `observed-version`, and a `version-contract` result.
- Narrowed `storage_override_is_allowed` to the project-local cache subtree, so
  an override is honoured only at or beneath `.claude/.cache/context-mode`.
  Everything else warns and falls back, leaving the refused path untouched.
- Updated the dispatcher test fixture to mirror a real npm install layout (bin
  symlink into a package directory) so version cases can be exercised at all.
- Updated the test that previously asserted external overrides are preserved,
  plus README, architecture, runtime-checks, and smoke-tests docs.

## Files Changed

- `shared/hooks/scripts/context-mode-dispatch.sh`
- `tests/test_context_mode_dispatch.py`
- `README.md`
- `docs/architecture.md`
- `docs/runtime-checks.md`
- `docs/smoke-tests.md`

## Tests Added

Finding 1 (version pin):

- `test_hook_uses_direct_binary_only_at_the_exact_pinned_version`
- `test_hook_refuses_a_direct_binary_that_is_not_the_pinned_version` —
  parametrized over `1.0.170`, `1.0.168`, `0.9.0`, and a manifest named
  `some-other-package` whose version *is* `1.0.169`
- `test_hook_refuses_a_direct_binary_with_an_undeterminable_version`
- `test_hook_falls_back_to_pinned_npx_when_direct_binary_is_rejected`
- `test_self_check_reports_the_observed_version_and_contract_result`
- `test_self_check_reports_a_failing_version_contract`

Finding 2 (cache ownership):

- `test_approved_cache_subtree_override_is_preserved` (narrowed from the old
  test that also asserted external overrides are preserved)
- `test_external_override_falls_back_and_never_touches_that_path` — asserts the
  external directory keeps its contents, gains no provenance marker, and is not
  renamed to a `.untrusted.*` sibling
- `test_external_override_is_not_created_when_absent`

## Verification Results

- Focused Context Mode/state-sync/installer tests — **118 passed**.
- Full suite — **812 passed**.
- `uv run mypy .` — no issues in 22 source files.
- Ruff check clean; `ruff format --check` clean (one new test file reformatted).
- `bash -n` on the dispatcher — OK.
- Generation, `validate_targets.py`, `validate_plan_frontmatter.py`, and
  `check_runtime.py` — pass, zero runtime failures.
- Two independent generations byte-identical via `diff -qr`.
- No cache or provenance artifact in `dist/`, the outer Git index, or the nested
  `ai-state` index.
- Live MCP probe against real Context Mode 1.0.169: exactly four tools
  advertised; `ctx_execute`, `ctx_execute_file`, `ctx_batch_execute`,
  `ctx_fetch_and_index`, `ctx_upgrade`, `ctx_purge`, `ctx_insight`, and an
  unknown tool all rejected locally; exact server version validated.
- MCP filter untouched and still holding: the notification/batch bypass probe and
  the cross-method id leak probe both fail to breach.
- Installed `--self-check` against the real binary reports
  `observed-version=1.0.169` and `version-contract=pinned-direct-binary`.

## Load-Bearing Proof

- Reverting the version gate (accepting any `context-mode` on `PATH`) fails 7
  tests.
- Reverting the ownership narrowing (re-allowing external absolute overrides)
  fails 3 tests, including `test_in_repo_symlink_escape_falls_back`.

## [LEARN] Entries

- [LEARN:security] Enforcing a version pin on one transport does not pin the
  dependency. The MCP filter proved `serverInfo.version` over stdio, which made
  the pin look complete while hook mode still exec'd whatever was on `PATH`.
  Enumerate every path that launches a pinned dependency, not just the one with
  the obvious handshake.
- [LEARN:security] A self-check that restates configuration proves nothing. It
  printed the required version as a PASS without ever observing the installed
  binary. A check should report the observed value and an explicit contract
  result, so the two can disagree visibly.
- [LEARN:architecture] Ownership follows the destructive operation. Accepting an
  arbitrary external path was harmless until quarantine began renaming
  directories; the remediation mechanism is what defines how far ownership may
  extend. Scope a writable/renameable location to what the tool created itself.

## Score: 100/100 (EXCELLENCE)

- `.claude/quality_reports/score-phase-H.json`
- `.claude/quality_reports/findings-phase-H.json` (0/0/0; profiles `code`,
  `security`, `tests`, `ponytail`, `documentation`)

## Remaining Limitations

- Version detection depends on the npm package layout (a bin entry resolving
  into a package directory containing `package.json`). An unusual repackaging
  that hides the manifest reads as "undeterminable" and is refused rather than
  trusted — fail-closed for correctness, but it would decline an otherwise valid
  1.0.169 install. The pinned `npx` fallback covers that case when present.
- Directory indexing remains deferred; `ctx_index` still takes content and a
  single guarded regular file only.
- The upstream server still performs an npm version check at startup and hourly,
  so it is not network-free.
- Stale root-`CLAUDE.md` Ponytail lifecycle wording and stale README
  planner-interview wording were left untouched as separately-tracked
  pre-existing guidance debt.

## Open Questions / Next Steps

- None for this correction. The branch remains local and unmerged; no push or PR
  was made by this phase.
