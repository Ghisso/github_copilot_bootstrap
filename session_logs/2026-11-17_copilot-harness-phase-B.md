# Session: Copilot harness migration, Phase B (tool inputs in the file guard)

**Date:** 2026-11-17
**Plan:** `.claude/plans/2026-11-17_phase-B-copilot-tool-inputs.md`
**Status:** IN-PROGRESS

## Goal

Fix the four kinds of Copilot-harness tool input that the file guard
(`shared/hooks/scripts/protect-files.py`) misreads: patch text (the urgent
one: file edits fail in the real VS Code whenever the chosen model uses the
patch tool), the shell helper tools, the read tool's PascalCase name, and
the search tools' `paths` list. Give every runtime tool a recorded handling.

## Work Log

- **19:50** - Phase A committed as `d34779a` and pushed; the commit hook
  activated Phase B. No re-planning needed: Phase A changed nothing that
  later phases rely on, except that the probe's temporary project removes
  the MCP server file, its mirror copy, and its manifest line (Phase A
  Scope-change record).
- **19:55** - Phase B delegated to a fresh `coder` with the evidence packet
  (the small plan, the big plan's decision-change table, the evidence
  folder's raw files, and the Phase A probe structure).

## [LEARN] Entries

- [LEARN] none - no new lessons this session

## Verification

```text
# filled at closeout step 4
```

## Open Questions / Next Steps

- Next: review Phase B with the six profiles, then closeout.
