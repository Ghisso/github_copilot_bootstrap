---
name: 2026-08-09_phase-0-graphify-compatibility-and-value-gate
type: small-plan
parent_plan: graphify-structural-code-intelligence
phase_index: 0
status: complete
closeout_session_log: 2026-08-09_graphify-phase-0-cross-project-supplement
---

# Small Plan: 2026-08-09_phase-0-graphify-compatibility-and-value-gate

## Scope

Run a disposable compatibility-and-value gate for exactly
`graphifyy==0.9.35` before any runtime, adapter, routing, state, dependency, or
tracked repository change. Use temporary fixtures and an ephemeral package
environment. The only task-specific durable artifact is **new**
`.claude/explorations/2026-08-09_graphify-compatibility-value-gate/evidence.md`;
mandatory plan, review, score, and session lifecycle artifacts remain under the
nested `.claude/` state repository.

This phase must not edit `shared/`, `scripts/`, `tests/`, `.devcontainer/`,
root adapters, generated output, a dependency file, or the outer repository's
Git configuration. Exact Graphify argv, outputs, emitted files, exit codes, and
update semantics are unverified until this phase records them. A NO-GO result
stops Phases A-F; it does not justify another Graphify version, a custom state
engine, or a tracked workaround.

The initial bootstrap-only experiment returned NO-GO. Before closeout, the
user authorized one supplementary read-only applicability test against two
refreshed consumer projects: `/home/ghisso/work/RAG` and
`/home/ghisso/work/git_projects/industrial-inspection`. Preserve the original
result as a separate record. The supplement may change the final adoption
decision only through the explicit cross-project override in Step 7; it must
not weaken or rewrite the original measurements and limitations.

## Ownership

- `coder`: execute only the disposable experiment and write the single gate
  evidence artifact; no implementation code.
- `verifier`: reproduce the measurements and verify the write allowlist and
  network/privacy boundaries.
- `reviewer`: inspect the evidence with `architecture`, `security`, `tests`,
  `documentation`, and `performance` profiles.
- `documenter`: skipped for tracked docs; the gate artifact itself is the
  dated documentation.
- `orchestrator`: record GO/NO-GO, lifecycle evidence, and the atomic nested
  AI-state checkpoint. Do not create an empty outer commit.

## Required Skills

- `.claude/skills/integration-gate-spike/SKILL.md`
- `.claude/skills/add-dependency/SKILL.md`
- `.claude/skills/testing-patterns/SKILL.md`

Ponytail does not apply because this phase writes no code. If execution reveals
that code is needed to run the gate, stop and amend the plan instead of adding
it here.

## Review Profiles

- `architecture`
- `security`
- `tests`
- `documentation`
- `performance`

## Steps

### 1. Freeze the experiment boundary

- **Owner:** coder
- **Files:** create only
  `.claude/explorations/2026-08-09_graphify-compatibility-value-gate/evidence.md`;
  temporary repositories live outside the workspace and are deleted after
  evidence capture.
- **Required Skills:**
  `.claude/skills/integration-gate-spike/SKILL.md`,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `architecture`, `security`, `tests`.
- **Contract:** record the outer `git status --short`, current HEAD, candidate
  version, host/container facts, temporary directory, Graphify cache location,
  test fixture hashes, and exact commands before execution. Capture a final
  path allowlist showing that no tracked workspace file changed. Package
  download/cache writes are allowed only outside the repository.
- **Verification:** `git status --short` before and after; compare
  `git diff --name-only` and `git diff --cached --name-only`; inspect untracked
  paths explicitly.

### 2. Verify the pinned package and exact CLI contract

- **Owner:** coder
- **Files:** append results to the gate evidence only.
- **Required Skills:** `.claude/skills/add-dependency/SKILL.md`,
  `.claude/skills/integration-gate-spike/SKILL.md`.
- **Review Profiles:** `security`, `tests`.
- **Contract:** acquire only `graphifyy==0.9.35` through an ephemeral `uvx` or
  temporary uv environment. Confirm the distribution name, executable name,
  reported version, top-level help, exact code-only extraction command, query
  operations, output selection, update/refresh operation, exit codes, stdout
  versus stderr behavior, graph-missing behavior, and emitted filenames. Copy
  exact help excerpts only as needed; do not infer undocumented flags. Never
  run any installer, hook installer, platform installer, MCP mode,
  `--no-gitignore`, save/reflect/memory feature, or LLM backend.
