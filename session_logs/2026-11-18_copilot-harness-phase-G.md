# Session: Copilot harness migration, Phase G (knowledge refresh and final audit)

**Date:** 2026-11-18
**Plan:** `.claude/plans/2026-11-17_phase-G-knowledge-refresh.md`
**Status:** COMPLETED

## Goal

Final phase of the plan. Refresh the OpenWiki pages (the generated
repository wiki) for the changes of Phases A to F, inspect the generated
pages against the code they cite, and run the standing final-phase audit
of the live-advice surfaces for statements this plan made outdated.

## Work Log

- **07:46** - Phase F committed as `adfe3bc` and pushed; the commit hook
  activated Phase G.
- **07:50** - Order of work, a deviation from the plan's step order: the
  audit of the surfaces outside `openwiki/` runs first, the wiki refresh
  second, the inspection of the generated pages third. Reason: the wiki
  pages cite line ranges of the docs and policy files, so those files
  must be final before OpenWiki reads them; a refresh before the audit
  would leave fresh pages with stale citations. Two more points:
  - The OpenWiki skill forbids page sub-agents, so the orchestrator
    writes the wiki pages itself. The plan's step 1 names the `coder` for
    page writing; the `coder` does the audit instead.
  - Edits to `.claude/MEMORY.md` and to the project context file are made
    by the orchestrator, which owns the AI state; the `coder` reports what
    it finds there.
  - Not in this phase: the bare evidence labels in comments of
    `subagent-context.sh`, `run-hook.sh`, and some test docstrings. They
    are code, not a live-advice surface, and a change there would move the
    line ranges the wiki cites. Recorded as a follow-up with the two old
    defects of the guard hooks.
- **07:52** - Audit delegated to a fresh `coder`.
- **08:20** - Audit done. Four statements corrected in four tracked files:
  `docs/native-client-acceptance.md` (it said Copilot stays covered by
  the generated-target checks; it now says its command does not cover
  Copilot and points to the Copilot runtime check and the manual
  checklist), `shared/skills/knowledge-refresh/SKILL.md` (the wording on
  OpenWiki's `copilot` integration), `SECURITY.md` (the trust paragraph
  named only Codex and Claude), and `README.md` (the notes on upgrading a
  consumer had no word on the guard changes). The `coder` reported 9
  items for `.claude/MEMORY.md`, 9 for the project context file, and 28
  stale or missing statements on 9 wiki pages. Its full suite run: 5,927
  passed, 1 skipped.
- **08:25** - The orchestrator applied the proposals to
  `.claude/MEMORY.md` (the Copilot harness entry rewritten to state the
  current behavior first; the entry on turning hooks off limited to the
  Local harness; the tool-names entry and the sidecar discovery entry
  extended; five new entries for the shell helper tools, the inherited
  `COPILOT_CLI`, VS Code's tool set for each model, the reason against a
  stand-down on the Local harness, and the trade-off of option B) and to
  the project context file (layout, design decisions, status, open
  follow-ups, what a refresh brings, the runtime version, and a caveat on
  evidence labels).
- **08:31** - OpenWiki refresh by the orchestrator: `openwiki_begin` with
  mode `update`, a plan of eight pages, eight page jobs, and
  `openwiki_finish` returned `complete`. After `openwiki_begin`, root
  `AGENTS.md` and `CLAUDE.md` had no change. After the run there is no
  `openwiki/.run.json` and no managed block in either root file. Pages:
  `architecture/hooks-and-guardrails.md` (a new section on the two hook
  files of the Copilot harness and the seven stand-down conditions; the
  five events of the Copilot hook file; the answer shape; patch text, the
  `Read` name, the search tools' `paths`, the two workflow tools; the
  three modes of the reminder; the sub-agent hook),
  `architecture/agents-and-skills.md`,
  `architecture/source-generated-consumer-layout.md`,
  `operations/deterministic-verification.md` (the budgets 900 and 1,020),
  `operations/git-backed-ai-state-sync.md`,
  `operations/install-ownership-and-runtime-checks.md` (a new section on
  the opt-in Copilot runtime check), `operations/sidecar-overlay.md`, and
  `quickstart.md`. All 14 claims that OpenWiki had marked stale or
  unresolved were rechecked against the current source and resubmitted
  with current line ranges; new claims were added for the new text. Each
  line range came from a search made in the same job.
