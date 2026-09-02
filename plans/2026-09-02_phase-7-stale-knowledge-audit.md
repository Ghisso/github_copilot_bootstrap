---
name: 2026-09-02_phase-7-stale-knowledge-audit
type: small-plan
parent_plan: verification-gate-semantic-hardening
phase_index: 7
status: complete
closeout_session_log: .claude/session_logs/2026-09-02_phase-7-stale-knowledge-audit.md
---

# Phase 7 — Stale Knowledge Audit

**Parent:** `verification-gate-semantic-hardening`
**Phase:** 7 of 7
**Primary objective:** bring the stale-claims rule to cover the memory index,
then audit every documentation surface, memory entry, and LEARN entry for
claims this plan or earlier work invalidated, correcting or superseding each.

## 1. Problem

### 1.1 The stale-claims rule does not cover memory

Big plan §3.7 obliges a phase that changes a documented fact to update
affected claims in active plans, `docs/`, `README.md`, and user-facing
workflow documentation. It says nothing about `.claude/MEMORY.md`.

That omission produced a measured failure inside this very plan. The phase 2
memory entry advised resolving a receipt's certified commit as "the first
entry of `git rev-list --ancestry-path --reverse`". Phase 4 proved that rule
accepts an unproven commit on a non-linear range and replaced it with
parentage-proof selection. The phase 4 correction was appended further down
the file, but nothing marked the phase 2 entry as superseded, so for three
phases the memory index carried live advice to reintroduce a defect the plan
had just removed. It was found only because the user asked whether the lesson
had been recorded.

`MEMORY.md` is loaded into context every session, which makes a wrong entry
more dangerous than a wrong sentence in a document nobody opens.

### 1.2 The memory index has accumulated stale content

Measured: `.claude/MEMORY.md` is 689 lines and names `quality_score.py`,
which Phase 1 deleted and which no longer exists anywhere on disk. The same
duplication problem also appeared — two entries recording one lesson at
different resolution, now consolidated by hand.

### 1.3 LEARN entries are spread across 74 immutable logs

Measured: 74 session logs hold 164 LEARN entries. At least ten of those logs
are bound by a closeout receipt's `closeout_log` artifact hash and are
therefore immutable under §3.6 — editing one breaks historical receipt
validation.

So a stale LEARN entry cannot simply be corrected in place, and the audit
needs an explicit rule for which surface gets which treatment.

### 1.4 The audit should be a standing step, not a one-off phase

This phase exists because staleness accumulated until someone noticed. Every
straggler found across phases 1–6 — the shipped skills still requiring a
deleted score report, five documents describing MAJOR as blocking only
push/PR, root `CLAUDE.md`'s "scoring", the superseded certified-commit rule
in memory — was found by an ad-hoc sweep that happened to look, not by a step
the lifecycle required.

A one-off audit fixes today's staleness and guarantees nothing about the next
plan. The durable fix is to make a documentation, memory, and LEARN audit a
required final step of every big plan, with recorded evidence.

## 2. Settled behavior

### 2.0 Make the audit a required final step of every big plan

Add the audit to the lifecycle contract so a future plan inherits it rather
than depending on someone asking:

- state it in the big plan's completion evidence, the lifecycle documentation
  in `shared/policies/workflow.instructions.md`, the orchestrator prompt, and
  `shared/templates/plan-big.md`;
- make `shared/skills/plan-decomposition/SKILL.md` produce plans whose final
  phase includes it, since that skill governs how every future plan is
  written — it is the leverage point that carries this forward.

**Gate the evidence, not the judgement.** Whether an audit was done *well* is
not deterministically checkable, and this plan's own §3.3 principle is that a
gate verifies a contract's shape rather than an agent's honesty. So require
what can be checked: the final phase's closeout log records which surfaces
were audited and the outcome for each. That is the same shape as the
DOCUMENT and LEARN evidence the commit gate already requires.

Decide deliberately whether to enforce that recorded evidence at the gate or
leave it as documented process. If enforcing, it must fail closed, must not
fire on a non-final phase, and must not become a second definition of "final
phase" that can drift from the big plan's own phase list. If that cannot be
met cleanly, keep it as documented process and say why — a documented step
the orchestrator follows is still a large improvement over nothing.

### 2.1 Extend the stale-claims rule to the memory index

Add `.claude/MEMORY.md` to §3.7's minimum surfaces, in the big plan and in
every shipped surface that states the rule — the documenter prompt at minimum.

State the distinction that makes the rule actionable: `MEMORY.md` is **live
advice** loaded every session, so a superseded entry must be corrected or
deleted, not merely followed by a newer entry elsewhere in the file. Appending
a correction without touching the wrong entry is what failed here.

### 2.2 Live advice is corrected; a dated record is left alone

The audit must not rewrite history. Classify each surface before touching it:

- **Live advice** — `CLAUDE.md`, `AGENTS.md`, `README.md`, `docs/` (except
  documents whose own frontmatter or heading dates them), `shared/policies/`,
  `shared/skills/`, `shared/templates/`, `shared/agents/`, and
  `.claude/MEMORY.md`. A claim here that is now false gets corrected or
  removed.
- **Dated record** — archived plans under `plans/`, dated design narratives
  such as `docs/plan-deterministic-commit-gate.md`'s D1–D5 section, and
  session logs. These record what was true at the time. Leave them, and do
  not add churn to them.

