---
name: 2026-10-21_phase-H-guard-shell-scanner
type: small-plan
parent_plan: backlog-followups
phase_index: 8
status: complete
closeout_session_log: .claude/session_logs/2026-10-21_backlog-followups-phase-h.md
---

# Small Plan: Guard Shell Scanner

## Scope

The file-protection guard reads shell text with Python's `shlex` after
turning every newline into `;`. That does not follow Bash's rules, and it
lets writes to protected files through on every client. Comments and blank
lines hide the lines after them, and quoted or escaped operators split one
command into two. It also denies some harmless commands. Evidence:
findings R1, R2, R5, and R7 (all but its last bullet) in
`.claude/quality_reports/2026-10-21_backlog-followups-reopen-findings.md`.

This phase replaces `shlex` in `split_segments` with one small scanner that
follows Bash's quoting, escape, comment, and newline rules. The heredoc and
process-substitution code uses the same scanner (user decision 2026-10-21,
big plan "Decisions recorded" item 7). Phase I handles command substitution
inside quotes, grouped operators such as `|&`, inline `sed` writes, the
`cd`-folder gap, and the restore messages.

- **BF-H1.** The guard splits and tokenizes shell text as Bash does, for
  the rules listed in step 1. Every required deny case is denied and every
  required allow case is allowed.
- **BF-H2.** No guard decision loosens outside the intended classes; the
  differential check in step 2 proves it. Exception accepted by the user
  on 2026-10-21 (big plan "Decisions recorded" item 8): a looser result is
  allowed only when the command holds a backtick, `$(` inside double
  quotes, a grouped operator (`|&`, `&>`, `&>>`, `>&`, `<>`), or a quoted
  variable glued to a file name, because the old guard already let each of
  those through on its own. Phase I closes them.
- **BF-H3.** The docs, one parity row, and one recorded follow-up describe
  the change.

This is control-plane work (`shared/hooks/scripts/`): full review profiles
apply.

## Steps

- [x] **1. Replace `shlex` with a Bash scanner (BF-H1).**
  **Owner:** coder.
  **Files:** modify `shared/hooks/scripts/protect-files.py`
  (`split_segments`; the quote handling in `_find_unquoted_heredoc`,
  `extract_process_substitutions`, and `_matching_paren`; the order of
  `protect_quoted_globs` relative to the scanner; the `\\\n` and `\n`
  rewrites at the top of `split_segments`); modify
  `tests/test_hook_gates.py` and/or `tests/test_protect_files_scoping.py`;
  modify `scripts/validate_targets.py` only if its installed-hook smoke
  cases need a matching case.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Read every caller of each changed function first. Write the tests first
  and show each new case failing on the current guard.
  Scanner rules, as Bash reads text outside a heredoc body:
  - Outside quotes, a backslash makes the next character literal; a
    backslash before a newline joins the lines; an escaped backslash
    (`\\`) before a newline does not.
  - `'...'` is literal with no escapes. In `$'...'`, a backslash escapes
    the next character, including `'`.
  - In `"..."`, a backslash escapes only `$`, `` ` ``, `"`, `\`, and a
    newline. `$( )` and backticks inside it are code: track their nesting
    to find the closing `"`. (Phase I classifies their inner commands.)
  - `#` starts a comment only at the start of a word, outside quotes, and
    the comment ends at the next newline.
  - An unquoted newline separates commands. A newline after `;`, `&&`,
    `||`, `|`, or `&`, and a blank line, add no empty segment. A truly
    empty segment (`| head`, `a && && b`) still fails closed. A leading
    `(` opens a group and is not an empty segment.
  - A quoted or escaped operator character is part of a word. A token
    that came from quoted or escaped text and equals an operator, or that
    `is_redirect` would match, is returned with `QUOTED_VALUE_PREFIX` so
    later stages never read it as an operator or redirect.
  - Grouped operators (`|&`, `&>>`, `>&`, `<>`) keep today's result in
    this phase; Phase I changes them.
  - An unterminated quote, `$(`, or backtick fails closed, as today.
  Restore every marker before `split_segments` returns, so
  `protected_path_literals` and the redirect checks see real text.
  Required cases. Call `shell_targets()` for every case. Run the full hook
  through `protect-files.sh` for one deny case per client (Claude Code,
  Codex, Copilot, Antigravity) and for the `.claude/settings.json` case.
  Never run a command itself. `<NL>` is a newline.
  - Must deny (`.env` is a write target): `tee '|' cat .env`, the same with
    `';'`, `'&&'`, `'||'`, `'&'`, `'('`, `"|"`, `'|''|'`, `''\|`, `\|`,
    `\;`, or a quoted newline in place of `'|'`; `# step 1<NL>tee .env`;
    `ls # note<NL>tee .env`; `echo hi # note<NL>rm .env`;
    `cat README.md<NL><NL>touch .env`; `grep -n x README.md<NL><NL>rm .env`;
    `git status<NL><NL>git restore .env`; `cat x;<NL>tee .env`;
    `cat x &<NL>tee .env`; `cat x |<NL>tee .env`; `cat x &&<NL>tee .env`;
    `cat <<EOF &&<NL>body<NL>EOF<NL>touch .env`; `cat x#y; tee .env`;
    `cat x#y<NL>tee .env`; `echo ${#X}; tee .env`; `cat $# ; tee .env`;
    `cat x\\<NL>tee .env`; `cat $'\'' ; tee .env ; cat \'`;
    `cat \' <(tee .env)`; `cat \' <(tee .env) \'`;
    `cat \' '<<EOF' \'<NL>tee .env<NL>EOF`; `tee "|cat $Y" .env`;
    `cat <<< '|' ; tee .env`.
  - Must get the protected-config decision (ask on Claude Code and
    Copilot, deny on Codex and Antigravity):
    `tee '&&' cat .claude/settings.json`.
  - Must allow: `printf 'x|y\n' | grep '|' | head -1`;
    `find . -exec grep x {} \; | head -1`; `grep ';' README.md | head -1`;
    `grep '>' README.md`; `grep '>' .env` and `cat '2>' .env` (reads,
    as `cat .env` is today); `ls # don't`; `cat a &&<NL><NL>cat b`;
    `(cd docs && ls)`; a multi-line read-only command with comments and
    blank lines.
  - Must keep today's result: `echo hi | tee .env`, `tee .env`,
    `cmd > .env`, `cat x 3>> .env`, `cat x 2>&1 > .env`,
    `{ cat x; tee .env; }`, `case a in a) tee .env;; esac`,
    `tee $'|' cat .env`, `tee "\|" cat .env`, `tee a'|'b cat .env`,
    `cat $(tee .env)` (deny); `eval 'tee .env'`, `bash -c 'tee .env'`,
    `echo .env | xargs tee`, `find . -name .env -exec rm {} \;`,
    `find . -name .env -exec tee {} +` (deny as uncertain); `cat .env`,
    `ls | head` (allow); `| head`, `a && && b`, an unterminated quote
    (fail closed).
  - Added after the first coder round (2026-10-21): a run of unquoted
    operator characters splits into Bash operators by longest match, so
    `cat x;(tee .env)` and `cat x&&(tee .env)` are denied, while grouped
    forms keep today's meaning until Phase I. An operator right after `)`
    is valid: `echo $(date) && ls`, `echo $(date) &&<NL>ls`, and
    `(cd docs && ls) && ls` are allowed; `cat $(tee .env) && ls` and
    `(tee .env) && ls` stay denied. A `)` on its own line closing a
    multi-line group is allowed.
  Check each expected value against Bash's own reading with a harmless
  stand-in (`printf '[%s]'` or `echo RAN`, run from a scratch script),
  never against the implementation.
  Must not: change `emit()`, the client decision table, or the read-only
  command list; add a dependency or an option; use syntax that the Python
  3.9 hook-compatibility job in `.github/workflows/validate.yml` rejects.

