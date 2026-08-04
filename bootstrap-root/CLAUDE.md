# Claude Code Bootstrap Guidance

This target is generated from `shared/`. Do not edit generated files manually.

Preserve the pre-flight -> branch -> plan -> implement -> verify -> review -> document -> score -> learn -> session-log -> commit workflow and hook guardrails. Score >= 90 plus required documentation updates are mandatory before commit or PR closeout.

`.claude/` is the canonical shared project space. Custom agents are rendered as Claude Code project subagents in `.claude/agents/`; skills, plans, session logs, quality reports, memory, templates, and hook scripts also live under `.claude/`.

## Workspace

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
- Apply the `ponytail` skill in `full` mode to every coding task.
- Prefer config-first design for new features.
- Verify every change with tests, typing, and linting.
- Review with profile-driven checks before commit or PR.
- After the code review converges, update documentation for changed public interfaces, config, workflows, and user-facing behavior before the persisted score/findings gate (so both reports bind to the final code+docs) and before commit/PR closeout.
- Keep hook guardrails enabled.
- Capture reusable lessons in `.claude/MEMORY.md`.

## Instructions

Always consult the relevant files under `.claude/instructions/`:

| File | Covers |
|---|---|
| `workflow.instructions.md` | Pre-flight -> branch -> plan -> implement -> verify -> review -> document -> score -> learn -> session-log -> commit loop |
| `quality-and-testing.instructions.md` | Verification commands, scoring, and gates |
| `tool-routing.instructions.md` | Direct reads, `rg`, Semble, and context-mode routing |
| `code-standards.instructions.md` | Python architecture and style rules |
| `tests.instructions.md` | Test authoring and mocking boundaries |
| `config-first-design.instructions.md` | Hydra ConfigStore and dataclass config patterns |
| `api-service-standards.instructions.md` | BentoML and API service expectations |
| `deployment.instructions.md` | Deployment and runtime checks |

## Workflow

```text
PRE-FLIGHT -> BRANCH -> PLAN -> PONYTAIL -> IMPLEMENT -> VERIFY -> REVIEW -> DOCUMENT -> SCORE -> LEARN -> SESSION LOG -> COMMIT
```

Use the orchestrated path for ambiguous, multi-file, or control-plane work:

```text
orchestrator -> planner -> coder -> verifier -> reviewer -> documenter -> score
```

Control-plane files include `.claude/hooks/`, `.claude/settings.json`, `.claude/hooks/`, `.codex/`, `.mcp.json`, `.devcontainer/`, `CLAUDE.md`, and `AGENTS.md` — the hook, agent, and config surfaces that affect every session in this project.

## Ponytail Coding Rule

Before writing, adding, fixing, refactoring, reviewing, or designing code, or
choosing a dependency, read `.claude/skills/ponytail/SKILL.md` and apply it in
`full` mode for the whole task. Search for reusable code and trace the real
flow before editing; then prefer YAGNI, existing helpers, the standard library,
native platform features, installed dependencies, and the minimum correct
diff, in that order.

Ponytail never removes required validation, data-loss protection, security,
accessibility, root-cause investigation, or the smallest meaningful regression
check. A user may explicitly select another Ponytail mode for implementation,
but every non-documentation diff still requires the mandatory Ponytail review
before commit or push.

## Agents

| Agent | Purpose |
|---|---|
| `orchestrator` | Coordinates complex workflows and delegates work |
| `planner` | Creates implementation plans with required skills and review profiles |
| `coder` | Implements backend/code changes and Gradio/Streamlit UI changes (loads the `gradio-streamlit` skill), and performs local simplification |
| `reviewer` | Runs profile-driven reviews as two sequential passes (primary then adversarial), with no helper agents |
| `verifier` | Runs final tests, typing, linting, imports, deprecation checks, and scoring |
| `documenter` | Updates documentation after code review converges, before the persisted score/findings gate and commit/PR closeout |

## Review Profiles

This is the **single authoritative profile-routing table**. The unified `reviewer` loads checklists from `.claude/review-profiles/`. Agents and skills reference this table by path rather than restating it.

| Surface | Profiles |
|---|---|
| Python source | `code`, `security`, `ponytail` |
| New modules/refactors | `architecture`, `ponytail` |
| Tests | `tests`, `ponytail` |
| APIs/services | `api`, `security`, `tests`, `ponytail` |
| Configs | `config`, `ponytail` when executable behavior changes |
| I/O-heavy or ML-heavy paths | `performance` |
| Docs/user-facing behavior | `documentation` |
| Domain-specific correctness | `domain` |
| Hooks, scripts, generators, and control-plane code | `code`, `architecture`, `security`, `tests`, `ponytail` |
| Any pre-PR gate | `code`, `security`, `tests`, `ponytail` (minimum for non-documentation diffs) |

