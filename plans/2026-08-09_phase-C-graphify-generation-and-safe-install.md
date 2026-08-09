---
name: 2026-08-09_phase-C-graphify-generation-and-safe-install
type: small-plan
parent_plan: graphify-structural-code-intelligence
phase_index: 3
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-09_phase-C-graphify-generation-and-safe-install

## Scope

Project the Phase A adapter and Phase B guidance from `shared/` into the single
installable multi-agent bundle, which carries GitHub Copilot, Claude Code, and
OpenAI Codex surfaces. Establish one consumer-local raw Graphify output boundary
that is ignored by the outer repository and nested AI-state repository and is
preserved safely across bootstrap refreshes. Raw graph data remains disposable
and unsynchronized; `graph.json` is not persistent state.

Use existing generator, installer, runtime-ownership, and state-sync contracts.
Do not hand-edit `dist/multi-agent/`, add a Graphify installer/hook/MCP path, or
let Graphify own `AGENTS.md`, `CLAUDE.md`, `.github/`, `.codex/`, `.mcp.json`,
`.devcontainer/`, or `core.hooksPath`. Reinstall must preserve tracked authoring
root adapters and all existing consumer state as well as the ignored local graph
workspace.

## Ownership

- `coder`: generator projection, local-state ownership/ignore contract,
  installer/state-sync/generation regressions, and validator prohibitions.
- `verifier`: generate twice, validate all three clients, install into fresh and
  existing fixtures, run Trace2 local-only checks, and run full verification.
- `reviewer`: `code`, `architecture`, `security`, `tests`, `ponytail`, `config`,
  `documentation`, and `performance`.
- `documenter`: update target/install/state documentation after review
  converges, but describe Graphify as provisional until Phase D retention.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` in `full` mode
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

### 1. Generate the thin adapter from shared source

- **Owner:** coder
- **Files:** modify `scripts/generate_targets.py`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode.
- **Review Profiles:** `code`, `architecture`, `tests`, `config`, `ponytail`.
- **Contract:** extend `render_shared_basis()`'s existing explicit helper-copy
  pattern so **new** `shared/scripts/graphify_structural.py` becomes **new
  generated** `.claude/scripts/graphify_structural.py`. Preserve target path
  transformation and executable/readability requirements established by the
  gate. Do not refactor unrelated generator code. The existing skill and policy
  copy paths should carry `shared/skills/graphify-code-graph/SKILL.md` and
  `shared/policies/tool-routing.instructions.md`; modify them only if a failing
  regression proves that necessary.
- **Verification:** `uv run python scripts/generate_targets.py --all`; compare
  source and generated adapter bytes after documented transformations.

### 2. Define ignored consumer-local graph ownership

- **Owner:** coder
- **Files:** modify `scripts/runtime_ownership.py`; modify
  `shared/hooks/scripts/state-sync.sh`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `config`,
  `performance`, `ponytail`.
- **Contract:** add the gate-confirmed raw output root (expected
  `graphify-local`) as one explicit consumer-local ownership root so
  `copy_generated_tree()` does not prune it during reinstall. Add that same
  root to the nested `.claude/.gitignore` rendered by `state-sync.sh` so no raw
  graph, cache, manifest, report, cost, HTML, or auxiliary output is committed
  to `ai-state`. The outer repository already ignores `.claude/`; retain and
  verify that rule. Keep the output disposable and do not add generated seed
  content.
- **Must not:** add `graph.json` to synchronized state; use a negated ignore to
  track selected raw files; change merge drivers; change remote sync; create a
  new hook owner; use `--no-gitignore`.
- **Verification:** test `is_consumer_state_path()` for the local root, generated
  nested ignore text, and outer/nested `git check-ignore -v` results.

### 3. Prove safe reinstall and root-adapter preservation

- **Owner:** coder
- **Files:** modify `tests/test_install_bootstrap.py`; modify installer code only
  if the regression proves existing generic ownership behavior is insufficient.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md`,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `ponytail`.
- **Contract:** install a generated bundle, create byte-marked raw local graph
  files, plans, explorations, session logs, quality reports, project context,
  settings-local state, nested Git metadata, and tracked authoring
  `AGENTS.md`/`CLAUDE.md`. Reinstall and assert every consumer/authoring byte is
  preserved while generated adapter, skill, policy, agents, hooks, and config
  update. Cover fresh, existing git-backed, pre-git legacy, `--allow-self`, and
  repeated local-only refresh paths where current tests provide fixtures.
- **Minimality rule:** prefer adding the output root to the existing ownership
  contract over a Graphify-specific installer branch.
- **Verification:**
  `uv run pytest tests/test_install_bootstrap.py -q --tb=short` and the
  installer scenarios in `scripts/validate_targets.py`.

### 4. Prove nested state ignores raw graph data

- **Owner:** coder
- **Files:** modify `tests/test_state_sync.py`; update
  `scripts/validate_targets.py` state-sync fixtures as needed.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md`,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`,
  `performance`, `ponytail`.
