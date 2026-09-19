---
name: 2026-09-19_openwiki-knowledge-layer-integration
type: big-plan
status: in-progress
originating_branch: dev
implementation_branch: 2026-09-19_openwiki-knowledge-layer-integration_implementation
started_at: 2026-09-19T06:51:50Z
phases:
  - 2026-09-19_phase-A-openwiki-runtime-and-safety-boundary
  - 2026-09-19_phase-B-openwiki-knowledge-ownership-and-agent-access
  - 2026-09-19_phase-C-openwiki-lifecycle-integration
  - 2026-09-19_phase-D-openwiki-dogfood-migration-and-closeout
  - 2026-09-19_phase-E-openwiki-child-process-sandbox
current_phase: 2026-09-19_phase-B-openwiki-knowledge-ownership-and-agent-access
---
# Big Plan: 2026-09-19_openwiki-knowledge-layer-integration

## Context

The bootstrap keeps durable agent state under `.claude/`, maintains repository documentation
by hand, and treats `.claude/MEMORY.md` as a cross-session project-memory surface. This works,
but repository-derived facts get duplicated across source, `README.md`, `docs/`, root guidance,
and memory. The standing final-phase stale-claims audit reduces drift, but it still relies on
manual discovery.

OpenWiki (`langchain-ai/openwiki`, pinned at `0.5.2`) can provide a generated, evidence-backed
repository knowledge layer under `openwiki/`. Its code mode maintains Markdown pages plus
grounded claim sidecars under `openwiki/.claims/`, records the last documented Git HEAD in
`openwiki/.last-update.json`, and updates incrementally by diffing that HEAD against the current
one. It is a good fit for derived architecture, component, workflow, API, testing, and runtime
knowledge.

Verified upstream behavior that shapes this plan (checked against the `v0.5.2` source):

- Every code-mode run, both `--init` and `--update`, rewrites a managed
  `<!-- OPENWIKI:START -->…<!-- OPENWIKI:END -->` block in root `AGENTS.md` and `CLAUDE.md`.
  There is no flag or environment variable that disables this. The bootstrap requires those
  adapters to remain bootstrap-owned and restorable byte-for-byte.
- `--init` also creates `.github/workflows/openwiki-update.yml`, a scheduled GitHub Actions
  workflow. `--update` never does, and upstream's own CI example documents that `--update`
  performs the first generation when no wiki exists yet.
- Provider choice, keys, and OAuth tokens live in `~/.openwiki/` (relocatable with
  `OPENWIKI_CONFIG_DIR`). Non-interactive runs fail with an actionable message when
  credentials are missing.
- Anonymous telemetry is on by default and honors `OPENWIKI_TELEMETRY_DISABLED=1` and
  `DO_NOT_TRACK=1`.
- In-progress generation state lives in `openwiki/.run.json`, kept across interrupted runs for
  resume and deleted only after successful finalization.
- A no-op update skips model work but still rewrites `openwiki/.last-update.json`.
- Incremental change detection is best-effort: when the recorded base HEAD is unreachable
  (for example after a squash merge or history rewrite), OpenWiki silently falls back to
  dirty and untracked paths only.
- `mermaid` and `jsdom` are optional peer dependencies; without them OpenWiki uses a
  lightweight Mermaid validator.

This plan adds OpenWiki as an **opt-in generated knowledge layer**, dogfoods it on the
bootstrap repository, and makes a dedicated final knowledge-refresh phase the lifecycle pattern
for future OpenWiki-enabled big plans.

## Goals

- Pin and expose a compatible OpenWiki CLI, with its optional Mermaid validators, in the
  bootstrap devcontainer, and persist the user's OpenWiki configuration across rebuilds without
  the bootstrap owning any provider credential.
- Add one bootstrap-owned, target-neutral OpenWiki runner that works from Codex, Claude,
  GitHub Copilot, and Antigravity without host-specific OpenWiki integrations.
- Preserve bootstrap ownership of `AGENTS.md`, `CLAUDE.md`, workflow files, and other
  control-plane surfaces even though upstream writes its own managed snippets.
- Never run OpenWiki from deterministic verification, hooks, post-commit automation, or
  scheduled CI as part of this integration.
- Keep the runner privacy-preserving by default: telemetry off unless the user chooses
  otherwise; resumable run state never enters Git.
- Define an explicit knowledge-ownership model:
  - source/tests define behavior;
  - human-authored policy, security, ADR, runbook, and README content remains authoritative;
  - `openwiki/**` contains generated descriptive repository knowledge;
  - `MEMORY.md` contains durable project-specific learning that is not derivable from the
    repository;
  - plans and session logs remain execution/history evidence.
