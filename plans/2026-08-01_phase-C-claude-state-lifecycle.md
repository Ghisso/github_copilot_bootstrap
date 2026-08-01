---
name: 2026-08-01_phase-C-claude-state-lifecycle
type: small-plan
parent_plan: ai-state-lifecycle-sync
phase_index: 3
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-01_phase-C-claude-state-lifecycle

## Scope

Give Claude Code the same ordered Stop checkpoint/publication guarantee, plus
publication at UserPromptSubmit, a local StopFailure checkpoint, and a
SessionEnd checkpoint+best-effort publish bounded by Claude's 60-second project
hook ceiling. The generated `.claude/settings.json` is shared by Claude CLI and
the Claude runtime bundled with VS Code, so this is one wiring surface.

## Ownership

- `coder`: Claude wrapper, generator/validator/runtime-checker updates, and
  extension of the lifecycle regression harness.
- `verifier`: focused and full checks plus score.
- `reviewer`: two-pass control-plane/config review.
- `documenter`: Claude CLI/VS Code lifecycle documentation before score.
- `orchestrator`: findings, LEARN/session-log closeout, and commit.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` — `full` mode throughout.
- `.claude/skills/testing-patterns/SKILL.md` — orchestration/config regressions.
- `.claude/skills/run-tests/SKILL.md` — focused/full verification.
- `.claude/skills/documentation/SKILL.md` — shared Claude settings/runtime docs.
- `.claude/skills/ponytail-review/SKILL.md` — mandatory reduction review.

## Steps

### 1. Extend the lifecycle contracts for Claude

- **Owner:** `coder`
- **Files:** modify `tests/test_lifecycle_hooks.py` and the Claude settings
  validation in `scripts/validate_targets.py`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` (`full`) and
  `.claude/skills/testing-patterns/SKILL.md`.
