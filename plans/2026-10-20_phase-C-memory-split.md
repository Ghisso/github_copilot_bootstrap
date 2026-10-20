---
name: 2026-10-20_phase-C-memory-split
type: small-plan
parent_plan: backlog-followups
phase_index: 3
status: complete
closeout_session_log: .claude/session_logs/2026-10-20_backlog-followups-phase-c.md
---

# Small Plan: MEMORY.md Split and caveman-compress Backup

## Scope

Every non-trivial task starts by reading all of `.claude/MEMORY.md`. On
2026-10-20 it held about 106 KB, 1,530 lines, and 326 `[LEARN]` entries,
against 49,455 bytes and 171 entries on 2026-09-03. This phase moves the
entries that the current memory admission rule would no longer accept into
a dated archive. The working file keeps the rest plus a short index (BF-C1,
BF-C2). Nothing is lost: every entry ends up, unchanged, in exactly one of
the two files, and a script proves it (BF-C1). The archive lives in
`.claude/explorations/`, which a bootstrap refresh already preserves, so the
archive needs no ownership change (option (a)). No gate, hook, or skill
reads entry content from the file, so nothing breaks (BF-C3). The phase
marks the 2026-09-03 exploration as decided (BF-C5).

It also fixes the `caveman-compress` skill, which writes its safety backup
where the next refresh deletes it (BF-C4). Exploration
`2026-09-03_memory-md-size-reduction` §6 recorded that defect.

**Selection rule (BF-C2).** An entry moves only when it fails the existing
admission rule (`shared/skills/learn/SKILL.md:24-31` and `:38-43`, and the
`MEMORY.md` row of the Knowledge Ownership table,
`shared/policies/workspace.instructions.md:53`), with named evidence:

- `E` (enforced): a named test, validator, hook, or `verify.py` check now
  prevents the failure, and the entry's whole instruction is about what
  that check covers.
- `S` (source fact): the entry restates what a named source file already
  shows, such as how one module, script, or test behaves.
- `H` (historical): the entry records one finished plan, incident, pull
  request, or superseded version, and gives no instruction that still
  applies.

Everything else stays: process and judgement lessons that apply beyond one
file, current client and environment behavior, and rationale the code does
not show. An entry also stays when any part of its instruction reaches
beyond what its evidence covers, or when the evidence is unclear. The
`[LEARN:domain]` project pointer always stays, because the `onboard` skill
updates it in place. An entry that tells the agent how to run or recover its
own commands (for example how to work around a guard denial) always stays,
because the orchestrator needs it during Phases D to G. Entries that refer to each other move or stay
together (one known case points to "the parentage-proof entry below").


**Two change sets.** The split, the archive, and the exploration note are
AI state in the nested `.claude` repository; the closeout checkpoints commit
them. The outer commit holds the code, tests, and skill text of BF-C4;
`dist/`, `.claude/`, and `.agents/` are ignored there (`.gitignore:2`,
`:24`, `:26`).

**Cross-phase notes.** Phases A and B run first; the baseline is the file
at the start of this phase. The working file keeps `## Domain-Specific`,
where `onboard` step 4 writes (`shared/skills/onboard/SKILL.md:96-102`). The Phase G
audit treats the working file as live advice and the archive as a dated
record.

## Scope-change record

**2026-10-20, user decision at the step 1 stop condition:** do not apply the
split. Step 1 classified all 328 entries under the rule above and found only
18 to archive (E=7, S=11, H=0; 6,505 of 106,520 entry bytes, 6.11%, below
the 25% stop threshold); applying it would have cut the working file by
about 5% while adding an archive, an index, and a check script. The user
chose to skip the split for now. Consequences: step 3 is not run; BF-C1 and
BF-C3 are not delivered (`MEMORY.md` keeps every entry); BF-C2 is delivered
as evidence only (the classification table is kept beside the 2026-09-03
exploration for a later attempt); BF-C4 and BF-C5 are delivered as planned.

## Steps

