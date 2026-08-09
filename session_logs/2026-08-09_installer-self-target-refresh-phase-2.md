# Session: Installer self-target refresh — Phase 2

**Date:** 2026-08-09
**Plan:** .claude/plans/2026-08-09_phase-2-promote-orphan-skill.md
**Status:** COMPLETED

## Goal

Promote the orphan `safe-consumer-bootstrap-refresh` skill into `shared/` so it
regenerates into every target and survives refreshes, then clear the last drift
failure.

## Work Log

- Copied the skill from the `.claude/skills/` overlay into
  `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md`, body unchanged.
- Added the required `visibility: background` frontmatter. Shared skills must
  declare `public|background`; the overlay copy had neither, since it was never
  authored as source. `background` matches its nature — a diagnostic helper
  loaded by description match, not a slash-menu entry.
- Regenerated. The skill now appears in the generated target and in the Codex
  `[[skills.config]]` set, which the validator requires to equal the
  `shared/skills` set exactly.
- Refreshed this repository's overlay with `--allow-self`.

## Result: Zero Drift

```text
check_runtime.py FAIL count: 0
```

Down from 12 at the start of this work. Before refreshing, a predicted-removals
check reported **0 files would be removed**, and the run removed none —
`settings.local.json` survived, confirming the Phase 1 preservation fix in a
real run rather than only in tests.

The remaining failure had also changed character before this phase: once the
skill existed in `shared/`, it stopped being reported as "absent from generated
target" (an orphan awaiting a decision) and became an ordinary stale file that a
refresh resolves.

## Verification Results

```bash
uv run python scripts/generate_targets.py --all                  # PASS twice
uv run python scripts/validate_targets.py                        # PASS
uv run pytest tests/ -q --tb=short                               # 129 passed
uv run mypy . --ignore-missing-imports --explicit-package-bases  # PASS, 19 files
uv run ruff check scripts/ tests/                                # PASS
uv run ruff format --check scripts/ tests/                       # PASS
uv run python scripts/check_runtime.py                           # 0 FAIL
```

## Score: 100/100 — EXCELLENCE

- Findings: `.claude/quality_reports/findings-20260809T034500Z.json`
- Score: `.claude/quality_reports/score-20260809T034500Z.json`

## [LEARN] Entries

- [LEARN:architecture] A file living only in the generated overlay is not
  content, it is pending deletion. Authored material belongs in `shared/`, where
  it regenerates; the drift checker naming it "absent from generated target" is
  the signal to promote it rather than to restore it again.

## Open Questions / Next Steps

- Native hook re-test completed early on 2026-08-09; the separate persistent-
  thread release gates remain open as recorded below.

## Follow-up Native Codex Evidence — 2026-08-09

The dedicated release probe was refreshed and executed early because Codex
quota was available:

```bash
uv run python scripts/check_native_clients.py \
  --workspace /tmp/native-client-probe-release \
  --client codex --require --timeout 420 --json
```

Codex CLI 0.147.0 passed project trust, root instruction, scoped instruction,
workflow contract, hook, candidate-shim execution, and candidate sentinel
parity checks. This closes the post-refresh native hook follow-up without
changing project trust or approving hooks automatically.

The overall `--require` result remains `FAIL` because `compact_resume`,
`codex_role_matrix`, and `coder_escalation` are still `unexercised` through
`codex exec`. Those are separate release-gate limitations of the non-persistent
execution interface, not hook failures; the MultiAgent V2 removal gate remains
open.
