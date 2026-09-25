---
name: 2026-09-25_phase-H-sidecar-preflight-robustness-and-uninstall
type: small-plan
parent_plan: consumer-sidecar-bootstrap-overlay
phase_index: 8
status: planned
---

# Small Plan: Phase H — Sidecar Preflight, Robustness, and Uninstall

## Scope

Make the installer refuse unsafe targets before it writes anything, and make
every run safe with unusual repositories, file names, and sources. Today:

- A team `.claude` submodule or a Git error can send a plain install into a
  full takeover.
- A symlink inside `.git` can make a run delete a folder elsewhere.
- Unbalanced markers can erase the person's own ignore lines.
- Non-UTF-8 bytes crash runs, including full installs.
- A nested repository under a skill folder gets visible sidecar files.
- An empty source silently uninstalls every unit.

This phase also adds `--uninstall` (a user decision) and does the full
documentation pass for both new phases.

Findings covered (IDs from the two 2026-09-25 review reports): S1, S2, S5,
S6, S7, S10, S11, S13, S14, R3, R5, R6, S8 (docs), S15 and S16 (preflight and
installer messages), S17, and design item 4. Big plan Decisions 26-29, 31,
and 33-36.

Phase G already changed the planner, the snapshot gathering, the gate paths,
and the preserve action. This phase changes the installer entry, mode
detection, preflight, the Git-directory and exclude-file I/O, source
validation, and docs. It reuses Phase G's planner for `--uninstall`.

### Required Skills

- `shared/skills/ponytail/SKILL.md` — `full`
- `shared/skills/code-style/SKILL.md`
- `shared/skills/testing-patterns/SKILL.md`
- `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md`
- `shared/skills/documentation/SKILL.md`
- `shared/skills/humanize/SKILL.md` — for the README and docs pass

## Primary Files

- `scripts/install_bootstrap.py` — `_full_install_evidence`,
  `_sidecar_evidence`, `_team_config_evidence`, `tracked_generated_paths`,
  `detect_install_mode`, the CLI (`--uninstall`), full-mode source check,
  and refusal messages.
- `scripts/sidecar_overlay.py` — `git_path` callers, `sidecar_evidence`,
  `rev_parse`, every target Git call, `_check_ignore`, `run_ignore_gate`,
  `_parse_check_ignore_verbose`, exclude-file parsing and writing,
  `_empty_staging`, preflight in `install_sidecar`, `_sidecar_source_violations`,
  the manifest model (`bootstrap_commit`), reporting, and a new uninstall
  entry point.
- `scripts/runtime_ownership.py` — the shared exact sidecar source allowlist.
- `scripts/validate_targets.py` — use the shared allowlist
  (`sidecar_allowed_relative_path`, `validate_sidecar_target`).
- `tests/test_install_bootstrap.py`, `tests/test_sidecar_install.py`,
  `tests/test_sidecar_update.py`, `tests/test_sidecar_overlay.py`,
  `tests/sidecar_test_helpers.py`.
- `README.md`, `docs/target-mapping.md`, `docs/architecture.md`, and
  `docs/sidecar-provider-contract.md` (implementation claims only).

## Steps

Every step adds regression tests that fail on HEAD `c90aac9` before the
change. For each refusal, assert exit 1 and that stderr names the path and the
remedy. Also assert that the `info/exclude` bytes, `git status`, and the
worktree are unchanged, and that no staging folder is created, in both the
real run and the dry run.

- [ ] **1. Run target Git calls without inherited repository variables (Decision 27; S10).**
  - **Owner:** `coder`
  - One helper returns `os.environ` without `GIT_DIR`, `GIT_WORK_TREE`,
    `GIT_INDEX_FILE`, `GIT_COMMON_DIR`, `GIT_OBJECT_DIRECTORY`,
    `GIT_ALTERNATE_OBJECT_DIRECTORIES`, and `GIT_NAMESPACE`. Every Git call
    against a target in `scripts/sidecar_overlay.py` and in mode detection
    uses it. Full-install steps after detection are unchanged.
  - Tests: an exported `GIT_DIR` that points at another repository, and an
    exported `GIT_INDEX_FILE`. The target gets its own block and manifest,
    and the other repository is untouched.

