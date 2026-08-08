# Session: Native client acceptance — session wrap-up

**Date:** 2026-08-09
**Plan:** .claude/plans/bootstrap-guidance-runtime-modernization.md
**Status:** COMPLETED

## Scope Of This Session

Picked up a quota-interrupted handoff at Phase I and closed the big plan. Six
phases completed end to end (I closeout, J, K, L, M, N), each scored, logged,
and committed.

## What Happened

The session began by closing Phase I, which had passed every gate — 100/100,
clean two-pass review, zero findings — while shipping a native acceptance probe
that **had never been executed against a Claude or Codex binary**. Everything
after that followed from running it.

| Phase | Commit | Outcome |
| --- | --- | --- |
| I | `28ecfc9` | Closed as handed off; native evidence was WARN |
| J | `a80e59c` | Four probe defects found and fixed on first real run |
| K | `24d06c4` | Per-client scoped-instruction semantics; determinism restored |
| L | `3e5c44d` | `spawn_unsupported` evidence class; no speculative parser |
| M | `be0e405` | Role matrix verified; Phase L record corrected; dogfood drift diagnosed |
| N | `91fb509` | Phase extensions explained; false routing claims corrected |

## Environment Fixes Along The Way

- Codex was an outdated third-party snap (0.114.0, publisher
  `jcat-nysasounds`) that could not parse `[features.multi_agent_v2]` and
  aborted with `invalid type: map, expected a boolean`. Replaced with official
  `@openai/codex` 0.147.0 via npm.
- The npm global `bin` directory was not on `PATH`; `codex` was linked into
  `~/.local/bin` to match how `node` and `npm` are already exposed.

## The Result That Mattered

Six named roles route to their configured model and effort, verified natively:

| Role | Model | Effort |
| --- | --- | --- |
| orchestrator | `gpt-5.6-sol` | xhigh |
| planner | `gpt-5.6-sol` | max |
| coder | `gpt-5.6-terra` | high |
| reviewer | `gpt-5.6-sol` | high |
| documenter | `gpt-5.6-terra` | medium |
| verifier | `gpt-5.6-luna` | low |

Twelve child threads across the interactive CLI and the VS Code extension.
Evidence is client-emitted: spawn events plus each child's persisted session
record. **Not one child correctly identified its own model** — all reported
"GPT-5" with effort "unspecified". Believing them would have reproduced the
exact 0.144.x conclusion, wrongly.

## Verification At Session End

```bash
uv run pytest tests/ -q --tb=short                               # 123 passed
uv run mypy . --ignore-missing-imports --explicit-package-bases  # PASS, 19 files
uv run ruff check scripts/ tests/                                # PASS
uv run python scripts/generate_targets.py --all                  # PASS twice
uv run python scripts/validate_targets.py                        # PASS
uv run python scripts/validate_plan_frontmatter.py .claude/plans/*.md  # PASS
```

Big plan `status: complete`, 14 phases checked. Outer and nested trees clean.
Branch `bootstrap-guidance-runtime-modernization_implementation` is 14 commits
ahead of `dev`.

## Open Items (Deliberately Not Done)

1. **`--allow-self` installer flag.** The dogfood overlay in this repository
   cannot be refreshed: both `install_bootstrap.py` and `update_consumers.py`
   refuse overlapping source and target, and `check_runtime.py` prints a repair
   command that cannot work here. Operator decision: implement directly on
   `dev` after this PR merges, not on this branch.
2. **Hook failures.** `PreToolUse` failed with exit 1 on every spawn. Root
   cause is the stale overlay (absent `protect-files.py` and
   `pretool-bash-guard.sh`, differing `protect-files.sh` and
   `.codex/hooks.json`). Not fixed here: the generated classifier is *stricter*
   than the installed one, so a refresh could change the failure mode rather
   than remove it, and confirming needs Codex quota (resets 2026-08-15).
3. **MultiAgent V2 removal gate.** Still open. Routing was verified **with** the
   shim present; the shim-removed candidate has never been exercised on a
   persistent-thread interface. `tool_namespace = "agents"` is provably inert in
   0.147.0, but `hide_spawn_agent_metadata` remains untested. The shim stays.
4. **Probe cannot measure the matrix.** `check_native_clients.py` drives
   `codex exec`, which has no persistent thread and cannot spawn. Closing this
   means driving `codex app-server` or `mcp-server`.

## Next Step

Operator publishes the branch and opens a PR to `dev`. `--allow-self` lands on
`dev` afterwards.

## [LEARN] Entries

All lessons from this session were flushed to `.claude/MEMORY.md` at each phase
closeout (J, K, L, M, N). No new unrecorded lessons at wrap-up.
