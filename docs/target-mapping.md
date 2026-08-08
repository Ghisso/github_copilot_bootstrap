# Target Mapping

The repo generates one installable output: `dist/multi-agent/` (gitignored — run `uv run python scripts/generate_targets.py --all` to build).

## Devcontainer Bootloader

The generated `.devcontainer/` directory is intended to be committed in consumer
repos. It provides a GPU-capable sandbox and a post-start sync helper that restores
ignored AI bootstrap/state files by checking `.claude/` out from its nested `ai-state`
git branch (see [ADR-002](../plans/adr-002-git-backed-state-sync.md)).

## Shared Basis

Bootstrap maintainers author reusable content in `shared/`. Generation renders
that content into `.claude/`, which is the canonical runtime basis in an
installed consumer project:

- `.claude/skills/**/SKILL.md`
- `.claude/skills/ponytail/SKILL.md` and `.claude/skills/ponytail-review/SKILL.md`
- `.claude/review-profiles/*.md`
- `.claude/third_party/ponytail/{LICENSE,UPSTREAM.md}`
- `.claude/instructions/*.instructions.md`
- `.claude/rules/*.instructions.md` for conditional Claude policy adapters
- `.claude/agents/*.md`
- `.claude/prompts/*.prompt.md`
- `.claude/scripts/quality_score.py`
- `.claude/templates/*.md`, including big-plan, small-plan, session-log, and quality-report templates
- `.claude/MEMORY.md`, `.claude/plans/`, `.claude/session_logs/`, `.claude/quality_reports/`, `.claude/explorations/`
- `.claude/hooks/scripts/*.sh`

`run-hook.sh` is the executable dispatcher for target-native hook configs. Generated output marks it runnable because Claude and Codex call it directly.

Keep `.claude/` when pruning optional tool adapters, because it is the shared basis for all supported systems.

Put consumer-specific facts in
`.claude/instructions/project-context.instructions.md`. Preserve consumer-owned
memory, plans, explorations, session logs, and quality reports during refreshes.

## Native Adapters

Claude Code:

- `CLAUDE.md`
- `.mcp.json`
- `.claude/settings.json`
- `.claude/rules/*.instructions.md` for conditional policy adapters

`CLAUDE.md` is a generated entrypoint to the installed `.claude/` basis; do not hand-edit it. Claude Code uses `.claude/agents/` and `.claude/skills/` natively. Conditional shared policies are native `.claude/rules/` adapters with equivalent YAML `paths`; always-on policy remains root guidance. Claude VS Code bundles that same runtime and reads the generated `.claude/settings.json`, so no duplicate VS Code adapter is installed. Agent names are identical across every target — the generator performs no per-target renaming. (The reviewer runs its own primary and verification passes; there are no separate review-helper agents.)

OpenAI Codex:

- `AGENTS.md`
- `.codex/config.toml`
- `.codex/hooks.json`
- `.codex/agents/*.toml`

`AGENTS.md` is a generated entrypoint to the installed `.claude/` basis; do not hand-edit it. Codex discovers project guidance from the repository root down to the current working directory, with closer `AGENTS.md` files taking precedence and a default 32 KiB combined-project-document cap. This bootstrap emits nested `AGENTS.md` only when a policy owns a stable concrete directory. The Phase C policy scopes are mixed/glob/file-specific, so their non-widening Codex mapping is the corresponding shared skill rather than speculative nested guidance.

Codex custom agents remain project-scoped `.codex/agents/*.toml` files with `name`, `description`, `model`, `model_reasoning_effort`, and `developer_instructions`. Each adapter points to the canonical body in `.claude/agents/` and takes its model/effort pair from `model_intent.openai-codex`.

Codex skills are stored under `.claude/skills/` and enabled through `[[skills.config]]` entries in `.codex/config.toml` whose `path` points at each skill's `SKILL.md` file, such as `../.claude/skills/run-tests/SKILL.md`. The config omits the redundant flat `[features]` block (Codex enables hooks by default), sets `agents.max_concurrent_threads_per_session = 6`, omits the legacy `max_threads` and redundant `agents.enabled`, configures `[features.multi_agent_v2]` to expose named-agent routing metadata through the `agents` namespace, and wires the documented `PreCompact` event. Codex project trust is required for that project config, hooks, and skill wiring to load. Because `.codex/hooks.json` trust is content/hash-bound, reopen/reload Codex for VS Code and review/reapprove project hooks when prompted after an actual install or update; the installer never approves them or edits user trust settings.

The generated consumer config is mirrored under
`.claude/bootstrap-root/.codex/` for restoration. The bootstrap repository's
root `.codex/config.toml` is instead tracked authoring and stays protected when
dogfooding refreshes generated siblings. The protected MultiAgent V2
metadata-exposure configuration and `max_depth = 1` are distinct compatibility
decisions: retain both until their respective gates in the [dated Codex routing
compatibility record](2026-08-08-codex-routing-compatibility.md) pass. Current
generation validation is structural; it is not evidence that a contemporary
native client has routed all six roles.

GitHub Copilot (secondary compatibility adapter):

- `.github/copilot-instructions.md`
- `.github/instructions/*.instructions.md`
- `.github/agents/*.agent.md`
- `.github/hooks/hooks.json`
- `.vscode/mcp.json`

Copilot files are native adapters. Agent wrappers preserve Copilot frontmatter
and point to `.claude/agents/`; each policy adapter points to the canonical
`.claude/instructions/` copy and derives `applyTo` from the target-neutral
`applicability` patterns. This parity is generator-validated alongside Claude
`paths`; it is not a claim of real-client loading before Phase I.
