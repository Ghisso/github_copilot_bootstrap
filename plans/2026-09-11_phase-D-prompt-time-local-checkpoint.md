---
name: 2026-09-11_phase-D-prompt-time-local-checkpoint
type: small-plan
parent_plan: 2026-09-11_consumer-ceremony-friction
phase_index: 4
status: planned
closeout_session_log:
---

# Small Plan: Stop doing network work before every prompt

## Scope

Change the generated UserPromptSubmit hook for Claude Code and OpenAI Codex
from `state-sync.sh push` to `state-sync.sh checkpoint`, so prompt submission
commits local state without contacting the remote. Publication keeps
happening at Stop, SessionEnd, and after every outer commit.

This phase is a policy change. Cancel it if the current behaviour is
preferred; the other phases do not depend on it.

## Findings This Plan Is Built On

- `scripts/generate_targets.py` wires `cmd("state-sync.sh", "push", timeout=60)`
  under `UserPromptSubmit` for both Claude (`:1093`) and Codex (`:1181`). No
  comment records why publication, rather than a local checkpoint, was chosen
  there.
- `cmd_push` is `cmd_checkpoint` then `cmd_publish`. `cmd_publish` on a clean
  worktree with a remote runs `ls-remote`, `fetch`, and `push` every time,
  even when nothing new exists locally. Measured in this repository online:
  fetch 0.42 s, push 0.59 s, ls-remote similar, so roughly 1.5 s before each
  prompt is processed. Offline, each call waits for Git to give up, capped by
  the 60 s hook timeout, and appends warnings to `hooks-errors.log`.
- The Stop hook (`claude-stop.sh`, `codex-stop.sh`) already runs checkpoint
  and publish; SessionEnd runs `push` (Claude) or `checkpoint` (Codex); the
  native post-commit hook runs `push`. Those remain the durable publication
  points.
- `state-sync.sh` drains stdin with `timeout 2 cat`; hook runtimes close
  stdin after writing the payload, so this does not add latency.

## Decisions

- UserPromptSubmit becomes `cmd("state-sync.sh", "checkpoint")` with the
  default 10 s timeout for both Claude and Codex. Checkpoint performs no
  remote Git operation by contract.
- Leave SessionStart `pull`, Stop, SessionEnd, StopFailure, and post-commit
  unchanged.
- Codex SessionEnd `checkpoint` keeps its 3 s timeout; this phase does not
  touch it, but the closeout log records whether the timing concern (2 s
  stdin drain inside a 3 s budget) was observed during testing.

## Steps

- [ ] Change the two `UserPromptSubmit` entries in
  `scripts/generate_targets.py`.
- [ ] Update `scripts/validate_targets.py` expectations that assert
  `state-sync.sh push` appears in Claude settings, Codex hooks, and GitHub
  hooks text, so they assert `checkpoint` for UserPromptSubmit and still
  assert `push` for Stop, SessionEnd, and post-commit. Keep the negative
  assertion that UserPromptSubmit performs no remote operation if one exists;
  add it if not, by grepping the generated settings.
- [ ] Update `docs/architecture.md` hooks table, `docs/runtime-checks.md`
  hook list, and the README hooks section to say prompt submission
  checkpoints locally and publication happens at Stop, SessionEnd, and
  post-commit.
- [ ] Regenerate and install locally.

## Review Profiles

Generator and validator changes are control-plane: `code`, `architecture`,
`security`, `tests`, and `ponytail`. Load the Ponytail skill in `full` mode.

## Verification

```bash
uv run pytest tests/test_validate_targets.py -q --tb=short
uv run pytest tests/ -q
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests && uv run ruff format --check shared scripts tests
uv run python scripts/generate_targets.py --all && uv run python scripts/install_bootstrap.py . --allow-self --local-only
uv run python scripts/validate_targets.py && uv run python scripts/check_runtime.py
```

Phase-specific proof: `python3 -c` over
`dist/multi-agent/.claude/settings.json` shows UserPromptSubmit runs
`checkpoint` and Stop still runs `claude-stop.sh`; timing
`state-sync.sh checkpoint` on a clean nested repository is well under one
second and performs no network call (run with the network disabled or with
Git Trace2 to show no remote transport).

## Risks And Fallback Paths

- A machine that loses its session without a Stop event publishes later than
  before. Post-commit publication and SessionStart pull on the next machine
  bound the gap to uncommitted-between-commits state. If that is not
  acceptable, cancel this phase.

## Done Criteria

- Prompt submission performs no remote Git operation on any target.
- Stop, SessionEnd, and post-commit publication unchanged.
- Docs and validator match the generated settings.

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
