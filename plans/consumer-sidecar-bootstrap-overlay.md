---
name: consumer-sidecar-bootstrap-overlay
type: big-plan
status: planning
originating_branch: dev
implementation_branch: consumer-sidecar-bootstrap-overlay_implementation
started_at:
phases:
  - 2026-09-24_phase-A-sidecar-provider-contract
  - 2026-09-24_phase-B-sidecar-profile-and-ownership
  - 2026-09-24_phase-C-sidecar-install-and-provider-bridges
  - 2026-09-24_phase-D-sidecar-update-and-reconciliation
  - 2026-09-24_phase-E-sidecar-knowledge-refresh
current_phase:
---

# Big Plan: Consumer Sidecar Bootstrap Overlay

## Context

The bootstrap assumes it owns the consumer repository's agent harness. That
is right for personal and new repositories. It is wrong for an existing team
repository that already tracks one or more of:

```text
.claude/  .agents/  .codex/  .github/  CLAUDE.md  AGENTS.md  GEMINI.md
```

The full installer is a takeover, and its protection is narrower than it
looks. Its only hard pre-write refusal is `validate_agents_takeover` for an
existing `.agents/` tree. It migrates any `.claude/` without `.git` as legacy
state, rewrites tracked `.gitignore`, overwrites root adapters, and only
warns about already-tracked generated paths, after copying. A full install
into a team repository therefore changes team files.

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
  carries sidecar evidence, or that tracks agent configuration and has no
  bootstrap evidence.
- Project an allowlisted skill set into `.claude/skills/<skill>/` and
  `.agents/skills/<skill>/`, plus one bridge file per client where Phase A
  proves an additive native mechanism.
- Keep every sidecar file out of the team's Git state through the local
  `info/exclude` file, proven with `git check-ignore` before any write.
- Record ownership in a manifest inside the Git directory, where it cannot be
  tracked.
- Use one reconciliation code path for first install, rerun, and update.
- Let `update_consumers.py` auto-detect sidecar consumers, including in batches
  that mix full and sidecar consumers.
- Never overwrite, delete, or shadow team-owned content. Preserve and report
  local edits to sidecar-owned files.

## Non-Goals

- Replacing or weakening the full installer.
- Automatic full -> sidecar or sidecar -> full migration.
- Global per-user installation (`~/.claude`, `~/.codex`, `~/.agents`, ...).
- Editing tracked `.gitignore` or tracked team instruction files.
- Symlinks, custom agents, hooks, the plan/review/commit lifecycle, MCP
  servers, plans, MEMORY, or session logs in the consumer.
- A worktree folder holding a canonical copy of the sidecar content (the
  earlier `ai-bootstrap/` root; see Decisions).
- Linked worktrees in v1 (see Decision 15).
- Copilot CLI or Copilot cloud agents. Copilot support means VS Code, which
  matches the README's existing Copilot claim.
- Skill-name prefixes in v1.
- Sidecar support when a projection parent directory is a symlink.
- Merging into an existing `CLAUDE.local.md`.
- A sidecar uninstall command. Phase D documents manual removal.
- An always-on Codex instruction unless Phase A proves an additive mechanism.
- Manifest schema migration code before a second schema version exists.

## Decisions

These decisions come from the 2026-09-24 reviews of the first draft and of
the first revision.

