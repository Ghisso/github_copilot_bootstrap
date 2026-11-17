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

- `README.md`: product intent, full and sidecar install/update, project-owned
  skills, architecture, hooks, and gates.
- `docs/`: architecture, deterministic commit gate, runtime checks, smoke
  tests, sidecar provider contract, native-client acceptance, dated evidence
  notes, and `target-mapping.md` (per-client adapters, the gate-repair and
  backlog-followups parity tables, and the "Recorded follow-ups" list).
- `openwiki/`: generated OpenWiki knowledge layer (descriptive, never
  authority; refresh only through the `knowledge-refresh` skill).
- `shared/policies/`: twelve source policy files. Seven apply always
  (`workspace`, `workflow`, `closeout`, `plan-lifecycle`,
  `quality-and-testing`, `tool-routing`, `agent-reporting`). Five apply only
  to matching paths (`code-standards`, `tests`, `config-first-design`,
  `api-service-standards`, `deployment`); they become Claude Code
  `.claude/rules/` files, Copilot `applyTo` adapters, and Codex fallback
  skills. The CLOSEOUT steps live in `closeout`, and the plan pause, cancel,
  and reopen rules in `plan-lifecycle`, not in `workflow`.
- `shared/skills/`: 37 reusable skills (cut from 55 on 2026-11-14). Each
  skill's listing text (description plus `when_to_use`) is capped at 300
  characters, except `ponytail` and `ponytail-review`, whose text is pinned
  to upstream by hash. Niche library lessons live as `references/` files
  inside `haystack` and `data-and-graph-pitfalls`. `onboard` is one of the 37.
- `shared/agents/`: canonical agent metadata and target-neutral prompts, one
  folder per agent. Five agents are universal (`orchestrator`, `planner`,
  `coder`, `reviewer`, `documenter`), two are Codex-only (`luna_coder`,
  `sol_coder`), and one is Antigravity-only (`antigravity_flash_coder`).
- `shared/review-profiles/`: ten profile checklists used by the unified
  reviewer.
- `shared/hooks/`: lifecycle configuration and shell/Python guardrails,
  including `context-mode-dispatch.sh` (pins Context Mode `2.1.8`). Its
  `git-hooks/` folder holds the real Git hooks `commit-msg`, `post-commit`,
  and `pre-push`. `hooks.json` is the GitHub Copilot hook file (five events,
  including `SubagentStart`, which runs `subagent-context.sh`). The launcher
  `run-hook.sh` makes the five lifecycle hooks reached through the Claude
  settings stand down on the Copilot harness; guards never stand down.
- `shared/prompts/`: reusable prompt templates copied into a consumer's
  `.claude/prompts/`; today it holds only a placeholder `README.prompt.md`.
- `shared/mcp/servers.json`: Semble, Context7, and Context Mode definitions
  (Context Mode is filtered to exactly three tools: `ctx_index`,
  `ctx_search`, `ctx_stats`; Antigravity gets no Context Mode entry).
- `shared/devcontainer/`: generated GPU devcontainer and AI-state bootloader
  (pins OpenWiki `0.7.2`; Node.js stage `node:24.22.3-bookworm-slim`). Its
  `initializeCommand` creates `~/.openwiki` and `~/.cache/huggingface` on the
  host, because Docker refuses a bind mount whose source folder is missing.
- `shared/third_party/ponytail/`: vendored Ponytail (a local fork, partially
  merged from upstream `v5.3.2`) with provenance.
- `shared/sidecar/`: sources for the personal sidecar overlay. The `workflow`
  profile ships its own `onboard` skill
  (`shared/sidecar/workflow/skills/onboard/`), which writes
  `.ai-bootstrap/project-context.instructions.md` instead of this file.
- `shared/schemas/`: only `native-client-observation.schema.json`.
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
  workspace instructions) with the target directory name. Before the first
  write, `validate_project_skills` and `validate_no_symlink_writes` refuse
  unsafe states (see Design decisions); a copy-time guard checks every file
  copy again.
- `scripts/runtime_ownership.py`: which installed paths the bootstrap owns and
  which are consumer state (`CONSUMER_STATE_PATHS`); anything else under
  `.claude/` that the target lacks is deleted on refresh, except a
  marker-claimed third-party bundle and a `.claude/skills/<name>/` folder
  marked with `.project-skill` (`PROJECT_SKILL_MARKER`).
