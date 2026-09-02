---
description: "Always-on: Quality gates, verification commands, and testing protocol. Load when verifying or testing code."
applicability: always
---

# Quality Gates & Testing Protocol

---

## Verification Commands

```bash
uv run python .claude/scripts/verify.py fast --format json  # Focused feedback during IMPLEMENT
```

### Deterministic verification evidence

The generated `.claude/scripts/verify.py` is the single authority for
deterministic measurement. It also offers machine-readable `fast`, `phase`,
and `closeout` receipts. During IMPLEMENT, use `fast` and project-native
focused checks; do not repeat the complete fixed suite after every small edit.
The orchestrator runs the authoritative complete suite with `verify phase
--format json --persist` before REVIEW, then runs `verify closeout` after
CLOSEOUT. A completed closeout receipt records exact hashes and paths for its
phase receipt, findings report, and completed session log. Completed commit,
push, and PR gates read that one strict receipt rather than rediscovering a
newest report. `closeout` reuses fresh phase evidence and binds the final
tracked state.

### Consumer-native verification scope

Bootstrap authoring repositories keep explicit `shared`, `scripts`, and
`tests` checks. Installed consumers use project-native configuration: Ruff
checks the project while excluding the bootstrap-owned `.claude` runtime,
pytest uses native discovery, and Mypy uses its selected native config's
`files`, `packages`, or `modules` setting before the conventional `src/`
fallback. If a required scope or selected config cannot be safely resolved,
verification returns `UNVERIFIED`; real lint, type, and test findings remain
`FAIL`.

**Testing order:** unit tests -> existing tests (regression) -> E2E (if applicable).
**Never claim completion without running all three unless the repository lacks that surface and you say so.**

---

## Mock vs Real Objects

See `tests.instructions.md` for detailed mocking rules.

> Quick guideline: Mock external services (API, DB, LLM). Use real objects for configs, dataclasses, pure functions.

---

## Coverage Target

80%+ on critical paths. Bootstrap authoring repositories run
`uv run pytest tests/ --cov=shared --cov=scripts --cov-report=term-missing`;
installed consumers run `uv run pytest tests/ --cov=src --cov-report=term-missing`
(or their project's own configured source root).

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

## Verification Detail

There is no numeric score. A real lint, type, or test problem is `FAIL`; a
tool that could not be measured at all (missing executable, malformed output,
an abnormal exit) is `UNVERIFIED` rather than a silent pass.

| Signal | Source | Result |
|---|---|---|
| Any mypy type errors | `mypy --ignore-missing-imports --explicit-package-bases` | `FAIL` |
| Any pytest failures | `pytest tests/ -q` | `FAIL` |
| Any ruff violations | `ruff check --output-format=json` | `FAIL` |

### Gate metadata (enforced by the commit gate)

The completed closeout receipt binds exact hashes and paths for its phase
receipt, findings report, and completed session log:

- the phase receipt's aggregate `status` must be `PASS` — any `FAIL` or
  `UNVERIFIED` check blocks closeout.
- `dirty` must be `false` in every bound report — `dirty` means the working
  tree has **unstaged** changes to tracked files (the tree does not match the
  index). Stage everything destined for the commit, then re-run verification.

### Severity-Gated Findings

A **findings report**, persisted by `record_findings.py`, carries a
git-metadata freshness binding (`branch`, `head_sha`, `merge_base_sha`,
`base_ref`, `dirty`, `content_hash`) plus computed severity counts
(`critical`, `major`, `minor`).

The reviewer runs its primary + verification passes as usual (see the
`reviewer` agent) and returns the surviving findings as JSON; the reviewer has
no `execute` capability, so **the orchestrator** persists that JSON:

```bash
uv run python .claude/scripts/record_findings.py src/ --profile code --profile security [--profile ponytail] --phase <current_phase> --base-ref dev --findings-json <path-or-stdin> --out .claude/quality_reports/findings-<current_phase>.json
```

An empty findings list (`[]`) is valid and yields all-zero counts — the normal
"review passed clean" report, not an omission.

**Severity tiering:**

| Gate | Requires |
|---|---|
| Phase-completion commit | `counts.critical == 0` **and** `counts.major == 0` in a fresh, matching findings report, and an explicit `disposition` plus non-empty `reason` on every surviving MINOR |
| Push / PR | the same contract, re-checked across every completed phase |

An intermediate commit made while the phase is still in progress is not
blocked merely because an unresolved MAJOR finding exists. MAJOR blocks the
phase-completion commit, not the work leading up to it.

The findings remain agent-authored — the gate verifies the contract (fresh,
matching, severity-counted), not the reviewer's honesty. That is a
consciously-accepted residual, not a gap this gate is meant to close.

---

## Gates

Ready for commit/PR closeout requires a passing `verify phase`/`verify
closeout` receipt plus required documentation updates; any `FAIL` blocks
commit or PR.

---

## Persisted Findings Reports

When `.claude/scripts/record_findings.py` is available, persist the reviewer's
surviving findings with deterministic phase-named output:

```bash
uv run python .claude/scripts/record_findings.py src/ --profile code --profile security [--profile ponytail] --phase <current_phase> --base-ref dev --findings-json <path-or-stdin> --out .claude/quality_reports/findings-<current_phase>.json
```

Commit and push gates read the persisted JSON, not the reviewer's prose
report. A findings report must match the current branch and phase, be as
fresh as the phase receipt (push gates accept a report generated for an
ancestor of the pushed commit, since REVIEW happens before COMMIT), and carry
`counts.critical == 0` and `counts.major == 0` at the phase-completion commit
and again at push/PR, with an explicit `disposition` and non-empty `reason` on
every surviving MINOR. The metadata matrix is exact: selecting the
`ponytail` profile always emits `ponytail_reviewed: true` and a numeric
`ponytail_findings` count; a report for an unselected profile omits both
fields. A routed high-risk review requires true evidence. The
authoritative routing table selects Ponytail for deterministic
control-plane/high-risk, multi-file, dependency, script, generator, or
reviewer-selected complexity. Ordinary low-complexity and exactly one
documentation OR exactly one mutable workflow-state file do not require it unless
control-plane/high-risk precedence applies. Ponytail findings use the ordinary
severity gates: CRITICAL and MAJOR both block the phase-completion commit
(not only push/PR), and a surviving MINOR needs an explicit disposition and
reason but is otherwise advisory. There is no special zero-Ponytail gate.

---

## Common Pitfalls

- **Never assume tests pass** - always run them.
- **Deprecation warnings** = future breakage. Fix immediately, document in MEMORY.md.
- **Mock-heavy tests passing != real code works** - verify with at least one integration test.
- **Partial testing** - run ALL tests, not just new ones. Catch regressions.
