# Session: Language reporting reminder hardening

**Date:** 2026-09-09
**Plan:** .claude/plans/2026-09-08_phase-A-language-reporting-reminder-hardening.md
**Status:** COMPLETED

This log closes the only phase of the big plan
`language-reporting-reminder-hardening`. The phase was paused on 2026-09-08 for
usage reasons; that pause is recorded separately in
`.claude/session_logs/2026-09-08_language-reporting-reminder-hardening.md`,
which stays `PAUSED` as the pause evidence.

## Goal

Keep `shared/policies/agent-reporting.instructions.md` the single detailed
writing authority, and add one short, non-blocking reporting reminder for Claude
Code and OpenAI Codex only: once at prompt start, and once after a small set of
late lifecycle Bash commands.

## Work Log

- Resumed the paused phase: read the PAUSED log, inspected `git log`, `git
  status`, and the diff, reported the recorded resume point, and set the same
  small plan back to `in-progress` while keeping its pause metadata.
- Found that the PAUSED log's remaining-work list was stale. The interrupted
  coder had already fixed both surviving findings from the earlier review, and
  both had tests. Verified this against the working tree instead of re-doing the
  work.
- Re-ran every verification command, because the log correctly marked all
  earlier passes as stale.
- Ran the six-profile review three times. Four findings surfaced and all four
  were fixed; the final round reported PASS with one MINOR finding, which was
  also fixed.
- Corrected an inaccurate documentation and plan claim about outcome gating.
- Fixed a CRITICAL defect that made one whole reminder boundary dead code, and
  rebuilt the test fixture that had hidden it.
- Removed a leftover duplicated git invocation in one test, closing the last
  MINOR finding rather than carrying it.

## Design decisions and rationale

- **The two script boundaries match on command shape only.** The documentation
  and the plan's own step 2 originally claimed the late reminder fires only
  after a *successful* `verify.py closeout` or `record_findings.py --out` run.
  The script never inspected the outcome. No hook script in this repository
  reads a tool-outcome field from a hook payload, and no documented payload
  contract for Claude Code or OpenAI Codex records one, so implementing that
  claim would have meant inventing an unverified cross-runtime field or adding
  file correlation to a hook whose entire effect is one 183-byte advisory
  sentence. The user chose to correct the wording. The plan's step 2 now records
  the decision and its reason, and step 4's test expectation matches.

- **Committed plan state lives in the nested `.claude` repository.** The
  phase-completion-commit boundary read `git -C "$REPO_ROOT" show
  "HEAD:.claude/plans/<plan>.md"`. That can never succeed: `.gitignore` line 5
  excludes `.claude/`, `git ls-tree -r HEAD` matches zero `.claude/` paths, and
  that read exits 128 while the same read against the nested repository exits 0.
  The boundary was therefore dead code, and the earlier "race removed" judgment
  held only because the read never succeeded. The fix reads
  `git -C "$REPO_ROOT/.claude" show "HEAD:plans/$plan.md"`, matching the pattern
  already established at `scripts/validate_targets.py:8212`.

- **Why that fix is not dead code again.** The outer repository's `post-commit`
  git hook runs `state-sync.sh push` during the commit, which commits `.claude`
  state into the nested repository before the Bash tool call returns and
  therefore before `PostToolUse` runs. That path is warn-never-fail, so the
  boundary is best-effort: it never fires wrongly, and it simply does not fire
  if the nested commit did not happen.

- **The fixture must mirror the shipped topology.** The original fixture built
  one flat repository tracking `.claude/plans/*.md` directly. That shape exists
  only in tests, so 1,262 tests passed over an inert feature. The fixture now
  builds an outer repository whose `.gitignore` excludes `.claude/` plus a
  nested repository inside `.claude/`, and its docstring records why.

- **No new skill was created.** The lessons below are traps to recognize, not
  repeatable multi-step procedures, so they belong in `.claude/MEMORY.md`, which
  is read before non-trivial work.

## Review findings and their resolution

All findings are resolved; the persisted report is therefore empty.

| Round | Severity | Finding | Resolution |
|---|---|---|---|
| 1 | MAJOR | Docs and plan claimed outcome gating the script does not implement | Corrected three docs statements and the plan's steps 2 and 4 |
| 2 | CRITICAL | `head_frontmatter_value` read the outer repository, so the phase-completion boundary was dead code | Reads the nested `.claude` repository |
| 2 | MAJOR | Docs claimed that boundary was confirmed against committed state while it was inert | Fixed the defect, then made the sentence name the nested `.claude` repository |
| 2 | MAJOR | Flat single-repository fixture hid the defect | Fixture rebuilt with the nested topology, plus one new negative test |
| 3 | MINOR | One test duplicated the raw git identity invocation that `run_git` replaced | Replaced with `run_git` |

Round one judged the outer-repository read "correct" by reading it. Round two
found the defect by executing the script. That is recorded below as a lesson.

## Verification results

Final state of the tree, all commands re-run after the last edit:

- `uv run python scripts/generate_targets.py --all`: PASS
- `uv run python scripts/validate_targets.py`: PASS, "generated target is
  structurally valid"
- `uv run pytest tests/ -q --tb=short`: PASS, 1263 tests
- `uv run ruff check shared scripts tests`: PASS, 0 violations
- `uv run ruff format --check shared scripts tests`: PASS, 25 files already
  formatted
- `uv run mypy shared scripts tests --ignore-missing-imports
  --explicit-package-bases`: PASS, no issues in 25 source files
- `uv run python scripts/install_bootstrap.py . --allow-self --local-only`:
  PASS, with `AGENTS.md` and `CLAUDE.md` SHA-256 verified unchanged
