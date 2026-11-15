# Review findings, round 2: skills-and-instructions-trim

Reviewed on 2026-11-15 against `e1bf94f` (branch `skills-and-instructions-trim_implementation`, after Phases E to G). Sources: a second independent review by another agent, which the user shared in the conversation (it was not saved as a file), and the main agent's own reproductions below. Each finding was checked against the code.

This report is the "Record new findings in a quality report" input for the second reopen of the big plan (`.claude/instructions/plan-lifecycle.instructions.md`, "Reopening a completed big plan"). Completed phases, logs, findings reports, and receipts stay unchanged. Round 1 is `2026-11-14_skills-and-instructions-trim-review-claude.md` (R1 to R23).

**Result: hold before the PR.** Phase F's symlink guarantee has a hole, and its documentation claims more than the code does.

## Evidence the main agent ran itself

- Folder-over-file runs. Each one used `_installed_consumer` from `tests/test_install_bootstrap.py`, which does one real install into a scratch Git repository. Then a real folder replaced a generated file, with a link inside it, under the same name, pointing to an outside sentinel file. Then a second, ordinary refresh ran:

  | Folder in place of a generated file | Sentinel overwritten | Installer result |
  |---|---|---|
  | `.devcontainer/Dockerfile` | yes | exit 0, `install-bootstrap: done` |
  | `.claude/plans/README.md` | yes | exit 0, `install-bootstrap: done` |
  | `.claude/bootstrap-root/CLAUDE.md` | yes | exit 0, `install-bootstrap: done` |
  | `CLAUDE.md`, with the link tracked by Git | yes | exit 1, after the write |
  | `.claude/agents/coder.md` (control) | no | exit 0 |
  | `CLAUDE.md`, untracked link (control) | no | exit 0 |

  The two controls stay safe only because the obsolete-file cleanup in `copy_generated_tree` unlinks the planted link before the copy. That cleanup skips `.devcontainer/` (not a root adapter), consumer state, `.claude/bootstrap-root/`, and tracked root-adapter paths.
- Whole-folder history check of `img-classification`: each of its 52 skill folders has the complete file list and contents of the same skill's folder at one bootstrap commit, under some layout (`shared/skills/`, `skills/`, or the AI-state `bootstrap-root/.agents/skills/`). The other agent reached the same result for the 22 folders the new bootstrap does not ship.
- Local consumers, as examples only (the user has consumers on other computers): RAG, industrial-inspection, and `schema-bootstrap-llm-wiki` have the `bootstrap-root` record. `img-classification` has neither the record nor a live `.agents/` folder; its last commit is from 2026-05-15.
- The other agent's full verifier run failed while building Git tree metadata. `verify.py` runs `git write-tree`, which writes into `.git/objects`, and that session had read-only `.git` access (the other agent confirmed this). Phase G's phase and closeout receipts passed in this checkout just before `e1bf94f`.

## Findings and the phase that fixes each

Severity uses this repository's scale. "Pre-existing" means the defect predates this branch.

### Phase H: installer copy safety and the no-record refusal

| ID | Severity | Finding | Evidence |
|---|---|---|---|
| R24 | CRITICAL (the write is pre-existing; Phase F's claim is new) | A full refresh writes outside the project through a link inside a real folder that sits where it copies a file. `shutil.copy2(src, dst)` writes to `dst/<name>` when `dst` is a folder, and opening that path follows a link there. The Phase F preflight checks only links at the written paths and at the folders above them, so it passes. Four write paths are affected: the copy step (`copytree` and the top-level file copy), the state-folder README refresh, and the `bootstrap-root` record copy. The README, `docs/runtime-checks.md`, the refresh skill, and the install wiki page say that the refresh refuses, before any write, a link at every path it writes. The Phase F plan's note "No separate copy-time guard: the preflight is complete" was wrong. A related defect, where a regular file sits where a folder is copied, makes `copytree` stop partway, after earlier writes. | `scripts/install_bootstrap.py` `validate_no_symlink_writes` (`visit`, line 1000), `copy_generated_tree` (lines 911-926 and 934-947), `populate_bootstrap_root` (lines 1494-1496); the table above |
| R25 | MAJOR | The no-record recovery calls a folder an "unmodified bootstrap copy" when each file's `git hash-object` appears anywhere in `git rev-list --all --objects` of a bootstrap checkout. That ignores file names and the complete file list, so it does not prove the folder equals any bootstrap version of that skill. It is the proof offered before a deletion. | `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md:58-63` |
| R26 | MAJOR | Decision 9's fallback: with no `bootstrap-root` record (only the live `.agents/skills/`, a symlinked record, or nothing), an unmarked skill folder whose name the new source ships is overwritten, and its extra files are deleted without a warning. The installer cannot tell an old bootstrap copy from the project's own skill there. The user overturned Decision 9 on 2026-11-15 (option A below). | `scripts/install_bootstrap.py:655-667`; `tests/test_install_bootstrap.py:2442` and the `PROJECT_SKILL_PASSES` fixtures pin it |
| R27 | MINOR | The stale `.agents/skills/` recovery says to delete the listed folders "if you did not create them". Moving them out of the folder first is the safe default; delete only copies whose bootstrap origin is verified. | `scripts/install_bootstrap.py:472-475`; `SKILL.md:64-67`; README "Never create or edit `.agents/skills/<name>/` by hand" paragraph |
| R28 | MINOR (an accepted Phase G follow-up, fixed now because Phase H rewrites the same sentences) | README, `docs/runtime-checks.md`, and the refresh skill say that the devcontainer write and its symlink check happen "with `--state-remote`". An exported `AI_STATE_REMOTE` triggers both too, because `main` takes either value. | `docs/target-mapping.md:124` |

### Phase I: knowledge refresh

| ID | Severity | Finding | Evidence |
|---|---|---|---|
| R29 | MINOR | The install wiki page repeats the claims behind R24 to R28: the symlink guarantee, the no-record overwrite, delete the stale folders, and "with `--state-remote`". | `openwiki/operations/install-ownership-and-runtime-checks.md:121, 135, 161, 171` |

## Decisions (the user, 2026-11-15)

- **8. Symlinks:** confirmed. Fix R24 before release. The `state-sync.sh` gap stays visible as a priority follow-up.
- **9. Newly shipped name without a record:** overturned. Option A: refuse an unmarked skill folder whose name the new source ships when no shipped-before record lists it, with three refinements from the second review:
  - a missing record alone never blocks an install; only existing unmarked skill folders whose ownership is uncertain do, so a fresh project with no skills installs normally;
  - rename a project skill only when its name conflicts with a shipped one; otherwise keep the name and add `.project-skill`;
  - test every affected copy operation (main copy, state README refresh, install-record copy, tracked root guidance): the outside file stays unchanged, and refusals happen before any project change.
- **10. Stale `.agents/` folders:** manual recovery confirmed. Recommend moving or backing up the listed folders. Delete only copies whose bootstrap origin is verified.
- **11. Missing install record:** no runtime dependency on Git history, confirmed. The manual procedure is corrected (R25).
- **12. Size limits:** confirmed as ceilings; raising one needs a stated reason.

## Not changed, with reasons

- The other agent's failed full verifier run: an environment limit (read-only `.git`), not a repository defect.
- `img-classification`'s cleanup advice stands: all of its folders pass the stricter whole-folder check.
