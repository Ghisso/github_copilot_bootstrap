---
name: guidance-and-review-calibration
type: big-plan
status: planning
originating_branch: dev
implementation_branch: guidance-and-review-calibration_implementation
started_at: 2026-08-09T02:13:42Z
phases:
  - 2026-08-09_phase-A-consumer-neutral-root-guidance
  - 2026-08-09_phase-B-human-facing-writing-guidance
  - 2026-08-09_phase-C-ponytail-authority-calibration
current_phase:
bypass_acknowledged: false
---

# Big Plan: guidance-and-review-calibration

## Context

The attached review correctly identifies three related guidance problems:

1. Generated root `AGENTS.md` and `CLAUDE.md` files describe every consumer repository as a reusable multi-agent bootstrap, which is inaccurate.
2. The current reporting convention defaults both orchestrator-facing and user-facing reports to `caveman full`, although terse compressed prose is not the right default for communication with a user.
3. Ponytail has accumulated more authority than a simplification aid needs: it is a named lifecycle phase, a mandatory pre-coding load, a required review profile for broad classes of work, and a special commit/push gate where even a minor Ponytail finding blocks progress.

These concerns belong in one big plan because they calibrate how generated agents describe a project, communicate with people, and apply simplification guidance. Each concern remains an independently verifiable, commit-sized phase.

The root `AGENTS.md` and `CLAUDE.md` in this authoring repository correctly describe the bootstrap itself and must remain byte-for-byte unchanged. The generated copies installed from `dist/multi-agent/` must be project-neutral.

## Goals

- Make generated Claude Code and OpenAI Codex root guidance neutral to the consuming project's purpose.
- Keep the authoring repository's root `AGENTS.md` and `CLAUDE.md` bytes unchanged across generation, installer self-refresh, and state restoration.
- Make clear, direct, normal prose the default for user-facing responses and documentation.
- Restrict `caveman` compression to agent-to-agent status/reporting where it provides value.
- Remove Ponytail as a standalone lifecycle phase and universal pre-coding requirement.
- Retain Ponytail as a conditional simplification/review capability for diffs with meaningful complexity risk.
- Gate Ponytail findings by the ordinary severity model so minor suggestions are advisory.

## Design Overview

### Neutral consumer guidance

Update `render_root_guidance()` in `scripts/generate_targets.py` so generated adapters use project-neutral titles and language. Reject only the known authoring-specific phrases in generated roots: `Bootstrap Guidance`, `reusable multi-agent bootstrap`, `In an installed project`, and `Bootstrap maintainers own authoring and regeneration`.

Root `AGENTS.md` is currently Git-tracked and preserved during self-refresh, while root `CLAUDE.md` is ignored and untracked. Force-track the existing `CLAUDE.md` without changing its content and add it beside `AGENTS.md` in `TRACKED_AUTHORING_PATHS`, allowing the existing installer/restorer ownership rules to preserve both files consistently.

### Human-facing writing

Evolve `shared/policies/agent-reporting.instructions.md`; do not create a competing communication policy. Define two audiences:

- User-facing responses and user-facing documentation use clear, direct, natural prose, with detail calibrated to the task.
- Agent-to-agent status and handoff messages may default to `caveman full`, while preserving code, commands, paths, identifiers, structured data, and exact evidence.

Align canonical agent prompts, generated adapters, README documentation, and validation assertions with that audience boundary. Keep `humanize` optional rather than adding a mandatory rewrite stage.

### Ponytail authority

Use this bounded model:

- The canonical lifecycle becomes `PRE-FLIGHT -> BRANCH -> PLAN -> IMPLEMENT -> VERIFY -> REVIEW -> DOCUMENT -> SCORE -> LEARN -> SESSION LOG -> COMMIT`; Ponytail is no longer a separate phase.
- Loading Ponytail `full` before every coding task is no longer mandatory. Its reusable principles—reuse first, prefer native capabilities, and choose the minimum correct diff—remain implementation guidance.
- Ponytail review is conditional: require/select it for control-plane or high-risk work and when a diff introduces or substantially changes abstractions, dependencies, architecture, generalized infrastructure, or similar complexity. It is optional for ordinary low-complexity work and unnecessary for documentation-only changes.
- Remove the special hook rule requiring zero Ponytail findings. If Ponytail runs, its findings remain in the unified findings report and obey existing severity gates: CRITICAL blocks commit, MAJOR blocks push, and MINOR is advisory.
- Preserve report-field compatibility where practical, but stop requiring `ponytail_reviewed` and `ponytail_findings` for diffs where the profile is not applicable.

## Non-Goals

- Do not neutralize or rewrite the authoring repository's root `AGENTS.md` or `CLAUDE.md`.
- Do not redesign the complete generated guidance hierarchy.
- Do not remove, fork, or rewrite the vendored Ponytail skills.
- Do not weaken the ordinary code, architecture, security, tests, documentation, score, or severity gates.
- Do not add a second writing policy or mandate `humanize` as a workflow stage.
- Do not bundle Graphify, ast-grep, Serena, capability registry, telemetry, LLM evaluation, diagnostic expansion, or external-tool version pinning.
- Do not open a PR, push, or merge without explicit user instruction.

