---
name: 2026-09-19_phase-B-openwiki-knowledge-ownership-and-agent-access
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 2
status: complete
closeout_session_log: .claude/session_logs/2026-09-19_openwiki-phase-B-knowledge-ownership.md
---
# Small Plan: 2026-09-19_phase-B-openwiki-knowledge-ownership-and-agent-access

## Scope

Define what OpenWiki owns, what remains human-authored, what belongs in MEMORY, and how every
agent target finds and refreshes the wiki. This phase encodes the ownership contract in canonical
policy, adds one narrow OpenWiki skill that wraps the Phase A runner, and adds provider-neutral
root guidance. It does not change planner, orchestrator, documenter, learn, or onboard behavior;
Phase C does that on top of this contract.

The central rule is: **OpenWiki is derived context, not authority.** Source/tests and canonical
human-authored policy remain authoritative.

## Steps

### Step B1 — Define the canonical knowledge-ownership contract

- [x] **Owner:** `coder`
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
    evidence and are never replaced by OpenWiki;
  - OpenWiki refresh is a serial, explicit, model-backed lifecycle action, never a hook,
    verifier, installer, state-sync, or scheduled-CI action.
- **Acceptance criteria:**
  - there is one consistent ownership table/rule set, not several conflicting definitions;
  - existing state-sync/ai-state semantics remain intact;
  - no text claims OpenWiki replaces MEMORY or every `docs/` file.
- **Verification:**
  - focused policy/content tests if the repository has them;
  - generated-target checks;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step B2 — Add a narrow OpenWiki skill

- [x] **Owner:** `coder`
- **Target files:**
  - create `shared/skills/openwiki/SKILL.md`
  - modify skill validation/routing tests if required
- **Required Skills:**
  - `shared/skills/create-feature/SKILL.md`
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Skill contract:**
  - narrow trigger: initialize, refresh, rebaseline, or review the repository OpenWiki
    knowledge layer;
  - use `.claude/scripts/openwiki_refresh.py`, never raw `openwiki --init`;
  - explain opt-in via `openwiki/INSTRUCTIONS.md`;
  - require serial execution;
  - state that source/tests/policies outrank generated wiki;
  - never instruct agents to edit generated pages or `.claims` sidecars manually;
  - never install host-specific OpenWiki integrations as part of ordinary execution;
  - never create a scheduled workflow;
  - when generation fails, preserve resumable state (`openwiki/.run.json` is gitignored and
    stays on disk) and return the failure to the orchestrator;
  - keep provider/auth setup user-local (`~/.openwiki`, relocatable with
    `OPENWIKI_CONFIG_DIR`) and outside repository state; telemetry is off by default through
    the runner and a user may opt in by setting `OPENWIKI_TELEMETRY_DISABLED` themselves;
  - **merge-history and rebaseline rule:** incremental detection depends on the base HEAD
    recorded in `openwiki/.last-update.json` staying reachable. If a squash merge or history
    rewrite makes it unreachable, treat OpenWiki's fallback as degraded incremental
    assistance. Do not use `--init`. When a clean baseline is required: preserve
    `openwiki/INSTRUCTIONS.md`, remove the rest of `openwiki/**`, and run the standard
    runner again, which performs a first generation.
- **Acceptance criteria:**
  - the skill is usable from every generated target;
  - description is specific enough to avoid unrelated automatic loading;
  - the skill passes the existing skill-library validator.
- **Verification:**
  - skill validator and target-generation tests;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step B3 — Add provider-neutral root guidance

- [x] **Owner:** `coder`
- **Target files:**
  - modify authoring `AGENTS.md`
  - modify authoring `CLAUDE.md`
  - modify the canonical generated-root source/propagation path in `scripts/generate_targets.py`
    only if inspection shows one is required beyond these authoring files
  - regenerate targets
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
  - `shared/skills/documentation/SKILL.md`
  - `shared/skills/humanize/SKILL.md`
- **Guidance (concise, cross-target):**
  - if `openwiki/` exists, use it as optional just-in-time repository context;
  - do not treat generated wiki as authority over source/tests/policies;
  - do not hand-edit generated wiki pages;
  - invoke the bootstrap-owned OpenWiki skill/runner for refresh;
  - OpenWiki's own managed root snippet is never committed as a competing root owner.
- **Acceptance criteria:**
  - tracked bootstrap authoring root files remain byte-stable across self-refresh;
  - consumer-generated root adapters carry equivalent guidance through the canonical generator;
  - root guidance stays short; details live in the skill and policy.
- **Verification:**
  - regenerate and validate targets;
  - root-preservation/self-refresh tests;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step B4 — High-risk + documentation review and closeout

- [x] **Owner:** `reviewer`
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
  - root/control-plane ownership remains singular;
  - generated docs are not presented as normative;
  - the rebaseline rule never reintroduces `--init`;
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

Use focused tests for skill and root-guidance behavior while editing. Normal completion then
follows the canonical closeout order and requires `verify phase` then `verify closeout` PASS
receipts.

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`.

- [x] Documentation updated — `README.md`, `docs/architecture.md`, both root adapters, and the new skill
- [x] LEARN entries saved or no-lessons marker recorded — three entries
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason — none survived; the `verify.py` message MINOR is pre-existing and out of this diff's scope, recorded as a follow-up
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` then `verify closeout` PASS)
- [x] Knowledge-ownership wording is consistent across policy, skill, and root guidance — one MAJOR drift found and fixed, then confirmed
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
