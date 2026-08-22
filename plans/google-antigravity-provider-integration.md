---
name: google-antigravity-provider-integration
type: big-plan
status: complete
originating_branch: dev
implementation_branch: google-antigravity-provider-integration_implementation
started_at: 2026-08-20T15:02:59Z
phases:
  - 2026-08-20_phase-A-antigravity-provider-and-static-adapters
  - 2026-08-20_phase-B-antigravity-hook-runtime-and-safety
  - 2026-08-20_phase-C-antigravity-installer-and-native-acceptance
---

# Big Plan: Google Antigravity provider integration

## Context

The bootstrap currently generates one `multi-agent` distribution for GitHub Copilot, Claude Code, and OpenAI Codex.

Add Google Antigravity as another provider adapter without creating a second distribution and without duplicating the canonical workflow, agents, skills, policies, MCP registry, hook safety rules, or AI-state lifecycle.

The integration must use current Antigravity native surfaces where they are documented and verified:

- workspace custom agents: `.agents/agents/`;
- workspace skills: `.agents/skills/`;
- workspace MCP: `.agents/mcp_config.json`;
- workspace hooks: `.agents/hooks.json`;
- workspace rules: `.agents/rules/` only if the exact serialized rule metadata is verified;
- root `AGENTS.md` as shared provider-neutral guidance.

The repository currently has six cross-provider base roles:

- `orchestrator`;
- `planner`;
- `coder`;
- `verifier`;
- `reviewer`;
- `documenter`.

It also has Codex-only derived roles:

- `luna_coder`;
- `sol_coder`.

Those Codex-only roles remain Codex-only. Antigravity must not accidentally render them.

This plan adds one Antigravity-only derived implementation role:

- `antigravity_flash_coder`.

It reuses the canonical `coder` prompt and provides a low-cost first implementation tier before escalation to the canonical Antigravity `coder` on `pro`.

## Prerequisite: land the writing/communication plan first

The `humanize-avoid-ai-writing-upstream-integration` work is being implemented before this plan.

Start this plan only after that work is merged into `dev`.

At PRE-FLIGHT:

1. update/rebase from current `dev`;
2. re-read the current generator, root guidance, reporting policy, documenter prompt, and target validation;
3. preserve all user-facing communication and documenter-`humanize` behavior added by that plan;
4. integrate Antigravity on top of those changes;
5. do not restore stale versions of `AGENTS.md`, `CLAUDE.md`, `scripts/generate_targets.py`, or reporting/documentation policy.

If the completed writing plan changes a file path named below, use the live `dev` path as authority.

## Approved execution note

These plans have already been reviewed and decomposed.

Do not delegate a planner merely to restate or split them. If the workflow mechanically requires planner delegation, use a confirmation-only pass. Redesign only when current `dev` or the installed Antigravity client proves a material assumption wrong.

The three phase boundaries are intentional:

1. provider contract and static adapters;
2. hook/security runtime;
3. installer ownership and real native acceptance.

Do not split the static adapter work into separate agent/skills/MCP phases.

## Goals

- Keep one `multi-agent` target.
- Add `google-antigravity` as a supported agent target/provider adapter.
- Keep six cross-provider canonical roles.
- Keep `luna_coder` and `sol_coder` Codex-only.
- Add one Antigravity-only `antigravity_flash_coder`.
- Use Flash first for bounded implementation and Pro as the only automatic coder escalation.
- Use Pro for orchestrator, planner, canonical coder fallback, and reviewer.
- Use Flash for verifier and documenter.
- Render exact documented Antigravity tool names only.
- Render persistent Antigravity agents from canonical role metadata.
- Preserve provider-neutral root `AGENTS.md`.
- Copy canonical skills rather than authoring an Antigravity-specific skill set.
- Render workspace MCP from `shared/mcp/servers.json`.
- Preserve specialist access to workspace MCP using verified Antigravity inheritance semantics.
- Keep native rules optional for v1 if exact on-disk activation metadata is not verified.
- Add Antigravity hooks through one normalization boundary that reuses existing guard logic.
- Hard-deny protected writes and dangerous Git operations in `PreToolUse`.
- Add file-granular `.agents/` installer ownership.
- Preserve unrelated user-authored `.agents/` files.
- Prove important behavior in an installed native `agy` client, not only through generated-file tests.
- Preserve all existing Copilot/Claude/Codex behavior.

## Non-goals

- No second top-level target.
- No Teamwork Preview dependency.
- No `flash_lite`.
- No user-global `~/.gemini/` mutation.
- No duplicated canonical agents, policies, skills, MCP registry, or guard rules.
- No guessed Antigravity tool names.
- No guessed native rule metadata.
- No fake `UserPromptSubmit` equivalent.
- No replacement of durable Git-hook/state-sync behavior with best-effort Antigravity lifecycle events.
- No Antigravity mapping for `todo` unless a real semantic equivalent is documented later.
- `manage_task` is not treated as the bootstrap `todo` capability; it manages background tasks.
- No Antigravity mapping for `vscode`.
- No exact concrete Gemini model claim when Antigravity exposes only a tier.
- No performance benchmark framework in this integration.
- No automatic escalation beyond Flash -> Pro for Antigravity coding.

