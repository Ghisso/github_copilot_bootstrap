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

A full-install refresh deletes every file under `.claude/` that the bootstrap does not generate, except consumer state and marker-claimed third-party bundles. Skills a project writes itself fall in that set. That is how RAG lost its own `retrieval-routing` and `iterative-plan-review` skills on 2026-08-09.

This phase lets a project keep its own skills. A real folder `.claude/skills/<name>/` that holds a regular file named `.project-skill` belongs to the project:
- a refresh never deletes or overwrites it;
- a refresh copies it, without the marker, to `.agents/skills/<name>/`, the folder Codex, Antigravity, and Copilot read;
- before any write, a full install or refresh refuses:
  - a project skill whose name clashes with a shipped skill;
  - a third-party destination;
  - an invalid or mismatched name;
  - any symlink at the skill-folder level;
  - an unmarked skill folder the bootstrap never shipped (big plan Decision 2).

The learn skill then points new project skills there. Covers REQ-001. The client table, the trade-offs, and the choice of the shipped-before record are in the big plan's Design Overview.

These promises cover the full install. In a sidecar repository, team skills are already never touched, and nothing mirrors them. The phase owns the files its steps list; a file may be revisited after a failing-first test or a review finding.

Risk notes:
- An unmarked folder whose name the bootstrap shipped before is a retired skill and is still deleted.
- A consumer with no shipped-before record gets refusals until the operator marks or removes each folder.
- Codex, Antigravity, and Copilot see a project skill as it was at the last refresh.
- Antigravity discovery is documented, not observed.
- This phase relies on Codex reading `.agents/skills/`. A native run observed that, and spike S4 checks it again before the branch.

<!-- Cite the big plan's requirement IDs where present; do not copy the requirements. -->

## Steps

