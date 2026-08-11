---
name: 2026-08-09_phase-F-graphify-optional-persistence-gate
type: small-plan
parent_plan: graphify-structural-code-intelligence
phase_index: 6
status: cancelled
cancelled_at: 2026-08-11T07:37:06Z
cancelled_reason: Phase 0 returned NO-GO because measured value did not justify bootstrap integration
cancelled_evidence: .claude/explorations/2026-08-09_graphify-compatibility-value-gate/evidence.md
closeout_session_log:
---

# Small Plan: 2026-08-09_phase-F-graphify-optional-persistence-gate

## Scope

Run an independently skippable persistence gate only after Phase D RETAIN and
Phase E diagnostics. The default decision is `SKIP`: raw Graphify output stays
under the ignored consumer-local directory and `graph.json` is never
synchronized. `PERSIST` requires measured cross-session benefit, an available
Graphify-native compact/report output that does not require parsing raw graph
internals, explicit user approval to synchronize structural metadata, and
accepted privacy, size, churn, staleness, and multi-writer risks.

If approved, persist only a bounded compact report and manifest under the
already consumer-owned `.claude/quality_reports/graphify/<source-head>/`
namespace. Persist only clean-commit snapshots. The manifest marks the exact
source commit and Graphify version; any mismatch makes the report stale
navigation evidence. Source reads remain mandatory. A SKIP decision produces
dated nested-state evidence and no tracked implementation change or empty outer
commit.

## Ownership

- `orchestrator`: request the explicit persistence approval only after all gate
  evidence passes; otherwise record SKIP.
- `coder`: only for PERSIST, add the minimum native-report copy/manifest logic
  and focused regressions.
- `verifier`: prove privacy allowlist, size/churn bounds, staleness, reinstall,
  state sync, and fallback.
- `reviewer`: for PERSIST use `code`, `architecture`, `security`, `tests`,
  `ponytail`, `config`, `documentation`, and `performance`; for SKIP review the
  decision evidence with `architecture`, `security`, `tests`, `documentation`,
  and `performance`.
- `documenter`: document only the final SKIP or PERSIST contract after review.

## Required Skills

- `.claude/skills/integration-gate-spike/SKILL.md`
- `.claude/skills/ponytail/SKILL.md` in `full` mode for PERSIST code changes
- `.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md`
- `.claude/skills/testing-patterns/SKILL.md`
- `.claude/skills/documentation/SKILL.md`

## Review Profiles

- `code` when PERSIST writes code
- `architecture`
- `security`
- `tests`
- `ponytail` when PERSIST writes code
- `config` when PERSIST changes generated/runtime behavior
- `documentation`
- `performance`

## Steps

### 1. Prove cross-session benefit before asking for approval

- **Owner:** verifier and orchestrator
- **Files:** create **new**
  `.claude/explorations/2026-08-09_graphify-persistence-gate/evidence.md`; read
  Phase D evidence and existing nested-state behavior.
- **Required Skills:** `.claude/skills/integration-gate-spike/SKILL.md`,
  `.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md`.
- **Review Profiles:** `architecture`, `security`, `tests`, `documentation`,
  `performance`.
- **Contract:** compare two fresh sessions/machines or equivalent isolated
  consumers: one with only local raw graph regeneration and one supplied a
  compact native report. Measure whether the report reduces repeated structural
  discovery while preserving source verification. Record time, tool calls,
  context bytes, useful confirmed relationships, stale/misleading leads, merge
  behavior, and sync overhead. No benefit is presumed from the existence of a
  report.
- **Gate:** if the report does not materially reduce repeated structural work,
  or if Graphify cannot emit a compact source-safe report without a raw-graph
  parser/custom state engine, decide SKIP immediately.
- **Verification:** use identical bounded tasks and confirm every report-derived
  lead in source.

### 2. Apply privacy, size, churn, and staleness gates

- **Owner:** verifier and reviewer
- **Files:** append results to the persistence evidence only.
- **Required Skills:** `.claude/skills/integration-gate-spike/SKILL.md`.
- **Review Profiles:** `architecture`, `security`, `tests`, `documentation`,
  `performance`.
