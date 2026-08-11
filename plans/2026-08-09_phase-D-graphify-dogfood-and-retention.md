---
name: 2026-08-09_phase-D-graphify-dogfood-and-retention
type: small-plan
parent_plan: graphify-structural-code-intelligence
phase_index: 4
status: cancelled
cancelled_at: 2026-08-11T07:37:06Z
cancelled_reason: Phase 0 returned NO-GO because measured value did not justify bootstrap integration
cancelled_evidence: .claude/explorations/2026-08-09_graphify-compatibility-value-gate/evidence.md
closeout_session_log:
---

# Small Plan: 2026-08-09_phase-D-graphify-dogfood-and-retention

## Scope

Exercise the generated Graphify capability through real bootstrap planning,
review, generation, installation, local-state, and fallback workflows. Then make
one explicit `RETAIN` or `REMOVE` decision before adding diagnostics or any
cross-session persistence. This is a test of operational usefulness and
correctness for this bootstrap, not a claim that Graphify is generally better
than Semble or `rg`.

Retention requires source-confirmed usefulness, current-worktree freshness,
acceptable cold/warm/no-op latency, bounded local size and churn, privacy and
ignore compliance, deterministic generation/reinstall, selective routing, and
clean fallback. If any mandatory criterion fails, remove the dependency,
adapter, Graphify-specific routing/guidance, generation/ownership changes, and
tests in one reviewed Phase D change while keeping dated evidence. Do not keep
the dependency by default because infrastructure has already been built.

## Ownership

- `coder`: prepare controlled dogfood fixtures; make only evidence-backed fixes
  or the clean removal required by the decision.
- `verifier`: reproduce the end-to-end matrix and measurements in managed and
  missing-tool environments.
- `reviewer`: run `code`, `architecture`, `security`, `tests`, `ponytail`,
  `config`, `documentation`, and `performance`; independently source-check the
  structural evidence.
- `documenter`: after review converges, document the retained operating
  contract or confirm current docs contain no removed capability.
