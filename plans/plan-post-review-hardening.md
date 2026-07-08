# Plan — Post-review hardening (`R-HOOKS-08/09`, `R-CI-01`, `R-SCORE-03`, `R-VALID-02`, `R-DOCS-02`, `R-MCP-01`)

**Status:** Proposed
**Date:** 2026-07-08
**Derives from:** external assessment of the repo after [architecture-review-2026-07.md](architecture-review-2026-07.md) (all 31 items implemented) and [plan-deterministic-commit-gate.md](plan-deterministic-commit-gate.md) (R-HOOKS-07a–e implemented on branch `deterministic-commit-gate`), cross-checked against the three inspiration projects (sources in §9).
**Effort:** L (7 phases; each phase is one small plan / one commit; Phase 4 splits into sub-commits like R-HOOKS-07 did)
**Audience note:** this plan is written to be implemented by an agent without prior context. Every phase names its files, its behavior contract, and a runnable acceptance check. Read §1 (required context) before touching anything.

---

## 1. Required context (read these first, in this order)

1. [docs/architecture.md](architecture.md) — source-vs-generated layout, hook dispatcher, lifecycle enforcement model.
2. [docs/plan-deterministic-commit-gate.md](plan-deterministic-commit-gate.md) — the two-layer commit enforcement design (D1–D5). This plan extends the same design vocabulary; D4-B ("git-layer hooks gate only `<plan>_implementation` branches, pass through everywhere else") applies to every git hook added here.
3. [shared/hooks/git-hooks/commit-msg](../shared/hooks/git-hooks/commit-msg) — the existing git-layer gate (39 lines).
4. [shared/hooks/scripts/_lib-frontmatter.sh](../shared/hooks/scripts/_lib-frontmatter.sh) — the shared library; `assert_commit_invariants` (the single-homed ceremony contract), `is_implementation_branch`, `is_bypass_subject`, `fm_read`/`fm_read_list`, `json_file_string_value`.
5. [shared/hooks/scripts/enforce-pr-gate.sh](../shared/hooks/scripts/enforce-pr-gate.sh) — the PreToolUse PR/push gate whose ceremony body Phase 3 extracts.
6. [shared/scripts/quality_score.py](../shared/scripts/quality_score.py) — the scorer; its git-metadata stamping (`branch`, `head_sha`, `merge_base_sha`, `base_ref`, `dirty`, `content_hash`, `generated_at`) is the pattern Phase 4 reuses.
7. [scripts/generate_targets.py](../scripts/generate_targets.py) — note line ~177: `shared/hooks/git-hooks/` is already copied to `.claude/hooks/git-hooks/` and chmodded for every target. New git hooks are picked up automatically.
8. [scripts/validate_targets.py](../scripts/validate_targets.py) — `validate_lifecycle_hook_guardrails` builds throwaway git repos and executes real gates; the R-HOOKS-07d cases (search for `core.hooksPath`) are the template for every new validator case in this plan.
9. [scripts/install_bootstrap.py](../scripts/install_bootstrap.py) — sets `core.hooksPath` and chmods `.claude/hooks/git-hooks/*` (already covers new hooks).

**Repo conventions that bind this plan:**

- Never hand-edit `dist/`. Change `shared/` or `scripts/`, then run `uv run python scripts/generate_targets.py --all`.
- Every phase must leave `uv run python scripts/validate_targets.py` green and the `dist/` drift/determinism check passing.
- Guardrail scripts must work without `uv` (pure bash primary path); `uv` is only for the Python scripts and enhancements.
- One phase = one commit, subject prefixed with the phase ID (e.g. `R-HOOKS-08: ...`), matching the existing history style.

---

## 2. Phase 1 — `R-HOOKS-08`: merge commits must pass through the `commit-msg` gate

### Issue

