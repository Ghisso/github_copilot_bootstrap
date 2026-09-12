---
name: 2026-09-12_phase-B-skill-regression-prevention
type: small-plan
parent_plan: 2026-09-12_skill-library-hardening
phase_index: 2
status: planned
closeout_session_log:
---
# Small Plan: 2026-09-12_phase-B-skill-regression-prevention

## Scope

Add deterministic prevention for objective skill-library regressions after Phase A has established the corrected baseline. The validator must enforce facts that tooling can decide reliably and leave subjective semantic judgments—such as whether a trigger is slightly too broad—to review/deep-audit unless there is a high-confidence mechanical rule.

Integrate the validator into the existing authoring verification path rather than creating a parallel quality system. Finish with the required documentation, memory/LEARN, and stale-claims audit across live advice surfaces.

## Steps

- [ ] **Define the canonical skill validation contract before implementing it.**
  - Add a short authoritative description in the most appropriate existing policy/documentation surface; do not create a second workflow policy.
  - The contract should distinguish:
    - hard deterministic errors;
    - advisory semantic issues for `deep-audit`;
    - generated/runtime targets versus canonical `shared/**` authoring sources.
  - Hard validation should cover only high-confidence invariants such as:
    - valid YAML frontmatter;
    - `name` matches the skill directory name;
    - recognized `visibility`;
    - non-empty routing description for public skills;
    - local relative references resolve when they claim to name repository files;
    - known obsolete bootstrap paths are rejected;
    - required root `SKILL.md` exists;
    - generated targets remain synchronized with canonical sources.
  - Do not hard-fail on arbitrary line count, skill count, or general words like `"any"` without task context.

- [ ] **Create a deterministic skill validator.**
  - Create `scripts/validate_skills.py` unless the existing validation architecture has a clearer established location; follow current script patterns rather than inventing a new framework.
  - Provide a small testable API, for example:
    - `discover_skills(root: Path) -> list[Path]`
    - `validate_skill(skill_dir: Path, repo_root: Path) -> list[Finding]`
    - `validate_all(repo_root: Path) -> ValidationResult`
    - `main() -> int`
  - Use stable finding IDs/messages so tests and CI can assert behavior.
  - Return non-zero only for hard deterministic violations.
  - If advisory findings are emitted, label them clearly and do not make them a hidden closeout gate.
  - Avoid network access and model calls.

- [ ] **Add regression tests for validator behavior and the concrete audit defects.**
  - Add focused tests under the existing `tests/` organization.
  - Cover at minimum:
    - malformed/mismatched skill frontmatter;
    - missing `SKILL.md`;
    - broken local reference detection;
    - obsolete `workspace.md` guidance rejection;
    - canonical/generated synchronization expectations;
    - corrected `np.bool_` example/claim;
    - `run-tests` not masking a failing script;
    - plan-small template no longer containing `quality_score.py` or `Score >= 90`;
    - reviewer MINOR behavior remaining advisory with disposition rather than mandatory fixing.
  - Use fixtures/temporary directories for validator tests; do not mutate real repository state.
  - Do not build a generic code-fence execution engine unless existing repository patterns make that clearly simpler than targeted regression tests.

- [ ] **Extend `deep-audit` with advisory instruction/skill hygiene checks.**
  - Modify `shared/skills/deep-audit/SKILL.md`.
  - Make audit/report the default behavior; do not silently fix repository content unless implementation was requested.
  - Add checks for:
    - suspiciously broad public trigger descriptions;
    - duplicated normative policy;
    - unconditional full-repository/document reads;
    - version-sensitive claims without qualification;
    - project-specific benchmark/timing claims in shared guidance;
    - canonical/generated ownership confusion;
    - stale references to removed scripts, paths, or lifecycle concepts.
  - Keep these semantic checks advisory unless an objective equivalent is already enforced by `validate_skills.py`.

- [ ] **Integrate validation into the existing authoring verification path.**
  - Add `scripts/validate_skills.py` to the existing target/runtime/check pipeline at the narrowest appropriate point.
  - Prefer extending `scripts/check_runtime.py`, `scripts/validate_targets.py`, or their existing test coverage if one already owns repository-authoring validation; do not create a duplicate top-level gate without need.
  - Ensure failures identify the skill path, finding ID, and actionable reason.
  - Regenerate all targets after canonical source changes and confirm the validator handles both authoring and generated layouts correctly where relevant.

- [ ] **Run cross-model-oriented regression review.**
  - Review representative public descriptions and root skill bodies as they will be exposed to:
    - Codex;
    - Claude;
    - Gemini/Antigravity;
    - GitHub Copilot.
  - Confirm no correctness rule relies on one model's autonomous judgment or proprietary routing behavior.
  - Confirm core lifecycle requirements remain directly discoverable while secondary specialist references use progressive disclosure.
  - Treat Astra compatibility as useful but non-normative.

- [ ] **Complete the final documentation, memory/LEARN, and stale-claims audit.**
  - This is the final phase in the big plan, so inspect every live-advice surface required by the current `plan-decomposition` contract:
    - root guidance;
    - `docs/`;
    - shared policies;
    - shared skills;
    - shared templates;
    - shared agents/review profiles;
    - state READMEs;
    - `.claude/MEMORY.md`.
  - Correct or supersede claims invalidated by either phase.
  - Pay specific attention to:
    - numeric-score language;
    - obsolete `workspace.md` paths;
    - skill authoring/generated ownership;
    - automatic routing rules;
    - testing breadth;
    - review severity behavior;
    - onboarding `"read everything"` expectations.
  - Leave dated/closed historical records unchanged unless the repository's existing errata rules require a correction artifact.
  - In the closeout session log, add the exact heading:
    - `## Stale-claims surfaces checked`
  - Under that heading, record every audited surface and its outcome.

## Verification

Use focused validator tests first, then run the complete authoring/runtime verification:

```bash
uv run python scripts/validate_skills.py
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run ruff check .
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run python .claude/scripts/verify.py phase --format json --persist
uv run python .claude/scripts/verify.py closeout --format json --persist
```

The phase is not complete unless the new validator proves the canonical skill tree is clean, generated targets are synchronized, and the final stale-claims audit is recorded.

## Closeout Checklist

- [ ] `validate_skills.py` passes on the canonical skill tree
- [ ] Validator regression tests cover hard rules and the confirmed audit regressions
- [ ] Generated targets validate and runtime checks pass
- [ ] Review findings resolved under canonical severity rules
- [ ] Documentation updated or explicitly marked not applicable with a reason
- [ ] LEARN entries saved or a no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Closeout session log contains non-empty `## Stale-claims surfaces checked`
- [ ] No subjective semantic heuristic was accidentally promoted to a brittle hard gate without evidence

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later. Set `status: paused`, record the required pause fields, and create a PAUSED session log. A checkpoint preserves incomplete work and does not complete or advance the phase.