## Skills

Skills live under `.claude/skills/`. Each `SKILL.md` has machine-readable `visibility: public|background` metadata:

- `public` skills are intended for direct slash-menu or user-triggered use.
- `background` skills are hidden helpers loaded by description match or by agents.

High-leverage public skills include `ponytail`, `ponytail-review`, `create-feature`, `refactor`, `run-tests`, `code-review`, `review-api`, `hydra-config`, `bentoml-service`, `debug-investigator`, `deep-audit`, `commit`, and `context-status`.

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

## Tool Routing

This file is the authoritative routing policy for retrieval helpers in this bootstrap. Semble and context-mode are retrieval helpers; they do not replace the pre-flight, branch, plan, verify, review, score, document, learn, session-log, commit workflow, hook guardrails, or project-specific instructions.

## Routing Contract

- Use direct file reads when the path is known or the user named a specific file.
- Use `rg` or equivalent exact search for literals, symbols, error text, config keys, and filenames.
- Use Semble for semantic repository discovery: behavior ownership, related-code lookup, architectural neighbors, and "where is this implemented?" questions.
- Use context-mode for large outputs, logs, generated prose, long markdown artifacts, session continuity, and compaction-safe retrieval.
- Use context7 for current external library API documentation (fast-moving stacks like Haystack, BentoML, Hydra, Gradio go stale in training data quickly); it is not a substitute for Semble (repo code), `rg` (literals), or context-mode (long outputs).
- Avoid running broad Semble and context-mode retrieval for the same question unless the first pass leaves a concrete gap.

## Fallback Order

1. Prefer the narrowest reliable source: known file, exact search, or local config.
2. Use Semble when semantic relationships matter more than exact text.
3. Use context-mode when the task depends on large artifacts, conversational continuity, or content likely to be lost during compaction.
4. Inside the generated devcontainer, Semble and context-mode are installed as required tools. Outside that managed environment, if retrieval helpers are unavailable, continue with direct reads and `rg`; missing optional binaries are warnings, not blockers.

## Do Not Use Optional Retrieval For

- Simple edits in already-open files.
- Validation commands, formatting, or test execution.
- Secrets, credentials, or protected files.
- Replacing project instructions, skills, hooks, or review gates.

## Workflow

---

## Plan-First Protocol

**For any non-trivial task (>1 file or >30 min), plan before coding.**

1. Check `.claude/MEMORY.md` for relevant `[LEARN]` entries.
2. For ambiguous/complex tasks: clarify with user (max 3-5 questions), optionally create a spec in `.claude/quality_reports/specs/`.
3. Draft plan -> save to `.claude/plans/` for concrete implementation plans or `.claude/explorations/` for exploratory/PoC plans.
4. Present to user -> wait for approval unless the user explicitly supplied an approved implementation plan.
5. After approval: create session log, then implement via the orchestrator loop.

**Skip planning only for:** single-file fixes, clear-and-specific requests, or when the user provides detailed approved steps.

---

## Branch Lifecycle

- `dev` is the working base branch for implementation work.
- Before starting new work, the current branch must be `dev` and the working tree must be clean.
- Each big plan creates exactly one implementation branch named `<plan_name>_implementation` from `dev`.
- Big plans live at `.claude/plans/<plan_name>.md` and must use `type: big-plan` frontmatter.
- Small plans live at `.claude/plans/<phase_slug>.md` and must use `type: small-plan` frontmatter.
- Commit once per completed small plan after DOCUMENT, LEARN, session log, and score gates pass.
- Open a PR to `dev` only after every small plan in the big plan is complete and only when the user explicitly asks for a PR.
- The user performs merge/squash decisions manually in GitHub. After merge, return to `dev` and pull before starting new work.

---

## Canonical Orchestrator Loop

```text
PRE-FLIGHT -> BRANCH -> PLAN -> PONYTAIL -> IMPLEMENT -> VERIFY -> REVIEW -> DOCUMENT -> SCORE -> LEARN -> SESSION LOG -> COMMIT
```

For each small plan:

1. **PLAN:** Delegate to `planner`; save concrete small-plan file under `.claude/plans/`.
2. **PONYTAIL:** Load `.claude/skills/ponytail/SKILL.md` in `full` mode and pass that requirement to every code-writing delegate.
3. **IMPLEMENT:** Delegate to `coder` (including Gradio/Streamlit UI work).
4. **VERIFY:** Delegate to `verifier`; run tests, typing, linting, imports, and score when available.
5. **REVIEW:** Delegate to `reviewer`; for every non-documentation diff include the `ponytail` profile alongside the normal correctness/security profiles. It runs its own primary and verification passes and returns the surviving findings as JSON (it has no `execute` capability, so it cannot persist them itself). Resolve every surviving Ponytail finding, even `MINOR`, then repeat IMPLEMENT/VERIFY/REVIEW until the review is clean on the code. Do not persist findings yet — persistence happens at step 7 (after DOCUMENT) so the report binds to the final code+docs content.
6. **DOCUMENT:** Delegate to `documenter` with diff range, changed files, and public/config/workflow/user-facing changes. Skip only when the change is purely internal. DOCUMENT runs before the persisted SCORE/FINDINGS so the documenter's tracked edits are inside the content those reports are bound to — otherwise a post-score doc change stales both.
7. **SCORE & PERSIST:** After documentation is final, persist the converged findings with `record_findings.py --profile ponytail --phase <current_phase> --base-ref dev --findings-json <path> --out .claude/quality_reports/findings-<timestamp>.json` and run `quality_score.py` with `--phase <current_phase> --base-ref dev --out .claude/quality_reports/score-<timestamp>.json`. Both artifacts now bind to the final code+docs `content_hash`. Doc-only changes from DOCUMENT are not re-reviewed — the code review already converged; persisting here simply keeps the reports fresh against the committed content. Re-run REVIEW only if a later fix changes code.
8. **FIX LOOP:** If verification, review, or score fails, update TodoWrite, re-add IMPLEMENT/VERIFY/REVIEW/DOCUMENT/SCORE, and repeat until score is >= 90, the findings report has `counts.critical == 0`, and a required Ponytail review has zero surviving Ponytail findings.
9. **LEARN:** Run the `learn` skill and save reusable discoveries to `.claude/MEMORY.md`, or record `[LEARN] none - no new lessons this session`.
10. **SESSION LOG:** Update the closeout session log using `.claude/templates/session-log.md`; final status must be `COMPLETED`.
11. **COMMIT:** Commit the completed small plan atomically.

**Score >= 90 plus a matching findings report with `counts.critical == 0` is required before commit; `counts.major == 0` in that same report is additionally required before PR/push closeout. For non-documentation diffs the report must also have `ponytail_reviewed: true` and `ponytail_findings: 0`.**

---

## Bypass Policy

Commit-gate bypasses are allowed only for commit subjects beginning with:

- `fixup!`
- `squash!`
- `chore(typo):`
- `docs(typo):`

Every successful bypass commit is logged to `.claude/session_logs/hooks-bypass.log`. A PR is blocked until bypasses since the big plan's `started_at` timestamp are acknowledged with `bypass_acknowledged: true` in the big-plan frontmatter.

Environment-variable bypasses are not supported.

---

## Subagent Reporting Style

Subagents reporting back to the orchestrator should use `caveman` `full` for narrative report sections. Preserve tables, code blocks, commands, file paths, identifiers, and structured findings literally. The documenter writes normal user-facing prose.

---

## Session Logging

**Log location:** `.claude/session_logs/YYYY-MM-DD_description.md`

**Log when:**
- After plan approval (goal, approach, rationale)
- During work: design decisions, problems solved, verification results, `[LEARN]` entries
- Before stopping: summary, scores, open questions, next steps
- At small-plan closeout: `**Status:** COMPLETED`, `**Plan:** <small-plan path>`, `[LEARN]` entries or explicit no-lessons marker

**Frequency:** Every 30 responses or at session end, whichever comes first.

Merge-time review reports should be stored in `.claude/quality_reports/merges/`.

---

## Context Management

**Before finishing or when context is getting large:**
1. Save `[LEARN]` entries to `.claude/MEMORY.md`.
2. Update session log.
3. Ensure plan is saved to disk.
4. Document open questions.

**Starting a new session:**
1. Read `.claude/instructions/workspace.md` plus the current plan in `.claude/plans/` or exploration in `.claude/explorations/`.
2. Check `git log --oneline -10` and `git diff`.
3. State understood task and next step.

---

