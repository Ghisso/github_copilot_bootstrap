---
name: 2026-09-24_phase-B-sidecar-profile-and-ownership
type: small-plan
parent_plan: consumer-sidecar-bootstrap-overlay
phase_index: 2
status: planned
closeout_session_log:
---

# Small Plan: Phase B — Sidecar Profile and Ownership

## Scope

Generate `dist/sidecar/`, validate that it is self-contained and carries its
license notices, and build the pure reconciliation planner with its tests.
This phase changes no consumer repository and no installer CLI. Path
constants come from the Phase A matrix.

### Required Skills

- `shared/skills/ponytail/SKILL.md` — `full`
- `shared/skills/code-style/SKILL.md`
- `shared/skills/testing-patterns/SKILL.md`

## Primary Files

- `scripts/runtime_ownership.py` — sidecar constants and `FULL_INSTALL_ROOT_PATHS`.
- `scripts/generate_targets.py` — the `"sidecar"` target and `SIDECAR_TEXT_REPLACEMENTS`.
- `shared/sidecar/bridge.md` — new; the one bridge body.
- `scripts/validate_targets.py` — sidecar checks, with adversarial cases in
  its existing self-test style.
- `scripts/sidecar_overlay.py` — new; pure planner functions only.
- `tests/test_sidecar_overlay.py` — new.

Do not hand-edit `dist/`.

## Steps

- [ ] **1. Add the sidecar constants.**
  - **Owner:** `coder`
  - In `scripts/runtime_ownership.py`, add `SIDECAR_SKILLS`, the write roots
    and the read roots frozen in Phase A, the bridge paths, the manifest file
    name `ai-bootstrap-sidecar.json`, the staging folder name
    `ai-bootstrap-sidecar-staging`, and the exclude-block markers
    `# BEGIN ai-bootstrap sidecar` and `# END ai-bootstrap sidecar`.
  - Add `FULL_INSTALL_ROOT_PATHS = (".claude", ".devcontainer") + RESTORABLE_ROOT_PATHS`
    for the unbootstrapped team-config check (big plan, Decision 18). Do not
    keep a second list by hand.
  - Do not add a mode class. Phase C adds one mode-detection function.

- [ ] **2. Add the `sidecar` generator target.**
  - **Owner:** `coder`
  - Add `"sidecar"` to `TARGETS` and a `render_sidecar()` branch in
    `generate()`, so `--all` renders `dist/sidecar/`. `TARGETS` alone only
    feeds argparse `choices` and `--all`; `generate()` raises `ValueError`
    for any other target.
  - Copy each allowlisted skill folder with the existing `copy_tree` helper
    into `.claude/skills/` and `.agents/skills/`, then apply
    `SIDECAR_TEXT_REPLACEMENTS`, a new constant beside
    `TARGET_PATH_REPLACEMENTS`. Keep `TARGET_PATH_REPLACEMENTS` keyed by
    client names only. None of the four skills contains a `claude-code`
    replacement string, so both roots get the same text.
  - The replacements remove the known bootstrap references with
    repository-neutral wording:
    - `humanize`: replace the `../../third_party/avoid-ai-writing/` snapshot
      path with a plain credit, `avoid-ai-writing v3.25.0` by Conor Bronsdon
      (MIT);
    - `ponytail`: replace "the workflow's final Ponytail diff review remains
      mandatory" with a sentence that asks for `ponytail-review` on
      non-trivial diffs;
    - `ponytail-review`: replace "Return findings to the coder" with a
      sentence that returns the findings to whoever changes the diff.
  - Copy `shared/third_party/ponytail/LICENSE` as `LICENSE` into `ponytail/`
    and `ponytail-review/` at both roots (big plan, Decision 19).
  - Render each proven bridge from `shared/sidecar/bridge.md`, adding only
    its client's frontmatter: none for Claude Code, `applyTo: "**"` for
    Copilot, and `trigger: always_on` for Antigravity.
  - `dist/multi-agent/` output must not change.

- [ ] **3. Write the bridge body.**
  - **Owner:** `coder`
  - `shared/sidecar/bridge.md` contains exactly two rules:
    - Repository-provided tracked instructions and conventions are
      authoritative. This personal sidecar augments them. If sidecar guidance
      conflicts with repository guidance, follow the repository.
    - Apply the `ponytail` skill in `full` mode to coding tasks unless
      repository guidance says otherwise, and use `ponytail-review` on
      non-trivial diffs.

