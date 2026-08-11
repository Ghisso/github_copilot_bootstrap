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

Keep Context Mode's optional lifecycle hooks and derived cache local, but remove
Context Mode from every generated Model Context Protocol (MCP) configuration.
This is the minimum enforceable response to the confirmed upstream mismatch:
installed Context Mode 1.0.169 applies project-boundary containment to
`ctx_execute_file`, but its `ctx_index` path branch applies deny rules and then
passes absolute paths directly to indexing. The bootstrap must not expose that
uncontained tool and must not claim local repository indexing is approved.

Direct file reads, `rg`, and Semble remain the supported retrieval routes.
Context Mode hook events remain optional, fail open when the binary is missing,
and share an absolute project-local cache under
`.claude/.cache/context-mode/`. That cache is derived state: it must not remain
tracked after checkpoint or reconciliation, must not be published on
`ai-state`, and must not be used as lifecycle evidence.

This phase does **not** build an MCP proxy. Local evidence proves that a shell
launcher cannot inspect MCP request parameters, the repository has no existing
proxy or per-tool filter, and the installed package exposes all tools together.
A proxy would require a new JSON-RPC mediation subsystem whose framing,
lifecycles, error responses, and three-target behavior are outside this bounded
phase. Re-enabling Context Mode MCP requires a separate approved plan and
evidence that containment is enforced at the `ctx_index` request boundary.

## Confirmed Evidence and Decisions

- Installed package evidence:
  `/home/ghisso/.local/nodejs/node-v24.15.0-linux-x64/lib/node_modules/context-mode/package.json`
  reports version `1.0.169`.
- `src/server.ts` calls `checkProjectBoundary(...)` for `ctx_execute_file`, but
  the `ctx_index` handler calls only `checkFilePathDenyPolicy(...)` before
  `resolveProjectPath(path)`; `resolveProjectPath` returns an absolute input
  unchanged.
- `shared/mcp/servers.json` supports only process command/arguments and the
  dispatcher only starts a stdio child. Neither can validate `tools/call`
  parameters.
- No repository-owned MCP proxy or proved individual Context Mode tool filter
  exists. Therefore removing the whole Context Mode MCP server is the only
  locally proved containment action that can land in Phase F.
- Lifecycle hooks remain because they do not grant an agent the uncontained
  `ctx_index` MCP call. They continue to be optional observability/continuity
  helpers and make no safety decision.
- An explicit absolute `CONTEXT_MODE_DIR` may remain supported outside the
  repository. Inside the repository, only the canonical
  `.claude/.cache/context-mode/` subtree is valid. Relative, tracked,
  protected, symlink-escaping, or other in-repository overrides fall back to
  the default with a warning.
- The phase remains `in-progress`; the confirmed stop condition changes the
  deliverable instead of fabricating a successful local-indexing claim.

## Partial-Edit Disposition

| Current partial surface | Disposition | Required final contract |
|---|---|---|
| `shared/hooks/scripts/context-mode-dispatch.sh` cache initialization, hook target mapping, self-check, and unsafe-override filter | **KEEP AND NARROW** | Keep hook dispatch only. Remove `server` mode. Canonicalize the repository and override; accept an in-repository override only within `.claude/.cache/context-mode/`. Preserve hook fail-open behavior. |
| `shared/hooks/scripts/state-sync.sh` `.cache/` ignore, pre-checkpoint untracking, and post-reconcile cleanup | **KEEP AND VERIFY** | Preserve user ignore entries, add `.cache/` once, remove cache paths from the nested index before every `git add -A`, and repeat cleanup after every successful reconciliation path before publication. |
| `tests/test_state_sync.py` cache tests | **KEEP AND EXTEND** | Add remote-reconciliation coverage for both applicable reconciliation outcomes so remote tracked cache cannot remain tracked or be republished. |
| `tests/test_context_mode_dispatch.py` | **KEEP AND REWRITE** | Retain hook/default/self-check/fail-open coverage; remove server-sharing and MCP-start tests; add tracked, protected, traversal, symlink, relative, approved-subtree, and external-absolute override cases. |
| `shared/mcp/servers.json` dispatcher `server` route | **REPLACE** | Remove the `context-mode` MCP entry entirely; do not restore the prior direct `context-mode` command. |
| `shared/policies/tool-routing.instructions.md` local `ctx_index` permission | **REVERT AND REPLACE** | State that path-backed Context Mode indexing and Context Mode MCP routing are disabled until request-boundary containment is proved. Route repository retrieval to direct reads, `rg`, and Semble. |
| `scripts/validate_targets.py` Context Mode route/parity assertions | **REWRITE** | Assert Context Mode MCP absence in GitHub Copilot, Claude Code, and Codex output. Retain only cache/hook/protected-rule checks that prove the reduced contract. |
| `scripts/check_runtime.py` dispatcher self-check | **KEEP AND ADJUST** | Validate the hook launcher's default cache and ignore state; do not require or start an MCP server. |
| `README.md` text claiming local `ctx_index` is allowed | **REVERT AND REPLACE** | Document hook-only Context Mode use, the cache boundary, MCP disablement, and direct/`rg`/Semble fallback. |

