---
type: architecture
title: Agent roster, prompts, and the skill library
description: How the bootstrap defines its specialist agents once in shared/agents, renders each agent into GitHub Copilot, Claude Code, OpenAI Codex, and Google Antigravity adapters, routes review profiles, and validates the shared skill library.
tags: [agents, skills, prompts, review-profiles, generation, validation]
verified:
  - by: openwiki/0.5.2
    at: 2026-09-21T03:23:13.016Z
sources:
  - id: openwiki-source-aedfa38e00652688559a19c4
    resource: repo://scripts/generate_targets.py
  - id: openwiki-source-71fc4d2e4c5527b7b8a068ba
    resource: repo://scripts/validate_targets.py
  - id: openwiki-source-ec8523003261d0fba9ffc89a
    resource: repo://shared/agents/antigravity_flash_coder/agent.yaml
  - id: openwiki-source-f31a67de52a2fd7dd5d4484c
    resource: repo://shared/agents/coder/agent.yaml
  - id: openwiki-source-5cc3c80e7d4c70a9288dc99f
    resource: repo://shared/agents/luna_coder/agent.yaml
  - id: openwiki-source-4e810ead2bce9272eff7a8fa
    resource: repo://shared/agents/orchestrator/agent.yaml
  - id: openwiki-source-fd43a5fc69056375b46b4386
    resource: repo://shared/agents/reviewer/prompt.md
  - id: openwiki-source-fa7286655feb8d4301c96b64
    resource: repo://shared/agents/sol_coder/agent.yaml
  - id: openwiki-source-9fa38289fd921baabf765923
    resource: repo://shared/policies/workflow.instructions.md
  - id: openwiki-source-66b9be26404846b939fba828
    resource: repo://shared/policies/workspace.instructions.md
  - id: openwiki-source-3f83db488140df5d5a38535a
    resource: repo://shared/templates/skill-template.md
generated: { by: "claude-code", at: "2026-09-21T03:23:13.016Z" }
---

# Agent roster, prompts, and the skill library

Source, tests, and the policies under `shared/policies/` outrank this page.
Where this page and the code disagree, the code is right.

## One definition, four targets

Every agent lives in one directory under `shared/agents/<id>/` with two
kinds of file: `agent.yaml`, which despite its name holds JSON metadata, and
one or more prompt bodies. `scripts/generate_targets.py` loads every
`agent.yaml`, validates it, and renders a native adapter for each target the
agent is eligible for. The four supported targets are `github-copilot`,
`claude-code`, `openai-codex`, and `google-antigravity`.

The metadata contract is strict. `validate_agent_metadata` rejects unknown
fields, requires `id`, `description`, `role_type`, and `visibility`
(`public` or `hidden`), checks `capabilities` against a fixed vocabulary
(`read`, `search`, `edit`, `execute`, `delegate`, `todo`, and a few more),
validates `delegates` as stable agent ids, and requires a `model_intent`
entry for exactly the targets the agent is eligible for, no more and no
fewer. An agent that omits `targets` is eligible everywhere; one that lists
them is rendered only there.

## The roster

Five canonical agents are eligible for all four targets and each carries a
canonical `prompt.md`:

| Agent | Role | Visibility | Notes |
|---|---|---|---|
| `orchestrator` | main-thread lifecycle driver | public | the only agent with `delegates`: `planner`, `coder`, `reviewer`, `documenter` |
| `planner` | phased implementation plans | hidden | |
| `coder` | implementation and focused verification | hidden | Codex `model_intent` names `sol_coder` as its escalation target |
| `reviewer` | profile-driven review in two passes | hidden | |
| `documenter` | README and docs updates | hidden | |

Three more agents exist only for one provider and are derived from `coder`
through `prompt_base`: `luna_coder` and `sol_coder` for `openai-codex`, and
`antigravity_flash_coder` for `google-antigravity`. A derived agent has no
`prompt.md` of its own; it carries only a provider supplement file
(`prompt.openai-codex.md` or `prompt.google-antigravity.md`), and the
generator composes base prompt plus supplement at render time.

Prompt composition is deliberately one level deep. `validate_prompt_composition`
refuses a `prompt_base` that points at itself, at a missing agent, or at an
agent that itself has a `prompt_base`; refuses a derived agent that also
ships a `prompt.md`; refuses an empty supplement; and refuses a supplement
that contains the whole transformed base prompt, so a "supplement" cannot
silently fork the canonical text. A supplement file on a canonical agent is
allowed only when that agent is eligible for the matching provider.

## How each target sees an agent

The same metadata renders differently per target:

- **Claude Code** (`render_claude_agents`) writes `.claude/agents/<name>.md`
  with frontmatter `name`, `description`, a `tools` list derived from
  `capabilities`, and optional `model` and `effort` taken from
  `model_intent["claude-code"]`. The body is the canonical `prompt.md` with
  target-specific path rewrites applied.
