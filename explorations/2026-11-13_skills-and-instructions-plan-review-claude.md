# Devil's Advocate Report (Claude) — skills-and-instructions-trim

**Date:** 2026-11-13. **Reviewer:** separate read-only Claude Opus subagent at
`xhigh` effort with `.claude/skills/devils-advocate/SKILL.md`. It did not read
the Codex review (`2026-11-13_skills-and-instructions-plan-review-codex.md`).
It ran no generator, validator, installer, `verify.py`, or pytest. This file
records its report as returned to the main agent.

**Overall:** the order holds. A, then B, then C, then D, and no phase depends
on a later one. Most citations are accurate. The verification blocks contain
no `rg` and pass the hedge patterns. The Phase A design does stop the deletion
in exploration §7.1 on both a refresh and a fresh install. The main gaps:

- the closeout procedure is still restated in a different order in two live places;
- the Completion Protocol removal drops the only instruction to read the learn skill;
- the consumer-refresh step would mark retired skills as project skills;
- the symlink edge cases are not specified;
- the spike setup and Phase D have small holes.

## Devil's advocate table

| # | Concern | Risk | Alternative | Rec. | Evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | Deleting the Completion Protocol removes the only "Read `.claude/skills/learn/SKILL.md`" in `shared/`. Skill extraction at phase end stops, and so does Phase A's marker guidance. | HIGH | CLOSEOUT step 2 names the learn skill, and the validator pins it. | CHANGE | `shared/agents/orchestrator/prompt.md:163`; grep `learn/SKILL.md` in `shared/` finds only that line |
| 2 | Phase A's refresh step says to list unmarked folders the new dist does not ship, then "Mark or move each one first". After Phase C, all 20 retired skills match, so an agent marks them and keeps them in every consumer. | HIGH | Leave out names already in the consumer's `.agents/skills/` (the set the bootstrap shipped before). Only the rest were created by the project. | CHANGE | Phase A:96; generated `.agents/skills` = shipped set (Phase C:153) |
| 3 | README "Updating Full Consumers" restates CLOSEOUT as 6 steps with no closeout dry run and no second checkpoint, and says "Never checkpoint after step 5". Phase B edits only lines 326 and 358. | MED | Replace the list with a pointer to the closeout file. | CHANGE | `README.md:306-333`; `workflow.instructions.md:191-197` |
| 4 | The commit skill says "Never checkpoint after the receipts are persisted". That conflicts with CLOSEOUT step 5, which checkpoints after the phase receipt. Phase B edits only lines 46 and 57. | MED | Lines 45 and 47 become the pointer. | CHANGE | `shared/skills/commit/SKILL.md:45,47` |
| 5 | Root guidance never names the closeout file. Nothing makes the Claude Code main thread load the orchestrator prompt. The workflow step-5 pointer is read early and can be lost to compaction. | MED | Add the pointer to the always-loaded CLOSEOUT bullet in `render_root_guidance` and pin it. | CHANGE | `generate_targets.py:1370-1373`; only Copilot gets a pointer (Phase B:143) |
| 6 | Symlinks are only partly covered. `Path.is_file()` follows a symlinked marker. A symlinked skill folder is "a folder holding" nothing, and walking or copying it follows the link, so outside files land in `.agents/` and the ai-state remote. A project folder named `openwiki` would also overwrite OpenWiki's `.agents/skills/openwiki` bundle. | MED | Require `not dir_path.is_symlink()` and a non-symlink regular marker (the pattern of `_regular_text`). Refuse when the destination is a third-party skill folder. | CHANGE | `install_bootstrap.py:369-376`, `264-271`; Phase A:69, 74 |
| 7 | Copilot keeps the `.agents/skills/` copy, so it sees the stale mirror. The table says "Yes, directly". A hand edit to `.agents/skills/<name>` blocks the next refresh and breaks the receipt fingerprint. | LOW-MED | Correct the table. In the learn skill: "Codex, Antigravity, and Copilot see edits at the next refresh; never edit `.agents/skills/` by hand". | CHANGE | `docs/sidecar-provider-contract.md:525`; `install_bootstrap.py:468-475`; `verify.py:917-963` |
| 8 | Spike S1 copies the whole dist, including `.codex/hooks.json`. Its SessionEnd hook runs `state-sync.sh checkpoint`, which can commit inside the scratch nested repo where Claude's commit guard cannot see it. The copy also brings `npx` MCP servers. | MED | Build the S1 tree from `AGENTS.md`, `.agents/skills`, `.claude/skills`, and `.codex/config.toml` only, as S5 already does. | CHANGE | `dist/multi-agent/.codex/hooks.json:3-24,116-125`; big plan:162 |
| 9 | S5 has no positive control. If the baseline run shows no warning, the grep cannot tell "no overflow" from "the wording is different". Phase C's Optional Verification check then passes no matter what. | MED | One run with `SLASH_COMMAND_TOOL_CHAR_BUDGET` set low to capture the exact warning text. Run the measurement with `claude --bare -p --add-dir <tree>` (no hooks, no user skills; `--add-dir` skills still load). | CHANGE | big plan:176-181, 201; Phase C:172 |
| 10 | S2 (ways to hide skills) only records an option the user already rejected. | LOW | Delete S2. | CHANGE | big plan:170-171, 202 |
| 11 | Phase D Step 2 may edit `shared/`, but Phase D has no regenerate/refresh step and its Verification has no `generate_targets.py --all` or `check_runtime.py`, so `dist/` and the installed runtime can go stale. | MED | Add an unconditional regenerate-and-refresh step and both commands. | CHANGE | Phase D:92-103; compare A:131, B:223, C:147 |
| 12 | Opt-in marker: the rollout refresh after this plan deletes any unmarked project skills in RAG and industrial-inspection, unless the operator follows the listing step. Recoverable from nested Git. | MED | The installer refuses when an unmarked `.claude/skills/<name>/` is in neither the source nor the consumer's `.agents/skills/`. | INVESTIGATE (user) | Phase A:35; §7.1 |
| 13 | `test_retired_skills_stay_removed` repeats the Verification absence check and blocks a future re-add. `validate_project_skills` returns names nobody uses. | LOW | Keep only the merged-skill existence test. Return `None`. | CHANGE | Phase C:112; Phase A:73 |
| 14 | The Phase C absence check skips backticked `refactor` by design, so the coder prompt line-70 edit goes unverified. | LOW | Add one check. | CHANGE | `coder/prompt.md:70`; Phase C:156 |
| 15 | Phase B is large (about 28 files, 9 steps). Most of it is moved text. | LOW | Keep the B1/B2 fallback; no split needed. | ACCEPT RISK | Phase B:73 |

