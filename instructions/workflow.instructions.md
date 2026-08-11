---
description: "Always-on: Workflow protocol, branch lifecycle, session logging, context management. Load when planning, implementing, or starting a session."
applicability: always
---

# Workflow: Pre-Flight -> Branch -> Plan -> Implement -> Verify -> Review -> Document -> Score -> Learn -> Session Log -> Commit

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
- Commit once per completed small plan after DOCUMENT, LEARN, session log, and score gates pass.
- Open a PR to `dev` only after every small plan in the big plan is complete or cancelled and only when the user explicitly asks for a PR.
- The user performs merge/squash decisions manually in GitHub. After merge, return to `dev` and pull before starting new work.

### Cancelling a plan or phase

`cancelled` means an authorized decision was made that a plan or phase will
never run. It is distinct from `complete` and requires `cancelled_at` as a real
UTC calendar date and time in exact `YYYY-MM-DDTHH:MM:SSZ` format; a meaningful
`cancelled_reason` written as plain single-line scalar prose without leading
quotes, YAML block headers, collections, list markers, or comment-only values;
and a repository-relative `cancelled_evidence` path that stays inside the
repository and resolves to an existing regular, readable UTF-8 text artifact
containing the same-line prefix `**Status:** CANCELLED`.

A cancelled phase requires no commit, findings report, score, or closeout
session log. A cancelled big plan is terminal and cannot start an implementation
branch. A branch containing cancelled phases becomes pushable only when at
least one phase is complete, every cancelled phase has the full evidence
contract, and commit-count checks count completed phases only. Gate support for
these conditions is separate from the status contract. Until Phase D implements
that behavior, the existing push gate remains strict and a branch containing a
cancelled phase remains blocked.

---

## Canonical Orchestrator Loop

```text
PRE-FLIGHT -> BRANCH -> PLAN -> IMPLEMENT -> VERIFY -> REVIEW -> DOCUMENT -> SCORE -> LEARN -> SESSION LOG -> COMMIT
```

For each small plan:

1. **PLAN:** Delegate to `planner`; save concrete small-plan file under `.claude/plans/`.
2. **IMPLEMENT:** Delegate to `coder` (including Gradio/Streamlit UI work). The coder applies `.claude/skills/ponytail/SKILL.md` once in `full` mode, simplifies the changed scope, and re-verifies it; Ponytail is not a standalone lifecycle phase.
3. **VERIFY:** Delegate to `verifier`; run tests, typing, linting, imports, and score when available.
4. **REVIEW:** Delegate to `reviewer` with profiles selected from the authoritative routing table, including its Ponytail applicability and documentation-only precedence rules. The reviewer returns surviving findings as JSON; do not persist them yet.
5. **DOCUMENT:** Delegate to `documenter` with diff range, changed files, and public/config/workflow/user-facing changes. Skip only when the change is purely internal. DOCUMENT runs before the persisted SCORE/FINDINGS so the documenter's tracked edits are inside the content those reports are bound to — otherwise a post-score doc change stales both.
6. **SCORE & PERSIST:** After documentation is final, persist the converged findings with one `--profile <name>` for each profile that ran, then run `quality_score.py` with `--phase <current_phase> --base-ref dev --out .claude/quality_reports/score-<timestamp>.json`. Both artifacts bind to the final code+docs `content_hash`. Doc-only changes from DOCUMENT are not re-reviewed — the code review already converged; persisting here simply keeps the reports fresh against the committed content. Re-run REVIEW only if a later fix changes code.
7. **FIX LOOP:** If verification, review, or score fails, update TodoWrite, re-add IMPLEMENT/VERIFY/REVIEW/DOCUMENT/SCORE, and repeat until score is >= 90 and the findings report has `counts.critical == 0`. Resolve findings according to the ordinary severity gates: CRITICAL blocks commit, MAJOR blocks push/PR, and MINOR is advisory.
8. **LEARN:** Run the `learn` skill and save reusable discoveries to `.claude/MEMORY.md`, or record `[LEARN] none - no new lessons this session`.
9. **SESSION LOG:** Update the closeout session log using `.claude/templates/session-log.md`; final status must be `COMPLETED`.
10. **COMMIT:** Commit the completed small plan atomically.

**Score >= 90 plus a matching findings report with `counts.critical == 0` is required before commit; `counts.major == 0` in that same report is additionally required before PR/push closeout. When the conditional `ponytail` profile ran, its metadata is recorded; when it did not run, metadata is optional and legacy reports remain compatible. Ponytail findings use these ordinary severity gates; there is no separate zero-Ponytail gate.**

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
- Before stopping: summary, scores, open questions, next steps
- At small-plan closeout: `**Status:** COMPLETED`, `**Plan:** <small-plan path>`, `[LEARN]` entries or explicit no-lessons marker

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
2. Check `git log --oneline -10` and `git diff`.
3. State understood task and next step.

---

## Recovery Checklist

```text
[ ] On dev before branch creation
[ ] Working tree clean before branch creation
[ ] Big plan and current small plan saved under .claude/plans/
[ ] TodoWrite reflects canonical workflow and current loop
[ ] Verification passed (pytest + mypy + ruff)
[ ] Review passed; findings persisted via record_findings.py (including Ponytail metadata when the profile was required)
[ ] Score >= 90 with persisted matching quality report
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
- Commit closeout is gated on small-plan completion, score >= 90, a matching findings report with `counts.critical == 0`, required Ponytail review evidence where applicable, and DOCUMENT/LEARN/session-log evidence.
- PR creation/push is gated on all small plans complete, bypass acknowledgement, required Ponytail review evidence where applicable, and the findings report additionally having `counts.major == 0`.
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
