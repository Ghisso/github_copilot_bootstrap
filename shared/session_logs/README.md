# Session Logs

This directory stores implementation session logs.

Use the canonical template at `.claude/templates/session-log.md`.

## Naming Convention

`YYYY-MM-DD_description.md`

For the final session that closes a small plan, prefer:

`YYYY-MM-DD_<phase-slug>-closeout.md`

Closeout logs must include:

- `**Plan:**` pointing at the small-plan file
- `**Status:** COMPLETED`
- `## [LEARN] Entries` with either `[LEARN:category] ...` entries or `[LEARN] none - no new lessons this session`

`MEMORY.md` can still be updated as a separate persistence action, but its
mtime is never evidence of LEARN completion; the closeout gate reads only the
`## [LEARN] Entries` section of this file.

## Immutability and Errata

A closeout log already bound by a completed phase's receipt must not be
edited afterward - the receipt hashes its exact bytes, and historical
receipt-chain validation depends on that byte stability. Corrections use a
sibling file named `<original-log-name>.errata.md`, for example:

```markdown
# Errata for 2026-09-02_phase-1-verification-authority.md

- 2026-09-02
  - Supersedes: <short identification of the stale claim>
  - Corrected conclusion: <new conclusion>
  - Evidence/reference: <later phase/log/doc>
```

An erratum written during a later active phase is evidence of that
discovering/correcting phase and may be bound by its own receipt; the
original phase's receipt never changes. An erratum written outside an active
plan may remain unbound until a later phase reviews or changes it - it needs
no dedicated receipt ceremony of its own.
