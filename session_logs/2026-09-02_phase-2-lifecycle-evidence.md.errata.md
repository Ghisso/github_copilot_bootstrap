# Errata: Session 2026-09-02 — Phase 2, Lifecycle Evidence

**Original log:** `.claude/session_logs/2026-09-02_phase-2-lifecycle-evidence.md`
(receipt-bound; immutable — corrected here instead of in place, per big plan
§3.6.)
**Written during:** `2026-09-02_phase-7-stale-knowledge-audit`
**Reason:** the original log's certified-commit LEARN entry states a rule
later proved incorrect. Left standing without this note, it would mislead a
reader into reintroducing a defect Phase 4 removed.

## The superseded entry

`## [LEARN] Entries` in the original log reads, in relevant part:

> Resolve the certified commit as the first entry of `git rev-list
> --ancestry-path --reverse <head_sha>..<later_head>`.

The same superseded method is also restated once more, in different variable
names, in the 14:30 Work Log entry: "The rule now resolves the certified
commit as the first entry of `git rev-list --ancestry-path --reverse
earlier_head..chain_head` and compares that commit's tree." Both statements
describe the identical disproven position-based selection and are superseded
together by this errata.

## Why it is wrong

Selecting by list position alone cannot distinguish a linear implementation
branch from one where `head_sha` gained two divergent, reconverging
children. On such a range, "the first entry" can be a commit that is not
actually a child of `head_sha`, so the tree check would validate against the
wrong commit and silently accept an unproven state.

## The corrected rule (settled in Phase 4)

Query the same ancestry path with `--parents` and filter to the commit(s)
whose own parent set contains `head_sha` — proof by parentage, not position —
then fail closed (record a chain error, produce no receipt) unless that
yields exactly one candidate. See big plan §3.5 ("Refined in Phase 4") and
`.claude/session_logs/2026-09-02_phase-4-minor-findings-closure.md` for the
full investigation and fix. `.claude/MEMORY.md`'s certified-commit LEARN
entries already reflect this corrected rule.

## Scope of this errata

Only the certified-commit resolution method is superseded. The rest of the
original log — including its correct diagnosis that a receipt's `head_sha` is
the parent of the commit it certifies and `tree_sha` is the staged tree that
becomes that commit's tree — is unaffected and still accurate.
