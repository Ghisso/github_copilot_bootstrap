---
name: codex-gpt-5.6-model-tiering
type: big-plan
status: in-progress
originating_branch: dev
implementation_branch: codex-gpt-5.6-model-tiering_implementation
started_at: 2026-07-18T04:15:10Z
phases:
  - 2026-07-18_phase-B-configure-codex-gpt-5.6
current_phase: 2026-07-18_phase-B-configure-codex-gpt-5.6
---

# Big Plan: codex-gpt-5.6-model-tiering

## Context

The generated Codex target currently pins `gpt-5.5` globally and varies only
reasoning effort. GPT-5.6 adds explicit Sol, Terra, and Luna roles plus `max`
reasoning effort. The approved migration keeps Sol for quality-critical
coordination and planning, uses Terra for routine implementation and
documentation, and uses Luna for mechanical verification.

## Goals

- Make `gpt-5.6-sol` with `xhigh` effort the generated Codex session default.
- Give every Codex agent an explicit model and effort matched to its task.
- Validate the canonical-to-generated model/effort contract and reject drift.
- Update active documentation without rewriting the historical GPT-5.5 plan.

## Design Overview

Reuse the existing `model_intent.openai-codex` objects and
`render_codex_agent_adapter` implementation. Add only the missing explicit
model values, global effort pin, strict validation, and documentation.

## Phases

- [ ] `2026-07-18_phase-B-configure-codex-gpt-5.6`

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```
