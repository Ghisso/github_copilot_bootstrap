#!/usr/bin/env python3
"""Check runtime wiring for the generated bootstrap target."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

from runtime_ownership import (
    RESTORABLE_ROOT_PATHS,
    TRACKED_AUTHORING_PATHS,
    bootstrap_root_paths,
    install_mode_from_manifest,
    is_consumer_state_path,
    is_root_adapter_path,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = REPO_ROOT / "dist"
OPTIONAL_BINARIES = ("context-mode", "npx", "uv", "uvx", "hf", "gh")
REQUIRED_FILES = (
    "dist/multi-agent/.devcontainer/devcontainer.json",
    "dist/multi-agent/.devcontainer/Dockerfile",
    "dist/multi-agent/.devcontainer/post-start.sh",
    "dist/multi-agent/.devcontainer/state-sync.sh",
    "dist/multi-agent/.devcontainer/restore-root-adapters.sh",
    "dist/multi-agent/.claude/hooks/scripts/state-sync.sh",
    "dist/multi-agent/.claude/hooks/scripts/context-mode-dispatch.sh",
    "dist/multi-agent/.claude/hooks/scripts/claude-stop.sh",
    "dist/multi-agent/.claude/hooks/scripts/codex-stop.sh",
    "dist/multi-agent/.claude/hooks/scripts/restore-root-adapters.sh",
    "dist/multi-agent/.vscode/mcp.json",
    "dist/multi-agent/.github/hooks/hooks.json",
    "dist/multi-agent/.mcp.json",
    "dist/multi-agent/.claude/settings.json",
    "dist/multi-agent/.codex/config.toml",
    "dist/multi-agent/.codex/hooks.json",
    "dist/multi-agent/.claude/skills/ponytail/SKILL.md",
    "dist/multi-agent/.claude/skills/ponytail-review/SKILL.md",
    "dist/multi-agent/.claude/third_party/ponytail/LICENSE",
    "dist/multi-agent/.claude/third_party/ponytail/UPSTREAM.md",
    "dist/multi-agent/.claude/scripts/verify.py",
)
REQUIRED_DIRS = (
    "dist/multi-agent/.codex/agents",
    "dist/multi-agent/.github/agents",
    "dist/multi-agent/.claude/agents",
    "dist/multi-agent/.claude/skills",
    "dist/multi-agent/.claude/review-profiles",
    "dist/multi-agent/.claude/hooks/scripts",
)
# The dogfood drift check compares this checkout against its own generated
# output, so the repair is always a self-refresh. `--allow-self` is required:
# without it the installer rejects the overlapping source and target.
REINSTALL_COMMAND = "uv run python scripts/generate_targets.py --all && uv run python scripts/install_bootstrap.py . --allow-self --local-only"
PROJECT_PLACEHOLDER = "**Project:** [TODO: project name and one-liner description]"


def drift_diagnostic(relative_path: str, authoritative_source: str) -> str:
    """Describe a stale dogfood path and the exact safe repair workflow."""
    return (
        f"stale runtime path: {relative_path}; authoritative source: {authoritative_source}; "
        f"regenerate and reinstall: {REINSTALL_COMMAND}"
    )


def same_bytes(left: Path, right: Path) -> bool:
    """Return whether two files have identical content."""
    return (
        left.is_file() and right.is_file() and left.read_bytes() == right.read_bytes()
    )


def normalize_documented_substitutions(text: str, repo_root: Path) -> str:
    """Undo only the installer substitutions intentionally unique to a consumer."""
    return text.replace(f"**Project:** {repo_root.name}", PROJECT_PLACEHOLDER)


def is_exact_tracked(repo_root: Path, relative_path: Path) -> bool:
    """Return whether Git tracks exactly ``relative_path`` in ``repo_root``."""
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "ls-files",
            "--error-unmatch",
            "--",
            relative_path.as_posix(),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    return relative_path.as_posix() in result.stdout.splitlines()


def parity_matches(path: Path, authoritative_path: Path, repo_root: Path) -> bool:
    """Compare a bootstrap-controlled file after documented substitutions."""
    if not path.is_file():
        return False
    if same_bytes(path, authoritative_path):
        return True
    # The installer substitutes the project name into every file carrying the
    # placeholder, not just workspace.instructions.md. Byte-comparing those
    # reported permanent drift no self-refresh could ever clear.
    try:
        actual = normalize_documented_substitutions(
            path.read_text(encoding="utf-8"), repo_root
        )
        expected = (
            authoritative_path.read_text(encoding="utf-8")
            if authoritative_path.is_file()
            else ""
        )
    except (OSError, UnicodeDecodeError):
        return False
    return actual == expected


def runtime_drift_errors(
    repo_root: Path = REPO_ROOT, target_root: Path | None = None
) -> list[str]:
    """Return read-only dogfood parity failures without examining consumer state."""
    target_root = target_root or repo_root / "dist" / "multi-agent"
    errors: list[str] = []

    for authoring_relative in TRACKED_AUTHORING_PATHS:
        path = repo_root / authoring_relative
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        required_fragments: tuple[str, ...] = ("review -> closeout",)
        if authoring_relative == "AGENTS.md":
            required_fragments += ("source of truth lives in `shared/`",)
        if any(fragment not in text.lower() for fragment in required_fragments):
            errors.append(
                drift_diagnostic(
                    authoring_relative, "shared/policies/workflow.instructions.md"
                )
            )

    manifest = repo_root / ".claude" / "bootstrap-ownership.env"
    install_mode: bool | None = None
    valid_ownership_manifest = False
    if manifest.is_file():
        try:
            manifest_text = manifest.read_text(encoding="utf-8")
        except OSError:
            errors.append(
                drift_diagnostic(
                    ".claude/bootstrap-ownership.env",
                    "valid installer ownership manifest",
                )
            )
        else:
            install_mode = install_mode_from_manifest(manifest_text)
            valid_ownership_manifest = install_mode is not None
            if not valid_ownership_manifest:
                errors.append(
                    drift_diagnostic(
                        ".claude/bootstrap-ownership.env",
                        "valid installer ownership manifest",
                    )
                )
    active_bootstrap_paths = tuple(
        Path(path) for path in bootstrap_root_paths(install_mode or False)
    )
    expected: dict[Path, Path] = {}
    for authoritative_path in target_root.rglob("*"):
        if not authoritative_path.is_file():
            continue
        target_relative = authoritative_path.relative_to(target_root)
        if target_relative.parts[0] == ".claude":
            claude_relative = target_relative.relative_to(".claude")
            if (
                claude_relative == Path("bootstrap-ownership.env")
                and valid_ownership_manifest
            ):
                continue
            if claude_relative == Path("antigravity-ownership.env"):
                continue
            if not is_consumer_state_path(claude_relative) and (
                not claude_relative.parts
                or claude_relative.parts[0] != "bootstrap-root"
            ):
                expected[target_relative] = authoritative_path
        if not is_root_adapter_path(target_relative):
            continue
        if target_relative.as_posix() in TRACKED_AUTHORING_PATHS and is_exact_tracked(
            repo_root, target_relative
        ):
            continue
        if not is_exact_tracked(repo_root, target_relative):
            expected[target_relative] = authoritative_path
        if any(
            target_relative == root or root in target_relative.parents
            for root in active_bootstrap_paths
        ) and not is_exact_tracked(repo_root, target_relative):
            expected[Path(".claude/bootstrap-root") / target_relative] = (
                authoritative_path
            )

    for expected_relative, authoritative_path in expected.items():
        if parity_matches(repo_root / expected_relative, authoritative_path, repo_root):
            continue
        source = (
            authoritative_path.relative_to(repo_root)
            if authoritative_path.is_relative_to(repo_root)
            else authoritative_path
        )
        errors.append(drift_diagnostic(expected_relative.as_posix(), str(source)))

    installed: set[Path] = set()
    claude_root = repo_root / ".claude"
    if claude_root.is_dir():
        for path in claude_root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(claude_root)
            if (
                (relative.parts and relative.parts[0] == ".git")
                or relative == Path(".gitignore")
                or (relative.parts and relative.parts[0] == ".cache")
                or is_consumer_state_path(relative)
                or (relative.parts and relative.parts[0] == "bootstrap-root")
                or (
                    relative == Path("bootstrap-ownership.env")
                    and valid_ownership_manifest
                )
            ):
                continue
            installed.add(Path(".claude") / relative)
    for adapter in RESTORABLE_ROOT_PATHS:
        adapter_path = repo_root / adapter
        if adapter_path.is_file():
            candidates = [adapter_path]
        elif adapter_path.is_dir():
            candidates = [path for path in adapter_path.rglob("*") if path.is_file()]
        else:
            candidates = []
        installed.update(
            path.relative_to(repo_root)
            for path in candidates
            if path.relative_to(repo_root).as_posix() not in TRACKED_AUTHORING_PATHS
            if not is_exact_tracked(repo_root, path.relative_to(repo_root))
        )
    bootstrap_root = claude_root / "bootstrap-root"
    if bootstrap_root.is_dir():
        for path in bootstrap_root.rglob("*"):
            if not path.is_file():
                continue
            root_relative = path.relative_to(bootstrap_root)
            is_active = any(
                root_relative == root or root in root_relative.parents
                for root in active_bootstrap_paths
            )
            if is_active and is_exact_tracked(repo_root, root_relative):
                continue
            installed.add(Path(".claude/bootstrap-root") / root_relative)
    for obsolete_relative in sorted(installed - expected.keys()):
        errors.append(
            drift_diagnostic(
                obsolete_relative.as_posix(), "absent from generated target"
            )
        )
    return errors


def python_baseline_warning() -> str | None:
    """Warn when the shipped `**Python:**` baseline in generated guidance drifts
    from the bootstrap's own `requires-python`. Consumers reconcile this at
    install time from their own pyproject; this guards the source baseline."""
    pyproject = REPO_ROOT / "pyproject.toml"
    workspace = (
        DIST_ROOT
        / "multi-agent"
        / ".claude"
        / "instructions"
        / "workspace.instructions.md"
    )
    if not pyproject.is_file() or not workspace.is_file():
        return None
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    spec = (data.get("project") or {}).get("requires-python")
    if not isinstance(spec, str) or not spec.strip().startswith(">="):
        return None
    version = spec.strip()[2:].strip()
    if not version or any(ch in version for ch in ",<>=!~* "):
        return None
    documented = f"{version}+"
    for line in workspace.read_text(encoding="utf-8").splitlines():
        if line.startswith("**Python:**") and documented not in line:
            return (
                f"documented Python baseline in workspace.instructions.md does not match "
                f"pyproject requires-python ({spec!r} -> expected {documented!r}); "
                f"update the **Python:**/**Stack:** lines in shared/policies/workspace.instructions.md"
            )
    return None


def context_mode_dispatch_errors() -> list[str]:
    """Run the generated launcher's local, network-free cache self-check."""
    dispatcher = (
        DIST_ROOT / "multi-agent/.claude/hooks/scripts/context-mode-dispatch.sh"
    )
    if not dispatcher.is_file():
        return []  # REQUIRED_FILES reports the missing artifact.
    result = subprocess.run(
        [str(dispatcher), "--self-check"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    expected = str((DIST_ROOT / "multi-agent/.claude/.cache/context-mode").resolve())
    errors: list[str] = []
    if result.returncode != 0:
        errors.append(f"Context Mode dispatcher self-check exited {result.returncode}")
    if f"storage-root={expected}" not in result.stdout:
        errors.append(
            "Context Mode dispatcher did not report the generated target's absolute local cache root"
        )
    if not any(
        marker in result.stdout for marker in ("storage=writable", "storage=creatable")
    ):
        errors.append(
            "Context Mode dispatcher did not confirm writable or creatable local cache storage"
        )
    return errors


def plan_frontmatter_errors(repo_root: Path) -> list[str]:
    """Run the shipped plan-frontmatter validator and surface failures as
    hard errors. A missing validator script is not itself an error here; the
    REQUIRED_FILES/REQUIRED_DIRS checks already gate on the generated tree."""
    validator = repo_root / "scripts" / "validate_plan_frontmatter.py"
    if not validator.exists():
        return []
    result = subprocess.run(
        [sys.executable, str(validator)],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        print("PASS plan frontmatter validation")
        return []
    output = (result.stdout + result.stderr).strip()
    return [f"plan frontmatter validation reported issues: {output}"]


# Bash 3.2 (the declared consumer orchestration baseline; see
# docs/runtime-checks.md) raises "unbound variable" under `set -u` when `arr`
# has zero elements and is expanded as `${arr[@]}`, `${arr[*]}`, or the
# indices form `${!arr[@]}`/`${!arr[*]}`; Bash 4.4+ does not. Confirmed
# against Chet Ramey's own bash-4.3 transcript on bug-bash@gnu.org
# (2019-05-13, "set -u and empty arrays"), which reproduces the failure for
# BOTH `${a[@]}` and `${a[*]}` UNQUOTED, and against the current bash(1)
# manual's nounset exception text ("array variables subscripted with @ or
# *"), which does not exempt the indices form either - so quoting never
# changes vulnerability, and the indices form is the same bug class as the
# value form (this repository's own record-commit-closeout.sh already
# guards a bare `${!phases[@]}` the same way). The repository's guard idiom
# is `${arr[@]+"${arr[@]}"}` (or, for the indices form,
# `${arr[@]+"${!arr[@]}"}` - the guard check always tests values, even when
# the protected alternate is the indices list); a naive scan for
# `${arr[@]}` would also match the guarded idiom's own inner quoted part, so
# the guarded form is masked out first, allowing the guard-check subscript
# and the inner alternate's subscript/indices-prefix to differ.
_GUARDED_ARRAY_EXPANSION = re.compile(r'\$\{(\w+)\[[@*]\]\+"\$\{!?\1\[[@*]\]\}"\}')
_ARRAY_EXPANSION = re.compile(r"\$\{(!?)(\w+)\[([@*])\]\}")

# Sites that still expand an array the unguarded way, each verified safe by an
# explicit preceding emptiness guard or by a literal non-empty initializer
# that is never cleared. Keyed by the exact stripped source line so the entry
# stays tied to the reviewed code rather than a line number that drifts with
# unrelated edits. Keep this list short, and say why each entry is safe.
_ALREADY_SAFE_ARRAY_EXPANSIONS: dict[str, dict[str, str]] = {
    "shared/hooks/git-hooks/pre-push": {
        'reason="$(printf \'%s; \' "${failures[@]}")"': (
            'guarded above by [[ "${#failures[@]}" -gt 0 ]]'
        ),
    },
    "shared/hooks/git-hooks/commit-msg": {
        'reason="$(printf \'%s; \' "${failures[@]}")"': (
            'guarded above by [[ "${#failures[@]}" -gt 0 ]]'
        ),
    },
    "shared/hooks/scripts/enforce-commit-gate.sh": {
        'reason="$(printf \'%s; \' "${failures[@]}")"': (
            'guarded above by [[ "${#failures[@]}" -gt 0 ]]'
        ),
    },
    "shared/hooks/scripts/enforce-pr-gate.sh": {
        'reason="$(printf \'%s; \' "${failures[@]}")"': (
            'guarded above by [[ "${#failures[@]}" -gt 0 ]]'
        ),
    },
    "shared/hooks/scripts/_lib-frontmatter.sh": {
        'for path in "${paths[@]}"; do': (
            'guarded above by [[ "${#paths[@]}" -gt 0 ]] || return 1'
        ),
        'output="$(cd "$repo_root" && python3 "$reader" "${args[@]}" 2>&1)" || status=$?': (
            "args is a literal with seven elements; never empty"
        ),
        'for phase in "${phases[@]}"; do': (
            'guarded above by [[ "${#phases[@]}" -eq 0 ]] with an early return'
        ),
    },
    "shared/hooks/scripts/reporting-reminder.sh": {
        'effective="$(git "${options[@]}" rev-parse --show-toplevel 2>/dev/null || true)"': (
            'options is initialized with -C "$REPO_ROOT" and only ever appended '
            "to; never empty"
        ),
        '&& [[ " ${_TOKENS[*]} " == *" --out "* ]]': (
            "reached only when the preceding command_starts_with ... && "
            "short-circuit already returned success, which requires "
            "${#_TOKENS[@]} -ge ${#expected[@]} with expected non-empty; "
            "never empty here"
        ),
    },
    "shared/hooks/scripts/restore-root-adapters.sh": {
        'for relative in "${paths[@]}"; do': (
            "guarded above by ((${#paths[@]})) || fail"
        ),
    },
}


def unguarded_array_expansion_errors(repo_root: Path = REPO_ROOT) -> list[str]:
    """Flag hook scripts under ``shared/hooks/`` that expand a bash array with
    a Bash-3.2-unsafe form - ``${arr[@]}``, ``${arr[*]}``, ``${!arr[@]}``, or
    ``${!arr[*]}``, quoted or not - and neither the repository's
    ``${arr[@]+"<form>"}`` guard nor a listed reason. Scans every ``.sh`` file
    and every extensionless file whose first line names bash (the git hook
    entry points)."""
    hooks_root = repo_root / "shared" / "hooks"
    if not hooks_root.is_dir():
        return []
    errors: list[str] = []
    for path in sorted(hooks_root.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.splitlines()
        first_line = lines[0] if lines else ""
        if path.suffix != ".sh" and "bash" not in first_line:
            continue
        relative = path.relative_to(repo_root).as_posix()
        allowlisted = _ALREADY_SAFE_ARRAY_EXPANSIONS.get(relative, {})
        for line_number, line in enumerate(lines, start=1):
            masked = _GUARDED_ARRAY_EXPANSION.sub(lambda m: " " * len(m.group(0)), line)
            for match in _ARRAY_EXPANSION.finditer(masked):
                if line.strip() in allowlisted:
                    continue
                _, name, _ = match.groups()
                errors.append(
                    f"unguarded array expansion: {relative}:{line_number} expands "
                    f"{match.group(0)!r} without the "
                    f'${{{name}[@]+"{match.group(0)}"}} guard or a listed reason; '
                    "Bash 3.2 raises 'unbound variable' under set -u when "
                    f"{name} is empty (docs/runtime-checks.md)"
                )
    return errors


def main() -> int:
    errors: list[str] = []
    for relative_path in REQUIRED_FILES:
        if not (REPO_ROOT / relative_path).exists():
            errors.append(f"missing runtime file: {relative_path}")
    for relative_path in REQUIRED_DIRS:
        if not (REPO_ROOT / relative_path).is_dir():
            errors.append(f"missing runtime directory: {relative_path}")

    errors.extend(plan_frontmatter_errors(REPO_ROOT))

    for command in OPTIONAL_BINARIES:
        path = shutil.which(command)
        if path:
            print(f"PASS optional binary available: {command} -> {path}")
        else:
            if command == "gh":
                print(
                    "WARN optional binary missing: gh; enforce-pr-gate.sh still blocks common "
                    "implementation-branch git push paths, but GitHub web UI PR opening itself is not gated"
                )
            elif command == "uv":
                print(
                    "WARN optional binary missing: uv; guardrails use Bash 3.2 orchestration and "
                    "Python 3 standard-library JSON parsing for report reads without uv; "
                    "verify.py needs uv"
                )
            elif command == "context-mode":
                print(
                    "WARN optional binary missing: context-mode; retrieval falls back to direct reads "
                    "and rg (context-mode is a convenience, not a requirement)"
                )
            elif command == "npx":
                print(
                    "WARN optional binary missing: npx; the context7 MCP server (current external "
                    "library API docs) is unavailable, falling back to training-data knowledge, and "
                    "context-mode-dispatch.sh loses its npx fallback for launching context-mode"
                )
            else:
                print(f"WARN optional binary missing: {command}")

    if shutil.which("uvx"):
        print("PASS Semble can be launched through uvx when requested")
    else:
        print("WARN Semble MCP launcher uvx is missing; Semble is optional")

    baseline_warning = python_baseline_warning()
    if baseline_warning:
        print(f"WARN {baseline_warning}")
    else:
        print("PASS documented Python baseline matches pyproject requires-python")

    errors.extend(runtime_drift_errors())
    errors.extend(context_mode_dispatch_errors())
    array_errors = unguarded_array_expansion_errors()
    if not array_errors:
        print("PASS hook scripts guard empty-array expansions for Bash 3.2")
    errors.extend(array_errors)

    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1

    print("PASS generated runtime wiring is present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