- **Contract:** candidate persisted content may contain only relative source
  paths, symbol names, relationship types, confidence labels, source citations,
  Graphify version, source commit, schema version, report digest, and generation
  timestamp. It must not contain source bodies/snippets, secret values, ignored
  paths, absolute paths, usernames/home paths, environment variables, raw graph
  nodes/JSON, cache data, LLM content, or credentials. Require:
  - clean source worktree; dirty snapshots are refused;
  - path `.claude/quality_reports/graphify/<40-hex-source-head>/`;
  - one `manifest.json` plus one `report.md` per accepted source commit;
  - combined pair size `<= 256 KiB`;
  - identical semantic input at the same commit produces byte-identical files
    and no nested Git diff;
  - source HEAD or Graphify version mismatch reports STALE and prevents the
    artifact from being presented as current;
  - raw local output remains ignored and never enters the nested commit.
- **Gate:** any privacy allowlist violation, unstable no-op output, ambiguous
  staleness, unbounded size, or unacceptable multi-writer conflict produces
  SKIP.
- **Verification:** scan candidate bytes, inspect nested diffs and commits,
  switch commits/versions, and test two writers with existing state-sync
  behavior.

### 3. Obtain explicit PERSIST approval or record default SKIP

- **Owner:** orchestrator
- **Files:** finalize the persistence evidence; no tracked file change for SKIP.
- **Required Skills:** `.claude/skills/integration-gate-spike/SKILL.md`.
- **Review Profiles:** `architecture`, `security`, `documentation`,
  `performance`.
- **Contract:** summarize measured benefit and the accepted residual privacy,
  metadata-sharing, staleness, size, churn, and conflict risks. Ask for explicit
  user approval to synchronize the bounded structural metadata. Missing or
  declined approval is `Decision: SKIP`. Approval is `Decision: PERSIST` and
  authorizes only Steps 4-7 below; it does not authorize raw graph persistence
  or Graphify-owned state sync.
- **Verification:** the evidence records exact decision, approver response,
  accepted schema/paths/budgets, and rejected alternatives.

### 4. If PERSIST, add a compact snapshot operation

- **Owner:** coder
- **Files:** modify `shared/scripts/graphify_structural.py`; modify
  `tests/test_graphify_structural.py`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/testing-patterns/SKILL.md`,
  `.claude/skills/integration-gate-spike/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `ponytail`,
  `config`, `performance`.
- **Contract:** add normalized `snapshot` only around the Phase 0-confirmed
  native compact report command. Refuse dirty worktrees. Write through a
  temporary sibling then atomically replace only
  `.claude/quality_reports/graphify/<source-head>/manifest.json` and
  `report.md`. Validate the privacy allowlist and 256 KiB pair budget before
  replacement. The manifest contains exactly `schema_version`,
  `graphify_version`, `source_head`, `source_branch`, `generated_at`,
  `report_sha256`, and `report_bytes`. If existing bytes are identical, do not
  rewrite. Add a read/status operation that returns CURRENT only when source
  HEAD and Graphify version match; otherwise return STALE with no current-report
  claim.
- **Must not:** read/parse/rewrite `graph.json`; persist dirty-tree graphs;
  persist source bodies or absolute paths; delete older snapshots; add a merge
  driver; change state-sync; treat the report as source authority.
- **Verification:** tests cover clean/dirty, allowed/forbidden content, size
  boundary, atomic failure, identical no-op, HEAD/version staleness, hash
  mismatch, symlink/path escape, and raw graph exclusion.

### 5. If PERSIST, test generic install and nested sync

