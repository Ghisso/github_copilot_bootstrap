---
name: caveman-compress
visibility: public
description: |
  Safely compress note-like natural-language files into terse form while
  preserving code and structure. Use when:
  - User asks to "compress this memory file", "shrink this markdown", or
    invokes "/caveman:compress <filepath>"
  - You want lower recurring context cost for prose-heavy notes or logs
  - The target is a note-like file, not a source-of-truth customization file
argument-hint: "<filepath>"
---

# Caveman Compress

## Problem

Large prose-heavy markdown files cost tokens every time the agent reads them.
Compression helps for notes and logs, but it is dangerous for skill files,
instructions, and agent definitions that depend on exact trigger phrases,
frontmatter, and table structure.

## Context / Trigger Conditions

Use this skill for note-like files such as:

- session notes
- exploration documents
- project notes
- prose-heavy markdown docs that are not machine-sensitive

Do not use this skill on source-of-truth customization files.

## Solution

### Allowed targets

- `.md`, `.txt`, `.markdown`, `.rst`
- extensionless natural-language files
- mixed prose/code docs where only the prose sections need compression

### Hard-blocked targets

- `CLAUDE.md`
- `shared/policies/**`
- `.claude/skills/**/SKILL.md`
- `shared/agents/**`
- `shared/review-profiles/**`
- `*.original.md`
- code and config files

### Workflow

1. Run the detector first:

   ```bash
   uv run python .claude/skills/caveman-compress/scripts/detect.py <filepath>
   ```

2. If the detector rejects the file, stop and explain why.
3. Read the target file.
4. Refuse to continue if a sibling `.original.md` backup already exists, unless the user explicitly asks to replace it.
5. Create `<stem>.original.md` with the untouched original text.
6. Rewrite only the prose sections in caveman style.
7. Preserve exactly:
   - YAML frontmatter
   - heading text
   - code blocks
   - inline code
   - URLs and links
   - file paths and commands
   - table structure
   - numbers, versions, and identifiers
8. Validate the result:

   ```bash
   uv run python .claude/skills/caveman-compress/scripts/validate.py <original-backup> <compressed-file>
   ```

9. If validation reports errors, patch only the broken sections and rerun validation.
10. If validation still fails, restore the original file from the backup and report the failure.

## Verification

- Detector blocks protected targets before any rewrite.
- A `.original.md` backup exists beside every compressed file.
- Validation passes with zero errors.
- Only prose became shorter; protected structures stayed exact.

## Example

```text
/caveman:compress .claude/session_logs/2026-04-09_caveman-integration.md
```

Expected flow:

- detector accepts the session log
- backup is created
- prose is shortened
- validator confirms frontmatter-free markdown structure is still intact

## References

- `.claude/skills/caveman-compress/scripts/detect.py`
- `.claude/skills/caveman-compress/scripts/validate.py`
