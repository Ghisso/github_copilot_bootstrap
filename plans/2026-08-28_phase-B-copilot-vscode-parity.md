---
name: 2026-08-28_phase-B-copilot-vscode-parity
type: small-plan
parent_plan: paused-push-copilot-vscode-parity
phase_index: 2
# status must occur exactly once: in-progress | paused | complete | cancelled
status: complete
closeout_session_log: .claude/session_logs/2026-08-29_copilot-vscode-parity.md
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---
# Small Plan: 2026-08-28_phase-B-copilot-vscode-parity

## Scope

Bring the existing GitHub Copilot **VS Code** adapter up to the current repository contract with the minimum native changes. Remove current exact Copilot model pins, use the existing `target-default` inheritance sentinel, expose the configured MCP retrieval servers to search-capable Copilot agents, and render existing delegation/visibility intent with current VS Code custom-agent fields.

Do not implement Copilot CLI/cloud support and do not create a cross-provider model-routing abstraction. Use `ponytail/SKILL.md` in `full` mode. Run review profiles `code`, `architecture`, `security`, `tests`, and `ponytail`.

### Required Skills

- `.claude/skills/ponytail/SKILL.md` — `full`
- `.claude/skills/ponytail-review/SKILL.md`
- `.claude/skills/humanize/SKILL.md` — `edit`, docs profile for documentation
- `.claude/skills/commit/SKILL.md` at closeout

### Verified VS Code Contracts

Checked 2026-08-28:

- https://code.visualstudio.com/docs/agent-customization/custom-agents
- https://code.visualstudio.com/docs/agents/run/subagents
- https://docs.github.com/en/copilot/concepts/models/auto-model-selection

Use these verified facts:

- omitted `model` -> current VS Code model-picker selection;
- a model list is ordered availability fallback, not semantic complexity routing;
- `agents: []` prevents subagent use; an explicit list restricts allowed subagents;
- if `agents:` is present, `agent` must be in `tools`;
- `user-invocable: false` hides an agent from the picker but keeps subagent/programmatic access;
- `disable-model-invocation: true` blocks general model-driven subagent invocation;
- a coordinator can explicitly list an otherwise protected child;
- `<server-name>/*` includes all tools of an MCP server;
- Auto is a user/session model choice; no documented VS Code custom-agent field provides per-agent `fast/deep` classes or adaptive reasoning effort.

### Primary Files

Modify:

- `shared/agents/orchestrator/agent.yaml`
- `shared/agents/planner/agent.yaml`
- `shared/agents/coder/agent.yaml`
- `scripts/generate_targets.py`
- `scripts/validate_targets.py`
- `README.md`
- `docs/runtime-checks.md`

Reference, normally unchanged:

- `shared/agents/reviewer/agent.yaml`
- `shared/agents/verifier/agent.yaml`
- `shared/agents/documenter/agent.yaml`
- `shared/mcp/servers.json`
- `shared/policies/tool-routing.instructions.md`
- `scripts/check_native_clients.py`

Regenerate; never hand-edit `dist/multi-agent/**`.

## Steps

- [ ] **1. Replace current Copilot pins with the existing inheritance sentinel.**
  - Owner: `coder`
  - Required Skills: `ponytail/SKILL.md` (`full`)
  - Change only `model_intent.github-copilot` in:
    - `shared/agents/orchestrator/agent.yaml`
    - `shared/agents/planner/agent.yaml`
    - `shared/agents/coder/agent.yaml`
  - Set each to `"target-default"`.
  - Do not change Claude Code, OpenAI Codex, or Google Antigravity model intent.
  - Confirm `reviewer`, `verifier`, and `documenter` already use `target-default`; leave them unchanged.
  - Do not add `execution`, `tier`, `effort`, `adaptive`, or model-class fields.
  - Preserve current renderer behavior: `target-default` emits no `model:` line.
  - Required documentation boundary: selecting Auto in VS Code makes Auto the session/runtime choice; the bootstrap does not promise a different complexity-routed model for each specialist.
  - Verify:
    ```bash
    uv run python scripts/generate_targets.py --all
    uv run python scripts/validate_targets.py
    ```