- **Owner:** coder and verifier
- **Files:** modify `tests/test_install_bootstrap.py` and
  `tests/test_state_sync.py` only as needed; installer/state-sync implementation
  should remain unchanged because `quality_reports` is already consumer state.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md`,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `ponytail`,
  `performance`.
- **Contract:** prove reinstall preserves compact artifacts byte-for-byte and
  still preserves every other consumer state/root adapter. Prove nested sync
  commits only the compact pair, never local raw graph data. Exercise local-only
  Trace2 no-remote-I/O and two-writer conflict behavior. Prefer existing generic
  `quality_reports` ownership; do not add a Graphify installer branch.
- **Verification:** focused installer/state-sync tests and generated validation.

### 6. If PERSIST, generate and validate the bounded contract

- **Owner:** coder
- **Files:** modify `scripts/validate_targets.py` and
  `tests/test_validate_targets.py`; generation code should need no new copy
  path because the adapter is already projected.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `config`,
  `documentation`, `performance`, `ponytail`.
- **Contract:** require the exact compact paths/schema/size/staleness/privacy
  contract, source verification, and raw graph prohibition. Reject any
  generated seed report, `graph.json` synchronization, custom raw parser,
  Graphify hook/MCP/installer, or report-as-authority language. Generate all
  three clients and confirm identical adapter behavior.
- **Verification:** focused validator tests, generation twice, target
  validation, default and strict runtime diagnostics, and full tests.

### 7. Review, document the final decision, score, and close

- **Owner:** reviewer, documenter, verifier, orchestrator
- **Files if PERSIST:** all changed Phase F files plus applicable Graphify
  sections in `README.md`, `docs/architecture.md`, `docs/runtime-checks.md`,
  `docs/smoke-tests.md`, `shared/skills/graphify-code-graph/SKILL.md`, and
  `shared/policies/tool-routing.instructions.md`. **Files if SKIP:** persistence
  evidence and lifecycle state only; retained docs must continue to say raw
  output is local and ignored.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode for
  PERSIST code, `.claude/skills/documentation/SKILL.md`.
- **Review Profiles:** PERSIST uses `code`, `architecture`, `security`, `tests`,
  `ponytail`, `config`, `documentation`, `performance`; SKIP uses
  `architecture`, `security`, `tests`, `documentation`, `performance`.
- **Contract:** review implementation or decision evidence, then update docs,
  persist findings and score against final content, complete LEARN/session log,
  and close atomically. PERSIST creates one atomic outer Phase F commit. SKIP
  creates one atomic nested AI-state checkpoint and no empty outer commit.
- **Verification:** PERSIST runs the full block below; SKIP runs all read-only
  verification applicable to the unchanged retained integration and records
  the reason implementation commands were not needed.

## Dependencies and Risks

- Hard dependencies: Phase D RETAIN, Phase E diagnostics, measurable
  cross-session benefit, all safety gates, and explicit approval.
- The default is SKIP. Ambiguous benefit or risk never rounds up to persistence.
- Structural metadata can reveal architecture even without source bodies. User
  approval must cover synchronization to the configured AI-state remote.
- Per-commit paths avoid stale overwrite but may accumulate. Automatic deletion
  is out of scope; approve only the first bounded snapshot contract, then
  reassess real growth before adding retention policy.
- A native compact report may not exist. Do not implement a raw graph parser to
  manufacture one; record SKIP.

## Verification

For PERSIST:

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
uv run python .claude/scripts/record_findings.py . --profile code --profile architecture --profile security --profile tests --profile ponytail --profile config --profile documentation --profile performance --phase 2026-08-09_phase-F-graphify-optional-persistence-gate --base-ref dev --findings-json <reviewer-findings.json> --out .claude/quality_reports/findings-<timestamp>.json
uv run python .claude/scripts/quality_score.py . --phase 2026-08-09_phase-F-graphify-optional-persistence-gate --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

For SKIP, run generation, target validation, runtime checks, full tests, typing,
lint, format, plan validation, and evidence review without changing tracked
implementation files.

## Acceptance Criteria

- [ ] Cross-session benefit is measured rather than assumed.
- [ ] The decision is exactly SKIP or explicitly approved PERSIST.
- [ ] SKIP leaves raw output local/ignored and adds no tracked implementation change.
- [ ] PERSIST is impossible without clean source state and a native compact report.
- [ ] Persisted content contains only the approved metadata/relationship allowlist.
- [ ] One compact pair is at most 256 KiB and identical no-op input creates no diff.
- [ ] HEAD/version mismatch is STALE; source verification remains mandatory.
- [ ] `graph.json`, source bodies, ignored paths, absolute paths, secrets, caches, hooks, MCP, and installers are never persisted.
- [ ] Reinstall/state sync preserve compact reports without syncing raw graph output.
- [ ] Final docs match SKIP or PERSIST and closeout is atomic for the chosen path.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
