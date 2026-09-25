"""Ownership boundaries for generated bootstrap runtime content.

The generator, installer, restoration wrapper, and validators share this
small contract.  It intentionally classifies only boundaries that affect
bootstrap refreshes; it is not a manifest of every generated file.
"""

from __future__ import annotations

from pathlib import Path, PurePath, PurePosixPath


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
    ".agents",
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
    # Derived machine-local hook state. It is ignored/untracked by state sync
    # and must never be restored, compared, or deleted by bootstrap refreshes.
    ".cache",
    "instructions/project-context.instructions.md",
    # Machine-local client settings the bootstrap never generates. Without this
    # every install deleted the consumer's own settings as an obsolete owned
    # file, which is data loss, not a refresh.
    "settings.local.json",
)

# Each of these README files is bootstrap-authored reference documentation
# that merely lives inside an otherwise consumer-owned state directory above.
# Unlike the rest of that directory's content (real plans, logs, and
# reports), it must always match the shipped copy, so a refresh regenerates
# it even though the directory it lives in is exempt from that comparison.
# A repeat install must still leave every sibling file in the same
# directory untouched.
STATE_DIR_OWNED_README_PATHS = tuple(
    f"{state_dir}/README.md"
    for state_dir in ("plans", "explorations", "session_logs", "quality_reports")
)

# OpenWiki's own installer takes ownership of its skill bundle inside every
# skill-hosting surface (`.claude/skills/openwiki`, `.agents/skills/openwiki`)
# once it runs there. Each entry is checked relative to the surface root that
# hosts it (`.claude` or `.agents`), the same way `CONSUMER_STATE_PATHS` is
# checked relative to `.claude`. A path shaped like one of these entries is
# ordinary bootstrap-generated content — refreshed and drift-checked like any
# other — until `THIRD_PARTY_SKILL_MARKER` actually exists in it; see
# `is_third_party_skill_dir`.
THIRD_PARTY_SKILL_PATHS = ("skills/openwiki",)

# The file OpenWiki's own installer writes into a skill directory it takes
# ownership of. Its presence, not the path shape alone, is what stops the
# bootstrap from generating, drift-checking, or refreshing that directory.
THIRD_PARTY_SKILL_MARKER = ".openwiki-install.json"

INSTALL_MODE_KEY = "BOOTSTRAP_COMMIT_COPILOT_SURFACE"

# Every root path a full install writes. A repository that tracks one of them
# and carries no bootstrap evidence is team-owned, so a plain install refuses
# it instead of taking it over.
FULL_INSTALL_ROOT_PATHS = (".claude", ".devcontainer") + RESTORABLE_ROOT_PATHS

# The sidecar: a private, per-clone overlay inside a team-owned harness. Paths
# come from the native runs frozen in docs/sidecar-provider-contract.md.
SIDECAR_SKILLS = ("debug-investigator", "humanize", "ponytail", "ponytail-review")
SIDECAR_SKILL_WRITE_ROOTS = (".claude/skills", ".agents/skills")
# Every repository skill folder a supported client reads. A skill name taken
# in any of them by content the sidecar does not own is skipped everywhere,
# so a sidecar copy never hides a team skill.
SIDECAR_SKILL_READ_ROOTS = SIDECAR_SKILL_WRITE_ROOTS + (
    ".github/skills",
    ".agent/skills",
    ".codex/skills",
)
# Bridge path -> the frontmatter its client needs ("" means none).
SIDECAR_BRIDGES = {
    ".claude/rules/ai-bootstrap-sidecar.md": "",
    ".github/instructions/ai-bootstrap-sidecar.instructions.md": 'applyTo: "**"',
}
SIDECAR_MANIFEST_NAME = "ai-bootstrap-sidecar.json"
SIDECAR_STAGING_NAME = "ai-bootstrap-sidecar-staging"
SIDECAR_EXCLUDE_BEGIN = "# BEGIN ai-bootstrap sidecar"
SIDECAR_EXCLUDE_END = "# END ai-bootstrap sidecar"


def active_ignore_patterns(commit_copilot_surface: bool) -> tuple[str, ...]:
    """Return install-time ignore patterns for generated runtime overlays."""
    patterns = (
        ".claude/",
        ".codex/",
        ".agents/",
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


def is_consumer_state_path(relative_path: str | PurePath) -> bool:
    """Return whether a path relative to ``.claude`` belongs to the consumer."""
    path = PurePosixPath(relative_path)
    return any(
        path == PurePosixPath(owner) or PurePosixPath(owner) in path.parents
        for owner in CONSUMER_STATE_PATHS
    )


def is_third_party_skill_path(relative_path: str | PurePath) -> bool:
    """Return whether a skill-surface-relative path is shaped like a
    third-party skill bundle. Shape alone does not mean it is owned; see
    ``is_third_party_skill_dir`` for the marker-gated ownership check."""
    path = PurePosixPath(relative_path)
    return any(
        path == PurePosixPath(owner) or PurePosixPath(owner) in path.parents
        for owner in THIRD_PARTY_SKILL_PATHS
    )


def is_third_party_skill_dir(dir_path: Path) -> bool:
    """Return whether a live directory is a marker-claimed third-party bundle.

    Requires both that ``dir_path`` is shaped like an entry in
    ``THIRD_PARTY_SKILL_PATHS`` (e.g. ends in ``skills/openwiki``) and that
    OpenWiki's own installer has already claimed it by writing
    ``THIRD_PARTY_SKILL_MARKER`` directly inside it. Before that marker
    exists, the directory is ordinary bootstrap-generated content.
    """
    posix_dir = PurePosixPath(dir_path.as_posix())
    is_owned_shape = any(posix_dir.match(owner) for owner in THIRD_PARTY_SKILL_PATHS)
    return is_owned_shape and (dir_path / THIRD_PARTY_SKILL_MARKER).is_file()


def is_root_adapter_path(relative_path: str | PurePath) -> bool:
    """Return whether a path is restored from ``.claude/bootstrap-root``."""
    path = PurePosixPath(relative_path)
    return any(
        path == PurePosixPath(adapter) or PurePosixPath(adapter) in path.parents
        for adapter in RESTORABLE_ROOT_PATHS
    )


def restore_manifest(
    commit_copilot_surface: bool = False,
) -> str:
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
    """Read the inert Copilot-surface install mode from a root manifest."""
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
