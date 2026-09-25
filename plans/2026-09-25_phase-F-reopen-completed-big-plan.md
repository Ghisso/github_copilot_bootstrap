---
name: 2026-09-25_phase-F-reopen-completed-big-plan
type: small-plan
parent_plan: consumer-sidecar-bootstrap-overlay
phase_index: 6
status: in-progress
---

# Small Plan: Phase F — Reopen After a Completed Knowledge Refresh

## Scope

This big plan was complete, and its last phase (E) is a completed
knowledge-refresh phase. The plan validator requires a knowledge-refresh
phase to be unique and last, so the plan cannot take new phases today. This
phase changes the validator so a knowledge-refresh phase that is not last,
and whose small plan is already `complete` or `cancelled`, no longer counts
toward that rule. A plan that has knowledge-refresh phases must still end with one (big
plan, Decision 21). It also writes the procedure for reopening a completed
big plan into the canonical workflow instructions, so the next reopen needs
no investigation.

This is control-plane work: the validator and the workflow instructions ship
to every consumer. It must be the first outer commit on this branch, because
until the installed validator carries the change, it rejects this big plan
and so blocks every outer commit.

Evidence: the workflow finding in
`.claude/quality_reports/2026-09-25_consumer-sidecar-bootstrap-overlay-review-2.md`.
A scratch clone tested the exact rule below: the 626 existing tests in
`tests/test_validate_plan_frontmatter.py` and `tests/test_check_runtime.py`
passed. After F's commit, the post-commit hook advanced to the next phase.
The receipt history walk from the new final phase back through E to A had
no errors.

### Required Skills

- `shared/skills/ponytail/SKILL.md` — `full`
- `shared/skills/code-style/SKILL.md`
- `shared/skills/testing-patterns/SKILL.md`
- `shared/skills/documentation/SKILL.md`

## Primary Files

- `scripts/validate_plan_frontmatter.py` — `validate_knowledge_refresh_phase_position`
  and the comment above `KNOWLEDGE_REFRESH_PHASE_SUFFIX`.
- `tests/test_validate_plan_frontmatter.py` — new cases next to the existing
  knowledge-refresh tests (around lines 560-650).
- `shared/policies/workflow.instructions.md` — the Termination paragraph of
  "Knowledge-Refresh Final Phase", and a new "Reopening a completed big plan"
  subsection under "Branch Lifecycle".
- Generated and installed copies, never hand-copied:
  `dist/multi-agent/.claude/scripts/validate_plan_frontmatter.py`,
  `.claude/scripts/validate_plan_frontmatter.py`, and
  `.claude/instructions/workflow.instructions.md`.

## Steps

- [ ] **1. Change the validator rule.**
  - **Owner:** `coder`
  - Keep the signature
    `validate_knowledge_refresh_phase_position(path: Path, phases: list[str], errors: list[str]) -> None`.
  - A knowledge-refresh phase (slug ends in `-knowledge-refresh`) is
    *settled* when it is not the last entry of `phases` and its small plan,
    `path.parent / f"{phase}.md"`, parses with `status: complete` or
    `status: cancelled`. Check the phase name against the existing slug
    pattern (`[A-Za-z0-9][A-Za-z0-9._-]*`) before building that path, so the
    rule never reads a file outside the plans folder. Use the module's
    existing frontmatter parser; add no new parsing code.
  - Standard library only, and keep Python 3.9-compatible runtime syntax:
    the commit gate runs this script with each consumer's system `python3`
    (Bootstrap Hooks Runtime Contract in
    `shared/policies/workspace.instructions.md`).
  - Count only unsettled knowledge-refresh phases. More than one gives the
    existing "at most one knowledge-refresh phase is allowed" error. One that
    is not last gives the existing "must be the last phase in phases" error.
  - When knowledge-refresh phases exist, all are settled, and the last entry
    is not a knowledge-refresh phase, give the "must be the last phase in
    phases" error. This keeps "append a phase after a completed refresh"
    rejected.
  - A missing, unreadable, or not-`complete` small plan makes its phase
    unsettled. Fail closed.
  - Must not: change any other validation, read any file other than the
    sibling small plans' frontmatter, or change the result for a plan with
    zero knowledge-refresh phases or with one that is last.
  - Update the comment above `KNOWLEDGE_REFRESH_PHASE_SUFFIX` to describe the
    exemption in one sentence.

