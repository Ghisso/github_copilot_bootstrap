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

## Stale-claims surfaces checked

## [LEARN] Entries

## Verification

```text
# filled at closeout step 4
```

## Open Questions / Next Steps
