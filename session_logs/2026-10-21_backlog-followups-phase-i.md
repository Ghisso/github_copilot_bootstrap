# Session: Backlog follow-ups — Phase I, guard substitutions and restore messages

**Date:** 2026-10-21
**Plan:** .claude/plans/2026-10-21_phase-I-guard-substitutions-and-restore-messages.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** IN-PROGRESS

## Goal

Close the write paths the file-protection guard still misses after Phase H
(command substitution in double quotes and backticks, grouped operators,
inline `sed` writes, the `cd`-folder gap, and the R9 and R10 forms), close
the Phase H loosening exception, and make the OpenWiki restore messages say
the user runs them (BF-I1 to BF-I7).

## Task Tracking

- [x] PRE-FLIGHT: Phase H committed (`b0dc4c3`) and pushed; the commit hook
  advanced `current_phase` to this phase and set it `in-progress`. The user
  asked to continue to the end of the big plan. No planner.
- [ ] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT — repeat until verification and review pass
- [ ] COMMIT
- [ ] PUSH

## Work Log

- **Start** - Applying the Phase H lesson: the coder runs a sweep of every
  new construct under plain Bash, `bash --posix`, and dash before review,
  and adds each new shape class to the differential generators first.
- **Coder steps 1 to 3** - `extract_substitutions` now classifies `$( )`
  and backticks inside double quotes and unquoted backticks;
  `_matching_paren` is heredoc-aware; commit-message heredocs
  (`git commit|tag|merge -m "$(cat <<'EOF' ...)"`) are message text. `|&`
  is a pipe; `&>>`, `<>`, and `>&` with a word are write redirects (the
  five strict xfails now pass). New `sed_effects` reads `w`, `W`, `s///w`,
  and denies `e` and `s///e`. Unmodelled commands after `cd` resolve
  against every `cd` folder. BF-I7 and R10 forms handled (ANSI-C names,
  heredoc delimiters as whole words, same-line functions and aliases,
  `$IFS` and blank-valued variables split, names built around a
  substitution, arrays, globs glued to variables, parameter operations on
  tracked variables, `find -delete`/`-exec rm {} +`, fail-closed
  `dotglob` and zsh code-running qualifiers). The sweep and Bash oracle
  also found and fixed: brace lists in the command word (`{tee,.env}`),
  commands after `then`/`do`/`else`/`{`/`!`/`time`, and blank-valued
  variable splitting, all pre-existing. Restore messages reworded in
  `verify.py` and `openwiki-guard.py`, one failing-first test each. Sweep
  (`phase-i/phase-i-sweep.txt`): 544 snippets x 30 contexts = 16,320
  commands under plain Bash, `bash --posix`, and dash; gaps original guard
  5,367, Phase H 6,487, now 30, all one recorded gap (a `cd` into a folder
  computed at run time). Differential against the Phase H guard: 5,159
  looser commands, 0 under-protected under the three readings with plain
  and hidden stand-ins; of the 99 Phase H exception commands, 88 now
  blocked as required and 11 were stand-in artifacts (Bash writes nothing
  with a hidden stand-in). 589 cases agree with Bash; scanner against Bash
  30,000 commands, 0 disagreements; 3.9, 3.12, and 3.13 identical on 45,153
  commands; 285 new tests fail on the Phase H guard. Slowest pathological
  input 2.32 s (alarm 4 s). One test run while the guard had a bug
  appended a line to the ignored `hooks-errors.log`. Regenerated,
  self-installed; `validate_targets.py` and `check_runtime.py` PASS.
- **Docs (step 4)** - documenter: `docs/runtime-checks.md` shell-parsing
  block (new rules, over-blocks, the final not-yet-checked list) and the
  OpenWiki managed-state row's fix ("Ask the user to run ... in their own
  shell"); `docs/smoke-tests.md` `protect-files.sh` bullet;
  `docs/target-mapping.md` Phase I parity row and an updated caveat. The
  Phase G cited text in `docs/runtime-checks.md` is now at 747-779 (Phase J
  refreshes those claims). `verify.py phase` PASS (4365 passed, 1 skipped;
  no xfails left). Sent to a fresh reviewer with six profiles.
- **Review round 1** - Gate Result FAIL, 10 major and 5 minor. Sorted by
  origin. Introduced by Phase I (must fix): the commit-message heredoc
  exemption hides a write when piped into `sh`; the parameter-operation
  evaluator uses `fnmatch`, not Bash rules (`[^...]`, `[[:upper:]]`, `@E`);
  the dotglob and alias checks are raw-text regexes that quoting defeats;
  the `find` narrowing tests patterns against 14 sample names.
  Pre-existing and cheap to close: abbreviated `sed` long options, `sed 'e
  cmd'` not actually denied, `cd` with a glob, `pushd`, `env -C`,
  `CDPATH`, more shapes of names built around a substitution, and
  assignments that do not run (conditional, prefix, subshell, pipeline).
  To record as gaps unless cheap: whole-word command output as a name,
  names fed to `xargs`, `perl -e`, `git -c alias.x='!...'`,
  `rg --pre`. The reviewer's ponytail advice is taken: delete the
  evaluator (about 300 lines) and fail closed on operations over variables
  assigned on the same line. Also asked: re-check the original 261 Phase H
  exception commands, and make the NUL-byte case an explicit rule.

## [LEARN] Entries

To be written at closeout.

## Verification

To be written at closeout.

## Open Questions / Next Steps

- Phase J (final knowledge refresh) follows.
