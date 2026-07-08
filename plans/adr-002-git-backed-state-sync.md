# ADR-002: Git-backed AI state sync over object-storage mirroring

**Status:** Accepted
**Date:** 2026-07-08
**Revisit trigger:** if a consumer's branch policy forbids the `ai-state` branch appearing on `origin` and `--state-remote` proves too heavy an escape, or if Git hosting adds native support for a second, access-scoped ref namespace per repo.

## Decision

`.claude/` in each consumer becomes a plain, self-contained git repository (its own `.git/` inside `.claude/`), tracking both the bootstrap-controlled files and the mutable AI state on one branch, `ai-state`. By default its remote is the consumer repo's own `origin`; `install_bootstrap.py --state-remote <url>` (env `AI_STATE_REMOTE`) points it anywhere else instead — a private personal repo, for example. `shared/hooks/scripts/state-sync.sh` (`setup`/`pull`/`push`/`migrate-from-hf`, pure bash) replaces `hf-ai-sync.py`/`hf-ai-sync.sh` and the Hugging Face bucket sync they drove. Bootstrap updates land as `bootstrap:`-prefixed commits (installer/updater); session state lands as `session:`-prefixed commits (the Stop hook).

## Context

All AI state previously lived in gitignored directories mirrored to a Hugging Face bucket ([docs/architecture.md](../docs/architecture.md) "HF State Sync and Pull Safety", now rewritten). Object storage gave none of the properties this data actually needs:

| Problem | Object-storage symptom |
| --- | --- |
| Last-writer-wins | Two machines pushing state meant the later push silently destroyed the earlier one; `.state_backups/` existed only to soften this, and was documented as a non-durable local convenience |
| No history | A plan file had only its current contents — "when did phase 3 complete?" was answerable only if session-log discipline happened to capture it, even though that discipline exists to record exactly this history |
| Monotonic drift | `push-state` never deleted; reconciliation was the opt-in `--prune`, made opt-in precisely because a blind mirror is dangerous |
| Separate auth and config | HF token resolution, bucket path resolution, `sync_bucket` API-version guards, and a CLI fallback — a whole dependency surface that exists only because the state wasn't where the code credentials already are |
| Fresh-clone window | A new clone had no `.claude/` (so no `commit-msg` hook) until an authenticated HF pull completed ([plan-deterministic-commit-gate.md](plan-deterministic-commit-gate.md) D2) |

Git provides all five natively: rejected non-fast-forward pushes instead of silent overwrites, `git log` as the audit trail, deletion tracked as commits, the same credentials as the code remote, and checkout as the restore mechanism.

### Alternatives considered and rejected

- **Status quo (HF bucket mirroring).** Keeps the problems above; the entire reason for this ADR.
- **`git worktree` of an orphan branch.** A worktree must belong to the same repository as its parent, which rules out pointing state at a different remote (the privacy escape below) and couples the state checkout to the outer repo's worktree bookkeeping — prunable, breaks if the outer `.git` moves, interacts badly with bind-mounted devcontainers.
- **Committing state into the consumer repo's own branches.** Atomic with code commits, but publishes AI ceremony (session logs, plan churn) into shared code history and forces a philosophy change repo-wide; not worth it for a personal/small-team workflow.
- **File-level sync (e.g. Syncthing).** Solves last-writer-wins no better than the HF bucket did, and adds a background daemon and a second piece of infrastructure to run and trust, in exchange for nothing git doesn't already provide.

### The D2/D3 trade-off

By default, `ai-state` lives on the consumer's own `origin`, born with no shared ancestry with `dev`/`main`, so collaborators never encounter it unless they fetch it deliberately — but it is visible to anyone with read access to that remote, and some hosts/policies may not expect an unexpected branch to appear. `--state-remote` (`AI_STATE_REMOTE`) is the escape: point the nested repo at a different git URL — a personal private repo, most naturally — and everything else about the mechanism (setup/pull/push, rebase-with-autostash, warn-never-fail) is unchanged, because the sync script never hardcodes which remote it talks to.

## Consequences

- The Hugging Face bucket's remaining role in this bootstrap shrinks to what it was always used for outside this repo's own machinery: the devcontainer's model/dataset cache (`~/.cache/huggingface`, `huggingface_hub` pin). `hf-ai-sync.py`, `hf-ai-sync.sh`, `.state_backups/`, and the bucket-path/token-resolution surface are retired.
- Sync failure modes change shape: a same-line conflict now requires one manual `git` resolution instead of silently picking a last-writer-wins winner. This is treated as strictly better (loud and recoverable beats silent and destructive), but it is a genuine workflow change from "sync always just works" to "sync usually rebases cleanly, and rarely asks you to resolve something."
- State is agent-authored either way; git makes tampering and drift *visible* (via `git log -C .claude`), not impossible. This ADR does not claim otherwise.
- The fresh-clone `commit-msg`-gate window ([plan-deterministic-commit-gate.md](plan-deterministic-commit-gate.md) D2) shrinks from "until an authenticated HF pull completes" to "before `post-start.sh`'s checkout" — no separate credential is needed inside the devcontainer, since the state checkout rides on the same git auth as the code checkout.
- Consumers that never re-run `install_bootstrap.py`/`update_consumers.py` keep working on the old HF path until migrated; `state-sync.sh migrate-from-hf` and the updater's automatic migration step are the one-way, explicit on-ramp (no automatic HF pull during migration — the local tree is the source of truth at migration time).

See [plan-git-state-sync.md](plan-git-state-sync.md) for the full phase-by-phase implementation record.
