---
name: 2026-11-15_phase-H-installer-copy-safety
type: small-plan
parent_plan: skills-and-instructions-trim
phase_index: 8
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: planned
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---

# Small Plan: 2026-11-15_phase-H-installer-copy-safety

## Scope

The second review (`.claude/quality_reports/merges/2026-11-15_skills-and-instructions-trim-review-2.md`) found that a full refresh can still write outside the project. It also found that the no-record guidance proves too little before a deletion. This phase fixes findings R24 to R28:
- **R24.** A real folder that sits where the refresh copies a file makes `shutil.copy2` write to `<folder>/<name>`, and a link there is followed. This happens in the copy step, the state-folder README refresh, and the `bootstrap-root` record copy. A regular file where a folder is copied makes `copytree` stop partway. The docs claim the symlink refusal covers every written path.
- **R25.** The no-record recovery accepts per-file content found anywhere in the bootstrap's Git history as proof of an unmodified copy.
- **R26.** With no trustworthy record, an unmarked skill folder with a shipped name is overwritten. The user overturned Decision 9; option A refuses instead.
- **R27.** The stale `.agents/skills/` recovery says "delete" where "move aside" is the safe default.
- **R28.** The docs name only `--state-remote` for the devcontainer write; an exported `AI_STATE_REMOTE` triggers it too.

Covers REQ-014 in the big plan. Decisions 8 to 12 there, as the user confirmed or changed them on 2026-11-15, set the behavior. The phase owns the files its steps list; a file may be revisited after a failing-first test or a review finding.

