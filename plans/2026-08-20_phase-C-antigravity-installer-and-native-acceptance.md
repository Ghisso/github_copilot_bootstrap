---
name: 2026-08-20_phase-C-antigravity-installer-and-native-acceptance
type: small-plan
parent_plan: google-antigravity-provider-integration
phase_index: 2
status: in-progress
closeout_session_log:
---

# Phase C: Antigravity installer ownership and native acceptance

## Scope

Complete the provider integration in one phase by combining:

- installer/root-adapter ownership;
- refresh/prune/restore semantics;
- target manifest;
- complete semantic validation;
- dogfood install;
- disposable-consumer native `agy` acceptance;
- final documentation and closeout.

The old installer and validation/native-acceptance phases are merged because native acceptance is the proof that the installed ownership work is correct. A separate verification-only small plan would add a full lifecycle/commit cycle without a meaningful implementation boundary.

## Approved execution note

Do not create a new planning/decomposition phase.

Fix concrete defects found by native acceptance in this phase and re-run the relevant verification.

## Current ownership source

Use the current live files after Phase B:

```text
scripts/install_bootstrap.py
scripts/runtime_ownership.py
```

The old plan's "source freshness" uncertainty is obsolete. `scripts/generate_targets.py` currently imports runtime ownership from `runtime_ownership.py`, and the installer uses the same ownership layer.

Still inspect current local code before editing because preceding plans may have changed it.

## Design decisions

### `.agents/` is shared

Do not own/delete `.agents/` as a directory.

Bootstrap ownership must be file/path granular.

Bootstrap-owned examples:

- known generated agent adapter files;
- known generated skill paths;
- `.agents/mcp_config.json`;
- `.agents/hooks.json`;
- native rule files only if Phase A actually generated them.

Preserve unrelated user content such as:

```text
.agents/skills/company-private/SKILL.md
.agents/agents/company-reviewer/agent.md
```

unless it collides with an exact bootstrap-owned path and existing safe collision policy says otherwise.

### `AGENTS.md` is shared between providers

Codex and Antigravity both use the provider-neutral root `AGENTS.md`.

Pruning rules must not say:

```text
no Codex => remove AGENTS.md
```

Root guidance can be removed only when no installed/retained provider needs it and the existing ownership rules permit removal.

No new provider-selection CLI is required. The `multi-agent` target continues to install all adapters.

### No global Antigravity mutation

Do not write:

```text
~/.gemini/*
```

for agents, MCP, hooks, permissions, rules, or settings.

All bootstrap provider state remains workspace-local.

### Native acceptance is required

Generated-file tests are not enough.

Use a disposable Git consumer repository and the installed Antigravity client.

Do not perform deny/destructive acceptance experiments in the bootstrap development repo.

### Model evidence

Do not ask the model what model it is and treat self-report as proof.

Prefer client-provided evidence such as hook `modelName`.

Acceptance proves:

- Flash-tier route;
- Pro-tier route;
- one Flash -> Pro escalation path.

Do not claim exact Gemini model identity unless native runtime evidence proves it.

### MCP acceptance

Two levels:

1. configuration/discovery must work;
2. runtime use should be proved for one available server and one specialist if practical.

Optional local MCP server absence follows existing fallback rules and does not fail the provider integration by itself.

## Expected files

Expected:

```text
scripts/install_bootstrap.py
scripts/runtime_ownership.py
targets/multi-agent/manifest.json
scripts/validate_targets.py
tests/*
README.md
```

Use existing installer/ownership test modules when practical.

Generated `dist/` is regenerated, not edited.

## Steps

### 1. Inspect current ownership model

Before changes, identify in live code:

- root adapter paths;
- restorable root paths;
- generated/owned path sets;
- stale-file cleanup;
- collision behavior;
- ignore block generation;
- bootstrap-root mirror/restore.

Use current code, not the old August 14 plan assumptions.

### 2. Add file-granular Antigravity ownership

Integrate generated `.agents/` paths.

Required behavior:

- fresh install copies bootstrap-owned Antigravity files;
- update refreshes owned files;
- stale owned files can be pruned;
- unrelated user `.agents/` files survive;
- collision with a user-owned file at an intended bootstrap path uses the repository's safe preservation/error policy;
- repeated install/update is deterministic.

### 3. Integrate restore/mirror

Include only bootstrap-owned Antigravity root/provider files in durable restore/mirror behavior.

Do not mirror unrelated user `.agents/` content into bootstrap-owned AI-state.

### 4. Update ignore handling

Add only required managed ignore entries.

Do not ignore an entire `.agents/` namespace if it would hide user-authored tracked customizations.

Repeated installer runs must keep managed ignore content deterministic.

