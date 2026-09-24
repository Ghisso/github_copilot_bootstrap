---
name: 2026-09-24_phase-C-sidecar-install-and-provider-bridges
type: small-plan
parent_plan: consumer-sidecar-bootstrap-overlay
phase_index: 3
status: planned
closeout_session_log:
---

# Small Plan: Phase C — Sidecar Install and Provider Bridges

## Scope

Add `--mode`, mode detection, preflight, the exclude block and its ignore
gate, and the apply step that executes the Phase B plan. First install and
rerun use this one path. Mode detection lands here, not in Phase D, so no
commit on this branch can leave a sidecar consumer exposed to a full install.

This phase changes one existing test expectation.
`test_generated_session_pull_restores_ignored_adapter_after_branch_switch`
installs into an unbootstrapped repository that tracks `CLAUDE.md`, which the
new refusal blocks (big plan, Decision 18), so that test now passes
`--mode full`. The 2026-09-24 review scanned the rest of the suite and the
validator's self-tests: every other installer run either starts from an
empty repository or calls `copy_generated_tree` directly.

### Required Skills

- `shared/skills/ponytail/SKILL.md` — `full`
- `shared/skills/code-style/SKILL.md`
- `shared/skills/testing-patterns/SKILL.md`
- `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md`

## Primary Files

- `scripts/install_bootstrap.py` — CLI, mode detection, source choice, and dispatch only.
- `scripts/sidecar_overlay.py` — the apply step and reporting.
- `tests/test_sidecar_install.py` — new; uses real temporary Git repositories.
- `tests/test_install_bootstrap.py` — new full-mode refusal cases, plus
  `--mode full` in `test_generated_session_pull_restores_ignored_adapter_after_branch_switch`.

## Steps

- [ ] **1. Add the CLI mode.**
  - **Owner:** `coder`
  - Add `--mode {full,sidecar}`. Omitting it keeps today's default except
    for the new refusals in step 2.
  - Change `--source` to default to none, so the installer can tell an
    explicit source from the default. After mode detection, the default
    source is `dist/multi-agent/` for full mode and `dist/sidecar/` for
    sidecar mode. Tests pass `--source`.
  - Full-only options are ignored with one warning on a sidecar target, and
    `--local-only` is accepted as a no-op (big plan, Decision 13). In sidecar
    mode, `validate_install_roots` always receives `allow_self=False`.

- [ ] **2. Add mode detection.**
  - **Owner:** `coder`
  - One function in `install_bootstrap.py` implements the big plan's mode
    table. That includes the linked-worktree abort (Decision 15), the
    unbootstrapped team-config abort over `FULL_INSTALL_ROOT_PATHS`
    (Decision 18), and `--allow-self` with this repository as the target
    counting as full evidence. The function reads only the target.
  - `main()` order: parse arguments, detect the mode, choose the source, run
    `validate_install_roots`, then dispatch. Full mode then runs today's
    steps unchanged, starting with `validate_agents_takeover`. The sidecar
    path never calls a full-install step and does not print the Codex
    hook-trust notice.
  - The sidecar path refuses a source that is not a sidecar tree, meaning
    any source with a path outside the allowlisted skill folders, their
    `LICENSE` files, and the bridge paths.
  - Each refusal names the evidence found and the manual way forward. When
    `.devcontainer/state-sync.sh` is tracked (a fresh clone of a full
    consumer whose `.claude/` is not restored yet), the team-config refusal
    also says to run `bash .devcontainer/state-sync.sh setup` first, or to
    pass `--mode full`.

- [ ] **3. Run preflight.**
  - **Owner:** `coder`
  - Gather the planner inputs with Git, always with
    `--path-format=absolute`, because `--git-path` prints a relative path in
    the main worktree: `git rev-parse --show-toplevel`, `--git-dir`,
    `--git-common-dir`, `--git-path info/exclude`,
    `--git-path ai-bootstrap-sidecar.json`, and
    `--git-path ai-bootstrap-sidecar-staging`. Use `git ls-files` for tracked
    state, and `git check-ignore --stdin -z` for which untracked files are
    currently ignored.
  - Apply every preflight abort from the big plan before any write:
    Git older than 2.31, a Git directory on a different filesystem from the
    worktree, and a symlinked `info/exclude` included.

- [ ] **4. Write the exclude block and prove it.**
  - **Owner:** `coder`
  - Create `info/` when it is missing. Keep one marked block. It holds one
    anchored unit line with no trailing slash, for example
    `/.claude/skills/ponytail`, for every unit that is owned after this run,
    being written, or being removed. It also holds one escaped exact-path
    line for each untracked file of a team-taken unit that this run deletes
    or retains, and that unit loses its unit line in this same write (big
    plan, Decisions 16 and 17).
  - Preserve every byte outside the block. Write the file atomically: a
    temporary file in `info/`, then `os.replace`.
  - Run the ignore gate (Decision 17): pipe every path that must stay
    ignored to `git check-ignore --stdin -z` without `-v`, and pass only
    when the printed set equals that set, byte for byte. On failure, restore
    the previous exclude file, or remove the one this run created, then
    abort and print each path with the rule from `git check-ignore -v`.
  - The gate is one function that takes candidate exclude text, so dry-run
    can call it without writing `info/exclude`.

