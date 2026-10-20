---
name: 2026-10-20_phase-B-nested-state-files
type: small-plan
parent_plan: backlog-followups
phase_index: 2
status: planned
closeout_session_log:
---

# Small Plan: Keep the Nested `.gitignore` and `.gitattributes` Across Refreshes

## Scope

A bootstrap refresh deletes the nested `.claude/.gitignore` and
`.claude/.gitattributes`, because both count as bootstrap-owned files that
the generated output does not contain (`scripts/install_bootstrap.py:573-596`,
`:612-627`; seen in
`.claude/session_logs/2026-09-19_openwiki-phase-G-host-driven-guard.md:77`).
`state-sync.sh` then rebuilds `.gitignore` from its template, so lines a
consumer added are lost, and the installer's following `git add -A` and
`bootstrap: update` commit (`scripts/install_bootstrap.py:1139-1160`) can
stage, commit, and push files those lines kept out of the shared ai-state
remote (BF-B1). Nothing rewrites `.gitattributes`, so the
`session_logs/*.log merge=union` rule that `docs/runtime-checks.md:362-364`
promises disappears after the first refresh; this repository's nested
history has never had that file (BF-B2). This is item 6 of
`.claude/explorations/2026-09-21_openwiki-followups-and-instruction-alignment.md`,
handed over by Phase A; that record rated it LOW, but the possible push of
an ignored secret makes it a security fix, so it runs early.

This phase changes only refresh ownership and `state-sync.sh`. It is the
plan's only change to `scripts/runtime_ownership.py`; the memory archive in
Phase C needs none.

## Steps

- [ ] **1. Stop a refresh from deleting the nested `.gitignore` and `.gitattributes` (BF-B1).**
  **Owner:** coder.
  **Files:** modify `scripts/runtime_ownership.py`,
  `scripts/check_runtime.py`, `scripts/validate_targets.py`,
  `shared/hooks/scripts/state-sync.sh` (`write_nested_gitignore` only),
  `tests/test_install_bootstrap.py`, and `tests/test_state_sync.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Root cause: `owned_files()` counts every file at the nested root except
  `.git` as bootstrap-owned (`scripts/install_bootstrap.py:573-596`), and
  the removal loop deletes each one the generated output lacks
  (`:612-627`); `dist/multi-agent/.claude/` has neither file. Add
  `".gitignore"` and `".gitattributes"` to `CONSUMER_STATE_PATHS`
  (`scripts/runtime_ownership.py:42-56`), with a comment in the style of
  the `settings.local.json` entry: `state-sync.sh` writes both and a
  consumer may extend them, so a refresh must not delete them. That entry,
  not `STATE_DIR_OWNED_README_PATHS` from `d2d0847`, is the fitting
  precedent, because these are consumer-side files, not bootstrap-owned
  ones. `is_consumer_state_path` then covers the installer and
  `check_runtime.py` alike, so delete the now-redundant
  `relative == Path(".gitignore")` special case in `scripts/check_runtime.py`
  (about line 259). Keep both files out of `NESTED_MUTABLE_STATE_ROOTS` in
  `shared/scripts/verify.py`: they decide what reaches the shared ai-state
  remote, so they stay bound to control-plane provenance.
  Safety hardening that must ship with it: today every refresh restores
  the template, so `settings.local.json` is always ignored again before
  the installer runs `git add -A` (`scripts/install_bootstrap.py:1139-1160`).
  Once the file is preserved, a nested `.gitignore` without that line would
  let the installer commit local settings. So `write_nested_gitignore`
  (`state-sync.sh:90-111`) also appends a `settings.local.json` line when
  that exact line is absent, the same way it handles `.cache/`.
  **Tests:** in `tests/test_install_bootstrap.py`, `copy_generated_tree`
  keeps a nested `.gitignore` with a consumer line and a `.gitattributes`
  byte for byte (show it failing on the current code first), and
  `runtime_drift_errors` reports no drift for either file. In
  `tests/test_state_sync.py`, setup adds `settings.local.json` once to a
  `.gitignore` that lacks it, and a second run adds nothing; update the
  exact line list in
  `test_setup_upgrades_existing_nested_gitignore_without_overwriting_user_entries`.
  In `scripts/validate_targets.py`, update the exact `CONSUMER_STATE_PATHS`
  tuple (`:9785-9803`) and add both files to the repeat-install
  `consumer_state` fixture (`:9776-9784`). Build the fixture `.gitignore`
  from `temp_repo/.claude/.gitignore`, the file the first temporary install
  wrote, plus one sentinel line, so `settings.local.json` stays ignored and
  the byte comparison holds. Never read this repository's own `.claude/`:
  CI runs `validate_targets.py` on a fresh checkout that has none
  (`.github/workflows/validate.yml`). Seed the `.gitattributes` fixture with
  `session_logs/*.log merge=union` plus a sentinel line, so step 2's append
  leaves it byte-identical.

- [ ] **2. Restore the union-merge rule in existing nested repositories (BF-B2).**
  **Owner:** coder (same coder as step 1; same files).
  **Files:** modify `shared/hooks/scripts/state-sync.sh`
  (`write_nested_gitattributes` and its callers) and
  `tests/test_state_sync.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  `write_nested_gitattributes` (`state-sync.sh:187-192`) runs only from
  `init_nested_repo` and overwrites the file. Make it write the current
  two lines when the file is missing, and otherwise append
  `session_logs/*.log merge=union` only when that exact line is absent,
  mirroring `write_nested_gitignore`. Call it wherever
  `write_nested_gitignore` runs for an existing nested repository
  (`commit_local_state`, `setup_local_state`, `cmd_setup`). Then
  `docs/runtime-checks.md:362-364`, which says every `session_logs/*.log`
  is union-merged, becomes true for upgraded repositories too.
  **Tests:** an existing nested repository without `.gitattributes` has it
  after `setup` and after `checkpoint`, with the union line once and the
  file tracked; an existing `.gitattributes` with a user line keeps that
  line and gains the union line once; a second run changes nothing.
  `test_append_only_log_union_merges` stays green.


- [ ] **3. Regenerate, refresh, prove durability, document, review, close out.**
  **Owner:** orchestrator; fresh reviewer; documenter after review.
  **Required Skills:** `shared/skills/documentation/SKILL.md`,
  `shared/skills/code-review/SKILL.md`.
  Before the first refresh, record `git -C .claude ls-files .gitignore
  .gitattributes` and a copy of `.claude/.gitignore` in the session log.
  Run `uv run python scripts/generate_targets.py --all` and
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  before verification. When auto mode denies the refresh, hand it to the
  user. This refresh is the first one with BF-B1 and BF-B2 in place: it
  must keep `.claude/.gitignore` byte for byte and add and commit
  `.claude/.gitattributes`. The `ls-files` item below runs after it. The
  documenter updates the consumer-state lists in
  `docs/runtime-checks.md:34-37` and `:79-80` to name the nested
  `.gitignore` and `.gitattributes`.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/test_install_bootstrap.py tests/test_state_sync.py -q
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
git -C .claude ls-files --error-unmatch .gitignore .gitattributes
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- In a disposable consumer install, add a custom ignore line to the nested
  `.gitignore`, run the installer again, and record that the line and an
  ignored file stay out of the nested `bootstrap: update` commit.

## Review Profiles

Use `.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Give the reviewer item 6 of
`2026-09-21_openwiki-followups-and-instruction-alignment.md`, BF-B1 and
BF-B2, the failing-first test output, the before and after nested
`.gitignore`, and the final outer diff.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
