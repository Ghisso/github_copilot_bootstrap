---
name: pre-receipt-phase-exemption
type: big-plan
status: in-progress
originating_branch: dev
implementation_branch: pre-receipt-phase-exemption_implementation
started_at: 2026-10-23T09:26:43Z
phases:
  - 2026-10-23_phase-A-pre-receipt-phase-exemption
current_phase: 2026-10-23_phase-A-pre-receipt-phase-exemption
---

# Big Plan: Pre-Receipt Phase Exemption

## Context

A closeout receipt is the file `.claude/quality_reports/verification-closeout-<phase>.json`. `verify.py closeout --persist` writes it to prove a phase passed its checks. Closeout receipts exist only since commit `b3c6bec` (2026-08-29, "add deterministic verification foundation").

The commit, push, and PR gates all reach `historical_chain_errors` in `shared/scripts/verify.py`, through `assert_completed_receipt` in `shared/hooks/scripts/_lib-frontmatter.sh`. That function starts at the last completed phase (the terminal phase) and walks back through every earlier phase in the big plan's `phases:` list. Each earlier completed phase must have a valid closeout receipt.

The consumer `industrial-inspection` has a long-running big plan, `2026-07-21_haystack-3-agent-refactor`. Its phases A to F were completed on July 21-22, before receipts existed, so they have none. Its phase G0, `2026-09-04_phase-g0-state-sync-runtime-sync`, has one. Every commit there now fails with `historical phase 2026-07-21_phase-f-eval-benchmark-parity receipt is invalid: ... No such file or directory`.

Planning evidence, 2026-10-23: a read-only run of today's `historical_chain_errors` against that consumer checkout returned exactly that error. A scratch copy with the change below returned no errors and skipped exactly the six July phases.

## Goals

- The historical walk skips an earlier phase only when all of these hold:
  1. its slug starts with a `YYYY-MM-DD_` date before `2026-08-29`;
  2. its small plan is complete, its small plan's `closeout_session_log` names a file whose name starts with a `YYYY-MM-DD` date before `2026-08-29`, and no closeout receipt file is on disk at its path;
  3. every phase listed before it also meets (1) and (2), or is cancelled.
  In short, only the leading run of the `phases:` list can be skipped.
- Every other case fails exactly as today: a receipt file that is on disk but malformed or tampered with, an undated slug, a phase dated on or after 2026-08-29, and a dated phase listed after any phase that has a receipt.
- Documentation, policies, and `.claude/MEMORY.md` describe the exception.

## Non-Goals and Constraints

- User decision, 2026-10-23, after the devil's-advocate review: condition (2) also checks the closeout log's date. Slug dates are planning dates, and many plans give every phase the plan's start date, so without it a phase planned before the cutoff but finished later could be marked complete without a closeout and still be skipped.
- User decision, 2026-10-23: this narrowly reverses the rule from commit `8ed2c9e` (2026-09-02) that "a phase predating receipts gets no implicit pass". It stays narrow because only an early, pre-cutoff, receipt-less prefix of the list is skipped. Deleting a receipt cannot exempt a phase dated on or after 2026-08-29, or a phase listed after one that has a receipt. `tests/test_verify.py::test_historical_chain_rejects_missing_receipt_file` uses undated slugs and keeps failing closed, with its input and assertion unchanged.
- Rejected: a big-plan frontmatter field that names where the chain starts; using the `fixup!`/`squash!` commit bypass.
- Code changes only `shared/scripts/verify.py`, with the standard library only, plus one corrected comment in `shared/hooks/scripts/_lib-frontmatter.sh` (no logic change). It stays the single source that `scripts/generate_targets.py` copies to `dist/` and the self-install copies to `.claude/scripts/verify.py`; check `VFY-GEN-001` compares them. Never hand-edit a copy.
- No edits under `openwiki/`. It is derived context, refreshed only through OpenWiki's own tools. The stale-claims audit records each wiki statement this change makes stale, for the next knowledge-refresh phase.
- Refreshing the consumer is the user's own follow-up after merge.
- Control-plane/high-risk work: every coding step applies `.claude/skills/ponytail/SKILL.md` in `full` mode. Review uses `code`, `architecture`, `security`, `tests`, `ponytail`, and `documentation`.

## Design Overview

One module constant and one helper in `shared/scripts/verify.py`:

