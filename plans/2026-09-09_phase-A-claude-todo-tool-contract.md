---
name: 2026-09-09_phase-A-claude-todo-tool-contract
type: small-plan
parent_plan: claude-todo-tool-contract
phase_index: 1
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-09-09_phase-A-claude-todo-tool-contract

## Scope

Stop the bootstrap from emitting the Claude tool name `TodoWrite`, which
current Claude Code runtimes do not enable, and stop the canonical instruction
text from naming it. Resolve two further suspect names in the same map —
`MultiEdit` and `Task` — against the live runtime and correct them where the
runtime does not provide them. Add validation that rejects any generated Claude
agent tool name outside a reviewed allowlist. Keep the abstract `todo`
capability and its meaning for GitHub Copilot, OpenAI Codex, and Google
Antigravity unchanged.

One phase is deliberate: the generator mapping, the instruction text, the new
validation, and the regenerated output form one contract. Delivering any part
separately leaves generated output contradicting canonical instructions, and
the new validation rejects the current generated output until the generator
change lands.

This is control-plane and generator work. Use the `code`, `architecture`,
`security`, `tests`, and `ponytail` review profiles. Preserve every other
runtime's tool mapping exactly.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` in `full` mode during implementation.
- `.claude/skills/testing-patterns/SKILL.md` for the focused regression tests.
- `.claude/skills/code-style/SKILL.md` for the changed Python.
- `.claude/skills/documentation/SKILL.md` for current documentation.
- `.claude/skills/commit/SKILL.md` only after all closeout gates pass.

## Primary Files

Modify:

- `scripts/generate_targets.py` — remove the `"todo"` entry from
  `CLAUDE_TOOL_MAP`, correct any other entry step 3a proves unavailable, and
  extend the comment above the maps.
- `shared/policies/workflow.instructions.md` — reword the two lines that name
  `TodoWrite` (currently lines 125 and 249).
- `scripts/validate_targets.py` — add the reviewed Claude tool allowlist and
  the subset check.
- `tests/test_validate_targets.py` — add the focused regression cases.
- `docs/target-mapping.md` and `README.md` only if inspection shows an existing
  statement about Claude task tracking or capability mappings becomes
  incomplete. Neither currently names `TodoWrite` or documents a
  capability-to-tool table, so treat both as conditional.

Regenerate `dist/multi-agent/**` with the generator; never edit it directly and
never copy it from `shared/`.

Do not modify: `shared/agents/*/agent.yaml`, `shared/agents/orchestrator/prompt.md`,
`COPILOT_TOOL_MAP`, `ANTIGRAVITY_TOOL_MAP`, the Codex capability prose, or the
`AGENT_CAPABILITIES` allowlist.

## Steps

- [ ] **1. Remove the Claude `todo` mapping.**
  - Owner: `coder`.
  - Modify `CLAUDE_TOOL_MAP` in `scripts/generate_targets.py`: delete the
    `"todo": ["TodoWrite"]` entry. Change nothing else in the map.
  - Extend the existing comment block above the maps — the one that already
    explains why `vscode` is Copilot-only and why the `mcp__` wildcards are
    required — with a short note recording why `todo` has no Claude tool: the
    runtime enables `TodoWrite` only when `CLAUDE_CODE_ENABLE_TASKS` is false,
    enables the four task tools otherwise, removes those four from background
    subagents regardless of the `tools:` field, and on Claude Code v2.1.233 and
    later omits all five on current model families unless
    `CLAUDE_CODE_ENABLE_TODO_TOOLS=1`. State that `render_claude_tools()` skips
    unmapped capabilities through its existing `.get(capability, [])` default,
    so no other generator change is needed.
  - Do not add a replacement tool name. Do not touch `render_claude_tools()`
    itself.
  - Confirm before finishing that `coder`, `orchestrator`, and `planner` each
    still emit a non-empty `tools:` line. A `tools:` field that resolves to
    nothing is a documented Claude Code spawn error.

- [ ] **2. Make the canonical instruction text runtime-neutral.**
  - Owner: `coder`.
  - Modify `shared/policies/workflow.instructions.md`.
  - Reword the FIX LOOP step (line 125) so it no longer names `TodoWrite`.
    Preserve the step's meaning exactly: on failed verification, review, or
    closeout, update task tracking, return to IMPLEMENT, and repeat until
    `verify phase` and `verify closeout` report PASS and the findings report has
    `counts.critical == 0`. Keep the severity-gate sentence that follows it
    byte-identical.
  - Reword the checklist line (line 249) so it refers to task tracking rather
    than a tool name.
  - Match the phrasing `shared/agents/orchestrator/prompt.md` already uses:
    the runtime's native task tracker when one is available, and the same
    checklist written as prose where it is not. Do not copy the prompt's full
    paragraph into the policy.
  - Preserve every exact command, path, identifier, and field name on both
    lines.
  - Search the canonical sources again after editing to confirm no remaining
    `TodoWrite` reference outside `dist/` and dated records under `plans/`.
    Dated design narratives under top-level `plans/` are historical and stay
    unchanged.

