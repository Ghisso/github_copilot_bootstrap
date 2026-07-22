#!/usr/bin/env bash
set -euo pipefail

# Git-backed AI state sync (R-SYNC-05 / D4 in plans/plan-git-state-sync.md).
# .claude/ is a plain, self-contained git repository (its own .git/ inside
# .claude/), tracking both bootstrap-controlled files and mutable AI state on
# one branch (BRANCH below). It replaces hf-ai-sync.py/hf-ai-sync.sh.
#
# This file is installed in TWO locations by generate_targets.py:
#   - .claude/hooks/scripts/state-sync.sh (the normal, post-checkout copy)
#   - .devcontainer/state-sync.sh (a bootstrap copy reachable BEFORE .claude/
#     exists at all, since .claude/ is gitignored in the outer repo — a fresh
#     clone has no .claude/ until this script's own `setup` creates it; see
#     REPO_ROOT resolution below, which is why it cannot use a single fixed
#     "../../.." relative path the way the other hook scripts do)
#
# Subcommands: setup | pull | push | migrate-from-hf
# `pull`/`push` accept a second positional arg `--local-only` (or set
# AI_STATE_LOCAL_ONLY=1) to skip all origin interaction and commit to the
# nested repo locally only. AI_STATE_REPO_ROOT overrides REPO_ROOT resolution
# for callers that already know the repo root.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -n "${AI_STATE_REPO_ROOT:-}" ]]; then
  REPO_ROOT="$(cd "$AI_STATE_REPO_ROOT" && pwd 2>/dev/null || true)"
  if [[ -z "$REPO_ROOT" ]]; then
    printf 'WARN state-sync: AI_STATE_REPO_ROOT=%s is not a usable directory; falling back to script-relative resolution.\n' "$AI_STATE_REPO_ROOT" >&2
  fi
fi
if [[ -z "${REPO_ROOT:-}" ]]; then
  case "$SCRIPT_DIR" in
    */.claude/hooks/scripts)
      REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
      ;;
    */.devcontainer)
      REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
      ;;
    *)
      REPO_ROOT="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel 2>/dev/null || true)"
      [[ -n "$REPO_ROOT" ]] || REPO_ROOT="$SCRIPT_DIR"
      ;;
  esac
fi

CLAUDE_DIR="$REPO_ROOT/.claude"
BRANCH="${AI_STATE_BRANCH:-ai-state}"
ERROR_LOG="$REPO_ROOT/.claude/session_logs/hooks-errors.log"
mkdir -p "$(dirname "$ERROR_LOG")" 2>/dev/null || true

warn() {
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%S.000Z 2>/dev/null || echo unknown-timestamp)"
  local msg="$ts state-sync: $*"
  printf 'WARN %s\n' "$msg" >&2
  mkdir -p "$(dirname "$ERROR_LOG")" 2>/dev/null || true
  printf '%s\n' "$msg" >> "$ERROR_LOG" 2>/dev/null || true
}

info() {
  printf 'state-sync: %s\n' "$*"
}

# Drain hook JSON from stdin, verbatim contract from hf-ai-sync.sh: a Stop
# hook or VS Code task invocation never closes stdin, so this must not block.
timeout 2 cat >/dev/null 2>/dev/null || true

MODE="${1:-push}"
LOCAL_ONLY="${AI_STATE_LOCAL_ONLY:-0}"
if [[ "${2:-}" == "--local-only" ]]; then
  LOCAL_ONLY=1
fi

is_local_only() {
  [[ "$LOCAL_ONLY" == "1" ]]
}

resolve_remote() {
  if [[ -n "${AI_STATE_REMOTE:-}" ]]; then
    printf '%s' "$AI_STATE_REMOTE"
    return 0
  fi
  git -C "$REPO_ROOT" config --get remote.origin.url 2>/dev/null || true
}