## Action items

**CHANGE (exact edits):**

1. **Phase B, Step 2, closeout file:** step 2 reads "read `.claude/skills/learn/SKILL.md` and route each lesson (project skill with `.project-skill`, a MEMORY entry, or none)". Step 1: `closeout_procedure_errors` requires `learn/SKILL.md` in step 2. Verification: add `grep -q -F 'learn/SKILL.md' shared/policies/closeout.instructions.md`.
2. **Phase A, Step 3, safe-consumer-bootstrap-refresh:** list folders the new dist does not ship, that have no `.project-skill`, **and that are absent from the consumer's current `.agents/skills/`**. Add: "a name present there was shipped by the bootstrap and is retired on purpose; do not mark it."
3. **Phase B, Step 7, README:** replace lines 306-327 and the sentence at 332-333 with one pointer to `.claude/instructions/closeout.instructions.md`. Keep the upgrade-specific paragraphs. Verification: `test "$(grep -c -F 'Never checkpoint after step 5' README.md)" = "0"`.
4. **Phase B, Step 7, commit skill:** change "(lines 46 and 57)" to "(lines 45-47 and 57; 45 and 47 become the pointer)". Verification: `test "$(grep -c -F 'Never checkpoint after the receipts are persisted' shared/skills/commit/SKILL.md)" = "0"`.
5. **Phase B, Step 3:** the root-guidance CLOSEOUT bullet adds "follow `.claude/instructions/closeout.instructions.md` step by step" and keeps the pinned fragment. Step 1: the pointer pins add both root files. Verification: `grep -q -F 'closeout.instructions.md' dist/multi-agent/CLAUDE.md` and the same for `dist/multi-agent/AGENTS.md`.
6. **Phase A, Step 2:** `is_project_skill_dir` requires `not dir_path.is_symlink()` and a marker that `is_file()` and is not a symlink. `mirror_project_skills` refuses a destination that `is_third_party_skill_dir`. Step 1 adds two tests: a symlinked marked folder and a symlinked marker are never mirrored.
7. **Big plan line 134:** "Yes, through the mirror; Copilot keeps the `.agents/skills/` copy (`docs/sidecar-provider-contract.md:525`)". Line 140: drop "possibly". **Phase A, Step 3, learn:** "Codex, Antigravity, and Copilot get edits at the next refresh. Never create or edit `.agents/skills/<name>/` by hand." Optional: "keep the description at most 300 characters".
8. **Big plan, spike line 162:** replace `cp -a dist/multi-agent "$SPIKE/full"` with copies of `AGENTS.md`, `.agents/skills`, `.claude/skills`, and `.codex/config.toml`. Strip `[mcp_servers.*]` from the copy with a `python3 -I` tool script. Add the rule "no hook configuration in any spike tree".
9. **Big plan, S5:** add a `claude-overflow` run on the before tree with `SLASH_COMMAND_TOOL_CHAR_BUDGET=1000` and record the warning text. Run the before and after measurements with `claude --bare -p --add-dir <tree> --debug-file ...`. The "baseline shows no warning" row then means "no overflow". Optionally add `skillOverrides` `"name-only"` as option (e) in the still-warns row. That is the user's decision.
10. **Big plan:** delete lines 170-171 (S2) and the S2 row at line 202. Also add "S3: record only" so every result has a mapped outcome.
11. **Phase D:** add Step "Regenerate and refresh this repository" (the same two commands as A Step 4). Verification gets `uv run python scripts/generate_targets.py --all` as its first line and `uv run python scripts/check_runtime.py`.
12. **Phase C, Step 6:** cut the name-absence half of `test_retired_skills_stay_removed`. **Phase A, Step 2:** `validate_project_skills` returns `None`.
13. **Phase C, Verification:** add ``test "$(grep -c -F '`refactor` ceremony' shared/agents/coder/prompt.md)" = "0"``.
14. **Big plan line 196:** drop "and this repository's tracked `.codex/config.toml`". It has no skill entries: 0 `SKILL.md` mentions, against 57 in dist.
15. **Phase A line 78:** remove `shared/skills/caveman-compress/scripts/detect.py`, which does not import `runtime_ownership`. Add `scripts/generate_targets.py` (it imports it at line 16 and copies the file at 377-378).
16. **Phase C line 173:** replace "whether any skill is reported as excluded" with "the Skills row size and `/doctor`'s listing-cost estimate".

