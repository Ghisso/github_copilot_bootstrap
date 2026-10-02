---
name: behavioral-evaluation-pilot
type: big-plan
status: planning
originating_branch: dev
implementation_branch: behavioral-evaluation-pilot_implementation
started_at:
phases:
  - 2026-10-03_phase-A-behavioral-pilot-evidence
  - 2026-10-03_phase-B-behavioral-pilot-runner
  - 2026-10-03_phase-C-behavioral-pilot-comparison
  - 2026-10-03_phase-D-behavioral-pilot-knowledge-refresh
current_phase:
---

# Big Plan: Behavioral Evaluation Pilot

## Context

Big plan `engineering-workflow-improvements` (branch
`engineering-workflow-improvements_implementation`, commits `ca0fb37`,
`1d0ead1`, `d035226`) changed the reviewer: it now compares the diff against
the approved requirements and approved scope-change records. Its tests prove
the guidance text ships. They do not prove a model behaves differently.
That plan deferred REQ-006, a bounded behavioral evaluation, to this plan.
The approved design for it is
`.claude/explorations/2026-10-02_bootstrap-engineering-workflow/behavioral-evaluation-pilot.md`.

This plan starts after the user merges `engineering-workflow-improvements`
into `dev`. Its "after" revision is that merge commit on `dev`. Its "before"
revision is `1626364`, the `dev` commit just before that work.

The question is narrow: for one ordinary code-review task, does the
reviewer's new requirement-comparison guidance change whether a missing
requirement is reported? A "no difference" answer is a valid result.

Approved decisions (user, 2026-10-03):

- The plan is approved for implementation after the merge.
- Native run budget: at most 5 Claude Code runs in Phase A and at most 12
  in Phase C, each limited to 420 seconds (about 2 hours of runtime at the
  ceiling). The user runs each native step in their own shell from a script
  the orchestrator prepares.
- Claude Code is the only client.

## Goals

- Prove that the test actually loads the reviewer role and can tell a
  defective change from correct ones, before any comparison.
- Compare the "before" and "after" reviewer on that one case, with one fixed
  runner and one fixed scorer.
- Report the result honestly, including "no difference" or "inconclusive".
- Finish with the required knowledge refresh and the follow-ups left by the
  previous plan.

## Non-Goals and Constraints (optional)

- One client only: Claude Code. Codex `exec` does not select a specialist
  agent (`scripts/check_native_clients.py` `codex_workload_command`), so it
  cannot load the changed reviewer prompt.
- One case only: requirement review. The planner and original-symptom cases
  from the pilot design stay deferred.
- No new provider registry, SDK, model judge, dashboard, prompt optimizer,
  or commit gate. Ordinary tests and `verify.py` never call a model.
- Keep `--planner-workloads`, the shim control/candidate experiment,
  `shared/schemas/native-client-observation.schema.json`, and the existing
  report keys unchanged.
- Never save credentials, raw client transcripts, or user paths. Save only
  the bounded final task output of synthetic fixtures.
- Native runs need an authenticated, trusted Claude Code session. In auto
  mode the safety classifier has denied nested `claude -p` probes in this
  repository (`.claude/MEMORY.md`), so the user runs each native step in
  their own shell from a prepared script, and the orchestrator checks the
  saved results.
