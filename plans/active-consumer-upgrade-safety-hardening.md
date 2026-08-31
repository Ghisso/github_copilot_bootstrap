---
name: active-consumer-upgrade-safety-hardening
type: big-plan
status: complete
originating_branch: dev
implementation_branch: active-consumer-upgrade-safety-hardening_implementation
started_at: 2026-08-30T14:44:50Z
phases:
  - 2026-08-30_phase-A-active-consumer-upgrade-safety-hardening
  - 2026-08-31_phase-B-checkpointed-terminal-push-recovery
current_phase:
---
# Big Plan: active-consumer-upgrade-safety-hardening

## Context

`consumer-verification-provenance-hardening` is complete with three finished
phases: consumer-native verification, nested control-plane provenance and
generated-consumer lifecycle proof, and terminal-push provenance recovery.

Post-completion testing against an upgraded active consumer found three new
MAJOR gaps that were not fully covered by the original acceptance criteria:

1. provenance binds the nested `.claude` runtime/mirror but not every live
   generated root adapter that consumers actually execute;
2. the terminal big-plan transition exception can return true without
   independently requiring the recorded current small plan to be complete and
   unchanged;
3. the supported old-to-new active-consumer refresh path is not covered by one
   committed deterministic regression spanning schema-v2 evidence to schema-v3
   runtime/evidence.

The completed parent plan also has a historical consistency defect: its
frontmatter lists three phases, but the body still says "Why Two Phases" and
lists only phases A/B.

The observed upgrade simulation otherwise passed important safety checks:
active plans/evidence were preserved, dirty active-plan state was checkpointed,
nested `.claude` ended clean with a valid HEAD, schema-v2 receipts were
preserved but rejected by schema v3, evidence-only checkpoints did not
self-stale provenance, active-plan/runtime mutations did stale provenance, and
`--local-only` used no remote Git operation.

## Goals

- Bind every bootstrap-owned live generated adapter that can affect consumer
  behavior to the provenance trust boundary.
- Reuse the existing ownership/runtime manifest as the sole adapter inventory.
- Fail closed for required live-adapter absence/type/symlink/content mismatch.
- Make both terminal-transition provenance paths independently require the
  recorded current small plan to be complete and unchanged.
- Add one offline deterministic old-to-new active-plan upgrade regression using
  the real installer, verifier, closeout, commit, and pre-push paths.
- Preserve schema-v2 evidence on upgrade while ensuring it cannot authorize
  schema-v3/current gates.
- Preserve the `--local-only` no-network contract.
- Document the supported mid-plan consumer upgrade procedure.
- Correct or prevent big-plan frontmatter/body phase-inventory drift.
- Preserve all current workflow, verification, reviewer, pause, score, findings,
  Context Mode, provider, and gate behavior except these targeted fixes.

## Non-Goals

- Do not reopen/rewrite completed predecessor phases A/B/C.
- Do not redesign control-plane provenance.
- Do not create another adapter inventory or recursive root scanner.
- Do not hash consumer-owned mutable state.
- Do not add a historical-version matrix or network-dependent historical checkout.
- Do not weaken outer/nested provenance, schema-v3 parsing, score/findings,
  branch/plan/pause/cancellation/bypass, commit/push/PR rules.
- Do not change Context Mode/Semble or provider model/tool routing.
- Do not change paused checkpoint publication semantics.
- Do not add PMAT, `pv`, Lean, Kani, or another contract framework.

## Design

### Live root-adapter provenance

Use the existing ownership/runtime manifest. For every bootstrap-owned live
adapter installed outside `.claude`, provenance must establish that the
consumer-visible adapter matches its bound generated state.

Expected families include current live equivalents of:

```text
.codex/hooks.json
.agents/
.mcp.json
.vscode/mcp.json
AGENTS.md
CLAUDE.md
```

Do not hard-code this list when the manifest already provides it.

Validate only semantics already meaningful in the current cross-platform
ownership contract: path, file/directory type, supported symlink semantics, and
content equality/hash. Include mode/permissions only if already authoritative.

Missing, unreadable, mismatched, partially discovered, wrong-type, or unexpected
symlink state is unavailable provenance, never PASS. Keep the operation bounded
by the finite manifest.

### Terminal-transition small-plan invariant

The terminal big-plan transition exception is valid only if the recorded current
phase exists in the big plan, its small plan is `complete`, current small-plan
bytes remain authoritative/unchanged, later phases satisfy cancellation rules,
the big-plan change is exactly the accepted automatic terminal transition, and
no other relevant nested dirty/index/runtime/plan mutation exists.

Both immediate/unstaged and clean-checkpoint terminal paths must use the same
shared small-plan validator. Python provenance must be correct independently of
surrounding Bash gates.

### Offline old-to-new active-consumer upgrade regression

Use one deterministic consumer and one minimal version/hash-pinned legacy
schema-v2 fixture. Do not fetch historical commits during tests.

Exercise:

```text
legacy schema-v2 consumer with active work
-> local-only supported refresh
-> preserve active/user state
-> install schema-v3/current runtime
-> reject old receipts
-> checkpoint governing nested state
-> verify fast
-> verify phase --persist
-> deterministic closeout evidence
-> verify closeout --persist
-> native commit gate
-> terminal plan transition
-> native pre-push gate
```

Cover both immediate terminal worktree and supported clean-checkpoint pre-push
states. No LLM calls.

## Why One Phase

These are three defects in one consumer-upgrade/provenance trust boundary. The
existing architecture is already stable. Splitting them would add review/score/
commit ceremony without an independent rollback boundary.

## Phase

- [ ] `2026-08-30_phase-A-active-consumer-upgrade-safety-hardening`
- [ ] `2026-08-31_phase-B-checkpointed-terminal-push-recovery`

## Repository-Wide Acceptance

- No owned live generated adapter can differ while provenance still matches.
- Live adapter discovery comes only from the existing ownership/runtime manifest.
- Missing/type/symlink/content mismatch fails closed.
- Consumer-owned mutable state remains outside the fingerprint.
- Terminal provenance cannot pass unless the recorded current small plan is
  complete and unchanged.
- Both terminal paths enforce identical small-plan semantics.
- Old schema-v2 active-consumer refresh preserves required active/user state.
- Schema-v2 receipts remain preserved but cannot authorize current gates.
- Regenerated current evidence reaches native commit and pre-push allow.
- Arbitrary live-adapter, plan, runtime, receipt, dirty, and index-only mutations
  remain denied.
- `--local-only` performs no remote Git command.
- Parent-plan body/frontmatter phase inventory cannot remain contradictory.
- Zero CRITICAL and zero MAJOR findings remain before merge.
- Full generated/install/runtime/state-sync/determinism coverage passes.

## Verification

```bash
uv run pytest tests/ -q --tb=short
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

Also run the committed old-to-new active-plan integration independently and
exercise native installed commit/pre-push allow/deny paths.

## Merge Gate

Do not merge the current implementation line into `dev` until all three MAJOR
findings are closed, full verification passes, the offline active-plan upgrade
regression passes, installed commit/pre-push cases pass, and zero CRITICAL/MAJOR
findings remain.
