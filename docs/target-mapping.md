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

`CLAUDE.md` is a consumer-neutral generated entrypoint to the installed `.claude/` basis; do not hand-edit it. Claude Code uses `.claude/agents/` and `.claude/skills/` natively. Conditional shared policies are native `.claude/rules/` adapters with equivalent YAML `paths`; always-on policy remains root guidance. Claude VS Code bundles that same runtime and reads the generated `.claude/settings.json`, so no duplicate VS Code adapter is installed. Claude receives exactly the six universal agents: `orchestrator`, `planner`, `coder`, `reviewer`, `verifier`, and `documenter`. Eligible agent names are not renamed between targets. (The reviewer runs its own primary and verification passes; there are no separate review-helper agents.)

OpenAI Codex:

- `AGENTS.md`
- `.codex/config.toml`
- `.codex/hooks.json`
- `.codex/agents/*.toml`

`AGENTS.md` is a consumer-neutral generated entrypoint to the installed `.claude/` basis; do not hand-edit it. Codex discovers project guidance from the repository root down to the current working directory, with closer `AGENTS.md` files taking precedence and a default 32 KiB combined-project-document cap. This bootstrap emits nested `AGENTS.md` only when a policy owns a stable concrete directory. The Phase C policy scopes are mixed/glob/file-specific, so their non-widening Codex mapping is the corresponding shared skill rather than speculative nested guidance.

The shared agent loader resolves target eligibility before rendering. Omitted
`targets` keeps the six universal agents eligible everywhere; explicit
`targets: ["openai-codex"]` limits `luna_coder` and `sol_coder` to Codex.
GitHub Copilot therefore also retains exactly the universal six, while Codex
generates eight project-scoped `.codex/agents/*.toml` files.

Codex custom agents contain `name`, `description`, `model`,
`model_reasoning_effort`, and `developer_instructions`. The generator places a
short metadata header before the exact target-transformed role body; it never
tells the subagent to read `.claude/agents/<id>.md` at runtime. For an ordinary
agent, the body is its `prompt.md` plus an optional Codex supplement. For
`luna_coder` and `sol_coder`, one-level `prompt_base: "coder"` composition
produces the transformed coder prompt, one literal role-supplement delimiter,
and the specialist supplement. The loader rejects missing, copied, recursive,
multi-level, or cyclic composition before rendering.

`agent.yaml` remains the metadata, eligibility, composition, and model/effort
source of truth, so the prompt body is not a second metadata source. The TOMLs
intentionally omit `mcp_servers` and skill overrides: Codex applies the trusted
project's `.codex/config.toml`, including the shared MCP and skill
registrations. Structural validation checks exact body parity and records the
actual `developer_instructions` size for all eight roles. The current official
custom-agent schema does not publish a separate size cap; these measurements
are observability, not a product limit or delivery evidence.

The current declared Codex matrix is orchestrator Sol/xhigh, planner Sol/xhigh,
reviewer Sol/high, coder Terra/high, documenter Luna/medium, verifier Luna/low,
`luna_coder` Luna/xhigh, and `sol_coder` Sol/xhigh. The experimental named
implementation path is exactly `luna_coder -> coder -> sol_coder`, with no
successor after Sol and no spawn-time model or effort override. The Codex-only
orchestrator supplement owns the bounded packet, Luna selection, structured
blocker, evidence attribution, and stop behavior. `visibility: hidden` for the
specialists is an internal orchestration convention, not a native Codex UI
guarantee.

The dated 2026-08-09 native record observed the historical six roles only.
Future optional persistent-thread probes may exercise all eight current roles;
no native run is required for this feature. Claude and Copilot behavior remains
unchanged.

Codex skills are stored under `.claude/skills/` and enabled through `[[skills.config]]` entries in `.codex/config.toml` whose `path` points at each skill's `SKILL.md` file, such as `../.claude/skills/run-tests/SKILL.md`. The config omits the redundant flat `[features]` block (Codex enables hooks by default), sets `agents.max_concurrent_threads_per_session = 6`, omits the legacy `max_threads` and redundant `agents.enabled`, configures `[features.multi_agent_v2]` to expose named-agent routing metadata (its `tool_namespace = "agents"` key is inert in Codex 0.147.0 — see the [dated record](2026-08-08-codex-routing-compatibility.md)), and wires the documented `PreCompact` event. Codex project trust is required for that project config, hooks, and skill wiring to load. Because `.codex/hooks.json` trust is content/hash-bound, reopen/reload Codex for VS Code and review/reapprove project hooks when prompted after an actual install or update; the installer never approves them or edits user trust settings.

For both primary targets, generated `PreToolUse` separates mutation safety from
observability: native edit matchers call `protect-files.sh`, `Bash` calls one
ordered guard wrapper, and `*` calls only context-mode dispatch. The Codex
native-edit matcher is `Edit|Write`; Claude additionally supports `MultiEdit`.
The Bash wrapper invokes direct `python3` target classification rather than
`uv run`, allowing protection before a project environment exists. It classifies
mutation targets segment by segment, allows proven read-only inspection, checks
copy/install/move sources and destinations, and fails closed for missing Python,
redirects, in-place edits, and ambiguous commands. This preserves Codex's
deny-only hook-config protection and Claude's approval path without routing Read
or MCP calls through a mutation handler. Opaque command handling is deliberately
literal-based rather than a claim that every unknown command mutates: it covers
`.env*`, `uv.lock`, `credentials*`, secret names, `.pem`/`.key`, hook paths, and
protected hook configuration files.

The generated consumer config is mirrored under
`.claude/bootstrap-root/.codex/` for restoration. The bootstrap repository's
root `.codex/config.toml` is instead tracked authoring and stays protected when
dogfooding refreshes generated siblings. The protected MultiAgent V2
metadata-exposure configuration and `max_depth = 1` are distinct compatibility
decisions: retain both until their respective gates in the [dated Codex routing
compatibility record](2026-08-08-codex-routing-compatibility.md) pass. Current
generation validation is structural; it is not evidence that a contemporary
native client has routed all eight current roles. The dated record preserves
its six-role observations separately.

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
`paths`; it is not by itself a claim of real-client loading. Copilot generates
only the six universal agents and receives no Codex routing supplement.