Do not revert unrelated user or agent edits. The coder must first compare the
listed partial hunks with the current worktree and edit only the Phase F scope.

## Ownership

- `coder`: control-plane sources, generator/validator updates, and focused
  regression tests listed below.
- `verifier`: focused tests, full suite, generation, target validation,
  frontmatter validation, runtime checks, and cache sentinel proof.
- `reviewer`: two sequential passes using every profile listed below.
- `documenter`: reconcile README and existing architecture/runtime/smoke-test
  paragraphs after review. Do not add a new policy document.

## Required Skills

Every code-writing step requires `.claude/skills/ponytail/SKILL.md` in `full`
mode. The coder also reads `.claude/skills/code-style/SKILL.md` and
`.claude/skills/testing-patterns/SKILL.md`; the verifier reads
`.claude/skills/run-tests/SKILL.md`; the documenter reads
`.claude/skills/documentation/SKILL.md`; closeout uses
`.claude/skills/learn/SKILL.md` and `.claude/skills/commit/SKILL.md`.

## Review Profiles

- `.claude/review-profiles/code.md`
- `.claude/review-profiles/architecture.md`
- `.claude/review-profiles/security.md`
- `.claude/review-profiles/tests.md`
- `.claude/review-profiles/ponytail.md`
- `.claude/review-profiles/documentation.md`

The complete control-plane review set is mandatory. The Ponytail pass must
specifically challenge any new proxy, protocol parser, dependency, second
launcher, or generalized cache abstraction.

## Steps

