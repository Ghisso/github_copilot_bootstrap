# Review findings: skills-and-instructions-trim (consolidated)

Reviewed on 2026-11-14 against `ef4accf` (branch `skills-and-instructions-trim_implementation`, base `cfde280`). This report merges four independent phase reviews run by Claude, the two Codex reports beside this file ([review](2026-11-14_skills-and-instructions-trim-review.md), [comparison](2026-11-14_skills-and-instructions-trim-review-comparison.md)), and the main agent's own checks. Each finding below was checked against the code; the wording follows the Codex comparison where it narrowed a claim.

It is the "Record new findings in a quality report" input for reopening the big plan (`.claude/instructions/plan-lifecycle.instructions.md`, "Reopening a completed big plan"). Completed phases, logs, findings reports, and receipts stay unchanged.

**Result: hold before the PR.** The size goals are met and every check passes, but the findings below need one fix pass.

## Evidence the main agent ran itself

- Full installer run in a scratch target: a shipped `.claude/skills/learn/SKILL.md` replaced by a symlink to an outside file. The refresh exited 0 and wrote the shipped skill text into the outside file (R13).
- Claude Code 2.1.226, `--setting-sources project --add-dir <tree> --debug-file`, from an empty folder:
  - `claude-haiku-4-5` (200K context, 8,000-character listing budget): 55-skill tree `69 skills, 25999 chars > 8000 budget`; 37-skill tree `51 skills, 15900 chars > 8000 budget`.
  - `claude-opus-5` and `claude-sonnet-5`: no `Skill listing over budget` line for either tree that was run.
- `git rev-list --all --objects` comparison: every file in `img-classification`'s 22 old skill folders matches a blob in the bootstrap's history (no local edits). RAG's `retrieval-routing` and `iterative-plan-review` at nested commit `8dc7085` are byte-identical to the bootstrap's copies before `5eea6e6`.
- Consumer state: RAG, industrial-inspection, and `schema-bootstrap-llm-wiki` have a shipped-before record; `img-classification` has none. RAG's `.claude/MEMORY.md` has 14 entries naming removed skills, industrial-inspection's has 1.
- Full test suite rerun: 5,084 passed, 1 skipped. The generated Codex config holds 37 `[[skills.config]]` entries.

## Findings and the phase that fixes each

Severity uses this repository's scale. "Pre-existing" means the defect predates this branch.

### Phase E: closeout and guidance fixes

