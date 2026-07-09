# Plan — Per-agent model & effort tiering for the Claude Code target

**Status:** Proposed
**Date:** 2026-07-09
**Implementation branch:** `agent-model-effort-tiers` (off `dev`)
**Derives from:** conversation on matching model spend to role — powerful models where reasoning matters, cheap models for mechanical work — after finding the Claude target currently applies no per-agent model at all.
**Effort:** S (five `agent.yaml` edits, one generator function, one validator block, docs; single implementation pass).
**Audience note:** written to be implemented without prior context. Every change names its file and behavior contract; every claim about Claude Code capabilities is doc-verified with a cited source.

---

## 1. Context

Today the Claude Code target has **flat** model selection. Every agent's
`model_intent.claude-code` is the string `"target-native"`, and the generator that
emits Claude agents — [`render_claude_agents`](../scripts/generate_targets.py)
(lines 616-633) — **never reads `model_intent` at all**; it emits only `name`,
`description`, and `tools`. Consequence: every subagent inherits the session
model, so running the session on Opus makes even the verifier run on Opus. There
is no cost/quality tiering.

The goal: put the powerful model + high reasoning effort where mistakes cascade
(planning, review, implementation) and a cheap model on mechanical work
(verification). Only the **Claude Code** target changes; GitHub Copilot per-agent
models already work via [`render_github_agent_adapter`](../scripts/generate_targets.py)
(lines 583-613), and Codex ignores model intent entirely.

## 2. Capability findings (doc-verified — cite in review)

