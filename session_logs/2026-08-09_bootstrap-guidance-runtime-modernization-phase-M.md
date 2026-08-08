# Session: Bootstrap guidance/runtime modernization — Phase M

**Date:** 2026-08-09
**Plan:** .claude/plans/2026-08-04_phase-M-role-matrix-correction-and-dogfood-drift.md
**Status:** COMPLETED

## Goal

Correct the Phase L record now that the role matrix has been verified, and
diagnose the failing Codex hooks.

## 1. The Role Matrix Passes

Operator runs on 2026-08-09, Codex 0.147.0, spawned all six roles on **both**
the interactive CLI and the VS Code extension. Twelve child threads, every one
matching the installed configuration:

| Role | Model | Effort |
| --- | --- | --- |
| orchestrator | `gpt-5.6-sol` | xhigh |
| planner | `gpt-5.6-sol` | max |
| coder | `gpt-5.6-terra` | high |
| reviewer | `gpt-5.6-sol` | high |
| documenter | `gpt-5.6-terra` | medium |
| verifier | `gpt-5.6-luna` | low |

Client-emitted twice over: the spawn events, and each child's persisted session
record (`payload.model`, `payload.effort`).

### The self-report rule earned itself

Not one of the twelve children correctly identified its own model. All reported
"GPT-5"; efforts came back "unspecified" or "not exposed", two matching by
coincidence. Believing them would have yielded "routing is broken, everything
is GPT-5 with no tiering" — exactly the 0.144.x symptom, and exactly wrong.

### Corrections applied

Phase L blockers 2 and 4 described `codex exec`, not Codex. The agents are
reachable from any persistent-thread interface; the openai/codex #14579/#18823
citation was incorrect. Blockers 1, 3 and 5 stand, scoped to `codex exec`. The
real blocker is the probe's own interface choice — not upstream.

Corrected in: the Phase L session log, the Phase L plan,
`docs/native-client-acceptance.md`.

### The shim still stays

Routing was verified with `[features.multi_agent_v2]` **present**. The
candidate config was never exercised on a persistent-thread interface. This is
evidence the shim works, not that it is unnecessary.

## 2. Hook Failures: Diagnosed, Not Fixed

`PreToolUse` failed with exit 1 on every spawn; one `SessionStart` hook failed.
`hooks-errors.log` shows repeated `unparseable tool payload` and
`protected-file classifier exited with status 2`.

The installed overlay is a materially older generation than `shared/`:

- `.claude/hooks/scripts/protect-files.py` — **absent**
- `.claude/hooks/scripts/pretool-bash-guard.sh` — **absent**
- `.claude/hooks/scripts/protect-files.sh` — differs
- `.codex/hooks.json` — differs
- all six `.codex/agents/*.toml` — differ (installed `documenter` is
  `gpt-5.6-terra`; generated is `gpt-5.6-luna`)

### Why the drift survived every prior phase

`check_runtime.py` prints `install_bootstrap.py <consumer-repo>` as the repair.
That command **cannot repair this repository** — the installer refuses
overlapping source and target. The bootstrap's own dogfood overlay has no
working refresh path, so the failure has been unactionable all along.

Recorded in `docs/runtime-checks.md`.

### Deliberately not fixed here

Local payload replay shows the generated classifier is *stricter* than the
installed one — it fails closed on `{}` where the old exits 0. A refresh could
therefore change the failure mode rather than remove it. Confirming needs a
Codex run, and quota resets 2026-08-15. Claiming a fix without that evidence
would repeat the Phase I mistake.

The repair mechanism is also an open design decision (opt-in self-target flag
on `install_bootstrap.py` versus a separate dogfood-refresh path) that mutates
the live control plane. Operator decision required.

## Verification Results

```bash
uv run pytest tests/ -q --tb=short                               # 123 passed
uv run mypy . --ignore-missing-imports --explicit-package-bases  # PASS, 19 files
uv run ruff check scripts/ tests/                                # PASS
uv run python scripts/generate_targets.py --all                  # PASS
uv run python scripts/validate_targets.py                        # PASS
```

## Score: 100/100 — EXCELLENCE

- Findings: `.claude/quality_reports/findings-20260808T171800Z.json`
- Score: `.claude/quality_reports/score-20260808T171800Z.json`

## [LEARN] Entries

- [LEARN:testing] Twelve child agents each misreported their own model as
  "GPT-5". Client records showed all six routing correctly. Self-report is
  unreliable exactly where routing verification needs it most.
- [LEARN:tooling] A diagnostic that prints an inapplicable repair command
  makes a real failure unactionable. `check_runtime.py` flagged this drift
  correctly for months while its suggested fix could never work here.
- [LEARN:architecture] `codex exec` has no persistent thread and therefore
  cannot spawn agents. Interface choice, not client capability, decided what
  the probe could observe.

## Open Questions / Next Steps

- Decide the dogfood refresh mechanism, then refresh and re-test the hooks
  after quota resets (2026-08-15).
- Run the shim A/B on a persistent-thread interface to finally test
  removability.
- Consider driving `codex app-server` or `mcp-server` from the probe so
  `codex_role_matrix` becomes measurable.
