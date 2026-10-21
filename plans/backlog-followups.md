---
name: backlog-followups
type: big-plan
status: in-progress
originating_branch: dev
implementation_branch: backlog-followups_implementation
started_at: 2026-10-20T14:54:11Z
phases:
  - 2026-10-20_phase-A-status-and-wording-cleanup
  - 2026-10-20_phase-B-nested-state-files
  - 2026-10-20_phase-C-memory-split
  - 2026-10-20_phase-D-agent-definition-protection
  - 2026-10-20_phase-E-ponytail-5-adoption
  - 2026-10-20_phase-F-openwiki-0.7-upgrade
  - 2026-10-20_phase-G-backlog-followups-knowledge-refresh
current_phase: 2026-10-20_phase-F-openwiki-0.7-upgrade
---

# Big Plan: Backlog Follow-ups

## Context

The `gate-repair` plan merged into `dev` as PR #46 (`f964551`). The
2026-10-17 audit (`.claude/explorations/2026-10-17_bootstrap-backlog-audit.md`,
§7) listed the next steps after it: the `MEMORY.md` split, Ponytail 5
adoption, and a behavioral evaluation retry. `gate-repair` itself recorded
more open follow-ups in `docs/target-mapping.md` ("Recorded follow-ups"),
the 2026-09-21 OpenWiki follow-up record is still open, and OpenWiki is two
minor versions behind. On 2026-10-20 the user asked for the ranked next
steps in one big plan.

Five read-only planning agents re-checked every item against `dev` at
`f964551` on 2026-10-20 and drafted one phase each. They confirmed the items
and found three new defects:

- An agent can delete or replace a whole hook folder (`rm -rf
  .claude/hooks`, `mv`, `ln -s`, `git -C .claude rm -r hooks`) with no guard
  decision (Phase D).
- The vendored Ponytail `LICENSE` is not byte-identical to upstream
  (Phase A).
- The guard scans heredoc bodies, so after Phase D any closeout command
  whose inline text names an agent folder is denied (Phase D documents the
  file-based route).

They also re-confirmed and re-rated two items of the 2026-09-21 record:
`verify closeout` crashes with a misleading traceback when the findings
report is missing (item 5, Phase A), and a bootstrap refresh deletes the
nested `.claude/.gitignore` and `.claude/.gitattributes` (item 6, rated LOW
there). The second is a security defect: lines a consumer added to
`.gitignore` are lost, and the installer's following `git add -A` can commit
and push files those lines ignored (Phase B).

An independent devil's-advocate review checked the assembled plan against
the code on 2026-10-20; its changes are folded in (see "Devil's advocate").

## Goals

- Make the AI-state records, root guidance, skills, and vendored license
  say what is true (Phase A).
- Stop refreshes from deleting consumer-owned nested Git files (Phase B).
- Cut the per-session cost of `.claude/MEMORY.md` without losing a lesson,
  and make `caveman-compress` backups survive a refresh (Phase C).
- Protect agent definition files and whole hook folders in all four clients,
  and drop the Codex agent setting that implies a guarantee Codex never
  applies (Phase D).
- Close audit gap A2 (no step checks callers, tests, fixtures, or config
  outside the diff) through a gated Ponytail 5 merge (Phase E).
- Move OpenWiki to `0.7.2` without weakening its guard, and harden the guard
  either way (Phase F).
- Finish with the required stale-claims audit and OpenWiki refresh
  (Phase G).

Work and verify clients in this order: Claude Code, Codex, GitHub Copilot,
Antigravity. Record each remaining gap with its evidence instead of
claiming parity.

## Non-Goals and Constraints

- No model call in tests, hooks, or `verify.py`. No network download in a
  required check. No new agent role, provider, or evaluation runner.
- Context Mode stays pinned at `1.0.169`.
- Releasing `dev` to `main` (`dev` is 273 commits ahead; `main` was last
  updated 2026-05-24) is the user's decision, not phase work.
- Native client runs (including the open Antigravity questions in
  `docs/target-mapping.md`) are optional host evidence, run by the user.
  Offline tests are the required evidence.
- Parked until a real need appears, unless the user decides otherwise
  (see "Decisions for the user"): the behavioral evaluation retry, the
  consumer CI template (`.claude/explorations/2026-09-08_consumer-ci-enforcement/`),
  Serena, ast-grep, Monty, and GLiClass.
