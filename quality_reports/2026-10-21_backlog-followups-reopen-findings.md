# Backlog follow-ups: findings that reopen the big plan

Date: 2026-10-21
Branch: `backlog-followups_implementation` at `abdefa1` (Phase G, the
plan's last phase, complete and pushed)
Big plan: [backlog-followups](../plans/backlog-followups.md)

## Why the plan reopens

After Phase G closed, a read-only search command was denied by the
file-protection hook. Tracing that denial found a parsing defect in
`shared/hooks/scripts/protect-files.py` that also lets some writes to
protected files through. On 2026-10-21 the user asked for a plan that
fixes it and does the two follow-ups the Phase G closeout log recorded
("Open Questions / Next Steps"). The branch is not merged, so the big
plan reopens with Phase H (fixes) and Phase I (the required final
knowledge refresh).

## Completed phases

Phases A to G are complete, each with one commit, PASS review gates, and
zero critical or major findings (`findings-2026-10-20_phase-*.json`). No
completed phase is reopened; the defect in R1 predates this plan.

## Findings

### R1 - MAJOR (security): a quoted or escaped shell operator splits one command into two

`split_segments` tokenizes with `shlex.shlex(..., posix=True,
punctuation_chars=";&|<>()")`. In POSIX mode the lexer removes quotes and
backslashes, so a quoted `'|'`, `";"`, `'&&'`, `'('`, `'&'`, an escaped
`\|` or `\;`, or a quoted line break (which the function turns into `;`
before lexing) comes out as the same token as a real operator. The guard
then splits one command into two segments. A mutating command's later
operands are read as a separate command, and when that command is on the
read-only list, the guard reports no target.

Real Bash passes these characters to the command as ordinary arguments.
`tee '|' cat .env` writes the files `|`, `cat`, and `.env`.

Classifier-only probe (the commands were never run; `shell_targets()` and
the full `protect-files.py` decision were called with the text):

- `tee '|' cat .env`: no target, and the hook allows it. Correct: `.env`
  is a write target, so deny.
- The same with `';'`, `'&&'`, `'||'`, `'&'`, `'('`, `"|"`, or `'|''|'`
  in place of `'|'`: no target. Correct: `.env` is a write target.
- `tee \| cat .env` and `tee \; cat .env`: no target. Correct: `.env` is a
  write target.
- `tee`, a quoted line break, then `cat .env`: no target. Correct: `.env`
  is a write target.
- `tee '&&' cat .claude/settings.json`: no target, and the hook allows it.
  Correct: a protected config write, so ask or deny by client.

The flaw exists on `dev` since `240fe2d` (2026-08-08, "optimize safety
routing"); this plan did not introduce it.

### R2 - MINOR (usability): the same flaw denies ordinary read-only commands

When the false operator sits next to a real one, the segment between them
is empty and the guard fails closed with `empty shell command segment`
(`hooks-errors.log`, 2026-10-21T02:38:41Z):

- `printf 'x|y\n' | grep '|' | head -1`
- `find . -exec grep x {} \; | head -1` (a common `find` form)

A quoted `'>'` is also read as a redirect, so `grep '>' .env` reports
`.env` as a write target. That direction only over-protects.

### R3 - MINOR (guidance): restore messages tell an agent to run a command it cannot run

`verify.py` (the `openwiki-managed-state` message), `openwiki-guard.py`
(the `pre` deny reason and the `post` error), and the Fix column of the
OpenWiki row in `docs/runtime-checks.md` say "run ... openwiki-guard.sh
post". An agent is denied when it runs a hook script, so the message
should tell it to ask the user. Phase G already changed the
`knowledge-refresh` skill and `docs/architecture.md` this way.

### R4 - INFO (style): long sentences in generated wiki pages

Some generated sentences are far over the 20-word target in
`openwiki/INSTRUCTIONS.md`, for example the `protect-files` bullet in
`openwiki/architecture/hooks-and-guardrails.md` and the "Reading outside
the diff" bullet in `openwiki/architecture/agents-and-skills.md`. Only an
OpenWiki run may change them.

## Findings added by the plan's devil's-advocate review

An independent read-only review (Opus, extra-high effort, devils-advocate
skill) checked the draft plan against the code on 2026-10-21. It found that
R1 is one symptom of a wider defect: `split_segments` turns every newline
into `;` and then lexes with Python's `shlex`, which does not follow Bash's
rules. The orchestrator re-ran the first seven forms below through the full
`protect-files.py` decision for Claude Code and Codex: all were allowed
(`tee .env` alone is denied). Every probe passed command text only; no
write command was run. Bash's own reading was checked with harmless
stand-ins (`echo RAN`).

### R5 - CRITICAL (security): comments and blank lines hide the lines after them

Once newlines become `;`, `shlex` treats a `#` as "skip to the next
newline", and none are left, so everything after the first `#` is dropped.
A blank line, or a line ending in `;`, `&&`, `||`, `|`, or `&`, glues into
one unknown token (`;;`, `&&;`), so the next line joins the read-only
command before it. No bad intent is needed: agents write multi-line
commands with comments and blank lines.

- `# step 1` then `tee .env` on the next line: allowed.
- `ls # note` then `tee .env`: allowed.
- `cat README.md`, a blank line, then `touch .env`: allowed.
- `git status`, a blank line, then `git restore .env`: allowed.
- `cat x &&` then `tee .env`: allowed (also `;`, `|`, `&` line ends).

### R6 - MAJOR (security): command substitution inside double quotes or backticks is never checked

`cat "$(tee .env)"` and `` cat `tee .env` `` are allowed; Bash runs the
inner command. Only an unquoted `$(` is caught today.

### R7 - MAJOR (security): other lexer mismatches

- An escaped quote outside quotes confuses the heredoc and
  process-substitution scanners: `cat \' <(tee .env)` is allowed.
- A `#` inside a word (`cat x#y; tee .env`, `echo ${#X}; tee .env`), an
  escaped backslash before a newline, and ANSI-C quoting
  (`cat $'\'' ; tee .env ; cat \'`) are allowed.
- `protect_quoted_globs` removes the quotes from a quoted value that holds
  an operator and a variable: `tee "|cat $Y" .env` loses `.env`.
- Grouped operators are one unknown word to `shlex`: `cat x |& tee .env`,
  `cat x &>> .env`, `cat x >& .env`, and `cat x <> .env` are allowed.

### R8 - MAJOR (security): two write paths outside the lexer

- An inline `sed` write script is not checked: `sed -n 'w .env' README.md`
  reports no target (the heredoc form is checked).
- An unmodelled command after `cd` is resolved against the repository
  root, not the `cd` folder.

### Correction to R3

An agent can still run the restore through `cd .claude/hooks/scripts &&
bash openwiki-guard.sh post </dev/null` (that is R8's `cd` gap). The
message wording should say that the guard denies an agent command that
names a hook script, which is accurate, and that the user runs the command
in their own shell.

### Not bypasses today

`tee $'|' cat .env`, `tee "\|" cat .env`, `tee a'|'b cat .env`,
`{ cat x; tee .env; }`, and a `case` statement are denied. `eval`,
`bash -c`, `xargs`, and `find -exec` forms are denied as uncertain. A
single-line `;;` is a Bash syntax error, not a bypass.

### Outside this plan

Bash reads of secret-shaped files (`cat .env`) are allowed while native
read tools on them are denied. That is a policy question for the user,
not a parsing defect.

## Disposition

User decisions on 2026-10-21: two code phases, a dedicated Bash scanner,
and secret-file Bash reads kept as a follow-up.

- R1, R2, R5, and R7 (except grouped operators): Phase H
  (`2026-10-21_phase-H-guard-shell-scanner`).
- R3, R6, R7 grouped operators, and R8: Phase I
  (`2026-10-21_phase-I-guard-substitutions-and-restore-messages`).
- R4 and the wiki pages Phases H and I change: Phase J
  (`2026-10-21_phase-J-guard-hardening-knowledge-refresh`).
- Secret-file Bash reads: a "Recorded follow-ups" bullet in
  `docs/target-mapping.md` (Phase H step 3).
