# Approved requirements

The proposed function is `normalize_items(items: list[str]) -> list[str]`.

- REQ-001: Raise `TypeError` when `items` is not a list.
- REQ-002: Return the items in their original order.
- REQ-003: Retain every occurrence of an item, including repeated values.