- Carried without work, and kept in "Recorded follow-ups": protecting the
  parent folders `.claude`, `.github`, `.codex`, `.agents` (it would block
  the nested checkpoint `git -C .claude add -A`); protecting skill folders;
  wiring upstream's `antigravity-cli` Context Mode hooks; VS Code task tools
  such as `create_and_run_task`; the commit gate's five-profile rule not
  covering every multi-file diff; the Copilot SDK and CLI payload key
  casing.
- Dated records (closed session logs, archived plans, dated explorations
  and evidence docs) stay unchanged unless an entry actively misleads a
  reader. Under that exception, Phase A changes status lines and plan
  status fields and adds Resolution notes, and Phase C changes the
  2026-09-03 exploration's status line and adds one Outcome line.

## Design Overview

### Phase order

| Phase | Why here |
| --- | --- |
| A. Status and wording cleanup | Small, and its `verify closeout` fix helps every later closeout |
| B. Nested state files | Security fix: a refresh can commit and push files a consumer ignored. Every later phase refreshes the installed copy |
| C. Memory split | Lowers the session cost for the rest of the plan; independent of B for correctness. Split not applied after the step 1 stop condition (user decision 2026-10-20); only the `caveman-compress` fix and the measurement ship |
| D. Agent definition protection | Security gap. After D, commands that name an agent file or protected folder outside the read-only list are denied, so later phases use `cat`, `rg --files`, `git diff --no-index`, `check_runtime.py`, and file-based findings and PR bodies |
| E. Ponytail 5 | Evaluation-gated; may cancel. Edits `shared/agents/` (source), which D leaves editable |
| F. OpenWiki 0.7 | Spike-gated; may stop at `0.5.2` or cancel. Runs last before G, so G's refresh uses the new version |
| G. Knowledge refresh | Required final phase (Knowledge-Refresh Final Phase rule) |

### Gates that can stop or cancel a phase

- **C, step 1:** if the classified archive holds less than 25% of the entry
  bytes, stop and ask the user whether to accept the smaller cut. Hit on
  2026-10-20 (6.11%); the user chose not to split.
- **E, step 1:** a recorded comparison decides ADOPT, PARTIAL ADOPT, or
  NO-GO. NO-GO cancels Phase E with evidence (E step 2); no outer commit.
- **F, steps 1 and 4:** an isolated `0.7.2` spike (scratch folder, no
  network for the probes, temporary `HOME`) must pass eight stop conditions,
  and the live install must leave the root MCP adapters unchanged. On a stop,
  keep `0.5.2` and ask the user: finish at `0.5.2` with the guard hardening
  and round-trip test only, cancel Phase F with evidence (F step 7), or
  re-plan the guard.

A phase cancelled while it is current never certifies a commit. Its cancel
step advances `current_phase` to the next phase by hand, as
`shared/hooks/scripts/_lib-frontmatter.sh:1425` instructs, flips that phase
to `in-progress`, ticks and annotates the cancelled entry in `## Phases`,
and runs `uv run python scripts/validate_plan_frontmatter.py`.

### Parity table

Phase D creates a `## Backlog-Followups Client Parity` table in
`docs/target-mapping.md`, after the gate-repair table and with its columns.
Later phases add a row only for a client-visible change. Phase G checks the
table against the shipped state.

### Hand-offs between phases

- Phase A hands item 6 of the 2026-09-21 OpenWiki follow-ups to Phase B,
  item 7 (Codex guard re-probe) to Phase F as optional evidence, and item 2
  (a generated quickstart row) to Phase G.
- Phases D and E name the generated OpenWiki pages Phase G must refresh.
- Phase E's NO-GO path hands audit gap A2 to Phase G's "Recorded
  follow-ups" update.
- Phase C did not split `MEMORY.md` (user decision 2026-10-20), so later
  phases correct superseded `[LEARN]` entries in place, as the workflow's
  live-advice rule requires.

### Decisive assumptions

