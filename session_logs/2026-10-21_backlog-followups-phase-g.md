# Session: Backlog follow-ups — Phase G, knowledge refresh

**Date:** 2026-10-21
**Plan:** .claude/plans/2026-10-20_phase-G-backlog-followups-knowledge-refresh.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** COMPLETED

## Goal

Run the final stale-claims audit across every live-advice surface (BF-G1),
refresh the OpenWiki knowledge layer with the `0.7.2` server, and confirm
the plan's boundaries held (BF-G2).

## Task Tracking

- [x] PRE-FLIGHT: Phase F committed (`f05c3b3`) and pushed; Phase G is the
  current and last phase. No planner.
- [x] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT — repeat until verification and review pass
- [x] COMMIT
- [x] PUSH

## Work Log

- **Start** - Asked the user to reconnect the `openwiki` MCP server with
  `/mcp`: this session's server started on `0.5.2` before the orchestrator's
  upgrade to `0.7.2`. Started the read-only stale-claims sweep with a
  research agent meanwhile (report in the session scratch folder,
  `phase-g/audit.md`).
- **Step 1** - Audit fixes applied (see the next section). Regenerated and
  refreshed the self-install before the refresh, so the verifier's
  provenance check matched the edited sources.
- **Step 2, refresh** - After `/mcp` reconnected the server on `0.7.2`, ran
  one managed `update` run (`d1f285b5-4468-4e5a-89b6-d8acb60ab1fc`): 8
  planned pages (agents and skills, hooks and guardrails, layout,
  deterministic verification, state sync, install and ownership,
  lifecycle, quickstart, in that queue order), each with its claims
  revised or added through `openwiki_submit_page`. `openwiki_finish`
  returned `complete`. One submission was rejected for evidence past the
  end of a file (`#L184-L260` on a 259-line test) and passed with
  `#L184-L259`. All six required corrections landed: no generated page
  restates the parity table, and the hooks page lists `.claude/hooks` in
  `CONTROL_PLANE_DIRS`; the commit-gate sentence is scoped to phase
  completion; the quickstart "refresh this wiki" row names
  `openwiki-guard.sh`; the Phase B consumer-state and `setup` text; the
  Phase D protected set and `sandbox_mode` text; the Phase E Ponytail
  text.
- **Step 2, link stamps** - The `0.7.2` finalizer
  (`dist/agent/wiki-link-validator.js`) stamped 63 root-absolute wiki
  links (`/openwiki/...`) in 10 pages with `<!-- openwiki: broken internal
  link ... -->` comments. Its host prompt asks for page-relative links,
  and each pass strips old stamps before validating. Rather than
  hand-edit, ran a second `update` run
  (`0aaf238f-257e-4752-baa9-553be66988af`) scoped to those 10 pages with
  a link-only purpose: each page's links were rewritten relative to its
  folder and the stamps removed, with no claim changes. `openwiki_finish`
  returned `complete`; no stamp or root-absolute link remains, `AGENTS.md`
  and `CLAUDE.md` are unchanged, and `openwiki/.run.json` is gone.
- **Verify** - `generate_targets.py --all`, self-install refresh,
  `check_runtime.py` (all PASS), and `verify.py phase` PASS (3270 passed,
  1 skipped).

## Stale-claims surfaces checked

Audit by a read-only research agent (report in the session scratch folder,
`phase-g/audit.md`), fixes applied by a documenter (outer repository) and
the orchestrator (nested `.claude` state). Every live-advice surface and
its outcome:

- Root `CLAUDE.md`, `AGENTS.md`, `README.md`: no stale claim.
- `docs/architecture.md`: fixed K2 (the manual `openwiki-guard.sh post`
  restore is the user's, because the guard denies an agent command naming
  the hook script); added that no test checks whether models follow the
  merged Ponytail rules. Its scope passage near line 397 is not an
  exhaustive protected-set list, so it was left unchanged.
- `docs/runtime-checks.md`: fixed C2 (only running a checkpoint script, not
  reading it, is denied); the path-coverage sentence now names agent
  definition paths and `*.code-workspace` files.
- `docs/smoke-tests.md`, `docs/native-client-acceptance.md`, and the
  undated sections of `docs/sidecar-provider-contract.md`: no stale claim
  (`docs/smoke-tests.md` already lists agent paths and workspace files).
- `docs/target-mapping.md`: fixed T1 (the finished decision-6 behavior moved
  from "Recorded follow-ups" into the backlog-followups parity paragraph;
  one short follow-up bullet on newly denied mixed commands remains) and T2
  (new follow-up: the Codex re-probe of the OpenWiki guard was not run).
  The three carried follow-ups stay listed (Copilot SDK/CLI key casing,
  `create_and_run_task`, the five-profile rule); Phase D's finished items
  are gone; Phase E was not cancelled, so A2 is not added.
