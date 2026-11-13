---
name: 2026-11-12_phase-C-skill-set
type: small-plan
parent_plan: skills-and-instructions-trim
phase_index: 3
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: in-progress
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

# Small Plan: 2026-11-12_phase-C-skill-set

## Scope

Claude Code lists every skill's name and description on every turn. With 55 skills, the list overflowed its budget, and some skills lost their descriptions. This phase takes the shipped skills to 37, as exploration section 4 decided:

| Change | Skills |
|---|---|
| Remove (9) | `review-api`, `run-tests`, `refactor`, `pdf`, `caveman-compress`, `dataclass-classvar-constant`, `domain-type-placement`, `graph-schema-compat-migration`, `extraction-metadata-sourcing` |
| Merge into `haystack` | `pipeline-patterns`, `haystack-conditional-router`, `docling-haystack`, `ollama-chat-generator` |
| Merge into `data-and-graph-pitfalls` | `pandas-nan-bool-coercion`, `networkx-igraph-graphml-interop`, `pyvis-xss-testing`, `csv-driven-integration-tests` |
| Merge into `bentoml-service` | `deploy-service` (the Codex deployment fallback now points there) |
| Become one rule line each in the tests policy | `context-manager-testing`, `test-helper-public-api` |

`create-feature` loses its repeated Hydra section.

The phase also:
- caps each skill's listing text (description plus `when_to_use`) at 300 characters, with trigger words first; `ponytail` and `ponytail-review` are exempt (big plan Decision 1);
- adds a validator check that enforces the cap;
- rewrites the 14 long descriptions among kept skills;
- turns `code-style` and `testing-patterns` into short pointers;
- makes the planner read `plan-decomposition` only in full-plan mode;
- makes the coder's always-load tier Ponytail only;
- applies the Codex result from the pre-branch spike.

Covers REQ-003, REQ-004, REQ-005, REQ-006, and REQ-009. The phase owns the files its steps list; a file may be revisited after a failing-first test or a review finding.

Risk notes:
- Section 6 cuts stay out: `code-style`, `testing-patterns`, `debug-investigator`, and `gradio-streamlit` remain.
- A merged skill that the sidecar workflow profile cannot ship goes into `shared/sidecar/workflow/skills.txt` with a reason (DA-8). Its moved content is not edited to fit.
- `debug-investigator` ships in the default sidecar, so the profile snapshot hash is captured again.
- The big plan's spike table says how S1 and S5 results change this plan. The planner applies any revision before the branch.
- Phase B already removed the workspace policy's skill list and fixed its "hidden" wording, so this phase does not edit that file.
- This phase's self-refresh runs Phase A's refusals. The 20 retired names are in this repository's `.claude/bootstrap-root/.agents/skills/`, so they are deleted, not refused.

## Steps

