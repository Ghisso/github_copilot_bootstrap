---
name: 2026-08-01_phase-B-codex-state-lifecycle
type: small-plan
parent_plan: ai-state-lifecycle-sync
phase_index: 2
status: complete
closeout_session_log: .claude/session_logs/2026-08-01_ai-state-lifecycle-sync-phase-B.md
---

# Small Plan: 2026-08-01_phase-B-codex-state-lifecycle

## Scope

Replace Codex's concurrent Stop handler list with one sequential wrapper and
add the prompt/session lifecycle boundaries that use Phase A's shared
operations. Enforce Codex's Stop JSON contract and three-second SessionEnd
ceiling with behavioral validation, not loose generated-text checks.

Codex `SessionEnd` is best-effort and may be delayed. This phase deliberately
does not publish from it; the Stop wrapper, UserPromptSubmit retry,
post-commit hook, and manual VS Code push remain the publication paths.

## Ownership

- `coder`: Codex wrapper, generator wiring, validator/runtime-checker updates,
  and lifecycle regressions.
- `verifier`: focused wrapper tests, generated target validation, full quality
  checks, and score.
- `reviewer`: two-pass control-plane/config review.
- `documenter`: Codex lifecycle/output/timeout docs before score.
- `orchestrator`: findings, LEARN/session-log closeout, and commit.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` — `full` mode throughout.
- `.claude/skills/testing-patterns/SKILL.md` — wrapper and generated-config
  behavior tests.
- `.claude/skills/run-tests/SKILL.md` — focused/full verification.
- `.claude/skills/documentation/SKILL.md` — Codex operational docs.
- `.claude/skills/ponytail-review/SKILL.md` — mandatory reduction review.

## Steps

### 1. Add failing Codex wrapper/config contracts

- **Owner:** `coder`
- **Files:** create `tests/test_lifecycle_hooks.py`; modify the Codex hook
  validation inside `scripts/validate_targets.py`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` (`full`) and
  `.claude/skills/testing-patterns/SKILL.md`.
- Build a small reusable test harness that invokes a copied wrapper against
  deterministic child-script fixtures. The fixtures may stand in for child
  process boundaries because wrapper ordering/payload/output—not child Git
  behavior—is the unit under test; Phase A already covers the real sync engine.
- Assert:
  - exact child order: `session-log.sh openai-codex`,
    `stop-session-log-check.sh openai-codex`, `state-sync.sh checkpoint`, then
    `state-sync.sh publish`;
  - every child receives the original hook JSON payload;
  - a child non-zero does not prevent later best-effort steps or final result;
  - stdout parses as exactly one JSON object with no prefix/suffix/plain text,
    while diagnostics may appear on stderr;
  - generated Codex `Stop` has exactly one command handler and references the
    wrapper, not the four child commands;
  - generated `UserPromptSubmit` has one `push` handler, so tracked diagnostics
    written by a failed Stop publication are checkpointed before retry;
  - generated `SessionEnd` has one `checkpoint` handler, timeout exactly `3`,
    and no `publish`/`push` command.
- Keep tests independent of handler array ordering—the array must contain only
  one command where sequencing matters.
- **Verify:** run
  `uv run pytest tests/test_lifecycle_hooks.py -q --tb=short`; preserve the
  failing result before Steps 2-3 and the passing result afterward.

### 2. Implement the minimal Codex Stop wrapper

