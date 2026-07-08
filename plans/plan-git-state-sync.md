# Plan — Git-backed AI state sync (`R-SYNC-05`)

**Status:** Proposed
**Date:** 2026-07-08
**Derives from:** [architecture-review-2026-07.md](architecture-review-2026-07.md) §3.4 Fault line 4 (sync configuration and state safety) and the post-implementation observation that the remaining HF-sync complexity (`.state_backups/`, `--prune`, last-writer-wins overwrites, the fresh-clone fail-open window in [plan-deterministic-commit-gate.md](plan-deterministic-commit-gate.md) D2) are all symptoms of keeping mutable, project-scoped, history-shaped state on object storage instead of in git.
**Effort:** L (6 phases, one commit each; Phase 5 is the migration/retirement phase and is the largest)
**Audience note:** written to be implemented by an agent without prior context. Read §1 before touching anything. All design decisions in §3 are settled — do not re-litigate them.

---

## 0. Relationship to `plan-post-review-hardening.md` (read this first)

This plan is **independent of and must not modify** [docs/plan-post-review-hardening.md](plan-post-review-hardening.md) or any of its phases.

- **Do not edit that file.** Its phases (R-HOOKS-08/09, R-CI-01, R-SCORE-03, R-VALID-02, R-DOCS-02, R-MCP-01) stand as written.
- **Suggested ordering:** implement this plan *after* the hardening plan, or at minimum after its Phase 1 (R-HOOKS-08) and Phase 2 (R-CI-01), so the CI workflow protects this plan's validator cases too.
- **Shared surfaces:** both plans touch README's sync/hooks sections, `docs/runtime-checks.md`, `docs/smoke-tests.md`, and `scripts/validate_targets.py`. This plan's doc/validator changes are **additive or replace only HF-sync-specific content**; where a section was rewritten by the hardening plan (e.g. the two-layer commit enforcement docs), extend it, never rewrite it.
- **No functional collision:** the hardening plan touches git hooks, gates, scorer, CI, MCP; this plan touches the *sync layer* (installer, `post-start.sh`, Stop/SessionStart sync hooks, `hf-ai-sync.*`). The only intersection is documentation wording and validator file growth.
- **One beneficial interaction (document, don't depend on):** the D2 "fresh clone fails open until first sync" degradation shrinks under this plan, because `.claude/` (including `hooks/git-hooks/`) arrives via a credentialed-anyway `git` checkout in `post-start.sh` instead of an HF pull that needs separate auth. Phase 5 updates that doc text.

---

## 1. Required context (read in order)

1. [docs/architecture.md](architecture.md) — §"HF State Sync and Pull Safety" describes the machinery this plan replaces: pull-time `.state_backups/` snapshots, identical-file backup deletion, `push-state --prune`, `MEMORY.md` single-homing in the state bundle, `import_hf_api()` fallback.
2. [README.md](../README.md) — "Quick Install", "Updating Existing Repos", the HF bucket/auth sections, and the generated-layout description (what is bootstrap-controlled vs consumer-owned state).
3. [shared/devcontainer/hf-ai-sync.py](../shared/devcontainer/hf-ai-sync.py) — the current sync engine: `BOOTSTRAP_PATHS` vs `STATE_INCLUDES` (which files count as state: `MEMORY.md`, `plans/**`, `explorations/**`, `session_logs/**`, `quality_reports/**`), pull/push/upload-bootstrap subcommands, backup logic.
4. [shared/hooks/scripts/hf-ai-sync.sh](../shared/hooks/scripts/hf-ai-sync.sh) — the Stop-hook wrapper: warn-never-fail semantics, the 2-second stdin drain (both must be preserved in the replacement).
5. [shared/devcontainer/post-start.sh](../shared/devcontainer/post-start.sh) — git-ownership fix → set `core.hooksPath` → HF pull. This plan changes the third step.
6. [scripts/install_bootstrap.py](../scripts/install_bootstrap.py) — copies bootstrap files into the consumer, writes the gitignore block, sets `core.hooksPath`, requires `--bucket`/`HF_AI_SYNC_BUCKET`, uploads the bundle.
7. [scripts/update_consumers.py](../scripts/update_consumers.py) — regenerate + reinstall loop with MEMORY.md backup/restore.
8. [shared/vscode/tasks.json](../shared/vscode/tasks.json) — the folderOpen auto-pull and manual push tasks.
9. [scripts/validate_targets.py](../scripts/validate_targets.py) — the bucket/sync assertions (search for `HF_AI_SYNC` and `bucket`) and the throwaway-repo test harness used as the template for Phase 6.
10. [docs/plan-deterministic-commit-gate.md](plan-deterministic-commit-gate.md) — D2 (why `.claude/` is gitignored + synced, and the accepted fresh-clone degradation this plan improves).

**Vocabulary used below:**

- **Consumer repo** — a project the bootstrap is installed into. Its `.claude/`, root adapters (`CLAUDE.md`, `AGENTS.md`, `.mcp.json`, `.codex/`, and by default the Copilot surface) are gitignored there today and restored from the HF bucket.
- **State** — the files agents mutate across sessions: `MEMORY.md`, `plans/**`, `explorations/**`, `session_logs/**`, `quality_reports/**`. Per-project, history-shaped (they record what was done and what is planned next), and read by the hook gates.
- **Bootstrap-controlled files** — everything the installer/updater owns: agents, skills, instructions, hooks, templates, settings, scripts.

---

## 2. Problem

All AI state in a consumer repo lives in gitignored directories mirrored to a Hugging Face bucket. Object storage gives none of the properties this data actually needs:

1. **Last-writer-wins.** Two machines pushing state means the later push silently destroys the earlier one. The entire `.state_backups/` snapshot-then-reconcile mechanism exists only to soften this, and it is explicitly documented as a non-durable local convenience.
2. **No history.** A plan file has only its current contents. "When did phase 3 complete?" or "what did Tuesday's session change?" is answerable only if the session-log discipline happened to capture it. Yet the *purpose* of session logs and explorations is exactly that history — the design wants versioning and is hand-rolling it.
3. **Monotonic drift.** `push-state` never deletes; reconciliation is the opt-in `--prune`, made opt-in precisely because a blind mirror is dangerous — a symptom of the storage layer lacking merge semantics.
4. **Separate auth and config.** HF token resolution, bucket path resolution, `sync_bucket` API-version guards, and a CLI fallback — an entire dependency surface that exists only because the state isn't where the credentials already are.
5. **Fresh-clone window.** A new clone has no `.claude/` (so no `commit-msg` hook) until an authenticated HF pull completes ([plan-deterministic-commit-gate.md](plan-deterministic-commit-gate.md) D2's accepted degradation).

Git provides all five missing properties natively: rejected non-fast-forward pushes instead of silent overwrites, `git log` as the audit trail, deletion tracked as commits, the same credentials as the code remote, and checkout as the restore mechanism.

## 3. Design decisions (settled)

### D1 — `.claude/` becomes a nested git repository, not a worktree *(decided)*

`.claude/` in each consumer becomes a plain, self-contained git repository (its own `.git/` directory inside `.claude/`), holding **both** the bootstrap-controlled files and the state. The outer consumer repo continues to gitignore `.claude/` entirely, so the nested repo is invisible to the code branches.

**Rejected: `git worktree` of an orphan branch.** A worktree must belong to the same repository as its parent, which makes the privacy variant (D3) impossible and couples the state checkout to the outer repo's worktree bookkeeping (prunable, breaks if the outer `.git` moves, interacts badly with bind-mounted devcontainers). A nested repo has one mental model, identical sync commands, and a URL that can point anywhere.

**Rejected: committing state into the consumer repo's own branches.** Atomic with code commits, but it publishes AI ceremony into shared code history and forces the whole philosophy change; recorded as an alternative in the ADR (Phase 1), not chosen.

Consequence: the HF **bootstrap bundle** and **state bundle** are both subsumed — bootstrap updates become commits on the state repo made by the installer/updater (prefix `bootstrap:`), session state becomes commits made by the Stop hook (prefix `session:`). The commit log cleanly separates the two.

### D2 — Default remote: the consumer's own `origin`, branch `ai-state` *(decided)*

By default the nested repo's remote is **the consumer repo's own `origin` URL**, and it pushes to/pulls from a branch named `ai-state` (`push`/`fetch` refspecs pinned to `refs/heads/ai-state`). One project = one remote = code + state; no new infrastructure, credentials already present.

- The `ai-state` branch shares no ancestry with `dev`/`main` (it is born as the nested repo's initial commit) — collaborators never encounter it unless they fetch it deliberately.
- The outer repo may incidentally fetch `origin/ai-state`; harmless.
- **Known constraint (document, accept):** company branch policies may forbid unexpected branches, and repo admins can read the state. Both are resolved by D3.

### D3 — Privacy variant: `--state-remote <url>` *(decided)*

`install_bootstrap.py` gains `--state-remote <git-url>` (env: `AI_STATE_REMOTE`). When set, the nested repo's remote is that URL (e.g. a personal private repo, one per project or one repo with per-project branches — if per-project branches, the branch name becomes the project name and the refspecs adjust). Everything else is identical because D1 made the mechanism URL-agnostic. Resolution order mirrors the existing pattern: CLI flag, env var, else default to `origin`'s URL.

### D4 — Sync semantics: rebase-with-autostash, fail toward local, never fail the session *(decided)*

One new script, `shared/hooks/scripts/state-sync.sh` (pure bash, no `uv`, no Python), with subcommands:

- `setup` — idempotent: if `.claude/.git` missing → `git init`, add remote per D2/D3, `git fetch origin ai-state` (tolerate absence), check out `ai-state` (create orphan-equivalent initial commit if the branch doesn't exist anywhere yet), write the nested repo's own `.gitignore` (see D5).
- `pull` — `git -C .claude pull --rebase --autostash origin ai-state`. On conflict: `git rebase --abort`, print a loud `WARN` naming the conflicting files and the manual-resolution commands, **exit 0** with local files intact. Local state is never destroyed or half-merged by automation.
- `push` — `git -C .claude add -A && git commit -m "session: <ISO-timestamp>"` (skip commit if nothing staged), then `pull` (as above), then `git push origin ai-state`. On push rejection after a failed rebase: same loud-warn-exit-0 contract.

All subcommands preserve the two behaviors that made `hf-ai-sync.sh` robust: **warn-never-fail** (a sync problem must not fail a Stop hook or block a session) and the **2-second stdin drain** (VS Code task invocation never closes stdin — copy the existing drain block verbatim). Errors also append to `.claude/session_logs/hooks-errors.log`, same as today. Timestamps: generate in bash (`date -u +%Y-%m-%dT%H:%M:%SZ`), same rationale as `session-log.sh`.

**Consequently deleted, not ported:** `.state_backups/` snapshots (git history is the backup), identical-file reconciliation, `push-state --prune` (deletions are commits), the `import_hf_api()` version guard, HF token resolution for state, and the MEMORY.md backup/restore dance in `update_consumers.py` (memory is just a tracked file now; the updater's `bootstrap:` commit doesn't touch it).

### D5 — What the nested repo tracks *(decided)*

Tracked: everything currently in the bootstrap bundle under `.claude/` **plus** all `STATE_INCLUDES` state, **plus** a new `bootstrap-root/` directory holding the root-level adapter files that live *outside* `.claude/` in a consumer (`CLAUDE.md`, `AGENTS.md`, `.mcp.json`, `.codex/**`, `.vscode/mcp.json`, `.vscode/tasks.json`, and the Copilot surface when not committed). The installer writes them both to their real locations and into `bootstrap-root/`; a small `restore-root-adapters.sh` (called by `state-sync.sh setup` and `post-start.sh`) copies `bootstrap-root/` back out to the repo root on fresh machines. This replaces the HF bootstrap bundle's job of restoring root adapters.

The nested repo's own `.gitignore` excludes: `.state_backups/` (until Phase 5 deletes the concept), caches, `settings.local.json`, and any `*.local.*` files.

### D6 — Migration is explicit and one-way per consumer *(decided)*

`state-sync.sh migrate-from-hf` (or an installer step, implementer's choice — keep it one code path): if `.claude/` exists with content but no `.claude/.git`, run `setup`, `git add -A`, initial commit `migrate: import pre-git state`, push. If HF sync settings are present in `.devcontainer/`, print a notice that HF state sync is retired and the bucket contents are now historical. **No automatic HF pull is performed during migration** — the local tree is the source of truth at migration time (if the user wants the bucket's newer copy, they run one final manual `hf-ai-sync.py pull` first; document this in the migration notes). `update_consumers.py` performs migration automatically for each consumer it touches.

---

## 4. Implementation phases

Each phase is one commit; each leaves `uv run python scripts/generate_targets.py --all && uv run python scripts/validate_targets.py` green and `dist/` drift-free.

### Phase 1 — `R-SYNC-05a`: ADR-002

Create `docs/adr-002-git-backed-state-sync.md` (~1 page): the decision (D1–D6 in summary), the problem table from §2, alternatives considered and rejected (HF bucket status quo, worktree, state committed into code branches, file-level sync like Syncthing), consequences (HF bucket's remaining role shrinks to devcontainer model caches; `hf-ai-sync.*` retired in Phase 5), and the D2/D3 trade-off (state visible on the code remote by default; `--state-remote` as the privacy escape). Link it from README and `docs/architecture.md`. If `docs/adr-001-*.md` does not exist yet (it is created by the hardening plan's Phase 6), do **not** create it or renumber — the two ADRs are independent files.

**Acceptance:** ADR exists and is linked from both places; no generated-output change.

### Phase 2 — `R-SYNC-05b`: `state-sync.sh`

Create `shared/hooks/scripts/state-sync.sh` implementing D4 (`setup`, `pull`, `push`, `migrate-from-hf`) and `shared/hooks/scripts/restore-root-adapters.sh` implementing the D5 restore. Follow the house style of the existing hook scripts (`set -euo pipefail`, `SCRIPT_DIR` resolution, sourcing `_lib-frontmatter.sh` only if actually needed — it likely isn't). No changes to any wiring yet; the script must be independently testable by hand.

**Acceptance:** in a scratch directory (not this repo): create a fake consumer with a bare `origin`, run `setup` → nested repo exists on branch `ai-state`; `push` → branch appears on the bare remote; clone the consumer fresh, run `setup && pull` → state files restored; simulate divergence (commit different files from two clones) → second `push` rebases cleanly; simulate a same-line conflict → script warns, aborts the rebase, exits 0, local files intact. Record the exact commands used in the commit message body. Regenerate; the new scripts appear executable under `dist/multi-agent/.claude/hooks/scripts/`.

### Phase 3 — `R-SYNC-05c`: hook and task wiring

- In [scripts/generate_targets.py](../scripts/generate_targets.py) (or the settings templates it renders — find where Stop hooks reference `hf-ai-sync.sh`): Stop hooks call `state-sync.sh push`; SessionStart sync steps call `state-sync.sh pull`. Keep the guardrail hooks' ordering unchanged.
- [shared/vscode/tasks.json](../shared/vscode/tasks.json): folderOpen task → `state-sync.sh pull`; manual push task → `state-sync.sh push`. Rename task labels from "HF bucket" to "AI state".
- Leave `hf-ai-sync.sh`/`.py` present but unwired (deleted in Phase 5), so a half-migrated consumer can still run them manually.

**Acceptance:** `grep -rn "hf-ai-sync" dist/multi-agent/.claude/settings.json dist/multi-agent/.github/hooks/hooks.json dist/multi-agent/.codex/hooks.json dist/multi-agent/.vscode/tasks.json` → no matches; the same grep for `state-sync.sh` → present in all four. Existing validator sync assertions updated in the same commit if they pin the old script name.

### Phase 4 — `R-SYNC-05d`: installer, updater, devcontainer

- [scripts/install_bootstrap.py](../scripts/install_bootstrap.py): after copying files — populate `bootstrap-root/` (D5), run `state-sync.sh setup` in the target, make the `bootstrap: install <version/date>` commit, push (warn-don't-fail on network absence). Add `--state-remote` (D3). **Demote `--bucket`/`HF_AI_SYNC_BUCKET` from required to absent** — remove the requirement and the bundle upload (the state repo carries everything); keep writing nothing HF-related into `.devcontainer/`.
- [scripts/update_consumers.py](../scripts/update_consumers.py): drop the MEMORY.md backup/restore (D4); after reinstalling files, commit as `bootstrap: update <date>` and push. Runs `migrate-from-hf` first when it finds a pre-git `.claude/`.
- [shared/devcontainer/post-start.sh](../shared/devcontainer/post-start.sh): replace the HF pull with `state-sync.sh setup && state-sync.sh pull && restore-root-adapters.sh`, keeping the git-ownership fix first and `core.hooksPath` set immediately after `setup` (the hook files arrive with the checkout, so the fail-open window closes at checkout time — note this for Phase 5's doc update).
- Devcontainer files: remove `hf-ai-sync.py` wiring; the `~/.cache/huggingface` mount and `huggingface_hub` pin **stay** (projects themselves use HF; only the state-sync role is retired — add a one-line comment in the Dockerfile saying the pin is for project use, no longer for state sync).

**Acceptance:** on a throwaway consumer with a bare `origin`: `install_bootstrap.py <repo>` (no bucket flag) succeeds; `git -C <repo>/.claude log --oneline` shows the `bootstrap:` commit; the bare remote has `ai-state`; `core.hooksPath` is set; a fresh clone of the consumer + `post-start.sh` restores `.claude/` and root adapters and an invalid ceremony commit on an `_implementation` branch is rejected by the `commit-msg` hook (proving the window closes at checkout).

### Phase 5 — `R-SYNC-05e`: retirement and documentation

- Delete `shared/devcontainer/hf-ai-sync.py`, `shared/hooks/scripts/hf-ai-sync.sh`, and every reference (generator copy lists, validator assertions, `check_runtime.py` if it mentions them).
- Delete the `.state_backups/` concept: docs, the nested `.gitignore` entry from D5, any remaining code.
- Rewrite the sync-related sections of [README.md](../README.md) (Quick Install, Updating Existing Repos, generated-layout, the `hf://` path examples), [docs/architecture.md](architecture.md) ("HF State Sync and Pull Safety" → "Git-backed state sync"), [docs/runtime-checks.md](runtime-checks.md), [docs/smoke-tests.md](smoke-tests.md), [docs/target-mapping.md](target-mapping.md) (devcontainer bootloader description). Update the D2 degradation text (in README's commit-gate section and `runtime-checks.md`) to the new, smaller window — **extend the two-layer wording added by the hardening plan; do not rewrite it, and do not touch either plan file.**
- Update [AGENTS.md](../AGENTS.md) / `CLAUDE.md` sources if they reference HF sync.

**Acceptance:** `grep -rn "hf-ai-sync\|HF_AI_SYNC\|state_backups\|sync_bucket" shared/ scripts/ docs/ README.md AGENTS.md` → only historical mentions inside `docs/architecture-review-2026-07.md`, `docs/plan-*.md`, `docs/history/`, and the ADR (these are records; leave them). Regenerate + validate green.

### Phase 6 — `R-SYNC-05f`: adversarial validator cases

Add a `validate_state_sync` section to [scripts/validate_targets.py](../scripts/validate_targets.py), using the existing throwaway-repo harness pattern:

1. Install into a temp consumer with a temp bare `origin` → `ai-state` exists on the remote; nested repo checked out.
2. "Machine B": clone the consumer, run `setup && pull` → plans/logs present and byte-identical.
3. Divergence: commit state on A (new session-log file) and on B (different file), push A, then push B → B's push succeeds after auto-rebase; both files present on both sides after a final pull.
4. Conflict: same line of the same plan frontmatter changed on both → B's `push` exits 0, prints `WARN`, leaves B's local file untouched, and the remote still has A's version (nothing lost on either side).
5. Stop-hook contract: run `state-sync.sh push` with stdin held open → returns within the drain timeout (no hang).
6. `--state-remote`: install with a second bare remote → state lands there, not on `origin`.

**Acceptance:** all cases pass on Linux and macOS (via the hardening plan's CI if already landed; locally otherwise); full regenerate + validate green.

---

## 5. What this closes vs. leaves open

**Closes:** silent last-writer-wins state loss (pushes are rejected, rebased, or loudly left local); the backup/prune compensations (deleted, subsumed by git history); the separate HF auth/config surface for state; monotonic bucket drift; the fresh-clone fail-open window shrinks to "before `post-start.sh` checkout" with no separate credential needed; agents gain a queryable history (`git -C .claude log --stat`) of what every session changed.

**Leaves open (by design):** state on the default remote is visible to repo admins (D2; escape: D3 `--state-remote`); a genuine same-line conflict requires one manual resolution (the script never auto-resolves); the state remains agent-authored — versioning makes tampering *visible*, not impossible; consumers that never run `install`/`update_consumers` keep working on the old HF path until migrated (Phase 3 leaves the old scripts present until Phase 5).

## 6. Out of scope

- Any change to the gates, hooks, scorer, plan formats, or file paths — the state moves storage, not location.
- Everything in [plan-post-review-hardening.md](plan-post-review-hardening.md) — implemented separately, before this plan.
- Encrypting state or making it tamper-proof (single-author workflow; visibility is the goal, not cryptographic integrity).
- Retiring the devcontainer's HF cache mount or `huggingface_hub` pin (still used by the projects themselves).

## 7. Overall acceptance

End-to-end on two throwaway "machines" (two clones of a temp consumer with a bare remote): install on A → work a fake session (edit a plan, add a session log) → Stop-hook push → open on B → SessionStart pull shows the state → B edits and pushes → A pulls cleanly → force a conflict → automation warns and preserves both sides → `git -C .claude log` shows `bootstrap:` and `session:` commits in order. `validate_targets.py` green including the Phase 6 suite; `grep` sweep from Phase 5 clean; `docs/plan-post-review-hardening.md` byte-identical to before this plan started (`git diff` proof in the final commit message).

## 8. Sources

**This repo:** [docs/architecture-review-2026-07.md](architecture-review-2026-07.md) §3.4 Fault line 4 and R-SYNC-01..04 (the HF-layer fixes this plan supersedes); [docs/architecture.md](architecture.md) "HF State Sync and Pull Safety"; [docs/plan-deterministic-commit-gate.md](plan-deterministic-commit-gate.md) D2 (fresh-clone degradation); [shared/devcontainer/hf-ai-sync.py](../shared/devcontainer/hf-ai-sync.py) (`STATE_INCLUDES` — the authoritative list of what counts as state); [shared/hooks/scripts/hf-ai-sync.sh](../shared/hooks/scripts/hf-ai-sync.sh) (warn-never-fail + stdin-drain contracts to preserve).

**External:**

- https://git-scm.com/docs/git-worktree — evaluated and rejected in D1 (worktrees are same-repository-only, incompatible with the D3 privacy variant).
- https://git-scm.com/docs/git-checkout (`--orphan`) and the `gh-pages` convention — precedent for an unrelated-history branch coexisting in one remote (D2).
- https://git-scm.com/docs/git-pull (`--rebase --autostash`) — the D4 sync primitive.
- https://github.com/pedrohcgs/claude-code-my-workflow — precedent for splitting committed/shared memory from gitignored personal memory, and for version-controlled workflow state generally.
- https://github.com/Mathews-Tom/armory — precedent for a git-tracked, hook-refreshed session handoff file (`.docs/handoff.md` refreshed on Stop) — the same "state history in git" instinct this plan generalizes.
