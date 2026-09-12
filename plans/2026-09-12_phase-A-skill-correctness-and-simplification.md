---
name: 2026-09-12_phase-A-skill-correctness-and-simplification
type: small-plan
parent_plan: 2026-09-12_skill-library-hardening
phase_index: 1
status: planned
closeout_session_log:
---
# Small Plan: 2026-09-12_phase-A-skill-correctness-and-simplification

## Scope

Correct and simplify the existing shared skill library without changing the bootstrap's core lifecycle architecture. This phase fixes confirmed factual/security/workflow defects first, then cleans up routing, stale ownership/path assumptions, excessive ceremony, and reference-heavy roots where those changes improve all primary targets: Codex, Claude, Gemini/Antigravity, and GitHub Copilot.

This phase also fixes `shared/templates/plan-small.md`, whose numeric-score closeout instructions are stale relative to the current deterministic PASS/FAIL workflow. Generated targets must be regenerated from canonical sources; do not hand-edit generated copies.

## Steps

- [ ] **Fix confirmed correctness and safety defects.**
  - Modify `shared/skills/pandas-nan-bool-coercion/SKILL.md`.
    - Correct the false claim that `np.bool_` is a Python `bool`.
    - Keep the useful NaN/boolean coercion guidance, but make examples executable and internally consistent.
  - Modify `shared/skills/text-to-sql-safety/SKILL.md`.
    - Remove the claim that SQLite `mode=ro` is OS-enforced or cannot be bypassed by an application bug.
    - Describe it as one connection-level defense.
    - Prefer a parser/AST or SQLite authorizer approach where applicable, plus allowlists and bounded execution/resource controls.
    - Keep filesystem permissions as a separate stronger boundary when deployment permits them.
    - Do not present regex/string inspection as a complete SQL security boundary.
  - Modify `shared/skills/pyvis-xss-testing/SKILL.md`.
    - Stop treating absence of raw `<script>` text in serialized HTML as proof of XSS safety.
    - Require testing the actual rendered sink/browser behavior or the exact escaping boundary being relied on.
  - Modify `shared/skills/haystack-conditional-router/SKILL.md`.
    - Correct the `output_name` explanation: it names the router output socket, not the downstream component.
    - Qualify version-sensitive Haystack behavior.
  - Verify with focused content/unit tests and the repository's fast deterministic verifier.

- [ ] **Fix execution and lifecycle conflicts.**
  - Modify `shared/skills/run-tests/SKILL.md`.
    - Detect whether E2E/example scripts exist before executing them.
    - Never convert a real test failure into `"No E2E scripts"` or another success-looking message.
    - Run explicitly requested/focused tests before broad suites.
    - Delegate final breadth to canonical phase verification instead of prescribing repeated full-suite runs.
  - Modify `shared/skills/code-review/SKILL.md`.
    - Align severities with the canonical workflow: CRITICAL and MAJOR block; surviving MINOR is advisory only with explicit disposition and reason.
    - In lifecycle mode, return findings to the orchestrator; do not persist the final findings artifact from the reviewer.
    - Keep ad-hoc read-only review usable without lifecycle artifacts.
  - Modify `shared/skills/test-helper-public-api/SKILL.md`.
    - Remove the rule that a public production API should be added merely because a test lacks access.
    - Prefer observable public behavior or an existing seam; add a production seam only when it is a useful application abstraction.
  - Modify `shared/skills/caveman-compress/SKILL.md`.
    - Protect canonical authoring skill sources such as `shared/skills/**` as well as generated/native skill surfaces.
    - Preserve its opt-in compression role.
  - Verify with focused tests covering failure propagation, severity semantics, and protected path detection.

- [ ] **Fix stale paths and plan-template drift.**
  - Modify `shared/skills/create-feature/SKILL.md` and `shared/skills/setup-project/SKILL.md`.
    - Remove/update references to obsolete `.claude/instructions/workspace.md`.
    - Treat `.claude/instructions/project-context.instructions.md` as mutable project-specific context only when a durable project fact actually changes.
    - Do not make generated runtime paths canonical authoring sources.
  - Modify `shared/templates/plan-small.md`.
    - Remove `quality_score.py`, numeric score persistence, and `Score >= 90`.
    - Represent the current deterministic phase/closeout verification and severity contract.
    - Allow the current `planned` phase state required by the active workflow.
    - Keep pause/cancellation frontmatter consistent with `workflow.instructions.md`.
  - Review `shared/templates/plan-big.md` for the same current-state contract and change only if required.
  - Regenerate all targets with `scripts/generate_targets.py --all`; do not patch generated copies directly.
  - Run `scripts/validate_targets.py` and `scripts/check_runtime.py`.

- [ ] **Narrow automatic skill routing without weakening explicit workflow invocation.**
  - Modify `shared/skills/ponytail/SKILL.md`.
    - Remove public-description language equivalent to `"ANY coding task"`.
    - Make the semantic trigger about simplification/YAGNI requests or cases where unnecessary complexity is the relevant problem.
    - Preserve explicit invocation from the canonical coding workflow.
  - Modify `shared/skills/ponytail-review/SKILL.md`.
    - Remove public-description language equivalent to `"after every coding task"`.
    - Let reviewer routing decide when it is required.
    - Remove fake precision such as mandatory line-count reduction claims.
  - Review all other public skill descriptions for similarly broad automatic triggers.
    - Change only high-confidence over-broad descriptions.
    - Do not add a generic requirement that descriptions be short.
    - Do not make specialist skills harder to invoke by removing their actual task vocabulary.
  - Record any borderline semantic routing cases for Phase B/advisory deep-audit rather than inventing brittle hard lint.

