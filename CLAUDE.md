# Claude Code Bootstrap Guidance

This is the entrypoint for a reusable multi-agent bootstrap for Python AI engineering. In an installed project, `.claude/` is the canonical runtime guidance; do not hand-edit generated target adapters.

**Project:** github_copilot_bootstrap
**Python:** 3.12+ | **Package Manager:** uv
**Stack:** Python 3.12+ with uv; adapt framework guidance to the target repository.

## Source Of Truth

- Installed canonical guidance, skills, agents, hooks, templates, and mutable AI state live under `.claude/`.
- Put repository-specific facts in `.claude/instructions/project-context.instructions.md`; preserve consumer-owned memory, plans, explorations, session logs, and quality reports during refreshes.
- Use direct reads for known files, `rg` for exact literals, Semble for semantic repository discovery, and context-mode for large outputs or compaction-safe continuity. Missing optional retrieval helpers are warnings, not hard failures.

## Task Lanes

- Read the authoritative Task Lanes decision table in `.claude/instructions/workflow.instructions.md` before acting; it is the sole normative classifier.
- Read-only/reporting stays with the main agent and produces evidence only. Diagnose stays read-only until a fix is requested.
- Only an explicit, one-file, low-risk edit with no high-risk impact and no requested commit or PR is lightweight; it stays with the main agent and needs focused verification, not lifecycle artifacts.
- Standard implementation and control-plane/high-risk work use `orchestrator -> planner -> coder -> verifier -> reviewer -> documenter -> score`; all commit/PR work is standard or higher.
- Control-plane/high-risk includes control-plane, security, dependency/lockfile, migration, multi-file, user-data, generators, and scripts. It always uses a full plan and the required high-risk review profiles.
- Audited typo commit bypasses are recovery exceptions, never lane classification.

## Required Lifecycle

`PRE-FLIGHT -> BRANCH -> PLAN -> PONYTAIL -> IMPLEMENT -> VERIFY -> REVIEW -> DOCUMENT -> SCORE -> LEARN -> SESSION LOG -> COMMIT`

- Before non-trivial work, read `.claude/MEMORY.md`, save the approved plan under `.claude/plans/`, and create one `<plan_name>_implementation` branch from a clean `dev` branch.
- Load `.claude/skills/ponytail/SKILL.md` in `full` mode before every coding task. Search and reuse before adding code.
- Verify, then run profile-driven review until clean. Update required documentation before persisting findings and score.
- Commit each completed small plan only after a fresh score is at least 90, critical findings are zero, required Ponytail findings are zero, reusable lessons are recorded in `.claude/MEMORY.md`, and the closeout session log is complete.
- Do not open a PR, push, or merge unless the workflow permits it and the user requested the external action. The user owns merge decisions.

## Exact Commands

```bash
uv sync
uv run pytest tests/ -q --tb=short
uv run mypy src/ --ignore-missing-imports --explicit-package-bases
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

Use `uv run` for project Python entrypoints and tooling; never substitute bare `python`, `pip`, `pytest`, `mypy`, or `ruff` in the normal workflow.

## Safety And Control Plane

- Keep hook guardrails enabled. Never hand-edit `.env*`, private keys, credentials, secret-bearing files, or `uv.lock`; never run destructive Git commands such as force-push, hard reset, or cleaning untracked files without explicit safe authorization.
- Control-plane files include root guidance, `.claude/hooks/`, `.github/hooks/`, `.claude/settings.json`, `.mcp.json`, and `.devcontainer/`. They require a full plan and `code`, `architecture`, `security`, `tests`, and `ponytail` review profiles.
- Keep `.claude/` as the canonical runtime basis. Bootstrap maintainers own authoring and regeneration; consumers should customize only their project context and consumer-owned state.

## Map

- Policies: `.claude/instructions/workspace.instructions.md`, `workflow.instructions.md`, `quality-and-testing.instructions.md`, and `tool-routing.instructions.md`.
- Skills: `.claude/skills/<name>/SKILL.md`; apply Ponytail to all coding and use task-matched skills when relevant.
- Agents: canonical bodies in `.claude/agents/`; the orchestrator coordinates complex work and specialists own planning, implementation, verification, review, documentation, and scoring.
- Hooks: target-native configuration dispatches to `.claude/hooks/scripts/`; runtime errors are recorded under `.claude/session_logs/`.

## Target Runtime

Claude Code uses `.claude/settings.json`, `.claude/agents/`, and `.claude/skills/` natively. Keep the configured hooks enabled.
