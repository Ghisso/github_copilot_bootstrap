---
name: 2026-10-20_phase-E-ponytail-5-adoption
type: small-plan
parent_plan: backlog-followups
phase_index: 5
status: in-progress
closeout_session_log:
---

# Small Plan: Ponytail 5 Adoption

## Scope

Evaluate upstream Ponytail `v5.3.2` against the vendored `v4.8.4` baseline
and this bootstrap's local fork. Merge the upstream changes that close
audit gap A2 (no coder, reviewer, or `ponytail-review` step checks callers,
tests, fixtures, or config outside the diff;
`.claude/explorations/2026-10-17_bootstrap-backlog-audit.md`, §4 A2), plus
the few small upstream safety and reuse rules that need no new mechanism
(table rows P3 to P6 and R3). Everything else stays declined.
Step 1 gathers evidence only and decides the path (BF-E1). NO-GO cancels
this phase with evidence and changes no outer file (BF-E2). ADOPT or PARTIAL
ADOPT merges the upstream change into the two vendored skills by the
three-way procedure in `shared/third_party/ponytail/UPSTREAM.md`, closes the
same gap in the local prompts and profiles (BF-E3, BF-E4), moves every
skill pin (BF-E5), keeps both sidecar profiles
consistent (BF-E6), and vendors neither `ponytail-audit` nor any plugin
runtime (BF-E7).

One generator run gives all four clients the same text: Claude Code
(`.claude/skills/`, `.claude/agents/`), Codex (`[[skills.config]]`,
`.codex/agents/*.toml`), GitHub Copilot (`.github/agents/`, skills), and
Antigravity (`.agents/skills/`). No hook, `verify.py` path, or required check
makes a model call or a network download. Upstream's benchmark numbers are
self-reported and measure the whole plugin, hooks included; this plan does
not use them as evidence. Ponytail is vendored skill text, not a binary,
CLI, MCP server, or SDK, so the `integration-gate-spike` rule does not apply.

