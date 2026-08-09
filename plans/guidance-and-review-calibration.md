---
name: guidance-and-review-calibration
type: big-plan
status: in-progress
originating_branch: dev
implementation_branch: guidance-and-review-calibration_implementation
started_at: 2026-08-09T02:13:42Z
phases:
  - 2026-08-09_phase-A-consumer-neutral-root-guidance
  - 2026-08-09_phase-B-planner-reliability-calibration
  - 2026-08-09_phase-C-human-facing-writing-guidance
  - 2026-08-09_phase-D-ponytail-authority-calibration
current_phase: 2026-08-09_phase-A-consumer-neutral-root-guidance
bypass_acknowledged: false
---

# Big Plan: guidance-and-review-calibration

## Context

The attached review and the planner-run investigation identify four related guidance problems:

1. Generated root `AGENTS.md` and `CLAUDE.md` files describe every consumer repository as a reusable multi-agent bootstrap, which is inaccurate.
2. The current reporting policy declares that it applies to reports sent to either the orchestrator or the user, but its concrete `caveman full` instructions are used mainly by specialist agents reporting to the orchestrator. User-facing documentation is already normal prose, and primary-agent responses are not consistently caveman in practice. The actual gap is an ambiguous audience boundary and the absence of a positive, testable standard for clear human-facing technical communication.
3. Ponytail has accumulated more authority than a simplification aid needs: it is a named lifecycle phase, a mandatory implementation discipline, a second coder simplification pass, a required review profile for every non-documentation change, and a special commit/push gate where even a minor Ponytail finding blocks progress.
4. Planner runs have repeatedly appeared unresponsive even when they were still making progress or completing normally. The investigated runs point to `max` effort, broad or repeated discovery, long silent intervals, and premature interruption rather than a general planner transport failure. The orchestrator needs a reliable way to brief, supervise, measure, and, only when justified, interrupt planners.

These concerns belong in one big plan because they calibrate how generated agents describe a project, communicate with people, and apply simplification guidance. Each concern remains an independently verifiable, commit-sized phase.

The root `AGENTS.md` and `CLAUDE.md` in this authoring repository correctly describe the bootstrap itself and must remain byte-for-byte unchanged. The generated copies installed from `dist/multi-agent/` must be project-neutral.

## Goals

- Make generated Claude Code and OpenAI Codex root guidance neutral to the consuming project's purpose.
- Keep the authoring repository's root `AGENTS.md` and `CLAUDE.md` bytes unchanged across generation, installer self-refresh, and state restoration.
- Set the Claude Code and OpenAI Codex planners to `xhigh` by default while preserving their current models and leaving the GitHub Copilot planner model unchanged.
- Give planners a compact evidence packet so they reuse verified discovery, decisions, constraints, exact artifacts, and unresolved questions instead of repeating broad exploration.
- Define single-planner supervision, pending-wait semantics, evidence-based health checks, user status updates, and benchmarked `max`/`high` exceptions.
- Add an ASD-STE100-inspired human-facing technical-writing standard without claiming formal ASD-STE100 compliance.
- Make precise, clear, direct, natural prose the default for user-facing responses, plans, explanations, reviews, reports, summaries, and documentation.
- Restrict `caveman` compression to agent-to-agent status/reporting where it provides value.
- Remove Ponytail as a standalone lifecycle phase while retaining it once as a coder implementation discipline.
- Retain Ponytail as a conditional simplification/review capability for diffs with meaningful complexity risk.
- Gate Ponytail findings by the ordinary severity model so minor suggestions are advisory.
- Define simplicity in terms of unnecessary concepts, dependencies, abstractions, layers, configuration, execution paths, and speculative behavior—not minimum physical line count.

## Design Overview

### Planner reliability and effort calibration

Change the canonical Claude Code planner from `opus`/`max` to `opus`/`xhigh` and the OpenAI Codex planner from `gpt-5.6-sol`/`max` to `gpt-5.6-sol`/`xhigh`. Keep the GitHub Copilot planner at `Claude Opus 4.6`. `xhigh` is the conservative first reduction: it remains suitable for quality-sensitive planning while avoiding the blanket use of the highest-cost setting. Do not claim that equal effort labels represent equal compute across vendors.

