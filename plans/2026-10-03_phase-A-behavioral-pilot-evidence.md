---
name: 2026-10-03_phase-A-behavioral-pilot-evidence
type: small-plan
parent_plan: behavioral-evaluation-pilot
phase_index: 1
status: planned
closeout_session_log:
---

# Small Plan: Behavioral Pilot Evidence

## Scope

Settle the open decisive assumptions in the big plan with native evidence,
and freeze the one test case before any runner code exists. Covers BEP-001,
BEP-002, and BEP-007. No production code: only fixture data, one fixture
test, a scratch probe script that is never committed, and a dated evidence
document. This phase ends with an explicit proceed-or-stop decision.

## Steps

- [ ] **1. Author and freeze the requirement-review fixture.**
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
  variant: whether a requirement finding is expected and which requirement),
  and `README.md` (what each file is for and its shortcuts; not a production
  reference). Add one test in `tests/test_check_native_clients.py` that
  rendered prompts for every variant contain no phrase that names the defect
  or asks for a requirements check (for example "check requirements",
  "consistency review", "duplicate", the expected requirement ID outside
  the requirements block), and that `expected.json` is never referenced by
  `prompt.md`.
  **Required Skills:** `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/testing-patterns/SKILL.md`,
  `.claude/skills/code-style/SKILL.md`.
  **Acceptance:** expected results are written before any native run; the
  approved-change variant tests that an approved scope change supersedes a
  requirement; the fixture test fails if the prompt names the defect.

- [ ] **2. Prepare the native probe.**
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
  and allowlisted metadata (client version, reported model, duration, usage
  counts) and discards raw events in memory. It never saves credentials,
  user paths, or transcripts, and never changes trust or settings.
  **Acceptance:** the script's argv shape, kept fields, and budget are
  written down before the user runs it.

- [ ] **3. User runs the probe; orchestrator checks the saved results.**
  **Owner:** user runs the script in their own shell; orchestrator checks.
  **Files:** copy the bounded saved outputs to
  `docs/evidence/behavioral-pilot/phase-a/`.
  Record, for role loading, the strongest evidence class observed: a
  client-reported agent field, or else the reviewer's report shape
  (`## Review Report` plus a fenced findings JSON list), labeled as
  model-produced. Score each variant by hand against `expected.json`.
  Record an unavailable or timed-out run as unavailable, never as a result.
  **Acceptance:** each variant has an outcome or an explicit unavailable
  reason; no automatic retry.

- [ ] **4. Write the dated evidence document and the decision.**
  **Owner:** documenter, with the orchestrator's results.
  **Files:** create `docs/2026-10-03-behavioral-pilot-evidence.md` (use the
  actual date of the run).
  **Required Skills:** `.claude/skills/documentation/SKILL.md`,
  `.claude/skills/humanize/SKILL.md`.
  Record: the source revision and client version; the exact argv shape;
  the role-loading evidence class; per-variant outcomes against expected
  results; what the output format means for the scorer (parse the
  reviewer's own findings JSON, or use a schema); limits; and the decision.
  Proceed only when BEP-001 and BEP-002 both hold. Otherwise state the stop
  and the evidence, so the orchestrator can cancel Phases B and C under the
  big plan's stop rule.
  **Acceptance:** a reader can reproduce the probe from the document; the
  decision follows the stop rule exactly.

- [ ] **5. Review and close out.**
  **Owner:** reviewer, then orchestrator.
  **Required Skills:** `.claude/skills/code-review/SKILL.md`.
  Check the fixture for answer leakage, the controls for false-positive
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