| Step | Owner | Target files | Required Skills | Review Profiles | Verification |
|---|---|---|---|---|---|
| 1. Lock the hook-only cache boundary. Remove dispatcher `server` mode; keep one hook path, absolute default storage, and fail-open missing-tool behavior. Canonically reject unsafe overrides as defined above. | `coder` | `shared/hooks/scripts/context-mode-dispatch.sh`, `tests/test_context_mode_dispatch.py` | `ponytail` full, `code-style`, `testing-patterns` | `code`, `architecture`, `security`, `tests`, `ponytail` | `uv run pytest tests/test_context_mode_dispatch.py -q --tb=short` |
| 2. Make cache exclusion survive upgrades and reconciliation. Keep `.cache/` idempotent without overwriting user ignores; untrack before checkpoint and after every successful reconciliation before any publish. Do not alter Phase A/B rebase ownership or warn-never-fail semantics. | `coder` | `shared/hooks/scripts/state-sync.sh`, `tests/test_state_sync.py` | `ponytail` full, `code-style`, `testing-patterns` | `code`, `architecture`, `security`, `tests`, `ponytail` | `uv run pytest tests/test_state_sync.py -q --tb=short` |
| 3. Remove the unsafe MCP capability from the source of truth and all generated contracts. Delete only Context Mode MCP wiring; leave Semble and Context7 behavior unchanged. Remove dead Context Mode MCP allowlist expectations and ensure agents fall back consistently. | `coder` | `shared/mcp/servers.json`, `scripts/generate_targets.py`, `scripts/validate_targets.py`, affected `shared/agents/*/prompt.md`, `shared/skills/onboard/SKILL.md`, focused validator tests | `ponytail` full, `code-style`, `testing-patterns` | `code`, `architecture`, `security`, `tests`, `ponytail` | Regenerate; run focused generator/validator tests; inspect all three generated MCP configs for Context Mode absence and Semble/Context7 parity. |
| 4. Replace the untrue indexing permission with the reduced routing contract and keep runtime diagnostics aligned with hook-only operation. | `coder` | `shared/policies/tool-routing.instructions.md`, `scripts/check_runtime.py`, focused runtime/target tests | `ponytail` full, `code-style`, `testing-patterns` | `code`, `architecture`, `security`, `tests`, `ponytail` | Focused runtime tests plus `uv run python scripts/check_runtime.py`; no command may start a Context Mode MCP server. |
| 5. Reconcile user-facing documentation after code review converges. State why MCP indexing is disabled, what hooks still do, where cache lives, and which retrieval fallbacks remain. | `documenter` | `README.md`, existing relevant paragraphs in `docs/architecture.md`, `docs/runtime-checks.md`, and `docs/smoke-tests.md` | `documentation` | `documentation` | Link/path checks plus exact searches for stale claims that Context Mode MCP or `ctx_index` is available. |
| 6. Run full verification, two-pass review, documentation, persisted findings/score, learn, session log, and atomic Phase F commit. | `verifier`, then `reviewer`, `documenter`, orchestrator | Final Phase F diff only | `run-tests`, `documentation`, `learn`, `commit` | all profiles above | Commands below; `counts.critical == 0`, `counts.major == 0` before push/PR, score `>= 90`. |

## Test Scenarios

- No generated GitHub Copilot, Claude Code, or Codex MCP configuration contains
  a `context-mode` server; Semble and Context7 remain unchanged.
- Generated agent tool allowlists and prompts do not claim access to a missing
  Context Mode MCP server. `onboard` does not instruct agents to call
  `ctx_index`.
- Hook dispatch exports the canonical absolute
  `<repo>/.claude/.cache/context-mode` default and retains the existing target
  mappings and fail-open behavior.
- Relative overrides fall back. In-repository tracked/protected paths,
  `..` traversal, and symlinks resolving to those paths fall back. The approved
  cache subtree and a canonical external absolute override are preserved.
- Existing nested repositories retain user-added `.gitignore` entries and gain
  exactly one `.cache/` rule.
- A locally tracked legacy cache is removed from the nested index without
  deleting its local derived bytes before reconciliation.
- A remote branch containing tracked `.cache/**` is reconciled through every
  applicable success path; before publication, no `.cache/**` path remains in
  `git ls-files`, and the next remote state does not contain it.
- Dispatcher `--self-check` is network-free and reports cache path,
  writability/creatability, and nested ignore state without starting MCP.
- Protected Claude-format read-deny rules remain generated. This defense in
  depth does not substitute for MCP removal.

## Verification