- `scripts/sidecar_overlay.py`: sidecar install, update, and uninstall engine.
- `scripts/update_consumers.py`: batch regenerate/update of mixed full and
  sidecar consumers; it finishes every target even when one fails.
- `scripts/validate_targets.py`: structural and behavioral target validator,
  including installed Git-hook smoke runs, byte budgets for root guidance and
  policies, and the 300-character skill listing cap
  (`SKILL_DESCRIPTION_MAX_CHARS`).
- `scripts/validate_plan_frontmatter.py`: plan frontmatter and L1–L4
  Verification-block checks (run at branch creation and at commit).
- `scripts/check_runtime.py`: runtime-file drift and optional-helper checker.
- `scripts/check_native_clients.py`: optional native-client probes and
  evidence (Claude Code and Codex only).
- `scripts/check_copilot_runtime.py` with `scripts/copilot_runtime_probe.mjs`:
  an opt-in, offline probe of the real Copilot runtime that ships inside VS
  Code (three sessions, 48 result lines on runtime `1.0.108-0`). It is run
  by hand and as a required item of a plan phase, never by tests or hooks.
- `tests/`: pytest suite for hooks, gates, verifier, installer, sidecar,
  state sync, the Context Mode dispatcher and MCP filter, and the Copilot
  harness (`test_protect_files_copilot_harness.py`,
  `test_check_copilot_runtime.py`, and the stand-down and sub-agent hook
  cases in `test_hook_gates.py`).
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
- Small always-loaded context. Claude Code lists every skill's listing text
  each turn and cuts the list when it grows too long, and every always-apply
  policy loads at session start. So the shipped set is 37 skills with a
  300-character listing cap, procedures that only some steps need live in
  their own files (`closeout`, `plan-lifecycle`), and `validate_targets.py`
  enforces byte budgets (generated `CLAUDE.md` is about 4.4 KB, `AGENTS.md`
  about 4.8 KB). Section 6 of
  `.claude/explorations/2026-11-12_skills-and-instructions-review.md` lists
  cuts that were proposed and rejected; do not propose them again without
  new evidence.
- Ponytail is vendored as portable skills so coding/review behavior does not
  depend on a per-user plugin or network availability.
- Guardrails are shared shell scripts, while commit/push invariants also run as
  real Git hooks; this closes tool-layer and human/IDE bypasses where possible.
- On VS Code's Copilot harness (the runtime shared with Copilot CLI), the
  guards print each decision at the top level and nested, the lifecycle hooks
  reached through the Claude settings stand down, and the guards run from both
  hook files and never stand down (option B of the plan
  `copilot-harness-migration`, chosen by the user on 2026-11-17). The Local
  harness stays supported until VS Code removes it in February 2027.
- The commit gate trusts only what it checks: the findings report records the
  reviewer's `gate_result` and open requests (schema version 2), and the gate
  requires the review profiles the branch's changed paths call for. The
  report's `content_hash` covers every tracked change from the merge base,
  documentation and unstaged edits included, so a late documentation edit
  needs findings recorded again. Reports written before schema version 2
  stay valid at push. The push and PR gates' receipt-chain check skips only a
  plan's leading run of phases dated before 2026-08-29 that have no receipt
  file (`RECEIPT_CHAIN_SINCE` in `shared/scripts/verify.py`), because closeout
  receipts did not exist then.
- A full refresh deletes every `.claude/` file the bootstrap does not
  generate, so a project-owned skill survives only in a real folder holding a
  `.project-skill` file. When the installer cannot tell a project skill from
  an old bootstrap copy, it refuses before any write instead of guessing.
  This includes an unmarked folder whose name the new bootstrap ships but the
  shipped-before record (`.claude/bootstrap-root/.agents/skills`) does not
  list, with or without a record (option A, the user's decision on
  2026-11-15).
- A full refresh never writes through a symbolic link or over a path of the
  wrong kind (for example a folder where a file goes). The preflight refuses
  both before the first write, runs again after a legacy state migration,
  and a copy-time guard checks each copy as a second line. The gaps it does
  not cover are listed in `docs/target-mapping.md` ("Recorded follow-ups").
