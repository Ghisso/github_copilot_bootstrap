---
name: 2026-10-02_phase-B-sidecar-workflow-repair
type: small-plan
parent_plan: sidecar-workflow-repair
phase_index: 2
status: complete
closeout_session_log: .claude/session_logs/2026-10-02_sidecar-workflow-repair.md
---

# Small Plan: Repair the Sidecar Workflow

## Scope

Resolve the seven hands-on review findings, plus finding 8 (planner and
reviewer prompts ask for file saves their tools cannot make), in one phase.
Phase A confirmed the `.ai-bootstrap/` state root; see `## Workflow state
write gate, 2026-10-02` in `docs/sidecar-provider-contract.md`. Keep one
coder responsible for installer, overlay, generator, and regression tests;
their shared state and ownership contracts should change together.

### Required Skills

- `shared/skills/ponytail/SKILL.md` — full mode for every code-writing step
- `shared/skills/code-style/SKILL.md`
- `shared/skills/testing-patterns/SKILL.md`
- `shared/skills/code-review/SKILL.md`
- `shared/skills/documentation/SKILL.md`
- `shared/skills/humanize/SKILL.md`
- `shared/skills/integration-gate-spike/SKILL.md` — native fixture rerun

## Steps

- [x] **1. Refuse recognized legacy full installs before sidecar mutation (finding 2).**
  **Owner:** coder.
  **Files:** modify `scripts/install_bootstrap.py`,
  `tests/test_install_bootstrap.py`, `tests/test_sidecar_uninstall.py`, and
  `tests/test_sidecar_update.py` for the existing batch-routing regressions.
  **Required Skills:** `shared/skills/ponytail/SKILL.md`,
  `shared/skills/code-style/SKILL.md`, `shared/skills/testing-patterns/SKILL.md`.
  Extend `_full_install_evidence(target: Path, allow_self: bool) -> tuple[str, ...]`
  and reuse it in `detect_install_mode` and uninstall refusal. Preserve the
  existing `claude_tracked` guard, including deleted tracked entries,
  symlinks, gitlinks, and staged team content. Define legacy evidence as a
  real, untracked `.claude` directory with either (a) the exact tracked
  `.devcontainer/hf-ai-sync.py` or `.devcontainer/state-sync.sh` path plus
  local bootstrap hooks/scripts, or (b) a local `.claude/scripts/verify.py`
  plus bootstrap-specific hook filenames/content confirmed from historical
  source. Do not use an arbitrary hooks directory as sufficient evidence.
  Verify the chosen signatures against a read-only historical source or
  sanitized fixture of the reported legacy layout before fixing the table
  in tests; record exact signals and counterexamples in docs.
  Modern markers keep their current meaning. Plain mode selects full for
  confirmed legacy evidence; explicit sidecar, dry-run sidecar, and sidecar
  uninstall refuse before changes. Tracked devcontainer paths alone stay
  ambiguous; guidance must explain restoration/full refresh without urging
  sidecar over an untracked legacy `.claude` setup. Mixed evidence refuses
  with backup and inspected recovery advice, not an impossible flag choice.
  **Checks:** real-Git CLI tests for HF-era, pre-manifest full, current full,
  empty/unrelated `.claude`, tracked team `.claude`, devcontainer-only,
  sidecar-only, and mixed evidence. Assert status, index, excludes, manifests,
  and files are unchanged on refusals. Preserve batch continue-on-error.

- [x] **2. Make state backup safe for reuse by migration (finding 4).**
  **Owner:** coder.
  **Files:** modify `scripts/sidecar_overlay.py`,
  `scripts/install_bootstrap.py`, `tests/test_sidecar_workflow_scenario.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md`,
  `shared/skills/code-style/SKILL.md`, `shared/skills/testing-patterns/SKILL.md`.
  Preserve `backup_sidecar_state(target: Path, *, dry_run: bool = False) -> int`.
  Real backups acquire `_acquire_run_lock` before selecting a destination
  and hold it until publication/cleanup finishes. Release handles on all
  paths. Reuse existing Git-directory, symlink, containment, and filesystem
  diagnostics without requiring a manifest for retained state. Copy into
  an exclusively created temporary sibling under the preserved directory,
  then publish the collision-free `state--<timestamp>` name only on success.
  Catch filesystem failures, return a nonzero `ABORT: filesystem error at
  <path>: <reason>` diagnostic, and preserve the source and earlier backups.
  Remove only this operation's partial copy; if cleanup fails, report its
  exact path as incomplete. Never report partial output as a good backup.
  Use one narrow internal copy helper for callers already holding the lock;
  avoid nested lock acquisition or a new backup framework. Dry-run creates
  neither a backup nor a lock file and reports only predictions.
  **Checks:** real lock contention, two backups in one second, copy/rename
  failure injection, lock release, unsafe paths, no-state success, and a
  byte-for-byte dry-run snapshot through the public CLI.

