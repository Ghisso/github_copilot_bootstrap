---
name: 2026-10-21_phase-H-guard-quoting-and-restore-messages
type: small-plan
parent_plan: backlog-followups
phase_index: 8
status: planned
closeout_session_log:
---

# Small Plan: Guard Quoting and Restore Messages

## Scope

Fix the shell-parsing defect in the file-protection guard and make the
OpenWiki restore messages tell an agent to ask the user. Findings R1, R2,
and R3 in
`.claude/quality_reports/2026-10-21_backlog-followups-reopen-findings.md`
give the evidence; this plan does not repeat it.

- **BF-H1 (R1, R2).** A quoted or backslash-escaped operator character is a
  word, as in Bash. It never splits a command, never acts as a pipe or
  group, and a quoted `>` or `<` is never a redirect. A quoted line break
  is not a separator. Real operators still split, and a truly empty
  segment still fails closed.
- **BF-H2.** No guard decision loosens for a command that has no quoted or
  escaped operator character. Any decision that changes is one of the
  intended classes below.
- **BF-H3 (R3).** Every message that tells the reader to run
  `openwiki-guard.sh post` says the user runs it, because the guard denies
  an agent that runs a hook script.
- **BF-H4.** The docs and the parity table describe the change.

This is control-plane work (`shared/hooks/scripts/`, `shared/scripts/`):
full review profiles apply.

## Steps

- [ ] **1. Parse quoted and escaped operators as words (BF-H1, BF-H2).**
  **Owner:** coder.
  **Files:** modify `shared/hooks/scripts/protect-files.py`
  (`split_segments`, and any other place that turns command text into
  segments or redirect tokens; check `extract_process_substitutions`,
  `classify_command`, and the `\n` to `;` rewrite); modify
  `tests/test_hook_gates.py` and/or `tests/test_protect_files_scoping.py`;
  modify `scripts/validate_targets.py` only if its installed-hook smoke
  cases need a matching case.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Write the tests first and show each new case failing on the current
  guard. Reuse the module's existing approach for quoted text: a
  quote-aware pass before lexing, like `protect_quoted_globs`, that hides
  each quoted or escaped operator character behind a marker, and puts the
  literal character back inside the tokens after segmenting. Read every
  caller of the changed function before writing.
  Required cases (call `shell_targets()` and the full hook through
  `protect-files.sh` for all four clients; never run the command itself):
  - must now report `.env` as a write target and deny: `tee '|' cat .env`,
    `tee ';' cat .env`, `tee '&&' cat .env`, `tee '||' cat .env`,
    `tee '&' cat .env`, `tee '(' cat .env`, `tee "|" cat .env`,
    `tee '|''|' cat .env`, `tee \| cat .env`, `tee \; cat .env`, and
    `tee` with a quoted line break before `cat .env`;
  - must now get the protected-config decision (ask on Claude Code and
    Copilot, deny on Codex and Antigravity):
    `tee '&&' cat .claude/settings.json`;
  - must now be allowed: `printf 'x|y\n' | grep '|' | head -1`,
    `find . -exec grep x {} \; | head -1`, `grep ';' README.md | head -1`,
    `grep '>' README.md`, and `grep '>' .env` (a read, not a write);
  - must keep today's result: `echo hi | tee .env` (deny),
    `tee .env` (deny), `cat .env` (allow), `ls | head` (allow), a
    truly empty segment such as `| head` or `a && && b` (fail closed),
    `echo a; tee .env` (deny), `cmd > .env` (deny),
    `find . -exec rm {} \;` on a protected path (same decision as today).
  Negative controls: each new deny case fails on the unchanged guard, and
  each case is checked against Bash's own reading of the text, not the
  implementation.
  Differential check (BF-H2): run the old guard (`git show
  HEAD:shared/hooks/scripts/protect-files.py` saved to the session scratch
  folder) and the new guard over the same inputs: every command string in
  the hook test files and `scripts/validate_targets.py`, plus a generated
  set (the Phase D battery generator, session scratch `phase-d/`, may be
  reused). Record the counts. Every changed decision must contain a quoted
  or escaped operator character, a quoted `>`/`<`, or a quoted line break;
  any other change is a defect.
  Must not: loosen a decision outside the intended classes; change
  `emit()`, the client decision table, or the read-only command list; add
  a dependency or an option; use syntax that the Python 3.9
  hook-compatibility job in `.github/workflows/validate.yml` rejects.

- [ ] **2. Make the restore messages say the user runs them (BF-H3).**
  **Owner:** coder.
  **Files:** modify `shared/scripts/verify.py` (the `openwiki-managed-state`
  message, near line 3083), `shared/hooks/scripts/openwiki-guard.py` (the
  `pre` deny reason near line 410 and the `post` error near line 444);
  modify `tests/test_verify.py` and `tests/test_openwiki_guard.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`.
  Each message names the exact command
  `bash .claude/hooks/scripts/openwiki-guard.sh post </dev/null` and says
  the user runs it, for example "ask the user to run ... (the
  file-protection guard does not let an agent run a hook script)". Keep
  the existing prefixes (`openwiki-guard:`, `openwiki-managed-state:`) and
  exit codes. Add one assertion per message that fails on the current
  text. No other message changes.

- [ ] **3. Document the change (BF-H4).**
  **Owner:** documenter, after review of steps 1 and 2.
  **Files:** `docs/runtime-checks.md` (the shell-parsing paragraph near
  line 255 and the Fix column of the OpenWiki managed-state row near line
  602), `docs/smoke-tests.md` (the `protect-files.sh` bullets near line
  205), `docs/target-mapping.md` (one row in `## Backlog-Followups Client
  Parity`: quoted and escaped operators parsed as words, same classifier
  on all four clients, evidence the new tests).
  **Required Skills:** `shared/skills/documentation/SKILL.md`.
  State the rule plainly: quoted or escaped `|`, `;`, `&`, `(`, `)`, `<`,
  `>`, and quoted line breaks are ordinary words. Keep the line count of
  each paragraph that a wiki claim cites (`docs/runtime-checks.md`
  L678-L710; `docs/architecture.md` L32-L123) or leave the stale claims to
  Phase I's refresh. Do not edit dated records.

- [ ] **4. Regenerate, self-install, verify, review, close out.**
  **Owner:** orchestrator; fresh reviewer.
  Run `uv run python scripts/generate_targets.py --all` and
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  before verification. Probe the guard only with payload files and the
  `shared/` script copy, never by running a write command. Write findings
  that name a protected path with the Write tool and pass
  `--findings-json <file>`. Correct the `MEMORY.md` entry that records
  this defect as unfixed.
  **Required Skills:** `shared/skills/code-review/SKILL.md`.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/test_hook_gates.py tests/test_protect_files_scoping.py tests/test_openwiki_guard.py tests/test_verify.py tests/test_validate_targets.py -q
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Record the differential check: input counts, the number of changed
  decisions, and that every changed decision is in an intended class.
- Claude Code: in this repository, run `printf 'x|y\n' | grep '|' | head -1`
  and record that the guard allows it.

## Review Profiles

Use `.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Give the reviewer BF-H1 to
BF-H4, the findings report, the negative-control output, the differential
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
