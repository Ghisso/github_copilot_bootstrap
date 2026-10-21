# Session: Backlog follow-ups — Phase F, OpenWiki 0.7 upgrade

**Date:** 2026-10-21
**Plan:** .claude/plans/2026-10-20_phase-F-openwiki-0.7-upgrade.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** IN-PROGRESS

## Goal

Move the pinned OpenWiki tool from `0.5.2` to `0.7.2` without weakening the
`openwiki_begin` guard (BF-F1 to BF-F7), with the guard hardened to allow
only `mode: "update"` either way.

## Task Tracking

- [x] PRE-FLIGHT: Phase E committed (`02e22de`) and pushed; Phase F is the
  current phase. Phase E outcomes do not affect Phase F; no planner.
- [x] IMPLEMENT/VERIFY/REVIEW — two review rounds; round 1 `PASS` with three
  MINORs (all fixed), round 2 `PASS` with no findings.
- [x] CLOSEOUT: documentation, final AI state, checkpoint, staged index,
  findings, phase receipt, closeout dry run, checkpoint, closeout receipt.
- [ ] COMMIT
- [ ] PUSH

## Work Log

- **Earlier (during Phase C's wait)** - Step 1 ran in the scratch folder
  (evidence only; capture below). Result: GO, all eight stop conditions
  PASS.
- **Start** - Delegated step 2 (docs, skill, policies) to a documenter and
  step 3 (real-binary round-trip test, strict `mode` check) to a coder, in
  parallel on disjoint files. Step 4 (environment upgrade) is user-owned.
- **Later** - Step 2 done: `docs/runtime-checks.md` gains an `openwiki`
  optional-helper entry, a six-step pin-upgrade procedure with its stop
  rule, and the corrected Dockerfile line; `knowledge-refresh` says
  "once when enabling, once per pin change", never `--force`, never other
  host integrations, and that the guard allows only `update`;
  `tool-routing.instructions.md` routes the read-only OpenWiki tools as
  just-in-time derived context; `workflow.instructions.md` OpenWiki Refresh
  says the guard denies every other mode, `init` included, and a call with
  no `mode`. Generate + validate PASS.
- **Later** - Step 3 done at `0.5.2`: the handshake test pins
  `openwiki_begin`'s `required` and `mode.enum`; new
  `test_real_openwiki_begin_update_is_restored_by_the_guard` runs the real
  binary with an isolated `HOME`, asserts begin touches only `openwiki/`
  and the two adapters, and that `post` restores every other file byte for
  byte; `_cmd_pre` denies any `mode` other than `"update"`, missing
  included; docstring version-free. Negative controls: the two new deny
  cases failed on the old guard (it allowed them); the round trip failed
  with `post` stubbed out in a scratch copy. 78 tests pass; the smoke test
  also passes under `unshare -rn` (offline).
- **Later** - Step 5 prepared by a coder ahead of step 4 (pin `0.7.2` in
  the Dockerfile and validator, ten tools in `EXPECTED_TOOLS`); the smoke
  test is expected to fail locally until the user's global install.
  Asked the user to run step 4; the user chose to run the commands
  themselves.
- **Before step 4** - `command -v openwiki` = `/home/ghisso/.local/bin/openwiki`;
  global package version `0.5.2`; both installed skill receipts
  (`.claude/skills/openwiki/` and `.agents/skills/openwiki/`) say `0.5.2`;
  `git status --porcelain` shows no change to the root MCP adapters. With
  the step 5 pin already moved, the smoke test fails only at the version
  assertion (`'0.5.2' == '0.7.2'`), as expected; the round-trip test passes
  on `0.5.2`; generate + validate PASS.
- **Step 4, first attempt (user)** - After the user's run, a new session
  showed a partial result: the only global install
  (`~/.local/nodejs/node-v24.15.0-linux-x64/lib/node_modules/openwiki`)
  still reported `0.5.2`; the Claude skill receipt said `0.7.2` (written
  10:26:40); the Codex skill had been rewritten by `0.5.2` (10:27:31) and
  `integrations list` showed `bob modified`; the root MCP adapters were
  unchanged. Reported to the user, who approved the orchestrator running
  the commands.
- **Step 4, second attempt (orchestrator, user-approved)** -
  `npm install -g openwiki@0.7.2`: exit 0 ("added 40 packages, and changed
  292 packages"); the PATH binary now resolves to the same global package,
  version `0.7.2`. `openwiki integrations install claude --project <root>`
  and `... codex --project <root>` (no `--force`): both exit 0. Both
  receipts now say `0.7.2`; `git status --porcelain` shows no change to the
  root MCP adapters; `integrations list`: `claude installed`,
  `codex installed`, every other host `not-installed` (`bob` no longer
  `modified`). `uv run pytest tests/test_openwiki_cli_smoke.py
  tests/test_openwiki_guard.py tests/test_lifecycle_hooks.py -q`: 78
  passed; the smoke test also passes under `unshare -rn` (offline).
  Rollback, if ever needed: `npm install -g openwiki@0.5.2` and the same
  two install commands. This session's OpenWiki server was started on
  `0.5.2` and is now stale; Phase G needs a reconnect or a new session.
- **Verify and review** - Regenerated and self-installed;
  `git status --porcelain -- AGENTS.md CLAUDE.md` empty; `check_runtime.py`
  only PASS lines; `verify.py phase` PASS (3270 passed). Review round 1
  (six profiles, commit gate): `PASS`, three MINORs: the upgrade procedure
  said "both `openwiki@` lines" (only one line has it; the other is the
  `package.json` check); `_file_bytes` excluded the whole `shared/` tree
  (weakening stop rule (a)); two over-long lines in the knowledge-refresh
  skill. All fixed; 33 OpenWiki tests pass; `verify.py phase` PASS again
  (3270 passed). Review round 2: `PASS`, no findings.

## Step 1 capture table

Date: 2026-10-21. Plan: `.claude/plans/2026-10-20_phase-F-openwiki-0.7-upgrade.md`, step 1, items 1-6.

### Setup

- Install (network): `npm install --prefix phase-f/pkg openwiki@0.7.2` -> exit 0, 333 packages.
  `diff -rq` of `pkg/node_modules/openwiki` against the planner's `npm pack` of 0.7.2
  (`plan-e/v0.7.2/package`): identical except the nested `node_modules/`.
- Node v24.15.0 (package needs `>=22.22.0`).
- Every probe ran as `unshare -rn env -i PATH="$PATH" bash phase-f/probe/<script>.sh`.
  Inside: only the `lo` interface (`/proc/net/dev`), a per-item temporary `HOME`
  (`phase-f/homes/<item>`), `OPENWIKI_CONFIG_DIR=$HOME/.openwiki`, `TMPDIR=$HOME/tmp`,
  `DO_NOT_TRACK=1`, `OPENWIKI_TELEMETRY_DISABLED=1`. The MCP driver passes the server only
  those variables plus `PATH`.
- Probe scripts: `phase-f/probe/` (`mcp.py`, `snap.py` run with `python3 -I`;
  `run_synth.sh`, `run_clone.sh`, `run_cli.sh`, `run_item6.sh`). Raw outputs: `phase-f/out/`.
- "Changes" below come from a full-tree fingerprint (sha256 per file, symlinks not followed,
  `.git/` included) taken before `pre`, after `pre`, after begin, and after `post`.
- No commit was made anywhere (no synthetic repository needed one). No host `openwiki_*`
  tool was called. The main repository was only read (`git status --porcelain` there is
  unchanged: the three caveman-compress files only).

### Item 1: handshake

| Field | Observed |
| --- | --- |
| `serverInfo` | `{"name": "openwiki", "version": "0.7.2"}` (protocolVersion `2024-11-05`) |
| `tools/list` (10) | `openwiki_begin`, `openwiki_submit_plan`, `openwiki_next_page`, `openwiki_inspect_page_claims`, `openwiki_submit_page`, `openwiki_finish`, `openwiki_list_workspaces`, `openwiki_list_wikis`, `openwiki_search`, `openwiki_read` |
| Required args | begin `[root, mode]`; submit_plan `[runId, pages]`; next_page `[runId]`; inspect_page_claims `[runId, jobId]`; submit_page `[runId, jobId]`; finish `[runId]`; list_workspaces `[root]`; list_wikis `[root, workspace]`; search `[root, query]`; read `[root, page, sections]` |

`openwiki_begin` full `inputSchema` (identical in all four runs):

```json
{
 "$schema": "http://json-schema.org/draft-07/schema#",
 "type": "object",
 "properties": {
  "root": {"type": "string", "minLength": 1},
  "mode": {"type": "string", "enum": ["init", "update"]},
  "language": {"type": "string", "minLength": 1, "description": "BCP-47 code, e.g. \"ko\" (not \"Korean\")."},
  "force": {"type": "boolean"}
 },
 "required": ["root", "mode"],
 "additionalProperties": false
}
```

Source cross-check: `dist/integrations/core/protocol.js` lines 1-16 (`BeginInput`) are
byte-identical between 0.5.2 and 0.7.2; `dist/ingestion/code-mode.js` lines 8-9 (the two
markers) are identical too.

### Items 2-4: guard `pre` -> `openwiki_begin` (`mode: "update"`) -> guard `post`

Guard: `shared/hooks/scripts/openwiki-guard.sh`, reached in each synthetic repository
through a `shared/hooks/scripts` symlink to the main repository's directory (as
`tests/test_hook_gates.py::_isolated_hook_scripts_dir` does). `pre` payload:
`{"tool_name":"mcp__openwiki__openwiki_begin","tool_input":{"root":"<realpath>","mode":"update"}}`;
`post` payload: `{"tool_name":"mcp__openwiki__openwiki_begin"}`. The clone used its own
tracked guard files, which `cmp` equal to the main working tree.

| | Item 2: both adapters | Item 3: no adapters | Item 4: local clone |
| --- | --- | --- | --- |
| Setup | `git init`; `AGENTS.md` = `# Guidance\n\nSome text` (no trailing newline); `CLAUDE.md` = `# Claude\n\nStuff\n`; `openwiki/INSTRUCTIONS.md`; `.claude/session_logs/`; symlinked guard | same, without `AGENTS.md` and `CLAUDE.md` | `git clone --local --no-hardlinks` of the main repo (branch `backlog-followups_implementation` @ `06eb8e0`); tracked 0.5.2-era `openwiki/` (`.last-update.json` `status: complete`, `gitHead bac1d59`) |
| `pre` | exit 0, no output; created `.claude/.cache/openwiki-guard/manifest.json` | exit 0, no output; same manifest | exit 0, no output; same manifest |
| Begin result | no `isError`; `status: active`, `phase: planning`; 0.037 s | no `isError`; `status: active`, `phase: planning`; 0.032 s | no `isError`; `status: active`, `phase: planning`; 1.142 s |
| Begin created | `openwiki/.last-update.json`, `openwiki/.run.json` | `AGENTS.md`, `openwiki/.last-update.json`, `openwiki/.run.json` | `openwiki/.run.json` |
| Begin changed | `AGENTS.md`, `CLAUDE.md` | none | `AGENTS.md`, `CLAUDE.md`, `openwiki/.last-update.json` |
| Begin removed / `.git/` / temp `HOME` | none / none / none | none / none / none | none / none / not snapshotted (no writes expected; see items 2-3, 5, 6) |
| Markers after begin | `AGENTS.md` 1 START + 1 END; `CLAUDE.md` 1 + 1 (`<!-- OPENWIKI:START -->` / `<!-- OPENWIKI:END -->`) | `AGENTS.md` 1 + 1; `CLAUDE.md` absent (not created) | both adapters `M` in `git status` |
| `post` exit | 0 | 0 | 0 |
| `post` stdout | `restored_from: snapshot; .github/workflows/openwiki-update.yml=unchanged; AGENTS.md=restored; CLAUDE.md=restored` | `restored_from: snapshot; .github/workflows/openwiki-update.yml=unchanged; AGENTS.md=removed; CLAUDE.md=unchanged` | `restored_from: snapshot; .github/workflows/openwiki-update.yml=unchanged; AGENTS.md=restored; CLAUDE.md=restored` |
| `post` stderr | empty | empty | empty |
| `cmp` vs copies taken before `pre` | `AGENTS.md` exit 0; `CLAUDE.md` exit 0 | both absent before `pre` and absent after `post` | adapters clean in `git status` after `post` |
| Net change before `pre` -> after `post` | `.claude/.cache/openwiki-guard/` (empty dir), `openwiki/.last-update.json`, `openwiki/.run.json` | same | `.claude/.cache/openwiki-guard/` (empty dir, ignored), `openwiki/.run.json` (ignored), `openwiki/.last-update.json` (changed) |

Item 4 detail (Phase G preview):

- Begin response: `changedPaths` 27 source paths since `bac1d59`; `pageUpdateWindows` 1
  window, base `bac1d59`, covering 10 pages; `claimIssues` 8 (all `kind: stale`, e.g. in
  `/openwiki/operations/git-backed-ai-state-sync.md`); `completedPages` 0; `lastUpdate`
  echoes the committed `.last-update.json`.
- Filesystem paths begin created or changed: 4 (1 created, 3 changed; listed above).
- `git status --porcelain` before `pre`: empty.
- After begin, before `post`: ` M AGENTS.md`, ` M CLAUDE.md`, ` M openwiki/.last-update.json`.
- After `post`: ` M openwiki/.last-update.json` only (`--ignored` adds `!! openwiki/.run.json`).
- The `.last-update.json` diff: `updatedAt` new, `status` `complete` -> `interrupted`;
  `gitHead` unchanged. The 0.5.2 source has the same `"interrupted"` write
  (`repository-run.js:160`), so this is not new in 0.7.2.

### Item 5: CLI exit codes (cwd: empty scratch directory)

| Command | Exit | Output |
| --- | --- | --- |
| `openwiki integrations list </dev/null` | 0 | 9 rows, all `not-installed`: bob, codex, claude, opencode, cursor, kiro, omp, antigravity, copilot |
| `openwiki --version </dev/null` | 1 | stderr `Unknown option: --version` |

Temp `HOME` and cwd unchanged by both.

### Item 6: integration installs in a second synthetic repository

Setup: `git init`; the main repository's `.mcp.json` and `.codex/config.toml` read with
the Read tool and written with the Write tool into the synthetic repository and into
`phase-f/copies/item6/` (`mcp.json.orig`, `codex-config.toml.orig`). Fidelity: both copies
`cmp` equal (exit 0) to the clone's tracked files (clone HEAD = main HEAD; main's working
tree shows neither file modified).