| # | Topic | Decision | Why |
| --- | --- | --- | --- |
| 1 | Canonical folder | Drop `ai-bootstrap/`. The manifest lives at `git rev-parse --path-format=absolute --git-path ai-bootstrap-sidecar.json`. | No client reads that folder. It stored every skill a third time and added a reconciliation class. A manifest inside the worktree can be committed or forged by a pulled commit; a Git-directory file cannot be tracked. |
| 2 | Content source | New generator target `dist/sidecar/`: add `"sidecar"` to `TARGETS` and a `render_sidecar()` branch in `generate()`, which today raises `ValueError` for any target except `multi-agent`. The tree mirrors consumer-relative paths. | Rendering and validation stay in the generator; the installer only copies. `--all` and `update_consumers.py` then regenerate it. |
| 3 | Profile | Constants in `scripts/runtime_ownership.py`: `SIDECAR_SKILLS = ("debug-investigator", "humanize", "ponytail", "ponytail-review")`. | That module is already the single ownership contract for generator, installer, and validator. No JSON loader is needed. `code-style`, `testing-patterns`, `run-tests`, and `refactor` are excluded because they depend on `.claude/instructions/*` and `.claude/scripts/verify.py`. |
| 4 | Self-containment | A `"sidecar"` entry in `TARGET_PATH_REPLACEMENTS` rewrites the remaining bootstrap references at render time. `validate_targets.py` rejects any sidecar file that still names a path the sidecar does not install, or still contains one of the replaced phrases. | Known references: `humanize` cites `../../third_party/avoid-ai-writing/`; `ponytail` says "the workflow's final Ponytail diff review remains mandatory"; `ponytail-review` says "Return findings to the coder". `str.replace` does not fail on a miss, so the phrase check catches a replacement that stops matching. Source skills and vendored Ponytail stay unchanged. |
| 5 | Bridge content | One body in `shared/sidecar/bridge.md`: the precedence rule, plus "apply `ponytail` in `full` mode to coding tasks unless repository guidance says otherwise, and use `ponytail-review` on non-trivial diffs". Nothing else. | Without hooks, the bridge is what keeps Ponytail active. That is its whole value. |
| 6 | Claude bridge | Candidate `.claude/rules/ai-bootstrap-sidecar.md`. Fallback `CLAUDE.local.md` only if Phase A disproves the rules file and `CLAUDE.local.md` is absent. | A sidecar-named file, like the other bridges. `CLAUDE.local.md` is one personal file that users often already own. |
| 7 | Codex bridge | Expected skill-only. Rejected by design: `AGENTS.override.md` (it replaces `AGENTS.md` in its directory), `project_doc_fallback_filenames` (used only without an `AGENTS.md`, and it needs a config file), and any `~/.codex` change. | These mechanisms either suppress team guidance or need files the sidecar must not write. |
| 8 | Collisions | A skill whose name is taken by non-sidecar content at any projection root is skipped at every root and reported. A taken bridge path skips that bridge and is reported. | Installing at one root while the team owns the other would shadow the team skill in clients that read both roots. |
| 9 | Failure classes | Unsafe states abort before any write with a non-zero exit. Per-path conflicts skip that path, exit 0, and print a summary with a remedy. | A single colliding path should not block the whole overlay, and a batch update should continue. |
| 10 | Crash recovery | Before any unit write, write an intent manifest that marks every unit this run will write or remove as `pending`. A rerun finishes pending units. Manifest writes are atomic: a temporary file in the Git directory, then `os.replace`. | Without intent records, an interrupted first install looks foreign forever. Pending units are only ever planned for paths that were absent, sidecar-owned and unchanged, or byte-identical to the desired content, so finishing them cannot overwrite user or team bytes. |
| 11 | Mode detection | One function in `install_bootstrap.py`, landing in Phase C. | `update_consumers.py` calls the installer without `--mode`, so detection must live in the installer and must exist before any sidecar can be installed. |
| 12 | Manifest fields | `schema_version`, per-unit records with per-file SHA-256 hashes, and a diagnostic `bootstrap_commit` that no decision reads. No timestamps. Rewrite the manifest and the exclude block only when their bytes change. | Timestamps would break "a second update changes nothing". Per-file hashes are needed to clean up after a team takeover (Decision 16). |
| 13 | Full-only options | On a sidecar target, `--commit-copilot-surface`, `--no-commit-copilot-surface`, `--state-remote`, `AI_STATE_REMOTE`, and `--allow-self` are ignored with one warning. `--local-only` is accepted as a no-op. `--dry-run` works. | `update_consumers.py` forwards these options to every target in a batch. |
| 14 | Claims follow evidence | A projection root or bridge path ships only when at least one client has `native-run` evidence for it in Phase A. A client without that evidence is documented as unverified, not supported. | No later phase may depend on "probably discovered" behavior. |
| 15 | Worktrees | Sidecar mode aborts in a linked worktree (absolute `--git-dir` differs from absolute `--git-common-dir`). | Verified with Git 2.50: `info/exclude` is shared by all worktrees, while `--git-path ai-bootstrap-sidecar.json` is per worktree. Trimming the shared block from one worktree would expose another worktree's files. |
| 16 | Team takeover | When the team starts tracking a sidecar path: delete untracked files in that unit whose bytes match the record; keep every other untracked file with one exact-path exclude line, record it as `retained`, and report it on every run until it is deleted or tracked. | Verified: `git checkout` silently overwrites an ignored file with the team's tracked version and leaves our other files behind. Dropping the directory line would then show them in `git status`, and `git add -A` would commit them. Keeping the directory line instead would hide the team's own new files in that folder. |
| 17 | Ignore gate | Pipe every planned file path to `git check-ignore --stdin` without `-v`. The gate passes only when the printed set equals the planned set. Use `-v` only to explain a failure. | Verified: with a team `!.claude/skills/**` rule, `git check-ignore -v` exits 0 although the file is not ignored, and `--stdin` exits 0 when any one path is ignored. |
| 18 | Unbootstrapped team repository | With no `--mode` and no bootstrap evidence, abort when `git ls-files` lists any path under `.claude/` or under `RESTORABLE_ROOT_PATHS`. The message offers `--mode full` (today's takeover) and `--mode sidecar`. | Without this, the first run against a team repository that has never seen the bootstrap is still a full takeover, which is the problem this plan exists to solve. Explicit `--mode full` keeps today's behavior. |

## Design Overview

### Consumer layout after a sidecar install

```text
<git dir>/ai-bootstrap-sidecar.json                          manifest (cannot be tracked)
<git dir>/info/exclude                                       marked block, one anchored line per owned unit
.claude/skills/<skill>/                                      skill root read by Claude Code
.agents/skills/<skill>/                                      skill root read by Codex and Antigravity
.claude/rules/ai-bootstrap-sidecar.md                        Claude bridge, if Phase A proves it
.agents/rules/ai-bootstrap-sidecar.md                        Antigravity bridge, if Phase A proves it
.github/instructions/ai-bootstrap-sidecar.instructions.md    Copilot VS Code bridge, if proven
```

Phase A confirms which of these roots Copilot VS Code reads and the exact
Antigravity rule path. Nothing else is written: no hooks, no `core.hooksPath`
change, no nested repository, no MCP file, no devcontainer change, and no
`.gitignore` edit.

### Mode detection

```text
sidecar evidence = a manifest file at the Git-dir path (valid or not)
                   OR the sidecar marker block in info/exclude
full evidence    = .claude/.git OR .claude/bootstrap-ownership.env
team config      = git ls-files lists a path under .claude/ or RESTORABLE_ROOT_PATHS

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

Every refusal names the evidence it found and the manual way forward. The
sidecar path never calls a full-install step (`validate_agents_takeover`,
state migration, `.gitignore` merge, `core.hooksPath`, state sync).

### Reconciliation rules

A unit is one skill directory at one projection root, or one bridge file.
The manifest records each unit's files with per-file SHA-256 hashes. A
unit's hash is SHA-256 over its sorted (relative path, bytes) pairs.

Preflight aborts, before any write, with a non-zero exit when:

- the target is not the top level of the main Git worktree;
- mode detection refuses (see above);
- the manifest is unreadable, fails schema validation, has an unknown
  `schema_version`, or lists a path outside the sidecar namespace
  (`.claude/skills/<name>` or `.agents/skills/<name>` with one safe segment,
  a fixed bridge path, or a `retained` file inside one of those), an absolute
  path, or `..`;
- a planned path, or any existing ancestor of it inside the worktree, is a
  symlink;
- after the exclude block is written, the ignore gate fails (Decision 17).
  The installer restores the previous exclude file and names each path with
  the rule that `git check-ignore -v` shows winning.

Each unit is then classified. The first matching row wins:

| Current state | Manifest record | Desired content | Action |
| --- | --- | --- | --- |
| Any file in the unit is tracked by the outer repository | any | any | Team-owned. Never touch tracked files. Delete untracked files whose bytes match the record, keep the rest as `retained` (Decision 16), drop the unit record and its line, and report. |
| Untracked or absent | `pending` | any | Interrupted sidecar write. Write the desired content, or remove the unit when nothing is desired. |
| Untracked, hash equals the record | present | same hash | Unchanged. |
| Untracked, hash equals the record | present | different hash | Update. |
| Untracked, hash equals the record | present | none | Remove. |
| Untracked, hash equals the desired content | any | present | Adopt and record. |
| Untracked, hash differs from the record | present | any | Locally modified. Keep the files and the old record. Report with remedy. |
| Untracked | none | any | Foreign. Skip. Report with remedy. |
| Absent | any | present | Install (this also reinstalls a deleted owned unit). |
| Absent | present | none | Drop the record. |

A `retained` file keeps its exact-path line and its report until it is
deleted (drop it) or tracked (drop it).

Skill-level rule: when any projection of a skill is team-owned or foreign,
skip the skill at every root. Remove an unchanged sidecar copy at the other
root.

Write order:

1. Preflight and classification. No writes.
2. Write the exclude block with lines for every owned and planned unit, then
   run the ignore gate.
3. Write the intent manifest: current records plus a `pending` record for
   every unit this run will write or remove.
4. Write and remove units.
5. Trim the exclude block to the final owned and `retained` set.
6. Write the final manifest without `pending` records.

Each write happens only when bytes change. Every crash point between steps
converges on rerun: extra exclude lines are harmless, and pending units are
finished.

Remedies printed in the report:

- Locally modified: "delete or restore `<path>`, then rerun to take the
  current version".
- Foreign: "the sidecar will not replace `<path>`; rename or remove it only
  if it is not needed".
- Retained: "`<path>` was left behind when the repository started tracking
  its folder; delete it or commit it".
- Invalid manifest: "move `<manifest path>` aside and rerun with
  `--mode sidecar`. Files that match current content are adopted. Any other
  sidecar file is reported as foreign and stops being ignored".

Dry-run runs preflight and classification. It runs the same ignore-gate
function on the candidate exclude text through a temporary
`core.excludesFile`, instead of writing `info/exclude`. It prints every
action as "would ..." and writes nothing.

### Required invariants

```text
git status --porcelain --untracked-files=all : identical before and after install and update
pre-existing team files                     : byte-identical after install and update
hooks                                       : no hook file copied, no core.hooksPath change, no provider hook config change
ownership                                   : never inferred from a filename or from living under .claude/ or .agents/
second run from the same bootstrap commit   : no file changes, including the manifest and the exclude file
```

## Pre-Flight Before Branching

These already fail on `dev` (checked 2026-09-24) and are not caused by this
plan. Resolve them before creating the implementation branch:

1. `.claude/plans/hook-python-3.9-follow-up.md` fails plan validation
   (`missing required field: closeout_session_log`). The commit gate
   validates every plan, so this blocks every commit. The user decides how
   to resolve it.
2. `scripts/check_runtime.py` reports 176 stale files in this repository's
   own installed overlay. Refresh it with
   `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
   as its own change, or record why it stays stale.
3. Confirm `uv run python .claude/scripts/verify.py phase --format text`
   passes on `dev` inside the devcontainer. `pytest` is not installed on the
   host, so `uv run pytest` fails there.

## Phases

- [ ] `2026-09-24_phase-A-sidecar-provider-contract` — record native discovery evidence per client and freeze the provider matrix; no code.
- [ ] `2026-09-24_phase-B-sidecar-profile-and-ownership` — generate `dist/sidecar/`, validate self-containment, and build the pure reconciliation planner.
- [ ] `2026-09-24_phase-C-sidecar-install-and-provider-bridges` — add `--mode`, mode detection, preflight, the ignore gate, and the apply step for install and rerun.
- [ ] `2026-09-24_phase-D-sidecar-update-and-reconciliation` — prove updates across bootstrap versions and mixed batches, then document both modes.
- [ ] `2026-09-24_phase-E-sidecar-knowledge-refresh` — refresh OpenWiki and run the final stale-claims audit.

## Decision Gate After Phase A

If Phase A evidence changes the projection roots, a bridge path, or the
duplicate-discovery assumption, revise Phases B-D through the workflow's
material-impact check before Phase B starts. One example: Copilot VS Code
reads neither `.claude/skills/` nor `.agents/skills/` and needs a
`.github/skills/` root. A NO-GO for one client is a valid result. That client
is documented as unsupported for sidecar v1, and the other clients proceed.

## Devil's Advocate Summary

1. One folder is not natively discovered by all four clients, so the sidecar
   writes into each client's own roots and keeps only the manifest elsewhere.
2. Symlinks look cleaner but add Windows/WSL/provider risk. Use copies.
3. Shared skill roots can collide with team skills. Skip the whole skill and
   report it; never shadow.
4. `CLAUDE.local.md` may already be personal state. Prefer a sidecar-named
   rules file, and never merge.
5. Codex is the weakest always-on case. Expect skill-only.
6. Do not duplicate the installer. The sidecar gets its own small module and
   shares only low-level helpers and `runtime_ownership.py`.
7. Update is more dangerous than install. Removal requires an exact hash
   match with the manifest record.
8. `info/exclude` is convenience, not a security boundary, and a team
   `.gitignore` can override it. Prove every path is ignored before writing.
9. Keep the profile an explicit constant so it cannot grow into the full
   bootstrap by accident.
10. The full installer is already a takeover. Refuse it explicitly on sidecar
    targets and on unbootstrapped team repositories, instead of relying on
    the incidental `.agents` refusal.
11. Git treats ignored files as disposable: checkout overwrites them without
    warning. Design every rule so that this is safe.

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
  `.github`, `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md`.
- `uv run python scripts/install_bootstrap.py TARGET --mode sidecar` installs
  without changing any pre-existing byte.
- `git status --porcelain --untracked-files=all` is unchanged by install and
  by update.
- No `ai-bootstrap/` folder, hook, `core.hooksPath` change, nested
  repository, MCP file, devcontainer change, or `.gitignore` edit appears.
- `docs/sidecar-provider-contract.md` records every client's skill roots and
  bridge with an evidence tier. Support is claimed only at `native-run`.
- Mode detection follows the table above. In particular, a plain
  `install_bootstrap.py TARGET` never takes over a sidecar consumer or an
  unbootstrapped repository that tracks agent configuration.
- Full install and full updates are otherwise unchanged: the existing
  `tests/test_install_bootstrap.py` passes without edits to its expectations.
- `update_consumers.py` updates a batch that mixes full and sidecar consumers.
- Added, changed, and removed skills reconcile by the rules above. Team,
  foreign, retained, and locally modified paths are preserved and reported.
  An interrupted install or update finishes when rerun.
- A repeated update is idempotent.
- README and docs describe full versus sidecar installation correctly.
- The final knowledge refresh and stale-claims audit are complete.