- [ ] **5. Apply the plan.**
  - **Owner:** `coder`
  - Empty the staging folder, then execute the Phase B actions: install,
    update, remove, adopt, drop, and team takeover cleanup. There are no
    intent records (big plan, Decision 10).
  - Build each new unit in the staging folder, move the old copy into
    staging, then move the new copy into place with `os.replace`. Remove a
    unit by moving it into staging. A bridge is a single file, so one
    `os.replace` from staging replaces it.
  - Then drop the exclude lines of removed units and deleted files, write the
    manifest last (a temporary file in the Git directory, then `os.replace`),
    and empty the staging folder.
  - Write the exclude file and the manifest only when their bytes change.

- [ ] **6. Report the result.**
  - **Owner:** `coder`
  - Print counts for installed, updated, removed, adopted, and unchanged
    units, then one `SKIPPED` or `RETAINED` line per path with its reason and
    remedy.
  - Exit 0 unless preflight aborted.

- [ ] **7. Implement dry-run.**
  - **Owner:** `coder`
  - Run preflight and planning, and call the same ignore-gate function on
    the candidate exclude text through a temporary `core.excludesFile`.
  - Print every action as "would ...". Write nothing in the worktree or the
    Git directory, including the staging folder.
  - Say in the output that the dry-run gate is an approximation: Git ranks
    `info/exclude` above `core.excludesFile`, so the real run's gate decides.

- [ ] **8. Add failing-first installer tests.**
  - **Owner:** `coder`
  - Required cases:

    ```text
    tracked team config for all four clients, --mode sidecar       -> byte-identical after install
    git status --porcelain --untracked-files=all                   -> identical before and after
    .gitignore, core.hooksPath, hook files                         -> unchanged
    .claude/.git, ai-bootstrap/                                    -> not created
    ponytail and ponytail-review at both roots                     -> LICENSE present, bytes equal the source
    skill name taken by a tracked team skill                       -> skipped at both roots, reported
    skill name taken only in .github/skills/                       -> skipped at both roots, reported
    team-tracked skill folder with no manifest record              -> skipped, no exclude line added
    foreign untracked skill directory                              -> skipped, bytes kept, still visible in git status
    visible untracked copy identical to the sidecar's              -> reported foreign, not adopted, still visible
    bridge path already occupied                                   -> bridge skipped, reported
    team .gitignore with !.claude/skills/**                        -> abort, exclude file restored, nothing written
    same repository with --dry-run                                 -> same abort and message, nothing written
    one planned path ignored and another not                       -> abort (the --stdin exit-0 trap)
    retained names with [ * ? \ , a leading ! or #, a trailing space, non-ASCII -> each hidden exactly, no other file hidden
    team .gitignore re-includes a retained file                    -> abort before any unit write, exclude file restored
    .agents/skills symlinked to ../.claude/skills                  -> abort
    linked worktree                                                -> abort
    Git directory on another filesystem (injected device IDs)      -> abort
    full evidence with --mode sidecar                              -> abort
    sidecar evidence with no --mode                                -> sidecar path, never a full install
    sidecar evidence with --mode full                              -> abort
    invalid manifest with no --mode                                -> abort with remedy
    unbootstrapped repo tracking CLAUDE.md, no --mode              -> abort offering --mode full or --mode sidecar
    unbootstrapped repo tracking only .devcontainer/, no --mode    -> same abort
    same repository with --mode full                               -> today's full-install behavior
    --allow-self with this repository's own path                   -> full evidence, never a refusal (detection unit test)
    --mode sidecar with --source dist/multi-agent                  -> abort before any write
    dry-run                                                        -> worktree, exclude file, manifest, and staging unchanged
    fault after a unit move, before the manifest write             -> rerun adopts that unit, nothing reported foreign
    fault after moving the old copy out, before moving the new in  -> rerun installs the unit
    manifest moved aside after a good install, then rerun          -> listed units adopted
    one file changed after a good install, then rerun              -> reported as locally modified, bytes kept
    team checkout tracks one file of a sidecar skill folder        -> matching files deleted, hidden user file retained, status unchanged
    fault after the takeover exclude write, before deleting files  -> matching files still hidden; rerun deletes them, retained file stays hidden
    rerun with no upstream change                                  -> no file changes, including exclude and manifest
    ```

  - Each fault case arms the fault at the named point and asserts the
    on-disk state before the rerun, so it proves that the rerun did the
    recovery.
  - Existing full-install tests pass. The only expectation change is
    `--mode full` in
    `test_generated_session_pull_restores_ignored_adapter_after_branch_switch`.

## Acceptance Criteria

A repository may already contain provider configuration for all four
clients. After a sidecar install:

- every pre-existing team file is byte-identical;
- `git status --porcelain --untracked-files=all` is unchanged;
- only sidecar-owned, ignored units exist, and the manifest records them;
- no hook, MCP, or configuration takeover occurs;
- a plain `install_bootstrap.py TARGET` on that repository never runs a full
  install;
- an interrupted install or update finishes on rerun, without intent records.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_sidecar_overlay.py tests/test_sidecar_install.py tests/test_install_bootstrap.py -q --tb=short
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- The operator installs the sidecar into the Phase A fixture and repeats one native client check per skill root.

## Review Profiles

- `code`
- `architecture`
- `security`
- `tests`
- `ponytail`

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT).

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
