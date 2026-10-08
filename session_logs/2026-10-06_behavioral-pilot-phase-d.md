# Behavioral evaluation pilot — final audit and knowledge refresh

**Status:** IN PROGRESS
**Plan:** .claude/plans/2026-10-03_phase-D-behavioral-pilot-knowledge-refresh.md

The paused checkpoint is `f9c47f7`. Its continuation handoff is
`2026-10-06_behavioral-pilot-phase-d-paused.md` beside this log. Phase D
resumed on 2026-10-08 for final closeout.

## Context and workflow tracking

Phase A completed in `f3a8337`, with full verification (2326 tests, typing,
lint) and a clean independent review. The first attempted commit required
the canonical no-lessons marker; correcting it and regenerating closeout
evidence resolved that gate without a bypass. B and C were cancelled under
the approved stop rule. The post-commit hook activated D. No planner revision
is needed: the stopped-pilot path was explicitly planned.

- [x] PRE-FLIGHT: Phase A evidence, review and receipts checked.
- [x] BRANCH: continue `behavioral-evaluation-pilot_implementation`.
- [x] PLAN WHEN NEEDED: existing final phase covers the negative result.
- [x] IMPLEMENT: live advice audit, two source corrections, docs and OpenWiki complete.
- [x] VERIFY: source/runtime/plan/fast and full phase checks passed; closeout not run.
- [x] REVIEW: fresh independent final-phase review PASS; both MINOR findings resolved.
- [ ] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT: repeat until checks and review pass.
- [ ] CLOSEOUT: final audit, requirement mapping, findings and receipts.
- [ ] COMMIT: one final-phase completion commit.
- [ ] PUSH: normal outer-repository publication.

## Publication status

Automatic approval review rejected Phase A's normal `git push -u origin HEAD`
because origin ownership and trust had not been established. No push occurred.
Read-only inspection confirms `origin` is
`https://github.com/Ghisso/github_copilot_bootstrap.git` and local `origin/dev`
matches the approved starting merge. GitHub CLI cannot confirm account ownership
because it is not authenticated. Local work continues; publication needs the
user's approval if no additional trust evidence becomes available.

## Implementation

The source-audit coder completed read-only research but reached its usage
limit before implementation. The orchestrator applied the two planned prose
corrections from that audit: authoring versus installed skill paths, and big
versus small plan statuses in the sidecar planner. No executable behavior
changed and no new test is warranted for these wording corrections; existing
generation and validation checks verify rendering. Independent review passed
with no findings. The documenter completed README and live native-acceptance documentation.

Before each source edit, its OpenWiki claim ranges were checked. Source edits
finish before the single planned MCP refresh. No native reruns occur.

## Stale-claims surfaces checked

- Shared policies, skills, templates, agents and review profiles: audit found
  the two planned corrections only; no unsupported behavioral-pilot claims.
- Generated dist/multi-agent and dist/sidecar: read-only audit located the
  same two source-derived phrases; regenerated after corrections and validated.
- MEMORY.md: searched native evidence, behavioral evaluation, reviewer
  requirements, status and skill-path guidance; no invalidated live advice
  identified. Historical run details remain in dated evidence, not memory.
- README.md: added a short dated-evidence link and stopped/advisory boundary.
- Root AGENTS.md and CLAUDE.md: report-only audit found no invalidated pilot
  claim; both stayed byte-identical through install and OpenWiki begin.
- Non-dated docs: documenter found no contradictory native/deterministic
  claims; docs/native-client-acceptance.md now links the dated stopped pilot
  and states the exact role-evidence level. Other live docs need no change.
- State READMEs: plans already distinguish big/small statuses, including
  planned/paused; exploration, session-log and quality-report guidance remains
  accurate. Dated records and completed logs were left unchanged.
- Installer help: inspected full/sidecar profiles, local-only, and trust
  boundaries; no invalidated claims or behavioral-mode option is present.
- OpenWiki: managed agents-page refresh repaired the planned validator ranges,
  expanded sidecar advisory and guidance-test evidence, updated descriptive
  plan statuses and skill paths, and corrected the stale planner/reviewer
  visibility table. The added dated-pilot claim is advisory, not a gate.

## OpenWiki completion

