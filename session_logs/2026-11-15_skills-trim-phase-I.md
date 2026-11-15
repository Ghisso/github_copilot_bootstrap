# Session: Knowledge refresh and final audit after the second reopen (skills-and-instructions-trim, Phase I)

**Date:** 2026-11-15
**Plan:** `.claude/plans/2026-11-15_phase-I-knowledge-refresh.md`
**Status:** IN-PROGRESS

## Goal

Fix finding R29 in the wiki: the install page repeated the claims R24 to R28 corrected. Refresh every OpenWiki page that describes what Phase H changed, through OpenWiki's own tools. Then run the final documentation, memory, and LEARN audit and record it under `## Stale-claims surfaces checked` (REQ-015).

## Work Log

- Phase H was committed as `969e59c` and pushed. The post-commit hook set this phase `in-progress` and moved `current_phase` here.
- Material-impact check: Phase H changed the installer, its tests, and the installer docs. This phase refreshes the wiki pages for exactly those changes, and the plan's page list and stale-text checks already name them. No planner run is needed.
- **Step 1, OpenWiki.** Read the knowledge-refresh and openwiki skills. Called `openwiki_begin` with `mode: "update"` (run `2197c784-4a1a-4892-84f0-d3bffab84428`, `planning`). Right after it, `git status --porcelain -- AGENTS.md CLAUDE.md` was empty.
  - OpenWiki flagged 11 claims on the install page (7 stale, 4 unresolved) and 2 on `quickstart.md`.
  - A grep of every other page for the behavior Phase H changed found nothing else to change. `agents-and-skills.md` still holds. The state-sync page says only that `--state-remote` *can* point the remote elsewhere, which is still true.
  - The plan submitted two pages.
- **The install page.**
  - Edits:
    - the ownership-table README row now has the unsafe-path skip;
    - the project-skill rules now cover option A and the "is a symlink and was not read" wording;
    - the record paragraph says the live stand-in serves every check, a missing record alone blocks nothing, and a legacy consumer is refused once (bulk remedy);
    - "Never writing through a symlink" became "Unsafe write destinations", with the walker rules, the exact coverage, both headings, the stricter behavior, the copy-time guard, the README skip, and the exact not-checked list, including Git's own writes;
    - the diagram has the recheck node;
    - steps 2, 6, 7, 8, and 12 changed: move-aside wording, the recheck, and `AI_STATE_REMOTE`;
    - the batch section names the legacy refusal;
    - the representative tests are updated.
  - Inspected all 41 claims before the edits. Claims submitted:
    - all 11 flagged claims revised with the same ids and current evidence;
    - two unflagged claims my edits changed, revised: `claim_bf73…` (the devcontainer write and `AI_STATE_REMOTE`) and `claim_094b…` (the README regeneration and the skip);
    - four new claims: the copy-time guard, the recheck after migration, the stricter kind refusal, and the record-folder check before `rmtree`.
  - Every evidence range starts and ends on a non-blank line. The submission was accepted on the first try.
- **`quickstart.md`.** The install routing row now names `Refusing to write over a path of the wrong kind:`. Two claims were revised: the target-mapping range is now L88-L154, and the refusal claim names both headings (L1149-L1170).
- `openwiki_next_page` returned `complete`, and `openwiki_finish` returned `complete`. Afterwards: no `openwiki/.run.json`, no `<!-- OPENWIKI:START -->` block in `AGENTS.md` or `CLAUDE.md`, and only the two pages, their `.claims` files, `.last-update.json`, and `.page-manifest.json` changed.
- **Step 3.** `generate_targets.py --all` exit 0. The self-refresh exited 0 and changed no installed runtime file. `validate_targets.py` PASS, `check_runtime.py` exit 0, `validate_plan_frontmatter.py` exit 0, and every quick Verification line PASS.
- **Review round 1** (`reviewer`, six profiles, the acceptance bar stated up front). Gate FAIL, with one MAJOR, four MINORs, and one open request (a `verify.py phase` result after the fixes).
  - **MAJOR (bar item 3, a false statement about what is checked).** The install page said `validate_no_symlink_writes` "checks every path a full refresh writes". Step 6 said "at any path the refresh writes", and claim `claim_7846…` said the same. But the page's own "These writes are not checked" list names writes it does not check. This is the overclaim pattern from `[LEARN:documentation]` again.
  - **MINORs.**
    - (1) "other than a claimed third-party bundle" is wrong. `_skill_folder_problems` exempts by path shape alone (`is_third_party_skill_path`), claimed or not.
    - (2) The page left out two coverage notes that `docs/target-mapping.md` records: some writes have the preflight only, and an unmarked shipped-name folder without `SKILL.md` is not refused.
    - (3) Two new statements had no claim: the reads-through-links limit with the "no guarantee" sentence, and the legacy-consumer sequence.
    - (4) The audit missed project-context lines 271-275.
