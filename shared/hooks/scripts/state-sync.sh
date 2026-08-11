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
# Subcommands: setup | pull | checkpoint | publish | push | status |
# migrate-from-hf
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
PROTECTED_REBASE_STATE=2

prepare_error_log() {
  mkdir -p "$(dirname "$ERROR_LOG")" 2>/dev/null || true
}

warn() {
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%S.000Z 2>/dev/null || echo unknown-timestamp)"
  local msg="$ts state-sync: $*"
  printf 'WARN %s\n' "$msg" >&2
  prepare_error_log
  printf '%s\n' "$msg" >> "$ERROR_LOG" 2>/dev/null || true
}

info() {
  printf 'state-sync: %s\n' "$*" >&2
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

# Commits whatever is currently uncommitted under .claude/ as a session
# snapshot. Reconciliation calls this immediately before `git pull --rebase`
# so the working tree is clean when the rebase starts.
commit_local_state() {
  local message="${1:-}"
  if ! git -C "$CLAUDE_DIR" add -A; then
    return 1
  fi
  if ! git -C "$CLAUDE_DIR" diff --cached --quiet \
    || [[ -z "$(git -C "$CLAUDE_DIR" log -1 --format=%H 2>/dev/null || true)" ]]; then
    local ts
    ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown-timestamp)"
    if ! git -C "$CLAUDE_DIR" commit -q --allow-empty -m "${message:-session: $ts}"; then
      return 1
    fi
  fi
}

# Older nested repositories retain Git's default wildcard fetch refspec even
# though init_nested_repo now pins state sync to one branch. Re-pin it on every
# reconciliation so drift is repaired without requiring a reinstall.
# ASSUMPTION: wildcard refspecs caused historical "Cannot rebase onto multiple
# branches" failures; this needs empirical verification.
ensure_pinned_refspecs() {
  if ! git -C "$CLAUDE_DIR" config --replace-all "remote.origin.fetch" "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"; then
    return 1
  fi
  if ! git -C "$CLAUDE_DIR" config --replace-all "remote.origin.push" "refs/heads/$BRANCH:refs/heads/$BRANCH"; then
    return 1
  fi
}

append_error_output() {
  [[ -n "$1" ]] || return 0
  prepare_error_log
  printf '%s\n' "$1" >> "$ERROR_LOG" 2>/dev/null || true
}

nested_rebase_in_progress() {
  [[ -d "$CLAUDE_DIR/.git/rebase-merge" || -d "$CLAUDE_DIR/.git/rebase-apply" ]]
}