Per `githooks(5)`, the `commit-msg` hook is invoked by **`git-merge` as well as `git-commit`**. The shipped hook ([commit-msg:21-30](../shared/hooks/git-hooks/commit-msg#L21-L30)) has no merge handling, so a routine mid-phase refresh — `git merge dev` on a `<plan>_implementation` branch — produces a merge commit whose subject (`Merge branch 'dev' into ...`) is not a bypass prefix, on a branch whose ceremony state is legitimately incomplete mid-phase. The merge is therefore **blocked**, and the only documented way out is `git commit --no-verify` / `git merge --no-verify`. This recreates the exact incentive loop §3.5 of the architecture review warned about: friction on a legitimate action pushes the user toward the escape hatch, normalizing its use.

D4-B's rationale ("`dev`/`main` stay free for merges") covered merges *into* `dev` but missed merges *from* `dev` into implementation branches.

### Fix

A merge commit introduces no new working-tree content of its own; the ceremony contract (score, closeout, LEARN) is about authored changes and is re-checked on the next real commit anyway (and the score's `merge_base_sha`/`content_hash` checks will correctly demand a fresh report after the merge). So: **pass merge commits through**, unledgered — a merge from `dev` is routine housekeeping, not a ceremony bypass, and ledgering it would force `bypass_acknowledged` churn in the big plan for every refresh.

### Changes

1. In [shared/hooks/git-hooks/commit-msg](../shared/hooks/git-hooks/commit-msg), after the `is_implementation_branch` check and before the `is_bypass_subject` check, add:

   ```bash
   # githooks(5): commit-msg also fires for git-merge. A merge commit authors
   # no content of its own; ceremony re-attaches at the next real commit
   # (the score's merge_base/content_hash checks force a fresh report then).
   if git -C "$REPO_ROOT" rev-parse -q --verify MERGE_HEAD >/dev/null 2>&1; then
     exit 0
   fi
   ```

2. Documentation (same commit): add one paragraph to the "Two-Layer Commit Enforcement" section of [docs/runtime-checks.md](runtime-checks.md) and the "Deterministic Commit Gate" section of [README.md](../README.md) stating: (a) merge commits pass through the `commit-msg` layer by design; (b) `git rebase` and `git cherry-pick` do **not** invoke `commit-msg` (git behavior, not a bug) — commits created by them skip the git layer, and the next real commit is still gated; (c) `git commit --amend` *does* invoke it, and the `content_hash` check is designed to survive content-preserving amends.

3. Regenerate `dist/`.

### Acceptance

- New validator case in [scripts/validate_targets.py](../scripts/validate_targets.py) (extend the R-HOOKS-07d throwaway-repo block): on an `_implementation` branch with **invalid** ceremony state, `git merge --no-ff dev` (with a diverging commit on `dev` so a real merge commit is created) **succeeds**; immediately afterwards a normal `git commit` with the same invalid state is still **rejected**.
- `uv run python scripts/generate_targets.py --all && uv run python scripts/validate_targets.py` → PASS.
- `grep -n "MERGE_HEAD" dist/multi-agent/.claude/hooks/git-hooks/commit-msg` → one match.

---

## 3. Phase 2 — `R-CI-01`: continuous validation via GitHub Actions

### Issue

The repo has **no `.github/workflows/` directory at all**. `validate_targets.py` (~1,200 lines, including real behavioral tests that execute the hook gates in throwaway git repos) is the repo's strongest asset, and it only runs when someone remembers to run it. The upstream project (`claude-code-my-workflow`) added mechanical drift-policing scripts *after being burned three times* by docs/inventory drift; armory runs per-package validation in CI with weekly drift detection. This repo already owns the validation logic — it is simply not automated. Every subsequent phase of this plan adds validator cases; CI is what makes them permanent protection instead of a one-time check.

### Fix

One workflow that regenerates and validates on every push and PR, on both Linux and macOS (the hook layer has explicit GNU-vs-BSD `stat`/`find` fallback paths — `file_mtime` in `_lib-frontmatter.sh` — that only a macOS runner actually exercises).

### Changes

1. Create `.github/workflows/validate.yml`:
   - Triggers: `push` (all branches), `pull_request`.
   - Matrix: `ubuntu-latest`, `macos-latest`.
   - Steps: checkout → install uv (`astral-sh/setup-uv@v5`) → `uv run python scripts/generate_targets.py --all` → `uv run python scripts/validate_targets.py`.
   - The validator creates commits in throwaway repos; CI runners have no git identity. Set `GIT_AUTHOR_NAME/EMAIL` and `GIT_COMMITTER_NAME/EMAIL` env vars at the job level **unless** the validator already passes `-c user.name=... -c user.email=...` when committing — check first (`grep -n "user.name" scripts/validate_targets.py`) and only add what is missing.
   - The scripts are stdlib-only (per [docs/architecture.md](architecture.md)); no dependency install step is needed beyond uv itself. If `uv run` demands a project venv, fall back to `python3 scripts/...` — both scripts are stdlib-only by design.
2. **Do not** add this repo's `.github/workflows/` to any generated target or ignore logic. It is authoring-repo infrastructure, not part of the bootstrap bundle. Verify: `generate_targets.py` does not glob `.github/` from the repo root (it renders Copilot adapters from `shared/`, not from the root `.github/`) — confirm with a regenerate + `git status` showing no `dist/` change from this phase.

### Acceptance

- Workflow file exists; `git push` on the feature branch shows the run green on both OSes (or, if pushing is out of scope for the implementing agent, `actionlint` or careful YAML review plus a note in the commit message that first-run verification is pending).
- Regenerating `dist/` produces no diff attributable to this phase.

---

## 4. Phase 3 — `R-HOOKS-09`: deterministic `pre-push` gate (mirror of the PR gate)

### Issue

R-HOOKS-07 gave the **commit** invariant a deterministic git layer, but the **push/PR** invariant still lives only in the PreToolUse hook [enforce-pr-gate.sh](../shared/hooks/scripts/enforce-pr-gate.sh). A human `git push`, an IDE push button, a script, or a `git p` alias never passes through it — so phase-completion and bypass-acknowledgment checks gate only the agent, exactly the structural gap §1 of [plan-deterministic-commit-gate.md](plan-deterministic-commit-gate.md) identified for commits. A `pre-push` git hook closes it on the same one-code-path terms, and additionally backstops `--no-verify` commits: a commit that skipped `commit-msg` still cannot be *pushed* until the ceremony is complete.

### Fix

Mirror the D3 single-homing pattern: extract the ceremony body of `enforce-pr-gate.sh` into one shared function both layers call; add `shared/hooks/git-hooks/pre-push` scoped per D4-B.

### Design decisions (settled — do not re-litigate)

- **D3-analog:** extract `assert_push_invariants <repo_root> <branch>` into [_lib-frontmatter.sh](../shared/hooks/scripts/_lib-frontmatter.sh), covering: big-plan file exists for the branch slug; all `phases` small plans exist with `status: complete`; `rev-list --count dev..HEAD` ≥ phase count; bypass-ledger acknowledgment (the `hooks-bypass.log` / `bypass_acknowledged` logic at [enforce-pr-gate.sh:69-80](../shared/hooks/scripts/enforce-pr-gate.sh#L69-L80)). Appends to the caller-provided `failures` array, same convention as `assert_commit_invariants`.
- **What stays PreToolUse-only:** the `gh pr create --base dev` check. `pre-push` has no PR concept; PR-creation shape remains gated at the tool layer only. Document this divergence.
- **D4-B scope:** `pre-push` reads the ref lines from stdin (`<local-ref> <local-sha> <remote-ref> <remote-sha>` per line). For each line: skip if the local ref is not `refs/heads/<name>_implementation`; skip branch deletions (local sha = 40 zeros). If any implementation ref fails `assert_push_invariants`, print the joined reasons to stderr and `exit 1` (which aborts the whole push — acceptable; mixed pushes of implementation + other branches are not a supported workflow).
- **Escape:** `git push --no-verify` skips `pre-push`; it is the same sanctioned manual escape as the commit layer. Document it identically.
- **Branch to validate against:** `assert_push_invariants` derives the plan slug from the *ref name being pushed*, not from `HEAD` — a `git push origin foo_implementation` while checked out elsewhere must still gate `foo_implementation`. Use `git rev-list --count dev..<local-sha>` with the pushed sha, not `HEAD`.

### Changes

1. `_lib-frontmatter.sh`: add `assert_push_invariants` (extraction; no behavior change to the checks themselves). Refactor `enforce-pr-gate.sh` to call it (keeping payload parsing, branch-shape denial for agents, and the `--base dev` check in the caller).
2. Create `shared/hooks/git-hooks/pre-push` following the structure of the existing [commit-msg](../shared/hooks/git-hooks/commit-msg) (same `SCRIPT_DIR` sourcing, same header comment style, `set -euo pipefail`, pure bash / no `uv`).
3. Generation and installation are **already wired**: `generate_targets.py` copies and chmods everything under `shared/hooks/git-hooks/` (line ~177-180), and `install_bootstrap.py` chmods `.claude/hooks/git-hooks/*`. Verify rather than re-implement.
4. Docs: extend the two-layer sections of [README.md](../README.md), [docs/runtime-checks.md](runtime-checks.md), and [docs/smoke-tests.md](smoke-tests.md) to a "two layers, two invariants" description: commit invariant (`commit-msg`) and push invariant (`pre-push`), each with the PreToolUse twin, the `--no-verify` escape, and the un-synced-clone degradation from D2.

### Acceptance

New validator cases (throwaway repo + a bare remote created with `git init --bare` in the temp dir, `core.hooksPath` set to the generated dir):

- Push of an `_implementation` branch with an incomplete small plan → **blocked** (`git push` exits non-zero, stderr names the phase).
- Same push after marking all phases complete and satisfying the commit-count and bypass checks → **allowed**.
- Push of `dev` with arbitrary ceremony state → **allowed** (passthrough).
- Push of a branch deletion (`git push origin :foo_implementation` or `--delete`) → **allowed**.
- `git push --no-verify` with invalid state → **allowed** (documents the escape).
- Existing PreToolUse `enforce-pr-gate.sh` payload cases still pass byte-identically (the extraction is behavior-preserving).

`uv run python scripts/generate_targets.py --all && uv run python scripts/validate_targets.py` → PASS; generated `pre-push` exists and is executable in `dist/multi-agent/.claude/hooks/git-hooks/`.

---

## 5. Phase 4 — `R-SCORE-03`: severity-gated review findings (the review's own deferred direction)

### Issue

R-SCORE-01/02 made the score report's *binding* rigorous (branch/SHA/merge-base/`content_hash`/`tests_passed`/`dirty` all verified by the gate), but the *number* inside it is still weak: [quality_score.py](../shared/scripts/quality_score.py) `compute_score` is `100 − (mypy>0)·20 − (pytest fail)·15 − Σ ruff·(1–5)`. Clean lint plus a green suite scores 100 **regardless of what the change contains**. The REVIEW stage — the unified reviewer with its primary + refutation passes — produces no artifact the gate can see, so "review happened and found nothing blocking" is enforced only by prompt choreography. R-SCORE-01(d) explicitly deferred the fix: *"direction for the next iteration: severity-count predicate over review findings (upstream-tested) rather than deeper numeric rubric."* Both benchmarks converge on it: upstream replaced its 0–100 score with `CRITICAL>0 → BLOCK, MAJOR>0 → REVISE, else PASS` plus a hallucination gate; armory's `pre-landing-review` blocks CRITICAL findings before merge.

### Fix

Keep the deterministic arithmetic score as the floor (it is honest about what it measures, per the rewritten rubric). **Add** a second gated artifact — a findings report the reviewer persists — bound with the same git metadata as the score report, and tier the gates:

- **Commit gate** (both layers, via `assert_commit_invariants`): requires a fresh matching findings report with `critical == 0`.
- **Push/PR gate** (both layers, via `assert_push_invariants`): additionally requires `major == 0`.

This mirrors upstream's commit-vs-PR tiering in severity form, and reuses the binding machinery this repo has already built twice. The findings remain agent-authored — the gate verifies the contract, not the reviewer's honesty (same consciously-accepted residual as the score inputs, recorded in [plan-deterministic-commit-gate.md §5](plan-deterministic-commit-gate.md)).

### Sub-phases (one commit each, in order)

**4a — `R-SCORE-03a`: `record_findings.py` + schema.**
Create `shared/scripts/record_findings.py` (stdlib-only, rendered into `.claude/scripts/` — mirror how `quality_score.py` is wired in `generate_targets.py`). It accepts `--phase`, `--base-ref` (default `dev`), `--findings-json <path-or-stdin>` (a JSON list of `{severity: CRITICAL|MAJOR|MINOR, title, file, line?, profile}`), `--out .claude/quality_reports/findings-<timestamp>.json`, and stamps the **same git metadata block as `quality_score.py`**: `generated_at`, `branch`, `head_sha`, `merge_base_sha`, `base_ref`, `dirty`, `content_hash`, `target`, plus computed `counts: {critical, major, minor}`. Factor the metadata-stamping into a shared helper only if it can be done without breaking `quality_score.py`'s CLI; otherwise duplicate the ~40 lines with a header comment naming the twin (single-file, no-dependency scripts are a deliberate property here). An empty findings list is valid and yields all-zero counts — that is the normal "review passed clean" artifact.

**4b — `R-SCORE-03b`: commit-gate wiring.**
Extend `assert_commit_invariants` in `_lib-frontmatter.sh`: locate the newest-by-`generated_at` `findings-*.json` matching branch + phase + `merge_base_sha` + `head_sha` + `content_hash` + `dirty: false` (reuse the exact selection/verification code path the score report uses — factor a shared `select_fresh_report <glob> ...` helper if the existing code permits; the score and findings artifacts must be matched by identical rules or they will drift). Missing/stale/mismatched findings report → failure naming the regenerate command (`uv run python .claude/scripts/record_findings.py ...`); `counts.critical > 0` → failure listing the critical titles. Because both `enforce-commit-gate.sh` and `commit-msg` call `assert_commit_invariants`, both layers inherit this with **no per-caller changes** — that is the D3 payoff; verify no caller edits are needed.

**4c — `R-SCORE-03c`: push-gate wiring.**
Extend `assert_push_invariants` (from Phase 3): same freshness matching, plus `counts.major == 0`. Both `enforce-pr-gate.sh` and `pre-push` inherit it.

**4d — `R-SCORE-03d`: prompts and policies.**
Update [shared/agents/reviewer/prompt.md](../shared/agents/reviewer/prompt.md): after the verification pass converges, the reviewer emits the surviving findings as the JSON list and runs `record_findings.py` (or, where the reviewer lacks execute capability on a runtime, returns the JSON for the orchestrator to record — check `reviewer/agent.yaml` capabilities and write the instruction to match what the reviewer can actually do; the architecture review's R-AGENTS-01 lesson is that prompts must not command what capabilities forbid). Update [shared/policies/quality-and-testing.instructions.md](../shared/policies/quality-and-testing.instructions.md) (the rubric section describes both artifacts and the severity tiering) and [shared/policies/workflow.instructions.md](../shared/policies/workflow.instructions.md) (REVIEW stage now has a persisted deliverable; commit prerequisites list the findings report). Update the README's commit-gate and verification sections.

**4e — `R-SCORE-03e`: adversarial validator cases.**
Throwaway-repo cases alongside the existing commit-gate ones: valid score but no findings report → commit **blocked**; findings with `critical: 1` → commit **blocked** (message names the finding); `critical: 0, major: 2` → commit **allowed**, push **blocked**; all-zero counts → commit and push **allowed**; stale findings `content_hash` → **blocked**; two findings reports where the older is clean and the newer has a critical → the **newer** wins (blocked).

### Acceptance (whole phase)

Full regenerate + validate green; `docs/smoke-tests.md` gains the findings-gate expectations; a manual end-to-end on a throwaway consumer repo (the [plan-deterministic-commit-gate.md §7](plan-deterministic-commit-gate.md) procedure, extended) shows: review-clean commit passes, injected CRITICAL blocks at commit via **both** a gated-agent path and a bare human `git commit`, injected MAJOR blocks only at push.

---

## 6. Phase 5 — `R-VALID-02`: docs-and-surface parity checks

### Issue

The architecture review's Fault line 3 was semantic drift across copies, and §0 caught this document class drifting *during the review itself* (a stale agent count). The upstream's answer after three drift incidents was mechanical parity scripts (`check-surface-sync.py`, `check-skill-integrity.py`); armory validates manifest-vs-package sync in CI. This repo's README enumerates agents, skills, hook scripts, and policies by name with relative links — every list a future rename can silently invalidate — and `validate_targets.py` (now CI-run after Phase 2) is the natural home for the checks, but currently asserts generated-output properties, not authoring-doc parity.

### Fix

Add a `validate_docs_parity` section to [scripts/validate_targets.py](../scripts/validate_targets.py):

1. **Link integrity:** every relative markdown link in `README.md`, `AGENTS.md`, and `docs/*.md` resolves to an existing file or directory in the repo. (Skip `dist/` links when `dist/` is absent — or regenerate first, which the validator's callers already do; note the assumption in the check.)
2. **Named-inventory parity:** every `shared/skills/<name>/` referenced by name in README exists, and vice-versa is *not* required (README lists "most important", not all — assert the subset relation only). Same for the agent names in the README "Current agents" list vs `shared/agents/*/` (this one **is** exact: list == disk), and the hook script names in `docs/runtime-checks.md` vs `shared/hooks/scripts/*.sh` (exact).
3. **Skill frontmatter integrity:** every `shared/skills/*/SKILL.md` has `visibility: public|background` and a non-empty `description`; no two skills share an identical description (duplicate descriptions break description-match loading of background skills).
4. Prefer structural assertions over exact sentences, per the already-implemented R-VALID-01 lesson.

**Recorded future direction (not in this plan's scope):** armory-style per-skill trigger evals (positive/negative `cases.yaml` asserting a skill loads for matching prompts and not for near-misses). Valuable, but it needs an LLM-in-the-loop harness this repo doesn't have; revisit when one exists.

### Acceptance

- Break a README link locally → validator FAILs naming file and link; restore → PASS.
- Rename a skill directory without updating README → FAIL; revert → PASS.
- Full regenerate + validate green on both CI OSes.

---

## 7. Phase 6 — `R-DOCS-02`: record the multi-target trade-off as a decision

### Issue

§3.3 of the architecture review asked for the lowest-common-denominator consequence of the multi-target design — forgoing Claude Code's native plugin packaging because Copilot and Codex have no equivalent — to be "a recorded decision, revisited annually, not an inheritance." Nothing in `docs/` records it. Meanwhile armory demonstrates the choice is not binary: one source tree, generated adapters for other platforms, *and* plugin-marketplace packaging on the Claude side.

### Fix

Create `docs/adr-001-multi-target-lcd.md` (title: "ADR-001: Multi-target bootstrap over native per-platform packaging"), ~1 page:

- **Decision:** one shared `.claude/` basis + thin native adapters for Copilot/Claude/Codex; no Claude plugin packaging for now.
- **Context:** what each platform offered as of 2026-07 (cite the review §3.3), what LCD costs (no plugin distribution, no marketplace updates, HF-sync machinery instead).
- **Consequences:** the HF-sync + devcontainer distribution model exists *because* of this decision.
- **Revisit trigger:** annually (next: 2027-07), or earlier if (a) Copilot/Codex ship a plugin-equivalent, or (b) a Claude-only consumer repo appears — in which case the recorded option is: add a **plugin-manifest adapter** as one more `generate_targets.py` output (a `plugin.json` + marketplace layout over the same `.claude/` payload), not a fork of the source tree. Sketch the option in two sentences; do **not** implement it in this plan.
- Link the ADR from README ("Customization Notes" section) and from `docs/architecture.md`.

### Acceptance

ADR exists, is linked from both places, states the revisit date, and Phase 5's link-integrity check covers the new links. No generated-output change.

---

## 8. Phase 7 — `R-MCP-01` (optional): current-docs MCP server

### Issue

Ultralight bundles the Context7 MCP server so its coder cites current library documentation instead of stale training data. This repo's stack (Haystack, BentoML, Hydra, Gradio — all fast-moving APIs) is exactly the case where training-data memories go stale, and the repo already has the wiring pattern: [shared/mcp/servers.json](../shared/mcp/servers.json) renders into all three targets' MCP configs, and the devcontainer pre-installs Node 22 (so `npx` is available), with warn-don't-fail semantics for optional helpers.

### Fix

1. Add to `shared/mcp/servers.json`:

   ```json
   "context7": { "command": "npx", "args": ["-y", "@upstash/context7-mcp"] }
   ```

2. Regenerate; confirm all three MCP surfaces (`.vscode/mcp.json`, `.mcp.json`, `[mcp_servers.context7]` in `.codex/config.toml`) carry it. Check how the generator renders `servers.json` per target before assuming — read the rendering code first.
3. Add one routing line to [shared/policies/tool-routing.instructions.md](../shared/policies/tool-routing.instructions.md) (the single authoritative home for retrieval routing): use context7 for *current external library API documentation*; Semble stays for repo code, `rg` for literals, context-mode for long outputs. Do not restate the table anywhere else.
4. `docs/runtime-checks.md`: add context7 to the optional-helpers list (missing binary → WARN, not FAIL — verify `check_runtime.py` treats it that way if it enumerates helpers explicitly).

### Acceptance

Regenerate + validate green; `check_runtime.py` reports context7 as optional; smoke-tests doc's MCP Routing section lists it. If the validator asserts exact MCP server sets anywhere, update those assertions in the same commit.

---

## 9. Sources

**This repo (primary anchors):**

- [docs/architecture-review-2026-07.md](architecture-review-2026-07.md) — §3.2 (upstream lessons), §3.3 (platform capabilities + LCD trade), §3.5 (bypass-incentive loop), §5 R-SCORE-01(d) (deferred severity-predicate direction), §6 (plan-clustering conventions this plan mimics).
- [docs/plan-deterministic-commit-gate.md](plan-deterministic-commit-gate.md) — D1–D5 design decisions; D3 single-homing pattern (`assert_commit_invariants`); D4-B branch scoping; §5 accepted residuals.
- [shared/hooks/git-hooks/commit-msg](../shared/hooks/git-hooks/commit-msg), [shared/hooks/scripts/_lib-frontmatter.sh](../shared/hooks/scripts/_lib-frontmatter.sh), [shared/hooks/scripts/enforce-pr-gate.sh](../shared/hooks/scripts/enforce-pr-gate.sh), [shared/scripts/quality_score.py](../shared/scripts/quality_score.py), [scripts/generate_targets.py](../scripts/generate_targets.py), [scripts/validate_targets.py](../scripts/validate_targets.py), [scripts/install_bootstrap.py](../scripts/install_bootstrap.py).

**External:**

- `githooks(5)` — https://git-scm.com/docs/githooks — authority for: `commit-msg` invoked by `git-commit` **and** `git-merge` (Phase 1); `pre-push` stdin ref-line contract and `--no-verify` behavior (Phase 3); `rebase`/`cherry-pick` not invoking `commit-msg` (Phase 1 docs).
- https://github.com/pedrohcgs/claude-code-my-workflow — upstream inspiration: version-controlled git pre-commit hook as the only hard gate with an explicit escape (`SKIP_QUALITY_GATE=1`); severity predicate replacing the 0–100 score (`CRITICAL>0 → BLOCK, MAJOR>0 → REVISE`); hallucination gate (findings must survive re-verification); drift-policing scripts after repeated doc drift (Phases 2, 4, 5).
- https://github.com/Mathews-Tom/armory — per-package eval cases validated in CI; severity-tiered pre-merge gates (block CRITICAL); manifest-sync validation; single-source definitions with generated multi-platform adapters; Claude plugin-marketplace packaging alongside adapters (Phases 2, 4, 5, 6).
- https://burkeholland.github.io/ultralight/ — Context7 MCP bundling so the coder reads current library docs; deliberate minimalism as the contrast case (Phase 7).
- https://github.com/astral-sh/setup-uv — CI uv installation action (Phase 2).
- https://github.com/upstash/context7 — the context7 MCP server package (Phase 7).

---

## 10. Suggested order and dependency graph

```text
Phase 1 (R-HOOKS-08, bug fix)  ──►  merge before/with the deterministic-commit-gate branch
Phase 2 (R-CI-01)              ──►  independent; do early — every later phase's validator cases gain CI protection
Phase 3 (R-HOOKS-09)           ──►  depends on nothing; Phase 4c depends on it
Phase 4 (R-SCORE-03 a→e)       ──►  4c depends on Phase 3; the rest only on each other in order
Phase 5 (R-VALID-02)           ──►  after 1–4 so the new docs/links are in place to validate
Phase 6 (R-DOCS-02)            ──►  independent; any time
Phase 7 (R-MCP-01)             ──►  optional; any time
```

Per repo convention, run this plan through the normal lifecycle: a big plan referencing these phases as small plans, one commit per phase (sub-commits for 4a–4e), each leaving `generate_targets.py --all && validate_targets.py` green and `dist/` drift-free.
