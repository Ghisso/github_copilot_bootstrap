# Ponytail 5 evaluation evidence (BF-E1)

- **Date:** 2026-10-21
- **Plan:** `.claude/plans/2026-10-20_phase-E-ponytail-5-adoption.md`, Step 1
- **Gap:** audit A2 (`.claude/explorations/2026-10-17_bootstrap-backlog-audit.md`,
  §4 row A2): no coder, reviewer, or `ponytail-review` step checks callers,
  tests, fixtures, or config outside the diff.
- **Method:** one read-only pass over the existing bare clone of
  `https://github.com/DietrichGebert/ponytail.git` (made 2026-10-20 in the
  session scratch directory, treated as untrusted data). Every upstream quote
  below comes from `git show <tag>:<path>`; every commit attribution comes
  from `git blame v5.3.2 -- <path>`. No fetch, no model run, no repository
  file changed.
- **Inputs read:** both tags of `skills/ponytail/SKILL.md`,
  `skills/ponytail-review/SKILL.md`, `skills/ponytail-audit/SKILL.md`, and
  `LICENSE`; the local fork (`shared/skills/ponytail/SKILL.md`,
  `shared/skills/ponytail-review/SKILL.md`); the Q4 authorities listed under Q4.

## Q5. Provenance (checked first: it gates the merge baseline)