- `RECEIPT_CHAIN_SINCE = "2026-08-29"`, with a comment naming commit `b3c6bec`. It follows the slug-date precedent `VERIFICATION_CONTRACT_SINCE` in `scripts/validate_plan_frontmatter.py`.
- `leading_pre_receipt_count(root: Path, phases: list[str], parent_plan: str) -> int` counts how many phases at the start of the list are either cancelled (`is_cancelled_small_plan`) or meet conditions (1) and (2), including the closeout log's date. It stops at the first phase that does not. It tests for the receipt with `os.path.lexists`, so any directory entry at the path, even a broken symlink, counts as a receipt and goes through today's validation.
- `historical_chain_errors` runs that count over the phases before the terminal phase, then walks back only over the phases after the counted run. Nothing else in the walk changes, and no error message changes.

### Decisive assumptions and evidence

| Assumption | Evidence | Remaining limit |
| --- | --- | --- |
| No closeout receipt could exist before 2026-08-29 | `git show -s b3c6bec`: 2026-08-29, "feat: add deterministic verification foundation" | A phase dated 2026-08-29 itself is always checked (strict cutoff, user choice) |
| Slug dates tell when a phase was planned | Slug convention `YYYY-MM-DD_phase-X-slug` (`plan-decomposition` skill); `validate_plan_frontmatter.py` trusts slug dates the same way | A new plan would have to back-date both its first slugs and their closeout log names, then delete their receipts, to be skipped. The gates guard against agent mistakes, not a hostile editor; the deletion stays visible in nested Git history |
| A symlinked reports folder cannot fake a missing receipt | `gate_receipt_errors` loads the terminal receipt from the same folder through `confined_path`, which refuses symlinked parents (`test_gate_rejects_symlinked_closeout_receipt`) | None |
| The change unblocks the consumer's walk | Read-only planning run on the consumer checkout, 2026-10-23: today's code returns the reported phase F error; the patched copy returns `[]` and counts 6 | The consumer must still refresh its runtime and regenerate its G0 receipts (README "Upgrading a consumer with active work"); this plan does not cover the other gate checks there. The devil's-advocate probe found G0's closeout log edited after its receipt (`closeout receipt artifact closeout_log was tampered with`), so the consumer must re-run `verify.py closeout --persist` for G0 after the refresh |

### Contracts touched

| Contract (source) | Behavior to keep | Planned change | Evidence |
| --- | --- | --- | --- |
| `historical_chain_errors`, `shared/scripts/verify.py:1784-1925` | Every check and message for each walked phase; undated slugs never skipped | Skip the leading pre-receipt run; docstring paragraph | Existing `test_historical_chain_*` tests, unchanged |
| `gate_receipt_errors`, `verify.py:2044-2220` | Calls the walk once the terminal receipt head is known | None | `test_gate_receipt_errors_wires_in_historical_chain_validation` |
| `is_complete_small_plan`, `is_cancelled_small_plan`, `receipt_path` | Reused unchanged | None | Existing tests |
| `assert_completed_receipt` and `assert_push_invariants`, `_lib-frontmatter.sh` | Unchanged | None | `scripts/validate_targets.py` hook scenarios (undated slugs) |

### Test strategy

- Real Git in `tmp_path` repositories, built with the existing fixtures `_init_repo`, `_commit_all`, `_write_big_plan`, and `_write_historical_phase`. No mocks.
- Expected values come from the fixture: the slugs it lists, the files it deletes or corrupts, and the commits it makes. Never from `verify.py` output.
- Tests are written first. Each new test that expects a pass must fail against today's `verify.py` with `receipt is invalid` (MEMORY: confirm a new test fails against the old code for the intended reason). Each guard test that expects a failure already passes today and says so in its docstring.
- One test runs the public `gate_receipt_errors` on the consumer's exact shape, with a paired control that proves the fixture reaches the walk.

## Phases

- [ ] `2026-10-23_phase-A-pre-receipt-phase-exemption` — skip only the leading run of pre-receipt phases; tests, docs, and the stale-claims audit.

## Verification

```bash
uv run python scripts/validate_plan_frontmatter.py .claude/plans/pre-receipt-phase-exemption.md .claude/plans/2026-10-23_phase-A-pre-receipt-phase-exemption.md
```

## Completion Evidence

The only phase, `2026-10-23_phase-A-pre-receipt-phase-exemption`, is also the last one. It runs the documentation, memory, and LEARN audit across all live-advice surfaces and records each audited surface and its outcome under `## Stale-claims surfaces checked` in its closeout session log. A one-phase plan gets no knowledge-refresh phase; the audit lists the stale OpenWiki statements for the next one. The phase has its own verification, review, findings, session log, commit, and normal push evidence.
