---
name: 2026-08-09_phase-A-graphify-managed-dependency-and-thin-adapter
type: small-plan
parent_plan: graphify-structural-code-intelligence
phase_index: 1
status: cancelled
cancelled_at: 2026-08-11T07:37:06Z
cancelled_reason: Phase 0 returned NO-GO because measured value did not justify bootstrap integration
cancelled_evidence: .claude/explorations/2026-08-09_graphify-compatibility-value-gate/evidence.md
closeout_session_log:
---

# Small Plan: 2026-08-09_phase-A-graphify-managed-dependency-and-thin-adapter

## Scope

Proceed only when Phase 0 records `Decision: GO`. Pin
`graphifyy==0.9.35` in the managed devcontainer and add the smallest isolated
standard-library adapter needed to make the evidence-confirmed structural
operations safe and fail-open. The adapter delegates graph extraction,
refresh, and query semantics to Graphify; it does not parse or rewrite the raw
graph, maintain its own freshness database, infer freshness from Git HEAD, or
create a second state engine.

Raw output is provisional local data under the exact ignored workspace proved
by Phase 0; the expected name is `.claude/graphify-local/`, but the gate artifact
is authoritative. Do not add Graphify to a consumer project's dependencies or
lockfile. Missing Graphify outside the managed devcontainer must emit a concise
warning that names the direct-read/`rg`/Semble fallback and must not corrupt or
present stale graph output.

## Ownership

- `coder`: managed dependency pin, thin adapter, focused unit tests, and target
  validator assertions.
- `verifier`: package provenance/integrity/security evidence, focused and full
  verification, and optional managed-container smoke.
- `reviewer`: `code`, `architecture`, `security`, `tests`, `ponytail`, `config`,
  `documentation`, and `performance`.
