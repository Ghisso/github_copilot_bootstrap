---
name: 2026-08-09_phase-E-graphify-runtime-diagnostics
type: small-plan
parent_plan: graphify-structural-code-intelligence
phase_index: 5
status: cancelled
cancelled_at: 2026-08-11T07:37:06Z
cancelled_reason: Phase 0 returned NO-GO because measured value did not justify bootstrap integration
cancelled_evidence: .claude/explorations/2026-08-09_graphify-compatibility-value-gate/evidence.md
closeout_session_log:
---

# Small Plan: 2026-08-09_phase-E-graphify-runtime-diagnostics

## Scope

Proceed only when Phase D records `Decision: RETAIN`. Add deterministic,
read-only availability, exact-version, and health diagnostics for the retained
Graphify dependency. Default host checks must report missing or incompatible
Graphify as `WARN` with direct-read/`rg`/Semble fallback. An explicit strict
mode used inside the managed devcontainer must fail when the pinned executable
is missing, has the wrong version, or cannot complete the Phase 0-confirmed
harmless health operation.

Diagnostics must not build, refresh, query, parse, persist, or rewrite a graph;
must not contact the network; and must remain fast enough for ordinary runtime
checks. This phase does not change retention and does not authorize compact
persistence. It extends the Phase A adapter and existing `check_runtime.py`
instead of adding a second diagnostic framework.

## Ownership

- `coder`: adapter diagnostic operation, runtime-check strict/default behavior,
  focused tests, generated/runtime validators, and narrow documentation.
- `verifier`: run absent, exact, wrong-version, malformed-output, and failing
  executable cases on host and managed paths.
- `reviewer`: `code`, `architecture`, `security`, `tests`, `ponytail`, `config`,
  `documentation`, and `performance`.
- `documenter`: update retained runtime and smoke-test guidance after code
  review, before findings and score persistence.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` in `full` mode
- `.claude/skills/testing-patterns/SKILL.md`
- `.claude/skills/documentation/SKILL.md`
- `.claude/skills/integration-gate-spike/SKILL.md`

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

### 1. Gate diagnostics on RETAIN evidence

- **Owner:** orchestrator and verifier
- **Files:** read Phase D dogfood evidence; append the diagnostic test matrix to
  the Phase E session/quality evidence.
- **Required Skills:** `.claude/skills/integration-gate-spike/SKILL.md`.
- **Review Profiles:** `architecture`, `security`, `tests`.
- **Contract:** refuse to modify code unless Phase D says RETAIN and names exact
  version output plus one harmless no-network health operation. Capture
  expected outcomes for absent, `0.9.35`, wrong version, non-zero health,
  malformed version output, timeout, and unexpected executable path.
- **Verification:** cite the Phase D decision and Phase 0 raw CLI contract in
  the implementation handoff.

### 2. Add a read-only adapter diagnostic

- **Owner:** coder
- **Files:** modify `shared/scripts/graphify_structural.py`; modify
  `tests/test_graphify_structural.py`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`,
  `performance`, `ponytail`.
- **Contract:** add normalized `diagnose --json` to the existing
  `main(argv: Sequence[str] | None = None) -> int` interface. Emit one stable
  JSON object with exactly the evidence-needed fields: `available`, `version`,
  `compatible`, `healthy`, and `message`. Exact compatibility means
  `0.9.35`. Use the Phase 0-confirmed version and harmless health argv with a
  bounded timeout. Missing executable has a stable distinct adapter exit code;
  wrong version and failed health have separate stable codes. Human warnings go
  to stderr; JSON stays parseable on stdout.
- **Must not:** create the local output directory, inspect source, run extract/
  update/query, invoke Git, use network, install Graphify, or add generalized
  diagnostics abstractions.
- **Verification:** fake-executable tests assert exact argv, exit codes, JSON
  schema, stderr, timeout, no filesystem writes, and no Graphify lifecycle call.

### 3. Add default-WARN and managed-strict runtime checks

- **Owner:** coder
- **Files:** modify `scripts/check_runtime.py`; modify
  `tests/test_check_runtime.py`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `config`,
  `performance`, `ponytail`.
