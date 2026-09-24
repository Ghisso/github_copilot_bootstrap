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

Generate `dist/sidecar/`, validate that it is self-contained, and build the
pure reconciliation planner with its tests. This phase changes no consumer
repository and no installer CLI. Path constants come from the Phase A matrix.

### Required Skills

- `shared/skills/ponytail/SKILL.md` — `full`
- `shared/skills/code-style/SKILL.md`
- `shared/skills/testing-patterns/SKILL.md`

## Primary Files

- `scripts/runtime_ownership.py` — sidecar constants.
- `scripts/generate_targets.py` — the `"sidecar"` target.
- `shared/sidecar/bridge.md` — new; the one bridge body.
- `scripts/validate_targets.py` — sidecar checks, with adversarial cases in
  its existing self-test style.
- `scripts/sidecar_overlay.py` — new; pure planner functions only.
- `tests/test_sidecar_overlay.py` — new.

Do not hand-edit `dist/`.

## Steps

- [ ] **1. Add the sidecar constants.**
  - **Owner:** `coder`
  - In `scripts/runtime_ownership.py`, add `SIDECAR_SKILLS`, the skill roots,
    the bridge paths frozen in Phase A, the manifest file name
    `ai-bootstrap-sidecar.json`, and the exclude-block markers
    `# BEGIN ai-bootstrap sidecar` and `# END ai-bootstrap sidecar`.
  - Do not add a mode class. Phase C adds one mode-detection function.
  - The unbootstrapped team-config check (big plan, Decision 18) reuses the
    existing `RESTORABLE_ROOT_PATHS` plus `.claude`; do not add a second list.

- [ ] **2. Add the `sidecar` generator target.**
  - **Owner:** `coder`
  - Add `"sidecar"` to `TARGETS` and a `render_sidecar()` branch in
    `generate()`, so `--all` renders `dist/sidecar/`. `TARGETS` alone only
    feeds argparse `choices`; `generate()` raises `ValueError` for any other
    target.
  - Render only the allowlisted skills into `.claude/skills/` and
    `.agents/skills/`, with the same copy helpers the full target uses, plus
    a `"sidecar"` entry in `TARGET_PATH_REPLACEMENTS`.
  - The replacements remove the known bootstrap references: the `humanize`
    citation of `../../third_party/avoid-ai-writing/`, the `ponytail` sentence
    "the workflow's final Ponytail diff review remains mandatory", and the
    `ponytail-review` sentence "Return findings to the coder". Use
    repository-neutral wording.
  - Render each proven bridge from `shared/sidecar/bridge.md`, adding only
    the frontmatter its client needs (Copilot: `applyTo: "**"`).
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
    - any path outside the allowlisted skills and proven bridges;
    - any file that names a path the sidecar does not install:
      `.claude/instructions/`, `.claude/scripts/`, `.claude/agents/`,
      `.claude/hooks/`, `.claude/review-profiles/`, `third_party/`,
      `verify.py`, or `record_findings`;
    - any MCP tool reference (`mcp__`, `ctx_`);
    - any of the three replaced phrases from step 2, so a replacement that
      stops matching after a source edit fails validation instead of
      shipping silently;
    - output that differs between two generations.
  - Add an adversarial case for each rejection, and prove each one fails
    when its rule is removed.

- [ ] **5. Build the pure planner.**
  - **Owner:** `coder`
  - In `scripts/sidecar_overlay.py`, add functions for manifest parsing and
    schema validation, per-file and per-unit hashing, and classification.
    They return actions, reports, and aborts.
  - The manifest schema holds `schema_version`, one record per unit with its
    per-file SHA-256 hashes and an optional `pending` flag, `retained`
    entries, and a diagnostic `bootstrap_commit`. No timestamps.
  - Inputs are data: desired units read from `dist/sidecar/`, the parsed
    manifest, and a per-unit snapshot (exists, symlink, symlinked ancestor,
    tracked files, per-file hashes). Git queries happen in the caller.
  - Implement the big plan's preflight rules, the classification table
    (including `pending` and team takeover with `retained` files), and the
    skill-level anti-shadowing rule exactly. Planner functions never write
    to disk.

- [ ] **6. Add failing-first planner tests.**
  - **Owner:** `coder`
  - In `tests/test_sidecar_overlay.py`, add one case per classification row,
    plus:
    - manifest path outside the namespace, absolute, or containing `..` -> abort;
    - manifest with invalid JSON or schema, or an unknown `schema_version` -> abort;
    - symlinked unit, or symlinked ancestor directory -> abort;
    - skill taken at one root -> skipped at both roots, and an unchanged
      sidecar copy at the other root is removed;
    - an untracked path matching the desired bytes -> adopted;
    - a `pending` unit with partial content and no earlier record -> finished;
    - team tracks one file of a sidecar skill directory -> matching untracked
      files deleted, a user-added file kept as `retained` with its own line;
    - a `retained` file later deleted or tracked -> entry and line dropped;
    - applying a plan and planning again -> no actions.
  - Every test must fail when the rule it covers is removed.

## Acceptance Criteria

- `dist/sidecar/` is deterministic and contains only allowlisted units.
- `validate_targets.py` rejects every listed bootstrap-only reference.
- `dist/multi-agent/` output is unchanged.
- The planner covers every classification row and performs no writes.

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
