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

Complete both control-plane corrections atomically. Make `.agents/` a single
bootstrap-owned, ignored, mirrored, and restorable provider directory like
`.codex/`; migrate existing generated-only consumers without deleting unknown
content. Correct the four proven stale canonical skills—`commit`,
`plan-decomposition`, `context-status`, and `setup-project`—and add
structural validation so generated copies cannot drift back.

This is intentionally the only phase. The minimum design extends the existing
root-adapter contract and deletes Antigravity-only ownership machinery; it does
not add a generic ownership or lifecycle framework.

## Pre-flight

Before editing:

1. Update clean `dev` from `origin/dev`, then create
   `antigravity-directory-ownership-and-paused-commit-skill_implementation`.
2. Generate targets and run the focused baseline in Verification.
3. Inspect current callers of:
   - `ROOT_ADAPTER_PATHS`, `RESTORABLE_ROOT_PATHS`,
     `active_ignore_patterns()`, `restore_manifest()`, and
     `install_mode_from_manifest()` in `scripts/runtime_ownership.py`;
   - `copy_generated_tree()`, `populate_bootstrap_root()`,
     `merge_gitignore()`, and Antigravity helpers in
     `scripts/install_bootstrap.py`;
   - Antigravity rendering in `scripts/generate_targets.py`;
   - root restoration in `shared/hooks/scripts/restore-root-adapters.sh`;
   - runtime/target validation and relevant installer/state-sync tests.
4. Audit every `shared/skills/*/SKILL.md` lifecycle, commit, PR, installer,
   generated-surface, and outer-Git claim. Change only statements proven false
   on current `dev`.
5. Record any material deviation from this plan in the implementation session
   log. Current `dev` wins over names or line locations below.

## Required skills and ownership

- Coder: `ponytail` in full mode, `code-style`, `testing-patterns`, and
  `refactor`; own source, skill, and focused-test changes.
- Verifier: `run-tests`; own focused then full verification, generation,
  target/runtime/plan checks, consumer smoke tests, and determinism.
- Reviewer: one consolidated two-pass review using `code`, `architecture`,
  `security`, `tests`, `ponytail`, and `documentation`.
- Documenter: `documentation` plus targeted `humanize edit`; update only
  prose made false by the final implementation.
- Closeout: `learn` and the corrected `commit` skill.

Treat takeover classification and pre-write ordering as data-loss and trust
boundaries. Agents share the worktree and must not revert concurrent edits.

## Implementation

- [ ] **1. Reconfirm ownership and stale-skill evidence**
  - Trace legacy evidence in `.claude/bootstrap-ownership.env`,
    `.claude/antigravity-ownership.env`, and
    `.claude/bootstrap-root/.agents/`.
  - Verify how repeat installs retain `--commit-copilot-surface`; the
    migration must not reset that unrelated mode.
  - Record file-and-line evidence for the four known stale skills. Add another
    skill only if the exact audit proves a false current statement.

- [ ] **2. Adopt directory-level `.agents` ownership**
  - In `scripts/runtime_ownership.py`, add `.agents` to
    `ROOT_ADAPTER_PATHS` and add exactly `.agents/` to
    `active_ignore_patterns()`.
  - Reuse normal root-adapter manifest, mirror, and restore behavior for
    `.agents`, including existing containment, symlink, and tracked-file
    protections.
  - Preserve `.context-mode-provenance.secret*`, `.claude/`, `.codex/`,
    Copilot mode handling, and every unrelated root/ignore path.
  - Remove ongoing Antigravity per-file ownership constants, parsers,
    renderers, allowlist records, and predicates once the narrow migration read
    required by Step 3 is isolated.