- Make OpenWiki activation explicit and repository-local. Presence of
  `openwiki/INSTRUCTIONS.md` is the enablement marker.
- For OpenWiki-enabled multi-phase big plans, make the last phase a small knowledge-refresh
  phase that runs after implementation phases have completed and committed.
- Dogfood the design on `github_copilot_bootstrap` itself, then reduce duplicated descriptive
  docs/memory only where generated coverage is proven adequate.
- Preserve the current manual final-phase stale-claims audit for normative and non-derivable
  surfaces that OpenWiki cannot own.

## Non-Goals

- Do not delete `MEMORY.md`.
- Do not delete `docs/` wholesale.
- Do not make generated OpenWiki pages normative source of truth.
- Do not install OpenWiki's host-specific integrations as a bootstrap requirement.
- Do not add an OpenWiki scheduled GitHub Actions workflow or auto-merge path.
- Do not store provider credentials, OAuth state, or OpenWiki private configuration in the
  repository, and do not forward individual provider API keys through the devcontainer.
- Do not make `verify.py` invoke a model, network service, or OpenWiki generation.
- Do not initialize OpenWiki automatically in every consumer repository in this first rollout.
- Do not optimize the integration for one model provider.
- Do not change the repository's merge policy to suit OpenWiki. The user owns merge and
  squash decisions.

## Design Overview

```mermaid
flowchart TD
    S[Source + tests] --> OW[Bootstrap-owned OpenWiki runner]
    N[Policies / ADRs / security / README] --> OW
    I[openwiki/INSTRUCTIONS.md opt-in brief] --> OW
    OW --> W[openwiki/** generated knowledge + claims]

    S --> A[Authoritative behavior]
    N --> A

    L[Non-derivable lessons / rationale / caveats] --> M[.claude/MEMORY.md]
    P[Plans + session logs] --> H[Execution/history evidence]

    W --> J[Just-in-time agent context]
    M --> J
    A --> J

    X[Implementation phases committed] --> K[Final knowledge-refresh phase]
    K --> OW
    K --> D[Manual stale-claims audit]
    D --> C[Final phase closeout + commit]
```

### Activation and execution contract

An outer repository is OpenWiki-enabled only when `openwiki/INSTRUCTIONS.md` exists.

The bootstrap runner:

1. exits cleanly without mutation when OpenWiki is not enabled, unless `--require-enabled`
   was requested;
2. invokes `openwiki code --update --print`, including for the first generation;
3. never invokes `--init`, because `--init` scaffolds a scheduled workflow and replaces the
   whole wiki;
4. builds the child environment from the current environment and sets
   `OPENWIKI_TELEMETRY_DISABLED=1` only when the user has not already set that variable;
5. snapshots bootstrap-owned root `AGENTS.md` and `CLAUDE.md` as exact working-tree bytes,
   restores them in `finally`, and proves the bytes match the pre-run state;
6. snapshots `.github/workflows/openwiki-update.yml` when it exists and proves it was not
   created or changed;
7. permits OpenWiki-caused outer-repository changes only under `openwiki/**` after protected
   surfaces are restored;
8. preserves `openwiki/.run.json` or other OpenWiki-owned recovery state on a failed run so a
   later retry can resume; `openwiki/.run.json` is ignored by Git through the installer-managed
   ignore block;
9. never reads, writes, or persists provider secrets itself;
10. runs serially. The lifecycle must not start parallel OpenWiki runs against one checkout.

The runner is an explicit model-backed lifecycle action, not a deterministic quality gate.

### Rebaseline rule

Incremental refresh quality depends on the base HEAD recorded in `openwiki/.last-update.json`
staying reachable. When a squash merge or history rewrite makes it unreachable, OpenWiki's
fallback is degraded incremental assistance, not a failure. When a clean baseline is required:
preserve `openwiki/INSTRUCTIONS.md`, remove the rest of `openwiki/**`, and run the standard
runner again. Never use `--init` for this. The runner gets no rebaseline flag in this plan; the
OpenWiki skill documents the manual procedure.

### Knowledge ownership

| Surface | Ownership |
| --- | --- |
| Source code and tests | Authoritative behavior |
| Shared policies, security docs, ADRs, operator runbooks | Human-authored normative authority |
| `README.md` | Small human entry point and externally useful instructions |
| `openwiki/INSTRUCTIONS.md` | Human-authored OpenWiki scope/priority brief and enablement marker |
| `openwiki/**` except `INSTRUCTIONS.md` | Generated descriptive repository knowledge |
| `.claude/MEMORY.md` / `shared/MEMORY.md` seed | Non-derivable durable lessons, rationale, caveats, operational knowledge |
| Plans / explorations / session logs / receipts | Historical execution and evidence |

