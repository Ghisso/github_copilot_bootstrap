# Comparison with the second skills-and-instructions review

Reviewed on 2026-11-14, Asia/Tokyo, against the unchanged `ef4accf` implementation. This supplements the [first review](2026-11-14_skills-and-instructions-trim-review.md).

**The hold recommendation is justified. The second review found material issues that my first review missed.** Its strongest additions are the incorrect closeout recovery, unsafe consumer skill-update guidance, a destructive skill-name collision, and the second-clone restoration problem. Several other points are useful improvements or need narrower wording. They should not all be treated as equally severe defects.

The implementation remains unchanged. This comparison does not reopen the plan, refresh consumers, delete old skill folders, or change user-level memory.

## Confirmed additions

1. **Late documentation edits require fresh findings.** The second review is correct. [closeout.instructions.md:141](/home/ghisso/work/github_copilot_bootstrap/shared/policies/closeout.instructions.md:141) incorrectly says findings do not cover documentation. [record_findings.py:51](/home/ghisso/work/github_copilot_bootstrap/shared/scripts/record_findings.py:51) hashes the complete tracked diff from the merge base, including documentation and unstaged tracked edits. The commit gate recomputes that hash and can reject it with `findings report content_hash is stale`.

   There is an important distinction: the phase receipt's scoped content hash excludes ordinary documentation, but the findings hash does not. A repeated closeout step 6 can appear to pass and still leave the commit blocked. For an ordinary late documentation edit, review the changed prose as needed, stage and inspect it, re-record honest findings, checkpoint the changed findings artifact, and persist a new closeout receipt. A full phase-test rerun is not required solely for an ordinary documentation-only path when its other evidence remains fresh. I missed this distinction in the first review.

2. **The learn skill has no safe consumer path for updating a shipped skill.** [learn/SKILL.md:59](/home/ghisso/work/github_copilot_bootstrap/shared/skills/learn/SKILL.md:59) says to update an existing skill or add a variant. It does not distinguish a project-owned skill from an installed bootstrap skill. A local edit to an installed shipped skill is overwritten by refresh. Adding `.project-skill` to that shipped name instead causes a name-clash refusal. The guidance needs to route shared changes to the bootstrap authoring source, or consumer-specific lessons to a distinct marked project skill. My first review caught the false missing-marker assurance but missed this separate update path.

3. **A newly shipped name can overwrite an existing unmarked skill.** [install_bootstrap.py:590](/home/ghisso/work/github_copilot_bootstrap/scripts/install_bootstrap.py:590) accepts an unmarked folder when its name appears in the new source, even if a trustworthy previous-install record does not contain it. The copy then overwrites matching files and deletes extra files. This is a real destructive collision for a consumer-created skill that predates or missed the marker rule.

   The detailed phase plan explicitly allowed names present in the new source. This is a design gap in the approved plan, rather than a coder deviation. A trustworthy previous-install record can help detect it. The no-record case needs its own migration policy; an absent record does not prove ownership either way.

4. **An existing second clone can retain retired skills and then fail refresh.** [restore-root-adapters.sh:117](/home/ghisso/work/github_copilot_bootstrap/shared/hooks/scripts/restore-root-adapters.sh:117) copies current files without deleting obsolete live files. After another clone upgrades and pushes the reduced `.claude/bootstrap-root/.agents` tree, the old clone's live `.agents` can therefore contain extra retired skills. The next takeover check rejects the mismatch. A genuinely fresh clone does not have those stale files.

   This behavior predates the trim, but retiring 20 folders makes it a concrete upgrade concern. A repair must preserve the ownership guard and unrelated content. It should not blindly delete everything absent from the new mirror. The other review overstates one detail: deleting each retired folder is not the only recovery. The existing refusal also allows backing up or moving the conflicting `.agents` tree before rebuilding it.

5. **The description cap has parser gaps.** Valid YAML forms such as `|+`, `>2`, and multiline quoted strings are accepted by the structural check but undercounted by [extract_frontmatter_scalar()](/home/ghisso/work/github_copilot_bootstrap/scripts/validate_targets.py:8555). The reviewer confirmed an in-memory 400-character continuation being measured as only two or five characters, with no structural error. This is a real enforcement gap. All 37 current skills still measure correctly; it is not evidence that the current size result is false. The smallest fix can reject unsupported forms explicitly or correctly measure the forms the validator accepts.

