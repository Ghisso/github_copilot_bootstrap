# Session: Skill set 55 to 37 with a description cap (skills-and-instructions-trim, Phase C)

**Date:** 2026-11-13
**Plan:** `.claude/plans/2026-11-12_phase-C-skill-set.md`
**Status:** IN-PROGRESS

## Goal

Take the shipped skills from 55 to 37 (9 removed, 4 + 4 merged into `haystack` and `data-and-graph-pitfalls`, `deploy-service` into `bentoml-service`, two folded into the tests policy), cap each non-Ponytail skill's listing text at 300 characters with a validator check, make `code-style` and `testing-patterns` pointers, make the planner read `plan-decomposition` only in full-plan mode and the coder's always-load tier Ponytail only, and apply the Codex spike result (REQ-003, REQ-004, REQ-005, REQ-006, REQ-009).

## Work Log

- Phase B committed as `86d6598` and pushed; Phase C set `in-progress` by the post-commit hook. Material-impact check: Phase B removed the workspace skill list and the "hidden" wording as Phase C assumes; root guidance and the workflow core (35 B and 45 B of budget left) are outside Phase C's files. No planner run.
- Spike result applied (big plan table, S1 first row): Codex 0.147.0 lists repository skills from `.agents/skills/` only, and the 55 `[[skills.config]]` entries add none. Step 5 rewrites the `render_codex_config` comment to say so and cites the spike report; no configuration change. S5: no overflow today; the cap stands for size.
- Delegation by file ownership: coder C1 Steps 1 and 6 (validator cap, fallback map, tests; failing-first in a `git archive HEAD` scratch copy so parallel edits cannot touch it), coder C2 Step 2 (remove, merge, fold the skill folders), coder C3 Steps 3-4 (14 descriptions, two pointer skills, moved rules), coder C4 Step 5 (lists, prompts, docs, Codex comment). No content agent runs the generator or validators; C1 integrates after edits settle.

## [LEARN] Entries

## Verification

## Open Questions / Next Steps
