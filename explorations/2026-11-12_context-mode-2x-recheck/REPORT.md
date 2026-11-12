# Context Mode 2.x recheck (pre-branch spike S1 to S8)

**Date:** 2026-11-12. **Kind:** evidence only. **Plan:** `.claude/plans/context-mode-2x-migration.md`, section "Pre-Branch Spike".
**Settle check:** waived by the user on 2026-11-12 (decision 1 changed to "Start now"; see the plan's Approval record).
**Who:** an evidence-only `coder` subagent ran the probes in the session scratch folder; the orchestrator saved this report, the harness (`scripts/`), and the small raw outputs (`raw/`, files under 64 KB). The outer repository was not changed: clean `dev`, no branch, no commit.

Pinned candidate: 2.1.8
Node image: node:24.22.3-bookworm-slim
Server identity: argv `context-mode server --agent codex` (direct binary, or `npx -y context-mode@2.1.8 server --agent codex`); working folder = the outer repository root (the dispatcher must `cd` there first); environment `CONTEXT_MODE_DATA_DIR=<repo>/.claude/.cache/context-mode`; `CLAUDE_PROJECT_DIR` and `--workspace-folder` are not needed
Server name: context-mode / context-mode

Host 1.0.169 reports `{"name":"context-mode","version":"1.0.169"}`. 2.1.8 reports `{"name":"context-mode","version":"dev"}`. The names are the same, so a gate on the name alone cannot tell 1.x from 2.x.

## Probe results

- S1 PASS
- S2 PASS: both identities pass; `--agent codex` needs the dispatcher to `cd` to the repository root.
- S3 PASS as a probe. It finds no bound and finds symlinks followed, so the files-only fallback is required.
- S4 PASS
- S5 PASS (evidence gathered)
- S6 PASS
- S7 PASS (no Antigravity id)
- S8 PASS (drift listed)

**Stop conditions hit: none.** Not a stop, but reported: S3 found no bound and symlinks followed.

## Plan impact

- Phase A: replace `PIN_FROM_SPIKE` with `2.1.8`; the identity gate accepts `serverInfo.name == "context-mode"` with `serverInfo.version == "dev"` (what 2.1.7 and 2.1.8 report; 1.0.169 reports `"1.0.169"`); set `AGENT_FROM_SPIKE` to `codex`; write the kit `ctx_index` description as files-only: `Example: \`ctx_index({path:"docs/api.md"})\`. Required: one of path, content.` / `Stores content so it can be searched later: one local file inside this repository, or raw text. Folders and URLs are not accepted. Use it for documentation or large files you will query more than once, then use ctx_search instead of reading the content again. Returns the source label and how many chunks were stored.` (Orchestrator note: Phase A still runs on 1.0.169, so its gate must also accept what 1.0.169 reports until Phase B switches the pin.)
- Phase B: replace `PIN_FROM_SPIKE` with `2.1.8` and `NODE_IMAGE_FROM_SPIKE` with `node:24.22.3-bookworm-slim`; launch `context-mode server --agent codex` (or `npx -y context-mode@2.1.8 server --agent codex`) through the filter after the dispatcher does `cd "$REPO_ROOT"` (outer repository root, taken from its own script location; it has no `cd` today), exporting `CONTEXT_MODE_DATA_DIR`; no `CLAUDE_PROJECT_DIR` and no `--workspace-folder`; the `ctx_index` files-only fallback IS needed, so its step runs: `validateIndex` accepts `content` or a regular-file `path` only (reject folders), and `FILTER_CONTRACT` gets a new value.

## Surprises and cautions

1. 2.1.8 was under 9 hours old at spike time (published 2026-11-11T22:11Z). Start Gate line 1 (age at least 14 days) exits 1 for it, so that line must be waived or edited. Any later release also moves `latest`.
2. S3: `ctx_index` on a folder has no limit on files, depth, or size. 3000 files, depth 25, and a 19.2 MB file were all accepted.
   - A `.gitignore` above the indexed folder is ignored. It is honored only when it sits inside the folder, or when you index `.`.
   - The upstream containment root is the repository's **parent folder**, not the repository. Symlinks inside a folder that point anywhere inside the parent folder are followed, which reaches sibling projects.
   - The kit filter's `validateIndex` checks only the top-level path, so it cannot see this.
   - Indexing `.` with an un-ignored data root picked up `.claude/.cache/context-mode/projects/<key>/owners/<session>.pid`.
3. `--agent codex` keys the project to the working folder. From `<repo>/.claude` (a nested Git repository) it uses the nested repository's folder. `CLAUDE_PROJECT_DIR` keeps the outer repository from either folder.
4. Per-host agent ids are not needed. One identity served all three client names with no differences. The check used probe clients, not live Claude Code, Codex, or VS Code sessions.
5. 2.1.7 to 2.1.8 is invisible to every kit-facing contract tested: `initialize`, `tools/list` for all 9 tools, 32 recorded hook inputs, 35 synthetic hook steps, and tool results were byte-identical.
6. `ctx_doctor` with `--agent codex` also starts the host's `codex app-server` (it wrote under the scratch `HOME/.codex`). It is outside the kit's three-tool surface.
7. The server exits with code 1 when stdin closes (same as 2.1.7).

NOT RUN: live-client sessions (real hook payloads, how Codex and VS Code name the server's tools, auto mode and `updatedToolOutput`). Also not re-run: the NODE_TOO_OLD hook fallback on Node 22 (the hook lane is being removed).

## Method

- Install: `npm install --prefix $SCRATCH/pkg --cache $SCRATCH/npm-cache --ignore-scripts context-mode@2.1.8`. 2.1.7 was installed the same way into `$SCRATCH/pkg-2.1.7`, for drift comparison only. Nothing was installed globally. `setup`, `upgrade`, `doctor --fix`, and `ctx_upgrade` were never run.
- Every probe ran through `scripts/cmrun.sh`: `env -i`, with `HOME`, `XDG_*`, `TMPDIR`, `CONTEXT_MODE_DIR`, `CONTEXT_MODE_DATA_DIR`, `CLAUDE_CONFIG_DIR`, `CODEX_HOME` and the other client variables inside `run/<label>/`. The working folder was a scratch Git repository (`git init` only).
- Kit-tool probes ran in `bwrap --unshare-net --ro-bind / / --bind <run> <run>`: no network, and every write outside the run folder fails.
- Harness edits, kept small:
  - `cmrun.sh` finds its scratch folder from its own path, exports `CONTEXT_MODE_DATA_DIR`, accepts `-KEY` to drop a variable, and accepts `--ro`.
  - `mcp_probe.py` can declare client capabilities (`PROBE_CAPS`), answers `roots/list` (`PROBE_ROOTS`), and records server-to-client requests.
  - New scripts: `case.sh`, `s2_matrix.py`, `s2_single.py`, `s2_same.py`, `dump_tools.py`, `s3_build.py`, `s3_calls.py`, `s3b.py`, `s3c.py`, `list_sources.mjs`, `s4_run.sh`, `s4_analyze.py`, `notes_since.py`, `s8_replay.py`, `s8_hook_diff.py`, `s8_sequences.py`, `s8_dirs.py`, `s8_misc.py`, `s8_dispatch.py`, `s8_node22.py`.
- The dispatcher and filter were copied from `shared/hooks/scripts/` into the scratch folder. `filter-gate-dev.mjs` differs from the filter by one line (`PINNED_VERSION = "dev"`) and was used only to see what the filter lets through.

## S1 Release record

`npm view context-mode time dist-tags --json` (`raw/npm-time-disttags.json`):

```
dist-tags: {"next":"2.0.0-next.40","latest":"2.1.8"}
stable 2.x: 2.0.0 11-04T17:27Z, 2.0.1 11-04T19:41Z, 2.0.2 11-04T21:37Z, 2.1.0 11-05T01:06Z, 2.1.1 11-05T13:10Z,
            2.1.2 11-05T14:30Z, 2.1.3 11-05T15:34Z, 2.1.4 11-05T22:07Z, 2.1.5 11-06T15:45Z, 2.1.6 11-08T01:07Z,
            2.1.7 11-08T15:02Z, 2.1.8 11-11T22:11:23Z   (31 prereleases)
```

- Candidate = newest stable 2.x = `2.1.8` = npm `latest`.
- `npm audit signatures` in the install prefix: 1 package has a verified registry signature, 1 package has a verified attestation. Provenance predicate `slsa.dev/provenance/v1`, gitHead `92c1ad26d57b45e786a3dc9149549c416badca09`.
- `sha256sum --check SHA256SUMS`: 38 of 38 OK.
- Package facts: 39 files, 6.6 MB, no `dependencies`, no `scripts`, `engines.node >=24.15.0`, `Elastic-2.0`. LICENSE sha256 `92f11a86...` is the same as 2.1.7. `package.json` equals 2.1.7 apart from `version`.
- Release notes since 2.1.7 (`raw/release-notes-after-2.1.7.md`, GitHub releases API): one stable release, v2.1.8, 18 fixes and one performance line. Per item the plan lists:
  - Server command: no change. Agent ids: no change (notes touch only OpenCode, Codex setup, Copilot CLI setup). `CONTEXT_MODE_DATA_DIR`: no change.
  - Tool names and schemas: no change to `tools/list`. Behavior fixes only: `ctx_search` treats a blank `source` as absent and accepts `offset:0` and `after:0`; `ctx_resume` treats a blank session as absent (#1353, #1354). Also a `..` check on the raw tool path, and "Claude Code replace pointer names only tools the caller can call" (#1342, #1358, #1345).
  - Network calls: none listed. Writes outside the data root: none listed.
- Code cross-check (`raw/diff-server-2.1.7-2.1.8.txt`, 276 changed lines). No changed line mentions fetch, http, connect, writeFile, mkdir, `DATA_DIR`, `AGENT_IDS`, `resolveAgent`, or `CLAUDE_PROJECT_DIR`. The changes are renames, the three `ctx_search` input fixes, doctor and setup code, and the build hash. The database schema list is unchanged (versions 1 to 6).
- `tools/list` for all 9 tools and the `initialize` result are byte-identical between 2.1.7 and 2.1.8.

## S2 Server contract and one server identity

Settings for every case: working folder = scratch Git repository, `CONTEXT_MODE_DATA_DIR=<repo>/.claude/.cache/context-mode`, `HOME` = scratch, no network. Each case runs `initialize`, `tools/list`, `ctx_index(content)`, `ctx_search`, `ctx_stats` (`raw/s2-matrix.txt`):

```
a1 --agent claude-code, CLAUDE_PROJECT_DIR set        index/search/stats ok
a2 --agent claude-code, no CLAUDE_PROJECT_DIR         ok
b1 --agent codex, no CLAUDE_PROJECT_DIR               ok
b2 --agent codex, CLAUDE_PROJECT_DIR set              ok
c1 --agent vscode --workspace-folder <repo>           ok
c2 --agent vscode, no --workspace-folder              ERROR "Project source arg:workspaceFolder is missing. Fix: run ctx_doctor."
d1 no --agent, CLAUDE_PROJECT_DIR set                 ok
d2 no --agent, no CLAUDE_PROJECT_DIR                  ERROR "Project source --agent is missing. Fix: run ctx_doctor."
```

Same in all eight cases (`raw/s2-tools-2.1.8.txt` has the full listing):

- `initialize` keys: `capabilities`, `instructions`, `protocolVersion` (`2025-06-18`), `serverInfo` (`{"name":"context-mode","version":"dev"}`). Capabilities: `{"experimental":{"codex/sandbox-state-meta":{}},"tools":{"listChanged":true}}`.
- `instructions`: 509 characters, identical to 2.1.7. It tells the model to use `ctx_execute` and says a large Read is denied.
- Tool names (9): `ctx_execute`, `ctx_batch`, `ctx_index`, `ctx_search`, `ctx_resume`, `ctx_stats`, `ctx_doctor`, `ctx_upgrade`, `ctx_purge`.
- `ctx_index`:
  - Keys: `description`, `inputSchema`, `name`. No `_meta`, no annotations.
  - Description (439 characters): `Example: \`ctx_index({path:"docs/api.md"})\`. Required: one of path, content, url.` / `Stores content so it can be searched later: a local file or folder (nested .gitignore files are respected), raw text, or a URL, which is fetched and converted to Markdown. Use it for documentation or large files you will query more than once, then use ctx_search instead of reading the content again. Returns the source label and how many chunks were stored.`
  - `inputSchema`: `additionalProperties:false`, no `required` list. Properties `path`, `content`, `url`, `source`, each `{"type":"string"}`. No property descriptions.
- `ctx_search`:
  - Annotations `{"readOnlyHint":true}`. No `_meta`.
  - Description: 838 characters, starts `Example: \`ctx_search({queries:["auth middleware"]})\`. Required: queries.`
  - `inputSchema`: `required:["queries"]`, `additionalProperties:false`. Properties: `queries` (array of string), `scope` (enum session/worktree/project), `source` (string), `offset` (integer, minimum 0), `sort` (enum relevance/timeline), `after` (integer, minimum 0).
- `ctx_stats`: annotations `{"readOnlyHint":true}`; description (259 characters) `Example: \`ctx_stats({})\`. Required: none.` / `Reports the bytes context-mode kept out of the chat: a text report (bars, per tool, per agent) and a Markdown table. Show the text block to the user unchanged, in a code block. Use it when the user asks what it saved.`; no input properties.
- Host 1.0.169: `serverInfo` `{"name":"context-mode","version":"1.0.169"}`, 11 tools, capabilities prompts/resources/tools, no `instructions`.

Single-identity check (`raw/s2-single.txt`, `raw/s2-same.txt`):

- Setup:
  - Identities: X = `--agent codex` from the repository root; Y = no `--agent` with `CLAUDE_PROJECT_DIR=<repo>`. X was also run with `CLAUDE_PROJECT_DIR` set (X2).
  - Each identity ran three sessions in one repository, with `clientInfo.name` = `claude-code`, `codex-mcp-client`, `Visual Studio Code`. Each session ran `ctx_index(content)` then `ctx_search`.
  - Each combination ran with no declared capabilities, and again with `{"roots":{"listChanged":true}}` declared and `roots/list` answered. Flat and nested layouts both ran.
- Results:
  - All 36 sessions indexed and searched. Later sessions also found earlier notes (one shared index).
  - Server-to-client requests, including `roots/list`: none, even when roots were declared. No client has to answer anything differently.
  - Files written outside the data root: none in any combination.
  - Project folder: one folder per combination. Started at the repository root, it equals `sha256(<repo>/.git)[:16]` (the outer repository) for X, X2, and Y. X and Y run against the same repository shared one folder.
- Nested Git repository at `<repo>/.claude`:
  - Started at the repository root: X and Y both use the outer repository's folder.
  - Started in `<repo>/.claude`: X and X2 use the nested repository's folder, a different project. Y still uses the outer repository's folder.
  - Source (`resolveProject`): key = `sha256(git common dir)[:16]`. `--agent codex` uses the working folder. Claude Code uses `CLAUDE_PROJECT_DIR` first.
  - So X needs the dispatcher to `cd` to the outer repository root before launching. The current dispatcher does not `cd`; it only exports `CONTEXT_MODE_PROJECT_ROOT`.
- Verdict: both pass. X passes with the `cd`; Y passes without it. X is preferred because it sets no other client's variable.

## S3 `ctx_index` folders

Fixtures (`scripts/s3_build.py`): `bulk/` with 300 small files at depth 0 to 7, `ignored.txt` and `ignored-dir/` listed in the repository-root `.gitignore`, three symlinks (to a file beside the repository, to a folder beside the repository, to a file two levels above it), plus `deep/` (depth 25), `many/` (3000 files), `huge/big.txt` (19.2 MB). Results (`raw/s3-results.txt`):

```
ctx_index "bulk"      -> Indexed 304 source(s) (300 files + ignored.txt + ignored-dir/x.txt + link-sibling.txt + link-dir/inner.txt)
ignoredtoken          -> FOUND (the repo-root .gitignore was not applied)
siblingtoken          -> FOUND via bulk/link-sibling.txt  (symlink to a file OUTSIDE the repo was followed)
siblingdirtoken       -> FOUND via bulk/link-dir/inner.txt (symlink to a folder OUTSIDE the repo was followed)
outsidetoken          -> no hits (symlink target outside the repo's PARENT folder: skipped silently)
bulktoken007          -> found at bulk/d1/.../d7/f007.txt (depth 7)
ctx_index "deep"      -> indexed a file at depth 25
ctx_index "many"      -> Indexed 3000 source(s)
ctx_index huge/big.txt-> Indexed 1 source, 4688 chunks (19.2 MB)
ctx_index "../sibling.txt" -> accepted (outside repo, inside parent folder)
ctx_index <abs path above the parent> -> error "is outside the project"
ctx_index bulk/link-outside.txt -> error "is outside the project"
```

- Source reading: no maximum for files, depth, or bytes. Containment root = the repository's **parent folder** (`containmentRootOf`). `.gitignore` files are read only from folders the walk enters.
- Follow-ups (`s3b.py`, `s3c.py`):
  - A `.gitignore` inside the indexed folder works, and nested ones work. `ctx_index .` applied the root `.gitignore`.
  - `ctx_index .` with an un-ignored data root indexed `.claude/.cache/context-mode/projects/<key>/owners/<session>.pid`. `context.db` itself was not indexed.
- The kit filter's `validateIndex` checks only the top-level path (no `..`, not a symlink, real path inside the repository, file or folder). It cannot see inside a folder.
- Rule in the plan: "no bound, or symlinks followed -> files-only fallback". Both hold.

## S4 Writes and network

Server under `strace -f -e trace=%file,%network,%process,%desc` in the no-network, read-only sandbox, for startup alone and for startup plus `ctx_index` (content and path), `ctx_search`, `ctx_stats`:

- Network syscalls: 0 for startup, and 0 for startup plus the three tools. The server only opens `/etc/resolv.conf` to read. It runs `git worktree list --porcelain` once for a path index.
- Files created: under the data root only (`projects/<key>/context.db` plus empty `owners/` and parent folders). Startup alone creates nothing.
- `HOME`, `XDG_*`, `TMPDIR`, repository tree outside the data root: nothing created. The only write attempt outside the run folder was `O_RDWR` on `/dev/null`. `~/.context-mode` does not exist on the real home.
- The S2, S3, and S8 runs also ran read-only outside their run folders with no errors.

## S5 Codex compaction

- Codex source: `main` (c0cc9fc, 2026-11-12), host `rust-v0.147.0`, and latest stable `rust-v0.167.2` all have the same code:
  - `codex-rs/hooks/src/events/session_start.rs`: `enum SessionStartSource { Startup, Resume, Clear, Compact, Fork }`. `matcher_input()` returns the source string.
  - `codex-rs/core/src/session/mod.rs` (line 3282 in v0.147.0, 4681 in v0.167.2, 5003 on main): after a compaction it calls `queue_pending_session_start_source(SessionStartSource::Compact)`.
- Codex docs (https://developers.openai.com/codex/hooks, redirects to https://learn.chatgpt.com/docs/hooks), read through a summarizer, so the source above is the verbatim proof: `source` is "startup, resume, clear, compact, or fork"; "`matcher` is applied to `source`"; "SessionStart hooks that match `source: "compact"` run before the next model request", including mid-turn automatic compaction.
- Answer: yes, Codex sends SessionStart with `source: compact` (and `fork`).
- Kit matchers:
  - Codex `startup|resume|clear` (`scripts/generate_targets.py:1218`) matches neither, so nothing runs after a compaction.
  - The Claude SessionStart group has no matcher. It would run on `compact`, but the filter drops its text (plugin prefix).
  - Copilot `shared/hooks/hooks.json` has no matcher.
- This only informs decision 4's "narrow plus Codex compaction" option, which the user did not choose. The 2.1.8 Codex compact output is 246 bytes, which the filter forwards.

## S6 Node.js 24 image

- `https://nodejs.org/dist/index.json`: newest v24 is `v24.22.3` (2026-11-10). Next: 24.22.2, 24.22.1.
- `docker manifest inspect node:24.22.3-bookworm-slim`: exit 0, OCI index with amd64, arm64 v8, ppc64le. Pulled digest `sha256:dc26ae92c9fb15cf6b1d63e20f0944b2efe0f115b20e00be48fb23fceb061c54`.
- Phase B's two slim checks with pin `2.1.8` (`raw/s6-slim-checks.txt`):
  1. The node floor check exits 0 (`v24.22.3`).
  2. `docker run --rm node:24.22.3-bookworm-slim bash -c "npm install -g --ignore-scripts context-mode@2.1.8 >/dev/null 2>&1 && context-mode --version"` prints `2.1.8`, equal to the pin.
- Full build: a scratch copy of `shared/devcontainer/Dockerfile` with exactly three changes (image `node:24.22.3-bookworm-slim`, `context-mode@2.1.8`, and `test "$(context-mode --version)" = "2.1.8"` in place of `--help`). `docker build` exit 0, **134 s**. Only the CUDA base image was cached; apt, npm, PyPI, and `uv:latest` were fetched. Its own checks passed (`raw/s6-build.log`).
- In the built image (`raw/s6-image-checks.txt`):
  - `node v24.22.3`, `context-mode 2.1.8`.
  - `openwiki integrations list </dev/null` printed 9 integrations, exit 0.
  - `require(".../jsdom")` worked.
  - Global `mermaid` is `11.16.0`. The plan's optional one-liner printed PASS.
  - The real 2.1.8 server also ran inside the image with `--network none`: 9 tools, and `ctx_index` plus `ctx_search` worked.
- The built image was removed. The pulled `node:24.22.3-bookworm-slim` and `node:22.22.0-bookworm-slim` stay in the local Docker cache.

## S7 Antigravity

- Accepted ids (`var AGENT_IDS`, 2.1.8, identical to 2.1.7): `claude-code`, `codex`, `gemini`, `qwen`, `copilot-cli`, `vscode`, `kiro`, `zcode`, `pi`, `opencode`.
- None targets Antigravity. `--agent antigravity` prints `unknown --agent antigravity` and every tool call fails. Antigravity appears only in an `UNSUPPORTED_HOSTS` list the doctor uses. The 2.0.0 notes say it is not supported and that to keep it you stay on 1.0.169.
- Decision 2 stands: no Antigravity Context Mode entry.

## S8 Drift

Context section of the plan:

| # | Finding | Result | Evidence |
|---|---|---|---|
| 1 | Node 24.15+ required | unchanged | `engines >=24.15.0`. On `node:22.22.0-bookworm-slim`: `npm install` succeeds with `EBADENGINE`, `--version` prints 2.1.8, the server is degraded with only `ctx_doctor`, and `ctx_index` returns "Tool ctx_index not found". |
| 2 | `serverInfo.version` always `"dev"`, filter gate fails | unchanged | The unmodified kit filter against 2.1.8 returns `-32002 "Context Mode 1.0.169 required"` and exits 1. |
| 3 | Needs `--agent` or `CLAUDE_PROJECT_DIR`; no Antigravity id | unchanged | c2 and d2 fail; S7. |
| 4 | Server command is `context-mode server` | unchanged | `mcp` alias works; bare `context-mode` prints usage and exits 0; `--version` and `-v` print 2.1.8; `version` exits 2. |
| 5 | `instructions` passes the filter and names blocked tools | unchanged | 509 characters, identical to 2.1.7. The gate-patched filter copy passes the full text. |
| 6 | `CONTEXT_MODE_DIR` ignored, `CONTEXT_MODE_DATA_DIR` sets the root, 1.x not migrated | unchanged | `raw/s8-dirs.txt`: with only `CONTEXT_MODE_DIR`, data went to `HOME/.context-mode/...` and 0 sources were found. With `DATA_DIR` set to the folder holding the 1.x files, 0 sources were found and the 1.x files were still present. File contents were not hashed. |
| 7 | PreCompact no-op; PreToolUse forwards nothing | unchanged | 32 of 32 hook replays identical to 2.1.7; 7 of 32 equal the 1.0.169 fixtures (all empty); the filter forwards only Codex SessionStart compact (246 B). |
| 8 | New hook shapes; Claude text uses the plugin prefix | unchanged | 3 synthetic sequences (35 steps) identical to 2.1.7, including `updatedToolOutput` and `mcp__plugin_context-mode_context-mode__ctx_*`. |
| 9 | `ctx_doctor` goes online, fails D3, writes reports | unchanged | In the no-network sandbox: DNS attempts for `registry.npmjs.org` and `github.com`; D1 UNKNOWN; D3 FAIL "wrong: MCP entry, hook entries"; report at `<data root>/reports/doctor-<ts>.md`. New detail: D5 starts `codex app-server`. |
| 10 | Kit's Codex SessionStart matcher excludes `compact` | unchanged | `generate_targets.py:1218`; S5 shows Codex does send `compact`. |

2026-11-11 REPORT.md "Go or no-go" lines:

| Line | Result | Evidence |
|---|---|---|
| Gives: cleaner install (no native module, no install script, provenance, checksums) | unchanged | S1. |
| Gives: no startup or hourly network calls | unchanged | S4: 0 network syscalls. |
| Gives: a working `--version` | unchanged | prints 2.1.8. |
| Gives: no Agent prompt rewrite | unchanged | Claude Agent replay prints nothing. |
| Gives: better search and upstream containment | unchanged in code, newly qualified | S3: parent-folder containment, symlinks followed, no bounds. |
| Gives: a maintained release line | changed | one more stable release (2.1.8). |
| Costs 1: Node 24.15+ | unchanged | S6, S8 row 1. |
| Costs 2: per-host `--agent`, no Antigravity id | changed | S2: one identity serves all three client names. Antigravity unchanged (S7). |
| Costs 3: version gate and `instructions` | unchanged | rows 2 and 5. |
| Costs 4: `CONTEXT_MODE_DATA_DIR`, old data abandoned | unchanged | row 6. |
| Costs 5: hook-lane rework | unchanged | rows 7 and 8. |
| Costs 6: `ctx_doctor` decision | unchanged | row 9. |
| Costs 7: fixtures, tests, docs, pin-bump procedure | unchanged | |
| Costs 8: release churn (11 stable in 4 days) | changed | 12 stable in 7 days (2.0.0 11-04 to 2.1.8 11-11). 2.1.8 came 3 days 7 hours after 2.1.7. |
| Verdict: no-go as a simple pin bump | unchanged | |
| Verdict: reasonable once 2.1.x settles | changed | the settle check was waived by the user; Start Gate line 1 now fails. |
| Verdict: 1.0.169 stays safe, the dispatcher refuses other versions | unchanged | `--self-check` with the 2.1.8 binary first on `PATH`: `observed-version=2.1.8`, WARN, `version-contract=pinned-via-npx@1.0.169`. |
| Open: real client hook payloads | NOT RUN | needs live clients. |
| Open: how Codex and VS Code name the kit's tools | NOT RUN | needs live clients. |
| Open: Antigravity agent id | answered, unchanged | none. |
| Open: devcontainer on Node 24 | answered, yes | S6. |
| Open: keying inside the nested `.claude` repository | answered | S2. |
| Open: auto mode and `updatedToolOutput` | NOT RUN | moot (filter drops it; hook lane removed). |
