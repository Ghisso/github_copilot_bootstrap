---
name: 2026-09-12_phase-B-skill-routing-and-provenance
type: small-plan
parent_plan: 2026-09-12_skill-library-hardening
phase_index: 2
status: planned
closeout_session_log:
---
# Small Plan: 2026-09-12_phase-B-skill-routing-and-provenance

## Scope

Correct the vendored Ponytail provenance record, resolve canonical-versus-
generated path confusion in skill guidance, and simplify skills that impose
one project architecture, excessive ceremony, or reference-heavy roots.

This is the judgment-heavy half of the content work. Phase A carried the
mechanical corrections. Changes here need a clear reason recorded per skill,
not stylistic churn.

`shared/skills/ponytail/SKILL.md` and `shared/skills/ponytail-review/SKILL.md`
are out of scope for content edits. They are hash-pinned vendored files whose
descriptions match canonical policy; see the big plan's
`## Decision: leave the vendored Ponytail pair unmodified`. This phase edits
their provenance record, not the skills themselves.

All edits go to canonical `shared/**` sources. Never hand-edit a generated
copy.

## Steps

- [ ] **Correct the Ponytail provenance record (evidence row 10).**
  - Modify `shared/third_party/ponytail/UPSTREAM.md`.
  - The file currently states that local changes are "limited to formatting,
    the bootstrap's required `visibility` frontmatter, and references to this
    bootstrap's review workflow". Measured against upstream `v4.8.4`, the real
    divergence is much larger:
    - `shared/skills/ponytail/SKILL.md` is 72 lines against upstream's 120,
      with the `## Output`, `## Intensity`, and `## When NOT to be lazy`
      sections dropped and `## Boundaries` renamed to `## Safety boundaries`;
    - `shared/skills/ponytail-review/SKILL.md` is 38 lines against 57.
  - Replace the understated sentence with an accurate description of the
    fork: which sections were dropped, that the descriptions were rewritten,
    and that the imported files are a reduced local adaptation rather than a
    faithful import.
  - Keep the release, commit, import date, and allowlist hashes as they are.
    This step changes prose only. The file hashes must not change, so
    `scripts/validate_targets.py` must still pass unmodified.
  - Update the `## Upgrade procedure` so it tells a future maintainer that a
    bump is a three-way merge against a local fork, not a file replacement.
  - Record the upstream survey result for the next maintainer: upstream
    `v4.9.0` (2026-08-08) changes exactly one bullet in the vendored surface
    (upstream commit `b6c0448`), and that change is already present locally at
    `shared/skills/ponytail/SKILL.md:51-52`. See the big plan's
    `## Decision: do not bump Ponytail to v4.9.0`.

- [ ] **Fix canonical-versus-generated path confusion (evidence row 11).**
  - `.claude/instructions/workspace.md` is not obsolete. It is emitted on
    every generation run by `scripts/generate_targets.py`, and it is required
    by `scripts/validate_targets.py` and `scripts/install_bootstrap.py`. Do
    not remove it, and do not add a validator rule that rejects it outright.
  - The real defect is narrower: skills point authors at that generated
    runtime copy as if it were an authoring source.
  - Modify `shared/skills/onboard/SKILL.md:91`,
    `shared/skills/setup-project/SKILL.md:39`, and
    `shared/skills/create-feature/SKILL.md:71` so authoring guidance points at
    the canonical source, while runtime reading guidance may still name the
    generated path.
  - Treat `.claude/instructions/project-context.instructions.md` as mutable
    project-specific context, updated only when a durable project fact
    actually changes.
  - Decide and record one canonical name for the policy surface. Both
    `.claude/instructions/workspace.md` and
    `.claude/instructions/workspace.instructions.md` are generated from
    `shared/policies/workspace.instructions.md` and are currently byte-
    identical, so either reference resolves. This is a naming-consistency
    choice, not a broken path.
  - If the decision is to prefer the `.instructions.md` name, update
    `shared/policies/workflow.instructions.md:251` to match, since canonical
    policy currently points at the shorter alias. Edit the canonical policy
    under `shared/policies/`, never the generated copy under
    `.claude/instructions/`.

