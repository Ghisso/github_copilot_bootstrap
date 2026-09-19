---
name: 2026-09-19_phase-D-openwiki-dogfood-migration-and-closeout
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 4
status: in-progress
closeout_session_log:
---
# Small Plan: 2026-09-19_phase-D-openwiki-dogfood-migration-and-closeout

## Scope

Enable the new knowledge layer for `github_copilot_bootstrap` itself and complete the big plan.
All implementation/control-plane work from Phases A, B, and C must already be committed before
this phase starts.

**This is a transition and dogfood phase, not the template for future knowledge-refresh
phases.** It includes one-time work (creating the brief and ignore file, migrating manual
documentation and memory) that a normal final phase does not have. The normal shape, defined in
Phase C, is: refresh OpenWiki, inspect the generated delta, run the stale-claims/MEMORY audit,
then review, verify, and commit. The Phase D closeout session log must state this distinction.

Generate the bootstrap wiki through the safe runner, review its grounded content, then reduce
manual descriptive duplication only where coverage is proven. Keep policy, security, ADRs,
operator instructions, README entry-point material, plans/logs, and non-derivable MEMORY content
under human ownership. Finish by refreshing OpenWiki after the migration and running the required
repository-wide stale-claims audit.

## Steps

### Step D1 — Enable OpenWiki for the bootstrap repository with a bounded brief

- [ ] **Owner:** `coder`
- **Target files:**
  - create `openwiki/INSTRUCTIONS.md`
  - create `.openwikiignore`
- **Required Skills:**
  - `shared/skills/openwiki/SKILL.md`
  - `shared/skills/ponytail/SKILL.md` in `full` mode for any script/config changes
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
  - `shared/skills/documentation/SKILL.md`
  - `shared/skills/humanize/SKILL.md`
- **`openwiki/INSTRUCTIONS.md` scope:**
  - document the bootstrap as a source-of-truth + generated multi-target coding-agent system;
  - prioritize `shared/`, `scripts/`, `tests/`, lifecycle, agents, skills, hooks, target
    generation, consumer ownership, state sync, and deterministic verification;
  - explain the distinction between bootstrap authoring repo, generated `dist/multi-agent/`,
    consumer outer repo, and nested `.claude` ai-state;
  - prefer current implementation evidence and tests;
  - do not treat archived plans/session logs as current behavior.
- **`.openwikiignore` minimum intent:**
  - exclude nested/generated/private AI-state such as `.claude/`, `.codex/`, `.agents/`;
  - exclude generated `dist/`;
  - exclude generated target adapters that would duplicate canonical `shared/` sources;
  - exclude root `AGENTS.md` / `CLAUDE.md` from OpenWiki source discovery so temporary upstream
    managed snippets cannot become claim evidence;
  - exclude secrets, local caches (`.context-mode/`, `.uv-cache/`, `.venv/`), build output,
    and other existing irrelevant paths;
  - keep source/tests/manual normative docs available as evidence.
- **Acceptance criteria:**
  - the ignore file is narrow enough that OpenWiki can still explain the real architecture;
  - it does not hide canonical source needed to verify claims;
  - no credential path is made more visible;
  - `openwiki/.run.json` is already ignored by the Phase A installer block after self-install
    (confirm with `git check-ignore openwiki/.run.json`).
- **Verification:**
  - inspect active ignore rules;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step D2 — Run the first real bootstrap OpenWiki generation

- [ ] **Owner:** `coder`
- **Target files:** generated `openwiki/**` except human-authored `openwiki/INSTRUCTIONS.md`;
  no other outer-repository file is an allowed generated target
- **Required Skills:**
  - `shared/skills/openwiki/SKILL.md`
- **Execution:**
  - confirm the host `~/.openwiki` directory is mounted and writable, with a configured
    provider;
  - run `.claude/scripts/openwiki_refresh.py --require-enabled` through the supported runtime;
  - do not run raw `openwiki --init`;
  - do not create/enable a scheduled workflow;
  - do not run host-specific integration installers.
- **Acceptance criteria:**
  - runner reports success;
  - `AGENTS.md` and `CLAUDE.md` are byte-identical to their pre-run state;
  - `.github/workflows/openwiki-update.yml` is absent (it does not exist in this repository);
  - new OpenWiki changes are confined to `openwiki/**`;
  - generated wiki contains the `openwiki/.claims/` sidecars and `.last-update.json` /
    `.page-manifest.json` metadata expected by `0.5.2`;
  - no secrets or AI-state content appear in the generated output;
  - `git status` does not list `openwiki/.run.json` as trackable.
