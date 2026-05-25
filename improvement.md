---
name: orchestrator-and-lifecycle-hardening
type: big-plan
status: complete
originating_branch: dev
implementation_branch: orchestrator-and-lifecycle-hardening_implementation
started_at: 2026-05-24T15:00:00Z
completed_at: 2026-05-24T15:25:00Z
phases:
  - phaseA-documenter-delegate
  - phaseB-workflow-rewrite
  - phaseC-templates
  - phaseD-branch-commit-hooks
  - phaseE-pr-and-session-hooks
  - phaseF-validator-and-docs
  - phaseG-agent-communication-contracts
current_phase:
---

# Orchestrator and Lifecycle Hardening

## Implementation Handoff (actual changes applied)

Implementation status: complete in source files. `dist/multi-agent/` was regenerated from `shared/` with `uv run python scripts/generate_targets.py --all`; do not hand-edit `dist/`.

This implementation was applied directly in the current worktree because the user asked to implement immediately before the new branch hooks existed. Future consumer repos should use the enforced flow described here: start on clean `dev`, create `<plan_name>_implementation`, close one small plan per commit, then open `gh pr create --base dev` only on explicit user request.

### Files added

- `scripts/validate_plan_frontmatter.py`
- `shared/hooks/scripts/_lib-frontmatter.sh`
- `shared/hooks/scripts/enforce-branch-state.sh`
- `shared/hooks/scripts/record-branch-state.sh`
- `shared/hooks/scripts/enforce-commit-gate.sh`
- `shared/hooks/scripts/record-commit-closeout.sh`
- `shared/hooks/scripts/enforce-pr-gate.sh`
- `shared/hooks/scripts/session-start-state.sh`
- `shared/hooks/scripts/stop-session-log-check.sh`
- `shared/templates/plan-big.md`
- `shared/templates/plan-small.md`

### Files changed

- Workflow and gates: `shared/policies/workflow.instructions.md`, `shared/policies/quality-and-testing.instructions.md`, `shared/policies/workspace.instructions.md`, `shared/policies/tool-routing.instructions.md`
- Agent contracts: every `shared/agents/*/prompt.md`, plus `shared/agents/orchestrator/agent.yaml`
- Hook wiring: `shared/hooks/hooks.json`, `scripts/generate_targets.py`
- Validation/runtime: `scripts/validate_targets.py`, `scripts/check_runtime.py`, `scripts/install_bootstrap.py`
- Scoring/templates: `shared/scripts/quality_score.py`, `shared/templates/session-log.md`, `shared/templates/quality-report.md`, `shared/plans/README.md`, `shared/session_logs/README.md`
- Docs/root guidance: `README.md`, `AGENTS.md`, `docs/architecture.md`, `docs/runtime-checks.md`, `docs/smoke-tests.md`, `docs/target-mapping.md`

### Important corrections discovered during implementation

1. **Plan template frontmatter must start at byte 0.** The first draft of `shared/templates/plan-big.md` and `shared/templates/plan-small.md` had `# Big Plan` / `# Small Plan` before frontmatter. That breaks both `scripts/validate_plan_frontmatter.py` and hook frontmatter reads. The shipped templates now start with `---`, and `scripts/validate_targets.py` asserts generated plan templates start with frontmatter.
2. **The Python frontmatter parser must convert empty scalars to lists.** `phases:` initially parsed as an empty string before the indented `- phase` lines arrived. `scripts/validate_plan_frontmatter.py` now converts `""` into `[]` when list items are encountered.
3. **The no-lessons marker is ASCII exact text.** Hooks grep for `[LEARN] none - no new lessons this session`. Do not use an em dash in generated templates or closeout logs unless the hook is changed too.
4. **`_lib-frontmatter.sh` is a library, not an executable hook.** `scripts/validate_targets.py` now has `REQUIRED_HOOK_LIBRARIES = ("_lib-frontmatter.sh",)` and skips the executable-bit check for that file.
5. **Lifecycle hook tests need `.claude/` ignored in the temporary repo.** Without a `.gitignore` entry for `.claude/`, the branch gate's "clean worktree" check fails because test plan files are untracked. `setup_hook_repo()` writes `.gitignore` with `.claude/`.
6. **Codex config validation had to move out of the TOML exception path.** The validator now always checks `[features] hooks = true` and bans `codex_hooks = true`; these checks are no longer accidentally nested only under `TOMLDecodeError`.
7. **`gh` is optional.** `scripts/check_runtime.py` warns when `gh` is missing: the push gate still blocks common implementation-branch push paths, but GitHub web UI PR creation cannot be gated. Branch protection on `dev` is still the external compensating control.
8. **PR/push gate actual behavior:** `enforce-pr-gate.sh` requires `gh pr create --base dev`. For `git push`, it gates any push from a `*_implementation` branch until all small plans are complete, commit count is at least phase count, and bypass logs are acknowledged. It does not parse a push "base" because push has no PR base.
9. **Quality score smoke can write anywhere, commit gate reads only score reports.** The smoke test wrote `/tmp/qreports/test.json`. The commit gate reads `.claude/quality_reports/score-*.json` whose JSON metadata matches the active branch and phase.
10. **Generated scorer metadata includes `dirty: true` during normal development.** That is expected when the worktree has pending edits. The gate trusts branch/phase/score/freshness, not a clean-tree requirement at scoring time.
11. **SubagentStop artifact enforcement remains out of scope.** The plan's stretch section was not implemented.
12. **Docs correction:** Runtime docs now say the devcontainer does not require `/dev/fuse` or apparmor overrides, but it still intentionally includes `SYS_ADMIN` and `seccomp=unconfined` for `bubblewrap`.

### Exact verification performed

Commands run successfully:

```bash
uv run python -m py_compile scripts/validate_targets.py scripts/validate_plan_frontmatter.py scripts/check_runtime.py shared/scripts/quality_score.py
bash -n shared/hooks/scripts/_lib-frontmatter.sh shared/hooks/scripts/enforce-branch-state.sh shared/hooks/scripts/record-branch-state.sh shared/hooks/scripts/enforce-commit-gate.sh shared/hooks/scripts/record-commit-closeout.sh shared/hooks/scripts/enforce-pr-gate.sh shared/hooks/scripts/session-start-state.sh shared/hooks/scripts/stop-session-log-check.sh
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python shared/scripts/quality_score.py shared/scripts/quality_score.py --skip-tests --phase smoke --base-ref dev --json --out /tmp/qreports/test.json
uv run python scripts/validate_plan_frontmatter.py shared/templates/plan-big.md shared/templates/plan-small.md
git diff --check
rg -n 'After score >= 80|After score ≥ 80|Score >= 80|Score ≥ 80|codex_hooks|Just do it|plan/verify/review/score loop|plan -> implement -> verify -> review -> score workflow|PLAN -> IMPLEMENT -> VERIFY -> REVIEW -> FIX -> SCORE' dist/multi-agent README.md docs shared AGENTS.md
```

Observed results:

- `scripts/validate_targets.py`: `PASS generated target is structurally valid`
- `scripts/check_runtime.py`: passes, with only the expected `gh` optional-binary warning
- `quality_score.py` smoke: score `100`, gate `EXCELLENCE`, JSON written to `/tmp/qreports/test.json`
- Plan template validator: passes after the list-parser fix
- Stale phrase scan: no matches
- `git diff --check`: clean

Replication note for this sandbox: `uv run ...` initially failed under the filesystem sandbox because `/home/ghisso/.cache/uv` was read-only. Re-running the same `uv run` commands with approved cache access fixed it; no code change was needed.

### Post-review findings and resolution plan

Review status: follow-up fixes implemented. The original implementation broadly landed the intended lifecycle hardening, and the advertised verification can be reproduced with local-safe cache paths, but several issues weakened the actual enforcement.

Non-issues from review:

- The plan file is named `improvement.md`, not `improvements.md`; this was a request typo and needs no repository change.
- The untracked root `.codex/config.toml` is intentional local Codex MCP configuration for Semble and context-mode access. Do not include it in this plan's source/generator changes.

Findings to resolve:

1. **Generated dispatcher is not executable.** Generated Claude and Codex hook commands invoke `.claude/hooks/scripts/run-hook.sh` directly, but `run-hook.sh` is currently mode `0644` in source and generated `dist/`. Installed consumer repos are repaired by `scripts/install_bootstrap.py`, but generated output and `scripts/validate_targets.py` do not catch the mismatch.
   - Resolution: make `shared/hooks/scripts/run-hook.sh` executable in source, add it to executable validation, regenerate `dist/multi-agent/`, and add a validator check that generated hook commands cannot reference a non-executable dispatcher.
2. **README score-report path does not match commit gate glob.** `README.md` tells users to write `.claude/quality_reports/<timestamp>-<phase>.json`, while `enforce-commit-gate.sh` only reads `.claude/quality_reports/score-*.json`.
   - Resolution: standardize all docs, templates, agent prompts, and remediation text on `.claude/quality_reports/score-<timestamp>.json`; add a stale-string validation for the wrong `<timestamp>-<phase>.json` pattern.
3. **Score metadata contract is under-enforced.** The plan requires persisted score reports to identify branch, phase, base ref, merge base, head SHA, dirty status, generated timestamp, target, and changed files. The commit gate currently trusts only branch, phase, and score; the validator's positive fixture also omits most required metadata.
   - Resolution: strengthen `enforce-commit-gate.sh` to require the full metadata set and reject empty/mismatched `base_ref`, `merge_base_sha`, `head_sha`, `generated_at`, `target`, `dirty`, and `changed_files` fields where applicable. Update lifecycle hook tests to include both complete metadata and missing-metadata failure cases.
4. **Branch creation parser misses common branch forms.** `parse_branch_create_command` handles `git checkout -b` and `git switch -c`, but misses `git switch --create` and `git checkout -B`, allowing those paths to bypass the clean-dev and plan checks.
   - Resolution: expand parsing for `git switch --create`, `git switch -C`, `git checkout -B`, and quoted branch names. Add explicit negative tests showing these forms are denied on dirty or non-`dev` state and allowed only with valid metadata.
5. **Commit closeout can mutate plan state without confirmed commit correlation.** `record-commit-closeout.sh` only compares the intercepted subject to `git log -1` when it can parse a subject. Commands without `-m`/`-F` can still advance `current_phase` after an unrelated or unconfirmed commit.
   - Resolution: require a positive commit correlation before mutating frontmatter. Use hook result payloads when available, otherwise require a parsed subject or captured pre/post HEAD comparison. If correlation is unavailable, emit `additionalContext` and leave plan state unchanged.