A fact that can be re-derived from current source/tests should normally not be copied into
`MEMORY.md`. A policy or design decision remains human-authored even if OpenWiki describes it.

## Cross-Model Principles

1. OpenWiki execution is owned by a repository script/skill, not by one model vendor's native
   integration.
2. Codex, Claude, Copilot, and Antigravity receive the same rule: generated wiki is optional
   just-in-time context; source/tests and canonical policy remain authoritative.
3. Missing OpenWiki provider authentication is an actionable lifecycle failure only when an
   enabled repository reaches its required knowledge-refresh phase. It must not break ordinary
   bootstrap installation or deterministic verification.
4. Automated tests use fakes/test doubles for OpenWiki subprocess behavior. Real model-backed
   generation is limited to explicit acceptance/dogfood runs.
5. Generated OpenWiki pages are reviewed as generated artifacts; agents do not hand-edit them.

## Phases

- [x] `2026-09-19_phase-A-openwiki-runtime-and-safety-boundary` — pin the dependency and its optional validators, persist user config, add the target-neutral runner, protect bootstrap-owned surfaces, ignore resumable run state, and cover the failure/restore contract with deterministic tests.
- [ ] `2026-09-19_phase-B-openwiki-knowledge-ownership-and-agent-access` — encode the knowledge-ownership contract in canonical policy, add the narrow OpenWiki skill with the rebaseline rule, and add provider-neutral root guidance.
- [ ] `2026-09-19_phase-C-openwiki-lifecycle-integration` — teach planner, orchestrator, documenter, learn, and onboard behavior how OpenWiki-enabled big plans end with a small knowledge-refresh phase, without touching disabled repositories.
- [ ] `2026-09-19_phase-D-openwiki-dogfood-migration-and-closeout` — transition phase: enable OpenWiki for the bootstrap repository, run the real generation/update path, migrate only proven duplicate descriptive knowledge, and complete the repository-wide stale-claims audit.
- [ ] `2026-09-19_phase-E-openwiki-child-process-sandbox` — replace Phase A's detect-and-refuse symlink containment with operating-system-enforced isolation of the OpenWiki child process, so a write outside `openwiki/**` becomes impossible rather than merely reported.

## Step Summary

| Phase | Owner | Main target files | Required Skills | Review Profiles | Verification |
| --- | --- | --- | --- | --- | --- |
| A | coder | `shared/devcontainer/Dockerfile`, `shared/devcontainer/devcontainer.json`, new `shared/scripts/openwiki_refresh.py`, `scripts/generate_targets.py`, `scripts/install_bootstrap.py`, `scripts/validate_targets.py`, runner tests, devcontainer docs | `create-feature`, `add-dependency`, `ponytail` (full), `code-style`, `testing-patterns` | `code`, `architecture`, `security`, `tests`, `ponytail` | focused runner/generator/installer tests; `verify.py fast`; canonical phase/closeout receipts |
| B | coder + documenter | `shared/policies/workflow.instructions.md`, `shared/policies/workspace.instructions.md`, `shared/MEMORY.md`, `docs/architecture.md`, `README.md`, new `shared/skills/openwiki/SKILL.md`, authoring `AGENTS.md` / `CLAUDE.md` | `create-feature`, `ponytail` (full), `code-style`, `testing-patterns`, `documentation`, `humanize` | `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation` | focused policy/skill/root tests; generated-target validation; `verify.py fast`; receipts |
| C | coder + documenter | planner/orchestrator/documenter prompts, `plan-decomposition`, `documentation`, `learn`, `onboard` skills, `shared/templates/plan-big.md`, `shared/policies/workflow.instructions.md` | `ponytail` (full), `code-style`, `testing-patterns`, `documentation`, `humanize` | `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation` | focused plan-generation/lifecycle tests; generated-target validation; `verify.py fast`; receipts |
| D | coder + documenter | new `openwiki/INSTRUCTIONS.md`, new `.openwikiignore`, generated `openwiki/**`, `README.md`, `docs/**`, `shared/MEMORY.md`, stale live-advice surfaces | `openwiki`, `documentation`, `humanize`, `learn`, `deep-audit`, `ponytail` (full) for any code fix | `code`, `architecture`, `security`, `tests`, `ponytail` when code changes, `documentation` | real OpenWiki acceptance runs plus deterministic repository checks; final stale-claims audit; receipts |