| ID | Severity | Finding | Evidence |
|---|---|---|---|
| R1 | MAJOR | The docs-only stale-receipt recovery says to repeat step 6 only because "findings do not cover documentation". The findings `content_hash` hashes `git diff <merge-base>` over the whole working tree, docs and unstaged tracked edits included, and the commit gate recomputes it, so the commit is refused with `findings report content_hash is stale`. The phase receipt's scoped hash does skip ordinary docs, so it need not be redone. | `shared/policies/closeout.instructions.md:139-141`; `shared/scripts/record_findings.py:51`; `shared/scripts/verify.py` `content_hash_for` and `verify_current_content`; `_lib-frontmatter.sh` passes the final-state flag at commit |
| R2 | MINOR | Errata rules conflict: Immutability allows a sibling `<log-name>.errata.md` for a receipt-bound log; the standing audit and the workflow core allow one only where no receipt binds the log. | `closeout.instructions.md:99-106` vs `:116-119`; `workflow.instructions.md:212-214` |
| R3 | MINOR | The stale-provenance explanation lists the big plan and the current small plan, but `active_plan_paths` covers every plan in `phases:`. Editing a future phase's plan between steps 3 and 7 stales the receipts. | `closeout.instructions.md:146`; `verify.py` `active_plan_paths` |
| R4 | MINOR | The core says to update the session log "before finishing" and "every ~30 responses" with no exception for a log a closeout receipt already binds; doing so refuses the commit or push (`closeout receipt artifact closeout_log was tampered with`). | `workflow.instructions.md:220`, `:242` |
| R5 | MINOR | Wording that misleads but is not a runtime contradiction: the completion-commit list reads as complete although the gate checks more; the general "return to IMPLEMENT" rule and the specific stale-receipt recovery do not say which applies; step 3 says `verify closeout` "refuses to run at all" (it runs the items, then refuses); step 6 is titled "Why last" though steps 7-8 follow; "the plan templates point here" (the big-plan template does not). | `closeout.instructions.md:11-12, 23, 30, 41-49`; `workflow.instructions.md:84` |
| R6 | MINOR | The stale-receipt pin searches the whole file, and both messages also appear in step 6 and hard rule 2, so deleting the whole recovery section still passes. | `scripts/validate_targets.py:931-1001`; fixture in `tests/test_validate_targets.py` |
| R7 | MINOR | The MEMORY search example `[LEARN:installer]` is a regular-expression character class when pasted into `grep` or `rg` (1,826 of 1,833 lines match; `grep -F` matches 5). Nothing lists the 23 tags, which are broad categories. Keyword search still works, so this is a usability gap, not a broken command. | `workflow.instructions.md:42, 224`; `scripts/generate_targets.py:1364` (generated `CLAUDE.md` and `AGENTS.md`) |
| R8 | MINOR | Codex routes to two policies are weak: `hydra-config` never names `config-first-design.instructions.md`; the coder's always-read tier dropped `code-style` with no replacement read of the code-standards policy (Claude Code loads it through `.claude/rules/`, Codex has no path rules); the regression-test rule lives only in the tests policy, which the coder reads only when a test file changes; the validator checks only that each fallback skill exists. | `shared/skills/hydra-config/SKILL.md`; `shared/agents/coder/prompt.md:9-13`; `validate_targets.py:1463`; `shared/policies/tests.instructions.md:113` |
| R9 | MINOR | The description cap undercounts valid YAML forms the structural check accepts: `|+`, `>2`, `| # comment`, multi-line plain scalars, multi-line double-quoted strings (measured 2-16 characters for 400-plus). All 37 current skills measure correctly. | `validate_targets.py` `extract_frontmatter_scalar`, `skill_frontmatter_yaml_errors` |
| R10 | IMPROVEMENT | Byte budgets cover only the workflow core and the generated `CLAUDE.md` and `AGENTS.md`. Workspace (7,466), quality-and-testing (2,973), and tool-routing (2,960) sit just under their targets, and `closeout` (14,285) and `plan-lifecycle` (10,057) have none. | `validate_targets.py:405` |
| R11 | MINOR | Trigger phrases lost from the listing: "review an API or endpoint" (from `review-api`) appears nowhere; `rag-auditor` lost "RAG evaluation" and "retrieval quality"; `research-critique` lost "review this research"; `data-and-graph-pitfalls` lost the classifier, router, and SQL-generator integration-test triggers. | `shared/skills/*/SKILL.md` descriptions |
| R12 | MINOR | Outdated or wrong docs outside the installer area (list in the Phase E plan, step 6). Examples: `README.md:304` points to a deleted list; the authoring `CLAUDE.md:56` says to run `verify.py phase` before REVIEW, which the core loop does not ask for; `.claude/instructions/project-context.instructions.md` still calls the Context Mode 2.x migration unmerged; the standing audit list omits project context, `.github/`, and `openwiki/`; follow-ups live only in a closed session log. | see the plan |

### Phase F: installer safety and project-skill guidance

| ID | Severity | Finding | Evidence |
|---|---|---|---|
| R13 | MAJOR, pre-existing (the first Codex review rated it CRITICAL) | A full refresh writes through a symlink at a destination path, so it can overwrite a file outside the repository. Affects every generated file it copies, not only skills (`.agents/` is already checked by the takeover guard). | reproduced end-to-end; `scripts/install_bootstrap.py:821` (`copytree(..., dirs_exist_ok=True)`) and the top-level `copy2` |
| R14 | MAJOR | An unmarked skill folder whose name the new source ships is overwritten (extra files deleted) even when a trustworthy shipped-before record shows the last install did not ship that name. A design gap in the approved Phase A plan, not a coder deviation. | reproduced by a reviewer with `haystack`; `install_bootstrap.py:590` |
| R15 | MINOR | With no shipped-before record, the refusal says each folder is "an unmarked skill the bootstrap never shipped" and suggests the marker. `img-classification` would get this for 22 unmodified old bootstrap copies; marking them would keep retired skills forever. An absent record proves nothing either way. | `install_bootstrap.py:590-595`; read-only preflight run by Codex |
| R16 | MAJOR (guidance) | The learn skill, read at every CLOSEOUT step 2, tells consumer agents to "update existing skill" or "add variant to existing" without excluding shipped skills (a refresh overwrites them; marking one is a name clash); promises a refusal for any unmarked folder (false for shipped or previously shipped names); and never mentions the 300-character cap (nor do `shared/templates/skill-template.md` and the `deep-audit` validator list). | `shared/skills/learn/SKILL.md:59-60, 69-71, 83` |
| R17 | MINOR, pre-existing mechanism | On a second, existing clone, `restore-root-adapters.sh` copies the new record into `.agents/` but deletes nothing, so the retired skills stay listed in Codex and Copilot and the next refresh is refused by the takeover check. The refusal does not explain the cause or the recovery, and the docs forbid touching `.agents/skills/` by hand. Moving `.agents/` aside and refreshing recovers (the check passes when `.agents/` is absent and the record exists). | `shared/hooks/scripts/restore-root-adapters.sh:117-135`; `install_bootstrap.py` `validate_agents_takeover` |
| R18 | MINOR | The mirror silently skips a subfolder it cannot read (`os.walk` without `onerror`), so the copy is incomplete; it also copies `__pycache__/` and `*.pyc`, which the generator excludes; it logs "mirror project skill" before the destination-exists skip. | `install_bootstrap.py:1071-1139` |
| R19 | MINOR, preventive | A stray `.project-skill` inside a shipped skill would make every consumer's next-but-one refresh refuse a name clash until each operator deletes it by hand. No shipped skill has one today. | reproduced by a reviewer with a modified copy of `dist` |
| R20 | NIT | After finding a marked folder under a symlinked `.claude` unprotected, the preflight still reads its `SKILL.md` through that link. | `install_bootstrap.py:600-612` |
| R21 | MINOR | Installer-area docs are outdated or false: `README.md:968` ("only refusal"); `docs/runtime-checks.md:35-36, 53-56` (every non-generated file is removed; promote overlay skills into `shared/skills/`); Copilot also reads `.claude/skills/`, so it finds a new project skill without a refresh, while an already mirrored skill shows its last-refresh copy (`learn` 76-78, `README.md:952`, `docs/target-mapping.md:72`); `scripts/runtime_ownership.py:94-96` states the false RAG incident; no map from the 20 retired names to their new homes exists for consumers whose MEMORY names them. | see the plan |
| R22 | MINOR, test gap | No test proves an edit or a deleted file in a project skill reaches its mirror on refresh, and one real-run step asserts only that the output contains the folder name. | `tests/test_install_bootstrap.py` |

