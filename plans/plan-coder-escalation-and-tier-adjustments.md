# Plan — Escalate-on-failure for the Codex `coder`, plus two evidence-backed tier adjustments

**Status:** Proposed
**Date:** 2026-08-01
**Implementation branch:** `coder-escalation-and-tier-adjustments` (off `dev`)
**Derives from:** conversation reconsidering the "no dynamic per-task model/effort selection" rule from [plan-agent-model-effort-tiers.md](plan-agent-model-effort-tiers.md), after (a) GPT-5.6 Terra/Luna got a real price cut on 2026-07-30 (Terra -20%, Luna -80%), (b) online commentary claims Luna/Terra at high effort rivals Sol on generalist coding-agent benchmarks, and (c) a live audit of this bootstrap's two real consumer repos (`tap`, `translation-workflow`) plus external benchmarks showed that claim holds on aggregate indices but not on the code-review-specific benchmark closest to this repo's `reviewer`/`coder` workload.
**Effort:** S (one prompt-doc edit, one small validator addition, two `agent.yaml` data edits, docs).
**Audience note:** written to be implemented without prior context. Every capability claim is doc-verified with a cited source, matching the rigor of the plan this one derives from.

---

## 1. Context

The current design (`plan-agent-model-effort-tiers.md`, then `codex-gpt-5.6-model-tiering_implementation`) fixes one static `(model, effort)` pair per role per target, and explicitly rules out dynamic per-task selection: *"No dynamic per-task model/effort selection in the orchestrator (fixed tiers)."* That call was correct for **upfront, judgment-based** selection — an orchestrator guessing task difficulty from a description is exactly the failure mode this plan avoids repeating.

But a narrower, **signal-based** form of dynamism is safe: re-run a step at a stronger tier only after a structured, already-existing tool output (`verifier` failure, or a `reviewer` CRITICAL/MAJOR/`ponytail` finding) says the base tier's result was actually wrong. This is not a guess — it is a reaction to a fact the pipeline already produces today.

Two live-repo audits (this session, read-only, no edits) support keeping the *base* `coder`/`reviewer` tiers as they are and not trusting a cheaper tier by default:

- `tap`: a fail-closed async Redis approval protocol (`src/tap/triage/approval.py`), a path-traversal-proof artifact store built on a verified Haystack hook-lifecycle fact, and deterministic sha256-bucket split logic — plus three integration defects that survived a green unit-test suite and only surfaced in a live pass.
- `translation-workflow`: era-calendar/full-width-digit normalization requiring `Decimal` (not `float`, with a named regression test), a false-positive-elimination fix distinguishing `3-SHAKE` from `8-year` (structurally identical digit-hyphen-Latin patterns), and a real Bedrock API migration with a documented dead end.

External benchmarks corroborate the risk is concentrated exactly where the audits found it: CodeRabbit's own code-review benchmark shows Terra trailing Sol by **17 points** (52.5% vs 69.7%) with **no data at all for Luna on review** — the closest available proxy to this repo's `reviewer`/`coder` job, versus a much smaller ~5-point Sol/Terra/Luna spread on the generalist Artificial Analysis Coding Agent Index. The "Luna/Terra at high effort is great" chatter is real (Sebastian Raschka: *"Luna with Extra High effort may be better and cheaper than Sol with Medium effort"*) but is winning on generalist agentic benchmarks, not on the review-specific one.

Conclusion: don't lower the base tiers. Instead, give the Codex `coder` a verified escape hatch upward, and apply the two tier changes that both audits and the external Luna use-case guidance actually support.

## 2. Capability findings (doc-verified — cite in review)

