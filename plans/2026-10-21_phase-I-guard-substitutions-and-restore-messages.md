---
name: 2026-10-21_phase-I-guard-substitutions-and-restore-messages
type: small-plan
parent_plan: backlog-followups
phase_index: 9
status: planned
closeout_session_log:
---

# Small Plan: Guard Substitutions and Restore Messages

## Scope

Close the remaining write paths the guard misses, using Phase H's scanner,
and make the OpenWiki restore messages say the user runs them. Evidence:
findings R3 (with its correction), R6, R7 (last bullet), and R8 in
`.claude/quality_reports/2026-10-21_backlog-followups-reopen-findings.md`.

- **BF-I1 (R6).** The inner command of `$( )` or backticks inside double
  quotes, and of unquoted backticks, is classified like a process
  substitution today.
- **BF-I2 (R7).** `|&` is a pipe. `&>>`, `<>`, and `>&` followed by a word
  that is not a file descriptor number or `-` are write redirects.
- **BF-I3 (R8).** An inline `sed` script that writes a file (`w file`,
  `W file`, or the `w file` flag of `s///`) gives the guard that file as a
  write target.
- **BF-I4 (R8).** An unmodelled command after `cd` in the same command line
  resolves its path operands against the `cd` folder, as Phase D does for
  unmodelled Git commands.
- **BF-I5 (R3).** Every message that names `openwiki-guard.sh post` says
  the user runs it in their own shell.
- **BF-I6.** No decision loosens; docs and parity rows describe the
  change. This phase also closes the Phase H loosening exception (big plan
  "Decisions recorded" item 8): its differential check must show none of
  the 261 Phase H exception commands still allowed.
- **BF-I7 (R9).** The pre-existing gaps the Phase H coder found are
  closed: a quoted variable glued to a protected name (`tee .env"$X"`,
  `tee "$X".env`), a parameter default that names one
  (`tee "${X:-.env}"`), ANSI-C escapes that spell one
  (`touch $'\x2eenv'`), a `#` inside `${ }` (`echo ${x:- #}; tee .env`),
  and a heredoc body inside `"$( )"`. Added from the Phase H review: a
  shell function or alias that hides a write (`cat() { tee "$@"; }; cat
  .env`), `$IFS` word splitting (`tee$IFS.env`), and heredoc delimiters
  the guard reads short (`<<EOF#x`, `<<END-OF-DATA`). Added from the
  Phase H round 2 coder report: a name built by a command
  (`tee $(echo .e)nv`), array elements (`a=(.env); tee ${a[0]}`), a glob
  glued to a variable (`tee "$X".e*`), and `find -delete` or
  `find -exec rm {} +` with or without a pattern. A form the guard cannot
  resolve safely is an uncertain hit, which denies on every client; where
  a deny would block common harmless commands, record the gap with its
  reason instead.

This is control-plane work (`shared/hooks/scripts/`, `shared/scripts/`):
full review profiles apply.

## Steps