- [ ] **1. Write the failing tests first.**
  - Owner: `coder`. Files (modify): `tests/test_install_bootstrap.py`, `tests/test_sidecar_install.py`, `tests/test_sidecar_update.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - Every new test name contains `project_skill`.
  - Every refusal case checks four things:
    - the exit is non-zero;
    - the message names the folder;
    - every file's bytes and every symlink's target in the target tree are unchanged;
    - an external sentinel file outside the target keeps its bytes and its path.
  - `copy_generated_tree` case, modeled on `test_refresh_preserves_third_party_openwiki_skill_bundle` (line 1409): a marked `.claude/skills/demo/` keeps its bytes across two refreshes whose source lacks `demo`.
  - `validate_project_skills` refusal cases:
    - a marker planted in a shipped skill folder;
    - a marked folder whose frontmatter `name:` differs from its folder name;
    - a marked folder whose name is not lowercase kebab case;
    - a marked folder named `openwiki` while `.agents/skills/openwiki` holds the OpenWiki marker;
    - a symlink as an entry under `.claude/skills/`;
    - a symlinked `.project-skill`;
    - a symlinked `SKILL.md` in a marked folder;
    - an unmarked folder with a `SKILL.md` whose name is neither in the source nor in `.claude/bootstrap-root/.agents/skills/`.
  - `validate_project_skills` pass cases:
    - an unmarked folder whose name is in `.claude/bootstrap-root/.agents/skills/` (a retired skill);
    - the same name recorded only in the live `.agents/skills/`, with no `bootstrap-root` copy;
    - an unmarked folder with no `SKILL.md`.
  - `mirror_project_skills` cases:
    - the mirror equals the folder minus `.project-skill`;
    - a valid marked folder that holds a symlink deeper inside is skipped whole, a warning names it, nothing is written under `.agents/skills/<name>/`, and the sentinel is unchanged.
  - Real-run cases. Run `INSTALLER` with `subprocess`, `--local-only`, and `_actor_env()`, like `test_fresh_install_gitignore_excludes_provenance_secret` (line 1475). Split across two tests if one runs long.
    - Run 1: a target whose `.claude/` already holds a marked `demo` before the first full install (the legacy path in `migrate_pre_existing_state`). Exit 0. `demo` keeps its bytes. `.agents/skills/demo/SKILL.md` and `.claude/bootstrap-root/.agents/skills/demo/SKILL.md` match, with no marker. `bootstrap_root_fingerprint_diagnostics(target)` from `shared/scripts/verify.py` returns no diagnostics.
    - Then add an unmarked `stray` holding a `SKILL.md`.
    - Run 2: refused; the message names `stray`.
    - Then remove `stray`.
    - Run 3: with a copy of `GENERATED` in `tmp_path` that drops one shipped skill. Exit 0. That skill's folder is removed from `.claude/skills/` and `.agents/skills/`, with no refusal.
    - Run 4: with a copy of `GENERATED` that adds a skill named `demo`. Refused while the marked `demo` remains.
    - Then delete the project `demo`.
    - Run 5: with the normal source. `.agents/skills/demo/` is gone.
    - Run 6: with the source that adds `demo`. Exit 0. `.agents/skills/demo/` and its `bootstrap-root` copy hold the bootstrap version.
  - Sidecar cases. Sidecar code stays unchanged; the marker must change nothing:
    - a team repository whose `.claude/skills/team-skill/` holds `.project-skill` keeps it byte-identical through the initial sidecar install and a refresh;
    - a recorded sidecar skill that was locally modified and given a marker gets the same outcome as the existing modified-skill case without the marker.
  - Acceptance: the new installer tests fail before Step 2. The sidecar cases pin existing behavior and pass before and after. Record both in the session log.

- [ ] **2. Add the project-skill ownership rule and its safety checks.**
  - Owner: `coder`. Files (modify): `scripts/runtime_ownership.py`, `scripts/install_bootstrap.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - `runtime_ownership.py`:
    - `PROJECT_SKILL_MARKER = ".project-skill"`;
    - `def is_project_skill_dir(dir_path: Path) -> bool`. It is true only when all of these hold:
      - `dir_path` is a real directory (`lstat`, not a symlink);
      - its parent is a real `skills` directory directly under a real `.claude` directory;
      - `dir_path / PROJECT_SKILL_MARKER` is a regular file by `lstat` (`stat.S_ISREG`, no link followed).
    - It reads no file content. A comment gives the reason: the RAG loss, and that no client reads another folder.
  - `install_bootstrap.py`, `owned_files()`: prune a project skill directory in the `.claude` walk, next to the `_third_party_skill_owner` pruning (about line 584).
  - `install_bootstrap.py`, `def validate_project_skills(source: Path, target: Path) -> None`. Call it in `main()` directly after `validate_agents_takeover(source, target)`, before any write.
    - It checks every path with `lstat` before reading anything. It reads a `SKILL.md` frontmatter `name:` (with `sidecar_overlay._parse_frontmatter_name`) only from a regular file inside a real folder.
    - It collects every problem, then raises one `SystemExit` listing them all.
    - It refuses:
      1. a symlink as `.claude/skills/` or as any entry directly under it;
      2. a marked folder:
         - whose marker or `SKILL.md` is a symlink or not a regular file;
         - whose name does not match `[a-z0-9]+(-[a-z0-9]+)*`;
         - whose `name:` differs from the folder name;
         - whose name is a folder in `source/.claude/skills/`;
         - whose name is a third-party shape in `THIRD_PARTY_SKILL_PATHS`, or names a marker-claimed directory at `target/.agents/skills/<name>`;
         - that also holds the OpenWiki marker;
      3. an unmarked, non-third-party folder that holds an entry named `SKILL.md`, whose name is neither in `source/.claude/skills/` nor in the shipped-before record. The record is `target/.claude/bootstrap-root/.agents/skills/`, or the live `target/.agents/skills/` only when that copy is absent; read it as directory entries with no link followed. The message says: add `.claude/skills/<name>/.project-skill` to keep it, or remove the folder, then rerun.
    - Folders with no `SKILL.md` entry are ignored.
    - Folder names, never frontmatter values, are used for every comparison and destination. The name rule plus "`name:` equals the folder name" rules out duplicate names and case variants without a separate pass.
  - `install_bootstrap.py`, `def mirror_project_skills(target: Path, dry_run: bool) -> None`. Call it in `main()` after `substitute_python_version` and before `populate_bootstrap_root`.
    - For each marked folder, first walk it with `os.walk(followlinks=False)` and check every entry with `lstat`.
    - A folder holding any symlink or non-regular entry is skipped whole with `warn(...)`.
    - Otherwise, check that `.agents/` and `.agents/skills/` are real directories and that `.agents/skills/<name>` is free after pruning, then copy every regular file except the marker.
  - Must not change:
    - `CONSUMER_STATE_PATHS` or the OpenWiki marker logic;
    - `shared/scripts/verify.py`, `scripts/check_runtime.py`, or `scripts/sidecar_overlay.py`.
  - Record in the session log why no other importer of `runtime_ownership` needs the rule. The importers are `scripts/install_bootstrap.py`, `scripts/generate_targets.py` (line 16; it copies the module into `dist`), `scripts/check_runtime.py`, `scripts/validate_targets.py`, `scripts/sidecar_overlay.py`, `shared/scripts/verify.py`, and the tests. The reasons:
    - `verify.py`'s root-adapter comparison sees only the unmarked mirror, which `populate_bootstrap_root` records; its nested-runtime fingerprint binds the project skill under `.claude/`;
    - `check_runtime.py` covers this authoring repository, which keeps its skills in `shared/skills/`;
    - the generator only copies the module.
  - Acceptance: the Step 1 tests and all of `tests/test_install_bootstrap.py` pass.

