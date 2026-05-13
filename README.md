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

# 3) Optional but recommended root/workspace surfaces
mkdir -p "$TARGET_REPO/.vscode"
cp "$BOOTSTRAP_REPO/.vscode/mcp.json" "$TARGET_REPO/.vscode/mcp.json"
cp "$BOOTSTRAP_REPO/AGENTS.md" "$TARGET_REPO/AGENTS.md"

# 4) Ensure hook scripts are executable
chmod +x "$TARGET_REPO/.github/hooks/scripts/"*.sh

# 5) Optional: commit in target repo
cd "$TARGET_REPO"
git add .github .vscode/mcp.json AGENTS.md
git commit -m "chore: add Copilot bootstrap"
```

If you are already inside this bootstrap repo and only need to set the target path:

```bash
set -euo pipefail

TARGET_REPO="/absolute/path/to/your-project"
mkdir -p "$TARGET_REPO/.github"
rsync -av .github/ "$TARGET_REPO/.github/"
mkdir -p "$TARGET_REPO/.vscode"
cp .vscode/mcp.json "$TARGET_REPO/.vscode/mcp.json"
cp AGENTS.md "$TARGET_REPO/AGENTS.md"
chmod +x "$TARGET_REPO/.github/hooks/scripts/"*.sh
```

`.github/` is the main scaffold. `.vscode/mcp.json` and `AGENTS.md` are optional but recommended add-ons: `.vscode/mcp.json` enables VS Code MCP servers for Semble and context-mode, while `AGENTS.md` gives CLI and sub-agent tools a root-level compatibility entry point. Target repositories can skip either file and still keep the bootstrap workflow functional.

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
- Optional workspace/root surfaces: [.vscode/mcp.json](.vscode/mcp.json) and [AGENTS.md](AGENTS.md)
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
- [config-first-design.instructions.md](.github/instructions/config-first-design.instructions.md)
  - Pure ConfigStore approach (no YAML)
  - Dataclass validation and registration patterns
- [api-service-standards.instructions.md](.github/instructions/api-service-standards.instructions.md)
  - BentoML service design, async endpoints, Pydantic validation
- [deployment.instructions.md](.github/instructions/deployment.instructions.md)
  - Pre-deploy checks, Bento build/container workflow, health checks
- [tool-routing.instructions.md](.github/instructions/tool-routing.instructions.md)
  - Routing between direct reads, `rg`, Semble, and context-mode

## Most Important Skills

Skills have two visibility levels: **public** skills appear in the `/` slash menu; **background** skills are hidden from the menu but auto-load when the model's description matches the task context. Both types are documented in the skills table in `copilot-instructions.md`.

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

Communication and context control:

- [caveman](.github/skills/caveman/SKILL.md)
- [caveman-compress](.github/skills/caveman-compress/SKILL.md)

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

Reviewer agents run adversarial dual-pass review through two model-specific sub-agents (`review-pass-codex` and `review-pass-sonnet`) and synthesize findings into one report. When only one sub-agent is available, reviewers fall back to single-pass mode and label findings as `[single-pass, unconfirmed]`.

Orchestrator routing:

- The orchestrator does a shallow exploration pass, then decides between `--mode micro-plan` (small, well-scoped changes) and `--mode full-plan` (new features, cross-cutting changes) before delegating to the planner.
- The planner does NOT self-classify; routing ownership stays with the orchestrator.
- Planner micro-plan mode: load skills → draft → done (no interview required).
- Planner full-plan mode: intake → exploration → interview (min 2 rounds) → module sketch → draft → optional devil's advocate.
- Control-plane files (`.github/agents/`, `.github/instructions/`, `.github/hooks/`, `copilot-instructions.md`) always use full-plan and always trigger dual adversarial review.

Coder skill loading:

- Tier 1 (always): `code-style/SKILL.md`, `testing-patterns/SKILL.md`
- Tier 2: task-specific skills loaded by type (e.g. `hydra-config` for config work, `bentoml-service` for API work)
- Coder pauses and asks the user before modifying any control-plane file.

## Hooks

Hooks provide guardrails and lightweight observability.

Configured events:

- PreToolUse
  - [protect-files.sh](.github/hooks/scripts/protect-files.sh) blocks protected files (env files, key files, secrets patterns, lockfiles) and hook config files; handles both relative and absolute paths correctly
  - [git-protection.sh](.github/hooks/scripts/git-protection.sh) blocks dangerous git commands (force push, reset --hard, clean -fd, deleting main/master)
  - [context-mode-dispatch.sh](.github/hooks/scripts/context-mode-dispatch.sh) forwards optional context-mode hook events after guardrails run
- PostToolUse / PreCompact
  - [context-mode-dispatch.sh](.github/hooks/scripts/context-mode-dispatch.sh) forwards optional context-mode lifecycle events and warns without failing when context-mode is unavailable
- SessionStart / Stop
  - [session-log.sh](.github/hooks/scripts/session-log.sh) appends lifecycle entries to `.github/session_logs/hooks-sessions.log`
  - SessionStart also calls [context-mode-dispatch.sh](.github/hooks/scripts/context-mode-dispatch.sh) when available

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
- uv run ruff format src/ tests/
- uv run python .github/scripts/quality_score.py src/ --json  (when available)

Quality gates:

- >= 80: commit-ready
- >= 90: PR-ready

## Optional Retrieval Helpers

VS Code can load the checked-in MCP servers from [.vscode/mcp.json](.vscode/mcp.json):

- `semble` uses `uvx --from "semble[mcp]" semble`.
- `context-mode` uses the portable bare `context-mode` command.

For machines without a global `context-mode` binary, install it globally or adapt local setup to use `npx -y context-mode`. Hook events already go through `.github/hooks/scripts/context-mode-dispatch.sh`, which calls `context-mode hook vscode-copilot ...`, falls back to `npx -y context-mode hook vscode-copilot ...` when `npx` is available, and otherwise prints `WARN` while exiting successfully.

Install `context-mode` with npm when Node.js is already available:

```bash
npm install -g context-mode
context-mode --help
```

If Node.js is not installed and you do not want to use `sudo`, install the official Node.js LTS binary under `~/.local` and expose it through `~/.local/bin`:

```bash
NODE_VERSION="v24.15.0"
NODE_DIST="node-${NODE_VERSION}-linux-x64"
mkdir -p "$HOME/.local/bin" "$HOME/.local/nodejs"
curl -L -o "/tmp/${NODE_DIST}.tar.xz" "https://nodejs.org/dist/${NODE_VERSION}/${NODE_DIST}.tar.xz"
tar -xJf "/tmp/${NODE_DIST}.tar.xz" -C "$HOME/.local/nodejs"
ln -sf "$HOME/.local/nodejs/${NODE_DIST}/bin/node" "$HOME/.local/bin/node"
ln -sf "$HOME/.local/nodejs/${NODE_DIST}/bin/npm" "$HOME/.local/bin/npm"
ln -sf "$HOME/.local/nodejs/${NODE_DIST}/bin/npx" "$HOME/.local/bin/npx"
"$HOME/.local/bin/npm" install -g context-mode
ln -sf "$HOME/.local/nodejs/${NODE_DIST}/bin/context-mode" "$HOME/.local/bin/context-mode"
```

Make sure `~/.local/bin` is on `PATH` before starting VS Code:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Run the bootstrap runtime check after copying optional surfaces:

```bash
python .github/scripts/check_agent_runtime.py
```

## How To Use This Bootstrap In Another Project

1. Copy the `.github` directory from this repo into your target project (or use Quick Copy above).
2. Optionally copy `.vscode/mcp.json` for VS Code MCP integration and `AGENTS.md` for root-level agent compatibility.
3. Review and adjust `copilot-instructions.md` for project-specific stack details.
4. Keep hooks enabled and ensure scripts are executable in your environment.
5. Update instruction apply scopes to match your project paths.
6. Add or remove skills and agents according to your domain.

## Customization Notes

This bootstrap is intentionally opinionated, because consistency beats improvisation when quality matters.

If you customize it, prioritize:

- preserving the plan/verify/review/score loop
- keeping verification commands accurate for your stack
- maintaining clear ownership between instructions, skills, and hooks
- treating terse-mode and compression as opt-in guardrailed tools, not blanket rewrites of source-of-truth customization files
