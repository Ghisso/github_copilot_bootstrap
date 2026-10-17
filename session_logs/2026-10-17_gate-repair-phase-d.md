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
- [x] IMPLEMENT/VERIFY/REVIEW — four review rounds (same reviewer for
  confirmations; round 3 a full review of the scope change); final Gate
  Result `PASS` with no findings.
- [x] CLOSEOUT: final AI state, checkpoint, staged index, findings, phase
  receipt, closeout dry run, checkpoint, closeout receipt.
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

- **15:20** - Review round 3: scope change reviewed in full, items 1 and 4
  closed; Gate Result `PASS` with one MINOR: the read exemption skipped the
  whole classifier, dropping the existing secret-file deny for Copilot read
  tools (`.env` read had been denied, then allowed). Fixed by the coder
  (`read_only` flag: drop hook-config hits only; no patch scan of read-tool
  text); controls caught both directions. Plan scope-change record
  corrected (git-protection already covered Copilot terminals). Docs: VS
  Code task tools added as an unverified follow-up; read rule made precise.
  Regenerate, self-install, `check_runtime.py` PASS, `validate_targets.py`
  PASS, `verify.py phase` PASS (pytest 2767 passed, 1 skipped). Same
  reviewer asked to confirm.

- **15:35** - Review round 4 (same reviewer, scoped to the fix): Gate Result
  `PASS`, findings `[]`. Every finding and request from rounds 1–3 closed.

### Phase-boundary summary

- **Objective and change:** eight more hook- and server-launching configs
  are protected for all four clients; the nested ai-state repository no
  longer tracks `settings.local.json` and keeps a second clone's copy;
  branch creation runs the plan validator on the plan's own files; shipped
  deprecation checks keep pytest's exit status, with a validator check;
  the unused agent schema is gone.
- **Deviations from the plan (scope change, reported to the user):** VS
  Code's Local harness sends the terminal tool as `run_in_terminal` /
  `send_to_terminal`, so Copilot terminal commands had skipped the commit,
  branch, and PR gates and the protected-file shell analysis. The shared
  shell guards and `protect-files.py` now recognize both names, and
  Copilot's documented read-only tools read hook configs without a prompt
  (secret-shaped files stay denied). Recorded in the big plan's
  "Scope-change records". Also added: the three documented Copilot hook
  switch files to the protection list.
- **Checks:** see `## Verification` below.
- **Open findings:** none. Follow-ups recorded in `docs/target-mapping.md`:
  Copilot SDK harness and Copilot CLI payload key casing; other VS Code
  command-running tools (for example `create_and_run_task`), unverified;
  `*.code-workspace` and `.agent.md` frontmatter hooks not protected.
  Accepted limits: a listed phase without a file is skipped at branch
  creation; an old nested `.gitignore` without the `settings.local.json`
  line could re-track it; a settings write that lands before git's own
  write in the same window restores the older copy.
- **Next operation:** Phase E, knowledge refresh and final audit.

### Requirement mapping

- GR-008: `test_protect_files_gates_hook_and_server_configs_per_client`,
  `test_pretool_bash_guard_gates_hook_and_server_config_redirects`,
  `test_antigravity_bridge_denies_hook_and_server_config_writes`, read and
  self-install allowance tests, `test_protect_files_denies_a_command_that_only_names_a_hook_config`,
  scoping tests in `tests/test_protect_files_scoping.py`, the Copilot
  terminal and read-tool tests (including the secret-file read deny), and
  the state-sync tests (`test_checkpoint_untracks_previously_committed_local_settings_without_deleting_it`,
  `test_second_clone_keeps_its_local_settings_when_it_pulls_the_untrack_commit`,
  `test_pull_keeps_a_settings_write_made_while_it_ran`, and the merge,
  conflict, and skip variants). Live: this repository's nested repository
  no longer tracks the file; its Git hash is unchanged.
- GR-009: branch-gate tests in `tests/test_branch_state.py` for all four
  clients and both Copilot terminal tools.
- GR-010: `test_deprecation_check_steps_keep_pytests_exit_status`,
  `test_add_dependency_step_fails_when_the_import_check_fails`, the
  failure-masking validator tests, and the shipped-text lint.
- GR-011: `validate_targets.py` PASS; no reader remains.
- GR-013: no model call; no version change; no network in required checks.

## [LEARN] Entries

- [LEARN:security] Confirm a client's real hook tool names from source
  before claiming a gate covers it; VS Code's `run_in_terminal` had skipped
  every Copilot shell guard.
- [LEARN:security] An exemption written as an early return skips every
  later check; the Copilot read exemption first dropped the secret deny.
- [LEARN:tooling] `.vscode/settings.json` and `.github/copilot/settings*.json`
  can turn off Copilot hooks; protect them like hook configs.
- [LEARN:workflow] After a self-install, new protect-files rules apply to
  the orchestrator's own commands; probe with payload files and the
  `shared/` script copy.

## Verification

- optional 1: NOT RUN — the native Claude Code checks (an agent edit of `.claude/settings.local.json` prompting, and a "don't ask again" approval still saving) are user-run host checks; protect-files returns `ask` for `claude-code` in the offline tests.
- optional 2: NOT RUN — a native Codex edit of `.codex/hooks.json` is a user-run host check; the `openai-codex` deny is covered offline.
- optional 3: NOT RUN — a native Antigravity write to `.agents/hooks.json` in a disposable install is a user-run host check; the bridge deny is covered offline.

## Open Questions / Next Steps

- Next: Phase E, `2026-10-17_phase-E-gate-repair-knowledge-refresh`.
