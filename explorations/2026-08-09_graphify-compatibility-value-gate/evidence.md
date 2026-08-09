# Graphify compatibility and value gate — 2026-08-09

## Decision: NO-GO

`graphifyy==0.9.35` has a usable local AST extraction path, honors the tested
ignore rules, and passed a network-denied code-only run. It does **not** meet
the Phase 0 adoption gate: only one of the three required real questions gave
useful, source-confirmed structural connectivity. The other two were,
respectively, an excessively broad truncated traversal and a material miss
that returned unrelated nodes because `CONSUMER_STATE_PATHS` is not represented
in the graph. This is below the required two useful questions. The branch
switch check also could not be fully reproduced because the workspace commit
gate blocks fixture commits, and `update` cannot choose an external output
directory. Reproducibility, write-boundary, and broad raw-tree churn evidence
are also incomplete as described below. These are additional failures, not
waived checks. The primary value failure is sufficient by itself: only 1/3
questions was useful, below the required 2/3 threshold.

Phases A through F are **not authorized**. Do not add an adapter, dependency,
routing surface, generated output, hook, MCP configuration, or workaround for
this result.

## Frozen boundary

| Item | Observed value |
| --- | --- |
| Outer HEAD | `6373f67cd327f07d539a31df8170bcc6c8d7a86a` |
| Initial outer status / unstaged diff / staged diff | all empty |
| Host | Linux 6.18.33.2-microsoft-standard-WSL2, x86_64 |
| `uv` | `/home/ghisso/.local/bin/uv`, 0.10.7 |
| Candidate | PyPI distribution `graphifyy==0.9.35`; candidate executable `graphify` |
| Durable write allowlist | only this ignored file: `.claude/explorations/2026-08-09_graphify-compatibility-value-gate/evidence.md` |
| Ephemeral locations | `/tmp/graphify-phase0.Gg5y04`, `/tmp/graphify-cache.wAigTB`, `/tmp/graphify-tools.lXNCCB` |

The outer repository was never used as a Graphify output location. The real
repository runs used `--out` beneath `/tmp/graphify-phase0.Gg5y04/`; temporary
fixtures and a temporary repository copy were also under that same `/tmp`
directory.

## Acquisition and package origin

The first exact acquisition command was:

```text
env UV_CACHE_DIR=/tmp/graphify-cache.wAigTB UV_TOOL_DIR=/tmp/graphify-tools.lXNCCB \
  uvx --from graphifyy==0.9.35 graphify --version
```

The sandboxed attempt failed DNS lookup for `https://pypi.org/simple/graphifyy/`.
The same exact command was then explicitly approved for this one disposable
download and printed `graphify 0.9.35` with exit 0. No substitute version was
used.

Installed metadata at
`/tmp/graphify-cache.wAigTB/archive-v0/BXRtu64V67Hn3LvET7vGo/lib/python3.13/site-packages/graphifyy-0.9.35.dist-info/METADATA`
reported:

- Name/version: `graphifyy` / `0.9.35`.
- Project origin: `https://github.com/Graphify-Labs/graphify`.
- License expression: `Apache-2.0`.
- Required Python: `>=3.10`.
- Base dependencies: `networkx`, `numpy`, `rapidfuzz`, and 27 Tree-sitter
  language packages; LLM, MCP, document, database, video, and other remote
  integrations are extras and were not installed or invoked.

`uv` retained an unpacked distribution rather than a wheel file, so a wheel
artifact digest was not available. The observed uv package-index cache record
was `graphifyy.rkyv` SHA-256
`5e5d0a44b1e12564528fc5c5d1d5aaa20cb11748ae42caf797c33a9871c03425`;
this is **not** presented as a wheel digest. No advisory scanner was already
available and acquiring a second package would violate the exact-package gate;
therefore advisory scanning is unperformed, another supply-chain limitation.

## Verified CLI contract

`graphify --help` exited 0. The relevant, observed contract is below; all
listed arguments are literal help output, not inferred behavior.