| Assumption | Status | Evidence or remaining limit |
| --- | --- | --- |
| A plan can be marked `complete` without inventing a missing closeout log | Settled | `scripts/validate_plan_frontmatter.py:387-388,660-661`; `.claude/plans/README.md` defines `complete` as "the authorized work shipped" |
| A refresh deletes the nested `.gitignore` and `.gitattributes`, and consumer `.gitignore` lines are lost | Settled from code; not run end to end | `scripts/install_bootstrap.py:573-627`; `state-sync.sh:90-111`. Phase B's test must fail on the current code first |
| No gate reads `MEMORY.md` entry content | Settled | LEARN evidence comes from the closeout log only (`shared/scripts/verify.py:2594-2650`) |
| Files under `.claude/explorations/` survive a refresh | Settled | `scripts/runtime_ownership.py:45`; `validate_targets.py` repeat-install check |
| No agent tool call legitimately writes an installed agent folder | Settled | Installer and sidecar write from Python; consumers customize only project context and state |
| Claude Code's native `.claude` protection does not make the agent-folder hook redundant | Documented, not run here | Native protection reaches only the classifier in `auto` and is off in `bypassPermissions`; a hook `ask` forces a prompt in `auto` (Claude Code docs, read 2026-10-20) |
| Unmodelled mutating Git subcommands resolve path tokens against the repository root only | Settled by probe | `protect-files.py:1309-1337`; `git -C .claude rm -r -q hooks` gets no decision today |
| Codex ignores `sandbox_mode` in a custom agent file | Documented, not run here | Codex subagents docs, read 2026-10-20 |
| A `.code-workspace` file can turn Copilot hooks off | Docs plus pinned VS Code source | Same evidence tier gate-repair Phase D accepted for `.vscode/settings.json` |
| Ponytail 5's A2 rules live in the skill text, not the plugin runtime | Settled | `v5.3.2` skill text never refers to the codebase-map hook |
| Upstream Ponytail's `LICENSE` is the same at `v4.8.4` and `v5.3.2` | Settled | Same blob `715d483`, sha256 `fb1bc690…` at both tags |
| OpenWiki `0.7.2` keeps everything the guard reads and does not rewrite the root MCP adapters on install | Static diff; observed only at `0.5.2` | Phase F step 1 observes `0.7.2`, including an isolated integration install, before any pin change |

## Requirement Map

IDs are prose references for this plan only. Each small plan states the
full acceptance text; this map is the index.

