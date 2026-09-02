# Session: Phase 3 — Consistency, Immutable History, and Hardening

**Date:** 2026-09-02
**Plan:** `.claude/plans/2026-09-02_phase-3-consistency-hardening.md`
**Status:** COMPLETED

## Goal

Align runtime and documentation, make session-log history immutable with
explicit errata, constrain typo bypasses, and protect the whole design with
end-to-end regression coverage. Final phase of the
`verification-gate-semantic-hardening` big plan.

## Work Log

- **16:00** - Delegated implementation to a fresh `coder` with the Phase 1 and
  Phase 2 outcomes supplied, including the hard-won certified-commit rule, so
  they would not be re-derived or disturbed.
- **17:30** - Round 1: LEARN contract, errata guidance, typo-bypass
  restriction, surface sweep, and 8 new tests. 1183 tests pass.
- **18:00** - Review round 1: **FAIL**, 1 CRITICAL + 4 MAJOR, two proven by
  executing the code rather than reading it. The typo-bypass exclusion covered
  `shared/scripts/` and `shared/hooks/` but not `shared/agents/`,
  `shared/policies/`, `shared/skills/`, `shared/templates/`, or
  `shared/review-profiles/` — all Markdown, all shipped, all live runtime
  guidance. A `docs(typo):` commit could rewrite an agent's own instructions
  with no ceremony. Separately, the new LEARN check accepted the unedited
  template boilerplate and fenced examples as evidence: one hollow gate
  swapped for another.
- **18:40** - Round 2: exclusion widened to the whole `shared/` tree, derived
  by tracing the generator rather than hand-listed, so it cannot drift. Fence
  stripper added and the template rewritten to prose. End-to-end lifecycle test
  delivered. 1187 tests pass.
- **19:20** - Review round 2: **FAIL**, 1 CRITICAL + 2 MAJOR. `CLAUDE.md` and
  `AGENTS.md` were still bypass-eligible despite the repo's own policy naming
  them control-plane — outside the fix's scope by construction, since it had
  been scoped to `shared/`. The fence stripper still missed `~~~`,
  unterminated, and indented fences. `README.md:377` still advertised a
  "Quality scoring rubric".
- **19:50** - Round 3: root control-plane files excluded, reusing the pattern
  already encoded in the sibling `diff_requires_ponytail` so the two
  classifiers cannot drift. Fence handling replaced with a GFM-aware line-by-
  line state machine. README inventory swept. 1190 tests pass.

## Design decisions

- **The typo-bypass exclusion is derived, not enumerated.** Two rounds were
  lost to hand-listed subsets that drifted from reality. The final form
  excludes the entire `shared/` tree, sourced by tracing what
  `generate_targets.py` actually copies, plus the root control-plane files
  reusing `diff_requires_ponytail`'s existing encoding of the same policy
  sentence. Real documentation typos still qualify: `docs/**`, `README.md`,
  and nested docs remain eligible.
- **An unterminated fence swallows to end of section.** Content inside a fence
  that never closes is not evidence, so failing closed is correct even though
  it can reject a malformed-but-well-intentioned log.
- **The LEARN gate needed the template fixed too, not just the parser.**
  Enforcement alone was insufficient while the shipped template's own example
  lines satisfied the check. A gate whose boilerplate passes it is not a gate.
- **Errata rather than log edits.** A closed receipt-bound log stays
  byte-identical; corrections go in a sibling `<log>.errata.md` that the
  discovering phase may bind under the ordinary receipt mechanism. No separate
  errata ceremony exists.
- **Two end-to-end deviations were accepted after review scrutiny.** Step 2
  exercises real per-phase completion commits rather than mid-phase WIP
  commits, because an `in-progress` status is structurally blocked regardless
  of findings, and the paused path is covered elsewhere with a stronger
  assertion. Step 8 uses the `enforce-pr-gate.sh` layer rather than a second
  `git push`, because a hand-edit with no new commit leaves push nothing to
  negotiate so `pre-push` never fires; the PreToolUse layer re-evaluates
  unconditionally and produces a real deny on live bytes.
- **Dated historical documents keep their score-era language.**
  `docs/plan-deterministic-commit-gate.md`'s D1–D5 narrative and the
  `plans/` archives are records of what was true then, not live claims.

## [LEARN] Entries

- [LEARN:security] A path-based bypass allowlist must be derived from what the
  build actually ships, never hand-listed. Two review rounds here were spent
  on enumerated subsets that each missed a live runtime surface — first the
  non-script `shared/` subdirectories, then the root control-plane files. When
  a sibling function already encodes the same policy, reuse its pattern so the
  two classifiers cannot drift apart.
- [LEARN:verification] Replacing a hollow gate can produce another hollow gate.
  The `MEMORY.md` mtime shortcut was swapped for a regex that accepted the
  shipped template's own placeholder text and fenced examples. Check a new
  evidence rule against the artifact a user would actually start from, and tie
  that check to the real template file rather than a hardcoded copy of it.
- [LEARN:testing] A test that reproduces an exploit must reproduce its exact
  shape. An indented-fence test that also indented the entry line passed
  against the buggy code for an unrelated reason, because the entry regex was
  column-0-anchored too. Verify a new test fails against the old code for the
  intended reason, not merely that it fails.
- [LEARN:review] Ask for execution, not inspection, on any gate that classifies
  paths or parses text. Every CRITICAL in this phase was found by running the
  shell function or regex against real inputs; static review had passed the
  same code twice.

## Verification Results

```bash
uv run pytest tests/ -q --tb=short
# 1190 passed (baseline on dev: 1135; +55 across the three phases)

uv run mypy scripts/ --ignore-missing-imports --explicit-package-bases
# Success: no issues found in 8 source files

uv run ruff check tests/ scripts/ shared/
# All checks passed!

uv run python scripts/validate_targets.py
# PASS generated target is structurally valid
# (includes the adversarial bypass cases and the end-to-end lifecycle test)

uv run python scripts/validate_plan_frontmatter.py
# (clean)

uv run python .claude/scripts/verify.py fast --format text
# fast: PASS

uv run python .claude/scripts/verify.py phase --format text
# phase: PASS
```

## Stale-claims surfaces checked

Triggered because this plan changed documented behavior. Surfaces reviewed:
`README.md`, `docs/architecture.md`, `docs/runtime-checks.md`,
`docs/smoke-tests.md`, `docs/target-mapping.md`,
`docs/plan-deterministic-commit-gate.md`, every `shared/policies/*`,
`shared/agents/*/prompt.md`, `shared/review-profiles/*`,
`shared/session_logs/README.md`, `shared/templates/*`, and the big plan itself
(§3.5 corrected, since Phase 2 disproved its stated tree rule).

## Open Questions / Next Steps

- Four files were already unformatted on `dev` and were not touched:
  `shared/hooks/scripts/protect-files.py`,
  `shared/skills/caveman-compress/scripts/{detect,validate}.py`,
  `tests/test_check_native_clients.py`.
- No compatibility allowance exists anywhere in this plan, so none carries a
  removal condition.
- The user owns the merge decision; no PR was opened.
