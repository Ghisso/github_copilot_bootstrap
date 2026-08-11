---
name: 2026-08-11_phase-F-context-mode-local-indexing-and-cache-boundary
type: small-plan
parent_plan: state-sync-recovery-and-plan-cancellation
phase_index: 6
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-11_phase-F-context-mode-local-indexing-and-cache-boundary

## Scope

Keep Context Mode hooks and Model Context Protocol (MCP) tools available through
one repository-owned dispatcher and one absolute project-local
`CONTEXT_MODE_DIR`. Insert a deliberately small public-stdio filter between MCP
clients and pinned Context Mode 1.0.169. The filter exposes only guarded
`ctx_index`, `ctx_search`, `ctx_stats`, and `ctx_doctor`; all other Context Mode
tools stay hidden and rejected through the end of this big plan.

The audited version applies configured `Read(...)` deny rules to `ctx_index`,
including resolved/canonical and per-file directory checks, but does not apply
the project-containment guard used by `ctx_execute_file`. The repository filter
therefore owns containment and bounded-input validation for `ctx_index` only.
It must not import private Context Mode modules, patch installed code, execute
blocked capabilities, or become a general MCP gateway.

Preserve the frozen partial work that isolates `.claude/.cache/`, rejects unsafe
storage overrides, protects cache bytes during installer refresh, and removes
tracked cache state before checkpoint and after both reconciliation shapes.
Direct reads, `rg`, and Semble remain normal retrieval routes and fallbacks, not
replacements for the four advertised Context Mode capabilities. Graphify stays
closed and out of scope.

## Approved Capability Contract

| Capability | Result through generated MCP | Boundary |
|---|---|---|
| `ctx_index` | Advertised and callable | Filter validates content/file/directory input; upstream 1.0.169 still applies `Read` deny rules. |
| `ctx_search` | Advertised and callable | Searches only the fresh/audited project cache selected by the dispatcher. |
| `ctx_stats` | Advertised and callable | Read-only statistics for the selected project cache/session. |
| `ctx_doctor` | Advertised and callable | Diagnostics only; must not upgrade or rewrite configuration. |
| `ctx_execute`, `ctx_execute_file`, `ctx_batch_execute`, `ctx_fetch_and_index`, `ctx_upgrade`, `ctx_purge`, `ctx_insight` | Removed from `tools/list`; direct `tools/call` is rejected locally | The request is never forwarded upstream. |

The allowlist is exact and closed. A new upstream tool is unavailable until a
later approved plan audits and adds it.

## `ctx_index` Validation Contract

- Require exactly one of `content` or `path`.
- Content-only indexing is allowed and does not perform a filesystem read.
- Resolve relative paths against the canonical repository root exported by the
  dispatcher. Absolute, traversal, and canonical symlink targets must remain
  inside that root.
- A file path must resolve to an existing non-symlink regular file. Rely on the
  pinned upstream file-open/fstat and `Read`-deny checks as defense in depth.
- A directory root must resolve canonically inside the repository. Reject
  `followSymlinks: true` and `respectGitignore: false`; accept only caller bounds
  at or below upstream's audited defaults (`maxDepth <= 5`, `maxFiles <= 200`).
- Directory indexing must retain upstream per-file `Read` deny evaluation and
  must always exclude `.git`, `.claude/.cache`, `node_modules`, `dist`, `build`,
  `.next`, `coverage`, `.venv`, and `__pycache__`, even if caller options try to
  weaken exclusions.
- If directory containment or option-merging cannot be proved without materially
  expanding the filter, ship guarded regular-file/content indexing first,
  reject all directories with an actionable temporary-limitation message, and
  record that limitation in README and closeout evidence. Do not weaken the
  boundary to preserve directory support.

Read-deny and repository containment are separate gates. Passing one never
implies passing the other.

## Version and Cache Provenance Contract

- Pin `context-mode@1.0.169` in the devcontainer install, documented npm install,
  dispatcher `npx` fallback, generated/runtime validation, and capability tests.
- Use only public stdio MCP initialization and messages. The filter must reject
  or expose no tools when the upstream `serverInfo.version` is not exactly
  `1.0.169`.
