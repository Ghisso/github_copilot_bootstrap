---
name: 2026-09-10_phase-D-shell-classifier-runtime-guidance
type: small-plan
parent_plan: consumer-lifecycle-friction-hardening
phase_index: 5
status: complete
closeout_session_log: .claude/session_logs/2026-09-11_consumer-lifecycle-friction-hardening-phase-D-closeout.md
---

# Small Plan: Phase D — Shell Classifier and Final Runtime Guidance

## Scope

Reduce false fail-closed results for safe heredocs and process substitutions
without treating their inner content as harmless prose. Extend the existing
standard-library classifier rather than adding a shell dependency or a second
policy engine. Finish with generated-consumer acceptance and the required
repository-wide documentation, memory, and LEARN audit.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` in `full` mode
- `.claude/skills/code-style/SKILL.md`
- `.claude/skills/testing-patterns/SKILL.md`
- `.claude/skills/documentation/SKILL.md`

## Review Profiles

- `code`
- `architecture`
- `security`
- `tests`
- `ponytail`
- `documentation`

## Steps

1. **Capture the reported false positives and security controls first.**
   Owner: `coder`.
   Add failing tests in `tests/test_hook_gates.py` for a read-only process
   substitution and a data heredoc containing an unmatched apostrophe. Pair
   every allowed case with a protected-write control: a mutator inside process
   substitution, a shell heredoc that writes `.env` or hook files, an
   interpreter heredoc using `open(..., "w")` or `Path.write_text`, a heredoc
   redirected to a protected target, nested substitutions, and malformed or
   unterminated delimiters. Assert normal policy denials use reasoned JSON and
   malformed syntax retains the infrastructure fail-closed result.

2. **Parse process substitutions as executable nested commands.**
   Owner: `coder`.
   Extend `shared/hooks/scripts/protect-files.py` with the minimum balanced,
   quote-aware extraction needed for `<(...)` and `>(...)`. Replace each
   extracted construct with an inert placeholder for outer tokenization, then
   recursively classify its inner command and merge confirmed and uncertain
   targets. Preserve nesting, working-directory resolution, variable handling,
   and redirection semantics. An unbalanced or ambiguous construct must remain
   fail-closed. Do not infer safety merely from a read-only outer command.

3. **Separate heredoc data from executable heredoc input.**
   Owner: `coder`.
   Add a line-oriented, quote-aware heredoc extractor supporting the ordinary
   `<<WORD`, quoted delimiter, and `<<-WORD` forms needed by repository and
   consumer commands. Remove heredoc bodies from outer `shlex` tokenization so
   prose punctuation and apostrophes cannot corrupt parsing. Continue to
   classify the outer command and redirect targets. For shell or interpreter
   consumers, recursively classify or apply the existing protected-literal and
   opaque-write checks to the body. For known data-only consumers, treat the
   body as data, not filesystem operands. Unknown consumers with protected
   evidence remain conservative. Missing or ambiguous delimiters fail closed.

4. **Preserve the policy boundary across native clients.**
   Owner: `coder`.
   Extend `scripts/validate_targets.py` and target-generation tests so GitHub
   Copilot, Claude Code, Codex, and Google Antigravity copies run the same
   positive and negative corpus with bare system Python 3.9 compatibility.
   Keep current target-specific hook-file `deny` versus `ask` behavior and all
   protected path categories unchanged. Compile standalone hook Python under
   an available Python 3.9 runtime where CI provides one.

5. **Update guidance for supported complex commands.**
   Owner: `documenter` after code review converges.
   Correct live shell-safety guidance and any MEMORY advice superseded by the
   new supported forms. Continue to recommend a script file for complex loops,
   functions, or constructs the lightweight parser still cannot model. State
   that support for heredoc/process-substitution syntax does not weaken nested
   protected-write detection.

6. **Run generated consumer acceptance for the complete plan.**
   Owner: `coder`.
   Generate a fresh consumer and exercise: planned-to-active transitions;
   annotated phase inventory; closeout with an `-F -` commit; native
   post-commit advancement; nested state checkpoint; restored ignored root
   adapters after session-start pull; safe process substitution and heredoc;
   blocked protected writes inside both constructs; and final push against the
   last completed receipt. No manual state edit, bypass, or receipt refresh is
   allowed in the positive path.

7. **Perform the standing final-phase stale-claims audit.**
   Owner: `documenter` after code review converges.
   Sweep root guidance (`CLAUDE.md`, `AGENTS.md`, `README.md`), `docs/` except
   dated records, shared policies, skills, templates, agents, review profiles,
   state READMEs, and `.claude/MEMORY.md` for claims invalidated by any phase of
   this plan. Correct or supersede live claims. Leave archived plans, dated
   design narratives, and receipt-bound session logs unchanged; create a
   sibling errata file only when an unbound closed log would actively mislead.
   Record every surface and outcome under the exact heading
   `## Stale-claims surfaces checked` in this phase's closeout session log.

## Acceptance Criteria

- [x] Safe read-only process substitutions and data heredocs no longer fail because of parser limitations.
- [x] Protected writes inside process substitutions, executable heredocs, interpreter heredocs, and outer redirections are still denied.
- [x] Nested, quoted, tab-stripped, malformed, and unterminated cases have explicit regression coverage.
- [x] No external shell-parser dependency or parallel protection engine is added.
- [x] Standalone hooks remain compatible with Python 3.9.
- [x] All native targets receive identical classifier behavior.
- [x] A fresh generated consumer completes the full lifecycle and terminal push without manual recovery.
- [x] The final closeout log contains a complete `## Stale-claims surfaces checked` audit.

## Verification

```bash
uv run pytest tests/test_hook_gates.py tests/test_lifecycle_hooks.py tests/test_validate_targets.py tests/test_install_bootstrap.py -q
python3 -m py_compile shared/hooks/scripts/protect-files.py
bash -n shared/hooks/scripts/protect-files.sh shared/hooks/scripts/pretool-bash-guard.sh
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q
uv run ruff check shared scripts tests
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run python .claude/scripts/verify.py phase --format json --persist
uv run python .claude/scripts/verify.py closeout --format json --persist
```

## Closeout Checklist

- [x] Verification passed (`verify phase` PASS)
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record `paused_at`, `paused_reason`, and
`pause_session_log`, and keep the big plan `in-progress` with this same
`current_phase`. Resume this file rather than creating a replacement phase.