| Check | Result |
| --- | --- |
| `openwiki integrations install claude --project <root>` (no `--force`) | exit 0; created `.claude/skills/openwiki/{SKILL.md,.openwiki-install.json,agents/bob.yaml,agents/openai.yaml}`; changed nothing |
| `openwiki integrations install codex --project <root>` (no `--force`) | exit 0; created `.agents/skills/openwiki/{SKILL.md,.openwiki-install.json,agents/bob.yaml,agents/openai.yaml}`; changed nothing |
| `cmp` `.mcp.json` vs copy | exit 0 (unchanged) |
| `cmp` `.codex/config.toml` vs copy | exit 0 (unchanged) |
| Receipts | `version: 0.7.2`, single `target` (`claude` / `codex`); same four-file set as the main repo's installed 0.5.2 skills |
| `integrations list --project <root>` | exit 0; `claude installed`, `codex installed`, others `not-installed` |
| Temp `HOME` | unchanged |

### Stop rule (a)-(h)

| | Condition | Verdict | Evidence |
| --- | --- | --- | --- |
| a | Begin creates or changes a path outside `openwiki/**`, `AGENTS.md`, `CLAUDE.md` | PASS | Items 2-4: begin touched only `openwiki/.run.json`, `openwiki/.last-update.json`, `AGENTS.md`, `CLAUDE.md`; nothing in `.git/`; temp `HOME` unchanged (items 2-3). `.claude/.cache/openwiki-guard/` comes from `pre`, not begin. |
| b | `post` exits nonzero or an adapter differs from its copy | PASS | `post` exit 0 in all three; item 2 `cmp` exit 0 for both; item 3 created `AGENTS.md` removed; item 4 adapters clean in `git status`. |
| c | Markers differ | PASS | `<!-- OPENWIKI:START -->` / `<!-- OPENWIKI:END -->`, exactly one pair per adapter; `code-mode.js:8-9` identical to 0.5.2. |
| d | `openwiki_begin` renamed, loses `root`/`mode`, or `mode` gains a value | PASS | Name unchanged; `required: [root, mode]`; `mode.enum: [init, update]`; `additionalProperties: false`; `BeginInput` source identical to 0.5.2. |
| e | `tools/list` has a tool beyond the six lifecycle and four read-only tools | PASS | Exactly 10 tools, listed in item 1. |
| f | Begin fails without network or errors on the clone's wiki state | PASS | All runs under `unshare -rn` (only `lo`); no `isError`; `active`/`planning` in all three, including the clone with 0.5.2-era state. |
| g | `integrations list` exits nonzero | PASS | Exit 0. |
| h | Item 6 changes either copied file | PASS | `cmp` exit 0 for `.mcp.json` and `.codex/config.toml`. |