write_nested_gitignore() {
  cat > "$CLAUDE_DIR/.gitignore" <<'EOF'
# Local convenience only; never synced (D5 in plans/plan-git-state-sync.md).
settings.local.json
*.local.*
__pycache__/
*.pyc
# Retired hf-ai-sync.py pull-time snapshots (R-SYNC-05e). Nothing on the
# state-sync.sh path creates this directory anymore, but a consumer
# migrating from a pre-git-backed-state install may still have one on disk;
# never let migrate-from-hf commit it into ai-state history.
.state_backups/
EOF
}

# Multi-writer conflict policy (big plan: state-sync-durability). Append-only
# machine logs auto-reconcile via git's built-in `union` merge driver, so two
# sessions writing separate lines never conflict during rebase. Narrative
# state (plans/**, MEMORY.md, session-log prose) is intentionally left on the
# default conflict-and-abort path so genuine divergences get a manual semantic
# merge instead of a silent ours/theirs.
write_nested_gitattributes() {
  cat > "$CLAUDE_DIR/.gitattributes" <<'EOF'
# See write_nested_gitattributes in state-sync.sh for the policy rationale.
session_logs/*.log merge=union
EOF
}

# Creates the nested repo shell (git init, branch name, gitignore, remote
# config) if .claude/.git is missing. Never commits anything itself, so the
# caller controls the message on the first real commit (cmd_setup says
# "bootstrap: init ai-state"; cmd_migrate says "migrate: import pre-git
# state" — same mechanism, different meaning).
init_nested_repo() {
  if [[ -d "$CLAUDE_DIR/.git" ]]; then
    return 0
  fi
  mkdir -p "$CLAUDE_DIR"
  git init -q "$CLAUDE_DIR"
  # Name the branch before the first commit exists (works on any git version,
  # regardless of init.defaultBranch) rather than relying on `git init -b`.
  git -C "$CLAUDE_DIR" symbolic-ref HEAD "refs/heads/$BRANCH"
  write_nested_gitignore
  write_nested_gitattributes

  local remote
  remote="$(resolve_remote)"
  if [[ -n "$remote" ]]; then
    git -C "$CLAUDE_DIR" remote add origin "$remote" 2>/dev/null \
      || git -C "$CLAUDE_DIR" remote set-url origin "$remote"
    # Pin push/fetch refspecs to this one branch (D2) so a bare `push`/`pull`
    # with no arguments can never touch any other ref on the remote.
    git -C "$CLAUDE_DIR" config "remote.origin.fetch" "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
    git -C "$CLAUDE_DIR" config "remote.origin.push" "refs/heads/$BRANCH:refs/heads/$BRANCH"
  else
    warn "no state remote configured (set AI_STATE_REMOTE, pass --state-remote at install time, or ensure this repo has an 'origin'); state will stay local-only until one is configured."
  fi
}

# Commits whatever is currently on disk under the given message (there is
# always at least .gitignore the first time this runs), then reconciles with
# origin/$BRANCH if a remote is configured and already has that branch. Used
# by both cmd_setup and cmd_migrate so they share one mechanism and differ
# only in the commit message.
commit_and_reconcile() {
  local message="$1"
  git -C "$CLAUDE_DIR" add -A
  if ! git -C "$CLAUDE_DIR" diff --cached --quiet \
    || [[ -z "$(git -C "$CLAUDE_DIR" log -1 --format=%H 2>/dev/null || true)" ]]; then
    git -C "$CLAUDE_DIR" commit -q --allow-empty -m "$message"
  fi

  if is_local_only || ! git -C "$CLAUDE_DIR" remote get-url origin >/dev/null 2>&1; then
    return 0
  fi
  if git -C "$CLAUDE_DIR" fetch origin -q 2>/dev/null \
    && git -C "$CLAUDE_DIR" rev-parse --verify -q "origin/$BRANCH" >/dev/null 2>&1; then
    # A real merge (not a bare checkout) so the freshly-committed local
    # content and the remote's independent history combine file-by-file;
    # --allow-unrelated-histories is required the first time any two
    # machines' ai-state branches meet, since neither was cloned from the
    # other. Genuinely conflicting files abort cleanly, same contract as
    # cmd_pull's rebase-conflict handling below.
    if ! git -C "$CLAUDE_DIR" merge -q --allow-unrelated-histories -m "bootstrap: merge existing ai-state" "origin/$BRANCH" 2>>"$ERROR_LOG"; then
      local conflicts
      conflicts="$(git -C "$CLAUDE_DIR" diff --name-only --diff-filter=U 2>/dev/null || true)"
      git -C "$CLAUDE_DIR" merge --abort 2>/dev/null || true
      warn "local .claude/ content conflicts with origin/$BRANCH and could not be merged automatically. Conflicting file(s): ${conflicts:-see $ERROR_LOG}. Resolve manually: cd $CLAUDE_DIR && git merge --allow-unrelated-histories origin/$BRANCH, fix conflicts, commit, then git push origin $BRANCH."
    fi
  fi
}

# Commits whatever is currently uncommitted under .claude/ as a session
# snapshot. Both cmd_push and cmd_pull call this before touching the remote so
# the working tree is clean before `git pull --rebase`: a clean tree means the
# only reachable pull failure is a rebase conflict (which we abort cleanly),
# never an --autostash pop conflict that would leave the tree half-merged
# (F4 in §9 of plans/plan-git-state-sync.md).
commit_local_state() {
  git -C "$CLAUDE_DIR" add -A
  if ! git -C "$CLAUDE_DIR" diff --cached --quiet; then
    local ts
    ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown-timestamp)"
    git -C "$CLAUDE_DIR" commit -q -m "session: $ts"
  fi
}

# Idempotent: safe to call at the top of pull/push so every entry point works
# standalone, not just after an explicit `setup` call.
cmd_setup() {
  if [[ -d "$CLAUDE_DIR/.git" ]]; then
    return 0
  fi
  init_nested_repo
  commit_and_reconcile "bootstrap: init ai-state"

  # D5 / F1 (§9): once .claude/ is first materialised here, restore the
  # root-level adapter files that live outside .claude/ (carried in
  # bootstrap-root/). This makes every entry point that first creates .claude/
  # restore them — a non-devcontainer `setup`, or a `pull`/`push` that reaches
  # setup — not just the devcontainer post-start.sh. Idempotent: it copies
  # bytes already committed under bootstrap-root/. post-start.sh keeps its own
  # explicit restore call for the case where a later `pull` brings a newer one.
  local restore="$SCRIPT_DIR/restore-root-adapters.sh"
  if [[ -f "$restore" ]]; then
    bash "$restore" || warn "restoring root adapters failed; continuing."
  fi
}

cmd_pull() {
  cmd_setup
  if is_local_only; then
    info "pull: local-only mode; bootstrap complete, remote sync skipped."
    return 0
  fi
  if ! git -C "$CLAUDE_DIR" remote get-url origin >/dev/null 2>&1; then
    warn "no state remote configured; nothing to pull from."
    return 0
  fi
  if ! git -C "$CLAUDE_DIR" ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
    info "pull: origin has no $BRANCH branch yet; nothing to pull."
    return 0
  fi

  # Commit any local edits first so the rebase below runs against a clean tree
  # (F4): removes the --autostash-pop-conflict path entirely.
  commit_local_state

  local output status
  set +e
  output="$(git -C "$CLAUDE_DIR" pull --rebase --autostash origin "$BRANCH" 2>&1)"
  status=$?
  set -e

  if [[ $status -ne 0 ]]; then
    local conflicts
    conflicts="$(git -C "$CLAUDE_DIR" diff --name-only --diff-filter=U 2>/dev/null || true)"
    git -C "$CLAUDE_DIR" rebase --abort 2>/dev/null || true
    warn "pull --rebase failed; local state left untouched. Conflicting file(s): ${conflicts:-see output below}. Resolve manually: cd $CLAUDE_DIR && git pull --rebase origin $BRANCH, fix conflicts, git add <files>, git rebase --continue, then git push origin $BRANCH."
    printf '%s\n' "$output" >&2
    # Report the failed reconciliation to callers (cmd_push guards its push on
    # this). Top-level dispatch converts it into a non-blocking warning, so a
    # Stop/SessionStart hook still exits 0 and never blocks Codex shutdown.
    return 1
  fi
  info "pull: up to date with origin/$BRANCH"
}

cmd_push() {
  cmd_setup

  commit_local_state

  if is_local_only; then
    info "push: local-only mode; committed locally without contacting origin."
    return 0
  fi

  if ! git -C "$CLAUDE_DIR" remote get-url origin >/dev/null 2>&1; then
    warn "no state remote configured; committed locally only."
    return 0
  fi

  # Reconcile first. If the pull failed (a rebase conflict aborted cleanly),
  # the local commits are safe but a push would be a doomed non-fast-forward;
  # skip it and require manual reconciliation rather than attempting a push
  # that git will reject.
  if ! cmd_pull; then
    warn "push skipped: reconciliation with origin/$BRANCH failed. Local commits are safe and will retry on the next sync once the conflict is resolved (see the pull warning above for recovery steps)."
    return 1
  fi

  local output status
  set +e
  output="$(git -C "$CLAUDE_DIR" push origin "$BRANCH" 2>&1)"
  status=$?
  set -e
  if [[ $status -ne 0 ]]; then
    warn "push to origin/$BRANCH failed; local commits are intact and will retry on the next sync."
    printf '%s\n' "$output" >&2
    return 0
  fi
  info "push: origin/$BRANCH updated"
}

cmd_migrate() {
  if [[ -d "$CLAUDE_DIR/.git" ]]; then
    info "$CLAUDE_DIR is already git-backed; nothing to migrate."
    return 0
  fi
  if [[ ! -d "$CLAUDE_DIR" ]] || [[ -z "$(ls -A "$CLAUDE_DIR" 2>/dev/null || true)" ]]; then
    info "no pre-existing $CLAUDE_DIR content to migrate; run setup instead."
    return 0
  fi

  # No automatic HF pull here on purpose (D6): the local tree is the source
  # of truth at migration time. If a bucket has newer state, pull it manually
  # with the old hf-ai-sync.py before running this, one last time.
  init_nested_repo
  commit_and_reconcile "migrate: import pre-git state"

  if ! is_local_only && git -C "$CLAUDE_DIR" remote get-url origin >/dev/null 2>&1; then
    if ! git -C "$CLAUDE_DIR" push origin "$BRANCH" 2>>"$ERROR_LOG"; then
      warn "migration commit created locally but push to origin/$BRANCH failed; push manually once network/auth is available: git -C $CLAUDE_DIR push origin $BRANCH"
    fi
  fi

  if [[ -f "$REPO_ROOT/.devcontainer/devcontainer.json" ]] \
    && grep -q "HF_AI_SYNC" "$REPO_ROOT/.devcontainer/devcontainer.json" 2>/dev/null; then
    info "NOTICE: Hugging Face state sync is retired. .devcontainer/devcontainer.json still references HF_AI_SYNC_* settings; the bucket's contents are now historical only, and AI state lives on the ai-state branch from here on."
  fi
}

case "$MODE" in
  setup) cmd_setup || warn "setup failed; continuing." ;;
  pull) cmd_pull || warn "pull failed; continuing." ;;
  push) cmd_push || warn "push failed; continuing." ;;
  migrate-from-hf) cmd_migrate || warn "migrate-from-hf failed; continuing." ;;
  *) warn "unknown mode: $MODE (expected setup|pull|push|migrate-from-hf)" ;;
esac

exit 0
