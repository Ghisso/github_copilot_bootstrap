# Session: Sidecar Phase M — detection follow-up knowledge refresh

**Date:** 2026-09-27
**Plan:** `.claude/plans/2026-09-27_phase-M-sidecar-detection-follow-up-knowledge-refresh.md`
**Status:** IN PROGRESS

## Goal

Refresh the generated OpenWiki pages after Phase L, then run the standing
final-phase audit of stale claims, as the big plan's final
knowledge-refresh phase.

## Work Log

- PRE-FLIGHT: Phase L committed as `883edf0` and pushed; the post-commit
  hook set Phase M to `in-progress` and the big plan's `current_phase` to
  it. Outer tree clean.
- Step 1, refresh: `openwiki_begin` (`mode: "update"`) returned run
  `8f754ccc-04a1-40e6-8155-890b6a75cf20` in planning at base `7d294ca`
  for most pages, with 26 stale or unresolved claims across six pages.
  The guard restored `AGENTS.md` and `CLAUDE.md` (status empty after the
  call). Plan submitted with the six pages that carried issues; no page
  added, moved, or deleted. Pages rewritten and submitted, in queue order:
  - `architecture/source-generated-consumer-layout.md`: the validator's
    forbidden-token list; one stale claim re-anchored and three claims
    whose validator ranges drifted by five lines corrected.
  - `operations/deterministic-verification.md`: the 480-second command
    budget and what a timeout reports; the stale budget claim and 13
    drifted `verify.py` ranges corrected, one new claim.
  - `operations/git-backed-ai-state-sync.md`: no prose change; the
    dispatch claim re-anchored to `main`, one drifted range corrected.
  - `operations/install-ownership-and-runtime-checks.md`: full evidence
    when `.claude` is tracked, the fresh-default rows, the marker remedy,
    the `git`-missing message, and the `--uninstall` target checks and
    option warning; five issue claims revised, two new claims, 15 drifted
    ranges corrected.
  - `operations/sidecar-overlay.md`: the pending record and lock file, the
    preflight and writability additions, the `OSError` abort, the bridge
    index rule, the pending-record row, dropped-skill precedence, alias by
    identity, frontmatter parsing, backslash names, user-line order, the
    gate diagnostic, the write order, dry-run, report wording, the
    still-ignored recheck, and empty-folder cleanup; 17 issue claims
    revised, seven new claims, every other cited range re-mapped.
  - `quickstart.md`: no prose change; two claims re-anchored.
  For every page a scratch script mapped each cited range from the page's
  recorded base to the current file (MEMORY lesson from Phase K).
- `openwiki_finish` returned `complete`. No other agent edited tracked
  files during the run (MEMORY lesson from Phase K).
- Known drift left for the next refresh: on the first page, one claim's
  re-cited `scripts/sidecar_overlay.py#L1986-L1999` range (the sidecar
  source check) had already moved to about `L2203`; the page job was
  complete before the map for that file existed. The other two resources
  of that claim are correct.
- Step 2, generated diff reviewed: 14 files changed under `openwiki/`
  (six pages, their six claim sidecars, `.page-manifest.json`, and
  `.last-update.json`, now `status: complete` at `gitHead 883edf0`);
  `git status --porcelain -- AGENTS.md CLAUDE.md` empty; no
  `openwiki/.run.json` left behind. No generated page was hand-edited
  outside the page loop.
- Step 3, the stale-claims audit, delegated to `documenter` after
  `openwiki_finish`, with the surfaces and topics from the small plan.

- Step 3 result: `documenter` made no edits. Every surface already
  reflected Phase L, whose own documentation step and review had checked
  the quoted messages against the final code; the audit re-verified each
  quote and the remaining surfaces directly against
  `scripts/install_bootstrap.py`, `scripts/sidecar_overlay.py`,
  `scripts/validate_targets.py`, and `shared/scripts/verify.py`.
- Step 4: no MEMORY entry was wrong after Phase L. One lesson added (below).
- Required items pre-checked on the refreshed tree: `validate_targets.py`
  PASS, `validate_plan_frontmatter.py` PASS, `verify.py fast` PASS.
- REVIEW round 1 (`reviewer`, all six profiles, on `git diff -- openwiki`):
  FAIL with one MAJOR and one MINOR. MAJOR: the quickstart claim on the
  verification entrypoints cited `README.md#L990-L999` and `#L1064`,
  which are the skill list and the Task Lanes paragraph; the mapping
  script had matched text that was already wrong at the page's base.
  MINOR: the forbidden-token sentence on the source-and-layout page read
  as an exhaustive list but omitted `third_party/`. The reviewer
  spot-checked well over 25 other evidence ranges and found them exact,
  found no contradiction with Decisions 48-58, and no style violation.
