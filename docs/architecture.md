# Architecture

The bootstrap now uses a source-of-truth plus generated-target layout.

## Source Directories

- `shared/policies/`: reusable workflow, quality, code, testing, routing, and deployment guidance.
- `shared/skills/`: reusable skills with `visibility: public|background` metadata.
- `shared/third_party/ponytail/`: pinned Ponytail provenance and MIT license; portable skills live in `shared/skills/ponytail*`.
- `shared/hooks/`: hook config and guardrail scripts.
- `shared/devcontainer/`: GPU devcontainer bootloader. The `Dockerfile` uses a two-stage build: Node.js 22 binaries are copied from `node:22-bookworm-slim` into the NVIDIA CUDA DL base image (Ubuntu ships Node 18, which is too old for `context-mode`). `bubblewrap` and `context-mode` are installed so hook events work inside the container. `--cap-add=SYS_ADMIN` and `--security-opt=seccomp=unconfined` are required for bubblewrap namespace creation inside Docker. The `Dockerfile` also handles pre-existing GID/UID 1000 conflicts (GID guard by numeric ID; user rename via `usermod`/`groupmod` when UID is already taken). The devcontainer bind-mounts `~/.cache/huggingface` from the host so cached credentials and models are available without re-authenticating inside the container — used by the projects themselves, not by AI state sync (see [ADR-002](../plans/adr-002-git-backed-state-sync.md)). `post-start.sh` bootstraps AI state via `state-sync.sh`/`restore-root-adapters.sh`, both also rendered here (see "Git-Backed State Sync" below).
- `shared/mcp/servers.json`: single MCP server definition for Semble and context-mode.
- `shared/vscode/tasks.json`: VS Code workspace tasks source. Rendered into `.vscode/tasks.json` by the generator. Contains two tasks: an auto-pull on `folderOpen` (runs `state-sync.sh pull` silently when the workspace opens) and a manual push task for non-AI sessions.
- `shared/agents/`: canonical custom-agent metadata and neutral prompts.
- `shared/review-profiles/`: checklists consumed by the unified `reviewer` agent.
- `shared/prompts/`: reusable prompt templates.
- `shared/templates/`, `shared/scripts/`, `shared/MEMORY.md`, and state README directories: source inputs rendered into the shared `.claude/` basis.
- `shared/schemas/`: schema documentation for shared metadata.

## Generated Target

The single installable output is `dist/multi-agent/`.

It includes a trackable `.devcontainer/` GPU sandbox plus the `.claude/` shared basis for skills, instructions, review profiles, canonical agent bodies, prompts, memory, plans, explorations, session logs, quality reports, templates, quality scoring, third-party notices, and hook scripts — `.claude/` is itself a nested git repository (branch `ai-state`; see "Git-Backed State Sync" below). Native files outside `.claude/` are thin adapters or runtime config for GitHub Copilot, Claude Code, and OpenAI Codex. `.vscode/tasks.json` provides VS Code-native AI state sync that works independently of any AI tool session.

## Ponytail Integration

Ponytail `v4.8.4` is vendored at the portable skill layer rather than installed
as a per-user plugin. Every target receives `.claude/skills/ponytail/`,
`.claude/skills/ponytail-review/`, and the upstream license/provenance. Root
guidance and the coder role require `full` mode for coding, so fresh consumers
work without network access or global plugin state.

The unified reviewer runs a `ponytail` profile for every non-documentation
diff. `record_findings.py --profile ponytail` persists top-level
`ponytail_reviewed` and `ponytail_findings` fields with the existing diff
content hash. Commit and push gates require a fresh review with zero surviving
Ponytail findings; any subsequent code/config/script edit invalidates it.
Documentation-only diffs are exempt.

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

Hook errors (from `state-sync.sh` and others) are written to `.claude/session_logs/hooks-errors.log` in addition to stderr, so failures are auditable after the fact.

## Lifecycle Enforcement

The canonical workflow is:

```text
PRE-FLIGHT -> BRANCH -> PLAN -> IMPLEMENT -> VERIFY -> REVIEW -> SCORE -> DOCUMENT -> LEARN -> SESSION LOG -> COMMIT
```

Lifecycle hook scripts keep that workflow stateful without mutating during validation hooks:

- `enforce-branch-state.sh` runs before branch commands and validates clean `dev`, branch naming, and big-plan metadata. It recognizes `git checkout -b`, `git checkout -B`, `git switch -c`, `git switch -C`, `git switch --create`, and `git switch --create=<branch>` forms.
- `record-branch-state.sh` runs after successful branch creation and records `originating_branch`, `implementation_branch`, `started_at`, and `current_phase`.
- `enforce-commit-gate.sh` runs before normal commits and requires completed small-plan metadata, completed closeout logs, `[LEARN]` evidence, and a fresh score >= 90 report for the current branch and phase. The report must also match `base_ref`, merge-base SHA, and current HEAD SHA; record `tests_passed: true`, not be `tests_skipped`, and be `dirty: false` (no unstaged changes); target a repo-relative path; and carry a `content_hash` (`git hash-object` of the diff against the merge base) that still matches the working tree. The content hash replaces the old mtime freshness check, so an amend/rebase/editor-touch that preserves content no longer false-blocks while any real post-scoring edit does. Report selection is newest-by-`generated_at`, not filename order, and failure messages name the exact mismatch plus the regenerate command. The git classifiers tokenize past global flags (`git -C .`, `git -c k=v`, `--git-dir=`), and an unparseable payload fails closed with a non-zero exit.
- `record-commit-closeout.sh` runs after successful commits and advances the big-plan phase or marks the big plan complete only after the intercepted commit subject correlates with `HEAD`.
- `enforce-pr-gate.sh` blocks PRs or pushes unless every phase is complete, the base is `dev`, and bypass commits have been acknowledged.
- `session-start-state.sh` and `stop-session-log-check.sh` provide reminders for stale phase, score, and session-log state.

Bypass commit prefixes `fixup!`, `squash!`, `chore(typo):`, and `docs(typo):` are allowed for short-lived recovery work, but they skip only the plan-ceremony checks (small-plan/closeout/score/LEARN) — branch-shape validation still runs, so a bypass commit off a non-`*_implementation` branch is still denied. Bypasses are logged and must be acknowledged before PR or push.

The two safety-critical guards, `protect-files.sh` and `git-protection.sh`, run their primary checks in pure bash with no `uv` dependency (the Python path in `protect-files.sh` is an enhancement used only when `uv` is present). On an internal error a guard fails toward `ask` (deny on Codex) rather than a silent allow, and the PreToolUse gates exit non-zero on an unparseable payload so runtimes that key blocking on exit status deny the call.

## Git-Backed State Sync

`.claude/` in each consumer is a plain, self-contained git repository (its own `.git/` inside `.claude/`), tracking both the bootstrap-controlled files and mutable AI state (`MEMORY.md`, `plans/**`, `explorations/**`, `session_logs/**`, `quality_reports/**`) on one branch, `ai-state`. The outer consumer repo gitignores `.claude/` entirely, so the nested repo is invisible to the code branches. See [ADR-002](../plans/adr-002-git-backed-state-sync.md) for the full rationale and the alternatives it replaced (Hugging Face bucket mirroring, `git worktree`, committing state into code branches).

`shared/hooks/scripts/state-sync.sh` (pure bash, no `uv`/Python) implements four subcommands, all warn-never-fail (a sync problem never fails a Stop hook or blocks a session start) and all draining stdin with the same 2-second timeout the old sync helper used:

- **`setup`** — idempotent. If `.claude/.git` is missing: `git init`, resolve and configure the remote (`AI_STATE_REMOTE` / `--state-remote` at install time, else the outer repo's own `origin`), commit whatever is already on disk (there is always something — at minimum this script itself), then reconcile with `origin/ai-state` via `git merge --allow-unrelated-histories` if it already exists remotely (a real merge, not a bare checkout, so it combines file-by-file instead of refusing to overwrite untracked files that are about to converge anyway). A genuine conflict aborts the merge and warns, leaving the local commit as the source of truth.
- **`pull`** — `git pull --rebase --autostash origin ai-state`. On conflict: abort the rebase, print a `WARN` naming the conflicting files and the manual-resolution commands, and exit 0 with local files intact.
- **`push`** — commit any staged state as `session: <ISO-timestamp>` (skipping the commit if nothing changed), `pull` (as above), then push. A push rejection after a failed rebase gets the same loud-warn-exit-0 contract.
- **`migrate-from-hf`** — one-way, explicit: if `.claude/` has content but no `.claude/.git` yet, runs `setup`'s init/remote logic, commits everything on disk as `migrate: import pre-git state`, and pushes. No automatic pull from the old Hugging Face bucket happens here — the local tree is the source of truth at migration time; run the retired `hf-ai-sync.py pull-state` once first, manually, if you want the bucket's newer copy. `update_consumers.py` calls this automatically for any consumer whose `.claude/` predates git-backed state.

Bootstrap updates land as `bootstrap:`-prefixed commits (made by `install_bootstrap.py`/`update_consumers.py`); session state lands as `session:`-prefixed commits (made by the Stop hook). The commit log on `ai-state` cleanly separates the two — `git -C .claude log --stat` is a full audit trail of what every session and every bootstrap update changed, something the old bucket mirror had no equivalent of.

`state-sync.sh` and `restore-root-adapters.sh` (which copies `.claude/bootstrap-root/` — the root-level adapter files that live outside `.claude/`, such as `CLAUDE.md`/`AGENTS.md`/`.mcp.json`/`.codex/**` — back out to the repo root) are rendered in two locations: `.claude/hooks/scripts/` for normal use, and `.devcontainer/` so `post-start.sh` has a copy it can run before `.claude/` exists at all on a fresh clone.

`MEMORY.md` is single-homed as a tracked file in `.claude/`, evolving via `session:`/`bootstrap:` commits like everything else — no separate bundle or restore-order dependency the old bucket split required.

## VS Code Tasks

`.vscode/tasks.json` (source: `shared/vscode/tasks.json`) provides AI state sync that works without an active AI tool session:

- **AI state: pull** — runs automatically on `folderOpen` (VS Code prompts once to allow automatic tasks). Pulls state silently in the background via `state-sync.sh pull`.
- **AI state: push** — run manually via `Tasks: Run Task` or a keyboard shortcut binding. Shows output so the developer can confirm the push succeeded, via `state-sync.sh push`.

These complement the AI SessionStart/Stop hooks (which already pull/push on every session start/end) for workflows where VS Code is open without an active AI session.

## Custom Agents

Custom agents are source-controlled under `shared/agents/<agent-id>/`.

Each agent contains:

- `agent.yaml`: stable metadata, capabilities, visibility, delegates, and per-target model/effort intent.
- `prompt.md`: target-neutral behavior.

The generator derives Copilot, Claude Code, and Codex adapters from those two files. Copilot model fields are target bindings, not portable semantics. GitHub Copilot agent `model` fields must be a single supported Copilot model string. Claude and Codex adapters must not include Copilot model pins.

The Claude Code target carries per-agent model and reasoning-effort tiers. Each `agent.yaml` sets `model_intent.claude-code` to an object (`{ "model": ..., "effort": ... }`); the generator emits matching `model:` and `effort:` frontmatter on each `.claude/agents/*.md`, skipping `inherit` values so the orchestrator (main-thread persona) follows the session. Effort-heavy roles run on the stronger model (planner `opus`/`max`, reviewer and coder `sonnet`/`xhigh`, documenter `sonnet`/`high`); the mechanical `verifier` runs on `haiku` with no `effort:` line, because Haiku does not support the effort field. **Extended thinking is intentionally not configured per agent**: Claude Code subagents inherit the session's thinking state, so there is no per-agent knob to set.

Agent names are identical across every target — the generator performs no per-target renaming. Codex agents are generated as project-scoped `.codex/agents/*.toml` adapters that point to `.claude/agents/`. The root Codex session is pinned to `gpt-5.6-sol` / `xhigh` in `.codex/config.toml`. Each custom agent overrides both `model` and `model_reasoning_effort` from its canonical `model_intent.openai-codex`: orchestrator Sol/xhigh, planner Sol/max, reviewer Sol/high, coder Terra/high, documenter Terra/medium, and verifier Luna/low. The validator requires those generated values to match the canonical intent exactly.

Codex skills are wired through `[[skills.config]]` entries in `.codex/config.toml` whose `path` points at each skill's `SKILL.md` file; the config omits the redundant flat `[features]` block (hooks are on by default), exposes MultiAgent V2 spawn metadata through the `agents` namespace so named model/effort profiles are selectable, and wires the documented `PreCompact` event.

## Design Decisions

- [ADR-001: Multi-target bootstrap over native per-platform packaging](../plans/adr-001-multi-target-lcd.md) — why this repo generates thin adapters for Copilot/Claude/Codex from one shared basis instead of shipping Claude-native plugin packaging, what that costs, and the trigger for revisiting it.
- [ADR-002: Git-backed AI state sync over object-storage mirroring](../plans/adr-002-git-backed-state-sync.md) — why `.claude/` is a nested git repository synced via `state-sync.sh` instead of Hugging Face bucket mirroring, and the `--state-remote` privacy trade-off.

The unified `reviewer` runs both review passes itself (a primary pass, then a verification pass that refutes the primary findings and drops any that do not survive), so it is a single-nesting-level operation that executes identically on every runtime — there are no separate review-helper agents. The orchestrator is the main-thread persona: it holds `edit`+`execute` and owns the branch/commit/PR and memory/session-log ceremony itself rather than delegating it. UI work goes through the `coder` (which loads the `gradio-streamlit` skill); there is no separate designer agent. The `verifier` is the single owner of the persisted score report.
