---
description: "Always-on: what this specific repo is and how it's built. Not part of the generated shared/ bootstrap — safe to hand-edit."
---

# Project Context

## What this project is

`github_copilot_bootstrap` is a reusable, multi-target agent-workflow bootstrap
for other repositories. It is a source-of-truth repository plus two generated
installable targets; it is not an application and has no runtime inference,
API-service, or UI product of its own.

The generic workspace guidance mentions Hydra, BentoML, Haystack, and Gradio
because consumer repositories may use them. Those frameworks do not apply to
this repository's bootstrap scripts, shell hooks, or generated adapters. There
is no `src/` and no `pyproject.toml` here; tooling comes from the devcontainer
image, and canonical Python lives under `shared`, `scripts`, and `tests`.

## Layout

- `README.md`: product intent, full and sidecar install/update, architecture,
  hooks, and gates.
- `docs/`: architecture, deterministic commit gate, runtime checks, smoke
  tests, sidecar provider contract, native-client acceptance, dated evidence
  notes, and `target-mapping.md` (per-client adapters, the gate-repair and
  backlog-followups parity tables, and the recorded follow-ups list).
- `openwiki/`: generated OpenWiki knowledge layer (descriptive, never
  authority; refresh only through the `knowledge-refresh` skill).
- `shared/policies/`: source instruction files (workflow, quality,
  tool-routing, workspace, agent reporting).
- `shared/skills/`: 55 reusable skills; `onboard` is one of them.
- `shared/agents/`: canonical agent metadata and target-neutral prompts.
- `shared/review-profiles/`: profile checklists used by the unified reviewer.
- `shared/hooks/`: lifecycle configuration and shell/Python guardrails,
  including `context-mode-dispatch.sh` (pins Context Mode `1.0.169`).
- `shared/mcp/servers.json`: Semble, Context7, and Context Mode definitions
  (Context Mode is filtered to exactly four guarded tools).
- `shared/devcontainer/`: generated GPU devcontainer and AI-state bootloader
  (pins OpenWiki `0.7.2`).
- `shared/third_party/ponytail/`: vendored Ponytail (a local fork, partially
  merged from upstream `v5.3.2`) with provenance.
- `shared/sidecar/`: sources for the personal sidecar overlay.
- `shared/schemas/`: only `native-client-observation.schema.json` (the stale
  agent schema was removed by gate-repair).
- `shared/scripts/` and `shared/templates/`: `verify.py`,
  `record_findings.py`, plan templates, and other rendered workflow artifacts.
- `scripts/generate_targets.py`: renders `dist/multi-agent/` (the full
  bootstrap) and `dist/sidecar/<profile>/` (the personal per-clone overlay,
  profiles `skills` and `workflow`).
- `scripts/install_bootstrap.py`: installs generated output into a consumer,
  in `full` mode (a takeover, including a nested `.claude` `ai-state`
  repository) or `sidecar` mode (a private overlay inside a team-owned
  harness), chosen by `--mode` or auto-detected. It fills each generated
  `**Project:**` placeholder line (`CLAUDE.md`, `AGENTS.md`, and the installed
  workspace instructions) with the target directory name.
- `scripts/runtime_ownership.py`: which installed paths the bootstrap owns and
  which are consumer state (`CONSUMER_STATE_PATHS`); anything else under
  `.claude/` that the target lacks is deleted on refresh.
- `scripts/sidecar_overlay.py`: sidecar install, update, and uninstall engine.
- `scripts/update_consumers.py`: batch regenerate/update of mixed full and
  sidecar consumers; it finishes every target even when one fails.
- `scripts/validate_targets.py`: structural and behavioral target validator,
  including installed Git-hook smoke runs.
- `scripts/validate_plan_frontmatter.py`: plan frontmatter and L1–L4
  Verification-block checks (run at branch creation and at commit).
- `scripts/check_runtime.py`: runtime-file drift and optional-helper checker.
- `scripts/check_native_clients.py`: optional native-client probes and
  evidence (Claude Code and Codex only).
- `tests/`: pytest suite for hooks, gates, verifier, installer, sidecar,
  state sync, and Context Mode dispatch (recorded hook fixtures).
- `.github/workflows/validate.yml`: CI for generation and target validation
  on Ubuntu and macOS plus Python 3.9 hook compatibility. It does not run the
  full pytest, Ruff, or Mypy suite.
- `plans/`: older ADRs, implementation plans, closeouts, and architecture
  reviews. Current plans live in `.claude/plans/`.
- `dist/`: generated and gitignored; never hand-edit it.