- [ ] **1. Change the validator first.**
  - Owner: `coder`. File (modify): `scripts/validate_targets.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Add `SKILL_DESCRIPTION_MAX_CHARS = 300` and `SKILL_DESCRIPTION_CAP_EXEMPT = frozenset({"ponytail", "ponytail-review"})`.
  - Add `def skill_listing_length(frontmatter: str) -> int`. It returns the stripped length of `description` plus the stripped length of `when_to_use`, reusing the block-scalar logic of `extract_frontmatter_description`. It is the only length definition, used by the cap check and by the total in Verification.
  - In `shared_skill_integrity_errors`, add `SKILL_DESCRIPTION_TOO_LONG` for a non-exempt skill whose `skill_listing_length` exceeds the cap. The message names the path and the length.
  - Set `CODEX_POLICY_SKILL_FALLBACKS["deployment.instructions.md"] = "bentoml-service"`.
  - Update the comment near line 9371 that names the retired skills.
  - Failing-first evidence: run `uv run python scripts/validate_targets.py` against the unchanged 55-skill library, and record the 24 `SKILL_DESCRIPTION_TOO_LONG` errors. After Step 2, record the 14 that remain among kept skills.

- [ ] **2. Remove, merge, and fold the skill folders.**
  - Owner: `coder`. Files:
    - delete the nine removed skills, the eight merged sources, `deploy-service`, `context-manager-testing`, and `test-helper-public-api`;
    - create `shared/skills/haystack/SKILL.md` with `references/{pipelines,conditional-router,docling,ollama-chat}.md`;
    - create `shared/skills/data-and-graph-pitfalls/SKILL.md` with `references/{pandas-nan-bool,graphml-interop,pyvis-xss,csv-driven-tests,csv-case-study}.md`;
    - modify `shared/skills/bentoml-service/SKILL.md`, `shared/skills/setup-project/SKILL.md` (line 32), `shared/skills/create-feature/SKILL.md`.
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Merged skills:
    - `visibility: public`;
    - listing text of 300 characters or less with trigger words first. Example for `haystack`: "Haystack 2.x pipelines: component wiring, ConditionalRouter routes, Docling PDF conversion, and OllamaChatGenerator setup. Use when building, debugging, or testing a Haystack pipeline or one of these components.";
    - the body is one short paragraph per topic, naming its reference file and when to read it;
    - the source bodies move without content changes. Rename old skill-name headings, and make every `references/...` path resolve. This includes the CSV body's two `references/case-study.md` links (lines 152 and 170 of the source), which become `references/csv-case-study.md`.
  - `bentoml-service`: add the deploy body as `## Deploy`, and drop its two `deploy-service` mentions (lines 30 and 104).
  - `create-feature`: Phase 1A becomes one line that points to `.claude/skills/hydra-config/SKILL.md`.

- [ ] **3. Rewrite the long descriptions and the two pointer skills.**
  - Owner: `coder`. Files (modify): the `SKILL.md` of `caveman`, `concept-to-image`, `debug-investigator`, `draw-io`, `html-presentation`, `integration-gate-spike`, `knowledge-refresh`, `literature-review`, `md-to-pdf`, `onboard`, `plan-decomposition`, `prompt-lab`, `rag-auditor`, `research-critique`, `code-style`, and `testing-patterns`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Change only the 14 descriptions. Each puts the trigger words a user would say first and stays unique.
  - `code-style` and `testing-patterns`:
    - each body becomes "read `.claude/instructions/code-standards.instructions.md` (or `tests.instructions.md`), then run `verify.py fast`";
    - each description keeps the Codex trigger words, because Codex reaches those policies only through these skills;
    - list any rule their old bodies held that the policy lacks; Step 4 moves it.

- [ ] **4. Add the moved rules to the policies.**
  - Owner: `coder`. Files (modify): `shared/policies/tests.instructions.md`, `shared/policies/code-standards.instructions.md`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Tests policy: one rule line for the context-manager lesson, one for the test-helper public-API lesson, and any Step 3 rule from `testing-patterns`.
  - Code standards: any Step 3 rule from `code-style`.

