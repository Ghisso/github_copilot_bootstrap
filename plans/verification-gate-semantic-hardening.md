---
name: verification-gate-semantic-hardening
type: big-plan
status: complete
originating_branch: dev
implementation_branch: verification-gate-semantic-hardening_implementation
phases:
  - 2026-09-02_phase-1-verification-authority
  - 2026-09-02_phase-2-lifecycle-evidence
  - 2026-09-02_phase-3-consistency-hardening
  - 2026-09-02_phase-4-minor-findings-closure
  - 2026-09-02_phase-5-inactive-phase-diagnostics
  - 2026-09-02_phase-6-canonical-command-parity
  - 2026-09-02_phase-7-stale-knowledge-audit
started_at: 2026-09-02T01:16:25Z
current_phase: 
---

# Big Plan — Verification Gate Semantic Hardening

**Date:** 2026-09-02  
**Branch base:** `dev`  
**Implementation branch:** `verification-gate-semantic-hardening_implementation`  
**Scope:** bootstrap authoring repo only. Do not patch consumer repos directly.

## 1. Goal

Harden the verification and lifecycle gates so that deterministic checks are authoritative, review findings cannot silently survive phase completion, historical phase receipts form a verifiable chain, and documented workflow contracts match the runtime that consumers actually receive.

The main design rule is:

> Reduce agent-authored authority. Do not add metadata around claims that the verifier can derive itself.

This plan intentionally removes the 0–100 quality score instead of trying to make it more trustworthy.

## 2. Why this work is needed

PRs #26–#28 materially improved verification by adding fail-closed, receipt-based closeout evidence bound to the exact implementation state. The remaining gaps are semantic:

1. The quality score is still a separate artifact whose claimed value is not authoritative.
2. Open MAJOR findings can survive a phase-completion commit.
3. MINOR findings can survive without an explicit disposition.
4. The plan-frontmatter validator exists in the authoring repo but is not shipped and is not a hard consumer gate.
5. Session-log enforcement is weaker than the documented template.
6. Cancellation evidence is not enforced at the commit boundary.
7. Push/PR validation checks only the terminal completed phase receipt.
8. Historical receipts need ancestor-chain semantics instead of current-HEAD semantics.
9. Typo bypass subjects are broader than necessary.
10. Documentation can retain stale facts, counts, conclusions, and behavior descriptions after later phases invalidate them.

## 3. Settled design decisions

Do not re-litigate these during implementation unless current code makes one impossible.

### 3.1 Delete the authoritative quality score

Delete `quality_score.py` and remove the score artifact, score threshold, gate label, deductions, and `## Score:` session-log contract.

`verify.py phase` is the authority for deterministic measurements.

A phase-completion gate must require:

- required deterministic checks PASS;
- zero open CRITICAL findings;
- zero open MAJOR findings;
- every surviving MINOR finding has an explicit disposition and reason;
- required lifecycle evidence is valid.

Do not replace the deleted score with another numeric rubric.

### 3.2 MAJOR findings block only phase completion

Open MAJOR findings block the **phase-completion commit**.

They do not make arbitrary intermediate implementation commits impossible while a phase remains active.

CRITICAL findings remain blocking wherever the existing lifecycle already treats them as blocking.

### 3.3 MINOR dispositions are audit evidence, not trust evidence

A surviving MINOR finding requires an explicit disposition and reason.

The purpose is legibility and auditability, not proof that the agent's judgment is correct.

Do not add authority-implying fields such as signatures, `accepted_by`, HMAC-like metadata, or tool provenance.

### 3.4 Canonical per-phase findings artifacts

Prefer deterministic phase-named output such as:

`findings-<phase>.json`

Do not keep timestamp-based discovery or `latest_report()` behavior where it is no longer needed.

Git history already preserves prior versions.

### 3.5 Historical receipt chain semantics

Do not re-run the terminal current-state validation unchanged for every old phase.

**Corrected in Phase 2, per its own investigation:** a receipt is generated
*before* the completion commit it certifies (stage everything, generate
reports and the receipt, then commit), so a historical receipt's `head_sha`
is the *parent* of the commit it certifies, not that commit itself, and
`tree_sha` must equal that certified commit's tree — not
`git rev-parse <receipt-head>^{tree}`, which would check `head_sha`'s own
(parent) tree and always fail for a real lifecycle receipt. This is settled
Phase 2 behavior; do not revert to the equality this section originally
proposed.

