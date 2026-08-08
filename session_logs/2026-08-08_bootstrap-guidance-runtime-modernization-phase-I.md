# Session: Bootstrap guidance/runtime modernization — Phase I

**Date:** 2026-08-08
**Plan:** .claude/plans/2026-08-04_phase-I-native-client-acceptance.md
**Status:** COMPLETED

## Goal

Add opt-in native Claude/Codex acceptance probes that test what structural
validation cannot — discovered instructions, trusted project hooks, and actual
named-agent model/effort routing — while keeping the default offline test
suite deterministic and credential-free.

## Work Log

- Added `scripts/check_native_clients.py` with `--client claude|codex|all`,
  `--require`, `--prepare-only`, `--workspace`, and machine-readable JSON
  output. Missing binaries, missing auth, and untrusted workspaces are `WARN`
  by default and non-zero only under `--require`.
- Added `shared/schemas/native-client-observation.schema.json` so probe output
  is a versioned contract rather than ad-hoc prose, and so schema drift is
  detectable.
- Kept the probe strictly read-only with respect to trust: it prepares stable
  `control` and `candidate` workspaces for manual operator inspection but never
  approves project hooks and never mutates user trust settings.
- Implemented A/B comparison that independently parses control and candidate
  results instead of trusting a single combined run.
- Added mocked unit tests covering output parsing, redaction, timeout, missing
  client, untrusted project, schema drift, and partial agent failure
  (16 focused tests).
- Documented `docs/native-client-acceptance.md` as the operator guide and
  release checklist, and updated `README.md`, `docs/runtime-checks.md`,
  `docs/smoke-tests.md`, and `docs/2026-08-08-codex-routing-compatibility.md`.

## Native Evidence Limitations

This phase closes with honest `WARN` evidence, not a native `PASS`:

```text
codex   WARN  unavailable_untrusted   # workspace not manually trusted
claude  WARN  unavailable_untrusted   # binary/auth unavailable
```

Persistent workspace preparation passes. Executing the required native matrix
needs a human to inspect and manually trust the stable `control` and
`candidate` workspaces, and needs an available, authenticated Claude binary:

```bash
uv run python scripts/check_native_clients.py \
  --workspace /tmp/native-client-probe-release --prepare-only --json
# human inspects and trusts control + candidate, then:
uv run python scripts/check_native_clients.py \
  --workspace /tmp/native-client-probe-release --client all --require --json
```

Because no executed native evidence exists yet, the Codex MultiAgent V2 block
and the nesting shims **remain in place**. Their removal gate is now empirical
and versioned — it requires repeated native `PASS` across supported client
versions, not documentation silence.

## Verification Results

```bash
uv run python scripts/generate_targets.py --all                  # PASS twice, deterministic
uv run python scripts/validate_targets.py                        # PASS
uv run pytest tests/ -q --tb=short                               # 111 passed
uv run mypy . --ignore-missing-imports --explicit-package-bases  # PASS, 19 files
uv run ruff check scripts/ tests/                                # PASS
uv run ruff format --check <changed Python files>                # PASS
git diff --cached --check                                        # PASS
```

Review: two sequential passes (`code`, `architecture`, `security`, `tests`,
`performance`, `documentation`, `ponytail`) with zero surviving findings.

`check_runtime.py` continues to report the known stale installed dogfood
overlay and a missing optional `gh`. Neither was hidden by hand-editing
generated files or by mutating trust state.

## Score: 100/100 — EXCELLENCE

- Findings: `.claude/quality_reports/findings-20260808T145657Z.json`
- Score: `.claude/quality_reports/score-20260808T145657Z.json`

## [LEARN] Entries

- [LEARN:testing] Native acceptance must keep three evidence tiers distinct:
  structural validation, executed native runs, and unavailable/untrusted. A
  probe that collapses the third tier into "pass" reports confidence it never
  measured.
- [LEARN:testing] Model prose cannot prove client routing metadata. Assert on
  the client-reported agent type/model/effort fields, not on what the model
  says about itself.
- [LEARN:testing] Trusted-project probes need a stable, operator-inspected
  workspace. Throwaway temp dirs cannot be manually trusted, and a probe must
  never grant trust to itself.
- [LEARN:testing] A/B acceptance must parse and compare control and candidate
  independently; a single combined run cannot distinguish a real difference
  from a shared failure.

## Open Questions / Next Steps

- Big plan `bootstrap-guidance-runtime-modernization` is complete (Phases A–I).
- Before raising a minimum client version or removing any compatibility shim,
  run the native matrix under `--require` on a trusted workspace with an
  authenticated Claude binary and record repeated `PASS`.
