## Stale-claims surfaces checked

Repository-wide sweep for the big plan `consumer-lifecycle-friction-hardening`'s
final phase (Phase D), covering all five phases (A, B, B2, C, D). Each entry
below was verified against current code before any correction was made.

### Corrected

- `docs/runtime-checks.md` — the "Other gates that newly block a refresh"
  table said `planned` "looks plausible but has never been a valid value" for
  plan `status`. Phase C added `planned` as a real small-plan status
  (`SMALL_PLAN_STATUSES` in `scripts/validate_plan_frontmatter.py` includes
  `"planned"`). Corrected the row to list `planned` as a valid small-plan
  value instead of calling it invalid.
- `README.md` — the "Plan status" bullet made the identical now-false claim
  ("`planned`, which has never been a valid value"). Corrected to list
  `planned` as valid and note that new small-plan files default to it.
- `docs/runtime-checks.md` — the devcontainer bootstrap paragraph said
  `post-start.sh` runs `state-sync.sh pull` **and** `restore-root-adapters.sh`
  as two separate steps. Phase B moved that restoration inside `pull` itself
  (`finish_pull` in `shared/hooks/scripts/state-sync.sh`); `post-start.sh` no
  longer calls `restore-root-adapters.sh` directly (confirmed against the
  current `shared/devcontainer/post-start.sh`, which only calls
  `state-sync.sh setup` then `state-sync.sh pull`). Corrected to describe
  `pull` restoring adapters internally.
- `docs/architecture.md` (two places) — the devcontainer bootloader summary
  and the "rendered in two locations" paragraph both said `post-start.sh`
  bootstraps AI state via `state-sync.sh`/`restore-root-adapters.sh` as if
  `post-start.sh` called both directly. `restore-root-adapters.sh` is still
  rendered into `.devcontainer/` and still used — but now only via
  `state-sync.sh` calling it internally (`local restore=... restore-root-adapters.sh`
  in `state-sync.sh`), not via a direct `post-start.sh` call. Corrected both
  to attribute the call to `state-sync.sh`, not `post-start.sh` directly.
- `docs/runtime-checks.md` (`The refreshed hook guards are stricter...`
  paragraph, part of Phase D step 5 already done this phase, re-verified here
  for the full sweep) — no longer claims process substitution/heredocs are
  denied outright; states they're recursively classified, malformed syntax
  still fails closed, wider syntax support does not weaken nested-write
  detection, and records the `-c` script-content limitation. Already correct
  from the earlier step-5 pass; re-checked, no further change needed.
- `.claude/MEMORY.md` (three entries, corrected earlier in this same phase's
  step-5 pass, re-verified here as part of the full sweep):
  - `[LEARN:tooling]` entry that said the shell guard "denies process
    substitution, heredocs piped into an interpreter" — corrected to say it
    recursively classifies both instead of blanket-denying them.
  - `[LEARN:tooling]` entry that said `for`/`while`/`{ }`/heredocs all raise
    `AmbiguousCommand` (exit 2) — corrected to remove heredocs/process
    substitutions from that group (verified via direct classifier
    invocation: well-formed heredocs/process-subs now exit 0 and are
    classified; only malformed/unterminated syntax exits 2).
  - Added a new `[LEARN:security]` entry recording the pre-existing,
    unchanged `-c` script-content limitation (`bash -c '...'`/
    `python3 -c '...'` are only scanned for literal protected paths, not
    recursively parsed), per the reviewer's explicit request that it be
    recorded durably.
- **New gap found by the acceptance run** (not a stale claim, a missing one):
  committing/checkpointing the nested `.claude` AI-state repository before
  `verify.py closeout --persist` changes what the persisted receipt's
  `control_plane_provenance` (specifically the relevant nested tracked/dirty
  state, which unlike `nested_head` is not treated as informational — see
  `control_plane_provenance_matches` in `shared/scripts/verify.py`, which
  compares every field except `nested_head`) binds to, and the next commit
  fails closed with "closeout receipt governing control-plane provenance is
  stale". Verified against `shared/scripts/verify.py`
  (`nested_tracked_state_fingerprint`, `control_plane_provenance_matches`)
  and `shared/hooks/git-hooks/post-commit` (which runs
  `record-commit-closeout.sh` then `state-sync.sh push` — i.e. the nested
  checkpoint is meant to happen automatically *after* the outer commit, not
  manually before closeout persist). Documented the correct order — persist
  receipts last, leave nested `.claude` changes uncommitted, let the native
  `post-commit` hook checkpoint them — in three places: the CLOSEOUT step in
  `shared/policies/workflow.instructions.md`, the `control_plane_provenance`
  paragraph in `docs/runtime-checks.md`, and the CLOSEOUT step in
  `shared/agents/orchestrator/prompt.md`.

