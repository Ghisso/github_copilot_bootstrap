# Session: Context Mode local cache Phase F

**Date:** 2026-08-11
**Plan:** [2026-08-11_phase-F-context-mode-local-indexing-and-cache-boundary](../plans/2026-08-11_phase-F-context-mode-local-indexing-and-cache-boundary.md)
**Status:** COMPLETED

## Goal

Keep Context Mode hooks and MCP available through one repository-owned
dispatcher and one absolute project-local `CONTEXT_MODE_DIR`, with a
deliberately small public-stdio filter exposing only guarded `ctx_index`,
`ctx_search`, `ctx_stats`, and `ctx_doctor` in front of pinned Context Mode
`1.0.169`.

## Work Log

- Phase E committed as `df8a1e8`; the lifecycle advanced to Phase F.
- Resumed a partially implemented, entirely unverified Phase F: the prior
  session was cut off by an execution limit before running any test.
- Confirmed command execution, then ran the previously blocked focused tests.
  Reordered the filter's symlink check ahead of containment so a symlink
  escape reports deterministically, and added a strict `ctx_index` argument
  allowlist (`content`, `path`, `source`) that closes the `followSymlinks`
  weakening class.
- Fixed the confirmed MCP parity-loop defect in `scripts/validate_targets.py`:
  a leaked `server` loop variable checked Context7 twice and never validated
  Semble parity. Parity is now compared per target per server, with a
  regression proving each server fails independently.
- Restored the filtered MCP contract that the repository had regressed to a
  "hook-only, MCP absent" design: generator, validator, and all three targets
  (GitHub Copilot, Claude Code, OpenAI Codex) now route Context Mode through
  `context-mode-dispatch.sh server`, and stale absence assertions were
  inverted into positive four-tool assertions.
- Reconciled documentation and policy across README, architecture, runtime
  checks, smoke tests, the routing policy, onboarding, all six agent prompts,
  and the generated root-guidance template, together with the coupled
  validator assertion that had been enforcing the stale wording.
- Ran four adversarial review rounds and resolved every confirmed finding.

## Security Defects Found And Fixed

- **CRITICAL, empirically confirmed exploitable.** The filter gated the
  allowlist, version check, and `ctx_index` validation on
  `method === "tools/call" && Object.hasOwn(message, "id")`. A notification
  shaped message (no `id`) and a JSON-RPC batch array both fell through to the
  unvalidated forward. A probe sent no `initialize` at all and still reached a
  fake upstream with `ctx_execute` and `ctx_batch_execute` — the two arbitrary
  code execution tools. Replaced with default-deny on message shape, then
  dispatch on `method` alone.
- **CRITICAL.** The cache provenance marker consisted of a hardcoded version, a
  hardcoded filter contract literal, and a frequently predictable repository
  path, stored inside the nested `ai-state` working tree, so a hostile remote
  could ship a poisoned cache plus a forged marker. Bound provenance to a
  locally generated secret held outside that tree.
- **MAJOR.** `Set`-based request-id tracking forwarded the second response for a
  reused `tools/list` id unfiltered, leaking every blocked tool name and schema.
  Replaced with counted tracking.
- **MAJOR.** The list counter was consumed by any response sharing the id, so a
  cross-method id collision untracked a pending `tools/list` and leaked it.
  The counter is now consumed only on a structurally confirmed list result.
- **MAJOR.** The consumer-generated `.gitignore` did not exclude the provenance
  secret, so a routine `git add -A` would commit it into a consumer's main
  history. Added as a glob that also covers the pre-rename temp file.
- **CRITICAL, self-inflicted and caught in review.** Bounding the id map by
  evicting the oldest entry was fail-open, reintroducing the same leak class.
  Replaced with fail-closed refusal at capacity.
- **MAJOR.** A tautological test (`process.stderr.read(0)` always returns `""`)
  meant "never log raw arguments" had no real coverage.
- **MAJOR.** Dispatcher `server` mode had zero runtime coverage despite being a
  plan Step 1 verification requirement.
- Minor: unvalidated `source` argument, missing child-process signal cleanup,
  unbounded id-map growth, an unlocked secret-creation race, a missing
  `upstream.stdin` error handler, a `stdout.end()` race against buffered
  upstream output, and an `INT`/`TERM` trap left set process-wide.

## Verification Results

