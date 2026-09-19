# OpenWiki Phase A: Runtime and Safety Boundary

**Status:** COMPLETED
**Plan:** `.claude/plans/2026-09-19_phase-A-openwiki-runtime-and-safety-boundary.md`

## Goal

Implement the approved Phase A runtime, wrapper, installation, ignore, and deterministic safety-test contract for OpenWiki.

## Approach

- Keep OpenWiki behind one bootstrap-owned runner.
- Pin the runtime and optional Mermaid validators.
- Preserve user-owned root adapters and workflow files byte-for-byte.
- Restrict new mutations to `openwiki/**` and leave resumable run state on disk but ignored.
- Use fake executables for deterministic tests; do not make a provider or model request.

## Progress

- Pre-flight confirmed a clean outer `dev` branch and clean nested `ai-state` branch.
- Created `2026-09-19_openwiki-knowledge-layer-integration_implementation`.
- Branch hooks activated Phase A and updated the big-plan state.

## Verification

- Focused runner and installer tests: 31 passed.
- `scripts/generate_targets.py --all`: passed.
- `scripts/validate_targets.py`: passed.
- `scripts/check_runtime.py`: passed after local-only self-install.
- `.claude/scripts/verify.py fast --format json`: PASS.
- `git diff --check`: passed.
- Devcontainer Node/OpenWiki smoke build: not run because no build environment was used.

## Review

- Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`.
- Round 3 result: 3 CRITICAL and 4 MAJOR findings.
  Exact results: `.claude/quality_reports/review-results-2026-09-19_phase-A-openwiki-round3.json`.
- Round 4 result: FAIL on 1 new MAJOR, plus 1 MINOR needing disposition.
  Exact results: `.claude/quality_reports/review-results-2026-09-19_phase-A-openwiki-round4.json`.
- Ponytail result across both rounds: no simplification finding survived. Round 4 judged the
  growth from roughly 460 to 766 lines proportionate to the round-3 CRITICAL fixes, with no
  speculative interface, reinvented standard library, or dead flexibility.

### Round 3 finding disposition (all seven accounted for)

| # | Finding | Disposition |
| --- | --- | --- |
| 1 | Nested repository collapses to one directory fingerprint | Resolved. `_walk_ignored_directory` expands any entry ending in `/`. Verified empirically that this is the exclusive signal for a non-recursed nested repository. |
| 2 | Adapter restoration can delete concurrent edits | Resolved. Restoration authenticates through retained file descriptors, never unlinks a present file, and performs no write at all when content already matches. |
| 3 | Symlink walk is check-then-use | Scope changed by user decision, not re-raised. Phase A detects and fails closed; operating-system-enforced isolation moved to Phase E. Detection verified to match the documented claim. |
| 4 | Control-plane allowlist omits the provenance secret | Resolved. |
| 5 | Version probe before the lock and outside the telemetry default | Resolved. Lock acquired first; both probes share the child environment. |
| 6 | Post-run failures drop restoration errors | Resolved. All nine post-child returns carry restoration evidence. |
| 7 | Credential validator heuristic too narrow | Resolved. Closed six-key allowlist asserted as a subset relation. |

### Round 4 MINOR disposition

`_run()` is roughly 240 lines covering lock, preflight, snapshot, launch, restore, and compare.
**Accepted as-is.** Reason: the ordering of those stages is itself the safety property. Splitting
them into helpers would move that ordering into call-site convention, where a later edit could
reorder it without an obvious tell. The reviewer raised the same counter-argument and did not
assert the finding should block.

## Completed Work

- Added the pinned OpenWiki runtime, optional Mermaid validators, and host config mount.
- Added the bootstrap-owned runner, generator/installer wiring, ignore entry, validator coverage, and deterministic fake-command tests.
- Completed two review-driven fix loops for lock ordering, dirty-path fingerprints, symlink checks, sentinel restoration, nested-root resolution, ignored-path checks, and structured failures.

## Resumed-Session Rounds

Nine fix rounds and six review rounds ran after the pause. Every round is on
record in `.claude/quality_reports/review-results-2026-09-19_phase-A-openwiki-round*.json`.

| Round | Result | What it found |
| --- | --- | --- |
| 3 (pre-pause) | FAIL | 3 CRITICAL, 4 MAJOR |
| 4 | FAIL | Nested `.git` excluded wholesale, hiding `hooks/` and `config` |
| 5 | FAIL | The churn denylist missed `info/refs`, which `git gc` creates |
| 6 | FAIL | Decoy `.git` bypass; submodule nesting stopped at one level |
| 7 (coder-found) | — | `git ls-files` never reaches inside any `.git`-named directory, so round 6's fix was unreachable for non-repository control-plane paths |
| 8 | FAIL | No test pinned the `.cache` exclusion's boundaries |
| final | PASS | Empty findings |

Two defects were found by the reviewer running live experiments rather than
reading code. Two were found by the coder checking its own work, including a
test that passed for the wrong reason because a dangling symlink makes
`Path.is_dir()` false regardless of the check under test.

### Decisions taken during the resumed session

- **Detect now, sandbox later.** User decision. Phase A fails closed on a symlink
  escape inside the working tree; operating-system-enforced isolation of the
  child process became `2026-09-19_phase-E-openwiki-child-process-sandbox`.
- **Allowlist, not denylist, inside a nested `.git`.** Reversal of orchestrator
  guidance after rounds 4 and 5 each missed an entry. The set of files Git writes
  is open-ended and grows per release, so a denylist produces false failures on
  ordinary maintenance, and a check that fails on routine work gets ignored.
  The allowlist covers the execution vectors: `hooks/`, `config`,
  `config.worktree`, `info/attributes`, `worktrees/*/config.worktree`, and the
  same set under submodules at any depth.
- **Enumerate from disk, not through `git ls-files`.** Verified on git 2.43.0:
  `git ls-files --others --ignored --exclude-standard` omits everything inside
  any directory named `.git`, real repository or not, with no boundary entry.
  The result field was renamed `ignored_control_plane_paths` to
  `control_plane_paths`, since tracked files are now in scope.
- **`.claude/.cache/` excluded; `MEMORY.md`, plans, and logs are not.** One
  unrelated tool call changed two files under `.cache/`. Excluding the protected
  surface instead would have reopened the round-3 CRITICAL, so concurrent agent
  activity is documented as a residual limit rather than silenced.
- **Accepted MINOR:** `_run()` length. The stage ordering is the safety property;
  extracting helpers would move it into call-site convention.

### Accuracy note

The final review found the coder's account of which code mutation causes which
test failure was imprecise: a substring-match mutation fails only the near-miss
case, not the symlink case as reported. The delivered tests are correct; the
narrative about them was not. Recorded because the evidence trail should match
what was actually observed.

## [LEARN] Entries

- [LEARN:quality] `git ls-files --others --ignored --exclude-standard` silently
  omits everything inside any directory literally named `.git`, whether or not it
  is a real repository, and emits no boundary entry for it. Verified on git
  2.43.0. Enumerate from disk when the question is "what exists", not "what does
  git consider ignored".
- [LEARN:review] Do not build a detection rule from a denylist of what an
  external tool writes. Two consecutive rounds missed an entry (`COMMIT_EDITMSG`,
  then `info/refs` from `git gc`) because Git's written-file set is open-ended and
  grows per release. Allowlist the surface you own and document the narrower claim.
- [LEARN:quality] A check that fails on ordinary activity gets ignored, which is a
  worse security outcome than a narrower check that never cries wolf. Measure
  churn against the real directory before shipping a fingerprint comparison.
- [LEARN:review] When narrowing behaviour on a name, validate that the thing named
  is what it claims to be. Narrowing at any directory called `.git` without
  checking it was a Git directory let a decoy hide an arbitrary tree. The
  narrowing rule and its validation are one change, not two.
- [LEARN:quality] A fixture pointing a symlink at a non-existent path can make a
  test pass for the wrong reason: `Path.is_dir()` is false on a dangling link
  regardless of any `is_symlink()` check, so the check under test never runs.

## Documentation Decision

No documentation change this session, recorded as a decision rather than a skip.
The user-facing surface — devcontainer prerequisite, pinned versions, the
`~/.openwiki` mount — is already in `README.md` and `docs/architecture.md` from
the checkpoint commit. This session changed internal runner logic only. The
operational constraints live in the module docstring; Phase B adds the skill that
documents how to run the runner.

## Residual Limits Carried Forward

Stated in the runner's module docstring and repeated here so they are not lost:

1. A write landing outside the repository entirely is not detected. Phase E.
2. A file inside a *validated* git directory but off the allowlist is not
   fingerprinted. It can hide inert data, not a code-execution vector.
3. A nested repository whose `.git` is a `gitdir:` pointer outside the tracked
   tree escapes the mechanism; the pointer file itself is fingerprinted.
4. `.claude/.cache/` is excluded by deliberate exception.
5. Concurrent agent-session writes to `.claude` cause a fail-closed failure
   naming unrelated files. Re-run when the checkout is quiet. The `flock`
   serialises runner against runner, not runner against an agent session.

## Original Remaining Work (from the pause, now complete)

- Resolve every finding in the saved round 3 review result.
- Re-run focused tests, generation, validation, runtime consistency, and fast verification.
- Re-run the full five-profile review until no CRITICAL or MAJOR finding remains.
- Complete normal Phase A closeout, findings persistence, phase/closeout receipts, commit, and push.

## Resume (2026-09-19)

Resumed on the same implementation branch. Plan restored to `in-progress`; no new phase created.

### Scope decision taken on resume

Round 3 CRITICAL finding 3 (the OpenWiki symlink walk is check-then-use) has no in-process fix:
Python cannot supervise another program's file writes. The user chose **detect and refuse now,
prevent later**:

- Phase A re-walks `openwiki/` after the child exits and fails closed, naming every symlink and
  every path that moved. The root adapters are restored from pre-run bytes regardless. Nothing
  is committed on a failed refresh.
- Operating-system-enforced isolation of the child process is recorded as a new
  `2026-09-19_phase-E-openwiki-child-process-sandbox`, added to the big plan's phase list,
  step summary, and risk table.
- Accepted residual limit, documented in the runner docstring: a write landing outside the
  repository entirely is not detected until Phase E.

### Original resume point (from the pause)

## Resume Point

Resume Phase A on the same implementation branch. Restore this plan to `in-progress`, then return the saved round 3 findings to the existing coder context if available. Start with the three CRITICAL runner findings before the four MAJOR findings. Do not create a new phase or treat the current verification as final after code changes.