- `uv run python scripts/check_runtime.py`: PASS, generated runtime wiring is
  present
- `uv run python .claude/scripts/verify.py phase --format json --persist`: PASS

Behavior proved by executing the real script against a fixture with the shipped
nested topology, run by the orchestrator independently of the coder:

- committed `status: complete` plus a phase-completion commit command: exactly
  one `PostToolUse` context object, exit 0
- working tree rewritten to `status: in-progress` while the nested repository's
  HEAD still said `complete`: still exactly one object, which proves the read is
  bound to committed state and not the mutable working tree
- nested HEAD advanced to `status: in-progress`: no output, exit 0
- `git -C /tmp commit -m "feat: elsewhere"`: no output, exit 0
- `ls -la`: no output, exit 0
- malformed input: `WARN reporting-reminder: malformed hook input` on stderr
  only, exit 0
- provider `gemini-cli`: `WARN reporting-reminder: unsupported provider:
  gemini-cli` on stderr only, exit 0
- prompt mode for `openai-codex`: exactly one `UserPromptSubmit` object, exit 0

Reminder size: the reminder text measures exactly 183 bytes, under the
validator's 200-byte ceiling. Injections in a bounded workflow: one at each
prompt start, plus at most one per recognized late boundary. No token saving or
writing-quality improvement is claimed from these structural checks.

## Native client acceptance: UNVERIFIED as of 2026-09-08

Probes of authenticated Claude Code and OpenAI Codex clients both returned
`unavailable_untrusted`, so native prompt-start and late-report injection are
recorded as dated UNVERIFIED. No synthetic pass replaces them. The structural
and execution evidence above does not substitute for native acceptance.

## Stale-claims surfaces checked

- `CLAUDE.md`: current. It points to the reporting policy without copying its
  detail, so the new `## Violations to recognize` section creates no second
  authority. No change.
- `AGENTS.md`: current, for the same reason. Byte-for-byte unchanged through
  self-install, verified by SHA-256.
- `README.md`: updated in this phase. Its hook inventory now lists
  `reporting-reminder.sh` with the Claude Code and Codex scope and the note that
  the static policy still applies to all four supported targets.
- `docs/architecture.md`: updated. New `### Reporting reminders` section, and
  the policy paragraph now separates static guidance for all four targets from
  recurring reminders for two.
- `docs/runtime-checks.md`: updated, including the guardrail script list, which
  `scripts/validate_targets.py` validates exactly.
- `docs/smoke-tests.md`: updated with a `## Reporting reminders` expectations
  section.
- `docs/target-mapping.md`: updated with the hook inventory and target scope.
- `docs/native-client-acceptance.md` and `docs/plan-deterministic-commit-gate.md`:
  no reporting or reminder claim. No change.
- `docs/2026-08-08-codex-routing-compatibility.md`,
  `docs/2026-08-09-planner-reliability-calibration.md`, and
  `docs/2026-08-09-state-sync-rebase-recovery.md`: dated records, left alone.
- `shared/policies/agent-reporting.instructions.md`: the single writing
  authority, extended with `## Violations to recognize`.
- `shared/policies/workflow.instructions.md` and `workspace.instructions.md`:
  their `UserPromptSubmit` statements describe state synchronization and remain
  true; the reminder is additive. No change.
- `shared/agents/*`, `shared/skills/*`, `shared/templates/*`, and
  `shared/review-profiles/*`: no copied writing rules to correct. No change.
- State directory READMEs (`.claude/plans/`, `.claude/session_logs/`,
  `.claude/quality_reports/`, `.claude/explorations/`): no reporting claim. No
  change.
- `.claude/MEMORY.md`: its existing lesson that audience-aware writing rules
  need one canonical policy with prompt pointers is consistent with this change.
  Five new lessons appended.
- `.claude/session_logs/2026-09-08_language-reporting-reminder-hardening.md`:
  left as the `PAUSED` pause evidence. Its remaining-work list was stale on
  resume, but no completion receipt binds it and this log records the correct
  final state, so no errata file is warranted.

## [LEARN] Entries

- [LEARN:testing] A hook that needs committed AI state must read the nested
  `.claude` repository (`git -C "$ROOT/.claude" show "HEAD:plans/<plan>.md"`),
  not the outer repository, which gitignores `.claude/`. The outer form always
  fails and quietly turns a fail-closed boundary into dead code. A fixture that
  tracks `.claude/plans/*.md` in one flat repository hides this completely.
- [LEARN:testing] Review shell hooks by executing them, not by reading them. A
  reading-only pass judged a dead-code git read "correct"; execution exposed it
  immediately.
- [LEARN:architecture] Do not add outcome gating to an advisory hook when the
  runtime payload has no verified tool-outcome field. Classify from command
  shape and document that honestly, or correlate against real committed state
  where the boundary allows it.
- [LEARN:workflow] A PAUSED session log's remaining-work list can be stale: the
  interrupted agent may have already finished it. Verify the working tree and
  the suite before re-delegating.
- [LEARN:testing] This repository's branch guard and commit gate intercept
  `git checkout -b <slug>_implementation` and `git commit` issued through Bash
  even when they target a throwaway fixture directory. Prove hook behavior in
  pytest instead.

## Open questions and next steps

- Native acceptance for both clients stays open until an authenticated client is
  available. Re-run the bounded acceptance check then, and keep the dated
  UNVERIFIED record until it passes.
- The phase-completion-commit boundary depends on a warn-never-fail state
  synchronization step. If future work needs a guaranteed late reminder at that
  point, that dependency is the thing to change, not the reminder.
- Measure before considering periodic, `PreCompact`, or `Stop` reminders, which
  this version deliberately excludes.