- [ ] **3. Point agents and operators at the marker.**
  - Owner: `documenter`, with `coder` for the validator lines. Files (modify):
    - `shared/skills/learn/SKILL.md`;
    - `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md`;
    - `scripts/validate_targets.py` (`stale_skill_contract_errors`);
    - `README.md`, `docs/architecture.md`, `docs/target-mapping.md`.
  - Required Skills: `.claude/skills/documentation/SKILL.md`, `.claude/skills/humanize/SKILL.md` (`edit` mode), and `.claude/skills/ponytail/SKILL.md` (`full` mode) for the validator lines.
  - learn, Phase 3, consumer branch. Create `.claude/skills/<name>/SKILL.md` with a lowercase kebab-case name equal to `name:`, plus an empty `.claude/skills/<name>/.project-skill`, and say:
    - without the marker, the next refresh refuses to run until the folder is marked or removed;
    - use a name no bootstrap or third-party skill uses;
    - no symlinks in the folder;
    - Codex, Antigravity, and Copilot see it through `.agents/skills/<name>/` after the next refresh;
    - never create or edit `.agents/skills/<name>/` by hand;
    - create or edit the skill no later than CLOSEOUT step 2, because the receipts bind `.claude/` runtime files.
    - The Output section also reports the marker.
  - safe-consumer-bootstrap-refresh, before refreshing:
    - list the folders under `.claude/skills/` that hold a `SKILL.md`, that the new `dist/multi-agent/.claude/skills/` does not ship, that are not listed in the consumer's `.claude/bootstrap-root/.agents/skills/`, and that have no `.project-skill`;
    - mark or move each one first;
    - a name listed in that record was shipped by the bootstrap and is retired on purpose, so do not mark it;
    - the installer refuses the same set.
  - Validator: add `"learn": ("`.project-skill`", "`.agents/skills/`")` to `required`, with an empty `forbidden` entry.
  - README:
    - in "What a full install changes" (near line 964), add the marker exception and the refusals;
    - in "Updating Full Consumers" (near line 254), add the listing step;
    - add a short "Project-owned skills" paragraph with the client table and the full-install scope from the big plan.
  - `docs/architecture.md` ownership section: the rule beside the OpenWiki marker. `docs/target-mapping.md`: the `.agents/skills/` mirror.
  - Acceptance: the validator passes. README states the refusal, the refresh delay, and the hand-edit rule.

- [ ] **4. Regenerate and refresh this repository.**
  - Owner: orchestrator. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`. Never hand-copy `dist/`.
  - Acceptance:
    - the self-refresh passes the new checks (this repository's `.claude/skills/` holds only shipped skills and the third-party `openwiki`);
    - `.claude/skills/openwiki/` keeps its `.openwiki-install.json`;
    - the generated `runtime_ownership.py` is byte-identical to the source.

- [ ] **5. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.
  - Focus:
    - no path deletes or overwrites a marked folder;
    - every refusal runs before any write and reads nothing through a link;
    - the mirror never follows a link and writes only under `.agents/skills/<name>/`;
    - the shipped-before record is read safely;
    - the call order keeps `validate_agents_takeover` and the root fingerprint consistent (the real-run tests);
    - retired skills are still deleted;
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
uv run pytest tests/test_install_bootstrap.py tests/test_sidecar_install.py tests/test_sidecar_update.py -q --tb=short -k project_skill
uv run pytest tests/test_install_bootstrap.py tests/test_check_runtime.py tests/test_verify.py tests/test_sidecar_install.py tests/test_sidecar_update.py -q --tb=short
cmp scripts/runtime_ownership.py dist/multi-agent/.claude/scripts/runtime_ownership.py
grep -q -F '.project-skill' dist/multi-agent/.claude/skills/learn/SKILL.md
grep -q -F '.project-skill' dist/multi-agent/.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md
grep -q -F 'bootstrap-root/.agents/skills' dist/multi-agent/.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md
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

- In a fresh `mktemp -d` Git repository outside the checkout, install from `dist/multi-agent` with `--local-only`, add a marked `.claude/skills/demo/`, and install again. Then run `codex debug prompt-input` there with the spike's isolated `HOME` and `CODEX_HOME`. Expected: `.agents/skills/demo/SKILL.md` is listed once.

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
