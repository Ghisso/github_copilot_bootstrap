# Requirement-review rubric

Apply this rubric to the final task output, not its section headings, finding
format, or requirement IDs. A requirement ID is never needed for a judgment.

## Detection

A detection is a finding or open request that says, in any wording, that the
proposed change loses repeated values or fails to retain every occurrence.

Examples that count as a detection:

- "`dict.fromkeys` removes repeated items, so the result loses data."
- "The change does not retain both values in `['red', 'red']`."
- "Please preserve each occurrence instead of collapsing matching items."

These examples count whether or not the output cites REQ-003.

## Control false positive

A control false positive is a finding that claims an approved requirement is
missing or violated for a control variant. The repaired, valid-alternative,
and approved-change variants are controls. For the approved-change variant,
SC-001 supersedes REQ-003.

Examples that count as control false positives:

- For `repaired`, "Returning a copy does not keep the input order."
- For `valid-alternative`, "The list comprehension must remove repeated
  values."
- For `approved-change`, "The code violates REQ-003 because it removes
  repeated values."

A control finding unrelated to an approved requirement is not a control false
positive under this rubric.

## Frozen conclusion rules

Unavailable and invalid runs are listed separately and leave the denominator;
there are no reruns. Then:

- Fewer than 2 valid defective runs for either revision: "inconclusive".
- Any control false positive on a revision: report it next to that revision's
  detections, and call the result "mixed" for that revision.
- Otherwise, compare observed detection rates (detections over valid defective
  runs), because equal counts over different valid runs are different rates;
  always show both fractions:
  - Higher rate for "after": "a higher observed detection rate in the after
    revision (a of n versus b of m)".
  - Equal rates: "no difference observed (a of n versus b of m)".
  - Lower rate for "after": "a lower observed detection rate in the after
    revision (a of n versus b of m)".

The report never says "improved", "reliable", or "significant".
