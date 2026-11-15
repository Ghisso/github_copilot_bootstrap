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

## [LEARN] Entries

## Verification

## Open Questions / Next Steps
