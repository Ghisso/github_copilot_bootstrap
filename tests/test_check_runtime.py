"""Regression coverage for check_runtime.py's hard consumer-facing checks."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_runtime  # noqa: E402


def _write_plan(root: Path, frontmatter: str) -> None:
    plans = root / ".claude" / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    (plans / "example.md").write_text(
        f"---\n{frontmatter.strip()}\n---\n\n# Example\n", encoding="utf-8"
    )


def test_plan_frontmatter_errors_reports_invalid_metadata_as_fail(
    tmp_path: Path,
) -> None:
    """R-LIFECYCLE-04: check_runtime.py now surfaces invalid plan frontmatter
    as a hard FAIL, not the earlier advisory WARN."""
    (tmp_path / "scripts").mkdir()
    shutil.copy2(
        REPO_ROOT / "scripts" / "validate_plan_frontmatter.py",
        tmp_path / "scripts" / "validate_plan_frontmatter.py",
    )
    _write_plan(
        tmp_path,
        "type: big-plan\nstatus: planning\noriginating_branch: dev\n"
        "implementation_branch: example_implementation\nphases:\n  - phase-one",
    )
    errors = check_runtime.plan_frontmatter_errors(tmp_path)
    assert len(errors) == 1
    assert "plan frontmatter validation reported issues" in errors[0]
    assert "missing required field: name" in errors[0]


def test_plan_frontmatter_errors_passes_for_valid_metadata(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    shutil.copy2(
        REPO_ROOT / "scripts" / "validate_plan_frontmatter.py",
        tmp_path / "scripts" / "validate_plan_frontmatter.py",
    )
    _write_plan(
        tmp_path,
        "name: example\ntype: big-plan\nstatus: planning\noriginating_branch: dev\n"
        "implementation_branch: example_implementation\nphases:\n  - phase-one",
    )
    assert check_runtime.plan_frontmatter_errors(tmp_path) == []


def test_plan_frontmatter_errors_skips_when_validator_is_absent(
    tmp_path: Path,
) -> None:
    """A missing validator is the generated-target-parity checks' job to
    catch, not a duplicate failure reason here."""
    assert check_runtime.plan_frontmatter_errors(tmp_path) == []


def test_unguarded_array_expansion_errors_passes_for_the_shipped_hooks() -> None:
    """Phase B2 (2026-09-11_phase-B2-hook-empty-array-safety): every
    reachable `"${arr[@]}"` expansion in the real shared/hooks/ scripts must
    already be guarded or explicitly allowlisted. This is a pure source scan,
    so unlike the Bash-3.2 unbound-variable abort itself it does not depend
    on the host Bash version."""
    assert check_runtime.unguarded_array_expansion_errors(REPO_ROOT) == []


def test_unguarded_array_expansion_errors_flags_a_bare_expansion(
    tmp_path: Path,
) -> None:
    """A `"${arr[@]}"` expansion with neither the guard idiom nor an
    allowlist entry must be reported, naming the file, line, and variable so
    a future regression is diagnosable."""
    hooks = tmp_path / "shared" / "hooks" / "scripts"
    hooks.mkdir(parents=True)
    (hooks / "probe.sh").write_text(
        "#!/usr/bin/env bash\n"
        "local -a items=()\n"
        'for item in "${items[@]}"; do echo "$item"; done\n',
        encoding="utf-8",
    )
    errors = check_runtime.unguarded_array_expansion_errors(tmp_path)
    assert len(errors) == 1
    assert "shared/hooks/scripts/probe.sh:3" in errors[0]
    assert "items" in errors[0]


def test_unguarded_array_expansion_errors_ignores_the_guarded_idiom(
    tmp_path: Path,
) -> None:
    """The guarded form `${arr[@]+"${arr[@]}"}` must not be flagged - its own
    inner quoted part is textually identical to the unsafe form, which is
    exactly the false-positive a naive regex produces."""
    hooks = tmp_path / "shared" / "hooks" / "scripts"
    hooks.mkdir(parents=True)
    (hooks / "probe.sh").write_text(
        "#!/usr/bin/env bash\n"
        "local -a items=()\n"
        'for item in ${items[@]+"${items[@]}"}; do echo "$item"; done\n',
        encoding="utf-8",
    )
    assert check_runtime.unguarded_array_expansion_errors(tmp_path) == []


@pytest.mark.parametrize(
    "expression",
    [
        pytest.param("${items[@]}", id="unquoted-at"),
        pytest.param("${items[*]}", id="unquoted-star"),
        pytest.param('"${items[*]}"', id="quoted-star"),
        pytest.param("${!items[@]}", id="unquoted-indices"),
        pytest.param('"${!items[@]}"', id="quoted-indices"),
    ],
)
def test_unguarded_array_expansion_errors_flags_every_vulnerable_shape(
    tmp_path: Path, expression: str
) -> None:
    """Bash 3.2 raises 'unbound variable' under set -u for every one of
    these shapes, not only the quoted `"${arr[@]}"` form: confirmed against
    Chet Ramey's own bash-4.3 transcript on bug-bash@gnu.org (2019-05-13,
    "set -u and empty arrays"), which reproduces the failure for unquoted
    `${a[@]}` and `${a[*]}` alike, and against the current bash(1) manual's
    nounset exception text ("array variables subscripted with @ or *"),
    which does not exempt the indices form either."""
    hooks = tmp_path / "shared" / "hooks" / "scripts"
    hooks.mkdir(parents=True)
    (hooks / "probe.sh").write_text(
        "#!/usr/bin/env bash\n"
        "local -a items=()\n"
        f'for item in {expression}; do echo "$item"; done\n',
        encoding="utf-8",
    )
    errors = check_runtime.unguarded_array_expansion_errors(tmp_path)
    assert len(errors) == 1
    assert "shared/hooks/scripts/probe.sh:3" in errors[0]
    assert "items" in errors[0]


def test_unguarded_array_expansion_errors_ignores_the_mixed_subscript_guard(
    tmp_path: Path,
) -> None:
    """shared/hooks/scripts/record-commit-closeout.sh guards the indices
    form with a guard-check on the `@` subscript and an inner alternate on
    the `!` indices form: `${phases[@]+"${!phases[@]}"}`. The guard-check
    subscript and the inner alternate's subscript/indices-prefix may differ
    from each other; this must not be flagged."""
    hooks = tmp_path / "shared" / "hooks" / "scripts"
    hooks.mkdir(parents=True)
    (hooks / "probe.sh").write_text(
        "#!/usr/bin/env bash\n"
        "local -a phases=()\n"
        'for index in ${phases[@]+"${!phases[@]}"}; do echo "$index"; done\n',
        encoding="utf-8",
    )
    assert check_runtime.unguarded_array_expansion_errors(tmp_path) == []


def test_unguarded_array_expansion_errors_respects_the_allowlist(
    tmp_path: Path,
) -> None:
    """A site with an explicit, commented allowlist entry keyed to the real
    repository path is accepted even though it is unguarded, because the
    entry records a verified reason (an explicit preceding guard or a
    non-empty literal initializer)."""
    hooks = tmp_path / "shared" / "hooks" / "git-hooks"
    hooks.mkdir(parents=True)
    (hooks / "pre-push").write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "${#failures[@]}" -gt 0 ]]; then\n'
        '  reason="$(printf \'%s; \' "${failures[@]}")"\n'
        "fi\n",
        encoding="utf-8",
    )
    assert check_runtime.unguarded_array_expansion_errors(tmp_path) == []
