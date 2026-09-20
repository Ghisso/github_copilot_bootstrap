---
description: "Always-on: Workflow protocol, branch lifecycle, session logging, context management. Load when planning, implementing, or starting a session."
applicability: always
---

# Workflow: Pre-Flight -> Branch -> Plan When Needed -> Implement -> Verify -> Review -> Closeout -> Commit -> Push

---

## Task Lanes

Classify a request before planning or delegating. This is the single normative
task-size decision table; other guidance must refer here instead of redefining
the lanes. Do not use time or line-count thresholds to classify a lane.

| Lane | Enter only when | Owner and required work | Lifecycle artifacts |
|---|---|---|---|
| Read-only/reporting | No change is requested. | Main agent; inspect and provide evidence only. A requested diagnosis stays here until a fix is requested. | None. |
| Lightweight edit | The request is explicit, changes one non-control-plane file, is low risk, has no dependency/lockfile, migration, user-data, security, or control-plane impact, and requests no commit or PR. | Main agent; make the focused edit and run proportionate focused verification. | No lifecycle artifacts. |
| Standard implementation | Any requested change that is not lightweight or control-plane/high-risk, including all work with a requested commit or PR. | Main-thread orchestrator; use a micro-plan or full-plan, then the canonical specialist loop. | Full lifecycle below. |
| Control-plane/high-risk | Any control-plane, security, dependency/lockfile, migration, multi-file, user-data, generator, or script change. | Main-thread orchestrator; use a full plan and the canonical specialist loop with `code`, `architecture`, `security`, `tests`, and `ponytail` review. | Full lifecycle below. |

An already-explicit request or approved plan is sufficient authority to enter
the control-plane/high-risk lane; ask the user only when targets, authority, or
material scope are unclear. Narrow `fixup!`, `squash!`, `chore(typo):`, and
`docs(typo):` commit bypasses are audited recovery exceptions, never task-lane
classification or permission to skip safeguards.

## Plan-First Protocol

Standard implementation uses a micro-plan when its scope is obvious and one
phase; use a full plan for ambiguous, multi-phase, or new-module work.
Control-plane/high-risk work always uses a full plan.

An approved existing implementation-ready plan normally skips new plan
creation. Before each new phase, inspect completed-phase outcomes and relevant
deterministic verification/reviewer findings. Invoke one planner only when new evidence,
constraints, regressions, or architecture decisions materially affect remaining
work; revise affected future phases only, without reopening completed or
unaffected scope.

1. Check `.claude/MEMORY.md` for relevant `[LEARN]` entries.
2. For ambiguous/complex tasks: clarify with user (max 3-5 questions), optionally create a spec in `.claude/quality_reports/specs/`.
3. Draft plan -> save to `.claude/plans/` for concrete implementation plans or `.claude/explorations/` for exploratory/PoC plans.
4. Present to user -> wait for approval unless the user explicitly supplied an approved implementation plan.
5. After approval: create session log, then implement via the orchestrator loop.

---

## Branch Lifecycle

- `dev` is the working base branch for implementation work.
- Before starting new work, the current branch must be `dev` and the working tree must be clean.
- Each big plan creates exactly one implementation branch named `<plan_name>_implementation` from `dev`.
- Big plans live at `.claude/plans/<plan_name>.md` and must use `type: big-plan` frontmatter.
- Small plans live at `.claude/plans/<phase_slug>.md` and must use `type: small-plan` frontmatter.
- Commit once per completed small plan after DOCUMENT, LEARN, session log, and verification gates pass.
- Open a PR to `dev` only after every small plan in the big plan is complete or cancelled and only when the user explicitly asks for a PR.
- The user performs merge/squash decisions manually in GitHub. After merge, return to `dev` and pull before starting new work.

### Declaring future phases

