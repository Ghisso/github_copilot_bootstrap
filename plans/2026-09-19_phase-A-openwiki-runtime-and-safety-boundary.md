---
name: 2026-09-19_phase-A-openwiki-runtime-and-safety-boundary
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 1
status: planned
closeout_session_log:
---
# Small Plan: 2026-09-19_phase-A-openwiki-runtime-and-safety-boundary

## Scope

Add OpenWiki as a pinned optional runtime capability and isolate it behind one bootstrap-owned
runner. This phase does not change planner/documentation semantics yet. Its job is to make
OpenWiki execution safe enough that later phases can depend on it without giving the upstream
CLI ownership of bootstrap root adapters, workflow files, provider credentials, or deterministic
verification.

Current upstream behavior is a known compatibility constraint: code mode writes managed blocks
to root `AGENTS.md` and `CLAUDE.md`. The runner must contain that behavior rather than teaching
the bootstrap to accept competing root-file ownership.

## Steps

### Step A1 — Pin and verify the runtime dependency

- [ ] **Owner:** `coder`
- **Target files:**
  - modify `shared/devcontainer/Dockerfile`
  - modify dependency/runtime tests that already validate devcontainer tool pins; create a
    focused test only if no suitable test exists
- **Required Skills:**
  - `shared/skills/create-feature/SKILL.md`
  - `shared/skills/add-dependency/SKILL.md`
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Behavior:**
  - Pin the exact OpenWiki version verified during planning (`openwiki@0.5.2`) rather than
    installing a floating latest version.
  - Keep the existing pinned `context-mode` installation.
  - Ensure the Node runtime used by the devcontainer satisfies OpenWiki's documented
    `>=22.22.0` engine requirement. Prefer a deterministic Node image/tag rather than relying
    on an unbounded `node:22` tag if the existing Dockerfile permits this cleanly.
  - Do not authenticate OpenWiki or select a provider while building the image.
  - Do not install OpenWiki host integrations during bootstrap image creation.
- **Acceptance criteria:**
  - Dockerfile construction is reproducible.
  - `node --version` satisfies the pinned OpenWiki engine.
  - `openwiki --version` reports the pinned package version in a built runtime.
  - No credential material is baked into an image or repository file.
- **Verification:**
  - use the repository's existing Dockerfile/static dependency tests;
  - when a devcontainer build environment is available, run one smoke check for Node and
    OpenWiki versions;
  - run `uv run python .claude/scripts/verify.py fast --format json`.

### Step A2 — Add the bootstrap-owned OpenWiki runner

- [ ] **Owner:** `coder`
- **Target files:**
  - create `shared/scripts/openwiki_refresh.py`
  - modify `scripts/generate_targets.py`
  - create/modify focused runner tests under `tests/`
- **Required Skills:**
  - `shared/skills/create-feature/SKILL.md`
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Public contract:**
  - installed path: `.claude/scripts/openwiki_refresh.py`
  - default repository root: current outer Git repository
  - support a machine-readable JSON result plus concise text output if that matches current
    script conventions
  - support `--require-enabled`
  - define OpenWiki-enabled as presence of `openwiki/INSTRUCTIONS.md`
- **Required behavior:**
  1. When not enabled:
     - normal invocation exits successfully with an explicit `not_enabled` result and performs
       no mutation;
     - `--require-enabled` exits non-zero with an actionable message.
  2. Preflight:
     - require a Git repository root;
     - require `node` and `openwiki` and report detected versions;
     - do not probe or print provider secrets;
     - record pre-run outer Git status so pre-existing user changes can be distinguished from
       new changes caused by OpenWiki.
  3. Protect bootstrap-owned surfaces:
     - snapshot `AGENTS.md` and `CLAUDE.md` as raw bytes, including the distinction between
       absent and present files;
     - snapshot `.github/workflows/openwiki-update.yml` if present and record absence if not;
     - do not broaden this into a generic repository rollback mechanism.
  4. Invoke OpenWiki:
     - use argument-vector subprocess execution, never `shell=True`;
     - invoke exactly the pinned code-mode update path:
       `openwiki code --update --print`;
     - do not invoke `--init`;
     - inherit provider selection/authentication from the user's OpenWiki environment/config;
     - never copy provider credentials into command arguments, logs, plans, or AI-state.
  5. Cleanup in `finally`:
     - restore `AGENTS.md` and `CLAUDE.md` exactly to their pre-run bytes, deleting a file only
       when it was absent before the run and created by OpenWiki;
     - prove any pre-existing `.github/workflows/openwiki-update.yml` is byte-identical and
       prove an absent workflow was not created;
     - never remove `openwiki/.run.json` or other OpenWiki-owned recovery artifacts after a
       failed run.
  6. Mutation boundary:
     - compare pre/post outer Git status after protected-file restoration;
     - allow newly caused changes only below `openwiki/**`;
     - fail closed and report any new out-of-scope path;
     - never revert unrelated pre-existing user changes.
  7. Exit/result:
     - propagate OpenWiki failure as runner failure after protected surfaces are restored;
     - return enough structured evidence for a lifecycle/session log without exposing secrets.
