#!/usr/bin/env python3
"""Validate the generated bootstrap target."""

from __future__ import annotations

import filecmp
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = REPO_ROOT / "dist"
TARGETS = ("multi-agent",)
TARGET_ROOT = DIST_ROOT / "multi-agent"
COPILOT_MODEL_PINS = (
    "GPT-5.4",
    "Claude Opus 4.6",
    "Claude Sonnet 4.6",
    "(copilot)",
)
GITHUB_ALLOWED_AGENT_MODELS = {
    "GPT-5.4",
    "Claude Opus 4.6",
    "Claude Sonnet 4.6",
}
REQUIRED_HOOK_SCRIPTS = (
    "run-hook.sh",
    "protect-files.sh",
    "git-protection.sh",
    "context-mode-dispatch.sh",
    "session-log.sh",
    "hf-ai-sync.sh",
    "enforce-branch-state.sh",
    "record-branch-state.sh",
    "enforce-commit-gate.sh",
    "record-commit-closeout.sh",
    "enforce-pr-gate.sh",
    "session-start-state.sh",
    "stop-session-log-check.sh",
)
REQUIRED_HOOK_LIBRARIES = (
    "_lib-frontmatter.sh",
)
NON_COPILOT_REVIEW_LABEL_LEAKS = (
    "Review Pass (Codex)",
    "Review Pass (Sonnet)",
    "Findings (Codex)",
    "Findings (Sonnet)",
)
NON_COPILOT_PATH_LEAKS = (
    ".github/session_logs",
    ".github/quality_reports",
    ".github/explorations",
    ".github/plans",
    ".github/skills",
    ".github/agents",
    ".github/hooks",
    ".github/instructions",
    ".github/MEMORY.md",
    ".github/scripts",
    ".codex/skills",
    ".github/AGENTS.md",
    ".github/CLAUDE.md",
    "copilot-instructions.md",
    "Copy `.github/` directory",
    "new project's `.github/`",
    "git add .github/",
    "AGENTS.md/",
    "CLAUDE.md/",
    "AGENTS.md**",
    "CLAUDE.md**",
    "AGENTS.mdtool",
    "CLAUDE.mdtool",
)
OBSOLETE_GENERATED_DIRS = (
    ".github/skills",
    ".github/scripts",
    ".github/templates",
    ".github/session_logs",
    ".github/quality_reports",
    ".github/explorations",
    ".github/plans",
    ".agents/skills",
    ".codex/skills",
    ".codex/scripts",
    ".codex/templates",
    ".codex/session_logs",
    ".codex/quality_reports",
    ".codex/explorations",
    ".codex/plans",
    ".codex/hooks/scripts",
)
OBSOLETE_ROOT_SOURCE_DIRS = (
    ".github/agents",
    ".github/instructions",
    ".github/skills",
    ".github/scripts",
    ".github/templates",
    ".github/plans",
    ".github/session_logs",
    ".github/quality_reports",
    ".github/hooks/scripts",
)
def text_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and not any(part in {".git", "__pycache__"} for part in path.parts)
        and path.suffix not in {".pyc"}
    ]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_toml(path: Path) -> dict[str, object]:
    return tomllib.loads(read(path))


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def count_skills(root: Path) -> int:
    return len(list(root.glob("*/SKILL.md")))


def target_support_root(target: str) -> Path:
    if target not in TARGETS:
        raise ValueError(f"unknown target: {target}")
    return TARGET_ROOT / ".claude"


def compare_dirs(left: Path, right: Path, errors: list[str]) -> None:
    comparison = filecmp.dircmp(left, right)
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        errors.append("generated dist is not deterministic; rerun scripts/generate_targets.py --all")
        return
    # Compare file contents (shallow=False), not just stat signatures, so a
    # byte-level nondeterminism is caught even when size/mtime happen to match.
    _, mismatch, errored = filecmp.cmpfiles(left, right, comparison.common_files, shallow=False)
    if mismatch or errored:
        errors.append("generated dist is not deterministic; rerun scripts/generate_targets.py --all")
        return
    for name in comparison.common_dirs:
        compare_dirs(left / name, right / name, errors)


def validate_agents(errors: list[str]) -> None:
    shared_agents = sorted((REPO_ROOT / "shared" / "agents").glob("*/agent.yaml"))
    expected_count = len(shared_agents)
    check(expected_count > 0, f"no shared agents found under shared/agents/", errors)

    for metadata_path in shared_agents:
        data = json.loads(read(metadata_path))
        agent_id = data["id"]
        check((metadata_path.parent / "prompt.md").exists(), f"{agent_id} missing canonical prompt.md", errors)
        check(not (metadata_path.parent / "targets").exists(), f"{agent_id} must not keep target-specific prompt forks", errors)
        capabilities = set(data.get("capabilities", []))
        if agent_id == "orchestrator":
            # R-AGENTS-01: the orchestrator's prompt mandates branch/commit/PR
            # and memory/session-log writes, so its toolset must actually grant
            # delegation, editing, and execution.
            missing = {"delegate", "edit", "execute"} - capabilities
            check(
                not missing,
                f"orchestrator capabilities must cover its prompt-declared actions; missing {sorted(missing)}",
                errors,
            )

    generated_github_agents = sorted((TARGET_ROOT / ".github" / "agents").glob("*.agent.md"))
    check(len(generated_github_agents) == expected_count, "GitHub agent count must match shared agents", errors)
    for metadata_path in shared_agents:
        agent_id = json.loads(read(metadata_path))["id"]
        generated = TARGET_ROOT / ".github" / "agents" / f"{agent_id}.agent.md"
        check(generated.exists(), f"missing generated GitHub agent: {agent_id}", errors)
        if generated.exists():
            text = read(generated)
            check(
                ".claude/agents/" in text,
                f"GitHub agent adapter must point at canonical .claude agent: {generated}",
                errors,
            )
            for reference in re.findall(r"`(\.claude/agents/[^`]+\.md)`", text):
                check(
                    (TARGET_ROOT / reference).exists(),
                    f"GitHub agent adapter points at missing canonical agent: {generated}: {reference}",
                    errors,
                )
            check(
                "This file is the GitHub Copilot native adapter" in text,
                f"GitHub agent should be a thin native adapter: {generated}",
                errors,
            )

    claude_agents = sorted((TARGET_ROOT / ".claude" / "agents").glob("*.md"))
    check(len(claude_agents) == expected_count, "canonical .claude agent count must match shared agents", errors)
    for path in claude_agents:
        text = read(path)
        check(text.startswith("---\n"), f"Claude agent missing frontmatter: {path}", errors)
        check("\nname: " in text and "\ndescription: " in text, f"Claude agent missing required fields: {path}", errors)
        check(
            "tool-routing.instructions.md" in text,
            f"Claude agent must route retrieval through tool-routing instructions: {path}",
            errors,
        )
        if path.stem == "documenter":
            check(
                "normal prose" in text.lower() and "caveman" in text.lower(),
                f"Documenter must explicitly keep user-facing docs in normal prose: {path}",
                errors,
            )
        else:
            check(
                "caveman" in text.lower(),
                f"Claude agent must report back with caveman full prose framing: {path}",
                errors,
            )

    codex_agents = sorted((TARGET_ROOT / ".codex" / "agents").glob("*.toml"))
    check(len(codex_agents) == expected_count, "Codex custom agent count must match shared agents", errors)
    check(
        not (TARGET_ROOT / ".codex" / "rules").exists(),
        "Codex target must not generate deprecated .codex/rules output",
        errors,
    )

    expected_codex_names = {json.loads(read(path))["id"] for path in shared_agents}
    check(
        {path.stem for path in codex_agents} == expected_codex_names,
        "Codex custom agent filenames must match mapped shared agent names",
        errors,
    )

    for path in codex_agents:
        text = read(path)
        try:
            data = read_toml(path)
        except tomllib.TOMLDecodeError as error:
            errors.append(f"invalid Codex custom agent TOML: {path}: {error}")
            continue
        for field in ("name", "description", "developer_instructions"):
            check(isinstance(data.get(field), str) and bool(data.get(field)), f"Codex agent missing required field {field}: {path}", errors)
        check(data.get("name") == path.stem, f"Codex agent name must match filename stem: {path}", errors)
        instructions = str(data.get("developer_instructions", ""))
        check(
            ".claude/agents/" in instructions,
            f"Codex agent adapter must point at canonical .claude agent: {path}",
            errors,
        )
        check(
            "OpenAI Codex custom-agent adapter" in instructions,
            f"Codex agent should be a thin native adapter: {path}",
            errors,
        )
        for reference in re.findall(r"`(\.claude/agents/[^`]+\.md)`", instructions):
            check(
                (TARGET_ROOT / reference).exists(),
                f"Codex agent adapter points at missing canonical agent: {path}: {reference}",
                errors,
            )
    for root in (TARGET_ROOT / ".claude" / "agents", TARGET_ROOT / ".codex" / "agents"):
        for path in text_files(root):
            text = read(path)
            for label in NON_COPILOT_REVIEW_LABEL_LEAKS:
                check(label not in text, f"non-Copilot review helper label leaked into {path}: {label}", errors)

    # R-AGENTS-06: control-plane guards must use consumer paths; the authoring
    # repo's shared/ and dist/ must not leak into generated agent bodies.
    for path in sorted((TARGET_ROOT / ".claude" / "agents").glob("*.md")):
        text = read(path)
        for authoring_path in ("shared/", "dist/"):
            check(
                authoring_path not in text,
                f"generated agent must not reference authoring-repo path '{authoring_path}': {path}",
                errors,
            )
        # R-AGENTS-07: the documenter must diff against the plan's originating
        # branch (dev), never main.
        check(
            "main...HEAD" not in text,
            f"generated agent must not diff against main...HEAD (use originating_branch/dev): {path}",
            errors,
        )
        # R-AGENTS-08: the verifier is the single owner of the persisted score
        # report; only it writes the report (`--json --out`).
        if "--json --out" in text:
            check(
                path.stem == "verifier",
                f"only the verifier may write a persisted score report (--json --out): {path}",
                errors,
            )

    validate_github_agent_models(errors)