- `documenter`: document the exact pin and upgrade re-gate contract in the
  canonical changed surface before score persistence; do not add broad user
  documentation before retention.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` in `full` mode
- `.claude/skills/add-dependency/SKILL.md`
- `.claude/skills/integration-gate-spike/SKILL.md`
- `.claude/skills/testing-patterns/SKILL.md`

## Review Profiles

- `code`
- `architecture`
- `security`
- `tests`
- `ponytail`
- `config`
- `documentation`
- `performance`

## Steps

### 1. Reconfirm GO and package provenance

- **Owner:** verifier
- **Files:** read Phase 0 evidence; create a dated dependency provenance report
  under `.claude/quality_reports/`.
- **Required Skills:** `.claude/skills/add-dependency/SKILL.md`,
  `.claude/skills/integration-gate-spike/SKILL.md`.
- **Review Profiles:** `security`, `documentation`.
- **Contract:** refuse to continue unless the gate artifact contains GO and a
  complete exact CLI table. Record the PyPI distribution/project origin,
  upstream source and release/tag association, declared license and included
  license file, artifact filename and SHA-256 digest, installed version,
  transitive dependency inventory, `uv pip check` result, and an advisory scan
  for the resolved environment. Record gaps as blockers rather than inventing
  provenance. The explicit upgrade procedure is: choose one new exact version,
  rerun Phase 0 in full, repeat provenance/license/digest/advisory checks, update
  the pin and validator together, regenerate all targets, then rerun dogfood.
- **Verification:** `uv pip index versions graphifyy` and the exact ephemeral
  install/audit commands supported in the managed environment; compare the
  installed distribution metadata and digest with the acquired artifact.

### 2. Pin Graphify in the managed devcontainer

- **Owner:** coder
- **Files:** modify `shared/devcontainer/Dockerfile`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/add-dependency/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `config`,
  `ponytail`.
- **Contract:** add exactly `graphifyy==0.9.35` to the existing managed Python
  tooling install without changing project dependency files. Verify the
  gate-confirmed executable, exact reported version, and a harmless help
  operation during image build. Keep Semble, context-mode, Hugging Face tooling,
  user switching, and cache behavior unchanged. Add a short comment that any
  version change requires the full compatibility/value/security re-gate.
- **Must not:** install extras for MCP or LLM use; run Graphify installers or
  hooks; add a floating range; invoke project `uv add`; hand-edit a lockfile.
- **Verification:** regenerate, run target validation, inspect the generated
  `dist/multi-agent/.devcontainer/Dockerfile`, and build the image when Docker
  is available.

### 3. Add the thinnest evidence-backed adapter

- **Owner:** coder
- **Files:** create **new**
  `shared/scripts/graphify_structural.py`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/integration-gate-spike/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `performance`,
  `ponytail`.
- **Contract:** provide one public entry point
  `main(argv: Sequence[str] | None = None) -> int`. Expose only the normalized
  structural operations that Phase 0 proved necessary; expected operations are
  `query`, `explain`, and `path`, but the evidence table decides their exact
  operands and raw Graphify mapping. Resolve the repository root and one local
  output directory, invoke Graphify with argument lists and `shell=False`, and
  pass through bounded useful output. Before a query, use only Graphify's
  evidence-confirmed current-worktree/update contract. If Graphify already
  refreshes as part of a query, do not add a second refresh.
- **Failure contract:** missing executable, wrong version, unsupported
  repository, graph-missing, corrupt graph, refresh failure, and query failure
  print one actionable `WARN` to stderr, return a stable non-zero adapter code,
  never run a query against known-stale data, and leave source files untouched.
  Agent routing later treats this as fallback, not task failure.
- **Must not:** add classes or a state manifest unless the gate proves one is
  unavoidable; call Git to decide freshness; parse or normalize `graph.json`;
  use a shell; add network, hooks, MCP, install, save, reflect, or LLM behavior;
  add diagnostics beyond what query safety needs (Phase E owns diagnostics).
- **Verification:** run focused unit tests with a fake executable and one
  gate-confirmed smoke in the managed environment.

### 4. Add behavior-first tests

- **Owner:** coder
- **Files:** create **new** `tests/test_graphify_structural.py`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `code`, `security`, `tests`, `performance`, `ponytail`.
- **Contract:** use `tmp_path` and a fake Graphify executable. Cover repository
  root and output resolution, exact pinned-version rejection, first-use and
  evidence-confirmed refresh ordering, dirty-worktree operation without a
  HEAD-only shortcut, normalized query/explain/path mapping, argv safety for
  spaces and shell metacharacters, stdout/stderr boundaries, missing binary,
  corrupt/missing graph, failed refresh short-circuit, no stale query, and no
  source writes. Assert subprocess argv and call order. Unit tests must not
  download or import Graphify.
- **Verification:**
  `uv run pytest tests/test_graphify_structural.py -q --tb=short`.

### 5. Encode pin and prohibition regressions

- **Owner:** coder
- **Files:** modify `scripts/validate_targets.py`; modify
  `tests/test_validate_targets.py` only when a focused public validator helper
  needs regression coverage.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `config`,
  `ponytail`.
- **Contract:** require the exact Dockerfile pin and evidence-confirmed harmless
  build checks. Reject floating pins, `graphifyy[mcp]`, Graphify install/hook/MCP
  commands, LLM features, and tracked raw graph artifacts. Do not yet require a
  generated adapter; Phase C owns projection and generated-surface assertions.
  Extend the existing devcontainer validator instead of adding a parallel
  validation framework.
- **Verification:**
  `uv run pytest tests/test_validate_targets.py -q --tb=short` followed by
  `uv run python scripts/generate_targets.py --all` and
  `uv run python scripts/validate_targets.py`.

### 6. Review, document narrowly, score, and close the phase

- **Owner:** reviewer, documenter, verifier, orchestrator
- **Files:** changed Phase A files; provenance report; canonical narrow comments
  or existing documentation only where the phase exposes an operating contract.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/documentation/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `ponytail`,
  `config`, `documentation`, `performance`.
- **Contract:** review implementation first, resolve findings, then update
  documentation, persist converged findings and score against final code+docs,
  run LEARN/session closeout, and create one atomic Phase A commit. Do not
  advertise Graphify as retained before Phase D.
- **Verification:** run the full command block below after documentation settles.

## Dependencies and Risks

- Hard dependency: Phase 0 GO and its exact contract table. NO-GO blocks this
  phase.
- The raw CLI may already provide all safe behavior. In that case, keep the
  adapter as a minimal availability/argv boundary; do not recreate lifecycle
  logic.
- If correctness requires parsing or rewriting Graphify's raw state, stop and
  amend the plan. A custom state engine is not authorized by default.
- The Docker build may be unavailable locally. Static and unit verification
  still run, but managed-image execution remains an explicit unmet acceptance
  item rather than a silent pass.
- Changes are control-plane and multi-file; the complete phase review is
  mandatory and uses ordinary severity gates.

## Verification

```bash
uv run pytest tests/test_graphify_structural.py tests/test_validate_targets.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ shared/scripts/ tests/
uv run ruff format --check scripts/ shared/scripts/ tests/
git diff --check
uv run python .claude/scripts/record_findings.py . --profile code --profile architecture --profile security --profile tests --profile ponytail --profile config --profile documentation --profile performance --phase 2026-08-09_phase-A-graphify-managed-dependency-and-thin-adapter --base-ref dev --findings-json <reviewer-findings.json> --out .claude/quality_reports/findings-<timestamp>.json
uv run python .claude/scripts/quality_score.py . --phase 2026-08-09_phase-A-graphify-managed-dependency-and-thin-adapter --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

When Docker is available, additionally build the generated managed devcontainer
and run the evidence-confirmed version/help and adapter smoke commands inside it.

## Acceptance Criteria

- [ ] Phase 0 GO and exact raw CLI contract are cited.
- [ ] `graphifyy==0.9.35` is exact and isolated to the managed devcontainer.
- [ ] Provenance, license, artifact digest, dependencies, compatibility, and advisory results are recorded.
- [ ] The upgrade procedure requires the full compatibility/value/security re-gate.
- [ ] The adapter contains only evidence-backed argv and fallback behavior.
- [ ] Current-worktree freshness delegates to Graphify and never relies only on Git HEAD.
- [ ] Missing/failed Graphify warns and cleanly enables direct-read/`rg`/Semble fallback.
- [ ] No installer, hook, MCP, LLM, platform ownership, or raw graph persistence is introduced.
- [ ] Focused and full verification pass.
- [ ] One atomic Phase A commit follows documentation, score, LEARN, and session closeout.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
