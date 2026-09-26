# Session: Sidecar Phase K — follow-up knowledge refresh

**Date:** 2026-09-26
**Plan:** `.claude/plans/2026-09-26_phase-K-sidecar-follow-up-knowledge-refresh.md`
**Status:** COMPLETED

## Goal

Refresh the generated OpenWiki pages after Phase J, then run the standing
final-phase audit of stale claims, as the big plan's new final
knowledge-refresh phase.

## Work Log

- Phase K activated by the Phase J completion commit `7d294ca` (pushed).
- Material-impact check: Phase J landed exactly the behavior the Phase K
  plan lists as stale (unit boundaries, incomplete units, uninstall order,
  the gate, symlink handling in the name scans, line splitting, reports,
  and the settled-refresh identity rule). Two more details to check: the
  preserved-folder message on every uninstall, and the known limit on
  mounted non-folder units recorded in the Phase J log. No change to
  scope.
- Step 3 (the stale-claims audit) went to `documenter` in parallel with the
  refresh; it edits only human docs, never `openwiki/`.
- Step 1, refresh: `openwiki_begin` (`mode: "update"`) returned run
  `d1517b39-c09c-4d8f-a5f8-4589f4b611b7` in planning, with 16 stale or
  unresolved claims on 4 pages. Right after it, `git status --porcelain --
  AGENTS.md CLAUDE.md` was empty. Four other pages in an older window
  mention none of the changed topics (Phase I left them unchanged too);
  the AI-state sync page and the quickstart stay true, and no page was
  added or moved. The plan covered 4 pages:
  - `source-generated-consumer-layout`: prose accurate; the source-check
    claim and the self-install README claim point at moved lines.
  - `install-ownership-and-runtime-checks`: the agent-harness wording,
    the `--mode full` refusal's `--uninstall` hint, `--uninstall`'s
    preserved-folder line, and the `warn_tracked_paths` warning; two new
    claims; every moved `install_bootstrap.py` range revised.
  - `sidecar-overlay`: rewritten for repository boundaries at skill
    folders, incomplete units, the one read-folder enumerator, line
    splitting, retained files of dropped skills, the gate's paths and
    symlink spelling, fail-closed Git errors, the kept-conflict report,
    and uninstall on the install's write order; 13 issue claims revised,
    7 moved claims revised, 11 new claims.
  - `lifecycle-and-task-lanes`: the settled-refresh identity rule; the
    stale validator claim revised, and five claims whose ranges had drifted
    since before Phase F corrected (the orchestrator loop, the completion
    contract, the closeout sequence, the lints, and the branch-state hooks).
  To find moved ranges, a scratch script mapped each cited range from the
  recorded base `f7d9af4` to the current file and flagged changed text.
- `openwiki_finish` returned `complete` with `sourceChanged: true`, and
  `.last-update.json` said `interrupted` at `f7d9af4`: the parallel audit
  had edited `README.md` and `docs/runtime-checks.md` during the run. A
  second `update` run (`ff154a32-67a0-4781-b435-86a143b75bc5`) showed no
  claim issues and the four pages at base `7d294ca`; it submitted an empty
  plan and finished `complete`. `.last-update.json` now records
  `7d294ca`, `status: complete`; `openwiki/.run.json` is absent;
  `AGENTS.md` and `CLAUDE.md` are unchanged.
- Step 2, diff review: 13 OpenWiki files changed (4 pages, their claim
  files, the operations index for the new sidecar description, the
  manifest, and `.last-update.json`). No page was edited outside the page
  loop. The sidecar page describes every item in step 2's list.
