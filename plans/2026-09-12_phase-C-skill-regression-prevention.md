---
name: 2026-09-12_phase-C-skill-regression-prevention
type: small-plan
parent_plan: 2026-09-12_skill-library-hardening
phase_index: 3
status: complete
closeout_session_log: .claude/session_logs/2026-09-12_phase-C-skill-regression-prevention.md
---
# Small Plan: 2026-09-12_phase-C-skill-regression-prevention

## Scope

Add deterministic prevention for objective skill-library regressions, now that
Phases A and B have established the corrected baseline. Validation must
enforce only facts that tooling can decide reliably, and leave subjective
judgments—such as whether a trigger is slightly too broad—to review and the
advisory `deep-audit` path.

This phase extends the gate that already owns skill validation rather than
adding a parallel one. `scripts/validate_targets.py:8131-8158` already
validates skill frontmatter across `shared/skills/*/SKILL.md`: recognized
`visibility`, non-empty description, and no duplicate descriptions (duplicates
break description-match loading). The code records at
`scripts/validate_targets.py:7535` that this integrity check happens once, in
`validate_docs_parity`, alongside the other named-inventory checks. A separate
`scripts/validate_skills.py` would duplicate that owner and split the contract
across two gates.

This is the final phase in the big plan, so it also completes the required
documentation, memory, LEARN, and stale-claims audit.

## Steps

- [x] **Define the validation contract before implementing it.**
  - Add a short authoritative description to the most appropriate existing
    policy or documentation surface. Do not create a second workflow policy.
  - The contract must distinguish three categories:
    - hard deterministic errors, which fail the gate;
    - advisory semantic issues, which route to `deep-audit`;
    - generated runtime targets versus canonical `shared/**` authoring
      sources, which have different rules.
  - Hard validation covers only high-confidence invariants:
    - valid YAML frontmatter;
    - `name` matches the skill directory name;
    - recognized `visibility`;
    - non-empty routing description for public skills;
    - no duplicate descriptions;
    - required root `SKILL.md` exists;
    - local relative references resolve when they claim to name repository
      files;
    - generated targets stay synchronized with canonical sources.
  - Do not hard-fail on line count, skill count, or general words such as
    "any" without task context.
  - Do not add a rule that rejects `.claude/instructions/workspace.md` as an
    obsolete path. It is a live generated file required by
    `scripts/generate_targets.py`, `scripts/validate_targets.py`, and
    `scripts/install_bootstrap.py`. If Phase B settled on a preferred
    canonical name, any rule here must target only obsolete *authoring
    guidance* references, and must not match generator code, generated
    outputs, test fixtures, or historical records.

- [x] **Extend the existing validator rather than creating a new one.**
  - Modify `scripts/validate_targets.py`, extending the skill-integrity block
    at lines 8131-8158 and following the surrounding `check(...)` and `errors`
    patterns already in that file.
  - If the added rules make that block unwieldy, extract a small pure
    validation helper that `validate_targets.py` calls, keeping a single
    entry point and a single gate. Do not add a second top-level command.
  - Use stable finding identifiers and messages so tests and continuous
    integration can assert on behavior.
  - Failures must identify the skill path, the finding identifier, and an
    actionable reason.
  - Return non-zero only for hard deterministic violations. If advisory
    findings are emitted, label them clearly and do not let them become a
    hidden closeout gate.
  - Avoid network access and model calls.
  - This modifies a script, so it is control-plane work. Apply the required
    review profiles: `code`, `architecture`, `security`, `tests`, and
    `ponytail`.

- [x] **Add regression tests for the validator and the corrected defects.**
  - Add focused tests under the existing `tests/` organization, following the
    established fixture patterns.
  - Cover the validator's own behavior:
    - malformed or mismatched skill frontmatter;
    - missing `SKILL.md`;
    - broken local reference detection;
    - duplicate description detection;
    - canonical-versus-generated synchronization expectations.
  - Cover the Phase A and Phase B corrections:
    - the corrected `np.bool_` claim;
    - `run-tests` not masking a failing example command;
    - the compression detector refusing a `shared/skills/**/SKILL.md` target;
    - `code-review` MINOR behavior remaining advisory with an explicit
      disposition rather than mandatory fixing;
    - `UPSTREAM.md` describing the fork rather than claiming formatting-only
      changes;
    - `data-analysis` still present.
  - Match the check to what can actually be proven. Most of these skills are
    prose, so the honest regression check is a targeted structural or textual
    assertion. Do not describe such a test as proving runtime behavior.
    A test may only assert runtime behavior where a real executable helper
    exists, as it does for `caveman-compress/scripts/detect.py`.
  - The numpy claim is a special case: numpy is not installed in this
    repository's environment, so a runtime assertion would require adding a
    dependency, which is itself a control-plane change. Default to a textual
    assertion on the corrected claim, and record that limitation in the test.
  - Use fixtures and temporary directories for validator tests; do not mutate
    real repository state.
  - Do not build a generic code-fence execution engine unless existing
    repository patterns make that clearly simpler than targeted tests.

