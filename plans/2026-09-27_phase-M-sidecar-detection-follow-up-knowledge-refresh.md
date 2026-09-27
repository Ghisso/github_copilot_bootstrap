---
name: 2026-09-27_phase-M-sidecar-detection-follow-up-knowledge-refresh
type: small-plan
parent_plan: consumer-sidecar-bootstrap-overlay
phase_index: 13
status: planned
closeout_session_log:
---

# Small Plan: Phase M — Sidecar Detection Follow-up Knowledge Refresh

## Scope

This is the big plan's new final knowledge-refresh phase after the third
reopen (Decision 21, and the reopening procedure in
`shared/policies/workflow.instructions.md`). It follows the
Knowledge-Refresh Final Phase rule in the same file. Phase K refreshed
OpenWiki before Phase L changed how the installer and the sidecar handle:

- full-install evidence when `.claude` is tracked in any form;
- the fresh-default refusals (subfolder, linked worktree, bare, file);
- tracked entries under a bridge path;
- precedence for dropped skills;
- frontmatter parsing and alias identity in the name scans;
- retained names with backslashes and the order of user lines;
- the pending ownership record and crash convergence across versions;
- file modes, `fsync`, writability preflight, clean aborts, and the lock;
- report wording and empty-folder cleanup after uninstall.

Refresh the generated pages, then run the standing final-phase audit of
stale claims.

Add no implementation scope unless the audit exposes a concrete defect.

Known stale generated content after Phase L:

- `openwiki/operations/sidecar-overlay.md`: the mode-detection evidence
  list, the classification rows (bridge folders, dropped skills, the
  pending-record row), the alias rule, the exclude-block rendering order,
  retained-name rules, the write order (pending record, lock, mode
  preservation), and the uninstall exit-1 cases.
- `openwiki/operations/install-ownership-and-runtime-checks.md`: the
  full-evidence definition, the fresh-default refusals, the `--uninstall`
  target checks, and the `git`-missing abort.
- `openwiki/workflows/lifecycle-and-task-lanes.md`: only if Phase L
  touched a lifecycle claim (it is not expected to).

### Required Skills

- `shared/skills/knowledge-refresh/SKILL.md`
- `shared/skills/documentation/SKILL.md`
- `shared/skills/humanize/SKILL.md`
- `shared/skills/learn/SKILL.md`
- `shared/skills/ponytail/SKILL.md` — `full`, only for a required code correction

## Steps

- [ ] **1. Refresh OpenWiki.**
  - **Owner:** `orchestrator`. Only the main session has the `openwiki` MCP
    tools (MEMORY lesson from Phase E).
  - Follow `.claude/skills/knowledge-refresh/SKILL.md`: call OpenWiki's own
    MCP tools with `mode: "update"`. Never run an init, and never create a
    scheduled workflow.
  - Check the `openwiki` MCP server with `/mcp` first. A connection timeout
    right after WSL boots is a cold start, so reconnect. A provider or
    authentication failure blocks this phase until it is fixed.
  - Every stale or unresolved claim the run shows gets an explicit decision.
    For each page being rewritten, inspect its full claim set, and revise
    current claims whose line ranges moved (MEMORY lesson from Phase I).
    Map every cited range from the recorded base to the current file and
    check the text there (MEMORY lesson from Phase K).
  - Let no other agent edit tracked files while the run is open (MEMORY
    lesson from Phase K): run step 3 only after `openwiki_finish`.

- [ ] **2. Review the generated diff.**
  - **Owner:** `orchestrator`
  - Never hand-edit a generated page outside the page loop. Never stage
    `openwiki/.run.json`. Confirm that `AGENTS.md` and `CLAUDE.md` are
    unchanged after `openwiki_begin`.
  - Check that the sidecar and install-ownership pages describe:
    - tracked `.claude` as team config in every form;
    - the fresh-default refusals;
    - the bridge index boundary and dropped-skill precedence;
    - the alias-by-identity rule;
    - user-line order and backslash names;
    - the pending ownership record and the lock;
    - the uninstall exit-1 cases and the empty-folder cleanup.

- [ ] **3. Audit stale claims.**
  - **Owner:** `documenter`, after step 1 has finished.
  - Surfaces: `README.md`, `docs/architecture.md`, `docs/target-mapping.md`,
    `docs/runtime-checks.md`, `docs/smoke-tests.md`,
    `docs/sidecar-provider-contract.md`, and `shared/policies/`. Also:
    - skills that describe installer ownership or plan structure;
    - `shared/templates/plan-big.md` and `plan-small.md`;
    - agent prompts that mention plans or the installer;
    - the docstrings and `--help` text of `scripts/install_bootstrap.py`,
      `scripts/update_consumers.py`, and `scripts/sidecar_overlay.py`;
    - `.claude/instructions/project-context.instructions.md`;
    - root guidance;
    - `.claude/MEMORY.md` (report only; the orchestrator edits it).
  - Topics: every item in the Scope list above, plus any claim this plan
    or earlier work invalidated.
  - Leave dated records unchanged: archived plans, closed session logs,
    `docs/2026-*`, and the five review reports.
  - Record every surface and its outcome under
    `## Stale-claims surfaces checked` in the closeout session log.

- [ ] **4. Record reusable lessons only.**
  - **Owner:** `orchestrator`
  - Correct or remove any MEMORY entry that Phase L made wrong. Do not store
    transient phase details.

- [ ] **5. Complete the final lifecycle checks.**
  - **Owner:** `orchestrator`
  - Run verification, review, and closeout as the workflow requires, with
    `verify.py phase` and closeout step 4 in the foreground. This is the
    final phase, so its closeout meets the strict terminal gates. The big
    plan becomes `complete` after its commit.

## Acceptance Criteria

- The generated knowledge layer reflects Phase L, and no generated page is
  hand-edited outside the page loop.
- No live-advice surface contradicts Decisions 48-58.
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
phase uses the full set, as Phases E, I, and K did:

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
