# Sidecar overlay review, round 2

**Date:** 2026-09-25
**Big plan:** [Consumer Sidecar Bootstrap Overlay](../plans/consumer-sidecar-bootstrap-overlay.md)
**Implementation branch:** `consumer-sidecar-bootstrap-overlay_implementation`
**Reviewed HEAD:** `c90aac9`
**Follows:** [round 1](2026-09-25_consumer-sidecar-bootstrap-overlay-review.md)

Verdict: **FAIL.** Round 1's six findings and five design items are all confirmed at
HEAD. Round 2 adds seven MAJOR findings, one accepted-risk design note, and a set of
MINOR findings. No repository file was changed during this review.

## Method

Five independent investigations ran against HEAD `c90aac9`. Four wrote pytest
reproductions in a session scratch folder (outside the repository) using temporary
Git repositories and `tests/sidecar_test_helpers.py`. Each reproduction asserts the
promised behavior, so a failing test means the defect is present. The main agent
re-ran the MAJOR reproductions for S1, S3, S4, and S7 and saw them fail as reported.
The repository stayed clean throughout (`git status --short` empty). The existing
sidecar suites passed at HEAD (101 tests).

1. Round 1 verification: 42 reproductions, all six findings and five design items confirmed.
2. Planner decision matrix: every classification row against every cross-cutting rule.
3. Filesystem shapes and Git repository states.
4. Mode detection, updater, generator and validator, documentation claims.
5. Workflow gates: how to add a phase after a completed knowledge-refresh phase.

Scratch reproductions are not durable. Every finding below names its scenario
precisely enough to rebuild the regression test in `tests/`.

## Round 1 findings, confirmed

All cited lines are still correct.

- **R1 MAJOR, adopt escapes team precedence** (`scripts/sidecar_overlay.py:726-745`).
  The collision loop rewrites only `unchanged`, `update`, and `install`. Siblings that
  share the cause, all reproduced: a crash before the manifest write followed by a
  collision; a foreign copy at one write root with an adoptable copy at the other; a
  team-tracked copy at one write root with an adoptable copy at the other. The wrong
  state clears on the next run, but the first run's report is false.
- **R2 MAJOR, symlinked read roots and skill entries are treated as empty**
  (`:1084-1097`). Reproduced for all three read-only roots, for a symlinked root, and
  for a symlinked skill folder. A naive "follow every link" fix is wrong: the common
  layout `.github/skills -> ../.claude/skills` would then see the sidecar's own copy as
  a team skill, and runs would alternate install, remove, install.
- **R3 MINOR, Git-directory metadata is validated only after writes.** Siblings: a
  regular file at the staging path, `info/exclude` as a folder or a named pipe (the
  pipe hangs forever), and a dangling or pipe manifest treated as absent. The last one
  un-hides a locally modified unit, which is worse than a crash.
- **R4 MINOR, ownership comes from disk, not the Git index** (`:1043-1081`).
  Siblings: sparse checkout and `skip-worktree` entries, a gitlink at a skill path, a
  tracked file deleted after a takeover, read-only root names read from disk only, and
  a tracked team symlink that uses a sidecar skill name. Each one either aborts the
  whole install or misses a collision.
- **R5 MINOR, non-UTF-8 names and bytes crash the run.** Every UTF-8 assumption is
  listed in the fix plan. One sibling is a regression for full installs:
  `sidecar_evidence` (`:862`) decodes `info/exclude` as strict UTF-8, so a Latin-1 or
  UTF-16 byte there crashes `detect_install_mode` for `--mode full` too.
  `tracked_generated_paths` (`scripts/install_bootstrap.py:1127-1136`) also reads
  `git ls-files` without `-z`.
- **R6 MINOR, `bootstrap_commit` is always empty.** No reliable source exists:
  `dist/` is local and ignored, and the full install records no commit either. Remove
  the field. No schema bump is needed, because the key is optional on read.
- **Design 1, one precedence rule** and **Design 3, transition tests:** confirmed.
- **Design 2, a modified copy stays discoverable next to a team skill:** confirmed.
  The report also says "skips `<skill>` at every root" while the copy stays, and the
  locally modified remedy is wrong once the name is taken, because a rerun removes a
  restored copy instead of taking the current version.
- **Design 4, removal instructions:** worse than round 1 said. Following
  `README.md:503-512` literally deletes hand edits, retained personal files, and,
  after a pull, a team-tracked file.
- **Design 5, scope limits:** accurate.

## New MAJOR findings

- **S1, a team `.claude` submodule counts as full-install evidence**
  (`scripts/install_bootstrap.py:1167-1169`). Any `.claude/.git`, including a
  submodule's `.git` file or an embedded repository tracked as a gitlink, selects
  `full`. A plain install, and therefore every `update_consumers.py` batch, took over
  the team submodule in the reproduction. It changed its `origin`, moved it to an
  orphan `ai-state` branch, overwrote the team `settings.json`, deleted a team skill,
  and set outer `core.hooksPath`. `--mode sidecar` is refused, and the refusal points
  to the takeover. This breaks the Done Criteria's "never takes over an unbootstrapped
  repository that tracks a path the full install writes".
