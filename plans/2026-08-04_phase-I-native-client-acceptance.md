---
name: 2026-08-04_phase-I-native-client-acceptance
type: small-plan
parent_plan: bootstrap-guidance-runtime-modernization
phase_index: 9
status: complete
closeout_session_log: .claude/session_logs/2026-08-08_bootstrap-guidance-runtime-modernization-phase-I.md
---

# Small Plan: 2026-08-04_phase-I-native-client-acceptance

## Scope

Add opt-in native Claude/Codex acceptance probes that test what structural
validation cannot: discovered instructions, trusted project hooks, compact/
resume behavior, and actual named-agent model/effort routing. Keep the default
offline test suite deterministic and credential-free.

## Ownership

- `coder`: probe CLI, result schema, redaction, and fixtures.
- `verifier`: native matrix execution and structural fallback.
- `reviewer`: `code`, `architecture`, `security`, `tests`, `performance`,
  `documentation`, `ponytail`.
- `documenter`: operator guide, prerequisites, and interpretation.

## Required Skills

- `ponytail` (`full`), `testing-patterns`, `context-manager-testing`,
  `run-tests`, `documentation`, `ponytail-review`.

## Steps

- [x] Add an opt-in script with `--client claude|codex|all`, `--require`, and
  machine-readable JSON output. Missing binaries/auth/trust are `WARN` by
  default and failures under `--require` are non-zero.
- [x] Probe root and scoped instruction discovery, critical workflow/command
  invariants, and behavior after compact/resume without exposing conversation
  content or credentials.
- [x] Probe project hook discovery/trust status without approving hooks or
  mutating user trust settings.
- [x] For Codex, spawn each named role in a trusted temporary consumer with no
  root model override. Capture client-reported agent type/model/effort metadata
  and assert the exact six-role matrix plus coder escalation contract.
- [x] Run A/B probes for candidate config removals only in the probe workspace;
  never alter generated defaults until all supported versions pass repeatedly.
- [x] Add mocked unit tests for output parsing, redaction, timeout, missing
  client, untrusted project, schema drift, and partial agent failure.
- [x] Document a release checklist requiring native probes before raising the
  minimum client version or removing a compatibility shim.

## Verification

```bash
uv run pytest tests/ -q --tb=short
uv run mypy scripts/ --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
# Opt-in, authenticated/trusted environment only:
uv run python scripts/check_native_clients.py --client all --require --json
```

## Acceptance Criteria

- Offline CI remains deterministic and needs no Claude/Codex credentials.
- Native probes detect instruction truncation, missing hook trust, and model/
  effort inheritance regressions.
- The MultiAgent V2 shim has an empirical, versioned removal gate rather than
  a documentation-silence assumption.

## Native Evidence At Closeout

Closed with documented `WARN` evidence, not native `PASS`:

- Persistent workspace preparation: `PASS`.
- Codex execution: `WARN` — the probe workspace has not been manually trusted,
  and the probe deliberately never grants trust to itself.
- Claude execution: `WARN` — binary/authentication unavailable.

Consequently the Codex MultiAgent V2 block and the nesting shims remain in
place. The removal gate is empirical and versioned: it requires repeated
native `PASS` under `--require` across supported client versions.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
