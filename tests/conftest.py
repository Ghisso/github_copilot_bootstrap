"""Shared pytest fixtures for the test suite.

Leak guard: several tests run the real hook scripts (``protect-files.sh``,
``pretool-bash-guard.sh``, ``antigravity-pretool.py``, ...) as subprocesses.
Those scripts write warnings to ``<REPO_ROOT>/.claude/session_logs/hooks-errors.log``.
Every such test must isolate ``REPO_ROOT`` under its own ``tmp_path`` so it
never touches the live checkout's error log; this fixture is the safety net
that catches a regression if one doesn't.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_LIVE_ERROR_LOG = REPO_ROOT / ".claude" / "session_logs" / "hooks-errors.log"


@pytest.fixture(scope="session", autouse=True)
def _live_error_log_must_stay_untouched() -> object:
    """Fail the session if the live error log's size or mtime changed.

    The log is gitignored (see ``write_nested_gitignore`` in
    ``state-sync.sh``), so a fresh clone or CI checkout starts with it
    absent. ``before`` is ``None`` in that case rather than skipping the
    guard outright, so a test that creates the file during the session still
    fails the leak check on the absent-to-present transition.
    """
    before = os.stat(_LIVE_ERROR_LOG) if _LIVE_ERROR_LOG.exists() else None
    yield
    after = os.stat(_LIVE_ERROR_LOG) if _LIVE_ERROR_LOG.exists() else None

    if before is None and after is not None:
        pytest.fail(
            f"{_LIVE_ERROR_LOG} was created during the test session: "
            "hook scripts must be run with REPO_ROOT under tmp_path, "
            "never the live checkout."
        )
    if (
        before is not None
        and after is not None
        and (before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns)
    ):
        pytest.fail(
            f"{_LIVE_ERROR_LOG} changed during the test session: "
            "hook scripts must be run with REPO_ROOT under tmp_path, "
            "never the live checkout."
        )