### Phase G: knowledge refresh

| ID | Severity | Finding | Evidence |
|---|---|---|---|
| R23 | MINOR | Refreshed wiki pages carry wrong or outdated text: `verify.py phase --persist` "before review" and the wrong docs-only recovery (`openwiki/workflows/lifecycle-and-task-lanes.md:87, 114`); a workspace Ponytail rule Phase B removed (`openwiki/architecture/agents-and-skills.md:194`); "each old body lives unchanged" (the CSV pair changed three lines, `:210`); plus the three cosmetic items in the Phase D log. Phases E and F also change behavior the install and verification pages describe. | page reads |

## Corrected premises and claims

- **The RAG incident did not happen as described.** RAG's `retrieval-routing` and `iterative-plan-review` were bootstrap skills (shipped 2026-05-14, retired 2026-07-03 by R-DEBLOAT-02), byte-identical to the bootstrap's copies; the 2026-08-09 refresh removed them correctly. The marker feature still addresses a real risk: the learn skill told consumers to save skills where a refresh deletes them.
- **The listing-budget evidence covers large-context models only.** On a 200K-context model the listing overflows before and after the trim (see above). Raising `skillListingBudgetFraction` to `0.02` is not a fix: about 16,000 characters is barely above the 15,900 measured without the user's 10 personal `opik*` skills.
- **Summary corrections:** 37 (not 55) `[[skills.config]]` entries, and only "adds no skills" was tested; `ponytail` (504) and `ponytail-review` (487) are exempt from the cap; of the 18 skills removed, 8 merged into two skills, 1 into `bentoml-service`, 2 became tests-policy rules, and 9 were deleted (approved); the workflow text was mostly moved (40,797 to 40,297 bytes across three files), while all policy text fell 17% (89,699 to 74,481); three optional checks were not run, not two.

## Not changed, with reasons

- "Always-on" in the two new policies' descriptions: every `applicability: always` policy uses that label; it means "applies to every path", not "loaded automatically".
- "CLOSEOUT sequence" in pointers versus the "CLOSEOUT procedure" heading: three validator pins use the first; the pointers resolve.
- Restating the commit and push commands in orchestrator steps 8-9, and the older nits in `shared/hooks/scripts/_lib-frontmatter.sh` (typo bypass not excluding `.agents/*.md`): low exposure; recorded as follow-ups.

## Follow-ups outside this fix pass (recorded in `docs/target-mapping.md` by Phase E)

- Remove or keep the 37 inert `[[skills.config]]` entries (user decision; their on/off effect is untested).
- Automatic cleanup of stale `.agents/` content on an existing clone (big plan Decision 10).
- The skill listing still overflows on 200K-context models.
- Consumer MEMORY entries that name removed skills (RAG 14, industrial-inspection 1): update them at each consumer's refresh using the map Phase F adds.
- Consumers installed at `76887a8` (2026-08-22) cannot refresh because of an older takeover rule.
- The typo-bypass allowlist does not exclude `.agents/*.md`.