- [x] **3. Relocate state and migrate owned legacy state (finding 1).**
  **Owner:** coder.
  **Files:** modify `scripts/runtime_ownership.py`, `scripts/sidecar_overlay.py`,
  `scripts/generate_targets.py`, `scripts/validate_targets.py`,
  `shared/sidecar/workflow/`, and `shared/agents/*/workflow-prompt.md`.
  Update `tests/test_sidecar_overlay.py`, `tests/test_sidecar_workflow_scenario.py`,
  `tests/test_sidecar_update.py`, `tests/test_sidecar_uninstall.py`, and
  `tests/test_validate_targets.py` where each owns the relevant contract.
  **Required Skills:** `shared/skills/ponytail/SKILL.md`,
  `shared/skills/code-style/SKILL.md`, `shared/skills/testing-patterns/SKILL.md`.
  Change `SIDECAR_STATE_ROOT` to `.ai-bootstrap`; retain an explicit legacy
  constant. Separate desired/generated state from recognized legacy state
  in `_ALL_STATE_ROOTS`, path validation, snapshot gathering, ignore-line
  parsing, filesystem preflight, backup, and uninstall. Keep manifest
  schema-1/2 compatibility and state outside ordinary hash reconciliation.
  Follow the parent plan's migration table. Before any migration writes,
  validate mode, all relevant paths, team ownership, and both state roots.
  A recognized old exclude entry must be present for automatic migration;
  a valid retained-state-only exclude block after uninstall also qualifies.
  Under the existing install lock, establish exclusions for both roots and
  prove the destination ignored, create the complete backup from step 2,
  then perform a no-overwrite directory rename on the same filesystem.
  Recheck the absent destination immediately before mutation. Preserve all
  personal bytes and seed only missing defaults through normal reconciliation.
  Refuse unsafe paths, cross-filesystem moves, unowned legacy folders, and
  two existing roots instead of copying/merging them. Roll back provisional
  exclude changes when failure occurs before the move; after a move, retain
  protection for the new root and report the rerun needed to finish tooling.
  Reuse current pending ownership/convergence machinery rather than creating
  a second journal. A rerun after backup, rename, or reconciliation failure
  must preserve state and finish without duplicate state migration.
  Keep legacy state on skills-only updates and ordinary uninstall; explicit
  purge preserves either recognized root to a backup, and backup recognizes
  both. Neither default uninstall nor switching profiles may delete state.
  Render every workflow state reference to the new root, including skill
  rewrites, agents, templates, rules, instructions, and state READMEs. Full
  consumers keep their own `.claude` state contract; account for the existing
  byte-for-byte copy of `runtime_ownership.py` into the full bundle.
  **Checks:** fresh install, edited legacy memory and extra files, retained
  old state with no manifest, schema-1/2 inputs, destination collision,
  foreign legacy root, tracked state, symlink ancestors/descendants, ignore
  negation, interruption/rerun, both profile switches, backup, uninstall,
  purge, and reinstall. Use real-Git public install/update calls; compare
  user bytes, index, and status at every successful step. The migration dry
  run predicts the real action while its complete filesystem snapshot stays
  unchanged. Assert active generated workflow content has no old state path.