- [ ] **3. Guard the directory takeover before any write**
  - Add one narrow preflight in `scripts/install_bootstrap.py`, adapting its
    name to live code, that compares an existing `.agents` tree with trusted
    evidence before migration, copy, ignore edits, mirroring, nested-state
    writes, chmod, or Git configuration.
  - Trust only byte-identical current generated content, the prior
    `bootstrap-root/.agents` mirror, or a strictly validated intersection of
    legacy allowlist and ownership records.
  - Reject unknown or modified files, unproved obsolete paths, malformed or
    mismatched legacy evidence, unsafe links, and non-regular entries.
  - Fail with stable sorted repository-relative paths and instructions to move
    or back up the content, remove it only if intended, then rerun. Never move,
    delete, overwrite, or adopt unproved content.
  - Apply the same classification during `--dry-run`. After a successful
    migration, emit only directory-level ownership and remove obsolete
    generated allowlist/per-file records.

- [ ] **4. Simplify install, generation, restore, and runtime paths**
  - Remove Antigravity-specific return values, collision skipping, per-file
    ignore entries, pruning, bootstrap-root copying, and manifest plumbing from
    `scripts/install_bootstrap.py`; use the existing root-adapter path after
    the takeover guard passes.
  - Make managed `.gitignore` refresh replace the old enumerated block with
    one `.agents/` line without changing text outside its markers.
  - Stop generating `.claude/antigravity-ownership.env` while retaining
    Antigravity agents, skills, MCP config, and hooks.
  - Remove the separate `BOOTSTRAP_ANTIGRAVITY_PATH`/allowlist branch from
    `shared/hooks/scripts/restore-root-adapters.sh`; restore `.agents`
    through `BOOTSTRAP_ROOT_PATH=.agents`.
  - Simplify `scripts/check_runtime.py` and
    `scripts/validate_targets.py` to validate directory parity, the
    bootstrap-root mirror, one root manifest record, one ignore entry, and no
    regenerated legacy records.
  - Never edit `dist/` directly.

- [ ] **5. Correct and guard stale skills**
  - `shared/skills/commit/SKILL.md`: document separate normal-completion and
    explicit paused-checkpoint commit paths. Preserve all completion gates;
    require pause evidence and real outer work; forbid phase advancement and
    empty checkpoint commits. State that push/PR needs every phase complete or
    fully evidenced as cancelled, at least one completed phase, and one commit
    per completed phase; paused remains blocked.
  - `shared/skills/plan-decomposition/SKILL.md`: include conditional pause and
    cancellation evidence in the frontmatter summary, and qualify the closeout
    checklist as the normal completion-commit gate.
  - `shared/skills/context-status/SKILL.md`: read actual frontmatter and report
    live big-plan statuses (`planning`, `in-progress`, `complete`,
    `cancelled`) and small-plan statuses (`in-progress`, `paused`,
    `complete`, `cancelled`) instead of obsolete
    `DRAFT/APPROVED/COMPLETED`.
  - `shared/skills/setup-project/SKILL.md`: use target generation plus
    `install_bootstrap.py`; preserve nested `ai-state`; stage only intended
    outer files. Remove hand-copy instructions and staging of `.claude/`,
    `.codex/`, `AGENTS.md`, and `CLAUDE.md`.
  - Add semantic structural checks in `scripts/validate_targets.py` and
    mutation tests in `tests/test_validate_targets.py`. Validate canonical
    and generated copies using required concepts plus narrow forbidden stale
    claims, not whole-paragraph snapshots.

- [ ] **6. Replace file-level tests with migration regressions**
  - Update `tests/test_install_bootstrap.py` for fresh/repeat directory
    ownership, one ignore entry, root manifest/mirror parity, idempotence, and
    removal of legacy outputs.
  - Prove valid generated-only legacy migration preserves Copilot mode and can
    prune only evidence-backed obsolete generated paths.
  - Prove unknown private agents/skills, modified collisions, unsafe links,
    malformed/mismatched evidence, unexpected entries, and consumer content
    added after takeover all stop before any filesystem, Git, or nested-state
    mutation. Verify dry-run gives the same blocker without writes.
  - Update `tests/test_state_sync.py` for ordinary root-manifest restoration;
    retain traversal, source/destination symlink, and tracked-file protections.
  - Extend disposable generated-consumer validation to exercise safe migration,
    refusal, mirror/restore, compact ignore output, and corrected skills.
  - Reuse existing fixtures; do not add another ownership test framework.

