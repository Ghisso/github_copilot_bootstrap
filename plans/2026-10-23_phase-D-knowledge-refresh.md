---
name: 2026-10-23_phase-D-knowledge-refresh
type: small-plan
parent_plan: state-sync-safety-fixes
phase_index: 4
status: complete
closeout_session_log: .claude/session_logs/2026-10-23_state-sync-safety-fixes-phase-D.md
---

# Small Plan: Knowledge Refresh and Stale-Claims Audit

## Scope

Refresh the enabled OpenWiki layer after phases A to C have settled, and audit live guidance for claims that this plan or earlier work made stale. OpenWiki pages are derived context, not authority; only OpenWiki's own MCP tools change them. Requirement: REQ-012.

## Steps

- [x] **1. Audit live advice for stale claims.**
  - Owner: `documenter` for `README.md`, `docs/`, and `shared/` text; orchestrator for `.claude/MEMORY.md`.
  - Required Skills: `.claude/skills/documentation/SKILL.md`.
  - Surfaces: root guidance, `README.md`, `docs/` (at least `runtime-checks.md`, `smoke-tests.md`, `architecture.md`, `target-mapping.md`), `shared/policies/`, `shared/skills/` (at least `commit`, `safe-consumer-bootstrap-refresh`, `knowledge-refresh`), `shared/agents/`, `shared/templates/`, `shared/review-profiles/`, state READMEs, and `.claude/MEMORY.md`.
  - Claims to look for: a current-pull recovery of "abort, then `--quit`"; advice to `rebase --quit` an ambiguous rebase; any statement that every checkpoint commits whatever is uncommitted, without the unfinished-operation exception; any statement that a killed sync always leaves its settings copy; a request to create `~/.openwiki` by hand; `status` output lists missing `merge:` or `lock:`; the MEMORY entries about state-sync recovery, `cmd_setup`, and the untrack functions; and `openwiki/operations/git-backed-ai-state-sync.md`, whose line 84 names `untrack_local_settings` (the refresh in step 2 must correct it).
  - Correct or supersede each live claim. Leave dated records unchanged: `docs/2026-08-09-state-sync-rebase-recovery.md`, `plans/plan-git-state-sync.md`, `plans/adr-002-git-backed-state-sync.md`, archived plans, and closed session logs, unless an entry would actively mislead a reader and no receipt binds its log.
  - Record each audited surface and its outcome under the exact heading `## Stale-claims surfaces checked` in this phase's closeout session log.

- [x] **2. Refresh OpenWiki through its own tools.**
  - Owner: orchestrator (the OpenWiki MCP tools and their guard hook run in the main session).
  - Required Skills: `.claude/skills/knowledge-refresh/SKILL.md`, `.claude/skills/openwiki/SKILL.md`.
  - Call `openwiki_begin` with `mode: "update"`, complete the page-job lifecycle, and require `openwiki_finish` to return `complete`. Follow the skill's restore check after `openwiki_begin`.
  - Inspect the generated diff, especially `openwiki/operations/git-backed-ai-state-sync.md` and any page that describes the devcontainer mounts or the root-adapter restorer. Never hand-edit a generated page, a `.claims` file, or the root snippet. A provider or authentication failure blocks this phase until it is fixed and retried; never skip the refresh.

- [x] **3. Finish the normal control-plane closeout.**
  - Owner: orchestrator.
  - Before CLOSEOUT step 2, run `uv run python scripts/generate_targets.py --all` and then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`. Record lessons in `.claude/MEMORY.md` only when they are reusable.

- [x] **4. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `config`, `documentation`. The findings report binds the whole branch diff against `dev`, so it keeps every earlier phase's profiles.
  - Focus: the refreshed pages and edited docs match the code; no stale claim from the list above survives on a live surface.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- Read the refreshed `openwiki/operations/git-backed-ai-state-sync.md` against `shared/hooks/scripts/state-sync.sh` and record any claim that does not match the code.

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