- [ ] **2. Harden mode detection (Decision 27; S1, S2, R5 sibling).**
  - **Owner:** `coder`
  - `_full_install_evidence`: `.claude/.git` counts only when it is a
    directory (checked with `lstat`) and `git ls-files -z -- .claude` prints
    nothing. A submodule's `.git` file, or an embedded repository that the
    outer index tracks as a gitlink, is team config instead.
  - Classify a failed `git rev-parse`: stderr saying "not a git repository"
    means no Git evidence (today's fresh-install default). Any other failure,
    for example "detected dubious ownership", aborts detection in every mode.
    The message quotes Git's error and names the remedy (for example
    `git config --global --add safe.directory <path>`).
  - `tracked_generated_paths` uses `-z` and `os.fsdecode`. It returns an
    empty list only for "not a git repository" and raises otherwise.
  - `sidecar_evidence` reads `info/exclude` as bytes, compares against the
    encoded marker lines, and never opens a non-regular file. A non-regular
    exclude file aborts detection with a remedy. Anything at the manifest
    path, including a dangling symlink, is sidecar evidence.
  - Tests:
    - A team `.claude` submodule, and an embedded repository tracked as a
      gitlink: a plain install refuses as team config, `--mode sidecar`
      proceeds, and the submodule's remote, branch, and files are unchanged.
    - `GIT_TEST_ASSUME_DIFFERENT_OWNER=1` aborts in every mode.
    - Latin-1 bytes, UTF-16 text, and a directory at `info/exclude`: a full
      install still works for the byte cases and refuses the directory.
    - A named pipe at `info/exclude` is refused without hanging. Guard the
      test with a timeout.
    - `core.quotePath=false` with a non-UTF-8 tracked name gives the
      team-config refusal, not a traceback.
    - `tests/test_install_bootstrap.py` passes unchanged except for new
      cases.

- [ ] **3. Validate Git-directory metadata before any write (Decision 26; R3, S6).**
  - **Owner:** `coder`
  - Build the manifest, staging, preserved, and exclude paths from
    `git rev-parse --absolute-git-dir` (run with the step 1 environment).
    Remove every remaining use of `git_path` for these paths. Update
    `tests/sidecar_test_helpers.py` if it still resolves paths through
    `git_path`.
  - Before any write, in the real run and the dry run, refuse when:
    - the manifest path is a symlink (dangling or not) or not a regular file;
    - the staging or preserved path is a symlink or exists and is not a folder;
    - `info/` is a symlink;
    - `info/exclude` is a symlink or exists and is not a regular file.
  - Check types with `lstat`. Never open a named pipe.
  - Tests:
    - Manifest as a folder, a dangling symlink, a symlink to a file, and a
      named pipe.
    - Staging as a regular file, and as a symlink to a folder holding a
      tracked file. The linked folder's contents must be untouched.
    - `info/` as a symlink to a shared folder; `info/exclude` as a folder and
      as a named pipe.

- [ ] **4. Require balanced exclude markers (Decision 26; S7).**
  - **Owner:** `coder`
  - The exclude file holds either no marker lines, or exactly one BEGIN line
    followed later by one END line. Anything else aborts before a write, in
    detection and in preflight, naming the line numbers. `_replace_exclude_block`
    replaces only a pair that preflight found intact.
  - Tests: an orphan BEGIN, END before BEGIN, two blocks, and a repeated
    BEGIN. Each is refused before any write, the person's own lines are
    byte-identical, and a normal block with CRLF line endings still works.

