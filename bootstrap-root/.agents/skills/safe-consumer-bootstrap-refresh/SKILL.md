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
   skill that lost its marker, so restore the marker. The installer refuses
   the same set.
7. With no shipped-before record, the installer cannot tell a retired
   bootstrap skill from a project skill. Run the installer with `--dry-run`
   and read the folders it lists. For each one, check whether every file is
   an unmodified bootstrap copy: the file's `git hash-object` must appear in
   `git rev-list --all --objects` of a bootstrap checkout. Remove unmodified
   copies. Mark the project's own folders with `.project-skill`.
8. A refresh refuses when the live `.agents/skills/` holds folders that the
   shipped-before record no longer lists. This happens when another clone
   refreshed, because this clone's restore copies files but never deletes
   them. Delete the listed folders if you did not create them, then rerun.
9. A refresh refuses before any write when a path it would write is a symlink
   or sits under a symlinked folder. The message starts
   `Refusing to write through symlinks:`. Replace each link with a regular
   file or folder, or remove it.
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
