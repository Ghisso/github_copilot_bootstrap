# Architecture

The bootstrap now uses a source-of-truth plus generated-target layout.

## Source Directories

- `shared/policies/`: reusable workflow, quality, code, testing, routing, and deployment guidance.
- `shared/skills/`: reusable skills with `visibility: public|background` metadata.
- `shared/hooks/`: hook config and guardrail scripts.
- `shared/devcontainer/`: GPU devcontainer bootloader and Hugging Face AI state sync helper. The `Dockerfile` uses a two-stage build: Node.js 22 binaries are copied from `node:22-bookworm-slim` into the NVIDIA CUDA DL base image (Ubuntu ships Node 18, which is too old for `context-mode`). `bubblewrap` and `context-mode` are installed so hook events work inside the container. `--cap-add=SYS_ADMIN` and `--security-opt=seccomp=unconfined` are required for bubblewrap namespace creation inside Docker. The `Dockerfile` also handles pre-existing GID/UID 1000 conflicts (GID guard by numeric ID; user rename via `usermod`/`groupmod` when UID is already taken). The devcontainer bind-mounts `~/.cache/huggingface` from the host so cached credentials and models are available without re-authenticating inside the container.
- `shared/mcp/servers.yaml`: single MCP server definition for Semble and context-mode.
- `shared/vscode/tasks.json`: VS Code workspace tasks source. Rendered into `.vscode/tasks.json` by the generator. Contains two tasks: an auto-pull on `folderOpen` (runs `hf-ai-sync.sh pull-state` silently when the workspace opens) and a manual push task for non-AI sessions.
- `shared/agents/`: canonical custom-agent metadata and neutral prompts.
- `shared/review-profiles/`: checklists consumed by the unified `reviewer` agent.
- `shared/prompts/`: reusable prompt templates.
- `shared/templates/`, `shared/scripts/`, `shared/MEMORY.md`, and state README directories: source inputs rendered into the shared `.claude/` basis.
- `shared/schemas/`: schema documentation for shared metadata.

## Generated Target

The single installable output is `dist/multi-agent/`.

It includes a trackable `.devcontainer/` GPU sandbox plus the `.claude/` shared basis for skills, instructions, review profiles, canonical agent bodies, prompts, memory, plans, explorations, session logs, quality reports, templates, quality scoring, and hook scripts. Native files outside `.claude/` are thin adapters or runtime config for GitHub Copilot, Claude Code, and OpenAI Codex. `.vscode/tasks.json` provides VS Code-native HF state sync that works independently of any AI tool session.

Do not edit `dist/` manually. Regenerate it with:

```bash
uv run python scripts/generate_targets.py --all
```

## Hook Dispatcher

All hook commands route through `shared/hooks/scripts/run-hook.sh` rather than calling guardrail scripts directly. The dispatcher resolves `REPO_ROOT` in order:

1. `BASH_SOURCE[0]` relative navigation (primary — works when the script is called by path)
2. Environment variable fallbacks: `GITHUB_WORKSPACE`, `WORKSPACE_FOLDER`, `VSCODE_CWD`, `PWD`
3. `git rev-parse --show-toplevel` from the current directory

This fixes two real failure modes found in consumer repos:

- `$CLAUDE_PROJECT_DIR` being empty in Claude Code, producing paths like `/.claude/hooks/scripts/...`
- `$(git rev-parse --show-toplevel)` resolving to a different directory than the repo root when invoked from certain working directories

The generated hook configs for all three tools use the pattern:

```bash
REPO_ROOT="<root-expr>"; "$REPO_ROOT/.claude/hooks/scripts/run-hook.sh" <script> [args...]
```

Claude and Codex generated configs execute `run-hook.sh` directly. `scripts/generate_targets.py` therefore marks the generated dispatcher executable, and `scripts/validate_targets.py` treats a non-executable dispatcher as a structural failure.

Hook errors (from `hf-ai-sync.sh` and others) are written to `.claude/session_logs/hooks-errors.log` in addition to stderr, so failures are auditable after the fact.

## Lifecycle Enforcement

The canonical workflow is:

