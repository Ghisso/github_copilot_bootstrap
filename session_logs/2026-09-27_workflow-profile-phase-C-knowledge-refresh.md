# Session: Workflow profile Phase C — knowledge refresh

**Date:** 2026-09-27
**Plan:** `.claude/plans/2026-09-27_phase-C-workflow-profile-knowledge-refresh.md`
**Status:** COMPLETED

## Goal

Refresh the generated OpenWiki pages after Phases A and B, audit the live
advice surfaces for stale claims, and close the big plan with the
final-phase gates.

## Work Log

- PRE-FLIGHT: Phase B committed as `753c354` and pushed; the post-commit
  hook set Phase C to `in-progress`. Outer tree clean.
- Step 1, refresh: `openwiki_begin` (`mode: "update"`) returned run
  `0205cf19-5f12-48a2-9ecf-750cba2888a1` in planning, with 29 stale or
  unresolved claims across six pages (bases `294382d`, `7d294ca`, and
  `883edf0`). The guard restored `AGENTS.md` and `CLAUDE.md` (status empty
  after the call). Plan submitted with the six pages that carried issues;
  no page added, moved, or deleted. Pages rewritten and submitted, in queue
  order, each with every cited range mapped from its recorded base to the
  current file by a scratch script (`map_ranges.py`):
  - `architecture/agents-and-skills.md`: `workflow-prompt.md` per canonical
    agent, `claude_agent_frontmatter` shared, `sidecar_agent_frontmatter`
    stripping `mcp__` grants; the stale claim re-anchored, one new claim,
    13 drifted ranges corrected.
  - `architecture/source-generated-consumer-layout.md`: the two profile
    trees, `render_sidecar(target_root, profile)`, the workflow units, the
    per-profile forbidden-token lists and allowlist; four issue claims
    revised, two new claims, eight drifted ranges corrected.
  - `operations/git-backed-ai-state-sync.md`: `--backup-state` and the
    state folder named as a plain ignored folder; one claim re-anchored.
  - `operations/install-ownership-and-runtime-checks.md`: `--profile`,
    `default_sidecar_source`, `--purge-state`, `--backup-state` with
    `--dry-run`, the full-only warnings, the updater forwarding no profile;
    three issue claims revised, three new claims, 15 drifted ranges
    corrected.
  - `operations/sidecar-overlay.md`: the two profiles and every unit kind,
    the state folder's rules and messages, manifest schema 2, agent
    precedence by identity, the shared enumerator, the report counts and
    kind words, uninstall keep and purge, the extended empty-folder
    cleanup, profile switching, the `git clean -x` limit, and the scenario
    test; 19 issue claims revised, five new claims.
  - `quickstart.md`: a row for the workflow profile; one claim re-anchored.
- `openwiki_finish` returned `complete`. No other agent edited tracked
  files during the run.
- Step 2, generated diff reviewed: 16 files changed under `openwiki/` (six
  pages, their claim sidecars, `.page-manifest.json`, and
  `.last-update.json`, now `status: complete` at `gitHead 753c354`);
  `git status --porcelain -- AGENTS.md CLAUDE.md` empty; no
  `openwiki/.run.json`; no OpenWiki workflow file. No generated page was
  hand-edited outside the page loop.
- Step 3, the stale-claims audit, run by the orchestrator instead of
  `documenter` to stay inside the organization's spend limit: every
  surface grepped for pre-profile wording (`dist/sidecar/` as one tree,
  "four skills" without a profile, the old constant names, the template
  passages) and each hit read in context. Fixed: two comments in
  `scripts/generate_targets.py` that still said only the two plan templates
  are rewritten (all four relaxed templates are); README's source-contract
  bullet and `docs/architecture.md`'s source-contract paragraph, which
  described only the skills profile's allowlist; `scripts/update_consumers.py`'s
  docstring, which said only skill and bridge files change; and
  `.claude/instructions/project-context.instructions.md`, which named
  `dist/sidecar/` as one tree. Left as is: parent-folder references to
  `dist/sidecar/` in README, `AGENTS.md`, and `docs/target-mapping.md`
  (each is followed by the profile trees), the historical "same four
  skills" line in the provider contract's 2026-09-25 evidence, and the
  `DEFAULT_SIDECAR_SOURCE` mention in `default_sidecar_source`'s docstring,
  which explains what replaced it.
- Verification items pre-checked on the audited tree: ruff and format
  clean, `validate_plan_frontmatter.py` PASS, `validate_targets.py` PASS,
  `verify.py fast` PASS, and a `verify.py phase --format text` dry run PASS
  (2260 tests).
- REVIEW round 1 (`reviewer`, six profiles, artifact `phase-C-wp.diff`,
  2277 lines): NOT CLEAN, 2 MAJOR and 1 MINOR, all `documentation`. The
  first run's finalization had replaced `operations/sidecar-overlay.md`'s
  frontmatter with a fallback (`type: "Reference"`, no description or
  tags) because the new description held an unquoted colon, and the
  operations index therefore lost that page's one-line summary; and the
  page called the Antigravity agent entry `reviewer/agent.md` instead of
  the folder `reviewer/`. Every other statement in the six pages was
  confirmed against the code; the scripts diff was confirmed
  comment-only.
