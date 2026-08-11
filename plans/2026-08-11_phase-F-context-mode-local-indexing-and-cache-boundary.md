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

Allow Context Mode to index non-protected project content locally and make the
storage boundary explicit.

The current bootstrap can lead an agent to interpret any "index" operation as
external disclosure. That is too broad for Context Mode. Its `ctx_index`
knowledge base is local SQLite/FTS5 state. The desired rule is:

- approved local Context Mode indexing of project content is allowed;
- protected paths remain denied;
- the index is derived cache, not canonical AI state;
- the cache stays local and never enters the nested `ai-state` history;
- this permission does not authorize repository upload to another service and
  does not change network-fetch policy.

Use `.claude/.cache/context-mode/` as the bootstrap's default project-local
Context Mode storage root. Route both the MCP server and Context Mode hooks
through the existing dispatcher so they cannot silently use different storage
roots.

This phase also extends existing deterministic checks for this behavior. It
does not create a general tool registry, telemetry system, evaluation harness,
or new retrieval integration.

## Current Upstream Contract To Preserve

The implementation depends on Context Mode behavior available in current
versions:

- `ctx_index` stores indexed content in a local SQLite/FTS5 knowledge base.
- `CONTEXT_MODE_DIR` selects an absolute writable storage root; indexed content
  lives below `<root>/content` and session/state data below `<root>/sessions`.
- Context Mode reads the project's Claude-format permission rules across
  supported platforms; deny rules win over allow rules.
- project-boundary containment remains enabled.
- `ctx_fetch_and_index` is a network-fetch operation and is not equivalent to
  indexing an existing local project file.

Do not weaken these assumptions in bootstrap policy. If implementation-time
inspection shows that the installed Context Mode version does not satisfy this
contract, stop this phase and report the mismatch instead of adding a workaround
that bypasses permissions.

## Ownership

- `coder`: `shared/hooks/scripts/context-mode-dispatch.sh`,
  `shared/hooks/scripts/state-sync.sh`,
  `shared/policies/tool-routing.instructions.md`,
  `shared/mcp/servers.json`, generated wiring support if required,
  `scripts/check_runtime.py`, `scripts/validate_targets.py`, and focused tests.
- `documenter`: the Context Mode section of `README.md` and any existing
  architecture/security paragraph that already owns this boundary. Do not
  create a second policy document when the routing policy is sufficient.
- `verifier`: focused launcher/cache tests plus full project verification and
  target determinism.
- `reviewer`: the profiles listed below.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` in `full` mode before implementation,
  because this is control-plane/high-risk work.
- `.claude/skills/code-style/SKILL.md` and
  `.claude/skills/testing-patterns/SKILL.md` for implementation.
- `.claude/skills/documentation/SKILL.md` for user-facing documentation.
- `.claude/skills/run-tests/SKILL.md` for verification.
- `.claude/skills/learn/SKILL.md` and `.claude/skills/commit/SKILL.md` at
  closeout.

Human-facing prose follows the already-shipped
`shared/policies/agent-reporting.instructions.md` clarity rules. Do not create a
new ASD-STE100 policy and do not claim formal ASD-STE100 compliance.

## Review Profiles

- `.claude/review-profiles/code.md`
- `.claude/review-profiles/architecture.md`
- `.claude/review-profiles/security.md`
- `.claude/review-profiles/tests.md`
- `.claude/review-profiles/ponytail.md`
- `.claude/review-profiles/documentation.md`

The full review set is required because this phase changes MCP launch behavior,
security semantics, and nested-state hygiene. This is consistent with the
current calibrated review policy; it does not make Ponytail universal again.

## Design Decisions

### Local indexing is not external disclosure

Update the routing/security wording so agents do not reject `ctx_index` merely
because it creates an index.

The permitted case is narrow:

```text
project file
  -> Context Mode ctx_index
  -> local project-scoped SQLite/FTS5 cache
```

The permission does not extend to:

```text
project file
  -> remote vector database
  -> remote embedding/index API
  -> unknown external indexer
