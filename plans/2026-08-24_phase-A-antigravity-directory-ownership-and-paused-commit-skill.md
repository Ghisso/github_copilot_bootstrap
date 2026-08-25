---
name: 2026-08-24_phase-A-antigravity-directory-ownership-and-paused-commit-skill
type: small-plan
parent_plan: antigravity-directory-ownership-and-paused-commit-skill
phase_index: 0
status: in-progress
closeout_session_log:
---

# Phase A: Antigravity directory ownership and paused commit skill

## Scope

Complete both approved fixes in one control-plane phase. Update the four stale
canonical skills and make their lifecycle/installer claims structurally
validated. Replace file-granular Antigravity ownership with one safe,
directory-level `.agents` root adapter that is ignored, mirrored, restored, and
refreshed like `.codex`.

The migration boundary is data-loss sensitive. The installer must inspect an
existing `.agents` tree before any write, accept only content proved to be from
the bootstrap, and stop with actionable repository-relative paths for anything
unknown or modified. Do not trade that check away for a smaller diff.

This is intentionally the only phase. Do not ask a planner to split it. If the
workflow mechanically requires PLAN delegation after approval, use a
confirmation-only planner pass against this file.

## Pre-flight and authority

Before editing:

1. Start on a clean `dev`, fetch/update from `origin/dev`, and rebase or create
   `antigravity-directory-ownership-and-paused-commit-skill_implementation`
   from that current base according to the live branch gate.
2. Regenerate once and run the focused installer/restore/validator baseline.
3. Inspect the current implementations and callers of:
   - `ROOT_ADAPTER_PATHS`, `RESTORABLE_ROOT_PATHS`,
     `active_ignore_patterns()`, `restore_manifest()`, and
     `install_mode_from_manifest()` in `scripts/runtime_ownership.py`;
   - `copy_generated_tree()`, `populate_bootstrap_root()`,
     `ignore_block()`, `merge_gitignore()`, `persisted_install_mode()`, and all
     Antigravity helpers in `scripts/install_bootstrap.py`;
   - `render_antigravity()` in `scripts/generate_targets.py`;
   - the manifest parser and copy loop in
     `shared/hooks/scripts/restore-root-adapters.sh`;
   - `runtime_drift_errors()` in `scripts/check_runtime.py`;
   - `validate_antigravity_manifest_and_skills()`,
     `validate_skills_and_paths()`, `validate_devcontainer_and_installer()`, and
     `validate_determinism()` in `scripts/validate_targets.py`;
   - relevant cases in `tests/test_install_bootstrap.py`,
     `tests/test_state_sync.py`, and `tests/test_validate_targets.py`.
4. Read every `shared/skills/*/SKILL.md` exact lifecycle/commit/PR/install claim.
   Confirm the current evidence for `commit`, `plan-decomposition`,
   `context-status`, and `setup-project`; only add another skill if current
   `dev` proves a specific stale statement.
5. Record any material plan assumption that current `dev` disproves in the
   implementation session log before adapting the design.

Current `dev` wins over function names or line locations in this plan. Preserve
the approved behavior with the smallest adaptation; do not restore older
provider-integration or pre-paused lifecycle code.

## Ownership

### Coder

Own the minimum source diff across ownership constants, installer migration,
root restoration, runtime drift, skill guidance, structural validation, and
focused regressions. The coder must apply Ponytail in full mode, reuse the
existing root-adapter path, and delete obsolete Antigravity-only machinery.

### Verifier

Own focused migration/skill tests first, then full tests, typing, linting,
formatting, generation, target validation, plan validation, runtime checks,
consumer smoke coverage, and deterministic regeneration.

### Reviewer

Run one consolidated two-pass review with these profiles:

- `code`;
- `architecture`;
- `security`;
- `tests`;
- `ponytail`;
- `documentation`.

Review migration path classification and pre-write ordering as data-loss and
trust-boundary concerns. Do not run separate overlapping reviews.

### Documenter

After code review converges, update only lifecycle/installation/ownership prose
made false by the change. Run the required targeted `humanize edit` pass on the
changed human-facing prose. Preserve commands, paths, identifiers, field names,
status literals, code blocks, tables, and test names exactly.

## Required Skills

- `.claude/skills/plan-decomposition/SKILL.md` for the approved one-big/
  one-small-plan lifecycle;
- `.claude/skills/ponytail/SKILL.md` in `full` mode for every implementation
  step;
