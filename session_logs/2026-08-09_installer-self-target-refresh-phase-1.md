# Session: Installer self-target refresh — Phase 1

**Date:** 2026-08-09
**Plan:** .claude/plans/2026-08-09_phase-1-installer-allow-self.md
**Status:** COMPLETED

## Goal

Add `--allow-self` so the bootstrap repository can refresh its own dogfood
overlay, then actually run it and confirm the drift resolves.

## What Was Built

- `--allow-self` on `install_bootstrap.py`. `validate_install_roots` now
  permits exactly one overlap — generated source inside the target — and only
  when the target is the bootstrap repository itself. `source == target` and
  target-beneath-source stay rejected with or without the flag. Without the
  flag the rejection message names the opt-in.
- The flag forwarded through `update_consumers.py`.
- `check_runtime.py` now prints a repair command that works here.
- Six regression tests covering the permitted case, both dangerous cases, the
  default fail-closed behavior, and unchanged consumer installs.

## It Was Actually Run

```bash
uv run python scripts/install_bootstrap.py . --allow-self --local-only
```

Result: **`check_runtime.py` drift failures went from 12 to 1.**

`protect-files.py` and `pretool-bash-guard.sh` are now installed, the six
`.codex/agents/*.toml` match generated output (documenter back to
`gpt-5.6-luna`), and `.codex/hooks.json` is current.

The one remaining failure is a pre-existing orphan:
`.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md` exists in the overlay
but not in `shared/skills/`. It needs a content decision — promote it to
`shared/` so it regenerates, or delete it — so it was left in place rather than
destroyed as a side effect of a plumbing change.

## Three Bugs The Run Exposed

Running it surfaced problems that no amount of unit testing would have.

1. **`settings.local.json` was being deleted on every install, in every
   consumer.** It is absent from generated output and was not in
   `CONSUMER_STATE_PATHS`, so it counted as an obsolete owned file. Worse,
   `state-sync.sh` deliberately gitignores it in the nested repo ("local
   convenience only; never synced"), so the deletion was **unrecoverable**.
   Added to `CONSUMER_STATE_PATHS`, with a test and a validator fixture entry.
   The legacy-migration assertion skips it, since a never-synced file cannot
   appear in migration history.

2. **`check_runtime.py` reported permanent, unfixable drift.**
   `parity_matches` applied the project-name normalization only to
   `workspace.instructions.md`; every other file was byte-compared. Any file
   carrying the substituted project name (`CLAUDE.md`,
   `.claude/bootstrap-root/CLAUDE.md`, `.claude/instructions/workspace.md`)
   therefore failed forever, and no refresh could ever clear it. Normalization
   now applies to all comparisons, with a byte-compare fast path.

3. **A freshly generated tree failed its own validator.**
   `generate_targets.py` chmod'd `*.sh` only, but `protect-files.py` is in
   `REQUIRED_HOOK_SCRIPTS`, so `validate_targets.py` failed with
   `hook script is not executable`. The loop now covers every file in
   `hooks/scripts`, matching its own comment.

## Side Effects Worth Knowing

- The refresh writes the consumer ignore block into `.gitignore`. Already
  tracked files stay tracked; the installer prints a `git rm --cached` hint.
- **The refreshed hook guards are noticeably stricter.** They fail closed on
  opaque shell syntax, and during this session they denied several legitimate
  read-only commands: process substitution, heredocs piped into an interpreter,
  and any command whose write target came from a shell variable rather than a
  literal path. This is the fail-closed design working as specified, but it
  changes day-to-day ergonomics inside a refreshed repository. Documented in
  `docs/runtime-checks.md`.

This confirms the Phase M prediction that a refresh could change failure modes
rather than simply remove them.

## Verification Results

```bash
uv run python scripts/generate_targets.py --all                  # PASS twice
uv run python scripts/validate_targets.py                        # PASS
uv run pytest tests/ -q --tb=short                               # 129 passed
uv run mypy . --ignore-missing-imports --explicit-package-bases  # PASS, 19 files
uv run ruff check scripts/ tests/                                # PASS
uv run ruff format --check scripts/ tests/                       # PASS
uv run python scripts/validate_plan_frontmatter.py .claude/plans/*.md  # PASS
uv run python scripts/check_runtime.py                           # 1 FAIL (orphan skill)
```

`scripts/validate_plan_frontmatter.py` was reformatted by `ruff format`. It was
already failing `ruff format --check` before this branch; including the fix
makes the documented verification command pass.

## Score: 100/100 — EXCELLENCE

- Findings: `.claude/quality_reports/findings-20260809T031500Z.json`
- Score: `.claude/quality_reports/score-20260809T031500Z.json`

## [LEARN] Entries

- [LEARN:tooling] A guard that blocks the only legitimate use of a tool makes a
  real failure unactionable. The overlap check was correct in intent and made
  the bootstrap's own drift permanently unfixable; an explicit opt-in keeps the
  guard while restoring the case it wrongly caught.
- [LEARN:security] Before deleting anything as "obsolete", check whether it is
  deliberately never synced. `settings.local.json` is gitignored in `ai-state`
  by design, so removing it was unrecoverable data loss for every consumer.
- [LEARN:testing] Running a thing once found three bugs that a green suite had
  not: unrecoverable deletion, permanently unfixable drift, and a generated
  tree failing its own validator. All three needed execution, not more tests.
- [LEARN:tooling] Fail-closed shell classification denies process substitution,
  heredocs into an interpreter, and variable-derived write targets. Use literal
  paths and plain commands, or run a script from a file.

## Open Questions / Next Steps

- Decide the orphan skill: promote `safe-consumer-bootstrap-refresh` into
  `shared/skills/`, or delete it.
- Re-test the Codex hooks natively once quota resets (2026-08-15); the guards
  are now current but have not been exercised by a real client run.
