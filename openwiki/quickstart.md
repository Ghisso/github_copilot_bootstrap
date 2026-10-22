---
type: quickstart
title: "Quickstart: where to look for what"
description: A routing map from common tasks in the github_copilot_bootstrap repository to the wiki page that explains the mechanism and the source files that are authoritative for it.
tags: [quickstart, routing, navigation, authority]
sources:
  - id: openwiki-source-df8f0c6d7ed23c271434d0c4
    resource: repo://docs/smoke-tests.md
  - id: openwiki-source-7aaa88e66a4141ea24c14706
    resource: repo://docs/target-mapping.md
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
  - id: openwiki-source-aedfa38e00652688559a19c4
    resource: repo://scripts/generate_targets.py
  - id: openwiki-source-7c162969a98fb2f3fa853ffc
    resource: repo://scripts/install_bootstrap.py
  - id: openwiki-source-71fc4d2e4c5527b7b8a068ba
    resource: repo://scripts/validate_targets.py
  - id: openwiki-source-9fa38289fd921baabf765923
    resource: repo://shared/policies/workflow.instructions.md
  - id: openwiki-source-b7cd6d01f37550e855f61bdc
    resource: repo://shared/scripts/verify.py
  - id: openwiki-source-1c38db574c5e411bfd8c36ea
    resource: repo://shared/sidecar/workflow/skills/onboard/SKILL.md
generated: { by: "codex", at: "2026-10-22T17:57:02.699Z" }
verified:
  - by: openwiki/0.7.2
    at: 2026-10-22T17:57:02.699Z
---

# Quickstart: where to look for what

Source under `shared/`, `scripts/`, and `tests/`, and the policies under `shared/policies/`, outrank every page in this wiki. When a page and the code disagree, the code is right; the page is refreshed, never hand-edited.

## The repository in one picture

This diagram shows how content moves from authoring source to a consumer.

```mermaid
flowchart LR
    S[shared/] -->|generate_targets.py| D[dist/multi-agent/]
    S -->|generate_targets.py| SC[dist/sidecar/skills and workflow]
    D -->|full install| C[consumer repo]
    C --> N[nested .claude on ai-state]
    SC -->|--mode sidecar| T[team repo overlay]
```

This repository is a source-of-truth plus generated bootstrap for AI coding agents, not an application. Hooks enforce a plan-driven lifecycle, and `shared/scripts/verify.py` produces the receipts the commit and push gates check.

## Route by task