def validate_github_agent_models(errors: list[str]) -> None:
    agent_root = TARGET_ROOT / ".github" / "agents"
    for path in sorted(agent_root.glob("*.agent.md")):
        text = read(path)
        if not text.startswith("---\n"):
            errors.append(f"GitHub agent missing frontmatter: {path}")
            continue
        parts = text.split("---\n", 2)
        if len(parts) != 3:
            errors.append(f"GitHub agent frontmatter is malformed: {path}")
            continue
        lines = parts[1].splitlines()
        for index, line in enumerate(lines):
            if not line.startswith("model:"):
                continue
            value = line.split(":", 1)[1].strip()
            check(value, f"GitHub agent model must be a single string, not a YAML list: {path}", errors)
            if value:
                check(
                    value in GITHUB_ALLOWED_AGENT_MODELS,
                    f"GitHub agent model is not a current supported Copilot model string: {path}: {value}",
                    errors,
                )
                check("(copilot)" not in value, f"GitHub agent model must not include provider suffix: {path}", errors)
            if index + 1 < len(lines):
                check(
                    not lines[index + 1].lstrip().startswith("- "),
                    f"GitHub agent model must not be a YAML sequence: {path}",
                    errors,
                )


def validate_model_leaks(errors: list[str]) -> None:
    non_github_roots = (
        TARGET_ROOT / "CLAUDE.md",
        TARGET_ROOT / "AGENTS.md",
        TARGET_ROOT / ".claude",
        TARGET_ROOT / ".codex",
    )
    for root in non_github_roots:
        paths = [root] if root.is_file() else text_files(root)
        for path in paths:
            text = read(path)
            for pin in COPILOT_MODEL_PINS:
                if pin in text:
                    errors.append(f"Copilot model pin leaked into non-GitHub output: {path} contains {pin}")


def validate_mcp_and_hooks(errors: list[str]) -> None:
    github_mcp = json.loads(read(TARGET_ROOT / ".vscode" / "mcp.json"))
    claude_mcp = json.loads(read(TARGET_ROOT / ".mcp.json"))
    for server in ("semble", "context-mode"):
        check(server in github_mcp.get("servers", {}), f"github missing MCP server: {server}", errors)
        check(server in claude_mcp.get("mcpServers", {}), f"claude missing MCP server: {server}", errors)
    check("servers" not in claude_mcp, "Claude .mcp.json must use mcpServers, not servers", errors)

    codex_config = read(TARGET_ROOT / ".codex" / "config.toml")
    try:
        read_toml(TARGET_ROOT / ".codex" / "config.toml")
    except tomllib.TOMLDecodeError as error:
        errors.append(f"invalid Codex config TOML: {error}")
    # R-CODEX-01: hooks are on by default in current Codex; the [features] block
    # is redundant and must not be emitted.
    check("[features]" not in codex_config, "Codex config must not emit the redundant [features] block", errors)
    check("hooks = true" not in codex_config, "Codex config must not restate hooks = true (on by default)", errors)
    check("codex_hooks = true" not in codex_config, "Codex config must not use deprecated codex_hooks alias", errors)
    check("[agents]" in codex_config, "Codex config missing agents section", errors)
    check("max_depth = 1" in codex_config, "Codex config must cap agent nesting depth", errors)
    check("[mcp_servers.semble]" in codex_config, "Codex config missing Semble MCP server", errors)
    check("[mcp_servers.context-mode]" in codex_config, "Codex config missing context-mode MCP server", errors)
    check("../.claude/skills/" in codex_config, "Codex config must point skills at .claude/skills", errors)
    # R-CODEX-01: skill paths point at the SKILL.md file, not the directory.
    check('/SKILL.md"' in codex_config, "Codex skill paths must point at the SKILL.md file", errors)

    codex_hooks = json.loads(read(TARGET_ROOT / ".codex" / "hooks.json"))
    check(set(codex_hooks) == {"hooks"}, "Codex hooks.json should only contain the top-level hooks object", errors)
    # R-CODEX-01: PreCompact is a documented Codex event and must be wired.
    check("PreCompact" in codex_hooks.get("hooks", {}), "Codex hooks must wire the documented PreCompact event", errors)
    for event_name, groups in codex_hooks.get("hooks", {}).items():
        check(isinstance(groups, list), f"Codex hook event must be a list: {event_name}", errors)
        for group in groups if isinstance(groups, list) else []:
            check(isinstance(group, dict), f"Codex hook group must be an object: {event_name}", errors)
            check("hooks" in group and isinstance(group.get("hooks"), list), f"Codex hook group missing nested hooks: {event_name}", errors)
            for hook in group.get("hooks", []) if isinstance(group, dict) else []:
                command = hook.get("command", "") if isinstance(hook, dict) else ""
                check(
                    "git rev-parse --show-toplevel" in command,
                    f"Codex repo-local hook should resolve from git root: {event_name}",
                    errors,
                )
                check(
                    ".claude/hooks/scripts/" in command,
                    f"Codex hooks should invoke shared .claude hook scripts: {event_name}",
                    errors,
                )
                if (
                    "session-log.sh" in command
                    or "protect-files.sh" in command
                    or "enforce-" in command
                    or "record-" in command
                    or "session-start-state.sh" in command
                    or "stop-session-log-check.sh" in command
                ):
                    check(
                        "openai-codex" in command,
                        f"Codex hook command should pass target id: {event_name}",
                        errors,
                    )

    hook_roots = (TARGET_ROOT / ".claude" / "hooks" / "scripts",)
    for hook_root in hook_roots:
        for script in REQUIRED_HOOK_SCRIPTS:
            path = hook_root / script
            check(path.exists(), f"missing hook script: {path}", errors)
            check(path.exists() and path.stat().st_mode & 0o111, f"hook script is not executable: {path}", errors)
        for script in REQUIRED_HOOK_LIBRARIES:
            path = hook_root / script
            check(path.exists(), f"missing hook library: {path}", errors)

    github_hooks = json.loads(read(TARGET_ROOT / ".github" / "hooks" / "hooks.json"))
    github_hook_text = json.dumps(github_hooks)
    check(".claude/hooks/scripts/" in github_hook_text, "GitHub hooks should invoke shared .claude hook scripts", errors)
    check("github-copilot" in github_hook_text, "GitHub hooks should pass target id", errors)
    check("hf-ai-sync.sh" in github_hook_text, "GitHub stop hooks should push HF AI state", errors)
    for event_name, hooks in github_hooks.get("hooks", {}).items():
        check(isinstance(hooks, list), f"GitHub hook event must be a list: {event_name}", errors)
        for hook in hooks if isinstance(hooks, list) else []:
            if not isinstance(hook, dict):
                errors.append(f"GitHub hook must be an object: {event_name}")
                continue
            check(hook.get("type") == "command", f"GitHub hook must be command type: {event_name}", errors)
            check("args" not in hook, f"GitHub hooks must not use unsupported args field: {event_name}", errors)
            check("bash" in hook, f"GitHub hook must include bash field to avoid /bin/sh fallback: {event_name}", errors)
            check("timeout" in hook, f"GitHub hook missing VS Code timeout: {event_name}", errors)
            check("timeoutSec" in hook, f"GitHub hook missing Copilot CLI/cloud timeoutSec: {event_name}", errors)
            for field in ("bash", "linux", "osx"):
                command = hook.get(field)
                if command is not None:
                    check(
                        ".claude/hooks/scripts/run-hook.sh" in str(command),
                        f"GitHub hook {field} should invoke shared dispatcher: {event_name}",
                        errors,
                    )
                    check(
                        "/bin/sh" not in str(command),
                        f"GitHub hook {field} must not depend on /bin/sh: {event_name}",
                        errors,
                    )

    claude_settings = json.loads(read(TARGET_ROOT / ".claude" / "settings.json"))
    claude_settings_text = json.dumps(claude_settings)
    check(".claude/hooks/scripts/" in claude_settings_text, "Claude settings should invoke shared .claude hook scripts", errors)
    check("claude-code" in claude_settings_text, "Claude hooks should pass target id", errors)
    check("hf-ai-sync.sh" in claude_settings_text, "Claude stop hooks should push HF AI state", errors)

    check("hf-ai-sync.sh" in json.dumps(codex_hooks), "Codex stop hooks should push HF AI state", errors)

    # R-SYNC-02: consumers push state only; the canonical bootstrap is never
    # re-uploaded from a consumer's Stop hook.
    for label, text in (
        ("Claude settings", claude_settings_text),
        ("GitHub hooks", github_hook_text),
        ("Codex hooks", json.dumps(codex_hooks)),
    ):
        check("push-state" in text, f"{label} Stop hook must push state", errors)
        check("upload-bootstrap" not in text, f"{label} Stop hook must not re-mirror the bootstrap (upload-bootstrap)", errors)

    dispatcher = TARGET_ROOT / ".claude" / "hooks" / "scripts" / "run-hook.sh"
    check(
        dispatcher.exists() and dispatcher.stat().st_mode & 0o111,
        "generated hook dispatcher run-hook.sh must be executable because Claude/Codex invoke it directly",
        errors,
    )

    validate_hook_guardrails(errors)
    validate_generated_scripts(errors)


