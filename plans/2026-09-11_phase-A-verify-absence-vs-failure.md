---
name: 2026-09-11_phase-A-verify-absence-vs-failure
type: small-plan
parent_plan: 2026-09-11_consumer-ceremony-friction
phase_index: 1
status: planned
closeout_session_log:
---

# Small Plan: Let the verifier tell "nothing to measure" from "measurement failed"

## Scope

Change `shared/scripts/verify.py` so a consumer with no tests can still
produce a `PASS` receipt, keep every real tool failure blocking, make each
blocking message name the exact fix, and document the consumer prerequisites
the gates assume.

## Findings This Plan Is Built On

- `aggregate_status` (`shared/scripts/verify.py:169`) returns `UNVERIFIED`
  when any check is `UNVERIFIED`. The commit gate requires the phase receipt
  status to equal `PASS` (`:1745`) and the push gate requires the closeout
  receipt status to equal `PASS` (`:1644`). `NOT_APPLICABLE` does not block.
- `_pytest_measurement` (`:2355`) maps exit 0 to `PASS`, exit 1 to `FAIL`,
  and everything else to `UNVERIFIED` with the text
  `pytest infrastructure exit (<rc>)`. pytest exits 5 when it collects no
  tests. A new project therefore cannot commit its first phase.
- `consumer_mypy_targets` (`:2480`) returns `None` when there is no
  `[tool.mypy]` scope (`files`, `packages`, or `modules`) and no `src/`
  directory; the check then reads
  `Mypy has no configured scope or conventional src root` and is
  `UNVERIFIED`.
- A missing executable surfaces as `Ruff did not run`, `mypy did not run`, or
  `pytest did not run`, all `UNVERIFIED`, with the raw OSError appended.
- `docs/architecture.md:358` and `docs/runtime-checks.md:446` mention
  `UNVERIFIED` for mypy only. No document says `UNVERIFIED` blocks the commit
  or lists what a consumer must install and configure.

## Decisions

- pytest exit 5 becomes `NOT_APPLICABLE` only when the repository has no test
  files at all: no file matching `test_*.py` or `*_test.py` outside
  `.claude/`, `.venv/`, and `.git/`. When test files exist and pytest still
  collects nothing, the result stays `UNVERIFIED` and the message says
  pytest found test files it did not collect, so `testpaths` or naming
  patterns need attention. Absence is honest; a collection mismatch is a
  misconfiguration.
- mypy without a scope stays `UNVERIFIED`. Typed Python is this bootstrap's
  standard, and running mypy over `.` on a flat layout produces duplicate
  module errors that would be worse than a clear refusal. The message must
  name the two accepted fixes: a `src/` directory, or a `[tool.mypy]` entry
  with `files`, `packages`, or `modules`.
- Missing executables stay `UNVERIFIED`. The message must say the tool is not
  installed in the project environment and name the command
  `uv add --dev ruff mypy pytest`.
- No receipt schema change. `NOT_APPLICABLE` is already a valid check state
  and already appears in `fast` and `closeout` receipts.

## Steps

- [ ] In `shared/scripts/verify.py`, add one helper that answers whether the
  repository contains any test file, walking from the root and skipping
  `.claude`, `.venv`, `.git`, and any directory Git ignores if that is cheap
  to honour; otherwise skip only the three named directories. Keep it to a
  few lines.
- [ ] In `_pytest_measurement`, when `rc == 5`: return
  `("NOT_APPLICABLE", "pytest collected no tests and the repository has no test files yet")`
  when the helper finds none, else return
  `("UNVERIFIED", "pytest collected no tests although test files exist; check testpaths and file naming")`.
  Leave the exit 0 and exit 1 branches unchanged.
- [ ] Replace the three `did not run` messages so an `OSError` with
  `errno.ENOENT` (or a `FileNotFoundError`) reads
  `<tool> is not installed in the project environment; run uv add --dev ruff mypy pytest`.
  Keep the generic text for other errors.
- [ ] Replace the mypy no-scope summary with
  `mypy has no scope: add a src/ directory or set [tool.mypy] files, packages, or modules in pyproject.toml`.
- [ ] Tests in `tests/test_verify.py`: a temp repository with no test files
  and pytest exit 5 yields `NOT_APPLICABLE` and the receipt aggregate is
  `PASS`; a repository holding `tests/test_x.py` that pytest still does not
  collect yields `UNVERIFIED`; a missing executable yields the install
  message; the mypy no-scope message names both fixes. Drive
  `_pytest_measurement` through a fake `_run` rather than a real pytest
  process where the existing tests already do so.
- [ ] Documentation. In `README.md`'s consumer install section, add a short
  "What the gates need from your project" list: ruff, mypy, and pytest as dev
  dependencies; a mypy scope or `src/`; tests, or acceptance that pytest is
  reported as not applicable until the first test exists. In
  `docs/runtime-checks.md` next to the existing `UNVERIFIED` sentence, state
  that any `UNVERIFIED` check makes the receipt `UNVERIFIED` and that the
  commit and push gates accept only `PASS`. Update `docs/architecture.md:358`
  to match.
- [ ] Regenerate with `uv run python scripts/generate_targets.py --all` and
  install locally with
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`.

## Review Profiles

Control-plane work on the canonical verifier: `code`, `architecture`,
`security`, `tests`, and `ponytail`. Load `.claude/skills/ponytail/SKILL.md`
in `full` mode before every coding step.

## Verification

```bash
uv run python .claude/scripts/verify.py fast --format text
uv run pytest tests/test_verify.py -q --tb=short
uv run pytest tests/ -q
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests && uv run ruff format --check shared scripts tests
uv run python scripts/generate_targets.py --all && uv run python scripts/install_bootstrap.py . --allow-self --local-only
uv run python scripts/validate_targets.py && uv run python scripts/check_runtime.py
```

Phase-specific proof: a scratch consumer with a `pyproject.toml`, ruff, mypy,
pytest, a `src/` package, and no tests gets a `phase` receipt whose status is
`PASS` and whose pytest check reads not applicable. The same consumer with an
uncollected `tests/test_x.py` gets `UNVERIFIED`.

## Risks And Fallback Paths

- A consumer relies on `UNVERIFIED` for no-tests to force test creation.
  The receipt text still says no tests exist, and the `tests` review profile
  still applies. If the user wants the stricter policy, keep exit 5 as
  `UNVERIFIED` and ship only the messages and documentation.
- The test-file walk is slow on a huge tree. It runs only on exit 5, which
  already means pytest walked the same tree.

## Done Criteria

- A test-less consumer produces a `PASS` phase receipt with an explicit
  not-applicable pytest check.
- Uncollected test files, missing executables, and a missing mypy scope stay
  blocking with messages that name the fix.
- README and runtime docs state the prerequisites and that `UNVERIFIED`
  blocks commits.
- Generated copies regenerated, never hand-edited.

## Closeout Checklist

- [ ] All steps implemented and verified
- [ ] `uv run pytest tests/ -q` passes
- [ ] mypy, ruff check, and ruff format pass
- [ ] `validate_targets.py` and `check_runtime.py` pass
- [ ] Targets regenerated and installed locally
- [ ] Code, architecture, security, tests, and Ponytail reviews complete
- [ ] Critical and major findings at zero
- [ ] Documentation updated
- [ ] `.claude/MEMORY.md` records the reusable lessons or the no-lessons marker
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested state checkpointed before persisting the closeout receipt
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
