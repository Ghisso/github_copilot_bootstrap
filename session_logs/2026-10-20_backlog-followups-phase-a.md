# Session: Backlog follow-ups — Phase A, status and wording cleanup

**Date:** 2026-10-20
**Plan:** .claude/plans/2026-10-20_phase-A-status-and-wording-cleanup.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** COMPLETED

## Goal

Close the stale AI-state statuses (BF-A1), use one OpenWiki sentence in the
root guidance (BF-A2), remove an undefined term and the brief's em dashes
(BF-A3), correct the project-name advice in three skills (BF-A4), replace
the `verify closeout` traceback with a clear message (BF-A5), record an
outcome for every 2026-09-21 OpenWiki follow-up (BF-A6), and restore the
vendored Ponytail `LICENSE` verbatim (BF-A7).

## Task Tracking

- [x] PRE-FLIGHT: `dev` clean and equal to `origin/dev` (`f964551`); big plan
  approved by the user on 2026-10-20 with all four recommended decisions
  (behavioral retry parked; memory archive in `.claude/explorations/`;
  `ponytail-review` complexity-only; scope additions approved). The user
  then asked to continue to the end of the big plan while away.
- [x] BRANCH: `backlog-followups_implementation` created from `dev`; hooks
  set the big plan `in-progress` (`started_at` 2026-10-20T14:54:11Z) and
  Phase A `in-progress`.
- [x] PLAN WHEN NEEDED: approved plan is implementation-ready; no planner.
- [x] IMPLEMENT/VERIFY/REVIEW — one review round; Gate Result `PASS`, one
  MINOR (fixed).
- [x] CLOSEOUT: documentation, final AI state, checkpoint, staged index,
  findings, phase receipt, closeout dry run, checkpoint, closeout receipt.
- [ ] COMMIT
- [ ] PUSH

## Work Log

- **14:55** - Steps 1 and 7 (orchestrator, nested AI state): set the two
  July big plans and their phase files to `complete` with Resolution notes
  (PR #7 `767fefc`, PR #8 `ab87dd7`; commits `82e9fbe`, `18e0a08`; score
  gate removed in `2af3df7`), ticked the pilot plan's Phase D with its
  completion pointer, and replaced only the status lines of the 2026-10-02
  sidecar review, the 2026-10-02 engineering exploration README (plus its
  Plan 2 link line), its pilot proposal, and the 2026-09-21 OpenWiki
  follow-ups. The two 2026-07-18 session logs are unchanged.
  `validate_plan_frontmatter.py` passes.
- **14:58** - Extracted upstream Ponytail `LICENSE` from the planning clone
  (`v4.8.4` = `bc9ee949…`, `v5.3.2` = `16352ac2…`): sha256 `fb1bc690…`; the
  local copy differs by `Dietrich Gebert` versus `DietrichGebert` and one
  trailing blank line.
- **15:00** - Delegated steps 2 and 6 (tests and `verify.py`) and steps 3,
  4, 5, and 8 (generator, root guidance, policy, brief, three skills,
  license and pin) to two coders on disjoint files.
- **15:05** - Coder 1: renamed the July lint test to
  `test_pre_contract_july_bodies_pass_the_lint_because_of_their_date` (copies
  the real files to `tmp_path` and swaps the status back). `verify.py`:
  `relative_artifact` takes `created_by` and raises `MissingArtifactError`
  only when nothing is at the path; `closeout_log_reference` split out of
  `closeout_log_path`; `main` returns 2 with one stderr line for missing
  evidence. Negative control: all 6 new tests failed on the old code (the
  `main()` test with the original `artifact is outside repository`
  traceback chain).
- **15:06** - Coder 2: one OpenWiki sentence in the generator, `CLAUDE.md`,
  `AGENTS.md`; Shape paragraph sentence replaced; seven em dashes removed
  from `openwiki/INSTRUCTIONS.md`; onboard, setup-project, and
  create-feature corrected; `LICENSE` copied byte for byte, pin moved in
  `UPSTREAM.md` and `scripts/validate_targets.py`, sidecar skills-profile
  snapshot recaptured after proving the `LICENSE` bytes alone changed it.
  Negative control: `validate_targets.py` reported `FAIL Ponytail allowlist
  hash changed without a provenance update: .../LICENSE` before the pin
  moved.
