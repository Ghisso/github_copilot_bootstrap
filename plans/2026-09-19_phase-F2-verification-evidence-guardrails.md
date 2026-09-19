---
name: 2026-09-19_phase-F2-verification-evidence-guardrails
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 7
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-09-19_phase-F2-verification-evidence-guardrails

## Scope

Phase A listed a real-CLI smoke check, hedged it ("when a devcontainer build environment is
available"), never ran it, recorded "not run because no build environment was used", and passed
closeout. This phase makes that class of failure impossible without judgement: a plan's required
verification is a mandated, machine-read list; the completing phase's closeout log must account
for every item with a PASS; conditional phrasing about checks is refused at plan time; optional
checks have exactly one declared home; the spike skill is routed to third-party binaries, CLIs,
and MCP servers; and the `tests` review profile asks whether the external dependency was ever
exercised directly.

Measured before design, and it corrects the obvious assumption: Phase A's hedge was **not** in
the plan's `## Verification` block. It was a step-level `- **Verification:**` sub-bullet, and all
five commands the block did list genuinely passed. Closeout accounting alone would have passed
Phase A. The hedge lint is what catches it. The two mechanisms are complementary, not redundant,
and they fire at different times: plan approval, and completion commit.

This is unrelated to OpenWiki and lives on this branch by the user's decision, to avoid a second
branch and a `verify.py` conflict with Phase G. It changes no check ID: `load_receipt` requires
exactly `CHECK_IDS` and `historical_chain_errors` reloads every earlier completed phase's
receipt, so a new ID would invalidate Phases A–C. Both new gates surface through the existing
closeout-evidence error path, the way Phase C's stale-claims gate does. The closeout gate judges
only the phase being completed (`verify closeout` run and `gate --head-relation exact`); the
plan-time lint judges only live plans dated on or after 2026-09-19. Completed and cancelled plans
are dated records and are never re-judged.

Hedge-pattern measurement over this repository's 107 small plans: a verb-anchored pattern list
flags 10 plans, 7 of them genuine hedged checks (Phase A's line among them); a bare phrase list
flags 34, mostly ordinary prose; scoping to verification contexts only halves recall.

## Steps

### Step F2.1 — Write the canonical contract and update every surface that must produce it

- [ ] **Owner:** `documenter` (prose) + `coder` (templates, prompt strings)
- **Target files:**
  - modify `shared/policies/workflow.instructions.md`: new `## Verification Evidence Contract`
    section beside "Knowledge-Refresh Final Phase" (the single authoritative definition; all
    other surfaces link here); update "Session Logging" and the CLOSEOUT step of the Canonical
    Orchestrator Loop
  - modify `shared/templates/plan-small.md`: the `## Verification` block comment states that
    every non-comment line is a required item the closeout log must record as PASS; add an
    `## Optional Verification` section with a one-line comment stating it is the only place a
    check may be conditional; update the closeout checklist item
  - modify `shared/templates/session-log.md`: rename `## Verification Results` to
    `## Verification` and show the mandated line grammar
  - modify `shared/skills/plan-decomposition/SKILL.md` Step 4 "Verification" bullet
  - modify `shared/agents/planner/prompt.md` (Plan Requirements), plus the routing rule from F2.4
  - modify `shared/agents/orchestrator/prompt.md` CLOSEOUT step
  - modify `shared/skills/commit/SKILL.md`: add the accounted `## Verification` section to the
    listed completion gates
- **Required Skills:**
  - `shared/skills/documentation/SKILL.md`
  - `shared/skills/humanize/SKILL.md`
  - `shared/skills/ponytail/SKILL.md` in `full` mode
- **Canonical text must state, imperatively:** the plan block shape and parsing rules (section,
  fence languages, comment stripping, continuation joining, whitespace collapsing, labels for
  interactive procedures, `verify.py closeout` never listed); the `## Optional Verification`
  rule; the log line grammar; the hedge rule with the pattern list reproduced verbatim and the
  constant name `HEDGED_VERIFICATION_PATTERNS`; the scopes (`VERIFICATION_CONTRACT_SINCE`, live
  statuses, completing phase only); and which script enforces which rule with which message
  prefix.
- **Acceptance criteria:** every rule the code enforces is written here first; no other file
  restates it, they link; generated targets carry the template and prompt changes.

### Step F2.2 — Plan-time lint in `validate_plan_frontmatter.py`

- [ ] **Owner:** `coder`
- **Target files:** modify `scripts/validate_plan_frontmatter.py`; extend
  `tests/test_validate_plan_frontmatter.py`
- **Required Skills:**
  - `shared/skills/create-feature/SKILL.md`
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Contract:**
  - `VERIFICATION_CONTRACT_SINCE = "2026-09-19"`; `HEDGED_VERIFICATION_PATTERNS` compiled once.
  - `plan_verification_items(text)` returns (required, optional) normalized items from the
    `## Verification` and `## Optional Verification` H2 sections. Mirrored byte-for-byte in
    `verify.py` with an equality test; both ship to consumers as stdlib-only files and may not
    import each other.
  - `validate_verification_contract` runs only when `type == small-plan`,
    `status in {planned, in-progress, paused}`, and the slug date is absent or
    `>= VERIFICATION_CONTRACT_SINCE`.
  - Messages, each naming file, line, and fix: **L1** missing fenced block under
    `## Verification`; **L2** hedged verification, quoting the matched text and naming both
    remedies; **L3** a required item that cannot fail (`|| true`, `|| :`); **L4**
    `verify.py closeout` listed as an item.
  - Must not: read Git state, lint completed or cancelled plans, or parse step bullets.
- **Test scenarios:** in-scope plan without a block fails L1; a hedged sentence in a step title,
  an owner line, an acceptance bullet, and an HTML comment each fail L2 with the matched text;
  the same sentence inside a fenced block or under `## Optional Verification` passes; `|| true`
  in the required block fails L3; `verify.py closeout` fails L4; a `complete`, `cancelled`, or
  pre-2026-09-19 plan with all four defects passes; the Phase A plan text as a fixture copy
  fails L2 on its step-bullet sentence; the current G–K plan texts pass after F2.6; the two July
  `in-progress` plans pass unchanged.

### Step F2.3 — Closeout accounting in `verify.py`

- [ ] **Owner:** `coder`
- **Target files:** modify `shared/scripts/verify.py`; extend `tests/test_verify.py`
- **Required Skills:**
  - `shared/skills/create-feature/SKILL.md`
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Contract:**
  - `plan_verification_items` (mirror, equality-tested); `log_verification_outcomes` maps each
    normalized item recorded under the log's `## Verification` H2 to `(outcome, detail)`;
    `verification_accounting_errors(root, phase, log_path)`.
  - Errors, each naming the log path, the plan path, the item, and the fix: **G1** no
    `## Verification` section in the log; **G2** no outcome recorded for a required item;
    **G3** FAIL recorded for a required item; **G4** NOT RUN recorded for a required item;
    **G5** an optional item unaccounted for, or NOT RUN with an empty reason.
  - Call sites: `gate_receipt_errors` immediately after the existing `closeout_log_errors` call,
    guarded by `head_relation == "exact"`; and the `verify closeout` run as a pre-persist error
    alongside `missing_documentation_na_reason`, so the operator sees it when running
    `verify closeout` rather than only at `git commit`. Extra recorded items are ignored.
  - Must not: add to `CHECK_IDS`, change `SCHEMA_VERSION`, change `closeout_log_errors`, or run
    when `head_relation` is `ancestor` or `certified`.
- **Test scenarios:** every G1–G5 path; exact match after normalization (trailing comment,
  continuation lines, whitespace); PASS with trailing detail; optional NOT RUN with and without a
  reason; `ancestor` relation never produces these errors even with a non-compliant log; a
  persisted pre-F2 receipt for another phase still loads; the Phase A plan-and-log pair as
  fixture copies passes as historically written, proving the lint rather than the gate is what
  catches Phase A.

### Step F2.4 — Route the spike skill to third-party binaries, CLIs, and MCP servers

- [ ] **Owner:** `documenter` + `coder`
- **Target files:**
  - modify `shared/skills/integration-gate-spike/SKILL.md`: description triggers and Step 1
    unknowns gain "Invocation contract — flags, exit codes, TTY needs, stdio protocol,
    config-file side effects" and "any third-party binary, CLI, MCP server, or SDK whose real
    behavior has not been observed in this repository"
  - modify `shared/agents/planner/prompt.md`: a step that pins, wraps, or calls such a dependency
    lists `integration-gate-spike` in Required Skills and its real-invocation check in the
    required `## Verification` block, or the plan gets an evidence-only spike phase first
  - modify `shared/skills/add-dependency/SKILL.md`: one cross-reference line for binary and CLI
    dependencies
- **Required Skills:**
  - `shared/skills/documentation/SKILL.md`
  - `shared/skills/humanize/SKILL.md`
- **Acceptance criteria:** Phase A's Step A1, read against the new planner bullet, would have
  required the spike skill and a real-invocation item in the required block.

### Step F2.5 — Reviewer question in the `tests` profile

- [ ] **Owner:** `documenter`
- **Target files:** modify `shared/review-profiles/tests.md`
- **Required Skills:**
  - `shared/skills/documentation/SKILL.md`
- **Behavior:** add the checklist item "Was every third-party binary, CLI, MCP server, or SDK
  this diff depends on exercised directly at least once — spike evidence, a real-binary test, or
  a recorded observation — or only through test doubles? Name the evidence." Severity Major when
  only doubles exist. `tests` owns it because it is a test-doubles question; duplicating it
  across profiles invites two verdicts.

### Step F2.6 — Bring live plans into compliance and document the gates

- [ ] **Owner:** `coder`
- **Target files:**
  - `.claude/plans/2026-09-19_phase-G-openwiki-host-driven-guard.md`: Step G2 redesigned to add
    no check ID (the OpenWiki managed-block condition moves into `VFY-GEN-001`'s remit and the
    closeout-evidence path); Step G4's Docker-build assumption moved to `## Optional Verification`
    and the smoke item's recorded outcome must show `1 passed`, not `skipped`
  - `.claude/plans/2026-09-19_phase-I-openwiki-enable-and-first-generation.md`: Step I3's Codex
    re-probe declared under `## Optional Verification`
  - `docs/runtime-checks.md`: two rows in "Other gates that newly block a refresh" (plan-time
    lint L1–L4, closeout accounting G1–G5), each with the exact message prefix and the recovery,
    plus one paragraph describing the accounting and its `exact`-only scope
  - `docs/architecture.md` only if it describes the closeout gate list
- **Required Skills:**
  - `shared/skills/documentation/SKILL.md`
  - `shared/skills/humanize/SKILL.md`
- **Acceptance criteria:** `validate_plan_frontmatter.py` passes over the whole plans directory
  with the new lint active; both runtime-checks rows name the file the message points at and the
  fix.

### Step F2.7 — Review

- [ ] **Owner:** `reviewer`
- **Target files:** scoped Phase F2 diff
- **Review Profiles:**
  - `code`
  - `architecture`
  - `security`
  - `tests`
  - `ponytail`
  - `documentation`
- **Review focus:**
  - no check ID or schema change; Phase A–C receipts still load
  - the accounting never runs for an `ancestor` or `certified` relation
  - the two `plan_verification_items` copies are equality-tested
  - every message names file, line or item, and fix
  - the hedge list in code equals the canonical text
  - the lint's measured false-positive profile is acceptable, or the documented fallback scope
    is chosen
  - templates, prompts, skills, and docs link to the one canonical section rather than restating
    it
  - this plan's own `## Verification` block and closeout log satisfy the contract

## Verification

```bash
uv run pytest tests/test_validate_plan_frontmatter.py tests/test_verify.py -q --tb=short
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json
uv run python .claude/scripts/verify.py phase --format json --persist
```

This phase's own completion commit is the first real exercise of the new gate: the closeout log
must record each of the seven items above as PASS, exactly as written.

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, CLOSEOUT); the order below mirrors it rather than restating it.

- [ ] Documentation updated (`docs/runtime-checks.md` rows and paragraph)
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED` and a `## Verification` section recording every item above as PASS
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
- [ ] `CHECK_IDS` and `SCHEMA_VERSION` unchanged; Phase A–C receipts still load
- [ ] Live plans G–K pass the new lint; Phase G's plan text carries the amended Step G2

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