- **Owner:** `coder`
- **Files:** create `shared/hooks/scripts/codex-stop.sh`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` (`full`).
- Follow the existing hook script style (`bash`, `set -euo pipefail`, sibling
  path resolution, warn-never-fail).
- Consume stdin once and replay the unchanged payload to each existing child
  command sequentially. Keep the four calls literal and visible; do not add a
  generic pipeline/registry abstraction.
- Run every step best-effort. Log a step-specific warning on an unexpected
  non-zero, but continue so a prior committed checkpoint can still publish.
- Route/suppress every child stdout so wrapper stdout cannot be corrupted.
  Preserve child stderr and the existing `hooks-errors.log` diagnostics.
- Finish with one minimal valid Codex Stop JSON object and exit zero in the
  success and child-failure cases.
- Avoid a payload temp file unless shell-variable replay proves incorrect; if
  a temp file becomes necessary, require mode `0600` and a trap that removes it.
- **Verify:**
  `bash -n shared/hooks/scripts/codex-stop.sh` and the focused lifecycle tests.

### 3. Generate the Codex lifecycle events atomically with validation

- **Owner:** `coder`
- **Files:** modify `scripts/generate_targets.py`,
  `scripts/validate_targets.py`, and `scripts/check_runtime.py`.
- **Required Skills:** `.claude/skills/ponytail/SKILL.md` (`full`) and
  `.claude/skills/testing-patterns/SKILL.md`.
- In `render_codex_hooks`:
  - replace the Stop group's three commands with one `codex-stop.sh` command;
  - add one `UserPromptSubmit` group invoking `state-sync.sh push` with a
    bounded network timeout (use `60` unless current generated-schema evidence
    requires a smaller supported value), so a failed Stop publication's
    tracked diagnostics are checkpointed before publication is retried;
  - add one `SessionEnd` group invoking `state-sync.sh checkpoint` with timeout
    exactly `3`;
  - preserve existing SessionStart, PreToolUse, PostToolUse, and PreCompact
    wiring/matchers unchanged.
- Make the new wrapper executable through the existing sorted shared-script
  copy/chmod path. Add it to required hook/runtime file lists.
- Update validator logic that currently requires a direct Stop
  `state-sync.sh push`. Parse the Codex event objects and assert exact handler
  count, command, target-root resolution, operation, and timeouts. Continue to
  reject `upload-bootstrap` and unsupported top-level/schema fields.
- Execute the generated wrapper in validation and parse all of stdout with
  `json.loads`; a valid JSON prefix followed by text must fail.
- Assert operational Codex sync commands have no plain stdout. Retain
  `state-sync.sh` two-copy byte identity and deterministic temp generation.
- **Must not:** change authoring/generated overlays directly or add a Codex
  `SessionEnd` network call.
- **Verify:** run `uv run python scripts/generate_targets.py --all`,
  `uv run python scripts/validate_targets.py`, and
  `uv run python scripts/check_runtime.py`.

### 4. Document the Codex lifecycle contract

- **Owner:** `documenter`
- **Files:** update the relevant Codex/hook sections in `README.md`,
  `docs/architecture.md`, `docs/runtime-checks.md`, `docs/smoke-tests.md`,
  `docs/target-mapping.md`, and `shared/policies/workflow.instructions.md`.
- **Required Skills:** `.claude/skills/documentation/SKILL.md`.
- Explain Stop's turn scope, single-wrapper ordering, the UserPromptSubmit
  checkpoint-plus-publication retry after failed Stop diagnostics,
  local-only/delayed SessionEnd, exact three-second limit, JSON-only Stop
  stdout, error/status recovery, and continued post-commit/manual durability.
- Do not yet document Claude events as implemented; Phase C owns them.
- Keep claims scoped to project hooks and cite the generated paths users can
  inspect. Do not add an external dependency or copy a historical plan into
  living docs.
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
- Review payload handling, stdout isolation, child-failure continuation,
  shell quoting, generated JSON schema, timeout exactness, and accidental
  changes to unrelated Codex guardrails.
- Resolve findings, rerun, document, stage explicit files, persist artifacts,
  close plan/log/LEARN, and commit exactly once.
- **Verify:** run every command in this plan's Verification section, then
  inspect the persisted score/findings JSON and completed session log before
  `git commit`.

## Verification

```bash
bash -n shared/hooks/scripts/state-sync.sh
bash -n shared/hooks/scripts/codex-stop.sh
uv run pytest tests/test_lifecycle_hooks.py tests/test_state_sync.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy scripts/ tests/ --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python .claude/scripts/quality_score.py scripts/ --phase 2026-08-01_phase-B-codex-state-lifecycle --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

## Acceptance Criteria

- Codex Stop has one handler and the wrapper proves exact sequential order.
- Stop stdout is one parseable JSON object under success and child failure;
  no child info text appears there.
- UserPromptSubmit runs `push`, checkpointing tracked diagnostics left by a
  failed Stop publication before retrying publication; after a successful Stop
  it is harmless through Phase A's clean-tree/no-op contract.
- SessionEnd only checkpoints and has timeout `3`; it performs no remote Git
  operation and is documented as delayed/best-effort.
- Existing Codex lifecycle/guardrail hooks remain structurally unchanged.
- Generation and validation are deterministic and green.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved, including zero surviving Ponytail findings
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated before persisted findings/score
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] One atomic Phase B commit created