**Overall: GO.**

### Notes for later steps

- `openwiki_begin` (`update`) rewrites the tracked `openwiki/.last-update.json` to
  `status: interrupted` before any page work. The guard does not cover this path. A Phase G
  refresh that stops after begin leaves that tracked diff. The behavior is the same in 0.5.2.
- The 0.7.2 `AGENTS.md` managed block now tells agents to use `openwiki_search`,
  `openwiki_read`, `openwiki_list_workspaces`, and `openwiki_list_wikis`. The guard
  restores the adapters, so this text never lands in this repository.
- In 0.7.2, `openwiki_begin` creates a missing `AGENTS.md` but not a missing `CLAUDE.md`
  (item 3), as the plan expected.
- The guard leaves an empty `.claude/.cache/openwiki-guard/` directory after `post`.
  This is existing guard behavior and is ignored by git.
- `integrations list` reports 9 hosts. New since 0.5.2 per the plan: `omp`,
  `antigravity`, `copilot`.
- The install receipts and the skill file set match the main repository's installed 0.5.2
  skills (`SKILL.md`, `agents/bob.yaml`, `agents/openai.yaml`, `.openwiki-install.json`).
  Only the content hashes differ. Not observed here: an install on top of an existing 0.5.2
  install, which is step 4's real case. Item 6 was a first install.

