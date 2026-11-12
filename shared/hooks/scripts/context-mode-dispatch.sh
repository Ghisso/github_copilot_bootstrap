#!/usr/bin/env bash
set -euo pipefail

warn() {
  printf 'WARN context-mode-dispatch: %s\n' "$*" >&2
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
DEFAULT_CONTEXT_MODE_DIR="$REPO_ROOT/.claude/.cache/context-mode"
PINNED_CONTEXT_MODE_VERSION="2.1.8"
# Context Mode 2.x needs Node.js 24.15.0 or newer. Checked in server mode and
# --self-check only: legacy hook calls start nothing.
MIN_NODE_VERSION="24.15.0"
FILTER_CONTRACT="ctx-index-files-only-v2"
FILTER_SCRIPT="$SCRIPT_DIR/context-mode-mcp-filter.mjs"
# Outside the ai-state working tree (.claude/) on purpose: state-sync.sh adds
# and commits only under .claude/, so this file never enters ai-state history,
# and the root restore it runs copies only allowlisted adapter files, never this
# one. This gives no protection against a remote that replaces the synced
# scripts themselves. See configure_storage below.
PROVENANCE_SECRET_FILE="$REPO_ROOT/.context-mode-provenance.secret"

# Prints the installed package version of a direct `context-mode` executable.
#
# The server cannot prove its own version: Context Mode 2.x reports
# `serverInfo.version` "dev" over the wire. Running `context-mode --version`
# would prove it, but it starts a full Node.js process on every check. The
# executable is an npm bin symlink into the installed package directory, so
# resolve it and read the owning package.json instead: offline, no Node.js
# start, and independent of the bundle's internals. The name is checked too, so
# a nested dependency manifest can never be mistaken for Context Mode's own.
direct_context_mode_version() {
  local exe="$1" resolved dir manifest
  resolved="$(readlink -f "$exe" 2>/dev/null)" || return 1
  [[ -n "$resolved" && -f "$resolved" ]] || return 1
  dir="$(dirname "$resolved")"
  while :; do
    manifest="$dir/package.json"
    if [[ -f "$manifest" ]] \
      && grep -Eq '"name"[[:space:]]*:[[:space:]]*"context-mode"' "$manifest"; then
      sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$manifest" | head -1
      return 0
    fi
    [[ "$dir" == "/" || -z "$dir" ]] && return 1
    dir="$(dirname "$dir")"
  done
}

# A direct binary is used only when it is provably the pinned version. The `npx`
# fallback needs no such check because its version is pinned in the command
# itself, so it is correct by construction.
resolve_context_mode() {
  local exe version
  if exe="$(command -v context-mode 2>/dev/null)" && [[ -n "$exe" ]]; then
    if version="$(direct_context_mode_version "$exe")" \
      && [[ "$version" == "$PINNED_CONTEXT_MODE_VERSION" ]]; then
      printf 'context-mode'
      return 0
    fi
    warn "ignoring context-mode on PATH at $exe: requires exactly $PINNED_CONTEXT_MODE_VERSION, found ${version:-undeterminable}"
  fi
  if command -v npx >/dev/null 2>&1; then
    printf 'npx'
    return 0
  fi
  return 1
}

# Succeeds when "$1" (the output of `node --version`, for example v24.15.0) is
# at least $MIN_NODE_VERSION. Only major and minor are compared; the floor's
# patch is 0. Anything that is not a version fails, so a broken `node` is
# refused rather than assumed fine.
node_meets_floor() {
  local pattern='^v?([0-9]+)\.([0-9]+)\.' floor_major floor_minor have_major have_minor
  [[ "$1" =~ $pattern ]] || return 1
  have_major=$((10#${BASH_REMATCH[1]}))
  have_minor=$((10#${BASH_REMATCH[2]}))
  floor_major="${MIN_NODE_VERSION%%.*}"
  floor_minor="${MIN_NODE_VERSION#*.}"
  floor_minor="${floor_minor%%.*}"
  ((have_major > floor_major || (have_major == floor_major && have_minor >= floor_minor)))
}

# Walk up from $1 until an existing path is found and print it. Shared by
# canonical_storage_path (needs the remaining suffix too) and probe_storage
# (only needs the ancestor itself).
nearest_existing_ancestor() {
  local parent="$1" next_parent
  while [[ ! -e "$parent" ]]; do
    next_parent="$(dirname "$parent")"
    if [[ "$next_parent" == "$parent" ]]; then
      return 1
    fi
    parent="$next_parent"
  done
  printf '%s' "$parent"
}

canonical_storage_path() {
  local candidate="$1" ancestor suffix
  case "/$candidate/" in
    */../*) return 1 ;;
  esac
  ancestor="$(nearest_existing_ancestor "$candidate")" || return 1
  [[ -d "$ancestor" ]] || return 1
  suffix="${candidate#"$ancestor"}"
  printf '%s%s' "$(cd "$ancestor" && pwd -P)" "$suffix"
}

# The bootstrap owns exactly one cache location: the project-local
# $DEFAULT_CONTEXT_MODE_DIR subtree. Any override resolving elsewhere -- another
# path inside the repository, or anywhere outside it -- is refused.
#
# This is an ownership boundary, not just a safety check. configure_storage
# quarantines an unaudited cache by *renaming the directory*, so honouring an
# arbitrary external override would let the bootstrap reorganize user-owned
# state outside the repository. Refusing the override means such a path is never
# stamped, renamed, or otherwise touched.
storage_override_is_allowed() {
  case "$1" in
    "$DEFAULT_CONTEXT_MODE_DIR"|"$DEFAULT_CONTEXT_MODE_DIR/"*) return 0 ;;
    *) return 1 ;;
  esac
}

select_storage_root() {
  local requested="${CONTEXT_MODE_DIR:-}" canonical
  if [[ -z "$requested" ]]; then
    printf '%s' "$DEFAULT_CONTEXT_MODE_DIR"
    return 0
  fi
  if [[ "$requested" != /* ]]; then
    warn "ignoring non-absolute CONTEXT_MODE_DIR; using project-local cache"
    printf '%s' "$DEFAULT_CONTEXT_MODE_DIR"
    return 0
  fi
  if ! canonical="$(canonical_storage_path "$requested")"; then
    warn "ignoring unsafe CONTEXT_MODE_DIR; using project-local cache"
    printf '%s' "$DEFAULT_CONTEXT_MODE_DIR"
    return 0
  fi
  if ! storage_override_is_allowed "$canonical"; then
    warn "ignoring unsupported CONTEXT_MODE_DIR '$requested': only $DEFAULT_CONTEXT_MODE_DIR and paths beneath it are bootstrap-owned; using the project-local cache and leaving that path untouched"
    printf '%s' "$DEFAULT_CONTEXT_MODE_DIR"
    return 0
  fi
  printf '%s' "$canonical"
}

# Generates (once) and returns a random secret stored at
# $PROVENANCE_SECRET_FILE, outside the nested ai-state repository. The marker
# also checks three plaintext fields (repository, pinned version, filter
# contract) that are public or predictable, so a marker planted without the
# secret does not match. state-sync.sh adds and commits only under .claude/, so
# this file never enters ai-state history, and the root restore copies only
# allowlisted adapter files, never this one. This gives no protection against a
# remote that replaces the synced scripts themselves.
read_or_create_provenance_secret() {
  if [[ ! -s "$PROVENANCE_SECRET_FILE" ]]; then
    local secret="" tmp_secret
    if command -v openssl >/dev/null 2>&1; then
      secret="$(openssl rand -hex 32 2>/dev/null || true)"
    fi
    if [[ -z "$secret" ]]; then
      secret="$(od -An -tx1 -N32 /dev/urandom 2>/dev/null | tr -d ' \n' || true)"
    fi
    [[ -n "$secret" ]] || return 1
    # Write to a sibling temp file, then atomically no-clobber rename it into
    # place. Two dispatcher invocations racing on first run each land here
    # concurrently; without this, each generates its own value and each
    # overwrites the file directly, so a racing invocation can cat back a
    # different secret than the one that ultimately lands on disk. With
    # `mv -n`, at most one temp file ever becomes the real file, and every
    # invocation -- winner or loser -- always cats that same, single result.
    tmp_secret="$PROVENANCE_SECRET_FILE.tmp.$$"
    # Clean the temp file up even if this shell is interrupted between the
    # write and the rename; a leftover `.tmp.<pid>` is secret-bearing. The
    # handler reads a script-scope variable with a `:-` default, never a
    # function local, so it stays safe under `set -u` on every path.
    PROVENANCE_TMP="$tmp_secret"
    trap 'rm -f "${PROVENANCE_TMP:-}"' RETURN INT TERM
    if ! (umask 077; printf '%s' "$secret" > "$tmp_secret"); then
      # RETURN is function-scoped, but INT/TERM are process-wide, so reset them
      # on this early path too or a later signal re-fires a stale handler.
      trap - INT TERM
      return 1
    fi
    mv -n "$tmp_secret" "$PROVENANCE_SECRET_FILE" 2>/dev/null || true
    trap - INT TERM
  fi
  cat "$PROVENANCE_SECRET_FILE"
}

configure_storage() {
  CONTEXT_MODE_DIR="$(select_storage_root)"
  local provenance="$CONTEXT_MODE_DIR/.bootstrap-provenance" quarantine secret move_error
  if ! secret="$(read_or_create_provenance_secret)"; then
    warn "unable to establish a local Context Mode provenance secret"
    return 1
  fi
  if [[ -d "$CONTEXT_MODE_DIR" ]] && ! {
    grep -Fqx "repository=$REPO_ROOT" "$provenance" 2>/dev/null \
      && grep -Fqx "context-mode=$PINNED_CONTEXT_MODE_VERSION" "$provenance" 2>/dev/null \
      && grep -Fqx "filter=$FILTER_CONTRACT" "$provenance" 2>/dev/null \
      && grep -Fqx "secret=$secret" "$provenance" 2>/dev/null
  }; then
    quarantine="$CONTEXT_MODE_DIR.untrusted.$(date -u +%Y%m%dT%H%M%SZ).$$"
    if move_error="$(mv "$CONTEXT_MODE_DIR" "$quarantine" 2>&1)"; then
      warn "preserved unaudited Context Mode cache at $quarantine"
    elif [[ ! -e "$CONTEXT_MODE_DIR" && ! -L "$CONTEXT_MODE_DIR" ]]; then
      # Another dispatcher quarantined the same folder between the check above
      # and this move, so the folder is simply gone. Nothing was trusted, and
      # nothing is deleted: the other dispatcher's move preserved the bytes.
      warn "Context Mode cache at $CONTEXT_MODE_DIR was already moved aside by another dispatcher; starting with a fresh one"
    else
      # The unaudited folder is still there. It is never trusted, never
      # deleted, and never stamped: fail and keep mv's own diagnostic.
      [[ -z "$move_error" ]] || printf '%s\n' "$move_error" >&2
      return 1
    fi
  fi
  if ! mkdir -p "$CONTEXT_MODE_DIR" 2>/dev/null; then
    return 1
  fi
  CONTEXT_MODE_DIR="$(cd "$CONTEXT_MODE_DIR" && pwd)"
  provenance="$CONTEXT_MODE_DIR/.bootstrap-provenance"
  if [[ ! -f "$provenance" ]]; then
    if ! printf 'repository=%s\ncontext-mode=%s\nfilter=%s\nsecret=%s\n' \
      "$REPO_ROOT" "$PINNED_CONTEXT_MODE_VERSION" "$FILTER_CONTRACT" "$secret" > "$provenance"; then
      return 1
    fi
  fi
  export CONTEXT_MODE_DIR
  # Context Mode 2.x ignores CONTEXT_MODE_DIR and keeps everything it writes
  # under CONTEXT_MODE_DATA_DIR. Overwrite whatever the caller exported, so no
  # inherited value can move data out of the guarded root.
  CONTEXT_MODE_DATA_DIR="$CONTEXT_MODE_DIR"
  export CONTEXT_MODE_DATA_DIR
  CONTEXT_MODE_PROJECT_ROOT="$REPO_ROOT"
  export CONTEXT_MODE_PROJECT_ROOT
}

probe_storage() {
  local storage_root parent
  storage_root="$(select_storage_root)"
  printf 'PASS context-mode-dispatch: storage-root=%s\n' "$storage_root"
  if [[ -d "$storage_root" ]]; then
    if [[ -w "$storage_root" ]]; then
      printf 'PASS context-mode-dispatch: storage=writable\n'
      return 0
    fi
    return 1
  fi

  parent="$(nearest_existing_ancestor "$storage_root")" || return 1
  if [[ -d "$parent" && -w "$parent" ]]; then
    printf 'PASS context-mode-dispatch: storage=creatable\n'
    return 0
  fi
  return 1
}

self_check() {
  local command_path="" exe="" observed="" observed_node=""
  # Look the launcher up from the same folder `server` mode runs in.
  cd "$REPO_ROOT" || warn "unable to enter $REPO_ROOT; launcher lookups use the current folder"
  printf 'PASS context-mode-dispatch: required-version=%s\n' "$PINNED_CONTEXT_MODE_VERSION"
  printf 'PASS context-mode-dispatch: required-node=%s\n' "$MIN_NODE_VERSION"
  if command -v node >/dev/null 2>&1; then
    observed_node="$(node --version 2>/dev/null || true)"
  fi
  printf 'PASS context-mode-dispatch: observed-node=%s\n' "${observed_node:-none-on-PATH}"
  node_meets_floor "$observed_node" \
    || warn "Node.js $MIN_NODE_VERSION or newer is required (observed ${observed_node:-none}); the MCP server cannot start"

  # Report the observed version of whatever is actually on PATH before deciding
  # anything, so the self-check proves the version contract instead of merely
  # restating the pin.
  if exe="$(command -v context-mode 2>/dev/null)" && [[ -n "$exe" ]]; then
    printf 'PASS context-mode-dispatch: resolved-path=%s\n' "$exe"
    if observed="$(direct_context_mode_version "$exe")" && [[ -n "$observed" ]]; then
      printf 'PASS context-mode-dispatch: observed-version=%s\n' "$observed"
    else
      observed=""
      warn "observed-version=undeterminable for $exe"
    fi
  else
    printf 'PASS context-mode-dispatch: resolved-path=none-on-PATH\n'
  fi

  if command_path="$(resolve_context_mode 2>/dev/null)"; then
    printf 'PASS context-mode-dispatch: launcher=%s\n' "$command_path"
    if [[ "$command_path" == "npx" ]]; then
      printf 'PASS context-mode-dispatch: version-contract=pinned-via-npx@%s\n' \
        "$PINNED_CONTEXT_MODE_VERSION"
      if [[ -n "$exe" ]]; then
        warn "context-mode on PATH does not satisfy the version contract; using pinned npx instead"
      fi
    else
      printf 'PASS context-mode-dispatch: version-contract=pinned-direct-binary\n'
    fi
  else
    if [[ -n "$exe" ]]; then
      warn "version-contract=FAIL; context-mode on PATH is ${observed:-undeterminable}, npx is unavailable, so the MCP server cannot start"
    else
      warn "context-mode and npx are unavailable; the MCP server cannot start"
    fi
  fi
  printf 'PASS context-mode-dispatch: filter=%s\n' "$FILTER_SCRIPT"

  probe_storage \
    || warn "storage root is not writable or creatable: $(select_storage_root)"

  if [[ -d "$REPO_ROOT/.claude/.git" ]]; then
    if git -C "$REPO_ROOT/.claude" check-ignore -q .cache/context-mode 2>/dev/null; then
      printf 'PASS context-mode-dispatch: nested-ignore=.cache/\n'
    else
      warn "nested .claude repository does not ignore .cache/; run state-sync setup/checkpoint"
    fi
  else
    printf 'PASS context-mode-dispatch: nested-ignore=not-initialized\n'
  fi
}

if [[ "${1:-}" == "--self-check" ]]; then
  self_check
  exit 0
fi

MODE="${1:-}"

# Context Mode has no hook route any more. Stale hook wiring in an adapter that
# the installer keeps on refresh must stay harmless: read the event payload,
# print nothing, and exit 0 before any storage setup.
[[ "$MODE" == "server" ]] || { cat > /dev/null || true; exit 0; }

# Context Mode 2.x with `--agent codex` keys its project to the working folder's
# Git repository, so a server started inside the nested `.claude` repository
# would index into a separate project. Start from the outer repository root
# (computed from this script's own location), before any launcher lookup, so the
# version proof, the filter, and the server all search PATH from the same
# folder. The filter also checks `ctx_index` paths against this folder.
if ! cd "$REPO_ROOT"; then
  printf 'ERROR context-mode-dispatch: unable to enter the repository root %s\n' "$REPO_ROOT" >&2
  exit 1
fi

if ! configure_storage; then
  printf 'ERROR context-mode-dispatch: guarded storage/provenance unavailable\n' >&2
  exit 1
fi

if ! command_path="$(resolve_context_mode)"; then
  printf 'ERROR context-mode-dispatch: context-mode and npx are unavailable; MCP server cannot start\n' >&2
  exit 127
fi

if [[ ! -f "$FILTER_SCRIPT" ]] || ! command -v node >/dev/null 2>&1; then
  printf 'ERROR context-mode-dispatch: MCP filter or Node runtime unavailable\n' >&2
  exit 127
fi
observed_node="$(node --version 2>/dev/null || true)"
if ! node_meets_floor "$observed_node"; then
  printf 'ERROR context-mode-dispatch: Node.js %s or newer is required (observed %s); MCP server cannot start\n' \
    "$MIN_NODE_VERSION" "${observed_node:-none}" >&2
  exit 1
fi

# One server identity for every client: `--agent codex` needs no
# CLAUDE_PROJECT_DIR and no --workspace-folder, because the working folder
# (above) is what keys the project.
if [[ "$command_path" == "npx" ]]; then
  exec node "$FILTER_SCRIPT" -- npx -y "context-mode@$PINNED_CONTEXT_MODE_VERSION" server --agent codex
fi
exec node "$FILTER_SCRIPT" -- "$command_path" server --agent codex
