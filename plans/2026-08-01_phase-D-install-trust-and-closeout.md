---
name: 2026-08-01_phase-D-install-trust-and-closeout
type: small-plan
parent_plan: ai-state-lifecycle-sync
phase_index: 4
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-01_phase-D-install-trust-and-closeout

## Scope

Make the generated Codex hook trust boundary visible during direct install and
batch update, then close cross-runtime documentation, validation, and
determinism gaps. Trust remains an explicit human action: no installer code may
approve a hook hash or edit a user-level Codex trust store.

This phase should be small. `update_consumers.py` already streams each delegated
installer's output; reuse that behavior unless a regression proves the trust
notice is lost.

## Ownership

- `coder`: installer notice and behavioral validation; updater only if needed.
- `documenter`: final user/operator docs and lifecycle parity cleanup.
- `verifier`: full generation, validator, runtime, test, type/lint/format, and
  deterministic-output gates.
- `reviewer`: final two-pass cross-runtime/control-plane review.
- `orchestrator`: persisted findings/score, plan/LEARN/session-log closeout,
  atomic commit, and PR handoff when explicitly requested.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` — `full` mode throughout.
- `.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md` — preserve direct,
  local-only, legacy, and batch installer postconditions.
- `.claude/skills/testing-patterns/SKILL.md` — CLI-output and integration cases.
- `.claude/skills/run-tests/SKILL.md` — complete verification route.
- `.claude/skills/documentation/SKILL.md` — install/update/troubleshooting prose.
- `.claude/skills/ponytail-review/SKILL.md` — mandatory final reduction review.

## Steps

### 1. Add failing install/update trust-notice coverage

- **Owner:** `coder`
- **Files:** modify installer/updater cases in `scripts/validate_targets.py`;
  add a focused pytest only if it tests behavior not already exercised through
  `tests/test_validate_targets.py`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` (`full`),
  `.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md`, and
  `.claude/skills/testing-patterns/SKILL.md`.
- Assert a successful direct install and a successful batch update both expose
  guidance that:
  - names `.codex/hooks.json` and Codex for VS Code;
  - says project hook trust is bound to hook content/hash, so an install/update
    can require review/retrust;
  - tells the user to reopen/reload the repository and review/approve the
    project hooks when prompted before relying on the new lifecycle;
  - never says the installer trusted/approved the hooks and never edits a
    user-level trust path.
- Cover default and `--local-only` install/update output. Dry-run should state
  the future trust action because it previews an update, but must not claim any
  hook content changed on disk.
- Retain every existing clean nested-state, migration ordering, Trace2 no-I/O,
  manual publish command, and default remote-publication assertion.
- **Verify:** run
  `uv run pytest tests/test_validate_targets.py -q --tb=short`; preserve the
  failing result before Step 2 and the passing result afterward, then run
  `uv run python scripts/validate_targets.py`.

### 2. Print deterministic, non-authoritative trust guidance