- [ ] **2. Complete the existing Copilot VS Code renderer instead of adding a new layer.**
  - Owner: `coder`
  - Required Skills: `ponytail/SKILL.md` (`full`)
  - Modify `scripts/generate_targets.py`.

  **Search/MCP mapping**
  - Replace the obsolete `COPILOT_TOOL_MAP` “KNOWN GAP” comment with the now-verified VS Code wildcard contract.
  - For canonical `search`, render:
    - `search`
    - `semble/*`
    - `context-mode/*`
    - `context7/*`
  - Keep server IDs exactly aligned with `shared/mcp/servers.json`.
  - Do not list Context Mode tools individually; its existing filtered MCP server remains the security boundary.
  - Do not grant these wildcards to agents without canonical `search`.

  **Delegation**
  - Keep current behavior for non-empty canonical `delegates`: emit the exact `agents:` list.
  - When canonical capabilities include `delegate` and canonical `delegates` is empty, emit `agents: []`.
  - This fixes the current planner case: it may retain its existing `agent` tool, but VS Code must not default it to all custom subagents.
  - Agents without `delegate` capability should not get a new `agents:` field.
  - Any rendered `agents:` field must retain the `agent` tool as required by VS Code.

  **Invocation/visibility**
  - Emit `disable-model-invocation: true` for `orchestrator`, matching its existing main-thread/not-delegatable contract.
  - Do not add new canonical metadata for this one stable role; use its existing `id` or `role_type`.
  - Keep orchestrator user-visible and keep its exact specialist `agents:` list.
  - Preserve hidden -> `user-invocable: false`; do not redesign visibility.
  - Do not add handoffs, `target`, agent-scoped hooks, `mcp-servers`, or other fields that are not required here.

  - Verify:
    ```bash
    uv run python scripts/generate_targets.py --all
    uv run python scripts/validate_targets.py
    ```

- [ ] **3. Update `scripts/validate_targets.py` atomically with the renderer.**
  - Owner: `coder`
  - Required Skills: `ponytail/SKILL.md` (`full`)
  - Extend existing GitHub-agent validation; do not add a generic frontmatter framework or dependency.

  **Model checks**
  - Current universal Copilot agents must generate with no `model:` because all current intents are `target-default`.
  - Remove the hand-maintained `GITHUB_ALLOWED_AGENT_MODELS` allow-list and stale-date comment.
  - Keep canonical-vs-generated inheritance/equality checks in the smallest useful form.
  - If current exact Copilot pins are gone, remove `COPILOT_MODEL_PINS`, `validate_model_leaks`, and its `main()` call instead of retaining dead validation.
  - Do not replace them with network lookup, a provider registry, or a new model catalog.
  - Do not globally ban a future intentional exact Copilot model string at schema level; this phase removes current pins, not future capability.

  **Generated metadata checks**
  - For each canonical agent, verify:
    - search-capable -> `search`, `semble/*`, `context-mode/*`, `context7/*`;
    - non-search -> no accidental retrieval wildcard grant;
    - non-empty `delegates` -> exact `agents:` set;
    - `delegate` + empty `delegates` -> `agents: []`;
    - no `delegate` -> no unintended `agents:` field;
    - hidden -> `user-invocable: false`;
    - public -> not hidden;
    - orchestrator -> `disable-model-invocation: true`;
    - non-orchestrators -> no accidental broad application;
    - any `agents:` -> `agent` tool present.
  - Add only focused negative fixtures that prove these checks fail on drift.
  - Prefer a small local frontmatter helper near existing GitHub validation if needed; no PyYAML.

  - Verify:
    ```bash
    uv run python scripts/generate_targets.py --all
    uv run python scripts/validate_targets.py
    ```

