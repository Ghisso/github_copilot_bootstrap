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
uv run python - <<'PY'
from pathlib import Path

for path in sorted(Path(".claude/plans").glob("*.md")):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        continue
    frontmatter = text.split("---", 2)[1]
    fields = dict(
        line.split(":", 1) for line in frontmatter.splitlines() if ":" in line
    )
    plan_type = fields.get("type", "").strip()
    status = fields.get("status", "").strip()
    if plan_type in {"big-plan", "small-plan"}:
        print(f"{plan_type}\t{status}\t{path.name}")
PY
```

Report the active big plan from its parsed `type: big-plan` and live status
(`planning`, `in-progress`, `complete`, or `cancelled`). Report the current
small plan from `type: small-plan` and its live status (`in-progress`,
`paused`, `complete`, or `cancelled`); prefer an `in-progress` or `paused`
small plan when more than one file exists.

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
  Active Big Plan: [filename] ([planning/in-progress/complete/cancelled]) or none
  Active Small Plan: [filename] ([in-progress/paused/complete/cancelled]) or none
  Session Log: [filename] (updated [N] min ago) or none
  MEMORY.md:   [N] lines, [M] [LEARN] entries
  Git:         [branch] ([N] uncommitted changes)
  Ruff:        [N violations or clean]

Recommendations:
  [warnings or suggestions]
```
