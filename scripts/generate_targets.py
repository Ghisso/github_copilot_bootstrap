#!/usr/bin/env python3
"""Generate target-native bootstrap files from shared source files."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runtime_ownership import (
    render_restore_script,
    restore_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "dist"
TARGETS = ("multi-agent",)
SUPPORTED_AGENT_TARGETS = (
    "github-copilot",
    "claude-code",
    "openai-codex",
    "google-antigravity",
)
AGENT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
AGENT_VISIBILITIES = {"public", "hidden"}
AGENT_CAPABILITIES = {
    "read",
    "search",
    "edit",
    "execute",
    "delegate",
    "todo",
    "web",
    "vscode",
}
AGENT_METADATA_FIELDS = {
    "id",
    "description",
    "role_type",
    "visibility",
    "capabilities",
    "delegates",
    "prompt_base",
    "targets",
    "model_intent",
}
COPY_IGNORE_PARTS = {".git", "__pycache__"}
COPY_IGNORE_SUFFIXES = {".pyc"}
SHARED_BASIS_NAMESPACE = ".claude"

# Every agent prompt (shared/agents/*/prompt.md) carries the identical line
# "Choose retrieval tools per .../tool-routing.instructions.md: Semble for
# semantic and related-code discovery..." — the "search" capability is this
# bootstrap's whole retrieval toolkit, not just literal-text grep. Without
# the mcp__<server> wildcards below, every subagent's `tools:` allowlist
# (an explicit list, not additive to defaults) silently omitted all
# mcp__semble__* tools, so a subagent told by its own
# prompt to "use Semble" had no such tool to call. `mcp__<server>` /
# `mcp__<server>__*` grants every tool from that MCP server (Claude Code
# subagent frontmatter `tools:` field: code.claude.com/docs/en/subagents.md).
# mcp__context-mode is included for the same reason: the dispatcher-backed
# server only ever advertises its filtered ctx_index/ctx_search/ctx_stats/
# ctx_doctor allowlist (shared/hooks/scripts/context-mode-mcp-filter.mjs), so
# granting the whole server here cannot expose a blocked tool.
CLAUDE_TOOL_MAP = {
    "read": ["Read"],
    "search": ["Grep", "Glob", "mcp__semble", "mcp__context-mode"],
    "edit": ["Edit", "MultiEdit", "Write"],
    "execute": ["Bash"],
    "delegate": ["Task"],
    "todo": ["TodoWrite"],
    "web": ["WebFetch", "WebSearch"],
}
# The "vscode" capability is intentionally Copilot-only: it maps to a Copilot
# tool and has no equivalent in Claude/Codex, so it is (correctly) omitted from
# their tool lists rather than silently mishandled.
#
# VS Code Copilot custom agents allow every tool from a configured MCP server
# with the documented `<server-name>/*` wildcard. Context Mode still exposes
# only its filtered server surface; this allowlist does not bypass that filter.
COPILOT_TOOL_MAP = {
    "read": ["read"],
    "search": ["search", "semble/*", "context-mode/*", "context7/*"],
    "edit": ["edit"],
    "execute": ["execute"],
    "delegate": ["agent"],
    "todo": ["todo", "todos"],
    "web": ["web"],
    "vscode": ["vscode"],
}
ANTIGRAVITY_TOOL_MAP = {
    "read": ["view_file", "list_dir", "find_by_name"],
    "search": ["grep_search"],
    "edit": ["write_to_file", "replace_file_content", "multi_replace_file_content"],
    "execute": ["run_command"],
    "delegate": ["invoke_subagent", "send_message", "manage_subagents"],
    "web": ["search_web", "read_url_content"],
}
PROVIDER_SUPPLEMENT_FILENAMES = {
    "openai-codex": "prompt.openai-codex.md",
    "google-antigravity": "prompt.google-antigravity.md",
}
TARGET_PATH_REPLACEMENTS = {
    "claude-code": (
        (".github/copilot-instructions.md", "CLAUDE.md"),
        (
            'normalized.endswith("/.github/copilot-instructions.md")',
            'normalized.endswith("/CLAUDE.md")',
        ),
        (".github/hooks/hooks.json", ".claude/settings.json"),
        (".github/hooks", ".claude/hooks"),
        ("git add .github/", "git add .claude/"),
        ("copilot-instructions.md", "CLAUDE.md"),
    ),
    "openai-codex": (
        (".github/copilot-instructions.md", "AGENTS.md"),
        (
            'normalized.endswith("/.github/copilot-instructions.md")',
            'normalized.endswith("/AGENTS.md")',
        ),
        (".github/hooks/hooks.json", ".codex/hooks.json"),
        (".github/hooks", ".codex/hooks"),
        ("git add .github/", "git add .claude/"),
        ("copilot-instructions.md", "AGENTS.md"),
    ),
}

ROOT_GUIDANCE_WORKFLOW = (
    "PRE-FLIGHT -> BRANCH -> PLAN WHEN NEEDED -> IMPLEMENT -> VERIFY -> REVIEW -> "
    "CLOSEOUT -> COMMIT"
)
CODEX_AGENT_INSTRUCTIONS_DELIMITER = "--- Canonical shared role instructions ---"
CODEX_ROLE_SUPPLEMENT_DELIMITER = "--- Codex role supplement: {agent_id} ---"
ANTIGRAVITY_ROLE_SUPPLEMENT_DELIMITER = (
    "--- Google Antigravity role supplement: {agent_id} ---"
)
POLICY_APPLICABILITY_KEY = "applicability"
POLICY_ALWAYS = "always"


@dataclass(frozen=True)
class Policy:
    """One canonical policy and its target-neutral applicability."""

    source: Path
    body: str
    paths: tuple[str, ...]

    @property
    def title(self) -> str:
        """Return the policy's first H1 or a filename-derived fallback."""
        fallback = (
            self.source.stem.replace(".instructions", "").replace("-", " ").title()
        )
        for line in self.body.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return fallback


def strip_quarantine(path: Path) -> None:
    """shared/ can carry macOS's com.apple.quarantine xattr (e.g. if this repo
    was ever extracted from a downloaded archive), and shutil.copy2/copytree
    preserve xattrs. Left alone that flag rides into dist/ and then into every
    consumer repo via install_bootstrap.py, where it makes git refuse to exec
    hook scripts (EPERM). Strip it from each generated target tree."""
    if sys.platform != "darwin":
        return
    subprocess.run(["xattr", "-rc", str(path)], check=False, capture_output=True)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, indent=2, sort_keys=False) + "\n")


def copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=copy_ignore)


def copy_ignore(directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        path = Path(directory) / name
        if name in COPY_IGNORE_PARTS or path.suffix in COPY_IGNORE_SUFFIXES:
            ignored.add(name)
    return ignored


def copy_skills(source: Path, destination: Path, target: str) -> None:
    copy_tree(source, destination)
    for path in destination.rglob("*"):
        if path.suffix not in {".md", ".py", ".sh"}:
            continue
        text = path.read_text(encoding="utf-8")
        path.write_text(transform_target_paths(text, target), encoding="utf-8")


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def ensure_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | 0o111)


def copy_text_transformed(
    source: Path,
    destination: Path,
    target: str,
    *,
    preserve_shared_git_hooks: bool = False,
) -> None:
    write_text(
        destination,
        transform_target_paths(
            source.read_text(encoding="utf-8"),
            target,
            preserve_shared_git_hooks=preserve_shared_git_hooks,
        ),
    )


def copy_tree_transformed(source: Path, destination: Path, target: str) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for path in sorted(source.rglob("*")):
        if (
            any(part in COPY_IGNORE_PARTS for part in path.parts)
            or path.suffix in COPY_IGNORE_SUFFIXES
        ):
            continue
        relative = path.relative_to(source)
        target_path = destination / relative
        if path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
        elif path.suffix in {".md", ".py", ".sh", ".json"}:
            copy_text_transformed(path, target_path, target)
            shutil.copymode(path, target_path)
        else:
            copy_file(path, target_path)


