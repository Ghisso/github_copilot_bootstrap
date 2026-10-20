---
name: 2026-10-20_phase-D-agent-definition-protection
type: small-plan
parent_plan: backlog-followups
phase_index: 4
status: planned
closeout_session_log:
---

# Small Plan: Agent Definition Protection

## Scope

Agent definition files set an agent's instructions and, in some clients,
its tools, hooks, MCP servers, and permission mode. Today any agent can edit
them in all four clients without a prompt (`docs/target-mapping.md`,
"Recorded follow-ups"). This phase protects the four agent folders the same
way gate-repair Phase D protected hook and server configs: an agent edit
asks on Claude Code and GitHub Copilot and is denied on Codex and
Antigravity (BF-D1). The same rule covers each protected folder as a whole.
That closes a gap found while planning: today `rm -rf`, `mv`, or `ln -s` of
a whole hook folder gets no decision (BF-D2). Workspace files
(`*.code-workspace`) join the list, because VS Code reads its hook switches
from them (BF-D3). Separately, generated Codex agent files stop carrying
`sandbox_mode`, which Codex ignores there (BF-D4). The docs record the
per-client result and the gaps that remain (BF-D5).

The bootstrap source in this repository, `shared/agents/`, stays editable.
The installer and generator write agent files from Python, which no hook
sees, so installs and regeneration are unaffected.

### Evidence settled during planning

- Agent files are generated, bootstrap-owned output. The installer treats
  every file under `.codex`, `.agents`, `.github/agents`, and `.claude`
  (outside consumer state) as owned and removes files the source no longer
  has (`scripts/runtime_ownership.py:21-35`,
  `scripts/install_bootstrap.py:572-625`). Consumers customize only project
  context and consumer-owned state (`CLAUDE.md:68`); maintainers add agents
  in `shared/` and regenerate (`README.md:1432`). No shipped skill or policy
  tells an agent to write an installed agent folder.
- Claude Code: subagent frontmatter supports `tools`, `permissionMode`,
  `mcpServers`, and `hooks` (https://code.claude.com/docs/en/sub-agents,
  read 2026-10-20). Native `.claude` write protection prompts in `default`
  and `acceptEdits`, only reaches the classifier in `auto`, and is off in
  `bypassPermissions` (https://code.claude.com/docs/en/permission-modes,
  "Protected paths"). A hook `ask` "also forces a permission prompt in auto
  mode" (https://code.claude.com/docs/en/hooks). The hook is therefore not
  redundant for Claude Code.
