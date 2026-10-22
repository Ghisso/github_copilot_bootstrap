# Behavioral Evaluation Pilot: Phase A Evidence

**Date:** 2026-10-06

**Plan:** [Behavioral Evaluation Pilot](../.claude/plans/behavioral-evaluation-pilot.md)

**Phase:** [Phase A small plan](../.claude/plans/2026-10-03_phase-A-behavioral-pilot-evidence.md)

**Decision:** Stop the pilot after Phase A; cancel Phases B and C; continue with Phase D.

Phase A tested whether the native Claude Code reviewer role could be loaded and
whether the frozen review case could distinguish one defective change from
three controls. The source revision was the full merge
`a6346968c5bb1fdc4ee4fc1dca43e23d327af3fd`. The client reported version
`2.1.226`. The generated reviewer configuration selected model `sonnet` with
effort `xhigh`; the saved role output reported model `claude-sonnet-5`. No
client-selected-agent field was present.

## Frozen inputs

The synthetic fixture is in
[`tests/fixtures/behavioral/requirement-review/`](../tests/fixtures/behavioral/requirement-review/).
It contains three approved requirements, an optional approved scope change,
one defective diff, and three controls:

| Variant | Expected judgment |
| --- | --- |
| `defective` | Detection: the change removes repeated values without an approved change. |
| `repaired` | No detection. |
| `valid-alternative` | No detection. |
| `approved-change` | No detection because `SC-001` supersedes `REQ-003`. |

The expected results and rubric were written before the native runs. The
rubric accepts any wording that identifies the loss of repeated values; it
never requires a requirement ID. The rubric was not changed after the runs.

The [frozen manifest](evidence/behavioral-pilot/phase-a/manifest.json)
records the source revision, run order, 420-second timeout, five-run budget,
and SHA-256 hashes for the generated consumer, fixture, runner, and related
inputs. The saved records are [role-loading](evidence/behavioral-pilot/phase-a/role-loading.json),
[defective](evidence/behavioral-pilot/phase-a/defective.json),
[repaired](evidence/behavioral-pilot/phase-a/repaired.json),
[valid-alternative](evidence/behavioral-pilot/phase-a/valid-alternative.json),
and [approved-change](evidence/behavioral-pilot/phase-a/approved-change.json).
The consolidated [judgments](evidence/behavioral-pilot/phase-a/judgments.json)
file records the manual result for every scheduled run.

## Probe contract

Each packet was rendered in memory from the fixture before any native call.
The packet contained the requirements, the optional scope change, and one
diff. It excluded the expected answers and rubric. The scratch probe checked
the frozen hashes, used an isolated disposable consumer and per-run client
runtime, bounded the final result to 32,000 characters, and created the result
directory exclusively to prevent accidental reruns. Process groups were
isolated and timed out through the existing native-client runner. Raw client
events were discarded after parsing, and stderr was discarded without saving.
These details describe the
completed evidence contract; the scratch script is not a committed runner.

The exact invocation shape was:

```text
claude -p --agent reviewer --permission-mode dontAsk
  --no-session-persistence --output-format FORMAT [--verbose]
  --strict-mcp-config --disallowedTools Edit,Write,Bash,mcp__* -- PACKET
```

The role-loading probe used `--output-format stream-json --verbose` with the
repaired packet. The four case calls used `--output-format json`, in this
order: `defective`, `repaired`, `valid-alternative`, `approved-change`.
Every call used `--agent reviewer`, a 420-second timeout, and no retry, model
change, or effort change. The five-call budget was consumed.

For the one saved output, validity means that the final text contains the
reviewer's `## Review Report` heading and a fenced JSON findings block that
parses as `[]`. This validity check applies only to the saved output. An
unavailable client exit is not a valid empty review and is not a control pass.

## Results

The role-loading output is **consistent with** reviewer role loading. It has
the expected report shape and a parseable empty findings list, but the client
reported no selected-agent field. Its report says:

> REQ-001, REQ-002, and REQ-003 all remain satisfied; this is a valid alternative implementation, not a deviation.

The manual judgment is valid output, no detection, and no control false
positive. This is evidence about the role probe only; it does not replace any
scheduled case run.

All four scheduled case runs returned `nonzero_client_exit` and saved no final
task output:

| Run | Status | Judgment |
| --- | --- | --- |
| `defective` | Unavailable: `nonzero_client_exit` | No detection judgment; unavailable runs remain outside the valid denominator. |
| `repaired` | Unavailable: `nonzero_client_exit` | No control judgment; unavailable is not a pass. |
| `valid-alternative` | Unavailable: `nonzero_client_exit` | No control judgment; unavailable is not a pass. |
| `approved-change` | Unavailable: `nonzero_client_exit` | No control judgment; unavailable is not a pass. |

The consolidated counts are:

| Measure | Count |
| --- | ---: |
| Scheduled native runs | 5 |
| Saved outputs | 1 |
| Unavailable runs | 4 |
| Invalid outputs | 0 |
| Missing judgments | 0 |
| Valid defective case runs | 0 |
| Defective detections recorded | 0 (no valid defective runs) |
| Valid control case runs | 0 |
| Control false positives recorded | 0 (no valid control runs) |
| Valid repaired role probes | 1 |
| Role-probe false positives | 0 |

The four unavailable case runs leave both the defective and control
denominators at zero. They are not model failures, successful negative
controls, or evidence of no difference. The retained records do not identify
why the Claude client exited nonzero because raw errors were not saved.

## Privacy and limits

The evidence saves only bounded synthetic final output and allowlisted
metadata: client version, model and simple agent fields when present, timing,
turn and token counts, run names, status, and fixed reasons. It does not save
credentials, raw client transcripts, stderr, or user paths. The role-loading
record shows the reported model `claude-sonnet-5`; it does not establish that the
reviewer agent was selected because no client-selected-agent field was
reported.

This is one synthetic requirement-review fixture, one client, and one native
session that produced a saved task output. It provides no generalization
beyond this run. It also provides no before/after comparison, detection rate,
or production-runner evidence. No production runner changes were made, and no
implementation-scope change or rubric change occurred.

## Decision

BEP-001 holds at the exact level **consistent with** role loading. BEP-002 is
unproven because all four scheduled case runs are unavailable. The approved
stop rule therefore cancels Phase B, the runner work, and Phase C, the
before/after comparison. Phase D proceeds to record the stopped pilot and
perform its planned knowledge refresh and audit. No native rerun is made: the
five-run budget is consumed, and the evidence remains frozen.