- Context Mode is MCP-only: no client wires a Context Mode hook, and a hook
  call from stale wiring reads its input, prints nothing, and exits 0. The
  filter exposes three tools, sends the client only `protocolVersion`,
  `capabilities.tools`, and `serverInfo` from `initialize`, replaces tool
  descriptions with kit text, and gates on `serverInfo.name ==
  "context-mode"` (1.x and 2.x report the same name, so the dispatcher's
  manifest or `npx` pin is the only version proof). The filter answers the
  MCP 2026-07-28 `server/discover` probe itself with `-32601` and never
  forwards it, so clients use `initialize`: the 2.1.8 answer to the probe
  carries upstream `instructions`, and a client that accepted it would skip
  `initialize` and get no tools. `ctx_index` takes raw text or one regular
  file inside the repository, never a folder: 2.x folder indexing has no
  bound and follows symlinks into sibling projects (2026-11-12 spike S3).
  `FILTER_CONTRACT="ctx-index-files-only-v2"` moves older caches aside.
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

## Bootstrap hooks runtime contract

Moved here from `shared/policies/workspace.instructions.md` on 2026-11-13
(skills-and-instructions-trim, Phase B): it binds only the authors of this
repository's hooks, and consumers have no hook sources or `tests/test_hook_gates.py`
to apply it to.

Standalone bootstrap hooks execute with bare system `python3` (not `uv run` or a project-managed environment) to function before project infrastructure initializes.

**Minimum Python version:** 3.9

Hook Python code is limited to:
- Standard library modules available in Python 3.9 (`json`, `re`, `sys`, `pathlib`, `datetime`, `stat`)
- No external packages or project dependencies
- Must not runtime-evaluate syntax or stdlib features that require Python newer than 3.9. Use `from __future__ import annotations` when newer annotation syntax (e.g. `X | Y`) is otherwise safe to parse on Python 3.9

When adding new hook Python code, verify it compiles under Python 3.9 with `python3 -m py_compile` and add regression coverage to the test suite (see `tests/test_hook_gates.py`).

## Current status and verification

