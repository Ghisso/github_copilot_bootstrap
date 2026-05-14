#!/usr/bin/env python3
"""Validate the generated bootstrap target."""

from __future__ import annotations

import filecmp
import json
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
OBSOLETE_TARGET_ROOTS = ("github-copilot", "claude-code", "openai-codex")
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
    "protect-files.sh",
    "git-protection.sh",
    "context-mode-dispatch.sh",
    "session-log.sh",
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
    if comparison.left_only or comparison.right_only or comparison.diff_files or comparison.funny_files:
        errors.append("generated dist is not deterministic; rerun scripts/generate_targets.py --all")
        return
    for name in comparison.common_dirs:
        compare_dirs(left / name, right / name, errors)


def validate_agents(errors: list[str]) -> None:
    shared_agents = sorted((REPO_ROOT / "shared" / "agents").glob("*/agent.yaml"))
    expected_count = len(shared_agents)
    check(expected_count == 8, f"expected 8 shared agents, found {expected_count}", errors)

    for metadata_path in shared_agents:
        data = json.loads(read(metadata_path))
        agent_id = data["id"]
        check((metadata_path.parent / "prompt.md").exists(), f"{agent_id} missing canonical prompt.md", errors)
        check(not (metadata_path.parent / "targets").exists(), f"{agent_id} must not keep target-specific prompt forks", errors)

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
    check("[features]" in codex_config, "Codex config missing features section", errors)
    check("codex_hooks = true" in codex_config, "Codex config must enable codex_hooks", errors)
    check("[agents]" in codex_config, "Codex config missing agents section", errors)
    check("max_depth = 1" in codex_config, "Codex config must cap agent nesting depth", errors)
    check("[mcp_servers.semble]" in codex_config, "Codex config missing Semble MCP server", errors)
    check("[mcp_servers.context-mode]" in codex_config, "Codex config missing context-mode MCP server", errors)
    check("../.claude/skills/" in codex_config, "Codex config must point skills at .claude/skills", errors)

    codex_hooks = json.loads(read(TARGET_ROOT / ".codex" / "hooks.json"))
    check(set(codex_hooks) == {"hooks"}, "Codex hooks.json should only contain the top-level hooks object", errors)
    check("PreCompact" not in codex_hooks.get("hooks", {}), "Codex hooks must not use unsupported PreCompact event", errors)
    for event_name, groups in codex_hooks.get("hooks", {}).items():
        check(isinstance(groups, list), f"Codex hook event must be a list: {event_name}", errors)
        for group in groups if isinstance(groups, list) else []:
            check(isinstance(group, dict), f"Codex hook group must be an object: {event_name}", errors)
            check("hooks" in group and isinstance(group.get("hooks"), list), f"Codex hook group missing nested hooks: {event_name}", errors)
            for hook in group.get("hooks", []) if isinstance(group, dict) else []:
                command = hook.get("command", "") if isinstance(hook, dict) else ""
                check(
                    "$(git rev-parse --show-toplevel)" in command,
                    f"Codex repo-local hook should resolve from git root: {event_name}",
                    errors,
                )
                check(
                    ".claude/hooks/scripts/" in command,
                    f"Codex hooks should invoke shared .claude hook scripts: {event_name}",
                    errors,
                )
                if "session-log.sh" in command or "protect-files.sh" in command:
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

    github_hooks = json.loads(read(TARGET_ROOT / ".github" / "hooks" / "hooks.json"))
    github_hook_text = json.dumps(github_hooks)
    check(".claude/hooks/scripts/" in github_hook_text, "GitHub hooks should invoke shared .claude hook scripts", errors)
    check("github-copilot" in github_hook_text, "GitHub hooks should pass target id", errors)

    claude_settings = json.loads(read(TARGET_ROOT / ".claude" / "settings.json"))
    claude_settings_text = json.dumps(claude_settings)
    check(".claude/hooks/scripts/" in claude_settings_text, "Claude settings should invoke shared .claude hook scripts", errors)
    check("claude-code" in claude_settings_text, "Claude hooks should pass target id", errors)

    validate_hook_guardrails(errors)
    validate_generated_scripts(errors)


def run_hook(script: Path, payload: dict[str, object], *args: str) -> tuple[int, str, str]:
    result = subprocess.run(
        [str(script), *args],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


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
            f'"permissionDecision": "{expected_decision}"' in stdout,
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
            '"permissionDecision": "deny"' in stdout,
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
            '"permissionDecision": "deny"' in stdout,
            f"protected-file guardrail did not deny Bash write to .env: {hook_root}",
            errors,
        )

        returncode, stdout, stderr = run_hook(
            hook_root / "git-protection.sh",
            {"tool_name": "Bash", "tool_input": {"command": "git reset --hard HEAD"}},
        )
        check(returncode == 0, f"git guardrail failed to run: {hook_root}: {stderr}", errors)
        check(
            '"permissionDecision": "deny"' in stdout,
            f"git guardrail did not deny git reset --hard: {hook_root}",
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
            f'"permissionDecision": "{expected_decision}"' in stdout,
            f"hook guardrail did not protect Bash hook edit with {expected_decision}: {script}",
            errors,
        )


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
    expected_skill_paths = {f"../.claude/skills/{path.parent.name}" for path in (REPO_ROOT / "shared" / "skills").glob("*/SKILL.md")}
    check(
        configured_skill_paths == expected_skill_paths,
        "Codex config must enable every shared .claude skill by relative path",
        errors,
    )

    forbidden_fragments = ("/home/ghisso", "/Users/", "BEGIN OPENSSH", "PRIVATE KEY")
    for relative_path in OBSOLETE_GENERATED_DIRS:
        check(
            not (TARGET_ROOT / relative_path).exists(),
            f"multi-agent must not generate obsolete target-local path: {relative_path}",
            errors,
        )
    for obsolete_target in OBSOLETE_TARGET_ROOTS:
        check(
            not (DIST_ROOT / obsolete_target).exists(),
            f"obsolete generated target directory must not exist: dist/{obsolete_target}",
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

    validate_support_files(errors)
    validate_generated_hygiene(errors)


def validate_support_files(errors: list[str]) -> None:
    required_files = (
        "MEMORY.md",
        "scripts/quality_score.py",
        "templates/session-log.md",
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
        "hooks/scripts/protect-files.sh",
        "hooks/scripts/git-protection.sh",
        "hooks/scripts/context-mode-dispatch.sh",
        "hooks/scripts/session-log.sh",
    )
    for target in TARGETS:
        support_root = target_support_root(target)
        for relative_path in required_files:
            path = support_root / relative_path
            check(path.exists(), f"{target} missing generated support file: {path}", errors)


def validate_generated_hygiene(errors: list[str]) -> None:
    for path in DIST_ROOT.rglob("*"):
        if path.name == "__pycache__" or path.suffix == ".pyc":
            errors.append(f"generated bytecode artifact must not be committed: {path}")


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


def main() -> int:
    errors: list[str] = []
    for target in TARGETS:
        check((DIST_ROOT / target).exists(), f"missing generated target: {target}", errors)
    for target in OBSOLETE_TARGET_ROOTS:
        check(not (DIST_ROOT / target).exists(), f"obsolete generated target still exists: {target}", errors)

    if not errors:
        validate_agents(errors)
        validate_model_leaks(errors)
        validate_mcp_and_hooks(errors)
        validate_skills_and_paths(errors)
        validate_determinism(errors)

    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1

    print("PASS generated target is structurally valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
