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

## Review findings and dispositions

(pending)

## [LEARN] Entries

(pending)

## Verification

(pending: paste `verify closeout --format text` summary lines)

- optional: none declared in the plan.

## Open Questions / Next Steps

- Phase K follows: style section, rebaseline refresh, final stale-claims
  audit.
