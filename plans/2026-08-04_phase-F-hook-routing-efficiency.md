---
name: 2026-08-04_phase-F-hook-routing-efficiency
type: small-plan
parent_plan: bootstrap-guidance-runtime-modernization
phase_index: 6
status: in-progress
closeout_session_log:
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

- [ ] Build an event/tool coverage matrix from current Claude/Codex hook docs
  and the repository's actual scripts before changing matchers.
- [ ] Make protected-file classification operate on the mutation target of
  each command segment. Permit proven read-only commands such as `rg`, `wc`,
  `cat`, and `sed` without `-i`, while continuing to deny in-place edits,
  output redirection to protected paths, write-capable apply-patch calls, and
  ambiguous/unparseable payloads.
- [ ] Route Git/lifecycle guards only to Bash-like commands; route file
  protection to Bash and native edit tools (`apply_patch`/Edit/Write aliases);
  keep observability wildcard behavior separate and best-effort.
- [ ] Test nested code-mode tool calls so `apply_patch` cannot bypass
  `PreToolUse` decisions.
- [ ] If multiple guards require order or short-circuiting, add one fail-closed
  wrapper with a documented JSON/exit aggregation contract. Do not combine
  scripts merely to reduce file count.
- [ ] Preserve the single sequential `claude-stop.sh`/`codex-stop.sh` wrappers,
  network-free checkpoint fallbacks, JSON-only Codex stdout, silent Claude
  stdout, and post-commit durable publication path.
- [ ] Re-run every compound-command, global-Git-option, nested `.claude`, secret
  path, merge, rebase/cherry-pick, and malformed-input adversarial fixture.
- [ ] Add a deterministic subprocess-count assertion for representative Read,
  MCP, edit, Bash, Stop, and SessionEnd events.

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

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