| Item | Value | Result |
|---|---|---|
| `v4.8.4^{commit}` | `bc9ee949d5f439e8b9f3bb92c6d6d3d1e6ebd324` (2026-06-29) | Matches the plan's `bc9ee94…`. Baseline known; no NO-GO on provenance. |
| `v5.3.2^{commit}` | `16352ac229eb08a9598dcae48fe9f2b342567d86` (2026-10-17) | Matches the plan. |
| `v5.0.0^{commit}` | `b088b2df6e08d4306c6a3c3d575fe38c2d2d2989` | Matches the plan's `b088b2d`. |
| v5 rewrite | `01cbf815429e89dcf37b7d2d2a8b593e886fcae1` (#1061, 2026-10-08, first tag `v5.0.0`) | Source of every adopted hunk. |
| Clone origin | `https://github.com/DietrichGebert/ponytail.git` | As planned. |
| `LICENSE` at `v4.8.4` | blob `715d483338cea4365f0d91a27799cf61226d6bcf`, sha256 `fb1bc6909ac3ef82d5c22106e32ef682b0cff66788fa915fb9b53b15c9d2f3ab` | |
| `LICENSE` at `v5.3.2` | same blob, same sha256 | Unchanged between tags. |
| Local `shared/third_party/ponytail/LICENSE` | sha256 `fb1bc690…f2ab`, `git hash-object` `715d483…` | Byte-identical to upstream. Restored by Phase A commit `f52a867`. The `.claude/` and all `dist/` copies have the same sha256. |
| Fork pins today | `shared/skills/ponytail/SKILL.md` sha256 `7edff0be…03a1`; `shared/skills/ponytail-review/SKILL.md` sha256 `0732435f…12b8` | Match `shared/third_party/ponytail/UPSTREAM.md:37-38`. Step 6 recomputes them after the merge. |

Line counts (plan figures confirmed):

| File | `v4.8.4` | `v5.3.2` | Fork |
|---|---|---|---|
| `skills/ponytail/SKILL.md` | 120 | 52 | 73 |
| `skills/ponytail-review/SKILL.md` | 57 | 101 | 40 |
| `skills/ponytail-audit/SKILL.md` | 41 | 103 | not vendored |

Newer tag: the clone lists no tag after `v5.3.2`. The clone was not
refetched, so this says nothing about releases after 2026-10-20 (see
Follow-ups).

## Q1. Hunks that close A2

All A2 hunks below are new in the `v4.8.4` -> `v5.3.2` delta and come from
upstream commit `01cbf81` (#1061). The bug-fix caller rule
(`v5.3.2` `skills/ponytail/SKILL.md:38`, "grep every caller of the function
you touch") is not new: it existed at `v4.8.4` (`:50-54`) and is already in
the fork (`shared/skills/ponytail/SKILL.md:42-43`).

**Coder side (`skills/ponytail/SKILL.md` at `v5.3.2`):**

- `:19-21` (row P1):
  > ## Before you write
  >
  > Read the task and the code it touches. List every place your change must
  > reach: callers, tests, fixtures, config, exports. Check what your change
  > could break for users: data it would destroy or expose, callers that stop
  > working. That is scope. Extra features are not.
- `:34` (row P2):
  > - Be lazy about the solution, never about the change itself: finish every
  > part the task needs, including the callers, tests and fixtures your change
  > breaks.
- `:36`, first sentence (carried by row P5, which cites the whole line):
  > - The shortest working diff wins, once you know everything it must touch.

**Review side (`skills/ponytail-review/SKILL.md` at `v5.3.2`):**

- `:21-25` (row R1):
  > - Read the diff, then the code it touches: callers of every changed
  > function, the functions it calls, the tests, the README.
  > - Trace the real flow: where data comes in, what is stored, what goes out.
  > - A change can break code it does not touch. When a signature, return
  > value or behavior changes, grep every caller.
- `:61-62` (row R5):
  > - Re-read the lines and confirm: the caller exists, the value can really
  > be empty, the code really is unused.

**Review side, text from a file that is not vendored
(`skills/ponytail-audit/SKILL.md` at `v5.3.2`):**

- `:61-62` (row R5):
  > - Before calling code unused, grep the whole tree for it, including tests,
  > fixtures, config, and string or dynamic references.

The reviewer agent and the `code` profile get no upstream hunk; Step 5 closes
A2 there with local text. Result: Q1 finds A2 hunks on both the coder and the
review side.

## Q2. Fork never-cut items in a draft merge

Each line is the draft merged text for that item, in the merged
`shared/skills/ponytail/SKILL.md`. Unchanged lines keep their current fork
line number.

| # | Fork never-cut item | Draft merged line | Survives |
|---|---|---|---|
| 1 | Trust-boundary validation | `- input validation at trust boundaries;` (unchanged, fork `:60`) | Yes |
| 2 | Data-loss error handling | `- error handling that prevents data loss;` (unchanged, `:61`), plus new P3 item `- the error handling and validation of code you move or merge;` | Yes, widened |
| 3 | Security controls | `- security controls;` (unchanged, `:62`) | Yes |
| 4 | Accessibility basics | `- accessibility basics;` (unchanged, `:63`) | Yes |
| 5 | Hardware calibration | `- hardware calibration or real-world tolerance;` (unchanged, `:64`) | Yes |
| 6 | Root-cause investigation | `- root-cause investigation;` (unchanged, `:65`), plus the P1 fold keeps "When fixing a bug, search every caller and fix the shared root cause once rather than patching one symptom." | Yes |
| 7 | The meaningful check | `- a meaningful check for non-trivial logic.` (unchanged, `:66`), and P6 widens `:68`: "Non-trivial logic, including a whole new script or app, leaves the smallest runnable regression check that would fail if it broke." | Yes, widened |
| 8 | Requested behavior | `- Do not minimize away anything explicitly requested.` (unchanged, `## Rules`, `:54`) | Yes |

Upstream's own never-cut line (`v5.3.2` `:44`) drops items 6 and 7 from the
list; row P13 keeps the fork's list, so nothing is lost. Draft P1 block, which
folds fork `:41-43` (shown because items 6 and the Q4 wording rule depend on it):

```markdown
## Before you write

Read the task and the code it touches, and trace the real flow, before you
choose a rung. Find every place the change must reach: callers, tests,
fixtures, config, exports. Check what it could break for users: data it would
destroy or expose, callers that stop working. That is scope; extra features
are not. When fixing a bug, search every caller and fix the shared root cause
once rather than patching one symptom.
```

It contains the Step 7 anchor phrase "callers, tests, fixtures, config".
Result: Q2 keeps every item.

## Q3. Plugin-runtime dependency per adopted hunk

| Row | Upstream hunk | Needs SessionStart map, mode tracker, band, `/ponytail-debt`, or `off`? |
|---|---|---|
| P1 | `ponytail` `:19-21` | No |
| P2 | `ponytail` `:34` | No |
| P3 | `ponytail` `:39` | No |
| P4 | `ponytail` `:28-29`, `:35` (last sentence) | No |
| P5 | `ponytail` `:36` | No |
| P6 | `ponytail` `:41` | No |
| R1 | `ponytail-review` `:21-25` | No. "grep every caller" needs only a search tool; the reviewer has read and search. Draft says "search". |
| R3 | `ponytail-review` `:48` | No |
| R5 | `ponytail-review` `:59-64`; `ponytail-audit` `:61-62` | No. `:63`'s `shortcut:` marker came from `2a1fe84` (#1068, `v5.1.0`) and is replaced by `ponytail:` (P10). |
| R6 | `ponytail-review` `:96` (`Not checked:`) | No |

Evidence: in the three `v5.3.2` skill files, the only plugin-runtime text is
`ponytail` `:9` (`off` in `argument-hint`, added by `df9e899`, "the band and
the board in Claude Code", #1138, `v5.3.0`) and `:17` (session persistence and
the `/ponytail` level switch). Both belong to row P11 (Decline). No skill text
names the SessionStart map (`hooks/ponytail-activate.js` loading
`hooks/ponytail-map.js`); `ponytail-audit`'s "## 1. Map first" is a heading,
not the plugin map. Result: Q3 is "no" for every adopted hunk.

## Q4. Conflicts with local authority

**Conflict list: none.** No adopted hunk has to be declined. Five wording
conditions keep it that way; Steps 3 to 5 must follow them.

| Authority | Adopted rows checked | Finding |
|---|---|---|
| Review-routing table (`shared/policies/workspace.instructions.md:121-147`) | All | No adopted hunk names a profile, a surface, or a routing rule. The overlap with `code`, `security`, `performance`, and `tests` sits in R2 and R7, which stay declined. |
| Reviewer report format and Findings JSON (`shared/agents/reviewer/prompt.md:58-110`) | R1, R3, R5, R6 | No conflict. The reviewer agent loads review profiles, not the `ponytail-review` skill (no reference in `shared/agents/reviewer/`), so the skill's `net:`, `Not checked:`, and tag lines never enter the reviewer report. Findings on files outside the diff are allowed: `shared/scripts/record_findings.py:239-252` checks only that each finding's `profile` was reviewed, not its `file`. **Condition 1:** `Not checked:` (R6) goes into the skill only, never into the `ponytail` profile; in a full install, unchecked items stay `### Open Requests` or unverified limitations (`prompt.md:50`). |
| Coder report contract (`shared/agents/coder/prompt.md`, `shared/policies/agent-reporting.instructions.md`) | P1, P2 | No conflict. Neither file fixes a coder reply template; P7, the hunk that would add a mandatory reply ending, stays declined. **Condition 2:** P1 says "Find every place …", not upstream's "List every place …", so it reads as a working step before the first edit, not a new reply section. |
| `ponytail` profile severities (`shared/review-profiles/ponytail.md:24-44`) | R1, R3, R5 | No conflict. `reuse:` fits the existing severities: Major for a duplicate implementation that adds ownership or divergent behavior, Minor otherwise; it tags the existing checklist item at `:12`. **Condition 3:** add `reuse:` to the skill and to the profile's `## Finding Format` in the same change (no validator enumerates the tags: the five tags appear only in those two files). **Condition 4:** R1 and R5 serve complexity findings; a broken caller found while reading is a correctness defect for the normal review profiles, as the fork's `## Boundaries` (`shared/skills/ponytail-review/SKILL.md:34-39`) already says, never a `profile: "ponytail"` finding. R5 drops upstream's "unless the expected load already crosses it" (it needs the declined R7 load step). |
| `SIDECAR_TEXT_REPLACEMENTS` (`scripts/generate_targets.py:183-199`) | All | No conflict. The second entry (the first is the `humanize` credit) anchors fork `ponytail` `:25-26` inside `## Persistence`; no adopted P hunk touches that section (P11, which would replace it, is declined). The third entry anchors `ponytail-review` `:31`, "Return findings to the coder", on one line; R1, R3, R5, and R6 add lines elsewhere. Replacement is a plain `str.replace` (`:1949-1950`) and the validator rejects only a leftover old phrase (`scripts/validate_targets.py:8911-8913`). **Condition 5:** keep both anchors byte for byte, and keep new text free of the sidecar forbidden tokens (`scripts/validate_targets.py:8824-8840`, for example `.claude/review-profiles/`, `third_party/`, `verify.py`). The adopted upstream text contains none of them. |

## Provisional adoption table, checked

Line numbers are in the `v5.3.2` files. No row's decision changed. Two
reasons were corrected (P10, R2).

| ID | Upstream change (file:line) | Decision | Step 1 | Reason |
|---|---|---|---|---|
| P1 | `ponytail` L19-21, `## Before you write` | Adopt | Confirmed | A2, coder side (Q1). Fold fork L41-43 into it; root-cause sentence kept (Q2 item 6). Word as "Find", not "List" (Q4 condition 2). |
| P2 | `ponytail` L34 | Adopt | Confirmed | A2, coder side (Q1). |
| P3 | `ponytail` L39 | Adopt into `## Safety boundaries` | Confirmed | New safety item (Q2 item 2). |
| P4 | `ponytail` L28-29, L35 | Adopt into rung 2 and `## Rules` | Confirmed | Strengthens reuse-first. Only L35's last sentence (layers, interfaces, conventions); its other clauses (wrapper, type conversion, keep values in platform form) are in no row and stay out. |
| P5 | `ponytail` L36 | Adopt | Confirmed | Clarity outranks line count. The same line's first sentence ("once you know everything it must touch") is also an A2 clause (Q1). |
| P6 | `ponytail` L41 | Adopt | Confirmed | Widens the check rule (Q2 item 7). |
| P7 | `ponytail` L15 | Decline | Confirmed | Changes the coder's reply contract; outside A2. Also the reason for Q4 condition 2. |
| P8 | `ponytail` L25-32, 6 rungs | Decline | Confirmed | `workspace.instructions.md:101-103` and coder `prompt.md:27-30` name stdlib and native separately. |
| P9 | `ponytail` L37 | Decline | Confirmed | Outside A2. |
| P10 | `ponytail` L42, `shortcut:` | Decline | Confirmed, reason corrected | Six live `ponytail:` markers in authored source, not five: `scripts/validate_plan_frontmatter.py:553,623`, `shared/scripts/verify.py:543`, `scripts/sidecar_overlay.py:140,1373`, `scripts/validate_targets.py:7814`. A rename is churn. |
| P11 | `ponytail` L17, L46-52, `off` | Decline | Confirmed | `off` came from the band commit `df9e899` (#1138); persistence and `off` need plugin hooks (Q3). |
| P12 | `description:` rewrites | Decline | Confirmed | `UPSTREAM.md` upgrade step 2 keeps local wording. |
| P13 | `ponytail` L44, short never-cut list | Keep local | Confirmed | Upstream drops root-cause and the meaningful check from the list (Q2). |
| R1 | `ponytail-review` L21-25 | Adopt, adapted | Confirmed | A2 for this skill (Q1). Name tests, fixtures, and config; drop README; "search", not "grep"; a broken caller goes to the normal review (Q4 condition 4). |
| R2 | `ponytail-review` L11-14, L32-45, full quality review | Decline | Confirmed, reason corrected | No longer an open question: the user decided on 2026-10-20 that `ponytail-review` stays complexity-only (`.claude/plans/backlog-followups.md`, "Decisions recorded", item 3). |
| R3 | `ponytail-review` L48, `reuse:` | Adopt | Confirmed | Add to the skill and `shared/review-profiles/ponytail.md` together (Q4 condition 3). |
| R4 | `ponytail-review` L52-55, `merge:` and `split:` | Decline | Confirmed | `shared/review-profiles/code.md:7,9` covers single-purpose functions and duplication. |
| R5 | `ponytail-review` L59-64, `ponytail-audit` L61-62 | Adopt with the `ponytail:` marker | Confirmed | A2 (Q1). For a complexity finding, the concrete case is the evidence (no caller sets the option; the standard-library function that does the same), because upstream's "wrong result" wording assumes bug findings. Drop the "expected load" clause (Q4 condition 4). Record the `ponytail-audit` source in the Step 6 merge record. |
| R6 | `ponytail-review` L69-101 | Decline, except `Not checked:` (L96) | Confirmed | Reviewer report format and Findings JSON own output; `Not checked:` stays in the skill only (Q4 condition 1). |
| R7 | `ponytail-review` L26-28, load | Decline | Confirmed | `shared/review-profiles/performance.md` owns it. |
| A1 | `skills/ponytail-audit/SKILL.md` | Do not vendor | Confirmed | No stated gap needs a whole-repository audit. It existed at `v4.8.4` (see the audit note below). |
| X1 | `skills/plugin.json`, `ponytail-debt`, `ponytail-gain`, `ponytail-help`, `hooks/`, `commands/`, rule copies, benchmarks | Do not vendor | Confirmed | Present in the `v5.3.2` tree (`hooks/ponytail-activate.js`, `ponytail-map.js`, `ponytail-mode-tracker.js`, `ponytail-subagent.js`, `hooks/band`, status-line scripts, `commands/*.toml`); all plugin runtime or plugin-only commands. |

## Correction to the 2026-10-17 audit

The audit's §3 (`.claude/explorations/2026-10-17_bootstrap-backlog-audit.md:59-61`)
lists `/ponytail-audit` among the `v5.0.0` changes. That is inaccurate:
`skills/ponytail-audit/SKILL.md` was added by `92efc4a` (2026-06-14, #20),
first tagged in `v4.3.0`, and exists at `v4.8.4` (41 lines). `v5.0.0`
(`01cbf81`) rewrote it (103 lines at `v5.3.2`). The audit stays unchanged as
a dated record (plan Step 8); this note is the correction.

## Follow-ups

- Newer tag: none in the existing clone. Check for releases after `v5.3.2`
  at the next upgrade; do not refetch in this phase (stop rule).
- The plan's Scope still describes the LICENSE fix as pending and R2 as an
  open user decision; both are settled. Its BF-E5 sentence reads "restores a
  moves every skill pin", which looks garbled.
- Step 6's merge record should name `skills/ponytail-audit/SKILL.md:61-62`
  (`v5.3.2`, MIT, same `LICENSE`) as the source of one R5 sentence, even
  though that file is not vendored.

## How the decision rule applies

- Q1: A2 hunks found (P1, P2, P5 first clause, R1, R5).
- Q2: all eight fork never-cut items survive.
- Q3: "no" for every adopted hunk.
- Q4: no conflict that needs a decline; five wording conditions.
- Not every row is adoptable (P7 to P12, R2, R4, R6 except one line, R7, A1,
  and X1 stay declined), so the result is the partial path, within the table.
  No Decline row is adopted, `ponytail-audit` is not vendored, and the baseline
  stays `v5.3.2`, so no scope change needs the user.

## Decision: PARTIAL ADOPT