- [ ] **2. Test the rule.**
  - **Owner:** `coder`
  - Build real big-plan and small-plan files under `tmp_path`, like the
    existing knowledge-refresh tests.
  - Accept: a completed refresh phase in the middle and a `planned` refresh
    phase last (the reopened shape).
  - Reject with "must be the last phase": a completed refresh phase in the
    middle and a non-refresh phase last (appending after a completed refresh).
  - Reject with "at most one": a mid-list refresh phase whose small plan is
    `in-progress`, `planned`, missing, or unreadable, plus a refresh phase
    last. Parametrize these four.
  - Reject: two unsettled refresh phases with neither of them last.
  - Accept: a `cancelled` refresh phase in the middle and a refresh phase
    last.
  - A phase name that fails the slug pattern is unsettled, and no file
    outside `tmp_path` is read.
  - Every existing test in the file passes unchanged, including the exact
    error message substrings.

- [ ] **3. Write the workflow text.**
  - **Owner:** `coder`
  - In `shared/policies/workflow.instructions.md`, amend the Termination
    paragraph of "Knowledge-Refresh Final Phase": when a completed big plan
    is reopened, its completed knowledge-refresh phase stays where it is, and
    the rule appends one new knowledge-refresh phase after the new phases.
    Name the validator's exemption (only completed or cancelled, non-final
    refresh phases).
  - Add `### Reopening a completed big plan` under "Branch Lifecycle", after
    "Cancelling a plan or phase", as a numbered procedure (a repeated
    procedure belongs in the canonical instructions, not in memory):
    1. Reopen only while the implementation branch exists and is not merged.
       After a merge, start a new big plan instead.
    2. Inspect the completed phases' outcomes and review findings. Record new
       findings in a quality report.
    3. Draft the new small plans as `planned`, with the next phase letters
       and `phase_index` values. Only a knowledge-refresh phase's slug may
       end in `-knowledge-refresh`; the validator counts any slug with that
       suffix (a first draft of this phase's own slug did).
    4. If any listed phase is a knowledge-refresh phase, append one new
       `-knowledge-refresh` phase after the new phases. The validator
       requires a plan with knowledge-refresh phases to end with one.
    5. Edit the big plan: `status: in-progress`, `current_phase:` the first
       new phase, and the new phases appended to `phases:` and to the body
       `## Phases` list in the same order. Update Done Criteria and
       Completion Evidence to name the new final phase. Keep `started_at`
       and the branch fields.
    6. Never edit a completed phase's small plan, closeout session log,
       findings report, or receipts (see Immutability under "Session
       Logging"). Never re-persist a completed phase's receipts, even when
       `verify.py` suggests it while the big plan is still `complete`.
    7. Set the first new phase to `in-progress` when its implementation
       starts. No hook does this on an existing branch.
    8. Checkpoint the nested `.claude` repository.
    9. The new final phase meets the same strict terminal gates. Reopening
       defers them; it never escapes them.
  - Keep the subsection short and link to existing sections instead of
    restating them.
  - Search `shared/skills/plan-decomposition/SKILL.md`,
    `shared/templates/plan-big.md`, `shared/agents/planner/`, and
    `shared/agents/orchestrator/` for text that restates "unique and last" or
    implies a completed plan cannot be reopened. Change such text only if it
    restates the rule; today these files link to the canonical rule.

- [ ] **4. Regenerate and install.**
  - **Owner:** `coder`
  - Run `uv run python scripts/generate_targets.py --all`, then
    `uv run python scripts/install_bootstrap.py . --allow-self --local-only`.
    Never copy generated files by hand.
  - Then `uv run python scripts/validate_plan_frontmatter.py` must pass on
    every real plan, including this reopened big plan.

- [ ] **5. Record the lesson.**
  - **Owner:** `orchestrator`
  - In closeout LEARN, update the existing MEMORY entry "Adding a phase to a
    big plan defers the strict terminal check" only if it now points to the
    wrong place. The procedure itself lives in the workflow instructions.

## Acceptance Criteria

- Every real plan in `.claude/plans/` validates, including this reopened big
  plan with two knowledge-refresh phases (E complete, I last).
- Appending a phase after a completed knowledge-refresh phase, with no new
  refresh phase last, is still rejected.
- The existing validator and runtime-check tests pass unchanged.
- The workflow instructions carry a numbered reopening procedure, and the
  Termination text matches the validator.
- The generated and installed copies match their sources.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_validate_plan_frontmatter.py tests/test_check_runtime.py -q --tb=short
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json
```

Run the self-install (`install_bootstrap.py . --allow-self --local-only`)
before `verify closeout`, because this block regenerates targets.

## Optional Verification

- The operator starts a new session and checks that the session-start summary reports this big plan with `phases done=5 pending=4` and `current_phase=2026-09-25_phase-F-reopen-completed-big-plan` before this phase's commit.

## Review Profiles

- `code`
- `architecture`
- `security`
- `tests`
- `ponytail`
- `documentation`

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT).

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