Make the orchestrator responsible for preparing a compact evidence packet before delegation. It should contain the user's approved decisions, verified facts and measurements, exact artifacts, constraints, prior rejected approaches, and genuinely unresolved questions. Prefer a fresh, narrowly scoped planner context over either an empty handoff that repeats discovery or full conversation inheritance that carries irrelevant history. Raw logs and broad retrieval output remain in context-mode or dated evidence; pass derived facts and source locations.

Supervise one active planner at a time. A polling timeout means that no mailbox event arrived during that polling window; it does not establish success, failure, progress, or a transport outage. Use runtime-native agent state, recent observable activity, and actual terminal/tool/configuration errors for health checks. Silence alone must not cause a duplicate spawn, effort escalation, or interruption. Keep the user informed at the host's required cadence, and at least every five minutes when no stricter cadence applies. Use 30 minutes as a provisional floor before a health review, not an automatic kill timer; explicit user cancellation and actual terminal errors remain immediate exceptions.

Benchmark the final `xhigh` behavior on frozen representative micro-plan and bounded full-plan workloads for Claude Code and Codex. Compare checklist completeness, scope discipline, invented surfaces, wall time, observable gaps, tool volume, and unique files read. Retain `max` only when the same material checklist failure recurs on two `xhigh` runs and a matched `max` control resolves it. Consider `high` later only through a paired benchmark. Treat historical and new timing results as dated observations, not consumer invariants.

### Neutral consumer guidance

Update `render_root_guidance()` in `scripts/generate_targets.py` so generated adapters use project-neutral titles and language. Reject only the known authoring-specific phrases in generated roots: `Bootstrap Guidance`, `reusable multi-agent bootstrap`, `In an installed project`, and `Bootstrap maintainers own authoring and regeneration`.

Root `AGENTS.md` is currently Git-tracked and preserved during self-refresh, while root `CLAUDE.md` is ignored and untracked. Force-track the existing `CLAUDE.md` without changing its content and add it beside `AGENTS.md` in `TRACKED_AUTHORING_PATHS`, allowing the existing installer/restorer ownership rules to preserve both files consistently.

### STE-inspired human-facing writing

Evolve `shared/policies/agent-reporting.instructions.md` as the single communication authority; do not create a competing policy file. State explicitly that the project borrows useful principles from ASD-STE100 but does not claim formal compliance.

Define two audiences:

- Human-facing communication optimizes for technical precision and comprehension. This includes answers to the user, plans, architecture explanations, review reports, quality reports, session summaries, and documentation.
- Agent-to-agent status and handoff messages optimize for precision and token efficiency and may default to `caveman full`.

The human-facing standard will require agents to:

- Prefer common words when they are as precise as uncommon words.
- Use one term consistently for one concept and avoid unnecessary synonyms.
- Use short, direct sentences and active voice where practical.
- Avoid idioms, buzzwords, marketing language, and unnecessary abbreviations.
- Define uncommon abbreviations and technical terms when first introduced.
- Keep established software terms when they are the most precise words.
- Split complex explanations into smaller statements.
- Keep code identifiers, API names, commands, file names, logs, errors, structured findings, and quoted external text exact.
- Treat technical precision as more important than vocabulary simplification.

Apply the standard lightly to commit messages and do not impose it on source code or compact internal agent communication. Align canonical agent prompts, generated adapters, README documentation, and validation assertions with this audience boundary. Keep `humanize` optional rather than adding a mandatory rewrite stage.

### Ponytail authority

Use this bounded model:

