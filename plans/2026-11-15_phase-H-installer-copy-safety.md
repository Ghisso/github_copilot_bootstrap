---
name: 2026-11-15_phase-H-installer-copy-safety
type: small-plan
parent_plan: skills-and-instructions-trim
phase_index: 8
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: in-progress
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

Covers REQ-014 in the big plan. Decisions 8 to 12 there, as the user confirmed or changed them on 2026-11-15, set the behavior. The phase owns the files its steps list; a file may be revisited after a failing-first test or a review finding. A separate read-only Opus devil's-advocate review challenged this plan before implementation, and its 13 points are folded in.

Review acceptance bar (the user's rule for guard and checker work): block only on a decision looser than before, a hole this change introduces, or a false or missing statement about what is checked. List any other pre-existing gap as a follow-up in `docs/target-mapping.md` instead of chasing it.

Risk notes:
- **Unsafe destination.** A write path is unsafe when any of these holds:
  - a link sits at any part of the path, from the target root down;
  - a part above the written path exists and is not a real folder;
  - a written file path exists and is not a regular file (for example a folder or a FIFO);
  - a written folder path exists and is not a real folder.
  One walker that never follows links decides this. It replaces `_first_symlink`, and the preflight, the state-README skip, and the copy-time guard all use it.
- **Before any write.** The refresh refuses every unsafe destination before any write. Links keep the heading `Refusing to write through symlinks:`. Every other case gets the exact heading `Refusing to write over a path of the wrong kind:`, with each path annotated (for example "a folder where the refresh writes a file"). Both lists appear in one refusal.
- **Copy-time guard.** The guard is a second line of defense and raises `SystemExit`.
  - It covers every file copy of a full refresh, through one helper; no other `shutil.copy2` call remains.
  - It covers every folder `copytree` creates. Each level's destination folder is checked in the `ignore` callback, which `copytree` runs before `os.makedirs` for that level.
  - If the preflight ever misses a path, the run stops there instead of writing through a link or into the wrong kind of path. That stop leaves a partial refresh. It is accepted, because the alternative is a write outside the project.
  - This reverses the Phase F note "No separate copy-time guard: the preflight is complete", which assumed a complete preflight.
- **After the legacy migration.** `migrate_pre_existing_state` runs after the preflights. Without `--local-only` it can merge remote AI state into `.claude/`. When it ran (pre-Git content, not a dry run), these three checks run again before the copy:
  - `validate_agents_takeover`;
  - `validate_project_skills`;
  - the link and kind preflight.
  A refusal at that point comes after the migration's own writes, and the docs say so.
- **State READMEs.** They are consumer state. A README whose path or folder is unsafe is skipped with a warning, not refused. `docs/runtime-checks.md` must stop saying these files are always overwritten.
- **Option A scope.**
  - A missing record never blocks an install by itself. Only an existing unmarked skill folder is refused: one that holds a `SKILL.md`, is not a claimed third-party bundle, has a name the new source ships, and is listed in no shipped-before record. A fresh project with no skill folders installs normally.
  - The record is the `bootstrap-root` copy of `.agents/skills`, or the live `.agents/skills/` when that copy is absent, as for every other check. This is consistent: `validate_agents_takeover` lets a live `.agents/` without a record copy through only when it equals the new source or the legacy record.
  - Option A is the only behavior change for skill folders. Every other refusal stays as strict as before.
- **Test fixtures.**
  - A fixture that models an installed consumer must carry the record its scenario names.
  - A fixture that models a project with no record tests the new refusal.
  - Never weaken an assertion to make a fixture pass.
  - A fixture that moves to another refusal branch must fail its test. Each refusal test asserts its own branch's message, not only fragments that two messages share.
- **Unchanged.** Sidecar mode, the `.agents` takeover rules, and the obsolete-file cleanup.
- **Not checked, stated in the docs.**
  - `state-sync.sh`'s own writes, the priority follow-up.
  - Hard links.
  - Whether macOS `strip_quarantine` (`xattr -rc` over whole folders, consumer state included) follows links.
  - Reads through links, for example `populate_bootstrap_root` copying a preserved, tracked adapter through a link into the AI state, which can then be pushed.
  Never write "never writes outside the project".
- **Docs.** Each guard is described by listing exactly what it covers and what it does not (`[LEARN:documentation]`). Check each sentence against the code before review.

## Steps

- [ ] **1. Write the failing tests first.**
  - Owner: `coder`. Files (modify): `tests/test_install_bootstrap.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - Every new or changed test name contains `destination_link`, `project_skill`, or `stale_agents`.
  - Every refusal case checks four things, reusing `_exact_snapshot`, `_make_outside`, and `_assert_run_refused`:
    - a non-zero exit;
    - the heading, and a message naming each path;
    - unchanged bytes and link targets in the target tree;
    - an unchanged outside sentinel.
  - `destination_link`, real runs (R24). Each case runs after `_installed_consumer`. A real folder replaces a generated file, with a link inside it that has the file's name and points to the sentinel:
    - the main copy: `.devcontainer/Dockerfile`, a generated file outside the obsolete-file cleanup;
    - tracked root guidance: `CLAUDE.md`, with the link inside it tracked by Git (`_git` add plus `_commit_tracked_paths`);
    - the install-record copy: `.claude/bootstrap-root/CLAUDE.md`.
  - `destination_link`, other cases, each refused before any write:
    - **Reverse kind.** A regular file at `.devcontainer`. Today `copytree` raises after `.agents`, `.claude`, and `.codex` were copied. Do not use `.claude/templates`: the obsolete-file cleanup deletes a file there, so that test could not fail today.
    - **Non-folder part above a written path.** A regular file at `.claude/bootstrap-root/.vscode`. Today `mkdir` raises after the copy.
    - **Not a regular file.** A FIFO at a generated file path.
    - **One run, two problems.** A kind problem and a link together, listed in one refusal under both headings.
    - **Dry run.** The dry run refuses a kind problem too.
  - `destination_link`, pass case: `.claude/plans/README.md` replaced by such a folder, and separately a regular file at `.claude/plans`. The run exits 0 and prints a warning naming the README. The folder, its link, the file, and the sentinel are unchanged.
  - `destination_link`, guard tests. Call each site directly, bypassing the preflight, one test per site:
    - the top-level file copy;
    - `copytree`, with a linked subfolder: nothing is created outside the target;
    - the state-README refresh;
    - `populate_bootstrap_root`, with a file adapter and a folder adapter;
    - the project-skill mirror.
    Each test makes the guard raise `SystemExit` and leaves the outside folder unchanged. A regular or missing destination still copies.
  - `destination_link`, after the migration. Patch `migrate_pre_existing_state` to plant a link at a written path. Assert that the run refuses, and that `copy_generated_tree` never runs (a spy).
  - `project_skill` (R26, option A):
    - **No record at all** (no `bootstrap-root` copy and no live `.agents/skills/`). An unmarked `.claude/skills/haystack/` with a `SKILL.md` and an extra file; the new source ships `haystack`. The run is refused before any write. The message contains `no shipped-before record was found` and `would overwrite it`. It names both remedies:
      - if the project wrote it, rename the folder and its `name:` line, then add `.project-skill`;
      - otherwise, move it out of `.claude/skills/`.
      This replaces `test_project_skill_unmarked_shipped_name_without_a_record_is_still_overwritten`.
    - **Record cases.** The three `PROJECT_SKILL_PASSES` fixtures become refusals:
      - `newly-shipped-name-with-no-record`;
      - `newly-shipped-name-with-only-the-live-agents-record`;
      - `newly-shipped-name-with-a-symlinked-record`.
      Fix the symlinked-record fixture's `mkdir` and link so it cannot crash.
    - **`_project_skill_world`.** It gets a `record` argument: `bootstrap-root` (the default), `live`, or `none`.
      - It writes `shipped` into the matching record.
      - For `none`, it leaves the target's unmarked `shipped` folder out.
      - The parametrized `none` and `live` cases keep their meaning.
      - `_refuse_marker_lost_former_project_skill_in_live_agents_only` must still reach the lost-marker branch.
      - The refusal tests assert that `.claude/skills/shipped` is not in the message unless the scenario expects it.
    - **Live-record pass, as a unit test.** It calls `validate_project_skills` directly, because a real run's `.agents` takeover check needs an exact generated tree. The live `.agents/skills/` lists the name, no `bootstrap-root` copy exists, and nothing is refused.
    - **Over-refusal guards** (refinement 1). A fresh Git repository with no `.claude/skills/` and no record installs with exit 0. So does one whose only skill folder is a marked project skill. These tests already pass today. Their mutation check is to make option A refuse whenever the record is missing, which must fail them.
  - `stale_agents` (R27): the explanation says to move the listed folders out of `.agents/skills/`, and never says to delete them unchecked. After the folders are moved, the refresh succeeds.
  - **Test discipline.**
    - Record each new test's first failing run in the session log.
    - Mutate each fix away once and confirm its test fails, then restore it byte-identical. This includes each guard call site and the post-migration recheck.

- [ ] **2. Refuse unsafe destinations before any write and guard every copy (R24).**
  - Owner: `coder`. Files (modify): `scripts/install_bootstrap.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - **The walker.** Replace `_first_symlink` with one walker that never follows links. For a target root, a relative path, and the expected kind (file or folder), it returns the first unsafe part and the reason, or nothing.
  - **The preflight** (`validate_no_symlink_writes`):
    - **Copy paths.** In the `visit` walk, with the same `_copy_rules` skips as the copy, use the walker for every path the copy writes. The kind comes from the generated source.
    - **Other written paths.** Use it for each path in the `written` list: the substitution files, `.gitignore`, `.claude/bootstrap-ownership.env`, the devcontainer file when a state remote is set, and each `.claude/bootstrap-root/<adapter>` path. A `bootstrap-root` adapter's kind comes from the generated source, or from the target when the copy step preserves that adapter.
    - **The refusal.** One refusal lists every problem under the two headings from the Scope. Links keep their remedy. Wrong kinds get "Move or rename each listed path, then rerun."
  - **The guard.** Add one small helper that refuses an unsafe destination (walker) by raising `SystemExit` with the path, then calls `shutil.copy2`.
    - Every file copy of a full refresh uses it: `copy_generated_tree` (the top-level file copy and `copytree`), `populate_bootstrap_root` (both branches), the state-README refresh, and `mirror_project_skills`. No other `shutil.copy2(` call remains in the file.
    - Every `shutil.copytree(` call passes `copy_function=` the helper and an `ignore` callback that checks the level's destination folder before `copytree` creates it. `copy_generated_tree` keeps its `copy_ignore` skips.
  - **After the migration.** When `migrate_pre_existing_state` ran (pre-Git content, not a dry run), run `validate_agents_takeover`, `validate_project_skills`, and the preflight again before `copy_generated_tree`.
  - **State-README refresh.** Skip, with a warning, a README whose path or folder the walker reports unsafe.
  - **Docstrings.** Keep the docstrings exact: what is checked, and the "not checked" list from the Scope.

- [ ] **3. Apply option A and the recovery wording (R26, R27).**
  - Owner: `coder`. Files (modify): `scripts/install_bootstrap.py`, `scripts/update_consumers.py` (docstring only, lines 21-23). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - **The refusal.** In `_skill_folder_problems`, refuse an unmarked folder holding `SKILL.md` that is not a claimed third-party bundle, whose name the new source ships and the record does not list, whatever the record is. The message says only what is known:
    - with a record, it keeps `does not list it` and `would overwrite it`;
    - with none, it says `no shipped-before record was found` and `would overwrite it`;
    - it gives the remedies from Step 1. The rename is needed because the name clashes with a shipped skill.
  - Every other message stays as it is.
  - **`_stale_agents_skills_note`.** Replace the "delete them" advice. The note says to move the listed folders out of `.agents/skills/` and rerun, and to delete them only once they are confirmed as old bootstrap copies.
  - **Comments.** Update every docstring and comment that describes Decision 9: `validate_project_skills`, `_shipped_before_record`, and the comment above the refusal.
  - **`update_consumers.py`.** The docstring says a legacy consumer with old skill copies and no record is refused once, listing each folder, until its folders are moved or marked.

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
      - Delete a folder only when its complete file list and contents equal that skill's folder at one bootstrap commit. Name the folder layout: `shared/skills/<name>/` in current history, and `skills/<name>/` in older commits. `dist/` is not in Git. One way: `git archive` that folder at the commit, then `diff -r`.
      - Otherwise, move the folder out of `.claude/skills/`, refresh, and compare the backup with the new copies.
      - For many folders, move every listed folder into one backup folder outside `.claude/`, refresh, then copy back the project's own skills.
      - To keep a project's own skill, keep its name and add `.project-skill`. Rename the folder and its `name:` line first only when the bootstrap ships that name.
    - **Step 8 (R27).** Move the stale folders aside; delete them only once they are confirmed as old bootstrap copies.
    - **Step 9 (R24, R28).**
      - The two refusal headings, the unsafe-destination rules, and the copy-time guard.
      - The recheck after the legacy migration.
      - The devcontainer check, with `--state-remote` or an exported `AI_STATE_REMOTE`.
      - The exact "not checked" list from the Scope.
  - `learn`: the no-record bullets now say the refresh refuses, never that it overwrites; the "every check except the newly-shipped-name refusal" sentence goes.
  - `README.md` and `docs/runtime-checks.md`:
    - **Project-skill section.** Remove "a newly shipped name is overwritten", "With no such record, an unmarked folder named like a shipped skill is overwritten", and "every check except the newly-shipped-name refusal".
    - **The refusal list.** Add both headings, the unsafe-destination rules, the guard, the recheck after the migration, and the "not checked" list.
    - **The "one exception" sentence.** Move the stale folders aside.
    - **The legacy-consumer bullet.** Such a consumer is refused once, with the bulk remedy.
    - **The devcontainer wording** (R28).
    - `docs/runtime-checks.md` "A refresh always overwrites these four files": name the skip.
  - `docs/target-mapping.md` follow-ups:
    - remove the `AI_STATE_REMOTE` wording item, which this phase fixes;
    - mark the `state-sync.sh` symlink gap as the priority follow-up;
    - add hard links and the macOS `strip_quarantine` question;
    - extend the `populate_bootstrap_root` read-through-link item: that content can be pushed to the AI-state remote;
    - record any new gap the review accepts.
  - `project-context` lines 72-75: name the newly-shipped-name refusal next to the never-shipped one.

- [ ] **5. Regenerate and refresh this repository.**
  - Owner: orchestrator. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`. This repository's own refresh must pass the new preflight and option A: every `.claude/skills/` folder here is either in its `bootstrap-root` record or the claimed `openwiki` bundle.

- [ ] **6. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`. State the acceptance bar from the Scope in the first-round prompt.
  - Focus:
    - every write of a full refresh is checked against the unsafe-destination rules, or is in the "not checked" list;
    - every new refusal happens before any write, except the post-migration recheck, which happens before the copy;
    - no Phase A or F refusal got looser;
    - the guard covers every `shutil.copy2` and every folder `copytree` creates;
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
uv run pytest tests/test_install_bootstrap.py tests/test_check_runtime.py tests/test_verify.py tests/test_sidecar_install.py tests/test_sidecar_update.py tests/test_sidecar_uninstall.py -q --tb=short
uv run python -I -c 'import pathlib, sys; text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"); hits = [s for s in sys.argv[2:] if s in text]; sys.exit("stale text: " + "; ".join(hits) if hits else 0)' README.md 'named like a shipped skill is overwritten' 'newly shipped name is overwritten' 'every check except the newly-shipped-name' 'one exception: delete folders'
uv run python -I -c 'import pathlib, sys; text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"); hits = [s for s in sys.argv[2:] if s in text]; sys.exit("stale text: " + "; ".join(hits) if hits else 0)' docs/runtime-checks.md 'every check except the newly-shipped-name' 'devcontainer.json` with `--state-remote`' 'A refresh always overwrites these four files'
uv run python -I -c 'import pathlib, sys; text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"); hits = [s for s in sys.argv[2:] if s in text]; sys.exit("stale text: " + "; ".join(hits) if hits else 0)' shared/skills/learn/SKILL.md 'refresh overwrites the folder' 'newly shipped name is overwritten' 'every check except the newly-shipped-name'
uv run python -I -c 'import pathlib, sys; text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"); hits = [s for s in sys.argv[2:] if s in text]; sys.exit("stale text: " + "; ".join(hits) if hits else 0)' shared/skills/safe-consumer-bootstrap-refresh/SKILL.md 'rev-list --all --objects' 'Delete the listed folders if you did not create them'
test "$(grep -c -F 'delete them and rerun' scripts/install_bootstrap.py)" = "0"
test "$(grep -c -F 'triggers both too, because' docs/target-mapping.md)" = "0"
test "$(grep -c -F 'shutil.copy2(' scripts/install_bootstrap.py)" = "1"
test "$(grep -c -F 'shutil.copytree(' scripts/install_bootstrap.py)" = "$(grep -c -F 'copy_function=' scripts/install_bootstrap.py)"
grep -q -F 'Refusing to write over a path of the wrong kind:' scripts/install_bootstrap.py
grep -q -F 'Refusing to write over a path of the wrong kind:' README.md
grep -q -F 'Refusing to write over a path of the wrong kind:' docs/runtime-checks.md
grep -q -F 'Refusing to write over a path of the wrong kind:' dist/multi-agent/.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md
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

- Rerun the round-2 reproduction in scratch folders: the four folder-over-file cases and the two controls. The script path is in the session log. Expected: the main copy, tracked `CLAUDE.md`, and record-copy cases are refused before any write. The README case is skipped with a warning. The sentinel is unchanged in every case.
- Real-consumer shapes, on scratch copies only, never the real repositories. `git clone` RAG, industrial-inspection, and img-classification into fresh `mktemp -d` folders. Copy in each one's git-ignored `.claude/` and `.agents/` when present. Then run a real `--local-only` refresh from `dist/multi-agent`.
  - RAG and industrial-inspection (record present): exit 0 and no refusal.
  - img-classification (no record): refused, listing its unmarked skill folders with the new wording. After every listed folder is moved into one backup folder outside `.claude/`, the refresh exits 0 and writes the record.
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
