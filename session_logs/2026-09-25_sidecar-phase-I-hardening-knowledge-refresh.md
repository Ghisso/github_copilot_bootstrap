# Session: Sidecar Phase I — hardening knowledge refresh

**Date:** 2026-09-26
**Plan:** `.claude/plans/2026-09-25_phase-I-sidecar-hardening-knowledge-refresh.md`
**Status:** IN-PROGRESS

## Goal

The big plan's final knowledge-refresh phase after the reopen (Decision 21):
refresh OpenWiki against Phases F-H, then run the standing final-phase
documentation, memory, and LEARN audit.

## Work Log

- Phase I activated by the Phase H completion commit `f7d9af4` (pushed).
- Material-impact check: Phases F-H changed the plan validator and the
  workflow text (F), the sidecar planner and ownership rules (G), and
  preflight, bytes-safety, sources, `--uninstall`, and the docs (H). This
  phase's scope already names these topics. No change.
- Owner for steps 1-2: only the main session has the `openwiki` MCP tools,
  so the orchestrator runs the refresh itself (MEMORY LEARN from Phase E).
  The stale-claims audit (steps 3-4) goes to `documenter`.
- Before the refresh, the orchestrator added team precedence, the
  preserved-copy folder, and `--uninstall` to the sidecar coverage item in
  the human-authored brief `openwiki/INSTRUCTIONS.md`.
- Step 1, refresh: `openwiki_begin` (`mode: "update"`) returned run
  `648c59de-72d9-46f6-a234-48b7bcf44eaa` in planning, with 21 changed paths
  since `faf1b7b` and 23 stale or unresolved claims on 6 pages. Right after
  it, `git status --porcelain -- AGENTS.md CLAUDE.md` was empty (the guard
  restored them). The other four pages mention none of the changed topics.
  The plan covered 6 pages:
  - `source-generated-consumer-layout`: the exact sidecar source set shared
    by the validator and the installer;
  - `git-backed-ai-state-sync`: uninstall also skips state sync;
  - `install-ownership-and-runtime-checks`: the environment scrub,
    submodule and gitlink rules, Git-error abort, `LC_ALL=C`,
    `require_source_exists`, `require_full_source_complete`, and
    `--uninstall` dispatch;
  - `sidecar-overlay`: rewritten for preflight, index ownership, team
    precedence, preserved copies, block parsing, the folder gate,
    bytes-safety, uninstall, and the removal of manual removal steps;
  - `lifecycle-and-task-lanes`: the knowledge-refresh exemption and the
    reopening procedure;
  - `quickstart`: routing rows for uninstall, preserved copies, and
    reopening.
  Every stale or unresolved claim was revised with current evidence
  (including the two known stale claims, `229e75d4` and `e46454b4`). Two
  current claims whose line ranges had moved were revised too, and new
  claims were added for the new behavior. `openwiki_finish` returned
  `complete`, `openwiki/.run.json` is absent, and `.last-update.json`
  records `f7d9af4`.
- Step 2, diff review: 16 OpenWiki files changed (6 pages, their claim
  files, the manifest and index, and the brief). No page was hand-edited
  outside the page loop.
- Orchestrator notes for the audit, found while researching pages:
  - `README.md` around line 627 still says the installer proves paths
    ignored "before writing anything"; it should say before any sidecar
    file is written.
  - The docstring of `_sidecar_source_violations`
    (`scripts/sidecar_overlay.py:1676-1681`) still describes the old,
    weaker check.
  - The linked-worktree refusal message in `detect_install_mode` gives the
    old reason ("its own Git directory, separate from the main worktree's
    shared one").
- Steps 3-4, audit by `documenter`: `README.md` and the
  `_sidecar_source_violations` docstring were corrected, every other
  surface is current, and no MEMORY entry needs correcting (full list under
  "Stale-claims surfaces checked").
- A code correction the audit exposed: the `--mode sidecar`
  linked-worktree refusal in `detect_install_mode` now gives the real
  reason (Decision 15: the shared `info/exclude` versus the per-worktree
  manifest). `test_detect_mode_sidecar_mode_aborts_in_linked_worktree`
  asserts the new wording. `coder` results: 94 installer tests pass, and
  ruff and mypy pass. One run hit the conftest leak guard on the live
  `.claude/session_logs/hooks-errors.log`, which the session's own hooks
  can write to while tests run; the rerun passed.
- VERIFY and REVIEW (full profile set) started.
- `verify.py phase` (run in the background) reported 2097 passed and 1
  error. The error was the conftest leak guard on the live
  `.claude/session_logs/hooks-errors.log`: this session's own
  `stop-session-log-check` hook appended a warning at 2026-09-26T00:22:23Z,
  while the test session was running, as the orchestrator's turn ended.
  This is environmental, not a code failure. `verify.py phase` is rerun in
  the foreground after the reviewer finishes, so no hook writes during the
  test run.
- REVIEW (`documentation`, `code`, `architecture`, `security`, `tests`,
  `ponytail`): PASS with no findings. Every refreshed page was
  cross-checked against the code: the sidecar preflight order, the
  classification table, team precedence, write order and fault points; the
  install detection table and sequence; and the lifecycle exemption and
  reopening summary. The reviewer also checked the style contract (the one
  em-dash is inside a quoted exact string), claim evidence (including the
  two known stale claims), the message change and its test, the docstring,
  the README bullet, the absent `openwiki/.run.json`, and the unchanged
  root adapters.

## Stale-claims surfaces checked

Audit by `documenter` against the current code, plus the OpenWiki refresh
above. Dated records (archived plans, closed session logs, `docs/2026-*`,
and the two 2026-09-25 review reports) were left unchanged.

- `openwiki/**`: refreshed through OpenWiki's own tools (six pages; every
  stale or unresolved claim revised). Not hand-edited.