| E | coder | `shared/scripts/openwiki_refresh.py`, `shared/devcontainer/Dockerfile`, `scripts/validate_targets.py`, runner tests | `ponytail` (full), `code-style`, `testing-patterns` | `code`, `architecture`, `security`, `tests`, `ponytail` | deterministic sandbox-escape tests; `verify.py fast`; receipts |

Skill names above refer to `shared/skills/<name>/SKILL.md`.

## Risks and Fallback Paths

| Risk | Level | Mitigation / fallback |
| --- | --- | --- |
| OpenWiki writes root `AGENTS.md` / `CLAUDE.md` on every run and offers no opt-out | HIGH | The runner restores exact pre-run bytes in `finally`, verifies the result, and rejects any unexpected out-of-scope mutation. Keep root adapters out of OpenWiki evidence via `.openwikiignore` in the dogfood repo. If upstream adds a stable opt-out before implementation, use it and retain restore assertions as defense-in-depth. |
| Upstream CLI behavior changes after installation (0.4.x to 0.5.2 shipped within weeks) | HIGH | Pin `openwiki@0.5.2`, `mermaid@11.16.0`, `jsdom@29.1.1`. Do not float `latest`. Upgrade only through a reviewed dependency change with runner acceptance tests. |
| Model/provider auth makes closeout nondeterministic | MEDIUM | OpenWiki remains opt-in. Do not call it from `verify.py`, hooks, installer, or CI. The explicit final knowledge phase reports actionable auth/provider failures and can be retried without bypassing the phase. |
| Devcontainer rebuild loses OpenWiki credentials | MEDIUM | Bind-mount the host `~/.openwiki` directory. Document that the host directory must exist before the first build, because Docker creates a missing bind source as root-owned. Do not forward provider keys through `containerEnv`. |
| Resumable `openwiki/.run.json` is committed by mistake | MEDIUM | Add it to the installer-managed `.gitignore` block and assert it in the target validator. Resume still works because the file stays on disk. |
| Generated wiki duplicates or contradicts normative docs | HIGH | Keep authority matrix explicit. Review generated content against source. Never delete normative docs because OpenWiki generated similar prose. |
| Incremental detection silently degrades after squash merge or history rewrite | MEDIUM | Document the rebaseline rule in the OpenWiki skill and in planning policy. Do not change the merge policy for OpenWiki. |
| Every big plan gains ceremony | MEDIUM | Add the final knowledge phase only in repositories that have enabled OpenWiki and only for multi-phase big plans that change documentable outer-repository behavior. Disabled repos retain the existing lifecycle. |
| OpenWiki generation consumes unnecessary model budget | MEDIUM | Use deterministic fakes for automated tests. Dogfood only the minimum real runs needed to prove initial generation and post-migration update. Do not run generation inside broad test matrices. |
| Concurrent OpenWiki runs corrupt/churn state | MEDIUM | Lifecycle requires one serial runner per checkout. If this cannot be guaranteed operationally, add a small atomic lock in the runner before enabling consumer rollout. |
| OpenWiki escapes `openwiki/**` through a symlink it creates while running | HIGH | Phase A checks before and after the run and fails closed, naming every path that moved, and restores the root adapters from pre-run bytes regardless. Nothing is committed on a failed refresh. Residual gap: a write landing outside the repository entirely is not detected. Phase E closes that gap with operating-system-enforced isolation of the child process. |
| Generated docs become a second hidden control plane | HIGH | Root guidance treats OpenWiki as optional just-in-time context. Source/tests/policies remain authority and the runner is not allowed to mutate bootstrap control-plane files. |

## Verification

During implementation, use focused tests plus the repository's deterministic fast verifier.
Do not make OpenWiki model execution part of deterministic verification.

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json
```

At each phase closeout, follow the canonical workflow and require `verify phase` followed by
`verify closeout` PASS receipts.

The real OpenWiki CLI is exercised only in Phase D acceptance. Phases A, B, and C must be fully
testable without provider credentials or model calls.

## Completion Evidence

The final phase listed under `phases:` (Phase D) must also run a documentation, memory, and
LEARN audit: sweep every live-advice surface for claims this plan or earlier work invalidated,
correct or supersede each one, leave dated records unchanged, and record the audited surfaces
and each one's outcome under a `## Stale-claims surfaces checked` heading in that phase's
closeout session log. `verify.py`'s closeout gate requires that exact heading, non-empty,
whenever the phase it is closing out is this list's last entry.

## Done Criteria

- OpenWiki is pinned to `0.5.2` with pinned optional Mermaid validators, and the runtime
  satisfies its Node engine (`>=22.22.0`).
