---
name: 2026-08-20_phase-A-antigravity-provider-and-static-adapters
type: small-plan
parent_plan: google-antigravity-provider-integration
phase_index: 0
status: in-progress
closeout_session_log:
---

# Phase A: Antigravity provider contract and static adapters

## Scope

Implement all non-hook, non-installer Antigravity provider surfaces in one phase:

- provider/model metadata;
- Flash -> Pro coder routing;
- Antigravity agent rendering;
- provider-neutral root `AGENTS.md`;
- skills;
- MCP;
- optional native rules only if exact serialization is verified;
- focused generation/validation tests.

This intentionally merges the old A/B/C phases. They touch the same generator and validation surfaces and do not justify three independent implementation/review/commit cycles.

Do not implement Antigravity hooks or installer ownership in this phase.

## Pre-flight dependency

This phase starts only after `humanize-avoid-ai-writing-upstream-integration` is merged to `dev`.

Before editing:

1. update/rebase from current `dev`;
2. inspect the current:
   - `scripts/generate_targets.py`;
   - `scripts/validate_targets.py`;
   - `AGENTS.md`;
   - `shared/policies/agent-reporting.instructions.md`;
   - `shared/agents/documenter/prompt.md`;
3. preserve all writing/communication changes from that completed plan;
4. run the current baseline generation/validation/tests.

Do not apply this plan against the older August 14 generator snapshot.

## Approved execution note

This plan has already been reviewed.

Do not use a planner to re-decompose it. If the workflow mechanically requires PLAN delegation, use a confirmation-only planner pass.

## Ownership

### Coder

Own:

- canonical provider metadata;
- derived Antigravity Flash coder source metadata/supplement;
- generator/provider adapters;
- root guidance ownership change;
- skills/MCP rendering;
- optional rule rendering only if exact schema is proved;
- focused tests.

### Verifier

Own:

- provider contract checks;
- generated-file checks;
- model/tool validation;
- no-regression checks;
- focused and full phase verification.

### Reviewer

Use one consolidated reviewer invocation with:

- `code`;
- `architecture`;
- `security`;
- `tests`;
- `ponytail`;
- `documentation` if root/provider documentation changes.

## Design decisions

### 1. Source agent set

Current source contains:

- six cross-provider base roles;
- `luna_coder` and `sol_coder`, both explicitly Codex-only.

Add:

```text
shared/agents/antigravity_flash_coder/
```

as an Antigravity-only derived coder.

Do not modify Luna/Sol eligibility.

Expected Antigravity role set:

```text
orchestrator
planner
antigravity_flash_coder
coder
verifier
reviewer
documenter
```

### 2. Provider identifier

Use:

```text
google-antigravity
```

Add it to the supported agent-target/provider set.

Keep:

```text
TARGETS = ("multi-agent",)
```

No second distribution.

### 3. Antigravity model-intent schema

Define a specific validation branch for `google-antigravity`.

Do not allow it to fall into the current Codex-shaped final `else` branch.

Allowed object fields:

```text
model
escalate_to   # optional, internal bootstrap routing metadata
```

Allowed `model` values:

```text
inherit
flash
pro
```

Do not allow:

```text
flash_lite
effort
```

unless a later plan explicitly adds a verified need.

Model intent:

| Agent | Intent |
|---|---|
| orchestrator | `{ "model": "pro" }` |
| planner | `{ "model": "pro" }` |
| antigravity_flash_coder | `{ "model": "flash", "escalate_to": "coder" }` |
| coder | `{ "model": "pro" }` |
| verifier | `{ "model": "flash" }` |
| reviewer | `{ "model": "pro" }` |
| documenter | `{ "model": "flash" }` |

### 4. Derived-agent composition

The current `prompt_base` implementation is restricted to explicitly Codex-only agents.

Generalize it narrowly to allow **single-provider derived agents**.

Requirements:

- preserve current Luna/Sol behavior byte-for-byte where possible;
- `prompt_base` still cannot be used by a multi-provider agent;
- base role must exist;
- no self-reference;
- no multi-level inheritance;
- provider-specific supplement naming must be deterministic;
- do not duplicate the canonical coder `prompt.md`.

For Antigravity create:

```text
shared/agents/antigravity_flash_coder/agent.yaml
shared/agents/antigravity_flash_coder/prompt.google-antigravity.md
```

The supplement should mirror the useful bounded-task/escalation contract from `luna_coder` without mentioning Codex/Luna.

