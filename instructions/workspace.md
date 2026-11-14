---
description: "Always-on: shared workspace guidance, agents, review profiles, skills, and verification defaults."
applicability: always
---

# Shared Workspace Instructions -- Python AI Engineering

**Python:** 3.12+ | **Package Manager:** uv | **Common frameworks:** Hydra, BentoML, Haystack, Gradio

## Package Manager: uv

Always use `uv`. Run every Python command through `uv run`, add dependencies with `uv add`, and install from a lockfile with `uv sync`. Avoid bare `python`, `python3`, `pip`, `pytest`, `ruff`, or `mypy` unless the user or a tool outside uv's control requires it.

## Core Principles

- Plan first when plan creation is needed for non-trivial work; an approved implementation-ready plan follows the conditional planner route in `workflow.instructions.md`.
- Search before writing new code. Prefer config-first design for new features.
- Before writing, fixing, refactoring, or designing code, read `.claude/skills/ponytail/SKILL.md` and apply it in `full` mode once per coding task during IMPLEMENT.
- Keep hook guardrails enabled. Capture reusable lessons in `.claude/MEMORY.md`.
- Hooks block edits to secret-bearing files (`.env*`, `*.pem`, `*.key`, `*secret*`, `credentials*`) and `uv.lock`, and block destructive Git commands (`git push --force`/`-f`, `git reset --hard`, `git clean -fd`, `git branch -D main`/`master`). If asked to change or run one, stop and explain why it is protected.

## Knowledge Ownership

This is the single authoritative knowledge-ownership contract; other files link here instead of restating it. Central rule: **OpenWiki is derived context, not authority.**

| Layer | What it is | Authority |
|---|---|---|
| Source and tests | The actual code, configuration, and test suite | Authoritative for current behavior. Nothing else in this table overrides it. |
| Human-authored policy and decisions | `shared/policies/*.instructions.md`, security requirements, ADRs, operator runbooks, explicit project decisions | Authoritative for process, security, and explicit choices. |
| `.claude/MEMORY.md` | Curated cross-session learning | Authoritative only for what repository evidence cannot reliably re-derive: rationale, operational caveats, and confirmed environmental behavior. Do not duplicate source-derived facts here. |
| `openwiki/INSTRUCTIONS.md` | A human-authored repository brief | Human-authored, and it doubles as the deterministic marker that OpenWiki is enabled for this repository. |
| Generated `openwiki/**` pages | OpenWiki's own generated wiki content | Derived descriptive knowledge only. Never hand-edited, and never outranks any layer above it. |

If a generated wiki page and the source disagree, the source is right: refresh or ignore the page, and never change the source to match it. Plans, explorations, session logs, findings, and receipts are historical evidence, not authority for current behavior.

## Instructions

Relevant files under `.claude/instructions/`:

| File | Covers |
|---|---|
| `workflow.instructions.md` | Task Lanes, plan first, branches, orchestrator loop |
| `closeout.instructions.md` | CLOSEOUT steps, through commit and push |
| `plan-lifecycle.instructions.md` | Future phases, pause, cancel, reopen, knowledge-refresh final phase |
| `quality-and-testing.instructions.md` | Verification commands, severity gates, findings |
| `tool-routing.instructions.md` | Direct reads, `rg`, Semble, context-mode |
| `code-standards`, `tests`, `config-first-design`, `api-service-standards`, `deployment` (each `.instructions.md`) | Path-scoped rules |

## Workflow

Classify work with the single authoritative **Task Lanes** table in `workflow.instructions.md` before acting. Use the orchestrated path for standard and control-plane/high-risk work:

```text
orchestrator -> [planner when needed] -> coder -> focused/fast verification -> reviewer -> closeout
```

Control-plane files include root guidance (`CLAUDE.md`, `AGENTS.md`), `.claude/hooks/`, `.claude/settings.json`, `.github/hooks/`, `.codex/`, `.agents/`, `.mcp.json`, `.vscode/mcp.json`, and `.devcontainer/`. They always use the full control-plane/high-risk lane. The commit gate is wider: it also treats `shared/` and every tracked path under `.claude/`, `.codex/`, `.agents/`, `.github/`, and `.devcontainer/` as control plane.

## Agents

`orchestrator` coordinates complex workflows, runs `verify phase`, and owns CLOSEOUT ordering. `planner` writes plans. `coder` implements code and Gradio/Streamlit UI changes (loading the `gradio-streamlit` skill). `reviewer` runs two sequential passes with no helper agents. `documenter` updates documentation after review.

## Review Profiles

This is the **single authoritative profile-routing table**. The `reviewer` loads checklists from `.claude/review-profiles/`; agents and skills reference this table by path.

| Surface | Profiles |
|---|---|
| Python source | `code`, `security`; add `ponytail` when complexity expands |
| New modules/refactors | `architecture`; add `ponytail` when complexity expands |
| Tests | `tests`; add `ponytail` when complexity expands |
| APIs/services | `api`, `security`, `tests`; add `ponytail` when complexity expands |
| Configs | `config`; add `ponytail` when executable behavior changes or complexity expands |
| I/O-heavy or ML-heavy paths | `performance` |
| Docs/user-facing behavior | `documentation` |
| Domain-specific correctness | `domain` |
| Hooks, scripts, generators, and control-plane code | `code`, `architecture`, `security`, `tests`, `ponytail` |
| Any pre-PR gate | `code`, `security`, `tests`; add `ponytail` for control-plane/high-risk or complexity-expanding diffs |

Ponytail is required for every control-plane/high-risk diff and every diff that introduces or substantially changes abstractions, dependencies, architecture, infrastructure, configuration, execution paths, or behavior; it is optional for ordinary low-complexity work. The only exemption is exactly one documentation OR one mutable workflow-state file with no control-plane/high-risk condition; every multi-file diff is control-plane/high-risk. The commit gate enforces that deterministic part; complexity expansion in one ordinary file is the reviewer's call.

**Required profiles by changed path.** The commit gate requires `profiles_reviewed` to include every profile the closeout receipt's `changed_paths` call for. A test path (under `tests/`, or named `test_*.py`, `*_test.py`, or `conftest.py`) requires only `tests`. Any other control-plane or generator path (`scripts/`, `shared/scripts/`) or dependency file (`DEPENDENCY_FILES` in `verify.py`, `pyproject.toml`, `requirements*.txt` or `.in`) requires `code`, `architecture`, `security`, `tests`, and `ponytail`. Documentation-only paths require none. Paths accumulate from the merge-base.

## Skills

Skills live under `.claude/skills/`; each `SKILL.md` has `visibility: public|background` metadata. Both values are listed to the model with their descriptions, and `visibility` marks only the intended use: `public` for slash-menu or user-triggered use, `background` for loading by description match or from agents.

## Verification

Run `uv run python .claude/scripts/verify.py fast --format json` during IMPLEMENT; `closeout.instructions.md` covers `verify phase` and `verify closeout`. A `FAIL` blocks commit and PR.

## Project State

**Project:** github_copilot_bootstrap
**Stack:** Python 3.12+ with uv; adapt framework guidance to the target repo.
