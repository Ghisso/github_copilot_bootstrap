---
type: operations
title: "Sidecar overlay: a personal install inside a team-owned repository"
description: How install_bootstrap.py --mode sidecar adds four skills and two instruction bridges to a team-owned repository as Git-ignored files, how the planner in sidecar_overlay.py decides ownership, repository boundaries, and team precedence, how preflight, the ignore gate, and atomic moves keep every run safe, how edited copies are preserved, and how --uninstall removes the overlay on the same write order.
tags: [sidecar, install, overlay, reconciliation, info-exclude, ignore-gate, manifest, team-repository, uninstall]
sources:
  - id: openwiki-source-00cc54d3b93f5692c95beeb7
    resource: repo://docs/sidecar-provider-contract.md
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
  - id: openwiki-source-cae9260f89e696dbf3ed5310
    resource: repo://scripts/runtime_ownership.py
  - id: openwiki-source-472dd9a20a81e8f5a312971f
    resource: repo://scripts/sidecar_overlay.py
  - id: openwiki-source-2d0d5ea9c4029722239233b8
    resource: repo://tests/test_sidecar_install.py
  - id: openwiki-source-0b6f8c38a312ee46c4820997
    resource: repo://tests/test_sidecar_uninstall.py
generated: { by: "claude-code", at: "2026-09-26T06:04:25.666Z" }
verified:
  - by: openwiki/0.5.2
    at: 2026-09-26T06:04:25.666Z
---

# Sidecar overlay: a personal install inside a team-owned repository

Source, tests, and the policies under `shared/policies/` outrank this page.

A sidecar install is a private, per-clone overlay for a repository that a team owns. It adds a few skills and one short always-on rule per client as Git-ignored files, and it never changes a tracked file. It is not equivalent to the full bootstrap: a full install owns the agent harness, while the sidecar only adds to a harness the team owns.

```bash
uv run python scripts/install_bootstrap.py <team-repo> --mode sidecar
uv run python scripts/install_bootstrap.py <team-repo> --uninstall
```

`scripts/install_bootstrap.py` detects the mode and hands the target to `install_sidecar` or `uninstall_sidecar` in `scripts/sidecar_overlay.py`; see [Installing the bootstrap](/openwiki/operations/install-ownership-and-runtime-checks.md) for mode detection.

## What it installs and what it never touches

A unit is one skill directory at one write root, or one bridge file. The sidecar writes these units, all defined in `scripts/runtime_ownership.py`:

| Unit | Paths |
| --- | --- |
| Skills (`SIDECAR_SKILLS`) | `debug-investigator`, `humanize`, `ponytail`, `ponytail-review` under both `.claude/skills/` and `.agents/skills/` |
| Ponytail license | `LICENSE` (MIT) inside `ponytail/` and `ponytail-review/` at both roots |
| Claude Code bridge | `.claude/rules/ai-bootstrap-sidecar.md`, no frontmatter |
| Copilot in VS Code bridge | `.github/instructions/ai-bootstrap-sidecar.instructions.md`, with `applyTo: "**"` |

Both bridges carry the same short body from `shared/sidecar/bridge.md`: tracked repository guidance wins over the sidecar, and `ponytail` applies to coding tasks in `full` mode.

The sidecar also keeps four things in the Git directory, where they can never be tracked:

