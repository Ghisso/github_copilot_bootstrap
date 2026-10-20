# Session: Backlog follow-ups — Phase B, nested state files

**Date:** 2026-10-20
**Plan:** .claude/plans/2026-10-20_phase-B-nested-state-files.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** COMPLETED

## Goal

Stop a bootstrap refresh from deleting the nested `.claude/.gitignore` and
`.claude/.gitattributes` and from rebuilding `.gitignore` without a
consumer's own lines (BF-B1), and restore the `session_logs/*.log
merge=union` rule in existing nested repositories (BF-B2).

## Task Tracking

- [x] PRE-FLIGHT: Phase A committed (`f52a867`) and pushed; the post-commit
  hook made Phase B the current phase. Phase A outcomes do not affect
  Phase B; no planner.
- [x] IMPLEMENT/VERIFY/REVIEW — two review rounds; round 1 `PASS` with three
  MINORs (all fixed), round 2 `PASS` with no findings.
- [x] CLOSEOUT: documentation, final AI state, checkpoint, staged index,
  findings, phase receipt, closeout dry run, checkpoint, closeout receipt.
- [ ] COMMIT
- [ ] PUSH

## Work Log

- **15:35** - Pre-refresh record (step 3): `git -C .claude ls-files
  .gitignore .gitattributes` lists only `.gitignore`; `.claude/.gitattributes`
  does not exist. `.claude/.gitignore` sha256 `bdcfda06…e67810`; a copy is
  in the session scratch folder (`phase-b/gitignore.before`). It is the
  template plus the `.cache/` and `session_logs/hooks-errors.log` blocks.
- **15:36** - Delegated steps 1 and 2 to one coder.
- **15:46** - Coder: both files joined `CONSUMER_STATE_PATHS` (comment in the
  `settings.local.json` style); the `check_runtime.py` `.gitignore` special
  case was deleted; the validator's exact tuple and repeat-install fixture
  (built from the temporary install's own `.gitignore` plus a sentinel, and
  a `.gitattributes` seeded with the union line plus a sentinel) cover both
  files; `write_nested_gitignore` appends `settings.local.json` when
  `git check-ignore -q --no-index` says it is not ignored;
  `write_nested_gitattributes` writes the template only when missing and
  otherwise appends the union line only when absent, and runs wherever
  `write_nested_gitignore` runs. Failing first: 3 installer tests and 7
  state-sync tests failed on the old code; removing the tuple entries made
  the validator fail on the tuple and on byte preservation.
- **15:37** - First real self-install refresh with the fix:
  `.claude/.gitignore` stayed byte-identical (`bdcfda06…`), and the
  installer's nested `bootstrap: update` commit added `.gitattributes`
  with `session_logs/*.log merge=union`.
- **15:40** - Documentation (before review, so the reviewer saw it): added
  `settings.local.json` and the two nested Git files to the consumer-state
  lists in `docs/runtime-checks.md` ("What a self-refresh removes" and the
  drift-check exclusion) and `README.md` (consumer-only files paragraph),
  with one sentence on the append-only maintenance.
- **15:44** - `verify.py phase` (not persisted): PASS, 2781 passed.
- **15:52** - Review round 1 (six profiles, commit gate): `PASS`, three
  MINORs: `check-ignore` exit 128 treated as "not ignored"; no test pins
  `--no-index`; a wrong test-helper docstring. The reviewer also handed
  Phase G two stale OpenWiki pages; added to the Phase G small plan.
- **15:58** - Coder fixed all three: append only on status exactly 1 (new
  test corrupts the nested `HEAD`, asserts status 128, and checks the bytes
  never change; negative control with `-ne 0` failed); the untrack test now
  asserts unchanged `.gitignore` bytes (negative control without
  `--no-index` failed only that test); docstring reworded. Refresh again;
  `verify.py phase`: PASS, 2782 passed.
- **16:00** - Review round 2: `PASS`, no findings.
- **16:01** - Optional check in a throwaway consumer (scratch folder):
  after a fresh install, a consumer line `secret-notes/` plus an ignored
  `secret-notes/token.txt` were added; a re-install kept `.gitignore`
  byte-identical and the file never entered the nested `bootstrap: update`
  commit. The re-install did delete the ignored file itself
  (`remove obsolete generated file .claude/secret-notes/token.txt`): every
  file under `.claude/` outside the consumer-state paths is treated as
  obsolete bootstrap output. That is existing, documented behavior
  (`docs/runtime-checks.md`, "What a self-refresh removes"), not changed
  here.

## [LEARN] Entries

- [LEARN:quality] In shell guards, `git check-ignore -q` needs `--no-index`
  to judge the ignore rules for a file that is still tracked, and it exits
  1 for "not ignored" but 128 when git itself fails (unsafe or broken
  repository). Act only on status exactly 1; treating every non-zero status
  as "not ignored" repeats the side effect on every run while git is broken.

## Verification

```text
PASS        0.3s  uv run python scripts/generate_targets.py --all
PASS       44.2s  uv run python scripts/validate_targets.py
PASS       54.5s  uv run pytest tests/test_install_bootstrap.py tests/test_state_sync.py -q
PASS        0.9s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS        0.0s  git -C .claude ls-files --error-unmatch .gitignore .gitattributes
PASS        0.2s  uv run python .claude/scripts/verify.py fast --format json
closeout: PASS
```

Phase receipt: `.claude/quality_reports/verification-phase-2026-10-20_phase-B-nested-state-files.json`.
Findings: `.claude/quality_reports/findings-2026-10-20_phase-B-nested-state-files.json`
(no findings; gate result `PASS`).

- optional 1: PASS — throwaway consumer install: the consumer's
  `secret-notes/` line survived a re-install byte for byte and the ignored
  file stayed out of the nested `bootstrap: update` commit (the re-install
  deleted the ignored file itself, which is existing documented refresh
  behavior).

## Open Questions / Next Steps

- Phase C follows: `MEMORY.md` split and `caveman-compress` backups.
