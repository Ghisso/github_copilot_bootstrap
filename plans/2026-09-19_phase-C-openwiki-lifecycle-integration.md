---
name: 2026-09-19_phase-C-openwiki-lifecycle-integration
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 3
status: complete
closeout_session_log: .claude/session_logs/2026-09-19_openwiki-phase-C-lifecycle-integration.md
---
# Small Plan: 2026-09-19_phase-C-openwiki-lifecycle-integration

## Scope

Teach the lifecycle how OpenWiki-enabled big plans end. Building on the Phase B ownership
contract and skill, this phase updates the planner, plan-decomposition skill, big-plan template,
orchestrator, documenter, learn, and onboard behavior so that a multi-phase big plan in an
enabled repository gets a small final knowledge-refresh phase, and so that documentation and
memory work stops duplicating facts OpenWiki can regenerate. Disabled repositories keep the
current lifecycle unchanged.

The normal shape of that final phase is small: refresh OpenWiki through the runner, inspect the
generated delta, run the standing stale-claims/MEMORY/LEARN audit, then review, verify, and
commit.

## Steps

### Step C1 — Teach planning to append the final knowledge-refresh phase

- [x] **Owner:** `coder`
- **Target files:**
  - modify `shared/agents/planner/prompt.md`
  - modify `shared/skills/plan-decomposition/SKILL.md`
  - modify `shared/templates/plan-big.md`
  - modify `shared/templates/plan-small.md` only if a small template hint is needed
  - modify relevant planner/plan-validation tests
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Planning rule:**
  - For a **multi-phase big plan** in a repository where `openwiki/INSTRUCTIONS.md` exists,
    and where the plan changes documentable outer-repository behavior, the planner must make
    the last small plan a dedicated knowledge-refresh phase with the small shape above.
  - The knowledge-refresh phase begins only after preceding implementation phases have completed
    and been committed.
  - The phase runs the bootstrap OpenWiki runner through the OpenWiki skill, reviews the
    generated diff, performs the standing stale-claims/MEMORY/LEARN audit, and closes normally.
  - If the recorded OpenWiki base HEAD is unreachable, the phase follows the skill's rebaseline
    rule; it never uses `--init`.
  - Do not add the phase for:
    - repos without the enablement marker;
    - read-only/reporting tasks;
    - AI-state-only work that does not change outer-repository knowledge;
    - a plan whose only purpose is already a knowledge/OpenWiki refresh.
  - Do not call OpenWiki from `verify.py`, hooks, or post-commit as a substitute.
- **Acceptance criteria:**
  - example/fixture plans show enabled and disabled behavior;
  - no recursion produces repeated knowledge-refresh phases;
  - the existing exact final-phase `## Stale-claims surfaces checked` requirement remains
    active and is what the knowledge-refresh phase satisfies.
- **Verification:**
  - focused plan/frontmatter tests;
  - target generation;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step C2 — Integrate the lifecycle without turning OpenWiki into a gate script

- [x] **Owner:** `coder`
- **Target files:**
  - modify `shared/agents/orchestrator/prompt.md`
  - modify `shared/policies/workflow.instructions.md`
  - modify lifecycle/verification tests as needed
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Behavior:**
  - The orchestrator recognizes a knowledge-refresh small plan as an explicit implementation
    phase, not as a hidden closeout hook.
  - In that phase it invokes the OpenWiki skill/runner during IMPLEMENT, reviews its diff, and
    then follows normal VERIFY -> REVIEW -> CLOSEOUT.
  - OpenWiki failure blocks completion of that phase but does not fabricate a deterministic
    verification failure.
  - Provider/auth failure is reported with the runner's actionable error and retried after
    the user/environment fixes auth; an enabled plan's required refresh is never silently
    skipped.
  - Normal repos without `openwiki/INSTRUCTIONS.md` keep the current workflow.
  - Keep one commit per completed small plan and the current push semantics.
  - `openwiki/.run.json` is never staged; it is gitignored by Phase A and the closeout
    staging step must not force-add it.