### Checked, no change needed

- `CLAUDE.md`, `AGENTS.md` — generic lifecycle/workflow references
  (`pre-flight -> branch -> plan -> implement -> verify -> review -> closeout
  -> commit`, orchestrator/coder/reviewer chain). No phase-count, closeout-
  order, shell-classifier, or root-adapter claim that any phase invalidated.
- `shared/policies/tool-routing.instructions.md` — already states "Prompt
  text, memory, or other inherited context that names a filtered or
  unavailable Context Mode operation does not make that operation callable"
  (Phase C requirement). Already accurate.
- `shared/agents/reviewer/prompt.md` — already states the diff-scoped
  evidence contract (changed paths plus scoped diff/artifact/changed hunks;
  no `execute` capability; full-file reads are not equivalent to diff
  review). Already accurate, matches Phase C's settled decision.
- `shared/agents/orchestrator/prompt.md`, `shared/agents/coder/prompt.md` —
  already state the incremental-intent material-deviation rule (a full
  rebuild when incremental/delta work was requested requires evidence and
  orchestrator approval). Already accurate.
- `shared/plans/README.md` — already accurately documents the `planned`
  status, its defaulting behavior, and activation-on-branch/post-commit.
  Already accurate; no correction needed.
- `shared/templates/plan-small.md` — already defaults new phases to
  `planned` and notes post-commit hooks flip the active phase to
  `in-progress` automatically. Already accurate.
- `shared/policies/quality-and-testing.instructions.md` — already references
  "the native post-commit hook" completing the final big-plan transition.
  Already accurate.
- `.claude/MEMORY.md` — searched for other Phase A/B/C claims
  (`post-commit`, `record-commit-closeout`, `PostToolUse`, `restore-root-
  adapters`, `in-progress` defaults, `current_phase`). The existing
  `[LEARN:workflow]` entry on advancing phases from the native `post-commit`
  hook is accurate (Phase A). No entry claims the old `PostToolUse`-based
  phase-advancement mechanism. No entry claims a fixed four-phase shape for
  this specific big plan.
- `docs/smoke-tests.md` — the `.devcontainer/` generated-file list still
  correctly includes `restore-root-adapters.sh` (the file is still
  generated, just invoked differently); the `protect-files.sh`/classifier
  description doesn't claim heredocs/process substitutions are denied.
  Already accurate.
- `docs/target-mapping.md` — the devcontainer bootloader description
  ("restores ignored AI bootstrap/state files by checking `.claude/` out
  from its nested `ai-state` git branch") describes the user-visible outcome,
  not the internal call chain Phase B changed. Still accurate.
- `docs/native-client-acceptance.md` — no `planned`/heredoc/process-
  substitution/root-adapter/post-commit claims found.
- `docs/plan-deterministic-commit-gate.md` — dated design narrative
  (`**Date:** 2026-07-08`, `**Status:** Proposed`, historical plan
  `R-HOOKS-07`), left unchanged per scope even though it separately
  references the retired HF-bucket sync — that staleness predates this plan
  and belongs to a different historical record, not one of this plan's five
  phases.
- `docs/2026-08-08-codex-routing-compatibility.md`,
  `docs/2026-08-09-planner-reliability-calibration.md`,
  `docs/2026-08-09-state-sync-rebase-recovery.md` — dated design narratives,
  left unchanged per scope.
- `.claude/plans/consumer-lifecycle-friction-hardening.md` (the parent big
  plan itself) — its Devil's Advocate table row "Four phases add lifecycle
  overhead" now understates the actual phase count (five, after Phase B2 was
  inserted). Plan files are outside this task's edit scope (`shared/`,
  `scripts/`, `docs/`, `.claude/MEMORY.md`, and this one session log only),
  so left unchanged and flagged here instead of silently ignored.

### Errata files

None created. No receipt-bound closed session log was found to contain a
claim that would actively mislead a reader into reintroducing a defect; every
correction above targeted live guidance (`docs/`, `README.md`, `shared/`
policy and agent prompts, `.claude/MEMORY.md`), which this task edits in
place rather than annotating with an errata sibling.