- [ ] **Remove rigid project-architecture and ceremony assumptions (evidence row 12).**
  - Modify `shared/skills/create-feature/SKILL.md`.
    - Inspect the repository's actual architecture before selecting a
      Hydra-based config-first pattern.
    - If a Hydra-specific scaffold is worth keeping, either narrow the skill's
      name and description to say so, or make Hydra conditional on conventions
      already present in the repository.
  - Modify `shared/skills/setup-project/SKILL.md`.
    - Scaffold the requested project type minimally instead of imposing one
      universal directory layout.
    - Do not create a populated secret-bearing environment file by default.
      Generating a template with placeholder names is acceptable; writing
      real-looking values is not.
    - Avoid duplicate dependency declarations.
    - Explain any repository-initialization exception to the normal lifecycle
      rather than silently bypassing it.
  - Modify `shared/skills/integration-gate-spike/SKILL.md`.
    - Reframe it as a minimal external-contract evidence spike.
    - Verify only unknown facts that materially affect implementation.
    - Remove mandatory feature flags, multi-provider abstractions, retries,
      caches, and similar architecture unless the gathered evidence requires
      them.
  - Modify `shared/skills/debug-investigator/SKILL.md`.
    - Keep hypothesis-driven debugging, but remove fixed quotas such as always
      producing three to five hypotheses.
    - Scale investigation depth to the uncertainty and the failure surface.
  - Modify `shared/skills/refactor/SKILL.md`.
    - Use focused verification during implementation.
    - Do not require a full suite or full coverage run after every logical
      edit; canonical phase verification remains the final floor.
  - Modify `shared/skills/bentoml-service/SKILL.md`,
    `shared/skills/deploy-service/SKILL.md`, and
    `shared/skills/gradio-streamlit/SKILL.md` where they repeat canonical
    policy or hard-code project-specific defaults. Keep the framework-specific
    knowledge; make configuration, runtime, and deployment choices conditional
    on the actual project and the installed versions.

- [ ] **Narrow genuinely over-broad public descriptions.**
  - A public skill's description is always in context; its body loads on
    demand. The cost being managed here is the description block, so weigh
    each change against that, not against the skill's line count.
  - Review public descriptions for triggers that would cause Codex, Claude,
    Gemini, or Copilot to load a skill for unrelated work.
  - Change only high-confidence cases, and record the reason for each change.
  - Do not change a description whose breadth matches a mandate this
    repository actually states. The `ponytail` and `ponytail-review`
    descriptions are the worked example: `CLAUDE.md:30` requires `ponytail` in
    `full` mode before every coding task, and
    `shared/skills/ponytail/SKILL.md:24-25` makes the final Ponytail diff
    review mandatory, so "ANY coding task" and "after every coding task" are
    accurate. Verify the same way before narrowing any other description.
  - Do not add a general rule that descriptions must be short.
  - Do not make specialist skills harder to invoke by stripping the task
    vocabulary that routes to them.
  - Record borderline semantic routing cases for the Phase C advisory
    `deep-audit` checks rather than inventing brittle hard lint.

- [ ] **Apply progressive disclosure only where reference material dominates.**
  - Consider these roots, and refactor one only when doing so measurably
    reduces irrelevant injected context without hiding required behavior:
    - `shared/skills/draw-io/SKILL.md`
    - `shared/skills/hydra-config/SKILL.md`
    - `shared/skills/md-to-pdf/SKILL.md`
    - `shared/skills/pdf/SKILL.md`
  - Keep the root `SKILL.md` as the trigger, the main procedure, the
    invariants, and a routing index.
  - Move large recipe catalogs, tool-specific tricks, dependency tables, and
    secondary workflows into local `references/` files.
  - Do not split a skill based on line count alone.
  - Update local links and regenerate target content accordingly.