```

Those remain external disclosure and require whatever approval/policy already
applies to sending repository content outside the workspace.

### Protected paths still win

Keep the generated Claude-format deny rules authoritative, including at least
the existing:

- `Read(./.env)`
- `Read(./.env.*)`
- `Read(./secrets/**)`
- `Read(./config/credentials.json)`

Do not add an allow rule that overrides or weakens them.

If focused review finds equivalent sensitive patterns already protected
elsewhere, reuse that policy rather than inventing a second secret list.

### Project-local cache is derived state

Default:

```text
<repo>/.claude/.cache/context-mode/
```

The dispatcher must resolve the repository root and provide an **absolute**
`CONTEXT_MODE_DIR` to Context Mode. If a caller deliberately supplies a valid
absolute `CONTEXT_MODE_DIR`, preserve that explicit override unless doing so
would violate an existing repository security rule.

`.claude/.cache/` is not canonical state. It must not be committed, pushed,
used as lifecycle evidence, or restored as bootstrap-owned state.

Add the ignore rule through the existing nested-state ignore mechanism. Existing
nested repositories must gain the rule idempotently without losing user-added
ignore entries.

### One launcher for MCP and hooks

Extend `shared/hooks/scripts/context-mode-dispatch.sh`; do not add a second
launcher.

The dispatcher needs two paths:

1. existing hook dispatch:
   `context-mode hook <target> <event>`;
2. MCP server mode:
   launch `context-mode` as the MCP server.

Both paths must initialize the same storage environment first.

Update `shared/mcp/servers.json` so all generated targets start Context Mode
through that dispatcher. Preserve fail-open behavior for hook events. MCP server
startup may report a clear unavailable-tool error rather than pretending the
server started.

Do not change Semble or Context7 wiring in this phase.

## Steps

- [ ] `shared/policies/tool-routing.instructions.md` (modify): classify
      Context Mode `ctx_index` of non-protected in-project content as approved
      local processing. State explicitly that this is not permission to upload
      repository content to a remote index/service. Keep direct reads, `rg`,
      Semble, Context Mode, and Context7 responsibilities distinct.
- [ ] In the same policy, state that protected/read-denied files must not be
      indexed and that deny rules take priority over local-index permission.
      Keep `ctx_fetch_and_index` in the network/external-fetch category.
- [ ] `shared/hooks/scripts/context-mode-dispatch.sh` (modify): resolve the
      repository root, create/select the project-local storage root, export an
      absolute `CONTEXT_MODE_DIR`, and use that setup for all existing hook
      events.
- [ ] Add a `server` mode to the same dispatcher that starts the Context Mode
      MCP server with the identical `CONTEXT_MODE_DIR`. Keep the existing target
      mapping for hooks unchanged.
- [ ] Extend `--self-check` to report, without network access:
      - resolved Context Mode binary/fallback state;
      - effective absolute storage root;
      - whether the root is writable or can be created;
      - whether `.claude/.cache/` is ignored by the nested repository when that
        repository exists.
      A missing optional Context Mode binary remains a warning, not a bootstrap
      failure.
- [ ] `shared/mcp/servers.json` (modify): route the `context-mode` MCP entry
      through the dispatcher `server` mode. Do not change the other MCP servers.
- [ ] `shared/hooks/scripts/state-sync.sh` (modify): add `.cache/` to the nested
      local-only ignore contract and ensure existing nested repositories gain
      the entry idempotently before `git add -A`. Preserve existing user-added
      ignore lines and all current state-sync semantics from Phases A/B.
- [ ] Verify the generated `.claude/settings.json` still contains the protected
      read-deny rules used by Context Mode across targets. Add only missing
      deterministic validation; do not broaden this phase into a general secrets
      policy rewrite.
- [ ] `scripts/check_runtime.py` (modify): extend the existing Context Mode
      runtime check to validate the dispatcher/self-check and report the
      effective local-cache configuration. Do not create a new `doctor`
      command.
- [ ] `scripts/validate_targets.py` (modify): assert generated MCP targets route
      Context Mode through the canonical dispatcher and that generated Claude
      permission denies remain present.
- [ ] Add focused tests for dispatcher storage resolution and nested-cache ignore
      behavior. Prefer existing test modules; create a new focused test file
      only if no current module owns the behavior.
- [ ] `README.md` (modify): document that Context Mode indexing is local,
      project-scoped derived cache by default; show the cache path; state that
      the cache is not synchronized; state that protected read-deny rules still
      apply. Keep the explanation short.
- [ ] Regenerate all targets and refresh the dogfood install only after focused
      tests pass.
- [ ] Run the full verification set and a final cache-sentinel check.

## Test Scenarios

- [ ] `context-mode-dispatch.sh --self-check` reports an absolute
      `<repo>/.claude/.cache/context-mode` default when no override is supplied.
- [ ] An explicit valid absolute `CONTEXT_MODE_DIR` override is preserved, if
      the implementation chooses to support overrides as specified.
- [ ] Hook dispatch receives the same `CONTEXT_MODE_DIR` as MCP server mode.
- [ ] Generated Copilot, Claude, and Codex MCP configurations start Context Mode
      through the dispatcher rather than directly with a separate storage root.
- [ ] Create
      `.claude/.cache/context-mode/test-sentinel.txt`, run the nested-state
      checkpoint path, and verify the sentinel is not staged or committed.
- [ ] Start from an already-initialized nested `.claude/.git` whose `.gitignore`
      lacks `.cache/`; the next supported setup/checkpoint path adds the ignore
      entry without deleting unrelated user-added ignore lines.
- [ ] Existing `.env`, `.env.*`, `secrets/**`, and
      `config/credentials.json` read-deny rules remain in generated Claude
      settings.
- [ ] The tool-routing policy allows local `ctx_index` for an ordinary project
      Markdown/source file but explicitly refuses protected paths and does not
      authorize remote indexing.
- [ ] Existing Context Mode hook fallback remains fail-open when the optional
      binary is unavailable.
- [ ] Semble and Context7 generated MCP wiring is byte-for-byte unchanged except
      for formatting that the generator already owns.

## Verification

```bash
uv sync
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

Cache-sentinel proof:

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

## Risks

- **Derived cache accidentally enters `ai-state`.** `state-sync.sh` uses
  `git add -A`, so an ignore mistake would persist SQLite/index data. Mitigation:
  add the nested ignore idempotently and prove it with the sentinel scenario.
- **Hooks and MCP server use different indexes.** Mitigation: one dispatcher
  owns storage initialization for both launch paths.
- **"Local indexing allowed" is read as "all files allowed".** Mitigation:
  routing text explicitly says protected deny rules win; generated deny rules
  are regression-tested.
- **A shell-launch change breaks one target.** Mitigation: validate all generated
  MCP configurations and keep the change inside the existing Bash-based
  bootstrap runtime rather than inventing target-specific launchers.
- **Context Mode upstream behavior changes.** Mitigation: this phase validates
  the storage/security contract it relies on. If the installed version does not
  support that contract, stop and report rather than bypassing it. A broader
  dependency-pinning policy remains outside this phase.
- **Scope expands into a generic security/tooling redesign.** Mitigation: no new
  tools, no capability registry, no telemetry, no remote-index integration, and
  no general secret-policy rewrite.

## Acceptance Criteria

- [ ] Agents are explicitly allowed to use Context Mode `ctx_index` for
      non-protected files inside the project.
- [ ] The policy clearly distinguishes local Context Mode indexing from sending
      repository content to an external service.
- [ ] Protected read-deny rules remain authoritative and are covered by
      generated-target validation.
- [ ] Hooks and the MCP server use one project-local Context Mode storage root
      by default.
- [ ] The default storage root is
      `.claude/.cache/context-mode/` and is passed to Context Mode as an absolute
      path.
- [ ] `.claude/.cache/` cannot be staged or committed by the nested-state
      checkpoint path, including in an existing installation upgraded from a
      version without that ignore entry.
- [ ] `scripts/check_runtime.py` and dispatcher `--self-check` expose enough
      information to diagnose the local-cache wiring without a new diagnostics
      subsystem.
- [ ] Semble and Context7 behavior is unchanged.
- [ ] No Graphify integration is introduced.
- [ ] Full verification and generator determinism pass.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
