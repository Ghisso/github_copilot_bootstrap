# Session: OpenWiki Phase K — knowledge refresh

**Date:** 2026-09-21
**Plan:** `.claude/plans/2026-09-19_phase-K-knowledge-refresh.md`

**Status:** IN-PROGRESS

Phases I and J were transition phases (first enablement and the one-time
docs migration). This phase is the normal knowledge-refresh shape that
every future OpenWiki-enabled big plan ends with: one host-driven refresh,
inspection of the generated diff, the standing final-phase stale-claims,
memory, and LEARN audit, then review, verify, commit. One addition specific
to this run: the user asked for a page-style change after inspecting the
Phase I wiki, so Step K0 adds a style section to the brief and Step K1 runs
the refresh as a rebaseline so every page is regenerated in the new style.

## Goal

Add the page-style section to `openwiki/INSTRUCTIONS.md`, regenerate the
wiki under it against the post-migration source, audit every live-advice
surface for claims this big plan invalidated, and close the big plan.

## Work Log

- Phase started 2026-09-21 after Phase J's completion commit `294382d`.
  Step K0 and the rebaseline shape of K1 were added to the plan on the
  user's request: "ok add instructions for style in phase K. you should
  model them on your own language instructions (simple, no jargon,
  everything clearly explained, avoid long paragraphs and use lists,
  charts ...)".
- Step K0 (fresh documenter): `## Page style` section inserted in
  `openwiki/INSTRUCTIONS.md` between "What to prioritize" and "Historical
  records are not current behavior", 67 lines, grouped under bold lead-ins
  Structure, Sentences and words, Lists and tables, Diagrams, and Code,
  paths, and enforcement, with a four-node Mermaid example and the rule
  that a page states when a hook, validator, or test enforces a rule it
  describes. Nothing else in the brief changed. Orchestrator approved the
  wording; documentation-profile review requested before K1.
- Step K0 review (`documentation` profile, two passes): PASS with two
  advisory MINORs, both sentences in the new section that broke its own
  20-word rule; the reviewer's replacement wording was applied. The section
  covers every item in the plan's Content list; the Mermaid example parses
  with the installed `mermaid` package; no contradiction with OpenWiki's own
  page contract; nothing outside the section changed.
- Step K1, rebaseline refresh on the main thread. Kept
  `openwiki/INSTRUCTIONS.md`, removed everything else under `openwiki/`,
  then `openwiki_begin(root=<repo>, mode=update)` returned `status: active`,
  `phase: planning`, `lastUpdate: null`; adapters clean and snapshot
  directory empty afterwards. Plan submitted with nine pages: the eight
  Phase I pages plus the new `operations/context-mode-dispatcher.md` for the
  brief's Context Mode coverage item added in Phase J. Nine
  `openwiki_next_page` / write / `openwiki_submit_page` cycles in alphabetical
  path order; every page rewritten in the new style (opening authority
  sentence, lists for parallel facts, numbered sequences, one Mermaid
  `flowchart` or `sequenceDiagram` with a lead-in sentence, no hard-wrapped
  prose or cells, enforcement named in the same sentence as the rule,
  Related pages). The state-sync page now cites `state-sync.sh` and the
  installer rather than `docs/architecture.md`, whose Git-Backed State Sync
  section Phase J shortened. `openwiki_finish` returned `status: complete`.
- Step K1 acceptance: adapters porcelain empty; no workflow file; snapshot
  directory empty; `openwiki/.run.json` absent; zero `mermaid parse failed`
  comments; every page has a Mermaid block; changes confined to
  `openwiki/**` (22 files changed, 953 insertions, 1254 deletions, plus the
  new page and its claims sidecar). `verify.py phase --format text` PASS:
  ruff 0, mypy 0, pytest 1759 passed, `VFY-GEN-001` PASS.
- Step K2, wiki surfaces (orchestrator): `openwiki/INSTRUCTIONS.md`,
  `quickstart.md`, and the four `index.md` files swept for the retired-design
  vocabulary. One hit, "hook-event runner" in the operations index
  describing the Context Mode dispatcher, is accurate and unrelated to the
  retired OpenWiki runner. No stale claim.
- Step K3 review round 1 (`code`, `architecture`, `security`, `tests`,
  `documentation`, `ponytail`; two passes plus a convergence pass): 0
  CRITICAL, 1 MAJOR, 3 MINOR. All ten Mermaid blocks parsed with
  `mermaid@11.16.0` under `jsdom@29.1.1`; every page met the style contract
  except the items below; three or more claims per page matched source; no
  secrets or AI-state content; nothing outside `openwiki/` changed.
  - MAJOR: the Context Mode page said hook mode checks for Node like server
    mode does; only the server branch (`context-mode-dispatch.sh` lines
    309 to 318) checks `command -v node`. Fixed through a corrective
    OpenWiki `update` run (not a hand edit): plan with the two affected
    pages, `openwiki_inspect_page_claims` to get the claim id, the sentence
    rewritten, the claim `claim_ee848aeb09444f659c02cce859a8a3a5` revised
    with evidence split into lines 288 to 307, 309 to 318, and 320 to 330,
    `openwiki_finish` returned `complete`.
  - MINOR (two pages): Mermaid node labels longer than "a few words" on the
    installer and cache-quarantine diagrams. Fixed in the same run: labels
    shortened, detail moved to a sentence under the diagram.
  - MINOR: the brief's "Do not use em-dashes" rule had no carve-out for a
    backtick-quoted exact required string (two pages quote the required
    `- optional <n>: PASS|FAIL|NOT RUN — <detail>` grammar verbatim). Fixed
    in the brief, which is human-authored: the rule now excepts a
    backtick-quoted exact required string.
  - Dropped by the reviewer: the OpenWiki-owned `index.md` files lack the
    style elements; they are generated indexes, not authored pages.

