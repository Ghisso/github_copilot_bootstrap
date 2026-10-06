# Behavioral evaluation pilot — pause and continuation handoff

**Status:** PAUSED
**Plan:** .claude/plans/2026-10-03_phase-D-behavioral-pilot-knowledge-refresh.md
**Parent plan:** .claude/plans/behavioral-evaluation-pilot.md
**Paused at:** 2026-10-06T13:59:31Z
**Reason:** User explicitly requested stopping at the next possible logical boundary and a detailed handoff for another agent.

## Exact stopping point

Implementation, documentation, the live-advice audit, both managed OpenWiki
runs, independent review, and full phase verification are finished. Stop
before Phase D CLOSEOUT. The full verifier was already running when the user
asked to stop; it finished successfully. No more checks or source changes are
needed merely to investigate the native client exits.

The big plan is `in-progress`. Its `current_phase` remains
`2026-10-03_phase-D-behavioral-pilot-knowledge-refresh`, which is `paused`.
Do not create a new plan or advance the phase. The earlier temporary
`complete` statuses were preparation for closeout and have been corrected
to reflect the user-requested pause.

## Git and publication

- Branch: `behavioral-evaluation-pilot_implementation`.
- Base: `a6346968c5bb1fdc4ee4fc1dca43e23d327af3fd`, the required merge on dev.
- Completed Phase A commit: `f3a8337fed3243023d225a6558b60e479c0d2fcb`.
- Local, non-final Phase D checkpoint: `f9c47f7`
  (`chore: checkpoint behavioral pilot final phase before closeout`).
  It retained D as paused and is not a final phase completion commit.
  Outer worktree was clean after it; the big plan remained in progress.
- No outer-repository push succeeded. Automatic approval review rejected
  `git push -u origin HEAD` because remote ownership/trust was not established.
- The verified configured remote is
  `https://github.com/Ghisso/github_copilot_bootstrap.git`.
  `gh repo view` and `gh api user` cannot establish account ownership because
  GitHub CLI is unauthenticated. Do not work around the rejected push.
  Before a later push, obtain explicit user approval for this exact destination
  or new evidence accepted by approval review. The user has now asked to stop,
  so no publication approval is being requested during this checkpoint.
- Do not push the nested `.claude` repository manually. Its existing hooks
  handle state synchronization separately.

## Settled pilot result — do not repeat the experiment

The user ran all five approved native Claude Code calls. The repaired-packet
role probe produced one valid report with a parseable empty findings list.
It supports only **consistent with reviewer loading**: there was no
client-reported selected-agent field. Client version: `2.1.226`; only the
successful role record reports model `claude-sonnet-5`. The generated role
configured `sonnet` and `xhigh`; no overrides were used.

All four scheduled case runs were unavailable with `nonzero_client_exit`.
Their raw errors were intentionally discarded, so the cause is unverified.
Do not call these task failures, valid negative controls, or evidence of no
difference. There are zero valid defective case runs and zero valid control
case runs; the repaired role probe separately has zero false positives in one
valid output. No before/after comparison or detection rate exists.

BEP-001 holds at the limited role-evidence level. BEP-002 is unproven. The
approved stop rule cancelled B and C, with canonical cancellation metadata
and `.claude/session_logs/2026-10-06_behavioral-pilot-cancellation.md`.
The five-run budget is consumed. **Do not rerun any native session, change
the rubric, implement the cancelled runner/scorer, or revive B/C.** A new
experiment would require new explicit authorization, outside this plan.

Committed Phase A artifacts:

- `docs/2026-10-06-behavioral-pilot-evidence.md`: dated decision and limits.
- `docs/evidence/behavioral-pilot/phase-a/`: five bounded run records,
  frozen manifest, and one judgment/unavailable reason per run.
- `tests/fixtures/behavioral/requirement-review/`: frozen ten-file fixture.
- `tests/test_check_native_clients.py`: one prompt-neutrality regression test.

The scratch probe remains under `/tmp`; it is not committed. Its retained
result directory prevents reruns. The committed evidence is sufficient for
continuation; do not rely on scratch files surviving across machines.

## Phase D work already finished

Eight outer files form the reviewed checkpoint diff:

1. `README.md`: dated stopped-pilot link and advisory boundary.
2. `docs/native-client-acceptance.md`: same link and exact role-evidence limit.
3. `shared/templates/skill-template.md`: authoring versus installed skill paths.
4. `shared/agents/planner/workflow-prompt.md`: correct big/small status lists.
5. `openwiki/architecture/agents-and-skills.md`: corrected visibility,
   skill/status guidance, and stopped-pilot evidence boundary.
6. `openwiki/.claims/architecture/agents-and-skills.json`: managed claim repairs.
7. `openwiki/.last-update.json`: managed refresh provenance.
8. `openwiki/.page-manifest.json`: managed page provenance.

`generate_targets.py --all` ran. `check_runtime.py` initially found the
installed skill template stale; the supported
`scripts/install_bootstrap.py . --allow-self --local-only` refreshed it.
Tracked root adapters and mutable state were preserved; trust settings were
not changed. Do not hand-edit generated runtime or `dist/` files.

