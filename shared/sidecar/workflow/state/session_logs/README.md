# session_logs/

A short log of what you did and why, one file per task, written with the
template under `.claude/templates/`. It is a record for your own future
sessions, not a deliverable anyone else reads.

This folder is personal and Git-ignored. It never shows up in `git
status`, is never committed, and survives a pull, a merge, or a branch
switch. Removing the sidecar keeps this folder unless you explicitly
choose to remove your personal state along with it.

Because this folder is Git-ignored, `git clean -x` (and `git clean -fdx`)
deletes it along with every other ignored file, and there is no automatic
backup. Run `install_bootstrap.py <repo> --backup-state` to copy this
folder into the Git directory first, a location `git clean` never
touches.
