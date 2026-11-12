---
name: 2026-11-12_phase-D-skill-description-cap
type: small-plan
parent_plan: skills-and-instructions-trim
phase_index: 4
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: planned
closeout_session_log:
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---

# Small Plan: 2026-11-12_phase-D-skill-description-cap

## Scope

Claude Code lists every skill's name and description on every turn. With 55 skills, the list overflowed its budget, and some skills lost their descriptions. This phase:
- caps each description at 300 characters, with key trigger words first; `ponytail` and `ponytail-review` are exempt (open decision; approval confirms it);
- adds a validator check that enforces the cap;
- rewrites the 14 descriptions that are too long;
- turns `code-style` and `testing-patterns` into short pointers;
- makes the planner skip `plan-decomposition` in micro-plan mode;
- makes the coder's always-load tier Ponytail only;
- fixes the false "background skills are hidden" wording;
- applies the Codex result from the pre-branch spike.

Covers REQ-004, REQ-005, REQ-006, and REQ-009.

Risk notes:
- `debug-investigator` ships in the default sidecar, so `SIDECAR_SKILLS_PROFILE_SNAPSHOT_SHA256` must be captured again.
- If spike S5 showed that the trimmed list still overflows, the user's decision from that row comes first, and the planner revised this plan before the branch.

## Steps

- [ ] **1. Add the cap check and its tests first.**
  - Owner: `coder`. Files (modify): `scripts/validate_targets.py`, `tests/test_validate_targets.py`, `docs/architecture.md` ("Skill Library Validation Contract"). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - Add `SKILL_DESCRIPTION_MAX_CHARS = 300` and `SKILL_DESCRIPTION_CAP_EXEMPT = frozenset({"ponytail", "ponytail-review"})`.
  - In `shared_skill_integrity_errors`, add `SKILL_DESCRIPTION_TOO_LONG`. It fires when the extracted description plus any `when_to_use` text is longer than the cap. The message names the path and the length.
  - Tests, each with `description_cap` in its name and a temporary skill library:
    - exactly 300 characters passes;
    - 301 fails;
    - an exempt name passes at 500;
    - `when_to_use` text counts.

- [ ] **2. Rewrite the long descriptions.**
  - Owner: `coder`. Files (modify):
    - the `SKILL.md` descriptions of `caveman`, `concept-to-image`, `debug-investigator`, `draw-io`, `html-presentation`, `integration-gate-spike`, `knowledge-refresh`, `literature-review`, `md-to-pdf`, `onboard`, `plan-decomposition`, `prompt-lab`, `rag-auditor`, and `research-critique`;
    - the bodies of `code-style` and `testing-patterns`;
    - `SIDECAR_SKILLS_PROFILE_SNAPSHOT_SHA256` in `tests/test_validate_targets.py`, with its comment naming this phase.
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Each rewrite puts the trigger words a user would say first and stays unique. Bodies stay unchanged, except for the two pointer skills.
  - `code-style` and `testing-patterns` become: read `.claude/instructions/code-standards.instructions.md` or `.claude/instructions/tests.instructions.md`, then run `verify.py fast`. Any rule in their bodies that the policy lacks moves into the policy. The descriptions keep the Codex trigger words, because Codex reaches those policies only through these skills.
  - Check that the `SIDECAR_TEXT_REPLACEMENTS` anchors still match (`_unmatched_sidecar_anchors`).

- [ ] **3. Change the loading rules and the visibility wording.**
  - Owner: `coder`. Files (modify): `shared/agents/planner/prompt.md`, `shared/agents/coder/prompt.md`, `shared/policies/workspace.instructions.md` (Skills section), `README.md` (line 1248). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Planner:
    - read `plan-decomposition/SKILL.md` only in `--mode full-plan`;
    - micro-plan step 1 reads `.claude/templates/plan-big.md` and `.claude/templates/plan-small.md` instead.
  - Coder:
    - Tier 1 is Ponytail only;
    - read `.claude/instructions/tests.instructions.md` when the task adds or changes a test file (Claude Code loads it through `.claude/rules/`);
    - the Tier 2 domain line names `haystack` and `data-and-graph-pitfalls`;
    - keep the pinned "callers, tests, fixtures, config".
  - Workspace and README: both visibility values are listed to the model with their descriptions. `visibility` marks only the intended use.

