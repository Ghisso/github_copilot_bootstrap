---
name: add-dependency
visibility: public
description: |
  Add a Python dependency with validation. Checks existence, adds with uv,
  updates lockfile, and runs tests to verify compatibility. Use when asked to
  add a dependency, install a package, or add a library.
argument-hint: "[package-name]"
---

# add-dependency — Dependency Management

## Step 1: Check Package
```bash
uv pip index versions [package] 2>/dev/null | head -5
```

## Step 2: Add
```bash
# Runtime dependency
uv add [package]

# Dev dependency
uv add --dev [package]

# With version constraint
uv add "[package]>=1.0,<2.0"
```

## Step 3: Lock
```bash
uv lock
```

## Step 4: Test Compatibility
```bash
uv run pytest tests/ -q
```

## Step 5: Check for Issues
```bash
# Check for deprecation warnings
uv run pytest tests/ -W default::DeprecationWarning 2>&1 | grep -i deprecat || echo "Clean"

# Verify import works
uv run python -c "import [package]; print('Import OK')"
```

## Step 6: Report
```
Dependency added: [package]==[version]
  Type: runtime / dev
  Tests: PASS/FAIL
  Conflicts: none / [details]
  Deprecation warnings: none / [details]
```

## Removing Dependencies
```bash
uv remove [package]
uv lock
uv run pytest tests/ -q
```
