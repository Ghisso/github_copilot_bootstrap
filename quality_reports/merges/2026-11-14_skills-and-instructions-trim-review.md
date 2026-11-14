# Review: skills-and-instructions-trim

Reviewed on 2026-11-14, Asia/Tokyo. Scope: `cfde280..ef4accf`, the four commits on `skills-and-instructions-trim_implementation`, plus the plan, closeout evidence, and affected live guidance.

**Result: HOLD.** The plan is substantially implemented, and its size results and stored verification evidence check out. I found one MAJOR defect in the new mirror code, one CRITICAL installer safety defect carried forward from the base branch, and three MINOR guidance or validation defects. Passing checks did not cover these cases.

This review does not change implementation, plans, completed logs, receipts, generated wiki pages, or user-level memory. The report is new review evidence, not a replacement for any completed phase's findings.

## Findings

### 1. CRITICAL: an unmarked shipped skill can overwrite a file outside the consumer repository

Location: [scripts/install_bootstrap.py:574](/home/ghisso/work/github_copilot_bootstrap/scripts/install_bootstrap.py:574), particularly the return at line 596. The downstream copy is at [scripts/install_bootstrap.py:820](/home/ghisso/work/github_copilot_bootstrap/scripts/install_bootstrap.py:820).

**Trigger:** a real `.claude/skills/<shipped-name>/` folder has no `.project-skill`, and its `SKILL.md` is a symlink to a file outside the target repository.

The new preflight returns no problem when the folder's name is in the shipped set. It checks whether `SKILL.md` is a regular file only in the marked-folder branch. The copier keeps the destination path because a corresponding source file exists. Its subsequent copy follows the destination symlink and replaces the outside file's contents.

The saved reproduction produced:

```text
symlink.preflight=PASS
symlink.outside_changed=True
symlink.outside_now_matches_source=True
symlink.target_still_symlink=True
```

**Scope qualification:** the unsafe copying predates this branch. The detailed Phase A plan explicitly limits its `SKILL.md` link check to marked folders. This is an existing safety defect left outside that check, not a new regression or a missing explicitly specified test. The big plan and completion summary describe the safety protection more broadly than the implementation provides.

**Fix:** validate the shape of any existing `SKILL.md` before returning success for an unmarked shipped name. Refuse a symlink or other non-regular entry before any write. Add a regression test for the unmarked shipped-name case that checks both the target tree and an outside sentinel remain unchanged. The copying code should also avoid following destination links; check the remaining managed skill files for the same exposure.

The reproduction exercises the preflight and copying helpers used by the installer. Inspection of the earlier `validate_agents_takeover()` call shows that a target with no `.agents` tree passes that guard. A full installer-command reproduction was not confirmed; see the limitations below.

### 2. MAJOR: an unreadable subfolder silently produces an incomplete project-skill mirror

Location: [scripts/install_bootstrap.py:1075](/home/ghisso/work/github_copilot_bootstrap/scripts/install_bootstrap.py:1075).

**Trigger:** a valid marked project skill has a nested directory that the installer cannot read. The reproduction used a `references/` directory with mode `000` and a `required.md` file inside it.

`os.walk()` ignores directory traversal errors unless an `onerror` handler is supplied. `_mirrorable_files()` therefore returns the files it could see and reports no failure. `mirror_project_skills()` logs a successful mirror and publishes `SKILL.md`, while silently omitting the required reference directory and its contents.

The reproduction produced:

```text
unreadable.mirror_skill=True
unreadable.mirror_required=False
unreadable.mirror_references=False
```

This is introduced by the new mirror implementation. It breaks the whole-folder copy promise and can leave Codex and Copilot with a skill whose references are missing. The existing test for a nested symlink or special file does not cover a directory that cannot be traversed.

**Fix:** treat a traversal error as failure of the whole folder's validation. Finish that validation before creating the destination, then refuse or skip the whole mirror with a clear warning. Add a permission-error regression test. A mocked directory-read failure can make the test deterministic on systems where permission bits do not restrict the test process.

### 3. MINOR: a refused symlinked parent is still followed to read skill content

Location: [scripts/install_bootstrap.py:600](/home/ghisso/work/github_copilot_bootstrap/scripts/install_bootstrap.py:600), followed by the content read at line 612.

**Trigger:** `.claude` is a symlink to another directory containing a marked skill.

The validator correctly adds a “marked but not protected” problem. It then continues and reads `SKILL.md` through that same parent link. The leaf-file check does not establish that its ancestors are real directories.

An instrumented reproduction recorded:

```text
ancestor.refused=True
ancestor.declared_name_reads=1
ancestor.read_path_resolves_outside=True
```

No write was demonstrated in this marked-folder case. The defect is that the preflight reads through a link after identifying the path as unsafe, contrary to the plan's “reads nothing through a link” requirement.

**Fix:** stop content validation once the parent-shape check fails. Extend the existing symlinked-`.claude` refusal test to assert that the frontmatter reader is never called.

### 4. MINOR: the learn skill promises a refusal that does not apply to retired names

Location: [shared/skills/learn/SKILL.md:69](/home/ghisso/work/github_copilot_bootstrap/shared/skills/learn/SKILL.md:69).

The text says that without `.project-skill`, “the next refresh refuses to run until you mark or remove the folder.” That is not always true.

An unmarked folder whose name appears in the shipped-before record without a project marker is treated as a retired bootstrap skill. It passes preflight and is deleted when the new source lacks that name. A project can therefore lose an unmarked custom skill that reuses a retired name.

That deletion is the approved retirement policy, not an implementation defect. The guidance is wrong to give an unconditional assurance of refusal. The README and Phase A risk notes already describe the exception.

**Fix:** say that an unmarked never-shipped name is refused, while an unmarked former bootstrap name may be deleted. Keep the instruction to create the marker when creating the skill.

### 5. MINOR: a refreshed wiki page still gives the wrong verification order

Location: [openwiki/workflows/lifecycle-and-task-lanes.md:87](/home/ghisso/work/github_copilot_bootstrap/openwiki/workflows/lifecycle-and-task-lanes.md:87).

The page says to run `verify.py phase --persist` “before review.” The canonical procedure places persisted phase verification at CLOSEOUT step 4, after review, documentation, final plan and learning state, staging, and findings. See [shared/policies/closeout.instructions.md:24](/home/ghisso/work/github_copilot_bootstrap/shared/policies/closeout.instructions.md:24).

The stale sentence predates this branch, but Phase D refreshed this page and recorded that its prose matched the current procedure. It is more than one of the three reported cosmetic wiki follow-ups: following it adds a full verification run at the wrong point and leaves evidence that later closeout edits can stale.

**Fix:** refresh this statement through OpenWiki's tools. Describe focused and fast checks before review, and the persisted phase check at closeout. Do not hand-edit the generated page.

## Improvements that do not block the review

- **Strengthen the Codex fallback check.** [scripts/validate_targets.py:1463](/home/ghisso/work/github_copilot_bootstrap/scripts/validate_targets.py:1463) checks only that a fallback skill exists. It does not check that the skill directs the agent to the mapped policy. The concern reported by the previous agent is real: `hydra-config` has no pointer to `config-first-design.instructions.md`, while that policy contains rules absent from the skill, including the exception for projects without Hydra. Add the policy pointer and a small negative test that removes it. Check all five mapping entries. This weakness predates the trim.
- **Resolve the Codex configuration follow-up using the evidence actually gathered.** The generated configuration now has **37**, not 55, `[[skills.config]]` entries. The spike establishes that these entries do not independently discover skills. It did not test their enable/disable effect. Avoid describing them as fully proven unused until that behavior is checked. Their removal was explicitly deferred by the plan, so retaining them is not an implementation omission.
- **Clarify empty-directory handling if exact directory copies matter.** The mirror records only files and creates their parents, so it omits empty directories. No existing affected caller was demonstrated, and Git also needs placeholder files to retain empty directories. This is a limit to document or test if a real project skill relies on it; it is not a separate blocking finding.

No concrete unnecessary abstraction or dependency was found that warrants removal. The safety checks should remain. No line-reduction recommendation is supported by this review.

## Corrections to the previous completion summary

| Claim | Accurate wording |
| --- | --- |
| Every description is at most 300 characters. | The cap exempts `ponytail` and `ponytail-review`. Their current listing lengths are 504 and 487 characters. The other 35 skills meet the cap. |
| Unsafe skill folders stop the refresh before it writes anything. | Certain folder and marked-skill shapes are refused. Nested links and special entries intentionally skip the mirror with a warning. The unmarked shipped-file case in finding 1 remains unsafe. |
| There are 55 unused Codex configuration entries to remove. | There are 37 entries after regeneration. Discovery was tested; switching behavior was not. |
| Only two optional checks were not run. | Phase B also records the fresh interactive Codex check as `NOT RUN`. It used a prompt-input inspection as a substitute. The Copilot loaded-instructions check and Claude `/context` plus `/doctor` were also not run. |
| Niche content was merged, not dropped. | Eight library-specific skill bodies were retained under the two merged skills. The approved review also removed four niche lesson skills: `dataclass-classvar-constant`, `domain-type-placement`, `graph-schema-compat-migration`, and `extraction-metadata-sourcing`. The first rule already exists in code standards. The blanket claim should be narrowed. |