- [ ] **4. Validate the sidecar target.**
  - **Owner:** `coder`
  - `validate_targets.py` rejects, in `dist/sidecar/`:
    - any path outside the allowlisted skill folders, their `LICENSE` files,
      and the proven bridges;
    - any file that names a path the sidecar does not install:
      `.claude/instructions/`, `.claude/scripts/`, `.claude/agents/`,
      `.claude/hooks/`, `.claude/review-profiles/`, `third_party/`,
      `verify.py`, or `record_findings`;
    - any MCP tool reference (`mcp__`, `ctx_`);
    - any phrase listed in `SIDECAR_TEXT_REPLACEMENTS`, so a replacement that
      stops matching after a source edit fails validation instead of
      shipping silently;
    - a `ponytail/` or `ponytail-review/` folder whose `LICENSE` is missing
      or differs from `shared/third_party/ponytail/LICENSE`, or a `humanize`
      skill without the credit line;
    - a bridge without its client's frontmatter;
    - output that differs between two generations.
  - It also rejects any file under `dist/multi-agent/` that no entry of
    `FULL_INSTALL_ROOT_PATHS` covers, so the team-config list cannot fall
    behind the full target.
  - Add an adversarial case for each rejection, and prove each one fails
    when its rule is removed.

- [ ] **5. Build the pure planner.**
  - **Owner:** `coder`
  - In `scripts/sidecar_overlay.py`, add functions for manifest parsing and
    schema validation, per-file and per-unit hashing, classification, and
    exclude-line rendering: one anchored line per unit, and one escaped
    exact-path line per `retained` file (big plan, Decision 17). They return
    actions, reports, and aborts.
  - The manifest schema holds `schema_version`, one record per unit with its
    per-file SHA-256 hashes, `retained` entries, and a diagnostic
    `bootstrap_commit`. No timestamps and no pending flags (big plan,
    Decision 10).
  - Inputs are data: the desired units read from `dist/sidecar/`, the parsed
    manifest, the unit lines currently in the sidecar's exclude block, the
    skill names found in each read-only folder of the read list, and a
    per-unit snapshot. The snapshot records whether the unit exists, whether
    it or an ancestor is a symlink, its tracked files, its per-file hashes,
    and which of its untracked files are currently ignored. Git queries
    happen in the caller.
  - Implement the big plan's preflight rules, the classification table, and
    the skill-level anti-shadowing rule across the read list exactly. That
    includes team takeover only for a recorded unit, team-owned without a
    record, and adoption only for a unit that the exclude block lists.
    Planner functions never write to disk.

- [ ] **6. Add failing-first planner tests.**
  - **Owner:** `coder`
  - In `tests/test_sidecar_overlay.py`, add one case per classification row,
    plus:
    - manifest path outside the namespace, absolute, or containing `..` -> abort;
    - manifest with invalid JSON or schema, or an unknown `schema_version` -> abort;
    - symlinked unit, or symlinked ancestor directory -> abort;
    - skill taken at one write root -> skipped at both write roots, and an
      unchanged sidecar copy at the other root is removed;
    - skill name found only in a read-only folder such as `.github/skills/`
      -> skipped at both write roots;
    - untracked copy equal to the desired bytes and listed in the exclude
      block -> adopted;
    - untracked copy equal to the desired bytes but not listed in the exclude
      block -> foreign, and no line is planned;
    - recorded unit whose bytes already equal the new desired content (an
      interrupted update) -> adopted with the new record;
    - team tracks one file of a recorded sidecar skill folder -> matching
      untracked files deleted, a hidden user-added file kept as `retained`
      with its own line;
    - team tracks a skill folder that the manifest does not record ->
      team-owned, no line, no `retained` entry;
    - a `retained` file later deleted or tracked -> entry and line dropped;
    - exact-path lines for names containing `\`, `*`, `?`, `[`, a leading `!`
      or `#`, a trailing space, or non-ASCII characters -> escaped as
      Decision 17 requires;
    - applying a plan and planning again -> no actions.
  - Every test must fail when the rule it covers is removed.

## Acceptance Criteria

- `dist/sidecar/` is deterministic and contains only allowlisted units, their
  license files, and proven bridges.
- `validate_targets.py` rejects every listed bootstrap-only reference, and a
  missing license or credit line.
- `dist/multi-agent/` output is unchanged.
- The planner covers every classification row, never adopts a unit that the
  exclude block does not list, and performs no writes.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/test_sidecar_overlay.py tests/test_validate_targets.py -q --tb=short
uv run pytest tests/test_install_bootstrap.py -q --tb=short
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- `diff -r` between `dist/multi-agent/` generated from `dev` and from this branch shows no difference.

## Review Profiles

- `code`
- `architecture`
- `security`
- `tests`
- `ponytail`

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