### 5. Update target manifest

Add `google-antigravity` to provider-adapter metadata for the existing:

```text
multi-agent
```

target.

Keep manifest paths aligned with actual generated files.

Do not add a second target.

### 6. Add installer regression tests

Use temporary Git repositories.

Cover:

1. fresh empty consumer install;
2. repeated update;
3. generated file refresh;
4. stale bootstrap-owned Antigravity file removal;
5. unrelated tracked `.agents/` file preservation;
6. user collision at a bootstrap-owned path;
7. restore/mirror;
8. dogfood/self-refresh path;
9. existing provider/root adapter regression;
10. shared `AGENTS.md` ownership.

### 7. Complete semantic target validation

`validate_targets.py` must prove at least:

- expected `.agents/` files exist;
- exactly seven Antigravity custom-agent adapters exist;
- Luna/Sol are absent from `.agents/agents/`;
- agent frontmatter parses;
- model tiers are valid;
- Flash coder escalation metadata is correct;
- tool names are in the verified set;
- no guessed `todo`/`vscode` tool exists;
- specialist MCP inheritance/config mechanism is present;
- skill output matches canonical source intent;
- MCP JSON parses and server keys match canonical source;
- rule output matches the Phase A proved schema or no guessed rule output exists;
- hook JSON parses and required provider commands/events are present;
- manifest declares Antigravity;
- provider-neutral `AGENTS.md` exists;
- no stale obsolete Antigravity output remains.

Prefer semantic parsing over line snapshots.

