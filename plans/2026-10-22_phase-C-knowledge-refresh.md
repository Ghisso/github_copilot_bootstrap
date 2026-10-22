---
name: 2026-10-22_phase-C-knowledge-refresh
type: small-plan
parent_plan: sidecar-onboard-and-validator
phase_index: 3
status: complete
closeout_session_log: .claude/session_logs/2026-10-23_sidecar-onboard-and-validator-phase-C.md
---

# Small Plan: Knowledge Refresh and Stale-Claims Audit

## Scope

Refresh the enabled OpenWiki layer after the sidecar behavior and validator change have settled. Audit current human-authored guidance for claims invalidated by this plan. Generated OpenWiki pages remain derived context and are changed only by OpenWiki's own tools.

## Steps

- [x] **1. Audit live advice.** Inspect root guidance, `README.md`, `docs/`, shared policies, skills, templates, agents, review profiles, state READMEs, and `.claude/MEMORY.md` for claims that this plan or earlier work invalidated, including the sidecar project-context path and new team conventions section. Correct or supersede active claims; leave dated plans, design narratives, and closed logs untouched unless an entry would actively mislead and no receipt binds it. In this phase's closeout session log, record each audited surface and outcome under the exact heading `## Stale-claims surfaces checked`.
- [x] **2. Refresh OpenWiki through its own tools.** Follow `.claude/skills/knowledge-refresh/SKILL.md` and the OpenWiki skill. Start `openwiki_begin` with `mode: "update"`, complete the page-job lifecycle, and require `openwiki_finish` to return `complete`. Inspect the generated diff for the workflow skill count and sidecar behavior. Do not hand-edit a generated page, `.claims` file, or root snippet; use the documented restore check after `openwiki_begin`.
- [x] **3. Finish the normal control-plane closeout.** Run the required reviews, update memory only for a reusable lesson, record findings and the complete session log, stage the intended outer files, and run the canonical phase and closeout verification before committing and normally pushing this phase.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- Inspect the rendered OpenWiki sidecar page and compare its current count and `onboard` description with `scripts/runtime_ownership.py` and the new skill source.

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
