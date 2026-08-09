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

> **Later addition.** A user-authorized two-consumer supplement was afterwards
> executed under Step 7. It also failed: see
> "Step 7 cross-project applicability supplement — EXECUTED". The decision on
> this line is unchanged and is now supported by two independent results.

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

## Step 7 cross-project applicability supplement — EXECUTED

**Supplement decision: cross-project override FAILED. The final Phase 0
decision remains NO-GO and Phases A-F remain unauthorized.**

This section supersedes the BLOCKED section above only on execution status.
The blocking cause was an external control (sandbox DNS plus an approval-service
usage limit), not a Graphify result, and that section's measurements stand as
written. Network access was available in this session, so the same pinned
package was acquired and all six required questions were executed.

### Acquisition and execution boundary

`graphifyy==0.9.35` was acquired from PyPI and pinned into one disposable
container image. No other version was used.

| Item | Observed value |
| --- | --- |
| Package | `graphifyy==0.9.35`, `requires_python >=3.10` |
| Wheel | `graphifyy-0.9.35-py3-none-any.whl`, 1 243 046 bytes, sha256 `97f5aa68a2779fe0bf14ce0419c3bfa42afeca2f4dc0c3db93b922c191f6967f` |
| Reported CLI version | `graphify 0.9.35` |
| Base image | `python:3.12-slim`, non-root user `gate` (uid 1000) |
| Extras installed | none; base deps are `networkx`, `numpy`, `rapidfuzz`, and tree-sitter grammars only — no MCP, LLM, document, or media backend |
| Docker | `Docker version 28.3.1, build 38b7060` |

Every Graphify invocation used `--network none`, mounted consumer source at
`/src` read-only, mounted a task-owned writable output dir at `/out`, and used
a task-owned writable `/work` as the working directory. The two literal
extraction commands were:

```text
docker run --rm --network none \
  -v /home/ghisso/work/RAG:/src:ro \
  -v /tmp/graphify-step7-run/RAG/out:/out \
  -v /tmp/graphify-step7-run/RAG/work:/work \
  -w /work graphify-gate:0.9.35 \
  graphify extract /src --code-only --no-cluster --out /out

docker run --rm --network none \
  -v /home/ghisso/work/git_projects/industrial-inspection:/src:ro \
  -v /tmp/graphify-step7-run/II/out:/out \
  -v /tmp/graphify-step7-run/II/work:/work \
  -w /work graphify-gate:0.9.35 \
  graphify extract /src --code-only --no-cluster --out /out
```

Every query reused that exact mount set, replacing the trailing program with
`graphify <op> ... --graph /out/graphify-out/graph.json`. The literal `<op>`
arguments per question are recorded verbatim in each question's section below.

**Positive controls for the two boundaries.** Both were re-run inside the same
pinned image rather than inferred from exit codes:

```text
$ docker run --rm --network none graphify-gate:0.9.35 \
    python -c "import socket; socket.create_connection(('pypi.org',443),timeout=5)"
PROBE-RESULT: BLOCKED OSError: [Errno -3] Temporary failure in name resolution

$ docker run --rm --network none -v /home/ghisso/work/RAG:/src:ro ... \
    graphify-gate:0.9.35 sh -c "touch /src/WRITE_PROBE; echo rc=$?"
touch: cannot touch '/src/WRITE_PROBE': Read-only file system
rc=1
```

The first proves the container could not reach the network even when it tried;
the second proves the consumer mount rejected a write attempt. The image is
reproducible: an independent rebuild from the same Dockerfile produced the
identical digest `sha256:199e272a8eab6ea1b4d86d5ef38e8f12a959aa90c7423473bb2283daf5887028`.

No consumer was written, no branch was switched, no `graphify update` ran
against a consumer, `--no-gitignore` was never used, and no installer, hook,
MCP, LLM, or media operation ran. No application import, test, service, or
dependency synchronization ran.

**Refinement of the earlier cwd lesson.** The prior run observed Graphify
creating `graphify-out/cache/stat-index.json` in the process working directory.
In both consumer runs here, every `extract` passed `--out` and the working
directory was left completely empty (`work_bytes=0`), with `stat-index.json`
written under `/out/graphify-out/cache/` instead.

This narrows the observed behavior but does **not** establish the cause. Only
`extract` accepts `--out`; `update`, `query`, `path`, and `affected` do not, so
the earlier artifact cannot be attributed to "omitting `--out`" without knowing
which command produced it, and that command was not recorded. The operational
rule is unchanged and still mandatory: always run Graphify from a task-owned
working directory, never with a consumer repository as cwd.

