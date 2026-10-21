---
name: 2026-10-21_phase-I-guard-quoting-knowledge-refresh
type: small-plan
parent_plan: backlog-followups
phase_index: 9
status: planned
closeout_session_log:
---

# Small Plan: Guard Quoting Knowledge Refresh

## Scope

The required final knowledge refresh after the reopen (Knowledge-Refresh
Final Phase rule). It brings live advice and the generated wiki in line
with Phase H, and does the wiki style follow-up recorded in the Phase G
closeout log (finding R4 in
`.claude/quality_reports/2026-10-21_backlog-followups-reopen-findings.md`).
It changes no executable behavior.

- **BF-I1.** Stale-claims audit of Phase H's changes across live advice,
  then one managed OpenWiki refresh that covers every page whose claims
  Phase H made stale or false.
- **BF-I2.** In the pages the refresh rewrites, long sentences are split
  so each states one idea, as `openwiki/INSTRUCTIONS.md` asks. At least the
  `protect-files` bullet in `openwiki/architecture/hooks-and-guardrails.md`
  and the "Reading outside the diff" bullet in
  `openwiki/architecture/agents-and-skills.md` are rewritten.

## Steps

- [ ] **1. Run the stale-claims audit (BF-I1).**
  **Owner:** orchestrator, with a documenter for prose changes.
  **Required Skills:** `shared/skills/documentation/SKILL.md`,
  `shared/skills/ponytail/SKILL.md` (full).
  Sweep root guidance, `docs/`, shared policies, skills, templates, agents,
  review profiles, state READMEs, and `.claude/MEMORY.md` for statements
  about how the guard parses shell text and how the OpenWiki restore is
  run. Correct each false one. The `[LEARN:tooling]` `protect-files.sh`
  entry in `MEMORY.md` must say the quoted-operator defect is fixed, and
  name Phase H. Leave dated records unchanged. Record every surface and
  its outcome under `## Stale-claims surfaces checked` in the closeout log.

- [ ] **2. Refresh the OpenWiki knowledge layer (BF-I1, BF-I2).**
  **Owner:** orchestrator on the main thread, as the knowledge-refresh
  skill requires.
  **Required Skills:** `shared/skills/knowledge-refresh/SKILL.md` and
  OpenWiki's own `openwiki` skill.
  Run one managed `update` refresh after all source edits. Plan at least
  `architecture/hooks-and-guardrails.md` (parser rule, new reasons),
  `operations/deterministic-verification.md` (restore message), and
  `architecture/agents-and-skills.md` (style item), plus every page
  `openwiki_begin` reports with claim issues. Give each page the
  instruction to keep sentences short, one idea each, and to write links
  relative to the page's folder. Reconcile every stale claim. Inspect the
  generated diff; if OpenWiki stamps a link, fix it with a second scoped
  `update` run. Never hand-edit generated pages or claims files.

- [ ] **3. Review, verify, close out.**
  **Owner:** orchestrator; fresh reviewer.
  **Required Skills:** `shared/skills/code-review/SKILL.md`.
  Map BF-H1 to BF-H4 and BF-I1 to BF-I2 to their evidence in the closeout
  log.

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

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
