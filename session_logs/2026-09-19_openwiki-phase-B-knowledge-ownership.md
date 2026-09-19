# OpenWiki Phase B: Knowledge Ownership and Agent Access

**Status:** IN PROGRESS
**Plan:** `.claude/plans/2026-09-19_phase-B-openwiki-knowledge-ownership-and-agent-access.md`

## Goal

Encode who owns which kind of knowledge, add one narrow OpenWiki skill wrapping the Phase A
runner, and add short provider-neutral root guidance. This phase does not change planner,
orchestrator, documenter, learn, or onboard behavior; Phase C does that on top of this contract.

The central rule: **OpenWiki is derived context, not authority.**

## Approach

- One ownership rule set, not several competing definitions across policy, skill, and root files.
- The skill wraps `.claude/scripts/openwiki_refresh.py` and never reaches for raw `openwiki --init`.
- Rebaseline means preserving `openwiki/INSTRUCTIONS.md`, removing the rest of `openwiki/**`, and
  running the ordinary runner again.
- Root guidance stays short; detail lives in the skill and the policies.

## Inherited Context From Phase A

Phase A shipped the runner with documented residual limits that the skill must not contradict:

1. A write landing outside the repository is not detected (Phase E covers this).
2. Inside a validated Git directory, files off the execution allowlist are not fingerprinted.
3. A `gitdir:` pointer outside the tracked tree escapes the mechanism.
4. `.claude/.cache/` is excluded by deliberate exception.
5. Concurrent agent-session writes to `.claude` cause a fail-closed failure naming unrelated
   files; re-run when the checkout is quiet. This is why the skill must require serial execution.

## Progress

- Phase A committed and pushed as `e9cf57d`; both repositories clean.
- Big plan `current_phase` advanced to Phase B by the branch hooks.

## Verification

Pending.

## Review

Pending. Profiles required: `code`, `architecture`, `security`, `tests`, `ponytail`,
`documentation`.

## [LEARN] Entries

Pending.

## Remaining Work

- B1 ownership contract, B2 OpenWiki skill, B3 root guidance, B4 review and closeout.