- **S2, a Git error is read as "no evidence"** (`install_bootstrap.py:1178-1193`,
  `1127-1137`, `1278`). When Git refuses the repository (for example "dubious
  ownership", common with containers, WSL, and shared drives), detection falls through
  to `full`. A team repository that tracks `.claude/` is then not refused. A sidecar
  target with `--mode full` is not refused, and with no mode it picks `full`.
- **S3, the exclude line proves ownership only in the adopt row**
  (`scripts/sidecar_overlay.py:401-418`, `544-545`, `605-628`, `521`). Decision 10
  makes the sidecar's own exclude line the proof of ownership, but every other
  recovery path treats "no manifest record" as "not ours". Reproduced:
  - A crash during a fresh install, then new content before the rerun: the unit
    becomes foreign, its line is dropped, and sidecar files appear in `git status`.
  - A crash, or the manifest moved aside as the remedy says, then a skill stops
    shipping: the unit is never classified. Its line is dropped silently, and the
    files become visible.
  - A crash during a fresh install, then the team tracks a file in the unit: the unit
    becomes `team_owned`, and the sidecar's other files become visible.
  - A crash during an update, then a team takeover: sidecar bytes are marked RETAINED
    as if they were personal files.
- **S4, the ignore gate misses directory-only rules** (`:1169-1184`, `1439-1440`,
  `1399`). Unit folders are gated as bare paths before they exist, so Git skips rules
  that end in `/`. Team rules such as `!.claude/skills/*/`, `!.claude/skills/ponytail/`,
  or `!**/ponytail/` pass the gate. The install and the dry run both report success,
  sidecar files appear in `git status`, and only the next run aborts. Gating `unit/`
  or the unit's file paths catches these rules (verified in scratch).
- **S5, a nested Git repository under a write root gets visible sidecar files**
  (preflight at `:1507-1535` has no repository-boundary check). If a team clones a
  shared skills repository into `.claude/skills`, the outer status stays clean, but
  the nested repository shows the sidecar files as untracked, where `git add -A` would
  commit and push them. A submodule at a write root fails safely, but with the
  misleading `.gitignore` remedy.
- **S6, Git-directory paths are resolved through symbolic links**
  (`git_path`, `:826-847`; `:1447`, `1334-1337`, `1537`, `1552-1557`).
  `rev-parse --path-format=absolute --git-path` resolves links. A link at
  `.git/ai-bootstrap-sidecar-staging` therefore makes every run `rmtree` the linked
  folder: a team-tracked `src/app.py` was deleted, with exit 0. A dangling manifest
  link writes the manifest outside the Git directory. A linked `.git/info/` folder is
  followed, so a shared exclude file elsewhere is rewritten. This needs a link planted
  inside `.git`, so it is rare, but the effect is destructive.
- **S7, unbalanced exclude markers erase the person's own ignore lines**
  (`:1100-1107`, `1132-1152`, `1451`). With a `# BEGIN ai-bootstrap sidecar` line but no
  END line, or END before BEGIN, a run appends a new block and then replaces everything
  from the orphan BEGIN to the new END. The person's own lines, for example
  `.env.personal`, are deleted, and those files appear in `git status` with exit 0. A
  partial manual removal is enough to cause it.

## Design note, accepted risk

- **S8, a hidden file loses Git's overwrite protection.** Git refuses to overwrite a
  visible untracked file on checkout or merge, but it overwrites an ignored one
  silently. A locally modified sidecar copy, or a retained file, is ignored on
  purpose, so a team commit at the same path replaces it on the next pull. The
  sidecar itself never overwrites it. The big plan accepted this in Devil's Advocate
  point 11 ("tell users not to keep personal edits in sidecar files"), but no user
  doc or remedy says it clearly today.

## New MINOR findings

- **S9, an empty leftover unit folder is classified foreign forever** (`:571`, `627`).
  The product's own path leads there: takeover, then untrack, then delete the retained
  file as told. The empty folder then blocks the skill at every root.
- **S10, inherited Git environment variables redirect the run.** An exported
  `GIT_DIR` sends the queries and writes to another repository. The block and
  manifest land there, and the target's sidecar files stay visible. `GIT_WORK_TREE`,
  `GIT_INDEX_FILE`, and `GIT_COMMON_DIR` have the same class of problem.
- **S11, bad filesystem shapes crash after the exclude write, on every run.** Examples:
  a regular file at `.agents`, a read-only unit folder during an update, and a mount
  point under a write root (`EXDEV` on `os.replace`). Nothing is un-hidden, but the run
  never converges.
- **S12, case variants.** With `core.ignorecase=true` on a case-sensitive filesystem,
  the exclude line `/.claude/skills/ponytail` also hides a visible, personal
  `.claude/skills/Ponytail/`. On a case-insensitive filesystem, a team-tracked
  `Ponytail/` is the same folder, but the case-sensitive comparisons classify it as
  foreign or locally modified.
- **S13, an empty or partial `dist/sidecar` silently uninstalls.** With an empty
  source the run reports "removed 10" and exits 0. The installer's source check is
  looser than the validator's exact allowlist.
- **S14, full mode accepts `dist/sidecar` as `--source`.** On a fresh target it writes
  the `.gitignore` block, `bootstrap-ownership.env`, and a dangling `core.hooksPath`,
  then exits 1. On an existing full consumer it drops the file count from 367 to 56.
- **S15, the printed report is inaccurate in several places.**
  - A gate failure lists every checked path, including correctly ignored ones.
  - When a write-root copy is foreign, the read-only collision report is suppressed.
  - A real run prints counts only, never the files a takeover deleted.
  - After a crash during an update and a deleted exclude block, units whose content
    already equals the desired content are reported as locally modified.
  - A newline or trailing carriage return in a retained file name writes a raw
    pattern line such as `src` into `info/exclude` during the gate, then blocks every
    later run with the wrong remedy.
- **S16, remedy wording is wrong or unsafe.**
  - Locally modified: "delete or restore" loses edits, and "take the current version"
    is false once the name is taken or the skill stops shipping.
  - Retained: a plain `git add` refuses a hidden file, so the text must mention
    `git add -f`.
  - Ignore gate: it says to fix the team `.gitignore`, which is a non-goal, and it
    ignores the person's own negations.
  - Team-owned: the wording is odd for a bridge file, and it names the folder when
    only one file inside is tracked.
  - Invalid manifest: it does not warn that files will become visible in
    `git status`.
  - Other messages: sidecar mode suggests `--allow-self`. `--mode full` in a linked
    worktree says to remove the main worktree's sidecar. The missing-source message
    says to point `--source` somewhere even when none was passed. The symlink abort
    tells the person to replace tracked team content.
- **S17, documentation claims.**
  - Unsafe removal steps appear in `README.md:503-512` and
    `openwiki/operations/sidecar-overlay.md:176-177`.
  - Overstated or wrong claims:
    - `README.md:61` ("neither mode is detected by guessing").
    - `README.md:453-457`, the stated reason for refusing linked worktrees.
    - `README.md:478-480`, `549-552`, `605-609`, the "before anything is written" and
      exit-code claims.
    - `openwiki/operations/sidecar-overlay.md:145`, `153`.
    - `openwiki/operations/install-ownership-and-runtime-checks.md:52` and the docstrings
      at `install_bootstrap.py:1180-1182`, `1190-1192` ("or has no commits").
    - The `docs/architecture.md` self-containment claim.
    - OpenWiki claims `229e75d4` and `e46454b4`.

## Latent or deferred

- **L1:** removing a bridge or write root in a future version makes every existing
  install abort on manifest validation. This is latent until such a change ships.
- **L2:** write-root collisions look only at units the planner tracks. This is latent,
  because `render_sidecar` always writes both roots, and it becomes impossible once
  S13 enforces a complete source.
- **L3:** collisions are keyed on folder names, not on frontmatter `name:`. No client
  run verified whether this matters.
- **L4:** `_validate_unit_path` does not reject a backslash. There is no Windows
  sidecar claim.
- **Uninstall command:** optional, per round 1.

## Workflow finding: adding a phase to this completed plan

The last phase, `2026-09-24_phase-E-sidecar-knowledge-refresh`, is a completed
knowledge-refresh phase. `scripts/validate_plan_frontmatter.py:280-295` requires the
knowledge-refresh phase to be unique and last, and the commit gate runs it on every
outer commit.

- **Append a fix phase after E:** fails the validator.
- **Insert it before E:** the post-commit hook never advances, and the push and PR
  gates fail permanently.
- **Rename E:** breaks the receipt chain of completed phases.

The only shape that keeps the final refresh and the stale-claims audit last:
keep E, append the fix phases and a new `-knowledge-refresh` phase, and change the
validator to accept an earlier knowledge-refresh phase that is already complete. This
was tested in a scratch clone, where the 626 existing validator and runtime tests
passed. It is a control-plane change that ships to consumers.

## Checked and correct

- Crash convergence with an unchanged source: 45 combinations match a clean run.
- A second run changes nothing, down to bytes and modification times.
- A dry run matches the real run's summary and report in 15 states.
- Other working cases:
  - separate Git directory (`gitdir:` file);
  - a repository with no commits;
  - CRLF in `info/exclude`;
  - hard links;
  - `git add -N` and staged-only files, which count as team-owned.
- Manifest validation rejects absolute, `..`, and out-of-namespace paths.
- Linked worktrees are refused.
- Updater: it continues past failures, prints `FAILED: <path> (exit N)`, and exits 1.
- Generation into a scratch folder is byte-identical to `dist/`.
- `runtime_ownership.py` matches its `dist/multi-agent` copy.
- `detect_install_mode` follows the plan's mode table row by row.