Applied knowledge-refresh and OpenWiki skills. Run
`e115c340-244c-40ca-9677-ce8ce344fe7b` used `mode: update`. The only page with
flagged claims was `openwiki/architecture/agents-and-skills.md`; it was also
the page explicitly required by this phase. After `inspect_page_claims`,
the run revised six existing claims and added three, retaining other current
claims. The four validator ranges were re-anchored from actual source, not
blindly offset: the duplicate-description evidence now includes its full
check rather than an unrelated following function. Guidance-test ranges now
include the real generated and sidecar assertions. The sidecar advisory
sentence has explicit planner/coder/reviewer source evidence.

`openwiki_submit_page`, the final `openwiki_next_page`, and `openwiki_finish`
returned `complete`. No `.run.json` remains, and no root setup snippet or
workflow file changed. No tracked source file changed while the run was open.

Final review found two MINOR evidence-completeness gaps: roster exclusivity
needed all eight metadata files, and sidecar advisory evidence needed the
explicit non-gating clauses. A second, narrowly scoped managed update
(`cf2ec248-4f91-4cf9-8d4f-4986fe3ece99`) inspected and expanded only those
two claim evidence sets. Its submit, queue completion and finish all returned
`complete`, and no active run remains. This is a review-driven extra refresh
beyond the planned single pass; no source or page-body edit occurred during
it. Claim sidecars were changed only by OpenWiki.

The required runtime check initially found the installed skill template stale.
The supported generated self-install with `--allow-self --local-only` refreshed
it, preserved root authoring adapters and mutable state, and performed no
network publication. The runtime check then passed. No trust settings changed.

## Requirement mapping

- BEP-001: met at "consistent with" only; role-loading.json and dated report.
- BEP-002: unproven; four unavailable case records trigger the stop rule.
- BEP-003: not implemented; Phase B validly cancelled.
- BEP-004: not implemented; Phase B validly cancelled.
- BEP-005: not evaluated; Phase C validly cancelled, no comparative conclusion.
- BEP-006: met; audited surfaces above, source/doc fixes, and completed OpenWiki run.
- BEP-007: ordinary tests/verifier make no model call; no new gate or runner
  mode; native calls were user-run; saved evidence is bounded and reviewed.

## Verification

Generation, target validation, runtime wiring, plan frontmatter, fast
verification, and diff whitespace checks passed. Source/doc review before the
refresh passed with no findings. Final generated-diff review passed after
the two evidence-range corrections; no findings or open requests remain.
Final `verify.py phase --format text --persist` passed: Ruff clean, mypy
zero errors, and 2326 tests passed in 214.65 seconds. The phase receipt is
`.claude/quality_reports/verification-phase-2026-10-03_phase-D-behavioral-pilot-knowledge-refresh.json`.
The user then requested stopping at the next logical boundary. No Phase D
closeout dry run or closeout receipt has been produced. Resume instructions
are in `.claude/session_logs/2026-10-06_behavioral-pilot-phase-d-paused.md`.

On 2026-10-08, plan-frontmatter validation, generated-target validation,
runtime wiring, and `tests/test_validate_targets.py` passed (194 tests).
The user discarded the pre-existing `.codex/config.toml` edit that had blocked
root-adapter provenance. The full phase verifier then passed as the checkout
owner: Ruff clean, mypy zero errors, and 2326 tests passed in 212.32 seconds.
The first root-run test failures were caused by root bypassing read-only
directory permissions. Owner-run retries exposed an inherited inaccessible
`/root` PATH entry and a temporary Unix socket path that exceeded the platform
limit. A clean PATH and the standard owner-accessible `/tmp` pytest directory
resolved both without changing source or tests. A diagnostic bytecode file
created under `.claude/scripts/__pycache__/` was removed after it made the
runtime check fail. The four required closeout commands passed in a dry run;
its freshness check correctly requires a receipt rebound to this plan state.

- optional 1: PASS — OpenWiki finish returned complete for initial run e115c340-244c-40ca-9677-ce8ce344fe7b and review-correction run cf2ec248-4f91-4cf9-8d4f-4986fe3ece99; reviewed page is openwiki/architecture/agents-and-skills.md; no active run file remains.

## [LEARN] Entries

[LEARN] none - no new lessons this session

No new root cause was established for the native client exits. The existing
knowledge-ownership and explicit stop-rule guidance covers the observed case.