- `orchestrator`: run the Planner/Reviewer handoff scenarios and record the
  final retention decision.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` in `full` mode for any code or policy change
- `.claude/skills/integration-gate-spike/SKILL.md`
- `.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md`
- `.claude/skills/testing-patterns/SKILL.md`
- `.claude/skills/documentation/SKILL.md`

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

### 1. Freeze a reproducible dogfood matrix

- **Owner:** verifier
- **Files:** create **new**
  `.claude/explorations/2026-08-09_graphify-dogfood-and-retention/evidence.md`;
  use temporary consumer repositories outside the workspace.
- **Required Skills:** `.claude/skills/integration-gate-spike/SKILL.md`,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `architecture`, `security`, `tests`, `performance`.
- **Contract:** record current implementation commit, Phase 0 evidence hash,
  exact Graphify version, generated target hash, fixture hashes, environment,
  cache state, and commands. Include managed Graphify, Graphify absent from
  `PATH`, clean consumer, existing consumer, dirty working tree, rename/delete,
  branch switch, corrupt/missing local graph, reinstall, and local-only state
  sync. No test may modify real consumer source or remote state.
- **Verification:** generate the bundle, validate it, install into a temporary
  Git repository, and confirm a clean baseline before Graphify runs.

### 2. Exercise the installed structural adapter

- **Owner:** verifier
- **Files:** temporary consumer and dogfood evidence only unless a defect needs
  an approved minimal fix.
- **Required Skills:** `.claude/skills/integration-gate-spike/SKILL.md`,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `code`, `security`, `tests`, `performance`.
- **Contract:** run every normalized adapter operation from the generated
  `.claude/scripts/graphify_structural.py`. Verify first-use, warm query, no-op,
  uncommitted call/import change, rename, deletion, source revert, branch A to B
  to A, graph corruption, graph removal, and version mismatch. A query must
  reflect the current worktree or fail explicitly; it must never return known-
  stale output as current.
- **Privacy/ignore:** execute source operations network-denied, inventory writes,
  and confirm raw output is only under the local root. Prove `.claude/`,
  `dist/`, ignored secrets, and non-code fixture content are absent without
  `--no-gitignore`.
- **Verification:** compare every material result with direct source reads and
  exact `rg` matches.

### 3. Repeat the three real structural-value comparisons

- **Owner:** coder and verifier
- **Files:** read repository source; append evidence only.
- **Required Skills:** `.claude/skills/integration-gate-spike/SKILL.md`.
- **Review Profiles:** `architecture`, `tests`, `performance`.
- **Contract:** run the Phase 0 questions through the installed adapter:
  `sync_state_after_install` callers/lifecycle, `render_shared_basis`
  generation-to-install path, and `CONSUMER_STATE_PATHS` ownership consumers.
  Compare with direct reads, `rg`, and Semble when available. Record files,
  relationships, omissions, ambiguous/false leads, source confirmations, and
  elapsed time. At least two questions must still add structural connectivity
  value beyond baseline after wrapper/routing overhead.
- **Verification:** Reviewer independently opens every cited source location;
  output wording and exact node counts are not acceptance criteria.

### 4. Dogfood Planner selection

- **Owner:** orchestrator
- **Files:** evidence only; use the generated Planner prompt and a bounded
  fixture request.
- **Required Skills:** `.claude/skills/integration-gate-spike/SKILL.md`.
- **Review Profiles:** `architecture`, `tests`, `documentation`, `performance`.
- **Contract:** run one full-plan scenario involving a shared interface with
  non-obvious consumers and one eligible micro-plan control. Full Planner must
  identify anchors with normal retrieval, invoke Graphify only for the concrete
  structural gap, confirm important edges in source, and record only material
  structural impact. Micro Planner must not call Graphify when its scope is
  already clear. Record tool calls, unique files, duplicated discovery, output
  volume, and whether Graphify changed scope or ordering.
- **Verification:** compare both plans with a direct-read/`rg`/Semble control;
  reject blind graph dumps or unsupported structural assumptions.

### 5. Dogfood Orchestrator-to-Reviewer evidence

- **Owner:** orchestrator and reviewer
- **Files:** evidence only; use a controlled diff fixture with one non-obvious
  real consumer and one intentionally ambiguous/non-edge candidate.
- **Required Skills:** `.claude/skills/integration-gate-spike/SKILL.md`.
- **Review Profiles:** `architecture`, `security`, `tests`, `documentation`.
- **Contract:** Orchestrator identifies anchors, runs targeted adapter queries,
  and passes only the compact evidence packet. Reviewer remains non-executing,
  reads each candidate, accepts the real source-confirmed issue if one exists,
  drops the ambiguous candidate, and completes its normal primary/adversarial
  convergence. Missing Graphify control must still complete review through
  ordinary retrieval.
- **Verification:** inspect native/generated capability metadata and reviewer
  output; a finding citing Graphify without source is a retention failure.

### 6. Prove reinstall, state, and client-context isolation

- **Owner:** verifier
- **Files:** temporary consumers and evidence only unless a minimal regression
  fix is required.
- **Required Skills:** `.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md`,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `architecture`, `security`, `tests`, `config`,
  `performance`.
- **Contract:** with raw graph output present, reinstall the generated bundle
  and confirm raw local bytes, consumer state, tracked authoring adapters, and
  generated refreshes. Run nested checkpoint/push fixtures and prove raw graph
  files remain ignored and remote refs contain none. Parse Trace2 for local-only
  no-remote-I/O. Inspect supported client context/debug evidence to determine
  whether the ignored raw directory is still swept into routine Claude,
  Copilot, or Codex context; if this cannot be measured, record it as an
  explicit uncertainty in the retention decision rather than inventing an
  ignore convention.
- **Verification:** focused installer/state-sync tests, target validator, nested
  `git status --short`, `git check-ignore -v`, remote tree inspection, and
  client evidence where available.

### 7. Measure integrated cost and decide RETAIN or REMOVE

- **Owner:** verifier, reviewer, orchestrator
- **Files:** finalize dogfood evidence; if REMOVE, modify/delete every
  Graphify-specific tracked file from Phases A-C and update their tests/docs.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode for any
  code/policy change, `.claude/skills/integration-gate-spike/SKILL.md`,
  `.claude/skills/documentation/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `ponytail`,
  `config`, `documentation`, `performance`.
- **RETAIN contract:** all of these pass: exact version/provenance remains
  acceptable; all freshness/rename/delete/branch tests pass; at least two of
  three questions add source-confirmed structural value; zero known material
  false relationships are accepted; Planner and Reviewer routing is selective
  and source-grounded; fallback is clean; network/ignore/privacy boundaries
  hold; deterministic generation/reinstall/state tests pass; cold median
  `<= 180 s`, warm changed-source median `<= 30 s`, no-op median `<= 10 s`, raw
  output `<= 50 MiB`, and no-op has no semantic graph change or unexplained
  rewrite above `1%` of graph bytes. Client-context uncertainty must be judged
  explicitly and cannot be silently ignored.
