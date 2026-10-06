---
name: 2026-10-03_phase-A-behavioral-pilot-evidence
type: small-plan
parent_plan: behavioral-evaluation-pilot
phase_index: 1
status: in-progress
closeout_session_log:
---

# Small Plan: Behavioral Pilot Evidence

## Scope

Settle the open decisive assumptions in the big plan with native evidence,
and freeze the one test case before any runner code exists. Covers BEP-001,
BEP-002, and BEP-007. No production code: only fixture data, one fixture
test, a scratch probe script that is never committed, and a dated evidence
document. This phase ends with an explicit proceed-or-stop decision.
Its native budget (at most 5 user-run Claude Code sessions) was approved
on 2026-10-03; see the big plan's approved decisions.

## Steps

- [x] **1. Author and freeze the requirement-review fixture.**
  **Owner:** coder.
  **Files:** create `tests/fixtures/behavioral/requirement-review/` with
  `requirements.md` (three approved requirements for one small function,
  for example: reject non-list input with `TypeError`; preserve input
  order; keep duplicates), `scope-change.md` (an approved scope-change
  record that supersedes the keep-duplicates requirement), four diffs
  (`defective.diff` drops duplicates; `repaired.diff` meets all three;
  `valid-alternative.diff` meets all three a different way;
  `approved-change.diff` drops duplicates as the scope change allows),
  `prompt.md` (the ordinary review request with placeholders for the
  requirements, optional scope change, and diff), `expected.json` (per
  variant: whether a detection is expected), `rubric.md` (the big plan's
  behavior-based detection and false-positive definitions, with two or three
  worked examples per definition, and the frozen conclusion rules; a
  requirement ID is never required), and `README.md` (what each file is for
  and its shortcuts; not a production reference). Add one test in
  `tests/test_check_native_clients.py` that checks only the fixed request
  wording of `prompt.md`, meaning everything outside the inserted
  requirements, scope-change, and diff blocks: it contains no phrase that
  names the defect or asks for a requirements check (for example "check
  requirements", "consistency review", "duplicate", or a requirement ID).
  The inserted requirements and scope-change blocks may name duplicates and
  requirement IDs, because they are legitimate inputs. The test also checks
  that `prompt.md` never references `expected.json` or `rubric.md`.
  **Required Skills:** `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/testing-patterns/SKILL.md`,
  `.claude/skills/code-style/SKILL.md`.
  **Acceptance:** expected results, rubric, and conclusion rules are written
  before any native run; the approved-change variant tests that an approved
  scope change supersedes a requirement; the fixture test fails if the
  request wording names the defect, and passes with duplicates named inside
  the requirements and scope-change blocks.

- [x] **2. Prepare the native probe.**
  **Owner:** orchestrator.
  **Files:** scratch only: a probe script in the session scratchpad and a
  dedicated workspace such as `/tmp/native-client-probe-behavioral` (outside
  `$HOME` and the repository, as `safe_workspace` requires).
  **Required Skills:** `.claude/skills/integration-gate-spike/SKILL.md`.
  Prepare the workspace with the existing
  `uv run python scripts/check_native_clients.py --client claude --workspace /tmp/native-client-probe-behavioral --prepare-only`.
  The script runs the reviewer in the prepared `control` consumer with the
  existing Claude command shape from `claude_workload_command`, but with
  `--agent reviewer` and the rendered prompt passed after `--`. It passes the
  packet inline (no file staging). It runs at most 5 native sessions: one
  role-loading probe with `--output-format stream-json --verbose`, then the
  defective, repaired, valid-alternative, and approved-change variants with
  `--output-format json`. From each run it keeps only the final result text
  and allowlisted metadata (client version, any client-reported agent or
  subagent field, reported model, duration, usage counts) and discards raw
  events in memory. It never saves credentials,
  user paths, or transcripts, and never changes trust or settings.
  **Acceptance:** the script's argv shape, kept fields, and budget are
  written down before the user runs it.

- [ ] **3. User runs the probe; orchestrator checks the saved results.**
  **Owner:** user runs the script in their own shell; orchestrator checks.
  **Files:** copy the bounded saved outputs to
  `docs/evidence/behavioral-pilot/phase-a/`.
  Record role loading at its exact level: "confirmed" when a client-reported
  agent field names the reviewer, or "consistent with" when only the
  reviewer's report shape (`## Review Report` plus a fenced findings JSON
  list) supports it. Judge each output against the frozen `rubric.md`, record
  one judgment per output with a quoted sentence as its reason, and compare
  it with `expected.json`. Record an unavailable or timed-out run as
  unavailable, never as a result.
  **Acceptance:** each variant has a rubric judgment or an explicit
  unavailable reason; no automatic retry.

- [ ] **4. Write the dated evidence document and the decision.**
  **Owner:** documenter, with the orchestrator's results.
  **Files:** create `docs/2026-10-03-behavioral-pilot-evidence.md` (use the
  actual date of the run).
  **Required Skills:** `.claude/skills/documentation/SKILL.md`,
  `.claude/skills/humanize/SKILL.md`.
  Record: the source revision and client version; the exact argv shape;
  the role-loading level ("confirmed" or "consistent with"); per-variant
  rubric judgments against expected results; how the scorer will check
  output validity (for example, whether the reviewer's findings JSON block
  parses); any rubric gap the outputs exposed; limits; and the decision.
  Proceed only when BEP-001 and BEP-002 both hold; "consistent with" is
  enough to proceed, but every later claim keeps that level. A rubric change
  is allowed only here, before Phase C, only to resolve an ambiguity the
  outputs exposed, and never to match one output's wording. A clarification
  rescores every Phase A output under the revised rubric. Keep the original
  rubric and judgments beside the revised ones, record the change and its
  reason, and freeze the revised rubric before Phase C.
  Otherwise state the stop
  and the evidence, so the orchestrator can cancel Phases B and C under the
  big plan's stop rule.
  **Acceptance:** a reader can reproduce the probe from the document; the
  decision follows the stop rule exactly.

- [ ] **5. Review and close out.**
  **Owner:** reviewer, then orchestrator.
  **Required Skills:** `.claude/skills/code-review/SKILL.md`.
  Re-check every rubric judgment against its saved output, and check that
  the rubric never requires a requirement ID. Check the fixture for answer
  leakage, the controls for false-positive
  coverage, the privacy of saved outputs, and the honesty of the evidence
  class. Before Phase B starts, the orchestrator runs the material-impact
  check and revises only affected future phases.

## Verification

```bash
uv run pytest tests/test_check_native_clients.py -q
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- The user-run native probe from step 3: at most 5 Claude Code sessions in a
  prepared, trusted workspace. Record client version, run count, and any
  unavailable run. This host evidence is required for the proceed decision
  but never becomes a deterministic gate.

## Review Profiles

Use `.claude/review-profiles/code.md`,
`.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