`planned` is a small-plan-only status for a phase that has not started. New
small-plan files default to `planned` and need only the ordinary identity
fields; they carry no pause, cancellation, or closeout evidence. Branch
creation activates the first phase, and a completed-phase commit activates the
next non-cancelled phase, by flipping exactly that one phase from `planned` to
`in-progress`; every other declared phase is left untouched. An unexpected
next-phase status (`paused`, `complete`, invalid, duplicate, missing, or
unreadable) is never overwritten; the transition warns and leaves the phase
machine at its current phase instead. `planned` is unfinished and blocks the
same push/PR and completion gates as `in-progress`. Plans already installed
with a future phase marked `in-progress` remain valid.

### Pausing a phase for a checkpoint

`paused` is a small-plan-only, non-terminal status. Enter it only after an
explicit user request to stop, pause, or checkpoint and resume later; a failed
check alone does not authorize it. If the user names a safe boundary, reach it
before pausing when it is safe to do so.

A paused phase requires `paused_at` in exact UTC `YYYY-MM-DDTHH:MM:SSZ`
format, meaningful single-line `paused_reason`, and repository-relative
`pause_session_log` evidence that resolves to a readable UTF-8 log containing
`**Status:** PAUSED`. The log records the reason, completed and remaining work,
verification already run, incomplete checks, and the exact resume point.

After the evidence is recorded, a checkpoint commit may preserve tracked outer
repository work without final findings, LEARN, DOCUMENT, or COMPLETED
closeout. It is not a bypass, does not advance `current_phase`, and leaves the
big plan `in-progress`. Do not create an empty outer-repository checkpoint
commit when only AI-state files changed; persist the PAUSED plan and session log
through the normal AI-state checkpoint path instead. A paused phase remains
unfinished. After its checkpoint commit, it may be pushed as a durable remote
checkpoint only when paused-publication invariants pass. It still blocks PR
creation and final closeout.

On resume, read the paused small plan and PAUSED log, inspect `git log --oneline
-10`, `git status`, and the current diff, report the recorded resume point, set
the same phase back to `in-progress`, preserve the latest pause metadata, and
continue without creating another small plan. Complete the ordinary lifecycle
once the phase actually finishes.

### Cancelling a plan or phase

`cancelled` means an authorized decision was made that a plan or phase will
never run. It is distinct from `complete` and requires `cancelled_at` as a real
UTC calendar date and time in exact `YYYY-MM-DDTHH:MM:SSZ` format; a meaningful
`cancelled_reason` written as plain single-line scalar prose without leading
quotes, YAML block headers, collections, list markers, or comment-only values;
and a repository-relative `cancelled_evidence` path that stays inside the
repository and resolves to an existing regular, readable UTF-8 text artifact
containing the same-line prefix `**Status:** CANCELLED`.

A cancelled phase requires no commit, findings report, or closeout
session log. A cancelled big plan is terminal and cannot start an implementation
branch. A branch containing cancelled phases reaches final push/PR closeout only
when at least one phase is complete, every cancelled phase has the full evidence
contract, and commit-count checks count completed phases only. The push gate
binds findings to the last completed phase. Commit closeout skips cancelled
phases when advancing `current_phase`, while a commit whose current phase is
cancelled remains blocked.

---

## Canonical Orchestrator Loop

```text
PRE-FLIGHT -> BRANCH -> PLAN when needed -> IMPLEMENT -> VERIFY -> REVIEW -> CLOSEOUT -> COMMIT -> PUSH
```

For each small plan:

1. **PLAN:** If no implementation-ready plan exists, delegate to `planner` and save the concrete small plan under `.claude/plans/`. Otherwise use the approved existing plan directly. Before each new phase, perform the material-impact check above; use one planner only for affected future work.
2. **IMPLEMENT:** Delegate to `coder` (including Gradio/Streamlit UI work). The coder applies `.claude/skills/ponytail/SKILL.md` once in `full` mode, simplifies the changed scope, and re-verifies it; Ponytail is not a standalone lifecycle phase.
3. **VERIFY:** Run focused and fast checks during implementation. Route a deterministic failure to the coder with its changed scope; do not spend another model merely to repeat deterministic checks.
4. **REVIEW:** Delegate to `reviewer` with profiles selected from the authoritative routing table, including its Ponytail applicability and documentation-only precedence rules. The reviewer returns surviving findings as JSON; do not persist them yet.
5. **CLOSEOUT:** Follow the numbered CLOSEOUT sequence below. Every other surface (the orchestrator prompt, the `commit` skill, README, plan templates) points here and does not restate it.