- **08:33** - Orchestrator checks: `validate_targets.py` exit 0,
  `validate_plan_frontmatter.py` exit 0, `verify.py fast` PASS; the three
  text checks of the plan's Verification block hold. Scope-change record
  added to the small plan. Review round 1 started with six profiles.
- **08:44** - Review round 1: every changed wiki sentence the reviewer
  opened against its source matched, and the audit list covers every
  surface. Gate FAIL on two MAJOR, both false statements that stayed: on
  the sidecar wiki page, the reason for shipping no `.github/agents` file
  still said Copilot has no way to find an agent in an ignored file, which
  the page's own new text contradicts; and the project context file still
  said no implementation branch is unmerged. Six MINOR: four statements
  in `.claude/MEMORY.md` without a basis or a "not run" label; "Copilot
  harness" used before its definition on four wiki pages; "starts with
  the marker" where the marker is an environment prefix on the launcher
  call; "and the wiki" in a context-file sentence on bracket labels;
  `SECURITY.md` not saying that VS Code's own trust prompt was not run;
  and two pages repeating the hooks page at length.
- **08:48** - All eight fixed. The wiki fixes went through a second scoped
  OpenWiki run (mode `update`, seven pages, `openwiki_finish` returned
  `complete`; no `openwiki/.run.json`, no managed block in the root
  files). The hooks page also says now that the launcher stands down no
  other script, so another Claude-settings hook such as
  `record-branch-state.sh` still runs on the Copilot harness. Open point,
  not checked: whether that script is safe to run twice there.
  `validate_targets.py` exit 0 and `verify.py fast` PASS. Review round 2
  started.
- **08:52** - Review round 2: Gate PASS, no open request. Three MINOR, all
  fixed: on the quickstart page the definition of the two harnesses had
  run into a table cell that lists files; the sidecar page pointed to a
  section by a wrong name; `SECURITY.md` used "Copilot harness" without
  an explanation. From the reviewer's notes: the rules of
  `subagent-context.sh` on the hooks page got a claim of their own again,
  and the open point on `record-branch-state.sh` went into the project
  context file. The wiki fixes went through a third scoped OpenWiki run
  (three pages, `openwiki_finish` returned `complete`).
- **08:56** - Review round 3: Gate PASS, no finding, no open request.

### Phase-boundary summary

- **Objective and change:** the generated wiki and the live-advice
  surfaces match the state after Phases A to F. Changed in the repository:
  eight wiki pages with their claim files, the two index pages, the page
  manifest and `openwiki/.last-update.json` (all written through
  OpenWiki's tools); `README.md` (one bullet in the notes on upgrading a
  consumer), `SECURITY.md` (the trust paragraph),
  `docs/native-client-acceptance.md`, and
  `shared/skills/knowledge-refresh/SKILL.md`. Changed in the AI state:
  `.claude/MEMORY.md` and the project context file. No code changed.
- **Deviations:** the Scope-change record under step 3 of the small plan.
- **Checks:** the required items below; three OpenWiki runs, each ended
  with `complete`; no `openwiki/.run.json`; no managed block in root
  `AGENTS.md` or `CLAUDE.md`.
- **Open findings:** none.
- **Open points for the user (none blocks the plan):** run the manual
  checklist in `docs/smoke-tests.md`; read the `macos-latest` job of the
  `Validate` workflow; decide on one small plan for the two old defects of
  the guard hooks; keep, narrow, or lift the deny of the two workflow
  tools; add an item for the Copilot harness to `openwiki/INSTRUCTIONS.md`;
  open a pull request to `dev` when wanted.
- **Next operation:** none in this plan. It is the last phase; the commit
  hook sets the big plan to `status: complete`.