## Phases

### Phase A: Consumer-neutral root guidance

1. Record individual SHA-256 hashes for root `AGENTS.md` and `CLAUDE.md`.
2. Update generated root titles, introduction, and ownership wording for generic consumer projects.
3. Add exact regression assertions rejecting the four known authoring-specific phrases without globally banning the word `bootstrap`.
4. Force-track the current root `CLAUDE.md` bytes and update the authoring-path ownership declaration.
5. Regenerate all targets and exercise installer self-refresh/state restoration.
6. Confirm both authoring root hashes remain unchanged.

Acceptance criteria:

- Generated `dist/multi-agent/CLAUDE.md` and `dist/multi-agent/AGENTS.md` describe a generic consumer repository.
- Neither generated file contains any of the four rejected authoring-specific phrases.
- Root `AGENTS.md` retains SHA-256 `440279e04b230e856c0670475a9f578ee6eacab1a6aa208323b40e5ce1ebbc8e`.
- Root `CLAUDE.md` retains SHA-256 `34416b9d55a24f2f4cb7f56e60dc47c097f4941da740ced3ea39e6f353455755`.
- Both authoring root adapters survive generation, self-refresh, and restoration unchanged.

### Phase B: Human-facing writing guidance

1. Change the central reporting policy from a universal caveman default to an explicit audience-based rule.
2. Update canonical agent prompts so user-facing answers use clear natural prose and internal status/handoffs may use caveman compression.
3. Update generated guidance and validators that currently require caveman wording from every non-documenter agent.
4. Update README documentation and examples to describe the new communication boundary.

Acceptance criteria:

- User-facing responses and documentation are explicitly governed by clear, direct, natural prose.
- Caveman remains available for internal agent status/handoffs but is not the default for user communication.
- Exact technical material is protected from lossy rewriting.
- No duplicate communication policy or mandatory rewrite step is introduced.
- Canonical sources, generated targets, and validation tests agree on the same audience distinction.

### Phase C: Ponytail authority calibration

1. Remove `PONYTAIL` from the canonical lifecycle in policies, generated root guidance, README documentation, and lifecycle validators.
2. Replace the universal `ponytail full` pre-coding requirement with concise implementation principles plus explicit conditional triggers for loading/reviewing with Ponytail.
3. Update reviewer/profile guidance so Ponytail is required for control-plane/high-risk or complexity-expanding changes and optional otherwise.
4. Remove the special zero-Ponytail-findings hook gate while retaining unified severity gates.
5. Make Ponytail-specific report metadata optional when the profile did not run, retaining backward compatibility for existing reports and tools.
6. Update commit/push, report-recording, diff-classification, generated-target, and policy tests for required, optional, advisory, and blocking cases.
7. Update README and architecture/workflow documentation affected by the authority change.

Acceptance criteria:

- The canonical lifecycle contains no standalone Ponytail phase.
- Ordinary coding tasks do not require loading Ponytail before implementation.
- Ponytail remains discoverable and required/selected for the documented high-risk and complexity triggers.
- A MINOR Ponytail finding is recorded but does not block commit or push.
- A Ponytail CRITICAL finding blocks commit and a Ponytail MAJOR finding blocks push through the ordinary severity gates.
- Documentation-only and non-applicable diffs do not require Ponytail metadata.
- Existing valid findings reports remain consumable where compatibility is promised.

## Cross-Phase Verification

For every phase:

- Create and approve the matching small plan before implementation.
- Regenerate targets from canonical sources; never hand-edit `dist/`.
- Run focused generator, policy, hook, findings-report, installer, and state-restoration tests affected by that phase.
- Run the full project test, lint, formatting, runtime, generated-wiring, and documentation checks required by repository policy.
- Complete profile-driven review, score, learning, and session-log gates before the atomic phase commit.

Before big-plan closeout:

- Verify all three small plans are complete and committed independently.
- Re-run full target generation and repository verification from a clean worktree.
- Confirm the authoring root file hashes still match the recorded values.
- Confirm generated roots, reporting policy, generated agent prompts, hook behavior, README, and validators express one consistent model.

## Risks and Mitigations

- **Tracking an ignored file is unusual:** keep the current `CLAUDE.md` bytes unchanged and document that this mirrors the existing tracked-root-adapter ownership model for `AGENTS.md`.
- **Audience rules could become subjective:** specify observable audience categories and protect exact technical material explicitly.
- **Removing the special Ponytail gate could hide serious findings:** preserve the ordinary CRITICAL-at-commit and MAJOR-at-push gates for every review profile.
- **Conditional Ponytail use could drift:** centralize triggers in workflow/review guidance and test representative required, optional, and exempt cases.
- **Metadata changes could break old reports:** prefer optional/backward-compatible readers and fixtures rather than deleting fields immediately.
- **Policy and generated output could diverge:** update canonical sources first, regenerate all targets, and validate exact lifecycle/reporting fragments.