- **Contract:** create representative raw graph files under the local output
  root, run nested setup/checkpoint/push flows, and prove none are staged,
  committed, restored from remote, or copied into bootstrap-root. Confirm
  ordinary plans/reports still synchronize. In local-only mode, capture
  `GIT_TRACE2_EVENT` across the full child process tree and reject `fetch`,
  `ls-remote`, `pull`, `merge`, and `push`, while also checking remote refs.
  Preserve valid HEAD, clean nested worktree, and ordered migration/bootstrap
  commit postconditions from the existing safe-refresh contract.
- **Verification:** `uv run pytest tests/test_state_sync.py -q --tb=short` plus
  generated state-sync validation.

### 5. Validate all three generated client surfaces and prohibitions

- **Owner:** coder
- **Files:** modify `scripts/validate_targets.py` and
  `tests/test_validate_targets.py`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `config`,
  `documentation`, `ponytail`.
- **Contract:** assert the generated adapter, skill, tool routing, Planner
  selection, Orchestrator evidence production, and Reviewer source verification
  appear in the multi-agent basis and target-native GitHub Copilot, Claude Code,
  and OpenAI Codex surfaces. Confirm Reviewer metadata remains non-executing.
  Confirm the generated devcontainer has the exact pin. Add negative assertions
  for Graphify hooks, MCP registration, installer commands, platform-owned
  guidance, root-adapter replacement, `core.hooksPath` changes, LLM features,
  `--no-gitignore`, and generated/tracked raw graph data.
- **Ignore contract:** in a real Graphify fixture, prove `.claude/` and `dist/`
  source content is absent from structural results. Do not assume Git ignore
  success from flags alone.
- **Verification:**
  `uv run pytest tests/test_validate_targets.py -q --tb=short` and
  `uv run python scripts/validate_targets.py`.

### 6. Prove deterministic generation and installation

- **Owner:** verifier
- **Files:** generated `dist/multi-agent/` only; no hand edits or commits.
- **Required Skills:** `.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md`.
- **Review Profiles:** `architecture`, `security`, `tests`, `config`,
  `performance`.
- **Contract:** generate all output twice and use the repository's existing
  `validate_determinism()` coverage to compare complete trees. Install into a
  clean temporary consumer, reinstall, and run runtime checks. Verify generated
  scripts are usable, local raw output survives, all consumer state survives,
  authoring adapters survive, and the nested repository remains clean because
  raw Graphify output is ignored.
- **Verification:** generation, target validation, focused installer/state-sync
  tests, and runtime checks in the full block below.

### 7. Review, document, score, and close the phase

- **Owner:** reviewer, documenter, verifier, orchestrator
- **Files:** all changed Phase C source/tests plus relevant sections of
  `docs/target-mapping.md`, `docs/runtime-checks.md`, and
  `docs/smoke-tests.md` when behavior is externally visible.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/documentation/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `ponytail`,
  `config`, `documentation`, `performance`.
- **Contract:** converge implementation review, update docs afterward, persist
  findings and score against final content, complete LEARN/session log, and
  create one atomic Phase C commit. Describe raw output as local and
  provisional; do not claim retention or persistence.
- **Verification:** run the complete command block after docs settle.

## Dependencies and Risks

- Depends on exact Phase A adapter path and Phase B shared guidance.
- The installer prunes unknown `.claude/` content. The local graph root must
  join the generic consumer-state ownership contract before reinstall tests.
- The nested state repository tracks everything not ignored. The local graph
  root must be explicitly ignored before any real extraction in an installed
  consumer.
- `dist/` is gitignored and disposable. Determinism must use generator/validator
  tree comparisons, not a misleading tracked `git diff` alone.
- Any installer or state-sync change is control-plane/high-risk. Preserve
  durable postconditions and no-remote-I/O tests from the safe-refresh skill.

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
uv run python .claude/scripts/record_findings.py . --profile code --profile architecture --profile security --profile tests --profile ponytail --profile config --profile documentation --profile performance --phase 2026-08-09_phase-C-graphify-generation-and-safe-install --base-ref dev --findings-json <reviewer-findings.json> --out .claude/quality_reports/findings-<timestamp>.json
uv run python .claude/scripts/quality_score.py . --phase 2026-08-09_phase-C-graphify-generation-and-safe-install --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

## Acceptance Criteria

- [ ] The adapter is generated from `shared/` into `.claude/scripts/`.
- [ ] Skill, policy, Planner, Orchestrator, and Reviewer contracts reach Copilot, Claude, and Codex.
- [ ] Reviewer remains non-executing on every client.
- [ ] Raw Graphify output is consumer-local, outer-ignored, nested-ignored, disposable, and unsynchronized.
- [ ] Reinstall preserves raw local output, all existing consumer state, and tracked authoring root adapters.
- [ ] `.claude/` and `dist/` are not structurally indexed; `--no-gitignore` is absent.
- [ ] No Graphify installer, hook, MCP, LLM, root guidance, or Git-hook ownership appears.
- [ ] Generation and repeat installation are deterministic.
- [ ] Generated output remains untracked and is never hand-edited.
- [ ] One atomic Phase C commit follows documentation, score, LEARN, and session closeout.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
