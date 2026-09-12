---
name: onboard
visibility: public
description: |
  Build or refresh this session's understanding of the project: read the
  README, index docs/ and retrieve targeted content from it, cross-check
  claims against the real code with direct reads, exact search, and Semble,
  then persist the findings so future agents don't have to redo the
  discovery. Use when asked to "get oriented", "understand this project",
  "refresh project context", or after README/docs/architecture changed
  significantly.
---

# onboard — Project Understanding + Persistence

## Problem

Re-deriving project understanding (what does this repo do, how is it
built, what's still prototype/unverified) from scratch every session
wastes a full read-and-search pass, and whatever gets learned is easy to
lose. `CLAUDE.md` and `AGENTS.md` at the repo root are **gitignored,
regenerated artifacts** (confirm with `git check-ignore -v CLAUDE.md
AGENTS.md`) — edits there are local-only and do not survive a fresh clone
or the next bootstrap regen. The durable location is the `.claude/`
nested git repo (its own git history, synced to the `ai-state` branch by
session hooks).

## Steps

### 1. Build a small project index, then retrieve on demand

- `README.md`
- `.claude/instructions/project-context.instructions.md` if it already
  exists — treat it as prior findings to refresh, not to redo from zero.
- List `docs/` (e.g. `ls docs/` or `rg --files docs/`) to index what exists
  by filename, rather than reading every file unconditionally. Open only
  the docs needed to confirm a specific README claim, fill a gap the
  existing `project-context.instructions.md` flags, or answer the current
  task's open question.
- For a large or unfamiliar `docs/` tree, prefer `mcp__semble__search` or a
  targeted `rg` query over a sequential full read.

### 2. Cross-check against the real code

Per `.claude/instructions/tool-routing.instructions.md`: use direct reads for
known files, `rg` for exact claims, and Semble for semantic "where is X
actually implemented" discovery. The Context Mode MCP server exposes exactly
four guarded tools (`ctx_index`, `ctx_search`, `ctx_stats`, `ctx_doctor`);
`ctx_index` accepts content, a contained regular file, or a contained real
directory. Directory indexing uses the pinned upstream defaults and does not
accept directory-policy overrides.

```
mcp__semble__search(repo=<project root>, query="<key behavior claimed in the docs>")
```

Confirm each major doc claim (entry points, key modules, config,
architecture) against actual file locations — docs describe intent, code
is ground truth. Note any mismatch explicitly instead of silently trusting
the docs.

### 3. Persist findings for future agents

Create or update `.claude/instructions/project-context.instructions.md`
with frontmatter:

```yaml
---
description: "Always-on: what this specific repo is and how it's built. Not part of the generated shared/ bootstrap — safe to hand-edit."
---
```

Cover:
- What the project is / is not (call out any generic framework guidance
  in the shared bootstrap — e.g. Hydra/BentoML/Gradio — that doesn't
  apply to this repo's actual stack)
- Repository layout, one line of purpose per key file/directory
- The pipeline / data flow, as a short list or ascii diagram
- Design decisions worth knowing before touching the code — the *why*,
  not the *what* (the code already shows what)
- Current status and any pre-production / pre-merge verification checklist
- Explicit scope boundaries (what's deliberately out of scope, and why)

This file is intentionally **not** part of the generated `shared/` output
(cross-check against `.claude/bootstrap-root/`, the vendored template, if
unsure) — safe to hand-edit and safe to re-run this skill against.

### 4. Add or refresh the MEMORY.md pointer

In `.claude/MEMORY.md` under `## Domain-Specific`, add or update a single
`[LEARN:domain]` entry that:
- One-line summarizes the project
- Flags any generic-template guidance that doesn't apply here
- Points to `.claude/instructions/project-context.instructions.md`

### 5. Fill the Project State slot

`CLAUDE.md`, `AGENTS.md`, and the generated
`.claude/instructions/workspace.instructions.md` (its `workspace.md` alias
carries the same content) each carry a `## Project State` section with a
`**Project:** [TODO: project name and one-liner description]` fill-in slot.
That slot — and only that slot — is a designated per-project customization
point, not shared prose. Fill it with the one-liner plus a pointer to
`project-context.instructions.md`.

Where to make that edit depends on which repository this is:

- **This is the bootstrap authoring repository itself** (a `shared/policies/`
  directory exists): the slot's canonical source is
  `shared/policies/workspace.instructions.md`. Edit it there and regenerate
  with `uv run python scripts/generate_targets.py --all` — hand-editing the
  generated `.claude/instructions/workspace.md` /
  `workspace.instructions.md` directly is silently overwritten by the next
  regeneration.
- **This is an installed consumer project** (no `shared/policies/` present):
  the delivered `.claude/instructions/workspace.instructions.md` /
  `workspace.md` copies are the only copies this project has, so filling
  the slot there is the correct, durable action.

Remember: the root `CLAUDE.md`/`AGENTS.md` copies are gitignored, so editing
them directly is a local convenience only, not the durable record. Any
recurring project fact beyond this one-line slot belongs in
`project-context.instructions.md`, not in the generated workspace file.

### 6. Verify persistence

```bash
git -C .claude status --short   # confirm the .claude/ nested repo sees the changes
```

## Output

```
Onboarding refreshed:
  Read: README.md + docs/ ([N] files)
  Verified against code via: direct/rg reads ([N]), Semble ([N] queries)
  Findings: .claude/instructions/project-context.instructions.md
  MEMORY.md: [LEARN:domain] entry added/updated
  Project State slot filled: CLAUDE.md, AGENTS.md, workspace.md, workspace.instructions.md
  Mismatches found (docs vs code): [none | list]
```
