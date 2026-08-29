---
description: "Always-on: Quality gates, verification commands, scoring rubric, and testing protocol. Load when verifying, testing, or scoring code."
applicability: always
---

# Quality Gates & Testing Protocol

---

## Verification Commands

```bash
uv run python .claude/scripts/verify.py fast --format json  # Focused feedback during IMPLEMENT
```

### Deterministic verification evidence

The generated `.claude/scripts/verify.py` also offers machine-readable
`fast`, `phase`, and `closeout` receipts. During IMPLEMENT, use `fast` and
project-native focused checks; do not repeat the complete fixed suite after
every small edit. The orchestrator runs the authoritative complete suite with
`verify phase --format json --persist` before REVIEW, then runs `verify
closeout` after CLOSEOUT. Existing score, findings, and hook gates remain
authoritative until their later migration. `closeout` reuses fresh phase
evidence and binds the final tracked state.

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
uv run python .claude/scripts/record_findings.py src/ --profile code --profile security [--profile ponytail] --phase <current_phase> --base-ref dev --findings-json <path-or-stdin> --out .claude/quality_reports/findings-<timestamp>.json
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
uv run python .claude/scripts/record_findings.py src/ --profile code --profile security [--profile ponytail] --phase <current_phase> --base-ref dev --findings-json <path-or-stdin> --out .claude/quality_reports/findings-<timestamp>.json
```

Commit and push gates read the persisted JSON, not the reviewer's prose
report. A findings report must match the current branch and phase, be as
fresh as the score report (push gates accept a report generated for an
ancestor of the pushed commit, since REVIEW happens before COMMIT), and carry
`counts.critical == 0` (commit) or `counts.critical == 0` and
`counts.major == 0` (push/PR). The metadata matrix is exact: selecting the
`ponytail` profile always emits `ponytail_reviewed: true` and a numeric
`ponytail_findings` count; a new report for an unselected profile omits both
fields. Optional diffs may still read compatible legacy reports containing
`false`/`0`, but a routed high-risk review requires true evidence. The
authoritative routing table selects Ponytail for deterministic
control-plane/high-risk, multi-file, dependency, script, generator, or
reviewer-selected complexity. Ordinary low-complexity and exactly one
documentation OR exactly one mutable workflow-state file do not require it unless
control-plane/high-risk precedence applies. Ponytail findings use the ordinary
severity gates: CRITICAL blocks commit, MAJOR blocks push/PR, and MINOR is
advisory. There is no special zero-Ponytail gate.

---

## Common Pitfalls

- **Never assume tests pass** - always run them.
- **Deprecation warnings** = future breakage. Fix immediately, document in MEMORY.md.
- **Mock-heavy tests passing != real code works** - verify with at least one integration test.
- **Partial testing** - run ALL tests, not just new ones. Catch regressions.
