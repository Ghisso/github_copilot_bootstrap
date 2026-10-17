# Session: Gate repair — Phase E, knowledge refresh and final audit

**Date:** 2026-10-17
**Plan:** .claude/plans/2026-10-17_phase-E-gate-repair-knowledge-refresh.md
**Parent plan:** .claude/plans/gate-repair.md
**Status:** COMPLETED

## Goal

Final stale-claims audit of every live-advice surface (GR-012), confirm the
plan's boundaries held (GR-013), and refresh the OpenWiki knowledge layer.

## Task Tracking

- [x] PRE-FLIGHT: Phase D committed (`bac1d59`) and pushed; post-commit hook
  activated Phase E. OpenWiki last refreshed at `f3a8337` (2026-10-06), so
  Phases A–D and the behavioral pilot's later commits are not in the wiki.
- [x] PLAN WHEN NEEDED: approved plan is implementation-ready.
- [x] IMPLEMENT (audit, fixes, OpenWiki refresh)/VERIFY/REVIEW/CLOSEOUT
- [ ] COMMIT
- [ ] PUSH

## Work Log

- **15:50** - Read-only stale-claims sweep delegated to an Explore agent;
  fixes follow, then one OpenWiki refresh after all source edits (MEMORY
  lesson: later source edits can stale cited claim ranges).

- **16:10** - Sweep results (read-only agent, HEAD `bac1d59`): no live claim
  contradicted by the plan's code; several incomplete or outdated
  statements and three missing follow-ups. Fixes split: coder (Ponytail
  "mandatory" wording in three skills with hash pins; `.vscode/mcp.json` in
  the control-plane list in policy, generator, quoted copies, and root
  guidance; root `CLAUDE.md` commit rule; workflow enforcement summary;
  tool-routing filtered-hook sentence; root `AGENTS.md` Context Mode line),
  documenter (parity table rows, Evidence column, follow-ups, runtime-checks
  line, sidecar-contract errata, README Copilot note), orchestrator (MEMORY
  entries at the MCP-grant and Ponytail-gate lessons; MEMORY file-protection
  lesson corrected after a probe showed `grep` naming a protected path is
  allowed while a heredoc is still denied; Phase E plan line pointed at the
  target-mapping follow-ups).

- **19:15** - After the source edits, the self-install, `check_runtime.py`,
  `validate_targets.py`, and `verify.py fast` passed. OpenWiki run
  `c04b431e-b61c-4d1f-82f6-5327b4a15671` refreshed ten pages and finished
  `complete`. Two evidence ranges on the `tracked_state_hash` claim of
  `operations/deterministic-verification.md` were wrong (taken from an
  earlier read, not a fresh search). A narrow run
  `10546fdb-a37d-4f48-94ad-4b937e92ce4c` planned that one page, revised only
  that claim's evidence to `verify.py#L1735-L1745` and `#L2093-L2101`, and
  finished `complete`. Root `AGENTS.md` and `CLAUDE.md` blobs are unchanged
  by both runs (`2a0f2f64…`, `f39e62b0…`); no `openwiki/.run.json` remains.

- **19:45** - Review round 1 (fresh reviewer; documentation, code,
  architecture, security, tests, ponytail): PASS, no CRITICAL or MAJOR,
  seven MINORs. Fixed four: the GR-008 count in this log, the Ponytail pin
  LEARN entry (`deep-audit` has no pin), two unrecorded `.vscode/mcp.json`
  leftovers added to the surfaces list, and a false "cannot drift" comment
  in `_lib-frontmatter.sh` (same line count, so no wiki range moved).
  Regenerated, self-installed, and re-ran the checks and `verify.py phase`
  (PASS, 2767 passed, 1 skipped). Round 2: PASS, no new findings, no open
  request. Three MINORs carry dispositions: the `ponytail-review`
  description (accepted), and the parity-row `.claude/hooks/` gap and the
  wiki "always applies both rules" wording (deferred to the next managed
  OpenWiki refresh).

## Stale-claims surfaces checked

The sweep ran read-only at HEAD `bac1d59` against `git diff dev...HEAD`
(67 files). Outcome per surface:

- **Root guidance.**
  - `CLAUDE.md`: commit rule now names the gate result, open requests, and
    required profiles; `.vscode/mcp.json` added to the control-plane list
    (from `scripts/generate_targets.py`); Context Mode line narrowed.
    Fixed.
  - `AGENTS.md`: Context Mode line said it gives "compaction-safe session
    continuity" everywhere; now names `ctx_index`/`ctx_search` and says
    Antigravity does not wire the hooks. Fixed.
  - `README.md`: hook-lane text did not mention Copilot terminal tools;
    note added. Fixed.
