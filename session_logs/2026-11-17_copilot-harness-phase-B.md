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

## Differential battery (plan step 9)

The guard from `dev` (`2e8c7bb`) against the working copy: 1,158 payloads on
4 clients, 4,632 runs for each guard. Compared: the parsed
`permissionDecision` and the exit code. 314 runs differ, and every one
belongs to a row of the big plan's decision-change table; 0 are
unexplained. For the 4,318 identical runs the output bytes are identical
too. Under Python 3.9.0 the new guard gave the same result as the default
`python3` in all 4,632 runs.

| Decision-change row | Differences | What they are |
| --- | --- | --- |
| L1 | 16 | `Read` on a hook or agent file: ask (Copilot, Claude) or deny (Codex, Antigravity) became no decision. The `.env` rows are identical. |
| L2 | 20 | `read_bash`, `list_bash`, `stop_bash` with no `command`: a stop (exit 2) became no decision, or a deny for a path key that names `.env`. |
| L3 | 148 | Patch text: a stop became the decision of its targets. |
| T1 | 48 | `grep`, `rg`, `glob` with a secret-shaped `paths` entry: no decision became deny. |
| T1 (the key `paths` is global) | 12 | Tools that are not search tools but carry a `paths` list are now judged by path. |
| T2 | 64 | Patch headers with leading blanks, inner blanks, or another letter case, and hunk context lines that spell a header. |
| T4 | 6 | `run_dynamic_workflow` and `dynamic_workflows_manage`, on `github-copilot` only. |

The full table of all 314 rows, with notes on each class, is
`.claude/explorations/2026-11-17_copilot-harness-migration-evidence/raw/phase-B-differential.md`.

## [LEARN] Entries

- [LEARN] none - no new lessons this session

## Verification

```text
# filled at closeout step 4
```

## Open Questions / Next Steps

- Next: review Phase B with the six profiles, then closeout.