- [ ] **Tighten learned and specialist skills where claims are project-specific or version-sensitive.**
  - Review and modify as needed:
    - `shared/skills/csv-driven-integration-tests/SKILL.md`
    - `shared/skills/context-manager-testing/SKILL.md`
    - `shared/skills/dataclass-classvar-constant/SKILL.md`
    - `shared/skills/docling-haystack/SKILL.md`
    - `shared/skills/domain-type-placement/SKILL.md`
    - `shared/skills/extraction-metadata-sourcing/SKILL.md`
    - `shared/skills/graph-schema-compat-migration/SKILL.md`
    - `shared/skills/networkx-igraph-graphml-interop/SKILL.md`
    - `shared/skills/ollama-chat-generator/SKILL.md`
    - `shared/skills/pipeline-patterns/SKILL.md`
    - `shared/skills/rag-auditor/SKILL.md`
    - `shared/skills/testing-patterns/SKILL.md`
  - Move domain-specific case-study material to references when it is useful
    but not universally required.
  - Remove environment-specific benchmark and timing claims from universal
    guidance, or mark them explicitly as observations with their conditions.
  - For version-sensitive framework behavior, state the tested or observed
    version, and require checking the installed API when versions differ.
  - Keep compatibility and migration guidance bounded, so temporary aliases
    and dual writes carry a stated removal condition.

- [ ] **Simplify interaction-heavy and generic skills.**
  - Modify `shared/skills/concept-to-image/SKILL.md`,
    `shared/skills/html-presentation/SKILL.md`, and
    `shared/skills/literature-review/SKILL.md` so they do not force
    confirmation rounds when reasonable defaults exist. Ask only when a
    missing decision materially changes the result.
  - Modify `shared/skills/prompt-lab/SKILL.md` to remove prompts that request
    hidden chain-of-thought. Prefer observable outputs, concise rationale and
    evidence, and empirical cross-model comparison.
  - Modify `shared/skills/onboard/SKILL.md` to replace unconditional
    "read everything under docs/" behavior with a small project index plus
    targeted retrieval. Keep always-on project context small: purpose,
    important entry points, unusual constraints, authoritative pointers, and
    durable facts.
  - Retain `shared/skills/data-analysis/`. The original audit proposed
    removing it; that is dropped. It is a public, task-triggered skill, so its
    standing cost is a roughly four-line description block, not its 64-line
    body, and nothing outside its own `SKILL.md` references it. Simplify or
    narrow it only if a concrete routing or dependency problem is found, and
    record that problem if so.

- [ ] **Tighten remaining policy duplication without unnecessary rewrites.**
  - Review and make small changes only where a concrete conflict with
    canonical policy exists:
    - `shared/skills/add-dependency/SKILL.md`
    - `shared/skills/caveman/SKILL.md`
    - `shared/skills/code-style/SKILL.md`
    - `shared/skills/context-status/SKILL.md`
    - `shared/skills/documentation/SKILL.md`
    - `shared/skills/learn/SKILL.md`
  - Leave these alone unless a concrete conflict is found: `commit`,
    `devils-advocate`, `humanize`, `plan-decomposition`, `research-critique`,
    `review-api`, `safe-consumer-bootstrap-refresh`.
  - `shared/skills/humanize/SKILL.md` is additionally hash-pinned as vendored
    third-party content in `scripts/validate_targets.py`; do not edit it.
  - Do not churn stable skills for stylistic consistency.

- [ ] **Regenerate and validate.**
  - Run `uv run python scripts/generate_targets.py --all` after the canonical
    source edits, then run the validators against the regenerated tree.
  - Confirm the vendored Ponytail and `humanize` file hashes are unchanged.

## Verification

Generation runs before validation, so the validators inspect a current tree:

```bash
uv run python .claude/scripts/verify.py fast --format text     # during IMPLEMENT
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
uv run ruff format --check shared scripts tests
uv run python .claude/scripts/verify.py phase --format json --persist
uv run python .claude/scripts/verify.py closeout --format json --persist
```

Verification must specifically demonstrate:

- `UPSTREAM.md` describes the fork accurately and its recorded hashes still
  match the unmodified vendored files;
- no live skill presents a generated runtime path as an authoring source;
- `.claude/instructions/workspace.md` is still generated and still validates;
- every description change has a recorded reason, and no description was
  narrowed against a mandate the repository states;
- `data-analysis` is still present;
- canonical `shared/**` sources regenerate target surfaces without drift.

## Closeout Checklist

- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] No generated target was hand-edited instead of its canonical `shared/**` source
- [ ] Vendored Ponytail and `humanize` files unchanged and pinned hashes still match
- [ ] Borderline routing cases recorded for the Phase C advisory checks

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume
later. Set `status: paused`, record the three pause fields, and create a
session log with `**Status:** PAUSED`. A checkpoint preserves incomplete work
and does not complete or advance the phase.
