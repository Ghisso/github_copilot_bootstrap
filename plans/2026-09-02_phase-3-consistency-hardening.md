---
name: consistency-hardening
type: small-plan
parent_plan: verification-gate-semantic-hardening
phase_index: 3
status: in-progress
---

# Phase 3 — Consistency, Immutable History, and Hardening

**Parent:** `verification-gate-semantic-hardening`  
**Phase:** 3 of 3  
**Primary objective:** align runtime and documentation, make session-log history immutable with explicit errata, constrain typo bypasses, and protect the final design with end-to-end regression coverage.

## 1. Session-log contract

### 1.1 Remove score-era requirements

The session log must not contain a required duplicated numeric quality score.

Do not reintroduce score consistency checks.

### 1.2 Require explicit LEARN structure

Reconcile the gate, README, and template around one contract.

Require the documented `## [LEARN] Entries` section.

The section must contain either:

- one or more explicit learning entries; or
- the exact sanctioned no-new-lessons marker.

Remove the `MEMORY.md` mtime shortcut as evidence of LEARN completion.

`MEMORY.md` can still be updated as a separate persistence action when useful. Its timestamp must not substitute for session-log evidence.

### 1.3 Closed logs are immutable

After closeout, a session log bound by a receipt must not be edited.

Historical artifact hash validation depends on byte stability.

Document this explicitly.

## 2. Errata model

Corrections to a closed session log must use a sibling file:

`<original-log-name>.errata.md`

Suggested minimal structure:

```markdown
# Errata for <original-log-name>

- YYYY-MM-DD
  - Supersedes: <short identification of stale claim>
  - Corrected conclusion: <new conclusion>
  - Evidence/reference: <later phase/log/doc>
```

Rules:

1. Never rewrite the original closed log.
2. An erratum created during an active phase is evidence of the discovering/correcting phase and may be bound by that phase's receipt.
3. The old receipt does not gain or change artifacts.
4. An erratum written outside an active plan can remain unbound.
5. A later phase may bind an existing unbound erratum if that phase reviews or changes it.
6. Do not invent a dedicated errata receipt workflow.

Errata is process guidance, not a semantic hook.

## 3. Conditional stale-claims review

Restore this explicit documenter responsibility.

When a phase changes a previously documented:

- fact;
- number/count;
- behavior;
- API;
- decision;
- conclusion;
- pipeline/runtime description;

the documenter must search likely affected sources and update or explicitly supersede stale claims.

Minimum surfaces:

- active/relevant plan files;
- `docs/`;
- `README.md`;
- workflow/policy documentation when relevant.

The phase/session log should record which document surfaces were checked when this rule triggers.

Do not run this sweep mechanically on every phase if no prior documented claim changed.

Do not attempt LLM or regex semantic enforcement in hooks.

## 4. Restrict commit-subject bypasses

Keep legitimate recovery/history behavior:

- `fixup!`
- `squash!`

Do not impose a crude diff line-count cap on these.

For typo bypasses such as:

- `docs(typo):`
- `chore(typo):`

restrict eligibility by changed paths and intended content class.

The exact allowlist must be based on current repo layout, but should be narrow enough that substantive runtime/code changes cannot hide under a typo subject.

Examples of likely eligible surfaces:

- Markdown documentation;
- non-runtime prose/config documentation where existing policy treats it as documentation-only.

Examples that must not qualify merely because of the subject:

- `shared/scripts/`;
- hook logic;
- generated runtime code;
- tests that change behavior;
- executable code.

Keep the existing bypass ledger/acknowledgement model unless current implementation proves it redundant.

## 5. Align every surface

Search and update all score-era, findings-era, session-log, receipt-chain, and frontmatter instructions.

Likely files:

- `README.md`
- `docs/runtime-checks.md`
- `docs/smoke-tests.md`
- architecture/lifecycle docs if they describe the old score
- `shared/agents/orchestrator/prompt.md`
- `shared/agents/reviewer/prompt.md`
- documenter instructions if present
- `shared/policies/workflow.instructions.md`
- `shared/policies/quality-and-testing.instructions.md`
- `shared/session_logs/README.md`
- `shared/templates/session-log.md`
- generated targets

Documentation must state:

- deterministic checks use PASS/FAIL, not a numeric score;
- MAJOR blocks only phase completion;
- MINOR disposition is audit acknowledgement, not trusted proof;
- plan-frontmatter validation is a hard runtime contract;
- cancellation evidence is commit-gated;
- every completed phase participates in historical receipt-chain validation;
- closed receipt-bound logs are immutable;
- corrections use sibling errata;
- conditional stale-claims review applies when later work invalidates documented claims.

