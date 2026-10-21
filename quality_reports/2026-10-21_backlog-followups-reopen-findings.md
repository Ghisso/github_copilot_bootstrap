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

| Command text | Guard result today | Correct result |
| --- | --- | --- |
| `tee '|' cat .env` | no target; hook allows | `.env` is a write target; deny |
| `tee ';' cat .env`, `tee '&&' cat .env`, `tee '||' cat .env`, `tee '&' cat .env`, `tee '(' cat .env`, `tee "|" cat .env`, `tee '|''|' cat .env` | no target | `.env` is a write target |
| `tee \| cat .env`, `tee \; cat .env` | no target | `.env` is a write target |
| `tee '<newline>' cat .env` (a quoted line break) | no target | `.env` is a write target |
| `tee '&&' cat .claude/settings.json` | no target; hook allows | protected config write; ask or deny by client |

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

## Disposition

- R1, R2, R3: Phase H (`2026-10-21_phase-H-guard-quoting-and-restore-messages`).
- R4 and the wiki pages Phase H changes: Phase I
  (`2026-10-21_phase-I-guard-quoting-knowledge-refresh`).