- [x] **Extend `deep-audit` with advisory hygiene checks.**
  - Modify `shared/skills/deep-audit/SKILL.md`.
  - Make audit and report the default behavior; do not silently fix
    repository content unless implementation was requested.
  - Add advisory checks for:
    - suspiciously broad public trigger descriptions, excluding those that
      match a mandate the repository states;
    - duplicated normative policy;
    - unconditional full-repository or full-document reads;
    - version-sensitive claims without qualification;
    - project-specific benchmark or timing claims in shared guidance;
    - canonical-versus-generated ownership confusion;
    - stale references to removed scripts, paths, or lifecycle concepts.
  - Feed in the borderline routing cases Phase B recorded.
  - Keep these checks advisory unless an objective equivalent is already
    enforced in `validate_targets.py`.

- [x] **Run a cross-model regression review.**
  - Review representative public descriptions and root skill bodies as they
    are exposed to Codex, Claude, Gemini/Antigravity, and GitHub Copilot.
  - Confirm no correctness rule depends on one model's autonomous judgment or
    proprietary routing behavior.
  - Confirm core lifecycle requirements stay directly discoverable while
    secondary specialist references use progressive disclosure.
  - Treat Astra compatibility as useful but non-normative.

- [x] **Complete the final documentation, memory, LEARN, and stale-claims audit.**
  - This is the final phase in the big plan, so inspect every live-advice
    surface required by the current `plan-decomposition` contract:
    - root guidance;
    - `docs/`;
    - shared policies;
    - shared skills;
    - shared templates;
    - shared agents and review profiles;
    - state READMEs;
    - `.claude/MEMORY.md`.
  - Correct or supersede claims invalidated by any of the three phases.
  - Pay specific attention to:
    - skill authoring versus generated ownership;
    - the vendored Ponytail divergence and the `v4.9.0` survey result;
    - automatic routing rules;
    - testing breadth;
    - review severity behavior;
    - onboarding "read everything" expectations.
  - Also record the three audit claims this plan rejected, so a future audit
    does not resurrect them: the already-removed numeric-score lifecycle, the
    supposedly obsolete `workspace.md`, and the supposedly over-broad Ponytail
    descriptions.
  - Leave dated and closed historical records unchanged unless the
    repository's existing errata rules require a correction artifact.
  - In the closeout session log, add the exact heading
    `## Stale-claims surfaces checked` and record every audited surface and
    its outcome underneath it. `verify.py`'s closeout gate requires that
    heading, non-empty, because this is the last phase in the big plan.

## Verification

Generation runs before validation, so the validators inspect a current tree:

```bash
uv run python .claude/scripts/verify.py fast --format text     # during IMPLEMENT
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
uv run ruff format --check shared scripts tests
uv run python .claude/scripts/verify.py phase --format json --persist
uv run python .claude/scripts/verify.py closeout --format json --persist
```

The phase is not complete unless the extended validator proves the canonical
skill tree is clean, generated targets are synchronized, and the final
stale-claims audit is recorded.

## Closeout Checklist

- [x] Extended `validate_targets.py` passes on the canonical skill tree
- [x] No second skill-validation gate was introduced
- [x] Regression tests cover the hard rules and the corrected defects
- [x] Each test asserts only what it can actually prove, with prose checks labeled as such
- [x] Generated targets validate and runtime checks pass
- [x] Verification passed (`verify phase` then `verify closeout` PASS)
- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Closeout session log contains non-empty `## Stale-claims surfaces checked`
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Every surviving MINOR has an explicit disposition and non-empty reason
- [x] No subjective heuristic was promoted to a hard gate without evidence

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume
later. Set `status: paused`, record the three pause fields, and create a
session log with `**Status:** PAUSED`. A checkpoint preserves incomplete work
and does not complete or advance the phase.
