---
name: 2026-07-18_phase-C-enforce-ponytail-review
type: small-plan
parent_plan: ponytail-integration
phase_index: 3
status: complete
closeout_session_log: plans/2026-07-18_ponytail-integration-closeout.md
---

# Small Plan: 2026-07-18_phase-C-enforce-ponytail-review

## Scope

Turn Ponytail review from a reminder into a deterministic closeout
requirement. Reuse the existing reviewer, findings recorder, content hash, and
commit/push gates so any post-review code change invalidates the evidence.

## Steps

- [ ] Add `shared/review-profiles/ponytail.md`, derived from the pinned
  `ponytail-review` skill.
  - Check for unnecessary code, duplicate helpers, avoidable dependencies,
    speculative abstractions/configuration, native/stdlib replacements, dead
    flexibility, and opportunities to delete or shrink.
  - Never report required validation, security, accessibility, root-cause
    handling, or the smallest meaningful regression check as bloat.
  - Use `MINOR`, `MAJOR`, and `CRITICAL` severities consistently with existing
    review profiles, while noting that all Ponytail findings must be resolved
    regardless of severity.
- [ ] Update the authoritative routing table in
  `shared/policies/workspace.instructions.md`.
  - Add `ponytail` to every code, test, API/service, refactor, hook, script, and
    control-plane review.
  - Keep documentation-only review exempt.
- [ ] Update `shared/agents/reviewer/agent.md`.
  - Load the Ponytail review profile whenever the diff is not
    documentation-only.
  - Run it in the same primary/refutation/convergence process as other
    profiles.
  - Emit `profile: "ponytail"` for its findings and separately return the list
    of reviewed profiles even when findings are empty.
- [ ] Extend `shared/scripts/record_findings.py`.
  - Add a repeatable `--profile` option or an equivalent explicit
    `--profiles-json` input.
  - Persist top-level `profiles_reviewed`, `ponytail_reviewed`, and
    `ponytail_findings` fields before the free-form findings array.
  - Reject a claim that Ponytail was reviewed when a Ponytail finding omits
    `profile: "ponytail"`.
  - Keep the current branch, phase, base, merge-base, HEAD, dirty-state,
    changed-files, and content-hash metadata unchanged.
- [ ] Add one shared documentation-only classifier to
  `shared/hooks/scripts/_lib-frontmatter.sh`.
  - Exempt only all-Markdown or documented state/report directories.
  - Treat mixed docs/code, renames, deletions, scripts, configs, manifests,
    Dockerfiles, generated-source inputs, and hook files as Ponytail-required.
  - Use the same merge-base plus staged/unstaged file view as report freshness.
- [ ] Extend `shared/hooks/scripts/enforce-commit-gate.sh` and
  `shared/hooks/scripts/enforce-pr-gate.sh`.
  - For a non-documentation diff, require the fresh findings report to have
    `ponytail_reviewed == true` and `ponytail_findings == 0`.
  - Name the exact remediation command and required reviewer profile when
    blocking.
  - Keep the existing bypass contract explicit and ledgered; do not create a
    Ponytail-only hidden bypass.
- [ ] Extend `scripts/validate_targets.py` adversarial hook suite with:
  - missing Ponytail profile;
  - Ponytail reviewed but one `MINOR` finding remains;
  - stale content hash after a source edit;
  - docs-only pass;
  - mixed docs/code block;
  - renamed/deleted code;
  - fresh zero-finding Ponytail report pass;
  - bypass behavior matching the existing policy.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
