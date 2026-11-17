# Session: Copilot harness migration, Phase F (documentation, manual checklist, sidecar check)

**Date:** 2026-11-18
**Plan:** `.claude/plans/2026-11-17_phase-F-copilot-docs.md`
**Status:** IN-PROGRESS

## Goal

Rewrite the Copilot statements in `README.md` and the docs so they match
what Phases A to E built and what was run, each with the runtime version it
was seen on. Add a short manual checklist for a signed-in VS Code window.
Record a check of the personal sidecar overlay on the Copilot harness. No
code change.

## Work Log

- **05:37** - Phase E committed as `5a77d4b` and pushed; the commit hook
  activated Phase F. The user's test folder
  `~/copilot-harness-probe-20261117` was refreshed with the Phase E hooks.
- **05:40** - Re-planning check against the outcome of Phases B to E.
  Points for the `coder`, all inside this phase's stated intent:
  - The plan's checklist item "the approval questions for a protected
    edit (two under option B)" follows the Phase D correction: the runtime
    raises two hook questions, and in the one real VS Code run VS Code
    answered the second itself. The item asks how many dialogs appear.
  - The manual checklist takes in the checks that Phases B to E left for
    a signed-in window (the patch tool, the Local-harness deny with the
    new answer, one session-log entry per chat, the sub-agent guidance,
    the session-start reminder).
  - The docs written in Phases B to E cite the evidence report by bare
    labels such as "A6" or "F13". The report is in the private AI state,
    not in the repository. Each label gets a plain description of what was
    seen and when.
  - Not added to the public docs in this phase: the follow-up on inline
    Python without `-I` in the older hooks. The user was told on
    2026-11-18 and decides how to handle it.
- **05:41** - Phase F delegated to a fresh `coder` in the documenter role.
- **06:22** - `coder` finished steps 1 and 2. Six files changed, docs
  only. Sidecar check on runtime `1.0.108-0`: the `skills` profile shows 2
  instruction sources, 4 skills, 0 agents; the `workflow` profile shows 4
  instruction sources, 22 skills, and the five sidecar agent files as
  Copilot agents. The docs had said Copilot gets no sidecar agents;
  corrected to what the discovery showed. A claims table with 238 rows
  gives the basis of each Copilot claim. The plan's Verification lines
  pass. The full suite had 1 failure and 1 error.
- **06:25** - Cause of that failure found by the orchestrator, and it is
  an old defect, not this phase. `protect-files.sh` makes a file with
  `mktemp` on every call and removes it only when the classifier fails, so
  each guard call leaves one empty `/tmp/tmp.XXXXXXXXXX` file
  (`openwiki-guard.sh` removes its file on both paths). `/tmp` held
  142,664 of them, all empty and all from 2026-11-17 and 2026-11-18. The
  classifier expands a glob with `glob.glob`, so the test
  `test_protect_files_checks_original_cwd_when_cd_is_not_provable[cd /tmp
  | mv * /tmp/out]` ran past the 4-second limit (exit 142). The error in
  `tests/test_verify.py` came from the same run: the fail-closed line went
  into the live `hooks-errors.log`, which a test guard reports. Cleanup:
  140,397 empty files of that name pattern, owned by the user and older
  than 30 minutes, were deleted; `/tmp` has 2,416 entries. The same test
  then passed in 0.20 s (2.75 s before). The fix of the leak is not part
  of this docs-only phase; it is recorded as an open follow-up with the
  `-I` item, and the user is told.
- **06:27** - Orchestrator checks: `verify.py fast` PASS. Scope-change
  record added to the small plan. Review round 1 started with six
  profiles.
- **06:40** - Review round 1: Gate PASS, no CRITICAL or MAJOR finding, 15
  MINOR. The reviewer opened about 75 rows of the claims table against
  their basis and found the counts, the real-window statements, the
  deny-and-question wording, and the sidecar section sound. Disposition:
  all 15 are fixed. The ones that matter most: the checklist did not say
  that it must run in a folder with no work to keep (item 10 is a deny
  that was never run); item 4 could pass without the patch tool; item 9
  told the reader to look for a denial in a log that does not record
  denials; `docs/architecture.md` said only the Local harness needs
  `.github/copilot-instructions.md`, which the sub-agent hook also reads;
  the February 2027 date named no source. Sent to the `coder`. For the
  final phase the reviewer listed: `openwiki/architecture/hooks-and-guardrails.md`
  is stale, and source comments in `subagent-context.sh`, `run-hook.sh`,
  and some test docstrings cite the private evidence report by bare
  labels.
