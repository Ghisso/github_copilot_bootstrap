---
name: 2026-11-12_phase-B-context-mode-2x-switch
type: small-plan
parent_plan: context-mode-2x-migration
phase_index: 2
status: complete
closeout_session_log: .claude/session_logs/2026-11-12_context-mode-2x-migration-phase-B.md
---

# Small Plan: Switch to Context Mode 2.x and Node.js 24

## Scope

Move the kit from Context Mode 1.0.169 to `2.1.8`, and the devcontainer's Node.js image to `node:24.22.3-bookworm-slim`. Both values come from the pre-branch spike report (`.claude/explorations/2026-11-12_context-mode-2x-recheck/REPORT.md`; big plan, decisions 5, 6, and 7). 2.1.8 was npm's `latest` at spike time. A later release is a later pin bump through the procedure in Step 7.

What changes:

- **Dispatcher:**
  - the pin;
  - the server starts as `context-mode server --agent codex`, from the outer repository root, with no `CLAUDE_PROJECT_DIR` and no `--workspace-folder` (spike S2);
  - `CONTEXT_MODE_DATA_DIR` is exported to the guarded root;
  - a Node.js 24.15.0 floor in server mode and `--self-check` only;
  - a quarantine move that loses a race with another dispatcher no longer fails.
- **Devcontainer:** the Node.js image, the pin, and a `--version` check.
- **Docs:** 2.x behavior, storage, a new pin-bump procedure, and a rollback note.

The MCP adapters and the filter do not change. Phase A already made `ctx_index` files-only (spike S3). Covers REQ-001, REQ-005, and REQ-006.

## Steps

- [x] **1. Prepare the private binary.**
  - Owner: orchestrator.
  - Run `npm install -g --prefix "$HOME/.cache/context-mode-pin" --ignore-scripts "context-mode@2.1.8"`. 2.x has no install scripts; the flag keeps that true, and the prefix leaves the global install and every other repository untouched.

- [x] **2. Write the tests first.**
  - Owner: `coder`. Files (modify): `tests/test_context_mode_dispatch.py`, `tests/test_context_mode_mcp_filter.py`, `tests/test_validate_targets.py`.
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - Dispatcher tests:
    - **Fakes:** they default to the pin read from the dispatcher source. Wrong versions are `0.0.0` and `2.0.0-next.1`.
    - **Server arguments:** `server --agent codex` through the filter, both direct and through `npx -y context-mode@<pin>`, with no `--workspace-folder` argument.
    - **Working folder:** start the dispatcher from a subfolder, for example a nested Git repository at `<repo>/.claude`. The fake `node` records `$PWD`, and it equals the repository root. With no `CLAUDE_PROJECT_DIR` in the caller's environment, the launched environment has none either.
    - **Data root:** `CONTEXT_MODE_DATA_DIR` equals the chosen storage root, and an inherited value that points elsewhere is overwritten. Extend `_fake_node` to record it and `$PWD`, and to answer `--version` with `v24.15.0` unless a test sets another version.
    - **Node.js floor**, server mode and `--self-check` only:
      - a fake `node` that reports `v22.22.0` or `v24.14.9` makes server mode exit 1 with one error line naming 24.15.0, and makes `--self-check` report `required-node=24.15.0` with a warning;
      - `v24.15.0` and `v25.0.0` pass;
      - legacy hook calls run no Node.js check.
    - **Old pin, correct secret:** a cache whose marker holds the correct secret and `context-mode=0.0.0`, plus a sentinel file, is moved aside on the first server start. Afterwards the sentinel is under `context-mode.untrusted.*`, the new marker names the pin, and `CONTEXT_MODE_DATA_DIR` equals the fresh root.
    - **Lost race:** a fake `mv` first on `PATH` removes the source folder and exits 1, as when another server moved it first. The server still launches with a fresh root and one warning line.
  - Validator test: the pin assertion near line 2602 reads the dispatcher pin instead of a literal.
  - State-sync test: no change. Since Phase A, `test_hostile_remote_cache_with_forged_marker_is_quarantined_not_trusted` runs `server` mode with a fake `node` above the floor and reads the pin and `FILTER_CONTRACT` from the dispatcher source, so it follows the new pin. The Verification block still runs it.
  - Real server test: extend `test_real_upstream_server_surface_is_filtered`:
    - run `git init` in the scratch repository (every spike probe ran in a Git repository, and 2.x keys its project by the Git folder);
    - no `.context-mode` folder appears under the scratch `HOME`, and a `projects/` folder appears under the data root;
    - add a regular file with a unique word to the scratch repository; `ctx_index` with its relative `path` succeeds, and a `ctx_search` finds the word, which shows that the filter and the server resolve the path from the same folder;
    - `ctx_index` with a folder `path` gets `-32602`.
  - Negative control before Step 3: run the new tests on today's code, and record in the session log which ones fail and why.

