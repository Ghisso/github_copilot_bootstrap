# plans/

Your own plans for this repository go here: a big plan for multi-phase
work, a small plan for one phase, written with the templates under
`.claude/templates/`. Use a plan when a task spans several files or
several decisions; skip it for a small, obvious fix.

This folder is personal and Git-ignored. It never shows up in `git
status`, is never committed, and survives a pull, a merge, or a branch
switch. Removing the sidecar keeps this folder unless you explicitly
choose to remove your personal state along with it.

Because this folder is Git-ignored, `git clean -x` (and `git clean -fdx`)
deletes it along with every other ignored file, and there is no automatic
backup. Run `install_bootstrap.py <repo> --backup-state` to copy this
folder into the Git directory first, a location `git clean` never
touches.