- **Contract:** extend `main` to
  `main(argv: Sequence[str] | None = None) -> int` with an explicit
  `--require-graphify` flag. The default path calls the generated adapter's
  diagnostic: exact healthy version is PASS; missing, incompatible, or unhealthy
  is WARN with fallback and does not change the final exit code. Strict mode,
  used in the managed devcontainer smoke, makes those conditions FAIL and
  returns non-zero. Invalid/malformed diagnostic output must be reported
  precisely; do not collapse it into “missing.” Existing runtime drift,
  optional-tool, and plan-frontmatter behavior stays unchanged.
- **Verification:** tests parameterize available/exact, absent, wrong version,
  unhealthy, timeout, malformed JSON, and adapter missing. Assert default and
  strict exit codes plus actionable messages.

### 4. Generate and validate the diagnostic contract

- **Owner:** coder
- **Files:** modify `scripts/validate_targets.py` and
  `tests/test_validate_targets.py` only for deterministic generated/runtime
  assertions; `scripts/generate_targets.py` should need no new copy path.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `config`,
  `performance`, `ponytail`.
- **Contract:** assert the generated adapter includes the stable diagnostic
  schema and no graph mutation. Assert default host diagnostics are WARN and
  managed strict mode is available. Run strict mode inside the generated
  devcontainer smoke; do not auto-detect managed environments with fragile
  filesystem/environment heuristics. Preserve all Graphify prohibition checks.
- **Verification:** focused validator tests, generation, target validation,
  default runtime check on the host, and strict check in the managed image.

### 5. Review, document, score, and close the phase

- **Owner:** reviewer, documenter, verifier, orchestrator
- **Files:** all changed Phase E files; modify applicable Graphify sections in
  `README.md`, `docs/runtime-checks.md`, and `docs/smoke-tests.md`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/documentation/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `ponytail`,
  `config`, `documentation`, `performance`.
- **Contract:** converge implementation review, then document the default WARN
  and explicit managed strict command, exact version, JSON fields, and fallback.
  Persist findings and score after docs, complete LEARN/session log, and create
  one atomic Phase E commit. Do not document or add persisted graph artifacts.
- **Verification:** run the full block below after documentation.

## Dependencies and Risks

- Hard dependency: Phase D RETAIN. REMOVE means this phase and Phase F do not run.
- Version output parsing can be brittle. Use only the exact format captured in
  Phase 0 and fail precisely on unexpected output.
- A “health” check can accidentally become an extraction. The allowed command
  is read-only, network-free, bounded, and tested for zero graph writes.
- Host absence is expected. Only explicit `--require-graphify` changes it from
  WARN to FAIL.
- Diagnostic code touches generated runtime/control-plane behavior and requires
  the full review set with ordinary severity gates.

## Verification

```bash
uv run pytest tests/test_graphify_structural.py tests/test_check_runtime.py tests/test_validate_targets.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ shared/scripts/ tests/
uv run ruff format --check scripts/ shared/scripts/ tests/
git diff --check
uv run python .claude/scripts/record_findings.py . --profile code --profile architecture --profile security --profile tests --profile ponytail --profile config --profile documentation --profile performance --phase 2026-08-09_phase-E-graphify-runtime-diagnostics --base-ref dev --findings-json <reviewer-findings.json> --out .claude/quality_reports/findings-<timestamp>.json
uv run python .claude/scripts/quality_score.py . --phase 2026-08-09_phase-E-graphify-runtime-diagnostics --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

Inside the generated managed devcontainer, additionally run:

```bash
uv run python scripts/check_runtime.py --require-graphify
uv run python .claude/scripts/graphify_structural.py diagnose --json
```

## Acceptance Criteria

- [ ] Phase D RETAIN and the exact harmless health contract are cited.
- [ ] Diagnostic output has stable availability, version, compatibility, health, and message fields.
- [ ] Exact `0.9.35` is required for compatibility.
- [ ] Diagnose performs no extraction, update, query, Git, network, or persistence work.
- [ ] Missing/wrong/unhealthy Graphify is WARN/fallback by default outside the managed devcontainer.
- [ ] `--require-graphify` deterministically fails those cases in managed smoke.
- [ ] Malformed output and timeouts are diagnosed accurately.
- [ ] Generated output and runtime documentation match the implementation.
- [ ] No raw or compact persistence is introduced.
- [ ] One atomic Phase E commit follows documentation, score, LEARN, and session closeout.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
