# Session: Project-owned skills (skills-and-instructions-trim, Phase A)

**Date:** 2026-11-13
**Plan:** `.claude/plans/2026-11-12_phase-A-project-owned-skills.md`
**Status:** IN-PROGRESS

## Goal

Let a consumer project keep its own skills across full-install refreshes: a `.claude/skills/<name>/` folder holding a regular `.project-skill` file is never deleted or overwritten, is mirrored without the marker to `.agents/skills/<name>/`, and unsafe or unmarked never-shipped skill folders are refused before any write (REQ-001).

## Work Log

- Approval: the user asked to implement the whole big plan on 2026-11-13. That approves the plan and its seven "Decisions for the user" as written.
- PRE-FLIGHT: `dev` clean in both repositories at `cfde280`; plan files read; MEMORY searched by area (installer, closeout, generation, OpenWiki, branch hook) through Context Mode.
- Pre-branch spike: `.claude/explorations/2026-11-12_skills-trim-client-spike/REPORT.md`. S1 success (55 shipped skills listed once from `.agents/skills/`; config-only run lists none), S3 recorded (891-character description shown cut to 404 characters), S4 success (`spike-project-skill` listed once), S5 working control with no baseline warning (`--bare` could not authenticate; `--setting-sources project` ran). No plan change before the branch.
- BRANCH: `git checkout -b skills-and-instructions-trim_implementation`; the hook set the big plan `in-progress` (`started_at: 2026-11-13T11:54:23Z`) and Phase A `in-progress`.
- IMPLEMENT, parallel on disjoint files: coder (Steps 1-2 and the Step 3 validator line), documenter (Step 3 docs).
- Coder failing-first: `-k project_skill` over the three Step 1 files gave 30 failed, 2 passed (the 2 sidecar pins, which also pass after). Failures: 26 `AttributeError` (no `validate_project_skills` / `mirror_project_skills`), 1 `ImportError` (`is_project_skill_dir`), the two-refresh test `assert {} == {...}` (marked folder pruned: the RAG loss), the real-run test (legacy-path `demo` deleted), the clash real-run test (no mirror). After Step 2: three Step 1 files 406 passed; `test_check_runtime.py` + `test_verify.py` 390 passed; ruff, format, mypy clean. Mutations (each reverted byte-identical): dropping the `owned_files()` pruning, accepting a symlinked `SKILL.md`, and dropping the mirror's link checks each fail their tests.
- Why no other `runtime_ownership` importer needs the rule (coder): `verify.py`'s root-adapter comparison reads only `.agents/` and its `bootstrap-root/.agents/` copy, and `populate_bootstrap_root` records the mirror, so both sides hold the same tree; its nested-runtime fingerprint already binds the project skill under `.claude/`. `check_runtime.py` covers this authoring repository, which keeps its skills in `shared/skills/` and has no marked folders. `generate_targets.py` only copies the module into `dist`. `validate_targets.py` and `sidecar_overlay.py` read other constants and never decide ownership of `.claude/skills/<name>`. Sidecar mode never touches team skills; the two sidecar pin tests show the marker is inert there.
- Coder deviations accepted: the "marker-claimed directory at `.agents/skills/<name>`" clause is covered by the third-party shape check (a claimed bundle has that shape by definition); a marked folder with a missing or unparseable `name:` or no regular `SKILL.md` is refused; "marked" during validation means an entry named `.project-skill` exists (`lexists`), so a symlinked or directory marker is refused rather than read as unmarked; `mirror_project_skills` warns and skips when `.agents/skills/<name>` already exists after pruning, and stops with an error naming the path when `.agents` or `.agents/skills` is a link or not a directory.
- Scope change (orchestrator): coder issue A — an unmarked mirror lands in the shipped-before record, so a project skill that lost its `.claude` marker would be deleted as retired. Fix: the mirror keeps the marker, and validation refuses an unmarked folder whose record copy holds `.project-skill`. Recorded in the big plan's Design Overview. Docs updated by the orchestrator (README, `docs/architecture.md`, `docs/target-mapping.md`, refresh skill step 6).
- Coder issue B: the learn skill lacked the standalone backticked tokens the new validator pin reads; the orchestrator reworded the paragraph to name `.project-skill` and `.agents/skills/` on their own.

## [LEARN] Entries

## Verification

## Open Questions / Next Steps