## Recovery Checklist

```text
[ ] On dev before branch creation
[ ] Working tree clean before branch creation
[ ] Big plan and current small plan saved under .claude/plans/
[ ] TodoWrite reflects canonical workflow and current loop
[ ] Verification passed (pytest + mypy + ruff)
[ ] Review passed; findings persisted via record_findings.py (including ponytail_reviewed + zero Ponytail findings for non-documentation diffs)
[ ] Score >= 90 with persisted matching quality report
[ ] Docs updated or explicitly skipped as pure-internal
[ ] Learn entries flushed or explicit no-lessons marker recorded
[ ] Closeout session log has Status: COMPLETED
[ ] Mermaid diagrams render without errors
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

When asked to edit protected files or run blocked git commands, stop and explain why it is protected.

## Automatic Reminders

Some behaviors are automated by hooks. Others are still manual.

**Automated via hooks:**
- Protected file edits are denied.
- Dangerous git commands are denied.
- Implementation branch creation is gated on dev + clean tree + matching big plan.
- Commit closeout is gated on small-plan completion, score >= 90, a matching findings report with `counts.critical == 0`, required Ponytail review evidence, and DOCUMENT/LEARN/session-log evidence.
- PR creation/push is gated on all small plans complete, bypass acknowledgement, required Ponytail review evidence, and the findings report additionally having `counts.major == 0`.
- Session start/end events are logged to `.claude/session_logs/hooks-sessions.log`.
- Session start pulls mutable AI state on the git-backed `ai-state` branch (`.claude/` is its own nested git repo; see `state-sync.sh`). Codex and Claude Stop each use one sequential log/check/checkpoint/publish wrapper; Codex returns JSON-only stdout and Claude emits no wrapper stdout. Both retry compatible `push` at `UserPromptSubmit` (60 seconds). Codex delayed SessionEnd and Claude StopFailure checkpoint locally only; Claude SessionEnd uses compatible `push` (60 seconds). Timeout or network failure preserves the local commit for retry; inspect `state-sync.sh status` and `.claude/session_logs/hooks-errors.log`. Closing a browser or editor tab is not a guaranteed lifecycle event, so do not rely on it for durability. The durable checkpoint-and-publish paths remain the `post-commit` git hook (after every outer-repo commit) and the explicit "AI state: push" VS Code task (manual, for state between commits).
- After an actual install or update, Codex for VS Code may require renewed review of content/hash-bound `.codex/hooks.json`. Reopen/reload the repository and approve project hooks only when Codex prompts; installers report this boundary but never approve hooks or mutate user trust settings.
- Runtime hook errors are logged to `.claude/session_logs/hooks-errors.log`.

**Manual reminders still required:**

**After editing any `src/**/*.py` file:**
```text
Run: uv run pytest tests/ -q --tb=short
Run: uv run mypy src/ --ignore-missing-imports --explicit-package-bases
Run: uv run ruff check src/ tests/
```

**Every ~30 responses or before stopping:**
```text
Update session log in .claude/session_logs/
Flush [LEARN] entries to .claude/MEMORY.md
```

## Quality And Testing

---

## Verification Commands (run after every task)

```bash
uv run pytest tests/ -q --tb=short          # All tests
uv run mypy src/ --ignore-missing-imports --explicit-package-bases  # Type check
uv run ruff check src/ tests/              # Lint (0 violations required)
```

**Testing order:** unit tests -> existing tests (regression) -> E2E (if applicable).
**Never claim completion without running all three unless the repository lacks that surface and you say so.**

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

`quality_score.py` computes a single deterministic number. It runs three tools
(`ruff`, `mypy`, `pytest`) and deducts from a base of **100**. This section
describes the **actual arithmetic the scorer implements** — not an aspirational
rubric. (A false spec is worse than a modest one.)

Starting score: **100**, floored at **0**.

| Signal | Source | Deduction |
|---|---|---|
| Any mypy type errors | `mypy --ignore-missing-imports --explicit-package-bases` | **-20** (binary) |
| Any pytest failures, or tests skipped | `pytest tests/ -q` | **-15** (binary) |
| ruff violations | `ruff check --output-format=json`, per violation, by rule-code prefix | see below |

ruff per-violation deductions (by the leading letters of the rule code):

| Rule prefix | Category | Per violation |
|---|---|---|
| `E`, `W`, `I` | style / whitespace / import order | -1 |
| `D`, `UP` | docstrings / pyupgrade | -2 |
| `G` | logging f-strings | -3 |
| `B`, `S` | bugbear / security (bandit) | -5 |
| any other code | (default) | -2 |

The scorer does **not** independently classify "missing type hints",
"missing docstrings", "no Pydantic validation", etc. — those are surfaced only
insofar as `ruff`/`mypy` emit a rule for them. Treat the tool configuration
(ruff rule selection, mypy strictness) as the real rubric and tune it there.

### Gate metadata (enforced by the commit gate)

The persisted report carries fields the commit gate checks in addition to the
score:

- `tests_passed` must be `true` — a report with `false` or a missing field is
  rejected **even at score 100**.
- `tests_skipped` must not be `true` — `--skip-tests` records `tests_skipped:
  true` and `tests_passed: false`, and the gate refuses it.
- `dirty` must be `false` — `dirty` means the working tree has **unstaged**
  changes to tracked files (the tree does not match the index). Stage
  everything destined for the commit, then re-run the scorer.

### Severity-Gated Findings (Second Artifact)

Numeric self-grading is a known reward-hacking setup once any input is
agent-controlled: clean lint plus a green suite scores 100 regardless of what
the change actually contains. The score above stays the deterministic floor —
it is honest about what it measures (lint/types/tests) — but it says nothing
about what the REVIEW stage found. A second gated artifact closes that gap: a
**findings report**, persisted by `record_findings.py`, carrying the same
git-metadata freshness binding as the score report (`branch`, `head_sha`,
`merge_base_sha`, `base_ref`, `dirty`, `content_hash`) plus computed severity
counts (`critical`, `major`, `minor`).

The reviewer runs its primary + verification passes as usual (see the
`reviewer` agent) and returns the surviving findings as JSON; the reviewer has
no `execute` capability, so **the orchestrator** persists that JSON:

```bash
uv run python .claude/scripts/record_findings.py src/ --profile code --profile security --profile ponytail --phase <current_phase> --base-ref dev --findings-json <path-or-stdin> --out .claude/quality_reports/findings-<timestamp>.json
```

An empty findings list (`[]`) is valid and yields all-zero counts — the normal
"review passed clean" report, not an omission.

**Severity tiering** (mirrors the score/findings binding pattern, tiered by
gate):

| Gate | Requires |
|---|---|
| Commit | `counts.critical == 0` in a fresh, matching findings report |
| Push / PR | `counts.critical == 0` **and** `counts.major == 0` |

The findings remain agent-authored — the gate verifies the contract (fresh,
matching, severity-counted), not the reviewer's honesty. This is the same
consciously-accepted residual as the score report's inputs (see
`docs/plan-deterministic-commit-gate.md` §5).

---

## Gates

| Score | Gate | Action |
|---|---|---|
| >= 95 | Excellence | Aspirational |
| >= 90 | Required | Ready for commit/PR closeout after required documentation updates |
| < 90 | Block | List blocking issues, do not commit or open PR |

---

## Persisted Score Reports

When `.claude/scripts/quality_score.py` is available, score with branch/phase metadata:

```bash
uv run python .claude/scripts/quality_score.py src/ --phase <current_phase> --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

