---
name: commit
visibility: public
description: |
  Git workflow for staging, committing, branching, and PR creation aligned with
  the enforced lifecycle (implementation branches off dev, PRs to dev). Use when
  ready to commit changes or open a PR.
argument-hint: "[commit message]"
---

# commit — Git Workflow

This follows the lifecycle the hooks enforce: implementation branches are named
`<plan_name>_implementation` and cut from a clean `dev`, PRs target `dev`, and a
human merges the PR. The guardrails reject non-`_implementation` branch names,
PRs to `main`, and agent-driven merges — do not fight them.

Use this skill only for standard implementation or control-plane/high-risk work
classified by `.claude/instructions/workflow.instructions.md`. A requested
commit or PR is never a lightweight edit. The narrow audited typo bypasses are
recovery exceptions, not task-lane classification or a way around lifecycle
requirements.

## Phase 1: Status Check
```bash
git status
git diff --stat
```

## Phase 2: Branch (if not already on an implementation branch)
Cut the implementation branch from a clean `dev`, named for the big plan:
```bash
git switch dev
git switch -c <plan_name>_implementation
```
**Never commit directly to `dev` or `main`.** The branch name must end in `_implementation`.

## Phase 3: File Staging
```bash
git add src/changed_file.py tests/test_changed.py
```
- Stage specific files (never `git add .` or `git add -A`)
- **Never stage**: `.env`, secrets, credentials
- Review: `git diff --cached`

## Phase 4: Commit
Choose one explicit commit path.

For a normal completion commit, commit exactly one completed small plan after
all gates pass: `status: complete`, a closeout log containing
`**Status:** COMPLETED`, LEARN evidence, and a fresh score ≥ 90 report matching
the branch, phase, and HEAD.

For a paused checkpoint, commit only after the user explicitly asks to stop and
resume later. The same small plan must be `status: paused` with `paused_at`,
`paused_reason`, and `pause_session_log`; that log must contain
`**Status:** PAUSED`. A checkpoint needs real outer-repository work, does not
advance the phase machine, and does not require final score, findings, LEARN,
DOCUMENT, or a COMPLETED closeout. Never create an empty outer commit for only
AI-state files. It keeps the big plan `in-progress` with the same
`current_phase`.

```bash
git commit -m "type: description

Details of what changed and why."
```
Types: `feat` | `fix` | `refactor` | `test` | `docs` | `config`

## Phase 5: Push & PR (if requested, after the last small plan)
```bash
git push -u origin <plan_name>_implementation
gh pr create --base dev --title "type: description" --body "$(cat <<'EOF'
## Summary
- change 1
- change 2

## Test Plan
- [ ] tests pass
EOF
)"
```
PRs must target `dev`. Every phase must be terminal: `complete` or fully
evidenced as `cancelled`. There must be at least one completed phase and one
commit per completed phase. Paused phases remain unfinished and block push/PR
closeout.

## Phase 6: Merge (human)
A human reviews and merges the PR into `dev`; the agent does not merge the PR
itself. Once the merge lands, return to `dev`:
```bash
git switch dev && git pull
```

## Phase 7: Report
```
Committed: [hash] [message]
Files: N files changed
PR: [URL if created]
```
