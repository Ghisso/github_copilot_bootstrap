# OpenAI Codex Bootstrap Guidance

This target is generated from `shared/`. Do not edit generated files manually.

Preserve the plan -> implement -> verify -> review -> score workflow and hook guardrails.

`.claude/` is the canonical shared project space for skills, plans, session logs, quality reports, memory, templates, and hook scripts. Codex discovers those skills through `.codex/config.toml`, so trust this project before expecting project skill wiring and hooks to load. Custom agents stay as thin Codex adapters in `.codex/agents/*.toml` and point back to `.claude/agents/`.

## Workspace

**Python:** 3.12+ | **Package Manager:** uv | **Common frameworks:** Hydra, BentoML, Haystack, Gradio

This file is target-neutral source guidance. Generated Copilot, Claude Code, and Codex adapters point back to the shared `.claude/` basis.

## Core Principles

- Plan first for non-trivial work.
- Search before writing new code.
- Prefer config-first design for new features.
- Verify every change with tests, typing, and linting.
- Review with profile-driven checks before commit or PR.
- Keep hook guardrails enabled.
- Capture reusable lessons in `.claude/MEMORY.md`.

## Instructions

Always consult the relevant files under `.claude/instructions/`:

| File | Covers |
|---|---|
| `workflow.instructions.md` | Plan -> implement -> verify -> review -> score loop |
| `quality-and-testing.instructions.md` | Verification commands, scoring, and gates |
| `tool-routing.instructions.md` | Direct reads, `rg`, Semble, and context-mode routing |
| `code-standards.instructions.md` | Python architecture and style rules |
| `tests.instructions.md` | Test authoring and mocking boundaries |
| `config-first-design.instructions.md` | Hydra ConfigStore and dataclass config patterns |
| `api-service-standards.instructions.md` | BentoML and API service expectations |
| `deployment.instructions.md` | Deployment and runtime checks |

## Workflow

```text
PLAN -> IMPLEMENT -> VERIFY -> REVIEW -> FIX -> SCORE
```

Use the orchestrated path for ambiguous, multi-file, or control-plane work:

```text
orchestrator -> planner -> coder/designer -> reviewer -> verifier
```

Control-plane files include `shared/**`, `.devcontainer/**`, target-native hook/agent/config adapters, generated adapters/config, and root guidance files.

## Agents

| Agent | Purpose |
|---|---|
| `orchestrator` | Coordinates complex workflows and delegates work |
| `planner` | Creates implementation plans with required skills and review profiles |
| `coder` | Implements backend/code changes and performs local simplification |
| `designer` | Implements Gradio/Streamlit UI changes |
| `reviewer` | Runs profile-driven dual-pass reviews |
| `review-pass-primary` | Hidden primary review helper |
| `review-pass-adversarial` | Hidden adversarial review helper |
| `verifier` | Runs final tests, typing, linting, imports, deprecation checks, and scoring |

## Review Profiles

