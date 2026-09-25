---
name: 2026-09-25_phase-I-sidecar-hardening-knowledge-refresh
type: small-plan
parent_plan: consumer-sidecar-bootstrap-overlay
phase_index: 9
status: planned
---

# Small Plan: Phase I — Sidecar Hardening Knowledge Refresh

## Scope

The big plan's new final knowledge-refresh phase, as defined by the
Knowledge-Refresh Final Phase rule in `shared/policies/workflow.instructions.md`
and by big plan Decision 21. Phase E refreshed OpenWiki before Phases F-H
changed the workflow rule, the planner, preflight, and the docs, so the
generated pages are stale again. Refresh them, then run the standing
final-phase audit of stale claims.

Add no implementation scope unless the audit exposes a concrete defect.

Known stale generated content (round 2, S17): OpenWiki claims `229e75d4`
("aborts before any write … manifest is invalid") and `e46454b4` ("skipped
at every write root"). Also stale: the manual removal steps in
`openwiki/operations/sidecar-overlay.md`, and the "or has no commits" wording
in `openwiki/operations/install-ownership-and-runtime-checks.md`.

### Required Skills

- `shared/skills/knowledge-refresh/SKILL.md`
- `shared/skills/documentation/SKILL.md`
- `shared/skills/humanize/SKILL.md`
- `shared/skills/learn/SKILL.md`
- `shared/skills/ponytail/SKILL.md` — `full`, only for a required code correction

## Steps

- [ ] **1. Refresh OpenWiki.**
  - **Owner:** `documenter`
  - Follow `.claude/skills/knowledge-refresh/SKILL.md`: call OpenWiki's own
    MCP tools with `mode: "update"`. Never run an init, and never create a
    scheduled workflow.
  - The `openwiki` MCP server must be connected first. Check it with `/mcp`.
    A connection timeout right after WSL boots is a cold start: reconnect
    with `/mcp`. A provider or authentication failure blocks this phase until
    it is fixed; it is never skipped.
  - Every stale claim the run shows must get an explicit decision: confirm,
    revise, or retract. Revise or retract the two known claims above
    against the Phase G and H code.

- [ ] **2. Review the generated diff.**
  - **Owner:** `documenter`
  - Treat generated pages as descriptive context, not policy. Source, tests,
    and policies stay authoritative.
  - Never hand-edit a generated page. Never stage `openwiki/.run.json`.
  - Check that `openwiki/operations/sidecar-overlay.md` describes
    `--uninstall`, the preserved folder, the taken-skill rule, and the new
    refusals, and no longer gives manual removal steps that delete personal
    files.

- [ ] **3. Audit stale claims.**
  - **Owner:** `documenter`
  - Surfaces: `README.md`, `docs/architecture.md`, `docs/target-mapping.md`,
    `docs/runtime-checks.md`, `docs/smoke-tests.md`,
    `docs/sidecar-provider-contract.md`, `shared/policies/` (including the new
    reopening procedure and the Termination text from Phase F), skills that
    describe installer ownership (including
    `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md`), the docstrings
    and `--help` text of `scripts/install_bootstrap.py` and
    `scripts/update_consumers.py`,
    `.claude/instructions/project-context.instructions.md`, root guidance,
    and `.claude/MEMORY.md`.
  - Topics:
    - reopening a completed big plan, and whether a knowledge-refresh phase
      must be unique and last;
    - sidecar ownership proof and team precedence;
    - the preserved folder and uninstall;
    - removal steps, and hidden files being overwritten by pulls;
    - mode detection with submodules and Git errors;
    - refusals before any write;
    - bytes-safe names;
    - source completeness;
    - the `bootstrap_commit` field;
    - any claim this plan or earlier work invalidated.
  - Leave dated records unchanged: archived plans, closed session logs, and
    the two review reports.
  - Record every surface and its outcome under
    `## Stale-claims surfaces checked` in the closeout session log.

- [ ] **4. Record reusable lessons only.**
  - **Owner:** `documenter`
  - Run LEARN for reusable implementation knowledge. Correct or remove any
    MEMORY entry that Phases F-H made wrong, for example the sidecar entries
    that describe the old collision loop or manual removal. Do not store
    transient phase details.

- [ ] **5. Complete the final lifecycle checks.**
  - **Owner:** `orchestrator`
  - Run verification, review, and closeout as the workflow requires. This is
    the final phase: its closeout meets the strict terminal gates, and the
    big plan becomes `complete` after its commit.

## Acceptance Criteria

- The generated knowledge layer reflects Phases F-H, and no generated page is
  hand-edited.
- No live-advice surface contradicts the reopening procedure, team
  precedence, ownership proof, the preserved folder, uninstall, or the new
  refusals.
- The closeout session log has a non-empty `## Stale-claims surfaces checked`
  section.
- No unrelated feature scope is introduced.

## Verification

```bash
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Review Profiles

Every multi-file diff is control-plane/high-risk
(`shared/policies/workspace.instructions.md`, Review Profiles), so this
phase uses the full set, as Phase E did:

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
