---
name: 2026-09-11_phase-A-outer-repo-auto-push
type: small-plan
parent_plan: 2026-09-11_outer-repo-auto-push
phase_index: 1
status: in-progress
closeout_session_log: session_logs/2026-09-11_outer-repo-auto-push.md
---

# Small Plan: Outer-repository automatic push

## Scope

Change the shared orchestrator workflow so it attempts a normal, non-force
outer-repository push after each successful commit. The behavior must render
into consumer targets and be dogfooded in this repository after regeneration
and local-only self-installation. It must not alter nested `.claude` state-sync
or make pull requests and merges automatic.

## Steps

- [ ] Modify `shared/agents/orchestrator/prompt.md`,
  `shared/policies/workflow.instructions.md`, and generated root guidance in
  `scripts/generate_targets.py` to add a conditional PUSH stage after COMMIT.
  Direct the orchestrator to use the branch upstream when configured, otherwise
  `origin`; use a normal non-force push with terminal prompts disabled. A
  missing remote, authentication failure, or network failure must warn and keep
  the completed commit local. PR creation and merge remain user-requested.
- [ ] Modify the public outer-repository push contract in
  `shared/hooks/scripts/_lib-frontmatter.sh` and its callers so a push after a
  completed phase is allowed only when the committed phase has valid persisted
  receipt/finding evidence. After `post-commit` advances the big plan to its
  next phase, identify and validate the just-completed prior phase against its
  certified completion commit; do not require the current phase to remain the
  completed one. Preserve existing paused-checkpoint and final closeout paths,
  and reject an arbitrary commit from an in-progress phase.
  Keep the nested `.claude` push exemption unchanged.
- [ ] Extend the existing local-bare-remote validator and hook tests in
  `scripts/validate_targets.py`, `tests/test_hook_gates.py`, and
  `tests/test_lifecycle_hooks.py`. Cover a valid completed-phase push, an
  in-progress or stale-evidence denial, Phase A publication followed by a
  valid Phase B completion/final push, historical Phase A artifact tampering,
  paused and final-closeout compatibility, absent/failed outer remotes, and
  generated prompt/policy parity. Do not make network-dependent tests.
- [ ] Regenerate `dist/multi-agent/` from source and locally self-install it
  with `install_bootstrap.py . --allow-self --local-only`; never hand-edit
  generated files. Confirm the authoring runtime and each consumer target carry
  the outer-push guidance.
- [ ] Update `README.md` and affected architecture/runtime/smoke-test docs to
  distinguish outer automatic publication from existing nested `ai-state`
  publication, including the non-blocking unavailable-remote behavior. Perform
  the required final stale-claims, documentation, memory, and LEARN audit.

## Verification

```bash
uv run pytest tests/test_hook_gates.py tests/test_lifecycle_hooks.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json
```

## Closeout Checklist

- [ ] Documentation updated for outer versus nested publication
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Code, architecture, security, tests, and Ponytail reviews complete
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