def render_shared_basis(target_root: Path, target: str) -> None:
    support_root = target_root / SHARED_BASIS_NAMESPACE
    target_label = {"multi-agent": "multi-agent"}[target]

    copy_text_transformed(
        REPO_ROOT / "shared" / "MEMORY.md", support_root / "MEMORY.md", "claude-code"
    )
    write_text(support_root / "bootstrap-ownership.env", restore_manifest())
    copy_tree_transformed(
        REPO_ROOT / "shared" / "templates", support_root / "templates", "claude-code"
    )
    copy_text_transformed(
        REPO_ROOT / "shared" / "scripts" / "record_findings.py",
        support_root / "scripts" / "record_findings.py",
        "claude-code",
    )
    copy_text_transformed(
        REPO_ROOT / "shared" / "scripts" / "verify.py",
        support_root / "scripts" / "verify.py",
        "claude-code",
    )
    # Ownership is a target-neutral authority shared by the installer and
    # generated verifier.  Transforming provider paths here would corrupt its
    # canonical root-adapter inventory (for example `.github/hooks`).
    copy_file(
        REPO_ROOT / "scripts" / "runtime_ownership.py",
        support_root / "scripts" / "runtime_ownership.py",
    )

    for name in ("plans", "quality_reports", "session_logs"):
        source = REPO_ROOT / "shared" / name / "README.md"
        copy_text_transformed(source, support_root / name / "README.md", "claude-code")

    write_text(
        support_root / "explorations" / "README.md",
        f"# Explorations\n\n"
        f"This directory stores exploratory or proof-of-concept plans created during {target_label} sessions.\n\n"
        "Use implementation plans for ready-to-execute work, and explorations when the work still needs "
        "research, feasibility checks, or throwaway prototypes.\n",
    )

    instructions_root = support_root / "instructions"
    instructions_root.mkdir(parents=True, exist_ok=True)
    for source in sorted((REPO_ROOT / "shared" / "policies").glob("*.instructions.md")):
        copy_text_transformed(
            source,
            instructions_root / source.name,
            "claude-code",
            preserve_shared_git_hooks=source.name == "workspace.instructions.md",
        )
    render_claude_policy_rules(support_root)
    write_text(
        instructions_root / "workspace.md",
        transform_agent_text(
            (REPO_ROOT / "shared" / "policies" / "workspace.instructions.md").read_text(
                encoding="utf-8"
            ),
            "claude-code",
            preserve_shared_git_hooks=True,
        ),
    )

    copy_skills(REPO_ROOT / "shared" / "skills", support_root / "skills", "claude-code")
    copy_tree_transformed(
        REPO_ROOT / "shared" / "third_party",
        support_root / "third_party",
        "claude-code",
    )
    copy_tree_transformed(
        REPO_ROOT / "shared" / "review-profiles",
        support_root / "review-profiles",
        "claude-code",
    )
    copy_tree(
        REPO_ROOT / "shared" / "hooks" / "scripts", support_root / "hooks" / "scripts"
    )
    restore_script = support_root / "hooks" / "scripts" / "restore-root-adapters.sh"
    write_text(
        restore_script,
        render_restore_script(restore_script.read_text(encoding="utf-8")),
    )
    # Every hook script must be executable: the runtime wrapper execs them, and
    # validate_targets.py invokes them by path. The shared sources are tracked
    # 0644 (git core.fileMode aside), so make them +x here rather than relying on
    # the checked-out mode.
    # Not just *.sh: protect-files.py is a required hook script too, and the
    # glob silently skipped it, so a freshly generated tree failed validation.
    for script in sorted((support_root / "hooks" / "scripts").iterdir()):
        if script.is_file():
            ensure_executable(script)
    copy_tree(
        REPO_ROOT / "shared" / "hooks" / "git-hooks",
        support_root / "hooks" / "git-hooks",
    )
    # git invokes these directly by exact filename (commit-msg, not *.sh), so
    # they need the same executable-bit treatment as hooks/scripts/*.sh above.
    for script in sorted((support_root / "hooks" / "git-hooks").glob("*")):
        ensure_executable(script)
    copy_tree(REPO_ROOT / "shared" / "prompts", support_root / "prompts")
    render_claude_agents(target_root)


def render_devcontainer(target_root: Path) -> None:
    copy_tree(REPO_ROOT / "shared" / "devcontainer", target_root / ".devcontainer")
    # A second rendered copy of the two state-sync scripts, reachable BEFORE
    # .claude/ exists at all: .claude/ is gitignored in consumers, so a fresh
    # clone has none of it until post-start.sh's own bootstrap run of these
    # scripts creates it (see the REPO_ROOT-resolution comment at the top of
    # state-sync.sh). Both copies come from the same shared/ source and are
    # regenerated together, so they cannot drift.
    for name in ("state-sync.sh", "restore-root-adapters.sh"):
        source = REPO_ROOT / "shared" / "hooks" / "scripts" / name
        destination = target_root / ".devcontainer" / name
        copy_file(source, destination)
        if name == "restore-root-adapters.sh":
            write_text(
                destination,
                render_restore_script(destination.read_text(encoding="utf-8")),
            )
        ensure_executable(destination)


def reset_target(output_root: Path, target: str) -> Path:
    target_root = output_root / target
    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True)
    return target_root


def resolve_agent_targets(
    metadata: dict[str, Any], metadata_path: Path
) -> tuple[str, ...]:
    """Resolve one agent's declared targets, defaulting omitted metadata to all."""
    if "targets" not in metadata:
        return SUPPORTED_AGENT_TARGETS
    declared_targets = metadata["targets"]
    if not isinstance(declared_targets, list):
        raise ValueError(f"{metadata_path}: targets must be an array")
    if not declared_targets:
        raise ValueError(f"{metadata_path}: targets must not be empty")
    if any(not isinstance(target, str) for target in declared_targets):
        raise ValueError(f"{metadata_path}: targets must contain only strings")
    if len(set(declared_targets)) != len(declared_targets):
        raise ValueError(f"{metadata_path}: targets must not contain duplicates")
    unknown_targets = sorted(set(declared_targets) - set(SUPPORTED_AGENT_TARGETS))
    if unknown_targets:
        raise ValueError(
            f"{metadata_path}: targets contains unsupported target IDs: {unknown_targets}"
        )
    return tuple(declared_targets)


def require_metadata_string(
    metadata: dict[str, Any], metadata_path: Path, field: str
) -> str:
    """Return one required non-empty metadata string or raise contextually."""
    return require_nonempty_string(metadata.get(field), metadata_path, field)


def validate_metadata_string_list(
    value: object,
    metadata_path: Path,
    field: str,
    allowed_values: set[str] | None = None,
) -> list[str]:
    """Validate a duplicate-free metadata list of non-empty strings."""
    if not isinstance(value, list):
        raise ValueError(f"{metadata_path}: {field} must be an array")
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{metadata_path}: {field} must contain non-empty strings")
    if len(set(value)) != len(value):
        raise ValueError(f"{metadata_path}: {field} must not contain duplicates")
    if allowed_values is not None:
        unknown_values = sorted(set(value) - allowed_values)
        if unknown_values:
            raise ValueError(
                f"{metadata_path}: {field} contains unsupported values: {unknown_values}"
            )
    return value


def require_nonempty_string(value: object, metadata_path: Path, field: str) -> str:
    """Return a required non-empty string or raise contextually."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{metadata_path}: {field} must be a non-empty string")
    return value


def validate_model_intent_object(
    value: object,
    metadata_path: Path,
    field: str,
    required_fields: tuple[str, ...],
    allowed_fields: tuple[str, ...],
) -> dict[str, Any]:
    """Validate one target's object-shaped model intent."""
    if not isinstance(value, dict):
        raise ValueError(f"{metadata_path}: {field} must be an object")
    unknown_fields = sorted(set(value) - set(allowed_fields))
    if unknown_fields:
        raise ValueError(
            f"{metadata_path}: {field} has unsupported fields: {unknown_fields}"
        )
    for required_field in allowed_fields:
        if required_field == "escalate_to" and required_field not in required_fields:
            continue
        if required_field not in value and required_field not in required_fields:
            continue
        require_nonempty_string(
            value.get(required_field), metadata_path, f"{field}.{required_field}"
        )
    return value


