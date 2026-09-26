# Consumer sidecar bootstrap overlay: independent re-review (Opus)

**Date:** 2026-09-26
**Reviewed HEAD:** `010f08c` on `consumer-sidecar-bootstrap-overlay_implementation`
**Big plan:** [consumer-sidecar-bootstrap-overlay](../plans/consumer-sidecar-bootstrap-overlay.md)
**Companion report:** [hardening re-review](2026-09-26_consumer-sidecar-bootstrap-overlay-review.md) (findings R1-R5)
**Earlier reports:** [round 1](2026-09-25_consumer-sidecar-bootstrap-overlay-review.md), [round 2](2026-09-25_consumer-sidecar-bootstrap-overlay-review-2.md)

## Verdict

**FAIL: three MAJOR findings, thirteen MINOR findings, and several NITs.**
Keep the architecture. The branch is not ready for a PR: phase-scoped
reviews missed interactions between features added in different phases,
and one defect sits inside a Phase H review fix.

## Method

An independent Opus agent reviewed the whole branch against the big plan,
the nine small plans, the session logs, and both 2026-09-25 review reports,
with instructions to be skeptical of those records. It read
`scripts/sidecar_overlay.py` in full, plus the installer diff,
`runtime_ownership.py`, `update_consumers.py`, the plan validator, the
tests, and the docs. It checked each finding with a real-Git pytest
reproduction, except where the finding says "reasoned". Each reproduction
asserts the promised behavior, so a failing test means the defect is
present. The orchestrator re-ran the reproductions for O1, O2, O3 (both
scenarios), and O5; all five fail at `010f08c`. The repository and the
nested `.claude` repository stayed clean.

The reproductions lived in this session's scratch folder
(`.../scratchpad/independent-review/`), which is not durable. Each finding
below describes its scenario precisely enough to rebuild the test in
`tests/`.

## Mapping to the companion report

| This report | Companion report | Note |
| --- | --- | --- |
| O1 | R1 | Same defect. R1 adds a variant: a disk-only nested repository at a unit is moved into the preserved folder, `.git` included. |
| O2 | R2 | Same defect. |
| O7, O8 | R3 | Same two symlink cases. R3 rates them MAJOR. |
| O17 (special-file bullet) | R4 | Same defect. R4 rates it MAJOR. |
| none | R5 | Only in the companion report: the settled-refresh check trusts a sibling's `status` without checking its identity or confinement. |
| O3-O6, O9-O16, O18, O19 | none | Only in this report. |

## Findings

### O1. MAJOR (safety): a team submodule at a recorded unit path

Location: `scripts/sidecar_overlay.py` `_SIDECAR_STRUCTURAL_PATHS` (the
boundary check covers only the write roots and bridge parents), preflight
around lines 2705-2707, `_unit_index_relpaths` around lines 1799-1815 (a
gitlink unit's tracked set is `{""}`, so every checked-out file counts as
untracked), `_team_takeover` around lines 830-836 (deletes files whose bytes
match the record), and `_check_ignore` around lines 1752-1767 (hides the
fatal error from `check-ignore`).

Scenario: the sidecar is installed. The team adds upstream ponytail as a
submodule at `.claude/skills/ponytail`, and the person initializes it.
Every install then exits 1 with a false ignore-gate message that lists
correctly ignored paths and blames a `.gitignore` negation. `--uninstall`
exits 0 after deleting `LICENSE` inside the team's submodule: `git status`
shows ` M .claude/skills/ponytail`, and the submodule shows ` D LICENSE`.

This contradicts Decision 28 and the "team files byte-identical after
uninstall" invariant. The Phase H log accepted the structural-only check
because "the sidecar never writes into" a unit-level nested repository;
that reason is wrong for a tracked gitlink. The README and the OpenWiki
sidecar page claim that skill units are checked.

Fix direction: check repository boundaries at every required unit, and
plan no file actions for a unit whose tracked set holds the unit path
itself.

### O2. MAJOR (correctness): uninstall after a profile change exposes an edited copy of a dropped skill

Location: `plan_sidecar_reconciliation` around lines 1223-1235. In
uninstall mode `taken_skills = set(SIDECAR_SKILLS)`, so a recorded or
listed unit of a skill the current bootstrap no longer ships is never
converted.

