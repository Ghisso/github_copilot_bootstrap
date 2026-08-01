---
name: 2026-08-01_phase-A-state-sync-operations
type: small-plan
parent_plan: ai-state-lifecycle-sync
phase_index: 1
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-01_phase-A-state-sync-operations

## Scope

Turn the existing combined `state-sync.sh push` flow into explicit local
checkpoint and remote publication operations, while keeping `push` as the
backward-compatible composition. Add a read-only live status view and focused
Git-backed tests. This phase does not wire new runtime events yet.

No new dependency or second sync module is allowed. The implementation must
reuse the current nested-repo setup, commit, rebase/abort, warning, error-log,
and conflict-preservation code.

## Ownership

- `coder`: shell refactor and direct regression tests.
- `verifier`: shell syntax, focused/full tests, generation/validator, typing,
  lint, formatting, and persisted score.
- `reviewer`: two-pass control-plane review with the profiles below.
- `documenter`: update living state-sync command documentation before score.
- `orchestrator`: findings persistence, LEARN/session-log closeout, and commit.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` — `full` mode for the entire phase.
- `.claude/skills/testing-patterns/SKILL.md` — real Git/state-transition tests.
- `.claude/skills/run-tests/SKILL.md` — focused then full verification.
- `.claude/skills/documentation/SKILL.md` — public command contract updates.
- `.claude/skills/ponytail-review/SKILL.md` — mandatory final diff reduction.

## Steps

### 1. Specify regressions before the refactor

- **Owner:** `coder`
- **Files:** modify `tests/test_state_sync.py`; modify the state-sync behavioral
  section of `scripts/validate_targets.py` so CI exercises the same contracts
  without depending on pytest availability.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` (`full`) and
  `.claude/skills/testing-patterns/SKILL.md`.
- Add real bare-repository cases that initially fail against the current
  script:
  - `checkpoint` commits dirty state locally and does not create/change a
    remote ref;
  - Git Trace2 for `checkpoint` contains no `fetch`, `ls-remote`, `pull`,
    `merge`, or `push`, even when a remote is configured;
  - `publish` sends a prior checkpoint without creating another local commit;
  - a second clean `publish` is idempotent (same local/remote heads and commit
    count, successful/no-op result);
  - dirty-tree `publish` warns, leaves files/HEAD intact, and does not publish
    uncheckpointed content;
  - `push` still checkpoints then publishes for compatibility;
  - `status` performs no remote command or mutation and distinguishes
    uninitialized, clean, dirty, and cached ahead/behind states without
    printing a remote URL;
  - operational modes (`checkpoint`, `publish`, `push`) emit no plain stdout;
    warnings/errors remain visible in stderr and
    `.claude/session_logs/hooks-errors.log`.
- Use markers unique to the new paths, not loose outcome-only assertions that
  Git's lower-level rejection could satisfy under both old and new code.
- **Verify:**
  `uv run pytest tests/test_state_sync.py -q --tb=short` must demonstrate the
  intended red state before implementation, then pass after Step 2.

### 2. Add `checkpoint`, `publish`, and `status`; retain `push`