6. **FIX LOOP:** If focused verification, review, or closeout fails, update task tracking (the runtime's native tracker when available, otherwise the phase checklist as prose), return to IMPLEMENT, and repeat the checks and review before CLOSEOUT. A later code change restarts verification and review. Continue until `verify phase`/`verify closeout` report PASS and the findings report has `counts.critical == 0`. Resolve findings according to the ordinary severity gates: CRITICAL and MAJOR both block the phase-completion commit (not only push/PR), and a surviving MINOR needs an explicit disposition and reason but is otherwise advisory.
7. **COMMIT:** On normal completion, commit the explicitly staged completed small plan atomically.
8. **PUSH:** After every successful outer-repository commit, attempt a normal non-force push. Prefer the configured branch upstream with `GIT_TERMINAL_PROMPT=0 git push`; otherwise, when `origin` exists, use `GIT_TERMINAL_PROMPT=0 git push -u origin HEAD`. If no remote exists or authentication/network access fails, warn clearly and keep the local commit; do not retry interactively or fail the completed phase. This outer publication is separate from the nested `.claude` `ai-state` post-commit sync. PR creation and merge remain explicitly user-requested.

**Conditional checkpoint branch:** When the user explicitly requests a pause,
write the PAUSED session log and required pause frontmatter, then checkpoint
tracked outer-repository work. Do not run this branch merely because a gate
failed. The checkpoint leaves the phase active; on resume, reopen that same
small plan and run the full loop before its normal completion commit.

**A passing `verify phase`/`verify closeout` receipt plus a matching findings report with `counts.critical == 0` and `counts.major == 0`, and an explicit disposition and non-empty reason on every surviving MINOR, is required before a normal completion commit; the same contract is re-checked across every completed phase at PR/push closeout. An intermediate commit while the phase is still in progress is not blocked merely because an unresolved MAJOR exists. An explicitly evidenced paused checkpoint follows its separate non-final path. When the conditional `ponytail` profile ran, its metadata is recorded; when it did not run, metadata is optional and legacy reports remain compatible. Ponytail findings use these ordinary severity gates; there is no separate zero-Ponytail gate.**

---

### CLOSEOUT sequence

Do these steps in this order. Each step's position exists because the step after it reads what it produced. Skipping ahead produces receipts or reports that the commit gate rejects, and the only recovery is to redo every step from the one skipped.

1. **Documentation.** Update `README.md` and `docs/` for changed public behaviour (delegate to `documenter` unless the change is pure-internal). When the phase is the big plan's last entry in `phases:`, also run the standing final-phase documentation, memory, and LEARN audit. *Why first:* findings and receipts bind the final code and docs.
2. **Final AI state.** Set the small plan to `status: complete` with `closeout_session_log:` filled in and every step box ticked; tick the phase in the big plan; write `[LEARN]` entries (or the no-lessons marker) in the session log and `MEMORY.md`; write the session log's `## Verification` section for optional items. Leave the required-items summary lines for step 4.
3. **First nested checkpoint.** `git -C .claude add -A && git -C .claude commit -m "checkpoint: <reason>"`. *Why here:* `verify closeout` refuses to run at all while the big plan's bytes are not retrievable from nested Git.
4. **Stage, findings, phase receipt, closeout dry run.** In one Bash command that contains no `git commit`:
   - `git add` the intended outer files (never `git add -A`; never `openwiki/.run.json`) and inspect `git diff --cached`. *Why before findings:* the findings report records `dirty: true` when any tracked change is unstaged, and receipts bind `git write-tree` on the index.
   - Give every surviving MINOR an explicit `disposition` and non-empty `reason`, then `record_findings.py . --findings-json - --phase <current_phase> --profile <name>... --out .claude/quality_reports/findings-<current_phase>.json`, one `--profile` per reviewed profile.
   - `uv run python .claude/scripts/verify.py phase --format json --persist`.
   - `uv run python .claude/scripts/verify.py closeout --format text` **without** `--persist`. It needs the findings report and the phase receipt to exist, runs the plan's required `## Verification` items, and prints one summary line per item. Paste those lines into the session log's `## Verification` section and set `**Status:** COMPLETED`. If any item is not `PASS`, return to IMPLEMENT.
5. **Second nested checkpoint.** Same command as step 3. *Why here:* the closeout receipt hashes the session log, so the log must be final and checkpointed before the receipt exists. Findings and receipt files are not provenance-bound, so having them in this checkpoint is expected.
6. **Closeout receipt.** `uv run python .claude/scripts/verify.py closeout --format json --persist` (add `--documentation-na "<reason>"` only when documentation is explicitly not applicable). A receipt made before staging is rejected at commit with `closeout receipt final tracked state is stale`.
7. **Commit.** `git commit` in its **own** Bash command, after step 6 has finished. The `post-commit` hook checkpoints and publishes nested state; do not do that yourself.
8. **Push.** One normal push to the branch upstream with `GIT_TERMINAL_PROMPT=0`; a missing remote or an authentication failure is a warning, not a failure.

Two hard rules:

- **Never put `git commit` in the same Bash command as steps 4 or 6.** The commit gate hook inspects the *text* of every Bash command before it runs; a chain such as `record_findings ... && verify.py closeout --persist && git commit` is judged on the receipts that exist *before* the chain runs, is denied in full, and none of the steps execute.
- **Never checkpoint, publish, or push nested state between step 6 and step 7.** That changes what the receipts bind to and fails the commit with `closeout receipt governing control-plane provenance is stale`.

The reviewer does not persist findings; the coder does not create receipts; the orchestrator does steps 2 to 8 itself. An open CRITICAL or MAJOR finding blocks step 7; resolve it in the FIX LOOP rather than deferring it to push or PR.
## Bypass Policy

Commit-gate bypasses are allowed only for commit subjects beginning with:

- `fixup!` and `squash!` — unconditional recovery/history bypass, regardless
  of changed paths.
- `chore(typo):` and `docs(typo):` — bypass only when every changed path is
  eligible documentation content outside runtime/execution directories (for
  example ordinary Markdown docs, not `shared/scripts/`, hook logic,
  generated runtime, behavior-changing tests, or other executable code). A
  typo subject over an ineligible diff is not a bypass at all: it falls
  through to the full ceremony gate like any other commit, so a substantive
  runtime/code change cannot hide under a typo subject.

Every successful bypass commit is logged to `.claude/session_logs/hooks-bypass.log`. Publication and PR creation are blocked until bypasses since the big plan's `started_at` timestamp are acknowledged with `bypass_acknowledged: true` in the big-plan frontmatter.

Environment-variable bypasses are not supported.

---

## OpenWiki Refresh

OpenWiki runs host-driven, not through a bootstrap-spawned process: the
coding agent calls OpenWiki's own MCP tools directly (see
`.claude/skills/openwiki/SKILL.md`), and OpenWiki's server writes
`openwiki/**` and, at `openwiki_begin` only, a managed block into root
`AGENTS.md` and `CLAUDE.md`. A hook guard, `openwiki-guard.sh`, snapshots
both adapters and the OpenWiki workflow-file path before `openwiki_begin`
and restores them after; restore coverage differs by host, so the skill
also tells the agent when to run the restore manually. `mode: "update"` is
the only mode the guard allows; it denies `init`. A commit-time backstop in
`verify.py` refuses a commit that still carries the managed block, a new
OpenWiki workflow file, or a tracked `openwiki/.run.json`, independently of
the hook. See `workspace.instructions.md`'s Knowledge Ownership section for
why the result carries no authority: OpenWiki is derived context, not
authority.