**Refined in Phase 4, per its own investigation:** the certified commit is
not simply the first entry of `git rev-list --ancestry-path --reverse
<earlier_head>..<chain_head>`, because list position alone cannot tell a
linear implementation branch apart from one where `earlier_head` gained two
divergent, reconverging children. Selection instead queries that same
ancestry path with `--parents` and filters to the commit(s) whose own parent
set contains `earlier_head` — proof by parentage, not position — and fails
closed (records a chain error, produces no receipt) when that yields zero or
more than one candidate. Merges inside an implementation branch remain
unsupported: a well-formed range is assumed linear, and the fail-closed
branch is what catches a violation of that assumption instead of guessing.
This is settled Phase 4 behavior; do not revert to plain ancestry-path
position.

For each historical completed phase:

- receipt schema and required fields are valid;
- recorded receipt HEAD exists;
- the certified commit's tree (resolved via the ancestry path above) equals `tree_sha`;
- receipt HEAD is ordered correctly relative to neighboring phase receipts and is an ancestor of the pushed/current terminal HEAD;
- immutable receipt artifacts still hash-match;
- phase identity and plan identity remain consistent.

Only the terminal completed phase receives current-tree/current-runtime freshness checks.

Reuse the existing receipt reader, `head_relation == ancestor`, and `enforce_final_state` machinery. Extend it with historical-chain semantics instead of creating a parallel verifier.

### 3.6 Closed session logs are immutable

After a phase closes, its session log must remain byte-identical so historical receipt hashes stay valid.

Corrections use a sibling file:

`<session-log-name>.errata.md`

If an erratum is discovered during a later phase, that later phase can bind the errata file as its evidence. The original phase receipt remains unchanged.

An errata file created outside an active plan is allowed to remain unbound. A later phase may bind it if that phase reviews or changes it. Do not create a special receipt ceremony for unbound errata.

### 3.7 Stale-claims review is conditional process guidance

When a phase changes a previously documented fact, number, behavior, API, decision, or conclusion, the documenter must identify affected claims in:

- active/relevant plans;
- `docs/`;
- `README.md`;
- other user-facing workflow documentation;
- `.claude/MEMORY.md`.

Update or explicitly supersede those claims.

**Corrected in Phase 7:** `.claude/MEMORY.md` is live advice loaded into every
session, not a dated record. A superseded entry must be corrected or removed
in place; appending a correction elsewhere in the file while the wrong entry
still stands is not sufficient — a reader can act on the wrong entry before
ever reaching the correction, which is exactly the failure Phase 7's own audit
measured (the phase 2 certified-commit entry stayed live for three phases).
Archived plans, dated design narratives, and closed session logs remain dated
records: they describe what was true at the time and are left unchanged
except a sibling `<log-name>.errata.md` where an entry would actively
mislead a reader into reintroducing a defect and no closeout receipt binds
that log.

The conditional per-phase sweep above remains review guidance, not a
deterministic hook. Phase 7 additionally makes a documentation, memory, and
LEARN audit a **required final-phase step** of every big plan (see §10), and
that required evidence — a non-empty `## Stale-claims surfaces checked`
section in the final phase's closeout log — **is** gated, not merely
documented.

**Corrected during Phase 7's own review:** the first draft of this section
declined to gate the evidence, reasoning that any enforceable shape would be
a receipt/evidence-contract change and would risk a second, drifting
definition of "final phase" — citing the `CHECK_IDS` lesson from Phase 6 as
the analogy. That reasoning does not hold: `closeout_log_errors` (the
function that already gates the sibling `## [LEARN] Entries` evidence) has
exactly one caller (`gate_receipt_errors`), and `historical_chain_errors`
never calls it, so extending it touches no `CHECK_IDS` and can never be
re-evaluated against an already-closed historical receipt from phases 1–6.
"Final phase" needs no new definition either: `frontmatter_phases` already
reads the big plan's own `phases:` list elsewhere in this same file, and the
new `is_final_phase` helper reuses it directly (small plan `parent_plan` ->
big plan `phases:` -> compare against the last entry), so it cannot drift
from the big plan's own phase list. The gate therefore fires only when the
phase being closed out is that list's last entry, fails closed on any
unreadable or malformed frontmatter (treated as "not final," never as
"final"), and touches neither the receipt schema nor the LEARN evidence
contract next to it. Nothing in this plan's non-goals blocks it.

### 3.8 Schema migration must be safe mid-plan

The receipt change is expected to require schema v4 or equivalent.

A consumer refreshed while an existing implementation plan is in progress must not become unrecoverable.

Phase 1 must include explicit migration/compatibility behavior and regression coverage for supported mid-plan upgrade paths.

## 4. Required context before implementation

Read the current `dev` versions of these files before editing:

- `shared/scripts/verify.py`
- `shared/scripts/quality_score.py`
- `shared/scripts/record_findings.py`
- `shared/hooks/scripts/_lib-frontmatter.sh`
- `shared/hooks/scripts/enforce-commit-gate.sh`
- `shared/hooks/scripts/enforce-pr-gate.sh`
- `shared/hooks/git-hooks/commit-msg`
- `shared/hooks/git-hooks/pre-push`
- `scripts/generate_targets.py`
- `scripts/validate_plan_frontmatter.py`
- `scripts/check_runtime.py`
- `shared/agents/orchestrator/prompt.md`
- `shared/agents/reviewer/prompt.md`
- `shared/policies/workflow.instructions.md`
- `shared/policies/quality-and-testing.instructions.md`
- `shared/session_logs/README.md`
- `shared/templates/session-log.md`
- `README.md`
- `docs/runtime-checks.md`
- `docs/smoke-tests.md`
- relevant tests under `tests/`

Relocate code by symbol or behavior. Do not trust old line numbers.

## 5. Repository constraints

- `shared/` is canonical for generated consumer runtime.
- Any runtime check consumers need must be rendered by `scripts/generate_targets.py`.
- Do not hand-edit generated targets.
- Regenerate targets after canonical-source changes.
- Keep the fail-closed posture. A migration allowance must have an explicit scope and removal condition.
- Preserve PR #28 mid-plan upgrade safety.
- Preserve paused-plan semantics.
- Preserve one-phase/one-completion-commit lifecycle.
- Keep git-hook primary paths compatible with their current runtime assumptions.
- Tests must be failing-first for each changed invariant where practical.

## Phase

- `2026-09-02_phase-1-verification-authority` — remove the score authority, simplify closeout artifacts, add schema/migration support, and make `verify.py` the only deterministic measurement authority.
- `2026-09-02_phase-2-lifecycle-evidence` — harden findings, plan-frontmatter, cancellation, and all-phase historical receipt-chain enforcement.
- `2026-09-02_phase-3-consistency-hardening` — align session logs, errata/stale-claim guidance, bypass restrictions, generated surfaces, docs, and regression coverage.
- `2026-09-02_phase-4-minor-findings-closure` — fix the three MINOR findings that phases 2 and 3 closed with an accepted disposition.
- `2026-09-02_phase-5-inactive-phase-diagnostics` — report a clear diagnostic instead of a traceback when no phase is active, and correct the big-plan claim Phase 4 superseded.
- `2026-09-02_phase-6-canonical-command-parity` — make the documented verification commands match what the gate runs, in both the authoring repository and consumers, and close the formatting drift the mismatch allowed.
- `2026-09-02_phase-7-stale-knowledge-audit` — make a documentation, memory, and LEARN audit a required final step of every big plan, bring the stale-claims rule to cover the memory index, then run that audit over every live-advice surface.

### Why this plan grew to seven phases

Phases 1–3 delivered the plan's §7 global acceptance criteria in full, and the
plan reached `complete` on that basis. Three MINOR findings were carried out of
phases 2 and 3 as `disposition: accepted` with recorded reasons, which the
findings contract introduced by §3.3 permits. The user subsequently asked for
those findings to be fixed rather than accepted, so the dispositions are
withdrawn and Phase 4 resolves each on its merits. Phase 4 adds no new scope:
it closes recorded residuals of earlier phases, and its non-goals forbid
widening anything those phases established.

Phase 5 was added after Phase 4's closeout surfaced a pre-existing defect that
this plan's own lifecycle makes newly visible: with a big plan `complete` and
`current_phase` empty, every receipt-producing `verify.py` mode exits with an
unhandled traceback rather than a diagnostic. The affected provenance
functions are byte-identical to `dev`, so this is not a regression from
phases 1–4, but the window it occurs in is one every consumer reaches at the
end of every plan. Phase 5 also lands the §3.5 correction Phase 4 could not:
editing the plan after it closed invalidated the closeout receipt's bound plan
digest with no active phase left to regenerate against, so the correction had
to wait for an active phase to bind it.

Phase 6 was added after Phase 5's review surfaced that the verification
commands documented in root `CLAUDE.md` and across the shipped policies do not
run in this repository at all — there is no `src/` here — while
`phase_checks` has always selected the correct scope by inspecting the
repository shape. Investigating that turned up a second mismatch in the same
class: `ruff format --check` is documented as required but is not gated
anywhere, which is why two files this plan itself edited drifted unformatted
across five phases with nothing catching it. Both are §3.7 stale-claim
failures against the plan's own design rule that the verifier is the single
measurement authority, so a document duplicating its scope can only drift.

## 6. Phase boundaries

### Phase 1 — `verification-authority`

Primary outcome:

- no authoritative quality score remains;
- closeout uses deterministic verification results plus findings/lifecycle evidence;
- schema migration is safe for in-progress consumers.