Review acceptance bar (the user's rule for guard and checker work): block only on a decision looser than before, a hole this change introduces, or a false or missing statement about what is checked. List any other pre-existing gap as a follow-up in `docs/target-mapping.md` instead of chasing it.

Risk notes:
- **Kind refusals.** A kind mismatch is a folder where the refresh writes a file, or a regular file where it writes a folder. The refresh must refuse every kind mismatch before any write, the same way it refuses links. Links and kind mismatches are listed together in one refusal.
- **Copy-time guard.** The guard is a second line of defense. If the preflight ever misses a path, the run stops at that file instead of writing through a link or into a folder. A stop there leaves a partial refresh. That is accepted: the preflight should catch every case first, and the alternative is a write outside the project. This reverses the Phase F note "No separate copy-time guard: the preflight is complete", which assumed a complete preflight.
- **State READMEs.** They are consumer state. A README path that is a folder is skipped with a warning, like a linked one, not refused.
- **Option A scope.**
  - A missing record never blocks an install by itself. Only an existing unmarked skill folder (one that holds a `SKILL.md` and is not a claimed third-party bundle) whose name the new source ships, and that no shipped-before record lists, is refused. A fresh project with no skill folders installs normally.
  - The record is the `bootstrap-root` copy of `.agents/skills`, or the live `.agents/skills/` when that copy is absent, as for every other check.
  - Option A is the only behavior change for skill folders. Every other refusal stays as strict as before.
- **Test fixtures.** A fixture that models an installed consumer must carry a record, as every real install now writes one. A fixture that models a project with no record tests the new refusal. Never weaken an assertion to make a fixture pass.
- **Unchanged.** Sidecar mode, the `.agents` takeover rules, the obsolete-file cleanup, and `state-sync.sh`'s own writes, which stay a priority follow-up.
- **Docs.** Each guard is described by listing exactly what it covers and what it does not (`[LEARN:documentation]`, 2026-11-15). Check each sentence against the code before review.

## Steps

- [ ] **1. Write the failing tests first.**
  - Owner: `coder`. Files (modify): `tests/test_install_bootstrap.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - Every new or changed test name contains `destination_link`, `project_skill`, or `stale_agents`.
  - Every refusal case checks four things, reusing `_exact_snapshot`, `_make_outside`, and `_assert_run_refused`:
    - a non-zero exit;
    - a message naming each path;
    - unchanged bytes and link targets in the target tree;
    - an unchanged outside sentinel.
  - `destination_link` (R24). Use real installer runs after `_installed_consumer`. In each case a real folder replaces a generated file, and the folder holds a link with the file's name that points to the sentinel:
    - the main copy: `.devcontainer/Dockerfile`, a generated file outside the obsolete-file cleanup;
    - tracked root guidance: `CLAUDE.md`, with the link inside it tracked by Git (`_git` add plus `_commit_tracked_paths`);
    - the install-record copy: `.claude/bootstrap-root/CLAUDE.md`;
    - the reverse kind: a generated folder (`.claude/templates`) replaced by a regular file;
    - one run with a kind mismatch and a link together, refused once and listing both;
    - the dry run refuses a kind mismatch too.
    - Pass case: `.claude/plans/README.md` replaced by such a folder. The run exits 0, prints a warning naming the README, and leaves the folder, its link, and the sentinel unchanged.
    - Guard unit test: the copy helper refuses three destinations, and the destination is unchanged afterwards:
      - a link;
      - a real folder;
      - a path under a linked folder below the target root.
      It copies to a regular or missing destination.
  - `project_skill` (R26, option A):
    - No record at all (no `bootstrap-root` copy and no live `.agents/skills/`): an unmarked `.claude/skills/haystack/` with a `SKILL.md` and an extra file. The new source ships `haystack`. The run is refused before any write. The message says that no shipped-before record was found and that the refresh would overwrite the folder. It names both remedies: if the project wrote it, rename the folder and its `name:` line and add `.project-skill`; otherwise move it out of `.claude/skills/`. This replaces `test_project_skill_unmarked_shipped_name_without_a_record_is_still_overwritten`.
    - The three `PROJECT_SKILL_PASSES` fixtures become refusals:
      - `newly-shipped-name-with-no-record`;
      - `newly-shipped-name-with-only-the-live-agents-record`;
      - `newly-shipped-name-with-a-symlinked-record`.
    - New pass: the live `.agents/skills/` lists the name and no `bootstrap-root` copy exists, so the folder is overwritten, as for every other stand-in check.
    - Refinement 1: a fresh Git repository with no `.claude/skills/` and no record installs with exit 0. So does one whose only skill folder is a marked project skill.
    - Every existing fixture that models an installed consumer (for example `_project_skill_world`) writes the shipped-before record for its shipped names, so that it keeps testing what it tested before.
  - `stale_agents` (R27): the explanation says to move the listed folders out of `.agents/skills/`. It never says to delete them unchecked. After the folders are moved, the refresh succeeds.
  - Record each new test's first failing run in the session log. Mutate each fix away once and confirm its test fails, then restore it byte-identical.

- [ ] **2. Refuse kind mismatches before any write and guard every copy (R24).**
  - Owner: `coder`. Files (modify): `scripts/install_bootstrap.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - In `validate_no_symlink_writes`, also collect kind mismatches:
    - in the `visit` walk, which uses the same `_copy_rules` skips as the copy: a source file whose destination is a real folder, or a source folder whose destination exists and is not a folder;
    - for the written files outside the copy walk (the substitution files, `.gitignore`, `.claude/bootstrap-ownership.env`, and the devcontainer file when a state remote is set): an existing real folder at the path;
    - for each `.claude/bootstrap-root/<adapter>` path `populate_bootstrap_root` writes: an existing entry of the other kind. The adapter's kind comes from the generated source, or from the target when the copy step preserves that adapter.
  - One refusal lists every problem. Links keep the heading `Refusing to write through symlinks:` and their remedy. Kind mismatches get their own heading, which names both directions (a file over a folder, a folder over a file), and a remedy: move or rename each listed path, then rerun.
  - **Copy-time guard.** Add one small helper that wraps `shutil.copy2`. It refuses when the destination is a link, is a real folder, or sits under a linked folder below the target root. Its message names the path. Every file copy of a full refresh uses it:
    - `copy_generated_tree`: the top-level file copy, and `copytree` through `copy_function`;
    - `populate_bootstrap_root`: both branches;
    - the state-README refresh;
    - `mirror_project_skills`.
  - **State-README refresh.** Also skip, with a warning, a README path that is a folder.
  - Keep the docstring of `validate_no_symlink_writes` exact: what is checked and what is not (`state-sync.sh`'s own writes).

- [ ] **3. Apply option A and the recovery wording (R26, R27).**
  - Owner: `coder`. Files (modify): `scripts/install_bootstrap.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - `_skill_folder_problems`: refuse an unmarked folder holding `SKILL.md` whose name the new source ships and the record does not list, whatever the record is. The message says only what is known:
    - it names the record path that lacks the name, or says that no shipped-before record was found, so the refresh cannot tell an old bootstrap copy from the project's own skill;
    - it says the refresh would overwrite the folder;
    - it gives the remedies from Step 1. The rename is needed here because the name clashes with a shipped skill.
  - Every other message stays as it is.
  - `_stale_agents_skills_note`: replace the "delete them" advice. The note says to move the listed folders out of `.agents/skills/` and rerun, and to delete them only once they are confirmed as old bootstrap copies.
  - Update the docstrings and comments that describe Decision 9:
    - `validate_project_skills`;
    - `_shipped_before_record`;
    - the comment above the refusal.

- [ ] **4. Correct the guidance and docs (R24 to R28).**
  - Owner: `documenter`. Files (modify):
    - `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md`;
    - `shared/skills/learn/SKILL.md`;
    - `README.md`;
    - `docs/runtime-checks.md`;
    - `docs/architecture.md`, only where it states what is refused before a write;
    - `docs/target-mapping.md`;
    - `.claude/instructions/project-context.instructions.md`, lines 72-75.
  - Required Skills: `.claude/skills/documentation/SKILL.md`.
  - `safe-consumer-bootstrap-refresh`:
    - **Step 6.** Newly shipped names: the refusal now applies with any record or none. Rename only on a name clash.
    - **Step 7 (R25).** The no-record recovery. Run the installer with `--dry-run` and read the listed folders.
      - Delete a folder only when its complete file list and contents equal that skill's folder at one bootstrap commit. One way: `git archive` that folder at the commit, then `diff -r`.
      - Otherwise, move the folder out of `.claude/skills/` (for example to a backup folder outside `.claude/`), refresh, and compare the backup with the new copies.
      - To keep a project's own skill, keep its name and add `.project-skill`. Rename the folder and its `name:` line first only when the bootstrap ships that name.
    - **Step 8 (R27).** Move the stale folders aside; do not delete them.
    - **Step 9 (R24, R28).**
      - Add the kind refusal and the copy-time guard.
      - Say that the devcontainer check applies with `--state-remote` or an exported `AI_STATE_REMOTE`.
      - Keep the exact "not checked" list.
  - `learn`: the no-record bullets now say the refresh refuses, never that it overwrites.
  - `README.md` and `docs/runtime-checks.md`:
    - the project-skill section, including "a newly shipped name is overwritten" and "With no such record, an unmarked folder named like a shipped skill is overwritten";
    - the refusal list, with the kind refusal and the copy-time guard;
    - the "one exception" sentence: move the stale folders aside;
    - the devcontainer wording (R28).
  - `docs/target-mapping.md` follow-ups:
    - remove the `AI_STATE_REMOTE` wording item, which this phase fixes;
    - mark the `state-sync.sh` symlink gap as the priority follow-up;
    - record any new gap the review accepts.
  - `project-context` lines 72-75: name the newly shipped refusal next to the never-shipped one.

- [ ] **5. Regenerate and refresh this repository.**
  - Owner: orchestrator. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`. This repository's own refresh must pass the new preflight and option A: every `.claude/skills/` folder here is listed in its `bootstrap-root` record.

- [ ] **6. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`. State the acceptance bar from the Scope in the first-round prompt.
  - Focus:
    - no file a full refresh copies can be reached through a link or written into a folder;
    - every new refusal happens before any write;
    - no Phase A or F refusal got looser;
    - the copy-time guard covers every `shutil.copy2` and `copytree` call of the full install;
    - option A blocks only uncertain unmarked skill folders;
    - messages say only what the code knows;
    - the docs and skills match the code, guard by guard;
    - sidecar mode is untouched.

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
uv run pytest tests/test_install_bootstrap.py -q --tb=short -k "destination_link or project_skill or stale_agents"
uv run pytest tests/test_install_bootstrap.py tests/test_check_runtime.py tests/test_verify.py tests/test_sidecar_install.py tests/test_sidecar_update.py -q --tb=short
test "$(grep -c -F 'rev-list --all --objects' shared/skills/safe-consumer-bootstrap-refresh/SKILL.md)" = "0"
test "$(grep -c -F 'delete them and rerun' scripts/install_bootstrap.py)" = "0"
test "$(grep -c -F 'Delete the listed folders if you did not create them' shared/skills/safe-consumer-bootstrap-refresh/SKILL.md)" = "0"
test "$(grep -c -F 'refresh overwrites the folder' shared/skills/learn/SKILL.md)" = "0"
test "$(grep -c -F 'named like a shipped skill is overwritten' README.md)" = "0"
test "$(grep -c -F 'triggers both too, because' docs/target-mapping.md)" = "0"
grep -q -F 'AI_STATE_REMOTE' dist/multi-agent/.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md
grep -q -F 'Refusing to write through symlinks:' scripts/install_bootstrap.py
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

<!-- The only place a check may be conditional or non-executable. One `- `
     bullet per item, numbered in the order it appears. -->

- Rerun the round-2 reproduction in scratch folders (the four folder-over-file cases and the two controls; script kept in the session log). Expected: the main copy, tracked `CLAUDE.md`, and record-copy cases are refused before any write. The README case is skipped with a warning. The sentinel is unchanged in every case.
- Real-consumer shapes, on scratch copies only, never the real repositories. `git clone` RAG, industrial-inspection, and img-classification into fresh `mktemp -d` folders. Copy in each one's git-ignored `.claude/` and `.agents/` when present. Then run a real `--local-only` refresh from `dist/multi-agent`.
  - RAG and industrial-inspection (record present): exit 0 and no refusal.
  - img-classification (no record): refused, listing its unmarked skill folders with the new wording. After every listed folder is moved out of `.claude/skills/`, the refresh exits 0 and writes the record.
  - Record the outputs.

## Closeout Checklist

Run the numbered CLOSEOUT sequence in `.claude/instructions/closeout.instructions.md` in order. Tick both boxes at its step 2. Later steps bind this file's bytes, so do not edit this file after step 2.

- [ ] Step 1: documentation updated, or skipped as pure-internal with a reason
- [ ] Step 2: this plan set to `status: complete` with `closeout_session_log`, every step ticked, and LEARN entries or the no-lessons marker recorded

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
