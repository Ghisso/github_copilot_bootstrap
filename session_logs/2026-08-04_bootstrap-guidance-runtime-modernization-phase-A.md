# Session: Bootstrap guidance/runtime modernization — Phase A

**Date:** 2026-08-04
**Plan:** .claude/plans/2026-08-04_phase-A-runtime-drift-contract.md
**Status:** COMPLETED

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
- **14:04** - The user explicitly authorized as many additional fix passes as
  required. Phase A resumed with a focused Sol/xhigh implementation pass for
  the three remaining major findings.
- **14:22** - The authorized repair passed 31 tests and resolved the prior three
  majors, but the next two-pass review found two further majors: committed
  Copilot install mode is not retained across repeat/batch updates, and runtime
  parity does not detect obsolete bootstrap-owned files. One dead ownership API
  also remained as a Ponytail minor. A fourth focused fix pass began.
- **14:50** - The fourth pass added mode retention and reverse parity and again
  passed 31 tests, but adversarial fixtures found four further majors: nested
  Git files could be pruned, committed-to-local migration retained stale tracked
  Copilot files, overlapping source/destination paths were accepted, and direct
  script typing failed. A fifth focused fix pass began, including the associated
  Ponytail cleanup.
- **15:04** - The fifth pass added ten installer regressions and passed 41 tests,
  direct script typing, lint, formatting, shell syntax, generation, validation,
  and diff hygiene. Two adversarial review rounds returned no code, architecture,
  security, test, or Ponytail findings.
- **15:08** - README and runtime/target documentation were updated. A single
  inaccurate pruning instruction was corrected, and documentation re-review
  passed with no findings.
- **15:10** - Phase A staging failed because `.git/index` is read-only. The
  required escalation was denied after the environment exhausted its approval
  quota. Per workflow, findings/score/commit were not generated and Phase B did
  not start.
- **16:08** - The user staged the reviewed Phase A file set manually, restoring
  the workflow boundary without changing the diff.
- **16:09** - Persisted an empty findings report across code, architecture,
  security, tests, Ponytail, and documentation profiles. The quality scorer
  returned 100/100 EXCELLENCE with 41 tests, zero lint/type deductions,
  `dirty: false`, and the staged content hash.

## [LEARN] Entries

- [LEARN:architecture] Runtime ownership metadata must encode the active install
  mode and remove entries that become inactive during mode migrations.
- [LEARN:architecture] Security-sensitive ownership allowlists need one generated
  source of truth; parallel Python and shell enumerations drift too easily.
- [LEARN:tests] Command-execution regressions must assert against an absolute
  marker or run the hook with an explicit working directory.
- [LEARN:workflow] The quality reports hash staged content, so staging must occur
  after documentation and before findings/score generation; an environment that
  denies `.git/index` writes blocks the phase boundary even when review passes.
- [LEARN:security] Installer path-overlap and nested Git-file fixtures belong in
  the permanent ownership-contract suite because both failures can escape
  ordinary generated-target validation.

## Verification Results

```bash
UV_CACHE_DIR=.uv-cache uv run pytest -q                       # 41 passed
UV_CACHE_DIR=.uv-cache uv run pytest -q -W error::DeprecationWarning
                                                               # 41 passed
UV_CACHE_DIR=.uv-cache uv run mypy scripts                    # passed
UV_CACHE_DIR=.uv-cache uv run ruff check scripts tests        # passed
UV_CACHE_DIR=.uv-cache uv run ruff format --check <changed>   # passed
bash -n shared/hooks/scripts/restore-root-adapters.sh         # passed
UV_CACHE_DIR=.uv-cache uv run python scripts/generate_targets.py --all
UV_CACHE_DIR=.uv-cache uv run python scripts/validate_targets.py  # passed
git diff --check                                              # passed
```

`scripts/check_runtime.py` reports only stale local dogfood paths pending the
denied local-only refresh, including the obsolete skill that reverse parity now
correctly detects. Final code and documentation reviews both passed with empty
findings arrays. Protected Codex MultiAgent V2 metadata and `max_depth = 1`
remain intact.

## Score: 100/100 — EXCELLENCE

- Findings: `.claude/quality_reports/findings-20260804T160847Z.json`
- Score: `.claude/quality_reports/score-20260804T160847Z.json`
- Tests: 41 passed
- Dirty: false

## Open Questions / Next Steps

- Commit the staged Phase A change set, then begin Phase B root-guidance budgets.
