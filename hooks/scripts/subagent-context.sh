#!/usr/bin/env bash
# SubagentStart context hook for the Copilot harness.
#
# A custom sub-agent gets only its agent file, no repository instructions and no
# skill list (evidence F9). This hook gives it the text of
# .github/copilot-instructions.md, the Copilot root guidance, plus one fixed line
# on where agent files and skills live. The runtime reads top-level
# `additionalContext` for this event under both event spellings (probe P2), so the
# answer carries the text at the top level and nested in `hookSpecificOutput`,
# with no top-level `hookEventName`: the shape `additional_context` in
# _lib-frontmatter.sh prints for `github-copilot`. python3 builds the line with
# json.dumps because `json_escape` turns control characters into spaces, which
# would change the guidance text.
#
# This is a context hook, not a guard. It has no decision to make, never prints a
# decision field, and never exits non-zero: any error ends in a warning on stderr
# and the sub-agent starts without the context. It reads the guidance file only
# when it is a regular file of at most 2048 bytes and neither the file nor a
# folder on its way is a link, so no path outside the repository is read. python3
# counts the bytes on the open file, so the count is the same on GNU, BusyBox, and
# macOS.
set -Eeu -o pipefail

warn() {
  printf 'WARN subagent-context: %s\n' "$*" >&2
}

fail_open() {
  warn "internal error; skipping context"
  exit 0
}

trap fail_open ERR

PROVIDER="${1:-}"
if [[ "$PROVIDER" != "github-copilot" ]]; then
  warn "unsupported provider: ${PROVIDER:-missing}"
  exit 0
fi
if ! command -v python3 >/dev/null 2>&1; then
  warn "python3 is required to build the context; skipping"
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

IFS= read -r -d '' PROGRAM <<'PY' || true
import json
import os
import stat
import sys

LIMIT = 2048
RELATIVE = os.path.join(".github", "copilot-instructions.md")
LINE = (
    "Agent files live in `.claude/agents/<id>.md` and skills live in "
    "`.claude/skills/<name>/SKILL.md`. When your agent file lists a skill, read "
    "its SKILL.md file with the read tool."
)


def warn(message):
    sys.stderr.write("WARN subagent-context: %s\n" % message)


def guidance(root):
    """Return the guidance text, or "" when the file is absent or must not be read."""
    path = os.path.join(root, RELATIVE)
    if os.path.realpath(path) != os.path.join(os.path.realpath(root), RELATIVE):
        warn("not reading %s: a link, or outside the repository" % RELATIVE)
        return ""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        with os.fdopen(os.open(path, flags), "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                warn("not reading %s: not a regular file" % RELATIVE)
                return ""
            data = handle.read(LIMIT + 1)
    except FileNotFoundError:
        return ""
    except OSError as error:
        warn("cannot read %s: %s" % (RELATIVE, error.strerror or error))
        return ""
    if len(data) > LIMIT:
        warn("not reading %s: over %d bytes" % (RELATIVE, LIMIT))
        return ""
    return data.decode("utf-8", errors="replace")


try:
    payload = json.loads(sys.stdin.buffer.read())
except (ValueError, RecursionError):
    payload = None
if not isinstance(payload, dict):
    warn("malformed hook input; skipping context")
else:
    text = guidance(sys.argv[1])
    context = text + "\n" + LINE if text else LINE
    answer = {
        "additionalContext": context,
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": context,
        },
    }
    sys.stdout.write(json.dumps(answer) + "\n")
PY

# -I: no PYTHON* variables and no working folder on the module path, so a file
# named json.py in a project cannot replace the standard library.
python3 -I -c "$PROGRAM" "$REPO_ROOT"