The Flash coder must return a structured escalation object when the implementation packet contains an unresolved design/root-cause/security/migration/ownership blocker.

### 5. Orchestrator routing supplement

Add an Antigravity-specific orchestrator supplement, for example:

```text
shared/agents/orchestrator/prompt.google-antigravity.md
```

It must define:

- default bounded implementation -> `antigravity_flash_coder`;
- direct `coder` Pro route when the task is not safely bounded;
- one automatic Flash -> Pro escalation;
- failure attribution:
  - `implementation`;
  - `environment`;
  - `baseline`;
  - `indeterminate`;
- only `implementation` triggers automatic model escalation;
- Pro failure stops automatic escalation;
- no retries at the same tier;
- no hidden third tier.

Do not modify the Codex Luna/Terra/Sol supplement except for shared composition infrastructure required to support provider supplements.

### 6. Flash rationale

Do not require a new benchmark.

Use the published Gemini 3.7 Flash model card as the rationale for a Flash-first bounded coder:

- explicitly intended for coding and agentic workflows;
- strong reported production-code and terminal-agent results.

Treat this as a bootstrap starting policy, not proof that every coding task should use Flash.

Native Phase C verifies tier routing and basic viability.

### 7. Agent frontmatter

Render workspace agents under:

```text
.agents/agents/<agent-id>/agent.md
```

Use documented fields only.

Visibility:

- orchestrator:
  - `mainAgent: true`;
  - `subagent: false`;
  - `model: pro`.
- all specialists:
  - `mainAgent: false`;
  - `subagent: true`;
  - model from canonical intent.

Do not require hidden specialists to appear as selectable primary agents in `/agents`.

Use `inheritMcp: true` for specialists if supported by the current installed/doc schema. Current Antigravity changelog documents the field for Markdown custom agents.

Do not invent a substitute if native validation rejects it; resolve the current schema and keep the plan's requirement that specialists receive usable MCP access.

### 8. Exact tool mapping

Add one Antigravity tool map using only documented names:

```text
read:
  view_file
  list_dir
  find_by_name

search:
  grep_search

edit:
  write_to_file
  replace_file_content
  multi_replace_file_content

execute:
  run_command

delegate:
  invoke_subagent
  send_message
  manage_subagents

web:
  search_web
  read_url_content
```

Explicitly unmapped:

```text
todo
vscode
```

`manage_task` is not a `todo` replacement. It controls background tasks.

Unknown abstract capabilities must not silently guess a tool.

Unknown emitted native tool names must fail validation.

### 9. Provider-neutral root `AGENTS.md`

Current `AGENTS.md` is emitted by `render_codex()`.

Change ownership so provider-neutral root guidance is written once by the shared/multi-agent rendering layer and is available to both Codex and Antigravity.

Requirements:

- preserve existing Codex content/behavior except where wording is intentionally provider-neutral;
- preserve the user-facing simple-language contract from the preceding writing plan;
- keep provider-specific runtime details under `.codex/` or `.agents/`;
- do not create two writers for the same root file.

### 10. Skills

Copy canonical:

```text
shared/skills/
```

to:

```text
.agents/skills/
```

Use the existing generic copy/transform mechanisms where possible.

Do not create Antigravity-specific authored copies.

### 11. Rules

Do not let rules block v1.

Current public docs describe rule locations and activation concepts but not enough exact serialized activation metadata to justify guessing.

Default outcome for this phase:

- no generated `.agents/rules/` unless the installed/current official docs expose exact on-disk metadata;
- required always-on guidance remains in `AGENTS.md`;
- canonical detailed policies remain under `.claude/instructions/` and are loaded through prompts/skills.

If exact native rule serialization is verified cheaply, add a narrow renderer and semantic tests. Otherwise record the deliberate fallback and continue.

### 12. MCP

Render:

```text
.agents/mcp_config.json
```

from:

```text
shared/mcp/servers.json
```

Use documented top-level:

```json
{
  "mcpServers": {}
}
```

Preserve canonical Semble, Context Mode, and Context7 source ownership.

Do not create a second MCP registry.

Phase A structural acceptance must prove configuration parity. Phase C proves one specialist can use MCP where an optional local server is available.

## Expected source files

Expected changes include:

```text
shared/agents/orchestrator/agent.yaml
shared/agents/orchestrator/prompt.google-antigravity.md
shared/agents/planner/agent.yaml
shared/agents/coder/agent.yaml
shared/agents/verifier/agent.yaml
shared/agents/reviewer/agent.yaml
shared/agents/documenter/agent.yaml

shared/agents/antigravity_flash_coder/agent.yaml
shared/agents/antigravity_flash_coder/prompt.google-antigravity.md

scripts/generate_targets.py
scripts/validate_targets.py
tests/test_validate_targets.py
```

Other focused tests are allowed if the current checkout has a better location.

Do not hand-edit `dist/`.

## Steps

- [ ] Rebase/update from post-writing-plan `dev` and run baseline checks.
- [ ] Reconfirm current Antigravity custom-agent schema/tool names from official docs and installed client.
- [ ] Add `google-antigravity` provider eligibility.
- [ ] Add explicit Antigravity model-intent validation.
- [ ] Add six base-role Antigravity model intents.
- [ ] Add `antigravity_flash_coder` derived agent.
- [ ] Generalize `prompt_base` only as needed for single-provider derived agents.
- [ ] Add Antigravity orchestrator/coder routing supplements.
- [ ] Add exact tool mapping and explicit unmapped capability handling.
- [ ] Render seven Antigravity custom agents.
- [ ] Move root `AGENTS.md` to shared/multi-agent ownership.
- [ ] Render canonical skills into `.agents/skills/`.
- [ ] Render canonical MCP into `.agents/mcp_config.json`.
- [ ] Add native rules only if exact serialized schema is proved; otherwise keep the explicit fallback.
- [ ] Add focused semantic validation and regression tests.
- [ ] Generate all targets and inspect diff.
- [ ] Run one consolidated review.
- [ ] Close the phase with one commit.

## Focused validation

Tests must prove at least:

- `google-antigravity` is a supported agent target;
- six base roles have valid Antigravity intent;
- Luna/Sol remain only `openai-codex`;
- `antigravity_flash_coder` is only `google-antigravity`;
- Flash coder escalates only to canonical `coder`;
- canonical Antigravity `coder` is Pro with no further escalation;
- invalid Antigravity model tiers fail;
- Antigravity rejects `effort`;
- invalid/unknown native tool names fail;
- `todo` and `vscode` emit no guessed tools;
- exactly seven Antigravity agent adapters are emitted;
- visibility/subagent flags are correct;
- provider-neutral `AGENTS.md` is emitted once;
- Codex root guidance remains valid;
- `.agents/skills/` is generated from canonical skills;
- `.agents/mcp_config.json` parses and matches canonical server keys;
- no rules are guessed when exact schema is unavailable;
- existing provider target output still validates.

Avoid whole-file snapshots where semantic parsing is possible.

## Verification

Run focused checks first, then:

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
```

Use current checkout commands if the configured tool invocation differs.

## Acceptance criteria

- [ ] One `multi-agent` target remains.
- [ ] `google-antigravity` is an explicit provider target.
- [ ] Six base roles are Antigravity-eligible.
- [ ] Luna/Sol remain Codex-only.
- [ ] `antigravity_flash_coder` exists as Antigravity-only derived role.
- [ ] Default bounded coding route is Flash.
- [ ] Automatic coder escalation is Flash -> Pro once.
- [ ] Orchestrator/planner/reviewer/canonical coder use Pro.
- [ ] Verifier/documenter use Flash.
- [ ] No `flash_lite`.
- [ ] No guessed tool name or capability mapping.
- [ ] Seven Antigravity agents render with valid frontmatter.
- [ ] `AGENTS.md` is provider-neutral and preserves the completed writing-plan communication contract.
- [ ] Canonical skills render under `.agents/skills/`.
- [ ] Canonical MCP renders under `.agents/mcp_config.json`.
- [ ] Specialist MCP inheritance is represented using a current verified mechanism.
- [ ] Rules are either generated from proved schema or explicitly deferred with no guessed metadata.
- [ ] Existing provider generation passes unchanged.
- [ ] Full phase verification passes.
- [ ] One phase commit is created.

## References

- https://github.com/Ghisso/github_copilot_bootstrap/blob/dev/scripts/generate_targets.py
- https://github.com/Ghisso/github_copilot_bootstrap/tree/dev/shared/agents
- https://antigravity.google/docs/subagents
- https://antigravity.google/docs/hooks
- https://antigravity.google/docs/skills
- https://antigravity.google/docs/rules-workflows
- https://antigravity.google/docs/mcp
- https://antigravity.google/changelog
- https://deepmind.google/models/model-cards/gemini-3-7-flash/