---

## Knowledge-Refresh Final Phase

This is the single authoritative definition of the knowledge-refresh final
phase. The planner prompt, orchestrator prompt, the `plan-decomposition`
skill, and the big-plan template link here instead of restating it.

**When to add it.** While drafting or revising a big plan's `phases:` list,
append one dedicated final small plan, after every phase already listed,
only when all of these hold: `openwiki/INSTRUCTIONS.md` exists; the plan has
more than one phase; the plan changes documentable outer-repository
behavior (not read-only/reporting, and not AI-state-only work); and the
plan's own purpose is not itself a knowledge/OpenWiki refresh. Name the
appended phase's slug so it ends with `-knowledge-refresh` (for example
`2026-09-19_phase-D-knowledge-refresh`, not `...-phase-D-openwiki-sync` or
any other conventionally reasonable but differently worded slug) — this
exact suffix is what the termination rule below and
`scripts/validate_plan_frontmatter.py` both key on; a phase named anything
else is invisible to both and the recursion guard silently does nothing.

**Termination.** This rule runs only while drafting or revising a plan's
`phases:` list, and only ever appends to the end of that list. Recognize an
existing knowledge-refresh phase by its slug suffix, `-knowledge-refresh`;
if the phase already at the end of the list carries that suffix, do not
append another one. The self-referential exclusion above means a plan whose
own purpose is a knowledge refresh never has one appended to itself, so
that phase can never produce a second one, whether through a later revision
of the same plan or as the reason for a follow-up plan.
`scripts/validate_plan_frontmatter.py` enforces this deterministically: a
big plan fails validation if more than one phase carries the
`-knowledge-refresh` suffix, or if one exists but is not the last phase.