- **Owner:** `coder`
- **Files:** modify `scripts/install_bootstrap.py`; modify
  `scripts/update_consumers.py` only if Step 1 proves delegated output is not
  visible or needs one final batch summary.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` (`full`) and
  `.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md`.
- Add one small installer reporting function/call near successful closeout,
  after the generated hook path is known. Keep the text stable for users and
  tests, include the resolved project/hook path only if doing so remains
  shell-/credential-safe, and distinguish normal versus dry-run wording.
- Do not compute/invent a hash algorithm, automatically open a GUI, write trust
  state, or make network calls. The fact that trust is hash/content scoped is
  guidance; Codex remains the authority that prompts and records approval.
- Let the updater inherit one notice per consumer from the installer. Avoid a
  duplicate updater implementation unless necessary.
- **Verify:** direct/default/local-only/dry-run and batch-updater cases in the
  validator, using `uv run python scripts/validate_targets.py`.

### 3. Finish living docs and exact parity validation

- **Owner:** `documenter` for prose; `coder` for checks.
- **Files:** final edits as needed in `README.md`, `docs/architecture.md`,
  `docs/runtime-checks.md`, `docs/smoke-tests.md`, `docs/target-mapping.md`,
  `shared/policies/workflow.instructions.md`, `scripts/validate_targets.py`,
  and `scripts/check_runtime.py`.
- **Required Skills:** `.claude/skills/documentation/SKILL.md` and
  `.claude/skills/ponytail/SKILL.md` (`full`) for executable checks.
- Add install/update steps for Codex VS Code trust/retrust and a troubleshooting
  path using `state-sync.sh status` plus
  `.claude/session_logs/hooks-errors.log`.
- Present the final lifecycle matrix:
  - both Stops are one sequential wrapper and remain turn-scoped;
  - both UserPromptSubmit events publish pending committed state;
  - Codex SessionEnd is local checkpoint only, timeout `3`, delayed/best-effort;
  - Claude StopFailure is local checkpoint;
  - Claude SessionEnd checkpoints+publishes, timeout `60`;
  - post-commit and manual VS Code push remain independent durability paths.
- Validate exact parsed hook commands/counts/timeouts, wrapper executability,
  no plain Codex Stop stdout, no forbidden Codex SessionEnd network mode, and
  no separate concurrent Claude SessionEnd operations.
- Ensure runtime checker required-file lists include both wrappers and living
  docs no longer claim Stop is a session-only/guaranteed boundary.
- Do not add brittle assertions that can pass on a matching comment or prose
  fragment.
- **Verify:** run `uv run python scripts/generate_targets.py --all`,
  `uv run python scripts/validate_targets.py`, and
  `uv run python scripts/check_runtime.py`.

### 4. Prove deterministic generation and end-to-end lifecycle behavior

- **Owner:** `verifier`.
- **Files:** no hand edits to `dist/`; inspect generated output only.
- **Required Skills:** `.claude/skills/run-tests/SKILL.md`.
- Run generation and the validator's independent temporary-output comparison.
  It must compare bytes/modes for the generated lifecycle scripts/configs, not
  merely report that two generation commands exited zero.
- Exercise real state flow with a bare remote:
  1. checkpoint local state;
  2. Stop wrapper records/checks/checkpoints/publishes in order;
  3. duplicate UserPromptSubmit publication is a no-op;
  4. Codex SessionEnd path performs no remote Trace2 command;
  5. Claude StopFailure path performs no remote Trace2 command;
  6. Claude SessionEnd publishes a pending checkpoint and preserves it on a
     simulated remote failure;
  7. `status` reports the remaining ahead/dirty/error state without network.
- Re-run the existing two-writer divergence, union-log, same-file conflict,
  migration, local-only, installer, and hook-gate regressions.
- Run `scripts/check_runtime.py`; Semble/context-mode remain optional warnings,
  not new runtime requirements.
- **Verify:** run the first nine commands in this plan's Verification section;
  `validate_targets.py` must report its deterministic temp-tree comparison as
  part of a clean result.

### 5. Final review, score, closeout, and handoff

- **Owner:** `reviewer`, then `verifier`, then `orchestrator`.
- **Required Skills:** `.claude/skills/code-review/SKILL.md`,
  `.claude/skills/ponytail-review/SKILL.md`,
  `.claude/skills/run-tests/SKILL.md`, `.claude/skills/learn/SKILL.md`, and
  `.claude/skills/commit/SKILL.md`.
- **Review Profiles:**
  - `.claude/review-profiles/code.md`
  - `.claude/review-profiles/architecture.md`
  - `.claude/review-profiles/security.md`
  - `.claude/review-profiles/tests.md`
  - `.claude/review-profiles/config.md`
  - `.claude/review-profiles/ponytail.md`
  - `.claude/review-profiles/documentation.md`
- Review the full branch diff against `dev`, with special attention to trust
  boundary wording, timeout correctness, hook JSON purity, publish idempotency,
  state preservation under overlap/failure, secret-safe status output, and
  generator/source-of-truth discipline.
- Resolve every surviving finding; rerun all gates after the final code/docs
  change. Stage explicit files before findings/score so the content hash covers
  all new wrapper/test/doc files.
- Persist zero-critical/zero-Ponytail findings, score >= 90, LEARN or explicit
  no-lessons evidence, completed session log, and complete statuses for all
  plans. Commit Phase D once. Push/open a PR only if the user explicitly asks
  and the push gate also has zero major findings.
- **Verify:** run the entire Verification section after the last code/docs
  change, then inspect persisted score/findings metadata and all completed
  phase logs before `git commit`.

## Verification

```bash
bash -n shared/hooks/scripts/state-sync.sh
bash -n shared/hooks/scripts/codex-stop.sh
bash -n shared/hooks/scripts/claude-stop.sh
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy scripts/ tests/ --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python .claude/scripts/quality_score.py scripts/ --phase 2026-08-01_phase-D-install-trust-and-closeout --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

## Acceptance Criteria

- Direct installer and batch updater both give accurate Codex VS Code
  hash/content trust guidance in default, local-only, and dry-run workflows.
- No code auto-trusts hooks or modifies user-level Codex trust state.
- All generated lifecycle commands, handler counts, timeouts, executable bits,
  output contracts, and operation semantics are behaviorally validated.
- Full existing state-sync/installer/hook-gate coverage remains green.
- Independent temp generation is byte-identical to `dist/multi-agent/`.
- Living docs/policy agree and provide a usable status/error recovery path.
- All phase quality/review/closeout gates pass.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved, including zero surviving Ponytail findings
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated before persisted findings/score
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] One atomic Phase D commit created
- [ ] Big plan marked complete only after all four phase commits exist
