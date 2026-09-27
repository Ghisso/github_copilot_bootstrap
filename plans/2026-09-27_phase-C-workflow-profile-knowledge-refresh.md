---
name: 2026-09-27_phase-C-workflow-profile-knowledge-refresh
type: small-plan
parent_plan: sidecar-workflow-profile
phase_index: 3
status: planned
closeout_session_log:
---

# Small Plan: Phase C — Workflow Profile Knowledge Refresh

## Scope

The big plan's final knowledge-refresh phase, following the
Knowledge-Refresh Final Phase rule in
`shared/policies/workflow.instructions.md`. Refresh the generated OpenWiki
pages after Phases A and B, then run the standing final-phase audit of
stale claims. Add no implementation scope unless the audit exposes a
concrete defect.

Expected stale content: `openwiki/operations/sidecar-overlay.md` (profiles,
unit kinds, the state folder, `--purge-state`, `--backup-state`),
`openwiki/architecture/source-generated-consumer-layout.md` (the two
profile trees and the per-profile validator), and
`openwiki/operations/install-ownership-and-runtime-checks.md` (the
`--profile` flag and the updater's reuse).

### Required Skills

- `shared/skills/knowledge-refresh/SKILL.md`
- `shared/skills/documentation/SKILL.md`
- `shared/skills/humanize/SKILL.md`
- `shared/skills/learn/SKILL.md`

## Steps

- [ ] **1. Refresh OpenWiki.**
  - **Owner:** `orchestrator`
  - Follow `.claude/skills/knowledge-refresh/SKILL.md` with `mode: "update"`.
    For every page rewritten, map each cited range of every file the page
    cites from the recorded base to the current file before submitting
    (MEMORY lessons from the first sidecar plan's Phases K and M). Let no
    other agent edit tracked files while the run is open.

- [ ] **2. Review the generated diff.**
  - **Owner:** `orchestrator`
  - Never hand-edit a generated page outside the page loop; never stage
    `openwiki/.run.json`; confirm `AGENTS.md` and `CLAUDE.md` unchanged.

- [ ] **3. Audit stale claims.**
  - **Owner:** `documenter`, after `openwiki_finish`
  - Surfaces: `README.md`, `docs/`, `shared/policies/`, the skills that
    describe installer ownership, the templates, agent prompts, the
    docstrings and `--help` of the installer, the updater, and
    `sidecar_overlay.py`, `.claude/instructions/project-context.instructions.md`,
    root guidance, and `.claude/MEMORY.md` (report only). Record every
    surface and outcome under `## Stale-claims surfaces checked` in the
    closeout session log.

- [ ] **4. Record reusable lessons only.**
  - **Owner:** `orchestrator`

- [ ] **5. Complete the final lifecycle checks.**
  - **Owner:** `orchestrator`
  - This is the final phase; its closeout meets the strict terminal gates,
    and the big plan becomes `complete` after its commit.

## Acceptance Criteria

- The generated knowledge layer reflects Phases A and B.
- No live-advice surface contradicts the big plan's decisions.
- The closeout session log has a non-empty `## Stale-claims surfaces checked`
  section.

## Verification

```bash
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Review Profiles

- `documentation`
- `code`
- `architecture`
- `security`
- `tests`
- `ponytail`

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT).

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
