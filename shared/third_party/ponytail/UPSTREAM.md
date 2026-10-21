# Ponytail provenance

- Upstream: https://github.com/DietrichGebert/ponytail
- Release: `v5.3.2`
- Commit: `16352ac` (`16352ac229eb08a9598dcae48fe9f2b342567d86`)
- License: MIT
- Imported: 2026-10-21

## Imported files

- `skills/ponytail/SKILL.md` -> `shared/skills/ponytail/SKILL.md`
- `skills/ponytail-review/SKILL.md` -> `shared/skills/ponytail-review/SKILL.md`
- `LICENSE` -> `shared/third_party/ponytail/LICENSE`

The two skill files are a local fork of upstream, not a faithful import. Local
changes go well beyond formatting and frontmatter:

- `shared/skills/ponytail/SKILL.md` is 85 lines against upstream `v5.3.2`'s
  52. It keeps the fork's own `## Persistence` section, seven-rung ladder, and
  longer `## Safety boundaries` list, and it leaves out upstream's reply
  ending, `## Levels` table, `off` mode, and `shortcut:` marker.
- `shared/skills/ponytail-review/SKILL.md` is 65 lines against upstream's
  101. It reviews for unnecessary complexity only, and it leaves out
  upstream's full quality review, four-part findings, and `Verdict:` ending.
- Both files' `description:` frontmatter was rewritten in this bootstrap's
  own wording (not just the required `visibility` field added), and both
  were pointed at this bootstrap's review workflow instead of upstream's.

The fork retains Ponytail's behavior and safety boundaries. The canonical
workflow and review-routing policies decide lifecycle placement and whether the
conditional `ponytail` review profile runs. `ponytail-review` remains an
imported skill, not a profile or lifecycle ceremony. Local policies take
precedence over imported generic workflow wording without modifying the
imported skill files further.

## Local allowlist hashes

- `shared/skills/ponytail/SKILL.md`: `sha256:1e0cf9db9eda588829f2e36d40ab95c0fbf3972dca1d70cf3184f1660612ff54`
- `shared/skills/ponytail-review/SKILL.md`: `sha256:56f23aa917442947ff5caaf18027bcbd17840209c8a051b3fc3a297a867e8450`
- `shared/third_party/ponytail/LICENSE`: `sha256:fb1bc6909ac3ef82d5c22106e32ef682b0cff66788fa915fb9b53b15c9d2f3ab`

## Not vendored

This bootstrap distributes only the portable skill layer and applies it
through its existing target adapters and deterministic review gates. These
upstream parts are not vendored:

- the skills `ponytail-audit`, `ponytail-debt`, `ponytail-gain`, and
  `ponytail-help`;
- `skills/plugin.json`;
- the SessionStart codebase map (`hooks/ponytail-activate.js` loading
  `hooks/ponytail-map.js`);
- the other plugin hooks (mode tracker, subagent, band, board), the status
  line, `commands/`, runtime mode files, and benchmarks.

## Merge record (v5.3.2)

The `v4.8.4` fork (commit `bc9ee94`) was merged with `v5.3.2` by the
three-way procedure below. Evidence, with the quoted upstream hunks and
file:line references, is in
`.claude/explorations/2026-10-20_ponytail-5-evaluation/evidence.md`; the
decision there is PARTIAL ADOPT. Row IDs are the evidence file's.

| Row | Decision | Merged as |
| --- | --- | --- |
| P1 | Adopt | `## Before you write`, worded "Find every place", with the fork's old ladder paragraph folded in |
| P2 | Adopt | First `## Rules` item |
| P3 | Adopt | New `## Safety boundaries` item |
| P4 | Adopt | Ladder rung 2 and the `## Rules` layers-and-conventions sentence |
| P5 | Adopt | `## Rules` shortest-diff item |
| P6 | Adopt | Check rule covers a whole new script or app |
| P7, P8, P9 | Decline | Reply ending, six-rung ladder, and comment rule stay out |
| P10 | Decline | The `ponytail:` marker stays (six live uses) |
| P11, P12 | Decline | Levels, `off`, session persistence, and upstream `description:` stay out |
| P13 | Keep local | The fork's never-cut list is a superset |
| R1 | Adopt, adapted | `## Read first` in `ponytail-review`; names tests, fixtures, and config, and says "search" |
| R2 | Decline | `ponytail-review` stays complexity-only (user decision, 2026-10-20) |
| R3 | Adopt | `reuse:` tag in the skill and in the `ponytail` review profile |
| R4 | Decline | The `code` profile covers `merge:` and `split:` |
| R5 | Adopt, adapted | Concrete case, whole-tree search before `delete:`, marked shortcut is a decision; no expected-load clause |
| R6 | Decline, one line | Only the `Not checked:` ending is merged, in the skill only |
| R7 | Decline | The `performance` profile owns load |
| A1, X1 | Not vendored | See the list above |

One R5 sentence (search the whole tree before calling code unused) comes from
`skills/ponytail-audit/SKILL.md:61-62` at `v5.3.2`, which is not vendored. It
is MIT-licensed under the same `LICENSE`.

## Upgrade procedure

The vendored files are a local fork, not a verbatim copy, so an upgrade is a
**three-way merge** (old upstream baseline -> new upstream release, applied on
top of the local fork) -- never a plain file replacement. Copying a new
upstream file over the local one would silently reintroduce the dropped
sections and undo the local rewording described above.

1. Diff the new upstream release against the `v5.3.2` baseline recorded here
   to isolate the actual upstream delta, and decide each changed hunk as the
   merge record above does.
2. Apply only that delta on top of the current local fork of
   `shared/skills/ponytail/SKILL.md` and
   `shared/skills/ponytail-review/SKILL.md` -- preserve the dropped
   sections' absence, the `## Safety boundaries` renaming, the `## Persistence`
   paragraph, and this bootstrap's own `description:` wording, unless the
   maintainer explicitly decides to re-adopt something upstream changed.
3. Preserve `visibility: public` and this provenance file.
4. Move every pin in the checklist below, computing the hashes from the final
   bytes after all text edits.
5. Refresh `LICENSE` only if upstream's license text itself changed.
6. Run:

   ```bash
   uv run python scripts/generate_targets.py --all
   uv run python scripts/validate_targets.py
   uv run python scripts/check_runtime.py
   ```

### Pin checklist

- This file: release, commit and full SHA, import date, the fork line counts
  above, the local allowlist hashes, and the merge record.
- `scripts/validate_targets.py`: the release and commit strings checked in
  `validate_skills_and_paths`; the two skill sha256 values in `pinned_files`
  (the `LICENSE` value only when upstream's license text changed); the release
  string checked for the installed provenance copy.
- `tests/test_validate_targets.py`: the line-count literals in
  `test_ponytail_upstream_describes_the_real_fork_divergence`; the `old_wrap`
  text in the re-wrap test, only when that paragraph's wrap changes; and
  `SIDECAR_SKILLS_PROFILE_SNAPSHOT_SHA256` with its comment, recaptured from
  `render_sidecar(tmp, "skills")`.
- `scripts/generate_targets.py`: both Ponytail entries of
  `SIDECAR_TEXT_REPLACEMENTS` (the last two lines of `## Persistence`, and
  "Return findings to the coder") must still match the skills byte for byte;
  the anchor test in `tests/test_validate_targets.py` checks this.
- `docs/architecture.md` (`## Ponytail Integration`) and `docs/smoke-tests.md`:
  the release number and the `ponytail-review` description.
