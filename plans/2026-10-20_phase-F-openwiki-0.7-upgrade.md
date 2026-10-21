---
name: 2026-10-20_phase-F-openwiki-0.7-upgrade
type: small-plan
parent_plan: backlog-followups
phase_index: 6
status: complete
closeout_session_log: .claude/session_logs/2026-10-21_backlog-followups-phase-f.md
---

# Small Plan: OpenWiki 0.7 Upgrade

## Scope

Move the pinned OpenWiki command-line tool from `0.5.2` to `0.7.2` (npm
`latest`, published 2026-10-09) without weakening the hook guard around
`openwiki_begin`. OpenWiki runs as an MCP (Model Context Protocol) server
that the coding agent calls. `openwiki_begin` is its only call that writes
outside `openwiki/`: it adds a managed block to root `AGENTS.md` and
`CLAUDE.md`, which `openwiki-guard` snapshots before the call and restores
after it. This phase observes `0.7.2` in isolation, restates the upgrade
rule (the old one, in a dated plan, names a retired runner), adds
real-binary tests, bumps the pin, and upgrades this checkout's local tool
so Phase G can refresh the wiki with it. Requirements: BF-F1 to BF-F7.

Planning evidence (2026-10-20: file diff of `npm pack openwiki@0.5.2`
against `@0.7.2`, release notes `v0.6.0` to `v0.7.2`, a live `0.5.2` run):

- Unchanged in `0.7.2`: the six lifecycle tool names; `openwiki_begin`'s
  input (`root`, `mode` = `init` or `update`, `language`, `force`;
  `integrations/core/protocol.js:7-14`); server name `openwiki`, so the
  hook matcher `mcp__openwiki__openwiki_begin` still applies; the markers
  `<!-- OPENWIKI:START -->` and `<!-- OPENWIKI:END -->`
  (`ingestion/code-mode.js:8-9`); the workflow file is written only for
  `init` (`generation/repository-run.js:106`); state files and their
  schema version 1; the telemetry opt-outs; Node `>=22.22.0`; peer ranges
  that accept the image's `mermaid@11.16.0` and `jsdom@29.1.1`; no
  `openwiki --version`.
- New: four read-only tools (`openwiki_list_workspaces`,
  `openwiki_list_wikis`, `openwiki_search`, `openwiki_read`) that start no
  run and write nothing in the repository; workspace links live in
  `~/.openwiki/wiki-workspaces.json`, written only by the `openwiki link`
  and `openwiki workspace` commands. New host integrations: `antigravity`
  (writes the bootstrap-owned `.agents/mcp_config.json`), `copilot` (GitHub
  Copilot CLI: `.github/mcp.json`, `.github/skills/openwiki`), and `omp`.
  The `.openwiki-install.json` receipt may list several owners; the
  bootstrap reads only its presence.
- Changed: `openwiki_begin` no longer creates a missing `CLAUDE.md` (it
  still creates a missing `AGENTS.md`) and replaces an exact pre-marker
  `## OpenWiki` template section with the managed block. The snapshot
  restore covers both; neither root adapter here has such a section.
- Live `0.5.2` run in a scratch repository under `unshare -rn` (no network)
  with a temporary `HOME`: guard `pre`, `openwiki_begin` (`update`, 0.03 s),
  guard `post` restored both adapters byte for byte. Begin wrote only
  `openwiki/.run.json`, `openwiki/.last-update.json`, and the two blocks.
- `verify.py phase` runs all of `tests/`, including
  `tests/test_openwiki_cli_smoke.py`, which requires the binary on `PATH`
  to report exactly `OPENWIKI_PINNED_VERSION`. After the bump this machine
  must run `0.7.2`, or every later phase fails verification. The test
  fails; it never downloads.

Out of scope: OpenWiki for GitHub Copilot or Antigravity, wiki linking,
refreshing this wiki (Phase G), and dated records (the 2026-09-19 OpenWiki
plan and spike narrative, session logs).

