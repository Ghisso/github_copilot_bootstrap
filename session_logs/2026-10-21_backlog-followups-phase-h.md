# Session: Backlog follow-ups — Phase H, guard shell scanner

**Date:** 2026-10-21
**Plan:** .claude/plans/2026-10-21_phase-H-guard-shell-scanner.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** COMPLETED

## Goal

Replace `shlex` in the file-protection guard with a scanner that reads
shell text as Bash does, so comments, blank lines, line-end operators, and
quoted or escaped operators no longer hide or split commands (BF-H1),
prove no decision loosened (BF-H2), and document it (BF-H3).

## Task Tracking

- [x] PRE-FLIGHT: Phase G committed (`abdefa1`) and pushed; the big plan
  reopened with Phases H, I, and J after the user's decisions
  (big plan "Decisions recorded" item 7). No planner: the plan was drafted
  by the orchestrator and challenged by a devil's-advocate subagent.
- [x] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT — repeat until verification and review pass
- [x] COMMIT
- [x] PUSH

## Work Log

- **Reopen** - The user asked for a plan to fix the guard defect found
  after Phase G and to do the two Phase G follow-ups. Probes of the
  classifier (command text only, never run) confirmed R1 and, after the
  devil's-advocate review, R5 to R8. Findings:
  `.claude/quality_reports/2026-10-21_backlog-followups-reopen-findings.md`.
  The user chose two code phases, a dedicated Bash scanner, and to keep
  secret-file Bash reads as a follow-up.
- **Coder round 1 (steps 1 and 2)** - `shlex` removed from
  `protect-files.py`; one quote scanner (`_skip_literal`, `_read_word`,
  `_shell_tokens`) now serves `split_segments`, `_matching_paren`,
  `_find_unquoted_heredoc`, and `extract_process_substitutions`; the
  quoted-variable rewrite in `protect_quoted_globs` no longer strips quotes
  around operators or spaces. 126 new tests in
  `tests/test_protect_files_scoping.py` (83 fail on the old guard; the rest
  are keep-today cases), two installed-hook smoke cases in
  `scripts/validate_targets.py`. Added beyond the plan: a step cap and cache
  on `_matching_paren` (nested `"$(` took exponential time and could
  outlast the hook timeout), and fail-closed on `#` right after `)`.
  All 86 cases agree with Bash's own reading; a 60,000-command scanner
  check against Bash had 0 disagreements; Python 3.9 and 3.13 decisions
  are identical on 23,344 inputs. Differential: 0 under-protected looser
  results in every set except the structured fuzz, which had 261 (each with
  a backtick, `$(` in double quotes, a grouped operator, or a glued quoted
  variable that the old guard blocked only by accident). The user accepted
  those until Phase I (big plan "Decisions recorded" item 8); R9 added.
