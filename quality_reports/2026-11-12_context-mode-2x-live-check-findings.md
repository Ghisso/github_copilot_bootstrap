# Quality Report — context-mode-2x-migration_implementation (reopen)

**Date:** 2026-11-12
**Branch:** context-mode-2x-migration_implementation
**Phase:** none (big plan complete at `7895856`; findings that reopen it)
**Base Ref:** dev
**Status:** FAIL (one functional defect found after completion)

---

## Summary

Live client checks after the three completed phases (`.claude/explorations/2026-11-12_context-mode-2x-live-checks/REPORT.md`) found one defect that the user asked to fix on this branch before the pull request ("fix problem 1"). Completed phases A (`51d89b9`), B (`3f2f48d`), and C (`7895856`) each passed `verify phase`, `verify closeout`, and a clean second review round; their artifacts are not changed by this reopen.

---

## Findings

| # | Severity | Finding | Evidence | Disposition |
|---|---|---|---|---|
| 1 | MAJOR | `context-mode-mcp-filter.mjs` refuses `tools/list` and `tools/call` with `-32001` whenever `serverAccepted` is false, including while a client's `initialize` is pending. A client that sends `tools/list` before the `initialize` reply arrives gets no tools for the whole session. Claude Code 2.1.226's newer MCP client path did this in one live run (`Failed to fetch tools: Context Mode server is not initialized`, 3 ms after connecting, `protocolEra: "modern"`). | Live run debug log; deterministic reproduction `pipeline_probe.py` (requested versions `2025-11-25` and `2026-07-28`). Pre-existing: the 1.x filter had the same rule. | Fix on this branch: reopened plan, new Phase D. |
| 2 | MINOR | Codex treats `ctx_index` (no `readOnlyHint` from 2.1.8) as needing approval; `codex exec` with `approval_policy=never` cancels it. | Live Codex run; capture shows `ctx_index` without annotations. | Not fixed: correct labeling; an interactive Codex session asks. A per-tool Codex approval setting would change a root adapter and needs its own plan. |
| 3 | MINOR | Two code comments overstate rules: `context-mode-dispatch.sh` lines 17-20 ("never ... restores anything" at the root) and `context-mode-mcp-filter.mjs` lines 13-14 ("naming no other tool"). | Phase C review rounds 1 and 2. | Fix as comment-only edits in Phase D (the filter is edited there anyway). |
| 4 | MINOR | Five OpenWiki pages outside the Phase C run cite drifted line ranges. | Phase C review. | Not in scope; a later refresh. |

---

## Reopen record

Per `workflow.instructions.md` "Reopening a completed big plan": the branch exists and is unmerged; new phases D (fix) and E (`-knowledge-refresh`, required because the plan already has knowledge-refresh phases) are appended as `planned`; the big plan returns to `in-progress` with `current_phase` set to Phase D.