- Do not use private `_registeredTools`, deep imports, or package-layout
  assumptions. Node's standard library is sufficient because Context Mode
  already requires Node 22.5+.
- Hooks and MCP must receive the same canonical repository identity and
  `CONTEXT_MODE_DIR` from the dispatcher.
- MCP search may use only a fresh guarded cache namespace created after this
  filter is installed, or an existing namespace whose local provenance matches
  the canonical repository, exact Context Mode version, and filter contract.
  Do not migrate or search an unmarked legacy/remote-restored content database.
- Provenance is local-only and must not be satisfiable by data restored from
  `ai-state`. On missing/mismatch, preserve old derived bytes separately or
  ignore them and initialize an empty guarded namespace; never silently trust
  or publish them.

The dispatcher owns storage/version/provenance setup. The MCP filter remains
limited to public stdio forwarding, `tools/list`, `tools/call`, and
`ctx_index` validation.

## Frozen Partial-Diff Disposition

| Surface | Disposition |
|---|---|
| Dispatcher storage canonicalization, hook mapping, self-check, and override tests | **KEEP**, then add `server` mode and shared hook/MCP environment. |
| State-sync `.cache/` ignore/untracking, post-reconcile cleanup, hostile two-clone tests | **KEEP AND REVERIFY**; do not restore cache to versioned state. |
| Installer/runtime ownership preservation of `.cache/` | **KEEP**, subject to fresh/audited MCP cache provenance above. |
| Protected Claude `Read` deny validation | **KEEP** as a distinct upstream indexing gate. |
| Context Mode removal from `shared/mcp/servers.json`, generated agents, prompts, onboarding, validators, and docs | **REPLACE** with dispatcher-backed filtered MCP and exact four-tool guidance. |
| Direct-read/`rg`/Semble fallback wording | **RETAIN**, but remove claims that they replace Context Mode. |
| Target parity validation using a stale loop variable after the server loop | **FIX** so every named server is compared in its own iteration and a focused regression can fail per server. |

Do not revert unrelated edits. The coder must adapt the current frozen hunks in
place and touch only the files named below.

## Ownership, Steps, and Verification

Every code-writing step requires `.claude/skills/ponytail/SKILL.md` in `full`
mode. Implementation also requires `.claude/skills/code-style/SKILL.md` and
`.claude/skills/testing-patterns/SKILL.md`; verification uses
`.claude/skills/run-tests/SKILL.md`; documentation uses
`.claude/skills/documentation/SKILL.md`; closeout uses
`.claude/skills/learn/SKILL.md` and `.claude/skills/commit/SKILL.md`.