## Model and routing design

Antigravity custom agents support model tiers `inherit`, `flash`, and `pro`.

Use this bootstrap mapping:

| Role | Antigravity tier | Purpose |
|---|---|---|
| `orchestrator` | `pro` | workflow/delegation decisions |
| `planner` | `pro` | architecture and decomposition |
| `antigravity_flash_coder` | `flash` | first-line bounded implementation |
| `coder` | `pro` | stronger implementation/recovery |
| `verifier` | `flash` | deterministic/tool-driven verification |
| `reviewer` | `pro` | independent adversarial review |
| `documenter` | `flash` | bounded documentation work |

Gemini 3.7 Flash is explicitly intended for coding and agentic workflows and reports strong coding/terminal results in Google's August 2026 model card. This justifies trying Flash as the first implementation tier. The Antigravity `flash` tier must still be treated as a tier, not assumed to resolve to one exact concrete model unless the runtime proves it.

### Flash -> Pro implementation routing

Follow the same design principles as the existing Codex low-cost coder path, but keep the Antigravity route to two tiers.

`antigravity_flash_coder`:

- `targets: ["google-antigravity"]`;
- `prompt_base: "coder"`;
- model intent `flash`;
- escalation target `coder`.

The canonical `coder` has Antigravity model intent `pro` and no further Antigravity escalation.

Default to `antigravity_flash_coder` for an approved, bounded implementation packet.

Route directly to `coder` (`pro`) when the implementation still contains an unresolved:

- architecture decision;
- interface contract;
- root-cause question;
- security decision;
- migration/data-loss decision;
- ownership/lifecycle decision.

Flash must return a structured escalation handoff instead of inventing those decisions when it cannot proceed safely.

Automatic escalation is allowed only once and only for an implementation-attributable blocker/failure.

Do not escalate for:

- missing dependencies;
- unavailable services;
- credentials;
- permission/sandbox restrictions;
- unrelated baseline failures;
- flaky/unreproduced failures;
- missing context the orchestrator can supply.

A Pro coder failure stops automatic model escalation and returns control to the orchestrator/user.

## Provider agent design

Antigravity custom agents live at:

```text
.agents/agents/<name>/agent.md
```

Expected Antigravity adapters:

```text
orchestrator
planner
antigravity_flash_coder
coder
verifier
reviewer
documenter
```

Do not render:

```text
luna_coder
sol_coder
```

Visibility:

- every custom adapter: `mainAgent: false`;
- six specialists: `subagent: true`;
- custom `orchestrator`: `subagent: false`.

The native default agent is the main thread and receives the orchestration
contract through root `AGENTS.md`. This approved compatibility deviation
replaces the original custom-main-agent design: in `agy` 1.1.17, a custom main
agent could not invoke a workspace custom subagent, while the default native
agent could. Do not require hidden specialists to be selectable as primary
agents.

Use `inheritMcp: true` for specialists if the installed/current Antigravity schema supports it as documented in the current changelog. Native acceptance must prove a specialist can use a workspace MCP tool or record the exact verified limitation.

## Capability contract

Build one exact Antigravity mapping from canonical abstract capabilities.

Verified native candidates include:

| Canonical capability | Antigravity tools |
|---|---|
| `read` | `view_file`, `list_dir`, `find_by_name` |
| `search` | `grep_search` |
| `edit` | `write_to_file`, `replace_file_content`, `multi_replace_file_content` |
| `execute` | `run_command` |
| `delegate` | `invoke_subagent`, `send_message`, `manage_subagents` |
| `web` | `search_web`, `read_url_content` |

Explicitly unmapped:

- `todo`;
- `vscode`.

Do not map `manage_task` to `todo`; Google documents it as a background-task controller.

Unknown emitted native tool names are a generation/validation error. Google documents that an invalid custom-agent tool name can hang a subagent.

## Root guidance

Current `AGENTS.md` is emitted inside the Codex renderer. Antigravity also consumes root `AGENTS.md`.

Move conceptual ownership of provider-neutral `AGENTS.md` to the shared/multi-agent rendering layer so it is written once and shared by Codex and Antigravity.

Provider-specific details remain under `.codex/` and `.agents/`.

Preserve the user-facing communication contract that exists on `dev` after the `avoid-ai-writing` plan lands.

## Skills

Render canonical `shared/skills/` into:

```text
.agents/skills/
```

Do not create a second authored skill tree.

Keep the existing source ownership in `shared/skills/`.

## Rules

