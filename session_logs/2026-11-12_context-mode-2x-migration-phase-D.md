# Session: Answer the MCP 2026-07-28 discovery probe (migration Phase D, reopen)

**Date:** 2026-11-12
**Plan:** `.claude/plans/2026-11-12_phase-D-context-mode-discover-fallback.md`
**Status:** IN-PROGRESS

## Goal

The filter answers `server/discover` itself with `-32601` and never forwards it, before or after an accepted `initialize`, so a client that speaks both MCP revisions falls back to `initialize` and gets the three tools, and no upstream `instructions` reach it through the probe (REQ-007, Finding 1). Plus the separable Finding 3 unit (three overstated comments and one README sentence), which the user chose to keep.

## Work Log

- Reopen: after the three phases completed (`7895856`, pushed), live client checks found one Claude Code session with no Context Mode tools. The user said "fix problem 1". Quality report `.claude/quality_reports/2026-11-12_context-mode-2x-live-check-findings.md` recorded the findings. A planner drafted Phases D and E; its probe of the real 2.1.8 showed the cause is the forwarded `server/discover` probe, not a pipelined `tools/list` (my first explanation, wrong because my probe lacked the 2026-07-28 `_meta`).
- The user asked to see the plan first and for a review prompt. Two independent reviews ran: GPT-6 Sol (the user's, verdict BLOCK pending two MAJORs: the notification test could not see an extra reply; Phase E's line-count rule protected positions, not meaning) and an Opus devil's-advocate subagent at max effort (verdict approve with changes: the verdict-cache risk was backwards, the live check could not confirm the fix, plus wording, evidence, scope, and process items). Both reproduced the failure and the `-32601` fix against the real 2.1.8. The planner applied all 12 changes (`reopen-v2`); the user kept the separable Finding 3 unit and said "go until the end of the big plan".
- Applied: Phases D and E saved, big plan edited (status `in-progress`, `current_phase` Phase D, Reopened note, REQ-007, follow-ups), `validate_plan_frontmatter.py` exit 0; evidence copied into the live-check exploration (`era_probe.py`, `era_probe-output.txt`, `shim.sh`, `pipeline_probe.py`, `discover_probe.py`); Phase D set `in-progress` by hand (reopen step 7); nested checkpoint `d7bd246` (reopen step 8).
- Step 1: dated Correction sections appended to the live-check `REPORT.md` and the quality report (original text kept). The wrong `[LEARN:tooling]` entry about a pipelined `tools/list` in `.claude/MEMORY.md` was corrected in place to the `server/discover` lesson.

- Coder (Steps 2-4, Step 5 comments) and documenter (Step 5 README sentence, Step 6) ran in parallel. Negative control on today's filter (`-k "discover or refused_until"`): 3 failed, 2 passed, exactly as the plan predicted (test 1: the probe's answer passed through with `supportedVersions` and `instructions`; test 2: the id-less probe reached the fake and the trace appeared; test 3: failed at its first probe; the parametrized refused-until-initialize test passed with and without `_meta`). Extra mutation by the coder: with the new branch limited to `!serverAccepted`, test 3 failed at the probe after `initialize`. Real-binary test on today's filter: failed (2.1.8 answered the probe with its `instructions`); after the fix: 1 passed.
- Coder results: three test files 350 passed, 1 skipped; filter test file 38 passed, 1 skipped; `validate_targets.py` PASS; `verify.py fast` PASS; ruff and mypy clean. New comments: filter line 13 ("each naming no tool outside the allowlist"), the `server/discover` branch comment, and two dispatcher comments stating that `state-sync.sh` adds and commits only under `.claude/`, the root restore copies only allowlisted adapter files, and this gives no protection against a remote that replaces the synced scripts.
- Documenter: README `server/discover` sentence (plan wording), README secret clause replaced (plus "ever" dropped from "To keep that scenario from ever becoming a trusted cache"), runtime-checks sentence and a new first "Known limits" bullet. It flagged one README clause it left absolute.
- Step 6 orchestrator part: project-context Context Mode bullet now says the filter answers `server/discover` itself with `-32601`.
- Step 7: `generate_targets.py --all`, then `install_bootstrap.py . --allow-self --local-only`.
- Review round 1 (six profiles): gate PASS, no CRITICAL or MAJOR; two MINORs, both fixed rather than disposed. (1) README line 1432 "no cache is ever searched or cited ... unless the dispatcher produced it" contradicted the new limit sentence; now scoped "short of a remote that replaces the synced scripts themselves". (2) `test_discover_probe_is_refused_before_initialize` had no ordering barrier before its trace check; it now sends a `ping` and reads its reply first. Orchestrator mutation check of that barrier: with the filter changed to answer AND forward the probe, the test failed at the ping read (`assert 0 == 2`); the filter was restored byte-identical (SHA-256). Filter test file after the fix: 38 passed, 1 skipped; ruff clean.

## [LEARN] Entries

- (filled at closeout)

## Verification

(filled at closeout)

## Open Questions / Next Steps

- Coder Steps 2-4 and the Step 5 comments; documenter Step 5 README sentence and Step 6; orchestrator Step 6 AI state and Step 7; reviewer Step 8.