- The canonical lifecycle becomes `PRE-FLIGHT -> BRANCH -> PLAN -> IMPLEMENT -> VERIFY -> REVIEW -> DOCUMENT -> SCORE -> LEARN -> SESSION LOG -> COMMIT`; Ponytail is no longer a separate phase.
- The coder loads/uses Ponytail once as an implementation discipline: reuse first, prefer native capabilities, and choose the minimum correct solution. Remove the separate mandatory `ponytail-review`/refactor ceremony after coding; retain a lightweight changed-scope self-check followed by re-verification.
- Ponytail review is conditional: require/select it for control-plane or high-risk work and when a diff introduces or substantially changes abstractions, dependencies, architecture, generalized infrastructure, or similar complexity. It is optional for ordinary low-complexity work and unnecessary for documentation-only changes.
- Remove the special hook rule requiring zero Ponytail findings. If Ponytail runs, its findings remain in the unified findings report and obey existing severity gates: CRITICAL blocks commit, MAJOR blocks push, and MINOR is advisory.
- Preserve report-field compatibility where practical, but stop requiring `ponytail_reviewed` and `ponytail_findings` for diffs where the profile is not applicable.
- Add an explicit local interpretation of `minimal`: clarity and maintainability take priority over reducing line count. Minimum means the fewest necessary concepts, dependencies, abstractions, layers, configuration, execution paths, and behaviors—not the fewest physical lines.

## Non-Goals

- Do not neutralize or rewrite the authoring repository's root `AGENTS.md` or `CLAUDE.md`.
- Do not change the GitHub Copilot planner model, add a second planner profile, or add automatic duplicate/max retries because a planner is silent.
- Do not encode historical timing, event shapes, or the absence of orphan processes as universal consumer guarantees.
- Do not move either planner to `high` by default without a later paired benchmark, or build a new benchmark framework when small frozen workloads and existing evidence records suffice.
- Do not redesign the complete generated guidance hierarchy.
- Do not remove, fork, or rewrite the vendored Ponytail skills.
- Do not weaken the ordinary code, architecture, security, tests, documentation, score, or severity gates.
- Do not claim formal ASD-STE100 compliance, add a second writing policy, or mandate `humanize` as a workflow stage.
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

### Phase B: Planner reliability and effort calibration

1. Change `shared/agents/planner/agent.yaml` from `max` to `xhigh` for Claude Code and OpenAI Codex. Preserve Claude `model: opus`, Codex `model: gpt-5.6-sol`, and GitHub Copilot `Claude Opus 4.6`.
2. Update `shared/agents/planner/prompt.md` so explicit artifact lists, supplied evidence, and approved decisions bound exploration. A bounded full-plan revision must not repeat intake or interview questions already answered by the user.
3. Update `shared/agents/orchestrator/prompt.md` to require a curated evidence packet, fresh/minimal scoped delegation when appropriate, one active planner, pending-wait semantics, evidence-based health checks, regular user updates, and a provisional 30-minute health-review floor before interruption absent cancellation or an actual terminal error.
4. Update `scripts/validate_targets.py`, `scripts/check_native_clients.py`, `tests/test_validate_targets.py`, and `tests/test_check_native_clients.py` for `xhigh`, unchanged Copilot intent, evidence-packet delegation, single-planner supervision, pending waits, status cadence, and the interruption floor.
5. Exercise `scripts/generate_targets.py`, regenerate all targets from canonical sources, and refresh the local dogfood overlay only after Phase A has established root-adapter preservation. Do not hand-edit generated `.claude/agents/*.md`, `.codex/agents/*.toml`, or `dist/` files.
6. Benchmark one frozen micro-plan workload and one frozen bounded full-plan workload on Claude Code and Codex. Record wall time, time to first observable activity, largest observable gap, tool volume, unique files read, checklist completeness, invented surfaces, duplicated discovery, and scope expansion.
7. Keep `max` as an exceptional measured override only when the same material checklist failure occurs on two `xhigh` runs and a matched `max` control resolves it. Leave `high` for a later paired benchmark.
8. Verify that Claude's resolved Opus model accepts `xhigh`. If native execution rejects it, record the client version, resolved model, and exact error, then fall back only the Claude planner to `high`; keep Codex at `xhigh` and Copilot unchanged.
9. Update `README.md`, `docs/architecture.md`, `docs/smoke-tests.md`, `docs/native-client-acceptance.md`, and `docs/2026-08-08-codex-routing-compatibility.md` with the current contract. Add `docs/2026-08-09-planner-reliability-calibration.md` for dated benchmark evidence without rewriting historical `max` observations.

