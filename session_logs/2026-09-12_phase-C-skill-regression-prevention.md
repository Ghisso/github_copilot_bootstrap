# Session: Skill-library regression prevention and the plan-wide stale-claims audit

**Date:** 2026-09-12
**Plan:** `.claude/plans/2026-09-12_phase-C-skill-regression-prevention.md`
**Status:** COMPLETED

## Goal

Add deterministic prevention for objective skill-library regressions inside the
gate that already owns skill validation, add regression tests pinning the
Phase A and Phase B corrections, extend `deep-audit` with advisory hygiene
checks, and complete the documentation, memory, LEARN, and stale-claims audit
required of the big plan's final phase.

## Work Log

- **IMPLEMENT** - Steps 1-4 delegated to `coder`. It extended
  `scripts/validate_targets.py` rather than creating a second gate, extracting
  the skill-integrity block into `shared_skill_integrity_errors()` called from
  the existing `validate_docs_parity` entry point. New hard rules carry stable
  identifiers: `SKILL_FRONTMATTER_INVALID`, `SKILL_NAME_MISSING` /
  `SKILL_NAME_MISMATCH`, `SKILL_MISSING_ROOT`, `SKILL_BROKEN_REFERENCE`.
- **IMPLEMENT** - The coder declined to duplicate the generated-versus-canonical
  synchronization rule, because the existing `validate_determinism` /
  `compare_dirs` already prove it tree-wide. It documented that instead. It
  also normalized the two wrap-sensitive Ponytail provenance checks that cost a
  verification cycle in Phase B.
- **IMPLEMENT** - Test count went 1483 to 1511.
- **AUDIT** - A read-only sweep covered every live-advice surface. Results are
  recorded under `## Stale-claims surfaces checked` below.
- **IMPLEMENT** - The orchestrator applied the audit corrections and closed a
  protection gap the phases themselves created: Phase B moved normative skill
  content into `references/` files, which `caveman-compress`'s detector did not
  protect. Extended it, updated the documented list, and added a test proven to
  fail against the pre-change detector.
- **VERIFY** - `verify.py phase` initially reported FAIL on `VFY-RUFF-001`
  because the orchestrator's new test needed `ruff format`. Fixed; re-verified.
- **REVIEW** - All five profiles. Gate FAIL: one MAJOR and one MINOR, both
  against the orchestrator's own edits rather than the coder's.
- **FIX LOOP** - MAJOR: the Hydra scoping in
  `shared/policies/config-first-design.instructions.md` was a half-fix. Only the
  Core Rule paragraph had been qualified; the `## Pure ConfigStore` section,
  code samples, Anti-Patterns bullet, and Checklist stayed absolute, so the file
  contradicted both its own preamble and the sibling bullet in
  `code-standards.instructions.md`. Fixed with a scoping statement covering the
  rest of the file, a corrected frontmatter description, and a conditional
  Anti-Patterns bullet cross-referencing the sibling policy.
- **FIX LOOP** - MINOR: `learn/SKILL.md`'s Output template still reported
  `.claude/skills/` unconditionally after Phase 3 became conditional. Fixed,
  along with one further occurrence in the Phase 5 memory template that the
  reviewer had not cited.
- **RE-REVIEW** - Both findings confirmed resolved, nothing new. The reviewer
  additionally checked that the new backtick path fragments in `learn/SKILL.md`
  cannot trip the new `SKILL_LOCAL_REFERENCE_PATTERN` rule, because that regex
  only matches spans ending in a known file extension.
- **CROSS-MODEL CHECK (step 5)** - Skill parity holds across every generated
  client surface: `shared/skills` 54, `dist/multi-agent/.claude/skills` 54,
  `dist/multi-agent/.agents/skills` 54, `.agents/skills` 54. The canonical
  lifecycle is stated directly in both root guidance files (`CLAUDE.md`, and
  `AGENTS.md:3`), not hidden behind progressive disclosure. The refactored
  `draw-io` root retains its XML-escaping safety rule rather than exiling it to
  `references/`. No new correctness rule depends on one model's autonomous
  judgment; every hard rule is enforced by `validate_targets.py`.

## [LEARN] Entries

- [LEARN:review] Scoping a policy means scoping the whole file. Qualifying only
  the opening rule of `config-first-design.instructions.md` left 130 lines of
  unconditional Hydra mandates below it, so the file contradicted itself and
  its sibling policy. When a rule becomes conditional, walk every section,
  sample, anti-pattern, and checklist item in that file before calling it done.
- [LEARN:review] Two phases running, the orchestrator's own remediation
  introduced the next finding. Route fixes back through review rather than
  treating an orchestrator edit as self-verifying.
- [LEARN:architecture] Progressive disclosure changes what protection rules
  cover. Moving normative content from a skill root into `references/` silently
  removed it from `caveman-compress`'s protected set, because that set matched
  `SKILL.md` only. When content moves, re-check every rule that matched its old
  location.

