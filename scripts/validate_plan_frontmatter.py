#!/usr/bin/env python3
"""Validate bootstrap plan frontmatter."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence


# Resolved from the current working directory, not __file__: this module is
# shipped byte-for-byte into consumer runtimes at .claude/scripts/ (see
# scripts/generate_targets.py), where a __file__-relative parent index would
# resolve to .claude instead of the repository root. Every caller - the
# authoring `uv run python scripts/validate_plan_frontmatter.py` entrypoint,
# check_runtime.py's subprocess (cwd=REPO_ROOT), and the shipped git-hook
# invocation (`cd "$repo_root" && python3 ...`) - already runs from the
# repository root, matching verify.py's own `Path.cwd()` convention.
REPO_ROOT = Path.cwd()
BIG_PLAN_STATUSES = {"planning", "in-progress", "complete", "cancelled"}
SMALL_PLAN_STATUSES = {"planned", "in-progress", "paused", "complete", "cancelled"}
CANCELLED_FIELDS = ("cancelled_at", "cancelled_reason", "cancelled_evidence")
PAUSED_FIELDS = ("paused_at", "paused_reason", "pause_session_log")
CANCELLED_AT_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
PAUSED_AT_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
CANCELLED_REASON_BLOCK_PATTERN = re.compile(
    r"^[|>](?:[+-][1-9]?|[1-9][+-]?)?(?:[ \t]*#.*)?$"
)
PAUSED_REASON_BLOCK_PATTERN = re.compile(
    r"^[|>](?:[+-][1-9]?|[1-9][+-]?)?(?:[ \t]*#.*)?$"
)
CANCELLED_STATUS_PATTERN = re.compile(
    r"^\*\*Status:\*\*[ \t]+CANCELLED\b", re.MULTILINE
)
PAUSED_STATUS_PATTERN = re.compile(r"^\*\*Status:\*\*[ \t]+PAUSED\b", re.MULTILINE)
BODY_PHASE_ITEM_PATTERN = re.compile(
    r"^- (?:\[[ xX]\] )?`(?P<phase>[^`]+)`(?:[ \t]+(?:—|--|:|-|\().*)?$"
)
BODY_PHASE_HEADING_PATTERN = re.compile(
    r"^## (?:Phase|Phases|Phase Order)[ \t]*\n(?P<body>.*?)(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)
# See the canonical Knowledge-Refresh Final Phase rule in
# shared/policies/workflow.instructions.md. This suffix is how a big plan's
# own dedicated final knowledge-refresh phase is recognized; enforcing at
# most one, and only as the last phase, is what makes the rule's termination
# condition deterministic rather than a convention the planner could forget.
KNOWLEDGE_REFRESH_PHASE_SUFFIX = "-knowledge-refresh"
# See the canonical Verification Evidence Contract rule in
# shared/policies/workflow.instructions.md. Only a live small plan (never a
# completed or cancelled one) dated on or after this value is in scope, so a
# historical plan is never re-judged against a rule it predates.
VERIFICATION_CONTRACT_SINCE = "2026-09-19"
LIVE_SMALL_PLAN_STATUSES = {"planned", "in-progress", "paused"}
# Each pattern looks for a condition word, an availability word, and a
# check-running verb within a bounded span of the same sentence - not just
# any two of the three words anywhere in the file. Order matters: 1 and 2
# cover "when available, run" and "run when available" word orders; 3
# catches the "as time permits"/"optionally" idiom neither word order
# expresses. Measured against every plan in this repository before being
# fixed: a verb-anchored list flags 10 plans (7 genuine hedged checks); a
# bare phrase list flags 34, mostly ordinary prose.
HEDGED_VERIFICATION_PATTERNS = (
    re.compile(
        r"\b(?:when|if|where|once|whenever|provided|should)\b[^.\n]{0,60}"
        r"\b(?:available|possible|present|installed|exists|feasible|reachable|"
        r"configured|set up)\b[^.\n]{0,60}"
        r"\b(?:runs?|executes?|exercises?|smoke[- ]?(?:tests?|checks?)|checks?|"
        r"verify|verifies|tests?|probes?|re-probes?|confirms?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:runs?|executes?|exercises?|smoke[- ]?(?:tests?|checks?)|checks?|"
        r"verify|verifies|tests?|probes?|re-probes?|confirms?)\b[^.\n]{0,80}"
        r"\b(?:when|if|where|once|whenever|provided)\b[^.\n]{0,60}"
        r"\b(?:available|possible|present|installed|exists|feasible|reachable|"
        r"practical|configured|set up)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:as time permits|time permitting|optionally\s+"
        r"(?:runs?|executes?|verify|verifies|checks?))\b",
        re.IGNORECASE,
    ),
)
_FENCE_BLOCK_PATTERN = re.compile(
    r"^[ \t]*(?P<fence>`{3,}|~{3,})[^\n]*\r?\n.*?^[ \t]*(?P=fence)[ \t]*\r?$",
    re.MULTILINE | re.DOTALL,
)


def parse_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        return {}
    data: dict[str, Any] = {}
    current_key = ""
    for raw_line in parts[1].splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_key:
            value = data.get(current_key)
            if not isinstance(value, list):
                value = [] if value in (None, "") else [str(value)]
                data[current_key] = value
            value.append(line[4:].strip())
            continue
        if line.startswith((" ", "\t")) and current_key in {
            "cancelled_reason",
            "paused_reason",
        }:
            value = data.get(current_key)
            data[current_key] = [value, line.strip()]
            continue
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            current_key = key.strip()
            value = value.strip().strip('"').strip("'")
            data[current_key] = value
    return data


def frontmatter_key_count(path: Path, key: str) -> int:
    """Count top-level key occurrences in the hand-parsed frontmatter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return 0
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        return 0
    return sum(
        1
        for line in parts[1].splitlines()
        if not line.startswith((" ", "\t"))
        and ":" in line
        and line.split(":", 1)[0].strip() == key
    )


