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
Require the review profiles that the changed paths call for (GR-002). Prove
the required-Ponytail path blocks (GR-003). Prove that a tracked change
after closeout blocks through `tree_sha` (GR-004). All four clients share
`shared/scripts/verify.py` and the commit hook path, so the change reaches
Claude Code, Codex, GitHub Copilot, and the Antigravity bridge at once.
This phase lands first so every later phase of this plan is reviewed under
the repaired gate.

## Steps

- [ ] **1. Record and enforce the reviewer's gate result (GR-001).**
  **Owner:** coder.
  **Files:** modify `shared/scripts/record_findings.py`,
  `shared/scripts/verify.py` (`report_errors`, about line 2227), and the
  tests named below.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Add a required `--gate-result` argument with choices `PASS`, `WARN`,
  `FAIL`, and a repeatable `--open-request TEXT`. Write `gate_result` (string)
  and `open_requests` (list of non-empty strings) into the report. Exit 1,
  writing nothing, when `--gate-result PASS` comes with any open request.
  In `report_errors`, when `require_major` is true (phase completion), add
  one error unless `gate_result == "PASS"` and `open_requests == []`. A
  report with no `gate_result` gets an error that tells the operator to
  re-record it with `--gate-result`. Intermediate validation
  (`require_major` false) does not require the fields. Find every caller
  that validates already-completed phases (the historical chain) and keep
  their old reports valid: historical reports are never re-judged.
  **Tests:** `tests/test_verify.py` — `WARN` blocks, `FAIL` blocks, `PASS`
  with an open request blocks, `PASS` with none passes, missing field blocks
  at completion and passes for intermediate and historical validation.
  `tests/test_commit_closeout.py` — the flag is required, `PASS` plus an
  open request is refused, and both fields are written.
  **Acceptance:** a `WARN` review can no longer complete a phase. A
  self-reported `PASS` is still a recorded claim, not proof (see the big
  plan's risks).

- [ ] **2. Require review profiles by changed surface (GR-002).**
  **Owner:** coder.
  **Files:** modify `shared/scripts/verify.py`; modify
  `shared/hooks/scripts/_lib-frontmatter.sh` only when the gate cannot
  compute the changed paths itself.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Add a pure function
  `required_review_profiles(paths: list[str]) -> frozenset[str]` built on
  `classify_path`. A `control-plane` or `generator` path, or a dependency
  file (`DEPENDENCY_FILES`, `requirements*`), requires `code`,
  `architecture`, `security`, `tests`, and `ponytail`. A test surface
  requires `tests`. A test surface is a path under `tests/`, or a file named
  `test_*.py`, `*_test.py`, or `conftest.py`. A documentation-only diff
  requires none. Compute the paths from the same merge-base diff the gate
  already uses (working tree for commit, pushed ref for push). Union the
  result with the existing multi-file Ponytail rule. Report missing profiles
  by name in one error. The user approved this rule on 2026-10-17.
  **Tests:** a table-driven unit test of the pure function (docs-only, a
  `tests/` path, a fixture JSON under `tests/`, `scripts/`, `shared/`,
  `.mcp.json`, `uv.lock`, an ordinary `src/` module); gate tests where a
  missing `tests` profile blocks a test-file diff and a five-profile
  report passes a `scripts/` diff.

- [ ] **3. Test the required-Ponytail blocking path (GR-003).**
  **Owner:** coder.
  **Files:** modify `tests/test_verify.py` and `tests/test_hook_gates.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/testing-patterns/SKILL.md`.
  In `tests/test_verify.py`, call the findings check with
  `require_ponytail=True` and a report without the `ponytail` profile, and
  assert the "requires a fresh Ponytail review" error. In
  `tests/test_hook_gates.py`, drive the installed commit hook in a temporary
  repository with a two-file diff and an otherwise valid closeout whose
  findings omit `ponytail`, and assert a deny. Confirm locally that each new
  test fails when the check it covers is removed; do not commit that
  experiment.

- [ ] **4. Prove post-closeout drift blocks the commit (GR-004).**
  **Owner:** coder.
  **Files:** modify `tests/test_verify.py`; add one comment next to the
  `tracked_state_hash` writer in `shared/scripts/verify.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/testing-patterns/SKILL.md`.
  Add a test where a documentation-only tracked change after the closeout
  receipt makes the commit gate fail with "closeout receipt final tracked
  state is stale". The comment states that `tracked_state_hash` is
  informational and `tree_sha` is the binding check. No receipt schema
  change.

- [ ] **5. Update guidance, regenerate, review, document, close out.**
  **Owner:** coder for guidance text; orchestrator for generation,
  self-install, and closeout; fresh reviewer; documenter after review.
  **Files:** modify `shared/policies/quality-and-testing.instructions.md`
  (report fields; `[]` passes clean only with `gate_result: PASS` and no open
  request), `shared/policies/workflow.instructions.md` (the CLOSEOUT
  `record_findings.py` call), `shared/skills/code-review/SKILL.md` and
  `shared/skills/commit/SKILL.md` (command examples), and the reviewer and
  orchestrator prompts only where they describe how findings are recorded.
  Documenter: `README.md` "Upgrading a consumer with active work" and
  `docs/runtime-checks.md` "Mid-plan consumer upgrade" (a findings report
  written before the upgrade must be re-recorded with `--gate-result`).
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
uv run pytest tests/test_verify.py tests/test_commit_closeout.py tests/test_hook_gates.py tests/test_lifecycle_hooks.py -q
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