- Fix: both findings live in OpenWiki-owned claim files, so they were
  corrected through a second run, `openwiki_begin` with `mode: "update"`
  and `force: true` (run `de93b4d3-2130-40f8-b057-daca08933123`), with a
  two-page plan. The source-and-layout page now names `third_party/` and
  its claim statement matches; the same submission re-anchored the
  drifted `sidecar_overlay.py` range (`L2203-L2218`) noted earlier, so
  that item is closed. The quickstart claim now cites README's
  "Verification Defaults" section (`L1100-L1122`). `openwiki_finish`
  returned `complete`; the guard restored the adapters after both
  `openwiki_begin` calls.
- REVIEW round 2 (`reviewer`, `documentation` and `architecture`, on the
  delta since round 1): PASS, no findings; both round-1 findings and the
  re-anchored range confirmed against the files. Required items after the
  second run: `validate_targets.py` PASS, `validate_plan_frontmatter.py`
  PASS, `verify.py fast` PASS. Findings persisted with all six reviewed
  profiles across the two rounds and an empty surviving list.
- CLOSEOUT step 1: no human-authored documentation changed in this phase
  (the audit found nothing stale). Step 2: small plan `complete`, every
  box ticked, Phase M ticked in the big plan, lessons recorded.

## [LEARN] Entries

- [LEARN:documentation] Before submitting an OpenWiki page, map the cited
  ranges of every file the page cites, not only the file that carries the
  flagged claim; a re-cited range in another file can stay stale after the
  page job closes. Added to MEMORY.

## Verification

Optional items: none (the plan has no `## Optional Verification` section).
The required items' summary lines from `verify.py closeout --format text`
follow.

## Stale-claims surfaces checked

Audited by `documenter` against the code at `883edf0` after
`openwiki_finish`, then checked by the orchestrator. Topics: full-install
evidence when `.claude` is tracked in any form, the fresh-default
refusals, `--uninstall` target checks and option warnings, the marker
remedy and the `git`-missing message, tracked entries under a bridge path,
precedence for dropped skills, frontmatter parsing and alias by identity,
backslash retained names and user-line order, the pending ownership
record, file modes, `fsync`, the writability preflight, the filesystem
abort and the lock, report wording, empty-folder cleanup, uninstall exit-1
cases, the forbidden text tokens, and the 480-second verifier budget.

| Surface | Outcome |
| --- | --- |
| `README.md` | unchanged, accurate: every Phase L message quoted word for word (verified against the code) |
| `docs/architecture.md` | unchanged, accurate: restates nothing Phase L changed |
| `docs/target-mapping.md` | unchanged, accurate: the `.json.next` and `.lock` descriptions match the code |
| `docs/runtime-checks.md` | unchanged, accurate |
| `docs/smoke-tests.md` | unchanged, accurate |
| `docs/sidecar-provider-contract.md` | unchanged; dated client evidence untouched by Phase L |
| `shared/policies/*.instructions.md` | not applicable: none restates a Phase L behavior or the command budget |
| `shared/skills/` (`knowledge-refresh`, `plan-decomposition`, `safe-consumer-bootstrap-refresh`, `commit`, `setup-project`) | not applicable: no behavior claim from this plan |
| `shared/templates/plan-big.md`, `plan-small.md` | not applicable |
| `shared/agents/` prompts | not applicable: only the OpenWiki `.claims` sidecar is mentioned |
| docstrings and `--help` of `install_bootstrap.py`, `update_consumers.py`, `sidecar_overlay.py` | unchanged, accurate |
| `.claude/instructions/project-context.instructions.md` | unchanged, accurate |
| `CLAUDE.md`, `AGENTS.md` | unchanged, accurate (generated adapters) |
| `.claude/MEMORY.md` | unchanged, accurate: the verifier-budget lesson already states the 180 to 480 change; one new lesson added by the orchestrator |
| `openwiki/**` | refreshed through OpenWiki's tools: six pages, as the Work Log lists |

Dated records were left unchanged: archived plans, closed session logs,
`docs/2026-*`, and the five review reports.

## Documentation

No human-authored documentation needed a change in this phase; the
generated `openwiki/` pages were refreshed through OpenWiki's own tools.

## Open Questions / Next Steps

- This is the big plan's last phase. The post-commit hook marks the big
  plan `complete` after this commit. The user owns the PR to `dev` and the
  merge.
- Known limits carried forward: Antigravity is still unverified for the
  sidecar; a skill unit that is a cross-filesystem mount point and not a
  real folder is not refused in preflight (since Phase L a failed preserve
  ends in a clean `ABORT: filesystem error at <path>` and a rerun
  converges); `tests/test_validate_targets.py::test_validate_targets`
  alone takes about 57 s of the suite.
