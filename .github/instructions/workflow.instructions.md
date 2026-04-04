---
description: "Always-on: Workflow protocol — plan-first, orchestrator loop, session logging, context management. Load when planning, implementing, or starting a session."
---

# Workflow: Plan → Implement → Verify → Review → Score

---

## Plan-First Protocol

**For any non-trivial task (>1 file or >30 min), plan before coding.**

1. Check `.github/MEMORY.md` for relevant `[LEARN]` entries
2. For ambiguous/complex tasks: clarify with user (max 3-5 questions)
3. Draft plan → save to `.github/plans/YYYY-MM-DD_short-description.md`
4. Present to user → wait for approval
5. After approval: create session log, then implement via Orchestrator Loop

**Skip planning for:** single-file fixes, clear-and-specific requests, or when user provides detailed steps.

---

## Orchestrator Loop (After Plan Approval)

```
IMPLEMENT → VERIFY → REVIEW → FIX → RE-VERIFY → SCORE
    ↑                                              |
    └──────── loop (max 5 rounds) ←────────────────┘
```

**IMPLEMENT:** Config-first: create dataclass + ConfigStore before feature code. Test-as-you-go.

**VERIFY:**
```bash
uv run pytest tests/ -q
uv run mypy src/ --ignore-missing-imports --explicit-package-bases
uv run ruff check src/ tests/
```

**REVIEW agents by file type:**

| Pattern | Agents |
|---|---|
| `src/**/*.py` | code-reviewer, security-reviewer, architecture-reviewer |
| `tests/**/*.py` | test-reviewer |
| `service.py`, `src/api/**` | api-reviewer, security-reviewer |
| `src/configs/**` | config-reviewer |

**FIX:** Critical → Major → Minor order.

**SCORE:** See `quality-and-testing.instructions.md` rubric.
- Score ≥ 80 = commit
- Score ≥ 90 = PR-ready

**"Just do it" mode:** Skip final approval pause, auto-commit if score ≥ 80, still run full loop.

---

## Session Logging

**Log location:** `.github/session_logs/YYYY-MM-DD_description.md`

**Log when:**
- After plan approval (goal, approach, rationale)
- During work: design decisions, problems solved, verification results, `[LEARN]` entries
- Before stopping: summary, scores, open questions, next steps

**Frequency:** Every 30 responses or at session end (whichever comes first).

---

## Context Management

**Before finishing or when context is getting large:**
1. Save `[LEARN]` entries to `.github/MEMORY.md`
2. Update session log
3. Ensure plan is saved to disk
4. Document open questions

**Starting a new session:**
1. Read `copilot-instructions.md` + most recent plan in `.github/plans/`
2. Check `git log --oneline -10` and `git diff`
3. State understood task and next step

---

## Recovery Checklist

```
[ ] Plan saved to .github/plans/
[ ] Session log created/updated
[ ] MEMORY.md has all [LEARN] entries
[ ] Verification passed (pytest + mypy + ruff)
[ ] Score ≥ threshold before commit/PR
```

---

## File Protection Rules

These protections are enforced by hooks in `.github/hooks/hooks.json`.

**Never modify these files directly** (edit manually only):
- `.env`, `.env.*`, `.env.local`
- `*.pem`, `*.key`, `*secret*`, `credentials*`
- `uv.lock` (managed by uv, not hand-edited)

Also blocked in pre-tool hooks:
- Dangerous git commands: `git push --force`, `git push -f`, `git reset --hard`, `git branch -D main/master`, `git clean -fd`

When asked to edit protected files or run blocked git commands, stop and explain why it's protected.

---

## Automatic Reminders

Some behaviors are automated by hooks. Others are still manual.

**Automated via hooks:**
- Protected file edits are denied
- Dangerous git commands are denied
- Session start/end events are logged to `.github/session_logs/hooks-sessions.log`
- Runtime hook errors are logged to `.github/session_logs/hooks-errors.log`

**Manual reminders still required:**

**After editing any `src/**/*.py` file:**
```
→ Run: uv run pytest tests/ -q --tb=short
```

**Every ~30 responses or before stopping:**
```
→ Update session log in .github/session_logs/
→ Flush [LEARN] entries to .github/MEMORY.md
```

**When the conversation is long / context is filling up:**
```
→ Save plan to .github/plans/
→ Update MEMORY.md with all [LEARN] entries
→ Write session log with open questions and next steps
```
