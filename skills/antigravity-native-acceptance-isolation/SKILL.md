---
name: antigravity-native-acceptance-isolation
description: |
  Isolate native Antigravity CLI acceptance when `agy` silently reuses a
  persisted project outside the current working directory. Use before sending
  disposable-workspace prompts to an external Antigravity service.
---

# Antigravity Native Acceptance Isolation

## Problem

Launching `agy` from a disposable repository does not prove that the CLI uses
that repository. A persisted Antigravity project can remain active and expose a
different workspace to the model.

## Context / Trigger Conditions

Use this workflow for native acceptance, especially when a response cites paths
outside the disposable repository or unexpectedly reads another project's
`AGENTS.md`.

## Solution

1. Create and install into a disposable Git repository.
2. Start every acceptance conversation with `--new-project --sandbox`.
3. Before sending repository guidance, use a read-only prompt that returns only
   the absolute workspace root.
4. Compare the reported root with the exact disposable path.
5. Stop immediately if they differ. Do not count that conversation as evidence.
6. Keep `--new-project --sandbox` on every later acceptance invocation.

## Verification

The isolation check passes only when the native response reports the exact
disposable repository path and later file links remain beneath that path.

## Example

```bash
agy -p "Read only. Return only the absolute workspace root you are using." \
  --output-format json --mode plan --new-project --sandbox
```
