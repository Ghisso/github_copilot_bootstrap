---
description: "Always-on: Quality gates, verification commands, scoring rubric, and testing protocol. Load when verifying, testing, or scoring code."
---

# Quality Gates & Testing Protocol

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

### Direction (not yet implemented)

Numeric self-grading is a known reward-hacking setup once any input is
agent-controlled. The intended evolution is to replace the numeric threshold
with a **severity-count predicate over review findings** (e.g. "0 criticals, ≤N
majors") rather than a deeper numeric rubric. Until then, the arithmetic above
is the whole story.

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

## Common Pitfalls

- **Never assume tests pass** - always run them.
- **Deprecation warnings** = future breakage. Fix immediately, document in MEMORY.md.
- **Mock-heavy tests passing != real code works** - verify with at least one integration test.
- **Partial testing** - run ALL tests, not just new ones. Catch regressions.
