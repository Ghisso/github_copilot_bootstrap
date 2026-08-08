---
name: 2026-08-04_phase-K-codex-scoped-instruction-semantics
type: small-plan
parent_plan: bootstrap-guidance-runtime-modernization
phase_index: 11
status: complete
closeout_session_log: .claude/session_logs/2026-08-09_bootstrap-guidance-runtime-modernization-phase-K.md
---

# Small Plan: 2026-08-04_phase-K-codex-scoped-instruction-semantics

## Scope

Phase J left `scoped_instruction_sentinel` non-deterministic for Codex: `PASS`
on one run, `FAIL` on two. The cause is a semantic mismatch, not flakiness.

Per the official Codex documentation, Codex discovers scoped instructions by
walking from the Git root **down to the current working directory**, taking at
most one file per directory (`AGENTS.override.md`, then `AGENTS.md`, then
`project_doc_fallback_filenames`), concatenating root -> cwd within
`project_doc_max_bytes` (32 KiB default). Codex scoping is therefore
**directory-based**.

This bootstrap scopes policy by **glob** (`applicability: [src/**/*.py, ...]`)
and renders native adapters for two targets only:

| Target | Native scoped surface |
| --- | --- |
| Copilot | `.github/instructions/*.instructions.md` with `applyTo` |
| Claude | `.claude/rules/*.md` with `paths:` |
| Codex | **none** |

The generated target ships no nested `AGENTS.md`, and no `src/` or `tests/`
directories to host one. The probe additionally runs Codex with the consumer
root as cwd, where a nested file would not load even if present. So the probe
asks Codex whether it discovered a surface that does not exist, and Codex
answers inconsistently.

**Decision (operator, 2026-08-09):** fix the probe, not the generated target.
Do not invent a Codex scoped surface or create directories in consumer repos.
Record the gap honestly.

## Ownership

- `coder`: per-client sentinel semantics and regression tests.
- `verifier`: full suite plus a repeated native matrix for determinism.
- `reviewer`: `code`, `architecture`, `security`, `tests`, `ponytail`.
- `documenter`: operator guide and the Codex scoping gap.

## Required Skills

- `ponytail` (`full`), `testing-patterns`, `run-tests`, `documentation`,
  `ponytail-review`.

## Steps

- [x] Define `scoped_instruction` per client in the probe prompt rather than
  as one target-neutral question: for Codex assert that the root `AGENTS.md`
  routes to the canonical `.claude/instructions/` policies; keep the existing
  meaning for Claude (`.claude/rules/` `paths:` adapters).
- [x] Keep the observation schema and its four sentinel fields unchanged so
  existing parsing, parity, and drift checks still apply.
- [x] Raise the default probe timeout, or document the required `--timeout`,
  so a Codex run that executes control and candidate consecutively does not
  time out at 120s.
- [x] Add regression tests asserting the per-client prompt difference and that
  neither client's prompt claims a surface the target does not generate.
- [x] Document the Codex scoping gap in `docs/native-client-acceptance.md`:
  Codex has no directory-scoped adapter here by deliberate decision, with the
  upstream discovery rules recorded so a future phase can revisit it.
- [x] Re-run the native matrix at least three times and record whether
  `scoped_instruction` is now deterministic for both clients.

## Verification

```bash
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_native_clients.py \
  --workspace /tmp/native-client-probe-release --client all --timeout 420 --json
```

## Acceptance Criteria

- `scoped_instruction` returns the same verdict across repeated native runs for
  both clients.
- No probe question asserts a surface the generated target does not produce.
- The generated target and consumer repositories are unchanged by this phase.
- The Codex scoping gap is documented rather than silently closed.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