- **Model** is settable per subagent via `model:` frontmatter. Valid values:
  `opus`, `sonnet`, `haiku`, `fable`, full IDs (e.g. `claude-opus-4-8`), or
  `inherit`. A delegating agent *can* override the model per-invocation, but we
  deliberately **do not** build dynamic selection into the orchestrator — tiers
  stay fixed in frontmatter (consistent with the "orchestrator has no per-task
  escape hatches" principle).
- **Effort** is settable per subagent via `effort:` frontmatter, overriding
  session effort while that agent runs. There is **no** per-invocation effort
  override — static frontmatter (or session `/effort`) is the only lever, so
  frontmatter is the only way to differentiate effort by role.
- **Effort × model matrix:** Sonnet 5 / Opus 4.8 / Fable 5 support
  `low|medium|high|xhigh|max`; **Haiku is not listed and does not support the
  `effort:` field at all** — setting any effort on Haiku is invalid.
- **Thinking** cannot be configured per subagent (Claude Code v2.1.198+:
  subagents inherit the session's extended-thinking state). Nothing to configure;
  it is a session-level toggle only. Documented so the omission is intentional.
- Sources: [subagents.md](https://code.claude.com/docs/en/subagents.md),
  [model-config.md § Adjust effort level](https://code.claude.com/docs/en/model-config.md#adjust-effort-level).

## 3. Target tiers

| Agent | `model` (claude-code) | `effort` | Rationale |
|---|---|---|---|
| orchestrator | `inherit` (session) | `inherit` | Main-thread persona; model/effort come from `/model` + `/effort`. Run session on **Opus or Fable**. |
| planner | `opus` | `max` | Deep planning; a bad plan cascades. (Copilot intent already pins planner to Opus.) |
| reviewer | `sonnet` | `xhigh` | Two-pass adversarial review — push reasoning hard. |
| coder | `sonnet` | `xhigh` | Real implementation; run at full reasoning. |
| documenter | `sonnet` | `high` | Wanted `high` effort; Haiku has no effort knob, so it runs on Sonnet to honor it. |
| verifier | `haiku` | *(none)* | Mechanical run/report; Haiku cannot take an effort setting, so none is emitted. |

- Orchestrator emits **no** `model:`/`effort:` line (values `inherit` → renderer
  omits them), so it fully follows the session. "Orchestrator uses Opus/Fable" is
  a session choice, documented — not enforceable via an agent file.
- **Verifier (Haiku) must omit `effort:`** — Haiku does not support it.

## 4. Changes

All source edits are under `shared/` and `scripts/`; `dist/` is regenerated,
never hand-edited (`python scripts/generate_targets.py --all`).

### 4.1 Encode intent — `shared/agents/*/agent.yaml`

Change each `model_intent.claude-code` from the string `"target-native"` to an
object `{ "model": ..., "effort": ... }` per §3. Example
([shared/agents/planner/agent.yaml](../shared/agents/planner/agent.yaml)):

```json
"model_intent": {
  "github-copilot": "Claude Opus 4.6",
  "claude-code": { "model": "opus", "effort": "max" },
  "openai-codex": "target-native"
}
```

Orchestrator uses `{ "model": "inherit", "effort": "inherit" }`; verifier uses
`{ "model": "haiku" }` (no `effort` key). Leave the `github-copilot` and
`openai-codex` values untouched (still strings) — only the Claude renderer reads
the new object shape.

### 4.2 Emit frontmatter — [`render_claude_agents`](../scripts/generate_targets.py) (lines 616-633)

After building the `tools` line, read the claude-code intent and append
`model:`/`effort:` lines, skipping absent/`inherit`/legacy-string values:

```python
intent = agent.get("model_intent", {}).get("claude-code")
if isinstance(intent, dict):
    model = intent.get("model")
    effort = intent.get("effort")
    if model and model != "inherit":
        frontmatter.append(f"model: {model}")
    if effort and effort != "inherit":
        frontmatter.append(f"effort: {effort}")
```

The `isinstance(dict)` guard keeps backward compatibility: a leftover
`"target-native"` string emits nothing (inherit).

### 4.3 Validate — [`scripts/validate_targets.py`](../scripts/validate_targets.py)

Mirror the existing hand-maintained `COPILOT_MODEL_PINS` /
`GITHUB_ALLOWED_AGENT_MODELS` pattern (lines 24-38) with Claude allow-lists and a
dated "re-verify against the reference" comment:

```python
CLAUDE_ALLOWED_AGENT_MODELS = {"opus", "sonnet", "haiku", "fable", "inherit"}
CLAUDE_ALLOWED_EFFORT = {"low", "medium", "high", "xhigh", "max"}
# Models that do NOT support the effort field (per model-config.md). Haiku
# accepts no effort level; setting one is invalid. Re-verify against the effort
# level table when you touch this (last checked 2026-07-09).
CLAUDE_NO_EFFORT_MODELS = {"haiku"}
```

In the existing `claude_agents` frontmatter loop (~lines 217-240 of
`validate_agents`), parse any `model:`/`effort:` lines and `check()`:
- `model` is in `CLAUDE_ALLOWED_AGENT_MODELS`;
- `effort` (if present) is in `CLAUDE_ALLOWED_EFFORT`;
- **model↔effort compatibility:** an agent whose `model` is in
  `CLAUDE_NO_EFFORT_MODELS` must **not** carry an `effort:` line — guards the
  verifier/Haiku case and any future Haiku agent.

### 4.4 Document — [docs/architecture.md](../docs/architecture.md) + [README.md](../README.md)

- `architecture.md` (the "model intent" bullet, ~line 107): note the Claude
  target now carries per-agent `model` + `effort`, and that **thinking is
  session-inherited (no per-agent knob)** so its absence is intentional.
- `README.md` agent section: add the §3 tier table and one line that the
  orchestrator's model/effort come from the session (run on Opus/Fable).

### 4.5 Regenerate

`python scripts/generate_targets.py --all`. Do not touch `dist/` by hand.

### Optional (not required)

[shared/schemas/agent.schema.json](../shared/schemas/agent.schema.json) already
permits the new shape (`model_intent` is `additionalProperties: true`).
Optionally tighten it later to document the object form; not needed here.

## 5. Verification

1. **Regenerate cleanly:** `python scripts/generate_targets.py --all` succeeds.
2. **Frontmatter is correct** — inspect the six
   `dist/multi-agent/.claude/agents/*.md`:
   - planner: `model: opus` + `effort: max`
   - reviewer: `model: sonnet` + `effort: xhigh`
   - coder: `model: sonnet` + `effort: xhigh`
   - documenter: `model: sonnet` + `effort: high`
   - verifier: `model: haiku`, **no `effort:` line**
   - orchestrator: **neither line**
3. **Validator passes:** `python scripts/validate_targets.py` and
   `python scripts/check_runtime.py` report no errors, including the new
   allow-list and model↔effort compatibility checks.
4. **Idempotent generation:** re-run `generate_targets.py --all`; `git diff` shows
   no further changes.
5. **Runtime spot-check:** in a real Claude Code session, invoke each
   effort-bearing subagent once (planner/reviewer/coder/documenter) — no
   "unsupported effort level" error — and invoke verifier to confirm Haiku runs
   cleanly with no effort set.

## 6. Out of scope

- No dynamic per-task model/effort selection in the orchestrator (fixed tiers).
- No per-agent thinking configuration (not supported by Claude Code).
- No changes to GitHub Copilot or Codex model handling.