### Measurements

| Metric | RAG | industrial-inspection | Budget |
| --- | --- | --- | --- |
| Cold extraction, exit code | 10.400 s, exit 0 | 2.785 s, exit 0 | `<= 180 s` — PASS |
| Slowest measured query | 2.099 s | 0.722 s | `<= 10 s` — PASS |
| Raw output tree | 18 770 292 B (17.90 MiB) | 3 624 560 B (3.46 MiB) | `<= 50 MiB` — PASS |
| `graph.json` | 9 135 881 B | 1 793 675 B | n/a |
| Graph size | 8 302 nodes, 17 739 edges | 1 390 nodes, 3 591 edges | n/a |
| Code files indexed | 451 | 126 | n/a |
| Distinct source files in graph | 446 | 120 | n/a |
| Working-dir artifacts | 0 B | 0 B | none — PASS |

Edge confidence in the RAG graph was `EXTRACTED` 15 637 and `INFERRED` 2 102.

### Exclusion and privacy result

Both graphs were scanned for forbidden paths and secret-shaped content.

- No `.env*`, `.claude/`, `.git/`, `credentials`, `secret`, `.venv/`,
  `node_modules`, `dist/`, `.pem`, or `.key` path appeared in either graph.
- No value matched `hf_[A-Za-z0-9]{20,}`, `sk-[A-Za-z0-9]{20,}`,
  `AKIA[0-9A-Z]{16}`, or a private-key header.
- Both consumers list `.env.example` among files Graphify skipped as
  unclassified. It was named in stdout but not indexed.
- An initial automated scan flagged ten industrial-inspection paths under
  `src/industrial_inspection/data/`, `src/configs/data/`, and `tests/data/`.
  These are first-party `.py` modules under a directory named `data`, not
  datasets or model weights. The flag was a false positive of the scan pattern,
  not an exclusion failure. No dataset, model, or binary artifact was indexed.

Network denial passed, established by the positive control above rather than by
exit codes alone: a deliberate outbound connection from inside the pinned image
under `--network none` failed with `OSError [Errno -3]`. Every Graphify run used
that same flag.

The read-only write boundary passed, established by three independent
observations: a deliberate `touch /src/WRITE_PROBE` was refused with
`Read-only file system`; both working-directory mounts finished at
`work_bytes=0`; and both consumers' full state captures are byte-identical
before and after. One limit is stated plainly: no kernel-level syscall audit was
run, so this is a strong behavioral result, not a formal proof that no write was
attempted anywhere.

### RAG — 0 of 3 questions add material connectivity value

Ignore-rule limitation, recorded and not defeated: `.gitignore:11` contains the
unanchored rule `build/`, confirmed by
`git check-ignore -v src/graph/build/text_graph_builder.py`. Graphify honored it,
so the entire live first-party directory `src/graph/build/**` is absent from the
graph. The rule was not edited and `--no-gitignore` was not used.

**Q1 — `RAGService.query` mixed routing and document join: FAIL.**
Literal commands:

```text
graphify query "From RAGService.query how does mode mixed activate semantic and graph retrieval and where do the two document streams join before the API response"
graphify query "result_joiner joiner document join priority" --context call --budget 4000
graphify path "RAGService" "GraphRetriever"
```

The first returned 873 candidate nodes in 1.390 s and truncated to
73 at the default budget, warning that the answer might be among the 800 cut
nodes. Narrowing with `--context call --budget 4000` (1.170 s) returned 23
nodes still dominated by noise. `graphify path "RAGService" "GraphRetriever"`
(1.280 s) returned a true but uninformative 3-hop chain
`RAGService --references--> service --imports_from--> bootstrap.py --imports--> GraphRetriever`,
which is file-level import discovery.

Source-confirmed ground truth that Graphify never produced: mixed mode is gated
at `src/retrieval/query_runner.py:212` and `:226` (`mode in {"graph","mixed"}`)
and `:778`; the join is `result_joiner`/`joiner` selected at
`src/retrieval/core/pipeline_builder.py:288` and `:298`, with final document
priority `ranker > result_joiner > joiner > retriever` at
`src/retrieval/query_runner.py:962-968`.

