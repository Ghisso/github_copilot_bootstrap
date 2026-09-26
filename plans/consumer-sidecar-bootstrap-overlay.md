---
name: consumer-sidecar-bootstrap-overlay
type: big-plan
status: complete
originating_branch: dev
implementation_branch: consumer-sidecar-bootstrap-overlay_implementation
started_at: 2026-09-25T03:07:56Z
phases:
  - 2026-09-24_phase-A-sidecar-provider-contract
  - 2026-09-24_phase-B-sidecar-profile-and-ownership
  - 2026-09-24_phase-C-sidecar-install-and-provider-bridges
  - 2026-09-24_phase-D-sidecar-update-and-reconciliation
  - 2026-09-24_phase-E-sidecar-knowledge-refresh
  - 2026-09-25_phase-F-reopen-completed-big-plan
  - 2026-09-25_phase-G-sidecar-ownership-and-precedence
  - 2026-09-25_phase-H-sidecar-preflight-robustness-and-uninstall
  - 2026-09-25_phase-I-sidecar-hardening-knowledge-refresh
  - 2026-09-26_phase-J-sidecar-safety-follow-up
  - 2026-09-26_phase-K-sidecar-follow-up-knowledge-refresh
current_phase: 
---

# Big Plan: Consumer Sidecar Bootstrap Overlay

## Context

The bootstrap assumes it owns the consumer repository's agent harness. That
is right for personal and new repositories. It is wrong for an existing team
repository that already tracks one or more of:

```text
.claude/  .agents/  .codex/  .github/  .devcontainer/  CLAUDE.md  AGENTS.md  GEMINI.md
```

The full installer is a takeover, and its protection is narrower than it
looks. Checked in `scripts/install_bootstrap.py` on 2026-09-24:

- Its only refusal about existing content is `validate_agents_takeover`, for
  an `.agents/` tree it cannot prove it generated.
- It treats any non-empty `.claude/` without `.git` as legacy state and turns
  it into a nested Git repository.
- Under `.claude/`, it overwrites the files it generates and deletes every
  other file that is not consumer state, tracked or not. A copy survives only
  in the new nested repository's history.
- Inside the root adapter paths (`RESTORABLE_ROOT_PATHS`), it deletes every
  untracked file it does not generate as an "obsolete generated file".
  Tracked root adapter files such as `CLAUDE.md` and `AGENTS.md` are
  preserved, except the Copilot surface in committed mode, where tracked team
  Copilot files are overwritten or deleted.
- It overwrites `.devcontainer/` even when the team tracks it.
- It rewrites the tracked `.gitignore`, sets `core.hooksPath`, and only warns
  about already-tracked generated paths, after copying.

A full install into a team repository therefore changes and deletes team
files.

This plan adds a second deployment model:

```text
FULL INSTALL     bootstrap owns the agent harness (unchanged)
SIDECAR INSTALL  a private, per-clone developer overlay inside a team-owned harness
```

The sidecar exposes a few generic skills and one short always-on rule per
client. It installs no hooks, no lifecycle, no nested AI-state repository,
no MCP configuration, and no devcontainer. It never changes a tracked file.

This is control-plane/high-risk work: it changes installer ownership,
generated provider surfaces, consumer update behavior, and safety boundaries.

## Goals

- Add `--mode sidecar` beside the full install:
  `uv run python scripts/install_bootstrap.py TARGET --mode sidecar`.
- Keep full-install behavior unchanged for full consumers and for explicit
  `--mode full`. Without `--mode`, the installer never full-installs a
  target that carries sidecar evidence, and it refuses one that tracks an
  agent-harness path (a path under `FULL_INSTALL_ROOT_PATHS`) and has no
  bootstrap evidence (Decisions 18 and 46).
- Project an allowlisted skill set into `.claude/skills/<skill>/` and
  `.agents/skills/<skill>/`, plus one bridge file per client where Phase A
  proves an additive native mechanism. Vendored skills keep their license
  notice (Decision 19).
- Keep every sidecar file out of the team's Git state through the local
  `info/exclude` file, proven with `git check-ignore` before any unit is
  written.
- Record ownership in a manifest inside the Git directory, where it cannot be
  tracked.
- Use one reconciliation code path for first install, rerun, and update.
- Let `update_consumers.py` auto-detect sidecar consumers, including in batches
  that mix full and sidecar consumers. A refused or failed target no longer
  stops the batch: the updater finishes the other targets and reports every
  failed one at the end (Decision 20).
- Never overwrite, delete, or shadow team-owned content in any skill folder a
  supported client reads. Preserve and report local edits to sidecar-owned
  files.
- Phases F-I (added 2026-09-25): make team precedence, ownership proof, and
  Git-directory safety hold in every recovery path and repository shape the
  two reviews found, and fix the messages and docs they found wrong
  (Decisions 22-33, 35, 36).
- Add `--uninstall`, which removes only unmodified sidecar files and keeps
  every personal file (Decision 34).

## Non-Goals

- Replacing or weakening the full installer.
- Automatic full -> sidecar or sidecar -> full migration.
- Global per-user installation (`~/.claude`, `~/.codex`, `~/.agents`, ...).
- Editing tracked `.gitignore` or tracked team instruction files.
- Symlinks, custom agents, hooks, the plan/review/commit lifecycle, MCP
  servers, plans, MEMORY, or session logs in the consumer.
- A worktree folder holding a canonical copy of the sidecar content (the
  earlier `ai-bootstrap/` root; see Decisions).
- Linked worktrees in v1, including the worktrees that clients create for
  background sessions (see Decision 15).
- Copilot CLI or Copilot cloud agents. Copilot support means VS Code, which
  matches the README's existing Copilot claim.
- Skill-name prefixes in v1.
- Sidecar support when a projection parent directory is a symlink, or when
  the Git directory is on a different filesystem from the worktree.
- Merging into an existing `CLAUDE.local.md`.
- An uninstall command that deletes anything other than unmodified sidecar
  files, sidecar metadata, and the sidecar's exclude block (Decision 34
  replaced the earlier "no uninstall command" non-goal).
- An always-on Codex instruction. Every documented Codex mechanism either
  replaces `AGENTS.md` or needs a config file (Decision 7).
- Intent records or any other multi-step transaction state in the manifest
  (Decision 10).
- Manifest schema migration code before a second schema version exists.
- Collision checks in nested per-folder skill roots below the repository
  root. Codex, which reads them, shows both copies of a duplicate name
  instead of hiding one (documented).

## Decisions

These decisions come from the 2026-09-24 reviews of the first draft, the
first revision, and the second revision. The second review checked every code
claim below against `dev`, tested the Git behavior in a scratch repository
with Git 2.43.0, and read each client's documentation. Its user decisions:
drop the pending crash-recovery state, let batch updates skip a refused target
and report it at the end, and discard the unrelated uncommitted edit on `dev`.