- [ ] **3a. Resolve the two suspect names against a live runtime.**
  - Owner: `coder`, with orchestrator confirmation before the allowlist is
    written.
  - `MultiEdit` (from `edit`) and `Task` (from `delegate`) are emitted today
    but may not resolve. Static inspection was inconclusive, so settle both
    empirically rather than by reasoning.
  - Determine, for each name, whether a Claude Code subagent granted it in
    `tools:` actually receives a usable tool. Prefer the runtime's own report
    of unmatched entries over inference: a `tools:` list whose entries fail to
    match is reported by the Agent tool, and an entry that resolves to nothing
    is silently dropped from the agent's tool set.
  - Record the evidence and the runtime version in the closeout log. Do not
    replace an unavailable live check with a synthetic pass; mark it dated
    `UNVERIFIED` and stop before changing a mapping on an unproven basis.
  - Correct `CLAUDE_TOOL_MAP` for every name the runtime does not provide:
    replace it with the documented equivalent where one exists — `Agent` for
    subagent spawning — and drop it where none does.
  - Keep each correction inside this phase. They are the same contract as the
    `todo` fix: one map, one validator, one regeneration.
  - If a correction changes which tools an agent receives in practice rather
    than only in name, say so plainly in the closeout log; a silently dropped
    `MultiEdit` means those agents have been editing through `Edit` and `Write`
    all along, while a silently dropped `Task` would mean the orchestrator
    could not delegate, which the observed behavior contradicts and which
    therefore needs explaining rather than assuming.

- [ ] **3. Add the reviewed Claude tool allowlist check.**
  - Owner: `coder`.
  - Modify `scripts/validate_targets.py`, mirroring the existing Antigravity
    precedent (`ANTIGRAVITY_ALLOWED_TOOLS` plus its "unknown native tools"
    check).
  - Define a module-level reviewed constant of permitted Claude tool names.
    Write it as an explicit literal set, not a set derived from
    `CLAUDE_TOOL_MAP`. A derived allowlist would accept whatever the map
    contains and would not have caught this bug; that is the whole point of the
    check.
  - Include only names confirmed present in the documented tool table:
    `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash`, `WebFetch`, `WebSearch`,
    and whichever of `Agent` or `Task` step 3a establishes as the resolving
    name for the `delegate` capability.
  - Do not add `MultiEdit` or `TodoWrite`. Both are names this check exists to
    reject.
  - Add the subset check inside the existing Claude agent frontmatter loop that
    already parses the `tools:` line for the Semble and Context Mode assertion.
    Reuse that parsed line rather than re-reading the file.
  - Treat entries beginning with `mcp__` as MCP server grants and exempt them
    from the built-in allowlist; the existing Semble and Context Mode check
    already covers them.
  - Report the offending names in the failure message, as the Antigravity check
    does, so the next occurrence is diagnosable from the message alone.
  - Add a short comment recording that `TodoWrite` is the name this check
    exists to reject and why.

- [ ] **4. Add focused regression coverage.**
  - Owner: `coder`.
  - Extend `tests/test_validate_targets.py`. Keep that module as the pytest
    entrypoint for this suite; a separate module risks `verify.py`'s pytest
    measurement reporting a false no-tests result instead of exercising the
    adversarial suite.
  - Assert that no generated Claude agent frontmatter contains `TodoWrite`.
    Mirror the existing Antigravity assertion style.
  - Assert that `render_claude_tools()` returns no tool for a capability list
    containing only `todo`, and that a realistic list such as the
    orchestrator's still returns its expected tools in order.
  - Assert that the three affected agents — `coder`, `orchestrator`,
    `planner` — still emit a non-empty `tools:` line, so a future mapping
    removal cannot silently produce a zero-tool agent.
  - Add an adversarial case: inject an unsupported tool name into a generated
    Claude agent's `tools:` line in a temporary copy and assert the new
    validation reports it. Pair it with a permitted name that must not be
    reported. A passing positive case alone does not establish that the check
    is fail-closed.
  - Assert the other runtimes are unchanged: `todo` still maps to `todo` and
    `todos` for Copilot, remains absent from the Antigravity adapter, and the
    Codex capability prose still lists the declared capability intents.