- **Verification:**
  - inspect `git status` and `git diff`;
  - inspect representative claims against canonical source/tests;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step D3 — Audit generated coverage before removing manual knowledge

- [ ] **Owner:** `documenter`
- **Target files (read/review only):** `openwiki/**`, `README.md`, live `docs/**`,
  `shared/MEMORY.md`, and relevant root/manual policy and ADR surfaces
- **Required Skills:**
  - `shared/skills/documentation/SKILL.md`
  - `shared/skills/humanize/SKILL.md`
  - `shared/skills/deep-audit/SKILL.md`
- **Create an evidence-backed migration disposition for each live manual documentation surface:**
  - **KEEP:** normative, security, ADR, operator/runbook, external human usage, or information
    OpenWiki should not own;
  - **SHORTEN/LINK:** human entry-point material can point to OpenWiki for derived detail while
    retaining the human contract;
  - **REMOVE:** purely descriptive duplicate whose current information is adequately generated
    and grounded by OpenWiki;
  - **KEEP + OPENWIKI GAP:** generated coverage is insufficient; update
    `openwiki/INSTRUCTIONS.md` rather than deleting the manual source.
- **MEMORY disposition:**
  - keep rationale, durable caveats, learned environmental/operational facts, and non-derivable
    decisions;
  - remove seed/examples or live advice that merely restate facts directly visible in current
    repository source and now covered by OpenWiki;
  - never rewrite closed historical plans/logs as part of this cleanup.
- **Acceptance criteria:**
  - no file is removed just because OpenWiki exists;
  - every removal/shortening has a concrete generated replacement or clear human-entry-point
    rationale;
  - OpenWiki does not become authority for normative requirements.
- **Verification:**
  - documentation profile review of the proposed disposition before destructive removals.

### Step D4 — Apply the conservative documentation/MEMORY migration

- [ ] **Owner:** `coder` for tracked repository edits, with `documenter` owning prose
- **Target files:**
  - `README.md`
  - selected live `docs/**` proven duplicate in D3
  - `shared/MEMORY.md`
  - `openwiki/INSTRUCTIONS.md` when D3 found generation gaps
  - root/manual links that point to removed descriptive docs
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode for any code/script change
  - `shared/skills/documentation/SKILL.md`
  - `shared/skills/humanize/SKILL.md`
  - `shared/skills/learn/SKILL.md`
- **Rules:**
  - prefer shortening/linking over deletion when a document has a human audience;
  - preserve ADRs, security docs, policy, operator procedures, and dated historical records;
  - keep README as a small useful entry point;
  - narrow MEMORY rather than deleting it;
  - update references atomically so no live link points to a removed path
    (`validate_targets.py` link integrity covers `README.md`, `AGENTS.md`, and `docs/*.md`).
- **Acceptance criteria:**
  - no stale live links;
  - no normative information exists only in generated OpenWiki;
  - no repository-derived fact is needlessly duplicated into MEMORY.
- **Verification:**
  - `uv run python scripts/validate_targets.py`;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step D5 — Refresh OpenWiki after migration and verify stable ownership

- [ ] **Owner:** `coder`
- **Target files:**
  - generated `openwiki/**` only
- **Required Skills:**
  - `shared/skills/openwiki/SKILL.md`
- **Execution:**
  - rerun `.claude/scripts/openwiki_refresh.py --require-enabled` after all D4 tracked manual
    changes are complete;
  - review the generated delta;
  - a clean no-op update spends no model work but still rewrites
    `openwiki/.last-update.json`; do not run a third pass merely to prove idempotence, since
    deterministic runner tests already cover the wrapper's invariants.
- **Acceptance criteria:**
  - OpenWiki reflects the final Phase D manual source state;
  - root adapters remain protected and no workflow file appeared;
  - generated content does not contain references to deleted manual docs unless those references
    are intentionally historical;
  - no unexpected outer path changed.
- **Verification:**
  - inspect `git diff -- openwiki`;
  - sample grounded claims against source/tests;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step D6 — Run the full cross-model and security acceptance review