6. **Several documentation and audit findings are real.** Direct reads confirmed:

   - [docs/runtime-checks.md:35](/home/ghisso/work/github_copilot_bootstrap/docs/runtime-checks.md:35) omits the new project-skill exception, and the nearby orphan-removal advice still tells authors to expect deletion.
   - [README.md:304](/home/ghisso/work/github_copilot_bootstrap/README.md:304) points to a deleted “step 1” list. [README.md:968](/home/ghisso/work/github_copilot_bootstrap/README.md:968) still calls `.agents` ownership the only existing-content refusal, just before listing additional refusals.
   - The authoring [CLAUDE.md:56](/home/ghisso/work/github_copilot_bootstrap/CLAUDE.md:56) still says to run `phase` before REVIEW. The first review found the same ordering mistake in the wiki but missed this root file.
   - [project-context.instructions.md:214](/home/ghisso/work/github_copilot_bootstrap/.claude/instructions/project-context.instructions.md:214) still describes the Context Mode migration as unmerged. Its statement that `dev` retains 1.x is stale: the base commit `cfde280` is the PR #55 merge. The dated statement about what consumers had on November 12 is historical; the subsequent current-status advice is the part that needs correction.
   - The closeout errata rules conflict. One passage permits a sibling correction for a receipt-bound log; the standing audit passage restricts such corrections to unbound logs. The original log must remain immutable in either case.
   - The provenance explanation omits future phase plans, although [active_plan_paths()](/home/ghisso/work/github_copilot_bootstrap/shared/scripts/verify.py:1186) includes every phase declared by the big plan.
   - The procedure validator still returns no errors after the entire stale-receipt recovery section is removed. I checked this with an in-memory truncation. The error messages remain earlier in the file, so the current string checks do not establish that recovery instructions exist.

## Two independently checked facts with direct practical impact

**The RAG incident was misidentified.** I compared Git objects from the bootstrap immediately before removal commit `5eea6e6` with RAG's imported state at `8dc7085`. Both skill bodies are byte-identical:

| Skill | Bytes | Same bootstrap and RAG contents |
| --- | ---: | --- |
| `retrieval-routing` | 761 | Yes |
| `iterative-plan-review` | 947 | Yes |

The bootstrap removed those skills on July 3, 2026. RAG's August 9 commit imported pre-existing state; it did not establish that RAG authored the skills. The source comment at [runtime_ownership.py:94](/home/ghisso/work/github_copilot_bootstrap/scripts/runtime_ownership.py:94) therefore gives a false incident history. The marker feature still addresses a real possible loss and unsafe learning guidance, but this example does not prove that a project-owned skill was lost. I did not check that historical premise in my first review.

**`img-classification` really would stop on 22 folders.** I ran only the read-only preflight helpers against `/home/ghisso/work/git_projects/img-classification` and the current generated source. The earlier `.agents` takeover check passed. There was no shipped-before record, and the project-skill check listed 22 old bootstrap names, including the two July removals.

The error says those skills were “never shipped,” which the available history disproves. It should say that prior ownership cannot be established from the available record. Do not mark all 22 as project-owned merely to satisfy that message. Also do not delete them solely because their names match retired skills: check for local edits before removal. No consumer files were changed during this check.

## Claims that need qualification