- [ ] **4. Apply the Codex spike result.**
  - Owner: `coder`. Files (modify): `scripts/generate_targets.py` (`render_codex_config` comment, line 1024), plus any doc that repeats it. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/integration-gate-spike/SKILL.md`.
  - Default outcome (S1 inert): the comment says Codex lists repository skills from `.agents/skills/`, and the `[[skills.config]]` entries only toggle skills Codex already found, citing REPORT.md.
  - If S1 found duplicates, the planner has replaced this step before the branch.

- [ ] **5. Regenerate and refresh this repository.**
  - Owner: orchestrator. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`.

- [ ] **6. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.
  - Focus:
    - each new description still names the cases its skill is for;
    - the exemption is limited to the two pinned files;
    - Codex still has a route to every path-scoped policy;
    - no prompt still loads `code-style` or `testing-patterns` on every task.

## Verification

<!-- Every non-comment line in a `bash`/`sh` block below is a required item:
     a shell command `verify closeout` runs itself, from the repository
     root, and that must exit 0. Never list `verify.py closeout` itself.
     Anything a script cannot run — an interactive probe, a host session, a
     manual inspection — belongs under `## Optional Verification` instead.
     See the Verification Evidence Contract in
     `.claude/instructions/workflow.instructions.md`. -->

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_validate_targets.py -q --tb=short
uv run pytest tests/test_validate_targets.py -q --tb=short -k description_cap
uv run python -I -c 'import sys; sys.path.insert(0, "scripts"); import validate_targets as v; from pathlib import Path; d = [len(v.extract_frontmatter_description(v.extract_frontmatter(p.read_text(encoding="utf-8"))).strip()) for p in sorted(Path("shared/skills").glob("*/SKILL.md"))]; print(len(d), sum(d)); sys.exit(0 if len(d) == 37 and sum(d) <= 10500 else 1)'
test "$(grep -c -F 'code-style/SKILL.md' shared/agents/coder/prompt.md)" = "0"
test "$(grep -c -F 'testing-patterns/SKILL.md' shared/agents/coder/prompt.md)" = "0"
test "$(grep -r -l -F 'hidden helpers' shared README.md | wc -l)" = "0"
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- Fresh Claude Code session (REQ-009). Make an empty folder with `mktemp -d` under the scratchpad, copy `dist/multi-agent/.claude/skills` into its `.claude/skills`, and run `git init` there. From that folder, run `claude -p --debug-file <folder>/claude.log "Reply with OK."`. Then grep `claude.log` for the listing-budget warning text that spike S5 recorded. PASS means no match. The folder has no `settings.json`, so no project hook runs.
- In an interactive Claude Code session in this repository, run `/context`. Record the Skills row and whether any skill is reported as excluded. Then ask "What skills are available?" and check that all 37 names appear with descriptions.
- In a scratch copy of `dist/multi-agent`, run `codex debug prompt-input` with the spike's trust override. Each shipped skill is listed once.

## Closeout Checklist

(The same two-box text as Phase A.)

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record the three pause fields, and create a session log
with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it
does not require final findings, LEARN, DOCUMENT, or a completed closeout.
After the checkpoint commit, it may be pushed as a durable remote backup when
paused-publication invariants pass. It remains unfinished and blocks PR creation
and final closeout.
Keep the big plan `in-progress` with the same `current_phase`. On resume, read
the pause log and Git state, restore this plan to `in-progress`, and continue
this same phase without creating another small plan.