| Requirement | Acceptance (summary) | Owning phase | Evidence |
| --- | --- | --- | --- |
| BF-A1 | July big plans `codex-gpt-5.6-model-tiering` and `preserve-consumer-memory` and their phases read `complete` with a Resolution note naming PR #7 and PR #8; their BLOCKED logs stay unchanged; the pilot plan's Phase D is ticked; three dated explorations get a closed status line only. The July-plan lint test keeps testing the date gate | `2026-10-20_phase-A-status-and-wording-cleanup` | `validate_plan_frontmatter.py`; grep items; reviewer read of the nested diff |
| BF-A2 | One OpenWiki sentence in the generator, `CLAUDE.md`, `AGENTS.md`, and generated copies | same | `validate_targets.py`; grep items |
| BF-A3 | No undefined "transition scope" in the knowledge-refresh rule; no prose em dash in `openwiki/INSTRUCTIONS.md` | same | grep items |
| BF-A4 | `onboard`, `setup-project`, and `create-feature` give correct project-name advice: the installer fills the generated line; the summary goes in `project-context.instructions.md`; the template placeholder is never filled | same | grep items; `validate_targets.py` install run |
| BF-A5 | `verify closeout` with a missing findings report, phase receipt, or closeout log exits 2 with one line naming the path and the step that creates it; no traceback, no receipt | same | new `tests/test_verify.py` cases |
| BF-A6 | Every 2026-09-21 OpenWiki follow-up has a written outcome: 1, 3, 4, 5 fixed in A; 8 already resolved; 6 to B, 7 to F, 2 to G | same (recording) | exploration status line; closeout log |
| BF-A7 | The vendored Ponytail `LICENSE` is byte-identical to upstream (sha256 `fb1bc690…`), with its pin moved in `UPSTREAM.md` and `scripts/validate_targets.py` | same | `sha256sum -c` item; `validate_targets.py` |
| BF-B1 | A refresh never deletes or rewrites the nested `.gitignore` or `.gitattributes` (both join `CONSUMER_STATE_PATHS`); `write_nested_gitignore` adds `settings.local.json` when missing, so the installer's `git add -A` never commits local settings | `2026-10-20_phase-B-nested-state-files` | `tests/test_install_bootstrap.py` (fails first on current code); `tests/test_state_sync.py`; `validate_targets.py` repeat-install fixture built from the temporary install; `git -C .claude ls-files` after the refresh |
| BF-B2 | Existing nested repositories gain `session_logs/*.log merge=union` when missing; user lines are kept; repeat runs change nothing | same | `tests/test_state_sync.py` |
| BF-C1 | Dropped by the 2026-10-20 scope change: the split was not applied, so `MEMORY.md` keeps every entry | `2026-10-20_phase-C-memory-split` | scope-change record in the small plan |
| BF-C2 | Delivered as evidence: one classification row per entry (18 `ARCHIVE`, 310 `KEEP`, 6.11% of entry bytes); the 25% stop condition fired and the user decided not to split | same | the table kept beside the 2026-09-03 exploration; session log |
| BF-C3 | Dropped with BF-C1 (no split, so nothing to break) | same | scope-change record |
| BF-C4 | `caveman-compress` writes its backup at a `Backup:` path a refresh cannot delete; sidecar output still passes its forbidden-token scan | same | `tests/test_caveman_compress_detect.py`; `validate_targets.py` |
| BF-C5 | The 2026-09-03 exploration's status says decided, with one outcome line naming the measurement and the decision | same | reviewer diff |
| BF-D1 | An agent write to `.claude/agents/`, `.codex/agents/`, `.github/agents/`, or `.agents/agents/` asks on Claude Code and Copilot and is denied on Codex and Antigravity; reads, `shared/agents/`, foreign checkouts, and the installer stay allowed | `2026-10-20_phase-D-agent-definition-protection` | `tests/test_hook_gates.py`; `tests/test_protect_files_scoping.py`; installed-hook smoke |
| BF-D2 | The three hook folders and four agent folders are protected as whole folders (`rm -rf`, `mv`, `ln -s`, interpreter removal, `cd` then remove, and unmodelled Git subcommands under `git -C`); parent folders stay unprotected | same | folder cases with a recorded negative control |
| BF-D3 | `*.code-workspace` files in the repository get the hook-config decision | same | scoping and hook tests |
| BF-D4 | Generated Codex agent files carry no `sandbox_mode`, and the validator rejects it | same | `test_validate_agents_rejects_codex_agent_local_override[sandbox_mode]` |
| BF-D5 | `docs/target-mapping.md` gets the new parity table, the remaining gaps, and `.claude/hooks/` in the gate-repair row; smoke tests, runtime checks, README, File Protection Rules, and the commit skill describe the behavior and the file-based recovery (`--findings-json <file>`, `--body-file <file>`) | same | `documentation` review |
| BF-E1 | A recorded comparison of Ponytail `v5.3.2` with the `v4.8.4` baseline and the local fork answers Q1–Q5 and states ADOPT, PARTIAL ADOPT, or NO-GO under fixed decision and stop rules | `2026-10-20_phase-E-ponytail-5-adoption` | `.claude/explorations/2026-10-20_ponytail-5-evaluation/evidence.md` |
| BF-E2 | NO-GO cancels Phase E with evidence and advances `current_phase` to Phase F; A2 goes to Phase G's follow-ups | same | evidence file; plan validator |
| BF-E3 | Coder side of A2: the merged `ponytail` skill, both coder prompts, and the workspace rule map callers, tests, fixtures, and config before writing; every fork safety item stays | same | guidance rows; hash pin |
| BF-E4 | Review side of A2: `ponytail-review`, both reviewer prompts, and the `code` profile read touched code, not only the diff; `ponytail-review` stays complexity-only unless the user decides otherwise | same | guidance rows; hash pin |
| BF-E5 | `UPSTREAM.md` names `v5.3.2` with a merge record and the full pin checklist; every skill pin moved | same | `validate_targets.py`; pytest |
| BF-E6 | Both sidecar profiles stay consistent; a new test proves every `SIDECAR_TEXT_REPLACEMENTS` anchor still matches | same | new anchor test; sidecar tests |
| BF-E7 | `ponytail-audit` and all plugin runtime stay unvendored; no new public skill, hook, or dependency | same | not-vendored list; skill-count check |
| BF-F1 | `openwiki@0.7.2` is observed in isolation before any pin change, including an isolated integration install against copies of the root MCP adapters; the stop rule decides go, finish at `0.5.2`, or cancel | `2026-10-20_phase-F-openwiki-0.7-upgrade` | capture table in the session log |
| BF-F2 | The live upgrade rule is restated in `docs/runtime-checks.md` and `knowledge-refresh` before the pin moves | same | docs diff |
| BF-F3 | The pin is `0.7.2` in `shared/devcontainer/Dockerfile` and `OPENWIKI_PINNED_VERSION` | same | `validate_targets.py`; `check_runtime.py` |
| BF-F4 | Real-binary tests never skip or download: handshake with the exact tool set and `openwiki_begin` schema, and a guard round trip that leaves both adapters byte-identical | same | `tests/test_openwiki_cli_smoke.py` |
| BF-F5 | The guard denies any `openwiki_begin` mode other than `update`, including a missing mode | same | `tests/test_openwiki_guard.py` |
| BF-F6 | OpenWiki's read-only tools are routed as optional just-in-time derived context; other OpenWiki host integrations are never installed here | same | docs diff; sidecar token check |
| BF-F7 | This checkout runs `0.7.2` (user-run install), both installed skill receipts read `0.7.2`, root MCP adapters unchanged, rollback recorded | same, used by Phase G | session log; smoke test |
| BF-G1 | Final stale-claims audit across all live-advice surfaces and the working `MEMORY.md` (the archive stays a dated record); the carried follow-ups stay listed; OpenWiki refresh including the hand-offs from A, D, E, and the two `gate-repair` leftovers | `2026-10-20_phase-G-backlog-followups-knowledge-refresh` | `## Stale-claims surfaces checked`; OpenWiki completion; `test ! -e openwiki/.run.json` |
| BF-G2 | Boundaries held: no model call in tests, hooks, or `verify.py`; no network download in required checks; Context Mode still `1.0.169`; dated records unchanged except the status changes Phases A and C name | all phases | review and existing tests |

