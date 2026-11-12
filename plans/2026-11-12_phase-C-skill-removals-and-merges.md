---
name: 2026-11-12_phase-C-skill-removals-and-merges
type: small-plan
parent_plan: skills-and-instructions-trim
phase_index: 3
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

# Small Plan: 2026-11-12_phase-C-skill-removals-and-merges

## Scope

This phase takes the shipped skills from 55 to 37, as exploration section 4 decided:

| Change | Skills |
|---|---|
| Remove (9) | `review-api`, `run-tests`, `refactor`, `pdf`, `caveman-compress`, `dataclass-classvar-constant`, `domain-type-placement`, `graph-schema-compat-migration`, `extraction-metadata-sourcing` |
| Merge into `haystack` | `pipeline-patterns`, `haystack-conditional-router`, `docling-haystack`, `ollama-chat-generator` |
| Merge into `data-and-graph-pitfalls` | `pandas-nan-bool-coercion`, `networkx-igraph-graphml-interop`, `pyvis-xss-testing`, `csv-driven-integration-tests` |
| Merge into `bentoml-service` | `deploy-service` (the Codex deployment fallback now points there) |
| Become one rule line each in the tests policy | `context-manager-testing`, `test-helper-public-api` |

`create-feature` loses its repeated Hydra section. Every list that names a changed skill is updated.

The description cap is not enforced yet; Phase D adds it. The two new skills already get descriptions of 300 characters or less. Covers REQ-003.

Risk notes:
- Section 6 cuts stay out: `code-style`, `testing-patterns`, `debug-investigator`, and `gradio-streamlit` remain.
- A merged skill that the sidecar workflow profile cannot ship goes into `shared/sidecar/workflow/skills.txt` with a reason (DA-8). Its moved content is not edited to fit.

## Steps

- [ ] **1. Update the tests first.**
  - Owner: `coder`. Files: `tests/test_validate_targets.py` (modify); `tests/test_caveman_compress_detect.py` (delete). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - Point the pandas test (about line 3350) and the pyvis test (about line 3607) at the new files `shared/skills/data-and-graph-pitfalls/references/pandas-nan-bool.md` and `.../references/pyvis-xss.md`.
  - Delete `test_run_tests_e2e_step_propagates_failure_instead_of_masking_it` and the `run-tests` entry in `DEPRECATION_CHECK_STEPS`.
  - Add `test_retired_skills_stay_removed`:
    - the 20 old names are absent from `shared/skills/`;
    - `haystack` and `data-and-graph-pitfalls` exist with their `references/` files.

- [ ] **2. Remove the nine skills and every list entry.**
  - Owner: `coder`. Files:
    - the nine `shared/skills/<name>/` folders (delete);
    - `scripts/runtime_ownership.py` (`SIDECAR_WORKFLOW_SKILLS`, and the "25" comment);
    - `shared/sidecar/workflow/skills.txt`;
    - `shared/agents/coder/workflow-prompt.md`, `shared/agents/planner/workflow-prompt.md`;
    - `shared/agents/coder/prompt.md` (line 70 names `refactor`);
    - `shared/policies/workspace.instructions.md` (line 157 list);
    - `scripts/validate_targets.py` (the comment near line 9371);
    - `README.md` ("Most Important Skills"), `docs/smoke-tests.md` (line 276).
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Leave `docs/evidence/` unchanged; it is a dated record.

- [ ] **3. Merge the four Haystack skills into `haystack`.**
  - Owner: `coder`. Files: create `shared/skills/haystack/SKILL.md` and `shared/skills/haystack/references/{pipelines,conditional-router,docling,ollama-chat}.md`; delete the four source folders; modify `shared/agents/documenter/prompt.md` (line 13 path), `scripts/runtime_ownership.py`, and the two `workflow-prompt.md` lists. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - `SKILL.md`:
    - `visibility: public`;
    - a description of 300 characters or less with trigger words first, for example: "Haystack 2.x pipelines: component wiring, ConditionalRouter routes, Docling PDF conversion, and OllamaChatGenerator setup. Use when building, debugging, or testing a Haystack pipeline or one of these components.";
    - the body is one short paragraph per topic, naming its reference file and when to read it.
  - Move each source body without content changes. Rename old skill-name headings, and fix links so `references/...` paths resolve.
  - In `SIDECAR_WORKFLOW_SKILLS`, replace `pipeline-patterns` with `haystack`, keeping the tuple sorted.

