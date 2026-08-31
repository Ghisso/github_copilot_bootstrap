---
name: 2026-08-30_phase-A-active-consumer-upgrade-safety-hardening
type: small-plan
parent_plan: active-consumer-upgrade-safety-hardening
phase_index: 0
status: complete
closeout_session_log: .claude/session_logs/2026-08-30_active-consumer-upgrade-safety-hardening.md
---
# Small Plan: 2026-08-30_phase-A-active-consumer-upgrade-safety-hardening

## Scope

Close the three post-completion MAJOR consumer-upgrade/provenance findings:

1. bind owned live root adapters to provenance;
2. require a complete, unchanged current small plan in both terminal provenance paths;
3. add one offline schema-v2 -> schema-v3/current active-plan upgrade lifecycle regression.

Also correct or prevent parent-plan phase-list drift discovered in the completed
predecessor plan. Keep the existing verification/provenance architecture. Use
Ponytail `full`.

## Pre-Flight

1. Continue from the current `consumer-verification-provenance-hardening_implementation`
   line unless live workflow requires the named corrective branch.
2. Record exact outer and nested `.claude` HEAD/state.
3. Re-run the clean generated-consumer lifecycle and all existing
   provenance/terminal negatives before edits.
4. Inspect:
   - `control_plane_provenance()` and matching helpers;
   - `nested_runtime_paths()` or equivalent;
   - runtime/ownership manifest helpers;
   - `terminal_control_plane_provenance_matches()`;
   - both terminal-transition helper paths;
   - big/small-plan parsers;
   - installer `--local-only` update/state-sync path;
   - generated-consumer lifecycle fixture;
   - historical/schema-v2 fixtures if any.
5. Treat the ownership manifest and current plan-state vocabulary as authoritative.
6. Preserve provider, Context Mode, reporting, pause, score, findings, bypass,
   branch, and gate behavior.

## Steps

- [ ] **1. Bind live root adapters through the existing ownership manifest.**
  - Owner: `coder`
  - Reuse the manifest/runtime-ownership source already used by install/update/
    prune/runtime validation.
  - Do not create another adapter list.
  - Resolve every bootstrap-owned live root adapter for the current target.
  - Bind directly by content hash, or prove live type/symlink/content equals the
    canonical `.claude/bootstrap-root` mirror and bind that equality into the
    canonical runtime fingerprint.
  - Include mode only where current cross-platform ownership already treats it
    as authoritative.
  - Missing/unreadable/wrong-type/unexpected-symlink/mismatched required adapter
    -> unavailable provenance / deny.
  - Preserve consumer-owned mutable state and intentional authoring-owned adapters.
  - Keep cost bounded by the finite manifest.

- [ ] **2. Add live-adapter falsifier tests.**
  - Owner: `coder`
  - Assert every owned live adapter matches its bound generated/mirror state.
  - Mutate each installed family represented by the manifest, including current
    equivalents of `.codex/hooks.json`, `.agents/`, `.mcp.json`,
    `.vscode/mcp.json`, `AGENTS.md`, and `CLAUDE.md`.
  - Each relevant mutation must stale provenance.
  - Missing required adapter -> deny.
  - File-type mismatch -> deny.
  - Symlink mismatch -> deny where supported.
  - Consumer-owned mutable state remains excluded.
  - Generated source/mirror/live runtime/manifest parity stays validated.

- [ ] **3. Make terminal provenance require a complete unchanged current small plan.**
  - Owner: `coder`
  - Add one shared terminal current-small-plan validator used by both terminal paths.
  - Require:
    - recorded `current_phase` exists in big-plan `phases:`;
    - authoritative recorded small plan is `status: complete`;
    - current index/worktree small-plan bytes match authoritative recorded bytes;
    - no checkpointed mutation exists after receipt authority;
    - later phases satisfy current cancellation rules;
    - big-plan mutation is exactly the automatic terminal transition;
    - no other relevant nested plan/runtime/index/dirty mutation exists.
  - Do not rely on Bash gates to supply these semantics.

- [ ] **4. Add terminal small-plan positive/negative matrix.**
  - Owner: `coder`
  - Exercise both immediate/unstaged and clean-checkpoint terminal paths.
  - `complete` -> allow when all invariants hold.
  - `in-progress`, `paused`, `cancelled` current phase -> deny.
  - missing/unreadable/malformed small plan -> deny.
  - index-only/worktree/checkpointed post-receipt small-plan mutation -> deny.
  - exact terminal transition + complete unchanged current phase + valid later
    cancellations -> allow.
  - Existing arbitrary plan/runtime/receipt/index/dirty negatives remain green.

- [ ] **5. Add one offline old-to-new active-plan upgrade integration fixture.**
  - Owner: `coder`
  - Extend current installer/generated-consumer integration coverage.
  - Use a minimal checked-in legacy schema-v2 fixture or existing local historical
    bytes. Do not fetch/clone historical commits during the test.
  - Pin fixture bytes to explicit version/hash.
  - Initial state includes outer implementation branch, application changes,
    nested `.claude` Git repo, in-progress big plan, active small plan, dirty
    small-plan edit, session log, memory, and schema-v2 phase/closeout evidence.
  - Run supported generated installer/update with `--local-only`.
  - Assert required before/after preservation of active plan/user/evidence bytes.
  - Assert nested `.claude` has valid HEAD and clean worktree after checkpointing.
  - Assert installed verifier is current schema.
  - Assert old schema-v2 receipts remain present but fail closed.

