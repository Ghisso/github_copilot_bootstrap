# GitHub Copilot Workspace Instructions — Python AI Engineering

**Python:** 3.12+ | **Package Manager:** uv | **Frameworks:** Hydra · BentoML · Gradio (adapt as needed)

---

## Core Principles

- **Plan first** — for non-trivial tasks, produce a plan and save it to `.claude/plans/` before writing code
- **Verify after** — run pytest, mypy, ruff at the end of every task
- **Config-first design** — create dataclasses + ConfigStore before implementing features
- **Quality gates** — nothing ships below 90/100 (see `.github/instructions/quality-and-testing.instructions.md`)
- **Fix immediately** — no TODOs; fix issues as they arise, especially deprecation warnings
- **Test as you go** — write unit tests after each logical unit, E2E before completion
- **Retrieval-led reasoning** — search workspace before writing new code

> **Style enforcement:** ruff + mypy in `pyproject.toml` enforce style rules automatically.
> Zero ruff violations required before any commit.

---

## Instructions (`.github/instructions/` — always check these)

| File | Scope | Covers |
|---|---|---|
| `workflow.instructions.md` | Always-on | Plan-first, orchestrator loop, session logging |
| `code-standards.instructions.md` | `src/**`, `tests/**` | Naming, architecture, deprecation protocol |
| `quality-and-testing.instructions.md` | Always-on | Verification commands, score rubric, gates |
| `tool-routing.instructions.md` | Retrieval decisions | Semble, context-mode, grep, and direct file routing |
| `config-first-design.instructions.md` | `src/configs/**` | Pure ConfigStore design, no YAML files, dataclass patterns |
| `api-service-standards.instructions.md` | `service.py`, `src/api/**` | BentoML service patterns, Pydantic |
| `tests.instructions.md` | `tests/**` | Testing patterns, mocking, coverage |
| `deployment.instructions.md` | `service.py`, `bentofile.yaml` | Deployment, Docker, health checks |

---

## Workflow: Plan → Implement → Verify → Review → Score

```
PLAN → IMPLEMENT → VERIFY → REVIEW → FIX → SCORE
  ↑                                          |
  └─────── loop (max 5 rounds) ←─────────────┘
```

1. **Plan** — For ambiguous/large tasks: save plan to `.claude/plans/YYYY-MM-DD_description.md`
2. **Implement** — Config-first; test as you go
3. **Verify** — `uv run pytest tests/ -q` + mypy + ruff (see verification commands below)
4. **Review** — Run appropriate agents (see agents table)
5. **Score** — Must reach ≥ 80 before commit; ≥ 90 before PR

### Orchestrated Variant (for complex tasks)

Use the new orchestration agents for multi-file or ambiguous work:

`orchestrator` → `planner` → `coder`/`designer` → reviewers → `verifier`

- `planner` must read planning skills before building a plan.
- `coder` must load relevant skills (and planner-provided required skills) before editing.
- `designer` is specialized for Gradio/Streamlit UI work.

---

## Verification Commands

```bash
uv run pytest tests/ -q --tb=short
uv run mypy src/ --ignore-missing-imports --explicit-package-bases
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Quality scoring (combines all three):
uv run python .claude/scripts/quality_score.py src/
uv run python .claude/scripts/quality_score.py src/ --json        # machine-readable
uv run python .claude/scripts/quality_score.py src/ --skip-tests  # ruff + mypy only
```

---

## Agents (`.github/agents/`)

| Agent | When to use |
|---|---|
| `orchestrator` | Coordinate complex multi-agent implementation workflows |
| `planner` | Build implementation plans with ownership, risks, and required skills |
| `coder` | Implement planned code changes (invoked by orchestrator) |
| `designer` | Implement Gradio/Streamlit UI changes (invoked by orchestrator) |
| `review-pass-codex` | Internal reviewer pass used by `*-reviewer` agents for GPT-5.4 adversarial review |
| `review-pass-sonnet` | Internal reviewer pass used by `*-reviewer` agents for Claude Sonnet adversarial review |
| `code-reviewer` | After implementing new features |
| `security-reviewer` | Before any PR or deployment |
| `architecture-reviewer` | When adding new modules or refactoring |
| `test-reviewer` | After writing tests |
| `api-reviewer` | When adding/changing API endpoints |
| `config-reviewer` | When adding/changing configs |
| `performance-reviewer` | For I/O-heavy or ML inference paths |
| `documentation-reviewer` | Before releases |
| `domain-reviewer` | Domain-specific correctness checks |
| `code-simplifier` | After implementing, to clean up and simplify code |
| `verifier` | Final gate before commit/PR |

