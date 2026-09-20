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
verification is a mandated, machine-read list of shell commands; `verify closeout` **runs every
one of them itself** and records each exit code and output tail inside the closeout receipt, so a
required check can neither be skipped nor reported as passed without having run; conditional
phrasing about checks is refused at plan time; optional checks have exactly one declared home;
the spike skill is routed to third-party binaries, CLIs, and MCP servers; and the `tests` review
profile asks whether the external dependency was ever exercised directly.

The user chose the run-it-yourself design over a log-accounting design on 2026-09-20. A gate that
only reads "PASS" out of the session log confirms the word was written, not that the command
ran; it would have moved Phase A's failure from "skipped and admitted" to "skipped and written as
passed". Running the commands removes the agent from the evidence path. The session log still
accounts for optional items, because those may be interactive procedures a script cannot run.

Measured before design, and it corrects the obvious assumption: Phase A's hedge was **not** in
the plan's `## Verification` block. It was a step-level `- **Verification:**` sub-bullet, and all
five commands the block did list genuinely passed. Running the block alone would have passed
Phase A. The hedge lint is what catches it. The two mechanisms are complementary, not redundant,
and they fire at different times: plan approval, and completion commit.

This is unrelated to OpenWiki and lives on this branch by the user's decision, to avoid a second
branch and a `verify.py` conflict with Phase G. It changes no check ID and no schema version:
`load_receipt` requires exactly `CHECK_IDS` and `historical_chain_errors` reloads every earlier
completed phase's receipt, so a new ID would invalidate Phases A–C. The run results live under
the receipt's existing optional `extensions` object (`RECEIPT_EXTENSIONS_FIELD`), which
`validate_receipt` already accepts as any dictionary, so Phase A–C receipts without it still
load. Both new gates surface through the existing closeout-evidence error path, the way Phase
C's stale-claims gate does. The closeout gate judges only the phase being completed
(`verify closeout` run and `gate --head-relation exact`); the plan-time lint judges only live
plans dated on or after 2026-09-19. Completed and cancelled plans are dated records and are
never re-judged.

Hedge-pattern measurement over this repository's small plans (110 at implementation time): a
bare phrase list flags 34, mostly ordinary prose; scoping to verification contexts only halves
recall. The first verb-anchored list flagged 10 plans, 7 genuine; re-measured on 2026-09-20, the
three `best-effort` false positives were design prose about sync behaviour and were dropped, and
plural verb forms were added. The final three patterns flag 5 plans, all genuine hedged checks:
four completed plans (Phase A's line among them) and the planned Phase G comment "runs only if a
Docker host is available", which Step F2.6 removes.

## Steps

### Step F2.1 — Write the canonical contract and update every surface that must produce it

- [ ] **Owner:** `documenter` (prose) + `coder` (templates, prompt strings)
- **Target files:**
  - modify `shared/policies/workflow.instructions.md`: new `## Verification Evidence Contract`
    section beside "Knowledge-Refresh Final Phase" (the single authoritative definition; all
    other surfaces link here); update "Session Logging" and the CLOSEOUT step of the Canonical
    Orchestrator Loop
  - modify `shared/templates/plan-small.md`: the `## Verification` block comment states that
    every non-comment line is a required shell command that `verify closeout` runs itself from
    the repository root and that must exit 0; anything a script cannot run (an interactive
    probe, a host session, a manual inspection) belongs under `## Optional Verification`; add
    that section with a one-line comment stating it is the only place a check may be
    conditional or non-executable; update the closeout checklist item
  - modify `shared/templates/session-log.md`: rename `## Verification Results` to
    `## Verification`; the section records each optional item's outcome (or NOT RUN with a
    reason) in the mandated line grammar, and pastes the one-line-per-item summary that
    `verify closeout --format text` prints for the required items
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
  fence languages, comment stripping, continuation joining, whitespace collapsing, every item a
  shell command run from the repository root, `verify.py closeout` never listed); that
  `verify closeout` runs the required items itself, in order, before it binds the tree, and
  refuses to persist a receipt when any item fails or times out; the per-item timeout constant
  `VERIFICATION_ITEM_TIMEOUT_SECONDS` and its value; where the results live
  (`extensions.verification_items` in the closeout receipt); the `## Optional Verification`
  rule; the log line grammar for optional items; the hedge rule with the pattern list
  reproduced verbatim and the constant name `HEDGED_VERIFICATION_PATTERNS`; the scopes
  (`VERIFICATION_CONTRACT_SINCE`, live statuses, completing phase only); and which script
  enforces which rule with which message prefix.
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

