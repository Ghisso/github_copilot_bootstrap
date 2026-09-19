---
name: 2026-09-19_phase-B-knowledge-model-and-lifecycle-integration
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 2
status: planned
closeout_session_log:
---
# Small Plan: 2026-09-19_phase-B-knowledge-model-and-lifecycle-integration

## Scope

Integrate OpenWiki into the bootstrap's knowledge and planning model after Phase A has established
a safe execution boundary. This phase defines what OpenWiki owns, what remains human-authored,
what belongs in MEMORY, and when a future big plan must refresh generated knowledge.

The central rule is: **OpenWiki is derived context, not authority.** Source/tests and canonical
human-authored policy remain authoritative. OpenWiki-enabled multi-phase plans gain a final
knowledge-refresh phase; disabled repositories keep the current lifecycle unchanged.

## Steps

### Step B1 — Define the canonical knowledge-ownership contract

- [ ] **Owner:** `coder`
- **Target files:**
  - modify `shared/policies/workflow.instructions.md`
  - modify `shared/policies/workspace.instructions.md`
  - modify `shared/MEMORY.md`
  - modify `docs/architecture.md`
  - modify `README.md` only where the source/installed ownership overview needs the new layer
- **Required Skills:**
  - `shared/skills/create-feature/SKILL.md`
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
  - `shared/skills/documentation/SKILL.md`
  - `shared/skills/humanize/SKILL.md` for human-facing prose
- **Contract to encode:**
  - source and tests are authoritative for current behavior;
  - shared policies, security requirements, ADRs, operator runbooks, and explicit project
    decisions remain human-authored authority;
  - `openwiki/INSTRUCTIONS.md` is a human-authored repository brief and the deterministic
    OpenWiki enablement marker;
  - generated files under `openwiki/**` are derived descriptive knowledge and must not be
    hand-edited;
  - `.claude/MEMORY.md` stores stable project-specific learning that cannot be reliably
    re-derived from current repository evidence: rationale, operational caveats, confirmed
    environmental behavior, and similar durable lessons;
  - source-derived architecture/module/API/test facts should not be duplicated into MEMORY
    merely to help future agents;
  - plans, explorations, session logs, findings, and receipts remain historical/lifecycle
    evidence and are never replaced by OpenWiki.
- **Acceptance criteria:**
  - there is one consistent ownership table/rule set, not several conflicting definitions;
  - existing state-sync/ai-state semantics remain intact;
  - no text claims OpenWiki replaces MEMORY or every `docs/` file.
- **Verification:**
  - focused policy/content tests if the repository has them;
  - generated-target checks;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step B2 — Add a narrow OpenWiki skill

- [ ] **Owner:** `coder`
- **Target files:**
  - create `shared/skills/openwiki/SKILL.md`
  - modify skill validation/routing tests if required
- **Required Skills:**
  - `shared/skills/create-feature/SKILL.md`
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Skill contract:**
  - make the trigger narrow: initialize/refresh/review the repository OpenWiki knowledge layer;
  - use `.claude/scripts/openwiki_refresh.py`, not raw upstream `openwiki --init`;
  - explain opt-in via `openwiki/INSTRUCTIONS.md`;
  - require serial execution;
  - state that source/tests/policies outrank generated wiki;
  - never instruct agents to edit generated pages or `.claims` sidecars manually;
  - never install host-specific OpenWiki integrations as part of ordinary execution;
  - never create a scheduled workflow;
  - when generation fails, preserve resumable state and return the failure to the orchestrator;
  - keep provider/auth setup user-local and outside repository state.
- **Acceptance criteria:**
  - the skill is usable from every generated target;
  - description is specific enough to avoid unrelated automatic loading.
- **Verification:**
  - skill validator and target-generation tests;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step B3 — Teach planning to append the final knowledge-refresh phase

