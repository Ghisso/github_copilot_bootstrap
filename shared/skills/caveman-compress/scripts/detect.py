#!/usr/bin/env python3
"""Detect whether a file is safe to caveman-compress."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

COMPRESSIBLE_EXTENSIONS = {".md", ".markdown", ".rst", ".txt"}

SKIP_EXTENSIONS = {
    ".bash",
    ".cfg",
    ".conf",
    ".css",
    ".csv",
    ".dockerfile",
    ".drawio",
    ".env",
    ".go",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".lock",
    ".lua",
    ".makefile",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".scss",
    ".sh",
    ".sql",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".xml",
    ".yaml",
    ".yml",
    ".zsh",
}

CODE_PATTERNS = [
    re.compile(r"^\s*(import |from .+ import |require\(|const |let |var )"),
    re.compile(r"^\s*(def |class |function |async function |export )"),
    re.compile(r"^\s*(if\s*\(|for\s*\(|while\s*\(|switch\s*\(|try\s*\{)"),
    re.compile(r"^\s*[\}\]\);]+\s*$"),
    re.compile(r"^\s*@\w+"),
    re.compile(r'^\s*"[^"]+"\s*:\s*'),
    re.compile(r"^\s*\w+\s*=\s*[\{\[\(\"']"),
]


@dataclass(slots=True)
class DetectionResult:
    """Outcome of a compression safety check."""

    path: str
    file_type: str
    compressible: bool
    reason: str


def _normalized_path(filepath: Path) -> str:
    return filepath.resolve().as_posix()


def _is_code_line(line: str) -> bool:
    return any(pattern.match(line) for pattern in CODE_PATTERNS)


def _is_json_content(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if not ((stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]"))):
        return False
    try:
        json.loads(text)
    except json.JSONDecodeError:
        return False
    return True


def _is_yaml_content(lines: list[str]) -> bool:
    yaml_indicators = 0
    non_empty_lines = 0

    for line in lines[:30]:
        stripped = line.strip()
        if not stripped:
            continue
        non_empty_lines += 1
        if stripped.startswith("---"):
            yaml_indicators += 1
        elif re.match(r"^\w[\w\s-]*:\s", stripped):
            yaml_indicators += 1
        elif stripped.startswith("- ") and ":" in stripped:
            yaml_indicators += 1

    if non_empty_lines == 0:
        return False
    return yaml_indicators / non_empty_lines > 0.6


def detect_file_type(filepath: Path) -> str:
    """Classify a file as natural language, code, config, or unknown."""

    extension = filepath.suffix.lower()

    if extension in COMPRESSIBLE_EXTENSIONS:
        return "natural_language"

    if extension in SKIP_EXTENSIONS:
        if extension in {".cfg", ".conf", ".env", ".ini", ".json", ".toml", ".yaml", ".yml"}:
            return "config"
        return "code"

    try:
        text = filepath.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return "unknown"

    if not extension:
        if _is_json_content(text[:10000]):
            return "config"
        lines = text.splitlines()[:50]
        if _is_yaml_content(lines):
            return "config"
        non_empty_lines = [line for line in lines if line.strip()]
        if non_empty_lines:
            code_lines = sum(1 for line in non_empty_lines if _is_code_line(line))
            if code_lines / len(non_empty_lines) > 0.4:
                return "code"
        return "natural_language"

    return "unknown"


def protected_reason(filepath: Path) -> str | None:
    """Return the protection reason when a file must never be compressed."""

    normalized = _normalized_path(filepath)

    if normalized.endswith(".original.md"):
        return "Backup files are never compressed."
    if normalized.endswith("/.github/copilot-instructions.md"):
        return "Workspace instructions are source-of-truth and must stay human-authored."
    if "/.github/instructions/" in normalized and normalized.endswith(".md"):
        return "Instruction files are source-of-truth and must keep exact structure."
    if "/.claude/skills/" in normalized and normalized.endswith("/SKILL.md"):
        return "Skill files must keep exact frontmatter and trigger phrases."
    if "/.github/agents/" in normalized and normalized.endswith(".agent.md"):
        return "Agent files must keep exact instructions and output contracts."
    return None


def inspect_path(filepath: Path) -> DetectionResult:
    """Inspect a path and decide whether caveman-compress may rewrite it."""

    resolved = filepath.resolve()

    if not resolved.exists():
        return DetectionResult(str(resolved), "unknown", False, "File not found.")

    if not resolved.is_file():
        return DetectionResult(str(resolved), "unknown", False, "Path is not a file.")

    protected = protected_reason(resolved)
    file_type = detect_file_type(resolved)
    if protected is not None:
        return DetectionResult(str(resolved), file_type, False, protected)

    if file_type != "natural_language":
        return DetectionResult(
            str(resolved),
            file_type,
            False,
            f"Only natural-language files can be compressed. Detected {file_type}.",
        )

    return DetectionResult(str(resolved), file_type, True, "Target is safe for caveman-compress.")


def should_compress(filepath: Path) -> bool:
    """Return True when the target passes all compression guardrails."""

    return inspect_path(filepath).compressible


def main(argv: list[str]) -> int:
    """CLI entry point."""

    if len(argv) not in {2, 3}:
        print("Usage: python detect.py <filepath> [--json]")
        return 1

    emit_json = "--json" in argv[1:]
    path_arg = next(argument for argument in argv[1:] if argument != "--json")
    result = inspect_path(Path(path_arg))

    if emit_json:
        print(json.dumps(asdict(result), indent=2))
    else:
        print(f"Path: {result.path}")
        print(f"Type: {result.file_type}")
        print(f"Compressible: {'yes' if result.compressible else 'no'}")
        print(f"Reason: {result.reason}")

    return 0 if result.compressible else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
