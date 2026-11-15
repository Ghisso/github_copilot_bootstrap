---
name: 2026-11-15_phase-I-knowledge-refresh
type: small-plan
parent_plan: skills-and-instructions-trim
phase_index: 9
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: complete
closeout_session_log: .claude/session_logs/2026-11-15_skills-trim-phase-I.md
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---

# Small Plan: 2026-11-15_phase-I-knowledge-refresh

## Scope

This is the final knowledge-refresh phase that the twice-reopened big plan needs, per the Knowledge-Refresh Final Phase rule in `.claude/instructions/plan-lifecycle.instructions.md`. It does four things:
- refreshes the OpenWiki pages that carry finding R29 or describe what Phase H changed, through OpenWiki's own tools;
- runs the standing final-phase documentation, memory, and LEARN audit;
- regenerates `dist/` and refreshes this repository, so that any audit fix to `shared/` reaches the generated and installed copies;
- records the audit under `## Stale-claims surfaces checked`.

Covers REQ-015 in the big plan. The phase owns the files its steps list; a file may be revisited after a review finding.

Risk notes:
- OpenWiki can time out right after the host boots. Reconnect with `/mcp` and retry.
- A provider failure blocks the phase. It is reported and retried, never skipped.
- OpenWiki evidence ranges must not start or end on a blank line ("Evidence does not resolve").

## Steps

- [x] **1. Refresh OpenWiki through its own tools.**
  - Owner: orchestrator, in the main session. Required Skills: `.claude/skills/knowledge-refresh/SKILL.md`, `.claude/skills/openwiki/SKILL.md`.
  - Call `openwiki_begin` with `mode: "update"`. Plan these pages plus every page OpenWiki flags:
    - `operations/install-ownership-and-runtime-checks.md` (R29):
      - the wrong-kind refusal (`Refusing to write over a path of the wrong kind:`) next to the symlink refusal, the copy-time guard, the recheck after the legacy migration, and the exact "not checked" list;
      - the state-README skip for an unsafe path or folder;
      - option A: an unmarked skill folder with a shipped name that no record lists is refused, with or without a record, and a project with no skill folders installs normally;
      - the stale `.agents/skills/` advice to move the folders aside;
      - the devcontainer write with `--state-remote` or an exported `AI_STATE_REMOTE`;
    - `quickstart.md`: its refusal list (line 66) names the refusal headings, so add the wrong-kind heading.
  - Right after `openwiki_begin`, run `git status --porcelain -- AGENTS.md CLAUDE.md` (the skill's restore check).
  - Reconcile every flagged claim, and require `openwiki_finish` to return `complete`.
  - Never hand-edit a generated page, a `.claims` file, or the root snippet.

- [x] **2. Audit live advice for stale claims.**
  - Owner: orchestrator; `documenter` for fixes in `README.md`, `docs/`, and `shared/`. Required Skills: `.claude/skills/documentation/SKILL.md`.
  - Surfaces: the standing final-phase audit list in `.claude/instructions/closeout.instructions.md`, and the orchestrator's user-level memory notes.
  - Claims to find:
    - an unmarked folder with a shipped name "is overwritten" when there is no record;
    - "delete the listed folders" for stale `.agents/skills/` folders;
    - per-file `git hash-object` presence as proof of an unmodified copy;
    - the symlink refusal described as covering every written path without the kind refusal and the copy-time guard, or "the preflight is complete";
    - the devcontainer write tied to `--state-remote` alone;
    - Decisions 8 to 12 described as awaiting the user's confirmation.
  - Correct each live claim in place. MEMORY entries are corrected, not appended to. A fix whose statement a generated page repeats goes through another OpenWiki `update`.
  - Leave dated records unchanged: archived plans, explorations, `docs/evidence/`, quality reports, and closed session logs.
  - Record each surface and its outcome under the exact heading `## Stale-claims surfaces checked`.

- [x] **3. Regenerate and refresh this repository.**
  - Owner: orchestrator. This always runs, even when Step 2 changed nothing in `shared/`. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`.

- [x] **4. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.
  - Focus:
    - the refreshed pages match the code they cite;
    - every audit fix that a page repeats went through another OpenWiki `update`;
    - the generated and installed copies match `shared/`;
    - no root adapter carries an OpenWiki block, and no `openwiki/.run.json` remains.

## Verification

<!-- Every non-comment line in a `bash`/`sh` block below is a required item:
     a shell command `verify closeout` runs itself, from the repository
     root, and that must exit 0. Never list `verify.py closeout` itself.
     Anything a script cannot run — an interactive probe, a host session, a
     manual inspection — belongs under `## Optional Verification` instead.
     See the Verification Evidence Contract in
     `.claude/instructions/workflow.instructions.md`. -->

```bash
uv run python scripts/generate_targets.py --all
uv run python -I -c 'import pathlib, sys; text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"); hits = [s for s in sys.argv[2:] if s in text]; sys.exit("stale text: " + "; ".join(hits) if hits else 0)' openwiki/operations/install-ownership-and-runtime-checks.md 'is still overwritten' 'delete the listed folders if you did not create them' 'when `--state-remote` is given.' 'without `--state-remote` it writes nothing' 'which needs the `bootstrap-root` copy'
grep -q -F 'Refusing to write through symlinks:' openwiki/operations/install-ownership-and-runtime-checks.md
grep -q -F 'Refusing to write over a path of the wrong kind:' openwiki/operations/install-ownership-and-runtime-checks.md
grep -q -F 'Refusing to write over a path of the wrong kind:' openwiki/quickstart.md
test ! -e openwiki/.run.json
test "$(grep -c -F '<!-- OPENWIKI:START -->' AGENTS.md)" = "0"
test "$(grep -c -F '<!-- OPENWIKI:START -->' CLAUDE.md)" = "0"
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

<!-- The only place a check may be conditional or non-executable. One `- `
     bullet per item, numbered in the order it appears. -->

- Read each refreshed page's prose against the code it cites, not only its flagged claims, and record any mismatch.

## Closeout Checklist

Run the numbered CLOSEOUT sequence in `.claude/instructions/closeout.instructions.md` in order. Tick both boxes at its step 2. Later steps bind this file's bytes, so do not edit this file after step 2.

- [x] Step 1: documentation updated, or skipped as pure-internal with a reason
- [x] Step 2: this plan set to `status: complete` with `closeout_session_log`, every step ticked, and LEARN entries or the no-lessons marker recorded

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record the three pause fields, and create a session log
with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it
does not require final findings, LEARN, DOCUMENT, or a completed closeout.
After the checkpoint commit, it may be pushed as a durable remote backup when
paused-publication invariants pass. It remains unfinished and blocks PR creation
and final closeout.
Keep the big plan `in-progress` with the same `current_phase`. On resume, read
the pause log and Git state, restore this plan to `in-progress`, and continue
this same phase without creating another small plan.
