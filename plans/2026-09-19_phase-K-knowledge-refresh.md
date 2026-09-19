---
name: 2026-09-19_phase-K-knowledge-refresh
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 13
status: planned
closeout_session_log:
---

# Small Plan: 2026-09-19_phase-K-knowledge-refresh

## Scope

The knowledge-refresh final phase defined in `workflow.instructions.md` ("Knowledge-Refresh
Final Phase"), applied to this big plan: one host-driven OpenWiki update after the Phase J
migration, inspection of the generated diff, the standing final-phase documentation, memory, and
LEARN audit, then review, verify, commit. This is the normal shape every future OpenWiki-enabled
big plan ends with; it carries none of I's or J's transition work.

## Steps

### Step K1 — Refresh

- [ ] **Owner:** `coder` (Claude Code or Codex session)
- **Target files:** generated `openwiki/**` only
- **Required Skills:** `shared/skills/knowledge-refresh/SKILL.md`, then OpenWiki's installed
  `openwiki` skill
- **Execution:** `openwiki_begin` with `mode: "update"`; confirm adapters clean; plan, page
  loop, `openwiki_finish`. A `noop` result is valid and recorded. If the recorded base HEAD is
  unreachable, follow the skill's rebaseline rule; never `init`.
- **Acceptance criteria:** wiki reflects the post-migration source state; no reference to a
  removed manual doc unless intentionally historical; changes confined to `openwiki/**`.
- **Verification:** `git diff --stat -- openwiki`; sample claims against source/tests;
  `uv run python .claude/scripts/verify.py fast --format json`

### Step K2 — Final stale-claims, MEMORY, and LEARN audit

- [ ] **Owner:** `documenter` + orchestrator closeout
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

- [ ] **Owner:** `reviewer`
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `documentation`
- **Review focus:** generated content subordinate to source/tests/policy; final live advice
  tells one coherent host-driven story; nothing outside `openwiki/**` changed.

## Verification

```bash
uv run python scripts/validate_targets.py
uv run python .claude/scripts/verify.py fast --format json               # during IMPLEMENT
uv run python .claude/scripts/verify.py phase --format json --persist    # before REVIEW
```

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED` and a non-empty `## Stale-claims surfaces checked`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed; `openwiki/.run.json` not staged
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
- [ ] Root adapters unchanged by the refresh; no scheduled workflow exists

## Pause Checkpoint

(template text, identical to Phase F)
