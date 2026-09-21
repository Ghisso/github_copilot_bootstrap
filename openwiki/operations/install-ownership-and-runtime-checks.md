---
type: operations
title: Installing the bootstrap, file ownership, and runtime drift checks
description: How scripts/install_bootstrap.py installs and refreshes a consumer, the ownership categories in scripts/runtime_ownership.py (bootstrap-controlled, consumer-owned, tracked authoring adapters, and marker-claimed third-party skill bundles) and what each means on refresh, the .claude/bootstrap-root mirror, the batch updater, and what scripts/check_runtime.py reports.
tags: [install, refresh, ownership, runtime-ownership, check-runtime, drift, bootstrap-root, consumers]
verified:
  - by: openwiki/0.5.2
    at: 2026-09-21T03:23:13.016Z
sources:
  - id: openwiki-source-42e51bf2d8e7ed2f137178e1
    resource: repo://scripts/check_runtime.py
  - id: openwiki-source-7c162969a98fb2f3fa853ffc
    resource: repo://scripts/install_bootstrap.py
  - id: openwiki-source-cae9260f89e696dbf3ed5310
    resource: repo://scripts/runtime_ownership.py
  - id: openwiki-source-c1d529b97e6e15ee64cf946b
    resource: repo://scripts/update_consumers.py
  - id: openwiki-source-92c74e76955d0f817db531c4
    resource: repo://shared/hooks/scripts/state-sync.sh
generated: { by: "claude-code", at: "2026-09-21T03:23:13.016Z" }
---

# Installing the bootstrap, file ownership, and runtime drift checks

Source, tests, and the policies under `shared/policies/` outrank this page.
Where this page and the code disagree, the code is right.

## The ownership model

`scripts/runtime_ownership.py` is the one small contract the generator,
installer, restore script, verifier, and validators share. It classifies
only the boundaries that matter during a refresh, not every generated file.

| Category | Paths | On refresh |
|---|---|---|
| Bootstrap-controlled | everything under `.claude/` not listed below, plus the generated root adapters | replaced with the generated copy; files no longer generated are pruned |
| Root adapters (`ROOT_ADAPTER_PATHS`) | `CLAUDE.md`, `AGENTS.md`, `.mcp.json`, `.codex`, `.agents`, `.vscode/mcp.json`, `.vscode/tasks.json` | regenerated and mirrored into `.claude/bootstrap-root/` so a fresh machine can restore them |
| Copilot surface (`COPILOT_SURFACE_PATHS`) | `.github/agents`, `.github/hooks`, `.github/instructions`, `.github/copilot-instructions.md` | mirrored and ignored like a root adapter unless the consumer chose `--commit-copilot-surface`, in which case it is committed to the outer repository and not mirrored |
| Tracked authoring adapters (`TRACKED_AUTHORING_PATHS`) | `AGENTS.md`, `CLAUDE.md` when tracked by the target's outer Git | preserved byte for byte, not overwritten; this is how the authoring repository keeps its concise root guidance |
| Consumer state (`CONSUMER_STATE_PATHS`) | under `.claude/`: `MEMORY.md`, `plans`, `explorations`, `session_logs`, `quality_reports`, `.cache`, `instructions/project-context.instructions.md`, `settings.local.json` | never compared, overwritten, or deleted; a generated seed is used only on a fresh install |
| State-directory READMEs | `plans/README.md`, `explorations/README.md`, `session_logs/README.md`, `quality_reports/README.md` | regenerated even though their directories are consumer-owned; sibling files untouched |
| Third-party skill bundles (`THIRD_PARTY_SKILL_PATHS`) | `skills/openwiki` under `.claude` or `.agents`, but only once it contains the marker file `.openwiki-install.json` | preserved, not refreshed, excluded from drift and takeover comparisons; the same path without the marker is ordinary bootstrap content |

The marker rule is the important subtlety. A directory shaped like
`skills/openwiki` is bootstrap-generated content until OpenWiki's own
installer writes `.openwiki-install.json` inside it. From then on the
bootstrap installer preserves it, `check_runtime.py` stops drift-checking
it, the `.agents` takeover check ignores it, and the verifier's
bootstrap-root fingerprint excludes it. Ownership keys on a fact only the
intended owner produces, not on path shape.

## `install_bootstrap.py`

```
uv run python scripts/install_bootstrap.py <target-repo> [--source dist/multi-agent]
    [--state-remote <git-url>] [--commit-copilot-surface] [--local-only]
    [--dry-run] [--allow-self]
```

`main` runs a fixed sequence:

1. `validate_install_roots` rejects overlapping source and target trees.
   `--allow-self` permits exactly one overlap, this repository refreshing
   its own overlay from its own `dist/`, and only when the target is the
   bootstrap repository itself.
2. `validate_agents_takeover` refuses to write when an existing `.agents`
   tree cannot be proven generated: it compares the live tree, the mirror
   under `.claude/bootstrap-root/.agents`, and the generated source, all
   with marker-claimed third-party bundles pruned, and reports the
   conflicting paths with
   `Refusing .agents takeover; move or back up the listed content ...`.
3. The Copilot surface mode is resolved: explicit flag, else the mode
   persisted in `.claude/bootstrap-ownership.env`, else local-only.
