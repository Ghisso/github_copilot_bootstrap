# Target Mapping

The repo generates one installable output: `dist/multi-agent/` (gitignored — run `uv run python scripts/generate_targets.py --all` to build).

## Devcontainer Bootloader

The generated `.devcontainer/` directory is intended to be committed in consumer
repos. It provides a GPU-capable sandbox and a post-start sync helper that restores
ignored AI bootstrap/state files by checking `.claude/` out from its nested `ai-state`
git branch (see [ADR-002](../plans/adr-002-git-backed-state-sync.md)).

## Shared Basis

Bootstrap maintainers author reusable content in `shared/`. Generation
renders that content into `.claude/` — skills, review profiles, Ponytail
provenance, instructions and Claude policy rules, agents, prompts,
`verify.py`/`record_findings.py`, templates, `MEMORY.md`/plans/session
logs/quality reports/explorations, and hook scripts including the
executable `run-hook.sh` dispatcher — which is the canonical runtime basis
in an installed consumer project. See [Source, generated output, consumer
repo, and nested AI
state](../openwiki/architecture/source-generated-consumer-layout.md) for
the full render sequence and what each rendered path holds.

Keep `.claude/` when pruning optional tool adapters, because it is the shared basis for all supported systems.

Put consumer-specific facts in
`.claude/instructions/project-context.instructions.md`. Preserve consumer-owned
memory, plans, explorations, session logs, and quality reports during refreshes.
`.claude/MEMORY.md` is the curated portable project-memory authority and is
seeded copy-if-absent; an existing consumer file remains byte-identical across
install, update, and migration. Native Claude and Codex memory is optional,
machine-local client state, not generated or synchronized bootstrap state, and
this bootstrap does not disable it. Promote only sanitized, durable,
project-wide facts into the shared file; resolve conflicts in shared narrative
state by manual semantic merge. See [Memory Authority and
Privacy](architecture.md#memory-authority-and-privacy) and
[SECURITY.md](../SECURITY.md).

Passwords, API tokens, confidential material, personal or customer-sensitive
data, and unredacted logs belong in approved protected data systems, never
shared or native memory. Only non-sensitive preferences and scratch may remain
local.

## Native Adapters

Claude Code:

- `CLAUDE.md`
- `.mcp.json`
- `.claude/settings.json`
- `.claude/rules/*.instructions.md` for conditional policy adapters

`CLAUDE.md` is a consumer-neutral generated entrypoint; do not hand-edit it. Claude Code uses `.claude/agents/` and `.claude/skills/` natively and receives the five universal agents.

OpenAI Codex:

- `AGENTS.md`
- `.codex/config.toml`
- `.codex/hooks.json`
- `.codex/agents/*.toml`

`AGENTS.md` is a consumer-neutral generated entrypoint; do not hand-edit it. Codex generates seven project-scoped `.codex/agents/*.toml` files — the five universal agents plus Codex-only `luna_coder` and `sol_coder` — each self-contained with its own pinned model and reasoning effort.

Google Antigravity:

- `AGENTS.md` — provider-neutral root guidance shared with Codex.
- `.agents/agents/` — six static Markdown custom-agent adapters (the five universal agents plus `antigravity_flash_coder`; Codex-only `luna_coder`/`sol_coder` are not emitted here).
- `.agents/skills/` — the shared skill tree.
- `.agents/mcp_config.json` — the shared MCP servers under Antigravity's `mcpServers` schema.
- `.agents/hooks.json` — the named `bootstrap-safety` configuration.

`.agents/` is a bootstrap-owned root adapter, like `.codex/`, with the same pre-write takeover check described in [Installing the bootstrap, file ownership, and runtime drift checks](../openwiki/operations/install-ownership-and-runtime-checks.md).

GitHub Copilot (secondary compatibility adapter):

- `.github/copilot-instructions.md`
- `.github/instructions/*.instructions.md`
- `.github/agents/*.agent.md`
- `.github/hooks/hooks.json`
- `.vscode/mcp.json`

Copilot files are native adapters; agent wrappers preserve Copilot frontmatter and point to `.claude/agents/`, and Copilot generates only the five universal agents.

See [Agent roster, prompts, and the skill
library](../openwiki/architecture/agents-and-skills.md) for how each
target renders an agent from the same `shared/agents/<id>/` metadata,
including the Codex prompt-composition rules, the per-agent model/effort
matrix (also in [Custom Agents](architecture.md#custom-agents)), and the
Antigravity `mainAgent`/`subagent` layout. See [Hook dispatcher and
guardrail scripts](../openwiki/architecture/hooks-and-guardrails.md) for
the shared `PreToolUse` safety lane every target routes through, including
the Antigravity Python bridge.
