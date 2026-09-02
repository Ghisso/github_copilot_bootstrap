---
description: "Always-on: shared workspace guidance, agents, review profiles, skills, and verification defaults."
applicability: always
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

- Plan first when plan creation is needed for non-trivial work; an approved implementation-ready plan follows the conditional planner route in `workflow.instructions.md`.
- Search before writing new code.
- During IMPLEMENT, the coder applies the `ponytail` skill in `full` mode once
  per coding task, then performs a lightweight simplification and re-verifies
  only the changed scope. This is coder discipline, not a separate lifecycle
  phase.
- Prefer config-first design for new features.
- Verify every change with tests, typing, and linting.
- Review with profile-driven checks before commit or PR.
- After the code review converges, update documentation for changed public interfaces, config, workflows, and user-facing behavior before the persisted findings gate (so the report binds to the final code+docs) and before commit/PR closeout.
- Keep hook guardrails enabled.
- Capture reusable lessons in `.claude/MEMORY.md`.

## Instructions

Always consult the relevant files under `.claude/instructions/`:

| File | Covers |
|---|---|
| `workflow.instructions.md` | Pre-flight -> branch -> plan when needed -> implement -> verify -> review -> closeout -> commit loop |
| `quality-and-testing.instructions.md` | Verification commands and gates |
| `tool-routing.instructions.md` | Direct reads, `rg`, Semble, and context-mode routing |
| `code-standards.instructions.md` | Python architecture and style rules |
| `tests.instructions.md` | Test authoring and mocking boundaries |
| `config-first-design.instructions.md` | Hydra ConfigStore and dataclass config patterns |
| `api-service-standards.instructions.md` | BentoML and API service expectations |
| `deployment.instructions.md` | Deployment and runtime checks |

## Workflow

```text
PRE-FLIGHT -> BRANCH -> PLAN when needed -> IMPLEMENT -> VERIFY -> REVIEW -> CLOSEOUT -> COMMIT
```

Classify work with the single authoritative **Task Lanes** table in
`workflow.instructions.md` before acting. Read-only/reporting and explicitly
eligible lightweight edits stay with the main agent; all commit/PR-bound,
standard, and control-plane/high-risk work follows the lifecycle. Use the
orchestrated path for standard and control-plane/high-risk work:

```text
orchestrator -> [planner when needed] -> coder -> verify phase -> reviewer -> closeout
```

Control-plane files include `.claude/hooks/`, `.claude/settings.json`, `.github/hooks/`, `.codex/`, `.mcp.json`, `.devcontainer/`, `CLAUDE.md`, and `AGENTS.md` — the hook, agent, and config surfaces that affect every session in this project. They always use the full control-plane/high-risk lane.

## Ponytail Coding Rule

Before writing, adding, fixing, refactoring, or designing code, read
`.claude/skills/ponytail/SKILL.md` and apply it once in `full` mode during
IMPLEMENT. Search for reusable code and trace the real flow before editing;
then prefer YAGNI, existing helpers, the standard library, native platform
features, installed dependencies, and the minimum correct conceptual diff, in
that order. Re-check the changed scope after simplification.

Ponytail never removes required validation, data-loss protection, security,
accessibility, root-cause investigation, or the smallest meaningful regression
check. Here, minimal means the fewest necessary concepts, dependencies,
abstractions, layers, configuration, execution paths, and behaviors; clarity
and maintainability outrank reducing physical line count.

## Agents

| Agent | Purpose |
|---|---|
| `orchestrator` | Coordinates complex workflows, runs deterministic `verify phase`, and owns CLOSEOUT ordering |
| `planner` | Creates implementation plans with required skills and review profiles |
| `coder` | Implements backend/code changes and Gradio/Streamlit UI changes (loads the `gradio-streamlit` skill), and performs local simplification |
| `reviewer` | Runs profile-driven reviews as two sequential passes (primary then adversarial), with no helper agents |
| `documenter` | Updates documentation after code review converges, before the persisted findings gate and commit/PR closeout |

## Review Profiles

This is the **single authoritative profile-routing table**. The unified `reviewer` loads checklists from `.claude/review-profiles/`. Agents and skills reference this table by path rather than restating it.

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

Ponytail is required for every control-plane/high-risk diff and every diff that
introduces or substantially changes abstractions, dependencies, architecture,
generalized infrastructure, configuration, execution paths, or behavior. It is
optional for ordinary low-complexity work. An exemption is exactly one
documentation OR one mutable workflow-state file, only when no
control-plane/high-risk condition applies. Every multi-file diff is
control-plane/high-risk and therefore is not exempt.

## Skills

Skills live under `.claude/skills/`. Each `SKILL.md` has machine-readable `visibility: public|background` metadata:

- `public` skills are intended for direct slash-menu or user-triggered use.
- `background` skills are hidden helpers loaded by description match or by agents.

High-leverage public skills include `ponytail`, `ponytail-review`, `create-feature`, `refactor`, `run-tests`, `code-review`, `review-api`, `hydra-config`, `bentoml-service`, `debug-investigator`, `deep-audit`, `commit`, and `context-status`.

## Verification

```bash
uv run python .claude/scripts/verify.py fast --format json                # during IMPLEMENT
uv run python .claude/scripts/verify.py phase --format json --persist     # before REVIEW
uv run python .claude/scripts/verify.py closeout --format json --persist  # after CLOSEOUT
```

`verify.py` inspects the repository and selects the matching scope — the
bootstrap authoring repository's explicit `shared`/`scripts`/`tests`, or an
installed consumer's own project layout — so routing through it here cannot
drift from what the gate actually checks. See
`quality-and-testing.instructions.md` for the full verification and
severity-gating contract.

Quality gates:

| Verification | Gate |
|---|---|
| `verify phase`/`verify closeout` PASS | Commit/PR closeout ready after required documentation updates |
| `FAIL` | Blocked |

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

## Bootstrap Hooks Runtime Contract

Standalone bootstrap hooks execute with bare system `python3` (not `uv run` or a project-managed environment) to function before project infrastructure initializes.

**Minimum Python version:** 3.9

Hook Python code is limited to:
- Standard library modules available in Python 3.9 (`json`, `re`, `sys`, `pathlib`, `datetime`, `stat`)
- No external packages or project dependencies
- Must not runtime-evaluate syntax or stdlib features that require Python newer than 3.9. Use `from __future__ import annotations` when newer annotation syntax (e.g. `X | Y`) is otherwise safe to parse on Python 3.9

When adding new hook Python code, verify it compiles under Python 3.9 with `python3 -m py_compile` and add regression coverage to the test suite (see `tests/test_hook_gates.py`).
