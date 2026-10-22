---
name: 2026-10-22_phase-B-sidecar-onboard
type: small-plan
parent_plan: sidecar-onboard-and-validator
phase_index: 2
status: planned
closeout_session_log:
---

# Small Plan: Workflow Sidecar Onboard Skill

## Scope

Ship a workflow-only `onboard` skill that records project context in the sidecar's ignored state folder. The public full-install skill remains unchanged. Prove that upgrading an existing team repository adds just the two new skill folders and does not expose personal state to Git.

## Steps

- [ ] **1. Preserve the old-build baseline before sidecar source edits.** Use the generated `9292776` baseline recorded in the big plan, or recreate it from a clean detached checkout at `9292776` with `uv run python scripts/generate_targets.py --all --output "$TMPDIR/before"` (use a fresh writable temporary directory if `TMPDIR` is unset). In a temporary Git repository, commit a team-owned `CLAUDE.md` and `.claude/skills/task-taker/SKILL.md`; install the old `sidecar/workflow` build with `--mode sidecar --profile workflow --source`. Record the baseline commit, pre-upgrade `git status --porcelain --untracked-files=all`, tracked file bytes, and installer output. The existing `tests/test_sidecar_workflow_scenario.py` fixture helpers may perform this setup so the host commit guard does not mistake a fixture commit for a project commit.
- [ ] **2. Add the source skill and one targeted generator choice.** Create `shared/sidecar/workflow/skills/onboard/SKILL.md` with public `onboard` frontmatter. It reads `README.md`, indexes only relevant `docs/`, verifies important claims against source with direct reads and `rg`, and writes only `.ai-bootstrap/project-context.md` plus one `[LEARN:domain]` pointer in `.ai-bootstrap/MEMORY.md`. It checks the repository's tracked instructions first and updates existing state without duplicate pointers. Before writing, it requires `.ai-bootstrap/` to be a real ignored directory, refuses symlinks at the state root or either destination, resolves both destinations inside that root, and refuses any tracked lexical or resolved destination. On refusal it leaves all files unchanged. It contains no `mcp__`, wiki name, `.claude/instructions/`, `.claude/MEMORY.md`, or nested `.claude` Git assumptions. Modify `scripts/generate_targets.py::render_sidecar(target_root: Path, profile: str)` to copy this source only when `profile == "workflow"` and `skill == "onboard"`; preserve the ordinary copying path for all other skills.
- [ ] **3. Update the allowlist and source inventory.** Modify `scripts/runtime_ownership.py::SIDECAR_WORKFLOW_SKILLS` to include `onboard` in sorted order and update its count comment from 24 to 25. Remove the `onboard` deny entry from `shared/sidecar/workflow/skills.txt`. Leave `SIDECAR_SKILLS` unchanged so the skills-only profile cannot install it.
- [ ] **4. Enforce the generated contract.** Modify `scripts/validate_targets.py::validate_sidecar_target(errors: list[str])` or its existing sidecar text validation helper to inspect both generated workflow `onboard/SKILL.md` copies. Reject forbidden tool and full-install references, including case variants of the wiki name, the full-install memory path, and a nested `.claude` Git command. Check that the two generated copies agree and that the skill retains an explicit refusal for symlinked or tracked state targets. Add negative cases to `tests/test_validate_targets.py` or the existing sidecar target cases: inject a forbidden reference in each root separately; inject a mixed-case wiki name; make the two copies differ; and remove the symlink refusal instruction. Each case must fail validation, then restore the generated tree.
- [ ] **5. Test the install and source behavior.** Complete the one-time old-build fixture upgrade from step 1 after regenerating `dist/`, using the new install without `--source`. Assert the only new install rows are `install .agents/skills/onboard` and `install .claude/skills/onboard`; every other managed unit is unchanged. Extend `tests/test_sidecar_workflow_scenario.py` with a repeatable upgrade case that models an installed workflow manifest and exclude block without `onboard`, then installs the current overlay. Assert the team's `CLAUDE.md` and task-taker skill bytes are identical, the new skill is ignored under both roots, `.ai-bootstrap/` remains ignored, and `git status --porcelain --untracked-files=all` is empty. Test that the skills-only profile still has no `onboard`.
- [ ] **6. Update human-authored docs.** Update `README.md` to describe the workflow-only skill and its `.ai-bootstrap/project-context.md` output. Update `docs/sidecar-provider-contract.md` only where its active behavior or inventory claims need correction; leave dated evidence intact. Do not hand-edit generated `dist/` or OpenWiki pages.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_sidecar_workflow_scenario.py tests/test_validate_targets.py -q --tb=short
uv run python scripts/validate_targets.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- In an interactive Claude Code sidecar session in a team repository, invoke `onboard` and inspect only `.ai-bootstrap/project-context.md`, `.ai-bootstrap/MEMORY.md`, and the team's unchanged Git status. Repeat with a state file symlinked to a tracked file and require refusal with the tracked target byte-identical. This checks model behavior that static tests cannot prove.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