| Operation | Exact argv after `graphify` | Observed result |
| --- | --- | --- |
| Version | `--version` | stdout `graphify 0.9.35`, exit 0 |
| Code-only extract | `extract <path> --code-only --no-cluster --out <DIR>` | writes `<DIR>/graphify-out/graph.json`, `manifest.json`, `.graphify_root`, and AST cache; exit 0 |
| Incremental extract | same extract argv against an unchanged output directory | reports `0 code files changed; 49 unchanged; 0 deleted` and `outputs left untouched`; exit 0 |
| Update | `update <path>` | no `--out` or `--code-only` option; writes `<path>/graphify-out/`; creates `graph.json`, `graph.html`, `GRAPH_REPORT.md`, label files, cache, and sometimes dated `backups/`; exit 0 |
| Query | `query "<question>" --graph <graph.json>` | BFS output; defaults to a 2,000-token budget; exit 0 |
| Path | `path <node-A> <node-B> --graph <graph.json>` | shortest path output; exit 0 |
| Reverse impact | `affected <node> --graph <graph.json>` | reverse traversal; exit 0 |
| Missing graph | query with a non-existent `--graph` path | stderr began `error: graph file not found:`, exit 1; the disposable path suffix was not preserved |
| Corrupt graph | query with a zero-byte `--graph` | stderr `error: could not load graph: Expecting value: line 1 column 1 (char 0)`, exit 1 |
| Missing executable | `env PATH=/usr/bin graphify --version` | stderr `env: ‘graphify’: No such file or directory`, exit 127 |

The top-level help also exposes `install`, platform-specific installers,
`hook install`, MCP, LLM labeling, document/media ingestion, `save-result`,
and `reflect`. None was run. `extract --no-gitignore`, all install/hook/MCP
paths, global graph operations, memory/reflection, LLM backends, and DOCX
commands were deliberately excluded. DOCX behavior remains provisional.

## Fixture and fallback experiment

Fixture source lived at `/tmp/graphify-phase0.Gg5y04/fixture`; its source hash
was recorded before mutation. It contained Python imports, a method call,
inheritance, a dirty edit, a rename (`main.py` to `entry.py`), a deletion
(`base.py`), ignored `.claude/`, `dist/`, and ignored private content, plus a
Markdown file.

Initial code-only extraction found 3 code files, 9 nodes, and 14 edges in
0.21 s. Its source-confirmed structural facts were:

- `src/main.py:5` calls `Worker`; Graphify emitted
  `execute() --calls--> Worker`.
- `src/worker.py:4` inherits `BaseService`; Graphify emitted
  `Worker --inherits--> BaseService`.
- `src/worker.py:6` calls `helper`; Graphify emitted
  `.run() --calls--> helper()`.
- `graphify path src_main_execute src_worker_helper` returned the correct
  three-hop call/method path.

`git check-ignore -v` confirmed `.claude/private.py` and `dist/generated.py`
were ignored. The code-only output contained neither tested ignored marker nor
the tested Markdown marker. Graphify reported only the three source Python
files. After a dirty non-topology edit, `update` reported `No code-graph
topology changes detected; outputs left untouched.` After rename/delete,
`update` rebuilt successfully (9 nodes, 10 edges) and emitted a dated backup.

`update` also indexed the Markdown file in the fixture (11 nodes after the
first update), despite being described as a no-LLM code re-extraction. This is
not a code-only contract and reinforces that later use would need the exact
`extract --code-only` argv. A true committed branch switch could not be
tested: a fixture `git commit` was rejected by the outer phase-closeout hook.
Changing the temporary unborn repository’s `HEAD` symbolic ref between
`fixture` and `alternate` and running `update` worked, but it is not evidence
of a commit-backed branch transition. This required check is therefore marked
incomplete, not passed.

Removing/corrupting the graph produced the failures in the CLI table. With
the executable removed from `PATH`, direct `rg` and direct file reads still
located `entry.py:4`, `worker.py:4-10`, and the call relationship; no stale
Graphify output was treated as current.

## Network-denied privacy proof

After package acquisition, `unshare -n` failed with `Operation not permitted`
and Bubblewrap failed to create `NETLINK_ROUTE`. A locally cached Docker image
provided a stronger available boundary. Docker was used only after explicit
approval, with `--network none`, no image pull, and read-only mounts for the
cached package/runtime and fixture.

The complete Docker argv, including the cached image and mount arguments, was
not preserved. The recorded control arguments were `--rm --network none` and
Python 3.13 running
`socket.create_connection(('1.1.1.1', 443), 2)`; it exited 1 as expected.

It failed with `OSError: [Errno 101] Network is unreachable`. In the same
boundary, exact cached `graphify` completed all of the following with exit 0:

