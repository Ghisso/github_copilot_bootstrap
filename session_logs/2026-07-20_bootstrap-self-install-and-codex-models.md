# Session: Bootstrap self-installation and Codex model roles

**Date:** 2026-07-20
**Status:** COMPLETED

## Goal

Make interactive Codex sessions selectable by the user while retaining explicit
role models, then enable this bootstrap repository's own nested `ai-state`
sync lifecycle.

## Decisions

- Generated project `.codex/config.toml` leaves the interactive session model
  and reasoning effort unpinned. A user can therefore choose Terra or Sol when
  starting a manual session.
- Generated custom-agent adapters retain canonical `model_intent.openai-codex`
  values. The orchestrator remains `gpt-5.6-sol` with `xhigh` effort.
- This repository self-installs only as a local runtime overlay. `shared/`
  remains the source of truth; generated root adapters are not committed back
  into the source repository.

## Changes

- Updated the target generator and validator to omit and reject generated
  top-level Codex model pins while continuing to validate per-agent model
  intent.
- Updated README and architecture/runtime/smoke-test documentation for the
  interactive-versus-agent model split.
- Configured this repository's existing nested `.claude` repository with the
  outer GitHub origin, restricted its fetch/push refspecs to `ai-state`, and
  installed the generated bootstrap locally.
- Published the initial local bootstrap state as `5f2545e` on `origin/ai-state`.
- Restored tracked bootstrap source adapters after installation and placed the
  local generated runtime overlay in `.git/info/exclude`.

## Verification

- `uv run python scripts/generate_targets.py --all`
- `uv run python scripts/validate_targets.py` — passed.
- `uv run python scripts/check_runtime.py` — passed (with the existing optional
  `gh` warning).
- Confirmed `.codex/hooks.json` invokes `state-sync.sh push` at Codex Stop.
- Confirmed the nested repository is clean and its remote `ai-state` points to
  commit `5f2545e`.

## Learn

[LEARN] A bootstrap source repository can dogfood the generated state-sync
runtime without tracking generated root adapters: retain the source files,
ignore the local overlay through `.git/info/exclude`, and keep state only in
the nested `ai-state` repository.
