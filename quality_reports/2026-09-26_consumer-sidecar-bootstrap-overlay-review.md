# Consumer sidecar bootstrap overlay — hardening re-review

Date: 2026-09-26 (Asia/Tokyo)  
Reviewed HEAD: `010f08c` on `consumer-sidecar-bootstrap-overlay_implementation`  
Review range: `c90aac9..010f08c`  
Big plan: [consumer-sidecar-bootstrap-overlay](../plans/consumer-sidecar-bootstrap-overlay.md)  
Previous reports: [first review](2026-09-25_consumer-sidecar-bootstrap-overlay-review.md), [second review](2026-09-25_consumer-sidecar-bootstrap-overlay-review-2.md)

## Verdict

**FAIL — four MAJOR findings remain; one MINOR finding is advisory.**

The hardening work is substantial and addresses the original reproductions. All 2,097 existing tests passed across the main run and an environment-related retry. However, eight new adversarial cases fail, mapping to the five findings below. In the most serious case, uninstall deletes files tracked by a nested repository that was added as a gitlink after installation. Do not treat the current implementation as safe for all documented consumer layouts yet.

Keep the overall design. The separate personal overlay, Git-local ownership records, shared reconciliation planner, team precedence, and preservation outside discovery directories fit the intended use. The remaining problems call for focused corrections to filesystem boundaries, ownership classification, and consistent collision detection—not a replacement architecture.

This is an independent, report-only review using code, architecture, security, tests, documentation, and simplification profiles, with primary and verification passes. No implementation fixes, plan changes, receipt rewrites, commits, or pushes were performed. Historical reports and evidence remain unchanged.

## What was implemented

The big plan records phases A–I complete and leaves `current_phase` blank. The new small plans and corresponding session logs agree about the work delivered:

| Phase and commit | Implemented work | Evidence |
| --- | --- | --- |
| F — `f6e13af` | Allows reopening a completed big plan after a settled knowledge-refresh phase while requiring a new final refresh. | [Small plan](../plans/2026-09-25_phase-F-reopen-completed-big-plan.md), [session log](../session_logs/2026-09-25_sidecar-phase-F-reopen-completed-big-plan.md) |
| G — `8d153c3` | Moves team precedence into reconciliation; recognizes ownership from records or exclude entries; preserves modified copies outside skill discovery; expands index, symlink, and declared-name handling. | [Small plan](../plans/2026-09-25_phase-G-sidecar-ownership-and-precedence.md), [session log](../session_logs/2026-09-25_sidecar-phase-G-ownership-and-precedence.md) |
| H — `f7d9af4` | Adds earlier target/metadata validation, Git environment isolation, stronger source/path handling, retired-namespace support, removal of unused provenance metadata, and uninstall through the existing planner. | [Small plan](../plans/2026-09-25_phase-H-sidecar-preflight-robustness-and-uninstall.md), [session log](../session_logs/2026-09-25_sidecar-phase-H-preflight-robustness-and-uninstall.md) |
| I — `010f08c` | Refreshes the knowledge layer and corrects documentation after hardening. | [Small plan](../plans/2026-09-25_phase-I-sidecar-hardening-knowledge-refresh.md), [session log](../session_logs/2026-09-25_sidecar-phase-I-hardening-knowledge-refresh.md) |

The latest terminal receipt gate and historical receipt-chain check pass. That confirms the recorded lifecycle evidence remains valid; it does not override the new behavioral findings.

### Previous findings now addressed

The five executable reproductions from the first review now pass: lost-manifest adoption with a team collision, same-folder collision through a symlinked read root, non-file manifest refusal before writes, missing-but-indexed team content, and unrelated non-UTF-8 Git filenames. The unused `bootstrap_commit` field was also removed while retaining compatibility with older manifests.

The design recommendations were adopted in meaningful ways: precedence is more centralized, modified copies can leave discovery directories without losing edits, uninstall reuses reconciliation, and test coverage includes more combined states. The failures below are remaining combinations and incomplete guarantees, not a claim that the hardening failed wholesale. Passing those five earlier cases also does not establish that every item in the separate second review is closed.

## Findings

### R1 — MAJOR: a previously owned unit can cross a nested-repository boundary during uninstall

