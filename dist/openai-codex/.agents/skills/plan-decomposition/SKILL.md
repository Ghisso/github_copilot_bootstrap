---
name: plan-decomposition
description: |
  Decompose large implementation plans into phased sub-plans, each with two files:
  an overview (plain language + Mermaid diagrams for stakeholders) and a detail
  spec (precise code, tests, and step ordering for a coding agent). Use when:
  - Creating a multi-step implementation plan for a feature or migration
  - User asks to "write a plan", "break this down into phases", or "plan this out"
  - A plan touches multiple files, configs, and test suites across >1 logical stage
  - User wants both a high-level summary and low-level coding instructions
  - Refactoring an existing monolithic plan into smaller, reviewable pieces
  Do NOT use for single-file fixes or tasks completable in one step.
---

# Plan Decomposition

Create phased implementation plans with dual audiences: stakeholders who need
the "what and why" and coding agents who need the "exactly how."

## Why Two Files Per Phase

A single plan file forces a choice: readable overview OR precise implementation
spec. Mixing both produces a document too vague for a coding agent and too dense
for a stakeholder. Splitting solves this:

- **Overview**: A PM, tech lead, or future-you skimming context can understand
  scope, dependencies, and risk in 2 minutes. Mermaid charts make architecture
  and data flow scannable without reading prose.
- **Detail**: A coding agent (or you next week) gets unambiguous instructions —
  file paths, module boundaries, function signatures, behavioral specs, constraints,
  and acceptance criteria — precise enough to implement without ambiguity, but
  without dictating exact code so the agent can adapt to the actual codebase state.

## When to Decompose

Split into phases when:
- The work has natural dependency stages (foundation before integration)
- Different phases need different verification criteria
- Any single phase would produce a plan >300 lines
- Partial delivery is valuable (Phase A works without Phase B)

A phase should be independently implementable and verifiable. If two steps must
happen atomically, they belong in the same phase.

## Process

### Step 1: Identify Phases

Read the full scope. Look for natural boundaries:
- **Foundation / scaffolding** — types, configs, pure functions (no external deps)
- **Integration** — wiring to external libraries, APIs, or models
- **Adaptation / training** — domain-specific tuning, fine-tuning, optimization
- **Validation / benchmarking** — end-to-end tests, accuracy measurement, docs

Name phases with letters (A, B, C, D) not numbers — avoids confusion with
step numbers inside each phase. Each phase gets a one-line goal statement.

### Step 2: Read Project Rules

Before writing any plan, read project instructions and relevant rules files. Extract:
- Naming conventions (file paths, class names, config patterns)
- Required tooling (pytest, mypy, ruff commands)
- Architecture patterns (config-first, builder pattern, etc.)
- Anti-patterns to avoid

Plans that ignore project conventions waste implementation time on rework.

### Step 3: Write Overview Files

**Filename pattern:** `YYYY-MM-DD_<project>-phase<X>-<slug>-overview.md`
**Location:** Depends on plan type:
- `.codex/plans/` — concrete implementation plans that a coding agent will execute immediately
- `.codex/explorations/YYYY-MM-DD_<project>/` — exploratory/PoC plans, feasibility analysis, research designs

Use `.codex/explorations/` when the plan is exploratory (proof-of-concept, feasibility study, research design).
Use `.codex/plans/` only when the plan is a direct coding spec ready for agent execution.

Structure:

```markdown
# Phase X: <Title>

**Goal:** One sentence.
**Depends on:** Phase(s) or "None"
**Produces:** What exists after this phase that didn't before.

---

## What This Phase Does

2-4 paragraphs in plain language. No jargon without definition.
Explain the WHY — what problem does this solve, what capability does it unlock.

## Architecture

Use Mermaid diagrams liberally. At minimum:
- A flowchart showing data/control flow for this phase
- A before/after if replacing existing functionality

## What Gets Built

Bullet list of deliverables with one-line descriptions.
NO code blocks. NO implementation details. Just outcomes.

## How We Know It Works

Plain-language verification criteria.
"When X happens, Y should result."

## Risks and Open Questions

Table format: Risk | Impact | Mitigation
Include items that NEED EMPIRICAL VERIFICATION — never state assumptions as facts.

## What Comes Next

One paragraph connecting to the next phase.
```

**Tone guidelines:**
- Write for someone who hasn't read the codebase in a month
- Define acronyms on first use
- Prefer concrete examples over abstract descriptions
- Use Mermaid `flowchart TD` or `graph LR` — avoid sequence diagrams unless
  modeling actual async message flow

### Step 4: Write Detail Files

**Filename pattern:** `YYYY-MM-DD_<project>-phase<X>-<slug>-detail.md`
**Location:** Same directory as overview.

Structure:

```markdown
# Phase X: <Title> — Implementation Detail

**For:** Coding agent / implementer
**Depends on:** Phase(s) + specific files from those phases
**Verification:** Exact commands to run after completion

---

## Prerequisites

Exact files/modules that must exist before starting.
Link to the phase that creates them if applicable.

## Steps

Number steps sequentially (X.1, X.2, ...).
Each step follows this template:

### Step X.N: <Action Verb> <Thing>

**File:** `src/path/to/file.py` (create | modify)
**Why:** One sentence explaining the purpose.

**Signatures:**
- Key function/class signatures with type hints (contracts, not bodies)

**Behavior:**
- What it does: takes X, validates Y, returns Z
- Edge cases: how to handle empty input, invalid state, etc.

**Constraints:**
- Must/must-not rules (e.g., "must not import from sibling layer")
- Performance or compatibility requirements

**Tests:** `tests/test_<thing>.py`
- List test scenarios as bullet points (happy path, error cases, edge cases)
- Specify key assertions, not full test code

**Verify:** `uv run pytest tests/test_<thing>.py -v`

## Files Created / Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/...` | Create | ... |

## ConfigStore Registration

(If applicable — exact cs.store() calls and where register function is called)

## Verification Checklist

- [ ] `uv run pytest tests/ -q` — all pass
- [ ] `uv run mypy src/ --ignore-missing-imports --explicit-package-bases` — clean
- [ ] `uv run ruff check src/ tests/` — zero violations
```

**Tone guidelines:**
- Be precise on contracts (signatures, types, constraints) but don't write implementations
- Include function/class signatures with type hints — these are the contracts
- Describe behavior and edge cases in prose, not code
- Specify field defaults, validator logic, and acceptance criteria
- When referencing existing code, include the file path and relevant context
- Let the coding agent handle implementation details — it can adapt to actual codebase state

### Step 5: Cross-Phase Consistency

After drafting all files, verify:
- File paths referenced in Phase B detail match what Phase A detail creates
- Class names, method signatures, and config field names are consistent
- No phase assumes something exists that a previous phase doesn't create
- The overview files tell a coherent story when read in sequence

### Step 6: Flag Unverified Assumptions

Any claim that hasn't been empirically tested gets marked explicitly:
- **In overview:** "Risks and Open Questions" table
- **In detail:** Inline `<!-- ASSUMPTION: ... needs empirical verification -->` comments

Never state performance numbers, accuracy estimates, or library behavior as fact
unless you've verified it against documentation or source code with a link.
