---
name: 2026-09-26_phase-K-sidecar-follow-up-knowledge-refresh
type: small-plan
parent_plan: consumer-sidecar-bootstrap-overlay
phase_index: 11
status: planned
---

# Small Plan: Phase K — Sidecar Follow-up Knowledge Refresh

## Scope

This is the big plan's new final knowledge-refresh phase after the second
reopen (Decision 21, and the reopening procedure in
`shared/policies/workflow.instructions.md`). It follows the
Knowledge-Refresh Final Phase rule in the same file. Phase I refreshed
OpenWiki before Phase J changed how the sidecar handles:

- unit boundaries;
- snapshot completeness;
- the uninstall write order;
- the ignore gate;
- symlink handling in the name scans;
- exclude-line splitting;
- reports and remedies;
- the settled-refresh identity check.

Refresh the generated pages, then run the standing final-phase audit of
stale claims.

Add no implementation scope unless the audit exposes a concrete defect.

Known stale generated content after Phase J:

- `openwiki/operations/sidecar-overlay.md`:
  - its preflight item 7 and classification text describe structural-only
    boundary checks, not the unit-level rule (a recorded or listed nested
    repository is refused, a personal clone is foreign, a gitlink is
    never touched);
  - its gate text lacks the symlink-unit spelling and the uninstall rule
    (only kept lines are gated);
  - its uninstall section describes the removed conflict-only gates;
  - its report table says "skips at every root" for a conflict copy.
- `openwiki/workflows/lifecycle-and-task-lanes.md`: its knowledge-refresh
  exemption needs the new sibling identity rule, which Phase J also writes
  into the Termination paragraph of `shared/policies/workflow.instructions.md`.
- `openwiki/operations/install-ownership-and-runtime-checks.md`: the
  `--mode full` refusal text and the tracked-path warning.

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

- [ ] **2. Review the generated diff.**
  - **Owner:** `orchestrator`
  - Never hand-edit a generated page outside the page loop. Never stage
    `openwiki/.run.json`. Confirm that `AGENTS.md` and `CLAUDE.md` are
    unchanged after `openwiki_begin`.
  - Check that the sidecar page describes:
    - the unit-level boundary rule;
    - incomplete units;
    - uninstall on the install's write order;
    - the one gate over every kept line;
    - the one path-identity rule;
    - the conflict reports.

- [ ] **3. Audit stale claims.**
  - **Owner:** `documenter`
  - Surfaces: `README.md`, `docs/architecture.md`, `docs/target-mapping.md`,
    `docs/runtime-checks.md`, `docs/smoke-tests.md`,
    `docs/sidecar-provider-contract.md`, and `shared/policies/`. Also:
    - skills that describe installer ownership or plan structure;
    - `shared/templates/plan-big.md` and `plan-small.md`;
    - agent prompts that mention plans or the installer;
    - the docstrings and `--help` text of `scripts/install_bootstrap.py`,
      `scripts/update_consumers.py`, `scripts/sidecar_overlay.py`, and
      `scripts/validate_plan_frontmatter.py`;
    - `.claude/instructions/project-context.instructions.md`;
    - root guidance;
    - `.claude/MEMORY.md` (report only; the orchestrator edits it).
  - Topics:
    - nested repositories and submodules at units;
    - incomplete units and special files;
    - uninstall after a profile change, and preserve conflicts;
    - what the gate covers;
    - symlinked read folders and aliases;
    - case variants at write roots;
    - line splitting;
    - retained files of dropped skills;
    - report wording;
    - the settled-refresh identity rule;
    - "agent-harness path" wording;
    - any claim this plan or earlier work invalidated.
  - Leave dated records unchanged: archived plans, closed session logs,
    `docs/2026-*`, and the four review reports.
  - Record every surface and its outcome under
    `## Stale-claims surfaces checked` in the closeout session log.

- [ ] **4. Record reusable lessons only.**
  - **Owner:** `orchestrator`
  - Correct or remove any MEMORY entry that Phase J made wrong. Do not store
    transient phase details.

- [ ] **5. Complete the final lifecycle checks.**
  - **Owner:** `orchestrator`
  - Run verification, review, and closeout as the workflow requires, with
    `verify.py phase` and closeout step 4 in the foreground. This is the
    final phase, so its closeout meets the strict terminal gates. The big
    plan becomes `complete` after its commit.

## Acceptance Criteria

- The generated knowledge layer reflects Phase J, and no generated page is
  hand-edited outside the page loop.
- No live-advice surface contradicts Decisions 37-47.
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
phase uses the full set, as Phases E and I did:

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
