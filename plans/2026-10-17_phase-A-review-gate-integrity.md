---
name: 2026-10-17_phase-A-review-gate-integrity
type: small-plan
parent_plan: gate-repair
phase_index: 1
status: planned
closeout_session_log:
---

# Small Plan: Review Gate Integrity

## Scope

Make the commit and push gates check the review evidence they rely on.
Record the reviewer's own gate result and open requests, and block phase
completion unless the result is `PASS` with no open request (GR-001).
Require the review profiles that the branch's changed paths call for
(GR-002). Add the missing unit and installed-hook tests (GR-003), and prove
that a staged change after closeout blocks the commit (GR-004). All four
clients share `shared/scripts/verify.py`, the commit and push hook path, and
the installed Git hooks, so the change reaches Claude Code, Codex, GitHub
Copilot, and the Antigravity bridge at once. This phase lands first so every
later phase of this plan is reviewed under the repaired gate.

## Steps

- [ ] **1. Record and enforce the reviewer's gate result (GR-001).**
  **Owner:** coder.
  **Files:** modify `shared/scripts/record_findings.py`,
  `shared/scripts/verify.py` (`report_errors`, line 2227, and its callers),
  `scripts/validate_targets.py` (the recorder smoke run near lines
  7411–7540 and every completion findings fixture it builds, for example
  near lines 4642, 5909, 6031, 6104, 6402, 6586, 6821, 7110, 7221), and
  the tests named below.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Add a required `--gate-result` argument with choices `PASS`, `WARN`,
  `FAIL`, and a repeatable `--open-request TEXT`. Write `schema_version: 2`,
  `gate_result` (string), and `open_requests` (list of non-empty strings)
  into the report. Exit 1, writing nothing, when `--gate-result PASS` comes
  with any open request.
  In `report_errors`, at the commit gate (`exact` head relation, phase
  completion) add one error unless `gate_result == "PASS"` and
  `open_requests == []`; a report without `gate_result` gets an error that
  tells the operator to re-record it with `--gate-result` before closeout.
  At the push gates (`ancestor` and `certified` relations, called from
  `_lib-frontmatter.sh:1541` and `:1756`) apply the same rule only when
  `schema_version >= 2`, so completed phases recorded before the upgrade
  stay valid. Intermediate validation does not require the fields.
  **Tests:** `tests/test_verify.py` — at the commit gate `WARN`, `FAIL`, and
  `PASS` with an open request block, `PASS` with none passes, and a missing
  field blocks; at the push gates a schema-1 report without the field passes
  and a schema-2 `WARN` report blocks. `tests/test_commit_closeout.py` — the
  flag is required, `PASS` plus an open request is refused, and all three
  fields are written.
  **Acceptance:** a `WARN` review can no longer complete a phase, and no
  already-completed phase is re-judged. A self-reported `PASS` is still a
  recorded claim, not proof (see the big plan's risks).

- [ ] **2. Require review profiles by changed surface (GR-002).**
  **Owner:** coder.
  **Files:** modify `shared/scripts/verify.py` (`gate_receipt_errors`,
  about line 2011; `CONTROL_PLANE_FILES`; the dependency-file set).
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Add a pure function
  `required_review_profiles(paths: list[str]) -> frozenset[str]`. Check test
  surfaces first: a path under `tests/`, or a file named `test_*.py`,
  `*_test.py`, or `conftest.py`, requires `tests`. Otherwise use
  `classify_path`: a `control-plane` or `generator` path requires `code`,
  `architecture`, `security`, `tests`, and `ponytail`. Dependency files
  (`DEPENDENCY_FILES`, plus `pyproject.toml`, `requirements*.txt`,
  `requirements*.in`) require the same five. Add `.vscode/mcp.json` to
  `CONTROL_PLANE_FILES`. A documentation-only path requires none. In
  `gate_receipt_errors`, compute the requirement from the receipt's
  machine-produced `changed_paths` (bound by `tree_sha`); add no new path
  discovery in shell. Union it with the existing multi-file Ponytail rule,
  and report missing profiles by name in one error. The changed paths are
  cumulative from the merge-base, so a later phase keeps the requirements of
  earlier phases on the same branch; document that. The user approved this
  rule on 2026-10-17.
  **Tests:** a table-driven unit test with expected values written from the
  GR-002 table, not from the code: docs-only gives none; `tests/test_x.py`
  gives `tests`; `tests/fixtures/x.json` gives `tests`;
  `tests/fixtures/behavioral/requirement-review/requirements.md` gives
  `tests`; `scripts/x.py`, `shared/x.md`, `.mcp.json`, `.vscode/mcp.json`,
  `uv.lock`, and `pyproject.toml` give all five; `src/pkg/mod.py` gives
  none. Gate tests: a test-file diff whose report lacks `tests` blocks; a
  five-profile report passes a `scripts/` diff.

- [ ] **3. Add the missing unit and installed-hook tests (GR-003).**
  **Owner:** coder.
  **Files:** modify `tests/test_verify.py` and `scripts/validate_targets.py`
  (the installed-hook smoke that already covers Ponytail near lines
  6098–6112 and 6580–6600).
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/testing-patterns/SKILL.md`.
  In `tests/test_verify.py`, call `report_errors` with
  `require_ponytail=True` and a report without the `ponytail` profile, and
  assert the "requires a fresh Ponytail review" error. In the
  `validate_targets.py` smoke, add two cases next to the existing Ponytail
  case: a `WARN` report denied by the installed commit-msg hook, and a
  test-file diff whose report lacks `tests` denied. Do not build a new
  closeout harness in `tests/test_hook_gates.py`. Confirm locally that each
  new case fails when the check it covers is removed; do not commit that
  experiment.

- [ ] **4. Prove post-closeout drift blocks the commit (GR-004).**
  **Owner:** coder.
  **Files:** modify `tests/test_verify.py`; add one comment next to the
  `tracked_state_hash` writer in `shared/scripts/verify.py` (line 1707).
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/testing-patterns/SKILL.md`.
  Add a test where a documentation-only change, staged after the closeout
  receipt, makes the commit gate fail with "closeout receipt final tracked
  state is stale" (`git write-tree` reads the index; an unstaged change is
  caught by the `content_hash` check instead). The push variant is already
  covered near `scripts/validate_targets.py:7143`. The comment states that
  `tracked_state_hash` is informational and `tree_sha` is the binding
  check. No receipt schema change.