- Fix through a second refresh run, never by hand-editing a generated
  page: `openwiki_begin` (`mode: "update"`) returned run
  `a89c74d5-4a1d-4c10-b165-71b6842655fa` at base `753c354` with two stale
  claims (both on `render_sidecar_workflow_units`, whose docstring the
  audit changed). Plan of three pages: `agents-and-skills.md` and
  `source-generated-consumer-layout.md` (each stale claim rechecked and
  confirmed unchanged), and `sidecar-overlay.md` (frontmatter restored
  with a quoted description and the sibling pages' `type: operations` and
  tags, and the Antigravity entry reworded as the folder `reviewer/`).
  `openwiki_finish` returned `complete`; the operations index regained the
  page's summary; adapters unchanged; no `openwiki/.run.json`.
- REVIEW round 2 (same reviewer, six profiles, fix-only diff plus the
  refreshed artifact): CLEAN, each fix confirmed against the files on disk,
  frontmatter parsed with PyYAML, no new finding.
- Step 4: three lessons recorded (below and in MEMORY). Step 5: closeout
  sequence follows; this is the big plan's final phase.

## [LEARN] Entries

- [LEARN:documentation] Make the stale-claims audit's source fixes (comments
  and docstrings) after `openwiki_finish`, and keep each replacement at the
  same line count, so the ranges the refreshed pages just cited do not
  shift and the next refresh reports no drift from the audit itself. Added
  to MEMORY.
- [LEARN:tooling] An OpenWiki page job lists only its stale or unresolved
  claims; an issue-free claim whose cited range merely moved can be
  resubmitted with the same id and the mapped range in the same
  `openwiki_submit_page` call, which keeps the whole page's evidence
  current instead of only the flagged claims'. Added to MEMORY.
- [LEARN:tooling] Quote an OpenWiki page's `description:` whenever it
  contains a colon. An unquoted colon makes the frontmatter invalid YAML,
  and `openwiki_finish` silently replaces the whole frontmatter with a
  fallback (`type: "Reference"`, no description or tags), so the folder
  index loses that page's summary. Parse the frontmatter with a YAML
  reader before submitting the page. Added to MEMORY.

## Verification

Optional items: none (the plan has no `## Optional Verification` section).

`verify.py phase --format json --persist`: PASS (Ruff, mypy, pytest 2260
passed, freshness, provenance, generated runtime). Findings report: 0
critical, 0 major, 0 minor, six profiles, `dirty: false`.

Required items from `verify.py closeout --format text`:

```text
PASS       51.3s  uv run python scripts/validate_targets.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS        0.3s  uv run python .claude/scripts/verify.py fast --format json
closeout: PASS
```

## Documentation

`README.md` (source-contract bullet) and `docs/architecture.md`
(source-contract paragraph) corrected by the audit; `openwiki/` refreshed
through OpenWiki's page loop (six pages). No other public behavior changed
in this phase.

## Stale-claims surfaces checked

| Surface | Outcome |
| --- | --- |
| `README.md` | one fix: the source-contract bullet now names `dist/sidecar/<profile>/` and the per-profile allowlist; the Personal Sidecar Install section was written by Phase B's documenter and re-verified against the code |
| `docs/architecture.md` | one fix: the source-contract paragraph now covers both profiles' allowlists and the whole-skill-folder rule |
| `docs/target-mapping.md` | no change: the profile trees and unit rows from Phase B hold |
| `docs/sidecar-provider-contract.md` | no change: the 2026-09-25 evidence is historical; the 2026-09-27 workflow-profile evidence matches the shipped coverage |
| `docs/runtime-checks.md` | no change: names no sidecar detail |
| `shared/policies/` | no change: no policy names the sidecar's contents |
| skills describing installer ownership (`safe-consumer-bootstrap-refresh`, `knowledge-refresh`) | no change: neither names the sidecar's units |
| `shared/templates/` and `shared/sidecar/workflow/templates/` | no change |
| agent prompts (`prompt.md`, `workflow-prompt.md`) | no change: the workflow prompts were written for the profile in Phase A |
| `scripts/install_bootstrap.py` docstrings and `--help` | no change: `--profile`, `--purge-state`, `--backup-state`, and the uninstall help already describe the profile behavior |
| `scripts/update_consumers.py` docstring | one fix: a sidecar consumer is updated in the profile its manifest records, not "only its skill and bridge files" |
| `scripts/sidecar_overlay.py` docstrings | no change: written with the profile work |
| `scripts/generate_targets.py` comments | two fixes: the path-rewrite comment and the `render_sidecar_workflow_units` docstring said only the two plan templates are rewritten |
| `.claude/instructions/project-context.instructions.md` | one fix: `dist/sidecar/<profile>/` |
| root guidance (`AGENTS.md`, `CLAUDE.md`) | no change: `dist/sidecar/` there names the parent folder of both profile trees |
| `.claude/MEMORY.md` (report only) | no entry contradicts the profile decisions; the sidecar lessons describe mechanisms (exclude block, precedence, preserved copies) that still hold |
| `openwiki/` | refreshed through the page loop above |

## Open Questions / Next Steps

- The big plan is complete after this commit. The user decides on the pull
  request to `dev`.
- Copilot and Codex still get no workflow agents from the sidecar; revisit
  only if a client adds a config-free way to discover an agent from an
  ignored file.
