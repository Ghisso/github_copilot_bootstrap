---
name: consumer-sidecar-bootstrap-overlay
type: big-plan
status: in-progress
originating_branch: dev
implementation_branch: consumer-sidecar-bootstrap-overlay_implementation
started_at: 2026-09-25T03:07:56Z
phases:
  - 2026-09-24_phase-A-sidecar-provider-contract
  - 2026-09-24_phase-B-sidecar-profile-and-ownership
  - 2026-09-24_phase-C-sidecar-install-and-provider-bridges
  - 2026-09-24_phase-D-sidecar-update-and-reconciliation
  - 2026-09-24_phase-E-sidecar-knowledge-refresh
current_phase: 2026-09-24_phase-D-sidecar-update-and-reconciliation
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
  `--mode full`. Without `--mode`, the installer now refuses a target that
  carries sidecar evidence, or that tracks a path the full install writes and
  has no bootstrap evidence (Decision 18).
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
- A sidecar uninstall command. Phase D documents manual removal.
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

## Design Overview

### Consumer layout after a sidecar install

```text
<git dir>/ai-bootstrap-sidecar.json                          manifest (cannot be tracked)
<git dir>/ai-bootstrap-sidecar-staging/                      staging for atomic moves; emptied by every run
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
sidecar evidence = a manifest file at the Git-dir path (valid or not)
                   OR the sidecar marker block in info/exclude
full evidence    = .claude/.git OR .claude/bootstrap-ownership.env
                   OR --allow-self with this repository as the target
team config      = git ls-files lists a path under FULL_INSTALL_ROOT_PATHS
                   (.claude, .devcontainer, and RESTORABLE_ROOT_PATHS)

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
- a planned path, or any existing ancestor of it inside the worktree, is a
  symlink, or `info/exclude` is a symlink;
- after the exclude block is written, the ignore gate fails (Decision 17).
  The installer restores the previous exclude file and names each path with
  the rule that `git check-ignore -v` shows winning.

Each unit is then classified. The first matching row wins:

| Current state | Manifest record | Desired content | Action |
| --- | --- | --- | --- |
| Any file in the unit is tracked by the outer repository | present | any | Team takeover (Decision 16). Never touch tracked files. Delete untracked files whose bytes match the record, keep the other ignored untracked files as `retained`, leave visible untracked files alone, drop the unit record and its line, and report. |
| Any file in the unit is tracked by the outer repository | none | any | Team-owned. Skip and report. Add no line and record nothing. |
| Untracked, hash equals the record | present | same hash | Unchanged. |
| Untracked, hash equals the record | present | different hash | Update. |
| Untracked, hash equals the record | present | none | Remove. |
| Untracked, hash equals the desired content, and the sidecar's exclude block already lists the unit | any | present | Adopt and record. This finishes an interrupted install or update, or rebuilds a lost manifest. |
| Untracked, hash differs from the record | present | any | Locally modified. Keep the files, the record, and the line. Report with remedy. |
| Untracked | none | any | Foreign. Skip. Report with remedy. |
| Absent | any | present | Install (this also reinstalls a deleted owned unit). |
| Absent | present | none | Drop the record. |

A `retained` file keeps its exact-path line and its report until it is
deleted (drop it) or tracked (drop it).

Skill-level rule: when any folder on the read list (Decision 8) holds a copy
of a skill name that the sidecar does not own, skip that skill at every write
root. Remove an unchanged sidecar copy at the other write roots, and keep and
report a modified one.

Write order:

1. Preflight and classification. No writes.
2. Write the exclude block. It has a line for every unit that is owned after
   this run, being written, or being removed. A team-taken unit loses its
   unit line in this same write, and each of its untracked files that this
   run deletes or retains gets its own escaped exact-path line. Then run the
   ignore gate on every path that must stay ignored.
3. Empty the staging folder, then write and remove units. Build each new unit
   in staging, move the old copy into staging, and move the new copy into
   place with `os.replace`. Remove a unit by moving it into staging. Delete a
   team-taken unit's untracked files that match the record.
4. Drop the exclude lines of removed units and deleted files.
5. Write the manifest (temporary file in the Git directory, then
   `os.replace`), and empty the staging folder.

Each write happens only when bytes change. Step 4 only drops lines whose
paths are gone, so it cannot un-hide a remaining file, and step 2's gate
therefore also covers the final block. Every crash point converges on rerun:
extra lines cover only sidecar paths; each unit is old, new, or absent; the
adopt row takes a new unit whose record was not written yet; the install row
restores an absent one; and the next run empties staging.

Remedies printed in the report:

- Locally modified: "delete or restore `<path>`, then rerun to take the
  current version".
- Foreign: "the sidecar will not replace `<path>`; rename or remove it only
  if it is not needed".
- Team-owned: "the repository tracks `<path>`; the sidecar skips `<skill>` at
  every root".
- Retained: "`<path>` was left behind when the repository started tracking
  its folder; delete it or commit it".
- Invalid manifest: "move `<manifest path>` aside and rerun with
  `--mode sidecar`. Units that the exclude block lists and that match current
  content are adopted. Any other sidecar file is reported as foreign and
  stops being ignored".

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
                                               two recovery runs: after a person deleted the exclude
                                               block, a rerun re-hides or removes the sidecar's own
                                               files; after a person moved an invalid manifest aside,
                                               a rerun un-hides the files that no longer match
pre-existing team files                     : byte-identical after install and update
hooks                                       : no hook file copied, no core.hooksPath change, no provider hook config change
ownership                                   : never inferred from a filename or a location; adoption needs the sidecar's own exclude line
second run from the same bootstrap commit   : no file changes, including the manifest and the exclude file
written paths                               : only the sidecar namespace, the exclude block, and the Git-directory manifest and staging folder
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
- [ ] `2026-09-24_phase-E-sidecar-knowledge-refresh` — refresh OpenWiki and run the final stale-claims audit.

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
`architecture`, and `security`.

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
  unbootstrapped repository that tracks a path the full install writes.
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
- The final knowledge refresh and stale-claims audit are complete.

## Completion Evidence

The final phase listed under `phases:`,
`2026-09-24_phase-E-sidecar-knowledge-refresh`, runs the documentation,
memory, and LEARN audit. It sweeps every live-advice surface for claims this
plan invalidated, corrects or supersedes each one, leaves dated records
unchanged, and records the audited surfaces and each outcome under
`## Stale-claims surfaces checked` in its closeout session log. `verify.py`'s
closeout gate requires that heading, non-empty, for the last listed phase.
Because `openwiki/INSTRUCTIONS.md` exists, that phase is also the dedicated
knowledge-refresh phase defined in `shared/policies/workflow.instructions.md`.