- Add initially failing cases for:
  - exact Claude Stop child order: `session-log.sh claude-code`,
    `stop-session-log-check.sh claude-code`, `state-sync.sh checkpoint`, then
    `state-sync.sh publish`;
  - original payload replay to every child and continuation after one child
    fails;
  - no plain wrapper stdout (diagnostics belong on stderr; Claude has no need
    for Codex's final `{}`);
  - one generated Stop command referencing `claude-stop.sh`;
  - one `UserPromptSubmit` command invoking `publish` with timeout `60`;
  - one `StopFailure` command invoking local `checkpoint` and no publication;
  - one `SessionEnd` command invoking the `push` compatibility composition
    (checkpoint then publish) with timeout exactly `60`;
  - no event contains separate checkpoint/publish handlers whose runtime
    concurrency could reorder them.
- Parse the generated settings structure; do not satisfy the test with global
  text substrings.
- **Verify:** run
  `uv run pytest tests/test_lifecycle_hooks.py -q --tb=short`; preserve the
  failing result before Steps 2-3 and the passing result afterward.

### 2. Implement the minimal Claude Stop wrapper

- **Owner:** `coder`
- **Files:** create `shared/hooks/scripts/claude-stop.sh`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` (`full`).
- Mirror the Codex wrapper's small, literal sequencing and payload replay, but
  hard-code/use the Claude target identifier and emit no Codex JSON response.
- Child non-zero statuses warn with target/step context and do not short-circuit
  later checkpoint/publication. Wrapper exit remains zero.
- Route any child routine output to stderr so Claude responses cannot acquire
  accidental hook chatter. Continue using the shared `hooks-errors.log` for
  failures.
- Keep the wrappers separate rather than introducing a cross-runtime
  parameterized framework; their output contracts are materially different.
- **Verify:**
  `bash -n shared/hooks/scripts/claude-stop.sh` and focused lifecycle tests.

### 3. Generate Claude prompt/failure/session lifecycle wiring

- **Owner:** `coder`
- **Files:** modify `scripts/generate_targets.py`,
  `scripts/validate_targets.py`, and `scripts/check_runtime.py`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` (`full`) and
  `.claude/skills/testing-patterns/SKILL.md`.
- In `render_claude_settings`:
  - replace the Stop command list with one `claude-stop.sh` command, retaining
    the established long Stop timeout budget;
  - add `UserPromptSubmit` -> one `state-sync.sh publish`, timeout `60`;
  - add `StopFailure` -> one `state-sync.sh checkpoint`, using the existing
    normal short command timeout unless generated-schema evidence requires an
    explicit smaller supported value;
  - add `SessionEnd` -> one `state-sync.sh push`, timeout exactly `60`;
  - preserve SessionStart, PreToolUse, PostToolUse, and PreCompact unchanged.
- A SessionEnd `push` is intentionally one command: Phase A defines its internal
  checkpoint-before-publish order, so Claude cannot run those operations
  concurrently.
- Add the wrapper to required generated/runtime script lists and executable
  checks. Update old direct-Stop-push assertions to the exact new lifecycle
  contract while retaining no-HF-upload, root-resolution, target-ID, and
  deterministic-generation checks.
- Run the generated wrapper behaviorally in `validate_targets.py`; CI must not
  rely only on pytest or static text.
- **Must not:** add a second Claude settings file for VS Code, exceed 60 seconds
  on SessionEnd, or make a StopFailure network call.
- **Verify:** run `uv run python scripts/generate_targets.py --all`,
  `uv run python scripts/validate_targets.py`, and
  `uv run python scripts/check_runtime.py`.

### 4. Document Claude CLI and VS Code behavior

- **Owner:** `documenter`
- **Files:** update `README.md`, `docs/architecture.md`,
  `docs/runtime-checks.md`, `docs/smoke-tests.md`, `docs/target-mapping.md`, and
  `shared/policies/workflow.instructions.md` where cross-runtime lifecycle is
  described.
- **Required Skills:** `.claude/skills/documentation/SKILL.md`.
- State that Claude VS Code bundles the Claude runtime and reads the same
  `.claude/settings.json`; no duplicate adapter is installed.
- Document Stop as turn-scoped, prompt publication as retry, StopFailure local
  checkpoint, SessionEnd checkpoint+best-effort publication, timeout `60`,
  local-commit preservation on timeout/network failure, status/error commands,
  and continued post-commit/manual durability.
- Reconcile any Phase B Codex-only wording into a compact comparison table or
  flow without duplicating the entire lifecycle in multiple sections.
- **Verify:** regenerate and run `uv run python scripts/validate_targets.py` so
  documentation-parity checks evaluate the final wording.

### 5. Verify, review, score, and close the phase

- **Owner:** `verifier`, then `reviewer`, then `orchestrator`.
- **Required Skills:** `.claude/skills/run-tests/SKILL.md`,
  `.claude/skills/code-review/SKILL.md`,
  `.claude/skills/ponytail-review/SKILL.md`,
  `.claude/skills/learn/SKILL.md`, and `.claude/skills/commit/SKILL.md`.
- **Review Profiles:**
  - `.claude/review-profiles/code.md`
  - `.claude/review-profiles/architecture.md`
  - `.claude/review-profiles/security.md`
  - `.claude/review-profiles/tests.md`
  - `.claude/review-profiles/config.md`
  - `.claude/review-profiles/ponytail.md`
  - `.claude/review-profiles/documentation.md`
- Review exact timeout support, concurrent-handler elimination, failure-path
  local durability, shell quoting/payload handling, CLI/VS Code settings parity,
  and wrapper duplication size.
- Resolve, rerun, document, stage, persist findings/score, close plan/log/LEARN,
  and commit exactly once.
- **Verify:** run every command in this plan's Verification section, then
  inspect the persisted score/findings JSON and completed session log before
  `git commit`.

## Verification

```bash
bash -n shared/hooks/scripts/state-sync.sh
bash -n shared/hooks/scripts/codex-stop.sh
bash -n shared/hooks/scripts/claude-stop.sh
uv run pytest tests/test_lifecycle_hooks.py tests/test_state_sync.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy scripts/ tests/ --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python .claude/scripts/quality_score.py scripts/ --phase 2026-08-01_phase-C-claude-state-lifecycle --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

## Acceptance Criteria

- Claude Stop has one handler and wrapper order/payload/continuation are proven.
- UserPromptSubmit publishes pending committed state.
- StopFailure checkpoints locally and performs no remote Git operation.
- SessionEnd is one checkpoint+publish composition with timeout `60`; a failed
  publication leaves the checkpoint safe for a later retry.
- Claude CLI and VS Code behavior comes from one generated settings file.
- Codex contracts from Phase B and all unrelated Claude guardrails remain green.
- Generation remains deterministic.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved, including zero surviving Ponytail findings
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated before persisted findings/score
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] One atomic Phase C commit created
