---
name: 2026-10-17_phase-E-gate-repair-knowledge-refresh
type: small-plan
parent_plan: gate-repair
phase_index: 5
status: in-progress
closeout_session_log:
---

# Small Plan: Gate Repair Knowledge Refresh

## Scope

Finish the plan with the required knowledge refresh and the final
stale-claims audit (GR-012), and confirm the plan's boundaries held
(GR-013). This phase changes no executable behavior. It brings the live
advice and the generated wiki in line with Phases A–D, and completes the
per-client parity table in priority order: Claude Code, Codex, GitHub
Copilot, Antigravity.

## Steps

- [ ] **1. Run the final stale-claims audit (GR-012).**
  **Owner:** orchestrator, with a documenter for prose changes.
  **Files:** as the audit finds; at least `docs/target-mapping.md`,
  `shared/skills/ponytail/SKILL.md`,
  `shared/policies/workspace.instructions.md`, and `.claude/MEMORY.md`.
  **Required Skills:** `shared/skills/documentation/SKILL.md`,
  `shared/skills/ponytail/SKILL.md` (full).
  Sweep root guidance, `docs/`, shared policies, skills, templates, agents,
  review profiles, state READMEs, and `.claude/MEMORY.md` for claims this
  plan or earlier work made false. Required items:
  - the parity table in `docs/target-mapping.md` covers every GR fix for all
    four clients, with each gap and its evidence;
  - the Ponytail "mandatory" (`shared/skills/ponytail/SKILL.md:25`) versus
    "optional for low-complexity work"
    (`shared/policies/workspace.instructions.md:138-142`) wording matches what
    the gate now enforces;
  - the MEMORY `[LEARN:planning]` entry saying subagent tool lists exclude
    project MCP servers is superseded by the 2026-10-17 probe result (servers
    present at session start are granted);
  - `docs/smoke-tests.md`, `shared/policies/tool-routing.instructions.md`, and
    `shared/policies/quality-and-testing.instructions.md` agree with Phases
    A–D;
  - the follow-ups this plan left open are recorded where the next planner
    will find them (the audit exploration's "out of scope" list or a new
    dated note): agent definition files are unprotected in all four clients,
    including Codex `sandbox_mode` in `.codex/agents/*.toml`, which Codex ignores entirely (official Codex subagents docs and source, 2026-10-17), so the read-only Codex roles run with the parent session's sandbox; upstream's
    `antigravity-cli` Context Mode hooks are not wired; GR-002 enforces the
    Task Lanes profiles for control-plane paths but not for every multi-file
    diff.
  Leave dated records (archived plans, dated docs, closed session logs, the
  2026-10-17 audit exploration) unchanged. Record every surface and its
  outcome under `## Stale-claims surfaces checked` in the closeout log.

- [ ] **2. Refresh the OpenWiki knowledge layer.**
  **Owner:** orchestrator on the main thread, as the knowledge-refresh
  skill requires.
  **Required Skills:** `shared/skills/knowledge-refresh/SKILL.md` and
  OpenWiki's own `openwiki` skill.
  Run one managed refresh after all source edits. Inspect the generated diff.
  Never hand-edit generated pages or Claims sidecars.

- [ ] **3. Review, verify, close out.**
  **Owner:** orchestrator; fresh reviewer.
  **Required Skills:** `shared/skills/code-review/SKILL.md`.
  Map GR-001 to GR-013 to evidence in the closeout log.

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