- **`docs/`.**
  - `docs/target-mapping.md`: "Later phases add rows." removed; rows added
    for the review gate (A) and the failure-masking check (D); Evidence
    column added; stray "read tools allowed" removed from the branch-check
    row; three missing follow-ups added (agent definition files
    unprotected, `antigravity-cli` hooks not wired, GR-002 not covering
    every multi-file diff). Fixed.
  - `docs/runtime-checks.md` upgrade table: "A live plan blocks approval"
    now says it blocks implementation-branch creation and the next commit.
    Fixed.
  - `docs/sidecar-provider-contract.md`: dated evidence record; quote left
    as it is, one errata line added after it. Fixed by errata.
  - `docs/smoke-tests.md`: already carries the enforcement note. No change.
- **Shared policies.**
  - `workspace.instructions.md`: `.vscode/mcp.json` added to the
    control-plane list; Ponytail routing now says what the commit gate
    enforces. Fixed.
  - `workflow.instructions.md`: enforcement summary and recovery
    checklist now name the branch-time plan validator and the gate result
    and profile rules. Fixed.
  - `tool-routing.instructions.md`: hooks described as advice only; root
    adapters described as starting the server only through the guarded
    dispatcher. Fixed.
  - `quality-and-testing.instructions.md`: every `record_findings.py`
    example carries `--gate-result`; `[]` is qualified. No change.
- **Shared skills.** `ponytail/SKILL.md` ("mandatory"),
  `ponytail-review/SKILL.md` ("after every coding task"), and
  `deep-audit/SKILL.md` (cited "mandatory") now match what the gate
  enforces. Hash pins updated in `scripts/validate_targets.py` and
  `shared/third_party/ponytail/UPSTREAM.md`; sidecar snapshot hash and line
  counts updated in `tests/test_validate_targets.py`. `commit` and
  `code-review` skills already carry `--gate-result`. Fixed.
- **Hook and generator quotes.** `_lib-frontmatter.sh` comment and
  `generate_targets.py` quoted the control-plane sentence word for word;
  updated with it. Fixed.
- **Templates, agents, review profiles.** Reviewer prompt already maps
  PASS/WARN/FAIL and qualifies `[]`. No change. Left on purpose:
  `shared/agents/coder/prompt.md` lists the control-plane files without
  `.vscode/mcp.json`, because `tests/test_validate_targets.py` forbids
  "vscode" in the rendered Antigravity adapter.
- **Hook classifier.** `diff_requires_ponytail` in `_lib-frontmatter.sh`
  omits `.vscode/mcp.json`. Left on purpose: `required_review_profiles` in
  `verify.py` requires all five profiles for it. The comment above
  `typo_bypass_diff_allowed` had claimed the two lists match; it now names
  the gap (review round 1 finding).
- **State READMEs.** `.claude/quality_reports/README.md` is not wrong. No
  change.
- **`.claude/MEMORY.md`.** Subagent MCP-grant entry superseded by the
  2026-10-17 probe; Ponytail gate entry extended with the GR-002 path
  rules; file-protection entry corrected after a probe (`grep`/`rg` naming
  a protected path is allowed; heredocs and interpreter code are denied).
  Fixed.
- **Live plan.** Phase E plan line 46 pointed follow-ups at the audit
  exploration, which line 53 says to leave unchanged; now points at the
  `docs/target-mapping.md` follow-ups list. Fixed.
- **OpenWiki (generated).** Pre-plan gate wording, plan-approval timing, and
  `sandbox_mode` wording on `workflows/lifecycle-and-task-lanes.md`,
  `operations/deterministic-verification.md`, and
  `architecture/agents-and-skills.md`. Fixed through the two managed runs
  only; no hand edits.
- **Dated records left unchanged.** `plans/plan-agent-model-effort-tiers.md`
  (a 2026-07-09 proposal linking the deleted `agent.schema.json`), archived
  plans, closed session logs, and the 2026-10-17 audit exploration.

## Phase Summary

Phase E changed no executable behavior. It aligned root guidance, docs,
policies, three Ponytail-related skills (two of them hash-pinned), and
MEMORY with Phases A–D, completed
the client parity table with evidence, recorded the open follow-ups where
the next planner reads them, and refreshed ten OpenWiki pages.

## Requirement Mapping

