# Session: Workflow sidecar onboarding skill

**Date:** 2026-10-22
**Plan:** `.claude/plans/2026-10-22_phase-B-sidecar-onboard.md`
**Status:** IN-PROGRESS

## Goal

Ship a workflow-only sidecar `onboard` skill that records evidence-based project context and team conventions under `.ai-bootstrap/`, while preserving tracked team files and the skills-only profile.

## Work Log

- Continued from Phase A commit `7c6fdf5` on `sidecar-onboard-and-validator_implementation` with clean outer and nested worktrees.
- Preserved the generated `9292776` sidecar baseline at `/tmp/sidecar-onboard-before-9292776.LWwNp5/sidecar/workflow` before source edits. The temporary team repository at `/tmp/phase-b-old-upgrade-x9uqt3l0` had clean baseline commit `5dd701aedec079c765a5b337698814f5bc0261b4`.
- Added a workflow-only `onboard` skill, its single generator source choice, the sorted 25-skill inventory, and checks of both generated copies. The skills-only profile still has no `onboard`.
- Upgraded the real old-build fixture using the current installer without `--source`: installed only `.agents/skills/onboard` and `.claude/skills/onboard`; 71 existing units, the tracked `CLAUDE.md`, and the team skill bytes stayed unchanged. Both new skills and `.ai-bootstrap/` are ignored, and Git porcelain status is empty. Fixture evidence is under `/tmp/phase-b-old-upgrade-x9uqt3l0/.git/`.
- Updated `README.md` for the new skill, its saved project context, and the Claude Code and Codex discovery behavior. Independent review found and then verified a fix for quoted nested Git commands; final review passed with no findings.
- Ran Claude Code 2.1.226 against `/tmp/phase-b-live-onboard-kl_gvd48`. It loaded and invoked the installed skill, wrote only ignored context and memory files, cited tracked instructions, source/test paths and commit hashes, separated written rules from inferred patterns, and treated a legacy camelCase function and one `wip` commit as outliers. Tracked Git status stayed clean. A repeat run kept one pointer. With `.ai-bootstrap/MEMORY.md` symlinked to tracked `CLAUDE.md`, Claude refused before writing; tracked and context file hashes stayed unchanged, and Git status remained clean. Summaries were checked from the client events and resulting files; no raw transcript was committed.

## [LEARN] Entries

[LEARN] none - no new lessons this session

## Verification

- Generated both targets with `uv run python scripts/generate_targets.py --all`.
- Focused sidecar and validator tests: 272 passed in 78.12s, exit 0.
- Direct `uv run python scripts/validate_targets.py`: PASS, exit 0.
- Fast verifier: PASS (Ruff check and format, 0 violations).
- optional 1: PASS — Claude Code 2.1.226 positive onboarding, repeat-run pointer, and tracked-file symlink refusal all matched the client fixture requirements; tracked Git status remained clean.
- Required closeout summary lines: pending dry run.

## Open Questions / Next Steps

- Phase C remains planned after this phase is committed.