- `uv run pytest tests/ -q` — **797 passed**.
- `uv run mypy . --ignore-missing-imports --explicit-package-bases` — no issues
  in 22 source files.
- `uv run ruff check scripts/ tests/` — clean. `ruff format --check` — clean.
- `bash -n` on both changed shell scripts and `node --check` on the filter — OK.
- `scripts/generate_targets.py --all`, `scripts/validate_targets.py`,
  `scripts/validate_plan_frontmatter.py` — pass.
- `scripts/check_runtime.py` — zero failures after the dogfood refresh. The
  stale-runtime failures were this phase's own changed files, not unrelated
  drift.
- Two independent generations compared with `diff -qr` — identical. No
  `.cache/context-mode` artifact under `dist/`.
- Installed dispatcher `--self-check` — 6 PASS. `state-sync.sh status` — healthy.
- `git diff --check` — clean.
- Live integration probe through the real dispatcher against real upstream
  `1.0.169`: exact version, `tools/list` exactly the four allowed tools, all
  seven blocked tools plus an unknown tool rejected locally, guarded content
  indexing and search succeeding from the local cache, and absolute-outside,
  traversal, directory, `followSymlinks`, and ambiguous-argument inputs all
  rejected.
- Independent exploit probes for the notification/batch bypass and the
  cross-method id leak both re-run against final code: filter held.
- Read-only repository root: hooks warn and fail open with exit 0; `server`
  mode fails closed with exit 1; no orphaned secret temp file.

## [LEARN] Entries

- [LEARN:security] A protocol allowlist must key on the method alone, never on
  `method && has(id)`. Gating on request shape let a `tools/call` notification
  and a batch array reach upstream with no allowlist and no version gate.
- [LEARN:security] Bounding a security-relevant tracking map by evicting the
  oldest entry is fail-open: eviction untracks a still-pending request so its
  later response bypasses the filter. Refuse new entries at capacity instead.
- [LEARN:security] Anti-forgery state must live outside every channel that can
  restore it, and its temp-file glob must be ignored too, not just its final
  name.
- [LEARN:tests] An assertion that cannot fail is worse than none, because it
  advertises coverage. Prove a new guard by running its test against the
  pre-fix code and watching it fail.
- [LEARN:tests] When a regression's failure mode is a silent hang, assert with a
  bounded wait so a future regression fails cleanly instead of stalling.
- [LEARN:verification] Reconcile agent claims against the artifact, not the
  report; a subagent mislabeled this phase's own changed files as unrelated
  pre-existing drift on a required gate.
- [LEARN:security] `trap ... RETURN INT TERM` is not uniformly scoped: `RETURN`
  is function-local while `INT`/`TERM` are process-wide. Reset signal traps on
  every exit path, including early returns.

## Score: 100/100 (EXCELLENCE)

- Quality report: `.claude/quality_reports/score-phase-F.json`
- Findings report: `.claude/quality_reports/findings-phase-F.json`
  (0 critical, 0 major, 0 minor; profiles `code`, `architecture`, `security`,
  `tests`, `ponytail`, `documentation`)

## Shipped Limitations And Residual Risks

- **Directory indexing did not ship.** `ctx_index` accepts content and a single
  guarded regular file; directory input is rejected with an actionable message.
  This is the plan's documented temporary-limitation fallback, taken because
  proving safe directory containment and option merging would have materially
  expanded the filter. Documented as such in README, the routing policy, and
  the architecture doc.
- The upstream server performs an npm version check at startup and hourly, so
  nothing claims it is network-free.
- Two minor fixes (the secret-creation race and the `upstream.stdin` error
  handler) are covered by manual verification rather than automated regressions,
  because reproducing them deterministically would require test-only seams or a
  flaky true-concurrency test.
- Review round 5 was self-verified rather than delegated: the permission
  classifier blocked further reviewer subagent spawns. The four round-4 fixes
  were checked by direct reading plus targeted empirical probes, including the
  read-only-root fail-open/fail-closed test above.
- Codex project-hook trust is content-bound. Reopen or reload the repository in
  Codex for VS Code and re-approve the project hooks before relying on the
  refreshed lifecycle hooks.

## Open Questions / Next Steps

- Phase F is complete. Proceed to big-plan closeout for
  `state-sync-recovery-and-plan-cancellation`.
- A later approved plan may revisit bounded directory indexing; any Context Mode
  pin change must re-run the Phase F capability and security tests.
- Graphify remains a closed NO-GO and was not touched.