## Stale-claims surfaces checked

The standing final-phase audit. The `coder`'s table with the search terms
and the files read in full is `raw/phase-G-audit.md` in the evidence
folder `.claude/explorations/2026-11-17_copilot-harness-migration-evidence/`.

- Root guidance `CLAUDE.md` and `AGENTS.md`: searched for the Copilot,
  hook, reminder, sub-agent, and time-budget statements; no stale
  statement.
- `README.md`: rewritten in Phase F. One gap found and closed: the notes
  on upgrading a consumer had no word on the guard changes; a bullet lists
  the two new denies and the three looser decisions.
- `SECURITY.md`: the trust paragraph named only Codex and Claude. It now
  states what the offline run on the Copilot runtime showed and that VS
  Code's own trust prompt was not run.
- `docs/` except dated documents: `docs/architecture.md`,
  `docs/runtime-checks.md`, `docs/smoke-tests.md`,
  `docs/target-mapping.md`, `docs/sidecar-provider-contract.md` (current
  after Phase F; no stale statement). `docs/native-client-acceptance.md`
  said Copilot stays covered by the generated-target checks; corrected to
  say that its command does not cover Copilot, with pointers to the
  Copilot runtime check and the manual checklist.
- Dated records, left unchanged: root `plans/`, the files `docs/2026-*`,
  `docs/plan-deterministic-commit-gate.md`, `docs/evidence/`, and the
  closed session logs of Phases A to F. No entry in a closed log was found
  that would mislead a reader, so no erratum was written.
- Canonical policy source `shared/policies/` (12 files): no stale
  statement; `workflow.instructions.md` states the 1020-second item
  budget. The generated copies under `.claude/instructions/` follow from
  it.
- Canonical skill source `shared/skills/`: `knowledge-refresh/SKILL.md`
  corrected (what OpenWiki's `copilot` integration writes; that the
  Copilot hook file has no `openwiki-guard.sh` entry); no stale statement
  in the other skills.
- `shared/agents/`, `shared/templates/`, `shared/review-profiles/`,
  `shared/sidecar/`: no stale statement.
- State READMEs: the sources under `shared/plans/`,
  `shared/session_logs/`, `shared/quality_reports/`, the four sidecar
  state READMEs, the explorations README text in
  `scripts/generate_targets.py`, and the two MEMORY seeds: no stale
  statement.
- `.github/`: `workflows/validate.yml` and the generated
  `.github/copilot-instructions.md`: no stale statement.
- Other shipped text: `shared/devcontainer`, `shared/mcp`,
  `shared/vscode`, `shared/prompts`, `shared/schemas`, `shared/scripts`,
  `targets/`, `.vscode/mcp.json`, `.codex/config.toml`: no stale
  statement.
- Active plans: the big plan and this phase's plan hold no statement that
  this plan made false; the big plan's two dated corrections (the item
  limit; row B of the options table) stand.
- `.claude/MEMORY.md`: the Copilot harness entry was rewritten to state
  the current behavior first; the entry on turning hooks off is limited
  to the Local harness; the tool-names entry and the sidecar discovery
  entry are extended; five entries are added (the shell helper tools, the
  inherited `COPILOT_CLI`, VS Code's tool set for each model, the reason
  against a stand-down on the Local harness, the trade-off of option B).
  After review, four statements got their basis or a "not run" label.
- Project context file
  (`.claude/instructions/project-context.instructions.md`): the layout,
  the design decisions, the status, the open follow-ups, what a refresh
  brings to a consumer, the runtime version, and a caveat on evidence
  labels are updated. After review, a sentence that said no
  implementation branch is unmerged was corrected.
