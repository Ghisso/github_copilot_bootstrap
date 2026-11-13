---
description: "Always-on: Quality gates, verification commands, and testing protocol. Load when verifying or testing code."
applicability: always
---

# Quality Gates & Testing Protocol

## Verification Commands

```bash
uv run python .claude/scripts/verify.py fast --format json
```

`verify.py` is the single authority for deterministic measurement. During IMPLEMENT use `fast` and project-native focused checks, not the full suite after every small edit; `closeout.instructions.md` orders the final `phase` and `closeout` runs.

**Consumer-native scope.** Bootstrap authoring repositories keep explicit `shared`, `scripts`, and `tests` checks. Installed consumers use project-native configuration: Ruff excludes the bootstrap-owned `.claude` runtime, pytest uses native discovery, and Mypy uses its config's `files`, `packages`, or `modules` setting before the conventional `src/` fallback. If a required scope or config cannot be resolved safely, verification returns `UNVERIFIED`.

Never claim completion without running the unit, regression, and E2E tests the repository has; see `tests.instructions.md`.

## Verification Detail

There is no numeric score. A real lint, type, or test problem is `FAIL`; a tool that could not be measured is `UNVERIFIED`, never a silent pass.

| Signal | Source | Result |
|---|---|---|
| Any mypy type errors | `mypy --ignore-missing-imports --explicit-package-bases` | `FAIL` |
| Any pytest failures | `pytest tests/ -q` | `FAIL` |
| Any ruff violation or unformatted file | `ruff check` and `ruff format --check` | `FAIL` |

## Severity-Gated Findings

A findings report carries a git freshness binding, severity counts, `schema_version: 2`, the reviewer's `gate_result`, and `open_requests`. Only the orchestrator persists it:

```bash
uv run python .claude/scripts/record_findings.py . --findings-json - --phase <current_phase> --profile <name>... --gate-result <PASS|WARN|FAIL> [--open-request "<text>" ...] --out .claude/quality_reports/findings-<current_phase>.json
```

An empty findings list (`[]`) is the normal clean report, valid only with `PASS` and no open request. Give every surviving MINOR a `disposition` and non-empty `reason`.

| Gate | Requires |
|---|---|
| Phase-completion commit | `counts.critical == 0` and `counts.major == 0` in a fresh, matching report, a `disposition` and `reason` on every surviving MINOR, and `gate_result == "PASS"` with `open_requests == []` |
| Push / PR | The same contract across every completed phase (leading phases dated before 2026-08-29 with no receipt file excepted); the `gate_result` and profile rules apply only to `schema_version >= 2` reports |

The metadata matrix is exact: selecting the `ponytail` profile always emits `ponytail_reviewed: true` and a numeric `ponytail_findings` count; a report for an unselected profile omits both. Ponytail findings use these same gates. Required profiles by changed path: see **Review Profiles** in `workspace.instructions.md`.