- **Owner:** `coder`
- **Files:** modify `shared/hooks/scripts/state-sync.sh` only for the engine.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` (`full`).
- Extend the accepted mode list to
  `setup|pull|checkpoint|publish|push|status|migrate-from-hf`.
- Introduce the smallest reusable internal functions needed for these exact
  contracts:
  - `cmd_checkpoint`: initialize/restore local scaffolding if required and call
    the existing local commit logic. It must not execute a remote Git command.
  - `cmd_publish`: require a clean nested worktree, reconcile committed state
    with `origin/$BRANCH`, and push only after successful reconciliation. It
    must never run `git add` or `git commit`; dirty state is warned and
    preserved for the next checkpoint.
  - `cmd_push`: call checkpoint, skip/diagnose publication if checkpoint failed,
    otherwise call publish. Keep top-level exit zero.
  - `cmd_pull`: preserve commit-before-rebase and all existing clean-abort
    guarantees; reuse the new primitives only where their contracts remain
    exact.
  - `cmd_status`: inspect only local `.claude/.git`, worktree, configured-remote
    presence, and cached tracking refs. Print stable human-readable fields and
    the error-log path/last matching state-sync error; never fetch and never
    print a credential-bearing URL.
- Preserve local-only mode: `push --local-only` still creates a local commit and
  performs no remote I/O; an explicit `publish` in local-only mode is a
  non-mutating remote skip.
- Preserve `migrate-from-hf` and explicit `setup` behavior. A fresh local
  checkpoint must not silently create an unrelated-history trap: if the later
  publish sees independently initialized local/remote histories, reuse the
  existing safe unrelated-history reconciliation and abort-on-conflict path.
- Route routine operational diagnostics to stderr. Only `status` intentionally
  uses stdout. Continue appending failures to the existing error log and
  always leave the nested repository outside an active rebase/merge.
- **Must not:** add force operations, automatic ours/theirs, a status file, a
  dependency, or a background process.
- **Verify:**
  `bash -n shared/hooks/scripts/state-sync.sh` and the focused tests from Step 1.

### 3. Update shared behavioral validation and living command docs

- **Owner:** `coder` for validator; `documenter` for docs.
- **Files:** modify `scripts/validate_targets.py`, `README.md`,
  `docs/architecture.md`, and `docs/smoke-tests.md` only where the shared
  command contract is described.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` (`full`) for the
  validator and `.claude/skills/documentation/SKILL.md` for prose.
- Validate exact subcommand behavior using real Git state and Trace2. Retain
  the existing two-copy byte-identity check and all conflict/migration/local-
  only coverage.
- Replace the four-subcommand documentation with the seven-command contract.
  Explain checkpoint versus publish, `push` compatibility, dirty publication
  refusal, no-stdout operational behavior, read-only/cached status fields, and
  the existing error-log recovery path. Do not yet claim new Codex/Claude
  events are wired.
- **Verify:**
  `uv run python scripts/generate_targets.py --all` followed by
  `uv run python scripts/validate_targets.py`.

### 4. Verify, review, score, and close the phase

- **Owner:** `verifier`, then `reviewer`, then `orchestrator`.
- **Files:** the complete Phase A diff; generated `dist/` is verification
  output and remains unedited/gitignored.
- **Required Skills:** `.claude/skills/run-tests/SKILL.md`,
  `.claude/skills/code-review/SKILL.md`,
  `.claude/skills/ponytail-review/SKILL.md`,
  `.claude/skills/learn/SKILL.md`, and `.claude/skills/commit/SKILL.md`.
- **Review Profiles:**
  - `.claude/review-profiles/code.md`
  - `.claude/review-profiles/architecture.md`
  - `.claude/review-profiles/security.md`
  - `.claude/review-profiles/tests.md`
  - `.claude/review-profiles/ponytail.md`
  - `.claude/review-profiles/documentation.md`
- Review specifically for credential leakage in status, accidental remote I/O
  from checkpoint, a dirty-tree data-loss path, non-zero hook exits, and
  unnecessary abstraction.
- Resolve all findings, rerun verification, document, stage explicit phase
  files, persist findings/score, add LEARN evidence, complete the phase session
  log, mark this small plan complete, and commit once.
- **Verify:** run every command in this plan's Verification section, then
  inspect the persisted score/findings JSON and completed session log before
  `git commit`.

## Verification

```bash
bash -n shared/hooks/scripts/state-sync.sh
uv run pytest tests/test_state_sync.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy scripts/ tests/test_state_sync.py --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python .claude/scripts/quality_score.py scripts/ --phase 2026-08-01_phase-A-state-sync-operations --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

## Acceptance Criteria

- `checkpoint` is a demonstrably network-free local commit boundary.
- `publish` never commits dirty state, reconciles safely, and is idempotent
  when repeated after success.
- `push` preserves every existing caller's checkpoint+publish behavior.
- `pull`, migration, local-only, multi-writer union/conflict, stdin-drain, and
  warn-never-fail contracts remain green.
- `status` is read-only, network-free, useful, and credential-safe.
- Operational modes produce no stdout that could corrupt a Codex hook result.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved, including zero surviving Ponytail findings
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated before persisted findings/score
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] One atomic Phase A commit created
