---
name: 2026-09-19_phase-A-openwiki-runtime-and-safety-boundary
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 1
status: complete
resumed_at: 2026-09-19T16:55:00Z
prior_pause_session_log: .claude/session_logs/2026-09-19_openwiki-phase-A-runtime-and-safety.md
closeout_session_log: .claude/session_logs/2026-09-19_openwiki-phase-A-runtime-and-safety.md
---
# Small Plan: 2026-09-19_phase-A-openwiki-runtime-and-safety-boundary

## Scope

Add OpenWiki as a pinned optional runtime capability and isolate it behind one bootstrap-owned
runner. This phase does not change planner or documentation semantics. Its job is to make
OpenWiki execution safe enough that later phases can depend on it without giving the upstream
CLI ownership of bootstrap root adapters, workflow files, provider credentials, telemetry
choices, or deterministic verification.

Verified upstream constraints this phase contains: every code-mode run rewrites a managed block
in root `AGENTS.md` and `CLAUDE.md` with no opt-out; `--init` scaffolds a scheduled workflow;
telemetry is on unless `OPENWIKI_TELEMETRY_DISABLED=1` is set; `openwiki/.run.json` is
resumable state that must stay on disk after a failure but must never enter Git.

## Steps

### Step A1 — Pin the runtime dependency and persist user configuration

- [x] **Owner:** `coder`
- **Target files:**
  - modify `shared/devcontainer/Dockerfile`
  - modify `shared/devcontainer/devcontainer.json`
  - modify `scripts/validate_targets.py` (`validate_devcontainer_and_installer`, next to the
    existing `context-mode` pin assertion)
  - modify `README.md` (devcontainer bullet) and `docs/architecture.md` (devcontainer bullet)
- **Required Skills:**
  - `shared/skills/create-feature/SKILL.md`
  - `shared/skills/add-dependency/SKILL.md`
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Behavior:**
  - Install `openwiki@0.5.2 mermaid@11.16.0 jsdom@29.1.1` globally in the Dockerfile, in
    the same `npm install -g` step pattern as the pinned `context-mode`. `mermaid` and `jsdom`
    are OpenWiki's optional peer dependencies; installing them replaces its lightweight
    Mermaid validator with the authoritative one.
  - Keep the existing pinned `context-mode` installation.
  - Ensure the Node runtime satisfies OpenWiki's `>=22.22.0` engine requirement. The current
    `node:22-bookworm-slim` stage ships 22.23.2. Prefer a deterministic Node tag if the
    Dockerfile permits this cleanly; otherwise record the floating-tag risk.
  - Add a bind mount `source=${localEnv:HOME}/.openwiki,target=/home/vscode/.openwiki,type=bind,consistency=cached`
    to `devcontainer.json` `mounts`, following the Hugging Face cache mount pattern.
  - Do not add any provider API key to `containerEnv`. OpenWiki owns its provider matrix
    through the mounted config directory.
  - Document in the README and architecture devcontainer bullets that the host `~/.openwiki`
    directory must exist before the first container build. Docker creates a missing bind
    source as root-owned, which the `vscode` user cannot write to. A non-fatal warning in
    `post-start.sh` when `~/.openwiki` is not writable is acceptable if it fits the existing
    warning pattern; do not make it fatal.
  - Do not authenticate OpenWiki or select a provider while building the image.
  - Do not install OpenWiki host integrations during bootstrap image creation.
- **Acceptance criteria:**
  - `validate_targets.py` asserts the exact pinned `openwiki`, `mermaid`, and `jsdom`
    versions in the Dockerfile, and asserts the `~/.openwiki` mount in `devcontainer.json`,
    using one module-level pinned-version constant per package.
  - `node --version` satisfies the pinned OpenWiki engine.
  - `openwiki --version` reports `0.5.2` in a built runtime.
  - No credential material is baked into an image or repository file.
- **Verification:**
  - `uv run python scripts/validate_targets.py`;
  - when a devcontainer build environment is available, run one smoke check for Node and
    OpenWiki versions;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step A2 — Add the bootstrap-owned OpenWiki runner

- [x] **Owner:** `coder`
- **Target files:**
  - create `shared/scripts/openwiki_refresh.py`
  - create focused runner tests under `tests/test_openwiki_refresh.py`
- **Required Skills:**
  - `shared/skills/create-feature/SKILL.md`
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Public contract:**
  - installed path: `.claude/scripts/openwiki_refresh.py`
  - default repository root: current outer Git repository
  - machine-readable JSON result plus concise text output, matching current script conventions
  - support `--require-enabled`
  - OpenWiki-enabled means `openwiki/INSTRUCTIONS.md` exists
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
  3. Child environment:
     - copy the current environment;
     - set `OPENWIKI_TELEMETRY_DISABLED=1` only when the user has not already set that
       variable (setdefault semantics), so an explicit user choice wins over the bootstrap
       default;
     - never add provider credentials.
  4. Protect bootstrap-owned surfaces:
     - snapshot `AGENTS.md` and `CLAUDE.md` as raw working-tree bytes, including the
       distinction between absent and present files;
     - snapshot `.github/workflows/openwiki-update.yml` if present and record absence if not;
     - do not broaden this into a generic repository rollback mechanism.
     - Rationale to keep in the module docstring: `restore-root-adapters.sh` restores the
       canonical mirrored adapters from nested state; this runner must preserve the exact
       pre-run bytes, including legitimate uncommitted edits, and must work before any mirror
       exists. The two are not duplicates.
  5. Invoke OpenWiki:
     - argument-vector subprocess execution, never `shell=True`;
     - exactly `openwiki code --update --print`;
     - never `--init`;
     - inherit provider selection/authentication from the user's OpenWiki config directory;
     - never copy provider credentials into command arguments, logs, plans, or AI-state.
  6. Cleanup in `finally`:
     - restore `AGENTS.md` and `CLAUDE.md` exactly to their pre-run bytes, deleting a file only
       when it was absent before the run and created by OpenWiki;
     - prove any pre-existing `.github/workflows/openwiki-update.yml` is byte-identical and
       prove an absent workflow was not created;
     - never remove `openwiki/.run.json` or other OpenWiki-owned recovery artifacts.
  7. Mutation boundary:
     - compare pre/post outer Git status after protected-file restoration;
     - allow newly caused changes only below `openwiki/**`;
     - fail closed and report any new out-of-scope path;
     - never revert unrelated pre-existing user changes.
  8. Exit/result:
     - propagate OpenWiki failure as runner failure after protected surfaces are restored;
     - return enough structured evidence for a session log without exposing secrets.
