---
name: 2026-08-09_phase-1-installer-allow-self
type: small-plan
parent_plan: installer-self-target-refresh
phase_index: 1
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-09_phase-1-installer-allow-self

## Scope

Add an explicit `--allow-self` opt-in to `install_bootstrap.py` so the
bootstrap repository can refresh its own dogfood overlay, propagate it through
`update_consumers.py`, correct the `check_runtime.py` repair diagnostic, then
actually run it and confirm the drift is resolved.

## Ownership

- `coder`: guard relaxation, flag plumbing, diagnostic text, tests.
- `verifier`: full suite, typing, linting, generation, validator, runtime check.
- `reviewer`: `code`, `architecture`, `security`, `tests`, `ponytail`.
- `documenter`: `docs/runtime-checks.md` known-gap block and installer docs.

## Required Skills

- `ponytail` (`full`), `testing-patterns`, `run-tests`, `documentation`,
  `ponytail-review`.

## Steps

- [ ] Add `--allow-self` to `install_bootstrap.py`; default remains fail-closed.
- [ ] Relax `validate_install_roots` for the source-inside-target case **only**,
  and only when the target is the bootstrap repository itself. Keep
  `source == target` and `target.is_relative_to(source)` rejected regardless.
- [ ] Plumb the flag through `update_consumers.py`.
- [ ] Update the `check_runtime.py` drift diagnostic so a stale path inside this
  repository prints a command that works.
- [ ] Add regression tests: the flag permits the dogfood case, still rejects the
  two dangerous cases, and the default (no flag) still rejects all three.
- [ ] **Run it.** Dry-run first, review removals, then refresh for real and
  confirm `check_runtime.py` drift failures are resolved.
- [ ] Replace the known-gap block in `docs/runtime-checks.md` with the working
  workflow.

## Verification

```bash
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

## Acceptance Criteria

- Without `--allow-self`, every overlapping-root case is still rejected.
- With `--allow-self`, only the dogfood case is permitted.
- `check_runtime.py` prints a repair command that works for this repository.
- The overlay is actually refreshed and drift failures are gone.
- Consumer install behavior is unchanged.

## Known Follow-Up (not this phase)

`.claude/settings.local.json` is absent from the generated target and not in
`CONSUMER_STATE_PATHS`, so the installer removes it as an obsolete owned file.
This affects every consumer today, not just self-install. Capture its contents
before refreshing and decide separately whether local settings should be
preserved.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
