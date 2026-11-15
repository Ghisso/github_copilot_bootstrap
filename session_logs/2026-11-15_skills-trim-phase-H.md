# Session: Installer copy safety and the no-record refusal (skills-and-instructions-trim, Phase H)

**Date:** 2026-11-15
**Plan:** `.claude/plans/2026-11-15_phase-H-installer-copy-safety.md`
**Status:** IN-PROGRESS

## Goal

Fix second-review findings R24 to R28 (`.claude/quality_reports/merges/2026-11-15_skills-and-instructions-trim-review-2.md`) (REQ-014):
- R24: no file copy of a full refresh may write through a link or into a folder. A kind mismatch is refused before any write, and every copy is guarded.
- R25: an exact deletion proof in the refresh skill.
- R26: option A for unrecorded shipped names (user decision, 2026-11-15).
- R27: move-aside wording for stale `.agents/skills/` folders.
- R28: the `AI_STATE_REMOTE` wording.

## Work Log

- The second review, shared by the user, held the PR on R24 and R25. The main agent reproduced R24 in scratch folders with real installer runs. The outside sentinel was overwritten through `.devcontainer/Dockerfile` (exit 0), `.claude/plans/README.md` (exit 0), `.claude/bootstrap-root/CLAUDE.md` (exit 0), and a `CLAUDE.md` folder holding a Git-tracked link (exit 1, after the write). Two controls stayed safe because the obsolete-file cleanup unlinks the planted link first: `.claude/agents/coder.md`, and `CLAUDE.md` with an untracked link. Script: `/tmp/claude-1000/-home-ghisso-work-github-copilot-bootstrap/6501bedf-edf7-4f48-ab59-744ddbaef609/scratchpad/repro_dir_mismatch/test_repro_dir_mismatch.py`.
- A whole-folder history check (`skill_history_match.py` in the same scratchpad) found that each of img-classification's 52 skill folders equals one past bootstrap version exactly.
- The user chose option A for Decision 9, with the second reviewer's three refinements, and confirmed Decisions 8, 10, 11, and 12. The user also said that consumers exist on other computers, so a local survey is never the full list.
- Big plan reopened a second time per `.claude/instructions/plan-lifecycle.instructions.md`:
  - findings report written;
  - Phases H and I drafted as `planned` and appended;
  - `status: in-progress`, with `current_phase` set to Phase H;
  - Done Criteria, Requirement Map, and Completion Evidence updated;
  - `validate_plan_frontmatter.py` exit 0.
- Devil's-advocate round on Phases H and I: a separate read-only Opus subagent at `xhigh` effort with the devils-advocate skill. Verdict: hold until items 1 to 4 change.
  - **HIGH.**
    - (1) The fixture guidance would lose test intent: `_project_skill_world` needs a `record` argument (`bootstrap-root`, `live`, `none`), and one lost-marker fixture would silently move branches.
    - (2) The kind check missed non-folder parts above a written path, and FIFOs. One walker that never follows links replaces `_first_symlink`.
    - (3) A `copy_function` guard does not cover `copytree`'s own `makedirs`. Each level's destination folder is now checked in the `ignore` callback, and the guard raises `SystemExit`.
  - **MEDIUM.**
    - (4) `migrate_pre_existing_state` runs after both preflights and can merge remote state into `.claude/`. The pre-write checks now run again after it. The main agent added `validate_agents_takeover` to that rerun, because the migration can change the `.agents` record copy.
    - (5) Add direct-call guard tests per call site, and pins on `shutil.copy2(` and `copy_function=`.
    - (6) The reverse-kind test moves to `.devcontainer`, because the cleanup deletes a file at `.claude/templates`.
    - (7) Missing absence checks, the exact wrong-kind heading, and Phase I checks that already passed.
  - **LOW.**
    - (8) Keep the live-record stand-in; its pass case becomes a unit test.
    - (9) Keep the guard; it is uniform across copies.
    - (10) Doc exactness: the "always overwrites these four files" line, the R25 folder layouts, the message pins, and the quickstart page.
    - (11) Add hard links, `strip_quarantine`, and reads through links to "not checked".
    - (12) The `update_consumers.py` docstring, and the bulk remedy for legacy consumers.
    - (13) The third-party bundle exception in the change to Decision 9.
  - All 13 were folded into the plans; Phase I's verification now uses absence checks plus the new heading. Every new absence check was confirmed to fail on today's text.
