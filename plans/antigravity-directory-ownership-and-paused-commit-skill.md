---
name: antigravity-directory-ownership-and-paused-commit-skill
type: big-plan
status: planning
originating_branch: dev
implementation_branch: antigravity-directory-ownership-and-paused-commit-skill_implementation
started_at:
phases:
  - 2026-08-24_phase-A-antigravity-directory-ownership-and-paused-commit-skill
current_phase:
---

# Big Plan: Antigravity directory ownership and paused commit skill

## Context

Two bootstrap contracts drifted after the paused-phase checkpoint work.

First, the generated commit skill still describes normal completion as the only
valid commit path. It therefore contradicts the enforced lifecycle, which also
permits an explicitly evidenced paused checkpoint without final score,
findings, LEARN, DOCUMENT, or a COMPLETED closeout. A bounded audit found three
more stale canonical skills: `plan-decomposition` omits pause/cancellation
evidence and treats the normal closeout checklist as a gate for every commit;
`context-status` reports obsolete DRAFT/APPROVED/COMPLETED labels instead of the
live big/small-plan statuses; and `setup-project` bypasses the installer and
stages generated local AI surfaces that the current nested-state and ignore
model intentionally keeps out of the outer repository.

Second, Google Antigravity is the only generated provider surface managed as a
file-granular shared namespace. That produces a long `.gitignore` block and a
separate Antigravity allowlist, manifest records, pruning path, and restoration
branch. The approved end state treats `.agents/` like `.codex/`: the bootstrap
owns the whole ignored directory, mirrors it under `.claude/bootstrap-root/`,
and restores it as one allowlisted root adapter.

These changes belong in one phase. Skill guidance, installer ownership,
restoration, generated output, validation, migration safety, and documentation
must agree in the same completion commit.

## Goals

- Correct all four evidence-backed stale shared skills and their generated and
  installed copies.
- Add structural validator regressions that reject the obsolete lifecycle and
  installer phrases instead of relying on a one-time prose edit.
- Add `.agents` to directory-level root adapter ownership and render one
  `.agents/` ignore entry.
- Mirror and restore `.agents/` through `.claude/bootstrap-root/.agents/` using
  the same root-adapter contract as `.codex/`.
- Remove ongoing Antigravity per-file ownership records, the generated
  allowlist, and special per-file ignore/prune/restore logic.
- Before any takeover write, fail closed when existing `.agents` content cannot
  be proved to be generated. Report sorted repository-relative conflict paths
  and clear move/backup/remove-and-rerun instructions; never silently delete or
  overwrite consumer content.
- Preserve existing Copilot commit-mode retention, nested AI-state behavior,
  tracked authoring protection, restoration path safety, paused/completed/
  cancelled gates, and generated-target determinism.

## Design Overview

```text
shared/skills/{commit,plan-decomposition,context-status,setup-project}
    -> generate_targets.py
    -> .claude/skills and .agents/skills
    -> validate_targets.py structural lifecycle/installer contracts

dist/multi-agent/.agents/
    -> installer pre-write takeover check
    -> consumer .agents/                       (one ignored owned directory)
    -> .claude/bootstrap-root/.agents/         (nested-state mirror)
    -> restore-root-adapters.sh                (one root-adapter record)
```

The minimum design is an extension of the existing root-adapter tuple and copy
path, plus one narrow migration guard. It is not a new ownership framework.
Legacy file records may be read only long enough to prove that old generated
files are safe to replace and to retain the consumer's Copilot install mode.
They must not remain an output, runtime restoration contract, or ongoing
per-file pruning mechanism after migration.

## Decisions

1. `.agents/` becomes fully bootstrap-managed and local-only, matching
   `.codex/`. Consumers that want custom Antigravity files must move them out of
   `.agents/` or intentionally incorporate them into this bootstrap's shared
   source before retrying an update.
2. The installer checks the full existing `.agents` tree before its first
   mutation. Known generated content can be established from the current
   generated source, the prior mirrored `.claude/bootstrap-root/.agents/` tree,
   or strictly validated legacy Antigravity ownership evidence. Unknown files,
   modified collisions, unsafe links, and unproved paths stop the install.
3. After takeover, the prior bootstrap-root mirror is the narrow evidence that
   distinguishes obsolete generated files from newly added consumer content on
   later refreshes. Refresh must still fail before deleting an unexpected file.
4. Existing tracked root-adapter protection stays intact. The migration guard
   does not run `git rm`, move user files, or infer permission from a matching
   filename alone.
5. The commit skill documents two explicit paths: a normal completed-phase
   commit with all current gates, and a non-final paused checkpoint with pause
   evidence and no phase advancement. It continues to state that paused work
   blocks push/PR closeout.
6. PR guidance says every phase must be `complete` or fully evidenced as
   `cancelled`, with at least one completed phase and one commit per completed
   phase. `paused` remains unfinished.
7. The exact skill audit covers every `shared/skills/*/SKILL.md`, but source
   edits stay limited to the four evidence-backed stale skills unless current
   `dev` supplies concrete contrary evidence.

## Non-goals

- No generic state machine, ownership registry, migration framework, or new
  provider configuration flag.
- No committed `.agents` mode analogous to the optional committed Copilot
  surface.
- No relaxation of paused evidence, completion quality gates, cancellation
  evidence, or push/PR closeout.
- No redesign of Antigravity agents, skills, hooks, MCP configuration, model
  routing, or provider metadata.
- No changes to `.claude/` nested-repository ownership or `.codex/` semantics.
- No silent adoption, deletion, overwrite, or relocation of consumer-created
  `.agents` content.
- No direct edits to generated `dist/` files.

## Live-verification assumptions

Current `dev` is authoritative. Verify these assumptions before editing and
record any material deviation in the implementation session log:

- `scripts/runtime_ownership.py` still owns `ROOT_ADAPTER_PATHS`,
  `RESTORABLE_ROOT_PATHS`, `active_ignore_patterns()`, `restore_manifest()`, and
  `install_mode_from_manifest()`.
- `scripts/install_bootstrap.py` still owns `copy_generated_tree()`,
  `populate_bootstrap_root()`, `ignore_block()`/`merge_gitignore()`, and the
  current Antigravity file-manifest compatibility helpers.
- `scripts/generate_targets.py::render_antigravity()` still emits
  `.claude/antigravity-ownership.env`.
- `shared/hooks/scripts/restore-root-adapters.sh` still has a separate
  `BOOTSTRAP_ANTIGRAVITY_PATH`/allowlist parser in addition to its root-adapter
  allowlist.
- `scripts/check_runtime.py::runtime_drift_errors()` and
  `scripts/validate_targets.py::validate_antigravity_manifest_and_skills()`
  still special-case file-granular Antigravity ownership.
- Existing generated-only consumers can be recognized from valid legacy
  ownership evidence and/or the old bootstrap-root mirror. Verify the actual
  manifest shape and install order before choosing the smallest compatibility
  reader.
- `scripts/validate_targets.py::validate_determinism()` remains the canonical
  independent temporary-generation comparison.
- The four audited stale skills are still the only evidence-backed stale
  `shared/skills/*/SKILL.md` files. Re-run the exact audit after updating from
  `dev`; do not broaden edits from keyword matches alone.

## Phase

- [ ] `2026-08-24_phase-A-antigravity-directory-ownership-and-paused-commit-skill`

## Verification

```bash
uv run pytest tests/test_install_bootstrap.py tests/test_state_sync.py tests/test_validate_targets.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy scripts/ --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
```
