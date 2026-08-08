---
name: 2026-08-04_phase-M-role-matrix-correction-and-dogfood-drift
type: small-plan
parent_plan: bootstrap-guidance-runtime-modernization
phase_index: 13
status: complete
closeout_session_log: .claude/session_logs/2026-08-09_bootstrap-guidance-runtime-modernization-phase-M.md
---

# Small Plan: 2026-08-04_phase-M-role-matrix-correction-and-dogfood-drift

## Scope

Two things Phase L got wrong or left open, now resolvable without Codex quota.

### 1. The role matrix passes; Phase L's blockers were CLI artifacts

Phase L concluded `codex_role_matrix` could not be measured and listed five
blockers. Operator runs on 2026-08-09 disproved two of them. Spawning all six
roles works in **both** the interactive Codex CLI and the VS Code extension.
Twelve child threads across two interfaces, every one matching the installed
configuration:

| Role | Client-recorded model | Effort |
| --- | --- | --- |
| orchestrator | `gpt-5.6-sol` | xhigh |
| planner | `gpt-5.6-sol` | max |
| coder | `gpt-5.6-terra` | high |
| reviewer | `gpt-5.6-sol` | high |
| documenter | `gpt-5.6-terra` | medium |
| verifier | `gpt-5.6-luna` | low |

Evidence is client-emitted twice over: the spawn events, and each child's own
persisted session record under `~/.codex/sessions` (`payload.model`,
`payload.effort`). Not model prose.

Corrections required to the Phase L record:

- Blocker 2 ("no spawn even without `--ephemeral`") was scoped to
  `codex exec`, not to Codex generally.
- Blocker 4 ("project agents unreachable from `spawn_agent`", citing
  openai/codex #14579/#18823) was wrong as stated. The agents are reachable
  from any persistent-thread interface.
- The real blocker is the probe's own choice of `codex exec`, which has no
  persistent thread. Not an upstream defect.

Every child misreported its own model as "GPT-5" with effort "unspecified" or
"high". Accepting self-report would have produced the exact false negative the
shim exists to catch. This is the strongest available justification for the
client-metadata-only rule.

### 2. The dogfood overlay is stale and cannot be repaired as documented

`PreToolUse` hooks failed with exit 1 on every spawn, and one `SessionStart`
hook failed. `hooks-errors.log` records repeated `unparseable tool payload` and
`protected-file classifier exited with status 2`.

The installed overlay in this repository is a materially older generation:

- `.claude/hooks/scripts/protect-files.py` is **absent** (present in generated).
- `.claude/hooks/scripts/protect-files.sh` differs from generated.
- `.claude/hooks/scripts/pretool-bash-guard.sh` is absent.
- `.codex/hooks.json` differs from generated.
- All six `.codex/agents/*.toml` differ (documenter is installed as
  `gpt-5.6-terra`, generated as `gpt-5.6-luna`).

`check_runtime.py` reports this and prints the repair command
`install_bootstrap.py <consumer-repo>` — but that command **cannot repair this
repository**, because the installer refuses overlapping source and target:

```text
Generated source and target repository must be separate, non-overlapping
directories: source=.../dist/multi-agent; target=...
```

So the bootstrap's own dogfood overlay has no working refresh path. That is why
the drift has persisted across every phase of this plan.

## Not In Scope (blocked or needs a decision)

- **Proving the hooks are fixed.** Local payload replay shows the generated
  classifier is *stricter* than the installed one (it fails closed on `{}`
  where the old exits 0), so a refresh could change failure modes rather than
  remove them. Confirming requires a Codex run; quota resets 2026-08-15.
- **Choosing the repair mechanism.** Adding an opt-in self-target flag to
  `install_bootstrap.py` versus a separate dogfood-refresh path is a design
  decision that mutates the live control plane. Operator decision required.

## Steps

- [x] Correct the Phase L session log and plan: mark blockers 2 and 4 as
  CLI-scoped/incorrect, record the twelve-thread matrix evidence.
- [x] Correct `docs/native-client-acceptance.md` to state that the matrix
  passes on persistent-thread interfaces and that `codex exec` is the probe's
  own limitation.
- [x] Record the dogfood repair gap in `docs/runtime-checks.md`: the printed
  command cannot target this repository.
- [x] Do not change the installer or refresh the overlay in this phase.
- [x] Do not remove the MultiAgent V2 shim: routing was verified **with** the
  shim present; the candidate config was never exercised.

## Verification

```bash
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
```

## Acceptance Criteria

- No committed document still claims the role matrix is unmeasurable.
- The corrected records distinguish `codex exec` from persistent-thread
  interfaces.
- The dogfood repair gap is documented rather than silently tolerated.
- The shim remains in place.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
