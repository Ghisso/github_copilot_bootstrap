# Session: OpenWiki Phase H — skill rename and host rules

**Date:** 2026-09-21
**Plan:** `.claude/plans/2026-09-19_phase-H-openwiki-skill-rename-and-host-rules.md`
**Status:** COMPLETED

## Goal

Rename the bootstrap's `openwiki` skill to `knowledge-refresh` so OpenWiki's
own host integration can install its `openwiki` skill at
`.claude/skills/openwiki` and `.agents/skills/openwiki` without a name
collision; rewrite the skill for host-driven operation; replace the remaining
rule that forbade host integrations with a precise one (never from hooks,
`verify.py`, the bootstrap installer, state-sync, CI, or inside a refresh;
once per checkout, by a person); sweep every reference; and remove this
checkout's stale installed copies so Phase I's installer finds the paths free.

## Work Log

- Phase started 2026-09-21 after Phase G's completion commit `e9b70fd`, on the
  existing implementation branch.
- Plan pre-check before IMPLEMENT found four statements the plan inherited
  from before Phases F2 and G that no longer held. Corrected in the plan file
  first: only one committed rule forbidding host integrations remained (the
  skill's own line 83; Phase G had already removed the policy and prompt
  copies), not three; the `## Verification` block gained the focused pytest
  line and an `## Optional Verification` section (none) per the Phase F2
  evidence contract; the claim that the Codex `[[skills.config]]` set is
  "validator-enforced" was replaced by an inspection step, since no such
  validator exists; the expectation that `check_runtime.py` flags the stale
  installed copies was labelled an expectation to confirm. The Step H1
  checklist also states that the provider-configuration bullet survives in
  condensed form. Plan lint exit 0.
- IMPLEMENT (one coder, Ponytail full): `git mv shared/skills/openwiki
  shared/skills/knowledge-refresh`; frontmatter `name: knowledge-refresh`,
  `visibility: public`, new description naming the split with OpenWiki's own
  `openwiki` skill. Body gained the two-skill split, the once-per-checkout
  enablement procedure, the precise installer rule, one-run-per-checkout with
  `.run.json` resume semantics, `noop` and `openwiki_finish: complete`
  reporting, and the supported-hosts statement. Kept unchanged: ownership
  pointer, per-host restore coverage, manual `post` command, result reading,
  `verify.py` backstop, rebaseline rule, references.
- Reference sweep: one-line path substitutions in `AGENTS.md:9`,
  `CLAUDE.md:14`, `scripts/generate_targets.py` (`render_root_guidance`
  string), `shared/policies/workflow.instructions.md` (OpenWiki Refresh and
  Knowledge-Refresh Final Phase Shape), `shared/agents/orchestrator/prompt.md`,
  `shared/agents/documenter/prompt.md`, `docs/architecture.md`. `README.md`
  and `workspace.instructions.md` do not name the skill path; unchanged.
- Deviation 1: the plan's enablement wording ("a reported unmanaged skill at
  either path") requires naming `skills/openwiki`, which the Step H2
  acceptance grep forbids outside third-party-ownership code. Reworded to
  "an unmanaged skill directory already occupying the `openwiki` slot under
  `.claude/skills/` or `.agents/skills/`"; same meaning, grep unambiguous.
- Deviation 2: `tests/test_install_bootstrap.py::test_runtime_check_marker_gates_openwiki_skill_bundle_drift`
  created its fixture files inside a `skills/openwiki` directory it expected
  the generated tree to contain. The bootstrap no longer generates that
  directory, so the test now creates it (`mkdir(parents=True,
  exist_ok=True)`), matching reality: only OpenWiki's installer creates it.
  Not a target file in the plan; a direct consequence of the rename.
- Deviation 3: the self overlay refresh needs `--allow-self` in addition to
  `--local-only` for this repository; the plan text and Phase G summary
  omitted the flag. The installer preserved tracked `AGENTS.md`/`CLAUDE.md`
  itself (`preserve tracked authoring adapter`), so no restore was needed.
  Note for future phases: `git checkout -- <path>` is denied by
  `git-protection.sh`; `git restore -- <path>` is the allowed form.
- Step H2.3 observation: the overlay refresh pruned `.claude/skills/openwiki/`
  and `.agents/skills/openwiki/` itself before `check_runtime.py` could be run
  against them (same behaviour Phase G recorded for the runner copy). The
  coder reconstructed both copies without `.openwiki-install.json` and ran
  `check_runtime.py`: it flagged each as `FAIL stale runtime path ...
  authoritative source: absent from generated target`. Expectation confirmed;
  copies removed again; `check_runtime.py` exit 0. Neither path exists now.
- Step H2.4: `[[skills.config]]` names in `dist/multi-agent/.codex/config.toml`
  equal `ls shared/skills` exactly; `knowledge-refresh` present, `openwiki`
  absent from both.