- **GitHub Copilot** (`render_github_agent_adapter`) writes a thin adapter:
  frontmatter with `name`, `description`, tools, an `agents:` list from
  `delegates`, `user-invocable: false` for hidden agents, and
  `disable-model-invocation: true` for the orchestrator. The body tells
  Copilot to read the canonical `.claude/agents/<name>.md` and follow it.
  An agent that is not eligible for Claude Code gets a self-contained body
  instead, because there is no canonical file to point at.
- **OpenAI Codex** (`render_codex_agent_adapter`) emits a TOML agent with
  `name`, `description`, optional `model` and `model_reasoning_effort` from
  `model_intent["openai-codex"]`, a `sandbox_mode` derived from
  capabilities, and the composed prompt as `developer_instructions`.
- **Google Antigravity** (`render_antigravity_agent_adapter`) writes
  `.agents/agents/<id>/agent.md` with `mainAgent: false`, `subagent: true`
  for every agent except the orchestrator, the model from
  `model_intent["google-antigravity"]`, and `inheritMcp: true` for
  subagents.

`render_multi_agent` runs these renderers in a fixed order after the shared
`.claude/` basis is written, so every adapter points back at the same
canonical files.

## Review profiles

The `reviewer` does not carry checklists in its prompt. It loads one or more
profiles from `shared/review-profiles/` (`api`, `architecture`, `code`,
`config`, `documentation`, `domain`, `performance`, `ponytail`, `security`,
`tests`), each with its own `## Severity` section, and runs at least two
passes: a primary pass that records candidate findings and a verification
pass that tries to refute each one, repeating until a pass changes nothing.

Which profiles apply is decided by the single routing table in
`shared/policies/workspace.instructions.md`, not by the reviewer. Hooks,
scripts, generators, and control-plane code always get `code`,
`architecture`, `security`, `tests`, and `ponytail`. Ponytail review is
mandatory for every control-plane or high-risk diff and every multi-file
diff; it is optional only for one low-complexity documentation file or one
workflow-state file.

## The skill library

Skills live under `shared/skills/<name>/SKILL.md`, 55 of them at the time of
writing: 40 with `visibility: public` and 15 with `visibility: background`.
Public skills are invoked by name; background skills are loaded by matching
their `description`, which is why duplicate descriptions are an error.
`shared/templates/skill-template.md` is the starting shape: frontmatter with
`name`, `visibility`, `description`, and an optional `argument-hint`,
followed by Problem, Trigger Conditions, and Solution sections.

Two skills are structurally special. `ponytail` and `ponytail-review` are
adapted third-party skills: the generator must ship them, they must stay
public, and they must keep their `license: MIT` metadata, with the upstream
LICENSE and provenance copied under `.claude/third_party/ponytail/`. The
workflow policy requires the coder to apply `ponytail` in `full` mode once
per coding task before simplifying and re-verifying the changed scope.
`humanize` is likewise an adaptation of the third-party `avoid-ai-writing`
skill, and the generated target must expose only `humanize`, never the
upstream name.

### How skills reach each target

`copy_skills` copies `shared/skills/` into the target's `.claude/skills/`
and rewrites target-specific paths inside `.md`, `.py`, and `.sh` files.
Codex reaches the same files through `[[skills.config]]` entries in
`.codex/config.toml`, one per shared skill, each pointing at
`../.claude/skills/<name>/SKILL.md`. Antigravity gets a plain copy of the
tree under `.agents/skills/`. There is one skill library, rendered three
ways.

### What the validator enforces

`scripts/validate_targets.py` treats a small set of skill rules as hard
failures, implemented in `shared_skill_integrity_errors`:

- every skill directory has a root `SKILL.md` (`SKILL_MISSING_ROOT`);
- frontmatter is well-formed flat YAML with matched `---` delimiters, no
  tabs, and no duplicate keys (`SKILL_FRONTMATTER_INVALID`);
- frontmatter `name` equals the directory name (`SKILL_NAME_MISMATCH`);
- `visibility` is `public` or `background`, and `description` is non-empty
  and unique across the library;
- a backtick-quoted path that names a known repository root (`.claude/`,
  `shared/`, `scripts/`, `docs/`, `tests/`, and so on) or a `references/`
  path must resolve to a real file (`SKILL_BROKEN_REFERENCE`); bare
  filenames and glob or placeholder patterns are not checked.

`validate_skills_and_paths` adds the target-level checks: the generated
skill count equals the shared count, the Ponytail and humanize contracts
above hold, and the generated documenter prompt still references
`humanize`. Semantic judgments about skill quality are left to the
`deep-audit` skill on purpose; the validator only enforces what can be
decided mechanically.

## Representative tests

`tests/test_validate_targets.py` covers the agent loader's refusals
(invalid target scope, non-object metadata, prompt-base cycles, copied base
prompts, supplements on ineligible providers), target-scoped rendering (a
Codex-only agent renders only to Codex; a GitHub-only agent embeds its
prompt), the exact Codex coder specialist metadata, and the stale-skill
contract checks. Those tests, not this page, define the contract.

## Related pages

- [Source, generated output, consumer repo, and nested AI state](/openwiki/architecture/source-generated-consumer-layout.md)
- [Task lanes and the enforced lifecycle](/openwiki/workflows/lifecycle-and-task-lanes.md)
