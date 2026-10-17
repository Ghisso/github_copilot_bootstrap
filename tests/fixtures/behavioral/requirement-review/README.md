# Requirement-review behavioral fixture

This synthetic packet tests one ordinary review task before any native run.
It is not a production reference.

- `requirements.md` contains the three original approved requirements.
- `scope-change.md` contains SC-001, which replaces the third requirement.
- `defective.diff` removes repeated values without an approved change.
- `repaired.diff` satisfies the original requirements with `list.copy()`.
- `valid-alternative.diff` satisfies them with a list comprehension.
- `approved-change.diff` removes repeated values as SC-001 allows.
- `prompt.md` is the neutral request template. Render it with
  `prompt.format(requirements=..., scope_change=..., diff=...)`; render
  `scope_change` as an empty string when no approved change applies.
- `expected.json` records the frozen expected detection for each variant.
- `rubric.md` defines the manual judgments and frozen conclusion wording.

Use `defective` with the original requirements and no scope change. Use
`repaired` and `valid-alternative` with the original requirements and no scope
change. Use `approved-change` with both the requirements and SC-001.
