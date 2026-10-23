# Session: Restorer symlink checks and devcontainer mount folders

**Date:** 2026-10-23
**Plan:** `.claude/plans/2026-10-23_phase-C-restorer-and-devcontainer-hardening.md`
**Status:** COMPLETED

## Goal

Make `restore-root-adapters.sh` refuse a symlinked `.claude` or `.claude/bootstrap-root` (defense in depth), and have the generated `devcontainer.json` create both bind-mount source folders on the host before the container starts.

## Work Log

- Phase B committed as `cedb3b0` and pushed; the post-commit hook advanced `current_phase` to this phase.
- This repository's own `.devcontainer/` is untracked (`.git/info/exclude`) and byte-identical to the generated copy, so the overlay refresh updates it without touching the outer diff.
- Coder implemented steps 1-3 with no deviations: two one-line symlink refusals after `fail()` (the early `exit 0` stays first), the list-form `initializeCommand`, one inline validator check, and three tests plus a `_restore_from_devcontainer` helper. Negative controls: on the `HEAD` restorer both rejection tests failed (exit 0 instead of 1) and a scratch reproduction showed the old script copying an outside `CLAUDE.md` into the root; removing `initializeCommand` failed `validate_targets.py`. Coder checks: 367 passed across the three test files; `validate_targets.py` PASS; ruff clean.
- I wrote the step 4 docs myself (three small edits): the README devcontainer bullet no longer asks for a hand-made `~/.openwiki`; `docs/runtime-checks.md` describes the `initializeCommand` and the restorer's symlink refusal; `docs/smoke-tests.md` gained one Expected bullet.
- Regenerated and refreshed the overlay; the full required check set and the review are running.
- Review round 1 (seven profiles): gate WARN with one MINOR and two open requests. MINOR fixed: `_restore_from_devcontainer` duplicated `_restore`, so `_restore` now takes a `script_dir` argument (default the hooks copy) and the two callers pass `.devcontainer`; the 12 restorer tests pass, ruff and mypy clean. Open request on a real devcontainer start answered with a probe in the session scratchpad (`phase-c/dc-probe/`): an `alpine:3.20` devcontainer carrying the generated `initializeCommand` and `mounts`, started by `@devcontainers/cli up` with `HOME` pointed at an empty folder. The CLI logged `Run: mkdir -p <home>/.openwiki <home>/.cache/huggingface`, both folders appeared owned by the host user, and the container started with both bind mounts (`outcome: success`). The same config without `initializeCommand` failed: `invalid mount config for type "bind": bind source path does not exist: <home>/.cache/huggingface`. Both probe containers were removed.

## [LEARN] Entries

- [LEARN:tooling] Devcontainer `mounts` use Docker's `--mount`, which refuses a missing bind source; a list-form `initializeCommand` creates the sources on the host first. Prove such config with the exact keys on an `alpine` image and `@devcontainers/cli up` under an empty `HOME`, not a full image rebuild.

## Verification

```text
PASS        0.3s  uv run python scripts/generate_targets.py --all
PASS      111.8s  uv run pytest tests/test_state_sync.py tests/test_validate_targets.py tests/test_check_runtime.py -q --tb=short
PASS       50.6s  uv run python scripts/validate_targets.py
PASS        0.9s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS      322.9s  uv run python .claude/scripts/verify.py phase --format text
```

- Findings: `.claude/quality_reports/findings-2026-10-23_phase-C-restorer-and-devcontainer-hardening.json` (0 findings after round 2, gate PASS, seven profiles including `config`).
- optional 1: PASS — with `HOME` pointed at an empty folder, `@devcontainers/cli up` on an `alpine:3.20` devcontainer carrying the generated `initializeCommand` and `mounts` (not the full CUDA image) created both folders owned by the host user and started the container with both bind mounts; the same config without `initializeCommand` failed with `bind source path does not exist`.

## Open Questions / Next Steps

- Phase D next: the OpenWiki refresh and the stale-claims audit across live guidance.
