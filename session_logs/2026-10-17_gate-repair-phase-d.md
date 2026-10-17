# Session: Gate repair — Phase D, guard coverage

**Date:** 2026-10-17
**Plan:** .claude/plans/2026-10-17_phase-D-guard-coverage.md
**Parent plan:** .claude/plans/gate-repair.md
**Status:** IN-PROGRESS

## Goal

Protect every client's in-repository hook- and server-launching config and
stop syncing `settings.local.json` (GR-008); run the plan checks at branch
creation (GR-009); keep test failures visible in shipped commands (GR-010);
remove the stale agent schema (GR-011).

## Task Tracking

- [x] PRE-FLIGHT: Phase C committed (`4103933`) and pushed; post-commit hook
  activated Phase D. Material-impact check: Phase C already changed the
  root `.mcp.json` and `.vscode/mcp.json` that step 1 now protects (the
  intended order). No planner needed.
- [x] PLAN WHEN NEEDED: approved plan is implementation-ready.
- [ ] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT — repeat until verification and review pass.
- [ ] COMMIT
- [ ] PUSH

## Work Log

- **11:00** - Code steps 1, 2, 4, 5, 6 delegated to one coder (sequential, so
  only one process regenerates `dist/`); step 3 Copilot documentation
  research delegated in parallel to a read-only agent.

- **11:25** - Step 3 research (WebFetch on code.visualstudio.com; raw
  sources at microsoft/vscode-docs `ef0ca127806a0e7eb9cd9e39e1d71c05e0a5769b`
  and microsoft/vscode `1e81fc75bb564738c29771d9b17c72e708a8211c`;
  docs.github.com fetched 2026-10-17):
  - VS Code agent hooks load from `.github/hooks/*.json`, and also from
    `.claude/settings.json` and `.claude/settings.local.json` when
    `chat.useClaudeHooks` is on (https://code.visualstudio.com/docs/agent-customization/hooks).
  - Workspace settings `chat.useHooks` (default true; false turns off local
    hooks), `chat.hookFilesLocations` (can drop `.github/hooks` or add
    locations), and `chat.useClaudeHooks` have window scope, so
    `.vscode/settings.json` can set them in a trusted workspace.
  - Copilot CLI (and VS Code's Copilot harness, same SDK) also reads
    `.github/copilot/settings.json` and `.github/copilot/settings.local.json`
    (inline `hooks`, top-level `disableAllHooks` that skips every hook)
    (https://docs.github.com/en/copilot/reference/hooks-reference).
  - Auto-approval does not bypass PreToolUse: `deny` returns before
    auto-confirm in `languageModelToolsService.ts`; approvals docs say a
    PreToolUse `deny` blocks a terminal call.
  - Decision: protect `.vscode/settings.json`, `.github/copilot/settings.json`,
    `.github/copilot/settings.local.json` by the same rule (plan step 3:
    protect each documented file). Not protected: `.agent.md` frontmatter
    hooks (add-only; most restrictive wins); `*.code-workspace` (unverified).
    Sent to the coder as an addition to step 1.

- **12:10** - Coder finished steps 1, 2, 4, 5, 6 (plus the three Copilot
  hook-switch files). `PROTECTED_PATH_LITERAL` is now built from
  `HOOK_CONFIGS`. State-sync preserves `settings.local.json` around pulls and
  unrelated-history merges (the deletion path needed an unpushed tracking
  commit or a merge to be reached; both tested with controls). Branch gate
  validates the big plan plus its listed phase files. Negative controls
  failed as expected for every guard. Accepted: a listed phase without a
  file is skipped at branch creation (matches the commit gate); an upgraded
  nested `.gitignore` without the `settings.local.json` line could re-track
  it (the template always had it). Recorded follow-up, not fixed: shell
  guards parse the Claude-compatible payload VS Code sends, not the Copilot
  CLI shape (`toolName` + `toolArgs` string); Copilot CLI is unsupported per
  `docs/runtime-checks.md:170`.
- **12:20** - Self-install; `check_runtime.py` PASS. Ran the installed
  `state-sync.sh checkpoint`: the nested repository no longer tracks
  `settings.local.json` (commit `3315617`), and the file's Git object hash
  is unchanged (`1af9b5fb38cf…`) before and after. The new protection now
  applies to the orchestrator too (a compound command naming the file was
  refused). `verify.py phase` PASS (pytest 2688 passed, 1 skipped).
  Documenter updated `docs/smoke-tests.md`, `docs/target-mapping.md`,
  `docs/runtime-checks.md`, and `README.md`; one stale README intro count
  sent back.

## [LEARN] Entries

## Verification

## Open Questions / Next Steps

- Await coder and research results.