### Step F2.3 — `verify closeout` runs the required items and records them in the receipt

- [ ] **Owner:** `coder`
- **Target files:** modify `shared/scripts/verify.py`; extend `tests/test_verify.py`; adjust the
  two fixture helpers in `scripts/validate_targets.py` (`write_small_plan`,
  `write_fixture_closeout_receipt`) so their throwaway plans carry a one-command
  `## Verification` block and their fixture receipts carry the matching result, because the
  end-to-end scenarios drive the real commit and push hooks and must satisfy the new contract
- **Required Skills:**
  - `shared/skills/create-feature/SKILL.md`
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Contract — the runner (`verify closeout` side):**
  - `plan_verification_items` (mirror of the lint's copy, equality-tested).
  - `VERIFICATION_ITEM_TIMEOUT_SECONDS = 600`, separate from `COMMAND_TIMEOUT_SECONDS`
    because a required item may itself be `verify.py phase`, which already spends up to
    `COMMAND_TIMEOUT_SECONDS` on one pytest run.
  - `run_verification_items(root, phase) -> list[dict]` reads the completing phase's plan file
    through `confined_path` under `.claude/plans/`, extracts the required items, and runs each
    one in order with `subprocess.run(["bash", "-c", item], cwd=root, capture_output=True,
    text=True, timeout=VERIFICATION_ITEM_TIMEOUT_SECONDS)`. It never reads items from the
    command line or the environment. Each result is
    `{"item": <normalized text>, "status": "PASS" | "FAIL" | "TIMEOUT", "exit_code": int |
    None, "duration_seconds": float, "output_tail": <last 20 lines, at most 2000 characters>}`.
    It stops at the first non-PASS item and records the remaining items as
    `{"status": "NOT RUN", "exit_code": None, ...}`, because a later item may depend on an
    earlier one (for example `validate_targets.py` after `generate_targets.py --all`).
  - Nesting refusal: an item whose normalized text contains `verify.py closeout` is recorded as
    `FAIL` with `output_tail` "closeout may not list itself" and is not executed. This mirrors
    the lint's L4 for plans that predate the lint or were edited after approval.
  - **Ordering in `main`.** The runner executes **before** metadata is collected for closeout
    mode, so any file an item rewrites (generated targets, a persisted phase receipt) is part of
    the `tree_sha` and `content_hash` the receipt binds. `closeout_checks` then reuses the phase
    receipt an item may just have persisted, which is the intended freshness path, not a
    side effect.
  - Failure path: when any result is not `PASS`, `main` prints one line per item to stderr
    (`item`, `status`, `exit_code`, first line of `output_tail`) and returns 2 **before**
    `build_receipt`, alongside the existing `missing_documentation_na_reason` and
    `unpublishable_closeout_reason` pre-persist refusals. No receipt is written or overwritten.
  - Success path: the results list is stored at `receipt["extensions"]["verification_items"]`
    in the closeout receipt. `build_receipt` gains an optional `extensions` argument used only
    by closeout mode; `validate_receipt` is not changed, because it already accepts the field.
    In `--format text`, `verify closeout` prints one summary line per item
    (`PASS  1.3s  <item>`), which the closeout log pastes.
- **Contract — the gate (`git commit` side):**
  - `verification_items_errors(root, phase, receipt) -> list[str]` is called from
    `gate_receipt_errors` immediately after the existing `closeout_log_errors` call, guarded by
    `head_relation == "exact"`. Errors, each naming the plan path, the receipt path, the item,
    and the fix: **G1** the receipt has no `extensions.verification_items`; **G2** a required
    item in the plan has no result in the receipt; **G3** a result whose `status` is not `PASS`;
    **G4** the optional items are not all accounted for in the closeout log's `## Verification`
    section (an outcome line, or NOT RUN with a non-empty reason). G2 exists because the plan is
    a tracked file: under `exact` the tree binding already catches a plan edited after
    `verify closeout`, but the message names the item rather than reporting a stale tree.
    Extra results for items no longer in the plan are ignored.
  - `log_verification_outcomes(text)` is the only session-log parsing that remains, and it is
    used for optional items only.
  - Must not: add to `CHECK_IDS`, change `SCHEMA_VERSION`, change `validate_receipt`, change
    `closeout_log_errors`, or run for `ancestor` or `certified` relations.
- **Test scenarios (runner):** all items exit 0 and appear in `extensions.verification_items`
  with `PASS`, positive duration, and a captured tail; an item exiting 3 records `FAIL` with
  `exit_code: 3`, the following item records `NOT RUN`, `main` returns 2, and no receipt file is
  written; an item that sleeps past a monkeypatched one-second timeout records `TIMEOUT`; an
  item containing `verify.py closeout` is refused without executing; an item that writes a
  tracked file changes the receipt's `tree_sha` relative to a run without it, proving the
  runner precedes metadata collection; `output_tail` is cut to 20 lines and 2000 characters;
  a plan with an empty required block yields an empty results list and a passing closeout; an
  existing passing receipt is left unchanged when the rerun fails (existing refusal path).
- **Test scenarios (gate):** every G1–G4 path; a plan item added after the receipt was written
  fails G2 naming the item; optional NOT RUN with and without a reason; `ancestor` relation never
  produces these errors even with a receipt lacking `extensions`; a persisted pre-F2 closeout
  receipt for another phase (no `extensions`) still loads and passes `historical_chain_errors`;
  the two `plan_verification_items` copies are byte-equal; the Phase A plan text as a fixture
  passes the runner's extraction with its five historically listed commands, proving the lint
  rather than the runner is what catches Phase A.

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
  - `docs/runtime-checks.md`: three rows in "Other gates that newly block a refresh" (plan-time
    lint L1–L4; `verify closeout` refusing to persist when a required item fails, times out, or
    is `NOT RUN`; commit-time gate G1–G4), each with the exact message prefix and the recovery,
    plus one paragraph describing that closeout runs the plan's required block itself, where the
    results are stored in the receipt, the per-item timeout, and the gate's `exact`-only scope
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
  - no check ID or schema change; Phase A–C receipts (which have no `extensions`) still load
  - the runner reads items only from the tracked plan file under `.claude/plans/` through
    `confined_path`, never from arguments or the environment, and refuses `verify.py closeout`
    as an item (`security`)
  - the runner executes before closeout metadata is collected, so files an item rewrites are
    inside the bound tree (`architecture`)
  - a failing or timed-out item returns 2 before `build_receipt`; no receipt is written
  - the gate never runs for an `ancestor` or `certified` relation
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

This phase's own completion commit is the first real exercise of the new runner: `verify closeout`
runs the seven items above itself, and its receipt must carry seven `PASS` results. The last item
persists the phase receipt that closeout then reuses, which is the intended order.

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, CLOSEOUT); the order below mirrors it rather than restating it.

- [ ] Documentation updated (`docs/runtime-checks.md` rows and paragraph)
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED` and a `## Verification` section pasting the runner's seven PASS summary lines (this plan has no optional items)
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
