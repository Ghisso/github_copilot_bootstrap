---
name: setup-project
visibility: public
description: |
  Initialize a new Python project from this scaffold, sized to the project
  type actually requested (library, CLI tool, Hydra pipeline, or API
  service). Creates a minimal directory structure, copies config files,
  initializes git and uv. Use when starting a new project or asked to set
  up a project.
argument-hint: "[project-name]"
---

# setup-project — Initialize New Project

## Step 1: Create a Minimal Directory Structure

Scaffold only what the requested project type needs — do not impose one
universal layout on every project.

```bash
mkdir -p src tests
touch src/__init__.py tests/__init__.py tests/conftest.py .env.example
```

Add directories only for what this project actually needs:

| Project type | Additional directories |
|---|---|
| Library / package | none beyond `src/<package>/` |
| CLI tool | `scripts/`, if it needs standalone entrypoints |
| Hydra-config ML pipeline | `src/configs/`, `src/pipelines/` — only when Hydra is actually in scope (see `create-feature`'s config-pattern check) |
| API/service | `src/api/` — see `bentoml-service`/`deploy-service` for service-specific layout |
| Any type, if requested | `docs/`, `examples/`, `data/`, `output/` |

## Step 2: Initialize Git and Python

```bash
git init
uv init
uv add --dev pytest pytest-cov pytest-asyncio "mypy>=1.0" "ruff>=0.3"
```

`git init` here is a deliberate, one-time exception to the normal
`PRE-FLIGHT -> BRANCH -> ...` lifecycle: that lifecycle assumes an existing
clean `dev` branch to branch from, and no branch exists until this step
creates the repository. Once the repository exists, all further work —
including finishing this scaffold — follows the normal lifecycle.

## Step 3: Install the Bootstrap
- Regenerate this bootstrap with `uv run python scripts/generate_targets.py --all`
- Install the generated target with `uv run python scripts/install_bootstrap.py <project-root>`
- Let the installer create and preserve the nested `.claude/` AI-state repo
- Copy only project-owned files such as `pyproject.toml` and `.env.example`

## Step 4: Configure Project

```bash
# Update pyproject.toml with project name
cp .env.example .env   # local-only; .env stays gitignored
```

- `.env.example` holds placeholder names only (e.g. `API_KEY=` or
  `API_KEY=changeme`) — never real-looking values, since this file is
  tracked and reviewed. Real secrets go only in the gitignored `.env`.
- Fill the `## Project State` slot in the installed
  `.claude/instructions/workspace.instructions.md` (its `workspace.md`
  alias carries the same content). This project has no `shared/policies/`
  of its own — that canonical source lives only in the bootstrap
  repository this scaffold was installed from. See `onboard`'s Project
  State step for the full explanation of when to edit the canonical source
  instead of the generated copy.

## Step 5: pyproject.toml ruff config
```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "D", "G", "S", "B", "A", "C4", "SIM", "TCH"]
ignore = ["D107", "D105", "D401", "D104", "D203", "S101", "D413"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.isort]
known-first-party = ["src"]
```

## Step 6: Verify
```bash
uv run python -c "import src; print('OK')"
uv run pytest tests/ -v              # empty suite, should pass
uv run mypy src/ --ignore-missing-imports --explicit-package-bases
uv run ruff check src/ tests/
```

## Step 7: Initial Commit

Stage only the files this scaffold actually created — Step 1 may not have
created `src/configs/` or the optional directories:

```bash
git add pyproject.toml .gitignore .env.example src/__init__.py tests/__init__.py tests/conftest.py
git commit -m "feat: initialize project with AI scaffold"
```
