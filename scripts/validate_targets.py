#!/usr/bin/env python3
"""Validate generated target outputs."""

from __future__ import annotations

import filecmp
import json
import py_compile
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = REPO_ROOT / "dist"
TARGETS = ("github-copilot", "claude-code", "openai-codex")
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
CODEX_BAD_REVIEW_HELPERS = (
    "review-pass-codex-primary-primary",
    "review-pass-codex-primary-adversarial",
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
    ".instructions.md",
)
CODEX_REVIEW_NAME_MAP = {
    "review-pass-codex": "review-pass-codex-primary",
    "review-pass-sonnet": "review-pass-codex-adversarial",
}


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
    if target == "github-copilot":
        return DIST_ROOT / target / ".github"
    if target == "claude-code":
        return DIST_ROOT / target / ".claude"
    if target == "openai-codex":
        return DIST_ROOT / target / ".codex"
    raise ValueError(f"unknown target: {target}")


def compare_dirs(left: Path, right: Path, errors: list[str]) -> None:
    comparison = filecmp.dircmp(left, right)
    if comparison.left_only or comparison.right_only or comparison.diff_files or comparison.funny_files:
        errors.append(
            "generated dist is not deterministic; rerun scripts/generate_targets.py --all"
        )
        return
    for name in comparison.common_dirs:
        compare_dirs(left / name, right / name, errors)


def validate_agents(errors: list[str]) -> None:
    shared_agents = sorted((REPO_ROOT / "shared" / "agents").glob("*/agent.yaml"))
    legacy_agents = sorted((REPO_ROOT / ".github" / "agents").glob("*.agent.md"))
    check(len(shared_agents) == len(legacy_agents) == 17, "expected 17 shared and legacy agents", errors)

    for metadata_path in shared_agents:
        data = json.loads(read(metadata_path))
        agent_id = data["id"]
        for target in TARGETS:
            check(
                target in data.get("targets", {}),
                f"{agent_id} missing target metadata for {target}",
                errors,
            )
            target_file = metadata_path.parent / data["targets"].get(target, "")
            check(target_file.exists(), f"{agent_id} missing target override: {target}", errors)
            if target == "openai-codex":
                check(
                    target_file.suffix == ".md",
                    f"{agent_id} Codex target override should be an agent instruction body, not rules: {target_file}",
                    errors,
                )

    for legacy_path in legacy_agents:
        generated = DIST_ROOT / "github-copilot" / ".github" / "agents" / legacy_path.name
        check(generated.exists(), f"missing generated GitHub agent: {legacy_path.name}", errors)
        if generated.exists() and read(generated) != read(legacy_path):
            errors.append(f"GitHub agent metadata/body changed unexpectedly: {legacy_path.name}")

    claude_agents = sorted((DIST_ROOT / "claude-code" / ".claude" / "agents").glob("*.md"))
    check(len(claude_agents) == 17, "expected 17 Claude Code subagent files", errors)
    for path in claude_agents:
        text = read(path)
        check(text.startswith("---\n"), f"Claude agent missing frontmatter: {path}", errors)
        check("\nname: " in text and "\ndescription: " in text, f"Claude agent missing required fields: {path}", errors)

    codex_agents = sorted((DIST_ROOT / "openai-codex" / ".codex" / "agents").glob("*.toml"))
    check(len(codex_agents) == 17, "expected 17 Codex custom agent TOML files", errors)
    check(
        not (DIST_ROOT / "openai-codex" / ".codex" / "rules").exists(),
        "Codex target must not generate deprecated .codex/rules output",
        errors,
    )

    expected_codex_names = {
        CODEX_REVIEW_NAME_MAP.get(json.loads(read(path))["id"], json.loads(read(path))["id"])
        for path in shared_agents
    }
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
        for helper_name in CODEX_BAD_REVIEW_HELPERS:
            check(helper_name not in text, f"invalid Codex review helper name in {path}: {helper_name}", errors)

    for root in (
        DIST_ROOT / "claude-code" / ".claude" / "agents",
        DIST_ROOT / "openai-codex" / ".codex" / "agents",
    ):
        for path in text_files(root):
            text = read(path)
            for label in NON_COPILOT_REVIEW_LABEL_LEAKS:
                check(label not in text, f"non-Copilot review helper label leaked into {path}: {label}", errors)

    validate_github_agent_models(errors)


