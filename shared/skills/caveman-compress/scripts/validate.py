#!/usr/bin/env python3
"""Validate caveman-compressed markdown for protected structure regressions."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

CODE_BLOCK_REGEX = re.compile(r"```.*?```", re.DOTALL)
FRONTMATTER_REGEX = re.compile(r"\A---\n.*?\n---\n?", re.DOTALL)
HEADING_REGEX = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
INLINE_CODE_REGEX = re.compile(r"`[^`\n]+`")
URL_REGEX = re.compile(r"https?://[^\s)]+")
PATH_REGEX = re.compile(
    r"(?:\./|\.\./|/|[A-Za-z]:\\)[\w\-/\\\.]+|[\w\-.]+[/\\][\w\-/\\\.]+"
)
BULLET_REGEX = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)


@dataclass(slots=True)
class ValidationResult:
    """Structured validation result."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


def _extract_frontmatter(text: str) -> str | None:
    match = FRONTMATTER_REGEX.match(text)
    if match is None:
        return None
    return match.group(0)


def _extract_headings(text: str) -> list[tuple[str, str]]:
    return [(level, title.strip()) for level, title in HEADING_REGEX.findall(text)]


def _extract_code_blocks(text: str) -> list[str]:
    return CODE_BLOCK_REGEX.findall(text)


def _remove_code_blocks(text: str) -> str:
    return CODE_BLOCK_REGEX.sub("", text)


def _extract_inline_code(text: str) -> list[str]:
    return INLINE_CODE_REGEX.findall(_remove_code_blocks(text))


def _extract_urls(text: str) -> set[str]:
    return set(URL_REGEX.findall(text))


def _extract_paths(text: str) -> set[str]:
    return set(PATH_REGEX.findall(text))


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2
    )


def _table_signature(block: list[str]) -> tuple[int, ...]:
    column_counts: list[int] = []
    for line in block:
        cells = [cell for cell in line.strip().strip("|").split("|")]
        column_counts.append(len(cells))
    return tuple(column_counts)


def _extract_table_signatures(text: str) -> list[tuple[int, ...]]:
    signatures: list[tuple[int, ...]] = []
    current_block: list[str] = []

    for line in text.splitlines():
        if _is_table_line(line):
            current_block.append(line)
            continue
        if current_block:
            signatures.append(_table_signature(current_block))
            current_block = []

    if current_block:
        signatures.append(_table_signature(current_block))

    return signatures


def _count_bullets(text: str) -> int:
    return len(BULLET_REGEX.findall(text))


def validate_text(original: str, compressed: str) -> ValidationResult:
    """Validate a compressed markdown document against the original."""

    result = ValidationResult()

    original_frontmatter = _extract_frontmatter(original)
    compressed_frontmatter = _extract_frontmatter(compressed)
    if original_frontmatter != compressed_frontmatter:
        result.add_error("YAML frontmatter changed; preserve it exactly.")

    if _extract_headings(original) != _extract_headings(compressed):
        result.add_error(
            "Markdown headings changed; preserve heading text and order exactly."
        )

    if _extract_code_blocks(original) != _extract_code_blocks(compressed):
        result.add_error("Code blocks changed; preserve them exactly.")

    if _extract_inline_code(original) != _extract_inline_code(compressed):
        result.add_error("Inline code changed; preserve it exactly.")

    original_urls = _extract_urls(original)
    compressed_urls = _extract_urls(compressed)
    if original_urls != compressed_urls:
        result.add_error(
            f"URLs changed: lost={sorted(original_urls - compressed_urls)}, added={sorted(compressed_urls - original_urls)}"
        )

    if _extract_table_signatures(original) != _extract_table_signatures(compressed):
        result.add_error("Markdown table structure changed.")

    original_paths = _extract_paths(original)
    compressed_paths = _extract_paths(compressed)
    if original_paths != compressed_paths:
        result.add_warning(
            f"File paths changed: lost={sorted(original_paths - compressed_paths)}, added={sorted(compressed_paths - original_paths)}"
        )

    original_bullets = _count_bullets(original)
    compressed_bullets = _count_bullets(compressed)
    if original_bullets:
        diff_ratio = abs(original_bullets - compressed_bullets) / original_bullets
        if diff_ratio > 0.15:
            result.add_warning(
                f"Bullet count changed significantly: {original_bullets} -> {compressed_bullets}"
            )

    return result


def validate(original_path: Path, compressed_path: Path) -> ValidationResult:
    """Validate two files from disk."""

    original_text = original_path.read_text(encoding="utf-8", errors="ignore")
    compressed_text = compressed_path.read_text(encoding="utf-8", errors="ignore")
    return validate_text(original_text, compressed_text)


def main(argv: list[str]) -> int:
    """CLI entry point."""

    if len(argv) != 3:
        print("Usage: python validate.py <original> <compressed>")
        return 1

    result = validate(Path(argv[1]).resolve(), Path(argv[2]).resolve())
    print(f"Valid: {result.is_valid}")

    if result.errors:
        print("Errors:")
        for error in result.errors:
            print(f"  - {error}")

    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    return 0 if result.is_valid else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
