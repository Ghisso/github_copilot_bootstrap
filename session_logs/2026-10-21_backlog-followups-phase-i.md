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
- **Coder round 1 fixes** - every item reproduced first (116 cases under
  three readings: 40 bypasses, 22 failed expectations before; 0 and 0
  after, 3 recorded gaps). Commit-message exemption only for a lone `cat`
  heredoc; evaluator deleted (operations, subscripts, indirection, and
  arrays on same-line variables fail closed); `shopt`/`setopt`/`set`/
  `alias`/`GLOBIGNORE=`/`CDPATH=` read from scanned words; `find` patterns
  instantiated, `-path`/`-regex` never narrow; GNU `getopt` prefixes for
  `sed`, and `sed` `e` fails closed; `cd` operands expanded, `pushd`,
  `popd`, `builtin cd`, `env -C`, and `bash -c`/`sh -c`/`eval` scripts
  followed; names continuing `.env.`/`credentials` around a substitution
  flagged; earlier variable values kept and all checked; `perl`, `git -c`,
  and `rg --pre` read as runners; NUL bytes cut or refused explicitly.
  Test file renamed to `tests/test_protect_files_substitutions.py`.
  Removed about 230 lines (evaluator, arrays, find samples); the file is
  3,390 lines. All 261 original Phase H exception commands re-run: 257
  denied on every client, 4 config writes at ask/deny, 0 defects. Sweep:
  668 snippets x 30 contexts = 20,040 commands; gaps original 7,304, Phase
  H 8,712, now 114 (the computed `cd` folder and whole-word or `xargs`-fed
  names, all recorded). Differential vs Phase H: 5,175 looser, 0
  under-protected; vs round 1: 655 looser, 0 defects. 589 Bash cases hold;
  scanner vs Bash 30,000, 0 disagreements; 3.9, 3.12, and 3.13 identical
  on 45,284 commands; slowest input 2.49 s. Regenerated, self-installed;
  `validate_targets.py` and `check_runtime.py` PASS. Docs second pass
  started.
- **Docs second pass** - evaluator text removed; new rules, over-blocks,
  and the final not-yet-checked list; the parity row cites the renamed
  test file; the caveat says some commands are looser by design. Phase G
  cited text now at 762-794. `verify.py phase` PASS (4532 passed, 1
  skipped).
