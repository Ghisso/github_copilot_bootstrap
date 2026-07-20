---
name: plan-decomposition
visibility: public
description: |
  Decompose a large implementation plan into a big plan plus one small-plan file
  per phase, matching templates/plan-small.md and the lifecycle the hooks
  enforce. Use when:
  - Creating a multi-step implementation plan for a feature or migration
  - User asks to "write a plan", "break this down into phases", or "plan this out"
  - A plan touches multiple files, configs, and test suites across >1 logical stage
  - Refactoring an existing monolithic plan into smaller, reviewable pieces
  Do NOT use for single-file fixes or tasks completable in one step.
---

# Plan Decomposition

Turn a large scope into one **big plan** (`templates/plan-big.md`) that lists its
phases, and one **small-plan file per phase** (`templates/plan-small.md`). This
is the single-file-per-phase model the lifecycle and `validate_plan_frontmatter.py`
enforce — there is no separate overview/detail split.

## One File Per Phase

Each phase is a single small-plan file carrying both the "what/why" and the
"exactly how":

- **Frontmatter** (validated): `name`, `type: small-plan`, `parent_plan`,
  `phase_index`, `status`, `closeout_session_log`.
- **Body**: a short plain-language Scope, the ordered Steps with enough
  precision for a coding agent, Verification commands, and the Closeout
  Checklist.

One file keeps stakeholder context and implementation detail in the same
reviewable unit and matches what the commit/PR gates read.

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

Name phases with letters (A, B, C, D) not numbers — avoids confusion with step
numbers inside each phase. Each phase gets a one-line goal statement.

### Step 2: Read Project Rules

Before writing any plan, read project instructions and relevant rules files. Extract:
- Naming conventions (file paths, class names, config patterns)
- Required tooling (pytest, mypy, ruff commands)
- Architecture patterns (config-first, builder pattern, etc.)
- Anti-patterns to avoid

Plans that ignore project conventions waste implementation time on rework.

### Step 3: Write the Big Plan

Use `templates/plan-big.md`. It carries the frontmatter the branch/PR gates read
(`type: big-plan`, `originating_branch`, `implementation_branch`, `phases`,
`current_phase`) plus Context, Goals, a Design Overview (Mermaid welcome here),
and the ordered `phases` list naming each small-plan slug.

**Location:**
- `.claude/plans/` — concrete implementation plans a coding agent will execute
- `.claude/explorations/YYYY-MM-DD_<project>/` — exploratory/PoC or research designs

### Step 4: Write One Small-Plan File Per Phase

Use `templates/plan-small.md`. Filename/slug follows `YYYY-MM-DD_phase-X-slug`
and must appear in the big plan's `phases` list. Fill:

- **Scope** — 2-4 sentences in plain language: what this phase changes and why
  (define acronyms; a Mermaid `flowchart TD`/`graph LR` is fine when it makes
  the change scannable).
- **Steps** — ordered, each precise enough to implement without dictating exact
  code. For each step name the target file (create|modify), the key
  function/class signatures (contracts, with type hints), the behavior and edge
  cases in prose, must/must-not constraints, and the test scenarios + verify
  command. Let the coding agent adapt bodies to the actual codebase.
- **Verification** — the exact commands (pytest, mypy, ruff, and the
  `quality_score.py` invocation with `--phase`/`--base-ref dev`/`--out`).
- **Closeout Checklist** — leave the template's checklist; it gates the commit.

### Step 5: Cross-Phase Consistency

After drafting all files, verify:
- File paths referenced in Phase B match what Phase A creates
- Class names, method signatures, and config field names are consistent
- No phase assumes something a previous phase doesn't create
- Read in `phases` order, the small plans tell a coherent story

### Step 6: Flag Unverified Assumptions

Any claim not empirically tested is marked explicitly — in Scope's risk notes or
inline `<!-- ASSUMPTION: ... needs empirical verification -->` comments. Never
state performance numbers, accuracy estimates, or library behavior as fact
unless verified against documentation or source with a link.
