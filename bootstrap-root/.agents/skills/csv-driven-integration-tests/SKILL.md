---
name: csv-driven-integration-tests
visibility: public
description: |
  Build integration test datasets as CSV files with expected outputs, then use
  pytest parametrize to run them against real (or mock) components. Especially
  effective for discovering regex classifier pattern gaps and SQL generation bugs.
  Triggers:
  - "I want integration tests for my classifier / router / SQL generator"
  - Building a test dataset for component-level validation
  - Need to check if a regex-based classifier handles real-world query variance
---

## Problem

Unit tests cover happy paths but miss the breadth of real-world input. Regex-based
classifiers and LLM-driven components (e.g., text-to-SQL) need large parametrized
test suites to surface pattern gaps. Hand-writing fixture CSVs causes silent column
misalignment.

## Context / Trigger Conditions

- You want to validate a component (classifier, text-to-SQL, router) against 50+ inputs
- The component uses regex patterns or an LLM to classify / generate output
- You need the dataset to be human-readable AND uploadable (e.g., HF Hub)
- You want deterministic, reproducible tests against a fixture database

## Solution

### Step 1: Generate Fixture Data Programmatically

**Never hand-write CSV files.** Use `csv.DictWriter` or pandas to generate them:

```python
import csv
from pathlib import Path

rows = [
    {"id": 1, "title": "Resolution 2700", "year": 2023, "chapter7": True, ...},
    {"id": 2, "title": "Resolution 2701", "year": 2024, "chapter7": False, ...},
]

path = Path("tests/fixtures/test_data.csv")
with path.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
```

**Why:** Hand-edited CSVs silently drift — 36-column header vs 34-value rows causes
`pandas.errors.ParserError` or worse, silent column shift. `DictWriter` guarantees
key-value alignment.

### Step 2: Create Test Cases CSV

Structure with these columns:

| Column | Purpose |
|--------|---------|
| `id` | Unique int for debugging |
| `question` | Natural language input |
| `expected_route` | Expected classification (sql/semantic/both) |
| `expected_sql` | Expected SQL (empty for non-SQL routes) |
| `category` | Test category for grouping (counting, superlative, vote_lookup...) |
| `description` | Human-readable description |
| `expected_min_rows` | Min expected result rows (for SQL validation) |
| `validate_columns` | Pipe-delimited column names to check in output |

### Step 3: Pre-validate Expected SQL

Before writing tests, validate all expected SQL against the fixture DB:

```python
import sqlite3

conn = sqlite3.connect(":memory:")
# ... load fixture data ...

for case in sql_cases:
    try:
        cursor = conn.execute(case["expected_sql"])
        rows = cursor.fetchall()
        assert len(rows) >= int(case["expected_min_rows"])
    except Exception as e:
        print(f"FAIL id={case['id']}: {e}")
```

**Critical GROUP BY gotcha:** For `GROUP BY` queries, `len(rows)` is the number
of groups, NOT the aggregate value. Don't assert `rows[0]["count"] >= expected_min_rows`
— assert `len(rows) >= expected_min_rows` instead. If you need to check the aggregate,
use a separate `expected_aggregate` column.

### Step 4: Module-Scoped Fixtures

```python
# tests/integration/conftest.py
import pytest

@pytest.fixture(scope="module")
def fixture_db(tmp_path_factory):
    """Load fixture CSV into SQLite once per module."""
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    manager = SQLiteManager(str(db_path))
    manager.load_csv("tests/fixtures/test_data.csv")
    return manager

@pytest.fixture(scope="module")
def all_test_cases():
    """Load test cases CSV."""
    import csv
    with open("tests/fixtures/test_cases.csv") as f:
        return list(csv.DictReader(f))
```

### Step 5: Parametrized Tests

```python
def _load_ids():
    """Load test case IDs for parametrize (called at collection time)."""
    import csv
    with open("tests/fixtures/test_cases.csv") as f:
        return [row["id"] for row in csv.DictReader(f)]

class TestRouteClassification:
    @pytest.mark.parametrize("case_id", _load_ids())
    def test_route_matches_expected(self, case_id, all_test_cases, classifier):
        case = next(c for c in all_test_cases if c["id"] == case_id)
        result = classifier.classify(case["question"])
        assert result.route == case["expected_route"], (
            f"Q: {case['question']}\n"
            f"Expected: {case['expected_route']}, Got: {result.route}\n"
            f"Reasoning: {result.reasoning}"
        )
```

**Tip:** Use `_load_ids()` at module level so pytest shows each test case as a
separate parametrized test (visible in `-v` output).

### Step 6: Surface & Fix Pattern Gaps

When tests fail, the failure message shows EXACTLY which patterns are missing:

```
FAILED test_route[42] - Q: "List resolutions mentioning Syria"
  Expected: sql, Got: semantic
  Reasoning: No strong signals detected, using default route
```

This tells you: need `\blist\b.*\bresolutions?\b` pattern (not just `\blist\s+all\b`).

**Common pattern gaps discovered empirically:**
- "list resolutions" (not just "list all")
- "which resolutions" (structured lookup)
- Superlatives with intervening words: "latest resolution on Libya" ≠ "latest resolution"
- Standalone "abstain" without "voted"
- Junction lookups: "what countries/subjects/topics"
- Plural variants: "meeting records" not just "meeting record"

**Common BOTH pattern mistakes:**
- `\bwhat\b.*\b(?:latest|most recent)\b` is too broad — matches pure SQL superlatives
- Tighten to require content words: `\b(?:latest|most recent)\b.*\b(?:say|about|content|discuss)\b`

## Verification

```bash
# Pre-validate SQL
uv run python tests/fixtures/validate_sql_cases.py

# Run integration tests
uv run -m pytest tests/integration/ -v

# Full regression
uv run -m pytest tests/ -v
```

## Example

CSV-driven tests with 64 test cases across 11 categories revealed:
- 6 missing SQL patterns in a regex classifier
- 1 overly-broad BOTH pattern that stole SQL classifications
- 1 GROUP BY validation false positive in test assertions

Net result: classifier went from 43/64 → 64/64 correct after fixes.
Full regression: all tests passed, 0 failures.