**Shape.** Small, and only this: refresh through
`.claude/skills/openwiki/SKILL.md`, inspect the generated
diff, run the standing final-phase documentation/memory/LEARN audit already
required below — the same `## Stale-claims surfaces checked` requirement;
this phase is what satisfies it, not a second, competing one — then review,
verify, and commit like any other phase. It does not carry a larger phase's
transition scope.

**Failure.** A failed refresh blocks that phase's completion like any other
failed phase, without fabricating a deterministic verification failure —
see "OpenWiki Refresh" above for that boundary. A provider or
authentication failure is reported with OpenWiki's own actionable error
and retried once fixed; an enabled repository's required refresh is never
silently skipped. An unreachable recorded base HEAD follows the skill's
rebaseline rule, never `--init`.

---

## Verification Evidence Contract

This is the single authoritative definition of a small plan's verification
evidence. Every other surface — the plan and session-log templates, the
`plan-decomposition` skill, the planner and orchestrator prompts, and the
`commit` skill — links to this section instead of restating it.

### The required `## Verification` block

A small plan's `## Verification` section holds one or more fenced code
blocks, each labeled `bash` or `sh` and fenced with either ``` or ~~~. Every
non-comment line inside those
blocks is a required item: a shell command that `verify closeout` runs
itself, from the repository root, and that must exit 0. Never list
`verify.py closeout` as a required item; it cannot certify itself.

Parse each fenced block with these rules, applied in order:

- Join a line that ends in `\` with the line that follows it, before
  evaluating either line.
- Drop a line whose first non-whitespace character is `#`.
- Cut a trailing ` # comment` from the end of a command line.
- Collapse repeated whitespace.

### The `## Optional Verification` section

`## Optional Verification` is an H2 section of top-level `- ` bullets. It is
the only place a check may be conditional or non-executable. Put an
interactive probe, a host session, or a manual inspection here, never in the
required block. Each bullet is one optional item, numbered from 1 in the
order it appears.

### What `verify closeout` does with the required items

`verify closeout` runs the required items itself, in order, before it binds
the tree. Each item gets `VERIFICATION_ITEM_TIMEOUT_SECONDS = 600` seconds.
It stops at the first item that is not `PASS` and refuses to persist a
receipt when any item failed, timed out, or was never run because an
earlier item stopped the run. On success, it stores the run results at
`extensions.verification_items` in the closeout receipt: for every item,
the item text, its status, exit code, duration, and the last 20 lines of
output. In `--format text`, it prints one summary line per item, for
example `PASS      1.3s  <item>`.

