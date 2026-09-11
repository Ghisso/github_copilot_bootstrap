---
name: commit
visibility: public
description: |
  Git workflow for staging, committing, branching, pushing, and PR creation
  aligned with the enforced lifecycle (implementation branches off dev, PRs to
  dev). Use when ready to commit changes, publish a commit, or open a PR.
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
- Stage only after focused/fast checks, review, documentation, final plan/log/LEARN state, and before `record_findings.py`, `verify phase --persist`, and `verify closeout --persist`.
- `dirty` in the findings and receipt gates means unstaged tracked changes. Untracked files do not appear in `git diff`; stage intended files before recording findings.

## Phase 4: Commit
Choose one explicit commit path.

For a normal completion commit, commit exactly one completed small plan after
all gates pass: `status: complete`, a closeout log containing
`**Status:** COMPLETED`, LEARN evidence, and a passing `verify phase`/`verify
closeout` receipt matching the branch, phase, and HEAD.

For a paused checkpoint, commit only after the user explicitly asks to stop and
resume later. The same small plan must be `status: paused` with `paused_at`,
`paused_reason`, and `pause_session_log`; that log must contain
`**Status:** PAUSED`. A checkpoint needs real outer-repository work, does not
advance the phase machine, and does not require final findings, LEARN,
DOCUMENT, or a COMPLETED closeout. Never create an empty outer commit for only
AI-state files. It keeps the big plan `in-progress` with the same
`current_phase`.

```bash
git commit -m "type: description

Details of what changed and why."
```
Types: `feat` | `fix` | `refactor` | `test` | `docs` | `config`

## Phase 5: Push (automatic), then PR on request

Attempt one normal, non-force push after every successful outer-repository
commit. Use the branch upstream when it is configured; otherwise use `origin`:

```bash
GIT_TERMINAL_PROMPT=0 git push                    # upstream configured
GIT_TERMINAL_PROMPT=0 git push -u origin HEAD     # no upstream, origin exists
```

A missing remote, an authentication failure, or a network failure is a visible
warning only: report it, keep the completed commit local, and continue. Do not
retry interactively and do not force-push. This outer-repository publication is
separate from the nested `.claude` AI-state sync that the `post-commit` hook
runs on its own.

The push gate accepts three states. A valid paused checkpoint commit publishes
as a durable remote backup; it remains unfinished, keeps the big plan
`in-progress` with the same `current_phase`, and does not make the branch
PR-ready. The exact completion commit of the phase immediately before a
now-current `in-progress` phase publishes only when its receipt and findings
directly certify that one commit, so a later in-progress commit cannot publish
under that authority. For final closeout, every phase must be terminal:
`complete` or fully evidenced as `cancelled`, with at least one completed phase
and one commit per completed phase.

PR creation stays user-requested and must target `dev`:

```bash
gh pr create --base dev --title "type: description" --body "$(cat <<'EOF'
## Summary
- change 1
- change 2

## Test Plan
- [ ] tests pass
EOF
)"
```

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