- [ ] **Owner:** `reviewer`
- **Target files:** full Phase D diff plus the integrated behavior from Phases A, B, and C
- **Required Skills:** none beyond reviewer-owned profile guidance
- **Review Profiles:**
  - `code`
  - `architecture`
  - `security`
  - `tests`
  - `ponytail` when Phase D includes code/config changes
  - `documentation`
- **Review focus:**
  - Codex, Claude, Copilot, and Antigravity all have a provider-neutral path to find/use the
    wiki without OpenWiki host installers;
  - root guidance remains bootstrap-owned;
  - no provider credential or local OpenWiki config entered Git or ai-state;
  - `.openwikiignore` excludes the intended state/generated paths without hiding canonical
    implementation evidence;
  - generated wiki is clearly subordinate to source/tests/policy;
  - final knowledge-phase semantics from Phase C are implementable by the orchestrator;
  - documentation migration did not erase unique human/normative content.
- **Acceptance criteria:**
  - CRITICAL/MAJOR findings resolved;
  - surviving MINOR findings explicitly disposed;
  - documentation review passes.

### Step D7 — Complete the required final stale-claims, MEMORY, and LEARN audit

- [ ] **Owner:** `documenter` + orchestrator closeout
- **Surfaces to inspect:** root guidance (`AGENTS.md`, `CLAUDE.md`, `README.md`); live
  `docs/` except dated historical documents; canonical `shared/policies/**`,
  `shared/skills/**`, `shared/templates/**`, `shared/agents/**`, and review profiles; state
  READMEs; `shared/MEMORY.md` and live `.claude/MEMORY.md`; `openwiki/INSTRUCTIONS.md` and the
  generated OpenWiki entry/index pages.
- **Required Skills:**
  - `shared/skills/documentation/SKILL.md`
  - `shared/skills/humanize/SKILL.md`
  - `shared/skills/learn/SKILL.md`
  - `shared/skills/deep-audit/SKILL.md`
- **Audit targets:**
  - old wording that says MEMORY is the portable authority for repository-derived architecture;
  - instructions to read all of `docs/` at startup;
  - documenter rules that always create/update descriptive `docs/ARCHITECTURE.md` even when
    OpenWiki owns that detail;
  - any implication that generated root adapters may be hand-edited;
  - any implication that OpenWiki is scheduled or automatic;
  - any claim that OpenWiki replaces policy, ADRs, plans, logs, or all documentation;
  - any stale dependency/runtime version claim (Node, `context-mode`, `openwiki`, `mermaid`,
    `jsdom`).
- **Closeout evidence:**
  - leave closed historical plans/logs unchanged unless current errata rules specifically apply;
  - in the Phase D COMPLETED session log add the exact heading:
    `## Stale-claims surfaces checked`;
  - list every audited surface and outcome under that heading before `verify.py closeout`;
  - state in the same log that Phase D was a transition phase and that future OpenWiki-enabled
    plans use the small knowledge-refresh shape from Phase C.
- **Acceptance criteria:**
  - final live advice tells one coherent ownership/lifecycle story;
  - closeout gate accepts the non-empty stale-claims section.

## Verification

Phase D is the only phase that intentionally performs real model-backed OpenWiki work. Keep those
runs bounded to the generation/update needed to prove and finalize the integration.

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json
```

The actual OpenWiki acceptance command is the bootstrap wrapper, not raw OpenWiki:

```bash
uv run python .claude/scripts/openwiki_refresh.py --require-enabled
```

Normal completion then follows the fixed closeout sequence and requires canonical
`verify phase` then `verify closeout` PASS receipts.

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`.

- [ ] Bootstrap repository has `openwiki/INSTRUCTIONS.md` and a reviewed `.openwikiignore`
- [ ] Real OpenWiki generation/update succeeded through the bootstrap-owned runner
- [ ] Root `AGENTS.md` / `CLAUDE.md` remained bootstrap-owned and byte-stable across the run
- [ ] No OpenWiki scheduled workflow was created or changed
- [ ] No credential/private OpenWiki config was committed; `openwiki/.run.json` is not tracked
- [ ] Documentation/MEMORY migration was conservative and evidence-backed
- [ ] Documentation updated
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED` and names Phase D as a transition phase
- [ ] Closeout session log contains a non-empty `## Stale-claims surfaces checked`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
- [ ] Final OpenWiki content is subordinate to source/tests/policy and is not hand-edited

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
