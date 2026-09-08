---
name: 2026-09-08_phase-A-language-reporting-reminder-hardening
type: small-plan
parent_plan: language-reporting-reminder-hardening
phase_index: 1
status: complete
paused_at: 2026-09-08T14:39:16Z
paused_reason: User requested a stop because session usage was nearly exhausted
pause_session_log: .claude/session_logs/2026-09-08_language-reporting-reminder-hardening.md
closeout_session_log: .claude/session_logs/2026-09-09_language-reporting-reminder-hardening.md
---

# Small Plan: 2026-09-08_phase-A-language-reporting-reminder-hardening

## Scope

Strengthen the canonical human-facing reporting policy and add short context
reminders for Claude Code and OpenAI Codex at the beginning of a prompt and near
the end of long implementation turns. Keep one phase because the policy,
generated hook wiring, executable script, validation, and documentation form one
contract and should not be delivered separately.

This is control-plane work. Use the code, architecture, security, tests, and
Ponytail review profiles. Preserve the existing Copilot and Google Antigravity
hook surfaces exactly.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` in `full` mode during implementation.
- `.claude/skills/testing-patterns/SKILL.md` for focused regression tests.
- `.claude/skills/code-style/SKILL.md` for changed Python validation code.
- `.claude/skills/documentation/SKILL.md` for current documentation.
- `.claude/skills/commit/SKILL.md` only after all closeout gates pass.

## Primary Files

Create:

- `shared/hooks/scripts/reporting-reminder.sh`
- A focused test module under `tests/` only if existing validator coverage cannot
  express the behavioral cases clearly.

Modify:

- `shared/policies/agent-reporting.instructions.md`
- `scripts/generate_targets.py`
- `scripts/validate_targets.py`
- `docs/architecture.md`
- `docs/runtime-checks.md`
- `docs/smoke-tests.md`
- `docs/target-mapping.md` if its hook matrix needs the new Claude/Codex entries
- `README.md` only if its current hook or reporting summary becomes incomplete

Regenerate `dist/multi-agent/**`; never edit it directly. Modify
`scripts/check_runtime.py` only if inspection proves that its generated runtime
inventory does not already discover the new script.

## Steps

- [ ] **1. Strengthen the single reporting authority.**
  - Owner: `coder`.
  - Modify `shared/policies/agent-reporting.instructions.md`.
  - Add a short “violations to recognize” section with concrete corrections:
    - a bare label such as `P1`, `G2`, or `Phase Q` must be accompanied by what
      it represents;
    - an uncommon abbreviation such as `YAGNI` must be expanded or omitted;
    - an idiom such as “say the word” or “arena” must be replaced with direct
      wording;
    - each offered option must state its practical result or tradeoff.
  - Keep exact identifiers, commands, paths, logs, structured findings, source
    code, and quotations unchanged.
  - Preserve the existing distinction between normal user-facing prose and
    compact internal handoffs.
  - Do not duplicate the full policy into root guidance or agent prompts.

- [ ] **2. Add the canonical non-blocking reminder script.**
  - Owner: `coder`.
  - Create `shared/hooks/scripts/reporting-reminder.sh` using Bash and existing
    helpers; add no dependency.
  - Accept an explicit mode and provider argument rather than inferring the
    runtime from paths. Supported providers are `claude-code` and
    `openai-codex`.
  - Prompt mode must drain or safely read hook input and emit exactly one valid
    JSON object whose event is `UserPromptSubmit` and whose only model-facing
    content is the compact reminder.
  - Late-report mode must parse the `PostToolUse` Bash payload using existing
    helper patterns. Emit exactly one reminder only when the completed command
    is a recognized final lifecycle boundary. Begin with the smallest justified
    set: `verify.py closeout`, findings persistence when it is the last closeout
    operation, and a phase-completion commit.
    Use tokenized or existing command-classification helpers where available;
    do not rely on an unrestricted substring that can match quoted prose.
  - Recognize the two script boundaries from command shape only. This
    repository has no verified tool-outcome field in a Claude Code or OpenAI
    Codex hook payload, and a false match costs one short advisory sentence, so
    do not add outcome correlation for them. Confirm the phase-completion commit
    against committed plan state, which the existing helper patterns already
    support.
  - A normal non-match must emit no standard output and exit zero.
  - Malformed payloads, unknown modes/providers, unavailable optional helpers,
    and internal errors must warn on standard error, emit no blocking decision,
    and exit zero.
  - Keep the reminder within a validator-owned byte ceiling and no more than
    three short sentences. The script must not read assistant transcripts or
    call a model.

- [ ] **3. Wire only the supported runtime boundaries.**
  - Owner: `coder`.
  - Modify `render_claude_settings()` and `render_codex_hooks()` in
    `scripts/generate_targets.py`.
  - Add prompt mode to each existing `UserPromptSubmit` group without removing,
    reordering unsafely, or weakening `state-sync.sh push`.
  - Add late-report mode to each existing Bash `PostToolUse` group through
    `run-hook.sh`. Preserve branch-state, commit-closeout, and Context Mode
    handlers.
  - Confirm how each runtime aggregates multiple handler outputs. If runtime
    evidence shows that two context-producing handlers in one group conflict,
    adjust grouping with the minimum provider-specific change and record the
    evidence in the closeout log.
  - Do not change `shared/hooks/hooks.json`, `render_antigravity_hooks()`, or any
    Google Antigravity bridge.
  - Do not wire `PreCompact`, periodic `PostToolUse`, or Stop-based rewriting.

- [ ] **4. Add structural and behavioral regression coverage.**
  - Owner: `coder`.
  - Extend `scripts/validate_targets.py` and focused tests.
  - Prove that generated Claude and Codex configurations retain every existing
    handler and add exactly the intended reminder invocations.
  - Execute the generated script with representative Claude and Codex payloads
    and assert:
    - prompt mode emits one parseable object with the correct event and exact
      bounded reminder;
    - recognized late commands emit one `PostToolUse` context object;
    - ordinary Bash commands emit no output;
    - malformed input and unknown arguments warn but never block;
    - standard output never contains diagnostics or more than one JSON object.
  - Assert that the canonical script is present and executable in generated
    output and installed runtime inventory.
  - Assert unchanged Copilot and Antigravity event sets and the absence of
    `GEMINI.md`, `.gemini/`, or a Gemini renderer.
  - Add a determinism assertion if the existing generated-target validation
    does not already cover the changed files.

- [ ] **5. Regenerate, install, and run proportional native acceptance.**
  - Owner: `orchestrator` for authoritative verification; route failures to the
    coder.
  - Generate and validate the target before installing it locally.
  - Run the complete repository test, Ruff, formatting, and Mypy commands shown
    below.
  - Refresh the dogfood installation with `--allow-self --local-only`, then run
    `scripts/check_runtime.py`; do not repair runtime drift by deleting
    consumer-owned state.
  - When authenticated Claude and Codex clients are available, run a bounded
    acceptance check that proves prompt-start injection, late-report injection,
    non-blocking failure behavior, and no duplicate user-visible reminder. Mark
    unavailable native checks as dated `UNVERIFIED`; do not replace them with a
    synthetic pass.
  - Record reminder byte size, number of injections in the bounded workflow, and
    observed context output. Do not claim general token savings or language
    quality improvement from a structural test.

- [ ] **6. Update current guidance and close out the only phase.**
  - Owner: `documenter`, followed by orchestrator closeout.
  - Document that static reporting guidance covers all four supported targets,
    while recurring prompt and late-turn reminders apply only to Claude Code and
    Codex.
  - Document the selected late lifecycle commands, reminder byte ceiling,
    non-blocking behavior, and why periodic, Stop, PreCompact, Copilot, and
    Antigravity reminders are out of scope for this version.
  - Audit README, current docs, shared policies, skills, templates, agents,
    review profiles, state READMEs, project context, and `.claude/MEMORY.md` for
    stale reporting or target-support claims. Preserve dated plans and completed
    session logs unless they actively mislead and no receipt binds them.
  - Record every audited surface and its outcome under
    `## Stale-claims surfaces checked` in the completed closeout session log.
  - Record either reusable `[LEARN]` entries or the exact approved no-lessons
    marker.

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

After documentation, findings, LEARN, and the completed session log are current:

```bash
uv run python .claude/scripts/verify.py closeout --format json --persist
```

## Review Profiles

- `code`: shell behavior, generator changes, and command classification.
- `architecture`: one-policy authority and provider-boundary consistency.
- `security`: payload parsing, shell quoting, non-blocking failures, and command
  recognition.
- `tests`: generated behavior, negative cases, and native acceptance limits.
- `ponytail`: recurring-token cost, unnecessary state, duplicated policy, and
  avoidable hook complexity.
- `documentation`: current target mapping and operational guidance.

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
