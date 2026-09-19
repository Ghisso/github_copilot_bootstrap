---
name: openwiki
visibility: public
description: |
  Initialize, refresh, rebaseline, or review this repository's OpenWiki
  knowledge layer (the generated openwiki/ wiki) through the bootstrap-owned
  runner. Use only for that specific generated layer. Do not use for
  README/docs/ writing, general documentation review, or any other wiki or
  knowledge-base tool.
---

# OpenWiki Knowledge Layer

OpenWiki is derived context, not authority: source, tests, and canonical
policy always outrank anything generated under `openwiki/`. See
`.claude/instructions/workspace.instructions.md`'s Knowledge Ownership
section for the full contract; this skill covers only how to run and use
the refresh safely.

## Enablement

OpenWiki is opt-in. It is enabled only when `openwiki/INSTRUCTIONS.md`
exists — a human-authored repository brief the maintainer writes once. Its
presence is also the deterministic marker the runner checks. Do not create
that file on a user's behalf unless asked to enable OpenWiki.

## Running a refresh

Always run the bootstrap-owned runner. Never call `openwiki` directly, and
never pass `--init`:

```bash
uv run python .claude/scripts/openwiki_refresh.py
uv run python .claude/scripts/openwiki_refresh.py --require-enabled
```

Run it as one serial, explicit, model-backed step — never from a hook,
`verify.py`, the installer, state-sync, post-commit, or scheduled CI. The
runner's own `flock` only serializes one refresh invocation against
another; it does not protect against a concurrent agent session writing to
`.claude` in the same checkout. Run the refresh when nothing else in the
checkout is writing to `.claude`, and simply re-run it later if it fails for
that reason — the failure names files OpenWiki never touched, and nothing
is damaged or committed.

## Reading the result

The runner prints one JSON result object. `status: "success"` means the
refresh completed and touched nothing outside `openwiki/**`. Any other
status means it failed closed and changed nothing outside `openwiki/**`:

- **`not_enabled`** — no `openwiki/INSTRUCTIONS.md`; nothing to do.
- **`preflight_failed`** — a precondition (missing `node`/`openwiki`, a
  symlinked `openwiki/` tree, or a lock/snapshot error) blocked the run
  before OpenWiki started.
- **`busy`** — another refresh is already running; wait and retry.
- **`failed`** — OpenWiki exited non-zero, or a write landed outside
  `openwiki/**`. `out_of_scope_paths` and `restoration_errors` name exactly
  what happened.

On any failure, retry the refresh; do not clean up first. A failed run
deliberately leaves `openwiki/.run.json` and partial generated pages on
disk so the next run can resume incrementally, and the runner never
commits, so a failed refresh cannot have published anything. Report the
failure and its named paths to the orchestrator instead of working around
it.

## What never changes

- Never hand-edit a generated page or a `.claims` sidecar under
  `openwiki/**`; run the refresh again instead.
- Never install a host-specific OpenWiki integration as part of an ordinary
  refresh.
- Never create or modify a scheduled workflow for OpenWiki.
- Provider selection and authentication live entirely in the user's own
  `~/.openwiki` (relocatable with `OPENWIKI_CONFIG_DIR`), never in
  repository state. Telemetry is off by default through the runner; a user
  who wants it opts in by setting `OPENWIKI_TELEMETRY_DISABLED` themselves.

## Merge history and rebaseline

Incremental detection depends on the base commit recorded in
`openwiki/.last-update.json` staying reachable. A squash merge or history
rewrite can make it unreachable; treat OpenWiki's own fallback in that case
as degraded incremental assistance, not a failure to fix.

Never use `openwiki --init` to recover. When a clean baseline is genuinely
required: keep `openwiki/INSTRUCTIONS.md`, remove everything else under
`openwiki/**`, and run the standard refresh again — the runner performs a
first generation the same way it performs an incremental one.

## References

- `.claude/scripts/openwiki_refresh.py`
- `.claude/instructions/workspace.instructions.md`
- `.claude/instructions/workflow.instructions.md`