Ownership and review:

- `coder`: `shared/agents/planner/agent.yaml`, `shared/agents/planner/prompt.md`, `shared/agents/orchestrator/prompt.md`, `scripts/validate_targets.py`, `scripts/check_native_clients.py`, `tests/test_validate_targets.py`, and `tests/test_check_native_clients.py`; use `.claude/skills/ponytail/SKILL.md` in `full` mode plus `.claude/skills/code-style/SKILL.md` and `.claude/skills/testing-patterns/SKILL.md` where applicable.
- `verifier`: target generation, dogfood refresh, native compatibility, frozen workloads, and full verification using `.claude/skills/run-tests/SKILL.md`.
- `documenter`: the documentation paths in step 9 using `.claude/skills/documentation/SKILL.md`.
- `reviewer`: load `.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`, `.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`, `.claude/review-profiles/config.md`, `.claude/review-profiles/performance.md`, `.claude/review-profiles/documentation.md`, and `.claude/review-profiles/ponytail.md`; run two passes.

Acceptance criteria:

- Canonical and generated Claude planner configuration is `opus`/`xhigh`, or an evidence-backed Claude-only `high` fallback records a native rejection.
- Canonical and generated Codex planner configuration is `gpt-5.6-sol`/`xhigh`; GitHub Copilot remains `Claude Opus 4.6`.
- Generated planner/orchestrator prompts carry the evidence-packet, scoped-delegation, pending-wait, one-planner, health-check, status-update, and interruption-floor contracts.
- Both frozen workloads satisfy every mandatory planning checklist item without invented surfaces or duplicated discovery.
- Timing, silence, and tool-volume results are recorded as observations rather than generalized vendor claims.
- No generic `max` retry, second planner, or unbenchmarked move to `high` is added.
- Existing historical evidence remains explicitly historical.

Primary verification:

```bash
uv run pytest tests/test_validate_targets.py tests/test_check_native_clients.py -q --tb=short
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/install_bootstrap.py . --allow-self --local-only
uv run python scripts/check_runtime.py
```

### Phase C: STE-inspired human-facing writing guidance

1. Correct the central reporting policy's ambiguous scope by defining separate human-facing and agent-to-agent communication modes.
2. Add the project-specific ASD-STE100-inspired rules from the design section, including the no-formal-compliance statement and the technical-precision priority.
3. Apply the human-facing standard strongly to user answers, plans, architecture explanations, review and quality reports, session summaries, and documentation; apply it lightly to commit messages; exempt exact technical material, source code, quoted text, and compact internal communication.
4. Update canonical agent prompts so they point to the single policy without duplicating its rules. Preserve the documenter's existing normal-prose requirement.
5. Update generated guidance and validators to check the audience distinction, the STE-inspired clarity rules, exact-content protection, and policy pointers.
6. Update README documentation and examples to describe the new communication boundary and give at least one jargon-to-clear-prose example.

Acceptance criteria:

- The policy says it is inspired by ASD-STE100 principles and explicitly disclaims formal ASD-STE100 compliance.
- Human-facing communication is explicitly governed by precise, clear, direct, natural prose and the listed terminology, sentence, abbreviation, jargon, and active-voice rules.
- Caveman remains available for internal agent status/handoffs but is not the default for user communication.
- Technical precision explicitly takes priority over simpler vocabulary.
- Code identifiers, API names, commands, file names, logs, errors, structured findings, and quoted text are protected from lossy rewriting.
- No duplicate communication policy or mandatory rewrite step is introduced.
- Canonical sources, generated targets, and validation tests agree on the same audience distinction.

### Phase D: Ponytail authority calibration

