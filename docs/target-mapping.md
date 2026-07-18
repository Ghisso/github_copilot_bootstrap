# Target Mapping

The repo generates one installable output: `dist/multi-agent/` (gitignored — run `uv run python scripts/generate_targets.py --all` to build).

## Devcontainer Bootloader

The generated `.devcontainer/` directory is intended to be committed in consumer
repos. It provides a GPU-capable sandbox and a post-start sync helper that restores
ignored AI bootstrap/state files by checking `.claude/` out from its nested `ai-state`
git branch (see [ADR-002](../plans/adr-002-git-backed-state-sync.md)).

## Shared Basis

The shared basis lives under `.claude/`:

- `.claude/skills/**/SKILL.md`
- `.claude/skills/ponytail/SKILL.md` and `.claude/skills/ponytail-review/SKILL.md`
- `.claude/review-profiles/*.md`
- `.claude/third_party/ponytail/{LICENSE,UPSTREAM.md}`
- `.claude/instructions/*.instructions.md`
- `.claude/agents/*.md`
- `.claude/prompts/*.prompt.md`
- `.claude/scripts/quality_score.py`
- `.claude/templates/*.md`, including big-plan, small-plan, session-log, and quality-report templates
- `.claude/MEMORY.md`, `.claude/plans/`, `.claude/session_logs/`, `.claude/quality_reports/`, `.claude/explorations/`
- `.claude/hooks/scripts/*.sh`

`run-hook.sh` is the executable dispatcher for target-native hook configs. Generated output marks it runnable because Claude and Codex call it directly.

Keep `.claude/` when pruning optional tool adapters, because it is the shared basis for all supported systems.

## Native Adapters

GitHub Copilot:

- `.github/copilot-instructions.md`
- `.github/instructions/*.instructions.md`
- `.github/agents/*.agent.md`
- `.github/hooks/hooks.json`
- `.vscode/mcp.json`

Copilot files are native adapters. Agent wrappers preserve Copilot frontmatter and point to `.claude/agents/`; instruction wrappers preserve Copilot discovery and point to `.claude/instructions/`; hook config invokes `.claude/hooks/scripts/`.

Claude Code:

- `CLAUDE.md`
- `.mcp.json`
- `.claude/settings.json`

Claude Code uses `.claude/agents/` and `.claude/skills/` natively. Agent names are identical across every target — the generator performs no per-target renaming. (The reviewer runs its own primary and verification passes; there are no separate review-helper agents.)

OpenAI Codex:

- `AGENTS.md`
- `.codex/config.toml`
- `.codex/hooks.json`
- `.codex/agents/*.toml`

Codex custom agents remain project-scoped `.codex/agents/*.toml` files with `name`, `description`, `model`, `model_reasoning_effort`, and `developer_instructions`. Each adapter points to the canonical body in `.claude/agents/` and takes its model/effort pair from `model_intent.openai-codex`.

Codex skills are stored under `.claude/skills/` and enabled through `[[skills.config]]` entries in `.codex/config.toml` whose `path` points at each skill's `SKILL.md` file, such as `../.claude/skills/run-tests/SKILL.md`. The config omits the redundant flat `[features]` block (Codex enables hooks by default), configures `[features.multi_agent_v2]` to expose named-agent routing metadata through the `agents` namespace, and wires the documented `PreCompact` event. Codex project trust is required for that project config, hooks, and skill wiring to load.
