# Session: OpenWiki Phase J — docs and memory migration

**Date:** 2026-09-21
**Plan:** `.claude/plans/2026-09-19_phase-J-openwiki-docs-memory-migration.md`
**Status:** IN-PROGRESS

This is a transition phase, not the template for future knowledge-refresh
phases. It reduces duplicated descriptive documentation and memory content
only where the Phase I wiki proves adequate coverage; no OpenWiki refresh
runs here.

## Goal

After the user's confirmation, audit the generated wiki against `README.md`,
live `docs/**`, and `shared/MEMORY.md`; keep policy, security, ADRs,
operator instructions, README entry-point material, plans, logs, and
non-derivable memory under human ownership; shorten or remove only purely
descriptive duplicates that the wiki covers and grounds; update the brief
where the audit finds gaps.

## Work Log

- Phase started 2026-09-21 after Phase I's completion commit `40a9eb8`.
- Step J1, confirmation gate. The user inspected `openwiki/**` and wrote:
  "wiki seems fine, just not very nice alignment, and not really using
  lists, bullet points, or mermaid charts. can this be changed during
  generation or refresh?" and then: "ok add instructions for style in
  phase K. ... continue then". Content confirmed; the style request is a
  refresh concern and was recorded as Step K0 in the Phase K plan (a page
  style section in `openwiki/INSTRUCTIONS.md`, then a rebaseline refresh),
  not as a Phase J edit. Phase K's Optional Verification section now carries
  the Codex re-probe from Phase I.
- Step J2, read-only coverage audit (documenter). Surfaces: `README.md` by
  section, the six live docs, `shared/MEMORY.md` by entry, dated docs and
  root `plans/` by rule. Result: no REMOVE anywhere; no file goes away
  because OpenWiki exists. Dispositions:
  - KEEP: README entry-point, install and update runbooks, Main Philosophy,
    Architecture Flow diagram, Most Important Instructions and Skills
    (curated selection), How To Use, Customization Notes; all of
    `docs/runtime-checks.md`, `docs/smoke-tests.md`,
    `docs/native-client-acceptance.md`, `docs/plan-deterministic-commit-gate.md`
    (operator and QA contracts with exact constants, or decision records);
    in `docs/architecture.md` the Skill Library Validation Contract (cited as
    authority by `deep-audit`), Memory Authority and Privacy (anchor-linked
    as normative), OpenWiki Knowledge Layer (the authority boundary itself),
    Ponytail Integration (severity-gate policy), VS Code Tasks, Design
    Decisions; every `shared/MEMORY.md` entry (the Authority and Scope rule
    plus the OpenWiki caveat that prevents re-duplication, and empty
    category placeholders).
  - SHORTEN/LINK, each keeping a short paragraph plus a link to the named
    wiki page: README "Hooks" and "Deterministic Commit And Push Gates"
    (keep design-intent bullets and the `--no-verify` note; link
    `hooks-and-guardrails`), README "Agent System" (short roster table; link
    `agents-and-skills`), README "Task lanes" (four-row table; link
    `lifecycle-and-task-lanes`), README "What Is Included" and the
    "Generated layout" bullets (keep links; link
    `source-generated-consumer-layout` and
    `install-ownership-and-runtime-checks`), README Verification Defaults
    prose (keep the command list verbatim; link `deterministic-verification`);
    `docs/architecture.md` Source Directories and policy discovery, Hook
    Dispatcher and its three subsections, Task-Lane Routing prose (keep the
    diagram), Lifecycle Enforcement with reporting reminders and deterministic
    verification, Git-Backed State Sync (link the wiki page and ADR-002),
    Custom Agents; `docs/target-mapping.md` Shared Basis and Native Adapters.
  - KEEP + OPENWIKI GAP: README "Optional Retrieval Helpers". The Context
    Mode dispatcher's security model (cache quarantine by provenance secret,
    `CONTEXT_MODE_DIR` containment, the version-pin self-check) is covered by
    no wiki page. Phase K's brief gains this in its "Cover, at minimum" list.
  - Stale claims: none. No live doc links to the old `skills/openwiki` path
    or describes a runner or child process; "runner" occurrences refer to the
    native-client acceptance probe runner.
  - Proposed J3 edits, by value: (1) README Hooks + gates; (2) architecture
    Hook Dispatcher; (3) README Agent System; (4) architecture Custom Agents;
    (5) README Task lanes; (6) architecture Lifecycle Enforcement group;
    (7) architecture Git-Backed State Sync; (8) architecture Source
    Directories and target-mapping Shared Basis; (9) README What Is Included;
    (10) README Generated layout and target-mapping Native Adapters.