## Stale-claims surfaces checked

Audit targets from Step K2: subprocess runner, child process, `flock`, or
control-plane fingerprinting claims; "never install host integrations"
wording; scheduled, automatic, or credential-needing OpenWiki claims; guard
claims contradicting the per-host spike outcome; hand-editable root adapters
or MEMORY as architecture authority; stale version claims (Node 22.22.0,
`context-mode` 1.0.169, `openwiki@0.5.2`, `mermaid@11.16.0`,
`jsdom@29.1.1`); Phase A residual limits. Swept with `rg -n -i` over the
full pattern set, every hit read in context (documenter, read-only).

| Surface | Outcome |
| --- | --- |
| Root guidance `AGENTS.md`, `CLAUDE.md`, `README.md` | CURRENT. The OpenWiki sentence names `knowledge-refresh`; no runner, subprocess, or `init` wording. No generator-string change needed. |
| Live `docs/architecture.md`, `runtime-checks.md`, `smoke-tests.md`, `target-mapping.md`, `native-client-acceptance.md`, `plan-deterministic-commit-gate.md` | CURRENT. The OpenWiki Knowledge Layer section states the host-driven design and the per-host restore split; "residual limits inherited from the earlier runner design" is provenance of a still-valid guard limit, not a claim the runner exists. Other hits are the CI runner, the native-client probe runner, or AI-state fingerprints. |
| Dated `docs/2026-*` (four files) | HISTORICAL, untouched. |
| `shared/policies/**` | CURRENT. OpenWiki Refresh and Knowledge-Refresh Final Phase sections match the code. Zero hits for the retired-design vocabulary. |
| `shared/skills/**` (55 skills; hits in 14) | CURRENT. `knowledge-refresh/SKILL.md` read in full and accurate; other hits unrelated. Zero repository-wide matches for the old `skills/openwiki/SKILL.md` path as the refresh owner. |
| `shared/templates/**`, `shared/agents/**`, `shared/review-profiles/**` | CURRENT. Planner, orchestrator, documenter prompts and the big-plan template point at the canonical rule and the new skill name. |
| State READMEs (`shared/plans`, `shared/session_logs`, `shared/quality_reports`); `shared/explorations` absent | No hits. |
| `shared/MEMORY.md` | No hits. |
| Live `.claude/MEMORY.md` | Entries about the retired runner are explicitly labelled as carried lessons (HISTORICAL); per-host restore and `openwiki@0.5.2` entries are CURRENT. No edit. |
| `shared/devcontainer/**`, `.devcontainer/**` | CURRENT. Pins match exactly; authoring and generated Dockerfiles are byte-identical. |
| `openwiki/INSTRUCTIONS.md` and the generated quickstart and index pages (after the K1 rebaseline) | CURRENT. No retired-design vocabulary; the only "runner" hit describes the Context Mode dispatcher's hook-event role, not OpenWiki. The brief's Page style section changed no scope, priority, or historical-records rule. |

Non-documentation observation: `shared/scripts/__pycache__/openwiki_refresh.cpython-313.pyc` is a stale bytecode artifact of the retired runner; `__pycache__` is git-ignored, so it is a local leftover only.

## Review findings and dispositions

Round 1: 0 CRITICAL, 1 MAJOR, 3 MINOR (see the Work Log). All four were
fixed rather than dispositioned: the MAJOR and two MINORs through a
corrective OpenWiki update run, the third MINOR in the human-authored brief.
Round 2 (same reviewer, delta only): PASS, no surviving findings; the
revised claim's evidence split was confirmed against the script; Mermaid
10 of 10 parse; changes remain confined to `openwiki/`. Final: 0 findings
across `code`, `architecture`, `security`, `tests`, `documentation`,
`ponytail`.

## [LEARN] Entries

- [LEARN:documentation] OpenWiki fixes structure, claims, and validation;
  the writing agent fixes page style. A style change therefore goes in the
  brief's `## Page style` section, and applying it to existing pages needs a
  rebaseline (keep `openwiki/INSTRUCTIONS.md`, remove the rest, `update`),
  because an incremental update rewrites only pages whose source changed.
- [LEARN:documentation] When a human doc is shortened, wiki claims that cited
  it by line range go stale even though the fact is unchanged. Cite the
  script or test that implements a fact, not the human doc that describes
  it, so a later doc edit does not invalidate the evidence.
- [LEARN:workflow] A style section that states a sentence-length rule must
  itself obey it; the reviewer caught two sentences in the new section that
  broke the rule they stated. Read a new instruction block against its own
  rules before submitting it.

## Verification

(pending: paste `verify closeout --format text` summary lines)

- optional 1: NOT RUN — no Codex session was available in this phase; the Codex guard re-probe remains an interactive check for a future Codex session and does not block this refresh, which ran on Claude Code where the guard was re-probed in Phase I.

## Open Questions / Next Steps

- This is the big plan's last phase. After this commit every phase of
  `2026-09-19_openwiki-knowledge-layer-integration` is complete or
  cancelled; the user owns the PR to `dev` and the merge.
- Follow-ups carried: the Codex guard re-probe (optional, interactive);
  `verify closeout` traceback when the findings report is missing (MINOR,
  from Phase F2); the overlay refresh removing the nested `.claude/.gitignore`
  that `state-sync.sh` recreates; a stale `__pycache__` bytecode file of the
  retired runner (git-ignored, local only).
- Future knowledge refreshes follow this phase's shape without Step K0 and
  without the rebaseline: `update`, inspect the diff, audit, review, verify,
  commit.