- **Verification:** start with
  `uvx --from graphifyy==0.9.35 graphify --version` and gate-confirmed `--help`
  discovery. Record every later argv literally. If the candidate executable or
  exact version cannot be confirmed, declare NO-GO.

### 3. Prove code-only, ignore, update, and fallback behavior

- **Owner:** coder
- **Files:** temporary fixture repositories and gate evidence only.
- **Required Skills:** `.claude/skills/integration-gate-spike/SKILL.md`,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `architecture`, `security`, `tests`, `performance`.
- **Contract:** create a fixture with calls, imports, inheritance, a rename, a
  deletion, unsupported/non-code content, ignored secrets, `.claude/`, and
  `dist/`. Exercise cold extraction, a warm query, a dirty uncommitted update,
  rename/delete update, branch switch, and no-op update. Prove ignored content,
  `.claude/`, and `dist/` are not indexed and never use `--no-gitignore`.
  Corrupt or remove the graph, then remove Graphify from `PATH`; record exact
  failure output and confirm direct reads/`rg` remain usable without stale
  Graphify output being presented as current.
- **Verification:** verify fixture truth with direct source reads and `rg`;
  use the exact gate-confirmed graph inspection/query commands; run
  `git check-ignore -v` for the ignored fixture paths.

### 4. Prove local privacy after package acquisition

- **Owner:** verifier
- **Files:** gate evidence only.
- **Required Skills:** `.claude/skills/integration-gate-spike/SKILL.md`.
- **Review Profiles:** `security`, `tests`.
- **Contract:** after the pinned package is locally available, repeat extraction,
  update, and all required query operations in a network-denied boundary such
  as a container with `--network none` or an equivalent verified namespace.
  Package acquisition is the only permitted network step. Confirm no Graphify
  source operation requires credentials, an LLM, remote APIs, or writes outside
  the fixture, declared output directory, and external package cache.
- **Verification:** the evidence must name the isolation mechanism, its own
  control check showing network is denied, Graphify exit codes, and the
  filesystem write inventory. An unavailable or unproven network-denied
  boundary is NO-GO, not an accepted assumption.

### 5. Compare three real structural questions

- **Owner:** coder
- **Files:** read repository source; append measurements and source citations to
  the gate evidence only.
- **Required Skills:** `.claude/skills/integration-gate-spike/SKILL.md`.
- **Review Profiles:** `architecture`, `tests`, `performance`.
- **Contract:** ask at least these repository questions through Graphify and
  compare the result with direct reads, `rg`, and Semble when available:
  1. What directly and transitively calls `sync_state_after_install`, and which
     installer lifecycle paths reach it?
  2. How does `render_shared_basis` flow into generated output, installation,
     and target validation?
  3. Which code consumes `CONSUMER_STATE_PATHS`, and how does that affect
     reinstall preservation and runtime drift checks?
  For each tool, record elapsed time, commands/queries, useful files and edges,
  missed relevant locations, false or ambiguous claims, and the source lines
  that confirm or refute every material Graphify result. Missing Semble is a
  recorded comparison limitation, not a Graphify advantage.
- **Verification:** direct reads are final authority. A question counts as
  added structural value only when Graphify exposes a correct relationship or
  path that is materially less direct to assemble from the baseline; file
  discovery alone does not count.

### 6. Measure budgets and issue the initial bootstrap decision

- **Owner:** verifier, then reviewer and orchestrator
- **Files:** finalize the gate evidence only.
- **Required Skills:** `.claude/skills/integration-gate-spike/SKILL.md`.
- **Review Profiles:** `architecture`, `security`, `tests`, `documentation`,
  `performance`.
