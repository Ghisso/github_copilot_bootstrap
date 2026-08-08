---
name: 2026-08-04_phase-H-memory-security-authority
type: small-plan
parent_plan: bootstrap-guidance-runtime-modernization
phase_index: 8
status: complete
closeout_session_log: .claude/session_logs/2026-08-08_bootstrap-guidance-runtime-modernization-phase-H.md
---

# Small Plan: 2026-08-04_phase-H-memory-security-authority

## Scope

Document the authority boundary between synchronized shared AI state and
native client memories, and add a dedicated security threat model. This phase
must not disable user-level native memory or alter consumer state.

## Ownership

- `documenter`: memory model, `SECURITY.md`, README/architecture updates.
- `coder`: only minimal validator/schema checks required by the docs contract.
- `verifier`: install/update preservation and link validation.
- `reviewer`: `security`, `documentation`, `domain`, `ponytail` if executable
  validation changes are included.

## Required Skills

- `documentation`, `deep-audit`, `ponytail` (`full` only for executable
  changes), `ponytail-review` when required.

## Steps

- [x] Define `.claude/MEMORY.md` as curated, portable, cross-target project
  memory and native Claude/Codex memory as optional machine-local scratch.
- [x] Define conflict handling, privacy expectations, what may be promoted to
  shared memory, and what must remain local or secret.
- [x] Preserve the existing installer/updater contract that existing consumer
  `MEMORY.md` is never overwritten; add a regression only if coverage is weak.
- [x] Add root `SECURITY.md` covering assets, trust boundaries, hostile inputs,
  generated hook trust, command parsing, protected paths, nested Git state,
  credential handling, accepted escapes, reporting criteria, and exclusions.
- [x] Keep commands and workflow in `AGENTS.md`/`CLAUDE.md`; keep threat-model
  detail in `SECURITY.md` to avoid root-instruction bloat.
- [x] Update links and target-mapping docs without introducing an automatic
  native-memory disable setting.

## Verification

```bash
uv run pytest tests/test_install_bootstrap.py tests/test_validate_targets.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
```

## Acceptance Criteria

- Shared and native memory have unambiguous authority and privacy boundaries.
- Existing consumer memory remains byte-identical across install/update/migration.
- Security reviewers have one authoritative threat-model document.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
