# Session: Engineering workflow Phase C — knowledge refresh and live-advice audit

**Date:** 2026-10-02
**Plan:** `.claude/plans/2026-10-02_phase-C-engineering-knowledge-refresh.md`
**Status:** IN-PROGRESS

## Goal

Run the standing final-phase documentation, memory, and LEARN audit for the
whole `engineering-workflow-improvements` plan, correct stale live advice,
then refresh the enabled OpenWiki layer through its own MCP lifecycle. This
is the plan's last phase; its closeout log must carry
`## Stale-claims surfaces checked`.

## Work Log

- **Resume** - Phase B committed (`1d0ead1`) and pushed; the post-commit
  hook set `current_phase` to Phase C and Phase C `in-progress`.
- **Order** - The audit and its source fixes run before the OpenWiki
  refresh. OpenWiki's skill forbids source edits while a refresh is open, and
  fixing first avoids a second refresh for pages the fixes would stale. The
  plan allows a second refresh but does not require this order; recorded as
  a deliberate ordering choice.
- **Known stale advice (from Phase B review)** - Generated full templates
  `session-log.md`, `plan-big.md`, `plan-small.md` point to
  `shared/policies/workflow.instructions.md`, which does not exist in a
  consumer (`.claude/instructions/workflow.instructions.md` does).
  `shared/sidecar/workflow/templates/plan-small.md` ends with three orphan
  lines about a pause log the relaxed sidecar does not have.
- **Audit (documenter)** - Swept the live-advice surfaces listed below.
  One correction: README's sidecar "relaxed loop" text implied the planner
  and reviewer save files themselves; it now says the caller saves their
  returned text. No other stale claim; reported the two known `shared/`
  items for routing.
- **Audit (orchestrator, MEMORY)** - Corrected one entry in place: the
  auto-mode denial of `install_bootstrap.py . --allow-self --local-only` was
  not reproduced (the refresh ran twice in auto mode this session). No other
  MEMORY entry contradicts this plan's changes.
- **Audit fixes (coder)** - Three full templates now point to
  `.claude/instructions/workflow.instructions.md` (the generator copies
  templates verbatim, `scripts/generate_targets.py:353`); the sidecar
  `plan-small.md` orphan pause-log lines are deleted (the full template keeps
  its pause text, which the full install supports). New regression test
  `test_rendered_templates_carry_no_stale_authoring_paths_or_pause_text`;
  reverting either fix fails it.
- **OpenWiki refresh** - `openwiki_begin` in `update` mode (run
  `78bd8306-edee-4334-9591-01f2b1f1ce42`); root adapters unchanged after
  begin. Planned 2 pages from the 4 flagged claims:
  `architecture/agents-and-skills.md` (2 claims revised, 1 confirmed, 6
  new; new "Requirement authority and evidence" section) and
  `workflows/lifecycle-and-task-lanes.md` (1 revised, 2 new). Other pages
  checked and not planned: none describe what this plan changed
  ("planner" in `sidecar-overlay.md` is `sidecar_overlay.py`'s planner
  function). `openwiki_finish` returned `complete`; no `openwiki/.run.json`
  left; no workflow file added.
- **VERIFY** - After `generate_targets --all` and the self-overlay
  refresh: `validate_targets.py`, `check_runtime.py`,
  `validate_plan_frontmatter.py`, `verify.py fast` all exit 0; both pytest
  groups together 1460 passed.
- **REVIEW round 1** - Fresh `reviewer`, six profiles. Gate WARN: 0
  CRITICAL, 0 MAJOR, 4 MINOR, one open request (the full `verify.py phase`
  result on the final tree, not only `verify.py fast`). Reviewer checked 65
  claim line ranges by hash (61 exact; 4 older off-by-one ranges in
  `scripts/validate_targets.py`, not from this diff) and found the wiki
  prose accurate with no behavioral overclaim. MINORs: C-#1 the sidecar
  `plan-small.md` header still claims hooks and lists pause fields; C-#2
  both `plan-big.md` templates name authoring-only `scripts/...` commands
  and `skill-template.md` names only `shared/skills/`; C-#3 the shipped
  `code-review` skill cites `shared/policies/...`, so the audit line for
  `shared/skills/` was wrong; C-#4 two claim-evidence gaps (statements true).
  Decisions: fix C-#1..#3 in one coder round, without shifting any cited
  wiki line range; accept C-#4 (statements verified true against source;
  claim ranges change only through an OpenWiki update; fold into the next
  refresh).
