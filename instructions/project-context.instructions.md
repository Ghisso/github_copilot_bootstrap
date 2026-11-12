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
  (pins OpenWiki `0.7.2`). Its `initializeCommand` creates `~/.openwiki` and
  `~/.cache/huggingface` on the host, because Docker refuses a bind mount
  whose source folder is missing.
- `shared/third_party/ponytail/`: vendored Ponytail (a local fork, partially
  merged from upstream `v5.3.2`) with provenance.
- `shared/sidecar/`: sources for the personal sidecar overlay. The `workflow`
  profile ships its own `onboard` skill
  (`shared/sidecar/workflow/skills/onboard/`), which writes
  `.ai-bootstrap/project-context.instructions.md` instead of this file.
- `shared/schemas/`: only `native-client-observation.schema.json` (the stale
  agent schema was removed by gate-repair).
- `shared/scripts/` and `shared/templates/`: `verify.py`,
  `record_findings.py`, plan templates, and other rendered workflow artifacts.
- `shared/vscode/tasks.json`: the "AI state: pull" and "AI state: push" VS
  Code tasks. `shared/MEMORY.md`, `shared/plans/`, `shared/session_logs/`,
  and `shared/quality_reports/` are starting content that a fresh install
  copies into a consumer's `.claude/` state.
- `targets/multi-agent/manifest.json`: the generator's target manifest, with
  four adapters (GitHub Copilot, Claude Code, OpenAI Codex, Google
  Antigravity).
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
  on Ubuntu and macOS plus Python 3.9 hook compatibility. It runs the
  validator as `uv run --with pytest`, because the validator's hook-gate
  smoke tests need pytest (without it, the validator says how to provide
  it). CI does not run the full pytest, Ruff, or Mypy suite.
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
  written before schema version 2 stay valid at push. The push and PR gates'
  receipt-chain check skips only a plan's leading run of phases dated before
  2026-08-29 that have no receipt file (`RECEIPT_CHAIN_SINCE` in
  `shared/scripts/verify.py`), because closeout receipts did not exist then.
- The Context Mode hook lane is advisory only: the dispatcher forwards an
  allowlist of advice fields and never forwards a decision or input rewrite.
  On Claude Code the PreToolUse group uses the anchored matcher
  `^(Bash|Read|Grep|WebFetch|mcp__.*)$` (`CLAUDE_CONTEXT_MODE_MATCHER` in
  `scripts/generate_targets.py`), so it never fires on `Agent`: Context
  Mode's only `Agent` action rewrites the subagent prompt, and Claude Code's
  auto mode refuses a call whose input a hook changed. Other targets keep
  `*`. A Context Mode pin bump must recheck this matcher (procedure in
  `docs/runtime-checks.md`).
- Consumer `.claude/` state is a nested `ai-state` Git repository so mutable
  plans, memory, logs, and bootstrap files have an auditable history.
  `state-sync.sh` lets one run work on a checkout at a time (an `flock` on
  the repository root), cancels an HTTPS transfer slower than 1,000 bytes per
  second for 60 seconds, never waits for a typed password, and never commits
  over an unfinished rebase or merge. Two sessions therefore cannot sync over
  each other, a stalled network call cannot hang a hook, and a half-finished
  rebase or merge is never recorded as state.
- Semble is for semantic code discovery. context-mode is optional; when it is
  unavailable or blocked, direct reads and `rg` are the supported fallback.
- Tests, hooks, and `verify.py` make no model call.

## Current status and verification

Onboarding was refreshed on `dev` at `7b221ce` on 2026-11-11.
`uv run python scripts/check_runtime.py` printed 20 lines, all PASS.

Pull requests merged into `dev` since the 2026-10-20 refresh:

- #47 `backlog-followups` (Phases A to J). Phases H and I replaced `shlex`
  in the file-protection guard (`shared/hooks/scripts/protect-files.py`)
  with a Bash-rules scanner; `docs/runtime-checks.md` lists the forms it
  still does not check, and a recorded follow-up in
  `docs/target-mapping.md` asks to split or shrink the hook.
- #49 `sidecar-onboard-and-validator`: the sidecar `workflow` profile's
  `onboard` skill, and a validator that explains a missing pytest.
- #51 `state-sync-safety-fixes`: one state sync at a time, bounded network
  calls, no commit over an unfinished rebase or merge, and a root-adapter
  restore that refuses a symlinked `.claude` or `.claude/bootstrap-root`.
- #52 `pre-receipt-phase-exemption`: the receipt-chain skip described above.
- #53 `context-mode-agent-matcher`: the anchored Claude Code matcher
  described above.
- #54 `readme-and-wiki-drift-fixes` (2026-11-12): README wording for Context
  Mode routing and the "Verification Defaults" scope, and an OpenWiki refresh
  for PRs #52 and #53.

`origin/main` was last updated on 2026-10-23 by PR #50 (`dev` into `main`);
`dev` is 12 commits ahead of it (PRs #51 to #54). Releasing `dev` to `main` is
the user's call. Every local implementation branch is already merged into
`dev`.

On 2026-11-12 none of the four local full consumers (`~/work/RAG`,
`~/work/git_projects/img-classification`, `industrial-inspection`, and
`schema-bootstrap-llm-wiki`) had PR #53's matcher in `.claude/settings.json`.
They need a refresh through `scripts/update_consumers.py`; that is the user's
call.

Pinned versions: Context Mode `1.0.169`, OpenWiki `0.7.2` (the guard allows
only `mode: "update"`), and Ponytail partially merged from upstream `v5.3.2`
(`ponytail-review` stays complexity-only). Context Mode `2.1.7` (2026-11-08)
is a full rewrite: it needs Node.js 24.15 or newer (the devcontainer has 22),
always reports server version `"dev"` (the filter's version gate fails), needs
a per-host `--agent` server argument (Antigravity has none), ignores
`CONTEXT_MODE_DIR`, and forwards almost nothing through the kit's advice-only
filter. A 2026-11-11 evidence spike judged it a planned control-plane
migration, not a pin bump (`.claude/explorations/2026-11-11_context-mode-2x-evidence/REPORT.md`).
Until then the dispatcher refuses any other version, so `1.0.169` stays safe.
The migration plan `.claude/plans/context-mode-2x-migration.md` was approved
on 2026-11-12 with every recommended option (MCP-only, drop `ctx_doctor`,
drop Antigravity's entry, one server identity). It waits for its settle
check: 2.1.8 shipped on 2026-11-11, so nothing runs before 2026-11-26. On
2026-11-12 npm `latest` was still 2.1.8.

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
- The 2026-11-11 onboarding found two README sentences and three OpenWiki
  statements out of date (Context Mode routing for "three" targets, the
  consumer `src/` scope of "Verification Defaults", the Claude Code Context
  Mode matcher from PR #53, and the receipt-chain skip from PR #52). The big
  plan `readme-and-wiki-drift-fixes` fixed all five, merged into `dev` as
  PR #54 on 2026-11-12.
- A one-phase plan gets no knowledge-refresh phase, so the wiki drifts until
  the next refresh (PRs #52 and #53 were the latest case). Refresh pages only
  through the `knowledge-refresh` skill, never by hand.
