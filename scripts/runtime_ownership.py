"""Ownership boundaries for generated bootstrap runtime content.

The generator, installer, restoration wrapper, and validators share this
small contract.  It intentionally classifies only boundaries that affect
bootstrap refreshes; it is not a manifest of every generated file.
"""

from __future__ import annotations

from pathlib import PurePath, PurePosixPath


# The source repository deliberately keeps concise root adapters tracked. They
# describe bootstrap authoring, so they are validated by required invariants
# rather than compared byte-for-byte with a consumer's generated adapters.
TRACKED_AUTHORING_PATHS = ("AGENTS.md", "CLAUDE.md")

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
# Antigravity owns individual files below its shared workspace directory, not
# the directory itself.  Consumers can keep private agents and skills beside
# generated adapters, so this surface is recorded file-by-file in the inert
# ownership manifest instead of being added to ``ROOT_ADAPTER_PATHS``.
ANTIGRAVITY_ROOT = ".agents"
ANTIGRAVITY_MANIFEST_KEY = "BOOTSTRAP_ANTIGRAVITY_PATH"
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
    # Derived machine-local hook state. It is ignored/untracked by state sync
    # and must never be restored, compared, or deleted by bootstrap refreshes.
    ".cache",
    "instructions/project-context.instructions.md",
    # Machine-local client settings the bootstrap never generates. Without this
    # every install deleted the consumer's own settings as an obsolete owned
    # file, which is data loss, not a refresh.
    "settings.local.json",
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
        # Anti-forgery secret for the Context Mode cache provenance marker
        # (context-mode-dispatch.sh), created at the consumer repository
        # root, outside .claude/. It must never enter the consumer's main
        # history via a routine `git add -A`. The glob also covers the
        # `.tmp.<pid>` sibling the dispatcher writes before renaming, which a
        # signal between write and rename can leave behind.
        ".context-mode-provenance.secret*",
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


def is_antigravity_owned_path(path: str | PurePath) -> bool:
    """Return whether one file belongs to a generated Antigravity surface."""
    pure_path = PurePosixPath(path)
    if pure_path.parts[:1] != (ANTIGRAVITY_ROOT,):
        return False
    if pure_path.as_posix() in {
        f"{ANTIGRAVITY_ROOT}/mcp_config.json",
        f"{ANTIGRAVITY_ROOT}/hooks.json",
    }:
        return True
    return (
        len(pure_path.parts) == 4
        and pure_path.parts[1] == "agents"
        and pure_path.parts[3] == "agent.md"
    ) or (len(pure_path.parts) >= 3 and pure_path.parts[1] == "skills")


def antigravity_manifest_paths(
    text: str, allowed_paths: tuple[str, ...] | None = None
) -> tuple[str, ...] | None:
    """Return validated file-granular Antigravity ownership records.

    Older manifests did not record Antigravity files and intentionally map to
    an empty tuple.  A malformed record returns ``None`` so callers fail
    closed rather than treating arbitrary consumer files as generated.
    """
    paths: list[str] = []
    allowed = set(allowed_paths) if allowed_paths is not None else None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if (
            not line
            or line.startswith("#")
            or not line.startswith(f"{ANTIGRAVITY_MANIFEST_KEY}=")
        ):
            continue
        path = line.removeprefix(f"{ANTIGRAVITY_MANIFEST_KEY}=")
        pure_path = PurePosixPath(path)
        if (
            not is_antigravity_owned_path(path)
            or pure_path.is_absolute()
            or "." in pure_path.parts
            or ".." in pure_path.parts
            or path.endswith("/")
            or "//" in path
            or path in paths
            or (allowed is not None and path not in allowed)
        ):
            return None
        paths.append(path)
    return tuple(paths)


def antigravity_allowlist_paths(text: str) -> tuple[str, ...] | None:
    """Read a generated Antigravity allowlist without accepting extra records."""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if (
            not line
            or line.startswith("#")
            or line.startswith(f"{ANTIGRAVITY_MANIFEST_KEY}=")
        ):
            continue
        return None
    return antigravity_manifest_paths(text)


def render_antigravity_ownership_manifest(paths: tuple[str, ...]) -> str:
    """Render the generated allowlist used to validate dynamic ownership."""
    parsed_paths = antigravity_manifest_paths(
        "\n".join(f"{ANTIGRAVITY_MANIFEST_KEY}={path}" for path in paths), paths
    )
    if parsed_paths is None or tuple(sorted(parsed_paths)) != paths:
        raise ValueError("Antigravity ownership paths must be sorted unique adapters")
    return (
        "# Generated Antigravity ownership allowlist.\n"
        + "\n".join(f"{ANTIGRAVITY_MANIFEST_KEY}={path}" for path in paths)
        + "\n"
    )


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


def restore_manifest(
    commit_copilot_surface: bool = False,
    antigravity_paths: tuple[str, ...] = (),
) -> str:
    """Render inert root-adapter records for the restoration shell script."""
    paths = "\n".join(
        f"BOOTSTRAP_ROOT_PATH={path}"
        for path in bootstrap_root_paths(commit_copilot_surface)
    )
    antigravity_records = antigravity_manifest_paths(
        "\n".join(f"{ANTIGRAVITY_MANIFEST_KEY}={path}" for path in antigravity_paths),
        antigravity_paths,
    )
    if (
        antigravity_records is None
        or tuple(sorted(antigravity_records)) != antigravity_paths
    ):
        raise ValueError(
            "Antigravity manifest paths must be sorted unique .agents files"
        )
    antigravity = "\n".join(
        f"{ANTIGRAVITY_MANIFEST_KEY}={path}" for path in antigravity_paths
    )
    mode = int(commit_copilot_surface)
    return (
        "# Generated from scripts/runtime_ownership.py.\n"
        f"{INSTALL_MODE_KEY}={mode}\n{paths}\n{antigravity}\n"
    )


def install_mode_from_manifest(
    text: str, allowed_antigravity_paths: tuple[str, ...] | None = None
) -> bool | None:
    """Read the inert install mode, including manifests from older releases."""
    if antigravity_manifest_paths(text, allowed_antigravity_paths) is None:
        return None
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
            if line.startswith(f"{ANTIGRAVITY_MANIFEST_KEY}="):
                continue
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
