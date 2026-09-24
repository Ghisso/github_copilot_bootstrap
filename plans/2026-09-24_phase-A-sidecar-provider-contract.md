---
name: 2026-09-24_phase-A-sidecar-provider-contract
type: small-plan
parent_plan: consumer-sidecar-bootstrap-overlay
phase_index: 1
status: planned
closeout_session_log:
---

# Small Plan: Phase A — Sidecar Provider Contract

## Scope

An evidence-gathering spike before any implementation. The single output is
`docs/sidecar-provider-contract.md`. It freezes each client's skill roots and
bridge, with an evidence tier for every claim. This phase changes no
installer, generator, validator, or test code.

Clients in scope: Claude Code, OpenAI Codex, Google Antigravity, and GitHub
Copilot in VS Code. Copilot CLI and cloud agents are out of scope, which
matches the README's Copilot claim.

### Required Skills

- `shared/skills/integration-gate-spike/SKILL.md`
- `shared/skills/documentation/SKILL.md`

## Questions Per Client

1. Which repository skill roots does it read: `.claude/skills/`,
   `.agents/skills/`, or `.github/skills/`?
2. Does it discover a skill or bridge file that Git ignores through
   `info/exclude`?
3. When the same skill name is in two roots it reads, does it show one copy,
   both copies, or an error?
4. Does the candidate bridge load in every session while tracked team
   guidance stays active?
   - Claude Code: `.claude/rules/ai-bootstrap-sidecar.md` with no `paths`
     frontmatter. Second candidate: `CLAUDE.local.md`, used only when absent.
   - Google Antigravity: `.agents/rules/ai-bootstrap-sidecar.md`. This
     repository has never verified an Antigravity rule schema
     (`docs/smoke-tests.md`), so record the exact rule directory, including
     whether it is `.agents/` or `.agent/`, and the frontmatter it needs.
   - Copilot VS Code: `.github/instructions/ai-bootstrap-sidecar.instructions.md`
     with `applyTo: "**"`. Record whether `.github/copilot-instructions.md`
     stays active.
   - Codex: record whether any additive repository-local mechanism exists.
     Rejected by design: `AGENTS.override.md` (it replaces `AGENTS.md` in its
     directory), `project_doc_fallback_filenames` (used only without an
     `AGENTS.md`, and it needs a config file), and any `~/.codex` change.
5. Does it reject or warn about any skill frontmatter field the bootstrap
   ships, such as `visibility` or a multi-line `description`?
6. Client name, version, and observation date.

## Steps

- [ ] **1. Collect documented behavior.**
  - **Owner:** `coder`
  - Answer each question from official documentation. Record the source link
    and mark the answer `documented`.
  - Undocumented behavior is not a claim.

- [ ] **2. Write the fixture recipe.**
  - **Owner:** `coder`
  - In the contract document, write the exact shell commands that create a
    throwaway Git repository outside this repository, containing:
    - tracked team `CLAUDE.md`, `AGENTS.md`, and
      `.github/copilot-instructions.md`, each with a unique team marker phrase;
    - one tracked team skill in each skill root;
    - one sidecar marker skill in each skill root, with a unique name and a
      unique reply phrase;
    - the three bridge files, each with a unique sidecar marker phrase;
    - an `info/exclude` block that ignores every sidecar file.
  - The recipe ends by printing `git status --porcelain --untracked-files=all`,
    which must be empty.

- [ ] **3. Run each client against the fixture.**
  - **Owner:** user (operator); `coder` records the results.
  - Follow the `check_native_clients.py` conventions: a stable workspace that
    the operator trusts manually, explicit user authorization, and no change
    to trust or user settings.
  - Antigravity: use the `agy` CLI with `--new-project --sandbox`. A run
    that reuses a persisted project is invalid (`docs/runtime-checks.md`,
    Google Antigravity evidence boundary).
  - Ask the client to list its skills and to quote its active instructions.
    Record which marker phrases appear, and whether duplicates appear.
  - Where a client exposes structured data (an init event or a skills list),
    record that data. A model's description of itself is not proof.

- [ ] **4. Freeze the matrix.**
  - **Owner:** `coder`
  - One table row per client: skill roots read, ignored-file discovery,
    duplicate behavior, bridge path and frontmatter, evidence tier
    (`native-run`, `documented`, or `unavailable`), client version, and date.
  - State the resulting projection roots and bridge paths under the big
    plan's rule: a path ships only when at least one client has `native-run`
    evidence for it.

- [ ] **5. Apply the decision gate.**
  - **Owner:** `orchestrator`
  - If the matrix differs from the big plan's expected layout, revise Phases
    B-D before Phase B starts.

## Acceptance Criteria

- Every matrix row has an evidence tier. Nothing below `native-run` is
  described as supported.
- The Codex row names the rejected mechanisms and the result.
- Copilot is covered for VS Code only.
- Phase B can copy its path constants directly from the matrix.

## Verification

```bash
test -s docs/sidecar-provider-contract.md
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Claude Code native run against the fixture, done by the operator.
- OpenAI Codex native run against the fixture, done by the operator.
- Google Antigravity native run against the fixture, done by the operator.
- GitHub Copilot VS Code native run against the fixture, done by the operator.

## Review Profiles

- `documentation`
- `architecture`
- `security`

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT).

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
