---
name: 2026-07-20_phase-9-local-only-consumer-updates
type: small-plan
parent_plan: consumer-local-only-update
phase_index: 9
status: complete
closeout_session_log: .claude/session_logs/2026-07-21_local-only-consumer-updates.md
---

# Small Plan: 2026-07-20_phase-9-local-only-consumer-updates

## Scope

Add a complete, durable `--local-only` consumer refresh that updates all
bootstrap-controlled files and commits the nested `ai-state` repository without
contacting its remote. Preserve the existing update-and-push default for
human-operated CLI use. Make source-layout validation distinguish tracked
legacy mirrors from ignored self-install overlays.

## Ownership

- Coder: updater, installer, state-sync local-only behavior, and focused validator coverage.
- Verifier: generation, target validation, runtime checks, tests, typing, lint, and score.
- Reviewer: `code`, `architecture`, `security`, `tests`, `config`, and `ponytail`.
- Documenter: README and architecture/runtime documentation affected by the CLI contract.

## Steps

- [x] Add `--local-only` to `scripts/update_consumers.py` and forward it to
  `scripts/install_bootstrap.py`.
- [x] Centralize a hard local-only remote-I/O boundary in
  `shared/hooks/scripts/state-sync.sh`: setup/migration may initialize,
  configure, and commit, but must not fetch, pull, reconcile, or push.
- [x] Make local-only installation create the normal migration/bootstrap commit,
  including `.claude/bootstrap-root`, while suppressing fetch, pull, and push.
- [x] Consolidate legacy migration ownership in the installer so local-only mode
  cannot invoke an older consumer helper that does not understand the new
  safety boundary. Commit pre-existing state before generated files replace it,
  then create a distinct bootstrap update commit.
- [x] Preserve the current default behavior, including legacy migration and
  remote publication.
- [x] Print the pending nested-state status and exact manual sync command after
  a local-only update.
- [x] Change obsolete root-source validation to reject tracked or accidentally
  unignored mirrors while allowing ignored self-install overlays that match
  generated output.
- [x] Add focused validation fixtures for local-only existing-state, fresh
  install, legacy migration, remote non-mutation, default push behavior, and
  tracked/ignored source-layout cases.
- [x] Update user-facing CLI and self-install documentation.

## Risks

- A local-only path could accidentally invoke `setup`, migration, or `push`
  code that contacts a configured remote.
- Skipping remote reconciliation can leave a local commit ahead of a changed
  remote; the later explicit `state-sync.sh push` must retain the established
  rebase-and-warn behavior.
- Pre-git migration must preserve mutable consumer files while generated
  bootstrap content is refreshed.
- Allowing ignored overlays must not permit tracked legacy source mirrors or
  silently accept stale generated adapters.
- Reported manual commands must remain shell-safe when consumer paths contain
  spaces.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy scripts/ --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run python .claude/scripts/quality_score.py scripts/ --phase phase-9-local-only-consumer-updates --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

## Acceptance Criteria

- `update_consumers.py` retains its existing full update-and-push default.
- `--local-only` produces a clean, durable nested-state commit without remote
  reads or writes and tells the user how to publish it later.
- Fresh and pre-git consumers work in local-only mode without losing state.
- Legacy local-only migration produces ordered `migrate:` and `bootstrap:`
  commits before any manual publication.
- Self-installed ignored overlays no longer fail source-layout validation;
  tracked, unignored, or stale mirrors still fail.
- Required verification and review gates pass with score >= 90 and zero
  surviving Ponytail findings.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
