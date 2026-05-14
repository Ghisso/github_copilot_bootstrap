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
- `dist/multi-agent/` is the only generated installable output.
- Existing root runtime files stay active in the first pass.
- `.claude/` is now the canonical generated shared basis for skills, instructions, agent bodies, prompts, plans, logs, reports, memory, templates, scoring, and hook scripts.
- GitHub Copilot preserves native custom-agent frontmatter while generating thin adapters that point to `.claude/agents/`.
- Claude Code uses `.claude/agents/` and `.claude/skills/` natively.
- OpenAI Codex now renders project-scoped custom-agent adapters under `.codex/agents/*.toml`, matching the current Codex custom-agent format.
- OpenAI Codex uses `[[skills.config]]` entries in `.codex/config.toml` to point at `.claude/skills/<name>`.
- Separate generated target directories for GitHub Copilot, Claude Code, and OpenAI Codex are obsolete; the single generated directory includes all three native adapter surfaces.
- Codex `.codex/rules/*.rules` output is deprecated and should fail validation if regenerated.