- the manifest `ai-bootstrap-sidecar.json`, which records each owned unit's per-file SHA-256 hashes and the paths of retained files;
- the staging folder `ai-bootstrap-sidecar-staging`, used for atomic moves and emptied by every run;
- the preserved-copy folder `ai-bootstrap-sidecar-preserved`, which holds edited copies moved out of the client folders and which the sidecar never empties;
- one marked block in `info/exclude` (a local, untracked ignore file, separate from the team's tracked `.gitignore`), between `# BEGIN ai-bootstrap sidecar` and `# END ai-bootstrap sidecar`.

It never installs hooks, changes `core.hooksPath`, creates a nested `.claude` repository, writes MCP configuration or a devcontainer, edits `.gitignore`, or adds custom agents. It never deletes, moves, or writes anything inside a nested repository or a submodule.

## Client support

Support is claimed only where a real client run observed it. `docs/sidecar-provider-contract.md` records the evidence from native runs on 2026-09-25.

| Client | Reads | Bridge | Status |
| --- | --- | --- | --- |
| Claude Code | `.claude/skills/` | `.claude/rules/ai-bootstrap-sidecar.md` | verified |
| OpenAI Codex | `.agents/skills/` | none by design; skills only | verified |
| Copilot in VS Code, Local agent | `.agents/skills/`, `.github/skills/`, `.claude/skills/` | loads both bridges, so it sees the bridge text twice | verified |
| Copilot in VS Code, Agent Host with the Copilot harness | all three folders | `.github/instructions/` bridge | verified |
| Google Antigravity | `.agents/skills/` (documented) | none shipped | unverified for sidecar v1 |

Every verified client loaded skills and bridges that only `info/exclude` hides. Copilot CLI and cloud agents are out of scope.

## Preflight

Install and uninstall share one preflight, `_run_target_preflight`. Every check runs before any write, in the real run and in `--dry-run`, and a failure prints `sidecar-install: ABORT: <evidence>` with a remedy and exits 1:

1. For an install only, the source exists and holds exactly the sidecar source set: every skill at both roots, both Ponytail licenses, and both bridges, and nothing else. A half-built `dist/sidecar/` or `--source dist/multi-agent` is refused.
2. Git is 2.31 or newer, because the sidecar needs `git rev-parse --path-format`.
3. The target is a Git repository, is the top level of its worktree, and is not a linked worktree.
4. The Git directory and the worktree are on the same filesystem, because atomic moves need one filesystem.
5. The manifest, staging, preserved-copy, and `info/exclude` paths are built from the Git directory, never through `--git-path`, which resolves symlinks. Each is checked with `lstat`: none may be a symlink, the manifest and exclude file must be regular files, and the two folders must be real folders. `info/` itself must not be a symlink. A named pipe is refused without being opened.
6. The manifest, when present, parses and names only paths inside the sidecar namespace.
7. No nested repository or submodule sits at or above a skill write root or a bridge parent, and every existing ancestor of those paths is a real folder on the target's device. Skill folders themselves follow the unit-level rule in the next section.
8. The sidecar markers in `info/exclude` form exactly one BEGIN line followed by one END line. Anything else is refused, naming the line numbers, because an orphan BEGIN would otherwise let a run erase the person's own ignore lines.

After preflight, the run gathers each unit's state from disk and the index, then plans. These checks also run before any write:

- Gathering asks `git check-ignore` which untracked files are already ignored. A Git exit other than 0 or 1, such as 128 for a path inside a submodule, raises `GitCheckIgnoreError`, and the run aborts with Git's own message instead of planning from a partial answer.
- The device check also runs on every existing skill folder, so a folder on another filesystem is refused before a move could fail.
- A symlinked ancestor of a planned unit aborts the run, because sidecar mode does not support a symlinked skill folder or projection parent. A symlink inside a unit does not abort; it makes the unit incomplete.
- A recorded or listed skill folder that holds a nested repository aborts the run, as the next section describes.
- A folder that a move must change, including every folder inside a unit being removed, must be writable.

An invalid manifest gets this remedy: move the manifest aside and rerun with `--mode sidecar`. Units that the exclude block lists are then recovered: matching units are adopted, and any other listed unit is kept hidden and reported. `tests/test_sidecar_install.py` covers each abort in both the real run and the dry run.

## Repository boundaries at skill folders

The outer repository's `info/exclude` does not apply inside a submodule, and the files of a nested repository belong to that repository. Gathering therefore stops at a gitlink (a submodule entry, mode `160000`, in the index) and at a `.git` entry, at any depth, and never hashes or follows anything below either one.

Each skill folder then falls into one of these cases:

- The folder is itself a gitlink. It is team-owned: the run drops any record, plans no file action, and reports that the sidecar never touches files inside a submodule and skips the skill at every root.
- The folder holds a `.git` entry that is not inside a gitlink, and the manifest records the unit or the exclude block lists it. The run aborts before any write, with a message that sidecar mode does not support the nested repository or submodule at that path and that nothing was written.
- The folder holds such a `.git` entry, but the sidecar never recorded or listed it, as with a personal clone. The unit is foreign: its skill is taken, and nothing inside it is touched.

A gitlink can also sit below a skill folder, for example a team skill that carries its own submodule in `vendor/`. Its paths are never sent to `git check-ignore`, and a retained or listed file line under it is dropped and reported as now visible. `tests/test_sidecar_install.py` covers every case through real Git, including a real `git submodule add` at a recorded unit.

## How ownership is decided

The planner, `plan_sidecar_reconciliation`, is pure. The apply step gathers Git and disk state, and the planner turns it into actions. A unit's hash is SHA-256 over its files sorted by relative path, with each record framed as the path bytes, a NUL byte, the file's own hex digest, and a newline.

Ownership comes from the Git index, not from files on disk. A unit is tracked when the index has any entry at or under its path, including `skip-worktree`, intent-to-add, gitlink, and symlink entries, even when the file is deleted from disk. When `core.ignorecase` is true, index paths are compared without regard to case. The sidecar never restores or writes over a deleted tracked file.

"Listed" below means the sidecar's own exclude block has the unit's line. `_classify_unit` checks these cases in order, and the first match wins:

| State of the unit | Result |
| --- | --- |
| The unit path is a gitlink | gitlink: team-owned, skipped, nothing inside it is touched |
| Tracked, and recorded in the manifest or listed | team takeover (see below) |
| Tracked, neither recorded nor listed | team-owned: skipped, no exclude line, no record |
| Absent, or a folder holding only folders, and still wanted | install (this also reinstalls a deleted owned unit) |
| Absent, recorded, and no longer wanted | drop the record |
| Complete, equals the record, and no longer wanted | remove |
| Complete, equals the record and the wanted content | unchanged |
| Complete, equals the record, and the wanted content changed | update |
| Complete, equals the wanted content, and listed or recorded | adopt and record |
| Recorded, but different or incomplete | locally modified: kept, reported |
| Listed, with no record | unfinished sidecar copy: kept hidden by its line, reported |
| Anything else | foreign: skipped, reported, never hidden |

A unit is incomplete when it holds a symlink, named pipe, socket, device, empty subfolder, or unreadable subfolder at any depth. The unit hash cannot represent those entries, so an incomplete unit never matches its record or the wanted content, and a run never deletes it as an unchanged copy. A folder that holds no non-folder entry at any depth still counts as absent, so install replaces an empty leftover folder.

A symlink or a plain file at a unit path is classified like any other entry: a tracked one is team-owned, a recorded one is locally modified, and an untracked, unrecorded one is foreign. Adoption needs a record or the sidecar's own exclude line, so it never claims or hides a file the sidecar did not plan. It finishes an interrupted install or update, or rebuilds a lost manifest. `tests/test_sidecar_overlay.py` has cases for every row.

## Team precedence

The planner decides which skills are taken before it settles any unit's action. A skill is taken when any of these holds:

- a write-root unit for it is team-owned, a team takeover, a gitlink, or foreign;
- `.github/skills/`, `.agent/skills/`, or `.codex/skills/` has an entry with its name;
- the index has an entry under a read folder for that name;
- a non-sidecar `SKILL.md` in a read folder declares it as its frontmatter `name:`;
- `core.ignorecase` is true and a case variant of its name exists in any read folder, including a write root.

Folder names and frontmatter names come from one enumerator, `_enumerate_read_entries`, so both scans follow the same path-identity rule:

- A read folder that is a symlink is listed through its link, unless it resolves into a write root. Then it only mirrors the sidecar's own copies, as in the common `.github/skills -> ../.claude/skills` layout, and contributes nothing.
- An entry that is a symlink resolving into a write root is an alias to a sidecar copy and never takes a skill, even inside a write root.
- Every other entry, including a broken symlink, is listed by its own name. Write roots are listed directly, so a case variant or a differently named folder there is seen.

A taken skill may only end with an allowed outcome. `_convert_for_taken_skill` turns a planned install into nothing, an unchanged, updated, or adopted copy into a removal, and a locally modified or unfinished copy into a preserve. A new outcome kind that the table does not cover fails loudly instead of slipping past, which is how an adopted copy once escaped. The report names every path that took the skill, and a property test asserts that no taken skill ever keeps, installs, updates, or adopts a copy.

The rule exists because Copilot's Local agent lists one copy per skill name and prefers `.agents/skills/`. In a native run, a sidecar copy there hid the team's skill of the same name in `.github/skills/`.

## Preserved copies

When a skill is taken and the person edited a sidecar copy of it, the copy is moved, never deleted. The destination is `<git dir>/ai-bootstrap-sidecar-preserved/<unit path with "/" replaced by "__">--<content hash>`, one level deep: a folder for a skill and a file for a bridge. An incomplete copy is moved whole, with every entry intact. The run prints `PRESERVED <unit> -> <path>`, drops the unit's record, and drops its exclude line.

A move never overwrites anything. When the destination already exists, the unit stays in place with its record and line, and the report names both paths as a conflict. While that conflict keeps an edited copy, the skill's other taking paths are reported as keeping the skill until the conflict is resolved, not as skipped at every root. The Git directory is out of reach of `git checkout` and `git clean`, so a preserved copy stays until the person copies it back or deletes it on purpose.

## Team takeover and retained files

A team takeover happens when the team starts tracking a file in a unit the manifest records or the block lists. Git overwrites an ignored file on checkout without warning, so the planner handles the rest of that unit:

- Untracked files whose bytes match the record or the wanted content are the sidecar's own and are deleted.
- Other untracked files that are currently ignored are kept as retained files, each hidden by its own escaped exact-path line.
- An untracked symlink has no hash to match, so it is never deleted. It is retained with its own line when ignored, like a file that matches nothing.
- A retained name that gitignore cannot express, one with a newline or a trailing carriage return, gets no line and is reported instead.
- Visible untracked entries are left alone and get no line.

The unit loses its record and its unit line. A retained file keeps its line and a `RETAINED` report until it is deleted or tracked; then its entry and line are dropped. A file-level line in the block keeps hiding its file even when the manifest is lost. The owning unit of every file line is always gathered, so a retained file of a skill that a later bootstrap version dropped keeps hiding, and uninstall reports it as now visible.

## The exclude block and the ignore gate

Each owned unit gets one anchored line with no trailing slash, for example `/.claude/skills/ponytail`. Exact-path lines escape the gitignore pattern characters `\`, `*`, `?`, and `[`, a leading `!` or `#`, and trailing spaces. Without the escaping, a line for `notes[1].md` would hide an unrelated `notes1.md` instead.

Every exclude-block reader and writer splits lines on `\n` only, as Git does, and ignores one trailing carriage return when comparing. Python's `str.splitlines()` also splits on characters such as a form feed or U+2028. That would turn one escaped retained-file line into two patterns, and the extra pattern could hide unrelated team files.

Reading the block, the planner sorts each line into a unit line, a file line, or a line it does not recognize. An unrecognized line is kept on every run and reported once, so a run never un-hides a file through a line it does not understand.

The planner returns the gate paths next to the exclude lines. On install and update the gate checks every unit and file path the write-phase block lists, including unfinished and locally modified units and retained files, not only manifest records and actions. `run_ignore_gate` pipes those paths to `git check-ignore --stdin -z` and passes only when the printed set equals that set exactly.

A skill unit that is a real folder, or absent, is gated as `<unit>/`, so a team rule ending in `/`, such as `!.claude/skills/*/`, is caught before the folder exists. A unit that exists as a symlink or another non-folder is gated as `<unit>`, because Git refuses a trailing slash beyond a symlink. On failure the installer restores the previous exclude file and names each path that is not ignored, with its winning rule from `git check-ignore -v -n -z --stdin`; a correctly ignored path is never listed. A Git exit other than 0 or 1 also restores the exclude file and aborts with Git's message. When Git cannot name a directory-only rule for a path that does not exist yet, the message says that a rule ending in `/` may be un-ignoring the folder.

Every Git path is handled as bytes (`os.fsdecode` and `os.fsencode`), so a legal but non-UTF-8 file name never crashes a run.

## Write order and crash recovery

This diagram shows the order of the writes in a real install or update.

```mermaid
flowchart LR
    P[preflight and plan] --> E[write exclude block]
    E --> G[ignore gate]
    G --> U[move units via staging]
    U --> F[final exclude lines]
    F --> M[write manifest]
```

1. The exclude block gets a line for every unit that is owned after the run, being written, removed, or preserved, plus the exact-path lines of a takeover. Then the gate runs.
2. The staging folder is emptied. Each new unit is built in staging, the old copy is moved into staging, and the new copy is moved into place with `os.replace`. A removed unit is moved into staging, a preserved unit is moved into the preserved-copy folder, and a takeover's matching files are deleted.
3. The block drops the lines of removed and preserved units and of deleted files.
4. The manifest is written last, through a temporary file and `os.replace`, and staging is emptied.

The exclude file and the manifest are written only when their bytes change. There are no intent records. After a crash, each unit is old, new, or absent, and the next run's classification finishes the work: the adopt row takes a new unit whose record was not written, and the install row restores an absent one. Tests inject faults after the exclude write, in the middle of a unit swap, and before the manifest write, and uninstall adds a fault after its units are removed; each rerun converges. Uninstall follows the same order, as described below.

## Dry-run

`--dry-run` runs preflight and planning, then the same gate on the candidate block through a temporary `core.excludesFile` outside the worktree and the Git directory. It prints each action as `would ...` and writes nothing, including the staging folder. Git ranks `info/exclude` above `core.excludesFile`, so the output says the dry-run gate is an approximation and the real run's gate decides.

## Reports and remedies

An install prints `installed N, updated N, removed N, adopted N, unchanged N, preserved N`, then one line per removed, deleted, or preserved path, then one line per report. Per-path skips never fail an install.

| Report | Cause | What the remedy says |
| --- | --- | --- |
| `SKIPPED` | the team tracks a path in the unit | the repository tracks that path; the sidecar skips the skill at every root, or does not install the bridge |
| `SKIPPED` | the skill folder is a submodule | the sidecar never touches files inside a submodule and skips the skill at every root |
| `SKIPPED` | another path takes the skill name | names that path; the sidecar skips the skill at every root |
| `SKIPPED` | another path takes the skill while a preserve conflict keeps an edited copy | names that path; the skill is kept in place until its edited-copy conflict is resolved |
| `SKIPPED` | a recorded unit was edited or is incomplete | the copy is kept; a pull can overwrite hidden files; to take the current version, copy your edits elsewhere, delete the path, and rerun |
| `SKIPPED` | a listed copy has no record | an unfinished copy the sidecar cannot verify stays hidden; copy anything you need, delete it, and rerun |
| `SKIPPED` | an edited copy of a taken skill cannot move because the destination exists | the copy stays in place; resolve the two copies by hand, then rerun |
| `SKIPPED` | an unrecorded entry is in the way | the sidecar will not replace it and skips the skill at every root |
| `PRESERVED` | an edited copy of a taken skill was moved | where the copy now lives |
| `RETAINED` | a file was left behind by a team takeover | it stays hidden and a pull can overwrite it; move it out, or commit it with `git add -f` |
| `RETAINED` | a retained file now sits inside a submodule, or uninstall un-hid it | it is now visible to `git add -A` |
| `RETAINED` | a block line the sidecar does not recognize | the line is kept; move it outside the block to keep it, or delete it |

## Uninstall

`--uninstall` removes the overlay through the same preflight, the same planner, and the same write order and apply step as an install. With no manifest and no block, it prints where the preserved-copy folder is if that folder holds anything, then prints `no sidecar found; nothing to do` and exits 0.

Otherwise it gathers every well-known unit, including retired skill roots and retired bridges, and plans against an empty wanted set. Every classified unit is taken, including a skill the current bootstrap no longer ships:

- a unit whose content matches its record is removed;
- an edited or unfinished copy, including an incomplete one and a bridge, is preserved in the preserved-copy folder;
- team, submodule, and foreign content is never touched;
- a retained file loses its line and is reported as now visible to `git add -A`;
- a block line the sidecar does not recognize is written back as a plain line where the block was.

The run then follows the install's order:

1. It writes the write-phase block. A rerun with no block and no line to write leaves the exclude file alone.
2. It runs the gate over only the paths whose lines the final block keeps. That set is empty unless a preserve conflict keeps a unit, so a team rule that exposes a path being removed never blocks an uninstall. A person's own negation that exposes a kept unit fails the gate, and the run restores the exclude file before any unit moves.
3. It empties staging and applies the actions through the same `_apply_actions` step as an install.
4. With no conflict, it removes the block, deletes the manifest, and removes the staging folder. With a conflict, it writes the final block and a manifest that holds only the kept units' records, empties staging, and exits 1.

Every run ends by printing `preserved copies are in <folder>; the sidecar never empties this folder` when that folder holds anything. The exit code depends only on the units a preserve conflict actually kept (`kept_conflicts`), so a preserve conflict is the only reason uninstall exits 1 after preflight. `tests/test_sidecar_uninstall.py` covers each path through real Git, including a dropped skill, a retired root and retired bridges, a team negation added after install, both crash points, and dry-run.

## Limits

- Sidecar mode supports only the main worktree. The main worktree's `info/exclude` also hides the sidecar's paths in every linked worktree, because all worktrees share it.
- Worktrees that VS Code or the Codex app create for background sessions contain no sidecar files, unless they are listed in `git.worktreeIncludeFiles` or `.worktreeinclude`.
- Git overwrites a hidden sidecar file without warning when the team later commits a file at the same path, so keep personal edits elsewhere.
- `info/exclude` is a convenience, not a security boundary.

## Updating

`scripts/update_consumers.py` updates sidecar consumers through the same `install_sidecar` path, because it passes no `--mode` and the installer detects sidecar evidence. It never passes `--uninstall`. `tests/test_sidecar_update.py` covers updates across two bootstrap versions: changed, added, and removed skills, bridge changes, local edits, team takeovers, a deleted exclude block, a corrupted manifest, and an idempotent second update. The README keeps a safe manual fallback for removal, which never deletes retained files or the preserved-copy folder.

## Representative tests

- `tests/test_sidecar_overlay.py` covers the planner: every classification row, team precedence as a property test with real `adopt` and `unchanged` fixtures, preserve and conflicts, block parsing, manifest validation, escaping against real `git check-ignore`, and plan-apply-plan idempotency.
- `tests/test_sidecar_install.py` covers preflight aborts, index-based ownership (sparse checkout, `skip-worktree`, gitlinks, deleted tracked files), repository boundaries at skill folders, incomplete units (pipes, sockets, empty subfolders, inner symlinks, a plain file), symlinked read folders, aliases, and case variants, frontmatter names, the gate (directory-only rules, symlink units, unfinished units, fatal Git errors), line splitting, non-UTF-8 names, dry-run, fault recovery, and reruns.
- `tests/test_sidecar_update.py` covers upgrades and mixed full and sidecar batches.
- `tests/test_sidecar_uninstall.py` covers uninstall, dropped skills and retired units, preserve conflicts with the gate, team rules that never block, crash convergence, and refusals.

## Related pages

- [Installing the bootstrap, file ownership, and runtime drift checks](/openwiki/operations/install-ownership-and-runtime-checks.md)
- [Source, generated output, consumer repo, and nested AI state](/openwiki/architecture/source-generated-consumer-layout.md)
- [Git-backed AI-state sync](/openwiki/operations/git-backed-ai-state-sync.md)
- [Agent roster, prompts, and the skill library](/openwiki/architecture/agents-and-skills.md)
- [Quickstart](/openwiki/quickstart.md)
