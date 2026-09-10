# Consumer Lifecycle Friction Hardening — Phase B2 Closeout

**Status:** COMPLETED
**Plan:** `.claude/plans/2026-09-11_phase-B2-hook-empty-array-safety.md`
**Branch:** `consumer-lifecycle-friction-hardening_implementation`
**Started:** 2026-09-11

## Goal

Make every reachable empty-array expansion in the lifecycle hook scripts safe
on the declared Bash 3.2 orchestration baseline, so a gate reports its intended
diagnostic instead of aborting with an unbound-variable error.

## Completed phase

Phase B2: `.claude/plans/2026-09-11_phase-B2-hook-empty-array-safety.md`

This phase was added to the big plan during Phase B, at the user's request,
after another agent using this bootstrap reported the defect. It was inserted
after Phase B and before Phase C rather than folded into Phase B, because it is
unrelated control-plane work and Phase C edits the same frontmatter library.

## Origin and corrections to the original report

The report was verified against source before any work started. Three parts of
its framing were wrong and are recorded so the fix is not justified by a wrong
premise:

- No gate message instructs an operator to clear `current_phase` after the last
  phase. An empty `current_phase` is itself a gate failure. The defect masks
  that failure rather than arising from following gate advice.
- The branch was not affected at the time of the report. Its big plan had a
  valid `current_phase` and a populated `phases` list.
- The defect cannot be reproduced on this machine, which runs Bash 5.2.
  `BASH_COMPAT=3.2` does not restore the Bash 3.2 behavior. Confirmation is by
  code reading plus the repository's declared baseline.

The reported line was one instance of an inconsistently applied idiom.
`git-protection.sh:104` already used the guarded form while line 105 did not.

## Work log

- Swept every array expansion under `shared/hooks/` and classified each by
  whether a preceding emptiness guard exists. Seven were reachable while empty;
  ten were already guarded and deliberately left alone.
- Applied the repository's existing `${arr[@]+"${arr[@]}"}` idiom at the seven
  reachable sites in `_lib-frontmatter.sh` and `git-protection.sh`.
- Traced `reporting-reminder.sh`'s `options` array and confirmed it is always
  non-empty, so it was left unchanged.
- Added `unguarded_array_expansion_errors()` to `scripts/check_runtime.py`, a
  source-level scanner that masks the guarded idiom before scanning, so the
  guard's own inner quoted text does not produce a false positive.
- Review round 1 returned a PASS gate with three minor findings. The security
  analysis confirmed element integrity, absence of pathname expansion,
  empty-string survival, unchanged tokenization, and, at each of the seven
  sites individually, that zero iterations is the correct safe outcome rather
  than a downgrade from a fail-closed abort.
- Two minor findings were fixed and one accepted. The scanner was widened from
  the quoted `@`-subscript form to the full shape class, and the Bash 3.2
  constraints paragraph in `docs/runtime-checks.md` was corrected.
- Widening the scanner surfaced two sites the original review never examined,
  both in `reporting-reminder.sh`. Line 63 was genuinely reachable if misused
  and was guarded. Line 74 is provably safe through cross-function control flow
  and was allowlisted with that reasoning recorded.
- Review round 2 confirmed both fixed findings resolved, independently verified
  the cross-function safety claim, independently swept `shared/hooks/` and found
  no unaccounted site, and returned a PASS gate.

## Evidence resolved during review

The reviewer was uncertain whether a fully unquoted `${arr[@]}` shares the
defect. A primary source settles it: Chet Ramey, the Bash maintainer, on
`bug-bash@gnu.org` (2019-05-13, "set -u and empty arrays"), reproduces with
`declare -a INSTANCES; echo ${INSTANCES[*]}` yielding
`bash: INSTANCES[*]: unbound variable`, and quotes the bash-4.4 CHANGES entry:
"Using `${a[@]}` or `${a[*]}` with an array without any assigned elements when
the nounset option is enabled no longer throws an unbound variable error."
Both reproduction commands are unquoted, so quoting is irrelevant to this bug;
the set check precedes word splitting and quote removal.

For the indices form `${!arr[@]}` no equally direct primary source was found.
It is covered anyway, because this repository already guards a bare
`${!phases[@]}` at `record-commit-closeout.sh:101,104`, and guarding costs
nothing if the shape is not vulnerable while missing a real one is costlier.

## Verification state

- `uv run pytest tests/ -q`: 1334 passed.
- `scripts/check_runtime.py`: 0 failed, including the new
  `PASS hook scripts guard empty-array expansions for Bash 3.2`.
- `scripts/validate_targets.py`: generated target structurally valid.
- Ruff check, Ruff format check, and Mypy passed for `shared scripts tests`.
- `scripts/validate_plan_frontmatter.py` passed.

## Review outcome

Two review rounds, each running the `code`, `architecture`, `security`,
`tests`, `ponytail`, and `documentation` profiles over two sequential passes.
Final gate: PASS, with no surviving critical or major finding.

One minor finding was accepted rather than fixed: the scanner's allowlist is
keyed on exact source-line text and does not re-verify that each entry's
claimed preceding guard is still present. Verifying that would require parsing
shell control flow, which is the over-engineering the plan forbids. The
disposition explicitly notes that the twelfth entry, `reporting-reminder.sh:74`,
is justified by cross-function control flow rather than a local guard, which is
a weaker justification class than the other eleven. That claim was independently
verified to hold today.

## Documentation

`docs/runtime-checks.md`'s Bash 3.2 constraints paragraph previously listed
only bash-4-only builtins, associative arrays, and negative array indices. It
now also names the empty-array pitfall, the guarded idiom, and the new check.
No dedicated entry was added for the check function itself, consistent with its
sibling check functions.

## [LEARN] Entries

- [LEARN:runtime] This repository declares Bash 3.2 as the orchestration
  baseline, so under `set -u` every reachable empty-array expansion needs the
  `${arr[@]+"${arr[@]}"}` idiom. A modern host cannot reproduce the failure and
  `BASH_COMPAT=3.2` does not restore it, so this defect class must be found by
  reading and pinned by asserting the guarded form in source.
- [LEARN:review] When a reported defect is one instance of an idiom applied
  inconsistently, sweep the whole class before fixing the reported line. Here
  the report named one line; the sweep found seven, and widening the resulting
  regression check surfaced an eighth the review had never examined.
- [LEARN:review] Replacing an abort with a silent zero-iteration loop is not
  automatically safe. An abort under `set -e` is fail-closed; a clean skip may
  be fail-open. Decide per site whether zero iterations is correct rather than
  assuming the guard is always an improvement.
- [LEARN:quality] A regression check that claims to prevent a defect class must
  cover the class, not one syntactic shape of it. Widening this scanner from
  the quoted `@`-subscript form to the full shape class immediately found a
  real unguarded site that the narrower form could not see.