Root cause: the join is dynamic, string-keyed Haystack wiring
(`pipeline.add_component("result_joiner", ...)`), which an AST symbol graph does
not model. Material false lead: `join_prefix()` at
`.devcontainer/hf-ai-sync.py:L171` ranked into both traversals purely on the
lexical token "join" and is unrelated to document joining. It was identified as
false and **not accepted**.

**Q2 — `src.create_index.main` injected lifecycle and success-gated push: FAIL
(after escalation).**

First attempt, literal command:

```text
graphify query "From create_index main how do injected dependencies select import versus chunk embed mode guarantee indexing and allow storage push only after success" --budget 4000
```

It ran 2.099 s, found 270 nodes, truncated to 151, and returned **zero edges**.

Because that looked like the same generic budget truncation that a larger budget
fixed for industrial-inspection, Q2 was re-attempted with the same escalation
path used there, rather than being scored on the first result. The graph was
rebuilt first and reproduced exactly (8 302 nodes, 17 739 edges, 18 770 292 B,
10.504 s versus the original 10.401 s). Literal escalation commands and results:

| Command | Elapsed | Edges |
| --- | --- | --- |
| `graphify query "<same question text>" --budget 30000` | 1.206 s | 553 |
| `graphify affected "main()" --depth 3` | 0.785 s | 0 |
| `graphify affected "import_embedded_chunks()" --depth 3` | 0.636 s | 0 |
| `graphify path "main()" "push_csv_to_hub.py"` | 1.189 s | 0 |

What escalation did produce, all source-confirmed: the injected-dependency
entrypoints imported at `src/create_index.py:19-24`
(`run_create_index_with_dependencies`, `run_index_pipeline_with_dependencies`,
`_load_chunks_from_jsonl`, `sync_from_storage_config`,
`push_from_storage_config`), matching the real call at `src/create_index.py:49`
with those functions passed as parameters at `:66-68`; plus two `indirect_call`
edges from `affected "import_embedded_chunks()"` —
`main()` at `src/create_index.py:L63` and `run_index_pipeline()` at
`src/corpus/indexing/pipeline_runner.py:L94`.

What it still missed — the decisive part of the question. The success gate is
`src/corpus/indexing/cli.py:212-218`: inside a `finally` block,
`if pipeline_succeeded and validated_cfg.storage.push_on_complete and
validated_cfg.storage.backend != "local"`, with the push itself at `:220`.
Graphify named the push helper but never reached the `pipeline_succeeded`
guard, and produced nothing about import-versus-chunk/embed mode selection.
`affected "main()"` failed outright with `No unique node match for main()` —
a real usability limit, since `main()` is defined in many modules and the tool
offers no way to disambiguate by file. `path` found no directed route.

**Scoring note, recorded because it is borderline.** The 553-edge result is
mostly module-level `imports` inventory from one file, which is close to the
file-and-symbol discovery that Step 7 scores as zero; the two `indirect_call`
edges are genuine connectivity. Judged against the question actually asked —
three behaviors, of which mode selection and success gating are unanswered —
this is scored **FAIL**. The overall decision does not depend on this call: had
Q2 been scored PASS, RAG would reach 1/3, still below the required 2/3, and the
cross-project override would still fail.

**Q3 — `TextGraphBuilder` ownership, identity, public shim: FAIL.**
Literal command:

```text
graphify query "Which module owns TextGraphBuilder and how do compatibility imports preserve object identity through the public shim" --budget 4000
```

It ran 1.189 s over 49 nodes. It located the
shim `src/graph/build_text_graph.py` and its docstring, but the only edges it
produced from that file were `imports sys` and `imports_from importlib`.

The owner cannot be reached for two independent reasons, both confirmed in
source. The shim is:

```python
"""Temporary compatibility alias for moved graph build owner."""

import sys
from importlib import import_module

_owner_module = import_module("src.graph.build.build_text_graph")
sys.modules[__name__] = _owner_module
```

First, the owner `src/graph/build/**` is gitignored and absent from the graph.
Second, the link is a dynamic `import_module("...")` string and the identity
guarantee is the `sys.modules[__name__] = _owner_module` rebinding — neither is
a static import edge. Even with the ignore rule removed, an AST import graph
would not represent this relationship.

**RAG result: 0/3.** Below the required 2/3. No false relationship was accepted.

### industrial-inspection — 2 of 3 questions add material connectivity value

