# Sidecar overlay review

**Date:** 2026-09-25  
**Big plan:** [Consumer Sidecar Bootstrap Overlay](../plans/consumer-sidecar-bootstrap-overlay.md)  
**Implementation branch:** `consumer-sidecar-bootstrap-overlay_implementation`  
**Reviewed HEAD:** `c90aac9`

Reviewed `dev...c90aac9` on `consumer-sidecar-bootstrap-overlay_implementation` on 2026-09-25. Scope: all five completed phases, installer and reconciliation logic, generator and validators, mixed updates, tests, and documented guarantees.

Verdict: **FAIL — two MAJOR findings and four MINOR findings**. Changes are implemented, but the branch needs corrections before release. Passing completion receipts did not cover the combinations below. Two findings break the central promise that team skills take precedence. Four smaller findings affect failure handling, compatibility, and diagnostic metadata. No repository source, plan, session log, or receipt was changed during this review.

The independent reviewer completed primary and adversarial verification passes using the code, architecture, security, tests, ponytail, and documentation profiles. Findings below combine that review with the main agent's reproductions.

## Findings

### 1. MAJOR — recovery can keep a sidecar skill despite a team collision

Location: [scripts/sidecar_overlay.py:732](../../scripts/sidecar_overlay.py#L732).

Install the sidecar, move its manifest aside, then add a tracked team skill at `.github/skills/ponytail/SKILL.md`. Rerunning the installer reports that `ponytail` is skipped at every root, but adopts both `.claude/skills/ponytail` and `.agents/skills/ponytail` and leaves them installed.

The collision loop handles `unchanged`, `update`, and `install`, but does not handle `adopt`. Adoption is the supported recovery path for a lost manifest or interrupted update. Matching sidecar copies therefore survive the collision and remain available to clients that read multiple roots. This contradicts Decision 8 and the printed result.

Correction: apply the collision rule to adopted copies too, preserving the existing ownership proof and rules for locally modified content. Add a regression that combines manifest recovery with a team collision and checks the resulting files, manifest, and report.

### 2. MAJOR — symlinked team skill folders are omitted from collision checks

Location: [scripts/sidecar_overlay.py:1089](../../scripts/sidecar_overlay.py#L1089).

In a team repository, make `.github/skills` a symlink to a directory containing `ponytail/SKILL.md`. Installation succeeds and creates both sidecar copies of `ponytail`. The collision scan explicitly skips both symlinked read roots and symlinked skill directories, treating their names as absent.

The documented collision contract covers every read root and requires skipping a name already used by non-sidecar content. Ignoring an occupied symlink can introduce competing skills for clients that follow it. The filesystem collision was reproduced; client behavior for this new symlink fixture was not tested natively.

Correction: conservatively recognize collisions through the read roots, or refuse an ambiguous symlink with a clear explanation. Do not silently interpret it as an empty folder. Cover both a symlinked root and an individual symlinked skill.

### 3. MINOR — a non-file manifest is detected only after installation writes

Location: [scripts/sidecar_overlay.py:1539](../../scripts/sidecar_overlay.py#L1539).

Create a directory at `.git/ai-bootstrap-sidecar.json`, then install. Preflight treats it as an absent manifest because it only enters validation when `is_file()` is true. The installer changes `info/exclude` and installs all ten units, then raises `IsADirectoryError` while replacing the manifest.

This is an uncommon damaged-metadata state, but the documented behavior is to reject invalid manifests before writing and give a recovery remedy. The run instead leaves a partial installation and a traceback.

Correction: distinguish a missing manifest from an existing non-regular path before writing anything. Add a regression asserting the exclude file and worktree remain unchanged on refusal.

### 4. MINOR — missing tracked files turn a team collision into a whole-install failure

Location: [scripts/sidecar_overlay.py:1053](../../scripts/sidecar_overlay.py#L1053).

Track `.claude/skills/ponytail/SKILL.md`, then delete it from the working tree while leaving it in the Git index. The snapshot derives tracked ownership only from files currently present on disk, so it incorrectly plans an installation. The ignore gate catches the tracked path and safely aborts, but reports a nonexistent team `.gitignore` negation and blocks every other skill.

No tracked file was overwritten in the reproduction. The defect is incorrect ownership classification, failure scope, and recovery advice. The contract says a team-owned unit should be skipped while the rest of the overlay proceeds.

Correction: derive unit ownership from the Git index independently of disk presence. Preserve local deletions and skip the affected skill at both roots.

### 5. MINOR — an unrelated non-UTF-8 filename prevents installation

Location: [scripts/sidecar_overlay.py:987](../../scripts/sidecar_overlay.py#L987).

Stage a filename containing byte `0xff` anywhere in a consumer repository. Installing the sidecar raises `UnicodeDecodeError` while decoding `git ls-files -z`, before planning. Git permits such names on POSIX systems. The path does not need to be inside a skill folder.

This was independently reproduced by both reviewers. No installation writes occur, so user files remain safe. Use filesystem-safe path decoding and encoding consistently across Git queries, hashing, and ignore checks, or explicitly reject unsupported filenames with a useful diagnostic. Add a regression for arbitrary filename bytes.

### 6. MINOR — installed manifests lack the promised commit diagnostic

Location: [scripts/sidecar_overlay.py:643](../../scripts/sidecar_overlay.py#L643).

`plan_sidecar_reconciliation` defaults `bootstrap_commit` to an empty string, and `install_sidecar` never supplies a value. Normal installed manifests therefore contain `"bootstrap_commit": ""`, despite the plan describing that field as diagnostic provenance. Content hashes still drive reconciliation, so this does not affect ownership decisions.

Correction: populate the field from reliable generated-source metadata, or remove the unused field and its diagnostic claim. Avoid inventing provenance from the consumer's own commit.

## Verification

- Existing suite: **1,883 test cases passed across the initial run and focused retry**. Initial run: 1,881 passed, 2 failed because temporary consumer environments could not download dependencies inside the network sandbox. The same two tests passed with network access. These were environment failures, separate from the findings above.
- Ruff lint and formatting: PASS.
- Mypy: PASS.
- Runtime checks: PASS.
- Sidecar target validation, adversarial validator cases, and full-install ownership coverage checks: PASS.
- Additional temporary review probes: **five reproducible failures**, corresponding to findings 1–5. Finding 6 was confirmed from the planner default and its live caller. The temporary probes exercised the reproduction steps documented in findings 1–5.
- Working tree remained clean during the review, before this report was saved.

The test suite was executed without replacing completed lifecycle receipts. Its existing tests do not cover these particular combinations. Native client sessions were not rerun; this review used the recorded provider evidence and exercised the filesystem and Git behavior directly. Antigravity remains unverified as documented.

## Design assessment

The core architecture fits the intended goal: personal skills inside a team repository, with the team's configuration taking priority. Keep the architecture and make targeted improvements. Explicit install modes, ownership records outside tracked files, one reconciliation path for installation and updates, and content checks before deleting owned files are sound choices for that goal.

The recommendations below are design follow-ups, separate from the six implementation findings above. They have not been implemented and do not change the recorded finding counts.

### Make team precedence one rule for every action

**Priority: high. Recommendation: CHANGE.**

The recovery bug arose because collision handling covered `install`, `update`, and `unchanged`, but missed `adopt`. Determine ownership and whether a skill name is available before selecting the final action, then constrain every action by the same precedence decision. Recovery must obey the same collision rules as an ordinary installation.

Keep the existing planner and data model where practical. This needs a consistent decision boundary, not a new framework. Ensure adopted copies have sufficient ownership evidence before removing them, and continue to preserve modified content.

### Resolve preservation versus active discovery for modified copies

**Priority: high. Recommendation: CHANGE.**

The current design deliberately keeps a modified sidecar copy when the team takes the same skill name. The existing test, [`test_skill_taken_keeps_and_reports_a_modified_copy_at_the_other_root`](../../tests/test_sidecar_overlay.py#L587), confirms this behavior. Preserving the bytes protects personal edits, but leaving the copy in a discovery folder can keep it available alongside the team's skill. The design therefore cannot promise both unconditional preservation in place and absence of competing skills.

Report this state as an unresolved conflict. Provide an explicit, safe resolution that preserves the personal copy outside client discovery folders while disabling the competing projection. Any backup must avoid overwriting existing content and identify where the preserved copy can be recovered. Until the conflict is resolved, do not report that the skill was successfully skipped at every root.

This is a policy improvement to the existing behavior, not a claim that the current implementation accidentally omitted its documented preservation rule.

### Test combinations and transitions

**Priority: medium. Recommendation: CHANGE.**

Individual mechanisms have substantial coverage. The review failures appeared where mechanisms interacted: recovery plus a team collision, or tracked ownership plus missing files. Add a small, explicit matrix of these combinations using the existing real-Git test helpers.

Assert the actual guarantees: team files and local deletions are preserved, competing sidecar skills are absent or explicitly reported as unresolved, Git status remains unchanged within the documented recovery exceptions, invalid metadata is refused before writes, and reruns reach a stable result. A new testing framework is unnecessary.

### Make removal safer

**Priority: medium, after the correctness fixes. Recommendation: CHANGE the instructions; consider an uninstall command later.**

The current [manual removal instructions](../../README.md#personal-sidecar-install) say to delete every manifest-owned path. Those paths can contain personal modifications that the installer deliberately preserved. At minimum, require checking for and preserving such content before removal.

A later uninstall command could reuse ownership and content checks to remove unchanged copies while preserving modified or foreign content. It should remove only its own metadata and exclude entries, and clearly report anything left behind. This is an optional usability improvement, not a prerequisite for retaining the current architecture.

### Keep the scope limits explicit

**Recommendation: ACCEPT the limits for the stated v1 goal; revisit them if the intended workflow expands.**

In this implementation, Codex gets skills without an always-on bridge, and sidecar installation refuses linked worktrees. The sidecar also omits the full bootstrap's hooks, agents, and plan/review/commit lifecycle. It does not provide the full workflow automatically in every agent session.

These limits are deliberate in the [big plan's non-goals](../plans/consumer-sidecar-bootstrap-overlay.md#non-goals). If automatic activation or background-worktree support becomes essential, investigate that requirement separately with native client evidence before expanding the design.

## Next step

Keep the architecture. Correct the two collision defects before release, resolve the precedence policy for modified copies, address or explicitly disposition the smaller findings, and add focused transition regressions. Improve the removal instructions; defer an uninstall command unless it is needed. Rerun the affected checks and review after implementation. This was a review and design-assessment request; production fixes have not been applied.

No independent over-engineering finding was identified. Required safety checks should remain. Ponytail review net: -0 lines possible.
