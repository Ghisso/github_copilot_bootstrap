# Session: Outer-repository automatic push

**Date:** 2026-09-11
**Plan:** `.claude/plans/2026-09-11_phase-A-outer-repo-auto-push.md`
**Status:** COMPLETED

## Goal

Make the orchestrator publish successful outer-repository commits by default
when a normal remote push is available, without changing nested `.claude`
`ai-state` publication or automatic PR/merge behavior.

## Work Log

- Plan approved and implementation branch created.
- Confirmed that completed-phase receipts must become historical records after
  the post-commit transition; later phases must not stale their certified state.
- Added the `PUSH` lifecycle stage to shared orchestrator and workflow
  guidance, generated root guidance, and consumer-target validation. The
  intended command is a normal non-force outer-repository push using the
  branch upstream or `origin`, with `GIT_TERMINAL_PROMPT=0`.
- Added the completed-phase publication path. It permits only the exact,
  non-merge completion commit directly certified by the prior phase's receipt
  and findings after `post-commit` advances to the next in-progress phase.
  Paused checkpoints, terminal closeout, nested `.claude` state sync, PRs,
  and merges retain their separate behavior.
- Added local-bare-remote coverage for Phase A publication, agent-facing
  `HEAD` resolution, receipt/artifact tampering, bypass acknowledgement,
  arbitrary Phase B work, stale completion evidence, and Phase B final push.
- Updated README and architecture, runtime-check, and smoke-test docs to
  distinguish outer code publication from nested `ai-state` publication.
- Narrowed the `assert_push_invariants` dispatch so the new intermediate route
  is selected only when the big plan is `in-progress`, the current small plan
  is `in-progress`, and a completed predecessor phase exists. First-phase and
  current-complete in-progress states retain strict closeout behavior.
- Ran the required stale-claims audit across all eleven surface categories
  named by the big plan. Corrected four canonical sources; see
  `## Stale-claims surfaces checked`.
- Completed two review rounds across the `code`, `architecture`, `security`,
  `tests`, and `ponytail` profiles. Round one returned two MAJOR and two MINOR
  findings; all four were fixed. Round two returned zero findings.
- Regenerated targets and completed local-only self-install after every edit.
  The nested state repository is locally ahead; no outer or nested remote push
  was attempted during implementation.

## Review Findings And Resolutions

Round one raised four findings. All were verified against the code before
being acted on, and all four were fixed rather than dispositioned.

- MAJOR (`ponytail`) — `assert_paused_publication_invariants` and
  `assert_completed_phase_publication_invariants` carried near-identical
  phase-walk loops, differing only in their accumulator and one message
  string. Both gate real pushes on the same complete-or-evidenced-cancelled
  invariant, so a fix applied to one copy would silently diverge the two
  gates. Factored into `assert_prior_phases_terminal`, which reports results
  through `PRIOR_PHASES_COMPLETED_COUNT` and `PRIOR_PHASES_LAST_COMPLETED` and
  takes a `push_label` so each path keeps its own duplicate-status message.
- MAJOR (`tests`) — `git_is_direct_child` had no coverage for merge commits or
  abbreviated SHAs, so loosening `len(parts) == 2` to `len(parts) >= 2` would
  have admitted merge commits as certified while every existing test passed.
  Added `test_certified_receipt_relation_rejects_a_merge_and_accepts_short_shas`.
- MINOR (`code`) — `git_is_direct_child` resolved `child` through
  `rev-parse --verify --quiet` but compared `parent` by raw string equality.
  Not exploitable, because `head_sha` is always written as a full canonical
  SHA by the same trusted tool, but it would deny a legitimate push if that
  ever changed. Both endpoints are now resolved the same way.
- MINOR (`tests`) — the `tampered_publication` check asserted only a generic
  deny, so an unrelated denial would have satisfied it. Now pinned to
  `artifact closeout_log was tampered with`.

Round two confirmed each fix and returned zero findings.

Four round-one concerns were investigated and refuted rather than recorded as
findings. The load-bearing one: the `certified` relation does not weaken
receipt binding. Its tree check and the findings-report `content_hash` check
both run unconditionally, and `historical_chain_errors` runs whenever a
receipt head is present, so outer-tree or artifact tampering is still caught.
The only check this route skips is nested-runtime `control_plane_provenance`
freshness, which `docs/architecture.md` and `docs/runtime-checks.md` already
documented as terminal-phase-only before this change.

