# Session: Backlog follow-ups — Phase H, guard shell scanner

**Date:** 2026-10-21
**Plan:** .claude/plans/2026-10-21_phase-H-guard-shell-scanner.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** IN-PROGRESS

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
- [ ] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT — repeat until verification and review pass
- [ ] COMMIT
- [ ] PUSH

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

## [LEARN] Entries

To be written at closeout.

## Verification

To be written at closeout.

## Open Questions / Next Steps

- Phase I and Phase J follow.