## 6. Tests

Extend existing suites rather than creating a parallel hardening test framework.

At minimum:

### Session logs

- missing `[LEARN]` section -> closeout fail;
- exact no-lessons marker -> pass;
- MEMORY.md mtime alone -> does not satisfy LEARN;
- post-closeout mutation of historical log -> historical chain fail;
- sibling errata creation does not invalidate old receipt;
- discovering phase can bind errata evidence under the normal receipt mechanism.

### Bypass

- docs typo subject + allowed docs-only diff -> follows intended bypass path;
- docs typo subject + runtime/code path -> bypass rejected;
- chore typo subject + disallowed code path -> rejected;
- `fixup!` / `squash!` retain intended behavior;
- push/PR still requires final valid lifecycle evidence after bypassed commits.

### Surface parity

- generated targets contain no scorer or score-era instructions;
- shipped plan validator exists;
- generated runtime has consistent receipt/findings/session-log semantics;
- documentation parity checks remain green;
- regenerate produces no unexpected drift.

### End-to-end

Create or extend a throwaway-consumer lifecycle test covering:

1. plan starts;
2. implementation commits occur;
3. verification passes;
4. reviewer leaves a MINOR and dispositions it;
5. phase completion succeeds;
6. later phase closes;
7. push validates both historical and terminal receipts;
8. old session log mutation is rejected;
9. sibling errata preserves old receipt;
10. final PR/push gate passes only with the full chain valid.

Also preserve:

- paused-plan resume behavior;
- cancellation behavior;
- mid-plan upgrade behavior from Phase 1;
- git-hook/PreToolUse parity.

## 7. Files to inspect and likely change

Runtime/gates:

- `shared/scripts/verify.py`
- `shared/hooks/scripts/_lib-frontmatter.sh`
- commit/push gate callers as needed

Docs/templates/prompts:

- `README.md`
- `docs/runtime-checks.md`
- `docs/smoke-tests.md`
- `shared/agents/orchestrator/prompt.md`
- `shared/agents/reviewer/prompt.md`
- documenter agent instructions if present
- `shared/policies/workflow.instructions.md`
- `shared/policies/quality-and-testing.instructions.md`
- `shared/session_logs/README.md`
- `shared/templates/session-log.md`

Generation/validation:

- `scripts/generate_targets.py`
- `scripts/validate_targets.py` if surface parity needs adjustment

Tests:

- `tests/test_verify.py`
- `tests/test_hook_gates.py`
- `tests/test_lifecycle_hooks.py`
- `tests/test_validate_plan_frontmatter.py`
- `tests/test_validate_targets.py`

## 8. Acceptance criteria

Phase 3 is complete when:

- [ ] session-log contract no longer requires a score.
- [ ] `[LEARN]` section is enforced consistently by gate, README, and template.
- [ ] MEMORY.md mtime no longer satisfies session-log LEARN evidence.
- [ ] closed receipt-bound session logs are documented and tested as immutable.
- [ ] sibling `.errata.md` guidance exists.
- [ ] errata can be bound by the discovering phase without mutating the old receipt.
- [ ] unbound out-of-plan errata requires no special ceremony.
- [ ] conditional stale-claims review guidance covers plans, `docs/`, and `README.md`.
- [ ] typo bypass subjects are path-restricted.
- [ ] `fixup!` / `squash!` behavior is preserved.
- [ ] all canonical docs/prompts/policies/templates describe the same lifecycle.
- [ ] generated targets match canonical sources.
- [ ] end-to-end historical-chain lifecycle test passes.
- [ ] paused/cancelled/migration regressions remain green.
- [ ] no stale score-era strings or generated scorer files remain.
- [ ] full repo test and validation suite passes.

## 9. Final closeout sweep

Before marking the big plan complete:

1. search the repository for removed score-era terminology and files;
2. regenerate all targets;
3. run target validation;
4. run plan-frontmatter validation;
5. run the full test suite;
6. review `git diff` for generated/runtime parity;
7. perform the conditional stale-claims sweep for facts changed by this plan;
8. create the final session log under the new immutable-log contract;
9. verify the complete receipt chain once using the same path consumers use.

Do not mark the big plan complete if any compatibility allowance lacks an explicit removal condition.
