---
name: iterative-plan-review
description: |
  Run architecture-reviewer and code-reviewer agents in parallel on plan files,
  fix findings by severity (CRITICAL > MAJOR > minor), and iterate until both
  score 90+. Use when reviewing implementation plans before coding begins,
  or when user says "review the plan" or "run reviewers until they pass".
---

# iterative-plan-review — Plan Quality Gate

## Problem

Implementation plans with embedded code snippets and architecture decisions need
the same quality gates as production code. A single review pass misses issues that
only surface after fixes shift the design.

## Solution

### Step 1: Run dual reviewers in parallel

Launch `architecture-reviewer` and `code-reviewer` agents simultaneously on each
plan file in `.github/plans/`:

```
architecture-reviewer: Review [plan file] for separation of concerns, coupling,
  dependency direction, and design pattern correctness. Score out of 100.

code-reviewer: Review [plan file] for Python code quality in all code blocks:
  type hints, naming, imports, error handling, patterns. Score out of 100.
```

### Step 2: Triage findings by severity

Sort all findings across both reviewers:
1. **CRITICAL** (score < 80): Fix immediately, these block everything
2. **MAJOR** (score 80-89): Fix to reach PR threshold
3. **minor** (score 90+): Incorporate if straightforward

### Step 3: Apply fixes in severity order

- Fix all CRITICAL items first, then re-run reviewers (scores may shift)
- Fix MAJOR items, re-run reviewers
- Incorporate minor items directly without re-running (diminishing returns)

### Step 4: Convergence check

- Target: both reviewers score 90+ on all files
- Typical convergence: 3 rounds (R1: 72-82, R2: 86-92, R3: 91-94)
- Cap at 5 rounds to avoid infinite loops

## Key Pitfalls

- **`from __future__ import annotations` breaks Hydra/dataclass introspection** in Python 3.12+. Use native `X | None` instead.
- **Bulk rename creates double-prefix bugs**: check for already-partially-renamed instances before bulk replace.
- **Cross-file consistency**: renames in Plan A must propagate to Plans B/C.

## Verification

- Both architecture-reviewer and code-reviewer score 90+ on all plan files
- No CRITICAL or MAJOR items remain
- Cross-file references are consistent

## Example

```
Round 1: Arch 78/100, Code 72/100
  -> Fixed: missing task-type grouping, dead code, leaky abstractions
Round 2: Arch 88/100, Code 86/100
  -> Fixed: stale references, missing validation
Round 3: Arch 92/100, Code 94/100
  -> DONE: all plans pass 90+ threshold
```