Scenario: version 1 installs `humanize` and the person edits it. Version 2
drops `humanize`, so the edited copy is correctly kept. `--uninstall` then
leaves it as locally modified, removes the whole block, deletes the
manifest, and exits 0. `?? .claude/skills/humanize/SKILL.md` appears in
`git status`, and the sidecar no longer records the copy.

This contradicts Decision 34, the Done Criterion that no run exposes a
sidecar file, and the OpenWiki uninstall text.

Fix direction: during uninstall, treat every classified unit as taken.

### O3. MAJOR (correctness): false preserve conflicts; uninstall can be blocked permanently

Location: `uninstall_sidecar` around lines 3084-3095 computes
`preserved_conflicts` for every required unit whose destination name
exists, including units only being removed and absent units (which share
the empty hash). The apply step and the dry run branch on that raw set,
and their gates then check paths whose lines were correctly dropped.

Scenarios:

- A first install crashes, or the manifest is moved aside. The person
  uninstalls (preserving every listed copy), reinstalls, and uninstalls
  again. The dry run and the real run both exit 1 with a gate failure
  listing all 10 units and a false `.gitignore` remedy. The units are
  already gone, the old block is restored, the manifest stays, and staging
  still holds the removed copies.
- A symlink at a unit is preserved once. Later the team takes that skill,
  so the unit is absent. Every `--uninstall` now fails its gate before any
  write (3 of 3 runs exit 1), so the person can never uninstall.