### The closeout session log

A completed small plan's session log has a `## Verification` section. Paste
the summary lines `verify closeout --format text` printed for the required
items. Then record every optional item's outcome, one line per item, in
this grammar:

```
- optional <n>: PASS|FAIL|NOT RUN — <detail>
```

A `NOT RUN` line needs a non-empty `<detail>` explaining why.

### The hedge rule

Outside a fenced code block and outside `## Optional Verification`, a live
small plan may not contain text matching `HEDGED_VERIFICATION_PATTERNS`. A
plan is live when its `status` is `planned`, `in-progress`, or `paused`, and
its slug date is absent or on or after `VERIFICATION_CONTRACT_SINCE =
"2026-09-19"`. Hedging a required check — writing that it runs only when
something is available, or marking it optional in prose instead of moving
it to `## Optional Verification` — turns a required item into one nobody
ever runs. A completed or cancelled plan is a dated record; it is never
re-judged.

`HEDGED_VERIFICATION_PATTERNS`, case-insensitive:

```text
\b(?:when|if|where|once|whenever|provided|should)\b[^.\n]{0,60}\b(?:available|possible|present|installed|exists|feasible|reachable|configured|set up)\b[^.\n]{0,60}\b(?:runs?|executes?|exercises?|smoke[- ]?(?:tests?|checks?)|checks?|verify|verifies|tests?|probes?|re-probes?|confirms?)\b
\b(?:runs?|executes?|exercises?|smoke[- ]?(?:tests?|checks?)|checks?|verify|verifies|tests?|probes?|re-probes?|confirms?)\b[^.\n]{0,80}\b(?:when|if|where|once|whenever|provided)\b[^.\n]{0,60}\b(?:available|possible|present|installed|exists|feasible|reachable|practical|configured|set up)\b
\b(?:as time permits|time permitting|optionally\s+(?:runs?|executes?|verify|verifies|checks?))\b
```

### Enforcement

Three scripts enforce this contract, at three different times. At plan
approval, `scripts/validate_plan_frontmatter.py` rejects the plan text
itself. At phase closeout, `verify.py closeout` refuses to persist a
receipt whenever a required item is not `PASS`; this refusal has no message
prefix, because it is `verify.py closeout`'s own ordinary failure path, not
a named lint or gate rule. At commit, `verify.py gate` blocks the commit,
and only when the plan and the receipt have an `exact` head relation.

| When | Script | Message prefix | Refuses when |
|---|---|---|---|
| Plan approval | `scripts/validate_plan_frontmatter.py` | `L1 verification-block-missing:` | the `## Verification` section has no `bash` or `sh` fenced block |
| Plan approval | `scripts/validate_plan_frontmatter.py` | `L2 hedged-verification:` | text matches a hedge pattern; the message quotes the matched text |
| Plan approval | `scripts/validate_plan_frontmatter.py` | `L3 unfailable-verification:` | a required item contains `\|\| true` or `\|\| :`, so it can never fail |
| Plan approval | `scripts/validate_plan_frontmatter.py` | `L4 self-listed-closeout:` | a required item lists `verify.py closeout` |
| Commit, `exact` relation only | `verify.py gate` | `G1 verification-results-missing:` | the receipt has no `extensions.verification_items` |
| Commit, `exact` relation only | `verify.py gate` | `G2 verification-item-unrun:` | a required item in the plan has no result in the receipt |
| Commit, `exact` relation only | `verify.py gate` | `G3 verification-item-failed:` | a recorded result's `status` is not `PASS` |
| Commit, `exact` relation only | `verify.py gate` | `G4 optional-verification-unaccounted:` | an optional item has no outcome line in the closeout session log |

---

## Reporting

Follow `.claude/instructions/agent-reporting.instructions.md` for human-facing
communication and agent-to-agent status or handoffs.

---

## Session Logging

**Log location:** `.claude/session_logs/YYYY-MM-DD_description.md`