def validate_target_model_intent(
    target: str, value: object, metadata_path: Path
) -> None:
    """Validate the required shape for one eligible target's model intent."""
    field = f"model_intent.{target}"
    if target == "github-copilot":
        require_nonempty_string(value, metadata_path, field)
        return
    if target == "claude-code":
        validate_model_intent_object(
            value, metadata_path, field, ("model",), ("model", "effort")
        )
        return
    if target == "google-antigravity":
        antigravity_intent = validate_model_intent_object(
            value, metadata_path, field, ("model",), ("model", "escalate_to")
        )
        model = antigravity_intent["model"]
        if model not in {"inherit", "flash", "pro"}:
            raise ValueError(
                f"{metadata_path}: {field}.model must be one of ['flash', 'inherit', 'pro']"
            )
        if "escalate_to" in antigravity_intent:
            escalate_to = require_nonempty_string(
                antigravity_intent["escalate_to"],
                metadata_path,
                f"{field}.escalate_to",
            )
            if not AGENT_ID_PATTERN.fullmatch(escalate_to):
                raise ValueError(
                    f"{metadata_path}: {field}.escalate_to must be a stable agent ID"
                )
        return
    codex_intent = validate_model_intent_object(
        value,
        metadata_path,
        field,
        ("model", "effort"),
        ("model", "effort", "escalate_to"),
    )
    if "escalate_to" in codex_intent:
        escalate_to = require_nonempty_string(
            codex_intent["escalate_to"], metadata_path, f"{field}.escalate_to"
        )
        if not AGENT_ID_PATTERN.fullmatch(escalate_to):
            raise ValueError(
                f"{metadata_path}: {field}.escalate_to must be a stable agent ID"
            )


def validate_agent_metadata(
    metadata: dict[str, Any], metadata_path: Path
) -> dict[str, Any]:
    """Validate and normalize canonical agent metadata before rendering."""
    unknown_fields = sorted(set(metadata) - AGENT_METADATA_FIELDS)
    if unknown_fields:
        raise ValueError(
            f"{metadata_path}: metadata has unsupported fields: {unknown_fields}"
        )
    agent_id = require_metadata_string(metadata, metadata_path, "id")
    if not AGENT_ID_PATTERN.fullmatch(agent_id):
        raise ValueError(
            f"{metadata_path}: id must be a stable lowercase identifier using letters, digits, underscores, and hyphens"
        )
    require_metadata_string(metadata, metadata_path, "description")
    require_metadata_string(metadata, metadata_path, "role_type")
    visibility = require_metadata_string(metadata, metadata_path, "visibility")
    if visibility not in AGENT_VISIBILITIES:
        raise ValueError(
            f"{metadata_path}: visibility must be one of {sorted(AGENT_VISIBILITIES)}"
        )
    validate_metadata_string_list(
        metadata.get("capabilities"), metadata_path, "capabilities", AGENT_CAPABILITIES
    )
    delegates = (
        validate_metadata_string_list(metadata["delegates"], metadata_path, "delegates")
        if "delegates" in metadata
        else []
    )
    invalid_delegate_ids = [
        delegate for delegate in delegates if not AGENT_ID_PATTERN.fullmatch(delegate)
    ]
    if invalid_delegate_ids:
        raise ValueError(
            f"{metadata_path}: delegates must contain stable agent IDs: {invalid_delegate_ids}"
        )

    targets = resolve_agent_targets(metadata, metadata_path)
    prompt_base = metadata.get("prompt_base")
    if prompt_base is not None:
        prompt_base = require_nonempty_string(prompt_base, metadata_path, "prompt_base")
        if not AGENT_ID_PATTERN.fullmatch(prompt_base):
            raise ValueError(f"{metadata_path}: prompt_base must be a stable agent ID")
        if "targets" not in metadata or len(targets) != 1:
            raise ValueError(
                f"{metadata_path}: prompt_base is limited to explicitly single-provider agents"
            )
    model_intent = metadata.get("model_intent")
    if not isinstance(model_intent, dict):
        raise ValueError(f"{metadata_path}: model_intent must be an object")
    missing_intents = [target for target in targets if target not in model_intent]
    if missing_intents:
        raise ValueError(
            f"{metadata_path}: model_intent is missing eligible targets: {missing_intents}"
        )
    ineligible_intents = sorted(set(model_intent) - set(targets))
    if ineligible_intents:
        raise ValueError(
            f"{metadata_path}: model_intent declares ineligible targets: {ineligible_intents}"
        )
    for target in targets:
        validate_target_model_intent(target, model_intent[target], metadata_path)
    return {**metadata, "delegates": delegates, "targets": targets}


def provider_supplement_path(agent_dir: Path, target: str) -> Path | None:
    """Return the target-specific prompt supplement path when one is supported."""
    filename = PROVIDER_SUPPLEMENT_FILENAMES.get(target)
    return agent_dir / filename if filename else None


def validate_prompt_composition(
    agents: list[tuple[dict[str, Any], Path]], agents_root: Path
) -> None:
    """Validate deliberately one-level, single-provider prompt composition."""
    agents_by_id = {agent["id"]: (agent, agent_dir) for agent, agent_dir in agents}
    prompt_bases = {
        agent["id"]: agent["prompt_base"]
        for agent, _agent_dir in agents
        if "prompt_base" in agent
    }

    def visit(agent_id: str, visiting: list[str], visited: set[str]) -> None:
        if agent_id in visited or agent_id not in prompt_bases:
            return
        if agent_id in visiting:
            cycle = " -> ".join([*visiting, agent_id])
            raise ValueError(f"{agents_root}: prompt_base cycle detected: {cycle}")
        visit(prompt_bases[agent_id], [*visiting, agent_id], visited)
        visited.add(agent_id)

    visited: set[str] = set()
    for agent_id, base_id in prompt_bases.items():
        if agent_id == base_id:
            raise ValueError(
                f"{agents_root / agent_id / 'agent.yaml'}: prompt_base must not self-reference"
            )
        if base_id not in agents_by_id:
            raise ValueError(
                f"{agents_root / agent_id / 'agent.yaml'}: prompt_base references missing agent '{base_id}'"
            )
        visit(agent_id, [], visited)
        if "prompt_base" in agents_by_id[base_id][0]:
            raise ValueError(
                f"{agents_root / agent_id / 'agent.yaml'}: prompt_base must not create multi-level inheritance"
            )

    for agent, agent_dir in agents:
        prompt_path = agent_dir / "prompt.md"
        prompt_base = agent.get("prompt_base")
        if prompt_base is None:
            if not prompt_path.is_file():
                raise ValueError(f"{agent_dir}: missing canonical prompt.md")
            for target, filename in PROVIDER_SUPPLEMENT_FILENAMES.items():
                supplement_path = agent_dir / filename
                if not supplement_path.exists():
                    continue
                if target not in agent["targets"]:
                    provider_label = "Codex" if target == "openai-codex" else target
                    raise ValueError(
                        f"{agent_dir}: {filename} requires {provider_label} eligibility"
                    )
                supplement = supplement_path.read_text(encoding="utf-8")
                if not supplement.strip():
                    raise ValueError(f"{agent_dir}: {filename} must not be empty")
                if "role supplement:" in supplement:
                    raise ValueError(
                        f"{agent_dir}: {filename} must not contain a role-supplement delimiter"
                    )
            continue

        base_dir = agents_by_id[prompt_base][1]
        base_prompt_path = base_dir / "prompt.md"
        if not base_prompt_path.is_file():
            raise ValueError(
                f"{agent_dir / 'agent.yaml'}: prompt_base '{prompt_base}' is missing prompt.md"
            )
        if prompt_path.exists():
            raise ValueError(
                f"{agent_dir}: derived agents must not copy a canonical prompt.md"
            )
        target = agent["targets"][0]
        derived_supplement_path = provider_supplement_path(agent_dir, target)
        if derived_supplement_path is None or not derived_supplement_path.is_file():
            provider_label = "Codex" if target == "openai-codex" else target
            raise ValueError(
                f"{agent_dir}: derived {provider_label} agents require prompt.{target}.md"
            )
        supplement = derived_supplement_path.read_text(encoding="utf-8")
        if not supplement.strip():
            raise ValueError(
                f"{agent_dir}: {derived_supplement_path.name} must not be empty"
            )
        transformed_base = normalize_prompt_whitespace(
            transform_agent_text(base_prompt_path.read_text(encoding="utf-8"), target)
        )
        transformed_supplement = normalize_prompt_whitespace(
            transform_agent_text(supplement, target)
        )
        if transformed_base in transformed_supplement:
            raise ValueError(
                f"{agent_dir}: prompt.openai-codex.md must not copy its full base prompt"
            )
        if "role supplement:" in supplement:
            raise ValueError(
                f"{agent_dir}: {derived_supplement_path.name} must not contain a role-supplement delimiter"
            )


