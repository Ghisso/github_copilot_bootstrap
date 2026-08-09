# Plan — Deterministic commit gate (`R-HOOKS-07`)

**Status:** Proposed
**Date:** 2026-07-08
**Derives from:** architecture-review-2026-07.md §4.2 ("the strategic option that obsoletes half of this") and the post-review assessment of remaining item #1.
**Effort:** M (5 phases, each independently committable)

---

## 1. Problem

All commit enforcement today lives in a **`PreToolUse` hook** ([enforce-commit-gate.sh](../shared/hooks/scripts/enforce-commit-gate.sh)), which can only gate the AI agent's own Bash tool calls. Four gaps follow structurally, none closable by improving the classifier:

1. **Only the agent is gated.** A human `git commit`, an IDE commit button, or a script never pass through the hook — the gate guardrails the agent, it does not guarantee a repo invariant.
2. **git aliases bypass it.** The classifier matches the literal `commit` token; a user alias `git ci` → `commit` is invisible. `§0` of the review lists this as the one acknowledged residual.
3. **Timeout fails open on Copilot.** ~6 git calls + `find` + N×`stat` under a pinned 10s `timeoutSec`; on Copilot, timeout = *allow*.
4. **Self-attested, tool-layer-dependent.** Blocking depends on runtime stdout conventions that differ across Claude/Copilot/Codex.

## 2. Goal

Add a **second, deterministic enforcement layer that runs inside git itself**, mirroring the must-never-skip commit contract. Because it fires from git's own lifecycle, it catches human/alias/script/IDE commits uniformly, on one code path, with no payload to parse, no stdout convention, and no timeout-fail-open.

**Non-goal:** removing the `PreToolUse` gate. That layer stays — it provides *edit-time* protection ([protect-files.sh](../shared/hooks/scripts/protect-files.sh)) and the ability to `ask` (which a git hook cannot), and it gives the agent an actionable message *before* it wastes a turn. The git hook is belt-and-suspenders for the commit invariant specifically.

---

## 3. Design decisions

### D1 — Use the `commit-msg` hook, not `pre-commit` *(decided)*

The existing gate keys its bypass logic (`fixup!`/`squash!`/`chore(typo):`/`docs(typo):`) off the **commit subject**. The commit message does not exist at `pre-commit` time (for editor commits it is entered *after*), so `pre-commit` cannot achieve bypass parity. `commit-msg` receives the message file as `$1`, fires for `-m`/`-F`/editor commits alike, has full repo state available, and is skipped by `--no-verify`. It is therefore the only stage that can faithfully mirror the current subject-aware contract.

### D2 — Install via `core.hooksPath` → a generated, tracked-in-bootstrap dir *(decided)*

The hook ships as source in `shared/hooks/git-hooks/commit-msg`, generates into the consumer's `.claude/hooks/git-hooks/commit-msg`, and the installer sets `git config core.hooksPath .claude/hooks/git-hooks`. Rationale:

- Fits the existing generate-from-`shared/` / install-into-consumer model; `update_consumers.py` refreshes it for free.
- Reuses the executable-bit machinery the generator already runs on `hooks/scripts/*.sh` (the `§0` fix).
- Reuses `_lib-frontmatter.sh` directly — no new parsing code.

**Known degradation (accepted):** `.claude/` is gitignored + HF-synced in consumers, so on a fresh clone *before* HF sync the hook dir is absent → git prints a warning and runs no hook (fails open for humans on un-bootstrapped clones). This is consistent with how the rest of the AI state already behaves; the devcontainer `post-start` step (Phase 3) closes it for the container path. Rejected alternative: writing `.git/hooks/commit-msg` directly — not version-controlled, drifts, and `update_consumers.py` could not refresh it.

### D3 — Full contract parity via a single shared function *(decided)*

Rather than duplicating checks, extract the **ceremony** body of `enforce-commit-gate.sh` (big/small-plan, score JSON schema + `content_hash` freshness, closeout `**Status:** COMPLETED`, LEARN evidence) into one shared function `assert_commit_invariants <repo_root> <branch>` in `_lib-frontmatter.sh`. **Branch-shape is deliberately *not* in the shared function** — per D4-B the two callers diverge on it, so each owns its own branch decision and then calls the shared ceremony checks:

