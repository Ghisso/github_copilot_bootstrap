"""Ownership boundaries for generated bootstrap runtime content.

The generator, installer, restoration wrapper, and validators share this
small contract.  It intentionally classifies only boundaries that affect
bootstrap refreshes; it is not a manifest of every generated file.
"""

from __future__ import annotations

from pathlib import PurePath, PurePosixPath


# The source repository deliberately keeps this concise adapter tracked.  It
# describes authoring the bootstrap, so it is validated by required invariants
# rather than compared byte-for-byte with a consumer's generated AGENTS.md.
TRACKED_AUTHORING_PATHS = ("AGENTS.md",)

# These root paths are generated in consumer repositories and copied into the
# nested ai-state repository for restoration on a fresh machine.
ROOT_ADAPTER_PATHS = (
    "CLAUDE.md",
    "AGENTS.md",
    ".mcp.json",
    ".codex",
    ".vscode/mcp.json",
    ".vscode/tasks.json",
)
COPILOT_SURFACE_PATHS = (
    ".github/agents",
    ".github/hooks",
    ".github/instructions",
    ".github/copilot-instructions.md",
)
RESTORABLE_ROOT_PATHS = ROOT_ADAPTER_PATHS + COPILOT_SURFACE_PATHS
RESTORE_ALLOWLIST_TOKEN = "__BOOTSTRAP_ALLOWED_ROOT_PATHS__"

# These paths are intentionally mutable in every consumer.  A generated seed
# can exist for a fresh install, but a refresh must not use it as an equality
# target or overwrite an existing consumer copy.
CONSUMER_STATE_PATHS = (
    "MEMORY.md",
    "plans",
    "explorations",
    "session_logs",
    "quality_reports",
    "instructions/project-context.instructions.md",
)

INSTALL_MODE_KEY = "BOOTSTRAP_COMMIT_COPILOT_SURFACE"


def active_ignore_patterns(commit_copilot_surface: bool) -> tuple[str, ...]:
    """Return install-time ignore patterns for generated runtime overlays."""
    patterns = (
        ".claude/",
        ".codex/",
        ".github/agents/",
        ".github/hooks/",
        ".github/instructions/",
        ".github/copilot-instructions.md",
        ".vscode/mcp.json",
        ".mcp.json",
        ".claude/quality_reports/",
        "AGENTS.md",
        "CLAUDE.md",
        ".uv-cache/",
    )
    if not commit_copilot_surface:
        return patterns
    copilot_patterns = tuple(
        f"{path}/" if "." not in path.rsplit("/", 1)[-1] else path
        for path in COPILOT_SURFACE_PATHS
    )
    return tuple(pattern for pattern in patterns if pattern not in copilot_patterns)


def bootstrap_root_paths(commit_copilot_surface: bool) -> tuple[str, ...]:
    """Return generated root adapters copied into ``.claude/bootstrap-root``."""
    if commit_copilot_surface:
        return ROOT_ADAPTER_PATHS
    return ROOT_ADAPTER_PATHS + COPILOT_SURFACE_PATHS


def is_consumer_state_path(relative_path: str | PurePath) -> bool:
    """Return whether a path relative to ``.claude`` belongs to the consumer."""
    path = PurePosixPath(relative_path)
    return any(
        path == PurePosixPath(owner) or PurePosixPath(owner) in path.parents
        for owner in CONSUMER_STATE_PATHS
    )


def is_root_adapter_path(relative_path: str | PurePath) -> bool:
    """Return whether a path is restored from ``.claude/bootstrap-root``."""
    path = PurePosixPath(relative_path)
    return any(
        path == PurePosixPath(adapter) or PurePosixPath(adapter) in path.parents
        for adapter in RESTORABLE_ROOT_PATHS
    )


def restore_manifest(commit_copilot_surface: bool = False) -> str:
    """Render inert root-adapter records for the restoration shell script."""
    paths = "\n".join(
        f"BOOTSTRAP_ROOT_PATH={path}"
        for path in bootstrap_root_paths(commit_copilot_surface)
    )
    mode = int(commit_copilot_surface)
    return (
        "# Generated from scripts/runtime_ownership.py.\n"
        f"{INSTALL_MODE_KEY}={mode}\n{paths}\n"
    )


def install_mode_from_manifest(text: str) -> bool | None:
    """Read the inert install mode, including manifests from older releases."""
    mode: bool | None = None
    paths: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(f"{INSTALL_MODE_KEY}="):
            if mode is not None:
                return None
            value = line.removeprefix(f"{INSTALL_MODE_KEY}=")
            if value not in {"0", "1"}:
                return None
            mode = value == "1"
            continue
        if not line.startswith("BOOTSTRAP_ROOT_PATH="):
            return None
        path = line.removeprefix("BOOTSTRAP_ROOT_PATH=")
        if path not in RESTORABLE_ROOT_PATHS or path in paths:
            return None
        paths.append(path)

    path_set = set(paths)
    if mode is not None:
        return mode if path_set == set(bootstrap_root_paths(mode)) else None
    if path_set == set(bootstrap_root_paths(False)):
        return False
    if path_set == set(bootstrap_root_paths(True)):
        return True
    return None


def render_restore_script(template: str) -> str:
    """Bind the shell restorer's trusted allowlist to this ownership map."""
    if template.count(RESTORE_ALLOWLIST_TOKEN) != 1:
        raise ValueError("restore script must contain exactly one allowlist token")
    return template.replace(RESTORE_ALLOWLIST_TOKEN, "|".join(RESTORABLE_ROOT_PATHS))
