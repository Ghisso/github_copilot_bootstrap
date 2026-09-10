# Consumer Lifecycle Friction Hardening — Phase C Closeout

**Status:** COMPLETED
**Plan:** `.claude/plans/2026-09-10_phase-C-plan-and-delegation-semantics.md`
**Branch:** `consumer-lifecycle-friction-hardening_implementation`
**Started:** 2026-09-11

## Goal

Make plan files describe lifecycle state honestly, accept readable phase
annotations without weakening frontmatter parity, add a backward-compatible
`planned` status for future phases, and tighten agent handoffs so incremental
requirements, reviewer diff evidence, and callable-tool boundaries survive
delegation.

## Completed phase

Phase C: `.claude/plans/2026-09-10_phase-C-plan-and-delegation-semantics.md`

All seven steps were implemented. Steps 1 through 4 were coder work; steps 5
through 7 were documenter work run after code review converged, as the plan
required.

## Work log

- Steps 1-4: phase-annotation parsing, the `planned` small-plan status, phase
  activation at the branch and post-commit transition boundaries, and context
  status reporting planned phases as pending.
- Review round 1 failed the gate with one critical, one major, and two minor
  findings.
- The critical finding was a path traversal introduced by this phase.
  `record-branch-state.sh` used the big plan's first `phases:` entry to build
  `FIRST_PLAN="$REPO_ROOT/.claude/plans/$FIRST_PHASE.md"` and then wrote to it
  with `fm_write`, without calling `is_plan_slug`. The sibling script
  `record-commit-closeout.sh` validates every phase before building a path;
  this script called `is_plan_slug` zero times. A `phases:` entry such as
  `../../../../tmp/target` would make a branch-creation hook rewrite a file
  outside the plans directory. Branch creation runs before any commit-time
  gate inspects the plan, so no earlier checkpoint would catch it.
- Before this phase, that value was only ever written as data into the big
  plan's frontmatter. This phase was the first to turn it into a path that
  gets written, so the exposure was newly introduced rather than pre-existing.
- The fix validates `FIRST_PHASE` immediately after it is read and bails out
  before either use, matching the empty-`phases:` bailout directly above it.
  Bailing out entirely was chosen over skipping only the activation, because
  persisting an unsafe `current_phase` would move the failure downstream
  instead of catching it at the source.
- Steps 5-7: incremental-intent protection in the orchestrator and coder
  briefs, a reviewer diff-evidence contract that keeps the reviewer at read
  and search capabilities only, and a statement that agents use only tools
  their runtime actually exposes.
- Review round 2 passed the gate and raised three minor findings. Round 3
  confirmed two resolved and narrowed the third. All three were fixed.

## Notable review outcomes

**A security regression test that passed for the wrong reason.** The test
guarding the critical fix seeded its victim file with `status: untouched`. The
vulnerable code only calls `fm_write` when the status is `planned`, so with the
guard removed that path would emit a warning and never attempt a write. The
byte-identity assertion therefore succeeded because nothing tried to touch the
file, not because the guard stopped it. The test did fail without the fix, but
only through a secondary assertion about `current_phase`, which proves the
unsafe value does not propagate rather than that the write primitive is
blocked. The fixture is now `status: planned`, and the test was proven
load-bearing by temporarily bypassing the guard and observing the victim file
outside `.claude/plans/` change from `status: planned` to `status: in-progress`
on exactly the byte-identity assertion. The script was then restored and
confirmed byte-identical.

**A validation heuristic that discouraged the prose it was meant to protect.**
The check for text recommending a filtered Context Mode tool matched a literal
verb-plus-tool substring. It was evadable by this repository's own house style
of wrapping tool names in backticks, and it also flagged correct prohibitions
such as "do not use ctx_execute", pushing authors toward vaguer phrasing. Three
successive rounds narrowed it: first backtick stripping, a broader verb list,
and a negation exemption; then, after the reviewer reproduced three further
misfires with realistic prose, a sentence-scoped rewrite. The negation check is
now "anywhere in the sentence before the verb" rather than a fixed
twenty-character window, and scanning cannot cross a sentence boundary.

**A step deliberately delivered narrower than its prose.** Step 1 asked to
accept trailing prose after a whitespace boundary. The shipped pattern also
requires a delimiter. Two earlier attempts were rejected against real data:
banning backticks in annotations broke an installed plan whose annotation
legitimately contains inline code, and allowing any non-whitespace start caused
ordinary narrative bullets in another installed plan to parse as phase-inventory
entries and produce false frontmatter mismatches. The plan's own acceptance
criterion says "Parenthetical and documented delimiter annotations validate",
which is exactly what shipped. The reviewer verified against about twenty
adversarial inputs that no input can make the extracted slug list diverge from
frontmatter.

## Verification state

- `uv run pytest tests/ -q`: 1371 passed.
- `scripts/validate_plan_frontmatter.py`: exit 0 against all live plan files.
- `scripts/validate_targets.py`: generated target structurally valid.
- `scripts/check_runtime.py`: 0 failed.
- Ruff check, Ruff format check, and Mypy passed.

## Review outcome

Three review rounds, each running the `code`, `architecture`, `security`,
`tests`, `ponytail`, and `documentation` profiles over two sequential passes.
Final gate: PASS with no surviving findings. The one critical, one major, and
five minor findings raised across the rounds were all fixed rather than
accepted.

## [LEARN] Entries

- [LEARN:security] When a refactor starts using an existing configuration value
  to build a filesystem path, the value needs slug validation even if it was
  previously safe as data. A value written into frontmatter carries no path
  risk; the same value interpolated into a path does.
- [LEARN:testing] A security regression test must be proven load-bearing by
  removing the guard and confirming the intended assertion fails. A fixture
  that never reaches the vulnerable code path makes the test pass for the wrong
  reason and reports protection that is not being verified.
- [LEARN:quality] A prose-validation check with no negation awareness punishes
  clear prohibitions and pushes authors toward vaguer wording. Scope such a
  check to a sentence and look for negation anywhere before the verb, rather
  than using a fixed-width character lookback.
