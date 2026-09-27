# Consumer sidecar bootstrap overlay: post-Phase-K review (round 3)

**Date:** 2026-09-27
**Reviewed HEAD:** `f6f36c8` on `consumer-sidecar-bootstrap-overlay_implementation`
**Big plan:** [consumer-sidecar-bootstrap-overlay](../plans/consumer-sidecar-bootstrap-overlay.md) (status `complete`, Phases A-K)
**Earlier reports:** [round 1](2026-09-25_consumer-sidecar-bootstrap-overlay-review.md), [round 2](2026-09-25_consumer-sidecar-bootstrap-overlay-review-2.md), [hardening re-review](2026-09-26_consumer-sidecar-bootstrap-overlay-review.md) (R1-R5), [Opus re-review](2026-09-26_consumer-sidecar-bootstrap-overlay-review-2.md) (O1-O19)

## Verdict

**FAIL for a PR: two BLOCKER findings, six MAJOR findings, twelve MINOR
findings, and a set of NITs.** The architecture holds. One blocker (N1) is
a realistic team-repository takeover through the plain install path and
sits in the mode-detection code that Phase G and Phase H hardened. The
other blocker (N2) needs a contrived tree but breaks the stated invariant
with exit 0. The six MAJOR findings are all in classification, exclude
rendering, and rerun convergence, and each has a small fix.

Nothing in R1-R5 or O1-O19 regressed. The test suite is strong on the
paths it covers: 326 sidecar tests pass, and five deliberate mutations of
safety logic (empty `kept_conflicts`, gate ignored on uninstall, takeover
deleting every untracked file, unrecognized lines dropped, uninstall
limited to the current profile) each failed at least two tests.

## Method

Five parallel reviewers, one per area: planner and classification; Git
ignore semantics and the exclude file; the write path, crash points, and
preflight; mode detection, the updater, generators, and the Phase F
validator; uninstall, bridges, test quality, and docs. Each read the code
against the big plan's decisions and the two 2026-09-26 reports, then
reproduced every suspected defect in a throwaway Git repository under the
session scratchpad, guarded by a `git rev-parse --show-toplevel` check
before any write. Findings marked "reasoned" were not reproduced. The
orchestrator re-read the code for every BLOCKER and MAJOR finding and
confirmed each anchor. The repository and the nested `.claude` repository
stayed clean throughout, including after an in-place
`generate_targets.py --all`.

Scratch reproductions lived under `.../scratchpad/{planner,exclude,apply,modes,uninstall}/`
and are not durable. Each finding describes its scenario precisely enough
to rebuild as a real-Git test in `tests/`.

## Findings

### N1. BLOCKER: a plain install takes over a team repository whenever `.claude/bootstrap-ownership.env` exists, even when `.claude` is tracked, a submodule, or a tracked symlink

