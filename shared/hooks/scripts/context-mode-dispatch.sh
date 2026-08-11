#!/usr/bin/env bash
set -euo pipefail

warn() {
  printf 'WARN context-mode-dispatch: %s\n' "$*" >&2
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
DEFAULT_CONTEXT_MODE_DIR="$REPO_ROOT/.claude/.cache/context-mode"
PINNED_CONTEXT_MODE_VERSION="1.0.169"
FILTER_CONTRACT="ctx-index-file-content-v1"
FILTER_SCRIPT="$SCRIPT_DIR/context-mode-mcp-filter.mjs"
# Outside the ai-state working tree (.claude/) on purpose: state-sync.sh never
# adds, commits, or restores anything at $REPO_ROOT other than under .claude/,
# so a hostile/compromised ai-state remote can never read or overwrite this
# file. See configure_storage below.
PROVENANCE_SECRET_FILE="$REPO_ROOT/.context-mode-provenance.secret"

# Prints the installed package version of a direct `context-mode` executable.
#
# Context Mode 1.0.169 has no `--version`/`-v`/`version` flag (all three exit 0
# printing nothing), and `doctor` is slow, ANSI-decorated, and performs a network
# npm check, so neither is usable as a per-hook-event gate. The executable is an
# npm bin symlink into the installed package directory, so resolve it and read
# the owning package.json: offline, deterministic, and independent of the
# bundle's internals. The name is checked too, so a nested dependency manifest
# can never be mistaken for Context Mode's own.
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
# $PROVENANCE_SECRET_FILE, outside the nested ai-state repository. Comparing
# this value is what makes the on-disk provenance marker unforgeable by a
# hostile ai-state remote: the three plaintext fields it also checks
# (repository, pinned version, filter contract) are public/predictable, but
# the remote can never read or write this file, so it cannot learn or plant
# a matching secret.
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
  local provenance="$CONTEXT_MODE_DIR/.bootstrap-provenance" quarantine secret
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
    if ! mv "$CONTEXT_MODE_DIR" "$quarantine"; then
      return 1
    fi
    warn "preserved unaudited Context Mode cache at $quarantine"
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
  local command_path="" exe="" observed=""
  printf 'PASS context-mode-dispatch: required-version=%s\n' "$PINNED_CONTEXT_MODE_VERSION"

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
      warn "version-contract=FAIL; context-mode on PATH is ${observed:-undeterminable}, npx is unavailable, so hook events will be skipped"
    else
      warn "context-mode and npx are unavailable; hook events will be skipped"
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
shift || true

if ! configure_storage; then
  if [[ "$MODE" == "server" ]]; then
    printf 'ERROR context-mode-dispatch: guarded storage/provenance unavailable\n' >&2
    exit 1
  fi
  warn "storage unavailable; skipping optional hook event"
  exit 0
fi

if ! command_path="$(resolve_context_mode)"; then
  if [[ "$MODE" == "server" ]]; then
    printf 'ERROR context-mode-dispatch: context-mode and npx are unavailable; MCP server cannot start\n' >&2
    exit 127
  fi
  warn "context-mode and npx are unavailable; skipping optional hook event: $MODE $*"
  exit 0
fi

if [[ "$MODE" == "server" ]]; then
  if [[ ! -f "$FILTER_SCRIPT" ]] || ! command -v node >/dev/null 2>&1; then
    printf 'ERROR context-mode-dispatch: MCP filter or Node runtime unavailable\n' >&2
    exit 127
  fi
  if [[ "$command_path" == "npx" ]]; then
    exec node "$FILTER_SCRIPT" -- npx -y "context-mode@$PINNED_CONTEXT_MODE_VERSION"
  fi
  exec node "$FILTER_SCRIPT" -- "$command_path"
fi

case "$MODE" in
  github-copilot) CONTEXT_MODE_TARGET="vscode-copilot" ;;
  claude-code) CONTEXT_MODE_TARGET="claude-code" ;;
  openai-codex) CONTEXT_MODE_TARGET="codex" ;;
  *) CONTEXT_MODE_TARGET="$MODE" ;;
esac

if [[ "$command_path" == "npx" ]]; then
  exec npx -y "context-mode@$PINNED_CONTEXT_MODE_VERSION" hook "$CONTEXT_MODE_TARGET" "$@"
fi
exec "$command_path" hook "$CONTEXT_MODE_TARGET" "$@"