### 8. Run complete repository verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
```

Regenerate twice and compare output for determinism.

### 9. Dogfood the target

Use the current supported self-install command from live installer help/code.

Confirm:

- generated provider files install;
- root guidance restore works;
- existing providers still work;
- no unexplained generated/install diff remains.

### 10. Create disposable native consumer

Create a temporary Git repository.

Install the generated `multi-agent` target.

Start `agy` from repo root.

Record:

- Antigravity CLI version;
- relevant provider configuration paths;
- no real secrets.

### 11. Verify root guidance

Use a read-only prompt.

Confirm Antigravity can identify:

- workflow lifecycle;
- canonical `.claude/` AI-state location;
- specialist role model;
- provider-specific `.agents/` surfaces.

Confirm root guidance keeps the completed user-facing simple-language contract and does not describe Codex-only behavior as Antigravity behavior.

### 12. Verify agent discovery/invocation

Use `/agents` and `invoke_subagent`.

Acceptance:

- orchestrator is selectable as the main agent;
- specialists do not need to be selectable main agents because `mainAgent: false`;
- specialists are invocable as subagents;
- Luna/Sol are not available as Antigravity roles;
- `antigravity_flash_coder` is available as a subagent;
- at least planner, Flash coder, Pro coder, verifier, and reviewer can complete a harmless read-only invocation;
- no invalid tool name causes a hang.

Do not require all hidden specialists to appear in the primary-agent picker.

### 13. Verify Flash/Pro tier routing

Cause harmless tool activity so hook metadata can expose client-side `modelName`.

Verify:

- orchestrator/planner/reviewer/canonical coder use Pro tier;
- Flash coder/verifier/documenter use Flash tier where invoked;
- runtime evidence is consistent with configured tier semantics.

Do not claim an exact backing Gemini version unless `modelName` or equivalent client evidence proves it.

### 14. Verify Flash -> Pro coder escalation

Use a controlled disposable task.

Preferred test:

- give `antigravity_flash_coder` a bounded-looking implementation packet with one deliberately unresolved interface/root-cause/ownership decision;
- confirm it returns the defined escalation handoff rather than inventing the decision;
- confirm orchestrator routes once to canonical `coder` Pro;
- confirm Pro receives original packet plus escalation evidence/current diff state;
- confirm no second automatic model escalation occurs.

Also prove an ordinary bounded implementation can stay on Flash without mandatory Pro escalation.

This is a routing smoke test, not a broad coding benchmark.

### 15. Verify skills

Use `/skills`.

Confirm representative generated skills are discovered.

Trigger at least one harmless skill use and confirm linked resources can be read.

Full skill-set parity remains structurally validated; do not manually invoke every skill.

### 16. Verify MCP, including specialist access

Use `/mcp` and confirm generated server entries.

If one optional local server is available:

- perform one harmless read-only MCP request from the top-level agent;
- perform one harmless read-only MCP request from a specialist with `inheritMcp`/the verified inheritance mechanism.

If no optional server can start, record the environment limitation and verify configuration/fallback rather than failing unrelated provider functionality.

### 17. Verify native hard deny

In the disposable consumer:

1. select a path protected by existing bootstrap policy;
2. ask Antigravity to write it;
3. confirm the file is unchanged;
4. confirm `PreToolUse` generated the deny;
5. then perform an allowed operation to prove hooks do not block everything.

Do not use real secrets.

### 18. Verify lifecycle behavior

Confirm:

- initialization does not run repeatedly on every model invocation;
- subagent use does not corrupt state;
- Stop behavior does not loop;
- any best-effort closeout matches Phase B evidence;
- durable Git-hook/state-sync behavior remains intact.

### 19. Final documentation

Update README/provider documentation with only proved behavior:

- Antigravity support in `multi-agent`;
- `.agents/` surfaces;
- six base roles plus Antigravity Flash coder;
- Flash -> Pro coding route;
- provider-neutral `AGENTS.md`;
- skills/MCP;
- hard-deny hooks;
- installer ownership/pruning;
- rule fallback if native rules were deferred;
- lifecycle semantic differences;
- optional MCP fallback.

Do not advertise:

- Teamwork Preview;
- `flash_lite`;
- exact Gemini model identity without runtime evidence;
- unsupported native rule metadata;
- a `todo` mapping that does not exist.

Because the documenter is expected to use the mandatory `humanize edit` self-check after the preceding writing plan, preserve that workflow here.

### 20. Final review, score, learn, closeout

Run one consolidated final reviewer invocation after implementation/documentation is complete.

Resolve blocking findings.

Persist final findings/quality score after final docs so the content hash reflects final state.

Run LEARN and complete session log.

Commit this phase once.

After all three phases are complete, mark the parent big plan complete and publish AI-state through the normal state-sync path.

## Native acceptance checklist

```text
[ ] root AGENTS.md loaded
[ ] orchestrator main-agent selection works
[ ] hidden specialists are invocable
[ ] Luna/Sol absent from Antigravity
[ ] antigravity_flash_coder available
[ ] Flash-tier specialist tool call completes
[ ] Pro-tier specialist tool call completes
[ ] Flash -> Pro escalation smoke test passes
[ ] bounded Flash task can complete without Pro
[ ] generated skills discovered
[ ] representative skill loads
[ ] generated MCP servers discovered
[ ] specialist MCP access works when optional server is available
[ ] PreToolUse hard-denies protected write
[ ] allowed operation still works
[ ] lifecycle hooks do not repeat/loop incorrectly
[ ] installer preserves user-owned .agents content
[ ] repeated install/update is deterministic
[ ] existing provider adapters still validate
[ ] dogfood install has no unexplained drift
```

## Acceptance criteria

- [ ] `multi-agent` manifest declares Antigravity.
- [ ] Fresh install produces expected bootstrap-owned `.agents/` files.
- [ ] Repeated refresh is deterministic.
- [ ] Stale bootstrap-owned Antigravity files can be pruned safely.
- [ ] Unrelated user `.agents/` files survive.
- [ ] Collision behavior is safe and explicit.
- [ ] Restore/mirror includes only bootstrap-owned Antigravity state.
- [ ] Shared `AGENTS.md` ownership handles both Codex and Antigravity.
- [ ] No user-global Antigravity configuration is modified.
- [ ] Complete semantic validation passes.
- [ ] Generated output is deterministic.
- [ ] Native Antigravity loads root guidance.
- [ ] Seven expected Antigravity roles are structurally present.
- [ ] Hidden specialists are invocable.
- [ ] Flash and Pro tier routing has client-provided evidence where available.
- [ ] Flash -> Pro coder escalation works exactly once.
- [ ] Ordinary bounded coding can remain Flash-only.
- [ ] Skills are discovered.
- [ ] MCP configuration is discovered.
- [ ] Specialist MCP access is proved when the optional environment permits it.
- [ ] Protected write is hard-denied before execution.
- [ ] Allowed operation works after deny.
- [ ] Lifecycle hooks do not create repeated initialization or Stop loops.
- [ ] Existing providers have no regression.
- [ ] Documentation matches observed behavior.
- [ ] Final repository checks pass.
- [ ] Final findings satisfy push/PR gates.
- [ ] Quality score >= 90.
- [ ] One phase commit is created.

## References

- https://github.com/Ghisso/github_copilot_bootstrap/blob/dev/scripts/install_bootstrap.py
- https://github.com/Ghisso/github_copilot_bootstrap/blob/dev/scripts/runtime_ownership.py
- https://github.com/Ghisso/github_copilot_bootstrap/blob/dev/scripts/validate_targets.py
- https://antigravity.google/docs/subagents
- https://antigravity.google/docs/hooks
- https://antigravity.google/docs/mcp
- https://antigravity.google/docs/cli/features
- https://deepmind.google/models/model-cards/gemini-3-7-flash/
