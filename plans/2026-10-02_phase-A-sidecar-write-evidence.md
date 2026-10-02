---
name: 2026-10-02_phase-A-sidecar-write-evidence
type: small-plan
parent_plan: sidecar-workflow-repair
phase_index: 1
status: planned
closeout_session_log:
---

# Small Plan: Native Sidecar State Write Evidence

## Scope

Prove that `.ai-bootstrap/` supports the writes the workflow needs before
changing production code. This is an evidence-only phase: update the
provider contract and record the exact native session outcomes. The
hands-on review proved a simple write to a different root-level hidden
folder; it did not prove the proposed root or delegated plan/report writes.

### Required Skills

- `shared/skills/integration-gate-spike/SKILL.md`
- `shared/skills/documentation/SKILL.md`
- `shared/skills/humanize/SKILL.md`

## Steps

- [ ] **1. Prepare one isolated fixture and a bounded probe recipe.**
  **Owner:** orchestrator; documenter records the recipe in
  `docs/sidecar-provider-contract.md`.
  **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`,
  `shared/skills/documentation/SKILL.md`.
  Use a disposable repository under `/tmp` with no push remote, staged
  team `.claude/settings.json`, a team rule, and a small source file. Reuse
  the provider contract's fixture conventions; staged files suffice when
  the authoring hook blocks fixture commits. Snapshot status, index entries,
  and team-file bytes. Ignore exact fixture tooling paths and
  `/.ai-bootstrap` through the fixture's local exclude file. Create only
  fixture copies of workflow agents/templates, with their state references
  changed to the candidate root; do not edit production source or `dist/`.
  Keep an old-root write probe as a control, and a normal root-file probe
  to distinguish general Write denial from the protected-path problem.

- [ ] **2. Run direct state writes with ordinary client permissions.**
  **Owner:** orchestrator on the native host.
  **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`.
  Record `claude --version`, the working directory, model, exact command,
  tool allowlist, permission mode, exit/result status, and denied requests.
  Start from the review's invocation shape: `claude -p --model sonnet
  --permission-mode acceptEdits`, with native Write/Edit available. Confirm
  available flags from the installed CLI before the run. Do not bypass
  permissions, edit settings, grant blanket shell writes, or install/update
  a client. Use native Write/Edit to create and then edit distinct marker
  files in `.ai-bootstrap/plans/`, `session_logs/`, `quality_reports/`,
  `explorations/`, and `MEMORY.md`. Inspect actual file contents and tool
  results outside the model. A Bash-created file does not pass this check.
  **Acceptance:** all new-root markers match with no per-file approval;
  team bytes and index match the snapshot. Remove the root-file control
  created by this probe before comparing final status.

- [ ] **3. Prove delegated writes and a short end-to-end task.**
  **Owner:** orchestrator; documenter records results.
  **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`,
  `shared/skills/documentation/SKILL.md`.
  Run the fixture's planner and reviewer through the client's native
  delegation mechanism. Require a saved plan and review report, then a
  short session log and a memory edit. Confirm delegation from tool events,
  not a claimed role in reply text. Have the reviewer inspect a supplied
  small fixture diff, so it has real evidence to review. The task may change
  only that fixture source and the ignored state. Record discovery, direct
  writing, and delegated writing as separate capabilities.
  **Acceptance:** all required artifacts exist at the new root with the
  expected content, without manual approvals or writes to the old root.

- [ ] **4. Record the decision gate and review the evidence.**
  **Owner:** documenter, then reviewer; orchestrator owns closeout.
  **Required Skills:** `shared/skills/documentation/SKILL.md`,
  `shared/skills/humanize/SKILL.md`, `shared/skills/code-review/SKILL.md`.
  Append dated observations and a reproducible recipe to
  `docs/sidecar-provider-contract.md`. Preserve the 2026-09-27 discovery
  matrix as historical evidence and label this as a separate write gate.
  Keep a compact evidence table rather than raw transcripts or credentials.
  Record unsupported/unavailable clients as unverified; do not expand
  Copilot, Codex, or Antigravity support claims.
  **Acceptance:** Phase B may begin only after steps 2 and 3 pass. If the
  client is unavailable or writes fail, retain the evidence, leave this
  phase incomplete, and report the exact blocker. Do not fabricate a
  deterministic test failure or cancel future phases without authorization.

## Verification

```bash
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Host-session evidence from steps 2 and 3 is recorded here because the
  verifier cannot reproduce a host session. Its placement in this section
  does not waive the explicit native-evidence acceptance gate for Phase B.
- Other client sessions may add dated observations if already available;
  they are not prerequisites and do not justify new discovery paths.

## Review Profiles

Load `.claude/review-profiles/code.md`,
`.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`.

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