- `openwiki/INSTRUCTIONS.md` (the human-authored brief): corrected. The
  sidecar coverage item now names team precedence, the preserved-copy
  folder, and `--uninstall`.
- `README.md`: corrected. The "Limits" bullet said the installer proves
  every path ignored "before writing anything"; it now says "before any
  sidecar file is written". The rest of "Personal Sidecar Install"
  (uninstall, limits, behavior changes) matches the code.
- `scripts/sidecar_overlay.py` docstrings: corrected. The
  `_sidecar_source_violations` docstring described the old, weaker check;
  it now describes the exact-set comparison. The module docstring and the
  `compute_unit_hash` docstring already describe `os.fsencode`: unchanged.
- `scripts/install_bootstrap.py` module docstring, `--help` text, and
  `detect_install_mode`: unchanged apart from the `--mode sidecar`
  linked-worktree refusal message, which gave the old reason. That message
  is being corrected with a test (see Work Log).
- `scripts/update_consumers.py` docstring and `--help`: unchanged; they
  match the batch behavior.
- `docs/architecture.md`: unchanged; its exact-allowlist text matches
  `runtime_ownership.py`.
- `docs/target-mapping.md`: unchanged; uninstall, the preserved folder,
  and the taken-skill rules are current.
- `docs/runtime-checks.md`: unchanged; the knowledge-refresh row matches
  the validator's exemption.
- `docs/smoke-tests.md`: unchanged; no sidecar, uninstall, or reopening
  claims.
- `docs/sidecar-provider-contract.md`: unchanged; it is Phase A's dated
  native-run evidence and still matches the shipped skills and bridges.
- `shared/policies/workflow.instructions.md`: unchanged; the reopening
  procedure and the Termination text match the validator.
- Other `shared/policies/*`: unchanged; no sidecar, precedence, or
  reopening claims.
- `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md`,
  `shared/skills/plan-decomposition/SKILL.md`, and
  `shared/skills/knowledge-refresh/SKILL.md`: unchanged. They point to the
  canonical rules rather than restating them.
- `shared/templates/plan-big.md` and `shared/templates/plan-small.md`:
  unchanged; they point to the canonical rule.
- `shared/agents/documenter/prompt.md`, `shared/agents/orchestrator/prompt.md`,
  and `shared/agents/planner/prompt.md`: unchanged; they point to the
  canonical policy.
- `.claude/instructions/project-context.instructions.md`: unchanged; the
  installer and updater descriptions are current.
- Root guidance `AGENTS.md` and `CLAUDE.md`: unchanged; they have no claim
  that Phases F-H invalidated.
- `.claude/MEMORY.md`: unchanged by the audit. No entry describes the old
  collision loop, manual removal, `bootstrap_commit`, or "no commits"
  detection as current. The sidecar entries record native-run evidence and
  the Phase G and H lessons, and they are accurate.

## [LEARN] Entries

- [LEARN:verification] Run `verify.py phase`, and closeout step 4, in the
  foreground. A background run lets this session's own
  `stop-session-log-check` hook append to
  `.claude/session_logs/hooks-errors.log` when a turn ends mid-run. The
  conftest leak guard then reports one error on an otherwise passing suite.
  Added to MEMORY.
- [LEARN:documentation] An OpenWiki update does not flag a current claim
  whose evidence line range moved while the cited text still exists
  elsewhere. When rewriting a page, inspect its full claim set
  (`openwiki_inspect_page_claims`) and revise such claims too; two did so on
  the sidecar page.

## Verification

Required items are pasted at closeout step 4.

This plan has no `## Optional Verification` section.

## Documentation

Updated in this phase: six OpenWiki pages (through OpenWiki's tools) and
the brief `openwiki/INSTRUCTIONS.md`; the README "Limits" bullet; the
`_sidecar_source_violations` docstring; and the `--mode sidecar`
linked-worktree refusal message with its test. The standing final-phase
audit is recorded under `## Stale-claims surfaces checked`.

## Open Questions / Next Steps

- Every phase of the reopened big plan is complete after this commit, and
  the post-commit hook marks the big plan `complete`. A PR to `dev` is
  opened only when the user asks.
- Antigravity remains unverified for the sidecar; a later native run could
  add its rules-file bridge.
