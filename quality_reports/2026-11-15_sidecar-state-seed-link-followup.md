# Follow-up (open): sidecar state seed written through a linked subfolder

Found on 2026-11-15, after the big plan `skills-and-instructions-trim` was complete, while checking whether its copy-safety work also covers the sidecar install. The user chose to record it now and fix it later in a separate plan.

When the fix lands, also record it, or close it, in `docs/target-mapping.md` ("Recorded follow-ups"). That list could not be edited here, because a commit on the completed branch needs a new plan phase.

## Finding

The `workflow` sidecar profile adds its missing state seed files on every refresh: `MEMORY.md`, and a `README.md` in `plans`, `explorations`, `session_logs`, and `quality_reports`. `_seed_state_file` in `scripts/sidecar_overlay.py` checks only the seed path itself (`exists()` or `is_symlink()`), then runs `mkdir` and `shutil.copy2`.

When a subfolder inside `.ai-bootstrap/` is a link to a folder outside the project, and its `README.md` is missing, the refresh creates that `README.md` in the outside folder.

## Evidence

Scratch reproduction, outside the real repositories:
1. Install the workflow sidecar into a fresh team repository.
2. Replace `.ai-bootstrap/plans` with a link to an empty folder outside the repository.
3. Run `install_sidecar(repo, dist/sidecar/workflow, profile="workflow")` again.

Result: exit 0, and `README.md` is created in the outside folder.

The same run found these shapes safe, with nothing outside changed:
- a folder holding a same-named link at an installed file unit (`.claude/rules/ai-bootstrap-workflow.md`): left alone;
- a FIFO at that path: left alone;
- a link at `SKILL.md` inside an installed skill: handled;
- `.claude/skills` as a link to an outside folder: refused;
- `.claude/rules` as a regular file: refused.

## Severity

Low.
- It only creates a missing file. It never overwrites or deletes anything.
- Only the person's own link can cause it. The sidecar refuses to run when the team tracks anything under `.ai-bootstrap/`, and it refuses a state root that is itself a link.
- The `skills` profile has no state folder, so it is not affected.

## Proposed fix

- In `_seed_state_file`, skip with a warning a seed when its path, or any folder between the state root and it, is a link or not a real folder. The full install already does this for an unsafe state README (`_unsafe_destination` in `scripts/install_bootstrap.py`).
- Add a sidecar test that plants a linked state subfolder and checks that nothing outside the repository changes.
- Consider one small plan for this and the priority follow-up in `docs/target-mapping.md`, which covers `state-sync.sh`'s own writes. Both are writes in state areas that are not checked for links.
