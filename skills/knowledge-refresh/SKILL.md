---
name: knowledge-refresh
visibility: public
description: |
  Refresh, enable, or rebaseline this repository's generated OpenWiki
  knowledge layer (`openwiki/**`) by calling OpenWiki's own MCP tools,
  guarded by this repository's hook. Not for README/docs writing, general
  documentation review, or any other wiki or knowledge-base tool. Load
  OpenWiki's own `openwiki` skill for the MCP tool sequence itself; this
  skill covers the lifecycle policy around it.
---

# Knowledge Refresh

Two skills split this job. OpenWiki's own `openwiki` skill is the tool
lifecycle and authoring contract — the exact MCP call sequence and what a
generated page may contain. This skill is the lifecycle policy around it:
when to refresh, how to enable it once per checkout, what the guard does,
who owns the result, how to rebaseline, and commit hygiene. Use this skill
only for this repository's generated `openwiki/**` layer. Do not use it for
README/docs writing, general documentation review, or any other wiki or
knowledge-base tool.

OpenWiki is derived context, not authority: source, tests, and canonical
policy always outrank anything generated under `openwiki/`. See
`.claude/instructions/workspace.instructions.md`'s Knowledge Ownership
section for the full contract; this skill covers only how to enable and run
the refresh safely.

## Enablement

OpenWiki is opt-in. It is enabled only when `openwiki/INSTRUCTIONS.md`
exists — a human-authored repository brief the maintainer writes once. Its
presence is also the deterministic marker the hook guard checks. Do not
create that file on a user's behalf unless asked to enable OpenWiki.

## Enabling host integrations (once per checkout)

A person, not an automated step, enables OpenWiki for a checkout:

1. Write `openwiki/INSTRUCTIONS.md` and, if needed, `.openwikiignore`.
2. Run `openwiki integrations install claude --project <root>` and
   `openwiki integrations install codex --project <root>`, once each, for
   this checkout.
3. Approve the project MCP server the installer adds when Claude Code asks.
4. Confirm `openwiki integrations list --project <root>` reports
   `installed` for both hosts.
5. Commit the resulting `.mcp.json` and `.codex/config.toml` diffs.

Never pass `--force`. If either command reports an unmanaged skill
directory already occupying the `openwiki` slot under `.claude/skills/` or
`.agents/skills/`, that is a stale bootstrap copy from before this skill's
rename to `knowledge-refresh`: confirm it has no `.openwiki-install.json`
marker, remove it, then re-run the install command.

## Running a refresh

Call OpenWiki's own MCP tools directly — there is no bootstrap runner or
child process. Start with `openwiki_begin`, always with `mode: "update"`.
Never pass `mode: "init"`: a hook guard, `openwiki-guard.sh`, denies it
before the tool runs, and it also denies an unenabled repository (no
`openwiki/INSTRUCTIONS.md`) or a resolved root outside this repository.

The guard snapshots root `AGENTS.md`, `CLAUDE.md`, and the OpenWiki workflow
path immediately before `openwiki_begin` runs, and restores them
byte-for-byte after. Restore coverage differs by host:

- **Claude Code** restores automatically on both a successful call
  (`PostToolUse`) and a failed one (`PostToolUseFailure`).
- **Codex** restores automatically only on a successful call
  (`PostToolUse`) and again at the end of the turn (`Stop`); nothing runs
  automatically if the tool call itself errors.

Because of that gap, check `git status --porcelain -- AGENTS.md CLAUDE.md`
right after calling `openwiki_begin`; if it is not empty, run the restore
yourself:

```bash
bash .claude/hooks/scripts/openwiki-guard.sh post </dev/null
```

This is redundant but harmless when the host already restored automatically,
and it is the only protection on a Codex tool-call error.

Run at most one refresh per checkout: the guard takes no lock, so avoid
starting one while another session is writing to the same checkout. A
failed run leaves `openwiki/.run.json` behind so the next `openwiki_begin`
in the same checkout can resume it — never delete that file and never
commit it. A response of `noop` means there was nothing left to refresh.
Only report the refresh as successful once `openwiki_finish` returns
`complete`.

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
an untracked or newly staged OpenWiki workflow file (`openwiki-update.yml` under
the GitHub workflows directory), or a
tracked `openwiki/.run.json`, even if the hook guard was skipped or its
restore was missed.

## What never changes

- Never hand-edit a generated page or a `.claims` sidecar under
  `openwiki/**`; run the refresh again instead.
- Never pass `mode: "init"`, and never create or modify a scheduled
  workflow for OpenWiki.
- Never run the integration installer (`openwiki integrations install ...`)
  from a hook, `verify.py`, the bootstrap installer, state-sync, or CI, and
  never run it as a step inside an ordinary refresh. It runs exactly once
  per checkout, by a person deliberately enabling OpenWiki, never `--force`.
- Supported hosts are Claude Code and Codex. Any other target can read
  `openwiki/**` but has no integration to refresh it.
- Provider configuration is optional: OpenWiki's MCP tools run using the
  coding session's own model, not a separately configured provider.
  Anything you do configure lives entirely in your own `~/.openwiki`
  (relocatable with `OPENWIKI_CONFIG_DIR`), never in repository state.
  Nothing in this repository sets `OPENWIKI_TELEMETRY_DISABLED`
  automatically; set it yourself if you want telemetry off. Provider
  credentials are never needed for a host-driven refresh and never enter
  the repository.

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
