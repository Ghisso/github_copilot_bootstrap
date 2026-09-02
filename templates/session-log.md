# Session: [short description]

**Date:** YYYY-MM-DD
**Plan:** [link to small-plan file]
**Status:** IN-PROGRESS | PAUSED | COMPLETED | CANCELLED | BLOCKED

Use `**Status:** COMPLETED` when the planned work finished and passed closeout.
Use `**Status:** CANCELLED` when an authorized plan or phase will never run.
Use `**Status:** PAUSED` only for an explicit user-requested checkpoint that
will resume later. A PAUSED log must record the pause reason, completed work,
verification already run, known failures or incomplete checks, remaining work,
the exact resume-next step, and a useful resume command, config, or model
identifier when applicable.

## Goal

[What this session aims to accomplish]

## Work Log

- **HH:MM** - [What was done, what was decided, what was learned]

## [LEARN] Entries

Add one bullet per real lesson, formatted as `[LEARN:category] what was
learned`. If nothing new was learned this session, use the exact
no-new-lessons marker documented in `.claude/session_logs/README.md`
instead. Delete this paragraph; an untouched template with no bullet line
here fails closeout.

## Verification Results

```bash
# pytest output
# mypy output
# ruff output
# verify.py phase/closeout receipt path
```

## Open Questions / Next Steps

- [Question or next step]

## Pause Checkpoint (PAUSED only)

- **Pause reason:**
- **Completed work:**
- **Verification already run:**
- **Known failures or incomplete checks:**
- **Remaining work:**
- **Resume next:**
- **Resume command/config/model:**