- [ ] **4. Merge the four data and graph skills into `data-and-graph-pitfalls`.**
  - Owner: `coder`. Files: create `shared/skills/data-and-graph-pitfalls/SKILL.md` and `references/{pandas-nan-bool,graphml-interop,pyvis-xss,csv-driven-tests,csv-case-study}.md`; delete the four source folders; modify `scripts/runtime_ownership.py` and the two `workflow-prompt.md` lists. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Use the same rules as Step 3. In `SIDECAR_WORKFLOW_SKILLS`, replace `csv-driven-integration-tests` with `data-and-graph-pitfalls`.

- [ ] **5. Fold `deploy-service` into `bentoml-service`.**
  - Owner: `coder`. Files: modify `shared/skills/bentoml-service/SKILL.md` (lines 30 and 104 name `deploy-service`), `shared/skills/setup-project/SKILL.md` (line 32), `scripts/validate_targets.py` (`CODEX_POLICY_SKILL_FALLBACKS["deployment.instructions.md"] = "bentoml-service"`), `shared/sidecar/workflow/skills.txt`, and `README.md`; delete `shared/skills/deploy-service/`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Add the deploy body as a `## Deploy` section, and keep the description at 300 characters or less.

- [ ] **6. Move the two test lessons and trim `create-feature`.**
  - Owner: `coder`. Files: modify `shared/policies/tests.instructions.md` and `shared/skills/create-feature/SKILL.md`; delete `shared/skills/context-manager-testing/` and `shared/skills/test-helper-public-api/`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Add one rule line for each lesson to the tests policy.
  - Replace create-feature's Phase 1A Hydra block with one line that points to `.claude/skills/hydra-config/SKILL.md`.

- [ ] **7. Regenerate and refresh this repository.**
  - Owner: orchestrator. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`.
  - Acceptance: `.claude/skills/` has 38 folders (37 plus the third-party `openwiki`).

- [ ] **8. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.
  - Focus:
    - moved content matches the sources;
    - no live surface names a retired skill;
    - the Codex fallback map still covers all five path-scoped policies;
    - the sidecar workflow set equals the public skills minus `skills.txt`.

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
uv run pytest tests/test_validate_targets.py tests/test_sidecar_install.py tests/test_sidecar_update.py tests/test_sidecar_workflow_scenario.py -q --tb=short
test ! -e tests/test_caveman_compress_detect.py
test "$(ls -d shared/skills/*/ | wc -l)" = "37"
test "$(ls -d dist/multi-agent/.claude/skills/*/ | wc -l)" = "37"
test "$(ls -d dist/multi-agent/.agents/skills/*/ | wc -l)" = "37"
test "$(ls -d .claude/skills/*/ | wc -l)" = "38"
test "$(grep -r -l -E -e 'skills/(review-api|run-tests|refactor|pdf|caveman-compress|dataclass-classvar-constant|domain-type-placement|graph-schema-compat-migration|extraction-metadata-sourcing|pipeline-patterns|haystack-conditional-router|docling-haystack|ollama-chat-generator|pandas-nan-bool-coercion|networkx-igraph-graphml-interop|pyvis-xss-testing|csv-driven-integration-tests|deploy-service|context-manager-testing|test-helper-public-api)/' -e '`(review-api|run-tests|caveman-compress|pipeline-patterns|csv-driven-integration-tests|deploy-service|pandas-nan-bool-coercion|pyvis-xss-testing|networkx-igraph-graphml-interop|haystack-conditional-router|docling-haystack|ollama-chat-generator|context-manager-testing|test-helper-public-api|dataclass-classvar-constant|domain-type-placement|graph-schema-compat-migration|extraction-metadata-sourcing)`' shared scripts README.md docs/smoke-tests.md docs/architecture.md docs/target-mapping.md | wc -l)" = "0"
grep -q -F '"deployment.instructions.md": "bentoml-service"' scripts/validate_targets.py
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- In a fresh Claude Code session in this repository, ask "What skills are available?". Confirm that `haystack` and `data-and-graph-pitfalls` appear and no retired name does.

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