- The devcontainer persists `~/.openwiki` from the host; no provider key is forwarded or stored.
- Consumer generation installs one bootstrap-owned OpenWiki runner under `.claude/scripts/`.
- The runner can initialize/update an enabled repository using `openwiki code --update --print`
  while preserving bootstrap root adapters and any existing OpenWiki workflow byte-for-byte,
  with telemetry disabled unless the user opted in.
- A failed OpenWiki subprocess restores protected surfaces and leaves resumable OpenWiki-owned
  state intact; `openwiki/.run.json` is ignored by Git in every bootstrap-managed repository.
- No automated verifier, hook, installer, state-sync action, or scheduled workflow performs
  model-backed OpenWiki generation.
- Knowledge ownership is explicit in canonical policy, the OpenWiki skill, and root guidance.
- `MEMORY.md` is narrowed to non-derivable durable knowledge rather than repository facts that
  OpenWiki can regenerate.
- Planner/orchestrator behavior adds a small final knowledge-refresh phase for applicable
  OpenWiki-enabled big plans without changing disabled repositories.
- The documenter does not hand-edit generated OpenWiki pages.
- The bootstrap repo contains an intentional `openwiki/INSTRUCTIONS.md`, safe
  `.openwikiignore`, and a generated evidence-backed wiki.
- Any `docs/` or memory content removed during migration has a reviewed replacement or is
  proven redundant; normative/manual content remains.
- Final repository-wide stale-claims audit is recorded in the Phase D closeout log.

## Devil's Advocate Report

| Concern | Risk | Alternative | Recommendation |
| --- | --- | --- | --- |
| Why add a wrapper instead of waiting for an upstream opt-out for agent files? | HIGH | Wait for upstream and make no integration now. | CHANGE: isolate upstream behavior behind one wrapper so the bootstrap can ship safely now and later delete the workaround when upstream exposes a stable policy. |
| Why not reuse `restore-root-adapters.sh` instead of a new snapshot? | MEDIUM | Call the existing hook script after each run. | ACCEPT the snapshot: the hook restores the canonical mirrored adapters, while the wrapper must preserve the exact pre-run working-tree bytes, including legitimate uncommitted edits, and must work before any mirror exists. This is not duplicated functionality. |
| Why not use OpenWiki's native host integrations? | MEDIUM | Install each supported host integration and add separate behavior for unsupported targets. | ACCEPT: keep one CLI path. Host-specific installation would undermine the bootstrap's cross-target contract and still does not cover all targets. |
| Why keep `MEMORY.md` if OpenWiki is intended as memory? | HIGH | Replace it entirely with generated wiki. | ACCEPT: keep a smaller MEMORY surface because rationale, operational lessons, user/project decisions, and AI-state are not reliably derivable from outer-repository source. |
| Why append a final knowledge phase instead of invoking OpenWiki in `verify.py`? | HIGH | Treat docs freshness as a deterministic verification check. | ACCEPT: model/network work is not deterministic verification. A separate phase preserves lifecycle evidence and retry semantics. |
| Why forward no provider keys through the devcontainer? | MEDIUM | Add `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and similar to `containerEnv` like `HF_TOKEN`. | CHANGE to bind mount only: OpenWiki supports many providers including OAuth and cloud credentials; forwarding keys makes the bootstrap own a provider matrix it should not own. |
| Why not require merge commits so incremental refresh stays reliable? | MEDIUM | Prohibit squash merges in OpenWiki-enabled repos. | ACCEPT with documentation: the user owns merge decisions; document the rebaseline procedure instead of constraining Git policy. |
| Was the original three-phase split too coarse? | MEDIUM | Keep one phase for all policy, skill, agent, and root-guidance edits. | CHANGE to four phases: the ownership contract and agent access (B) is a dependency of the lifecycle integration (C); splitting along that boundary keeps each control-plane commit reviewable. |
| Could the final knowledge phase become expensive boilerplate? | MEDIUM | Run OpenWiki on every commit or in scheduled CI instead. | ACCEPT with guard: only explicitly enabled repos get the phase, its normal shape is small (refresh, inspect, audit, review, verify, commit), and automated tests never spend model calls. |
| Is removing descriptive `docs/` too aggressive in the first rollout? | HIGH | Keep all existing docs permanently and only add OpenWiki. | CHANGE: migration is evidence-based and optional per file. Remove or shorten a document only after generated coverage and remaining human audience needs are reviewed. |

No unresolved HIGH-risk user decision remains. The conservative defaults are: opt-in consumer
activation, no scheduled CI, no provider credential management, telemetry off by default,
no blanket docs deletion, no merge-policy change, and no replacement of MEMORY.
