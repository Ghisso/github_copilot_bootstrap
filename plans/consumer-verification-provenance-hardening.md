---
name: consumer-verification-provenance-hardening
type: big-plan
status: in-progress
originating_branch: dev
implementation_branch: consumer-verification-provenance-hardening_implementation
started_at: 2026-08-30T03:10:05Z
phases:
  - 2026-08-30_phase-A-consumer-native-verification
  - 2026-08-30_phase-B-provenance-and-consumer-lifecycle-proof
current_phase: 2026-08-30_phase-B-provenance-and-consumer-lifecycle-proof
---
# Big Plan: consumer-verification-provenance-hardening

## Context

The verification-evidence workflow consolidation is implemented. The bootstrap
now has deterministic verification, strict fail-closed states, receipt-based
closeout authority, conditional planning, independent review, bounded Context
Mode indexing, context reuse, and separate paused checkpoint publication.

A post-merge audit found three remaining high-value gaps:

1. generic verification still assumes bootstrap-authoring paths such as
   `shared`, `scripts`, and `tests`, which is unsafe for ordinary consumers;
2. receipts bind outer repository state but do not yet strongly bind the nested
   `.claude` control-plane/runtime/plan state that governed verification;
3. there is no small representative generated consumer exercising the whole
   deterministic lifecycle and proving those properties together.

A smaller semantic issue also remains: some emitted check IDs may represent
structural truths asserted as PASS rather than measurements that can actually
turn red.

## Goals

- Make `verify fast` and `verify phase` correct for bootstrap self-verification
  and ordinary generated consumers.
- Prefer consumer-native tool/project configuration over new bootstrap config.
- Fail closed when a required trustworthy verification scope cannot be derived.
- Bind persisted evidence to relevant nested `.claude` control-plane state.
- Reuse existing state-sync/runtime-ownership metadata and helpers.
- Add one deterministic generated-consumer lifecycle fixture.
- Add negative mutations for source, plan, runtime, nested-state, and receipt
  staleness/tampering.
- Audit emitted runtime checks for actual falsifiability.
- Preserve the current lifecycle and gate architecture.

## Non-Goals

- No lifecycle redesign.
- No LLM verifier.
- No PMAT, `pv`, Lean, Kani, mutation-testing framework, or contract DSL.
- No new bootstrap-specific verification config file.
- No generic framework/language detector.
- No weakening of verification, score, findings, branch, plan, pause,
  cancellation, bypass, commit, push, or PR rules.
- No Context Mode/Semble redesign.
- No provider model/tool routing changes.
- No hashing of every package/tool/environment variable.

## Design

### Consumer verification scope

```text
bootstrap authoring repo
    -> existing explicit authoring targets/check groups

generated consumer repo
    -> derive required scope from project-native configuration/layout
    -> exclude bootstrap-owned `.claude` runtime from application checks
    -> run project-native tools
    -> UNVERIFIED if required trustworthy scope cannot be established
```

Prefer existing configuration:

- Ruff: consumer-native project/repository scope and exclusions.
- Pytest: native discovery/configuration.
- Mypy: configured `files`, `packages`, `modules`, or equivalent first; otherwise
  only a narrowly proven conventional source root.
- If a required check applies but safe scope cannot be determined, use
  `UNVERIFIED`.

Do not create a parallel project classifier.

### Nested control-plane provenance

Completed evidence should prove:

```text
outer repository state measured
+
governing bootstrap/control-plane state used
```

Minimum semantic coverage:

- nested control-plane Git HEAD when available;
- nested tracked-state/dirty fingerprint when HEAD alone is insufficient;
- active big-plan digest;
- active small-plan digest;
- verification/runtime ownership fingerprint;
- schema/version.

Prefer one canonical control-plane fingerprint derived from existing ownership
metadata plus explicit active-plan digests. Exclude mutable evidence outputs so
receipts do not invalidate themselves merely by being written.

### Generated-consumer lifecycle proof

Use one tiny deterministic consumer:

```text
consumer/
├── pyproject.toml
├── src/example_consumer/
└── tests/
```

Exercise:

```text
generate/install
-> verify fast
-> verify phase
-> deterministic review/findings fixture
-> score/docs/learn/session evidence
-> verify closeout
-> commit gate
```

No LLM calls.

## Why Two Phases

1. Consumer-native verification is a current correctness issue and should be
   fixed independently.
2. Provenance, full lifecycle proof, and check-ID falsifiability all concern the
   trustworthiness of the now-correct verifier/receipt path.

A third phase would add ceremony without a distinct rollback boundary.

## Phases

- [ ] `2026-08-30_phase-A-consumer-native-verification` — consumer-native verification
- [ ] `2026-08-30_phase-B-provenance-and-consumer-lifecycle-proof` — nested provenance, generated-consumer lifecycle proof, check-ID audit

## Repository-Wide Acceptance

- Consumer verification no longer assumes bootstrap `shared/scripts/tests`.
- Bootstrap self-verification remains correct.
- Consumer tools use native project configuration/layout and fail closed when
  safe required scope cannot be established.
- `.claude` runtime is not accidentally linted/typed as consumer source.
- Representative clean/broken consumers behave correctly.
- Phase/closeout evidence binds outer and governing nested control-plane state.
- Relevant plan/runtime/control-plane mutations stale evidence.
- Receipt generation does not self-invalidate on its own mutable outputs.
- Generated consumer reaches valid commit gate without LLM calls.
- Every emitted runtime PASS is genuinely measured/falsifiable.
- Structural invariants live in schema/code/tests rather than synthetic PASS
  results.
- Existing workflow, conditional planner, Context Mode, review, language, pause,
  score, findings, and gate semantics remain unchanged.

## Verification

Final verification must include current equivalents of:

```bash
uv run pytest tests/ -q --tb=short
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

Also run the generated-consumer verification/lifecycle fixture from a clean
temporary directory.

## Upstream References

- https://github.com/paiml/aprender
- https://github.com/paiml/paiml-mcp-agent-toolkit