1. `extract <fixture> --code-only --no-cluster --out <declared-output>`:
   2 code files, 7 nodes, 10 edges;
2. `update <isolated-fixture>`: no topology changes, outputs untouched;
3. `query "What calls helper?"`, `path src_entry_execute src_worker_helper`,
   and `affected src_worker_helper` using an explicit graph path.

The code-only extraction had only the declared output mount writable; cached
Graphify and the fixture were read-only. The exact Docker mount list and a
complete write inventory were not preserved in the artifact. Therefore the
network-denial control passes, but filesystem write-boundary evidence is
incomplete. The source mount was read-only and the declared update target was
writable; this does not prove that Graphify attempted no other writes. No
credentials, LLM, API client, or source-network access was requested. Do not
claim a full privacy/write-boundary pass.

## Real-repository comparison

Semble was not installed (`command -v semble` produced no path); this is a
comparison limitation, not a Graphify advantage. Baseline used `rg` and direct
source reads. The recorded extraction form was `graphify extract
/home/ghisso/work/github_copilot_bootstrap --code-only --no-cluster --out
/tmp/graphify-phase0.Gg5y04/repo-warm`. The recorded query form was `graphify
query <question> --graph
/tmp/graphify-phase0.Gg5y04/repo-warm/graphify-out/graph.json`. Literal
per-question query strings were not preserved.

| Required question | Baseline/source authority | Graphify observation | Value result |
| --- | --- | --- | --- |
| Callers/lifecycle of `sync_state_after_install` | `scripts/install_bootstrap.py:760-819` defines `main` and calls `sync_state_after_install` at line 810; function begins at line 570. | Correctly found `main() --calls [EXTRACTED]--> sync_state_after_install()` at line 810. It also returned 22 nodes, including many unrelated sibling calls from `main`. | One useful, source-confirmed direct caller edge; over-broad but usable. |
| `render_shared_basis` through generation, install, and validation | `scripts/generate_targets.py:218` defines it; `render_multi_agent` calls it at 1063; `generate` invokes that path at 1069-1073. Installation copies generated content in `scripts/install_bootstrap.py:133-235`; validation imports/calls `copy_generated_tree` at `scripts/validate_targets.py:30-31,7250`. | Found `render_shared_basis()` but started six nodes and traversed 142 nodes. Output truncated at 73 nodes and did not establish the requested generation-to-install-to-validation path. | No: noisy file discovery/traversal is not sufficient connectivity evidence. |
| Consumers and effects of `CONSUMER_STATE_PATHS` | Defined at `scripts/runtime_ownership.py:40-52`; consumed by `is_consumer_state_path` at 88-94. Installer preserves it at `scripts/install_bootstrap.py:187,196,228-231`; runtime drift ignores it at `scripts/check_runtime.py:163,203`; validator checks it at `scripts/validate_targets.py:5201`. | The identifier was absent from `graph.json`. Query instead started `codex-stop.sh`, `codex_stop()`, and related lifecycle-test nodes. | No: material miss and false/unrelated result. |

The graph’s source citations for the accepted Q1 edge are correct. Q2 makes no
accepted material claim. Q3’s output is explicitly rejected; direct source is
the final authority. Therefore Graphify adds value to only **1/3**, below the
mandatory 2/3 threshold, and has one known material false lead.

## Reproducibility limitations

The literal Graphify commands and measurements retained in this artifact are
the ones shown in the acquisition, CLI, privacy, comparison, and performance
sections. The fixture source hash recorded during execution was not preserved
in the artifact. Baseline `rg`/direct-read command lines, per-tool elapsed
times, and any other disposable command transcripts not shown here were also
omitted. These are incomplete reproducibility requirements after cleanup; the
experiment must not be described as fully reproducible. No retest is required
for this gap because the value gate already failed at 1/3 useful questions.

## Performance, size, and churn

All samples use the exact package and code-only extraction unless labeled
`update`; values are wall-clock seconds from `/usr/bin/time`. Median uses the
middle of the three samples.

