---
type: operations
title: Git-backed AI-state sync
description: How the nested .claude repository on the ai-state branch stores installed bootstrap files and mutable AI state, what state-sync.sh's setup, pull, checkpoint, publish, push, and status commands do, how the outer post-commit hook checkpoints and publishes, why every path is warn-never-fail, and how root adapters are restored from the bootstrap-root mirror.
tags: [state-sync, ai-state, nested-repository, git, hooks, durability, restore]
verified:
  - by: openwiki/0.5.2
    at: 2026-09-21T03:23:13.016Z
sources:
  - id: openwiki-source-115b2dad781e2a2c5b5a980d
    resource: repo://docs/architecture.md
  - id: openwiki-source-df4b60402a82ef6f0601d69d
    resource: repo://shared/hooks/git-hooks/post-commit
  - id: openwiki-source-b5b439338ba5fba465bf930c
    resource: repo://shared/hooks/scripts/restore-root-adapters.sh
  - id: openwiki-source-92c74e76955d0f817db531c4
    resource: repo://shared/hooks/scripts/state-sync.sh
  - id: openwiki-source-c3f54dc63823dfff60ef659d
    resource: repo://tests/test_state_sync.py
generated: { by: "claude-code", at: "2026-09-21T03:23:13.016Z" }
---

# Git-backed AI-state sync

Source, tests, and the policies under `shared/policies/` outrank this page.
Where this page and the code disagree, the code is right.

## A separate repository inside the repository

In every consumer, `.claude/` is a plain, self-contained Git repository with
its own `.git/` directory, on one branch named `ai-state`. It tracks both
the installed bootstrap files and the mutable AI state: `MEMORY.md`,
`plans/**`, `explorations/**`, `session_logs/**`, and `quality_reports/**`
(findings reports and verification receipts). The outer repository ignores
`.claude/` entirely, so `git branch` and `git log` at the repository root
never show `ai-state` or its commits. Inspect it with
`git -C .claude <command>`.

The nested repository's remote is, by default, the outer repository's own
`origin`, with fetch and push refspecs pinned to the `ai-state` branch; an
install-time `--state-remote` can point it elsewhere for privacy. Commits
fall into two prefixes: `bootstrap:` for installer and updater refreshes and
`session:` for state saved by session hooks, so `git -C .claude log --stat`
is an audit trail of what every session and every bootstrap update changed.

## `state-sync.sh`

`shared/hooks/scripts/state-sync.sh` is pure Bash with no `uv` or Python
dependency. It is rendered into two places: `.claude/hooks/scripts/` for
normal use and `.devcontainer/` as a bootstrap copy that exists before
`.claude/` does on a fresh clone. It resolves the repository root from its
own location or from `AI_STATE_REPO_ROOT`, and honors `--local-only` or
`AI_STATE_LOCAL_ONLY=1` to skip every remote interaction.

| Command | What it does |
|---|---|
| `setup` | Idempotent. When `.claude/.git` is missing: `git init`, configure the remote and pinned refspecs, write the nested `.gitignore` and `.gitattributes`, commit whatever is on disk, reconcile with `origin/ai-state` by a real merge that allows unrelated histories, then restore root adapters and activate the outer Git hooks. When the nested repository already exists it stays local and does none of that. |
| `pull` | Records local nested changes, reconciles committed state with `origin/ai-state`, and only after that succeeds restores root adapters and checkpoints. A conflict aborts cleanly, leaves local files intact, and skips restoration, so unreconciled state never overwrites adapters. |
| `checkpoint` | The network-free durability boundary: initializes the nested repository if needed, then commits local AI state. No fetch, `ls-remote`, pull, merge, or push. |
| `publish` | Sends already committed state only. A dirty nested worktree makes it warn and preserve the uncheckpointed state; from a clean worktree it reconciles, then pushes. Repeated clean publication is a no-op. |
| `push` | The compatible composition: `checkpoint`, then `publish`. A failed checkpoint skips publication. |
| `status` | Read-only and network-free: initialized or not, clean or dirty, remote configured without exposing its URL, cached ahead and behind counts, rebase state, and the last recorded error. |
| `migrate-from-hf` | One-way import of pre-Git state as a `migrate:` commit; historical. |

Every mutating command runs through `dispatch_mutating`, which first checks
for a rebase left in progress inside the nested repository. A protected
rebase state is preserved rather than clobbered, and the command returns a
distinct status so callers can tell "refused to touch an active rebase"
from an ordinary failure. `pull` can clear the half-initialized rebase state
its own previous run left behind, but never someone else's.