| # | Topic | Decision | Why |
| --- | --- | --- | --- |
| 1 | Canonical folder | Drop `ai-bootstrap/`. The manifest lives at `git rev-parse --path-format=absolute --git-path ai-bootstrap-sidecar.json`. | No client reads that folder. It stored every skill a third time and added a reconciliation class. A manifest inside the worktree can be committed or forged by a pulled commit; a Git-directory file cannot be tracked. |
| 2 | Content source | New generator target `dist/sidecar/`: add `"sidecar"` to `TARGETS` and a `render_sidecar()` branch in `generate()`, which today raises `ValueError` for any target except `multi-agent`. The tree mirrors consumer-relative paths. | Rendering and validation stay in the generator; the installer only copies. `--all` and `update_consumers.py` then regenerate it. |
| 3 | Profile | Constants in `scripts/runtime_ownership.py`: `SIDECAR_SKILLS = ("debug-investigator", "humanize", "ponytail", "ponytail-review")`. | That module is already the single ownership contract for generator, installer, and validator. No JSON loader is needed. Verified: none of the four skills references another skill, and each excluded skill (`code-style`, `testing-patterns`, `run-tests`, `refactor`) names `.claude/instructions/` or `.claude/scripts/verify.py`. |
| 4 | Self-containment | A separate `SIDECAR_TEXT_REPLACEMENTS` constant in `scripts/generate_targets.py` rewrites the remaining bootstrap references at render time. `validate_targets.py`, which already imports generator constants, rejects any sidecar file that still names a path the sidecar does not install, or still contains one of the replaced phrases. | The known references are the only ones in the four skills (verified): `humanize` cites `../../third_party/avoid-ai-writing/`; `ponytail` says "the workflow's final Ponytail diff review remains mandatory"; `ponytail-review` says "Return findings to the coder". `str.replace` does not fail on a miss, so the phrase check catches a replacement that stops matching. `TARGET_PATH_REPLACEMENTS` stays keyed by client names. The hash pins cover only the `shared/` sources, so source skills and vendored Ponytail stay unchanged. |
| 5 | Bridge content | One body in `shared/sidecar/bridge.md`: the precedence rule, plus "apply `ponytail` in `full` mode to coding tasks unless repository guidance says otherwise, and use `ponytail-review` on non-trivial diffs". Nothing else. Each bridge adds only its client's frontmatter: none for Claude Code, `applyTo: "**"` for Copilot, and `trigger: always_on` for Antigravity. | Without hooks, the bridge is what keeps Ponytail active. That is its whole value. Antigravity silently discards a rule file without a valid `trigger` (documented). |
| 6 | Claude bridge | Candidate `.claude/rules/ai-bootstrap-sidecar.md` with no `paths` frontmatter. Fallback `CLAUDE.local.md` only if Phase A disproves the rules file and `CLAUDE.local.md` is absent. | A sidecar-named file, like the other bridges. Documented: rules load in addition to `CLAUDE.md`, and `CLAUDE.local.md` is still supported and additive. Not documented: whether a rule without `paths` loads in every session. `CLAUDE.local.md` is one personal file that users often already own. |
| 7 | Codex bridge | None: Codex is skill-only. Rejected: `AGENTS.override.md`, `project_doc_fallback_filenames`, `developer_instructions` in a project `.codex/config.toml`, and any `~/.codex` change. | Documented: Codex uses at most one instruction file per folder, so `AGENTS.override.md` replaces `AGENTS.md`; fallback names apply only when `AGENTS.md` is missing; `developer_instructions` needs a config file that loads only for trusted projects. Each either suppresses team guidance or needs a file the sidecar must not write. |
| 8 | Collisions | Collision checks cover every repository skill folder a supported client reads (the read list), not only the folders the sidecar writes (the write list). Phase A freezes the read list. The documented starting list is `.claude/skills/`, `.agents/skills/`, and `.github/skills/`, plus `.agent/skills/` (Antigravity legacy) and `.codex/skills/` (read by Codex's source, undocumented). A skill name taken by non-sidecar content in any read folder is skipped at every write root and reported. A taken bridge path skips that bridge and is reported. | Copilot in VS Code reads `.github/skills/`, `.claude/skills/`, and `.agents/skills/` (documented), and its Local agent keeps the first skill it finds (source). Without this, a sidecar copy could hide a team skill in `.github/skills/`. Installing at one root while the team owns another would shadow the team skill in clients that read both. Checking extra folders is always safe. |
| 9 | Failure classes | Unsafe states abort that target before any write, with a non-zero exit. Per-path conflicts skip that path, exit 0, and print a summary with a remedy. | A single colliding path should not block the whole overlay. Batch handling of a non-zero exit is Decision 20. |
| 10 | Crash recovery | No intent records. Safety comes from write order and atomic moves. The exclude block is written first. Each unit is built in a staging folder inside the Git directory; the old copy is moved into staging, and the new copy is moved into place with `os.replace`. The manifest is written last, through a temporary file and `os.replace`. A rerun adopts a unit whose bytes equal the desired content only when the sidecar's exclude block already lists that unit. Every run empties the staging folder before it writes units. | Pending records could finish work without re-checking files a person changed after a crash. With atomic moves, each unit is old, new, or absent after any crash, and the ordinary rows handle all three: unchanged or update, adopt, and install. Requiring the sidecar's own exclude line means adoption never hides a file that was visible, and never claims content that no earlier sidecar run planned. |
| 11 | Mode detection | One function in `install_bootstrap.py`, landing in Phase C. It reads only the target and runs first. The installer then chooses the source (`dist/multi-agent/` or `dist/sidecar/`; `--source` now defaults to none, so an explicit value is visible) and only then runs `validate_install_roots`. The sidecar path refuses a source that is not a sidecar tree. | `update_consumers.py` calls the installer without `--mode`, so detection must live in the installer and must exist before any sidecar can be installed. The default source depends on the detected mode, so detection comes before root validation. |
| 12 | Manifest fields | `schema_version`, per-unit records with per-file SHA-256 hashes, `retained` entries, and a diagnostic `bootstrap_commit` that no decision reads. No timestamps and no pending flags. Rewrite the manifest and the exclude block only when their bytes change. | Timestamps would break "a second update changes nothing". Per-file hashes are needed to clean up after a team takeover (Decision 16). |
| 13 | Full-only options | On a sidecar target, `--commit-copilot-surface`, `--no-commit-copilot-surface`, `--state-remote`, `AI_STATE_REMOTE`, and `--allow-self` are ignored with one warning. In sidecar mode `validate_install_roots` always receives `allow_self=False`, so a sidecar can never target this repository. `--local-only` is accepted as a no-op. `--dry-run` works. | `update_consumers.py` forwards `--dry-run`, `--local-only`, `--allow-self`, and the Copilot option to every target in a batch (verified), and `AI_STATE_REMOTE` reaches every target through the environment. |
| 14 | Claims follow evidence | A projection root or bridge path ships only when at least one client has `native-run` evidence for it in Phase A. A client without that evidence is documented as unverified, not supported. If no client reaches `native-run` evidence, cancel Phases B-E. | No later phase may depend on "probably discovered" behavior, and without evidence there is nothing to ship. |
| 15 | Worktrees | Sidecar mode aborts in a linked worktree (absolute `--git-dir` differs from absolute `--git-common-dir`). Document two side effects: the main worktree's exclude lines also hide those paths in every linked worktree, and worktrees that clients create for background sessions contain no sidecar files, because those tools copy ignored files only when they are listed (`git.worktreeIncludeFiles` in VS Code, `.worktreeinclude` for the Codex app). | Verified with Git 2.50 and again with 2.43.0: `info/exclude` is shared by all worktrees, while `--git-path ai-bootstrap-sidecar.json` is per worktree. Trimming the shared block from one worktree would expose another worktree's files. The client worktree behavior is documented by VS Code and Codex. |
| 16 | Team takeover | When the team starts tracking a file in a unit that the manifest records: delete untracked files in that unit whose bytes match the record; keep every other untracked file there that is currently ignored as `retained`, each with its own escaped exact-path line (Decision 17); leave visible untracked files alone. From the step-2 exclude write until step 3 deletes them, the matching files keep their own exact-path lines too, so a crash never exposes them. Report retained files on every run until they are deleted or tracked. When the team tracks a unit that the manifest does not record, the unit is simply team-owned: skip and report, add no line, and record nothing. | Verified: `git checkout` silently overwrites an ignored file with the team's tracked version and leaves our other files behind. Dropping the directory line would then show them in `git status`, and `git add -A` would commit them. Keeping the directory line instead would hide the team's own new files in that folder. Without a record, those untracked files were never ours to hide. |
| 17 | Ignore gate | Pipe every path that must stay ignored to `git check-ignore --stdin -z` without `-v`, and pass only when the printed set equals that set, byte for byte. Use `-v` only to explain a failure. Exact-path lines escape the gitignore pattern characters: `\`, `*`, `?`, `[`, a leading `!` or `#`, and trailing spaces. | Verified: with a team `!.claude/skills/**` rule, `git check-ignore -v` exits 0 although the file is not ignored, and `--stdin` exits 0 when any one path is ignored. Without `-z`, non-ASCII names come back quoted, so the sets never match. An unescaped `notes[1].md` line does not hide that file but hides an unrelated `notes1.md`. |
| 18 | Unbootstrapped team repository | With no `--mode` and no bootstrap evidence, abort when `git ls-files` lists any path under `FULL_INSTALL_ROOT_PATHS` (`.claude`, `.devcontainer`, and `RESTORABLE_ROOT_PATHS`). The message offers `--mode full` (today's takeover) and `--mode sidecar`. `--allow-self` with this repository as the target counts as full evidence. | Without this, the first plain install into a team repository is still a full takeover, which is the problem this plan exists to solve. `.devcontainer/` is the only full-install path that the restorable list misses, and the installer overwrites it even when tracked. `--allow-self` keeps this repository's own refresh working on a fresh clone, where `CLAUDE.md` and `AGENTS.md` are tracked by design. Explicit `--mode full` keeps today's behavior. |
| 19 | License notices | Ship `shared/third_party/ponytail/LICENSE` as `LICENSE` inside each vendored skill folder (`ponytail/`, `ponytail-review/`) at every write root. The rewritten `humanize` citation keeps a plain credit: `avoid-ai-writing v3.25.0` by Conor Bronsdon (MIT). | Both Ponytail skills are copies of MIT-licensed upstream work, and MIT requires the notice to travel with copies. The full install already ships it, and `validate_targets.py` requires that (`scripts/validate_targets.py:8914-8930`). `humanize` is informed by, not copied from, its source, so a credit line is enough. |
| 20 | Batch failures | `update_consumers.py` runs every target. When an installer exits non-zero, or a target is not a directory, the updater records it and continues. At the end it prints one line per failed target with its exit code and exits 1. It prints `All projects updated.` only when every target succeeded. A generator failure still stops the batch before any target runs. | User decision, 2026-09-24. One refused team repository should not block updates to the others, and the non-zero exit still tells scripts that something failed. Today `check=True` stops the batch at the first failure. |

Decisions 21-36 come from two reviews of the completed Phases A-E on
2026-09-25:
[round 1](../quality_reports/2026-09-25_consumer-sidecar-bootstrap-overlay-review.md)
and [round 2](../quality_reports/2026-09-25_consumer-sidecar-bootstrap-overlay-review-2.md).
Finding IDs (R1-R6, S1-S17, L1-L4) refer to those reports. User decisions
on 2026-09-25: add the fixes to this big plan after Phase E with a
plan-checker change, use four new phases, move an edited copy of a taken
skill into a backup folder inside the Git directory, and cover every
confirmed finding plus an uninstall command and the latent items L1-L4.
Where Decisions 21-36 conflict with the design text below them, the
decisions win; the design text has been updated to match. Round 1's design
item 5 (the v1 scope limits) is accepted with no change. An independent
review of this plan text on 2026-09-25 found no blocker; its corrections are
folded into Decisions 24-31 and 34 and into Phases F-H.

| # | Topic | Decision | Why |
| --- | --- | --- | --- |
| 21 | Reopening | Keep Phase E, its plan, log, findings, and receipts unchanged. Append Phases F-I; Phase I is the new final knowledge-refresh phase. Phase F changes `scripts/validate_plan_frontmatter.py` so a knowledge-refresh phase that is not last and whose small plan is `complete` or `cancelled` no longer counts toward "unique and last". A plan that has knowledge-refresh phases must still end with one. | Tested in a scratch clone (round 2, workflow finding): appending after E fails the validator; inserting before E stops the post-commit advance and fails the push and PR gates permanently; renaming E breaks the receipt chain. The final refresh and the stale-claims audit must follow the final code. |
| 22 | One precedence decision | Decide which skills are taken before choosing any unit action. A skill is taken when any read folder has an index entry for its name; any read-only folder has a disk entry for it (folder, symlink, or broken symlink); a write root holds team-owned or foreign content for it; a non-sidecar `SKILL.md` in a read folder declares it as its frontmatter `name:`; or, when `core.ignorecase` is true, a case variant of it exists in a read folder. A taken skill may only produce these outcomes: team-owned, team takeover, foreign (left untouched), no-op, drop the record, remove (content proven ours and unmodified), and preserve (Decision 24). The report names every path that took the skill, and never says "skipped at every root" while a sidecar copy of it remains in a client folder. | R1 and design item 1: the old loop rewrote only `unchanged`, `update`, and `install`, so `adopt` escaped. An allowlist of outcomes cannot miss a future kind. The frontmatter and case checks are conservative: a false match costs one sidecar skill, never a team file (L3, S12). |
| 23 | Ownership proof | A unit is ours when its manifest record matches, or when the sidecar's own exclude block lists it. Every unit the block lists is classified, even with no record and no desired content. A listed unit with no record whose content differs from the desired content is an unfinished sidecar copy: keep its files and its line, and report it. A recorded unit whose content equals the desired content is adopted even when its line is missing. A team takeover deletes untracked files whose bytes match the record or the desired content. A file-level line in the block keeps hiding its file while that file exists and is untracked. | S3: treating "no record" as "not ours" dropped lines and exposed sidecar files after a crash, a lost manifest, or a dropped skill. This also removes the "moved an invalid manifest aside" exception from the `git status` invariant. |
| 24 | Preserving edited copies | When a skill is taken and a sidecar copy of it is locally modified or unfinished, move that unit with `os.replace` to `<git dir>/ai-bootstrap-sidecar-preserved/<unit path with "/" replaced by "__">--<unit hash>`: one level deep, a folder for a skill and a file for a bridge. Drop its record and its final line, and print `PRESERVED <unit> -> <path>`. Never overwrite: when the destination exists, leave the unit in place and report a conflict. Refuse a preserved path that is a symlink or not a folder. Uninstall (Decision 34) uses the same move. | User decision, 2026-09-25 (design item 2, option A). Clients stop seeing the copy, and `git checkout` or `git clean` cannot reach the Git directory. Preflight already requires one filesystem. A crash after the move converges: the next run finds the unit absent and drops the record. |
| 25 | Index is the ownership source | A unit is tracked when the index has any entry at or under its path, including `skip-worktree`, intent-to-add, gitlink (`160000`), and symlink (`120000`) entries, whether or not the file is on disk. Read-folder names come from the index and the disk together. A tracked unit is team-owned before any symlink check, so a team symlink with a sidecar skill name skips that skill instead of aborting the run. An untracked symlink at a unit path is foreign: the skill is taken, and nothing is written through it. When `core.ignorecase` is true, compare index paths with unit paths and with the files inside a unit using `casefold()`, so a case-variant tracked folder makes the unit tracked, and a case-variant tracked file is never counted as untracked, deleted, removed, or preserved. Never restore or write over a deleted tracked file. | R4: disk-only ownership made sparse checkouts, local deletions, and team symlinks abort the whole run or miss a collision. |
| 26 | Git-directory metadata | Build the manifest, staging, and preserved paths from `git rev-parse --absolute-git-dir`, and the `info/exclude` path from `--path-format=absolute --git-common-dir` plus `info/exclude` (Git reads the exclude file from the common directory; in the main worktree both are the same), never from `--git-path`. Before any write, and in dry-run too, refuse when any of them, or `info/`, is a symlink, or has the wrong type: the manifest and the exclude file must be absent or regular files, and staging and preserved must be absent or real folders. Never open a named pipe. The exclude file must hold no sidecar markers, or exactly one BEGIN line followed later by one END line; anything else aborts before a write and names the lines. | R3, S6, S7: `--git-path` resolves links, so a staging link made a run delete a team folder; an orphan BEGIN line made a run erase the person's own ignore lines. |
| 27 | Mode detection hardening | `.claude/.git` counts as full evidence only when it is a directory and the outer index has no entry at or under `.claude`. Detection runs Git with `LC_ALL=C`. A Git failure other than "not a git repository" aborts detection in every mode, with Git's message and a remedy; a target folder that does not exist still gives no Git evidence, as today. Detection checks `info/exclude` with `lstat`, never opens a non-regular one (it is simply not sidecar evidence; sidecar preflight refuses it, Decision 26), and reads a regular one as bytes. At startup, `install_bootstrap.main()` removes Git's repository-local environment variables (the `git rev-parse --local-env-vars` list, hard-coded, plus `GIT_NAMESPACE`) from its own environment, for both modes. | S1, S2, S10, and an R5 sibling: a team `.claude` submodule was taken over by a plain install; a "dubious ownership" error fell through to a full install; an exported `GIT_DIR` redirected every write; a non-UTF-8 exclude byte crashed full installs. |
| 28 | Repository boundary and filesystem shape | Sidecar preflight aborts before any write when the nearest existing ancestor of any planned path (unit, write root, or bridge parent) reports a `--show-toplevel` other than the target, or the index holds a gitlink at or above a planned path (nested clone or submodule). It also aborts when an existing ancestor of a planned path is not a folder or is on another device, or when a folder the run must change is not writable. That means the parent of every unit that moves, every unit folder that moves, and every folder inside a unit that is removed, replaced, or emptied from staging. | S5, S11: a nested clone received visible sidecar files, and bad shapes crashed after the exclude write on every run. Decision 9 already requires unsafe states to abort before any write. |
| 29 | Bytes-safe paths | Decode Git `-z` output with `os.fsdecode`, encode Git input and hashed relative paths with `os.fsencode`, read and write `info/exclude` as bytes, and use `-z` for the explanatory `check-ignore -v` call. A file name that gitignore cannot express (a newline anywhere, or a trailing carriage return) never gets a line; it is reported instead, and such a retained file becomes visible. Printed paths escape undecodable bytes. | R5, S15: strict UTF-8 crashed on legal Git names, and a newline in a retained name wrote a raw pattern line such as `src`. `os.fsencode` is byte-identical to UTF-8 for valid names, so existing manifest hashes do not change. |
| 30 | Ignore gate on folders | Gate each skill unit as `<unit>/`, so directory-only rules apply before the folder exists. A gate failure names only the paths that are not ignored. | S4: team rules ending in `/` passed the gate and exposed files. Verified in scratch: `check-ignore --stdin -z` applies directory-only rules to an absent `unit/` path. |
| 31 | Complete, exact sources | One exact allowlist, shared by `validate_targets.py` and the installer, defines the sidecar source: every sidecar skill at every write root, both Ponytail licenses, every bridge, and nothing else. The installer refuses an incomplete source. Full mode refuses a source that lacks `.claude/hooks/scripts/state-sync.sh`, checked after `validate_install_roots` and `validate_agents_takeover` and before any write, so existing refusal messages keep their order. | S13, S14, L2: an empty source silently uninstalled every unit, and `dist/sidecar` given to a full install wrecked a full consumer. A complete source also makes a one-root install impossible. |
| 32 | Stable manifest namespace | Manifest validation accepts the current write roots and bridges plus `SIDECAR_RETIRED_SKILL_WRITE_ROOTS` and `SIDECAR_RETIRED_BRIDGES`, both empty today. A recorded unit outside the current desired set goes through the normal remove row. A unit path containing a backslash is rejected. | L1, L4: dropping a bridge constant would make every existing install abort, and the documented remedy would silently un-hide the old bridge. |
| 33 | No `bootstrap_commit` | Remove the field from the manifest model and writer. An old manifest that carries it still parses. `KNOWN_SCHEMA_VERSION` stays 1, and Decision 12's diagnostic field is withdrawn. | R6: no reliable source exists, and no decision reads it. Unknown keys are already ignored on read. |
| 34 | Uninstall | `install_bootstrap.py TARGET --mode sidecar --uninstall`, with `--dry-run` support, reconciles against an empty desired set and treats every sidecar skill and bridge as taken. It removes units whose content matches the record, preserves modified and unfinished units (Decision 24; a listed copy with no record is preserved even when it equals the current source), un-hides retained files and reports each one as now visible to `git add -A`, then deletes the exclude block, the manifest, and the staging folder. It keeps the preserved folder and prints its path. With `--uninstall`, detection skips the team-config refusal; with no sidecar evidence it prints "no sidecar found; nothing to do" and exits 0; full evidence or `--mode full` refuses. A preserve conflict keeps that unit, its line, the block, and a manifest that holds only the kept units, and exits 1: the one exception to Decision 9, because the uninstall did not finish. `update_consumers.py` never passes it. A rerun after a crash finishes the removal. | User decision, 2026-09-25, replacing the earlier non-goal. The manual removal steps could delete personal edits, retained files, and, after a pull, team files (design item 4). Reusing the planner keeps one ownership code path. |
| 35 | Hidden files and pulls | State plainly in user docs and in the relevant remedies that a pull or checkout overwrites a hidden (ignored) file without warning, so personal edits must not live in sidecar files. No code change. | S8, already accepted in Devil's Advocate point 11 but never stated to users. |
| 36 | Messages and docs | Every refusal and remedy names the evidence, what was written (normally nothing), and a safe next step that never asks the person to change tracked team content. README and docs replace the manual removal steps with `--uninstall`, keep a safe manual fallback, and correct the claims listed in S16 and S17. Generated OpenWiki pages are corrected only by Phase I's refresh. | S15-S17 and design item 4. |

Decisions 37-47 come from two independent reviews of the completed Phases
A-I at `010f08c` on 2026-09-26:
[hardening re-review](../quality_reports/2026-09-26_consumer-sidecar-bootstrap-overlay-review.md)
(findings R1-R5) and
[Opus re-review](../quality_reports/2026-09-26_consumer-sidecar-bootstrap-overlay-review-2.md)
(findings O1-O19; its mapping table links the two reports). Both kept the
architecture and failed the branch on safety grounds. User decisions on
2026-09-26: fix within this big plan as Phase J with a new final refresh
Phase K. Decision 37 replaces the Phase H deviation (Decision 28 checked
only the write roots and bridge parents) with a unit-level rule. An
independent review of this plan text found no blocker; its corrections are
folded into Decisions 37-47 and Phase J. Where Decisions 37-47 conflict
with earlier decisions or design text, the later decisions win; the design
text has been updated to match.

| # | Topic | Decision | Why |
| --- | --- | --- | --- |
| 37 | Unit-level repository boundary | Decision 28's `--show-toplevel`, gitlink, and shape checks stay on the write roots and bridge parents, and its device check also runs on every existing unit folder. At unit level, every required unit (desired, recorded, listed, the owner of a listed file line, and, during uninstall, every well-known unit) gets this rule instead. No path at or under any gitlink index entry is sent to `git check-ignore`, gets a file action, or keeps a file line (the outer exclude file does not apply inside a submodule, so such a line is dropped and reported). A unit that is itself a gitlink is team-owned: its skill is taken, and the report says the sidecar never touches files inside a submodule. A unit folder that holds a `.git` entry at any depth whose parent folder is not a gitlink aborts the run before any write, with the nested-repository message, when the unit is recorded or listed; when it is neither, the unit is foreign, its skill is taken, and nothing inside it is touched. Gathering stops hashing below a `.git` entry. | R1 and O1: uninstall deleted a team submodule's `LICENSE`, and a disk-only nested repository at a recorded unit was moved, `.git` included, into the preserved folder. A plan review showed that extending Decision 28's own checks to units would abort gitlink and symlink units that Decision 25 treats as team-owned or foreign, and that a submodule inside a team skill folder would abort every run. Refusing a personal clone the sidecar never owned would turn today's one-skill skip into a whole-run refusal. |
| 38 | Complete snapshots | A unit folder with no non-folder entry at any depth and no unreadable subfolder counts as absent (Phase G), and install replaces it. Otherwise a unit folder that holds a symlink, named pipe, socket, device, empty subfolder, or unreadable subfolder is incomplete: it never matches its record or the desired content, and it is locally modified when recorded, unfinished when listed, and foreign otherwise. A taken skill's incomplete unit is preserved intact with `os.replace`. A team takeover never deletes a non-regular entry; an untracked symlink inside a taken-over unit is treated like an untracked file that matches nothing (retained with its own exact-path line when ignored, and reported as now visible on uninstall). A symlink inside a unit no longer aborts the run; a symlinked ancestor of a unit still does (non-goal). | R4 and the O17 special-file bullet: a person's named pipe was deleted with a unit whose files matched the record. O9: a symlink inside a tracked team skill aborted every run, although Decision 25 puts the tracked check before any symlink check. |
| 39 | Uninstall on the install's write order | During uninstall every classified unit is taken, including dropped skills and retired roots or bridges. Uninstall writes the write-phase block, runs the gate over the lines the final block keeps (none when nothing is kept), applies actions through the same apply step as the install, and then either removes the block (writing unrecognized lines back as plain lines) when no unit is kept, or writes the final block when a preserve conflict keeps a unit. The planner reports the units it kept because of a conflict (`kept_conflicts`); exit 1 and the kept manifest depend only on that set. The conflict-only gates and the separate uninstall apply step are removed. A rerun with no block and no line to write writes nothing to the exclude file. | R2, O2, O3, O18. One write order and one apply step for install and uninstall. Uninstall gates exactly the lines that stay, so a team rule that exposes a path the run is removing can never block the uninstall, and the raw preserve-destination set can no longer block it either. |
| 40 | The gate covers every line the block keeps | The planner returns the gate paths next to the exclude lines. On install and update the gate checks every unit and file path the write-phase block lists, not only manifest records and actions, so an unfinished or locally modified unit or a retained file that a rule exposes fails the gate instead of being reported as hidden. During uninstall it checks only the paths whose lines the final block keeps (Decision 39). A unit is gated as `<unit>/` only when it is a real folder or absent (Decision 30); a unit that exists as a symlink or any other non-folder is gated as `<unit>`, because Git refuses a trailing slash on a symlink. The gate treats a Git exit other than 0 or 1 as an error, restores the exclude file, and aborts with Git's message. A gate failure names only the paths that are not ignored. | O11, and O10 (round 2's S15 bullet 1, still open). A plan review found that a symlink unit gated as `<unit>/` makes Git exit 128 with "beyond a symbolic link", which already blocks install today. |
| 41 | One path-identity rule for collision sources | Folder names, case variants, and frontmatter names come from one enumerator over the read folders. A read-only folder is listed through its symlink unless it resolves into a write root. A symlink entry in any read folder, including a write root, that resolves into a write root is an alias to a sidecar projection and never takes a skill. Every other entry is listed by its own name, so write roots are listed directly and a case variant or a differently named folder there is seen. | R3, O6, O7, O8: the frontmatter scan missed a collision behind a symlinked folder and invented one through a per-entry alias, and a case variant at a write root was never seen (S12 at write roots). |
| 42 | Git line splitting | Every exclude-block parser and writer splits on `\n` only, as Git does, and ignores one trailing `\r` when comparing. `str.splitlines()` is never used for `info/exclude`. | O5: a retained name with a form feed produced a raw `src` pattern that hid team files. |
| 43 | Retained files of dropped skills | The owning unit of every file line in the block is snapshotted, so a retained file of a dropped skill keeps hiding on install and is reported as now visible on uninstall. | O4. |
| 44 | Accurate reports | A taken skill whose edited copy stays because of a preserve conflict is reported as kept until the conflict is resolved, never as skipped at every root. Uninstall prints the preserved-copy folder's path whenever it holds anything, including on both "no sidecar found; nothing to do" paths (the CLI's and `uninstall_sidecar`'s). The `--mode full` sidecar refusal mentions `--uninstall`. The full install's tracked-path warning never aborts a run after its writes. | O12, O16, O17. |
| 45 | Settled refresh identity | An earlier knowledge-refresh phase counts as settled only when the big plan has a non-empty `name` and the phase's sibling file is a regular file (not a symlink) that declares `type: small-plan`, `name` equal to the phase slug, `parent_plan` equal to the big plan's `name`, and `status: complete` or `cancelled`. The Termination paragraph in `shared/policies/workflow.instructions.md` and the validator's module comment state the same rule. | R5. The validator ships to consumers and runs under the commit gate with the system `python3` (3.9). |
| 46 | Agent-harness wording | "A path the full install writes" means a path under `FULL_INSTALL_ROOT_PATHS`, the agent harness, not `.gitignore`. A plain full install into a repository that tracks only code and `.gitignore` stays allowed, and the docs say "an agent-harness path". | O15. Refusing on `.gitignore` would block a plain install into almost every repository. |
| 47 | Tests through real gathering | Each sidecar behavior finding (R1-R4, O1-O12, O16, and O17 bullets 2 and 4) gets a real-Git regression test through `install_sidecar`, `uninstall_sidecar`, or the installer CLI, not only a pure-planner test. R5 gets validator tests. O13 is closed by fixing the precedence property test's fixtures so they produce real `adopt` and `unchanged` outcomes. O17 bullet 1 gets an installer test with a patched Git call. O14, O15, O18, and O19 are closed by the doc changes, Phase J's removals, and Decisions 37 and 40, recorded as dispositions. Each finding's regression test fails on `010f08c`; tests that guard behavior that already works are named as guards. | O13, O19, and the MEMORY lesson that planner-injection tests cannot catch gathering defects. |

## Design Overview

### Consumer layout after a sidecar install

```text
<git dir>/ai-bootstrap-sidecar.json                          manifest (cannot be tracked)
<git dir>/ai-bootstrap-sidecar-staging/                      staging for atomic moves; emptied by every run
<git dir>/ai-bootstrap-sidecar-preserved/<unit__path>--<hash>  edited copies moved out of client folders (Decision 24); never emptied by the sidecar
<git dir>/info/exclude                                       marked block: one line per owned unit, one escaped line per retained file
.claude/skills/<skill>/                                      skill root read by Claude Code and Copilot VS Code
.agents/skills/<skill>/                                      skill root read by Codex, Antigravity, and Copilot VS Code
<root>/skills/ponytail/LICENSE, <root>/skills/ponytail-review/LICENSE    MIT notice at both write roots (Decision 19)
.claude/rules/ai-bootstrap-sidecar.md                        Claude bridge, if Phase A proves it
.agents/rules/ai-bootstrap-sidecar.md                        Antigravity bridge (trigger: always_on), if proven
.github/instructions/ai-bootstrap-sidecar.instructions.md    Copilot VS Code bridge (applyTo: "**"), if proven
```

Phase A confirms natively what the documentation says: which folders each
client reads, how Copilot treats the two identical sidecar copies, and the
Antigravity rule path and frontmatter. Nothing else is written: no hooks, no
`core.hooksPath` change, no nested repository, no MCP file, no devcontainer
change, and no `.gitignore` edit.

### Mode detection

```text
sidecar evidence = anything at the manifest path, including a dangling
                   symlink (valid or not)
                   OR a sidecar marker line in info/exclude (read as bytes)
full evidence    = .claude/.git as a directory, with no index entry at or
                   under .claude (Decision 27)
                   OR .claude/bootstrap-ownership.env
                   OR --allow-self with this repository as the target
team config      = git ls-files -z lists a path under FULL_INSTALL_ROOT_PATHS
                   (.claude, .devcontainer, and RESTORABLE_ROOT_PATHS)

any mode         a Git error other than "not a git repository" (Git run
                 with LC_ALL=C) -> abort; a missing target folder -> no
                 Git evidence, as today
                 a non-regular info/exclude is never opened and is not
                 sidecar evidence (sidecar preflight refuses it)
--uninstall      skips the team-config refusal; no sidecar evidence ->
                 "nothing to do", exit 0; full evidence -> abort

--mode sidecar   full evidence -> abort
                 linked worktree -> abort
                 otherwise -> sidecar reconcile
--mode full      sidecar evidence -> abort
                 otherwise -> current full install
no --mode        both kinds of evidence -> abort
                 sidecar evidence -> sidecar reconcile
                 full evidence -> current full install (refresh)
                 team config -> abort; offer --mode full or --mode sidecar
                 otherwise -> current full install (fresh default)
```

Detection runs first and reads only the target. The installer then picks
the source and runs `validate_install_roots`. Every refusal names the
evidence it found and the manual way forward. The sidecar path never calls a
full-install step (`validate_agents_takeover`, state migration, `.gitignore`
merge, `core.hooksPath`, state sync, or the Codex hook-trust notice).

### Reconciliation rules

A unit is one skill directory at one write root, or one bridge file. The
manifest records each unit's files with per-file SHA-256 hashes. A unit's
hash is SHA-256 over its sorted (relative path, bytes) pairs.

Preflight aborts, before any write, with a non-zero exit when:

- the target is not the top level of the main Git worktree;
- mode detection refuses (see above);
- Git is older than 2.31, which lacks `--path-format`;
- the Git directory and the worktree are on different filesystems (atomic
  moves need one filesystem);
- the manifest is unreadable, fails schema validation, has an unknown
  `schema_version`, or lists a path outside the sidecar namespace
  (`.claude/skills/<name>` or `.agents/skills/<name>` with one safe segment,
  a fixed bridge path, or a `retained` file inside one of those), an absolute
  path, or `..`;
- any existing ancestor of a planned path inside the worktree is a symlink,
  tracked or not (non-goal). A symlink at a unit path itself does not abort:
  a tracked one is team-owned, and an untracked one is foreign (Decision 25).
  A symlink inside a unit does not abort either (Decision 38);
- a recorded or listed unit folder holds a `.git` entry at any depth whose
  parent folder is not a gitlink in the outer index (Decision 37);
- the manifest, staging, preserved, or `info/exclude` path, or `info/`, is a
  symlink or has the wrong type, or the exclude file's sidecar markers are
  unbalanced or repeated (Decision 26);
- an existing write root or bridge parent belongs to another Git repository,
  or an existing ancestor of a planned path is not a folder, is on another
  device, or is not writable where a move happens (Decision 28);
- the source is incomplete or holds a file outside the sidecar allowlist
  (Decision 31);
- after the exclude block is written, the ignore gate fails (Decisions 17,
  30, and 40). The installer restores the previous exclude file and names
  each path that is not ignored with the rule that `git check-ignore -v -z`
  shows winning.

Before classifying units, the planner decides which skills are taken
(Decision 22). "Tracked" below means the index has an entry at or under the
unit path, whether or not it exists on disk (Decision 25). "Listed" means the
sidecar's own exclude block has the unit's line (Decision 23). Every listed
unit is classified, even with no record and no desired content. An existing
unit folder that holds no files and is not tracked counts as absent. A unit
folder that holds an entry the unit hash cannot represent never matches its
record or the desired content (Decision 38). A unit that is a gitlink in the
outer index gets no file action at all (Decision 37).

Each unit is then classified. The first matching row wins:

| Current state | Manifest record | Desired content | Action |
| --- | --- | --- | --- |
| Tracked | present, or none but listed | any | Team takeover (Decision 16). Never touch tracked files or restore deleted ones. Delete untracked files whose bytes match the record or the desired content, keep the other ignored untracked files as `retained`, leave visible untracked files alone, drop the unit record and its line, and report. |
| Tracked | none, not listed | any | Team-owned. Skip and report. Add no line and record nothing. |
| Untracked, hash equals the record | present | same hash | Unchanged. |
| Untracked, hash equals the record | present | different hash | Update. |
| Untracked, hash equals the record | present | none | Remove. |
| Untracked, hash equals the desired content, and either the unit is listed or a record exists | any | present | Adopt and record. This finishes an interrupted install or update, or rebuilds a lost manifest. |
| Untracked, hash differs from the record | present | any | Locally modified. Keep the files, the record, and the line, and report with remedy. When the skill is taken, preserve instead (Decision 24). |
| Untracked, listed | none | any | Unfinished sidecar copy. Keep the files and the line, record nothing, and report with remedy. When the skill is taken, preserve instead (Decision 24). |
| Untracked, not listed | none | any | Foreign. Skip. Report with remedy. |
| Absent | any | present | Install (this also reinstalls a deleted owned unit). |
| Absent | present | none | Drop the record. |

A `retained` file keeps its exact-path line and its report until it is
deleted (drop it) or tracked (drop it). With no manifest, a file-level line
in the block keeps hiding its file while that file exists and is untracked
(Decision 23). A name that gitignore cannot express is never retained; it is
reported (Decision 29).

Skill-level rule (Decision 22): for a taken skill, convert every unit
outcome to an allowed one. `install` becomes no-op; `unchanged`, `update`,
and `adopt` become remove; locally modified and unfinished copies are
preserved (Decision 24); team-owned, team takeover, foreign, no-op, drop,
and remove stay as they are. A test asserts that no taken skill produces
any other outcome.

Write order:

1. Preflight and classification. No writes.
2. Write the exclude block. It has a line for every unit that is owned after
   this run, being written, or being removed. A team-taken unit loses its
   unit line in this same write, and each of its untracked files that this
   run deletes or retains gets its own escaped exact-path line. Then run the
   ignore gate on every path that must stay ignored.
3. Empty the staging folder, then write and remove units. Build each new unit
   in staging, move the old copy into staging, and move the new copy into
   place with `os.replace`. Remove a unit by moving it into staging. Preserve
   a unit by moving it into the preserved folder (Decision 24). Delete a
   team-taken unit's untracked files that match the record or the desired
   content.
4. Drop the exclude lines of removed and preserved units and of deleted
   files.
5. Write the manifest (temporary file in the Git directory, then
   `os.replace`), and empty the staging folder.

Each write happens only when bytes change. Step 4 only drops lines whose
paths are gone, so it cannot un-hide a remaining file, and step 2's gate
therefore also covers the final block. Every crash point converges on rerun:
extra lines cover only sidecar paths; each unit is old, new, or absent; the
adopt row takes a new unit whose record was not written yet; the install row
restores an absent one; and the next run empties staging.

Remedies printed in the report (Decisions 35 and 36; Phases G and H may
tighten the wording but not the meaning):

- Locally modified: "`<path>` has local edits, so the sidecar keeps it. A
  pull can overwrite hidden files without warning. To take the current
  version, copy your edits elsewhere, delete `<path>`, and rerun". When the
  sidecar no longer ships the skill: "`<path>` has local edits and the
  sidecar no longer ships `<skill>`; copy your edits elsewhere, then delete
  `<path>`".
- Unfinished sidecar copy: "`<path>` is an unfinished sidecar copy that the
  sidecar cannot verify. It stays hidden. Copy anything you need from it,
  delete it, and rerun".
- Preserved: "`PRESERVED <unit> -> <preserved path>`: the repository now uses
  `<skill>`, so your edited copy was moved out of the client folders".
- Foreign: "the sidecar will not replace `<path>` and skips `<skill>` at every
  root; rename or remove `<path>` only if you do not need it".
- Team-owned skill: "the repository tracks `<tracked path>`; the sidecar skips
  `<skill>` at every root". Team-owned bridge: "the repository tracks
  `<path>`; the sidecar does not install this bridge".
- Retained: "`<path>` was left behind when the repository started tracking
  its folder. It stays hidden, and a pull can overwrite it. Move it out of the
  folder, or commit it with `git add -f`".
- Invalid manifest: "move `<manifest path>` aside and rerun with
  `--mode sidecar`. Units that the exclude block lists are recovered: matching
  units are adopted, and any other listed unit is kept hidden and reported.
  Keep the old manifest until the report looks right".

Dry-run runs preflight and classification. It runs the same ignore-gate
function on the candidate exclude text through a temporary
`core.excludesFile`, instead of writing `info/exclude`, and prints every
action as "would ...". It writes nothing, including the staging folder. The
dry-run gate is an approximation: Git ranks `info/exclude` above
`core.excludesFile`, so a person's own negation lines in `info/exclude` can
make dry-run report a refusal that a real run would not make (tested). The
real run's gate is authoritative.

### Required invariants

```text
git status --porcelain --untracked-files=all : identical before and after install and update, except
                                               after a person deleted the exclude block, when a rerun
                                               re-hides or removes the sidecar's own files. Uninstall
                                               un-hides retained files and reports each one. A retained
                                               name that gitignore cannot express becomes visible and
                                               is reported (Decision 29)
pre-existing team files                     : byte-identical after install, update, and uninstall
hooks                                       : no hook file copied, no core.hooksPath change, no provider hook config change
ownership                                   : never inferred from a filename or a location; it needs a matching record or the sidecar's own exclude line
precedence                                  : a taken skill never produces install, update, unchanged, or adopt
other repositories                          : no run deletes, moves, or writes anything inside a nested repository or submodule
unrepresented entries                       : an entry the unit hash cannot represent is never deleted; its unit is kept or
                                               preserved intact, except the empty folders of a unit that
                                               counts as absent (Decision 38)
second run from the same bootstrap commit   : no file changes, including the manifest and the exclude file
written paths                               : only the sidecar namespace, the exclude block, and the Git-directory manifest,
                                               staging folder, and preserved folder
```

## Pre-Flight Before Branching

Checked 2026-09-24 on `dev` at `1a06f1e`, after the second review:

- The unrelated uncommitted edit to `shared/policies/workspace.instructions.md`
  was discarded (user decision), and `dist/` was regenerated with
  `uv run python scripts/generate_targets.py --all`.
- `git status --porcelain` is empty, and the nested `.claude` repository has
  no changes.
- `uv run python scripts/check_runtime.py` passes.
- `uv run python scripts/validate_plan_frontmatter.py` passes every plan,
  including `hook-python-3.9-follow-up.md`.
- `uv run pytest` works on this host (pytest 9.0.3).
- The `openwiki` MCP server is installed and configured correctly: a manual
  start answered the MCP handshake in 4 seconds and listed its 6 tools. It
  failed in the review session only because it started within a minute of
  WSL booting, when every MCP server was slow, and it passed Claude Code's
  30-second startup limit. Phase E step 1 says how to reconnect it and how to
  raise the limit.

Right before creating the implementation branch, confirm again. `verify.py
phase` needs an active phase, so it first runs inside Phase A.

```bash
git status --porcelain
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format text
```

## Phases

- [x] `2026-09-24_phase-A-sidecar-provider-contract` — record documented and native discovery evidence per client, and freeze the read list, write list, and bridges; no code.
- [x] `2026-09-24_phase-B-sidecar-profile-and-ownership` — generate `dist/sidecar/` with license notices, validate self-containment, and build the pure reconciliation planner.
- [x] `2026-09-24_phase-C-sidecar-install-and-provider-bridges` — add `--mode`, mode detection, preflight, the ignore gate, and the atomic apply step for install and rerun.
- [x] `2026-09-24_phase-D-sidecar-update-and-reconciliation` — make batches skip and report failures, prove updates across bootstrap versions and mixed batches, then document both modes.
- [x] `2026-09-24_phase-E-sidecar-knowledge-refresh` — refresh OpenWiki and run the final stale-claims audit.
- [x] `2026-09-25_phase-F-reopen-completed-big-plan` — let the plan validator accept a completed earlier knowledge-refresh phase, and write the procedure for reopening a completed big plan (Decision 21).
- [x] `2026-09-25_phase-G-sidecar-ownership-and-precedence` — decide taken skills first, prove ownership by record or exclude line, read ownership from the index, preserve edited copies, and gate folders with a trailing slash (Decisions 22-25, 30, 32).
- [x] `2026-09-25_phase-H-sidecar-preflight-robustness-and-uninstall` — harden mode detection and preflight, make paths bytes-safe, require complete sources, add `--uninstall`, and correct messages and docs (Decisions 26-29, 31, 33-36).
- [x] `2026-09-25_phase-I-sidecar-hardening-knowledge-refresh` — refresh OpenWiki and run the final stale-claims audit again.
- [x] `2026-09-26_phase-J-sidecar-safety-follow-up` — unit-level repository boundaries, complete snapshots, uninstall on the install's write order, one path-identity rule, Git line splitting, accurate reports, the settled-refresh identity check, and corrected docs (Decisions 37-47).
- [x] `2026-09-26_phase-K-sidecar-follow-up-knowledge-refresh` — refresh OpenWiki and run the final stale-claims audit after Phase J.

Phase F must land before any other outer commit on this branch: once
Phases F-I are listed, the installed validator rejects two knowledge-refresh
phases, and the commit gate runs it on every outer commit. Commits in the
nested `.claude` repository are not gated.

## Decision Gate After Phase A

If Phase A evidence changes the read list, the write list, a bridge path, or
the duplicate-discovery assumption, revise Phases B-D through the workflow's
material-impact check before Phase B starts. If no client reaches
`native-run` evidence, cancel Phases B-E (Decision 14). A NO-GO for one
client is a valid result: that client is documented as unsupported for
sidecar v1, and the other clients proceed.

The documentation already settles three points, and this plan assumes them:

- Copilot in VS Code reads `.github/skills/`, `.claude/skills/`, and
  `.agents/skills/`, so it sees both sidecar copies. If Phase A shows that it
  lists the two identical copies twice or reports an error, revise the write
  list before Phase B.
- An Antigravity rule needs `trigger: always_on` frontmatter.
- VS Code runs two session types: the Local agent, which is marked for
  removal, and Agent Host sessions, which follow the selected harness's
  discovery rules. Copilot evidence must name its session type.

## Devil's Advocate Summary

1. One folder is not natively discovered by all four clients, so the sidecar
   writes into each client's own roots and keeps only the manifest elsewhere.
2. Symlinks look cleaner but add Windows/WSL/provider risk. Use copies.
3. Shared skill roots can collide with team skills, including roots the
   sidecar never writes. Check every folder a client reads, skip the whole
   skill, and report it; never shadow.
4. `CLAUDE.local.md` may already be personal state. Prefer a sidecar-named
   rules file, and never merge.
5. Codex is the weakest always-on case. It is skill-only by design.
6. Do not duplicate the installer. The sidecar gets its own small module and
   shares only low-level helpers and `runtime_ownership.py`.
7. Update is more dangerous than install. Removal requires an exact hash
   match with the manifest record.
8. `info/exclude` is convenience, not a security boundary, and a team
   `.gitignore` can override it. Prove every path is ignored before writing
   any unit, and escape exact-path lines.
9. Keep the profile an explicit constant so it cannot grow into the full
   bootstrap by accident.
10. The full installer is already a takeover. Refuse it explicitly on sidecar
    targets and on unbootstrapped team repositories, instead of relying on
    the incidental `.agents` refusal.
11. Git treats ignored files as disposable: checkout overwrites them without
    warning. Design every rule so that this is safe, and tell users not to
    keep personal edits in sidecar files.
12. Intent records add a state that can act on stale assumptions after a
    crash. Atomic moves plus the ordinary classification need no extra state.
13. Adoption by content alone would claim and hide files the sidecar never
    planned. Adopt only units that the sidecar's own exclude block lists.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

Each small plan lists its own focused tests. Run every phase's required
verification inside the devcontainer. Phase A's native client runs happen on
the host where the clients are installed.

Required review profiles: Phases B-E use `code`, `architecture`, `security`,
`tests`, and `ponytail`, plus `documentation` where documentation changes.
Phase A changes one evidence document and uses `documentation`,
`architecture`, and `security`. Phases F-H and J use `code`, `architecture`,
`security`, `tests`, `ponytail`, and `documentation`. Phases I and K use the
same full set, as Phase E did, because every multi-file diff is
control-plane/high-risk (`shared/policies/workspace.instructions.md`).

## Done Criteria

- A team repository may already track `.claude`, `.agents`, `.codex`,
  `.github`, `.devcontainer`, `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md`.
- `uv run python scripts/install_bootstrap.py TARGET --mode sidecar` installs
  without changing any pre-existing byte.
- `git status --porcelain --untracked-files=all` is unchanged by install and
  by update, apart from the two recovery runs named in the invariants.
- No `ai-bootstrap/` folder, hook, `core.hooksPath` change, nested
  repository, MCP file, devcontainer change, or `.gitignore` edit appears.
- `docs/sidecar-provider-contract.md` records every client's read folders,
  write folders, and bridge with an evidence tier. Support is claimed only at
  `native-run`.
- Mode detection follows the table above. In particular, a plain
  `install_bootstrap.py TARGET` never takes over a sidecar consumer or an
  unbootstrapped repository that tracks an agent-harness path (Decision 46).
- Full install and full updates are otherwise unchanged:
  `tests/test_install_bootstrap.py` passes, and its only expectation change
  is `--mode full` in
  `test_generated_session_pull_restores_ignored_adapter_after_branch_switch`.
- `update_consumers.py` updates a batch that mixes full and sidecar
  consumers. A refused or failed target is reported at the end, the other
  targets are updated, and the updater exits 1.
- Added, changed, and removed skills reconcile by the rules above. Team,
  foreign, retained, and locally modified paths are preserved and reported.
  An interrupted install or update finishes when rerun, without intent
  records.
- The vendored Ponytail skills ship with their MIT `LICENSE` at every write
  root.
- A repeated update is idempotent.
- README and docs describe full versus sidecar installation correctly,
  including the worktree limits.
- Every confirmed finding in the two 2026-09-25 review reports has a
  regression test that failed before its fix, or a documented disposition.
  Nothing is deferred: L1-L4 and the uninstall command are in scope.
- A taken skill never keeps, installs, adopts, or updates a sidecar copy at
  any root, in any recovery path, and an edited copy of a taken skill ends up
  in the preserved folder. The one exception is a preserve conflict (the
  destination already exists): the edited copy stays and is reported as kept
  until the conflict is resolved (Decisions 24 and 44).
- Every confirmed finding in the two 2026-09-26 review reports has a
  real-Git regression test that failed before its fix, or a documented
  disposition (Decision 47).
- No run deletes, moves, or writes anything inside a nested repository or
  submodule, and no run deletes an entry the unit hash cannot represent.
- `--uninstall` works after a profile change, never exits 1 except for a
  unit it actually kept because of a preserve conflict or a preflight
  refusal that names its cause, and never exposes a sidecar file. A team
  rule that exposes a sidecar path never blocks an uninstall.
- No run exposes a sidecar file or one of the person's own ignored files in
  `git status`, except the documented block-deletion recovery, uninstall's
  retained files, and a reported retained name that gitignore cannot express.
- A team `.claude` submodule, a Git error, a nested repository, a symlink in
  the Git directory, unbalanced markers, non-UTF-8 names, and an incomplete
  source each end in a clear refusal before any write, or in a correct run.
- `--uninstall` removes only unmodified sidecar files and sidecar metadata,
  preserves edited copies, and is idempotent.
- The final knowledge refresh and stale-claims audit are complete, and they
  ran after the last code change (Phase K).

## Completion Evidence

Phase E, `2026-09-24_phase-E-sidecar-knowledge-refresh`, was the final phase
until the plan was reopened on 2026-09-25 (Decision 21), and Phase I,
`2026-09-25_phase-I-sidecar-hardening-knowledge-refresh`, was the final phase
until it was reopened again on 2026-09-26; their closeout evidence stays as
it is. The final phase listed under `phases:` is now
`2026-09-26_phase-K-sidecar-follow-up-knowledge-refresh`. It runs the documentation,
memory, and LEARN audit. It sweeps every live-advice surface for claims this
plan invalidated, corrects or supersedes each one, leaves dated records
unchanged, and records the audited surfaces and each outcome under
`## Stale-claims surfaces checked` in its closeout session log. `verify.py`'s
closeout gate requires that heading, non-empty, for the last listed phase.
Because `openwiki/INSTRUCTIONS.md` exists, that phase is also the dedicated
knowledge-refresh phase defined in `shared/policies/workflow.instructions.md`.
