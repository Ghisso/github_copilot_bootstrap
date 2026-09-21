# Brief: follow-ups carried out of the OpenWiki knowledge-layer big plan

**Date:** 2026-09-21
**Author:** orchestrator session (Claude Fable 5.1), at the close of big plan
`2026-09-19_openwiki-knowledge-layer-integration` (branch
`2026-09-19_openwiki-knowledge-layer-integration_implementation`, final commit
`27c059d`, all 11 live phases complete, D and E cancelled).
**Status:** OPEN. Nothing here blocks the PR to `dev`. Each item is small;
together they fit one small plan.
**Why an exploration and not a phase:** the big plan's last phase is
`2026-09-19_phase-K-knowledge-refresh`. `scripts/validate_plan_frontmatter.py`
requires a `-knowledge-refresh` phase to be the last phase and the only one,
so no phase can be appended to this plan, and the rule is a deliberate
recursion guard from the workflow policy's Knowledge-Refresh Final Phase
section. The fixes go in a new one-phase big plan after the merge, or as an
early phase of the next big plan that touches these files.

## What I want from the next session

Treat the items below as ready-to-plan facts, not as a plan. Re-read each
cited location before editing; three phases of this plan changed line
numbers in the docs. Group items 1 to 4 into one small plan with profiles
`documentation`, `architecture`, `security`, `code` (the generator string is
code), and `ponytail` (multi-file diff). Items 5 to 8 are independent and can
stay carried.

## A. Instruction-clarity findings from the final review (2026-09-21)

Source: a two-pass `documentation` and `architecture` review of every
OpenWiki instruction surface after Phase K. The reviewer confirmed the
mechanism is described once and consistently everywhere and found no
contradiction with the hook configurations or scripts. These four wording
items survived.

### 1. MAJOR: the root-guidance OpenWiki sentence has three variants

The sentence that introduces OpenWiki to a new maintainer differs across
the files that are meant to carry it identically:

- `CLAUDE.md:14` uses a comma: "...is just-in-time repository context, never
  authority...".
- `AGENTS.md:9` uses an em dash: "...is just-in-time repository context — never
  authority...".
- `scripts/generate_targets.py:1321` (`render_root_guidance`, the string that
  renders both files for consumers) says "Refresh only through
  `.claude/skills/knowledge-refresh/SKILL.md`;" where the tracked root files
  say "Refresh only by calling OpenWiki's own MCP tools per
  `.claude/skills/knowledge-refresh/SKILL.md`;".
- All three say "just-in-time repository context". The central rule in
  `shared/policies/workspace.instructions.md` (Knowledge Ownership) and
  `README.md:16` say "derived context". The pages are pre-generated and
  refreshed by a person, so "derived" is also the accurate word.

Fix: one exact sentence in all three places. Proposed text:

> An optional OpenWiki knowledge layer, enabled when `openwiki/INSTRUCTIONS.md`
> exists, is derived context, never authority over source, tests, or policy.
> Refresh only by calling OpenWiki's own MCP tools per
> `.claude/skills/knowledge-refresh/SKILL.md`; never hand-edit a generated page
> or commit OpenWiki's own root snippet.

Edit the generator string first, then make the two tracked authoring files
match it byte for byte. `validate_targets.py` checks root-source mirror
cases, so run it after the edit. Note that Phase H's sweep named all three
locations as one target; the generator string was updated to the new skill
path but not to the same wording, which is how the variants arose.

### 2. MINOR: the quickstart's refresh row omits the guard's entry point

`openwiki/quickstart.md`, the "refresh this wiki" row, lists only
`shared/hooks/scripts/openwiki-guard.py`. The command people run is
`bash .claude/hooks/scripts/openwiki-guard.sh post </dev/null`; the `.sh`
wrapper handles stdin and fail-closed behaviour, and `.py` is not an
alternate entry point. Fix: add `shared/hooks/scripts/openwiki-guard.sh` to
that cell. This is a generated page, so the fix is one scoped OpenWiki
`update` run (plan with only `/openwiki/quickstart.md`; no claim change
needed), never a hand edit.

### 3. MINOR: an undefined term in the canonical refresh rule

`shared/policies/workflow.instructions.md`, Knowledge-Refresh Final Phase,
Shape paragraph, ends with "It does not carry a larger phase's transition
scope." No canonical surface defines a transition phase; the only
explanation is in Phase I's session log, which the brief itself classifies
as historical evidence. Fix: replace the sentence with self-contained
wording, for example: "Keep it this small even for a checkout's first
enablement; do not fold a larger one-time rollout's setup work into it."
The policy is authoring source; `generate_targets.py --all` and the self
overlay refresh propagate it.

### 4. MINOR: the brief breaks its own em-dash rule

`openwiki/INSTRUCTIONS.md` now says "Do not use em-dashes, except inside a
backtick-quoted exact required string", but the brief's own prose uses seven
em dashes (lines 34, 42, 44, 46, 143, 145, 147 at the time of review), none
inside a quoted string. The brief is the document that models the standard
for generated pages. Fix: replace each with a colon, semicolon, or period.
The brief is human-authored and may be edited directly; no OpenWiki run is
needed for this item alone, but item 2 already needs one, so do item 4 first
and let that run read the corrected brief.