| Req | Phase | Evidence |
| --- | --- | --- |
| GR-001 | A (`5eaa18e`) | `record_findings.py` schema 2; `tests/test_verify.py`, `tests/test_commit_closeout.py`, installed-hook smoke |
| GR-002 | A | `required_review_profiles` in `verify.py`; `.vscode/mcp.json` in `CONTROL_PLANE_FILES`; `tests/test_verify.py` |
| GR-003 | A | Ponytail error unit test; WARN-report and missing-`tests` smoke denials |
| GR-004 | A | Staged change after closeout blocks with "closeout receipt final tracked state is stale"; `tracked_state_hash` documented informational |
| GR-005 | C (`4103933`) | `root_mcp_adapter_errors` over three root adapters; `tests/test_validate_targets.py` |
| GR-006 | C | `mcp__context7` in `CLAUDE_TOOL_MAP["search"]`; Codex and Antigravity evidence and gaps in `docs/target-mapping.md` |
| GR-007 | B (`de5a2f8`) | Field allowlist filter; 32 fixtures under `tests/fixtures/context_mode_hook/1.0.169/`; real-binary check |
| GR-008 | D (`bac1d59`) | Eight configs added to `HOOK_CONFIGS` (twelve total); `settings.local.json` untracked with preserve/restore; `tests/test_hook_gates.py`, `tests/test_protect_files_scoping.py`, `tests/test_state_sync.py` |
| GR-009 | D | Branch gate runs the plan validator on the big plan and listed phases; `tests/test_branch_state.py` |
| GR-010 | D | Deprecation steps keep pytest's status; `failure_masking_command_errors` check |
| GR-011 | D | `shared/schemas/agent.schema.json` deleted; only `native-client-observation.schema.json` remains |
| GR-012 | E | This log's surfaces list; OpenWiki runs `c04b431e…` and `10546fdb…` complete |
| GR-013 | all | No model call or new network download added to tests, hooks, or `verify.py` since `dev` (the only `npx` line is the pre-existing pinned runtime fallback; `curl` strings are recorded fixture data); Context Mode pin still `1.0.169`; no dependency file changed; push gates apply the new rules only to `schema_version >= 2` reports |

## [LEARN] Entries

- [LEARN:documentation] Take every OpenWiki claim's line range from a search
  run in the same step as `openwiki_submit_page`, not from an earlier read
  or a subagent report. Two ranges cited from an earlier read were about 40
  lines off and needed a corrective run (gate-repair Phase E).
- [LEARN:verification] Editing a pinned Ponytail skill (`ponytail` or
  `ponytail-review`) moves these pins: the hash in
  `scripts/validate_targets.py`; the hash in "Local allowlist hashes" and the
  "N lines against upstream" text in
  `shared/third_party/ponytail/UPSTREAM.md`; the matching line-count
  literals and, for a skill the sidecar ships,
  `SIDECAR_SKILLS_PROFILE_SNAPSHOT_SHA256` in
  `tests/test_validate_targets.py`. `deep-audit` has no pin (gate-repair
  Phase E).

## Verification

- PASS       53.9s  uv run python scripts/validate_targets.py
- PASS        0.8s  uv run python scripts/check_runtime.py
- PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
- PASS        0.2s  uv run python .claude/scripts/verify.py fast --format json

Phase receipt: `verify.py phase --format json --persist` PASS (pytest 2767
passed, 1 skipped). Findings report:
`.claude/quality_reports/findings-2026-10-17_phase-E-gate-repair-knowledge-refresh.json`
(3 MINOR with dispositions, `gate_result: PASS`, six profiles).

- optional 1: PASS — OpenWiki runs `c04b431e-b61c-4d1f-82f6-5327b4a15671` and `10546fdb-a37d-4f48-94ad-4b937e92ce4c` returned `complete` from `openwiki_finish`; reviewed pages: `architecture/agents-and-skills.md`, `architecture/hooks-and-guardrails.md`, `architecture/source-generated-consumer-layout.md`, `operations/context-mode-dispatcher.md`, `operations/deterministic-verification.md`, `operations/git-backed-ai-state-sync.md`, `operations/install-ownership-and-runtime-checks.md`, `operations/sidecar-overlay.md`, `quickstart.md`, `workflows/lifecycle-and-task-lanes.md`.

## Open Questions / Next Steps

- The big plan is complete after this commit. Opening a pull request from
  `gate-repair_implementation` to `dev` is the user's decision.
- Next managed OpenWiki refresh: add `.claude/hooks/` to the Claude Code
  cell of the parity table's config-protection row, and scope the
  deterministic-verification page's "always applies both rules" sentence
  to phase completion.
- Open follow-ups are listed under "Recorded follow-ups" in
  `docs/target-mapping.md`.