- **Anchors:** `scripts/install_bootstrap.py:1275-1311` (`_full_install_evidence`): the `claude_tracked` guard is computed only inside `if nested_is_dir:` and applied only to the `.claude/.git` evidence; the `ownership_env.exists()` branch has no guard. `README.md:697-700` claims the guard covers "a team `.claude` submodule or embedded repository".
- **Why it is realistic:** the nested AI-state repository tracks `bootstrap-ownership.env` (`git -C .claude ls-files -- bootstrap-ownership.env` prints it in this repository). Any team that adds an AI-state repository as a submodule, vendors it, or force-commits it at `.claude` ships the file to every clone, and every clone then carries "full evidence".
- **Scenario A:** team repo tracks `README.md`, `src/`, `CLAUDE.md`, `.claude/settings.json`, `.claude/skills/team-skill/SKILL.md`, `.claude/bootstrap-ownership.env`. Run `install_bootstrap.py TARGET` with no `--mode`. Observed: exit 0; `git status` shows ` M .claude/settings.json`, ` D .claude/skills/team-skill/SKILL.md`, a new `.gitignore`, `.devcontainer/*`, `.vscode/tasks.json`; `core.hooksPath` set. Expected: the team-config refusal naming the tracked `.claude` paths.
- **Scenario B:** team repo with a submodule at `.claude` whose content includes the env file. Observed: exit 0; the installer checked out a new `ai-state` branch inside the team's submodule, committed `bootstrap: init ai-state` there, moved the outer gitlink (` M .claude`), and tried to push `ai-state` to the submodule's `origin`, which is the team's remote (`git push --dry-run` from the submodule reports `* [new branch] ai-state -> ai-state`).
- **Scenario E2:** `.claude` is a tracked symlink (mode 120000) to a folder holding a `.git` dir and the env file. Observed: full install selected, because `Path.exists()` follows the link.
- **Existing tests** cover only `.claude/.git`-directory variants (`test_claude_submodule_refuses_as_team_config_not_full_evidence`, `test_claude_embedded_gitlink_without_gitmodules_is_team_config`).
- **Fix:** read the index once before either branch (`git ls-files -s -z -- .claude`), set `claude_tracked` when any entry of any mode is `.claude` or under `.claude/`, and count neither `.claude/.git` nor the env file as full evidence when it is true. Use `os.path.lexists` for the env file. Add real-Git tests for A, B, E2, and `--uninstall` on the same shapes. Correct `README.md:697-700`.

### N2. BLOCKER (contrived input, invariant broken): a tracked directory at a bridge path is classified as untracked, and uninstall moves the team's tracked files into the preserved folder