orphaned_preexisting_autostash() {
  local rebase_dir="$CLAUDE_DIR/.git/rebase-merge" entry entries=0
  [[ -d "$rebase_dir" && ! -d "$CLAUDE_DIR/.git/rebase-apply" ]] || return 1
  for entry in "$rebase_dir"/* "$rebase_dir"/.[!.]* "$rebase_dir"/..?*; do
    [[ -e "$entry" || -L "$entry" ]] || continue
    ((entries += 1))
    [[ "$entry" == "$rebase_dir/autostash" && -f "$entry" && ! -L "$entry" ]] || return 1
  done
  [[ $entries -eq 1 ]]
}

preflight_mutating_rebase_state() {
  if ! nested_rebase_in_progress; then
    return 0
  fi
  if ! orphaned_preexisting_autostash; then
    printf 'WARN state-sync: pre-existing rebase state is ambiguous; state sync will not alter it. Inspect with: git -C %s status. Resolve with: git -C %s rebase --continue, or quit with: git -C %s rebase --quit\n' "$CLAUDE_DIR" "$CLAUDE_DIR" "$CLAUDE_DIR" >&2
    return "$PROTECTED_REBASE_STATE"
  fi

  local quit_output quit_status
  warn "orphaned autostash rebase state from a previous sync detected; clearing it with rebase --quit before continuing."
  set +e
  quit_output="$(git -C "$CLAUDE_DIR" rebase --quit 2>&1)"
  quit_status=$?
  set -e
  append_error_output "$quit_output"
  if [[ $quit_status -ne 0 ]]; then
    warn "orphaned autostash rebase state from a previous sync could not be cleared. Resolve manually: git -C $CLAUDE_DIR rebase --quit"
    return 1
  fi
}

dispatch_mutating() {
  local preflight_status command_status
  set +e
  preflight_mutating_rebase_state
  preflight_status=$?
  set -e
  if [[ $preflight_status -eq $PROTECTED_REBASE_STATE ]]; then
    return 0
  fi
  if [[ $preflight_status -ne 0 ]]; then
    return "$preflight_status"
  fi
  set +e
  "$@"
  command_status=$?
  set -e
  if [[ $command_status -eq $PROTECTED_REBASE_STATE ]]; then
    return 0
  fi
  return "$command_status"
}

clear_current_pull_rebase_state() {
  local abort_output abort_status quit_output quit_status
  set +e
  abort_output="$(git -C "$CLAUDE_DIR" rebase --abort 2>&1)"
  abort_status=$?
  if [[ $abort_status -eq 0 ]]; then
    set -e
    append_error_output "$abort_output"
    return 0
  fi

  quit_output="$(git -C "$CLAUDE_DIR" rebase --quit 2>&1)"
  quit_status=$?
  set -e
  append_error_output "$abort_output"
  append_error_output "$quit_output"
  return "$quit_status"
}

restore_root_adapters() {
  local restore="$SCRIPT_DIR/restore-root-adapters.sh"
  if [[ -f "$restore" ]]; then
    bash "$restore" || warn "restoring root adapters failed; continuing."
  fi
}

# Idempotent: safe to call at the top of pull/push so every entry point works
# standalone, not just after an explicit `setup` call.
cmd_setup() {
  if [[ -d "$CLAUDE_DIR/.git" ]]; then
    return 0
  fi
  init_nested_repo
  if ! commit_local_state "bootstrap: init ai-state"; then
    return 1
  fi
  local reconcile_status
  set +e
  reconcile_committed_state
  reconcile_status=$?
  set -e
  if [[ $reconcile_status -eq $PROTECTED_REBASE_STATE ]]; then
    return "$reconcile_status"
  fi

  # D5 / F1 (§9): once .claude/ is first materialised here, restore the
  # root-level adapter files that live outside .claude/ (carried in
  # bootstrap-root/). This makes every entry point that first creates .claude/
  # restore them — a non-devcontainer `setup`, or a `pull`/`push` that reaches
  # setup — not just the devcontainer post-start.sh. Idempotent: it copies
  # bytes already committed under bootstrap-root/. post-start.sh keeps its own
  # explicit restore call for the case where a later `pull` brings a newer one.
  restore_root_adapters
  commit_local_state
}

# A checkpoint deliberately initializes only local Git state. Unlike setup,
# it never fetches or merges an existing remote branch.
cmd_checkpoint() {
  if [[ ! -d "$CLAUDE_DIR/.git" ]]; then
    init_nested_repo
    restore_root_adapters
  fi
  commit_local_state
}

reconcile_committed_state() {
  if is_local_only || ! git -C "$CLAUDE_DIR" remote get-url origin >/dev/null 2>&1; then
    return 0
  fi

  if ! ensure_pinned_refspecs; then
    warn "configuring pinned origin refspecs failed; local commits are intact and will retry on the next sync."
    return 1
  fi

  local remote_ref_status output status conflicts preflight_status
  set +e
  git -C "$CLAUDE_DIR" ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1
  remote_ref_status=$?
  set -e
  if [[ $remote_ref_status -eq 2 ]]; then
    return 0
  fi
  if [[ $remote_ref_status -ne 0 ]] || ! git -C "$CLAUDE_DIR" fetch origin -q 2>/dev/null; then
    warn "fetch from origin/$BRANCH failed; local commits are intact and will retry on the next sync."
    return 1
  fi

  if ! git -C "$CLAUDE_DIR" merge-base HEAD "origin/$BRANCH" >/dev/null 2>&1; then
    set +e
    output="$(git -C "$CLAUDE_DIR" merge -q --allow-unrelated-histories -m "bootstrap: merge existing ai-state" "origin/$BRANCH" 2>&1)"
    status=$?
    set -e
    if [[ $status -ne 0 ]]; then
      conflicts="$(git -C "$CLAUDE_DIR" diff --name-only --diff-filter=U 2>/dev/null || true)"
      git -C "$CLAUDE_DIR" merge --abort 2>/dev/null || true
      append_error_output "$output"
      warn "local .claude/ content conflicts with origin/$BRANCH and could not be merged automatically. Conflicting file(s): ${conflicts:-see $ERROR_LOG}. Resolve manually: cd $CLAUDE_DIR && git merge --allow-unrelated-histories origin/$BRANCH, fix conflicts, commit, then git push origin $BRANCH."
      return 1
    fi
    return 0
  fi

  # Re-check immediately before staging: an operator rebase can begin after
  # the entrypoint guard, while hook logging can dirty the tree before pull.
  set +e
  preflight_mutating_rebase_state
  preflight_status=$?
  set -e
  if [[ $preflight_status -ne 0 ]]; then
    return "$preflight_status"
  fi
  if ! commit_local_state; then
    warn "local state checkpoint failed; reconciliation will retry on the next sync."
    return 1
  fi

  set +e
  # Git's autostash mode writes rebase metadata before discovering renewed log
  # churn; without it, this residual race fails cleanly and retries next sync.
  output="$(git -C "$CLAUDE_DIR" pull --rebase origin "$BRANCH" 2>&1)"
  status=$?
  set -e
  if [[ $status -ne 0 ]]; then
    conflicts="$(git -C "$CLAUDE_DIR" diff --name-only --diff-filter=U 2>/dev/null || true)"
    append_error_output "$output"
    if nested_rebase_in_progress; then
      if ! clear_current_pull_rebase_state; then
        warn "leftover rebase state from a failed reconciliation could not be cleared. Resolve manually: git -C $CLAUDE_DIR rebase --quit"
      fi
    fi
    warn "reconciliation with origin/$BRANCH failed; local state left untouched. Conflicting file(s): ${conflicts:-see output below}. Resolve manually: cd $CLAUDE_DIR && git pull --rebase origin $BRANCH, fix conflicts, git add <files>, git rebase --continue, then git push origin $BRANCH."
    printf '%s\n' "$output" >&2
    return 1
  fi
}

cmd_publish() {
  if [[ ! -d "$CLAUDE_DIR/.git" ]]; then
    warn "publish skipped: no local ai-state repository exists yet; run checkpoint first."
    return 1
  fi
  if is_local_only; then
    info "publish: local-only mode; remote sync skipped."
    return 0
  fi
  if [[ -n "$(git -C "$CLAUDE_DIR" status --porcelain)" ]]; then
    warn "publish skipped: local ai-state worktree is dirty; run checkpoint before publishing."
    return 1
  fi
  if ! git -C "$CLAUDE_DIR" remote get-url origin >/dev/null 2>&1; then
    warn "no state remote configured; local checkpoint remains unpublished."
    return 0
  fi
  local reconcile_status
  set +e
  reconcile_committed_state
  reconcile_status=$?
  set -e
  if [[ $reconcile_status -eq $PROTECTED_REBASE_STATE ]]; then
    return "$reconcile_status"
  fi
  if [[ $reconcile_status -ne 0 ]]; then
    warn "publish skipped: reconciliation with origin/$BRANCH failed. Local commits are safe and will retry once the conflict is resolved."
    return 1
  fi

  local output status
  set +e
  output="$(git -C "$CLAUDE_DIR" push origin "$BRANCH" 2>&1)"
  status=$?
  set -e
  if [[ $status -ne 0 ]]; then
    append_error_output "$output"
    warn "push to origin/$BRANCH failed; local commits are intact and will retry on the next sync."
    printf '%s\n' "$output" >&2
  fi
}

cmd_pull() {
  local setup_status reconcile_status
  set +e
  cmd_setup
  setup_status=$?
  set -e
  if [[ $setup_status -ne 0 ]]; then
    return "$setup_status"
  fi
  if is_local_only; then
    info "pull: local-only mode; bootstrap complete, remote sync skipped."
    return 0
  fi
  if ! git -C "$CLAUDE_DIR" remote get-url origin >/dev/null 2>&1; then
    warn "no state remote configured; nothing to pull from."
    return 0
  fi
  set +e
  reconcile_committed_state
  reconcile_status=$?
  set -e
  if [[ $reconcile_status -ne 0 ]]; then
    return "$reconcile_status"
  fi
  info "pull: up to date with origin/$BRANCH"
}

cmd_push() {
  if ! cmd_checkpoint; then
    warn "push skipped: checkpoint failed; publication was not attempted."
    return 1
  fi
  cmd_publish
}

cmd_status() {
  if [[ ! -d "$CLAUDE_DIR/.git" ]]; then
    printf 'repository: uninitialized\nworktree: uninitialized\nremote: unavailable\ntracking: unavailable\nrebase: none\n'
  else
    local worktree remote tracking ahead behind rebase
    if [[ -n "$(git -C "$CLAUDE_DIR" status --porcelain)" ]]; then
      worktree="dirty"
    else
      worktree="clean"
    fi
    if git -C "$CLAUDE_DIR" remote get-url origin >/dev/null 2>&1; then
      remote="configured"
    else
      remote="not-configured"
    fi
    tracking="unavailable"
    if git -C "$CLAUDE_DIR" rev-parse --verify -q HEAD >/dev/null 2>&1 \
      && git -C "$CLAUDE_DIR" rev-parse --verify -q "origin/$BRANCH" >/dev/null 2>&1; then
      read -r ahead behind < <(git -C "$CLAUDE_DIR" rev-list --left-right --count "HEAD...origin/$BRANCH")
      tracking="ahead=$ahead behind=$behind"
    fi
    rebase="none"
    if nested_rebase_in_progress; then
      rebase="in-progress"
    fi
    printf 'repository: initialized\nworktree: %s\nremote: %s\ntracking: %s\nrebase: %s\n' "$worktree" "$remote" "$tracking" "$rebase"
  fi
  printf 'error-log: %s\n' "$ERROR_LOG"
  if [[ -f "$ERROR_LOG" ]]; then
    local last_error
    last_error="$(grep 'state-sync:' "$ERROR_LOG" 2>/dev/null | tail -n 1 || true)"
    printf 'last-error: %s\n' "${last_error:-none}"
  else
    printf 'last-error: none\n'
  fi
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
  if ! commit_local_state "migrate: import pre-git state"; then
    return 1
  fi
  local reconcile_status
  set +e
  reconcile_committed_state
  reconcile_status=$?
  set -e
  if [[ $reconcile_status -eq $PROTECTED_REBASE_STATE ]]; then
    return "$reconcile_status"
  fi
  if [[ $reconcile_status -ne 0 ]]; then
    warn "migration state committed locally but reconciliation with origin/$BRANCH failed; not pushing. Resolve the reported issue, then: git -C $CLAUDE_DIR push origin $BRANCH."
  elif ! is_local_only && git -C "$CLAUDE_DIR" remote get-url origin >/dev/null 2>&1; then
    local output status
    set +e
    output="$(git -C "$CLAUDE_DIR" push origin "$BRANCH" 2>&1)"
    status=$?
    set -e
    if [[ $status -ne 0 ]]; then
      append_error_output "$output"
      warn "migration commit created locally but push to origin/$BRANCH failed; push manually once network/auth is available: git -C $CLAUDE_DIR push origin $BRANCH"
    fi
  fi

  if [[ -f "$REPO_ROOT/.devcontainer/devcontainer.json" ]] \
    && grep -q "HF_AI_SYNC" "$REPO_ROOT/.devcontainer/devcontainer.json" 2>/dev/null; then
    info "NOTICE: Hugging Face state sync is retired. .devcontainer/devcontainer.json still references HF_AI_SYNC_* settings; the bucket's contents are now historical only, and AI state lives on the ai-state branch from here on."
  fi
}

case "$MODE" in
  setup) dispatch_mutating cmd_setup || warn "setup failed; continuing." ;;
  pull) dispatch_mutating cmd_pull || warn "pull failed; continuing." ;;
  checkpoint) dispatch_mutating cmd_checkpoint || warn "checkpoint failed; continuing." ;;
  publish) dispatch_mutating cmd_publish || warn "publish failed; continuing." ;;
  push) dispatch_mutating cmd_push || warn "push failed; continuing." ;;
  status) cmd_status ;;
  migrate-from-hf) dispatch_mutating cmd_migrate || warn "migrate-from-hf failed; continuing." ;;
  *) warn "unknown mode: $MODE (expected setup|pull|checkpoint|publish|push|status|migrate-from-hf)" ;;
esac

exit 0