def normalize_prompt_whitespace(text: str) -> str:
    """Normalize whitespace only when detecting a copied complete prompt base."""
    return " ".join(text.split())


def validate_escalation_targets(
    agents: list[tuple[dict[str, Any], Path]], agents_root: Path, provider: str
) -> None:
    """Validate named, acyclic provider-specific escalation targets."""
    agents_by_id = {agent["id"]: agent for agent, _agent_dir in agents}
    edges: dict[str, str] = {}
    for agent, agent_dir in agents:
        intent = agent["model_intent"].get(provider)
        if not isinstance(intent, dict) or "escalate_to" not in intent:
            continue
        target_id = intent["escalate_to"]
        if target_id not in agents_by_id:
            raise ValueError(
                f"{agent_dir / 'agent.yaml'}: escalate_to references missing agent '{target_id}'"
            )
        if target_id == agent["id"]:
            raise ValueError(
                f"{agent_dir / 'agent.yaml'}: escalate_to must not self-reference"
            )
        if provider not in agents_by_id[target_id]["targets"]:
            raise ValueError(
                f"{agent_dir / 'agent.yaml'}: escalate_to target '{target_id}' is not {provider}-eligible"
            )
        edges[agent["id"]] = target_id

    for agent_id in edges:
        seen: set[str] = set()
        current = agent_id
        while current in edges:
            if current in seen:
                provider_label = "Codex" if provider == "openai-codex" else provider
                raise ValueError(
                    f"{agents_root}: {provider_label} escalation cycle detected at '{current}'"
                )
            seen.add(current)
            current = edges[current]


def load_shared_agents(
    agents_root: Path | None = None,
) -> list[tuple[dict[str, Any], Path]]:
    """Load all shared agents through the canonical metadata contract."""
    agents_root = agents_root or REPO_ROOT / "shared" / "agents"
    agents: list[tuple[dict[str, Any], Path]] = []
    for metadata_path in sorted(agents_root.glob("*/agent.yaml")):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"{metadata_path}: invalid JSON metadata") from error
        if not isinstance(metadata, dict):
            raise ValueError(f"{metadata_path}: metadata must be an object")
        agents.append(
            (
                validate_agent_metadata(metadata, metadata_path),
                metadata_path.parent,
            )
        )
    agent_ids = [agent["id"] for agent, _agent_dir in agents]
    if len(set(agent_ids)) != len(agent_ids):
        raise ValueError(f"{agents_root}: id must be unique across shared agents")
    validate_prompt_composition(agents, agents_root)
    for provider in ("openai-codex", "google-antigravity"):
        validate_escalation_targets(agents, agents_root, provider)
    return agents


def shared_agents(target: str | None = None) -> list[tuple[dict[str, Any], Path]]:
    """Return canonical agents, optionally limited to one eligible target."""
    agents = load_shared_agents()
    if target is None:
        return agents
    if target not in SUPPORTED_AGENT_TARGETS:
        raise ValueError(f"unsupported agent target: {target}")
    return [(agent, path) for agent, path in agents if target in agent["targets"]]


def transform_agent_text(
    text: str, target: str, *, preserve_shared_git_hooks: bool = False
) -> str:
    # Model names live only in agent.yaml model_intent (consumed directly when
    # rendering the GitHub adapter), never in prompt bodies or descriptions, so
    # there are no model-name substitutions to apply here — only path rewrites.
    return transform_target_paths(
        text, target, preserve_shared_git_hooks=preserve_shared_git_hooks
    )


def transform_target_paths(
    text: str, target: str, *, preserve_shared_git_hooks: bool = False
) -> str:
    shared_hook_marker = "__BOOTSTRAP_SHARED_GITHUB_HOOKS__"
    transformed = (
        text.replace(".github/hooks", shared_hook_marker)
        if preserve_shared_git_hooks
        else text
    )
    for old, new in TARGET_PATH_REPLACEMENTS.get(target, ()):
        transformed = transformed.replace(old, new)
    return transformed.replace(shared_hook_marker, ".github/hooks")


def render_claude_tools(capabilities: list[str]) -> str:
    tools: list[str] = []
    for capability in capabilities:
        for tool_name in CLAUDE_TOOL_MAP.get(capability, []):
            if tool_name not in tools:
                tools.append(tool_name)
    return ", ".join(tools)


def render_copilot_tools(capabilities: list[str]) -> list[str]:
    tools: list[str] = []
    for capability in capabilities:
        for tool_name in COPILOT_TOOL_MAP.get(capability, []):
            if tool_name not in tools:
                tools.append(tool_name)
    return tools


def render_antigravity_tools(capabilities: list[str]) -> list[str]:
    """Render only documented Antigravity tool names for abstract capabilities."""
    tools: list[str] = []
    for capability in capabilities:
        for tool_name in ANTIGRAVITY_TOOL_MAP.get(capability, []):
            if tool_name not in tools:
                tools.append(tool_name)
    return tools


def toml_string(value: str) -> str:
    return json.dumps(value)


def codex_sandbox_mode(capabilities: list[str]) -> str | None:
    if not capabilities:
        return None
    if "edit" not in capabilities and "execute" not in capabilities:
        return "read-only"
    return None


def codex_agent_metadata_header(agent: dict[str, Any]) -> str:
    """Return the stable generated metadata header for one Codex agent."""
    capabilities = agent.get("capabilities", [])
    return (
        "Generated Codex custom-agent instructions.\n"
        f"Role type: {agent.get('role_type', 'unspecified')}; "
        f"visibility: {agent.get('visibility', 'public')}; "
        f"capability intents: {', '.join(capabilities) or 'target default'}."
    )


def provider_agent_prompt_body(agent: dict[str, Any], target: str) -> str:
    """Return one target-transformed, self-contained canonical agent prompt."""
    agent_dir = REPO_ROOT / "shared" / "agents" / agent["id"]
    prompt_base = agent.get("prompt_base")
    prompt_path = (
        REPO_ROOT / "shared" / "agents" / prompt_base / "prompt.md"
        if isinstance(prompt_base, str)
        else agent_dir / "prompt.md"
    )
    base_prompt = transform_agent_text(
        prompt_path.read_text(encoding="utf-8"), target
    ).strip()
    supplement_path = provider_supplement_path(agent_dir, target)
    if supplement_path is None or not supplement_path.exists():
        return base_prompt
    supplement = transform_agent_text(
        supplement_path.read_text(encoding="utf-8"), target
    ).strip()
    delimiter_template = (
        CODEX_ROLE_SUPPLEMENT_DELIMITER
        if target == "openai-codex"
        else ANTIGRAVITY_ROLE_SUPPLEMENT_DELIMITER
    )
    delimiter = delimiter_template.format(agent_id=agent["id"])
    return f"{base_prompt}\n\n{delimiter}\n\n{supplement}"


