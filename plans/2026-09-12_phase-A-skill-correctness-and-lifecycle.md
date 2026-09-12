---
name: 2026-09-12_phase-A-skill-correctness-and-lifecycle
type: small-plan
parent_plan: 2026-09-12_skill-library-hardening
phase_index: 1
status: planned
closeout_session_log:
---
# Small Plan: 2026-09-12_phase-A-skill-correctness-and-lifecycle

## Scope

Correct the verified factual, security, and lifecycle defects in the shared
skill library, and close the protected-path gap that leaves canonical skill
sources compressible.

Every change in this phase corresponds to a numbered row in the big plan's
`## Verified audit evidence` table. Each was confirmed against the working
tree before planning. Re-read each cited line before editing, because line
numbers drift as the files change.

This phase deliberately excludes judgment-heavy content work (routing
breadth, progressive disclosure, architecture assumptions). That work is
Phase B. This phase touches no vendored file and no generated target.

`shared/skills/ponytail/SKILL.md` and `shared/skills/ponytail-review/SKILL.md`
are out of scope. They are hash-pinned vendored files; see the big plan's
`## Decision: leave the vendored Ponytail pair unmodified`.

All edits go to canonical `shared/**` sources. Generated targets are produced
by `scripts/generate_targets.py --all`; never hand-edit a generated copy.

## Steps

- [ ] **Fix the verified factual and security defects (evidence rows 1-4).**
  - Modify `shared/skills/pandas-nan-bool-coercion/SKILL.md` (row 1).
    - Correct line 28: `isinstance(np.bool_(True), bool)` returns `False`.
      `np.bool_` subclasses `np.generic`, not Python `bool`.
    - Keep the useful NaN and boolean coercion guidance, and make the
      surrounding examples executable and internally consistent with the
      corrected claim.
    - Confirm the corrected behavior against the installed numpy before
      writing it down. Note that numpy is not currently installed in this
      repository's environment, so this must be checked where numpy is
      available rather than assumed.
  - Modify `shared/skills/text-to-sql-safety/SKILL.md` (row 2).
    - Correct line 22 ("enforced at the filesystem") and the line 34 comment
      ("enforced by SQLite/OS"). SQLite URI `?mode=ro` is a connection-level
      flag enforced by the SQLite library, not by the operating system, and
      an application bug can still open a writable connection.
    - Describe it as one connection-level defense among several.
    - Prefer a parser/AST approach or the SQLite authorizer callback where
      applicable, plus allowlists and bounded execution and resource limits.
    - Keep filesystem permissions as a separate, genuinely stronger boundary
      where the deployment permits them.
    - Do not present regex or string inspection as a complete SQL security
      boundary.
  - Modify `shared/skills/pyvis-xss-testing/SKILL.md` (row 3).
    - Lines 15-24 currently tell the reader to assert the raw payload is
      absent from serialized HTML. Absence of the raw payload is not proof
      that the output is safe when rendered.
    - Require testing the actual rendered sink or browser behavior, or the
      exact escaping boundary being relied on.
    - Keep the correct and useful observation that pyvis double-encodes HTML
      entities through JSON serialization, which is why naive assertions on a
      specific escaped form fail.
  - Modify `shared/skills/haystack-conditional-router/SKILL.md` (row 4).
    - Correct lines 23 and 29: `output_name` names the router's output
      socket, which is then connected to a downstream component input. It is
      not required to match the `add_component()` name.
    - Qualify version-sensitive Haystack behavior: state the tested or
      observed version, or instruct the agent to check the installed API when
      versions differ.
  - Verify with focused content checks and
    `uv run python .claude/scripts/verify.py fast --format text`.