- [x] **3. Dispatcher.**
  - Owner: `coder`. File: `shared/hooks/scripts/context-mode-dispatch.sh` (modify).
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/integration-gate-spike/SKILL.md`.
  - Set `PINNED_CONTEXT_MODE_VERSION="2.1.8"`, and add `MIN_NODE_VERSION="24.15.0"`.
  - Server mode:
    - one `node --version` call, compared in Bash (major above 24, or major 24 with a minor of 15 or more);
    - if Node.js is too old: one error line and exit 1;
    - otherwise launch `context-mode server --agent codex` (or `npx -y "context-mode@$PINNED_CONTEXT_MODE_VERSION" server --agent codex`) through the filter.
  - Working folder. Spike S2: `--agent codex` keys the project to the working folder, and started in `<repo>/.claude` it used the nested repository as a separate project.
    - `server` and `--self-check` run `cd "$REPO_ROOT"` before they resolve the launcher. `REPO_ROOT` is the value the dispatcher already computes from its own location (`$SCRIPT_DIR/../../..`, resolved with `pwd -P`), so it is the outer repository root from any starting folder, `.claude` included.
    - The `cd` comes before the launcher lookup, so the version proof, the self-check report, and the filter's later start of `context-mode` all search `PATH` from the same folder.
    - The filter and the server then run in that folder too, so the server resolves a relative `ctx_index` path from the same folder the filter checks it against (`CONTEXT_MODE_PROJECT_ROOT`).
    - In server mode, a failed `cd` prints one error line and exits 1. In `--self-check`, it prints a warning. Legacy hook calls do not `cd`.
    - Set no `CLAUDE_PROJECT_DIR` and pass no `--workspace-folder`. An inherited `CLAUDE_PROJECT_DIR` is left alone: under `--agent codex` the server keys the project by its working folder and ignores it (spike S2, case X2).
  - `--self-check` prints `required-node` and `observed-node`, and warns when Node.js is too old.
  - `configure_storage`:
    - exports `CONTEXT_MODE_DATA_DIR="$CONTEXT_MODE_DIR"`, overwriting any inherited value;
    - keeps exporting `CONTEXT_MODE_DIR`, and `CONTEXT_MODE_PROJECT_ROOT`, which the filter reads;
    - when the quarantine move fails and the cache folder no longer exists, treats it as a lost race with another dispatcher and continues; when the folder still exists, keeps today's failure path.
  - `FILTER_CONTRACT` keeps the value Phase A set. The pin change alone moves older caches aside.
  - Rewrite the comments that describe 1.0.169 (no `--version`, a slow `doctor`). The manifest check stays because it needs no Node.js start. Update the network comment near lines 22-28.
  - Must not change: storage selection, the override rule, the provenance secret, quarantine without deletion, the legacy hook no-op, or `FILTER_CONTRACT`.

- [x] **4. Filter: no change.**
  - Owner: `coder` (check only). File: `shared/hooks/scripts/context-mode-mcp-filter.mjs` (unchanged). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Spike S3 required the files-only `ctx_index` fallback, and Phase A made it: `validateIndex` accepts `content` or one regular file inside the repository, `FILTER_CONTRACT` has its new value, and the kit description says so. Do not change them here.
  - The 2.1.8 `ctx_index` schema has `path`, `content`, `url`, and `source` (spike S2). `INDEX_ARGS` keeps stripping `url`. The real server test from Step 2 covers the filtered surface on 2.1.8; a different `tools/list` there stops the phase for a re-plan.

- [x] **5. Devcontainer and validator.**
  - Owner: `coder`. Files (modify): `shared/devcontainer/Dockerfile`, `scripts/validate_targets.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Dockerfile:
    - `FROM node:24.22.3-bookworm-slim AS nodejs`;
    - `npm install -g context-mode@2.1.8`;
    - replace `context-mode --help >/dev/null` with `test "$(context-mode --version)" = "2.1.8"`.
  - Validator:
    - `CONTEXT_MODE_PINNED_VERSION = "2.1.8"`.
    - `OPENWIKI_NODE_IMAGE = "node:24.22.3-bookworm-slim"`, with its message saying that the image must meet both OpenWiki's and Context Mode's engine requirements.
    - The Dockerfile checks require the `--version` test instead of `--help`.
    - `CONTEXT_MODE_BLOCKED_TOOLS` adds `ctx_batch` and `ctx_resume`.