def render_antigravity_default_agent_contract() -> str:
    """Render the native default-agent bridge from canonical role sources."""
    orchestrator = next(
        agent
        for agent, _agent_dir in shared_agents("google-antigravity")
        if agent["id"] == "orchestrator"
    )
    rendered = provider_agent_prompt_body(orchestrator, "google-antigravity")
    delimiter = ANTIGRAVITY_ROLE_SUPPLEMENT_DELIMITER.format(agent_id="orchestrator")
    _base, separator, supplement = rendered.partition(f"\n\n{delimiter}\n\n")
    if not separator:
        raise ValueError("Antigravity orchestrator routing supplement is required")
    return (
        "## Google Antigravity Default-Agent Contract\n\n"
        "Google Antigravity's native default agent is the main-thread orchestrator. "
        "Before complex work, read and follow the canonical workflow in "
        "`.claude/agents/orchestrator.md`; delegate only to the eligible custom "
        "specialists in `.agents/agents/`.\n\n"
        f"{delimiter}\n\n{supplement}"
    )


def codex_agent_prompt_body(agent: dict[str, Any]) -> str:
    """Return the exact target-transformed, self-contained Codex prompt body."""
    return provider_agent_prompt_body(agent, "openai-codex")


def shared_mcp_servers() -> dict[str, Any]:
    data = load_json(REPO_ROOT / "shared" / "mcp" / "servers.json")
    return data["servers"]


def shared_skill_names() -> list[str]:
    return sorted(
        path.parent.name
        for path in (REPO_ROOT / "shared" / "skills").glob("*/SKILL.md")
    )


def render_vscode_mcp_json(path: Path) -> None:
    write_json(path, {"servers": shared_mcp_servers()})


def render_vscode_tasks_json(path: Path) -> None:
    src = REPO_ROOT / "shared" / "vscode" / "tasks.json"
    write_json(path, json.loads(src.read_text()))


def render_claude_mcp_json(path: Path) -> None:
    write_json(path, {"mcpServers": shared_mcp_servers()})


def render_codex_config(path: Path) -> None:
    lines = [
        "# Generated from shared/mcp/servers.json.",
        "# Skills are sourced from the shared .claude basis; project trust is required.",
        "# Semble and Context Mode hooks are optional; missing binaries should warn, not block.",
        "# Hooks are enabled by default in current Codex, so no flat features block is emitted.",
        "# Preserve the MultiAgent V2 routing shim until trusted native probes prove removal.",
        "# See docs/2026-08-08-codex-routing-compatibility.md in the bootstrap source.",
        "# Codex resolves a non-absolute skill `path` relative to config.toml; the generated",
        "# bundle cannot know the consumer's absolute path, so each skill points at",
        "# ../.claude/skills/<name>/SKILL.md relative to this config. This relative form is",
        "# the tested contract: validate_targets.py asserts it structurally in two places -",
        '# validate_mcp_and_hooks ("../.claude/skills/" in config) and validate_skills_and_paths',
        "# (the enabled-skill path set must equal the shared/skills SKILL.md set exactly).",
        "# Runtime resolution follows Codex's documented relative-path handling (docs accessed",
        "# 2026-07-03); see architecture-review-2026-07.md appendix B for the epistemic status.",
        "#",
        "# The interactive session model and effort are intentionally unpinned so users can",
        "# choose them manually. Custom agents set their own values from",
        "# model_intent.openai-codex according to task role.",
        "",
        "[agents]",
        "max_concurrent_threads_per_session = 6",
        "max_depth = 1",
        "",
        "[features.multi_agent_v2]",
        "hide_spawn_agent_metadata = false",
        'tool_namespace = "agents"',
        "",
    ]
    for name, server in shared_mcp_servers().items():
        lines.append(f"[mcp_servers.{name}]")
        lines.append(f'command = "{server["command"]}"')
        if "args" in server:
            args = ", ".join(json.dumps(arg) for arg in server["args"])
            lines.append(f"args = [{args}]")
        lines.append("")
    for skill_name in shared_skill_names():
        lines.append("[[skills.config]]")
        lines.append(
            f"path = {toml_string(f'../.claude/skills/{skill_name}/SKILL.md')}"
        )
        lines.append("enabled = true")
        lines.append("")
    write_text(path, "\n".join(lines))


def _claude_hook_cmd(script: str, *args: str) -> str:
    root_expr = (
        "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
    )
    parts = [
        f'REPO_ROOT="{root_expr}"',
        '"$REPO_ROOT/.claude/hooks/scripts/run-hook.sh"',
        script,
        *args,
    ]
    return "; ".join(parts[:2]) + " " + " ".join(parts[2:])


def render_claude_settings(path: Path) -> None:
    def cmd(script: str, *args: str, timeout: int = 10) -> dict[str, Any]:
        return {
            "type": "command",
            "command": _claude_hook_cmd(script, *args),
            "timeout": timeout,
        }

    def cmd_stop(script: str, *args: str) -> dict[str, Any]:
        return {
            "type": "command",
            "command": _claude_hook_cmd(script, *args),
            "timeout": 180,
        }

    settings: dict[str, Any] = {
        "permissions": {
            "deny": [
                "Read(./.env)",
                "Read(./.env.*)",
                "Read(./secrets/**)",
                "Read(./config/credentials.json)",
            ]
        },
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        cmd("state-sync.sh", "pull", timeout=60),
                        cmd("session-log.sh", "claude-code"),
                        cmd("session-start-state.sh", "claude-code"),
                        cmd("context-mode-dispatch.sh", "claude-code", "sessionstart"),
                    ]
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "Edit|MultiEdit|Write",
                    "hooks": [
                        cmd("protect-files.sh", "claude-code"),
                    ],
                },
                {
                    "matcher": "Bash",
                    "hooks": [cmd("pretool-bash-guard.sh", "claude-code")],
                },
                {
                    "matcher": "*",
                    "hooks": [
                        cmd("context-mode-dispatch.sh", "claude-code", "pretooluse")
                    ],
                },
            ],
            "PostToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        cmd("record-branch-state.sh", "claude-code"),
                        cmd("record-commit-closeout.sh", "claude-code"),
                        cmd("context-mode-dispatch.sh", "claude-code", "posttooluse"),
                    ],
                }
            ],
            "PreCompact": [
                {
                    "hooks": [
                        cmd("context-mode-dispatch.sh", "claude-code", "precompact")
                    ]
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        cmd_stop("claude-stop.sh"),
                    ]
                }
            ],
            "UserPromptSubmit": [{"hooks": [cmd("state-sync.sh", "push", timeout=60)]}],
            "StopFailure": [{"hooks": [cmd("state-sync.sh", "checkpoint")]}],
            "SessionEnd": [{"hooks": [cmd("state-sync.sh", "push", timeout=60)]}],
        },
    }
    write_json(path, settings)


def render_codex_hooks(path: Path) -> None:
    def command(script: str, *args: str) -> str:
        root_expr = "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
        parts = [
            f'REPO_ROOT="{root_expr}"',
            '"$REPO_ROOT/.claude/hooks/scripts/run-hook.sh"',
            script,
            *args,
        ]
        return "; ".join(parts[:2]) + " " + " ".join(parts[2:])

    def cmd(script: str, *args: str, timeout: int = 10) -> dict[str, Any]:
        return {
            "type": "command",
            "command": command(script, *args),
            "timeout": timeout,
        }

    hooks: dict[str, Any] = {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup|resume|clear",
                    "hooks": [
                        cmd("state-sync.sh", "pull", timeout=60),
                        cmd("session-log.sh", "openai-codex"),
                        cmd("session-start-state.sh", "openai-codex"),
                        cmd("context-mode-dispatch.sh", "openai-codex", "sessionstart"),
                    ],
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "Edit|Write",
                    "hooks": [
                        cmd("protect-files.sh", "openai-codex"),
                    ],
                },
                {
                    "matcher": "Bash",
                    "hooks": [cmd("pretool-bash-guard.sh", "openai-codex")],
                },
                {
                    "matcher": "*",
                    "hooks": [
                        cmd("context-mode-dispatch.sh", "openai-codex", "pretooluse")
                    ],
                },
            ],
            "PostToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        cmd("record-branch-state.sh", "openai-codex"),
                        cmd("record-commit-closeout.sh", "openai-codex"),
                        cmd("context-mode-dispatch.sh", "openai-codex", "posttooluse"),
                    ],
                }
            ],
            "PreCompact": [
                {
                    "hooks": [
                        cmd("context-mode-dispatch.sh", "openai-codex", "precompact")
                    ]
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        cmd("codex-stop.sh", timeout=180),
                    ]
                }
            ],
            "UserPromptSubmit": [{"hooks": [cmd("state-sync.sh", "push", timeout=60)]}],
            "SessionEnd": [{"hooks": [cmd("state-sync.sh", "checkpoint", timeout=3)]}],
        },
    }
    write_json(path, hooks)