- `.claude/skills/code-style/SKILL.md`;
- `.claude/skills/testing-patterns/SKILL.md`;
- `.claude/skills/run-tests/SKILL.md`;
- `.claude/skills/documentation/SKILL.md`;
- `.claude/skills/humanize/SKILL.md` in targeted `edit` mode for the documenter;
- `.claude/skills/learn/SKILL.md`;
- the corrected `.claude/skills/commit/SKILL.md` for final closeout.

`create-feature` was inspected during planning but is not an implementation
authority here: this work adds no Hydra config or new application module.

## Steps

- [ ] **1. Reconfirm live ownership and stale-skill evidence**
  - Run the baseline commands in Verification before source edits.
  - Trace every caller of the Antigravity ownership constants and helpers.
  - Capture the exact old consumer evidence shape:
    `.claude/bootstrap-ownership.env`,
    `.claude/antigravity-ownership.env`, and
    `.claude/bootstrap-root/.agents/` when present.
  - Confirm how a legacy `--commit-copilot-surface` choice is retained during
    refresh; migration must not reset that unrelated choice.
  - Audit all canonical `shared/skills/*/SKILL.md` files for exact lifecycle,
    commit, PR, installer, outer-Git, and generated-surface statements.
  - Record evidence-backed findings. Do not edit skills based only on generic
    words such as "commit" or "complete".

- [ ] **2. Make `.agents` a normal directory-level root adapter**
  - Modify `scripts/runtime_ownership.py`.
  - Add `.agents` to `ROOT_ADAPTER_PATHS`, allowing
    `RESTORABLE_ROOT_PATHS`, `bootstrap_root_paths()`,
    `is_root_adapter_path()`, `restore_manifest()`, and
    `render_restore_script()` to use the existing root-adapter contract.
  - Add exactly `.agents/` to `active_ignore_patterns()`.
  - Remove ongoing `ANTIGRAVITY_MANIFEST_KEY`, per-file path predicates,
    renderers, dynamic restore-manifest records, and allowlist parsing after
    extracting only the narrow legacy compatibility read that Step 3 proves is
    needed.
  - Preserve `.context-mode-provenance.secret*`, `.claude/`, `.codex/`, the
    Copilot mode, and every other current ignore/root path unchanged.
  - Do not introduce a generalized owner class, registry, or state-machine
    abstraction.

- [ ] **3. Add a fail-closed pre-write `.agents` takeover check**
  - Modify `scripts/install_bootstrap.py` with one narrowly named helper such
    as `antigravity_takeover_conflicts(source: Path, target: Path) -> tuple[str,
    ...]` and a small validator/reporting wrapper, adapting names to live code.
  - Invoke the guard after source/target root validation and before migration,
    copy, ignore, mirror, nested-state, chmod, Git config, or any other write.
  - Classify existing `.agents` entries from the smallest trustworthy evidence:
    current generated bytes for a fresh/idempotent install; the previous
    `.claude/bootstrap-root/.agents/` snapshot for a directory-owned refresh;
    and strictly validated intersection of the old generated allowlist and old
    ownership manifest for the one-time file-granular migration.
  - Treat an unproved file, a locally modified collision, an unexpected empty
    path, an unsafe symlink, malformed legacy evidence, or an ownership-record
    mismatch as a conflict. Never widen ownership from a filename pattern.
  - Permit deletion/replacement only for content proved to be generated,
    including obsolete generated files recorded by valid prior evidence.
  - On conflict, exit nonzero before writes and print stable, sorted,
    repository-relative paths plus instructions to move or back up the content
    outside `.agents`, remove it only if intended, and rerun the installer.
  - Apply the same read-only check during `--dry-run`; dry-run must not imply a
    takeover would succeed when the real install would stop.
  - Preserve the legacy Copilot install mode while reading the old manifest.
    After a successful install, write only the current directory-level manifest
    and let normal source ownership remove the obsolete generated allowlist.