- **Codex supports spawn-time overrides, not just named profiles.** Per the Codex subagent configuration docs (`developers.openai.com/codex/subagents`, redirects to `learn.chatgpt.com/docs/agent-configuration/subagents`, checked 2026-08-01): *"Explicit spawn values override `agents.default_subagent_model` and `agents.default_subagent_reasoning_effort`."* This means the **same** `coder` agent definition can be invoked with a different `model`/`model_reasoning_effort` at spawn time — escalation needs **no second `.codex/agents/*.toml` file**, no generator change, and no change to `expected_codex_names`/`expected_count` in `validate_targets.py`. This simplifies the design from an earlier sibling-adapter-file sketch.
- **Claude Code has no per-invocation effort override.** Per `plan-agent-model-effort-tiers.md` §2 (`code.claude.com/docs/en/model-config.md#adjust-effort-level`, checked 2026-07-09): *"There is no per-invocation effort override — static frontmatter (or session `/effort`) is the only lever."* Model *can* be overridden per-call on Claude, but effort cannot — so a Claude-side escalation lane would need a second static agent file to get a genuinely different effort tier, which is a materially different (and unproven-necessary) change. **Out of scope for this plan** — see §6.
- **Both Codex allow-lists already cover the escalated values.** `CODEX_ALLOWED_AGENT_MODELS` already includes `gpt-5.6-sol`; `CODEX_ALLOWED_EFFORT` already includes `xhigh` and `medium` (`scripts/validate_targets.py:49-53`). No allow-list expansion needed.

## 3. Design

### 3.1 Encode the escalation target — `shared/agents/coder/agent.yaml`

Add a declarative `escalate_to` key next to the existing Codex intent. This is **documentation-as-data**, not consumed by the TOML emitter — `coder.toml` itself is unchanged; the value only has to match what the orchestrator prompt says (validated in §3.3).

```json
"model_intent": {
  "github-copilot": "GPT-5.4",
  "claude-code": { "model": "sonnet", "effort": "xhigh" },
  "openai-codex": {
    "model": "gpt-5.6-terra",
    "effort": "high",
    "escalate_to": { "model": "gpt-5.6-sol", "effort": "xhigh" }
  }
}
```

### 3.2 Orchestrator guidance — `shared/agents/orchestrator/prompt.md`

Add a new `## Escalation On Failure` section after `## Reviewer Routing` (target-neutral text, rendered into all three targets — inert on Claude/Copilot since neither has a matching mechanism to invoke):

```markdown
## Escalation On Failure

On OpenAI Codex only (spawn-time model/effort overrides are a Codex capability;
Claude Code has no per-invocation effort override): if `verifier` fails, or
`reviewer` returns a CRITICAL/MAJOR finding or any surviving `ponytail` finding,
on a diff `coder` just produced, re-delegate the fix to `coder` with explicit
spawn overrides `model = gpt-5.6-sol`, `model_reasoning_effort = xhigh` instead
of retrying at its configured `gpt-5.6-terra`/`high` tier. Escalate at most once
per phase. If the escalated attempt also fails verification or review, stop the
fix loop and report the failure to the user instead of retrying further.
```

### 3.3 Validator — `scripts/validate_targets.py`

In `validate_agents()`, alongside the existing per-agent Codex intent read (`scripts/validate_targets.py:289-295`):

```python
escalate_to = codex_intent.get("escalate_to") if isinstance(codex_intent, dict) else None
if escalate_to is not None:
    check(agent_id == "coder", f"{agent_id} defines escalate_to but only coder is expected to", errors)
    esc_model, esc_effort = escalate_to.get("model"), escalate_to.get("effort")
    validate_codex_model_contract(f"{agent_id} escalate_to", esc_model, esc_effort, errors)
    check(
        (esc_model, esc_effort) != (model, effort),
        f"{agent_id} escalate_to must differ from its base Codex tier",
        errors,
    )
    orchestrator_prompt = read(REPO_ROOT / "shared" / "agents" / "orchestrator" / "prompt.md")
    check(
        esc_model in orchestrator_prompt and esc_effort in orchestrator_prompt,
        "orchestrator prompt.md must name the coder escalate_to model/effort verbatim, or it will silently drift from agent.yaml",
        errors,
    )
```