- **Contract:** record cold build, warm changed-source refresh plus query, and
  no-op refresh plus query over three runs after one warm-up; report individual
  samples, median, output bytes/files, and byte/semantic churn. Use these
  working budgets:
  - cold build median `<= 180 s`;
  - warm changed-source refresh plus query median `<= 30 s`;
  - no-op refresh plus query median `<= 10 s`;
  - total raw output `<= 50 MiB` on this repository;
  - no-op produces no semantic graph change and no unexplained raw-output
    rewrite larger than `1%` of the graph bytes;
  - at least two of the three real questions add structural value;
  - every material accepted relationship is source-confirmed, with zero known
    material false relationships;
  - code-only, ignore, rename/delete, dirty-tree, branch, fallback, and
    network-denied checks all pass.
  These are bootstrap adoption budgets, not general Graphify benchmarks. Any
  mandatory failure is NO-GO. Do not average away a failed correctness or
  privacy check.
- **Verification:** reviewer performs primary and adversarial passes over the
  full evidence. Orchestrator records the initial bootstrap `Decision: GO` or
  `Decision: NO-GO`, the exact reasons, and the verified raw CLI contract
  table. When the user has authorized Step 7, later-phase authorization remains
  deferred until that supplement is verified and reviewed.

### 7. Test applicability on two real consumer projects

- **Owner:** coder, then verifier and reviewer.
- **Files:** read both consumer repositories; append a clearly separated
  supplement to
  `.claude/explorations/2026-08-09_graphify-compatibility-value-gate/evidence.md`.
  All Graphify output, caches, copies, and timing data remain under `/tmp`.
- **Required Skills:**
  `.claude/skills/integration-gate-spike/SKILL.md`,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `architecture`, `security`, `tests`, `documentation`,
  `performance`.
- **Write boundary:** treat both consumer projects as read-only. Record exact
  initial and final branch, HEAD, `git status --short`, staged/unstaged diffs,
  and nested `.claude` status. Preserve all pre-existing dirty files. Mount
  source read-only for network-denied Graphify runs and place every output in a
  writable `/tmp` mount. Do not run application imports, services, tests,
  dependency synchronization, bootstrap refresh, Graphify update, or any
  Graphify installer/hook/MCP/LLM operation. Never read or index `.env*`,
  credentials, data/model directories, dependency environments, caches,
  generated adapters, or mutable `.claude` state.
- **RAG questions:**
  1. From `RAGService.query`, how does `mode="mixed"` activate semantic and
     graph retrieval, and where do the two document streams join before the API
     response?
  2. From `src.create_index.main`, how do injected dependencies select import
     versus chunk/embed mode, guarantee indexing, and allow storage push only
     after success?
  3. Which module owns `TextGraphBuilder`, how do compatibility imports preserve
     object identity, and how does the owner refer back through the public shim?
     Record that `src/graph/build/**` is live but hidden by the existing
     unanchored `build/` ignore rule. Do not use `--no-gitignore` or edit the
     consumer ignore file to rescue this question.
- **Industrial-inspection questions:**
  1. How do CLI, benchmark, and Gradio requests converge on
     `AgentInspectionRuntime`, and exactly when is a submitted verdict trusted
     versus replaced by heuristic fallback?
  2. How do MVTec masks become stable `cc_n` identities and flow through
     manifests, benchmark cases, grounding comparison, and aggregate metrics?
  3. Across repeated ground/count calls, which evidence stays raw, becomes the
     selected overlap cluster, is count-only NMS-deduplicated, and drives
     verdicts, overlays, or benchmark grounding-hit?
- **Comparison contract:** for every question record the literal Graphify
  command/query, elapsed time, output size, candidate nodes/edges/files,
  omissions, noise/truncation, and every material false or ambiguous result.
  Compare with direct reads and `rg`, plus Semble when available. Confirm every
  accepted relationship against the source paths and lines identified during
  read-only discovery. File discovery alone does not count as structural value.
- **Cross-project override:** both projects must independently add material,
  source-confirmed connectivity value on at least two of three questions; all
  accepted relationships must have zero known material falsehoods; each cold
  extraction must remain `<= 180 s`, each measured query `<= 10 s`, and each
  raw output tree `<= 50 MiB`; network denial and read-only write boundaries
  must pass; ignored/sensitive/generated paths must remain absent; and initial
  and final consumer statuses must match exactly. If either project fails any
  mandatory condition, final decision remains NO-GO and Phases A-F stop.
- **Verification:** verifier reproduces the decisive question scoring and
  source citations, checks Docker mount/network evidence, searches graph output
  for forbidden paths/secrets, compares before/after statuses, and confirms all
  task-created `/tmp` paths are removed. Reviewer runs primary and adversarial
  passes over the combined original and supplementary evidence.