def antigravity_hook_command() -> str:
    """Return the repo-local command for the Antigravity pre-tool bridge."""
    root_expr = "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
    return (
        f'REPO_ROOT="{root_expr}"; '
        'exec "$REPO_ROOT/.claude/hooks/scripts/antigravity-pretool.py"'
    )


def render_antigravity_hooks(path: Path) -> None:
    """Render the documented Antigravity pre-execution safety boundary.

    Lifecycle hooks stay deliberately absent until native cadence evidence can
    show that they cannot duplicate state publication or create Stop loops.
    """
    command = antigravity_hook_command()
    write_json(
        path,
        {
            "bootstrap-safety": {
                "PreToolUse": [
                    {
                        # Antigravity documents '*' as the PreToolUse regex for
                        # every tool. The bridge explicitly allows only known
                        # non-mutating tools and denies unknown tool shapes.
                        "matcher": "*",
                        "hooks": [
                            {"type": "command", "command": command, "timeout": 10}
                        ],
                    }
                ]
            }
        },
    )


def render_root_guidance(target: str) -> str:
    if target == "multi-agent":
        title = "AI Coding Agent Project Guidance"
        control_plane_paths = (
            "root guidance, `.claude/hooks/`, `.github/hooks/`, `.codex/`, `.agents/`, "
            "`.mcp.json`, and `.devcontainer/`"
        )
        runtime_note = (
            "Codex uses `.codex/config.toml`, `.codex/hooks.json`, and `.codex/agents/*.toml` "
            "as native adapters. Google Antigravity uses `.agents/agents/`, `.agents/skills/`, "
            "and `.agents/mcp_config.json`. Keep provider-specific runtime details in those "
            "directories and preserve the canonical `.claude/` basis."
        )
    elif target == "claude-code":
        title = "Claude Code Project Guidance"
        control_plane_paths = (
            "root guidance, `.claude/hooks/`, `.github/hooks/`, `.claude/settings.json`, "
            "`.mcp.json`, and `.devcontainer/`"
        )
        runtime_note = (
            "Claude Code uses `.claude/settings.json`, `.claude/agents/`, and "
            "`.claude/skills/` natively. Keep the configured hooks enabled."
        )
    elif target == "openai-codex":
        title = "OpenAI Codex Project Guidance"
        control_plane_paths = (
            "root guidance, `.claude/hooks/`, `.github/hooks/`, `.codex/`, "
            "`.mcp.json`, and `.devcontainer/`"
        )
        runtime_note = (
            "Codex uses `.codex/config.toml`, `.codex/hooks.json`, and "
            "`.codex/agents/*.toml` as native adapters to the canonical `.claude/` basis. "
            "Trust the project before expecting them to load. Preserve `max_depth` and "
            "`[features.multi_agent_v2]` metadata exposure until native routing smoke tests "
            "prove they are unnecessary."
        )
    else:
        raise ValueError(f"unsupported root-guidance target: {target}")

    guidance = f"""# {title}

This is the repository entrypoint for Python AI engineering guidance. `.claude/` is the canonical runtime guidance; do not hand-edit generated target adapters.

**Project:** [TODO: project name and one-liner description]
**Python:** 3.12+ | **Package Manager:** uv
**Stack:** Python 3.12+ with uv; adapt framework guidance to the target repository.

## Source Of Truth

- Installed canonical guidance, skills, agents, hooks, templates, and mutable AI state live under `.claude/`.
- Put repository-specific facts in `.claude/instructions/project-context.instructions.md`; preserve consumer-owned memory, plans, explorations, session logs, and quality reports during refreshes.
- Follow `.claude/instructions/agent-reporting.instructions.md` for audience-aware human-facing communication and internal handoffs.
- Reporting rules are output requirements. For every user-facing message, use clear, direct language with short sentences and common precise words. Avoid unnecessary jargon, buzzwords, and idioms. Define uncommon terms when needed, retain precise technical terms, and do not use `caveman full` with the user. Self-check user-facing prose before sending. Compact internal agent handoffs may still use `caveman full`. See the reporting policy for details.
- Use direct reads for known files, `rg` for exact literals, and Semble for semantic repository discovery. Context Mode exposes exactly four guarded MCP tools (`ctx_index`, `ctx_search`, `ctx_stats`, `ctx_doctor`) alongside its lifecycle hooks; these are normal routes alongside direct reads, `rg`, and Semble, not replacements for them. A guarded bounded project index is optional for broader discovery, never repository truth, and missing optional helpers are warnings, not hard failures.

## Task Lanes

- Read the authoritative Task Lanes decision table in `.claude/instructions/workflow.instructions.md` before acting; it is the sole normative classifier.
- Read-only/reporting stays with the main agent and produces evidence only. Diagnose stays read-only until a fix is requested.
- Only an explicit, one-file, low-risk edit with no high-risk impact and no requested commit or PR is lightweight; it stays with the main agent and needs focused verification, not lifecycle artifacts.
- Standard implementation and control-plane/high-risk work use `orchestrator -> [planner when needed] -> coder -> verify phase -> reviewer -> closeout`; an approved implementation-ready plan normally skips planner. All commit/PR work is standard or higher.
- Control-plane/high-risk includes control-plane, security, dependency/lockfile, migration, multi-file, user-data, generators, and scripts. It always uses a full plan and the required high-risk review profiles.
- Audited typo commit bypasses are recovery exceptions, never lane classification.

## Required Lifecycle

`{ROOT_GUIDANCE_WORKFLOW}`

- Before non-trivial work, read `.claude/MEMORY.md`, save the approved plan under `.claude/plans/`, and create one `<plan_name>_implementation` branch from a clean `dev` branch.
- Load `.claude/skills/ponytail/SKILL.md` in `full` mode before every coding task. Search and reuse before adding code.
- Run `verify phase`, then profile-driven review until clean. CLOSEOUT updates required documentation, persists findings, records learning and the completed session log, then runs `verify closeout`.
- Commit each completed small plan only after `verify phase` reports PASS, critical findings are zero, required Ponytail review evidence is present, reusable lessons are recorded in `.claude/MEMORY.md`, and the closeout session log is complete. Ponytail findings follow the ordinary severity gates.
- Do not open a PR, push, or merge unless the workflow permits it and the user requested the external action. The user owns merge decisions.

## Exact Commands

```bash
uv sync
uv run pytest tests/ -q --tb=short
uv run mypy src/ --ignore-missing-imports --explicit-package-bases
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

Use `uv run` for project Python entrypoints and tooling; never substitute bare `python`, `pip`, `pytest`, `mypy`, or `ruff` in the normal workflow.

## Safety And Control Plane

- Keep hook guardrails enabled. Never hand-edit `.env*`, private keys, credentials, secret-bearing files, or `uv.lock`; never run destructive Git commands such as force-push, hard reset, or cleaning untracked files without explicit safe authorization.
- Control-plane files include {control_plane_paths}. They require a full plan and `code`, `architecture`, `security`, `tests`, and `ponytail` review profiles.
- Keep `.claude/` as the canonical runtime basis. Treat generated adapters as managed runtime files; customize only project context and consumer-owned state.

## Map

- Policies: `.claude/instructions/workspace.instructions.md`, `workflow.instructions.md`, `quality-and-testing.instructions.md`, and `tool-routing.instructions.md`.
- Skills: `.claude/skills/<name>/SKILL.md`; apply Ponytail to all coding and use task-matched skills when relevant.
- Agents: canonical bodies in `.claude/agents/`; the orchestrator coordinates complex work and specialists own planning, implementation, review, and documentation. Deterministic verification and closeout run through canonical scripts.
- Hooks: target-native configuration dispatches to `.claude/hooks/scripts/`; runtime errors are recorded under `.claude/session_logs/`.

## Target Runtime

{runtime_note}
"""
    if target == "multi-agent":
        return f"{guidance}\n{render_antigravity_default_agent_contract()}\n"
    return guidance