- [ ] **4. Simplify installer copy, ignore, mirror, and restore paths**
  - Remove `generated_antigravity_paths()`, ongoing
    `persisted_antigravity_paths()`/allowlist plumbing, Antigravity collision
    skipping, dynamic return values, individual ignore entries, and special
    bootstrap-root per-file pruning from `scripts/install_bootstrap.py`.
  - Let `copy_generated_tree()` and `populate_bootstrap_root()` handle
    `.agents` through the same `RESTORABLE_ROOT_PATHS`/`bootstrap_root_paths()`
    logic as `.codex`, after the pre-write guard proves takeover safety.
  - Make `ignore_block()`/`merge_gitignore()` emit one `.agents/` line and
    replace old per-file lines inside the managed block without touching text
    outside its markers.
  - Ensure refresh removes proved-obsolete generated `.agents` files from both
    the live surface and `.claude/bootstrap-root/.agents/`, but stops rather
    than deleting an unproved path.
  - Preserve tracked authoring adapters and current warn-only instructions for
    already tracked generated paths; do not run `git rm --cached` automatically.
  - Modify `shared/hooks/scripts/restore-root-adapters.sh` to accept `.agents`
    only through `BOOTSTRAP_ROOT_PATH=.agents`, then remove the separate
    Antigravity record/allowlist parser and path append branch. Keep its
    canonical-path, traversal, source-link, destination-link, and tracked-file
    protections intact.

- [ ] **5. Stop generating or validating the obsolete Antigravity allowlist**
  - Modify `scripts/generate_targets.py::render_antigravity()` to keep
    generating agents, skills, MCP config, and hooks, but stop creating
    `.claude/antigravity-ownership.env`.
  - Simplify `scripts/check_runtime.py::runtime_drift_errors()` so `.agents`
    parity and its bootstrap-root mirror flow through normal root-adapter
    expected/installed sets. Remove dynamic per-file manifest handling.
  - Simplify
    `scripts/validate_targets.py::validate_antigravity_manifest_and_skills()` to
    retain provider metadata and canonical skill parity checks while rejecting
    any regenerated Antigravity allowlist or per-file ownership records.
  - Extend installer/target integration validation to require one ignored
    `.agents/` directory, one bootstrap-root mirror, a root manifest entry, and
    no per-file ignore/ownership records.
  - Keep generated output derived. Never patch `dist/` directly.

- [ ] **6. Correct and structurally guard the four stale shared skills**
  - Modify `shared/skills/commit/SKILL.md` to distinguish:
    - a normal completion commit, retaining every score/findings/LEARN/
      DOCUMENT/COMPLETED gate;
    - an explicitly user-authorized paused checkpoint, requiring valid pause
      frontmatter/session-log evidence, real outer work, no phase advancement,
      and no final quality claim;
    - push/PR closeout, which requires every phase complete or fully evidenced
      as cancelled, at least one completed phase, and one commit per completed
      phase, while paused remains blocked.
  - Modify `shared/skills/plan-decomposition/SKILL.md` so its frontmatter summary
    covers conditional pause and cancellation evidence, and its closeout
    checklist is explicitly the normal completion-commit gate rather than the
    paused checkpoint path.
  - Modify `shared/skills/context-status/SKILL.md` so status reporting reads the
    live plan frontmatter and reports the valid big-plan vocabulary
    (`planning`, `in-progress`, `complete`, `cancelled`) and small-plan
    vocabulary (`in-progress`, `paused`, `complete`, `cancelled`) instead of
    DRAFT/APPROVED/COMPLETED.
  - Modify `shared/skills/setup-project/SKILL.md` to use
    `scripts/generate_targets.py` plus `scripts/install_bootstrap.py` from the
    bootstrap repository, preserve the installer/nested `ai-state` contract,
    and stage only intended outer-repository files such as `.devcontainer/`,
    `.gitignore`, and project source/config. Remove hand-copy and `git add
    .claude/ .codex/ AGENTS.md CLAUDE.md` instructions.
  - Add a structural helper in `scripts/validate_targets.py` for these four
    contracts. Validate canonical and generated skill text, positive required
    concepts, and narrow forbidden obsolete claims. Do not pin whole paragraphs
    or exact prose.
  - Add mutation tests in `tests/test_validate_targets.py` proving each contract
    fails when paused checkpoint semantics, cancellation-aware PR semantics,
    live status vocabulary, or installer-only setup is removed/replaced with
    its obsolete text.
  - Re-run the all-skills exact audit. Only change additional skills when a
    specific surviving false statement is recorded with file and line evidence.