- [x] **6. Regenerate and refresh the self-install.**
  - Owner: orchestrator. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`. Never hand-copy.
  - Reconnect the Context Mode MCP server in the running client.
  - After the self-install, this repository's own sessions use the pin through the dispatcher. On this host the global `context-mode` is still 1.0.169, so the dispatcher refuses it and uses `npx` with the pin (a one-time download into the npm cache). Updating the global install is the user's choice.

- [x] **7. Documentation.**
  - Owner: `documenter`. Required Skills: `.claude/skills/documentation/SKILL.md`.
  - `docs/runtime-checks.md`, Context Mode bullet:
    - the pin and the Node.js 24.15.0 floor;
    - how the version is proved (the manifest, or the `npx` pin; the server itself reports `"dev"`);
    - the single server identity: `--agent codex`, started from the repository root, with no `CLAUDE_PROJECT_DIR`;
    - `CONTEXT_MODE_DATA_DIR`, and that everything 2.x writes is under it;
    - older caches are moved aside and never migrated; exact-version provenance resets the cache on every bump;
    - the lost-race behavior.
  - Rewrite the pin-bump procedure:
    1. install the candidate into `$HOME/.cache/context-mode-pin` with `--ignore-scripts`;
    2. run the `CONTEXT_MODE_REAL=1` server test with that prefix first on `PATH`;
    3. compare `tools/list` (schemas, property descriptions) with the kit descriptions and `INDEX_ARGS`;
    4. run the two slim-image checks;
    5. optionally build the full devcontainer;
    6. bump the pin in the dispatcher, the Dockerfile, and the validator together.
  - Known limits:
    - tool-result text can name another client's tool prefix, because one identity serves all clients and the filter does not rewrite results;
    - upstream 2.x folder indexing has no limit, follows symlinks inside the repository's parent folder, and ignores a `.gitignore` above the folder (spike S3), which is why the filter accepts only content or one regular file;
    - the user-level plugin note stays.
  - Rollback note, three lines: reverting the merge brings back the previous pin; its dispatcher moves the 2.x cache aside on the first run; it does not restore the older cache by itself, so a user who wants the old index back moves the newest untrusted folder back by hand before that first run.
  - `README.md`:
    - the devcontainer runs Node.js 24 (near line 1428);
    - install commands (near lines 1436-1456) with the pin, `context-mode --version`, and the Node.js floor;
    - the version-pinning and storage paragraphs (near lines 1430-1432);
    - the rollback note.
  - `shared/policies/tool-routing.instructions.md`: the pin; the data root variable; and the filtered-tool list with the 2.x names (`ctx_execute`, `ctx_batch`, `ctx_resume`, `ctx_upgrade`, `ctx_purge`, `ctx_doctor`). The files-only `ctx_index` sentence from Phase A stays.
  - `docs/smoke-tests.md` (near lines 283-285): the self-check lines.
  - Write "the 1.x cache" or "the previous pin" instead of the old version number; a required item checks for it.
  - Orchestrator: update the pinned-versions paragraph in `.claude/instructions/project-context.instructions.md` (AI state).
  - LEARN candidates:
    - `[LEARN:tooling] Context Mode 2.x reports serverInfo.version "dev"; prove its version from the package manifest or the npx pin, never over the wire.`
    - `[LEARN:tooling] Context Mode 2.x ignores CONTEXT_MODE_DIR; CONTEXT_MODE_DATA_DIR sets its data root, and 1.x data is not imported.`
    - `[LEARN:tooling] Context Mode 2.x with --agent codex keys its project to the working folder's Git repository; start it from the outer repository root, or a nested .claude repository becomes a separate project.`
    - `[LEARN:workflow] Check a hook-lane claim against the generated matcher, not only a replayed fixture: the Codex SessionStart matcher startup|resume|clear never delivered compact.`

- [x] **8. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `config`, `documentation`.
  - Focus:
    - the dispatcher refuses every version except the pin, and Node.js below 24.15.0 in server mode;
    - the dispatcher runs `cd "$REPO_ROOT"` before it resolves the launcher, and sets no `CLAUDE_PROJECT_DIR`;
    - no inherited `CONTEXT_MODE_DATA_DIR` can move data;
    - the lost-race path never treats an existing, unaudited folder as trusted;
    - the quarantine still never deletes;
    - no live surface names the old pin.

## Risks and Fallbacks

