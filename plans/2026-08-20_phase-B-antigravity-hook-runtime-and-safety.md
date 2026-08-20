---
name: 2026-08-20_phase-B-antigravity-hook-runtime-and-safety
type: small-plan
parent_plan: google-antigravity-provider-integration
phase_index: 1
status: complete
closeout_session_log: .claude/session_logs/2026-08-21_antigravity-phase-b.md
---

# Phase B: Antigravity hook runtime and safety

## Scope

Add native Antigravity hook configuration and one provider normalization boundary that reuses the bootstrap's existing protection and lifecycle logic.

Keep this phase separate because failures in provider hook normalization can bypass hard security boundaries.

Hard requirements:

- protected mutations are denied before execution;
- dangerous Git operations remain protected;
- hook stdout is valid Antigravity protocol JSON only;
- diagnostics go to stderr/log files;
- existing canonical protection policy is reused, not copied;
- lifecycle events are used only for semantics that are safe for the actual observed Antigravity cadence.

Do not implement installer ownership in this phase.

## Approved execution note

The hook design has already been reviewed.

Do not re-plan general provider architecture in this phase.

## Verified documented facts

Current Google hook documentation already defines:

- `.agents/hooks.json`;
- `PreToolUse`;
- `PostToolUse`;
- `PreInvocation`;
- `PostInvocation`;
- `Stop`;
- camelCase/common hook fields;
- `toolCall.name`;
- `toolCall.args`;
- `PreToolUse.decision = "deny"` as a hard pre-execution block;
- `run_command.CommandLine`;
- file mutation `TargetFile`;
- `PreInvocation.invocationNum` as the 0-indexed model invocation sequence number;
- `Stop.terminationReason`;
- `Stop.fullyIdle`;
- `Stop.decision = "continue"` to re-enter execution;
- common `modelName`.

Do not spend implementation time rediscovering these definitions.

Native probing is only for:

- event ordering/cadence in this workflow;
- whether one user turn produces multiple `PreInvocation` events;
- `conversationId` stability for the intended initialization scope;
- interaction with subagent invocations;
- when `Stop` appears relative to background tasks;
- whether a proposed lifecycle mapping causes repeated work or loops.

## Design

### One normalization boundary

Prefer one provider bridge at the existing shared hook boundary.

The bridge:

1. reads Antigravity JSON from stdin;
2. validates the required event/tool shape;
3. normalizes Antigravity fields to the canonical shape consumed by existing guard scripts;
4. invokes existing policy/guard logic;
5. short-circuits on deny;
6. translates the decision back to Antigravity JSON;
7. writes diagnostics only to stderr or existing error logs.

Do not let each protection script parse Antigravity independently.

If shell JSON handling would be fragile, add one small Python-standard-library adapter under the existing shared hook scripts. Policy decisions stay in canonical existing scripts.

### Required PreToolUse normalization

At minimum:

`run_command`:

```text
toolCall.args.CommandLine
toolCall.args.Cwd
```

File mutation:

```text
write_to_file -> TargetFile
replace_file_content -> TargetFile
multi_replace_file_content -> TargetFile
```

Add another mutation tool only when its current official payload is verified.

Unknown/ambiguous write-capable payloads must fail safely according to the existing bootstrap protection posture.

### PostToolUse

Use only for existing lifecycle behavior that genuinely matches post-tool semantics.

Do not use `PostToolUse` for durable AI-state publication.

### PreInvocation

`invocationNum` definition is already documented.

If using `PreInvocation` for initialization:

- prove through a disposable native probe how often it fires in one normal user turn;
- make initialization idempotent per conversation/workspace;
- do not pull/checkpoint state on every model reasoning invocation.

### Stop

Google documents `fullyIdle`, `terminationReason`, and continuation behavior.

If using Stop for best-effort closeout:

- only act when the native cadence proves it is safe;
- do not create a `continue` loop;
- do not describe Stop as durable session close;
- preserve existing Git-hook and explicit state-sync durability.

### No fake UserPromptSubmit mapping

Do not present `PreInvocation` as a direct semantic replacement for Claude/Codex `UserPromptSubmit`.

