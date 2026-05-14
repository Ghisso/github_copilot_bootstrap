# Migration Audit

Date: 2026-05-13

## Current State

This repository started as a GitHub Copilot bootstrap centered on `.github/`.

Inventory before migration:

- 8 instruction files in `.github/instructions/`
- 17 custom agents in `.github/agents/`
- 52 skills in `.github/skills/`
- Hook guardrails in `.github/hooks/hooks.json` and `.github/hooks/scripts/`
- MCP configuration in `.vscode/mcp.json`
- Root compatibility guidance in `AGENTS.md`

## Migration Risks

- Current custom agents use GitHub Copilot frontmatter. Any model binding must use a single current Copilot model string.
- Reviewer agents depend on model-specific helper agents: `review-pass-codex` and `review-pass-sonnet`.
- Hook behavior must remain intact, especially file protection and dangerous git command blocking.
- Semble and context-mode are optional and must never become hard validation dependencies.

## Decisions

- `shared/` is the source of truth.
- `dist/` is generated only by `scripts/generate_targets.py`.
- Existing root runtime files stay active in the first pass.
- GitHub Copilot preserves current custom agent files exactly after normalizing model frontmatter to GitHub's single-string custom-agent shape.
- Claude Code and OpenAI Codex receive target-native agent forks instead of copied Copilot model pins.
- OpenAI Codex now renders project-scoped custom agents under `.codex/agents/*.toml`, matching the current Codex custom-agent format.
- OpenAI Codex renders repository skills under `.agents/skills/`, matching Codex skill discovery.
- Codex `.codex/rules/*.rules` output is deprecated and should fail validation if regenerated.