- Step 3 audit landed: three corrections (README's "Skill name taken"
  symlink rule, README's kept-conflict remedy under "Preserved copies",
  and `docs/runtime-checks.md`'s settled-refresh row); every other surface
  was accurate. Checked against the code by the orchestrator.
- Step 4: the audit found no stale MEMORY entry, but one was: the Phase H
  review lesson named `preserved_conflicts` as the authoritative set, which
  O3 showed was too broad. Corrected to say the authoritative set is the
  one the planner decided (`kept_conflicts`).
- Early run of the required items: `validate_targets.py` PASS, plan
  validation PASS, `verify.py fast` PASS.
- REVIEW (one `reviewer`, all six profiles): PASS with no findings. It
  spot-checked 26 claim ranges across the four claim files (all match),
  confirmed the named tests exist, checked the audit edits and the MEMORY
  correction against O3, and swept extra surfaces (docs, templates, the
  `knowledge-refresh` skill, project context, and module docstrings) with
  no contradiction of Decisions 37-47. No em-dash was added to the pages.
- CLOSEOUT started.

## [LEARN] Entries

- [LEARN:tooling] Do not let another agent edit tracked files while an
  OpenWiki run is open. The parallel audit changed `README.md` mid-run, so
  `openwiki_finish` returned `complete` with `sourceChanged: true` and
  recorded `status: interrupted` at the old base. A second `update` run
  with an empty plan settled it at `7d294ca`. Added to MEMORY.
- [LEARN:documentation] OpenWiki flags a claim only when its cited text
  changes, so a range that drifted because an earlier phase inserted text
  above it stays unflagged: five lifecycle-page claims had pointed at the
  wrong section since Phase F. Map every cited range on a rewritten page
  from the recorded base to the current file and check the text there.
  Added to MEMORY.
- MEMORY correction (not a new lesson): the Phase H review lesson now names
  the planner's `kept_conflicts` as the authoritative set (O3).

## Verification

Required items (`verify closeout --format text` summary lines):

```text
PASS       53.3s  uv run python scripts/validate_targets.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS        0.3s  uv run python .claude/scripts/verify.py fast --format json
```

`verify.py phase --format json --persist`: PASS (ruff, mypy, full pytest
with 2143 passed, freshness, generated runtime). Findings report:
`.claude/quality_reports/findings-2026-09-26_phase-K-sidecar-follow-up-knowledge-refresh.json`
(0 critical, 0 major, 0 minor; `ponytail_reviewed=true`). The plan has no
optional verification items.

## Stale-claims surfaces checked

Audited by `documenter` against the code at `7d294ca`, then checked by the
orchestrator. Topics: nested repositories and submodules at skill folders,
incomplete units and special files, uninstall after a profile change and
preserve conflicts, what the gate covers, symlinked read folders and
aliases, case variants at write roots, line splitting, retained files of
dropped skills, report wording, the settled-refresh identity rule, and the
"agent-harness path" wording.

| Surface | Outcome |
| --- | --- |
| `README.md` | corrected: the "Skill name taken" row now says a symlink that resolves into a write root only mirrors it and never collides; "Preserved copies" now gives the kept-conflict remedy. Phase J's own README edits were already accurate. |
| `docs/architecture.md` | unchanged, accurate |
| `docs/target-mapping.md` | unchanged, accurate |
| `docs/runtime-checks.md` | corrected: the settled-refresh row states the identity check |
| `docs/smoke-tests.md` | unchanged, accurate (no sidecar content) |
| `docs/sidecar-provider-contract.md` | unchanged; Phase A's dated native-run evidence, unaffected |
| `shared/policies/` | unchanged, accurate (Phase J rewrote the Termination paragraph) |
| `shared/skills/` (`knowledge-refresh`, `plan-decomposition`, `safe-consumer-bootstrap-refresh`, `commit`) | unchanged, accurate (they point to the canonical rule) |
| `shared/templates/plan-big.md`, `plan-small.md` | unchanged, accurate (pointers only) |
| `shared/agents/` prompts | unchanged, accurate |
| docstrings and `--help` of `install_bootstrap.py`, `update_consumers.py`, `sidecar_overlay.py`, `validate_plan_frontmatter.py` | unchanged, accurate (Phase J wrote them) |
| `.claude/instructions/project-context.instructions.md` | unchanged, accurate |
| `CLAUDE.md`, `AGENTS.md` | unchanged, accurate |
| `.claude/MEMORY.md` | corrected by the orchestrator: the Phase H review lesson now names the planner's `kept_conflicts` as the authoritative set, not the caller's `preserved_conflicts` (O3) |
| `openwiki/**` | refreshed through OpenWiki's tools: four pages, as the Work Log lists |

Dated records were left unchanged: archived plans, closed session logs,
`docs/2026-*`, and the four review reports.

## Documentation

Updated in this phase:

- `openwiki/**`: four pages refreshed through OpenWiki's own tools
  (`sidecar-overlay`, `install-ownership-and-runtime-checks`,
  `lifecycle-and-task-lanes`, `source-generated-consumer-layout`), plus
  OpenWiki's own index, manifest, claim files, and `.last-update.json`.
- `README.md`: the "Skill name taken" symlink rule and the kept-conflict
  remedy under "Preserved copies".
- `docs/runtime-checks.md`: the settled-refresh row.

## Open Questions / Next Steps

- This is the big plan's last phase. The post-commit hook marks the big
  plan `complete` after this commit. The user owns the PR to `dev` and the
  merge.
- Known limits: Antigravity is still unverified for the sidecar (no client
  was available for a native run). A skill unit that is a mount point from
  another filesystem and not a real folder is not refused in preflight;
  preserving it would fail mid-apply with an unhandled `OSError` (recorded
  in the Phase J log as a possible later hardening).
