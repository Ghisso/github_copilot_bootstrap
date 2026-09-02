---
name: 2026-09-02_phase-6-canonical-command-parity
type: small-plan
parent_plan: verification-gate-semantic-hardening
phase_index: 6
status: in-progress
---

# Phase 6 — Canonical Command Parity

**Parent:** `verification-gate-semantic-hardening`
**Phase:** 6 of 6
**Primary objective:** make the documented verification commands match what the
gate actually runs, in both the authoring repository and installed consumers,
and close the formatting drift that the mismatch allowed.

## 1. Problem

Three separate mismatches, all measured.

### 1.1 The documented commands do not run in this repository

Root `CLAUDE.md` §Exact Commands, and the same block in
`workspace.instructions.md`, `workflow.instructions.md`,
`quality-and-testing.instructions.md`, `deployment.instructions.md`,
`code-standards.instructions.md`, `templates/plan-small.md`, and the
`code-style`, `refactor`, and `context-status` skills, all document:

```bash
uv run mypy src/ --ignore-missing-imports --explicit-package-bases
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

Measured in this repository: mypy exits 2 with `Cannot read file 'src'`, ruff
check exits 1, ruff format exits 2. There is no `src/` directory here.

Meanwhile `phase_checks` already selects the correct scope by inspecting the
repository: `["shared", "scripts", "tests"]` when
`is_bootstrap_authoring_repository(root)`, and `["."]` with `.claude`
excluded plus `consumer_mypy_targets(root)` otherwise. So the code has always
known the difference; only the documentation is wrong.

The consequence is concrete: a contributor following the documentation gets a
hard error, and one who reasonably substitutes `mypy scripts/` passes locally
while checking 8 of the 25 files the real gate checks.

### 1.2 `ruff format` is documented as required but never gated

`measure_ruff` runs only `ruff check`. No check anywhere runs
`ruff format --check`, yet it is documented as a required command.

The consequence is also concrete and current: `shared/scripts/verify.py` and
`tests/test_verify.py` — both edited repeatedly across phases 1–5 — are now
unformatted, alongside four files that were already unformatted on `dev`. Six
files total. Nothing caught it, because the documented requirement is not a
gate and the gate does not include the requirement.

### 1.3 `src/` is correct for consumers, so this is not a substitution

Most of the affected files ship into consumer projects, where a `src/` layout
is the template's own convention and the documented command is right. The fix
must therefore distinguish the authoring repository's scope from the consumer
template's, not replace one with the other.

## 2. Settled behavior

### 2.1 Prefer routing to the authority over duplicating its scope

This plan's design rule is that `verify.py` is the single deterministic
measurement authority, and §1's whole failure is a hardcoded duplicate of that
authority's scope drifting away from it.

So where a document's purpose is "here is how you verify this repository",
prefer pointing at the authoritative runner:

```bash
uv run python .claude/scripts/verify.py fast --format text     # during IMPLEMENT
uv run python .claude/scripts/verify.py phase --format text    # before REVIEW
```

`verify.py` selects the right scope for whichever repository it is in, so a
document that routes through it cannot drift from the gate.

Keep a raw tool command only where a reader genuinely needs to run one tool
directly. Where one is kept, it must be correct for the repository the
document governs.

### 2.2 Authoring scope must be stated where it applies

Root `CLAUDE.md` governs this repository. Its commands must be the ones that
actually work here and match `phase_checks`' authoring branch:

```bash
uv run pytest tests/ -q --tb=short
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
```

### 2.3 Consumer-facing documents keep the consumer shape

A shipped policy, skill, or template that a consumer reads about its own
project keeps `src/`, or routes through `verify.py`, whichever is clearer for
that document. Do not push authoring-repo paths into consumer guidance.

Where a shipped document is *also* installed into this repository's own
`.claude/` and would be wrong here, routing through `verify.py` per §2.1
resolves both at once. Prefer that over branching the prose.

### 2.4 Reconcile the formatting requirement with the gate

Documentation and gate must agree. Choose one and make it true:

- add a formatting check to the deterministic gate, so the documented
  requirement becomes real; or
- stop documenting `ruff format --check` as a required command.

Prefer the first: formatting is deterministic, trivially auto-fixed with
`uv run ruff format`, and already claimed as required. If the gate gains the
check, then:

- it must use the same scope selection as the other measurements, so it is
  correct in both authoring and consumer repositories;
- a tool that cannot be measured stays `UNVERIFIED` rather than passing;
- the mid-plan upgrade impact must be considered explicitly. A consumer that
  refreshes runtime mid-plan and has unformatted files would newly fail. The
  recovery is one command, but it must be documented where a consumer will
  find it, and the phase must state the impact rather than discover it later.

If the consumer impact is judged unacceptable, take the second option and say
why. Do not add the check and leave the impact unrecorded.

### 2.5 Close the existing formatting drift

Format the six files that are currently unformatted. Two of them
(`shared/scripts/verify.py`, `tests/test_verify.py`) drifted during this plan;
four predate it.

Formatting `verify.py` changes a generated runtime file, so regenerate targets
and confirm parity afterwards.

## 3. Non-goals

- Do not change any measurement's strictness, or what any check accepts.
- Do not replace `src/` in guidance a consumer reads about its own project.
- Do not add a flag, config, or environment variable to select scope; the
  repository-shape detection already exists.
- Do not reformat files by hand; use `uv run ruff format`.
- Do not touch the certified-commit rule, the inactive-phase diagnostics, the
  typo-bypass exclusion, the LEARN evidence contract, or receipt schema v4.
- Add no compatibility allowance.

## 4. Files to inspect and likely change

Authoring guidance:

- `CLAUDE.md`

Shipped guidance (each judged per §2.3):

- `shared/policies/workspace.instructions.md`, `workflow.instructions.md`,
  `quality-and-testing.instructions.md`, `deployment.instructions.md`,
  `code-standards.instructions.md`, `tests.instructions.md`
- `shared/templates/plan-small.md`
- `shared/skills/code-style/SKILL.md`, `refactor/SKILL.md`,
  `context-status/SKILL.md`, `setup-project/SKILL.md`,
  `create-feature/SKILL.md`, `domain-type-placement/SKILL.md`,
  `graph-schema-compat-migration/SKILL.md`

Runtime and validation:

- `shared/scripts/verify.py` — if §2.4 adds a check
- `scripts/validate_targets.py` — if a shipped-surface assertion is needed
- `tests/test_verify.py`

## 5. Implementation sequence

1. Fix root `CLAUDE.md` (§2.2) and confirm each documented command runs clean.
2. Sweep the shipped surfaces, deciding per document between routing through
   `verify.py` and keeping a correct consumer-shaped command. Record the
   judgement for any file left unchanged.
3. Resolve §2.4, failing-first if a gate check is added.
4. Format the six drifted files and regenerate targets.
5. Consider a guard so this cannot silently recur — for example asserting that
   no shipped canonical-command block names a scope the gate would not use.
   Add one only if it is cheap and does not duplicate the gate.

## 6. Acceptance criteria

- [ ] every command documented in root `CLAUDE.md` runs clean in this
      repository.
- [ ] no authoring-repo document instructs a scope the gate would not use.
- [ ] consumer-facing guidance still reads correctly for a `src/` project.
- [ ] documentation and gate agree about formatting, by whichever of §2.4's two
      options was chosen, with the choice recorded.
- [ ] if a formatting check was added, its scope selection matches the other
      measurements and its mid-plan consumer impact is documented.
- [ ] `uv run ruff format --check` is clean across the authoring scope.
- [ ] generated targets match canonical sources with no drift.
- [ ] full repository tests and validation pass.

## 7. Completion evidence

Updated plan status, deterministic verification PASS, a findings report with
zero surviving findings or explicit dispositions, the closeout session log
under the immutable-log contract, generated-target parity, and the receipt
chain validated across all six phases.