- [ ] **7. Document, verify, and close once**
  - Update `README.md`, `docs/architecture.md`,
    `docs/target-mapping.md`, `docs/runtime-checks.md`, and
    `docs/smoke-tests.md` where they describe file-granular `.agents`,
    legacy manifests, individual ignore entries, setup copying/staging, or
    stale checkpoint semantics.
  - Document that `.agents` is bootstrap-owned and migration refuses unknown
    content with preservation instructions.
  - Generate and inspect outputs, run one consolidated review, resolve findings,
    delegate DOCUMENT, then run final verification.
  - Stage the final code/docs before persisting findings and score so their
    content hashes match. Require score >= 90, zero CRITICAL findings for
    commit, and zero MAJOR findings before later push/PR.
  - Run LEARN, write a `**Status:** COMPLETED` session log, mark this plan
    complete, and create exactly one normal completion commit.

## Focused acceptance cases

- Generated and installed commit skills describe both commit paths and retain
  completion/cancellation-aware push semantics.
- The other three stale skills use current plan, installer, nested-state, and
  outer-Git contracts; mutation tests reject every obsolete form.
- Fresh and migrated consumers receive one `.agents/` ignore entry,
  `BOOTSTRAP_ROOT_PATH=.agents`, and a byte-identical bootstrap-root mirror,
  with no legacy allowlist or per-file ownership records.
- Unknown or modified `.agents` content blocks before writes with sorted,
  actionable paths; generated-only migration and repeat refresh are
  deterministic.
- Existing Claude, Codex, Copilot, cancellation, paused checkpoint, completion,
  restore safety, and consumer-state tests remain green.

## Verification

Focused first:

```bash
uv run pytest tests/test_install_bootstrap.py tests/test_state_sync.py tests/test_validate_targets.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/check_runtime.py
```

Then full:

```bash
uv run pytest tests/ -q --tb=short
uv run mypy scripts/ --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/check_runtime.py
```

Run the supported disposable-consumer install/update/restore smoke path,
including `--dry-run` and `--local-only`, without overwriting authoring
files. Verify determinism independently:

```bash
DIST_SNAPSHOT_DIR="$(mktemp -d /tmp/dist-agents-ownership.XXXXXX)"
cp -a dist/. "$DIST_SNAPSHOT_DIR/"
uv run python scripts/generate_targets.py --all
diff -ru "$DIST_SNAPSHOT_DIR" dist
rm -rf "$DIST_SNAPSHOT_DIR"
```

After DOCUMENT, persist findings for all six review profiles and run:

```bash
uv run python .claude/scripts/quality_score.py scripts/ \
  --phase 2026-08-24_phase-A-antigravity-directory-ownership-and-paused-commit-skill \
  --base-ref dev --json \
  --out .claude/quality_reports/score-<timestamp>.json
```

## Risks and constraints

- **Data loss:** takeover guard runs before every write and never infers
  ownership from a path name alone.
- **Legacy trust:** compatibility reads are narrowly validated and removed
  after successful migration; they are not a new runtime contract.
- **Later consumer additions:** refresh still refuses unexpected content rather
  than silently pruning it.
- **Scope growth:** reuse root-adapter helpers and delete special cases; no new
  registry, framework, provider mode, or state machine.
- Do not alter `.claude/` nested-state semantics, `.codex/`, Copilot mode,
  paused/completion/cancellation gates, protected-file behavior, or generated
  Antigravity content beyond ownership packaging.

## Closeout checklist

- [ ] Focused and full verification pass
- [ ] One consolidated six-profile review passes
- [ ] Documenter completes targeted `humanize edit`
- [ ] Final findings are persisted; score >= 90
- [ ] LEARN and `**Status:** COMPLETED` closeout are recorded
- [ ] Small plan is `complete`
- [ ] Exactly one normal completion commit is created

## Pause checkpoint

Use only after explicit user intent to stop and resume later. Preserve this same
phase, add valid pause evidence and a `**Status:** PAUSED` log, commit only
real outer work, and do not advance the big plan. Resume this plan rather than
creating another phase.