Do not move historical all-phase validation into this phase except where schema compatibility requires shared primitives.

### Phase 2 — `lifecycle-evidence`

Primary outcome:

- phase completion cannot occur with open MAJOR findings;
- surviving MINOR findings are explicit;
- plan-frontmatter and cancellation evidence are hard gates;
- every completed phase participates in a valid historical receipt chain.

### Phase 3 — `consistency-hardening`

Primary outcome:

- docs/templates/runtime agree;
- closed logs are immutable and corrections use sibling errata;
- stale claims are actively reviewed when relevant;
- bypass behavior is constrained;
- end-to-end regression coverage protects all new invariants.

## 7. Global acceptance criteria

The big plan is complete only when all of the following are true:

1. `quality_score.py` no longer exists in canonical runtime or generated consumers.
2. No gate depends on a numeric quality score, score JSON, `gate: EXCELLENCE`, deductions, or `## Score:`.
3. `verify.py` reports deterministic measurement PASS/FAIL directly.
4. A phase-completion commit fails with an open MAJOR finding.
5. A non-completion intermediate commit is not blocked merely because the active phase still has an unresolved MAJOR finding.
6. A surviving MINOR finding without disposition/reason fails phase completion.
7. The shipped consumer runtime hard-validates plan frontmatter.
8. A cancelled plan lacking valid cancellation evidence cannot pass the relevant commit gate.
9. Push/PR validation covers every completed phase, not only the last one.
10. Historical receipts are validated using ancestor/tree/artifact-chain semantics.
11. Terminal-phase current-state freshness remains strict.
12. Mid-plan consumer upgrade from the supported v3 state to the new schema is tested and recoverable.
13. Closed session logs remain immutable after closeout.
14. Sibling errata files can carry corrections without invalidating old receipts.
15. Typo bypasses cannot be used for substantive non-documentation changes.
16. Documentation states the conditional stale-claims review rule.
17. Generated targets are deterministic and contain every shipped validator/check required by consumers.
18. Full repository validation and tests pass.

## 8. Test strategy

At minimum, add or update regression cases for:

- score artifact no longer required or accepted as authority;
- deleted scorer is absent from generated targets;
- phase verifier summary reports deterministic checks directly;
- open MAJOR blocks the phase-completion commit;
- the same MAJOR does not turn every in-progress commit into an impossible state;
- MINOR without disposition blocks completion;
- MINOR with disposition + reason passes the findings contract;
- missing `name` / `phase_index` or malformed plan inventory blocks consumer commit;
- cancellation without evidence blocks commit;
- historical receipt HEAD/tree validation;
- historical artifact hash mismatch;
- out-of-order receipt chain;
- historical receipt ancestor failure;
- terminal receipt current-state freshness;
- supported v3 -> v4 mid-plan upgrade;
- unsupported/unsafe schema state still fails closed;
- session log mutation after closeout breaks historical validation;
- sibling errata leaves the old receipt valid;
- path-restricted typo bypass;
- generation drift and target validation.

Use the existing test files where they own the behavior instead of creating parallel suites without need.

## 9. Out of scope

- Authentication/HMAC of agent-authored review findings.
- LLM-based truth checking of findings or stale documentation.
- New numeric quality or confidence scores.
- Automatic semantic detection of superseded conclusions.
- Editing consumer repos directly.
- Replacing the existing receipt architecture with a new provenance system.

## 10. Completion evidence

Each small plan must close with:

- updated plan status;
- deterministic verification PASS;
- valid findings/lifecycle evidence under the new contract available at that stage;
- session log;
- generated-target parity where runtime files changed;
- targeted regression evidence;
- full relevant test suite green.

The final phase must also run the repo-wide validation path and confirm no stale score-era instructions or generated files remain.

The final phase of **every** big plan — not only this one — must also run a
documentation, memory, and LEARN audit: sweep every live-advice surface for
claims this plan or earlier work invalidated, correct or supersede each one,
leave dated records unchanged, and record the audited surfaces and each
one's outcome under a `## Stale-claims surfaces checked` heading in the
closeout session log. This requirement is stated in
`shared/policies/workflow.instructions.md`, `shared/agents/orchestrator/prompt.md`,
`shared/templates/plan-big.md`, and `shared/skills/plan-decomposition/SKILL.md`
so every future big plan inherits it, and the recorded-evidence half of it is
gated: `verify.py`'s closeout check (`closeout_log_errors` /
`is_final_phase`) requires that exact heading, non-empty, whenever the
closing phase is the big plan's own last declared phase. See §3.7 for the
reasoning and why an earlier draft's decision to leave it ungated was wrong.
