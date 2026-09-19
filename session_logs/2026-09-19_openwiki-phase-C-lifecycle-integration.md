# OpenWiki Phase C: Lifecycle Integration

**Status:** IN PROGRESS
**Plan:** `.claude/plans/2026-09-19_phase-C-openwiki-lifecycle-integration.md`

## Goal

Teach the lifecycle how an OpenWiki-enabled big plan ends: a small final knowledge-refresh
phase. Narrow documenter, learn, and onboard so they stop duplicating facts OpenWiki can
regenerate. Repositories without the enablement marker keep the current lifecycle unchanged.

## Approach

- One canonical statement of the knowledge-refresh phase rule; every other location links to it.
  This follows the Phase B pattern that worked, and avoids the one failure Phase B had.
- The disabled-repository path must be provably unchanged, not merely intended to be.
- No recursion: a plan whose purpose is already a knowledge refresh must not gain another
  refresh phase.

## Inherited Context

- Phase A: the runner, with five documented residual limits.
- Phase B: the canonical Knowledge Ownership contract in
  `shared/policies/workspace.instructions.md`, and `shared/skills/openwiki/SKILL.md`.
  Phase C must link to that contract rather than restate it.

## Carried-Forward Lesson From Phase B

Phase B's only defect came from retyping one sentence into a second file instead of copying it,
which produced three drifts at once including a path no skill-loading runtime reads. Phase C
touches more files with more shared wording, so the same rule applies with more force: one
canonical home, links everywhere else, and copy rather than retype wherever a restatement is
genuinely required.

## Progress

- Phase B committed and pushed as `04fd159`; both repositories clean.
- Big plan `current_phase` advanced to Phase C by the branch hooks.
- C1, C2, C3 implemented by one author in sequence. One review round; one MAJOR and one MINOR
  found and fixed.

## Completed Work

- **C1 — planning rule.** Canonical home is a new "Knowledge-Refresh Final Phase" section in
  `shared/policies/workflow.instructions.md`, placed beside the pre-existing standing
  final-phase audit rule it complements. The planner prompt, `plan-decomposition`, and
  `plan-big.md` link to it rather than restate it.
- **C1 — recursion made deterministic.** Rather than relying on prompt text,
  `validate_knowledge_refresh_phase_position` in `scripts/validate_plan_frontmatter.py` fails
  any big plan carrying more than one `-knowledge-refresh` phase, or one that is not last.
  A plan violating the rule now fails validation regardless of what the planner did.
- **C2 — orchestrator.** A knowledge-refresh small plan is an explicit IMPLEMENT phase, not a
  hidden closeout hook. One clause added to the existing CLOSEOUT staging sentence so
  `openwiki/.run.json` is never staged.
- **C3 — documenter, learn, onboard narrowed.** Classification by the Phase B ownership ranking
  (linked, not restated), lesson routing, and OpenWiki's entry page as optional just-in-time
  orientation rather than mandatory startup reading.

## Verification

- `scripts/generate_targets.py --all`: passed.
- `scripts/validate_targets.py`: PASS.
- `scripts/check_runtime.py`: passed after a local-only self-install.
- `verify.py fast`: PASS.
- `tests/test_validate_plan_frontmatter.py`: 586 passed.
- Full suite: 1587 passed.

## Review

Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.

Round 1: FAIL on one MAJOR and one MINOR.

The MAJOR is the instructive one. The `-knowledge-refresh` suffix was documented only as a way
to *recognize* an existing phase, never as a mandate for *naming* a new one. A planner appending
`2026-09-19_phase-D-openwiki-sync` — conventional and fully conformant to the naming rules that
did exist — would produce a plan the validator silently ignored, because its only signal is the
literal suffix. The enforcement was real but conditional on a convention that lived only in the
author's head, which is a more dangerous shape than no enforcement at all, because it reads as a
guarantee during review.

Fixed by adding an imperative naming instruction with a positive and a negative example, tied
explicitly to the mechanism it feeds, plus inline mentions in the planner prompt and
`plan-decomposition` so a planner reading only its own prompt would know.

The MINOR was an untested defensive guard; a parametrized test now proves its skip path is
deliberate rather than accidentally silent.

Everything else passed on independent verification: wording discipline was judged the opposite
of Phase B's drift, the knowledge-refresh shape stays small and distinct from Phase D's
migration scope, no competing audit rule was created, failure semantics match word for word,
zero OpenWiki references in verifier, hooks, state-sync, post-commit, or CI, humanize
requirements intact, no mandatory startup reading in `onboard`, and ponytail found nothing to cut.

## Decision: the validator does not require a suffixed phase to exist

Considered and rejected, with reasoning recorded because it will come up again. Making the
validator fail an enabled repository's big plan that lacks a suffixed final phase would require
it to evaluate two trigger conditions that are not structural: whether the plan changes
documentable outer-repository behavior, and whether the plan is itself a refresh. Both are
judgements about plan prose, not facts a frontmatter parser can extract. Enforcing from the two
checkable conditions alone would fail legitimate exempt plans — read-only, AI-state-only, or a
refresh plan itself — that a parser cannot distinguish from a plan that should have had the
phase. Uniqueness and trailing position, enforced when the suffix is present, is the portion of
the rule that is fully mechanical, and that is what the validator owns.

## Scope correction: C3 is not gated to disabled repositories

Recorded precisely because an earlier summary of mine was too broad. The claim that disabled
repositories see an unchanged lifecycle is scoped to **C1 and C2 only** — the planning and
orchestration rule. C3's narrowing of documenter, learn, and onboard applies in every
repository: `learn`'s lesson-routing paragraph and the "do not duplicate source-derivable facts
into MEMORY" guidance are general. Only the OpenWiki-specific clauses inside them are gated by
the enablement marker. C3 was never intended to be a no-op for a disabled repository.

## Limit of the disabled-path proof

Worth stating plainly for whoever reads this next. A literal proof — run the planner against a
disabled-repository fixture and diff its output — is not possible in this repository, because
the planner is a prompt-governed agent with no deterministic entry point and no planner-output
harness exists. What was proven instead: every prose edit is additive (zero deletions in eight
of nine files; the ninth is a single in-place insertion into the existing staging sentence, with
the rest byte-identical), the rule's first trigger condition is a file a disabled repository does
not have, the validator keys on a slug nothing in a disabled repository produces, and all 581
pre-existing frontmatter tests plus every real plan still validate unchanged.

A planner-output harness would be valuable well beyond OpenWiki. It is its own piece of work.

## [LEARN] Entries

- [LEARN:review] Enforcement that keys on a naming convention is only as strong as the
  instruction to follow that convention. A validator rejecting duplicate `-knowledge-refresh`
  phases looked like a hard guarantee, but nothing told the planner to use the suffix, so a
  reasonable alternative name made the check silently no-op. Conditional enforcement is more
  dangerous than none, because it reads as a guarantee in review. When a check keys on a string,
  mandate that string imperatively and say what keys on it.
- [LEARN:workflow] Prompt-governed agents cannot be tested for behavior in this repository, only
  for the text of their prompt files. When asked to prove an agent's behavior is unchanged, say
  that limit out loud and offer the strongest available proxy rather than writing a weaker test
  and describing it as the thing that was asked for.
- [LEARN:quality] Before making a deterministic gate stricter, check whether every condition it
  would enforce is observable from the data it actually receives. Two of the four
  knowledge-refresh trigger conditions are judgements about prose; a gate enforcing only the
  observable two would have failed legitimately exempt plans.

## Remaining Work

- Confirmation review pass, then closeout: findings, receipts, commit, push.
