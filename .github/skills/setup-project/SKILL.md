---
name: setup-project
description: |
  Initialize a new Python AI project from this scaffold. Creates directory
  structure, copies config files, initializes git and uv.
  Use when starting a new project or asked to set up a project.
argument-hint: "[project-name]"
---

# setup-project — Initialize New Project

## Step 1: Create Directory Structure
```bash
mkdir -p src/{configs,models,pipelines,utils,api}
mkdir -p tests/{unit,integration,fixtures}
mkdir -p {docs,examples,scripts,data,output}
touch src/__init__.py src/configs/__init__.py
touch tests/__init__.py tests/conftest.py
```

## Step 2: Copy Scaffold Files
- Copy `.github/` directory (instructions, agents, skills, plans, session_logs, MEMORY.md)
- Copy `pyproject.toml`, `.gitignore`, `.env.example`
- Copy `copilot-instructions.md` to new project's `.github/`

## Step 3: Configure Project
```bash
# Update pyproject.toml with project name
# Update copilot-instructions.md Project State section
# Add required env vars to .env.example
cp .env.example .env
```

## Step 4: Initialize
```bash
git init
uv init
uv add --dev pytest pytest-cov mypy ruff pytest-asyncio
uv add --dev "ruff>=0.3" "mypy>=1.0"
```

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
```bash
git add .github/ pyproject.toml .gitignore .env.example
git commit -m "feat: initialize project with AI scaffold"
```
