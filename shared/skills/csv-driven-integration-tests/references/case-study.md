# CSV-Driven Integration Tests — Worked Case Study

Domain-specific example from a UN Security Council resolution classifier.
Kept here because the vocabulary and numbers are project-specific — the
technique in the root `SKILL.md` does not depend on this domain.

## Common Pattern Gaps Discovered Empirically

- "list resolutions" (not just "list all")
- "which resolutions" (structured lookup)
- Superlatives with intervening words: "latest resolution on Libya" ≠ "latest resolution"
- Standalone "abstain" without "voted"
- Junction lookups: "what countries/subjects/topics"
- Plural variants: "meeting records" not just "meeting record"

## Common BOTH Pattern Mistakes

- `\bwhat\b.*\b(?:latest|most recent)\b` is too broad — matches pure SQL superlatives
- Tighten to require content words: `\b(?:latest|most recent)\b.*\b(?:say|about|content|discuss)\b`

## Example

CSV-driven tests with 64 test cases across 11 categories revealed:
- 6 missing SQL patterns in a regex classifier
- 1 overly-broad BOTH pattern that stole SQL classifications
- 1 GROUP BY validation false positive in test assertions

Net result: classifier went from 43/64 → 64/64 correct after fixes.
Full regression: all tests passed, 0 failures.
