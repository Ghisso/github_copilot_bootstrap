# Session: Correct verified skill defects and close the compression protected-path gap

**Date:** 2026-09-12
**Plan:** `.claude/plans/2026-09-12_phase-A-skill-correctness-and-lifecycle.md`
**Status:** COMPLETED

## Goal

Correct the nine verified factual, security, and lifecycle defects in the
shared skill library, close the protected-path gap that left canonical
`shared/skills/**` sources compressible, and bring the small-plan template up
to the current closeout contract.

## Work Log

- **PRE-FLIGHT** - Classified the work as control-plane/high-risk because it
  changes `shared/skills/caveman-compress/scripts/detect.py`. Required review
  profiles: `code`, `architecture`, `security`, `tests`, `ponytail`. Read
  `.claude/MEMORY.md` and the canonical Task Lanes table. Tree clean on `dev`.
- **BRANCH** - Created `2026-09-12_skill-library-hardening_implementation`
  from clean `dev`. The branch-creation hook set the big plan to
  `in-progress`, recorded `started_at: 2026-09-12T08:32:57Z`, pointed
  `current_phase` at this phase, and flipped this plan to `in-progress`.
- **PLAN** - This phase is one of three in a revised big plan. The revision
  dropped three audit claims that failed verification: the numeric-score
  lifecycle was already removed in commit `2af3df7`; `.claude/instructions/
  workspace.md` is a live generated file, not an obsolete path; and the
  `ponytail` / `ponytail-review` descriptions match a mandate this repository
  states deliberately, so narrowing them was both wrong and build-breaking.
- **IMPLEMENT** - Delegated to `coder`, which applied `ponytail` in `full`
  mode. Ten canonical `shared/**` files changed plus one new test. No
  generated copy was hand-edited.
- **IMPLEMENT** - The coder verified the numpy claim properly rather than
  assuming it: numpy is absent from this repository's environment, so it built
  a throwaway virtual environment, installed numpy 2.5.3, and confirmed
  `isinstance(np.bool_(True), bool)` is `False` with method resolution order
  `bool -> generic -> object`.
- **VERIFY** - Re-ran the gates independently rather than accepting the
  coder's report. `verify.py phase` PASS, 1483 tests passed, mypy/ruff clean,
  `validate_targets.py` PASS.
- **VERIFY** - `check_runtime.py` initially failed with exit 1 and 28 stale
  runtime paths under `.agents/`, `.claude/`, and
  `.claude/bootstrap-root/.agents/`. The coder reported this honestly and
  correctly declined to fix it, because the prescribed remedy commits nested
  AI state, which belongs to the orchestrator's CLOSEOUT step (b). Resolved
  with `generate_targets.py --all` then
  `install_bootstrap.py . --allow-self --local-only`; `check_runtime.py` then
  returned exit 0 with zero failures.
- **REVIEW** - `reviewer` ran all five required profiles over the real diff,
  instructed to re-derive the affected surface itself rather than confirm the
  implementer's change list. It grepped the repository for surviving
  restatements of each corrected claim, byte-compared every touched canonical
  file against its generated counterparts, and mentally reverted `detect.py`
  to confirm the new test fails against the pre-change code for the intended
  reason. Gate result PASS, zero findings at every severity.
- **REVIEW** - Two independent readings converged on the same candidate
  concern (the new `detect.py` branch duplicates the return string of the
  branch above it) and both refuted it as matching that function's
  established repeated-branch style.

## [LEARN] Entries

- [LEARN:verification] In this authoring repository, `check_runtime.py`
  reporting `stale runtime path` after a `shared/**` edit is expected state,
  not a defect. The repository installs its own bootstrap, so its runtime
  copies under `.agents/`, `.claude/`, and `.claude/bootstrap-root/` lag until
  `generate_targets.py --all` is followed by
  `install_bootstrap.py . --allow-self --local-only`. Those paths are
  gitignored and outer-untracked, so the staleness never reaches the outer
  commit. The refresh commits nested AI state, which makes it orchestrator
  CLOSEOUT work rather than something the coder should run mid-implementation.
- [LEARN:verification] Read a verification exit status from the command
  itself, never through a pipe. `cmd | tail; echo $?` reports `tail`'s status
  and turned a real `check_runtime.py` exit 1 into an apparent pass during
  this phase. Use `cmd > file; echo $?` or `${PIPESTATUS[0]}` when a gate's
  pass/fail decision depends on it.
- [LEARN:review] An audit finding is a hypothesis until re-verified against
  the working tree. Three of this plan's original findings were stale or
  wrong, and one of them (narrowing the vendored `ponytail` descriptions)
  would have changed a hash-pinned file and failed
  `validate_targets.py:7641-7660` in every phase that ran it. Re-check each
  cited line before planning work around it.

## Verification Results

```bash
uv run python scripts/generate_targets.py --all
#   generated multi-agent -> dist/multi-agent

uv run python scripts/validate_targets.py
#   PASS generated target is structurally valid

uv run python scripts/check_runtime.py
#   exit 0, 0 FAIL lines (after regenerate + local-only reinstall)

uv run pytest tests/ -q --tb=short
#   1483 passed

uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
#   Success: no issues found in 30 source files

uv run ruff check shared scripts tests
#   All checks passed!

uv run ruff format --check shared scripts tests
#   30 files already formatted

uv run python .claude/scripts/verify.py phase --format text
#   phase: PASS (RUFF, MYPY, PYTEST, FRESH-001, FRESH-002, GEN-001 all PASS)

# Vendored hash constraint held:
#   9e2611144a8da730f110af6f789fd4dc9f6574f7fbff1fd5be7220b0b30a6fc3  shared/skills/ponytail/SKILL.md
#   bf0f50e5a406c8c1587ab4a69340369bf0293ef1022450cb9142468aa15f8656  shared/skills/ponytail-review/SKILL.md

# Receipts:
#   .claude/quality_reports/verification-phase-2026-09-12_phase-A-skill-correctness-and-lifecycle.json
#   .claude/quality_reports/verification-closeout-2026-09-12_phase-A-skill-correctness-and-lifecycle.json
```

## Open Questions / Next Steps

- Phase B (`2026-09-12_phase-B-skill-routing-and-provenance`) is next. Its
  first step corrects `shared/third_party/ponytail/UPSTREAM.md`, which
  currently understates the local fork: `ponytail/SKILL.md` is 72 lines
  against upstream's 120 with three sections dropped, and
  `ponytail-review/SKILL.md` is 38 against 57.
- Phase B must decide one canonical name between
  `.claude/instructions/workspace.md` and `workspace.instructions.md`. Both
  are generated and byte-identical today, so either reference resolves; this
  is a consistency choice, not a broken path.
- Upstream Ponytail `v4.9.0` was surveyed and deliberately not adopted. Its
  only vendored-surface change is already present locally at
  `shared/skills/ponytail/SKILL.md:51-52`.