- [ ] **Rewrite skills that currently impose one project architecture or excessive ceremony.**
  - Modify `shared/skills/create-feature/SKILL.md`.
    - Inspect the repository's architecture before selecting Hydra/config-first patterns.
    - If a Hydra-specific feature scaffold is valuable, either narrow the description/name or make Hydra conditional on existing project conventions.
  - Modify `shared/skills/setup-project/SKILL.md`.
    - Scaffold the requested project type minimally instead of imposing one universal directory layout.
    - Do not create a populated `.env` by default.
    - Avoid duplicate dependency declarations.
    - Explain any repository-initialization exception to the normal lifecycle rather than silently bypassing it.
  - Modify `shared/skills/integration-gate-spike/SKILL.md`.
    - Reframe it as a minimal external-contract/evidence spike.
    - Verify only unknown facts that materially affect implementation.
    - Remove mandatory feature flags, multi-provider abstractions, retries, caches, and other architecture unless evidence requires them.
  - Modify `shared/skills/debug-investigator/SKILL.md`.
    - Keep hypothesis-driven debugging but remove arbitrary requirements such as always producing 3-5 hypotheses.
    - Scale investigation depth to the uncertainty and failure surface.
  - Modify `shared/skills/refactor/SKILL.md`.
    - Use focused verification during implementation.
    - Avoid full coverage/full suite after every logical edit; canonical phase verification remains the final floor.
  - Modify BentoML/deployment/Gradio-Streamlit skills where they repeat canonical policy or impose project-specific defaults:
    - `shared/skills/bentoml-service/SKILL.md`
    - `shared/skills/deploy-service/SKILL.md`
    - `shared/skills/gradio-streamlit/SKILL.md`
    - Keep framework-specific knowledge, but make config/runtime/deployment choices conditional on the actual project and installed versions.

- [ ] **Apply progressive disclosure only where reference material dominates the root skill.**
  - Refactor these roots when doing so reduces irrelevant injected context without hiding required behavior:
    - `shared/skills/draw-io/SKILL.md`
    - `shared/skills/hydra-config/SKILL.md`
    - `shared/skills/md-to-pdf/SKILL.md`
    - `shared/skills/pdf/SKILL.md`
  - Keep the root `SKILL.md` as the trigger, main procedure, invariants, and routing index.
  - Move large recipe catalogs, XML/tool tricks, dependency/reference tables, or secondary workflows under local `references/` files.
  - Do not split a skill based on line count alone.
  - Update local links and generated target content accordingly.

- [ ] **Tighten learned/specialist skills where the audit found project-specific or version-sensitive claims.**
  - Modify as needed:
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
  - Move domain-specific case-study material to references when it is useful but not universally required.
  - Remove environment-specific benchmark/timing claims from universal guidance or mark them explicitly as observations.
  - For version-sensitive framework behavior, state tested/observed versions when available and require checking the installed API/docs when versions differ.
  - Keep compatibility/migration guidance bounded so temporary aliases/dual writes have a removal condition.

- [ ] **Simplify interaction-heavy and generic skills.**
  - Modify `shared/skills/concept-to-image/SKILL.md`, `shared/skills/html-presentation/SKILL.md`, and `shared/skills/literature-review/SKILL.md`.
    - Do not force confirmation/feedback rounds when reasonable defaults are available.
    - Ask only when a missing decision materially changes the result.
  - Modify `shared/skills/prompt-lab/SKILL.md`.
    - Remove prompts that request hidden chain-of-thought.
    - Prefer observable outputs, concise rationale/evidence, and empirical cross-model comparison.
  - Modify `shared/skills/onboard/SKILL.md`.
    - Replace unconditional `"read everything under docs/"` behavior with a small project index plus targeted retrieval.
    - Keep always-on project context small: purpose, important entry points, unusual constraints, authoritative pointers, and durable facts.
  - Remove or deprecate `shared/skills/data-analysis/` after confirming no required workflow references depend on it.
    - Generic pandas analysis knowledge does not justify automatic/shared skill context.
    - Do not remove project-specific analysis guidance from projects that actually need it.

- [ ] **Tighten remaining policy-duplication without unnecessary rewrites.**
  - Review and make small changes only where needed:
    - `shared/skills/add-dependency/SKILL.md`
    - `shared/skills/caveman/SKILL.md`
    - `shared/skills/code-style/SKILL.md`
    - `shared/skills/context-status/SKILL.md`
    - `shared/skills/documentation/SKILL.md`
    - `shared/skills/learn/SKILL.md`
  - Preserve skills that already have a good narrow contract unless a concrete conflict is found:
    - `commit`
    - `devils-advocate`
    - `humanize`
    - `plan-decomposition`
    - `research-critique`
    - `review-api`
    - `safe-consumer-bootstrap-refresh`
  - Do not churn these stable skills merely for stylistic consistency.

## Verification

Use focused tests while editing, then run the full authoring/runtime checks before closeout:

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run ruff check .
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run python .claude/scripts/verify.py phase --format json --persist
uv run python .claude/scripts/verify.py closeout --format json --persist
```

Verification must specifically demonstrate:

- failing E2E/example commands are not masked as absent scripts;
- current plan templates contain no numeric-score lifecycle;
- no live skill points authors to obsolete `workspace.md`;
- confirmed factual errors from the audit are corrected;
- CRITICAL/MAJOR/MINOR review behavior matches the canonical workflow;
- canonical `shared/**` sources regenerate target surfaces without drift.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved under canonical severity rules
- [ ] Documentation updated or explicitly marked not applicable with a reason
- [ ] LEARN entries saved or a no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] No generated target was hand-edited instead of its canonical `shared/**` source

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later. Set `status: paused`, record the required pause fields, and create a PAUSED session log. A checkpoint preserves incomplete work and does not complete or advance the phase.
