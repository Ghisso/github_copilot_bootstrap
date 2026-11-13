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

1. Search `.claude/MEMORY.md` for the task's area tags (for example `[LEARN:installer]`) and keywords, and read the matching entries. Read the whole file only for a memory audit.
2. For ambiguous/complex tasks: clarify user preferences (max 3-5 questions) and settle decisive technical assumptions with evidence (planner Phase 1). A spec in `.claude/quality_reports/specs/` and requirement IDs are optional; equivalent approved content in the plan suffices.
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

Plan-course changes live in `.claude/instructions/plan-lifecycle.instructions.md`. Before you make one, read its section:

- Declaring phases that have not started (`planned`): "Declaring future phases".
- Pausing, only after the user explicitly asks to stop or checkpoint: "Pausing a phase for a checkpoint".
- Cancelling a plan or phase: "Cancelling a plan or phase".
- Adding phases to a `complete` big plan with an unmerged branch: "Reopening a completed big plan".
- Drafting a big plan's `phases:` list: "Knowledge-Refresh Final Phase".

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
5. **CLOSEOUT:** On entering CLOSEOUT, read and follow `.claude/instructions/closeout.instructions.md` step by step. The orchestrator prompt, the `commit` skill, README, and the plan templates point at that file and do not restate it.
6. **FIX LOOP:** If focused verification, review, or closeout fails, update task tracking (the runtime's native tracker when available, otherwise the phase checklist as prose), return to IMPLEMENT, and repeat the checks and review before CLOSEOUT. A later code change restarts verification and review. Continue until `verify phase`/`verify closeout` report PASS and the findings report has `counts.critical == 0`. Resolve findings by the severity contract in the closeout file: CRITICAL and MAJOR both block the completion commit.
7. **COMMIT:** On normal completion, commit the explicitly staged completed small plan atomically.
8. **PUSH:** After every successful outer-repository commit, attempt one normal non-force push; a missing remote or an authentication or network failure is a warning that keeps the local commit. This push is separate from the nested `.claude` `ai-state` sync. PR creation and merge remain explicitly user-requested.

**Conditional checkpoint branch:** only an explicit user pause request starts it; see its section in `.claude/instructions/plan-lifecycle.instructions.md`. A failed gate alone never does.

---

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
order it appears. The closeout session log records each optional item's
outcome in the grammar in `.claude/instructions/closeout.instructions.md`.

### What `verify closeout` does with the required items

`verify closeout` runs the required items itself, in order, each with
`VERIFICATION_ITEM_TIMEOUT_SECONDS = 600` seconds. It stops at the first item
that is not `PASS` and refuses to persist a receipt when any item failed,
timed out, or never ran. `--format text` prints one summary line per item, for
example `PASS      1.3s  <item>`.

### The hedge rule

Outside a fenced code block and outside `## Optional Verification`, a live
small plan may not hedge a required check, for example by writing that it runs
only when something is available, or by marking it optional in prose. A hedged
check is one nobody ever runs. A plan is live when its `status` is `planned`,
`in-progress`, or `paused`, and its slug date is absent or on or after
`VERIFICATION_CONTRACT_SINCE = "2026-09-19"`; a completed or cancelled plan is
a dated record and is never re-judged. The matching patterns are
`HEDGED_VERIFICATION_PATTERNS` in `.claude/scripts/validate_plan_frontmatter.py`.

### Enforcement

`scripts/validate_plan_frontmatter.py` (L1-L4, at branch creation and commit)
and `verify.py gate` (G1-G4, at commit) name the broken rule in their
messages.

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
- At small-plan closeout: the fields in "Closeout session log" in `.claude/instructions/closeout.instructions.md`
- At an explicit checkpoint: `**Status:** PAUSED`, `**Plan:** <small-plan path>`, pause reason, completed and remaining work, verification state, incomplete checks, and resume point

**Frequency:** Every 30 responses or at session end, whichever comes first.

Merge-time review reports should be stored in `.claude/quality_reports/merges/`.

A session log bound by a closeout receipt is never edited; see "Immutability"
in `.claude/instructions/closeout.instructions.md`.

**Conditional stale-claims review:** When a phase changes a previously
documented fact, number/count, behavior, API, decision, conclusion, or
pipeline/runtime description, search likely-affected active plans, `docs/`,
`README.md`, workflow/policy documentation, and `.claude/MEMORY.md`, then
update or explicitly supersede the stale claim. Record which surfaces were
checked in the session log when this rule triggers. Do not run this sweep
mechanically when nothing documented actually changed. The final phase of every
big plan also runs the standing final-phase audit in the closeout file.

`.claude/MEMORY.md` is live advice that agents act on, not a dated record. A
superseded entry must be corrected or removed in place; appending a
correction elsewhere in the file and leaving the wrong entry standing is not
sufficient, because a reader can act on the wrong entry before ever reaching
the correction. Archived plans, dated design narratives, and closed session
logs are dated records: they describe what was true at the time and stay
unchanged. A closed log's correction goes in a sibling `<log-name>.errata.md`,
only where the original entry would actively mislead a reader into
reintroducing a defect and no closeout receipt binds the log.

---

## Context Management

**Before finishing or when context is getting large:** save `[LEARN]` entries to `.claude/MEMORY.md`, update the session log, make sure the plan is saved to disk, and document open questions.

**Starting a new session:**
1. Read `.claude/instructions/workspace.instructions.md` plus the current plan in `.claude/plans/` or exploration in `.claude/explorations/`.
2. Search `.claude/MEMORY.md` for the task's area tags (for example `[LEARN:installer]`) and keywords, and read the matching entries. Read the whole file only for a memory audit.
3. If the current small plan is `paused`, read its `pause_session_log`, then set that same plan to `in-progress` while preserving its pause metadata; do not create another small plan.
4. Check `git log --oneline -10`, `git status`, and `git diff`.
5. State the recorded resume point, understood task, and next step.

---

## Automatic Reminders

**Automated via hooks:**
- Secret-shaped files, hook, server, agent, and workspace configuration, and dangerous Git commands are guarded (see root guidance).
- Implementation branch creation is gated on `dev`, a clean tree, a matching big plan, and plan checks L1-L4 on the big plan and its listed phase files.
- A completion commit is gated by the completion-commit gate in `.claude/instructions/closeout.instructions.md`. That file also lists the PR and push gates.
- Session start/end events go to `.claude/session_logs/hooks-sessions.log`; runtime hook errors go to `hooks-errors.log` in the same folder.
- Session start pulls mutable AI state from the `ai-state` branch of the nested `.claude/` repository (`state-sync.sh`). Hooks checkpoint and publish it, and a timeout or network failure keeps the local commit for a retry. Inspect `state-sync.sh status` and `hooks-errors.log`; a `lock: held` that outlasts any running sync means a stuck process (find it with `lsof <repository root>`). The durable paths are the `post-commit` hook and the manual VS Code task "AI state: push"; closing a browser or editor tab is not a guaranteed lifecycle event.

**Manual reminders:**
- After editing any Python source file, run `uv run python .claude/scripts/verify.py fast --format json` (it selects the repository's real scope, in an installed consumer or the authoring repository).
- Every ~30 responses or before stopping, update the session log in `.claude/session_logs/` and flush `[LEARN]` entries to `.claude/MEMORY.md`.
