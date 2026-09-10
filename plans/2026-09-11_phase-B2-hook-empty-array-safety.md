---
name: 2026-09-11_phase-B2-hook-empty-array-safety
type: small-plan
parent_plan: consumer-lifecycle-friction-hardening
phase_index: 3
status: in-progress
closeout_session_log:
---

# Small Plan: Phase B2 — Hook Empty-Array Safety On Bash 3.2

## Scope

Make every reachable empty-array expansion in the lifecycle hook scripts safe
on the declared Bash 3.2 orchestration baseline. Under `set -u`, Bash 3.2
treats `"${arr[@]}"` on an empty array as an unbound-variable error and aborts
the script. Bash 4.4 and later do not. Every hook entry point sets
`set -euo pipefail`, and `docs/runtime-checks.md` states that gate
orchestration must run identically on a stock macOS consumer machine, whose
default `/bin/bash` is 3.2.

The immediate consequence is a masked diagnostic in the commit gate. When a big
plan has no `current_phase`, `assert_commit_invariants` intends to report
`big plan has no current_phase`. On Bash 3.2 it instead aborts earlier with
`all_phases[@]: unbound variable`, so the operator sees an internal shell error
instead of the actionable message the gate was written to produce.

This phase changes expansion safety only. No gate decision, severity, message
text, or protected-path inventory changes.

## Context And Evidence

Reported by another agent using this bootstrap, then verified against source.
Corrections to the original report, recorded so the fix is not justified by a
wrong premise:

- No gate message instructs an operator to clear `current_phase` after the last
  phase. An empty `current_phase` is itself a gate failure
  (`_lib-frontmatter.sh:1232`). The defect masks that failure; it does not
  arise from following gate advice.
- The current branch is not affected. Its big plan has a valid `current_phase`
  and a populated `phases` list, so `all_phases` is non-empty.
- The defect could not be reproduced on this machine, which runs Bash 5.2 where
  the expansion is legal. `BASH_COMPAT=3.2` does not restore the Bash 3.2
  behavior. Confirmation is by code reading plus the repository's own declared
  baseline. Any test must therefore assert the guarded form directly rather
  than depend on the host shell version.
- The reported single line is one instance of an inconsistently applied idiom.
  `git-protection.sh:104` already uses the guarded form while the immediately
  following line 105 does not.

The repository already uses the intended idiom in three places:
`session-start-state.sh:29`, `record-commit-closeout.sh:101`, and
`record-commit-closeout.sh:104`.

## Confirmed Reachable Instances

Each was checked for a preceding emptiness guard. These have none and can be
reached with an empty array:

| Location | Why it can be empty |
|---|---|
| `_lib-frontmatter.sh:1253` | `all_phases` is populated only when `current_phase` is non-empty and a valid slug |
| `_lib-frontmatter.sh:652` | guard is `[[ "${#paths[@]}" -gt 1 ]] && return 0`, so zero paths falls through into the loop |
| `_lib-frontmatter.sh:392` | `_TOKENS` is empty when `_shell_tokenize` receives blank input |
| `_lib-frontmatter.sh:429` | same |
| `_lib-frontmatter.sh:531` | same |
| `_lib-frontmatter.sh:535` | `tokens` inherits the empty `_TOKENS` |
| `git-protection.sh:105` | `tokens` stays empty when `_TOKENS` is empty |

## Confirmed Already Safe — Do Not Change

Each of these is preceded by an explicit count check. Leave them alone; adding
a redundant guard would obscure the real invariant.

- `pre-push:38`, `commit-msg:41`, `enforce-commit-gate.sh:57`,
  `enforce-commit-gate.sh:66`, `enforce-pr-gate.sh:51` — guarded by
  `[[ "${#failures[@]}" -gt 0 ]]`.
- `_lib-frontmatter.sh:719` — guarded by `[[ "${#paths[@]}" -gt 0 ]] || return 1`.
- `_lib-frontmatter.sh:1361`, `_lib-frontmatter.sh:1464` — guarded by
  `[[ "${#phases[@]}" -eq 0 ]]` with an early return.
- `restore-root-adapters.sh:111` — guarded by `((${#paths[@]})) || fail`.
- `_lib-frontmatter.sh:1170` — `args` is initialized with seven elements.
- `reporting-reminder.sh:122` — confirm `options` during implementation and
  treat it as reachable only if no guard exists.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` in `full` mode
- `.claude/skills/code-style/SKILL.md`
- `.claude/skills/testing-patterns/SKILL.md`

## Review Profiles

- `code`
- `architecture`
- `security`
- `tests`
- `ponytail`

## Steps

1. **Guard the reachable expansions.**
   Owner: `coder`.
   Apply the existing repository idiom `${arr[@]+"${arr[@]}"}` to each location
   in Confirmed Reachable Instances, and to `reporting-reminder.sh:122` only if
   it proves unguarded. Do not touch the Confirmed Already Safe list. Do not
   introduce a helper function, a new abstraction, or a shell-compatibility
   layer; this is a literal expansion-safety change.

2. **Preserve the masked diagnostic.**
   Owner: `coder`.
   Confirm that with `all_phases` guarded, a big plan with an empty
   `current_phase` reports exactly `big plan has no current_phase` and the
   surrounding cancellation sweep is skipped rather than partially executed.

3. **Test the guarded form directly.**
   Owner: `coder`.
   Add tests that assert the source uses a guarded expansion at each fixed
   location, since the host Bash cannot reproduce the 3.2 failure. Add a
   behavioral test that a big plan with an empty `current_phase` produces the
   intended gate failure message. Where an existing hook test harness already
   exercises these code paths, extend it rather than adding a parallel harness.

4. **Prevent regression of the idiom.**
   Owner: `coder`.
   Add one check that fails when a hook script under `shared/hooks/` expands an
   array unguarded without a preceding emptiness guard, or record explicitly in
   the closeout why a reliable check is not practical. Prefer extending
   `scripts/check_runtime.py` or the existing hook test suite over creating a
   new script. Keep any allowlist of already-safe sites short and commented.

## Acceptance Criteria

- [ ] Every location in Confirmed Reachable Instances uses the guarded idiom.
- [ ] No location in Confirmed Already Safe was modified.
- [ ] An empty `current_phase` yields `big plan has no current_phase`, not a shell error.
- [ ] Tests assert the guarded form at each fixed site and do not depend on the host Bash version.
- [ ] Gate decisions, severities, message text, and the protected-path inventory are unchanged.
- [ ] A regression check exists, or its absence is explicitly justified in the closeout.

## Verification

```bash
uv run pytest tests/ -q
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run ruff check shared scripts tests
uv run ruff format --check shared scripts tests
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run python .claude/scripts/verify.py phase --format json --persist
```

## Closeout Checklist

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record the three pause fields, and create a session log
with `**Status:** PAUSED`. Keep the big plan `in-progress` with the same
`current_phase`. On resume, read the pause log and Git state, restore this plan
to `in-progress`, and continue this same phase without creating another small
plan.