## Pipeline / data flow

```text
shared/ source files
    -> generate_targets.py
dist/multi-agent/            dist/sidecar/{skills,workflow}/
    -> install_bootstrap.py --mode full | --mode sidecar
consumer repo (full): Claude Code + Codex + Copilot + Antigravity adapters
    + .claude shared basis (nested ai-state repo) + Git hooks
consumer repo (sidecar): ignored skills/rules (+ agents and .ai-bootstrap/
    state for the workflow profile); no hooks, no receipts
    -> full-install workflow: plan -> implement -> verify -> review
       -> record findings (gate result + profiles) -> closeout receipt
       -> gated commit -> push
```

## Design decisions

- One shared basis produces thin Claude Code, Codex, Copilot, and Google
  Antigravity adapters so workflow semantics stay aligned while each target
  keeps native wiring. Client priority for parity work is Claude Code, Codex,
  GitHub Copilot, Antigravity; a gap in a lower client is recorded in
  `docs/target-mapping.md`, not hidden.
- Ponytail is vendored as portable skills so coding/review behavior does not
  depend on a per-user plugin or network availability.
- Guardrails are shared shell scripts, while commit/push invariants also run as
  real Git hooks; this closes tool-layer and human/IDE bypasses where possible.
- The commit gate trusts only what it checks: the findings report records the
  reviewer's `gate_result` and open requests (schema version 2), and the gate
  requires the review profiles the branch's changed paths call for. Reports
  written before schema version 2 stay valid at push.
- The Context Mode hook lane is advisory only: the dispatcher forwards an
  allowlist of advice fields and never forwards a decision or input rewrite.
- Consumer `.claude/` state is a nested `ai-state` Git repository so mutable
  plans, memory, logs, and bootstrap files have an auditable history.
- Semble is for semantic code discovery. context-mode is optional; when it is
  unavailable or blocked, direct reads and `rg` are the supported fallback.
- Tests, hooks, and `verify.py` make no model call.

## Current status and verification

Onboarding was refreshed on `dev` at `f964551` on 2026-10-20, after the
`gate-repair` big plan merged (PR #46). `uv run python scripts/check_runtime.py`
reported only PASS lines. `dev` is 273 commits ahead of `origin/main`, which
was last updated 2026-05-24; releasing `dev` to `main` is the user's call.

The `backlog-followups` big plan (Phases A to G, 2026-10-20 to 2026-10-21)
then ran on `backlog-followups_implementation`; opening its pull request to
`dev` is the user's decision. Pinned versions after it: Context Mode
`1.0.169`, OpenWiki `0.7.2` (from `0.5.2`; the guard allows only
`mode: "update"`), and Ponytail partially merged from upstream `v5.3.2`
(from `v4.8.4`; `ponytail-review` stays complexity-only).

Before merging bootstrap changes, run:

1. `uv run python scripts/generate_targets.py --all`
2. `uv run python scripts/validate_targets.py`
3. `uv run python scripts/check_runtime.py`
4. relevant tests/lint/type checks and the profile-driven review
5. findings gate, documentation updates, `[LEARN]` capture, and a session
   closeout before commit/PR

After a `shared/` change, refresh the installed copy here with
`uv run python scripts/install_bootstrap.py . --allow-self --local-only`.
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
- A new file under `.claude/` survives a self-refresh only inside a
  `CONSUMER_STATE_PATHS` entry; elsewhere the installer deletes it.

## Known documentation/status caveats

- Some older files under root `plans/` still say `Proposed`. Treat code and
  target validation as the source of truth. (The stale July plan statuses and
  the 2026-10-02 exploration statuses were closed by `backlog-followups`
  Phase A on 2026-10-20.)
- Root `CLAUDE.md` and `AGENTS.md` are tracked, hand-maintained maintainer
  guides here, not gitignored generated files; `AGENTS.md` has no
  `**Project:**` line and must not get one. Never fill the `**Project:**`
  placeholder in `shared/policies/workspace.instructions.md`: that file is the
  consumer template, and the installer fills the line per target. The
  installed workspace copy reads `**Project:** github_copilot_bootstrap`, and
  `check_runtime.py` accepts only that exact substitution, so a longer
  one-liner there would show as drift. The `onboard`, `setup-project`, and
  `create-feature` skills say this since Phase A.
- While tracked root `CLAUDE.md` or `AGENTS.md` differs from its mirror in
  `.claude/bootstrap-root/`, `verify.py` cannot build a receipt and stops with
  `receipt metadata control-plane provenance is invalid`. Run
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  after editing either file.
