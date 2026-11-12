---
name: 2026-11-12_phase-A-project-owned-skills
type: small-plan
parent_plan: skills-and-instructions-trim
phase_index: 1
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: planned
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

# Small Plan: 2026-11-12_phase-A-project-owned-skills

## Scope

A full-install refresh deletes every file under `.claude/` that the bootstrap does not generate. That is how RAG lost its own `retrieval-routing` and `iterative-plan-review` skills on 2026-08-09.

This phase lets a project keep its own skills. A skill folder `.claude/skills/<name>/` that holds a file named `.project-skill` belongs to the project:
- a refresh never deletes or overwrites it;
- a refresh refuses to start when the folder name or its frontmatter `name:` equals a bootstrap skill;
- a refresh copies the folder, without the marker, to `.agents/skills/<name>/`, the only folder Codex and Antigravity read.

The learn skill then points new project skills there. Covers REQ-001. The per-client discovery table is in the big plan's Design Overview.

Risk notes:
- The marker is opt-in, so an unmarked folder is still deleted, as today.
- Codex and Antigravity see a project skill as it was at the last refresh.
- Antigravity discovery is documented, not observed.
- This phase relies on Codex reading `.agents/skills/`. A native run observed that, and spike S4 checks it again before the branch.

<!-- Cite the big plan's requirement IDs where present; do not copy the requirements. -->

## Steps

- [ ] **1. Write the failing tests first.**
  - Owner: `coder`. File (modify): `tests/test_install_bootstrap.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - Every new test name contains `project_skill`.
  - `copy_generated_tree` cases, modeled on `test_refresh_preserves_third_party_openwiki_skill_bundle` (line 1409):
    - a marked `.claude/skills/demo/` keeps its bytes across two refreshes whose source lacks `demo`;
    - an unmarked `.claude/skills/stray/` is still removed (pins the documented trade-off).
  - `validate_project_skills` cases:
    - a marked folder named like a source skill raises `SystemExit`, and the message names it;
    - a marked folder whose `SKILL.md` frontmatter `name:` equals a source skill raises `SystemExit`;
    - after a refusal, the target tree is byte-identical to before.
  - `mirror_project_skills` cases:
    - the mirror equals the folder minus `.project-skill`;
    - a folder holding a symlink is not mirrored, and a warning names it.
  - Real-run case. Run `INSTALLER` with `subprocess`, `--source GENERATED --local-only`, and `_actor_env()`, like `test_fresh_install_gitignore_excludes_provenance_secret` (line 1475). Use one fresh `tmp_path` Git repository:
    - Run 1: a fresh install.
    - Then add a marked `demo` and an unmarked `stray`.
    - Run 2: exit code 0. `demo` keeps its bytes. `.agents/skills/demo/SKILL.md` and `.claude/bootstrap-root/.agents/skills/demo/SKILL.md` hold the same bytes, with no marker. `stray` is gone. `bootstrap_root_fingerprint_diagnostics(target)` from `shared/scripts/verify.py` returns no diagnostics.
    - Then delete `demo`.
    - Run 3: `.agents/skills/demo/` is gone.
  - Acceptance: every new test fails before Step 2. Record the failure lines in the session log.

- [ ] **2. Add the project-skill ownership rule.**
  - Owner: `coder`. Files (modify): `scripts/runtime_ownership.py`, `scripts/install_bootstrap.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - `runtime_ownership.py`:
    - `PROJECT_SKILL_MARKER = ".project-skill"`;
    - `def is_project_skill_dir(dir_path: Path) -> bool`. It is true only for a directory directly under a `skills` folder whose parent is named `.claude`, and that holds `PROJECT_SKILL_MARKER` as a regular file (`Path.is_file()`);
    - a comment giving the reason (the RAG loss, and that no client reads another folder).
  - `install_bootstrap.py`:
    - `owned_files()`: prune a project skill directory in the `.claude` walk, next to the `_third_party_skill_owner` pruning (about line 584).
    - Add `def validate_project_skills(source: Path, target: Path) -> tuple[str, ...]`. It returns the marked names. It raises `SystemExit` for a name clash: the folder name, or the frontmatter `name:` read with `sidecar_overlay._parse_frontmatter_name`, equals a folder in `source/.claude/skills/`. The message says to rename the folder and its `name:` field, then rerun. Call it in `main()` directly after `validate_agents_takeover(source, target)`.
    - Add `def mirror_project_skills(target: Path, dry_run: bool) -> None`. It copies every regular file except the marker to `target/.agents/skills/<name>/`, never following a symlink. A folder holding any symlink or non-regular entry is skipped whole with `warn(...)`. Call it in `main()` after `substitute_python_version` and before `populate_bootstrap_root`.
  - Must not change:
    - `CONSUMER_STATE_PATHS` or the OpenWiki marker logic;
    - `shared/scripts/verify.py`, `scripts/check_runtime.py`, or `scripts/sidecar_overlay.py`.
  - Grep every importer of `runtime_ownership` and record in the session log why none other needs the rule. The importers are `scripts/install_bootstrap.py`, `scripts/check_runtime.py`, `scripts/validate_targets.py`, `scripts/sidecar_overlay.py`, `shared/scripts/verify.py`, `shared/skills/caveman-compress/scripts/detect.py`, and the tests. The reasons:
    - `verify.py` sees only the unmarked mirror, which `populate_bootstrap_root` records;
    - `check_runtime.py` covers this authoring repository, which keeps its skills in `shared/skills/`.
  - Acceptance: the Step 1 tests and all of `tests/test_install_bootstrap.py` pass.

