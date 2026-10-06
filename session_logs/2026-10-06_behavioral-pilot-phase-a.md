# Behavioral evaluation pilot — Phase A

**Status:** COMPLETED
**Plan:** .claude/plans/2026-10-03_phase-A-behavioral-pilot-evidence.md

## Objective and authorization

Execute the approved pilot as main-thread orchestrator. The required merge is
present: `a6346968c5bb1fdc4ee4fc1dca43e23d327af3fd` on `dev`. The starting
outer worktree was clean. The approved plan requires the user to run native
Claude sessions from their own shell. The user ran all five approved sessions;
one role output was saved and all four scheduled case runs were unavailable.

## Workflow tracking

- [x] PRE-FLIGHT: approved plan, Phase A, guidance, merge, and clean tree checked.
- [x] BRANCH: `behavioral-evaluation-pilot_implementation`; hook activated Phase A.
- [x] PLAN WHEN NEEDED: existing approved plan remains ready; planner not needed.
- [x] IMPLEMENT: fixture, test, scratch probe, evidence, and judgments complete.
- [x] VERIFY: focused tests, fast checks, frozen hashes and saved records checked.
- [x] REVIEW: all five judgments independently reviewed; no findings.
- [x] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT: verification and review converged.
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
- optional 1: FAIL — five user-run Claude Code 2.1.226 sessions produced one saved role output and four unavailable nonzero_client_exit case runs; case sensitivity remains unproven and the stop rule applies. Evidence: `docs/evidence/behavioral-pilot/phase-a/`.

- Evidence check: PASS for frozen fixture hashes, five records, four unavailable
  runs, parseable role findings list, and five unique recorded judgments.

## Pre-run review

The independent reviewer used code, architecture, security, tests, ponytail,
and documentation profiles. The parent found and the coder corrected the
escaped requirement-ID regex and incorrect diff line counts. The reviewer
found that reading fixtures between calls could invalidate frozen-input
evidence; the orchestrator resolved it by rendering immutable packets before
execution and checking hashes around rendering. No surviving pre-run finding
was reported. The final evidence review is PASS, with no findings or open
requests. Every judgment was independently re-checked against its output.

## Result and stop decision

The dated document is `docs/2026-10-06-behavioral-pilot-evidence.md`.
The reviewer checked it after documentation and resolved its sole wording
finding; the final report has zero findings and no open requests.

BEP-001 is met at the exact level "consistent with". The repaired role probe
contains the reviewer heading and a valid empty findings list, but no
client-selected-agent field. The reported model is `claude-sonnet-5`.
BEP-002 is unproven: all four scheduled case runs are unavailable. Their
nonzero exits are not model review failures or valid negative controls.
There are zero valid defective case runs and zero valid control case runs;
the repaired role probe separately has zero false positives in one valid output.
No detection rate or before/after conclusion is available. All five calls
consumed the approved budget; no retry was attempted.

The approved stop rule cancels Phases B and C, with evidence at
`.claude/session_logs/2026-10-06_behavioral-pilot-cancellation.md`. Phase D
still runs. The unknown nonzero-exit cause is a stated limitation because raw
errors were discarded. No rubric change or material scope deviation occurred.

The default uv cache was read-only. Checks use
`UV_CACHE_DIR=/tmp/behavioral-pilot-uv-cache`. Branch creation needed the normal
sandbox escalation because `.git` is read-only in the default sandbox; it succeeded.

## Next steps

Finish the dated document and receipt checks, commit Phase A, attempt its
normal push, then activate Phase D. Do not rerun native sessions or modify the
frozen fixture. Phases B and C are cancelled, not deferred experiments.

## [LEARN] Entries

No new reusable lessons. The scratch packet-integrity issue was fixed and
checked before running; the client-exit cause remains unknown. These are
historical evidence and do not justify a new skill or MEMORY.md entry.
