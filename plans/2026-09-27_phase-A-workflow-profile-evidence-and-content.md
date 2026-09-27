---
name: 2026-09-27_phase-A-workflow-profile-evidence-and-content
type: small-plan
parent_plan: sidecar-workflow-profile
phase_index: 1
status: complete
closeout_session_log: .claude/session_logs/2026-09-27_workflow-profile-phase-A-evidence-and-content.md
---

# Small Plan: Phase A — Workflow Profile Evidence and Relaxed Content

## Scope

Two document-only jobs in one phase. First, record per client whether the
unit kinds the workflow profile wants to ship are discovered when they are
Git-ignored files inside a repository whose `.claude/` is team-tracked, and
freeze the profile's write roots, read roots, and client coverage on that
evidence (big plan Decisions 7, 9, and 12). Second, author everything the
profile ships that is text: the relaxed instruction set, the per-agent
workflow supplements, the skill denylist, and the state seeds, under
`shared/sidecar/workflow/` (Decisions 4, 5, 6, and 8). No Python changes.

The evidence comes first. If step 3 finds that Claude Code does not load an
ignored `.claude/agents/<id>.md` and an ignored `.claude/rules/ai-bootstrap-*.md`
from a team-tracked `.claude/`, stop at step 4, record the result, and
cancel Phases B and C (the big plan's decision gate). The content steps
run only past that gate.

### Required Skills

- `shared/skills/documentation/SKILL.md`
- `shared/skills/integration-gate-spike/SKILL.md` — every client run is a real invocation of a third-party client
- `shared/skills/humanize/SKILL.md`
- `shared/skills/ponytail/SKILL.md` — `full`, for the authored content: the fewest rules that work

## Primary Files

- `docs/sidecar-provider-contract.md` — new section "Workflow profile
  evidence"; the existing sections stay unchanged.
- `shared/sidecar/workflow/rules/workflow.md`, `reporting.md`,
  `tool-routing.md`; `shared/sidecar/workflow/instructions.md`;
  `shared/sidecar/workflow/skills.txt`; `shared/sidecar/workflow/state/`
  (`MEMORY.md` and one `README.md` per state folder) — all created.
- `shared/agents/<id>/workflow-supplement.md` for `orchestrator`,
  `planner`, `coder`, `reviewer`, `documenter` — created.

## Steps

- [x] **1. Documented starting point.**
  - **Owner:** `documenter`
  - For Claude Code, Codex, Copilot in VS Code, and Antigravity, cite the
    vendor page and the date checked for: where custom agents are
    discovered (`.claude/agents/`, `.github/agents/`, `.codex/agents/`,
    `.agents/agents/`); whether discovery needs a config entry
    (`.codex/config.toml` `[agents]` or `[features.multi_agent_v2]`);
    whether several `.claude/rules/*.md` files without `paths` all load;
    whether an instructions file under `.github/instructions/` with
    `applyTo: "**"` loads; and whether being Git-ignored changes any of
    it. Record each answer at the `documented` or `source` tier.

- [x] **2. Fixture recipe.**
  - **Owner:** `documenter`
  - A throwaway repository that tracks `.claude/settings.json` (with an
    unrelated setting), `.claude/skills/team-skill/SKILL.md`,
    `.claude/agents/team-agent.md`, `.claude/rules/team.md`,
    `.github/instructions/team.instructions.md`, and code. Then, as ignored
    files hidden through `info/exclude` lines exactly as the installer
    writes them: `.claude/agents/probe-agent.md` (answers with a fixed
    token), `.claude/rules/ai-bootstrap-a.md` and `ai-bootstrap-b.md`
    (distinct tokens), `.github/agents/probe-agent.agent.md`,
    `.github/instructions/ai-bootstrap-workflow.instructions.md`, and for
    Codex `.codex/agents/probe-agent.toml` with no `.codex/config.toml`.
    `git status --porcelain --untracked-files=all` must be empty after
    placement.

- [x] **3. Native runs.**
  - **Owner:** `orchestrator` (the clients run on the host)
  - For each installed client: does the probe agent appear and answer; do
    both rule tokens appear; does the instructions token appear; does the
    team agent still work. Record client version and date. A client not
    installed is recorded as unverified.

- [x] **4. Frozen matrix and the gate.**
  - **Owner:** `documenter`, confirmed by the orchestrator
  - The matrix per client and unit kind (`native-run`, `documented`,
    `unverified`); the frozen write roots, read roots, and client coverage
    in one table that Phase B copies into constants; the gate result.

- [x] **5. The relaxed workflow rule.**
  - **Owner:** `documenter`
  - `workflow.md`, under 120 lines: read `.claude/ai-bootstrap/MEMORY.md`
    before non-trivial work; for a task spanning several files or
    decisions, ask the planner for a plan under
    `.claude/ai-bootstrap/plans/` using the templates, otherwise implement
    directly; run the project's own test, lint, and type commands, named
    from the repository's own docs; review any non-trivial diff with the
    reviewer agent, whose report goes to
    `.claude/ai-bootstrap/quality_reports/`; at the end write a session
    log under `.claude/ai-bootstrap/session_logs/` and record reusable
    lessons in `MEMORY.md`. State that nothing here blocks a commit and
    that the repository's own guidance wins on any conflict.
  - Must not mention hooks, receipts, findings JSON, branches, the nested
    repository, `verify.py`, `record_findings`, MCP servers, Context Mode,
    or OpenWiki.

- [x] **6. Reporting and tool-routing rules, and the Copilot body.**
  - **Owner:** `documenter`
  - `reporting.md`: the plain-language policy from
    `shared/policies/agent-reporting.instructions.md` without hook
    references. `tool-routing.md`: direct reads for known files, exact
    search for literals, semantic search when the client has it; no
    Semble, Context Mode, or OpenWiki. `instructions.md`: the same
    content condensed for the single Copilot instructions file.

- [x] **7. Agent workflow prompts (Decision 6 as amended 2026-09-27).**
  - **Owner:** `documenter`
  - One complete `workflow-prompt.md` per shipped agent, self-contained
    and never merged with the canonical prompt: the orchestrator runs the
    relaxed loop and delegates and never gates; the planner writes plans
    with the two templates and never creates branches; the coder
    implements and runs the project's own checks; the reviewer writes a
    Markdown report with severity sections to the quality-reports folder,
    no JSON; the documenter updates docs and the state folder. Each names
    only the profile's rule files, the templates, the state paths, and
    skills the profile ships, and carries no reference to the full
    install. A first draft as a supplement replacing canonical sections
    was abandoned after two review rounds kept finding dangling
    references.

- [x] **8. Skill denylist and state seeds.**
  - **Owner:** `documenter`, checked by the orchestrator
  - Walk every `visibility: public` skill; deny each that needs the full
    install (`commit`, `context-status`, `knowledge-refresh`,
    `safe-consumer-bootstrap-refresh`, `setup-project`, `deep-audit`,
    `code-review` if it names `record_findings`, `run-tests` if it names
    `verify.py`, and any other whose text names a forbidden token), one
    reason each. `MEMORY.md` seed: the headings of `shared/MEMORY.md` with
    no entries. One README per state folder saying what goes there and
    that the folder is personal, Git-ignored, and kept by `--uninstall`.

## Acceptance Criteria

- The evidence section carries a documented row per client and unit
  kind, a reproducible fixture recipe, dated native-run results with
  client versions, the frozen tables, and the gate result.
- Every authored file reads without a forbidden token (`.claude/hooks/`,
  `.claude/scripts/`, `verify.py`, `record_findings`, `mcp__`, `ctx_`,
  `openwiki`, `settings.json`, `core.hooksPath`, `ai-state`).
- The workflow rule fits one screen and names only paths under
  `.claude/ai-bootstrap/`; the denylist has one reason per denied skill.

## Verification

```bash
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/validate_targets.py
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

- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