def validate_github_agent_models(errors: list[str]) -> None:
    agent_root = DIST_ROOT / "github-copilot" / ".github" / "agents"
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
    for target in ("claude-code", "openai-codex"):
        for path in text_files(DIST_ROOT / target):
            text = read(path)
            for pin in COPILOT_MODEL_PINS:
                if pin in text:
                    errors.append(f"Copilot model pin leaked into {target}: {path} contains {pin}")


def validate_mcp_and_hooks(errors: list[str]) -> None:
    github_mcp = json.loads(read(DIST_ROOT / "github-copilot" / ".vscode" / "mcp.json"))
    claude_mcp = json.loads(read(DIST_ROOT / "claude-code" / ".mcp.json"))
    for server in ("semble", "context-mode"):
        check(server in github_mcp.get("servers", {}), f"github missing MCP server: {server}", errors)
        check(server in claude_mcp.get("mcpServers", {}), f"claude missing MCP server: {server}", errors)
    check("servers" not in claude_mcp, "Claude .mcp.json must use mcpServers, not servers", errors)

    codex_config = read(DIST_ROOT / "openai-codex" / ".codex" / "config.toml")
    try:
        read_toml(DIST_ROOT / "openai-codex" / ".codex" / "config.toml")
    except tomllib.TOMLDecodeError as error:
        errors.append(f"invalid Codex config TOML: {error}")
    check("[features]" in codex_config, "Codex config missing features section", errors)
    check("codex_hooks = true" in codex_config, "Codex config must enable codex_hooks", errors)
    check("[agents]" in codex_config, "Codex config missing agents section", errors)
    check("max_depth = 1" in codex_config, "Codex config must cap agent nesting depth", errors)
    check("[mcp_servers.semble]" in codex_config, "Codex config missing Semble MCP server", errors)
    check("[mcp_servers.context-mode]" in codex_config, "Codex config missing context-mode MCP server", errors)

    codex_hooks = json.loads(read(DIST_ROOT / "openai-codex" / ".codex" / "hooks.json"))
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

    hook_roots = (
        DIST_ROOT / "github-copilot" / ".github" / "hooks" / "scripts",
        DIST_ROOT / "claude-code" / ".claude" / "hooks" / "scripts",
        DIST_ROOT / "openai-codex" / ".codex" / "hooks" / "scripts",
    )
    for hook_root in hook_roots:
        for script in REQUIRED_HOOK_SCRIPTS:
            path = hook_root / script
            check(path.exists(), f"missing hook script: {path}", errors)
            check(path.exists() and path.stat().st_mode & 0o111, f"hook script is not executable: {path}", errors)

    validate_hook_guardrails(errors)
    validate_generated_scripts(errors)


