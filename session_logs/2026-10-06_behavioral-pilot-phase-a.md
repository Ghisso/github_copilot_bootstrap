# Behavioral evaluation pilot — Phase A

**Status:** IN PROGRESS
**Plan:** .claude/plans/2026-10-03_phase-A-behavioral-pilot-evidence.md

## Objective and authorization

Execute the approved pilot as main-thread orchestrator. The required merge is
present: `a6346968c5bb1fdc4ee4fc1dca43e23d327af3fd` on `dev`. The starting
outer worktree was clean. The approved plan requires the user to run native
Claude sessions from their own shell. No native sessions have run in this turn.

## Workflow tracking

- [x] PRE-FLIGHT: approved plan, Phase A, guidance, merge, and clean tree checked.
- [x] BRANCH: `behavioral-evaluation-pilot_implementation`; hook activated Phase A.
- [x] PLAN WHEN NEEDED: existing approved plan remains ready; planner not needed.
- [ ] IMPLEMENT: fixture, test, and scratch probe complete; native evidence and dated document remain.
- [ ] VERIFY: focused tests and fast checks; native evidence requires user action.
- [ ] REVIEW: no surviving pre-run findings; final review needs saved outputs.
- [ ] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT: repeat until checks and review pass.
- [ ] CLOSEOUT: evidence, judgments, dated document, findings, and receipts.
- [ ] COMMIT: one completed-phase commit after required gates.
- [ ] PUSH: one normal outer-repository push after commit.

## Decisions and probe contract

The probe is scratch-only: `/tmp/behavioral-pilot-phase-a.py`. It uses the
existing runner to prepare isolated runtime state and reap timed-out process
groups. The disposable consumer is `/tmp/native-client-probe-behavioral/control`.
The generated reviewer selects `sonnet`, effort `xhigh`; there is no override.
The role-loading probe reviews the repaired packet. Then the defective,
repaired, valid-alternative, and approved-change packets run, in that order.
Each invocation has a 420-second timeout. There are no retries.

The argv shape is `claude -p --agent reviewer --permission-mode dontAsk
--no-session-persistence --output-format FORMAT [--verbose]
--strict-mcp-config --disallowedTools Edit,Write,Bash,mcp__* -- PACKET`.
`FORMAT` is `stream-json` with `--verbose` for role loading and `json` for
the four variants. The planner-only JSON schema is omitted so the reviewer
can emit its ordinary report. The packet includes requirements, optional
scope change, and diff; expected answers and rubric are excluded.

Saved fields: bounded final result (maximum 32,000 characters), numeric
duration/turn/token fields, simple model and selected-agent fields, numeric
client version, run/variant names, elapsed time, status and fixed reason.
An available-agents list is not selected-agent evidence. Raw events and stderr
are discarded. Sensitive-looking or oversized final results are rejected.
An exclusive result-directory creation prevents accidental reruns. Input
hashes are frozen in `/tmp/behavioral-pilot-phase-a-freeze.json` and checked
before execution. All packets are rendered once before calls begin, with hash
checks around rendering, so later fixture edits cannot change later packets.

## Verification

- Workspace preparation: PASS using the existing `--prepare-only` command.
- Scratch probe Ruff check: PASS.
- Offline parser checks: PASS for final output, allowlist filtering, malformed
  and multiple final results, client errors, output limit, and user-path rejection.
- Plan frontmatter validation: PASS.
- Final focused suite after corrections: 41 passed.
- `verify.py fast --format json`: PASS (coder execution).
- All four diffs: dry-run application to baseline PASS (coder execution).
- Prompt test: REQ-003 negative mutation detected after fixing regex escaping.
- `git diff --check`: PASS.
- Probe `--freeze` then `--check-only`: PASS; no native calls.
- Native evidence: not run; handoff prepared at
  `/tmp/behavioral-pilot-phase-a-handoff.md`.

## Pre-run review

The independent reviewer used code, architecture, security, tests, ponytail,
and documentation profiles. The parent found and the coder corrected the
escaped requirement-ID regex and incorrect diff line counts. The reviewer
found that reading fixtures between calls could invalidate frozen-input
evidence; the orchestrator resolved it by rendering immutable packets before
execution and checking hashes around rendering. No surviving pre-run finding
was reported. The full Phase A review is WARN only because native outputs and
independent re-checks of every rubric judgment remain outstanding.

The default uv cache was read-only. Checks use
`UV_CACHE_DIR=/tmp/behavioral-pilot-uv-cache`. Branch creation needed the normal
sandbox escalation because `.git` is read-only in the default sandbox; it succeeded.

## Next steps

The next action is the user's one-shot command in the handoff. Then inspect saved
outputs, record rubric judgments, obtain independent re-checks, and follow
the proceed-or-stop rule. Phase B cannot begin without Phase A evidence.
Do not rerun native sessions or modify the frozen fixture. Results are expected
in `/tmp/native-client-probe-behavioral/phase-a-results/`. The phase remains
`in-progress`; no completed-phase commit or push is appropriate yet.

## [LEARN] Entries

No reusable lesson identified yet; this is an open session, not closeout evidence.