- **15:07** - Regenerated targets and ran the self-install refresh. Before
  the refresh, `verify.py fast` stopped with `receipt metadata control-plane
  provenance is invalid`: the edited root `CLAUDE.md` and `AGENTS.md`
  differed from `.claude/bootstrap-root/`, which empties the root
  fingerprint. This is the known behavior in MEMORY (`[LEARN:quality]` and
  `[LEARN:workflow]` on root-adapter mirrors); after the refresh it passed.
- **15:12** - `verify.py phase` (not persisted): PASS, 2773 passed,
  1 skipped. All required plan checks passed.
- **15:20** - Review (code, architecture, security, tests, ponytail,
  documentation; commit gate): Gate Result `PASS`, no open request, one
  MINOR: `.claude/instructions/project-context.instructions.md` still listed
  the stale statuses and the onboard mismatch as open. Fixed in nested
  state: the caveats now say Phase A closed them, keep the root-plans
  `Proposed` caveat and the template rule, and add the mirror rule above.
- **15:22** - Documentation: no `README.md` or `docs/` text described the
  changed behavior (searched for the old messages and terms); the skill and
  policy edits are this phase's documentation.

## [LEARN] Entries

- [LEARN:workflow] When two coders work in parallel in this repository, at
  most one of them may run `generate_targets.py` and `validate_targets.py`,
  and only after the other has stopped editing `shared/`: the validator's
  determinism check regenerates and fails with "generated dist is not
  deterministic" when a source file changes between the two renders.

## Verification

```text
PASS        0.3s  uv run python scripts/generate_targets.py --all
PASS       43.9s  uv run python scripts/validate_targets.py
PASS       71.8s  uv run pytest tests/test_verify.py tests/test_validate_plan_frontmatter.py tests/test_validate_targets.py -q
PASS        0.0s  echo "fb1bc6909ac3ef82d5c22106e32ef682b0cff66788fa915fb9b53b15c9d2f3ab shared/third_party/ponytail/LICENSE" | sha256sum -c -
PASS        0.8s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS        0.0s  for f in CLAUDE.md AGENTS.md dist/multi-agent/CLAUDE.md dist/multi-agent/AGENTS.md; do grep -qF "is derived context, never authority over source, tests, or policy. Refresh only by calling OpenWiki's own MCP tools per" "$f" || exit 1; done
PASS        0.0s  ! grep -nF -e "just-in-time repository context" -e "transition scope" -e "Project State" CLAUDE.md AGENTS.md scripts/generate_targets.py dist/multi-agent/CLAUDE.md dist/multi-agent/AGENTS.md shared/policies/workflow.instructions.md shared/skills/onboard/SKILL.md shared/skills/setup-project/SKILL.md shared/skills/create-feature/SKILL.md
PASS        0.0s  ! grep -nF "—" openwiki/INSTRUCTIONS.md
PASS        0.0s  ! grep -n "^status: in-progress" .claude/plans/codex-gpt-5.6-model-tiering.md .claude/plans/preserve-consumer-memory.md .claude/plans/2026-07-18_phase-A-preserve-consumer-memory.md .claude/plans/2026-07-18_phase-B-configure-codex-gpt-5.6.md
PASS        0.0s  grep -qF -e '- [x] `2026-10-03_phase-D-behavioral-pilot-knowledge-refresh`' .claude/plans/behavioral-evaluation-pilot.md
PASS        0.0s  ! grep -nF -e "Nothing below is fixed yet" -e "Plan 2 remains a deferred proposal" .claude/explorations/2026-10-02_sidecar-workflow-profile-hands-on-review.md .claude/explorations/2026-10-02_bootstrap-engineering-workflow/README.md
PASS        0.2s  uv run python .claude/scripts/verify.py fast --format json
closeout: PASS
```

Phase receipt: `.claude/quality_reports/verification-phase-2026-10-20_phase-A-status-and-wording-cleanup.json`.
Findings: `.claude/quality_reports/findings-2026-10-20_phase-A-status-and-wording-cleanup.json`
(1 MINOR, fixed; gate result `PASS`).

- optional 1: PASS — the reviewer read the nested AI-state diff (nine files)
  and confirmed only the named status lines, plan status fields, Resolution
  notes, and the one pilot phase line changed, and that no session log,
  findings report, or receipt changed.

## Open Questions / Next Steps

- Phase B follows: nested `.gitignore` and `.gitattributes` preservation.
- Known, unfixed: `verify.py` still stops with a traceback (not a FAIL check
  that names the file and the remedy) while a root adapter differs from its
  mirror. Already recorded in MEMORY `[LEARN:quality]`; candidate for a later
  plan.
