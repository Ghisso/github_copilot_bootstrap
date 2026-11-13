# Session: Project-owned skills (skills-and-instructions-trim, Phase A)

**Date:** 2026-11-13
**Plan:** `.claude/plans/2026-11-12_phase-A-project-owned-skills.md`
**Status:** COMPLETED

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
- Marker-lost fix (coder): failing-first 6 failed (3 marker-lost refusal cases `DID NOT RAISE SystemExit`, the mirror-equality test, 2 real-run marker assertions); after the fix `-k project_skill` 33 passed, the five installer/sidecar/runtime/verify test files 799 passed; ruff, format, mypy clean. A real-run step deletes the marker and confirms the refusal keeps `demo/SKILL.md`.
- Step 4: `generate_targets.py --all` exit 0; `install_bootstrap.py . --allow-self --local-only` exit 0 (only warning: the existing "some generated AI paths are already tracked by git"). `.claude/skills/openwiki/.openwiki-install.json` kept; `.agents/skills/` holds 56 folders (55 shipped plus `openwiki`).
- Required Verification block, orchestrator scratch runner: 13 items, 0 failed (`verify.py phase` PASS, 321.5 s).
- Optional 1 run: scratch Git repository, real `--local-only` install, marked `.claude/skills/demo/` added, second install (both exit 0). `.agents/skills/demo/` and its `bootstrap-root` copy hold `SKILL.md` and `.project-skill`. Isolated `codex debug prompt-input`: 61 entries, 61 unique; `demo` listed once from `r1` = `<tree>/.agents/skills`.
- Coder issue B: the learn skill lacked the standalone backticked tokens the new validator pin reads; the orchestrator reworded the paragraph to name `.project-skill` and `.agents/skills/` on their own.
- Review round 1 (six profiles: code, architecture, security, tests, ponytail, documentation): gate PASS, no CRITICAL or MAJOR, five MINORs, all fixed rather than disposed: (1) a marked folder under a symlinked `.claude` passed validation but `is_project_skill_dir` would not protect it, so the validator now refuses it ("marked but not protected"); (2) the mirror's destination-exists skip and `.agents`-not-a-directory refusal gained direct tests; (3) two stale test comments; (4) README and `docs/architecture.md` now say a folder holding a symlink or non-regular entry is not mirrored; (5) `_remove_tree` replaced by `shutil.rmtree`. Failing-first for (1): 1 failed (`DID NOT RAISE SystemExit`); mutations for (1) and (2) each fail their tests and were reverted byte-identical. After: `-k project_skill` 36 passed; the five installer/sidecar/runtime/verify test files 802 passed; ruff, format, mypy clean; regenerate + self-refresh 0; `validate_targets.py` PASS; `check_runtime.py` 0. Plan wording aligned to the scope change.
- Review round 2 (same reviewer, six profiles): gate PASS, 0 findings, no open requests.
- CLOSEOUT step 1: README (listing step, Project-owned skills section, full-install exceptions and refusals), `docs/architecture.md`, `docs/target-mapping.md`, learn and refresh skills. Not the big plan's last phase, so no standing audit here.
- CLOSEOUT step 2: small plan `status: complete`, boxes ticked; Phase A ticked in the big plan; one MEMORY entry (skill-listing probes).

## [LEARN] Entries

- [LEARN:tooling] Skill listings can be probed with no model call: `codex debug prompt-input` with an isolated `HOME`/`CODEX_HOME`, and `claude -p --setting-sources project --debug-file` (`--bare` reads no OAuth). The Claude overflow signal is `Skill listing over budget`, forced with `SLASH_COMMAND_TOOL_CHAR_BUDGET=1000`. Saved to `.claude/MEMORY.md`.
- [LEARN:installer] A record used to decide what a refresh may delete must not absorb copies the installer makes for the project. The unmarked mirror landed in the shipped-before record, so losing one marker file would have deleted a project skill as retired. Enforced by the marker-lost refusal tests, so no MEMORY entry.
- [LEARN:installer] A pre-write validator must use the same predicate as the pruner it protects (`is_project_skill_dir`); otherwise it accepts a layout (a symlinked `.claude`) that the pruner then deletes. Enforced by the `marked-folder-under-symlinked-claude` test, so no MEMORY entry.

## Verification

```text
PASS        0.3s  uv run python scripts/generate_targets.py --all
PASS        5.9s  uv run pytest tests/test_install_bootstrap.py tests/test_sidecar_install.py tests/test_sidecar_update.py -q --tb=short -k project_skill
PASS       92.4s  uv run pytest tests/test_install_bootstrap.py tests/test_check_runtime.py tests/test_verify.py tests/test_sidecar_install.py tests/test_sidecar_update.py -q --tb=short
PASS        0.0s  cmp scripts/runtime_ownership.py dist/multi-agent/.claude/scripts/runtime_ownership.py
PASS        0.0s  grep -q -F '.project-skill' dist/multi-agent/.claude/skills/learn/SKILL.md
PASS        0.0s  grep -q -F '.project-skill' dist/multi-agent/.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md
PASS        0.0s  grep -q -F 'bootstrap-root/.agents/skills' dist/multi-agent/.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md
PASS        0.0s  grep -q -F '.project-skill' README.md
PASS        0.0s  test -f .claude/skills/openwiki/.openwiki-install.json
PASS       48.0s  uv run python scripts/validate_targets.py
PASS        0.8s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS      322.5s  uv run python .claude/scripts/verify.py phase --format text
```

- Findings: `.claude/quality_reports/findings-2026-11-12_phase-A-project-owned-skills.json` (0 findings after review round 2; gate PASS; six profiles; round 1 had five MINORs, all fixed before round 2).
- Phase receipt: `verify.py phase --persist` PASS (pytest 5031 passed, 1 skipped; mypy 0 errors; Ruff 0 violations).
- optional 1: PASS — scratch Git repository, real `--local-only` install, marked `.claude/skills/demo/` added, second install (both exit 0); isolated `codex debug prompt-input` listed `demo` once from `r1` = `<tree>/.agents/skills` (61 entries, 61 unique).

## Open Questions / Next Steps

- Next: Phase B (instructions split and trims).
- User follow-up from spike S1: the 55 `[[skills.config]]` entries in the generated Codex config add no skills; removing them is the user's call.