Follow-up implementation results:

- `scripts/generate_targets.py` now makes generated `run-hook.sh` executable, and `scripts/validate_targets.py` enforces that generated hook commands cannot point at a non-executable dispatcher.
- Score report paths now consistently use `.claude/quality_reports/score-<timestamp>.json`; stale `<timestamp>-<phase>` paths are blocked by validation.
- `enforce-commit-gate.sh` now requires the promised score metadata: `base_ref`, `merge_base_sha`, `head_sha`, `generated_at`, `target`, `dirty`, and `changed_files`, in addition to score, branch, and phase.
- Branch lifecycle parsing now catches `git switch --create`, `git switch --create=...`, `git switch -C`, and `git checkout -B` in addition to the original `git checkout -b` and `git switch -c` forms.
- `record-commit-closeout.sh` now refuses to mutate plan frontmatter when it cannot parse and correlate the intercepted commit subject.

Planned verification for the follow-up fixes:

```bash
PYTHONPYCACHEPREFIX=/tmp/github_copilot_bootstrap-pycache python -m py_compile scripts/validate_targets.py scripts/validate_plan_frontmatter.py scripts/check_runtime.py shared/scripts/quality_score.py
bash -n shared/hooks/scripts/_lib-frontmatter.sh shared/hooks/scripts/run-hook.sh shared/hooks/scripts/enforce-branch-state.sh shared/hooks/scripts/record-branch-state.sh shared/hooks/scripts/enforce-commit-gate.sh shared/hooks/scripts/record-commit-closeout.sh shared/hooks/scripts/enforce-pr-gate.sh shared/hooks/scripts/session-start-state.sh shared/hooks/scripts/stop-session-log-check.sh
PYTHONPYCACHEPREFIX=/tmp/github_copilot_bootstrap-pycache python scripts/generate_targets.py --all
PYTHONPYCACHEPREFIX=/tmp/github_copilot_bootstrap-pycache python scripts/validate_targets.py
PYTHONPYCACHEPREFIX=/tmp/github_copilot_bootstrap-pycache python scripts/check_runtime.py
UV_CACHE_DIR=/tmp/github_copilot_bootstrap-uv-cache python shared/scripts/quality_score.py shared/scripts/quality_score.py --skip-tests --phase smoke --base-ref dev --json --out /tmp/qreports/test.json
PYTHONPYCACHEPREFIX=/tmp/github_copilot_bootstrap-pycache python scripts/validate_plan_frontmatter.py shared/templates/plan-big.md shared/templates/plan-small.md
git diff --check
rg -n 'After score >= 80|After score ≥ 80|Score >= 80|Score ≥ 80|codex_hooks|Just do it|plan/verify/review/score loop|plan -> implement -> verify -> review -> score workflow|PLAN -> IMPLEMENT -> VERIFY -> REVIEW -> FIX -> SCORE|quality_reports/<timestamp>-<phase>\\.json' dist/multi-agent README.md docs shared AGENTS.md
```

## Context

The orchestrator agent currently skips required workflow phases (DOCUMENT, LEARN, session-log) even though the prompt says they're mandatory — because the enforcement is prose-only and gameable. The user runs work through a two-tier plan structure (big plans decomposed into small plans via the `plan-decomposition` skill, with one branch per big plan and one commit per small-plan closeout), but none of this is encoded in `shared/`: no dev-branch default, no `<plan>_implementation` naming, no commit/PR gates, no enforced TodoWrite-first contract, no hook that blocks `git commit` when the loop wasn't completed.

This plan adds three layers of enforcement that must all hold for the workflow to be skippable-by-accident:

1. **Instructions** (prompt prose) — the canonical sequence, branch lifecycle, and "loop until score ≥ 90" rule, in [shared/policies/workflow.instructions.md](shared/policies/workflow.instructions.md) and [shared/agents/orchestrator/prompt.md](shared/agents/orchestrator/prompt.md).
2. **Metadata** (agent capabilities) — fix the missing `documenter` delegate in [shared/agents/orchestrator/agent.yaml](shared/agents/orchestrator/agent.yaml).
3. **Hooks** (harness-enforced) — new PreToolUse / SessionStart / Stop scripts that block `git checkout -b`, `git commit`, and `gh pr create` unless plan/score/session-log gates pass.

Every change must propagate to all three target tools — **Claude Code**, **GitHub Copilot**, **OpenAI Codex** — through the existing generator. **Important caveat from docs verification (May 2026):** enforcement strength differs per tool. See "Per-tool enforcement degradation" section below. Constraints to respect:

- Workflow phrase strings appear in [scripts/generate_targets.py:451](scripts/generate_targets.py#L451) and [scripts/generate_targets.py:513](scripts/generate_targets.py#L513); both must stay in sync with [shared/policies/workflow.instructions.md](shared/policies/workflow.instructions.md).
- [scripts/validate_targets.py:610-618](scripts/validate_targets.py#L610-L618) requires specific phrases in generated `CLAUDE.md` and `AGENTS.md`; [scripts/validate_targets.py:621-642](scripts/validate_targets.py#L621-L642) bans stale phrasing. Any workflow-string change must update both lists.
- New hook scripts must be added to `REQUIRED_HOOK_SCRIPTS` at [scripts/validate_targets.py:34-40](scripts/validate_targets.py#L34-L40) and registered in three places: [scripts/generate_targets.py:311-366](scripts/generate_targets.py#L311-L366) (Claude `settings.json`), [shared/hooks/hooks.json](shared/hooks/hooks.json) (Copilot, copied approximately verbatim — note that Copilot's file retains `PreCompact` while Codex strips it via [scripts/validate_targets.py:308](scripts/validate_targets.py#L308); the asymmetry is acceptable but must not be silently widened), and [scripts/generate_targets.py:369-416](scripts/generate_targets.py#L369-L416) (Codex `hooks.json`).
- Codex supports `PreCompact`/`PostCompact`, but the current bootstrap strips `PreCompact` from Codex via validator policy. This plan does not add new compaction hooks; new lifecycle gates use shared operational events (`SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`) and track the Codex compaction-validator relaxation as a follow-up.
- Hook scripts always exit 0; blocking is communicated by writing `{"hookSpecificOutput": {"hookEventName": "...", "permissionDecision": "deny", "permissionDecisionReason": "..."}}` to stdout, following the [shared/hooks/scripts/git-protection.sh](shared/hooks/scripts/git-protection.sh) template.
- `TARGET_ID` is **not** uniformly passed — `protect-files.sh` and `session-log.sh` receive it as the first positional arg, but `git-protection.sh` does not (per [scripts/generate_targets.py:341](scripts/generate_targets.py#L341)). New gating hooks need target awareness, so the generator's command construction for the new scripts must explicitly pass `TARGET_ID` as the first arg in all three tool configs. Codex cannot ask for user approval (must `deny`, not `ask`).
- Hook scripts must **fail closed**: the existing `command -v uv >/dev/null 2>&1 || exit 0` pattern in `git-protection.sh:12-14` silently no-ops when `uv` is missing. New gating hooks must NOT depend on `uv` and must NOT silently no-op on missing tools; they must use plain `awk`/POSIX shell (busybox-compatible) for frontmatter parsing and emit `deny` with a clear remediation if a required tool is unavailable.
- **VS Code Copilot hooks ARE fully documented** at [code.visualstudio.com/docs/copilot/customization/hooks](https://code.visualstudio.com/docs/copilot/customization/hooks) (verified May 2026). Supported events: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `SubagentStart`, `SubagentStop`, `Stop`. VS Code Copilot reads BOTH `.github/hooks/*.json` AND `.claude/settings.json` — the bootstrap's existing emission works. **Caveat:** VS Code Copilot ignores `matcher` (hooks fire on all tool invocations regardless). Per-tool filtering must be done inside the hook script itself.
- **OpenAI Codex hooks ARE fully documented** at [developers.openai.com/codex/hooks](https://developers.openai.com/codex/hooks) (verified May 2026). Supported events: `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStop`, `Stop`, `SessionStart`, `SubagentStart`. **Codex DOES support PreCompact AND PostCompact** — the bootstrap's `validate_targets.py:308` that strips PreCompact from Codex is overly conservative and outdated. Default `timeout` is 600 seconds (vs 30 for Claude/Copilot). Hook discovery: `.codex/hooks.json`, `.codex/config.toml` inline `[hooks]`, plus user-scope `~/.codex/`.
- **github.com cloud Copilot DOES support hooks, but with a different execution model.** Current GitHub docs say Copilot cloud agent loads `.github/hooks/*.json` from the cloned repository, runs hooks inside an ephemeral non-interactive Linux sandbox, honors only `bash` or `command` command entries, and does not load `.claude/settings.json` by default. The bootstrap's `.github/hooks/hooks.json` therefore matters for cloud Copilot too, but hook scripts must be portable to the cloud sandbox and cannot rely on local user-level hook config or interactive approvals.
- **GitHub Copilot `agents:` frontmatter field is not in the github.com docs.** Copilot's published agent schema (verified at docs.github.com/en/copilot/reference/custom-agents-configuration) lists `name`, `description`, `target`, `tools`, `model`, `disable-model-invocation`, `user-invocable`, `mcp-servers`, `metadata` — no `agents:` field. The bootstrap's current rendering at [scripts/generate_targets.py:549-552](scripts/generate_targets.py#L549-L552) emits `agents:`; this may be silently ignored by cloud Copilot but may work for VS Code Copilot agent definitions (which can carry custom frontmatter fields). The documented Copilot delegation path is `tools: [agent]` + named-in-body.
- **TodoWrite is not available on github.com cloud Copilot agent** (explicitly stated: "Currently not applicable for cloud agent today, but supported by VS Code"). The TodoWrite-first contract degrades on Copilot cloud only. It works in VS Code Copilot.
- **`SubagentStart` and `SubagentStop` hooks are broadly available** — Claude Code, VS Code Copilot, Copilot cloud, and Codex all support them in some form. The Phase D stretch (per-phase artifact verification) can target all surfaces, not just Claude.
- **`UserPromptSubmit` / user-prompt-submitted hooks are broadly available** — could detect explicit user requests (e.g. "create PR") as a hook signal across supported surfaces. Tracked as a future improvement; not adopted in this plan.
- **Exit code semantics are NOT uniform across all targets.** Use the portable pattern for blocking gates: `exit 0` with documented JSON decision on stdout (`hookSpecificOutput.permissionDecision: "deny"` for PreToolUse, or the event-specific `decision: "block"` form where required). Do not rely on exit code `2` for enforcement across all targets: Claude and Codex can block some events with exit `2`, while GitHub Copilot treats exit `2` as fail-open for most command hooks except specific hook types.
- **Hook payloads differ by surface and event-name style.** New scripts must normalize snake_case and camelCase variants already seen in this repo (`tool_name`/`toolName`, `tool_input`/`toolArgs`, `tool_response`/`toolResponse`, `hook_event_name`/`hookEventName`) and should tolerate PascalCase and lower/camel event names emitted by different Copilot surfaces.

## Goals (verbatim from user)

1. **Dev is the working branch.** All implementation work starts on `dev`; PR to `main` is a manual user decision outside this flow.
2. **Pre-flight on `dev`.** Before starting new work, current branch must be `dev` with a clean working tree (no uncommitted files).
3. **Implementation branch.** Each big plan creates `<plan_name>_implementation` off `dev`.
4. **Orchestrator workflow (mandatory order):** PLAN (concrete plan saved in `.claude/plans/`, delegated to `planner`) → IMPLEMENT (`coder`) → VERIFY (`verifier`) → REVIEW (`reviewer` + `review-pass-adversarial`) → SCORE (with profiles) → DOCUMENT (`documenter`) → learn skill + session log → commit.
5. **PR on explicit user request.** After the last small plan in a big plan is done, and only when the user explicitly asks for it, open a PR to `dev`. Merge is squash. After merge, return to `dev`.
6. **TodoWrite mandatory.** Orchestrator must create a TodoWrite list following the canonical workflow at session start.
7. **Loop on review/verify failure.** If verifier or reviewer report issues, orchestrator updates the TodoWrite list, re-adds IMPLEMENT/VERIFY/SCORE steps, and repeats until score ≥ 90.
8. **Learn + session log are not optional.** Orchestrator must invoke the `learn` skill and write a session log following the canonical template at [shared/templates/session-log.md](shared/templates/session-log.md) (this is the file that ships into `dist/multi-agent/.claude/templates/` and is enforced by `validate_support_files`; the embedded snippet in [shared/session_logs/README.md](shared/session_logs/README.md) is being replaced with a pointer to it — see Phase C).

## Design Overview

### Canonical phase sequence (target-neutral)

```
PRE-FLIGHT (on dev + clean tree)
   ↓
BRANCH (create <plan>_implementation, record originating_branch)
   ↓
For each small plan:
   PLAN (planner → .claude/plans/YYYY-MM-DD_<phase>.md)
      ↓
   ┌→ IMPLEMENT (coder)
   │     ↓
   │  VERIFY (verifier)
   │     ↓
   │  REVIEW (reviewer + review-pass-adversarial)
   │     ↓
   │  SCORE (quality_score.py with profiles)
   │     ↓
   └─ if score < 90 → re-add IMPLEMENT/VERIFY/SCORE to TodoWrite, loop
      ↓ (score ≥ 90)
   DOCUMENT (documenter)
      ↓
   LEARN (learn skill → MEMORY.md updates)
      ↓
   SESSION LOG (Status: COMPLETED, per template)
      ↓
   COMMIT (atomic, one per small plan)
   ↓
(repeat for next small plan)
   ↓
After last small plan + explicit user request:
   PR (gh pr create --base dev, squash merge mode in body)
   ↓
After merge, on next session:
   SessionStart hook detects merged branch, suggests `git checkout dev && git pull`
```

### Enforcement matrix

| Phase | Instructions layer | Metadata layer | Hook layer |
|---|---|---|---|
| PRE-FLIGHT (on dev, clean) | workflow.instructions.md "Branch Lifecycle" | — | `enforce-branch-state.sh` on PreToolUse for `git checkout -b` / `git switch -c` |
| BRANCH | orchestrator/prompt.md step | — | `enforce-branch-state.sh` validates before branch creation; `record-branch-state.sh` writes `originating_branch` after branch creation succeeds |
| PLAN | workflow.instructions.md | `planner` already in delegates | — |
| IMPLEMENT | workflow.instructions.md | `coder` already in delegates | — |
| VERIFY | workflow.instructions.md | `verifier` already in delegates | — |
| REVIEW (primary+adversarial) | workflow.instructions.md, prompt | `reviewer` already; add reviewer's two sub-delegates | — |
| SCORE | workflow.instructions.md (≥ 90 threshold) | — | (enforced indirectly via commit gate) |
| DOCUMENT | workflow.instructions.md, prompt | **`documenter` missing from agent.yaml — must add** | — |
| LEARN | prompt Completion Protocol (exists) | — | enforced indirectly via commit gate (requires `[LEARN]` entries flushed or explicit "no lessons" marker) |
| SESSION LOG | prompt Completion Protocol (exists) | — | `stop-session-log-check.sh` warns; `enforce-commit-gate.sh` requires session log with `Status: COMPLETED` |
| COMMIT | workflow.instructions.md | — | `enforce-commit-gate.sh` on PreToolUse for `git commit` |
| PR | workflow.instructions.md, prompt | — | `enforce-pr-gate.sh` on PreToolUse for `gh pr create` / PR-opening push |
| TodoWrite first | orchestrator/prompt.md (already partially) | — | (not hook-enforceable — relies on prompt + TodoWrite reminder) |
| Resume after merge | workflow.instructions.md | — | `session-start-state.sh` on SessionStart |

### Per-tool enforcement degradation (verified May 2026 docs)

| Layer | Claude Code | Copilot VS Code IDE | Copilot Cloud (github.com) | OpenAI Codex |
|---|---|---|---|---|
| Hooks (PreToolUse / Stop / SessionStart / SubagentStop / etc.) | Authoritative — [docs.claude.com](https://docs.claude.com/en/docs/claude-code/hooks) | Authoritative — [code.visualstudio.com/docs/copilot/customization/hooks](https://code.visualstudio.com/docs/copilot/customization/hooks); reads `.github/hooks/*.json` AND `.claude/settings.json` | **Supported with constraints** — loads `.github/hooks/*.json` only, runs in ephemeral non-interactive Linux sandbox, honors `bash`/`command` entries | Authoritative — [developers.openai.com/codex/hooks](https://developers.openai.com/codex/hooks) |
| Matcher support | Per-tool matchers (e.g. `"Bash"`, `"Edit\|Write"`) | **Ignored** — hooks fire on all tools; per-tool filtering must be in-script | Supported in GitHub hook schema; use script-level filtering anyway because generated hooks use PascalCase and must stay portable | Regex matchers; some events ignore matcher (`UserPromptSubmit`, `Stop`) |
| PreCompact / PostCompact | Yes, both | Yes (PreCompact), PostCompact unclear | `preCompact` fires for auto compaction only; no manual compaction user flow | **Yes, both** (contradicts bootstrap's `validate_targets.py:308`) |
| TodoWrite-first contract | Available | Available | **Unavailable** — explicitly "not applicable for cloud agent today" | Unverified (no `CODEX_TOOL_MAP` in generator) |
| Delegate metadata (`agents:` frontmatter) | Not used (body prose carries it) | Not in cloud Copilot's documented schema; may or may not be honored | Not in documented schema | Not used (body prose carries it) |
| Prompt-prose enforcement (workflow, caveman, semble/context-mode directives) | Strong | Strong | Strong — still needed because cloud hooks are sandboxed/non-interactive and TodoWrite is unavailable | Strong |
| `SubagentStop` for per-phase artifact verification (Phase D stretch) | Available | Available | Available, but must account for cloud sandbox and generated hook file shape | Available |

**Practical consequence:** All four surfaces can run some form of hook enforcement, but Copilot cloud is the most constrained: no local user hook config, ephemeral filesystem, non-interactive decisions, cloud firewall, and no TodoWrite. **Phase B (workflow contract) and Phase G (agent contracts) remain important everywhere and especially in Copilot cloud, but the hook layer is no longer prompt-only there.** The Phase D `SubagentStop` stretch becomes a four-surface enhancement, with extra cloud-sandbox validation.

## Authoritative artifacts

- **Source of truth for workflow text:** [shared/policies/workflow.instructions.md](shared/policies/workflow.instructions.md). Two strings in the generator must mirror it: [scripts/generate_targets.py:451](scripts/generate_targets.py#L451), [scripts/generate_targets.py:513](scripts/generate_targets.py#L513).
- **Orchestrator contract:** [shared/agents/orchestrator/prompt.md](shared/agents/orchestrator/prompt.md) (behavior) and [shared/agents/orchestrator/agent.yaml](shared/agents/orchestrator/agent.yaml) (capabilities + delegates).
- **Plan tracking state:** plan-file frontmatter (no separate state files). Big-plan frontmatter holds `originating_branch`, `implementation_branch`, `started_at`, `phases:`, `current_phase:`, `status`. Small-plan frontmatter holds `parent_plan`, `phase_index`, `status`, `closeout_session_log:` (relative path to the session log that closes this small plan).
- **Small-plan completion signal:** `status: complete` in the small-plan frontmatter, flipped by the orchestrator at the end of LEARN. Human-readable counterpart: session log `Status: COMPLETED` with `Plan:` link. The session log is named via `closeout_session_log:` in the small-plan frontmatter — this resolves the "today" ambiguity for multi-session small plans (the closing session log can be from a different day than the opening session log; the small plan declares which log is its closeout).
- **Score threshold:** **≥ 90** (per user decision). Single threshold for commit (commit happens at small-plan closeout, which is also PR-eligible material). The current ≥80 commit / ≥90 PR distinction in [shared/policies/quality-and-testing.instructions.md](shared/policies/quality-and-testing.instructions.md) (specifically the table at lines 99-104) and [shared/policies/workflow.instructions.md](shared/policies/workflow.instructions.md) lines 53-54 will be flattened to ≥90 everywhere. Note: any new wording must not substring-collide with the existing blocklist phrases at [scripts/validate_targets.py:621-642](scripts/validate_targets.py#L621-L642) (`"Score ≥ 80 = commit"`, `"Score ≥ 90 = PR-ready"`); using "Score ≥ 90 required before commit" or similar avoids both forbidden strings.
- **Quality report file:** `quality_score.py` currently only prints JSON to stdout — **nothing persists**. This plan adds a `--out PATH` flag to [shared/scripts/quality_score.py](shared/scripts/quality_score.py) that writes the JSON to `.claude/quality_reports/score-<ISO-timestamp>.json`. The commit-gate hook reads the newest matching file for the active branch + phase, then validates its metadata and freshness. The orchestrator invokes `quality_score.py` with `--out` set, every time it scores. Without this change, the commit-gate hook has no durable signal to read.
- **Quality report freshness:** persisted score files must identify the branch, phase, base ref, merge-base SHA, current HEAD SHA, dirty status, generated timestamp, and target path. The commit gate must reject a score file that does not match the current implementation branch + current phase, or that is older than any tracked changed file in the pending closeout. This prevents accepting a stale score from a different branch, earlier phase, or pre-fix run.
- **Session log template (canonical):** [shared/templates/session-log.md](shared/templates/session-log.md) is the canonical, shipped artifact (it's the file `validate_support_files` requires under `dist/multi-agent/.claude/templates/`). Phase C rewrites this file to the bullet-based structure currently embedded in [shared/session_logs/README.md](shared/session_logs/README.md); the README is then reduced to a pointer to the template.

## Phase-by-phase changes

### Phase A — Documenter delegate fix

**File:** [shared/agents/orchestrator/agent.yaml](shared/agents/orchestrator/agent.yaml)
- Add `"documenter"` to the `delegates` array (currently lines 12-18, missing the documenter even though prompt.md step 8a delegates to it).
- Regenerate (`uv run python scripts/generate_targets.py --all`); validate (`uv run python scripts/validate_targets.py`); no validator change needed.
- **Verification commands** (all three tools):
  - Copilot: the bootstrap emits an `agents:` frontmatter field at [scripts/generate_targets.py:549-552](scripts/generate_targets.py#L549-L552), but the Copilot agent schema does NOT document this field — it may be silently ignored. Run `grep -A6 'agents:' dist/multi-agent/.github/agents/orchestrator.agent.md` to confirm the bootstrap's emission, then verify the documenter is also named in the **prose body** of the same file (the documented Copilot delegation path is `tools: [agent]` + prose mention).
  - Claude: `grep -i documenter dist/multi-agent/.claude/agents/orchestrator.md` — documenter must appear in the body adapter text.
  - Codex: `grep -i documenter dist/multi-agent/.codex/agents/orchestrator.toml` — documenter must appear in `developer_instructions`.
- **Caveat:** For Claude and Codex, the delegate addition is partially cosmetic — the canonical agent body (`prompt.md`) already names `documenter` in step 8a. For Copilot, the `agents:` field is undocumented; the actual binding to the documenter agent depends on the agent being discoverable under `.github/agents/` AND named in the orchestrator's prose. Do not expect a behavior change on Claude/Codex from this phase alone; on Copilot, the change is best-effort.

### Phase B — Workflow contract rewrite

**File 1:** [shared/policies/workflow.instructions.md](shared/policies/workflow.instructions.md)
- Replace the "Orchestrator Loop" section (current lines 23-62) with the canonical sequence in this plan's Design Overview (PRE-FLIGHT → BRANCH → per-small-plan loop → PR-on-request).
- Add a new "Branch Lifecycle" section: dev as base, clean-tree precondition, `<plan>_implementation` branch naming, squash PR to dev on explicit request, return-to-dev after merge.
- Replace the "Score ≥ 80 / Score ≥ 90" two-tier wording (current lines 53-54) with single "Score ≥ 90 required before commit" wording (avoids substring-collision with the existing forbidden phrases `"Score ≥ 80 = commit"` and `"Score ≥ 90 = PR-ready"` at validator lines 626-627).
- **Remove the "Just do it" mode paragraph** (current line 62) — it's the explicit escape hatch the user wants gone.
- Add a "Loop on review/verify failure" rule: orchestrator must re-add IMPLEMENT/VERIFY/SCORE to TodoWrite and repeat until score ≥ 90.
- Add an "Explicit user request required for PR" rule.

**File 2:** [shared/agents/orchestrator/prompt.md](shared/agents/orchestrator/prompt.md)
- Rewrite the "Core Workflow" section (current lines 16-31) to match the canonical sequence verbatim from workflow.instructions.md.
- Strengthen the existing "Task Tracking (Mandatory)" section (current lines 5-14): require that the very first TodoWrite call enumerates every phase in the canonical order, including a parameterized "VERIFY/REVIEW/FIX/RE-VERIFY/SCORE — repeat until score ≥ 90" task.
- Rewrite "Quality Gates" (current lines 63-67) to single ≥90 threshold (use "≥ 90 required before commit" phrasing, not "= commit").
- Rewrite the closing of the workflow to add: COMMIT phase (atomic, after LEARN + session log), PR-on-user-request phase, return-to-dev guidance.
- Keep "Completion Protocol (Mandatory)" (current lines 69-81) intact; it already covers learn + session log.
- **Codex TodoWrite gap:** Whether Codex agents can call `TodoWrite` is unverified (no `CODEX_TOOL_MAP` entry exists in `generate_targets.py:20-36` analogous to the Claude/Copilot maps). Document in the prompt that TodoWrite-first compliance is mandatory on Claude/Copilot and best-effort on Codex (Codex enforcement degrades to prompt prose). This is acceptable because Codex is the lowest-volume target; budgeted as a known limitation rather than a blocker.

**File 3 (new addition to scope):** [shared/policies/quality-and-testing.instructions.md](shared/policies/quality-and-testing.instructions.md)
- Update the gate-threshold table around lines 99-104 to a single ≥90 row, removing the ≥80 commit row.
- Use phrasing "Score ≥ 90 required" rather than "Score ≥ 80 = Commit" to avoid stale-phrase collisions.

**File 3b (new addition to scope):** [shared/policies/workspace.instructions.md](shared/policies/workspace.instructions.md)
- Update the core-principle documentation gate from "After score ≥ 80" to the single ≥90 gate.
- Update the verification gate table around lines 118-124 to remove the ≥80 commit-ready row and require ≥90 before commit/PR closeout.
- Update the instruction summary string "Plan -> implement -> verify -> review -> score -> document loop" if Phase B changes the canonical phase wording.

**File 4:** [scripts/generate_targets.py](scripts/generate_targets.py)
- Update the hardcoded workflow string at line 451 in `render_root_guidance()` to reflect the new canonical sequence and the single ≥90 gate. Keep it short and stable since it appears in both CLAUDE.md and AGENTS.md.
- Update line 513 in `render_copilot_instructions()` similarly.

**File 5:** [scripts/validate_targets.py](scripts/validate_targets.py)
- Update the "required phrases" list at lines 610-618 to match the new canonical string (must contain the new workflow phase order including DOCUMENT and the new single ≥90 score gate).
- Update the "stale fragments" blocklist at lines 621-642 to **add** the following entries (none of which are currently in the list):
  - `"Just do it"` (the mode label being removed)
  - `"After score >= 80"` and `"After score ≥ 80"` (old documentation gate)
  - `"plan -> implement -> verify -> review -> score -> document workflow"` only if the new wording differs — keep the old exact string in `required_phrases` if not, otherwise add to blocklist
  - `"eligible for commit"` and `"eligible for PR"` if the new wording drops "eligible" language
- Preserve the existing forbidden phrases (the adversarial reviewer confirmed they do not collide with `"Score ≥ 90 required before commit"`).

### Phase C — Templates

**File 1 (canonical, rewritten):** [shared/templates/session-log.md](shared/templates/session-log.md)
- This is the file that ships into `dist/multi-agent/.claude/templates/` and is validated by `validate_support_files`. It currently uses a table-based structure (Session Info, Changes Made, Design Decisions, Verification Results all as tables) that is structurally incompatible with the bullet-based template embedded in [shared/session_logs/README.md](shared/session_logs/README.md).
- **Rewrite this file** to a single canonical bullet-based structure consistent with what the user actually writes in `RAG/.claude/session_logs/*.md`:
  - Frontmatter NOT used (Status is in body, per `^\*\*Status:\*\*\s+(IN-PROGRESS|COMPLETED|BLOCKED)\b` regex)
  - `# Session: [short description]`
  - `**Date:** YYYY-MM-DD`
  - `**Plan:** [link to small-plan file]`
  - `**Status:** IN-PROGRESS | COMPLETED | BLOCKED` (these three values are the only ones the commit-gate hook accepts; case-sensitive)
  - `## Goal`
  - `## Work Log` (timestamped bullet entries)
  - `## [LEARN] Entries` (`[LEARN:category] entry`, or `[LEARN] none - no new lessons this session` to satisfy the loose [LEARN] rule)
  - `## Verification Results` (code block)
  - `## Score: N/100`
  - `## Open Questions / Next Steps`

**File 2 (rewritten):** [shared/session_logs/README.md](shared/session_logs/README.md)
- Remove the embedded template snippet.
- Replace with a short readme that names the canonical template path and the naming convention. Closeout-session-log naming convention documented here: `YYYY-MM-DD_<phase-slug>-closeout.md` for the final session that closes out a small plan (optional but recommended for human readability).

**File 3 (new):** `shared/templates/plan-big.md`
- Frontmatter:

  ```yaml
  ---
  name: <slug>
  type: big-plan
  status: planning | in-progress | complete
  originating_branch: dev
  implementation_branch: <slug>_implementation
  started_at: <ISO-8601-UTC-timestamp-or-empty-until-branch-created>
  phases:
    - <small-plan-slug-1>
    - <small-plan-slug-2>
  current_phase: <small-plan-slug>   # which small plan is currently in flight; advanced by record-commit-closeout.sh after each successful closeout commit
  ---
  ```

- Required sections: `## Context`, `## Goals`, `## Design Overview`, `## Phases`, `## Verification`.
- **Slug regex** (enforced by `enforce-branch-state.sh`): `^[a-zA-Z0-9._-]+$`. Rejects spaces, slashes, colons. The full branch name is `<slug>_implementation`, also validated with `git check-ref-format --branch` after the suffix is appended so Git's real ref rules are authoritative.

**File 4 (new):** `shared/templates/plan-small.md`
- Frontmatter:

  ```yaml
  ---
  name: <YYYY-MM-DD_phase-X-slug>
  type: small-plan
  parent_plan: <big-plan-slug>
  phase_index: 1
  status: in-progress | complete
  closeout_session_log: <relative-path-to-session-log-md>   # required when status flips to complete; resolves multi-session "today" ambiguity
  ---
  ```

- Required sections: `## Scope`, `## Steps`, `## Verification`, `## Closeout Checklist`.

**File 5:** [scripts/validate_targets.py](scripts/validate_targets.py)
- Add a check that both new templates exist under `dist/multi-agent/.claude/templates/`.
- Add a check that the rewritten `shared/templates/session-log.md` has a `**Status:**` line (sanity check the rewrite didn't drop the required field).
- The "active plan frontmatter" runtime validation moves to `scripts/check_runtime.py` (see Phase F).

### Phase D — Quality score persistence, bypass policy, branch & commit gate hooks

**Prerequisite — File 0 (modify):** [shared/scripts/quality_score.py](shared/scripts/quality_score.py)
- Add `--out PATH` CLI flag. When set, write the JSON payload to PATH in addition to stdout.
- Add `--phase PHASE_SLUG` and `--base-ref dev` CLI flags. When `--out` is set inside a git repo, include metadata in the JSON payload: `generated_at`, `branch`, `head_sha`, `base_ref`, `merge_base_sha`, `phase`, `target`, `dirty`, and `changed_files`.
- The orchestrator/coder must always invoke with `--phase <current_phase> --base-ref dev --out .claude/quality_reports/score-$(date -u +%Y%m%dT%H%M%SZ).json`. Document this in [shared/agents/coder/prompt.md](shared/agents/coder/prompt.md) and [shared/agents/verifier/prompt.md](shared/agents/verifier/prompt.md).
- The commit-gate hook reads the newest score file whose metadata matches the active implementation branch and current phase. It parses `score` from JSON and also verifies the score file is newer than every tracked changed file participating in the pending closeout.
- Add `.claude/quality_reports/` to the `.gitignore` block written by the installer (if not already; verify in [scripts/install_bootstrap.py](scripts/install_bootstrap.py)).
- **Without this change, the commit-gate has no signal to read.** This is the single most critical fix from the adversarial review.

**Bypass policy (new section in [shared/policies/workflow.instructions.md](shared/policies/workflow.instructions.md)):**
- Commit subject prefixes that bypass the gate: `fixup!`, `squash!`, `chore(typo):`, `docs(typo):`. These are intended for amend/rebase fixups and trivial doc/typo fixes on an implementation branch.
- All successful bypass commits are written to `.claude/session_logs/hooks-bypass.log` (timestamp, branch, commit subject, target). The PR-gate refuses to open a PR if `hooks-bypass.log` contains entries since the start of the current big plan AND the big plan has no `bypass_acknowledged: true` field in its frontmatter — forcing the user to acknowledge bypasses before the PR opens.
- Env var `CLAUDE_HOOK_BYPASS=1` is **not** supported (too easy to set by accident); only commit-message prefixes.

**File 1 (new):** `shared/hooks/scripts/enforce-branch-state.sh`
- PreToolUse on `Bash` matching `git checkout -b\b` / `git switch -c\b` (use word boundary to avoid false positives on aliases).
- Parse the proposed new branch name from the command (positional arg after `-b` / `-c`).
- Validate new branch name against `^[a-zA-Z0-9._-]+_implementation$` and `git check-ref-format --branch`. Reject malformed slugs with a specific remediation.
- Verify current branch == `dev` (use `git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD`).
- Verify working tree clean (`git -C "$REPO_ROOT" status --porcelain` is empty).
- Verify a big-plan file exists at `.claude/plans/<slug>.md` where slug = new-branch with `_implementation` suffix stripped.
- Verify big-plan frontmatter `status` is `planning` or `in-progress`.
- If all checks pass: emit no decision and allow the git command to run. **Do not mutate frontmatter in PreToolUse**; the branch may still fail to create.
- If any check fails: emit a deny JSON with a specific remediation message naming the failed check.

**File 1b (new):** `shared/hooks/scripts/record-branch-state.sh`
- PostToolUse on `Bash` matching `git checkout -b\b` / `git switch -c\b`.
- Verify the Bash tool result succeeded using the event payload when available; then independently verify `git rev-parse --abbrev-ref HEAD` equals the requested `<slug>_implementation` branch.
- After success is confirmed, update the big-plan frontmatter to record `implementation_branch: <name>`, `originating_branch: dev`, `started_at: <ISO-8601-UTC-timestamp>` if absent, `status: in-progress`, and `current_phase:` set to the first slug in the `phases:` list.
- If the command failed or the current branch does not match the requested branch, do not mutate frontmatter; emit a `systemMessage`/`additionalContext` warning if supported.

**File 2 (new):** `shared/hooks/scripts/enforce-commit-gate.sh`
- PreToolUse on `Bash` matching `git commit\b` (any form).
- **Bypass check (first):** Parse the commit message (`-m` arg or `git commit --file`). If the subject starts with `fixup!`, `squash!`, `chore(typo):`, or `docs(typo):`, emit no decision and allow. No other gates run. Do not append `hooks-bypass.log` here; PostToolUse records the bypass only after the commit succeeds.
- Verify current branch matches `^[a-zA-Z0-9._-]+_implementation$` (block any commits on dev/main with a remediation pointing to the new flow).
- Read the big-plan file's `current_phase:` field to identify the in-flight small plan.
- Read the small-plan file at `.claude/plans/<current_phase>.md`. Verify `status: complete` in its frontmatter.
- Read the small-plan's `closeout_session_log:` field. Open that session log; verify its body contains `^\*\*Status:\*\*\s+COMPLETED\b` (case-sensitive, exact regex). Reject `Status: Done`, `Status: Complete`, lowercase, etc.
- Read the newest `.claude/quality_reports/score-*.json` whose metadata matches the current branch and `current_phase`. Parse `score` from JSON, verify `score >= 90`, and verify the report is newer than every tracked changed file participating in the pending closeout. If no matching quality_report files exist, emit a remediation: "no matching quality report found — run `uv run python .claude/scripts/quality_score.py <target> --phase <current_phase> --base-ref dev --json --out .claude/quality_reports/score-<ts>.json`".
- Verify [LEARN] evidence (loose): either `.claude/MEMORY.md` was modified after the small plan's first-mention mtime, OR the closeout session log contains the line `[LEARN] none - no new lessons this session`.
- If all checks pass: emit no decision and allow the git command to run. **Do not advance `current_phase:` in PreToolUse**; the commit may still fail.
- If any check fails: emit deny JSON listing the failed checks with exact remediation strings.

**File 2b (new):** `shared/hooks/scripts/record-commit-closeout.sh`
- PostToolUse on `Bash` matching `git commit\b`.
- Self-filter bypass commits (`fixup!`, `squash!`, `chore(typo):`, `docs(typo):`), append the bypass entry to `.claude/session_logs/hooks-bypass.log` after success is confirmed, and leave plan state unchanged.
- Verify the Bash tool result succeeded using the event payload when available; then independently verify `git log -1 --format=%s` matches the commit subject parsed from the original command when a subject was available.
- After success is confirmed, update the big-plan `current_phase:` to the next phase in the `phases:` list, or clear it and set `status: complete` if this was the last phase.
- If the commit failed or the latest commit subject cannot be correlated with the intercepted command, do not mutate frontmatter; emit a warning context message where the target supports it.

**File 3 (new helper):** `shared/hooks/scripts/_lib-frontmatter.sh`
- POSIX-shell helpers for reading/writing YAML frontmatter fields. Uses plain `awk` only (no `uv`, no Python dependency, no jq). Busybox-compatible.
- Functions: `fm_read FILE KEY`, `fm_write FILE KEY VALUE`, `fm_has FILE KEY`.
- **Fails closed:** if `awk` is unavailable (which would be exotic but possible in stripped containers), the lib exits 127 with a clear stderr message. Hooks that source this lib propagate the failure as a `deny` decision (do NOT silently allow).
- This lib does NOT use the `command -v uv >/dev/null 2>&1 || exit 0` pattern from `git-protection.sh:12-14` — that pattern is wrong for gating hooks because it silently disables enforcement.

**File 4:** [scripts/generate_targets.py](scripts/generate_targets.py)
- Register the four branch/commit hooks in three places. **Pass `TARGET_ID` as the first positional arg** in all three configs (the existing `git-protection.sh` does not receive `TARGET_ID` — see line 341 — but the new gating hooks need target awareness):
  - `render_claude_settings()` (lines 311-366): add `enforce-branch-state.sh` and `enforce-commit-gate.sh` to `PreToolUse` with matcher `"Bash"`; add `record-branch-state.sh` and `record-commit-closeout.sh` to `PostToolUse` with matcher `"Bash"`.
  - [shared/hooks/hooks.json](shared/hooks/hooks.json): add the same scripts to `PreToolUse` and `PostToolUse`. Copilot surfaces differ in matcher behavior, so every script self-filters to Bash commands.
  - `render_codex_hooks()` (lines 369-416): add PreToolUse hooks with matcher `"Bash"` (or `"*"` plus script filtering if compatibility requires); add PostToolUse hooks with matcher `"Bash"`. Pass `openai-codex` as TARGET_ID.
- Update `render_codex_config()` to emit `[features] hooks = true` instead of deprecated `codex_hooks = true`. Update validator/docs references at the same time.

**File 5:** [scripts/validate_targets.py](scripts/validate_targets.py)
- Add `enforce-branch-state.sh`, `record-branch-state.sh`, `enforce-commit-gate.sh`, `record-commit-closeout.sh`, and `_lib-frontmatter.sh` to `REQUIRED_HOOK_SCRIPTS` (lines 34-40). Note: `_lib-frontmatter.sh` is a library, not an executable — flag it as such in the validator (skip the `chmod +x` check if applicable).
- Add guardrail tests in `validate_hook_guardrails()` (lines 393-499):
  - `git commit` on dev → expect deny.
  - `git checkout -b foo_implementation` with dirty tree → expect deny.
  - `git checkout -b invalid:slug_implementation` → expect deny (slug regex violation).
  - `git commit -m "fixup! whatever"` on `*_implementation` → expect ALLOW (bypass policy).
  - `git commit -m "phase 1 closeout"` on `*_implementation` with all gates met → expect ALLOW.
  - Successful branch creation PostToolUse event → expect big-plan frontmatter updated only after current branch is `foo_implementation`.
  - Failed branch creation PostToolUse event → expect no frontmatter mutation.
  - Successful closeout commit PostToolUse event → expect `current_phase` advances only after HEAD contains the expected commit.
  - Failed closeout commit PostToolUse event → expect no `current_phase` mutation.

**Stretch enhancement (universal — Claude Code, VS Code Copilot, Codex) — `SubagentStop` hook:**
- Docs verification (May 2026) confirmed all four active surfaces support `SubagentStop` (fires when a delegated sub-agent finishes) and `SubagentStart`, with Copilot cloud running inside its constrained sandbox. Sources: docs.claude.com/en/docs/claude-code/hooks, code.visualstudio.com/docs/copilot/customization/hooks, docs.github.com/en/copilot/reference/hooks-reference, developers.openai.com/codex/hooks.
- **Optional addition:** a new `shared/hooks/scripts/enforce-phase-completion.sh` wired to `SubagentStop` in all three configs. When a sub-agent finishes, the hook inspects which agent it was (via the hook-input field that carries the agent identity — `agent_type` on Claude/Copilot, possibly different field on Codex; the script normalizes) and verifies its expected artifact was produced:
  - `planner` finished → small plan file exists in `.claude/plans/` with valid frontmatter
  - `coder` finished → at least one tracked source file changed since the agent started
  - `verifier` finished → fresh `score-*.json` quality report exists (mtime newer than agent start)
  - `reviewer` finished → review notes recorded in session log
  - `documenter` finished → at least one doc file changed
- If artifact is missing, the hook emits a `decision: block` (legacy form) or `permissionDecision: deny` (PreToolUse-style — but SubagentStop uses the `decision: block` continuation form per Codex docs) with the missing-artifact reason.
- Wiring:
  - `render_claude_settings()` ([scripts/generate_targets.py:311-366](scripts/generate_targets.py#L311-L366)) → register on `SubagentStop` with matcher `"*"`.
  - [shared/hooks/hooks.json](shared/hooks/hooks.json) → register on `SubagentStop` (VS Code Copilot ignores matchers).
  - `render_codex_hooks()` ([scripts/generate_targets.py:369-416](scripts/generate_targets.py#L369-L416)) → register on `SubagentStop` with matcher `"*"`.
- Flagged as stretch because (1) the hook-input schema for identifying the finished agent may differ across surfaces and needs probing, (2) artifact-detection heuristics will need empirical tuning, (3) Copilot cloud's ephemeral sandbox can discard hook-side logs unless they are written into repo state or sent externally, and (4) it's not strictly needed to meet the user's stated goals.

### Phase E — PR gate + session state hooks + runtime checks

**File 1 (new):** `shared/hooks/scripts/enforce-pr-gate.sh`
- PreToolUse on `Bash` matching either:
  - `gh pr create\b` (most common path)
  - `git push` from a `*_implementation` branch when the destination appears to publish the current branch (`git push -u origin <branch>`, `git push origin HEAD`, `git push origin <branch>`, or plain `git push` with upstream already configured). This is the likely fallback if `gh` is not installed, and the user might push then open the PR via web UI.
- Verify current branch matches `^[a-zA-Z0-9._-]+_implementation$`.
- Read the matching big-plan file's `phases:` list.
- For each listed phase slug, verify a small-plan file exists with `status: complete`.
- Verify commit count on branch (vs `dev`) ≥ phase count.
- For `gh pr create`: parse `--base` from command; reject if `--base main` or missing (`--base dev` required).
- For implementation-branch `git push`: allow only when ALL small plans are complete; otherwise deny with the message "this push will allow opening a PR via web UI before all phases close out — close out all small plans first, then `gh pr create --base dev`".
- Also reject any `git push --force` or `git push -f` to `*_implementation` (already blocked by `git-protection.sh`; do not duplicate, but document the overlap).
- Check `.claude/session_logs/hooks-bypass.log` for entries newer than the big-plan `started_at` timestamp. If any exist AND the matching big-plan frontmatter lacks `bypass_acknowledged: true`, deny with: "this branch has logged commit-gate bypasses (see hooks-bypass.log); add `bypass_acknowledged: true` to the big plan to acknowledge before opening a PR".
- If all checks pass: exit 0.
- **Residual leaks (acknowledged):** `gh api repos/.../pulls`, the VS Code GitHub PR extension, and the GitHub web UI cannot be blocked by these hooks. The mitigation is a documented recommendation in Phase F docs to enable GitHub branch protection on `dev` requiring approved PRs and status checks — that's the compensating control outside the hook layer.

**File 2 (new):** `shared/hooks/scripts/session-start-state.sh`
- SessionStart event (matcher: `startup|resume|clear` for Codex; no matcher for Claude/Copilot).
- Detect if current branch matches `^[a-zA-Z0-9._-]+_implementation$` and a big-plan file exists.
- If yes: emit a `systemMessage` (or equivalent per-tool mechanism — Claude uses stdout text under `hookSpecificOutput.systemMessage`) reporting:
  - Big plan name and originating branch
  - Phases done / pending (parsed from small-plan `status` fields)
  - `current_phase:` from big-plan frontmatter
  - Last quality score if a recent `score-*.json` file exists
- Detect if the branch was merged upstream (`git -C "$REPO_ROOT" branch -r --merged origin/dev | grep -q <branch>`); if so, emit a suggestion to `git checkout dev && git pull`.

**File 3 (new):** `shared/hooks/scripts/stop-session-log-check.sh`
- Stop event.
- Walk `git status --porcelain` to detect files modified during the session.
- If any source files were modified AND no session log under `.claude/session_logs/YYYY-MM-DD_*.md` was created/updated today, append a loud warning line to `.claude/session_logs/hooks-errors.log`.
- Never block (Stop blocks are intrusive); only warn.

**File 4:** [scripts/check_runtime.py](scripts/check_runtime.py)
- Add `gh` to the `OPTIONAL_BINARIES` list (around line 13). Report status during the runtime check.
- Without `gh`, the user can still run the workflow but PR creation falls back to `git push` + web UI; document this in the check's WARN message: "gh CLI not available; `enforce-pr-gate.sh` will still block common implementation-branch git push paths, but PR opening through the GitHub web UI itself is not gated".
- Update the Codex runtime check from deprecated `[features] codex_hooks = true` to canonical `[features] hooks = true`; keep accepting `codex_hooks` only as backward-compatible legacy output if needed during migration.

**File 5:** [scripts/generate_targets.py](scripts/generate_targets.py)
- Register the three new hooks in all three tool configs:
  - SessionStart hook → `session-start-state.sh`
  - Stop hook → `stop-session-log-check.sh` (Claude already has `hf-ai-sync.sh` on Stop; chain them — ensure ordering so the warning fires even if the HF sync fails)
  - PreToolUse → `enforce-pr-gate.sh` (matcher `Bash` for Claude, no matcher for Copilot, `*` for Codex). Pass `TARGET_ID` as first positional arg.
  - Codex config → use `[features] hooks = true` (canonical) rather than `codex_hooks = true` (deprecated alias).

**File 6:** [scripts/validate_targets.py](scripts/validate_targets.py)
- Add the three new scripts to `REQUIRED_HOOK_SCRIPTS`.
- Add guardrail tests:
  - `gh pr create --base main` from `foo_implementation` → expect deny.
  - `gh pr create --base dev` from `foo_implementation` with incomplete small plans → expect deny.
  - `git push -u origin foo_implementation`, `git push origin HEAD`, and `git push origin foo_implementation` with incomplete small plans → expect deny.
  - `gh pr create --base dev` with bypass-log entries but no `bypass_acknowledged: true` → expect deny.

### Phase F — Plan-frontmatter validator + documentation update

**File 1 (new):** [scripts/validate_plan_frontmatter.py](scripts/validate_plan_frontmatter.py)
- Validates the new schema on any plan file under `.claude/plans/*.md`:
  - Big plans must have `type: big-plan`, `originating_branch`, `implementation_branch`, `phases` (list), `current_phase`, `status` (in: `planning|in-progress|complete`), and `started_at` once status is `in-progress` or `complete`.
  - Small plans must have `type: small-plan`, `parent_plan`, `phase_index`, `status` (in: `in-progress|complete`), and `closeout_session_log` when status is `complete`.
- Returns non-zero on any violation with the file path and specific missing field.
- Invoked by [scripts/check_runtime.py](scripts/check_runtime.py) as part of the optional runtime checks (skipped if `.claude/plans/` is empty).

**File 2:** [scripts/check_runtime.py](scripts/check_runtime.py)
- Add invocation of `validate_plan_frontmatter.py`. Treat schema violations as WARN (not FAIL) so adoption is incremental — users with existing plain plan files don't get blocked, but new plans must conform.

**Files (doc updates):**
- [README.md](README.md) — add a "Branch Lifecycle and Workflow Enforcement" section summarizing the new flow, with a pointer to [shared/policies/workflow.instructions.md](shared/policies/workflow.instructions.md). Include a "Recommended: GitHub branch protection on `dev`" callout naming this as the compensating control for the web-UI PR leak. Also update the current agent list to include `documenter`.
- [docs/architecture.md](docs/architecture.md) — add the new hook scripts to the dispatcher description (current discussion of `run-hook.sh` and the existing five scripts). Include the bypass-policy ladder (`fixup!` / `chore(typo):` / etc.) and the `hooks-bypass.log` audit trail.
- [docs/smoke-tests.md](docs/smoke-tests.md) — update the hardcoded agent-count expectations from 8 to the actual shared-agent count after `documenter` is included in the generated target.
- [AGENTS.md](AGENTS.md) — replace any orchestrator wording that conflicts, including the root summary that currently omits DOCUMENT from the workflow.
- [docs/runtime-checks.md](docs/runtime-checks.md) — mention the new required hook scripts in the runtime check list, the new `gh` optional binary, and the plan-frontmatter validator.

### Phase G — Agent communication contracts (semble/context-mode + caveman)

This is the baseline enforcement layer that works uniformly across all supported agent surfaces, including Copilot cloud where hooks are constrained and TodoWrite is unavailable. It hardens the prompt prose layer without depending on hook-side state.

**Two contracts being added to every agent prompt:**

1. **Retrieval tool routing (mandatory when available):**
   - For repo discovery / "where is X" / behavioral neighborhoods → Semble search
   - For long file reads / large outputs / indexed Q&A → context-mode `ctx_index` + `ctx_search`, or `ctx_execute_file` for files that need processing not reading
   - Direct Read only when path is known and file is small
   - `rg` for exact literal/symbol/error-string searches
   - If `semble` or `context-mode` are unavailable, fall back to direct reads + `rg`; missing helpers are warnings, not blockers (matches existing tool-routing.instructions.md policy)
   - All agents must load [shared/policies/tool-routing.instructions.md](shared/policies/tool-routing.instructions.md) as part of their session bootstrap

2. **Caveman `full` reporting from subagents to orchestrator (mandatory):**
   - The existing pattern in [shared/agents/coder/prompt.md](shared/agents/coder/prompt.md) and [shared/agents/designer/prompt.md](shared/agents/designer/prompt.md) — "Default to `caveman` `full` style for status updates and summaries" — is extended to **every subagent** that reports back to the orchestrator.
   - Caveman compression applies to **prose sections only**. Tables, code blocks, file paths, identifiers, and structured findings stay literal — never compress them. The `caveman/SKILL.md` rules already enforce this.
   - The orchestrator's prompt explicitly instructs subagents: "Use caveman `full` for narrative report sections; preserve tables, code, paths, and structured findings literally."

**Files to update** (per-file additions, not rewrites):

| File | Add semble/context-mode routing? | Add caveman `full` reporting? |
|---|---|---|
| [shared/agents/orchestrator/prompt.md](shared/agents/orchestrator/prompt.md) | YES — "shallow exploration" step (current line 20) routes through semble first, falls back to direct reads | Adds **instruction to subagents** about caveman; orchestrator itself reports normally to the user |
| [shared/agents/planner/prompt.md](shared/agents/planner/prompt.md) | YES — planner reads many files during decomposition; route through context-mode for large reads | YES — terse plan summaries back to orchestrator |
| [shared/agents/coder/prompt.md](shared/agents/coder/prompt.md) | YES — code lookup via semble | Already conforms ("caveman full" — current line 35) — confirm |
| [shared/agents/designer/prompt.md](shared/agents/designer/prompt.md) | YES — same | Already conforms — confirm |
| [shared/agents/verifier/prompt.md](shared/agents/verifier/prompt.md) | YES — context-mode for large test/lint output | YES, but tables stay literal — prose framing only |
| [shared/agents/reviewer/prompt.md](shared/agents/reviewer/prompt.md) | YES — semble for understanding changed code | YES — synthesis prose; finding tables stay literal |
| [shared/agents/review-pass-primary/prompt.md](shared/agents/review-pass-primary/prompt.md) | YES — semble | YES |
| [shared/agents/review-pass-adversarial/prompt.md](shared/agents/review-pass-adversarial/prompt.md) | YES — semble | YES |
| [shared/agents/documenter/prompt.md](shared/agents/documenter/prompt.md) | YES — context-mode for reading large docs | NO — documenter writes prose for human readers; output should be normal, not compressed |

**Wording template** for each agent (target-neutral, gets inserted into each prompt):

```markdown
## Retrieval
Load `.claude/instructions/tool-routing.instructions.md` before searching. Prefer:
- Semble search for repo discovery and behavioral neighborhoods
- context-mode `ctx_index` + `ctx_search` for long files / large outputs
- `rg` for exact literal matches
- direct Read only for known short files
Fall back gracefully if either MCP server is unavailable.

## Reporting back to the orchestrator
Default to `caveman full` style for prose sections of your report (drop filler/articles where safe; fragments allowed). Preserve tables, code blocks, file paths, identifiers, and structured findings literally. Load `.claude/skills/caveman/SKILL.md` if you need a refresher.
```

**Documenter exception:** the documenter writes user-facing documentation, not orchestrator reports. Its retrieval section is added, but the caveman block is omitted (or replaced with: "Reports back in normal prose — caveman is for orchestrator status, not for docs you write").

**Reporting-style instructions update**:
- Do **not** add caveman/reporting rules to [shared/policies/tool-routing.instructions.md](shared/policies/tool-routing.instructions.md); that file should remain the single source of truth for retrieval routing only.
- Add a brief "Subagent reporting style" subsection to [shared/policies/workflow.instructions.md](shared/policies/workflow.instructions.md) or [shared/policies/workspace.instructions.md](shared/policies/workspace.instructions.md), codifying caveman `full` as the default for narrative report sections (currently scattered across coder and designer prompts only).
- Cross-reference the canonical caveman skill location from that workflow/workspace section.

**Validator addition** ([scripts/validate_targets.py](scripts/validate_targets.py)):
- For each agent prompt under `dist/multi-agent/.claude/agents/`, validate that:
  - Body references `tool-routing.instructions.md` (string match), OR loads it via `[[skills.config]]` for Codex
  - Body references caveman (string match) for non-documenter agents
- Skip these checks for the orchestrator (which doesn't report back to itself) and documenter (caveman-exempt).

## Existing functions and utilities to reuse

- **Hook dispatcher and REPO_ROOT resolution:** [shared/hooks/scripts/run-hook.sh](shared/hooks/scripts/run-hook.sh) lines 19-32 — all new scripts will be invoked through this; no need to re-implement REPO_ROOT logic.
- **Blocking pattern:** [shared/hooks/scripts/git-protection.sh](shared/hooks/scripts/git-protection.sh) lines 40-58 — exact template for new git-related blocking hooks (regex match, emit JSON deny, exit 0).
- **Target-aware decisions:** [shared/hooks/scripts/protect-files.sh](shared/hooks/scripts/protect-files.sh) lines 233-247 — pattern for "deny on Codex, ask on Claude/Copilot" if any new hook needs it (most won't; commit/PR blocks are absolute).
- **Quality score JSON parsing:** [shared/scripts/quality_score.py](shared/scripts/quality_score.py) lines 151-189 — the JSON shape (`score`, `gate`, `deductions`) is what `enforce-commit-gate.sh` will parse, extended by Phase D with branch/phase/freshness metadata. Score field is plain int; gate field can be checked against `PR-READY`. **However, the script currently only prints JSON to stdout — Phase D extends it with `--out PATH` to also persist to `.claude/quality_reports/score-*.json`. The commit-gate reads the matching persisted file, not stdout.**
- **Validator guardrail harness:** [scripts/validate_targets.py:393-499](scripts/validate_targets.py#L393-L499) — existing `validate_hook_guardrails()` already simulates hook scripts with mocked tool calls; new hooks plug into the same harness.
- **Frontmatter parsing in shell:** there's no shared helper — new hooks will use `awk` or `python3 -c` for frontmatter parsing. Prefer a tiny helper at `shared/hooks/scripts/_lib-frontmatter.sh` to avoid duplicating awk logic across three new scripts. Sourced via `. "$(dirname "$0")/_lib-frontmatter.sh"`.

## Phase ordering and dependencies

- **A is independent** and lowest risk → do first.
- **B and C are loosely coupled** but the validator changes in B reference template existence checks in C — sequence B before C, or do them together in one small plan if changes are small.
- **D is the critical phase** (commit gate, quality_score.py persistence, bypass policy, `_lib-frontmatter.sh`). Depends on C (commit gate needs plan-file frontmatter parsing). Within Phase D: the `quality_score.py --out` change and `_lib-frontmatter.sh` come first; then the two hooks; then generator/validator wiring.
- **E depends on D** (PR gate reuses commit-gate frontmatter library; session-start-state reads the same big-plan fields).
- **F adds the runtime validator script and docs** — do last after all behavior is locked. The validator script is intentionally warn-only so this phase ships without breaking pre-existing plan files.
- **G can run in parallel with B or C** — it touches per-agent prompt.md files, which are not modified by B (workflow.instructions.md / orchestrator) or C (templates). It depends only on stable references to `tool-routing.instructions.md` and the new workflow/workspace reporting-style section; either order works. Recommended ordering: G after B but before D, so prompt-layer enforcement is in place before the hook layer is finalized.

## Verification

End-to-end smoke test, run after each phase merge:

```bash
# In the bootstrap repo
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py    # should show gh as OPTIONAL with status

# Verify quality_score.py persistence
mkdir -p /tmp/qreports
uv run python shared/scripts/quality_score.py shared/scripts/quality_score.py --skip-tests --phase smoke --base-ref dev --json --out /tmp/qreports/test.json
test -f /tmp/qreports/test.json
uv run python -c 'import json; print(json.load(open("/tmp/qreports/test.json"))["score"])'  # must print a score

# Manual: in a scratch consumer repo with dist/multi-agent/ installed
cd /tmp/scratch-consumer-repo
git checkout -b foo_implementation             # should DENY (no big-plan file)
git checkout -b "with:colon_implementation"   # should DENY (slug regex violation)
echo "..." > .claude/plans/foo.md              # add minimal big-plan with frontmatter
git checkout -b foo_implementation             # should ALLOW; after successful PostToolUse, big-plan frontmatter updates with implementation_branch/originating_branch/current_phase

# Commit-gate negative tests
git commit --allow-empty -m "test"             # should DENY (not on *_implementation? actually we ARE; deny because no session log/score/LEARN)
git commit --allow-empty -m "fixup! typo"      # should ALLOW (bypass); bypass logged to hooks-bypass.log
git commit --allow-empty -m "chore(typo): readme"  # should ALLOW (bypass)

# Commit-gate positive path
# 1. write small-plan with status: complete and closeout_session_log: <path>
# 2. write session log with **Status:** COMPLETED and [LEARN] entries
# 3. run quality_score.py --phase <current_phase> --base-ref dev --out .claude/quality_reports/score-<ts>.json (score ≥ 90, metadata matches branch/phase, report newer than pending changes)
git commit -m "phase 1 closeout"               # should ALLOW; after successful PostToolUse, big-plan current_phase advances

# Verify "Status: Done" / "Status: complete" (wrong case) are rejected
sed -i 's/COMPLETED/Done/' .claude/session_logs/<closeout>.md
git commit -m "phase 1 closeout"               # should DENY (regex mismatch)

# PR-gate tests
gh pr create --base main                       # should DENY (base must be dev)
gh pr create --base dev                        # should DENY if any phase still in-progress
git push -u origin foo_implementation         # should DENY if any phase still in-progress (common web-UI bypass path)
git push origin HEAD                          # should also DENY if any phase still in-progress
# … flip all phases to status: complete …
git push -u origin foo_implementation         # should ALLOW
gh pr create --base dev                        # should ALLOW
# After bypass with no acknowledgement
echo "test" >> .claude/session_logs/hooks-bypass.log
gh pr create --base dev                        # should DENY (unacknowledged bypass); fix by adding bypass_acknowledged: true to big-plan
```

Per-tool parity check after each generator change:

```bash
# Inspect what got generated for each tool
ls dist/multi-agent/.claude/hooks/scripts/     # Claude (canonical)
cat dist/multi-agent/.claude/settings.json      # Claude hook registrations
cat dist/multi-agent/.github/hooks/hooks.json   # Copilot hook registrations
cat dist/multi-agent/.codex/hooks.json          # Codex hook registrations
diff <(jq -r '.hooks | keys[]' dist/multi-agent/.claude/settings.json | sort) \
     <(jq -r '.hooks | keys[]' dist/multi-agent/.codex/hooks.json | sort)
```

Validate orchestrator delegates propagation:

```bash
grep -A6 'agents:' dist/multi-agent/.github/agents/orchestrator.agent.md
# expected: planner, coder, designer, reviewer, verifier, documenter
```

## Decisions (locked) and remaining assumptions

**Decisions confirmed with the user:**

1. **Score threshold = ≥90** for both commit and merge eligibility (single gate). Aligns with the existing PR-READY label in [shared/scripts/quality_score.py](shared/scripts/quality_score.py).
2. **PR creation only.** Orchestrator runs `gh pr create --base dev` with a body recommending squash-merge. User merges via GitHub UI. Orchestrator does **not** run `gh pr merge --squash` and does **not** auto-delete the branch.
3. **[LEARN] requirement is loose.** Commit-gate hook accepts either MEMORY.md modified this session OR session log containing an explicit `[LEARN] none - no new lessons this session` marker.

**Decisions made during adversarial review (locked):**

4. **Quality reports persist to disk with freshness metadata.** `quality_score.py --out PATH --phase <current_phase> --base-ref dev` writes JSON to `.claude/quality_reports/score-<ts>.json` including branch, phase, base ref, merge-base SHA, HEAD SHA, dirty status, generated timestamp, target, and changed files. Commit-gate reads the newest matching file for the active branch + phase and rejects stale reports. Without this change, the commit-gate has nothing trustworthy to read; this is the most critical addition from the review.
5. **Bypass policy = commit-message prefix only.** `fixup!`, `squash!`, `chore(typo):`, `docs(typo):` bypass the commit-gate. Every successful bypass commit is logged to `.claude/session_logs/hooks-bypass.log` by PostToolUse after the commit succeeds. The PR-gate refuses to open a PR if unacknowledged bypasses exist on the branch (requires `bypass_acknowledged: true` in big-plan frontmatter). No env var bypass — too easy to set by accident.
6. **"Today" semantics resolved via small-plan `closeout_session_log:` field.** The small-plan frontmatter declares which session log closes it. The commit-gate reads that specific log, not "most recent log modified today" — fixes multi-day small plans.
7. **Canonical session log file = `shared/templates/session-log.md`** (the one `validate_support_files` already ships). It gets rewritten to the bullet-based structure; `shared/session_logs/README.md` is reduced to a pointer.
8. **Status regex is exact and case-sensitive:** `^\*\*Status:\*\*\s+(IN-PROGRESS|COMPLETED|BLOCKED)\b`. "Done", "complete", lowercase variants are rejected.
9. **Slug regex:** `^[a-zA-Z0-9._-]+$`. Branch = `<slug>_implementation`; both the regex and `git check-ref-format --branch` are validated by `enforce-branch-state.sh`.
10. **`_lib-frontmatter.sh` is fail-closed.** Plain `awk`/POSIX (busybox-compatible), no `uv` dependency. If `awk` is missing the lib exits 127 with stderr; gating hooks propagate as `deny` (do NOT use the silent-no-op pattern from `git-protection.sh:12-14`).
11. **Web-UI PR leak is unfixable in hooks.** The plan blocks `gh pr create` AND common implementation-branch `git push` forms (`git push -u origin <branch>`, `git push origin HEAD`, `git push origin <branch>`, plain upstream push) to close the most common bypass paths, but `gh api`, the VS Code GitHub PR extension, and the GitHub web UI cannot be intercepted once a branch is already published. Documented compensating control: GitHub branch protection on `dev` requiring approved PRs and status checks.
12. **`gh` is OPTIONAL, not required.** Added to `OPTIONAL_BINARIES` in `check_runtime.py`. Workflow degrades gracefully (push gate still works).

**Remaining assumptions** (calling out so they can be challenged at review):

13. **`dev` branch is assumed to exist** in the consumer repo. Adoption is a one-time manual step; the bootstrap installer is not modified to auto-create `dev`.
14. **Big-plan slug = filename minus `.md` extension.**
15. **Small-plan completion authority = frontmatter, not session log.** `status: complete` in the small-plan file is the gate; the session log's `Status: COMPLETED` is the human-facing record that must agree.
16. **TodoWrite enforcement is prompt-only.** Hooks cannot see whether the model called TodoWrite at session start. On Codex the enforcement is even weaker because no `CODEX_TOOL_MAP` exists in the generator — TodoWrite availability is unverified for Codex; treated as best-effort. Documented as a known limitation.
17. **Frontmatter writes from hooks happen in the harness process, not necessarily the agent sandbox.** PostToolUse record hooks can mutate big-plan frontmatter after successful branch/commit commands even when the calling agent is otherwise constrained. This is unusual but intentional; PreToolUse hooks validate only and must not mutate workflow state.

**Decisions made during docs-verification pass (May 2026, locked):**

18. **github.com cloud Copilot enforcement is hook-capable but constrained.** Cloud Copilot agents can run repository `.github/hooks/*.json` hooks inside an ephemeral non-interactive Linux sandbox. They do not load `.claude/settings.json` by default, and `ask` decisions are not interactive. The bootstrap continues to emit `.github/hooks/hooks.json` for both VS Code and cloud Copilot, while Phase B (workflow contract) + Phase G (agent contracts) remain the fallback for gaps such as TodoWrite unavailability and web-UI actions outside the agent.
19. **Copilot `agents:` field is best-effort.** Not in cloud Copilot's documented schema. The bootstrap continues to emit it; the canonical delegation path is `tools: [agent]` + named-in-body. Phase A is treated as "completeness of bootstrap emission" rather than "guaranteed behavior change on cloud Copilot".
20. **TodoWrite-first contract is mandatory on Claude Code and VS Code Copilot, best-effort on cloud Copilot (unavailable) and Codex (unverified).** The orchestrator prompt prose still mandates it; on environments where it's unavailable, the orchestrator falls back to writing the phase checklist as the first response paragraph.
21. **`SubagentStop` per-phase verification is a universal stretch** (Claude Code + VS Code Copilot + Copilot cloud + Codex). Earlier revisions marked this as Claude-only; the docs check confirmed all active surfaces support some form of `SubagentStop`. The plan still ships without it (artifact-detection heuristics need empirical tuning), but the wiring becomes all-surface, not single-tool.
22. **Codex supports `PreCompact` and `PostCompact`.** The bootstrap's existing `validate_targets.py:308` rejection of PreCompact for Codex is overly conservative (verified at [developers.openai.com/codex/hooks](https://developers.openai.com/codex/hooks)). Relaxing this validator is **out of scope for this plan** but worth noting — tracked as a follow-up.
23. **Copilot hook surfaces need script-level filtering.** VS Code Copilot ignores `matcher` in hook configs; Copilot cloud has its own hook schema and payload naming. Per-tool filtering (e.g. "only fire on Bash") must be done inside the hook script itself for all Copilot surfaces. Claude and Codex respect matchers, so we still emit them for those two tools, but the hook scripts must self-filter to stay portable.
24. **Semble + context-mode usage is mandatory in agent prompts but graceful in execution.** Every agent's prompt instructs use; runtime falls back to direct Read / `rg` if the MCP servers are unavailable (matching existing tool-routing policy that flags them as OPTIONAL).
25. **Caveman `full` mode is mandatory for subagent prose reports**, exempt for documenter (writes user-facing docs) and orchestrator (talks to the user, not subagents).

## Out of scope

- Auto-merge of PRs (manual user action on GitHub side).
- Auto-rebase of `<plan>_implementation` branches against `dev` (manual rebase if `dev` moved during work).
- Multi-repo coordination (each consumer repo independent).
- Changes to `main` branch policy or PR flow from `dev` → `main`.
- Renaming of existing skills (`plan-decomposition`, `iterative-plan-review`, `learn`) or agents — they stay as-is.
- New review profiles or quality_score.py rubric/threshold changes (existing rubric stays; only the `--out` flag is added).
- Closing the web-UI PR-creation leak. Mitigated by GitHub branch protection (documented in Phase F), not by hooks.
- Verifying Codex TodoWrite availability. Treated as best-effort prompt enforcement; if Codex doesn't expose TodoWrite, the canonical phase sequence still applies via the orchestrator prompt's prose contract.
- Conversation-state introspection from hooks (i.e. "did the model call TodoWrite first?"). Out of scope because the harness does not expose this.
- **Modernizing per-tool agent frontmatter to use newly-documented fields.** Claude Code now supports `skills:` (preload), `mcpServers:` (per-agent), `permissionMode:` (e.g. `plan`), `isolation: worktree`, `maxTurns`. Copilot now supports `disable-model-invocation` (replacing deprecated `infer`), `user-invocable`, `mcp-servers` (cloud only), `metadata`, `target`. Adopting these would significantly strengthen enforcement (e.g. `permissionMode: plan` would force orchestrator into plan mode automatically), but each requires generator + validator + per-agent decisions. Tracked as a follow-up plan: `agent-frontmatter-modernization`.
- **Refreshing Copilot's allowed-model list.** [scripts/validate_targets.py:29-33](scripts/validate_targets.py#L29-L33) currently allows `"GPT-5.4"`, `"Claude Opus 4.6"`, `"Claude Sonnet 4.6"`. Verified May 2026 list includes additional models (`Claude Opus 4.7`, `Claude Haiku 4.5`, `Gemini 3.1 Pro`, etc.). Out of scope for this plan; tracked separately.
- **Adopting Claude Code Agent Teams (experimental).** A coordinated multi-session team primitive exists but is experimental and disabled by default. Out of scope.
- **Adopting `UserPromptSubmit` / user-prompt-submitted hook** (available on Claude, VS Code Copilot, Copilot cloud, and Codex per May 2026 docs, with event naming differences) for detecting "user said PR". Could replace the "explicit user request" prose contract with a hook-detected signal across supported surfaces. Out of scope; the prose contract is sufficient for now.
- **Relaxing the Codex PreCompact rejection** at [scripts/validate_targets.py:308](scripts/validate_targets.py#L308). Codex docs confirm both `PreCompact` and `PostCompact` are supported. The validator change is small but out of scope here — tracked as a follow-up.
- **Adopting VS Code Copilot's per-agent `hooks` frontmatter field**. VS Code Copilot allows `hooks` in `.agent.md` frontmatter for per-agent enforcement (verified May 2026). Could enable phase-specific hooks attached to individual sub-agents. Out of scope for this plan.
