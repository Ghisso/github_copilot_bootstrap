# Multi-Agent Bootstrap

A reusable multi-target agent bootstrap I drop into my other projects.

This repository is my personal starter kit for opinionated agent workflows in Python AI engineering repos. It packages the hooks, agents, skills, and instruction files I want available everywhere so I can keep quality and execution style consistent across GitHub Copilot, Claude Code, and OpenAI Codex.

Inspired and adapted from:

- [claude-code-my-workflow](https://github.com/pedrohcgs/claude-code-my-workflow)
- [armory](https://github.com/Mathews-Tom/armory)
- [ultralight](https://burkeholland.github.io/ultralight/)

## What This Repo Is

This is not an app.
It is a source-of-truth plus generated bootstrap. Bootstrap maintainers edit `shared/`; `dist/multi-agent/` is the generated installable output. In an installed project, `.claude/` is the canonical runtime basis, while generated root files such as `CLAUDE.md` and `AGENTS.md` are entrypoints and must not be hand-edited.

Main goals:

- Keep coding workflow consistent across repositories.
- Enforce planning, verification, and quality gates.
- Make multi-agent execution predictable and repeatable.
- Capture learned patterns as reusable skills.

## Main Philosophy

I use a strict execution loop:

PRE-FLIGHT -> BRANCH -> PLAN -> PONYTAIL -> IMPLEMENT -> VERIFY -> REVIEW -> DOCUMENT -> SCORE -> LEARN -> SESSION LOG -> COMMIT

Core principles:

- Start from `dev`, branch for each big plan, and keep plan frontmatter current.
- Plan first for non-trivial work and split big plans into commit-sized small plans.
- Run every coding task through Ponytail `full`: reuse first, standard library/native platform next, minimum correct diff last.
- Config-first design for new features.
- Verify every change with tests, typing, and linting.
- Use the unified reviewer to challenge implementation quality.
- Ship only after score >= 90, a matching findings report with zero CRITICAL findings and zero Ponytail findings, documentation updates, learning capture, and closeout logs.
- Preserve lessons learned in memory and session logs.

## Quick Install

Regenerate first, then install the single generated bootstrap into a target repo.
The installer copies the generated AI files, substitutes the target repo name into
the workspace instructions, keeps `.devcontainer/` trackable, adds an idempotent
`.gitignore` block for generated/private AI content, and turns `.claude/` into its
own nested git repository on a branch named `ai-state` that carries both the
bootstrap files and mutable AI state (plans, session logs, memory) — see
[ADR-002](plans/adr-002-git-backed-state-sync.md).

After installation, record project-specific facts in
`.claude/instructions/project-context.instructions.md`. Keep the generated root
guidance as an entrypoint to that installed basis; change bootstrap behavior in
`shared/` and regenerate rather than editing root adapters or `dist/` directly.

By default the nested repo's remote is this project's own `origin`, so no separate
credentials or bucket configuration are needed. Pass `--state-remote <git-url>`
(env `AI_STATE_REMOTE`) to point it somewhere else instead — a private personal
repo, for example, if you would rather AI state not be visible to anyone with
read access to the code remote.

Because it is a separate repository — not a worktree, not a branch of the outer
one — `ai-state` never shows up in the outer repo's own `git branch`/`git log`.
That is expected, not a sync failure. Inspect it explicitly: `git -C .claude
branch`, `git -C .claude log --oneline`, etc.

```bash
set -euo pipefail

# 1) Set paths
BOOTSTRAP_REPO="/absolute/path/to/github_copilot_bootstrap"
TARGET_REPO="/absolute/path/to/your-project"

# 2) Regenerate installable output
cd "$BOOTSTRAP_REPO"
uv run python scripts/generate_targets.py --all

# 3) Install into the project root
uv run python scripts/install_bootstrap.py "$TARGET_REPO"

# 4) Commit the trackable devcontainer and ignore rule in the target repo
cd "$TARGET_REPO"
git add .devcontainer .gitignore
git commit -m "chore: add AI devcontainer bootstrap"
```

If you are already inside this bootstrap repo and only need to set the target path:

```bash
set -euo pipefail

TARGET_REPO="/absolute/path/to/your-project"
uv run python scripts/generate_targets.py --all
uv run python scripts/install_bootstrap.py "$TARGET_REPO"
```

After an actual install or update, reopen or reload the repository in Codex for
VS Code. Project-hook trust is bound to the content/hash of
`.codex/hooks.json`, so changed generated hooks can require review and renewed
approval. Review and approve them when Codex prompts before relying on the
lifecycle hooks. The installer only reports this boundary; it never approves
hooks or changes user trust settings.

To keep AI state off the code remote instead of the default:

```bash
uv run python scripts/install_bootstrap.py "$TARGET_REPO" --state-remote git@github.com:you/private-ai-state.git
```

By default, a fresh install creates `bootstrap: init ai-state`; a repeat or
legacy refresh creates `bootstrap: update <timestamp>` after any migration.
The installer pushes that nested `ai-state` commit. Missing push access or
network failures produce warnings and leave the commit local; publish it later
with `state-sync.sh push` or the manual VS Code task. Normal Stop-hook runs do
not originate installer updates, but their `git add -A` commits any uncommitted
nested changes — including locally modified bootstrap-controlled files — as
session state. Clean installer/updater commits and the normal pull/rebase flow
are the intended protection.

To refresh a consumer completely while working offline or before an explicit
review, use `--local-only`:

```bash
uv run python scripts/install_bootstrap.py "$TARGET_REPO" --local-only
```

This refreshes every bootstrap-controlled file and commits the nested state
without contacting its remote: no fetch, `ls-remote`, pull, merge, or push. If
the consumer has pre-git `.claude/` content, the installer first records
`migrate: import pre-git state`, then records the bootstrap update. It prints
the nested `ai-state` status and a shell-safe `Publish later: ...` command for
the target path.

### Self-installing this source repository

This repository can use the generated bootstrap itself to dogfood the same
`ai-state` lifecycle as consumer repositories. Its editable source of truth
remains `shared/`; do **not** commit the generated root adapters back into the
bootstrap source tree.

When the local `.claude/` directory already is a nested Git repository without
a remote, configure its `origin` to the outer repository's `origin` and restrict
its refspecs to `ai-state` before installing. The install then creates or updates
the nested-state commit, and Codex's `SessionStart`/`Stop` hooks pull/push that
branch automatically. `Stop` is best-effort — it fires only when the agent
process emits the event, not on tab closure — so the `post-commit` git hook
(pushed after every commit) is the durable checkpoint; see [Hooks](#hooks).

The source repository tracks authoring versions of files such as `AGENTS.md`,
`.codex/config.toml`, and MCP config. After self-installing, restore those
tracked source files and keep the generated runtime overlay local via
`.git/info/exclude` (for example `.codex/hooks.json`, `.devcontainer/`, and
`.vscode/tasks.json`). This keeps `git status` clean while preserving the
installed hooks and devcontainer files locally.

The installed `.claude/bootstrap-ownership.env` is an inert ownership manifest,
not a shell configuration file. It records the selected Copilot mode and the
root adapters that state restoration may copy. The installer, restorer, updater,
and runtime checker use that one contract: tracked authoring adapters are
preserved where appropriate, bootstrap-controlled runtime files are refreshed,
and consumer-owned state remains untouched.

## Updating Existing Repos

When you update this bootstrap (new hooks, revised instructions, agent changes),
push the new version to all consumer repos with:

```bash
uv run python scripts/update_consumers.py \
  /path/to/repo1 \
  /path/to/repo2 \
  /path/to/repo3
```

The script regenerates `dist/` automatically, then delegates each consumer to
`install_bootstrap.py`. The installer owns legacy migration: when `.claude/`
predates git-backed state, it first creates `migrate: import pre-git state`
before replacing bootstrap-controlled files and creating its distinct
`bootstrap: update <timestamp>` commit. The default updater publishes that
commit to the nested `ai-state` remote.

Files that exist only in the consumer repo — `MEMORY.md`, plans, session logs,
quality reports, explorations — are never touched by the file-copy step. They
are state, tracked in git history rather than files a bucket pull could
silently overwrite, so there is no backup/restore step to run around them.
The generated `MEMORY.md` is a fresh-install seed only: if the consumer already
has `.claude/MEMORY.md`, reinstall and legacy migration preserve it byte-for-byte.
Refreshes also prune obsolete bootstrap-controlled files, including files no
longer generated after an upgrade or mode change. They do not prune consumer
state or nested `.claude/.git` metadata.

```bash
# Preview without writing
uv run python scripts/update_consumers.py --dry-run /path/to/repo
```

The dry-run notice describes the trust action that an actual update may require;
it does not claim that hook content changed. Default and `--local-only` updates
print the same per-consumer reminder. After each actual update, reopen/reload
the repository in Codex for VS Code and approve project hooks if prompted.

For a durable offline batch refresh, pass `--local-only`. It applies the full
generated bootstrap to every target and preserves the same ordered migration
and bootstrap commits, but makes no remote reads or writes. Each target reports
its nested status and a quoted command to publish later.

```bash
uv run python scripts/update_consumers.py --local-only /path/to/repo
```

When self-installing this repository, ignored generated overlays under the root
`.github/` tree are valid only when they are byte-identical to generated output.
Validation rejects a tracked, unignored, or stale overlay; keep editable source
files in `shared/` instead.

Generated layout:

- `.devcontainer/`: trackable GPU sandbox and AI-state sync bootloader for consumer repos; Node.js 22 + `context-mode` pre-installed; the container mounts `~/.cache/huggingface` from the host so credentials and cached models are available without re-authenticating (still used by projects themselves — HF sync for AI state moved to git, see [ADR-002](plans/adr-002-git-backed-state-sync.md))
- `.claude/`: installed canonical runtime basis for skills, canonical agent bodies, instructions, plans, explorations, logs, reports, memory, templates, prompts, hook scripts, and Claude settings — its own nested git repo on branch `ai-state`, gitignored in the outer repo
- `.github/`, `.vscode/mcp.json`, `.vscode/tasks.json`: GitHub Copilot native adapters/config; `tasks.json` auto-pulls AI state on folder open and exposes a manual push task
- `CLAUDE.md`, `.mcp.json`: Claude Code native entrypoint/config
- `AGENTS.md`, `.codex/`: OpenAI Codex native entrypoint/adapters/config

Consumer repos should commit `.devcontainer/` and `.gitignore`, but generated AI
content such as `.claude/`, `.codex/`, `AGENTS.md`, `CLAUDE.md`, native adapters,
and MCP files should stay ignored. A fresh clone can reopen in the devcontainer;
`post-start.sh` restores the ignored AI content by checking `.claude/` out from
the `ai-state` branch (and copying `.claude/bootstrap-root/` back out to the root
adapters — `CLAUDE.md`, `AGENTS.md`, etc.) using the same git credentials as the
code checkout, with no separate auth to configure.

**Changing dev machines without a devcontainer:** if you open a fresh clone in
plain VS Code, the `.vscode/tasks.json` `folderOpen` task now bootstraps state
automatically — it calls `.devcontainer/state-sync.sh setup` (idempotent; creates
`.claude/.git` and resolves the remote from the outer repo's own `origin` if
`.claude/` doesn't exist yet) followed by `pull`, so opening the folder is enough.
Without VS Code at all, run the same two commands by hand once:

```bash
bash .devcontainer/state-sync.sh setup
bash .devcontainer/state-sync.sh pull
```

Both are safe to (re-)run anytime — `setup` no-ops once `.claude/.git` already
exists. `.claude/hooks/scripts/state-sync.sh` (the copy normal hooks call) can't
be used for this first bootstrap: it doesn't exist until `.claude/` does, which
is exactly why `.devcontainer/` carries its own copy of the same script.

### GitHub Copilot: local-IDE vs cloud

By default the installer gitignores the GitHub Copilot surface
(`.github/agents/`, `.github/hooks/`, `.github/instructions/`,
`.github/copilot-instructions.md`), so **only local-IDE Copilot is configured** —
cloud Copilot agents read that surface only from the committed default branch and
will not see gitignored files. To enable cloud Copilot, install with
`--commit-copilot-surface`, which keeps those paths out of the ignore block so you
can commit them (like `.devcontainer/`); the AI state in `.claude/` still stays
ignored and git-backed. The selected mode is persisted in the ownership manifest:
later installs and `update_consumers.py` retain it unless you explicitly pass
`--commit-copilot-surface` or `--no-commit-copilot-surface`.

If you do not use one of the tools, you may delete its native adapter/config
files locally after installing. A later installer refresh restores every path
present in `dist/`; persistent pruning requires changing the source/ownership
contract and regenerating. Keep `.claude/` unless you are intentionally removing
the shared basis.

Optional pruning after copy:

- No Copilot: delete `.github/` and `.vscode/mcp.json`.
- No Claude Code: delete `CLAUDE.md`, `.mcp.json`, and `.claude/settings.json`.
- No Codex: delete `AGENTS.md` and `.codex/`.

## Architecture Flow

```mermaid
flowchart LR
  U[Developer Request] --> A[Orchestrator / Planner]
  A --> C[Coder]
  C --> V[Verifier + Quality Gates]
  V --> D[Documenter]
  D --> L[Learn + Session Log]

  I[Instructions] --> A
  I --> C

  S[Skills] --> A
  S --> C

  H[Hooks] --> T[Tool Execution Guardrails]
  T --> C

  R[Reviewer] --> V
  C --> R

  L --> O[Commit or PR Decision]
```

Interpretation:

- Instructions define non-negotiable rules.
- Skills provide reusable playbooks for specific tasks.
- Agents execute and review the work.
- Hooks enforce safety and log lifecycle events.
- Verifier and quality gates decide whether code is ready.

## What Is Included

- Generated bootstrap: installable output in `dist/multi-agent/` (gitignored — run `uv run python scripts/generate_targets.py --all` to build)
- Source policies: reusable instruction files in [shared/policies/](shared/policies/)
- Agents: canonical metadata and prompts in [shared/agents/](shared/agents/)
- Review profiles: unified reviewer checklists in [shared/review-profiles/](shared/review-profiles/)
- Skills: reusable workflows in [shared/skills/](shared/skills/)
- Ponytail: pinned MIT-licensed coding and over-engineering-review skills with provenance in [shared/third_party/ponytail/](shared/third_party/ponytail/)
- Hooks: policy and observability scripts in [shared/hooks/](shared/hooks/)
- Devcontainer: GPU sandbox and git-backed AI-state sync bootloader in [shared/devcontainer/](shared/devcontainer/) — Node.js 22 (multi-stage build; avoids Ubuntu's outdated Node 18), `bubblewrap`, and `context-mode` are pre-installed; handles GID/UID conflicts in NVIDIA base images and mounts the host HF cache for seamless auth; `--cap-add=SYS_ADMIN` and `--security-opt=seccomp=unconfined` are set so bubblewrap namespace creation works inside Docker; `huggingface_hub>=1.0` stays pinned for the projects' own use (models/datasets), not for AI state sync anymore — see [ADR-002](plans/adr-002-git-backed-state-sync.md)
- MCP config: shared Semble and context-mode server definitions in [shared/mcp/](shared/mcp/)
- Templates, prompts, memory, plans, session logs, quality reports, and quality scoring rendered into the shared `.claude/` basis

## Most Important Instructions

These are the source files that render into `.claude/instructions/` in every generated target:

- [workspace.instructions.md](shared/policies/workspace.instructions.md)
  - Shared workspace guidance
  - Agent and review-profile overview
  - Skill visibility and verification defaults
- [workflow.instructions.md](shared/policies/workflow.instructions.md)
  - Pre-flight, branch, plan, implementation, verification, review, score, documentation, learn, session-log, commit protocol
  - Branch lifecycle and commit/PR gates
  - Session logging and recovery reminders
- [quality-and-testing.instructions.md](shared/policies/quality-and-testing.instructions.md)
  - Verification commands and required testing order
  - Quality scoring rubric and gates
- [code-standards.instructions.md](shared/policies/code-standards.instructions.md)
  - Naming, architecture patterns, deprecation protocol
- [tests.instructions.md](shared/policies/tests.instructions.md)
  - Fixture design, mocking boundaries, async testing patterns
- [config-first-design.instructions.md](shared/policies/config-first-design.instructions.md)
  - Pure ConfigStore approach (no YAML)
  - Dataclass validation and registration patterns
- [api-service-standards.instructions.md](shared/policies/api-service-standards.instructions.md)
  - BentoML service design, async endpoints, Pydantic validation
- [deployment.instructions.md](shared/policies/deployment.instructions.md)
  - Pre-deploy checks, Bento build/container workflow, health checks
- [tool-routing.instructions.md](shared/policies/tool-routing.instructions.md)
  - Routing between direct reads, `rg`, Semble, and context-mode
  - Single authoritative home for retrieval-tool choice; agents point here instead of restating it
- [agent-reporting.instructions.md](shared/policies/agent-reporting.instructions.md)
  - Single home for how agents report back (caveman-full prose, structured content preserved) with the documenter's normal-prose exception

### Conditional policy applicability

`shared/policies/` is the sole editable policy library. Every policy declares
target-neutral `applicability`: either `always` or an explicit YAML list of
repository-relative path patterns. Generation copies the canonical policy to
`.claude/instructions/`; target-native files are discovery adapters, never
second authoring sources.

Claude Code is the primary scoped-policy path: conditional policies generate
`.claude/rules/*.instructions.md` files with equivalent `paths` frontmatter.
Always-on policy remains in concise root guidance rather than consuming an
unconditional rule. This matches Claude's native path-scoped rules, which load
when a matching file is read. See [Claude Code rules and memory
documentation](https://code.claude.com/docs/en/memory).

Codex is also primary: its root `AGENTS.md` holds durable repository-wide
guidance. Codex discovers `AGENTS.md` from the repository root to the current
working directory; closer files take precedence, and the combined project
guidance limit defaults to 32 KiB. Generate nested `AGENTS.md` only where a
policy owns one stable concrete directory. Mixed, file-specific, or glob scopes
use the corresponding `.claude/skills/` workflow instead, so the root guidance
budget is not widened speculatively. See [Codex AGENTS.md
guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

GitHub Copilot is compatibility coverage: its `.github/instructions/` adapters
derive `applyTo` from the same target-neutral patterns. Claude/Copilot scope
parity is structurally validated; real-client loading probes remain Phase I
work.

## Most Important Skills

Skills have machine-readable `visibility: public|background` frontmatter. **Public** skills are intended for direct use; **background** skills are hidden helpers loaded by description match or by agents.

There are many skills; these are the high-leverage ones I rely on most:

Core workflow:

- [ponytail](shared/skills/ponytail/SKILL.md)
- [ponytail-review](shared/skills/ponytail-review/SKILL.md)
- [plan-decomposition](shared/skills/plan-decomposition/SKILL.md)
- [create-feature](shared/skills/create-feature/SKILL.md)
- [run-tests](shared/skills/run-tests/SKILL.md)
- [refactor](shared/skills/refactor/SKILL.md)
- [code-review](shared/skills/code-review/SKILL.md)

Quality and architecture:

- [code-style](shared/skills/code-style/SKILL.md)
- [testing-patterns](shared/skills/testing-patterns/SKILL.md)
- [review-api](shared/skills/review-api/SKILL.md)
- [text-to-sql-safety](shared/skills/text-to-sql-safety/SKILL.md)
- [debug-investigator](shared/skills/debug-investigator/SKILL.md)

Communication and context control:

- [caveman](shared/skills/caveman/SKILL.md)
- [caveman-compress](shared/skills/caveman-compress/SKILL.md)

Project acceleration:

- [setup-project](shared/skills/setup-project/SKILL.md)
- [add-dependency](shared/skills/add-dependency/SKILL.md)
- [deploy-service](shared/skills/deploy-service/SKILL.md)
- [hydra-config](shared/skills/hydra-config/SKILL.md)
- [bentoml-service](shared/skills/bentoml-service/SKILL.md)

These skills encode battle-tested workflows and reduce ad-hoc execution.

## Agent System

The agent layer gives me orchestration plus profile-driven reviews. Full shared agent bodies render into `.claude/agents/`; Copilot keeps thin native wrappers in `.github/agents/`. Codex custom-agent TOML files embed the transformed canonical shared prompt, so a spawned Codex agent receives its complete role contract without first reading a Claude-native agent file.

Primary flow for complex work:

- orchestrator -> planner -> coder -> verifier -> reviewer -> documenter

Current agents:

- orchestrator
- planner
- coder
- reviewer
- verifier
- documenter

Claude Code and Codex both carry per-agent model/effort tiers (Copilot uses its own model pins):

| Agent | Claude model | Claude effort | Codex model | Codex effort |
| --- | --- | --- | --- | --- |
| orchestrator | session (`/model`) | session (`/effort`) | `gpt-5.6-sol` | `xhigh` |
| planner | `opus` | `max` | `gpt-5.6-sol` | `max` |
| reviewer | `sonnet` | `xhigh` | `gpt-5.6-sol` | `high` |
| coder | `sonnet` | `xhigh` | `gpt-5.6-terra` | `high` |
| documenter | `sonnet` | `medium` | `gpt-5.6-luna` | `medium` |
| verifier | `haiku` | — | `gpt-5.6-luna` | `low` |

**Claude:** the orchestrator is the main thread, so its model and effort come from the session — run it on **Opus or Fable**. The `verifier` runs on `haiku` with no effort, because Haiku does not support the effort field. Extended thinking is inherited from the session (Claude Code has no per-agent thinking knob), so it is intentionally not set per agent.

**Codex:** the interactive root session is intentionally unpinned, so users can choose its model and reasoning effort manually. Every generated `.codex/agents/*.toml` pins its own model and `model_reasoning_effort` from the canonical `model_intent.openai-codex` object; in particular, the orchestrator is Sol/xhigh. Its `developer_instructions` consists of a generated metadata header followed by the exact target-transformed `shared/agents/<id>/prompt.md` body. `agent.yaml` remains the single source for metadata and model intent; generated agent files omit MCP and skill overrides, so they inherit the trusted project's `.codex/config.toml` wiring. The generated config uses `agents.max_concurrent_threads_per_session = 6`, not the legacy `max_threads`, and omits the redundant `agents.enabled = true` because the documented default is enabled. Its `[features.multi_agent_v2]` table exposes spawn metadata through the `agents` namespace so Codex can select those named profiles instead of inheriting the parent model. Keep that shim and the separate `max_depth = 1` limit until the [dated Codex routing compatibility record](docs/2026-08-08-codex-routing-compatibility.md) removal gate is met; generation checks are structural, not a claim of current native six-role routing proof. Sol is reserved for coordination, planning, and review; Terra handles implementation; Luna handles documentation and mechanical verification.

**Escalation on failure (Codex only):** `coder`'s `model_intent.openai-codex` also declares an `escalate_to` (`gpt-5.6-sol`/`xhigh`), documentation-only in `agent.yaml` — it is not consumed by the generator, so there is no second `.codex/agents/coder-*.toml` file. Codex subagent spawning supports explicit per-call `model`/`model_reasoning_effort` overrides on an existing named agent, so the orchestrator's own prompt carries the instruction: if `verifier` fails or `reviewer` returns a CRITICAL/MAJOR/ponytail finding on a diff `coder` just produced, re-delegate the fix to `coder` with those override values instead of retrying at the base Terra/high tier, capped at one escalation per phase. A validator check keeps the `agent.yaml` data and the prompt wording from silently drifting apart. Claude Code has no per-invocation effort override, so there is no equivalent lane on that target.

The unified `reviewer` loads one or more profiles from `.claude/review-profiles/` (`code`, `architecture`, `security`, `tests`, `api`, `config`, `performance`, `documentation`, `domain`), routed via the single authoritative table in `.claude/instructions/workspace.instructions.md`. It runs two passes itself — a primary pass, then a verification pass that refutes the primary findings and drops any that do not survive — then synthesizes the survivors into one report, with no helper agents.

Orchestrator routing:

- The orchestrator does a shallow exploration pass, then decides between `--mode micro-plan` (small, well-scoped changes) and `--mode full-plan` (new features, cross-cutting changes) before delegating to the planner.
- The planner does NOT self-classify; routing ownership stays with the orchestrator.
- Planner micro-plan mode: load skills → draft → done (no interview required).
- Planner full-plan mode: intake → exploration → interview (min 2 rounds) → module sketch → draft → optional devil's advocate.
- Control-plane files (`.claude/hooks/`, `.claude/settings.json`, `.github/hooks/`, `.codex/`, `.mcp.json`, `.devcontainer/`, `CLAUDE.md`, `AGENTS.md`) — the consumer-side surfaces that affect every session — always use full-plan and always trigger profile-driven review.

Coder skill loading:

- Tier 1 (always): `ponytail/SKILL.md` in `full` mode, `code-style/SKILL.md`, `testing-patterns/SKILL.md`
- Tier 2: task-specific skills loaded by type (e.g. `hydra-config` for config work, `bentoml-service` for API work)
- Coder pauses and asks the user before modifying any control-plane file.

## Hooks

Hooks provide guardrails and lightweight observability.

All hook commands route through [run-hook.sh](shared/hooks/scripts/run-hook.sh), a dispatcher that resolves the repo root robustly — via `BASH_SOURCE`, environment variable fallbacks (`GITHUB_WORKSPACE`, `WORKSPACE_FOLDER`, `VSCODE_CWD`), then `git rev-parse`. This avoids the broken-path failures that occur when `$CLAUDE_PROJECT_DIR` is empty or when `git rev-parse` runs from the wrong directory.

[hooks.json](shared/hooks/hooks.json) sets `"cwd": "."` on every entry rather than `"${workspaceFolder}"`. Copilot's hook runner does not interpolate VS Code variables, so using the literal string would resolve to a non-existent path and produce `spawn /bin/sh ENOENT` errors. `run-hook.sh` resolves the repo root itself, so `"."` is sufficient.

Generated Claude and Codex hook configs execute `run-hook.sh` directly, so the generator marks the generated dispatcher executable and the target validator fails if it is not runnable.

Configured events:

- SessionStart
  - [session-start-state.sh](shared/hooks/scripts/session-start-state.sh) reminds agents about the current branch, active plan phase, latest score report, and any open lifecycle state
  - [context-mode-dispatch.sh](shared/hooks/scripts/context-mode-dispatch.sh) forwards optional context-mode lifecycle events when available
- PreToolUse
  - [protect-files.sh](shared/hooks/scripts/protect-files.sh) blocks protected files (env files, key files, secrets patterns, lockfiles) and hook config files. Its primary check is pure bash (no `uv` dependency); a Python precision pass runs only as an enhancement when `uv` is present, and an internal error fails toward `ask` (deny on Codex), never a silent allow
  - [git-protection.sh](shared/hooks/scripts/git-protection.sh) blocks dangerous git commands (force push, reset --hard, clean -fd, deleting main/master) in pure bash — no `uv` dependency — and tokenizes past global git flags so forms like `git -C . reset --hard` are still caught
  - [enforce-branch-state.sh](shared/hooks/scripts/enforce-branch-state.sh) validates branch creation from clean `dev` into `<plan_name>_implementation`, including `git checkout -b`, `git checkout -B`, `git switch -c`, `git switch -C`, and `git switch --create`
  - [enforce-commit-gate.sh](shared/hooks/scripts/enforce-commit-gate.sh) blocks normal commits until the small plan is complete, the closeout log is completed, `[LEARN]` evidence exists, and a fresh score >= 90 report matches the current branch, phase, base ref, merge base, and HEAD SHA. The report must also record `tests_passed: true`, not be `tests_skipped`, and be `dirty: false` (no unstaged changes), and its `content_hash` — `git hash-object` of the diff against the merge base — must still match, so an amend/rebase/editor-touch that preserves content does not false-block while any real post-scoring edit does. The gate additionally requires a fresh, matching `findings-*.json` report (produced by [record_findings.py](shared/scripts/record_findings.py) from the reviewer's surviving findings) with `counts.critical == 0`; non-documentation diffs also require `ponytail_reviewed: true` and `ponytail_findings: 0`. Failure messages name the exact mismatch and regenerate command. Classifiers tokenize past global git flags, so `git -C . commit` / `git -c k=v commit` cannot bypass the gate; on an unparseable payload the gate fails closed (exit 2)
  - [enforce-pr-gate.sh](shared/hooks/scripts/enforce-pr-gate.sh) requires `gh pr create --base dev` and blocks implementation-branch pushes until every phase is complete, bypasses are acknowledged, and the final phase's findings report has `counts.major == 0` (in addition to the `counts.critical == 0` already required to land the commit), via `assert_push_invariants` in `_lib-frontmatter.sh` (shared with the `pre-push` git hook below)
  - [context-mode-dispatch.sh](shared/hooks/scripts/context-mode-dispatch.sh) forwards optional context-mode hook events after guardrails run
- PostToolUse / PreCompact
  - [record-branch-state.sh](shared/hooks/scripts/record-branch-state.sh) records branch metadata and the active phase in the big plan after successful branch creation
  - [record-commit-closeout.sh](shared/hooks/scripts/record-commit-closeout.sh) advances the big-plan phase only after correlating the intercepted commit subject with `HEAD`; it completes the big plan after the final phase and logs allowed bypass commits
  - [context-mode-dispatch.sh](shared/hooks/scripts/context-mode-dispatch.sh) forwards optional context-mode lifecycle events and warns without failing when context-mode is unavailable
- SessionStart / Stop
  - [session-log.sh](shared/hooks/scripts/session-log.sh) appends lifecycle entries to `.claude/session_logs/hooks-sessions.log`; generates timestamps in bash (Claude Code payloads carry no `timestamp` field) and accepts both snake_case (`hook_event_name`) and camelCase (`hookEventName`) field names for cross-tool compatibility
- SessionStart
  - [state-sync.sh](shared/hooks/scripts/state-sync.sh) `pull` first records local nested state, then reconciles it with the configured `ai-state` remote. A genuine conflict aborts cleanly, prints recovery guidance, and leaves local state intact; a sync problem never blocks a session from starting.
- Stop
  - [stop-session-log-check.sh](shared/hooks/scripts/stop-session-log-check.sh) warns when code or docs changed but no session log was updated for the day
  - `state-sync.sh push` remains the compatible checkpoint-then-publish flow: it commits local nested changes, reconciles committed state, then publishes it when safe. Publication refuses a dirty nested worktree, preserving it for the next checkpoint; reconciliation conflicts skip publication rather than force a non-fast-forward push. Operational diagnostics go to stderr, and failures are also recorded in `.claude/session_logs/hooks-errors.log`; sync remains warn-never-fail and drains stdin with a two-second timeout. See [ADR-002](plans/adr-002-git-backed-state-sync.md) for why it is git-backed instead of a Hugging Face bucket mirror.
  - Stop is a best-effort checkpoint-and-publish attempt: it only runs when the agent process emits the Stop event. Closing a browser tab or an editor window is not a guaranteed lifecycle event, so use `state-sync.sh checkpoint` when you need a network-free local durability boundary; use `publish` later to send that committed clean state. The existing post-commit hook and **AI state: push** VS Code task still invoke compatible `push`.
  - Codex Stop is turn-scoped. Its single [codex-stop.sh](shared/hooks/scripts/codex-stop.sh) wrapper runs session logging, the session-log check, `checkpoint`, then best-effort `publish` in that order. Its stdout is exactly one valid JSON response; child diagnostics stay on stderr and failures remain recoverable through `.claude/session_logs/hooks-errors.log`.
  - Claude CLI and the Claude runtime bundled with VS Code use the same generated `.claude/settings.json`; no separate VS Code adapter is installed. Its turn-scoped [claude-stop.sh](shared/hooks/scripts/claude-stop.sh) wrapper runs the same four steps sequentially, with no wrapper stdout.
- Prompt and end retries
  - Codex and Claude `UserPromptSubmit` run compatible `state-sync.sh push` with a 60-second timeout. A timeout or network failure preserves the local checkpoint for a later retry; inspect `state-sync.sh status` and `.claude/session_logs/hooks-errors.log` for recovery details.
  - Codex `SessionEnd` is delayed and best-effort: it runs local-only `checkpoint` with a three-second limit and does not publish. Claude `StopFailure` also runs local-only `checkpoint`; its `SessionEnd` runs compatible `push` with a 60-second limit. These do not replace post-commit or the manual **AI state: push** task.
- post-commit (git hook)
  - [post-commit](shared/hooks/git-hooks/post-commit) runs `state-sync.sh push` after every successful outer-repo commit, publishing plans, reports, memory, and session logs finalized by that commit without waiting on a Stop event that may never arrive. Like the Stop-hook push, it is warn-never-fail: git ignores a git hook's exit status, and `state-sync.sh` itself only warns and exits 0 on a missing remote, offline network, or rebase conflict, so a sync problem never blocks or fails the commit. Installed the same way as `commit-msg` and `pre-push` below, via `core.hooksPath`.

### Deterministic Commit And Push Gates (Git Hooks)

`enforce-commit-gate.sh` and `enforce-pr-gate.sh` above are `PreToolUse` hooks: they can only gate the AI agent's own Bash tool calls, so a human `git commit`/`git push`, an IDE button, a script, or a `git ci` alias never pass through them. Two generated git hooks close that gap — [commit-msg](shared/hooks/git-hooks/commit-msg) for the commit invariant and [pre-push](shared/hooks/git-hooks/pre-push) for the push invariant — both installed via `core.hooksPath` (set by [install_bootstrap.py](scripts/install_bootstrap.py) and, for fresh devcontainers, by `post-start.sh` before the state pull runs). Because they fire from git's own lifecycle, every commit or push reaching a `<plan_name>_implementation` branch is gated on one code path regardless of how it was invoked, with no command string to parse, no stdout convention, and no timeout to fail open on.

Two layers, two invariants, one shared contract each:

- **Commit invariant** — `enforce-commit-gate.sh` (`PreToolUse`) and `commit-msg` (git hook) both call `assert_commit_invariants` in [_lib-frontmatter.sh](shared/hooks/scripts/_lib-frontmatter.sh), covering the small-plan/closeout/score/LEARN checks.
- **Push invariant** — `enforce-pr-gate.sh` (`PreToolUse`) and `pre-push` (git hook) both call `assert_push_invariants` in the same file, covering the big-plan/phase-completeness/commit-count/bypass-acknowledgment checks. `pre-push` reads ref lines from stdin and derives the branch from the ref being pushed, not from whatever is checked out, so `git push origin foo_implementation` from elsewhere still gates `foo_implementation`. `gh pr create --base dev` has no push-hook analog and stays `PreToolUse`-only.

Both invariants deliberately diverge on branch scope the same way: the `PreToolUse` layer denies an *agent* commit/push on any wrong branch, while the git-hook layer passes through untouched on any branch other than `<plan_name>_implementation` — merges, deletions, and casual commits/pushes on `dev`/`main` are unaffected.

- `git commit --no-verify` / `git push --no-verify` are the sanctioned manual escapes: git skips the hook entirely, and there is no git hook that fires when hooks are skipped.
- `.claude/` is gitignored in consumers, so on a fresh clone *before* `.claude/` is checked out, `.claude/hooks/git-hooks/` does not exist yet — git prints a warning and runs no hook (fails open for humans until the checkout completes). Since AI state moved from a Hugging Face bucket to a nested git repo ([ADR-002](plans/adr-002-git-backed-state-sync.md)), this window shrank: `post-start.sh` runs `state-sync.sh setup` (which checks `.claude/` out from the `ai-state` branch using the same git credentials as the code checkout — no separate auth to configure) and sets `core.hooksPath` immediately after, before the subsequent `state-sync.sh pull`, so the devcontainer path closes the window at checkout time rather than waiting on an authenticated bucket pull.
- Per `githooks(5)`, `commit-msg` also fires for `git merge`, not just `git commit`. A plain merge commit carries no authored content of its own, so on an implementation branch it passes through unledgered — the ceremony re-attaches at the next real commit. `git rebase` and `git cherry-pick` do **not** invoke `commit-msg` at all (git behavior, not a bootstrap gap); the commits they create skip the git layer, but the next real commit is still gated. `git commit --amend` does invoke it, and `content_hash` freshness survives a content-preserving amend. The `MERGE_HEAD` passthrough is, like `--no-verify`, a known accepted escape: `git merge --no-commit` followed by manually staging extra changes lands ungated content on an implementation branch, since the hook cannot distinguish a pure merge from a merge plus manual staging.
- See [docs/plan-deterministic-commit-gate.md](docs/plan-deterministic-commit-gate.md) and [plans/plan-post-review-hardening.md](plans/plan-post-review-hardening.md) for the full design rationale.

Core Copilot hook adapter source: [hooks.json](shared/hooks/hooks.json)

Design intent:

- deny risky actions early
- keep audit trails lightweight and local
- leave nuanced coaching (reminders/cadence) to instruction files

## Verification Defaults

Expected verification commands after implementation:

- uv run pytest tests/ -q --tb=short
- uv run mypy src/ --ignore-missing-imports --explicit-package-bases
- uv run ruff check src/ tests/
- uv run ruff format src/ tests/
- uv run python .claude/scripts/quality_score.py src/ --phase <current_phase> --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
- uv run python .claude/scripts/record_findings.py src/ --profile code --profile security --profile ponytail --phase <current_phase> --base-ref dev --findings-json <path-or-stdin> --out .claude/quality_reports/findings-<timestamp>.json

Quality gates:

- >= 95: excellence target
- >= 90: required for commit and PR closeout
- < 90: blocked until implementation, verification, review, and score are rerun
- findings report `counts.critical == 0`: required for commit
- findings report `counts.major == 0`: additionally required for PR/push closeout
- findings report `ponytail_reviewed == true` and `ponytail_findings == 0`: required for every non-documentation commit and push

Documentation gate:

- after score >= 90, update docs for changed public interfaces, config, workflows, and user-facing behavior before commit or PR closeout

## Optional Retrieval Helpers

VS Code can load the checked-in MCP servers from [.vscode/mcp.json](.vscode/mcp.json):

- `semble` uses `uvx --from "semble[mcp]" semble`.
- `context-mode` uses the portable bare `context-mode` command.

**Inside the devcontainer**, Node.js 22 and `context-mode` are pre-installed — no extra setup needed.

**Outside the devcontainer**, hook events go through `.claude/hooks/scripts/context-mode-dispatch.sh`, which maps the calling target id to the context-mode target name, falls back to `npx -y context-mode hook ...` when `npx` is available, and otherwise prints `WARN` while exiting successfully.

Install `context-mode` with npm when Node.js is already available:

```bash
npm install -g context-mode
context-mode --help
```

If Node.js is not installed and you do not want to use `sudo`, install the official Node.js LTS binary under `~/.local` and expose it through `~/.local/bin`:

```bash
NODE_VERSION="v24.15.0"
NODE_DIST="node-${NODE_VERSION}-linux-x64"
mkdir -p "$HOME/.local/bin" "$HOME/.local/nodejs"
curl -L -o "/tmp/${NODE_DIST}.tar.xz" "https://nodejs.org/dist/${NODE_VERSION}/${NODE_DIST}.tar.xz"
tar -xJf "/tmp/${NODE_DIST}.tar.xz" -C "$HOME/.local/nodejs"
ln -sf "$HOME/.local/nodejs/${NODE_DIST}/bin/node" "$HOME/.local/bin/node"
ln -sf "$HOME/.local/nodejs/${NODE_DIST}/bin/npm" "$HOME/.local/bin/npm"
ln -sf "$HOME/.local/nodejs/${NODE_DIST}/bin/npx" "$HOME/.local/bin/npx"
"$HOME/.local/bin/npm" install -g context-mode
ln -sf "$HOME/.local/nodejs/${NODE_DIST}/bin/context-mode" "$HOME/.local/bin/context-mode"
```

Make sure `~/.local/bin` is on `PATH` before starting VS Code:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Run the bootstrap runtime check after copying optional surfaces:

```bash
uv run python scripts/check_runtime.py
```

## How To Use This Bootstrap In Another Project

1. Regenerate the installable output with `uv run python scripts/generate_targets.py --all`.
2. Copy `dist/multi-agent/` into your target project.
3. Put project-specific stack details in `.claude/instructions/project-context.instructions.md`; do not edit generated root guidance.
4. Keep hooks enabled and ensure `.claude/hooks/scripts/*.sh` is executable in your environment.
5. Update instruction apply scopes to match your project paths.
6. Add or remove skills and agents in `shared/`, then regenerate instead of hand-editing `dist/`.

## Customization Notes

This bootstrap is intentionally opinionated, because consistency beats improvisation when quality matters.

If you customize it, prioritize:

- preserving the PRE-FLIGHT -> BRANCH -> PLAN -> PONYTAIL -> IMPLEMENT -> VERIFY -> REVIEW -> DOCUMENT -> SCORE -> LEARN -> SESSION LOG -> COMMIT workflow
- keeping verification commands accurate for your stack
- maintaining clear ownership between instructions, skills, and hooks
- treating terse-mode and compression as opt-in guardrailed tools, not blanket rewrites of source-of-truth customization files

See [plans/adr-001-multi-target-lcd.md](plans/adr-001-multi-target-lcd.md) for the recorded decision behind supporting Copilot, Claude, and Codex from one shared basis instead of native Claude plugin packaging, and [plans/adr-002-git-backed-state-sync.md](plans/adr-002-git-backed-state-sync.md) for why AI state syncs through a nested git repository instead of a Hugging Face bucket.
