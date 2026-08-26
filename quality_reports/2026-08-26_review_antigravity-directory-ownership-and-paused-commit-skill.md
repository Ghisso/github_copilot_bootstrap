# Review Report

Profiles: code, architecture, security, tests, ponytail, documentation

Gate: commit

This re-review examined the remediated uncommitted diff and explicitly
re-verified every finding from the first review. Pass 1 reviewed the updated
implementation and regressions. Pass 2 attempted to refute each candidate with
direct code reads and focused disposable-directory probes. The code/skill
fixes removed five previous findings, but one critical takeover path remains;
the documentation finding also remains open pending DOCUMENT.

## Critical

- **[high confidence] [security] `scripts/install_bootstrap.py:323` — matching outer and mirror trees are trusted without proof that the mirror is bootstrap-owned.** When `.agents` and `.claude/bootstrap-root/.agents` contain identical content, lines 323-330 add no conflict and lines 344-345 accept the tree solely because the bytes match. No current `bootstrap-ownership.env` record or valid legacy evidence is required. A disposable probe placed the same private `skills/private/SKILL.md` in both locations with no ownership manifest; takeover succeeded, `copy_generated_tree()` pruned the private file, and `populate_bootstrap_root()` replaced the mirror. Require a valid current root manifest or strictly valid legacy evidence before treating a matching tree as a “prior mirror.” Byte-identical current generated content may still pass independently. The same ownership proof should allow a valid current consumer whose outer `.agents` is absent and whose older managed mirror needs refresh; the current code incorrectly blocks that safe case as source drift.

## Major

- **[high confidence] [security] `scripts/install_bootstrap.py:252` — invalid-UTF-8 legacy evidence escapes the fail-closed diagnostic path.** `_regular_text()` catches `OSError` but not `UnicodeDecodeError`. A disposable probe with invalid UTF-8 in `antigravity-ownership.env` raised an uncaught traceback instead of the stable, sorted, actionable refusal required for malformed evidence. Catch decoding errors and classify the evidence file as a conflict. Add equivalent coverage for non-regular evidence.

- **[high confidence] [tests] `tests/test_install_bootstrap.py:522` — the safety matrix still misses the surviving trust bug and malformed/non-regular evidence cases.** The new mirror tests cover absent/current outer trees only when the mirror differs. They do not test identical unowned outer/mirror content, a valid current manifest with a managed prior mirror and missing outer tree, invalid UTF-8, or non-regular evidence. The legacy-only fixture and `.agents` restore happy path now close earlier gaps. `tests/test_validate_targets.py:103` also mutates selected required fragments but still does not exercise each forbidden stale claim even though the phase requires mutation tests for every obsolete form.

- **[high confidence] [documentation] `README.md:516` — checked-in docs still describe removed file-granular ownership.** README says adjacent private agents survive; `docs/architecture.md:201`, `docs/target-mapping.md:140`, `docs/runtime-checks.md:211`, and `docs/smoke-tests.md:196` repeat the old namespace, two-manifest, per-file ownership and restore contract. This finding is intentionally still open pending DOCUMENT. Update the planned documentation set to state directory-level bootstrap ownership, fail-closed migration, and backup/removal instructions, and remove obsolete manifest/path-count claims.

## Minor

None.

## Resolved From Pass 1

- The preflight now inspects a differing or unsafe mirror before the previous
  early-return paths and reports mirror-relative conflicts.
- Legacy evidence symlinks and malformed root-manifest records are rejected.
- `context-status` now reads `type` and `status` from plan frontmatter.
- `setup-project` initializes Git before installation and stages only paths the
  scaffold creates.
- Commit and plan-decomposition guidance now states the current-phase,
  terminal cancellation, and exact cancellation-field contracts.
- A legacy-evidence-only migration test and ordinary `.agents` restore test now
  exist.

## Ponytail

No unnecessary dependency, framework, provider mode, or generic lifecycle
abstraction survived review. The migration helpers remain narrowly scoped.

## Gate Result

**FAIL** — one CRITICAL data-loss/trust-boundary defect blocks commit. The
remaining MAJOR findings also block later push/PR closeout.

```json
[
  {"severity":"CRITICAL","title":"matching outer and mirror trees are trusted without ownership proof","file":"scripts/install_bootstrap.py","line":323,"profile":"security"},
  {"severity":"MAJOR","title":"invalid-UTF-8 legacy evidence escapes the fail-closed diagnostic path","file":"scripts/install_bootstrap.py","line":252,"profile":"security"},
  {"severity":"MAJOR","title":"safety matrix still misses surviving trust and malformed-evidence cases","file":"tests/test_install_bootstrap.py","line":522,"profile":"tests"},
  {"severity":"MAJOR","title":"checked-in docs still describe removed file-granular .agents ownership","file":"README.md","line":516,"profile":"documentation"}
]
```
