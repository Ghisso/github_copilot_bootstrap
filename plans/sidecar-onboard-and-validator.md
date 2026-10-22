---
name: sidecar-onboard-and-validator
type: big-plan
status: planning
originating_branch: dev
implementation_branch: sidecar-onboard-and-validator_implementation
started_at: 2026-10-22T12:35:06Z
phases:
  - 2026-10-22_phase-A-validator-pytest-error
  - 2026-10-22_phase-B-sidecar-onboard
  - 2026-10-22_phase-C-knowledge-refresh
current_phase:
---

# Big Plan: Sidecar Onboarding and Validator Error

## Context

On `dev` at `9292776`, the workflow sidecar excludes `onboard`, so a sidecar user has no safe onboarding instructions. The public skill writes full-install state under `.claude/` and assumes tools and a nested Git repository that the sidecar does not provide. `validate_hook_gate_regression_tests()` directly runs a file that imports `pytest`; an isolated `uv` interpreter has no `pytest` and raises `ModuleNotFoundError`.

The 2026-10-22 planning check generated the unchanged source to `/tmp/sidecar-onboard-before-9292776.LWwNp5`. That temporary baseline may disappear; recreate it from a clean checkout at `9292776` before sidecar source edits. The exact read-only guard command in the handoff returned exit 0 with no denial from both `protect-files.py` and `protect-files.sh`, as did each side of its semicolon. The optional hook defect is therefore unconfirmed. A standalone fixture commit was blocked by this checkout's commit hook while planning, so the upgrade acceptance remains to be run inside the scenario test.

## Goals

- Replace the validator's raw missing-`pytest` traceback with a short, actionable failure while keeping the hook gate check mandatory.
- Add a workflow-only `onboard` skill at both sidecar skill roots, with its own source text and all persistent writes under `.ai-bootstrap/`.
- Make onboarding record the team's code placement, naming, implementation, testing, and commit conventions with evidence, so later changes fit the repository's existing work.
- Keep the skills-only profile unchanged, and prove a real team repository upgrades by adding only the two new skill folders without changing tracked files.
- Update public documentation and refresh the enabled OpenWiki knowledge layer through its own tools.

## Constraints and Design

- Use `shared/sidecar/workflow/skills/onboard/SKILL.md` as the single special case in `render_sidecar()`. Copy it in place of `shared/skills/onboard/` only for the workflow profile. Do not add a general skill override framework.
- The skill writes `.ai-bootstrap/project-context.instructions.md` and one pointer entry in `.ai-bootstrap/MEMORY.md` that tells later sessions to read that file before coding. A `## Team conventions` section records explicit repository rules separately from patterns inferred from code, tests, folder layout, and recent commit subjects; each claim cites a local path or commit. The saved context is derived advice and yields to tracked team guidance. It refuses symlinked or tracked state paths and any resolved destination outside `.ai-bootstrap/` before writing. It reads the team's tracked instructions as authority, uses direct reads, `rg`, and read-only Git history, and leaves all tracked paths untouched. The installer and skill do not create another state root.
- The validator must reject forbidden full-install references in either generated `onboard` copy, including case variants of the wiki name and the full-install memory path. Keep a test that proves the check catches a deliberately inserted forbidden reference.
- Review the control-plane diff with `code`, `architecture`, `security`, `tests`, and `ponytail` profiles. Apply `ponytail` in full mode during implementation. Commit once per completed small plan and push normally. The user decides whether to create a pull request or merge.
- Run required phase and closeout checks in the repository devcontainer or an environment with its full test, lint, and type-check toolchain. The isolated `uv` interpreter is an expected-failure probe for the missing-dependency message, not a closeout environment.
- Do not change the file-protection guard on the current evidence. If a later exact payload reproduces the reported status 2, add a separately planned regression and fix that still denies uncertain writes.

## Phases

- [ ] `2026-10-22_phase-A-validator-pytest-error` — give the validator an actionable missing-dependency failure and test both environments.
- [ ] `2026-10-22_phase-B-sidecar-onboard` — add the safe skill, validation, upgrade test, and sidecar docs.
- [ ] `2026-10-22_phase-C-knowledge-refresh` — refresh OpenWiki and audit live documentation and memory for stale claims.

## Verification

```bash
uv run python scripts/validate_plan_frontmatter.py .claude/plans/sidecar-onboard-and-validator.md .claude/plans/2026-10-22_phase-A-validator-pytest-error.md .claude/plans/2026-10-22_phase-B-sidecar-onboard.md .claude/plans/2026-10-22_phase-C-knowledge-refresh.md
```

## Completion Evidence

The last phase runs the documentation, memory, and LEARN audit across all live-advice surfaces, records the outcome under `## Stale-claims surfaces checked` in its closeout session log, and refreshes OpenWiki through `.claude/skills/knowledge-refresh/SKILL.md`. Each completed phase has its own verification, review, findings, session log, commit, and normal push evidence.
