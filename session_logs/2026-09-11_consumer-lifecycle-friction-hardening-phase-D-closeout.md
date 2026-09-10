# Consumer Lifecycle Friction Hardening — Phase D Closeout

**Status:** COMPLETED
**Plan:** `.claude/plans/2026-09-10_phase-D-shell-classifier-runtime-guidance.md`
**Branch:** `consumer-lifecycle-friction-hardening_implementation`
**Started:** 2026-09-11

## Goal

Reduce false fail-closed results for safe heredocs and process substitutions
without treating their inner content as harmless prose, prove the whole plan
composes in a generated consumer, and complete the standing final-phase audit.

## Completed phase

Phase D: `.claude/plans/2026-09-10_phase-D-shell-classifier-runtime-guidance.md`

This is the big plan's last declared phase.

## Work log

- Steps 1-4 were implemented test-first, as the parent plan's Risks section
  requires for a security relaxation. Writing the negative controls before the
  parser is what made the rest of this phase's findings possible.
- The pre-implementation test run against the unmodified classifier exposed
  three real under-protection gaps rather than only false positives:
  interpreter heredocs performing an opaque write were silently allowed; an
  unterminated heredoc and an unbalanced process substitution were silently
  allowed instead of failing closed; and a nested mutator was denied only
  through soft wording caused by token leakage, not real classification.
- Six review rounds followed. Each of the first five found at least one
  confirmed silent bypass. Round six returned clean.
- Step 5 corrected live shell-safety guidance and recorded the interpreter
  inline-script limitation.
- Step 6 ran generated-consumer acceptance for the complete plan.
- Step 7 performed the repository-wide stale-claims audit recorded below.

## Bypasses found and fixed

Six confirmed ways to write a protected file while the guard returned exit 0
with no output. Four existed before this phase began.

1. A heredoc nested inside a process substitution was never classified,
   because heredocs are extracted before process substitutions and the
   extracted mapping was not threaded into the recursive call. Fixed by
   sharing one mapping by reference through the recursion.
2. Heredoc bodies were skipped entirely for read-only consumers. That rule
   reused a list curated for "never writes through its arguments" to justify
   "never writes through its stdin", which is false: an unquoted delimiter
   lets the shell expand a command substitution before the consumer runs, and
   `sed`'s script language can write and execute without needing `-i`. Fixed
   by always applying the conservative floor and tracking delimiter quoting.
3. Quote-wrapped command substitution inside an unquoted heredoc body. Caught
   by the coder in its own first draft, which had treated quotes as
   suppressing detection. Heredoc bodies are not re-tokenized with quoting
   rules, so a single-quoted substitution still executes.
4. Placeholder gluing. When an operator had no preceding whitespace, as in a
   heredoc operator attached directly to the command name, the inserted
   placeholder concatenated onto the previous word and `shlex` merged them, so
   the command name became garbage and nothing was scanned. Fixed by padding
   placeholders on both sides.
5. Prefix-form environment assignments were not threaded into the bare-shell
   heredoc recursion, so a quoted-delimiter heredoc whose body wrote to a
   prefix-assigned target was missed. Fixed by distinguishing a prefix
   assignment from a persistent one and selecting by delimiter quoting.
6. Wrapper flags taking a separate value token, such as `env -u NAME`, caused
   the value to be misread as the command name, so the real interpreter was
   never dispatched. Fixed with flag tables plus a fail-closed backstop for
   unrecognized flags.

## Notable process outcomes

**Two reviewer reproductions were wrong, and verifying them mattered.** The
prefix-assignment repro used an unquoted delimiter, which does not exploit,
because the parent expands the body using a scope that never contains a prefix
assignment. Implementing against it would have changed correct behavior into a
false positive while leaving the real quoted-delimiter hole open. Separately,
an orchestrator check of a glued process substitution was itself flawed: it
captured output with a redirect, which creates the file whether or not the
command succeeds. The coder corrected it with `set -x` and confirmed the
vector is real by a different mechanism, since the inner command still
executes during word expansion even when the outer word fails.

**A requested fix would have caused a regression without a companion change.**
The fail-closed backstop for unrecognized wrapper flags only fails closed if
the fallback denies. That fallback had never examined heredoc bodies or
process-substitution content, both already placeholders by then, so an
ambiguous segment would have raised and then denied nothing. The coder found
this by verifying the backstop actually failed closed rather than merely
raised, and fixed the fallback in the same pass. That change also closed a
further pre-existing gap involving a process substitution supplied as a
wrapper flag's value.

