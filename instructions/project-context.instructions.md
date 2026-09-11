---
description: "Always-on: what this specific repo is and how it's built. Not part of the generated shared/ bootstrap — safe to hand-edit."
---

# Project Context

## What this project is

`github_copilot_bootstrap` is a reusable, multi-target agent-workflow bootstrap
for other repositories. It is a source-of-truth repository plus a generated
installable target; it is not an application and has no runtime inference,
API-service, or UI product of its own.

The generic workspace guidance mentions Hydra, BentoML, Haystack, and Gradio
because consumer repositories may use them. Those frameworks do not apply to
this repository's bootstrap scripts, shell hooks, or generated adapters.

## Layout

- `README.md`: product intent, install/update workflow, architecture, and gates.
- `docs/`: architecture, deterministic commit-gate, runtime, smoke-test, and
  target-mapping documentation.
- `shared/policies/`: source instruction files, including workflow, quality,
  tool-routing, and workspace rules.
- `shared/skills/`: reusable public/background skills; `onboard` is one of them.
- `shared/agents/`: canonical agent metadata and target-neutral prompts.
- `shared/review-profiles/`: profile checklists used by the unified reviewer.
- `shared/hooks/`: lifecycle configuration and shell guardrails.
- `shared/mcp/servers.json`: Semble, Context7, and Context Mode definitions
  (Context Mode is filtered to exactly four guarded tools).
- `shared/devcontainer/`: generated GPU devcontainer and AI-state bootloader.
- `shared/scripts/` and `shared/templates/`: shared scoring, findings, and
  workflow artifacts rendered into targets.
- `scripts/generate_targets.py`: renders the single `dist/multi-agent/` target.
- `scripts/install_bootstrap.py`: installs generated output into a consumer and
  initializes its nested `.claude` `ai-state` repository.
- `scripts/update_consumers.py`: regenerates and updates consumer repositories.
- `scripts/validate_targets.py`: structural and behavioral target validator.
- `scripts/check_runtime.py`: runtime-file and optional-helper checker.
- `scripts/check_native_clients.py`: runs optional native-client probes and
  records evidence for Claude Code, Codex, Copilot, and Google Antigravity.
- `plans/`: ADRs, implementation plans, closeouts, and architecture reviews.
- `dist/multi-agent/`: generated and gitignored; never hand-edit it.

## Pipeline / data flow

```text
shared/ source files
    -> generate_targets.py
dist/multi-agent/ generated bundle
    -> install_bootstrap.py
consumer repo: Copilot + Claude Code + Codex + Antigravity adapters
    + .claude shared basis
    -> hooks and state-sync.sh
consumer workflow: plan -> implement -> verify -> review -> score -> document
    -> learn/session log -> gated commit or PR
```

## Design decisions

- One shared basis produces thin Copilot, Claude Code, Codex, and Google
  Antigravity adapters so workflow semantics stay aligned while each target
  keeps native wiring.
- Ponytail is vendored as portable skills so coding/review behavior does not
  depend on a per-user plugin or network availability.
- Guardrails are shared shell scripts, while commit/push invariants also run as
  real Git hooks; this closes tool-layer and human/IDE bypasses where possible.
- Consumer `.claude/` state is a nested `ai-state` Git repository so mutable
  plans, memory, logs, and bootstrap files have an auditable history and can
  use the code remote or an explicitly configured private remote.
- Semble is for semantic code discovery. context-mode is optional; when it is
  unavailable or blocked, direct reads and `rg` are the supported fallback.

## Current status and verification

Onboarding was refreshed on `dev` on 2026-09-11 from clean outer and nested
worktrees. `UV_CACHE_DIR=/tmp/github-copilot-bootstrap-uv-cache uv run python
scripts/validate_targets.py` passed with `PASS generated target is structurally
valid`; `scripts/check_runtime.py` also passed. The structural validator checks
generation, determinism, hooks, adapters, lifecycle contracts, and its
regression suite. It is not proof that every supported native client routed
every role at runtime; use the optional `scripts/check_native_clients.py`
release probe when that evidence is needed.

Before merging bootstrap changes, run:

1. `uv run python scripts/generate_targets.py --all`
2. `uv run python scripts/validate_targets.py`
3. `uv run python scripts/check_runtime.py`
4. relevant tests/lint/type checks and the profile-driven review
5. score and findings gates, documentation updates, `[LEARN]` capture, and a
   session closeout before commit/PR

The local environment may require `UV_CACHE_DIR` to point at a writable path.
Optional Semble/context-mode binaries warn and do not invalidate the bootstrap.

## Scope boundaries

- Do not add application/runtime framework code here; consumer projects own
  their model, data, API, and UI stacks.
- Do not hand-edit `dist/`; change `shared/` or the generator and regenerate.
- Do not treat generated adapters as independent sources of truth.
- Do not make context-mode a hard dependency for onboarding, hooks, or runtime
  checks; local direct-read/`rg` behavior must remain viable.
- Consumer-specific state belongs in the consumer's nested `.claude` repo, not
  in shared source templates or generated output.

## Known documentation/status caveat

Some older plan files still say `Proposed` even though the corresponding
implementation and documentation are present (notably state-sync and
post-review hardening). Treat code and generated-target validation as the
current source of truth, and refresh plan status when the next related change
touches those plans.

The `onboard` skill's generic consumer-project wording assumes both root
entrypoints have a Project State slot. This authoring repository instead keeps
the tracked root `AGENTS.md` as its maintainer guide, without that slot; do not
add one there. Its generated consumer adapter is validated separately.
