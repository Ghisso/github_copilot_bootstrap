---
name: 2026-09-24_phase-D-sidecar-update-and-reconciliation
type: small-plan
parent_plan: consumer-sidecar-bootstrap-overlay
phase_index: 4
status: complete
closeout_session_log: .claude/session_logs/2026-09-25_sidecar-phase-D-update-and-reconciliation.md
---

# Small Plan: Phase D — Sidecar Update and Reconciliation

## Scope

Prove that sidecar consumers update correctly across bootstrap versions
through `update_consumers.py`, including batches that mix full and sidecar
consumers. Change the updater so that a refused or failed target no longer
stops the batch (big plan, Decision 20). Then document both modes.
Reconciliation logic already exists from Phases B and C; this phase adds no
second update path.

### Required Skills

- `shared/skills/ponytail/SKILL.md` — `full`
- `shared/skills/code-style/SKILL.md`
- `shared/skills/testing-patterns/SKILL.md`
- `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md`
- `shared/skills/documentation/SKILL.md`
- `shared/skills/humanize/SKILL.md` — `edit`, docs profile

## Primary Files

- `scripts/update_consumers.py` — skip-and-report batch handling, and a
  docstring that describes both modes.
- `tests/test_sidecar_update.py` — new.
- `scripts/sidecar_overlay.py` — fixes found by the upgrade suite only.
- `scripts/validate_targets.py` — only where its updater checks need the new
  failure summary.
- `README.md`, `docs/target-mapping.md`, and `docs/architecture.md` where
  they describe installer ownership.

## Steps

- [x] **1. Make batches skip and report failures.**
  - **Owner:** `coder`
  - In `update_consumers.py`, run every target. When the installer exits
    non-zero, or a target is not a directory, record the target and its exit
    code and continue with the next one. After the last target, print one
    line per failed target and exit 1. Print `All projects updated.` only
    when every target succeeded.
  - A generator failure still stops the batch before any target runs.
  - Keep the dry-run lines that `check_batch_dry_run_summary` in
    `validate_targets.py` requires, and print `=== Preview complete: ...`
    only for targets that succeeded.
  - `update_consumers.py` passes no `--mode`, so the installer detects each
    target's mode.

- [x] **2. Confirm option forwarding in mixed batches.**
  - **Owner:** `coder`
  - Test a mixed batch with `--local-only` and with
    `--commit-copilot-surface`. Full targets use the options; sidecar targets
    warn once and ignore them.

- [x] **3. Add the upgrade regression suite.**
  - **Owner:** `coder`
  - In `tests/test_sidecar_update.py`, build two bootstrap versions as
    fixture sources, install the first, and update to the second:
    1. skill content changed -> updated at both roots;
    2. skill added -> installed;
    3. skill removed -> removed when unchanged; a modified copy is kept and reported;
    4. bridge text changed -> updated;
    5. projection modified by the user -> kept, reported, and reported again on the next run;
    6. projection replaced by a tracked team file -> record and exclude line dropped, file untouched;
    7. unrelated tracked team config added after install -> untouched;
    8. exclude block deleted by the user -> restored;
    9. owned projection deleted by the user -> reinstalled;
    10. manifest corrupted -> abort with remedy; after the remedy, the rerun adopts the listed units that match;
    11. a batch target with both full and sidecar evidence -> refused before any write, the next target updated, the summary names the refused target, exit 1;
    12. a batch target that the full path refuses (for example an unproved `.agents/` tree) -> reported, the other targets updated, exit 1;
    13. dry-run update -> no changes;
    14. mixed batch of full and sidecar targets through `update_consumers.py` -> both updated, exit 0;
    15. install, update, update -> the second update changes no file.
  - Every test must fail when the rule it covers is removed.

- [x] **4. Document consumer behavior.**
  - **Owner:** `documenter`
  - In README, split install and update guidance into four parts: full
    install, personal sidecar install, updating full consumers, and updating
    sidecar consumers.
  - Explain the team-repository use case, what the sidecar does not include,
    the `SKIPPED` and `RETAINED` reports and their remedies, manual removal
    (delete the paths listed in the manifest, the marked exclude block, the
    manifest, and the staging folder), and how to switch modes manually.
  - State the behavior changes:
    - a plain install now refuses a repository that tracks a path the full
      install writes and has no bootstrap evidence; pass `--mode full` to
      keep today's takeover. This includes a fresh clone of a full consumer
      whose `.claude/` is not restored yet: run
      `bash .devcontainer/state-sync.sh setup` first, or pass `--mode full`
      (Phase C found this through `validate_state_sync()`);
    - sidecar mode supports the main worktree only;
    - a batch update now finishes the other targets when one fails, then
      exits 1.
  - Describe the full install's takeover as the big plan's Context lists it,
    including the deleted untracked files in root adapter folders and the
    overwritten `.devcontainer/`.
  - Document the limits:
    - the main worktree's exclude lines also hide those paths in linked
      worktrees;
    - worktrees that VS Code or the Codex app create for background sessions
      contain no sidecar files unless they are listed in
      `git.worktreeIncludeFiles` or `.worktreeinclude`;
    - Git overwrites an edited sidecar file without warning when the team
      later commits a file at the same path, so keep personal edits
      elsewhere.
  - Say that the vendored Ponytail skills ship with their MIT `LICENSE`.
  - Add the sidecar projection table (write roots, read roots, and bridges)
    to `docs/target-mapping.md`, and point at
    `docs/sidecar-provider-contract.md` for evidence.
  - From the Phase A native runs: Antigravity is unverified for sidecar v1
    (no rules-file bridge ships), Codex is skill-only, and Copilot's Local
    agent loads both the `.github/instructions/` and `.claude/rules/`
    bridges, so it sees the same bridge text twice.
  - Do not describe the sidecar as equivalent to the full bootstrap.

## Acceptance Criteria

Expected lifecycle:

```text
uv run python scripts/install_bootstrap.py /work/team-repo --mode sidecar   # first use
uv run python scripts/update_consumers.py /work/team-repo /work/own-repo    # later, mixed batch
```

The updater:

- auto-detects sidecar mode;
- updates sidecar content by the reconciliation rules;
- preserves team-owned configuration and never adds hooks;
- leaves `git status --porcelain --untracked-files=all` unchanged;
- removes only unchanged, obsolete, sidecar-owned units;
- preserves and reports locally modified sidecar files;
- refuses an unsafe target before any write, finishes the other targets,
  and exits 1 with a summary.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/test_sidecar_overlay.py tests/test_sidecar_install.py tests/test_sidecar_update.py tests/test_install_bootstrap.py -q --tb=short
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- The operator runs `update_consumers.py` on a clone of a real team repository with configuration for all four clients and records `git status --porcelain --untracked-files=all` before and after.

## Review Profiles

- `code`
- `architecture`
- `security`
- `tests`
- `ponytail`
- `documentation`

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT).

- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
