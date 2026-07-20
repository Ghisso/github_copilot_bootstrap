---
description: "Always-on: Workflow protocol, branch lifecycle, session logging, context management. Load when planning, implementing, or starting a session."
---

# Workflow: Pre-Flight -> Branch -> Plan -> Ponytail -> Implement -> Verify -> Review -> Score -> Document -> Learn -> Session Log -> Commit

---

## Plan-First Protocol

**For any non-trivial task (>1 file or >30 min), plan before coding.**

1. Check `.claude/MEMORY.md` for relevant `[LEARN]` entries.
2. For ambiguous/complex tasks: clarify with user (max 3-5 questions), optionally create a spec in `.claude/quality_reports/specs/`.
3. Draft plan -> save to `.claude/plans/` for concrete implementation plans or `.claude/explorations/` for exploratory/PoC plans.
4. Present to user -> wait for approval unless the user explicitly supplied an approved implementation plan.
5. After approval: create session log, then implement via the orchestrator loop.

**Skip planning only for:** single-file fixes, clear-and-specific requests, or when the user provides detailed approved steps.

---

## Branch Lifecycle

- `dev` is the working base branch for implementation work.
- Before starting new work, the current branch must be `dev` and the working tree must be clean.
- Each big plan creates exactly one implementation branch named `<plan_name>_implementation` from `dev`.
- Big plans live at `.claude/plans/<plan_name>.md` and must use `type: big-plan` frontmatter.
- Small plans live at `.claude/plans/<phase_slug>.md` and must use `type: small-plan` frontmatter.
- Commit once per completed small plan after DOCUMENT, LEARN, session log, and score gates pass.
- Open a PR to `dev` only after every small plan in the big plan is complete and only when the user explicitly asks for a PR.
- The user performs merge/squash decisions manually in GitHub. After merge, return to `dev` and pull before starting new work.

---

## Canonical Orchestrator Loop

```text
PRE-FLIGHT -> BRANCH -> PLAN -> PONYTAIL -> IMPLEMENT -> VERIFY -> REVIEW -> SCORE -> DOCUMENT -> LEARN -> SESSION LOG -> COMMIT
```

For each small plan:

1. **PLAN:** Delegate to `planner`; save concrete small-plan file under `.claude/plans/`.
2. **PONYTAIL:** Load `.claude/skills/ponytail/SKILL.md` in `full` mode and pass that requirement to every code-writing delegate.
3. **IMPLEMENT:** Delegate to `coder` (including Gradio/Streamlit UI work).
4. **VERIFY:** Delegate to `verifier`; run tests, typing, linting, imports, and score when available.
5. **REVIEW:** Delegate to `reviewer`; for every non-documentation diff include the `ponytail` profile alongside the normal correctness/security profiles. It runs its own primary and verification passes and returns the surviving findings as JSON (it has no `execute` capability, so it cannot persist them itself). Resolve every surviving Ponytail finding, even `MINOR`, then repeat IMPLEMENT/VERIFY/REVIEW. Persist the converged JSON with `record_findings.py --profile ponytail --phase <current_phase> --base-ref dev --findings-json <path> --out .claude/quality_reports/findings-<timestamp>.json`.
6. **SCORE:** Run `quality_score.py` with `--phase <current_phase> --base-ref dev --out .claude/quality_reports/score-<timestamp>.json`.
7. **FIX LOOP:** If verification, review, or score fails, update TodoWrite, re-add IMPLEMENT/VERIFY/REVIEW/SCORE, and repeat until score is >= 90, the findings report has `counts.critical == 0`, and a required Ponytail review has zero surviving Ponytail findings.
8. **DOCUMENT:** Delegate to `documenter` with diff range, changed files, and public/config/workflow/user-facing changes. Skip only when the change is purely internal.
9. **LEARN:** Run the `learn` skill and save reusable discoveries to `.claude/MEMORY.md`, or record `[LEARN] none - no new lessons this session`.
10. **SESSION LOG:** Update the closeout session log using `.claude/templates/session-log.md`; final status must be `COMPLETED`.
11. **COMMIT:** Commit the completed small plan atomically.

**Score >= 90 plus a matching findings report with `counts.critical == 0` is required before commit; `counts.major == 0` in that same report is additionally required before PR/push closeout. For non-documentation diffs the report must also have `ponytail_reviewed: true` and `ponytail_findings: 0`.**

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

## Subagent Reporting Style

Subagents reporting back to the orchestrator should use `caveman` `full` for narrative report sections. Preserve tables, code blocks, commands, file paths, identifiers, and structured findings literally. The documenter writes normal user-facing prose.

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
[ ] Review passed; findings persisted via record_findings.py (including ponytail_reviewed + zero Ponytail findings for non-documentation diffs)
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
- Commit closeout is gated on small-plan completion, score >= 90, a matching findings report with `counts.critical == 0`, required Ponytail review evidence, and DOCUMENT/LEARN/session-log evidence.
- PR creation/push is gated on all small plans complete, bypass acknowledgement, required Ponytail review evidence, and the findings report additionally having `counts.major == 0`.
- Session start/end events are logged to `.claude/session_logs/hooks-sessions.log`.
- Session start/stop pull/push mutable AI state on the git-backed `ai-state` branch (`.claude/` is its own nested git repo; see `state-sync.sh`).
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