Reviewer behavior:

- All `*-reviewer` agents now run adversarial dual-pass reviews using:
  - `review-pass-codex` (GPT-5.4)
  - `review-pass-sonnet` (Claude Sonnet 4.6)
- Reviewers then synthesize both outputs into a single consolidated report.
- Shared findings are treated as high-confidence; model-unique findings are kept as disputed findings.

---

## Skills (`.claude/skills/` — load SKILL.md before proceeding)

Important for orchestration agents:

- `planner` must always load planning skills first (`plan-decomposition`, `iterative-plan-review`, and `create-feature` when applicable).
- `coder` must always load Tier 1 skills (`code-style`, `testing-patterns`) plus Tier 2 skills by task type before editing.
- Orchestrator owns the `--mode micro-plan` / `--mode full-plan` routing decision before delegating to `planner`.
- Retrieval helper selection is centralized in `.github/instructions/tool-routing.instructions.md`; keep Semble/context-mode guidance there and avoid duplicating long routing policy in skills or agent files.

**Skill visibility:** Skills marked `background` are auto-loaded by the model on description match but hidden from the `/` slash menu. Skills marked `public` appear in the slash menu.

| Trigger | Skill | Visibility | What it does |
|---|---|---|---|
| "commit" / "stage changes" | `commit` | public | Git workflow: stage, commit, PR, merge |
| "run tests" / "test this" | `run-tests` | public | Pytest orchestration with coverage |
| "review the code" | `code-review` | public | Multi-agent parallel review |
| "review the API" | `review-api` | public | API + security + test review |
| "add dependency" | `add-dependency` | public | uv add with validation |
| "refactor" | `refactor` | public | Safe refactoring with test gate |
| "create feature" | `create-feature` | public | Config-first scaffolding |
| "deploy" | `deploy-service` | public | BentoML/Docker deployment workflow |
| "setup project" | `setup-project` | public | Initialize new project from scaffold |
| "data analysis" | `data-analysis` | public | Load → explore → clean → analyze → report |
| "audit the repo" | `deep-audit` | public | Repository-wide consistency audit |
| "challenge this design" | `devils-advocate` | public | Structured critique before committing |
| "review the plan" | `iterative-plan-review` | background | Architecture review on plans (arch-reviewer only) |
| "I learned something" | `learn` | public | Extract discovery into reusable skill |
| "session status" | `context-status` | public | Show context health, plans, git status |
| "create BentoML service" / "deploy ML model" | `bentoml-service` | public | Production BentoML service with lifecycle, Pydantic, CORS |
| "code style" / "style review" | `code-style` | public | Python type hints, docstrings, logging, naming conventions |
| "integration tests" / "CSV tests" / "classifier tests" | `csv-driven-integration-tests` | public | CSV fixture datasets + pytest parametrize for classifiers/SQL |
| "classvar" / "constant field in dataclass" | `dataclass-classvar-constant` | background | Fix mutable instance fields that should be ClassVar constants |
| "docling" / "PDF with Haystack" | `docling-haystack` | background | Docling + Haystack PDF ingestion, OCR config, pipeline options |
| "write docs" / "add docstrings" | `documentation` | public | Google-style docstrings, README structure, docs/ layout |
| "gradio" / "streamlit" / "build UI" | `gradio-streamlit` | public | Gradio/Streamlit decision framework, lazy-loading, async wrapping |
| "conditional router" / "multi-branch pipeline" | `haystack-conditional-router` | background | Haystack ConditionalRouter wiring for semantic/SQL/hybrid pipelines |
| "hydra config" / "ConfigStore" | `hydra-config` | public | Pure ConfigStore, no YAML, config groups, runtime composition |
| "networkx" / "igraph" / "graphml" | `networkx-igraph-graphml-interop` | background | Fix edge_recall=0, opaque node IDs, GraphML export control chars |
| "ollama" / "OllamaChatGenerator" | `ollama-chat-generator` | background | Fix system prompt ignored, format=json ignored, warm_up() missing |
| "NaN" / "bool coercion" / "pandas dtype" | `pandas-nan-bool-coercion` | background | Fix silent NaN/bool coercion bugs in pandas DataFrames |
| "PDF" / "read PDF" / "extract text" | `pdf` | public | Read, merge, split, OCR, extract tables from PDFs |
| "Haystack pipeline" / "pipeline patterns" | `pipeline-patterns` | public | Haystack pipeline construction, component ordering, query inputs |
| "pyvis" / "XSS" / "HTML escaping test" | `pyvis-xss-testing` | background | Correctly assert HTML escaping in pyvis output (double-encoding) |
| "test helper" / "public API coverage" | `test-helper-public-api` | background | Prevent helpers bypassing public API and hiding bugs |
| "testing patterns" / "pytest patterns" | `testing-patterns` | background | scope: test case authoring, enumeration, and structure |
| "text-to-SQL" / "SQL safety" | `text-to-sql-safety` | public | Defense-in-depth safety layers for LLM-generated SQL execution |
| "context manager test" / "test __exit__" | `context-manager-testing` | background | Correctly test context manager cleanup (close, flush, etc.) |
| "metadata extraction" / "curated metadata" / "CSV extraction bottleneck" | `extraction-metadata-sourcing` | background | Separate in-text extraction from externally sourced curated metadata |
| "graph schema migration" / "entity_type" / "relation_type" | `graph-schema-compat-migration` | background | Migrate graph key names safely with dual-write and dual-read compatibility |
| "shared type" / "layer violation" / "cross-layer import" | `domain-type-placement` | background | Place shared types in src/domain/ to avoid layer coupling |
| "integration spike" / "unknown API contract" / "external contract validation" | `integration-gate-spike` | background | Gate uncertain external integrations before adapter implementation |
| "write a plan" / "break this down" / "phase plan" | `plan-decomposition` | public | Phased plans with overview + detail files per phase |
| "literature review" / "survey papers" / "research survey" | `literature-review` | public | Systematic academic literature review with screening + synthesis |
| "critique this paper" / "research critique" / "evaluate study" | `research-critique` | public | Anti-checklist analytical critique of research papers |
| "caveman mode" / "less tokens" / "be brief" / "be terse" | `caveman` | public | Ultra-terse technical communication mode with clarity exceptions |
| "compress memory file" / "shrink this markdown" / "/caveman:compress" | `caveman-compress` | public | Safely compress note-like natural-language files with backups and validation |
| "humanize" / "rewrite naturally" / "remove AI tone" | `humanize` | public | Detect and rewrite AI-sounding text into natural prose |
| "create presentation" / "HTML slides" / "slide deck" | `html-presentation` | public | Reveal.js presentations with scroll mode and 4 themes |
| "concept to image" / "create visual" / "make a diagram image" | `concept-to-image` | public | HTML/CSS/SVG visuals exported as PNG or SVG |
| "prompt engineering" / "prompt lab" / "optimize prompt" | `prompt-lab` | public | Systematic prompt design with variants, rubrics, and test cases |
| "audit RAG" / "RAG quality" / "retrieval evaluation" | `rag-auditor` | public | RAG pipeline evaluation: retrieval metrics + generation quality |
| "debug systematically" / "root cause analysis" / "bisect bug" | `debug-investigator` | public | Hypothesis-driven debugging with bisection and instrumentation |
| "markdown to PDF" / "convert md to pdf" / "export as PDF" | `md-to-pdf` | public | Markdown → styled PDF with Mermaid, KaTeX, and code highlighting |
| "retrieval routing" / "Semble" / "context-mode" | `retrieval-routing` | background | Thin pointer to `.github/instructions/tool-routing.instructions.md` |

---

## Quality Gates

| Score | Gate | Action |
|---|---|---|
| ≥ 95 | Excellence | Aspirational |
| ≥ 90 | PR-ready | Ready for review/deploy |
| ≥ 80 | Commit | Good enough to save |
| < 80 | Block | List blockers, do not commit |

---

## Project State

**Project:** [TODO: project name and one-liner description]
**Stack:** Python 3.12+ · uv · Hydra · BentoML · Haystack · Gradio
**Branch strategy:** main / feature branches

### Component Status

| Component | Status | Key Files |
|---|---|---|
[TODO: update this table as you build out the project; remove irrelevant rows, add new ones as needed]

### Active Work
<!-- Update when starting a new task -->
_No active plan. Check `.claude/plans/` for recent plans._