- [ ] **3. Point agents and operators at the marker.**
  - Owner: `documenter`, with `coder` for the validator line. Files (modify):
    - `shared/skills/learn/SKILL.md`;
    - `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md`;
    - `scripts/validate_targets.py` (`stale_skill_contract_errors`);
    - `README.md`, `docs/architecture.md`, `docs/target-mapping.md`.
  - Required Skills: `.claude/skills/documentation/SKILL.md`, `.claude/skills/humanize/SKILL.md` (`edit` mode), and `.claude/skills/ponytail/SKILL.md` (`full` mode) for the validator line.
  - learn, Phase 3, consumer branch. Create `.claude/skills/<name>/SKILL.md` plus an empty `.claude/skills/<name>/.project-skill`, and say:
    - without the marker, the next refresh deletes the folder;
    - use a name no bootstrap skill uses, because the refresh refuses a clash;
    - Codex and Antigravity get the skill at the next refresh;
    - create or edit it no later than CLOSEOUT step 2, because the receipts bind `.claude/` runtime files.
    - The Output section also reports the marker.
  - safe-consumer-bootstrap-refresh: before refreshing, list skill folders that the new `dist/multi-agent/.claude/skills/` does not ship (for example with `comm -23`) and that have no `.project-skill`. Mark or move each one first.
  - Validator: add `"learn": ("`.project-skill`",)` to `required`, with an empty `forbidden` entry.
  - README:
    - add the marker exception to "Updating Full Consumers" (near line 254) and to "What a full install changes" (near line 964);
    - add a short "Project-owned skills" paragraph with the client table from the big plan.
  - `docs/architecture.md` ownership section: the rule beside the OpenWiki marker. `docs/target-mapping.md`: the `.agents/skills/` mirror.
  - Acceptance: the validator passes, and README states the opt-in trade-off and the refresh delay for Codex.

- [ ] **4. Regenerate and refresh this repository.**
  - Owner: orchestrator. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`. Never hand-copy `dist/`.
  - Acceptance:
    - `.claude/skills/openwiki/` keeps its `.openwiki-install.json`;
    - the generated `runtime_ownership.py` is byte-identical to the source.

- [ ] **5. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.
  - Focus:
    - no path deletes or overwrites a marked folder;
    - the clash refusal runs before any write;
    - the mirror never follows a symlink and writes only under `.agents/skills/<name>/`;
    - the call order keeps `validate_agents_takeover` and the root fingerprint consistent (the real-run test);
    - unmarked behavior is unchanged;
    - the sidecar is untouched.

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
uv run pytest tests/test_install_bootstrap.py -q --tb=short -k project_skill
uv run pytest tests/test_install_bootstrap.py tests/test_check_runtime.py tests/test_verify.py tests/test_sidecar_install.py tests/test_sidecar_update.py -q --tb=short
cmp scripts/runtime_ownership.py dist/multi-agent/.claude/scripts/runtime_ownership.py
grep -q -F '.project-skill' dist/multi-agent/.claude/skills/learn/SKILL.md
grep -q -F '.project-skill' dist/multi-agent/.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md
grep -q -F '.project-skill' README.md
test -f .claude/skills/openwiki/.openwiki-install.json
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

<!-- The only place a check may be conditional or non-executable. One `- `
     bullet per item, numbered in the order it appears. -->

- In a scratch Git repository under the scratchpad, install from `dist/multi-agent` with `--local-only`, add a marked `.claude/skills/demo/`, install again, and run `codex debug prompt-input` there. Expected: `.agents/skills/demo/SKILL.md` is listed once.

## Closeout Checklist

Run the numbered CLOSEOUT sequence in `.claude/instructions/workflow.instructions.md` (Canonical Orchestrator Loop, step 5) in order. Tick both boxes at its step 2. Later steps bind this file's bytes, so do not edit this file after step 2.

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
