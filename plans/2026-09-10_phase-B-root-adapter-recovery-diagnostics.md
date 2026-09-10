---
name: 2026-09-10_phase-B-root-adapter-recovery-diagnostics
type: small-plan
parent_plan: consumer-lifecycle-friction-hardening
phase_index: 2
status: in-progress
closeout_session_log:
paused_at: 2026-09-10T12:24:00Z
paused_reason: User requested a usage-limit checkpoint during Phase B review remediation
pause_session_log: .claude/session_logs/2026-09-10_consumer-lifecycle-friction-hardening-phase-B.md
---

# Small Plan: Phase B — Root Adapter Recovery and Diagnostics

## Scope

Make session startup restore installer-owned ignored root adapters after the
nested AI-state pull, including already-initialized repositories. When adapter
provenance is unavailable, report the exact manifest-relative path and failure
category without disclosing file content. Preserve warn-never-fail session
behavior while testing the durable filesystem postconditions directly.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` in `full` mode
- `.claude/skills/code-style/SKILL.md`
- `.claude/skills/testing-patterns/SKILL.md`
- `.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md`

## Review Profiles

- `code`
- `architecture`
- `security`
- `tests`
- `ponytail`
- `documentation`

## Steps

1. **Return path-level adapter diagnostics from the existing fingerprint walk.**
   Owner: `coder`.
   Refactor the smallest shared portion of `shared/scripts/verify.py` so
   `bootstrap_root_fingerprint()` retains its digest contract while callers can
   obtain structured relative-path diagnostics from the same validation pass.
   Distinguish invalid/missing ownership manifest, live missing or unsafe,
   mirror missing or unsafe, unsupported file type, unreadable bytes, and live
   versus mirror content difference. Never include contents, absolute external
   paths, or hashes that are not already part of receipt metadata.

2. **Surface actionable provenance failures.**
   Owner: `coder`.
   Thread the diagnostic details into verifier measurement and gate errors
   without changing PASS/FAIL authority. When the mirror is valid and the live
   ignored adapter is missing or different, include the exact recovery command
   `bash .claude/hooks/scripts/restore-root-adapters.sh`. For an invalid mirror
   or ownership manifest, do not recommend restoration as if it could repair
   the source of truth. Add tests asserting both detail and non-disclosure.

3. **Restore adapters after every successful pull path.**
   Owner: `coder`.
   Modify `shared/hooks/scripts/state-sync.sh` so `cmd_pull` invokes the existing
   `restore_root_adapters` only after local setup and any configured remote
   reconciliation succeed. Cover local-only, no-remote, existing nested repo,
   fresh repo, successful remote pull, and failed/conflicted pull. Do not
   restore from state that failed to reconcile. Keep the top-level SessionStart
   hook warn-never-fail and preserve the restoration script's rule that tracked
   outer files are never overwritten.

4. **Prove installer-owned boundaries and generated parity.**
   Owner: `coder`.
   Extend `tests/test_state_sync.py`, `tests/test_verify.py`,
   `tests/test_install_bootstrap.py`, and the generated consumer checks in
   `scripts/validate_targets.py`. Cover the reported missing `.github/`
   adapters, directory adapters, tracked-file skip, symlink ancestry, missing
   mirror, divergent live bytes, and session-start restoration after a branch
   switch. Assert valid nested `HEAD` and clean nested state where a
   warn-never-fail wrapper cannot prove preservation by exit code alone.

5. **Update ownership and recovery documentation.**
   Owner: `documenter` after code review converges.
   Update only live guidance under `docs/`, shared policies, or state READMEs
   that describes root-adapter restoration and verifier provenance. State when
   restoration runs, which manifest owns the paths, why tracked files are
   skipped, and how to interpret each diagnostic. Do not edit receipt-bound
   historical logs.

## Acceptance Criteria

- [ ] Every successful session-start pull restores missing installer-owned ignored adapters from the validated mirror.
- [ ] Failed reconciliation never restores potentially stale pulled state.
- [ ] Tracked root adapters remain untouched.
- [ ] Provenance errors name the relative manifest path and exact failure category.
- [ ] Recoverable live-side errors suggest `restore-root-adapters.sh`; invalid source-side errors do not.
- [ ] Diagnostics expose no adapter contents or unsafe external paths.
- [ ] Warn-never-fail hooks remain non-blocking, while tests verify durable postconditions directly.

## Verification

```bash
uv run pytest tests/test_state_sync.py tests/test_verify.py tests/test_install_bootstrap.py -q
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run ruff check shared/scripts/verify.py tests/test_state_sync.py tests/test_verify.py tests/test_install_bootstrap.py scripts/validate_targets.py
uv run mypy shared/scripts/verify.py tests/test_state_sync.py tests/test_verify.py tests/test_install_bootstrap.py scripts/validate_targets.py --ignore-missing-imports --explicit-package-bases
uv run python .claude/scripts/verify.py phase --format json --persist
```

## Closeout Checklist

- [ ] Verification passed (`verify phase` PASS)
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record `paused_at`, `paused_reason`, and
`pause_session_log`, and keep the big plan `in-progress` with this same
`current_phase`. Resume this file rather than creating a replacement phase.