- GitHub Copilot in VS Code reads workspace agents from both
  `.github/agents` and `.claude/agents`
  (https://code.visualstudio.com/docs/copilot/customization/custom-agents,
  updated 2026-10-14). Agent-scoped hooks "run in addition to" workspace
  hooks (https://code.visualstudio.com/docs/agent-customization/hooks), and
  the most restrictive PreToolUse decision wins
  (https://code.visualstudio.com/docs/agents/reference/hooks-reference).
  The Copilot wrappers read `.claude/agents/<id>.md`
  (`docs/target-mapping.md:86`) through read tools, which the guard already
  exempts (`READ_ONLY_TOOLS`, `shared/hooks/scripts/protect-files.py:45-56`).
- VS Code workspace files: in a multi-root workspace, workspace settings
  live in the `.code-workspace` file, and folder settings apply only
  resource-scoped settings
  (https://code.visualstudio.com/docs/editing/workspaces/multi-root-workspaces,
  updated 2026-10-14). `chat.useHooks`, `chat.hookFilesLocations`, and
  `chat.useClaudeHooks` declare no scope (microsoft/vscode `9a59550f`,
  `src/vs/workbench/contrib/chat/browser/chat.shared.contribution.ts:2233-2291`),
  so they default to window scope
  (`src/vs/platform/configuration/common/configurationRegistry.ts:846`),
  which the workspace file accepts and folder settings do not
  (`src/vs/workbench/services/configuration/common/configuration.ts:33-34`).
- Codex: "Other session settings, including `sandbox_mode`,
  `approval_policy`, `model_provider`, and `mcp_servers`, don't override the
  parent configuration when placed in a custom agent file." and "Custom
  agent instructions can ask an agent to avoid edits, but they don't create
  a separate read-only sandbox."
  (https://learn.chatgpt.com/docs/agent-configuration/subagents, read
  2026-10-20). Only the reviewer carries the key today
  (`dist/multi-agent/.codex/agents/reviewer.toml:5`); no test requires it.
- Gap reproduced with the current `shared/` script and `claude-code` and
  `openai-codex` payloads: `rm -rf`, `mv`, `ln -s`, `bash -c 'rm -rf ...'`,
  and a Python `shutil.rmtree` on the whole `.claude/hooks` folder all get no
  decision. `protected()` matches only paths below a hook folder
  (`protect-files.py:330-335`), and the literal matcher needs a path after
  the folder name (`protect-files.py:128`).

## Steps

- [ ] **1. Protect agent folders, whole protected folders, and workspace files (BF-D1, BF-D2, BF-D3).**
  **Owner:** coder.
  **Files:** modify `shared/hooks/scripts/protect-files.py` (the hook-folder
  regex alternative at line 128, the folder checks in `protected()` at
  lines 330–335, and the two reasons in `emit()` at lines 1476–1480);
  modify `scripts/validate_targets.py` (the case tuples in
  `validate_hook_guardrails`, from line 3680); modify
  `tests/test_hook_gates.py` and `tests/test_protect_files_scoping.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Add one module-level tuple beside `HOOK_CONFIGS`, for example
  `CONTROL_PLANE_DIRS: tuple[str, ...] = (".github/hooks", ".claude/hooks",
  ".codex/hooks", ".claude/agents", ".codex/agents", ".github/agents",
  ".agents/agents")`. Build both the folder checks in `protected()` and the
  folder alternative of `PROTECTED_PATH_LITERAL` from it, so the two cannot
  drift (the same pattern gate-repair Phase D used for `HOOK_CONFIGS`). In `protected()`,
  a normalized path is a control-plane name when it equals a folder, starts
  with the folder plus `/`, ends with `/` plus the folder, or contains `/`
  plus the folder plus `/`. A path whose base name ends in `.code-workspace`
  (any letter case) is also a control-plane name. The repository scoping in
  `_control_plane_in_repo_root` is unchanged, so the same names in another
  checkout stay unprotected. The literal matcher matches each folder with or
  without a path after it, and `<name>.code-workspace`, keeping the existing
  left boundary and adding a right boundary that refuses `.claude/agents-old`
  and `.claude/agentsx`.
  The decision rule in `emit()` stays as it is: Codex and Antigravity deny,
  Claude Code and Copilot ask; the read-tool exemption, the secret-file
  rules, and the uncertain-literal deny do not change. Reword the two
  reasons so they name agent files in plain words: "Editing agent, hook, or
  server configuration requires approval: " and "Editing agent, hook, or
  server configuration is blocked because PreToolUse cannot request
  approval: ". Update the one assertion that quotes the old text
  (`tests/test_hook_gates.py:2725-2728`).
  Must not: protect `shared/agents/`, `.claude/skills/`, `.agents/skills/`,
  or the parent folders `.claude`, `.github`, `.codex`, `.agents` (that
  would deny `git -C .claude add -A`, the documented nested checkpoint);
  change a client decision; add a setting or an option; use syntax that the
  Python 3.9 hook-compatibility job in `.github/workflows/validate.yml`
  rejects.
  Also resolve the path tokens of unmodelled mutating Git subcommands
  against the `-C` directory, not only the repository root: in the `git`
  branch of the shell analysis (`protect-files.py`, about lines 1309-1337),
  pass those tokens through
  `resolve_from_directories(tokens, git_roots, repo_root)`, which the same
  branch already uses for `git mv`. Today
  `git -C .claude rm -r -q hooks` and
  `git -C .claude checkout HEAD~5 -- hooks/scripts/protect-files.py` get no
  decision (probed 2026-10-20). If that change grows beyond this one call
  site, stop and record the case as a remaining gap with the probe as
  evidence instead.
  In `scripts/validate_targets.py`, add one generated-copy case per client
  for an agent file: `.claude/agents/reviewer.md` asks for `claude-code`,
  `.codex/agents/reviewer.toml` denies for `openai-codex`,
  `.github/agents/reviewer.agent.md` asks for `github-copilot`, and
  `.agents/agents/reviewer/agent.md` denies for `google-antigravity`. Add a
  Copilot `read_file` case for `.claude/agents/reviewer.md` that must return
  no decision, because the Copilot wrappers read that file.
  **Tests** (offline, no model call):
  - Add `AGENT_DEFINITION_PATHS = (".claude/agents/coder.md",
    ".codex/agents/reviewer.toml", ".github/agents/planner.agent.md",
    ".agents/agents/coder/agent.md", "team.code-workspace")` to the gate-repair Phase D
    parametrizations that use `HOOK_AND_SERVER_CONFIGS`
    (`tests/test_hook_gates.py:3240-3450`): per-client edit and redirect,
    the Claude Code and Codex `pretool-bash-guard.sh` chain, the
    Antigravity bridge `write_to_file` and `run_command`, `cat` and native
    reads allowed, and the Antigravity `view_file` read allowed. Add
    `.claude/agents/coder.md` to the Copilot read-tool test
    (`test_protect_files_allows_copilot_read_tools_on_hook_configs`).
  - For each of the seven folders, `rm -rf <folder>`, `mv <folder> /tmp/x`,
    and `ln -s /tmp/x <folder>` ask for `claude-code` and deny for
    `openai-codex`; `python3 -c "import shutil; shutil.rmtree('<folder>')"`
    is denied for both (the existing uncertain-literal rule).
  - In `tests/test_protect_files_scoping.py`, add the new names to
    `_CONTROL_PLANE_RELATIVE_PATHS` (lines 212–226), so each is allowed in
    a foreign checkout and denied inside the repository. Add literal rows:
    must match `.claude/agents/coder.md`, `.claude/agents`,
    `/repo/.agents/agents/coder/agent.md`, and `team.code-workspace`; must
    not match `shared/agents/coder/prompt.md`, `.claude/agents-old/x.md`,
    `x.claude/agents/y.md`, `.agents/skills/ponytail/SKILL.md`, and
    `team.code-workspaces`.
  - `git -C .claude rm -r -q hooks`,
    `git -C .claude checkout HEAD~5 -- hooks/scripts/protect-files.py`, and
    `cd .claude && rm -rf hooks` ask for `claude-code` and deny for
    `openai-codex`.
  - Still allowed for every client: `git -C .claude add -A`, `ls .claude`,
    `rg --files .claude/agents`, `git diff --no-index` of an agent file
    against its `dist/` copy, a write under `shared/agents/`, and the
    existing self-install and generator command lines.
  - Negative control: run the new cases against the unchanged script first.
    The agent-folder, whole-folder, and workspace-file cases must fail and
    the still-allowed cases must pass. Record both runs in the session log.

- [ ] **2. Remove the dead Codex `sandbox_mode` key (BF-D4).**
  **Owner:** coder.
  **Files:** modify `scripts/generate_targets.py` (delete
  `codex_sandbox_mode`, lines 931–936, and its use in
  `render_codex_agent_adapter`, lines 1755–1757); modify
  `scripts/validate_targets.py` (remove `"sandbox_mode"` from
  `CODEX_AGENT_ALLOWED_FIELDS`, lines 150–157); modify
  `tests/test_validate_targets.py` (add `"sandbox_mode"` to the parametrize
  of `test_validate_agents_rejects_codex_agent_local_override`, line 2066).
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Codex ignores the key in a custom agent file (see the evidence above), so
  it implies a read-only sandbox that never applies. Delete it rather than
  keep it with a comment. With the field out of the allowed set, the
  validator reports it as a per-agent override, like `skills` and
  `mcp_servers`.
  Must not: add a replacement mechanism or a TOML comment, or change any
  other Codex field. Keep the capability line in
  `codex_agent_metadata_header`, which already tells the reviewer it may
  only read and search.
  **Tests:** the new `sandbox_mode` parameter fails before the validator
  change and passes after it. `validate_targets.py` passes on the
  regenerated `dist/`, so no generated Codex agent carries the key.

- [ ] **3. Document the protection and the remaining gaps (BF-D5).**
  **Owner:** documenter, after steps 1 and 2 pass `verify.py fast`, so the
  reviewer sees the docs with the `documentation` profile.
  **Files:** modify `docs/target-mapping.md` (create a `## Backlog-Followups Client Parity`
  section after the gate-repair section, with the gate-repair table's
  columns, holding the parity rows below; replace the three resolved "Recorded follow-ups"
  bullets at lines 112–114 with the remaining-gap bullets there); `docs/smoke-tests.md`
  (lines 206 and 212); `docs/runtime-checks.md` (one new row after the
  protected-configs row at line 586); `README.md` (one bullet after
  "Protected configs and branch-time plan check", lines 364–377);
  `shared/policies/workflow.instructions.md` ("File Protection Rules",
  lines 511–523, one bullet under "Also blocked in pre-tool hooks");
  `shared/skills/commit/SKILL.md` (the PR example, about line 112: write the
  body to a file and pass `gh pr create --body-file <file>` instead of an
  inline heredoc). In the existing gate-repair table of
  `docs/target-mapping.md`, add `.claude/hooks/` to the Claude Code cell of
  the hook- and server-config protection row (line 96).
  **Required Skills:** `shared/skills/documentation/SKILL.md`,
  `shared/skills/integration-gate-spike/SKILL.md` (record each third-party
  claim with its link, read date, and tier: documented, source, or
  unverified).
  The runtime-checks row, the README bullet, and the smoke-tests lines say:
  an agent edit of an agent file, a protected folder, or a workspace file
  asks on Claude Code and Copilot and is denied on Codex and Antigravity.
  Any command outside the guard's read-only list that names one of them is
  denied on all four clients, for example `ls`, `diff`, `cmp`, or `find` on
  an agent file. Recovery: read with `cat`, a native read tool, or
  `rg --files`; compare with `git diff --no-index` or
  `uv run python scripts/check_runtime.py`; change agents in `shared/agents/`
  and regenerate (this repository) or re-run the installer (a consumer).
  The guard also scans heredoc bodies and the arguments of commands it does
  not model, so text that names a protected path is denied too: write
  findings JSON, PR bodies, and session-log additions that name such a path
  with the native Write or Edit tool (a scratch file for the first two),
  then pass `record_findings.py --findings-json <file>` or
  `gh pr create --body-file <file>`.
  The policy bullet names the protected folders and workspace files, the
  per-client decision, and "change the source and reinstall instead".
  Must not: hand-edit `openwiki/` pages (Phase G refreshes
  `openwiki/architecture/hooks-and-guardrails.md` and
  `openwiki/architecture/agents-and-skills.md`); change dated records
  (`docs/sidecar-provider-contract.md`, closed plans, session logs); claim a
  native run that did not happen.

- [ ] **4. Regenerate, self-install, verify, review, close out.**
  **Owner:** orchestrator; fresh reviewer; documenter for review fixes.
  Run `uv run python scripts/generate_targets.py --all` and
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  before verification. After the self-install the new rules apply to the
  orchestrator's own commands: compare agent files with `git diff --no-index`
  or `check_runtime.py`, never `diff`, `cmp`, or `ls` on the file; probe the
  guard with payload files and the `shared/` script copy; keep agent paths
  out of other non-read commands. This phase's own findings name agent
  folders, so write the findings JSON with the Write tool into the scratch
  folder and pass `--findings-json <file>`; never pipe it through a
  heredoc. The agent folders are ignored by Git in
  this repository, so staging names only `shared/`, `scripts/`, `tests/`,
  `docs/`, and `README.md` paths.
  **Required Skills:** `shared/skills/documentation/SKILL.md`,
  `shared/skills/code-review/SKILL.md`.

### Parity rows for `docs/target-mapping.md`

Put these rows in the new `## Backlog-Followups Client Parity` table, with the same columns as the
gate-repair table:

| Change | Claude Code (`claude-code`) | Codex (`openai-codex`) | GitHub Copilot (`github-copilot`) | Antigravity | Evidence |
| --- | --- | --- | --- | --- | --- |
| Agent definition protection (ask on Claude and Copilot, deny on Codex and Antigravity; each folder also protected as a whole) | `.claude/agents/`. Native `.claude` protection only reaches the classifier in `auto` and is off in `bypassPermissions`, so the hook still adds a prompt | `.codex/agents/` | `.github/agents/` and `.claude/agents/` (VS Code reads both). Read tools stay allowed, so the wrappers can read `.claude/agents/<id>.md` | `.agents/agents/` | `tests/test_hook_gates.py`, `tests/test_protect_files_scoping.py`, `scripts/validate_targets.py` installed-hook smoke; [Claude Code permission modes](https://code.claude.com/docs/en/permission-modes) and [VS Code custom agents](https://code.visualstudio.com/docs/copilot/customization/custom-agents), read 2026-10-20 |
| Hook folders protected as whole folders | `.claude/hooks` | `.codex/hooks` | `.github/hooks` | `.claude/hooks` (the scripts the bridge runs) | `tests/test_hook_gates.py` |
| Workspace files (`*.code-workspace`) protected | Same guard; Claude Code does not read the file | Same guard; Codex does not read the file | In a multi-root workspace the file holds the window-scoped hook switches `chat.useHooks`, `chat.hookFilesLocations`, and `chat.useClaudeHooks` ([multi-root workspaces](https://code.visualstudio.com/docs/editing/workspaces/multi-root-workspaces); `microsoft/vscode` `9a59550f` source, read 2026-10-20) | Same guard; Antigravity does not read the file | `tests/test_hook_gates.py`, `tests/test_protect_files_scoping.py` |
| Codex agent `sandbox_mode` removed | Not applicable | Removed: Codex ignores it in a custom agent file. The reviewer is read-only by its instructions and runs in the parent session's sandbox ([Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), read 2026-10-20) | Not applicable | Not applicable | `tests/test_validate_targets.py`, `scripts/validate_targets.py` |

Remaining-gap bullets for "Recorded follow-ups":

- Workspace files outside this repository's root are not protected, like
  every other control-plane name. A `.code-workspace` file often sits
  beside the repository, not inside it.
- Codex read-only roles are read-only by instruction only. Codex ignores a
  custom agent's `sandbox_mode`, so the bootstrap no longer writes it, and
  the reviewer runs with the parent session's sandbox and approval policy.
- Removing or replacing a whole parent folder (`.claude`, `.github`,
  `.codex`, `.agents`) gets no decision; only the protected folders and the
  files inside them do. Protecting the parents would also deny
  `git -C .claude add -A`, the documented nested checkpoint.
- Skill folders (`.claude/skills/`, `.agents/skills/`) are not protected,
  although a Claude Code skill can register `hooks` and pre-approve tools
  with `allowed-tools` ([skills](https://code.claude.com/docs/en/skills),
  read 2026-10-20).

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/test_hook_gates.py tests/test_protect_files_scoping.py tests/test_validate_targets.py tests/test_lifecycle_hooks.py -q
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Claude Code: in this repository, ask the agent to add a line to
  `.claude/agents/reviewer.md`, record the approval prompt, and decline it.
  Repeat in `auto` mode and record that a prompt still appears.
- Codex: record that an edit to `.codex/agents/reviewer.toml` is denied
  natively, and that the `reviewer` custom agent still loads without
  `sandbox_mode`.
- GitHub Copilot (VS Code Local harness): record that an edit of
  `.github/agents/coder.agent.md` asks, and that running the `coder` agent,
  which reads `.claude/agents/coder.md`, gets no prompt for that read.
- Antigravity: in a disposable install, record whether a write to
  `.agents/agents/coder/agent.md` is denied natively.

## Review Profiles

Use `.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Give the reviewer BF-D1 to
BF-D5, the evidence list in Scope, the negative-control output, and the
final diff.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