| Budget | Samples | Median | Result |
| --- | --- | --- | --- |
| Cold build `<=180 s` | 1.47, 1.63, 1.39 | 1.47 s | Pass |
| Warm changed-source refresh plus Q1 `<=30 s` | 2.60, 2.01, 2.65 | 2.60 s | Pass on disposable repository copy |
| No-op update plus Q1 `<=10 s` | 1.93, 1.93, 1.92 | 1.93 s | Pass on disposable repository copy |
| Raw output `<=50 MiB` | 8,163,371 bytes (7.79 MiB) after update/backups | n/a | Pass |
| No-op graph semantic churn | graph SHA-256 `af2d8c9d144677421aa7401193eb17488ed9f41896caffeb20b8ff522ffd9d11` before and after each no-op; 0-byte graph change | 0% | Pass for `graph.json` only |

The code-only real-repository graph was 2,574,971 bytes (938 nodes, 2,136
edges). `update` lacks `--out`, so it cannot operate on that externally stored
graph; all update timing used a disposable copy of this repository under
`/tmp/graphify-phase0.Gg5y04/repo-fixture`. That copy had the same baseline
source and received only three docstring mutations. Full raw-output-tree
byte/file churn, warm-up behavior, and per-tool elapsed measurements were not
preserved as literal evidence. The exact `graph.json` hash and zero-byte
semantic result above remain valid, but the broad raw-output churn criterion is
incomplete, not passed. This limitation is imposed by the Phase 0
no-workspace-write boundary, not a reason to relax the gate.

## Mandatory criteria ledger

| Criterion | Result | Evidence |
| --- | --- | --- |
| Exact package and executable | Pass | `graphifyy==0.9.35`; `graphify 0.9.35` |
| Code-only network denial | Pass; filesystem write-boundary evidence incomplete | Docker `--network none` control and extraction/update/query operations; exact mount/write inventory unavailable |
| Ignore behavior | Pass for tested `.claude/`, `dist`, ignored private content, and Markdown exclusion in code-only extract | fixture `git check-ignore`, source count, marker scan |
| Dirty edit and rename/delete | Pass | topology no-op and successful 9-node/10-edge rebuild |
| Commit-backed branch transition | **Incomplete** | fixture commit blocked by outer closeout hook; symbolic-ref substitute is not accepted |
| Missing/corrupt graph and missing tool fallback | Pass | exit 1/1/127 and baseline `rg`/direct reads remain usable |
| Cold/warm/no-op/size/churn budgets | Incomplete | cold/warm/no-op timings and size are recorded; `graph.json` SHA/0-byte result is recorded, but broad raw-tree churn and warm-up evidence are unavailable |
| At least two valuable real questions | **Fail** | only Q1 qualifies; Q2 truncated/noisy; Q3 absent/false |
| Every accepted material edge source-confirmed; zero known material false relationships | **Fail** | Q3 produced unrelated nodes for an absent required identifier |

Any one mandatory failure is NO-GO. The primary failure is insufficient
real-question value: only 1/3 qualified, below 2/3. Additional failures are a
known material false lead, an incomplete commit-backed branch-switch test,
incomplete reproducibility, incomplete filesystem write-boundary evidence, and
incomplete broad raw-output churn evidence. Granting disputed or incomplete
checks would not change the primary 1/3 NO-GO decision. The decision is
unambiguous: stop Phases A through F.

## Cleanup and final status

Before cleanup, all disposable package data, fixtures, outputs, logs, and the
temporary repository copy are confined to the three recorded `/tmp` paths.
An independent verifier found an outer untracked
`graphify-out/cache/stat-index.json`; no gitignore rule matched it, and its
timestamp was after Phase 0 started. The earlier claim that this artifact
predated the task and was untouched was wrong. The orchestrator classified it
as task-created, deleted that exact generated file with `apply_patch`, removed
the now-empty `graphify-out/cache` and `graphify-out` directories, and then
confirmed clean outer `git status --short --branch`. That corrected provenance
replaces the earlier statement.

The outer repository had no other tracked or staged Phase 0 file change before
this evidence artifact was created. Final nested status remains a lifecycle
responsibility of the orchestrator; no further cleanup or retest is implied by
this artifact.

---

## Step 7 cross-project applicability supplement — BLOCKED before execution

**Supplement decision: BLOCKED; the original bootstrap NO-GO remains recorded
and the final cross-project override decision is deferred.**

The user authorized the two-consumer read-only supplement, but the exact
package could not be acquired in its required new isolated `/tmp` cache. The
initial sandboxed command was:

```text
env UV_CACHE_DIR=/tmp/graphify-step7-cache.pJalTD \
  UV_TOOL_DIR=/tmp/graphify-step7-tools.lX35JD \
  uvx --from graphifyy==0.9.35 graphify --version
```

It exited 1 after three DNS retries for `https://pypi.org/simple/graphifyy/`.
The required narrowly scoped escalation for that identical command was then
rejected by the approval service due to an account usage limit. The rejection
explicitly prohibits indirect or workaround execution. No alternate version,
pre-existing cache, package, installer, Graphify command, consumer source
index, Docker run, or external network operation was used.

This is an external execution blocker, not a new Graphify quality result. None
of the six required Graphify questions was executed and no cross-project
override can be evaluated. The original bootstrap NO-GO still stops Phases A-F
unless a future authorized supplement can be executed and reviewed.

### Read-only pre-flight completed before the block

Both root `AGENTS.md` files were read before consumer source access. Neither
consumer source tree was otherwise inspected or modified. RAG's tracked
`.gitignore` was read only because Step 7 requires its existing unanchored
`build/` limitation to be recorded; it contains `build/`, which hides live
`src/graph/build/**`. No ignore rule was changed or defeated.

| Consumer | Branch / HEAD | Initial dirty status | SHA-256 of pre-existing dirty files |
| --- | --- | --- | --- |
| `/home/ghisso/work/RAG` | `gliner2-graph-improvements` / `b48613f480ad87a3fa5e76975d37bc9ce5139fec` | `M .devcontainer/Dockerfile`; `M .devcontainer/devcontainer.json`; `M .devcontainer/post-start.sh`; `M .gitignore`; `?? .devcontainer/restore-root-adapters.sh`; `?? .devcontainer/state-sync.sh` | `Dockerfile` `1b80fc0bdbfef9e49d455664f3b0125d692c4776d5e953e13f019529a860bb45`; `devcontainer.json` `a80f84e6079b59b2e7fde4ae0e3358b39c8e9364d7c08c9858ba9f2239ca56a9`; `post-start.sh` `7a5a7c2eb1cd3f6f9556c0d9720347abcaa51f73b22425cce5aac2530df5d0d4`; `.gitignore` `f4b873a6600109e05233ef0a579b30492a3f2485c3bff9f0fdea506b19d49155`; `restore-root-adapters.sh` `bdf148398cd4ce2fb6cabcfd005a760e9b0a4913584a08c6143c70177466b1a1`; `state-sync.sh` `eaefeffedad382de6aaca210b6ab923f604d24a9477127a39c3c4bfffe467d70` |
| `/home/ghisso/work/git_projects/industrial-inspection` | `2026-07-21_haystack-3-agent-refactor_implementation` / `28378951c91c08abdb136f549ab6136e6919b7d6` | `M .devcontainer/restore-root-adapters.sh`; `M .devcontainer/state-sync.sh` | `restore-root-adapters.sh` `bdf148398cd4ce2fb6cabcfd005a760e9b0a4913584a08c6143c70177466b1a1`; `state-sync.sh` `eaefeffedad382de6aaca210b6ab923f604d24a9477127a39c3c4bfffe467d70` |

Both nested `.claude` status commands were clean at pre-flight. Semble was not
available. The bootstrap outer worktree had no status, unstaged-diff, or
staged-diff output at the same pre-flight check. The only task paths created
before the block were the three named `/tmp/graphify-step7*` directories.
Their cleanup and final equality checks are recorded below.

### Final status and cleanup

Both consumers were rechecked after the blocked acquisition. Their branch,
HEAD, full `git status --short --untracked-files=all`, clean nested `.claude`
status, and every listed dirty-file SHA-256 exactly matched the pre-flight
table. The bootstrap outer worktree also remained clean; its nested status
shows this evidence artifact as the only Phase 0 supplement modification.

The empty working directory `/tmp/graphify-step7.1ZmFA3` was removed. The uv
cache and tool directories contained only the failed acquisition's uv metadata:
`/tmp/graphify-step7-cache.pJalTD` and
`/tmp/graphify-step7-tools.lX35JD`. Recursive removal of these explicit,
task-created paths was rejected by the command approval service due to the
same account usage limit, with an instruction not to work around it. They are
the only remaining temporary paths; no consumer or bootstrap path is a
cleanup target. A permitted cleanup action must remove them before phase
closeout.
