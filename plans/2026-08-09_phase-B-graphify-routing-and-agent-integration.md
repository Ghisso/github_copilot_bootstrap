---
name: 2026-08-09_phase-B-graphify-routing-and-agent-integration
type: small-plan
parent_plan: graphify-structural-code-intelligence
phase_index: 2
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-09_phase-B-graphify-routing-and-agent-integration

## Scope

After Phase A verifies the managed dependency and thin adapter, add Graphify's
narrow structural role to canonical `shared/` guidance. Preserve every existing
retrieval responsibility. Planner may use Graphify selectively during bounded
full-plan discovery when callers, downstream consumers, or cross-module paths
are materially uncertain; micro-plans do not invoke it by default.

For structurally significant reviews, Orchestrator prepares a compact evidence
packet. Reviewer remains non-executing, treats graph edges only as navigation
leads, reads the candidate source, and makes findings only from source-confirmed
behavior. Coder may use the globally routed skill when useful. Verifier has no
mandatory Graphify path. Guidance is authored only in `shared/`; generated
Copilot, Claude, and Codex files are not hand-edited.

## Ownership

- `coder`: canonical skill, routing policy, Planner/Orchestrator/Reviewer
  prompts, structural validators, and focused tests.
- `verifier`: generate all client surfaces, validate capability boundaries,
  run focused/full tests, and inspect normalized commands.
- `reviewer`: `code`, `architecture`, `security`, `tests`, `ponytail`, `config`,
  `documentation`, and `performance`.
- `documenter`: keep routing and evidence language clear in canonical shared
  sources; defer broad README promotion until Phase D retention.

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

### 1. Add the structural-intelligence skill

- **Owner:** coder
- **Files:** create **new**
  `shared/skills/graphify-code-graph/SKILL.md`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/documentation/SKILL.md`,
  `.claude/skills/integration-gate-spike/SKILL.md`.
- **Review Profiles:** `architecture`, `security`, `documentation`,
  `performance`, `ponytail`.
- **Contract:** include valid skill frontmatter with
  `visibility: public|background` chosen from current conventions. Define
  Graphify as local structural connectivity only: callers/callees, imports,
  inheritance/implementation, paths between symbols, architectural
  neighborhoods, and candidate blast radius. Route executable agents through
  the Phase A adapter's normalized commands and use only operations recorded by
  Phase 0. Explain missing-tool fallback and the exact-pin upgrade re-gate.
- **Must:** require direct source verification for every material relationship;
  label `EXTRACTED`, `INFERRED`, and `AMBIGUOUS` as lead quality, not finding
  authority; keep output compact.
- **Must not:** replace direct reads, `rg`, Semble, context-mode, or context7;
  call raw lifecycle commands; instruct any installer, hook, MCP, save, reflect,
  memory, LLM, or `--no-gitignore` use; require Graphify for trivial work.
- **Verification:** generate targets and confirm the transformed skill preserves
  adapter paths and commands without adding target-specific ownership.

### 2. Extend the single authoritative routing policy

- **Owner:** coder
- **Files:** modify `shared/policies/tool-routing.instructions.md`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/documentation/SKILL.md`.
- **Review Profiles:** `architecture`, `config`, `documentation`, `performance`,
  `ponytail`.
- **Contract:** retain direct read for known paths, `rg` for exact literals and
  symbols, Semble for semantic/related-code ownership, context-mode for large
  output and continuity, and context7 for current external documentation. Add
  Graphify only for structural connectivity and blast-radius candidates. A
  graph result normally flows to direct source read, or to Semble then direct
  read when behavior semantics remain unclear. Missing Graphify outside the
  managed devcontainer is WARN/fallback.
- **Must not:** put Graphify first in a generic fallback order, run broad
  Graphify and Semble for the same question without a concrete gap, or imply
  that graph output verifies behavior.
- **Verification:** focused prose validators and generated-target inspection.

### 3. Add selective Planner use

- **Owner:** coder
- **Files:** modify `shared/agents/planner/prompt.md`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/documentation/SKILL.md`.
- **Review Profiles:** `architecture`, `security`, `documentation`,
  `performance`, `ponytail`.
- **Contract:** in bounded full-plan discovery, consider Graphify only for
  cross-module changes, shared/public interfaces, shared config/schema,
  architecture boundaries, broad refactors, or genuinely unknown callers and
  consumers. Suggested sequence: direct read/Semble identifies anchors;
  Graphify inspects connectivity; direct reads confirm material edges; the plan
  records structural impact only when it changed scope or dependency order.
  The structural-impact note contains anchors, confirmed consumers, downstream
  boundaries, candidate tests, and uncertainty.
- **Micro-plan contract:** no automatic Graphify call. Use it only when the
  apparently small task has a concrete architecture/consumer uncertainty that
  would otherwise make the plan unsafe.
- **Verification:** validator fixtures reject unconditional Graphify calls,
  missing source verification, and Graphify use that repeats bounded discovery.

### 4. Make Orchestrator the review-evidence producer

- **Owner:** coder
- **Files:** modify `shared/agents/orchestrator/prompt.md`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/documentation/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `documentation`,
  `performance`, `ponytail`.
- **Contract:** before REVIEW only when a diff changes a shared/public API,
  shared config/schema, cross-module architecture, central utility with unclear
  consumers, or control-plane dependency boundary, identify anchor symbols and
  run targeted adapter queries. Pass Reviewer the compact evidence packet from
  the big plan with graph status, purpose, anchors, labeled observations,
  candidate relative files, and caveats. If Graphify is unavailable, say so
  and continue with existing retrieval.
- **Must not:** alter the canonical lifecycle order, dump a raw graph/report,
  run Graphify for documentation-only or isolated changes, or present a graph
  edge as a finding.
- **Verification:** structural prompt validation plus generated Orchestrator
  inspection for all three clients.

### 5. Add Reviewer consumption without execute capability

- **Owner:** coder
- **Files:** modify `shared/agents/reviewer/prompt.md`; read but do not modify
  `shared/agents/reviewer/agent.yaml` unless a regression test exposes unrelated
  drift.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/documentation/SKILL.md`.
