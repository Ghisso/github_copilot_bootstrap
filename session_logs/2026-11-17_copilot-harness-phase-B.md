# Session: Copilot harness migration, Phase B (tool inputs in the file guard)

**Date:** 2026-11-17
**Plan:** `.claude/plans/2026-11-17_phase-B-copilot-tool-inputs.md`
**Status:** COMPLETED

## Goal

Fix the four kinds of Copilot-harness tool input that the file guard
(`shared/hooks/scripts/protect-files.py`) misreads: patch text (the urgent
one: file edits fail in the real VS Code whenever the chosen model uses the
patch tool), the shell helper tools, the read tool's PascalCase name, and
the search tools' `paths` list. Give every runtime tool a recorded handling.

## Work Log

- **19:50** - Phase A committed as `d34779a` and pushed; the commit hook
  activated Phase B. No re-planning needed: Phase A changed nothing that
  later phases rely on, except that the probe's temporary project removes
  the MCP server file, its mirror copy, and its manifest line (Phase A
  Scope-change record).
- **19:55** - Phase B delegated to a fresh `coder` with the evidence packet
  (the small plan, the big plan's decision-change table, the evidence
  folder's raw files, and the Phase A probe structure).
- **20:35** - `coder` finished steps 1 to 10. The patch-text crash is fixed
  on the real runtime (`1.0.108-0`): a plain `apply_patch` file succeeds, a
  `.env` patch is denied, and hook, server, agent, and indented-header
  patches raise the hook questions. Step 6 found two tools for row T4:
  `run_dynamic_workflow` and `dynamic_workflows_manage` are denied by name
  on `github-copilot` only, because offline they answer "extensions are not
  configured" and no run could show their code passing through a hook. The
  user was told and can lift or narrow the deny.
- **20:40** - Scope-change record added to the small plan (the shell
  heredoc expectation, the two T4 tools, the probe steps step 6 calls for,
  `print_decision` with the two patch constants, and the updated probe
  counts in the docs). Evidence saved under
  `.claude/explorations/2026-11-17_copilot-harness-migration-evidence/raw/phase-B-*`.
- **20:50** - Review round 1 (`code`, `architecture`, `security`, `tests`,
  `ponytail`, `documentation`): no finding on the guard, the probe, or the
  batteries. Gate FAIL on documentation: one MAJOR (row L3 in
  `docs/target-mapping.md` claimed that patch text gets the same decision as
  the same patch inside a shell command) and two MINOR (the known false ask
  for a hunk context line that spells a header was neither documented nor
  pinned; the `sql` row made a universal claim from five tried statements).
  Two open requests: the step 9 table in this log, and the two run times
  saved as evidence.
- **21:05** - All three fixed; one test added
  (`test_a_hunk_context_line_that_spells_a_header_is_judged_as_that_target`).
  Review round 2: Gate PASS, no finding, no open request.
- **21:25** - First closeout run stopped at step 4: `verify.py phase
  --persist` gave `VFY-PYTEST-001: UNVERIFIED`, because the full suite
  (5,560 tests) ran past the verifier's 480-second budget for one command.
  No test failed. Approved as a scope change: the `coder` set
  `COMMAND_TIMEOUT_SECONDS = 900` and `VERIFICATION_ITEM_TIMEOUT_SECONDS =
  1020` in `shared/scripts/verify.py` and corrected the three statements of
  the old item budget (`shared/policies/workflow.instructions.md`, two
  places in `docs/runtime-checks.md`). One timed full run: 5,560 passed,
  1 skipped, 409.74 s by pytest, 436.43 s wall time. The generated OpenWiki
  page `openwiki/operations/deterministic-verification.md` still states 480
  and 600; the final phase of this plan refreshes it.
- **21:45** - Review round 3 on the budget addition (the same six
  profiles): Gate PASS, no finding, no open request. The reviewer confirmed
  from the source that both constants are used only as `timeout=` values,
  that a timeout still ends as UNVERIFIED or TIMEOUT and never as PASS, and
  that no hook or CI file runs `verify.py phase` or `verify.py closeout`
  under a shorter limit.

### Phase-boundary summary

- **Objective and change:** the file guard reads patch text, the shell
  helper tools, the read tool's PascalCase name, and the search tools'
  `paths` list. Changed: `shared/hooks/scripts/protect-files.py`,
  `scripts/check_copilot_runtime.py`, `scripts/copilot_runtime_probe.mjs`,
  `tests/test_check_copilot_runtime.py`, `docs/target-mapping.md`,
  `docs/runtime-checks.md`; new: `tests/test_protect_files_copilot_harness.py`.
  Added at closeout: the verifier's time budgets in
  `shared/scripts/verify.py` and the item budget stated in
  `shared/policies/workflow.instructions.md`.
- **Deviations:** the Scope-change record before step 11 of the small plan.
- **Checks:** the required items below; the probe printed 31 PASS lines on
  runtime `1.0.108-0`; the differential battery section below; the negative
  control (`raw/phase-B-probe-negative-control.txt`: 11 of 31 lines fail
  with the earlier guard).
- **Open findings:** none.
- **Decision for the user (not blocking):** keep, narrow, or lift the deny
  of the two workflow tools on `github-copilot`.
- **Next operation:** Phase C,
  `.claude/plans/2026-11-17_phase-C-copilot-hook-answers.md` (the documented
  answer format for the Copilot client).

## Differential battery (plan step 9)

The guard from `dev` (`2e8c7bb`) against the working copy: 1,158 payloads on
4 clients, 4,632 runs for each guard. Compared: the parsed
`permissionDecision` and the exit code. 314 runs differ, and every one
belongs to a row of the big plan's decision-change table; 0 are
unexplained. For the 4,318 identical runs the output bytes are identical
too. Under Python 3.9.0 the new guard gave the same result as the default
`python3` in all 4,632 runs.

| Decision-change row | Differences | What they are |
| --- | --- | --- |
| L1 | 16 | `Read` on a hook or agent file: ask (Copilot, Claude) or deny (Codex, Antigravity) became no decision. The `.env` rows are identical. |
| L2 | 20 | `read_bash`, `list_bash`, `stop_bash` with no `command`: a stop (exit 2) became no decision, or a deny for a path key that names `.env`. |
| L3 | 148 | Patch text: a stop became the decision of its targets. |
| T1 | 48 | `grep`, `rg`, `glob` with a secret-shaped `paths` entry: no decision became deny. |
| T1 (the key `paths` is global) | 12 | Tools that are not search tools but carry a `paths` list are now judged by path. |
| T2 | 64 | Patch headers with leading blanks, inner blanks, or another letter case, and hunk context lines that spell a header. |
| T4 | 6 | `run_dynamic_workflow` and `dynamic_workflows_manage`, on `github-copilot` only. |

The full table of all 314 rows, with notes on each class, is
`.claude/explorations/2026-11-17_copilot-harness-migration-evidence/raw/phase-B-differential.md`.

## Stale-claims surfaces checked

This phase changed documented guard behavior (rows L1, L2, L3, T1, T2, T4).
Surfaces checked for claims it made wrong:

- `docs/target-mapping.md`: updated in this phase (the GitHub Copilot cells
  of the hook-config and agent-definition rows, the secret-read follow-up,
  and the new tool table).
- `docs/runtime-checks.md`: updated in this phase (forms the guard does not
  check; the probe section).
- `README.md` and `docs/architecture.md`: searched for read tools, search
  tools, the shell helper tools, and `apply_patch`; no statement found, so
  nothing to correct. Their general Copilot statements describe the Local
  harness and are rewritten in Phase F of this plan.
- `docs/smoke-tests.md:220`: it says Copilot's read-only tools (it names
  `view`, `grep`, `rg`, `glob` for the Copilot SDK harness) read protected
  hook and server configs without a prompt and that secret-shaped files
  stay denied for read tools. Still true; after this phase it also holds
  for the search tools' `paths` list and for the name `Read`. Not changed.