## Phases

- [x] `2026-10-20_phase-A-status-and-wording-cleanup` — complete: stale statuses closed, one OpenWiki sentence, project-name advice in three skills, clean `verify closeout` message for missing evidence, verbatim Ponytail license. See `.claude/session_logs/2026-10-20_backlog-followups-phase-a.md`.
- [x] `2026-10-20_phase-B-nested-state-files` — complete: a refresh keeps the nested `.gitignore` and `.gitattributes`; `state-sync.sh` appends `settings.local.json` and the union-merge rule only when missing. See `.claude/session_logs/2026-10-20_backlog-followups-phase-b.md`.
- [x] `2026-10-20_phase-C-memory-split` — complete: `caveman-compress` backups now land where a refresh keeps them; the `MEMORY.md` split was measured (6.11%) and not applied by user decision. See `.claude/session_logs/2026-10-20_backlog-followups-phase-c.md`.
- [x] `2026-10-20_phase-D-agent-definition-protection` — complete: agent folders, whole hook folders, and workspace files protected; the guard fails closed on uncertain hits and secret-shaped targets (decision 6); Codex `sandbox_mode` removed. See `.claude/session_logs/2026-10-21_backlog-followups-phase-d.md`.
- [x] `2026-10-20_phase-E-ponytail-5-adoption` — complete: partial adopt of Ponytail `v5.3.2` (callers, tests, fixtures, and config outside the diff for the coder and the review); `ponytail-review` stays complexity-only. See `.claude/session_logs/2026-10-21_backlog-followups-phase-e.md`.
- [x] `2026-10-20_phase-F-openwiki-0.7-upgrade` — complete: OpenWiki pinned to `0.7.2` after an isolated spike; the guard allows only `mode: "update"`; real-binary round-trip test; upgrade procedure documented. See `.claude/session_logs/2026-10-21_backlog-followups-phase-f.md`.
- [ ] `2026-10-20_phase-G-backlog-followups-knowledge-refresh` — final stale-claims audit and OpenWiki refresh

## Ownership and Required Skills

The main-thread orchestrator owns activation, AI-state writes under
`.claude/` (Claude Code treats that folder as sensitive, so background
subagents cannot get write approval there), the self-install refresh,
closeout, commits, and pushes. A coder owns code and tests; a fresh
reviewer reviews each phase; a documenter updates live docs after review.
The user runs the Phase F environment upgrade (`npm install -g` and the two
`openwiki integrations install` commands) and any self-install refresh the
auto-mode classifier denies. Every coding step loads
`shared/skills/ponytail/SKILL.md` (full) plus the skills each small plan
lists. Every phase uses the `code`, `architecture`, `security`, `tests`, and
`ponytail` review profiles, plus `documentation` where docs change.

