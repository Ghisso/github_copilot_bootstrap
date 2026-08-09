# Session: Graphify Phase 0 Step 7 cross-project supplement

**Date:** 2026-08-09
**Plan:** [.claude/plans/2026-08-09_phase-0-graphify-compatibility-and-value-gate.md](../plans/2026-08-09_phase-0-graphify-compatibility-and-value-gate.md)
**Status:** COMPLETED

## Goal

Execute the user-authorized Step 7 supplement that a previous session could not
run, testing exactly `graphifyy==0.9.35` read-only against `/home/ghisso/work/RAG`
and `/home/ghisso/work/git_projects/industrial-inspection`, then close Phase 0
with one unambiguous decision. The prior session was blocked by sandbox DNS plus
an approval-service usage limit, not by a Graphify result.

## Work Log

- **PRE-FLIGHT** - Read big plan, Step 7, and the existing evidence artifact.
  Captured exact initial state of both consumers (branch, HEAD, status, staged
  and unstaged diff names, untracked files, nested `.claude`, SHA-256 of every
  dirty file). Both matched the handoff exactly; both nested `.claude` clean.
- **Guard diagnosis** - The Bash guard denied a multi-line capture script with
  `protect-files.sh exited with status 2`. Read the classifier and found this is
  `AmbiguousCommand` fail-closed behavior for unparseable shell, working as
  designed. Moved complex logic into script files invoked as `bash script.sh`
  rather than routing around the guard.
- **Acquisition** - Resolved the external blocker: fetched
  `graphifyy==0.9.35` from PyPI and pinned it into a disposable
  `python:3.12-slim` image with no extras (base deps are tree-sitter, networkx,
  numpy, rapidfuzz only; no MCP, LLM, document, or media backend).
- **Execution** - Ran every operation under `docker --network none`, consumer
  source mounted `:ro`, output and cwd on task-owned `/tmp` mounts. Cold
  extraction: RAG 10.40 s (8 302 nodes / 17 739 edges, 17.90 MiB);
  industrial-inspection 2.79 s (1 390 / 3 591, 3.46 MiB). No `graphify update`
  against consumers, no `--no-gitignore`, no installer/hook/MCP/LLM operation.
- **Scoring** - RAG 0/3, industrial-inspection 2/3. Every accepted relationship
  confirmed at exact source lines; one lexical false lead
  (`join_prefix()` in `hf-ai-sync.py`) identified and rejected rather than
  accepted. Cross-project override requires both projects at >= 2/3, so it fails.
- **VERIFY** - Independent verifier returned VERIFIED on all six dimensions:
  17 citations matched source, both consumers byte-identical, cleanup surgical,
  outer repo boundary intact, internal logic consistent.
- **REVIEW** - Unified reviewer, two passes, profiles architecture, security,
  tests, documentation, performance. Gate WARN: 0 critical, 3 major, 2 minor.
  Findings were correct, including that RAG Q2 had been scored FAIL without the
  budget escalation applied to industrial-inspection.
- **Remediation** - Rebuilt the image (identical digest), re-extracted RAG
  (reproduced exactly), re-ran Q2 at `--budget 30000` plus two `affected` calls
  and one `path`. Added positive controls for both sandbox boundaries. Recorded
  literal argv for all six questions and both extractions. Removed the
  unsupported cwd causal claim. Added the top-level cross-reference.
- **Cleanup** - Two rounds, exact paths only. All `/tmp/graphify-step7*` paths
  and the disposable image removed; the three pre-existing earlier-phase caches
  verified present and untouched. Consumers re-captured a third time and still
  byte-identical.

## [LEARN] Entries

Recorded in `.claude/MEMORY.md`:

- [LEARN:architecture] AST symbol graphs cannot model string-keyed wiring,
  `import_module` shims with `sys.modules` rebinding, or f-string identities.
- [LEARN:quality] Score a candidate tool at its best reasonable effort, not its
  default; asymmetric escalation biases a comparison.
- [LEARN:quality] State a gate result's robustness to its borderline call.
- [LEARN:security] Prove sandbox boundaries with positive controls, not exit codes.
- [LEARN:workflow] Never write a cleanup claim before performing the action.
- [LEARN:tooling] The fail-closed Bash guard's exit 2 on complex shell is by
  design; use script files instead of bypassing it.

## Verification Results

```bash
uv run python .claude/scripts/record_findings.py . --profile architecture \
  --profile security --profile tests --profile documentation \
  --profile performance --phase 2026-08-09_phase-0-graphify-compatibility-and-value-gate \
  --base-ref dev --findings-json <findings> \
  --out .claude/quality_reports/findings-20260809T111009Z-phase-0.json
# recorded 5 finding(s): 0 critical, 3 major, 2 minor

uv run python .claude/scripts/quality_score.py . \
  --phase 2026-08-09_phase-0-graphify-compatibility-and-value-gate \
  --base-ref dev --json --out .claude/quality_reports/score-20260809T111009Z-phase-0.json
# score 100, gate EXCELLENCE
# pytest: 156 passed in 35.95s
# mypy: Success: no issues found in 19 source files
# ruff: 0 violations
# changed_files: [] (Phase 0 changes nothing tracked, by design)
```

## Score: 100/100

Gate EXCELLENCE. All 5 review findings resolved before closeout; 0 critical.

## Decision

**Phase 0 closes NO-GO.** The cross-project override failed because RAG scored
0/3 against a required 2/3, and the override needs both consumers to pass
independently. Phases A through F remain unauthorized. No adapter, dependency,
routing surface, generated output, hook, or MCP configuration may be added for
this result.

The conclusion is supported twice over and is robust to the one borderline call:
the original bootstrap-only test scored 1/3, and even if RAG Q2 were scored PASS
the project would reach only 1/3.

## Open Questions / Next Steps

- The nested `ai-state` repo has a stale `.git/rebase-merge` directory from the
  aborted 10:35Z sync. Local is 0 behind / 6 ahead of `origin/ai-state`, so
  there is no real conflict, but every `state-sync pull` fails with "there is
  already a rebase-merge directory" and state is not publishing. Clearing it is
  a git recovery action outside Phase 0 scope and needs the user's decision.
- No outer commit was created: Phase 0 is closed by nested AI-state checkpoint
  only, per the plan. No push and no PR were performed.
- The big plan's `current_phase` stays at Phase 0 and the big plan should move
  to a stopped/closed state rather than advancing, since A-F are unauthorized.