**INVESTIGATE:**

- Does `codex debug prompt-input` fire project hooks or start MCP servers? Item 8 makes this moot.
- Do path-scoped `.claude/rules/` load inside a Claude Code subagent (the coder)? Not documented. Phase C's explicit "read the tests policy" instruction already covers it.
- Row 12: see the question below.

## Wrong or stale claims

- **Big plan:196:** this repository's tracked `.codex/config.toml` has no `[[skills.config]]` entries. Exploration §7.7's "enables all 55" is true for `dist/` only.
- **Phase A:78:** the importer list is wrong (`detect.py` is listed, `generate_targets.py` is missing).
- **Big plan:134:** the Copilot "Yes, directly" claim contradicts `docs/sidecar-provider-contract.md:525`.
- **Phase C:173:** `/context` reporting excluded skills is unverified. The docs say the Skills row shows the listing size after the budget.
- **Phase B:69:** the "exactly one" rule is stated imprecisely. The workspace file needs exactly one `.claude/hooks/` **and** exactly one `.github/hooks/` (`validate_targets.py:711-720`). The root files need only presence (`validate_targets.py:692-694`); the exactly-one count there comes from the leak exemption (`validate_targets.py:8203-8206`).
- **Verified accurate:** the baseline sizes (6,507, 9,467, 1,393, 40,797, 2,786, and 19,579 / 13,391 description characters); 14 descriptions over 300 among kept skills, total after the cap at most about 10,134; `workflow` 175, 181, 185-207, 450; `verify.py` 99-106, 2148, 2174; `validate_targets` 619-625, 703-708, ~4343, ~8217, ~8783, 9371; `generate_targets` 969-988, 1024, 1405, 1517-1519; test lines 1409, 1475, 3350, 3607, 460-462; prompt lines (coder 23 and 70, documenter 13 and 98, planner 9, 101, 121, orchestrator 3); skill lines (commit 46 and 57, code-review 26 and 38, setup-project 32, bentoml-service 30 and 104); README 254, 326, 358, 964, 1248; `docs/smoke-tests.md:276`; "there are 55" exists in `openwiki/`, so Phase D's check is not vacuous.

