---
name: bootstrap-efficiency-fixes
type: big-plan
status: complete
originating_branch: dev
implementation_branch: dev
started_at: 2026-07-22T11:42:35+09:00
phases:
  - b2-python-version-derivation
  - b3-workflow-freshness-order
  - b4-uv-cache-writable
  - b5-typed-role-fork-rule
  - gitignore-block-refresh
current_phase: gitignore-block-refresh
---

# Big Plan: Bootstrap Efficiency Fixes

## Context

Investigation of a high-usage consumer session (`industrial-inspection`,
recorded in the now-deleted `bootstrap-agent-efficiency-findings.md`) surfaced
several control-plane defects. This plan addresses **only the identifiably
broken issues** grounded in code/docs. The speculative batching/turn-budget
policy work was explicitly deferred pending real (uncached) cost measurement.

Work was done directly on `dev` with the normal branch/score/findings lifecycle
intentionally skipped, because the change modifies that very lifecycle. Landed
as two commits rather than the usual per-phase commits.

## What was done (2 commits)

### Commit `d872d10` — four control-plane fixes

- **B2 — Python version derivation.** `install_bootstrap.py` now derives the
  documented Python version from the consumer's `pyproject.toml`
  `requires-python` (`>=3.13` -> `3.13+`) and rewrites the two project-fact
  lines across all four generated surfaces (`CLAUDE.md`, `AGENTS.md`,
  `.claude/instructions/workspace.instructions.md`, `workspace.md`). Incidental
  prose mentions are left untouched. A fresh target with no parseable
  `requires-python` keeps the `3.12+` baseline (no invented value, no crash).
  `check_runtime.py` warns if the shipped baseline drifts from the bootstrap's
  own `requires-python`.
- **B3 — Workflow freshness order.** The lifecycle was reordered from
  `... REVIEW -> SCORE -> DOCUMENT ...` to
  `... REVIEW -> DOCUMENT -> SCORE ...` across the workflow/workspace policies,
  orchestrator prompt, generator strings, `validate_targets.py` assertion, and
  `docs/architecture.md`. Reason: the commit gate binds the score and findings
  reports to the whole-tree `content_hash`, so documenting *after* SCORE staled
  both reports and forced a redundant re-score/re-findings cycle every phase.
  DOCUMENT now runs before the persisted gate; doc-only changes are not
  re-reviewed (REVIEW re-runs only if a later fix changes code).
- **B4 — uv cache writable.** `UV_CACHE_DIR` in `devcontainer.json` moved from
  `/home/vscode/.cache/uv` (under `$HOME`, read-only in the execute sandbox) to
  `${containerWorkspaceFolder}/.uv-cache` (inside the workspace, writable), and
  `.uv-cache/` was added to the generated ignore block. Fixes the verifier's
  `uv run` failing before execution; also helps the `uvx`-launched Semble
  server.
- **B5 — Typed-role fork rule.** The orchestrator prompt now documents spawning
  typed roles fresh (compact task, not full-history inheritance), with the
  Codex `fork_turns: "none"` mechanism as the concrete case.

### Commit `7dc09a7` — gitignore block refresh

`merge_gitignore` previously skipped when the ignore block already existed, so
new patterns (like `.uv-cache/`) never reached consumers that already had the
block. It now rewrites the block in place between its markers (idempotent; text
outside the markers untouched), so pattern changes propagate on refresh.

## Out of scope (deliberately)

- MCP `.mcp.json`/Codex parity — generator emits identical servers to all
  targets from one source; the observed drift was a consumer hand-edit.
- MCP-in-subagent beyond the shared cache cause (Codex propagation not
  verifiable from bootstrap code).
- shared-vs-Codex effort/model "disagreement" — intentional, works at runtime.
- All batching/turn-budget/context policy — deferred pending real (uncached)
  cost measurement.

## Verification

```bash
uv run python scripts/generate_targets.py --all      # PASS
uv run python scripts/validate_targets.py            # PASS (full behavioral suite)
uv run python scripts/check_runtime.py               # PASS (incl. new baseline check)
uv run pytest tests/ -q                              # PASS
uv run mypy scripts/install_bootstrap.py scripts/check_runtime.py --ignore-missing-imports  # clean
uv run ruff check scripts/install_bootstrap.py scripts/check_runtime.py                     # clean
```

Standalone smoke tests confirmed: Python-version parse/substitute across 4
surfaces with fresh/compound fallbacks; `merge_gitignore` refresh adds
`.uv-cache/`, preserves surrounding text, and is idempotent.

## Consumer rollout

`industrial-inspection` was updated (`update_consumers.py`, full mode) and its
`ai-state` pushed. Verified live: Python docs read `3.13+`, `UV_CACHE_DIR` is
workspace-relative, workflow order is `REVIEW -> DOCUMENT -> SCORE`, the fork
rule is present, and `.uv-cache/` is now gitignored.

## Closeout

- Session log: `.claude/session_logs/2026-07-22_bootstrap-efficiency-fixes.md`
- Both commits pushed to `origin/dev` (`d872d10`, `7dc09a7`).
