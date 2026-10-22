# avoid-ai-writing provenance

- Upstream: https://github.com/conorbronsdon/avoid-ai-writing
- Release: `v3.25.0`
- Commit: `3c0fd8a2668962df97f0a6771dcd57c84a4be568`
- License: MIT
- Imported: 2026-08-20

## Imported files

- `SKILL.md` -> `shared/third_party/avoid-ai-writing/SKILL.md`
- `LICENSE` -> `shared/third_party/avoid-ai-writing/LICENSE`

## Local hashes

- `shared/third_party/avoid-ai-writing/SKILL.md`: `sha256:1caf9c5191332437d985c9d8a58434f8a6333b913d09819db80ade4093d54013`
- `shared/third_party/avoid-ai-writing/LICENSE`: `sha256:4da9b9f0bb899269b6e79fb383b4c3f24ebcadf7352f970871bae3e215401589`

The snapshot is inert provenance. The live local adaptation is
`shared/skills/humanize/SKILL.md`. It follows local policy first and does not
import the upstream detector, scripts, examples, plugins, or runtime tooling.

## Upgrade procedure

1. Verify the intended upstream release, commit, and MIT license.
2. Copy only `SKILL.md` and `LICENSE` from that pinned commit.
3. Record actual local SHA-256 hashes, the import date, and excluded content.
4. Review the compact local `humanize` adaptation against local policies; do
   not expose the upstream snapshot as a public skill.
5. Run target generation and validation before accepting the update.