- [ ] **1. Close the remaining write paths (BF-I1 to BF-I4, BF-I7).**
  **Owner:** coder.
  **Files:** modify `shared/hooks/scripts/protect-files.py` (the scanner
  from Phase H, `OPERATORS`, `REDIRECTS`/`is_redirect`, the `sed` handling
  and the `READ_ONLY` path for `sed`, and the unmodelled-command path
  resolution Phase D added for Git); modify the hook test files; modify
  `scripts/validate_targets.py` only if its smoke cases need a match.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Read every caller first. Write the tests first and show each new case
  failing on the Phase H guard. Required cases (call `shell_targets()` for
  every case; run the full hook for one deny case per client; never run a
  command):
  - Must deny: `cat "$(tee .env)"`, `` cat `tee .env` ``,
    `` cat "`tee .env`" ``, `cat <<< "$(tee .env)"`; `cat x |& tee .env`,
    `cat x &>> .env`, `cat x >& .env`, `cat x <> .env`;
    `sed -n 'w .env' README.md`, `sed 's/a/b/w .env' README.md`,
    `sed -e 'w .env' README.md`; `cd .claude/hooks/scripts && bash
    openwiki-guard.sh post </dev/null` (names a hook script).
  - Must get the protected-config decision: one unmodelled command after
    `cd .claude` that writes `settings.json` (the coder picks a command
    the guard does not model and records why).
  - Must allow: `echo "$(date)"`, `` echo "`date`" ``,
    `echo '$(tee .env)'` (single quotes are literal);
    `cat x 2>&1 | head`, `cat x >&2`, `cat x |& head`;
    `sed -n '1p' README.md`, `sed 's/a/b/' README.md`.
  - Must deny (BF-I7): `tee .env"$X"`, `tee "$X".env`,
    `tee "${X:-.env}"`, `touch $'\x2eenv'`, `echo ${x:- #}; tee .env`, and
    a `tee .env` line inside a heredoc body inside `"$( )"`.
  - Must allow: `echo "$X"`, `echo "${X:-default}"`, and the usual
    `git commit -m "$(cat <<'EOF' ... EOF)"` form, including a message
    body whose prose contains the word `case` (Phase H refuses an unquoted
    `case` inside `$( )`; that refusal must not reach quoted heredoc
    bodies when this phase classifies double-quoted substitutions).
  - Must keep today's result: `cat $(tee .env)` (deny), and every Phase H
    case.
  Check each expected value against Bash's own reading with a harmless
  stand-in. Must not: change `emit()`, the client decision table, or the
  read-only command list beyond the `sed` write forms; add a dependency or
  an option; break Python 3.9 compatibility.

- [ ] **2. Make the restore messages say the user runs them (BF-I5).**
  **Owner:** coder.
  **Files:** modify `shared/scripts/verify.py` (the `openwiki-managed-state`
  message, near line 3083), `shared/hooks/scripts/openwiki-guard.py` (the
  `pre` deny reason near line 410 and the `post` error near line 444);
  modify `tests/test_verify.py` and `tests/test_openwiki_guard.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`.
  Each message stays on one line, keeps its prefix (`openwiki-guard:`,
  `openwiki-managed-state:`) and exit code, names the exact command
  `bash .claude/hooks/scripts/openwiki-guard.sh post </dev/null`, says the
  user runs it in their own shell, and says why: the guard denies an agent
  command that names a hook script. Add one assertion per message that
  fails on the current text. No other message changes.

- [ ] **3. Prove no decision loosened (BF-I6).**
  **Owner:** coder; the orchestrator records the result.
  Repeat Phase H's differential check with the Phase H guard as the old
  guard, adding this phase's cases and the substitution set. Every looser
  change is listed with Bash's reading and must be a step 1 allow case.

- [ ] **4. Document the change (BF-I6).**
  **Owner:** documenter, after review of steps 1 to 3.
  **Files:** `docs/runtime-checks.md` (the shell-parsing paragraph and the
  Fix column of the OpenWiki managed-state row near line 602),
  `docs/smoke-tests.md`, `docs/target-mapping.md` (parity rows for the new
  write paths, same classifier on all four clients).
  **Required Skills:** `shared/skills/documentation/SKILL.md`.
  Keep the line count of paragraphs that wiki claims cite, or leave those
  claims to Phase J. Do not edit dated records.

- [ ] **5. Regenerate, self-install, verify, review, close out.**
  **Owner:** orchestrator; fresh reviewer.
  Same procedure as Phase H step 4.
  **Required Skills:** `shared/skills/code-review/SKILL.md`.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/test_hook_gates.py tests/test_protect_files_scoping.py tests/test_openwiki_guard.py tests/test_verify.py tests/test_validate_targets.py tests/test_lifecycle_hooks.py -q
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Record the differential check: input counts per set, changed results by
  direction, and every looser change with Bash's reading.

## Review Profiles

Use `.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Give the reviewer BF-I1 to
BF-I6, the findings report, the negative-control output, the differential
check, and the final diff.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
