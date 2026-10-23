---
name: 2026-10-23_phase-C-restorer-and-devcontainer-hardening
type: small-plan
parent_plan: state-sync-safety-fixes
phase_index: 3
status: planned
closeout_session_log:
---

# Small Plan: Restorer Symlink Checks and Devcontainer Mount Folders

## Scope

Two small hardening fixes. Requirements: REQ-010 and REQ-011.

First, `restore-root-adapters.sh` copies root adapter files out of `.claude/bootstrap-root/` to the repository root. It resolves `.claude/bootstrap-root` through symlinks before its containment checks, and those checks compare against the resolved folder. A symlinked `.claude` or `.claude/bootstrap-root` would therefore let it copy files from outside the repository. Severity is low: the synced `ai-state` repository already carries `settings.json` and `hooks/**`, which run code, and the installer already treats a tracked `.claude` symlink as foreign team configuration (`scripts/install_bootstrap.py::_claude_dir_tracked`). This is defense in depth.

Second, the devcontainer bind-mounts `~/.openwiki` and `~/.cache/huggingface` from the host, and Docker's `--mount` refuses a source folder that does not exist (Docker bind-mount documentation). An `initializeCommand` creates both folders on the host, as the host user, before the container starts. The containers.dev JSON reference documents what this relies on: `initializeCommand` runs on the host and may run more than once; its list form runs the program directly, with no shell; and `${localEnv:VAR}` works in any property, with an unset variable left empty.

## Steps

- [ ] **1. Refuse symlinked roots in the restorer.**
  - Owner: `coder`. File: `shared/hooks/scripts/restore-root-adapters.sh`.
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Keep the early `exit 0` at lines 33-35, so a repository with nothing to restore still exits quietly. That includes one whose `.claude` is a symlink with no restore content.
  - Right after `fail()` is defined, set `CLAUDE_ROOT="$REPO_ROOT/.claude"` and refuse a symlink at either level: `fail ".claude is a symlink; root adapters were not restored"` and `fail ".claude/bootstrap-root is a symlink; root adapters were not restored"`.
  - After `REPO_ROOT` is resolved (line 88), resolve `CLAUDE_ROOT` with `canonical_path` and require it inside `REPO_ROOT` (`fail ".claude resolves outside the repository root"`). After `SOURCE_ROOT` is resolved, require it inside `CLAUDE_ROOT` (`fail "bootstrap root resolves outside .claude"`). A comment says these two checks are defense in depth: after the symlink checks pass, they can only fail if the tree changes during the run.
  - Do not edit the line `for relative in "${paths[@]}"; do`: `scripts/check_runtime.py` (line 473) allowlists it by exact text. Add no unguarded array expansion.
  - `state-sync.sh` already turns a restorer failure into the logged warning `restoring root adapters failed; continuing.`; it needs no change.

- [ ] **2. Create the bind-mount folders before the container starts.**
  - Owner: `coder`. Files: `shared/devcontainer/devcontainer.json`, `scripts/validate_targets.py`, `tests/test_validate_targets.py`.
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - Add, just before `"mounts"`: `"initializeCommand": ["mkdir", "-p", "${localEnv:HOME}/.openwiki", "${localEnv:HOME}/.cache/huggingface"]`. The list form runs `mkdir` with no shell, so a home path with spaces or shell characters stays one argument.
  - Add `devcontainer_bind_source_errors(data: dict[str, Any]) -> list[str]` to `scripts/validate_targets.py` and call it from `validate_devcontainer_and_installer`. It requires `initializeCommand` to be a list that starts with `"mkdir", "-p"` and contains the `source=` value of every `type=bind` entry in `mounts`.
  - `scripts/install_bootstrap.py::update_devcontainer_state_remote` (lines 1005-1025) rewrites the file through `json.loads` and `json.dumps`, which keeps unknown keys, so it needs no change.
  - Tests: the shared `devcontainer.json` returns `[]`; with the Hugging Face path dropped from `initializeCommand`, one error names `${localEnv:HOME}/.cache/huggingface`; the string form returns one error; a missing `initializeCommand` returns one error.

- [ ] **3. Restorer regression tests.**
  - Owner: `coder`. File: `tests/test_state_sync.py`.
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - New tests:
    1. `test_restore_root_adapters_rejects_symlinked_claude_dir`. The repository's `.claude` is a symlink to an outside folder that holds a manifest for `CLAUDE.md` and `bootstrap-root/CLAUDE.md`. Run the rendered restorer from the devcontainer location (MEMORY: cover the devcontainer entry point). Expect exit 1, `.claude is a symlink` on stderr, and no `CLAUDE.md` at the repository root.
    2. `test_restore_root_adapters_rejects_symlinked_bootstrap_root`. A real `.claude` with a manifest, whose `bootstrap-root` is a symlink to an outside folder that holds `CLAUDE.md`. Run it through `_restore`. Expect exit 1, `.claude/bootstrap-root is a symlink` on stderr, and no root `CLAUDE.md`.
    3. `test_restore_root_adapters_ignores_symlinked_claude_without_content`. `.claude` is a symlink to an empty outside folder. Expect exit 0 and no new file at the root.
  - Both rejection tests fail against today's script, which copies the outside file.
  - `test_restore_root_adapters_rejects_allowed_source_symlink_escape` and the other restorer tests pass unchanged.

- [ ] **4. Update documentation.**
  - Owner: `documenter` (CLOSEOUT step 1). Files: `README.md`, `docs/runtime-checks.md`, `docs/smoke-tests.md`.
  - Required Skills: `.claude/skills/documentation/SKILL.md`.
  - `README.md` line 1151: drop the request to create `~/.openwiki` by hand; the devcontainer's `initializeCommand` now creates both mount folders as the host user.
  - `docs/runtime-checks.md`, the post-start paragraph near line 848: the restorer refuses a symlinked `.claude` or `.claude/bootstrap-root`.
  - `docs/smoke-tests.md`, the devcontainer bullets (line 92 and nearby): the generated `devcontainer.json` creates its bind-mount folders before the container starts.

- [ ] **5. Orchestrator closeout items.**
  - Owner: orchestrator.
  - Before CLOSEOUT step 2, run `uv run python scripts/generate_targets.py --all` and then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`.

- [ ] **6. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `config`, `documentation`. `config` is added because `devcontainer.json` changes (routing table in `.claude/instructions/workspace.instructions.md`).
  - Focus: the restorer still exits 0 with nothing to restore; no new code path follows a symlinked root; the devcontainer change runs no shell.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_state_sync.py tests/test_validate_targets.py tests/test_check_runtime.py -q --tb=short
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- On a host without `~/.openwiki` and `~/.cache/huggingface`, rebuild the devcontainer and record that both folders appear, owned by the host user, and that the container starts.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
