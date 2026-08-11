---
name: 2026-08-09_phase-D-cancelled-phase-gates
type: small-plan
parent_plan: state-sync-recovery-and-plan-cancellation
phase_index: 4
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-09_phase-D-cancelled-phase-gates

## Scope

Teach the commit and push gates about cancelled phases. `assert_push_invariants`
currently refuses any branch whose phases are not all `complete`, requires one
commit per listed phase, and binds its final findings report to the last listed
phase. All three are wrong once a phase can be legitimately cancelled. This
phase accepts `cancelled` phases that carry full evidence, counts commits
against completed phases only, binds the findings report to the last completed
phase, requires at least one completed phase before push, blocks a commit whose
`current_phase` points at a cancelled phase, and makes the closeout hook skip
cancelled phases when advancing the pointer.

## Ownership

- `coder`: `shared/hooks/scripts/_lib-frontmatter.sh`,
  `shared/hooks/scripts/record-commit-closeout.sh`,
  `shared/hooks/scripts/enforce-branch-state.sh`,
  `scripts/validate_targets.py`, `tests/test_hook_gates.py`.
- `verifier`: full verification plus target generation and determinism.
- `reviewer`: the profiles listed below.
- `documenter`: skip for this phase; README and `docs/` land in Phase E.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` in `full` mode.
- `.claude/skills/code-style/SKILL.md` and
  `.claude/skills/testing-patterns/SKILL.md`.
- `.claude/skills/run-tests/SKILL.md` for the verifier.
- `.claude/skills/learn/SKILL.md` and `.claude/skills/commit/SKILL.md` at
  closeout.

## Review Profiles

- `.claude/review-profiles/code.md`
- `.claude/review-profiles/architecture.md`
- `.claude/review-profiles/security.md`
- `.claude/review-profiles/tests.md`
- `.claude/review-profiles/ponytail.md`

Review is mandatory here because this phase changes control-plane/high-risk
lifecycle code. This use of the Ponytail profile follows the current calibrated
review policy; it is not a return to universal Ponytail review for every diff.

## Cancellation Validation Authority

Phase C made the cancellation contract stricter than the original Phase D
draft. The Python frontmatter validator remains the authoring/pre-flight check,
but the push gate must independently enforce the same contract at action time.
Plan and evidence files are mutable after an earlier validator run, so relying
on that earlier result would create a time-of-check/time-of-use bypass.

`assert_cancellation_evidence` therefore repeats the full Phase C semantics. It
uses Bash 3.2-compatible orchestration and a fail-closed `python3` standard-
library probe for semantic date/time, raw frontmatter scalar shape, canonical
path, regular-file, UTF-8, and marker validation. Python 3 is already the
bootstrap runtime baseline and this adds no dependency. Missing Python, an
exception, malformed probe output, or any validation failure becomes a
distinct accumulated gate failure; none may escape or silently pass.

## Steps

- [ ] Add `assert_cancellation_evidence <plan_file> <phase_label>` to
      `shared/hooks/scripts/_lib-frontmatter.sh` (create). It follows the file's
      existing dynamic-scoping convention: it appends to a `failures` array the
      caller declares. Each failure gets its own distinct message naming the
      phase. Must be Bash 3.2 compatible: no `mapfile`, no `readarray`, no
      negative array indices.
- [ ] The helper must repeat Phase C timestamp and reason semantics rather than
      trust an earlier validator run. `cancelled_at` is non-empty, matches exact
      `YYYY-MM-DDTHH:MM:SSZ` UTC syntax, and is a real calendar date/time.
      `cancelled_reason` is meaningful plain single-line scalar prose: reject
      empty/whitespace/quoted-empty values, YAML block-scalar headers including
      modifiers and comment suffixes, list/object-like values, and indented
      continuation or multiline forms. Preserve accepted lookalike prose such
      as `| useful reason` and `>+9 prose`.
- [ ] The helper must require non-empty `cancelled_evidence` to be a
      repository-relative path. Reject absolute paths and any lexical `..`
      component before filesystem access. Canonically resolve the repository
      root and evidence target, follow symlinks, and reject any target outside
      the repository. Require an existing regular readable file whose complete
      contents decode as UTF-8; directories, missing files, symlink loops,
      outside symlinks, unreadable files, and decode errors all fail closed.
- [ ] Evidence must contain a line matching
      `^\*\*Status:\*\*[ \t]+CANCELLED\b`: horizontal whitespace only and the
      marker on one physical line. Split-line, vertical-whitespace, misspelled,
      lowercase, and word-character suffix near-misses must fail. The helper's
      standard-library probe must return a fixed machine-readable result that
      shell maps to distinct accumulated messages; missing Python, unexpected
      output, or an exception is itself a blocking failure.
- [ ] `assert_commit_invariants` (modify): when the current phase's small-plan
      status is `cancelled`, replace the generic
      "must have status: complete before commit" failure with a distinct message
      saying the phase is cancelled, that a commit is never certified by a
      cancelled phase, and that `current_phase` must be advanced past it. Leave
      every other check unchanged. Do not add a commit path for cancelled
      phases: `.claude/` is ignored by the outer repository, so recording a
      cancellation produces no outer commit and needs none.
- [ ] `assert_push_invariants` (modify), phase loop: accept `complete` or
      `cancelled`. Track `completed_count` and the slug of the last completed
      phase. For each `cancelled` phase, call `assert_cancellation_evidence`.
      For any other status, keep the current failure message.
- [ ] `assert_push_invariants` (modify): fail when `completed_count` is 0, with
      a message saying the branch certifies no work and should be deleted rather
      than pushed.
- [ ] `assert_push_invariants` (modify): change the commit-count comparison from
      `${#phases[@]}` to `completed_count`, and update the message to say "one
      commit per completed small plan".
- [ ] `assert_push_invariants` (modify): bind the final findings report to the
      last completed phase instead of `${phases[${#phases[@]}-1]}`. Keep the
      Bash 3.2 indexing style. Update the surrounding comment to explain that a
      cancelled trailing phase has no findings report and never will.
- [ ] Must not add a branch-level acknowledgement flag. The per-phase evidence
      contract is the whole anti-abuse mechanism; a second big-plan flag was
      considered and deliberately rejected as bookkeeping without new
      information.
- [ ] `shared/hooks/scripts/record-commit-closeout.sh` (modify): when advancing
      `current_phase`, skip forward over phases whose small-plan `status` is
      `cancelled`. When no non-cancelled phase remains, clear `current_phase`,
      and write `status: complete` only when the big plan's current status is
      not already `cancelled`, so the hook never overwrites a recorded human
      cancellation. Preserve the existing `additional_context` warn-on-miss
      paths so the phase machine never stalls silently.
- [ ] `shared/hooks/scripts/enforce-branch-state.sh` (modify): keep the existing
      `planning`/`in-progress` allow-list and extend the denial message to name
      `cancelled` explicitly as a terminal, non-startable status.
- [ ] Add adversarial scenarios to `scripts/validate_targets.py` (modify),
      extending the existing `write_small_plan` helper with a `cancelled`
      variant that writes the three fields and its evidence file.
- [ ] Add direct unit coverage to `tests/test_hook_gates.py` (modify) using the
      existing `_bash_source` harness.
- [ ] Regenerate targets.

## Test Scenarios

In `scripts/validate_targets.py`, driven by `tests/test_validate_targets.py`:

- [ ] Push accepted for a branch mixing completed and cancelled phases when all
      three conditions hold.
- [ ] Push refused when a cancelled phase is missing `cancelled_at`,
      `cancelled_reason`, or `cancelled_evidence` (one case each).
- [ ] Push refused when the evidence file does not exist.
- [ ] Push refused when the evidence file exists but lacks
      `**Status:** CANCELLED`.
- [ ] Push refused for absolute evidence paths, any lexical `..` traversal,
      canonical escape through an outside symlink, a symlink loop, a directory,
      an unreadable file where portable, and invalid UTF-8. Use unique paths so
      each scenario proves its intended branch rather than a prior failure.
- [ ] Push refused for malformed or impossible `cancelled_at` and for
      whitespace, YAML block-header/comment, collection/list, or multiline
      `cancelled_reason` values that Phase C rejects.
- [ ] Push refused for split-line or vertical-whitespace cancellation markers
      and other near misses; a same-line marker separated by spaces or tabs
      passes.
- [ ] Push refused when every phase is cancelled, with the "certifies no work"
      message.
- [ ] Commit-count check satisfied by completed phases only: a branch with one
      completed phase, six cancelled phases, and one commit passes.
- [ ] Findings report bound to the last completed phase: a report for the last
      completed phase satisfies the gate even though the last listed phase is
      cancelled.
- [ ] Commit refused with the distinct stale-pointer message when
      `current_phase` names a cancelled phase.
- [ ] Closeout advance skips a cancelled next phase and lands on the following
      non-cancelled phase.
- [ ] Closeout advance past a cancelled tail clears `current_phase` and sets
      `status: complete`, and leaves an already-`cancelled` big plan alone.
- [ ] Branch creation denied for a `cancelled` big plan, with the new message.
- [ ] Regression: a branch with no cancelled phases behaves exactly as today.
      Assert an existing all-complete scenario still passes unchanged.

In `tests/test_hook_gates.py`:

- [ ] `assert_cancellation_evidence` accepts a fully-formed cancelled plan.
- [ ] `assert_cancellation_evidence` produces a distinct failure for each
      missing field, a missing evidence file, and a marker-less evidence file.
- [ ] Direct helper coverage rejects malformed/impossible timestamps; invalid
      reason scalar shapes; absolute, traversal, outside-symlink, loop,
      directory, unreadable, and invalid-UTF-8 evidence; and split-line or
      vertical-whitespace markers. It also accepts ordinary reason prose that
      merely begins like a block header and a tab-separated same-line marker.
- [ ] A missing `python3`, a standard-library probe exception, and malformed
      probe output each fail closed with the phase name in the message.

## Verification

```bash
uv sync
uv run pytest tests/test_hook_gates.py tests/test_validate_targets.py -q --tb=short
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/quality_score.py scripts/ --phase 2026-08-09_phase-D-cancelled-phase-gates --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

Generator determinism, after all edits settle:

```bash
uv run python scripts/generate_targets.py --all
cp -a dist /tmp/dist-gen-a
uv run python scripts/generate_targets.py --all
diff -r /tmp/dist-gen-a dist
rm -rf /tmp/dist-gen-a
```

## Risks

- Two layers now read the same cancellation contract: the Python validator from
  Phase C and this shell gate. Silent drift or relying on a stale earlier
  validation would let a plan mutate into a push-time bypass. Mitigation: the
  shell helper repeats the full semantic contract at action time through one
  fail-closed Python-standard-library probe, with parity cases asserted in both
  suites and the helper as the single shell-side home.
- These gates run on macOS CI where `/bin/bash` is 3.2. No `mapfile`, no
  `readarray`, no negative array indices, matching the existing comments in
  `_lib-frontmatter.sh`.
- Changing `record-commit-closeout.sh` risks stalling the phase machine.
  Mitigation: the existing warn-on-miss `additional_context` paths stay, and
  three explicit tests cover skip, clear-and-complete, and
  do-not-overwrite-cancelled.
- Relaxing a push gate is the highest-risk edit in this plan. Every relaxation is
  paired with a new requirement: cancelled phases must carry evidence, and at
  least one phase must be complete.
- The per-phase evidence contract is the only anti-abuse mechanism here, so it
  carries the full weight. A branch-level acknowledgement flag was considered
  and rejected; if review finds the evidence contract too weak, strengthen the
  evidence contract rather than adding a second flag beside it.

## Acceptance Criteria

- [ ] A branch with completed and fully-evidenced cancelled phases passes the
      push gate without any falsified record.
- [ ] A cancelled phase missing any part of its evidence contract blocks push
      with a distinct message.
- [ ] The push-time helper rejects every timestamp, reason, path, file, decode,
      and marker shape rejected by the committed Phase C validator, including
      absolute/traversal/outside-symlink evidence and YAML-like reasons.
- [ ] A branch whose phases are all cancelled is refused.
- [ ] Commit count is measured against completed phases only.
- [ ] The final findings report binds to the last completed phase.
- [ ] A commit whose `current_phase` is cancelled is refused with a distinct,
      actionable message.
- [ ] Closeout advance skips cancelled phases and never overwrites a recorded
      big-plan cancellation.
- [ ] A `cancelled` big plan cannot start an implementation branch.
- [ ] Branches with no cancelled phases behave identically to today.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