**Upstream evidence (2026-10-20,** https://github.com/DietrichGebert/ponytail**).**
`v4.8.4` is commit `bc9ee949d5f439e8b9f3bb92c6d6d3d1e6ebd324`; `v5.3.2` is
`16352ac229eb08a9598dcae48fe9f2b342567d86`; the v5 rewrite is `01cbf81`
(PR #1061, released as `v5.0.0` `b088b2d`). `skills/ponytail/SKILL.md` is
120 lines at `v4.8.4` and 52 at `v5.3.2` (fork: 73); `ponytail-review` is 57
and 101 (fork: 40). `LICENSE` is the same blob `715d483` at both tags, sha256
`fb1bc6909ac3ef82d5c22106e32ef682b0cff66788fa915fb9b53b15c9d2f3ab`. The local
copy (`fc5bd8de…`) has differed since import commit `1b7dc44`: it reads
`Dietrich Gebert` where upstream reads `DietrichGebert`, plus one extra blank
line; Phase A restores it, because the blob is the same at both tags and
the fix must not depend on this phase. The v5 codebase map is plugin-only: a SessionStart hook
(`hooks/ponytail-activate.js`) loads `hooks/ponytail-map.js`, and `v5.1.1`
fixed repository text leaking into its session context. The skill text never
refers to it.

### Provisional adoption table

Step 1 confirms or narrows this table. Adopting a Decline row is a scope
change that needs the user's approval. Line numbers are in the `v5.3.2` files.

| ID | Upstream change (file:line) | Decision | Reason |
|---|---|---|---|
| P1 | `ponytail` L19-21, `## Before you write`: list every place the change must reach (callers, tests, fixtures, config, exports) and what it could break for users | Adopt | A2, coder side. Fold the fork's "Run the ladder after understanding the problem" paragraph (fork L41-43) into it |
| P2 | `ponytail` L34: finish every part the task needs, including the callers, tests, and fixtures the change breaks | Adopt | A2, coder side |
| P3 | `ponytail` L39: code you move or merge keeps its error handling and validation | Adopt into `## Safety boundaries` | New safety item |
| P4 | `ponytail` L28-29, L35: reuse code the way the surrounding code does; a house component beats a native widget; keep the codebase's layers, interfaces, and conventions | Adopt into ladder rung 2 and `## Rules` | Strengthens reuse-first |
| P5 | `ponytail` L36: a one-liner that needs decoding is not short | Adopt | Matches the workspace rule that clarity outranks line count |
| P6 | `ponytail` L41: the check rule also covers a whole new script or app | Adopt | Widens a safety boundary |
| P7 | `ponytail` L15: end the reply with what was skipped or not checked, and any risk | Decline | Changes the coder's reply contract, which `shared/policies/agent-reporting.instructions.md` and the coder prompt own; outside A2 |
| P8 | `ponytail` L25-32: 7 rungs become 6 (standard library and native merged) | Decline | Workspace policy and coder prompt name the 7-rung order |
| P9 | `ponytail` L37: comment only the why | Decline | Outside A2 |
| P10 | `ponytail` L42: `shortcut:` marker replaces `ponytail:` | Decline | Five live markers (for example `scripts/validate_plan_frontmatter.py:623`, `scripts/sidecar_overlay.py:140,1373`, `scripts/validate_targets.py:7814`); a rename is churn |
| P11 | `ponytail` L17, L46-52, `argument-hint` `off`: session persistence, Levels table, new `ultra`, `off` | Decline | The fork dropped Intensity on purpose; `off` and persistence depend on upstream's mode-tracker hooks |
| P12 | `description:` rewrites in both skills | Decline | Upgrade procedure step 2 keeps local wording |
| P13 | `ponytail` L44: never-cut list without root-cause and the meaningful check | Keep local | The fork's list is a superset |
| R1 | `ponytail-review` L21-25: read the diff, then the code it touches (callers of every changed function, the functions it calls, the tests); search every caller when a signature, return value, or behavior changes | Adopt, adapted | A2 for this skill; name tests, fixtures, and config; drop the README item |
| R2 | `ponytail-review` L11-14, L32-45: full quality review (bug, risk, scale, missing test, speed, lean) | Decline | The `code`, `security`, `performance`, and `tests` profiles own these; the fork's `## Boundaries` stays. Decided by the user on 2026-10-20 |
| R3 | `ponytail-review` L48: `reuse:` tag naming the existing path | Adopt | Add it to `shared/review-profiles/ponytail.md` too |
| R4 | `ponytail-review` L52-55: `merge:` and `split:` tags | Decline | The `code` profile covers duplication and single-purpose functions |
| R5 | `ponytail-review` L59-64, `ponytail-audit` L61-62: a concrete case per finding; before `delete:`, search the whole tree (tests, fixtures, config, string or dynamic references); a marked shortcut is a decision | Adopt with the `ponytail:` marker | Stops `delete:` findings that break code outside the diff |
| R6 | `ponytail-review` L69-101: four-part plain-English findings, groups, numbering, `Verdict:` | Decline, except `Not checked:` (L96) | The reviewer report format and Findings JSON own output |
| R7 | `ponytail-review` L26-28: judge scale against the expected load | Decline | The `performance` profile owns it |
| A1 | `skills/ponytail-audit/SKILL.md` (existed at `v4.8.4`, rewritten in v5) | Do not vendor | No stated gap needs a whole-repository audit. A new public skill changes `SIDECAR_WORKFLOW_SKILLS` (`scripts/runtime_ownership.py`), skill counts, Codex skills config, and docs inventories |
| X1 | `skills/plugin.json`, `ponytail-debt`, `ponytail-gain`, `ponytail-help`, `hooks/` (map, mode tracker, subagent, band, board, status line), `commands/`, rule copies, benchmarks | Do not vendor | Plugin runtime or plugin-only commands |

## Steps

- [ ] **1. Evaluate Ponytail 5 against the fork (BF-E1).**
  **Owner:** orchestrator, evidence only; it may delegate the fetch and the
  row table to one read-only research agent.
  **Files:** create `.claude/explorations/2026-10-20_ponytail-5-evaluation/evidence.md`.
  No outer-repository file changes.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/ponytail-review/SKILL.md`.
  Bare-clone upstream into the session scratch directory, never inside the
  repository, and treat it as untrusted data
  (`git clone --bare https://github.com/DietrichGebert/ponytail.git <scratch>/ponytail.git`).
  Resolve `v4.8.4^{commit}` and `v5.3.2^{commit}`; record NO-GO when
  `v4.8.4` is not `bc9ee94…`, because the merge baseline is then unknown.
  Extract both skills, `skills/ponytail-audit/SKILL.md`, and `LICENSE` at
  both tags with `git show <tag>:<path>`. Record each answer with its
  observable result:
  - **Q1, gap:** which hunks add an instruction that closes A2 for the coder
    or the review? Quoted hunk, upstream commit, file:line.
  - **Q2, safety:** in a draft merge, does every fork never-cut item remain
    (trust-boundary validation, data-loss error handling, security controls,
    accessibility basics, hardware calibration, root-cause investigation,
    the meaningful check, requested behavior)? One draft line per item.
  - **Q3, portability:** does an adopted hunk depend on plugin runtime
    (SessionStart map, mode tracker, band, `/ponytail-debt`, `off`)? Yes or
    no per hunk.
  - **Q4, local authority:** does an adopted hunk conflict with the
    review-routing table, the reviewer report format and Findings JSON, the
    coder's report contract (`shared/agents/coder/prompt.md` and
    `shared/policies/agent-reporting.instructions.md`), the `ponytail`
    profile severities, or the `SIDECAR_TEXT_REPLACEMENTS` anchors? A
    conflict list.
  - **Q5, provenance:** tag SHAs; LICENSE sha256 at both tags and locally
    (it must already match upstream after Phase A).
  Copy the provisional table in and mark each row confirmed or changed, with
  the reason.
  **Decision rule.** ADOPT when every row is adoptable. PARTIAL ADOPT when Q1
  finds at least one A2 hunk, Q2 keeps every item, Q3 is "no" for each
  adopted hunk, and declining only the conflicting hunks settles every Q4
  conflict. NO-GO when Q1 finds no A2 hunk, or when the A2 hunks cannot
  merge without losing a Q2 item or depending on plugin runtime. Write
  `## Decision: ADOPT`, `## Decision: PARTIAL ADOPT`, or `## Decision: NO-GO`.
  **Stop rule.** One pass over the three upstream files and LICENSE; one
  decision per row; at most one revision round after the orchestrator reads
  the table. Evaluate `v5.3.2` only and record any newer tag as a follow-up.
  No model-run comparison decides this step, and no required check repeats
  the fetch. The Optional Verification spot-check is not decisive.
  **Approval.** The approved big plan authorizes PARTIAL ADOPT within the
  table and NO-GO cancellation. Adopting a Decline row, vendoring
  `ponytail-audit`, or a newer baseline is a scope change: stop and ask the
  user.

- [ ] **2. NO-GO path only: cancel this phase (BF-E2).**
  **Owner:** orchestrator.
  **Files:** the Step 1 evidence file, this small plan, the big plan
  `backlog-followups.md`, and the Phase F small plan.
  **Required Skills:** none beyond the workflow policy.
  Add `**Status:** CANCELLED` near the top of the evidence file, with the
  reason and one follow-up for Phase G's "Recorded follow-ups" list in
  `docs/target-mapping.md`: A2 stays open. Set this plan to `status: cancelled` with `cancelled_at` (exact
  UTC), a single-line `cancelled_reason`, and
  `cancelled_evidence: .claude/explorations/2026-10-20_ponytail-5-evaluation/evidence.md`.
  A cancelled current phase never certifies a commit, and
  `shared/hooks/scripts/_lib-frontmatter.sh:1425` says to advance
  `current_phase` past it: set the big plan's `current_phase` to
  `2026-10-20_phase-F-openwiki-0.7-upgrade` and that phase to
  `status: in-progress`. Tick this phase's entry in the big plan's
  `## Phases` list and annotate it "cancelled (NO-GO), see <evidence
  path>". Run `uv run python scripts/validate_plan_frontmatter.py`
  on the big plan and its phases, then checkpoint the nested `.claude`
  repository. No outer commit, findings report, or closeout log. Skip
  Steps 3 to 8.

- [ ] **3. Merge the coding skill (BF-E3).**
  **Owner:** coder.
  **Files:** modify `shared/skills/ponytail/SKILL.md`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`.
  Re-read the file on the branch first. Apply
  the confirmed P rows on top of the fork; never copy the upstream file over
  it. Add `## Before you write` (P1) before `## The ladder`, containing the
  phrase "callers, tests, fixtures, config". Keep unchanged: the frontmatter
  (`name`, `visibility: public`, the fork's `description:`, `argument-hint`,
  `license: MIT`); the `## Persistence` paragraph byte for byte, line breaks
  included, because `SIDECAR_TEXT_REPLACEMENTS`
  (`scripts/generate_targets.py:183-199`) matches its last two lines
  literally; the 7-rung ladder; `## Safety boundaries` and every item on it;
  and the `ponytail:` marker.

- [ ] **4. Merge the review skill (BF-E4).**
  **Owner:** coder.
  **Files:** modify `shared/skills/ponytail-review/SKILL.md`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`.
  Add `## Read first` for R1, containing the phrase "not only the diff" and
  naming callers of every changed function, the functions it calls, its
  tests and fixtures, and config that names it; search every caller when a
  signature, return value, or behavior changes. Add `reuse:` (R3), the R5
  checks before a finding, and a one-line `Not checked:` ending (R6). Keep
  the complexity-only scope and `## Boundaries` (R2), the five existing tags,
  the `net:` and `Lean already. Ship.` endings, and the frontmatter as in
  Step 3. Keep the words `Return findings to the coder` on one line;
  `SIDECAR_TEXT_REPLACEMENTS` matches them literally.

- [ ] **5. Close the gap in local prompts and profiles (BF-E3, BF-E4).**
  **Owner:** coder.
  **Files:** modify `shared/agents/reviewer/prompt.md` (`## Review Flow`,
  step 2), `shared/agents/reviewer/workflow-prompt.md` (`## Review flow`,
  step 2), `shared/agents/coder/prompt.md` (`## Mandatory Skills-First Rule`,
  the Ponytail ladder paragraph), `shared/agents/coder/workflow-prompt.md`
  (`## Skills to load first`), `shared/review-profiles/code.md`
  (`## Checklist`), `shared/review-profiles/ponytail.md` (`## Checklist`,
  `## Finding Format`), and `shared/policies/workspace.instructions.md`
  (`## Ponytail Coding Rule`).
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`.
  Both reviewer prompts get one sentence: read the code the change touches,
  not only the diff (callers of every changed function, signature, or return
  value; the tests and fixtures that exercise it; the config or exports that
  name it); a caller, test, fixture, or config entry outside the diff that
  the change breaks or leaves stale is an ordinary finding. The reviewer
  already has read and search tools. The sidecar sentence keeps that
  prompt's advisory wording. Both coder prompts and the workspace rule
  replace "trace the real flow and callers" (or its current wording) with
  mapping every place the change must reach, using the phrase "callers,
  tests, fixtures, config". `code.md` gets one checklist line about callers,
  tests, fixtures, and config outside the diff; `ponytail.md` gets `reuse:`
  (name the existing path). Routing, severities, and gates do not change.

- [ ] **6. Move every skill provenance pin (BF-E5, BF-E7).**
  **Owner:** coder.
  **Files:** modify `shared/third_party/ponytail/UPSTREAM.md`,
  `scripts/validate_targets.py` (`:7937-7983` release, commit, and the two
  skill sha256 pins; the `LICENSE` pin already moved in Phase A; `:9681-9686`
  installed provenance release), and `tests/test_validate_targets.py`
  (`:3264-3274` line-count literals; `:2975-3010` re-wrap sanity text).
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Confirm `LICENSE` still has sha256 `fb1bc690…` (Phase A). In
  `UPSTREAM.md`: set release `v5.3.2`, commit `16352ac` plus the full SHA,
  and the import date; rewrite the fork-divergence paragraph with real line
  counts against `v5.3.2` and drop "reduced" (the fork can now be longer);
  keep the three phrases the validator matches ("canonical workflow and
  review-routing policies decide lifecycle placement", "conditional
  `ponytail` review profile runs", "`ponytail-review` remains an imported
  skill"); replace `## Upstream survey (v4.9.0)` with a short
  `## Merge record (v5.3.2)` listing each row ID, its decision, and the
  evidence file; add `ponytail-audit`, `ponytail-debt`, `ponytail-gain`,
  `ponytail-help`, `skills/plugin.json`, and the SessionStart codebase map to
  the not-vendored list; base the upgrade procedure on `v5.3.2` and add the
  full pin checklist from Steps 6 and 7, so the next upgrade does not depend
  on `.claude/MEMORY.md`. Compute hashes from the final bytes, after Steps 3
  to 5. Update the re-wrap test's `old_wrap` only when that paragraph's wrap
  changes.
  **Tests:** the pin checks in `validate_skills_and_paths` and
  `test_ponytail_upstream_describes_the_real_fork_divergence` pass with the
  new values. Negative control, run once and reverted: a one-byte change to
  the merged skill makes `validate_targets.py` report "allowlist hash
  changed".

- [ ] **7. Keep both sidecar profiles consistent; add text-ships rows (BF-E3, BF-E4, BF-E6).**
  **Owner:** coder.
  **Files:** modify `tests/test_validate_targets.py`; modify
  `scripts/generate_targets.py` only to move a `SIDECAR_TEXT_REPLACEMENTS`
  anchor.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/testing-patterns/SKILL.md`.
  Add one test: every `old` phrase in `SIDECAR_TEXT_REPLACEMENTS` occurs in
  at least one `shared/skills/<name>/SKILL.md` for a name in
  `SIDECAR_SKILLS`. Today a re-wrapped anchor fails nothing: the validator
  rejects only a leftover old phrase (`scripts/validate_targets.py:8911-8913`),
  and a snapshot recapture would accept the unreplaced text. Make it pass,
  then recapture `SIDECAR_SKILLS_PROFILE_SNAPSHOT_SHA256` (`:3314-3316`) from
  `render_sidecar(tmp, "skills")` and update the comment naming the last
  change. Add rows in the `_guidance_errors` pattern (`:3547-3880`):
  - `FULL_REVIEW_GUIDANCE`, with new `_source_texts()` assets
    `ponytail-skill` (`## Before you write`: "callers, tests, fixtures,
    config") and `ponytail-review-skill` (`## Read first`: "not only the
    diff"); `reviewer` `## Review Flow` ("not only the diff"); `coder`
    `## Mandatory Skills-First Rule` ("callers, tests, fixtures, config");
    `code-profile` `## Checklist` ("outside the diff");
  - `SIDECAR_REVIEW_GUIDANCE`: sidecar `reviewer` `## Review flow` ("not
    only the diff") and `coder` `## Skills to load first` ("callers, tests,
    fixtures, config").
  Add the two skill assets to the full-install generated-text test's
  dictionary, so the `.claude/skills/` copies are checked too.
  **Tests:** negative controls, each run once and reverted: the anchor test
  fails on a fork copy whose `## Persistence` paragraph is re-wrapped; each
  new row fails when its phrase is removed or moved (the pattern of
  `test_review_guidance_check_fails_when_text_is_removed_or_moved`).

- [ ] **8. Regenerate, self-install, document, review, close out (BF-E7).**
  **Owner:** orchestrator; documenter after review; fresh reviewer.
  **Files:** regenerate `dist/`; self-install `.claude/`; modify
  `docs/architecture.md` (`## Ponytail Integration`: `v4.8.4` at line 221
  and the `ponytail-review` description) and `docs/smoke-tests.md:75`. Read
  `README.md` lines 35, 483, 510-517, and 1098; change only a claim the merge
  made false.
  **Required Skills:** `shared/skills/documentation/SKILL.md`,
  `shared/skills/code-review/SKILL.md`.
  Run `uv run python scripts/generate_targets.py --all` and
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  before verification; never copy `dist/` by hand. Dated records stay
  unchanged: `docs/evidence/behavioral-pilot/phase-a/manifest.json` keeps its
  old `ponytail-review` hash, and the 2026-10-17 audit keeps its text. Phase
  G refreshes the OpenWiki pages that describe the Ponytail skills (for
  example `openwiki/architecture/agents-and-skills.md:191`). At LEARN,
  correct the Ponytail `[LEARN:architecture]` and `[LEARN:verification]`
  pin entries in `.claude/MEMORY.md` in place: their line counts change, and
  the pin list now lives in `UPSTREAM.md`.

## Verification

```bash
grep -Eq '^## Decision: (ADOPT|PARTIAL ADOPT)$' .claude/explorations/2026-10-20_ponytail-5-evaluation/evidence.md
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/test_validate_targets.py tests/test_install_bootstrap.py tests/test_sidecar_install.py tests/test_sidecar_update.py tests/test_sidecar_uninstall.py tests/test_sidecar_overlay.py -q
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Behavioral spot-check, one run per arm, not decisive. In a scratch
  directory outside the repository, create `lib.py` with
  `def parse(text: str) -> list[str]`, `app.py` that calls `parse(raw)`, and
  `tests/test_app.py` with a fixture value. Ask a fresh Claude Code coder
  session to give `parse` a required `sep: str` argument: once with the
  skills installed from `dev`, once with the merged skills. Record for each
  arm whether `app.py` and the test fixture changed in the same edit. Then
  give a fresh reviewer the signature-only diff and record whether it
  reports the `app.py` caller. Make no commits there; compare working-tree
  diffs.

## Review Profiles

Use `.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Give the reviewer audit §4 A2,
BF-E1 to BF-E7, the Step 1 evidence file with its table, and the final diff.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