- [ ] **7. Replace file-granular tests with migration and directory-owner regressions**
  - Update `tests/test_install_bootstrap.py` to cover:
    - fresh install writes `.agents/` once and no individual `.agents` ignores;
    - `.agents` is mirrored under `.claude/bootstrap-root/.agents/` and recorded
      as `BOOTSTRAP_ROOT_PATH=.agents`;
    - a valid legacy generated-only install migrates successfully, preserves
      the Copilot commit mode, removes obsolete allowlist/per-file records, and
      becomes idempotent;
    - an obsolete path proved by legacy evidence or the prior mirror can be
      pruned;
    - an unknown private agent, private skill, modified generated collision,
      unsafe symlink, malformed/mismatched legacy record, and unexpected path
      each fail before any filesystem/Git/nested-state mutation;
    - diagnostics contain sorted repository-relative conflict paths and an
      actionable move/backup/remove-and-rerun message;
    - a later refresh also stops on consumer content added after takeover
      instead of deleting it;
    - dry-run reports the same blocker without writes.
  - Update `tests/test_state_sync.py` to exercise `.agents` through the ordinary
    inert root manifest and bootstrap-root restore path. Retain traversal,
    source-symlink, destination-symlink, and tracked-file protection tests;
    remove tests whose only purpose was the deleted per-file allowlist parser.
  - Update `tests/test_validate_targets.py` for the four skill contract mutation
    cases and directory-level generated/installer invariants.
  - Extend `scripts/validate_targets.py` disposable-consumer scenarios so the
    actual generated installer and generated restore script exercise both the
    safe legacy migration and unknown-content refusal.
  - Prefer the existing fixtures and helper style. Do not create a second
    ownership test framework or whole-file snapshots.

- [ ] **8. Update public lifecycle, install, and ownership documentation**
  - Update `README.md`, including the install-only consumer workflow, generated
    layout, `.gitignore` description, restoration description, Antigravity
    section, and any remaining copy/stage instructions made false by the
    corrected `setup-project` skill.
  - Update `docs/architecture.md`, `docs/target-mapping.md`,
    `docs/runtime-checks.md`, and `docs/smoke-tests.md` where they describe
    `.agents` as a shared/file-granular namespace, the allowlist, per-file
    pruning, individual ignore lines, or non-restorable ownership.
  - Document migration behavior: `.agents` is now bootstrap-owned; an update
    refuses unknown existing content and tells the user how to preserve it
    before retrying.
  - Preserve the distinction between source `shared/`, generated `dist/`,
    installed nested AI state, and outer-repository trackable files.
  - Ensure paused lifecycle prose agrees with the corrected commit skill:
    checkpoint durability is not completion certification and still blocks
    push/PR closeout.
  - After review converges, delegate the documenter and apply targeted
    `humanize edit` only to changed prose.

- [ ] **9. Generate, verify, review, document, and close out once**
  - Run focused tests before full verification.
  - Generate targets, inspect source/generated parity, and run target/runtime/
    plan validation.
  - Run the full repository test, type, lint, and format checks.
  - Confirm deterministic generation through the live
    `validate_determinism()` path and an independent second generation.
  - Run one consolidated reviewer with `code`, `architecture`, `security`,
    `tests`, `ponytail`, and `documentation`; resolve surviving gate findings.
  - Delegate DOCUMENT after code review converges, then rerun affected
    verification if docs or validators changed.
  - Stage every file intended for the phase completion commit before persisting
    final findings and score so their content hash covers final code and docs.
  - Persist findings with all six review profiles and require zero CRITICAL
    findings; require zero MAJOR findings before any later push/PR.
  - Persist a quality score >= 90, run LEARN, and write a normal session log with
    `**Status:** COMPLETED`.
  - Mark this small plan `complete` and create exactly one normal completion
    commit for the phase. Do not create a checkpoint or extra source commit for
    this implementation unless the user later explicitly pauses it.

## Focused test cases

### Skill lifecycle and installer text

- [ ] Canonical and generated `commit` skills describe both completion and
  paused checkpoint commits without weakening completion gates.
- [ ] The commit skill keeps paused phases blocked and describes fully
  evidenced cancellation as PR-eligible without requiring a cancellation
  commit.
- [ ] The plan-decomposition skill names optional pause/cancellation evidence
  and scopes its closeout checklist to normal completion.
- [ ] The context-status skill reports current parsed big/small status values
  and contains no DRAFT/APPROVED vocabulary.
- [ ] The setup-project skill invokes the installer, does not instruct a raw
  `dist/multi-agent` copy, and does not stage ignored generated AI surfaces.
- [ ] Each narrow mutation back to the obsolete claim produces an actionable
  validation failure.
- [ ] The final exact all-skills audit finds no other evidence-backed stale
  lifecycle/commit/PR/installer statement.

