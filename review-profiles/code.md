# Code Review Profile

Use for Python source quality, maintainability, and local design.

## Checklist

- Functions are small, single-purpose, and readable.
- Classes follow SOLID principles where they apply.
- No unnecessary duplication or avoidable coupling.
- Public functions and classes have Python 3.12+ type hints.
- Public APIs have useful Google-style docstrings.
- Logging uses percent formatting, not f-strings.
- File I/O uses `pathlib.Path`.
- Resources use context managers.
- Exceptions are specific and chained with `from e`.

## Severity

- Critical: Broken behavior, unsafe error handling around external calls, or security-adjacent defects.
- Major: Missing public typing/docstrings, avoidable duplication, unclear structure, or brittle coupling.
- Minor: Naming, comments, style polish, or small simplification opportunities.