**Log when:**
- After plan approval (goal, approach, rationale)
- During work: design decisions, problems solved, verification results, `[LEARN]` entries
- Before stopping: summary, verification results, open questions, next steps
- At small-plan closeout: `**Status:** COMPLETED`, `**Plan:** <small-plan path>`, `[LEARN]` entries or explicit no-lessons marker, and a `## Verification` section satisfying the Verification Evidence Contract above
- At an explicit checkpoint: `**Status:** PAUSED`, `**Plan:** <small-plan path>`, pause reason, completed and remaining work, verification state, incomplete checks, and resume point

**Frequency:** Every 30 responses or at session end, whichever comes first.

Merge-time review reports should be stored in `.claude/quality_reports/merges/`.

**Immutability:** A session log already bound by a completed phase's closeout
receipt must not be edited afterward; the receipt hashes its exact bytes, and
historical receipt-chain validation depends on that byte stability. Write a
correction to a sibling `<log-name>.errata.md` file next to the closed log
instead. An erratum discovered and written during a later active phase is
evidence of that later phase and may be bound by its own receipt; the earlier
phase's receipt is never edited or regenerated. An erratum written outside an
active plan may remain unbound until a later phase reviews or changes it.

**Conditional stale-claims review:** When a phase changes a previously
documented fact, number/count, behavior, API, decision, conclusion, or
pipeline/runtime description, search likely-affected active plans, `docs/`,
`README.md`, workflow/policy documentation, and `.claude/MEMORY.md`, then
update or explicitly supersede the stale claim. Record which surfaces were
checked in the session log when this rule triggers. Do not run this sweep
mechanically when nothing documented actually changed.

`.claude/MEMORY.md` is live advice, loaded into every session, not a dated
record. A superseded entry must be corrected or removed in place; appending a
correction elsewhere in the file and leaving the wrong entry standing is not
sufficient, because a reader can act on the wrong entry before ever reaching
the correction. Archived plans, dated design narratives, and closed session
logs are dated records instead — they describe what was true at the time and
are left unchanged; a closed session log's correction uses a sibling
`<log-name>.errata.md` file only where the original entry would actively
mislead a reader into reintroducing a defect, and only when no closeout
receipt binds that log.

**Standing final-phase audit:** The final phase of every big plan must run a
documentation, memory, and LEARN audit: sweep the live-advice surfaces above
for claims that this plan or earlier work invalidated (not only this plan's
own changes), correct or supersede each one under the live-advice/dated-record
distinction, and record the audited surfaces and each one's outcome under a
`## Stale-claims surfaces checked` heading in that phase's closeout session
log - the same heading the conditional review above already uses. This
recorded-surface-list evidence is a deterministic gate, not only documented
process: `verify.py`'s closeout check derives "final phase" from the big
plan's own `phases:` frontmatter list (the same source used elsewhere, so it
cannot become a second, independently drifting definition) and requires a
non-empty `## Stale-claims surfaces checked` section only when the phase
being closed out is that list's last entry - it never fires on an earlier
phase. It checks the section's presence and non-emptiness, not the
correctness of its judgement, matching the shape of the existing `## [LEARN]
Entries` evidence requirement next to it.

---

## Context Management

**Before finishing or when context is getting large:**
1. Save `[LEARN]` entries to `.claude/MEMORY.md`.
2. Update session log.
3. Ensure plan is saved to disk.
4. Document open questions.

**Starting a new session:**
1. Read `.claude/instructions/workspace.instructions.md` plus the current plan in `.claude/plans/` or exploration in `.claude/explorations/`.
2. If the current small plan is `paused`, read its `pause_session_log`, then set that same plan to `in-progress` while preserving its pause metadata; do not create another small plan.
3. Check `git log --oneline -10`, `git status`, and `git diff`.
4. State the recorded resume point, understood task, and next step.

---

## Recovery Checklist