## [LEARN] Entries

- [LEARN:workflow] A post-commit phase transition means an intermediate push
  must validate the prior receipt against the exact completion commit, not the
  newly current plan state. The `HEAD` form used by PreToolUse must be resolved
  to a commit SHA before direct-parent validation.
- [LEARN:review] When two gate functions enforce the same security invariant
  through copied loops, the duplication is the defect, not the style. The two
  copies here differed only in their accumulator, so a later fix to one would
  have silently diverged the paused-checkpoint and completed-phase gates while
  every test still passed.
- [LEARN:testing] A direct-parent check needs a merge-commit case to be
  load-bearing. Loosening `len(parts) == 2` to `>= 2` left the original
  linear-history test passing, and the fixture must put the certified commit
  in the merge's *first* parent position so a naive parent-count fix cannot
  satisfy it either.
- [LEARN:quality] Tighten a test assertion to the mechanism the code actually
  reports, not to the identifier you expect to see. Pinning the tamper denial
  to the phase name failed because the real message names the tampered
  artifact (`artifact closeout_log was tampered with`); the fix was to read the
  produced message rather than to guess at it.
- [LEARN:workflow] Guidance that is both generated and hand-maintained drifts
  in the hand-maintained copy. `render_root_guidance` already emitted the
  correct push bullet and `dist/` carried it, but this repository's own root
  `CLAUDE.md` stayed stale because no gate validates it — only freshly
  rendered guidance is checked. Shared skills have `stale_skill_contract_errors`
  for exactly this; authoring-repo root guidance has no equivalent.

## Stale-claims surfaces checked

Repository-wide sweep required by the big plan's `## Completion Evidence`,
covering root guidance, `README.md`, `docs/`, shared policy, agent, hook,
generator, validator, test, template, and runtime-mirror surfaces. Each entry
was verified against current code before any correction was made.

### Corrected

- `CLAUDE.md` (two places) — the Required Lifecycle line ended at `COMMIT`,
  and the bullet "Do not open a PR, push, or merge unless the workflow permits
  it and the user requested the external action" directly contradicted the new
  default. Corrected to `COMMIT -> PUSH` and replaced the bullet with the
  wording `render_root_guidance` already emits, so source and generator agree
  word for word.
- `AGENTS.md` — the workflow sentence read `... closeout -> commit workflow`.
  Corrected to `... closeout -> commit -> push workflow`.
- `shared/policies/workspace.instructions.md` (two places) — the
  instruction-index row for `workflow.instructions.md` and the `## Workflow`
  block both omitted the new stage, so this file contradicted its own sibling
  `workflow.instructions.md`, which already read `... COMMIT -> PUSH`. Both
  corrected.
- `shared/skills/commit/SKILL.md` — the behavioral surface that mattered most.
  Phase 5 was titled "Push or PR (if requested)", its frontmatter description
  covered only "staging, committing, branching, and PR creation", and the
  automatic push appeared nowhere, so an agent following the skill literally
  would never learn that push is now a default. Rewrote Phase 5 to document
  the non-force push, upstream-then-`origin` selection,
  `GIT_TERMINAL_PROMPT=0`, the warn-and-keep-local failure behavior, the
  separation from nested `.claude` AI-state sync, and all three states the
  push gate accepts. PR creation stays explicitly user-requested.

### Verified consistent, no change needed

- `.github/copilot-instructions.md`, `.github/instructions/*.md`,
  `.github/agents/*.agent.md` — pointer adapters with no push claims;
  `workflow.instructions.md`'s title already read `... -> Commit -> Push`.
- `.codex/agents/orchestrator.toml`, `.agents/agents/orchestrator/agent.md` —
  already carry the full `9. **PUSH:**` stage.
- `SECURITY.md` — no push claims.
- `README.md` — lifecycle lines, the new push bullet, and the closeout
  sequence all updated in this phase. The paused-checkpoint text is about the
  `pre-push` gate invariant, which is unchanged, not about who initiates a push.