## Test Strategy

- **Critical cases:** a refresh keeps consumer `.gitignore` lines and never
  commits local settings; the memory split is lossless; agent-folder and
  whole-folder edits (including `git -C` forms) get the client's decision;
  the OpenWiki guard round trip restores both adapters byte for byte on the
  real pinned binary; `verify closeout` reports a missing artifact without
  a traceback.
- **Negative controls:** each new protection case fails on the unchanged
  guard; the nested-file test fails on the current installer;
  `split_memory.py selftest` catches four kinds of tampering; the license
  and skill pins report a hash mismatch on a changed byte; reads, `shared/`
  sources, foreign checkouts, and the installer stay allowed.
- **Real integration:** the self-install refresh in every phase; the
  installed-hook smoke in `validate_targets.py`; the real OpenWiki binary in
  Phase F.
- **Mocked boundaries:** temporary Git repositories, the existing hook-test
  harnesses, synthetic repositories for the OpenWiki spike.
- **Independent expected values:** from policy tables, upstream sources, and
  the evidence files, never from the implementation.
- **No available verification:** whether models follow the new Ponytail
  text (optional spot-check only); native Antigravity enforcement; Copilot
  behavior inside VS Code. Docs must say so.

## Risks and Dependencies

- **Size and waiting.** Seven phases, one branch, one PR. Each phase is one
  commit and can be reviewed alone. Phases E and F can wait on the user (a
  scope question, a user-run install, a new session). When one stalls, the
  orchestrator offers to cancel it with evidence so B and D are not held
  back, then runs G.
- **Line numbers move.** Each small plan cites lines from `f964551`.
  Implementers re-read the current file before editing.
- **New protections apply to the orchestrator.** After Phase D, commands
  that name an agent file or protected folder outside the read-only list,
  including heredoc text, are denied on every client. Write findings JSON,
  PR bodies, and session-log additions that name such a path with the
  native Write or Edit tool, and pass `--findings-json <file>` or
  `gh pr create --body-file <file>`. PR titles must not name protected
  paths.
- **Environment coupling.** After Phase F's pin bump, any checkout without
  OpenWiki `0.7.2` on `PATH` fails `verify phase`, and the global `0.7.2`
  install breaks the smoke test in any other checkout still pinned to
  `0.5.2`. Phase G starts in a new session so the OpenWiki server runs
  `0.7.2`.
- **Auto-mode classifier.** It has denied the self-install refresh before;
  the orchestrator then hands that one command to the user.

### Devil's advocate

Independent review on 2026-10-20 (separate read-only subagent, Opus,
extra-high effort, devils-advocate skill). Outcome:

| Concern | Risk | Recommendation | Applied |
| --- | --- | --- | --- |
| Behavioral evaluation retry parked without asking the user | HIGH | CHANGE | Moved to "Decisions for the user" |
| Rename leftover: Phase E said Phase F refreshes the wiki | MED | CHANGE | Fixed to Phase G |
| Later LEARN corrections clash with the byte-identical archive | MED | CHANGE | Later phases edit the working file only; G never re-runs `split_memory.py check` |
| Whole-folder protection misses `git -C .claude rm -r hooks` and `git -C … checkout` | MED | CHANGE | Phase D resolves unmodelled Git tokens against the `-C` directory, with a fallback to record the gap |
| After D, heredoc findings, PR bodies, and log appends that name agent paths are denied | MED | CHANGE | File-based route in Phase D docs, commit skill, and risks |
| Phase B fixture read this repository's `.claude/` (absent in CI) and would fail its byte check | MED | CHANGE | Fixture built from the temporary install; `.gitattributes` fixture seeded with the union line |
| Independent fixes tied to cancellable phases | MED | CHANGE | `LICENSE` restore moved to Phase A; Phase F can finish at `0.5.2` with the guard hardening; step-4 stop defined |
| Phase E scope claimed "only A2" but adopted other rows; P7 changes the coder's reply contract | MED | CHANGE | Scope restated; P7 declined; Q4 checks the coder report contract |
| Phase F spike never ran the integration install in isolation | MED | CHANGE | Step 1 item 6 and stop condition (h) |
| One PR delays the security fixes in B and D | MED | ACCEPT with fallback | Offer to cancel a stalled E or F with evidence |
| Two "new" defects were already in the 2026-09-21 record | LOW | CHANGE | Context says re-confirmed and re-rated |
| Dated-record exception named only Phase A | LOW | CHANGE | Non-Goals and BF-G2 name A and C |
| `S` rule could archive command-recovery lessons | LOW | CHANGE | Such entries always stay |
| `split_memory.py` in AI state as a one-shot required check | LOW | ACCEPT | Reviewer reads the tool |
| July plans `complete` while logs say BLOCKED | LOW | KEEP | Resolution notes and merge SHAs make it honest |
| Exact-line `settings.local.json` check misses negations | LOW | ACCEPT | Implementer may use `git check-ignore` instead |
| Phase D friction on `ls`, `find`, `diff` of agent paths | LOW | KEEP | Documented recovery; Python 3.9 hook job must keep passing |
| Phase G cannot detect a skipped refresh | LOW | CHANGE | `test ! -e openwiki/.run.json` |
| Three recorded follow-ups unnamed; gate-repair row lacks `.claude/hooks/` | LOW | CHANGE | Carried list in Non-Goals and Phase G; row fixed in Phase D |
| No explicit cancel procedure for Phase F; E's cancelled entry not ticked | LOW | CHANGE | F step 7; both tick and annotate |
| Leftover "Phase A" cross-references in C and E | LOW | CHANGE | Removed |
| Spike install needs network and runs dependency scripts | LOW | ACCEPT | Stated in F step 1 and the rollback note |
| `.code-workspace` protection as YAGNI | LOW | KEEP | Matches `.vscode/settings.json` protection |

## Decisions recorded

The user approved this plan on 2026-10-20 with these decisions:

1. **Behavioral evaluation retry (audit §7 item 4):** parked. The
   2026-10-06 pilot stopped because all four native case runs failed with no
   captured error; a retry needs error capture for native runs first, and no
   current failure calls for it.
2. **Memory archive location (Phase C):** option (a), the preserved
   `.claude/explorations/2026-10-20_memory-archive/` folder, with no
   ownership change. Option (b), a dedicated `.claude/memory/` state path,
   was declined.
3. **`ponytail-review` scope (Phase E, row R2):** stays a complexity-only
   review. Upstream v5's full quality review was declined because it would
   duplicate the profile-based reviewer in full installs.
4. **Scope additions found during planning:** approved. Whole-folder and
   `git -C` protection and `.code-workspace` protection in Phase D, the
   verbatim license in Phase A, and the stricter OpenWiki `mode` check in
   Phase F each close a confirmed defect in code the same phase already
   changes.
5. **Memory split (Phase C), 2026-10-20 at the stop condition:** not
   applied. Only 18 of 328 entries (6.11% of entry bytes) qualified under
   the approved rule; the user chose to skip the split for now rather than
   apply the small cut or build a topic-scoped live-advice archive.
6. **Guard decision rule (Phase D), orchestrator decision 2026-10-21
   within the approved goals:** two review rounds showed that resolving
   unmodelled Git tokens against the `-C`/`cd` directory let a command that
   was denied at the start of this plan become "ask" (for example an
   absolute path under `git -C`, or the same hook file named in two
   segments of one command line, or a secret file beside a newly protected
   agent path). The fix makes the guard fail closed: a redirect target
   (also a leading one) counts only as a confirmed target, any "uncertain"
   hit (a protected path the guard cannot judge) denies on every client,
   and a secret-shaped target denies before the hook-config rule applies.
   This departs from Phase D's "the decision rule in `emit()` stays as it
   is": it never loosens a decision (the comparison against the pre-plan
   guard is recorded in the Phase D closeout log), and it tightens some
   pre-existing mixed commands from ask to deny (for example `git restore`
   of a protected config chained with `rm` of it, `rm .env .mcp.json`, or
   a settings edit whose heredoc body names a hook script), and it denies
   secret-shaped names inside the older hook folders (`.claude/hooks/.env`:
   edit and `rm` asked and read tools were allowed before).

## Verification

```bash
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Completion Evidence

Each phase's closeout log maps its BF IDs to tests or evidence. Phase G's
log maps every BF ID, including any phase cancelled with evidence, and
records the audit under `## Stale-claims surfaces checked`. Each completed
phase gets one commit and one normal push attempt. PR creation and merge
stay the user's decision.