### Ownership and ignore output

- [ ] `ROOT_ADAPTER_PATHS` contains `.agents` exactly once.
- [ ] A fresh consumer `.gitignore` managed block contains `.agents/` exactly
  once and contains no `.agents/agents/...` or `.agents/skills/...` entries.
- [ ] `bootstrap-ownership.env` records `BOOTSTRAP_ROOT_PATH=.agents` and no
  `BOOTSTRAP_ANTIGRAVITY_PATH` records.
- [ ] Generation emits no `.claude/antigravity-ownership.env`.
- [ ] `.claude/bootstrap-root/.agents/` byte-matches the installed generated
  surface after normal target substitutions.
- [ ] Refresh and restore use the normal root-adapter path and preserve current
  root manifest/path traversal/link/tracked-file defenses.

### Safe migration

- [ ] A legacy generated-only `.agents` tree migrates and refreshes normally.
- [ ] The legacy Copilot committed/local-only selection survives migration.
- [ ] Proved-obsolete generated files can be deleted from live and mirrored
  trees.
- [ ] Unknown private content is never silently adopted, overwritten, or
  deleted.
- [ ] A locally changed generated-path file is a conflict, not proof of
  ownership.
- [ ] Symlinks and malformed or widened legacy ownership records fail closed.
- [ ] Conflict output names every sorted repository-relative path and tells the
  consumer how to preserve it and retry.
- [ ] The conflict occurs before `.gitignore`, `.claude`, root adapters, nested
  Git, hook configuration, or any other target state changes.
- [ ] `--dry-run` observes the same safety boundary without mutation.
- [ ] A post-takeover refresh rejects newly introduced unknown `.agents`
  content instead of pruning it.

### Regression boundaries

- [ ] `.codex`, `.claude`, Copilot committed/local-only mode, tracked authoring
  adapters, context-mode secret ignore, and nested state sync remain unchanged.
- [ ] Antigravity agents, skill parity, hooks, MCP config, model routing, and
  provider metadata remain generated as before.
- [ ] Existing paused checkpoint gate tests still pass.
- [ ] Existing complete and cancelled commit/push/PR tests still pass.
- [ ] Runtime drift detects missing, stale, or extra owned `.agents` and mirror
  files without consulting the deleted per-file allowlist.
- [ ] Generated output remains byte-deterministic.

## Verification

Run the focused checks first:

```bash
uv sync
uv run pytest tests/test_install_bootstrap.py tests/test_state_sync.py tests/test_validate_targets.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/check_runtime.py
```

Run the complete repository verification after focused checks pass:

```bash
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/check_runtime.py
```

`scripts/validate_targets.py` must execute its independent temporary-output
`validate_determinism()` comparison. Also perform one explicit second
generation snapshot comparison with a validated temporary directory; do not
hand-edit or commit `dist/`:

```bash
DIST_SNAPSHOT_DIR="$(mktemp -d /tmp/bootstrap-dist-check.XXXXXX)"
cp -a dist/. "$DIST_SNAPSHOT_DIR/"
uv run python scripts/generate_targets.py --all
diff -ru "$DIST_SNAPSHOT_DIR" dist
```

After confirming `DIST_SNAPSHOT_DIR` is the `/tmp/bootstrap-dist-check.*`
directory created by this run, remove that temporary directory.

Run a disposable-consumer smoke path if the generated-target validator does not
already cover the actual installed scripts end to end:

```bash
uv run python scripts/install_bootstrap.py <disposable-consumer> --source dist/multi-agent --local-only
uv run python scripts/install_bootstrap.py <disposable-consumer> --source dist/multi-agent --local-only --dry-run
```

Persist final findings and quality evidence only after DOCUMENT and final
staging:

```bash
uv run python .claude/scripts/record_findings.py . \
  --profile code \
  --profile architecture \
  --profile security \
  --profile tests \
  --profile ponytail \
  --profile documentation \
  --phase 2026-08-24_phase-A-antigravity-directory-ownership-and-paused-commit-skill \
  --base-ref dev \
  --findings-json <reviewer-findings.json> \
  --out .claude/quality_reports/findings-<timestamp>.json

uv run python .claude/scripts/quality_score.py . \
  --phase 2026-08-24_phase-A-antigravity-directory-ownership-and-paused-commit-skill \
  --base-ref dev \
  --json \
  --out .claude/quality_reports/score-<timestamp>.json
```

