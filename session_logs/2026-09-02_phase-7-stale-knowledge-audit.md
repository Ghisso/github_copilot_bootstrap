# Session: Phase 7 — Stale Knowledge Audit

**Date:** 2026-09-02
**Plan:** `.claude/plans/2026-09-02_phase-7-stale-knowledge-audit.md`
**Status:** COMPLETED

## Goal

Make a documentation, memory, and LEARN audit a required final step of every
big plan, bring the stale-claims rule to cover the memory index, and run that
audit over every live-advice surface. Final phase of
`verification-gate-semantic-hardening`.

## Work Log

- **13:00** - The user asked for the memory gap to become a phase, then
  refined the goal mid-turn: make the audit a standing final step of every big
  plan rather than a one-off cleanup. That reframing became the phase's primary
  objective; the cleanup is the instance.
- **13:10** - Measured the surface first. `.claude/MEMORY.md` is 689 lines,
  loaded every session, and named `quality_score.py`, deleted in Phase 1. 74
  session logs hold 164 LEARN entries, with 12 bound by a closeout receipt and
  therefore immutable.
- **15:00** - Round 1: standing requirement stated in five places, §3.7
  extended to the memory index, five MEMORY.md corrections, one errata.
- **16:30** - Review round 1: **FAIL**, 1 CRITICAL + 2 MAJOR + 2 MINOR.
- **17:00** - I tested the reviewer's proposed fix for the CRITICAL and it did
  not work, which turned a documentation slip into a structural finding. See
  below.
- **18:30** - Round 2: all five fixed, including the structural installer
  change and the gate the earlier reasoning had wrongly ruled out.

## Design decisions

- **The standing requirement is enforced, not merely documented.** Round 1
  declined a gate, reasoning from Phase 6's `CHECK_IDS` lesson that any
  evidence requirement would invalidate prior receipts. That was a false
  analogy, and review caught it. `closeout_log_errors` has exactly one caller
  and `historical_chain_errors` never invokes it, so extending it touches no
  schema field and can never be re-evaluated against phases 1–6's closed logs.
  The plan's own bar was "keep it documented if a gate cannot be met cleanly";
  it could be met cleanly, so it was. A final phase now must carry a non-empty
  `## Stale-claims surfaces checked` section, with `is_final_phase` deriving
  finality from the big plan's own `phases` list and failing closed to
  not-final on any malformed frontmatter.
- **The gate checks shape, not judgement.** Whether an audit was done well is
  not deterministically checkable, so the requirement is that the surfaces be
  recorded — the same shape as the existing LEARN evidence, per §3.3.
- **Live advice is corrected; a dated record is left alone.** Archived plans,
  dated design narratives, and session logs record what was true then. Only
  one LEARN entry across 164 met the bar for an erratum.
- **The installed `.claude/` overlay is a live-advice surface.** Round 1
  audited the canonical `shared/` sources and missed the copies actually read
  at runtime here. That omission is what hid the CRITICAL.

## The CRITICAL: bootstrap documentation seeded into preserved directories can never be updated

`.claude/session_logs/README.md` still required `## Score: N/100` and
`.claude/quality_reports/README.md` still templated `**Score:** [N]/100` and a
`Gate: Excellence` label, months after Phases 1 and 3 fixed their `shared/`
sources.

The review proposed resyncing with `install_bootstrap.py --allow-self
--local-only`. I tested it: `Score` was still present afterward. The cause is
structural. Those READMEs live inside directories the installer preserves as
consumer state, and the tree walk skips such a directory by name before ever
looking inside it. So a canonical fix could never reach an existing install —
every consumer who installed before Phase 1 still had score-era README text
and always would, no matter how often they refreshed.

The fix separates ownership from location: a state directory's `README.md` is
bootstrap-owned documentation that merely sits beside consumer-owned content.
`STATE_DIR_OWNED_README_PATHS` names the four exact paths, kept separate from
`CONSUMER_STATE_PATHS` so every existing preservation invariant is untouched,
and the installer refreshes exactly those after its generic copy. An explicit
allowlisted refresh was chosen over reworking the generic walk, because that
walk is pinned by several existing tests and selectively descending into a
preserved directory risked new edge cases.

Verified end to end rather than by inspection: I deliberately wrote a stale
marker into `.claude/session_logs/README.md`, ran the installer, and it
reported `refresh bootstrap-owned state directory README` for all four paths
and restored clean content, while the sibling errata file in the same
directory was preserved. A regression test pins both halves — README refreshed,
sibling state file byte-for-byte preserved.

