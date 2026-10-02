---
type: architecture
title: Agent roster, prompts, and the skill library
description: How the bootstrap defines each specialist agent once under shared/agents, renders it into GitHub Copilot, Claude Code, OpenAI Codex, and Google Antigravity adapters and into the sidecar's workflow profile, routes review profiles, and validates the shared skill library.
tags: [agents, skills, prompts, review-profiles, generation, validation]
verified:
  - by: openwiki/0.5.2
    at: 2026-10-02T14:20:50.150Z
sources:
  - id: openwiki-source-aedfa38e00652688559a19c4
    resource: repo://scripts/generate_targets.py
  - id: openwiki-source-71fc4d2e4c5527b7b8a068ba
    resource: repo://scripts/validate_targets.py
  - id: openwiki-source-ec8523003261d0fba9ffc89a
    resource: repo://shared/agents/antigravity_flash_coder/agent.yaml
  - id: openwiki-source-f31a67de52a2fd7dd5d4484c
    resource: repo://shared/agents/coder/agent.yaml
  - id: openwiki-source-b397cd38b7af4d0c49c77993
    resource: repo://shared/agents/coder/prompt.md
  - id: openwiki-source-5cc3c80e7d4c70a9288dc99f
    resource: repo://shared/agents/luna_coder/agent.yaml
  - id: openwiki-source-4e810ead2bce9272eff7a8fa
    resource: repo://shared/agents/orchestrator/agent.yaml
  - id: openwiki-source-d2263c0776c9d71ecd3760cf
    resource: repo://shared/agents/orchestrator/prompt.md
  - id: openwiki-source-869fc2d8dd56f006523bcc67
    resource: repo://shared/agents/orchestrator/workflow-prompt.md
  - id: openwiki-source-ba6a39790d4410301d299af2
    resource: repo://shared/agents/planner/prompt.md
  - id: openwiki-source-277d57d25696ddfa72249dd2
    resource: repo://shared/agents/planner/workflow-prompt.md
  - id: openwiki-source-fd43a5fc69056375b46b4386
    resource: repo://shared/agents/reviewer/prompt.md
  - id: openwiki-source-ed5529d66aa4a666e3003ed9
    resource: repo://shared/agents/reviewer/workflow-prompt.md
  - id: openwiki-source-fa7286655feb8d4301c96b64
    resource: repo://shared/agents/sol_coder/agent.yaml
  - id: openwiki-source-f11e4ce184d9addc83c16d26
    resource: repo://shared/hooks/scripts/_lib-frontmatter.sh
  - id: openwiki-source-9fa38289fd921baabf765923
    resource: repo://shared/policies/workflow.instructions.md
  - id: openwiki-source-66b9be26404846b939fba828
    resource: repo://shared/policies/workspace.instructions.md
  - id: openwiki-source-ac6151a0e717fb82e280dbaf
    resource: repo://shared/scripts/record_findings.py
  - id: openwiki-source-a931d0171c8876319a735abf
    resource: repo://shared/skills/debug-investigator/SKILL.md
  - id: openwiki-source-3f83db488140df5d5a38535a
    resource: repo://shared/templates/skill-template.md
  - id: openwiki-source-d2aea9dc34db53f2030dc7a0
    resource: repo://tests/test_validate_targets.py
generated: { by: "claude-code", at: "2026-10-02T14:20:50.150Z" }
---

# Agent roster, prompts, and the skill library

Source, tests, and the policies under `shared/policies/` outrank this page.

Every agent is defined once under `shared/agents/<id>/` and rendered into a native adapter for each host it is eligible for. Skills live once under `shared/skills/` and are copied to every host the same way. The generator does the rendering, and the target validator refuses output that breaks the contract.

## How one agent definition becomes four adapters

This diagram shows what the generator reads for one agent and what it writes per host.

```mermaid
flowchart LR
    Y[agent.yaml] --> L[load_shared_agents]
    P[prompt.md] --> L
    S[provider supplement] --> L
    L --> C[.claude/agents/id.md]
    L --> G[.github/agents/id.agent.md]
    L --> X[.codex/agents/id.toml]
    L --> A[.agents/agents/id/agent.md]
    W[workflow-prompt.md] --> K[sidecar workflow profile]
    K --> C
```

An agent directory holds two kinds of file:

- `agent.yaml`, which holds JSON metadata despite its name: `id`, `description`, `role_type`, `visibility`, `capabilities`, optional `delegates`, optional `targets`, optional `prompt_base`, and a `model_intent` object.
- One or more prompt bodies: a canonical `prompt.md`, or a provider supplement named `prompt.openai-codex.md` or `prompt.google-antigravity.md`.
- For the five canonical agents, a `workflow-prompt.md`: a complete, self-contained relaxed prompt that the sidecar's `workflow` profile ships instead of `prompt.md`. It names no verifier, receipt, checkpoint, or hook, and the target validator checks that with a forbidden-token list. The full install never reads it.

The generator's `load_shared_agents` parses every `agent.yaml`, validates it, requires unique ids, and checks prompt composition before anything renders. That validation is code, not policy: a bad metadata file stops generation.

