---
name: 2026-10-22_phase-B-sidecar-onboard
type: small-plan
parent_plan: sidecar-onboard-and-validator
phase_index: 2
status: complete
closeout_session_log: .claude/session_logs/2026-10-22_sidecar-onboard-and-validator-phase-B.md
---

# Small Plan: Workflow Sidecar Onboard Skill

## Scope

Ship a workflow-only `onboard` skill that records project context and team conventions in the sidecar's ignored state folder. The public full-install skill remains unchanged. Prove that upgrading an existing team repository adds just the two new skill folders and does not expose personal state to Git.

## Steps

- [x] **1. Preserve the old-build baseline before sidecar source edits.** Use the generated `9292776` baseline recorded in the big plan, or recreate it from a clean detached checkout at `9292776` with `uv run python scripts/generate_targets.py --all --output "$TMPDIR/before"` (use a fresh writable temporary directory if `TMPDIR` is unset). In a temporary Git repository, commit a team-owned `CLAUDE.md` and `.claude/skills/task-taker/SKILL.md`; install the old `sidecar/workflow` build with `--mode sidecar --profile workflow --source`. Record the baseline commit, pre-upgrade `git status --porcelain --untracked-files=all`, tracked file bytes, and installer output. The existing `tests/test_sidecar_workflow_scenario.py` fixture helpers may perform this setup so the host commit guard does not mistake a fixture commit for a project commit.
- [x] **2. Add the source skill and one targeted generator choice.** Create `shared/sidecar/workflow/skills/onboard/SKILL.md` with public `onboard` frontmatter. It reads `README.md`, indexes relevant `docs/`, checks the repository's tracked instructions first, and verifies important claims against source. It writes only `.ai-bootstrap/project-context.instructions.md` plus one `[LEARN:domain]` pointer in `.ai-bootstrap/MEMORY.md`; the pointer explicitly tells future sessions to read the context file before coding and to follow tracked team guidance when it differs. Update existing state without duplicate pointers. Before writing, require `.ai-bootstrap/` to be a real ignored directory, refuse symlinks at the state root or either destination, resolve both destinations inside that root, and refuse any tracked lexical or resolved destination. On refusal leave all files unchanged. The skill contains no `mcp__`, wiki name, `.claude/instructions/`, `.claude/MEMORY.md`, or nested `.claude` Git assumptions. Modify `scripts/generate_targets.py::render_sidecar(target_root: Path, profile: str)` to copy this source only when `profile == "workflow"` and `skill == "onboard"`; preserve the ordinary copying path for all other skills.
- [x] **3. Discover and record team conventions.** In the new skill, use direct reads and `rg` to inspect tracked guidance, `README.md`, relevant `docs/`, formatting and lint configuration, the tracked folder and file layout, representative source files, nearby tests and fixtures, and repeated usage patterns. Use read-only `git log` on a bounded set of recent commits to inspect commit subjects; use more nearby examples for the area being changed. In `.ai-bootstrap/project-context.instructions.md`, require a `## Team conventions` section covering supported practices for feature placement and extension points, folder and file placement, variable/function/class/file naming, imports and public interfaces, configuration and dependencies, error handling and logging, tests and fixtures, documentation, build and test commands, and commit message style. Record branch or review practices only where tracked guidance or history supports them. Separate explicit team rules from patterns inferred from repeated examples. Cite paths or commit hashes, note meaningful exceptions or conflicts, and say when evidence is too thin to infer a convention. Mark the section as derived advice beneath tracked team guidance. End with a short checklist for making a change that fits this repository. Keep the section concise and useful rather than copying whole files or treating a one-off example as a rule.
- [x] **4. Update the allowlist and source inventory.** Modify `scripts/runtime_ownership.py::SIDECAR_WORKFLOW_SKILLS` to include `onboard` in sorted order and update its count comment from 24 to 25. Remove the `onboard` deny entry from `shared/sidecar/workflow/skills.txt`. Leave `SIDECAR_SKILLS` unchanged so the skills-only profile cannot install it.
- [x] **5. Enforce the generated contract.** Modify `scripts/validate_targets.py::validate_sidecar_target(errors: list[str])` or its existing sidecar text validation helper to inspect both generated workflow `onboard/SKILL.md` copies. Reject forbidden tool and full-install references, including case variants of the wiki name, the full-install memory path, and a nested `.claude` Git command. Check that the two generated copies agree and that the skill retains explicit symlink/tracked-target refusals, the `## Team conventions` output contract, and the memory pointer's read-before-coding instruction. Add negative cases to `tests/test_validate_targets.py` or the existing sidecar target cases: inject a forbidden reference in each root separately; inject a mixed-case wiki name; make the two copies differ; remove the symlink refusal instruction; remove the conventions output contract; and remove the pointer read instruction. Each case must fail validation, then restore the generated tree.
- [x] **6. Test the install and source behavior.** Complete the one-time old-build fixture upgrade from step 1 after regenerating `dist/`, using the new install without `--source`. Assert the only new install rows are `install .agents/skills/onboard` and `install .claude/skills/onboard`; every other managed unit is unchanged. Extend `tests/test_sidecar_workflow_scenario.py` with a repeatable upgrade case that models an installed workflow manifest and exclude block without `onboard`, then installs the current overlay. Assert the team's `CLAUDE.md` and task-taker skill bytes are identical, the new skill is ignored under both roots, `.ai-bootstrap/` remains ignored, and `git status --porcelain --untracked-files=all` is empty. Test that the skills-only profile still has no `onboard`.
- [x] **7. Update human-authored docs.** Update `README.md` to describe the workflow-only skill, its `.ai-bootstrap/project-context.instructions.md` output, and the evidence-based team conventions section. Explain that the workflow rule makes Claude Code read the memory pointer, while Codex receives skills and state only: later Codex sessions must invoke `onboard` or explicitly read the memory pointer and context file. Update `docs/sidecar-provider-contract.md` only where its active behavior or inventory claims need correction; leave dated evidence intact. Do not hand-edit generated `dist/` or OpenWiki pages.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_sidecar_workflow_scenario.py tests/test_validate_targets.py -q --tb=short
uv run python scripts/validate_targets.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- The client fixture is required behavioral acceptance before claiming convention discovery works. In an interactive Claude Code sidecar session in a local team-repository fixture, invoke `onboard` and inspect `.ai-bootstrap/project-context.instructions.md`, `.ai-bootstrap/MEMORY.md`, and the team's unchanged Git status. Give the fixture consistent variable and function names, a clear folder and test layout, several commit subjects with one outlier, and a tracked instruction that takes precedence over an observed pattern. Require the `## Team conventions` section to cite those examples, distinguish written rules from inferred patterns, and avoid claiming the outlier as a rule; require the memory pointer to tell a later session to read the context file before coding. Repeat with a state file symlinked to a tracked file and require refusal with the tracked target byte-identical. Record the output and result in the session log. If no suitable client is available, record this behavior as unverified and do not claim the phase's behavioral acceptance is complete.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`.

- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
