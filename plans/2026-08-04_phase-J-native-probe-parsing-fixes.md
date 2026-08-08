---
name: 2026-08-04_phase-J-native-probe-parsing-fixes
type: small-plan
parent_plan: bootstrap-guidance-runtime-modernization
phase_index: 10
status: complete
closeout_session_log: .claude/session_logs/2026-08-09_bootstrap-guidance-runtime-modernization-phase-J.md
---

# Small Plan: 2026-08-04_phase-J-native-probe-parsing-fixes

## Scope

Phase I shipped `scripts/check_native_clients.py` without ever executing it
against a real Claude or Codex binary. Its first genuine run (Codex 0.147.0,
Claude Code 2.1.226, trusted workspace, authenticated) found two defects in the
probe itself.

1. **Codex result unreadable.** Codex returns the structured answer as a JSON
   *string* in an `agent_message` item (`item.completed -> item.text`).
   `find_structured_observation` walks nested dicts only and never parses an
   embedded JSON string, so a correct Codex answer is scored `FAIL`
   (`result_schema` / `client_schema_sentinel`).

2. **Claude invocation broken, then mislabelled.** `--disallowedTools` is
   variadic and swallows the positional prompt, so Claude exits non-zero with
   `Input must be provided either through stdin or as a prompt argument`. The
   probe maps *any* non-zero exit to `untrusted`, so a CLI argument bug is
   reported as a false claim about the operator's trust settings.

Defect 2's mislabelling is the more serious of the two: it makes the probe
assert something untrue about the environment, which is exactly the failure
mode Phase I existed to prevent.

## Ownership

- `coder`: observation parsing, Claude argv construction, failure
  classification, and regression tests.
- `verifier`: full suite, typing, linting, and the native matrix.
- `reviewer`: `code`, `architecture`, `security`, `tests`, `ponytail`.
- `documenter`: correct the Phase I record and the operator guide.

## Required Skills

- `ponytail` (`full`), `testing-patterns`, `run-tests`, `documentation`,
  `ponytail-review`.

## Steps

- [x] Parse embedded JSON string observations (Codex `agent_message.text`)
  in `find_structured_observation`, keeping the exactly-one-observation and
  sentinel-field rules intact.
- [x] Pass the probe prompt so a variadic option cannot consume it (`--`
  separator), for Claude and Codex alike.
- [x] Stop classifying every non-zero exit as `untrusted`. Reserve `untrusted`
  for a genuine trust/preflight failure and report an invocation failure
  distinctly.
- [x] Add regression tests using the real recorded output shapes from Codex
  0.147.0 and Claude Code 2.1.226, covering embedded-JSON parsing, the argv
  ordering guarantee, and the failure-classification split.
- [x] Correct the Phase I session log and plan: the earlier WARN was an
  outdated third-party Codex snap (0.114.0, publisher `jcat-nysasounds`) that
  could not parse `[features.multi_agent_v2]`, not a missing binary and not an
  untrusted workspace.
- [x] Re-run the native matrix and record the real result.

## Verification

```bash
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_native_clients.py \
  --workspace /tmp/native-client-probe-release --client all --json
```

## Acceptance Criteria

- A correct Codex answer parses as a valid observation instead of `FAIL`.
- Claude receives its prompt regardless of variadic option ordering.
- No failure path reports `untrusted` unless trust actually failed.
- The Phase I record states the real reason for its WARN evidence.

## Native Evidence Recorded

Codex 0.147.0 and Claude Code 2.1.226, trusted and authenticated workspace:

```text
claude  WARN   trust/root/scoped/workflow/hooks/shim/parity  PASS  (stable)
               compact_resume  WARN (unexercised)
codex   varies trust/root/workflow/hooks/shim/parity  PASS
               scoped_instruction_sentinel  PASS on one run, FAIL on two
               compact_resume, codex_role_matrix, coder_escalation  WARN (unexercised)
```

The probe now executes for real against both clients, which it never did in
Phase I. Claude passes every measurable check stably. Codex passes all but
`scoped_instruction_sentinel`, which is **non-deterministic across runs** and
is therefore not claimed as a pass.

Root cause of that instability, from inspecting the control workspace: the
generated Codex target has **no nested `AGENTS.md`**, which is Codex's native
scoped-instruction surface. The scoped policy exists only as
`.claude/instructions/*.instructions.md`, a Claude/Copilot surface. Codex is
being asked whether it discovered something that has no Codex-native
representation, so it answers inconsistently. That is a real finding about the
generated target or the probe's per-client definition, not model flakiness, and
it is outside this phase's parsing scope. Tracked for a follow-up phase.

One run also hit `codex_timeout` at the 120s default; Codex needs a longer
`--timeout` because it runs control and candidate consecutively.

The `unexercised` entries are hardcoded `WARN`: `compact_resume` is never
implemented, and `coder_escalation` has no stable client event to read. They
are honest gaps, deliberately left visible rather than scored as `PASS`.

## Native Evidence Expectations

Report what the matrix actually returns. A remaining non-`PASS` is acceptable
if it is a true observation honestly recorded; a `PASS` is claimed only when
both clients genuinely return valid observations.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
