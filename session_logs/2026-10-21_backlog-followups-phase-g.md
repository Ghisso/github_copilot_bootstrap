# Session: Backlog follow-ups — Phase G, knowledge refresh

**Date:** 2026-10-21
**Plan:** .claude/plans/2026-10-20_phase-G-backlog-followups-knowledge-refresh.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** IN-PROGRESS

## Goal

Run the final stale-claims audit across every live-advice surface (BF-G1),
refresh the OpenWiki knowledge layer with the `0.7.2` server, and confirm
the plan's boundaries held (BF-G2).

## Task Tracking

- [x] PRE-FLIGHT: Phase F committed (`f05c3b3`) and pushed; Phase G is the
  current and last phase. No planner.
- [ ] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT — repeat until verification and review pass
- [ ] COMMIT
- [ ] PUSH

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

## [LEARN] Entries

To be written at closeout.

## Verification

To be written at closeout.

## Open Questions / Next Steps

- After closeout, the big plan is complete. Opening a pull request from
  `backlog-followups_implementation` to `dev` is the user's decision.
