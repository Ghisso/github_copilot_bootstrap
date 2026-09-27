---
name: 2026-09-27_phase-A-workflow-profile-provider-evidence
type: small-plan
parent_plan: sidecar-workflow-profile
phase_index: 1
status: planned
closeout_session_log:
---

# Small Plan: Phase A — Workflow Profile Provider Evidence

## Scope

Record, per client, whether the unit kinds the workflow profile wants to
ship are discovered when they are Git-ignored files inside a repository
whose `.claude/` is team-tracked. Freeze the profile's write roots, read
roots, and client coverage on that evidence. This phase changes one
evidence document and no code (big plan Decisions 7, 9, and 12).

### Required Skills

- `shared/skills/documentation/SKILL.md`
- `shared/skills/integration-gate-spike/SKILL.md` — every client run is a real invocation of a third-party client
- `shared/skills/humanize/SKILL.md`

## Primary Files

- `docs/sidecar-provider-contract.md` — new section "Workflow profile
  evidence" with its own fixture recipe, operator checklist, and frozen
  matrix; the existing skills-profile sections stay unchanged.

## Steps

- [ ] **1. Documented starting point.**
  - **Owner:** `documenter`
  - For Claude Code, Codex, Copilot in VS Code, and Antigravity, cite the
    vendor page and the date checked for: where custom agents or subagents
    are discovered (`.claude/agents/`, `.github/agents/`, `.codex/agents/`,
    `.agents/agents/`); whether discovery needs a config entry (`.codex/config.toml`
    `[agents]` or `[features.multi_agent_v2]`); whether several
    `.claude/rules/*.md` files without `paths` all load; whether an
    instructions file under `.github/instructions/` with `applyTo: "**"`
    loads; and whether any of these is affected by the file being ignored.
  - Record each answer at the `documented` or `source` tier, never as
    support.

- [ ] **2. Fixture recipe.**
  - **Owner:** `documenter`
  - A throwaway repository that tracks `.claude/settings.json` (with an
    unrelated setting), `.claude/skills/team-skill/SKILL.md`,
    `.claude/agents/team-agent.md`, `.claude/rules/team.md`, and
    `.github/instructions/team.instructions.md`, plus code. Then, as
    ignored files placed by hand and hidden through `info/exclude` lines
    exactly as the installer would write them: `.claude/agents/probe-agent.md`
    (a subagent that answers with a fixed token), two rules files
    `.claude/rules/ai-bootstrap-a.md` and `ai-bootstrap-b.md` (each
    injecting a distinct token), `.github/agents/probe-agent.agent.md`,
    `.github/instructions/ai-bootstrap-workflow.instructions.md`, and, for
    Codex, `.codex/agents/probe-agent.toml` with no `.codex/config.toml`.
  - The recipe states `git status --porcelain --untracked-files=all` must
    be empty after placement.

- [ ] **3. Native runs.**
  - **Owner:** `orchestrator` (the clients run on the host)
  - For each installed client, run the fixture and record: does the probe
    agent appear and answer; do both rules tokens appear; does the
    instructions token appear; does the team agent still work. Record the
    client version and date. A client not installed on the host is
    recorded as unverified, never as unsupported.

- [ ] **4. Frozen matrix and decisions.**
  - **Owner:** `documenter`, with the orchestrator's confirmation
  - Write the matrix: per client, per unit kind, `native-run`,
    `documented`, or `unverified`. Freeze the profile's write roots
    (Decision 9), the read roots for collision checks, and the client
    coverage (Decision 7). State the decision-gate result for Phase B.

## Acceptance Criteria

- The new section carries a documented row per client and unit kind, a
  reproducible fixture recipe, the operator checklist, and a dated frozen
  matrix.
- Every claim above the `documented` tier names a client version and date.
- The write roots, read roots, and client coverage for the profile are
  frozen in one table that Phases C and D copy into constants.
- The decision gate for Phase B is stated with its evidence.

## Verification

```bash
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- The native client runs in step 3 happen on the host where the clients
  are installed; their results are recorded in the evidence document and
  in the closeout session log.

## Review Profiles

- `documentation`
- `architecture`
- `security`

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
