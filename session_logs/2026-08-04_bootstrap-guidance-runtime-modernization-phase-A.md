# Session: Bootstrap guidance/runtime modernization — Phase A

**Date:** 2026-08-04
**Plan:** .claude/plans/2026-08-04_phase-A-runtime-drift-contract.md
**Status:** BLOCKED

## Goal

Define the runtime ownership/parity contract, detect stale self-install
surfaces, and make `REVIEW -> DOCUMENT -> SCORE` authoritative everywhere
without comparing or overwriting consumer-owned AI state.

## Work Log

- **13:12** - User approved implementation of all nine phases and requested the
  orchestrated workflow.
- **13:12** - Pre-flight passed: outer repository is clean on `dev`; the big
  plan and all nine small plans validate.
- **13:12** - Reconfirmed the protected Codex routing invariant from commit
  `82e9fbe`, `.claude/MEMORY.md`, and the 2026-07-18 model-tiering session log:
  the MultiAgent V2 metadata-exposure shim must remain until a native routing
  matrix proves safe removal.
- **13:14** - Created branch
  `bootstrap-guidance-runtime-modernization_implementation` and delegated Phase
  A through Ponytail full mode.
- **13:24** - The first implementation and verifier pass completed. The initial
  review found one critical and four major findings, so the orchestrator invoked
  its single permitted Sol/xhigh coder escalation.
- **13:46** - The escalated implementation removed the executable ownership
  manifest, added containment and tracked-file protections, made installer
  exclusions contract-driven, and expanded regression coverage. Verification
  passed all 30 tests plus typing, lint, formatting, shell syntax, generation,
  and target validation.
- **13:52** - The post-escalation review still found three major issues: the
  restoration manifest is not install-mode-aware, the shell restoration hook
  duplicates the Python ownership enumeration, and the command-execution test
  observes the wrong working directory. Per the orchestrator escalation cap,
  the fix loop stopped and later phases were not started.

## [LEARN] Entries

- [LEARN:architecture] Runtime ownership metadata must encode the active install
  mode and remove entries that become inactive during mode migrations.
- [LEARN:architecture] Security-sensitive ownership allowlists need one generated
  source of truth; parallel Python and shell enumerations drift too easily.
- [LEARN:tests] Command-execution regressions must assert against an absolute
  marker or run the hook with an explicit working directory.

## Verification Results

```bash
UV_CACHE_DIR=.uv-cache uv run pytest -q                       # 30 passed
UV_CACHE_DIR=.uv-cache uv run mypy scripts                    # passed
UV_CACHE_DIR=.uv-cache uv run ruff check <changed-python>     # passed
UV_CACHE_DIR=.uv-cache uv run ruff format --check <changed>   # passed
bash -n shared/hooks/scripts/restore-root-adapters.sh          # passed
UV_CACHE_DIR=.uv-cache uv run python scripts/generate_targets.py --all
UV_CACHE_DIR=.uv-cache uv run python scripts/validate_targets.py  # passed
```

`scripts/check_runtime.py` reports only the six expected stale dogfood files
pending a local-only refresh. The final review gate failed on three major
findings; there were no critical or Ponytail findings.

## Score: not run

Scoring and persisted findings are intentionally deferred because review did not
converge and documentation is not final.

## Open Questions / Next Steps

- User direction is required to authorize an additional Phase A fix pass despite
  the repository's one-escalation-per-phase limit, or to stop and decide how to
  handle the preserved uncommitted branch state.