## Verification Results

```bash
uv run python scripts/generate_targets.py --all      # exit 0
uv run python scripts/validate_targets.py            # exit 0, 0 FAIL lines
uv run python scripts/install_bootstrap.py . --allow-self --local-only  # exit 0
uv run python scripts/check_runtime.py               # exit 0, 0 FAIL lines
uv run python .claude/scripts/verify.py phase        # PASS (all measurements)

# 1511 tests passed. Vendored hashes unchanged throughout:
#   9e2611144a8da730f110af6f789fd4dc9f6574f7fbff1fd5be7220b0b30a6fc3  shared/skills/ponytail/SKILL.md
#   bf0f50e5a406c8c1587ab4a69340369bf0293ef1022450cb9142468aa15f8656  shared/skills/ponytail-review/SKILL.md
```

## Stale-claims surfaces checked

Every live-advice surface required by the `plan-decomposition` contract was
swept for claims invalidated by Phases A, B, or C. Dated historical records
(top-level `plans/`, `.claude/plans/`, dated session logs, dated design
narratives under `docs/`) were deliberately left unchanged, and generated
copies under `.claude/`, `.agents/`, `.codex/`, and `dist/` were excluded
because they regenerate from `shared/`.

| Surface | Outcome |
| --- | --- |
| Root guidance (`CLAUDE.md`, `AGENTS.md`, `README.md`, `SECURITY.md`) | Clean. No claim invalidated by any of the three phases. |
| `docs/` (non-dated) | `docs/architecture.md` updated with the new Skill Library Validation Contract. `runtime-checks.md`, `smoke-tests.md`, `target-mapping.md`, `native-client-acceptance.md` clean. |
| `shared/policies/` | Corrected: `code-standards.instructions.md` (unconditional `argparse` ban and YAML/ConfigStore mandate), `config-first-design.instructions.md` (whole-file Hydra scoping), `api-service-standards.instructions.md` (CORS wildcard, corrected in Phase B). Clean: `workflow.instructions.md`, `quality-and-testing.instructions.md`, `workspace.instructions.md`, `tests.instructions.md`, `tool-routing.instructions.md`, `agent-reporting.instructions.md`, `deployment.instructions.md`. |
| `shared/skills/` | Corrected: `learn/SKILL.md` (directed skill creation into the generated tree), `caveman-compress/` (protected set did not cover `references/`). All other skills read consistently after their own phase edits; no skill restates another's superseded behavior. |
| `shared/templates/` | Corrected: `skill-template.md` (omitted `visibility`, silent on `name` matching the directory — both now enforced by the Phase C rules). Clean: `plan-big.md`, `plan-small.md`, `quality-report.md`, `requirements-spec.md`, `session-log.md`. |
| `shared/agents/` and `shared/review-profiles/` | Corrected: `coder/prompt.md` (unconditional ConfigStore standard). Review profiles clean; `review-profiles/config.md` is already self-scoped to Hydra work. |
| State READMEs | Corrected: `shared/quality_reports/README.md` (still prescribed dated markdown review reports, the last survivor of the line Phase A removed from `code-review`). Clean: `session_logs/README.md`, `plans/README.md`, `explorations/README.md`. |
| `.claude/MEMORY.md` | Updated across all three phases with LEARN entries covering runtime staleness, pipe-masked exit codes, vendored Ponytail divergence, relocated-not-completed fixes, and wrap-sensitive validator prose. |

Three claims from the original audit were rejected rather than implemented, and
are recorded here so a future audit does not resurrect them:

1. The numeric-score lifecycle was already gone from `shared/templates/plan-small.md`;
   all three copies were clean, removed in commit `2af3df7`.
2. `.claude/instructions/workspace.md` is not obsolete. It is emitted on every
   generation run and required by `validate_targets.py` and
   `install_bootstrap.py`. Phase B chose `workspace.instructions.md` as the
   canonical authoring reference name and kept the alias generated.
3. The `ponytail` and `ponytail-review` descriptions are not over-broad. They
   match a mandate this repository states at `CLAUDE.md:30`, and both files are
   hash-pinned, so editing them would have failed `validate_targets.py` in every
   phase that ran it.

## Open Questions / Next Steps

- Observation, not a defect from this plan: `.claude/skills/` carries 55 entries
  against 54 canonical. The extra, `antigravity-native-acceptance-isolation`,
  exists only in the generated overlay and dates to 2026-08-20, three weeks
  before this work. Per the recorded architecture lesson, overlay-only skills
  are pending deletion and should be promoted into `shared/skills/` if the
  content is wanted. Out of scope here; both validators pass and the path is not
  outer-tracked.
- The big plan's three phases are complete. The PR and merge decision belongs to
  the user.
