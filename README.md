# GitHub Copilot Bootstrap

A reusable .github bootstrap I drop into my other projects.

This repository is my personal starter kit for opinionated Copilot workflows in Python AI engineering repos. It packages the hooks, agents, skills, and instruction files I want available everywhere so I can keep quality and execution style consistent.

Inspired and adapted from:

- [claude-code-my-workflow](https://github.com/pedrohcgs/claude-code-my-workflow)
- [armory](https://github.com/Mathews-Tom/armory)
- [ultralight](https://burkeholland.github.io/ultralight/)

## What This Repo Is

This is not an app.
It is a reusable automation + guidance layer under .github/ that I copy into new repos.

Main goals:

- Keep coding workflow consistent across repositories.
- Enforce planning, verification, and quality gates.
- Make multi-agent execution predictable and repeatable.
- Capture learned patterns as reusable skills.

## Main Philosophy

I use a strict execution loop:

Plan -> Implement -> Verify -> Review -> Fix -> Score

Core principles:

- Plan first for non-trivial work.
- Config-first design for new features.
- Verify every change with tests, typing, and linting.
- Use reviewer agents to challenge implementation quality.
- Ship only when quality gates are met.
- Preserve lessons learned in memory and session logs.

## Quick Copy

Use these exact commands to copy this bootstrap into another repo.

```bash
set -euo pipefail

# 1) Set paths
BOOTSTRAP_REPO="/absolute/path/to/github_copilot_bootstrap"
TARGET_REPO="/absolute/path/to/your-project"

# 2) Copy .github scaffold
mkdir -p "$TARGET_REPO/.github"
rsync -av "$BOOTSTRAP_REPO/.github/" "$TARGET_REPO/.github/"

# 3) Ensure hook scripts are executable
chmod +x "$TARGET_REPO/.github/hooks/scripts/"*.sh

# 4) Optional: commit in target repo
cd "$TARGET_REPO"
git add .github
git commit -m "chore: add Copilot bootstrap (.github)"
```

If you are already inside this bootstrap repo and only need to set the target path:

```bash
set -euo pipefail

TARGET_REPO="/absolute/path/to/your-project"
mkdir -p "$TARGET_REPO/.github"
rsync -av .github/ "$TARGET_REPO/.github/"
chmod +x "$TARGET_REPO/.github/hooks/scripts/"*.sh
```

## Architecture Flow

```mermaid
flowchart LR
  U[Developer Request] --> A[Orchestrator / Planner]
  A --> C[Coder or Designer]
  C --> V[Verifier + Quality Gates]

  I[Instructions] --> A
  I --> C

  S[Skills] --> A
  S --> C

  H[Hooks] --> T[Tool Execution Guardrails]
  T --> C

  R[Reviewer Agents] --> V
  C --> R

  V --> O[Commit or PR Decision]
```

Interpretation:

- Instructions define non-negotiable rules.
- Skills provide reusable playbooks for specific tasks.
- Agents execute and review the work.
- Hooks enforce safety and log lifecycle events.
- Verifier and quality gates decide whether code is ready.

## What Is Included

- Instructions: always-on and path-scoped rules in [.github/instructions/](.github/instructions/)
- Agents: specialized implementation and review agents in [.github/agents/](.github/agents/)
- Skills: reusable workflows in [.github/skills/](.github/skills/)
- Hooks: policy and observability scripts in [.github/hooks/](.github/hooks/)
- Templates and scripts: planning, session logs, quality scoring

## Most Important Instructions

These are the files that matter most in day-to-day use:

- [workflow.instructions.md](.github/instructions/workflow.instructions.md)
  - Plan-first protocol
  - Orchestrator loop and review order
  - Session logging and context management
- [quality-and-testing.instructions.md](.github/instructions/quality-and-testing.instructions.md)
  - Verification commands and required testing order
  - Quality scoring rubric and gates
- [code-standards.instructions.md](.github/instructions/code-standards.instructions.md)
  - Naming, architecture patterns, deprecation protocol
- [tests.instructions.md](.github/instructions/tests.instructions.md)
  - Fixture design, mocking boundaries, async testing patterns
- [config-first-design.instructions.md](.github/instructions/config-first-design.instructions.md) + [configs.instructions.md](.github/instructions/configs.instructions.md)
  - Pure ConfigStore approach (no YAML)
  - Dataclass validation and registration patterns
- [api-service-standards.instructions.md](.github/instructions/api-service-standards.instructions.md)
  - BentoML service design, async endpoints, Pydantic validation
- [deployment.instructions.md](.github/instructions/deployment.instructions.md)
  - Pre-deploy checks, Bento build/container workflow, health checks

## Most Important Skills

There are many skills; these are the high-leverage ones I rely on most:

Core workflow:

- [plan-decomposition](.github/skills/plan-decomposition/SKILL.md)
- [iterative-plan-review](.github/skills/iterative-plan-review/SKILL.md)
- [create-feature](.github/skills/create-feature/SKILL.md)
- [run-tests](.github/skills/run-tests/SKILL.md)
- [refactor](.github/skills/refactor/SKILL.md)
- [code-review](.github/skills/code-review/SKILL.md)

Quality and architecture:

- [code-style](.github/skills/code-style/SKILL.md)
- [testing-patterns](.github/skills/testing-patterns/SKILL.md)
- [review-api](.github/skills/review-api/SKILL.md)
- [text-to-sql-safety](.github/skills/text-to-sql-safety/SKILL.md)
- [debug-investigator](.github/skills/debug-investigator/SKILL.md)

Project acceleration:

- [setup-project](.github/skills/setup-project/SKILL.md)
- [add-dependency](.github/skills/add-dependency/SKILL.md)
- [deploy-service](.github/skills/deploy-service/SKILL.md)
- [hydra-config](.github/skills/hydra-config/SKILL.md)
- [bentoml-service](.github/skills/bentoml-service/SKILL.md)

These skills encode battle-tested workflows and reduce ad-hoc execution.

## Agent System

The agent layer gives me orchestration plus specialist reviews.

Primary flow for complex work:

- [orchestrator](.github/agents/orchestrator.agent.md) -> [planner](.github/agents/planner.agent.md) -> [coder](.github/agents/coder.agent.md)/[designer](.github/agents/designer.agent.md) -> reviewers -> [verifier](.github/agents/verifier.agent.md)

Key reviewer agents:

- [code-reviewer](.github/agents/code-reviewer.agent.md)
- [security-reviewer](.github/agents/security-reviewer.agent.md)
- [architecture-reviewer](.github/agents/architecture-reviewer.agent.md)
- [test-reviewer](.github/agents/test-reviewer.agent.md)
- [api-reviewer](.github/agents/api-reviewer.agent.md)
- [config-reviewer](.github/agents/config-reviewer.agent.md)
- [performance-reviewer](.github/agents/performance-reviewer.agent.md)
- [documentation-reviewer](.github/agents/documentation-reviewer.agent.md)

Reviewer agents run adversarial dual-pass review through model-specific reviewer passes and synthesize findings into one report.

## Hooks

Hooks provide guardrails and lightweight observability.

Configured events:

- preToolUse
  - [protect-files.sh](.github/hooks/scripts/protect-files.sh) blocks protected files (env files, key files, secrets patterns, lockfiles)
  - [git-protection.sh](.github/hooks/scripts/git-protection.sh) blocks dangerous git commands
- sessionStart/sessionEnd
  - [session-log.sh](.github/hooks/scripts/session-log.sh) appends lifecycle entries
- errorOccurred
  - [error-log.sh](.github/hooks/scripts/error-log.sh) records hook/runtime errors

Core hook config: [hooks.json](.github/hooks/hooks.json)

Design intent:

- deny risky actions early
- keep audit trails lightweight and local
- leave nuanced coaching (reminders/cadence) to instruction files

## Verification Defaults

Expected verification commands after implementation:

- uv run pytest tests/ -q --tb=short
- uv run mypy src/ --ignore-missing-imports --explicit-package-bases
- uv run ruff check src/ tests/

Quality gates:

- >= 80: commit-ready
- >= 90: PR-ready

## How To Use This Bootstrap In Another Project

1. Copy the .github directory from this repo into your target project (or use Quick Copy above).
2. Review and adjust copilot-instructions.md for project-specific stack details.
3. Keep hooks enabled and ensure scripts are executable in your environment.
4. Update instruction apply scopes to match your project paths.
5. Add or remove skills and agents according to your domain.

## Customization Notes

This bootstrap is intentionally opinionated, because consistency beats improvisation when quality matters.

If you customize it, prioritize:

- preserving the plan/verify/review/score loop
- keeping verification commands accurate for your stack
- maintaining clear ownership between instructions, skills, and hooks