def split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---\n"):
        return None, text
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        return None, text
    return parts[1].strip(), parts[2].lstrip()


def parse_policy(source: Path) -> Policy:
    """Parse the deliberately small, target-neutral policy frontmatter schema."""
    frontmatter, body = split_frontmatter(source.read_text(encoding="utf-8"))
    if frontmatter is None:
        raise ValueError(f"policy frontmatter is required: {source}")

    lines = frontmatter.splitlines()
    fields: dict[str, str | tuple[str, ...]] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line:
            index += 1
            continue
        if line.startswith((" ", "\t")) or ":" not in line:
            raise ValueError(f"invalid policy frontmatter line in {source}: {line}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key not in {"description", POLICY_APPLICABILITY_KEY}:
            raise ValueError(f"unsupported policy frontmatter field in {source}: {key}")
        if key in fields:
            raise ValueError(f"duplicate policy frontmatter field in {source}: {key}")
        if key != POLICY_APPLICABILITY_KEY:
            fields[key] = value
            index += 1
            continue
        if value:
            fields[key] = value
            index += 1
            continue

        patterns: list[str] = []
        index += 1
        while index < len(lines) and lines[index].startswith("  - "):
            pattern = lines[index][4:].strip()
            if not pattern:
                raise ValueError(f"empty policy applicability pattern in {source}")
            patterns.append(pattern)
            index += 1
        if not patterns:
            raise ValueError(
                f"policy applicability needs patterns or 'always': {source}"
            )
        fields[key] = tuple(patterns)

    applicability = fields.get(POLICY_APPLICABILITY_KEY)
    if applicability is None:
        raise ValueError(f"policy applicability is required: {source}")
    if applicability == POLICY_ALWAYS:
        paths: tuple[str, ...] = ()
    elif isinstance(applicability, tuple):
        paths = applicability
    else:
        raise ValueError(
            f"policy applicability must be 'always' or a YAML list in {source}"
        )
    for path in paths:
        if path.startswith("/") or ".." in Path(path).parts or "," in path:
            raise ValueError(
                f"invalid relative policy applicability pattern in {source}: {path}"
            )
    return Policy(source=source, body=body, paths=paths)


def shared_policies() -> list[Policy]:
    """Return canonical policies parsed through the single scope schema."""
    return [
        parse_policy(source)
        for source in sorted(
            (REPO_ROOT / "shared" / "policies").glob("*.instructions.md")
        )
    ]


def canonical_agent_name(agent_id: str) -> str:
    # Agent names are identical across every target; there is no per-target
    # renaming (the earlier mapped_agent_name was an identity function).
    return agent_id


def canonical_agent_path(agent_id: str) -> str:
    return f".claude/agents/{canonical_agent_name(agent_id)}.md"


def render_copilot_instructions() -> str:
    return """# GitHub Copilot Workspace Adapter

This target is generated from `shared/`. Do not edit generated files manually.

`.claude/` is the canonical shared project space for all AI systems in this repo. Use it for skills, plans, explorations, session logs, quality reports, memory, templates, prompts, shared agent bodies, and hook scripts.

Native Copilot files under `.github/` are adapters:

- `.github/instructions/*.instructions.md` preserves Copilot discovery and points to `.claude/instructions/`.
- `.github/agents/*.agent.md` preserves Copilot agent metadata and points to `.claude/agents/`.
- `.github/hooks/hooks.json` invokes shared hook scripts in `.claude/hooks/scripts/`.

Before planning or implementation, load the relevant canonical instruction files from `.claude/instructions/`, especially `workflow.instructions.md`, `quality-and-testing.instructions.md`, and `tool-routing.instructions.md`. Before every coding action, load `.claude/skills/ponytail/SKILL.md` in `full` mode.

Preserve the pre-flight -> branch -> plan -> implement -> verify -> review -> document -> learn -> session-log -> commit workflow. A passing `verify phase` plus required documentation updates are mandatory before commit or PR closeout. Write all plans, session logs, exploration notes, memory updates, and quality reports under `.claude/`, not target-local `.github/` or `.codex/` state directories.
"""


def render_github_instruction_adapter(policy: Policy) -> str:
    """Render the Copilot discovery adapter from canonical policy scope."""
    adapter = (
        f"# {policy.title} Adapter\n\n"
        f"This Copilot instruction file is a native discovery adapter. "
        f"Read and follow the canonical shared instruction at `.claude/instructions/{policy.source.name}`.\n\n"
        "Critical shared-state rule: plans, explorations, session logs, memory, and quality reports "
        "belong under `.claude/` for every AI target.\n"
    )
    if policy.paths:
        return f"---\napplyTo: {json.dumps(','.join(policy.paths))}\n---\n\n{adapter}"
    return adapter


def render_claude_rule_adapter(policy: Policy) -> str:
    """Render a Claude-native, path-scoped pointer to a canonical policy."""
    if not policy.paths:
        raise ValueError(
            f"always-on policy has no Claude rule adapter: {policy.source}"
        )
    frontmatter = "\n".join(
        ["---", "paths:", *(f"  - {json.dumps(path)}" for path in policy.paths), "---"]
    )
    return (
        f"{frontmatter}\n\n"
        f"# {policy.title} Adapter\n\n"
        "This Claude rule is a native discovery adapter. Read and follow the canonical "
        f"shared instruction at `.claude/instructions/{policy.source.name}`.\n"
    )


def render_claude_policy_rules(support_root: Path) -> None:
    """Generate only conditional Claude rules; root guidance covers always-on policy."""
    for policy in shared_policies():
        if policy.paths:
            write_text(
                support_root / "rules" / policy.source.name,
                render_claude_rule_adapter(policy),
            )


def render_github_agent_adapter(
    agent: dict[str, Any], agent_dir: Path | None = None
) -> str:
    """Render a GitHub agent adapter or a self-contained scoped agent body."""
    frontmatter_lines = [
        "---",
        f"name: {agent['id']}",
        f"description: {json.dumps(agent['description'])}",
    ]
    github_model = agent.get("model_intent", {}).get("github-copilot")
    if github_model and github_model != "target-default":
        frontmatter_lines.append(f"model: {github_model}")
    tools = render_copilot_tools(agent.get("capabilities", []))
    if tools:
        frontmatter_lines.append("tools:")
        frontmatter_lines.extend(f"  - {tool}" for tool in tools)
    delegates = agent.get("delegates", [])
    if delegates:
        frontmatter_lines.append("agents:")
        frontmatter_lines.extend(f"  - {delegate}" for delegate in delegates)
    elif "delegate" in agent.get("capabilities", []):
        frontmatter_lines.append("agents: []")
    if agent.get("visibility") == "hidden":
        frontmatter_lines.append("user-invocable: false")
    if agent["id"] == "orchestrator":
        frontmatter_lines.append("disable-model-invocation: true")
    frontmatter_lines.append("---")
    if "claude-code" in agent.get("targets", SUPPORTED_AGENT_TARGETS):
        canonical_path = canonical_agent_path(agent["id"])
        body = (
            f"# {agent['id']} Copilot Adapter\n\n"
            "This file is the GitHub Copilot native adapter for the shared agent body.\n\n"
            f"Before doing the task, read `{canonical_path}` and follow that canonical role guidance. "
            "Use the Copilot model, tools, delegation, and visibility metadata in this file when it "
            "conflicts with Claude-specific frontmatter in the canonical file.\n\n"
            "Shared skills, memory, plans, explorations, session logs, quality reports, templates, "
            "prompts, and hook scripts live under `.claude/`.\n"
        )
    else:
        if agent_dir is None:
            raise ValueError(f"{agent['id']}: GitHub-only agent requires prompt source")
        prompt = transform_agent_text(
            (agent_dir / "prompt.md").read_text(encoding="utf-8"), "github-copilot"
        ).strip()
        body = (
            f"# {agent['id']} Copilot Agent\n\n"
            "This file is self-contained because this agent is not eligible for Claude Code.\n\n"
            f"{prompt}\n"
        )
    return "\n".join(frontmatter_lines) + "\n\n" + body


def render_claude_agents(target_root: Path) -> None:
    for agent, agent_dir in shared_agents("claude-code"):
        target_name = canonical_agent_name(agent["id"])
        body = (agent_dir / "prompt.md").read_text(encoding="utf-8")
        body = transform_agent_text(body, "claude-code")
        tools = render_claude_tools(agent.get("capabilities", []))
        frontmatter = [
            "---",
            f"name: {target_name}",
            f"description: {json.dumps(transform_agent_text(agent['description'], 'claude-code'))}",
        ]
        if tools:
            frontmatter.append(f"tools: {tools}")
        # Per-agent model/effort tiering lives in agent.yaml model_intent under the
        # "claude-code" key as an object; a legacy "target-native" string emits
        # nothing (inherit). "inherit" values are omitted so the agent follows the
        # session. Haiku agents must not carry effort (Haiku has no effort level).
        intent = agent.get("model_intent", {}).get("claude-code")
        if isinstance(intent, dict):
            model = intent.get("model")
            effort = intent.get("effort")
            if model and model != "inherit":
                frontmatter.append(f"model: {model}")
            if effort and effort != "inherit":
                frontmatter.append(f"effort: {effort}")
        frontmatter.append("---")
        write_text(
            target_root / ".claude" / "agents" / f"{target_name}.md",
            "\n".join(frontmatter) + "\n\n" + body.strip() + "\n",
        )


def render_codex_agent_adapter(agent: dict[str, Any]) -> str:
    codex_name = agent["id"]
    capabilities = agent.get("capabilities", [])
    prompt_body = codex_agent_prompt_body(agent)
    instructions = (
        f"{codex_agent_metadata_header(agent)}\n\n"
        f"{CODEX_AGENT_INSTRUCTIONS_DELIMITER}\n\n{prompt_body}"
    )
    agent_lines = [
        f"name = {toml_string(codex_name)}",
        f"description = {toml_string(transform_agent_text(agent['description'], 'openai-codex'))}",
    ]
    # Per-agent model/effort tiering. model_intent.openai-codex is an object
    # carrying an optional per-agent model override and a reasoning-effort tier;
    # a legacy "target-native" string or an omitted/"inherit" value emits nothing,
    # so the agent inherits the session model/effort.
    codex_intent = agent.get("model_intent", {}).get("openai-codex")
    if isinstance(codex_intent, dict):
        model = codex_intent.get("model")
        effort = codex_intent.get("effort")
        if model and model != "inherit":
            agent_lines.append(f"model = {toml_string(model)}")
        if effort and effort != "inherit":
            agent_lines.append(f"model_reasoning_effort = {toml_string(effort)}")
    sandbox_mode = codex_sandbox_mode(capabilities)
    if sandbox_mode:
        agent_lines.append(f"sandbox_mode = {toml_string(sandbox_mode)}")
    agent_lines.append(f"developer_instructions = {toml_string(instructions)}")
    return "\n".join(agent_lines) + "\n"


def render_github(target_root: Path) -> None:
    write_text(
        target_root / ".github" / "copilot-instructions.md",
        render_copilot_instructions(),
    )
    instructions_root = target_root / ".github" / "instructions"
    instructions_root.mkdir(parents=True, exist_ok=True)
    for policy in shared_policies():
        write_text(
            instructions_root / policy.source.name,
            render_github_instruction_adapter(policy),
        )

    copy_file(
        REPO_ROOT / "shared" / "hooks" / "hooks.json",
        target_root / ".github" / "hooks" / "hooks.json",
    )
    render_vscode_mcp_json(target_root / ".vscode" / "mcp.json")
    render_vscode_tasks_json(target_root / ".vscode" / "tasks.json")

    for agent, agent_dir in shared_agents("github-copilot"):
        write_text(
            target_root / ".github" / "agents" / f"{agent['id']}.agent.md",
            render_github_agent_adapter(agent, agent_dir),
        )


def render_claude(target_root: Path) -> None:
    write_text(target_root / "CLAUDE.md", render_root_guidance("claude-code"))
    render_claude_mcp_json(target_root / ".mcp.json")
    render_claude_settings(target_root / ".claude" / "settings.json")


def render_codex(target_root: Path) -> None:
    render_codex_config(target_root / ".codex" / "config.toml")
    render_codex_hooks(target_root / ".codex" / "hooks.json")

    for agent, _agent_dir in shared_agents("openai-codex"):
        target_name = agent["id"]
        write_text(
            target_root / ".codex" / "agents" / f"{target_name}.toml",
            render_codex_agent_adapter(agent),
        )


def render_antigravity_agent_adapter(agent: dict[str, Any]) -> str:
    """Render one documented Antigravity Markdown custom agent."""
    intent = agent["model_intent"]["google-antigravity"]
    frontmatter = [
        "---",
        f"name: {agent['id']}",
        f"description: {json.dumps(transform_agent_text(agent['description'], 'google-antigravity'))}",
        "tools:",
        *(f"  - {tool}" for tool in render_antigravity_tools(agent["capabilities"])),
        "mainAgent: false",
        f"subagent: {'false' if agent['id'] == 'orchestrator' else 'true'}",
        f"model: {intent['model']}",
    ]
    if agent["id"] != "orchestrator":
        frontmatter.append("inheritMcp: true")
    frontmatter.append("---")
    return (
        "\n".join(frontmatter)
        + "\n\n"
        + provider_agent_prompt_body(agent, "google-antigravity")
        + "\n"
    )


def render_antigravity(target_root: Path) -> None:
    """Render the static Google Antigravity provider adapter surface."""
    copy_tree(REPO_ROOT / "shared" / "skills", target_root / ".agents" / "skills")
    write_json(
        target_root / ".agents" / "mcp_config.json",
        {"mcpServers": shared_mcp_servers()},
    )
    render_antigravity_hooks(target_root / ".agents" / "hooks.json")
    for agent, _agent_dir in shared_agents("google-antigravity"):
        write_text(
            target_root / ".agents" / "agents" / agent["id"] / "agent.md",
            render_antigravity_agent_adapter(agent),
        )


def render_multi_agent(target_root: Path) -> None:
    render_devcontainer(target_root)
    render_shared_basis(target_root, "multi-agent")
    write_text(target_root / "AGENTS.md", render_root_guidance("multi-agent"))
    render_github(target_root)
    render_claude(target_root)
    render_codex(target_root)
    render_antigravity(target_root)


def generate(targets: list[str], output_root: Path) -> None:
    for target in targets:
        target_root = reset_target(output_root, target)
        if target == "multi-agent":
            render_multi_agent(target_root)
        else:
            raise ValueError(f"unknown target: {target}")
        strip_quarantine(target_root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all", action="store_true", help="Generate the installable target."
    )
    parser.add_argument(
        "--target", action="append", choices=TARGETS, help="Target to generate."
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT_ROOT, help="Output root."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    targets = list(TARGETS) if args.all or not args.target else args.target
    generate(targets, args.output)
    for target in targets:
        print(f"generated {target} -> {args.output / target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