- Budget ceiling (each run is limited to the runner's 420-second timeout):
  Phase A at most 5 native runs; Phase C at most 12 native runs. No automatic
  retries, model switching, or effort changes.

## Design Overview

Settle the decisive assumptions first (Phase A), with evidence and no
production code. Phase A also freezes the test case. Then add the smallest
runner support (Phase B): an optional source root for generation, the one
case, and an offline scorer. Then run the comparison and publish a dated
result (Phase C). Then refresh the knowledge layer and audit live advice
(Phase D).

The case is an ordinary code-review request. It supplies approved
requirements and a diff, never names the defect, and never asks for a
"requirements check". The expected results are written before any run and
are never given to the model.

### Decisive assumptions

A decisive assumption is one that would invalidate this design if false.

| Assumption | Status | Evidence or remaining limit |
| --- | --- | --- |
| One fixed runner can build consumers from an older revision | Settled | An exported `1626364` tree (`git archive`) generated cleanly with its own `scripts/generate_targets.py`; its reviewer prompt lacks "approved scope-change records" (0 matches), while the current build has it (1). |
| `claude -p --agent reviewer` loads the generated reviewer prompt | Open (Phase A) | `--agent planner` ran in the 2026-08-09 calibration with Claude Code 2.1.226 (`docs/2026-08-09-planner-reliability-calibration.md`), and the generated planner and reviewer files have the same frontmatter shape. Loading the reviewer itself is not yet observed. |
| A client-reported field can show which agent ran | Open (Phase A) | Unknown. If none exists, the fallback is the reviewer's own report shape (`## Review Report`, a fenced findings JSON list), which is weaker, model-produced evidence and must be labeled that way. |
| The case flags the defective diff and none of the three correct controls | Open (Phase A) | Not observed. If the case cannot tell them apart, stop: cancel Phases B and C with evidence. |
| The case packet can be given inline in the prompt | Open (Phase A) | The reviewer accepts "the exact changed hunks" as scope (`shared/agents/reviewer/prompt.md` Inputs), so no file staging inside the locked workspace should be needed. |

## Requirement Map (optional)

IDs are prose references for this plan only.

| Requirement | Acceptance and existing contract | Owning phase | Evidence |
| --- | --- | --- | --- |
| BEP-001 | Role loading for the Claude reviewer is shown with the strongest available evidence class, and that class is named. | `2026-10-03_phase-A-behavioral-pilot-evidence` | Dated evidence document |
| BEP-002 | On the "after" revision, the case flags the defective diff and does not flag the repaired, approved-scope-change, or valid-alternative control. The prompt never names the defect. | `2026-10-03_phase-A-behavioral-pilot-evidence` | Dated evidence document; frozen fixture and expected results |
| BEP-003 | One fixed runner prepares consumers from a given source tree. Without the new option, every existing invocation, report key, and privacy rule is unchanged (`prepare_variants`, `safe_workspace`, `claude_workload_command`). | `2026-10-03_phase-B-behavioral-pilot-runner` | Offline tests in `tests/test_check_native_clients.py` |
| BEP-004 | An offline scorer compares saved outputs with the frozen expected results. It counts correct results, behavioral failures, invalid outputs, unavailable runs, and missing observations separately, and replays saved outputs without a model. | `2026-10-03_phase-B-behavioral-pilot-runner` | Offline tests |
| BEP-005 | A bounded before/after comparison on Claude Code, with a dated report: run counts, denominators, settings, source revisions, confounders, and saved outputs. "No difference" is allowed. | `2026-10-03_phase-C-behavioral-pilot-comparison` | Dated report; replay test reproduces its counts |
| BEP-006 | Knowledge refresh and final audit, including the follow-ups below. | `2026-10-03_phase-D-behavioral-pilot-knowledge-refresh` | OpenWiki completion; `## Stale-claims surfaces checked` |
| BEP-007 | Boundaries hold: no model call in ordinary tests or `verify.py`; no new gate; native steps run by the user; no credentials or transcripts saved. | all phases | Review and existing tests |

Follow-ups from the previous plan, owned by Phase D:
`shared/templates/skill-template.md` names only `shared/skills/`; four
OpenWiki claim ranges in `scripts/validate_targets.py` start one line early;
two agents-page claims have incomplete evidence ranges; the sidecar planner
prompt lists only big-plan statuses
(`shared/agents/planner/workflow-prompt.md:15`).

## Phases

- [ ] `2026-10-03_phase-A-behavioral-pilot-evidence` — settle role loading and case sensitivity with native evidence; freeze the fixture and expected results; no production code.
- [ ] `2026-10-03_phase-B-behavioral-pilot-runner` — add the optional source root, the one case, and the offline scorer, with tests (revised after Phase A if its evidence requires it).
- [ ] `2026-10-03_phase-C-behavioral-pilot-comparison` — run the bounded before/after comparison and publish the dated report.
- [ ] `2026-10-03_phase-D-behavioral-pilot-knowledge-refresh` — refresh OpenWiki, run the final audit, and close the follow-ups.

Stop rule: if Phase A cannot show role loading (BEP-001) or case
sensitivity (BEP-002), cancel Phases B and C with the cancellation evidence
contract and still run Phase D, which records the negative result.

## Ownership and Required Skills

The main-thread orchestrator owns activation, native-run handoff to the
user, result checks, findings, closeout, commits, and pushes. A coder owns
fixtures, runner code, and tests. A fresh reviewer reviews each phase. A
documenter writes the dated documents and live-doc updates after review.

Every coding step uses `.claude/skills/ponytail/SKILL.md` (full),
`.claude/skills/code-style/SKILL.md`, and
`.claude/skills/testing-patterns/SKILL.md`. Native probes use
`.claude/skills/integration-gate-spike/SKILL.md`. Each phase uses the
`code`, `architecture`, `security`, `tests`, `ponytail`, and `documentation`
review profiles.

## Test Strategy

- Critical case: the defective diff must produce a requirement finding.
- Negative cases: the repaired, approved-scope-change, and valid-alternative
  controls must not produce one (false-positive checks).
- Real integration: native Claude Code runs in a prepared workspace (user-run).
- Mocked boundaries: runner and scorer unit tests use the existing
  `run_process` doubles in `tests/test_check_native_clients.py`.
- Independent expected values: written with the fixture in Phase A, before
  any native run, and kept out of every prompt.
- No available verification: whether the result generalizes beyond one
  case, one client, or one model. The report must say so.

## Risks and Dependencies

- A strong model may report the missing requirement with or without the new
  guidance (ceiling effect). Then the result is "no difference", which is
  still useful evidence.
- Role loading may only be observable through the report shape. Label that
  evidence as model-produced, not client-reported.
- Results come from a few runs of one model; they are a diagnostic, not a
  statistical claim.
- The two consumers differ by the whole `engineering-workflow-improvements`
  diff (agent prompts, review profiles, policies, skills, templates, sidecar
  guidance, docs), not only the reviewer prompt. Checked during planning:
  `git diff 1626364 d035226` changes no hook and no script. Phase C records
  the same check against the merge commit, so the report states exactly
  what differed.
- Native steps depend on the user's shell, login, and trust state. An
  unavailable client is recorded as unavailable, never as a pass or fail.

## Verification Strategy

Small plans list their required commands. Native runs are optional,
host-only evidence and never enter `verify.py` or a receipt.

```bash
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Completion Evidence

Phase A's dated evidence document records BEP-001 and BEP-002. Phase C's
dated report records BEP-005 and links the saved outputs. The Phase D log
maps BEP-001 to BEP-007 to evidence and records the audit under
`## Stale-claims surfaces checked`. One commit per completed phase and one
normal push attempt each; PR creation and merge stay the user's decision.
