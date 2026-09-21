---
type: quickstart
title: "Quickstart: where to look for what"
description: A routing map from common tasks in the github_copilot_bootstrap repository to the wiki page that explains the mechanism and the source files that are authoritative for it.
tags: [quickstart, routing, navigation, authority]
verified:
  - by: openwiki/0.5.2
    at: 2026-09-21T03:23:13.016Z
sources:
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
  - id: openwiki-source-aedfa38e00652688559a19c4
    resource: repo://scripts/generate_targets.py
  - id: openwiki-source-9fa38289fd921baabf765923
    resource: repo://shared/policies/workflow.instructions.md
  - id: openwiki-source-b7cd6d01f37550e855f61bdc
    resource: repo://shared/scripts/verify.py
generated: { by: "claude-code", at: "2026-09-21T03:23:13.016Z" }
---

# Quickstart: where to look for what

This wiki is derived context. Source under `shared/`, `scripts/`, and
`tests/`, and the policies under `shared/policies/`, outrank every page
here. When a page and the code disagree, the code is right, and the page
should be refreshed, never hand-edited.

## Orientation in one paragraph

This repository is a source-of-truth plus generated bootstrap for AI coding
agents. Maintainers edit `shared/`; `scripts/generate_targets.py --all`
renders it into `dist/multi-agent/`; `scripts/install_bootstrap.py`
installs that into a consumer, whose `.claude/` becomes a nested Git
repository on the `ai-state` branch. Hooks enforce a plan-driven lifecycle
and `shared/scripts/verify.py` produces the receipts the commit and push
gates check.

## Route by task

| I want to... | Read | Then look at |
|---|---|---|
| understand what lives where and why `dist/` and `.claude/` are ignored | [Source, generated output, consumer repo, and nested AI state](/openwiki/architecture/source-generated-consumer-layout.md) | `README.md`, `docs/architecture.md`, `scripts/generate_targets.py` |
| classify a request, start a phase, or close one out | [Task lanes and the enforced lifecycle](/openwiki/workflows/lifecycle-and-task-lanes.md) | `shared/policies/workflow.instructions.md`, `shared/templates/plan-small.md` |
| understand why a commit, push, or PR was denied | [Deterministic verification](/openwiki/operations/deterministic-verification.md) then [Hook dispatcher and guardrail scripts](/openwiki/architecture/hooks-and-guardrails.md) | `shared/scripts/verify.py`, `shared/hooks/scripts/enforce-commit-gate.sh`, `docs/runtime-checks.md` |
| add or change an agent, a review profile, or a skill | [Agent roster, prompts, and the skill library](/openwiki/architecture/agents-and-skills.md) | `shared/agents/<id>/agent.yaml`, `shared/skills/<name>/SKILL.md`, `scripts/validate_targets.py` |
| add or change a hook or guardrail | [Hook dispatcher and guardrail scripts](/openwiki/architecture/hooks-and-guardrails.md) | `shared/hooks/scripts/`, `shared/hooks/hooks.json`, the hook wiring in `scripts/generate_targets.py`, `tests/test_hook_gates.py` |
| install into a consumer, refresh one, or refresh this repository's own overlay | [Installing the bootstrap, file ownership, and runtime drift checks](/openwiki/operations/install-ownership-and-runtime-checks.md) | `scripts/install_bootstrap.py`, `scripts/runtime_ownership.py`, `scripts/update_consumers.py` |
| understand or debug AI-state sync, the nested repository, or a stale root adapter | [Git-backed AI-state sync](/openwiki/operations/git-backed-ai-state-sync.md) | `shared/hooks/scripts/state-sync.sh`, `shared/hooks/scripts/restore-root-adapters.sh`, `tests/test_state_sync.py` |
| refresh this wiki | the `knowledge-refresh` skill, then OpenWiki's own `openwiki` skill | `shared/skills/knowledge-refresh/SKILL.md`, `shared/hooks/scripts/openwiki-guard.py` |

## Commands you will run most

From this repository's root, through `uv run`:

```
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format text
uv run python .claude/scripts/verify.py phase --format text
```

The verifier selects the right lint, type, and test scope for whichever
repository it runs in, so prefer it over restating the scope by hand.

## Things that are historical, not current

`.claude/plans/`, `.claude/session_logs/`, dated documents named
`docs/2026-*`, and the root `plans/` directory record past decisions and
their evidence. A later phase may have reversed or refined them. Re-derive
current behavior from `shared/`, `scripts/`, and `tests/`.