- [ ] **5. Update the lists, prompts, docs, and Codex comment.**
  - Owner: `coder` (`documenter` for `README.md` and `docs/`). Files (modify):
    - `scripts/runtime_ownership.py`: `SIDECAR_WORKFLOW_SKILLS` drops `caveman-compress`, `pdf`, `review-api`, `pipeline-patterns`, and `csv-driven-integration-tests`, and adds `haystack` and `data-and-graph-pitfalls`; keep it sorted, and fix the "25" comment;
    - `shared/sidecar/workflow/skills.txt`: remove the `run-tests`, `refactor`, and `deploy-service` lines;
    - `shared/agents/coder/workflow-prompt.md`, `shared/agents/planner/workflow-prompt.md`;
    - `shared/agents/coder/prompt.md`: Tier 1 is Ponytail only; read `.claude/instructions/tests.instructions.md` when the task adds or changes a test file (Claude Code loads it through `.claude/rules/`); the Tier 2 domain line names `haystack` and `data-and-graph-pitfalls`; line 70 drops `refactor`; keep "callers, tests, fixtures, config";
    - `shared/agents/planner/prompt.md`: read `plan-decomposition/SKILL.md` only in `--mode full-plan`; micro-plan step 1 reads `.claude/templates/plan-big.md` and `.claude/templates/plan-small.md`;
    - `shared/agents/documenter/prompt.md`: the line-13 path becomes `.claude/skills/haystack/SKILL.md`;
    - `README.md`: the "Most Important Skills" catalog, and the line-1248 "hidden helpers" wording;
    - `docs/smoke-tests.md` (line 276);
    - `docs/architecture.md`: a cap bullet in "Skill Library Validation Contract", naming the listing-length definition;
    - `scripts/generate_targets.py`, the `render_codex_config` comment at line 1024:
      - when S1 parsed each shipped skill once from `.agents/skills/`, the comment says Codex lists repository skills from `.agents/skills/` and that `[[skills.config]]` entries only toggle skills Codex already found, citing REPORT.md;
      - when S1 ended in error, unsupported, or no-entry, it says the effect of the entries was not observed and cites REPORT.md;
      - also fix any doc that repeats the old claim.
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/integration-gate-spike/SKILL.md` (Codex comment), `.claude/skills/documentation/SKILL.md`.
  - Leave `docs/evidence/` unchanged.

- [ ] **6. Update the tests.**
  - Owner: `coder`. Files: `tests/test_validate_targets.py` (modify); `tests/test_caveman_compress_detect.py` (delete). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - Point the pandas test (about line 3350) and the pyvis test (about line 3607) at `shared/skills/data-and-graph-pitfalls/references/pandas-nan-bool.md` and `.../pyvis-xss.md`.
  - Delete `test_run_tests_e2e_step_propagates_failure_instead_of_masking_it` and the `run-tests` entry in `DEPRECATION_CHECK_STEPS`.
  - Add `test_merged_skills_have_their_references`: both merged skills exist with every `references/` file their `SKILL.md` names. The absence of retired names is checked in Verification, not here, so a later re-add stays possible.
  - Add tests with `description_cap` in their names, using a temporary skill library:
    - exactly 300 characters passes;
    - 301 fails;
    - an exempt name passes at 500;
    - `when_to_use` text counts toward `skill_listing_length`.
  - Add tests with `loading_rules` in their names, reading the prompt sections:
    - the planner's `### Micro-Plan Mode (--mode micro-plan)` names both templates and not `plan-decomposition/SKILL.md`;
    - its full-plan path names `plan-decomposition/SKILL.md`;
    - the coder's `## Mandatory Skills-First Rule` Tier 1 names only `ponytail/SKILL.md` and holds the conditional tests-policy read.
  - Capture `SIDECAR_SKILLS_PROFILE_SNAPSHOT_SHA256` again, with its comment naming this phase.
  - Confirm `_unmatched_sidecar_anchors` is still empty.