- **Anchors:** `scripts/sidecar_overlay.py:2112-2118` (`_unit_index_relpaths`, bridge branch matches only the exact path, never entries under it); `:2175-2197` (`_gather_unit` bridge branch: a directory yields `exists=True`, `file_hashes={}`, `incomplete=False`); `:1196` (`_convert_for_taken_skill` turns `locally_modified` into `preserve`).
- **Scenario:** sidecar installed; team commits `.claude/rules/ai-bootstrap-sidecar.md/note.md` (a folder with the bridge's name). Rerun install, then `--uninstall`.
- **Observed:** rerun install exits 1 blaming the ignore gate and the `.gitignore` remedy (wrong diagnosis: the path is tracked). Uninstall exits 0, prints `PRESERVED .claude/rules/ai-bootstrap-sidecar.md -> ...--e3b0c4...` (the empty-unit hash), and `git status` shows ` D .claude/rules/ai-bootstrap-sidecar.md/note.md`.
- **Expected:** index entries at or under a bridge path make the bridge team-owned (drop record, no file action), as skill units already do.
- **Fix:** in the bridge branch of `_unit_index_relpaths` also match `path.startswith(f"{unit_path}/")`. Optionally refuse to preserve a bridge whose `kind` is a folder.

### N3. MAJOR: a skill dropped from the profile is never "taken", so an edited copy stays discoverable next to the team's version

- **Anchors:** `scripts/sidecar_overlay.py:1379` and `:1396` (both precedence loops iterate `SIDECAR_SKILLS` only); `:1413-1416` (`taken_units` built from current skills and current write roots only); `:1109` (dropped-skill `locally_modified` remedy).
- **Scenario:** v1 ships `humanize`; the person edits `.claude/skills/humanize/SKILL.md`. v2 drops `humanize` and the team commits `.github/skills/humanize/SKILL.md`. Run v2's install.
- **Observed:** exit 0; `.agents/skills/humanize` removed, but `.claude/skills/humanize` stays hidden, recorded, and listed with the "copy your edits elsewhere" remedy. The team's copy takes nothing; Claude Code still sees the sidecar copy. Decisions 22 and 24 do not apply to recorded units whose skill left the profile. Uninstall was fixed for this (Decision 39); install and update were not.
- **Fix:** compute precedence over `set(SIDECAR_SKILLS) | {skill of every required unit}` and build `taken_units` over `_ALL_SKILL_WRITE_ROOTS`.

### N4. MAJOR: a team skill's frontmatter `name:` is missed when byte 4096 of `SKILL.md` falls inside a multibyte character, or the file starts with a BOM

- **Anchors:** `scripts/sidecar_overlay.py:2445` (`_FRONTMATTER_MAX_BYTES = 4096`); `:2454` (`data.decode("utf-8")` on the truncated read returns `None` for the whole file on `UnicodeDecodeError`); `:2458` (`lines[0].strip() != "---"` fails on a BOM).
- **Scenario:** team `.github/skills/team-review/SKILL.md` declares `name: ponytail` in a short frontmatter followed by Japanese body text past 4 KB. With n-byte characters roughly (n-1)/n of such files hit the cut mid-character.
- **Observed:** `_declared_skill_names` returns `{}`; install exits 0 and installs `ponytail` at both write roots next to the team's declared `ponytail`. Decision 22's frontmatter rule silently fails.
- **Fix:** decode with `errors="replace"` (the name line is always before the cut) or find the closing `---` on bytes; strip a leading BOM after decoding. Related NIT: a closing `---` beyond 4096 bytes also declares nothing.

### N5. MAJOR: a read-only root reached through a symlinked parent folder is treated as team content, and runs flip between install and remove

- **Anchors:** `scripts/sidecar_overlay.py:2406-2408` (`_enumerate_read_entries` skips a root only when `root_path.is_symlink()` itself); `:2416` (an entry is an alias only when `entry.is_symlink()`); `_reflects_a_write_root` `:2365`.
- **Scenario:** `.agent -> .claude` (a person letting Antigravity see Claude skills; `.codex -> .claude` behaves the same). Run install three times.
- **Observed:** run 1 installs 10; run 2 removes all 8 skill units with `SKIPPED .agent/skills/ponytail: the repository has ...`; run 3 installs 8 again. An edited copy would be preserved on every even run and reinstalled pristine on every odd run.
- **Fix:** decide "alias" by identity: an entry or root is an alias when its resolved path differs from `target / p` and lies inside a write root.

### N6. MAJOR: a retained file whose name contains a backslash makes the sidecar write a manifest it refuses to read back

- **Anchors:** `scripts/sidecar_overlay.py:250-260` (`_validate_retained_path` rejects any `\`); `:974-977` (`_team_takeover` retains any ignored name that passes only `_can_express_in_gitignore`); `:360` (`serialize_manifest` writes without validating); `:3155-3160` (manifest parse abort).
- **Scenario:** install; create `.claude/skills/ponytail/back\slash`; team runs `git add -f .claude/skills/ponytail/SKILL.md` and commits; rerun.
- **Observed:** rerun 1 succeeds and writes `"retained": [".claude/skills/ponytail/back\\slash"]`. Rerun 2 and `--uninstall` abort with `invalid sidecar manifest ... unsafe retained path`. After the move-aside remedy the block line is "unrecognized" and uninstall writes it back as a plain user line, so the file stays hidden after uninstall (contradicts Decision 34).
- **Fix:** retain only when `_validate_retained_path` accepts the path (route the rest to the existing "cannot express" report), or drop the backslash rejection for retained paths since unit paths are fixed ASCII. Validate in `serialize_manifest` as well.

### N7. MAJOR: install and update re-sort a person's own lines inside the block, flipping gitignore's last-match-wins order

- **Anchors:** `scripts/sidecar_overlay.py:1574-1577` (`for line in sorted(unrecognized_lines)` into a set); `:1590-1591` (`tuple(sorted(exclude_write))`, `tuple(sorted(exclude_final))`).
- **Scenario:** block holds user lines `*.log` then `!keep.log`; `keep.log` exists; rerun install.
- **Observed:** before rerun `?? keep.log`; after rerun nothing (block now reads `!keep.log`, `*.log`; `git check-ignore -v keep.log` names `*.log`). Exit 0 and the report says "keeps it". Uninstall then writes the sorted order back as plain lines. The "git status identical" invariant and Decision 23's "keeps any line" are broken in spirit.
- **Fix:** keep `unrecognized_lines` as an ordered tuple in file order and render the block as `sorted(sidecar lines) + unrecognized lines in original order`.

### N8. MAJOR: an update interrupted before the manifest write, followed by a rerun with a newer bootstrap, never converges and reports the sidecar's own bytes as personal edits

- **Anchors:** `scripts/sidecar_overlay.py:1073-1120` (`_classify_unit`: record-hash mismatch falls to `locally_modified`; the only escape is the adopt row, which needs the current desired bytes); plan claim at big plan line 388 ("Every crash point converges on rerun").
- **Scenario:** v1 installed; `update_consumers.py` with v2 is interrupted at `before_manifest_write` (units already v2, manifest still v1). The next update carries v3.
- **Observed:** rerun with v3 exits 0 but reports `SKIPPED .claude/skills/ponytail: ... has local edits` at both roots; disk stays v2 on every later run. `--uninstall` then moves the v2 copies into the preserved folder as if they were edits.
- **Note:** the same crash during a fresh install followed by a newer source leaves the unit "unfinished"; `tests/test_sidecar_update.py:678` asserts that as intended, so the convergence claim already holds only for a same-source rerun. The crash window is milliseconds and the remedy text does get the person out, so this is narrow but real.
- **Fix:** write `next_manifest` to `<gitdir>/ai-bootstrap-sidecar.json.next` right after the gate passes, unlink it after the real manifest lands, and let `_classify_unit` accept a hash match against either record as ownership proof. It is an ownership record, never an intent record. Cheaper: correct the plan text and make the locally-modified remedy mention an interrupted update.

### N9. MINOR: every rewrite of `info/exclude` replaces it with a 0600 file (found independently by two reviewers)

- **Anchor:** `scripts/sidecar_overlay.py:2623-2634` (`tempfile.mkstemp` creates 0600; `os.replace` carries the mode). Also hit by `_restore_exclude` on a gate failure even when the bytes were unchanged.
- **Observed:** 0664 before install, 0600 after install and after uninstall. In a `core.sharedRepository=group` clone other members lose read access to a team-owned file.
- **Fix:** `os.fchmod(fd, stat.S_IMODE(original_mode))` before `os.replace` when the file existed.

### N10. MINOR: the writability preflight misses three write targets, so a run can crash after the write-phase block is on disk

- **Anchor:** `scripts/sidecar_overlay.py:1956-1983` (`_unwritable_paths_for_actions` skips `team_takeover_delete`; never checks `preserved_root` or the Git directory).
- **Observed:** (a) team tracks `SKILL.md` in `.claude/skills/ponytail`, folder mode 555: rerun raises `PermissionError` on `LICENSE`, block left in write-phase state, rerun after chmod converges. (b) `--uninstall` with an edited unit and a read-only preserved root: `PermissionError` mid-move. (c) `.git` not writable while `.git/info` is: block written, then `_empty_staging` mkdir fails.
- **Fix:** add the parent of every `team_takeover_delete` path, the nearest existing ancestor of each preserve destination, and the Git directory to the check set; wrap `_apply_actions` in `except OSError` and abort with the path (the Phase J log already suggests this for the mount-point case).

### N11. MINOR: environmental failures end in tracebacks instead of a clean abort

- `git` not on PATH: `FileNotFoundError` from `scripts/sidecar_overlay.py:1622` and `:1763`; `scripts/install_bootstrap.py:1323-1331` catches only `CalledProcessError`. All three CLI entry paths affected.
- `info/exclude` unreadable (mode 000): `PermissionError` at `scripts/sidecar_overlay.py:1675`.
- An unreadable regular file inside a unit: `PermissionError` at `:2275` and `:2185`; Decision 38 covers an unreadable subfolder but not a file.
- `info/` as a regular file, or a read-only `info/` directory: `FileExistsError` or `PermissionError` from `_atomic_write` `:2623-2635`; only `info_dir.is_symlink()` is checked at `:3148-3153`.
- Undecodable bytes in a reported path: `_info` `:1731` prints the surrogate-escaped name raw; with strict stdout encoding the run tracebacks in `_print_report` after the manifest was written, so exit 1 for a completed run. Decision 29's "printed paths escape undecodable bytes" is not implemented.
- **Fix:** catch `FileNotFoundError` around git calls; catch `OSError` on exclude and unit reads (treat an unreadable file as incomplete); abort in preflight when `info` exists and is not a directory; print paths through `backslashreplace`.

### N12. MINOR: no cross-process lock; two overlapping runs corrupt each other's staging

- **Anchor:** `scripts/sidecar_overlay.py:3033` and `:3450` (`_empty_staging` rmtree at the start of every apply).
- **Observed:** run B's rmtree during run A's unit swap makes run A raise `FileNotFoundError` on `os.replace`; rerun converges; no edited content lost. A manual run overlapping `update_consumers.py` is plausible.
- **Fix:** `fcntl.flock` on `<gitdir>/ai-bootstrap-sidecar.lock`, non-blocking, abort with "another sidecar run is active".

### N13. MINOR: unbalanced or doubled exclude markers are reported as a Git failure with a `safe.directory` hint, and `_EXCLUDE_MARKER_REMEDY` is never shown

- **Anchor:** `scripts/install_bootstrap.py:1314-1332` (`except ExcludeMarkerError` reuses `_detection_abort_message`). Affects every mode.
- **Fix:** a dedicated message carrying `_EXCLUDE_MARKER_REMEDY`.

### N14. MINOR: a hand-added unit-shaped line for a private folder turns it into "an unfinished sidecar copy", and uninstall moves it out as "your edited copy"

- **Anchors:** `parse_exclude_block` `:692-741` accepts any `<write root>/<segment>` line as a listed unit; `_validate_unit_path` `:235-248` never checks the segment against `SIDECAR_SKILLS`; `:1122-1127`; `:1210-1240`.
- **Observed:** install prints advice to delete the person's own skill; `--uninstall` moves it into the preserved folder. Consistent with Decision 23 but contradicts `README.md:516`.
- **Fix:** treat a unit line whose skill name is neither in `SIDECAR_SKILLS` nor in the manifest as unrecognized, or reword the remedies.

### N15. MINOR: README says a preserve conflict is the only post-preflight reason `--uninstall` exits 1; the code has four more

- `README.md:591-598` vs `scripts/sidecar_overlay.py:3570-3591` and `:3421-3428` (plan aborts, unwritable paths, fatal `check-ignore`, gate failure on a kept unit; the suite's own `test_preserve_conflict_with_a_negation_aborts_before_any_write` expects exit 1 past preflight).

### N16. MINOR: "now visible to `git add -A`" is printed for a retained file that a team rule still ignores

- **Anchors:** `_now_visible_remedy` `:867`, used at `:963-965` and `:1442-1447`. Reproduced with a team `*.log` rule and a retained `notes.log`.
- **Fix:** re-run `check-ignore` on the un-hidden paths and say "no longer hidden by the sidecar; a team rule still ignores it".

### N17. MINOR: `--uninstall` on a missing or non-Git path exits 0 with "no sidecar found; nothing to do"

- **Anchor:** `scripts/install_bootstrap.py:1470-1479`, `:1319-1320`. A typo in the target path looks like a successful uninstall. No test covers either path.

### N18. MINOR (pre-existing on `dev`, listed because the new rule's intent is bypassed): full-install detection gaps

- A subfolder of a team repository gets a full install with no refusal: `_team_config_evidence` runs `git ls-files` relative to the cwd, so `repo/packages/svc` never sees the root's tracked `.claude/`; the full path has no `--show-toplevel == target` check, unlike the sidecar preflight.
- A linked worktree of a full consumer gets the "fresh default" full install with no `--mode` (dry-run only; a real run would create a second nested AI-state clone and rewrite the shared `core.hooksPath`).
- A bare repository passes plain and `--mode full` dry-runs.
- `.claude` as an untracked regular file: dry-run exit 0, real run `FileExistsError` after about 75 paths were written.

### N19. MINOR (reasoned, not reproducible here): `_atomic_write` never calls `fsync`, so a power cut can leave a zero-length `info/exclude` on some filesystems, erasing the person's own lines

- **Fix:** `os.fsync(fd)` before close and fsync the parent directory after `os.replace`.

### N20. MINOR: test-suite realism and coverage gaps

- `tests/test_sidecar_uninstall.py:98` `assert install_sidecar is not None` cannot fail.
- `test_uninstall_dry_run_cli_flag` asserts only exit 0 and one folder; `test_listed_copy_with_no_record_is_preserved_on_uninstall` never asserts the units left the worktree or that status is clean; `test_update_consumers_never_forwards_uninstall_source_has_no_flag` greps the script text and passes for a script that forwards `args` wholesale.
- 34 of 36 uninstall tests run against a README-only repository; the realistic `team_repo` fixture lives only in `test_sidecar_install.py`.
- Matrix cells with no test (all behaved correctly when reproduced, except where a finding above says otherwise): team tracks other files under `.claude/rules/` and `.github/instructions/` plus `CLAUDE.md`, install then uninstall; bridge path tracked by the team, install then uninstall; person deleted a unit and a bridge, then uninstall; block deleted but manifest present with one edited unit; uninstall from main with a linked worktree present; uninstall, install, uninstall; team tracks one file of `.agents/skills/ponytail` with `LICENSE` untracked and matching.

### NITs

- Uninstall leaves empty `.claude/`, `.claude/rules/`, `.claude/skills/`, `.agents/`, `.agents/skills/`, `.github/`, `.github/instructions/` folders it created, creates an empty `info/exclude` where none existed, and adds a trailing newline to an exclude that had none (`_replace_exclude_block` `:2591-2592`, `_remove_exclude_block` `:2596-2620`).
- A SIGKILL between `mkstemp` and `os.replace` leaves `.exclude.XXXXXX` or `.ai-bootstrap-sidecar.json.XXXXXX` behind; nothing cleans them.
- `--uninstall` silently ignores `--source`, `--local-only`, `--state-remote`, `--commit-copilot-surface` (`scripts/install_bootstrap.py:1488-1489` returns before `warn_full_only_options_ignored`).
- `_validate_unit_path` `:235-247` accepts `\n`, `\r`, `\x00`, and a space-only segment; a newline path renders as a unit line plus a raw pattern `tail`. Hand-edited manifest only.
- A block file line with a `.` segment (`/.claude/skills/./notes.md`) makes `required_snapshot_units` return `.claude/skills/.` and walk the whole write root as one unit; harmless.
- A blank line inside the block is reported every run as "does not recognize `` ".
- Gate diagnostic `_NO_MATCHING_RULE` `:2666-2670` blames a rule ending in `/` for a path that does not exist yet, even when the folder exists and the winning rule is a plain negation.
- During uninstall, team-owned, gitlink, and foreign reports still say "the sidecar skips `<skill>` at every root" (`:764-771`, `:774-788`, `:828-838`).
- README report table paraphrases two remedies ("To get the skill back, the team would need to stop tracking the path" is not in code; "Foreign file in the way" omits "and skips `<skill>` at every root").
- A dangling manifest symlink is sidecar evidence (`lexists`); a dangling `bootstrap-ownership.env` symlink is not (`exists`).
- `_full_install_evidence` reads the whole index; `-- .claude` would do.
- `SIDECAR_FORBIDDEN_TEXT_TOKENS` omits `MEMORY.md`, `openwiki`, `.github/hooks/`, `.claude/plans/`, `.claude/session_logs/`; the rendered text is clean today.
- The static bridge text does not say that a named skill may have been skipped as team-owned.
- Installing into a submodule's own worktree works (manifest under `.git/modules/<sub>`); worth one docs line.

## Checked and found correct

- Unit lines are anchored exact paths; gate spells folders with a trailing slash; rerun is byte-identical for manifest and exclude.
- Escaping of `*`, `?`, `[`, `\`, leading `!` and `#`, single and multiple trailing spaces, leading space, tab, mid-name CR, non-ASCII, and raw non-UTF-8 bytes: every line matches literally and `git status` stayed empty. Git strips exactly one trailing CR, matching `_split_exclude_text`.
- Negations at every level tried (`!.claude/skills/ponytail/`, `!*.md`, nested `.gitignore` re-includes) fail the gate, restore the exclude bytes, and write no unit; directory-level negations that Git cannot honor pass correctly. `core.excludesFile` is out-ranked and passes.
- Exclude file states: missing `info/`, missing file, no trailing newline, CRLF-only, BOM, user lines after the block, near-miss markers: user bytes preserved. Doubled or orphan markers abort before any write.
- Linked worktrees: install, uninstall, and auto-detect from a linked worktree abort; uninstall from main with a linked worktree present is clean. Decision 15's side effect is real and documented.
- `.git` file with `gitdir:`, `GIT_DIR`/`GIT_WORK_TREE` scrubbed, renamed root, `core.ignorecase=true`, cone sparse checkout excluding `.claude`, symlinked target path, paths with spaces and unicode, `index.lock` present: all correct.
- Git version regex accepts `2.31.0.windows.1`, `2.45.2.vfs.0.0`, `2.39.5 (Apple Git-154)`, `2.31`.
- Dry run for install and uninstall writes nothing anywhere including `.git` (full-tree hash and mode diff).
- Crash at `after_exclude_write`, `mid_unit_swap`, `before_manifest_write`, and `after_units_removed` converges on a same-source rerun and on `--uninstall`.
- Manifest: unknown fields ignored; schema 2 and empty file abort with the move-aside remedy; removed manifest adopts; written by temp-plus-replace.
- Hash framing is unambiguous; preserved slugs include the unit path; slug length about 123 < NAME_MAX.
- Hard links, FIFOs, broken symlinks, a file at a unit path, `SKILL.md` as a directory: foreign, locally modified, or unfinished; never removed; a taken skill preserves by rename.
- Gitlink at a unit: nothing inside touched, record dropped; gitlink children never hashed.
- Mode table order for `--mode sidecar`, `--mode full`, and no-mode is implemented as written, apart from N1. Self-install refused in every mode. `dist/multi-agent` byte-identical to `dev`; full-install differential shows only the intended fresh-clone refusal.
- `update_consumers.py`: mixed batch runs every target, lists `FAILED:` lines at the end, exits 1; `--dry-run` forwards; `--uninstall` never forwarded.
- `dist/sidecar/` byte-reproducible; both write roots identical; Ponytail `LICENSE` identical to `shared/third_party/ponytail/LICENSE`; no full-install-only reference in the four skills; bridges name only `ponytail` and `ponytail-review`.
- Phase F validator: settled refresh followed by more phases and a final pending refresh passes; two settled refreshes then a pending non-refresh last phase is rejected; a settled sibling with the wrong parent is not exempt; the repository's real plans pass.
- Bridges: the Claude rules file without `paths` loads (native run in the contract); a team-tracked `.claude/rules/` with other files does not block the bridge; a team-tracked bridge path is skipped and never touched, including on uninstall.
- Uninstall matrix: unchanged removed via staging; edited unit and bridge preserved; preserve conflict keeps the unit and its line with exit 1; gate on a kept unit aborts before any write; takeover during uninstall deletes only matching files; dropped-skill and retired-root units handled; block-missing and manifest-missing shapes converge; second uninstall is a no-op.
- Mutation checks (copy of the module loaded through a pytest plugin): `kept_conflicts` always empty (4 failures), gate ignored on uninstall (2), takeover deleting every untracked file (20+), unrecognized lines dropped (2), uninstall limited to the current profile (2). All caught.
