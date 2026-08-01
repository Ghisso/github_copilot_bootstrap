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
PRE-FLIGHT -> BRANCH -> PLAN -> IMPLEMENT -> VERIFY -> REVIEW -> DOCUMENT -> SCORE -> LEARN -> SESSION LOG -> COMMIT
```

Lifecycle hook scripts keep that workflow stateful without mutating during validation hooks:

- `enforce-branch-state.sh` runs before branch commands and validates clean `dev`, branch naming, and big-plan metadata. It recognizes `git checkout -b`, `git checkout -B`, `git switch -c`, `git switch -C`, `git switch --create`, and `git switch --create=<branch>` forms.
- `record-branch-state.sh` runs after successful branch creation and records `originating_branch`, `implementation_branch`, `started_at`, and `current_phase`.
- `enforce-commit-gate.sh` runs before normal commits and requires completed small-plan metadata, completed closeout logs, `[LEARN]` evidence, and a fresh score >= 90 report for the current branch and phase. The report must also match `base_ref`, merge-base SHA, and current HEAD SHA; record `tests_passed: true`, not be `tests_skipped`, and be `dirty: false` (no unstaged changes); target a repo-relative path; and carry a `content_hash` (`git hash-object` of the diff against the merge base) that still matches the working tree. The content hash replaces the old mtime freshness check, so an amend/rebase/editor-touch that preserves content no longer false-blocks while any real post-scoring edit does. Report selection is newest-by-`generated_at`, not filename order, and failure messages name the exact mismatch plus the regenerate command. The git classifiers tokenize past global flags (`git -C .`, `git -c k=v`, `--git-dir=`), and an unparseable payload fails closed with a non-zero exit. `git_targets_nested_claude` (`_lib-frontmatter.sh`) exempts `git commit`s that target the nested `ai-state` repo (`git -C .claude commit`, `--git-dir=.claude/.git`, `--work-tree .claude`) from the outer-repo ceremony — `state-sync.sh` commits state there constantly and has no plan/score/closeout of its own to satisfy. This is checked per git invocation, not per whole command string: a compound command mixing a nested-`.claude` call with an unrelated outer-repo `git commit` (e.g. `git -C .claude status && git commit -m "..."`) must still be gated for that second commit, so the helper walks each `git ...` segment individually and only exempts when the matching `commit` invocation itself carries the nested-repo flag.
- `record-commit-closeout.sh` runs after successful commits and advances the big-plan phase or marks the big plan complete only after the intercepted commit subject correlates with `HEAD`. `commit_subject_from_command` tokenizes the command (honoring quotes) to read `-m`/`--message`/`-F <file>`/`--file=<file>`; `-F -`/`--file=-` (message piped via stdin) has no subject the hook can read from the command string alone, so it leaves a clear `additionalContext` note naming the supported forms and pointing at manual phase advancement instead of silently skipping the phase advance with no explanation.
- `enforce-pr-gate.sh` blocks PRs or pushes unless every phase is complete, the base is `dev`, and bypass commits have been acknowledged. It exempts nested `.claude/` pushes (`state-sync.sh push`) the same way and with the same per-invocation scoping as the commit gate above.
- `session-start-state.sh` and `stop-session-log-check.sh` provide reminders for stale phase, score, and session-log state.

Bypass commit prefixes `fixup!`, `squash!`, `chore(typo):`, and `docs(typo):` are allowed for short-lived recovery work, but they skip only the plan-ceremony checks (small-plan/closeout/score/LEARN) — branch-shape validation still runs, so a bypass commit off a non-`*_implementation` branch is still denied. Bypasses are logged and must be acknowledged before PR or push.

The two safety-critical guards, `protect-files.sh` and `git-protection.sh`, run their primary checks in pure bash with no `uv` dependency (the Python path in `protect-files.sh` is an enhancement used only when `uv` is present). On an internal error a guard fails toward `ask` (deny on Codex) rather than a silent allow, and the PreToolUse gates exit non-zero on an unparseable payload so runtimes that key blocking on exit status deny the call.

`git-protection.sh` scans a possibly-chained Bash command for destructive git subcommands (`reset --hard`, `push --force`, `checkout --`, `clean -fd`, deleting `main`/`master`). Because `_shell_tokenize` drops shell operators (`;`/`|`/`&`) as mere separators, the flattened token stream for `git clean -f && ls -d /tmp` has no trace of the `&&` — scanning "does -d appear anywhere after clean" would misattribute `ls`'s unrelated `-d` to `git clean`, denying a wholly benign command (and the same shape misattributes an unrelated later `--force` to an earlier `git push`). `git_danger_reason` bounds each invocation's argument scan to `_unquoted_operator_boundary` — the point right before the next unquoted operator — so a later chained command's flags can never bleed into an earlier invocation's danger check, while a real danger later in the same chain (`git status && git reset --hard`) is still caught on its own invocation.

`protect-files.sh`'s bash pass only recognizes explicit path shapes (a leading `/`, `./`, `../`, a known dotfolder prefix, or a tracked extension) — it deliberately does **not** treat "contains a `/`" as path-like, since that flagged ordinary prose or unrelated tool arguments (a docs sentence mentioning `docs/section`, a script that merely imports something named `Secret`) as a protected-file edit. The Python enhancement pass is stricter where it matters instead: for a token containing `/` that the bash pass would ignore, it checks whether the *basename* looks like a secret (`.env*`, `credentials*`, `*.pem`/`*.key`, or `secret` in the name) before flagging it — so `cp app/secrets/db_secret.txt other/` is still caught even though neither path has a recognized extension or absolute prefix. That Python pass must run whenever `uv` is available regardless of whether the bash pass found any candidates of its own; short-circuiting it when the coarse bash scan comes up empty would silently let exactly this kind of relative secret-file copy through.

## Git-Backed State Sync

`.claude/` in each consumer is a plain, self-contained git repository (its own `.git/` inside `.claude/`), tracking both the bootstrap-controlled files and mutable AI state (`MEMORY.md`, `plans/**`, `explorations/**`, `session_logs/**`, `quality_reports/**`) on one branch, `ai-state`. The outer consumer repo gitignores `.claude/` entirely, so the nested repo is invisible to the code branches. See [ADR-002](../plans/adr-002-git-backed-state-sync.md) for the full rationale and the alternatives it replaced (Hugging Face bucket mirroring, `git worktree`, committing state into code branches) — `git worktree` in particular was rejected, not overlooked: a worktree must belong to the same repository as its parent, which would rule out pointing state at a different remote (the `--state-remote` privacy escape) and would couple the state checkout to the outer repo's worktree bookkeeping.

**This is a genuinely separate repository, not a branch of the outer one — plain `git branch`/`git log` run at the consumer root will never show `ai-state` or its commits.** Inspect it with `git -C .claude <command>` (e.g. `git -C .claude branch`, `git -C .claude log --oneline`), or `cd .claude` first. Looking for `ai-state` with the outer repo's own `git branch -a` and finding nothing is expected, not a sign that the sync failed.

`shared/hooks/scripts/state-sync.sh` (pure bash, no `uv`/Python) implements seven subcommands. It drains stdin with the same two-second timeout as the old helper. `setup`, `pull`, `checkpoint`, `publish`, `push`, and `migrate-from-hf` remain warn-never-fail for hook compatibility and emit operational diagnostics on stderr; only `status` deliberately writes its stable report to stdout.

- **`setup`** — idempotent. If `.claude/.git` is missing: `git init`, resolve and configure the remote (`AI_STATE_REMOTE` / `--state-remote` at install time, else the outer repo's own `origin`), commit whatever is already on disk (there is always something — at minimum this script itself), then reconcile with `origin/ai-state` via `git merge --allow-unrelated-histories` if it already exists remotely (a real merge, not a bare checkout, so it combines file-by-file instead of refusing to overwrite untracked files that are about to converge anyway). A genuine conflict aborts the merge and warns, leaving the local commit as the source of truth.
- **`pull`** — records local nested changes, then reconciles committed state with `origin/ai-state`. On conflict, it aborts cleanly and leaves local files intact.
- **`checkpoint`** — initializes local nested Git state if needed and commits local AI state as the durable boundary. It performs no remote Git operation, including no fetch, `ls-remote`, pull, merge, or push.
- **`publish`** — sends already committed state only. It never stages or commits; if the nested worktree is dirty, it warns and preserves that uncheckpointed state. From a clean worktree it reconciles with `origin/ai-state`, then pushes; repeated clean publication is a no-op. With `--local-only`, it skips remote interaction without mutation.
- **`push`** — the backward-compatible composition: checkpoint, then publish. Existing SessionStop, post-commit, and VS Code task wiring continues to use it.
- **`status`** — read-only and network-free. It reports whether the nested repository is initialized, its clean/dirty worktree state, remote configuration without exposing its URL, and cached tracking ahead/behind information when available. It also reports the existing error-log path and the last state-sync error; it never fetches or exposes credentials.
- **`migrate-from-hf`** — one-way, explicit: if `.claude/` has content but no `.claude/.git` yet, initializes it, commits everything on disk as `migrate: import pre-git state`, then reconciles and publishes when safe. No automatic pull from the retired Hugging Face bucket occurs; the local tree is the source of truth at migration time. `install_bootstrap.py` invokes this before replacing generated files.

Bootstrap updates land as `bootstrap:`-prefixed commits (made by `install_bootstrap.py` through the updater); session state lands as `session:`-prefixed commits when a consumer's Stop hook runs the normal push flow. The commit log on `ai-state` cleanly separates the two — `git -C .claude log --stat` is a full audit trail of what every session and every bootstrap update changed, something the old bucket mirror had no equivalent of.

**Multi-writer conflict policy.** `init_nested_repo` writes a `.gitattributes` into the nested `.claude/` repo alongside its `.gitignore`. Append-only machine logs matching `session_logs/*.log` get git's built-in `merge=union` driver, so two sessions appending different lines to the same log auto-reconcile during rebase instead of conflicting. Narrative state — `plans/**`, `MEMORY.md`, and session-log prose — intentionally keeps the default conflict-and-abort behavior, so a genuine divergence there still stops for a manual semantic merge rather than being silently resolved ours/theirs. Both files are written by `init_nested_repo` at nested-repo init, so this policy reaches every fresh nested `.claude/` repo the same way the existing `.gitignore` does — not just repos created before this policy existed.

**Durable checkpoints vs. best-effort hooks.** `checkpoint` is the explicit network-free local durability boundary. Post-commit continues to invoke compatible `push`, which attempts checkpoint then publication. Runtime-specific Stop paths are best-effort: they run only when the runtime emits the event, and closing a browser tab or editor window is not guaranteed to do so. Run `checkpoint` explicitly when local durability matters before a later `publish`; the hooks remain warn-never-fail, so sync trouble never blocks a session or outer-repo commit.

**Runtime lifecycle boundaries.** Matching Stop handlers can run concurrently, so Codex and Claude each use one sequential wrapper. Both continue after a child failure; checkpointed local commits remain available for a later retry, with failures recorded in `.claude/session_logs/hooks-errors.log` and inspectable through `state-sync.sh status`.

| Runtime | Turn-scoped Stop | Prompt retry | Failure/end boundary |
| --- | --- | --- | --- |
| Codex | [`codex-stop.sh`](../shared/hooks/scripts/codex-stop.sh): log, check, checkpoint, publish; one JSON stdout response | `push`, 60 seconds | Delayed best-effort SessionEnd: local `checkpoint`, 3 seconds, no publication |
| Claude CLI / VS Code | [`claude-stop.sh`](../shared/hooks/scripts/claude-stop.sh): log, check, checkpoint, publish; no stdout | `push`, 60 seconds | StopFailure: local `checkpoint`; SessionEnd: `push`, 60 seconds |

Claude VS Code bundles the Claude runtime and reads the same generated `.claude/settings.json` as the CLI; no second settings adapter exists. Post-commit and the manual **AI state: push** VS Code task remain the durable checkpoint-and-publish paths.

Both human CLIs push by default after a complete refresh. Their `--local-only`
mode still refreshes all bootstrap-controlled files and creates durable nested
commits, including ordered `migrate:` then `bootstrap:` commits for a legacy
consumer, but has a hard remote-I/O boundary: it performs no fetch,
`ls-remote`, pull, merge, or push. The installer prints nested status and a
shell-quoted manual `state-sync.sh push` command so publication is deliberate.

`state-sync.sh` and `restore-root-adapters.sh` (which copies `.claude/bootstrap-root/` — the root-level adapter files that live outside `.claude/`, such as `CLAUDE.md`/`AGENTS.md`/`.mcp.json`/`.codex/**` — back out to the repo root) are rendered in two locations: `.claude/hooks/scripts/` for normal use, and `.devcontainer/` so `post-start.sh` has a copy it can run before `.claude/` exists at all on a fresh clone.

`MEMORY.md` is single-homed as a tracked file in `.claude/`, evolving via `session:`/`bootstrap:` commits like everything else — no separate bundle or restore-order dependency the old bucket split required.

## VS Code Tasks

`.vscode/tasks.json` (source: `shared/vscode/tasks.json`) provides AI state sync that works without an active AI tool session:

- **AI state: pull** — runs automatically on `folderOpen` (VS Code prompts once to allow automatic tasks). Pulls state silently in the background via `state-sync.sh pull`.
- **AI state: push** — run manually via `Tasks: Run Task` or a keyboard shortcut binding. It retains the compatible `state-sync.sh push` checkpoint-then-publish behavior.

These complement the AI SessionStart/Stop hooks, which retain the normal
pull/push flow for sessions in that consumer. For a guaranteed local boundary,
run `state-sync.sh checkpoint` explicitly before publishing later.

## Custom Agents

Custom agents are source-controlled under `shared/agents/<agent-id>/`.

Each agent contains:

- `agent.yaml`: stable metadata, capabilities, visibility, delegates, and per-target model/effort intent.
- `prompt.md`: target-neutral behavior.

The generator derives Copilot, Claude Code, and Codex adapters from those two files. Copilot model fields are target bindings, not portable semantics. GitHub Copilot agent `model` fields must be a single supported Copilot model string. Claude and Codex adapters must not include Copilot model pins.

The Claude Code target carries per-agent model and reasoning-effort tiers. Each `agent.yaml` sets `model_intent.claude-code` to an object (`{ "model": ..., "effort": ... }`); the generator emits matching `model:` and `effort:` frontmatter on each `.claude/agents/*.md`, skipping `inherit` values so the orchestrator (main-thread persona) follows the session. Effort-heavy roles run on the stronger model (planner `opus`/`max`, reviewer and coder `sonnet`/`xhigh`, documenter `sonnet`/`medium`); the mechanical `verifier` runs on `haiku` with no `effort:` line, because Haiku does not support the effort field. **Extended thinking is intentionally not configured per agent**: Claude Code subagents inherit the session's thinking state, so there is no per-agent knob to set.

Agent names are identical across every target — the generator performs no per-target renaming. Codex agents are generated as project-scoped `.codex/agents/*.toml` adapters that point to `.claude/agents/`. The root Codex session is intentionally unpinned in `.codex/config.toml`, leaving the user free to choose the interactive model and effort. Each custom agent overrides both `model` and `model_reasoning_effort` from its canonical `model_intent.openai-codex`: orchestrator Sol/xhigh, planner Sol/max, reviewer Sol/high, coder Terra/high, documenter Luna/medium, and verifier Luna/low. The validator requires those generated values to match the canonical intent exactly.

`coder`'s `model_intent.openai-codex` additionally carries an `escalate_to` key (`{ "model": "gpt-5.6-sol", "effort": "xhigh" }`), declarative-only: the generator does not emit a second adapter file for it. Codex subagent spawning supports explicit per-call `model`/`model_reasoning_effort` overrides on an existing named agent (`developers.openai.com/codex/subagents`: "explicit spawn values override `agents.default_subagent_model` and `agents.default_subagent_reasoning_effort`"), so `shared/agents/orchestrator/prompt.md` instructs the orchestrator to re-delegate a `coder` fix with those override values — instead of retrying at the base Terra/high tier — when `verifier` fails or `reviewer` surfaces a CRITICAL/MAJOR/`ponytail` finding on that diff, capped at one escalation per phase. `scripts/validate_targets.py` checks that `escalate_to`'s model/effort pair is allow-listed, differs from the base tier, and appears verbatim in the orchestrator prompt text, so the data and the instruction that acts on it cannot silently drift apart. Claude Code has no per-invocation effort override, so this lane is Codex-only.

Codex skills are wired through `[[skills.config]]` entries in `.codex/config.toml` whose `path` points at each skill's `SKILL.md` file; the config omits the redundant flat `[features]` block (hooks are on by default), exposes MultiAgent V2 spawn metadata through the `agents` namespace so named model/effort profiles are selectable, and wires `PreCompact` plus the Codex lifecycle boundaries summarized above.

## Design Decisions

- [ADR-001: Multi-target bootstrap over native per-platform packaging](../plans/adr-001-multi-target-lcd.md) — why this repo generates thin adapters for Copilot/Claude/Codex from one shared basis instead of shipping Claude-native plugin packaging, what that costs, and the trigger for revisiting it.
- [ADR-002: Git-backed AI state sync over object-storage mirroring](../plans/adr-002-git-backed-state-sync.md) — why `.claude/` is a nested git repository synced via `state-sync.sh` instead of Hugging Face bucket mirroring, and the `--state-remote` privacy trade-off.

The unified `reviewer` runs both review passes itself (a primary pass, then a verification pass that refutes the primary findings and drops any that do not survive), so it is a single-nesting-level operation that executes identically on every runtime — there are no separate review-helper agents. The orchestrator is the main-thread persona: it holds `edit`+`execute` and owns the branch/commit/PR and memory/session-log ceremony itself rather than delegating it. UI work goes through the `coder` (which loads the `gradio-streamlit` skill); there is no separate designer agent. The `verifier` is the single owner of the persisted score report.