Onboarding was refreshed on `dev` at `2e8c7bb` (the merge of PR #56) on
2026-11-17. No tracked file has changed since the 2026-11-15 refresh, and
`dev` matched `origin/dev`. `uv run python scripts/check_runtime.py` exited 0
with 22 PASS lines and one expected WARN: the global `context-mode` on this
host is still 1.0.169, so the dispatcher refuses it and uses
`npx -y context-mode@2.1.8`. `uv run pytest tests/ -q` gave 5243 passed,
1 skipped (about 6 minutes) at this same commit on 2026-11-15; it was not run
again on 2026-11-17.

The tracked documents (`README.md`, `SECURITY.md`, root `CLAUDE.md` and
`AGENTS.md`, and the undated files in `docs/`) were checked against the code
on 2026-11-17: every source path they name exists, the pinned versions and
the skill count match, and the README agent table, hook list, and verifier
options match the source. Nothing needed a change on that day.

Since then (2026-11-17 to 2026-11-18): the plan `copilot-harness-migration`
on the branch `copilot-harness-migration_implementation`, seven phases (A to
G), each committed and pushed; not merged, and no pull request opened (the
user's call). It moved the GitHub Copilot support to VS Code's Copilot
harness. Phase F rewrote the Copilot statements in `README.md` and five
documents; the final audit in Phase G corrected `README.md`, `SECURITY.md`,
`docs/native-client-acceptance.md`, and
`shared/skills/knowledge-refresh/SKILL.md`, and the wiki was refreshed. On
that branch `uv run pytest tests/ -q` gave 5,927 passed, 1 skipped (about 7
minutes) on 2026-11-18. The verifier's budgets are 900 seconds for one
command and 1,020 seconds for one required item (`shared/scripts/verify.py`).
Evidence report:
`.claude/explorations/2026-11-17_copilot-harness-migration-evidence/REPORT.md`.

Pull requests merged into `dev` since the 2026-11-12 refresh:

- #55 `context-mode-2x-migration` (2026-11-12): MCP-only Context Mode with
  three tools, the 2.1.8 pin with one server identity, and the local answer
  to the `server/discover` probe.
- #56 `skills-and-instructions-trim` (Phases A to I, 2026-11-13 to
  2026-11-15): project-owned skills (`.project-skill`); the workflow policy
  split into `closeout` and `plan-lifecycle` with byte budgets; skills cut
  from 55 to 37 with the 300-character cap; and the installer's link and
  wrong-kind refusals (Phases F and H).

PR #57 (`217b3ca`, 2026-11-15) merged `dev` into `main`, so `origin/main`
holds everything on `dev`, and `dev` is 0 commits ahead of it. The local
`main` branch on this computer is still at PR #50 (`d514277`, 2026-10-23),
29 commits behind `origin/main`; it can be fast-forwarded, and doing so is
the user's call. No implementation branch is unmerged; the remote has only
`dev`, `main`, and `ai-state`.

Open follow-ups to start from:

- From `copilot-harness-migration`, open on 2026-11-18:
  - The user has not yet run the manual checklist in `docs/smoke-tests.md`
    (section "VS Code Copilot harness (manual)", 11 items, test folder
    `~/copilot-harness-probe-20261117`). No item has a run in a signed-in
    window since the changes.
  - The result of the `macos-latest` job of the `Validate` workflow has not
    been read (`gh` was not signed in on this computer). It is the first run
    of the shell escaping and the launcher on macOS tools.
  - Two old defects in the guard hooks, told to the user, who decides: inline
    Python without `-I` (a `json.py` in the repository root runs inside the
    guards), and `protect-files.sh` leaving one empty `/tmp/tmp.*` file for
    each call. Recommended as one small plan. Not in the public docs. The
    same plan can replace the bare evidence labels in comments of
    `run-hook.sh`, `subagent-context.sh`, and `protect-files.py`.
  - The user can keep, narrow, or lift the deny of `run_dynamic_workflow` and
    `dynamic_workflows_manage` on `github-copilot`.
  - At the Local harness removal (February 2027): rename the hook events to
    camelCase (recheck the input side first), drop the Local-only fields of
    the agent wrappers, decide on `.vscode/mcp.json`, and keep
    `.github/copilot-instructions.md` (the sub-agent hook reads it). The list
    is in `docs/target-mapping.md`, "Recorded follow-ups".

- Low severity, open: the `workflow` sidecar profile seeds a missing state
  `README.md` through a linked `.ai-bootstrap/` subfolder, which can create
  the file outside the project. Details and the proposed fix:
  `.claude/quality_reports/2026-11-15_sidecar-state-seed-link-followup.md`.
  It is not yet in the `docs/target-mapping.md` follow-ups list; add it when
  the fix plan starts.
- Priority follow-up in `docs/target-mapping.md`: the unsafe-destination
  check does not cover `state-sync.sh`'s own writes (the nested `.gitignore`
  and `.gitattributes` appends, and the `settings.local.json` restore). The
  sidecar note suggests one small plan for both.

All four local full consumers (`~/work/RAG`,
`~/work/git_projects/img-classification`, `industrial-inspection`, and
`schema-bootstrap-llm-wiki`) were refreshed on 2026-11-15 at 14:29 UTC. Each
nested `.claude` repository has a `bootstrap: update` commit from that
minute; `img-classification` first got a `migrate: import pre-git state`
commit. Checked on 2026-11-17: each has the Context Mode `2.1.8` pin and the
37 shipped skills, and its `.claude/scripts/verify.py`,
`closeout.instructions.md`, and `safe-consumer-bootstrap-refresh` skill are
byte-identical to `dist/multi-agent/`. Two things are still open there:

- The consumer MEMORY entries that name retired skills were not updated at
  the refresh. `~/work/RAG/.claude/MEMORY.md` still has 14 such lines and
  `industrial-inspection` has 1. The `safe-consumer-bootstrap-refresh` skill
  maps the 20 retired skills to where their content went.
- `RAG` and `schema-bootstrap-llm-wiki` each keep two empty folders,
  `.claude/skills/iterative-plan-review` and `.claude/skills/retrieval-routing`
  (dated 2026-08-09; both were bootstrap skills retired in July). The
  obsolete-file cleanup in `install_bootstrap.py` removes a folder only after
  it deletes a file inside it, so an already-empty folder stays. The refresh
  ran with them present. They are harmless and can be deleted by hand.