```text
[ ] On dev before branch creation
[ ] Working tree clean before branch creation
[ ] Big plan and current small plan saved under .claude/plans/
[ ] Task tracking reflects canonical workflow and current loop
[ ] Verification passed (pytest + mypy + ruff via `verify phase`)
[ ] Review passed; findings persisted via record_findings.py (including Ponytail metadata when the profile was required)
[ ] Docs updated or explicitly skipped as pure-internal
[ ] Learn entries flushed or explicit no-lessons marker recorded
[ ] Closeout session log has Status: COMPLETED
[ ] Mermaid diagrams render without errors
```

---

## File Protection Rules

These protections are enforced by target-native hook adapters that call shared scripts in `.claude/hooks/scripts/`.

**Never modify these files directly** (edit manually only):
- `.env`, `.env.*`, `.env.local`
- `*.pem`, `*.key`, `*secret*`, `credentials*`
- `uv.lock` (managed by uv, not hand-edited)

Also blocked in pre-tool hooks:
- Dangerous git commands: `git push --force`, `git push -f`, `git reset --hard`, `git branch -D main/master`, `git clean -fd`

When asked to edit protected files or run blocked git commands, stop and explain why it is protected.

## Automatic Reminders

Some behaviors are automated by hooks. Others are still manual.

**Automated via hooks:**
- Protected file edits are denied.
- Dangerous git commands are denied.
- Implementation branch creation is gated on dev + clean tree + matching big plan.
- Commit closeout is gated on small-plan completion, a passing `verify phase`/`verify closeout` receipt, a matching findings report with `counts.critical == 0` and `counts.major == 0` plus an explicit disposition and non-empty reason on every surviving MINOR, required Ponytail review evidence where applicable, and DOCUMENT/LEARN/session-log evidence. An explicitly evidenced paused small plan may instead create a non-final checkpoint commit that does not advance the phase.
- A valid paused checkpoint commit may be pushed as a remote backup while the big plan remains `in-progress` and the same phase remains current. A normal completed-phase commit may also be pushed after post-commit advances `current_phase`, but only when its receipt and findings directly certify that exact commit; later in-progress work cannot publish under that authority. PR creation and final push closeout are gated on every small plan being complete or fully evidenced as cancelled, at least one completed phase, one commit per completed phase, bypass acknowledgement, required Ponytail review evidence where applicable, and a valid historical receipt chain across every completed phase, each with `counts.critical == 0` and `counts.major == 0`.
- Session start/end events are logged to `.claude/session_logs/hooks-sessions.log`.
- Session start pulls mutable AI state on the git-backed `ai-state` branch (`.claude/` is its own nested git repo; see `state-sync.sh`). Codex and Claude Stop each use one sequential log/check/checkpoint/publish wrapper; Codex returns JSON-only stdout and Claude emits no wrapper stdout. Both retry compatible `push` at `UserPromptSubmit` (60 seconds). Codex delayed SessionEnd and Claude StopFailure checkpoint locally only; Claude SessionEnd uses compatible `push` (60 seconds). Timeout or network failure preserves the local commit for retry; inspect `state-sync.sh status` and `.claude/session_logs/hooks-errors.log`. Closing a browser or editor tab is not a guaranteed lifecycle event, so do not rely on it for durability. The durable checkpoint-and-publish paths remain the `post-commit` git hook (after every outer-repo commit) and the explicit "AI state: push" VS Code task (manual, for state between commits).
- After an actual install or update, Codex for VS Code may require renewed review of content/hash-bound `.codex/hooks.json`. Reopen/reload the repository and approve project hooks only when Codex prompts; installers report this boundary but never approve hooks or mutate user trust settings.
- Runtime hook errors are logged to `.claude/session_logs/hooks-errors.log`.

**Manual reminders still required:**

**After editing any Python source file:**
```text
Run: uv run python .claude/scripts/verify.py fast --format json
```

`fast` selects the repository's real scope instead of assuming a `src/`
layout, so it stays correct in both the bootstrap authoring repository and an
installed consumer.

**Every ~30 responses or before stopping:**
```text
Update session log in .claude/session_logs/
Flush [LEARN] entries to .claude/MEMORY.md
```