- **The MEMORY example is not a prescribed broken command.** The guidance gives `[LEARN:installer]` as an example tag. It does not tell the agent to run `grep '[LEARN:installer]'`. Recommending `rg -F` or `grep -F` would make literal matching clearer, but the reported regular-expression mistake is a possible misuse, not an existing command defect in the file. Topic keywords also remain part of the search instruction.
- **Copilot needs different wording for creation and updates.** The repository's dated native-client evidence shows that Copilot discovers `.claude/skills/`, so a new unique skill name need not wait for a bootstrap refresh once the client discovers it. That evidence also shows `.agents/skills/` can win when names are duplicated. Updating an already mirrored skill can therefore leave Copilot using the older copy until refresh. “Immediately” should not imply that every running client rescans files at once.
- **The templates omit the cap, but their current examples do not exceed it.** The shared skill template's placeholder description measures 180 characters. Asking for specific triggers does not inherently require more than 300 characters. Add the limit and a concise example; do not describe the present template as already invalid.
- **The fallback routes are weak, not proof that Codex can never read the policies.** The missing Hydra policy pointer is confirmed. Removing the coder's mandatory `code-style` read also removes a deterministic route to code standards. Other task-matched skill loading and plan requirements can still supply those policies. A conditional policy pointer can restore reliable routing without reinstating every removed always-load skill. The regression-test requirement should likewise be reachable when fixing code, before the agent decides whether to edit tests.
- **A stray marker in authoring source is a useful preventative check.** No shipped skill currently has that erroneous marker. Rejecting one in the source validator would prevent a future bad bundle; it is not a present consumer defect.
- **An incomplete checklist or general/specific recovery rule is not automatically a runtime contradiction.** The completion-commit list gives necessary conditions without saying it is exhaustive, and the gate enforces additional requirements. A specific stale-receipt recovery can be a deliberate exception to a general return-to-IMPLEMENT rule. Clarify those passages, but distinguish them from the demonstrably false findings-hash recovery.
- **Separate confirmation of seven decisions is not inherently required.** The recorded instruction to implement the whole plan can approve its listed decisions. Neither review has the original approval conversation needed to establish otherwise. Item 13 should not become a mandatory new seven-question approval step. The user can still revise those preferences explicitly.
- **Do not treat the unreadable-directory severity difference as a factual dispute.** Both reviews confirm the silent partial mirror. My first report rated its broken-copy behavior MAJOR; the other agent weighs its restricted trigger as MINOR. The fix and missing test are agreed. Fix size alone does not establish severity.

## Size and model-budget claims

I independently confirmed the second review's broader byte totals:

| Measurement | Before | After |
| --- | ---: | ---: |
| Workflow core plus the two extracted policies | 40,797 | 40,297 |
| All shared policy files | 89,699 | 74,481 |

The total policy reduction is **16.97%**. The much larger reduction in the workflow core is primarily a split into files that can be read later. That can reduce initial context use; it is not a 61% reduction in all workflow text. Byte totals alone do not measure actual tokens or per-turn prompt use.

The second review's Haiku-specific results were not independently rerun or checked against current external documentation in this comparison. They identify a useful limit: the original spike used one model configuration and already acknowledged that the old list fit there. Neither a 300-character cap nor success in that configuration proves that every model retains every description.

Do not adopt `skillListingBudgetFraction = 0.02` as a universal fix on the strength of this pasted report alone. Even its reported numbers leave only about 100 characters below a doubled 16,000-character budget. Personal skills or a larger built-in list could exceed it. Verify the target model and actual loaded set before changing that setting.

The other review's exact claims about 14 RAG memory references, one industrial-inspection reference, its new live-client runs, and its latest full-suite rerun were not independently reproduced here. They should retain their own evidence rather than being restated as checks I ran. An old-to-new skill map is a useful migration aid regardless, and added byte limits are reasonable protection against future growth rather than evidence that current size acceptance failed.

## Recommended order

Keep the branch on hold. First address destructive copying and name collisions, the late-documentation recovery, safe learning destinations, and the upgrade/restoration cases. Then close the validator gaps and correct live documentation and the false incident narrative. Refresh generated wiki pages through OpenWiki's tools after the source is final.

Those are suitable inputs to a new fix phase and the required final knowledge-refresh phase if the user requests implementation. Keep completed phase receipts and logs unchanged. There is no reason to undo the entire trim, weaken ownership checks, automatically mark retired skills, or repeat approval questions solely because decisions were accepted together.

This comparison used direct source reads, Git-object comparisons, read-only consumer preflight checks, byte measurements, and safe in-memory validator checks. The existing reviewer performed a focused second verification pass on the findings hash, collision, restoration, and YAML claims. No full suite, generator, consumer refresh, or write probe was run for this comparison.