- **Review round 2** (same reviewer, with the plan's acceptance bar:
  pre-existing gaps that the docs list are minor) - Gate Result FAIL, 5
  major and 5 minor. A copy of a variable after a conditional
  reassignment loses the earlier value (`x=.env; false && x=safe; y=$x;
  tee "$y"`); a self-referencing default (`PORT=${PORT:-8080} ./run.sh`,
  `export PATH="${PATH:-/usr/bin}:/opt/bin"`) was refused, and the coder
  had edited two existing tests to hide it; the `perl` scan was skipped
  when any option held the letter `i`; `bash -O dotglob` was missed and
  `eval` scripts were read in a copy of the shell state; and the docs had
  a stale clause and four missing gaps. Sent back with the reviewer's
  simpler rule: delete the earlier-values mechanism and fail closed on a
  second, different assignment to a tracked name. Scope change recorded:
  reading `bash -c`, `sh -c`, and `eval` scripts as command lines (added
  by the coder in round 1, beyond the plan's list) is kept, because it
  closes `bash -c 'cd .claude && tee settings.json'`.
- **Coder round 2 fixes** - 57 new probe cases reproduced first (9
  bypasses, 17 failed expectations, including one `eval 'alias'`
  regression from round 1); now 183 cases, 0 and 0, 7 recorded gaps.
  Earlier-values mechanism deleted; a second, different assignment to a
  tracked name fails closed ("assigned twice"); an assignment's value is
  read before the name is marked, so `PORT=${PORT:-8080}` and
  `export PATH="${PATH:-/usr/bin}:..."` are allowed again; the two edited
  scoping tests are restored and pass for the right reason. `perl` flag
  clusters parsed and script text always scanned; `bash -O dotglob` and
  `zsh -o glob_dots` fail closed; `eval` read in the current shell;
  wrappers matched by base name; any command's `-C`/`--chdir`/
  `--directory` adds a folder; `git notes add -m` and `git stash push -m`
  join the message exemption. File now 3,437 lines. Sweep: 727 snippets x
  30 = 21,810 commands; gaps original 8,004, Phase H 9,517, now 234, all
  recorded (computed `cd`, whole-word and `xargs` names, loop variables,
  one-character tails). Differential vs Phase H: 0 under-protected; vs
  round 2: 293 looser, none writes. Bash cases, scanner oracle, and the
  three Python versions all agree. New over-block to raise with the user:
  counters (`i=$((i+1))`) and `if`/`else` branches that set one name both
  ways now fail closed. Regenerated, self-installed;
  `validate_targets.py` and `check_runtime.py` PASS. Docs third pass
  started.
- **Docs third pass** - the "assigned twice" rule replaces the
  earlier-values text; perl, `eval`/`bash -c`, wrappers, folder options,
  fail-closed limits, over-blocks, and the not-yet-checked list updated;
  the `docs/target-mapping.md` caveat lists the allowed mention contexts,
  and a new recorded follow-up asks to split or shrink the 3,400-line
  hook. Phase G cited text now at 773-805. `verify.py phase` PASS (4628
  passed, 1 skipped). Review round 3 requested.
- **Review round 3** - Gate Result FAIL, 2 major and 1 minor; every
  round-2 item verified fixed and nothing looser than Phase H. A bare
  assignment whose value holds a default or unresolved expansion was not
  tracked (`y=${z:-.env}; tee "$y"` allowed while the direct form is
  denied); the docs said `time` is not unwrapped (it is) and missed other
  unwrapped runners, a variable read when a same-line function is called,
  and a heredoc run by `source`; an in-place `perl` edit of a config now
  denied everywhere instead of asking like `sed -i`. Code items sent to the
  coder; docs to follow.
- **Coder round 3 fixes** - `_protected_candidate` tracks an assignment
  value with a default or unresolved expansion when a candidate names a
  protected file (`y=${z:-.env}; tee "$y"` denied; `PORT=${PORT:-8080}`
  allowed). `_perl_command_line` replaces `_perl_in_place`: with `-i` the
  file operands are confirmed write targets (config edits ask on Claude
  Code and Copilot, deny on Codex and Antigravity, like `sed -i`) and only
  the `-e`/`-E`/`-M`/`-m` text is scanned. Orchestrator decision: accept
  the coder's deviation to keep scanning every operand without `-i`,
  because a perl program can write to a file it only gets as an argument
  (`perl -e 'open(F,">",$ARGV[0]) ...' victim.txt` writes it); the
  over-block `perl -ne 'print' .env` is recorded. `source`/`.` of
  `/dev/stdin` (and `/dev/fd/0`, `/proc/self/fd/0`) with a heredoc,
  `source <(cat <<'EOF' ...)`, and `eval "$(cat <<'EOF' ...)"` are read in
  the current shell. Recorded gaps: a variable read when a same-line
  function is called, and `source`/`eval` of text another command prints.
  217 probe cases, 0 bypass; sweep gaps 291, all recorded; differential vs
  Phase H 0 under-protected, vs round 3 56 looser (all perl in-place
  config edits now ask/deny); Bash cases, scanner oracle, three Python
  versions agree. Regenerated, self-installed; `validate_targets.py` and
  `check_runtime.py` PASS. Docs fourth pass started.
- **Docs fourth pass** - assignment-default tracking, the perl `-i`
  rules, the `source`/`eval` heredoc line, the corrected wrapper item
  (`time` is followed), new over-blocks, and two recorded gaps. Phase G
  cited text now at 779-811. `verify.py phase` PASS (4727 passed, 1
  skipped). Review round 4 requested.
- **Review round 4** - Gate Result FAIL, 3 major (all pre-existing and
  cheap, or docs) and 1 minor; nothing looser than Phase H. Assignment
  tracking read the raw value, so fragments and chained unresolved
  expansions lost the name (`y=${z:-.e}; tee "${y}nv"`); a heredoc-fed
  shell was read only when spelled `bash`/`sh`/`zsh` (`/bin/bash`, `dash`,
  `bash /dev/stdin` missed); the docs did not list a script fed to a shell
  by a here-string or a pipe; the follow-up bullet's line count drifted.
  To stop finding one spelling per round, the coder also runs a
  systematic command-spelling sweep (full paths, quoted and escaped
  names, `command`/`builtin`/`env`/`exec`, a variable holding the name)
  for every command the guard treats specially.
- **User decision (2026-10-22)** - "we don't need to be so exhaustive":
  from review round 5, Phase I's gate blocks only on a decision looser
  than Phase H, a hole Phase I introduced, or a false or missing docs
  statement about what is checked. Any other pre-existing gap goes to the
  docs' not-yet-checked list and the recorded follow-up to split the hook.
- **Coder round 4 fixes** - assignment values read after substitution,
  with fragment defaults kept (`MAYBE_KEY`, ignored by "assigned twice");
  shells fed by a heredoc, a here-string, or a pipe from literal
  `echo`/`printf`/`cat <<` read as child-shell scripts in any spelling
  and behind runners that start a shell (`PREFIX_RUNNERS`); a command name
  held in a variable is re-read. Spelling sweep (`spelling-sweep.txt`): 69
  names x 24 spellings = 4,249 rows; 600 under-protected rows on the
  round-4 guard, 0 now. 321 probe cases, 0 bypass; sweep 40,620 runs, 381
  gaps, all recorded; differential vs Phase H 0 under-protected, vs round
  4 189 looser (variable-held read-only commands now allowed like the
  plain name, config writes now ask/deny), 0 under-protected. Bash cases,
  scanner oracle, and the three Python versions agree; slowest 2.27 s.
  Regenerated, self-installed; `validate_targets.py` and
  `check_runtime.py` PASS. Docs fifth pass started.

## [LEARN] Entries

To be written at closeout.

## Verification

To be written at closeout.

## Open Questions / Next Steps

- Phase J (final knowledge refresh) follows.
