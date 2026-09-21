# Repository Brief for OpenWiki

## What this repository is

`github_copilot_bootstrap` is a reusable multi-target bootstrap for AI
coding agents, not an application. It packages the hooks, agents, skills,
and instruction files a Python AI engineering project wants available
across GitHub Copilot, Claude Code, OpenAI Codex, and Google Antigravity,
and keeps them consistent through one deterministic build-and-install
pipeline.

Four places hold different parts of the system. Keep them distinct:

- **Authoring source** (`shared/`) is what a maintainer edits: policies,
  agent prompts, skills, hooks, MCP config, templates, and scripts. Every
  real behavior change originates here.
- **Generated build output** (`dist/multi-agent/`), produced by
  `scripts/generate_targets.py`, is a rendered, installable copy of
  `shared/` for one target family. It is never hand-edited, and it is
  gitignored in this repository.
- **A consumer's outer repository** is any project that installs the
  generated bootstrap. It gets root entrypoint files (`AGENTS.md`,
  `CLAUDE.md`, `.mcp.json`, `.codex/**`) and a `.claude/` directory.
- **The nested `.claude` ai-state repository** is its own separate Git
  repository living inside `.claude/`, on a branch named `ai-state`. It
  tracks both the installed bootstrap files and mutable AI state
  (`MEMORY.md`, plans, session logs, quality reports). The outer
  repository's own Git history never shows these commits; inspect them
  with `git -C .claude <command>`.

This repository also installs its own generated output into itself, to
develop and test the bootstrap end to end (`scripts/install_bootstrap.py
--allow-self`). Do not describe that self-install as how a normal consumer
project works — a normal consumer only ever receives the generated copy,
never `shared/`.

## What to prioritize

Ground every page in what the current code and tests actually do, in this
order of authority:

1. `shared/`, `scripts/`, and `tests/` — the real source and its test
   coverage.
2. `README.md` and `docs/architecture.md` — maintained, current
   human-authored explanation.
3. `shared/policies/*.instructions.md` and `shared/skills/*/SKILL.md` — the
   normative rules and reusable workflows agents follow.

Cover, at minimum:

- the lifecycle: PRE-FLIGHT -> BRANCH -> PLAN when needed -> IMPLEMENT ->
  VERIFY -> REVIEW -> CLOSEOUT -> COMMIT -> PUSH;
- the agent roster (orchestrator, planner, coder, reviewer, documenter, and
  the target-specific extras) and how each specialist gets its prompt;
- the skill library and the contract `scripts/validate_targets.py`
  enforces on it;
- the hook dispatcher and guardrail scripts under `shared/hooks/`;
- how `scripts/generate_targets.py` renders `shared/` into a target;
- how `scripts/install_bootstrap.py` and `scripts/check_runtime.py`
  establish and check consumer ownership (which files are
  bootstrap-controlled versus consumer-owned);
- the Git-backed AI-state sync described above
  (`shared/hooks/scripts/state-sync.sh`);
- the Context Mode dispatcher's security model: cache quarantine by the
  provenance secret, `CONTEXT_MODE_DIR` containment, and the version-pin
  self-check (`shared/hooks/scripts/context-mode-dispatch.sh`, README's
  "Optional Retrieval Helpers").

## Historical records are not current behavior

Treat the following as evidence of past decisions only, never as a
description of what the code currently does. Re-derive current behavior
from `shared/`, `scripts/`, and `tests/` instead:

- `.claude/plans/` and `.claude/session_logs/` — this checkout's own
  completed and in-progress plans and session logs;
- files under `docs/` named `docs/2026-*` — dated, point-in-time spikes and
  review records;
- the root-level `plans/` directory — architecture decision records and
  historical phase plans.

A plan or session log can describe a decision a later phase reversed or
refined. Only the current source and tests are authoritative.

## Do not do

- Do not treat this brief, or anything generated under `openwiki/`, as more
  authoritative than `shared/`, `scripts/`, `tests/`, or the policies under
  `shared/policies/`.
- Do not describe the devcontainer or CI as something every consumer runs;
  both are optional.
