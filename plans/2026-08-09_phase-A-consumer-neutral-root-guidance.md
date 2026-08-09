---
name: 2026-08-09_phase-A-consumer-neutral-root-guidance
type: small-plan
parent_plan: guidance-and-review-calibration
phase_index: 1
status: in-progress
closeout_session_log: .claude/session_logs/2026-08-09_guidance-and-review-calibration-phase-A.md
---

# Small Plan: 2026-08-09_phase-A-consumer-neutral-root-guidance

## Scope

Make generated Claude Code and OpenAI Codex root guidance neutral to the consuming project while preserving this authoring repository's tracked root adapters byte-for-byte through generation, installer self-refresh, and state restoration.

## Ownership

- `coder`: canonical generator and installer ownership changes, regression tests, regeneration, and focused verification.
- `verifier`: full tests, typing, linting, formatting, generation, target validation, self-refresh, runtime checks, and root-hash verification.
- `reviewer`: `code`, `architecture`, `security`, `tests`, and `ponytail` profiles.
- `documenter`: user-facing source/generation/ownership behavior where the final diff requires documentation.

## Required Skills

- `ponytail` in `full` mode for all code changes.
- `code-style` and `testing-patterns` where applicable.

## Steps

- [ ] Confirm root `AGENTS.md` SHA-256 is `440279e04b230e856c0670475a9f578ee6eacab1a6aa208323b40e5ce1ebbc8e`.
- [ ] Confirm root `CLAUDE.md` SHA-256 is `34416b9d55a24f2f4cb7f56e60dc47c097f4941da740ced3ea39e6f353455755`.
- [ ] Update canonical root-guidance generation to use consumer-neutral titles, introductions, and ownership wording.
- [ ] Add exact regression assertions rejecting `Bootstrap Guidance`, `reusable multi-agent bootstrap`, `In an installed project`, and `Bootstrap maintainers own authoring and regeneration` in generated roots without banning the word `bootstrap` globally.
- [ ] Force-track the current root `CLAUDE.md` without changing its bytes and add it beside `AGENTS.md` in the authoring-path ownership declaration.
- [ ] Regenerate all targets and exercise installer self-refresh and state restoration.
- [ ] Confirm both root adapter hashes remain unchanged.

## Verification

```bash
uv run pytest tests/test_validate_targets.py -q --tb=short
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/install_bootstrap.py . --allow-self --local-only
uv run python scripts/check_runtime.py
sha256sum AGENTS.md CLAUDE.md
```

## Acceptance Criteria

- [ ] Generated `dist/multi-agent/CLAUDE.md` and `dist/multi-agent/AGENTS.md` describe a generic consumer repository.
- [ ] Neither generated root contains any of the four rejected authoring-specific phrases.
- [ ] Root `AGENTS.md` retains its recorded SHA-256.
- [ ] Root `CLAUDE.md` retains its recorded SHA-256.
- [ ] Both authoring root adapters survive generation, self-refresh, and restoration unchanged.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