- [ ] **4. Correct the Copilot support documentation without broad rewrites.**
  - Owner: `coder`
  - Required Skills: `humanize/SKILL.md` (`edit`, docs profile), `ponytail/SKILL.md` (`full`)
  - In `README.md`:
    - replace “Copilot is compatibility coverage” with first-class **VS Code Copilot custom-agent** support;
    - remove stale exact-model-pin statements;
    - state session model inheritance and the Auto boundary accurately;
    - summarize native delegation/visibility restrictions and shared MCP retrieval access;
    - explicitly exclude Copilot CLI/cloud from this claim.
  - In `docs/runtime-checks.md`:
    - add a compact Copilot VS Code evidence boundary beside the existing native-client sections;
    - structural generation/validation is not native runtime proof;
    - record native evidence only if an authenticated VS Code Copilot test is actually executed.
  - Do not rewrite unrelated provider or runtime sections.
  - Verify:
    ```bash
    uv run python scripts/generate_targets.py --all
    uv run python scripts/validate_targets.py
    uv run python scripts/check_runtime.py
    ```

- [ ] **5. Run one small native VS Code smoke when available; do not build a harness.**
  - Owner: `verifier`
  - Review Profiles: `tests`
  - In an authenticated current VS Code + GitHub Copilot environment, use a disposable generated/installed consumer and **Chat: Open Customizations** / agent diagnostics.
  - Check:
    1. generated agents load without frontmatter/tool errors;
    2. orchestrator is visible;
    3. coder/documenter are hidden;
    4. orchestrator can invoke one explicitly allowed specialist;
    5. orchestrator is not generally offered as a subagent;
    6. planner has no subagents (`agents: []`);
    7. search-capable agent tools show configured MCP server surfaces when available;
    8. with Auto selected, a tiny read-only agent run is not overridden by generated `model:` metadata.
  - Keep the prompt tiny. Do not run a full lifecycle only for metadata proof.
  - If authenticated VS Code is unavailable, record `not run`; do not convert documentation into runtime evidence.
  - Default to **no change** in `scripts/check_native_clients.py`.

- [ ] **6. Run required control-plane review and Ponytail shrink pass.**
  - Owner: `reviewer`
  - Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`
  - Adversarial checks:
    - no current exact Copilot pin remains;
    - docs do not claim list-based complexity routing or per-role Auto;
    - no CLI/cloud claim appears;
    - planner cannot fall back to VS Code's default all-subagent set;
    - orchestrator remains the main entry point;
    - hidden specialists remain available when explicitly allowed;
    - MCP wildcards use exact configured server IDs and do not bypass Context Mode filtering;
    - no new provider-neutral schema, dependency, or unnecessary native harness exists.
  - Run Ponytail review last. Prefer shrinking/deleting helper code if existing renderer/validator branches can express the same contract.

## Expected Generated Contract

| Agent/feature | Expected Copilot VS Code result |
|---|---|
| `orchestrator` model | no `model:` |
| `planner` model | no `model:` |
| `coder` model | no `model:` |
| reviewer/verifier/documenter model | remain inherited; no `model:` |
| search capability | `search` + `semble/*` + `context-mode/*` + `context7/*` |
| orchestrator `agents:` | exact planner/coder/reviewer/verifier/documenter list |
| planner `agents:` | `[]` |
| orchestrator invocation | visible + `disable-model-invocation: true` |
| hidden coder/documenter | `user-invocable: false` |
| model-routing claim | session-selected model; Auto only when selected |
| CLI/cloud claim | none |
| new execution-tier abstraction | none |

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

Persist the normal quality report after the final diff:

```bash
uv run python .claude/scripts/quality_score.py scripts/ \
  --phase 2026-08-28_phase-B-copilot-vscode-parity \
  --base-ref dev \
  --json \
  --out .claude/quality_reports/score-<timestamp>.json
```

Record findings with the actual required profiles, including `ponytail`, through the existing `record_findings.py` workflow.

If the VS Code smoke runs, record VS Code/Copilot versions if exposed, date, target SHA, observed agent metadata behavior, MCP availability, Auto selection, and delegation result. Otherwise record `not run`.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.

Set `status: paused`, record the three pause fields, and create a session log with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it does not require final score, findings, LEARN, DOCUMENT, or a completed closeout.

Because Phase A implements paused remote checkpoints, a valid paused checkpoint for this phase may be pushed to the implementation branch remote without making the plan PR-ready.

Keep the big plan `in-progress` with the same `current_phase`. On resume, read the pause log and Git state, restore this plan to `in-progress`, and continue this same phase without creating another small plan.
