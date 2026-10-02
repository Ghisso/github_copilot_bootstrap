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

## [LEARN] Entries

- Pending closeout.

## Stale-claims surfaces checked

- Pending audit.

## Verification

```text
# verify closeout --format text summary lines
# verify.py phase/closeout receipt path
```

## Open Questions / Next Steps

- Audit, source fixes, OpenWiki refresh, then VERIFY, REVIEW, CLOSEOUT.