- **07:01** - Fix round 1 done: all 15 points. The checklist opens with a
  safety paragraph, every item starts with one of two marks ("Never run
  anywhere" or "Seen before, not since the changes") and names its
  Session Target and the dialog answer. The long passage in
  `docs/target-mapping.md` that repeated the README is one short paragraph
  with links; its facts moved to the README. Full suite on the final tree
  with a clean `/tmp`: 5,927 passed, 1 skipped, 424 s. Link check: 133
  relative links, 0 broken. Orchestrator checks: `verify.py fast` PASS,
  and the start of the checklist read. Review round 2 started.
- **07:06** - Review round 2: 14 of the 15 fixes hold. Gate FAIL on one
  MAJOR that a fix introduced: the new paragraph in
  `docs/target-mapping.md` was inserted inside the Gate-Repair table, so
  the table's last row no longer renders as a row. The `coder`'s table
  check counted cells only. Eight MINOR, seven in the checklist and the
  wording (item 3 missing from the safety paragraph; two items marked
  "Never run anywhere" although something was seen; no result word for an
  item that only records an observation; "any dialog means FAIL" has no
  basis on the Local harness; "the recovery needed a window reload" says
  more than the record; "reads the nested copy only" says more than the
  source reading) and one in the small plan's Scope-change record, which
  the orchestrator extended. Sent to the `coder`.
- **07:11** - Fix round 2 done. The paragraph follows the table's last
  row; the table check now also fails for a table cut in two (it reported
  the orphan row before the fix, and 26 tables with 0 problems after).
  The checklist has three marks and five result words, defined once. The
  pass rule of the deny items is "the command does not run and the chat
  shows the guard's reason". Orchestrator checks: `verify.py fast` PASS,
  and the two table rows read. Review round 3 started.
- **07:13** - Review round 3: Gate PASS, no open request. The table is one
  block again; the reviewer confirmed both halves of the Local-harness
  sentence in VS Code's `extension.js`. Three MINOR, all fixed: a heading
  still said "the two marks"; item 2 of the checklist could never fail
  when the guard asks nothing (a `FAIL` rule is added); the Scope-change
  record lacked two corrections and had an old finding count (extended
  by the orchestrator). The two doc lines went to the `coder`.
- **07:16** - Review round 4 on those lines: Gate PASS, no open request,
  one MINOR: item 2 said the command "ran after the user approved the
  question", which the record of 2026-11-17 does not state. The
  orchestrator replaced the sentence with the reviewer's own wording (the
  user answered the first question, VS Code approved the second itself,
  and the agent then read the file back). `validate_targets.py` and
  `verify.py fast` pass after it.
- **07:17** - `uv run python scripts/check_copilot_runtime.py --require`
  run by the orchestrator: Copilot SDK version `1.0.30-preview.0`, Copilot
  runtime version `1.0.108-0`, `Result: PASS (0 of 48 checks failed)`.

### Phase-boundary summary

- **Objective and change:** the Copilot statements in the repository's
  documents match what Phases A to E built and what was run. Changed:
  `README.md` (a Quick Install note on the two harnesses, policy
  applicability, Agent System, Hooks), `docs/target-mapping.md` (Native
  Adapters, both parity tables split into Local harness and Copilot
  harness, recorded follow-ups, the tool table), `docs/runtime-checks.md`
  ("VS Code Copilot evidence boundary", the probe section),
  `docs/smoke-tests.md` (a manual checklist of 11 items),
  `docs/architecture.md` (a subsection on the Copilot adapter),
  `docs/sidecar-provider-contract.md` (a discovery check of 2026-11-18).
  No code changed.
- **Deviations:** the Scope-change record under step 2 of the small plan.
- **Checks:** the required items below; a claims table of 265 rows with
  the basis of each Copilot statement, of which the reviewer opened about
  75; link check (133 relative links, 0 broken); table check (26 tables,
  0 problems).
- **Open findings:** none.
- **Unverified limitations:** no item of the manual checklist has a run in
  a signed-in window since these changes; the Local harness was not run
  with the current answer format or hooks; the exact button names in VS
  Code were not checked; the result of the CI workflow's macOS job has not
  been read.