- `docs/` (all eight files) — `architecture.md`, `runtime-checks.md`, and
  `smoke-tests.md` describe the new behavior. `architecture.md`'s "manual push
  task" references are the VS Code **AI state: push** task for nested
  `ai-state`, correctly out of scope. `plan-deterministic-commit-gate.md` and
  `2026-08-09-state-sync-rebase-recovery.md` are dated design records.
- `shared/policies/` — `workflow.instructions.md` updated; the remaining seven
  files carry only gate-contract push text or none.
- `shared/agents/` — `orchestrator/prompt.md` updated. `coder`, `planner`,
  `documenter`, `luna_coder`, `sol_coder`, `antigravity_flash_coder`, and the
  Codex/Antigravity supplements make no push claims; `reviewer/prompt.md` is
  gate-signal text only.
- `shared/skills/` — `safe-consumer-bootstrap-refresh` is entirely nested
  `ai-state`; `plan-decomposition` is paused-checkpoint only.
- `shared/hooks/` — no script comment or user-facing message claims push is
  manual. `enforce-pr-gate.sh`, `git-hooks/pre-push`, and `git-protection.sh`
  messages describe unchanged invariants; all `state-sync.sh` warnings are
  nested-`ai-state` scoped.
- `scripts/` — `generate_targets.py` and `validate_targets.py` updated in this
  phase; `check_runtime.py`, `install_bootstrap.py`, and `update_consumers.py`
  concern `pre-push` gate ownership or nested-state publication only.
- `tests/` — no test asserted the old wording.
  `test_rendered_root_guidance_defaults_only_outer_commits_to_push` asserts
  both the new lifecycle string and `GIT_TERMINAL_PROMPT=0`.
- `shared/templates/` — `plan-small.md` and `session-log.md` describe only the
  user-requested paused checkpoint, whose semantics are unchanged.
- Runtime mirror `.claude/` and `dist/multi-agent/` — regenerated and
  self-installed after every source edit; all previously stale copies now
  follow their corrected sources, including the
  `.claude/bootstrap-root/` root-adapter mirror.

### Known gap, deliberately not closed in this phase

This repository's own root `CLAUDE.md` and `AGENTS.md` are hand-maintained
authoring variants that no gate validates; `root_guidance_errors` runs only
against freshly rendered guidance. That is why `CLAUDE.md` went stale while
`dist/multi-agent/CLAUDE.md` was correct. Shared skills have a drift gate
(`stale_skill_contract_errors` in `scripts/validate_targets.py`) for exactly
this class of problem. Adding the equivalent gate for authoring-repo root
guidance is separate work and was not folded into this phase's scope.

## Verification Results

```bash
uv run python scripts/validate_plan_frontmatter.py \
  .claude/plans/2026-09-11_outer-repo-auto-push.md \
  .claude/plans/2026-09-11_phase-A-outer-repo-auto-push.md
```

Plan frontmatter passed before branch creation.

Final state, after the review fixes and the stale-claims corrections, with
targets regenerated and locally self-installed beforehand:

```text
uv run pytest tests/ -q --tb=short            1440 passed
uv run python scripts/validate_targets.py     exit 0
uv run python scripts/check_runtime.py        20 PASS, 0 FAIL
uv run python .claude/scripts/verify.py fast  PASS
uv run mypy shared scripts tests              no issues in 28 source files
uv run ruff check shared scripts tests        0 violations
uv run ruff format --check shared scripts tests   0 files need reformatting
bash -n shared/hooks/scripts/_lib-frontmatter.sh  clean
generate_targets.py --all                     regenerated
install_bootstrap.py . --allow-self --local-only  installed
```

The new merge/abbreviated-SHA test was proven load-bearing by mutation:
loosening `len(parts) == 2` to `len(parts) >= 2` in `git_is_direct_child`
failed the new test while the pre-existing linear-history test still passed.
The guard was restored and the suite re-run.

## Open Questions / Next Steps

1. Consider adding a drift gate for this repository's hand-maintained root
   `CLAUDE.md` and `AGENTS.md`, mirroring `stale_skill_contract_errors`. See
   `## Stale-claims surfaces checked` for why this phase left it open.
2. No outer-repository remote push has been attempted on this branch. The new
   default applies from the next commit onward.
