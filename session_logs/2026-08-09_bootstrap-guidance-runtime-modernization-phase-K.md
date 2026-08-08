# Session: Bootstrap guidance/runtime modernization — Phase K

**Date:** 2026-08-09
**Plan:** .claude/plans/2026-08-04_phase-K-codex-scoped-instruction-semantics.md
**Status:** COMPLETED

## Goal

Make `scoped_instruction` deterministic for Codex by asking each client only
about the scoped surface its own target actually ships.

## Research First

Read the official Codex documentation before changing anything
(<https://learn.chatgpt.com/docs/agent-configuration/agents-md>). Codex
discovers scoped instructions **by directory**: it walks from the Git root
down to the current working directory, taking at most one file per directory
(`AGENTS.override.md`, then `AGENTS.md`, then
`project_doc_fallback_filenames`), concatenating root -> cwd until
`project_doc_max_bytes` (32 KiB default). A nested file loads only when Codex
is working inside that directory.

This bootstrap scopes policy by **glob** (`applicability:`) and renders native
adapters for Copilot (`applyTo`) and Claude (`paths:`) only. It generates no
nested `AGENTS.md`, and the target ships no `src/` or `tests/` directory to
host one. The probe also ran Codex with the consumer root as cwd, where a
nested file would not load even if present.

So Codex was being asked whether it discovered a surface that does not exist.
The inconsistent answers were a fair response to an unanswerable question, not
model flakiness.

## Decision

Operator chose to **fix the probe, not the generated target**: do not invent a
Codex scoped surface, do not create directories in consumer repositories, and
record the gap honestly.

## Work Log

- Added `scoped_instruction_question(client)` so the sentinel means something
  true per client: for Codex, that the root `AGENTS.md` routes to
  `.claude/instructions/`; for Claude, that a `.claude/rules/` adapter declares
  `paths:` frontmatter.
- Left the observation schema and its four sentinel fields unchanged, so
  parsing, parity, and drift checks still apply unmodified.
- Raised the default timeout from 120s to 420s. Each client runs control and
  candidate consecutively, and 120s produced a spurious `codex_timeout`.
- Added regression tests for the per-client prompt split, for the guarantee
  that no prompt claims a surface the target does not generate, and for the
  timeout floor.
- Documented the Codex scoping gap and the upstream discovery rules in
  `docs/native-client-acceptance.md` so a future phase can revisit it.

## Verification Results

```bash
uv run pytest tests/ -q --tb=short                               # 119 passed
uv run mypy . --ignore-missing-imports --explicit-package-bases  # PASS, 19 files
uv run ruff check scripts/ tests/                                # PASS
uv run ruff format --check <changed Python files>                # PASS
uv run python scripts/generate_targets.py --all                  # PASS twice
uv run python scripts/validate_targets.py                        # PASS
git diff --cached --check                                        # PASS
```

## Native Evidence — Deterministic

Three consecutive full matrix runs, identical every time:

```text
codex   WARN   trust, root, scoped, workflow, hooks, shim, parity   PASS
               compact_resume, codex_role_matrix, coder_escalation  WARN (unexercised)
claude  WARN   trust, root, scoped, workflow, hooks, shim, parity   PASS
               compact_resume                                       WARN (unexercised)
summary: fail 0, warn 2
```

Every check the probe measures now passes for both clients, repeatably. The
generated target and consumer repositories are unchanged by this phase.

The remaining `unexercised` entries stay hardcoded `WARN`: `compact_resume` is
not implemented, and `coder_escalation` has no stable client event to read.
They are honest gaps, not failures, and the MultiAgent V2 removal gate is still
unmet.

## Score: 100/100 — EXCELLENCE

- Findings: `.claude/quality_reports/findings-20260808T162405Z.json`
- Score: `.claude/quality_reports/score-20260808T162405Z.json`

## [LEARN] Entries

- [LEARN:testing] A check that asks every target the same question measures
  the targets' differences, not their correctness. Codex scopes by directory,
  Claude and Copilot by glob pattern; one shared question made a passing
  system look intermittently broken.
- [LEARN:testing] Non-deterministic model output is a symptom worth tracing,
  not a flake to retry. Here it pointed at a surface the generator never
  produced.
- [LEARN:tooling] Read the client's own current documentation before changing
  code to satisfy it. The Codex `AGENTS.md` discovery rules (root -> cwd, one
  file per directory, `project_doc_max_bytes`) decided the whole design.

## Open Questions / Next Steps

- Codex-native directory scoping remains unimplemented by choice. If it is
  ever wanted, the documented discovery rules are what an implementation must
  satisfy.
- `compact_resume`, `codex_role_matrix`, and `coder_escalation` remain
  unmeasured; the MultiAgent V2 shim removal gate is still unmet.