- **Must not:**
  - be called from `verify.py`, hooks, installer, state-sync, or post-commit;
  - create a scheduled workflow;
  - install a host-specific OpenWiki integration;
  - modify `.claude/MEMORY.md`, plans, session logs, or policy;
  - run more than one OpenWiki process concurrently;
  - implement a rebaseline or `--init` path (the OpenWiki skill documents manual rebaseline
    in Phase B).
- **Verification:**
  - unit tests with a fake `openwiki` executable;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step A3 — Install the runner and ignore resumable run state

- [x] **Owner:** `coder`
- **Target files:**
  - modify `scripts/generate_targets.py`
  - modify `scripts/install_bootstrap.py` (`ignore_block`)
  - modify `scripts/validate_targets.py`
  - modify generator/installer tests as needed
  - generated `dist/multi-agent/` is verification output only and must not become an
    authoring source
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Behavior:**
  - Extend the existing canonical script-copy mapping so
    `shared/scripts/openwiki_refresh.py` is installed as
    `.claude/scripts/openwiki_refresh.py`, next to `verify.py` and `record_findings.py`.
  - Add `openwiki/.run.json` to the installer-managed
    `# BEGIN multi-agent bootstrap generated/private AI content` ignore block so every
    consumer, and this repository through self-install, ignores it. Resume still works because
    the file stays on disk.
  - Assert the new ignore entry in `validate_targets.py` where the block's other entries are
    checked.
  - Do not special-case one target; `.claude/` remains the canonical installed runtime basis.
- **Acceptance criteria:**
  - regeneration installs the runner exactly once;
  - generated-target validation detects drift;
  - an existing consumer `.gitignore` block is refreshed in place with the new entry;
  - no generated copy is hand-edited.
- **Verification:**
  - `uv run python scripts/generate_targets.py --all`
  - `uv run python scripts/validate_targets.py`
  - focused generator/installer tests
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step A4 — Cover destructive and failure cases deterministically

- [x] **Owner:** `coder`
- **Target files:**
  - extend `tests/test_openwiki_refresh.py`
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Test scenarios:**
  - disabled repo is a true no-op;
  - `--require-enabled` fails when the marker is absent;
  - successful fake update writes only `openwiki/**`;
  - upstream-style edits to existing `AGENTS.md` / `CLAUDE.md` are restored byte-for-byte,
    including a pre-run file with uncommitted local edits;
  - upstream-created root adapter is removed when it did not exist pre-run;
  - an existing OpenWiki workflow stays byte-identical;
  - creation of an unexpected workflow is detected and fails;
  - subprocess non-zero still restores protected surfaces;
  - failed run leaves `openwiki/.run.json` and partial OpenWiki state available for retry;
  - a new out-of-scope mutation is reported and causes failure;
  - pre-existing dirty paths are not reverted or falsely attributed to OpenWiki;
  - command execution uses an argv list and no shell interpolation;
  - child environment carries `OPENWIKI_TELEMETRY_DISABLED=1` by default and keeps a
    user-set value (for example `0`) unchanged;
  - structured output contains no environment/provider secret values.
- **Acceptance criteria:**
  - tests do not invoke a real provider or model;
  - test failures show the exact path/invariant that broke.
- **Verification:**
  - `uv run pytest tests/test_openwiki_refresh.py -q --tb=short`;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step A5 — High-risk review and phase closeout

- [x] **Owner:** `reviewer`
- **Target files:** scoped Phase A diff
- **Required Skills:** none beyond reviewer-owned profile guidance
- **Review Profiles:**
  - `code`
  - `architecture`
  - `security`
  - `tests`
  - `ponytail`
- **Review focus:**
  - subprocess/credential safety and telemetry default;
  - failure restoration cannot delete consumer-owned content;
  - Git dirty-state delta handling does not revert unrelated changes;
  - upstream behavior is isolated to one wrapper;
  - no model/network call has leaked into deterministic verification;
  - dependency/version pinning is explicit and asserted by the validator;
  - the bind mount forwards no credential and the host-directory prerequisite is documented.
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

- [x] Documentation updated (devcontainer prerequisite) or explicitly skipped as pure-internal — README.md and docs/architecture.md carry the devcontainer prerequisite and pins from the checkpoint commit; this session changed internal runner logic only, so no public interface moved
- [x] LEARN entries saved or no-lessons marker recorded — five entries in `.claude/MEMORY.md`
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason — one surviving MINOR (`_run()` length), accepted with reason
- [x] Review findings resolved and persisted with branch/phase metadata — 0 critical, 0 major, 1 minor
- [x] Verification passed (`verify phase` then `verify closeout` PASS)
- [x] No real provider/model request was needed to prove Phase A correctness
- [x] Root-adapter and workflow restoration tests cover both success and failure paths
- [x] `openwiki/.run.json` is in the installer-managed ignore block and asserted by the validator

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