- `.claude/MEMORY.md`: the 2026-11-17 Copilot harness entry said
  `apply_patch` crashes `protect-files.py`; corrected in place to say the
  crash lasted until this phase and that the real VS Code also gave the
  patch tool to `gpt-6-luna`. The entry on VS Code's Local harness tool
  names stays true for the Local harness.
- `openwiki/`: not searched; it is refreshed through OpenWiki's tools in
  the final phase of this plan.

## [LEARN] Entries

- [LEARN:tooling] The file guard denies an Edit or Write whose text holds a
  patch start marker with no end marker; define the markers as constants or
  split the string. Recorded in `.claude/MEMORY.md`.
- [LEARN:testing] In a differential battery, read each "unexplained" row
  before touching the guard; the classifier can be the wrong part. Recorded
  in `.claude/MEMORY.md`.
- [LEARN:tooling] The full suite ran past the verifier's 480-second budget
  at closeout; raise `COMMAND_TIMEOUT_SECONDS` when the suite passes about
  two thirds of it, because a late raise costs one more review round and a
  second closeout. The existing entry in `.claude/MEMORY.md` is updated in
  place.
- No lesson recorded for: the hook names of the runtime tools and the
  handling of each tool (the table in `docs/target-mapping.md` carries
  them), and a long pytest run piped into `tail` keeping the call open
  (general shell knowledge).