| I want to... | Read | Then open |
| --- | --- | --- |
| understand what lives where and why `dist/` and `.claude/` are ignored | [Source, generated output, consumer repo, and nested AI state](architecture/source-generated-consumer-layout.md) | `README.md`, `scripts/generate_targets.py` |
| classify a request, start a phase, close one out, or reopen a completed big plan | [Task lanes and the enforced lifecycle](workflows/lifecycle-and-task-lanes.md) | `shared/policies/workflow.instructions.md`, `shared/templates/plan-small.md` |
| understand why a commit, push, or PR was denied | [Deterministic verification](operations/deterministic-verification.md), then [Hook dispatcher and guardrail scripts](architecture/hooks-and-guardrails.md) | `shared/scripts/verify.py`, `docs/runtime-checks.md` |
| add or change an agent, a review profile, or a skill | [Agent roster, prompts, and the skill library](architecture/agents-and-skills.md) | `shared/agents/<id>/agent.yaml`, `shared/skills/<name>/SKILL.md`, `scripts/validate_targets.py` |
| add or change a hook or guardrail | [Hook dispatcher and guardrail scripts](architecture/hooks-and-guardrails.md) | `shared/hooks/scripts/`, the hook wiring in `scripts/generate_targets.py`, `tests/test_hook_gates.py` |
| understand why the file-protection guard denied or refused a shell command, or which shell forms it does not check | [Hook dispatcher and guardrail scripts](architecture/hooks-and-guardrails.md) | `docs/runtime-checks.md` (the shell-parsing rules, the harmless commands it blocks, and the forms not yet checked), `shared/hooks/scripts/protect-files.py`, `tests/test_protect_files_substitutions.py` |
| choose an install mode, understand why a plain install refused, install or refresh a full consumer, run a batch update, or refresh this repository's own overlay | [Installing the bootstrap, file ownership, and runtime drift checks](operations/install-ownership-and-runtime-checks.md) | `scripts/install_bootstrap.py`, `scripts/runtime_ownership.py`, `scripts/update_consumers.py` |
| add a personal overlay to a team-owned repository, remove it with `--uninstall`, recover a preserved copy, or act on a `SKIPPED`, `RETAINED`, or `PRESERVED` report | [Sidecar overlay](operations/sidecar-overlay.md) | `scripts/sidecar_overlay.py`, `docs/sidecar-provider-contract.md` |
| install the sidecar's `workflow` profile (`--profile workflow`: agents, relaxed rules, review profiles, templates, and a hidden personal state folder for plans, memory, and logs), switch profiles, back up the state folder with `--backup-state`, or purge it with `--uninstall --purge-state` | [Sidecar overlay](operations/sidecar-overlay.md), "What it installs" and "Profile switching" | `scripts/runtime_ownership.py`, `shared/sidecar/workflow/`, `tests/test_sidecar_workflow_scenario.py` |
| learn a team repository's code placement, naming, test, and commit conventions after installing the workflow sidecar | [Sidecar overlay](operations/sidecar-overlay.md), then [Agent roster, prompts, and the skill library](architecture/agents-and-skills.md) | `shared/sidecar/workflow/skills/onboard/SKILL.md`, `.ai-bootstrap/project-context.instructions.md` in the consumer |
| understand or debug AI-state sync, the nested repository, or a stale root adapter | [Git-backed AI-state sync](operations/git-backed-ai-state-sync.md) | `shared/hooks/scripts/state-sync.sh`, `tests/test_state_sync.py` |
| understand the Context Mode pin, tool filter, hook-output filter, or cache quarantine | [Context Mode dispatcher](operations/context-mode-dispatcher.md) | `shared/hooks/scripts/context-mode-dispatch.sh`, `shared/hooks/scripts/context-mode-mcp-filter.mjs`, `tests/fixtures/context_mode_hook/` |
| check which guard or capability each client (Claude Code, Codex, GitHub Copilot, Antigravity) actually gets, and the recorded gaps | [Hook dispatcher and guardrail scripts](architecture/hooks-and-guardrails.md), then [Agent roster, prompts, and the skill library](architecture/agents-and-skills.md) | `docs/target-mapping.md` ("Gate-Repair Client Parity" and "Backlog-Followups Client Parity"), `shared/hooks/scripts/protect-files.py` |
| refresh this wiki | the `knowledge-refresh` skill, then OpenWiki's own `openwiki` skill | `shared/skills/knowledge-refresh/SKILL.md`, `shared/hooks/scripts/openwiki-guard.sh` (the hook entry point) and `shared/hooks/scripts/openwiki-guard.py` |

## Commands you will run most

Run these from the repository root. The verifier selects the right lint, type, and test scope for whichever repository it runs in, so prefer it over restating the scope by hand.

```
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format text
uv run python .claude/scripts/verify.py phase --format text
```

If `scripts/validate_targets.py` reports that `pytest` is absent from an isolated interpreter, use the devcontainer or `uv run --with pytest python scripts/validate_targets.py`. The hook-gate regression check remains required.

## Things that are historical, not current

- `.claude/plans/` and `.claude/session_logs/` record this checkout's own plans and sessions.
- Dated documents named `docs/2026-*` are point-in-time spikes and reviews.
- The root `plans/` directory holds architecture decision records and past phase plans.

A later phase may have reversed or refined any of them. Re-derive current behavior from `shared/`, `scripts/`, and `tests/`.

## Related pages

- [Source, generated output, consumer repo, and nested AI state](architecture/source-generated-consumer-layout.md)
- [Task lanes and the enforced lifecycle](workflows/lifecycle-and-task-lanes.md)
- [Agent roster, prompts, and the skill library](architecture/agents-and-skills.md)
- [Hook dispatcher and guardrail scripts](architecture/hooks-and-guardrails.md)
- [Deterministic verification: verify.py modes, receipts, and findings](operations/deterministic-verification.md)
- [Installing the bootstrap, file ownership, and runtime drift checks](operations/install-ownership-and-runtime-checks.md)
- [Sidecar overlay](operations/sidecar-overlay.md)
- [Git-backed AI-state sync](operations/git-backed-ai-state-sync.md)
- [Context Mode dispatcher: version pin, tool filter, and cache security](operations/context-mode-dispatcher.md)