This reuses `validate_codex_model_contract` (already defined at `scripts/validate_targets.py:161`) for the allow-list check, adds a sanity check that escalation actually changes the tier, and — matching the existing drift-guard style already in this file (e.g. the `mcp__semble`/`mcp__context-mode` tools-line check at `scripts/validate_targets.py:353-359`) — guards against the prompt text and the data silently diverging.

The `agent_id == "coder"` check is a deliberate tripwire, not a hard restriction: if this bootstrap later adds `escalate_to` to another role, the failing check is a two-second edit to widen, not a silent gap.

### 3.4 Static tier adjustments (evidence-backed, no design needed)

Both audits independently flagged `documenter` as the one role that's a notch over-provisioned (`tap` survey: *"most of its work (README/docs sync) is descriptive, not decision-making"*), and CodeRabbit explicitly names *"quick summaries, simple code explanations, PR summaries"* as Luna's use case — a near-literal description of the documenter's job (read diff, describe changed interfaces).

`shared/agents/documenter/agent.yaml`:

```diff
   "model_intent": {
     "github-copilot": "target-default",
-    "claude-code": { "model": "sonnet", "effort": "high" },
-    "openai-codex": { "model": "gpt-5.6-terra", "effort": "medium" }
+    "claude-code": { "model": "sonnet", "effort": "medium" },
+    "openai-codex": { "model": "gpt-5.6-luna", "effort": "medium" }
   }
```

Both target values (`medium` effort, `gpt-5.6-luna` model) are already in their respective allow-lists — no validator change needed for this part.

### 3.5 Docs

- `README.md`: update the Codex tier table row for `documenter` (`gpt-5.6-terra`/`medium` → `gpt-5.6-luna`/`medium`) and the Claude row (`high` → `medium`); add one sentence under the existing per-agent tiering paragraph describing the Codex-only escalate-on-failure lane for `coder`.
- `docs/architecture.md`: add a short paragraph under "Custom Agents" documenting the `escalate_to` field and that it's declarative-only (no generated sibling file), citing the spawn-time-override capability.
- `docs/smoke-tests.md`: add an expectation under "Custom Agent Portability": *"`coder`'s `escalate_to` (Codex) names an allow-listed model/effort pair distinct from its base tier, and the orchestrator prompt names both values verbatim."*

## 4. Phases

- [ ] `coder-escalation-lane` — §3.1-3.3: `agent.yaml` `escalate_to`, orchestrator prompt section, validator check. Regenerate + validate green.
- [ ] `documenter-tier-adjustment` — §3.4: both `documenter` tier edits. Regenerate + validate green.
- [ ] `docs-sync` — §3.5: README/architecture/smoke-tests updates. Final regenerate + validate green.

## 5. Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

Negative-test the new drift-guard once: temporarily change `escalate_to.effort` in `coder/agent.yaml` without updating `orchestrator/prompt.md`, confirm `validate_targets.py` fails with the new message, then revert.

Runtime spot-check (mirrors `plan-agent-model-effort-tiers.md` §5 item 7): in a real Codex session, have the orchestrator actually trigger the escalation path once (force a `verifier` failure) and confirm the re-delegated `coder` call runs on `gpt-5.6-sol`/`xhigh` with no unsupported-model/effort error.

## 6. Out of scope

- No Claude-side escalation lane (no per-invocation effort override exists to build one on; would require a second static agent file, a materially different change from this one).
- No escalation for `reviewer`, `documenter`, `verifier`, or `planner` — no evidence from either audited repo or external benchmarks that any of them need it.
- No multi-rung ladder (Terra → Sol only, not Terra → Sol → beyond).
- No changes to gates/hooks — escalation is purely an orchestrator-delegation-time decision layered on top of structured signals the gates already produce; `enforce-commit-gate.sh`/`enforce-pr-gate.sh`/score/findings logic is untouched.
