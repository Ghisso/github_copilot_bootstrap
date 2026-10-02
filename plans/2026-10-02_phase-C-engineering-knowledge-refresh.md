---
name: 2026-10-02_phase-C-engineering-knowledge-refresh
type: small-plan
parent_plan: engineering-workflow-improvements
phase_index: 3
status: planned
closeout_session_log:
---

# Small Plan: Engineering Workflow Knowledge Refresh

## Scope

Refresh the enabled OpenWiki layer after Phase A's and Phase B's guidance changes, then
audit live advice for the full plan. This is the final phase retained
by the canonical Knowledge-Refresh Final Phase rule. It adds no feature,
provider, or verification authority.

## Steps

- [ ] **1. Refresh through OpenWiki's own MCP lifecycle.**
  **Owner:** orchestrator.
  **Required Skills:** `shared/skills/knowledge-refresh/SKILL.md`,
  `.claude/skills/openwiki/SKILL.md`.
  Use `mode: "update"`; inspect the returned jobs and source changes.
  Likely pages include `openwiki/architecture/agents-and-skills.md`,
  `openwiki/workflows/lifecycle-and-task-lanes.md`,
  `openwiki/operations/deterministic-verification.md`, and
  `openwiki/operations/sidecar-overlay.md`. Use actual tool jobs, not this
  candidate list, to define work. Map every cited source range on rewritten
  pages. Allow no concurrent tracked-file edits while the refresh is open.
  Check/restore root adapters immediately after begin, including a failed
  call, per the skill. Resume failed runs; do not delete `.run.json` or use
  init. Rebaseline only by the documented unreachable-base procedure.
  **Acceptance:** the OpenWiki lifecycle reports completion; generated
  claims distinguish optional behavioral measurements from deterministic
  receipts and full-install gates from sidecar advice. They also preserve
  approved-plan/scope-change authority, optional specs/IDs, `.ai-bootstrap/`,
  and caller-saved specialist outputs. REQ-006 remains deferred; do not
  describe an evaluator as delivered or text checks as behavioral evidence.

- [ ] **2. Audit live advice and durable learning.**
  **Owner:** documenter; orchestrator owns MEMORY and the session log.
  **Required Skills:** `shared/skills/documentation/SKILL.md`,
  `shared/skills/humanize/SKILL.md`, `shared/skills/learn/SKILL.md`.
  Audit README, root guidance, docs, shared policies/skills/templates/agents/
  review profiles, state READMEs, installer/runtime help where relevant,
  `.claude/instructions/project-context.instructions.md`, and
  `.claude/MEMORY.md`. Correct or supersede live advice invalidated by this
  or earlier work. Keep historical calibration evidence, completed plans,
  dated exploration claims, and receipt-bound logs unchanged. Never rewrite
  a historic self-audit PASS into a new behavioral verdict. Record each
  audited surface/outcome under `## Stale-claims surfaces checked` in the
  final closeout log. If source corrections stale generated claims/ranges,
  refresh the affected pages through MCP again.

- [ ] **3. Review and complete terminal closeout.**
  **Owner:** reviewer, then orchestrator.
  **Required Skills:** `shared/skills/code-review/SKILL.md`,
  `shared/skills/learn/SKILL.md`.
  Inspect the generated diff; never hand-edit wiki pages/claims. Exclude
  `openwiki/.run.json` and OpenWiki-managed root snippets from the commit.
  Record reusable lessons or the no-lessons marker. Complete the existing
  findings, staging, phase/closeout receipts, commit, and normal push route.
  Provider failures block this required refresh with their actual error;
  they are not fabricated deterministic test failures. Complete the big
  plan only after every phase's evidence is valid.

## Verification

```bash
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Record the OpenWiki completion result and reviewed page list. This MCP
  evidence is required by the enabled-wiki policy but is not a shell command
  for the deterministic verifier to repeat.

## Review Profiles

Use `.claude/review-profiles/documentation.md`,
`.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
and `.claude/review-profiles/ponytail.md`.

## Closeout Checklist

Follow the fixed CLOSEOUT order in `shared/policies/workflow.instructions.md`.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
