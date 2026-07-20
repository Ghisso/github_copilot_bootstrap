---
name: consumer-local-only-update
type: big-plan
status: complete
originating_branch: dev
implementation_branch: consumer-local-only-update_implementation
started_at: 2026-07-20T14:59:36Z
phases:
  - 2026-07-20_phase-9-local-only-consumer-updates
current_phase: 2026-07-20_phase-9-local-only-consumer-updates
---

# Big Plan: Consumer Local-Only Update

## Context

Consumer refreshes currently combine a complete bootstrap update with private
`ai-state` publication. Agent environments can safely update local files but
may require separate authorization for external private-state pushes. The
source repository's ignored self-install overlays also need validation that
distinguishes local generated runtime files from tracked legacy source mirrors.

## Goals

- Add a complete, durable `--local-only` consumer refresh with zero remote Git
  I/O.
- Preserve the existing update-and-push default for human terminal use.
- Prove legacy state is committed before generated replacement.
- Accept only ignored, byte-identical self-install overlays.
- Document and adversarially verify both update modes.

## Design Overview

Reuse the existing installer and shared state-sync helper. Put one local-only
boundary around all remote operations, require installer-owned nested-Git
postconditions, and exercise the real validator through pytest.

## Phases

- [x] `2026-07-20_phase-9-local-only-consumer-updates`

## Verification

```bash
bash -n shared/hooks/scripts/state-sync.sh
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy scripts/ --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
```
