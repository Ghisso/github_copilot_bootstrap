---
name: 2026-08-04_phase-C-scoped-policy-adapters
type: small-plan
parent_plan: bootstrap-guidance-runtime-modernization
phase_index: 3
status: complete
closeout_session_log: .claude/session_logs/2026-08-08_bootstrap-guidance-runtime-modernization-phase-C.md
---

# Small Plan: 2026-08-04_phase-C-scoped-policy-adapters

## Scope

Add target-neutral applicability metadata to conditional shared policies and
generate native scoped adapters. Keep always-on lifecycle rules concise and do
not create a second editable policy home.

## Ownership

- `coder`: policy metadata schema and target renderers.
- `verifier`: path-scope parity and discovery fixtures.
- `reviewer`: `code`, `architecture`, `security`, `tests`, `documentation`,
  `ponytail`.
- `documenter`: authoring and customization documentation.

## Required Skills

- `ponytail` (`full`), `context-manager-testing`, `testing-patterns`,
  `documentation`, `ponytail-review`.

## Steps

- [x] Define minimal frontmatter for target-neutral applicability (always-on or
  path patterns) and validate it in `shared/policies/`.
- [x] Generate Claude `.claude/rules/*.md` with `paths` only for genuinely
  conditional guidance; use always-on rules sparingly.
- [x] Generate Copilot `applyTo` metadata from the same source patterns.
- [x] For Codex, use nested `AGENTS.md` only when directory ownership is stable;
  otherwise expose conditional workflows as skills to avoid consuming the
  combined project-doc budget.
- [x] Preserve `.claude/instructions/` as the canonical installed policy library
  used by agents/skills; native adapters must point to or derive from it and
  must never become authoring sources.
- [x] Add cross-target tests proving one source policy produces equivalent
  path-scope semantics for Claude and Copilot. For Codex, assert the skill
  fallback and absence of speculative nested project documents when stable
  directory ownership is unavailable. Keep real-client loading probes in
  Phase I.

## Verification

```bash
uv run pytest tests/test_validate_targets.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
```

## Acceptance Criteria

- Claude and Copilot conditional adapters encode equivalent relevant-path
  scopes; Codex uses skills unless stable directory ownership is proven.
- Scope metadata is single-homed and validated.
- Root guidance budgets from Phase B remain satisfied.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
