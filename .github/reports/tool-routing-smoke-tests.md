# Tool Routing Smoke Tests

Date: 2026-05-13

## Scenarios

- PASS: `.vscode/mcp.json` validates as JSON and contains `semble` and `context-mode` server keys.
- PASS: `.github/hooks/hooks.json` validates as JSON and preserves existing `SessionStart`, `Stop`, and `PreToolUse` guardrails.
- PASS: `context-mode-dispatch.sh --self-check` exits successfully when `context-mode` is installed.
- WARN: `context-mode-dispatch.sh --self-check` exits successfully with a warning when `context-mode` is missing but `npx` is available.
- WARN: `context-mode-dispatch.sh --self-check` exits successfully with a warning when both `context-mode` and `npx` are unavailable.
- WARN: `check_agent_runtime.py` reports missing optional binaries such as `context-mode`, `npx`, or `uvx` without failing structural validation.
- PASS: routing guidance stays centralized in `.github/instructions/tool-routing.instructions.md`, with thin references from `.github/copilot-instructions.md`, `AGENTS.md`, README, and the retrieval-routing skill.

## Expected Validation Commands

```bash
python -m json.tool .vscode/mcp.json >/dev/null
python -m json.tool .github/hooks/hooks.json >/dev/null
bash -n .github/hooks/scripts/context-mode-dispatch.sh
bash .github/hooks/scripts/context-mode-dispatch.sh --self-check
python -m py_compile .github/scripts/check_agent_runtime.py
python .github/scripts/check_agent_runtime.py
```