- **Must not:**
  - call OpenWiki from `verify.py`;
  - create a scheduled workflow;
  - install a host-specific OpenWiki integration;
  - modify `.claude/MEMORY.md`, plans, session logs, or policy itself;
  - run more than one OpenWiki process concurrently.
- **Verification:**
  - unit tests with a fake `openwiki` executable;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step A3 — Generate and validate the installed runner

- [ ] **Owner:** `coder`
- **Target files:**
  - modify `scripts/generate_targets.py`
  - modify generator/runtime validation tests as needed
  - generated `dist/multi-agent/` is verification output only and must not become an
    authoring source
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Behavior:**
  - Extend the existing canonical script-copy mapping so
    `shared/scripts/openwiki_refresh.py` is installed as
    `.claude/scripts/openwiki_refresh.py`.
  - Keep `shared/scripts/verify.py` and `record_findings.py` ownership unchanged.
  - Do not special-case one target; `.claude/` remains the canonical installed runtime basis.
- **Acceptance criteria:**
  - regeneration installs the runner exactly once;
  - generated-target validation detects drift;
  - no generated copy is hand-edited.
- **Verification:**
  - `uv run python scripts/generate_targets.py --all`
  - `uv run python scripts/validate_targets.py`
  - focused generator tests
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step A4 — Cover destructive and failure cases deterministically

- [ ] **Owner:** `coder`
- **Target files:**
  - create or extend `tests/test_openwiki_refresh.py`
  - extend generator/runtime tests only where the behavior belongs there
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Test scenarios:**
  - disabled repo is a true no-op;
  - `--require-enabled` fails when the marker is absent;
  - successful fake update writes only `openwiki/**`;
  - upstream-style edits to existing `AGENTS.md` / `CLAUDE.md` are restored byte-for-byte;
  - upstream-created root adapter is removed when it did not exist pre-run;
  - an existing OpenWiki workflow stays byte-identical;
  - creation of an unexpected workflow is detected and fails;
  - subprocess non-zero still restores protected surfaces;
  - failed run leaves `openwiki/.run.json`/partial OpenWiki state available for retry;
  - a new out-of-scope mutation is reported and causes failure;
  - pre-existing dirty paths are not reverted or falsely attributed to OpenWiki;
  - command execution uses an argv list and no shell interpolation;
  - structured output contains no environment/provider secret values.
- **Acceptance criteria:**
  - tests do not invoke a real provider or model;
  - test failures show the exact path/invariant that broke.
- **Verification:**
  - focused pytest for the runner tests;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step A5 — High-risk review and phase closeout

- [ ] **Owner:** `reviewer`
- **Target files:** scoped Phase A diff
- **Required Skills:** none beyond reviewer-owned profile guidance
- **Review Profiles:**
  - `code`
  - `architecture`
  - `security`
  - `tests`
  - `ponytail`
- **Review focus:**
  - subprocess/credential safety;
  - failure restoration cannot delete consumer-owned content;
  - Git dirty-state delta handling does not revert unrelated changes;
  - upstream behavior is isolated to one wrapper;
  - no model/network call has leaked into deterministic verification;
  - dependency/version pinning is explicit.
- **Acceptance criteria:**
  - CRITICAL/MAJOR findings resolved;
  - surviving MINOR findings have explicit disposition and reason;
  - canonical closeout receipts pass.

## Verification

Use focused checks during implementation. Do not run a real model-backed OpenWiki generation in
this phase.

```bash
uv run pytest tests/test_openwiki_refresh.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json
```

Normal completion then follows the fixed closeout sequence and requires canonical
`verify phase` then `verify closeout` PASS receipts.

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, CLOSEOUT); the order below mirrors it rather than restating it.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
- [ ] No real provider/model request was needed to prove Phase A correctness
- [ ] Root-adapter and workflow restoration tests cover both success and failure paths

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record the required pause fields, and create a session log
with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it
does not require final findings, LEARN, DOCUMENT, or a completed closeout.
After the checkpoint commit, it may be pushed as a durable remote backup when
paused-publication invariants pass. It remains unfinished and blocks PR creation
and final closeout.

Keep the big plan `in-progress` with the same `current_phase`. On resume, read
the pause log and Git state, restore this plan to `in-progress`, and continue
this same phase without creating another small plan.