- [ ] **5. Make paths bytes-safe (Decision 29; R5, S15).**
  - **Owner:** `coder`
  - Use `os.fsdecode` for Git `-z` output and `os.fsencode` for Git input
    and for the relative paths hashed in `compute_unit_hash`. Read and write
    `info/exclude` as bytes, and encode block lines with `os.fsencode`. Run
    the explanatory `check-ignore -v` call with `-z` and parse it as bytes.
    Print paths with undecodable bytes escaped.
  - Cover every place the verification report listed: `compute_unit_hash`,
    `sidecar_evidence`, the index reader, `_check_ignore`, `_excluded_units`,
    `run_ignore_gate` input and output, the dry-run and apply exclude
    reads and writes, `_info`, and `tracked_generated_paths`.
  - A name that gitignore cannot express (it contains a newline or a
    carriage return) never gets a line. It is reported, and it must never
    reach the exclude file, even during the gate.
  - Tests:
    - An unrelated staged `bad-\xff.txt`: the install succeeds and status is
      unchanged.
    - A `\xff` file inside an owned unit: it is locally modified, kept,
      still hidden, and a rerun is stable.
    - A retained `\xff` file after a takeover: its line is written as raw
      bytes, and the gate passes.
    - A Latin-1 line of the person's own in `info/exclude` is preserved byte
      for byte.
    - Retained names with a newline and with a trailing carriage return: they
      are reported, and no raw pattern line is ever written. Check the block
      at the gate with a fault point.
    - A fixed fixture's unit hash equals the value computed before this
      change.

- [ ] **6. Check repository boundaries and filesystem shape (Decision 28; S5, S11).**
  - **Owner:** `coder`
  - For every existing write root and bridge parent, `git rev-parse
    --show-toplevel` run there must equal the target, and the target index
    must have no gitlink at or above it. Otherwise abort with "sidecar mode
    does not support the nested repository or submodule at `<path>`; nothing
    was written".
  - Every existing ancestor of each planned path must be a real folder
    (`lstat`) with the target's `st_dev`. Every folder that a move changes
    must be writable (`os.access(..., os.W_OK)`).
  - Tests:
    - A nested clone at `.claude/skills`: refused, and the nested
      repository's status is unchanged.
    - A submodule at a write root: refused with the new message, not the
      `.gitignore` remedy.
    - A regular file at `.agents`, and a read-only unit folder during an
      update: refused before any write.
    - A different `st_dev`, simulated with a monkeypatched `os.lstat` result.

- [ ] **7. Require complete, exact sources (Decision 31; S13, S14, L2).**
  - **Owner:** `coder`
  - Move the exact sidecar source set into `scripts/runtime_ownership.py`:
    - every sidecar skill's `SKILL.md` at every write root;
    - `LICENSE` in the `ponytail` and `ponytail-review` folders at every
      write root;
    - every bridge.
  - `validate_targets.py` and the installer both use this set. The installer
    refuses a source with any missing or extra file.
  - Full mode refuses a source that lacks `.claude/hooks/scripts/state-sync.sh`,
    or whose files all fall inside the sidecar set.
  - Tests:
    - An empty source and a source with only `.claude/`: refused, and no unit
      is removed.
    - A source with an extra file: refused.
    - `--source dist/sidecar` in full mode, on a fresh target and on an
      existing full consumer: refused before any write.
    - A crafted tree gets the same verdict from the validator's check and
      the installer's check.

- [ ] **8. Remove `bootstrap_commit` (Decision 33; R6).**
  - **Owner:** `coder`
  - Remove it from the manifest dataclass, the serializer, the planner
    parameter, and the install call. Parsing still accepts and ignores it.
    `KNOWN_SCHEMA_VERSION` stays 1.
  - Tests: a new manifest has no such key; an old manifest with the key still
    parses; the first update rewrites the manifest once and the next run
    changes nothing.