## Risks and fallback paths

### Unknown `.agents` content is deleted during migration

Mitigation: classify the entire tree before the first write, fail closed on
missing/malformed evidence or changed bytes, and assert a complete pre/post tree
snapshot in failure tests. The fallback is user-directed preservation outside
`.agents`, never automatic relocation.

### Legacy evidence is trusted too broadly

Mitigation: accept only strict path-safe records present in both old generated
allowlist and old ownership manifest, or byte identity with a trusted source/
mirror. Never infer generated ownership from `.agents/agents/**` or
`.agents/skills/**` patterns alone.

### A later refresh reintroduces silent pruning

Mitigation: compare against the prior bootstrap-root `.agents` mirror before
every refresh. Add a regression where a private file appears after takeover and
prove the installer stops before deletion.

### Directory ownership weakens restore path safety

Mitigation: reuse the existing `.codex` root-adapter allowlist and canonical
path checks, remove only the redundant Antigravity branch, and retain direct
traversal/symlink/tracked-file tests.

### Removing legacy records loses Copilot mode retention

Mitigation: verify the old combined manifest format and keep the smallest
read-only compatibility parser until one successful rewrite emits the current
root-only manifest. Test both legacy mode values.

### Skill prose drifts again

Mitigation: add concept-level required/forbidden validators and mutation tests
for all four evidence-backed skills across canonical/generated copies. Avoid
exact paragraph pins that would make safe rewording fail.

### Scope expands into a generic lifecycle or ownership system

Mitigation: one root tuple addition, one migration classifier, deletion of
special per-file code, four targeted skill edits, existing validators/tests,
and documentation. Any new framework requires separate user approval.

## Must not change

- Paused checkpoint evidence or no-advance semantics.
- Completion score/findings/LEARN/DOCUMENT/COMPLETED gates.
- Cancellation evidence and mixed complete/cancelled push/PR behavior.
- Branch naming, one-big-plan/one-implementation-branch rules, or human merge
  authority.
- `.claude` nested `ai-state` storage and sync behavior.
- `.codex` directory ownership or Copilot's optional committed surface.
- Antigravity provider behavior beyond ownership/install/restore mechanics.
- Context-mode secret handling or protected-file/dangerous-Git controls.
- Generated files by direct editing.

## Acceptance criteria

- [ ] The exact shared-skill audit is recorded and only evidence-backed stale
  skills are changed.
- [ ] `commit`, `plan-decomposition`, `context-status`, and `setup-project`
  describe the live lifecycle/install model in canonical and generated output.
- [ ] Structural mutation coverage rejects all four obsolete contracts.
- [ ] `.agents` is a directory-level root adapter and one `.agents/` ignore
  entry replaces the generated per-file list.
- [ ] `.agents` is mirrored and restored through
  `.claude/bootstrap-root/.agents/`.
- [ ] No generated Antigravity allowlist or per-file ownership records remain.
- [ ] Ongoing per-file Antigravity ignore/prune/restore machinery is removed.
- [ ] Legacy generated-only consumers migrate without losing Copilot mode.
- [ ] Existing unknown or locally modified `.agents` content blocks before any
  write with actionable paths; no silent deletion or overwrite occurs.
- [ ] Later refreshes retain the same unknown-content safety boundary.
- [ ] Existing `.codex`, `.claude`, Copilot, pause, completion, cancellation,
  runtime safety, and provider-generation behavior remains green.
- [ ] Documentation no longer describes `.agents` as a shared/file-granular
  namespace or consumer install as a raw copy/stage workflow.
- [ ] Focused and full verification pass.
- [ ] Target generation and runtime validation pass.
- [ ] Independent determinism checks pass.
- [ ] One consolidated six-profile control-plane review converges.
- [ ] The documenter runs the targeted `humanize edit` pass.
- [ ] Final findings are persisted and quality score is >= 90.
- [ ] LEARN is completed or a no-lessons marker is recorded.
- [ ] The closeout session log contains `**Status:** COMPLETED`.
- [ ] This small plan is marked `complete`.
- [ ] Exactly one normal completion commit is created for this phase.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record the three pause fields, and create a session log
with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it
does not require final score, findings, LEARN, DOCUMENT, or a completed closeout.
Keep the big plan `in-progress` with the same `current_phase`. On resume, read
the pause log and Git state, restore this plan to `in-progress`, and continue
this same phase without creating another small plan.
