---
name: 2026-07-22_phase-2-durable-checkpoint-and-docs
type: small-plan
parent_plan: state-sync-durability
phase_index: 2
status: complete
closeout_session_log: .claude/session_logs/2026-07-22_state-sync-durability-sp2.md
---

# Small Plan: 2026-07-22_phase-2-durable-checkpoint-and-docs

## Scope

Add a reliable commit-time AI-state checkpoint so durability no longer depends
on a Codex `Stop` event (which tab closure does not guarantee), and correct the
documentation that overstates `Stop`. Source-only edits + generator/validator +
docs.

## Steps

- [ ] New `shared/hooks/git-hooks/post-commit`: best-effort `state-sync.sh push`
      after every successful outer commit. stdin from `/dev/null`; never fails a
      commit (git ignores the hook's exit status and state-sync is
      warn-never-fail). Auto-installed via the existing `copy_tree` +
      `chmod` + `core.hooksPath` wiring — no `install_bootstrap.py` change.
- [ ] `scripts/validate_targets.py`: assert the generated `post-commit` hook is
      present and pushes via `state-sync.sh`; keep the best-effort `Stop` push
      check; assert the two generated `state-sync.sh` copies
      (`.claude/hooks/scripts/` and `.devcontainer/`) are byte-identical.
- [ ] DOCUMENT (deferred to DOCUMENT phase): correct the "Stop always pushes"
      claims and add the tab-closure caveat + post-commit/explicit-task durable
      checkpoints in `shared/policies/workflow.instructions.md`, `README.md`,
      `docs/architecture.md`, `docs/smoke-tests.md`. Note that the nested
      `.gitattributes` policy is written at init (reaches fresh nested repos;
      matches the existing nested `.gitignore` behavior).
- [ ] Regenerate `dist/` and run the full validator + test suite.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/ -q --tb=short
uv run ruff check scripts/ tests/
```

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved (incl. ponytail)
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