The unified `reviewer` loads checklists from `.claude/review-profiles/`:

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
uv run python .claude/scripts/quality_score.py src/ --json
```

Quality gates:

| Score | Gate |
|---|---|
| >= 90 | PR-ready |
| >= 80 | Commit-ready |
| < 80 | Blocked |

## Project State

**Project:** [TODO: project name and one-liner description]
**Stack:** Python 3.12+ with uv; adapt framework guidance to the target repo.
**Active work:** Check `.claude/plans/` and `.claude/explorations/`.

## Tool Routing

This file is the authoritative routing policy for retrieval helpers in this bootstrap. Semble and context-mode are optional helpers; they do not replace the plan, verify, review, score loop, hook guardrails, or project-specific instructions.

## Routing Contract

- Use direct file reads when the path is known or the user named a specific file.
- Use `rg` or equivalent exact search for literals, symbols, error text, config keys, and filenames.
- Use Semble for semantic repository discovery: behavior ownership, related-code lookup, architectural neighbors, and "where is this implemented?" questions.
- Use context-mode for large outputs, logs, generated prose, long markdown artifacts, session continuity, and compaction-safe retrieval.
- Avoid running broad Semble and context-mode retrieval for the same question unless the first pass leaves a concrete gap.

## Fallback Order

1. Prefer the narrowest reliable source: known file, exact search, or local config.
2. Use Semble when semantic relationships matter more than exact text.
3. Use context-mode when the task depends on large artifacts, conversational continuity, or content likely to be lost during compaction.
4. If optional tools are unavailable, continue with direct reads and `rg`; missing optional binaries are warnings, not blockers.

## Do Not Use Optional Retrieval For

- Simple edits in already-open files.
- Validation commands, formatting, or test execution.
- Secrets, credentials, or protected files.
- Replacing project instructions, skills, hooks, or review gates.

## Workflow

---

## Plan-First Protocol

**For any non-trivial task (>1 file or >30 min), plan before coding.**

1. Check `.claude/MEMORY.md` for relevant `[LEARN]` entries
2. For ambiguous/complex tasks: clarify with user (max 3-5 questions), optionally create a spec in `.claude/quality_reports/specs/`
3. Draft plan → save to `.claude/plans/YYYY-MM-DD_short-description.md` (for concrete implementation plans) or `.claude/explorations/YYYY-MM-DD_description/` (for exploratory/PoC plans)
4. Present to user → wait for approval
5. After approval: create session log, then implement via Orchestrator Loop

**Skip planning for:** single-file fixes, clear-and-specific requests, or when user provides detailed steps.

---

## Orchestrator Loop (After Plan Approval)

```
IMPLEMENT → VERIFY → REVIEW → FIX → RE-VERIFY → SCORE
    ↑                                              |
    └──────── loop (max 5 rounds) ←────────────────┘
```

**IMPLEMENT:** Config-first: create dataclass + ConfigStore before feature code. Test-as-you-go.

**VERIFY:**
```bash
uv run pytest tests/ -q
uv run mypy src/ --ignore-missing-imports --explicit-package-bases
uv run ruff check src/ tests/
```

**Review profiles by file type:**

| Pattern | `reviewer` profiles |
|---|---|
| `src/**/*.py` | `code`, `security`; add `architecture` for new modules/refactors |
| `tests/**/*.py` | `tests` |
| `service.py`, `src/api/**` | `api`, `security`, `tests` |
| `src/configs/**` | `config` |
| docs/user-facing behavior | `documentation` |

**FIX:** Critical → Major → Minor order.

**SCORE:** See `quality-and-testing.instructions.md` rubric.
- Score ≥ 80 = commit
- Score ≥ 90 = PR-ready

**"Just do it" mode:** Skip final approval pause, auto-commit if score ≥ 80, still run full loop.

---

## Session Logging

**Log location:** `.claude/session_logs/YYYY-MM-DD_description.md`

**Log when:**
- After plan approval (goal, approach, rationale)
- During work: design decisions, problems solved, verification results, `[LEARN]` entries
- Before stopping: summary, scores, open questions, next steps

**Frequency:** Every 30 responses or at session end (whichever comes first).

Merge-time review reports should be stored in `.claude/quality_reports/merges/`.

---

## Context Management

**Before finishing or when context is getting large:**
1. Save `[LEARN]` entries to `.claude/MEMORY.md`
2. Update session log
3. Ensure plan is saved to disk
4. Document open questions

**Starting a new session:**
1. Read `.claude/instructions/workspace.md` + most recent plan in `.claude/plans/` or exploration in `.claude/explorations/`
2. Check `git log --oneline -10` and `git diff`
3. State understood task and next step

---

## Recovery Checklist

```
[ ] Plan saved to .claude/plans/ or .claude/explorations/
[ ] Session log created/updated
[ ] MEMORY.md has all [LEARN] entries
[ ] Verification passed (pytest + mypy + ruff)
[ ] Score ≥ threshold before commit/PR
```

---

## File Protection Rules

These protections are enforced by target-native hook adapters that call shared scripts in `.claude/hooks/scripts/`.

**Never modify these files directly** (edit manually only):
- `.env`, `.env.*`, `.env.local`
- `*.pem`, `*.key`, `*secret*`, `credentials*`
- `uv.lock` (managed by uv, not hand-edited)

Also blocked in pre-tool hooks:
- Dangerous git commands: `git push --force`, `git push -f`, `git reset --hard`, `git branch -D main/master`, `git clean -fd`

When asked to edit protected files or run blocked git commands, stop and explain why it's protected.


## Automatic Reminders

Some behaviors are automated by hooks. Others are still manual.

**Automated via hooks:**
- Protected file edits are denied
- Dangerous git commands are denied
- Session start/end events are logged to `.claude/session_logs/hooks-sessions.log`
- Session stop pushes mutable AI state to the configured Hugging Face bucket when auth is available
- Runtime hook errors are logged to `.claude/session_logs/hooks-errors.log`

**Manual reminders still required:**

**After editing any `src/**/*.py` file:**
```
→ Run: uv run pytest tests/ -q --tb=short
```

**Every ~30 responses or before stopping:**
```
→ Update session log in .claude/session_logs/
→ Flush [LEARN] entries to .claude/MEMORY.md
```

**When the conversation is long / context is filling up:**
```
→ Save plan to .claude/plans/ (implementation) or .claude/explorations/ (research/PoC)
→ Update MEMORY.md with all [LEARN] entries
→ Write session log with open questions and next steps
```

## Quality And Testing

---

## Verification Commands (run after every task)

```bash
uv run pytest tests/ -q --tb=short          # All tests
uv run mypy src/ --ignore-missing-imports --explicit-package-bases  # Type check
uv run ruff check src/ tests/              # Lint (0 violations required)
```

**Testing order:** unit tests → existing tests (regression) → E2E (if applicable).
**Never claim completion without running all three.**

---

## Mock vs Real Objects

See `tests.instructions.md` for detailed mocking rules.

> Quick guideline: Mock external services (API, DB, LLM). Use real objects for configs, dataclasses, pure functions.

---

## Coverage Target

80%+ on critical paths (`src/`). Run: `uv run pytest tests/ --cov=src --cov-report=term-missing`

Every bug fix MUST include a regression test.

---

## Async Tests

```python
@pytest.mark.asyncio
async def test_async_operation() -> None:
    result = await my_async_function()
    assert result is not None