The recorded marker-preservation design change is sensible. Keeping `.project-skill` in the mirror lets a later refresh distinguish a project skill that lost its marker from a retired bootstrap skill. The marker under `.agents/skills/` does not grant ownership there. I found no reason to revert that decision.

## Verification and evidence

The following checks were run during this review:

| Check | Result |
| --- | --- |
| `scripts/generate_targets.py --all` | PASS; both distributions regenerated. |
| `scripts/validate_targets.py` | PASS. |
| `scripts/check_runtime.py` | PASS. It warned that the PATH copy of Context Mode was version 1.0.169 and selected the existing pinned 2.1.8 fallback. |
| `scripts/validate_plan_frontmatter.py` | PASS. |
| `tests/test_validate_targets.py` and `tests/test_validate_plan_frontmatter.py` | **957 passed in 75.69 seconds.** |
| Targeted installer tests selected by the reviewer | **36 passed, 147 deselected in 3.27 seconds.** Together, the two test runs passed 993 focused tests. |
| `git diff --check cfde280..ef4accf` | PASS. |
| All four closeout receipts | PASS schema validation; each recorded parent and staged tree matches its corresponding phase commit. |
| Bound phase receipts, findings, and session logs | All recorded SHA-256 hashes match the current artifact bytes. |
| Historical completed-phase receipt chain | No errors returned by `historical_chain_errors()`. |
| Temporary safety reproductions | The helper-level results for findings 1–3 are preserved in the script linked below. |

Commands used `uv`; a cache under `/tmp` and offline mode avoided the read-only default cache. No completed receipt was regenerated.

The size claims were independently recalculated:

| Surface | Current result | Plan target |
| --- | ---: | ---: |
| Workflow core | 15,955 bytes | 16,000 bytes |
| Generated `CLAUDE.md` | 4,434 bytes | 4,500 bytes |
| Generated `AGENTS.md` | 4,765 bytes | 4,800 bytes |
| Workspace policy | 7,466 bytes | 7,500 bytes |
| Quality policy | 2,973 bytes | 3,000 bytes |
| Tool-routing policy | 2,960 bytes | 3,000 bytes |
| Orchestrator prompt | 11,856 bytes | 12,500 bytes |
| Documenter prompt | 6,344 bytes | 6,500 bytes |
| Skill count | 37 | 37 |
| Description plus `when_to_use` text | 9,810 characters | 10,500 characters |

The stored phase reports support the earlier test-count claims: A records 5,031 passed; B records 5,092; C and D each record 5,084. Each records one skipped test and passing Ruff and Mypy checks. These are historical results, not a new full-suite run by this review. The stored final findings also match the reported zero CRITICAL and MAJOR counts. Their clean result did not establish coverage of the cases found here.

The four commits exist, and HEAD matches the locally recorded `origin/skills-and-instructions-trim_implementation` reference. The remote was not queried again.

## Reproduction evidence and limits

Saved temporary script: [repro_project_skill_safety.py](/tmp/skills-trim-review-repros/repro_project_skill_safety.py).

It creates temporary fixtures and demonstrates the three installer findings. The overwrite case affects only a temporary sentinel outside its temporary target. The unreadable-directory case depends on permissions being enforced for the test process. The ancestor-read case instruments the frontmatter reader.

An attempted reviewer follow-up probe was stopped by an automated security filter reporting possible cybersecurity risk. The reviewer then completed its final verification summary from the evidence already obtained, without another probe. A full installer-command reproduction of finding 1 was not confirmed. This limits the execution evidence to the named helpers and their inspected call path; it does not establish that a full command was run successfully.

No fresh interactive client session, full 5,000-test run, external documentation verification, or remote push check was performed during this review. Earlier client observations are supported by the dated spike report and closeout logs, not by new live-client measurements. Earlier approval messages were not available for independent verification; the recorded plan was used as the review scope.

Fix the mirror traversal defect before treating the implementation as ready. Address the carried-forward outside-file write and the smaller findings as follow-up work on this unmerged branch. If the completed plan is reopened, append new phases and the required final knowledge refresh under `plan-lifecycle.instructions.md`; keep completed phase plans, logs, findings, and receipts unchanged.
