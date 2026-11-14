---
name: 2026-11-14_phase-F-installer-safety
type: small-plan
parent_plan: skills-and-instructions-trim
phase_index: 6
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: in-progress
closeout_session_log:
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---

# Small Plan: 2026-11-14_phase-F-installer-safety

## Scope

The 2026-11-14 review found that a full refresh can still damage files it should not touch, and that the project-skill guidance still sends lessons where a refresh destroys them. This phase fixes findings R13 to R22 of `.claude/quality_reports/merges/2026-11-14_skills-and-instructions-trim-review-claude.md`:
- a refresh writes through a symlink (a file that only points to another file) at a destination path, so it can overwrite a file outside the repository (R13, pre-existing);
- an unmarked skill folder is overwritten when the new source starts shipping its name, although the shipped-before record shows the last install did not ship it (R14);
- the refusal for consumers without a record calls old bootstrap copies "never shipped" and suggests marking them (R15);
- the learn skill tells consumer agents to edit shipped skills and promises a refusal that does not always happen (R16);
- a second, existing clone keeps retired `.agents/skills/` folders and its next refresh is refused with no explanation (R17);
- the mirror silently drops unreadable subfolders and copies Python caches (R18); a stray marker in a shipped skill would block every consumer (R19); the preflight reads through a refused link (R20);
- installer documentation is outdated, and a code comment states a false incident (R21); the mirror-update promise has no test (R22).

Covers REQ-012 in the big plan; Decisions 8 to 11 there set the behavior. The phase owns the files its steps list; a file may be revisited after a failing-first test or a review finding.

