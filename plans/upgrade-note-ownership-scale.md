---
name: upgrade-note-ownership-scale
type: big-plan
status: complete
originating_branch: dev
implementation_branch: upgrade-note-ownership-scale_implementation
phases:
  - 2026-09-03_phase-1-ownership-scale-note
current_phase: 
started_at: 2026-09-03T08:44:00Z
---

# Big Plan — Upgrade Note Ownership Scale

**Date:** 2026-09-03
**Branch base:** `dev`
**Scope:** bootstrap authoring repo documentation only.

## 1. Goal

Close the one MAJOR finding against commit `4a3c0c2` (merged via PR #30): the
root-owned-file guidance understates scale, so an operator fixes the visible
files and remains unaware of the latent ones.

## 2. Why this is needed

The note in `README.md` and `docs/runtime-checks.md` describes a single
root-owned file and offers a single-path ownership fix. The investigation that
produced that guidance found **156** root-owned Python files in one consumer
project, against the **2** that were visible because only those two happened
to need reformatting. The other 154 are correctly formatted today and
therefore silent, and each will fail the moment it needs rewriting.

The failure mode is precisely the one this documentation exists to prevent: an
operator succeeds today, then meets an unexplained `Permission denied` weeks
later and reads it as a bootstrap defect.

This repeats a lesson already recorded in
`.claude/session_logs/2026-09-03_phase-1-consumer-upgrade-notes.md` —
"[LEARN:diagnostics] Report the scale of a problem, not the first instance. A
count derived from the symptom rather than the cause will understate it." The
shipped guidance reproduced the blind spot the session had just named.

## 3. Settled behavior

State that ownership problems can affect far more tracked files than the ones
currently failing, and give the reader a way to see the true extent in one
step rather than discovering it file by file.

Keep it short. This is one clause plus an enumeration command in each of two
places, not a new section.

Any enumeration command must be verified to run, and must be safe to run —
read-only, no ownership change as a side effect.

If recursive ownership change is suggested at all, it carries a caution,
because a recursive change across a source tree is not obviously safe and the
reader may be root-adjacent.

## 4. Non-goals

- Do not change any gate, check, threshold, or scope.
- Do not restructure or expand the surrounding sections; the finding is about
  one omitted fact.
- Do not patch consumer repositories.
- Add no compatibility allowance.

## Phase

- `2026-09-03_phase-1-ownership-scale-note` — state the true scale of root-owned files and how to enumerate them.

## 5. Acceptance criteria

1. Both locations convey that scale can exceed the currently-failing files.
2. A read-only enumeration command is given and verified to run.
3. Any recursive ownership guidance carries a caution.
4. No gate behavior changed; both files remain additive prose.
5. No new stale claim introduced.
6. Full repository tests and validation pass with no regeneration drift.