- [ ] **9. Add `--uninstall` (Decision 34; design item 4).**
  - **Owner:** `coder`
  - CLI: `install_bootstrap.py TARGET --mode sidecar --uninstall`, also
    accepted with no `--mode` when detection finds sidecar evidence.
    `--dry-run` works. Refuse `--uninstall` with `--mode full`, and with full
    evidence. With no sidecar evidence, print "no sidecar found; nothing to
    do" and exit 0. `update_consumers.py` never passes it.
  - Behavior, through the same preflight (steps 3, 4, 6) and Phase G's
    planner with an empty desired set:
    - a unit whose content matches its record is removed;
    - a locally modified or unfinished unit is preserved (Decision 24);
    - team and foreign content is untouched;
    - retained files lose their lines, so they become visible, and each is
      reported.
  - Order: move or remove every unit first. Only then remove the whole
    block, then delete the manifest, then remove the staging folder. When a
    preserve destination already exists, keep that unit, its line, the
    block, and the manifest, report the conflict, and exit 1.
  - Keep the preserved folder, and print its path.
  - Tests:
    - A clean install then uninstall: status matches the state before the
      install, and no block, manifest, staging folder, or sidecar file
      remains.
    - An edited copy is preserved; a retained file becomes visible and is
      reported; team and foreign content is untouched.
    - A second uninstall prints "nothing to do".
    - Every fault point converges on rerun, and a dry run writes nothing.
    - Full evidence and `--mode full --uninstall` are refused.
    - `update_consumers.py` never forwards the flag.

- [ ] **10. Correct preflight and installer messages (Decision 36; S15, S16).**
  - **Owner:** `coder`
  - A gate failure lists only the paths that are not ignored, with the
    winning rule from `check-ignore -v -z`.
  - The ignore-gate remedy says to ask the team to change a rule, or to
    remove the person's own negation from `info/exclude`. It never tells the
    person to edit the team `.gitignore` themselves.
  - The invalid-manifest remedy uses the big plan's text.
  - Sidecar mode no longer suggests `--allow-self`.
  - `--mode full` in a linked worktree or a subdirectory says what was found
    and never tells the person to remove the main worktree's sidecar.
  - A missing default source says to run `generate_targets.py --all`; a
    missing explicit `--source` names that path.
  - A symlinked projection parent says sidecar mode does not support it and
    that nothing was written. It never tells the person to replace tracked
    team content.
  - Remove "or has no commits" from the docstrings at
    `install_bootstrap.py:1180-1182` and `1190-1192`.
  - Tests assert each message.

- [ ] **11. Documentation pass (Decisions 35, 36; S8, S17, design item 4).**
  - **Owner:** `documenter`
  - `README.md`:
    - Replace the manual removal steps with `--uninstall`.
    - Keep a safe manual fallback: skip any unit that `git ls-files` lists,
      delete only files whose hash matches the manifest, never delete
      retained files, move edited files out first, and remove the block
      last.
    - Correct each claim listed under S17: line 61, the linked-worktree
      reason, "before anything is written", exit codes, and "a second run
      writes nothing".
    - Add the hidden-file warning (Decision 35).
  - `docs/target-mapping.md` and `docs/architecture.md`: the exact allowlist
    replaces the self-containment claim; add uninstall and the new refusals.
  - `docs/sidecar-provider-contract.md`: change only statements about the
    implementation that are now false.
  - Never hand-edit `openwiki/`. Phase I refreshes it.

## Acceptance Criteria

- Each S1, S2, S5, S6, S7, S10, S11, S13, S14, R3, R5, and R6 scenario has a
  test that fails on `c90aac9` and passes after this phase.
- A plain install or batch update never takes over a team `.claude`
  submodule, and never picks full mode after a Git error.
- No run follows a symlink inside the Git directory, erases a personal
  ignore line, or crashes on a legal Git file name.
- An incomplete or wrong source is refused before any write, in both modes.
- `--uninstall` removes only unmodified sidecar files and sidecar metadata,
  preserves edited copies, and is idempotent.
- Full-install behavior is unchanged apart from the new refusals, and
  `tests/test_install_bootstrap.py` passes.
- The README and docs match the code, and there are no manual steps left
  that can delete personal or team files.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_sidecar_overlay.py tests/test_sidecar_install.py tests/test_sidecar_update.py tests/test_install_bootstrap.py -q --tb=short
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- The operator installs the sidecar into the Phase A fixture, runs `--uninstall`, and checks that `git status` there matches the state before the install.

## Review Profiles

- `code`
- `architecture`
- `security`
- `tests`
- `ponytail`
- `documentation`

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT).

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