- Dated records left unchanged: `docs/plan-deterministic-commit-gate.md`,
  `docs/2026-*`, `docs/evidence/**`, closed plans, closed session logs,
  dated explorations.
- `shared/policies/workflow.instructions.md`: fixed W1 (secret files denied
  everywhere; hook, server, agent, and workspace configs ask on Claude Code
  and Copilot and are denied on Codex and Antigravity) and K3 (the restore
  must be run by hand); CLOSEOUT step 4 now says to pass findings that name
  a protected path as `--findings-json <file>` written with the Write tool.
- The other nine policy files: no stale claim (OpenWiki version, upgrade
  rule, and `init` wording already matched Phase F).
- `shared/skills/knowledge-refresh/SKILL.md`: fixed K1 (the HIGH finding:
  the skill told the agent to run a restore command the guard denies on
  every client, both now and on `dev`). `shared/skills/commit/SKILL.md`:
  fixed C1.
- The other 53 skills (including `ponytail`, `ponytail-review`,
  `caveman-compress`, `onboard`, `setup-project`, `create-feature`): no
  stale claim.
- `shared/templates` (6), `shared/agents` (8), `shared/review-profiles`
  (10): no stale claim.
- State READMEs (`.claude/plans`, `session_logs`, `quality_reports` —
  byte-identical to their `shared/` sources — `.claude/explorations`, the
  four sidecar state READMEs), `shared/MEMORY.md`,
  `shared/third_party/ponytail/UPSTREAM.md`: no stale claim.
- `openwiki/INSTRUCTIONS.md` (human-authored brief): fixed B1 (the sidecar
  has two profiles, `skills` and `workflow`).
- `.claude/instructions/project-context.instructions.md`: fixed S1 (two
  parity tables), S2 (OpenWiki `0.7.2`), S3 (Ponytail partially merged from
  `v5.3.2`), S4 (status paragraph names this plan and the new pins), S5
  (the installer fills each generated `**Project:**` line).
- `.claude/MEMORY.md`: corrected in place M1 (CLOSEOUT step 2 sets
  `status: complete` before findings and receipts), M2 (current
  `state-sync.sh` names: `reconcile_committed_state`, `cmd_publish`), M3
  (OpenWiki `0.7.2` queue order and evidence rule, checked in the package
  source), M4 (`sandbox_mode` no longer written), M5 (`git -C .claude
  ls-files -s` for probes), M6 (running, not reading, a hook script is
  refused), M7 (the `0.7.2` `noop` conditions of `openwiki_begin`), M8 (cite
  the Ponytail pin check by name). Both Ponytail pin entries had already
  been corrected in Phase E. Every backticked identifier in `MEMORY.md` was
  checked against source; only `commit_and_reconcile` was missing.
- Generated `openwiki/**` pages: left to the managed refresh (step 2).

## Requirement Evidence (BF-A1 to BF-G2)

Phase commits on `backlog-followups_implementation`: A `f52a867`, B
`06eb8e0`, C `69bdb64`, D `86756e0`, E `02e22de`, F `f05c3b3`, G this
commit. Each phase's own session log carries its detailed evidence.

| ID | Outcome | Evidence |
| --- | --- | --- |
| BF-A1 | Done | `f52a867`; `2026-10-20_backlog-followups-phase-a.md`; `validate_plan_frontmatter.py` |
| BF-A2 | Done | `f52a867`; `validate_targets.py` |
| BF-A3 | Done | `f52a867`; grep items in the Phase A log |
| BF-A4 | Done | `f52a867`; three skills; `validate_targets.py` install run |
| BF-A5 | Done | `f52a867`; new `tests/test_verify.py` cases |
| BF-A6 | Done | 2026-09-21 exploration status line; item 2 closed here (quickstart row names `openwiki-guard.sh`) |
| BF-A7 | Done | `f52a867`; `sha256sum -c` item; `validate_targets.py` pin |
| BF-B1 | Done | `06eb8e0`; `tests/test_install_bootstrap.py`, `tests/test_state_sync.py` |
| BF-B2 | Done | `06eb8e0`; `tests/test_state_sync.py` |
| BF-C1 | Dropped (scope change, user decision 2026-10-20) | Phase C small plan scope-change record |
| BF-C2 | Done as evidence (6.11%, below the 25% stop) | `.claude/explorations/2026-09-03_memory-md-size-reduction/2026-10-20_classification.tsv` |
| BF-C3 | Dropped with BF-C1 | Phase C scope-change record |
| BF-C4 | Done | `69bdb64`; `tests/test_caveman_compress_detect.py` |
| BF-C5 | Done | 2026-09-03 exploration status and outcome line |
| BF-D1 to BF-D5 | Done | `86756e0`; `tests/test_hook_gates.py`, `tests/test_protect_files_scoping.py`; generated battery with 0 defects; `docs/target-mapping.md` parity table |
| BF-E1 | Done: PARTIAL ADOPT | `.claude/explorations/2026-10-20_ponytail-5-evaluation/evidence.md` |
| BF-E2 | Not applicable (no NO-GO) | same evidence file |
| BF-E3 to BF-E7 | Done | `02e22de`; guidance rows; hash pins; anchor test; `validate_targets.py` |
| BF-F1 to BF-F7 | Done | `f05c3b3`; `2026-10-21_backlog-followups-phase-f.md` capture table; `tests/test_openwiki_cli_smoke.py`, `tests/test_openwiki_guard.py`; receipts at `0.7.2` |
| BF-G1 | Done | "Stale-claims surfaces checked" above; OpenWiki runs `d1f285b5-...` and `0aaf238f-...` both `complete`; `test ! -e openwiki/.run.json` |
| BF-G2 | Held | Phase G changes no hook, script, test, or `verify.py`; Context Mode pin `1.0.169` (`context-mode-dispatch.sh:11`); `git diff --name-only dev..HEAD` lists no `docs/2026-*` or `docs/evidence/**`; the nested diff since Phase A changes only the Phase C exploration status and new evidence files; reviewer confirmed |

