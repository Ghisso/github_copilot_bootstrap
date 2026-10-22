---
name: ponytail-review
visibility: public
description: |
  Reviews a code diff exclusively for over-engineering and identifies what to
  delete or shrink: reinvented standard library, avoidable dependencies,
  speculative abstractions, dead flexibility, and unnecessary boilerplate.
  Use after a coding task whose diff is control-plane or high-risk, multi-file,
  dependency-, script-, or generator-related, or complexity-expanding, and
  whenever the user asks for a simplification or over-engineering review.
  Complements correctness and security review.
license: MIT
---

# Ponytail Review

Review the current diff for unnecessary complexity. The best outcome is a
shorter diff.

## Read first

Read the code the diff touches, not only the diff: callers of every changed
function, the functions it calls, its tests and fixtures, and config that names
it. Trace the real flow: where data comes in, what is stored, what goes out.
When a signature, return value, or behavior changes, search every caller. Use
what you read to judge complexity: a caller or test the change breaks is a
correctness defect for the normal review profiles, not a finding here.

## Findings

For each finding, report its location, what to cut, and what replaces it:

- `delete:` dead code, unused flexibility, or speculative behavior;
- `reuse:` an existing helper or component already does this; name its path;
- `stdlib:` hand-written behavior already provided by the standard library;
- `native:` a dependency or custom code replaced by a platform feature;
- `yagni:` an abstraction, option, or layer with no current second use;
- `shrink:` the same behavior expressed more directly.

Before you report, check each finding:

- Every finding needs a concrete case as evidence: for example, no caller sets
  the option, or the standard-library function that does the same. No case, no
  finding.
- Before `delete:`, search the whole tree for the code, including tests,
  fixtures, config, and string or dynamic references.
- Re-read the cited lines and confirm the code really is unused or the
  replacement really behaves the same.
- A shortcut marked with a `ponytail:` comment that names its limit is a
  decision, not a finding.

End with `net: -N lines possible.` If nothing can be removed, say
`Lean already. Ship.` Add one `Not checked:` line when something mattered and
you could not check it.

This review does not apply fixes. Return findings to the coder, then rerun
normal verification and review after the diff changes.

## Boundaries

Correctness, security, accessibility, and performance defects belong to the
normal review profiles. Never flag required validation, data-loss protection,
security controls, accessibility, root-cause handling, or the smallest useful
regression check as bloat.