- [ ] **7. Regenerate and refresh this repository.**
  - Owner: orchestrator. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`.
  - Acceptance:
    - the installer does not refuse;
    - `.claude/skills/` then has 38 folders (37 plus the third-party `openwiki`).

- [ ] **8. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.
  - Focus:
    - moved content matches the sources;
    - each new description still names its cases;
    - the exemption covers only the two pinned files;
    - one length definition serves the cap and the total;
    - no live surface names a retired skill;
    - the Codex fallback map still covers all five path-scoped policies;
    - the sidecar workflow set equals the public skills minus `skills.txt`;
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
uv run pytest tests/test_validate_targets.py tests/test_sidecar_install.py tests/test_sidecar_update.py tests/test_sidecar_workflow_scenario.py -q --tb=short
uv run pytest tests/test_validate_targets.py -q --tb=short -k "description_cap or loading_rules or merged_skills"
test ! -e tests/test_caveman_compress_detect.py
uv run python -I -c 'import pathlib, sys; want = {"shared/skills": 37, "dist/multi-agent/.claude/skills": 37, "dist/multi-agent/.agents/skills": 37, ".claude/skills": 38}; got = {r: sum(1 for p in pathlib.Path(r).iterdir() if p.is_dir() and not p.is_symlink()) for r in want}; print(got); sys.exit(0 if got == want else 1)'
uv run python -I -c 'import sys; sys.path.insert(0, "scripts"); import validate_targets as v; from pathlib import Path; d = {p.parent.name: v.skill_listing_length(v.extract_frontmatter(p.read_text(encoding="utf-8"))) for p in sorted(Path("shared/skills").glob("*/SKILL.md"))}; long = sorted(n for n, k in d.items() if k > v.SKILL_DESCRIPTION_MAX_CHARS and n not in v.SKILL_DESCRIPTION_CAP_EXEMPT); print(len(d), sum(d.values()), long); sys.exit(0 if len(d) == 37 and sum(d.values()) <= 10500 and not long else 1)'
uv run python -I -c 'import pathlib, re, sys; pat = re.compile(sys.argv[1].encode()); roots = [pathlib.Path(a) for a in sys.argv[2:]]; bad = [str(r) for r in roots if not r.exists()] + [str(p) for r in roots if r.exists() for p in ([r] if r.is_file() else sorted(r.rglob("*"))) if p.is_file() and "__pycache__" not in p.parts and pat.search(p.read_bytes())]; sys.exit("missing or matching: " + ", ".join(bad) if bad else 0)' 'skills/(review-api|run-tests|refactor|pdf|caveman-compress|dataclass-classvar-constant|domain-type-placement|graph-schema-compat-migration|extraction-metadata-sourcing|pipeline-patterns|haystack-conditional-router|docling-haystack|ollama-chat-generator|pandas-nan-bool-coercion|networkx-igraph-graphml-interop|pyvis-xss-testing|csv-driven-integration-tests|deploy-service|context-manager-testing|test-helper-public-api)/|`(review-api|run-tests|caveman-compress|pipeline-patterns|csv-driven-integration-tests|deploy-service|pandas-nan-bool-coercion|pyvis-xss-testing|networkx-igraph-graphml-interop|haystack-conditional-router|docling-haystack|ollama-chat-generator|context-manager-testing|test-helper-public-api|dataclass-classvar-constant|domain-type-placement|graph-schema-compat-migration|extraction-metadata-sourcing)`' shared scripts README.md docs/smoke-tests.md docs/architecture.md docs/target-mapping.md
grep -q -F '"deployment.instructions.md": "bentoml-service"' scripts/validate_targets.py
grep -q -F 'haystack/SKILL.md' shared/agents/documenter/prompt.md
test "$(grep -c -F 'code-style/SKILL.md' shared/agents/coder/prompt.md)" = "0"
test "$(grep -c -F 'testing-patterns/SKILL.md' shared/agents/coder/prompt.md)" = "0"
test "$(grep -c -F '`refactor`' shared/agents/coder/prompt.md)" = "0"
test "$(grep -c -F 'Always read `plan-decomposition/SKILL.md`' shared/agents/planner/prompt.md)" = "0"
test "$(grep -c -F 'Skills are sourced from the shared .claude basis' scripts/generate_targets.py)" = "0"
test "$(grep -c -F 'hidden helpers' README.md)" = "0"
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- Fresh Claude Code listing (REQ-009), using spike S5's method. In a fresh `mktemp -d` folder outside the checkout, copy `dist/multi-agent/.claude/skills` into `<tree>/.claude/skills`. From an empty working folder with no settings, run `claude --bare -p --add-dir <tree> --debug-file <log> "Reply with OK."`. When `--bare` cannot authenticate, use `--setting-sources project` instead. Grep `<log>` for the positive-control warning text that S5 recorded. PASS means no match while the control text is known. Record inconclusive when S5 had no working control.
- In an interactive Claude Code session in this repository, run `/context` and `/doctor`. Record the Skills row size and `/doctor`'s listing-cost estimate. Then ask "What skills are available?" and check that all 37 names appear with descriptions and no retired name does.
- In a fresh tree built like spike S1, run `codex debug prompt-input` with the isolated `HOME` and `CODEX_HOME`, and parse the entries. Each shipped skill is listed once.

## Closeout Checklist

Run the numbered CLOSEOUT sequence in `.claude/instructions/closeout.instructions.md` in order. Tick both boxes at its step 2. Later steps bind this file's bytes, so do not edit this file after step 2.

- [ ] Step 1: documentation updated, or skipped as pure-internal with a reason
- [ ] Step 2: this plan set to `status: complete` with `closeout_session_log`, every step ticked, and LEARN entries or the no-lessons marker recorded

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
