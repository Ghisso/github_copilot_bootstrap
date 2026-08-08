---
name: 2026-08-04_phase-F-hook-routing-efficiency
type: small-plan
parent_plan: bootstrap-guidance-runtime-modernization
phase_index: 6
status: complete
closeout_session_log: .claude/session_logs/2026-08-08_bootstrap-guidance-runtime-modernization-phase-F.md
---

# Small Plan: 2026-08-04_phase-F-hook-routing-efficiency

## Scope

Reduce irrelevant hook process fan-out with target-native matchers while
preserving fail-closed decisions, code-mode coverage, lifecycle ordering, and
all historical command-parsing regressions. The phase also fixes the observed
false positive where read-only `sed`/`wc` inspection of `.codex/config.toml`
was classified as a protected-file edit.

## Ownership

- `coder`: hook grouping/matchers and any shared dispatcher refactor.
- `verifier`: event-matrix, parser, lifecycle, and timing tests.
- `reviewer`: `code`, `architecture`, `security`, `performance`, `tests`,
  `ponytail`.
- `documenter`: hook event and troubleshooting docs.

## Required Skills

- `ponytail` (`full`), `testing-patterns`, `debug-investigator`, `run-tests`,
  `documentation`, `ponytail-review`.

## Steps

- [x] Build an event/tool coverage matrix from current Claude/Codex hook docs
  and the repository's actual scripts before changing matchers.
- [x] Make protected-file classification operate on the mutation target of
  each command segment. Permit proven read-only commands such as `rg`, `wc`,
  `cat`, and `sed` without `-i`, while continuing to deny in-place edits,
  output redirection to protected paths, write-capable apply-patch calls, and
  ambiguous/unparseable payloads.
- [x] Route Git/lifecycle guards only to Bash-like commands; route file
  protection to Bash and native edit tools (`apply_patch`/Edit/Write aliases);
  keep observability wildcard behavior separate and best-effort.
- [x] Test the documented code-mode matcher/alias contract structurally so a
  nested `apply_patch` reaches the same `PreToolUse` protection path. Reserve
  native JavaScript-nested execution proof for Phase I and do not claim it from
  synthetic payloads alone.
- [x] If multiple guards require order or short-circuiting, add one fail-closed
  wrapper with a documented JSON/exit aggregation contract. Do not combine
  scripts merely to reduce file count.
- [x] Preserve the single sequential `claude-stop.sh`/`codex-stop.sh` wrappers,
  network-free checkpoint fallbacks, JSON-only Codex stdout, silent Claude
  stdout, and post-commit durable publication path.
- [x] Re-run every compound-command, global-Git-option, nested `.claude`, secret
  path, merge, rebase/cherry-pick, and malformed-input adversarial fixture.
- [x] Add deterministic assertions for both runtime command handlers and child
  guard invocations. Mutation-handler budgets are Read/MCP `0`, native edit
  `1`, Bash `1` ordered wrapper, Stop `1`, and SessionEnd `1`; report optional
  observability separately. The Bash wrapper may invoke at most five ordered
  guards and must short-circuit on the first denial or malformed child result.
  Do not count incidental OS descendants.

## Verification

```bash
uv run pytest tests/test_hook_gates.py tests/test_lifecycle_hooks.py tests/test_state_sync.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
```

## Acceptance Criteria

- Unrelated read/MCP calls do not launch mutation-only guards.
- Every destructive or protected mutation remains blocked on both targets.
- Stop/session durability semantics are byte-for-byte and behaviorally preserved.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