Locations: [structural target set](../../scripts/sidecar_overlay.py#L87), [preflight boundary checks](../../scripts/sidecar_overlay.py#L2703), [team-takeover deletion](../../scripts/sidecar_overlay.py#L797).

Reproduction in a disposable consumer repository:

1. Install the sidecar normally.
2. Initialize a Git repository inside `.claude/skills/ponytail` and commit its files there.
3. Add that directory to the outer index with `git add -f -- .claude/skills/ponytail`, creating a gitlink.
4. Run uninstall.

Observed: uninstall returns success and deletes `SKILL.md` and `LICENSE`, although those files are tracked by the nested repository. It also reports the unit as team-owned. Without step 3, another reproduction moves the entire nested repository, including its `.git`, into the preservation directory instead of refusing the operation.

Cause: preflight checks the fixed write roots and bridge parents, not every actual unit path. Outer-index gitlink ownership does not describe the files tracked inside the nested repository; the takeover code treats matching inner files as deletable sidecar files.

The phase-H log explicitly accepts the narrower structural check on the assumption that a nested repository at a unit is always foreign. A previously installed unit invalidates that assumption. This contradicts big-plan Decision 28 and the protection of team content.

Correction: check repository boundaries for all desired, recorded, and exclude-listed units before planning destructive actions. Refuse both disk-only nested repositories and indexed gitlinks at those units. Do not infer inner-file ownership solely from the outer index. Cover install, update, and uninstall after an ordinary sidecar installation has changed into a nested repository.

### R2 — MAJOR: uninstall forgets a modified retired skill without taking it out of discovery

Location: [uninstall conversion set](../../scripts/sidecar_overlay.py#L1223).

Reproduction: install the current profile, edit `.claude/skills/ponytail/SKILL.md`, then simulate a later profile that removes `ponytail` from `SIDECAR_SKILLS` and run uninstall. The test changes only the in-memory profile constant; production files are not edited.

Observed: uninstall returns success, leaves the modified retired skill in its live discovery folder, and removes its manifest/exclude ownership. It gives the retired-unit copy/delete advice rather than moving the unit into preservation. The file can remain active and become visible to Git after an apparently successful uninstall.

Cause: uninstall marks only current skill names under current write roots as taken. Retired manifest units enter reconciliation but miss the preserve/remove conversion. This is a forward-compatibility defect, not a failure on every fresh current-profile install; profile retirement is nevertheless explicitly supported by Decisions 32 and 34.

Correction: derive uninstall conversion from all recognized required units, including supported retired names and roots, while keeping team/foreign-content protections. Add a public uninstall regression using an older manifest with a modified retired skill and assert content preservation, removal from discovery, and correct metadata cleanup.

### R3 — MAJOR: declared-name collision detection applies inconsistent symlink rules

Locations: [declared-name scan](../../scripts/sidecar_overlay.py#L2003), [taking-path filtering](../../scripts/sidecar_overlay.py#L1002).

Two independently reproduced cases:

- Make `.github/skills` a symlink to a team directory. Put a skill in a differently named folder there whose frontmatter declares `name: humanize`. Installation still creates both sidecar `humanize` copies. The folder-name scan follows the read-root alias, but the declared-name scan skips the symlinked root entirely.
- After normal installation, make the untracked `.github/skills/ponytail` path a symlink to `../../.claude/skills/ponytail`. Rerunning installation removes both actual sidecar copies and leaves the alias dangling. The folder-name scan recognizes an alias to the sidecar's own unit; the declared-name scan treats its declaration as competing content because filtering removes only the literal write-root path.

The first case misses a real collision; the second invents one. Both undermine Decision 22's unified precedence contract. These are confirmed filesystem/reconciliation results. Native client discovery behavior for these fixtures was not tested.

Correction: use the same resolved-path identity rules for folder names and frontmatter names. Distinguish aliases to owned projections from independent team content consistently. Test regular and symlinked read roots, individual aliases, different folder names, and repeat installation.

### R4 — MAJOR: a personal special filesystem node is omitted from the modification check and deleted

Location: [unit snapshot collection](../../scripts/sidecar_overlay.py#L1818), especially the special-file branch at line 1857.

Reproduction: install normally, create a FIFO named `.claude/skills/ponytail/personal-channel`, then uninstall.

Observed: uninstall returns success and removes the unit, including the personal FIFO, without a preserved copy. The test does not write to or read from the FIFO, so it does not depend on blocking pipe behavior.

Cause: special nodes count toward `has_content` but do not appear in the file hash map and do not mark the unit unsafe or modified. The ordinary files still match the manifest, allowing whole-directory removal. This proves loss of a personal filesystem node; it is not evidence of regular-file data loss in this particular case.

Correction: a hash match must not authorize recursive deletion when the snapshot omits non-directory entries. Refuse unsupported special nodes before any writes, or represent them in a safe classification that prevents unchanged-unit deletion. Add FIFO and socket cases without reading their contents, covering uninstall and destructive replacement paths.

### R5 — MINOR: settled refresh validation trusts status without checking phase identity or path confinement

Location: [settled-refresh helper](../../scripts/validate_plan_frontmatter.py#L286).

The new helper accepts a sibling with `status: complete` or `cancelled` without verifying its small-plan type, name, or parent big plan. `is_file()` also follows symlinks, despite the helper's statement that the slug check prevents reading outside the plans directory.

Two focused tests show that an unrelated-parent sibling, and a sibling symlink pointing outside the plans folder, both exempt an earlier refresh from the uniqueness check. This is a validation weakness, not evidence that the actual F–I plans have incorrect identities or that the later receipt gates can be bypassed.

Recommendation: validate sibling identity and parent relationship and enforce the intended confinement rule before exempting a phase. Use valid small-plan fixtures in the positive tests. Advisory disposition: open; the current plan passes and later evidence gates provide additional checks, so this does not determine the blocking verdict.

## Verification performed

| Check | Result |
| --- | --- |
| Full existing suite: `uv run pytest tests/ -q --tb=short` | 2,095 passed; two consumer-install tests failed because dependency downloads were blocked by sandbox DNS/network restrictions. |
| Retry of those two tests with approved network access | Both passed. Together, all 2,097 existing cases passed; this was not a single uninterrupted clean run. |
| Five original review reproductions | 5 passed. |
| New adversarial cases | 8 failed: two nested-repository cases, retired modified skill, two collision cases, FIFO, and two settled-refresh validation cases. These map to R1–R5, not eight separate findings. |
| Ruff check and format check | Passed; format check covered 41 files. |
| Mypy | Passed for 41 source files. |
| Runtime health check | Passed. |
| Plan frontmatter validation | Passed for the repository's current plans. |
| Focused generated-sidecar validation, malformed-target cases, and full-install root-coverage checks | Passed. |
| Existing historical receipt chain and latest terminal receipt gate | Passed. No receipts regenerated. |

Commands used `UV_CACHE_DIR=/tmp/github-copilot-bootstrap-uv-cache` to avoid the read-only default cache. All adversarial consumer mutations targeted disposable test repositories. The durable findings and reproduction steps are recorded here, not solely in temporary test output.

A direct diagnostic import initially created a disposable `verify` bytecode cache under the installed runtime and made the current runtime fingerprint differ. After removing that review-created cache and rerunning with `python -B`, the unmodified terminal gate passed. This was a review artifact, not a stale-closeout finding.

No new native-client smoke tests, live provider integration tests, coverage measurement, or full installer/consumer smoke cycle were performed in this review. Phase H records that its optional native fixture was not run; phase I did not rerun native checks. The earlier Antigravity limitation therefore remains. Passing automated checks is not a guarantee of issue-free operation.

## Design assessment and next steps

The architecture is suitable and improved. Avoid adding another framework, persistence layer, or reconciliation engine. The smallest useful follow-up is:

1. Restore Decision 28 at actual unit boundaries, including units already owned before they become nested repositories. This is the highest-priority safety correction.
2. Make snapshot completeness a condition of any destructive action. Unrepresented special nodes must prevent unchanged-unit deletion.
3. Apply uninstall semantics to the complete recognized ownership set, not just the current shipped profile.
4. Reuse one path-identity rule across folder and declared-name collision checks.
5. Add focused public-API regressions for the eight reproduced cases, then rerun the existing suite and terminal evidence checks. Tighten the refresh helper as a small advisory follow-up.

The key testing improvement is to combine supported states: prior ownership plus a new repository boundary; profile retirement plus personal edits plus uninstall; read-root aliases plus frontmatter names. The current suite is broad, but these interactions expose assumptions that isolated happy-path tests do not. Keep the shared planner and extend its inputs and safety checks rather than adding separate special-purpose workflows.

Until R1–R4 are corrected and re-reviewed, the recommendation is **do not approve the hardening as complete on behavioral safety grounds**, despite the completed plan and passing stored lifecycle receipts.