- [x] **1. Record the baseline and classify every entry (BF-C2).**
  **Owner:** coder. It works in the session scratch folder and writes
  nothing under `.claude/`.
  **Files:** create `classification.tsv` in the scratch folder.
  **Required Skills:** `shared/skills/learn/SKILL.md`,
  `shared/skills/ponytail/SKILL.md` (full).
  The orchestrator first confirms that
  `git -C .claude diff --quiet HEAD -- MEMORY.md` exits 0 (otherwise it
  checkpoints nested state), then gives the coder the baseline commit from
  `git -C .claude rev-parse HEAD`. Write one tab-separated row per baseline
  entry, in file order, with the columns `ordinal`, `sha256_12`, `heading`,
  `tag`, `disposition`, `reason`, `evidence`, `summary`. `disposition` is
  `KEEP` or `ARCHIVE`. `reason` is `E`, `S`, or `H` for `ARCHIVE` and `-`
  for `KEEP`. `E` and `S` evidence is a tracked outer-repository path,
  optionally `path::symbol` (for example
  `shared/scripts/verify.py::closeout_log_errors`), never a `.claude/` or
  `dist/` copy. `H` evidence names the finished plan slug, pull request, or
  version. `summary` is the entry's first 60 characters on one line. Report
  entry counts and bytes per reason.
  **Stop condition:** when the archived entries hold less than 25% of the
  baseline entry bytes, the orchestrator stops before step 3 and asks the
  user whether to accept that smaller cut. Widening the rule to
  topic-scoped lessons would make the archive live advice, which needs its
  own preserved path and a policy change; that is a separate decision.

- [x] **2. Write the split-and-check tool (BF-C1).**
  **Owner:** coder (scratch folder).
  **Files:** create `split_memory.py` (standard library only). It will live
  beside `archive.md` and `classification.tsv` and runs from the repository
  root.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Contracts:
  - `parse_entries(text: str) -> list[Entry]`. An `Entry` holds its H2
    heading and its exact text: a line starting with `- [LEARN` plus every
    following line that starts with two spaces. Any other line ends it.
  - `split_errors(baseline: str, working: str, archive: str, rows: list[Row], root: Path) -> list[str]`.
  - `write --base <sha>` reads the baseline with
    `git -C .claude show <sha>:MEMORY.md`. It refuses when the working
    `MEMORY.md` differs from the baseline, or when the table does not match
    the baseline row for row (count, ordinal, hash). It writes the working
    file: the original title and comment, a new `## Archived Lessons`
    section, then `## Domain-Specific` and `## Workflow` with the kept
    entries in original order. It writes `archive.md`: a header naming the
    baseline commit, the selection rule, and the command that re-checks the
    split, then the archived entries under the same two headings in
    original order. It prints entry counts, line counts, and bytes before
    and after.
  - The `## Archived Lessons` section contains no `[LEARN` text. It says
    where the archive is; that the archive is a dated record, not loaded
    every session and not corrected later, so current source wins over an
    archived entry; how to search it (`rg -n "<name>" <archive path>`);
    that before weakening or removing a gate, test, hook, or validator, the
    agent searches the archive for its name, because the lesson that
    explains it may be there; and the per-reason counts.
  - `check` reads the baseline commit from the archive header and prints
    every error `split_errors` finds: a baseline entry missing from both
    files or present in both; archived entries that differ from the
    `ARCHIVE` rows by a byte or are out of order; kept entries missing from
    the working file, changed, or out of order; an `E` or `S` path that does
    not exist, or a `::symbol` that does not occur in that file; an `H` row
    without evidence. Entries added to the working file after the split are
    allowed, so closeout `[LEARN]` entries pass. A later in-place correction
    of a kept entry makes `check` fail by design; the archive header says
    so, because `check` proves this split, not a standing rule.
  - `selftest` runs `split_errors` on mutated copies of the real inputs (one
    archived entry dropped, one byte changed in a kept entry, one archived
    entry copied into the working file, one `E` path renamed). It exits
    non-zero unless every mutation produces at least one error.
  - It must not edit, merge, reorder, or re-tag any entry. Tag cleanup
    (`tests` versus `testing`) is out of scope.

- [x] **3. Apply the split (BF-C1, BF-C3).** Not run: dropped by the
  2026-10-20 scope change above.
  **Owner:** orchestrator, in the main thread. Claude Code treats every path
  under `.claude/` as a sensitive file, so a background subagent cannot get
  write approval there (MEMORY `[LEARN:verification]` on the 2026-10-02
  write gate; `docs/sidecar-provider-contract.md:989-1004`).
  **Files:** create `.claude/explorations/2026-10-20_memory-archive/`
  with `archive.md`, `classification.tsv`, and `split_memory.py`; modify
  `.claude/MEMORY.md`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full).
  Copy in the table and the script after the coder's self-review. Run
  `write --base <sha>`, then `check` and `selftest`. Then checkpoint nested
  state with
  `git -C .claude add -A && git -C .claude commit -m "checkpoint: memory split"`.
  Record the before and after bytes, line counts, and entry counts in the
  session log. When review changes the table, restore the baseline with
  `git -C .claude show <sha>:MEMORY.md > .claude/MEMORY.md` and run `write`
  again; never edit the two files by hand.