def require_fields(
    path: Path, data: dict[str, Any], fields: Sequence[str], errors: list[str]
) -> None:
    for field in fields:
        if field not in data or data[field] in ("", []):
            errors.append(f"{path}: missing required field: {field}")


def validate_cancellation(path: Path, data: dict[str, Any], errors: list[str]) -> None:
    """Validate the audit evidence required for a cancelled plan.

    This contract is intentionally implemented twice. The shipped copy is
    ``cancellation_validation_probe`` in
    ``shared/hooks/scripts/_lib-frontmatter.sh``, which enforces it at push time
    inside consumer repositories and therefore may depend on nothing but a stock
    ``python3``. This copy is authoring-repo-only tooling and never ships. A
    change to the timestamp, block-scalar, or evidence-status rules here must be
    mirrored there; the equality test below guards that.
    """
    require_fields(path, data, CANCELLED_FIELDS, errors)

    cancelled_at = str(data.get("cancelled_at", ""))
    if cancelled_at:
        if not CANCELLED_AT_PATTERN.fullmatch(cancelled_at):
            errors.append(
                f"{path}: cancelled_at must use UTC format YYYY-MM-DDTHH:MM:SSZ"
            )
        else:
            try:
                datetime.strptime(cancelled_at, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                errors.append(f"{path}: cancelled_at must be a valid UTC timestamp")

    reason = data.get("cancelled_reason")
    if reason not in (None, "", []):
        if not isinstance(reason, str) or not reason.strip():
            errors.append(
                f"{path}: cancelled_reason must be meaningful plain single-line prose"
            )
        elif CANCELLED_REASON_BLOCK_PATTERN.fullmatch(
            reason.strip()
        ) or reason.lstrip().startswith(("[", "{", "- ", "#")):
            errors.append(
                f"{path}: cancelled_reason must be a plain single-line scalar"
            )

    evidence_value = data.get("cancelled_evidence", "")
    if evidence_value in ("", []):
        return
    if not isinstance(evidence_value, str):
        errors.append(f"{path}: cancelled_evidence must be a plain path scalar")
        return
    try:
        evidence_path = Path(evidence_value)
        if evidence_path.is_absolute():
            errors.append(f"{path}: cancelled_evidence must be repository-relative")
            return
        repository_root = REPO_ROOT.resolve(strict=True)
        evidence_path = (repository_root / evidence_path).resolve(strict=False)
        if not evidence_path.is_relative_to(repository_root):
            errors.append(f"{path}: cancelled_evidence must stay inside the repository")
            return
        evidence_path = evidence_path.resolve(strict=True)
        if not evidence_path.is_file():
            errors.append(
                f"{path}: cancelled_evidence must be a regular readable text file"
            )
            return
        evidence = evidence_path.read_text(encoding="utf-8")
    except (OSError, RuntimeError, TypeError, UnicodeError, ValueError) as error:
        errors.append(
            f"{path}: cannot read cancelled_evidence {evidence_path}: {error}"
        )
        return
    if not CANCELLED_STATUS_PATTERN.search(evidence):
        errors.append(f"{path}: cancelled_evidence must contain **Status:** CANCELLED")


def validate_pause(path: Path, data: dict[str, Any], errors: list[str]) -> None:
    """Validate the audit evidence required for a paused small plan."""
    require_fields(path, data, PAUSED_FIELDS, errors)

    paused_at = str(data.get("paused_at", ""))
    if paused_at:
        if not PAUSED_AT_PATTERN.fullmatch(paused_at):
            errors.append(f"{path}: paused_at must use UTC format YYYY-MM-DDTHH:MM:SSZ")
        else:
            try:
                datetime.strptime(paused_at, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                errors.append(f"{path}: paused_at must be a valid UTC timestamp")

    reason = data.get("paused_reason")
    if reason not in (None, "", []):
        if not isinstance(reason, str) or not reason.strip():
            errors.append(
                f"{path}: paused_reason must be meaningful plain single-line prose"
            )
        elif PAUSED_REASON_BLOCK_PATTERN.fullmatch(
            reason.strip()
        ) or reason.lstrip().startswith(("[", "{", "- ", "#")):
            errors.append(f"{path}: paused_reason must be a plain single-line scalar")

    log_value = data.get("pause_session_log", "")
    if log_value in ("", []):
        return
    if not isinstance(log_value, str):
        errors.append(f"{path}: pause_session_log must be a plain path scalar")
        return
    try:
        log_path = Path(log_value)
        if log_path.is_absolute():
            errors.append(f"{path}: pause_session_log must be repository-relative")
            return
        repository_root = REPO_ROOT.resolve(strict=True)
        log_path = (repository_root / log_path).resolve(strict=False)
        if not log_path.is_relative_to(repository_root):
            errors.append(f"{path}: pause_session_log must stay inside the repository")
            return
        log_path = log_path.resolve(strict=True)
        if not log_path.is_file():
            errors.append(
                f"{path}: pause_session_log must be a regular readable text file"
            )
            return
        log = log_path.read_text(encoding="utf-8")
    except (OSError, RuntimeError, TypeError, UnicodeError, ValueError) as error:
        errors.append(f"{path}: cannot read pause_session_log {log_path}: {error}")
        return
    if not PAUSED_STATUS_PATTERN.search(log):
        errors.append(f"{path}: pause_session_log must contain **Status:** PAUSED")


def validate_knowledge_refresh_phase_position(
    path: Path, phases: list[str], errors: list[str]
) -> None:
    """A knowledge-refresh phase must be unique and last, so it cannot recur."""
    refresh_phases = [
        phase for phase in phases if phase.endswith(KNOWLEDGE_REFRESH_PHASE_SUFFIX)
    ]
    if len(refresh_phases) > 1:
        errors.append(
            f"{path}: at most one knowledge-refresh phase is allowed, "
            f"found {len(refresh_phases)}"
        )
    elif refresh_phases and phases[-1] != refresh_phases[0]:
        errors.append(
            f"{path}: the knowledge-refresh phase must be the last phase in phases"
        )


def validate_big_plan(path: Path, data: dict[str, Any], errors: list[str]) -> None:
    require_fields(
        path,
        data,
        [
            "name",
            "type",
            "status",
            "originating_branch",
            "implementation_branch",
            "phases",
        ],
        errors,
    )
    status = str(data.get("status", ""))
    if status not in BIG_PLAN_STATUSES:
        errors.append(f"{path}: invalid status for big-plan: {status}")
    if status in {"in-progress", "complete"}:
        require_fields(path, data, ["started_at"], errors)
    if status == "in-progress":
        require_fields(path, data, ["current_phase"], errors)
    if status == "cancelled":
        validate_cancellation(path, data, errors)
    if not isinstance(data.get("phases"), list) or not data.get("phases"):
        errors.append(f"{path}: phases must be a non-empty list")
        return
    if all(isinstance(phase, str) for phase in data["phases"]):
        validate_knowledge_refresh_phase_position(path, data["phases"], errors)
    body = path.read_text(encoding="utf-8").split("---\n", 2)
    if len(body) != 3:
        return
    for phase_section in BODY_PHASE_HEADING_PATTERN.finditer(body[2]):
        section = phase_section.group("body")
        body_phases: list[str] = []
        malformed = False
        for line in section.splitlines():
            match = BODY_PHASE_ITEM_PATTERN.fullmatch(line)
            if match is not None:
                body_phases.append(match.group("phase"))
            elif line.startswith("- [") and "`" in line:
                malformed = True
        if not body_phases and not malformed:
            continue
        if (
            malformed
            or len(body_phases) != len(set(body_phases))
            or any(
                not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", phase)
                for phase in body_phases
            )
        ):
            errors.append(f"{path}: body phase inventory is malformed")
        elif body_phases != data["phases"]:
            errors.append(f"{path}: body phase inventory must match frontmatter phases")


def plan_verification_items(text: str) -> tuple[list[str], list[str]]:
    """Extract required and optional verification items from a plan's text.

    Required items are normalized shell commands from every fenced code
    block opened with ``bash`` or ``sh`` under the ``## Verification``
    heading. Optional items are the top-level ``- `` bullets under the
    ``## Optional Verification`` heading, with indented continuation lines
    joined in; fenced code blocks in that section are ignored. Each H2
    section runs from its own heading to the next ``^## `` heading or the
    end of the text; a missing section yields an empty list.

    Mirrored byte-for-byte between ``scripts/validate_plan_frontmatter.py``
    and ``shared/scripts/verify.py`` (an equality test in both suites
    guards drift); neither file may import the other, so both copies stay
    stdlib-only and self-contained.
    """

    def section_body(heading: str) -> str | None:
        match = re.search(
            rf"^## {re.escape(heading)}[ \t]*\r?\n(?P<body>.*?)(?=^## |\Z)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        return match.group("body") if match is not None else None

    def normalize(line: str) -> str:
        # Quote-aware scan: a "#" only opens a trailing comment when it is
        # whitespace-bounded on both sides and outside any open quote span,
        # so `git commit -m "Fix bug # 123"` is never truncated mid-string.
        # A backslash only escapes a quote inside a double-quoted span,
        # matching POSIX shell quoting; single quotes have no escape.
        quote = ""
        cut = len(line)
        index = 0
        while index < len(line):
            char = line[index]
            if quote:
                if quote == '"' and char == "\\" and index + 1 < len(line):
                    index += 2
                    continue
                if char == quote:
                    quote = ""
                index += 1
                continue
            if char in "'\"":
                quote = char
                index += 1
                continue
            if (
                char == "#"
                and index > 0
                and line[index - 1].isspace()
                and index + 1 < len(line)
                and line[index + 1].isspace()
            ):
                cut = index
                break
            index += 1
        return re.sub(r"\s+", " ", line[:cut]).strip()

    required: list[str] = []
    verification_body = section_body("Verification")
    if verification_body is not None:
        for fence in re.finditer(
            r"^[ \t]*(?P<mark>`{3,}|~{3,})[ \t]*(?P<lang>\S*)[ \t]*\r?\n"
            r"(?P<body>.*?)^[ \t]*(?P=mark)[ \t]*\r?$",
            verification_body,
            re.MULTILINE | re.DOTALL,
        ):
            if fence.group("lang") not in ("bash", "sh"):
                continue
            joined: list[str] = []
            buffer = ""
            for raw_line in fence.group("body").split("\n"):
                buffer += raw_line
                if buffer.endswith("\\"):
                    buffer = buffer[:-1]
                    continue
                joined.append(buffer)
                buffer = ""
            if buffer:
                joined.append(buffer)
            for line in joined:
                if line.lstrip()[:1] == "#":
                    continue
                item = normalize(line)
                if item:
                    required.append(item)

    optional: list[str] = []
    optional_body = section_body("Optional Verification")
    if optional_body is not None:
        stripped: list[str] = []
        in_fence = False
        for raw_line in optional_body.split("\n"):
            if re.match(r"^[ \t]*(?:`{3,}|~{3,})", raw_line):
                in_fence = not in_fence
                continue
            if not in_fence:
                stripped.append(raw_line)
        for bullet in re.finditer(
            r"^- [ \t]*(?P<rest>.*(?:\n[ \t]+\S.*)*)",
            "\n".join(stripped),
            re.MULTILINE,
        ):
            item = re.sub(r"\s+", " ", bullet.group("rest")).strip()
            if item:
                optional.append(item)

    return required, optional


def _names_closeout(item: str) -> bool:
    """Return whether a normalized item's text names ``verify.py closeout``.

    Strips quote characters first so ``verify.py "closeout"``,
    ``clos""eout``, or ``--format json closeout`` (mode given after
    options) cannot hide the nesting from a literal substring match.

    ponytail: this cannot see through a ``$VAR`` shell expansion that only
    resolves to "closeout" at runtime - bash still executes it, and the
    resulting recursive ``verify.py closeout`` run fails on the same plan
    it is trying to close out, which is a loud failure, not a silent pass.
    """
    stripped = item.replace("'", "").replace('"', "")
    return re.search(r"verify\.py\b.*\bcloseout\b", stripped) is not None


def _mask_span(text: str, start: int, end: int) -> str:
    """Blank a text span with same-length spaces, preserving line numbers."""
    return text[:start] + re.sub(r"[^\n]", " ", text[start:end]) + text[end:]


def _hedge_scan_text(text: str) -> str:
    """Return plan text with fenced code blocks and the ``## Optional
    Verification`` body blanked out, so a real command or an intentionally
    conditional optional check can never itself be mistaken for a hedge.
    Blanking (not deleting) keeps every remaining line number identical to
    the source file's, including HTML comments, which stay in scope: a
    hedge hidden inside one is still a hedge.
    """
    masked = text
    for fence in _FENCE_BLOCK_PATTERN.finditer(text):
        masked = _mask_span(masked, fence.start(), fence.end())
    optional_match = re.search(
        r"^## Optional Verification[ \t]*\r?\n(?P<body>.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if optional_match is not None:
        masked = _mask_span(masked, *optional_match.span("body"))
    return masked


def validate_verification_contract(
    path: Path, data: dict[str, Any], text: str, errors: list[str]
) -> None:
    """Enforce the mandatory, machine-run ``## Verification`` block.

    Applies only to a live small plan (``planned``, ``in-progress``, or
    ``paused``) dated on or after ``VERIFICATION_CONTRACT_SINCE`` (or
    undated). Never reads Git state and never parses step-level bullets for
    items - only the plan's own ``## Verification``/``## Optional
    Verification`` H2 sections, via ``plan_verification_items``.
    """
    if str(data.get("type", "")) != "small-plan":
        return
    if str(data.get("status", "")) not in LIVE_SMALL_PLAN_STATUSES:
        return
    date_match = re.match(r"^(\d{4}-\d{2}-\d{2})_", path.name)
    if date_match is not None and date_match.group(1) < VERIFICATION_CONTRACT_SINCE:
        return

    required, _optional = plan_verification_items(text)
    heading_match = re.search(r"^## Verification[ \t]*\r?\n", text, re.MULTILINE)
    heading_line = (
        text.count("\n", 0, heading_match.start()) + 1 if heading_match else 1
    )

    if not required:
        errors.append(
            f"{path}:{heading_line}: L1 verification-block-missing: no "
            "bash/sh fenced block under ## Verification; add the block "
            "with the required commands"
        )
    for item in required:
        # Quote characters can hide "|| true"/"verify.py closeout" from a
        # literal substring check (see _names_closeout), so both L3 and L4
        # scan the same quote-stripped form.
        quote_stripped_item = item.replace("'", "").replace('"', "")
        if re.search(r"\|\|\s*(?:true|:)(?![\w-])", quote_stripped_item):
            errors.append(
                f"{path}:{heading_line}: L3 unfailable-verification: "
                f'"{item}" can never fail; remove the fallback'
            )
        if _names_closeout(item):
            errors.append(
                f'{path}:{heading_line}: L4 self-listed-closeout: "{item}" '
                "lists closeout, which runs the block itself; remove it"
            )

    hedge_text = _hedge_scan_text(text)
    for pattern in HEDGED_VERIFICATION_PATTERNS:
        match = pattern.search(hedge_text)
        if match is not None:
            line = hedge_text.count("\n", 0, match.start()) + 1
            errors.append(
                f'{path}:{line}: L2 hedged-verification: "{match.group(0)}"; '
                "drop the condition, or move the check under ## Optional "
                "Verification"
            )
            break


def validate_small_plan(
    path: Path, data: dict[str, Any], text: str, errors: list[str]
) -> None:
    require_fields(
        path, data, ["name", "type", "parent_plan", "phase_index", "status"], errors
    )
    status = str(data.get("status", ""))
    if status not in SMALL_PLAN_STATUSES:
        errors.append(f"{path}: invalid status for small-plan: {status}")
    if status == "complete":
        require_fields(path, data, ["closeout_session_log"], errors)
    if status == "cancelled":
        validate_cancellation(path, data, errors)
    if status == "paused":
        validate_pause(path, data, errors)
    validate_verification_contract(path, data, text, errors)


def validate_plan(path: Path, errors: list[str]) -> None:
    data = parse_frontmatter(path)
    if frontmatter_key_count(path, "status") > 1:
        errors.append(f"{path}: duplicate status fields are not allowed")
        return
    plan_type = str(data.get("type", ""))
    if plan_type == "big-plan":
        validate_big_plan(path, data, errors)
    elif plan_type == "small-plan":
        text = path.read_text(encoding="utf-8")
        validate_small_plan(path, data, text, errors)
    else:
        errors.append(f"{path}: type must be big-plan or small-plan")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Plan files to validate.")
    args = parser.parse_args()

    if args.paths:
        paths = args.paths
    else:
        plan_root = REPO_ROOT / ".claude" / "plans"
        if not plan_root.exists():
            return 0
        paths = sorted(plan_root.glob("*.md"))

    errors: list[str] = []
    for path in paths:
        if path.name == "README.md":
            continue
        validate_plan(path, errors)

    for error in errors:
        print(f"FAIL {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
