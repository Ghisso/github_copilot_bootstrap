---
name: 2026-10-20_phase-G-backlog-followups-knowledge-refresh
type: small-plan
parent_plan: backlog-followups
phase_index: 7
status: planned
closeout_session_log:
---

# Small Plan: Backlog Follow-ups Knowledge Refresh

## Scope

Finish the plan with the required knowledge refresh and the final
stale-claims audit (BF-G1), and confirm the plan's boundaries held
(BF-G2). This phase changes no executable behavior. It brings the live
advice and the generated wiki in line with Phases A–F, and carries the two
OpenWiki corrections that `gate-repair` left for the next managed refresh.

## Steps

- [ ] **1. Run the final stale-claims audit (BF-G1).**
  **Owner:** orchestrator, with a documenter for prose changes.
  **Files:** as the audit finds; at least `docs/target-mapping.md`,
  `.claude/instructions/project-context.instructions.md`, and
  and the working `.claude/MEMORY.md`.
  **Required Skills:** `shared/skills/documentation/SKILL.md`,
  `shared/skills/ponytail/SKILL.md` (full).
  Sweep root guidance, `docs/`, shared policies, skills, templates, agents,
  review profiles, state READMEs, and the working `.claude/MEMORY.md` for
  claims this plan or earlier work made false. The Phase C archive is a
  dated record: never edit it, and do not re-run its `split_memory.py check`
  as evidence here, because any later in-place correction of a kept entry
  makes that check fail by design. When an archived lesson is now wrong and
  still needed, add a corrected entry to the working file. Required items:
  - the "Recorded follow-ups" list in `docs/target-mapping.md` no longer
    lists work Phases D–F finished, each remaining gap keeps its evidence,
    and the three follow-ups this plan carries without work stay listed:
    VS Code task tools such as `create_and_run_task`, the commit gate's
    five-profile rule not covering every multi-file diff, and the Copilot
    SDK and CLI payload key casing;
  - every statement of the Ponytail version, rules, and review scope matches
    what Phase E shipped (or still says `v4.8.4` if Phase E was cancelled),
    including the `[LEARN:architecture]` and `[LEARN:verification]` Ponytail
    pin entries if they are still in the working file (their line counts
    were already stale on 2026-10-20: they say 72 and 38 lines, the files
    have 73 and 40); if Phase E was cancelled, add audit gap A2 to the
    "Recorded follow-ups" list in `docs/target-mapping.md`;
  - every statement of the OpenWiki version and upgrade rule matches Phase F
    (or still says `0.5.2` if Phase F was cancelled), including the
    `[LEARN:tooling]` OpenWiki entry if it is still in the working file;
  - `.claude/instructions/project-context.instructions.md` "Current status"
    and pinned-version lines match the shipped state;
  - no `[LEARN]` entry in the working `MEMORY.md` contradicts a change in
    this plan, and its `## Archived Lessons` index still points at the
    archive.
  Leave dated records (archived plans, dated docs, closed session logs,
  dated explorations) unchanged. Record every surface and its outcome under
  `## Stale-claims surfaces checked` in the closeout log.

- [ ] **2. Refresh the OpenWiki knowledge layer.**
  **Owner:** orchestrator on the main thread, as the knowledge-refresh
  skill requires.
  **Required Skills:** `shared/skills/knowledge-refresh/SKILL.md` and
  OpenWiki's own `openwiki` skill.
  Start this phase in a new host session (or reconnect with `/mcp`) so the
  OpenWiki server runs the version Phase F installed; a `CONNECT_TIMEOUT`
  right after WSL boot is timing, not a broken install. Expect
  first-refresh churn after a version change (claims line references,
  `by: openwiki/<version>` provenance, index pages).
  Run one managed refresh after all source edits. Include the two
  corrections `gate-repair` left open
  (`.claude/session_logs/2026-10-17_gate-repair-phase-e.md`, "Open
  Questions / Next Steps"): add `.claude/hooks/` to the Claude Code cell of
  the config-protection row wherever a generated page restates the parity
  table, and scope the sentence "The commit gate (`exact`) always applies
  both rules" (`openwiki/operations/deterministic-verification.md:135`) to
  phase completion. Also carry item 2 of the 2026-09-21 OpenWiki follow-ups
  (handed over by Phase A): the "refresh this wiki" row of
  `openwiki/quickstart.md` lists only `openwiki-guard.py` and must also name
  the guard's entry point `shared/hooks/scripts/openwiki-guard.sh`. The
  refresh must also pick up Phase B (the consumer-state list in
  `openwiki/operations/install-ownership-and-runtime-checks.md` and the
  sentence in `openwiki/operations/git-backed-ai-state-sync.md` saying
  `setup` on an existing repository rewrites only `.gitignore`), Phase D (the protected-file list in
  `openwiki/architecture/hooks-and-guardrails.md` and the `sandbox_mode`
  sentence in `openwiki/architecture/agents-and-skills.md`) and Phase E (the
  pages that describe the Ponytail skills, for example
  `openwiki/architecture/agents-and-skills.md`). Inspect the generated diff. Never hand-edit generated pages or Claims sidecars.

- [ ] **3. Review, verify, close out.**
  **Owner:** orchestrator; fresh reviewer.
  **Required Skills:** `shared/skills/code-review/SKILL.md`.
  Map every BF requirement to its evidence in the closeout log, including
  any phase cancelled with evidence.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
test ! -e openwiki/.run.json    # a finished OpenWiki refresh removes its run file
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Record the OpenWiki completion result and the reviewed page list. This MCP
  evidence is required by the enabled-wiki policy but is not a shell command
  for the deterministic verifier to repeat.

## Review Profiles

Use `.claude/review-profiles/documentation.md`,
`.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
and `.claude/review-profiles/ponytail.md`.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