## Verification

```text
PASS        0.2s  uv run python scripts/generate_targets.py --all
PASS      133.6s  uv run pytest tests/test_protect_files_copilot_harness.py tests/test_hook_gates.py tests/test_protect_files_scoping.py tests/test_protect_files_substitutions.py tests/test_check_copilot_runtime.py -q --tb=short
PASS       11.9s  uv run python scripts/check_copilot_runtime.py --require
PASS        0.0s  python3 -c 'import ast, sys; ast.parse(open(sys.argv[1], encoding="utf-8").read(), feature_version=(3, 9))' shared/hooks/scripts/protect-files.py
PASS        0.0s  grep -q -F 'Copilot harness tools and guard handling' docs/target-mapping.md
PASS       44.7s  uv run python scripts/validate_targets.py
PASS        0.7s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS      415.7s  uv run python .claude/scripts/verify.py phase --format text
closeout: PASS
```

- Phase receipt: `verify.py phase --persist` PASS (Ruff, mypy, pytest with 5560 passed and 1 skipped in 410.13 s, freshness, provenance, generation). The first run of this step ended UNVERIFIED on the 480-second budget; this is the second run, after the budget change and review round 3.

- Findings: `.claude/quality_reports/findings-2026-11-17_phase-B-copilot-tool-inputs.json`
  (no surviving finding; gate PASS; six profiles; round 1 FAIL with one
  MAJOR and two MINOR in the documentation, all fixed before round 2;
  round 3 on the time-budget addition PASS with no finding).
- optional 1: PASS — the section "Differential battery (plan step 9)" above holds the class table (314 differences, 0 unexplained) and points to the full 314-row table in `raw/phase-B-differential.md`; every row belongs to L1, L2, L3, T1, T2, or T4.
- optional 2: NOT RUN — it needs a person in a signed-in VS Code window with this phase's guard installed in a test project; the offline probe session `codex-patch` shows the same patch input creating a plain file on runtime `1.0.108-0`, and the user is asked to repeat the check in VS Code.

## Open Questions / Next Steps

- Next: Phase C, the documented answer format for the Copilot client.
- For the user: keep, narrow, or lift the deny of `run_dynamic_workflow` and
  `dynamic_workflows_manage` on `github-copilot`.
- For the user: one prompt in a Copilot-harness chat that asks for a new
  plain file, to confirm the patch-tool fix in the real client.