1. Remove `PONYTAIL` from the canonical lifecycle in policies, generated root guidance, README documentation, and lifecycle validators.
2. Keep the main Ponytail skill as a once-per-coding-task implementation discipline, but remove the separate mandatory post-implementation `ponytail-review`/refactor invocation. Retain a lightweight changed-scope simplification self-check and re-verification.
3. Add the local definition of minimality that protects clarity and maintainability and rejects line-count minimization.
4. Update reviewer/profile guidance so Ponytail is required for control-plane/high-risk or complexity-expanding changes and optional otherwise.
5. Remove the special zero-Ponytail-findings hook gate while retaining unified severity gates.
6. Make Ponytail-specific report metadata optional when the profile did not run, retaining backward compatibility for existing reports and tools.
7. Update commit/push, report-recording, diff-classification, generated-target, and policy tests for required, optional, advisory, and blocking cases.
8. Update README and architecture/workflow documentation affected by the authority change.

Acceptance criteria:

- The canonical lifecycle contains no standalone Ponytail phase.
- The coder uses the main Ponytail skill once as an implementation discipline; it does not automatically invoke a second standalone Ponytail-review/refactor pass.
- Ponytail remains discoverable and required/selected for the documented high-risk and complexity triggers.
- A MINOR Ponytail finding is recorded but does not block commit or push.
- A Ponytail CRITICAL finding blocks commit and a Ponytail MAJOR finding blocks push through the ordinary severity gates.
- Documentation-only and non-applicable diffs do not require Ponytail metadata.
- Existing valid findings reports remain consumable where compatibility is promised.
- Policies explicitly state that clarity and maintainability outrank line-count reduction and define minimum scope by necessary concepts and behavior.

## Cross-Phase Verification

For every phase:

- Create and approve the matching small plan before implementation.
- Regenerate targets from canonical sources; never hand-edit `dist/`.
- Run focused generator, policy, hook, findings-report, installer, and state-restoration tests affected by that phase.
- Run the full project test, lint, formatting, runtime, generated-wiring, and documentation checks required by repository policy.
- Complete profile-driven review, score, learning, and session-log gates before the atomic phase commit.

Before big-plan closeout:

- Verify all four small plans are complete and committed independently.
- Re-run full target generation and repository verification from a clean worktree.
- Confirm the authoring root file hashes still match the recorded values.
- Confirm generated roots, reporting policy, generated agent prompts, hook behavior, README, and validators express one consistent model.

## Risks and Mitigations

- **Tracking an ignored file is unusual:** keep the current `CLAUDE.md` bytes unchanged and document that this mirrors the existing tracked-root-adapter ownership model for `AGENTS.md`.
- **Lower effort could omit planning details:** require checklist non-regression on frozen workloads and allow `max` only after a repeated material failure that a matched control resolves.
- **Claude's `opus` alias can resolve differently across client versions:** verify `xhigh` natively and allow only an evidence-backed Claude-only `high` fallback.
- **A fixed interruption timer can become stale:** make 30 minutes a provisional health-review floor, never an automatic kill timer, and recalibrate it from dated measurements.
- **Static validation can be mistaken for native proof:** report generated/configuration parity separately from persistent-thread runtime evidence.
- **The planner phase overlaps prompts and validators touched later:** establish root-adapter preservation in Phase A, land the supervision contract in Phase B, and require later phases to preserve it.
- **Audience rules could become subjective:** specify observable audience categories and protect exact technical material explicitly.
- **Removing the special Ponytail gate could hide serious findings:** preserve the ordinary CRITICAL-at-commit and MAJOR-at-push gates for every review profile.
- **Conditional Ponytail use could drift:** centralize triggers in workflow/review guidance and test representative required, optional, and exempt cases.
- **Metadata changes could break old reports:** prefer optional/backward-compatible readers and fixtures rather than deleting fields immediately.
- **Policy and generated output could diverge:** update canonical sources first, regenerate all targets, and validate exact lifecycle/reporting fragments.