- [ ] **5. Regenerate, install, and verify.**
  - Owner: `orchestrator` for authoritative verification; route any failure
    back to the `coder`.
  - Run `uv run python scripts/generate_targets.py --all`, then
    `uv run python scripts/validate_targets.py`. Never hand-copy generated
    files from `shared/`.
  - Confirm the regenerated diff is limited to the expected files: the three
    Claude agent frontmatter `tools:` lines and the two instruction lines in
    the generated copy of `workflow.instructions.md`. Investigate any other
    changed generated file before continuing.
  - Run the full repository test, Ruff, formatting, and Mypy commands below.
  - Refresh the dogfood installation with
    `uv run python scripts/install_bootstrap.py . --allow-self --local-only`,
    then run `uv run python scripts/check_runtime.py`. Do not resolve runtime
    drift by deleting consumer-owned state.
  - Confirm the installed `.claude/agents/*.md` no longer name `TodoWrite`.
  - Stage every changed file before running `record_findings.py`. The commit
    gate's `content_hash` is `git hash-object` of `git diff <base>`, which
    excludes untracked files; unstaged files make the recomputed hash mismatch
    and the gate rejects the report as dirty.

- [ ] **6. Document the runtime limitation and close out the only phase.**
  - Owner: `documenter`, followed by orchestrator closeout.
  - Record the confirmed contract in current guidance: `TodoWrite` and the four
    task tools are mutually exclusive and selected by
    `CLAUDE_CODE_ENABLE_TASKS`; Claude Code v2.1.233 and later omit all five on
    Opus 4.8, Sonnet 5, Fable 5, Mythos 5, and later versions of those families
    unless `CLAUDE_CODE_ENABLE_TODO_TOOLS=1`; background subagents lose the four
    task tools whatever the `tools:` field says; and generated Claude subagents
    therefore track phases as prose, which the orchestrator prompt already
    instructs.
  - State plainly that this is a runtime limitation the bootstrap does not work
    around, and that the bootstrap sets no environment variable to change it.
  - Update `docs/target-mapping.md` and `README.md` only where an existing
    statement would otherwise be incomplete.
  - Audit `README.md`, `CLAUDE.md`, `AGENTS.md`, current `docs/`, shared
    policies, skills, templates, agents, review profiles, state READMEs,
    `.claude/instructions/project-context.instructions.md`, and
    `.claude/MEMORY.md` for stale claims about Claude task tracking or the
    `todo` capability. Leave dated plans, dated design narratives, and closed
    session logs unchanged unless one actively misleads and no closeout receipt
    binds it.
  - Record every audited surface and its outcome under
    `## Stale-claims surfaces checked` in the completed closeout session log.
  - Record a `[LEARN]` entry covering the durable lesson — a generated tool
    allowlist must be validated against the runtime's enabled tools, not
    against the generator's own map — or the exact approved no-lessons marker.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/ -q --tb=short
uv run ruff check shared scripts tests
uv run ruff format --check shared scripts tests
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run python scripts/install_bootstrap.py . --allow-self --local-only
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py phase --format json --persist
```

Focused checks during implementation:

```bash
uv run pytest tests/test_validate_targets.py -q --tb=short
rg -n 'TodoWrite' shared scripts tests docs README.md CLAUDE.md AGENTS.md
rg -n '^tools:' dist/multi-agent/.claude/agents
```

After documentation, findings, LEARN, and the completed session log are current:

```bash
uv run python .claude/scripts/verify.py closeout --format json --persist
```

## Review Profiles

- `code`: the generator mapping change, the validator check, and the reworded
  instruction lines.
- `architecture`: whether an unmapped capability is the right expression of a
  runtime gap, and whether the `vscode` precedent genuinely applies.
- `security`: that the new allowlist is fail-closed, that it cannot be widened
  by accident, and that the `mcp__` exemption does not create a bypass.
- `tests`: adversarial coverage of the allowlist, the zero-tool guard, and the
  unchanged other-runtime assertions.
- `ponytail`: whether the change is the minimum correct diff, and whether the
  new constant, comment, and tests carry their weight.
- `documentation`: accuracy of the recorded runtime contract, including version
  and model qualifiers.

## Closeout Checklist

- [ ] Verification passed (`verify phase` PASS)
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Closeout session log has a non-empty
  `## Stale-claims surfaces checked` section

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record the required pause fields, and create a session log
with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it does
not complete or advance this phase. On resume, restore this same phase to
`in-progress`, read its pause evidence and current Git state, and continue
without creating another small plan.