- Step J2 disposition review (reviewer; `documentation`, `architecture`,
  `security`; two passes). All ten edits approved, seven with conditions;
  advisory gate FAIL until the conditions are bound into J3. Conditions:
  1. `docs/target-mapping.md` Shared Basis must keep the exact link text
     `[Memory Authority and Privacy](architecture.md#memory-authority-and-privacy)`;
     `validate_targets.py` checks that literal substring (CRITICAL).
  2. README Hooks must keep the `## Hooks` heading literal (self-link at
     line 173), the design-intent bullets, the `--no-verify` note, and the
     sentences on `commit-msg` under `git merge`, `rebase`, `cherry-pick`,
     and `--amend` including the `MERGE_HEAD` passthrough escape; none are in
     the wiki.
  3. The Antigravity PreToolUse deny-by-default contract survives in
     `docs/architecture.md` Hook Dispatcher (both copies were slated for
     shortening).
  4. The per-agent model and effort matrix survives in `docs/architecture.md`
     Custom Agents; README Agent System keeps only a short roster table.
  5. `docs/architecture.md` Lifecycle Enforcement keeps verbatim the
     repository-scoped versus path-agnostic protection distinction for
     `protect-files.sh` and `git-protection.sh`, and the reporting-reminder
     183-byte / 200-byte ceiling sentence.
  6. The `~/.openwiki` pre-creation instruction and the `--cap-add=SYS_ADMIN`
     / `seccomp=unconfined` rationale survive in README What Is Included's
     devcontainer bullet; the copies at README "Generated layout" and
     `docs/architecture.md` Source Directories may go.
  7. Two SHORTEN/LINK targets omitted from the list are folded in as edits
     11 and 12: README Verification Defaults prose (command list stays
     verbatim) and `docs/architecture.md` Task-Lane Routing prose (diagram
     stays).
  Downgrade suggestions (VS Code Tasks, the Design Decisions closing
  paragraph) are deferred; over-preservation is the conservative direction.
- Step J3 (same documenter, no code changes): twelve shortening edits plus
  one brief bullet applied. `README.md` 976 -> 765 lines,
  `docs/architecture.md` 675 -> 446, `docs/target-mapping.md` 222 -> 93,
  `openwiki/INSTRUCTIONS.md` +1 bullet (Context Mode dispatcher security
  model under "Cover, at minimum"). Net 268 insertions, 820 deletions. Every
  condition sentence preserved: the exact Memory Authority link text in
  target-mapping; README `## Hooks` heading, design-intent bullets,
  `--no-verify` note, and the `githooks(5)` merge/rebase/cherry-pick/amend
  paragraph with the `MERGE_HEAD` passthrough; the Antigravity
  deny-by-default sentence; the repository-scoped versus path-agnostic
  protection sentence and the 183-byte / 200-byte sentence; the
  `~/.openwiki` pre-creation instruction and the `--cap-add=SYS_ADMIN` /
  `seccomp=unconfined` rationale in README What Is Included.
- Deviation found by the gate, not the plan: `validate_targets.py`'s
  `readme_agent_contract_errors` requires README itself to carry the literal
  `Universal agents:` and `Codex-only agents:` lists and exactly one
  `| Agent | Claude model | Claude effort | Codex model | Codex effort |`
  table matching every agent's `model_intent`. The first pass moved the
  matrix out of README and failed three checks; the documenter restored the
  lists and table in README's Agent System. The matrix therefore lives in
  both README and `docs/architecture.md` Custom Agents by necessity. Moving
  it out of README would need a validator change, a code change outside this
  documentation-only phase.
- VERIFY: `validate_targets.py` PASS (link integrity over README, AGENTS.md,
  docs), `check_runtime.py` PASS, `verify.py fast` PASS, `verify.py phase`
  PASS (ruff 0, mypy 0, pytest 1759 passed, `VFY-GEN-001` PASS).
- Step J4 review round 1 (`documentation`, `architecture`, `security`; two
  passes): 0 CRITICAL, 1 MAJOR, 0 MINOR. The MAJOR: `docs/architecture.md`
  Custom Agents claimed to be the "single surviving home" of the model and
  effort matrix while README still carried the table the validator requires.
  Fix applied by the orchestrator (a two-place wording change, no content
  moved): the architecture doc now says README carries the same table because
  `validate_targets.py` requires it there, that both are edited together, and
  that the validator rejects a README copy drifting from `model_intent`;
  README's closing pointer no longer sends readers to the architecture doc
  for the matrix. `validate_targets.py` PASS. All seven conditions were
  confirmed preserved; every new `openwiki/...` link and every pre-existing
  anchor resolves; two risky-looking removals (the Codex hook-trust
  reapproval step, the `luna_coder` escalation schema) were confirmed to
  live in other human docs or in the canonical prompts.

## Review findings and dispositions

(pending)

## [LEARN] Entries

- [LEARN:documentation] Before shortening a human doc against generated
  coverage, grep the validators for literal-text contracts on that doc.
  `validate_targets.py` hard-requires README's agent lists and model table
  (`readme_agent_contract_errors`) and target-mapping's Memory Authority
  link; a disposition that ignores those gates fails at verification, not
  at review.
- [LEARN:documentation] A disposition review must check what the wiki does
  not say, not only what it does. Seven sentences (escape hatches, a
  deny-by-default contract, a scope distinction, two exact constants, one
  operator setup step) existed only in the human docs; shortening all their
  copies in one phase would have left them nowhere. Name the surviving home
  for each before editing.

## Verification

(pending: paste `verify closeout --format text` summary lines)

- optional: none declared in the plan.

## Open Questions / Next Steps

- Phase K follows: style section, rebaseline refresh, final stale-claims
  audit.
