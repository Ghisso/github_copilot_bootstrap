---
name: deep-audit
visibility: public
description: |
  Repository-wide consistency audit. Runs 5 parallel checks: documentation
  accuracy, instruction/agent quality, skill/rule consistency, code-config
  alignment, and skill-library hygiene. Use periodically or before major
  releases. Trigger: "audit the repo".
---

# deep-audit — Repository Consistency Audit

Default behavior is audit and report: describe each finding and a proposed
fix, and let the user decide. Only change repository content when the user
explicitly asked for implementation (for example "audit and fix" or "audit
the repo, then implement the fixes") — a plain "audit the repo" request is
report-only.

## Five Parallel Audits

### Audit 1: Documentation Accuracy
- README claims match actual file structure
- Path references in docs point to existing files
- Code examples in docs still compile/run
- Version numbers consistent across files

### Audit 2: Instruction/Agent Quality
- All agents referenced in workspace guidance exist in `shared/agents/`
- Generated adapters point to canonical `.claude/agents/`
- All skills referenced in workspace guidance exist in `.claude/skills/`
- Cross-references are accurate
- Naming conventions are consistent

### Audit 3: Skill/Rule Consistency
- Skills reference agents that exist
- Instructions reference skills that exist
- No dead references or missing files
- `applyTo` globs match actual file structure

### Audit 4: Code-Config Alignment
- All ConfigStore fields are used in code
- No dead config fields
- Builder `from_config()` passes all fields
- Environment variables documented in `.env.example`

### Audit 5: Skill-Library Hygiene (Advisory)

These are semantic judgments, not deterministic facts, so they stay advisory
here rather than becoming hard lint. `scripts/validate_targets.py`'s
skill-integrity gate already fails closed on the objective, high-confidence
skill-library facts (frontmatter validity, `name`-matches-directory,
recognized `visibility`, non-empty and non-duplicate descriptions, a required
root `SKILL.md`, and broken local references to real repository paths); see
"Skill Library Validation Contract" in `docs/architecture.md`. Do not
re-flag any of those here as a Critical/Major finding — report a genuine hit
against one of the checks below instead, and never silently rewrite a skill
for it unless the user asked for implementation.

- **Suspiciously broad public trigger description.** A description that
  would route Codex, Claude, Gemini, or Copilot to load the skill for
  unrelated work. Exclude a description whose breadth matches a mandate the
  repository actually states. Worked example: `ponytail`'s "Use on ANY coding
  task" is accurate, not over-broad, because `CLAUDE.md` requires loading it
  in `full` mode before every coding task, and
  `shared/skills/ponytail/SKILL.md` makes its final diff review mandatory.
  Find the equivalent stated mandate before flagging any other description as
  too broad.
- **Duplicated normative policy.** A skill restates a canonical policy's
  rules instead of referencing `shared/policies/` or a generated
  `.claude/instructions/*.instructions.md` adapter. Prefer a reference over a
  restatement; flag the drift risk of the same rule living in two places.
- **Unconditional full-repository or full-document read.** Guidance that
  tells the agent to read an entire large tree or document up front instead
  of scoping to what the task actually needs.
- **Unqualified version-sensitive claim.** A framework or library behavior
  claim with no stated tested/observed version, and no instruction to check
  the installed API when versions may differ.
- **Project-specific benchmark or timing claim in shared guidance.**
  `shared/**` content is reused across projects and hardware; a concrete
  timing number belongs in project-specific context
  (`.claude/instructions/project-context.instructions.md`) or must be
  qualified as hardware- and workload-dependent.
- **Canonical-versus-generated ownership confusion.** Authoring guidance that
  points at a generated runtime path (for example `.claude/instructions/...`
  or `.claude/skills/...`) as though it were an editable source, instead of
  the canonical `shared/**` file that generates it.
- **Stale reference to a removed script, path, or lifecycle concept.** A
  reference to a command, path, or lifecycle stage that no longer exists or
  was superseded (for example a removed numeric-score workflow or a retired
  script name). The hard gate already rejects a broken *local reference to a
  real repository path*; this check instead catches a reference to a
  *concept or command* that no longer applies, which the hard gate cannot
  evaluate.

## Triage

1. Separate genuine bugs from false positives.
2. Classify each finding: Critical / Major / Minor.
3. Report every finding with file:line references and a proposed fix. Do not
   apply any fix unless the user explicitly asked for implementation.
4. If implementation was requested, fix Critical first, then Major, then
   Minor, and re-run this audit afterward to confirm the fix.

Max 5 fix-verify iterations when implementation was requested.

## Report

```
Deep Audit Report -- [Date]
Mode: audit-and-report (default) | fixes applied (user requested implementation)

| Audit | Issues | Critical | Major | Minor |
|-------|--------|----------|-------|-------|
| Docs accuracy | N | N | N | N |
| Agent/skill quality | N | N | N | N |
| Reference consistency | N | N | N | N |
| Code-config | N | N | N | N |
| Skill-library hygiene (advisory) | N | N/A | N/A | N |

[Detailed findings with file:line references]
```