- [x] **4. Mark the 2026-09-03 exploration decided (BF-C5).**
  **Owner:** orchestrator.
  **Files:** modify
  `.claude/explorations/2026-09-03_memory-md-size-reduction/evidence.md`.
  Its line `**Status:** OPEN — paused for a later decision by the user` now
  misleads a reader into redoing the work. Change it to a decided status and
  add one `**Outcome (2026-10-20):**` line naming the measured result (6.11%
  under the rule), the user's decision not to split for now, where the
  classification table is kept, and the `caveman-compress` fix. Leave the
  rest of this dated record unchanged.

- [x] **5. Keep `caveman-compress` backups where a refresh cannot delete them (BF-C4).**
  **Owner:** coder. Steps 1-2 and this step touch disjoint files, so
  separate coders may run them in parallel.
  **Files:** modify `shared/skills/caveman-compress/scripts/detect.py`,
  `shared/skills/caveman-compress/SKILL.md` (workflow steps 4, 5, 8, and 10,
  and its `## Verification` list), and
  `tests/test_caveman_compress_detect.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`,
  `shared/skills/caveman-compress/SKILL.md`.
  Add `backup_path(filepath: Path) -> Path` and a `backup_path: str` field
  on `DetectionResult`, and print `Backup: <path>` for a compressible
  target. Rule: take the nearest ancestor folder named `.claude`. Use the
  sibling `<stem>.original.md` in three cases: there is no such folder; the
  target is inside its `plans`, `explorations`, `session_logs`, or
  `quality_reports` folder; or that `.claude` has no `explorations` folder
  (a team-owned `.claude` beside a sidecar install, or the user-level
  `~/.claude`). Otherwise use
  `<.claude>/explorations/caveman-compress-backups/<path relative to .claude>`
  with the file name `<stem>.original.md`, because a refresh deletes every
  unknown file elsewhere under `.claude/`
  (`scripts/install_bootstrap.py:573-627`). SKILL.md step 5 writes the
  backup at the printed `Backup:` path; steps 4, 8, and 10 and the skill's
  Verification list name that path instead of "beside" the target.
  Keep both files generic. The sidecar workflow profile copies this skill
  whole and scans every file for its forbidden tokens
  (`scripts/validate_targets.py:8824-8866`, `:9003-9016`), but rewrites
  state paths only in SKILL.md (`scripts/generate_targets.py:207-222`).
  So name no `.claude/<state folder>/` path and no memory-file path in
  either file, and keep the existing protected-target refusals
  (`detect.py:160-185`) and exit codes (`detect.py:223-242`).
  **Tests, with expected paths written as literals:** `.claude/MEMORY.md`
  maps to `.claude/explorations/caveman-compress-backups/MEMORY.original.md`;
  `.claude/instructions/project-context.instructions.md` maps to
  `.claude/explorations/caveman-compress-backups/instructions/project-context.instructions.original.md`;
  one target in each preserved folder, one outside `.claude`, and
  `.ai-bootstrap/MEMORY.md` keep the sibling; a `.claude` without
  `explorations` keeps the sibling; the CLI prints the `Backup:` line; a
  `*.original.md` target is still refused. A parity test asserts that the
  detector's preserved folders equal the entries of
  `runtime_ownership.CONSUMER_STATE_PATHS` that contain no `.`, so a future
  ownership change fails here first.


- [x] **6. Regenerate, refresh, prove durability, review, close out.**
  **Owner:** orchestrator; fresh reviewer.
  **Required Skills:** `shared/skills/documentation/SKILL.md`,
  `shared/skills/code-review/SKILL.md`.
  Run `uv run python scripts/generate_targets.py --all` and
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  before verification. When auto mode denies the refresh, hand it to the
  user. The `caveman-compress` skill text is the backup change's
  documentation; no other surface describes the backup location. The
  reviewer gets the outer diff, the nested diff of the 2026-09-03
  exploration, and the scope-change record.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/test_caveman_compress_detect.py -q
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Run the generated `detect.py` on a scratch `.claude/MEMORY.md` beside an
  `explorations` folder and record the printed `Backup:` path.


## Review Profiles

Use `.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Give the reviewer the
exploration `2026-09-03_memory-md-size-reduction` (§5, §6), BF-C4 and
BF-C5, the scope-change record, and the final outer diff.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
