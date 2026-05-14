---
name: deep-audit
description: |
  Repository-wide consistency audit. Runs 4 parallel checks: documentation
  accuracy, skill/rule consistency, and code-config alignment.
  Use periodically or before major releases. Trigger: "audit the repo".
---

# deep-audit — Repository Consistency Audit

## Four Parallel Audits

### Audit 1: Documentation Accuracy
- README claims match actual file structure
- Path references in docs point to existing files
- Code examples in docs still compile/run
- Version numbers consistent across files

### Audit 2: Instruction/Agent Quality
- All agents referenced in `copilot-instructions.md` exist in `.github/agents/`
- All skills referenced in `copilot-instructions.md` exist in `.github/skills/`
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

## Triage

1. Separate genuine bugs from false positives
2. Classify: Critical / Major / Minor
3. Fix critical issues immediately
4. Log major issues for follow-up

Max 5 fix-verify iterations.

## Report

```
Deep Audit Report -- [Date]

| Audit | Issues | Critical | Major | Minor |
|-------|--------|----------|-------|-------|
| Docs accuracy | N | N | N | N |
| Agent/skill quality | N | N | N | N |
| Reference consistency | N | N | N | N |
| Code-config | N | N | N | N |

[Detailed findings with file:line references]
```