## Steps

- [x] **1. Observe `0.7.2` in isolation (evidence only, BF-F1).**
  **Owner:** orchestrator.
  **Files:** none in the repository; a capture table in the session log.
  **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`,
  `shared/skills/ponytail/SKILL.md` (full).
  Work only in the session scratch directory and treat the package as
  untrusted: `npm install --prefix "$SCRATCH/openwiki-0.7.2" openwiki@0.7.2`.
  This install needs the network and runs the install scripts of
  OpenWiki's dependencies (`0.7.2` adds `@azure/identity`); only the probes
  below run without network. Keep the probe script in a separate scratch directory and run it with
  `python3 -I`. Run every probe under `unshare -rn` (supported here,
  checked 2026-10-20) with a temporary `HOME`, `OPENWIKI_CONFIG_DIR` inside
  it, `DO_NOT_TRACK=1`, and `OPENWIKI_TELEMETRY_DISABLED=1`. Never call the
  host's own `openwiki_*` tools and never point a probe at this
  repository's root. Record:
  1. `serverInfo.version`, the `tools/list` names, and
     `openwiki_begin`'s full `inputSchema`.
  2. In a synthetic repository (`git init`; `AGENTS.md` without a trailing
     newline; `CLAUDE.md` with one; `openwiki/INSTRUCTIONS.md`; the guard
     reached through a `shared/hooks/scripts` symlink to this repository's
     `shared/hooks/scripts`, as `tests/test_hook_gates.py` does): guard
     `pre`, `openwiki_begin` (`mode: "update"`), guard `post`. Record each
     created or changed path, the response `status` and `phase`, `post`'s
     output and exit code, and a `cmp` of both adapters against copies
     taken before `pre`.
  3. The same in a synthetic repository with neither adapter. Expected:
     only `AGENTS.md` is created, and `post` removes it.
  4. `openwiki_begin` (`mode: "update"`) in a scratch `git clone --local`
     of this repository, which carries the `0.5.2`-era `openwiki/` state:
     response status and phase, changed-path count, and
     `git status --porcelain` in the clone (a preview of Phase G).
  5. Exit codes of `openwiki integrations list </dev/null` and
     `openwiki --version`.
  6. In a second synthetic repository, copy this repository's tracked
     `.mcp.json` and `.codex/config.toml` (read them with a read tool and
     write the copies with the Write tool; the guard denies shell commands
     that name them), run `openwiki integrations install claude --project
     <synthetic root>` and `openwiki integrations install codex --project
     <synthetic root>` with the temporary `HOME` and without `--force`, and
     `cmp` both files against the copies.
  **Stop rule:** stop before step 2 when (a) begin creates or changes a
  path outside `openwiki/**`, `AGENTS.md`, and `CLAUDE.md`; (b) `post`
  exits nonzero or an adapter differs from its copy; (c) the markers
  differ; (d) `openwiki_begin` is renamed, loses `root` or `mode`, or
  `mode` gains a value; (e) `tools/list` has a tool beyond the six
  lifecycle and four read-only tools; (f) begin fails without network or
  errors on the clone's wiki state; (g) `integrations list` exits
  nonzero; or (h) item 6 changes either copied file. On a stop, keep
  `0.5.2`, change nothing, and give the user the capture with three
  choices: finish this phase at `0.5.2` with step 3 and only the step 2
  text that does not name `0.7.2` (the strict `mode` check and the
  real-binary round trip work at `0.5.2`); cancel this phase with the
  capture as cancellation evidence (step 7); or re-plan the guard. Phase G
  then refreshes with `0.5.2`. Paths only a refresh would rewrite (claims line references,
  provenance, index pages) are a preview, not a stop.
  **Limits:** one version, synthetic repositories, one clone, no host session.

- [x] **2. Restate the upgrade rule and the tool surface before the pin changes (BF-F2, BF-F6).**
  **Owner:** documenter.
  **Files:** modify `docs/runtime-checks.md`,
  `shared/skills/knowledge-refresh/SKILL.md`,
  `shared/policies/tool-routing.instructions.md`,
  `shared/policies/workflow.instructions.md`.
  **Required Skills:** `shared/skills/documentation/SKILL.md`,
  `shared/skills/humanize/SKILL.md`,
  `shared/skills/knowledge-refresh/SKILL.md`.
  1. `docs/runtime-checks.md`: add an `openwiki` entry to "Optional
     helpers" (the pin; the Dockerfile reads the package's own
     `package.json` because `--version` does not exist; the smoke test
     fails rather than downloads). Under it, add a numbered upgrade
     procedure like the Context Mode one in the same list: diff the old
     and new `npm pack` contents and release notes for the facts step 1
     records; observe the candidate in isolation with the guard round
     trip; change both Dockerfile lines, `OPENWIKI_PINNED_VERSION`, and
     `EXPECTED_TOOLS`; install the version locally and run the smoke and
     guard tests; re-run both integration installs (never `--force`) and
     confirm `.mcp.json` and `.codex/config.toml` are unchanged; start a
     new host session before the next refresh. Add the stop rule in one
     sentence: keep the old pin when begin writes outside `openwiki/**`
     and the two adapters or the round trip fails. Fix the stale
     "Devcontainer And Git-Backed State Sync" line listing what the
     Dockerfile installs (it omits `openwiki`, `mermaid`, `jsdom`).
  2. `knowledge-refresh` skill: after the pinned version changes, a person
     re-runs the two install commands once, never `--force`, to upgrade
     the installed `openwiki` skill; a diff in `.mcp.json` or
     `.codex/config.toml` is a stop to report. Change "exactly once per
     checkout" to once when enabling and once per pin change. Never install
     OpenWiki's other host integrations here, including `copilot` (Copilot
     CLI is unsupported) and `antigravity` (it writes the bootstrap-owned
     `.agents/mcp_config.json`). The guard covers only `openwiki_begin`;
     the read-only tools write nothing to restore.
  3. `tool-routing.instructions.md`: one Routing Contract bullet. Where
     OpenWiki is enabled and its Claude Code or Codex integration is
     installed, the session also has OpenWiki's read-only `openwiki_search`
     and `openwiki_read` (and the workspace-listing tools): just-in-time
     descriptive context only, never at task start; results, including
     linked wikis of other repositories, are derived context under the
     Knowledge Ownership contract; verify consequential details against
     source.
  4. `workflow.instructions.md`, "OpenWiki Refresh": the guard denies every
     mode other than `update`, `init` included (true after step 3).
  Describe what steps 3 and 5 build without quoting output strings that do
  not exist yet. Add no OpenWiki text under `shared/sidecar/`:
  `validate_targets.py` forbids the `openwiki` token in sidecar output.

- [x] **3. Real-binary round trip and a strict mode check, written at `0.5.2` (BF-F4, BF-F5).**
  **Owner:** coder.
  **Files:** modify `tests/test_openwiki_cli_smoke.py`,
  `shared/hooks/scripts/openwiki-guard.py`, `tests/test_openwiki_guard.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`,
  `shared/skills/integration-gate-spike/SKILL.md`.
  1. Handshake test: also assert `openwiki_begin`'s `inputSchema.required`
     contains `root` and `mode` and `properties.mode.enum` equals
     `["init", "update"]`, the fields the guard reads. `EXPECTED_TOOLS`
     stays at six in this step.
  2. Add `test_real_openwiki_begin_update_is_restored_by_the_guard`. Build
     the repository with `_guard_repo` in a subdirectory of `tmp_path`, run
     `git init` there, and reuse `_run_guard` (import both the way
     `tests/test_openwiki_guard.py` imports from `tests/test_hook_gates.py`)
     and this file's `_openwiki_binary`, `_send`, `_read_json_line`. Start
     `openwiki mcp --host claude` with a `HOME` outside the repository,
     `OPENWIKI_CONFIG_DIR` inside that `HOME`, `DO_NOT_TRACK=1`,
     `OPENWIKI_TELEMETRY_DISABLED=1`, and the current `PATH`. Record the
     bytes of every file outside `.git/` and the `shared/` harness symlink.
     Run guard `pre` (`mode: "update"`, the repository root; no deny), call
     `openwiki_begin` with the same input, and assert: no error result;
     `openwiki/.run.json` exists; each adapter has exactly one managed
     block; `.github/workflows/openwiki-update.yml` does not exist; no file
     outside `openwiki/`, `AGENTS.md`, `CLAUDE.md`, and
     `.claude/.cache/openwiki-guard/` was created, changed, or removed. Run
     guard `post`; assert exit 0 and that every recorded file outside
     `openwiki/` and `.claude/.cache/` matches its recorded bytes. No skip:
     a missing binary fails through `_openwiki_binary`; nothing downloads.
  3. `openwiki-guard.py` `_cmd_pre`: deny when `mode` is anything but the
     string `"update"`, a missing `mode` included; the reason names the
     received value and that only `update` is allowed. Make the module
     docstring's first paragraph version-free and line-number-free (cite
     `beginRepositoryRun` in `generation/repository-run.js` calling
     `ensureCodeModeRepoSetup` in `ingestion/code-mode.js`), and add one
     residual limit: the no-snapshot strip fallback cannot restore a
     replaced pre-marker `## OpenWiki` section; the snapshot restore can.
  4. `tests/test_openwiki_guard.py`: a parametrized deny test for
     `mode="rebuild"` and for a payload without `mode`, each asserting the
     deny and that no snapshot manifest was written. Keep the `init` test.
  Run `uv run pytest tests/test_openwiki_cli_smoke.py tests/test_openwiki_guard.py -q`
  against the installed `0.5.2`; it passes before step 4 starts.

- [x] **4. Upgrade this checkout's environment (BF-F7).**
  **Owner:** user. The orchestrator asks the user to run these commands,
  runs `npm install -g` itself only after the user explicitly approves it,
  and records every output in the session log.
  **Files:** none tracked in the outer repository. The installed OpenWiki
  skills change: `.claude/skills/openwiki/` (nested `ai-state` repository)
  and `.agents/skills/openwiki/` (ignored).
  **Required Skills:** `shared/skills/knowledge-refresh/SKILL.md`,
  `shared/skills/integration-gate-spike/SKILL.md`.
  1. Record `command -v openwiki` and the installed version; run
     `npm install -g openwiki@0.7.2`; record both again.
  2. Run `openwiki integrations install claude --project <root>` and
     `openwiki integrations install codex --project <root>`, never
     `--force`. Record `openwiki integrations list --project <root>`,
     `git status --porcelain -- .mcp.json .codex/config.toml` (empty), and
     the `version` in both `.openwiki-install.json` receipts (`0.7.2`).
  3. Run `uv run pytest tests/test_openwiki_cli_smoke.py -q`. Expected: the
     handshake test fails at its version assertion; the round trip passes
     on `0.7.2`.
  A diff in `.mcp.json` or `.codex/config.toml`, or a round-trip failure,
  is a stop: report it, hand-edit nothing, and roll back with
  `npm install -g openwiki@0.5.2` and the two install commands. Then offer
  the same three choices as the step 1 stop rule; steps 2 and 3 already
  written stay when they pass at `0.5.2`, and step 2 text that names
  `0.7.2` is reverted. Note for the user: after a successful global
  install, any other checkout or branch of this repository that still pins
  `0.5.2` fails its OpenWiki smoke test until it is updated or the global
  install is rolled back. The running
  session's OpenWiki server is now stale: call no host `openwiki_*` tool
  until a new session or `/mcp` reconnect.

- [x] **5. Bump the pin (BF-F3, BF-F4).**
  **Owner:** coder.
  **Files:** modify `shared/devcontainer/Dockerfile` (the `openwiki@`
  install line and the `package.json` version test),
  `scripts/validate_targets.py` (`OPENWIKI_PINNED_VERSION = "0.7.2"` and a
  one-line comment pointing to the procedure in `docs/runtime-checks.md`),
  `tests/test_openwiki_cli_smoke.py` (`EXPECTED_TOOLS` = the ten tools
  step 1 observed).
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/integration-gate-spike/SKILL.md`.
  Change nothing else: not the `verify.py` backstop, the hook matcher in
  `scripts/generate_targets.py`, `.mcp.json`, `.codex/config.toml`, or the
  `mermaid` and `jsdom` pins. The smoke and guard tests pass.

- [x] **6. Regenerate, refresh the installed runtime, review, close out.**
  **Owner:** orchestrator; fresh reviewer.
  Run `uv run python scripts/generate_targets.py --all` and
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  before verification; `git status --porcelain -- AGENTS.md CLAUDE.md`
  stays empty. The closeout log maps BF-F1 to BF-F7 to the capture table
  and tests, and hands off to Phase G: start it in a new host session (or
  reconnect with `/mcp`) so the OpenWiki server runs `0.7.2`; a
  `CONNECT_TIMEOUT` right after WSL boot is timing; expect first-refresh
  churn in claims line references, provenance (`by: openwiki/0.7.2`), and
  index pages.

- [x] **7. Stop path only: cancel this phase.** Not run: no stop condition
  fired.
  **Owner:** orchestrator.
  **Files:** a new evidence file
  `.claude/explorations/2026-10-20_openwiki-0.7-spike/evidence.md`, this
  small plan, the big plan `backlog-followups.md`, and the Phase G small
  plan.
  Use this step only when the user chooses cancellation at a step 1 or
  step 4 stop. Write the capture table into the evidence file with
  `**Status:** CANCELLED` near the top and the reason. Confirm the local
  binary is `0.5.2` again. Set this plan to `status: cancelled` with
  `cancelled_at` (exact UTC), a single-line `cancelled_reason`, and
  `cancelled_evidence` pointing at the evidence file. Revert any step 2 or
  step 3 edit that is not committed. Set the big plan's `current_phase` to
  `2026-10-20_phase-G-backlog-followups-knowledge-refresh` and that phase to
  `status: in-progress`; tick this phase's entry in the big plan's
  `## Phases` list and annotate it "cancelled, see <evidence path>". Run
  `uv run python scripts/validate_plan_frontmatter.py`, then checkpoint the
  nested `.claude` repository. No outer commit, findings report, or
  closeout log.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/test_openwiki_cli_smoke.py -q    # real pinned binary: handshake, begin schema, guard round trip
uv run pytest tests/test_openwiki_guard.py tests/test_lifecycle_hooks.py -q
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Claude Code: in a new session, confirm `/mcp` shows `openwiki`
  connected, call `openwiki_search` once with this repository's root and a
  short query, and record the result count. Read-only; starts no refresh.
- Codex: the same read-only `openwiki_search` call in a new session.
- Codex guard re-probe (item 7 of
  `.claude/explorations/2026-09-21_openwiki-followups-and-instruction-alignment.md`,
  handed over by Phase A): in a Codex session in this checkout, call
  `openwiki_begin` with `mode: "init"` and record the PreToolUse deny; then
  call it with `mode: "update"` while the wiki is current, record `noop`,
  and record that `git status --porcelain -- AGENTS.md CLAUDE.md` is empty
  after the turn ends.
- No-network rerun: `unshare -rn uv run pytest tests/test_openwiki_cli_smoke.py -q`.
- Devcontainer: rebuild the image from the regenerated `.devcontainer/`;
  record that the pinned-version and `integrations list` checks pass.

## Review Profiles

Use `.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Give the reviewer the step 1
capture table and stop-rule outcome, the step 4 environment record,
BF-F1 to BF-F7, and the final diff.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