Google documents workspace rules under `.agents/rules/` and the concepts Manual, Always On, Model Decision, and Glob, but current public documentation does not expose enough exact serialized activation metadata for this plan to require generated native rules safely.

For v1:

- do not guess native rule frontmatter/metadata;
- keep always-needed provider-neutral guidance in `AGENTS.md`;
- keep canonical policies under `.claude/instructions/` and load them through agent prompts/skills as today;
- add `.agents/rules/` only if the installed client/current official documentation exposes the exact on-disk schema during Phase A.

Failure to verify rule serialization does not block the provider integration.

## MCP

Render the canonical `shared/mcp/servers.json` registry into:

```text
.agents/mcp_config.json
```

Use Antigravity's documented `mcpServers` schema.

Do not create a second MCP registry.

Workspace MCP discovery is required. Runtime availability of optional local servers follows existing fallback behavior.

## Hooks and safety

Render:

```text
.agents/hooks.json
```

Use one provider normalization boundary.

Required v1 security path:

```text
Antigravity PreToolUse JSON
    -> Antigravity adapter/normalizer
    -> existing canonical protection logic
    -> Antigravity allow/deny JSON
```

Do not duplicate protected-path patterns or dangerous-Git policy.

Google documents:

- `PreToolUse` hard `deny`;
- `PostToolUse`;
- `PreInvocation`;
- `PostInvocation`;
- `Stop`;
- `invocationNum` as the 0-indexed model invocation number;
- `Stop.fullyIdle`;
- `Stop.terminationReason`;
- `modelName` in common hook fields.

Do not spend implementation time rediscovering these documented field definitions. Native probing is only for cadence/order and how they behave in this bootstrap workflow.

## Installer ownership

`.agents/` is a shared user namespace.

The installer owns only generated bootstrap paths/files.

It must preserve unrelated user-authored files such as:

```text
.agents/skills/company-private/SKILL.md
```

Do not own/delete the whole `.agents/` tree.

`AGENTS.md` is shared by Codex and Antigravity. Removal/prune logic must not assume Codex is its only consumer.

Use the current `scripts/runtime_ownership.py` and `scripts/install_bootstrap.py` implementation as the source of truth when this phase begins.

## Phases

### Phase A — Provider contract and static adapters

Plan:

```text
2026-08-20_phase-A-antigravity-provider-and-static-adapters.md
```

Merge the old contract/model, agents/root guidance, and skills/rules/MCP work into one phase.

Key gate:

- correct provider-target metadata;
- Flash -> Pro coder route;
- exact tool names;
- seven expected Antigravity agents;
- no Codex-only agent leakage;
- provider-neutral root guidance;
- skill/MCP generation;
- no guessed rules.

### Phase B — Hook runtime and safety

Plan:

```text
2026-08-20_phase-B-antigravity-hook-runtime-and-safety.md
```

Keep hook/security integration separate because a defect can bypass protected-file or Git guardrails.

Key gate:

- `PreToolUse` denies unsafe operations before execution;
- protocol output remains valid JSON;
- existing policy is reused;
- lifecycle mappings are only added where native cadence is proved.

### Phase C — Installer ownership and native acceptance

Plan:

```text
2026-08-20_phase-C-antigravity-installer-and-native-acceptance.md
```

Merge installer ownership and final/native verification.

Key gate:

- safe fresh/update/restore semantics;
- user `.agents/` content preserved;
- real `agy` default-agent delegation accepts the generated specialist adapters;
- Flash and Pro routing is observed from client-provided evidence where available;
- Flash -> Pro escalation works;
- specialist MCP use is checked;
- existing providers remain unchanged.

## Repository-wide acceptance

Before parent completion:

- all three small plans are complete;
- full tests/type/lint/format/generation/runtime checks pass;
- generated output is deterministic;
- no existing provider regression remains;
- native Antigravity evidence in a disposable consumer records completed checks
  and any remaining external acceptance gaps;
- documentation describes only behavior that was actually proved;
- final findings satisfy the repository's push/PR gates;
- quality score >= 90;
- final AI-state closeout is published through the normal durable state-sync path.

## References

Bootstrap:

- https://github.com/Ghisso/github_copilot_bootstrap/tree/dev
- https://github.com/Ghisso/github_copilot_bootstrap/blob/dev/scripts/generate_targets.py
- https://github.com/Ghisso/github_copilot_bootstrap/blob/dev/scripts/runtime_ownership.py
- https://github.com/Ghisso/github_copilot_bootstrap/blob/dev/shared/policies/workflow.instructions.md

Google Antigravity:

- https://antigravity.google/docs/subagents
- https://antigravity.google/docs/hooks
- https://antigravity.google/docs/skills
- https://antigravity.google/docs/rules-workflows
- https://antigravity.google/docs/mcp
- https://antigravity.google/changelog

Gemini 3.7 Flash:

- https://deepmind.google/models/model-cards/gemini-3-7-flash/