## Review

- Round 1 (fresh reviewer, profiles documentation, code, architecture,
  security, tests, ponytail): Gate Result PASS; 0 critical, 0 major, 1
  minor. The minor finding: the repository-scope sentence in
  `docs/runtime-checks.md` (and the same sentence in
  `docs/architecture.md` and `docs/smoke-tests.md`) did not name agent
  definition paths and workspace files. Fixed in all three, keeping the
  cited wiki line ranges in place.
- Also acted on two informational notes: `knowledge-refresh` now says the
  `post` output is read once the user has run it, and
  `openwiki/INSTRUCTIONS.md` tells page authors to write relative links.
  Regenerated, self-installed, `validate_targets.py` PASS, `verify.py
  phase` PASS (3270 passed, 1 skipped).
- Round 2 (same reviewer, same six profiles, the round-two edits only):
  Gate Result PASS; 0 findings; the round-one minor is resolved and no
  cited wiki claim range moved. Recorded gate: PASS, no open request.

## [LEARN] Entries

- [LEARN:tooling] OpenWiki `0.7.2` stamps root-absolute wiki links; fix
  them with a link-only `update` run scoped to the stamped pages, never by
  hand (saved to `MEMORY.md`).
- [LEARN:tooling] Extended the existing `protect-files.sh` entry: since the
  guard fails closed, a read-only command whose text names a protected
  folder can be denied; search with a scratch Python script.

## Verification

Optional items:

- optional 1: PASS - OpenWiki completion: run `d1f285b5-4468-4e5a-89b6-d8acb60ab1fc`, finish
  `complete`, 8 pages (`architecture/agents-and-skills.md`,
  `architecture/hooks-and-guardrails.md`,
  `architecture/source-generated-consumer-layout.md`,
  `operations/deterministic-verification.md`,
  `operations/git-backed-ai-state-sync.md`,
  `operations/install-ownership-and-runtime-checks.md`,
  `workflows/lifecycle-and-task-lanes.md`, `quickstart.md`). Run
  `0aaf238f-257e-4752-baa9-553be66988af`, finish `complete`, 10 pages
  (the same 8 plus `operations/context-mode-dispatcher.md` and
  `operations/sidecar-overlay.md`), links only. Every page diff was read;
  the reviewer checked every relative link target.

Required items (summary lines from `verify.py closeout`):

```text
PASS        0.3s  uv run python scripts/generate_targets.py --all
PASS       43.7s  uv run python scripts/validate_targets.py
PASS        0.9s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS        0.0s  test ! -e openwiki/.run.json
PASS        0.2s  uv run python .claude/scripts/verify.py fast --format json
closeout: PASS
VFY-FRESH-001: PASS - phase evidence matches relevant state
VFY-FRESH-002: PASS - phase evidence matches governing control-plane provenance
VFY-RECEIPT-001: PASS - reused successful phase receipt
```

Findings recorded: 1 finding (0 critical, 0 major, 1 minor, fixed);
`ponytail_reviewed=true`; `gate_result=PASS`
(`.claude/quality_reports/findings-2026-10-20_phase-G-backlog-followups-knowledge-refresh.json`).

## Open Questions / Next Steps

- After closeout, the big plan is complete. Opening a pull request from
  `backlog-followups_implementation` to `dev` is the user's decision.
- Follow-up (not in this plan's scope, executable text): the manual
  OpenWiki restore command is printed as the fix by
  `docs/runtime-checks.md` (troubleshooting table), `verify.py`, and
  `openwiki-guard.py`. It is right for a person, but an agent cannot run
  it. A later change could add "ask the user to run" to those messages.
- Follow-up: generated pages carry some long sentences (for example the
  `protect-files` bullet in `openwiki/architecture/hooks-and-guardrails.md`).
  Worth a style pass at the next managed refresh.