- **FIX LOOP round 2** - Coder fixed C-#1..#3 (sidecar plan-small header,
  both plan-big Verification blocks, skill-template, code-review skill) and
  broadened the template test (`AUTHORING_ONLY_TEXT`); edits avoid every
  cited wiki line range. Open request answered: after regeneration and the
  self-overlay refresh, `verify.py phase --format text` (no persist) exit 0
  with ruff 0 violations, mypy 0 errors, pytest 2325 passed; the Phase C
  Verification block items all exit 0. Round-2 delta sent to the same
  reviewer.
- **REVIEW round 2** - Gate PASS; C-#1..#3 confirmed fixed; open request
  closed. One new MINOR: the `skill-template.md` line-4 edit fell inside the
  cited range `#L1-L14` of agents-page claim `claim_11607a59`, so the
  orchestrator's "edits avoid every cited range" premise was wrong for that
  file. Disposition: fixed by reverting that hunk by hand (file now
  byte-identical to HEAD); no second OpenWiki refresh. The skill-template
  "installed project" wording is a follow-up for the next change that
  refreshes the agents page. Checks after the revert all exit 0. Round 3
  (revert confirmation) sent to the same reviewer.

## [LEARN] Entries

- Pending closeout.

## Stale-claims surfaces checked

- `README.md` - corrected: sidecar relaxed-loop text now says the caller
  saves the planner's and reviewer's returned text (diagram node "planner
  drafts a plan"). Phase A and B sentences (~1238-1244) match source.
- `CLAUDE.md`, `AGENTS.md` - no stale claim (lifecycle and lane text match
  `shared/policies/workflow.instructions.md`); not edited (control-plane).
- `docs/architecture.md`, `docs/target-mapping.md`, `docs/smoke-tests.md`,
  `docs/runtime-checks.md`, `docs/native-client-acceptance.md`,
  `docs/plan-deterministic-commit-gate.md` - no stale claim.
- `docs/sidecar-provider-contract.md` and `docs/2026-*.md` - dated records,
  left unchanged (the old `.claude/ai-bootstrap/` row is explicitly
  superseded in the same document).
- State READMEs (`.claude/plans/`, `.claude/session_logs/`,
  `.claude/quality_reports/`, `.claude/explorations/`) - no stale claim.
- `.claude/instructions/project-context.instructions.md` - no stale claim;
  its dated "Current status" note left as a dated record.
- `shared/policies/`, `shared/agents/`, `shared/review-profiles/`, sidecar
  state READMEs - no stale claim.
- `shared/skills/` - corrected (found by review round 1, missed by the first
  sweep): `code-review/SKILL.md` cited the authoring-only
  `shared/policies/workflow.instructions.md`; now
  `.claude/instructions/workflow.instructions.md`. Other skills: no stale
  claim.
- `shared/templates/{session-log,plan-big,plan-small}.md` - corrected:
  authoring-only `shared/policies/...` path replaced with the consumer path;
  the full `plan-big.md` Verification block now uses
  `.claude/scripts/verify.py fast` instead of authoring-only `scripts/...`
  commands. `skill-template.md` - stale (names only `shared/skills/`) but
  left unchanged: its lines 1-14 are cited OpenWiki evidence, so a fix waits
  for the next change that refreshes the agents page.
- `shared/sidecar/workflow/templates/plan-small.md` - corrected: orphan
  pause-log lines removed; header no longer claims hooks or lists pause
  status and fields. `plan-big.md` - Verification block now asks for the
  project's own commands instead of authoring-only `scripts/...`.
- `scripts/install_bootstrap.py --help` - no stale claim.
- `.claude/MEMORY.md` - corrected one entry in place (auto-mode refresh
  denial not reproduced); no other entry contradicted.
- `openwiki/**` - refreshed through OpenWiki's MCP lifecycle (two pages).
- Completed plans, closed session logs, receipts, and calibration evidence
  - dated records, left unchanged; no historic self-audit PASS reworded.

## Verification

```text
# verify closeout --format text summary lines
# verify.py phase/closeout receipt path
```

## Open Questions / Next Steps

- Audit, source fixes, OpenWiki refresh, then VERIFY, REVIEW, CLOSEOUT.