- [x] **2. Prove no decision loosened (BF-H2).**
  **Owner:** coder; the orchestrator records the result.
  Save the old guard (`git show HEAD:shared/hooks/scripts/protect-files.py`)
  in the session scratch folder. Run old and new over the same inputs on
  all four clients, counting a fail-closed exit 2 as its own result:
  every command string in the hook test files and
  `scripts/validate_targets.py`, every case in step 1, and a generated set
  (the Phase D battery generator in session scratch `phase-d/` may be
  reused). Add a substitution set: put each of `'|'`, `"|"`, `\|`, `''\|`,
  `$'|'`, a quoted newline, `'>'`, and `'2>'` in each argument slot of
  those commands; the result must equal the result with the plain word `X`
  in that slot. Sort changes by direction. Stricter changes are fine. List
  every looser change (deny to ask or allow, ask to allow, exit 2 to ask
  or allow) one by one with Bash's reading; each must be a step 1 allow
  case or the same class. Any other looser change is a defect.

- [x] **3. Document the change (BF-H3).**
  **Owner:** documenter, after review of steps 1 and 2.
  **Files:** `docs/runtime-checks.md` (the shell-parsing paragraph near
  line 255), `docs/smoke-tests.md` (the `protect-files.sh` bullets near
  line 205), `docs/architecture.md` if it describes `shlex` or the parsing,
  `docs/target-mapping.md` (one row in `## Backlog-Followups Client
  Parity`: the guard reads shell text as Bash does, the same classifier on
  all four clients, evidence the new tests; and one "Recorded follow-ups"
  bullet: Bash reads of secret-shaped files such as `cat .env` are allowed
  while native read tools on them are denied, kept by user decision
  2026-10-21 for a later policy choice).
  **Required Skills:** `shared/skills/documentation/SKILL.md`.
  State the rules plainly. Keep the line count of each paragraph a wiki
  claim cites (`docs/runtime-checks.md` L678-L710; `docs/architecture.md`
  L32-L123), or leave those claims to Phase J's refresh. Do not edit dated
  records.

- [x] **4. Regenerate, self-install, verify, review, close out.**
  **Owner:** orchestrator; fresh reviewer.
  Run `uv run python scripts/generate_targets.py --all` and
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  before verification. Probe the guard only with payload files and the
  `shared/` script copy. Write findings that name a protected path with the
  Write tool and pass `--findings-json <file>`. Correct the
  `[LEARN:tooling]` `protect-files.sh` entry in `.claude/MEMORY.md`, which
  records the quoted-pipe defect as unfixed.
  **Required Skills:** `shared/skills/code-review/SKILL.md`.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/test_hook_gates.py tests/test_protect_files_scoping.py tests/test_validate_targets.py tests/test_lifecycle_hooks.py -q
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Record the differential check: input counts per set, changed results by
  direction, and every looser change with Bash's reading.
- Claude Code: in this repository, run `printf 'x|y\n' | grep '|' | head -1`
  and a multi-line read-only command with a `#` comment, and record that
  the guard allows both.

## Review Profiles

Use `.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Give the reviewer BF-H1 to
BF-H3, the findings report, the negative-control output, the differential
check, and the final diff.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