### Warn, never fail

The dispatcher at the bottom of the script wraps every command in
`|| warn "... failed; continuing."` and always exits 0. Warnings go to
stderr and to `.claude/session_logs/hooks-errors.log`. This is deliberate:
the script runs from SessionStart and Stop hooks, from the outer
`post-commit` Git hook, and from VS Code tasks, and a missing remote, an
offline network, or a rebase conflict must never block a session or turn a
completed outer commit into a failed one. The cost is that a sync problem is
visible only in the log and in `status`, so the SessionStart hook reports
hook-path and sync problems as context for the next session.

### What the nested repository never tracks

`init_nested_repo` writes a nested `.gitignore` that excludes `.cache/`
(Context Mode storage and the OpenWiki guard's snapshot directory) and
`session_logs/hooks-errors.log`; `checkpoint` and every successful
reconcile untrack those paths if an earlier commit tracked them, without
deleting the files. `session_logs/hooks-bypass.log` stays tracked. The
`.gitattributes` gives append-only `session_logs/*.log` files Git's
`merge=union` driver so two sessions appending to the same log reconcile
automatically; plans, `MEMORY.md`, and session-log prose keep the default
conflict-and-abort behavior so a real divergence stops for a human.

## Root adapters and the bootstrap-root mirror

`state-sync.sh` only checks out `.claude/`. The installer-owned files that
live outside it (`AGENTS.md`, `CLAUDE.md`, `.mcp.json`, `.codex/**`,
`.agents/**`, `.vscode/*.json`, and the Copilot surface when it is not
committed) are carried inside the nested repository under
`.claude/bootstrap-root/` and copied back to their real locations by
`restore-root-adapters.sh`, which reads the list from
`.claude/bootstrap-ownership.env`. `state-sync.sh` calls it on a fresh
`setup`, on every successful `pull`, and on a `checkpoint` that had to
initialize the repository. The same mirror is what `verify.py` fingerprints
to prove control-plane provenance, which is why an adapter edited outside a
bootstrap refresh fails verification until the refresh remirrors it.

`configure_outer_hooks_path`, called from the same restore path, sets the
outer repository's `core.hooksPath` to `.claude/hooks/git-hooks` once that
directory exists. A matching value is left alone; a different value is
overwritten with a warning naming the old one; a failure only warns. It is
the one write `state-sync.sh` makes outside `.claude/`, and the value is a
fixed literal, so a hostile `ai-state` remote cannot inject anything into
the outer Git configuration.

## Where sync runs

- **SessionStart** on every host: `state-sync.sh pull`, followed by
  `session-start-state.sh`, which reports the active plan and phase and
  tells the session to run `state-sync.sh setup` when the hooks path is not
  active.
- **Stop**: `claude-stop.sh` and `codex-stop.sh` run `checkpoint` then
  `publish` after session logging. Codex also runs `push` on
  `UserPromptSubmit` and a three-second local `checkpoint` on `SessionEnd`.
  Stop paths are best-effort; closing an editor tab does not guarantee the
  event fires.
- **Outer `post-commit` Git hook**: after every outer commit it first runs
  `record-commit-closeout.sh` to advance a completed phase, then
  `state-sync.sh push` with stdin from `/dev/null`. Git ignores the hook's
  exit status and the script never fails, so this is the durable
  publication boundary the Stop hooks cannot promise.
- **VS Code tasks**: an automatic `AI state: pull` on folder open and a
  manual `AI state: push`, independent of any AI session.

## Representative tests

`tests/test_state_sync.py` runs the real script against temporary
repositories: checkpoint commits locally without remote I/O; setup and pull
activate the outer hooks path and do not rewrite a matching one; the error
log and cache are never tracked and are untracked without deletion; publish
refuses a dirty worktree and is idempotent from a clean one; push stays
checkpoint-then-publish; status is credential-safe; and a series of rebase
cases prove that half-initialized state is cleared only by the run that
created it while a valid pre-existing rebase is preserved.

## Related pages

- [Installing the bootstrap, file ownership, and runtime drift checks](/openwiki/operations/install-ownership-and-runtime-checks.md)
- [Hook dispatcher and guardrail scripts](/openwiki/architecture/hooks-and-guardrails.md)
- [Source, generated output, consumer repo, and nested AI state](/openwiki/architecture/source-generated-consumer-layout.md)