Commit gates read the persisted JSON, not terminal output. A score report must match the current branch and current phase and be newer than the files it gates.

---

## Persisted Findings Reports

When `.claude/scripts/record_findings.py` is available, persist the reviewer's
surviving findings with the same branch/phase metadata as the score report:

```bash
uv run python .claude/scripts/record_findings.py src/ --profile code --profile security --profile ponytail --phase <current_phase> --base-ref dev --findings-json <path-or-stdin> --out .claude/quality_reports/findings-<timestamp>.json
```

Commit and push gates read the persisted JSON, not the reviewer's prose
report. A findings report must match the current branch and phase, be as
fresh as the score report (push gates accept a report generated for an
ancestor of the pushed commit, since REVIEW happens before COMMIT), and carry
`counts.critical == 0` (commit) or `counts.critical == 0` and
`counts.major == 0` (push/PR). Every non-documentation diff must additionally
record `ponytail_reviewed: true` and `ponytail_findings: 0`; the same content
hash makes that review stale after any real diff change.

---

## Common Pitfalls

- **Never assume tests pass** - always run them.
- **Deprecation warnings** = future breakage. Fix immediately, document in MEMORY.md.
- **Mock-heavy tests passing != real code works** - verify with at least one integration test.
- **Partial testing** - run ALL tests, not just new ones. Catch regressions.