- `enforce-commit-gate.sh` (PreToolUse): classify Bash command → if commit → wrong branch adds a failure (unchanged) → if not bypass, `assert_commit_invariants` → emit `deny` JSON.
- `commit-msg` git hook: read subject from `$1` → **not an `_implementation` branch → `exit 0` (passthrough)** → bypass subject → `exit 0` (skip ceremony; branch already valid) → else `assert_commit_invariants` → `exit 1` with the joined reason on failure.

This is a **single-homing win** aligned with the review's `R-LIB-01`: the plan/score/closeout/LEARN contract gets exactly one definition and the two entry points cannot drift, while the intentional branch-scope difference stays visible in the callers rather than hidden in a flag. Bash 3.2 remains the orchestration baseline, while a small Python 3 standard-library helper performs top-level and `counts` JSON traversal. The helper is invoked by Bash and has no `uv` dependency, so the git hook remains enforceable without a project environment.

### D4 — Branch scope of the git-layer mirror *(decided — Option B)*

The current PreToolUse contract fails any commit not on a `<plan>_implementation` branch. The question is whether the git hook should mirror that for *everyone* (including humans) or scope itself to where feature work actually lands.

- **Option A:** full parity. Direct commits to `dev`/`main` are blocked for humans too; `git commit --no-verify` is the escape.
- **Option B (chosen):** the git hook runs ceremony checks **only on `<plan>_implementation` branches** and passes through (`exit 0`) on any other branch.

**Decision: Option B.** This is not merely "lighter" — it is the coherent line for this workflow. Feature work happens on `_implementation` branches, and every commit reaching one — human, IDE, script, or the `git ci` **alias** — is fully gated, so the meaningful cases behind remaining-item #1 and #2 are still closed. `dev`/`main` stay free for merges and casual human commits, which the branch-tier workflow expects anyway. The `PreToolUse` gate is unchanged and continues to deny *agent* commits on the wrong branch; only the git-layer mirror is scoped.

**Consequence for D3:** branch-shape handling therefore lives in each *caller*, not in the shared function — the two callers deliberately diverge on it (PreToolUse: wrong branch → deny; git hook: wrong branch → passthrough). See D3.

### D5 — Staged vs working-tree content is safe *(no action)*

The score's `content_hash` is computed over `git diff <merge-base>` (working tree). The contract already requires `dirty == false`, i.e. working tree == index, so the committed (staged) content equals what was hashed. `HEAD` at `commit-msg` time is still the parent (the new commit object does not exist yet), identical to when `PreToolUse` fires — so the `head_sha`/`merge_base_sha` equality checks translate unchanged.

---

## 4. Implementation phases

Each phase is one small plan, in dependency order; each leaves the tree green (`validate_targets.py` passing) and is independently committable.

### Phase 1 — `R-HOOKS-07a`: extract `assert_commit_invariants` (pure refactor)

- **Change:** move the **ceremony** body of [enforce-commit-gate.sh](../shared/hooks/scripts/enforce-commit-gate.sh) (big/small-plan, score JSON schema + `content_hash` freshness, closeout `**Status:** COMPLETED`, LEARN evidence — *not* the branch-shape check) into `assert_commit_invariants <repo_root> <branch>` in [_lib-frontmatter.sh](../shared/hooks/scripts/_lib-frontmatter.sh), appending to a caller-provided `failures` array (or printing a newline-joined reason + return code). `enforce-commit-gate.sh` keeps its own branch-shape failure + bypass handling and calls the shared fn for the rest.
- **Acceptance:** no behavior change; existing `validate_targets.py` commit-gate payloads still pass byte-identically; `dist/` regenerates drift-free.
- **Depends:** none.

### Phase 2 — `R-HOOKS-07b`: add the `commit-msg` hook + generation

