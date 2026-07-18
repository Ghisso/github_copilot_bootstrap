---
name: ponytail-review
visibility: public
description: |
  Reviews a code diff exclusively for over-engineering and identifies what to
  delete or shrink: reinvented standard library, avoidable dependencies,
  speculative abstractions, dead flexibility, and unnecessary boilerplate.
  Use after every coding task and whenever the user asks for a simplification
  or over-engineering review. Complements correctness and security review.
license: MIT
---

# Ponytail Review

Review the current diff for unnecessary complexity. The best outcome is a
shorter diff.

For each finding, report its location, what to cut, and what replaces it:

- `delete:` dead code, unused flexibility, or speculative behavior;
- `stdlib:` hand-written behavior already provided by the standard library;
- `native:` a dependency or custom code replaced by a platform feature;
- `yagni:` an abstraction, option, or layer with no current second use;
- `shrink:` the same behavior expressed more directly.

End with `net: -N lines possible.` If nothing can be removed, say
`Lean already. Ship.`

This review does not apply fixes. Return findings to the coder, then rerun
normal verification and review after the diff changes.

## Boundaries

Correctness, security, accessibility, and performance defects belong to the
normal review profiles. Never flag required validation, data-loss protection,
security controls, accessibility, root-cause handling, or the smallest useful
regression check as bloat.

