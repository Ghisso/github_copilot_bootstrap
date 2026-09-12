# Session: Correct Ponytail provenance, canonical paths, and rigid skill assumptions

**Date:** 2026-09-12
**Plan:** `.claude/plans/2026-09-12_phase-B-skill-routing-and-provenance.md`
**Status:** COMPLETED

## Goal

Correct the vendored Ponytail provenance record, resolve canonical-versus-
generated path confusion in skill guidance, simplify skills that impose one
project architecture or excessive ceremony, apply progressive disclosure where
reference material dominates a skill root, and narrow genuinely over-broad
routing descriptions.

## Work Log

- **IMPLEMENT** - Split across two coders with strictly disjoint file sets,
  both forbidden from running generation, the validators, or the full suite,
  because those write shared state and would race in a single working tree.
  The orchestrator regenerated and verified centrally.
- **IMPLEMENT** - Part 1 (15 files): Ponytail provenance, the canonical/
  generated path fix, architecture and ceremony assumptions, and the
  interaction-heavy skills.
- **IMPLEMENT** - Part 2 (22 files): progressive disclosure, specialist and
  learned skills, policy-duplication review, and `data-analysis` retention.
- **DECISION** - The orchestrator settled the open naming question:
  `workspace.instructions.md` is the canonical reference name, matching every
  sibling policy file and `CLAUDE.md`'s Map section. The `workspace.md` alias
  stays generated, because removing it would mean changing the generator,
  validator, and installer for no functional gain.
- **VERIFY** - First `validate_targets.py` run FAILED with two errors:
  `Ponytail provenance must preserve canonical workflow authority` and
  `Ponytail provenance must distinguish the review profile from the imported
  skill`. Cause: that validator matches literal substrings spanning line
  breaks, and the provenance rewrite re-flowed the paragraph. The wording was
  correct; the line wrapping was the contract. Restored the required wrapping
  and marked that paragraph's wrapping as load-bearing in the file itself.
- **REVIEW** - All five profiles over the real diff. Gate result FAIL: one
  MAJOR and one MINOR, both confirmed by the orchestrator before acting.
- **FIX LOOP** - MAJOR (security): Phase B removed the hard-coded CORS
  wildcard from `bentoml-service/SKILL.md`, but the same edit pointed the
  reader at `api-service-standards.instructions.md` as "the required shape",
  and that policy still carried
  `access_control_allow_origins: ["*"]` with Required Element 6 saying only
  "Enable in service decorator". The fix had been relocated, not completed,
  and the wildcard now carried canonical authority. Fixed at the source.
- **FIX LOOP** - MINOR (code): `draw-io/README.md` keeps a references list
  separate from `SKILL.md`'s, and only the latter gained the new
  `references/xml-recipes.md` entry. Added it.
- **RE-REVIEW** - The fixes went back to the same reviewer. It confirmed both
  findings resolved and raised one new MINOR against the orchestrator's own
  remediation: `ALLOWED_ORIGINS` was a bare undefined name that would raise
  `NameError` if the example were copied verbatim, and it contradicted the
  file's own Required Element 7 requiring `os.getenv()` for all
  configuration. Applied the reviewer's prescribed replacement, which also
  fails closed: an empty value means no cross-origin access, never a wildcard.

## [LEARN] Entries

- [LEARN:review] Removing an unsafe default from a skill is incomplete while
  the skill still points at a policy that keeps it. The `bentoml-service` CORS
  fix moved the wildcard from the skill into the reader's path to canonical
  policy, which made the posture worse rather than better, because the
  wildcard then carried canonical authority. When a change relocates
  responsibility to another document, re-read that document as part of the
  same change.
- [LEARN:verification] `scripts/validate_targets.py` matches several prose
  contracts as literal substrings that span line breaks, so re-flowing a
  paragraph fails the gate even when the wording is unchanged. The affected
  paragraph in `shared/third_party/ponytail/UPSTREAM.md` now says so in-line.
  Treat prose that a validator pins as wrap-sensitive.
- [LEARN:workflow] Parallel coders in one working tree are safe only when
  their file sets are disjoint AND neither runs generation, the validators, or
  the full suite. Those write shared state (`dist/`, `.claude/`, `.agents/`)
  and race. Splitting edit work while centralizing verification worked well
  across 37 files.
- [LEARN:review] A fix authored by the orchestrator needs review as much as a
  fix authored by a coder. The CORS remediation introduced an undefined name
  that would have failed at import time, and only the re-review caught it.

## Verification Results

```bash
uv run python scripts/generate_targets.py --all      # exit 0
uv run python scripts/validate_targets.py            # exit 0, 0 FAIL lines
uv run python scripts/install_bootstrap.py . --allow-self --local-only  # exit 0
uv run python scripts/check_runtime.py               # exit 0, 0 FAIL lines
uv run python .claude/scripts/verify.py phase        # PASS (all measurements)

# Vendored hash constraint held throughout:
#   9e2611144a8da730f110af6f789fd4dc9f6574f7fbff1fd5be7220b0b30a6fc3  shared/skills/ponytail/SKILL.md
#   bf0f50e5a406c8c1587ab4a69340369bf0293ef1022450cb9142468aa15f8656  shared/skills/ponytail-review/SKILL.md

# Receipts:
#   .claude/quality_reports/verification-phase-2026-09-12_phase-B-skill-routing-and-provenance.json
#   .claude/quality_reports/verification-closeout-2026-09-12_phase-B-skill-routing-and-provenance.json
```

## Open Questions / Next Steps

- Phase C (`2026-09-12_phase-C-skill-regression-prevention`) is the final
  phase. It extends `scripts/validate_targets.py` rather than adding a second
  gate, adds regression tests, extends `deep-audit` with advisory checks, and
  runs the plan-wide stale-claims audit that `verify.py`'s closeout gate
  requires under the exact heading `## Stale-claims surfaces checked`.
- Phase C should consider whether the wrap-sensitive prose checks in
  `validate_targets.py` deserve whitespace normalization. That is a real
  brittleness class, already recorded in `.claude/MEMORY.md`, and it cost a
  verification cycle in this phase.