- Acceptance grep `grep -rn 'skills/openwiki' shared scripts docs README.md
  AGENTS.md CLAUDE.md tests` returns only the third-party-ownership lines in
  `scripts/runtime_ownership.py`, `scripts/check_runtime.py`,
  `scripts/install_bootstrap.py`, and `tests/test_install_bootstrap.py`.
- VERIFY: focused pytest 255 passed after the test fix; `generate_targets.py
  --all`, `validate_targets.py`, `check_runtime.py`,
  `validate_plan_frontmatter.py` exit 0; `verify.py fast` PASS. `verify.py
  phase --format text` PASS: ruff 0 violations, mypy 0 errors, pytest 1755
  passed, `VFY-GEN-001` generated verifier runtime matches source.
- Session note: the first review agent was lost when the host session
  restarted mid-review; relaunched with the same brief.

## Review findings and dispositions

One round (profiles `code`, `architecture`, `security`, `tests`, `ponytail`,
`documentation`; two sequential passes): 0 CRITICAL, 0 MAJOR, 0 MINOR. Gate
PASS.

- Raised in pass 1 and dropped in pass 2 as not a defect: the skill's "Reading
  the result" list of `openwiki-guard.sh pre` denial reasons omits the
  unresolved-prior-run and symlinked-path denials. The remediation the skill
  gives for any denial (check `git status`, run `openwiki-guard.sh post
  </dev/null`) is the correct action for those cases too, so no reader is
  misled.
- Independently confirmed, not only asserted by the plan: the skill's claims
  about OpenWiki's own tool behaviour (`noop`, `openwiki_finish` returning
  `complete`, `openwiki/.run.json` as the resumable run state) were checked
  against the installed `openwiki@0.5.2` package source; the guard-restore
  timing against `openwiki-guard.py`, the generated Codex `Stop` wiring, and
  the spike's U6 observation.
- Held up on review: every target keeps the skill (`dist/multi-agent`
  `.claude/skills/knowledge-refresh`, `.agents/skills/knowledge-refresh`, and
  54 `[[skills.config]]` entries equal to `shared/skills`); the test fix still
  fails if the marker gate breaks in either direction; all `## References`
  paths resolve; the four remaining `skills/openwiki` references are the
  intentional third-party-ownership code.

## [LEARN] Entries

- [LEARN:planning] Re-read a small plan's factual claims against the
  repository right before starting it, not when it was written. Three phases
  had landed between this plan's drafting and its start; four of its
  statements (a count of rules, a "validator-enforced" claim, a verification
  block predating the F2 contract, an inferred `check_runtime.py` outcome) had
  drifted. Correcting the plan first cost minutes; discovering each mid-phase
  would have cost a review round.
- [LEARN:workflow] The self overlay refresh (`install_bootstrap.py .
  --local-only --allow-self`) prunes obsolete installed copies as a side
  effect. Take any "before removal" observation before running it, or you
  will have to reconstruct the stale state to observe it.
- [LEARN:planning] A plan that both requires prose to name a path and forbids
  that path in an acceptance grep over the same file has two literally
  incompatible requirements. Scope the grep to code, or phrase the acceptance
  as "only intentional references", and say which those are.

## Verification

```text
PASS       75.5s  uv run pytest tests/test_validate_targets.py tests/test_lifecycle_hooks.py tests/test_install_bootstrap.py -q --tb=short
PASS        0.2s  uv run python scripts/generate_targets.py --all
PASS       45.9s  uv run python scripts/validate_targets.py
PASS        0.9s  uv run python scripts/check_runtime.py
PASS        0.3s  uv run python .claude/scripts/verify.py fast --format json
PASS      118.2s  uv run python .claude/scripts/verify.py phase --format json --persist
closeout: PASS
```

Receipts: `.claude/quality_reports/` phase receipt (`VFY-RUFF-001`,
`VFY-MYPY-001`, `VFY-PYTEST-001` 1755 passed, `VFY-FRESH-001/002`,
`VFY-GEN-001` all PASS) and the closeout receipt persisted after this log was
checkpointed. Findings report:
`.claude/quality_reports/findings-2026-09-19_phase-H-openwiki-skill-rename-and-host-rules.json`
(0 findings, six profiles, `ponytail_reviewed=true`).

- optional 1: NOT RUN — the plan's `## Optional Verification` bullet is the placeholder "None"; there is no optional check to run.

## Open Questions / Next Steps

- Next phase is `2026-09-19_phase-I-openwiki-enable-and-first-generation`:
  enable OpenWiki here, run `openwiki integrations install` for Claude Code
  and Codex once, re-probe the guard, run one host-driven update, commit, and
  stop for inspection. Both `skills/openwiki` paths are now free for it.
- Follow-ups carried unchanged from Phase G: `verify closeout` traceback when
  the findings report is missing (MINOR, from Phase F2); the overlay refresh
  removing the nested `.claude/.gitignore` that `state-sync.sh` recreates.
