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

- **12:45** - Review round 1: Gate Result `PASS`, no CRITICAL or MAJOR, four
  MINOR: (1) `restore_local_settings` reverts a legitimate concurrent write
  made during the pull window (real data-safety issue); (2) state-sync
  change undocumented; (3) docs omit that any non-read command naming a
  protected config is denied on all clients, including an inline PR body;
  (4) branch-gate error loop can be an array slice. All four sent back:
  coder (restore only when missing or equal to git's blob, loop shrink,
  lock-in test), documenter (state-sync paragraph, naming-deny sentence
  with the `--body-file` advice).

- **13:30** - All four fixes landed. Restore now keeps a newer file unless
  it is missing or equals `origin/$BRANCH:settings.local.json`; branch-gate
  loop is an array slice; lock-in test for name-only denial. Docs state the
  exact restore rule, its one limit (a write before git's own write in the
  same window), three warnings, and the `--body-file` guidance. Regenerate,
  self-install, `check_runtime.py` PASS, nested repo still untracks the
  file with an unchanged hash, `verify.py phase` PASS (pytest 2695 passed,
  1 skipped), `validate_targets.py` PASS. Same reviewer asked to confirm.

- **13:55** - Review round 2: all four round-1 fixes confirmed. Gate Result
  `WARN`: one new MINOR (docs say three warnings; a fourth, informational
  "restored local settings.local.json …" warning exists) and one open
  request: does Copilot's native read of a protected config ask? Probe run
  by the orchestrator with `shared/hooks/scripts/protect-files.sh
  github-copilot` and payloads from files (`tool_name: read_file`,
  `tool_input.filePath`): `.vscode/settings.json`, `.mcp.json`, and the
  previously protected `.claude/settings.json` all return `ask` with the
  reason "Editing hook files requires approval"; `README.md` returns no
  decision. Pre-existing for Copilot (the guard runs on every Copilot tool
  call and treats any path key as a write), now wider. Related question
  raised: the shell guards recognize a terminal command only for tool names
  containing `bash`/`shell` or equal to `execute`; whether VS Code's
  terminal tool name reaches them is unknown in this repository. Research
  agent asked for the documented VS Code hook `tool_name` values.

- **14:20** - VS Code tool-name research (WebFetch of the hooks pages, last
  updated 10/14/2026; raw sources microsoft/vscode-docs
  `adb70b57fc27a9a6b9f6d99ef2f1eceb7d9bad8d` and microsoft/vscode
  `9a59550fc841805ebb44cfd5a09b92beed591d15`): Local-harness hooks receive
  the model-facing tool name with an object `tool_input`; terminal is
  `run_in_terminal` (`command`), plus `send_to_terminal`; reads are
  `read_file`, `view_image`, `list_dir`, `file_search`, `grep_search`,
  `semantic_search`; edits use case-variant path keys already matched.
  Copilot SDK harness names: `bash`/`powershell`, `view`, `grep`, `rg`,
  `glob`; its file-hook key casing is not established. Consequence: Copilot
  terminal commands skipped every shell guard (commit, branch, PR,
  git-protection, protected-file shell analysis). Recorded a scope change in
  the big plan (within approved goals: GR-008/GR-009 were false for
  Copilot) and sent the fix to the coder: recognize `run_in_terminal` and
  `send_to_terminal`; exempt the listed read-only tools from the
  protected-file path check. The SDK harness and Copilot CLI key casing
  stay a follow-up. Documenter fixed the warning count (lead-in without a
  count; informational "restored …" bullet added).

- **14:50** - Coder implemented the scope change: `is_bash_tool_payload` and
  `protect-files.py` `TERMINAL_TOOLS` accept `run_in_terminal` and
  `send_to_terminal`; `READ_ONLY_TOOLS` exempts the documented read tools;
  git-protection already read any `command` (lock-in test added);
  `record-branch-state.sh` now records Copilot terminal branch creation.
  Negative controls caught every change, including one dropped read name.
  Self-install; re-probe: Copilot `read_file` of `.vscode/settings.json`,
  `.mcp.json`, `.claude/settings.json` now returns no decision.
  `check_runtime.py` PASS; `verify.py phase` PASS (pytest 2749 passed,
  1 skipped). Documenter: Copilot notes in smoke-tests and target-mapping
  (with a source paragraph), "native read tool" wording, follow-up widened
  to the SDK harness and Copilot CLI key casing. `validate_targets.py` PASS.
  Same reviewer asked for a full review of the scope change plus the two
  confirmations.

## [LEARN] Entries

## Verification

## Open Questions / Next Steps

- Await coder and research results.
