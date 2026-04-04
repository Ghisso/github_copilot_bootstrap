# GitHub Copilot Workspace Instructions — Python AI Engineering

**Python:** 3.12+ | **Package Manager:** uv | **Frameworks:** Hydra · BentoML · Gradio (adapt as needed)

---

## Core Principles

- **Plan first** — for non-trivial tasks, produce a plan and save it to `.github/plans/` before writing code
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
| `configs.instructions.md` | `src/configs/**` | Pure ConfigStore design, no YAML files |
| `config-first-design.instructions.md` | `src/configs/**` | Dataclass + ConfigStore patterns, anti-patterns, checklist |
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

1. **Plan** — For ambiguous/large tasks: save plan to `.github/plans/YYYY-MM-DD_description.md`
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
python .github/scripts/quality_score.py src/
python .github/scripts/quality_score.py src/ --json        # machine-readable
python .github/scripts/quality_score.py src/ --skip-tests  # ruff + mypy only
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

## Skills (`.github/skills/` — load SKILL.md before proceeding)

Important for orchestration agents:

- `planner` must always load planning skills first (`plan-decomposition`, `iterative-plan-review`, and `create-feature` when applicable).
- `coder` must always scan available skills and load relevant SKILL.md files before implementation, plus all planner-requested skills.

| Trigger | Skill | What it does |
|---|---|---|
| "commit" / "stage changes" | `commit` | Git workflow: stage, commit, PR, merge |
| "run tests" / "test this" | `run-tests` | Pytest orchestration with coverage |
| "review the code" | `code-review` | Multi-agent parallel review |
| "review the API" | `review-api` | API + security + test review |
| "add dependency" | `add-dependency` | uv add with validation |
| "refactor" | `refactor` | Safe refactoring with test gate |
| "create feature" | `create-feature` | Config-first scaffolding |
| "deploy" | `deploy-service` | BentoML/Docker deployment workflow |
| "setup project" | `setup-project` | Initialize new project from scaffold |
| "data analysis" | `data-analysis` | Load → explore → clean → analyze → report |
| "audit the repo" | `deep-audit` | Repository-wide consistency audit |
| "challenge this design" | `devils-advocate` | Structured critique before committing |
| "review the plan" | `iterative-plan-review` | Architecture + code review on plans |
| "I learned something" | `learn` | Extract discovery into reusable skill |
| "session status" | `context-status` | Show context health, plans, git status |
| "create BentoML service" / "deploy ML model" | `bentoml-service` | Production BentoML service with lifecycle, Pydantic, CORS |
| "code style" / "style review" | `code-style` | Python type hints, docstrings, logging, naming conventions |
| "integration tests" / "CSV tests" / "classifier tests" | `csv-driven-integration-tests` | CSV fixture datasets + pytest parametrize for classifiers/SQL |
| "classvar" / "constant field in dataclass" | `dataclass-classvar-constant` | Fix mutable instance fields that should be ClassVar constants |
| "docling" / "PDF with Haystack" | `docling-haystack` | Docling + Haystack PDF ingestion, OCR config, pipeline options |
| "write docs" / "add docstrings" | `documentation` | Google-style docstrings, README structure, docs/ layout |
| "gradio" / "streamlit" / "build UI" | `gradio-streamlit` | Gradio/Streamlit decision framework, lazy-loading, async wrapping |
| "conditional router" / "multi-branch pipeline" | `haystack-conditional-router` | Haystack ConditionalRouter wiring for semantic/SQL/hybrid pipelines |
| "hydra config" / "ConfigStore" | `hydra-config` | Pure ConfigStore, no YAML, config groups, runtime composition |
| "networkx" / "igraph" / "graphml" | `networkx-igraph-graphml-interop` | Fix edge_recall=0, opaque node IDs, GraphML export control chars |
| "ollama" / "OllamaChatGenerator" | `ollama-chat-generator` | Fix system prompt ignored, format=json ignored, warm_up() missing |
| "NaN" / "bool coercion" / "pandas dtype" | `pandas-nan-bool-coercion` | Fix silent NaN/bool coercion bugs in pandas DataFrames |
| "PDF" / "read PDF" / "extract text" | `pdf` | Read, merge, split, OCR, extract tables from PDFs |
| "Haystack pipeline" / "pipeline patterns" | `pipeline-patterns` | Haystack pipeline construction, component ordering, query inputs |
| "pyvis" / "XSS" / "HTML escaping test" | `pyvis-xss-testing` | Correctly assert HTML escaping in pyvis output (double-encoding) |
| "test helper" / "public API coverage" | `test-helper-public-api` | Prevent helpers bypassing public API and hiding bugs |
| "testing patterns" / "pytest patterns" | `testing-patterns` | Async tests, mocking, parametrize, Hydra config testing, coverage |
| "text-to-SQL" / "SQL safety" | `text-to-sql-safety` | Defense-in-depth safety layers for LLM-generated SQL execution |
| "context manager test" / "test __exit__" | `context-manager-testing` | Correctly test context manager cleanup (close, flush, etc.) |
| "metadata extraction" / "curated metadata" / "CSV extraction bottleneck" | `extraction-metadata-sourcing` | Separate in-text extraction from externally sourced curated metadata |
| "graph schema migration" / "entity_type" / "relation_type" | `graph-schema-compat-migration` | Migrate graph key names safely with dual-write and dual-read compatibility |
| "shared type" / "layer violation" / "cross-layer import" | `domain-type-placement` | Place shared types in src/domain/ to avoid layer coupling |
| "integration spike" / "unknown API contract" / "external contract validation" | `integration-gate-spike` | Gate uncertain external integrations before adapter implementation |
| "write a plan" / "break this down" / "phase plan" | `plan-decomposition` | Phased plans with overview + detail files per phase |
| "literature review" / "survey papers" / "research survey" | `literature-review` | Systematic academic literature review with screening + synthesis |
| "critique this paper" / "research critique" / "evaluate study" | `research-critique` | Anti-checklist analytical critique of research papers |
| "humanize" / "rewrite naturally" / "remove AI tone" | `humanize` | Detect and rewrite AI-sounding text into natural prose |
| "create presentation" / "HTML slides" / "slide deck" | `html-presentation` | Reveal.js presentations with scroll mode and 4 themes |
| "concept to image" / "create visual" / "make a diagram image" | `concept-to-image` | HTML/CSS/SVG visuals exported as PNG or SVG |
| "prompt engineering" / "prompt lab" / "optimize prompt" | `prompt-lab` | Systematic prompt design with variants, rubrics, and test cases |
| "audit RAG" / "RAG quality" / "retrieval evaluation" | `rag-auditor` | RAG pipeline evaluation: retrieval metrics + generation quality |
| "debug systematically" / "root cause analysis" / "bisect bug" | `debug-investigator` | Hypothesis-driven debugging with bisection and instrumentation |
| "markdown to PDF" / "convert md to pdf" / "export as PDF" | `md-to-pdf` | Markdown → styled PDF with Mermaid, KaTeX, and code highlighting |

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
_No active plan. Check `.github/plans/` for recent plans._
