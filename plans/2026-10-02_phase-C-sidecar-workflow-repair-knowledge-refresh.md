---
name: 2026-10-02_phase-C-sidecar-workflow-repair-knowledge-refresh
type: small-plan
parent_plan: sidecar-workflow-repair
phase_index: 3
status: complete
closeout_session_log: .claude/session_logs/2026-10-02_sidecar-workflow-repair-knowledge-refresh.md
---

# Small Plan: Sidecar Repair Knowledge Refresh

## Scope

Refresh the enabled OpenWiki layer after the repair and audit live advice
for the whole plan. This is the dedicated final phase required by the
Knowledge-Refresh Final Phase rule in
`shared/policies/workflow.instructions.md`. It carries no additional
feature or migration work.

### Required Skills

- `shared/skills/knowledge-refresh/SKILL.md`
- `.claude/skills/openwiki/SKILL.md` — OpenWiki's own tool lifecycle
- `shared/skills/documentation/SKILL.md`
- `shared/skills/humanize/SKILL.md`
- `shared/skills/learn/SKILL.md`
- `shared/skills/code-review/SKILL.md`

## Steps

- [x] **1. Refresh through OpenWiki's own MCP tools.**
  **Owner:** orchestrator.
  **Required Skills:** `shared/skills/knowledge-refresh/SKILL.md`,
  `.claude/skills/openwiki/SKILL.md`.
  Begin with `mode: "update"` and follow the resumable page-job lifecycle.
  Expected affected pages include `openwiki/operations/sidecar-overlay.md`,
  `openwiki/operations/install-ownership-and-runtime-checks.md`, and
  `openwiki/architecture/source-generated-consumer-layout.md`; let source
  changes and the returned jobs determine the actual set. Map all cited
  source ranges on each rewritten page, including unchanged claims whose
  lines moved. Allow no concurrent tracked-file edits while the run is open.
  Check root-adapter restoration immediately after begin, including an error
  result, and use the skill's guard restore command if needed. Resume a
  failed run; do not delete `openwiki/.run.json`, switch to init, or claim
  success until the tool lifecycle reports completion. Use only the skill's
  rebaseline procedure when its recorded base is unreachable.

- [x] **2. Inspect generated changes and audit all live advice.**
  **Owner:** documenter after the refresh completes; orchestrator owns memory.
  **Required Skills:** `shared/skills/documentation/SKILL.md`,
  `shared/skills/humanize/SKILL.md`, `shared/skills/learn/SKILL.md`.
  Check generated claims against source and native evidence. Never hand-edit
  generated pages or claim sidecars; use page jobs for corrections. Confirm
  the generated root snippet and `.run.json` will not enter a commit.
  Audit README, docs, root guidance, shared policies, skills, templates,
  agent prompts, review profiles, state READMEs, installer/updater help and
  comments, `.claude/instructions/project-context.instructions.md`, and
  `.claude/MEMORY.md`. Distinguish full-install `.claude` state from retired
  sidecar paths; do not globally replace every `.claude` reference. Correct
  or supersede live advice invalidated by this plan or prior work. Preserve
  dated review records, completed plans, and receipt-bound session logs.
  Record each surface and its outcome under the exact heading
  `## Stale-claims surfaces checked` in the closeout log. If a correction
  changes a source claim or citation range, refresh the affected page again
  rather than leaving the knowledge layer stale.

- [x] **3. Review and complete the terminal lifecycle.**
  **Owner:** reviewer, then orchestrator.
  **Required Skills:** `shared/skills/code-review/SKILL.md`,
  `shared/skills/learn/SKILL.md`.
  Review generated and authored changes with the profiles below. Record only
  reusable lessons, or the explicit no-lessons marker. Run deterministic
  checks and the canonical closeout sequence, including the final-phase
  documentation/memory audit. A provider failure blocks this phase without
  pretending the Python checks failed; report the actionable tool error.
  Complete the big plan only after all phase evidence and gates pass.

## Verification

```bash
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Record the OpenWiki MCP completion result and reviewed page list in the
  log. Successful refresh is required by policy; the MCP lifecycle is not
  a shell command for the deterministic verifier to rerun.

## Review Profiles

Load `.claude/review-profiles/documentation.md`,
`.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
and `.claude/review-profiles/ponytail.md`.

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT).

- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