- **Change:** create `shared/hooks/git-hooks/commit-msg`: resolve repo root via `git rev-parse --show-toplevel` (reliable inside a git hook), source `_lib-frontmatter.sh`, read subject = first line of `$1`, then — per D4-B — **if the current branch is not `<plan>_implementation`, `exit 0` (passthrough)**; else if `is_bypass_subject`, `exit 0` (skip ceremony, branch already valid); else call `assert_commit_invariants` and `exit 1` with the reason on failure. Extend [generate_targets.py](../scripts/generate_targets.py) to copy `shared/hooks/git-hooks/` → `.claude/hooks/git-hooks/` for every target and mark it executable (the same `ensure_executable` loop that covers `hooks/scripts/*.sh`).
- **Acceptance:** `generate_targets.py --all` emits an executable `.claude/hooks/git-hooks/commit-msg` in each target; `dist/` drift check passes; the generated script is runnable (the validator's executability assertion covers it).
- **Depends:** Phase 1.

### Phase 3 — `R-HOOKS-07c`: wire installation

- **Change:**
  - [install_bootstrap.py](../scripts/install_bootstrap.py): add `configure_git_hooks_path(target, dry_run)` after `chmod_runtime_scripts` in `main()` — runs `git -C <target> config core.hooksPath .claude/hooks/git-hooks` (idempotent; skip with a warning if `<target>` is not a git repo). Extend `chmod_runtime_scripts` patterns to include `.claude/hooks/git-hooks/*`.
  - [post-start.sh](../shared/devcontainer/post-start.sh): after the `.git` ownership fix, set `core.hooksPath` so fresh container clones are gated even before other steps.
  - `update_consumers.py` inherits automatically (it regenerates + re-installs).
- **Acceptance:** after `install_bootstrap.py <repo> --bucket ...`, `git -C <repo> config core.hooksPath` returns `.claude/hooks/git-hooks`; a crafted invalid commit in `<repo>` is rejected by git with the gate's reason; a valid one succeeds.
- **Depends:** Phase 2.

### Phase 4 — `R-HOOKS-07d`: adversarial validator cases

- **Change:** in [validate_targets.py](../scripts/validate_targets.py), add throwaway-repo cases that set `core.hooksPath` to the generated dir and run real `git commit`s. All commits below are on a `<plan>_implementation` branch unless stated:
  - invalid state (no score / score < 90 / stale `content_hash` / small-plan not `complete` / missing closeout `**Status:** COMPLETED` / missing LEARN) → **blocked** (`git commit` exits non-zero).
  - fully valid state → **allowed**.
  - **alias evasion** (`git config alias.ci commit; git ci -m ...`) with invalid state → **blocked** — the residual the layer exists to close, caught here because the commit lands on an implementation branch.
  - `git -C <path> commit` with invalid state → **blocked**.
  - any commit on `dev`/`main` (human or agent, valid or not) → **allowed (passthrough)** per D4-B.
  - `git commit --no-verify` on an implementation branch → **allowed** (documents the sanctioned escape).
- **Acceptance:** all new cases pass; runs on both GNU and (if available) BSD `stat` paths via the portable `file_mtime`.
- **Depends:** Phase 3.

### Phase 5 — `R-HOOKS-07e`: documentation

- **Change:** update the Hooks section of [README.md](../README.md), [runtime-checks.md](runtime-checks.md), and [smoke-tests.md](smoke-tests.md) to describe the two-layer model (PreToolUse = edit-time + agent UX + `ask`; `commit-msg` = deterministic commit invariant), the `--no-verify` escape, and the un-synced-clone degradation (D2).
- **Acceptance:** docs describe both layers and the escape; no doc claims the git hook catches `--no-verify` commits.
- **Depends:** Phase 4.

---

## 5. What this closes vs. leaves open

**Closes**, for every commit reaching a `<plan>_implementation` branch: human/IDE/script commits ungated (#1), git-alias evasion (#2 — `git ci` now hits the same gate), Copilot timeout-fail-open for the commit invariant (#3, git hooks have no such timeout), and cross-runtime stdout-convention dependence for commits (#4).

**Leaves open (by design):**

- Commits on `dev`/`main` are not gated by this layer (D4-B) — feature work happens on `_implementation` branches, and the `PreToolUse` gate still denies *agent* commits on the wrong branch.
- `git commit --no-verify` — explicit, auditable, and the intended manual override.
- Un-bootstrapped fresh clones outside the devcontainer until `.claude/` is synced (D2).
- The score JSON / plan status remain **agent-authored** — this layer verifies the *contract*, it does not make the inputs independently trustworthy (out of scope; unchanged from today).

---

## 6. Out of scope

- Server-side / pre-receive enforcement (personal single-author workflow; `--no-verify` locally is sufficient).
- Detecting `--no-verify` usage (git provides no hook that fires when hooks are skipped; would need a wrapper/alias, rejected as gameable).
- Any change to the PreToolUse layer's edit-time behavior.

## 7. Overall acceptance

Orchestrated end-to-end on a throwaway consumer repo: install → `core.hooksPath` set → on an `_implementation` branch, invalid `git commit`s (including the `git ci` alias and `git -C` forms) are rejected by git and a fully valid one succeeds; commits on `dev`/`main` pass through untouched (D4-B); `--no-verify` documented and demonstrated as the escape; `validate_targets.py` adversarial suite green; `dist/` drift-free.