At the default budget all three questions returned **zero edges** with heavy
truncation (550, 525, and 537 candidates cut to about 125 each). Raising to
`--budget 30000` changed the outcome materially, producing 257 and 264 edges.
The default budget is therefore the binding limitation for this repository, not
the extractor.

Literal commands for the three questions (each also run at `--budget 4000`
first, then escalated to `--budget 30000`):

```text
graphify query "How do CLI benchmark and Gradio requests converge on AgentInspectionRuntime and when is a submitted verdict trusted versus replaced by heuristic fallback" --budget 4000
graphify query "How do MVTec masks become stable cc_n identities and flow through manifests benchmark cases grounding comparison and aggregate metrics" --budget 30000
graphify query "Which evidence stays raw becomes selected overlap cluster is count-only NMS deduplicated and drives verdicts overlays or benchmark grounding hit" --budget 30000
graphify path "AgentInspectionRuntime" "_run_heuristic_fallback()"
graphify affected "AgentInspectionRuntime" --depth 3
graphify affected "_select_highest_overlap_cluster()" --depth 3
```

**Q1 — runtime convergence and verdict authority: PASS.**
`graphify path "AgentInspectionRuntime" "_run_heuristic_fallback()"` (0.643 s)
returned a 2-hop chain naming the mediating method:
`AgentInspectionRuntime --method--> ._resolve_verdict() --calls--> _run_heuristic_fallback()`.
`graphify affected "AgentInspectionRuntime" --depth 3` (0.559 s) returned the
convergence set.

All accepted relationships confirmed in source:

- `src/industrial_inspection/app/runtime.py:21,31` — `build_inspection_runtime()`
  returns `AgentInspectionRuntime(cfg)`, the single shared builder.
- `src/industrial_inspection/cli/infer.py:166`,
  `src/industrial_inspection/cli/gradio.py:39`, and
  `src/industrial_inspection/eval/benchmark_runner.py:36`
  (`BenchmarkRunner.from_config`) each call that builder — the three converging
  entrypoints.
- `src/industrial_inspection/agent/inspection_runtime.py:341-380` —
  `_resolve_verdict` falls back at `:355` (agent error), `:359` (no verdict),
  `:363` (below `agent_confidence_threshold`), `:368` (counting task with
  missing or mismatched tool count), and `:372` (non-counting task that used the
  count tool); the submitted verdict is trusted only at `:374-376`.

Value beyond `rg`: the traversal named `_resolve_verdict` as the mediating
member and enumerated the three entrypoints in one call. Noise cost was high —
roughly 70 % of the `affected` output is test callers.

**Q2 — MVTec masks to `cc_n` identity through to aggregate metrics: FAIL.**
`--budget 30000` (0.704 s) produced 264 edges, but they are predominantly
`contains` file-to-symbol inventory plus test edges. The decisive step was
missed: the `cc_n` identity is constructed as an f-string at
`src/industrial_inspection/grounding/falcon_client.py:238-239`
(`f"q{query_index}_pred{prediction_index}_cc_{component_index}"`). The literal
token `cc_n` does not occur anywhere in the repository. Graphify surfaced
`grounding/types.py` and a mask-splitting test but never the construction site,
because an identity built inside a format string is invisible to an AST symbol
graph. The manifest to benchmark-case to grounding to metrics chain was not
produced as connected edges.

**Q3 — raw versus selected versus count-deduplicated evidence: PASS.**
`graphify query "..." --budget 30000` (0.722 s, 257 edges) and
`graphify affected "_select_highest_overlap_cluster()" --depth 3` (0.526 s)
produced three distinct, source-confirmed evidence paths:

- Count-only NMS dedup: `build_count_tool() --calls--> nms_dedup()` at
  `src/industrial_inspection/agent/tools.py:145`, confirmed in source, with
  `nms_dedup --calls--> compute_iou()` at
  `src/industrial_inspection/agent/dedup.py:31`. Confirmed that dedup is scoped
  to the count tool.
- Selected overlap cluster: `aggregate_grounding_results() --calls-->
  _select_highest_overlap_cluster()` at
  `src/industrial_inspection/grounding/aggregation.py:108` (definition at
  `:138`), reached from `inspection_runtime.py` `.run()`/`._run_locked()`.
- Benchmark grounding-hit: `compute_grounding_hit()` at
  `src/industrial_inspection/eval/region_matching.py:13` calling
  `_load_ground_truth_region_masks` `:39`, `_build_predicted_region_mask` `:50`,
  and `_compute_mask_iou` `:58`, consumed by `.run_case()` at
  `src/industrial_inspection/eval/benchmark_runner.py:123`.

