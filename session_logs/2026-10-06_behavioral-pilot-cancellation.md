# Behavioral pilot: cancellation of downstream experiments

**Status:** CANCELLED
**Parent plan:** .claude/plans/behavioral-evaluation-pilot.md
**Cancelled phases:** 2026-10-03_phase-B-behavioral-pilot-runner and 2026-10-03_phase-C-behavioral-pilot-comparison

The approved big plan requires cancelling Phases B and C when Phase A cannot
show reviewer loading or case sensitivity. The five approved native sessions
were run by the user. One repaired-packet role probe produced a report
consistent with reviewer loading, but no client-selected-agent field. Each
of the four scheduled case runs returned `nonzero_client_exit`, with no
saved final output. BEP-002 (case sensitivity) therefore remains unproven.

Evidence is in `docs/evidence/behavioral-pilot/phase-a/`: five run records,
the frozen manifest, and judgments. Unavailable runs are neither failures
of the review task nor successful negative controls. The retained metadata
does not identify their root cause. The budget is consumed and no rerun is
authorized by this plan. There is no before/after comparison or detection
rate to report.

Phase A closes with this stop decision. Phase D remains planned and will
record the stopped pilot, audit live advice, close the existing follow-ups,
and refresh OpenWiki. No requirement is silently treated as satisfied:
BEP-003 through BEP-005 are not implemented or evaluated.
