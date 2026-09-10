---
name: 2026-09-10_phase-C-plan-and-delegation-semantics
type: small-plan
parent_plan: consumer-lifecycle-friction-hardening
phase_index: 3
status: in-progress
closeout_session_log:
---

# Small Plan: Phase C — Plan and Delegation Semantics

## Scope

Make plan files describe lifecycle state honestly and accept readable phase
annotations without weakening frontmatter parity. Add a backward-compatible
`planned` status for future phases and activate it only when the branch or
previous completion selects that phase. Tighten agent handoffs so incremental
requirements, reviewer diff evidence, and callable-tool boundaries survive
delegation.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` in `full` mode
- `.claude/skills/code-style/SKILL.md`
- `.claude/skills/testing-patterns/SKILL.md`
- `.claude/skills/documentation/SKILL.md`

## Review Profiles

- `code`
- `architecture`
- `security`
- `tests`
- `ponytail`
- `documentation`

## Steps

1. **Accept safely bounded phase annotations.**
   Owner: `coder`.
   Update `BODY_PHASE_ITEM_PATTERN` in
   `scripts/validate_plan_frontmatter.py` to accept non-empty trailing prose,
   including parenthetical notes, only after a whitespace boundary following
   the closing backtick. Preserve exact slug extraction, safe-slug validation,
   duplicate detection, checkbox handling, body/frontmatter order equality,
   and rejection of malformed or unclosed backticks. Add positive cases for
   parentheses and existing delimiter forms plus negatives that could hide an
   extra or different slug. Update `shared/templates/plan-big.md` to document
   the allowed form.

2. **Add the `planned` small-plan status without breaking installed plans.**
   Owner: `coder`.
   Add `planned` to `SMALL_PLAN_STATUSES`, change
   `shared/templates/plan-small.md` to use it by default, and update
   `shared/plans/README.md`, workflow guidance, context-status guidance, and
   generator assertions. A planned plan requires the ordinary identity fields
   but no pause, cancellation, or closeout evidence. Push/PR and completion
   gates continue to treat it as unfinished. Existing future phases marked
   `in-progress` remain valid for compatibility.

3. **Activate planned phases at the two existing transition boundaries.**
   Owner: `coder`.
   Modify `shared/hooks/scripts/record-branch-state.sh` to change only the first
   selected phase from `planned` to `in-progress`. Extend the Phase A
   `record-commit-closeout.sh` transition so the next non-cancelled phase is
   changed from `planned` to `in-progress` when it becomes `current_phase`.
   Preserve an already-`in-progress` next phase for compatibility. Do not
   overwrite `paused`, `complete`, invalid, duplicate-status, missing, or
   unreadable next-phase state; emit an actionable warning and leave the plan
   machine unadvanced instead. Add branch, intermediate, final, cancelled-tail,
   repeat-invocation, and legacy tests.

4. **Make context status distinguish planned from active.**
   Owner: `coder`.
   Update `shared/skills/context-status/SKILL.md` and any generated assertions
   so `planned` phases are reported as pending and never selected as the active
   phase. `in-progress` and `paused` remain the only preferred active small-plan
   states. Add a fixture with multiple planned phases and one current phase.

5. **Protect incremental intent in delegation briefs.**
   Owner: `documenter` after code review converges.
   Update `shared/agents/orchestrator/prompt.md` and
   `shared/agents/coder/prompt.md`. When a plan or user asks for incremental or
   delta work, the evidence packet must identify existing builders and scoped
   entry points to inspect. A full rebuild is a material deviation: the coder
   must report it before implementation with evidence that no scoped path can
   satisfy the requirement, and the orchestrator must obtain approval rather
   than granting a generic rebuild allowance. Preserve the general minimal-diff
   and search-before-writing rules instead of duplicating them.

6. **Give reviewers diff scope without generic shell access.**
   Owner: `documenter` after code review converges.
   Keep `shared/agents/reviewer/agent.yaml` at `read` and `search`. Update the
   orchestrator evidence-packet rule and reviewer input contract so a reviewer
   without execute capability receives the changed paths and either the scoped
   diff, a repository artifact containing it, or exact changed hunks. Do not
   claim that full-file reads alone are equivalent to diff review. Add
   generator assertions that reviewer execute access is still absent and the
   diff-evidence requirement is present.

7. **Clarify unavailable inherited tool names.**
   Owner: `documenter` after code review converges.
   Add one concise statement to shared agent retrieval guidance: agents use only
   tools actually callable in their runtime; inherited text naming filtered or
   unavailable context-mode operations does not expose them. Continue to route
   through the authoritative tool policy, which permits only `ctx_index`,
   `ctx_search`, `ctx_stats`, and `ctx_doctor`. Do not attempt to strip or
   rewrite host-owned system/developer prompts. Test generated prompts for the
   statement and absence of recommendations for filtered operations.

## Acceptance Criteria

- [ ] Parenthetical and documented delimiter annotations validate while the extracted slug list must still exactly match frontmatter.
- [ ] New future small plans default to `planned`; legacy future `in-progress` plans remain valid.
- [ ] Branch creation and completed-phase advancement activate only the selected planned phase.
- [ ] Unexpected next-phase states are preserved and reported rather than overwritten.
- [ ] Context status reports planned phases as pending, not active.
- [ ] Incremental briefs cannot silently authorize a full rebuild.
- [ ] Reviewers receive diff-scoped evidence while retaining read/search-only capabilities.
- [ ] Generated prompts use only the guarded context-mode surface and do not claim control over host-owned context.

## Verification

```bash
uv run pytest tests/test_validate_plan_frontmatter.py tests/test_hook_gates.py tests/test_validate_targets.py tests/test_check_native_clients.py -q
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run ruff check scripts/validate_plan_frontmatter.py tests shared/agents shared/skills
uv run mypy scripts/validate_plan_frontmatter.py tests --ignore-missing-imports --explicit-package-bases
uv run python .claude/scripts/verify.py phase --format json --persist
```

## Closeout Checklist

- [ ] Verification passed (`verify phase` PASS)
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record `paused_at`, `paused_reason`, and
`pause_session_log`, and keep the big plan `in-progress` with this same
`current_phase`. Resume this file rather than creating a replacement phase.

