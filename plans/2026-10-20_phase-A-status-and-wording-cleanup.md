---
name: 2026-10-20_phase-A-status-and-wording-cleanup
type: small-plan
parent_plan: backlog-followups
phase_index: 1
status: complete
closeout_session_log: .claude/session_logs/2026-10-20_backlog-followups-phase-a.md
---

# Small Plan: Status and Wording Cleanup

## Scope

Clear the small, already-diagnosed backlog items before the larger phases
start. Four older plans still say `in-progress` although their work was
merged, the pilot big plan still shows its finished Phase D as paused, and
three dated records still say their work is open or deferred (BF-A1). The
OpenWiki sentence in the root guidance has three different wordings
(BF-A2). The knowledge-refresh rule uses an undefined term, and the
OpenWiki brief breaks its own em-dash rule (BF-A3). The `onboard` skill and
two sibling skills give wrong advice about the generated project-name line
(BF-A4). `verify closeout` crashes with a misleading traceback when the
findings report is missing (BF-A5). Every item of the 2026-09-21 OpenWiki
follow-up record gets a written outcome (BF-A6). The vendored Ponytail
`LICENSE` is not byte-identical to upstream, although upstream's blob is the
same at `v4.8.4` and `v5.3.2`; restoring it here keeps the fix independent of
Phase E's adoption decision (BF-A7).

Status corrections in the nested `.claude` AI-state repository never stand
alone: they ride the normal nested checkpoint, and the outer commit carries
the guidance, skill, generator, verifier, and test changes. No session log,
findings report, or receipt is edited. No OpenWiki run happens here;
Phase G refreshes the wiki after every source edit.

## Steps