A session log is a dated record, so a merely-outdated LEARN entry there needs
nothing. Use a sibling `<log>.errata.md` per §3.6 **only** where an entry
would actively mislead a reader into reintroducing a defect — the phase 2
certified-commit entry is the model of that bar. Never edit a receipt-bound
log; verify immutability by checking whether a closeout receipt binds it
before considering any change.

### 2.3 Audit for a defined set of invalidated claims

Sweep every live-advice surface for claims this plan invalidated, at minimum:

- the deleted numeric quality score, `quality_score.py`, score thresholds,
  `gate: EXCELLENCE`, deductions, `## Score:`, and score report artifacts —
  including inflections a word-boundary grep for `score` misses, such as
  `scoring`, which is how root `CLAUDE.md` kept a stale line through three
  phases of sweeps;
- MAJOR blocking only push/PR rather than the phase-completion commit, and
  any statement of the findings contract omitting the MINOR
  disposition/reason requirement;
- `MEMORY.md` mtime as LEARN evidence;
- the superseded certified-commit resolution rule;
- `latest_report()` and timestamp-based findings discovery;
- typo-bypass breadth predating the path restriction;
- `mypy src/`, `ruff check src/ tests/`, and `uv sync` where the document
  governs the authoring repository;
- any named file, module, script, or flag that no longer exists — verify
  against disk rather than assuming.

Also sweep for claims invalidated by work predating this plan where the audit
happens to surface them. Do not limit the audit to this plan's own changes;
that narrower scope is what let earlier stragglers survive.

### 2.4 Record what was checked

The closeout session log must list every surface checked and the outcome, so
a future audit can tell a deliberate leave-alone from an oversight. A file
left unchanged needs a recorded reason.

### 2.5 A deterministic guard only if it is cheap and does not duplicate

§3.7 is process guidance, not a hook, and Phase 6 correctly declined a guard
that would have become a second drifting definition.

Consider one narrow, high-value check: that no live-advice surface names a
runtime file the generator no longer ships. Add it only if it is cheap,
cannot drift from the generator's own file list, and produces no false
positives on legitimate historical discussion. If it cannot meet that bar,
decline it and say why.

## 3. Non-goals

- Do not compress, reorganize, or shorten `MEMORY.md` for its own sake. This
  is a correctness audit, not a rewrite; remove an entry only when it is
  wrong, superseded, or duplicated.
- Do not edit any receipt-bound session log, or any dated record.
- Do not rewrite archived plans under `plans/`.
- Do not change any gate's behavior, strictness, or scope.
- Do not touch the certified-commit rule, the inactive-phase diagnostics, the
  typo-bypass exclusion, the LEARN evidence contract, the folded Ruff check,
  or receipt schema v4.
- Add no compatibility allowance.

## 4. Files to inspect and likely change

- `.claude/plans/verification-gate-semantic-hardening.md` §3.7
- `shared/agents/documenter/prompt.md`, and any other shipped surface stating
  the stale-claims rule
- `.claude/MEMORY.md`
- `CLAUDE.md`, `AGENTS.md`, `README.md`
- `docs/*.md`
- `shared/policies/*.md`, `shared/skills/*/SKILL.md`,
  `shared/templates/*.md`, `shared/agents/*/prompt.md`,
  `shared/review-profiles/*.md`, and the state README files
- errata siblings under `.claude/session_logs/` only where §2.2's bar is met

## 5. Implementation sequence

0. Make the audit a standing final step per §2.0, including the
   plan-decomposition skill and the evidence decision.
1. Extend §3.7 and the shipped rule statement, including the live-advice
   versus dated-record distinction.
2. Audit `.claude/MEMORY.md` entry by entry against §2.3, verifying every
   named path, module, and flag against disk.
3. Audit the remaining live-advice surfaces the same way.
4. Classify the session-log LEARN entries; write errata only where §2.2's bar
   is met, and only for logs no receipt binds.
5. Resolve §2.5.
6. Record the full checked-surface list for the closeout log.

## 6. Acceptance criteria

- [ ] a documentation, memory, and LEARN audit is a required final step of
      every big plan, stated in the lifecycle documentation, the orchestrator
      prompt, the big-plan template, and the plan-decomposition skill.
- [ ] the required evidence is a recorded surface list in the final phase's
      closeout log, and the decision to enforce it at the gate or leave it as
      documented process is recorded with its reasoning.
- [ ] §3.7 covers `.claude/MEMORY.md`, and states that a superseded entry is
      corrected rather than merely followed by a newer one.
- [ ] the shipped stale-claims rule states the same.
- [ ] no live-advice surface names the deleted score machinery, in any
      inflection.
- [ ] no live-advice surface states the superseded certified-commit rule,
      MAJOR-blocks-push-only, `MEMORY.md`-mtime LEARN evidence, or an
      authoring-repo command that cannot run.
- [ ] every file, module, script, and flag named as current in a live-advice
      surface exists on disk.
- [ ] no receipt-bound session log was modified; the receipt chain still
      validates across all seven phases.
- [ ] dated records are unchanged.
- [ ] the closeout log lists every surface checked, with a reason for each one
      left unchanged.
- [ ] the §2.5 guard decision is recorded.
- [ ] full repository tests and validation pass with no regeneration drift.

## 7. Completion evidence

Updated plan status, deterministic verification PASS, a findings report with
zero surviving findings or explicit dispositions, the closeout session log
under the immutable-log contract, generated-target parity, and the receipt
chain validated across all seven phases.