| Step | Owner | Target files | Required Skills | Review Profiles | Focused verification |
|---|---|---|---|---|---|
| 1. Restore dispatcher-backed MCP and pin upstream. `server` mode must configure the same cache/project environment as hooks, start the public filter, and fail clearly when its pinned runtime is unavailable; hook events remain fail-open. | `coder` | `shared/hooks/scripts/context-mode-dispatch.sh`, `shared/devcontainer/Dockerfile`, `tests/test_context_mode_dispatch.py` | `ponytail` full, `code-style`, `testing-patterns` | `code`, `architecture`, `security`, `tests`, `ponytail` | Dispatcher tests prove hook/server environment parity, pinned binary/npx commands, version mismatch failure, and no network in self-check. |
| 2. Add the minimal public-stdio capability filter. Pass unrelated JSON-RPC messages byte-for-byte where possible; track only request IDs needed to filter `tools/list`; validate/reject `tools/call`; never log raw arguments. | `coder` | `shared/hooks/scripts/context-mode-mcp-filter.mjs` (create), `tests/test_context_mode_mcp_filter.py` (create) | `ponytail` full, `code-style`, `testing-patterns` | `code`, `architecture`, `security`, `tests`, `ponytail` | Fake-upstream tests cover fragmented/multiple messages, list filtering, direct-call rejection, upstream exit/error, exact version, and allowed-call passthrough. |
| 3. Implement the `ctx_index` trust boundary and fresh/audited cache selection. Prefer bounded directories under the contract above; take the documented regular-file-first fallback if directory proof expands the filter materially. | `coder` | filter/dispatcher files above and their focused tests | `ponytail` full, `code-style`, `testing-patterns` | `code`, `architecture`, `security`, `tests`, `ponytail` | Test content, ordinary file, directory bounds, absolute/traversal/root-symlink/child-symlink escape, option weakening, derived/vendor exclusion, deny-rule propagation, legacy/hostile cache provenance, and two-clone isolation. |
| 4. Restore generated MCP and agent capability routing. All three targets start Context Mode through dispatcher `server`; Claude agents receive the applicable MCP tool access; Codex inherits the server; Copilot capability claims stay limited to native evidence. Fix the MCP parity loop. | `coder` | `shared/mcp/servers.json`, `scripts/generate_targets.py`, `scripts/validate_targets.py`, affected `shared/agents/*/prompt.md`, `shared/skills/onboard/SKILL.md`, focused generator/validator tests | `ponytail` full, `code-style`, `testing-patterns` | `code`, `architecture`, `security`, `tests`, `ponytail` | Generated GitHub/Claude/Codex configs have identical dispatcher route; each MCP server parity assertion fails independently; advertised Context Mode tools equal the four-tool allowlist. |
| 5. Preserve and reverify cache/state/runtime hardening. Reconcile the existing partial tests with the guarded namespace; keep user ignore entries, pre-checkpoint and post-reconcile untracking, installer preservation, protected deny validation, and runtime diagnostics. | `coder` | `shared/hooks/scripts/state-sync.sh`, `scripts/runtime_ownership.py`, `scripts/check_runtime.py`, `tests/test_state_sync.py`, `tests/test_install_bootstrap.py` | `ponytail` full, `code-style`, `testing-patterns` | `code`, `architecture`, `security`, `tests`, `ponytail` | Focused state-sync, installer, runtime, hostile-cache, provenance, and exact-version tests. |
| 6. Reconcile policy and documentation after code review. Hooks must advertise only the four tools returned by filtered `tools/list`; suppress or replace upstream guidance that names blocked tools. Describe fallbacks, directory limitation if taken, cache provenance, and the exact pin. | `documenter` | `shared/policies/tool-routing.instructions.md`, `README.md`, existing relevant sections of `docs/architecture.md`, `docs/runtime-checks.md`, `docs/smoke-tests.md` | `documentation` | `documentation` | Exact searches find no hook/prompt/docs claim for blocked tools, unfiltered MCP, unpinned installs, or trusted legacy cache. |
| 7. Run the canonical verify/review/document/score/learn/session-log/commit loop only after Steps 1-6 pass. | `verifier`, `reviewer`, `documenter`, orchestrator | Final Phase F diff | `run-tests`, `documentation`, `learn`, `commit` | all profiles below | Full commands and gates below. |

## Review Profiles

- `.claude/review-profiles/code.md`
- `.claude/review-profiles/architecture.md`
- `.claude/review-profiles/security.md`
- `.claude/review-profiles/tests.md`
- `.claude/review-profiles/ponytail.md`
- `.claude/review-profiles/documentation.md`

## Acceptance Tests

- Public MCP initialize succeeds only with Context Mode `1.0.169`.
- `tools/list` returns exactly `ctx_index`, `ctx_search`, `ctx_stats`, and
  `ctx_doctor`; direct calls to each blocked/currently unknown tool are rejected
  without reaching the fake or real upstream.
- Hook guidance and every generated agent prompt name only advertised tools.
- Content and an ordinary in-repository regular file can be indexed and searched
  from the fresh guarded cache; a configured protected file is denied upstream.
- Absolute outside paths, `..`, root symlinks, and directory symlink escapes are
  rejected before upstream. Directory callers cannot enable symlink following,
  disable Git ignore, exceed bounds, or include derived/vendor paths.
- Hooks and MCP receive identical canonical `CONTEXT_MODE_DIR` and repository
  identity. Relative, tracked/protected in-repository, traversal, and symlinked
  storage overrides fall back; approved-subtree and external absolute overrides
  obey provenance checks.
- A hostile remote cache in unrelated/common-history two-clone reconciliation
  cannot become searchable, tracked, or republished. A valid local guarded cache
  remains local across installer refresh.
