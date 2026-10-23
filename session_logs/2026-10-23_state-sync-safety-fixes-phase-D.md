# Session: Knowledge refresh and stale-claims audit

**Date:** 2026-10-23
**Plan:** `.claude/plans/2026-10-23_phase-D-knowledge-refresh.md`
**Status:** COMPLETED

## Goal

Audit live guidance for claims that this plan or earlier work made stale, then refresh the enabled OpenWiki layer through OpenWiki's own MCP tools so its pages describe the new state-sync, restorer, and devcontainer behavior.

## Work Log

- Phase C committed as `ebc3bdd` and pushed; the post-commit hook advanced `current_phase` to this phase.
- `.claude/MEMORY.md`: corrected two older entries in place. The `[LEARN:security]` entry on automated recovery now reserves `--abort` for owned state and says never to force an operation out with `--quit`; the `[LEARN:recovery]` entry on `--quit` now limits it to the exact orphaned autostash shape. The `cmd_setup` `[LEARN:domain]` entry was already corrected in phase A.
- Documenter audit of every live-advice surface: no stale claim outside `openwiki/**`, so no file changed (per-surface results below).
- OpenWiki refresh through its own MCP tools: `openwiki_begin` (`mode: "update"`, run `74fb4fbe-50f2-45b8-970f-c676b77e44d1`) returned a planning run with eight claim issues on three pages; I submitted a three-page plan (`git-backed-ai-state-sync.md`, `hooks-and-guardrails.md`, `quickstart.md`), wrote each page, reconciled every flagged claim (revised with current evidence), added eleven new claims on the state-sync page, and `openwiki_finish` returned `complete`. On the hooks page I also corrected prose that said only Codex runs `state-sync.sh push` on `UserPromptSubmit` (`scripts/generate_targets.py` wires it for Claude Code too, with Claude `SessionEnd` push and `StopFailure` checkpoint). Afterwards root `AGENTS.md` and `CLAUDE.md` were unchanged and no `openwiki/.run.json` remained.
- Regenerated targets and refreshed the overlay; required checks on that tree: `validate_targets.py` and plan lint exit 0, `verify.py phase` PASS (4988 passed, 1 skipped).
- Review round 1 (seven profiles): gate WARN with one open request (the check results above) and three MINORs, all in the state-sync page's prose: "SessionStart on every host" (Antigravity wires no lifecycle hooks), "a stalled connection cannot hold the lock" (a connection still being opened has no stall limit), and "only `SIGKILL` can leave the copy" (a signal during the restore, other signals, and the restore's own keep rules also can). All three were fixed through a second OpenWiki update run (`3180def5-0833-4597-aca6-e1e92d68ec52`, one page job, `openwiki_finish` `complete`); the Stop bullet also gained GitHub Copilot's `state-sync.sh push`. Two claims were revised and one added; root adapters stayed unchanged and no `.run.json` remained.
- Review round 2: gate PASS, no findings, no open requests. Check rerun on the fixed tree: `validate_targets.py` and plan lint exit 0, `verify.py phase` PASS (4988 passed, 1 skipped).

## [LEARN] Entries

- [LEARN:documentation] A wiki page's prose can be wrong while its claims pass: the hooks page said only Codex runs `push` on `UserPromptSubmit`, and the matching claim was true but incomplete. During a refresh, read each assigned page's prose against the generator, not only the flagged claims.

## Stale-claims surfaces checked

- `CLAUDE.md`: clean.
- `AGENTS.md`: clean.
- `README.md`: clean (updated in phases A to C; re-checked for consistency).
- `docs/runtime-checks.md`: clean (updated in phases A to C).
- `docs/smoke-tests.md`: clean (updated in phases A to C).
- `docs/architecture.md`: clean; it only points to ADR-002 and the OpenWiki page.
- `docs/target-mapping.md`: clean.
- Other undated `docs/` files (`native-client-acceptance.md`, `sidecar-provider-contract.md`, `plan-deterministic-commit-gate.md`): clean.
- `shared/policies/`: clean (the session-start AI-state bullet was updated in phase B).
- `shared/skills/` (`commit`, `safe-consumer-bootstrap-refresh`, `knowledge-refresh`, `onboard`, `plan-decomposition`): clean.
- `shared/agents/`: clean.
- `shared/templates/`: clean.
- `shared/review-profiles/`: clean.
- `shared/sidecar/workflow/state/*/README.md`: clean.
- `shared/MEMORY.md`: not applicable; it is the memory template, not live advice about this behavior.
- `.claude/MEMORY.md`: fixed; two older entries corrected in place (automated recovery reserves `--abort` for owned state and never forces `--quit`; `--quit` only for the orphaned autostash shape), plus phase A's `cmd_setup` entry and this plan's new lessons.
- `openwiki/**`: fixed through the OpenWiki refresh (state-sync, hooks, and quickstart pages).
- `docs/2026-08-09-state-sync-rebase-recovery.md`: dated record, left unchanged by policy; current behavior lives in `docs/runtime-checks.md` and the corrected memory entries.

## Verification

```text
PASS        0.4s  uv run python scripts/generate_targets.py --all
PASS       55.4s  uv run python scripts/validate_targets.py
PASS        0.2s  uv run python scripts/validate_plan_frontmatter.py
PASS      367.0s  uv run python .claude/scripts/verify.py phase --format text
```

- Findings: `.claude/quality_reports/findings-2026-10-23_phase-D-knowledge-refresh.json` (0 findings after round 2, gate PASS, seven profiles).
- optional 1: PASS — the refreshed `openwiki/operations/git-backed-ai-state-sync.md` was read against `shared/hooks/scripts/state-sync.sh` (and the restorer, devcontainer, generator, validator, and tests) in two review rounds; round 1 found three prose statements that did not match the code, a second OpenWiki run corrected them, and round 2 found none.

## Open Questions / Next Steps

- Closeout of this final phase; then the branch is ready for a pull request when the user asks for one.