- [ ] **Owner:** `coder`
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
    the last small plan a dedicated knowledge-refresh phase.
  - The knowledge-refresh phase begins only after preceding implementation phases have completed
    and been committed.
  - It runs the bootstrap OpenWiki runner, reviews the generated diff, performs the standing
    human stale-claims/MEMORY/LEARN audit, and closes normally.
  - Do not add the phase for:
    - repos without the enablement marker;
    - read-only/reporting tasks;
    - AI-state-only work that does not change outer-repository knowledge;
    - a plan whose only purpose is already a knowledge/OpenWiki refresh.
  - Do not call OpenWiki from `verify.py`, hooks, or post-commit as a substitute.
- **Acceptance criteria:**
  - example/fixture plans show enabled and disabled behavior;
  - no recursion produces repeated knowledge-refresh phases;
  - the existing exact final-phase stale-claims heading requirement remains active.
- **Verification:**
  - focused plan/frontmatter tests;
  - target generation;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step B4 — Integrate the lifecycle without turning OpenWiki into a gate script

- [ ] **Owner:** `coder`
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
  - Provider/auth failure must be reported with the runner's actionable error and retried after
    the user/environment fixes auth; do not silently skip an enabled plan's required refresh.
  - Normal repos without `openwiki/INSTRUCTIONS.md` keep the current workflow.
  - Keep one commit per completed small plan and the current push semantics.
- **Acceptance criteria:**
  - no OpenWiki call exists in deterministic verifier code;
  - no OpenWiki call exists in hooks/state-sync/post-commit;
  - phase retry semantics are ordinary lifecycle semantics.
- **Verification:**
  - focused lifecycle tests/content assertions;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step B5 — Narrow documenter, learning, and onboarding responsibilities

- [ ] **Owner:** `coder`
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
  - current source-derived fact -> do not add redundant MEMORY entry; rely on source/OpenWiki;
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

### Step B6 — Add provider-neutral root guidance

- [ ] **Owner:** `coder`
- **Target files:**
  - modify authoring `AGENTS.md`
  - modify authoring `CLAUDE.md`
  - modify the canonical generated-root source/propagation path only if inspection shows one is
    required beyond these authoring files
  - regenerate targets
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
  - `shared/skills/documentation/SKILL.md`
  - `shared/skills/humanize/SKILL.md`
- **Guidance:**
  - if `openwiki/` exists, use it as optional just-in-time repository context;
  - do not treat generated wiki as authority over source/tests/policies;
  - do not hand-edit generated wiki pages;
  - invoke the bootstrap-owned OpenWiki skill/runner for refresh;
  - keep root guidance concise and cross-target.
- **Acceptance criteria:**
  - tracked bootstrap authoring root files remain byte-stable across self-refresh;
  - consumer-generated root adapters carry equivalent guidance through the canonical generator;
  - OpenWiki's own managed snippet is not committed as a competing root owner.
- **Verification:**
  - regenerate and validate targets;
  - root-preservation/self-refresh tests;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step B7 — High-risk + documentation review and closeout

- [ ] **Owner:** `reviewer`
- **Target files:** scoped Phase B diff
- **Required Skills:** none beyond reviewer-owned profile guidance
- **Review Profiles:**
  - `code`
  - `architecture`
  - `security`
  - `tests`
  - `ponytail`
  - `documentation`
- **Review focus:**
  - no circular authority between source, docs, wiki, and memory;
  - final-phase rule is deterministic and does not affect disabled repos;
  - root/control-plane ownership remains singular;
  - generated docs are not presented as normative;
  - plan complexity has not expanded beyond what is needed;
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

Use focused tests for planner/lifecycle/skill behavior while editing. Normal completion then follows
the canonical closeout order and requires `verify phase` then `verify closeout` PASS receipts.

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`.

- [ ] Documentation updated
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
- [ ] Knowledge-ownership wording is consistent across policy, skills, agents, and root guidance
- [ ] Disabled repositories retain the existing planning and closeout behavior
- [ ] No model-backed OpenWiki execution was added to deterministic verification or hooks

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
