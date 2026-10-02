---
name: 2026-10-03_phase-B-behavioral-pilot-runner
type: small-plan
parent_plan: behavioral-evaluation-pilot
phase_index: 2
status: planned
closeout_session_log:
---

# Small Plan: Behavioral Pilot Runner Support

## Scope

Add the smallest runner support the comparison needs, using Phase A's
frozen fixture and the findings in Phase A's evidence document. Covers
BEP-003, BEP-004, and BEP-007. This plan is provisional: before it starts,
the orchestrator revises any step that Phase A's evidence changes (for
example the output format the scorer parses). If Phase A stopped, this
phase is cancelled with evidence instead.

## Steps

- [ ] **1. Optional source root for generation.**
  **Owner:** coder.
  **Files:** modify `scripts/check_native_clients.py` and
  `tests/test_check_native_clients.py`.
  **Required Skills:** `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/code-style/SKILL.md`,
  `.claude/skills/testing-patterns/SKILL.md`.
  Add a `--source-root PATH` option used with `--prepare-only`. When given,
  `prepare_variants` runs that tree's own `scripts/generate_targets.py`
  instead of the one under `REPO_ROOT`; when absent, behavior is byte-for-byte
  unchanged. Reject a source root that lacks that generator or that sits
  inside the workspace. Keep the workspace safety rules,
  the marker, the shim control/candidate pair, and read-only locking.
  **Acceptance:** existing tests pass unchanged; new tests cover the default
  path, an exported tree, and each rejection.

- [ ] **2. The requirement-review case and evidence capture.**
  **Owner:** coder.
  **Files:** modify `scripts/check_native_clients.py`,
  `tests/test_check_native_clients.py`, and `docs/native-client-acceptance.md`.
  **Required Skills:** `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/testing-patterns/SKILL.md`.
  Add `--behavioral-case requirement-review` with `--repetitions N` and
  `--evidence-out DIR`. It runs only on Claude Code, in a prepared workspace,
  with the Phase A argv shape (`--agent reviewer`, prompt after `--`, packet
  inline), one fixture variant per run. It rejects `--planner-workloads`, a
  Codex client, and an `--evidence-out` inside the repository or workspace.
  It saves, per run, only the bounded final result text and allowlisted
  metadata (variant, repetition, source root, client version, reported
  model, duration, usage). It never saves raw events, transcripts,
  credentials, or user paths. Legacy modes keep their raw-output disposal.
  **Acceptance:** tests with `run_process` doubles show the argv shape, the
  rejections, and that a private-output marker never reaches saved evidence
  or the report.

- [ ] **3. Offline scorer and replay.**
  **Owner:** coder.
  **Files:** modify `scripts/check_native_clients.py` and
  `tests/test_check_native_clients.py`.
  **Required Skills:** `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/testing-patterns/SKILL.md`.
  Add `--score DIR`, which reads saved evidence, compares each output with
  `tests/fixtures/behavioral/requirement-review/expected.json`, and prints
  JSON counts per variant: correct, behavioral failure, invalid output,
  unavailable run, and missing observation, each with its denominator. It
  never calls a model. Parse the output the way Phase A's evidence document
  decided. A malformed or empty output is invalid, never a pass or a fail.
  **Acceptance:** replaying Phase A's saved real outputs in
  `docs/evidence/behavioral-pilot/phase-a/` reproduces the outcomes the
  evidence document recorded; synthetic tests cover each category and a
  duplicate or missing variant.

- [ ] **4. Review, document, and close out.**
  **Owner:** reviewer; documenter after review converges; orchestrator.
  **Required Skills:** `.claude/skills/code-review/SKILL.md`,
  `.claude/skills/documentation/SKILL.md`.
  Review old-invocation compatibility, workspace and output privacy, the
  scorer's independence from the outputs it scores, and that no ordinary
  test or `verify.py` path can start a model.

## Verification

```bash
uv run pytest tests/test_check_native_clients.py -q
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- One user-run smoke session of the new case mode (one repetition of the
  defective variant) in the Phase A workspace, to confirm the argv shape
  end to end. Host-only; not a gate.

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