The accepted risk is a consumer who hand-edited a state README losing that
edit. These are boilerplate reference documents about directory conventions,
unlike `MEMORY.md`, so the exposure is small and the alternative was permanent
staleness for every consumer.

## Stale-claims surfaces checked

| Surface | Outcome |
|---|---|
| `.claude/MEMORY.md` | Corrected — 5 stale claims fixed, plus a score-era phrasing reworded |
| `.claude/` installed overlay | Corrected — 4 state-directory READMEs were stale copies of already-fixed `shared/` sources; fixed here and structurally for every consumer. Full `dist/` versus `.claude/` diff swept for further drift: none beyond these, expected consumer state, and two intentional project-name substitutions |
| `CLAUDE.md`, `AGENTS.md`, `README.md` | Checked — clean |
| `docs/*.md` (non-dated) | Checked — clean |
| `docs/plan-deterministic-commit-gate.md`, date-prefixed `docs/*.md` | Left unchanged — dated record |
| `shared/policies/*.instructions.md` | Corrected — `workflow.instructions.md`; rest clean |
| `shared/skills/*/SKILL.md` | Corrected — `plan-decomposition/SKILL.md`; rest clean |
| `shared/templates/*.md` | Corrected — `plan-big.md`; rest clean |
| `shared/agents/*/prompt.md` | Corrected — `orchestrator`, `documenter`; `coder`, `reviewer`, `planner` clean |
| `shared/review-profiles/*.md` | Checked — clean |
| `shared/` state READMEs | Checked — already correct; the installed copies were the drifted layer |
| Named files, modules, and flags across all of the above | Verified against disk; no missing referent |
| 74 session logs / 164 LEARN entries | 12 receipt-bound, sha256-confirmed unmodified before and after; 1 errata written |

## [LEARN] Entries

- [LEARN:installer] Bootstrap-owned documentation seeded inside a preserved
  consumer-state directory can never be updated again, because the installer
  skips such a directory by name before looking inside. Separate ownership
  from location: name the owned paths explicitly and refresh them, keeping the
  preservation list untouched. Test it by corrupting the file and confirming a
  refresh restores it while a sibling state file survives.
- [LEARN:review] Auditing a canonical source is not auditing what runs. The
  `shared/` state READMEs were correct for months while the installed copies
  that agents actually read still demanded a deleted score. Include the
  installed overlay in any documentation audit of this repository.
- [LEARN:review] A plausible analogy to a real lesson is a good way to talk
  yourself out of the right fix. Phase 6's `CHECK_IDS` lesson genuinely
  forbids extending the receipt's check set, and it was cited to decline an
  evidence gate that lives in a different, historically-isolated mechanism.
  Verify the analogy applies before accepting it as a constraint — one grep
  for the caller settled it.
- [LEARN:verification] `closeout_log_errors` is the schema-free extension
  point for closeout-log evidence. It has one caller and
  `historical_chain_errors` never invokes it, so a requirement added there
  cannot retroactively invalidate a closed phase, unlike anything touching
  `CHECK_IDS` or the receipt's artifact set.
- [LEARN:workflow] A gate that a phase adds must be satisfied by that phase's
  own closeout. This log carries the `## Stale-claims surfaces checked`
  section the phase introduced; writing the gate without writing the section
  would have blocked its own commit.

## Verification Results

```bash
uv run pytest tests/ -q --tb=short
# 1242 passed (1135 on dev at the start of this plan; +107 across seven phases)

uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
# Success: no issues found in 25 source files

uv run ruff check shared scripts tests
# All checks passed!

uv run ruff format --check shared scripts tests
# 25 files already formatted

uv run python scripts/validate_targets.py
# PASS generated target is structurally valid

uv run python scripts/validate_plan_frontmatter.py
# (clean)

uv run python .claude/scripts/verify.py phase --format text
# phase: PASS
```

All 12 receipt-bound session logs still hash-match their receipts. The
historical receipt chain across all seven phases returns `[]`.
`is_final_phase` reports phase 6 false and phase 7 true.

## Open Questions / Next Steps

- A consumer who hand-edited a state-directory README will have it refreshed
  on their next install. Accepted, and recorded above with its reasoning.
- `.claude/skills/antigravity-native-acceptance-isolation` is an empty
  directory with no files and so no stale content; noted and left alone.
- No compatibility allowance exists in this plan, so none carries a removal
  condition.
- The user owns the merge decision; no PR was opened.