Not a finding: the skill's "Approve the project MCP server the installer
adds when Claude Code asks" is conditional wording. Claude Code did not
prompt in Phase I; the wording still holds.

## B. Follow-ups carried from earlier phases

### 5. MINOR: `verify closeout` traceback when the findings report is missing

From Phase F2 (`.claude/session_logs/2026-09-19_openwiki-phase-F2-verification-evidence-guardrails.md`,
"Known follow-up"): `verify closeout` raises an unhandled traceback from
`relative_artifact` in `shared/scripts/verify.py` when
`.claude/quality_reports/findings-<phase>.json` does not exist yet, instead
of naming the missing file and the `record_findings.py` step. Pre-existing.
Carried through G, H, I, J, K without a fix. Fix shape: catch the missing
file in `closeout_artifacts` or `relative_artifact` and exit 2 with a
one-line message naming the path and the recording command; one test in
`tests/test_verify.py`. Profiles `code`, `tests`, `ponytail`.

### 6. LOW: the overlay refresh removes the nested `.claude/.gitignore`

From Phase G (`.claude/session_logs/2026-09-19_openwiki-phase-G-host-driven-guard.md`,
Work Log, VERIFY round 1): `install_bootstrap.py . --local-only --allow-self`
reports `.claude/.gitignore` as an obsolete generated file and removes it;
`state-sync.sh` recreates it on the next checkpoint with `.cache/` and
`session_logs/hooks-errors.log` ignored. Harmless in practice because
`checkpoint` runs inside the same installer invocation, but the file should
not be classified as bootstrap-owned in the first place. Fix shape: exclude
`.gitignore` at the nested root from `owned_files()` in
`scripts/install_bootstrap.py` (it is written by `state-sync.sh`, not
generated), with a test in `tests/test_install_bootstrap.py`. Confirm first
that `check_runtime.py` does not then flag it as drift.

### 7. OPTIONAL: Codex re-probe of the OpenWiki guard

Carried as optional item 1 in Phases I and K, both `NOT RUN` because no
Codex session was available. In a Codex session in this checkout: call
`openwiki_begin` with `mode: "init"` and confirm the PreToolUse deny (spike
outcome O2 says Codex honours the deny); then call `openwiki_begin` with
`mode: "update"` in a state where the wiki is current, confirm `noop`, and
confirm `git status --porcelain -- AGENTS.md CLAUDE.md` is empty after the
turn ends (the Stop hook's payload-free `openwiki-guard.sh post`). Record
the result in whichever plan's session log is open. If Codex does not honour
the deny, that is a design input for the guard, not a wording fix.

### 8. TRIVIAL: stale bytecode of the retired runner

`shared/scripts/__pycache__/openwiki_refresh.cpython-313.pyc` remains on this
machine from the retired Phase A runner. `__pycache__/` is git-ignored
(`.gitignore:9`), so it is a local leftover with no repository effect.
Remove it by hand whenever convenient; no plan needed.

## C. Observations worth keeping (no action)

- The commit gate treats any multi-file diff as high-risk and requires
  `ponytail_reviewed=true` in the findings report, documentation-only diffs
  included. Phase J's first commit was refused for this. Run the `ponytail`
  profile in the same review round whenever more than one file changes.
- A `## Optional Verification` bullet that says "None" still counts as
  optional item 1 and needs an outcome line in the closeout log. Phase H's
  first commit was refused for this.
- OpenWiki 0.5.2 facts confirmed in this plan: `mode: "update"` on an empty
  wiki performs a first generation; `openwiki_begin` starts a run even when
  source is unchanged, so a corrective run needs no `force`; the page queue
  is served in alphabetical path order; evidence may not cite files excluded
  by `.openwikiignore` or generated OpenWiki output including
  `openwiki/INSTRUCTIONS.md`; fixing a wrong claim on a generated page uses
  `openwiki_inspect_page_claims` to get the id, then a revised claim with the
  same id in `openwiki_submit_page`.
- `protect-files.sh` denies a compound Bash command that merely names a
  protected path in read-only context (a heredoc mentioning the Codex config
  file, a `find` chained with `|| true`). Split such commands or use the
  editor tool.
- `git checkout -- <path>` is denied by `git-protection.sh`;
  `git restore -- <path>` is the allowed form.

## Evidence for the closed plan

- Final commit `27c059d`; `verify.py gate` on it with `--head-relation
  certified --require-major --require-ponytail --enforce-final-state`
  returned `{"errors":[]}` on 2026-09-21.
- The guard denied `mode: "init"` against the live server on 2026-09-21 with
  `openwiki-guard: mode="init" replaces the wiki and is denied; only
  mode="update" is allowed through this guard`.
- `bash .claude/hooks/scripts/openwiki-guard.sh post </dev/null` on the
  clean tree printed `restored_from: marker-strip; AGENTS.md=unchanged;
  CLAUDE.md=unchanged` and exited 0.
