# Ponytail provenance

- Upstream: https://github.com/DietrichGebert/ponytail
- Release: `v4.8.4`
- Commit: `bc9ee94`
- License: MIT
- Imported: 2026-07-18

## Imported files

- `skills/ponytail/SKILL.md` -> `shared/skills/ponytail/SKILL.md`
- `skills/ponytail-review/SKILL.md` -> `shared/skills/ponytail-review/SKILL.md`
- `LICENSE` -> `shared/third_party/ponytail/LICENSE`

The two skill files are a reduced local fork of upstream, not a faithful
import. Local changes go well beyond formatting and frontmatter:

- `shared/skills/ponytail/SKILL.md` is 72 lines against upstream `v4.8.4`'s
  120. The `## Output`, `## Intensity`, and `## When NOT to be lazy`
  sections were dropped, and `## Boundaries` was renamed to
  `## Safety boundaries`.
- `shared/skills/ponytail-review/SKILL.md` is 38 lines against upstream's
  57, with a comparable amount of upstream review ceremony removed.
- Both files' `description:` frontmatter was rewritten in this bootstrap's
  own wording (not just the required `visibility` field added), and both
  were pointed at this bootstrap's review workflow instead of upstream's.

The fork retains Ponytail's behavior and safety boundaries. The canonical
workflow and review-routing policies decide lifecycle placement and whether the
conditional `ponytail` review profile runs. `ponytail-review` remains an
imported skill, not a profile or lifecycle ceremony. Local policies take
precedence over imported generic workflow wording without modifying the
imported skill files further.

The exact line wrapping of the paragraph above is load-bearing:
`scripts/validate_targets.py` matches it as literal substrings that span line
breaks, so re-flowing it fails the target validator even when the wording is
unchanged. Re-wrap only together with that check.

## Local allowlist hashes

- `shared/skills/ponytail/SKILL.md`: `sha256:9e2611144a8da730f110af6f789fd4dc9f6574f7fbff1fd5be7220b0b30a6fc3`
- `shared/skills/ponytail-review/SKILL.md`: `sha256:bf0f50e5a406c8c1587ab4a69340369bf0293ef1022450cb9142468aa15f8656`
- `shared/third_party/ponytail/LICENSE`: `sha256:fc5bd8de55887831701aa9b9da85925fe0a581680187a5e23f2cf74235aadcd4`

Ponytail's plugin hooks, status line, benchmarks, and runtime mode files are
not vendored. This bootstrap distributes the portable skill layer and applies
it through its existing target adapters and deterministic review gates.

## Upstream survey (v4.9.0)

Checked 2026-09-12 against upstream `v4.9.0` (2026-08-08), one release ahead
of the pinned `v4.8.4`. Across the three vendored files, the entire delta is
one bullet in `skills/ponytail/SKILL.md` (upstream commit `b6c0448`,
narrowing the `ponytail:` marker to real corner-cuts only).
`ponytail-review/SKILL.md` and `LICENSE` are unchanged between the two tags.

That single change is already present in this bootstrap's local fork at
`shared/skills/ponytail/SKILL.md:51-52`. A bump to `v4.9.0` would therefore
change no local behavior and no file hash — it is not done for that reason
(see the parent plan's "do not bump Ponytail to v4.9.0" decision). Re-run
this survey against whichever upstream release is current the next time a
real behavioral difference is suspected.

## Upgrade procedure

The vendored files are a reduced local fork, not a verbatim copy, so an
upgrade is a **three-way merge** (old upstream baseline -> new upstream
release, applied on top of the local fork) — never a plain file replacement.
Copying a new upstream file over the local one would silently reintroduce
the dropped sections and undo the local rewording described above.

1. Diff the new upstream release against the `v4.8.4` baseline recorded here
   to isolate the actual upstream delta (see the survey above for the
   `v4.9.0` result as a worked example of this step).
2. Apply only that delta on top of the current local fork of
   `shared/skills/ponytail/SKILL.md` and
   `shared/skills/ponytail-review/SKILL.md` — preserve the dropped
   sections' absence, the `## Safety boundaries` renaming, and this
   bootstrap's own `description:` wording, unless the maintainer explicitly
   decides to re-adopt something upstream changed.
3. Preserve `visibility: public` and this provenance file.
4. Update the release, commit, import date, and local allowlist hashes above
   to match the new upstream baseline actually merged from.
5. Refresh `LICENSE` only if upstream's license text itself changed.
6. Run:

   ```bash
   uv run python scripts/generate_targets.py --all
   uv run python scripts/validate_targets.py
   uv run python scripts/check_runtime.py
   ```
