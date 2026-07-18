# Plan — Per-agent model & effort tiering for the Claude Code and Codex targets

**Status:** Proposed
**Date:** 2026-07-09
**Implementation branch:** `agent-model-effort-tiers` (off `dev`)
**Derives from:** conversation on matching model spend to role — powerful models where reasoning matters, cheap models for mechanical work — after finding that neither the Claude Code nor the Codex target applied any per-agent model/effort tiering.
**Effort:** S/M (five `agent.yaml` edits across two `model_intent` keys, two generator functions, two validator blocks, docs; single implementation pass covering both targets).
**Audience note:** written to be implemented without prior context. Every change names its file and behavior contract; every claim about Claude Code and Codex capabilities is doc-verified with a cited source.

---

## 1. Context

Today the Claude Code target has **flat** model selection. Every agent's
`model_intent.claude-code` is the string `"target-native"`, and the generator that
emits Claude agents — [`render_claude_agents`](../scripts/generate_targets.py)
(lines 616-633) — **never reads `model_intent` at all**; it emits only `name`,
`description`, and `tools`. Consequence: every subagent inherits the session
model, so running the session on Opus makes even the verifier run on Opus. There
is no cost/quality tiering.

Codex is flat the same way: its `.codex/agents/*.toml` adapters carry no
`model`/effort, and `.codex/config.toml` pins no session model, so every Codex
agent inherits the session default.

The goal: put the powerful model + high reasoning effort where mistakes cascade
(planning, review, implementation) and a cheap model on mechanical work
(verification), across **both** the Claude Code and Codex targets. GitHub Copilot
per-agent models already work via [`render_github_agent_adapter`](../scripts/generate_targets.py)
(lines 583-613) and stay unchanged.

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
- **Codex per-agent tiering.** Codex custom agents (`.codex/agents/*.toml`)
  support per-agent `model` and `model_reasoning_effort`. Codex effort levels are
  `minimal|low|medium|high|xhigh` — there is **no `max`**. Codex has **no stable
  model aliases** (unlike Claude's `opus`/`sonnet`/`haiku`): you must pin a
  concrete model string like `gpt-5.5`, and those get sunset over time — so a
  single global pin beats per-agent model rot.
- Sources: [subagents.md](https://code.claude.com/docs/en/subagents.md),
  [model-config.md § Adjust effort level](https://code.claude.com/docs/en/model-config.md#adjust-effort-level),
  Codex [subagents](https://developers.openai.com/codex/subagents) and
  [config-reference](https://developers.openai.com/codex/config-reference).

## 3. Target tiers

### Claude Code tiers

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

### Codex tiers

Codex uses one pinned session model (`gpt-5.5`) for everything and tiers only effort:

| Agent | Codex effort |
|---|---|
| planner / reviewer / coder | `xhigh` |
| documenter | `high` |
| verifier | `low` |
| orchestrator | inherit |

- Model is pinned once globally in `.codex/config.toml` from `CODEX_SESSION_MODEL`
  in the generator — the single bump point when gpt-5.6 ships. A global pin (not
  per-agent) avoids model-name rot and also covers the main session, which a
  per-agent field cannot.
- Codex effort tops out at `xhigh` (no `max`), so Claude's planner `max` maps to
  `xhigh` here. Orchestrator emits no effort (inherits the session).

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
`{ "model": "haiku" }` (no `effort` key). Leave the `github-copilot` value
untouched (still a string); the `openai-codex` key is changed separately in §4.5.
Only the Claude renderer reads the `claude-code` object shape.

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

- `architecture.md`: note both targets now carry per-agent tiering — the Claude
  target's per-agent `model` + `effort` (with **thinking session-inherited, no
  per-agent knob**), and the Codex target's global model pin + per-agent
  `model_reasoning_effort`.
- `README.md` agent section: add the combined Claude/Codex tier table and the
  session-model notes (Claude on Opus/Fable; Codex pinned to `gpt-5.5`).

### 4.5 Codex target — global model pin + per-agent effort

- **Constant + config** — add `CODEX_SESSION_MODEL = "gpt-5.5"` near the top of
  [`generate_targets.py`](../scripts/generate_targets.py); `render_codex_config`
  emits a top-level `model = "<CODEX_SESSION_MODEL>"` line (before `[agents]`, as
  TOML requires). Every Codex agent inherits it.
- **Encode intent** — set `model_intent.openai-codex` to an object carrying the
  effort tier for the five workers (`{ "effort": "xhigh" }` for
  planner/reviewer/coder, `"high"` for documenter, `"low"` for verifier);
  orchestrator keeps the legacy `"target-native"` string (inherit).
- **Emit** — `render_codex_agent_adapter` reads `model_intent.openai-codex`; if
  it is a dict, it appends `model_reasoning_effort` (and a per-agent `model` if
  ever set), skipping legacy-string/`inherit` values.
- **Validate** — add `CODEX_ALLOWED_EFFORT = {"minimal","low","medium","high","xhigh"}`;
  the Codex agent loop rejects any `model_reasoning_effort` outside it (message
  notes "no 'max' in Codex"), and `validate_mcp_and_hooks` asserts
  `.codex/config.toml` pins a session model (presence check for a top-level
  `model =` line — the concrete value stays single-sourced in the generator).

### 4.6 Regenerate

`python scripts/generate_targets.py --all`. Do not touch `dist/` by hand.

### Optional (not required)

[shared/schemas/agent.schema.json](../shared/schemas/agent.schema.json) already
permits the new shape (`model_intent` is `additionalProperties: true`).
Optionally tighten it later to document the object form; not needed here.

## 5. Verification

1. **Regenerate cleanly:** `python scripts/generate_targets.py --all` succeeds.
2. **Claude frontmatter is correct** — inspect the six
   `dist/multi-agent/.claude/agents/*.md`:
   - planner: `model: opus` + `effort: max`
   - reviewer: `model: sonnet` + `effort: xhigh`
   - coder: `model: sonnet` + `effort: xhigh`
   - documenter: `model: sonnet` + `effort: high`
   - verifier: `model: haiku`, **no `effort:` line**
   - orchestrator: **neither line**
3. **Codex output is correct** — `dist/multi-agent/.codex/config.toml` has
   `model = "gpt-5.5"` before `[agents]`; the agent TOMLs carry
   `model_reasoning_effort` = `xhigh` (planner/reviewer/coder), `high`
   (documenter), `low` (verifier), and **none** for orchestrator.
4. **Validators pass:** `python scripts/validate_targets.py` and
   `python scripts/check_runtime.py` report no errors, including the Claude
   allow-list + model↔effort compatibility checks and the Codex effort +
   model-pin checks.
5. **Idempotent generation:** `dist/` is gitignored, so compare a content hash of
   the tree before and after a second `generate_targets.py --all` — it must be
   identical.
6. **Negative tests:** setting a Haiku agent's `effort` (Claude) and a Codex
   agent's `model_reasoning_effort = "max"` must each fail validation, then pass
   again once reverted.
7. **Runtime spot-check:** in real Claude Code / Codex sessions, invoke each
   effort-bearing agent once and confirm no "unsupported effort level" error.

## 6. Out of scope

- No dynamic per-task model/effort selection in the orchestrator (fixed tiers).
- No per-agent thinking configuration (not supported by Claude Code).
- No changes to GitHub Copilot model handling (Copilot already pins per-agent models).
