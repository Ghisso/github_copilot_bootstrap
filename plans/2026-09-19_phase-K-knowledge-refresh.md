---
name: 2026-09-19_phase-K-knowledge-refresh
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 13
status: complete
closeout_session_log: .claude/session_logs/2026-09-19_openwiki-phase-K-knowledge-refresh.md
---

# Small Plan: 2026-09-19_phase-K-knowledge-refresh

## Scope

The knowledge-refresh final phase defined in `workflow.instructions.md` ("Knowledge-Refresh
Final Phase"), applied to this big plan: one host-driven OpenWiki update after the Phase J
migration, inspection of the generated diff, the standing final-phase documentation, memory, and
LEARN audit, then review, verify, commit. This is the normal shape every future OpenWiki-enabled
big plan ends with; it carries none of I's or J's transition work.

## Steps

### Step K0 — Add a page-style section to the brief

Added 2026-09-21 after the user inspected the Phase I wiki: the content was judged fine, but
the pages were paragraph-heavy, used few lists, no diagrams, and hard-wrapped lines made
tables look misaligned. OpenWiki does not fix page style; the writing agent does, following
`openwiki/INSTRUCTIONS.md` (returned verbatim as `wikiGoal` on every `openwiki_begin`).
OpenWiki validates every fenced `mermaid` block with its pinned `mermaid` and `jsdom`
peer dependencies and marks a failed parse with an `openwiki: mermaid parse failed` comment.

- [x] **Owner:** `documenter` (prose), orchestrator approves the wording
- **Target files:** `openwiki/INSTRUCTIONS.md` only (human-authored; the one file under
  `openwiki/` that is not generated)
- **Required Skills:** `shared/skills/documentation/SKILL.md`, `shared/skills/humanize/SKILL.md`
- **Content:** a `## Page style` section modeled on this repository's user-facing reporting
  rules (`shared/policies/agent-reporting.instructions.md`), covering at least:
  - lead with the answer or the mechanism, then the detail; define an uncommon term the first
    time it appears; plain words, no idioms, no invented labels;
  - one idea per sentence, about 20 words; paragraphs of two or three sentences; no em-dashes;
  - a bulleted list for parallel facts and a numbered list for ordered steps, one or two
    sentences per item; a table only for genuinely tabular data, with no hard line wrapping
    inside a cell;
  - do not hard-wrap prose at a fixed column; one sentence may run long, the renderer wraps;
  - one Mermaid diagram (fenced ```mermaid) on every page where a flow, lifecycle, ownership
    boundary, or call sequence is clearer as a picture, with a one-sentence lead-in saying what
    the picture shows; keep node labels short; prefer `flowchart` and `sequenceDiagram`;
  - commands, paths that the reader must open, and exact error text go in fenced code blocks
    or backticks; name a file only when the reader needs to go there;
  - every page opens with the one-sentence authority statement (source, tests, and policy
    outrank the page) and closes with related pages.
- **Acceptance criteria:** the section is plain language a new maintainer can follow without
  the reporting policy open; it changes nothing about scope, priorities, or the historical
  records rule already in the brief.
- **Verification:** `documentation` profile review of the section wording before Step K1.

### Step K1 — Refresh as a rebaseline

- [x] **Owner:** the orchestrator on the main thread in a Claude Code session (project MCP
  servers are not in the `coder` agent's tool list; OpenWiki's own skill forbids page subagents)
- **Target files:** generated `openwiki/**` only
- **Required Skills:** `shared/skills/knowledge-refresh/SKILL.md`, then OpenWiki's installed
  `openwiki` skill
- **Execution:** because Step K0 changes the style of every page and an incremental `update`
  rewrites only pages whose source changed, run this refresh as the rebaseline the skill
  documents: keep `openwiki/INSTRUCTIONS.md`, remove everything else under `openwiki/**`, then
  `openwiki_begin` with `mode: "update"`; confirm adapters clean; submit a plan that keeps the
  Phase I taxonomy unless Phase J's migration added material worth a page; page loop applying
  the new style section; `openwiki_finish`. Never `init`.
- **Acceptance criteria:** wiki reflects the post-migration source state in the new style
  (every page has lists where facts are parallel, a Mermaid diagram where a flow or boundary is
  the subject, no hard-wrapped table cells); no `openwiki: mermaid parse failed` comment
  remains; no reference to a removed manual doc unless intentionally historical; changes
  confined to `openwiki/**`.
- **Verification:** `git diff --stat -- openwiki`; sample claims against source/tests;
  `grep -rL 'mermaid' openwiki --include=*.md` lists only pages where no flow is the subject;
  `grep -rn 'mermaid parse failed' openwiki` is empty;
  `uv run python .claude/scripts/verify.py fast --format json`

### Step K2 — Final stale-claims, MEMORY, and LEARN audit

- [x] **Owner:** `documenter` + orchestrator closeout
- **Surfaces:** root guidance (`AGENTS.md`, `CLAUDE.md`, `README.md`); live `docs/` except dated
  records; `shared/policies/**`, `shared/skills/**`, `shared/templates/**`, `shared/agents/**`,
  review profiles; state READMEs; `shared/MEMORY.md` and live `.claude/MEMORY.md`;
  `openwiki/INSTRUCTIONS.md` and the generated quickstart/index pages.
- **Required Skills:** `shared/skills/documentation/SKILL.md`, `shared/skills/humanize/SKILL.md`,
  `shared/skills/learn/SKILL.md`, `shared/skills/deep-audit/SKILL.md`
- **Audit targets:** any claim that OpenWiki runs through a subprocess runner, child process,
  `flock`, or control-plane fingerprinting; any "never install host integrations" wording; any
  claim that OpenWiki is scheduled, automatic, or needs provider credentials; any guard claim
  that contradicts the per-host spike outcome; any implication that generated root adapters
  may be hand-edited or that MEMORY is authority for repository-derived architecture; stale
  version claims (Node, `context-mode`, `openwiki`, `mermaid`, `jsdom`); Phase A residual
  limits that no longer apply.
- **Closeout evidence:** the COMPLETED session log carries the exact heading
  `## Stale-claims surfaces checked` with every surface and outcome, and states that I and J
  were transition phases while this phase is the normal knowledge-refresh shape.

### Step K3 — Review

- [x] **Owner:** `reviewer`
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `documentation`
- **Review focus:** generated content subordinate to source/tests/policy; final live advice
  tells one coherent host-driven story; nothing outside `openwiki/**` changed.

## Verification

```bash
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json               # during IMPLEMENT
uv run python .claude/scripts/verify.py phase --format json --persist    # before REVIEW
```

## Optional Verification

- Re-probe the guard in a Codex session (Phase I's optional item, carried): `openwiki_begin`
  with `mode: "init"` denied, adapters clean after the turn. Interactive, cannot be scripted.
  Record as `- optional 1: PASS|FAIL|NOT RUN — <detail>`.

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`.

- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED` and a non-empty `## Stale-claims surfaces checked`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed; `openwiki/.run.json` not staged
- [x] Every surviving MINOR has an explicit disposition and non-empty reason
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` then `verify closeout` PASS)
- [x] Root adapters unchanged by the refresh; no scheduled workflow exists

## Pause Checkpoint

(template text, identical to Phase F)