## Dependencies and Risks

- Depends only on the approved big plan and access to the two source DOCX files.
- The candidate package or network may be unavailable. That produces explicit
  NO-GO evidence; it does not authorize a repository change.
- Natural-language output can vary. Judge stable structural facts and source
  confirmation, not exact prose or node counts.
- Performance budgets are explicit initial assumptions. If one is unsuitable,
  stop and amend the plan before execution; do not weaken it in the result.
- Phase 0 must leave the outer repository unchanged. Its closeout is one atomic
  nested AI-state checkpoint for evidence and lifecycle state, not an empty
  outer commit.
- Both consumer projects have pre-existing dirty worktrees. The supplement must
  preserve their exact contents and statuses; any consumer write is a mandatory
  failure, not cleanup work for this plan.

## Verification

```bash
git status --short
uv run python scripts/validate_plan_frontmatter.py .claude/plans/graphify-structural-code-intelligence.md .claude/plans/2026-08-09_phase-0-graphify-compatibility-and-value-gate.md .claude/plans/2026-08-09_phase-A-graphify-managed-dependency-and-thin-adapter.md .claude/plans/2026-08-09_phase-B-graphify-routing-and-agent-integration.md .claude/plans/2026-08-09_phase-C-graphify-generation-and-safe-install.md .claude/plans/2026-08-09_phase-D-graphify-dogfood-and-retention.md .claude/plans/2026-08-09_phase-E-graphify-runtime-diagnostics.md .claude/plans/2026-08-09_phase-F-graphify-optional-persistence-gate.md
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
git diff --check
uv run python .claude/scripts/record_findings.py . --profile architecture --profile security --profile tests --profile documentation --profile performance --phase 2026-08-09_phase-0-graphify-compatibility-and-value-gate --base-ref dev --findings-json <reviewer-findings.json> --out .claude/quality_reports/findings-<timestamp>.json
uv run python .claude/scripts/quality_score.py . --phase 2026-08-09_phase-0-graphify-compatibility-and-value-gate --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

## Acceptance Criteria

- [ ] The outer repository has no tracked, staged, or untracked task file change.
- [ ] The evidence identifies exact pinned CLI, output, update, and failure contracts.
- [ ] Code-only and network-denied execution is proven after package acquisition.
- [ ] `.gitignore` is honored; `.claude/`, `dist/`, ignored secrets, and non-code content are absent.
- [ ] Dirty edits, rename/delete, branch changes, graph-missing, corruption, and missing-tool fallback are measured.
- [ ] Three real questions are compared with `rg`, direct reads, and Semble when available.
- [ ] Six supplementary real-project questions are compared across RAG and industrial-inspection without writing either consumer.
- [ ] Any cross-project override satisfies at least two of three questions independently in each project and every other Step 7 condition.
- [ ] Every material Graphify claim is checked in source.
- [ ] Cold, warm, no-op, size, and churn budgets have reproducible measurements.
- [ ] The artifact contains one unambiguous GO or NO-GO decision.
- [ ] NO-GO explicitly stops Phases A-F without implementation.

## Closeout Checklist

- [x] Verification passed — verifier returned VERIFIED on all six dimensions
- [x] Review findings resolved — 0 critical, 3 major, 2 minor, all remediated
- [x] Score >= 90 persisted with branch/phase metadata — 100, gate EXCELLENCE,
      `.claude/quality_reports/score-20260809T111009Z-phase-0.json`
- [x] Documentation updated or explicitly skipped as pure-internal — the dated
      gate artifact is the documentation; no tracked docs changed
- [x] LEARN entries saved — six entries in `.claude/MEMORY.md`
- [x] Closeout session log has `**Status:** COMPLETED` —
      `.claude/session_logs/2026-08-09_graphify-phase-0-cross-project-supplement.md`

## Result

**NO-GO.** RAG scored 0/3 and industrial-inspection 2/3. The cross-project
override requires both consumers to pass independently, so it fails and Phases
A-F remain unauthorized. All budget, privacy, network-denial, and write-boundary
conditions passed; the failure is value, not cost or safety. Both consumers were
left byte-identical.