- **Coder round 2** - asked for three scanner fixes: longest-match
  operator runs (`cat x;(tee .env)` was allowed), an operator right after
  `)` (`echo $(date) && ls` was exit 2), and a `)` on its own line. Done
  with tests first: 191 Phase H tests, 118 fail on the old guard and 41
  (the three fixes' own) on the round 1 guard; 128 cases agree with Bash;
  another 60,000-command scanner check had 0 disagreements. Differential:
  under-protected looser results fell from 261 to 159, all in the accepted
  classes (backtick 151, grouped operator 5, glued quoted variable 2, `$(`
  in double quotes 1); 0 in every other set; substitution set 0
  mismatches over 287,072 inputs. Invalid punctuation such as `;|` or `))`
  now fails closed.
- **Install and checks** - regenerated, self-installed;
  `validate_targets.py` and `check_runtime.py` PASS. The live guard now
  allows `printf 'x|y\n' | grep '|' | head -1` and a multi-line read-only
  command with a `#` comment and a blank line (optional verification 2).
  `verify.py phase` PASS (3461 passed, 1 skipped).
- **Docs (step 3)** - documenter, before review so one review covers code
  and docs: `docs/runtime-checks.md` (scanner rules added on line 261, no
  line shift, cited lines 678-710 unchanged), `docs/smoke-tests.md` (one
  bullet), `docs/target-mapping.md` (parity row and the secret-read
  follow-up; the wiki claim range L88-L135 shifts and is left to Phase J).
  No statement in `README.md`, `docs/architecture.md`, or the policies
  needed a change.
- **Review round 1** (fresh reviewer, six profiles): Gate Result FAIL, 6
  major and 8 minor. Confirmed by the orchestrator with the full hook
  (old against new): `tee $((1)) .env` and `tee $(echo $(date)) .env`
  went from deny to allow (words after the `)` of an unquoted `$( )`
  became an unchecked command name); `rm $(git rev-parse
  --show-toplevel)/.env`, `echo x > $(pwd)/.env`, `tee $(true) .env`, a
  carriage return before `#`, `tee "$X(" cat .env`, and `tee $".env"` were
  allowed by both guards. A crafted 100 KB input failed closed in 4.0 s,
  close to the 10 s hook timeout. Other majors: the differential never
  generated these shapes, and `docs/runtime-checks.md` stated absolute
  rules the code did not meet. Sent all majors and minors 7, 10 to 13 back
  to the coder; docs to be redone after. Pre-existing gaps the review
  listed as information (shell functions or aliases, `$IFS` splitting,
  heredoc delimiters read short) were added to Phase I.
- **Coder review fixes** - unquoted `$( )` and `$(( ))` are now part of
  their word (`extract_substitutions`, inner command classified
  recursively; a substitution glued to a name counts as empty, so
  `tee .env$(true)` is denied); `\r` is a word character; the
  context-blind `protect_quoted_globs` rewrite is deleted and the scanner
  marks quoted glob, brace, and variable text itself (`rm 'credentials*'`
  is now an over-block); `$"..."` is read as `"..."`; one work budget per
  command replaces the step cap and cache (the reviewer's 100 KB input now
  fails closed in about 0.03 s; the worst crafted input 0.77 s on 3.9);
  `_skip_double_quoted` split out; tests use `match=`, budget assertions,
  and `xfail(strict=True)` for the grouped-operator cases Phase I flips.
  169 cases agree with Bash; 60,000 more scanner commands, 0
  disagreements; 3.9, 3.12, and 3.13 decisions identical. Differential with
  a new grammar set for the review's shapes: the 169 under-protected
  looser commands reduce, by a minimiser, to 125 minimal causes, each in
  an accepted class; nothing else. The coder also found a pre-existing
  timeout fail-open: the `.pem`/`.key` alternative of
  `PROTECTED_PATH_LITERAL` is quadratic (80 KB word 8 s, 160 KB over 30 s;
  the hook timeout is 10 s). Asked the coder to apply its linear form in
  this phase.
- **Long-word timeout fix** - the coder rejected the suggested regex
  (other alternatives stay quadratic; it would also loosen
  `/foreign/.claude/settings.json,x.pem`). Instead `protected_path_literals`
  reads word by word: words up to `LONG_WORD = 512` go to the unchanged
  regex; a longer word with no protected name (`PROTECTED_NAME`) is
  skipped; a longer word with one fails closed. A process alarm
  (`CLASSIFIER_SECONDS = 4`, default action, so it also works on 3.9)
  ends any other slow classification as a denial, before the 10 s hook
  timeout. The `QUOTED_MAGIC` brace part no longer backtracks. 200 KB
  words: 51 s or more before, about 0.005 s after. Literal lists identical
  on 1,202,329 texts; no decision changed on 131,666 commands. Regenerated,
  self-installed; `validate_targets.py` and `check_runtime.py` PASS.
  Documenter asked to redo the docs for review findings 6 and 14 and the
  new behavior.
- **Docs second pass** - `docs/runtime-checks.md` shell-parsing text split
  into short lines (261-285) with no absolute wording, a "not yet checked"
  list, the new behavior, and the fail-closed messages; its cited text
  moved from 678-710 to 702-734 (Phase J refreshes those claims).
  `docs/target-mapping.md` parity row now carries a caveat, and "No earlier
  decision was loosened" is scoped to the agent-definition rows with a note
  on the deliberate loosening. `verify.py phase` PASS (3573 passed, 1
  skipped, 5 xfailed).
- **Review round 2** - Gate Result WARN: every round-1 finding fixed, no
  critical or major; six minor findings and two open requests. The
  orchestrator confirmed finding 1 with Bash (`a=(x)#c; echo RAN` prints
  `RAN`, so `#` after an array assignment's `)` is not a comment). Sent all
  six minors back to the coder: array-assignment `#`, unquoted variables
  glued to a protected name (`tee .env$X`), forcing `SIGALRM` to its
  default before the alarm, restoring the old allow for quoted search
  patterns (`find . -name '*.pem'`), and tests for substitution
  placeholders in `cd` and `git -C` operands; docs to follow.
- **Coder round 2 fixes** - array assignments are one word and `)#` after
  one fails closed; unresolved `$NAME`/`${NAME}` is stripped with
  substitution placeholders in the bare-name checks (`tee .env$X` denied;
  `cat .env$X` still a read); `SIGALRM` reset to its default before the
  alarm (a test runs a child with `SIGALRM` ignored); a word that is
  exactly one quoted glob or brace pattern gets `QUOTED_PATTERN_PREFIX` and
  is skipped by the unknown-command scan, restoring the old allow for
  `find . -name '*.pem'` and `ls '*.key'` (`rm 'credentials*'` and
  `git add '*.pem'` stay denied). 197 cases agree with Bash; scoping tests
  512 passed and 5 xfailed; 3.9, 3.12, and 3.13 decisions identical on
  28,892 commands. Differential against the round-1 guard: every looser
  result comes from the pattern skip or the array rule (checked by
  switching each off); against HEAD, the 124 under-protected looser fuzz
  commands reduce to 95 minimal causes, all in the accepted classes or a
  stand-in artifact (`*` matching the stand-in but never a leading-dot
  `.env`). The `minimal-reproducers.txt` "no class" entry was relabelled as
  a glued quoted variable joined by a line continuation. More pre-existing
  gaps (a name built by a command, array elements, a glob glued to a
  variable, `find -delete`) were added to Phase I. Regenerated,
  self-installed; `validate_targets.py` and `check_runtime.py` PASS.
- **Docs third pass** - "Ordinary commands are very unlikely to be
  affected"; the not-yet-checked list matches the coder's final list; rule
  lines for arrays, unset glued variables, and quoted patterns; one
  over-block sentence. `verify.py phase` PASS (3669 passed, 1 skipped, 5
  xfailed). `MEMORY.md` `[LEARN:tooling]` `protect-files.sh` entry corrected
  (plan step 4).
- **Review round 3** - Gate Result FAIL on one major: a `case` statement
  inside an unquoted `$( )` closes the substitution at the pattern's `)`,
  so `cat $(case a in a) tee .env;; esac)`, the `git status` form, and the
  array form went from deny (HEAD) to allow. Confirmed by the orchestrator
  with the full hook and Bash (a stand-in prints `RAN`). Minor: the
  quoted-pattern exemption covered interpreters and brace lists
  (`bash -c '{rm,.env}'`, allowed at HEAD too), a misplaced comment, a
  thin margin on the alarm tests, and docs. All sent to the coder.
- **Coder round 3 fixes** - `_refuse_case_statement` fails closed on an
  unquoted word `case` inside an unquoted `$( )`, `<( )`, or `>( )`, also
  for substitutions inside unquoted heredoc bodies (a hole the coder found:
  `cat <<EOF` with `$(case ...)` was allowed); top-level and group `case`
  are read normally. Brace lists are no longer quoted patterns, and the
  pattern exemption skips a new `RUNNERS` set (shells, interpreters,
  wrappers such as `eval`, `xargs`, `timeout`). Alarm tests use 60,000
  `open(` (24.7 to 29.3 s without the alarm, at least 6x the 4 s alarm).
  220 cases agree with Bash; 3.9, 3.12, and 3.13 decisions identical on
  29,450 commands. Differential against the round-2 guard: 0 looser in
  every set. Against HEAD: 73 under-protected looser commands, 67 minimal
  causes, all accepted classes or the stand-in artifact; in a new set of
  4,068 `case` commands, every write Bash performs is blocked. Over-blocks:
  `echo $(grep -c case README.md)`, `find . -name '{a,b}.pem'`, and runner
  forms such as `bash -c '*.pem'`. Phase I gained a must-allow case so the
  `case` refusal never reaches quoted heredoc bodies in commit messages.
  Regenerated, self-installed; `validate_targets.py` and `check_runtime.py`
  PASS.
- **Docs fourth pass** - pattern, runner, and `case` rule lines and the
  over-block sentence; cited wiki text now at 725-757. `verify.py phase`
  PASS (3753 passed, 1 skipped, 5 xfailed).
- **Review round 4** - Gate Result FAIL on one major with the same root
  cause as round 3: a `)` inside `${ }` closes an unquoted `$( )` early, so
  `cat $(tee ${x//)/} .env)`, the `git status` form, and `x=$(tee ${x:-)}
  .env)` went from deny (HEAD) to allow. Confirmed with the full hook and
  Bash. Asked the coder for the principled fix (a `${ }` span read as one
  unit everywhere the scanner skips literals) and a systematic sweep of
  every Bash construct that can hold an unbalanced parenthesis, each
  checked against real Bash, so later rounds stop finding one instance at
  a time.
- **Coder round 4 fixes** - new `_matching_brace` reads `${ }` the way
  Bash 5.2 does; `_skip_literal`, `_skip_double_quoted`,
  `_matching_paren` (now also skipping backticks), `extract_substitutions`,
  and `_read_word` all treat `${ }` and `$$` as units; extended globs are
  one word and fail closed in a write operand; `protected()` and
  `protected_path_literals()` also check text with each `${ }` removed and
  with `${NAME:-word}` replaced by its word. This closed
  `echo ${x:- #}; tee .env` and `tee ${x:-.env}`, which moved out of
  Phase I. Sweep (`paren-sweep.txt`): 186 snippets in 13 contexts, 2,418
  commands run in Bash 5.2; writes the guard missed fell from 134 (HEAD)
  and 97 (round 3) to 0, apart from the accepted classes. 266 cases agree
  with Bash; 30,000 more scanner commands, 0 disagreements; 3.9, 3.12, and
  3.13 identical on 29,931 commands. Differential against round 3: every
  looser result that writes is a backtick body or the stand-in artifact;
  against HEAD: 89 under-protected, 66 minimal causes, all accepted
  classes. Regenerated, self-installed; `validate_targets.py` and
  `check_runtime.py` PASS.
- **Docs fifth pass** - `${ }` rules, default words, extended globs, the
  final not-yet-checked list, and over-blocks; cited wiki text at 728-760.
  `verify.py phase` PASS (3882 passed, 1 skipped, 5 xfailed).
- **Review round 5** - Gate Result FAIL on one major: `_matching_brace`
  reads a `'` inside a double-quoted `${ }` as a quote, so
  `cat "${x:-'}" ; tee .env ; echo "'}"` became one word and was allowed
  (HEAD denied it). The orchestrator's check: plain Bash 5.2 does not run
  the middle command (the guard matches it), but `bash --posix` and dash
  do. Since shells disagree, the coder is to fail closed on `'` or `$'`
  inside a double-quoted `${ }`, sweep those forms under plain Bash,
  `bash --posix`, and dash, rerun the whole sweep under the two POSIX
  readings, and split `_read_word`. New finding R10 (shell model): zsh
  glob qualifiers that run code (`cat *(e:'touch .env':)`, allowed before
  and after) go to Phase I.
- **Coder round 5 fixes** - `_matching_brace` takes `in_double_quotes`
  and fails closed on `'` or `$'` inside a double-quoted `${ }` ("read
  differently by Bash and by POSIX shells"); `_read_word` split into
  `_read_group_word`, `_quoted_part`, and `_mark_quoted_word` (with the fix
  switched off, decisions identical to round 4 on 246,000 inputs). The
  sweep now runs every command under plain Bash, `bash --posix`, and dash:
  3,228 commands, 2,252 written by some reading; gaps HEAD 142, round 4
  72, now 0 outside the accepted classes. The new 810-command group
  (quotes in double-quoted `${ }` for 15 operators) fails closed in full.
  Outside that group, POSIX readings add only dash-only forms the guard
  already denies. 277 cases hold under the union of the three readings;
  differential against round 4: 0 looser in every set; against HEAD, 99
  commands some reading writes and the guard allows, 77 minimal causes,
  all accepted classes. Regenerated, self-installed;
  `validate_targets.py` and `check_runtime.py` PASS.

## Review

- Six rounds by one reviewer (profiles code, architecture, security,
  tests, ponytail, documentation). Rounds 1 to 5 failed or warned, each
  on a shape the differential had not generated: words after `$( )`, then
  minor items, then `case` inside `$( )`, then `)` inside `${ }`, then a
  quote inside a double-quoted `${ }` that POSIX shells read differently.
  Round 6: Gate Result PASS, 0 critical, 0 major, 1 minor (a docs sentence
  claimed more than the sweep shows), fixed by the orchestrator: "For the
  forms its tests check, where Bash and POSIX `sh` read the same text
  differently, the guard either denies or fails closed."
- Every finding the orchestrator could reproduce was checked with the full
  hook (old against new) and with real shells before it went back to the
  coder.

## Requirement Evidence

| ID | Outcome | Evidence |
| --- | --- | --- |
| BF-H1 | Done | `tests/test_protect_files_scoping.py` (753 passed, 5 xfailed; new cases fail on the earlier guards); 277 cases agree with plain Bash, `bash --posix`, and dash; scanner against Bash, 30,000 random commands per round, 0 disagreements; `paren-sweep.txt`, 3,228 commands under three readings, 0 gaps outside the accepted classes |
| BF-H2 | Done, with the accepted exception (big plan item 8) | Differential against HEAD: 99 commands that some reading writes and the guard allows, 77 minimal causes, all backtick, grouped operator, `$(` in double quotes, or the stand-in artifact; against the round-4 guard, 0 looser in every set; substitution set, 0 differences over 432,852 inputs |
| BF-H3 | Done | `docs/runtime-checks.md` shell-parsing block, `docs/smoke-tests.md` bullet, `docs/target-mapping.md` parity row with caveat and the secret-read follow-up |

## [LEARN] Entries

- [LEARN:review] A guard that parses shell text needs a sweep of every
  construct that can hold an unbalanced delimiter, run through real
  shells, before review. Here reviewers found one instance per round
  (`case`, `${ }`, a quote in a double-quoted `${ }`) until a sweep of 186
  snippets in 13 contexts under three readings ended it (saved to
  `MEMORY.md`).
- [LEARN:security] A differential check proves only what its generators
  produce. When a review finds a new shape, add that shape class to the
  generator and the substitution set first, then fix (saved to
  `MEMORY.md`).
- [LEARN:tooling] A hook whose timeout lets the command through must bound
  its own time: a `signal.alarm` with `SIG_DFL` set first ends the process
  even inside a regex on Python 3.9, where a Python handler does not run
  until the regex returns (saved to `MEMORY.md`).

## Verification

Optional items:

- optional 1: PASS
- Differential recorded each round in the session scratch folder
  (`phase-h/diff-*`, `prev*-vs-new*`), with input counts per set, changes
  by direction, and every looser change with Bash's reading; summaries are
  in the Work Log and Requirement Evidence above.
- optional 2: PASS
- Claude Code in this repository with the final installed guard ran
  `printf 'x|y\n' | grep '|' | head -1` and a multi-line command with a
  `#` comment line and a blank line; both were allowed.

Required items (summary lines from `verify.py closeout`):

```text
PASS        0.3s  uv run python scripts/generate_targets.py --all
PASS       44.9s  uv run python scripts/validate_targets.py
PASS      139.8s  uv run pytest tests/test_hook_gates.py tests/test_protect_files_scoping.py tests/test_validate_targets.py tests/test_lifecycle_hooks.py -q
PASS        0.9s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS        0.2s  uv run python .claude/scripts/verify.py fast --format json
closeout: PASS
VFY-FRESH-001: PASS - phase evidence matches relevant state
VFY-FRESH-002: PASS - phase evidence matches governing control-plane provenance
VFY-RECEIPT-001: PASS - reused successful phase receipt
```

Findings recorded: 1 finding (0 critical, 0 major, 1 minor, fixed);
`ponytail_reviewed=true`; `gate_result=PASS`
(`.claude/quality_reports/findings-2026-10-21_phase-H-guard-shell-scanner.json`).

## Open Questions / Next Steps

- Phase I and Phase J follow.
- Phase I carries the accepted exception classes, R9, R10 (zsh glob
  qualifiers that run code), and the must-allow commit-message case.