def run_hook(
    script: Path,
    payload: dict[str, object],
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    result = subprocess.run(
        [str(script), *args],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        cwd=cwd,
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


def run_hook_raw(
    script: Path,
    raw_input: str,
    *args: str,
    cwd: Path | None = None,
) -> tuple[int, str, str]:
    result = subprocess.run(
        [str(script), *args],
        input=raw_input,
        text=True,
        capture_output=True,
        check=False,
        cwd=cwd,
    )
    return result.returncode, result.stdout, result.stderr


def path_without_uv() -> dict[str, str]:
    """A copy of os.environ with any directory containing a `uv` binary removed
    from PATH, so tests can exercise the pure-bash guardrail fallback."""
    env = dict(os.environ)
    kept = [
        part
        for part in env.get("PATH", "").split(os.pathsep)
        if part and not (Path(part) / "uv").exists()
    ]
    env["PATH"] = os.pathsep.join(kept)
    return env


def validate_hook_guardrails(errors: list[str]) -> None:
    hook_cases = (
        (
            TARGET_ROOT / ".claude" / "hooks" / "scripts" / "protect-files.sh",
            ".github/hooks/hooks.json",
            "ask",
            "github-copilot",
        ),
        (
            TARGET_ROOT / ".claude" / "hooks" / "scripts" / "protect-files.sh",
            ".claude/settings.json",
            "ask",
            "claude-code",
        ),
        (
            TARGET_ROOT / ".claude" / "hooks" / "scripts" / "protect-files.sh",
            ".codex/hooks.json",
            "deny",
            "openai-codex",
        ),
    )
    for script, protected_path, expected_decision, target_id in hook_cases:
        patch = f"*** Begin Patch\n*** Update File: {protected_path}\n@@\n x\n*** End Patch\n"
        returncode, stdout, stderr = run_hook(
            script,
            {"tool_name": "apply_patch", "tool_input": {"command": patch}},
            target_id,
        )
        check(returncode == 0, f"hook guardrail failed to run: {script}: {stderr}", errors)
        check(
            f'"permissionDecision":"{expected_decision}"' in stdout,
            f"hook guardrail did not protect {protected_path} with {expected_decision}: {script}",
            errors,
        )

    for target_id, hook_root in (
        ("github-copilot", TARGET_ROOT / ".claude" / "hooks" / "scripts"),
        ("claude-code", TARGET_ROOT / ".claude" / "hooks" / "scripts"),
        ("openai-codex", TARGET_ROOT / ".claude" / "hooks" / "scripts"),
    ):
        returncode, stdout, stderr = run_hook(
            hook_root / "protect-files.sh",
            {"tool_name": "Write", "tool_input": {"path": ".env"}},
            target_id,
        )
        check(returncode == 0, f"protected-file guardrail failed to run: {hook_root}: {stderr}", errors)
        check(
            '"permissionDecision":"deny"' in stdout,
            f"protected-file guardrail did not deny .env: {hook_root}",
            errors,
        )

        returncode, stdout, stderr = run_hook(
            hook_root / "protect-files.sh",
            {"tool_name": "Bash", "tool_input": {"command": "touch .env"}},
            target_id,
        )
        check(returncode == 0, f"Bash protected-file guardrail failed to run: {hook_root}: {stderr}", errors)
        check(
            '"permissionDecision":"deny"' in stdout,
            f"protected-file guardrail did not deny Bash write to .env: {hook_root}",
            errors,
        )

        returncode, stdout, stderr = run_hook(
            hook_root / "git-protection.sh",
            {"tool_name": "Bash", "tool_input": {"command": "git reset --hard HEAD"}},
        )
        check(returncode == 0, f"git guardrail failed to run: {hook_root}: {stderr}", errors)
        check(
            '"permissionDecision":"deny"' in stdout,
            f"git guardrail did not deny git reset --hard: {hook_root}",
            errors,
        )

        # R-HOOKS-03: the two safety-critical guards must survive without `uv`.
        no_uv = path_without_uv()
        returncode, stdout, stderr = run_hook(
            hook_root / "protect-files.sh",
            {"tool_name": "Write", "tool_input": {"path": ".env"}},
            target_id,
            env=no_uv,
        )
        check(returncode == 0, f"protect-files failed to run without uv: {hook_root}: {stderr}", errors)
        check(
            '"permissionDecision":"deny"' in stdout,
            f"protect-files must deny .env write even without uv: {hook_root}",
            errors,
        )
        returncode, stdout, stderr = run_hook(
            hook_root / "git-protection.sh",
            {"tool_name": "Bash", "tool_input": {"command": "git -C . reset --hard"}},
            env=no_uv,
        )
        check(returncode == 0, f"git-protection failed to run without uv: {hook_root}: {stderr}", errors)
        check(
            '"permissionDecision":"deny"' in stdout,
            f"git-protection must deny reset --hard even without uv (and past global flags): {hook_root}",
            errors,
        )

    bash_hook_cases = (
        (
            TARGET_ROOT / ".claude" / "hooks" / "scripts" / "protect-files.sh",
            "cat > .github/hooks/hooks.json",
            "ask",
            "github-copilot",
        ),
        (
            TARGET_ROOT / ".claude" / "hooks" / "scripts" / "protect-files.sh",
            "cat > .claude/settings.json",
            "ask",
            "claude-code",
        ),
        (
            TARGET_ROOT / ".claude" / "hooks" / "scripts" / "protect-files.sh",
            "cat > .codex/hooks.json",
            "deny",
            "openai-codex",
        ),
    )
    for script, command, expected_decision, target_id in bash_hook_cases:
        returncode, stdout, stderr = run_hook(
            script,
            {"tool_name": "Bash", "tool_input": {"command": command}},
            target_id,
        )
        check(returncode == 0, f"Bash hook-file guardrail failed to run: {script}: {stderr}", errors)
        check(
            f'"permissionDecision":"{expected_decision}"' in stdout,
            f"hook guardrail did not protect Bash hook edit with {expected_decision}: {script}",
            errors,
        )

    validate_lifecycle_hook_guardrails(errors)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, check=False)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def setup_hook_repo(temp_root: Path) -> Path:
    repo = temp_root / "repo"
    repo.mkdir()
    result = subprocess.run(["git", "init", "-b", "dev"], cwd=repo, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        subprocess.run(["git", "init"], cwd=repo, text=True, capture_output=True, check=False)
        git(repo, "checkout", "-b", "dev")
    git(repo, "config", "user.email", "agent@example.com")
    git(repo, "config", "user.name", "Agent")
    shutil.copytree(TARGET_ROOT / ".claude" / "hooks" / "scripts", repo / ".claude" / "hooks" / "scripts")
    write(repo / ".gitignore", ".claude/\n")
    write(repo / ".claude" / "MEMORY.md", "# Memory\n")
    write(repo / "README.md", "# Scratch\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "initial")
    return repo


def write_big_plan(repo: Path, status: str = "planning", phases: tuple[str, ...] = ("phase-one",)) -> None:
    phase_lines = "\n".join(f"  - {phase}" for phase in phases)
    write(
        repo / ".claude" / "plans" / "foo.md",
        f"""---
name: foo
type: big-plan
status: {status}
originating_branch: dev
implementation_branch: foo_implementation
started_at:
phases:
{phase_lines}
current_phase:
---

# Foo
""",
    )


def write_small_plan(repo: Path, status: str = "in-progress") -> None:
    write(
        repo / ".claude" / "plans" / "phase-one.md",
        f"""---
name: phase-one
type: small-plan
parent_plan: foo
phase_index: 1
status: {status}
closeout_session_log: .claude/session_logs/phase-one-closeout.md
---

# Phase One
""",
    )


def lifecycle_script(repo: Path, name: str) -> Path:
    return repo / ".claude" / "hooks" / "scripts" / name


def validate_lifecycle_hook_guardrails(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = setup_hook_repo(Path(temp_dir))
        write_big_plan(repo)
        write_small_plan(repo)

        # R-HOOKS-04: a present-but-unparseable payload must fail closed
        # (non-zero exit + deny) instead of silently allowing the tool call.
        # Run against the temp repo so fail-closed logging stays isolated.
        for gate in ("protect-files.sh", "git-protection.sh", "enforce-commit-gate.sh", "enforce-pr-gate.sh"):
            returncode, stdout, stderr = run_hook_raw(
                lifecycle_script(repo, gate), "this is not json", "github-copilot", cwd=repo
            )
            check(returncode != 0, f"{gate} must exit non-zero on unparseable payload (got {returncode})", errors)
            check(
                '"permissionDecision":"deny"' in stdout,
                f"{gate} must deny on unparseable payload",
                errors,
            )

        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-commit-gate.sh"),
            {"tool_name": "Bash", "tool_input": {"command": 'git commit -m "test"'}},
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"commit gate on dev failed to run: {stderr}", errors)
        check('"permissionDecision":"deny"' in stdout, "commit gate must deny commits on dev", errors)

        # R-HOOKS-01: global git flags must not smuggle a commit past the classifier.
        for command in (
            'git -C . commit -m x',
            'git -c a=b commit -m x',
            'git --git-dir=.git commit -m x',
        ):
            returncode, stdout, stderr = run_hook(
                lifecycle_script(repo, "enforce-commit-gate.sh"),
                {"tool_name": "Bash", "tool_input": {"command": command}},
                "github-copilot",
                cwd=repo,
            )
            check(returncode == 0, f"commit gate flag-evasion case failed to run: {command}: {stderr}", errors)
            check('"permissionDecision":"deny"' in stdout, f"commit gate must deny flag-smuggled commit on dev: {command}", errors)

        # R-HOOKS-02: bypass subjects still undergo branch-shape validation.
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-commit-gate.sh"),
            {"tool_name": "Bash", "tool_input": {"command": 'git commit -m "chore(typo): x"'}},
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"commit gate bypass-branch-shape case failed to run: {stderr}", errors)
        check(
            '"permissionDecision":"deny"' in stdout,
            "commit gate must deny bypass-subject commits off an implementation branch",
            errors,
        )

        write(repo / "dirty.txt", "dirty\n")
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-branch-state.sh"),
            {"tool_name": "Bash", "tool_input": {"command": "git checkout -b foo_implementation"}},
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"branch gate dirty-tree case failed to run: {stderr}", errors)
        check('"permissionDecision":"deny"' in stdout, "branch gate must deny dirty-tree branch creation", errors)
        for command in (
            "git switch --create foo_implementation",
            "git checkout -B foo_implementation",
            "git -C . checkout -b foo_implementation",
        ):
            returncode, stdout, stderr = run_hook(
                lifecycle_script(repo, "enforce-branch-state.sh"),
                {"tool_name": "Bash", "tool_input": {"command": command}},
                "github-copilot",
                cwd=repo,
            )
            check(returncode == 0, f"branch gate alternate dirty-tree case failed to run: {stderr}", errors)
            check('"permissionDecision":"deny"' in stdout, f"branch gate must deny dirty-tree branch creation: {command}", errors)
        (repo / "dirty.txt").unlink()

        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-branch-state.sh"),
            {"tool_name": "Bash", "tool_input": {"command": 'git checkout -b "bad:slug_implementation"'}},
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"branch gate invalid-slug case failed to run: {stderr}", errors)
        check('"permissionDecision":"deny"' in stdout, "branch gate must deny invalid branch slugs", errors)

        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-branch-state.sh"),
            {"tool_name": "Bash", "tool_input": {"command": "git checkout -b foo_implementation"}},
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"branch gate positive case failed to run: {stderr}", errors)
        check('"permissionDecision":"deny"' not in stdout, f"branch gate should allow valid branch: {stdout}", errors)
        git(repo, "checkout", "-b", "foo_implementation")
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "record-branch-state.sh"),
            {"tool_name": "Bash", "tool_input": {"command": "git checkout -b foo_implementation"}},
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"record branch state failed to run: {stderr}", errors)
        check("current_phase: phase-one" in read(repo / ".claude" / "plans" / "foo.md"), "record branch state must set current_phase", errors)

        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-commit-gate.sh"),
            {"tool_name": "Bash", "tool_input": {"command": 'git commit -m "fixup! whatever"'}},
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"commit bypass case failed to run: {stderr}", errors)
        check('"permissionDecision":"deny"' not in stdout, "commit gate must allow bypass prefixes", errors)

        for command in (
            "git push -u origin foo_implementation",
            "git push origin HEAD",
            "git push origin foo_implementation",
        ):
            returncode, stdout, stderr = run_hook(
                lifecycle_script(repo, "enforce-pr-gate.sh"),
                {"tool_name": "Bash", "tool_input": {"command": command}},
                "github-copilot",
                cwd=repo,
            )
            check(returncode == 0, f"PR gate incomplete-push case failed to run: {stderr}", errors)
            check('"permissionDecision":"deny"' in stdout, f"PR gate must deny incomplete push command: {command}", errors)

        write_small_plan(repo, status="complete")
        write(
            repo / ".claude" / "session_logs" / "phase-one-closeout.md",
            "# Session\n\n**Status:** COMPLETED\n\n## [LEARN] Entries\n\n- [LEARN] none - no new lessons this session\n",
        )
        write(repo / "work.txt", "work\n")
        git(repo, "add", "work.txt")
        write(
            repo / ".claude" / "quality_reports" / "score-test.json",
            json.dumps(
                {
                    "score": 95,
                    "branch": "foo_implementation",
                    "phase": "phase-one",
                    "generated_at": "2099-01-01T00:00:00Z",
                },
                indent=2,
            )
            + "\n",
        )
        os.utime(repo / ".claude" / "quality_reports" / "score-test.json", None)

        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-commit-gate.sh"),
            {"tool_name": "Bash", "tool_input": {"command": 'git commit -m "phase 1 closeout"'}},
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"commit missing-metadata case failed to run: {stderr}", errors)
        check('"permissionDecision":"deny"' in stdout, "commit gate must reject score reports missing required metadata", errors)

        head_sha = git(repo, "rev-parse", "HEAD").stdout.strip()
        merge_base = git(repo, "merge-base", "dev", "HEAD").stdout.strip()
        # Content signature the gate recomputes: git hash-object of git diff <merge-base>.
        diff_out = git(repo, "diff", "--no-color", "--no-ext-diff", merge_base).stdout
        content_hash = subprocess.run(
            ["git", "-C", str(repo), "hash-object", "--stdin"],
            input=diff_out, text=True, capture_output=True, check=False,
        ).stdout.strip()
        reports_dir = repo / ".claude" / "quality_reports"

        def score_report(**overrides: object) -> dict[str, object]:
            report: dict[str, object] = {
                "score": 95,
                "branch": "foo_implementation",
                "phase": "phase-one",
                "generated_at": "2099-01-01T00:00:00Z",
                "base_ref": "dev",
                "merge_base_sha": merge_base,
                "head_sha": head_sha,
                "target": str(repo / "work.txt"),
                "dirty": False,
                "tests_passed": True,
                "tests_skipped": False,
                "content_hash": content_hash,
                "changed_files": ["work.txt"],
            }
            report.update(overrides)
            return report

        def clear_reports() -> None:
            for stale in reports_dir.glob("score-*.json"):
                stale.unlink()

        def write_score(report: dict[str, object]) -> None:
            clear_reports()
            path = reports_dir / "score-test.json"
            write(path, json.dumps(report, indent=2) + "\n")
            os.utime(path, None)

        # R-SCORE-01: tests_passed:false / missing, tests_skipped:true, or
        # dirty:true must all be denied even at a passing score.
        for label, report in (
            ("tests_passed:false", score_report(tests_passed=False)),
            ("tests_passed missing", {k: v for k, v in score_report().items() if k != "tests_passed"}),
            ("tests_skipped:true", score_report(tests_skipped=True)),
            ("dirty:true", score_report(dirty=True)),
        ):
            write_score(report)
            returncode, stdout, stderr = run_hook(
                lifecycle_script(repo, "enforce-commit-gate.sh"),
                {"tool_name": "Bash", "tool_input": {"command": 'git commit -m "phase 1 closeout"'}},
                "github-copilot",
                cwd=repo,
            )
            check(returncode == 0, f"commit {label} case failed to run: {stderr}", errors)
            check('"permissionDecision":"deny"' in stdout, f"commit gate must deny score report with {label} even at score 95", errors)

        # R-SCORE-02: select the newest report by generated_at, not filename.
        # Older passing report has a lexically-later filename; newer failing
        # report has a lexically-earlier one. The gate must pick the newer.
        clear_reports()
        write(reports_dir / "score-zzz.json", json.dumps(score_report(generated_at="2099-01-01T00:00:00Z"), indent=2) + "\n")
        write(reports_dir / "score-aaa.json", json.dumps(score_report(score=50, generated_at="2099-06-01T00:00:00Z"), indent=2) + "\n")
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-commit-gate.sh"),
            {"tool_name": "Bash", "tool_input": {"command": 'git commit -m "phase 1 closeout"'}},
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"commit report-selection case failed to run: {stderr}", errors)
        check('"permissionDecision":"deny"' in stdout, "commit gate must select the newest report by generated_at", errors)
        check("found 50" in stdout, "commit gate must use the newer (failing) report, not the lexically-later passing one", errors)

        # R-SCORE-02: an amended-HEAD / stale report yields a diagnosable message.
        write_score(score_report(head_sha="0" * 40))
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-commit-gate.sh"),
            {"tool_name": "Bash", "tool_input": {"command": 'git commit -m "phase 1 closeout"'}},
            "github-copilot",
            cwd=repo,
        )
        check('"permissionDecision":"deny"' in stdout, "commit gate must deny a stale-HEAD report", errors)
        check("re-run quality_score" in stdout, "stale-HEAD failure must tell the user to re-run quality_score", errors)

        # R-SCORE-02: content edited since scoring is caught by the content hash.
        write_score(score_report(content_hash="deadbeef"))
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-commit-gate.sh"),
            {"tool_name": "Bash", "tool_input": {"command": 'git commit -m "phase 1 closeout"'}},
            "github-copilot",
            cwd=repo,
        )
        check('"permissionDecision":"deny"' in stdout, "commit gate must deny a content_hash mismatch", errors)
        check("re-run quality_score" in stdout, "content_hash mismatch failure must tell the user to re-run quality_score", errors)

        write_score(score_report())

        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-commit-gate.sh"),
            {"tool_name": "Bash", "tool_input": {"command": 'git commit -m "phase 1 closeout"'}},
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"commit positive case failed to run: {stderr}", errors)
        check('"permissionDecision":"deny"' not in stdout, f"commit gate should allow complete closeout: {stdout}", errors)
        git(repo, "add", ".")
        git(repo, "commit", "-m", "phase 1 closeout")
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "record-commit-closeout.sh"),
            {"tool_name": "Bash", "tool_input": {"command": "git commit"}},
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"record commit no-subject case failed to run: {stderr}", errors)
        check(
            "status: complete" not in read(repo / ".claude" / "plans" / "foo.md"),
            "record commit closeout must not complete big plan without commit correlation",
            errors,
        )
        # R-HOOKS-05: a whitespace-variant subject still correlates with HEAD.
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "record-commit-closeout.sh"),
            {"tool_name": "Bash", "tool_input": {"command": 'git commit -m "phase 1   closeout"'}},
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"record commit closeout failed to run: {stderr}", errors)
        check("status: complete" in read(repo / ".claude" / "plans" / "foo.md"), "record commit closeout must complete final big plan via normalized subject match", errors)

        write(
            repo / ".claude" / "session_logs" / "hooks-bypass.log",
            "2099-01-01T00:00:00Z, target=github-copilot, branch=foo_implementation, subject=fixup! bypass\n",
        )
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-pr-gate.sh"),
            {"tool_name": "Bash", "tool_input": {"command": "gh pr create --base dev"}},
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"PR gate bypass-log case failed to run: {stderr}", errors)
        check('"permissionDecision":"deny"' in stdout, "PR gate must deny unacknowledged bypass logs", errors)

        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-pr-gate.sh"),
            {"tool_name": "Bash", "tool_input": {"command": "gh pr create --base main"}},
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"PR gate base-main case failed to run: {stderr}", errors)
        check('"permissionDecision":"deny"' in stdout, "PR gate must deny --base main", errors)


