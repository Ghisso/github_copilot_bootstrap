---
name: safe-consumer-bootstrap-refresh
visibility: background
description: |
  Make consumer bootstrap installers safe when their synchronization hooks are
  deliberately warn-never-fail. Use when adding a local-only/no-network update
  mode, migrating pre-git state, or diagnosing an installer that reports
  success despite a failed nested Git commit.
---

# Safe Consumer Bootstrap Refresh

## Problem

Session hooks often warn and exit successfully so synchronization failures do
not block an AI session. An installer cannot treat that exit code as proof that
state was preserved: a failed `git commit` can otherwise be followed by
generated-file replacement and a misleading success message.

Likewise, checking only that a remote ref did not change proves “no push,” not
“no remote contact.” Fetch, `ls-remote`, pull, or reconciliation may still have
occurred.

## Context / Trigger Conditions

Use this workflow when:

- an installer invokes a fail-open state-sync helper;
- legacy mutable state must be committed before generated files replace it;
- a `--local-only` or offline mode promises no remote Git I/O;
- tests currently assert only that a remote branch was not created or changed.

## Solution

1. Keep session hooks fail-open, but make the installer verify durable
   postconditions itself.
2. Before copying generated files, require the nested repository to have a
   valid `HEAD`, a clean worktree, and the expected migration commit somewhere
   in its history. Abort the installer if any condition fails.
3. After the generated refresh, require the same valid-`HEAD` and clean-tree
   guarantees for the bootstrap commit.
4. Put the local-only boundary at the shared synchronization layer so every
   reachable fetch, `ls-remote`, pull, remote merge, and push path is skipped.
5. In integration tests, set `GIT_TRACE2_EVENT` for the complete child-process
   tree and reject forbidden Git commands. Also assert that remote refs remain
   unchanged.
6. Before refreshing a full consumer, list folders under `.claude/skills/`
   that hold a `SKILL.md`, that the new source does not ship, that are not
   listed in the consumer's `.claude/bootstrap-root/.agents/skills/`, and that
   have no `.project-skill`. Mark or move each one first. A name in that
   record was shipped before and is retired on purpose, so do not mark it,
   unless the record's copy holds `.project-skill`: that folder is a project
   skill that lost its marker, so restore the marker. Also list unmarked
   folders whose name the new source ships and that the shipped-before record
   does not list. The record is the `.claude/bootstrap-root/.agents/skills`
   copy, or the live `.agents/skills/` when that copy is missing. The
   installer refuses such a folder whether a record exists or not, because it
   would overwrite the folder. If the project wrote it, rename the folder and
   its `name:` line, then add `.project-skill`. Otherwise move it out of
   `.claude/skills/`. Rename only when the name clashes with a shipped skill.
   A project with no unmarked skill folder of that kind installs normally,
   even with no record.
7. With no shipped-before record, the installer cannot tell a retired
   bootstrap skill from a project skill. Run the installer with `--dry-run`
   and read the folders it lists. Delete a folder only when its complete
   file list and contents equal that skill's folder at one bootstrap commit.
   That folder is `shared/skills/<name>/` in current history and
   `skills/<name>/` in older commits; `dist/` is not in Git. One way: run
   `git archive` on that folder at the commit, then `diff -r` it against the
   consumer's folder. Otherwise, move the folder out of `.claude/skills/`,
   refresh, and compare the backup with the new copies. For many folders,
   move every listed folder into one backup folder outside `.claude/`,
   refresh, then copy back the project's own skills. To keep a project's own
   skill, keep its name and add `.project-skill`. Rename the folder and its
   `name:` line first only when the bootstrap ships that name.
8. A refresh refuses when the live `.agents/skills/` holds folders that the
   shipped-before record no longer lists. This happens when another clone
   refreshed, because this clone's restore copies files but never deletes
   them. Move the listed folders out of `.agents/skills/` and rerun. Delete
   them only once you have confirmed they are old bootstrap copies.
