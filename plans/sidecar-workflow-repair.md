---
name: sidecar-workflow-repair
type: big-plan
status: complete
originating_branch: dev
implementation_branch: sidecar-workflow-repair_implementation
started_at: 2026-10-02T06:40:46Z
phases:
  - 2026-10-02_phase-A-sidecar-write-evidence
  - 2026-10-02_phase-B-sidecar-workflow-repair
  - 2026-10-02_phase-C-sidecar-workflow-repair-knowledge-refresh
current_phase: 
---

# Big Plan: Sidecar Workflow Repair

## Context

The hands-on review at
`.claude/explorations/2026-10-02_sidecar-workflow-profile-hands-on-review.md`
records seven open findings against `dev` at `a2c68b3`. Installation and
ownership checks passed, but Claude Code blocked state writes under
`.claude/ai-bootstrap/`, and an older full install was accepted as a sidecar
target. The reported 699 passing tests establish the previous baseline;
they do not prove these defects are fixed.

The original `sidecar-workflow-profile` plan is complete and merged. This
is a new plan. Its decisions supersede the old state-location decision for
future sidecar releases, without editing completed plans or their receipts.

The user requested the fewest practical phases. Keep three: a small
evidence-only phase, one implementation phase covering all seven findings,
and the final knowledge refresh required because `openwiki/INSTRUCTIONS.md`
exists. Do not split implementation by finding or client.

## Goals

- Let Claude Code write personal plans, reports, logs, and memory without
  per-file approval under its ordinary `acceptEdits` mode.
- Preserve existing personal state when moving the sidecar namespace.
- Refuse sidecar installation into current and recognized legacy full
  installs, while preserving team-owned configuration precedence.
- Make dry-run reports accurate and state backups serialized and recoverable.
- Make workflow guidance usable when a client has no specialist agents or
  when a team agent name suppresses a sidecar specialist.
- Add meaningful regressions for the seven review findings plus Phase A's finding 8 (planner and reviewer saves; the caller saves) and update live advice.

## Boundaries

This authoring repository uses the full control-plane/high-risk lifecycle.
Its consumers' sidecar profile stays relaxed: no hooks, settings edits,
nested state repository, receipts, new dependencies, or new client support.
Do not weaken client permissions to make a probe pass. Do not change the
full install's state location or investigate its permission behavior unless
the new evidence makes that necessary for this repair.

Change `shared/` and `scripts/`, then regenerate both targets. Never edit
`dist/` directly. Preserve tracked files, index entries, foreign files,
cross-client team-name precedence, and the existing filesystem protections.
Do not update real consumer repositories as part of this plan. Refreshing
`img-classification` with full mode remains separate maintenance work.

## Design Overview

### Decisions

| Topic | Decision |
| --- | --- |
| State location | Use `.ai-bootstrap/` at the consumer root, subject to Phase A's native write gate. Keep `.claude/` for discoverable tooling. Do not introduce a configurable state root. |
| Known state paths | `SIDECAR_STATE_ROOT` names the new root. Keep one explicit legacy root for parsing old ownership/exclude evidence, backup, uninstall, and migration. Only the new root is generated and seeded for a new workflow install. |
| State ownership | State is mutable user work, not a hashed payload. An old managed exclude entry, with otherwise valid sidecar preflight, is evidence for an automatic move. Folder existence or familiar filenames alone do not authorize migration. |
| Migration | During a workflow install/update, migrate an owned legacy folder only when the new destination is absent. Under the existing run lock, validate both paths, establish the ignore gate, create a complete backup in the Git directory, then rename without merging. Finish normal reconciliation. |
| Collision | If both state roots exist, or a legacy folder has no sidecar ownership evidence, refuse the workflow update before writes. Name both paths and explain backup and manual reconciliation. Do not overwrite, auto-merge, adopt, or silently start a second memory store. |
| Compatibility | Preserve schema-1 skills and schema-2 workflow manifests. A path change alone does not require a new manifest schema. Skills-only reruns and ordinary uninstall retain legacy state; backup and explicit purge recognize both roots. A later workflow install migrates retained legacy state. |
| Legacy full installs | Keep the existing outer-index guard: any tracked `.claude` entry makes it team configuration. With an untracked, real `.claude` directory, require corroborating bootstrap evidence, not the folder name alone. Use the evidence table in Phase B. |
| Mixed installs | Full plus sidecar evidence is an actionable refusal, not a mode choice that either explicit flag will then reject. Do not add an automatic cleanup or conversion path. |
| Backup | Reuse the existing nonblocking run lock and filesystem diagnostics. Publish a backup name only after the copy completes. Share the narrow copy operation with migration without reacquiring the held lock. |
| Agent availability | Keep cross-client name precedence. Copilot plans and reviews directly. Sidecar rules and role prompts delegate only to roles actually available in the current client; otherwise the current agent performs the step under team guidance. |
| Reporting | Dry runs describe predicted actions and never print per-path messages asserting they happened. Real-run reports retain their useful detail. |

### Migration outcomes

