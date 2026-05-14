---
name: commit
description: |
  Git workflow for staging, committing, branching, PR creation, and merging.
  Use when ready to commit changes, create a PR, or merge a branch.
argument-hint: "[commit message]"
---

# commit — Git Workflow

## Phase 1: Status Check
```bash
git status
git diff --stat
```

## Phase 2: Branch Creation (if on main)
```bash
git checkout -b feature/description
```
**Never commit directly to main.**

## Phase 3: File Staging
```bash
git add src/changed_file.py tests/test_changed.py
```
- Stage specific files (never `git add .` or `git add -A`)
- **Never stage**: `.env`, secrets, credentials
- Review: `git diff --cached`

## Phase 4: Commit
```bash
git commit -m "type: description

Details of what changed and why."
```
Types: `feat` | `fix` | `refactor` | `test` | `docs` | `config`

## Phase 5: Push & PR (if requested)
```bash
git push -u origin feature/description
gh pr create --title "type: description" --body "$(cat <<'EOF'
## Summary
- change 1
- change 2

## Test Plan
- [ ] tests pass
EOF
)"
```

## Phase 6: Merge & Cleanup (if requested)
```bash
gh pr merge --merge
git checkout main && git pull
git branch -d feature/description
```

## Phase 7: Report
```
Committed: [hash] [message]
Files: N files changed
PR: [URL if created]
```