## Claude Code facts (docs read 2026-11-13)

**Verified:** names and descriptions are listed on every turn and bodies load only when used; the listing budget scales at 1% of the context window; on overflow the least-invoked skills lose their descriptions first and a warning goes to the debug log; `description` plus `when_to_use` is capped at 1,536 characters (configurable with `skillListingMaxDescChars`); `user-invocable: false` keeps the description in context and `disable-model-invocation: true` removes it; `skillListingBudgetFraction`, `SLASH_COMMAND_TOOL_CHAR_BUDGET`, `--debug-file` and `--bare` exist; CLAUDE.md loads at session start; rules without `paths:` load at launch and path-scoped rules load on Read, Write or Edit of a matching file, or on `cat`/`head` of one; Claude Code reads AGENTS.md only when there is no CLAUDE.md, so the AGENTS.md trim does not affect Claude Code; skill discovery runs from the start folder up to the repository root, nested folders load on demand, and `--add-dir` works.

**Unverified:** `/context` showing excluded skills; path-scoped rules loading inside subagents; the exact text of the overflow warning (item 9 captures it).

## Verification quality

- Phase A: `-k project_skill`, the `.project-skill` greps and the real-run test all fail before the change. `cmp` and `test -f .../.openwiki-install.json` are regression checks only.
- Phase B: every grep, size test and count fails before the change. The `wc -c` line is informational and can only fail on a missing file.
- Phase C: all checks fail first, except the coder line-70 gap (item 13).
- Phase D: the "loaded into every session", `.run.json` and OPENWIKI block checks are regression-only after Phase B. That is acceptable, but generation is missing (item 11).
- Run time: past closeout logs show the largest pytest items took at most 151 s, well inside the 600 s per-item limit.

## Questions for the user

No new HIGH-risk decision. The S5 "still overflows" row already routes that choice to the user. One optional MEDIUM decision (row 12): should the installer also refuse a refresh when an unmarked skill folder was never shipped by the bootstrap (it is not in the consumer's current `.agents/skills/`)? Yes protects existing consumers' own skills even if nobody adds a marker first, at the cost of about 15 more installer lines and one more refusal message. No keeps the opt-in marker and relies on the refresh skill's listing step, once item 2 is fixed.