- **REMOVE contract:** if any mandatory criterion fails, remove the Docker pin,
  adapter, skill/routing/agent additions, generator projection, local output
  ownership/ignore additions, and Graphify-specific validators/tests/docs.
  Regenerate and prove the pre-Graphify workflow remains green. Keep only dated
  exploration/lifecycle evidence in nested AI state. Do not proceed to E or F.
- **Verification:** evidence states exactly `Decision: RETAIN` or
  `Decision: REMOVE`, with each criterion PASS/FAIL and source/command links.

### 8. Review, document after the decision, score, and close

- **Owner:** reviewer, documenter, verifier, orchestrator
- **Files if RETAIN:** modify applicable sections of `README.md`,
  `docs/architecture.md`, `docs/runtime-checks.md`, `docs/smoke-tests.md`, and
  `docs/target-mapping.md`; keep `shared/policies/tool-routing.instructions.md`
  and `shared/skills/graphify-code-graph/SKILL.md` aligned with measured
  behavior. **Files if REMOVE:** ensure current docs and canonical sources
  contain no active Graphify contract.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode for
  implementation changes, `.claude/skills/documentation/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `ponytail`,
  `config`, `documentation`, `performance`.
- **Contract:** converge implementation/decision review first. Document only the
  final retained or removed state. Then persist findings and score against final
  code+docs, complete LEARN/session log, and create one atomic Phase D commit.
  Do not add Graphify diagnostics in this phase; Phase E is gated on RETAIN.
- **Verification:** run the complete command block after final docs settle.

## Dependencies and Risks

- Depends on completed Phases 0-C and an executable generated managed target.
- Native client context evidence may be unavailable. Record the exact gap; do
  not assert prompt-cache isolation from `.gitignore` alone.
- Dogfood can expose defects. Apply only the smallest root-cause fix under the
  full review set and rerun the whole affected scenario.
- Prior implementation cost creates retention bias. The checklist is binary;
  mandatory failures produce REMOVE.
- REMOVE is broad but recoverable in Git. It must be one coherent atomic phase
  change with full regression coverage, not partial dead guidance.

## Verification

```bash
uv run pytest tests/test_graphify_structural.py tests/test_install_bootstrap.py tests/test_state_sync.py tests/test_validate_targets.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/install_bootstrap.py . --allow-self --local-only
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ shared/scripts/ tests/
uv run ruff format --check scripts/ shared/scripts/ tests/
git diff --check
uv run python .claude/scripts/record_findings.py . --profile code --profile architecture --profile security --profile tests --profile ponytail --profile config --profile documentation --profile performance --phase 2026-08-09_phase-D-graphify-dogfood-and-retention --base-ref dev --findings-json <reviewer-findings.json> --out .claude/quality_reports/findings-<timestamp>.json
uv run python .claude/scripts/quality_score.py . --phase 2026-08-09_phase-D-graphify-dogfood-and-retention --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

Managed-environment smoke uses the Phase 0-confirmed raw CLI and the generated
adapter operations. Missing-tool smoke removes Graphify from `PATH` and must
still complete the normal retrieval/planning/review controls.

## Acceptance Criteria

- [ ] The installed adapter passes clean, dirty, rename/delete, branch, corruption, missing, and version-mismatch scenarios.
- [ ] Three real questions remain source-confirmed and at least two add structural value.
- [ ] Full-plan selection is useful; the clear micro-plan control does not call Graphify.
- [ ] Orchestrator passes compact evidence and Reviewer confirms source without execute capability.
- [ ] Reinstall preserves local output, consumer state, and authoring adapters; nested state never syncs raw graph data.
- [ ] Privacy, ignored-source, context-isolation evidence, latency, size, and churn are explicit.
- [ ] Fallback continues through direct reads, `rg`, and Semble without stale output.
- [ ] The decision is exactly RETAIN or REMOVE and every mandatory criterion is accounted for.
- [ ] Diagnostics and compact persistence have not been added early.
- [ ] One atomic Phase D commit follows final documentation, score, LEARN, and session closeout.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
