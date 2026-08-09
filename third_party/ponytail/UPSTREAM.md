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

The two skill files retain Ponytail's behavior and safety boundaries. Local
changes are limited to formatting, the bootstrap's required `visibility`
frontmatter, and references to this bootstrap's review workflow. The canonical
workflow and review-routing policies decide lifecycle placement and whether the
optional `ponytail-review` profile runs; they take precedence over imported
generic workflow wording without modifying the imported skill files.

## Local allowlist hashes

- `shared/skills/ponytail/SKILL.md`: `sha256:9e2611144a8da730f110af6f789fd4dc9f6574f7fbff1fd5be7220b0b30a6fc3`
- `shared/skills/ponytail-review/SKILL.md`: `sha256:bf0f50e5a406c8c1587ab4a69340369bf0293ef1022450cb9142468aa15f8656`
- `shared/third_party/ponytail/LICENSE`: `sha256:fc5bd8de55887831701aa9b9da85925fe0a581680187a5e23f2cf74235aadcd4`

Ponytail's plugin hooks, status line, benchmarks, and runtime mode files are
not vendored. This bootstrap distributes the portable skill layer and applies
it through its existing target adapters and deterministic review gates.

## Upgrade procedure

1. Read the new upstream release notes and compare it with `v4.8.4`.
2. Refresh only the two imported skill files and the license.
3. Preserve `visibility: public` and this provenance file.
4. Update the release, commit, import date, and local allowlist hashes above.
5. Run:

   ```bash
   uv run python scripts/generate_targets.py --all
   uv run python scripts/validate_targets.py
   uv run python scripts/check_runtime.py
   ```