- **Round-1 fixes.**
  - A second OpenWiki run (`3961c1e0-323b-4f14-91ee-2254803dda08`; root adapters clean right after `openwiki_begin`; one-page plan) fixed the install page:
    - the lead sentence now says "checks each path in the coverage list below", and step 6 says "at each path its coverage list names";
    - the bundle exemption is now "a folder shaped like a third-party bundle (`skills/openwiki`), claimed or not";
    - new sentences name the preflight-only writes and the no-`SKILL.md` folder.
  - Claims: `claim_7846…` revised to "the paths it covers"; `claim_570b…` revised to the shape wording; four new claims added (reads through links and no guarantee; the legacy sequence; the preflight-only writes; the no-`SKILL.md` folder). Every evidence range starts and ends on a non-blank line.
  - `openwiki_finish` returned `complete`, with no `openwiki/.run.json` left. A grep found no remaining "every path" or "any path" claim on the page. The only "claimed third-party bundle" left is the drift exemption in `check_runtime.py`, which does need the marker.
  - Project-context lines 271-275 were corrected in place.
  - The big plan's Decision 9 change note said "not a claimed third-party bundle". It was corrected to "not shaped like a third-party bundle such as `skills/openwiki`, claimed or not", and `validate_plan_frontmatter.py` exit 0.
  - The README, `docs/runtime-checks.md`, and the refresh skill keep "claimed third-party bundles" for the copy step's skips. That is accurate, because `copy_ignore` skips only marker-claimed bundles.
  - Reran: `generate_targets.py --all` exit 0, self-refresh exit 0, quick Verification lines all PASS. The full `verify.py phase` run was started for the open request.
- **Step 2, audit.** `rg` across every surface in the standing list, using the six claim patterns from the plan plus variants: "is still overwritten", "overwrites the folder", "delete the listed folders", "delete them and rerun", "if you did not create", `hash-object`, `rev-list --all --objects`, "any path it would write", "preflight is complete", "with/without `--state-remote`", "Decisions 8", "confirm or overturn", "symlink preflight", "except the newly-shipped", "Decision 9", and "newly shipped name". The results are under the heading below.

## [LEARN] Entries

## Verification

## Stale-claims surfaces checked

- Root guidance (`CLAUDE.md`, `AGENTS.md`): no hit. No change needed.
- `README.md`: the only hit is "Decision 9's new single-file kinds" (line 767), which belongs to the sidecar plan's own Decision 9, not this one. No change. Phase H already rewrote the installer passages.
- `docs/` (dated `docs/2026-*` excluded):
  - `docs/runtime-checks.md`: only unrelated `core.hooksPath` and `hash-object` mentions remain; Phase H rewrote the installer passages.
  - `docs/architecture.md:137`: "the installer's newly-shipped-name refusal relies on" the matching skill surfaces. Still true.
  - `docs/sidecar-provider-contract.md:969`: another plan's Decision 9. Unrelated.
  - `docs/target-mapping.md`: the follow-ups are current (Phase H).
  - No change.
- Canonical sources (`shared/` policies, skills, templates, agents, review profiles, scripts, hooks): no stale hit. The `hash-object` uses in `verify.py`, `record_findings.py`, and `state-sync.sh` are real code, and "a different value is overwritten with a warning" in `state-sync.sh` describes the settings restore. No change.
- State READMEs (`shared/plans/README.md` and the three other state READMEs): no hit.
- Active plans (`.claude/plans/skills-and-instructions-trim.md`, this phase's plan):
  - line 45's heading "confirm or overturn at approval" is about Decisions 1 to 7, approved in 2026-11.
  - line 118 keeps Decision 10's original "delete the listed folders" text as the record, with the 2026-11-15 change listed after Decision 12.
  - Both are deliberate records. No change.
- `.claude/MEMORY.md`: the `hash-object` entries (lines 153, 1633) are unrelated. Line 1853 is the Phase F lesson that quotes the old overclaim as history. No change; Phase H's two LEARN entries were added at its closeout.
- Project context (`.claude/instructions/project-context.instructions.md`): Phase H updated lines 72-77, the newly-shipped-name refusal. The first audit missed lines 271-275, which still said only an unmarked never-shipped skill folder makes the refresh refuse. Review round 1 caught it. Corrected in place: an unrecorded shipped name is refused too.
- `.github/`: no hit.
- `openwiki/`:
  - the install page and quickstart were refreshed in Step 1 through OpenWiki's tools;
  - `git-backed-ai-state-sync.md:46` ("an install-time `--state-remote` can point it elsewhere") and `:136` (`core.hooksPath`) are still true;
  - `deterministic-verification.md:131` (`hash-object` of the diff) is unrelated.
  - No other change.
- The orchestrator's user-level memory (`project_skills_trim.md` and its index line) said Decisions 8 to 12 still needed the user's confirmation, that the plan was complete after Phase G, and that img-classification would be refused for 22 folders. Corrected:
  - the user confirmed 8, 10, 11, and 12 and overturned 9 (option A);
  - the plan was reopened for H and I;
  - img-classification is refused for all 52 folders, each of which equals a past bootstrap version.
- Closed session logs, quality reports, explorations, and dated docs are dated records and stay unchanged. No closed log misleads enough to need an errata file.

## Open Questions / Next Steps