```

---

## Quality Scoring Rubric

### Python Source (`src/**/*.py`)

| Severity | Issue | Deduction |
|---|---|---|
| Critical | Syntax errors / module won't import | -100 |
| Critical | mypy type errors | -20 |
| Critical | Security vulnerability (hardcoded secrets, injection, unsafe deser.) | -20 |
| Critical | Missing tests for new public functions | -15 |
| Major | Missing type hints on public functions | -10 |
| Major | Missing Google-style docstrings on public functions | -5 |
| Major | Deprecated types (`List`/`Dict`/`Optional`) | -5 |
| Major | ruff lint errors | -3 per error |
| Major | f-strings in logging | -3 |
| Minor | Import order violation | -2 |
| Minor | Line length > 120 chars | -1 per occurrence |

### Test Files (`tests/**/*.py`)

| Severity | Issue | Deduction |
|---|---|---|
| Critical | No assertions in test | -20 |
| Critical | Test passes when it should fail | -20 |
| Major | No edge cases | -10 |
| Major | Inappropriate mocking (mocking what you own) | -5 |
| Major | Missing parametrize for multi-input tests | -3 |

### API Services (`service.py`, `src/api/**`)

| Severity | Issue | Deduction |
|---|---|---|
| Critical | No Pydantic input validation | -15 |
| Critical | No error handling on endpoints | -10 |
| Major | Secrets in code (not env vars) | -20 |
| Major | Missing async for I/O endpoints | -5 |
| Major | No health check endpoint | -5 |

### Config Files (`src/configs/**`)

| Severity | Issue | Deduction |
|---|---|---|
| Critical | Hardcoded values that should be configurable | -10 |
| Critical | Missing `__post_init__` validation | -5 |
| Major | Config not registered with ConfigStore | -10 |

---

## Gates

| Score | Gate | Action |
|---|---|---|
| ≥ 95 | Excellence | Aspirational |
| ≥ 90 | PR-ready | Ready for review/deploy |
| ≥ 80 | Commit | Good enough to save |
| < 80 | Block | List blocking issues, do not commit |

---

## Common Pitfalls

- **Never assume tests pass** — always run them.
- **Deprecation warnings** = future breakage. Fix immediately, document in MEMORY.md.
- **Mock-heavy tests passing ≠ real code works** — verify with at least one integration test.
- **Partial testing** — run ALL tests, not just new ones. Catch regressions.
