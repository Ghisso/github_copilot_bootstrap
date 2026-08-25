# Review Report

Profiles: code, architecture, security, tests, ponytail, documentation

Gate: commit

Pass 1 reviewed every uncommitted change plus the affected installer, restore,
runtime, skill, test, and documentation contracts. Pass 2 attempted to refute
each candidate against the live code and with focused disposable-directory
probes. The findings below survived verification without additions or drops.

## Critical

- **[high confidence] [security] `scripts/install_bootstrap.py:260` — takeover preflight can delete an unclassified bootstrap-root `.agents` tree.** `validate_agents_takeover()` returns immediately when the outer `.agents` path is absent, and returns at line 269 when that outer tree matches the generated source. Neither return classifies an already-present `.claude/bootstrap-root/.agents` tree. `populate_bootstrap_root()` later removes that directory recursively at lines 795-803. A disposable probe with a private `bootstrap-root/.agents/private.txt` confirmed that both the absent-outer-tree path and the byte-identical-outer-tree path return successfully and then delete the private file. This violates the pre-write/no-data-loss boundary. Classify every mirror that can be replaced before either early return, report mirror-relative conflicts accurately, and add regressions proving no write occurs.

- **[high confidence] [security] `scripts/install_bootstrap.py:224` — unsafe and malformed legacy evidence can authorize deletion.** `_legacy_agents_evidence()` uses `Path.is_file()` and `read_text()` without rejecting symlinks, while `_legacy_agents_records(..., True)` accepts any `BOOTSTRAP_ROOT_PATH=` value at lines 211-217. The takeover decision can then accept evidence at lines 293-298. A disposable probe used a symlinked `antigravity-ownership.env`, a manifest containing `BOOTSTRAP_ROOT_PATH=../../outside`, and an otherwise private legacy-shaped skill; the takeover was accepted. The later refresh can prune that skill as obsolete. Reject symlink/non-regular evidence files, validate the complete legacy manifest shape and mode before trusting its Antigravity intersection, and test symlinked and malformed-root evidence end to end.

## Major

- **[high confidence] [documentation] `shared/skills/context-status/SKILL.md:13` — the corrected skill still does not read plan frontmatter.** Its only plan check is `ls -lt ... | head -3`; that cannot distinguish big from small plans or obtain any live status. Changing only the report placeholders at lines 45-46 leaves the skill unable to produce the promised result. Parse the actual `type` and `status` frontmatter and select/report the active big and small plans from those values.

- **[high confidence] [documentation] `shared/skills/setup-project/SKILL.md:21` — the installer runs before Git initialization, so the generated project misses hook configuration.** Step 2 invokes `install_bootstrap.py`, but `git init` is deferred until Step 4. The installer explicitly skips `core.hooksPath` when `.git` does not exist, and the skill never reruns it. The Step 7 command also lists empty scaffold directories (`docs`, `examples`, and `scripts`), so the advertised `git add` can fail with unmatched pathspecs. Initialize Git before installation and make the staged-path example runnable for the files the skill actually creates.

- **[high confidence] [tests] `tests/test_install_bootstrap.py:522` — the high-risk takeover matrix is incomplete and missed both critical fail-open paths.** The new tests cover an outer-tree symlink and a syntactically invalid allowlist, but do not cover unknown/unsafe mirror content when the outer tree is absent or current, symlinked evidence, malformed `BOOTSTRAP_ROOT_PATH` records, non-regular evidence, sorted multi-conflict diagnostics, or a legacy-evidence-only migration (the migration fixture is accepted through byte-identical mirror evidence first). `tests/test_state_sync.py` also has no `.agents` directory restore regression. Add direct pre-write snapshots for these cases and mutation tests for every required/forbidden stale-skill claim, not only one required token per skill.

- **[high confidence] [documentation] `README.md:516` — checked-in lifecycle documentation still describes the removed file-granular ownership model.** README says adjacent private agents survive; `docs/architecture.md:201`, `docs/target-mapping.md:140`, `docs/runtime-checks.md:211`, and `docs/smoke-tests.md:196` repeat the old namespace, two-manifest, per-file ownership and restore contract. Those claims now directly contradict the directory-level implementation and could cause consumers to lose content after assuming it remains supported. Update the planned documentation set to state that `.agents/` is bootstrap-owned, describe fail-closed migration and backup instructions, and remove obsolete manifest/path-count claims.

## Minor

- **[high confidence] [documentation] `shared/skills/commit/SKILL.md:80` — cancellation-aware push wording is internally contradictory.** “All phases must be complete” is immediately qualified by allowing evidenced cancellation. Say that every phase must be terminal (`complete` or fully evidenced `cancelled`), require at least one completed phase and its commit, and keep paused blocked. Also state directly that a checkpoint keeps the big plan `in-progress` and the same `current_phase`, rather than relying only on “does not advance the phase machine.”

- **[high confidence] [documentation] `shared/skills/plan-decomposition/SKILL.md:31` — cancellation frontmatter remains underspecified.** The skill names all pause fields but only says “cancellation evidence”; the live validator requires `cancelled_at`, `cancelled_reason`, and `cancelled_evidence`. Name those fields so generated plans do not depend on readers guessing the enforced schema.

## Ponytail

No unnecessary dependency, framework, provider mode, or generic lifecycle
abstraction survived review. The narrow legacy helpers are justified by the
migration, subject to the safety corrections above.

## Gate Result

**FAIL** — two CRITICAL data-loss/trust-boundary defects block commit. The MAJOR
findings also block later push/PR closeout.

```json
[
  {"severity":"CRITICAL","title":"takeover preflight can delete an unclassified bootstrap-root .agents tree","file":"scripts/install_bootstrap.py","line":260,"profile":"security"},
  {"severity":"CRITICAL","title":"unsafe and malformed legacy evidence can authorize deletion","file":"scripts/install_bootstrap.py","line":224,"profile":"security"},
  {"severity":"MAJOR","title":"context-status skill still does not read plan frontmatter","file":"shared/skills/context-status/SKILL.md","line":13,"profile":"documentation"},
  {"severity":"MAJOR","title":"setup-project installs before Git initialization and misses hook configuration","file":"shared/skills/setup-project/SKILL.md","line":21,"profile":"documentation"},
  {"severity":"MAJOR","title":"high-risk takeover matrix is incomplete and missed fail-open paths","file":"tests/test_install_bootstrap.py","line":522,"profile":"tests"},
  {"severity":"MAJOR","title":"checked-in docs still describe removed file-granular .agents ownership","file":"README.md","line":516,"profile":"documentation"},
  {"severity":"MINOR","title":"cancellation-aware push wording is internally contradictory","file":"shared/skills/commit/SKILL.md","line":80,"profile":"documentation"},
  {"severity":"MINOR","title":"cancellation frontmatter remains underspecified","file":"shared/skills/plan-decomposition/SKILL.md","line":31,"profile":"documentation"}
]
```