- **Decisions for the user (not blocking):** a separate small plan for the
  two old defects in the guard hooks (inline Python without `-I`; the
  temp-file leak of `protect-files.sh`); whether the sidecar agents that
  the Copilot runtime lists should be described as supported after a
  check in a signed-in window (item 7 of the checklist).
- **Next operation:** Phase G,
  `.claude/plans/2026-11-17_phase-G-knowledge-refresh.md` (the OpenWiki
  refresh and the final audit).

## Stale-claims surfaces checked

This phase rewrote documented Copilot behavior in six files.

- `README.md`, `docs/target-mapping.md`, `docs/runtime-checks.md`,
  `docs/smoke-tests.md`, `docs/architecture.md`,
  `docs/sidecar-provider-contract.md`: updated in this phase. The list of
  32 stale sentences with their old and new text is
  `raw/phase-F-stale-sentences.md` in the evidence folder; the reviewer
  searched the six files for the earlier statements and found none left.
- `docs/native-client-acceptance.md:5-6`: says its script does not cover
  Copilot. Still true. A pointer to `scripts/check_copilot_runtime.py` and
  to the manual checklist would help; left for the final phase's audit.
- Source comments in `shared/hooks/scripts/subagent-context.sh` and
  `shared/hooks/scripts/run-hook.sh`, and some test docstrings: they cite
  the evidence report by bare labels. They are code, outside this
  docs-only phase; listed for the final phase's audit.
- `shared/policies/`, `shared/skills/`, root `CLAUDE.md` and `AGENTS.md`:
  the reviewer named no statement there that this plan made false. The
  final phase runs the full audit.
- `.claude/MEMORY.md`: three lessons of this phase added; the Copilot
  harness entry is corrected in the final phase, as its plan says.
- `openwiki/`: not searched. `openwiki/architecture/hooks-and-guardrails.md`
  is known to be stale (the launcher, `SubagentStart`, the session-start
  reminder, the `Read` alias); the final phase refreshes it through
  OpenWiki's tools.

## [LEARN] Entries

- [LEARN:documentation] A table check that counts cells does not see a
  table cut in two; check that the rows are contiguous. Recorded in
  `.claude/MEMORY.md`.
- [LEARN:documentation] What a manual checklist item needs (a mark for
  earlier evidence, the mode, the dialog answer, a supported pass rule, a
  result word for an observation, a safety note). Recorded in
  `.claude/MEMORY.md`.
- [LEARN:documentation] Docs in the repository must not cite the private
  evidence report by bare labels. Recorded in `.claude/MEMORY.md`.
- [LEARN:hooks] `protect-files.sh` leaks one empty temp file for each
  call, and the classifier's glob on `/tmp` then runs past its limit.
  Recorded in `.claude/MEMORY.md` at 06:25 with the cleanup command.
- No lesson recorded for: the sidecar discovery result (the dated section
  in `docs/sidecar-provider-contract.md` carries it).

## Verification

```text
# filled at closeout step 4
```

- Findings: `.claude/quality_reports/findings-2026-11-17_phase-F-copilot-docs.json`
  (no surviving finding; gate PASS; six profiles; round 1 PASS with 15
  MINOR, round 2 FAIL with one MAJOR and 8 MINOR, round 3 PASS with 3
  MINOR, round 4 PASS with 1 MINOR; all 27 MINOR and the MAJOR fixed).
- optional 1: PASS — the orchestrator ran `uv run python scripts/check_copilot_runtime.py --require` on 2026-11-18 at 07:17; it printed Copilot runtime version `1.0.108-0` and `Result: PASS (0 of 48 checks failed)`, and the docs name that version.
- optional 2: NOT RUN — the user has not yet run the manual checklist in a signed-in VS Code window; every item of the checklist carries a mark that says so, and the user has the list and the test folder `~/copilot-harness-probe-20261117`.

## Open Questions / Next Steps

- Next: Phase G, the OpenWiki refresh and the final audit.
- For the user: run the manual checklist in `docs/smoke-tests.md`
  (section "VS Code Copilot harness (manual)") in the test folder and
  report the results.
- For the user: decide on a separate small plan for the two old defects
  in the guard hooks.
- For the user: the result of the `macos-latest` job of the `Validate`
  workflow.
- For the user: keep, narrow, or lift the deny of the two workflow tools.
