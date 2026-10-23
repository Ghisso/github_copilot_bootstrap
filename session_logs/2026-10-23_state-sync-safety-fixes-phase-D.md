# Session: Knowledge refresh and stale-claims audit

**Date:** 2026-10-23
**Plan:** `.claude/plans/2026-10-23_phase-D-knowledge-refresh.md`
**Status:** IN-PROGRESS

## Goal

Audit live guidance for claims that this plan or earlier work made stale, then refresh the enabled OpenWiki layer through OpenWiki's own MCP tools so its pages describe the new state-sync, restorer, and devcontainer behavior.

## Work Log

- Phase C committed as `ebc3bdd` and pushed; the post-commit hook advanced `current_phase` to this phase.
- `.claude/MEMORY.md`: corrected two older entries in place. The `[LEARN:security]` entry on automated recovery now reserves `--abort` for owned state and says never to force an operation out with `--quit`; the `[LEARN:recovery]` entry on `--quit` now limits it to the exact orphaned autostash shape. The `cmd_setup` `[LEARN:domain]` entry was already corrected in phase A.
- Documenter audit of every live-advice surface: no stale claim outside `openwiki/**`, so no file changed (per-surface results below).
- OpenWiki refresh through its own MCP tools: `openwiki_begin` (`mode: "update"`, run `74fb4fbe-50f2-45b8-970f-c676b77e44d1`) returned a planning run with eight claim issues on three pages; I submitted a three-page plan (`git-backed-ai-state-sync.md`, `hooks-and-guardrails.md`, `quickstart.md`), wrote each page, reconciled every flagged claim (revised with current evidence), added eleven new claims on the state-sync page, and `openwiki_finish` returned `complete`. On the hooks page I also corrected prose that said only Codex runs `state-sync.sh push` on `UserPromptSubmit` (`scripts/generate_targets.py` wires it for Claude Code too, with Claude `SessionEnd` push and `StopFailure` checkpoint). Afterwards root `AGENTS.md` and `CLAUDE.md` were unchanged and no `openwiki/.run.json` remained.
- Regenerated targets and refreshed the overlay; the required checks and the review are running.

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

## Open Questions / Next Steps

- Closeout of this final phase; then the branch is ready for a pull request when the user asks for one.
