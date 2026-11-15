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
- Devil's-advocate round on Phases H and I started: a separate read-only Opus subagent at `xhigh` effort with the devils-advocate skill.

## [LEARN] Entries

## Verification

## Open Questions / Next Steps