## [LEARN] Entries

- [LEARN:tooling] After a user runs a global npm upgrade for a pinned tool,
  check the binary the repository actually uses before trusting it:
  `readlink -f "$(command -v <tool>)"` and that package's own
  `package.json` version, plus every install receipt. On 2026-10-21 a
  user-run `npm install -g openwiki@0.7.2` left this WSL global package at
  `0.5.2`, while one integration install ran on `0.7.2` and the other on
  `0.5.2`, leaving mixed receipts.

## Verification

```text
# verify closeout --format text summary lines
```

- optional 1: NOT RUN — Claude Code `/mcp` and a read-only `openwiki_search`
  call need a session started on `0.7.2`; this session's server started on
  `0.5.2`. Phase G starts after a reconnect and exercises the server.
- optional 2: NOT RUN — no Codex session available here.
- optional 3: NOT RUN — the Codex guard re-probe needs a Codex session.
- optional 4: PASS — `unshare -rn uv run --offline pytest
  tests/test_openwiki_cli_smoke.py -q`: 2 passed on `0.7.2`.
- optional 5: NOT RUN — the devcontainer image was not rebuilt here; the
  validator checks the Dockerfile pin text.

## Open Questions / Next Steps

- Step 4 needs the user: `npm install -g openwiki@0.7.2`, then
  `openwiki integrations install claude --project <root>` and
  `openwiki integrations install codex --project <root>` (never `--force`).