- **Review Profiles:** `architecture`, `security`, `documentation`, `ponytail`.
- **Contract:** add optional structural evidence to Reviewer inputs. Reviewer
  uses candidate files to choose source reads, confirms every material edge at
  the cited implementation, drops unsupported leads during its existing
  refutation/convergence passes, and never treats missing Graphify evidence as
  a review failure. `INFERRED` and `AMBIGUOUS` cannot become findings without
  independent source proof; `EXTRACTED` still requires source confirmation.
- **Capability boundary:** Reviewer keeps read/search only. Do not add execute,
  Bash, adapter invocation, delegation, or findings persistence capability.
- **Verification:** generated Claude/Copilot/Codex reviewer metadata and prompt
  tests assert no execute capability and no raw Graphify command.

### 6. Add structural routing regressions

- **Owner:** coder
- **Files:** modify `scripts/validate_targets.py` and
  `tests/test_validate_targets.py`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/testing-patterns/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `config`,
  `ponytail`.
- **Contract:** add small public validator helpers where current tests require
  mutation cases. Assert the full responsibility matrix, Planner selection and
  micro-plan restraint, Orchestrator packet production, Reviewer
  source-verification and non-execution, fallback, and prohibited Graphify
  surfaces. Reject obsolete language that Graphify replaces Semble or that
  every non-documentation diff has a special zero-Ponytail gate. Test semantic
  contracts with whitespace-tolerant assertions rather than fragile wrapping.
- **Verification:**
  `uv run pytest tests/test_validate_targets.py -q --tb=short`, then generation
  and full target validation.

### 7. Review, document, score, and close the phase

- **Owner:** reviewer, documenter, verifier, orchestrator
- **Files:** all changed Phase B files.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` in `full` mode,
  `.claude/skills/documentation/SKILL.md`.
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `ponytail`,
  `config`, `documentation`, `performance`.
- **Contract:** converge code/policy review, then finalize canonical guidance,
  persist findings and score against final content, complete LEARN and session
  log, and create one atomic Phase B commit. Do not update broad product docs or
  call Graphify retained before Phase D.
- **Verification:** run the complete block below after documentation.

## Dependencies and Risks

- Depends on Phase A's adapter command and warning/exit contract. Use its exact
  names; do not copy provisional commands from the DOCX sources.
- Graphify can be overused because it sounds generally useful. Selection rules
  must state positive structural triggers and explicit non-triggers.
- Reviewer evidence can anchor a false finding. Source confirmation and the
  existing adversarial review passes are mandatory.
- Agent capability changes can be subtle across clients. Tests must inspect
  metadata and generated prompts, not trust prose alone.
- All canonical behavior changes live under `shared/`; validator/test changes
  enforce them, and generated files remain outputs only.

## Verification

```bash
uv run pytest tests/test_validate_targets.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ shared/scripts/ tests/
uv run ruff format --check scripts/ shared/scripts/ tests/
git diff --check
uv run python .claude/scripts/record_findings.py . --profile code --profile architecture --profile security --profile tests --profile ponytail --profile config --profile documentation --profile performance --phase 2026-08-09_phase-B-graphify-routing-and-agent-integration --base-ref dev --findings-json <reviewer-findings.json> --out .claude/quality_reports/findings-<timestamp>.json
uv run python .claude/scripts/quality_score.py . --phase 2026-08-09_phase-B-graphify-routing-and-agent-integration --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

## Acceptance Criteria

- [ ] Graphify's structural role is distinct from every existing retrieval tool.
- [ ] The new shared skill uses only the Phase A adapter and exact verified operations.
- [ ] Planner uses Graphify selectively in full plans; micro-plans have no default call.
- [ ] Orchestrator prepares compact evidence only for structural review triggers.
- [ ] Reviewer remains non-executing and source-verifies every graph-derived lead.
- [ ] Coder remains optional and Verifier remains non-mandatory for Graphify.
- [ ] Missing Graphify warns and falls back without weakening the workflow.
- [ ] No installer, hook, MCP, LLM, raw lifecycle, or `--no-gitignore` guidance exists.
- [ ] Generated guidance stays deterministic and broad documentation waits for retention.
- [ ] One atomic Phase B commit follows documentation, score, LEARN, and session closeout.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