- Steps 1 to 3 went to the `coder`, which owned `scripts/install_bootstrap.py`, the `scripts/update_consumers.py` docstring, and `tests/test_install_bootstrap.py`. It did not run the generator, validators, or `verify.py`.
  - **Code.**
    - `_unsafe_destination`, an `lstat` walker that never follows a link, replaces `_first_symlink`.
    - `_require_safe_destination` raises `SystemExit`. `_copy_file` is the only `shutil.copy2` call. `_guard_levels` is the `copytree` `ignore` callback that checks each level's folder before it is created.
    - The preflight checks every copy path, every written file, and every `bootstrap-root` adapter path (kind from the source, or from the target for a preserved adapter). It refuses once, under two headings: `Refusing to write through symlinks:` and `Refusing to write over a path of the wrong kind:`, with reasons such as "a folder where the refresh writes a file".
    - Every copy site uses the guard, and the state-README refresh skips an unsafe path with a warning.
    - `populate_bootstrap_root` now checks the record folder before its `rmtree`, so a link above it cannot lead the removal outside. This replaces the old `Unsafe bootstrap-root adapter destination` branch, which the new check made unreachable.
    - `main()` reruns the takeover, project-skill, and link and kind checks after a legacy migration (`had_pre_existing_content and not args.dry_run`).
    - Option A is in `_skill_folder_problems`. The stale-folder note says to move the folders aside.
  - **First failing run** against the unchanged installer: 36 failed, 74 passed.
    - The three real-run copy cases overwrote the sentinel (exit 0) or failed after the write.
    - The reverse-kind, non-folder-above, and FIFO cases ended in a Python traceback from `copytree` or `mkdir` (`[Errno 17] File exists`), with no heading.
    - The guard unit tests did not raise `SystemExit`.
    - The recheck tests failed with "the copy ran before the recheck".
    - Option A's no-record, live-record, and symlinked-record cases did not raise.
    - The stale note lacked the move-aside text.
    - The over-refusal guards passed first, as planned. Raw outputs are in the scratchpad (`first_failing.txt`).
  - **Mutation checks.** 30 code mutations (M01 to M30) and 2 fixture mutations (T1, T2). Each failed at least one test, and each restore was byte-identical (sha256). Raw outputs: `mutation_results_run1.txt`, `mutate.py`.
  - **Stubbed wiring tests.** Four guard sites cannot be reached with real file-system state, so their tests stub the walker: the README copy after its skip, the mirror's own new folder, and populate's `ignore` and `copy_function` after its removal.
  - **Results.** `tests/test_install_bootstrap.py` 260 passed; the wider plan run 931 passed; ruff and mypy clean.
- **Main-agent check of the diff.**
  - Read every hunk against the plan. Reran `tests/test_install_bootstrap.py`: 260 passed. Pins: `shutil.copy2(` 1, `shutil.copytree(` 2, `copy_function=` 2.
  - Probed `Path.rglob("*")`, used by the obsolete-file cleanup for root adapter folders. On Python 3.12.3 and 3.13.6 it lists a link to a folder but does not go into it, so the cleanup cannot delete through one.
  - Fixed the `update_consumers.py` docstring: marking alone fails for a folder whose name the bootstrap ships (name clash), so it says to rename first.
- **Behavior change to document.** The preflight now refuses kind mismatches that the obsolete-file cleanup used to resolve silently. Examples: a regular file at `.claude/templates`, and a folder holding an untracked link at `CLAUDE.md` or `.claude/agents/coder.md` (round 2's "safe controls"). So a bootstrap version that turns a generated file into a folder, or the reverse, makes each refresh refuse until the old item is moved. This is stricter, not looser. It is kept simple on purpose, and narrowing it is recorded as a follow-up.
- **Round-2 reproduction rerun** on the fixed installer, with the same script and the current `dist/multi-agent`. The sentinel was unchanged in all six cases.
  - `.claude/plans/README.md`: exit 0, skipped with a warning.
  - Refused with exit 1: `.devcontainer/Dockerfile`, `.claude/bootstrap-root/CLAUDE.md`, the tracked `CLAUDE.md` link, and, under the stricter rule, both former controls (`.claude/agents/coder.md`, and `CLAUDE.md` with an untracked link).
- **Scratch consumer copies** for optional check 2 were made by `prep_consumer_copies.py` in the scratchpad: `git clone` plus the git-ignored bootstrap paths, links preserved, every outer and nested remote removed. RAG and industrial-inspection have the record; img-classification has none.
- Step 4 went to the `documenter`: the files listed in the plan, with the exact message texts and coverage lists taken from the verified diff.
- **Documenter result.**
  - Edits landed in all seven files. The project-context edit was committed into the nested repository by the automatic `session:` checkpoint.
  - The main agent read each new claim against the code: the refresh skill's steps 6 to 9, the README, `docs/runtime-checks.md`, `learn`, and the target-mapping follow-ups.
  - One README fix: a legacy consumer is refused when it has "no shipped-before record", not "no `.claude/bootstrap-root/` record". A live `.agents/skills/` can stand in.
- **Step 5.** `generate_targets.py --all` exit 0. `install_bootstrap.py . --allow-self --local-only` exit 0: this repository passes the new preflight and option A. The only warning is the usual one about tracked authoring adapters. `validate_targets.py` PASS, `check_runtime.py` exit 0, `validate_plan_frontmatter.py` exit 0, and every quick Verification line PASS.
- **Optional check 2** (scratch copies, no remotes; refreshed with `--local-only` from `dist/multi-agent`):
  - RAG: exit 0.
  - industrial-inspection: exit 0.
  - img-classification: exit 1, listing 52 unmarked folders: the 30 with shipped names under option A, with "no shipped-before record was found", and the 22 never-shipped ones. `move_listed_skills.py` then moved all 52 into one backup folder outside `.claude/`. The rerun exited 0, wrote the record (37 names), and installed the 37 shipped skills.
- **`verify.py phase --format text`** before review: PASS. Ruff 0, mypy 0, pytest 5235 passed and 1 skipped, freshness and generation PASS.

## [LEARN] Entries

## Verification

## Open Questions / Next Steps