- [ ] **Resolve the lifecycle conflicts (evidence rows 5-8).**
  - Modify `shared/skills/run-tests/SKILL.md` (row 5).
    - Line 40 currently reads
      `uv run python examples/run_*.py 2>/dev/null || echo "No E2E scripts"`,
      which reports a failing example command as an absent script.
    - Detect whether the example scripts exist before executing them, and
      report three distinct outcomes: scripts absent, scripts ran and passed,
      scripts ran and failed.
    - Never convert a real failure into a success-looking message.
    - Run explicitly requested or focused tests before broad suites.
    - Delegate final breadth to canonical phase verification instead of
      prescribing repeated full-suite runs.
  - Modify `shared/skills/code-review/SKILL.md` (rows 6 and 7).
    - Line 25 ("Fix findings by severity: critical, then major, then minor")
      conflicts with `shared/policies/workflow.instructions.md:139`: CRITICAL
      and MAJOR block the phase-completion commit, and a surviving MINOR is
      advisory but needs an explicit disposition and a non-empty reason.
    - Line 28 ("Save reports to
      `.claude/quality_reports/YYYY-MM-DD_review_[scope].md`") conflicts with
      `shared/policies/workflow.instructions.md:138`, where the orchestrator
      persists findings through `record_findings.py --out
      .claude/quality_reports/findings-<current_phase>.json` and the reviewer
      does not persist findings itself.
    - In lifecycle mode, return findings to the orchestrator.
    - Keep ad-hoc read-only review usable without lifecycle artifacts.
    - Reference the canonical severity contract rather than restating it in
      full, per the big plan's Cross-Model Principle 1.
  - Modify `shared/skills/test-helper-public-api/SKILL.md` (row 8).
    - Line 44 ("If no suitable public method exists, add one") tells the
      reader to widen the production API because a test lacks access.
    - Prefer asserting observable public behavior, or using an existing seam.
    - Add a production seam only when it is independently a useful
      application abstraction, not merely to satisfy a test.
    - Keep the skill's correct core point: a helper that chains private
      methods hides bugs in the public method real callers use.
  - Verify with focused tests covering failure propagation and severity
    semantics.

- [ ] **Close the protected-path gap (evidence row 9).**
  - Modify `shared/skills/caveman-compress/scripts/detect.py`.
    - Lines 171-177 protect `/shared/policies/`,
      `/.claude/skills/**/SKILL.md`, `/shared/agents/`, and
      `/shared/review-profiles/`, but not `/shared/skills/`. The canonical
      authoring source for every skill is therefore compressible while its
      generated copy is protected.
    - Add `/shared/skills/` to the protected set, matching the existing
      pattern style and suffix handling in that function.
  - Modify `shared/skills/caveman-compress/SKILL.md`.
    - Update the protected list at lines 45-48 so the documented set matches
      the detector's real behavior.
    - Preserve the skill's opt-in compression role; this change adds a
      protected path, it does not change when the skill runs.
  - This step changes a script, so it is control-plane work. Confirm the
    required review profiles are applied: `code`, `architecture`, `security`,
    `tests`, and `ponytail`.
  - Verify with a focused test asserting that a `shared/skills/**/SKILL.md`
    path is refused by the detector.

- [ ] **Bring the small-plan template up to the current closeout contract.**
  - Modify `shared/templates/plan-small.md`.
  - Do not remove a numeric-score lifecycle: it is already gone. All three
    copies are clean, and it was removed in commit `2af3df7`. Verify this
    before editing rather than assuming the original audit finding.
  - The template's existing closeout checklist already covers documentation,
    LEARN, the `COMPLETED` session log, staged-diff review, findings
    persistence, and `verify phase` then `verify closeout`. Two items are
    genuinely missing:
    - an explicit disposition and non-empty reason on every surviving MINOR;
    - the nested-state checkpoint, whose position in the closeout order is
      load-bearing.
  - Add only those two checklist lines, and point the template at the
    canonical closeout order in `shared/policies/workflow.instructions.md`
    rather than restating the full sequence. Restating a load-bearing
    sequence creates a second place for it to drift, which contradicts the
    big plan's Cross-Model Principle 1.
  - Review `shared/templates/plan-big.md` against the same contract and change
    it only if a concrete conflict is found.

- [ ] **Regenerate and validate.**
  - Run `uv run python scripts/generate_targets.py --all` after the canonical
    source edits. Never patch a generated copy directly.
  - Run the validators after generation, so they inspect a current tree.
  - Confirm `shared/skills/ponytail/SKILL.md` and
    `shared/skills/ponytail-review/SKILL.md` are byte-identical to their
    state at the start of this phase, and that their pinned hashes in
    `scripts/validate_targets.py` still match.

## Verification

Use focused checks while editing, then run the full authoring and runtime
checks before closeout. Generation runs before validation:

```bash
uv run python .claude/scripts/verify.py fast --format text     # during IMPLEMENT
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
uv run ruff format --check shared scripts tests
uv run python .claude/scripts/verify.py phase --format json --persist
uv run python .claude/scripts/verify.py closeout --format json --persist
```

Verification must specifically demonstrate:

- a failing example command is not reported as an absent script;
- the detector refuses a `shared/skills/**/SKILL.md` target;
- CRITICAL, MAJOR, and MINOR behavior in `code-review` matches
  `shared/policies/workflow.instructions.md`;
- the four corrected factual claims match observed behavior, with the numpy
  claim checked where numpy is actually installed;
- canonical `shared/**` sources regenerate target surfaces without drift;
- the vendored Ponytail hashes are unchanged.

## Closeout Checklist

- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] No generated target was hand-edited instead of its canonical `shared/**` source
- [ ] Vendored Ponytail files unchanged and their pinned hashes still match

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume
later. Set `status: paused`, record the three pause fields, and create a
session log with `**Status:** PAUSED`. A checkpoint preserves incomplete work
and does not complete or advance the phase.