- This repository's sessions download the pin through `npx` on first use (Step 6). It is a one-time cost.
- A later 2.x release changes `tools/list`. The pin-bump procedure's step 3 catches it.
- Quarantined caches use disk space in every consumer. The docs say so, and the user deletes them by hand.
- The tool-name text inside tool results can name another client's tool prefix, because one server identity serves every client and the filter does not rewrite results. This is cosmetic; the kit's routing policy names the real tools.
- Without the `cd`, a server started inside `.claude` would use a separate project for the nested repository (spike S2). The working-folder test in Step 2 guards it.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_context_mode_dispatch.py tests/test_context_mode_mcp_filter.py tests/test_validate_targets.py -q --tb=short
uv run pytest tests/test_state_sync.py -q --tb=short -k cache
# Needs the private prefix that Step 1 creates ($HOME/.cache/context-mode-pin).
test "$("$HOME/.cache/context-mode-pin/bin/context-mode" --version)" = "$(sed -n 's/^PINNED_CONTEXT_MODE_VERSION="\(.*\)"$/\1/p' shared/hooks/scripts/context-mode-dispatch.sh)"
# Needs the private prefix that Step 1 creates; the real 2.x server makes no network call for these requests (REPORT.md §9).
PATH="$HOME/.cache/context-mode-pin/bin:$PATH" CONTEXT_MODE_REAL=1 uv run pytest tests/test_context_mode_mcp_filter.py -q --tb=short -k real_upstream
# Needs the Docker daemon and network (pulls the devcontainer's Node.js image).
docker run --rm "$(sed -n 's/^FROM \(node:[^ ]*\) AS nodejs$/\1/p' shared/devcontainer/Dockerfile)" node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>24||(a===24&&b>=15)?0:1)'
# Needs the Docker daemon and network (pulls the Node.js image and downloads the pinned package from npm).
PIN="$(sed -n 's/^PINNED_CONTEXT_MODE_VERSION="\(.*\)"$/\1/p' shared/hooks/scripts/context-mode-dispatch.sh)"; test "$(docker run --rm "$(sed -n 's/^FROM \(node:[^ ]*\) AS nodejs$/\1/p' shared/devcontainer/Dockerfile)" bash -c "npm install -g --ignore-scripts context-mode@$PIN >/dev/null 2>&1 && context-mode --version")" = "$PIN"
test "$(grep -r -l -I -F '1.0.169' shared scripts tests | wc -l)" = "0"
test "$(cat README.md docs/runtime-checks.md docs/smoke-tests.md docs/target-mapping.md docs/architecture.md CLAUDE.md AGENTS.md | grep -c -F '1.0.169')" = "0"
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- Build the full devcontainer image and run its tools (recommended as optional). It needs the Docker daemon, the local CUDA base image `nvcr.io/nvidia/cuda-dl-base:26.03-cuda13.2-devel-ubuntu24.04` (9.2 GB), and network to ghcr.io, PyPI, and npm. Run `docker build -t context-mode-2x-devcontainer-check -f shared/devcontainer/Dockerfile shared/devcontainer`, then `docker run --rm context-mode-2x-devcontainer-check bash -c 'openwiki integrations list </dev/null >/dev/null && node -e "require(\"/usr/local/lib/node_modules/jsdom\")" && test -f /usr/local/lib/node_modules/mermaid/package.json'`. The layers after `COPY --from=ghcr.io/astral-sh/uv:latest` rebuild whenever that tag moves.
- Open the devcontainer from VS Code with "Rebuild Container". Inside it, `bash .claude/hooks/scripts/context-mode-dispatch.sh --self-check` reports `observed-version=<pin>`, `version-contract=pinned-direct-binary`, and the Node.js line without a warning.
- The `npx` route (needs network): with the host's global 1.0.169 first on `PATH`, `--self-check` reports `version-contract=pinned-via-npx@<pin>`, and `/mcp` in a live Claude Code session lists three tools.
- In live Claude Code, Codex, and VS Code Copilot sessions, the server lists three tools, and `ctx_index` followed by `ctx_search` works. Record the tool names each client shows.
- Put a fake `node` that reports `v22.22.0` first on `PATH`, and confirm that `--self-check` warns about the Node.js floor.

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

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record the three pause fields, and create a session log
with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it
does not require final findings, LEARN, DOCUMENT, or a completed closeout.
After the checkpoint commit, it may be pushed as a durable remote backup when
paused-publication invariants pass. It remains unfinished and blocks PR creation
and final closeout.
Keep the big plan `in-progress` with the same `current_phase`. On resume, read
the pause log and Git state, restore this plan to `in-progress`, and continue
this same phase without creating another small plan.