```text
PRE-FLIGHT -> BRANCH -> PLAN -> IMPLEMENT -> VERIFY -> REVIEW -> SCORE -> DOCUMENT -> LEARN -> SESSION LOG -> COMMIT
```

Lifecycle hook scripts keep that workflow stateful without mutating during validation hooks:

- `enforce-branch-state.sh` runs before branch commands and validates clean `dev`, branch naming, and big-plan metadata. It recognizes `git checkout -b`, `git checkout -B`, `git switch -c`, `git switch -C`, `git switch --create`, and `git switch --create=<branch>` forms.
- `record-branch-state.sh` runs after successful branch creation and records `originating_branch`, `implementation_branch`, `started_at`, and `current_phase`.
- `enforce-commit-gate.sh` runs before normal commits and requires completed small-plan metadata, completed closeout logs, `[LEARN]` evidence, and a fresh score >= 90 report for the current branch and phase. The score report must also match `base_ref`, merge-base SHA, current HEAD SHA, `target` (stored as a repo-relative path; absolute paths outside the repo are rejected), dirty flag, and changed-files metadata.
- `record-commit-closeout.sh` runs after successful commits and advances the big-plan phase or marks the big plan complete only after the intercepted commit subject correlates with `HEAD`.
- `enforce-pr-gate.sh` blocks PRs or pushes unless every phase is complete, the base is `dev`, and bypass commits have been acknowledged.
- `session-start-state.sh` and `stop-session-log-check.sh` provide reminders for stale phase, score, and session-log state.

Bypass commit prefixes `fixup!`, `squash!`, `chore(typo):`, and `docs(typo):` are allowed for short-lived recovery work, but they are logged and must be acknowledged before PR or push.

## HF State Sync and Pull Safety

`hf-ai-sync.py pull-state` snapshots all current state files (`MEMORY.md`, `plans/**`, `explorations/**`, `session_logs/**`, `quality_reports/**`) into `.claude/.state_backups/` before overwriting them. After the pull completes, backups whose content is identical to the pulled version are deleted. Only files that were actually overwritten by the pull retain a backup, so the developer can compare and recover any local changes that were not yet pushed to the bucket.

`import_hf_api()` checks `hasattr(HfApi, "sync_bucket")` before returning the class. If the method is absent (huggingface_hub < 1.0), the function emits a named warning and returns `None`, which triggers the `hf` CLI fallback path. This prevents a transitive downgrade — e.g. from a project dependency like `haystack-ai` — from causing silent no-op syncs: without the guard, the `AttributeError` raised inside `sync_bucket()` is caught by the broad exception handler and the script exits 0 having done nothing. The Dockerfile also pins `huggingface_hub>=1.0` to prevent the downgrade at build time.

This runs on every `pull-state` invocation — whether triggered by the VS Code `folderOpen` task, an AI tool `SessionStart` hook, or manually.

`.state_backups/` is excluded from `push-state` (it does not match `STATE_INCLUDES` patterns) and should be added to `.gitignore`.

## VS Code Tasks

`.vscode/tasks.json` (source: `shared/vscode/tasks.json`) provides HF state sync that works without an active AI tool session:

- **AI state: pull from HF bucket** — runs automatically on `folderOpen` (VS Code prompts once to allow automatic tasks). Pulls state silently in the background.
- **AI state: push to HF bucket** — run manually via `Tasks: Run Task` or a keyboard shortcut binding. Shows output so the developer can confirm the push succeeded.

These complement the AI Stop hooks (which already push on every session end) for workflows where VS Code is open without an active AI session.

## Custom Agents

Custom agents are source-controlled under `shared/agents/<agent-id>/`.

Each agent contains:

- `agent.yaml`: stable metadata, capabilities, visibility, delegates, and model intent.
- `prompt.md`: target-neutral behavior.

The generator derives Copilot, Claude Code, and Codex adapters from those two files. Copilot model fields are target bindings, not portable semantics. GitHub Copilot agent `model` fields must be a single supported Copilot model string. Claude and Codex adapters must not include Copilot model pins. Codex agents are generated as project-scoped `.codex/agents/*.toml` adapters that point to `.claude/agents/`. Codex skills are generated under `.claude/skills/` and wired through `[[skills.config]]` entries in `.codex/config.toml`.