- [x] **1. Close the stale AI-state statuses honestly (BF-A1).**
  **Owner:** orchestrator (nested AI-state writes).
  **Files (nested `.claude` repository only):**
  `plans/codex-gpt-5.6-model-tiering.md`,
  `plans/2026-07-18_phase-B-configure-codex-gpt-5.6.md`,
  `plans/preserve-consumer-memory.md`,
  `plans/2026-07-18_phase-A-preserve-consumer-memory.md`,
  `plans/behavioral-evaluation-pilot.md` (line 172 only),
  `explorations/2026-10-02_sidecar-workflow-profile-hands-on-review.md`
  (line 5 only),
  `explorations/2026-10-02_bootstrap-engineering-workflow/README.md`
  (lines 9 and 36-37 only), and
  `explorations/2026-10-02_bootstrap-engineering-workflow/behavioral-evaluation-pilot.md`
  (line 3 only).
  **Required Skills:** `shared/skills/documentation/SKILL.md`.
  Rules:
  1. Both July big plans: set `status: complete`, leave `current_phase:`
     with an empty value (the shape `gate-repair.md` uses), tick the body
     phase entry, and add one sentence naming the merge: PR #7 (`767fefc`)
     for `codex-gpt-5.6-model-tiering`, PR #8 (`ab87dd7`) for
     `preserve-consumer-memory`, both 2026-07-18.
  2. Both July phase files: set `status: complete` and keep the existing
     `closeout_session_log` value. Do not tick checklist items that were
     never met. Add a `## Resolution` section that states: the work was
     committed (`82e9fbe` for the Codex phase, `18e0a08` for the memory
     phase) and merged as the PR above; the linked session log still says
     BLOCKED because the retired score gate (85, below 90) stopped the
     agent's own commit; that score gate was removed on 2026-09-02
     (`2af3df7`), when `verify.py` became the only deterministic
     authority.
  3. Leave both 2026-07-18 session logs byte for byte unchanged. They are
     accurate records of what happened on that day.
  4. Pilot big plan line 172: tick Phase D and replace the "paused ...
     Resume from" text with its completion pointer
     (`.claude/session_logs/2026-10-06_behavioral-pilot-phase-d.md`, merged
     as PR #45, `050a1de`). Change no other line of that completed plan.
  5. Each of the three exploration status lines: replace only that line
     with a dated closed status and a pointer. Sidecar review: findings
     1-7 fixed by `sidecar-workflow-repair` (PR #43, `1626364`); the
     evidence map is the "Findings to evidence" table in
     `.claude/session_logs/2026-10-02_sidecar-workflow-repair.md`.
     Engineering README and pilot proposal: Plan 2 was approved and run as
     `.claude/plans/behavioral-evaluation-pilot.md` (PR #45); it stopped
     after Phase A under its stop rule, with no comparison result; see
     `docs/2026-10-06-behavioral-pilot-evidence.md`. Keep every finding,
     decision, and evidence paragraph below those lines unchanged. This
     follows the sidecar repair plan's rule against rewriting historical
     findings: only the status line changes.
  **Done when:** `uv run python scripts/validate_plan_frontmatter.py`
  passes, and the reviewer has read the nested diff for exactly these eight
  files.

- [x] **2. Keep the July-plan lint test meaningful (BF-A1).**
  **Owner:** coder.
  **Files:** modify `tests/test_validate_plan_frontmatter.py`
  (`test_pre_contract_july_in_progress_plans_pass_unchanged`, lines
  1657-1669).
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/testing-patterns/SKILL.md`.
  After step 1 the two real July phase files are `complete`, so the test
  would pass for the wrong reason (completed plans skip the lint). Reuse
  the pattern of `test_phase_a_fixture_fails_l2_on_its_step_bullet_sentence`
  (lines 1634-1654): copy each real file into `tmp_path` under its own
  name, replace `status: complete` with `status: in-progress` once, and
  assert no validation errors. Update the name and docstring to say the
  date gate, not the status, is what lets these live-status bodies pass.
  Never edit the real plan files from a test.

- [x] **3. Use one OpenWiki sentence in the root guidance (BF-A2).**
  **Owner:** coder.
  **Files:** modify `scripts/generate_targets.py` (`render_root_guidance`,
  line 1393), `CLAUDE.md` (line 14), and `AGENTS.md` (line 9).
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/documentation/SKILL.md`.
  Edit the generator string first, then make the two tracked root files
  carry the same sentence byte for byte. `CLAUDE.md` and the generator keep
  their leading `- ` list marker; `AGENTS.md` keeps it as a plain
  paragraph. The sentence is the one the 2026-09-21 review proposed. It
  uses "derived context", the term the central Knowledge Ownership rule in
  `shared/policies/workspace.instructions.md` and `README.md:16` already
  use:

  ```text
  An optional OpenWiki knowledge layer, enabled when `openwiki/INSTRUCTIONS.md` exists, is derived context, never authority over source, tests, or policy. Refresh only by calling OpenWiki's own MCP tools per `.claude/skills/knowledge-refresh/SKILL.md`; never hand-edit a generated page or commit OpenWiki's own root snippet.
  ```

  Must not: change any other root-guidance line, a budget, or a
  `root_guidance_errors` invariant in `scripts/validate_targets.py`. The
  installer keeps preserving the tracked root files in this repository
  (`scripts/install_bootstrap.py:560-571`), so regeneration changes only
  `dist/multi-agent/CLAUDE.md` and `dist/multi-agent/AGENTS.md`.

- [x] **4. Remove the undefined term and the brief's em dashes (BF-A3).**
  **Owner:** coder.
  **Files:** modify `shared/policies/workflow.instructions.md` (the
  Knowledge-Refresh Final Phase "Shape" paragraph, lines 288-294) and
  `openwiki/INSTRUCTIONS.md` (lines 39, 47, 49, 51, 154, 156, 158).
  **Required Skills:** `shared/skills/documentation/SKILL.md`.
  Replace the last sentence of the Shape paragraph, "It does not carry a
  larger phase's transition scope.", with self-contained wording. Proposed:

  ```text
  Setup work, such as enabling OpenWiki for the first time or upgrading it, belongs in an earlier phase, not in this one.
  ```

  In the brief, replace each of the seven prose em dashes with a colon,
  semicolon, or period. The brief is human-authored, so a direct edit is
  correct; never edit a generated `openwiki/**` page.

- [x] **5. Correct the project-name guidance in three skills (BF-A4).**
  **Owner:** coder.
  **Files:** modify `shared/skills/onboard/SKILL.md` (lines 21-26, 92-94,
  104-131, and the Output line 147), `shared/skills/setup-project/SKILL.md`
  (lines 65-71), and `shared/skills/create-feature/SKILL.md` (lines
  119-123).
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/documentation/SKILL.md`.
  Facts the new text must match:
  - The installer writes the target directory name into the generated
    `**Project:**` line of root `CLAUDE.md`, root `AGENTS.md`,
    `.claude/instructions/workspace.instructions.md`, and `workspace.md`
    (`scripts/install_bootstrap.py:818-848`). A refresh copies the
    generated files over the old ones and writes the name again, so a hand
    edit to those copies is lost.
  - `.claude/instructions/project-context.instructions.md` is consumer
    state that a refresh never overwrites
    (`scripts/runtime_ownership.py:51`). The project's one-line summary
    belongs there, as `README.md:83-86` and `README.md:1429` already say.
  - The installer adds root `CLAUDE.md` and `AGENTS.md` to a consumer's
    `.gitignore` (`scripts/runtime_ownership.py:354-355`), but it leaves a
    root file that Git already tracks untouched
    (`scripts/install_bootstrap.py:560-571`). In this authoring repository
    both files are tracked and maintained by hand.
  - `shared/policies/workspace.instructions.md` is the template every
    consumer receives. Its placeholder must stay, because the installer
    fills it (`scripts/validate_targets.py:10125-10138`) and
    `scripts/check_runtime.py:62,82` undoes only that exact substitution.
  Rewrite onboard step 5 around those facts: do not edit the generated
  `**Project:**` line; put the summary in `project-context`; edit a
  tracked root file's `**Project:**` line directly; never fill the
  template placeholder. Fix the Problem paragraph so it says the root files
  are gitignored generated files in a normal consumer and tracked
  hand-maintained files where Git tracks them. Replace the line 92-94
  pointer to `.claude/bootstrap-root/` (that directory mirrors root
  adapters only; it is not a template of the bootstrap) with the
  consumer-state fact above. Change the Output line to name
  `project-context.instructions.md`. In `setup-project` and
  `create-feature`, replace the slot instructions with one sentence that
  points to `project-context.instructions.md` and to onboard step 5. Do
  not use the words "Project State" in any of the three skills; refer to
  "the generated `**Project:**` line".
  Must not: change `shared/policies/workspace.instructions.md`, the
  installer, or `check_runtime.py`.

- [x] **6. Replace the closeout traceback with a clear message (BF-A5).**
  **Owner:** coder.
  **Files:** modify `shared/scripts/verify.py` (`relative_artifact` at
  lines 3162-3169, `closeout_artifacts` at lines 3270-3300, and its call in
  `main` at lines 3790-3794) and `tests/test_verify.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Today a missing findings report makes `confined_path` raise, and
  `relative_artifact` re-raises it as "artifact is outside repository",
  which `main` does not catch. Required behavior:
  - `verify closeout` with a missing findings report, phase receipt, or
    closeout log exits 2, prints one stderr line, and persists no receipt.
  - The line names the missing repository-relative path and the step that
    creates it: `record_findings.py` for the findings report,
    `verify.py phase --format json --persist` for the phase receipt, and
    the small plan's `closeout_session_log` for the log.
  - A path outside the repository, a symlinked path, and a non-regular
    file are still rejected, with a message that says which.
  Must not: change `confined_path`, the receipt schema, any other exit
  code, or the frozen fixtures `tests/fixtures/schema-v*-verify.py.txt`.
  **Tests:** follow
  `test_closeout_missing_documentation_na_reports_diagnostic_not_traceback`
  (`tests/test_verify.py:4536`). Add one `main()`-level test with a valid
  phase, a `--documentation-na` reason, and no findings report. Assert
  exit code 2, no `Traceback` in stderr, and stderr naming
  `.claude/quality_reports/findings-<phase>.json` and `record_findings.py`.
  Add one direct `closeout_artifacts` test for a missing phase receipt.
  The existing symlink and unsafe-reference tests (lines 394 and 1589)
  must pass unchanged.

- [x] **7. Record an outcome for every 2026-09-21 follow-up (BF-A6).**
  **Owner:** orchestrator.
  **Files:** nested
  `explorations/2026-09-21_openwiki-followups-and-instruction-alignment.md`
  (line 8 only), plus the phase closeout session log.
  Replace only the status line with a dated status that names each item's
  outcome: items 1, 3, 4, and 5 fixed by this phase; item 8 already
  resolved (no `openwiki_refresh` bytecode remains under
  `shared/scripts/__pycache__/`); items 2, 6, and 7 moved to the phases the
  big plan assigns. Proposed owners: item 2 (the quickstart "refresh this
  wiki" row omits `shared/hooks/scripts/openwiki-guard.sh`; a generated
  page, so only an OpenWiki run may fix it) to Phase G; item 6 (the
  self-refresh deletes the nested `.claude/.gitignore`) to Phase B, which
  changes consumer-state ownership; item 7 (a native Codex re-probe
  of the OpenWiki guard) to Phase F as an optional item. Name "carried,
  no owner" with the reason for any item the big plan does not assign.

- [x] **8. Restore the vendored Ponytail license verbatim (BF-A7).**
  **Owner:** coder; the orchestrator fetches the upstream file.
  **Files:** modify `shared/third_party/ponytail/LICENSE`,
  `shared/third_party/ponytail/UPSTREAM.md` (the `LICENSE` sha256 line,
  about line 39), `scripts/validate_targets.py` (the `LICENSE` entry of the
  Ponytail sha256 pins, about line 7974), and, only if its snapshot test
  fails because of these bytes, `SIDECAR_SKILLS_PROFILE_SNAPSHOT_SHA256` in
  `tests/test_validate_targets.py` (about lines 3314-3316, with its comment
  naming this change).
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`.
  Bare-clone `https://github.com/DietrichGebert/ponytail.git` into the
  session scratch folder (untrusted data, never inside the repository) and
  write `git show v4.8.4:LICENSE` byte for byte over the vendored file. The
  result must have sha256
  `fb1bc6909ac3ef82d5c22106e32ef682b0cff66788fa915fb9b53b15c9d2f3ab`
  (the same blob, `715d483`, at `v4.8.4` and `v5.3.2`). The local copy reads
  `Dietrich Gebert` where upstream reads `DietrichGebert` and has one extra
  trailing blank line. Change no other Ponytail pin, release, or commit
  value. **Negative control:** before the pin edit, `validate_targets.py`
  reports the `LICENSE` hash mismatch.

- [x] **9. Regenerate, refresh the installed runtime, review, close out.**
  **Owner:** orchestrator; fresh reviewer.
  **Required Skills:** `shared/skills/code-review/SKILL.md`.
  Run `uv run python scripts/generate_targets.py --all` and
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  before verification. The auto-mode safety classifier has denied the
  self-install refresh before; if it does, ask the user to run that one
  command. Give the reviewer the outer diff, the nested diff for the eight
  step 1 files and the step 7 file, and BF-A1 to BF-A7. In the closeout
  log, map each BF-A requirement to its evidence and record the carried
  items from step 7.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/test_verify.py tests/test_validate_plan_frontmatter.py tests/test_validate_targets.py -q
echo "fb1bc6909ac3ef82d5c22106e32ef682b0cff66788fa915fb9b53b15c9d2f3ab  shared/third_party/ponytail/LICENSE" | sha256sum -c -
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
for f in CLAUDE.md AGENTS.md dist/multi-agent/CLAUDE.md dist/multi-agent/AGENTS.md; do grep -qF "is derived context, never authority over source, tests, or policy. Refresh only by calling OpenWiki's own MCP tools per" "$f" || exit 1; done
! grep -nF -e "just-in-time repository context" -e "transition scope" -e "Project State" CLAUDE.md AGENTS.md scripts/generate_targets.py dist/multi-agent/CLAUDE.md dist/multi-agent/AGENTS.md shared/policies/workflow.instructions.md shared/skills/onboard/SKILL.md shared/skills/setup-project/SKILL.md shared/skills/create-feature/SKILL.md
! grep -nF "—" openwiki/INSTRUCTIONS.md
! grep -n "^status: in-progress" .claude/plans/codex-gpt-5.6-model-tiering.md .claude/plans/preserve-consumer-memory.md .claude/plans/2026-07-18_phase-A-preserve-consumer-memory.md .claude/plans/2026-07-18_phase-B-configure-codex-gpt-5.6.md
grep -qF -e '- [x] `2026-10-03_phase-D-behavioral-pilot-knowledge-refresh`' .claude/plans/behavioral-evaluation-pilot.md
! grep -nF -e "Nothing below is fixed yet" -e "Plan 2 remains a deferred proposal" .claude/explorations/2026-10-02_sidecar-workflow-profile-hands-on-review.md .claude/explorations/2026-10-02_bootstrap-engineering-workflow/README.md
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Reviewer inspection of the nested AI-state diff: confirm that only the
  status lines, frontmatter fields, Resolution notes, and the one pilot
  phase line named in steps 1 and 7 changed, and that no session log,
  findings report, or receipt changed.

## Review Profiles

Use `.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record the three pause fields, and create a session log
with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it
does not require final findings, LEARN, DOCUMENT, or a completed closeout.
After the checkpoint commit, it may be pushed as a durable remote backup when
paused-publication invariants pass. It remains unfinished and blocks PR creation
and final closeout.
Keep the big plan `in-progress` with the same `current_phase`. On resume, read
the pause log and Git state, restore this plan to `in-progress`, and continue
this same phase without creating another small plan.