The source-audit coder reached a usage limit after its read-only report.
The orchestrator applied the two small prose corrections; the documenter
updated the two live documentation files. Independent review covered the
whole diff, so there is no unfinished coder or documenter task.

## OpenWiki and review evidence

Two managed `mode: update` runs completed:

- `e115c340-244c-40ca-9677-ce8ce344fe7b`: planned refresh of the agents page.
- `cf2ec248-4f91-4cf9-8d4f-4986fe3ece99`: narrow review correction to two
  evidence sets, without changing source or page body.

Both `openwiki_finish` calls returned `complete`. No `openwiki/.run.json`
remains. AGENTS.md, CLAUDE.md and OpenWiki workflow files are unchanged.
Claim sidecars were written only through OpenWiki tools. The final page has
29 claims. Do not start another refresh unless later source changes make it
necessary; before editing a cited source range, inspect the claim evidence.

Final reviewer profiles: `code`, `architecture`, `security`, `tests`,
`ponytail`, `documentation`; two passes. Result: PASS with no findings or
open requests. Two MINORs were corrected: roster exclusivity now cites all
eight agent definitions, and sidecar advisory evidence includes explicit
non-gating clauses. Scratch exact diff:
`/tmp/behavioral-pilot-phase-d-corrected.diff`; re-derive it from the checkpoint
commit if scratch is gone. No review finding remains to implement.

The persisted final-phase findings report is
`.claude/quality_reports/findings-2026-10-03_phase-D-behavioral-pilot-knowledge-refresh.json`.
Its clean finding set remains informative; its bindings must be regenerated
after resume because the checkpoint and pause change HEAD/plan provenance.

## Verification

- Generation, target validation, runtime wiring, plan frontmatter, fast
  verification, and `git diff --check`: PASS.
- Final full phase: PASS; Ruff clean, mypy zero errors, **2326 tests passed
  in 214.65 seconds**.
- Persisted phase receipt:
  `.claude/quality_reports/verification-phase-2026-10-03_phase-D-behavioral-pilot-knowledge-refresh.json`.
- Final Phase D closeout dry run: NOT RUN.
- Final Phase D closeout receipt: NOT CREATED.
- Final completed-phase commit and outer push: NOT DONE.
- Native experiment: five calls consumed; no reruns.

Commands in this environment use `UV_CACHE_DIR=/tmp/behavioral-pilot-uv-cache`
because the default uv cache is read-only. Git mutations and the full verifier
need normal sandbox escalation: without it `git write-tree` cannot produce
`tree_sha`, and the verifier cannot create a receipt. This is an environment
permission issue, not a reason to bypass the gate or edit the verifier.

## Precise continuation sequence

1. Read this handoff, the big plan, the Phase D small plan, the Phase D log,
   and `.claude/instructions/workflow.instructions.md`. Inspect current
   `git log --oneline -5`, outer/nested status and diff; preserve unrelated work.
2. Set the **same** Phase D plan from `paused` to `in-progress`, preserving
   its latest `paused_at`, `paused_reason`, and `pause_session_log`. Keep the
   big plan in progress and `current_phase` on D while resuming.
3. Reuse the existing implementation and reviewed evidence. Do not rerun
   native Claude, restore B/C, rewrite closed Phase A evidence, or repeat the
   wiki refresh without new source changes. Required review is already clean;
   review any new edits if continuation introduces them.
4. Follow the canonical CLOSEOUT sequence. Complete the Phase D plan and big
   plan only as final closeout preparation; finalize the existing Phase D log
   at `.claude/session_logs/2026-10-06_behavioral-pilot-phase-d.md` with
   `**Status:** COMPLETED`, its requirement mapping, exact
   `## Stale-claims surfaces checked` heading, and the canonical marker
   `[LEARN] none - no new lessons this session`. Preserve this PAUSED handoff
   as the historical resume record.
5. Checkpoint final nested plan state before staging/persisting findings.
   The outer checkpoint already contains the eight reviewed files. An empty
   final completion commit may be needed because the checkpoint contains all
   implementation work; use only the ordinary gated completion path, never a
   bypass. Inspect the gate contract if it requests specific remediation.
6. Rebind findings and rerun `verify.py phase --format json --persist` because
   HEAD and plan state changed after the recorded phase run. Run
   `verify.py closeout --format text` **without** persist. It runs the Phase D
   required commands: `validate_targets.py`, `check_runtime.py`,
   `validate_plan_frontmatter.py`, and `verify.py fast --format json`.
7. Paste the required command summary lines into the final Phase D log's
   Verification section. Keep its existing `- optional 1: PASS` OpenWiki
   outcome. Make the second nested checkpoint, then run
   `verify.py closeout --format json --persist`.
8. Run the final completion commit in its own command. Do not touch nested
   state between the persisted closeout receipt and that commit. The
   post-commit hook owns phase/state synchronization. Do not manually push
   nested state. Do not rewrite the Phase A commit or use a bypass prefix.
9. Publication remains blocked by the prior automatic approval rejection.
   Obtain approval for the exact configured GitHub destination before a new
   attempt. No PR or merge has been requested. Report final local commit(s)
   and publication status honestly.

## [LEARN] Entries

[LEARN] none - no new lessons this session

The detailed execution history belongs in these dated logs. No new cause of
the client exits was established, so no speculative MEMORY entry was added.