```bash
uv sync
uv run pytest tests/test_context_mode_dispatch.py tests/test_state_sync.py -q --tb=short
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

Generated MCP absence and retained-server proof:

```bash
rg -n 'context-mode' dist/multi-agent/.vscode/mcp.json dist/multi-agent/.mcp.json dist/multi-agent/.codex/config.toml
# expected: no Context Mode MCP entry
rg -n 'semble|context7' dist/multi-agent/.vscode/mcp.json dist/multi-agent/.mcp.json dist/multi-agent/.codex/config.toml
```

Cache sentinel proof:

```bash
mkdir -p .claude/.cache/context-mode
printf 'derived-cache-sentinel\n' > .claude/.cache/context-mode/test-sentinel.txt
git -C .claude status --porcelain -- .cache/context-mode
# expected: no output
rm -f .claude/.cache/context-mode/test-sentinel.txt
```

Generator determinism:

```bash
uv run python scripts/generate_targets.py --all
cp -a dist /tmp/dist-gen-a
uv run python scripts/generate_targets.py --all
diff -r /tmp/dist-gen-a dist
rm -rf /tmp/dist-gen-a
```

## Stop Conditions

- If any generated target still exposes `ctx_index` or a Context Mode MCP
  server, stop before dogfood refresh, documentation, score, or commit.
- If removing the server breaks required (not optional) bootstrap behavior,
  stop and return to planning. Do not restore direct Context Mode routing as a
  workaround.
- If the cache cannot be excluded after a successful remote reconciliation,
  stop before publication. Do not accept a warning-only result.
- If safe completion appears to require parsing or proxying MCP JSON-RPC,
  adding a dependency, or patching installed Context Mode code, stop Phase F
  and propose a separate full plan. Do not expand this phase in place.
- A future upstream version is not sufficient evidence by version number
  alone. Re-enablement requires an executable regression proving absolute,
  traversal, and symlink-out `ctx_index(path=...)` requests are denied while an
  ordinary in-project file is accepted on every supported target route.

## Risks and Fallback Paths

| Risk | Mitigation / fallback |
|---|---|
| Removing Context Mode MCP reduces long-output retrieval. | Keep direct reads, `rg`, and Semble; Context Mode is already optional by repository policy. |
| Hooks inject guidance for tools that are no longer present. | Update prompts/routing and focused target validation; if upstream hook output still claims MCP availability, disable only that misleading hook event and re-review. |
| Remote reconciliation reintroduces tracked cache. | Repeat untracking after reconciliation and block publication on cleanup failure. |
| Override canonicalization misses a symlink or traversal case. | Resolve the repository and deepest existing ancestor physically; cover lexical and canonical escapes with regression tests. |
| A proxy is proposed as a quick preservation mechanism. | Defer it. A future plan must own protocol compatibility, request/response correlation, shutdown, backpressure, error semantics, and three-target acceptance. |

## Done Criteria

- [ ] Context Mode MCP and `ctx_index` are absent from every generated target.
- [ ] No policy, agent prompt, skill, or documentation claims that repository
      `ctx_index` is approved or available.
- [ ] Optional Context Mode hooks use one safe project-local cache by default
      and retain fail-open missing-tool behavior.
- [ ] Unsafe in-repository storage overrides cannot select tracked or protected
      state; approved cache-subtree and external absolute overrides are tested.
- [ ] `.claude/.cache/` cannot remain tracked after checkpoint or successful
      reconciliation and cannot be republished on `ai-state`.
- [ ] Semble and Context7 behavior is unchanged.
- [ ] Full verification, generator determinism, two-pass review, documentation,
      findings, score, learn, session log, and commit gates pass.

## Devil's Advocate Report

| Concern | Risk | Alternative | Recommendation |
|---|---|---|---|
| Disabling the whole MCP server removes safe Context Mode tools too. | MEDIUM | Add a per-tool JSON-RPC proxy. | **CHANGE:** accept temporary capability loss; the proxy is not locally proved and is larger than Phase F. |
| Policy-only prohibition could be ignored by an agent. | HIGH | Keep MCP wired and rely on instructions. | **CHANGE:** remove the server from generated configs so enforcement does not depend on agent compliance. |
| Upstream already has a containment helper, so a wrapper may look trivial. | HIGH | Patch/import upstream internals or rewrite the handler. | **INVESTIGATE LATER:** local evidence shows the helper is not called by `ctx_index`; patching installed code is not a durable bootstrap contract. |
| Post-reconcile cleanup may miss a control-flow branch. | HIGH | Rely on pre-checkpoint ignore/untracking only. | **CHANGE:** test and guard every successful reconciliation exit before publish. |
| Preserving arbitrary in-repository absolute overrides recreates the cache leak. | HIGH | Trust explicit caller intent. | **CHANGE:** allow only the canonical approved cache subtree inside the repository. |

No unresolved HIGH-risk question remains for Phase F. The next action after
plan approval is coder implementation of Step 1 against the current partial
diff, without reverting unrelated edits.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