9. A refresh refuses before any write on an unsafe destination. A path it
   writes is unsafe when any of these holds: a link sits at any part of it; a
   part above the written path exists and is not a real folder; the written
   path is a file that exists and is not a regular file (a folder, or a
   special file such as a FIFO); or the written path is a folder that exists
   and is not a real folder. The check reads each part with `lstat` from the
   project root down and never follows a link. It covers every path the copy
   step writes (with the copy's own skips: existing consumer state, preserved
   tracked adapters, and claimed third-party bundles), the project-name and
   Python-version files (`CLAUDE.md`, `AGENTS.md`, and the two workspace
   instruction files), `.gitignore`, `.claude/bootstrap-ownership.env`, every
   `.claude/bootstrap-root/` adapter path, and `.devcontainer/devcontainer.json`
   when a state remote is set, through `--state-remote` or an exported
   `AI_STATE_REMOTE`. It checks the project-name files and `.gitignore`
   even when no rewrite would happen, so a symlinked `AGENTS.md -> CLAUDE.md`
   is refused. The run refuses once and lists every problem in up to two
   sections. A link is listed under `Refusing to write through symlinks:`;
   replace each link with a regular file or folder, or remove it, then rerun.
   Every other case is listed under
   `Refusing to write over a path of the wrong kind:`, each path with its
   reason; move or rename each listed path, then rerun.
   A second check runs at copy time. Every file copy of a full refresh and
   every folder the copy creates is checked first. If the first check missed
   a path, the run stops with `Refusing to write <path>: ...`. That run may
   be partial. After a legacy migration (pre-Git `.claude/` content, not a
   dry run), the agents takeover, project-skill, and unsafe-destination
   checks run again before the copy; a refusal there comes after the
   migration's own writes. The state-folder READMEs (`.claude/plans/README.md`
   and the three others) are consumer state: an unsafe one is skipped with a
   warning instead of refused. The checks are stricter than the old cleanup:
   a regular file at `.claude/templates`, or a folder holding an untracked
   link at `CLAUDE.md`, used to be resolved silently and is now refused. A
   bootstrap version that turns a generated file into a folder, or the
   reverse, makes each refresh refuse until you move the old item by hand.
   Not checked: the nested state sync's own writes (it may append to
   `.claude/.gitignore` and `.claude/.gitattributes`, and it restores
   `settings.local.json`); hard links; whether the macOS quarantine strip
   (`xattr -rc` over whole folders, consumer state included) follows links;
   and reads through links, for example a preserved, tracked root adapter
   that is a link, which the record copy reads into the AI state, which can
   then be pushed.
10. Preserve the normal human-operated update-and-push behavior when
   local-only mode is absent.

## Retired Skills

The skill trim removed 20 skills. Update consumer MEMORY entries that name
them.

| Retired skill | Where the content went |
| --- | --- |
| `pipeline-patterns` | `.claude/skills/haystack/references/pipelines.md` |
| `haystack-conditional-router` | `.claude/skills/haystack/references/conditional-router.md` |
| `docling-haystack` | `.claude/skills/haystack/references/docling.md` |
| `ollama-chat-generator` | `.claude/skills/haystack/references/ollama-chat.md` |
| `pandas-nan-bool-coercion` | `.claude/skills/data-and-graph-pitfalls/references/pandas-nan-bool.md` |
| `networkx-igraph-graphml-interop` | `.claude/skills/data-and-graph-pitfalls/references/graphml-interop.md` |
| `pyvis-xss-testing` | `.claude/skills/data-and-graph-pitfalls/references/pyvis-xss.md` |
| `csv-driven-integration-tests` | `.claude/skills/data-and-graph-pitfalls/references/csv-driven-tests.md` |
| `deploy-service` | `bentoml-service`, "Deploy" section |
| `context-manager-testing` | one rule in the tests policy |
| `test-helper-public-api` | one rule in the tests policy |
| `dataclass-classvar-constant` | removed; the rule is in the code-standards policy |
| `review-api` | removed; use `code-review` |
| `run-tests` | removed; use `.claude/scripts/verify.py` |
| `refactor`, `pdf`, `caveman-compress`, `domain-type-placement`, `graph-schema-compat-migration`, `extraction-metadata-sourcing` | removed |

## Verification

- Remove Git author identity and confirm migration aborts before generated
  replacement.
- Exercise fresh, existing, legacy, and multi-consumer updater paths.
- Parse Git Trace2 events and assert no `fetch`, `ls-remote`, `pull`, `merge`,
  or `push` command ran in local-only mode.
- Confirm ordered `migrate:` then `bootstrap:` commits and a clean nested
  worktree.
- Confirm the default path still updates `origin/ai-state`.

## Example

```bash
uv run python scripts/update_consumers.py --local-only /path/to/consumer
git -C /path/to/consumer/.claude log --oneline -2
bash /path/to/consumer/.claude/hooks/scripts/state-sync.sh push
```

## References

- `scripts/install_bootstrap.py`
- `scripts/update_consumers.py`
- `shared/hooks/scripts/state-sync.sh`
- `scripts/validate_targets.py`
