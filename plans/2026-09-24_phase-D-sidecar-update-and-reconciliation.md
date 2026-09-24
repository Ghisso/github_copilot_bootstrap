---
name: 2026-09-24_phase-D-sidecar-update-and-reconciliation
type: small-plan
parent_plan: consumer-sidecar-bootstrap-overlay
phase_index: 4
status: planned
closeout_session_log:
---

# Small Plan: Phase D — Sidecar Update and Reconciliation

## Scope

Prove that sidecar consumers update correctly across bootstrap versions
through `update_consumers.py`, including batches that mix full and sidecar
consumers. Then document both modes. Reconciliation logic already exists from
Phases B and C; this phase adds no second update path.

### Required Skills

- `shared/skills/ponytail/SKILL.md` — `full`
- `shared/skills/code-style/SKILL.md`
- `shared/skills/testing-patterns/SKILL.md`
- `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md`
- `shared/skills/documentation/SKILL.md`
- `shared/skills/humanize/SKILL.md` — `edit`, docs profile

## Primary Files

- `tests/test_sidecar_update.py` — new.
- `scripts/update_consumers.py` — change only if a batch test exposes a gap.
- `scripts/sidecar_overlay.py` — fixes found by the upgrade suite only.
- `README.md`, `docs/target-mapping.md`, and `docs/architecture.md` where
  they describe installer ownership.

## Steps

- [ ] **1. Confirm batch behavior.**
  - **Owner:** `coder`
  - `update_consumers.py` passes no `--mode`, so the installer detects each
    target's mode.
  - Test a mixed batch with `--local-only` and with
    `--commit-copilot-surface`. Full targets use the options; sidecar targets
    warn once and ignore them.

- [ ] **2. Add the upgrade regression suite.**
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
    10. manifest corrupted -> abort with remedy; after the remedy, the rerun adopts matching units;
    11. full-to-sidecar and sidecar-to-full attempts through `update_consumers.py` -> abort;
    12. dry-run update -> no changes;
    13. mixed batch through `update_consumers.py`;
    14. install, update, update -> the second update changes no file.
  - Every test must fail when the rule it covers is removed.

- [ ] **3. Document consumer behavior.**
  - **Owner:** `documenter`
  - In README, split install and update guidance into four parts: full
    install, personal sidecar install, updating full consumers, and updating
    sidecar consumers.
  - Explain the team-repository use case, what the sidecar does not include,
    the `SKIPPED` and `RETAINED` reports and their remedies, manual removal
    (delete the paths listed in the manifest, the marked exclude block, and
    the manifest), and how to switch modes manually.
  - State the two behavior changes for full installs: a plain install now
    refuses a repository that tracks agent configuration and has no
    bootstrap evidence (pass `--mode full` to keep today's takeover), and
    sidecar mode supports the main worktree only.
  - Add the sidecar projection table to `docs/target-mapping.md` and point
    at `docs/sidecar-provider-contract.md` for evidence.
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
- aborts before any write on unsafe states.

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

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