- [ ] **6. Continue the upgrade fixture through the real current lifecycle.**
  - Owner: `coder`
  - Checkpoint governing active-plan state before authoritative verification as
    required by current provenance.
  - Run installed `verify fast` and `verify phase --persist`.
  - Create deterministic score/findings/docs applicability/LEARN/COMPLETED-session
    evidence using repository-supported formats/helpers.
  - Run installed `verify closeout --persist`.
  - Exercise native commit gate.
  - Complete plan through the real post-commit terminal transition.
  - Exercise native pre-push in immediate terminal and clean-checkpoint states.
  - Assert live-adapter, active-plan, runtime, receipt, index-only, dirty-state,
    referenced-artifact, and post-closeout outer mutations remain denied.
  - No LLM calls.

- [ ] **7. Prove `--local-only` remains network-free.**
  - Owner: `coder`
  - Assert tested refresh runs no `fetch`, `ls-remote`, `pull`, `merge`, or `push`.
  - Reuse current installer command-capture/mock infrastructure.
  - Do not add network-dependent coverage.

- [ ] **8. Fix or prevent big-plan frontmatter/body phase-list drift.**
  - Owner: `coder`
  - Correct the completed predecessor narrative only if repository policy permits
    historical body correction without falsifying evidence/history.
  - Prefer prevention: if frontmatter is authoritative, validation should reject
    contradictory duplicated body phase inventories, or templates/docs should
    avoid duplicating derived phase-count language.
  - No heavy Markdown parser/second plan parser.

- [ ] **9. Document active-consumer upgrade compatibility.**
  - Owner: `documenter`
  - State:
    1. old schema-v2 receipts are preserved but cannot be reused;
    2. use supported `--local-only` refresh;
    3. require nested `.claude` valid HEAD + clean worktree before verification;
    4. regenerate fast/phase evidence with installed current verifier;
    5. regenerate score/findings/docs/LEARN/session closeout evidence;
    6. run `verify closeout`;
    7. commit/push only after native gates pass.
  - Governing plan/runtime change after phase verification requires rerun;
    excluded evidence-only checkpoints should not stale it.
  - Apply mandatory `humanize` edit self-check.

- [ ] **10. Full verification and consolidated review.**
  - Owner: `reviewer`
  - Profiles: `code`, `architecture`, `security`, `tests`, `documentation`, `ponytail`.
  - Challenge omitted live adapters, unbounded discovery, platform-fragile mode
    semantics, Bash-only small-plan completeness, differing terminal paths,
    drifting legacy fixture, fake upgrade path, schema-v2 authorization,
    local-only remote Git, and misleading historical plan rewriting.
  - Run Ponytail last.

## Expected Source Surfaces

```text
shared/scripts/verify.py
shared/scripts/<provenance helpers>
shared/hooks/scripts/<receipt/gate helpers>
shared/hooks/scripts/enforce-commit-gate.sh
shared/hooks/scripts/enforce-pr-gate.sh
shared/hooks/git-hooks/pre-push
scripts/runtime_ownership.py
scripts/install_bootstrap.py
scripts/generate_targets.py
scripts/validate_targets.py
scripts/check_runtime.py
scripts/validate_plan_frontmatter.py   # only if appropriate
tests/test_install_bootstrap.py
tests/test_hook_gates.py
tests/<provenance/generated-consumer tests>
tests/fixtures/<minimal legacy schema-v2 fixture>  # if needed
README.md / upgrade/gate docs
```

Never hand-edit generated `dist/`.

## Verification

Run focused live-adapter, terminal, and upgrade tests first, then:

```bash
uv run pytest tests/ -q --tb=short
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

Run the committed old-to-new active-plan upgrade integration independently.

## Acceptance Criteria

- [ ] Every required owned live root adapter is bound through the existing manifest.
- [ ] No live adapter can differ while provenance still matches.
- [ ] Missing/type/symlink/content mismatch fails closed.
- [ ] Consumer-owned state remains excluded.
- [ ] Terminal provenance requires complete unchanged current small plan.
- [ ] Both terminal paths share identical small-plan semantics.
- [ ] Offline active-plan upgrade preserves required state/evidence.
- [ ] Old schema-v2 evidence is preserved but cannot authorize current gates.
- [ ] Regenerated current evidence reaches native commit/pre-push allow.
- [ ] `--local-only` runs no remote Git command.
- [ ] Arbitrary live-adapter/plan/runtime/receipt/index/dirty mutations deny.
- [ ] Parent-plan phase inventory cannot remain silently contradictory.
- [ ] Full generation/install/runtime/state-sync/determinism coverage passes.
- [ ] Zero CRITICAL findings.
- [ ] Zero MAJOR findings.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted
- [ ] Documentation updated
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log is COMPLETED

## Pause Checkpoint

Use only after explicit user request. Preserve the current paused checkpoint
commit and durable backup-push path. This plan must not change that behavior.