- `openwiki/`: eight pages refreshed through OpenWiki's tools in three
  runs (`architecture/hooks-and-guardrails.md`,
  `architecture/agents-and-skills.md`,
  `architecture/source-generated-consumer-layout.md`,
  `operations/deterministic-verification.md`,
  `operations/git-backed-ai-state-sync.md`,
  `operations/install-ownership-and-runtime-checks.md`,
  `operations/sidecar-overlay.md`, `quickstart.md`). No stale statement:
  `operations/context-mode-dispatcher.md`,
  `workflows/lifecycle-and-task-lanes.md`, and the index pages.
  `openwiki/INSTRUCTIONS.md`, the user's brief, has no item for the
  Copilot harness; reported to the user, not edited.
- Not a live-advice surface, recorded as a follow-up: comments in
  `run-hook.sh`, `subagent-context.sh`, and `protect-files.py`, and some
  test docstrings, cite the private evidence report by bare labels.

## [LEARN] Entries

- [LEARN:workflow] In a knowledge-refresh final phase, audit the docs,
  policies, and skills first and refresh the wiki second; the
  orchestrator writes the wiki pages, because the OpenWiki skill forbids
  page sub-agents. Recorded in `.claude/MEMORY.md`.
- [LEARN:documentation] After adding a new fact to a wiki page, search
  the page for an older sentence that says the opposite; fix a generated
  page after review through a new scoped run; keep a claim for each rule
  a page states. Recorded in `.claude/MEMORY.md`.
- No lesson recorded for: the file guard refusing a search command whose
  pattern names an agent folder (the existing entry on commands that name
  a protected path covers it).

## Verification

```text
PASS        0.3s  uv run python scripts/generate_targets.py --all
PASS        0.0s  test ! -e openwiki/.run.json
PASS        0.0s  test "$(grep -c -F '<!-- OPENWIKI:START -->' AGENTS.md)" = "0"
PASS        0.0s  test "$(grep -c -F '<!-- OPENWIKI:START -->' CLAUDE.md)" = "0"
PASS        0.0s  grep -q -F 'SubagentStart' openwiki/architecture/hooks-and-guardrails.md
PASS        0.0s  grep -q -F 'Copilot harness' openwiki/architecture/hooks-and-guardrails.md
PASS        0.0s  grep -q -F 'check_copilot_runtime.py' openwiki/operations/install-ownership-and-runtime-checks.md
PASS       44.5s  uv run python scripts/validate_targets.py
PASS        0.9s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS      615.0s  uv run python .claude/scripts/verify.py phase --format text
closeout: PASS
```

- Phase receipt: `verify.py phase --persist` PASS (Ruff, mypy, pytest with 5927 passed and 1 skipped in 424.56 s, freshness, provenance, generation). In the dry run the item `verify.py phase` took 615.0 s of wall time, against 425 to 435 s in the earlier phases; pytest's own time was unchanged, so the extra time fell after its result line. The budget for one command is 900 s.

- Findings: `.claude/quality_reports/findings-2026-11-17_phase-G-knowledge-refresh.json`
  (no surviving finding; gate PASS; six profiles; round 1 FAIL with two
  MAJOR and six MINOR, round 2 PASS with three MINOR, all fixed before
  round 3, which had no finding).
- optional 1: PASS — the orchestrator wrote each changed sentence from the source it read in the same page job, and the reviewer opened the source for every changed sentence on the eight pages; the two mismatches it recorded (the reason sentence on the sidecar page, and where the marker sits in a Claude settings hook command) were fixed through a second scoped run and confirmed in review rounds 2 and 3.

## Open Questions / Next Steps

- The plan is complete with this phase's commit. A pull request to `dev`
  is opened only when the user asks.
- For the user: the manual checklist in `docs/smoke-tests.md` (section
  "VS Code Copilot harness (manual)"), in the test folder
  `~/copilot-harness-probe-20261117`.
- For the user: the result of the `macos-latest` job of the `Validate`
  workflow.
- For the user: one small plan for the two old defects of the guard hooks
  (inline Python without `-I`; the temp-file leak of `protect-files.sh`),
  which can also replace the bare evidence labels in code comments and
  check `record-branch-state.sh` on the Copilot harness.
- For the user: keep, narrow, or lift the deny of the two workflow tools;
  add an item for the Copilot harness to `openwiki/INSTRUCTIONS.md`.