| Existing state | Workflow install/update outcome |
| --- | --- |
| Neither root exists | Seed `.ai-bootstrap/` after the ignore gate. |
| Only owned legacy root exists | Back up, move to `.ai-bootstrap/`, reconcile tooling, remove obsolete legacy exclusion once safe. |
| Only new root exists | Preserve user contents; seed missing standard files through existing behavior. |
| Both roots exist | Refuse before writes; preserve both stores and give a recovery route. |
| Legacy root exists without ownership evidence | Refuse before writes; do not claim the folder. |
| Either root is tracked or has an unsafe filesystem shape | Apply the existing refusal protections to both namespaces. |

The migration is atomic at the directory rename, not across every installed
tooling file. After interruption, the new root and retained backup remain
discoverable; a rerun converges without moving or resetting the state again.
Keep the old exclusion until the old path is absent. Never return success
while active workflow prompts still point at a retired state location.

## Phases

- [x] `2026-10-02_phase-A-sidecar-write-evidence` — prove direct and delegated writes and record the decision gate.
- [x] `2026-10-02_phase-B-sidecar-workflow-repair` — implement and verify findings 1–8 in one phase.
- [x] `2026-10-02_phase-C-sidecar-workflow-repair-knowledge-refresh` — refresh OpenWiki and audit live advice.

## Ownership and Workflow

The current task writes draft plans only. Leave this plan `planning` and
all small plans `planned`; do not create the implementation branch or run
consumer mutations while drafting.

Once implementation is authorized, the main-thread orchestrator owns
pre-flight, branch creation, phase activation, verification, final state,
findings persistence, closeout, commits, and normal pushes. The coder owns
Phase B code and tests. The documenter owns authored documentation after
review converges. The reviewer performs two sequential passes with no
helper agents. Use one coder for the shared installer/overlay/generator
surface rather than parallel edits to those files.

Required review profiles for each phase are
`.claude/review-profiles/code.md`, `architecture.md`, `security.md`,
`tests.md`, `ponytail.md`, and `documentation.md` in that same directory.
All code-writing steps require `shared/skills/ponytail/SKILL.md` in full
mode. Refer to each small plan for the remaining exact skill paths.
Follow the canonical closeout sequence in
`shared/policies/workflow.instructions.md`; do not add an alternate gate.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
```

The small plans define focused executable checks. The authoritative phase
verification supplies the full regression suite, lint, and typing. A
native session result must include actual file contents and tool results;
a model's statement that it saved a file is insufficient.

## Risks and Devil's Advocate Review

| Concern | Risk | Alternative and disposition |
| --- | --- | --- |
| A successful root-file write does not prove delegated workflow writes | High | Keeping the protected location would leave the original defect. INVESTIGATE direct, planner, and reviewer writes in Phase A before code changes. |
| Automatic migration could merge or lose personal work | High | A manual-only move is simpler but leaves every existing user to repair paths. CHANGE to one owned-source, absent-destination rename with a completed backup; collisions refuse. |
| Generic `.claude` folders could be mistaken for old full installs | High | Treating any hooks folder as proof is too broad. CHANGE to corroborating legacy evidence behind the existing tracked-path guard, tested against negative fixtures. |
| An already mixed install has no safe flag-based recovery | Medium | Automatic removal could damage unknown ownership. ACCEPT refusal and document backup plus inspected cleanup; never advertise a flag that cannot work. |
| Native client or credentials are unavailable | High | Simulated writes do not establish the contract. INVESTIGATE on a supported host; leave Phase A incomplete and implementation blocked without changing permission settings. |
| Five implementation mini-phases would add lifecycle cost | Medium | CHANGE to one implementation phase with ordered steps and focused checks; retain only the evidence and required wiki boundaries. |
| A backup cannot freeze writes by unrelated editors | Low | A filesystem snapshot service is outside scope. ACCEPT this limit; document quiescent state for a point-in-time backup. The run lock serializes sidecar commands only. |

No unresolved product choice requires a drafting-time interview. Phase A's
write behavior and Phase B's fixture-backed legacy signatures remain
explicit evidence gates, not assumed successes.

## Done Criteria

- Findings 1–8 (seven review findings plus Phase A's finding 8) have a fix and evidence in Phase B's closeout log.
- Native write evidence passes without elevated permissions or settings changes.
- Legacy migration preserves bytes, backup history, Git status, and the index;
  failure and rerun scenarios pass through public installer entrypoints.
- Old full installs refuse sidecar mode; team-owned and skills-only fixtures
  retain their intended behavior.
- Both generated targets validate; runtime, full tests, lint, typing, and
  required review/closeout gates pass.
- Final OpenWiki refresh completes and live advice is consistent.

## Completion Evidence

Keep per-phase evidence in `.claude/session_logs/` and matching findings and
verification receipts in `.claude/quality_reports/`. Record new dated
provider evidence in `docs/sidecar-provider-contract.md`, preserving older
observations as history. Do not mark the original dated exploration fixed
by rewriting its historical findings; link it from the new closeout record.

The last phase records every audited live-advice surface and its outcome
under the exact heading `## Stale-claims surfaces checked` in its closeout
session log. It audits the whole plan, including README, docs, root guidance,
shared policies/skills/templates/agents/review profiles, state READMEs, the
project-context file, and `.claude/MEMORY.md`. Completed plans, receipt-bound
logs, and dated narratives remain historical evidence.