- [ ] **5. Update guidance, regenerate, review, document, close out.**
  **Owner:** coder for guidance text; orchestrator for generation,
  self-install, and closeout; fresh reviewer; documenter after review.
  **Files:** modify `shared/agents/reviewer/prompt.md` (Gate Result mapping:
  `FAIL` when a CRITICAL or MAJOR survives, `WARN` when a request is open,
  otherwise `PASS`; surviving MINORs with dispositions allow `PASS`),
  `shared/policies/quality-and-testing.instructions.md` (report fields; `[]`
  passes clean only with `gate_result: PASS` and no open request),
  `shared/policies/workflow.instructions.md` (the CLOSEOUT
  `record_findings.py` call), `shared/skills/code-review/SKILL.md` and
  `shared/skills/commit/SKILL.md` (command examples), and the orchestrator
  prompts only where they describe recording findings. Documenter: `README.md`
  "Upgrading a consumer with active work" and `docs/runtime-checks.md`
  "Mid-plan consumer upgrade": the current phase's report must be
  re-recorded with `--gate-result` before closeout; completed phases stay
  valid.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-review/SKILL.md`,
  `shared/skills/documentation/SKILL.md`.
  Run `uv run python scripts/generate_targets.py --all`, then
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  so the installed `.claude/scripts/` match before verification. Record
  this phase's own findings with the new `--gate-result` flag.
  **Acceptance:** GR-001 to GR-004 map to named tests in the closeout log.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/test_verify.py tests/test_commit_closeout.py tests/test_validate_targets.py tests/test_lifecycle_hooks.py -q
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- In priority order (Claude Code, then Codex), the user tries one commit in
  a disposable clone with a findings report recorded as `WARN`, and records
  that the native commit hook denies it.

## Review Profiles

Use `.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Give the reviewer the audit
(`.claude/explorations/2026-10-17_bootstrap-backlog-audit.md` §5 D2, D4, D5),
GR-001 to GR-004, and the final diff.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