**Three tests in this plan passed for the wrong reason.** Phase C's traversal
fixture never reached the vulnerable code path; two prefix-assignment controls
produced identical verdicts before and after their fix only because an empty
dictionary never resolves anything. Each was corrected, and the traversal test
was proven load-bearing by removing the guard and confirming the intended
assertion fails.

## Generated-consumer acceptance

A fresh consumer was generated, installed from the shipped artifacts into a
scratch directory, and driven through the entire lifecycle against a local
bare remote. The positive path completed with no manual state edit, bypass, or
receipt repair.

Exercised: `planned` activation at both transition boundaries; an annotated
phase inventory using two accepted delimiter forms; closeout with a real
stdin-message heredoc commit whose body contained shell metacharacters and an
unmatched apostrophe; native post-commit advancement; automatic nested state
checkpoint and publish; an ignored root adapter restored after a genuine
non-local-only pull; safe process substitution and safe heredoc allowed;
protected writes blocked inside both constructs including nested composition;
and a final push validated against the last completed receipt.

Two methodology points were disclosed rather than hidden.
`record-branch-state.sh` has no native git hook, so it was invoked with the
same payload shape a live session produces, matching this repository's own
hook-test technique. The scratch consumer's git commands were wrapped in
script files because this session's own commit gate resolves its repository
root from the hook script's location and therefore judges any commit-shaped
command text against this repository. The guard stayed active throughout, and
the consumer's own native hooks fired normally. The classifier cases were
invoked with JSON payloads, so the wrapping did not apply to them.

## Verification state

- `uv run pytest tests/ -q`: 1437 passed.
- `scripts/validate_targets.py`: generated target structurally valid.
- `scripts/check_runtime.py`: 0 failed.
- `scripts/validate_plan_frontmatter.py`: exit 0.
- `python3 -m py_compile` and `bash -n`: clean. The classifier was also
  compiled and functionally re-run under a real Python 3.9.0 interpreter with
  byte-identical verdicts, matching the standalone-hook baseline.
- Ruff check, Ruff format check, and Mypy passed.

## Review outcome

Six review rounds, each running the `code`, `architecture`, `security`,
`tests`, `ponytail`, and `documentation` profiles over two sequential passes.
Final gate: PASS.

One minor finding is accepted rather than fixed: the process-substitution
recursion over-denies a same-segment prefix assignment it would not actually
see in real bash. It fails safe by over-denying, and correcting it would
require generalizing the prefix-scope distinction to a second recursion point,
which was deliberately deferred.

## Known limitations recorded, not fixed

- The classifier never recursively parses interpreter inline-script arguments.
  Values passed to an interpreter's inline-script flag are scanned only for
  literal protected paths, so a path assembled from pieces inside one is not
  detected. Pre-existing at every call site and unchanged by this phase.
  Fixing it would mean a recursive parser per interpreter language, which the
  settled decisions rule out. Now documented in live guidance and
  `.claude/MEMORY.md`.
- `record-branch-state.sh` is dispatched only from `PostToolUse`, with no
  native git-hook counterpart, so creating a branch by hand in a terminal does
  not activate the first `planned` phase. `record-commit-closeout.sh` is a real
  native `post-commit` hook and works either way. This asymmetry may be
  intentional; it is recorded for a future decision rather than changed here.
- One `.claude/MEMORY.md` sentence stating that write targets built from shell
  variables are flagged uncertain may be inaccurate for a genuinely unresolved
  variable, which appears to be dropped rather than flagged. The claim is
  pre-existing and unchanged by this phase; flagged for later confirmation.

## [LEARN] Entries

- [LEARN:security] Write the negative controls before relaxing a fail-closed
  security parser. The pre-implementation run here exposed three real
  under-protection gaps that no amount of positive-case testing would have
  surfaced, and it set the baseline that made six later bypasses provable.
- [LEARN:review] Verify a reported reproduction before implementing against
  it. Two repros in this phase were wrong in ways that would have produced a
  fix for working behavior while leaving the real defect open.
- [LEARN:review] A test corpus that shares a formatting convention shares a
  blind spot. Every heredoc test used a space before the operator, so glued
  operators went unexercised through two review rounds even though they are
  ordinary valid shell.
- [LEARN:review] Before-and-after comparison proves a delta, not security. It
  is structurally blind to any defect present unchanged in both states, which
  is exactly how the gluing bypass survived.
- [LEARN:security] Replacing a hard failure with a silent skip is not
  automatically safe. Confirm per site that zero iterations is correct, and
  that a fail-closed backstop actually reaches a path that denies.

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