Every relationship above was verified against the cited paths and lines. No
false relationship was accepted for this project.

**industrial-inspection result: 2/3.** Meets its own threshold.

### Cross-project override ledger

| Mandatory condition | RAG | industrial-inspection |
| --- | --- | --- |
| `>= 2/3` questions add material source-confirmed connectivity | **FAIL (0/3)** | PASS (2/3) |
| Zero accepted material false relationships | PASS | PASS |
| Cold extraction `<= 180 s` | PASS (10.400 s) | PASS (2.785 s) |
| Every measured query `<= 10 s` | PASS (max 2.099 s) | PASS (max 0.722 s) |
| Raw output `<= 50 MiB` | PASS (17.90 MiB) | PASS (3.46 MiB) |
| Network denial | PASS (positive control: probe blocked) | PASS (same image and flag) |
| Read-only write boundary | PASS (positive control: write to `/src` refused; `work_bytes=0`; consumer state byte-identical) | PASS (same controls) |
| Ignored/sensitive/generated/mutable-state paths absent | PASS | PASS |
| Initial and final consumer state identical | PASS | PASS |

The override required **both** projects to pass independently. RAG fails the
value condition, so the override fails. Per Step 7, the final Phase 0 decision
remains **NO-GO** and Phases A-F stop.

### What the supplement adds beyond the bootstrap result

The bootstrap-only test scored 1/3; RAG scored 0/3 and industrial-inspection
2/3. The spread is explained by repository shape rather than by tool defect:

- Graphify performs acceptably where relationships are static call and import
  edges between named symbols (industrial-inspection Q1 and Q3).
- It fails where connectivity is expressed dynamically — string-keyed pipeline
  wiring, `import_module` shims, `sys.modules` rebinding, or identities built in
  f-strings (RAG Q1 and Q3, industrial-inspection Q2). Both bootstrap consumers
  under test rely on those idioms in exactly the places a structural question
  targets.
- The default `--budget 2000` truncates aggressively enough to return zero edges
  on mid-sized graphs. Useful output required a 15x budget increase, which
  raises the per-question context cost the routing contract was meant to reduce.

### Final consumer status and cleanup

Both consumers were recaptured after all runs using the same command set. The
initial and final captures are byte-identical by `diff`, covering branch, HEAD,
`git status --short`, staged and unstaged diff names, untracked files, nested
`.claude` branch/HEAD/status, and the SHA-256 of every pre-existing dirty file.

| Consumer | Branch / HEAD unchanged | Dirty files unchanged | Nested `.claude` |
| --- | --- | --- | --- |
| `/home/ghisso/work/RAG` | `gliner2-graph-improvements` / `b48613f480ad87a3fa5e76975d37bc9ce5139fec` | 6 files, all hashes identical | `ai-state` / `9015859053a1cd0ec060125669b1e39b810ed9d3`, clean |
| `/home/ghisso/work/git_projects/industrial-inspection` | `2026-07-21_haystack-3-agent-refactor_implementation` / `28378951c91c08abdb136f549ab6136e6919b7d6` | 2 files, all hashes identical | `ai-state` / `efdb0af25dfd32b7fc434d68e624751db687d742`, clean |

Cleanup happened in two rounds, because review findings required re-running part
of the experiment after the first cleanup.

Round one removed `/tmp/graphify-step7-run` (all extraction output, caches,
logs, and state captures), plus the two paths left by the blocked attempt,
`/tmp/graphify-step7-cache.pJalTD` and `/tmp/graphify-step7-tools.lX35JD`, which
contained only uv metadata, and the disposable image `graphify-gate:0.9.35`.

Round two was created to satisfy the review findings on Q2 escalation and
boundary controls: the image was rebuilt from the same Dockerfile (identical
digest) and `/tmp/graphify-step7-fix` held the re-extraction and probe output.
Both were removed again at closeout, and the consumers were re-captured a third
time — branch, HEAD, status, diffs, nested `.claude`, and every dirty-file
SHA-256 still match the pre-flight table exactly.

All removals used exact paths, never a broad glob. Pre-existing `/tmp` paths
from earlier phases (`/tmp/graphify-plan-uv-cache`, `/tmp/graphify_plan_uv_cache`,
`/tmp/graphify-plan-amend-uv-cache`) were not created by this step, were
verified still present after both rounds, and were left untouched.
