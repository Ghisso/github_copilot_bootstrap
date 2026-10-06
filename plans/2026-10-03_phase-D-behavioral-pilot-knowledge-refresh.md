---
name: 2026-10-03_phase-D-behavioral-pilot-knowledge-refresh
type: small-plan
parent_plan: behavioral-evaluation-pilot
phase_index: 4
status: complete
closeout_session_log: .claude/session_logs/2026-10-06_behavioral-pilot-phase-d.md
---

# Small Plan: Behavioral Pilot Knowledge Refresh

## Scope

The final phase required by the canonical Knowledge-Refresh Final Phase
rule. Covers BEP-006 and BEP-007. Run the live-advice audit and its source
fixes first, then refresh OpenWiki once, so no source edit happens while a
refresh is open. It also closes the follow-ups the previous plan left. It
adds no feature, provider, or verification authority. It runs whether or
not Phases B and C were cancelled; a stopped pilot is recorded as such.

## Steps

- [x] **1. Audit live advice and fix stale claims before the refresh.**
  **Owner:** documenter for README and `docs/`; coder for `shared/` and
  tests; orchestrator for `.claude/MEMORY.md` and the session log.
  **Required Skills:** `.claude/skills/documentation/SKILL.md`,
  `.claude/skills/humanize/SKILL.md`, `.claude/skills/learn/SKILL.md`,
  `.claude/skills/ponytail/SKILL.md` (full).
  Sweep README, root guidance (report only), `docs/` except dated
  documents, `shared/` policies, skills, templates, agents, review profiles,
  state READMEs, installer help, and `.claude/MEMORY.md`. Grep the
  generated `dist/` output for authoring-only text, not only the source.
  Close these follow-ups: `shared/templates/skill-template.md` should name
  both `shared/skills/` (authoring) and `.claude/skills/` (installed
  project); `shared/agents/planner/workflow-prompt.md:15` lists only
  big-plan statuses. Make sure live docs describe the pilot mode and point
  to the dated result, and that no text calls it a gate or a general
  quality claim. Before editing any file, search `openwiki/.claims/**` for
  its path; an edit inside a cited range is fine here because step 2
  refreshes after it.
  **Acceptance:** every audited surface has a recorded outcome for
  `## Stale-claims surfaces checked`.

- [x] **2. Refresh through OpenWiki's own MCP lifecycle.**
  **Owner:** orchestrator.
  **Required Skills:** `.claude/skills/knowledge-refresh/SKILL.md`,
  `.claude/skills/openwiki/SKILL.md`.
  Use `mode: "update"`. Check root adapters right after `openwiki_begin`.
  Plan the pages the tool flags plus the agents page, so its claims can be
  re-anchored: the four `scripts/validate_targets.py` ranges that start one
  line early (`claim_d3de19e9`, `claim_2f92f8a6`, `claim_11607a59`), and
  the two thin evidence ranges (the sidecar advisory-checks sentence and the
  guidance-test claim). Use `openwiki_inspect_page_claims` before revising
  otherwise-current claims. Make no tracked-file edit while the run is open.
  **Acceptance:** `openwiki_finish` returns `complete`; no
  `openwiki/.run.json` remains; generated claims describe the pilot as
  advisory host evidence, never as a deterministic receipt.

- [x] **3. Review and complete terminal closeout.**
  **Owner:** reviewer, then orchestrator.
  **Required Skills:** `.claude/skills/code-review/SKILL.md`,
  `.claude/skills/learn/SKILL.md`.
  Inspect the generated diff; never hand-edit wiki pages or claims. Exclude
  `openwiki/.run.json` and OpenWiki-managed root snippets from the commit.
  Map BEP-001 to BEP-007 to evidence in the closeout log. Complete the big
  plan only after every phase is complete or validly cancelled.

## Verification

```bash
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Record the OpenWiki completion result and the reviewed page list. This MCP
  evidence is required by the enabled-wiki policy but is not a shell command
  for the deterministic verifier to repeat.

## Review Profiles

Use `.claude/review-profiles/documentation.md`,
`.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
and `.claude/review-profiles/ponytail.md`.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`.

- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
