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
lose. In a normal consumer project, `CLAUDE.md` and `AGENTS.md` at the
repo root are **gitignored, generated files** (confirm with `git
check-ignore -v CLAUDE.md AGENTS.md`). Edits there are local-only and do
not survive a fresh clone or the next bootstrap refresh. Where Git tracks
them, as in the bootstrap authoring repository, they are hand-maintained
files that the installer leaves untouched. The durable location for
project facts is the `.claude/` nested git repo (its own git history,
synced to the `ai-state` branch by session hooks).

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
- If `openwiki/INSTRUCTIONS.md` exists, treat OpenWiki's own entry/index page
  as optional just-in-time orientation — read it to get oriented, not every
  generated page at startup. It is derived, descriptive knowledge, never
  authority; see `.claude/instructions/workspace.instructions.md`'s
  Knowledge Ownership section. Verify any material implementation claim it
  makes against source and tests before editing, the same as any other doc
  claim in step 2. A repository without that marker uses this skill's
  existing targeted-retrieval steps unchanged.

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

This file is consumer state: a bootstrap refresh never overwrites it, so it
is safe to hand-edit and safe to re-run this skill against.

### 4. Add or refresh the MEMORY.md pointer

In `.claude/MEMORY.md` under `## Domain-Specific`, add or update a single
`[LEARN:domain]` entry that:
- One-line summarizes the project
- Flags any generic-template guidance that doesn't apply here
- Points to `.claude/instructions/project-context.instructions.md`

### 5. Place the project's one-line summary

The installer writes the target directory name into the generated
`**Project:**` line of root `CLAUDE.md`, root `AGENTS.md`,
`.claude/instructions/workspace.instructions.md`, and its `workspace.md`
alias. A refresh copies the generated files over the old ones and writes
the name again, so a hand edit to those copies is lost.

- Put the project's one-line summary, and every other recurring project
  fact, in `.claude/instructions/project-context.instructions.md` (step 3).
  Do not edit the generated `**Project:**` line.
- The exception is a root `CLAUDE.md` or `AGENTS.md` that Git tracks (the
  bootstrap authoring repository). The installer leaves that file
  untouched, so its `**Project:**` line is hand-maintained. Edit it
  directly there.
- Never fill the `**Project:** [TODO: project name and one-liner
  description]` placeholder in `shared/policies/workspace.instructions.md`.
  That file is the template every consumer receives, and the installer
  fills the placeholder.

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
  Project summary: .claude/instructions/project-context.instructions.md
  Mismatches found (docs vs code): [none | list]
```
