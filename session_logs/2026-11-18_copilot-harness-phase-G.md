# Session: Copilot harness migration, Phase G (knowledge refresh and final audit)

**Date:** 2026-11-18
**Plan:** `.claude/plans/2026-11-17_phase-G-knowledge-refresh.md`
**Status:** IN-PROGRESS

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

## Stale-claims surfaces checked

## [LEARN] Entries

## Verification

```text
# filled at closeout step 4
```

## Open Questions / Next Steps