The Phase H fix ("build the gates from the authoritative set
`preserved_conflicts`") made the set too broad.

Fix direction: let the planner report the units it actually kept because
of a conflict, and use only those.

### O4. MINOR: a listed retained file of a dropped skill is un-hidden without a report

Location: `required_snapshot_units` never adds the owning unit of a file
line in the block, so the carry-forward loop sees an empty snapshot and
drops the line.

Scenario: a team takes over `humanize` and the person's `notes.md` is
retained. Version 2 drops `humanize`. The manifest is moved aside, as the
invalid-manifest remedy says. The next run silently exposes
`?? .claude/skills/humanize/notes.md`. Uninstall has the same gap and
omits the "now visible" report. This contradicts Decision 23.

### O5. MINOR: `str.splitlines()` turns a retained name into a raw pattern

Location: the block parsers and writers (around lines 606, 613, 1428, 2097,
2124). Python also splits on `\f`, `\v`, `\x1c`-`\x1e`, U+0085, U+2028, and
U+2029; Git splits only on `\n`.

Scenario: a retained file named `x\fsrc`. The next run re-reads the block
and writes a separate `src` line as an "unrecognized line", which hides
every untracked path named `src`: the team's `app/src/main.py` disappeared
from `git status`. Decision 29 is incomplete.

### O6. MINOR: the case variant at a write root (S12) is not fixed

Location: `_read_list_skill_names` around line 1947: `_reflects_a_write_root`
is true for a write root itself, so disk names at write roots are always
empty. The only test injects `{".claude/skills": {"Ponytail"}}` into the
pure planner, which a real run never produces.

Scenario: `core.ignorecase=true` on a case-sensitive filesystem with a
personal `.claude/skills/Ponytail/`. The sidecar installs `ponytail`, and
Git's case-insensitive match of `/.claude/skills/ponytail` hides the
personal folder.

### O7. MINOR: a per-entry symlink into a write root makes runs flip

Location: `_declared_skill_names` around lines 2016-2036 follows
`.github/skills/ponytail -> ../../.claude/skills/ponytail`, but the name
scan skips it. Across runs the copy exists, then not, then exists.

### O8. MINOR: frontmatter names are not read through a symlinked read-only root

Location: `_declared_skill_names` around line 2019 skips a symlinked root,
although folder names are listed through it. A team `.codex/skills ->
../shared-skills` with `team-review/SKILL.md` declaring
`name: ponytail-review` does not stop the sidecar from installing
`ponytail-review`.

### O9. MINOR: a symlink inside a tracked team skill folder aborts the whole run

Location: the symlink abort (around lines 1847-1850 and 1177-1182) runs
before the tracked check. Decision 25 says a tracked unit is team-owned
"before any symlink check".

### O10. MINOR: S15 bullet 1 is not fixed

Location: `run_ignore_gate` passes the whole expected set to
`_parse_check_ignore_verbose`, which adds every record `-v -n` prints,
including correctly ignored paths. With a team `!/.claude/skills/humanize`
rule, the failure lists all 10 paths, and the one real failure is labeled
a directory-only rule. Phase H step 10 is ticked as done.

### O11. MINOR: the gate never checks unfinished units, which are reported as hidden

Location: `_write_raw_paths` builds the gate set from manifest records and
actions only. A team negation can expose a listed copy with no record
while the run exits 0 and reports "It stays hidden".

### O12. MINOR: "skips at every root" while a conflicting edited copy stays

Location: the taken-skill report (around lines 1218-1221) and
`_read_only_taken_remedy`. The Done Criterion "a taken skill never keeps a
copy at any root" is absolute, although Decision 24 keeps the copy on a
conflict.

### O13. MINOR (tests): the precedence property test does not cover `adopt` or `unchanged`

Location: `tests/test_sidecar_overlay.py` around lines 905-944. The adopt
fixture produces an unfinished unit (content differs from desired), and
the unchanged fixture produces an update. A mutation that brings back the
R1 adopt escape passes all 97 planner tests; only 4 real-Git tests catch
it.

### O14. MINOR: README claims the Phase I audit called correct

- `README.md` around lines 692-696 says both generated targets are checked
  against one exact allowlist; full mode checks only `state-sync.sh`.
- `README.md` around lines 678-683 says sidecar mode checks a skill unit
  against the repository boundary; it does not (O1).

### O15. MINOR: "a path the full install writes" is broader than the code

The big plan and the README promise a refusal when the target tracks a path
the full install writes. `FULL_INSTALL_ROOT_PATHS` leaves out `.gitignore`,
so a team repository that tracks only code and `.gitignore` still gets a
full takeover that edits its `.gitignore` and sets `core.hooksPath`.
Reasoned from the code.

### O16. MINOR: uninstall never prints the preserved folder path

Decision 34 and Phase H step 9 say it does. `_uninstall_sidecar_apply`
prints a `PRESERVED` line only for copies this run preserves. Reasoned.

### O17. NITs

- `tracked_generated_paths` can now raise `GitDetectionError` inside the
  full install's `warn_tracked_paths`, after most writes; before, it only
  skipped the warning.
- The `--mode full` refusal does not mention `--uninstall`.
- The named-pipe test's "hard deadline" cannot fire: the executor's
  shutdown waits for the hung thread.
- The unit hash ignores named pipes, sockets, and empty folders, so a
  matching remove or update also deletes such a personal entry (the
  companion report's R4 rates this MAJOR).

### O18. Over-engineering

Uninstall has its own apply path with gates that run only on conflicts,
plus a near-copy of `_apply_actions`. That path needed four review rounds
and still carries O3. Reusing the install's write order would give the
same safety more simply: write the write-phase block, run one gate over
every line it keeps, apply actions, write the final block, and remove the
block only when no unit is kept.

### O19. Process

- The Phase H deviation from Decision 28 (write roots and bridge parents
  only) was accepted "for review to confirm", but Decision 28 was never
  amended, and the docs state the original rule.
- The Done Criterion "every confirmed finding has a regression test or a
  documented disposition" is not met for S15 bullet 1 or for S12 at write
  roots.

## Checked and found correct

- The full-install tests change only the expected `--mode full` in one
  branch-switch test; full mode gains the source check after the takeover
  validation.
- Mode detection follows the table, including the `--uninstall` rule; Git
  errors abort detection; `.claude/.git` counts only as a directory with no
  `.claude` index entry; the environment scrub runs first in `main()`.
- Git-directory paths come from `--git-dir` with `lstat` checks; the marker
  check is shared by detection and preflight.
- The install write order is correct; the crash-recovery rows (adopt,
  drop, install) are consistent.
- The exact sidecar source set is shared with the validator.
- `update_consumers.py` continues after a failed target and never forwards
  `--uninstall`.
- The Phase F validator parses under Python 3.9 grammar, fails closed, and
  still requires a final refresh phase (the companion report's R5 found an
  identity gap this review missed).
- The profile patch in `tests/sidecar_test_helpers.py` matches real version
  changes, but no test runs uninstall after a profile change (O2).
- The real-Git suites catch the adopt-escape mutation (4 tests fail).