Review acceptance bar (the user's rule for guard and checker work): block only on a decision looser than before, a hole this change introduces, or a false or missing statement about what is checked. List any other pre-existing gap as a follow-up in `docs/target-mapping.md` instead of chasing it.

Risk notes:
- The symlink refusal covers every path a full refresh writes, not only the copy step:
  - the copy step's paths;
  - the project-name and Python-version substitution files (`PROJECT_NAME_FILES`, `PYTHON_FACT_FILES`), even when they are preserved tracked adapters;
  - `.gitignore`;
  - `.claude/bootstrap-root/` with every path `populate_bootstrap_root` writes or removes there, and `.claude/bootstrap-ownership.env`;
  - `.devcontainer/devcontainer.json` when `--state-remote` is given.
- The copy step never writes existing consumer state, other preserved tracked adapters, marker-claimed third-party bundles, or marked project skills, so a link there is not refused. A state-folder README (`STATE_DIR_OWNED_README_PATHS`) whose folder or file is a link is skipped with a warning instead: it is consumer state.
- Every new refusal must happen before any write. The existing tests' pattern (target-tree snapshot plus an outside sentinel) proves it.
- Sidecar mode returns before both full-install checks; it must stay untouched.
- Decision 10 keeps the second-clone fix to an explanation and documentation; automatic deletion stays a follow-up.

## Steps

- [ ] **1. Write the failing tests first.**
  - Owner: `coder`. Files (modify): `tests/test_install_bootstrap.py`, `tests/test_validate_targets.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - Every new test name contains `project_skill`, `destination_link`, or `stale_agents`. Every refusal case checks four things: a non-zero exit; a message naming each path; unchanged bytes and link targets in the target tree; an unchanged outside sentinel (reuse `_exact_snapshot` and `_make_outside`).
  - `destination_link` (R13), with real installer runs; each refusal lists every offending path at once:
    - a shipped `.claude/skills/<name>/SKILL.md` replaced by a link to the outside sentinel;
    - a generated hook script replaced by a link;
    - a generated directory (for example `.claude/templates`) replaced by a link to an outside directory;
    - `.claude/bootstrap-root` replaced by a link to an outside directory (today `populate_bootstrap_root` deletes and writes through it);
    - `.gitignore` replaced by a link;
    - a preserved tracked `CLAUDE.md` replaced by a link (the substitutions write it);
    - `.claude` itself replaced by a link.
    - Pass cases: a symlinked consumer-state path that already exists (for example `.claude/settings.local.json`) is not refused. A symlinked `.claude/plans` folder is not refused, its `README.md` refresh is skipped with a warning, and nothing is written through it. `chmod_runtime_scripts` skips a linked script instead of changing its target.
  - `project_skill`:
    - R14: the `bootstrap-root` record exists and lacks `haystack`; an unmarked `.claude/skills/haystack/` with a `SKILL.md` and an extra file; the new source ships `haystack`. The refresh is refused before any write. With no `bootstrap-root` record, the same folder is still overwritten as before (Decision 9), and the test pins that.
    - R15: with no record, the refusal does not contain "never shipped", says no record lists the folder, and names both remedies (remove an unmodified old bootstrap copy, or mark the project's own).
    - R18: a subfolder the walk cannot read skips the whole folder with a warning naming the folder (make it deterministic by patching the walk to raise `PermissionError`); `__pycache__/` and `*.pyc` are not mirrored; the "mirror project skill" line is printed only for folders actually mirrored.
    - R20: under a symlinked `.claude`, the refusal happens and `_declared_skill_name` is never called (patch it with a spy).
    - R22: edit a marked skill's `SKILL.md` and delete one of its reference files, refresh, and assert that the mirror and its `bootstrap-root` copy equal the edited folder exactly. Make the existing lost-marker run assert its specific message, not only the folder name.
    - R19, in `tests/test_validate_targets.py`: a `.project-skill` file in a fixture copy of `shared/skills/<name>/` fails validation; the real tree passes.
  - `stale_agents` (R17): a target whose `bootstrap-root` record lists 37 skills while the live `.agents/skills/` also holds retired folders that neither the record nor `.claude/skills/` has. The explanation lists only live `.agents/skills/<name>/` folders, never `.claude/bootstrap-root/...` paths, and says the record no longer lists them. After deleting the listed folders, the refresh succeeds and the live `.agents/` equals the record. A conflict of any other shape keeps today's generic message.
  - R14's assumption, in `tests/test_validate_targets.py` (name contains `project_skill`): the validator fails when a generated tree's `.claude/skills/` and `.agents/skills/` hold different skill names.
  - Record each new test's first failing run in the session log. Mutate each fix away once and confirm its test fails, then restore it byte-identical.

- [ ] **2. Never write through a link (R13).**
  - Owner: `coder`. Files (modify): `scripts/install_bootstrap.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Add a preflight in `main()`. It runs after `commit_copilot_surface` is computed, because the skip rules need it, and before `migrate_pre_existing_state`, the first write. It refuses when a write path, or any directory between the target root and it, is a symlink. The write paths are the ones in the risk notes:
    - each file and directory the copy step writes, minus the paths it skips; use the same predicates as `copy_generated_tree` (factor them out if needed) so the two cannot disagree;
    - the substitution files;
    - `.gitignore`;
    - `.claude/bootstrap-root` and each path `populate_bootstrap_root` writes or removes under it, plus `.claude/bootstrap-ownership.env`;
    - `.devcontainer/devcontainer.json` when `--state-remote` is given.
  - Collect every problem and refuse once, listing them all. The message starts with `Refusing to write through symlinks:` and gives the remedy: replace each link with a regular file or folder, or remove it, then rerun.
  - The README refresh skips, with a warning, a state-folder README whose folder or file is a link. `chmod_runtime_scripts` skips links.
  - No separate copy-time guard: the preflight is complete, and a refusal halfway through `copytree` would leave a partial write.
  - Unchanged: the removal loop (unlinking a link removes the link itself), the `.agents` takeover rules, and sidecar mode.

- [ ] **3. Tighten the project-skill preflight and the mirror (R14, R15, R18, R19, R20).**
  - Owner: `coder`. Files (modify): `scripts/install_bootstrap.py`, `scripts/runtime_ownership.py` (comment only), `scripts/validate_targets.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - R14 (Decision 9): when the record is the `bootstrap-root` copy and is a real directory, refuse an unmarked folder holding `SKILL.md` whose name that record lacks, even when the new source ships the name. The message says the refresh would overwrite it, and to rename and mark it, or remove it. With only the live `.agents/skills/` fallback or no record, keep today's behavior for shipped names.
  - R15 (Decision 11): reword the no-record and never-listed refusal so it says what is known. The new source does not ship the folder, and no shipped-before record lists it (name the record path, or say none was found). Then: remove it if it is an unmodified copy of an old bootstrap skill, or add the marker if the project wrote it.
  - R20: return the "marked but not protected" problem before reading `SKILL.md` through the unprotected path.
  - R18: `_mirrorable_files` passes an `onerror` handler to `os.walk`, and any walk error skips the whole folder with a warning that names the error. It leaves out `__pycache__/` and `*.pyc`, the generator's exclusions. Reuse an importable constant if one exists; otherwise define the two names once. Print "mirror project skill" only after the destination check passes.
  - R19: `validate_targets.py` fails when any `.project-skill` file exists under `shared/skills/` or under a generated skill folder in `dist/`.
  - R14's assumption: `validate_targets.py` fails when a generated tree's `.claude/skills/` and `.agents/skills/` hold different skill names.
  - R17 (Decision 10): in `validate_agents_takeover`, take the paths that exist only in the live tree. When every conflict is such a path inside `.agents/skills/<name>/`, and `<name>` is in neither the record nor `.claude/skills/`, append an explanation. It lists those live `.agents/skills/<name>/` folders and says the shipped-before record no longer lists them: another clone refreshed and this clone's restore copies files but never deletes them. If you did not create them, delete the listed folders and rerun. Any other conflict keeps today's message.
  - `scripts/runtime_ownership.py:94-96`: replace the false RAG incident with the real risk. The learn skill told consumers to save skills under `.claude/skills/`, and a refresh deletes every `.claude/` file it does not generate. RAG's two lost folders were retired bootstrap skills.

- [ ] **4. Correct the skill-authoring guidance and the installer docs (R16, R17, R21).**
  - Owner: `documenter`. Files (modify): `shared/skills/learn/SKILL.md`, `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md`, `shared/templates/skill-template.md`, `shared/skills/deep-audit/SKILL.md`, `README.md`, `docs/runtime-checks.md`, `docs/target-mapping.md`, `docs/architecture.md` (only if it lists the refusals). Required Skills: `.claude/skills/documentation/SKILL.md`.
  - `learn` (R16):
    - In Phase 2, rewrite the outcome rows (the old "Same trigger & fix → update existing skill" row must not survive, even with a qualifier) so they separate the cases. In this bootstrap's authoring repository, update `shared/skills/<name>`. In a consumer, update an existing skill only when it holds `.project-skill`. Never edit a shipped skill there: a refresh overwrites it, and marking it is a name clash. Instead, create a new marked project skill with its own name, or write a MEMORY entry.
    - Say plainly that every project skill needs the marker from the moment it is created. With no shipped-before record, an unmarked folder whose name the bootstrap later ships is overwritten (big plan Decision 9).
    - Replace the refusal promise with the real rules. An unmarked folder is refused only when the bootstrap neither ships its name nor shipped it before, and it is refused, not overwritten, when its name is newly shipped. Retired bootstrap names are deleted.
    - State the cap: `description` plus `when_to_use` at most 300 characters, trigger words first. The validator enforces it in the authoring repository; keep to it in consumers too.
    - Copilot also reads `.claude/skills/`, so it can find a new project skill without a refresh. Once a mirror copy exists, it lists that copy, so edits show after the next refresh.
  - `skill-template.md` and `deep-audit`: name the 300-character cap among the validator's hard checks.
  - `safe-consumer-bootstrap-refresh`:
    - No-record procedure: run the installer with `--dry-run`. For each listed folder, check whether every file is an unmodified bootstrap copy (each file's `git hash-object` appears in `git rev-list --all --objects` of a bootstrap checkout). Remove unmodified copies; mark the project's own.
    - A table mapping the 20 skills this plan removed to where their content went: the merged skill reference, the bentoml section, the tests-policy rule, or removed. Use bare names, never `skills/<name>/` paths. Add a note to update consumer MEMORY entries that name them.
    - The second-clone recovery from Step 3.
    - The symlink refusal from Step 2.
  - `README.md`:
    - line 968's "only refusal" sentence;
    - the full refusal list, including the symlink and newly-shipped-name refusals;
    - line 952's Copilot wording;
    - "never create or edit `.agents/skills/<name>/` by hand", with the one exception: deleting folders a refused refresh lists as stale.
  - `docs/runtime-checks.md:35-36, 53-56`: name the project-skill exception and the refusals, and replace "promote it into `shared/skills/`" with "mark it with `.project-skill`" for consumers. `docs/target-mapping.md:72`: the Copilot wording.

- [ ] **5. Regenerate and refresh this repository.**
  - Owner: orchestrator. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`. This repository's own refresh must pass the new preflight.

- [ ] **6. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`. State the acceptance bar from the Scope in the first-round prompt.
  - Focus:
    - no path the copy writes can be reached through a link;
    - every new refusal happens before any write;
    - no Phase A refusal got looser;
    - messages say only what the code knows;
    - the docs and skills match the code;
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
uv run pytest tests/test_install_bootstrap.py tests/test_validate_targets.py -q --tb=short -k "project_skill or destination_link or stale_agents"
uv run pytest tests/test_install_bootstrap.py tests/test_check_runtime.py tests/test_verify.py tests/test_sidecar_install.py tests/test_sidecar_update.py -q --tb=short
cmp scripts/runtime_ownership.py dist/multi-agent/.claude/scripts/runtime_ownership.py
test "$(grep -c -F 'lost its own' scripts/runtime_ownership.py)" = "0"
test "$(grep -c -F 'is an unmarked skill the bootstrap never shipped' scripts/install_bootstrap.py)" = "0"
test "$(grep -c -F 'Its only refusal about existing content' README.md)" = "0"
test "$(grep -c -F 'Same trigger & fix → update existing skill' shared/skills/learn/SKILL.md)" = "0"
grep -q -F 'Refusing to write through symlinks:' scripts/install_bootstrap.py
grep -q -F '300 characters' dist/multi-agent/.claude/skills/learn/SKILL.md
grep -q -F 'git hash-object' dist/multi-agent/.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md
grep -q -F 'pyvis-xss-testing' dist/multi-agent/.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md
test -f .claude/skills/openwiki/.openwiki-install.json
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

<!-- The only place a check may be conditional or non-executable. One `- `
     bullet per item, numbered in the order it appears. -->

- In a fresh `mktemp -d` Git repository outside the checkout, install from `dist/multi-agent` with `--local-only`, replace a shipped `SKILL.md` with a symlink to an outside sentinel file, and refresh. Expected: a refusal naming the path, and the sentinel unchanged.
- Real-consumer shapes, on scratch copies only, never the real repositories. For RAG, industrial-inspection, and img-classification: `git clone` each into a fresh `mktemp -d` folder and copy in its git-ignored `.claude/` and `.agents/` (when present). Then run a real `--local-only` refresh from `dist/multi-agent`.
  - RAG and industrial-inspection (both have a shipped-before record): exit 0 and no refusal, which shows R13 and R14 do not refuse real consumers.
  - img-classification (no record): the 22 old bootstrap folders are listed with the new wording, without "never shipped".
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
