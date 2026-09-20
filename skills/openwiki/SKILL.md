---
name: openwiki
visibility: public
description: |
  Initialize, refresh, rebaseline, or review this repository's OpenWiki
  knowledge layer (the generated openwiki/ wiki) by calling OpenWiki's own
  MCP tools directly, guarded by this repository's hook. Use only for that
  specific generated layer. Do not use for README/docs/ writing, general
  documentation review, or any other wiki or knowledge-base tool.
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
presence is also the deterministic marker the hook guard checks. Do not create
that file on a user's behalf unless asked to enable OpenWiki.

## Running a refresh

Call OpenWiki's own MCP tools directly — there is no bootstrap runner or
child process. Start with `openwiki_begin`, always with `mode: "update"`.
Never pass `mode: "init"`: a hook guard, `openwiki-guard.sh`, denies it
before the tool runs, because `init` creates a scheduled GitHub Actions
workflow and replaces the wiki wholesale.

The guard snapshots root `AGENTS.md`, `CLAUDE.md`, and the OpenWiki workflow
path immediately before `openwiki_begin` runs, and restores them
byte-for-byte after. Restore coverage differs by host:

- **Claude Code** restores automatically on both a successful call
  (`PostToolUse`) and a failed one (`PostToolUseFailure`).
- **Codex** restores automatically only on a successful call
  (`PostToolUse`) and again at the end of the turn (`Stop`); nothing runs
  automatically if the tool call itself errors.

Because of that gap, always run the restore yourself right after calling
`openwiki_begin`, on every host, whether or not the call succeeded:

```bash
bash .claude/hooks/scripts/openwiki-guard.sh post </dev/null
```

This is redundant but harmless when the host already restored automatically,
and it is the only protection on a Codex tool-call error. Run refreshes
serially: the guard takes no lock, so avoid starting one while another
session is writing to the same checkout.

## Reading the result

There is no runner JSON result. Read `openwiki_begin`'s own MCP response:
the host surfaces a denial from `openwiki-guard.sh pre` as an ordinary
permission-denial message, naming the reason (`mode` was not `update`, the
resolved `root` is not this repository, or `openwiki/INSTRUCTIONS.md` is
missing) — the tool never runs and nothing changes. When the call goes
through, OpenWiki's own response says whether the refresh succeeded or
failed.

Either way, the manual `post` command above tells you what happened: one
line naming what it restored on success, or a nonzero exit naming an
adapter it could not reconcile. Treat that nonzero exit as a real failure —
report it and stop; do not hand-edit the adapter to fix it.

A commit-time check in `verify.py` is the independent backstop: it refuses
a commit that still carries the managed block in `AGENTS.md`/`CLAUDE.md`,
an untracked or newly staged `.github/workflows/openwiki-update.yml`, or a
tracked `openwiki/.run.json`, even if the hook guard was skipped or its
restore was missed.

## What never changes

- Never hand-edit a generated page or a `.claims` sidecar under
  `openwiki/**`; run the refresh again instead.
- Never install a host-specific OpenWiki integration as part of an ordinary
  refresh.
- Never create or modify a scheduled workflow for OpenWiki.
- Provider configuration is optional: OpenWiki's MCP tools run using the
  coding session's own model, not a separately configured provider.
  Anything you do configure lives entirely in your own `~/.openwiki`
  (relocatable with `OPENWIKI_CONFIG_DIR`), never in repository state.
  Nothing in this repository sets `OPENWIKI_TELEMETRY_DISABLED`
  automatically; set it yourself if you want telemetry off.

## Merge history and rebaseline

Incremental detection depends on the base commit recorded in
`openwiki/.last-update.json` staying reachable. A squash merge or history
rewrite can make it unreachable; treat OpenWiki's own fallback in that case
as degraded incremental assistance, not a failure to fix.

Never call `openwiki_begin` with `mode: "init"` to recover — the guard
denies it. When a clean baseline is genuinely required: keep
`openwiki/INSTRUCTIONS.md`, remove everything else under `openwiki/**`, and
call `openwiki_begin` with `mode: "update"` again; it performs a first
generation the same way it performs an incremental one.

## References

- `.claude/hooks/scripts/openwiki-guard.sh`
- `.claude/instructions/workspace.instructions.md`
- `.claude/instructions/workflow.instructions.md`
