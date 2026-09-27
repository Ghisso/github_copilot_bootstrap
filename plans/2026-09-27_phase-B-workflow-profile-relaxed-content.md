---
name: 2026-09-27_phase-B-workflow-profile-relaxed-content
type: small-plan
parent_plan: sidecar-workflow-profile
phase_index: 2
status: planned
closeout_session_log:
---

# Small Plan: Phase B — Workflow Profile Relaxed Content

## Scope

Author everything the workflow profile ships that is text, not code: the
relaxed instruction set, the per-agent workflow supplements, the skill
denylist, and the state seeds. All of it lives under
`shared/sidecar/workflow/` and is rendered by Phase C. This phase writes no
Python (big plan Decisions 4, 5, 6, and 8).

### Required Skills

- `shared/skills/documentation/SKILL.md`
- `shared/skills/humanize/SKILL.md`
- `shared/skills/ponytail/SKILL.md` — `full`, for the authored content: the fewest rules that work

## Primary Files

- `shared/sidecar/workflow/rules/workflow.md`, `reporting.md`,
  `tool-routing.md` — the relaxed instruction set (create).
- `shared/sidecar/workflow/instructions.md` — the Copilot instructions body
  (create).
- `shared/agents/<id>/workflow-supplement.md` for `orchestrator`, `planner`,
  `coder`, `reviewer`, `documenter` (create).
- `shared/sidecar/workflow/skills.txt` — the denylist with one reason per
  line (create).
- `shared/sidecar/workflow/state/MEMORY.md` and one `README.md` per state
  folder (create).

## Steps

- [ ] **1. The relaxed workflow rule.**
  - **Owner:** `documenter`
  - `workflow.md`, under 120 lines, states: read `.claude/ai-bootstrap/MEMORY.md`
    before non-trivial work; for a task that spans several files or
    decisions, ask the planner for a plan under
    `.claude/ai-bootstrap/plans/` using the templates, otherwise implement
    directly; run the project's own test, lint, and type commands (name
    them from the repository's own docs, never `verify.py`); review any
    non-trivial diff with the reviewer agent, whose report goes to
    `.claude/ai-bootstrap/quality_reports/`; at the end write a session
    log under `.claude/ai-bootstrap/session_logs/` and record reusable
    lessons in `MEMORY.md`. State plainly that nothing here blocks a commit
    and that the repository's own guidance wins on any conflict.
  - Must not mention hooks, receipts, findings JSON, branches, the nested
    repository, `verify.py`, `record_findings`, MCP servers, or Context
    Mode.

- [ ] **2. Reporting and tool-routing rules.**
  - **Owner:** `documenter`
  - `reporting.md`: the plain-language policy from
    `shared/policies/agent-reporting.instructions.md`, without the
    caveman-mode references to hooks.
  - `tool-routing.md`: direct reads for known files, exact search for
    literals, semantic search when the client has it; no mention of
    Semble, Context Mode, or OpenWiki.

- [ ] **3. Agent supplements.**
  - **Owner:** `documenter`
  - One `workflow-supplement.md` per shipped agent, replacing the
    lifecycle sections of the canonical prompt: the orchestrator runs the
    relaxed loop from `workflow.md` and delegates; the planner writes plans
    with the templates and never creates branches; the coder implements
    and runs the project's own checks; the reviewer writes a Markdown
    report with severity sections and returns it, no JSON; the documenter
    is unchanged apart from paths. Each supplement lists the paths it uses
    under `.claude/ai-bootstrap/`.

- [ ] **4. Skill denylist.**
  - **Owner:** `documenter`, checked by the orchestrator
  - Walk every `visibility: public` skill. Deny each one that needs the
    full install (`commit`, `context-status`, `knowledge-refresh`,
    `safe-consumer-bootstrap-refresh`, `setup-project`, `deep-audit`,
    `code-review` if it names `record_findings`, `run-tests` if it names
    `verify.py`, and any other whose text names a forbidden token) and
    write the reason. Everything else is eligible.

- [ ] **5. State seeds.**
  - **Owner:** `documenter`
  - `MEMORY.md` seed: the section headings of `shared/MEMORY.md` with no
    entries. One README per state folder saying what goes there and that
    the folder is personal, Git-ignored, and kept by `--uninstall`.

## Acceptance Criteria

- Every authored file reads without a forbidden token (`.claude/hooks/`,
  `.claude/scripts/`, `verify.py`, `record_findings`, `mcp__`, `ctx_`,
  `openwiki`, `settings.json`, `core.hooksPath`, `ai-state`).
- The workflow rule fits one screen and names only paths under
  `.claude/ai-bootstrap/`.
- The denylist has one reason per denied skill.

## Verification

```bash
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

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