If no exact Antigravity event exists, record that difference.

## Expected files

Resolve exact current paths from post-Phase-A checkout.

Expected surfaces:

```text
scripts/generate_targets.py
scripts/validate_targets.py
shared/hooks/scripts/*
tests/test_hook_gates.py
tests/test_lifecycle_hooks.py
```

One new Antigravity adapter/bridge file is allowed if needed.

Generated:

```text
dist/multi-agent/.agents/hooks.json
```

Do not hand-edit generated files.

## Steps

- [ ] Rebase/update from Phase A commit and run focused baseline hook tests.
- [ ] Create a temporary diagnostic hook in a disposable workspace.
- [ ] Probe event order/cadence for:
  - simple prompt;
  - multiple tool calls;
  - one custom subagent invocation;
  - normal stop;
  - background task if relevant.
- [ ] Record only non-sensitive event metadata needed for design.
- [ ] Remove diagnostic hook/logs after evidence is recorded.
- [ ] Render `.agents/hooks.json`.
- [ ] Add one Antigravity normalization boundary.
- [ ] Reuse current protected-file/Git guard logic.
- [ ] Implement `PreToolUse` allow/deny translation.
- [ ] Add `PostToolUse` only for a real matching canonical purpose.
- [ ] Add `PreInvocation` initialization only if cadence proves it safe/idempotent.
- [ ] Add `Stop` behavior only if cadence proves no loop/repeated-closeout problem.
- [ ] Keep durable Git-hook/state-sync paths unchanged.
- [ ] Add protocol/adversarial tests.
- [ ] Generate and inspect all targets.
- [ ] Run one consolidated security-heavy review.
- [ ] Close with one phase commit.

## Required tests

Cover at least:

### Protocol

- valid Antigravity JSON input;
- JSON-only stdout;
- stderr diagnostic separation;
- malformed JSON;
- missing required fields;
- unknown event/tool.

### Hard deny

- protected file write denied;
- normal file write allowed;
- dangerous Git command denied;
- normal read-only Git command allowed;
- malformed/ambiguous mutation request fails safely.

### Tool normalization

- `run_command.CommandLine`;
- `run_command.Cwd`;
- `write_to_file.TargetFile`;
- `replace_file_content.TargetFile`;
- `multi_replace_file_content.TargetFile`.

### Lifecycle

When implemented:

- initialization does not repeat on every invocation;
- subagent invocation does not corrupt main conversation state;
- Stop does not loop;
- Stop with active background work does not claim full idle closeout;
- existing Git-hook durability remains unchanged.

### Regression

- existing Claude/Codex/Copilot hook tests still pass;
- generated non-Antigravity provider hook files stay unchanged except for intentional shared changes.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/test_hook_gates.py -q --tb=short
uv run pytest tests/test_lifecycle_hooks.py -q --tb=short
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
```

Run any shell-specific checks already configured by the repository.

## Acceptance criteria

- [ ] `.agents/hooks.json` is source-generated.
- [ ] One Antigravity normalization boundary exists.
- [ ] Existing protection policy is reused rather than copied.
- [ ] `PreToolUse` hard-denies protected mutations before execution.
- [ ] Dangerous Git operations remain hard-denied.
- [ ] Allowed operations still pass.
- [ ] Protocol stdout remains valid JSON.
- [ ] Diagnostics do not pollute stdout.
- [ ] Malformed/ambiguous mutation payloads fail safely.
- [ ] Documented hook fields are not needlessly re-probed.
- [ ] Native cadence evidence supports any implemented `PreInvocation`/`Stop` lifecycle mapping.
- [ ] No fake `UserPromptSubmit` equivalence is claimed.
- [ ] Existing durable state-sync mechanisms remain authoritative.
- [ ] Existing provider hook tests pass.
- [ ] Full phase verification passes.
- [ ] One phase commit is created.

## References

- https://antigravity.google/docs/hooks
- https://github.com/Ghisso/github_copilot_bootstrap/blob/dev/shared/policies/workflow.instructions.md
- https://github.com/Ghisso/github_copilot_bootstrap/tree/dev/tests