def run_hook(script: Path, payload: dict[str, object]) -> tuple[int, str, str]:
    result = subprocess.run(
        [str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def validate_hook_guardrails(errors: list[str]) -> None:
    hook_cases = (
        (
            DIST_ROOT / "github-copilot" / ".github" / "hooks" / "scripts" / "protect-files.sh",
            ".github/hooks/hooks.json",
            "ask",
        ),
        (
            DIST_ROOT / "claude-code" / ".claude" / "hooks" / "scripts" / "protect-files.sh",
            ".claude/settings.json",
            "ask",
        ),
        (
            DIST_ROOT / "openai-codex" / ".codex" / "hooks" / "scripts" / "protect-files.sh",
            ".codex/hooks.json",
            "deny",
        ),
    )
    for script, protected_path, expected_decision in hook_cases:
        patch = f"*** Begin Patch\n*** Update File: {protected_path}\n@@\n x\n*** End Patch\n"
        returncode, stdout, stderr = run_hook(
            script,
            {"tool_name": "apply_patch", "tool_input": {"command": patch}},
        )
        check(returncode == 0, f"hook guardrail failed to run: {script}: {stderr}", errors)
        check(
            f'"permissionDecision": "{expected_decision}"' in stdout,
            f"hook guardrail did not protect {protected_path} with {expected_decision}: {script}",
            errors,
        )

    for hook_root in (
        DIST_ROOT / "github-copilot" / ".github" / "hooks" / "scripts",
        DIST_ROOT / "claude-code" / ".claude" / "hooks" / "scripts",
        DIST_ROOT / "openai-codex" / ".codex" / "hooks" / "scripts",
    ):
        returncode, stdout, stderr = run_hook(
            hook_root / "protect-files.sh",
            {"tool_name": "Write", "tool_input": {"path": ".env"}},
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
            DIST_ROOT / "github-copilot" / ".github" / "hooks" / "scripts" / "protect-files.sh",
            "cat > .github/hooks/hooks.json",
            "ask",
        ),
        (
            DIST_ROOT / "claude-code" / ".claude" / "hooks" / "scripts" / "protect-files.sh",
            "cat > .claude/settings.json",
            "ask",
        ),
        (
            DIST_ROOT / "openai-codex" / ".codex" / "hooks" / "scripts" / "protect-files.sh",
            "cat > .codex/hooks.json",
            "deny",
        ),
    )
    for script, command, expected_decision in bash_hook_cases:
        returncode, stdout, stderr = run_hook(
            script,
            {"tool_name": "Bash", "tool_input": {"command": command}},
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
    check(shared_skill_count == 52, f"expected 52 shared skills, found {shared_skill_count}", errors)
    for target, skill_root in (
        ("github-copilot", DIST_ROOT / "github-copilot" / ".github" / "skills"),
        ("claude-code", DIST_ROOT / "claude-code" / ".claude" / "skills"),
        ("openai-codex", DIST_ROOT / "openai-codex" / ".agents" / "skills"),
    ):
        count = count_skills(skill_root)
        check(count == shared_skill_count, f"{target} skill count mismatch: {count}", errors)
    check(
        not (DIST_ROOT / "openai-codex" / ".codex" / "skills").exists(),
        "Codex skills must be generated under .agents/skills, not .codex/skills",
        errors,
    )

    shared_prompts = sorted((REPO_ROOT / "shared" / "prompts").glob("*.prompt.md"))
    generated_prompts = sorted((DIST_ROOT / "github-copilot" / ".github" / "prompts").glob("*.prompt.md"))
    check(
        [path.name for path in generated_prompts] == [path.name for path in shared_prompts],
        "GitHub prompt output must mirror shared/prompts",
        errors,
    )
    for source in shared_prompts:
        generated = DIST_ROOT / "github-copilot" / ".github" / "prompts" / source.name
        check(generated.exists() and read(generated) == read(source), f"generated prompt differs from source: {source.name}", errors)

    forbidden_fragments = ("/home/ghisso", "/Users/", "BEGIN OPENSSH", "PRIVATE KEY")
    for target in TARGETS:
        for path in text_files(DIST_ROOT / target):
            text = read(path)
            for fragment in forbidden_fragments:
                if fragment in text:
                    errors.append(f"forbidden fragment in generated file: {path} contains {fragment}")

    for target in ("claude-code", "openai-codex"):
        for path in text_files(DIST_ROOT / target):
            if "hooks" in path.parts and "scripts" in path.parts:
                continue
            text = read(path)
            for fragment in NON_COPILOT_PATH_LEAKS:
                if fragment in text:
                    errors.append(f"Copilot path leaked into {target}: {path} contains {fragment}")

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

    print("PASS generated targets are structurally valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
