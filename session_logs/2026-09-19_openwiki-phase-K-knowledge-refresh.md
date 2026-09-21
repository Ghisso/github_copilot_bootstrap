# Session: OpenWiki Phase K — knowledge refresh

**Date:** 2026-09-21
**Plan:** `.claude/plans/2026-09-19_phase-K-knowledge-refresh.md`

**Status:** IN-PROGRESS

Phases I and J were transition phases (first enablement and the one-time
docs migration). This phase is the normal knowledge-refresh shape that
every future OpenWiki-enabled big plan ends with: one host-driven refresh,
inspection of the generated diff, the standing final-phase stale-claims,
memory, and LEARN audit, then review, verify, commit. One addition specific
to this run: the user asked for a page-style change after inspecting the
Phase I wiki, so Step K0 adds a style section to the brief and Step K1 runs
the refresh as a rebaseline so every page is regenerated in the new style.

## Goal

Add the page-style section to `openwiki/INSTRUCTIONS.md`, regenerate the
wiki under it against the post-migration source, audit every live-advice
surface for claims this big plan invalidated, and close the big plan.

## Work Log

- Phase started 2026-09-21 after Phase J's completion commit `294382d`.
  Step K0 and the rebaseline shape of K1 were added to the plan on the
  user's request: "ok add instructions for style in phase K. you should
  model them on your own language instructions (simple, no jargon,
  everything clearly explained, avoid long paragraphs and use lists,
  charts ...)".
- Step K0 (fresh documenter): `## Page style` section inserted in
  `openwiki/INSTRUCTIONS.md` between "What to prioritize" and "Historical
  records are not current behavior", 67 lines, grouped under bold lead-ins
  Structure, Sentences and words, Lists and tables, Diagrams, and Code,
  paths, and enforcement, with a four-node Mermaid example and the rule
  that a page states when a hook, validator, or test enforces a rule it
  describes. Nothing else in the brief changed. Orchestrator approved the
  wording; documentation-profile review requested before K1.

## Stale-claims surfaces checked

Audit targets from Step K2: subprocess runner, child process, `flock`, or
control-plane fingerprinting claims; "never install host integrations"
wording; scheduled, automatic, or credential-needing OpenWiki claims; guard
claims contradicting the per-host spike outcome; hand-editable root adapters
or MEMORY as architecture authority; stale version claims (Node 22.22.0,
`context-mode` 1.0.169, `openwiki@0.5.2`, `mermaid@11.16.0`,
`jsdom@29.1.1`); Phase A residual limits. Swept with `rg -n -i` over the
full pattern set, every hit read in context (documenter, read-only).

| Surface | Outcome |
| --- | --- |
| Root guidance `AGENTS.md`, `CLAUDE.md`, `README.md` | CURRENT. The OpenWiki sentence names `knowledge-refresh`; no runner, subprocess, or `init` wording. No generator-string change needed. |
| Live `docs/architecture.md`, `runtime-checks.md`, `smoke-tests.md`, `target-mapping.md`, `native-client-acceptance.md`, `plan-deterministic-commit-gate.md` | CURRENT. The OpenWiki Knowledge Layer section states the host-driven design and the per-host restore split; "residual limits inherited from the earlier runner design" is provenance of a still-valid guard limit, not a claim the runner exists. Other hits are the CI runner, the native-client probe runner, or AI-state fingerprints. |
| Dated `docs/2026-*` (four files) | HISTORICAL, untouched. |
| `shared/policies/**` | CURRENT. OpenWiki Refresh and Knowledge-Refresh Final Phase sections match the code. Zero hits for the retired-design vocabulary. |
| `shared/skills/**` (55 skills; hits in 14) | CURRENT. `knowledge-refresh/SKILL.md` read in full and accurate; other hits unrelated. Zero repository-wide matches for the old `skills/openwiki/SKILL.md` path as the refresh owner. |
| `shared/templates/**`, `shared/agents/**`, `shared/review-profiles/**` | CURRENT. Planner, orchestrator, documenter prompts and the big-plan template point at the canonical rule and the new skill name. |
| State READMEs (`shared/plans`, `shared/session_logs`, `shared/quality_reports`); `shared/explorations` absent | No hits. |
| `shared/MEMORY.md` | No hits. |
| Live `.claude/MEMORY.md` | Entries about the retired runner are explicitly labelled as carried lessons (HISTORICAL); per-host restore and `openwiki@0.5.2` entries are CURRENT. No edit. |
| `shared/devcontainer/**`, `.devcontainer/**` | CURRENT. Pins match exactly; authoring and generated Dockerfiles are byte-identical. |
| `openwiki/INSTRUCTIONS.md` and the generated quickstart and index pages | (pending, audited after the Step K1 rebaseline) |

Non-documentation observation: `shared/scripts/__pycache__/openwiki_refresh.cpython-313.pyc` is a stale bytecode artifact of the retired runner; `__pycache__` is git-ignored, so it is a local leftover only.

## Review findings and dispositions

(pending)

## [LEARN] Entries

(pending)

## Verification

(pending: paste `verify closeout --format text` summary lines)

- optional 1: (pending)

## Open Questions / Next Steps

- (pending)
