---
name: consumer-neutral-root-guidance
type: big-plan
status: planning
originating_branch: dev
implementation_branch: consumer-neutral-root-guidance_implementation
started_at: 2026-08-09T02:13:42Z
phases:
  - 2026-08-09_phase-A-consumer-neutral-root-guidance
current_phase:
bypass_acknowledged: false
---

# Big Plan: consumer-neutral-root-guidance

## Context

The root `AGENTS.md` and `CLAUDE.md` in this authoring repository correctly describe the bootstrap itself and must remain byte-for-byte unchanged. The generated copies installed from `dist/multi-agent/` currently describe every consumer repository as a reusable multi-agent bootstrap, which is inaccurate.

The generator owns those consumer-facing files. A second ownership issue must be handled at the same time: root `AGENTS.md` is Git-tracked and therefore preserved during an installer self-refresh, while root `CLAUDE.md` is ignored and untracked. Regenerating neutral output without correcting that ownership distinction would allow a later self-refresh to replace the authoring repository's `CLAUDE.md` with the consumer template.

## Goals

- Make generated Claude Code and OpenAI Codex root guidance neutral to the consuming project's purpose.
- Keep the authoring repository's root `AGENTS.md` and `CLAUDE.md` bytes unchanged.
- Make preservation of both authoring root adapters durable across generation, installer self-refresh, and state restoration.
- Add focused regression coverage for wording, generated output, and preservation behavior.

## Design Overview

1. Update `render_root_guidance()` in `scripts/generate_targets.py` so generated adapters use project-neutral titles and language. Proposed wording:
   - `# Claude Code Project Guidance`
   - `# OpenAI Codex Project Guidance`
   - `This file is the root entrypoint for this repository's guidance. The canonical runtime guidance lives under .claude/; do not hand-edit generated target adapters.`
   - Keep `.claude/` as the canonical runtime basis, and direct customization to consumer-owned project context and state.
2. Reject only the known authoring-specific phrases in generated roots: `Bootstrap Guidance`, `reusable multi-agent bootstrap`, `In an installed project`, and `Bootstrap maintainers own authoring and regeneration`. Do not ban the word `bootstrap` globally because legitimate workflow/tool references may use it.
3. Force-track the existing root `CLAUDE.md` without changing its content, and add it beside `AGENTS.md` in `TRACKED_AUTHORING_PATHS`. Existing installer/restorer preservation logic can then treat both authoring adapters consistently.
4. Add per-file preservation assertions using pre/post hashes so a passing aggregate check cannot hide a change to one root adapter.
5. Regenerate `dist/multi-agent/` from `shared/` and the generator; do not hand-edit generated output.

## Non-Goals

- Do not neutralize or rewrite the authoring repository's root `AGENTS.md` or `CLAUDE.md`.
- Do not redesign the complete generated guidance hierarchy.
- Do not bundle the report's broader recommendations about Ponytail, Graphify, writing policy, diagnostics, tool pinning, or additional analysis tools.
- Do not open a PR or push without explicit user instruction.

## Phases

### Phase A: Consumer-neutral root guidance

Create the matching small plan, then:

1. Record individual SHA-256 hashes for root `AGENTS.md` and `CLAUDE.md`.
2. Create the implementation branch from a clean, synchronized `dev` branch.
3. Update generator wording and focused tests.
4. Force-track the current `CLAUDE.md` bytes and update the authoring-path ownership declaration.
5. Regenerate all targets and run the installer self-refresh/local state restoration checks.
6. Confirm both root hashes are unchanged and generated roots contain the neutral wording.
7. Run the repository's required verification, review, documentation-impact, score, learning, and session-log gates before the atomic phase commit.

Acceptance criteria:

- Generated `dist/multi-agent/CLAUDE.md` and `dist/multi-agent/AGENTS.md` describe a generic consumer repository, not a bootstrap repository.
- Neither generated file contains any of the four rejected authoring-specific phrases.
- Root `AGENTS.md` retains SHA-256 `440279e04b230e856c0670475a9f578ee6eacab1a6aa208323b40e5ce1ebbc8e`.
- Root `CLAUDE.md` retains SHA-256 `34416b9d55a24f2f4cb7f56e60dc47c097f4941da740ced3ea39e6f353455755`.
- Both root adapters are recognized as tracked authoring-owned paths and survive self-refresh/state restoration unchanged.
- Target validation, installer tests, runtime/state-restoration tests, and the full repository verification suite pass.

## Risks and Mitigations

- **Tracking an ignored file is unusual:** keep the current bytes unchanged and document that this mirrors the existing tracked-root-adapter ownership model for `AGENTS.md`.
- **Over-broad wording assertions could reject legitimate content:** assert against the known incorrect phrases rather than every occurrence of `bootstrap`.
- **Self-refresh could mask an ownership regression:** verify each authoring root independently before and after regeneration and self-refresh.

## Verification

- Generator/target validation tests covering both target roots.
- Installer preservation tests for tracked root adapters.
- State-sync/restoration tests for both root adapters.
- `uv run python scripts/generate_targets.py --all` followed by generated-output checks.
- Installer self-refresh against this repository followed by individual root hash comparison.
- Full project test, lint, formatting, runtime, and generated-wiring checks required by repository policy.