4. `migrate_pre_existing_state` commits a pre-Git `.claude/` with real
   content as `migrate: import pre-git state` before anything is replaced.
5. `copy_generated_tree` copies `dist/multi-agent/` over the target. It
   logs `preserve consumer state`, `preserve tracked authoring adapter`,
   and `preserve third-party skill` for the categories above, and
   `remove obsolete generated file` for bootstrap-owned files the new
   generation no longer produces. Pruning walks only `.claude/` and the
   restorable root paths, never consumer state or `.claude/.git`.
6. Project name and Python version substitutions are applied to the
   installed instructions.
7. `populate_bootstrap_root` mirrors the root adapters into
   `.claude/bootstrap-root/` so the Git-backed `.claude/` checkout carries
   them.
8. The devcontainer state remote is updated; `merge_gitignore` writes or
   refreshes an idempotent block between
   `# BEGIN multi-agent bootstrap generated/private AI content` and its
   `# END` marker covering the generated overlay (`.claude/`, `.codex/`,
   `.agents/`, the Copilot surface when not committed, `.mcp.json`,
   `AGENTS.md`, `CLAUDE.md`, `.uv-cache/`, the Context Mode provenance
   secret, and `openwiki/.run.json`); runtime scripts are made
   executable; `configure_git_hooks_path` sets `core.hooksPath` to
   `.claude/hooks/git-hooks`; tracked paths that should be ignored are
   reported with the exact `git rm --cached` command.
9. `sync_state_after_install` runs `state-sync.sh` to make the distinct
   `bootstrap: install/update <timestamp>` nested commit and, unless
   `--local-only`, publish it.
10. A reminder that Codex for VS Code may require renewed approval of the
    content-bound `.codex/hooks.json`; the installer never approves hooks
    itself.

`--local-only` performs the full refresh and creates the nested commits but
makes no fetch, `ls-remote`, pull, merge, or push; it prints the nested
status and a quoted `state-sync.sh push` command for later. `--dry-run`
prints the plan without writing.

### Self-refresh of this repository

This repository refreshes its own overlay with
`uv run python scripts/install_bootstrap.py . --local-only --allow-self`.
Tracked `AGENTS.md` and `CLAUDE.md` are preserved as authoring adapters, and
tracked `.mcp.json` and `.codex/config.toml` are preserved as well, so
entries another tool added (for example OpenWiki's MCP server) survive the
refresh and are remirrored. The refresh is also how a stale
`.claude/bootstrap-root/` mirror is healed after a root adapter changes,
which is what clears a
`receipt metadata control-plane provenance is invalid` failure in the
verifier. The refresh prunes obsolete installed copies as a side effect, so
observe stale state before running it if the observation matters.

## Batch updates with `update_consumers.py`

`uv run python scripts/update_consumers.py <repo>...` regenerates `dist/`
(unless `--skip-regen`) and runs the installer for each consumer, passing
through `--dry-run`, `--local-only`, `--allow-self`, and the Copilot
surface flags. Each consumer gets the same migration-then-`bootstrap:`
commit ordering, and the default mode publishes the commit to the nested
`ai-state` remote.

## `check_runtime.py`

`uv run python scripts/check_runtime.py` checks the installed runtime
wiring in this repository. It fails on: a missing required generated file
or directory; invalid plan frontmatter under `.claude/plans/` (delegating
to `validate_plan_frontmatter.py`); runtime drift, meaning an installed
file under `.claude/` or the root adapters whose bytes differ from the
generated source (`drift diagnostic` naming the path and its authoritative
source) or that is absent from the generated target
(`stale runtime path: <path>; authoritative source: absent from generated target`);
a Context Mode dispatch problem (wrong or undeterminable pinned version,
filter or storage misconfiguration); and an unguarded `"${arr[@]}"`
expansion in any hook script, which aborts under `set -u` on macOS's Bash
3.2. It prints `PASS` lines for optional binaries found (`context-mode`,
`npx`, `uv`, `uvx`, `hf`, `gh`), for the Semble launcher, for the Python
baseline matching `pyproject.toml`, and finally
`PASS generated runtime wiring is present`; any failure prints `FAIL ...`
and exits 1.

Drift checking honors the ownership model: consumer state is never
compared, the `.claude/.git` metadata and `bootstrap-root` mirror are
skipped, and a marker-claimed third-party skill bundle under `.claude` or
`.agents` is exempt in both the drift and the obsolete directions.

## Representative tests

`tests/test_install_bootstrap.py` covers the takeover check (unproved
content, a private mirror, symlinked or malformed evidence, a managed mirror
with the outer tree missing, and marker-claimed bundles that are ignored
while unmarked same-shaped directories still conflict), consumer-state
preservation across reinstall, the marker-gated third-party preservation
and drift exemption, and the ignore-block merge. `tests/test_check_runtime.py`
covers the plan-frontmatter delegation and every shape of the Bash 3.2
array-expansion rule.

## Related pages

- [Source, generated output, consumer repo, and nested AI state](/openwiki/architecture/source-generated-consumer-layout.md)
- [Git-backed AI-state sync](/openwiki/operations/git-backed-ai-state-sync.md)
- [Deterministic verification: verify.py modes, receipts, and findings](/openwiki/operations/deterministic-verification.md)
