---
name: onboard
visibility: public
description: |
  Learn this repository's structure and team conventions, verify important
  claims against source, and save private project context for later sessions.
  Use when joining a repository or when its guidance, docs, or layout change.
---

# Onboard this repository

The repository's tracked instructions take precedence over this personal
sidecar and over the notes you produce. Read those instructions first, then
read `README.md`. List `docs/` with `rg --files docs/` when it exists; open
only documents relevant to the current repository or task. Read any existing
`.ai-bootstrap/project-context.instructions.md` as prior findings to check.
Use direct file reads for known paths and `rg` for exact names or usages.
Verify important claims about entry points, architecture, configuration,
commands, and current behavior against source files and tests. Record a
disagreement between prose and source instead of treating either as proof.

## Find team conventions

Inspect tracked guidance, `README.md`, relevant docs, formatting and lint
configuration, and the tracked folder and file layout. Read representative
source files, nearby tests and fixtures, and repeated usages. For the area
you expect to change, inspect more nearby examples. Use read-only `git log`
for a bounded set of recent commit subjects. Treat a repeated pattern as
evidence, not as a team rule; do not infer a convention from one example or
one unusual commit.

Create or update `.ai-bootstrap/project-context.instructions.md` with a
short project summary, key directories and entry points, verified build and
test commands, relevant design decisions, current limits, and any material
disagreement between docs and source. Keep the notes concise and cite the
paths that support them. Include this exact section heading:

## Team conventions

In that section, explain supported practices for feature placement and
extension points; folder and file placement; variable, function, class, and
file naming; imports and public interfaces; configuration and dependencies;
error handling and logging; tests and fixtures; documentation; build and
test commands; and commit message style. Include branch and review practice
only when tracked guidance or history supports it. Label explicit team rules
separately from patterns inferred from repeated examples. Cite source paths
or commit hashes, describe meaningful exceptions or conflicts, and say when
evidence is too thin to infer a convention. State that these notes are
derived advice beneath tracked team guidance. End with a short checklist
for making a change that fits this repository. Do not copy whole files.

## Check private destinations before any write

The only files this skill may write are
`.ai-bootstrap/project-context.instructions.md` and `.ai-bootstrap/MEMORY.md`.
Check every condition below before changing either file. If any check fails,
explain the reason and leave both files unchanged.

- Require `.ai-bootstrap/` to exist as a real directory and to be ignored by
  Git (`git check-ignore`). Refuse a symlink at this state root or at either
  destination, including a dangling symlink.
- Resolve both destination paths and require each to remain inside the
  resolved state root. Refuse a tracked lexical or resolved destination;
  check both names with `git ls-files` before writing. Do not follow a
  symlink or overwrite a tracked file.

After these checks, update the context file and add or refresh exactly one
`[LEARN:domain]` pointer under `## Domain-Specific` in
`.ai-bootstrap/MEMORY.md`. The pointer must tell later sessions to read
`.ai-bootstrap/project-context.instructions.md` before coding and to follow
tracked team guidance when it differs. Preserve other memory entries and
avoid duplicate pointers on repeated runs. Check that both output paths are
still ignored (`git check-ignore`) and that `git status --porcelain
--untracked-files=all` shows no new files from this skill. Report the files
read, claims verified, conventions with thin evidence, and any conflicts.
