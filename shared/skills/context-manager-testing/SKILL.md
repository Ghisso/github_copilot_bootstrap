---
name: context-manager-testing
visibility: background
description: |
  Correctly test that context manager __exit__ calls cleanup methods (close, etc.).
  Triggers:
  - Writing `with obj: pass` followed by a comment like "just verify no exception"
  - `reviewer` with the `tests` profile flags a context manager test as zero-assertion
  - Wanting to verify that __exit__ calls close(), flush(), or similar
user-invocable: false
---

# Context Manager Testing

## Problem

`with obj: pass` only verifies that `__enter__` and `__exit__` don't raise.
It does NOT verify that `close()` (or any other method) was called inside `__exit__`.

A reviewer will flag this as a **zero-assertion test**.

## Context / Trigger Conditions

- Test method says `with tracker: pass  # verify no exception` with no mock assertions
- You have a class where `__exit__` calls `self.close()` and want to verify that
- Any Protocol or implementation where the context manager must guarantee cleanup

## Solution

Use `patch.object` with `wraps=` to spy on the real method while still executing it:

```python
def test_context_manager_calls_close(self) -> None:
    """Exiting context manager calls close()."""
    obj = MyClass()
    with patch.object(obj, "close", wraps=obj.close) as mock_close, obj:
        pass
    mock_close.assert_called_once()
```

**Key pattern:** `with patch.object(..., wraps=...) as mock, obj:` — combine both
context managers in one `with` statement (ruff SIM117 requires this).

### Why `wraps=obj.close`?

- `wraps=obj.close` keeps the real `close()` behavior (no side effects lost)
- The spy records calls without replacing the implementation
- Safe for NoopTracker and similar pass-through implementations

### For mock-based tests (no real object):

When the tracker is already a `MagicMock`, `close` is already a Mock:

```python
def test_context_manager_closes_task(self, mock_task: MagicMock) -> None:
    """__exit__ calls task.close()."""
    with patch("src.tracking.clearml_tracker._import_task") as mock_import:
        mock_task_cls = MagicMock()
        mock_task_cls.init.return_value = mock_task
        mock_import.return_value = mock_task_cls

        from src.tracking.clearml_tracker import ClearMLTracker
        with ClearMLTracker(cfg, "task") as tracker:
            tracker.log_scalar("x", "y", 1.0)

    mock_task.close.assert_called_once()
```

## Verification

The test must have at least one `assert_called*` after exiting the `with` block.

```python
mock_close.assert_called_once()      # called exactly once
mock_close.assert_called()           # called at least once
mock_close.assert_not_called()       # negative case (open, not closed)
```

## Example — Full Test Class

```python
class TestNoopTrackerContextManager:
    def test_close_called_on_exit(self) -> None:
        """NoopTracker.__exit__ calls close()."""
        tracker = NoopTracker()
        with patch.object(tracker, "close", wraps=tracker.close) as mock_close, tracker:
            pass
        mock_close.assert_called_once()

    def test_context_manager_returns_self(self) -> None:
        """__enter__ returns the tracker itself."""
        tracker = NoopTracker()
        with tracker as t:
            assert t is tracker

    def test_exception_still_closes(self) -> None:
        """close() is called even if body raises."""
        tracker = NoopTracker()
        with patch.object(tracker, "close", wraps=tracker.close) as mock_close:
            with pytest.raises(ValueError):
                with tracker:
                    raise ValueError("boom")
        mock_close.assert_called_once()
```

## Related

- `try/finally` for exactly-once cleanup vs `try/except` dual-close risk
- `test-helper-public-api` skill — public API must be tested, not private methods
