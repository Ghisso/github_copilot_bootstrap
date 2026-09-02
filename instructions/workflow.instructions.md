---
description: "Always-on: Workflow protocol, branch lifecycle, session logging, context management. Load when planning, implementing, or starting a session."
applicability: always
---

# Workflow: Pre-Flight -> Branch -> Plan When Needed -> Implement -> Verify -> Review -> Closeout -> Commit

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
PRE-FLIGHT -> BRANCH -> PLAN when needed -> IMPLEMENT -> VERIFY -> REVIEW -> CLOSEOUT -> COMMIT
```

For each small plan:

1. **PLAN:** If no implementation-ready plan exists, delegate to `planner` and save the concrete small plan under `.claude/plans/`. Otherwise use the approved existing plan directly. Before each new phase, perform the material-impact check above; use one planner only for affected future work.
2. **IMPLEMENT:** Delegate to `coder` (including Gradio/Streamlit UI work). The coder applies `.claude/skills/ponytail/SKILL.md` once in `full` mode, simplifies the changed scope, and re-verifies it; Ponytail is not a standalone lifecycle phase.
3. **VERIFY:** The orchestrator runs `uv run python .claude/scripts/verify.py phase --format json --persist`. Route a deterministic failure to the coder with its receipt and changed scope; do not spend another model merely to repeat deterministic checks.
4. **REVIEW:** Delegate to `reviewer` with profiles selected from the authoritative routing table, including its Ponytail applicability and documentation-only precedence rules. The reviewer returns surviving findings as JSON; do not persist them yet.
5. **CLOSEOUT:** In this fixed order: (a) delegate documentation applicability/update; (b) give every surviving MINOR finding an explicit `disposition` (e.g. `"accepted"`) and non-empty `reason`, then persist converged review findings with one `--profile <name>` per profile via `record_findings.py --out .claude/quality_reports/findings-<current_phase>.json`; (c) run `learn` or record `[LEARN] none - no new lessons this session`; (d) update the `COMPLETED` session log; then (e) run `uv run python .claude/scripts/verify.py closeout --format json --persist`. When documentation is explicitly not applicable, add `--documentation-na "<reason>"`; omission is not proof of N/A. Documentation precedes binding reports so findings remain fresh. The reviewer does not persist findings itself, and the coder cannot create final verification receipts.
6. **FIX LOOP:** If verification, review, or closeout fails, update TodoWrite, return to IMPLEMENT, and repeat until `verify phase`/`verify closeout` report PASS and the findings report has `counts.critical == 0`. Resolve findings according to the ordinary severity gates: CRITICAL and MAJOR both block the phase-completion commit (not only push/PR), and a surviving MINOR needs an explicit disposition and reason but is otherwise advisory.
7. **COMMIT:** On normal completion, commit the completed small plan atomically.

**Conditional checkpoint branch:** When the user explicitly requests a pause,
write the PAUSED session log and required pause frontmatter, then checkpoint
tracked outer-repository work. Do not run this branch merely because a gate
failed. The checkpoint leaves the phase active; on resume, reopen that same
small plan and run the full loop before its normal completion commit.

**A passing `verify phase`/`verify closeout` receipt plus a matching findings report with `counts.critical == 0` is required before a normal completion commit; `counts.major == 0` in that same report is additionally required before PR/push closeout. An explicitly evidenced paused checkpoint follows its separate non-final path. When the conditional `ponytail` profile ran, its metadata is recorded; when it did not run, metadata is optional and legacy reports remain compatible. Ponytail findings use these ordinary severity gates; there is no separate zero-Ponytail gate.**

---

## Bypass Policy

Commit-gate bypasses are allowed only for commit subjects beginning with:

- `fixup!`
- `squash!`
- `chore(typo):`
- `docs(typo):`

Every successful bypass commit is logged to `.claude/session_logs/hooks-bypass.log`. A PR is blocked until bypasses since the big plan's `started_at` timestamp are acknowledged with `bypass_acknowledged: true` in the big-plan frontmatter.

Environment-variable bypasses are not supported.

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
- At small-plan closeout: `**Status:** COMPLETED`, `**Plan:** <small-plan path>`, `[LEARN]` entries or explicit no-lessons marker
- At an explicit checkpoint: `**Status:** PAUSED`, `**Plan:** <small-plan path>`, pause reason, completed and remaining work, verification state, incomplete checks, and resume point

**Frequency:** Every 30 responses or at session end, whichever comes first.

Merge-time review reports should be stored in `.claude/quality_reports/merges/`.

---

## Context Management

**Before finishing or when context is getting large:**
1. Save `[LEARN]` entries to `.claude/MEMORY.md`.
2. Update session log.
3. Ensure plan is saved to disk.
4. Document open questions.

**Starting a new session:**
1. Read `.claude/instructions/workspace.md` plus the current plan in `.claude/plans/` or exploration in `.claude/explorations/`.
2. If the current small plan is `paused`, read its `pause_session_log`, then set that same plan to `in-progress` while preserving its pause metadata; do not create another small plan.
3. Check `git log --oneline -10`, `git status`, and `git diff`.
4. State the recorded resume point, understood task, and next step.

---

## Recovery Checklist

```text
[ ] On dev before branch creation
[ ] Working tree clean before branch creation
[ ] Big plan and current small plan saved under .claude/plans/
[ ] TodoWrite reflects canonical workflow and current loop
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
- Commit closeout is gated on small-plan completion, a passing `verify phase`/`verify closeout` receipt, a matching findings report with `counts.critical == 0`, required Ponytail review evidence where applicable, and DOCUMENT/LEARN/session-log evidence. An explicitly evidenced paused small plan may instead create a non-final checkpoint commit that does not advance the phase.
- A valid paused checkpoint commit may be pushed as a remote backup while the big plan remains `in-progress` and the same phase remains current. PR creation and final push closeout are gated on every small plan being complete or fully evidenced as cancelled, at least one completed phase, one commit per completed phase, bypass acknowledgement, required Ponytail review evidence where applicable, and the last completed phase's findings report additionally having `counts.major == 0`.
- Session start/end events are logged to `.claude/session_logs/hooks-sessions.log`.
- Session start pulls mutable AI state on the git-backed `ai-state` branch (`.claude/` is its own nested git repo; see `state-sync.sh`). Codex and Claude Stop each use one sequential log/check/checkpoint/publish wrapper; Codex returns JSON-only stdout and Claude emits no wrapper stdout. Both retry compatible `push` at `UserPromptSubmit` (60 seconds). Codex delayed SessionEnd and Claude StopFailure checkpoint locally only; Claude SessionEnd uses compatible `push` (60 seconds). Timeout or network failure preserves the local commit for retry; inspect `state-sync.sh status` and `.claude/session_logs/hooks-errors.log`. Closing a browser or editor tab is not a guaranteed lifecycle event, so do not rely on it for durability. The durable checkpoint-and-publish paths remain the `post-commit` git hook (after every outer-repo commit) and the explicit "AI state: push" VS Code task (manual, for state between commits).
- After an actual install or update, Codex for VS Code may require renewed review of content/hash-bound `.codex/hooks.json`. Reopen/reload the repository and approve project hooks only when Codex prompts; installers report this boundary but never approve hooks or mutate user trust settings.
- Runtime hook errors are logged to `.claude/session_logs/hooks-errors.log`.

**Manual reminders still required:**

**After editing any `src/**/*.py` file:**
```text
Run: uv run pytest tests/ -q --tb=short
Run: uv run mypy src/ --ignore-missing-imports --explicit-package-bases
Run: uv run ruff check src/ tests/
```

**Every ~30 responses or before stopping:**
```text
Update session log in .claude/session_logs/
Flush [LEARN] entries to .claude/MEMORY.md
```
