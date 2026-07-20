---
name: context-status
visibility: public
description: |
  Show session health: active plan status, session log recency, MEMORY.md size,
  and git status. Use when asked for session status, context health, or "what's
  the current state?".
---

# context-status — Session Health

## Checks

### 1. Active Plan
```bash
ls -lt .claude/plans/*.md 2>/dev/null | grep -v ".gitkeep" | head -3
```

### 2. Session Log Recency
```bash
ls -lt .claude/session_logs/*.md 2>/dev/null | grep -v ".gitkeep" | head -3
```

### 3. MEMORY.md
```bash
wc -l .claude/MEMORY.md
grep -c "\[LEARN" .claude/MEMORY.md
```

### 4. Git Status
```bash
git status --short
git log --oneline -5
```

### 5. Quality Check (quick)
```bash
uv run ruff check src/ tests/ --statistics 2>/dev/null | tail -3
```

## Report Format

```
Session Status:
  Active Plan: [filename] ([DRAFT/APPROVED/COMPLETED]) or none
  Session Log: [filename] (updated [N] min ago) or none
  MEMORY.md:   [N] lines, [M] [LEARN] entries
  Git:         [branch] ([N] uncommitted changes)
  Ruff:        [N violations or clean]

Recommendations:
  [warnings or suggestions]
```
