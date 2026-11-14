# Session: Installer safety and project-skill guidance (skills-and-instructions-trim, Phase F)

**Date:** 2026-11-15
**Plan:** `.claude/plans/2026-11-14_phase-F-installer-safety.md`
**Status:** IN-PROGRESS

## Goal

Fix review findings R13 to R22 (`.claude/quality_reports/merges/2026-11-14_skills-and-instructions-trim-review-claude.md`): no write through a symlink anywhere in a full refresh, a refusal for an unmarked folder whose name is newly shipped, an honest no-record refusal, a robust mirror, a stray-marker check, an explanation for stale `.agents/` content on a second clone, learn and refresh-skill guidance, installer docs, and the mirror-update test (REQ-012).

## Work Log

- Phase E committed as `4aa49d4` and pushed; the post-commit hook set Phase F `in-progress` and moved `current_phase`. Material-impact check: Phase E changed only guidance, validators, and docs; nothing in it changes Phase F's installer design, so no planner run. Phase F starts from the plan as revised after the devil's-advocate review (big plan Decisions 8 to 11).
- Delegation by file ownership: `coder` took Steps 1-3 (`scripts/install_bootstrap.py`, the `runtime_ownership.py` comment, `scripts/validate_targets.py`, the two test files); `documenter` took Step 4 (learn, refresh skill, skill template, deep-audit, README, `docs/runtime-checks.md`, `docs/target-mapping.md`). Neither ran the generator or the validators.
- Coder: `copy_generated_tree`'s `should_preserve` and `copy_ignore` moved into `_copy_rules`, which the copy and the new `validate_no_symlink_writes` preflight share. The preflight runs in `main()` after the Copilot mode is known and before `migrate_pre_existing_state`, also under `--dry-run`. It covers the copy paths, the substitution files, `.gitignore`, `.claude/bootstrap-ownership.env`, every `.claude/bootstrap-root/` adapter path, and `.devcontainer/devcontainer.json` with `--state-remote`, and lists each link once at its topmost point. The state-folder README refresh skips a linked folder or file with a warning; `chmod_runtime_scripts` skips links. R14, R15, R17, R18, R19, R20 implemented as planned, plus the R14-assumption validator check (`SKILL_SURFACE_MISMATCH`) and the stray-marker check (`SKILL_PROJECT_MARKER_SHIPPED`), both also on the sidecar trees. The existing fixture `_pass_retired_skill_in_bootstrap_root_record` now lists `shipped` in its record, as R14 requires. Every new test failed first for the right reason; every fix, when removed, failed at least one test (three first-pass mutation survivors got tests and a chmod pattern fix), and all files were restored byte-identical. `tests/test_install_bootstrap.py` 220 passed. Flag: the preflight refuses a symlinked substitution file or `.gitignore` even when no write would happen (the plan's blanket rule; stricter, and today's code would write through it).
- Documenter: learn Phase 2 rows rewritten (consumers extend only marked skills; never edit a shipped one), Phase 3 lists the four unmarked-folder outcomes and "mark every project skill when you create it", the 300-character cap, Copilot wording; refresh skill steps 7-9 (no-record check with `git hash-object`, second-clone recovery, symlink refusal) and the retired-skill table; README refusal list and the one allowed `.agents/skills/` deletion; `docs/runtime-checks.md` and `docs/target-mapping.md` corrected.
- Integration found one problem: the retired-skill table's `references/...` paths resolved against the refresh skill's own folder (`SKILL_BROKEN_REFERENCE`, 8 errors). The orchestrator rewrote them as `.claude/skills/<skill>/references/<file>.md`. After: `generate_targets.py --all` exit 0; `install_bootstrap.py . --allow-self --local-only` exit 0 (this repository passes the new preflight); `validate_targets.py` PASS; `check_runtime.py` exit 0; `validate_plan_frontmatter.py` exit 0; every quick Verification item PASS.
- Optional checks, on scratch copies only: (1) symlink: a real install, then a shipped `SKILL.md` replaced by a link to an outside sentinel; the refresh exited 1 with `Refusing to write through symlinks:` naming `.claude/skills/learn/SKILL.md`; sentinel unchanged; link kept. (2) Real-consumer shapes (`git clone` plus copies of the git-ignored `.claude/`, `.agents/`, and root adapters; nested remotes removed so nothing could be pushed): RAG exit 0, no refusal (`.claude/skills` 40 = 37 shipped + OpenWiki's bundle + two empty leftover folders, `.agents/skills` 38); industrial-inspection exit 0, no refusal (37/37); img-classification exit 1, listing exactly the 22 old bootstrap folders with "no shipped-before record was found" and both remedies, and without "never shipped".

## [LEARN] Entries

## Verification

## Open Questions / Next Steps
