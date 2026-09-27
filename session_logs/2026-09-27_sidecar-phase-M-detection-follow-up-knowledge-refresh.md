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

## [LEARN] Entries

(pending)

## Verification

(pending)

## Stale-claims surfaces checked

(pending)

## Documentation

(pending)

## Open Questions / Next Steps

(pending)