## The metadata contract

`validate_agent_metadata` in `scripts/generate_targets.py` enforces these rules:

- Unknown fields are rejected.
- `id`, `description`, `role_type`, and `visibility` are required. `visibility` is `public` or `hidden`.
- `capabilities` come from a fixed vocabulary (`read`, `search`, `edit`, `execute`, `delegate`, `todo`, and a few more).
- `delegates` must be stable agent ids.
- `model_intent` must have an entry for exactly the targets the agent is eligible for, no more and no fewer.
- An agent that omits `targets` is eligible for all four hosts. One that lists them is rendered only there.

## The roster

Five canonical agents are eligible everywhere and each has its own `prompt.md`.

| Agent | Role | Visibility | Note |
| --- | --- | --- | --- |
| `orchestrator` | main-thread lifecycle driver | public | the only agent with `delegates`: `planner`, `coder`, `reviewer`, `documenter` |
| `planner` | phased implementation plans | hidden | |
| `coder` | implementation and focused verification | hidden | its Codex `model_intent` names `sol_coder` as the escalation target |
| `reviewer` | profile-driven review in two passes | hidden | |
| `documenter` | README and docs updates | hidden | |

Three more agents exist for one provider each and are derived from `coder` through `prompt_base`:

- `luna_coder` and `sol_coder` for `openai-codex`.
- `antigravity_flash_coder` for `google-antigravity`.

A derived agent has no `prompt.md`. It carries only its provider supplement, and the generator composes the base prompt plus the supplement at render time.

## Prompt composition rules

Composition is one level deep, and `validate_prompt_composition` enforces it. The generator refuses:

- a `prompt_base` that points at itself, at a missing agent, or at an agent that itself has a `prompt_base`;
- a derived agent that also ships a `prompt.md`;
- an empty supplement;
- a supplement that contains the whole transformed base prompt, so a supplement cannot silently fork the canonical text;
- a supplement file on a canonical agent for a provider that agent is not eligible for.

## What each host receives

- **Claude Code.** `render_claude_agents` writes `.claude/agents/<name>.md` with the frontmatter `claude_agent_frontmatter` builds: `name`, `description`, a `tools` list derived from `capabilities`, optional `model` and `effort` from `model_intent["claude-code"]`, an `agents:` list from `delegates`, `user-invocable: false` for hidden agents, and `disable-model-invocation: true` for the orchestrator. The body is the canonical prompt with target path rewrites.
- **Sidecar workflow profile.** `render_sidecar_workflow_units` writes the same `.claude/agents/<id>.md` for the five canonical agents into `dist/sidecar/workflow/`, with `sidecar_agent_frontmatter`, which is the Claude Code frontmatter with every `mcp__*` tool grant removed because the sidecar ships no MCP configuration, around the agent's `workflow-prompt.md`. No `.github/agents` or `.codex/agents` file ships in that profile. The workflow orchestrator delegates a step only to an agent the session can start, and otherwise does that step itself and labels a self-review as one. The planner and reviewer return their plan or report as reply text, and the agent that asked saves it under `.ai-bootstrap/`, because their tools come from the shared `capabilities` and include no `Write` or `Edit`. These relaxed prompts carry short advisory versions of the checks described under "Requirement authority and evidence" below: the planner names each decisive assumption, the coder reruns the original reproduction after a bug fix, and the reviewer compares the diff against the approved requirements and lists anything it still needs at the end of its report. The [sidecar overlay page](/openwiki/operations/sidecar-overlay.md) covers how those files reach a team-owned repository.
- **GitHub Copilot.** `render_github_agent_adapter` writes a thin pointer: frontmatter with `name`, `description`, tools, an `agents:` list from `delegates`, `user-invocable: false` for hidden agents, and `disable-model-invocation: true` for the orchestrator. The body tells Copilot to read the canonical `.claude/agents/<name>.md`. An agent not eligible for Claude Code gets a self-contained body instead.
- **OpenAI Codex.** `render_codex_agent_adapter` emits TOML with `name`, `description`, optional `model` and `model_reasoning_effort`, a `sandbox_mode` derived from capabilities, and the composed prompt as `developer_instructions`.
- **Google Antigravity.** `render_antigravity_agent_adapter` writes `.agents/agents/<id>/agent.md` with `mainAgent: false`, `subagent: true` for every agent except the orchestrator, the provider model, and `inheritMcp: true` for subagents.

## Review profiles

The `reviewer` carries no checklists in its prompt. It loads one or more profiles from `shared/review-profiles/`, each with its own `## Severity` section, then runs a primary pass and a verification pass that tries to refute each finding. It repeats verification until two passes in a row change nothing, or after at most three rounds.

The ten profiles are `api`, `architecture`, `code`, `config`, `documentation`, `domain`, `performance`, `ponytail`, `security`, and `tests`.

Which profiles apply is decided by the routing table in `shared/policies/workspace.instructions.md`, not by the reviewer:

- Hooks, scripts, generators, and control-plane code always get `code`, `architecture`, `security`, `tests`, and `ponytail`.
- Ponytail review is mandatory for every control-plane or high-risk diff and every multi-file diff. The commit gate enforces this by requiring `ponytail_reviewed=true` in the findings report for such diffs.
- Ponytail is optional only for a single low-complexity documentation file or a single workflow-state file.

## Requirement authority and evidence

The approved plan or spec, its non-goals, and its approved scope-change records are the authority for required behavior. Specialists compare against that authority instead of rebuilding requirements from the diff.

- **Orchestrator.** Every delegation packet carries the approved requirements, non-goals, and scope-change records. The reviewer packet also carries the verification results already obtained, such as the coder's rerun of the original reproduction.
- **Reviewer.** Pass 1 checks that every in-scope behavior has an implementation and evidence, and that nothing unapproved was added. An approved scope change replaces the requirement it changes, and a valid alternative implementation is not a deviation. Missing material behavior is an ordinary finding at the existing severity; the reviewer never invents a requirement.
- **Open requests.** The reviewer cannot pause to ask a question. It lists missing requirements or execution evidence under an optional `### Open Requests` section and answers `WARN` instead of `PASS`. The orchestrator answers each request with the result or the plain reason it cannot be produced, then reruns the review; a request answered with a reason closes as an unverified limitation. Open requests never enter the findings JSON, and an empty `[]` means a clean review only when no request is open.
- **Planner.** In full-plan mode, Phase 1 lists each decisive assumption (one that would invalidate the design if false) and settles it from code, docs, or a bounded experiment before phases are split. An experiment never authorizes production changes, and an unresolved assumption stays explicit or blocked. Phase 2 asks the user only about preferences, and Phase 4 cites the existing contracts and the test strategy.
- **Coder and debugging.** After a bug fix, the coder and the `debug-investigator` skill rerun the original reproduction and record the outcome or why it could not be rerun. A green test suite alone does not count as that check. The `tests` profile also checks that expected values do not come from the implementation under test.

Section-scoped key-phrase tests in `tests/test_validate_targets.py` check that this guidance ships in the shared source and in the generated Claude Code, Codex, and sidecar output. They prove the text is present, not that a model follows it.

## The skill library

Skills live under `shared/skills/<name>/SKILL.md`. At the time of writing there are 55: 40 with `visibility: public` and 15 with `visibility: background`.

- Public skills are invoked by name.
- Background skills are loaded by matching their `description`, which is why two skills may not share a description.
- `shared/templates/skill-template.md` is the starting shape: `name`, `visibility`, `description`, an optional `argument-hint`, then Problem, Trigger Conditions, and Solution sections.

Two skills are special:

- `ponytail` and `ponytail-review` are adapted third-party skills. The validator requires them to ship, stay public, and keep `license: MIT`, with the upstream LICENSE and provenance under `.claude/third_party/ponytail/`. The workflow policy requires the coder to apply `ponytail` in `full` mode once per coding task.
- `humanize` adapts the third-party `avoid-ai-writing` skill. The generated target must expose only `humanize`, never the upstream name.

### How skills reach each host

- Claude Code: `copy_skills` copies `shared/skills/` into `.claude/skills/` and rewrites target paths inside `.md`, `.py`, and `.sh` files.
- Codex: `.codex/config.toml` gains one `[[skills.config]]` entry per skill, each pointing at `../.claude/skills/<name>/SKILL.md`.
- Antigravity: a plain copy of the tree under `.agents/skills/`.

There is one library, rendered three ways.

### What the validator enforces on skills

`shared_skill_integrity_errors` in `scripts/validate_targets.py` treats these as hard failures:

- every skill directory has a root `SKILL.md` (`SKILL_MISSING_ROOT`);
- frontmatter is flat YAML with matched `---` delimiters, no tabs, and no duplicate keys (`SKILL_FRONTMATTER_INVALID`);
- frontmatter `name` equals the directory name (`SKILL_NAME_MISMATCH`);
- `visibility` is `public` or `background`, and `description` is non-empty and unique across the library;
- a backtick-quoted path naming a known repository root or a `references/` path must resolve to a real file (`SKILL_BROKEN_REFERENCE`). Bare filenames and glob patterns are not checked.

`validate_skills_and_paths` adds the target-level checks: the generated skill count equals the shared count, the Ponytail and humanize contracts hold, and the generated documenter prompt still references `humanize`. Semantic skill quality is left to the `deep-audit` skill on purpose.

## Representative tests

`tests/test_validate_targets.py` covers the agent loader's refusals (invalid target scope, non-object metadata, prompt-base cycles, copied base prompts, supplements on ineligible providers), target-scoped rendering (a Codex-only agent renders only to Codex; a GitHub-only agent embeds its prompt), the exact Codex coder specialist metadata, and the stale-skill contract checks.

## Related pages

- [Source, generated output, consumer repo, and nested AI state](/openwiki/architecture/source-generated-consumer-layout.md)
- [Task lanes and the enforced lifecycle](/openwiki/workflows/lifecycle-and-task-lanes.md)
- [Sidecar overlay](/openwiki/operations/sidecar-overlay.md)
- [Deterministic verification](/openwiki/operations/deterministic-verification.md)
