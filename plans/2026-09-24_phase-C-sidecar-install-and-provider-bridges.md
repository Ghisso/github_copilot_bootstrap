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

### Required Skills

- `shared/skills/ponytail/SKILL.md` — `full`
- `shared/skills/code-style/SKILL.md`
- `shared/skills/testing-patterns/SKILL.md`
- `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md`

## Primary Files

- `scripts/install_bootstrap.py` — CLI, mode detection, and dispatch only.
- `scripts/sidecar_overlay.py` — the apply step and reporting.
- `tests/test_sidecar_install.py` — new; uses real temporary Git repositories.
- `tests/test_install_bootstrap.py` — new full-mode refusal cases only.

## Steps

- [ ] **1. Add the CLI mode.**
  - **Owner:** `coder`
  - Add `--mode {full,sidecar}`. Omitting it keeps today's default except
    for the new refusals in step 2.
  - In sidecar mode the default source is `dist/sidecar/`. `--source`
    overrides it, which tests use.
  - Full-only options are ignored with one warning on a sidecar target, and
    `--local-only` is accepted as a no-op (big plan, Decision 13).

- [ ] **2. Add mode detection.**
  - **Owner:** `coder`
  - One function in `install_bootstrap.py` implements the big plan's mode
    table, including the linked-worktree abort (Decision 15) and the
    unbootstrapped team-config abort (Decision 18). It runs in `main()`
    before `validate_agents_takeover` and before any side effect.
  - `validate_install_roots` still runs first in both modes. After that, the
    sidecar path never calls a full-install step.
  - Each refusal names the evidence found and the manual way forward. The
    team-config refusal also covers a fresh clone of a full consumer whose
    committed Copilot surface is tracked but whose `.claude/` is not restored
    yet; its message says to run `bash .devcontainer/state-sync.sh setup`
    first, or to pass `--mode full`.

- [ ] **3. Run preflight.**
  - **Owner:** `coder`
  - Gather the planner inputs with Git, always with
    `--path-format=absolute`, because `--git-path` prints a relative path in
    the main worktree: `git rev-parse --show-toplevel`, `--git-dir`,
    `--git-common-dir`, `--git-path info/exclude`,
    `--git-path ai-bootstrap-sidecar.json`, and `git ls-files` for tracked
    state.
  - Apply every preflight abort from the big plan before any write.

- [ ] **4. Write the exclude block and prove it.**
  - **Owner:** `coder`
  - Create `info/` when it is missing. Keep one marked block with one
    anchored line per owned or planned unit and no trailing slash, for
    example `/.claude/skills/ponytail`, plus one exact-path line per
    `retained` file.
  - Preserve every byte outside the block.
  - Run the ignore gate (Decision 17): pipe every planned file path to
    `git check-ignore --stdin` without `-v`, and pass only when the printed
    set equals the planned set. On failure, restore the previous exclude
    file, abort, and print each path with the rule from `git check-ignore -v`.
  - The gate is one function that takes candidate exclude text, so dry-run
    can call it without writing `info/exclude`.

- [ ] **5. Apply the plan.**
  - **Owner:** `coder`
  - Write the intent manifest with a `pending` record for every unit this
    run will write or remove. Then execute the Phase B actions: install,
    update, remove, adopt, drop, and team takeover cleanup.
  - Then trim the exclude block to the final owned and `retained` set, and
    write the final manifest without `pending` records.
  - Every manifest write goes to a temporary file in the Git directory,
    then `os.replace`. Write the exclude file and the manifest only when
    their bytes change.

- [ ] **6. Report the result.**
  - **Owner:** `coder`
  - Print counts for installed, updated, removed, adopted, finished, and
    unchanged units, then one `SKIPPED` or `RETAINED` line per path with its
    reason and remedy.
  - Exit 0 unless preflight aborted.

- [ ] **7. Implement dry-run.**
  - **Owner:** `coder`
  - Run preflight and planning, and call the same ignore-gate function on
    the candidate exclude text through a temporary `core.excludesFile`.
  - Print every action as "would ...". Write nothing in the worktree or the
    Git directory.

- [ ] **8. Add failing-first installer tests.**
  - **Owner:** `coder`
  - Required cases:

    ```text
    tracked team config for all four clients, --mode sidecar -> byte-identical after install
    git status --porcelain --untracked-files=all             -> identical before and after
    .gitignore, core.hooksPath, hook files                   -> unchanged
    .claude/.git, ai-bootstrap/                              -> not created
    skill name taken by a tracked team skill                 -> skipped at both roots, reported
    foreign untracked skill directory                        -> skipped, bytes kept
    bridge path already occupied                             -> bridge skipped, reported
    team .gitignore with !.claude/skills/**                  -> abort, exclude file restored, nothing written
    same repository with --dry-run                           -> same abort and message, nothing written
    one planned path ignored and another not                 -> abort (the --stdin exit-0 trap)
    .agents/skills symlinked to ../.claude/skills            -> abort
    linked worktree                                          -> abort
    full evidence with --mode sidecar                        -> abort
    sidecar evidence with no --mode                          -> sidecar path, never a full install
    sidecar evidence with --mode full                        -> abort
    invalid manifest with no --mode                          -> abort with remedy
    unbootstrapped repo tracking CLAUDE.md, no --mode        -> abort offering --mode full or --mode sidecar
    same repository with --mode full                         -> today's full-install behavior
    dry-run                                                  -> worktree, exclude file, and manifest unchanged
    fault injected after the intent manifest, first install  -> rerun finishes every pending unit
    manifest moved aside after a good install, then rerun    -> matching units adopted
    one file changed after a good install, then rerun        -> reported as locally modified, bytes kept
    team checkout tracks one file of a sidecar skill folder  -> matching files deleted, user file retained, status unchanged
    rerun with no upstream change                            -> no file changes, including exclude and manifest
    ```

  - The fault-injection case arms the fault only after the intent manifest
    exists, and asserts that no unit was complete before the rerun.
  - Existing full-install tests pass without edits to their expectations.

## Acceptance Criteria

A repository may already contain provider configuration for all four
clients. After a sidecar install:

- every pre-existing team file is byte-identical;
- `git status --porcelain --untracked-files=all` is unchanged;
- only sidecar-owned, ignored units exist, and the manifest records them;
- no hook, MCP, or configuration takeover occurs;
- a plain `install_bootstrap.py TARGET` on that repository never runs a full
  install.

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