def validate_generated_scripts(errors: list[str]) -> None:
    python_scripts = sorted(DIST_ROOT.rglob("*.py"))
    with tempfile.TemporaryDirectory() as temp_dir:
        bytecode_root = Path(temp_dir)
        for index, script in enumerate(python_scripts):
            try:
                py_compile.compile(
                    str(script),
                    cfile=str(bytecode_root / f"{index}.pyc"),
                    doraise=True,
                )
            except py_compile.PyCompileError as error:
                errors.append(f"generated Python script syntax failed: {script}: {error}")

    shell_scripts = sorted(DIST_ROOT.rglob("*.sh"))
    for script in shell_scripts:
        result = subprocess.run(
            ["bash", "-n", str(script)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        check(result.returncode == 0, f"generated shell script syntax failed: {script}: {result.stderr}", errors)


def validate_skills_and_paths(errors: list[str]) -> None:
    shared_skill_count = count_skills(REPO_ROOT / "shared" / "skills")
    skill_root = TARGET_ROOT / ".claude" / "skills"
    count = count_skills(skill_root)
    check(count == shared_skill_count, f"multi-agent skill count mismatch: {count}", errors)
    for skill_path in sorted((REPO_ROOT / "shared" / "skills").glob("*/SKILL.md")):
        text = read(skill_path)
        frontmatter = text.split("---\n", 2)[1] if text.startswith("---\n") and len(text.split("---\n", 2)) == 3 else ""
        check(
            "\nvisibility: public" in f"\n{frontmatter}" or "\nvisibility: background" in f"\n{frontmatter}",
            f"skill missing visibility metadata: {skill_path}",
            errors,
        )

    # R-SKILLS-01: the commit skill must follow the enforced lifecycle, never
    # walking the agent into feature/* branches or agent-driven merges.
    commit_skill = skill_root / "commit" / "SKILL.md"
    if commit_skill.exists():
        commit_text = read(commit_skill)
        check("feature/" not in commit_text, "commit skill must not use feature/* branches", errors)
        check("gh pr merge" not in commit_text, "commit skill must not run gh pr merge (human merges)", errors)
        check("_implementation" in commit_text, "commit skill must use <plan>_implementation branches", errors)
        check("--base dev" in commit_text, "commit skill must open PRs against dev", errors)

    shared_prompts = sorted((REPO_ROOT / "shared" / "prompts").glob("*.prompt.md"))
    generated_prompts = sorted((TARGET_ROOT / ".claude" / "prompts").glob("*.prompt.md"))
    check(
        [path.name for path in generated_prompts] == [path.name for path in shared_prompts],
        ".claude prompt output must mirror shared/prompts",
        errors,
    )
    for source in shared_prompts:
        generated = TARGET_ROOT / ".claude" / "prompts" / source.name
        check(generated.exists() and read(generated) == read(source), f"generated prompt differs from source: {source.name}", errors)

    shared_profiles = sorted((REPO_ROOT / "shared" / "review-profiles").glob("*.md"))
    generated_profiles = sorted((TARGET_ROOT / ".claude" / "review-profiles").glob("*.md"))
    check(
        [path.name for path in generated_profiles] == [path.name for path in shared_profiles],
        ".claude review profile output must mirror shared/review-profiles",
        errors,
    )

    codex_config = read_toml(TARGET_ROOT / ".codex" / "config.toml")
    skill_entries = codex_config.get("skills", {})
    if isinstance(skill_entries, dict):
        skill_config = skill_entries.get("config", [])
    else:
        skill_config = []
    configured_skill_paths = {
        entry.get("path")
        for entry in skill_config
        if isinstance(entry, dict) and entry.get("enabled") is True
    }
    expected_skill_paths = {f"../.claude/skills/{path.parent.name}/SKILL.md" for path in (REPO_ROOT / "shared" / "skills").glob("*/SKILL.md")}
    check(
        configured_skill_paths == expected_skill_paths,
        "Codex config must enable every shared .claude skill by relative SKILL.md path",
        errors,
    )

    forbidden_fragments = ("/home/ghisso", "/Users/", "BEGIN OPENSSH", "PRIVATE KEY")
    for relative_path in OBSOLETE_GENERATED_DIRS:
        check(
            not (TARGET_ROOT / relative_path).exists(),
            f"multi-agent must not generate obsolete target-local path: {relative_path}",
            errors,
        )
    for relative_path in OBSOLETE_ROOT_SOURCE_DIRS:
        check(
            not (REPO_ROOT / relative_path).exists(),
            f"root .github must not keep legacy source mirror: {relative_path}",
            errors,
        )
    for path in text_files(TARGET_ROOT):
        text = read(path)
        for fragment in forbidden_fragments:
            if fragment in text:
                errors.append(f"forbidden fragment in generated file: {path} contains {fragment}")

    for root in (TARGET_ROOT / "CLAUDE.md", TARGET_ROOT / "AGENTS.md", TARGET_ROOT / ".claude", TARGET_ROOT / ".codex"):
        paths = [root] if root.is_file() else text_files(root)
        for path in paths:
            if "hooks" in path.parts and "scripts" in path.parts:
                continue
            text = read(path)
            for fragment in NON_COPILOT_PATH_LEAKS:
                if fragment in text:
                    errors.append(f"Copilot path leaked into non-GitHub output: {path} contains {fragment}")

    for root_guidance in (TARGET_ROOT / "CLAUDE.md", TARGET_ROOT / "AGENTS.md"):
        text = read(root_guidance)
        check(
            "pre-flight -> branch -> plan -> implement -> verify -> review -> score -> document -> learn -> session-log -> commit workflow" in text,
            f"{root_guidance.name} must include the full root workflow summary",
            errors,
        )
        check(
            "Score >= 90 plus required documentation updates are mandatory before commit or PR closeout" in text,
            f"{root_guidance.name} must require score >= 90 and documentation updates before closeout",
            errors,
        )

    stale_workflow_fragments = (
        "After score >= 80",
        "After score ≥ 80",
        "Score >= 80",
        "plan -> implement -> verify -> review -> score workflow",
        "PLAN -> IMPLEMENT -> VERIFY -> REVIEW -> FIX -> SCORE\n",
        "plan, verify, review, score loop",
        "plan/verify/review/score loop",
        "Score ≥ 80 = commit",
        "Score ≥ 90 = PR-ready",
        "auto-commit if score ≥ 80",
        "auto-commit if score >= 80",
        "Just do it",
        "codex_hooks",
        "quality_reports/<timestamp>-<phase>.json",
    )
    for path in (
        TARGET_ROOT / "AGENTS.md",
        TARGET_ROOT / "CLAUDE.md",
        TARGET_ROOT / ".claude" / "instructions" / "workspace.instructions.md",
        TARGET_ROOT / ".claude" / "instructions" / "workflow.instructions.md",
        TARGET_ROOT / ".claude" / "instructions" / "tool-routing.instructions.md",
        TARGET_ROOT / ".claude" / "instructions" / "quality-and-testing.instructions.md",
        TARGET_ROOT / ".claude" / "agents" / "orchestrator.md",
        TARGET_ROOT / ".claude" / "agents" / "verifier.md",
    ):
        text = read(path)
        for fragment in stale_workflow_fragments:
            check(fragment not in text, f"{path} contains stale workflow/gate phrase: {fragment}", errors)
    # docs/history/ holds archived completed plans; they legitimately contain
    # old path patterns and are not living documentation.
    source_paths = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        *(p for p in text_files(REPO_ROOT / "docs") if "history" not in p.relative_to(REPO_ROOT / "docs").parts),
        *text_files(REPO_ROOT / "shared"),
    ]
    for path in source_paths:
        text = read(path)
        check(
            "quality_reports/<timestamp>-<phase>.json" not in text,
            f"{path} contains stale quality report path pattern",
            errors,
        )
    tool_routing_text = read(TARGET_ROOT / ".claude" / "instructions" / "tool-routing.instructions.md")
    check(
        "Inside the generated devcontainer, Semble and context-mode are installed as required tools" in tool_routing_text,
        "tool-routing instructions must distinguish required devcontainer tooling from outside-devcontainer fallbacks",
        errors,
    )

    validate_support_files(errors)
    validate_generated_hygiene(errors)


def validate_support_files(errors: list[str]) -> None:
    required_files = (
        "MEMORY.md",
        "scripts/quality_score.py",
        "templates/session-log.md",
        "templates/plan-big.md",
        "templates/plan-small.md",
        "templates/quality-report.md",
        "templates/requirements-spec.md",
        "templates/skill-template.md",
        "plans/README.md",
        "quality_reports/README.md",
        "session_logs/README.md",
        "explorations/README.md",
        "instructions/workflow.instructions.md",
        "instructions/quality-and-testing.instructions.md",
        "instructions/tool-routing.instructions.md",
        "instructions/workspace.md",
        "prompts/README.prompt.md",
        "review-profiles/code.md",
        "review-profiles/security.md",
        "hooks/scripts/run-hook.sh",
        "hooks/scripts/protect-files.sh",
        "hooks/scripts/git-protection.sh",
        "hooks/scripts/context-mode-dispatch.sh",
        "hooks/scripts/session-log.sh",
        "hooks/scripts/hf-ai-sync.sh",
        "hooks/scripts/_lib-frontmatter.sh",
        "hooks/scripts/enforce-branch-state.sh",
        "hooks/scripts/record-branch-state.sh",
        "hooks/scripts/enforce-commit-gate.sh",
        "hooks/scripts/record-commit-closeout.sh",
        "hooks/scripts/enforce-pr-gate.sh",
        "hooks/scripts/session-start-state.sh",
        "hooks/scripts/stop-session-log-check.sh",
    )
    for target in TARGETS:
        support_root = target_support_root(target)
        for relative_path in required_files:
            path = support_root / relative_path
            check(path.exists(), f"{target} missing generated support file: {path}", errors)
            if relative_path in {"templates/plan-big.md", "templates/plan-small.md"} and path.exists():
                check(read(path).startswith("---\n"), f"{target} plan template must start with frontmatter: {path}", errors)


def validate_generated_hygiene(errors: list[str]) -> None:
    for path in DIST_ROOT.rglob("*"):
        if path.name == "__pycache__" or path.suffix == ".pyc":
            errors.append(f"generated bytecode artifact must not be committed: {path}")


def validate_devcontainer_and_installer(errors: list[str]) -> None:
    devcontainer_root = TARGET_ROOT / ".devcontainer"
    required_files = (
        "devcontainer.json",
        "Dockerfile",
        "post-start.sh",
        "hf-ai-sync.py",
    )
    for relative_path in required_files:
        path = devcontainer_root / relative_path
        check(path.exists(), f"missing generated devcontainer file: {path}", errors)

    if (devcontainer_root / "devcontainer.json").exists():
        data = json.loads(read(devcontainer_root / "devcontainer.json"))
        build = data.get("build", {})
        run_args = data.get("runArgs", [])
        container_env = data.get("containerEnv", {})
        settings = data.get("customizations", {}).get("vscode", {}).get("settings", {})
        post_create = data.get("postCreateCommand", "")
        check(build.get("context") == ".", "devcontainer build context must stay inside .devcontainer", errors)
        check(data.get("postStartCommand") == "bash .devcontainer/post-start.sh", "devcontainer must run post-start sync script", errors)
        check("--gpus" in run_args and "all" in run_args, "devcontainer must default to GPU sandbox run args", errors)
        check("HF_HUB_ENABLE_HF_TRANSFER" not in container_env, "devcontainer must not use deprecated HF_HUB_ENABLE_HF_TRANSFER", errors)
        check(container_env.get("HF_XET_HIGH_PERFORMANCE") == "1", "devcontainer must enable high-performance Hugging Face Xet transfers", errors)
        check("HF_TOKEN" in container_env, "devcontainer must forward HF_TOKEN", errors)
        check("HUGGING_FACE_HUB_TOKEN" in container_env, "devcontainer must forward HUGGING_FACE_HUB_TOKEN", errors)
        check(
            container_env.get("UV_PROJECT_ENVIRONMENT") == "/home/vscode/.venv",
            "devcontainer must not reuse a host-mounted project .venv",
            errors,
        )
        check(container_env.get("UV_LINK_MODE") == "copy", "devcontainer must use uv copy link mode", errors)
        check(
            settings.get("python.defaultInterpreterPath") == "/home/vscode/.venv/bin/python",
            "devcontainer VS Code Python path must use the container-local uv venv",
            errors,
        )
        check("/home/vscode/.venv" in post_create, "devcontainer postCreateCommand must initialize the container-local uv venv", errors)
        forbidden_run_args = ("/dev/fuse", "apparmor:unconfined")
        for fragment in forbidden_run_args:
            check(
                fragment not in json.dumps(run_args),
                f"devcontainer must not require hf-mount/FUSE privilege: {fragment}",
                errors,
            )

    if (devcontainer_root / "Dockerfile").exists():
        dockerfile = read(devcontainer_root / "Dockerfile")
        check("cuda-dl-base" in dockerfile, "devcontainer Dockerfile must use the GPU base image", errors)
        check("npm install -g context-mode" in dockerfile, "devcontainer Dockerfile must install context-mode", errors)
        check("command -v context-mode" in dockerfile, "devcontainer Dockerfile must verify context-mode is on PATH", errors)
        check("context-mode --help >/dev/null" in dockerfile, "devcontainer Dockerfile must verify context-mode CLI execution", errors)
        check("huggingface_hub" in dockerfile, "devcontainer Dockerfile must install Hugging Face tooling", errors)
        check("hf_transfer" not in dockerfile, "devcontainer Dockerfile must not install deprecated hf_transfer tooling", errors)
        check("\"semble[mcp]\"" in dockerfile, "devcontainer Dockerfile must install Semble MCP tooling", errors)
        check("python3 -c \"import huggingface_hub, semble\"" in dockerfile, "devcontainer Dockerfile must verify HF hub and Semble imports", errors)
        check("command -v hf" in dockerfile, "devcontainer Dockerfile must verify the HF CLI is on PATH", errors)
        check("command -v semble" in dockerfile, "devcontainer Dockerfile must verify the Semble CLI is on PATH", errors)
        check("optional " not in dockerfile.lower(), "devcontainer tool installs must be required, not optional fallbacks", errors)
        check("getent passwd \"${USERNAME}\"" in dockerfile, "devcontainer Dockerfile must verify the remote user passwd entry", errors)
        check("id -gn \"${USERNAME}\"" in dockerfile, "devcontainer Dockerfile must use the remote user's actual primary group", errors)
        check("USER ${USERNAME}" in dockerfile, "devcontainer Dockerfile must switch to the non-host user", errors)

    post_start = devcontainer_root / "post-start.sh"
    if post_start.exists():
        post_start_text = read(post_start)
        check("python3 \"$@\"" in post_start_text, "post-start must run the HF helper with system python3", errors)
        check("uv run python" not in post_start_text, "post-start must not invoke project uv for HF sync", errors)

    helper = devcontainer_root / "hf-ai-sync.py"
    scrubbed_env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"HF_AI_SYNC_BUCKET", "HF_AI_SYNC_PREFIX"}
    }
    if helper.exists():
        # R-SYNC-01: a configured bucket is honored; there is no baked default.
        configured_env = {**scrubbed_env, "HF_AI_SYNC_BUCKET": "example-org/example-bucket"}
        result = subprocess.run(
            [sys.executable, str(helper), "status", "--repo-root", str(REPO_ROOT), "--dry-run"],
            cwd=REPO_ROOT,
            env=configured_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(result.returncode == 0, f"HF sync helper dry-run status failed: {result.stderr}", errors)
        check("example-org/example-bucket" in result.stdout, "HF sync helper must honor the configured bucket", errors)

        # R-SYNC-04: push-state prunes only with --prune (delete off by default).
        default_push = subprocess.run(
            [sys.executable, str(helper), "push-state", "--repo-root", str(REPO_ROOT), "--dry-run"],
            cwd=REPO_ROOT, env=configured_env, text=True, capture_output=True, check=False,
        )
        check("delete=False" in default_push.stdout, "push-state must not delete remote state by default", errors)
        prune_push = subprocess.run(
            [sys.executable, str(helper), "push-state", "--repo-root", str(REPO_ROOT), "--dry-run", "--prune"],
            cwd=REPO_ROOT, env=configured_env, text=True, capture_output=True, check=False,
        )
        check("delete=True" in prune_push.stdout, "push-state --prune must reconcile (delete) remote state", errors)
        # R-SYNC-04: MEMORY.md is single-homed in state, not the bootstrap bundle.
        helper_src = read(helper)
        check(
            '".claude/MEMORY.md"' not in helper_src,
            "MEMORY.md must not be in BOOTSTRAP_PATHS (single-homed in state)",
            errors,
        )

        # R-SYNC-01: with no bucket configured the helper is a graceful no-op.
        no_bucket = subprocess.run(
            [sys.executable, str(helper), "status", "--repo-root", str(REPO_ROOT), "--dry-run"],
            cwd=REPO_ROOT,
            env=scrubbed_env,
            text=True,
            capture_output=True,
            check=False,
        )
        combined = no_bucket.stdout + no_bucket.stderr
        check(no_bucket.returncode == 0, "HF sync helper must not hard-fail without a bucket", errors)
        check("no HF sync bucket configured" in combined, "HF sync helper must explain a missing bucket", errors)

    installer = REPO_ROOT / "scripts" / "install_bootstrap.py"
    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_repo = Path(temp_dir_name) / "consumer"
        temp_repo.mkdir()
        init_result = subprocess.run(
            ["git", "init", str(temp_repo)],
            text=True,
            capture_output=True,
            check=False,
        )
        check(init_result.returncode == 0, f"temporary git init failed: {init_result.stderr}", errors)
        # R-SYNC-01: installer errors without a bucket (no baked default).
        no_bucket_install = subprocess.run(
            [sys.executable, str(installer), str(temp_repo), "--skip-upload", "--dry-run"],
            cwd=REPO_ROOT,
            env=scrubbed_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(no_bucket_install.returncode != 0, "installer must refuse to run without a bucket", errors)
        check(
            "HF_AI_SYNC_BUCKET" in (no_bucket_install.stdout + no_bucket_install.stderr),
            "installer must tell the user how to configure a bucket",
            errors,
        )

        install_result = subprocess.run(
            [
                sys.executable,
                str(installer),
                str(temp_repo),
                "--bucket",
                "example-org/example-bucket/test-project",
                "--skip-upload",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        check(install_result.returncode == 0, f"installer temp run failed: {install_result.stderr}", errors)
        check((temp_repo / ".devcontainer" / "devcontainer.json").exists(), "installer must copy trackable devcontainer", errors)
        check((temp_repo / ".gitignore").exists(), "installer must create or update .gitignore", errors)
        devcontainer_data = json.loads(read(temp_repo / ".devcontainer" / "devcontainer.json"))
        container_env = devcontainer_data.get("containerEnv", {})
        check(
            container_env.get("HF_AI_SYNC_BUCKET") == "example-org/example-bucket/test-project",
            "installer must persist project-specific HF sync path in .devcontainer",
            errors,
        )

        # R-POLICY-01: installer substitutes the workspace project-name placeholder.
        installed_workspace = read(temp_repo / ".claude" / "instructions" / "workspace.instructions.md")
        check(
            "[TODO: project name" not in installed_workspace,
            "installer must fill the workspace project-name placeholder",
            errors,
        )
        check(
            "**Project:** consumer" in installed_workspace,
            "installer must substitute the target repo name into the workspace instructions",
            errors,
        )

        ignored_result = subprocess.run(
            ["git", "-C", str(temp_repo), "check-ignore", ".claude/MEMORY.md"],
            text=True,
            capture_output=True,
            check=False,
        )
        check(ignored_result.returncode == 0, "installer must ignore generated .claude content", errors)

        devcontainer_ignore_result = subprocess.run(
            ["git", "-C", str(temp_repo), "check-ignore", ".devcontainer/devcontainer.json"],
            text=True,
            capture_output=True,
            check=False,
        )
        check(devcontainer_ignore_result.returncode != 0, "installer must leave .devcontainer trackable", errors)

        # R-SYNC-03: default install keeps the Copilot cloud surface ignored
        # (local-IDE only).
        copilot_ignored = subprocess.run(
            ["git", "-C", str(temp_repo), "check-ignore", ".github/agents/orchestrator.agent.md"],
            text=True,
            capture_output=True,
            check=False,
        )
        check(copilot_ignored.returncode == 0, "default install must ignore the Copilot cloud surface (.github/agents)", errors)

        helper_status_env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"HF_AI_SYNC_BUCKET", "HF_AI_SYNC_PREFIX"}
        }
        helper_status = subprocess.run(
            [
                sys.executable,
                str(temp_repo / ".devcontainer" / "hf-ai-sync.py"),
                "status",
                "--repo-root",
                str(temp_repo),
                "--dry-run",
            ],
            cwd=temp_repo,
            env=helper_status_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(helper_status.returncode == 0, f"installed helper status failed: {helper_status.stderr}", errors)
        check(
            "hf://buckets/example-org/example-bucket/test-project/bootstrap" in helper_status.stdout,
            "installed helper must read HF sync path from .devcontainer when env vars are unset",
            errors,
        )

    # R-SYNC-03: --commit-copilot-surface keeps the Copilot surface trackable.
    with tempfile.TemporaryDirectory() as flag_dir_name:
        flag_repo = Path(flag_dir_name) / "consumer"
        flag_repo.mkdir()
        subprocess.run(["git", "init", str(flag_repo)], text=True, capture_output=True, check=False)
        flag_install = subprocess.run(
            [
                sys.executable,
                str(installer),
                str(flag_repo),
                "--bucket",
                "example-org/example-bucket/test-project",
                "--skip-upload",
                "--commit-copilot-surface",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        check(flag_install.returncode == 0, f"installer --commit-copilot-surface run failed: {flag_install.stderr}", errors)
        gitignore_text = read(flag_repo / ".gitignore") if (flag_repo / ".gitignore").exists() else ""
        check(".github/agents/" not in gitignore_text, "--commit-copilot-surface must omit .github/agents from the ignore block", errors)
        surface_trackable = subprocess.run(
            ["git", "-C", str(flag_repo), "check-ignore", ".github/agents/orchestrator.agent.md"],
            text=True,
            capture_output=True,
            check=False,
        )
        check(surface_trackable.returncode != 0, "--commit-copilot-surface must leave .github/agents trackable", errors)
        # State still stays ignored regardless of the flag.
        state_ignored = subprocess.run(
            ["git", "-C", str(flag_repo), "check-ignore", ".claude/MEMORY.md"],
            text=True,
            capture_output=True,
            check=False,
        )
        check(state_ignored.returncode == 0, "--commit-copilot-surface must still ignore .claude state", errors)


def validate_determinism(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "dist"
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "generate_targets.py"), "--all", "--output", str(output)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"temporary generation failed: {result.stderr or result.stdout}")
            return
        compare_dirs(DIST_ROOT, output, errors)


def validate_routing_table_parity(errors: list[str]) -> None:
    """R-AGENTS-05: the profile-routing table must have exactly one home. Its
    distinctive row marker may appear in only one shared source file
    (workspace.instructions.md); everything else references it by path."""
    marker = "Domain-specific correctness"
    owner = REPO_ROOT / "shared" / "policies" / "workspace.instructions.md"
    holders = sorted(
        path
        for path in (REPO_ROOT / "shared").rglob("*.md")
        if "__pycache__" not in path.parts and marker in read(path)
    )
    check(
        holders == [owner],
        "profile-routing table must live only in shared/policies/workspace.instructions.md; "
        f"found the routing marker in: {[str(p.relative_to(REPO_ROOT)) for p in holders]}",
        errors,
    )


def main() -> int:
    errors: list[str] = []
    for target in TARGETS:
        check((DIST_ROOT / target).exists(), f"missing generated target: {target}", errors)

    if not errors:
        validate_agents(errors)
        validate_model_leaks(errors)
        validate_mcp_and_hooks(errors)
        validate_skills_and_paths(errors)
        validate_routing_table_parity(errors)
        validate_devcontainer_and_installer(errors)
        validate_determinism(errors)

    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1

    print("PASS generated target is structurally valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
