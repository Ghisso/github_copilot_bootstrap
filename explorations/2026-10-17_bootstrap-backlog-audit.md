# Exploration — Audit of an Outside Improvement Backlog Against `dev`

**Date:** 2026-10-17
**Status:** COMPLETE — read-only audit of `dev` at `050a1de` (after PR #45).
Its confirmed defects feed the big plan `.claude/plans/gate-repair.md`.
**Trigger:** another agent with no code access wrote a consolidated
improvement backlog from August–October 2026 conversations and asked for a
read-only audit before choosing the next big plan. The user asked for that
audit and for the result to be saved here.

---

## 1. Read this first

- Most of the backlog is already implemented, partly implemented, or already
  decided. Do not re-plan an item below without reading its row.
- The audit found real gate defects that matter more than the new
  experiments. They are listed in §5 and planned in `gate-repair`.
- Each defect says whether the main agent **re-checked** it or whether it was
  only **reported** by one of the four audit agents.
- Status labels used in §4:
  - **VERIFIED** — implemented, and an automated deterministic test or
    check covers it.
  - **UNVERIFIED** — implemented, but only a "text ships" test (a required
    phrase is present) or nothing automated proves it works, or it was never
    observed in the real client.
  - **PARTIAL** — part of the idea exists.
  - **PLANNED** — only in a plan or exploration.
  - **REJECTED** — explicitly decided against or deferred as a non-goal.
  - **ABSENT** — no trace found.

Method: four parallel read-only audit agents (planning/evaluation,
context/knowledge, providers/consumers, security/skills), then main-agent
re-checks of the most important claims, plus live runs of the Context Mode
hook dispatcher and one subagent tool-list probe during planning.

---

## 2. Corrections to the outside backlog

| Outside claim | Actual state on 2026-10-17 |
| --- | --- |
| OpenWiki `0.6.0` is the newest release | Newest is `v0.7.2` (2026-10-09). The repo pins `0.5.2` in `shared/devcontainer/Dockerfile:31,37`, `scripts/validate_targets.py:261,9281,9298`, `shared/hooks/scripts/openwiki-guard.py:4`, and `tests/test_openwiki_cli_smoke.py:114`. The upgrade rule in `.claude/plans/2026-09-19_openwiki-knowledge-layer-integration.md:247` still names a retired runner. |
| Context Mode is integrated with four filtered tools | True for every generated target and the root Codex config. False for this repo's tracked root `.mcp.json` (Claude) and `.vscode/mcp.json` (Copilot): both start `context-mode` directly. See §5 D1. |
| Spec Kit concepts are open | Installing Spec Kit was rejected (`.claude/explorations/2026-10-02_bootstrap-engineering-workflow/README.md:104-105,182`); two ideas were borrowed. |
| 54 skills; implement `validate_skills.py` | 55 skills. A separate validator was rejected; skill checks live in `scripts/validate_targets.py` (`shared_skill_integrity_errors`, :8257). |
| Sidecar root `ai-bootstrap/` | It is `.ai-bootstrap/`. |
| Pi was investigated in September | No trace in plans, explorations, MEMORY, or docs. |
| Ponytail 5 is new | Correct. Upstream `v5.0.0` 2026-10-08, latest `v5.3.2` 2026-10-16. The repo vendors `v4.8.4` (`shared/third_party/ponytail/UPSTREAM.md:4-5`). Ponytail 5's own benchmark numbers are self-reported. |
| GLiClass v4 for task classification | Assessed 2026-10-17: not a fit for the bootstrap itself (hooks and `verify.py` stay model-free; the Task Lanes table is the only lane classifier). A possible later consumer skill only after real use. `gliclass` 0.1.21 needs `transformers>=5`. |

---

## 3. Upstream versions checked on 2026-10-17

- OpenWiki: `v0.5.2` 2026-09-15, `v0.6.0` 2026-09-23 (MCP search/read/link,
  linked wikis, parallel page workers), `v0.6.1`, `v0.7.0` 2026-10-02 (GitHub
  Copilot CLI integration), `v0.7.2` 2026-10-09.
- Ponytail: `v5.0.0` 2026-10-08 (rewritten rules: map callers, tests and
  config before writing; `/ponytail-review` reads touched code, not only the
  diff; `/ponytail-audit`), `v5.3.0`–`v5.3.2` 2026-10-16 (cost/token band in
  Claude Code).
- Context Mode: pinned `1.0.169` (`shared/hooks/scripts/context-mode-dispatch.sh:11`).

---

## 4. Item status

### A. Planning, evaluation and code quality

| # | Item | Status | Evidence | Gap |
| --- | --- | --- | --- | --- |
| A1 | Independent behavioral tests | PARTIAL | `scripts/check_native_clients.py:93-123` (two opt-in planner workloads); `tests/fixtures/behavioral/requirement-review/`; `docs/2026-10-06-behavioral-pilot-evidence.md` | Pilot stopped (4/4 case runs `nonzero_client_exit`). Planner workloads score model self-reports. No runner for the review fixture. |
| A2 | Ponytail affected-code completeness | PARTIAL | `shared/third_party/ponytail/UPSTREAM.md:4-5` (v4.8.4); caller guidance `shared/skills/ponytail/SKILL.md:40-42`, coder `prompt.md:28`, planner `prompt.md:56` | No reviewer or `ponytail-review` step checks callers, tests, fixtures or config outside the diff. |
| A3 | Regression learning | PARTIAL | `shared/skills/learn/SKILL.md:33-42` (text-ships test only) | Never requires a new test before a skill or instruction change. |
| A4 | Spec-to-test traceability | UNVERIFIED | `shared/templates/plan-big.md` Requirement Map; reviewer `prompt.md:35-38` | No validator reads requirement IDs. |
| A5 | Spec consistency analysis | PARTIAL | `plan-decomposition/SKILL.md:140-153`; `requirements-spec.md:43-55` | No independent read-only check before implementation. |
| A6 | Risk-first spikes | UNVERIFIED | Planner `prompt.md:57-67`, `integration-gate-spike` skill | Text-ships only; used in practice, not enforced. |
| A7 | Test strategy first | VERIFIED | `scripts/validate_plan_frontmatter.py:587-647` (L1–L4); `verify.py` G1–G4; tests `test_missing_verification_block_fails_l1`, `test_run_verification_items_stops_at_first_failure` | Only the runnable `## Verification` block is checked. L1–L4 run at commit, not at approval (§5 D8). |
| A8 | Independent test-quality review | PARTIAL | `shared/review-profiles/tests.md:10-11,26` | Skips/xfail never mentioned; no gate requires the `tests` profile. |
| A9 | Minimal reviewable changes | PARTIAL | `plan-decomposition/SKILL.md:44-53` | Nothing automated. |
| A10 | Plan contracts | PARTIAL | `plan-big.md` sections; planner `prompt.md:76,88-92,100` | No "permitted discretion" or escalation-criteria section. |
| A11 | Evidence-first review | UNVERIFIED | Reviewer `prompt.md:8-9,35-41,50`; text-ships tests | Gate ignores `WARN` and `### Open Requests` (§5 D2). |
| A12 | Bounded experiments skill | PARTIAL | Planner `prompt.md:59-63`; `prompt-lab/SKILL.md:62-74` | No reusable keep/revert experiment skill. |
| A13 | Unnecessary specialist calls | PARTIAL | `workflow.instructions.md:21` (any multi-file diff is high-risk); `_lib-frontmatter.sh:790` (`-gt 1`) | A two-file docs change still gets the full lifecycle and a required Ponytail review. |
| A14 | Decision maps for handoffs | PARTIAL | Orchestrator `prompt.md:126,170`; `agent-reporting.instructions.md:58` | No dedicated artifact. |
| A15 | GitHub Spec Kit | REJECTED | Exploration README `:104-105,182` | Two ideas borrowed. |

### B. Context, retrieval and knowledge

| # | Item | Status | Evidence | Gap |
| --- | --- | --- | --- | --- |
| B1 | Semble | VERIFIED (wiring) | `.mcp.json`, `shared/mcp/servers.json:3-6`; `validate_targets.py:2882`; `test_mcp_server_parity_errors_fail_independently` | Usefulness is not measured. |
| B2 | Context Mode four-tool surface | PARTIAL | Filter `shared/hooks/scripts/context-mode-mcp-filter.mjs:7`; `test_context_mode_tool_surface_is_exactly_four_tools_everywhere` | Root Claude/Copilot adapters unfiltered; hook output recommends blocked tools (§5 D1). |
| B3 | Stale-source recovery (delete/rename) | PARTIAL | `.claude/plans/orchestrator-plan-execution-defaults.md:94-103` | Deleted or renamed sources are not handled. |
| B4 | Context7 | VERIFIED (generated MCP config) | `shared/mcp/servers.json:14-17`; `dist/multi-agent/.mcp.json` | Claude subagents are not granted it (§5 D6); root Claude/Copilot/Codex adapters lack it. |
| B5 | OpenWiki | PARTIAL | Pinned `0.5.2` (see §2); `shared/skills/knowledge-refresh/SKILL.md` | Upgrade to `0.7.x` needs the upgrade rule restated first. |
| B6 | Wiki/MEMORY split rule | UNVERIFIED | `shared/policies/workspace.instructions.md:42-61`; `shared/MEMORY.md:20-25` | No check. |
| B7 | Onboard progressive disclosure | UNVERIFIED | `shared/skills/onboard/SKILL.md:30-49` | Filename listing, no curated index, no test. |
| B8 | Knowledge staleness | PARTIAL | `verify.py:2525-2565` (stale-claims section required); `validate_docs_parity` | Checks presence, not correctness. |
| B9 | Serena | ABSENT | Named only as out of scope in three plans | Never evaluated. |
| B10 | ast-grep | ABSENT | Same three plans | Never evaluated. |
| B11 | Graphify | REJECTED | `.claude/plans/graphify-structural-code-intelligence.md` (cancelled, NO-GO) | 1/3 useful answers. |
| B12 | MEMORY.md size | PLANNED | 100,425 bytes, 1,445 lines, 312 entries vs 49,455 bytes, 171 entries on 2026-09-03 | Exploration `2026-09-03_memory-md-size-reduction` still waits for a user decision. |

### C/E. Providers, consumers, model routing

| # | Item | Status | Evidence | Gap |
| --- | --- | --- | --- | --- |
| C1 | Native acceptance matrix | PARTIAL | `scripts/check_native_clients.py:157` (`claude`, `codex` only); `docs/native-client-acceptance.md` | No Copilot or Antigravity probe; skills/tools not probed. |
| C2 | Antigravity delegation and hooks | UNVERIFIED | `docs/runtime-checks.md:300-330`; offline bridge tests `tests/test_hook_gates.py:3009-3213` | Native PreToolUse hard-deny never observed. |
| C3 | Codex Sol/Terra/Luna routing | VERIFIED (structure) | `validate_targets.py:99-120`; `test_codex_routing_contract_rejects_aliases_and_root_pins` | No cost/quality measurement; new coders never observed running. |
| C4 | Cheap-coder benchmark | REJECTED (deferred) | `.claude/plans/codex-luna-coder-routing.md:65` | Not ruled out permanently. |
| C5 | Claude effort calibration | PARTIAL | `docs/2026-08-09-planner-reliability-calibration.md` (xhigh only) | No paired comparison. |
| C6 | Token/context efficiency | PARTIAL | Workload fields often `null` | Not measured. |
| C7 | Harness fingerprint | PARTIAL | Codex role matrix `check_native_clients.py:126-146` | No skills/hooks/MCP record. |
| C8 | JSONL traces | REJECTED (deferred) | `state-sync-recovery-and-plan-cancellation.md:165` | Lifecycle log only. |
| C9 | Deep-audit expansion | PARTIAL | `shared/skills/deep-audit/SKILL.md:19-93` | No shadowed-instruction, unprotected-path or duplicate-tool check. |
| C10 | Consumer lifecycle tests | VERIFIED (sidecar) / PARTIAL (full) | `tests/test_sidecar_workflow_scenario.py:143`, `tests/test_sidecar_update.py` | Full-install uninstall is refused (`scripts/install_bootstrap.py:1714-1718`, re-checked). |
| C11 | Receipt provenance | VERIFIED | `verify.py:133-141,253-267`; `test_control_plane_provenance_binds_runtime_and_active_plans` | Bound to the consumer revision, not the bootstrap's. |
| C12 | Minimal sidecar | VERIFIED | `tests/test_sidecar_install.py:249-264` | No separate `update` verb. |
| C13 | Sidecar reconciliation | VERIFIED | `tests/test_sidecar_update.py:1062+` | — |
| C14 | Unified doctor | PARTIAL | `scripts/check_runtime.py` (authoring only) | Not combined, not shipped. |
| C15 | Versioned config | PARTIAL | Receipt v4, sidecar manifest v2 | `.claude/bootstrap-ownership.env` unversioned. |
| C16 | Pi / full harness | ABSENT | ADR `plans/adr-001-multi-target-lcd.md` (native adapters) | No decision either way. |

### D. Security, skills and utilities

| # | Item | Status | Evidence | Gap |
| --- | --- | --- | --- | --- |
| D-1 | Four skill correctness bugs | UNVERIFIED (fixed) | Fixed in `cffc351` (PR #38) and `6d2d859` (PR #39); text tests in `tests/test_validate_targets.py:2868,2885,2939` | `text-to-sql-safety` has no test. |
| D-2 | Skill linting | VERIFIED | `validate_targets.py:8257,7545,7625`; tests `:2584-2829` | Trigger breadth not checked (hard lint rejected). |
| D-3 | Broad triggers / outdated refs | PARTIAL | R-SKILL-03 tested | Trigger lint rejected on purpose. |
| D-4 | Test masking | PARTIAL | L3 `validate_plan_frontmatter.py:627`; exit-5 handling `test_pytest_exit_5_with_uncollected_test_files_is_unverified` | Skips/xfail never fail; shipped skills not scanned (§5 D7). |
| D-5 | Hook false positives on assignments | VERIFIED | `tests/test_hook_gates.py:2078,2091,2099,2304-2414` | See §6 on interpreter commands. |
| D-6 | Receipt invalidation | PARTIAL | `verify.py:1698-1717`, VFY-FRESH-001/002, commit-gate `tree_sha` check `:2060-2066` | Tests weakened before the receipt are not detected (§5 D5). |
| D-7 | Monty sandbox | ABSENT | 0 hits | — |
| D-8 | Humanize provenance | UNVERIFIED | Pin enforced `validate_targets.py:464-486,802-830` | Identifier-preservation rule has only a required-text check. |
| D-9 | harness-score / stable IDs | PARTIAL | `verify.py:58-66` `CHECK_IDS`, `--format json` | `validate_targets.py` errors mostly have no IDs. |
| D-10 | `caveman-compress` backup defect | PLANNED | `shared/skills/caveman-compress/SKILL.md:64-65,88` still writes `<stem>.original.md` beside the target | Still present; only in exploration `2026-09-03_memory-md-size-reduction` §6. |

---

## 5. Defects found

| ID | Defect | Check | Evidence |
| --- | --- | --- | --- |
| D1 | **Context Mode is unguarded in this repo and its hook recommends blocked tools.** Tracked root `.mcp.json` and `.vscode/mcp.json` start `context-mode` directly; root `.codex/config.toml` and installed `.agents/mcp_config.json` use the guarded dispatcher. The validator checks only the root Codex config (`scripts/validate_targets.py:3007-3024`). Separately, `context-mode-dispatch.sh:328-330` forwards the upstream `context-mode hook` output unchanged. | Re-checked, and the hook was run live at the pinned `1.0.169` with target `claude-code` | `pretooluse` for Bash → a tip naming `ctx_batch_execute` and `ctx_execute`. `pretooluse` for WebFetch → `permissionDecision: deny`, redirecting to `ctx_fetch_and_index`, a tool the filter blocks, so a guarded consumer loses WebFetch. `pretooluse` for Bash `curl -s https://example.com` → also `deny`, redirecting to `ctx_execute`. `sessionstart` → 4,773 bytes naming `ctx_batch_execute`, `ctx_execute`, `ctx_execute_file`, `ctx_fetch_and_index`, `ctx_search`. All names use the plugin prefix `mcp__plugin_context-mode_context-mode__`. In this session the main agent used `ctx_batch_execute` and `ctx_fetch_and_index`, which `tool-routing.instructions.md:15` forbids. |
| D1b | The user-level Claude Code plugin `context-mode@context-mode` is enabled in `~/.claude/settings.json`. It brings its own unfiltered server and hooks. | Re-checked | Outside repository control; user decision. |
| D2 | **A `WARN` review passes the commit gate as clean.** The reviewer answers `WARN` while a request is open and keeps open requests out of the findings JSON, but `shared/scripts/record_findings.py` records no gate result and `verify.py` never reads one; `quality-and-testing.instructions.md:121` calls `[]` "passed clean". | Re-checked | `record_findings.py:189-260`; `verify.py:2229-2390` |
| D3 | **Hook-bearing configs not protected.** `protect-files.py` `HOOK_CONFIGS` (`:15-20`) and prefixes (`:290-299`) cover `.claude/settings.json`, `.codex/*`, `.github/hooks/*`, `.claude/hooks/*`, but not `.claude/settings.local.json` (Claude local settings can add hooks or disable them) or `.agents/hooks.json` (Antigravity's only hook config). `settings.local.json` is also excluded from the runtime fingerprint (`verify.py:142-153`). | Re-checked | Copilot workspace settings not yet assessed. |
| D4 | **No test covers the blocking path of the required Ponytail review.** Every call in `tests/test_verify.py` passes `require_ponytail=False`; `tests/test_hook_gates.py` and `tests/test_lifecycle_hooks.py` never mention Ponytail. | Re-checked | `_lib-frontmatter.sh:771-800`, `verify.py:2388` |
| D5 | **`tracked_state_hash` is written but never compared.** It is only required to be non-empty (`verify.py:296-306`, written at `:1707`). Not a hole at commit time: with an `exact` head relation the commit gate compares the closeout `tree_sha` with `git write-tree` (`verify.py:2060-2066`), so any tracked change after closeout, docs included, already blocks. The real remaining gap: tests or evaluators weakened *before* the receipt; no gate requires the `tests` profile. | Re-checked | — |
| D6 | **Claude subagents cannot use Context7.** `CLAUDE_TOOL_MAP["search"]` (`scripts/generate_targets.py:104`) grants `mcp__semble` and `mcp__context-mode` only. Copilot gets `context7/*` (`:119`); Antigravity agents use `inheritMcp: true`. A 2026-10-17 probe of the `reviewer` subagent listed every `mcp__semble__*` and `mcp__context-mode__*` tool, so a server-level grant works for project servers in a session that started with them. | Re-checked, probe | Also shows the reviewer had all 11 unfiltered Context Mode tools here. |
| D7 | **Shipped commands that hide failures.** `shared/skills/run-tests/SKILL.md:66` and `shared/skills/add-dependency/SKILL.md:47` run `uv run pytest tests/ -W default::DeprecationWarning 2>&1 \| grep -i deprecat \|\| echo "Clean"`, which prints "Clean" when pytest fails. No other shipped line matches. L3 scans plan Verification blocks only. | Re-checked | — |
| D8 | **Plan checks L1–L4 run at commit, not at plan approval.** `enforce-branch-state.sh` checks plan type and status only; `assert_plan_frontmatter` is called only from `assert_commit_invariants` (`_lib-frontmatter.sh:1360`). `workflow.instructions.md:386` says "At plan approval". | Re-checked | — |
| D9 | **`shared/schemas/agent.schema.json` is stale and unused.** Its `targets` enum lacks `google-antigravity`; no script reads it; it is not shipped in `dist/`. | Re-checked | Only reference: `plans/plan-agent-model-effort-tiers.md:197`. |

---

### Corrections from the devil's advocate review (same day)

An independent read-only review of the `gate-repair` plan (Opus,
extra-high effort) re-checked these rows against the code:

- **D4 was wrong as written.** The required-Ponytail blocking path *is*
  tested through the installed commit-msg and pre-push hooks in
  `scripts/validate_targets.py:6098-6112` and `:6580-6600`. Only a unit test
  in `tests/test_verify.py` is missing. (The original search covered
  `tests/` only.)
- **D1 is wider.** Upstream `context-mode hook` can also return `allow` with
  a rewritten tool input (`updatedInput`, for example a changed subagent
  prompt): upstream `hooks/core/formatters.mjs:23-77`. The dispatcher
  `exec`s upstream, so upstream's exit status reaches the client too.
- **D3 is wider.** `.mcp.json`, `.vscode/mcp.json`, and
  `.agents/mcp_config.json` launch server commands but are not protected
  either. The nested ai-state repository here still tracks
  `settings.local.json` (commits `3cb99a2`, `db082f3`, `8f51c51`) although
  `.claude/.gitignore` lists it.
- **D2 detail.** Push gates re-check the last completed phase's findings with
  the strict completion rule (`_lib-frontmatter.sh:1541`, `:1756`). The
  historical chain checks only artifact hashes, not `report_errors`.
- **Antigravity protect decision.** `protect-files.py:1427` itself denies for
  `google-antigravity`; the bridge's ask-to-deny conversion is a backstop.

## 6. Reported but not defects, or out of scope

- `protect-files.sh` denies `python3 -c "...open(path)..."` and commands with
  unresolved variables that name a protected path ("could not determine
  whether the command may modify them"). Reproduced twice while planning.
  This is the documented fail-closed design for interpreter code. It does
  push agents to switch tools (MEMORY `[LEARN:quality]` on guards that
  people route around); a narrower classifier is a separate decision.
- Lane wording: "no line-count thresholds" vs "multi-file is high-risk" is
  a file-count risk category, not a line count. Not a contradiction.
- Ponytail "mandatory" (`shared/skills/ponytail/SKILL.md:25`) vs "optional
  for low-complexity work" (`workspace.instructions.md:138-142`): a wording
  conflict for the final stale-claims audit of `gate-repair`.
- Stale AI-state statuses: big plans `codex-gpt-5.6-model-tiering` and
  `preserve-consumer-memory` (and their phase files) still say
  `in-progress` though merged as PR #7 and PR #8. The pilot big plan still
  shows Phase D unticked. The 2026-10-02 engineering exploration README
  still calls the pilot a deferred proposal.
- MEMORY `[LEARN:planning]` (about line 1167) says subagent tool lists
  exclude project MCP servers. The D6 probe contradicts this for servers
  present at session start; reconcile the entry in the final audit.

---

## 7. Recommended order

1. `gate-repair` big plan for D1–D9 (requested by the user on 2026-10-17),
   with capability parity across Claude Code, Codex, GitHub Copilot and
   Antigravity, in that priority order.
2. `MEMORY.md` split (exploration `2026-09-03_memory-md-size-reduction`).
3. Ponytail 5 adoption (affected-caller rules), evaluated before adoption.
4. Behavioral evaluation retry, only with error capture for native runs.

Leave Monty, Serena, ast-grep, GLiClass/GLiNER classifiers and trace logs
alone until a real failure calls for them.
