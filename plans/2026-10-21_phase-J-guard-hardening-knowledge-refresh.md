---
name: 2026-10-21_phase-J-guard-hardening-knowledge-refresh
type: small-plan
parent_plan: backlog-followups
phase_index: 10
status: complete
closeout_session_log: .claude/session_logs/2026-10-22_backlog-followups-phase-j.md
---

# Small Plan: Guard Hardening Knowledge Refresh

## Scope

The required final knowledge refresh after the reopen (Knowledge-Refresh
Final Phase rule). It brings live advice and the generated wiki in line
with Phases H and I, and does the wiki style follow-up recorded in the
Phase G closeout log (finding R4 in
`.claude/quality_reports/2026-10-21_backlog-followups-reopen-findings.md`).
It changes no executable behavior.

- **BF-J1.** Stale-claims audit of the Phase H and I changes across live
  advice, then one managed OpenWiki refresh that covers every page whose
  claims those phases made stale or false.
- **BF-J2.** In the pages the refresh rewrites, long sentences are split so
  each states one idea, as `openwiki/INSTRUCTIONS.md` asks. At least the
  `protect-files` bullet in `openwiki/architecture/hooks-and-guardrails.md`
  is rewritten, and the "Reading outside the diff" bullet in
  `openwiki/architecture/agents-and-skills.md` when the refresh plans that
  page.

## Steps

- [x] **1. Run the stale-claims audit (BF-J1).**
  **Owner:** orchestrator, with a documenter for prose changes.
  **Required Skills:** `shared/skills/documentation/SKILL.md`,
  `shared/skills/ponytail/SKILL.md` (full).
  Sweep root guidance, `docs/`, shared policies, skills, templates, agents,
  review profiles, state READMEs, and `.claude/MEMORY.md` for statements
  about how the guard reads shell text, which write forms it catches, and
  how the OpenWiki restore is run. Check that Phase H's `MEMORY.md`
  correction holds. Correct each false statement. Leave dated records
  unchanged. Record every surface and its outcome under
  `## Stale-claims surfaces checked` in the closeout log.

- [x] **2. Refresh the OpenWiki knowledge layer (BF-J1, BF-J2).**
  **Owner:** orchestrator on the main thread, as the knowledge-refresh
  skill requires.
  **Required Skills:** `shared/skills/knowledge-refresh/SKILL.md` and
  OpenWiki's own `openwiki` skill.
  Run one managed `update` refresh after all source edits. Plan at least
  `architecture/hooks-and-guardrails.md` and
  `operations/deterministic-verification.md`, plus every page
  `openwiki_begin` reports with claim issues. Give each page the
  instruction to keep sentences short, one idea each, and to write links
  relative to the page's folder. Reconcile every stale claim. Inspect the
  generated diff; if OpenWiki stamps a link, fix it with a second scoped
  `update` run. Never hand-edit generated pages or claims files.

- [x] **3. Review, verify, close out.**
  **Owner:** orchestrator; fresh reviewer.
  **Required Skills:** `shared/skills/code-review/SKILL.md`.
  Map BF-H1 to BF-J2 to their evidence in the closeout log.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
test ! -e openwiki/.run.json    # a finished OpenWiki refresh removes its run file
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

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
