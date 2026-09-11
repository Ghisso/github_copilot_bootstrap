---
name: 2026-09-11_phase-C-agent-facing-gate-messages
type: small-plan
parent_plan: 2026-09-11_consumer-ceremony-friction
phase_index: 3
status: planned
closeout_session_log:
---

# Small Plan: Make gate and verifier messages name commands the agent can run

## Scope

Fix the two verifier messages that recommend a command the agent guard
denies, make the push gate explain why a chained commit-and-push is refused,
and document the separate-commands rule where agents read it.

## Findings This Plan Is Built On

- `unpublishable_closeout_reason` and the `main()` nested-repository
  diagnostic in `shared/scripts/verify.py` both end with
  ``run `bash .claude/hooks/scripts/state-sync.sh checkpoint` ``. Run through
  the generated PreToolUse guard, that command is denied:
  `Command references protected file(s) .claude/hooks/scripts/state-sync.sh, but the hook could not determine whether the command may modify them`.
  The command `git -C .claude add -A && git -C .claude commit -m checkpoint`
  is allowed. `docs/runtime-checks.md` and the orchestrator prompt already
  tell agents to use the git form; the tool output does not.
- `enforce-pr-gate.sh` evaluates `assert_push_invariants "$REPO_ROOT" "$CURRENT_BRANCH" "HEAD"`
  when a Bash command contains `git push`. A command that also contains the
  `git commit` that would create the certified HEAD is evaluated against the
  pre-commit HEAD and denied with
  `implementation branch must have at least one commit per completed small plan before PR/push`
  plus stale-receipt errors. This happened in the session that produced this
  plan. No skill, policy, or doc mentions it.

## Decisions

- Message shape for both verifier diagnostics: name the agent form first and
  the script second, in one sentence:
  `run git -C .claude add -A && git -C .claude commit -m "checkpoint: <reason>" (or, from a terminal or editor task, bash .claude/hooks/scripts/state-sync.sh checkpoint)`.
- In `enforce-pr-gate.sh`, when the denied command also satisfies
  `is_git_commit_command`, prefix the reason with
  `commit and push must be separate Bash commands: the push gate evaluates the current HEAD before this command's commit exists; run the commit first, then push`.
  Do not change what is evaluated; only explain it.
- Document the rule in the commit skill's push section and in
  `docs/runtime-checks.md` next to the push-gate description. One sentence
  each.

## Steps

- [ ] Update the two message strings in `shared/scripts/verify.py`; update
  the assertions in `tests/test_verify.py` that match the old text.
- [ ] In `shared/hooks/scripts/enforce-pr-gate.sh`, add the prefixed reason
  under the stated condition. Add a test in `tests/test_hook_gates.py` that a
  payload `git commit -m x && git push` on an implementation branch yields a
  denial containing `separate Bash commands`, and that a plain `git push`
  denial does not.
- [ ] Update `shared/skills/commit/SKILL.md` Phase 5 and
  `docs/runtime-checks.md`.
- [ ] Regenerate and install locally.

## Review Profiles

Hook script and canonical verifier: `code`, `architecture`, `security`,
`tests`, and `ponytail`. Load the Ponytail skill in `full` mode.

## Verification

```bash
uv run pytest tests/test_verify.py tests/test_hook_gates.py -q --tb=short
uv run pytest tests/ -q
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests && uv run ruff format --check shared scripts tests
uv run python scripts/generate_targets.py --all && uv run python scripts/install_bootstrap.py . --allow-self --local-only
uv run python scripts/validate_targets.py && uv run python scripts/check_runtime.py
```

Phase-specific proof: run the generated guard against
`git commit -m x && git push` and show the new explanation; run it against the
new verifier message's git form and show `allow`.

## Risks And Fallback Paths

- A validator asserts the exact old message text. Update the assertion; the
  behaviour is unchanged.

## Done Criteria

- Both verifier diagnostics name a command the agent guard allows.
- A chained commit-and-push denial explains the rule.
- The commit skill and runtime docs state the rule.

## Closeout Checklist

- [ ] All steps implemented and verified
- [ ] `uv run pytest tests/ -q` passes
- [ ] mypy, ruff check, and ruff format pass
- [ ] `validate_targets.py` and `check_runtime.py` pass
- [ ] Targets regenerated and installed locally
- [ ] Code, architecture, security, tests, and Ponytail reviews complete
- [ ] Critical and major findings at zero
- [ ] Documentation updated
- [ ] `.claude/MEMORY.md` records the reusable lessons or the no-lessons marker
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested state checkpointed before persisting the closeout receipt
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