The user has other consumers on other computers, so this list is not
complete. For a consumer not yet refreshed, a refresh through
`scripts/update_consumers.py` brings MCP-only Context Mode 2.1.8 (Node.js
24.15.0 or newer on the host or in a rebuilt devcontainer), the 37-skill
set, and the new refusals; the `safe-consumer-bootstrap-refresh` skill
explains the refusals. Once `copilot-harness-migration` is merged, a refresh
also brings the marker `BOOTSTRAP_HOOK_SOURCE=claude-settings` in the Claude
settings hook commands, a `SubagentStart` entry and a session-start reminder
entry in the Copilot hook file, and the guard changes listed in `README.md`
under "Upgrading a consumer with active work". Consumers installed at `76887a8` (2026-08-22) cannot
refresh because of an older takeover rule. Refreshing is the user's call.

Pinned versions: Context Mode `2.1.8` (`PINNED_CONTEXT_MODE_VERSION` in
`shared/hooks/scripts/context-mode-dispatch.sh`), OpenWiki `0.7.2` (the guard
allows only `mode: "update"`), and Ponytail partially merged from upstream
`v5.3.2` (`ponytail-review` stays complexity-only). The Copilot runtime is
not pinned: `1.0.108-0` (Copilot SDK `1.0.30-preview.0`, VS Code 1.146.0) is
the version the offline probe last passed on, 2026-11-18; the probe prints
the version on every run and says nothing about another. Context Mode 2.x needs
Node.js 24.15.0 or newer (the dispatcher enforces it in server mode and
`--self-check`), always reports server version `"dev"`, needs `--agent` (the
kit uses `codex` for every client, started from the outer repository root),
ignores `CONTEXT_MODE_DIR` (the dispatcher exports `CONTEXT_MODE_DATA_DIR` to
the guarded root), and has no Antigravity id. Tests use a private copy in
`$HOME/.cache/context-mode-pin`. Evidence:
`.claude/explorations/2026-11-11_context-mode-2x-evidence/REPORT.md` and
`.claude/explorations/2026-11-12_context-mode-2x-recheck/REPORT.md`.

Before merging bootstrap changes, run:

1. `uv run python scripts/generate_targets.py --all`
2. `uv run python scripts/validate_targets.py`
3. `uv run python scripts/check_runtime.py`
4. relevant tests/lint/type checks and the profile-driven review
5. findings gate, documentation updates, `[LEARN]` capture, and a session
   closeout before commit/PR (`closeout.instructions.md`)

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
  `CONSUMER_STATE_PATHS` entry, a marker-claimed third-party bundle, or a
  `.claude/skills/<name>/` folder marked with `.project-skill`; elsewhere the
  installer deletes it. An unmarked skill folder it cannot classify makes it
  refuse instead.

## Known documentation/status caveats

- Some older files under root `plans/` still say `Proposed`. Treat code and
  target validation as the source of truth.
- Root `CLAUDE.md` and `AGENTS.md` are tracked, hand-maintained maintainer
  guides here, not gitignored generated files; `AGENTS.md` has no
  `**Project:**` line and must not get one. Never fill the `**Project:**`
  placeholder in `shared/policies/workspace.instructions.md`: that file is the
  consumer template, and the installer fills the line per target. The
  installed workspace copy reads `**Project:** github_copilot_bootstrap`, and
  `check_runtime.py` accepts only that exact substitution, so a longer
  one-liner there would show as drift.
- While tracked root `CLAUDE.md` or `AGENTS.md` differs from its mirror in
  `.claude/bootstrap-root/`, `verify.py` cannot build a receipt and stops with
  `receipt metadata control-plane provenance is invalid`. Run
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  after editing either file.
- `README.md`, `docs/`, and the wiki cite the private evidence report of the
  Copilot migration by bracket labels such as `[A6]` after a plain
  description. The report is in `.claude/explorations/` and is not tracked,
  so never cite it by a bare label in a tracked file.
- A one-phase plan gets no knowledge-refresh phase, so the wiki drifts until
  the next refresh. Refresh pages only through the `knowledge-refresh` skill,
  never by hand. PR #56 ended with a knowledge-refresh phase (Phase I).