- [x] **4. Correct dry-run output (finding 3).**
  **Owner:** coder.
  **Files:** modify `_print_report`, `_describe_dry_run_actions`, and their
  callers in `scripts/sidecar_overlay.py`; regression tests in
  `tests/test_sidecar_install.py`, `tests/test_sidecar_uninstall.py`, and
  `tests/test_sidecar_workflow_scenario.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Reuse one reporting path or a small explicit dry-run parameter. Print
  prospective counts and `would ...` actions once, plus useful skip/retain
  reasons. Do not emit past-tense removed/deleted/seeded/preserved per-path
  messages in a dry run, including migration and purge reports. Keep real
  run results accurate and name actual preserved destinations.
  **Checks:** profile downgrade, team takeover, seed restoration, migration,
  backup, and purge predictions; assert output and unchanged filesystem.

- [x] **5. Handle missing specialists, caller-saved output, and team precedence (findings 5–8).**
  **Owner:** coder.
  **Files:** modify `shared/sidecar/workflow/instructions.md`,
  `shared/sidecar/workflow/rules/workflow.md`, and
  `shared/agents/{orchestrator,planner,reviewer}/workflow-prompt.md`;
  adjust other workflow-only role prompts if their references assume a
  specialist exists. Update `tests/test_validate_targets.py` and
  `tests/test_sidecar_workflow_scenario.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Copilot's instructions direct the current agent to write plans using
  available templates and review against available profiles. Shared workflow
  guidance delegates only to a role actually exposed in that session;
  otherwise the current agent performs that step, labels self-review
  honestly, and follows team guidance. Do not install missing agents,
  change name precedence, or import the full install's mandatory delegation.
  A skipped template/profile may be supplied by the team; use the available
  artifact subject to team rules, or write a simple plan/review when absent.
  Finding 8: the Claude tools of the planner and reviewer come from the
  shared capabilities in `shared/agents/{planner,reviewer}/agent.yaml`,
  which grant no Write or Edit. Apply the user's caller-saves decision
  (2026-10-02): both return the plan or report text, and the agent that
  asked, or the current agent when no specialist exists, saves it under the
  state root. Align the orchestrator prompt, rules, and Copilot instructions.
  Do not change `agent.yaml` capabilities or add a generator tool override.
  **Checks:** a team `.github/agents/coder.agent.md` suppresses the Claude
  sidecar coder as before; emitted guidance includes the fallback. Add
  tracked and foreign-untracked profile/template collisions, deleted-but-
  tracked entries, dry run, rerun, and uninstall; assert preserved bytes,
  index/status, and skip reasons through real installer entrypoints.
  Beside the `test_render_sidecar_workflow_*` tests in
  `tests/test_validate_targets.py`, assert the rendered planner and reviewer
  return their text with no instruction to save a file themselves, and the
  orchestrator prompt and rules say the caller saves it.

- [x] **6. Regenerate, verify, review, and update public documentation.**
  **Owner:** coder for checks; reviewer for two-pass review; documenter
  after convergence; orchestrator for receipts, closeout, and preparing and
  verifying the native rerun, which the user runs.
  **Files:** `README.md`, `docs/sidecar-provider-contract.md`,
  `docs/target-mapping.md`, relevant runtime docs, and source comments/help
  affected by these contracts. Regenerate both targets; never edit outputs.
  **Required Skills:** `shared/skills/ponytail/SKILL.md`,
  `shared/skills/code-review/SKILL.md`, `shared/skills/documentation/SKILL.md`,
  `shared/skills/humanize/SKILL.md`,
  `shared/skills/integration-gate-spike/SKILL.md`.
  Run focused checks during the steps, then the required commands below.
  If changed runtime source makes this checkout's installed copy stale,
  regenerate and use `uv run python scripts/install_bootstrap.py .
  --allow-self --local-only` before rerunning runtime checks; do not manually
  patch installed files. For the native rerun, the orchestrator builds a
  disposable fixture from the actual generated workflow install (it already
  uses `.ai-bootstrap/`, so no prompt repointing) and a probe script based
  on the Phase A recipe. The user runs it in their own shell, because an
  agent session cannot start a nested `claude -p`; put any fixture `git
  commit` in that script. The orchestrator then checks `stream-json` events,
  `permission_denials`, and on-disk contents for a caller-saved plan and
  reviewer report, a log, and a memory edit at the new root. Use a fresh
  install only: Phase A showed the client's write check depends on the
  target path, and step 3's real-Git tests already prove migrated state.
  Document new/legacy behavior, refusal recovery, backup limitations,
  missing-agent and caller-saves behavior, and unchanged support boundaries.
  Map findings 1–8 to tests/native evidence in the closeout log. Resolve
  CRITICAL/MAJOR findings and explicitly dispose of MINOR findings before closing.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/test_install_bootstrap.py tests/test_sidecar_overlay.py tests/test_sidecar_install.py tests/test_sidecar_update.py tests/test_sidecar_uninstall.py tests/test_sidecar_workflow_scenario.py -q
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Record the native host-session rerun from step 6 here: the user runs the
  probe script, and the orchestrator records the verified results. Successful
  direct, coder, and documenter writes, plus caller-saved planner and
  reviewer output, from the actual generated installation are an
  acceptance condition even though this host check is not machine-run by
  `verify closeout`.
- Reproduce the reported legacy consumer layout in a disposable clone if
  available; never run an install/update in the real consumer for this plan.

## Review Profiles

Load `.claude/review-profiles/code.md`,
`.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Give the reviewer the state
transition table, native evidence, failure-injection results, and final diff.

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT).

- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
