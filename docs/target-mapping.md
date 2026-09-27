# Target Mapping

The repo generates two installable outputs: `dist/multi-agent/`, the full
bootstrap, and `dist/sidecar/`, the personal per-clone overlay described
below (both gitignored — run `uv run python scripts/generate_targets.py --all`
to build).

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

## Sidecar Overlay

`dist/sidecar/` is a second generated target: a narrow, per-clone developer
overlay that `scripts/install_bootstrap.py --mode sidecar` installs inside a
repository whose agent harness a team already owns, without changing any
tracked file. The same installer, with `--uninstall`, removes the overlay
again. See [README.md's Personal Sidecar
Install](../README.md#personal-sidecar-install) for install, update, and
uninstall instructions, and
[docs/sidecar-provider-contract.md](sidecar-provider-contract.md) for the
native-run evidence behind every row below.

`dist/sidecar/` renders two profile trees, one per `--profile` value:
`dist/sidecar/skills/` (today's default) and `dist/sidecar/workflow/`.
`dist/sidecar/skills/` is byte-identical to the pre-profile `dist/sidecar/`
output. `--profile` selects which tree `install_bootstrap.py` reads from by
default (`dist/sidecar/<profile>/`); an explicit `--source` overrides that.

| Projection | Path(s) | Client(s) that read it |
| --- | --- | --- |
| Skill write root | `.claude/skills/<skill>/` | Claude Code; Copilot in VS Code (Local agent and Agent Host) |
| Skill write root | `.agents/skills/<skill>/` | Codex; Copilot in VS Code (Local agent and Agent Host) |
| Skill read-only check (never written) | `.github/skills/`, `.agent/skills/`, `.codex/skills/` | Scanned only to detect a name collision with team-owned content; the sidecar skips a skill at every write root rather than shadow a skill in one of these folders |
| Bridge (`skills` profile) | `.claude/rules/ai-bootstrap-sidecar.md` (no frontmatter) | Claude Code; also loaded by Copilot's Local agent |
| Bridge (`skills` profile) | `.github/instructions/ai-bootstrap-sidecar.instructions.md` (`applyTo: "**"`) | Copilot in VS Code (Local agent and Agent Host) |
| Agent (`workflow` profile) | `.claude/agents/<id>.md` | Claude Code only |
| Rule (`workflow` profile) | `.claude/rules/ai-bootstrap-*.md` | Claude Code |
| Instructions (`workflow` profile) | `.github/instructions/ai-bootstrap-workflow.instructions.md` (`applyTo: "**"`) | Copilot in VS Code (Local agent and Agent Host) |
| Review profile (`workflow` profile) | `.claude/review-profiles/<name>.md` | Claude Code only |
| Template (`workflow` profile) | `.claude/templates/plan-big.md`, `plan-small.md` | Claude Code only |
| State (`workflow` profile) | `.claude/ai-bootstrap/` (`MEMORY.md`, `plans/`, `session_logs/`, `explorations/`, `quality_reports/`, each with a README) | Claude Code, Copilot in VS Code, and Codex all read it; it is content, not a discovery mechanism, so every client that opens the file sees it |

The `skills` profile ships the four skills — `debug-investigator`,
`humanize`, `ponytail`, and `ponytail-review` — plus the two bridges above.
The `workflow` profile ships every eligible public skill (a fixed denylist
in `scripts/runtime_ownership.py` excludes skills that need the full
install) plus the agent, rule, instructions, review-profile, template, and
state rows above. No `.github/agents` or `.codex/agents` file ships in
either profile: neither Copilot nor Codex has a config-free way to discover
a custom agent from an ignored file, so those two clients get the workflow
profile's skills and state folder only, never its agents. No bridge or
instructions file ships for Codex (skill-only by design) or for Google
Antigravity (unverified).

The manifest, staging folder, preserved-copy folder, pending
ownership record, and run lock that track sidecar ownership live inside the
Git directory (`ai-bootstrap-sidecar.json`, `ai-bootstrap-sidecar-staging/`,
`ai-bootstrap-sidecar-preserved/`, `ai-bootstrap-sidecar.json.next`, and
`ai-bootstrap-sidecar.lock`), never in the worktree, so none of them can be
tracked. The manifest is schema version 2 and records `profile`; a
version-1 manifest (no `profile` field) reads as `skills`.

The pending record is written after the ignore proof passes and
before any unit moves, and removed once the real manifest lands — extra
ownership evidence for a rerun after an interrupted run, never an
instruction on its own. The run lock is held from just after preflight to
the end of the run and stays in place, empty, afterward; a dry run takes
neither. All five paths are built from the same already-verified `git
rev-parse --path-format=absolute --git-dir` value, never through `git
rev-parse --git-path`: `--git-path` resolves a symlink in the path before
printing it, which would hide exactly the symlinked Git-directory case the
sidecar's own preflight checks exist to catch. The preserved folder holds an
edited sidecar copy that a taken skill name displaced; see
[README.md's Personal Sidecar Install](../README.md#personal-sidecar-install)
for its naming and recovery, and its [Uninstall
section](../README.md#personal-sidecar-install) for `--uninstall`, which
removes the manifest and staging folder but leaves the preserved folder in
place.

The state unit (`.claude/ai-bootstrap/`, `workflow` profile only) follows
its own rules, not the ordinary unit rules above: seeded once, from its
seed files, when the folder is absent; an existing folder only ever gets a
missing seed file added, never a comparison or an overwrite; kept in place
and hidden by plain `--uninstall`; moved into the preserved-copy folder and
un-hidden only by `--uninstall --purge-state`; copied to the preserved-copy
folder, without uninstalling anything, by the standalone `--backup-state`
action. See [README.md's Personal Sidecar
Install](../README.md#personal-sidecar-install), "The state folder", for
the exact messages each case prints and the `git clean -x` risk it
mitigates.

See [Agent roster, prompts, and the skill
library](../openwiki/architecture/agents-and-skills.md) for how each
target renders an agent from the same `shared/agents/<id>/` metadata,
including the Codex prompt-composition rules, the per-agent model/effort
matrix (also in [Custom Agents](architecture.md#custom-agents)), and the
Antigravity `mainAgent`/`subagent` layout. See [Hook dispatcher and
guardrail scripts](../openwiki/architecture/hooks-and-guardrails.md) for
the shared `PreToolUse` safety lane every target routes through, including
the Antigravity Python bridge.