- **Acceptance criteria:**
  - no OpenWiki call exists in deterministic verifier code;
  - no OpenWiki call exists in hooks/state-sync/post-commit;
  - phase retry semantics are ordinary lifecycle semantics.
- **Verification:**
  - focused lifecycle tests/content assertions;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step C3 — Narrow documenter, learning, and onboarding responsibilities

- [x] **Owner:** `coder`
- **Target files:**
  - modify `shared/agents/documenter/prompt.md`
  - modify `shared/skills/documentation/SKILL.md`
  - modify `shared/skills/learn/SKILL.md`
  - modify `shared/skills/onboard/SKILL.md`
  - modify focused skill/agent tests
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
  - `shared/skills/documentation/SKILL.md`
  - `shared/skills/humanize/SKILL.md`
- **Documenter behavior:**
  - classify documentation as human-authored normative/user-facing vs generated descriptive;
  - never hand-edit generated OpenWiki pages/claim sidecars;
  - update README, policies, ADRs, security docs, runbooks, or other manual docs when those
    surfaces actually own the changed requirement;
  - allow descriptive architecture/component detail to live in OpenWiki in enabled repos when
    no human/manual contract requires a duplicate page.
- **Learn behavior:**
  - cross-project reusable lesson -> skill;
  - project-specific non-derivable durable lesson -> MEMORY;
  - current source-derived fact -> no redundant MEMORY entry; rely on source/OpenWiki;
  - historical execution fact -> session log/plan, not MEMORY.
- **Onboard behavior:**
  - when an OpenWiki is present, use its entry/index as optional just-in-time orientation rather
    than reading all generated pages at startup;
  - verify material implementation claims against source/tests before editing;
  - disabled repos keep current targeted-retrieval behavior.
- **Acceptance criteria:**
  - existing humanize requirements remain intact;
  - no rule makes OpenWiki mandatory startup reading.
- **Verification:**
  - focused content/routing tests;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step C4 — High-risk + documentation review and closeout

- [x] **Owner:** `reviewer`
- **Target files:** scoped Phase C diff
- **Required Skills:** none beyond reviewer-owned profile guidance
- **Review Profiles:**
  - `code`
  - `architecture`
  - `security`
  - `tests`
  - `ponytail`
  - `documentation`
- **Review focus:**
  - final-phase rule is deterministic and does not affect disabled repos;
  - the knowledge-refresh phase shape is small and does not reintroduce Phase D's transition
    scope as the template;
  - plan complexity has not expanded beyond what is needed;
  - no OpenWiki call leaked into verifier, hooks, or post-commit;
  - user-facing prose is clear and non-promotional.
- **Acceptance criteria:**
  - CRITICAL/MAJOR findings resolved;
  - surviving MINOR findings have explicit disposition/reason;
  - canonical phase and closeout receipts pass.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json
```

Use focused tests for planner/lifecycle/skill behavior while editing. Normal completion then
follows the canonical closeout order and requires `verify phase` then `verify closeout` PASS
receipts.

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`.

- [x] Documentation updated — `docs/runtime-checks.md` gained a row for the new plan gate
- [x] LEARN entries saved or no-lessons marker recorded — three entries
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason — none survived; both findings were fixed
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` then `verify closeout` PASS)
- [x] Disabled repositories retain the existing planning and closeout behavior — scoped to C1 and C2; C3 applies everywhere by design, recorded in the session log
- [x] Knowledge-refresh phase wording is consistent across planner, orchestrator, templates, and skills — one MAJOR naming gap found and fixed, then confirmed
- [x] No model-backed OpenWiki execution was added to deterministic verification or hooks

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record the required pause fields, and create a session log
with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it
does not require final findings, LEARN, DOCUMENT, or a completed closeout.
After the checkpoint commit, it may be pushed as a durable remote backup when
paused-publication invariants pass. It remains unfinished and blocks PR creation
and final closeout.

Keep the big plan `in-progress` with the same `current_phase`. On resume, read
the pause log and Git state, restore this plan to `in-progress`, and continue
this same phase without creating another small plan.