- Generated GitHub Copilot, Claude, and Codex MCP configurations route Context
  Mode through the dispatcher. Semble and Context7 remain unchanged.
- Missing optional Context Mode still warns and falls back to direct reads,
  `rg`, and Semble without disabling those normal routes.

## Verification

```bash
uv sync
uv run pytest tests/test_context_mode_dispatch.py tests/test_context_mode_mcp_filter.py tests/test_state_sync.py tests/test_install_bootstrap.py -q --tb=short
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/check_runtime.py
bash .claude/hooks/scripts/context-mode-dispatch.sh --self-check
bash .claude/hooks/scripts/state-sync.sh status
```

Run an integration probe through the generated dispatcher using public MCP
initialize, `tools/list`, guarded `ctx_index`, `ctx_search`, and direct blocked
`tools/call`. The probe must use a temporary ordinary fixture, never a protected
or user file, and must assert exact version/tool names and cache provenance.

Generator determinism:

```bash
uv run python scripts/generate_targets.py --all
cp -a dist /tmp/dist-gen-a
uv run python scripts/generate_targets.py --all
diff -r /tmp/dist-gen-a dist
rm -rf /tmp/dist-gen-a
```

## Stop Conditions

- Stop before dogfood refresh, documentation, score, or commit if the public
  filter cannot prove exact upstream version, exact tool allowlisting, rejected
  calls never reaching upstream, or `ctx_index` containment.
- Stop and take the regular-file/content-only fallback if safe directory
  indexing requires a general filesystem policy engine, private Context Mode
  imports, or substantially broader MCP mediation.
- Stop if hooks or generated prompts advertise any filtered tool.
- Stop if an unmarked, mismatched, or remote-restored cache can be searched.
- Stop if Docker, documented npm, `npx`, generated runtime, and integration
  probes do not all bind to exactly `1.0.169`.
- Stop publication if `.cache/**` remains tracked after either successful
  reconciliation shape.
- Do not restore unfiltered Context Mode MCP, patch installed code, reopen
  Graphify, or broaden Phase F into a general gateway/dependency project.

## Risks and Fallback Paths

| Concern | Risk | Alternative | Recommendation |
|---|---|---|---|
| The filter grows into a general MCP proxy. | HIGH | Forward/transform more methods or schemas. | **CHANGE:** intercept only `tools/list` and `tools/call`; pass all else through. |
| Directory traversal requires duplicating upstream's walker. | HIGH | Reimplement walking/deny rules. | **CHANGE:** rely on pinned upstream with stricter caller options; otherwise reject directories temporarily. |
| A legacy/remote cache contains data indexed before filtering. | HIGH | Trust `.cache/` because Git ignores it. | **CHANGE:** require local fresh/audited provenance before search. |
| Private tool-disable APIs are fewer lines. | HIGH | Deep-import `_registeredTools`. | **CHANGE:** use public stdio despite the small extra module; private layout is not a contract. |
| Exact pin prevents automatic security updates. | MEDIUM | Continue unpinned npm/npx. | **ACCEPT RISK:** deterministic audited behavior wins through this big plan; later upgrades require capability/security tests. |
| Copilot custom-agent MCP tool naming remains unproved. | MEDIUM | Guess names in allowlists. | **INVESTIGATE:** advertise only evidence-backed access; workspace MCP stays configured and native acceptance is recorded separately. |

## Done Criteria

- [ ] Hooks and filtered MCP use one dispatcher, repository identity, and guarded local cache.
- [ ] Exactly four Context Mode tools are advertised; every other tool is locally rejected.
- [ ] Guarded `ctx_index` passes containment, bounds, provenance, and upstream `Read` deny tests.
- [ ] Context Mode is exactly `1.0.169` across install, fallback, runtime, and tests.
- [ ] Cache cannot be restored as trusted state, tracked, published, or used as lifecycle evidence.
- [ ] All generated MCP routes are coherent; per-server parity validation is correct.
- [ ] Direct reads, `rg`, Semble, and Context7 behavior remain available and accurately documented.
- [ ] Full verification, two-pass review, documentation, findings, score, learn, session log, and atomic Phase F commit gates pass.

The next action after approval is coder Step 1 against the frozen partial diff.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
