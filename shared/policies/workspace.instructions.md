---
description: "Always-on: shared workspace guidance, agents, review profiles, skills, and verification defaults."
---

# Shared Workspace Instructions -- Python AI Engineering

**Python:** 3.12+ | **Package Manager:** uv | **Common frameworks:** Hydra, BentoML, Haystack, Gradio

This file is target-neutral source guidance. Generated Copilot, Claude Code, and Codex adapters point back to the shared `.claude/` basis.

## Package Manager: uv

Always use `uv` — never invoke `python`, `pip`, or `python -m` directly.

| Instead of | Use |
|---|---|
| `python script.py` | `uv run python script.py` |
| `python -m pytest` | `uv run pytest` |
| `pip install foo` | `uv add foo` |
| `pip install -r requirements.txt` | `uv sync` |
| `python -m mypy src/` | `uv run mypy src/` |
| `python -m ruff check` | `uv run ruff check` |

`uv` manages the virtualenv automatically — no manual activation needed.

## Core Principles

- Plan first for non-trivial work.
- Search before writing new code.
- Prefer config-first design for new features.
- Verify every change with tests, typing, and linting.
- Review with profile-driven checks before commit or PR.
- After score >= 90, update documentation for changed public interfaces, config, workflows, and user-facing behavior before commit/PR closeout.
- Keep hook guardrails enabled.
- Capture reusable lessons in `.claude/MEMORY.md`.

## Instructions

Always consult the relevant files under `.claude/instructions/`:

| File | Covers |
|---|---|
| `workflow.instructions.md` | Pre-flight -> branch -> plan -> implement -> verify -> review -> score -> document -> learn -> session-log -> commit loop |
| `quality-and-testing.instructions.md` | Verification commands, scoring, and gates |
| `tool-routing.instructions.md` | Direct reads, `rg`, Semble, and context-mode routing |
| `code-standards.instructions.md` | Python architecture and style rules |
| `tests.instructions.md` | Test authoring and mocking boundaries |
| `config-first-design.instructions.md` | Hydra ConfigStore and dataclass config patterns |
| `api-service-standards.instructions.md` | BentoML and API service expectations |
| `deployment.instructions.md` | Deployment and runtime checks |

## Workflow

```text
PRE-FLIGHT -> BRANCH -> PLAN -> IMPLEMENT -> VERIFY -> REVIEW -> SCORE -> DOCUMENT -> LEARN -> SESSION LOG -> COMMIT
```

Use the orchestrated path for ambiguous, multi-file, or control-plane work:

```text
orchestrator -> planner -> coder -> verifier -> reviewer -> score -> documenter
```

Control-plane files include `shared/**`, `.devcontainer/**`, target-native hook/agent/config adapters, generated adapters/config, and root guidance files.

## Agents

| Agent | Purpose |
|---|---|
| `orchestrator` | Coordinates complex workflows and delegates work |
| `planner` | Creates implementation plans with required skills and review profiles |
| `coder` | Implements backend/code changes and Gradio/Streamlit UI changes (loads the `gradio-streamlit` skill), and performs local simplification |
| `reviewer` | Runs profile-driven reviews as two sequential passes (primary then adversarial), with no helper agents |
| `verifier` | Runs final tests, typing, linting, imports, deprecation checks, and scoring |
| `documenter` | Updates documentation after score passes and before commit/PR closeout |

## Review Profiles

This is the **single authoritative profile-routing table**. The unified `reviewer` loads checklists from `.claude/review-profiles/`. Agents and skills reference this table by path rather than restating it.

| Surface | Profiles |
|---|---|
| Python source | `code`, `security` |
| New modules/refactors | `architecture` |
| Tests | `tests` |
| APIs/services | `api`, `security`, `tests` |
| Configs | `config` |
| I/O-heavy or ML-heavy paths | `performance` |
| Docs/user-facing behavior | `documentation` |
| Domain-specific correctness | `domain` |
| Any pre-PR gate | `code`, `security`, `tests` (minimum) |

## Skills

Skills live under `.claude/skills/`. Each `SKILL.md` has machine-readable `visibility: public|background` metadata:

- `public` skills are intended for direct slash-menu or user-triggered use.
- `background` skills are hidden helpers loaded by description match or by agents.

High-leverage public skills include `create-feature`, `refactor`, `run-tests`, `code-review`, `review-api`, `hydra-config`, `bentoml-service`, `debug-investigator`, `deep-audit`, `commit`, and `context-status`.

## Verification

```bash
uv run pytest tests/ -q --tb=short
uv run mypy src/ --ignore-missing-imports --explicit-package-bases
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

When available, run:

```bash
uv run python .claude/scripts/quality_score.py src/ --phase <current_phase> --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

Quality gates:

| Score | Gate |
|---|---|
| >= 90 | Commit/PR closeout ready after required documentation updates |
| < 90 | Blocked |

## Project State

**Project:** [TODO: project name and one-liner description]
**Stack:** Python 3.12+ with uv; adapt framework guidance to the target repo.
**Active work:** Check `.claude/plans/` and `.claude/explorations/`.

## Command Defaults

- Use `uv` by default for Python execution, scripts, tests, linting, type checks, and dependency management.
- Prefer `uv run ...` commands over invoking `python`, `python3`, `pip`, or tool entrypoints directly, unless a project instruction or tool limitation explicitly requires otherwise.

## Python Command Policy

- Default to `uv run` for project Python commands, including scripts, module entrypoints, test runs, linters, formatters, and type checkers.
- Avoid bare `python`, `python3`, `pip`, `pytest`, `ruff`, or `mypy` invocations in normal workflow unless explicitly required by the user or by tooling outside uv's control.
